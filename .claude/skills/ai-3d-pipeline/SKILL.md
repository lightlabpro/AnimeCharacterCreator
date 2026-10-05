---
name: ai-3d-pipeline
description: How to build or fix a stylized 3D character the way the AI 3D generators (Meshy, Tripo, Hunyuan3D, TRELLIS, Rodin) are structured, as a staged pipeline with a check after every stage. Use when starting a character, when a model looks wrong and you do not know which stage failed, or when deciding whether to use an AI generator for a blockout. Based on the research report in reports/AI 3D generation pipelines.md.
---

# Staged 3D character pipeline (what the generators teach)

Production generators are not one model. They are stages: shape, then texture, then optional retopology, then rig. Each stage has its own failure modes and its own check. Do the same by hand: never fix a later stage while an earlier one is wrong.

Confidence: the staged structure is well sourced for the open systems (Hunyuan3D, TRELLIS, TripoSG). For Meshy itself only press-level facts exist; treat its internals as inference. Anime characters are the weak spot for every generator (small VRoid-based training sets, baked realistic shading), so assume human cleanup.

## Stages and gates
| Stage | Output | Gate before moving on | Skill / tool |
| --- | --- | --- | --- |
| 0 References | front/side/three-quarter sheet, reference head | references agree with each other on proportions | `anthropic-skills:anime-character-modeling` |
| 1 Blockout | whole-body volumes at correct proportions (7-7.5 heads adult) | silhouette overlay on the reference sheet | `render-validator` (silhouette IoU) |
| 2 Head form | skull, jaw, nose, sockets, ears | `head-shape-audit` prints HEAD_SHAPE_OK | `head-shape-audit` |
| 3 Topology | quads around eyes, mouth, joints; hair and clothes as separate shells | loops visible in a wire render, deformation test | `anime-character-modeling` |
| 4 UV and texture | face UV island, iris island, shade masks | no stretching, seams away from the face | `anime-character-modeling` |
| 5 Toon shading | hard ramp, warm shadow tint, outlines | `render-validator` PASS on front, three-quarter, side, face | `render-validator` |
| 6 Rig and shape keys | `DEF-` bones, `ID-` and `PF-` keys | names exist in `knowledge/expected-contract.json`; pose test | `creator-bridge` |
| 7 Export | glTF separate files, `pack.json` | the creator imports it and the slider moves it | `creator-bridge` |

## Rules that come from how the field evaluates 3D
- **Fixed views.** Evaluate from the same cameras every time (front, three-quarter, side, back, face). Moving the camera hides defects.
- **Several independent signals.** One score gets gamed. Use geometry audit, image metrics and a separate reviewer together.
- **Defects first.** Ask for a list of defects with evidence before any score.
- **Stage-local fixes.** A shading problem that a form fix would solve is not a shading problem.
- **Pose stress.** Static renders hide skinning collapse. Before export, pose the arms, neck and jaw once.

## Using an AI generator in the loop (optional, be honest about it)
A generator is useful for a fast blockout or a reference silhouette, not for the final asset: topology is not deformation-ready for faces, textures carry baked lighting, hands and hair are weak, and rigs assume a T or A pose with no face rig. If you use one: generate from a clean turnaround sheet, import only as a reference, retopologise by hand, and send it through the same gates. Licence of the output and of the training data are the user's call; never assume it is safe for commercial use.

## Log it
Every stage that fails a gate teaches something. Log the measured cause, not the fix you tried first, with `python3 bridge/tools/log.py` (see `creator-bridge`).
