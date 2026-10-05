# Designing a trustworthy pass/fail anatomy validator without per-character references

Scope note: about 13 searches were run, with no page fetches beyond search summaries. Claims marked "Cited" come from search summaries of the linked sources. Everything else is under Inferences and is my design judgment, not published fact. Some topics (VRM validators, UniVRM docs, CAD/FEM mesh checkers, the full Hi3DEval and 3DGen-Bench details) were not researched in depth and are listed under Gaps.

## 1. Statistical shape and pose priors, and a corpus-based "fingerprint"

### Takeaway
Body-model research already uses a statistical prior as a plausibility check: PCA shape spaces (SMPL), a learned pose prior (VPoser) and pose-conditioned joint limits. The same pattern transfers to stylised characters if the prior is built from a character corpus and expressed as a vector of ratios. Anime3D++ (VRoid Hub derived) is the obvious corpus, but licensing is the practical blocker.

### Cited Findings
- SMPL is learned from thousands of 3D body scans. Its shape space is PCA-based, with up to 300 components available and 10 used by default (`betas`). — [SMPL site](https://smpl.is.tue.mpg.de/), [smplx body_models.py](https://huggingface.co/spaces/Yuliang/ECON/blob/refs%2Fpr%2F3/lib/smplx/body_models.py)
- SMPL data is licensed for non-commercial research only. — [SMPL license](https://smpl.is.tue.mpg.de/license.html)
- VPoser is a variational autoencoder pose prior trained on AMASS. It is differentiable, penalises impossible poses while admitting valid ones, and models correlations among joints. It is used in SMPLify-X. — [human_body_prior repo](https://github.com/nghorbani/human_body_prior), [Expressive Body Capture](https://arxiv.org/pdf/1904.05866)
- Akhter and Black (CVPR 2015) argue that simple pose priors admit invalid poses because they ignore that joint limits vary with pose. They learn pose-dependent joint limits from a gymnast mocap dataset. — [MPI page](https://is.mpg.de/publications/akhter-cvpr-2015), [code and data](https://ps.is.tuebingen.mpg.de/code/poseprior)
- Anime3D (the dataset used by StdGEN) collected about 14,000 VRoid Hub models. Anime3D++ filtered these to 10,811 high-quality models, standardised in A-pose with arms 45 degrees down, with renders and semantic maps. — [StdGEN](https://arxiv.org/pdf/2411.05738), [StdGEN++](https://arxiv.org/pdf/2601.07660)
- VRoid Hub's terms prohibit reverse engineering data in the service. Preview data is deliberately mangled, and uploaded files are not public unless download is permitted. VRM licensing lets each author set redistribution and adaptation permissions in the licence settings. — [VRoid Hub content protection policy](https://hub.vroid.com/en/content-protection-policy), [VRM licence PDF](https://vrm.dev/licenses/1.0/pdf/en.pdf), [VRoid conditions of use](https://developer.vroid.com/en/guidelines/conditions_of_use.html)

### Inferences
- Fingerprint: compute a vector of scale-free ratios from the DEF- skeleton and mesh. Candidates: head height / total height, leg length / height, arm span / height, shoulder width / head width, upper arm / forearm, thigh / shin, hand length / face height, torso length / leg length, eye separation / face width, neck length / head height. Normalise by stature or head height so absolute scale drops out.
- Score: per-ratio robust z, plus a joint Mahalanobis distance computed with a robust covariance (for example MCD) on the ratios. Report the per-ratio z first, because it names the landmark. The joint distance catches combinations that are individually normal but jointly odd.
- Treat the SMPL shape space as a sanity reference for the realistic-proportion profile only. Its licence is non-commercial, and its PCA space does not describe chibi or exaggerated anime proportions.
- Do not ship a VPoser-style learned pose prior. A pose prior only matters for posed or POSE- clips. For rest pose, joint-limit rules (Akhter-style limits, written as hand-set per-bone ranges) are enough.
- Corpus source for this repo: use only models whose VRM licence permits this use, or models the user authored or owns. Store only the derived ratio vectors, not the meshes. That keeps the redistribution problem small. Mixamo, MakeHuman and SMPL give realistic anchors. Mixamo and MakeHuman licence terms were not verified here.

### Gaps
- I did not verify the Anime3D / CharacterGen dataset release licence, or whether the data is downloadable.
- I did not verify Mixamo or MakeHuman licence terms for statistics extraction.
- I did not research STAR or GHUM shape spaces.

## 2. Calibrating thresholds from a corpus

### Takeaway
Use robust statistics (median and MAD) with per-style profiles. Set hard-fail bands wide and warn bands narrow. Validate the false-alarm rate on a held-out set of known-good characters.

### Cited Findings
- Modified z-score: z_m = 0.6745 (x - median) / MAD. Iglewicz and Hoaglin flag |z_m| > 3.5. It has a 50% breakdown point and is suited to small samples or contaminated data. — [MetricGate modified z-score reference](https://metricgate.com/calculator/robust-z-score-modified), [comparison](https://metricgate.com/blogs/zscore-vs-modified-zscore/) (secondary source, not the original text)
- Conformal prediction uses an independent calibration set, takes a quantile of nonconformity scores as the threshold, and gives distribution-free coverage guarantees. — [Gentle Introduction to Conformal Prediction](https://arxiv.org/pdf/2107.07511)

### Inferences
- Procedure: (1) split the corpus into calibration and held-out test, split by author or source so near-duplicates do not straddle the split; (2) cluster or label styles (realistic, anime A-pose, chibi, MHS3-like) and compute per-style median and MAD; (3) set warn at |z_m| around 3.5 and fail at a larger value or at the corpus min/max plus a margin; (4) measure the false-alarm rate on the held-out set. Aim for under about 1% on known-good characters for hard fails.
- Conformal framing: choose the fail threshold as the (1 - alpha) quantile of per-ratio score on the calibration set, giving an explicit expected false-alarm rate alpha for in-distribution characters. This guarantee is only valid for characters exchangeable with the corpus, so it does not cover out-of-style inputs.
- Sample size: no published figure found for this use. Rule of thumb, my own: at least 30 to 50 per style for a median and MAD, and several hundred before trusting a 1st or 99th percentile band. Fewer than about 20 in a style should yield "unknown", not a band.
- Pitfalls: VRoid Hub skews to young female A-pose characters, so tails of other styles look like outliers; stylistic drift over time; correlated ratios (one body scale drives many); and Goodhart effects when an agent iterates until the numbers pass.
- Anchor each threshold to a landmark with a plain-language meaning so it can be sanity-checked against pictures, not just against the corpus.

### Gaps
- No published sample-size guidance for anatomy-ratio bands was found.
- Per-style profile construction for anime proportions (for example head-to-body ratio distributions) has no source here.

## 3. Learned plausibility models and VLM review

### Takeaway
Published learned 3D quality scorers exist, but they target generated object quality as judged by human preference, not anatomical correctness. VLMs are unreliable on hands, limbs and proportions, so use them only as a gated, structured, advisory reviewer.

### Cited Findings
- Hi3DEval (NeurIPS 2025) is a hierarchical evaluation framework covering object-level and part-level quality plus material evaluation. It ships Hi3DBench with a multi-agent annotation pipeline, uses video-based representations for object-level evaluation and pretrained 3D features for part-level perception, and reports better alignment with human preference than image-based metrics. — [Hi3DEval](https://arxiv.org/html/2508.05609v1), [NeurIPS page](https://neurips.cc/virtual/2025/poster/121787)
- 3DGen-Bench has 11,200 models from 19 generators, over 68,000 preference votes and more than 56,000 score labels. It trains two scorers, 3DGen-Score and 3DGen-Eval, and evaluates on five criteria. — [3DGen-Bench](https://arxiv.org/pdf/2503.21745)
- Gen3DEval uses vision-LLMs to evaluate generated 3D objects. — [Gen3DEval](https://arxiv.org/html/2504.08125v1) (title only seen in search results)
- HandVQA (over 1.6M multiple-choice questions on hand anatomy) found that VLMs including LLaVA, Qwen-VL and mPLUG struggle with fine-grained spatial reasoning about hands and hallucinate finger parts. — [HandVQA summary](https://chatpaper.com/es/paper/291977)
- A report cited in the same search describes VLMs failing to detect anatomically incorrect paw structures (fused or extra digits). — [UNIST record](https://scholarworks.unist.ac.kr/handle/201301/88295) (summary only, not read in full)
- LLM judges show position bias, self-preference bias and limited cross-judge agreement (reported kappa 0.51 in one study, Fleiss kappa 0.357 in another). Semantically equivalent prompts changed majority outcomes in about 25% of cases in one study. The cited mitigations are multi-trial aggregation, position randomisation and explicit uncertainty reporting. — [Coin Flip Judge](https://arxiv.org/pdf/2606.13685), [Position bias study](https://arxiv.org/html/2406.07791v7)

### Inferences
- No published learned scorer for "is this character's anatomy correct" was found. Hi3DEval and 3DGen-Bench scorers were trained on generator outputs, so using them as an anatomy pass/fail gate would be an unvalidated transfer. Treat them as an optional extra signal at most.
- Reliable VLM structure, my recommendation: fixed views (front, side, three-quarter, back) rendered by the existing capture pipeline; per-region crops (hands, face, feet, shoulders) rather than whole-body images; a closed checklist with yes/no/cannot-see answers per item; the geometric validator's measured numbers given as context; at least two independent reviewers with different prompts or models, with position randomisation; disagreement maps to "unknown", never to pass.
- Never let a VLM override a geometric fail. A VLM can raise a fail or flag "unknown", but a VLM-only "pass" must not clear a metric-based failure.
- Counting tasks (fingers, limbs) are better done geometrically from rig data (bone counts, DEF- chains) than by VLM, given the cited weaknesses.

### Gaps
- Part-level scoring details in Hi3DEval and 3DGen-Bench were not read in full.
- No measured VLM accuracy figure on stylised or anime anatomy errors was found.

## 4. Pass/fail design patterns

### Takeaway
Use tri-state outputs, hard rules separated from soft scores, per-region checks, severities, and explanations that name a landmark and a fix. Protect against gaming with held-out checks.

### Cited Findings
- The repo's own convention already has exit codes 0 pass, 12 failed, 13 unknown, 2 usage. — `/home/user/AnimeCharacterCreator/CLAUDE.md`
- glTF-Validator has four severities (Error, Warning, Info, Hint), designed to match VS Code diagnostic levels. Error means a definite spec violation, Warning means not a guaranteed failure but not good, Info means optimisable without harm, Hint means best practice. — [glTF-Validator issue #14](https://github.com/khronosgroup/gltf-validator/issues/14), [Vulkan docs on validation](https://docs.vulkan.org/tutorial/latest/Advanced_glTF/Tooling_Production_Pipeline/03_validation.html)
- VRChat ranks avatars Excellent / Good / Medium / Poor / Very Poor from metrics (polygons, materials, textures, animator complexity, PhysBones). The documented advice is to aim for Good and Medium is fine. — [VRChat performance ranks](https://creators.vrchat.com:443/avatars/avatar-performance-ranking-system)

### Inferences
- Output schema per finding: id, severity (error / warn / info), region (for example `hand.L`), landmark pair, measured value, corpus percentile or robust z, expected band, and a fix sentence ("shorten DEF-forearm.L by about 12%"). An overall verdict is the worst severity, with unknown if any required check was not measured.
- Do not average. A good body must not mask a bad hand. Keep one verdict per region and gate on the worst.
- Hard rules (binary, no corpus needed): bone chain exists, left/right symmetry within tolerance, no self-intersection at rest pose, joint order and parenting valid, limb counts, non-degenerate scales. Soft scores (corpus based): proportion ratios. Only hard rules and wide-band soft scores may produce a fail; narrower bands produce warn.
- Unknown (13) is for: a landmark missing, a style with too few corpus samples, a view not rendered, VLM reviewers disagreeing. Unknown must never count as pass, matching the repo's convention.
- Ratchet: store the validator result for known-good fixtures and fail CI if a change flips any of them, or if the false-alarm rate on the held-out set rises. This is the repo's calibration-file approach extended with a held-out set.
- Anti-gaming for an iterating agent: keep a held-out set of checks and characters not described in the skill text; show the agent only the failing landmark and direction, not the numeric threshold; report values rounded; periodically rotate a hidden check (an independent measurement of the same property, for example mesh-derived limb length in addition to bone-derived). Anything an agent can see and iterate against will be optimised, so the final gate should include something it cannot see (a human or independent review).
- Style handling: require the author to declare a style profile (realistic, anime, chibi), and show the style in the report. Do not auto-guess it silently. If the declared style disagrees with a classifier on head-to-body ratio, emit warn.

### Gaps
- VRM validators, UniVRM import warnings, VRChat Avatar Doctor, Unity/Unreal import validators, and CAD/FEM mesh quality checkers were not researched beyond the VRChat rank page and glTF-Validator severities.
- No evidence on how well hidden-threshold designs resist agent gaming; that is my reasoning from Goodhart-type effects, not a cited result.

## Recommended build order (all inferred)
1. Hard rules with explainable output and tri-state exit codes.
2. Ratio fingerprint with per-style median/MAD bands from a small, licence-clean corpus (author-owned plus permitted VRM).
3. Held-out false-alarm measurement, calibration file and ratchet test.
4. Optional structured two-reviewer VLM pass, advisory only, disagreement gives unknown.
