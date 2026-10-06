---
name: creator-bridge
description: Shared memory between Claude Code (improves the Anime Character Creator app) and Claude chat (builds the Blender asset library). Use at the start and end of any session on this project, whenever you learn a measurement or make a decision the other side needs, and before changing anything in the asset contract. Reads and writes the bridge/ folder in the lightlabpro/AnimeCharacterCreator repo.
---

# creator-bridge

The other Claude cannot hear you. The repo is how you talk. Full rules: `bridge/README.md`.

## Start of session (always)
1. Read `bridge/LEARNINGS.md` (the last 20 entries), your inbox (`inbox-for-code.md` if you are Claude Code, `inbox-for-chat.md` if you are the chat), and `knowledge/INDEX.md`.
2. Say in one line what the other side asked or learned that changes your plan. Then work.

## While working
- Assets built in Blender (chat): build to `knowledge/expected-contract.json`. It lists every shape key, performance key, socket and bone property the app really reads. A name that is not in it does nothing in the app.
- Every stage of a character goes through the `render-validator` skill before it is shown. Log measured values, not impressions.
- Something wrong in the app (a slider does nothing, an import fails, a pack looks wrong in the creator): add an item to the other inbox with the pack id, the exact symptom and the file involved.
- Something in the contract has to change: open an inbox item first. Never edit `docs/CLAUDE_BUILD_PROMPT.md` names unilaterally.

## End of session (always)
1. Log what you learned (not what you did) with `python3 bridge/tools/log.py ...`.
2. Clear finished inbox items to Done with a one-line result.
3. Skills you improved: rebuild with `python3 bridge/tools/package_skills.py` and say which zip to re-upload.

## If you cannot write to GitHub (the usual case for the chat)
Output exactly this block and ask Sammy to paste it to Claude Code:

```
BRIDGE-ENTRY
side: chat
kind: learning | request | done
topic: <short>
finding: <one sentence, measured or decided>
evidence: <file, number, render>
status: confirmed | unverified
use: <what Code should do>
```
Code commits it verbatim into `LEARNINGS.md` or `inbox-for-code.md`.

## Honesty rules
- Mark every number you did not measure as `unverified`.
- Never tell the other side a thing works because you expect it to. Run it.
- A measurement from one character is one data point. Say how many you measured.

## Gate results
When `character-gate` fails, log the measured cause (the check name and numbers from `gate_report.json`), not the fix you tried first, with `python3 bridge/tools/log.py`, so the other side can avoid it. A gate that keeps failing the same way is a lesson worth a `BRIDGE-ENTRY`.
