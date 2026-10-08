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

# Eyes again (q-series): painted eye decal, then the judge loop -> n53 + look_knobs.json

Why: every earlier eye round left outline_shape "off", and the corner knobs had no effect because the shape came from
the head mesh's eye opening. Now the eye is painted into an RGBA texture on a decal laid on the skin
(blender/newhead/eye_paint.py); the old eye plate became skin (lit shade mask, face normals, a skirt tucked behind the
lid rim) so the opening disappears. The outline curves, iris, pupil, highlight, sclera band and lid line were measured
column by column from the MHS3 near eye (101 px wide) and colours sampled from it. Tuned values live in
blender/newhead/look_knobs.json (apply_look.py reads them). Menu: blender/tools/visual_corrections/eyes_paint.json.

| round | TypeSafe pick (agreed) | off | needs a human |
|---|---|---|---|
| q1 | highlight_same_side | highlight, brow_position, brow_shape, brow_colour, eye_size | iris_pattern, eye_spacing |
| q2 | brow_higher | brow_position, brow_shape, brow_colour, eye_size | iris_pattern |
| q2b | brow_longer | brow_shape, brow_colour, eye_size, brow_position | iris_pattern, eye_spacing |
| q3 | brow_longer | brow_shape, brow_colour, eye_size | iris_pattern, brow_position, eye_spacing |
| q4 | brow_longer | brow_shape, brow_colour, eye_size | iris_pattern, brow_position |
| q5 | eye_bigger | brow_shape, brow_colour, eye_size, brow_position | iris_pattern, eye_spacing |
| q6 | eye_bigger | brow_shape, brow_colour, eye_size, brow_position | iris_pattern |
| q7 | brow_taper_sooner | brow_shape, brow_colour, brow_position, eye_size | iris_pattern |
| q8 | brow_taper_sooner | brow_shape, brow_colour, brow_position, eye_size | iris_pattern |
| q9 | brow_inner_end_thicker | brow_shape, brow_colour, eye_size | brow_position, iris_pattern, eye_spacing |
| q10 | brow_inner_end_thicker | brow_shape, brow_colour, brow_position, eye_size | iris_pattern |
| q11 | brow_longer | brow_colour, brow_shape, eye_size | brow_position, iris_pattern, eye_spacing |
| q12 | brow_longer | brow_colour, brow_shape | eye_size, iris_pattern, brow_position |
| q13 | eye_bigger | brow_colour | eye_size, brow_shape, brow_position, iris_pattern |
| q14 | eyes_further_apart | brow_colour, brow_shape, brow_position | iris_pattern, eye_spacing, eye_size |
| q15 | eyes_further_apart | brow_colour, brow_shape, brow_position | iris_pattern, eye_spacing, eye_size |
| q16 | brow_inner_end_thicker | brow_colour, brow_shape, brow_position | iris_pattern, eye_size, height_to_width |
| q17 | brow_darker | brow_colour | brow_position, brow_shape, iris_pattern, eye_size, height_to_width |
| q18 | brow_less_orange | brow_colour | brow_shape, brow_position, iris_pattern, eye_size, height_to_width |
| q19 | brow_straighter | - | brow_shape, brow_position, iris_pattern, brow_colour, eye_size, height_to_width |
| q21 | brow_thicker | - | iris_pattern, brow_shape, eye_size, brow_position, height_to_width, brow_colour |

Notes:
- q1: outline_shape, height_to_width, iris size/colour, pupil, sclera, both lid lines and flatness all judged "matches"
  on the first painted round.
- q2 brow_higher was not applied: the q2 brow row had been eyeballed; measured, the brow-lid gap already matched
  (0.15 vs 0.14 eye heights). brow_higher was excluded from then on, and the analyses use measure_eye numbers.
- Brows q2b-q19 (mesh strip): longer x5, taper sooner x2, heavier inner end x3, darker, less orange, straighter.
  Each step matched the measurement at two points, but by q20 the strip had become a tall wedge that folded over at
  the inner end (a diamond hole in the face render). q21 replaced it: the brow is painted in the same decal from the
  traced MHS3 brow edges (with the mauve shadow under the inner end and diagonal brush strokes).
- Eyes: bigger x3 (EYE_W2 0.092 -> 0.110; width / eye-centre-to-nose-bottom 0.61 -> 0.71, reference 0.77), further
  apart x2 (EYE_DX 0.012; gap 1.05 eye widths), highlight on the viewer's left in both eyes.
