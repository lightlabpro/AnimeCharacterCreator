# Dataset study: head and body bands from real anime-style models

Date: 2026-10-07. Tools: `.claude/skills/body-proportion-audit/scripts/measure_dataset.py` and `dataset_bands.py`.
Result file: `knowledge/head-targets-dataset.json`.

## Pipeline (what was run)
1. TexVerse metadata (858,669 Sketchfab models) filtered by words only: license CC BY, CC BY-SA or CC0; category
   Characters & Creatures; an explicit anime/manga/toon/cel style word; franchise, VRoid, NSFW and child terms
   excluded. 1,190 candidates.
2. TypeSafe (`jev-1.13.0`) asked six yes-is-good noul questions per candidate on name, tags and caption (single humanoid,
   anime style, original character, no sign of a child, full body, hand-made mesh). 0 errors. 436 passed the gates;
   652 had at least one gate answer with confidence below 0.4 (text alone rarely proves originality or age). The top
   200 by rank all passed the gates. Age is decided numerically afterwards (heads tall), not by the caption.
3. Downloaded the 200 GLBs (1.09 GB, TexVerse-1K) with Sammy's go-ahead. Measured only; nothing copied into the library.
4. Automatic measurement: hair, eyes, clothes removed by material and node name; skeleton used for orientation and the
   neck; skull top = highest non-hair vertex; chin = top of the steepest forward jump of the front profile; head
   profile from exact triangle slices (`head_audit.profile_from_mesh`).
5. Exclusions: 29 VRoid exports (Sammy's rule; they also share one base mesh), 83 with hair fused into the body
   material, 6 unreadable, and the rest failed orientation or plausibility. 65 remained, rendered as contact sheets
   with the landmarks drawn, checked by eye: 19 had correct top and chin landmarks, 1 was under 5.5 heads. Used: 18.

## Main numbers (p10-p90, median)
| Measure | Dataset | Screenshot target | Our head (head_v3) |
| --- | --- | --- | --- |
| Heads tall | 6.0-8.5, 7.2 | - | MHS3 brief 6.3-6.7 |
| Cranium width @0.25H | 0.66-0.80, 0.71 | 0.58 | 0.70 |
| Jaw width @0.8H | 0.53-0.72, 0.56 | 0.37 | 0.53 |
| Chin width @0.9H | 0.39-0.72, 0.44 | 0.27 | 0.37 (LOW) |
| Skull depth @0.3H | 0.77-0.89, 0.85 | 0.80 | 0.78 |
| Width:depth | 0.77-0.93, 0.81 | 0.72 | 0.89 |
| Forehead behind nose tip @0.3H | 0.03-0.10, 0.05 | 0.11 | 0.09 |
| Chin behind nose tip @0.9H | 0.06-0.12, 0.09 | 0.11 | 0.08 |

Our head sits inside the dataset band on every row except chin width at 0.9H (slightly narrow). The screenshot
target is narrower than every measured model at the cranium and jaw. So the remaining "flat face" problem is
surface form (planes, sockets, cheek and mouth volumes, normals), not the head proportions.

## Caveats
- n = 18 heads, 6-10 bodies. A band, not a law.
- If a model's scalp is in its hair material, its skull top reads low (head short, heads_tall high).
- Generic Sketchfab anime, not MHS3. MHS3 is chunkier; a style can sit at one edge of the band on purpose.
- Body bands use pose-independent metrics only.
