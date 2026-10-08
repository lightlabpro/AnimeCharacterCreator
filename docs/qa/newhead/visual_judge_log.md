# Reference-match judge: first run (eyes, n47 -> n49e)

| round | analysis | TypeSafe first fix (both orders) | applied | effect |
|---|---|---|---|---|
| n47 | usable 0.95 | eye_rounder_corners | yes | no visible change |
| n48 | usable 0.95 | eye_rounder_corners | yes, double step | no visible change (head grid limits the corner shape) -> excluded |
| n49 | usable 0.94 | upper_lid_line_even | yes | outer wedge thinner (upper_lid_line 0.02 -> 0.07) |
| n49b | usable 0.94 | eye_taller / upper_lid_line_even split; tie-break upper_lid_line_even | yes | even line, short wrap (0.07 -> 0.48) |
| n49c | usable 0.94 | lower_lid_line_full (tie-break) | yes | full lower line (0.03 -> 0.54) |
| n49d | usable 0.95 | eye_taller | no: Claude's height/spacing/iris rows were eyeballed; measured, they match | analysis corrected |
| n49e | usable 0.94 | brow_arch | yes | brow arched |

After n49e: matches = pupil, flatness, height_to_width, eye_spacing; needs a human = brow colour, iris colour,
iris pattern, lower/upper lid lines; off = outline_shape, brow_shape, brow_position, iris_size (ours larger),
highlight, sclera. Boards: eyes_n47c.png ... eyes_n49e.png.

# Whole-head pass (eyes r1-r4, nose/mouth f0-f8, face f9-g12, ears e1-e6) -> mesh n53

Every round: Claude wrote `visual_<round>_<region>.json` from the board, TypeSafe (jev-1.13.0) judged it against
`blender/tools/visual_corrections/<region>.json`; one agreed step was applied, re-rendered, bands re-checked.

| round | analysis | TypeSafe pick (both orders agree) | still off | matches |
|---|---|---|---|---|
| e1_ears | usable | ear_lit | inner_line, concha, ear_lighting, rim_highlight, shape_ratio | size_position, outline |
| e2_ears | usable | ear_lit | inner_line, concha, ear_lighting, rim_highlight, shape_ratio | size_position, outline |
| e3_ears | usable | add_ear_inner_line | inner_line, rim_highlight, concha, shape_ratio, ear_lighting | outline, size_position |
| e4_ears | usable | ear_inner_line_thicker | inner_line, rim_highlight, concha, shape_ratio, stand_off | size_position, outline |
| e5_ears | usable | ear_narrower | inner_line, rim_highlight, concha, ear_lighting, shape_ratio, stand_off | outline, size_position |
| e6_ears | usable | split: concha_mauve / ear_narrower | inner_line, rim_highlight, stand_off, concha, ear_lighting | outline, size_position |
| f0_nose_mouth | usable | add_mouth_line | nose_bridge, mouth_line, nose_tip, under_lip | nose_height |
| f1_nose_mouth | usable | mouth_line_wider | nose_bridge, mouth_line, nose_tip, under_lip | nose_height |
| f2_nose_mouth | usable | add_nose_line | nose_bridge, mouth_line, nose_tip, under_lip | nose_height |
| f3_nose_mouth | usable | mouth_line_wider | mouth_line, nose_tip, nose_bridge, under_lip | nose_height |
| f4_nose_mouth | usable | mouth_line_wider | mouth_line, nose_tip, nose_bridge, under_lip | nose_height |
| f4b_nose_mouth | usable | mouth_line_wider | mouth_line, nose_tip, nose_bridge, under_lip | nose_height |
| f5_nose_mouth | usable | nose_line_to_shadow_side | mouth_line, nose_tip, under_lip, nose_bridge | nose_height |
| f6_nose_mouth | usable | nose_line_join_tip | mouth_line, nose_tip, under_lip, nose_bridge | nose_height |
| f7_nose_mouth | usable | add_nostril | mouth_line, nose_tip, under_lip | nose_height |
| f8_nose_mouth | usable | add_lip_shadow | mouth_line | nose_height |
| f9_face | usable | chin_narrower | jaw_and_chin, chin_width, face_shadow, outline | skin_colour, nose_profile |
| g1_face | usable | face_shadow_smaller | face_shadow, outline, jaw_and_chin, chin_width | nose_profile, skin_colour |
| g2_face | usable | face_shadow_smaller | outline, face_shadow, jaw_and_chin, chin_width | nose_profile, skin_colour |
| g3_face | usable | face_shadow_smaller | face_shadow, outline, jaw_and_chin, chin_width | nose_profile, skin_colour |
| g3b_face | usable | face_shadow_smaller | outline, face_shadow, chin_width, jaw_and_chin | skin_colour, nose_profile |
| g4_face | usable | chin_narrower | outline, chin_width, jaw_and_chin | nose_profile, skin_colour |
| g5_face | usable | outline_thicker | outline | skin_colour, nose_profile |
| g6_face | usable | face_shadow_smaller | outline | skin_colour, nose_profile |
| g7_face | usable | face_shadow_smaller | face_shadow, outline | skin_colour, nose_profile |
| g8_face | usable | chin_lit | face_shadow, outline | nose_profile, skin_colour |
| g9_face | usable | chin_lit | face_shadow, outline | skin_colour, nose_profile |
| g10_face | usable | outline_darker | face_shadow, outline | skin_colour, nose_profile |
| g11_face | usable | chin_narrower | face_shadow | skin_colour, nose_profile |
| g12_face | usable | chin_wider | face_shadow | nose_profile, skin_colour |
| n48_eyes | usable | eye_rounder_corners | outline_shape, upper_lid_line, lower_lid_line, brow_shape, brow_position, eye_spacing, highlight, sclera, iris_colour, brow_colour, iris_size | flatness, pupil |
| n49b_eyes | usable | upper_lid_line_even | outline_shape, lower_lid_line, upper_lid_line, brow_shape, brow_position, eye_spacing, highlight, sclera, height_to_width, brow_colour, iris_colour | pupil, flatness |
| n49c_eyes | usable | lower_lid_line_full | outline_shape, lower_lid_line, brow_shape, brow_position, eye_spacing, highlight, sclera, height_to_width, brow_colour | pupil, flatness |
| n49d_eyes | usable | eye_taller | outline_shape, brow_shape, brow_position, eye_spacing, highlight, sclera, height_to_width | pupil, flatness |
| n49f_eyes | usable | brow_lower | brow_position, outline_shape, iris_size, brow_shape, highlight, sclera | height_to_width, eye_spacing, pupil, flatness |
| r1_eyes | usable | brow_lower | outline_shape, brow_position, iris_size, highlight, brow_shape | height_to_width, eye_spacing, pupil, flatness |
| r2_eyes | usable | iris_smaller | outline_shape, iris_size, highlight, brow_shape | height_to_width, eye_spacing, pupil, flatness |
| r3_eyes | usable | upper_lid_line_even | outline_shape, highlight | height_to_width, eye_spacing, pupil, flatness |
| r4_eyes | usable | split: sclera_greyer / lower_lid_line_full | outline_shape, highlight, brow_shape, sclera | height_to_width, eye_spacing, pupil, flatness |

