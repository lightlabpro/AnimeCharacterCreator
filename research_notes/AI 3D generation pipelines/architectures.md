# Core generative architectures behind modern text-to-3D / image-to-3D

Research caveat: arxiv.org and docs.meshy.ai were blocked for direct fetch in this session, so findings come from web-search snippets (which quote arXiv abstracts/READMEs) plus one GitHub README fetch. Items from background knowledge that I could not re-verify are listed under Gaps/Inferences and marked UNVERIFIED.

## 1. SDS / DreamFusion lineage: how it works, why slow, why industry left

### Takeaway
SDS-family methods optimize a per-prompt 3D representation (NeRF/mesh) against a frozen 2D diffusion model. They suffer from over-saturation, over-smoothing and low diversity, and need a per-asset optimization loop. The industry moved to feed-forward and 3D-native models.

### Cited Findings
- DreamFusion uses a pretrained large-scale text-to-image diffusion model and introduces Score Distillation Sampling (SDS), optimizing a 3D representation so that rendered images have high likelihood under the diffusion model. — [ProlificDreamer search summary](https://arxiv.org/pdf/2305.16213)
- SDS "often suffers from over-saturation, over-smoothing, and low-diversity problems." — [ProlificDreamer](https://arxiv.org/pdf/2305.16213)
- ProlificDreamer (NeurIPS 2023) proposes Variational Score Distillation (VSD), treating the 3D parameter as a random variable (particle-based variational framework); SDS is shown to be a special case of VSD. VSD works across CFG weights, improves diversity and quality, and yields 512x512 high-fidelity NeRFs plus VSD-finetuned meshes. — [ProlificDreamer](https://arxiv.org/pdf/2305.16213)
- Magic3D is cited as a related text-to-3D comparison method (details not retrieved). — [ProlificDreamer](https://arxiv.org/pdf/2305.16213)
- MVDream (Aug 2023) fine-tunes a pretrained text-to-image diffusion model on a mixture of 3D renders and large-scale text-to-image data to produce multi-view consistent images; it is positioned as the first multi-view diffusion model from text, giving a better 2D prior for SDS. — [MVDream](https://arxiv.org/pdf/2308.16512)

### Inferences
- The speed/quality/diversity problems and the arrival of 3D datasets (Objaverse) plus feed-forward LRMs (below) explain the shift; Meshy/Tripo etc. do not publish a statement that they abandoned SDS (no source found).

### Gaps
- No fetched source for DreamFusion's exact runtime (UNVERIFIED background: roughly 1.5 h per prompt on TPUv4; Magic3D ~40 min coarse-to-fine two-stage NeRF then DMTet mesh; ProlificDreamer hours per asset). Janus problem and 64x64 rendering resolution of DreamFusion also not verified here.
- Industry rationale for leaving SDS is my inference, not a cited statement.

## 2. Multi-view diffusion and feed-forward Large Reconstruction Models

### Takeaway
Pipeline 2023-24: fine-tune an image diffusion model to produce consistent multi-view images (Zero123, MVDream, Zero123++, Wonder3D, SV3D), then reconstruct with a feed-forward transformer (LRM family) in seconds. Seconds-scale inference replaced hours-scale SDS.

### Cited Findings
- LRM (Adobe/ANU, Nov 2023, ICLR 2024 oral): first Large Reconstruction Model, predicts a NeRF from a single image in about 5 seconds; transformer with 500M learnable parameters; trained end-to-end on ~1M objects of multi-view data (Objaverse synthetic renders plus MVImgNet real captures). — [LRM](https://arxiv.org/pdf/2311.04400)
- TripoSR (Stability AI + Tripo/VAST, Mar 2024): builds on LRM architecture with improvements in data processing, model design and training; mesh from a single image in under 0.5 s. — [TripoSR](https://arxiv.org/pdf/2403.02151)
- InstantMesh (Apr 2024): "Efficient 3D Mesh Generation from a Single Image with Sparse-view Large Reconstruction Models"; i.e., multi-view diffusion (Zero123++-style) feeding a sparse-view LRM that outputs a mesh; it uses TripoSR/LRM-style baselines for comparison. — [InstantMesh](https://arxiv.org/pdf/2404.07191)
- Zero123++ is an image-conditioned diffusion model producing 3D-consistent multi-view images from one view, continuing Zero-1-to-3; Zero-1-to-3 was the foundation for SyncDreamer, One-2-3-45, Consistent123. — [Unite.AI summary](https://www.unite.ai/zero123-a-single-image-to-consistent-multi-view-diffusion-base-model/)
- MV-Adapter (Dec 2024) made multi-view generation pluggable into existing image models. — [MV-Adapter](https://arxiv.org/pdf/2412.03632)

### Inferences
- Multi-view diffusion + LRM is a two-stage "2D prior then reconstruct" design whose weakness is view inconsistency and baked-in lighting; this motivated 3D-native latent diffusion (section 3). This is consistent with the order of publication but is my interpretation.

### Gaps
- Not retrieved: Instant3D, CRM, LGM, Wonder3D, SV3D details/numbers (UNVERIFIED background: Instant3D ~20 s with 4-view diffusion + sparse-view LRM; LGM uses 4-view diffusion + U-Net predicting 3D Gaussians; CRM uses convolutional reconstruction on a tri-plane/flexicubes; Wonder3D produces normal+color maps; SV3D from Stability repurposes SVD video diffusion for orbital views).
- Meshy's own architecture descriptions: none found (see section 6).

## 3. 3D-native latent diffusion (VAE on SDF/occupancy/point clouds, flow matching, DiT)

### Takeaway
Current state of the art encodes meshes into a compact latent (VAE) and trains a DiT/rectified-flow model directly in that space, conditioned on image/text. Scale (1.5B to 10B params, millions of assets) and sparse/high-resolution representations are the main axes of progress.

### Cited Findings
- CLAY (SIGGRAPH 2024, arXiv 2406.13897; Deemos/ShanghaiTech): multi-resolution VAE plus a minimalistic latent DiT on neural fields; progressive training on a very large 3D dataset to a 1.5B-parameter native geometry generator; supports text/image and 3D-aware controls (multi-view images, voxels, bounding boxes, point clouds); PBR material via a multi-view material diffusion model giving 2K diffuse/roughness/metallic textures. — [CLAY](https://arxiv.org/html/2406.13897v1)
- TRELLIS (Microsoft; arXiv 2 Dec 2024; CVPR 2025 Highlight): Structured LATent (SLAT) = sparse 3D grid integrated with dense multiview features from a vision foundation model; two-stage pipeline (generate sparse structure, then latents for non-empty cells) using rectified-flow transformers adapted to sparsity; decodes to radiance fields, 3D Gaussians or meshes; models up to 2B parameters trained on 500K objects. — [TRELLIS paper](https://arxiv.org/pdf/2412.01506), [project page](https://microsoft.github.io/TRELLIS/)
- Hunyuan3D 2.0 (Tencent, arXiv 2501.12202, Jan 2025): two-stage (bare mesh then texture). Hunyuan3D-DiT is a flow-based diffusion model: dual-single-stream transformer on the latent space of Hunyuan3D-ShapeVAE with flow-matching objective; ShapeVAE uses mesh-surface importance sampling and variable token length. Hunyuan3D-Paint does texture synthesis. User study with 50 participants. — [Hunyuan3D 2.0](https://arxiv.org/html/2501.12202v3)
- Hunyuan3D 2.1 (open-sourced 14 Jun 2025): Shape-v2.1 3.3B params, Paint-v2.1 2B params; PBR texture model; VRAM 10 GB shape, 21 GB texture, 29 GB combined; VAE + DiT + flow matching. — [Hunyuan3D-2.1 GitHub](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1)
- TripoSG (VAST-AI, arXiv 2502.06608, Feb 2025): rectified-flow transformer for image-to-shape, with a data-building pipeline, a VAE and a flow model; 1.5B base model trained on 2M data with 512 latent tokens; scaled to ~4B via MoE (FFNs of last six decoder layers replaced by top-K gated experts) with 4096 latent tokens, near-constant latency. — [TripoSG](https://arxiv.org/pdf/2502.06608), [GitHub](https://github.com/VAST-AI-Research/TripoSG)
- Direct3D-S2 (arXiv 2505.17412, NeurIPS 2025): sparse-volume SDF generation; end-to-end sparse SDF VAE with symmetric encoder-decoder; Spatial Sparse Attention gives 3.9x forward and 9.6x backward speedup; trains at 1024^3 with 8 GPUs (vs at least 32 GPUs for 256^3 volumetric). — [Direct3D-S2](https://arxiv.org/pdf/2505.17412)
- Rodin Gen-2 (Deemos, announced ~Oct 2025): 10B parameters on "BANG" architecture with recursive part-based generation; quad meshes at 4k/8k/18k/50k quads, triangle option to 500k; 2K PBR textures; ~60 s; up to 5 input images; "4x geometry improvement" over Gen-1 (vendor claims). — [Runware listing](https://runware.ai/models/hyper3d-rodin-gen-2), [Before & Afters](https://beforesandafters.com/2025/10/02/deemos-launches-rodin-gen-2-a-groundbreaking-generative-ai-for-intuitive-3d-creation/)

### Inferences
- The field converged on: VAE (point-cloud/surface-sample encoder, SDF/occupancy decoder) + DiT with rectified flow; differences are sparse-voxel (TRELLIS, Direct3D-S2) vs vecset/token latents (Hunyuan, TripoSG, CLAY). Rodin's lineage (CLAY to BANG to Gen-2) is a single-team progression.

### Gaps
- Not retrieved: 3DShape2VecSet, Michelangelo, Step1X-3D, TripoSF, Direct3D (v1), TRELLIS.2, Hunyuan3D 2.5/3.0 details (UNVERIFIED background: 3DShape2VecSet 2023 introduced vecset latent with cross-attention to point cloud; Step1X-3D from StepFun/LightIllusions 2025 uses geometry VAE-DiT plus multi-view texture model). Rodin BANG paper details (part-based "bounded" generation) unverified beyond vendor listing. Rodin Gen-2 specs come from reseller/trade press, not an academic paper.

## 4. Gaussian-splatting-based generation

### Takeaway
Gaussians appear mainly as an output/decoder format (TRELLIS decodes to 3D Gaussians) rather than a primary production target; production workflows still end in meshes.

### Cited Findings
- TRELLIS SLAT can be decoded into Radiance Fields, 3D Gaussians, or meshes. — [TRELLIS](https://arxiv.org/pdf/2412.01506)

### Inferences
- Production tools (Meshy, Tripo, Rodin) deliver meshes/PBR textures per the sources above, implying Gaussians are an intermediate or research format.

### Gaps
- LGM, GaussianDreamer, DreamGaussian, GRM, Splatter Image details not retrieved (UNVERIFIED background: DreamGaussian ~2 min; LGM ~5 s).

## 5. Autoregressive mesh generation and artist-style meshes

### Takeaway
Autoregressive transformers over tokenized triangles yield clean, artist-like topology but were limited by sequence length (800 faces originally); newer tokenizers raised caps to ~1.6k-4k and beyond.

### Cited Findings
- PolyGen: autoregressive vertex model generates vertex coordinates, then a face model connects them. MeshGPT: sorts faces, compresses via VQ-VAE, then an autoregressive transformer predicts token sequence. — [MeshGPT summary](https://www.emergentmind.com/topics/meshgpt)
- MeshAnything uses 9 tokens per triangle face, limiting to 800 faces due to quadratic cost; MeshAnything V2 (adjacent mesh tokenization) raised the limit to 1,600 and EdgeRunner to 4,000; Meshtron uses hourglass architecture with sliding-window inference; BPT uses block-wise indexing and patch aggregation. — [TreeMeshGPT](https://arxiv.org/pdf/2503.11629), [MeshAnything V2](https://arxiv.org/pdf/2408.02555), [EdgeRunner](https://arxiv.org/pdf/2409.18114)

### Inferences
- Autoregressive meshers are typically used as a retopology stage after a dense-geometry generator (MeshAnything is framed as "artist-created mesh" from shape inputs); whether specific vendors do this is unconfirmed.

### Gaps
- MeshXL details, Meshtron numbers (UNVERIFIED background: up to 64K faces), and Tripo/Meshy low-poly pipelines not retrieved.

## 6. Meshy's model generations and pipeline (confirmed vs inferred)

### Takeaway
Meshy publishes product/press-level descriptions only. No architecture paper exists; everything about internals is inference.

### Cited Findings (confirmed, vendor press)
- Meshy 4 launched around July/Aug 2024 (improved geometry quality for text- and image-to-3D, retry features). — [Barchart press](https://www.barchart.com/story/news/28447544/meshy-announces-the-launch-of-nextgen-generative-ai-for-3d-meshy4), [CGWorld](https://cgworld.jp/flashnews/202408-Meshy4.html)
- Meshy 5 Preview announced 28 Jul 2025 (higher-fidelity image-to-3D, better multi-view input, sharper geometry); full Meshy 5 announced 26 Aug 2025. — [Chainwire](https://chainwire.org/2025/07/28/meshy-launches-meshy-5-preview-with-enhanced-ai-3d-generation-tools-and-animation-library/), [Newsfile](https://www.newsfilecorp.com/release/263875)
- Meshy 6 Preview launched 16 Oct 2025; production release 18 Jan 2026 (per a secondary wiki); features cleaner topology, Low Poly Mode, multi-color 3D printing output, text/image/multi-view-to-3D; public material is workflow-level, no architecture paper. — [Newsfile Meshy 6 Preview](https://www.newsfilecorp.com/release/270549), [aiwiki.ai](https://www.aiwiki.ai/wiki/meshy_6)
- Meshy claims 3M+ users and 30M+ assets generated. — [Chainwire/press](https://www.acnnewswire.com/press-release/english/101451/introducing-the-meshy-5-preview:-smarter-ai,-cleaner-models,-bigger-animation-potential)

### Inferences (not confirmed)
- Given Meshy 5/6 emphasis on multi-view input and "sculpting-level" geometry, the likely stack is a 3D-native latent diffusion/flow geometry model plus a multi-view-conditioned PBR texturing stage, with optional remeshing/low-poly step; this mirrors Hunyuan3D 2.x/TripoSG/Rodin and cannot be confirmed.

### Gaps
- Meshy-3 and earlier details; Meshy 6 beyond Jan 2026 (current date is Oct 2026); docs.meshy.ai changelog blocked; no engineering interviews found. Tripo 2.5/3.0 and Hyper3D beyond Gen-2 not found. Meshy 4 exact date uncertain (July vs Aug 2024).
