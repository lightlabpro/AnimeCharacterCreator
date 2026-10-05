---
name: library-pack-check
description: Checks exported asset-library packs (glTF + pack.json + manifest.json) against the Anime Character Creator's contract before delivering them. Use after every export from Blender, before telling the user a pack is done, and whenever a pack imports but a slider, expression or accessory does nothing in the app. Catches wrong shape-key names, shape keys that do not start at 0, embedded textures, missing DEF- bones and SOC- sockets, wrong scale or origin, and library-tree mistakes.
---

# Library pack check

The app is a mixer that drives your pack by **name**. A pack that imports fine can still do nothing: a misspelled `ID-` key, shape keys that start above 0, textures packed inside a .glb, a body with no `DEF-` bones. This checks all of that without opening the app, and says exactly which name or file to fix.

## Run it
```
python3 scripts/check_pack.py <library root or one pack folder> --contract knowledge/expected-contract.json
```
(in the repo: `.claude/skills/library-pack-check/scripts/check_pack.py`). Pure Python, no Blender, no numpy. `--json report.json` writes the findings, `--strict` makes warnings fail.

Exit codes: 0 pass, **12 a check failed**, **13 something could not be measured** (never a pass), 2 usage. Findings are FAIL (the pack will not work), WARN (works but loses something), UNKNOWN (could not check), INFO (what it found).

## What it checks
| Area | FAIL when | Notes |
| --- | --- | --- |
| pack.json | `id`, `display_name`, `library`, `slot` missing; library not humanoid / robot / full_beast; duplicate id | same rules as the app importer |
| Folder | pack sits in the wrong library tree, or in a category folder the app does not know | humanoid, robot and full_beast never mix |
| manifest.json | entry library differs from pack.json; entry has no folder or no matching pack | an id mismatch or an unlisted pack is only a warning |
| glTF files | not valid glTF 2.0; buffer or texture is embedded (data URI, or textures inside a .glb); a referenced file is missing | export glTF **Separate** (.gltf + .bin + textures) |
| Shape keys | morph targets exist but `extras.targetNames` do not; names and targets differ in count; any default weight is not 0 | WARN for a key without `ID-`/`PF-`, or one the app does not read (it does nothing) |
| Body packs | no skin; no `DEF-` bones; no `SOC-` sockets; lowest point not at y=0 (feet on the floor); height outside 1.5-2.2 m (adult) or 1.0-1.6 m (child); triangles outside 500-120,000 | WARN outside the 18k-28k body budget; INFO for key coverage |
| Sockets | WARN: a body pack missing sockets listed in `docs/CLAUDE_BUILD_PROMPT.md`; an accessory whose `socket` no body provides and nothing documents | |
| Bounds | UNKNOWN when POSITION accessors have no min/max | enable "Include min/max" / use a standard exporter |

## What it cannot see
How the mesh deforms, edge-loop quality, shading, and whether the art is good. The `render-validator` and the `head-shape-audit` cover looks; a pose test covers deformation. A pass here means the app can find and drive everything in the pack, not that it is finished.

## Worked example and test packs
`python3 scripts/make_test_pack.py OUT_DIR` writes a small valid body pack (1.72 m, 19k triangles, 6 `ID-` keys, 4 `PF-` keys, all 38 documented sockets, skinned to `DEF-` bones). `--defect NAME` writes a broken one (embedded, nonzero_weights, no_targetnames, orphan_key, floating, tiny, no_bones, no_sockets, missing_bin, bad_library, no_slot). `--kind accessory --socket SOC-HeadTop` writes a hat. Compare your export's structure with it when a finding is unclear.

## In the loop
1. Export the pack. 2. Run `check_pack.py`. 3. Fix every FAIL and UNKNOWN, read the WARNs. 4. Only then run the visual gates. 5. Log the INFO coverage line (how many of the app's `ID-`/`PF-` keys the pack implements) with `bridge/tools/log.py`.

## Proven end to end
`node scripts/e2e_pack.cjs` (repo root, dev server running) imports a generated pack through the real Import button, applies it, and checks that "Round face" = 100 drives `ID-FaceRound` to 1, `PF-Blink` is driven by performance, and a hat attaches to the body pack's own `SOC-HeadTop`. If a pack passes this checker but a control still does nothing in the app, tell Code: it is an app bug.
