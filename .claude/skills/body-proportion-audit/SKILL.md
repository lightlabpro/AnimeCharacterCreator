---
name: body-proportion-audit
description: Measures real reference models (the MHS3-style characters) in Blender or from glTF to get exact body proportions, builds target bands from them, and checks a new character body against those bands, naming which proportion is off and how to fix it. Use before modeling a body, after blocking in a body, and before export, for leg/arm/torso/shoulder/hip proportions, rig joint placement and left/right symmetry. Complements head-shape-audit (head only).
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
Exit 0 pass, 12 fail, 13 unknown, 2 usage. Run it on the exported pack before `check_pack.py`. It measures: neck, shoulder, elbow, wrist, hip, knee and ankle heights; head-to-top; thigh/shin and upper-arm/forearm ratios; arm length; shoulder and hip joint widths; mesh width at shoulder, waist and hip; torso depth; foot length. Fixed ceilings (no reference needed): rig asymmetry 0.6% H, mesh mirror error 1.2% H (p95), centre offset 1% H.

## Rules of thumb
- Measure with shape keys at 0 and the rig in rest pose; the tool does this itself in Blender.
- A fail names the direction ("hip joints too low: legs too short"). Fix the proportion, then re-run; do not widen the band to pass.
- Comparing like with like: a heroic muscular reference gives targets for a heroic body. Declare the style in `--style` and use matching references per body type.
- Bands are only as good as the references. One screenshot-measured number is not a reference; a measured mesh is.
- Head shape is handled by `head-shape-audit`; this skill only uses the neck joint for head-to-top.
