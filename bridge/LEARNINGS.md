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

## 2026-10-05 [code] validator can now judge the creator app; first verdict; two validator bugs found by doing so
- finding: Clean transparent fixed-view captures of the app (window.creator.captureViews, scripts/capture_views.cjs) now feed the validator. First verdict on the app's face vs the official MHS3 face: shadows pass (skin shadow chroma 31.9, hue 55), shape and palette fail (silhouette IoU 0.48, palette 0.28, contour 13.1 px): the app head is a long thin neck with sparse spiky hair vs a broad head with full hair. Doing this exposed a render-hash overwrite bug and a wrong clipped-figure failure on close-ups (both fixed, tested), and a full game screenshot used as a reference gave meaningless fails, now UNKNOWN with instructions.
- evidence: tests/py (48 tests), scripts/capture_views.cjs, src/viewport/cleanCapture.ts, ws run against tests/fixtures/validator/mhs3.png
- status: confirmed
- use: chat: crop references to the character or use a transparent PNG; an unusable reference now returns exit 13 with the reason

## 2026-10-05 [code] pack pipeline proven end to end; one integration gap fixed; placeholders are placeholders
- finding: The app's procedural bodies are placeholders, so effort moved to the import pipeline. A generated contract pack imports through the real Import button, a slider drives its ID- key to 1, performance drives its PF- key, and a hat attaches to the pack's SOC-HeadTop. Found and fixed a gap: accessory and hair packs attached to the placeholder rig's sockets (0.48 m off in the test), now they move onto the SOC- nodes inside the body pack. A loaded body pack hides all procedural parts including face and hair, so the body pack must carry eyes, brows and mouth, and hair must come as separate packs.
- evidence: scripts/e2e_pack.cjs, tests/py/test_e2e_pack.py, tests/packSockets.test.ts, check_pack.py with 21 tests, 70 Python tests total
- status: confirmed
- use: chat: run check_pack.py on every export and reply with the findings for your first body pack; every socket documented in CLAUDE_BUILD_PROMPT.md must exist in the body export

## 2026-10-05 [code] loader renames bones; pose clips; perf is fine; motion packs unsupported
- finding: Three's GLTFLoader strips '.' from node names, so Rigify-style DEF-upper_arm.L loaded as DEF-upper_armL and every limb-length control silently missed sided bones; fixed by matching userData.name (real bug, test-first, proven end to end). Body packs can now carry POSE-<pose> animation clips that the app applies when that pose is picked. A 30 MB all-keys body: JS rebuild per slider change about 20 ms, GPU geometries and textures plateau (122 and 170 over 150 changes) so the earlier growth was a bounded cache filling, not a leak. Motion packs are not played by the app; the toast that claimed they were is corrected.
- evidence: tests/packSockets.test.ts (bone names, pose clips), scripts/e2e_pack.cjs steps, scripts/perf_pack.cjs series, 24 pack-check tests
- status: confirmed for the app side; unverified on real GPUs and real Blender exports
- use: chat: answer the pose clip proposal in inbox-for-chat; export a first body pack and run check_pack.py

## 2026-10-05 [code] Blender-side validators executed for the first time in real Blender 5.0.1; four bugs found
- finding: bpy 5.0.1 installs from PyPI, so the Blender scripts now run headless. First real runs found: (1) the head audit read vertex slabs and silently dropped rows on smooth meshes, replaced by exact triangle-plane slicing plus UNKNOWN status; (2) landmarks created by script were read at stale positions until view_layer.update(); (3) the render script permanently changed the user's scene (view transform, resolution, camera) and crashed on unsaved files, now restores everything and writes a camera manifest; (4) Blender's exporter writes current shape key values as default morph weights and needs export_extras for socket_name, both now handled by export_pack.py. The checker's assumptions all held on a real export (extras.targetNames, dotted bone names, sockets, pose clips, height, feet at 0). Pose clips are now sampled at the LAST frame after a real Blender action showed the first-frame rule was wrong.
- evidence: tests/blender (22 tests in real Blender 5.0.1), tests/py (83), scripts/e2e_pack.cjs run against a Blender-exported pack, export_pack.py
- status: confirmed on Blender 5.0.1; unverified on 5.2
- use: chat: use export_pack.py for every export, re-upload the three changed skills, tell Code if anything differs in 5.2

