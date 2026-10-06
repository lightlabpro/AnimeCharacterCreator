# Validators

Checks that run **inside Blender 5.2** (Text Editor or `blender -b file.blend -P blender/scripts/run_validators.py -- adult tag`) and also outside it on glTF exports. They compare a character against the anatomy manual, the build-prompt contract, and measured reference models, and they use TypeSafe to vet the references and grade the result.

## What runs where

| Layer | Needs | What it does |
| --- | --- | --- |
| `spec.py` | nothing | Every anatomy target as a ratio with its denominator, band, source and fix hint. |
| `measure.py`, `checks.py` | nothing | Landmarks to metrics to pass/warn/fail. Contract: objects, `SOC-` sockets, `ID-`/`PF-` keys, `DEF-` bones, triangle budgets, transforms, origin, facing. |
| `reference.py` | nothing | Compare against the min/max envelope of reference profiles for that body kind. |
| `vetting.py` | TypeSafe | Three TypeSafe passes over each reference profile. Only confirmed metrics are kept. |
| `judge.py` | TypeSafe | After the checks, grades the measured report and names what to fix first. |
| `silhouette.py` | numpy | Front/side silhouette overlap plus where (head, shoulders, hips...) the shapes differ. |
| `sweep.py` + `bpy_adapter.sweep` | Blender | Every key/length at 0, 0.5, 1. |
| `packs.py` | nothing | `library/` against the importer's rules, `manifest.json`, glTF presence, no trademarked names. |
| `gltf.py` | nothing | Reads `.gltf`/`.glb` into the same snapshot Blender produces. |

## How TypeSafe is used

TypeSafe reads text/JSON only (yes/no, score and choice answers). It cannot see a mesh or an image, so it is given **numbers**, which is what a model's dimensions are.

1. **Dump** a reference model's dimensions: `profile_from_scene` (in Blender via `bpy_adapter.snapshot`, or `python -m blender.validators ref model.glb --kind adult --name hina`).
2. **Vet** it: `python -m blender.validators vet blender/references/profiles/adult-hina.json`. TypeSafe scores each metric three times (anatomically correct / acceptable stylised / consistent with the model's other numbers). A metric is kept if the mean is >= 0.5 and the manual band does not hard-fail it. Dropped metrics stay in the file but are ignored.
3. **Validate** new work against the vetted envelope. TypeSafe never overrides a deterministic FAIL. It can add a FAIL only when every threshold passed but it is confident (< 0.3) the figure is implausible.

Set `TYPESAFE_API_KEY` in the environment on your PC. Without it the judge and vetting skip and the deterministic checks still run.

## Landmarks

Place empties named `LM-<Name>` (`Crown, Chin, Floor, Nipple, Navel, Pubis, EyeInner_L/R, EyeOuter_L, EyeTop_L, EyeBottom_L, Mouth, HandTip_L, HeelBack_L, ToeTip_L`). Limb joints are read from `DEF-` bones named like `upperarm.L`, `forearm.L`, `hand.L`, `thigh.L`, `shin.L`, `foot.L`. `bpy_adapter.place_basic_markers()` makes Crown, Chin and Floor. The rest are judgement calls, so they are placed by hand. A missing landmark is reported as SKIP, never guessed.

## Limits

- The 2D images in `docs/reference/mhs3/` and `docs/style_dataset/` are in-game screenshots with backgrounds, not orthographic sheets. They inform the rubric and bands; silhouette overlap needs clean front/side images with a plain or transparent background.
- `bpy_adapter.py` has not been run against a real Blender 5.2 here (no Blender in the cloud container). The pure checks, glTF reader, vetting and judge are unit-tested (`npm run test:validators`) and the TypeSafe calls were confirmed live.
- Face-metric bands come from the manual and the Hina/Amshani measurements; where they disagree the band covers both (see `spec.py` sources). Tighten them once vetted reference profiles from your own models exist.
