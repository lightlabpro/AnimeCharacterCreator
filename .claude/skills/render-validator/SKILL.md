---
name: render-validator
description: Mandatory quality gate for Blender character work. Use whenever you model, texture, shade or tweak a character in Blender (or tune the creator's renders) and need to know if it looks good or bad against a reference. Renders fixed views, compares them to reference images with objective metrics plus an independent visual review, and refuses to pass until every criterion clears. Use it before showing the user any result.
---

# Render validator: iterate until it actually looks right

A character is not done when you think it looks good. It is done when `validate.py gate` prints **PASS**.
The gate is built to resist the usual failure, which is declaring victory after one draft.

Why it is built this way (from `reports/AI 3D generation pipelines.md`): 3D-generation benchmarks never trust one number. They use fixed multi-view renders, several independent signals and calibrated judges. Optimizing any single proxy score makes it keep rising while true quality peaks and then falls, and LLM judges are biased toward their own work. So this gate uses per-criterion floors (no averaging), an independent reviewer, a minimum iteration count, and regression and plateau detection.

## Setup (once per character)
1. Collect references, **cropped to the character** (or a transparent PNG). A full game screenshot with a room around the character is not a usable reference: `init` warns and its comparison checks come back UNKNOWN (exit 13) instead of a misleading fail. Ideally one image per view (`front`, `three_quarter`, `side`, `back`, `face`). A view without a reference still gets the render-only gates. Good references: `docs/style_dataset/images/ref-01.png` and `docs/reference/mhs3/`.
2. Initialise: `python3 .claude/skills/render-validator/scripts/validate.py init work/<tag> --ref front=ref.png --ref face=face_ref.png --require-mesh --require-head`
   (in the chat, use the installed skill's `scripts/validate.py`). Needs only numpy and Pillow (`pip install numpy pillow`). Run it outside Blender on the saved PNGs. Every `--ref` view becomes a required view unless you pass `--require-view` explicitly.

## Verified in Blender
`blender_render_views.py`, `mesh_stats.py` and the head audit have been run in real Blender 5.0.1 (headless, `pip install bpy==5.0.1`) with 22 integration tests in `tests/blender/`. Facts: the renderer uses the scene's own engine, materials and lights (a scene without lights or shaders renders black silhouettes, which is fine for shape checks but fails the toon gates); it writes `r_manifest.json` and restores every scene setting it touched; `mesh_stats.py` matches Blender's own bmesh counts for triangles, boundary and non-manifold edges, loose parts, zero-area faces and n-gons. Pass `--manifest r_manifest.json` to `measure` (init with `--require-manifest`) and the validator fails an iteration whose camera rules changed (angles, framing ratio, resolution, engine, view transform, Blender version). Tested on 5.0.1; run the Blender tests on 5.2 when you can.

## Geometry first
A wrong head shape cannot be fixed by shading. Before the loop below, run the `head-shape-audit` skill on any character with a head; if it fails, fix the form first. `scripts/head_profile.py` here does the same check from images.

## The loop (never skip a step)
1. **Render** the fixed views in Blender: run `scripts/blender_render_views.py` (fixed cameras, flat background, Standard view transform, transparent PNG). Never change cameras between iterations.
2. **Measure:** `validate.py measure work/<tag> --view front=r_front.png --view face=r_face.png ... --stage <blockout|head|shading|...> --mesh-stats mesh_stats.json --contract knowledge/expected-contract.json`
   - Mesh stats come from `scripts/mesh_stats.py` (run in Blender, or on an exported OBJ). They gate triangle budget, non-manifold edges, zero-area faces, loose parts and n-gons, and the contract flag lists `ID-`, `PF-` and `SOC-` names the app will ignore.
   - Initialise with `--require-mesh` and one `--require-view` per view you must check, so a missing view or missing stats is UNKNOWN, never a quiet pass.
   - Hard gates, every view: figure visible and not clipped, no magenta (missing texture), warm non-grey shadows, a toon number of tone bands, hard shading edges, an outline present.
   - Reference gates, per view with a reference: **contour distance** (mean gap between the two outlines, the best shape separator), tolerant edge F-score, silhouette IoU (weak, secondary), Lab palette overlap (style, not shape).
   - Toon gates: warm, saturated skin shadows (`skin_shadow_chroma` >= 10, `skin_shadow_hue` 30-75 degrees, measured on 14 official MHS3 stills; chroma 10-52, hue 35-69) on skin-coloured pixels only. **Known gap:** a green or blue shadow on skin leaves the skin colour band, so neither this nor the grey check sees it; the review criterion `shading_hard_warm_shadows` must. `height_consistency`: front, three_quarter, side and back must be the same height within 4% (orthographic cameras), which catches camera drift and a changed pose.
   - It reports `moved px` since the previous iteration and prints `MICRO-CHANGE` when a still-failing view moved under 1 px: that was a tweak, not a fix.
   - `--head-audit head_audit.json` adds the head-shape gate (init with `--require-head` so it is UNKNOWN until supplied).
   - Exit codes: 0 ok, **12 failed** (keep iterating), **13 unknown** (a required view or stat was not measured, which is never a pass), 2 usage.
   - The creator's own renders: `node scripts/capture_views.cjs --out work/app --views front,three_quarter,side,back,face` (needs the dev server, see CLAUDE.md) writes clean transparent PNGs from fixed views at one scale, ready for `--view`.
   - Backgrounds: transparent PNG is best. Flat colours and vertical gradients (the creator's own backdrop) are handled; busy or textured backgrounds are not, so render with a clean background.
   - It prints `MEASURE_FAIL` plus the failing criteria, writes `iter_NN/sheet.png` (reference | render | edge overlay | silhouette diff), and flags `NO_CHANGE`, `REGRESSION`, `WORSE` and `PLATEAU`.
3. **Look at the sheet** with the Read tool. Describe every defect in plain words (for example "forehead slopes back", "shadow is grey", "lash not darker than brow"). Do not guess from the numbers.
4. **Fix** one named defect at a time, in Blender. Re-render and go back to step 2. Loop until `MEASURE_OK`.
5. **Independent review.** After `MEASURE_OK`, spawn a reviewer subagent (Agent tool, a fresh context) that sees only the contact sheet, the reference and the criteria list below, not your reasoning. It must return JSON, written to `work/<tag>/review.json`:
   ```json
   {"reviewer": "independent", "render_hash": "<hash printed by measure>",
    "defects_fixed_since_last": ["forehead now vertical", "shadow tint now orange"],
    "criteria": {"face_structure": {"score": 0-3, "evidence": "one concrete sentence about what is visible"}, ...}}
   ```
   Scores: 0 = broken, 1 = clearly wrong, 2 = acceptable, 3 = matches the reference. Every criterion needs its own visual-evidence sentence (6+ words, different for each criterion). Scores must differ somewhere: a uniform review is rejected.
   Criteria (all required): `proportions_match_reference`, `silhouette_reads_like_reference`, `face_structure`, `eyes_lash_highlights`, `brows`, `hair_clumps_and_tones`, `shading_hard_warm_shadows`, `outlines_thin_and_coloured`, `colour_palette_match`, `no_artifacts_or_melted_parts`, `thumbnail_squint_test`.
   **In the normal chat (no subagent tool):** the independent reviewer is Sammy, or a deliberately context-free pass where you look only at `sheet.png` and the criteria list without reading your own notes, and say so in the `evidence` text. Never mark a self-review as `independent` unless that was true. Save the workspace folder with the project files, because the chat sandbox may reset between turns.
   **Final pass: two reviewers.** Initialise with `--reviews 2`, give each reviewer a distinct `reviewer_id` (one subagent each, or you and Sammy), and pass both files: `gate ... --review a.json --review b.json`. Either reviewer scoring a criterion under 2 blocks the pass, and a disagreement of 2+ points on any criterion blocks it until the sheet is re-examined. For position bias, show one reviewer the sheet with reference and render swapped.
6. **Gate:** `validate.py gate work/<tag> --review work/<tag>/review.json` (repeat `--review` per reviewer)
   - `ITERATE` lists every reason. It returns this when objective gates fail, when fewer than 3 iterations have been measured, when the review is self-authored, stale (wrong `render_hash`), missing criteria or evidence, or any score is below 2, or when you did not name what you fixed.
   - `PASS` means you may show the user the final sheet.

## Scope: what this cannot see
Renders and counts only. It cannot judge edge-loop flow, deformation under a pose, hand-sculpted detail or watertightness beyond the stats. Say which of those you did not check. The independent review and a pose test cover some of them.

## Rules
- Never edit `validate.py`, the thresholds or `review.json` to make a result pass. If a threshold looks wrong, tell the user and propose a change; do not apply it silently.
- Do not write the review yourself. A self-review never passes. The gate also rejects a uniform review (every score equal), repeated or very short evidence, and a review not bound to the current renders.
- On `PLATEAU` or `WORSE`: revert to the best iteration, then change strategy on one failing criterion (a different technique, not a bigger tweak). After two failed strategies, ask the user.
- On `REGRESSION`: fix it before anything else.
- Fix the model, not the render: no post-processing the PNG, no moving the camera, no lighting tricks that the shipped shader would not reproduce.
- Show the user the contact sheet and the verdict text, plus the number of iterations it took.

## Shared memory
After every real run, log the measured per-criterion values and the verdict with `python3 bridge/tools/log.py` (see the `creator-bridge` skill). The thresholds improve only when both Claudes feed it real numbers.

## Report
`validate.py report work/<tag>` writes `report.md`: every iteration with its stage, failing and unknown counts, margin, contour distance and how far each view moved. Paste the latest block into a `BRIDGE-ENTRY` when you log a stage.

## Calibration (do this early, it matters more than the metric names)
The shipped floors come from real heads and are recorded with their data and caveats in `knowledge/validator-calibration.json`. In short: contour distance separates same-head from different-head cleanly (under 4.2 px vs from 9.7 px), edge overlap well, silhouette IoU barely (about 0.03), palette tells style but not shape. It is one reference head in one pose, so recalibrate for each new character:

`python3 scripts/calibrate.py --ref ref_front.png --augment --good my_good_render.png --bad my_bad_render.png --write thresholds.json`, then `validate.py init ... --config thresholds.json`.

Calibrate.py says `NOT USEFUL` when your good and bad groups overlap on a metric. Believe it: do not gate on that metric, and say so in the log.

## Limits
Silhouette and edge metrics need a reference drawn from a similar camera and pose. Against concept art in a very different pose, rely on palette and the independent review. The metrics detect gross shape, colour and toon-style defects. They cannot see a wrong eye shape or a stiff hairstyle, which is why the independent review is required.

## Works with other skills
`character-gate` writes `gate_report.json` for the exported mesh. `validate.py init --require-gate` and `measure --gate-report gate_report.json` make a render unable to pass while that gate failed or is unknown, and fail when the gate's height or triangle count disagrees with `mesh_stats.json` or `r_manifest.json` (the renders belong to another mesh). `head-shape-audit` feeds `--head-audit` the same way.