## 2026-10-05 [code] checker rules for what the app cannot load or render
- finding: three.js stores all morph targets of a mesh in one float array texture: one layer per target, vertices x (1 + 1 if morph normals) x 16 bytes x targets, and WebGL2 guarantees only 256 layers. The library plans about 228 keys, so there is little headroom. The app sets no Draco, Meshopt or KTX2 decoder, so packs using them cannot load. More than 4 bone influences are ignored. check_pack.py now fails or warns on all of these and prints the GPU memory estimate (a 19k triangle body with all 228 keys and normals: about 79 MB).
- evidence: node_modules/three WebGLMorphtargets.js and GLTFLoader, tests/py/test_pack_check.py AppLimits (29 pack-check tests)
- status: confirmed from the three.js source; unverified on real GPUs
- use: chat: keep one body mesh under 256 shape keys, export without compression, and read the morph_memory line of the checker

## 2026-10-05 [code] body proportions from reference models
- finding: Anatomy checks should compare against targets measured from real reference meshes with Blender python, not guessed bands. body_audit.py measures joints (Rigify/Mixamo/VRM names) and mesh slices as fractions of height, builds min/max bands from several references, and checks candidates (exit 0/12/13); rig and mesh symmetry use fixed ceilings.
- evidence: tests/py/test_body_audit.py (9) and tests/blender BodyAuditCase: Blender importer and plain glTF loader agree; scale invariant; long legs, asymmetric rig/mesh fail; missing joints unknown. Blender's glTF importer adds an Icosphere bone-shape mesh that must be excluded.
- status: unverified: tool built on synthetic figures, no real reference measured yet
- use: Run blender-measure on each reference model and send the JSON; then Code builds body-targets.json

## 2026-10-05 [code] first real reference model measured (Amshani)
- finding: The Amshani .blend (XxAlonexX/Blender-Character) measures cleanly but is a chibi-leaning single mesh with merged hair, skirt and boots, so it is not an MHS3 body target. Rigs name joints differently: this one uses Left Leg/knee/ankle/elbow/wrist (leg = thigh when a knee bone exists). T-posed arms inflate torso widths, so slices now clip to the torso. Blender's glTF importer adds an Icosphere bone-shape mesh; skip it. A script named inspect.py shadows the stdlib and crashes bpy.
- evidence: knowledge/body-profiles/amshani.json, README.md there; tests/py/test_body_audit.py Vroid case
- status: confirmed
- use: Measure MHS3-style references (separate head, hair and body meshes) for the real targets; panic3d is head-only and needs a GPU

## 2026-10-05 [code] Mirai reference measured; mirror ceiling recalibrated
- finding: mirai.blend (separate body/hair/clothes meshes, rig upperarm.L/lowerarm.L/upperleg.L/lowerleg.L with IK pole bones named elbow.L/knee.L) measures cleanly with --meshes mirai. IK pole bones named elbow/knee must not override explicit bones, so aliases are used only when no explicit bone exists. Mirror ceiling raised 1.2%->2% H: this good model measures 1.22%. Amshani (4%) still fails. Default mesh skip list now also skips shirt/skirt/jacket/shoes/ribbon/plane/light.
- evidence: knowledge/body-profiles/mirai.json; check of amshani against mirai targets exits 12 with sensible directions
- status: unverified: single reference band, thresholds not yet validated on more models
- use: More references of different builds widen the band; MHS3 reference still needed

## 2026-10-05 [code] Navia glb measured; orientation from skeleton
- finding: Sketchfab glb files import into Blender Y-up (root-node rotation), which made Blender-side measurements nonsense while the plain-glTF path was right. measure() now orients from the skeleton (up = head minus feet, x = left minus right), so any file orientation works and both paths agree. The glTF loader takes joint positions from inverse bind matrices. usdz import in Blender 5.0.1 yields no armature bones, so use the glb. Navia has the coat/hat merged into the meshes, so only joint metrics are reliable.
- evidence: tests/py/test_body_audit.py Orientation; navia python vs blender metrics identical to 4 decimals; knowledge/body-profiles/navia.json
- status: confirmed
- use: Prefer references with separate body meshes; export references as glb or measure from .blend/.fbx
