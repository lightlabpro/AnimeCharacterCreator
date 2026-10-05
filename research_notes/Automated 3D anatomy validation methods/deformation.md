# Automated skinning and deformation quality testing under pose

Research note. Source access was limited: docs.blender.org, github.khronos.org, projects.blender.org, scitepress.org and media.disneyanimation.com were blocked by the proxy, and arxiv.org PDFs were not fetched. Only claims with a URL come from search results. Everything else is marked "inferred" and is my own engineering judgement, not a published standard. All numeric thresholds in this note are starting values to be calibrated, not established values.

## 1. Which skinning failure modes matter, and how is each detected numerically?

### Takeaway
Published sources I could reach confirm the classic LBS failure (candy-wrapper collapse) and the DQS failures (bulge, flip), and that Blender has built-in tools for weight normalization, cleaning and limiting. I found no published, standard, numeric "skinning QA" metric suite, so the detector set below is mostly inferred and has to be calibrated on your own good and bad rigs.

### Cited Findings
- The candy-wrapper artifact is the skin-collapse effect that results from the linear nature of linear blend skinning (LBS). Dual quaternion skinning (DQS) avoids it and preserves volume better. — [Search summary: SeeLes DCC skinning guide, Autodesk Maya docs, Disney paper listing](https://www.seeles.ai/features/tools/dcc-skinning-deformation-methods-guide); see also [Disney: Enhanced Dual Quaternion Skinning for Production Use](https://disneyanimation.com/publications/enhanced-dual-quaternion-skinning-for-production-use)
- Disney states DQS is not a drop-in replacement for LBS and must be extended for production needs. — [Disney Animation](https://disneyanimation.com/publications/enhanced-dual-quaternion-skinning-for-production-use)
- DQS does not lose volume, but it introduces a bulging artifact at bent joints and a flipping limitation (skin always takes the shorter way round). — [Kavan et al., Skinning with Dual Quaternions (search summary)](https://users.cs.utah.edu/~ladislav/dq/); paper PDF: [Kavan et al. TOG08](https://dcgi.fel.cvut.cz/home/zara/papers/KavanEtAll-TOG08.pdf)
- glTF stores skinning per vertex as JOINTS_0 (joint indices, usually a 4-vector, so at most 4 influences per attribute set) and WEIGHTS_0 (influence strengths). Additional sets (JOINTS_1, ...) exist for more influences. — [Khronos glTF tutorial, Skins (search summary)](https://github.khronos.org/glTF-Tutorials/gltfTutorial/gltfTutorial_020_Skins.html). The search did not confirm the spec text that weights must sum to 1; treat that as a Gap.
- Blender's Normalize All makes each vertex's weights across all vertex groups sum to 1 (locked groups are untouched). Clean removes weights below a limit. These are the repair counterparts of "non-normalized" and "tiny weight" checks. — [Blender manual, Weight Paint Editing](https://docs.blender.org/manual/en/4.3/sculpt_paint/weight_paint/editing.html)
- Desirable skinning-weight properties in the literature: smoothness, non-negativity, no spurious local optima away from handles. Weight bleeding is a recognised issue, addressed in some methods with visibility-aware weights. — [Search results incl. Solomon quasi-harmonic and SkinCells](https://arxiv.org/pdf/2506.14714)
- RigNet evaluates predicted skinning against animator-made rigs and reports it beats BBW, NeuroSkinning and GeoVoxel in Table 2 (specific measures not retrieved). — [RigNet](https://arxiv.org/abs/2005.00559)

### Inferences
Detector table (all inferred unless noted). "Pose" = rest vs a stress pose; `V`=vertices, `E`=edges.

| Failure | Needs pose? | Metric | Starting threshold (to calibrate) |
|---|---|---|---|
| Unweighted vertex | no | `sum(w)==0` or no group | 0 allowed |
| Non-normalized | no | `abs(sum(w)-1)` | max error < 1e-3 (glTF export after normalise) |
| Too many influences | no | count of w > 1e-4 | max <= 4 (glTF JOINTS_0 limit, cited above) for the app; flag >4 as error |
| Tiny noisy weights | no | fraction of influences with 0 < w < 0.01 | warn if > 5% of verts |
| Weight island (disconnected patch with a bone) | no | for each bone, connected components of the vertex set with w>0.1 over mesh edges; count > 1 | error if a component has > 3 verts and is not adjacent to the main one (inferred; symmetric-twin meshes like eyes/accessories are separate islands by design, so run per mesh island) |
| Weight bleed between limbs/fingers | no | for each bone, geodesic or Euclidean distance from verts with w>0.1 to the bone segment, normalised by bone length; and for hand: finger-bone weight on verts nearer another finger | warn if a finger bone has w>0.1 on verts whose nearest finger bone is another finger by >2x distance |
| Non-smooth weights | no | Laplacian energy per vertex: `L_i = || w_i - mean(w_neighbours) ||_1`, using cotan or uniform Laplacian | flag verts above (median + 6*MAD); also report 99th percentile |
| Candy-wrapper collapse | yes: twist the forearm/upper-arm bone about its own axis (e.g. 90, 180 deg) | cross-section area or ring radius at mid-segment divided by rest | pass if min radius ratio > 0.6 at 90 deg, > 0.35 at 180 deg (guess) |
| Volume loss at elbow/knee/shoulder | yes: bend pose | local volume ratio of a region (below) | pass 0.75 to 1.15 at 90 deg bend; flag < 0.6 |
| Stretching/spiking | yes | per-edge stretch ratio `r_e = len_posed / len_rest`; per-vertex displacement outlier vs. neighbours | for non-rigid cloth-free body: 99.9th percentile of r_e in 0.5..2.0; any edge > 3 is a spike |
| Normal flips / crumpling | yes | fraction of faces where `dot(n_posed, R_bone * n_rest) < 0` (using the dominant bone's rotation), and fraction of dihedral angle changes > 120 deg between neighbours | flip fraction < 0.5% |
| Self-intersection | yes | BVH overlap count (section 4), minus rest-pose baseline | new overlapping pairs vs rest <= small count; compare per region |
| Asymmetry | yes | L/R mirrored pose comparison (section 5) | see section 5 |

## 2. Published and practical metrics (volume, stretch, Jacobian, flips, self-intersection, weight statistics)

### Takeaway
Volume, edge-stretch and deformation-gradient measures are standard geometry quantities; I did not find a published paper that sets pass thresholds for them in a skinning-QA context. The formulas below are standard and well defined, the thresholds are inferred.

### Cited Findings
- LBS: `v' = sum_j w_j * M_j * v`, where `M_j = pose_j * inverse_bind_j`; glTF applies this with weights from WEIGHTS_0 and joint matrices. — [glTF tutorial, Skins](https://github.khronos.org/glTF-Tutorials/gltfTutorial/gltfTutorial_020_Skins.html) (formula form from search summary of the vertex shader)
- DQS blends unit dual quaternions instead of matrices, avoids volume loss, but bulges and "flips". — [Kavan et al.](https://users.cs.utah.edu/~ladislav/dq/)
- Skinning weight smoothness is commonly formalised as Laplacian-type energy (biharmonic/bounded biharmonic weights). — [Search results, quasi-harmonic skinning, Solomon](https://people.csail.mit.edu/jsolomon/assets/quasiharmonic.pdf)
- Blender's own repair tools: Normalize All, Clean, and Limit Total (cap influences per vertex). — [Blender manual](https://docs.blender.org/manual/en/4.3/sculpt_paint/weight_paint/editing.html)

### Inferences
Formulas (standard geometry; use numpy):
- Closed-mesh volume: `V = (1/6) * sum_f dot(a, cross(b, c))` over triangles with vertices a,b,c. Needs a watertight mesh; for open or multi-part meshes use a regional volume instead.
- Local volume ratio per joint region (works on open meshes): choose region = vertices with weight on bone B and its parent above 0.5. Take the region's tetrahedral volume to the region's centroid, or use per-triangle signed volume against a fixed point at the joint position: `V_region = sum_f dot(a-p, cross(b-p, c-p))/6` with `p` = joint head in each pose. Ratio = posed / rest.
- Cross-section ring radius: pick the vertex ring near the joint (slice at plane through the bone with normal = bone axis), measure mean distance to the bone axis; ratio posed/rest is a cheaper and more targeted candy-wrapper detector than volume.
- Edge stretch: `r_e = ||p_i - p_j|| / ||rest_i - rest_j||`. Report p0.1, p99.9, max by region. Skin around a bent elbow legitimately compresses on the inside and stretches on the outside; accept r in about 0.5..1.8 for 90 deg bends (guess).
- Deformation gradient / Jacobian: per triangle, build the 3x3 (triangle plus normal as third axis) rest frame `Dm` and posed frame `Ds`, `F = Ds * inverse(Dm)`. Take SVD, singular values s1 >= s2 >= s3. Area stretch is about s1*s2; `det(F) <= 0` means inverted/flipped. Anisotropy `s1/s2`. Flag `det(F) < 0` (flip) and `s2 < 0.3` or `s1 > 3`.
- Normal flip rate: see table; use the posed vs rest normal after removing the rigid part (rotate rest normal by the dominant bone).
- Weight statistics: counts above, Laplacian energy, `entropy_i = -sum w log w` (influences blending, high entropy beyond 3-4 bones is suspect).
- Bone-heat artifacts (inferred; no source retrieved): automatic weights in Blender ("With Automatic Weights", based on bone heat) often fail on non-manifold or intersecting meshes, giving zero-weight vertices or weights from the wrong bone. They show up as unweighted vertices and as weight bleed between close limbs (finger/finger, arm/torso), so the same checks catch them.

### Gaps
- No published QA thresholds for these metrics found; no source for a Rigify, Auto-Rig Pro or Mixamo weight-report feature was retrieved. I did not verify whether those tools report weight problems.
- RigNet's exact skinning measures (Table 2) were not read; the PDF was not fetched.

## 3. Range-of-motion test protocols and joint angles

### Takeaway
No studio ROM pass-criteria document was found. Clinical AAOS ranges give defensible maximum angles; a stress library can use those for "extreme but plausible" and about 1.1-1.2x for "over the limit" stress.

### Cited Findings
- AAOS normal values (search summary): shoulder flexion 180 deg, elbow flexion 150 deg, wrist flexion 80 deg, hip flexion 120 deg, knee flexion 135 deg; neck rotation 60 deg was reported by the summary, which disagrees with the 80 deg I had asked about. — [Enlyte, normal range of motion](https://www.enlyte.com/insights/article/adjuster/understanding-normal-range-motion-joint-functionality); [AAOS flashcards](https://brainscape.com/flashcards/aaos-normal-values-8291725/packs/13631830). These are secondary sources, so treat the neck figure as uncertain (other clinical references list cervical rotation as about 80 deg each side; not verified here).
- Rig joint limits are typically defined per joint as rotation ranges (e.g. -30 to 30 deg on an axis in the examples found). — [Roblox HumanoidRigDescription](https://create.roblox.com/docs/en-us/reference/engine/classes/HumanoidRigDescription.md); [SideFX KineFX forum thread](https://www.sidefx.com/forum/topic/103450/?page=1)

### Inferences
Suggested stress pose library (degrees, inferred from AAOS values plus common animation practice; verify per rig axis conventions):

| Joint | Poses to test |
|---|---|
| Shoulder | abduct 90 and 150; flex 90 and 170; extend back 45; internal rotate 70 with arm at side; across chest (horizontal adduction 120) |
| Upper arm twist | 0, +/-90, +/-150 about bone axis |
| Elbow | 0, 90, 135, 150 flexion; with forearm pronation +/-80 |
| Forearm/wrist | twist +/-90; wrist flex 70, extend 70, radial 20, ulnar 30 |
| Hip | flex 90 and 120; abduct 45; extend 20; rotate +/-40 |
| Knee | flex 90, 135 (squat), 150 (kneeling) |
| Neck | rotate +/-70; flex 50, extend 60; tilt +/-40 |
| Spine | bend 30 each of forward, back, side; twist 30 total |
| Fingers | curl each finger joint 90 (MCP 90, PIP 100, DIP 70) |

Protocol (inferred): for each pose, apply to one joint chain only (isolates failures), evaluate, compute region metrics for the regions touching that joint, record stats at 50%, 100% and 120% of the pose, plus a turntable of 8 views for the optional visual review. A studio-style visual gate is manual; automate the numeric part only.

### Gaps
- Studio documents (e.g. Rigify, Auto-Rig Pro, game studio deformation test pages) with explicit pass criteria were not found.
- Anime-style characters often exaggerate; thresholds may need to be looser for stylized proportions.

## 4. Implementation in Blender headless and on glTF

### Takeaway
Blender: pose bones, take the evaluated mesh via the depsgraph, use `mathutils.bvhtree` for self-overlap. glTF: read the accessors and do LBS with numpy. Both are fast enough for tens of thousands of vertices.

### Cited Findings
- `mathutils.BVHTree` supports `overlap()`; the 2015 commit added self-intersection support using the same logic as `BKE_bmbvh_overlap`: skip triangle pairs sharing 2 or more vertices, otherwise run an epsilon triangle-triangle test. Overlap does not allocate ignored pairs and runs intersection tests multi-threaded. — [Blender commit 231ee60 (search summary)](https://projects.blender.org/archive/blender-archive/commit/231ee60ab5373bb2e5676fc4f5c6dea476fc1d42)
- glTF skin vertex shader: weighted sum of four joint matrices indexed by JOINTS_0. — [Khronos glTF tutorial](https://github.khronos.org/glTF-Tutorials/gltfTutorial/gltfTutorial_020_Skins.html)

### Inferences
Blender (bpy), sketch from my knowledge of the API, not verified against docs here:
```python
import bpy, bmesh, numpy as np
from mathutils import Euler, bvhtree

def posed_mesh(obj_mesh, arm_obj, pose):          # pose: {bone_name: (rx,ry,rz) rad}
    for pb in arm_obj.pose.bones: pb.rotation_mode='XYZ'; pb.rotation_euler=(0,0,0)
    for n,e in pose.items(): arm_obj.pose.bones[n].rotation_euler = Euler(e)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj_mesh.evaluated_get(dg)
    me = ev.to_mesh()                              # call ev.to_mesh_clear() after use
    co = np.empty(len(me.vertices)*3, np.float32); me.vertices.foreach_get('co', co)
    tris = ...  # me.calc_loop_triangles(); loop_triangles[i].vertices
    return me, co.reshape(-1,3)

def self_overlaps(co, tris):
    t = bvhtree.BVHTree.FromPolygons([tuple(v) for v in co], [tuple(t) for t in tris], epsilon=1e-6)
    pairs = t.overlap(t)                           # pairs include (i,j) and (j,i); halve
    return pairs
```
- Subtract rest-pose baseline pairs (overlaps already present in rest pose: eyes in head, clothing layers, teeth). Then count new pairs per region (map face to the dominant vertex-group bone).
- Overlap pairs between adjacent triangles on the same surface that share one vertex can still report touching; filter by topological distance (skip pairs within 2 edges) to avoid false positives (inferred).
- Use `ev.to_mesh()` rather than applying modifiers or `bpy.ops` (applying pose via ops mutates the file). Poses via `pose_bone.rotation_*` and `view_layer.update()`.
- Complexity: skinning cost O(V*4) per pose in numpy, effectively milliseconds for 50k verts; BVH build O(F log F) and self overlap roughly O(F log F + k), usually well under a second per pose for 50k tris (inferred estimate; measure it). A 40-pose by 3-amplitude library is therefore a minutes-scale test.

glTF with numpy (inferred, standard):
```python
# read with pygltflib/trimesh or raw accessors: POSITION (V,3), JOINTS_0 (V,4) uint8/16, WEIGHTS_0 (V,4) float or normalized uint
# skin.inverseBindMatrices (J,4,4) column-major -> transpose when reshaping; skin.joints node indices
# joint_world[j] = world matrix of node skin.joints[j] under the test pose (compute from node TRS hierarchy)
M = joint_world @ ibm                      # (J,4,4)
Mv = np.einsum('vk,vkij->vij', W, M[J])    # (V,4,4) weighted matrix, LBS
posed = np.einsum('vij,vj->vi', Mv, np.c_[P, np.ones(len(P))])[:, :3]
```
Note: normalized unsigned integer weights must be divided by 255 or 65535. Include the mesh node's own transform handling (glTF ignores the mesh node transform for skinned meshes). Report any `abs(sum(W)-1) > 1e-3` and `W.sum==0` before skinning. DQS comparison: convert each M to a dual quaternion and blend with sign alignment, then compare volume ratios of LBS vs DQS; if LBS volume loss is large and DQS is fine, the weights are not the cause (the skinning method is); if both lose volume, weights/joint placement are at fault (inferred reasoning).

### Gaps
- Exact current bpy 5.x signatures were not checked (docs.blender.org was blocked); verify `BVHTree.FromPolygons`, `overlap`, and `to_mesh` behaviour in the installed bpy before committing.
- Performance numbers are estimates, not measurements.

## 5. Setting pass/fail thresholds without a reference model

### Takeaway
Use relative checks: pose vs rest, left vs right, region vs region, and slider extreme vs slider 0. Nothing in the retrieved sources describes this scheme; it is an inferred design.

### Cited Findings
- None retrieved specific to reference-free thresholds. The closest published idea is that smoothness of weights (Laplacian energy) is an intrinsic, reference-free quality property. — [Solomon quasi-harmonic skinning](https://people.csail.mit.edu/jsolomon/assets/quasiharmonic.pdf)

### Inferences
- Rest-relative: every deformation metric is a ratio posed/rest (volume, ring radius, edge stretch), so no reference mesh is needed. Baseline-subtract any rest-pose self-intersections.
- Left/right symmetry: apply the mirrored pose to the mirrored bone (flip X, swap `.L`/`.R`, mirror the Euler axes for the rig's convention). Mirror the posed vertices through a vertex-correspondence map (nearest vertex of the rest mesh mirrored in X, or a topology symmetry map). Asymmetry = `||posed_L_region - mirror(posed_R_region)||` divided by region size. Pass if p95 under 2% of region size and ratio metrics (volume, stretch) differ by less than 10% between sides (guess). A strong asymmetry that exists at rest (asymmetric character) must be subtracted using the rest-pose asymmetry.
- Region statistics: robust outlier rule, flag a region metric if it lies beyond median + 5*MAD of the same metric over all regions that had the same pose angle, and also beyond an absolute floor (so uniformly bad rigs still fail).
- Slider sweep: for a character with morph sliders (this app's body sliders), run the same pose set at slider 0 and at each slider extreme (and one random combination). Pass is relative: metrics at extreme must not degrade versus slider 0 by more than a margin (e.g. volume ratio drop under 0.1, new self-intersections under N, stretch p99.9 growth under 25%). Because the weights are on the base mesh, shape-key extremes mostly change geometry under constant weights, so this finds shape keys that break proportions (thin limbs intersecting, wide hips crossing legs). Run this on the exported glTF with morph targets applied before skinning (glTF applies morph targets first, then skin).
- Exit status mapping for this repo: failed metric = 12, metric not measurable (no armature, no weights, open mesh for volume) = 13 unknown (never a pass), usage = 2, consistent with the validator codes in CLAUDE.md.
- Calibration: run on one known-good and one deliberately-broken rig (e.g. weights smoothed to zero at the elbow, forearm bone weights swapped, a normalise-off export) and set each threshold between the two, as the project already does with `knowledge/validator-calibration.json`.

### Gaps
- No published reference-free threshold sets were found; all numbers need calibration on this project's real packs.
- Whether Rigify, Auto-Rig Pro or Mixamo ship a weight-problem report was not established.
