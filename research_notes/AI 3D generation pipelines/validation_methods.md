# Automated validation of rendered 3D character images against a reference (Blender gating loop)

Research caveat: arxiv.org was blocked by the egress proxy for WebFetch, so only search-result snippets could be used as evidence. Items from general knowledge are placed under Inferences (not Cited Findings) and flagged as unverified.

## Pixel/structural metrics (SSIM, PSNR, edges, silhouette IoU, color) and robustness to offsets

### Takeaway
SSIM via scikit-image runs on numpy only and must be configured explicitly (data_range, Gaussian weights). Edge, silhouette and color metrics are not covered by sources found here; they are standard numpy/OpenCV techniques that should be verified empirically on your renders.

### Cited Findings
- scikit-image `structural_similarity`: pass `data_range` explicitly because the dtype-based estimate can be wrong for float images — [scikit-image source](https://github.com/scikit-image/scikit-image/blob/v0.23.2/skimage/metrics/_structural_similarity.py)
- To match Wang et al. SSIM, set `gaussian_weights=True`, `sigma=1.5`, `use_sample_covariance=False`; with gaussian_weights, win_size is ignored — [scikit-image source](https://github.com/scikit-image/scikit-image/blob/v0.23.2/skimage/metrics/_structural_similarity.py)
- LPIPS and similar metrics work at pixel/patch level and miss mid-level layout, pose and semantic similarity (DreamSim motivation) — [DreamSim, NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/9f09f316a3eaf59d9ced5ffaefe97e0f-Abstract.html)
- A 2025 benchmark of image-similarity metrics for novel view synthesis exists and is worth reading for which metrics track human judgment under small view shifts — [arXiv 2506.12563](https://arxiv.org/abs/2506.12563v1) (not read in full)

### Inferences (unverified, from general knowledge)
- SSIM/PSNR penalize any pixel shift, so for a reference that is concept art (different pose/camera) they are near-useless as a gate; use them only on same-camera renders (e.g. regression between iterations of the same model) or after alignment.
- Robustness recipes: compare at downsampled/blurred scale (Gaussian sigma 2-4 px); align by silhouette bounding box/centroid and scale before comparing; take max score over a small grid of translations/scales (cv2.matchTemplate or ECC `cv2.findTransformECC`); compare edge maps via distance transforms (chamfer) rather than raw overlap, so 1-3 px offsets cost little.
- Silhouette IoU: threshold alpha (Blender film transparent) or background color; normalize by bbox before IoU; good for proportions (head size, limb length, hair volume), blind to interior detail.
- Color: convert to Lab, compare k-means palettes (k=5-8) with CIEDE2000 (`skimage.color.deltaE_ciede2000`), or per-region (hair/skin/eyes) masked mean color; ignores layout so tolerant of pose changes.
- numpy + Pillow only: PSNR, silhouette IoU, histogram distance, banding stats, Sobel/DoG edges, simple SSIM (own implementation). scikit-image adds SSIM, CIEDE2000, Canny; OpenCV adds distance transform, ECC alignment, Hough/contours.

### Gaps
- No sourced evidence on chamfer/edge-overlap robustness or CIEDE2000 usage for toon renders; no source found on multi-scale alignment best practices.

## Perceptual/embedding and anime-specific metrics

### Takeaway
LPIPS/DISTS are available offline on CPU through pyiqa (torch required); DINOv2 gives strong general instance-level features; DreamSim claims better holistic agreement than LPIPS/DINO/CLIP. Anime tagging (WD14) exists as ONNX/HF models usable for tag-overlap checks; no sourced anime-specific aesthetic scorer or ArcFace-on-anime evidence was found.

### Cited Findings
- pyiqa implements many full- and no-reference metrics including LPIPS, DISTS, PieAPP, AHIQ; `pyiqa.list_models()` lists them; `pyiqa.create_metric('lpips', device=...)` — [PyPI pyiqa](https://pypi.org/project/pyiqa/0.1.7)
- DINOv2: self-supervised ViT features trained on curated 142M images; strong at instance retrieval and dense tasks without fine-tuning — [DINOv2 paper](https://arxiv.org/abs/2304.07193v1), [summary](https://huggingface.co/papers/2304.07193)
- DreamSim reports better alignment with human similarity judgments than LPIPS and DINO/CLIP embeddings, and is more robust to minor defects while capturing high-level similarity — [DreamSim](https://proceedings.neurips.cc/paper_files/paper/2023/hash/9f09f316a3eaf59d9ced5ffaefe97e0f-Abstract.html)
- WD14 tagger (SmilingWolf) predicts booru-style general, character and rating tags; variants include wd-swinv2/convnext/vit-tagger-v3 and wd-v1-4-moat-tagger-v2 — [WD14 overview](https://scrapbox.io/work4ai/WD14-tagger), [HF space app](https://www.huggingface.co/spaces/SmilingWolf/wd-tagger/blob/main/app.py)

### Inferences (unverified)
- Use DINOv2 CLS/patch cosine similarity on background-masked, cropped-to-bbox images, compared to a reference from similar view; treat as a coarse "same character" signal, not a defect detector.
- WD14 tag overlap: compare sets for hair color, hair length, eye color, clothing tags, "1girl/solo"; use as checklist (required tags present with prob > ~0.5, forbidden tags absent). Cheap, offline (ONNX CPU).
- Face metrics: MediaPipe face landmarks often fail on stylized faces; ArcFace is trained on photos and is unreliable for anime; prefer DINO/CLIP crops of the face region or anime face detectors. This is an unsourced judgment — test before relying on it.
- CLIP/SigLIP: weak for fine geometry; useful for "does this look like <description>" semantic gating and as the quality prior (T3Bench/3DGen-Score use CLIP-based scoring).

### Gaps
- No sources found for anime-specific aesthetic scorers, anime face detectors, ArcFace on anime, or DISTS/LPIPS thresholds on toon renders.

## VLM-as-judge and generative-3D evaluation benchmarks

### Takeaway
Generative-3D research evaluates via multi-view renders scored by CLIP-style models and GPT-4V, with pairwise comparison and Elo (GPTEval3D), human-preference datasets (3DGen-Bench), and hierarchical/part-level scoring (Hi3DEval). LLM judges have documented position, verbosity and self-preference biases, so rubrics must be structured and order-swapped.

### Cited Findings
- GPTEval3D: GPT-4V is prompted to compare two 3D assets on user-defined criteria; results become Elo ratings; reported strong alignment with human preference; uses 120 RGB and normal-map renderings per prompt; code at 3DTopia/GPTEval3D — [CVPR 2024 paper](https://openaccess.thecvf.com/content/CVPR2024/html/Wu_GPT-4Vision_is_a_Human-Aligned_Evaluator_for_Text-to-3D_Generation_CVPR_2024_paper.html), [arXiv 2401.04092](https://arxiv.org/pdf/2401.04092)
- T3Bench: 300 prompts at 3 complexity levels; quality metric = multi-view text-image scores plus regional convolution (to catch view inconsistency); alignment metric = multi-view captioning plus GPT-4 evaluation; both correlate with human judgments — [T3Bench](https://arxiv.org/pdf/2310.02977)
- 3DGen-Bench: multi-dimension human preference dataset gathered via 3DGen-Arena from public users and experts; trains CLIP-based 3DGen-Score and MLLM-based 3DGen-Eval; reported better correlation with human ranks than existing metrics — [3DGen-Bench](https://arxiv.org/pdf/2503.21745)
- Hi3DEval (NeurIPS 2025): object-level plus part-level evaluation, material realism (albedo, saturation, metallicness), video-based object-level scoring, pretrained 3D features for part-level; outperforms image-based metrics in human alignment — [Hi3DEval](https://arxiv.org/pdf/2508.05609)
- 3D Arena: open platform for human-preference evaluation of generative 3D — [arXiv 2506.18787](https://arxiv.org/html/2506.18787v1)
- LLM judge biases: position bias (GPT-4 kept the same verdict on only 65% of order-swapped pairs in one cited study), verbosity bias, self-preference bias (preference for lower-perplexity text); one analysis argues verbosity/self-enhancement biases are partly manifestations of position bias — [LLM-judge bias summary results](https://arxiv.org/pdf/2406.07791v5), [Self-preference bias](https://arxiv.org/pdf/2410.21819), [Survey](https://arxiv.org/pdf/2411.15594)

### Inferences (unverified)
- Rubric design: one criterion per call (silhouette/proportions, face/eyes, hair shape, outline, shading, color match, artifacts like holes/z-fighting/floating geometry); require a 0-3 or pass/fail score plus a quoted visual evidence sentence per criterion; give reference and render in both orders and average or require agreement; include anchored examples; ask for defect lists first, then scores; ask "what is wrong" rather than "how good".
- Use VLM verdicts only as soft signals and calibrate on ~20-50 hand-labeled good/bad renders; never let the VLM be the sole hard gate.
- Hi3DEval/3DGen-Eval models are heavy (GPU, multi-view video) and aimed at text-to-3D; likely overkill for CPU-only offline use. I did not verify their hardware requirements or license.
- Details of GPTEval3D's 5 criteria and 3DGen-Bench dimension counts could not be retrieved (arxiv blocked).

### Gaps
- Exact GPTEval3D prompt template, criteria and correlation numbers; 3DGen-Bench annotation counts; MATE-3D was not found/searched successfully; VLM reliability for anime-specific defects has no source.

## Toon/NPR statistics

### Takeaway
No sources found; these are simple image statistics to implement and calibrate on your own renders.

### Cited Findings
- None found.

### Inferences (unverified)
- Tone levels/banding: quantize luminance of masked character region (or Lab L), count histogram peaks/occupied bins with >1-2% mass; toon target is e.g. 2-3 dominant L clusters (k-means on L, check cluster separation and that between-cluster gradient pixels are a small fraction).
- Shadow edge hardness: take gradient magnitude of L along shading boundaries; hardness = fraction of transition pixels (between two clusters) that are within <= 2-3 px width; soft gradients give wide transitions.
- Outline thickness consistency: threshold dark pixels adjacent to silhouette, take distance transform ridge/medial width along outline; report median and coefficient of variation; compare median thickness (px at fixed render res) to target and across views.
- Shadow hue: compare mean Lab/HSV hue and chroma of shadow cluster vs lit cluster; warm/cool shift = hue difference and chroma ratio; grey shadow = shadow chroma much lower than lit chroma (e.g. ratio < ~0.5).
- Render at fixed resolution with Filmic/Standard view transform and no AA differences, to keep thresholds stable.

### Gaps
- No empirical thresholds sourced.

## Gating loop design, anti-gaming, plateau handling, tooling

### Takeaway
Treat metrics as proxies: optimizing against them produces gaming (Goodhart). Use multiple independent metrics, hidden/held-out checks, hard-fail for objective defects, and escalate when scores plateau.

### Cited Findings
- Goodhart's law applied to ML: optimizing an imperfect proxy reward, proxy score keeps rising while true ("gold") quality peaks then falls; the gap grows predictably with optimization strength — [Gao et al., Scaling Laws for Reward Model Overoptimization](https://proceedings.mlr.press/v202/gao23h.html), [arXiv 2210.10760](https://arxiv.org/pdf/2210.10760), [OpenAI summary](https://openai.com/index/scaling-laws-for-reward-model-overoptimization/)
- Reward-hacking survey for large models — [arXiv 2604.13602](https://arxiv.org/pdf/2604.13602)
- pyiqa is pure python/pytorch with backprop-capable FR metrics (LPIPS, DISTS) — [PyPI pyiqa](https://pypi.org/project/pyiqa/0.1.5/)
- Multi-view evaluation is standard in generative-3D benchmarks (GPTEval3D 120 renders; T3Bench multi-view scoring) — see above sources.

### Inferences (unverified)
- Gate structure: fixed cameras (front, 3/4 L/R, side, back, face close-up, plus a lighting variant), fixed resolution and seed. Hard-fail (any view): empty/clipped silhouette, silhouette IoU below floor, missing required WD14 tags, outline thickness outside range, NaN/black/pink-texture pixels, VLM-identified geometry artifact confirmed by 2 order-swapped calls. Soft-fail: weighted aggregate of DINO/CLIP/palette/toon stats with per-criterion thresholds; pass requires all criteria above their floor, not a weighted mean (avoids compensation).
- Regression: store per-iteration metrics, renders, parameter diff and VLM rationale in JSON (iteration index, git hash, .blend hash); fail if any previously-passing criterion drops by > epsilon.
- Anti-gaming: do not show the agent exact metric formulas or thresholds; keep a held-out view/camera and a VLM check not used for optimization; compare against reference by multiple metric families; require the fix to be explained by a specific defect; spot-check with human review of final result.
- Plateau detection: if best aggregate improves < delta over N=3 iterations or oscillates, escalate (change strategy, ask human, reduce scope to failing criterion, or revert to best-so-far).
- Minimal deps: numpy + Pillow (PSNR, IoU, palette, banding, histogram, own Sobel); + scikit-image (SSIM, CIEDE2000, Canny); + opencv-python-headless (distance transform, ECC alignment, contours); + torch (LPIPS/DISTS via pyiqa, DINOv2, CLIP) optional. Blender's bundled Python can `pip install` numpy/Pillow/opencv; torch is large — better to run scoring in a separate venv on saved PNGs.

### Gaps
- No sourced practitioner posts on closed-loop render-and-critique validators; no evidence on typical thresholds. Suggest calibrating on a labeled set of own good/bad renders.
