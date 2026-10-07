---
name: head-shape-audit
description: Measures a character head mesh (in Blender) or head renders against a reference head and says exactly which proportions are wrong and how to fix them. Use before judging shading, outlines or colour on any head, whenever a head looks wrong but you cannot say why, and whenever toon lighting looks wrong (it usually means the form is wrong). Runs as a Blender script on the real vertices, or on front and side images.
---

# Head shape audit: fix the form before the shader

Toon shading draws the form. A hard light/shadow edge on a wrong head shape looks wrong however good the shader is. Sammy's last Blender head had a good shader and wrong lighting for exactly this reason. Measure the head first.

## What was measured (so you know what "wrong" means)
Reference = the "Industry reference" head in Sammy's comparison image. Values are fractions of head height H (top of skull = 0, chin tip = 1). Source and accuracy are in `knowledge/head-targets.json` (screenshot-derived, about ±0.03H; if you have the reference mesh, measure it and replace the targets).

| Measure | Reference | Chat's last head | Verdict |
| --- | --- | --- | --- |
| Cranium width (0.2-0.3H) | 0.58H | 0.66H | too wide by 0.07-0.10H |
| Skull depth at 0.3H | 0.80H | 0.73H | too shallow by 0.06H |
| Width : depth | 0.72 | 0.91 | too round and flat seen from above |
| Jaw width at 0.8H / chin at 0.9H | 0.37 / 0.27H | 0.41 / 0.29H | a little wide |
| Chin behind the nose tip (0.9H) | 0.11H | 0.08H | chin recedes or nose too long |
| Forehead behind the nose tip (0.3H) | 0.11H | 0.09H | forehead recedes |

Also seen but not measured (mark as visual): the reference has deep eye sockets with an upper lid fold, a brow ridge, a nose with a real bridge and a wide base, visible cheekbones, a defined jaw angle and ears sitting between brow and nose level. The last head had flat disc eyes with no lids, a long thin pointed nose, a narrow mouth line, tiny high ears and a smooth cheek-less face.

Also found on the creator app's own ellipsoid head (so it is a common trap): a plain ellipsoid skull is widest around 0.3-0.4H, while the reference is flat-sided from 0.2H to 0.35H. Build the temples flat and vertical, not as a bulging egg.

## How it measures
The audit slices the real triangles with a plane at each height and takes the exact outline extents, so it does not depend on where your vertices happen to lie (an earlier vertex-slab version dropped rows on smooth meshes). If a row still cannot be measured the audit says UNKNOWN, writes `"status": "unknown"` to `head_audit.json`, and the validator treats that as not measured, never a pass. Checked in Blender against an analytic ellipsoid (widths within 1.2% of the head height at every tested row, and the same result at three different tessellations).

## Procedure (Blender)
1. Create two empties, `LM_top` at the highest point of the skull (not the hair) and `LM_chin` at the chin tip. Leave them.
2. Run `scripts/head_audit.py` in Blender's Text Editor (edit `HEAD_OBJECTS` at the top if your head mesh has another name). It slices the evaluated mesh, prints a table, lists fixes in the order to work, and prints a `BRIDGE-ENTRY` you can log.
3. Fix the first listed problem only, re-run. Order: cranium width and depth, then jaw and chin, then forehead and nose, then the width:depth ratio. Do not touch shading while the audit fails.
4. When it prints `HEAD_SHAPE_OK`, run front, three-quarter and side renders through the `render-validator` skill.
5. Log the final numbers with `bridge/tools/log.py`. If the reference mesh is available, run the audit on it first and paste its output over `TARGETS` in the script, then tell Code so `knowledge/head-targets.json` is replaced.

## Procedure (images, no Blender)
This route needs the `render-validator` skill installed as well, because the script lives there: `python3 <render-validator>/scripts/head_profile.py measure --front f.png --side s.png --front-chin-y <row> --side-chin-y <row> --out cand.json` then `compare --ref knowledge/head-targets.json --cand cand.json`. Read the chin row off the image. Accuracy is about ±0.03H, so treat results within tolerance 0.04 as a pass.

## Dataset bands (second opinion, measured)
`knowledge/head-targets-dataset.json` holds p10-p90 bands measured from 18 real anime-style models (TexVerse/Sketchfab, CC BY, VRoid excluded, landmarks checked by eye; method and caveats in `knowledge/dataset-study.md`). Set `DATASET_BANDS` at the top of the script to that path and the audit prints both verdicts. The bands disagree with the screenshot targets above on the cranium: every measured model is wider than 0.58H at 0.25H (band 0.66-0.80, median 0.71) and the width:depth band is 0.77-0.93 (median 0.81), not 0.72. Report both; do not pick one silently. Sammy decides which target governs the MHS3 style.

## Fix recipes (what to do in Blender)
- **Cranium too wide, skull too shallow:** scale X in with proportional editing (large falloff), then push the back of the skull out in Y. The head is deeper than it is wide.
- **Forehead recedes:** pull the brow and forehead forward at 0.2-0.3H. Keep the forehead near vertical from the eye line up to about 0.8H.
- **Chin recedes / nose too long:** move the chin forward at 0.9H, or shorten the nose; the nose tip should stand about 0.11H ahead of both forehead and chin.
- **Eyes:** model sockets (inset the eye opening two loops, then put the eyeball inside), add upper lid and lower lid loops, a brow ridge above. Flat discs on a flat face never read as eyes.
- **Cheeks and jaw:** add cheekbone volume at 0.5-0.6H and a jaw corner at 0.75H, then taper to the chin.
- **Ears:** between brow level and nose base, set back at about the middle of skull depth.
- **Lighting still wrong after the audit passes:** transfer smooth normals onto the face from an ellipsoid proxy so the terminator makes one clean shadow shape (see `anthropic-skills:anime-character-modeling`).

## Honesty
- The targets come from one reference head and a screenshot. One head is a style target, not a law. Say so when a stylised character should differ on purpose, and log the deviation.
- A pass means the proportions match the reference. It does not mean the face looks good: the `render-validator` review still decides that.

## Works with other skills
The `head_audit.json` it writes is read by `render-validator` (`validate.py --head-audit`) and by `character-gate` (`run_gate.py --head-audit`), which also checks that the head height here agrees with the neck-to-top height from `body-proportion-audit`. Run the gate after this audit so the result is cross-checked.
