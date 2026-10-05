# Lessons from meshy-dev/meshy-3d-agent

Read 2026-10-05, version 0.6.0 (CLI 0.4.0), `https://github.com/meshy-dev/meshy-3d-agent`, 31 files, MIT licence.

## What the repo is, and is not
It is the **agent layer** for Meshy's CLI: three skills (generation, printing, and an OpenClaw bundle), a skill validator, contract tests and CI. It contains **no model architecture, training data or generation internals**. It tells us nothing new about how Meshy's models work. It is a good example of how to make an agent skill reliable.

## What it does well, and where we applied it
| Idea in the repo | Where it came from | Applied here |
| --- | --- | --- |
| Checks return pass, fail or **unknown**, and unknown is never a pass (exit 12 failed, 13 unknown) | `inspect faces` gates before UV and rigging | `validate.py`: exit 12 and 13, `MEASURE_UNKNOWN`, required views and `--require-mesh` |
| Gate on face count before an expensive stage (UV needs ≤40k faces, rigging ≤300k) | `pipelines.md` | `mesh_stats.py` and the mesh gates (tri budget, non-manifold, zero-area, loose parts, n-gons) |
| A preview proves little: "a rendered image does not establish topology quality" | `delivery.md` | validator prints its SCOPE line; `ai-3d-pipeline` rule 4 |
| Pick the shortest route; reuse the existing asset for follow-ups | `pipelines.md`, `delivery.md` | `ai-3d-pipeline/references/routes.md`; validator `--stage` lineage |
| Skill entry file is short and points to references by need ("read what this request needs") | `SKILL.md` | `ai-3d-pipeline` restructured the same way |
| A validator for the skills themselves: frontmatter, name matches folder, line limit, links resolve, no stray runtime files | `scripts/validate_skills.py` | `scripts/validate_skills.py` plus CI, and it already caught a stale zip and a cross-skill reference that would have broken a chat install |
| Contract tests that execute the documented commands against a fake server | `tests/*.test.mjs` | `tests/py/test_validate.py` runs the real CLI through fail, unknown, no-change and pass paths |
| Never resubmit on unknown outcome; a timeout is not a failure | `troubleshooting.md` | `ai-3d-pipeline/references/meshy.md` rule 6 |
| Ask before any new cost; estimates only from a stated source; report actual cost or say unknown | `delivery.md` | `ai-3d-pipeline` rule 5 |

## Limits worth knowing (from the repo, vendor numbers, may change)
Smart topology 100-15,000 triangles; remesh 100-300,000; UV unwrap needs GLB ≤40,000 faces; rigging needs a textured humanoid in an A or T pose ≤300,000 faces and bundles walking and running clips; resize is in metres; text-to-motion is 2-10 s in 0.5 s steps and does not animate your rigged character; local inputs are limited to 50 MiB.

## What we did not copy
- Its Meshy-specific CLI commands (we do not assume a Meshy account or credits).
- Its "no scripts in a skill" rule. Our skills ship Blender and validator scripts on purpose, so our validator checks they compile instead.
