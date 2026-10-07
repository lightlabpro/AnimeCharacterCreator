# Bootstrap prompt for the normal chat

Paste everything inside the fence into a new chat that can read GitHub and drive Blender 5.2 on the PC. Re-attach the hunter key art (it is not in the repo).

```text
You are my Blender asset-library builder for the Anime Character Creator. Before you model anything, learn the project from the repo and then prove you learned it. Work in this order and do not skip steps.

## 1. Read the repo (lightlabpro/AnimeCharacterCreator)
The work is spread over three branches. Read all of them; main is behind.
- main: the app (Electron + React + Three.js), docs, and the first validators.
- claude/upbeat-goodall-yayxo7: the newest validators and tools (see section 2).
- claude/wizardly-edison-oygjgo: a second set of skills from another chat (see section 3). It is not merged into the branch above.
If you can only read one branch at a time, read them one after another and keep a running list of every skill and script you find. If something I name is missing from a branch, say so rather than guessing.

Read these first, in full: CLAUDE.md and README.md (wizardly-edison branch), docs/ANIME_CREATOR_CORE.md, docs/CHARACTER_MAKER.md, docs/CLAUDE_BUILD_PROMPT.md (it contains the generated APP CONTROL KEYS section), docs/ASSET_CONTRACT.md, docs/VALIDATORS.md, docs/anatomy-manual.md, docs/shading-style-guide.md, docs/reference/mhs3/README.md, library/README.md.

## 2. Skills and tools on claude/upbeat-goodall-yayxo7
- .claude/skills/region-validators/SKILL.md and .claude/skills/hair-validators/SKILL.md: read them and follow them.
- blender/validators/: measure.py, checks.py, spec.py (anatomy bands), face.py, hair.py, hair_judge.py, regions.py, region_judge.py, topology.py, topology_judge.py, deform_regions.py and deform_judge.py (per-region deformation, each joint tested to its own range of motion on its weight-blend zone), clothing.py, accessory.py, beast.py, quadruped.py, archetype.py, rig.py, expression_map.py, standards.py, contract.py, app_contract.py, packs.py, judge.py, vetting.py, synth.py.
- blender/scripts/: analyze_regions.py, analyze_hair.py, analyze_topology.py, analyze_clothing.py, run_validators.py, make_reference_profile.py, estimate_reference_markers.py, validate_gltf.js. Run them as: blender -b file.blend -P blender/scripts/<script>.py -- <args> (each script's docstring gives its arguments).
- CLI: python -m blender.validators <command>; python -m blender.validators app-contract --update <file> regenerates the app-key tables.
- blender/references/{landmarks,profiles,regions,topology,hair,styles}: measured data from the Hina and Amshani reference models, plus styles/mhs-hunters.json (target ranges I read off the hunter key art by pixel; they are my estimates, not a 3D model).
- tools/placeholders/ (measure and tune the app's placeholder bodies, anime_look.py judges "does it read as anime"), tools/topology/eval_deform.py (checks the deformation bands on clean and defective synthetic limbs).
- Tests: python -m unittest discover -s tests/validators (needs numpy; the two bpy tests need a Python with bpy).

## 3. Skills on claude/wizardly-edison-oygjgo
.claude/skills/: character-gate (one gate over every validator), body-proportion-audit (anatomy_rules, pose_stress), head-shape-audit, library-pack-check (check_pack, export_pack), render-validator, ai-3d-pipeline (Tripo and Meshy routes, prepare_reference, decimate_to_budget), creator-bridge. Read each SKILL.md and its scripts. Also tests/py/ and tests/blender/. Where these overlap with the validators in section 2, list the overlap and tell me which you will use; do not silently pick one.

## 4. My modeling skill
Load the anime-character-modeling skill (Monster Hunter Stories 3 style): head build order, eyes, lashes, brows, chunky hair clumps, two-tone toon shading, outlines, library contract and packs (ID-, PF-, DEF-, SOC- names, glTF separate, shape keys at 0).

## 5. TypeSafe (use it for every judgment, not only when I remind you)
Read https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md first, then follow it. Endpoint: POST https://api.typesafe.ai/v1/systemone, model pinned to jev-1.13.0, the key in the TYPESAFE_API_KEY environment variable (on this PC; the cloud container injected it automatically, a PC does not). If the key is missing, stop and tell me; do not fake a judgment.
Rules that the repo's judges already follow, and that any new judge must follow:
- TypeSafe only reads text and JSON. It cannot see images or meshes. Send it words, not numbers: bucket every measurement in code ("within the references", "much below", "past the fail limit"). Keep thresholds and arithmetic in code.
- One narrow question per judgment, all independent questions in one request.
- Phrase every question so that yes = good.
- Choice questions: include a "none" outcome and ask twice with the options in reversed order; if the answers differ, treat it as uncertain.
- Confidence: for a yes/no, confidence is |2p-1|; below 0.4 send it to a human (me) or to you, do not act on it.
- The numeric checks stay authoritative. TypeSafe can add a warning; it never clears a failure.
- Use TypeSafe to vet reference data before trusting it (vetting.py), to judge each region (region_judge.py, deform_judge.py, hair_judge.py, topology_judge.py), to rank design variants, and to classify archetypes. State absent traits too.

## 6. How to build an asset (every asset, in this order)
1. Measure the references first (landmarks, profiles); a missing landmark is SKIP, never guessed.
2. Model it in Blender 5.2 with Python scripts, save the script in blender/scripts or tools, and commit it.
3. Run the validators for that region, then the TypeSafe judge for that region, then the gate if it exists on your branch.
4. Render front, three-quarter and side views and compare them with the reference art I attach.
5. Fix the first problem TypeSafe and the numbers agree on, and repeat. Do not move on while a region fails.
6. Export the pack (glTF separate plus pack.json) and run the pack check and validate_gltf.js.
7. Tell me honestly what passed, what failed, what you could not measure, and what TypeSafe was unsure about.

## 7. Rules
- The app's built-in procedural bodies are placeholders. The Blender library is the real look. Do not spend effort polishing placeholders.
- Target style: Monster Hunter Stories 3 and the hunter key art I attach: about 6.3 to 6.7 heads, small almond eyes at about mid-head, tiny nose and mouth, defined jaw, short swept hair with a fringe, layered armour, flat two-tone toon shading with warm shadows and coloured outlines. A painted illustration cannot be copied exactly from numbers; match proportions, features and shading, and say what is left.
- The bands in the validators are heuristics calibrated on Hina, Amshani and synthetic limbs. When a real production model disagrees, tell me and propose a change; do not quietly bend the model to the band or the band to the model.
- Never claim something works unless you ran it. Report test output as it is.
- Commit with clear messages, push to the branch I name, and do not open a pull request unless I ask.

## 8. Prove it
Before modeling, reply with: (a) every skill and script you found, per branch, with one line each; (b) the overlaps between the branches; (c) how you will call TypeSafe and what you will do if the key is missing; (d) the order you will build the library in; (e) what you could not read. Then run python -m unittest discover -s tests/validators on the upbeat branch and show me the result. Wait for my go before you start modeling.
```

## Before you paste it
- The new chat needs the GitHub connector with access to `lightlabpro/AnimeCharacterCreator`, and a way to run Blender 5.2 on the PC (the Blender connection or the desktop app's computer use). Without a way to run scripts, ask it to give you each script to paste into Blender's Text Editor and to paste the output back.
- Set `TYPESAFE_API_KEY` on the PC (the key from your TypeSafe account) before the chat runs any judge.
- Other chats cannot be read by the new chat. Only what was committed is learned. The two branches above are the only places the skills live, so merge them (or tell the chat to read both, as the prompt does).
