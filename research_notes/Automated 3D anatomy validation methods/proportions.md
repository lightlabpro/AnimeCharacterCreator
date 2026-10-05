# Automated validation of 3D character body proportions

Research limits: wikipedia, PMC, ergocenter.ncsu.edu, libretexts and the Konstanz journal were blocked by the egress proxy for fetches, so several numbers come only from search-result summaries (flagged "search summary"). Nothing here was cross-verified against the primary tables.

## 1. How tools extract landmarks and measurements from a mesh; what is practical with mesh + armature only

### Takeaway
Every credible tool measures the same way: a fixed landmark (vertex id or joint) plus either a point-to-point distance or a plane cut with a convex hull for circumferences, in a neutral T/A pose. For a rigged Blender/glTF character, bone head positions and vertex-group extremes replace the SMPL vertex ids.

### Cited Findings
- SMPL-Anthropometry defines landmarks as vertex IDs (SMPL 6,890 verts, SMPL-X 10,475) in `landmark_definitions.py`; lengths are distances between landmarks; circumferences are plane cuts defined by a landmark point plus two joints giving the normal; face segmentation isolates the right slice when a cut yields several loops; T-pose only; unknown-scale bodies need height normalisation. Measures: height, shoulder breadth, shoulder-to-crotch height, inside leg, arm length, chest/waist/hip/thigh/calf/bicep/neck/head circumferences. — [SMPL-Anthropometry](https://github.com/DavidBoja/SMPL-Anthropometry)
- body_measurements (vcarlosrb) takes SMPL vertices+faces and returns height, chest, hip, waist, thigh, outer/inner leg, neck-hip length, shoulder; needs Trimesh; best in A-pose. Height = vertical extent head top to heel. Circumference = plane intersection then convex hull of the section. — [3d-body-measurements](https://github.com/vcarlosrb/3d-body-measurements), [PyPI](https://pypi.org/project/body-measurements/)
- Other SMPL measurement work: SHAPY (metric + semantic attributes) and "Accurate 3D Body Shape Regression using Metric and Semantic Attributes" use the same height/circumference measurement definitions. — [SHAPY](https://www.github.com/muelea/shapy), [arXiv 2206.07036](https://arxiv.org/pdf/2206.07036)
- MakeHuman: macro sliders (gender, age, muscle, weight, height, proportions, ethnicity) on normalised scales, plus a Measure tab with per-region sliders in chosen units; it is a template mesh transformed by scale factors. — [MakeHuman docs](https://static.makehumancommunity.org/makehuman/docs/gender_random_measure_and_custom.html), [JCU review](https://researchonline.jcu.edu.au/59814/)
- VRM 1.0 humanoid: required bones hips, spine, head, both upper/lower legs, feet, upper/lower arms, hands; optional chest, upperChest, neck, shoulders, toes, eyes, jaw, fingers. The spec does not enforce proportions; only hierarchy and naming. — [VRM humanoid spec](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md)
- ANSUR II: 93 measures on 4,082 men and 1,986 women (US Army), open data. — [OpenLab ANSUR II](https://www.openlab.psu.edu/ansur2/), [ph.health.mil](https://ph.health.mil/topics/workplacehealth/ergo/Pages/Anthropometric-Database.aspx)
- Not found: MB-Lab measurement internals; Meshcapade/BodyM specifics (no useful result).

### Inferences
- Landmark recipe from rig only (no scan): top of head = max Y of head-weighted verts; sole = min Y; crotch height = height of the lowest vertex-group-weighted-to-both-legs slice or bone `upper_leg` head Y minus pelvis offset; shoulder (acromion) height ~ upper_arm head Y; knee = lower_leg head; elbow = lower_arm head; wrist = hand head; chin = head-bone-weighted min Y in the front half; shoulder breadth = X extent of silhouette slice at shoulder bone height (biacromial approximation: distance between the two upper_arm heads is smaller, so use a mesh slice for bideltoid); hip breadth = X extent of the slice at the upper_leg head height (that is bitrochanteric-ish); arm span = X extent in T-pose across fingertips (hand tip vertices). Do this in rest pose, arms out (T or A).
- Circumferences are not needed for the proportion checks; widths from silhouette slices (front orthographic) are enough and robust to loose clothing only if measured on the nude/base body mesh.
- Heads: head height = chin-to-vertex of the head, measured from the mesh; head count = stature / head height.

### Gaps
- No open implementation found that works from bones only for glTF; the above is a design, not a cited method.

## 2. Numeric reference proportions

### Takeaway
Adult realistic reference: roughly 7.0 to 7.5 heads in real adults (8 is an artist's idealisation), sitting height about 0.52 of stature, biacromial about 0.22 to 0.24 of stature, children follow head fractions 1/4 (newborn) to 1/8 (adult).

### Cited Findings
- ANSUR (table "Anthropometric Summary Data Tables", values in inches as returned by search summary, not verified at source): male stature 5th/50th/95th = 64.88/69.09/73.62, SD 2.70; sitting height 33.86/36.14/38.46, SD 1.41; biacromial 15.12/16.34/17.60, SD 0.75; hip breadth 12.13/13.54/15.24, SD 0.95. Female stature 60.04/64.02/68.50, SD 2.53; sitting height 31.61/33.74/35.91, SD 1.37; biacromial 13.19/14.37/15.59, SD 0.72; hip breadth 12.24/13.90/15.75, SD 1.05. — [NCSU ergocenter table](https://www.ergocenter.ncsu.edu/wp-content/uploads/sites/18/2017/09/Anthropometric-Summary-Data-Tables.pdf) (search summary; unclear whether ANSUR II or the older 1988 survey, check)
- Head-to-body by age (textbook-level, coarse): newborn about 1/4 of length; age 2 about 1/5; age 5-6 about 1/6; age 10 just over 1/8 per one source (this conflicts with standard drawing canons of about 1/7 at age 10-12; treat as unreliable); adult 1/8 (drawing idealisation). — [LibreTexts Child Growth](https://socialsci.libretexts.org/Bookshelves/Early_Childhood_Education/Child_Growth_and_Development_(Paris_Ricardo_Rymond_and_Johnson)/04%3A_Physical_Development_in_Infancy_and_Toddlerhood/4.02%3A_Proportions_of_the_Body) (via search summary), [Scientific American](https://www.scientificamerican.com/article/human-body-ratios)
- Shoulder-to-hip ratio: men 1.27 ± 0.09 to 1.30 ± 0.06; women 1.14 ± 0.07 to 1.16 ± 0.06. Waist-to-hip: men 0.97 ± 0.06 to 1.03 ± 0.07, women 0.87 ± 0.10 to 0.89 ± 0.08 (study-dependent, populations differ, some include clothing/obesity). — [Hughes 2003 SHR](https://www.psy.uq.edu.au/~uqbziets/Hughes2003%20-%20Shoulder%20to%20hip%20ratio.pdf) and the PMC tables returned in the same search (e.g. [PMC7366200](https://pmc.ncbi.nlm.nih.gov/articles/PMC7366200/table/tab3))
- Fredriks et al. 2005: Dutch reference charts (14,500 children aged 0-21) for height, sitting height, leg length, sitting height/height by LMS; sitting height/height is negatively correlated with height SDS; cut-offs of +2.5 SD (short) and -2.2 SD (tall) for disproportion. Numeric tables not retrieved. — [Fredriks 2005](https://stefvanbuuren.name/publication/fredriks-2005-b), [ADC](https://adc.bmj.com/content/90/8/807)
- Drillis and Contini (1966) is the standard segment-length-as-fraction-of-stature model; exact constants did not appear in retrievable text. — [Konstanz CPA](https://ojs.ub.uni-konstanz.de/cpa/article/view/292)

### Inferences (computed from the ANSUR values above, plus well-known constants I could not source)
- Mean stature: male 175.5 cm, female 162.6 cm (inches x 2.54).
- Sitting height / stature: male 36.14/69.09 = 0.523; female 33.74/64.02 = 0.527. So leg (stature minus sitting) about 0.477 / 0.473 of stature. Check band: 0.50-0.55 adult realistic.
- Biacromial / stature: male 0.237; female 0.224. Hip breadth / stature: male 0.196; female 0.217. Biacromial / hip breadth: male 1.21; female 1.03 (the SHR studies above use bideltoid, which is larger, hence 1.27-1.30 and 1.14-1.16).
- Z-score spreads: SD of stature about 2.7 in (1.5%), so SD of ratios is small (typically 0.01-0.02 absolute); realistic checks can use mean ± 2 SD of ratios, but SD of ratios is not in the data I retrieved, so use mean ± about 5% as a placeholder band.
- From memory (UNCITED, verify): head about 1/7.5 of stature in real adults; arm span about equals stature (ratio ~1.0 ± 0.03); fingertips reach mid-thigh; crotch at about 0.47-0.52 of height; Loomis/Proko 8-head canon puts nipples at 2 heads, navel at 3, crotch at 4, knees at 6.

### Gaps
- No age-specific numbers for sitting height ratio, shoulder width or leg length at ages 2, 5, 10, 15 retrieved (PMC and Fredriks tables blocked). Old-age changes (stature loss, kyphosis) not found. CDC growth chart head-to-stature not found. Vitruvian and Loomis numbers are uncited here.

## 3. Stylized and anime proportion norms

### Takeaway
Only tutorial-grade sources found; no peer-reviewed survey of anime or VRoid proportions. Norms: realistic 7-8 heads, anime heroic up to 9+, chibi 2-4.

### Cited Findings
- Adults 7-8 heads in realism; anime ranges from 6 heads (compact) to 9 or more (elongated); chibi 2-4 heads, standard 2.5, 2 reads very young/toy-like, 3 reads "chibi-lite"; torso 3-4 heads; arms 2-3 heads. — search results from [Clip Studio Tips](https://tips.clip-studio.com/en-us/articles/4888) and others (aggregator-level; low authority)
- Toon Boom guidance: a standard character is six heads high; cartoony 3 heads. — [Toon Boom](https://learn.toonboom.com/modules/character-design/topic/character-proportions)
- Monster Hunter Stories 2 team chose "more realistic body proportions" than previous entry. No head-count figure found. — [Nintendo Everything](https://nintendoeverything.com/monster-hunter-stories-2-updated-graphics-co-op/)
- Head-to-body ratio used to set apparent age in anime: [Anime Art Academy](https://animeartacademy.artstation.com/projects/qeLrNN) (not read).

### Inferences
- Reasonable per-style head-count bands: realistic adult 7.0-8.0; anime adult 6.5-8.5 (heroic up to 9); teen 6-7.5; child 4.5-6; chibi 2-4. These are my synthesis, not measured.
- MHS3-style target: because the project already pins head proportions to `knowledge/head-targets.json`, derive the head-count band from the reference model rather than from the generic numbers.

### Gaps
- No VRoid default-body measurements, no published anime figure survey, no MHS head count found.

## 4. Turning ranges into pass/fail checks and finding landmarks automatically

### Takeaway
Use per-preset profiles: target ratio, tolerance band (or z-score vs SD), and pass/warn/fail with exit 13 for "not measured" if a landmark cannot be located.

### Cited Findings
- Fredriks proposes SD-score cut-offs on ratio (+2.5 / -2.2 SD) for disproportion, a precedent for z-score gating. — [Fredriks 2005](https://stefvanbuuren.name/publication/fredriks-2005-b)
- Circumference/plane-cut methods use segmentation to avoid picking the wrong loop (e.g. arm vs torso). — [SMPL-Anthropometry](https://github.com/DavidBoja/SMPL-Anthropometry)

### Inferences (design)
- Check = (value - target) / (target * tol_frac), or z = (value - mu) / sd from ANSUR. Realistic profile: pass |z| <= 2; warn 2-3; fail > 3. Stylized profile: replace mu with the style target and widen tolerance to 10-20% per ratio (head count tolerance ±0.5 head), keep hard sanity checks (symmetry, arm span within 0.85-1.15 of stature, limbs positive length, hips below shoulders, knee above ankle).
- Sex difference checks: SHR (bideltoid/hip) male about 1.28, female about 1.15; fail if ordering inverted relative to the preset sex.
- Robust landmark finding: (1) bones for joint heights, (2) vertex-weight argmax per bone for extremes, (3) silhouette slices at bone heights (front ortho depth-free) for widths, (4) fallbacks flagged unknown (exit 13) rather than guessed. Normalise by stature measured from mesh, not by the armature.
- Measure in rest pose; if the pack is A-pose, measure widths after bounding by bone positions, not hand tips.

### Gaps
- No published per-style tolerance values; the tolerance numbers above are proposals to calibrate on `tests/fixtures/validator` real images, as CLAUDE.md already does for other floors.
