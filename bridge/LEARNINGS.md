# Learnings ledger

Append-only. Newest at the bottom. Format (use `python3 bridge/tools/log.py`):

```
## YYYY-MM-DD [code|chat] topic
- finding: one sentence, measured or decided
- evidence: how you know (file, number, render, test)
- status: confirmed | unverified | superseded-by <date topic>
- use: what the other side should do with it
```

## 2026-10-05 [code] render validator calibration (toon stats)
- finding: On the 21 MHS3 / style_dataset reference stills, shadow chroma (Lab) is 4-40 with median about 15, dominant tone bands are 5-14, the share of sharp shading transitions is 0.18-0.57, and the outline ring score is 0.04-0.92.
- evidence: measured with `.claude/skills/render-validator/scripts/validate.py` helpers on `docs/style_dataset/images/*` and `docs/reference/mhs3/*`. These stills are painted scenes, not isolated characters, so segmentation is rough.
- status: unverified for isolated Blender renders. Reference-comparison floors (sil_iou 0.80, edge_f 0.35, palette 0.55) were never calibrated.
- use: chat, run `measure` on 10-20 of your renders you judge good and bad, then log the measured values here so the floors can be set from data.

## 2026-10-05 [code] default creator face vs the MHS3 target
- finding: The app's default face (Stories style, adult) misses the target in five visible ways: shadows are pink-grey not warm orange-brown, eyes are oversized and too far apart, no lash wing, brows hidden under the fringe, hair is thick spike cones not flat clumps.
- evidence: headless screenshot of the face camera against `docs/style_dataset/images/ref-01.png`.
- status: confirmed (visual). Not yet fixed.
- use: chat, if your Blender measurements for eye gap, lash wing and clump thickness differ from `anthropic-skills:anime-character-modeling`, log them. Code will tune `src/viewport/face.ts`, `hair.ts` and `toonMaterial.ts` to the logged numbers.

## 2026-10-05 [code] how AI 3D generators work, and what transfers
- finding: Production generators are staged (shape, then texture, then optional retopo, then rig). Every stage needs human cleanup for anime characters. Benchmarks never trust one score: they use fixed multi-view renders and several independent signals, and optimizing a single proxy makes it get gamed.
- evidence: `reports/AI 3D generation pipelines.md` (sources partly blocked, search summaries only; confirmed vs inference is labelled inside).
- status: confirmed for the pipeline shape, unverified for Meshy internals.
- use: chat, do not try to "generate" the asset library in one shot. Keep the staged approach, and run the validator after every stage.

## 2026-10-05 [code] bridge between Claude Code and chat is live
- finding: Shared memory is bridge/LEARNINGS.md plus two inboxes; the chat builds to knowledge/expected-contract.json (143 sliders, 169 identity keys, 59 PF keys, 30 sockets)
- evidence: bridge/tools/export_contract.py output committed; skill zips built and the validator zip runs after extraction
- status: confirmed
- use: chat: install bridge/skill-packages/*.zip, paste bridge/CHAT_PRIMER.md into the project instructions, reply with a BRIDGE-ENTRY

## 2026-10-05 [code] chat head vs reference head: measured
- finding: The chat's last Blender head is 0.07-0.10H too wide at the cranium, 0.06H too shallow front to back (width:depth 0.91 vs reference 0.72), chin 0.035H too far back relative to the nose, jaw slightly wide. This wrong form is the likely cause of the wrong toon lighting.
- evidence: head_profile.py on the front and side panels of Sammy's comparison image (knowledge/from-chat/head-comparison-2026-10-05.webp), chin rows read by eye, accuracy about 0.03H, one reference head
- status: confirmed for the numbers, unverified for the lighting cause
- use: chat: run head-shape-audit on the Blender head before any more shading work; fix cranium width and depth first

## 2026-10-05 [code] app ellipsoid head had the same flaw, now fitted
- finding: The creator's default head had cranium 0.70H, width:depth 0.88, jaw at 0.8H 0.57H, nose ahead of chin 0.08H. Fitted to the reference: 0.59H, 0.74, 0.34H, 0.11H. A plain ellipsoid skull is widest too low (0.3-0.4H) where the reference is flat-sided 0.2-0.35H.
- evidence: scripts/fit_head.ts, tests/headShape.test.ts, src/model/headShape.ts HEAD_TUNING; screenshots of the running app
- status: confirmed
- use: chat: build temples flat and vertical, not an egg. Code: the app head still has no jaw angle or cheekbones, the real fix is a sculpted head mesh from the library
