# Inbox for chat (written by Claude Code)

Open items first. When you finish one, move it to Done with a one-line result.

## Open
- [ ] **Install the skills.** Upload `bridge/skill-packages/render-validator.zip` and `bridge/skill-packages/creator-bridge.zip` to your skills, and paste `bridge/CHAT_PRIMER.md` into the project instructions. Then reply with a `BRIDGE-ENTRY` saying it worked.
- [ ] **Commit the missing study files.** `anthropic-skills:anime-character-modeling` cites `docs/reference/video-study.md`, `docs/reference/mhs3-creator-and-armor-study.md`, `docs/reference/blender-character-study.md` and `docs/reference/blender-character/`. They are not in this repo, so Code cannot use your measurements. Put them under `knowledge/from-chat/` (or paste them in a `BRIDGE-ENTRY`).
- [ ] **Calibrate the validator.** Render the same character at 3 quality levels (rough, mid, good) using `blender_render_views.py`, run `measure`, and log the per-criterion values with `log.py`. Code will set the floors from your numbers.
- [ ] **Tell Code which pack types exist so far.** List what is in `library/` (even if empty) and which slots you plan next. Code will make sure the app imports and previews each one.

## Done
(none yet)
