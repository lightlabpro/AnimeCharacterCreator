# Preconditions before an expensive stage

Check the input first, in this order. A stage with a failed or unknown precondition does not run.

## Texturing and UV
- UV unwrap on Meshy needs GLB and at most 40,000 faces. For our own meshes, unwrap only after `mesh_stats.py` reports no non-manifold edges, no zero-area faces and no loose parts beyond the plan.
- The face has its own big UV island, unwrapped straight on, and the iris its own island (see `anthropic-skills:anime-character-modeling`).

## Rigging
Meshy's rigging accepts a **textured humanoid with clear limbs**, preferably in an A or T pose, at most 300,000 faces. Use the textured model, not an untextured preview. A face count alone does not prove the geometry and texture are suitable; look at the model too.

For this project add: relaxed A-pose with palms inward and fingers slightly curled, origin at the floor between the feet, forward -Y, up Z, 1 unit = 1 m, transforms applied (see `docs/CLAUDE_BUILD_PROMPT.md`). Bones are `DEF-`, sockets `SOC-`, shape keys `ID-` and `PF-`, and every name must be in `knowledge/expected-contract.json` or it does nothing in the app.

Known rigger weak spots to test by posing once: hands and fingers, neck, hair, skirts and capes, face (no tool in the sources produces a facial rig).

## Before sending an image to a generator
Run `scripts/prepare_reference.py`: exit 0 means one isolated, uncut, large-enough subject on a flat background. 12: fix the image (margin, size). 13: the background is busy, remove it first. Never send an image whose status is unknown and call a bad result the generator's fault. Fix the seed and write it down with the asset.

## Before decimating a generated mesh
Merge close vertices first, then collapse to the budget (`scripts/decimate_to_budget.py`). The mesh must have **no shape keys** (Blender cannot decimate them): reduce the base mesh, then add `ID-`/`PF-` keys. Protect the face and hands with a vertex group. Decimation is not retopology: edge flow around eyes, mouth and joints is still hand work.

## Tri-state results
Every precondition is **pass, fail or unknown**.
- Pass: measured and within the limit.
- Fail: measured and outside it. Fix, do not proceed.
- Unknown: not measured (no stats file, no snapshot, an external mesh with no count). Unknown is not a pass. Do not "make it go away" by submitting speculative work; get the evidence.

The render-validator uses these meanings: exit 0 pass, 12 failed, 13 unknown.

## Previews
A rendered preview shows subject, completeness and obvious missing texture. It does not show back-face topology, watertightness, edge flow, deformation or polygon count. Never call a render a "3D preview" or imply it checked those things.
