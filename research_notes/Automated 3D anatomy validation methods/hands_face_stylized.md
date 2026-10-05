# Automated validation of hands, feet and face anatomy on stylized/anime 3D characters

Research status: limited. ~10 tool calls; PubMed Central (ncbi.nlm.nih.gov) and ph.health.mil were blocked by the egress proxy, so only search-result summaries were available for those. Items marked INFERRED are my reasoning, not sourced. Items in Gaps could not be sourced.

## 1. Hand and foot anatomy as measurable rules (finger count, chain lengths, ratios, naming)

### Takeaway
Skeleton-level checks (finger count, chain length, naming) are cheap and exact via VRM/Rigify naming. Numeric hand/foot ratios were NOT retrievable from primary sources (ANSUR II tables blocked), so the thresholds below are mostly inferred and must be calibrated on reference models.

### Cited Findings
- ANSUR II has 93 directly measured variables, 4,082 men and 1,986 women, all in mm; public CSVs ("ANSUR II MALE Public.csv" / "FEMALE") exist, so hand length, hand breadth, foot length, middle finger length etc. can be computed locally rather than quoted — [search summary of ph.health.mil](https://ph.health.mil/topics/workplacehealth/ergo/Pages/Anthropometric-Database.aspx), [overview PDF](https://ph.health.mil/PHC%20Resource%20Library/ANSURIIDatabasesOverview.pdf)
- One secondary source cites an average male hand length of 194 mm from ANSUR data (weak, aggregator) — [Morey blog](https://richarddmorey.medium.com/about-trumps-hands-86fd9a2c7c5)
- VRM 1.0 humanoid: thumb = Metacarpal (optional), Proximal, Distal; other fingers = Proximal, Intermediate, Distal; all finger bones are optional; toes are optional and parent to foot; non-humanoid nodes may sit between humanoid bones (so chain length must be computed along the actual node path, not by humanoid-bone-only distance) — [VRMC_vrm-1.0 humanoid.md](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md)
- VRM naming pattern, e.g. leftIndexProximal / leftIndexIntermediate / leftIndexDistal — [search summary](https://docs.unity3d.com/kr//ScriptReference/HumanBodyBones.html)
- Phalanx ratios: literature is split. A 2003 study found Fibonacci/phi relations in hand bones mathematically unsupported; a later study reports little-finger lengths follow Fibonacci and others a related sequence; one finding says middle + distal phalanx ≈ proximal phalanx length — [Kellogg/Northwestern summary](https://www.kellogg.northwestern.edu/academics-research/research/detail/2003/the-fibonacci-sequence-relationship-to-the-human-hand), [J Nat Sci Med 2021](https://doaj.org/article/95331bf144cd41be9b36472cfdb3530b)
- Hand length / face height and foot length / forearm length "rules of thumb": I searched and found NO supporting source — [search](https://motion-database.humanoids.kit.edu/anthropometric_table) (no confirmation).
- Rigging QA sources list "fused fingers" and "collapsing joints" as failures — [seeles.ai guide](https://www.seeles.ai/resources/blogs/3d-model-rigging-guide)

### Inferences
- Exact checks: per hand, 5 digits; 4 fingers with 3 bones, thumb 2 phalanges + metacarpal; foot has toe bone(s) (VRM: one optional `toes`). Fail on count mismatch.
- Chain-length rule (INFERRED): proximal >= middle >= distal for index to little; middle finger longest; thumb shortest of the five; sum of finger chain/hand length (wrist to middle fingertip) near 0.5-0.6 in real anatomy (INFERRED from general anatomy, not sourced; verify with ANSUR middle-finger length / hand length).
- Rigify names use `.L/.R` and f_index.01/02/03, thumb.01-03 (INFERRED from memory; verify in Blender). In this repo, match with `authoredName(o)` because GLTFLoader strips dots.
- Stylized tolerance: widen all hand/foot ratio bands (e.g. +/-25-30%) and keep topology/count checks strict (INFERRED).
- Compute foot/hand size relative to body height from ANSUR CSV (hand ~10.5-11% of stature, foot ~15% are common textbook values but UNSOURCED here).

### Gaps
- No primary ANSUR II hand/foot means/SDs (blocked); no sourced thumb opposition angle range; no sourced arch metrics (e.g. arch index); no sourced foot-vs-forearm rule.

## 2. Face landmark proportion rules and anime deviation

### Takeaway
Neoclassical canons (thirds, fifths, intercanthal = nasal width) are poorly followed even in real populations, so use them as wide bands. Anime eyes are documented as much larger than real ones, so eye-related rules need a separate stylized band.

### Cited Findings
- Canons: face in equal fifths; the middle fifth is endocanthion-to-endocanthion and should equal alar nose width — [Al-Sebaei 2015, Head & Face Med](https://head-face-med.biomedcentral.com/articles/10.1186/s13005-015-0064-y) (via search summary; page itself blocked)
- Real-population deviation: nose wider than intercanthal distance in 92% of males and 56% of females in a Saudi cohort; in another population intercanthal < nasal width in 98.5% F / 98.1% M; the canons were not validated in Arabian Peninsula young adults — same source and [search summary](https://www.mdedge.com/node/148479)
- Classical (Vitruvius/da Vinci) thirds: chin to nostrils, nostrils to eyebrows, eyebrows to hairline each a third — [discoveringdavinci.com](https://www.discoveringdavinci.com/human-proportion)
- Anime vs real: human eye height 15-33% of nose height vs 30-90% for female anime characters; Japanese animation eyes ~3.4x larger than human (US animation ~2x) — [core.ac.uk record](https://api.core.ac.uk/oai/oai:localhost:310904400/112410) (search summary only; primary text not read, treat as moderate confidence)
- Art-guide heuristics (low-quality sources): eyes about 1/2 down the head, eyes ~1/4 of face height in anime, nose about 1/3 of the way from eyes to mouth — [drawing guide aggregator](https://artisan.accel.com/how-to-draw-anime-faces-the-comprehensive-guide-to-getting-the-proportions-right)

### Inferences
- Use bands, not equalities: eye-line at 0.45-0.60 of head height; ear top near brow, ear bottom near nose base (the ear rule had no sourced numbers); nose and mouth width as fractions of eye span with generous upper bound; flag only gross violations (feature order, symmetry, features outside face silhouette).
- Anime-specific: allow eye width up to ~3x real; require small nose and mouth to remain present (non-zero) rather than hitting a realistic value.
- Repo already has `knowledge/head-targets.json` and `head-shape-audit`; add landmark ratios there, per-style bands.

### Gaps
- No sourced numeric means/SD for inter-ocular vs eye width, mouth vs inter-pupillary, ear position. No peer-reviewed anime landmark proportion study found beyond the eye-size summary.

## 3. Landmark tools for renders vs mesh

### Takeaway
Anime-specific detectors exist (hysts: 28 landmarks, near-frontal only; lbpcascade: boxes only). Mesh-based landmarks (vertex groups, bones, shape-key regions) avoid detector error entirely and are preferred.

### Cited Findings
- hysts/anime-face-detector: detects near-frontal anime faces, YOLOv3 or Faster R-CNN detector plus HRNetV2-W18 heatmap landmark model predicting 28 points; MIT code, mmdet/mmpose vendor code Apache-2.0; README does not state training data — [GitHub](https://github.com/hysts/anime-face-detector), [HF model](https://huggingface.co/hysts/anime-face-detector-hrnetv2)
- Install needs openmim, mmcv-full, mmdet, mmpose; tested only on Ubuntu — [PyPI](https://pypi.org/project/anime-face-detector)
- lbpcascade_animeface: OpenCV Haar-like LBP cascade, face box only, min size 24x24, license not stated; README mentions higher-accuracy animeface-2009 — [GitHub](https://github.com/nagadomi/lbpcascade_animeface)
- MediaPipe Face Landmarker docs describe real-face use; I found no documented accuracy on anime/stylized faces — [docs](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker)

### Inferences
- MediaPipe/dlib are likely unreliable on anime renders (trained on photos; large eyes, tiny nose) — INFERRED, untested. Test on `tests/fixtures/validator/mhs3.png` before trusting.
- Mesh route: use `SOC-`/DEF- bones (eye, jaw), vertex groups for eye/mouth/ear/nose, shape-key delta regions (mouth-open, blink) to get landmark centroids, and bounding boxes in head-local space; ray casts for ear/nose silhouette depth. Deterministic and works at any pose.
- Use the 2D detector only as a render cross-check, with exit code 13 (unknown) when no face is found, never a pass.

### Gaps
- No measured reliability numbers for MediaPipe/dlib/hysts on anime renders; Danbooru-derived landmark datasets (e.g. anime landmark sets) not found in searches.

## 4. Pro pipeline QA checklists (eyes, mouth, teeth, tongue, ears)

### Takeaway
Only generic rig-QA material was found: pose tests, range-of-motion sweeps, deformation checks. No sourced eye/teeth/tongue/ear checklist.

### Cited Findings
- Production rig must pass tests for pose, topology, limb separation, deformation zones, skeleton mapping, skin weights, motion, FBX handoff; automated pose tests and range-of-motion sweeps catch problems early — [seeles.ai](https://www.seeles.ai/resources/blogs/3d-model-rigging-guide)
- Weight failures: collapsing joints, candy-wrapper twist, hard boundaries, stray distant-bone weights; limit to 3-4 influences — [seeles.ai](https://www.seeles.ai/resources/blogs/3d-model-rigging-guide), [sorceress.games](https://sorceress.games/blog/rig-with-auto-rig-for-game-characters-weight-check)

### Inferences
- Face checklist to automate on mesh (INFERRED): eyeballs inside sockets with lids covering at blink=1; mouth-open shape key reveals teeth/tongue meshes that exist and stay inside the head; teeth and tongue not poking through lips at max viseme; ears symmetric and attached; expression keys start at 0 (matches existing pack contract).

### Gaps
- No sourced studio checklists (turntable/expression range) found.

## 5. Automatic hand pose and deformation tests

### Takeaway
Feasible with a pose sweep (curl, spread, fist) plus mesh metrics, but no sourced standard exists; design is inferred.

### Cited Findings
- Common failures: fused fingers, collapsing joints, twisted wrists, candy-wrapper — [seeles.ai](https://www.seeles.ai/resources/blogs/3d-model-rigging-guide)

### Inferences
- Curl test: rotate each phalanx 0 to ~90 deg (proximal) / ~100 (middle) / ~70 (distal) (typical human ROM, UNSOURCED); measure self-intersection (fingers piercing palm), volume change vs rest (candy wrapper/collapse), edge-length stretch ratio, max vertex displacement.
- Spread test: adjacent finger meshes must not interpenetrate; web gap preserved. Fist: fingertips within palm region, no fingers through each other; thumb crosses over index/middle.
- Weight sanity: each hand vertex has <=4 influences, finger vertices dominated by own chain, no weights from other fingers (fused-fingers cause).

### Gaps
- No sourced ROM numbers or automated finger-deformation test implementations found.
