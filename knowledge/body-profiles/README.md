# Reference body profiles

Measured with `body_audit.py blender-measure` (see `.claude/skills/body-proportion-audit/`). One JSON per reference model; `body_audit.py targets` turns them into `knowledge/body-targets.json`.

| Profile | Source | Style | Use as MHS3 target? |
| --- | --- | --- | --- |
| `amshani.json` | `XxAlonexX/Blender-Character`, `Amshani/Character/Amshani.blend` (public, no licence file: measurements only, the model is not copied here) | Chibi-leaning stylized anime girl, about 4.5 heads (head-to-top 0.22H), T-pose, one merged mesh that includes a tall ponytail, skirt and boots | **No.** Hair is inside the height H, so every ratio is shifted; the head is far larger than MHS3's. Fine for exercising the tool and as a "stylized small-head" data point. |

Measured caveats on `amshani.json`: `mirror_p95` is 4% H (asymmetric hair and clothing in the same mesh), torso depth is inflated by the ponytail, thigh/shin is 0.58 (thigh bone shorter than shin).
