# What the Tripo repos teach (TripoSG, TripoSR, Tripo Blender add-on)

Provenance: read from the source of `VAST-AI-Research/TripoSG`, `TripoSR` and `tripo-3d-for-blender` (MIT licensed code, checked at the time of writing). Nothing here was run: this environment has no GPU and the model weights were not downloaded. Numbers marked (source) are literal defaults in the code; anything about price or API behaviour is (client-side) and may be out of date, so check the vendor docs before spending.

## What they are
| Repo | What it does | Needs |
| --- | --- | --- |
| TripoSG | Image to 3D shape. A rectified-flow transformer (1.5B parameters, 2048 latent tokens) denoises a latent decoded by an SDF VAE, then marching cubes. Also a scribble+prompt variant (512 tokens, CFG-distilled) for fast prototyping from a sketch. Shape only, no texture | CUDA GPU, 8 GB VRAM; weights from Hugging Face, RMBG-1.4 for background removal |
| TripoSR | Fast feed-forward image to 3D (Large Reconstruction Model, triplane NeRF). Vertex colours, or a baked texture atlas with `--bake-texture` (xatlas UVs) | about 6 GB VRAM; marching cubes resolution 256, threshold 25 (source) |
| Tripo Blender add-on | Cloud API client inside Blender: text, image or multiview to model; also a small local socket server that lets an outside agent drive Blender | internet and a Tripo API key (never commit or paste one) |

## Input preparation (adopted: `scripts/prepare_reference.py`)
Both open models spend effort on the input image, because that decides the result more than any setting:
- **One subject, isolated, centred, square.** TripoSR crops to the subject's bounding box, pads to a square and scales it so the subject is 0.85 of the canvas (source); TripoSG pads 10% a side (source).
- **Flat neutral background.** TripoSR composites on grey 0.5, TripoSG on white. The model must not see scenery or text.
- **Trust alpha only when it is real:** TripoSG treats an alpha channel as a cut-out only if at least 1% of pixels are near 0 and 1% near 255; otherwise it runs RMBG-1.4 and cleans the mask (Otsu threshold, remove components under 200 px).
- Cap the long side at 2000 px; reject a pure black image.
Run `scripts/prepare_reference.py ref.png --out ref_prepared.png`. Exit 0 usable, 12 not usable (subject cut off by the image edge, too small, empty), 13 unknown (busy background that cannot be separated: remove it first, never guess). This is the same tri-state as every other gate here.

## Settings that matter (TripoSG source defaults)
- `seed` (42): fix it and log it; the same image with a new seed is a different model. Keep the seed with the asset.
- `num_inference_steps` 50, `guidance_scale` 7.0.
- `--faces N`: **not a generation setting.** After the mesh exists TripoSG merges close vertices, then quadric edge collapse to N faces. `scripts/decimate_to_budget.py` does the same inside Blender, with a protected vertex group for the face and hands.

## What comes out, and what it still needs here
- A marching-cubes isosurface: dense, uneven triangles, no UVs, no edge flow, no rig, closed even where the character is not (thin cloth and hair become thick shells). It is a blockout, not a deliverable. Our gates still apply: decimate, retopologise by hand around eyes, mouth and joints, unwrap, rig, then `head-shape-audit`, `body-proportion-audit`, `check_pack.py`.
- Decimate **before** adding shape keys: Blender cannot apply a Decimate modifier to a mesh with shape keys.
- Generated proportions come from the image. Verify them before building on the mesh; a pretty silhouette can still have wrong legs or head size.

## The Tripo cloud API (as the add-on calls it; client-side, unverified)
- `model_version`: v3.0-20250812, v2.5-20250123, v2.0-20240919, v1.4-20240625 in the add-on. Multiview (front, left, back, right; any may be missing) is gated to v2.* in the operator code even though the UI offers it on v3: check the docs.
- `face_limit` 1000-2000000, adaptive when unset; `quad=True` gives quad output and a default 10000 faces when no limit is set; `pbr=True` forces texture on; `texture_quality` and `geometry_quality` standard or detailed; `auto_size` scales to metres; `orientation=align_image` rotates to match the image; `style` presets (for example `person:person2cartoon`) are not for an asset that must match a reference sheet.
- The add-on's own price estimate is a client-side formula (10 base, plus extras per option); do not quote it as a price. Use the same rules as `meshy.md`: estimate from a stated source, ask before each new paid step, report the real charge, reconcile an unknown outcome instead of resubmitting.
- **Orientation:** the add-on imports models facing **+Y** (changed in 0.6). This project's contract is forward **-Y**, up Z: rotate 180 degrees about Z after import and apply transforms. Import in Object mode only (it lost models otherwise).

## The add-on's local server (relevant to driving Blender from an agent)
`server.py` runs a JSON-over-socket server on `localhost:9876` (commands: `get_scene_info`, `get_object_info`, `create_object`, `modify_object`, `delete_object`, `set_material`, `render_scene`, `execute_code`, Poly Haven asset search, and `import_tripo_glb_model`). Facts that matter:
- `execute_code` runs arbitrary Python inside Blender: bind to localhost only and use it only with an agent you trust.
- `localhost` is the user's PC. A cloud Claude Code session cannot reach it; a session running on the PC, or a client with a linked-computer connection, can. Our own checks do not need it: they run on exported files (`body_audit.py`, `anatomy_rules.py`, `pose_stress.py`, `check_pack.py`) or inside Blender with `blender -b -P`.

## Where each lesson landed
Input gate: `scripts/prepare_reference.py` and stage 0 of `SKILL.md`. Budget reduction: `scripts/decimate_to_budget.py` and stage 3. Seed logging and decimate-before-shape-keys: `preconditions.md`. Orientation and the localhost caveat: this file.
