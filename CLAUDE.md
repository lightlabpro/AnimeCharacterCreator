# Anime Character Creator: notes for Claude Code

- This repo is shared with a second Claude (the normal chat) that builds the Blender asset library. Use the `creator-bridge` skill: read `bridge/LEARNINGS.md` and `bridge/inbox-for-code.md` at session start, log what you learn at the end, and keep `knowledge/expected-contract.json` current (`python3 bridge/tools/export_contract.py`) after changing controls, performance keys or the rig code.
- Check before pushing: `npm run typecheck`, `npm test`, `npm run build`. Python needs only numpy and Pillow for the validator.
- Develop on the branch the session names. Do not open a PR unless asked. Never commit tokens.
- Changing the asset contract (names in `docs/CLAUDE_BUILD_PROMPT.md`) needs an inbox item to the chat first.
- Head proportions are tested against `knowledge/head-targets.json` (`tests/headShape.test.ts`). To retune the ellipsoid head run `npx vite-node scripts/fit_head.ts`. Python tests: `python3 -m unittest discover -s tests/py`.
