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
| `gltf.py` | nothing | Reads `.gltf`/`.glb`/VRM into the same snapshot Blender produces. VRM humanoid bone maps (0.x and 1.0) give exact joints with no name guessing. |
| `geometry.py` | numpy | PAniC-3D-style Chamfer and F1 between two meshes of the same character, mirror symmetry, and Meshy-style mesh health (non-manifold, degenerate, loose, floating fragments). |

## How TypeSafe is used

TypeSafe reads text/JSON only (yes/no, score and choice answers). It cannot see a mesh or an image, so it is given **numbers**, which is what a model's dimensions are.

1. **Dump** a reference model's dimensions: `profile_from_scene` (in Blender via `bpy_adapter.snapshot`, or `python -m blender.validators ref model.glb --kind adult --name hina`).
2. **Vet** it: `python -m blender.validators vet blender/references/profiles/adult-hina.json`. TypeSafe scores each metric three times (anatomically correct / acceptable stylised / consistent with the model's other numbers). A metric is kept if the mean is >= 0.5 and the manual band does not hard-fail it. Dropped metrics stay in the file but are ignored.
3. **Validate** new work against the vetted envelope. TypeSafe never overrides a deterministic FAIL. It can add a FAIL only when every threshold passed but it is confident (< 0.3) the figure is implausible.

Set `TYPESAFE_API_KEY` in the environment on your PC. Without it the judge and vetting skip and the deterministic checks still run.

## Landmarks

Place empties named `LM-<Name>` (`Crown, Chin, Floor, Nipple, Navel, Pubis, EyeInner_L/R, EyeOuter_L, EyeTop_L, EyeBottom_L, Mouth, HandTip_L, HeelBack_L, ToeTip_L`). Limb joints are read from `DEF-` bones named like `upperarm.L`, `forearm.L`, `hand.L`, `thigh.L`, `shin.L`, `foot.L`. `bpy_adapter.place_basic_markers()` makes Crown, Chin and Floor. The rest are judgement calls, so they are placed by hand. A missing landmark is reported as SKIP, never guessed.

## Hair

`hair.py`, `hair_judge.py`, `blender/scripts/analyze_hair.py` and the repo skill `.claude/skills/hair-validators/SKILL.md`. Clump statistics (count, vertices, thickness / width, width / head, taper, tube-like sides), UV islands, fit against the head (signed distance, cranium coverage, ear coverage when creature ears are equipped), length bucket and the build-prompt contract (hair socket, `NG_ToonHair`, volume and width controls, root / tip colour, highlight strength).

The measurement code was checked against the numbers the modeling skill recorded for Hina and reproduces them: 62 clumps, median 121 vertices, thickness / width 0.63 (skill: 0.64). Amshani's hair, isolated from its body mesh by material and head weight, has 16 clumps and thickness / width 0.43, so it reads weaker. TypeSafe agrees: it scored Hina's hair 3.3 and Amshani's 1.5 out of 4, with "too few clumps" as the first fix. Bands for taper, UV orientation and buried roots are calibrated on those two models and labelled as such in `hair.py`.

## Topology

`topology.py` + `blender/scripts/analyze_topology.py` check a mesh three ways and write a profile to `blender/references/topology/`:

- **Static:** quad/triangle/n-gon ratios, valence histogram and pole map, quad skew, aspect and planarity.
- **Loops:** edge loops circling the shoulder, elbow and knee against the manual's 3-5 / 2-4 / 4-6.
- **Deformation:** each joint is bent (shoulder 60, elbow 90, knee 90, hip 60 degrees, about local X and Z, both signs, worst kept) with linear blend skinning computed in numpy, normalised like Blender's armature modifier, and every shape key is applied at 1. Judged by the share of edges stretched past 2x or squashed under 0.5x, and the share of flipped faces; one isolated stretched edge is reported but does not fail. (Posing through the depsgraph did not update in headless `bpy`, so it is not used.)

`topology_judge.py` then asks TypeSafe, following its agent skill: word buckets instead of numbers, narrow questions all phrased so yes = good, one request, a "none" outcome and a second request with the choice options reversed, low confidence routed to a human. Measured on Amshani, TypeSafe and the numeric checks agree: shoulder/elbow/knee bend cleanly, the hip has a few flipped faces, the surface has too many triangles (77% quads), and the knee has 3 loops instead of 4-6. Hina has no armature, so only the static check applies (92% quads, sheared quads, many poles).

Thresholds for skew, aspect, planarity and the deformation shares are practical heuristics, not from the manual; the manual only fixes quads-throughout and the loop counts.

## What the reference repos taught

Studied with real data: both `XxAlonexX/blender-character` models were opened in headless Blender 5.2.2 (`pip install bpy`), and the code of `ShuhongChen/panic3d-anime-reconstruction`, `meshy-dev/meshy-3d-agent`, `VAST-AI-Research/TripoSG`, `TripoSR` and `tripo-3d-for-blender` was read.

- **Real rigs name bones differently.** Amshani uses `Left arm / Left elbow / Left wrist / Left Leg / Left knee`; Hina has no armature, only `DEF-` vertex groups. Bone patterns now cover Rigify, Mixamo/VRM and the plain names, and VRM maps are read directly.
- **References are in arbitrary poses.** Amshani is a T-pose. Arm checks now hang the measured limb lengths straight down from the shoulder, so they do not depend on pose; the A-pose angle only gates the new build and is skipped in reference comparison.
- **Meshes can include hair.** Amshani's single mesh has hair to z = 23.3, so a crown read from the mesh is the hair top, not the skull. `LM-Crown` and `LM-Chin` must be placed (a sidecar JSON works: `bpy_adapter.load_markers`); the validators report them missing instead of guessing.
- **Chamfer/F1 needs the same character.** PAniC-3D compares a reconstruction with its own ground-truth head. Use `geometry.fidelity_findings` for a retopo versus its generated source, never against an unrelated reference.
- **Hair and accessories are many shells.** Amshani's hair is 49 closed clumps in one mesh, so the floating-fragment check is skipped when `multi_part=True`.
- **Found by the new checks on the real files:** Hina's body has 30 non-manifold edges and Chamfer asymmetry 0.020; Amshani's has 43 non-manifold edges and its thigh/shin proportion sits outside the manual's band, which is why references go through vetting instead of being trusted.

## Reference markers and profiles (Hina, Amshani)

`blender/references/landmarks/{hina,amshani}.json` hold landmarks measured from the models' own geometry by `blender/scripts/estimate_reference_markers.py`; `_meta.methods` says how each was measured. `blender/scripts/make_reference_profile.py` turns them into `blender/references/profiles/adult-*.json`, which TypeSafe vetted (`vetted` field). Only kept metrics enter the reference envelope.

| | Hina | Amshani |
| --- | --- | --- |
| Faces | +Y (flipped to -Y on load) | -Y |
| Height | 6.72 heads, skull top to floor | 7.63 heads |
| Eye line | 0.39 H | 0.38 H |
| Measured from | mesh, vertex groups, eyeball and teeth objects | skin-material head shell, bones, Blink/viseme shape keys |
| Not measurable | Pubis (thighs touch), Navel, all joints (no armature) | Navel, Nipple (clothed) |
| Dropped by vetting | none | thigh/shin, foot/forearm, eye gap, eye proportions, neck width |

Caveats: these are estimates on low-poly meshes (crotch height is good to about 0.2 head); Hina's eye metrics come from eyeballs, so eye gap and eye proportions are excluded for her; bone-derived shoulder and hip widths are joint-centre distances, so they are shown but not graded unless `LM-shoulder_L/R` / `LM-hip_L/R` are placed at the outer points. Hina is 6.7 heads, the same as the MHS3 male figure in the manual, which is below the 7.0-7.5 adult band; decide whether the build target should be 6.7-7.5.

## TypeSafe usage rules (from docs.typesafe.ai)

The model is pinned to `jev-1.13.0`. Jev is weak at numbers, so it only ever sees named buckets ("slightly low", "far too high"); thresholds stay in code. Score answers below 0.4 confidence become a "needs a human or Claude look" note instead of a verdict. Limits: 32k tokens of state plus the longest question, 64k per request.

## Limits

- The 2D images in `docs/reference/mhs3/` and `docs/style_dataset/` are in-game screenshots with backgrounds, not orthographic sheets. They inform the rubric and bands; silhouette overlap needs clean front/side images with a plain or transparent background.
- `bpy_adapter.py` snapshot, mesh extraction and the geometry checks were run against real Blender 5.2.2 (the `bpy` module) on Hina and Amshani. The slider sweep (`bpy_adapter.sweep`) and `place_basic_markers` were not exercised yet. The pure checks, glTF/VRM reader, vetting and judge are unit-tested (`npm run test:validators`) and the TypeSafe calls were confirmed live.
- Face-metric bands come from the manual and the Hina/Amshani measurements; where they disagree the band covers both (see `spec.py` sources). Tighten them once vetted reference profiles from your own models exist.
