---
name: region-validators
description: Use when checking an Anime Character Creator asset per region and per feature in Blender: eyes, eyebrows, nose, mouth and teeth, ears, jaw, hair, neck, torso, arms, hands, legs, feet, clothing, accessories, humanoid-beast traits (muzzle, tail, wings, horns, surface, digitigrade legs) and the quadruped dragon. Runs the region validators and the TypeSafe region judge.
---

# Region validators

Everything is in `blender/validators/` and `blender/scripts/`; see docs/VALIDATORS.md for the full tables. Region ids are the app's own (`src/model/types.ts` Region) plus `clothing`, `accessory`, `quadruped`, `archetype`, `surface`.

## Run
1. Landmarks first: `LM-Crown`, `LM-Chin`, `LM-Floor`, eye corners, `LM-Mouth` (see docs/VALIDATORS.md). A missing landmark is SKIP, never guessed.
2. Body, face, rig, expressions: `blender -b file.blend -P blender/scripts/analyze_regions.py -- <name> <kind> <body> <armature|-> <landmarks.json> docs/qa/regions [typesafe]`
3. Hair: `analyze_hair.py` (see the hair-validators skill). Topology and bends: `analyze_topology.py`.
4. Clothing and accessories: `analyze_clothing.py -- <name> <body> <landmarks.json> <out> garment:<obj> accessory:<slot>:<obj>`; the manifest goes through `clothing.contract_findings`.
5. Humanoid beasts: `beast.py` functions on the muzzle, feet, tail, horns and wings; `beast.recipe_findings(archetype, looks)`; `archetype.classify(looks, archetype)` for distinctness.
6. Quadruped: `quadruped.metrics(verts, faces, landmarks)` with `LM-FootFront_L/R`, `LM-FootHind_L/R`, `LM-Belly`, `LM-WingRoot_L`.
7. Packs: `python -m blender.validators pack library/` and `node blender/scripts/validate_gltf.js <pack>.gltf` (Khronos glTF-Validator).

## The app is the consumer
The app's built-in bodies are placeholders that this library replaces. A model must provide every shape key, bone property, shader parameter and `PF-` key the app's controls are wired to (`app_contract.py`, regenerated list in docs/APP_CONTRACT.md); the build prompt names only part of them. A bidirectional slider drives `<key>` and `<key>_Neg`. Check `<region>.app.*` findings before accepting a model.

## Standards used (each page was fetched and read)
- VRM 1.0 humanoid spec: 55 bones, 15 required, parent/child tree (`standards.VRM_HUMANOID`, `rig.py`).
- VRM preset expressions, the 52 ARKit blendshapes (from the Perfect Sync article), Oculus 15 visemes, FACS action units by region (`standards.py`, `expression_map.py`).
- Khronos glTF-Validator for structure.
- docs/anatomy-manual.md for proportions, beasts (section 10) and the dragon (section 11).

## TypeSafe rules
- It only sees words; thresholds and arithmetic stay in code. Every question is yes = good; the Choice has a "none" outcome and is asked in two option orders; low confidence means "needs a human or Claude look".
- Uses: map unmatched shape-key and bone names to the standards (two-step region then name), classify archetypes from element looks (state the ABSENT traits too), and judge each region (`region_judge.py`, one small request per region).
- Numeric findings are authoritative. Bands marked heuristic or calibrated are not published figures; tighten them as more references are measured.
