---
name: reference-match-judge
description: Use when a render looks different from its reference images, especially MHS3 frames - Claude describes both images feature by feature, TypeSafe judges which features are off and picks the correction from a fixed menu, then Claude applies it and repeats.
---

# Reference match judge (Claude sees, TypeSafe decides)

Claude can see images but should not grade its own work; TypeSafe (jev-1.13.0) cannot see images but judges words
well. This skill splits the job: **Claude analyses the images in words, TypeSafe decides what is off and which
correction to make.** Use it whenever a model, shader, hair, outfit or pose looks different from its references,
with MHS3 (Monster Hunter Stories 3) frames as the main reference. It works together with the TypeSafe rules already
in the repo (docs/VALIDATORS.md "TypeSafe usage rules"): words only, yes = good, a "none" option, choices asked in both
option orders, answers under 0.4 confidence go to a human.

Files (repo `AnimeCharacterCreator-main`):
- `blender/tools/typesafe_visual_judge.py` - the judge (runs on Sammy's PC, key from TYPESAFE_API_KEY; never fake a
  judgment if it is missing).
- `blender/tools/visual_corrections/<region>.json` - the correction menu per region (eyes, nose_mouth, face, ears exist). Each entry:
  `id`, a plain description, and the exact `setting` in code it changes (one step).
- `docs/qa/<work>/visual_<tag>_<region>.json` - Claude's analysis for one render; `visual_judge_<tag>_<region>.json`
  - TypeSafe's result.

## Loop

1. **Board.** Render ours at the reference's framing (same view, similar crop and scale) and build one image: ours on
   top, the reference below (e.g. `render_look.py` close-up + the board script). Look at the board, not memory.
2. **Analyse (Claude).** Write `visual_<tag>_<region>.json`:
   `{"region", "subject", "reference_style", "features": {name: {"reference": "...", "ours": "..."}}}`.
   - Use the same feature list every round for a region (eyes: outline_shape, height_to_width, eye_spacing,
     iris_size, iris_colour, iris_pattern, pupil, highlight, sclera, upper_lid_line, lower_lid_line, brow_shape,
     brow_position, brow_colour, flatness).
   - Describe the reference first, then ours, **each on its own** in the same concrete terms: shape, size relative to
     the eye/head, colour, position, thickness. No verdict words (better, worse, wrong, matches).
   - **Measure anything measurable** - ratios, sizes, spacing - in pixels on the board or on the mesh, and write the
     number into the description. Eyeballed proportions were wrong in practice (n49: "about half as tall" when both
     eyes measured 0.60/0.61) and sent TypeSafe toward a wrong fix.
   - Describe what is visible now, honestly, including when a correction changed nothing.
   - Note what the reference cannot show, inside the description, so TypeSafe does not chase it: an open mouth in the
     reference when ours is closed (nose/mouth f4: mouth_line_wider was picked four times), a skull hidden under hair
     (leave the skull out of the shadow comparison).
   - Put a second view in the board when one view hides the problem (front + 3/4 for the face; a close-up crop for
     small features like ears), and check the whole head after a local change (ears e3: a box mask lit the skull).
3. **Judge (TypeSafe).** On the PC:
   `python blender/tools/typesafe_visual_judge.py <analysis.json> blender/tools/visual_corrections/<region>.json <out.json> [--exclude id,id]`
   It asks in one request: `analysis_usable` (are the descriptions concrete and comparable?), one yes/no per feature
   (do the two descriptions describe the same look?), and `first_fix` (a choice over the menu plus "none"), then the
   choice again with the options reversed. If the two orders disagree it re-asks with only the two candidates and
   "none" in both orders. It outputs the features ranked by `p_same` and `first_fix.apply` (set only when the orders
   agree and the analysis is usable).
4. **Act (Claude).**
   - `analysis` says rewrite → rewrite the descriptions, do not change the model.
   - `apply` is set → make exactly that one step from its `setting`, rebuild/re-render, re-run the deterministic
     checks (dataset bands, topology). If those fail, revert the step and report.
   - `apply` is null (orders still disagree) → change nothing; report the two candidates.
   - Features marked "needs a human" are shown to Sammy, not acted on.
5. **Repeat** from step 1 with a new tag.
   - The same fix chosen again with no visible change in its feature: apply it once more at double step; if it still
     does not move, add it to `--exclude` and record why (n49: the eye-corner shape is limited by the head grid, the
     knob had no visible effect).
   - When a knob is excluded because it had no effect, exclude its opposite too (face g8: face_shadow_smaller and
     face_shadow_bigger). Exclude `add_*` entries once applied; later rounds use the thicker/thinner entries.
   - Before excluding a knob for "no effect", check what actually produces the feature (read the shade mask, the
     attribute values, the geometry normals). If the knob is aimed at the wrong cause, fix the knob's implementation
     so its menu step reaches the real cause, note it in the menu `note`, and keep the entry (face g9: the chin patch
     was the forced jaw-underside shade, not the normal blend; ears e5: the helix-line band covered only 9 vertices
     per ear on the coarse grid). Re-measure the pixel change after every step (`>30` RGB difference fraction); under
     1% means the step did nothing.
   - When the geometry itself limits a feature (no knob moves it), move the feature to a painted layer whose shape
     is free (eyes q1: the eye and later the brow painted into a texture decal from curves traced off the reference),
     and seed it from measurements of the reference so the first round already starts close.
   - Measure a shape along its whole length, not at two points: stepping knobs until two sample points match can
     still drift the overall shape (brow q2b-q20 became a folded wedge). Look at the full board after each step and
     check the face/full-head render, not only the close-up.
   - A pick that contradicts a measured number in the analysis (e.g. "wider" when ours already measures wider) is
     declined and reported, not applied; that feature goes to Sammy.
   - Angle-dependent looks (v-series view keys): render a yaw sweep (0-90 degrees), pair each angle with a reference
     at a similar estimated angle, and measure ratios that survive different characters (far eye / near eye width,
     eye width / height against the front view, iris share of the eye). Check combinations too (expressions on top of
     view keys). When two opposite picks alternate around a measured reference value, stop and exclude both.
   - Deterministic checks after a geometry step: dataset bands, topology (quads only), skin skew. A step that pushes
     a band out is reverted and excluded (face g11: chin_narrower took width@0.85 below the band).
   - Stop when `first_fix` is "none", when the two orders (and the tie-break) still disagree, when every feature is
     "matches" or "needs a human", or after about five rounds; then report the remaining off features honestly.

## Writing a new region's menu

One file per region in `blender/tools/visual_corrections/`. Each correction is one small step on one setting, phrased
as the visible result ("Make the brows thicker"), with opposite pairs where both directions make sense (thicker /
thinner, higher / lower). Keep 10-30 entries; TypeSafe always gets "none" added. When a correction is added because
TypeSafe could not express a fix, note it in the menu's `note`.

## Rules

- TypeSafe never sees images or raw numbers alone; it reads Claude's descriptions (numbers inside a sentence are fine).
- Claude never applies a correction TypeSafe did not choose with agreement, and never claims a match TypeSafe did not
  report. The deterministic checks stay authoritative: a correction that breaks them is reverted.
- Show Sammy the final board, the judge's ranked features, what was applied each round, and what is still off.
