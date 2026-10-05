---
name: body-proportion-audit
description: Checks a character body's anatomy. Measures real reference models for exact proportions and checks a body against those bands; runs hard rig and skin-weight rules (finger and limb counts, bone chain order, unweighted vertices, weight sums, cross-side and finger weight bleed); and stress-tests deformation by posing the glTF (elbow, knee, hip, shoulder, neck, forearm twist) and sweeping every body slider. Use before modeling a body, after rigging or skinning, and before export. Complements head-shape-audit (head only).
---

# Body proportion audit: measure real references, never guess anatomy

Anime body proportions are a style, not a rule. The only trustworthy target is a measured reference model of the style we want. This skill measures reference models with real numbers, stores them as targets, and checks candidates against them. Every length is divided by body height H, so scale and units do not matter.

## 1. Measure each reference model (once per reference, on the PC that has it)
In Blender, any importable file (.fbx, .glb, .gltf, .blend) or the open scene:
```
blender -b -P .claude/skills/body-proportion-audit/scripts/body_audit.py -- blender-measure --file mhs3_hero.fbx --name mhs3_hero --out knowledge/body-profiles/mhs3_hero.json
```
Inside the Blender Text Editor, call `blender_import(path)` then `measure(*blender_collect(), "name")`. Use the **rest pose** (A or T pose). Hair, eyes, clothes and props are skipped by name; pass `--meshes Body,Head` to choose exactly. Without Blender, `body_audit.py measure model.glb --out ...` does the same on a glTF.

It needs bones the tool can name: Rigify `DEF-thigh.L`, Mixamo `mixamorig:LeftUpLeg`, VRM `J_Bip_L_UpperArm`, and similar all work. Joints it cannot find make those metrics UNKNOWN, never a pass.

## 2. Build the targets
Measure several references (different characters and body types make a band, not a point). Then:
```
python3 .claude/skills/body-proportion-audit/scripts/body_audit.py targets knowledge/body-profiles/*.json --style "mhs3 adult default" --out knowledge/body-targets.json
```
One reference gives a +-6% band; more references widen it to their spread. Commit the profiles and the targets.

## 3. Check a candidate (any time while modeling)
```
python3 .../body_audit.py check CHR_Body.glb --targets knowledge/body-targets.json
```
Exit 0 pass, 12 fail, 13 unknown, 2 usage. Run it on the exported pack before `check_pack.py`. It measures: neck, shoulder, elbow, wrist, hip, knee and ankle heights; head-to-top; thigh/shin and upper-arm/forearm ratios; arm length; shoulder and hip joint widths; mesh width at shoulder, waist and hip; torso depth; foot length. Fixed ceilings (no reference needed): rig asymmetry 0.6% H, mesh mirror error 2% H (p95; a good real model, Mirai, measures 1.2%, a merged hair-and-skirt mesh 4%), centre offset 1% H.

## Rules of thumb
- Measure with shape keys at 0 and the rig in rest pose; the tool does this itself in Blender.
- A fail names the direction ("hip joints too low: legs too short"). Fix the proportion, then re-run; do not widen the band to pass.
- Comparing like with like: a heroic muscular reference gives targets for a heroic body. Declare the style in `--style` and use matching references per body type.
- Bands are only as good as the references. One screenshot-measured number is not a reference; a measured mesh is.
- Head shape is handled by `head-shape-audit`; this skill only uses the neck joint for head-to-top.

## Hard rules: `anatomy_rules.py check pack.glb` (no reference needed)
Exact checks on the exported glTF: required joints (head, neck, spine, arm and leg chains both sides), left/right bone twins (body and finger bones fail, costume bones only warn), forearm under upper arm / hand under forearm / foot under shin under thigh in the hierarchy, legs running downwards, finger counts (at most 5 per hand; if any finger bones exist all 5 with 2-4 segments, same on both hands), unweighted vertices, weights not summing to 1, more than 4 influences (the creator reads 4), cross-side weights, finger bleed. Exit 0/12/13/2. A rig where the foot is not parented under the shin (IK controller rigs like Mirai's) fails `chain_order`: the DEF chain has to be a real parent chain for pose clips to work.

## Pose stress and sliders: `pose_stress.py poses|sliders pack.glb`
Linear blend skinning in numpy on the glTF, no Blender. `poses` bends elbow 90, knee 90, hip 90, shoulder forward 80 / raise 60, twists the neck 45 and the forearm 90, and measures on the triangles crossing each joint: stretch and collapse (posed/rest triangle area, 99.9th and 0.1th percentile), zone area ratio (a volume-loss proxy), fold-over fraction, and wrist pinching under forearm twist. `sliders --prefix ID-` pushes each shape key to 1 and fails on stretch spikes, collapses and flipped triangles. A joint with no triangle crossing it is UNKNOWN, never a pass.

Thresholds are calibrated on only three real models, so treat borderline results with care (`knowledge/anatomy-calibration.md`): a production game model (Navia) folds 1-2% of edges at 90 degree bends, hobby models (Mirai, Amshani) 5-34%, and a rigid-weighted test figure 22-28%. Fail limits: folds above 5%, stretch above 10, collapse below 0.05, zone area outside 0.6-1.5, wrist radius below 0.5 under twist. Self-intersection (limbs through the torso) needs Blender and is not checked yet.

## Fix hints
- unweighted / weight_sum: select all, Weights > Normalize All, Limit Total 4.
- cross_side / finger_bleed: Weight Paint with Mirror, or Transfer Weights from a clean body, then re-run.
- High folds or stretch at a joint: widen the weight blend over the joint (smoother gradient across 2-3 edge loops), add a joint edge loop, or add a corrective shape key. Pure 0/1 weights across a joint always fail.
