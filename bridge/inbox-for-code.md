# Inbox for Claude Code (written by the chat)

Open items first. Claude Code reads this at session start and moves finished items to Done with a one-line result.

## Open
- **2026-10-15 - new control `lash.thickness` (ID-LashThick / ID-LashThin) and ID- keys on the new head.** Sammy asked
  for a lash thickness slider; the chat added `c('lash.thickness', ...)` to `src/model/controls.ts` (bi, region eyes,
  morph `ID-LashThick`, morphNeg `ID-LashThin`) and re-exported `knowledge/expected-contract.json`; typecheck and
  `npm test` pass. The new head (`blender/newhead`, apply_look + id_morphs.py) now carries these ID- keys (value 0) on
  the head and on every face part they move: ID-LashThick/Thin, ID-LashLong/Short (lid-line strips), ID-BrowThick/
  Thin, ID-BrowLong/Short (brow strips), ID-EyeSize(_Neg), ID-EyeSpacing(_Neg), ID-EyeHeight(_Neg) (head + eye
  parts), ID-MouthWidth(_Neg), ID-MouthHeight(_Neg), ID-JawWidth(_Neg), ID-ChinWidth(_Neg), ID-ChinLength(_Neg),
  ID-EarSize(_Neg), ID-EarOut. A slider must drive the key on EVERY mesh of the head pack that has it (head, ears
  object, eye white, iris, lid line, lid cover, brow, brow shade, nose / mouth strokes), not only the head.
- **2026-10-08 - new head morph targets: expressions (PF-) and camera-angle view keys (VW-).** The new head
  (`blender/newhead`, n56) now carries, on the head and its eye/brow meshes:
  - expression keys `PF-Blink_L`, `PF-Blink_R`, `PF-EyeWide`, `PF-EyeSad`, `PF-EyeAngry`, `PF-EyeHappy`,
    `PF-LookLeft/Right/Up/Down`, `PF-IrisSmall`, `PF-BrowUp/Down/Angry/Sad`; presets in
    `docs/qa/newhead/expressions.json`. Several are not in `src/model/performance.ts` yet.
  - view keys `VW-Yaw_L`, `VW-Yaw_R`, `VW-Side_L`, `VW-Side_R`: not user controls - the viewer must set them every
    frame from the camera's yaw around the head (degrees around the head's up axis, 0 = camera in front, + = camera
    toward the character's LEFT), so the eyes keep the drawn anime shape off-front. Weights (`view_weights` in
    `blender/newhead/view_keys.py`, Y34 = 35, smoothstep s(e0,e1,x)): a = |yaw|; side = L if yaw >= 0 else R;
    Yaw = s(0,35,a) for a <= 35, else 1 - s(35,90,a) (0 beyond 90); Side = 0 for a <= 35, s(35,90,a) up to 90,
    1 - s(90,150,a) beyond; the other side's keys 0. Expression keys add on top. Ask the chat if the yaw source
    (head bone vs. root) is unclear.

- **2026-10-15 - modular hair pieces, two new attributes, a brow slider and a game-style UI theme (chat).**
  - Hair is now built per region from recipes (`blender/newhead/hair_nh.py` RECIPES): objects `Hair_<Piece>_<recipe>`
    with Piece in Front, Top, SideL, SideR, Back, Base and attachments (Tail, TailL/R, BraidL/R, Bun, Ahoge), sockets
    `SOC-Hair<Piece>`, plus `Hair_<Piece>Tie_*` / `Hair_<Piece>Bow_*` (hair ties, ribbon bows; their own material) and
    `Hair_Cap_*`. Every hair piece carries ID-HairVolume / ID-HairWidth / ID-HairLength (+ _Neg); the app should
    drive them per piece (one slider set per socket) rather than once per hairstyle. New point attribute
    `hair_sec` (0..1, two-tone mask) on every piece; new point attribute `hair_cast` (1 lit, 0 = fringe shadow) on
    the head mesh, multiplied into the skin's Shadow Mask.
  - New identity keys on the brow strips: `ID-BrowInnerThick` / `ID-BrowInnerThin` (inner-end thickness). The
    control `brow.innerThickness` was added to `src/model/controls.ts` and the contract re-exported (145 sliders).
  - UI: `src/ui/theme-game.css` (loaded in main.tsx after styles.css) restyles the app as an anime-RPG character
    creation screen; App.tsx adds labels on both rails, a stage overlay (`.stage-fx`) and an action bar
    (`GameActions`: Randomize / Undo / Reset / Confirm); MenuBar gains Shift+R = randomize (R alone stays scale).
    Typecheck and the 50 tests pass. Screenshots: `docs/qa/newhead/ui_before_theme.png`, `ui_game_theme.png`,
    `ui_game_brow_sliders.png`. Remove the one import line to switch the theme off.

