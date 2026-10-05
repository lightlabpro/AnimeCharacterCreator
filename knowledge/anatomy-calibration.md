# Anatomy rule and pose-stress calibration

Measured with `.claude/skills/body-proportion-audit/scripts/{anatomy_rules,pose_stress}.py` (exported to glb from the reference .blend files with Blender 5.0.1). Only three real models: thresholds are GUESSES with weak support. Add every new reference here.

| Model | anatomy_rules | worst pose (90 deg bends) |
| --- | --- | --- |
| Navia (Sketchfab, CC-BY, game-style, 678 bones) | PASS (costume bone `+HatS` has no twin; forearm weight mass 41 vs 96 warning) | folds 1.0-1.8%, stretch 1.8-6.1 (hip), collapse 0.11-0.25, zone area 0.94-1.25; twist ring 1.0 (PASS under the limits below) |
| Mirai (hobby, IK rig, body mesh only) | FAIL chain_order: foot not parented under shin (IK controller) | folds 5-12%, stretch 15-31, zone area 1.7-2.8 |
| Amshani (hobby, merged mesh) | PASS (hand weight mass 864 vs 226 warning) | folds 3-34%, zone area 1.0-2.7, shoulder and neck worst |
| Test figure, smooth weights (tubes) | PASS | folds 1-2% |
| Test figure, rigid 0/1 weights | PASS | folds 22-28%, zone area 1.35-1.59 |

Reading: fold fraction separates good from broken best (real good 1-2%, rigid 22-28%). Stretch is noisy at the hip (production model reached 6). Fail limits sit between: folds > 5%, stretch > 10, collapse < 0.05, zone area outside 0.6-1.5.

Not yet known: how MHS3-grade skinning scores, whether the limits are too strict for stylized hips and shoulders, and the right pose angles for each joint. Not measured: self-intersection, corrective shapes, hand and foot deformation.
