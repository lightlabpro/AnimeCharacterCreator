# Dataset pass 2 (2026-10-15): pictures checked by TypeSafe, face-form bands, why the head looked "pushed in"

Pass 1 is `dataset-study.md` (2026-10-07). This pass reuses its downloads and adds TypeSafe's picture questions
(jev-1.14, danger-zone images, Box). Only anime-style characters are used; nothing is copied into the library.

## Which of the linked datasets can be used (only anime characters)
| Dataset | Anime characters? | Used |
| --- | --- | --- |
| TexVerse (Sketchfab, 858,669 models with captions) | yes | pass 1 ranked 1,190 candidates, 200 GLBs on the PC (`datasets_work/glb_sel`, 65 + 2 kept); reused, not re-downloaded |
| Objaverse-XL (HF `allenai/objaverse-xl`) | some | metadata downloaded (sketchfab.parquet 80 MB: UIDs only, the same Sketchfab pool as TexVerse; thingiverse.parquet 341 MB: file names). 29 anime-figure STL names found, 24 after excluding swimsuit/franchise names; **all 24 downloads refused with HTTP 403** (Thingiverse bot protection). Not bypassed. |
| OmniObject3D | no (real scanned household objects) | no |
| Amazon Berkeley Objects | no (product models) | no |
| Stanford 3D Scanning Repository | no (bunny, dragon, Buddha, Lucy...) | no |
| Structured3D | no (indoor rooms) | no |
| LAION-3D | no data (a reading list of other datasets) | no |

## What TypeSafe's pictures can and cannot judge (measured on 65 models)
Tool: `blender/tools/typesafe_dataset_gate.py` (3 pictures per model: textured full body, textured face, the
measured geometry front + side with the measured skull-top and chin rows drawn) and
`blender/tools/typesafe_landmark_box.py` (Box around the head on the plain geometry renders).
- Reliable enough to gate: anime style (32 yes / 8 unsure / 25 no), adult proportions (59/3/3), face seen from the
  front (31/6/28), bare head without hat or hair mass (38/6/21). These agreed with Claude's own look at the sheets.
- Not reliable: "does the red line touch the chin?" (0 of 65 said yes, including sheets that are right) and the Box
  around "skull top to chin tip" (its bottom edge lands on the neck: chin errors 0.2-0.33 head heights on correct
  sheets; top edges agree within 0.01-0.04). So landmarks were checked by Claude on the sheet, with TypeSafe's style,
  age and bare-head answers as the gate: 16 passed the gates, 7 had correct chin rows (`verified_shape` below).
- Face Boxes (eyes, brows, mouth, nose, chin) came back with confidences 0.05-0.48 on both our face and the Leo
  reference, so they are a measuring aid only; pixel measurements stay authoritative.

## Face form bands (face_study.py, n = 7 verified anime heads, fractions of head height hh, p10 / median / p90)
`setback_k` = how far the face front at |x| = k hh lies behind the centre line (both sides averaged).
| Level | width | setback 0.10 | setback 0.20 | setback 0.30 |
| --- | --- | --- | --- | --- |
| brow (0.42 hh) | 0.71 / 0.83 / 0.89 | 0.010 / 0.015 / 0.033 | - | 0.12 / 0.14 / 0.19 |
| eye (0.50) | 0.70 / 0.80 / 0.85 | 0.021 / 0.023 / 0.042 | (eye hole) | 0.10 / 0.13 / 0.17 |
| cheek (0.62) | 0.70 / 0.78 / 0.89 | 0.028 / 0.039 / 0.050 | 0.05 / 0.09 / 0.74 | 0.12 / 0.14 / 0.19 |
| mouth (0.76) | 0.57 / 0.64 / 0.87 | 0.05 / 0.09 / 0.39 | 0.09 / 0.13 / 0.15 | - |

## Why the head looked "pushed in" (Sammy, 2026-10-15) and the fix
The p-series bake (`id_morphs.py`) scaled the eye box (opening, lids, brow ridge, upper cheek) toward each eye centre
and the skin kept its depth, so at brow and cheek height the cross-section bowed inward ~1 cm beside each eye
(setback at 0.30 hh: brow 0.146 -> 0.212, cheek 0.161 -> 0.228; the cheek value was above the dataset p90 0.19).
q1: moved skin slides on the pre-bake surface (depth re-read at its new x/z), the lid rim keeps its own depth -> brow
0.147, cheek 0.157 (pre-bake values, inside the band). q1c: the lateral orbit beside the smaller opening is filled to
the straight line from the brow ridge to the cheek -> eye-level setback 0.215 -> 0.169 (band p90 0.166).

## Caveats
n = 7 for the form bands. Generic Sketchfab anime heads, not MHS3. TypeSafe's image answers are a gate, not a
measurement; the slices are the measurement.
