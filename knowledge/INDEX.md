# Knowledge index

Read in this order. Both Claudes use the same files.

| File | What it is | Who maintains it |
| --- | --- | --- |
| `expected-contract.json` | Every shape key, performance key, socket and bone property the app drives, generated from the app source | Code (`python3 bridge/tools/export_contract.py`) |
| `../docs/CLAUDE_BUILD_PROMPT.md` | The asset library build prompt: phases, naming, sockets, gates | Both, through the inbox |
| `../docs/anatomy-manual.md`, `../docs/shading-style-guide.md` | Proportions and shading rules, with checklists | Chat proposes, Code mirrors them in the app |
| `../docs/style_dataset/`, `../docs/reference/mhs3/` | The reference images the validator compares against | Chat |
| `../reports/AI 3D generation pipelines.md` | How Meshy-style generators work, and what transfers to a validator. Sources were partly blocked, so confirmed vs inferred is labelled | Code |
| `../.claude/skills/render-validator/` | Quality gate for Blender renders | Code builds it, both calibrate it |
| `../.claude/skills/creator-bridge/` | How the two Claudes share memory | Both |
| `../bridge/LEARNINGS.md` | Append-only measurements and decisions | Both |
| `head-targets.json` | Reference head profile (fractions of head height) used by the head audit and the app's tests | Code, replaced by exact numbers when the chat measures the reference mesh |
| `../.claude/skills/head-shape-audit/` | Measures a head mesh against the reference and lists fixes | Code builds it, chat runs it |
| `../.claude/skills/character-gate/` | One gate over every validator, with cross-checks between them; writes gate_report.json | Code builds it, chat runs it on every export |
| `skill-graph.json` | Which skill feeds which (machine-checked by validate_skills.py) | Code |
| `../.claude/skills/ai-3d-pipeline/` | Staged character pipeline with a gate per stage | Both |
| `validator-calibration.json` | Where the validator's floors came from: data, ranges, findings and caveats | Code, re-run with calibrate.py when new data arrives |
| `../.claude/skills/ai-3d-pipeline/references/tripo.md` | What TripoSG, TripoSR and the Tripo Blender add-on teach: input preparation, seed and face budget, orientation (+Y vs our -Y), the add-on's localhost server | Both |
| `meshy-agent-lessons.md` | What Meshy's agent repo does well (tri-state checks, route choice, skill validation) and where it was applied | Code |
| `../.claude/skills/library-pack-check/` | Checks exported packs against the app contract; test-pack generator | Code builds it, chat runs it on every export |
| `head-targets-dataset.json`, `dataset-study.md` | Head and body bands measured from 18 real anime-style models (TexVerse sample, TypeSafe-ranked), with method and caveats | Chat (measure_dataset.py, dataset_bands.py) |
| `from-chat/` | Studies and measurements that live in the chat project (head ratios, hair clump stats, MHS3 video studies) | Chat |

## Quick facts
- The app reads packs from `library/humanoid/`, `library/robot/`, `library/full_beast/`, and refuses a pack that sits in the wrong tree.
- `pack.json` needs `id`, `display_name`, `library`, `slot`. A socket is optional but strongly advised for hair, accessories and elements.
- Export glTF as GLTF_SEPARATE. The loader breaks embedded .glb textures. Shape keys start at 0.
- If a name is missing from a pack, the app does not error: the slider or expression silently does nothing. Check the contract file first.
