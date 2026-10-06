---
name: ai-3d-pipeline
description: How to build or fix a stylized 3D character as a staged pipeline with a gate after every stage, using what the AI 3D generators (Meshy, Tripo, Hunyuan3D, TRELLIS) and Meshy's agent skills do. Use when starting a character, when a model looks wrong and you do not know which stage failed, when choosing the shortest route for a request, when deciding whether to use an AI generator for a blockout, or before rigging or export.
---

# Staged 3D character pipeline

Production generators are stages (shape, texture, optional retopology, rig), and each stage has its own failure modes and its own check. Do the same by hand. Never fix a later stage while an earlier one is wrong, and never spend effort (or money) on a stage whose input has not passed its gate.

Provenance and confidence: the staged structure is well sourced for open systems (Hunyuan3D, TRELLIS, TripoSG) in `reports/AI 3D generation pipelines.md`. The routing rules, limits and preconditions below come from Meshy's public agent skills (`meshy-dev/meshy-3d-agent` 0.6.0, Meshy CLI 0.4.0), which describe how to drive Meshy, not how its models work. Meshy's model internals remain unpublished.

## Read what this request needs
| Need | Reference |
| --- | --- |
| Pick the shortest route for a request, reuse what exists | [routes](references/routes.md) |
| Limits and preconditions before texturing, UV, rigging, export | [preconditions](references/preconditions.md) |
| Decide whether to use Meshy for a blockout, and how to spend safely | [meshy](references/meshy.md) |
| Use TripoSG, TripoSR or the Tripo cloud/Blender add-on for a blockout, prepare the input, reduce the result | [tripo](references/tripo.md) |

## Stages and gates
| Stage | Output | Gate before moving on | Skill / tool |
| --- | --- | --- | --- |
| 0 References | front/side/three-quarter sheet, reference head | views agree on proportions; any image sent to a generator passes `scripts/prepare_reference.py` (exit 0) | `anthropic-skills:anime-character-modeling` |
| 1 Blockout | whole-body volumes (7-7.5 heads adult) | silhouette overlay on the sheet | `render-validator` |
| 2 Head form | skull, jaw, nose, sockets, ears | `head-shape-audit` prints HEAD_SHAPE_OK | `head-shape-audit` |
| 3 Topology | quads around eyes, mouth, joints; hair and clothes as separate shells; a generated mesh is first brought to budget with `scripts/decimate_to_budget.py` (before any shape keys) | `mesh_stats.py` passes (tri budget, no non-manifold, no zero-area) and loops are visible in a wire render | `render-validator` |
| 4 UV and texture | face UV island, iris island, shade masks | no stretching, seams away from the face | `anime-character-modeling` |
| 5 Toon shading | hard ramp, warm shadow tint, outlines | `render-validator` PASS on every required view | `render-validator` |
| 6 Rig and shape keys | `DEF-` bones, `ID-` and `PF-` keys, `SOC-` sockets | names in `knowledge/expected-contract.json`; `check_pack.py`; pose test | `library-pack-check` |
| 7 Export | glTF separate files, `pack.json`, `manifest.json` | `check_pack.py` prints PACK_CHECK_OK, then the creator imports it and a slider moves it | `library-pack-check` |

## Rules (each one is something Meshy's skills enforce, adapted)
1. **Shortest route.** Do only the stages the request needs. A request for a prop does not need a rig. A flat-colour model does not need a PBR pass.
2. **Reuse before regenerate.** A follow-up ("a lower poly version", "now with the other hair") edits or derives from the existing asset and runs only the missing step. Rebuilding from scratch is the wrong answer.
3. **Gate on measurements, and unknown is not a pass.** If a count, a view or a stat was not measured, the stage is UNKNOWN. Say so. Never write "looks fine" over something nobody checked.
4. **A render proves little about structure.** An image cannot show edge-loop flow, deformation, watertightness or polygon count. State what the check did not cover. Missing preview: say it was not visually checked.
5. **Ask before a new cost.** Work inside the agreed plan proceeds. A new paid stage, a second variant or a rerun after a disappointing result needs the user's yes first. Estimates come only from a stated source, and the real charge is reported afterwards, or reported as unknown, never assumed zero.
6. **Unknown outcome: reconcile, do not repeat.** If a submission may have gone through (a lost response, a timeout), look for the existing result before submitting again. A timeout is not a failure.
7. **Keep the trail.** Record the stage name, the source asset and the check results for every iteration, so the next request is cheap and nothing is rebuilt blindly. The validator's `--stage` tag and `bridge/LEARNINGS.md` are that record.

## Log it
A failed gate teaches something: log the measured cause, not the fix you tried first, with `python3 bridge/tools/log.py` (see `creator-bridge`).
