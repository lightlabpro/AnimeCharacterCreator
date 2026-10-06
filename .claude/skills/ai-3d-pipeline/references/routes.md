# Pick the route from the intent

Source for the generator limits: Meshy agent skills 0.6.0 (Meshy CLI 0.4.0), `skills/meshy-3d-generation/references/pipelines.md`. Limits can change; re-check the vendor's current docs before relying on a number for a purchase.

| What is wanted | Route | Notes |
| --- | --- | --- |
| A character that matches a reference sheet | hand-model (stages 0-7) | the default for this project's asset library |
| A fast blockout or silhouette study | concept sheet, `prepare_reference.py`, then image-to-3D as a **reference only** (optional: [meshy](meshy.md) cloud, or [tripo](tripo.md): TripoSG/TripoSR on a local GPU, or the Tripo API) | retopologise by hand; topology is not deformation-ready |
| A low-poly or game-ready variant of a model that exists | derive from the existing model: decimate or retopo the existing mesh, keep the original | never rebuild; Meshy's smart topology covers 100-15000 triangles, remesh 100-300000 |
| A lower-poly LOD chain | one derivation per level, from the existing model | each level is a separate output of the same source |
| A different format or size | export or scale the existing asset, one step | Meshy resize works in metres, e.g. 0.15 is 15 cm |
| A new colour or look | retexture the existing model | keep the UVs when you only change colour |
| A character that must move | textured humanoid in A or T pose, then rig | see [preconditions](preconditions.md) |
| Motion for a rigged character | use the clips the rig step already provides (walk, run) before building a custom one | Meshy's rigging bundles walking and running |
| A standalone motion clip | text-to-motion style tools produce a skeleton clip of 2-10 s (0.5 s steps); it does not animate your rigged character | |

## Reference images for any generator or for your own modeling
- One clean reference with the whole subject visible. Several views must show the same subject consistently, front, side and back.
- For a humanoid that will be rigged, ask for an A-pose from the start (Meshy exposes a pose-mode option). It cannot be fixed cheaply later.
- A 2D character concept can be turned into a multi-view A-pose sheet first (Meshy's text-to-image and image-to-image support multi-view). Treat that as an optional, approved pre-step, never inserted silently.

## Follow-ups
"Make it lower poly", "now as FBX", "scale it to 150 mm", "rig the one from before" mean: find the existing asset and run only the missing step. Look in this order and stop at the first confident match: this conversation, the validator workspace (`state.json` lineage and `--stage` tags), `bridge/LEARNINGS.md`, then ask with candidates listed. A missing index is a lookup problem, not a reason to regenerate.
