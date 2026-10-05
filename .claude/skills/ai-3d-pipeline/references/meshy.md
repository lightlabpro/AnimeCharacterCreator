# Using Meshy (optional, user's call)

Meshy is a paid service. Using it is the user's decision, and so is the budget. This project does not need it: the asset library is hand-modeled in Blender. If the user wants a generated blockout or reference, use these rules. Source: `meshy-dev/meshy-3d-agent` 0.6.0, Meshy CLI 0.4.0, Node 22.12 or newer.

## Safety
- Sign in through the CLI's browser device login. Show the verification URL and code in your progress text and wait for the user to approve. **Never paste, request, print or commit an API key or token.** An existing `MESHY_API_KEY` overrides a stored session.
- Run everything through the CLI with `--output-schema v1 --format json --no-update-check`, and read the JSON result, not the progress text.
- Write only inside one workspace folder per job, and pass it explicitly. Do not overwrite existing files unless the user said to.

## Cost
- Estimates come from `meshy make "..." --dry-run` (spends nothing) or Meshy's published price list, dated, and called an estimate. The balance command reports a balance, not a price. Do not invent a price.
- Work inside the approved plan proceeds. A new stage, a second variant or a rerun needs a fresh yes.
- Report `consumed_credits` from the finished task, or say it is unknown.

## Submit once, then wait
- Create with `--async`, keep the task ID and the resource that owns it, then `wait` on that task. Do not poll by hand and do not end your turn while a stage is running.
- A timeout (exit 8) or a task stuck near 99% is not a failure: resume waiting on the same task.
- Exit 10 means the submission outcome is unknown. Reconcile by listing the resource and matching the request. Never resubmit automatically. Exit 9 (insufficient credit) stops all new paid submissions.
- A terminal FAILED task needs an explanation and the user's yes before any replacement.

## Exit codes worth knowing
| Exit | Meaning |
| --- | --- |
| 9 | insufficient credit |
| 10 | submission outcome unknown |
| 12 | a check failed |
| 13 | a check was unknown |

## Delivery
Deliver the file at the requested path, a preview image you actually looked at (or say none exists), the task IDs and project folder, and the real cost. A download link in a task snapshot expires: refresh it from the task, do not regenerate. Do not edit application code unless the user asked for the asset to be wired in.

## What a generated model still needs here
Retopology by hand, a head audit (`head-shape-audit`), toon shading in the project's shader, the `DEF-`, `ID-`, `PF-` and `SOC-` names, and the validator's gates. Assume baked lighting in the texture, weak hands and hair, and no face rig.