- Stopped at q21: every feature "matches" or "needs a human". Its pick (brow_thicker) was not applied: mid-brow
  thickness already measures the same as the reference (0.13); only the inner end is thinner (0.11 vs 0.25 eye widths
  with shadow, front view vs the reference's 3/4).
Needs a human: iris arcs (ours thinner/fainter), eye size (0.71 vs 0.77), brow inner end, brow colour.
Boards: eyes_q0.png (before), eyes_q1.png, eyes_q15.png, eyes_q21.png, face_q20.png (brow fold), face_q21.png,
eye_paint_cmp.png (painted eye + brow vs the reference crop), eye_paint_n53.png (the texture).

## r1 - animatable eyes and brows (rig, replaces the painted decal by default)

Sammy asked for eyes and brows that animate in the character creator (blink, amazed, sad...), smooth round lines
instead of polygonal ones, the brown line running down the outer corner, and thicker iris arcs.

Build (`EYE_RIG = 1` in apply_look.py; `EYE_RIG = 0` keeps the q21 decal path):
- `eye_shape.py`: the MHS3 eye/brow outlines as densely resampled, Gaussian-smoothed curves (no polygon chords) plus the
  expression offsets. The head's eye opening is cut to this contour in the cage (build_head `EYE_SHAPE`), n56.
- `face_rig.py`: per side an eye-white plate 2 mm behind the face, an iris disc (texture with highlight, `eye_tex.py`,
  arcs `RING_W` 0.042 = about twice the q-series), a lid-line ribbon with a wing down the outer corner, a brow strip
  with hatch texture and the mauve shade strip.
- Shape keys (glTF morph targets): head + lid strips `PF-Blink_L/R, PF-EyeWide, PF-EyeSad, PF-EyeAngry, PF-EyeHappy`;
  iris `PF-LookLeft/Right/Up/Down, PF-IrisSmall`; brows `PF-BrowUp/Down/Angry/Sad`. Presets in `expressions.json`
  (neutral, blink, wink_left, amazed, sad, angry, happy).
- `eye_lit`: skin moved by the lid keys blends to flat lit skin so rotated custom normals do not leave shadow specks.

Checks: dataset bands - nothing outside. Temples within 0.17 mm of n53. Skin skew p95 50.8 (was 38 on n53/n55):
an honest regression from cutting the curved opening into the cage; not hidden.

Judge (menu eyes_rig): s3 picked low_rim_off (applied). s4 picked brow_thicker in both orders (ours thinner, so no
contradiction) - applied as BROW_THICK 1.12 (s5). After s4 every other feature was "needs a human": height_to_width
0.40, upper_lid_line 0.40, eye_size 0.44, brow_shape 0.52, brow_position 0.55, lower_lid_line 0.61, brow_colour 0.69
- the stop condition, so the loop ends here.
Boards: board_eyes_s5.png, board_expr_s5.png (all 7 expressions, front), board_expr34_s3.png, board_look_s5.png.
Shape / placement entries in eyes_rig.json need a head rebuild (build_head), not just apply_look.

## v-series - camera-angle view keys (anime cheat for off-front views)

Sammy: away from the front the eyes looked warped, not anime; anime redraws the face parts per angle. Before
(board_view_before.png): at 35 degrees the near eye stretched to 2.27x as wide as tall (front 1.74) and the far eye
shrank to 0.33 of the near eye with most of it hidden behind the nose; at 50 degrees only a sliver showed.
References at matching angles (docs/reference/mhs3 and docs/style_dataset): MHS3-09 ~30 deg (far eye 0.70 of the near,
same height, iris 0.83), MHS3-07 ~50 deg (far eye 0.34, at the face edge), ref-04 ~65-70 deg (profile almond about
2.1x, iris 0.42 of the eye, set back 0.5 eye heights). The head datasets (head-targets-dataset, eyes_dataset) hold
front-view proportions and topology only, nothing per angle; the view keys do not change the basis mesh, so the
dataset bands are unaffected.

Build (`blender/newhead/view_keys.py`, run by apply_look when `VIEW_KEYS = 1`): shape keys `VW-Yaw_L/R` (camera 35
degrees toward the character's left/right) and `VW-Side_L/R` (90 degrees) on the head and every eye part. For each
key the eye, iris and brow outlines get a target screen position (near eye evenly compressed about the iris, far eye
fitted between the nose bridge and the face edge, profile eye a narrow almond behind the brow ridge, irises kept
round); each vertex slides ALONG the face surface to the point the camera sees there (so nothing leaves the face),
keeping its layer offset. The skin around follows with a falloff that is made monotone per row (no folds), fades out
toward the temple and ear, and is lit-mixed where it moves (no toon specks). Line strips step 1.5 mm toward the key's
camera and the eye white / iris 3.5 mm away from it (invisible in that view) so the lids still cover them when an
expression key is added on top. App drive: `view_weights(yaw)` in view_keys.py (inbox item for Claude Code).

Judge (menu view.json, analyses visual_v14..v30_view.json, ours at 12/30/50/70 deg vs the references):
- applied: profile_eye_longer x3 (SIDE_C 0.50 -> 0.68), far_eye_toward_nose (FAR_GAP 0.10/0.12 -> 0.05/0.17),
  far_iris_narrower (IRIS_FAR 0.85 -> 0.77), far_eye_wider (-> 0.00/0.12), near_eye_narrower x2 (NEAR_C 0.95 -> 0.85).
- far_eye_toward_nose picked twice; the double step moved the eye 0.06 eye heights only (our nose line is drawn on
  one side of the nose, so the gap to it is partly the line's own offset) -> reverted to the single step, excluded
  with its opposite.
- declined (contradict a measured number): profile_eye_longer once ours reached 0.87 of the front proportion;
  far_eye_wider at 0.74 (ref 0.70) -> far_eye_narrower applied back to 0.66, then both excluded (oscillation);
  far_iris_wider/narrower oscillated -> excluded; profile_iris_narrower (applied, then the reference measured 0.42 vs
  ours 0.37 -> reverted); profile_eye_shorter, profile_eye_forward (gap measured equal), near_eye_narrower at 1.51 vs
  1.47.
- final (v30): matches - near_eye_shape 0.74, near_brow, far_eye_height; needs a human - far_iris, far_eye_width
  (0.73 vs 0.70), far_brow, near_iris; off - far_eye_position (nose-line gap 0.6 vs 0.25 eye heights, limited as
  above), line_quality (small notches on the lower white edge at 30-70 deg, a few tiny cheek shade dots, ragged far
  white with amazed/angry at 30 deg), profile_eye (ours 1.51x = 0.87 of front; TypeSafe keeps asking for changes the
  measurements contradict).
Boards: board_view_before.png, board_view_v30_sweep.png (0-90 deg), board_view_v30_refs.png, board_view_v30_mirror.png
(-30/-60 deg), board_view_v30_expressions.png (expressions at 30/60 deg), board_expr_v30_front.png (front unchanged).
