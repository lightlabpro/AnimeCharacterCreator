---
name: character-gate
description: Runs every character check on the same exported file and makes the validators check each other. Use before telling the user a body or pack is done, after any export from Blender, and whenever one validator says pass but something still looks wrong. It runs pack-check, anatomy rules, pose stress, the slider sweep and the proportion audit, folds in the head audit, mesh stats and render manifest, cross-checks sockets against the skeleton and heights, triangle counts and shape keys between tools, and writes gate_report.json that the render-validator requires before it can pass a render.
---

# Character gate: one verdict, validators that audit each other

Each skill measures one thing. A pass from one means little if the others disagree or were never run. The gate runs them all on the **same file**, compares what they independently measured, and writes one report with a tri-state verdict. A skill that is not installed or a check that could not run is **UNKNOWN, never a pass**. This skill needs the validators it calls installed beside it: `library-pack-check`, `body-proportion-audit`, `head-shape-audit` (its JSON file) and `render-validator`.

## Run it
```
python3 .claude/skills/character-gate/scripts/run_gate.py library/humanoid/bodies/<pack> \
    --contract knowledge/expected-contract.json --targets knowledge/body-targets.json \
    --head-audit head_audit.json --mesh-stats mesh_stats.json --manifest r_manifest.json --out gate_report.json
```
`PATH` is a pack or library folder (the pack check runs too) or one `.glb`. Exit 0 pass, 12 fail, 13 unknown, 2 usage. `--require head_audit mesh_stats manifest` makes a missing file UNKNOWN instead of ignored. `--skip NAME` skips a check **and says so in the report**.

## What it runs
| Check | Source skill | Catches |
| --- | --- | --- |
| `pack_check` | `library-pack-check` | contract names, tree, counts, bounds, pose clips |
| `anatomy_rules`, `pose_stress`, `slider_sweep`, `body_proportions` | `body-proportion-audit` | rig and weight errors, bad deformation, broken shape keys, wrong proportions |
| `head_audit` | `head-shape-audit` | head form (from its `head_audit.json`) |
| `mesh_stats` | `render-validator` | triangle budget, non-manifold edges, loose parts |

## Cross-checks: the tools validating each other
| Check | Compares | A failure means |
| --- | --- | --- |
| `height_bounds` | glTF accessor bounds (`check_pack.py` code) vs the loader's mesh height | transforms are applied differently: one tool measures a different mesh than the other |
| `triangle_count` | glTF header vs loader vs `mesh_stats.json` | stale stats file, or a loader bug |
| `shape_keys` | target names in the glTF vs targets the loader found | names lost or sparse accessors misread |
| `sockets_vs_joints` | `SOC-` nodes vs the skeleton (head top above head, hand sockets at hands) | sockets present but in the wrong place: the pack check passes them, the app puts equipment in the air |
| `def_prefix` | bones the anatomy rules matched vs the contract's `DEF-` prefix | rig is anatomically fine but the app will not drive it |
| `head_vs_body` | head audit head height vs the body's neck-to-top height | the two audits looked at different meshes or units |
| `manifest_height` | renders' `character_height` vs this mesh | renders show a different model than the file being checked |

Tolerances are GUESSES (height 3%, triangles 1%, renders 5%, socket distances 12-20% of body height); tighten them when data allows.

## How the render-validator uses it
`validate.py init ... --require-gate` makes a missing report UNKNOWN. `validate.py measure ... --gate-report gate_report.json` fails the iteration when the gate failed (so **no render can pass over a structurally broken mesh**), is UNKNOWN when the gate was, and fails when the gate's triangle count or height disagrees with `mesh_stats.json` or `r_manifest.json` (the renders belong to a different mesh). The report records the mesh's sha256 and each iteration stores it.

## When it fails
Fix the first failing check named in the report, re-export, re-run; never edit the report or skip a failing check to pass. Log a measured cause with `python3 bridge/tools/log.py` (see `creator-bridge`).
## Scope
Structure, rigging, weights, deformation at fixed poses, names, counts, heights and sockets. Not art quality, hand detail, facial rigging or self-intersection.
