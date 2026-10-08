#!/usr/bin/env python3
"""Head topology of reference models (needs the bpy module or Blender's Python).

    python3 topology_dataset.py GLB_DIR MEASURED_JSON OUT_JSON [--only files.json]
    python3 topology_dataset.py --npz body_mesh.npz --top Z --chin Z OUT_JSON      (our own head, Blender -Y forward)

glTF stores triangles and splits vertices at UV seams, so every mesh is first welded (merge by distance, 1e-5 of
the body height) and its triangles re-joined into quads (bmesh join_triangles), the same thing a modeler does
when importing. Then, on the head region only (skull top down to 0.15 H under the chin, inside the head window):
  head_faces / head_quads_after_join / quad_ratio, poles (valence 3 or 5+, interior), face share of the front half,
  density_front_over_back (faces per area, face half vs skull half),
  eye openings: boundary loops in the upper-front face (their vertex counts = lid vertices),
  mouth opening: a boundary loop near the mouth line, if any,
  rings_around_eye: concentric topological rings around each eye opening that stay closed loops (up to 6).
Meshes are measured only.
"""
import json, os, sys
import numpy as np
import bpy, bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def bm_from(V, T, weld):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in V]
    bm.verts.ensure_lookup_table()
    for t in T:
        try:
            bm.faces.new((vs[t[0]], vs[t[1]], vs[t[2]]))
        except ValueError:
            pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=weld)
    tris = [f for f in bm.faces if len(f.verts) == 3]
    bmesh.ops.join_triangles(bm, faces=tris, angle_face_threshold=np.radians(40), angle_shape_threshold=np.radians(40))
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    return bm


def boundary_loops(edges):
    adj = {}
    for e in edges:
        a, b = e.verts
        adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    seen, loops = set(), []
    for s in adj:
        if s in seen: continue
        loop, cur, prev = [s], s, None
        seen.add(s)
        while True:
            nxt = [n for n in adj[cur] if n is not prev and n not in seen]
            if not nxt: break
            prev, cur = cur, nxt[0]; seen.add(cur); loop.append(cur)
        loops.append(loop)
    return loops


def rings(start_verts, allowed, maxk=6):
    """Topological rings outward from a hole: ring k = vertices first reached at step k. A ring counts while it is
    a single closed loop (each ring vertex has exactly 2 ring neighbours)."""
    cur = set(start_verts); seen = set(cur); out = []
    for k in range(maxk):
        nxt = set()
        for v in cur:
            for e in v.link_edges:
                o = e.other_vert(v)
                if o in allowed and o not in seen:
                    nxt.add(o)
        if not nxt: break
        closed = all(sum(1 for e in v.link_edges if e.other_vert(v) in nxt) == 2 for v in nxt)
        out.append({"n": len(nxt), "closed_loop": closed})
        seen |= nxt; cur = nxt
    good = 0
    for r in out:
        if r["closed_loop"]: good += 1
        else: break
    return good, out


