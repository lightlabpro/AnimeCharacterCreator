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

## 2026-10-05 [code] lessons from Meshy's agent repo applied to the validators
- finding: The Meshy agent repo is a CLI skill layer with no model internals. Its useful ideas are tri-state checks (unknown is not a pass), face-count gates before expensive stages, honest previews, shortest-route and reuse rules, and a validator for the skills themselves. All five were applied; the skill validator immediately caught a stale zip and a cross-skill script reference that would have broken a chat install.
- evidence: knowledge/meshy-agent-lessons.md, scripts/validate_skills.py, tests/py/test_validate.py (16 tests)
- status: confirmed
- use: chat: re-upload render-validator.zip and ai-3d-pipeline.zip, run mesh_stats.py in Blender and report the numbers

## 2026-10-05 [code] validator v2: calibrated on real heads
- finding: Contour distance separates same-head from different-head cleanly (perturbed copies <=4.2 px, different heads >=9.7 px on a 256 px frame). Edge overlap separates well (0.65 vs 0.63 worst/best, floor 0.60). Silhouette IoU separates by only ~0.03 and palette detects style not shape. The creator's gradient backdrop broke figure detection (97% foreground) and is now handled. The chat's two clay head attempts differ by 0.9 px, so the last revision was a tweak not a fix.
- evidence: tests/fixtures/validator real crops, knowledge/validator-calibration.json, tests/py/test_real_images.py
- status: confirmed on one reference head in one pose
- use: chat: run calibrate.py on your own good and bad renders, report NOT USEFUL metrics; treat a MICRO-CHANGE note as a signal to change the form, not the polish

## 2026-10-05 [code] validator: skin-shadow gate from 14 real MHS3 stills, two-reviewer gate, cross-view consistency
- finding: Shadowed skin in 14 official MHS3 stills has chroma 10-52 (mostly 19+) and hue 35-69 deg; the shadow:lit chroma ratio varies 0.45-1.8 so it is not gated. The user's toon shader measures chroma 25.6 hue 68.9 and passes; grey clay heads have no skin pixels. Known gap: a green or blue shadow on skin passes both the skin and the grey gates, only the review criterion shading_hard_warm_shadows catches it.
- evidence: tests/py/test_real_images.py SkinShadow (pins all 14 stills), knowledge/validator-calibration.json
- status: confirmed on 14 stills, one good toon shader
- use: chat: when shadows look wrong in a toon render, check skin_shadow_chroma and skin_shadow_hue in the measure output first; use --reviews 2 for the final pass
