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
    pc_v2 (scale 0.90, 4 mm lower).
  - Blender froze / crashed twice on v3h: attach_hair iterated src.all_objects while linking copies (Blender 5.2
    crash in Collection_all_objects_next, from the crash log). Fixed with list(...); hair copies now render-only.
    PC calls now run in bpy.app.timers / threads so a long step never blocks the add-on.
  - v3h: picture A/B v3g vs v3h tie (hair kept). Judge: chin_wider_flatter (both).
  - v3i: menu setting (h 1.00 half width +0.04) had no visible effect (tip hidden by the neck join). v3j: chin rows
    h .90 +0.02, .95 +0.04 -> broad rounded chin. Judge lower_face_width 0.06 -> 0.47, jaw_chin 0.02 -> 0.08;
    A/B inconclusive (orders disagree), v3j cleaner in both. Judge: face_shadow_smaller (both).
  - v3k: menu setting (face push 2.5 -> 3.2) moved ~500 px; even 8.0 only ~1200. Far-cheek band narrowed with the
    analytic ellipsoid x radius instead (0.40 -> 0.50 H). cheek_and_face_planes 0.03 -> 0.12; A/B tie.
    Judge: brows_lower_angled (both).
  - v3l: brows 1 step (eyes 0.045 -> 0.075; asked again); v3m: 2 more steps (eyes 0.105). A/B: artifacts up -> a
    skin patch through the right brow (brow lift 0.32 mm vs crease 0.30 mm z-fight); brow lift -> 0.48 mm.
  - v3n: iris_bigger (radii x1.15): eyes 0.105 -> 0.205; A/B clean -> v3n (both orders).
  - v3o: outline_thicker (0.0009 -> 0.0016): outline 0.03 -> 0.11; A/B tie.
  - v3p: brows 1 more step (x4 total): brows now as close to the lash as Leo's at the same framing
    (eyes_vs board); judge still picks brows_lower_angled with faithful_p 0.36 -> excluded (lower would sit on the
    lid). Next pick: neck_thicker (both) -> v3q (NECK rx/ry +0.02).
  - v3q: neck_thicker -> neck still 0.01 (Leo's neck is under his collar; no geometry can match) - neck items dropped.
  - v3r: ears_smaller_higher again: ears 0.28 -> 0.33 but the A/B called v3q cleaner (artifacts 0.61 vs 0.71) and the
    ear vanished behind the hair (Leo's near ear shows) -> reverted.
  - v3s: face_flatter_front (NF +0.3 at h .45-.65): A/B v3s wins nose_mouth and clean (both orders) -> kept.
  - v3t: eyes_bigger (0.33 -> 0.36 D) on trial: picture A/B tie; Leo measures 0.32 D -> reverted (picture tie, the
    measurement decides).
  - Menu exhausted (every face_v2 item applied or rejected with a reason). Still "off": nose_and_mouth (mouth line breaks
    into dots at the ends), hair_framing (n56 Leo hair: many thin spikes vs Leo's few broad clumps), cheek planes, neck
    (collar). These need new menu items / fixes, not more of the same knobs.
  - Judge scores v3h -> v3s: lower_face_width 0.06 -> 0.49, eyes 0.05 -> 0.24, outline 0.02 -> 0.10, cheek planes
    0.03 -> 0.14, jaw/chin 0.02 -> 0.11, ears 0.34 -> 0.32, nose_mouth 0.18 -> 0.24.
  - Pack head_mhs3_v2 re-exported from v3s (same 36 meshes); e2e_head_pack E2E OK (board v3s_app_board.png, no hair in the
    head-only pack). Boards: hq_34 (v3h vs v3q 3/4), v3s vs Leo.

## q24 (2026-10-17) - "keep iterating" + VRoid as reference + hair as a tweakable shader
- VRoid Studio 2.10 on Sammy's PC studied (reference only, no VRoid meshes used): hair = groups of strands drawn on
  guide sheets around the head; per strand Width / Thickness ratio / Twist / Cross section / Curve, texture Highlight
  Position; Look tab = outline width per part, Rim light Intensity / Concentration, Shading Area / Hardness / Softness.
  Sample model downloads failed inside VRoid (connection), VRM export not done yet.
- Hair shader in the app (src/viewport/hairShader.ts, GLSL - the app is WebGL; HLSL port shaders/hair/AnimeHair.hlsl):
  shared uniforms, live sliders (Material tab > Hair shader). Head-space ring reads as one band across clumps.
- Face loop (menu +5 items: eye_opening_narrower, cheek_shadow_softer, nose_side_shadow, ear_inner_lines, mouth_shorter):
  - v3u: mouth line fix (lift 0.50 mm, min end thickness - ends rendered as dots): nose_mouth 0.24 -> 0.39; A/B tie.
  - v3v: cheek_shadow_softer: menu x2 invisible; SKIN_SOFT 0.03 in a v2 copy of the skin group: cheek planes 0.13 -> 0.60.
  - v3w: eye_opening_narrower (upper lid middle x0.85): A/B tie, closer to Leo by eye; eyes 0.27 -> 0.23 (noise).
  - v3x: ear_inner_lines (line x1.6, darker): ears 0.21 -> 0.37; A/B tie.
  - v3y: nose_side_shadow: A/B v3x wins nose_mouth + clean (both orders), judge 0.415 -> 0.285 -> reverted.
  - v3x judge first_fix: none (both orders). Pack head_mhs3_v2 re-exported from v3x (same 36 meshes); e2e E2E OK.

## q25 (2026-10-17) - "this version looks worse than the previous version, the v2"
- Sammy picked A (v2 face from d374f5f) over the Leo-matched v3x: "the face in general looked better, but the mouth and
  eyes needed a bit of work". Face scripts restored from d374f5f; his pick is the baseline (gate --prev), his taste
  overrides the Leo-matching judge. v4 fixes on top of A: LIFT respaced (z-fight mottling), second catchlight, mouth line
  thickness profile, an_w = 1 at the mouth seam (jaggies), mark_corner_bridges + corner taper (open-mouth fangs).

## q26 (2026-10-17) - books on anime/manga faces + TypeSafe image gate as the standard process
- Three books read for every head / face element and expression -> docs/reference/books/rules_*_face.json; each rule
  page-checked by TypeSafe against its own page (confirmed: actionanime 47/73, mangaguide13 68/85, crilley 64/110).
- Face gate (blender/tools/typesafe_face_gate.py, skill face-gate, CLAUDE.md, character-gate --face-gate): book rules
  per render with an applicability question, MHS3 look per element side by side, no regression vs the approved version.
- v4l: FAIL - 44 rule failures; expressions unreadable (0.01-0.09); every MHS3-look question ~0.2.
- v5a (book expression presets, neutral mouth 0.49 -> 0.41 D, inner lid fold): FAIL - 28 rule failures (44 -> 28);
  happy same_expression 0.79 but happy regressed vs v4l (prev in both orders); MHS3 look still ~0.2 everywhere.
  Gate bug found: missing reference images (mouth/ refs not on the PC) were skipped silently, so laugh / talk / angry were
  never compared -> now "not measured" and the gate is "unknown" at best; refs copied to the PC.
- v5b: brow keys x2.2 (angry / sad read neutral on the board), PF-Squeeze_L/R built (contract key, ^ joy arcs) for
  laugh / happy, contract blush_strength as a skin shader mask (resting 0.30, happy 0.55, laugh 0.75), neutral mouth
  0.35 D (one eye width), lid fold inner 40%, angry shows teeth. Blush is Blender-shader only so far: the app / pack
  needs the same mask in its skin shader before export.
- v5b gate: 24 rule failures; mg13_cheek_blush 0.17 -> 0.97, cr_expr_joy_closed_arcs 0.04 -> 0.83, laugh same_expression
  0.89, happy 0.81. Narrowing the cavity to 0.35 D made the open mouths boxy with hooked line ends.
- v5c: line ends trimmed (1.03 -> 1.0, smaller corner accents), first PF-Grimace (open jaw) -> angry read as talking (0.36).
- v5d: iris / pupil / highlights clamped to the lids instead of squashed between them (books: iris tucked under the lid).
- v5e/v5f: PF-Grimace rebuilt as a real grit - lips pulled apart with the jaw closed (new 'bare' term, jaw weights pick the
  lip), lower teeth raised to meet the upper, tongue dropped: angry same_expression 0.49 -> 0.79, angry beats v4l in both
  orders.
- v5f gate: FAIL - 25 rule failures (44 at v4l), 57 MHS3-look failures (laugh / talk / angry now measured), 1 regression:
  laugh, v4l preferred in both orders against Eleanor's open-eyed laugh (m02); the books and MHS3 m08 want closed ^ eyes,
  and v4l's laugh mouth is wider (0.41 D cavity). Sammy decides.
- TypeSafe noise measured on unchanged renders: mean |dp| 0.02, p90 0.05, max 0.12, 5-7 of 108 verdict flips per run, so
  21 vs 25 rule failures between v5d and v5f is noise (front render unchanged). Written into the face-gate skill.
- Still failing everywhere: MHS3 look ~0.2 per element (flat cel vs MHS3's painted shading / hair detail - a shading
  task, not a face-piece one). Open book items: surprise small irises (needs an iris key; PF-Surprise is a mouth alias in
  the contract), crying tears, adult lower-lip line, head layout rules (brow band, ear position) on the v2 skull.
- Board: docs/qa/head_v2/gate/boards/q26_v4l_vs_v5f.png

## q27 (2026-10-17) - "iterate until the model looks like the mhs3" (standing goal, CLAUDE.md + memory)
- Measured v5f vs Leo at equal D (pupil line to chin): eye / nose / mouth heights matched; brows 0.16 D above the pupil
  (Leo 0.08), ear bottom 0.48 D (Leo 0.38), chin a narrow V (Leo ~0.5 D rounded), neck wider than the chin.
- TypeSafe judge (face_mhs3.json menu, images): all 8 features off; first_fix face_side_shadow (both orders).
  Cause: board KeySun from the front-left, FillSun lighting the other side into the same toon diffuse, no shadows.
  pc_v2.mhs3_lights (render-only): key from the viewer's right / above / front (3 directions tried, k2 kept), fill 0,
  hair casts shadows; bake_fringe_shadow writes the MHS3 under-fringe band into the forced-shadow attribute 'shade'
  (ray cast toward a steep light, blurred, forehead / temples only).
- Head (sdf_head): jaw line gonion (0.075, 0.80) -> (0.05, 0.72) (long "boat" jaw in 3/4 / side); neck slimmer and
  forward with a softer join (notch, dented 0.57 -> 0.39-0.52); ears up and Leo-sized. Chin: dataset-median widths
  (v6c) read square ("dented" 0.33 -> 0.50, TypeSafe preferred v6b) -> kept v6b, just under dataset p10 at 0.85-0.95 H
  (deliberate MHS3-look deviation). A/B (same lighting) v6e vs v5f geometry: front B overall + ears, 3/4 B ears, side A.
- Face (face_paint): upper lid flatter, slanting down outward; brows lowered onto the lash (0.07 / 0.09 D);
  nose highlight a wedge on the lit side; a joined nose side shadow drew a hard dark wedge (dented 0.65) -> removed;
  resting blush 0.30 -> 0.12.
- Judge v6g vs Leo: still all off but up: brows 0.01 -> 0.22, chin/jaw 0.01 -> 0.19, ears 0.02 -> 0.14, eyes
  0.08 -> 0.12; first_fix hair_fuller. Scaling the n56 hair (1.12 / 1.20 tall) only stretched the thin spikes
  (artifacts 0.61 -> 0.82) -> off. The hair needs a rebuild as MHS3 chunky clumps.
- Face gate v6g: FAIL - 23 rule failures (v5f 25), 55 look failures, 0 regressions; front and laugh beat v5f in both
  orders; front same_style 0.23 -> 0.33.
- Board: docs/qa/head_v2/gate/boards/q27_v5f_vs_v6g.png
- Next (biggest gaps per TypeSafe): hair rebuild (chunky clumps, painted light planes), face shading quality (soft
  painted edges, rim), eye size 0.33 -> 0.31 D and iris detail, side-view jaw/neck shadow edge.

## q28 (2026-10-17) - "the head has some distorted parts and weird shapes all around. validate with a 3d model"
- Validation against real anime head meshes: 5 verified dataset heads (TexVerse, landmark-checked; 2 of 7 dropped,
  scale/pose mismatch) and our built head, normalised, rendered in plain clay (blender/tools/dataset_clay).
- Clay showed what the toon paint hid on v6g (and v5f): horizontal ripples over the whole skull (Pchip section
  interpolation kinks), a trough / ridge band across the face at eye level (brow + socket relief, NF 2.9-3.0 boxy
  sections), a stick nose ridge, the jaw plane slicing the back of the skull, a skull bottom flaring past the neck,
  a deep notch at the nape, crown too long (depth at 0.1 H 0.65 vs dataset 0.55-0.58), lower back too shallow
  (depth at 0.5 H 0.72 vs 0.81-0.97).
- sdf_head: loft Gaussian-smoothed along h (LOFT_SMOOTH 0.03), crown shortened, lower back fuller then tucked into
  the neck (B 0.27 -> 0.12-0.25 below the ears), jaw plane limited to the front of the jaw corner with a sloped
  underside behind it, eye-level sections rounder (NF 2.4-2.5), brow and socket relief off, lips softer, nose a
  small tip, neck re-seated. measure_v2: all dataset bands ok.
- TypeSafe A/B on clay (REF = dataset head d60fb442): new head wins overall, head_shape and clean in front, 3/4 and
  side (both orders); artifacts 0.91-0.94 -> 0.33-0.45, dented 0.48-0.58 -> 0.32-0.45; reads a little less adult
  (front 0.65 -> 0.58).
- Toon v7a vs v6g: side wins every aspect (dented 0.51 -> 0.32, artifacts 0.85 -> 0.53); front / 3/4 undecided
  (toon hides form). Face gate v7a: FAIL as before (24 rule failures, within noise of 23), 0 regressions.
- Board: docs/qa/head_v2/gate/boards/q28_clay_validation.png

## q29 (2026-10-17) - "keep validating and improving the model, it looks very amateur"
- Hair rebuilt on the v2 skull (pc_v2.build_fitted_hair): hair_nh.py run on a temporary copy of the v2 head scaled to
  the n56 size it is tuned for, clumps ray-fitted to that scalp, then mapped back (was the n56 hair moved and scaled
  onto v2). A/B vs the moved hair: undecided (both orders disagree).
- Style menu (face_mhs3_style.json), TypeSafe reference-match judge vs Leo after each step (feature scores words /
  pictures):
  - first_fix skin_soft_shadows: softer terminator + wider forced-shadow ramp (MASK_SOFT) - A/B undecided at two
    strengths, so not adopted (knobs stay available).
  - eyes (crops vs Leo showed my first iris change went the wrong way): grey-white sclera, deeper lid shadow, light
    muted iris with a darker upper half, thinner rim, inner ring + fine radial lines, thinner lash with an outward
    wing, narrower almond opening: eyes 0.01 / 0.07 -> 0.18 / 0.205.
  - hair_painted_streaks: thin pale streaks along the clumps (a first try drew diagonal zebra hatching) + a soft lighter
    third tone: hair 0.045 / 0.105 -> 0.21 / 0.23.
  - brows_brush_strokes: solid lower stroke + dense feathered hair strokes (a first try read as a comb), stern slant:
    brows 0.02 / 0.11 -> 0.37 / 0.26.
  - Lowest now: skin_shading 0.02 / 0.06; outline 0.13 / 0.22.
- The A/B tool kept answering "disagree" on small eye changes (position bias); absolute judge scores were used instead.
- Face gate v7k vs v7a: front, 3/4, laugh, talk better in both orders, 0 regressions; front same_style 0.34 -> 0.43;
  look failures 56 -> 50; rule failures 27 (24, within noise). Still FAIL.
- Board: docs/qa/head_v2/gate/boards/q29_style.png

## q30 (2026-10-17) - "this looks horrible ... fix the head shape ... ears ... eyes look egyptian ... mouth too thin"
- Head driven by the measured dimensions of 5 dataset heads (v8b within about +-0.02 H of the medians at most
  heights); smaller, closer ears; lash ends at the eye corner; mouth 1.7x thicker, 0.40 D wide; neck set back under
  the skull. Blender was disconnected, so these were checked on clay and dims only (board q30_clay_shape).

## q31 (2026-10-17) - "you can even use the reference as a base model and rework it so it looks like mhs3"
- Base: dataset head "Autumn Girl" by Aryzus (CC BY 4.0, credit in docs/reference/ATTRIBUTION.md), re-proportioned to
  the dataset medians and resampled to an SDF grid (blender/head_v3/base_head.py -> base_grid_d60.npz, 3.6 MB).
- Hybrid (sdf_head.sdf_hybrid, on by default; HEAD_BASE= empty gives the procedural head): face front and ears from
  the base; skull, back of the head, jaw sides and neck from our measured head (the base's back was cut flat, 0.08 H
  short of the median); our smooth front closes the base's eye sockets; face front 6% less forward.
- Measured on the renders (D = pupil to chin): face width at the mouth 1.12 D (Leo 0.97), 0.81 D at 0.8 D (Leo 0.69)
  -> lower face narrowed (x 0.90 from h 0.58 to 0.78) = h6. This puts chin widths under the dataset band
  (width 0.85-0.95 LOW): the MHS3 match and the dataset bands disagree here; flagged, not hidden.
- TypeSafe A/B (both orders must agree), q31/*.json:
  - h6 vs v8b (old procedural): h6 wins overall in front, 3/4 and side; head_shape and ears in all three; clean in
    front; artifacts 0.82 -> 0.57 (front). v8b still wins nose_mouth in front.
  - h6 vs h5 (before narrowing): h6 wins overall, nose_mouth and clean in front and 3/4.
  - h7 (base nose half replaced by our small nose): lost to h6 -> reverted.
  - h8/h9 (base ear moved down x1.3 and re-seated, for the book rule "ear from eyelid to nose bottom"): the ear/cheek
    crease drew a jagged outline; lost to h6 in every view (artifacts 0.39 -> 0.87) -> off (BASE_BLEND ear_seat_mode).
- Face gate h6 vs v8b: both FAIL, 21 rule failures each, MHS3-look failures 50 vs 51, same laugh regression vs v4l.
  New for h6: ear position rules (mg13_ear_eyelid_to_nose, cr_ear_position) and cr_profile_face_line; cleared:
  aa_highlight_protruding, mg13_median_matches_contour, cr_lash_lines_tilt_center.
- Boards: q31/board_v8b_h6.png, board_h5_h6.png, board_h6_h8.png, clay_h5.png.

## q32 (2026-10-17) - "analyze the images ... it still looks bad ... doesnt even look like anime"
- New measuring tools: pupil_align_board.py (our render scaled/moved so the pupils land on the reference's pupils,
  side by side + overlay + eye and nose/mouth crops), pupil_align_widths.py (face widths at matched heights in
  pupil-distance units), typesafe_anime_check.py (does it read as anime / MHS3 / polished, and which element breaks it;
  the MHS3 refs are run through it as the ceiling), typesafe_defects.py + visual_corrections/defects_face_shape.json
  (yes/no defect statements, with Leia/Eleanor-vs-Leo as controls).
- Pupil-aligned vs Leo (IPD units): eye width 0.46 vs 0.44, opening 0.21 vs 0.26, mouth 0.54 vs 0.67 wide at the same
  height, nose tip / mouth heights within 0.03, face width close at cheek/jaw, chin 0.66 vs 0.81 at 1.2 IPD.
- Tried and measured (all TypeSafe A/B vs h6, both orders): taller eye opening + fuller iris + no spokes + sparkles +
  lash hook; nose wedge highlight + wing tip; mouth 0.48 D; broader chin; Leo-sampled skin / shadow tint; key light
  rotations; narrower face; volume smoothing; fuller neck; side hair dropped; thinner outline; softer fringe shadow.
  h6 won overall in front, 3/4 and side against every combination (p3, p4, p4s4) -> all defaults back to h6; the
  knobs stay (SHADOW_TINT, SKIN_COLOR, HAIR_DROP, face_sx, chin_back, VOL_SMOOTH; paint changes reverted).
- typesafe_anime_check (yes-probability): h6 anime 0.91, MHS3 match 0.63, polished 0.28. MHS3 Leia / Eleanor: 0.96 /
  0.90 / 0.87-0.90. Every variant tried tonight sat at anime 0.88-0.92, MHS3 0.57-0.65, polished 0.20-0.28: tuning
  this pipeline (SDF head + flat-colour decal pieces + n56 toon shader + blade hair) does not move the polish gap.
  Culprits named: face shape, outline, eyes, hair (3/4).
- Sammy chose to lift the no-VRoid rule ("Allow VRoid-standard base"). Five male VRoid exports (Sketchfab CC BY,
  TexVerse) downloaded with his OK to datasets_work/vroid_male (credits in docs/reference/ATTRIBUTION.md). All share the
  VRoid face mesh and UVs; the Sketchfab GLBs have no shape keys (expressions to rebuild).
- typesafe_anime_check, unlit (raw textures): anime 0.88-0.92, face shape 0.92-0.93, but MHS3 0.05-0.17, polished
  0.09-0.22 (culprit skin shading). With a toon set-up (blender/head_vroid/vroid_toon.py: texture lit / Leo-ratio
  shadow tint, outline, MHS3 key light): 3f8f0119 front anime 0.93, face 0.92, MHS3 0.57, **polished 0.50** (h6 0.28),
  3/4 0.46. Swapping 0fe1676a's face + iris onto it: polished 0.25 (worse, reverted). Warm skin tint + green iris by
  hue shift: 0.43 / 0.34 (noise). Ellipsoid-blended face normals: 0.37 (cleaner, flatter). Smoothed-proxy normals:
  blotchy (dropped). Ramp softness / light angle: 0.37-0.40, culprit still skin shading.
- Board: q32/board_vroid_base.png. Next: MHS3 painted skin details on the VRoid face (nose highlight, cheek warmth,
  painted shadow shapes), MHS3 eye/brow paint, hair highlight streaks, head pose, expressions rebuilt, export.

## q33 (2026-10-17) - "tweak them ... resemble mhs3 ... a bit of realism ... facial features must not look like vroid"
- blender/head_vroid/mhs3_paint.py repaints the VRoid face textures in their own UV layouts (any VRoid export takes them):
  MHS3 iris painted by 3D position (VRoid's iris art is pre-distorted; a UV circle rendered as a keyhole), grey sclera,
  smooth heavy upper lash with a short outer turn (no VRoid flicks/dots), lid crease, solid stern brushed brows (a
  hatch pattern scored brows_hatch 0.88), VRoid bandage and mouth line erased, wider darker mouth line, lower-lip
  shade, nose = pale wedge on the lit side + soft shape under the tip, warm skin baked in.
- blender/head_vroid/mhs3_reshape.py warps every mesh with one field (seams stay closed): longer lower face (nose 0.49 ->
  0.62, mouth 0.76 -> 0.86, chin 1.30 -> 1.42 IPD below the pupils, Leo-measured), identity through the eyes, broader
  jaw/chin, higher nose bridge, smaller eye region, rounder lower / more arched upper lid, brows lowered 18.5 mm.
- Caught by close-up renders / UV overlays: the depth remap stretched the iris x1.27 (tall pupil), lid offsets moved the
  iris, the brow mesh's lower UV row is tiny in 3D (brow drawn in the top row only rendered as a sliver).
- TypeSafe defect probe vs Leo (defects_vroid_mhs3.json; Leia control in brackets), VRoid toon -> m15:
  too_anime 0.84 -> 0.68 (0.58), nose_mhs3 0.46 -> 0.72 (0.40), mouth_mhs3 0.41 -> 0.72 (0.69), skin 0.53 -> 0.64
  (0.81), face_adult 0.38 -> 0.46 (0.55); still high: vroid_look 0.74 -> 0.84 (0.43), eyes_vroid 0.89 (0.58),
  artifacts 0.92-0.94 (0.59); eyes_mhs3 0.24-0.30 (0.57). Anime check: polished 0.50 (toon VRoid) -> 0.31, MHS3 0.57
  -> 0.52; culprit skin shading on every lighting / normal / ramp variant tried (best: original normals, hard ramp,
  MHS3 0.625, polished 0.37, but it shows a blotch under the eye).
- Board: q33/board_vroid_mhs3_m15.png, q33/aligned_m15_vs_leo.png, q33/eye_close_m15.png.

## q34 (2026-10-18) - "make it resemble mhs3 a bit more ... a bit of realism" / "eyes must be a bit bigger ... look almost evil"
- Realism pass kept: cheeks in, broader squarer chin (pupil-aligned chin 0.74 -> Leo 0.81 IPD), chin forward in
  profile, thicker neck, higher nose bridge, painted nostrils, upper-lid socket shade, faint philtrum, cheekbone shade.
  TypeSafe too_anime 0.69 -> 0.57-0.61, brows_mhs3 0.35 -> 0.45.
- Smaller / hooded eyes (m18-m20) read as a glare (Sammy: "almost evil") -> m21: eyes 4% bigger than base, open lids,
  only slightly shorter sideways. eyes_mhs3 0.21 -> 0.33 (best so far), too_anime 0.66.
- VRoid Studio face sliders read on the PC (docs/reference/vroid_face_sliders.md): the head is a default; every face
  part must be slider-editable in the creator like VRoid.

## q35 (2026-10-18) - "eyes too elongated (egyptian) ... mouth too thin ... shading rubbery ... nose too thin"
- Eyes: outer half pulled in harder (eye_sx_out 0.80), taller opening (eye_sz 1.06), lash ends at the corner with no
  hook/tail (book rule from q30), iris 12% larger so less white shows each side.
- Mouth: crisp painted line (hard edge, 0.016 IPD half-width mid, tapering, ends curving down), VRoid's pink interior /
  tongue darkened so the seam reads as part of the line, clear soft lower-lip shape + faint upper lip.
- Nose: widened 45% (bridge to wings) in geometry, crisp MHS3 nose base shape under the tip.
- Shading: VRoid's baked skin gradients flattened (MHS3 skin is flat colour + clean shapes), face normals 95% toward a
  smooth ellipsoid, hard two-tone ramp (0.285-0.315), key light (0.55,-0.75,0.40). Cheekbone / philtrum blobs removed.
- TypeSafe anime check: shading_anime 0.55 (m21) -> 0.735 (m25), MHS3 0.55 -> 0.57; defects: mouth_mhs3 0.69,
  nose_mhs3 0.74, skin 0.60.

## q36 - MHS3 rulebook, master loop, profile fix, eye-shape standard (m27-m46)
Sammy: "the side view shows that the face features are too forward ... make skills and rules ... a master rule ...
validation is always strictly necessary ... extremely strict". Mid-way: "The eye shape is not matching the mhs3 one,
please make them match, this is also a standard."
- Rulebook `knowledge/mhs3_face_rules.json`: 47 measured rules (profile P1-P8, proportions F1-F6, face outline R5-R9,
  eyes R1-R4/E1-E7, eye shape ES1-ES2 with a Leo outline template, mouth M1-M2, shader S1-S8) + TypeSafe sets with
  thresholds calibrated on real MHS3 faces (Leia, Eleanor judged the same way: a threshold MHS3 cannot meet is not a
  standard) + lessons. Skills: `mhs3-rulebook`, `mhs3-shader-match`, `mhs3-master-loop` (master rule, also in
  CLAUDE.md). Tools: `mhs3_measure.py` (mesh, per region), `mhs3_render_measure.py` (render vs Leo, same code),
  `mhs3_validate.py` (one verdict, exit 0/12/13), `mhs3_fit_profile.py`, `mhs3_fit_eyes.py` + `mhs3_eye_proxy.py`,
  `mhs3_warp_np.py`. New MHS3 profile reference: `docs/reference/mhs3/profile/face_profile_04.png`.
- Profile: m26 failed 10 profile rules - the nose sat 0.07 H ahead of the forehead (dataset median 0.053,
  MHS3-04 0.039 at brow level). nose_back 6 mm + nose-root lift in the band above the pupils; lower face shortened
  (MAP chin 1.42 -> 1.38: Leo pupils-to-chin 1.347 IPD). TypeSafe features_forward 0.41 -> 0.38 (passes 0.45).
- Eye shape: VRoid's opening was tilted (outer corner 0.27 of the width higher). eye_tilt + lid knobs fitted to the
  Leo template (pattern search on a mesh proxy, bias-corrected from the render): tilt 0.27 -> 0.05, outline RMS
  0.046 -> 0.024 (tol 0.03). Lash on the iris (was floating 1 mm: eyeline_sz/eyeline_dz), Leo-sized dark-green pupil,
  darker iris with lid shadow, thicker lower-set brows, crease row moved onto the visible strip.
- Face: square adult jaw (0.98 D at 0.80 D), cheeks via a full-depth cheek table, head side behind the jaw pulled in,
  ears lifted (squashing made them pointed), thinner neck, mouth 0.43 D.
- Shader: three skin tones like Leo (warm cel shadow 0.80, deep core tone along the jaw), light near-frontal (shadow
  area 16% like Leo), cast shadows off (EEVEE shadow noise made grey speckled patches - TypeSafe artifacts 0.93 -> 0.70).
- m46 verdict: all 47 measured mesh/render rules pass (rms 0.47 of tolerance). TypeSafe still fails 17 calibrated
  thresholds: polished 0.28 (MHS3 0.84-0.90), mhs3 0.47 (0.88), eyes_vroid 0.90 (<=0.61), vroid_look 0.86 (<=0.48),
  nose_pointed 0.82 / nose_long 0.72 in profile, skin 0.56, white_big 0.80, crease_missing 0.69; culprits hair, eyes.
  Board q36/board_m46_vs_m26_mhs3.png, eyes q36/eyes_m46_vs_leo.png, report q36/validate_m46.json.

## q36b - "you made it look worse": A/B regression gate, rebuilt from m26 (m47-m49)
Sammy: "you made it look worse... are you really validating or hallucinating?" Asked afterwards, TypeSafe agreed:
m26 vs m46 A/B preferred m26's side and 3/4 head shape; mhs3 0.56 -> 0.48, shading 0.71 -> 0.58. Cause: the
measured rules were single-view targets (front widths, Leo's face length, a frontal-light shader) and passing all of
them was reported as success without comparing to the version Sammy had accepted.
- New hard gate `blender/tools/mhs3_ab_gate.py` (rulebook `pass.regression_gate`, master-loop step 6b): TypeSafe A/B
  with pictures, both orders, front + 3/4 + side, + anime check; FAIL if any view gives overall/head_shape to the
  accepted version or mhs3/face_anime/shading/polished drop > 0.02; PASS needs one overall win and no loss.
- Screened (all vs m26): m47a_o (q36 profile + eyes, short face) FAIL side; m47a_c / m47b_c (crisp cast shadows)
  FAIL front/3/4/side; m47b_o FAIL side; m48_2/m48_3 (no root lift) FAIL side; m48_4 FAIL side + shading;
  m49a (nose_back 5 mm) PASS once, FAIL once (side) - not stable; **m48_1 PASS twice** (front overall win, no loss;
  mhs3 0.565 -> 0.66 / 0.55 -> 0.695, polished 0.23 -> 0.39, face_anime and shading equal).
- m48_1 = m26 shape + shader, with the eye-shape standard (level corners, Leo outline), lash on the iris, Leo pupil and
  iris, lower brows, softer profile fix (nose back 4 mm + root lift 2.5 mm), ears lifted 4 mm. Knobs
  `blender/head_vroid/knobs/m48_1_reshape.json`, paint `m46_paint.json`.
- Rulebook: the m26 shader is the locked spec again (MHS3_SPEC); rules the accepted version contradicts are marked
  advisory with the reason (front jaw/cheek/ear widths, face length, the 3-tone shader rules, eye/brow/mouth
  detectors tuned under the frontal light) - not loosened, to be re-derived before they block. Still failing,
  marginally: profile P2/P3/P5 (err 1.0-1.3): the stronger profile that passes them does not reliably beat m26 in
  the side A/B - Sammy's call. Board q36/board_m48_1_vs_m26.png, gates q36/gates/.
