---
name: parts-workflow
description: Sammy's part-by-part AI character route (q41, from Stefan 3D's free AI workflow) - Midjourney reference sheets on Discord (Basic plan), Hunyuan 3D 3.1 multi-view generation in Firefox on Sammy's PC, assembly and fixes in a fresh Blender 5.2 project, TypeSafe judging every stage, Kimi as a free second opinion, Unity toon setup last. Parts in a fixed order - head (hair, eyes, eyebrows, mouth, ears, nose, facial hair), torso, arms/hands, legs/feet. Use for every step of building the MHS3-style character this way; never spend money.
---

# Parts workflow (Midjourney -> Hunyuan 3D -> Blender 5.2 -> TypeSafe -> Unity)

Sammy, q41 (2026-10-25): "Create the assets with references using midjourney, passing them onto hunyuan, then
exporting to blender and fixing up in blender using typesafe. Remember to use the mhs3 character art style as
reference. Make sure you set up this workflow as skills and instructions so you dont deviate. ... focus on the head
first (hair, eyes, eyebrows, mouth, ear, nose, facial hair), then torso, arms/hands and legs/feet. Do not do anything
that costs me money or purchase anything, this is completely forbidden."

Source: Stefan 3D, "Ultimate Free AI Workflow for Anime 3D Character" (youtube ibMxfcNh_oY). What it teaches and how
it maps onto our tools: [video notes](references/video_notes.md). Prompts and per-part sheet specs:
[part specs](references/part_specs.md).

