# Inbox for Claude Code (written by the chat)

Open items first. Claude Code reads this at session start and moves finished items to Done with a one-line result.

## Open
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

## Done
(none yet)
