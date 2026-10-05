---
name: render-validator
description: Mandatory quality gate for Blender character work. Use whenever you model, texture, shade or tweak a character in Blender (or tune the creator's renders) and need to know if it looks good or bad against a reference. Renders fixed views, compares them to reference images with objective metrics plus an independent visual review, and refuses to pass until every criterion clears. Use it before showing the user any result.
---

# Render validator: iterate until it actually looks right

A character is not done when you think it looks good. It is done when `validate.py gate` prints **PASS**.
The gate is built to resist the usual failure, which is declaring victory after one draft.

Why it is built this way (from `reports/AI 3D generation pipelines.md`): 3D-generation benchmarks never trust one number. They use fixed multi-view renders, several independent signals and calibrated judges. Optimizing any single proxy score makes it keep rising while true quality peaks and then falls, and LLM judges are biased toward their own work. So this gate uses per-criterion floors (no averaging), an independent reviewer, a minimum iteration count, and regression and plateau detection.

## Setup (once per character)
1. Collect references: ideally one image per view (`front`, `three_quarter`, `side`, `back`, `face`). A view without a reference still gets the render-only gates. Good references: `docs/style_dataset/images/ref-01.png` and `docs/reference/mhs3/`.
2. `python3 .claude/skills/render-validator/scripts/validate.py init work/<tag> --ref front=ref.png --ref face=face_ref.png`
   Needs only numpy and Pillow (`pip install numpy pillow`). Run it outside Blender on the saved PNGs.

## The loop (never skip a step)
1. **Render** the fixed views in Blender: run `scripts/blender_render_views.py` (fixed cameras, flat background, Standard view transform, transparent PNG). Never change cameras between iterations.
2. **Measure:** `validate.py measure work/<tag> --view front=r_front.png --view face=r_face.png ...`
   - Hard gates, every view: figure visible and not clipped, no magenta (missing texture), warm non-grey shadows, a toon number of tone bands, hard shading edges, an outline present.
   - Reference gates, per view with a reference: silhouette IoU, tolerant edge F-score, Lab palette overlap.
   - It prints `MEASURE_FAIL` plus the failing criteria, writes `iter_NN/sheet.png` (reference | render | edge overlay | silhouette diff), and flags `NO_CHANGE`, `REGRESSION`, `WORSE` and `PLATEAU`.
3. **Look at the sheet** with the Read tool. Describe every defect in plain words (for example "forehead slopes back", "shadow is grey", "lash not darker than brow"). Do not guess from the numbers.
4. **Fix** one named defect at a time, in Blender. Re-render and go back to step 2. Loop until `MEASURE_OK`.
5. **Independent review.** After `MEASURE_OK`, spawn a reviewer subagent (Agent tool, a fresh context) that sees only the contact sheet, the reference and the criteria list below, not your reasoning. It must return JSON, written to `work/<tag>/review.json`:
   ```json
   {"reviewer": "independent", "render_hash": "<hash printed by measure>",
    "defects_fixed_since_last": ["forehead now vertical", "shadow tint now orange"],
    "criteria": {"face_structure": {"score": 0-3, "evidence": "one concrete sentence about what is visible"}, ...}}
   ```
   Scores: 0 = broken, 1 = clearly wrong, 2 = acceptable, 3 = matches the reference. Every criterion needs a quoted visual-evidence sentence (20+ characters).
   Criteria (all required): `proportions_match_reference`, `silhouette_reads_like_reference`, `face_structure`, `eyes_lash_highlights`, `brows`, `hair_clumps_and_tones`, `shading_hard_warm_shadows`, `outlines_thin_and_coloured`, `colour_palette_match`, `no_artifacts_or_melted_parts`, `thumbnail_squint_test`.
   For a stronger check, ask the reviewer twice with reference and render swapped in the sheet and keep the lower score (position bias).
6. **Gate:** `validate.py gate work/<tag> --review work/<tag>/review.json`
   - `ITERATE` lists every reason. It returns this when objective gates fail, when fewer than 3 iterations have been measured, when the review is self-authored, stale (wrong `render_hash`), missing criteria or evidence, or any score is below 2, or when you did not name what you fixed.
   - `PASS` means you may show the user the final sheet.

## Rules
- Never edit `validate.py`, the thresholds or `review.json` to make a result pass. If a threshold looks wrong, tell the user and propose a change; do not apply it silently.
- Do not write the review yourself. A self-review never passes.
- On `PLATEAU` or `WORSE`: revert to the best iteration, then change strategy on one failing criterion (a different technique, not a bigger tweak). After two failed strategies, ask the user.
- On `REGRESSION`: fix it before anything else.
- Fix the model, not the render: no post-processing the PNG, no moving the camera, no lighting tricks that the shipped shader would not reproduce.
- Show the user the contact sheet and the verdict text, plus the number of iterations it took.

## Calibration (do this early, it matters more than the metric names)
Thresholds in `validate.py` (`DEFAULTS`) are starting points. Toon statistics were checked on the MHS3 reference stills (tone bands 5-14, hard-edge ratio 0.18-0.57, shadow chroma 4-40), but the reference gates (`sil_iou` 0.80, `edge_f` 0.35, `palette` 0.55) are unvalidated. Render 10-20 characters you judge good and bad, run `measure` on them, and propose floors that separate the two. Pass overrides with `init --config thresholds.json`.

## Limits
Silhouette and edge metrics need a reference drawn from a similar camera and pose. Against concept art in a very different pose, rely on palette and the independent review. The metrics detect gross shape, colour and toon-style defects. They cannot see a wrong eye shape or a stiff hairstyle, which is why the independent review is required.