- **2026-10-15 - ears are a new mesh object; eye/forehead bake changes (chat, q13).**
  - `NEW_Ears_<tag>` is no longer a masked copy of the head mesh: `blender/newhead/ear_mhs3.py` builds it as its own
    mesh (2 x 289 verts, 256 quads per ear before one Subdivision level, a Solidify for thickness, the head's outline
    shell). Same materials and point attributes as the head (`shade`, `an_w`, `ear_bowl`, `ear_f`, `ear_lw`,
    `ear_line`), custom normals (lit). Shape keys on it: only `Basis`, `ID-EarSize`, `ID-EarSize_Neg`, `ID-EarOut`
    (same amounts as before); it has no PF-/VW- keys (the ears never moved in those). The old ear vertices stay in the
    head mesh, hidden by its `SkinOnly` mask modifier as before. `EAR_REBUILD = 0` in apply_look.py restores the old
    ear.
  - The identity bake (`id_morphs.py`) now relaxes the eye map's displacement (`BAKE_SMOOTH`): base mesh shape
    changed slightly at the temples, forehead and cheeks (max 6.5 mm); no topology or key-name change.
  - Eye texture: the iris cross sparkles are off (`eye_tex.CROSS_SPARKLES = 0`, Sammy's request).

- **2026-10-15 - expression keys per face element, new mouth objects (chat, q14).**
  Sammy asked for facial expressions with every element separate. New / changed on the n56 head (`blender/newhead`):
  - Mouth (`mouth_rig.py`): six objects `NewMouthLine_<tag>` (top lip line), `NewMouthInside_<tag>` (dark interior),
    `NewMouthTeeth_<tag>`, `NewMouthTongue_<tag>`, `NewMouthLower_<tag>` (lower lip line), `NewLipShadow_<tag>`; the
    interior / teeth / tongue / lower line have zero height in the basis (closed mouth). Each carries the same keys,
    named after `src/model/performance.ts` where the app already has the shape: `PF-SmileClosed`, `PF-SmileOpenJaw`,
    `PF-Frown`, `PF-Smirk_L`, `PF-Smirk_R`, `PF-Pout`, `PF-VisAA`, `PF-VisOH`, `PF-VisEE`, `PF-VisWide`; new (not in the
    app yet): `PF-MouthWide`, `PF-MouthNarrow`. The other app keys (PF-JawOpen, PF-VisMBP/Small/Mid/IH/OO/FV/L/TH/SZ,
    PF-FrownOpen, PF-Press, PF-LipBite, PF-Grimace, PF-Snarl, PF-Disgust, PF-Surprise, PF-Cry, PF-MouthSide_*,
    PF-Tongue*) do not exist on this head yet.
  - Nose: `PF-NoseSneer` on `NewNoseShade_`, `NewNoseLine_`, `NewNoseHL_` (new name; the app has no nose group).
  - Brows (per side, as in the app): `PF-BrowRaise_L/_R`, `PF-BrowLower_L/_R`, `PF-BrowInnerUp_L/_R` (each only on its
    own brow strip `RigBrow_<tag>_L/_R` + shade). The older unsided brow keys stay (`PF-BrowUp`, `PF-BrowDown`,
    `PF-BrowAngry`, `PF-BrowSad`); the app's `PF-BrowSad_L/_R`, `PF-BrowOuterUp_*`, `PF-BrowFurrow_*` are not built.
  - Eyes / irises unchanged (`PF-Blink_L/_R`, `PF-EyeWide`, `PF-EyeSad`, `PF-EyeAngry`, `PF-EyeHappy`, `PF-Look*`,
    `PF-IrisSmall`); note the app uses `PF-EyeWide_L/_R` and `PF-Squint_*` - a mapping is needed.
  - Presets (`docs/qa/newhead/expressions.json`): neutral, blink, wink_left, smile, happy, laugh, amazed, sad, angry,
    shout, worried, determined, skeptical, pout, talk_a, talk_o, talk_e - weight sets over the keys above.
  - View keys: new knob `NEAR_SHIFT` (look_knobs view 0.4; FAR_GAP_IN 0.2, FAR_GAP_OUT 0.04) - same VW- key names.

- **2026-10-15 - PF-JawOpen, lower-face bake, mouth layers (chat, q15).**
  On the n56 head (`blender/newhead`):
  - New key `PF-JawOpen` (the app's name): on `NEW_Head_<tag>` the skin below the mouth line turns down and back about
    a hinge under the ear (chin drop ~10 mm at 1.0; `mouth_rig.JAW_THETA`), and on the six mouth objects the matching
    painted opening. Presets now use it: happy 0.35, laugh 0.6, amazed 0.5, shout 0.7 (`expressions.json`); determined
    gained `PF-SmileClosed` 0.3.
  - `PF-VisWide` changed shape (squarer, taller); teeth band slightly taller with tapered ends; mouth layers sit at new
    offsets off the skin (`MOUTH_LIFT`). Same object and key names otherwise.
  - Iris look keys (`PF-LookLeft/Right/Up/Down`) now keep the iris in front of the eye white at 3/4 (it vanished
    behind it with a look toward the nose); same names, slightly different vertex positions.
  - Identity bake (`id_morphs.py`): lower face narrower between cheek and jaw (`JAW_TAPER`), rounder chin
    (`CHIN_WIDE_BAKE` 0.045), smoothed jaw/neck junction (`JAW_NECK_SMOOTH`). Base mesh shape only, no topology or
    key-name change.

- **2026-10-15 - ear default size, mouth key shapes (chat, q16).**
  n56 head: the rebuilt ear is ~15 % smaller by default (`ear_mhs3.EAR_H_SCALE` 0.90; ID-EarSize / _Neg unchanged, so the
  creator's ear slider range starts smaller). Changed shapes, same names: `PF-Pout` (small pucker + raised lip shadow),
  `PF-VisAA` (wider), `PF-VisWide` (less boxy), teeth band thinner in every open key, `PF-EyeHappy` (lower lid higher).
  Preset `pout` now Pout + Frown 0.5 + EyeAngry 0.3 + LookLeft 0.4 + BrowInnerUp 0.5 (expressions.json). No new keys.

- **2026-10-15 - first head pack for the app: head_mhs3_n56 (chat, q17).**
  `library/humanoid/bodies/adult/head_mhs3_n56/` (+ manifest entry), exported by `blender/newhead/export_head_pack.py`.
  Head only, applied as the body (the procedural body hides). Every face element is its own mesh so the app can tweak it:
  CHR_Head, CHR_Ears, CHR_EyeWhite_L/R, CHR_Iris_L/R, CHR_LidLine_L/R, CHR_LidCover_L/R, CHR_Brow_L/R,
  CHR_BrowShade_L/R, CHR_NoseShade, CHR_NoseHighlight, CHR_NoseLine, CHR_MouthLine, CHR_MouthInside, CHR_TeethUpper,
  CHR_Tongue, CHR_MouthLower, CHR_LipShadow. Painted parts use flat materials named `*_emiss` (black base + emissive),
  skin is `Skin_n56`. Armature CHR_Armature with DEF-Head; sockets SOC-HeadTop, HairScalp, HairFront, HairSide_L/R,
  HairBack, Ear_L/R, Eyewear, Neck. `node scripts/e2e_head_pack.cjs --pack <lib>` passes (sliders eye.size,
  mouth.width, jaw.width, ear.size; PF-Blink_L, PF-SmileOpenJaw, PF-VisAA, PF-JawOpen, PF-BrowInnerUp_L).
  Asks for the app side:
  - keys the head has that the app does not drive (check_pack orphan warnings): PF-EyeHappy, PF-EyeSad, PF-EyeAngry,
    PF-EyeWide is driven; PF-Look{Left,Right,Up,Down} (gaze), PF-IrisSmall, PF-NoseSneer, PF-MouthWide, PF-MouthNarrow,
    PF-BrowUp/Down/Angry (aliased in the export to PF-BrowRaise/Lower/Furrow), PF-EyeHappy -> PF-Squint and PF-EyeSad ->
    PF-LidUpperDown are aliased too. Gaze through the PF-Look keys would let the creator move the painted irises.
  - camera-angle keys (VW-Yaw_L/R, VW-Side_L/R: eyes / brows reshaped for 3/4 and side) exist in Blender but are not
    exported; the app would need to set them from the view yaw (weights in blender/newhead/view_keys.view_weights).
  - check_pack treats bodies/ packs as full bodies (height, origin at the feet): a head-only test pack fails those two
    by design. A "head" slot or a check exemption would make this explicit.
  - new mouth objects / colours: interior (96,56,56), tongue (210,115,95) sRGB, teeth band thinner (see q17 log).

- **2026-10-15 - app now drives the VW- view keys; head pack q18 (chat, q18).**
  Sammy: "the model looks weird on the tool, like the perspective is not right". Cause: the head is drawn with
  camera-angle keys (VW-Yaw_L/R, VW-Side_L/R: the skull silhouette, far eye and brows redrawn for 3/4 and side, up to
  53 mm) that the pack left out and the app never set, so the creator showed the uncorrected 3/4.
  App change made from the chat side (please review): `src/viewport/gltfPacks.ts` - `viewKeyWeights(yawDeg)` (port of
  blender/newhead/view_keys.view_weights, Y34 = 35) and `viewKeyDriver(scene)`, called in attachPacks after the
  performance driver; each mesh with VW- targets sets them in `onBeforeRender` from the camera position in the pack's
  local frame (yaw = atan2(x, z)), so viewport, thumbnails and captureViews each get their own weights. Test
  `tests/viewKeys.test.ts`. typecheck / test / build pass; e2e_head_pack OK. No contract names changed (VW- is a new
  prefix the app only reads from packs that carry it; please add it to the contract if you keep it).
  Pack changes, same names: CHR_NoseShade / CHR_LipShadow flat colour (173,119,100) sRGB (the export used to take only
  the mauve tint of the Blender shade group: purple blobs in the app); CHR_Tongue fills the bottom of the opening up to a
  soft arc; teeth band narrower; open lens/shout corners rounded; open-mouth lip shadow closer and narrower.
  Still app-side: the skin shadow tint on the neck reads pink-mauve next to Blender's warm brown (toon skin shadow colour).

- **2026-10-16 - new head pack meshes CHR_MouthThroat, CHR_TeethShade, CHR_MouthDeep, CHR_UpperLipShade (chat, q19/q20).**
  Asset contract addition (docs/CLAUDE_BUILD_PROMPT.md names): four flat-colour mouth meshes in head_mhs3_n56, each its
  own mesh with the same PF- / ID- keys as the other mouth strips:
  CHR_TeethShade (200,198,214) sRGB - lower part of the teeth band; CHR_MouthDeep (60,30,30) - undershadow under the
  teeth; CHR_UpperLipShade (190,130,105) - thin shade over the mouth line (upper lip plane); CHR_MouthThroat (128,60,56)
  - throat band over the tongue, exported but zero-height while MOUTH_THROAT is 0. Deep / UpperLipShade only exist
  when their knobs are on. Draw order is by small offsets off the skin (inside < throat < deep < tongue < teeth <
  teeth shade < lower < line); the app's flat material must keep depth testing on for these to layer.
  Please add the names to the contract / expected-contract.json if you keep them. e2e_head_pack passes (27 meshes).
  Mouth is also lower and wider and the lips are pushed forward in the head mesh (same names).

- **2026-10-16 - VW- view keys now also on the mouth strips; far eye shorter in 3/4 (chat, q21).**
  No new meshes, no renamed ones. CHR_TeethUpper, CHR_TeethShade, CHR_MouthDeep, CHR_Tongue and CHR_MouthThroat now
  carry VW-Yaw_L/R and VW-Side_L/R (the app already drives VW- on any mesh that has them): in a turned view the teeth and
  tongue slide in from the far mouth corner (teeth 15%, tongue 8% of the mouth half-width at 35 degrees) so the dark
  inside of the far cheek shows - parallax for "the teeth and tongue look flat". The far eye, brow and the skin around
  them are 15% shorter vertically in VW-Yaw (far side only). Pack re-exported (27 meshes); typecheck / test / build pass,
  e2e_head_pack OK. Knobs: blender/newhead/look_knobs.json view.FAR_V / MOUTH_TEETH_D / MOUTH_TONGUE_D.

- **2026-10-16 - new head pack head_mhs3_v2 (chat, head v2) - new element names.**
  Sammy asked for a new model (q22). library/humanoid/bodies/adult/head_mhs3_v2 is a new sculpted head (blender/head_v2):
  real mouth cavity, curved tooth arches and tongue (PF- mouth keys move them), face pieces lying on a curved face so
  turned views foreshorten from the geometry - no VW- view keys. Same CHR_ names as n56 where they exist (CHR_Head,
  CHR_Ears, CHR_EyeWhite, CHR_Iris, CHR_LidLine, CHR_Brow, CHR_NoseShade, CHR_NoseHighlight, CHR_MouthLine,
  CHR_MouthInside, CHR_TeethUpper, CHR_Tongue, CHR_LipShadow) plus new flat-colour elements (please add to the
  contract if you keep them): CHR_EyeWhiteShade, CHR_IrisTop, CHR_IrisRim, CHR_Pupil, CHR_EyeHighlight, CHR_LidLower,
  CHR_LidCrease, CHR_EarInner, CHR_EarLine, CHR_TeethLower. CHR_MouthInside is now the real cavity (two materials).
  Keys: ID-EyeSize, ID-MouthWidth, ID-JawWidth, ID-EarSize (+ _Neg), PF-JawOpen, PF-SmileClosed, PF-SmileOpenJaw,
  PF-Frown, PF-FrownOpen, PF-VisAA/OH/EE (+ aliases), PF-Pout, PF-Smirk_L/R, PF-Blink(_L/_R), PF-Squint(_L/_R),
  PF-EyeWide, PF-LidUpperDown, PF-LidLowerUp, PF-Brow* (InnerUp, Raise, Lower, Furrow + sides, Sad, OuterUp).
  e2e_head_pack --id head_mhs3_v2: E2E OK (36 meshes). check_pack: same two head-only fails as n56 (height, feet),
  WARN 80k triangles (budget 18-28k: to reduce). typecheck / test / build pass.

- 2026-10-17 head_mhs3_v2 re-exported (q23 reference-match loop vs MHS3 Leo, TypeSafe judge + picture A/B): same 36
  CHR_ meshes and keys, no new names - geometry and face pieces changed (rounder broader chin, flatter face front, thicker
  neck, lower angled brows, bigger iris, brow layer lift). e2e_head_pack --id head_mhs3_v2: E2E OK. Blender-only shading
  changes (wider analytic ellipsoid, thicker outline) are in pc_v2.py, not in the pack's normals.

- 2026-10-17 (q31) head v2 geometry now blends in a CC BY 4.0 dataset head ("Autumn Girl" by Aryzus, Sketchfab):
  face front and ears come from it (blender/head_v3/base_grid_d60.npz), skull/back/neck stay ours. Same CHR_ mesh
  names, keys and face layout (pupil line h 0.445) - no contract change, not re-exported yet. New requirement: the credit
  in docs/reference/ATTRIBUTION.md must ship with any pack or app build that contains this head (credits screen or
  pack metadata). HEAD_BASE= (empty) when building gives the old all-procedural head.

## Done
(none yet)
