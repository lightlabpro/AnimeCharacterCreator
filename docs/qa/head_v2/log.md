# Head v2 log

## q22 (2026-10-16) - new model
Sammy (after the q21 boards): "those look really bad. please, use all the skills, typesafe, and the book knowledge,
and start a new 3d model"; mid-way: "you're deviating way far from it being an anime character" -> style chosen with
Sammy: MHS3 / Leo.

Pipeline (blender/head_v2): sdf_head.py (signed-distance sculpt: dataset-median section widths, face relief, ears) ->
view_v2.remesh (voxel quads + relax + shrinkwrap) -> mouth_v2 (slot + cavity + tooth arches + tongue + keys) ->
face_paint_v2 (eyes, lashes, brows, nose / lip / ear marks in Leo's proportions projected onto the face; eye and brow
keys as 2D transforms) -> build_v2 (normals, identity keys, pieces follow the skin) -> pc_v2 (Sammy's Blender: n56
toon skin material with v2 constants) -> export_v2 (pack head_mhs3_v2).

Decisions and reasons:
- Curved face front (outer eye corner turning ~50 deg): drawn eyes foreshorten in 3/4 and profile by themselves
  (Graphic Novel "eyes wrap", TypeSafe 0.97); flatter across the iris so the profile iris is a narrow upright oval set
  back under the brow (books' profile-eye rule).
- Leo layout measured on hair-free rows: pupil line h 0.445 (D = 0.555 H), eye 0.33 D, pupils 0.72 D, nose 0.49 D,
  mouth 0.64 D / 0.49 D wide. Lower face narrower than the dataset median at 0.9 H (Leo's V jaw) - deliberate.
- Real mouth: cavity, tooth arch tapering out of sight (Pavelec p101), tongue; jaw rotation with a bowl lower lip and
  a small upper-lip lift (MHS3 open mouths).
- Anime shading: n56's analytic face normal (ellipsoid + forward push) mixed by an_w; live normals in Blender from a
  smoothed proxy with the same keys (baked custom normals speckled under shape keys).
- Smooth ear shells with painted inner forms (cut detail was lumpy at this density).

TypeSafe A/B (typesafe_ab_compare.py, both orders must agree), v2 vs n56:
- first PC render: n56 won nearly everything (v2 open-mouth artifacts 0.92).
- after Leo layout + n56 skin shading: neutral front/3/4/side - v2 wins overall, head_shape, eyes, eye_layout,
  nose_mouth; n56 wins profile_eye, ears, expression.
- side close-up: v2 wins profile_eye, eyes, ears, nose_mouth, upper_lip, head_shape.
- final (v2z) happy vs n56 happy: v2 wins eyes, nose_mouth, expression; n56 wins mouth_depth, upper_lip, ears (n56's
  happy is an open smile, v2's closed - not like for like).
App: e2e_head_pack --id head_mhs3_v2 E2E OK. check_pack: head-only fails as n56, WARN 80k triangles.
Known / not done: triangle budget; small white tooth ends at the corners of a wide-open mouth; no hair yet; a light
stripe on the back of the neck in side view; ID- keys only for the four sliders the e2e checks.
Boards: v2o_vs_n56_board.png, v2z_expressions_board.png, v2h_board.png, v2f_form_toon.png, v2_app_*.png.

## q23 (2026-10-16/17) - "too blocky, nothing like anime": reference-match loop vs MHS3 Leo
Sammy: "it looks too blocky and nothing like an anime or manga character. please keep iterating and use the
references from mhs3 as target look. remember to use typesafe".
- Softer form: jaw-line blend k 0.02 -> 0.05, rounder chin rows, smoother throat join (v3a).
- Leo's hair (n56 hair) fitted onto v2 for the boards (pc_v2.attach_hair) - MHS3 heads read through their hair.
- Reference-match judge (typesafe_visual_judge.py, menu blender/tools/visual_corrections/face_v2.json, analysis +
  pictures in docs/qa/head_v2/judge, D = pupil-to-chin framed to 300 px in both):
  - v3a: first_fix jaw_wider (both orders); every feature "off" except nose_mouth.
  - v3b, v3c: jaw_wider again (my outline measurement of Leo: 1.24 D at the mouth, ~1.2 D at 0.85 D).
  - v3c (jaw_wider excluded): ears_smaller_higher (both) -> applied (v3d): ears 0.01 -> 0.29.
  - v3e: lower face set to Leo's measured widths -> looked square. Picture A/B against the Leo front
    (typesafe_ab_compare.py): v3a beats v3c and v3e (overall, jaw_chin). Words and pictures disagreed: the outline
    measurement includes Leo's cheek shadow / sideburn area. Jaw reverted to v3a, ears kept (v3f).
  - v3f (jaw items excluded): face_rounder (both) -> applied (v3g); picture A/B v3f vs v3g: tie (no visible change).
  - v3g (menu + hair_fit_lower_wider, brows_lower_angled, iris_bigger): hair_fit_lower_wider (both) -> applied in
    pc_v2 (scale 0.90, 4 mm lower). Render v3h pending: Sammy's Blender stopped responding.
