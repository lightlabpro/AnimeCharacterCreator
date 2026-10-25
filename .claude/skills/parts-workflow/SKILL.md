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
   `passed` or Sammy skipped it. Head sub-parts in order: hair, eyes, eyebrows, mouth, ears, nose, facial hair (the
   head base mesh - skull, face, sockets - is generated first as `head_base`, because every head part attaches to it).
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

## Record
After each gate: `parts_state.py set <part> <stage> passed|failed --note "<numbers>"`, a line in
`docs/qa/parts/log.md` (job ids, credits used, TypeSafe numbers), commit and push. Failed gates: log the measured
cause with `bridge/tools/log.py`.
