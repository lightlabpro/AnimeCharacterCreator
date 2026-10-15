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

## Done
(none yet)
