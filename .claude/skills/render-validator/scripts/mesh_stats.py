#!/usr/bin/env python3
"""Mesh health stats for the validator's geometry gates. A render cannot show these.

Why: a render says nothing about triangle budget, holes, non-manifold edges, loose parts or flipped
detail. Meshy's agent skills gate on face counts before paying for the next stage and treat "unknown"
as not-a-pass. This does the same for Blender characters.

  python3 mesh_stats.py model.obj [--out stats.json]        any machine, plain OBJ
  In Blender (Text Editor > Run Script): writes <blend folder>/mesh_stats.json for the objects in OBJECTS

Output keys (a missing key means "not measured", which the validator reports as UNKNOWN, never as a pass):
  verts, faces, tris, ngons, ngon_share, non_manifold_edges, boundary_edges, loose_verts,
  loose_parts, zero_area_faces, and, from Blender only, shape_keys, bones, sockets.
"""
import json, sys
import numpy as np

OBJECTS = ["CHR_Body"]          # Blender: mesh objects to measure together (hair, accessories are separate packs)
ARMATURE = "CHR_Armature"

def stats_from_arrays(verts, faces):
    """verts: Nx3 floats, faces: list of vertex-index lists. Returns the stats dict."""
    V = np.asarray(verts, dtype=float).reshape(-1, 3)
    n = len(V)
    tris = sum(max(len(f) - 2, 0) for f in faces)
    ngons = sum(1 for f in faces if len(f) > 4)
    edge_count = {}
    parent = list(range(n))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    used = set()
    zero = 0
    for f in faces:
        used.update(f)
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            edge_count[(min(a, b), max(a, b))] = edge_count.get((min(a, b), max(a, b)), 0) + 1
            parent[find(a)] = find(b)
        area = 0.0
        for i in range(1, len(f) - 1):
            area += np.linalg.norm(np.cross(V[f[i]] - V[f[0]], V[f[i + 1]] - V[f[0]])) / 2
        if area < 1e-12: zero += 1
    comps = {find(v) for v in used}
    non_manifold = sum(1 for c in edge_count.values() if c > 2)
    boundary = sum(1 for c in edge_count.values() if c == 1)
    return {
        "verts": int(n), "faces": len(faces), "tris": int(tris), "ngons": int(ngons),
        "ngon_share": round(ngons / max(len(faces), 1), 4),
        "non_manifold_edges": int(non_manifold), "boundary_edges": int(boundary),
        "loose_verts": int(n - len(used)), "loose_parts": len(comps), "zero_area_faces": int(zero),
    }

def read_obj(path):
    verts, faces = [], []
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            p = line.split()
            if not p: continue
            if p[0] == "v": verts.append([float(x) for x in p[1:4]])
            elif p[0] == "f":
                idx = []
                for tok in p[1:]:
                    i = int(tok.split("/")[0]); idx.append(i - 1 if i > 0 else len(verts) + i)
                faces.append(idx)
    return verts, faces

def run_in_blender():
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    verts, faces, shape_keys, off = [], [], [], 0
    for name in OBJECTS:
        o = bpy.data.objects.get(name)
        if not o: continue
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        verts += [tuple(ev.matrix_world @ v.co) for v in me.vertices]
        faces += [[off + i for i in p.vertices] for p in me.polygons]
        off += len(me.vertices); ev.to_mesh_clear()
        if o.data.shape_keys: shape_keys += [k.name for k in o.data.shape_keys.key_blocks]
    if not faces: raise SystemExit(f"None of {OBJECTS} found. Edit OBJECTS at the top of the script.")
    st = stats_from_arrays(verts, faces)
    st["shape_keys"] = sorted(set(shape_keys))
    arm = bpy.data.objects.get(ARMATURE)
    if arm: st["bones"] = sorted(b.name for b in arm.data.bones)
    st["sockets"] = sorted(o.name for o in bpy.data.objects if o.name.startswith("SOC-"))
    out = bpy.path.abspath("//mesh_stats.json")
    with open(out, "w") as f: json.dump(st, f, indent=2)
    print(json.dumps({k: v for k, v in st.items() if k not in ("shape_keys", "bones", "sockets")}, indent=1), "->", out)

def main():
    try:
        import bpy  # noqa: F401
        return run_in_blender()
    except ImportError:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args: sys.exit(__doc__)
    st = stats_from_arrays(*read_obj(args[0]))
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    if out:
        with open(out, "w") as f: json.dump(st, f, indent=2)
    print(json.dumps(st, indent=1))

if __name__ == "__main__":
    main()
