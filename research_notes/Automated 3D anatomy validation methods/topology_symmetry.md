# Automated topology, edge flow and symmetry checks for animation-ready character meshes

Access note: WebFetch was blocked by the egress proxy for docs.blender.org, vrchat.github.io, wiki.vrchat.com, trimesh.org, sandia.gov/cubit, novedge.com and gnomonworkshop.com. Only WebSearch result summaries (plus the github.com/sandialabs/verdict page) were readable. Every "Cited" item below comes from those summaries. Algorithms and thresholds marked "Inferences" are my own engineering proposals and are NOT sourced. Exact VRChat rank tables, Blender API signatures and trimesh function names were NOT verified (see Gaps).

## 1. Professional topology rules and how to compute them

### Takeaway
Professional guidance is qualitative with few hard numbers: loops encircle every joint and expression area, at least 3 face loops per joint, quads in deforming areas, poles kept away from high-deformation zones. Each rule can be made computable, but the numeric thresholds below are proposals.

### Cited Findings
- Edge loops should encircle every joint (elbow, knee, knuckle) and every major expression area (eyes, mouth); topology is denser where deformation is higher, e.g. shoulders and knees. — [search summary of Blender manual/blenderartists/polycount results](https://docs.blender.org/manual/ru/2.79/_sources/modeling/meshes/structure.rst.txt)
- "At least 3 face loops of polys around each joint" for clean deformation (community guidance). — [CG Cookie thread](https://cgcookie.com/community/9812-searching-for-topology-and-modeling-advice) (via search summary; exact attribution to this page not confirmed)
- Elbow/knee: two to three tight rings on the crease side, one to two broader rings on the stretch side, to avoid candy-wrapper artifacts. Space loops closer on the pinching side and wider on the stretching side. — [NovEdge ZBrush tip](https://novedge.com/blogs/design-news/zbrush-tip-deformation-ready-joint-topology-with-zremesher) (search summary only)
- Shoulder: circular loops around deltoid insertions, longitudinal flow into torso and arm, extra loop stack for clavicle movement. — [NovEdge anatomy-driven retopology](https://novedge.com/blogs/design-news/zbrush-tip-anatomy-driven-retopology-for-predictable-deformation) (search summary only)
- Keep everything quads; poles (3-, 4-, 5-edge vertices) are tools to redirect flow but must be kept away from high-deformation areas. — [search summary of Shoot First / polycount / Blender manual](https://www.shootfirst.art/toplogy)
- A Gnomon workshop "Topology for animated characters" exists; its contents could not be read. — [Gnomon](https://www.thegnomonworkshop.com/workshops/topology-for-animated-characters)

### Inferences
- Joint loop count check: for each joint bone j with head h, axis a (unit, along the bone), build slab planes p(t) = h + t*a. For skin vertices within the bone's influence (weight>0.3 for DEF-bone j or its child), cluster vertex projections s = (v-h).a. Count distinct "rings": edges whose endpoints straddle level s (sign change of s - s0) form a cross-section; sweeping s0 over the joint region (+-0.5 * limb diameter), count the number of distinct vertex-level clusters (1D clustering with tolerance ~ 0.15 * median edge length) that form closed or limb-wrapping loops. Pass if >= 3 rings in the region (proposed; matches the "3 loops" rule) with >= 2 on the crease side.
- Crease/stretch side check: compute ring spacing on the inner vs outer side of the bend direction (bend axis = hinge axis from rig). Expect inner spacing <= outer spacing. Proposed warning only.
- Pole check: valence = len(v.link_edges). Flag valence 3 and >=5 within deformation regions (vertex weight to joint bone > ~0.5 or within 1 limb-diameter of a joint); allowed on low-motion areas (top of head, palms, chest centre). Valence-3 and 5 poles are legal but a "pole budget" per region can be reported.
- Tri/n-gon check: count faces with len != 4. Fail if any n-gon (>4) in deforming zones; warn for triangles in joint regions (bone weight-split > threshold or within joint slab), tolerate in low-motion zones (back of head, under hair, hands' palm tips).
- Eye/mouth rings: from landmark bone/socket (eye centre, mouth centre) cast concentric slices: group vertices by radial distance from landmark projected on the face plane; count closed edge loops around the landmark (loop is closed if the edge-cycle encircles the landmark: winding number of the polyline about the landmark = +-1). Proposed targets: >= 2 closed rings per eye, >= 2 around mouth (inference; no sourced number).

### Gaps
- No sourced numeric loop-count tables for shoulder/hip/wrist (only elbow/knee "2-3 / 1-2 rings" and "at least 3"). Gnomon content unreadable.
- Anime/stylised low-poly norms (e.g. 1-2 loops per joint) not found.

## 2. Algorithms for loops, rings, poles, quad metrics and degenerate checks

### Takeaway
Everything needed is simple graph work on faces/edges and can be written with numpy on any OBJ/glTF; bmesh just provides adjacency conveniences. Only quad metric thresholds from Verdict/Cubit were verifiable.

### Cited Findings
- Verdict (Sandia) is a library computing quality functions for 2D and 3D regions; it includes V_QuadMetric.cpp and a user manual (VerdictUserManual2007, SAND2007-2853p). — [GitHub sandialabs/verdict](https://github.com/sandialabs/verdict)
- Quad acceptable ranges in Cubit docs (Verdict-based): aspect ratio 1-4, skew 0-0.5, scaled Jacobian 0.5-1. Aspect ratio is max edge-length ratio at quad centre; skew is max |cos A| of the angle between edges at the quad centre; scaled Jacobian is min Jacobian divided by lengths of the two edge vectors. — [Cubit quad metrics (search result)](https://www.sandia.gov/files/cubit/15.3/help_manual/WebHelp/mesh_generation/mesh_quality_assessment/quadrilateral_metrics.htm)
- Verdict reference manual PDF and a known VTK issue on errors in the Verdict manual exist (treat formulas with care). — [VerdictManual revA](https://visit-sphinx-github-user-manual.readthedocs.io/en/stable/_downloads/9d944264b44b411aeb4a867a1c9b1ed5/VerdictManual-revA.pdf); [VTK issue 19644](https://gitlab.kitware.com/vtk/vtk/-/work_items/19644)

### Inferences (implementable, unsourced)
- Valence: build edge set from faces; valence[v] = number of unique edges. numpy: np.unique on sorted edge pairs, np.bincount of endpoints.
- Quad ratio = n_quads / n_faces; glTF stores triangles only, so quad structure must be recovered by pairing triangles (shared edge, coplanar within ~1 deg, forming a convex quad) or by reading the OBJ `f` lines. Report "quad-recoverable ratio" for glTF. Needs bmesh/OBJ for the true value.
- Edge loop walk (bmesh-free): at a valence-4 vertex, the continuation of edge e is the opposite edge in the vertex's cyclic order; stop at poles/boundary. Edge ring: for edge e in a quad, the opposite edge in that quad; walk across adjacent quads. Face loop = sequence of quads via ring. In bmesh, BMLoop.link_loop_radial_next and link_loop_next.link_loop_next give these steps; or call bpy.ops.mesh.loop_multi_select(ring=...) (operator, needs edit mode).
- Per-face quality: aspect = max edge / min edge; skew = max |cos| of the four corner angles (or at centre, per Verdict); scaled Jacobian = min over corners of sin(angle); min/max angle. Warn thresholds: aspect > 4, skew > 0.5, scaled Jacobian < 0.5 (taken from Cubit ranges); stricter in joints (aspect < 3 proposed). Warp: angle between triangle normals of the two diagonal splits.
- Edge-length uniformity: coefficient of variation of edge lengths per region (proposed < 0.5 outside detail zones); check ratio of neighbour-edge lengths along a loop (<2.5 proposed).
- Degenerate/non-manifold beyond the 3D-Print Toolbox: zero-area faces (area < 1e-10 * bbox^2), duplicate vertices (KD-tree/rounded hashing, tol 1e-5), duplicate faces (sorted vertex tuple), edges with >2 faces, vertices with disconnected fans ("bow-tie"), flipped normals (inconsistent winding on shared edges), loose verts/edges, isolated islands, UV overlap/flipped UV, faces with identical normals folded (dihedral > 170 deg), unweighted vertices, weights not normalised, >4 influences per vertex (glTF JOINTS_0 limit).

### Gaps
- Could not open Blender bmesh API docs, 3D-Print Toolbox docs or Mesh Check docs to confirm exact checks list.
- Verdict exact formulae and "acceptable vs normal" tables beyond the three metrics above were not read.

## 3. Symmetry detection and scoring

### Takeaway
Symmetry = reflect vertices through a plane and measure nearest-neighbour distance (Chamfer/Hausdorff); plane can be found by PCA/bbox initial guess + ICP refinement. Blender offers topology-based mirror and symmetrize, useful for index-level checks.

### Cited Findings
- Mirror symmetry can be recast as registration: reflect the point set, register with ICP, and derive the plane (via eigenvector of eigenvalue -1 of a combined transform, or fit a plane to midpoints of correspondences); reported 86% accuracy in tests using ICP. — [Finding Mirror Symmetry via Registration](https://ar5iv.arxiv.org/html/1611.05971)
- Blender Topology Mirror pairs vertices using mesh connectivity as well as position, so mirrored vertices need not be geometrically symmetric; works more reliably on detailed meshes, often fails on simple primitives. — [Blender wiki (Topology Mirror)](https://wiki.blender.org/index.php/User:Terrywallwork/WorkingOn/Topology_Mirror)
- Blender Symmetrize copies one side onto the other in one direction, splitting edges/faces that cross the plane; direction property selects axis and positive-negative. — [bf-codereview Symmetrize patch](https://lists.blender.org/pipermail/bf-codereview/2012-October/000702.html)

### Inferences (unsourced)
- Plane detection: for characters in this project the plane is expected at x=0 (VRM faces +Z, Y-up; glTF is Y-up, +Z front). First test x=0; otherwise candidate = plane normal along PCA axis with the smallest asymmetry, then refine with ICP on the reflected cloud.
- Score: reflect vertices (x -> -x), KD-tree (scipy cKDTree or numpy brute force for <20k verts) nearest distance d_i, report mean (Chamfer), 95th percentile and max (Hausdorff), normalised by bbox height. Proposed pass: p95 < 0.5% of height, max < 2% for body/head; per-region with exclusion of hair/accessory vertices (name or material tagged), or compute only on the face/body meshes.
- Partial symmetry: report fraction of vertices with d_i < tol (symmetric coverage); expected > 90% for body, lower for stylised hair (side parts, asymmetric ahoge) - gate on body+face only.
- Index symmetry (for shape keys/weights): for each left-side vertex find the mirror partner; require 1:1 matching; verify weights on DEF-x.L equal DEF-x.R of the partner, shape key deltas mirror, and bone naming .L/.R pairs. Topology-based pairing: BFS from the centre-line vertex set matching valence sequences (Blender's topology mirror does a similar thing).
- Libraries (trimesh, libigl, open3d, pymeshlab) - I could not confirm dedicated bilateral symmetry detectors; trimesh has `trimesh.symmetry` (radial/planar detection) per my recollection (unverified); the ICP route is implementable with trimesh.registration.icp or open3d.

### Gaps
- trimesh.symmetry docs, libigl/open3d/pymeshlab symmetry functions not verifiable (docs blocked).
- No source for tolerances; values above are proposals.

## 4. Mesh quality metrics (FEM/graphics) thresholds

### Takeaway
Verdict/Cubit quad ranges give usable numeric thresholds for animation meshes (see section 2): aspect 1-4, skew 0-0.5, scaled Jacobian 0.5-1.

### Cited Findings
- See section 2 (Cubit/Verdict). — [Cubit quad metrics](https://www.sandia.gov/files/cubit/15.3/help_manual/WebHelp/mesh_generation/mesh_quality_assessment/quadrilateral_metrics.htm)

### Inferences
- Minimum angle thresholds for triangles (e.g. > 20 degrees) are conventional in FEM but I did not find a source here; use as proposal. FEM thresholds target solver stability, not skinning; treat as heuristics.

### Gaps
- Jacobian ratio, Verdict triangle metric ranges not retrieved.

## 5. What runs on plain OBJ/glTF with numpy vs needs bmesh

### Takeaway
(Inference) Geometry, valence, degenerate, symmetry, per-face quality, weight checks and joint slicing all run on triangle/face index arrays with numpy (+scipy cKDTree optional). True quad/n-gon statistics require OBJ or Blender because glTF is triangulated.

### Cited Findings
- (none specific found; glTF triangulation is from my knowledge of the spec, not fetched in this session)

### Inferences
- numpy-only: valence, non-manifold edges, duplicates, zero-area, face quality on triangles, mirror Chamfer (brute force chunks), joint-slab loop counting using edge crossings, weight sums, influence count.
- Needs bmesh/OBJ: true quad ratio, n-gon locations, loop/ring walking in authored quad flow, topology-mirror pairing, shape-key checks authored in Blender (although glTF morph targets work in numpy).
- This repo: Blender scripts exist under tests/blender and pack checker check_pack.py (per CLAUDE.md); new checks fit as numpy functions in the validator plus a bmesh script for quad stats, covered by tests/blender.

### Gaps
- None sourced.

## 6. Existing validators to learn from

### Takeaway
VRChat ranks by counts (triangles, materials, bones), VRM export validates rig/bone conditions, not edge flow. I found no mainstream validator that checks edge-loop topology automatically.

### Cited Findings
- VRChat Avatar Performance Ranking uses ranks Excellent/Good/Medium/Poor/Very Poor based on avatar resource usage; actual threshold table could not be read. Community suggestions of triangle limits (32k, 70k, 110k, 150k) are user proposals, not official. — [VRChat wiki](https://wiki.vrchat.com/wiki/Avatar_Performance_Ranking); [VRChat feedback](https://feedback.vrchat.com/avatar-30/p/incremental-triangle-limit-for-performance-rankings)
- UniVRM export dialog checks: root rotation/scale default, Animator with humanoid avatar, facing +Z, active meshes; warnings for jaw bone, same-name bones, vertex colours, unknown shaders. Required humanoid bones: hips, spine, chest, neck, head, upper/lower arms, hands, upper/lower legs, feet (L/R). — [UniVRM export dialog](https://vrm.dev/en/univrm/export/univrm_export/); [VRM setup](https://vrm.dev/en/vrm/how_to_make_vrm/setup_vrm/)
- VRM expects a standard rest pose, T-pose safest. — [vrm.dev convert from humanoid](https://vrm.dev/en/vrm/how_to_make_vrm/convert_from_humanoid_model/)

### Gaps
- Not found/readable: Avatar Doctor, Unity/Unreal skeletal-mesh import checks, Rigify rig checks, Sketchfab inspector warnings, Blender Mesh Check and 3D-Print Toolbox check lists.
