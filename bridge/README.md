# Bridge: Claude Code (tool) <-> Claude chat (asset library)

Two Claudes, one project, one shared memory: this repo.

| | Claude Code (cloud session) | Claude chat (normal chat, Blender) |
| --- | --- | --- |
| Main job | Improve the creator app in `src/` | Build the Blender asset library in `library/` |
| Reads | `bridge/`, `knowledge/`, the whole repo | the same, through the GitHub link on the chat project |
| Writes | commits and pushes | commits if it has write access, otherwise pastes a block for Sammy |
| Strength | runs code, tests, a headless browser, subagents | sees Blender live, runs Sammy's scene, fast visual iteration |

Neither side can call the other directly. Everything moves through files here, so the rules below keep it clean.

## Files
- `LEARNINGS.md`: append-only ledger of things either side learned (measurements, what worked, what failed). Newest at the bottom.
- `inbox-for-chat.md`: Code leaves requests and handoffs for the chat. The chat clears items it finished by moving them to the Done list.
- `inbox-for-code.md`: the chat leaves requests for Code (a missing slider, an import bug, a contract change).
- `CHAT_PRIMER.md`: paste into the chat project's instructions once. It tells the chat how to use all of this.
- `tools/log.py`: writes a correctly formatted entry so the ledger never drifts in format.
- `../knowledge/`: distilled knowledge worth reading in full (tool contract, research digest, validator guide).
- `../.claude/skills/`: skills, source of truth. `skill-packages/` holds installable zips of them for the chat.

## Rules
1. **Read before you work.** Start of every session: read `LEARNINGS.md` (last 20 entries), your inbox, and `knowledge/INDEX.md`.
2. **Log what you learn,** not what you did. A good entry is a measurement, a decision with its reason, or a failure with its cause. Use `tools/log.py` (or copy the format by hand).
3. **Never edit the other side's inbox items.** Add your own, or move an item to Done with a one-line result.
4. **Contract changes need both sides.** If something in `docs/CLAUDE_BUILD_PROMPT.md` (the `ID-`, `PF-`, `DEF-`, `SOC-` naming, pack.json) has to change, open an item in the other inbox first, and change it only after the answer lands.
5. **Skills are shared, one copy.** Improve a skill in `.claude/skills/<name>/`, then rebuild its zip (`python3 bridge/tools/package_skills.py`). The chat installs the new zip. Log the change in `LEARNINGS.md` with the skill name.
6. **No secrets, no unlabelled guesses.** Mark anything unverified as `unverified`.
7. **When the chat can't write to GitHub,** it outputs a fenced block headed `BRIDGE-ENTRY` (format in `CHAT_PRIMER.md`) and asks Sammy to paste it to Code. Code commits it verbatim.

## What each side gets from the other
- Chat -> Code: real Blender measurements (head ratios, hair clump stats), which assets the app is missing, import failures, what looks right against the MHS3 refs. These turn into tool fixes, slider ranges and shader defaults.
- Code -> Chat: the validator (objective gate plus independent review), the research on how AI 3D pipelines work, what the app expects from each pack, a headless way to see an imported pack in the real creator, and tests that catch contract breaks.

## Connecting GitHub so both sides can read and write this repo
The repo only works as a bridge if each Claude can reach it.

- **Claude Code in the cloud (this session):** already connected through the environment. Nothing to do.
- **Claude Code on a local machine:** `.mcp.json` at the repo root registers the GitHub MCP server and reads the token from your `GITHUB_PAT` environment variable. No secret is stored in the repo. Set the variable, restart Claude Code, then check with `claude mcp list`.
- **The normal chat (Claude Desktop or claude.ai):** follow https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-claude.md. For Claude Desktop that means a `github` entry in `claude_desktop_config.json` (the local Docker server with a token). If your chat has a built-in GitHub connector or can sync a repo into a project, that also works and needs no token.
- **Token safety:** create a fine-grained personal access token limited to `lightlabpro/AnimeCharacterCreator` with Contents read/write and Metadata read. That is safer than a classic token with the full `repo` scope. Never paste a token into a chat, a commit or an inbox file.
- **Verify it:** in the chat, ask Claude to read `bridge/inbox-for-chat.md` and to log a test entry with `BRIDGE-ENTRY`. If it can commit it, write access works. If it can only read, it falls back to the paste route in the rules above.