## Hard rules (read every session, before any click)
1. **No money, ever.** Never click Subscribe, Upgrade, Buy, Top up, Pro, "Get more credits", a paid export (the
   video's FBX export in Modddif is Pro-only - not ours), a free trial that asks for a card, or anything with a price.
   If a free quota runs out, stop and tell Sammy. Never enter payment details.
2. **Midjourney Basic budget.** Basic has limited fast GPU time and no Relax mode. Generate only what the current part
   needs: one prompt per sheet, re-roll at most twice, upscale only the chosen tile, never batch variations. Log every
   job (prompt, job id, chosen tile) in `docs/qa/parts/log.md` so nothing is generated twice.
3. **Hunyuan 3D quota.** Use the free credits shown on screen. Read the counter before Generate; one generation per
   part, a second only after a measured failure of the first. 500K faces is enough (the video's setting).
4. **Order is fixed.** `scripts/parts_state.py` holds the state. A part starts only when the part before it is
   `passed` or Sammy skipped it. Every face/head element is its OWN OBJECT (Sammy q41b: "the face elements are
   supposed to be separate, as it is intended in the project ... hair, eyes, eyebrows, hair, ears, mouth, teeth,
   facial hair"). Order: `head_base` (bare head: skull, face skin, nose; NO ears, NO painted eyes/brows/mouth; eye
   and mouth openings cut in Blender), then hair, eyes, eyebrows, ears, mouth, teeth, facial hair.
   Then torso, arms_hands, legs_feet, then assembly, texture, rig, toon, unity.
5. **TypeSafe judges, not my eye.** Every gate below is a TypeSafe call with images on. Never print the key. If the key
   is missing, stop and tell Sammy; never fake a judgment. Kimi may give a free second opinion or draft a prompt; it
   never overrides TypeSafe, and Sammy's picks override both.
6. **Head changes run the master loop.** Once a head part is in Blender, every change to it goes through
   `mhs3-master-loop` (mesh rules, render with the locked `vroid_toon.py`, `mhs3_validate.py`, `face-gate`, strict A/B
   gate). Nothing reaches Sammy without those passes. Never widen a tolerance; unmeasured is never a pass.
7. **Downloads.** Saving a generated image or a Hunyuan GLB to Sammy's PC is a download: ask once per session for the
   whole workflow ("may I download the Midjourney sheets and Hunyuan GLBs this workflow makes into
   `datasets_work/parts/`?"), then keep to that folder.
8. **Style.** MHS3 character art (Leo, Leia, Rudy, Eleanor in `docs/reference/mhs3/`), not an exact copy of Leo. Read
   `knowledge/mhs3_face_rules.json` lessons before writing a head prompt (no shrunk eyes, no lash tail, no tilted
   Egyptian opening, no lid glare).

## head_base lessons (q41b, measured)
- A head generated from a sheet with painted eyes/brows/mouth carries those features as RELIEF in the geometry
  (brow ridges, eye rings, mouth slit, hairline ridge - visible only with studio/cavity light, Workbench). Cleaning it
  in Blender failed: Laplacian / Taubin keep it, coarse voxel and collapse-decimation keep it or add holes, a smoothed
  cage turns the head into a blob. Generate head_base from a BLANK-face sheet instead.
- Judge geometry with Workbench STUDIO light + cavity renders, never the flat-lit texture render (it hides the form).
- The TypeSafe anime check does not apply to a featureless sheet (every score low, culprit hair). Blank head sheets
  are judged by silhouette IoU (`scripts/sil_iou.py`) against the accepted MHS3-proportion sheet 10a851d2: must be
  at least as close as the earlier accepted sheet ce6f3794 was (front .915, side .906, back .904) minus 0.03.
  112daf18 tile 0: .887 / .907 / .931 -> used. cf30a9c8 (mannequin, realistic): .58 / .76 / .58 -> rejected.

## Face elements: which route (q41b)
| Element | Object | Route | Why |
|---|---|---|---|
| head_base | `HEAD_Base` | Midjourney blank-face sheet -> Hunyuan -> Blender (cut eye + mouth openings, decimate) | the generator paints eyes/mouth into one mesh otherwise (v1/v2 had them baked in) |
| hair | `HAIR_*` | Midjourney hair sheet on a grey head -> Hunyuan -> Blender shell fitted to `HEAD_Base` | large shape, generator-friendly (video) |
| eyes | `EYE_L/R` (white, iris, lash line) | built in Blender (eyeball + iris/lid texture), Midjourney sheet as the design reference | too small and layered for a generator; rulebook eye standard (R1-R4, E1-E9, ES1-ES2) |
| eyebrows | `BROW_L/R` | built in Blender (ribbon), Midjourney reference | thin strip |
| ears | `EAR_L/R` | Midjourney ear sheet -> Hunyuan -> Blender, mirrored like the video's hands, joined at a hidden seam | generator-friendly shape |
| mouth | `MOUTH` (lips line, interior) | built in Blender, Midjourney reference | thin / interior |
| teeth | `TEETH_Upper/Lower` | built in Blender | hidden interior |
| facial hair | `FACIAL_HAIR` (empty slot, `SOC-Beard`) | none unless Sammy asks | contract: extra object |
Object names: final names follow the contract when packed (`knowledge/expected-contract.json`); these working names are only for the Blender project.

## Stages per part
| # | Stage | Tool | Gate (must pass to move on) |
|---|---|---|---|
| 1 | Reference sheet | Midjourney in Discord (`/imagine`, `--ar`, `--sref`/`--cref` with an MHS3 image URL from the repo) | `prepare_reference.py` exit 0 on each view; TypeSafe `typesafe_anime_check.py` says the sheet reads as MHS3 (above the rulebook threshold) and the views agree (front/side/back same proportions) |
| 2 | 3D generation | Hunyuan 3D 3.1, multi-image, in Firefox on the PC (computer use) | GLB downloaded; `mesh_stats.py` (no non-manifold flood, faces under budget after decimation); TypeSafe compares a neutral render to the sheet (`typesafe_faithful_check.py`) |
| 3 | Blender import and fix | Blender 5.2 new project (Blender MCP); sculpt fixes = mask slice + fill holes, elastic grab, smooth, mirror after origin to cursor and Ctrl+A | part-specific checks below; for head parts the master loop |
| 4 | Assembly | Blender: join parts at hidden cuts (cut the body arm where the new hand slides in, hide seams inside) | `body-proportion-audit` on the assembled body; head re-runs face gate |
| 5 | Optimise | `<ai-3d-pipeline>/scripts/decimate_to_budget.py` (skill `ai-3d-pipeline`) (video budgets: head 15K, body 20K, hands 10K tris) with a baked normal map | `mesh_stats.py` within budget, render-validator PASS |
| 6 | Texture | Hunyuan's texture first; patch in Blender texture paint from the sheet (no paid tools) | TypeSafe faithful check vs sheet; face gate for the head |
| 7 | Rig | our rig/export (`export_pack.py`, `DEF-` bones); head bone 100 % on the face, neck 0 % (video's weight fix) | `character-gate` exit 0 |
| 8 | Toon | locked MHS3 shader `vroid_toon.py` (sha1 in the rulebook) in Blender | `render-validator`, strict gate |
| 9 | Unity | Unity 6 URP, `com.unity.toonshader` from git URL, one shading feather, outline, rim light feather off | screenshot judged by TypeSafe vs the Blender toon render |

## Stage-2 geometry standard (q41, provisional)
- TypeSafe render-vs-drawing questions failed a discrimination test: v2 renders scored about the same against the
  right and a wrong sheet on every side/back question (side silhouette 0.20 right vs 0.245 wrong). Only front
  `same_head` and `face` separated them. So stage 2 uses `scripts/sil_iou.py` (best-alignment silhouette IoU) per view:
  pass when IoU(model, own sheet) >= IoU(own sheet, a different head's sheet) + 0.02 in every view, plus TypeSafe
  front `same_head` >= its control - 0.05 (`scripts/parts_gen_gate.py`). Calibrated on 2 sheets (ce6f3794, 10a851d2):
  provisional until a third sheet is measured. Face-detail scores go to the eyes/eyebrows/mouth stages (face gate).

## Tools Sammy listed, and the job each one does (q41b: "use my browser, discord, hunyuan, blender, kimi, Typesafe and unity")
- Browser: the built-in browser pane (Firefox is read-only to computer use).
- Discord: Midjourney's bot; the Midjourney website (same account, same Basic quota) is the fallback when the Discord
  window cannot be brought forward.
- Kimi (kimi.ai, free): drafts and critiques each Midjourney prompt before it is spent, and gives a second opinion on
  a sheet. Its answer is advice; TypeSafe and the measured rules decide.
- Hunyuan 3D: head_base, hair, ears, body parts. Blender 5.2: everything else, fixes, decimation, assembly.
- TypeSafe: every gate. Unity: last stage (toon shader).

## Sammy's decisions
- 2026-10-25: "the hair will be made separately" - head_base stays bald; its stage-1 gate runs
  `scripts/parts_ref_gate.py --skip hair_anime`. The bald sheet ce6f3794 failed mhs3 (0.41) and polished (0.255),
  culprit hair; Sammy overrode and sent it to Hunyuan.
- 2026-10-25: "you can do it yourself, that's why i gave you control" - make the routine calls (re-rolls,
  regenerations within the free quota and the Basic budget, fix strategy) without asking; still stop for anything
  that costs money or cannot be undone. The bald-sheet override covers later bald head_base sheets too (mhs3 and
  polished fail with culprit hair on every bald sheet).
- 2026-10-25 q41b: "but now it looks bad" (head_base_v2b_30k: nose fix + 30K decimation) and "the face elements are
  supposed to be separate" -> head redone from a blank-face sheet; every face element its own object.

## Triangle budget (Sammy q41: "make sure (in blender) that the triangles are lower than 500k")
- Every generated part is decimated in Blender (weld by distance, Decimate COLLAPSE, triangulate, smooth shading)
  before it counts as done. Start at the video budget (head 15K, body 20K, hands 10K tris) and keep the lowest
  budget that loses no TypeSafe A/B (`blender/tools/typesafe_ab_compare.py`, front / 3/4 / side / profile close-up)
  against the full-resolution part. head_base: 15K lost `clean` on the front, 30K tied everywhere -> 30K.

## Nose (Sammy q41)
- [nose rules](references/nose_rules.json): N1 nose points 9 deg down (+-6), N2 tip angle 108 deg (+-6), measured on
  the MHS3 profile. The profile rules P1-P6 must still pass after any nose edit (moving the tip moves all of them).

## Part checks (stage 3)
- **head_base**: `head-shape-audit` HEAD_SHAPE_OK, then `mhs3_measure.py` profile and proportion rules.
- **hair**: separate shell; `mhs3_hair.py --map` thickness near VRoid (crown ~19, temple ~8.5, back ~16, front ~20 mm);
  no intersection with the face; TypeSafe A/B `hair` not a majority loss.
- **eyes / eyebrows / mouth / nose / ears**: face-gate per element against `face_gate_refs.json`; the eye-shape
  standard in the rulebook; ears and nose also by mesh rules.
- **facial hair**: none by default for this character; Sammy decides (`parts_state.py skip facial_hair` only on his word).
- **torso / arms_hands / legs_feet**: `body-proportion-audit` bands; hands generated separately (fingers merge in
  whole-body generations), five spread fingers counted by `anatomy_rules.py`.

## Session start
1. `creator-bridge` start (LEARNINGS, inbox, `docs/qa/head_v2/log.md`, `docs/qa/parts/log.md`).
2. `python3 .claude/skills/parts-workflow/scripts/parts_state.py status` (`scripts/parts_state.py`) - work only on the part it names.
3. Web tools (Hunyuan, Midjourney web, Kimi) run in the **built-in browser** (Sammy signs in there himself; I never
   enter passwords). Firefox is granted read-only to computer use - no clicks or typing, so it is only for looking at
   what Sammy has open. Discord (desktop app, full tier) is the Midjourney fallback: load
   `anthropic-skills:computer-use` and request access to `discord.exe` first. Hunyuan's free credits show top right
   (20 on 2026-10-25).
4. One sentence to Sammy: which part and stage, and what it will spend (Midjourney jobs, Hunyuan credits).

## Transfers
- Midjourney's CDN refuses non-browser downloads (403 from Blender urllib and the cloud shell). From the built-in
  browser a JS `fetch` of `cdn.midjourney.com/<job>/0_<i>.png` works from any tab (Hunyuan's too). A JS `a.download`
  of the blob lands in `~\Downloads` as `<uuid>.tmp` (the real PNG); copy it with Blender MCP. `127.0.0.1` is not
  reachable from the pane.
- Hunyuan upload: in the Hunyuan tab fetch the sheet, crop each view on a canvas (768 square, sheet background
  colour), wrap it in a `File`, set `input[type=file].files` via `DataTransfer` and dispatch `change`. Multi-image
  slots in DOM order: 0 top, 1 left45, 2 front (required), 3 right45, 4 left, 5 right, 6 back, 7 bottom. A side view
  whose nose points to image-left is the character's LEFT side (slot 4).
- Hunyuan 3.1 multi-image at 500k faces cost 1 free credit (2026-10-25).
- Generated images reach the PC through Blender MCP (`urllib` download into `datasets_work/parts/<part>/`); the cloud
  shell cannot reach cdn.midjourney.com. The PC root is `D:\Game Development\Tools\Anime Character Creator\datasets_work`.
- Never run a recursive glob or any long scan in Blender MCP: it blocks Blender for minutes and every later call queues
  behind it (q41). Use `device_list_dir` to find folders.

## Record
After each gate: `parts_state.py set <part> <stage> passed|failed --note "<numbers>"`, a line in
`docs/qa/parts/log.md` (job ids, credits used, TypeSafe numbers), commit and push. Failed gates: log the measured
cause with `bridge/tools/log.py`.
