# Inbox for chat (written by Claude Code)

Open items first. When you finish one, move it to Done with a one-line result.

## Open
- [ ] **Validator upgrade: mesh gates.** Re-upload `render-validator.zip` and `ai-3d-pipeline.zip`. In Blender run `scripts/mesh_stats.py` (set `OBJECTS` at the top) to get `mesh_stats.json`, then `validate.py init ... --require-mesh` and `measure ... --mesh-stats mesh_stats.json --contract knowledge/expected-contract.json --stage <stage>`. Results are now pass, **12 failed** or **13 unknown**. Reply with the printed values from your current body mesh (tri count, non-manifold edges, loose parts) so Code can calibrate the budgets, and tell Code any `ID-`/`PF-`/`SOC-` name it flags as unknown to the app.
- [ ] **Run the head audit on the current Blender head (priority).** Install `bridge/skill-packages/head-shape-audit.zip` and `ai-3d-pipeline.zip` (re-upload `render-validator.zip` too, it changed). Create the `LM_top` and `LM_chin` empties, run `scripts/head_audit.py`, and reply with the printed `BRIDGE-ENTRY`. Code measured your last head from the comparison image: cranium too wide by 0.07-0.10H, skull too shallow (width:depth 0.91 vs 0.72), chin and forehead too far back relative to the nose. Fix form before shading; the lighting problem is probably the form.
- [ ] **Measure the reference head exactly.** If you can open the "Industry reference" mesh in Blender, run `head_audit.py` on it and paste the output into a `BRIDGE-ENTRY`. Code will replace the screenshot-derived `knowledge/head-targets.json` with exact numbers.
- [ ] **Install the skills.** Upload `bridge/skill-packages/render-validator.zip` and `bridge/skill-packages/creator-bridge.zip` to your skills, and paste `bridge/CHAT_PRIMER.md` into the project instructions. Then reply with a `BRIDGE-ENTRY` saying it worked.
- [ ] **Commit the missing study files.** `anthropic-skills:anime-character-modeling` cites `docs/reference/video-study.md`, `docs/reference/mhs3-creator-and-armor-study.md`, `docs/reference/blender-character-study.md` and `docs/reference/blender-character/`. They are not in this repo, so Code cannot use your measurements. Put them under `knowledge/from-chat/` (or paste them in a `BRIDGE-ENTRY`).
- [ ] **Calibrate the validator.** Render the same character at 3 quality levels (rough, mid, good) using `blender_render_views.py`, run `measure`, and log the per-criterion values with `log.py`. Code will set the floors from your numbers.
- [ ] **Tell Code which pack types exist so far.** List what is in `library/` (even if empty) and which slots you plan next. Code will make sure the app imports and previews each one.

## Done
(none yet)
