---
name: hair-validators
description: Use when modeling, reviewing or accepting hair for the Anime Character Creator library in Blender (clumps, cards, braids, ponytails, facial hair): run the hair validators and the TypeSafe hair judge before a hair pack is exported.
---

# Hair validators

Run before exporting any hair pack. Everything below is in `blender/validators/` and `blender/scripts/`.

## What "good" means (measured, not guessed)
- Many separate chunky clumps: Hina has 62 (median 121 vertices); a short cut needs 20+; Amshani's hair is only 16 and reads weak.
- Clump thickness / width >= 0.45 (Hina 0.63); a round tube is 1.0.
- Clump width about 0.25-0.55 of the head height (Hina 0.47).
- Tapered tips: tip / root width <= 0.75 (Hina 0.61). Sides closed; only the root may be open.
- One UV island per clump, mostly taller than wide (the highlight band and dark root need a vertical island).
- Sits on the head: no more than 15% of vertices buried deeper than 3% of the head height; cranium covered; ears clear when creature ears are equipped (build prompt).
- Contract: parented to a `SOC-Hair*` socket, `NG_ToonHair`, volume and width controls (and length where the cut can grow), root colour, tip colour, highlight strength.

Bands marked "calibrated" in `hair.py` come from Hina and Amshani, not from a published source; tighten them once more references exist.

## Run
1. Landmarks: `LM-Crown` and `LM-Chin` must exist for the head (see docs/VALIDATORS.md). Hair is its own object (or `body:<obj>:<group>:<material>` for baked hair).
2. In Blender: `blender -b file.blend -P blender/scripts/analyze_hair.py -- <name> <hair_object> <body_object> <landmarks.json> docs/qa/hair [1 if creature ears]`
3. Contract: `hair.contract_findings(name, bpy_adapter.hair_object_info(name))`.
4. TypeSafe: `hair_judge.ask(topo_json, name, style, contract_dict)` (needs `TYPESAFE_API_KEY` on your PC). It sees words, not numbers; low-confidence answers are "needs a human look", and a first-fix answer that changes with option order is uncertain.

## Rules
- Numeric findings are authoritative; TypeSafe only adds a read of the combination and a first fix.
- Never accept a hair pack with FAIL findings. WARN needs a note in docs/PHASE_LOG.md.
- Hair clumps are many shells on purpose: do not "fix" floating fragments on hair (`multi_part=True`).
- Do not copy hair from commercial characters; reference geometry is for measuring only.
