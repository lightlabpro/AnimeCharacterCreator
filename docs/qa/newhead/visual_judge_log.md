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

## e-series - eye edges and expressions (face_rig.py, eye_shape.py, view_keys.py)
- Skin band between the lid line and the eye white (worst in amazed) was the inner wall of the lid rim facing the
  camera: `_tuck_rim` folds the rim rings under the lid loop (RIM_OUT/RIM_IN) and the lid keys carry the folded rim.
- Blink notch: the lid ribbon doubled back along the closed curve; `lid_ribbon` now keeps the neutral sample split
  between the upper lid and the wing for every key and collapses the wing for the blink (samples 100 -> 160).
- Dark tick at the outer corner in blink was the outline shell: `_no_outline_where_keys_move` (OutlineWeight 0 on
  skin any lid key moves, plus one ring).
- Barbs/broken blink lines at 30-60 deg (lid key + view key): COLUMN mode - eye/iris/brow parts take one horizontal
  shift per column computed at a reference row. Left: small tails at the ends of the blink line at angles.
- Expression audit (blender/tools/typesafe_expr_audit.py, pictures): calibrated on the MHS3 eye itself (clean 0.25,
  iris 0.15 for the reference) - read scores against the reference (vs_ref); lid_line was flagged for amazed/sad.

## s-series - face shading
- s1 PIXEL_NORMAL: the head normal field evaluated per pixel (an_w weight); s2/s3 the ears keep their own normals.
- s4 the blurry terminator at the temple / back of the skull was the toon softness (0.012 brightness units) over a
  slowly changing smooth normal, not a cast shadow (visible_shadow test identical): head-only group copy with
  Softness 0.002 (SKIN_SOFT). Edges crisp in the 0-90 deg sweep.

## TypeSafe v2 (jev-1.14.0)
Judge sends the pictures (danger-zone images) next to the words: analysis_faithful + look_<feature> check the
analysis against the pictures; Box tool (typesafe_box.py) is a measuring aid only (MHS3 eyes boxed 40-50 px off,
refined confidence 0.09-0.25); the API needs >= 280 px per side.