What was applied and what was not:
- Eyes r1-r4: brow_lower x2, iris_smaller, upper_lid_line_even. r4 split (sclera_greyer / lower_lid_line_full) -> stopped.
- Nose/mouth f0-f8: mouth line added (width 1.6 after three widenings; the MHS3 frame has an open mouth, so the
  mouth row can't match a closed mouth - noted in the analysis, mouth_line_wider excluded after f4b), nose line moved
  to the shadow side and joined to the tip, nostril, lip shadow.
- Face f9-g12: chin_narrower x2 (CHIN_TAPER 0.16), face_shadow_smaller x4 (FACE_FORWARD 2.5), outline_thicker
  (OUTLINE_W 0.0015), outline_darker (OUTLINE_DARK 1.5). g7/g8: face_shadow_smaller chosen a 5th time; the double step
  (FACE_FORWARD 3.3) changed under 1% of pixels -> reverted and excluded with its opposite. The patch it was aimed at
  was the forced jaw-underside shadow on the down-facing chin front; a new menu entry chin_lit (CHIN_LIT 1.0) removed
  it (face_shadow p_same 0.02 -> 0.20). The first chin_lit version only moved the normal blend (no effect) and was
  corrected to reach the shade mask. g11 chin_narrower (CHIN_TAPER 0.24) pushed width@0.85 below the dataset band
  -> reverted and excluded. g12 chin_wider declined: measured chin width is 0.27 of face width vs 0.25 in the
  reference, so wider moves away; chin_width is "needs a human". Face pass stopped.
- Ears e1-e6 (new menu ears.json, new knobs EAR_LIT / EAR_LINE / EAR_TINT / EAR_BOWL in apply_look.py and
  EAR_W / EAR_FLARE_DEG in ears_nh.py, an ear_line attribute saved in the npz): ear_lit x2 (ear normals turned toward
  the lit side; e3 first version used a box mask that also lit the skull - limited to the ear shells), inner helix
  line added and thickened (the band was too thin on the coarse ear grid to show; widened in ears_nh.py), ear_narrower
  (EAR_W 0.52, mesh n53; bands pass). e6 split (concha_mauve / ear_narrower, tie-break split too) -> stopped.

Deterministic checks on n53: dataset bands - none outside; quads only (5700 head faces), skin skew p95 38.1,
ear skew p95 32.8. Still off after the pass (TypeSafe): eyes outline_shape (head-grid limited), highlight, brow_shape,
sclera; face_shadow (3/4 shadow edge is stepped); ears inner_line (no run over the top), rim_highlight, concha colour
(warm brown, reference mauve), stand_off. Needs a human: chin width / jaw, ear lighting balance.
Boards: eyes_r4.png, face_f8.png, face_g7/g9/g11/final.png, ear_e1/final.png, look_final.png.