def head_topology(bm, top, chin, xc, yc, H_body, fs):
    hh = top - chin
    r = 0.11 * H_body
    def inside(co):
        return (co.z > chin - 0.15 * hh) and abs(co.x - xc) < r and abs(co.y - yc) < r
    hv = set(v for v in bm.verts if inside(v.co))
    hf = [f for f in bm.faces if all(v in hv for v in f.verts)]
    sizes = np.array([len(f.verts) for f in hf])
    fwd = lambda co: fs * (co.y - yc)
    front = [f for f in hf if fwd(f.calc_center_median()) > 0]
    back = [f for f in hf if fwd(f.calc_center_median()) <= 0]
    area = lambda fl: sum(f.calc_area() for f in fl) or 1e-12
    dens = (len(front) / area(front)) / max(len(back) / area(back), 1e-12) if back else None
    interior = [v for v in hv if not v.is_boundary and all(f in set(hf) or True for f in v.link_faces)]
    poles = [v for v in interior if len(v.link_faces) and all(len(f.verts) == 4 for f in v.link_faces)
             and len(v.link_edges) in (3, 5, 6, 7, 8)]
    # openings in the face
    bed = [e for e in bm.edges if e.is_boundary and all(v in hv for v in e.verts)]
    loops = boundary_loops(bed)
    eyes, mouth = [], None
    for lp in loops:
        if len(lp) < 6: continue
        c = np.mean([v.co for v in lp], axis=0)
        u = (top - c[2]) / hh                                     # 0 skull top .. 1 chin
        if fwd(bpy_vec(c)) <= 0.02 * hh: continue                 # not on the face
        if 0.35 <= u <= 0.65 and abs(c[0] - xc) > 0.05 * hh:
            ext = np.ptp([v.co.x for v in lp]) / hh
            g, detail = rings(lp, hv)
            eyes.append({"verts": len(lp), "u": round(float(u), 3), "width_over_H": round(float(ext), 3), "closed_rings": g,
                         "ring_sizes": [d["n"] for d in detail]})
        elif 0.7 <= u <= 0.9 and abs(c[0] - xc) < 0.05 * hh:
            g, detail = rings(lp, hv)
            mouth = {"verts": len(lp), "u": round(float(u), 3), "closed_rings": g, "ring_sizes": [d["n"] for d in detail]}
    return {"head_faces": int(len(hf)), "quad_ratio": round(float((sizes == 4).mean()), 3) if len(sizes) else None,
            "tri_ratio": round(float((sizes == 3).mean()), 3) if len(sizes) else None,
            "head_verts": len(hv), "poles": len(poles), "pole_fraction": round(len(poles) / max(len(interior), 1), 4),
            "front_share": round(len(front) / max(len(hf), 1), 3), "density_front_over_back": round(float(dens), 3) if dens else None,
            "eye_openings": sorted(eyes, key=lambda e: e["u"])[:2], "mouth_opening": mouth}


def bpy_vec(c):
    from mathutils import Vector
    return Vector(c)


def main():
    a = sys.argv[1:]
    if a[0] == "--npz":
        d = np.load(a[1]); top = float(a[a.index("--top") + 1]); chin = float(a[a.index("--chin") + 1]); out = a[-1]
        V, T = d["V"].astype(float), d["T"]
        H = float(V[:, 2].max() - V[:, 2].min())
        if "PL" in d.files:            # real polygons: no re-joining needed
            bm = bmesh.new(); vs = [bm.verts.new(p) for p in V]; bm.verts.ensure_lookup_table()
            PL, PS = d["PL"], d["PS"]; o = 0
            for n in PS:
                try: bm.faces.new([vs[i] for i in PL[o:o + n]])
                except ValueError: pass
                o += n
            bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
        else:
            bm = bm_from(V, T, 1e-5 * H)
        if "--H" in a: H = float(a[a.index("--H") + 1])   # a head-only mesh: give the body height it belongs to
        res = {"ours": head_topology(bm, top, chin, 0.0, 0.01, H, -1.0)}
        json.dump(res, open(out, "w"), indent=1); print(json.dumps(res, indent=1)); return
    import measure_dataset as MD
    d, meas, out = a[0], a[1], a[2]
    M = json.load(open(meas))
    if isinstance(M, dict):
        M = [dict(v, file=k) for k, v in M.items()]
    only = set(json.load(open(a[a.index("--only") + 1]))) if "--only" in a else None
    res = {}
    for r in M:
        f = r["file"]
        if only and f not in only: continue
        if "lm" not in r or not r.get("lm"): continue
        posed = (r.get("skin_space") or "").startswith("node")
        V, T, J, _ = MD.load_parts(os.path.join(d, f), posed=posed)
        V2, Jc, _ = MD.orient(np.asarray(V, float), J if MD.rig_agrees(V, J) else {})
        H = float(V2[:, 2].max() - V2[:, 2].min())
        fs, _ = MD.forward_sign(V2, Jc, float(V2[:, 2].min()), H)
        lm = r["lm"]
        bm = bm_from(V2, T, 1e-5 * H)
        res[f] = head_topology(bm, lm["top"], lm["chin"], lm["xc"], lm["yc"], H, fs)
        bm.free()
        print(f[-20:-9], json.dumps(res[f]), flush=True)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