## n-series - nose, mouth, ears (apply_look.py; mesh unchanged, so the dataset bands are unaffected)
Reference crops: ref_nosemouth.png, ref_ear.png (MHS3 frame). Measured in pupil distances (IPD).
- n1 nose: one curved stroke (NOSE_STYLE 2) thin in the middle, heavy hooked end running into a painted shadow lens
  under the tip (NOSE_SHADE; 0.25 x 0.08 IPD, toon shadow colour + NOSE_TINT mauve) - replaces the straight line, the
  "v" nostril tick and the hard vertex-mask rectangle. Line moved to the -x side (NOSE_SIDE -1) to match the
  reference (face turned to the viewer's left: line on the far side, lens toward the near side).
- n1 under-lip: a shadow lens (LIP_STYLE 2, 0.33 IPD wide) instead of a thin dark line.
- n1 strokes skip the view-key remap (VIEW SKIP): the column remap made the line jagged and pulled it off the nose
  at 20-35 deg. They get their own keys instead (stroke_view_keys): toward the line's side its top retracts to
  EYE_Z-0.07 so it does not cross the far eye (which the eye view key slides toward the nose). A mirror key was tried
  and dropped (the blend swept the strokes through the nose at 20 deg).
- n2 ears: the 24-spoke shells drew a polygonal rim/outline; they now render from their own object NEW_Ears_<tag>
  (Mask on the shared mesh + Subdivision 2 + outline), so the asset mesh keeps its topology and every index/key.
- n3 ear paint from ear-plane coordinates (PCA of each shell): mauve crescent bowl (EAR_BOWL_E minus EAR_LIT_E,
  EAR_TINT 1, tint edge at the toon shadow threshold) and a thin C line along its front-top edge (ear_f/ear_lw
  iso-band) - replaces the thick back slash and the oval blob.
TypeSafe (menus nose_mouth.json / ears.json updated, images on):
- n7 nose: picked nose_line_join_tip (the line already joins the tip: declined, excluded) then nose_line_start_higher
  (applied for the front view; at 3/4 it crossed the far eye, hence the retract key).
- n5 ears: ear_outline_close_top (tried EAR_TOP_LINE 0.6 on the upper root: no visible change - off, excluded);
  n10: ear_bowl_bigger (applied, +0.06 radii); n13: ear_bowl_edge_smoother (already applied at n9: stale pick).
- n13 nose: nose_bigger (geometry, build_head NOSE_GAIN, needs a mesh rebuild + band check: NOT applied yet; our
  nose bottom is 0.65 IPD under the pupils vs 0.69 in the reference, so it is consistent with the measurement).
- final words/pictures: ears - ear_shape 0.90 and ear_light 0.84 match; inner_line 0.61 / inner_shadow 0.47 need a
  human (from 0.53 / 0.16); ear_outline 0.18 off (gap at the top front remains). Nose/mouth - nose_line 0.34 (from
  0.20), nose_shadow 0.20, under_lip 0.17 off (reference has a darker top edge and a pinker tone); mouth_line 0.01 is
  not comparable (the reference mouth is open).
Boards: board_n13_face_sweep.png (-35..90 deg), board_n13_expressions.png, board_n13_nose_ear.png.

## p-series - face proportions from the official MHS3 renders (id_morphs.py, eye_shape.py, face_rig.py)
New references (docs/reference/mhs3/MHST3-*_Render_*.webp; Leo front render = main face reference). Measured in
D = pupil line to chin bottom (independent of skull and hair), Leo render and the game frame agree:
eye width 0.32-0.34 D, pupil distance 0.70-0.73 D, mouth 0.64 D below the pupils and 0.49 D wide, nose bottom
0.49 D, chin flat (~0.37 D wide). n56 measured eye width 0.43 D and pupil distance 0.82 D, a pointed chin.
- bake (all shape keys mapped through the same map, mesh topology unchanged): eyes x0.80 wide / x0.92 tall about
  their centres, eye centres x0.89 from the centre line, brows move with the eyes and are re-fitted to the skin,
  chin front +0.045 H spread (neck excluded), ears 8 deg further out; short falloff past the outer eye corner so
  the cheek silhouette at 20-35 deg does not dent (p2 did). Bands: all inside; topology quad_aspect_p95 3.16 -> 5.10
  (stretched quads past the outer eye corner; flat-shaded, not visible).
- lashes: drawn thickness profile LASH_IN/MID/OUT 0.22/0.55/0.85 x LID_TH (thin over the eye ~0.025 pupil distances,
  ~0.04 at the outer corner), the inner tip fades in (no upward tick), slimmer wing (WING 0.12, WING_TH 0.085), the
  lower-edge cover reaches the corner. The opening geometry is unchanged (base_curves keeps LID_TH).
- brows: irregular hair strokes (BROW_STROKES 2), thickness taper to 0.55 at the outer end, inner end lower
  (BROW_INNER_DROP 0.13), short warm under-brow shade (no pink band).
- nose: no dark line in the front view (zero width, grows in with the yaw / side keys), pale bridge highlight.
- ID- keys for the creator on every mesh they move: ID-EyeSize/Spacing/Height(_Neg), ID-MouthWidth/Height(_Neg),
  ID-JawWidth/ChinWidth/ChinLength(_Neg), ID-EarSize(_Neg), ID-EarOut, ID-LashThick/Thin/Long/Short,
  ID-BrowThick/Thin/Long/Short (slider sheet board_p11_id_sliders.png). set_expression only touches PF- keys now.
- app: lash.thickness slider (ID-LashThick / ID-LashThin), contract re-exported, typecheck + 50 tests pass.
TypeSafe (menu face_p.json, pictures on): p8 picked nose_line_off (applied; agrees with the render); p9: eye_size
0.71, eye_spacing 0.76, lash_line 0.81 match; brows 0.60, mouth 0.42, nose 0.42 (from 0.06), jaw_chin 0.31 need a
human; ears 0.29 off; pick brows_more_angled (applied, agrees with the render).

## h-series - hair started (hair_nh.py)
Clump hair fitted to the baked scalp: lens-section tubes along skull-hugging paths, cap shell, NG_ToonHair,
pieces Hair_Front_leo (SOC-HairFront) / Hair_Back_leo (SOC-HairBack) + Hair_Cap_leo, keys ID-HairVolume /
ID-HairWidth / ID-HairLength (+_Neg). Iterations h1 (flat helmet, comb stripes) -> h4 (volume, big fringe clumps,
covered crown, narrower sides) -> h6 (denser top, lighter colour).
TypeSafe h4 (menu hair.json): silhouette 0.11 and colour 0.11 off, clumps 0.35, sides_back 0.49, fringe 0.55 need
a human; pick hair_lighter (applied as LIGHTNESS 1.6: median sRGB 113 -> 130 red, reference 155). Still off by
measurement: hair half width 0.96 D vs 0.80, rounded mushroom outline vs the reference's jagged spiky one, too few
light strokes. This is a first draft of the hair, not a match.

## k-series - hair rebuilt (hair_nh.py k2-k31)
Rebuilt the cut from the Leo render: flat leaf-shaped blade clumps on slerp paths from the crown, a fringe sheet,
side locks, two rows of pointed back layers, an under layer in shadow; toon shading reuses the head's toon group
(hair copy NG_ToonSkin_NewHead_Hair) with painted rim lines and highlight strokes.
Bugs found on the way:
- k5/k6: every clump rendered in toon shadow - faces were wound inward (shaded as back faces; found with a normals
  render). Outward winding, no cast shadows from the hair.
- k13/k14: dark wedges in every fringe clump - the rim-line mask used sin(pi k/RING), so a whole side of each ring
  was "rim". Now sin(2 pi k/RING), thin thresholds, the tip point excluded.
- k20: the fringe hung over the eyes as separate spikes: p 100 is pupil level on this skull and FRINGE_LEN ran the
  tips further. Fringe rebuilt as a wide overlapping sheet swept from his right to his left, longest point just
  above the upper lid (k31 measured ~0.06 D above the pupils; Leo ~0.08 D), FRINGE_LEN back to 1.03.
- k23: the fringe arced ~4 cm off the forehead in profile; centre lift 0.040 -> 0.024.
- k26 -> k27: a flat x-split shadow side gave a seam at the back and a black profile; now the shadow side follows a
  painted light (front-top, from image left) by direction from the skull centre, tips stay lit. k28: hair-only
  shadow tint (0.50,0.42,0.40) - the skin tint made the hair shadow orange-red; now deep brown ~(110,75,50).
- k29/k30: thin strands over each fringe clump and a few flyaways over the top (k29's were too long and stuck out
  sideways like whiskers; shortened).
Measured (front, D = pupil line to chin): top 1.63 D incl. the two spikes (mass ~1.45; Leo 1.52 incl. strands),
half width above the ears 0.90 D (Leo 0.80; k19 was 1.02 - our skull is 0.75 D wide at the temples, so the hair
can only lie ~4 mm off it), lit colour (160,122,84) vs (152,112,80).
TypeSafe (jev-1.14, pictures on, honest descriptions incl. the misses):
| round | silhouette | clumps | colour | fringe | sides | faithful | first_fix |
|---|---|---|---|---|---|---|---|
| k17 | 0.145 | 0.15 | 0.15 | 0.235 | 0.825 | 0.315 | narrower_sides (applied structurally) |
| k25 | 0.05 | 0.04 | 0.045 | 0.18 | 0.235 | 0.66 | clumps_narrower (applied: WID_SCALE 0.88 + fine strands) |
| k28 | 0.055 | 0.04 | 0.19 | 0.185 | 0.685 | 0.615 | clumps_narrower (applied as fine strands k29) |
| k30 | 0.175 | 0.07 | 0.20 | 0.225 | 0.725 | 0.515 | fringe_longer (applied as FRINGE_LEN 1.03, not +0.06: measured tip 0.12 D vs Leo 0.08) |
| k31 | 0.195 | 0.085 | 0.215 | 0.235 | 0.725 | 0.445 | fringe_longer - declined: measured tip now 0.06 D, already at/below Leo's |
Note: k17's descriptions were not faithful to the pictures (0.315); k17's p_same values are therefore weaker than
the later rows. Still off: clumps (Leo's are many fine strands; ours a dozen big blades + strands), width 0.90 vs
0.80 D, top outline smoother than Leo's. Sides match. The hair is much closer but TypeSafe still calls four of five
features off - this is not a match yet.

## m-series - modular hair (hair_nh.py RECIPES)
Research (modular anime hair kits: front / back / side / ponytail / extras; Braidify / Braid Hair Curves; MHS3
creator Front + Back + two-tone) -> hair built per region (Front, Top, SideL, SideR, Back, Base) plus attachments
(tail, braid, bun, ahoge, tie, bow), each its own object with ID-HairVolume/Width/Length. Leo rebuilt as a recipe
(renders match k31). Demo recipes ponytail / twintails / braids / bun / leia (board m1_grid.png, m5_leia.png).
TypeSafe m4 (Leia, pictures): faithful 0.80, all features off (silhouette 0.015, sidelocks 0.02, clumps 0.02, fringe
0.035, ponytail 0.035); smoother_top applied (m5). Parked at Sammy's request to fix the head first.

## q-series - head form, MHS3 eyes, brows, ears (2026-10-15)
- Head "pushed in" (Sammy): the p-series eye bake dented the brow and cheek cross-sections ~1 cm beside each eye
  (face_study setback at 0.30 hh: brow 0.146 -> 0.212, cheek 0.161 -> 0.228; dataset band 0.12-0.19, n = 7 verified
  anime heads). q1 skin slides on the pre-bake surface (brow 0.147, cheek 0.157); q1b fixed jaw artifacts from the
  first slide; q1c orbit fill (eye-level setback 0.215 -> 0.169). Slices: slices_q1_brow_eye_cheek.png, slices3.png.
- Brows: inner end thinner (BROW_TAPER_IN 0.55, thickest at 0.35 of the length); new keys ID-BrowInnerThick/Thin and
  the creator slider "Brow inner end" (brow.thickness already existed).
- Eyes from the Leo reference (sRGB samples): near-white sclera, tall oval iris (RX 0.46, RY 0.62), dark top, lighter
  lower crescent, tall pupil set high, arcs only on the highlight side, cross sparkles, highlight on the viewer's right.
- TypeSafe (menu face_q.json, pictures on):
| round | eye_size | eye_spacing | sclera | iris | brows | ears | shading | jaw_chin | faithful | first_fix |
|---|---|---|---|---|---|---|---|---|---|---|
| q4 | 0.84 | 0.675 | 0.38 | 0.195 | 0.28 | - | - | 0.145 | 0.31 | chin_wider (applied) |
| q5 | 0.825 | 0.715 | 0.405 | 0.24 | 0.105 | 0.02 | - | 0.275 | 0.285 | brows_inner_thicker - DECLINED (Sammy: inner part too thick) |
| q5b | 0.74 | 0.79 | 0.805 | 0.485 | 0.10 | 0.01 | - | 0.14 | 0.24 | ears_closer (applied, EAR_OUT 8 -> 2 deg) |
| q6 (with hair) | 0.76 | 0.79 | 0.79 | 0.455 | 0.11 | 0.585 | 0.02 | 0.155 | 0.30 | hair_shadow_on_forehead (applied: hair_cast) |
| q7 | 0.73 | 0.82 | 0.76 | 0.48 | 0.105 | 0.585 | 0.115 | 0.17 | 0.255 | brows_more_angled (applied, BROW_INNER_DROP 0.18; little visible change) |
TypeSafe says "pictures disagree" with the descriptions (faithful 0.24-0.31) in every face round, even after plain
rewrites; a bald test head against Leo with hair kept it low. Eye size, spacing and sclera match; iris, ears need a
human; brows, jaw/chin, nose/mouth and shading are still off. Not near-perfect yet.
| q9 | 0.735 | 0.83 | 0.765 | 0.485 | 0.12 | 0.62 | 0.115 | 0.175 | 0.175 | nose_line_off (already off; excluded) |
| q10 | 0.74 | 0.825 | 0.755 | 0.505 | 0.11 | 0.59 | 0.11 | 0.15 | 0.235 | chin_wider (agreed again; applied CHIN_WIDE_BAKE 0.065) |
q8-q10 changes: brows darker (Leo median 108,80,62 / strokes 70,50,38) and more angled (BROW_INNER_DROP 0.30);
nose and under-lip shadows painted in Leo's sampled pink-brown (206,148,124 / 200,145,116), lip shadow wider.
Per-feature faithfulness check (typesafe_faithful_check.py, q7): every sentence 0.46-0.89 - no single description is
contradicted; the global "pictures disagree" verdict (0.17-0.31) stays low regardless. Plateau: eye size, spacing and
sclera match; iris, ears, lash line "need a human"; brows (Sammy's thin inner end vs Leo's thick one), jaw/chin,
nose/mouth and shading stay "off". Final boards: head_before_after_q11.png. Face form after q11: setback at 0.30 hh
brow 0.147, eye 0.169, cheek 0.157 (band 0.10-0.19).

## q12 - A/B regression check after Sammy: "the head looks worse now ... a step back" (2026-10-15)
New tool `blender/tools/typesafe_ab_compare.py`: TypeSafe sees two renders of the same head (same camera, light) plus
the Leo reference (front + 3/4 pair) and picks the better one per aspect; asked twice with the pictures swapped and
the options reversed, a winner counts only when both orders agree. Each variant = q11 with ONE change rolled back
(scripts copied to `_ab/<variant>/`, same npz), bald, front + 3/4.
| B vs A = q11 | overall | head_shape | eyes | brows | nose_mouth | jaw_chin | ears | clean | dented A/B | artifacts A/B |
|---|---|---|---|---|---|---|---|---|---|---|
| morning (73fe301) | B | B | ? | B | B | B | ? | B | 0.48/0.46 | 0.88/0.73 |
| skin slide + orbit fill off | B | B | B | B | B | B | ? | B | 0.56/0.38 | 0.92/0.65 |
| chin 0.065 -> 0.045 | = | = | = | = | ? | = | = | ? | 0.44/0.45 | 0.70/0.73 |
| ears 2 -> 8 deg | ? | = | = | = | = | = | ? | ? | - | - |
| q10 nose/lip shading off | B | = | = | = | ? | = | = | ? | - | - |
| q8 brow drop/colour off | B | = | = | ? | ? | = | = | ? | - | - |
| combo (all three B rows) | B | B | B | B | B | B | ? | B | 0.52/0.39 | 0.92/0.64 |
(? = the two orders disagree, = = tie.) Combo vs morning: nose_mouth B, clean B, the rest tie/disagree. With the Leo
hair (q11h vs q12h): brows B, jaw_chin B, the rest disagree. ORBIT_FILL without the slide changes < 0.02 % of pixels.
Cause: the skin slide moved the brow-ridge skin under the brow decals, so at 3/4 the near brow was clipped, a brow
piece floated off the outer end and stray marks appeared in the side view - the very "pushed in" look it was meant to
fix. Applied (q12): SKIN_SLIDE 0, LIP_SHADOW 1.0 / W 0.33 / toon colours, BROW_INNER_DROP 0.13, brow colours 122,95,71
/ 92,66,45. Kept: q3 MHS3 eyes, thin inner brow + slider, chin 0.065, ears 2 deg (A/B ties).
Band conflict, stated openly: without the slide the face_study setback at 0.30 hh is brow 0.212 / cheek 0.228, above
the 0.10-0.19 band of the 7 verified dataset heads. The pictures (Sammy + TypeSafe both orders) prefer it anyway; the
band is from 7 heads and its 0.30 hh slice crosses the eye socket. The band is not widened and the model is not bent
to it - a fix that meets both must move the brow decals with the skin (next).
Boards: q12_ab_single_reverts.png, q12_ab_form.png, head_q11_vs_q12.png.

## q13 - forehead, eyes at 3/4 / side, ears; mesh analysed without shading (2026-10-15)
Sammy: "the head shape still looks a bit deformed on the forehead, the eyes look off, especially on the 3/4 and side
views. The ears look horrible." Then: remove the X marks on the iris; analyse the mesh without shading.
New session helpers: `formshots` (Workbench studio light on a copy with the custom normals cleared - the real form)
and `wireshots` / `wire_view` (flat grey faces + wireframe, eye parts flat-coloured, optionally with the view keys).
- Forehead: the plain renders showed vertical ridges at the temples running up into the forehead and lumps on the
  cheeks; the unbaked mesh had none. Cause: the identity bake's eye map moves skin in x/z with a box weight whose
  edges are steep, and the skin keeps its depth while sliding over the curved forehead. Fix: `BAKE_SMOOTH` relaxes
  the eye map's displacement field (Laplacian on the displacement, lid rim pinned, 60 iterations), the chin map is
  applied after it unchanged; painted strokes get the same correction from the nearest skin.
- Eyes: iris X marks off. View-key knobs: PUSH 0.003 / PUSH_BACK 0.006 (the outer-corner "comb" at 60 deg and the
  highlight outside the opening are gone), WING 0.06 (shorter lid wing). SIDE_C: 0.56 won the eye close-ups
  (eyes/clean/overall, both orders) but lost "eyes" at face scale; kept at 0.68.
- Ears: `ear_mhs3.py` - new ear from the Leo render (outline traced off ref_leo_ear_hr, helix roll, upper crescent,
  antihelix, "?"-shaped concha, tragus, lobe; lit normals; stand-off over the skull per vertex with a rounded
  front-view profile). Design plot: ear_mhs3_design.png.
TypeSafe A/B (typesafe_ab_compare.py, both orders, Leo reference pair; sanity check q12 vs q12 = tie on all 8):
| comparison | result |
|---|---|
| mesh without shading, q12 vs q13 (front, 3/4, side) | q13 wins overall, head_shape, ears, clean; dented 0.60 -> 0.31, artifacts 0.81 -> 0.46 |
| mesh without shading, q12 vs q12 + relax only | relax wins head_shape, clean |
| ear close-ups (side, back 3/4, front), old vs new ear, ear reference | new ear wins "ears" |
| eye close-ups 35/60/90 deg, SIDE_C 0.68 vs 0.56 | 0.56 wins eyes, clean, overall |
| toon at face scale (front, 3/4, side), q12 vs q13 | ears: q13; eyes, brows: tie; jaw: split; overall, head_shape, nose_mouth, clean: q12 |
Honest reading: the geometry (plain-shaded and wireframe) is clearly better and the new ears win, but in the toon
renders at face scale TypeSafe still prefers q12 overall. Leave-one-out and add-one-in tests found no single change
that loses on its own (each tie/split), so the remaining preference is spread over small differences in the toon
paint (cheek and temple shadow shapes after the relax). Next: re-tune the toon shadow mask on the relaxed surface,
the jaw/neck fold (visible in the wireframe, present before q13), then re-run the A/B.
Boards: head_q12_vs_q13.png; results docs/qa/newhead/q13_ab/.

## q14 - 3/4 eye placement, ears round 2, facial expressions per element (2026-10-15)
Sammy: "The ears are looking much better, but still need work. The 3/4 eyes positioning also needs a bit of work.
You can start on facial expressions as well ... each element is separate."
- 3/4 eyes: measured on Leo's 3/4 frame (ref_face) in near-eye widths: gap between the eyes 1.21 (ours 0.94 at
  25 deg), far eye / near eye 0.79 (0.75), skin between the far eye and the nose line ~0.23 (0). New view-key knob
  NEAR_SHIFT (near eye and brow move toward the ear) = 0.4, FAR_GAP_IN 0.2, FAR_GAP_OUT 0.04. TypeSafe A/B could not
  separate the variants (eye_layout: the two orders disagree on 0 / 0.3 / 0.5), so the choice rests on the measurement
  and the board (q14_board.png row 1).
- Ears round 2: bigger "?"-shaped concha with its tail to the front notch, wider crescent under the top rim; a thin line
  along the inner rim was tried and removed (TypeSafe A/B: artifacts 0.74 vs 0.43). New ear vs previous: ear_shape tie.
- Expressions: mouth_rig.py (six mouth pieces with 12 keys), PF-NoseSneer, per-side brow keys (BrowRaise, BrowLower,
  BrowInnerUp), 17 presets. Eye white / iris moved 1.5 mm behind the skin (partial lid keys showed them under the
  lower lid; reduced, not gone). New check `typesafe_expr_check.py`: TypeSafe names the expression of each render,
  asked in both label orders; recognised = both orders pick the intended label.
| round | recognised | mean p_clear | change |
|---|---|---|---|
| expr3 | 3/13 | 0.39 | first mouth keys; TypeSafe read the neutral face and most presets as "angry" |
| expr4 | 5/13 | 0.46 | inner brows lifted in every non-angry preset, stronger BrowSad |
| expr5 | 7/13 | 0.59 | worried slope (inner end above the outer), bigger smirk / pout, one-sided brow lower |
| expr6 | 7/13 | 0.59 | key names aligned with src/model/performance.ts (same shapes) |
Recognised: smile, happy, amazed, sad, angry, shout, determined. Near misses: laugh -> happy, worried -> sad (p_clear
0.78), pout -> sad, blink -> angry (p_clear 0.91: eyes clearly closed; the stern default brows decide the label).
Neutral itself reads "angry": the default brows slope down toward the nose (identity look, BROW_INNER_DROP) - left as
Sammy tuned it; the creator's brow sliders soften it. Open: partial lid-key artifacts, far brow clipping at 3/4 with
the inner-up keys, no jaw drop with the open mouth yet.
Boards: q14_board.png, q14_expression_sheet.png; check results q14_expression_check.json.

## q15 (2026-10-15) - lower face, teeth and mouth, open items; section-by-section judging
Sammy: "check the lower part shape of the face, it looks a bit off, also check the teeth and general shape of face
elements and expressions ... subdivide face into sections for analysis and comparison with references."
- New `typesafe_section_judge.py`: both images cut into the same sections from four landmarks (face centre, eye line,
  mouth line, chin; boxes in units of eye-to-chin D) - brows, eyes, nose, mouth, jaw_chin, lower_face; per section a
  yes/no "looks like the reference" (p_same) and the biggest difference from a per-section menu, asked in both option
  orders (counted only when they agree). Repeat runs on unchanged sections move p_same by about +-0.03, so smaller
  differences are noise.
- Lower face: an outline overlay on Leo at the same landmarks showed ours ~0.13 D per side wider at nose height,
  ~0.08 at the mouth, the same at the chin; the section judge kept asking for a "rounder chin" and a "more curved jaw
  line". Tried: uniform jaw x scale (j1 0.88 / j2 0.82: j2 gave a V chin, p_same jaw_chin 0.375), a cheek-to-jaw taper
  (t1/t2 cut a ledge at nose height; t3/t4 with long fades), a rounder chin alone (r1/r2), and the taper with a
  rounder chin (c1). TypeSafe A/B could not separate any of them (overall / head_shape / jaw_chin: tie or the orders
  disagree; section p_same within noise), so the choice rests on the overlay: c1 follows Leo's face edge from the
  cheek to the chin (JAW_TAPER 0.14, CHIN_WIDE_BAKE 0.065 -> 0.045). A fold under the jaw angle (already in the
  un-baked mesh) drew a stray toon line at 3/4 and side: Taubin smoothing of the jaw/neck ring (JAW_NECK_SMOOTH 40).
- Teeth / mouth: white spikes at the teeth band ends (hard cut at |u| 0.8 -> smooth taper), jagged tongue and teeth
  edges (the mouth layers took per-point skin hits that jumped between the lip groove and the lip; now one smoothed
  depth field for every layer and wider layer offsets), shout was a flat lens (squarer, taller PF-VisWide). New
  PF-JawOpen (chin drop on the head + matching painted opening).
- Open items: the skeptical preset lost both irises at 3/4 - the look key pushed the iris back along the curved eye and
  the 3/4 view key bulges the white's inner half; the iris ended up 1.7 mm (35 deg) / 2.7 mm (60 deg) behind the white.
  Look keys keep 20 % of the push-back and come 3.5 mm forward at a full side look: occluded iris samples 56/59 ->
  0-2/59 (all looks, 0/+-35/60 deg). The far brow at 3/4 ends at the face edge like Leo's (not clipped).
- Expressions (13 labels as q14): recognised 7/13, mean p_clear 0.59 -> 0.63. happy needed JawOpen 0.35 (the taller
  teeth made it read "smile" in one order) and determined SmileClosed 0.3; tried and dropped: a skeptical without the
  lowered brow (p_clear 0.05), a worried without BrowSad/EyeSad (one order "worried", p_clear lower).
- Final, q14 -> q15 (section p_same, front / 3/4): mean 0.322 -> 0.335 / 0.344 -> 0.360 (within noise); A/B front+3/4
  pair: clean -> q15 (both orders), dented 0.435 -> 0.38, artifacts 0.715 -> 0.67, other aspects tie / disagree.
  Still asked for, not changed: brows "more angled down toward the nose" (Sammy's identity setting), nose "wider
  shadow under the tip" (a 25 % wider shadow did not move it: p_same 0.10 -> 0.10), eyes "taller / flatter opening"
  (orders disagree).
Boards: q15_board.png, q15_lower_face.png, q15_mouth.png, q15_expression_sheet.png, q15_expression_sheet_34.png;
check results q15_expression_check.json, sec_q15_front.json, sec_q15_34.json.

## q16 (2026-10-15) - ears, pout, teeth at 3/4, 3/4 expressions
Sammy: "The ears look too big (the creator will tweak size and shape), the pout expression can be reworked, the teeth on
the 3/4 ... look like buckteeth, and ... in 3/4 [happy, laugh, amazed, shout, pout, talk_a/o/e] look not that great."
- Ears: at 3/4 ours were 0.59 eye-to-chin units tall vs Leo 0.49; `EAR_H_SCALE` 1.06 -> 0.90 (ID-EarSize keys unchanged
  for the creator). Front+3/4 A/B q15 vs q16: clean -> q16 (both orders), artifacts 0.745 -> 0.66; ears / overall: the
  orders disagree.
- Teeth: band 0.013 -> 0.009 H, capped at 30 % of the opening (was 45 %), rounded ends - a thin strip under the lip line
  instead of a tall slab. Halving the layer offsets to cut 3/4 parallax brought the jagged tongue edge back, so they
  stay.
- Shout: S profile 0.3 -> 0.45 (the far end read as a box at 3/4). talk_a (PF-VisAA) wider 0.86 -> 0.98 (section judge
  at 3/4 against Leo's talking mouth: "wider").
- Happy eyes: lower lid rises 0.32 -> 0.42 (thinner smiling crescent).
- Mouth placement at 3/4: tried VW-Yaw keys on the mouth pieces shifting them 3-4 mm toward the far cheek (Leo's far /
  near mouth halves 45 / 65 px from the nose tip, ours 35 / 75), with the depth re-read from the skin. TypeSafe 3/4
  recognition fell (determined 0.725 -> 0.43, happy 0.62 -> 0.59), so the shift is off (`MOUTH_YAW_SHIFT = 0`).
- Pout: TypeSafe never picked "pout" for the old preset (sad / worried). Tried closed mouths with a lower-lip arc (p1-p3),
  four brow / eye sets, an arched mouth with a raised lip shadow: all read "neutral" (p_clear 0.27-0.52). Chosen: the
  small pucker (old shape) + a raised, fuller lip shadow + sulky eyes (Frown 0.5, EyeAngry 0.3, LookLeft 0.4, inner brows
  up 0.5): front "pout" in one order (first time), p_clear 0.58.
- Recognition (13 labels): 3/4 7/13, mean p_clear 0.665 (q15) -> 0.660; front 7/13, 0.632 -> 0.627 - unchanged within
  noise; pout front sad/sad -> pout/neutral. Per-expression 3/4 A/B q15 vs q16 ("expression", "nose_mouth", "clean"):
  ties or the orders disagree for all eight, so the teeth / shout / talk changes rest on the renders, not on TypeSafe.
- Tooling: `typesafe_expr_check.py` takes `label@variant=image` and `--labels` (score variants against a fixed label
  set); `session.py` persists `sec` and the landmarks. A headless Blender build (bpy 5.0.1 in the cloud with a stub
  NG_ToonSkin) reproduces the strokes and geometry for previews when Blender is closed (no TypeSafe there: the key is
  only on the PC).
Boards: q16_board.png, q16_mouth_34.png (q15 row / q16 row / pout + talk_e + happy), q16_expression_sheet.png,
q16_expression_sheet_34.png; checks q16_expression_check_34.json, q16_expression_check_front.json.

## q17 (2026-10-15) - mouth matched to MHS3 references; head exported into the creator
Sammy: "The mouth needs a lot of work. Find references from mhs3 and try to match the mouth on them ... upload the model
to the tool ... make sure the elements are separated so the tool can tweak them precisely."
- References: Sammy supplied MHS3 frames with open mouths; six square face crops with landmarks are in
  docs/reference/mhs3/mouth/ (README). New judge section `mouth_open` in typesafe_section_judge.py (opening shape,
  teeth band, interior, tongue, outline, corners, lower-lip shade). Pairs judged: happy / shout vs Eleanor's open
  laugh (m02) and the kid's smile (m07), laugh vs the closed-eye laugh (m08), talk_a / talk_e at 3/4 vs Eleanor talking
  at 3/4 (m01, m03).
- What the references share and ours lacked: a flat top edge and a deep round bowl (ours: a crescent with upturned,
  tapered corners), no dark line along the bottom edge, a thinner top line when open, a brown-maroon interior
  (96,56,56 sRGB) and a salmon tongue (210,115,95), a thin teeth band, talking mouths open as a real lens.
- Rounds (mean p_same of the six pairs): q16 0.191; d1/d2 profile + flat top 0.218 / 0.228; e1/e2 superellipse
  0.212 / 0.206 (flat-bottomed boxes); f1/f2 deeper ellipse 0.255 / 0.265; g1/g2 sine-spaced samples + bigger tongue
  0.282 / 0.279; h1/h2 bowl profile (D 0.95-1.2) 0.289 / 0.297; i1 (D open 0.080 width 0.90, tongue cap 0.36) 0.309;
  final 0.300. TypeSafe kept naming "rounder bottom edge" as the biggest remaining difference in every pair.
- A/B against the MHS3 crops (both orders), q16 vs q17: "expression" -> q17 for happy, laugh, shout and talk_e;
  "nose_mouth" orders disagree; "clean" tie.
- The flat top made the shout read "happy" (shout front happy/determined, p_clear 0.56 -> 0.28): the shout (S shape)
  keeps its downturned corners -> shout/shout again (0.445 front, 0.58 3/4).
- Recognition (13 labels): front 7/13, mean p_clear 0.627 -> 0.636; 3/4 7/13, 0.660 -> 0.672. happy 0.65 -> 0.76,
  laugh 0.38 -> 0.58 (still read as "happy"); amazed 0.74 -> 0.60.
- Creator: `export_head_pack.py` writes library/humanoid/bodies/adult/head_mhs3_n56 (23 meshes: CHR_Head, CHR_Ears and
  every face element per side, each with its own ID-/PF- keys; flat-colour "_emiss" materials for the painted parts,
  lit skin; DEF-Head + 10 SOC- sockets; VW- keys left out; app-name aliases PF-BrowRaise/Lower/Furrow, PF-Squint,
  PF-LidUpperDown, PF-VisSmall/Mid/IH/OO, PF-Surprise). check_pack: 2 FAIL by design (height / origin: a head is not a
  full body), orphan-key warnings for keys the app does not drive yet. New scripts/e2e_head_pack.cjs in the real app
  (headless): import, apply as body, 23 element meshes, 4 identity sliders and 5 performance keys move the right
  element, face captures: E2E OK. The skin's bent Blender normals drew pink shadow blotches in the app: the export
  clears them (smooth normals) -> clean toon shading (q17_app_head.png).
Boards: q17_mouth_refs.png, q17_app_head.png, q17_expression_sheet.png, q17_expression_sheet_34.png.
