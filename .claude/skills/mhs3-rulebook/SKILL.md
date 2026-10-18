---
name: mhs3-rulebook
description: The measured Monster Hunter Stories 3 face standards for the anime head - acceptable dimensions per region (profile depths, eye opening size and outline shape, corner tilt, pupil, lash, brows, mouth, jaw, cheeks, ears, face length) and the MHS3 shader numbers, each with a target, a strict tolerance and its source. Use before changing any head or face element, to look up what MHS3 means in numbers, and whenever a new reference, dataset result, version lesson or Sammy pick should become a rule.
---

# MHS3 rulebook: what "looks like MHS3" means, in numbers

Sammy (q36, 2026-10-18): "deep analyze the mhs3 screenshots and references, make skills and rules based off them
... establishing rules as to per acceptable dimensions for the head and elements ... make it extremely strict."
Then: "The eye shape is not matching the mhs3 one, please make them match, this is also a standard."

The rulebook is `knowledge/mhs3_face_rules.json`. The `mhs3-master-loop` skill runs it on every iteration. Never
judge a face against memory or taste when a rule exists. Never loosen a tolerance to make a version pass.

## Units (never mix them)
- **D**: pupil line to chin bottom. Mesh rules use the mesh chin. Render rules use the chin outline, which sits about
  2% higher, so compare like with like.
- **H**: skull top (highest skin vertex) to chin. This is the dataset unit (`knowledge/head-targets-dataset.json`).
- **IPD**: the reference's pupil distance after pupil alignment (`blender/tools/pupil_align_board.py`).
- **Opening width**: the eye-shape outline is measured in units of the eye opening's own width.

## Sources, in order of authority
1. **Sammy's picks.** They override everything and are recorded in the rule's `source`:
   - q34b: eyes a bit bigger, never a glare.
   - q35: no Egyptian or elongated eyes; fuller mouth; wider nose; neat shading.
   - q36: features not too far forward in profile; the eye shape is a standard.
2. **Official MHS3 renders.** Leo front (`docs/qa/head_v2/judge/leo_ref_front.png`) is measured by the same code as our
   renders (`blender/tools/mhs3_render_measure.py`), so every render rule has a like-for-like reference value.
3. **MHS3 in-game profile.** `docs/reference/mhs3/face_profile_04.png` is a ~70-degree near-profile crop of
   04-egg-lantern. Its landmarks were hand-read on a 1 px grid to about +-0.02 D.
4. **Dataset bands.** These come from 18 verified anime heads. Where MHS3 and the dataset agree (forehead 0.039 H
   behind the nose tip), the rule is firm.

## The regions (rule ids)
- **Profile P1-P8** (mesh): depth behind the nose tip at 0.3/0.4/0.5/0.6/0.8/0.9 H, plus the lower lip and chin in D.
  This group catches "features too forward": m26 failed 10 of them, and the nose sat 0.07 H ahead of the forehead.
- **Proportions F1-F4** (mesh): IPD/D, mouth height, nose-tip height, ear lobe.
- **Face outline R5-R9** (render, D units): the ear row at 0.40 D, cheeks at 0.48/0.56 D, the square adult jaw at
  0.80 D, and face length.
- **Eyes R1-R4 and E1-E7**: opening width, height and aspect, and white fraction. Lash on the iris (no gap) and lash
  thickness. Brow gap and thickness. Pupil (dark green, small), iris darkness, eye-white tone.
- **Eye shape ES1-ES2**:
  - ES1: corner tilt. Leo's corners are about level; VRoid's outer corner sat 0.27 of the width higher.
  - ES2: RMS of the upper and lower lid outline at 9 points, inner corner to outer corner, against
    `eye_shape_template`. The tolerance is 0.03 of the width.
- **Mouth M1-M2**: line width and height.
- **Shader S1-S8**: see the `mhs3-shader-match` skill.
- **TypeSafe sets** (`typesafe` block, thresholds per statement):
  - defects_vroid_mhs3 (front)
  - defects_eyes (eye close-up)
  - defects_profile (profile close-up against face_profile_04)
  - anime_check

## Adding or changing a rule
1. Measure the reference with the same tool as the render (never eyeball numbers if a detector can read them). Check
   the detector on a debug overlay first: the brow, lash and pupil detectors all misread at first in q36.
2. Write `target`, `tol` (strict: about the spread between Leo's two eyes, or the landmark precision), `source`
   (where the number came from) and `why`.
3. Run the last approved version and the version Sammy complained about. The rule must fail the complaint and must
   not fail the approved look for a measuring reason.
4. Record lessons in `lessons`. They are the trial-and-error memory: why a knob or detector was changed.

## Lessons kept from the versions (excerpt; the full list is in the JSON)
- Profile: q34 nose_lift and chin_fwd pushed the nose 0.07 H ahead of the forehead. The fix is nose_back plus a
  root lift in the band 0.28-0.05 IPD above the pupils, and the lower face is left alone.
- The face-mesh eye hole is not the visible lid edge, because the lid's inner skin shows. Place the lash by the
  render rule E1.
- Scaling the eye parts (eye_sz) more than the lid hole floats the lash. eyeline_sz and eyeline_dz exist for this.
- The front-view cheek silhouette lies behind the jaw table's front-half weight. Use cheek_tab, which covers all
  depths.
- The skin texture's warmth and scale set the lit colour (S3-S5), so tune the paint, not the light.
