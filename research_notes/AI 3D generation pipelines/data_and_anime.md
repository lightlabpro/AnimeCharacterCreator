# Training Data, Scaling, and Anime/Stylized Character Generation for AI 3D Generators

Research caveat: arxiv.org and huggingface.co were blocked by the network proxy, so only search-result summaries and some third-party pages were available. Claims below come from search snippets; primary papers were not read in full.

## Datasets and curation (Objaverse, Objaverse-XL, TRELLIS-500K, VRoid sets, licensing)

### Takeaway
Open 3D generators are trained mostly on curated subsets of Objaverse/Objaverse-XL (plus ABO, 3D-FUTURE, HSSD) rendered into multi-view images. Anime-specific data is a small, separate VRoid Hub-derived niche (about 14k models). Licensing and artist consent around Objaverse are contested.

### Cited Findings
- Objaverse-XL has over 10M deduplicated 3D objects, up from about 800K in Objaverse 1.0. Sources include GitHub (500k+ repos), Thingiverse, Sketchfab, Polycam and the Smithsonian. — [Stability AI](https://www.stability.ai/research/objaverse-xl-a-colossal-universe-of-3d-objects), [LAION](https://laion.ai/blog/objaverse-xl/)
- Zero123 trained on over 100M multi-view rendered images from Objaverse-XL showed strong zero-shot generalization, evidence that scale of rendered data drives results. — [DeepAI/NeurIPS 2023 summary](https://www.deepai.org/publication/objaverse-xl-a-universe-of-10m-3d-objects)
- TRELLIS (Microsoft) trained models of up to 2B parameters on TRELLIS-500K, 500K assets curated from Objaverse(XL), ABO, 3D-FUTURE and HSSD. This shows that curation (500K selected from a much larger pool) rather than raw count was used. — [HF paper page via search](https://huggingface.co/papers/2412.01506), [GitHub](https://github.com/microsoft/TRELLIS)
- Hunyuan3D 2.0 (Jan 2025) uses a two-stage pipeline, a flow-based diffusion transformer (Hunyuan3D-DiT) for shape and Hunyuan3D-Paint for texture. The ShapeVAE uses mesh surface importance sampling and variable token length. Texturing is decoupled from shape, so handcrafted meshes can be textured too. — [arXiv 2501.12202 via search](https://arxiv.org/html/2501.12202v3)
- Objaverse licensing: objects are CC-BY, CC-BY-NC, CC-BY-NC-SA, CC-BY-SA or CC0. Artist-community critics said creators were not properly credited. Sketchfab's CEO said the models were scraped before the NoAI tag existed. Critics also claim Sketchfab's ToS prohibits generative-AI use. — [FlippedNormals](https://blog.flippednormals.com/objaverse-raises-concerns-about-ethics-of-scraping-3d-content/), [3DVF](https://3dvf.com/en/ai-this-massive-dataset-of-3d-objects-is-a-game-change-heres-why-it-may-include-some-of-your-3d-assets/)

### Inferences
- Commercial tools (Meshy, Tripo) likely mix open data with licensed or proprietary sets, but I found no sourced confirmation of their data.
- Anything built on Objaverse derivatives inherits mixed and NC license risk; this matters for a commercial asset library.

### Gaps
- No primary-source details on quality scoring, aesthetic filtering or VLM captioning pipelines (paper pages blocked).
- ShapeNet, Thingi10K and TurboSquid/Sketchfab-licensed set specifics were not found.
- No confirmed training data for Meshy or Tripo.

## Scaling and preference optimization (DreamReward, DreamDPO, DSO)

### Takeaway
Preference/feedback alignment exists for 3D but is mostly research-stage and optimization-based; none of the sources I found targets aesthetic or anime quality specifically.

### Cited Findings
- DreamReward: Reward3D is a text-to-3D preference reward model built on ImageReward architecture, trained on 25k expert comparisons (ratings of 1-6 on text-3D alignment, overall quality, multi-view consistency). DreamFL tunes multi-view diffusion with it (ECCV 2024). — [Moonlight review](https://www.themoonlight.io/en/review/dreamreward-text-to-3d-generation-with-human-preference), [ECCV page](https://www.ecva.net/papers/eccv_2024/papers_ECCV/html/8897_ECCV_2024_paper.php)
- DreamDPO (ICML 2025): builds pairwise examples, ranks them with reward models or large multimodal models, and optimizes the 3D representation with a preference loss. — [PMLR](https://proceedings.mlr.press/v267/zhou25ae.html)
- DSO (ICCV 2025, Oxford VGG): fine-tunes a feed-forward 3D generator with DPO or a new DRO objective, using stability scores from a non-differentiable physics simulator. It can self-improve on its own outputs without ground-truth 3D. — [CVF](https://openaccess.thecvf.com/content/ICCV2025/html/Li_DSO_Aligning_3D_Generators_with_Simulation_Feedback_for_Physical_Soundness_ICCV_2025_paper.html), [arXiv HTML](https://arxiv.org/html/2503.22677v2)

### Inferences
- A similar loop with a toon-style or anime-aesthetic reward (e.g. artist-rated preferences) is plausible but I found no published example.

### Gaps
- No sourced compute/model-size figures for commercial companies, and no evidence of RLHF at Meshy/Tripo.
- Artist-quality fine-tuning practices are undocumented in what I could access.

## Anime / stylized character generation (research and tools)

### Takeaway
Anime-specific research is built on VRoid Hub data with pose canonicalization and semantic decomposition (body/clothes/hair). Commercial tools offer anime/cartoon style presets, but sourced detail on their quality is thin.

### Cited Findings
- CharacterGen (SIGGRAPH 2024) introduced the Anime3D dataset: 13,746 VRoid Hub characters rendered in multiple views and poses (A-pose plus Mixamo animations). It uses an image-conditioned multi-view diffusion model that canonicalizes pose, then a transformer sparse-view reconstruction model. — [arXiv 2402.17214 via search](https://arxiv.org/html/2402.17214v3)
- StdGEN: semantic-decomposed 3D character generation from a single image. Its Anime3D++ dataset filtered about 14,000 VRoid-Hub models to 10,811 high-quality A-pose models. — [arXiv 2411.05738](https://arxiv.org/pdf/2411.05738)
- StdGEN++ (Jan 2026): Anime3D-EX extends this, with renders for three configurations (complete model, body with clothing, base body alone), supporting decomposed, rig-ready characters. — [arXiv 2601.07660](https://arxiv.org/pdf/2601.07660)
- Meshy lists art styles including realistic, 2.5D cartoon, Japanese anime, and untextured base mesh; image-to-3D accepts a style prompt or style image. — [Meshy features page via search](https://www.meshy.ai/features/text-to-texture), [Scenario help](https://help.scenario.com/en/articles/meshy-the-essentials/)
- Tripo Studio offers style presets (Cartoon, Clay, Steampunk, Barbie, etc.) and one-click mesh stylization to voxel or LEGO looks; no dedicated anime preset was found in these sources. — [Tripo blog](https://www.tripo3d.ai/blog/how-to-achieve-different-artistic-styles)
- Blender toon workflow: cel shading uses flat light/shadow bands; inverted-hull outlines (Solidify modifier) are the non-destructive standard; special hair specular shaders create anime highlights. — [strayspark blog](https://www.strayspark.studio/blog/how-to-get-anime-toon-look-blender)

### Inferences
- Why anime is hard (my reasoning, not sourced): general 3D data is PBR/realistic, so generators bake in lighting and shading that fight cel shading; hair is clumped sheets/cards rather than strands; faces and eyes are painted textures. Decomposition into body/clothes/hair (StdGEN) and VRoid-derived training data address this directly.
- VRoid-derived data skews toward one avatar topology and style, so generalization to arbitrary anime designs is limited.

### Gaps
- No sourced coverage of Illustrious/NovelAI/Animagine multi-view sheet consistency, turnaround-sheet-to-3D tools, toon texture baking issues, or VRoid Hub licensing terms (VRoid models have per-model usage conditions; not verified).
- No sourced artist workflow posts on concept -> multi-view sheet -> 3D -> Blender cleanup; the Blender search returned only generic toon-shading tutorials.
- Quantitative quality comparisons of Meshy vs Tripo on anime characters were not found.
