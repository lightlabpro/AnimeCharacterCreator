#!/usr/bin/env python3
"""Measure a folder of reference GLBs (dataset sample) for head and body proportion bands.

    python3 measure_dataset.py GLB_DIR OUT_JSON [--meta top200.json]

Per model:
  body  : body_audit.measure (needs a skin with nameable joints; otherwise body metrics are absent, never guessed)
  head  : landmarks estimated from the geometry, then head_audit.profile_from_mesh (exact triangle slices)
          top  = highest vertex near the head axis (hair is excluded only when it is a separate mesh named hair)
          chin = lowest point of the front profile that still stands at least half way between the neck front and
                 the most forward point of the lower face
  Every estimate is recorded in `methods`; sanity flags mark profiles that should not enter a band.
Meshes are only measured; nothing from them is copied or saved.
"""
import json, math, os, re, sys, traceback
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "head-shape-audit", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "library-pack-check", "scripts"))
import body_audit as BA          # noqa: E402
import head_audit as HA          # noqa: E402


HAIR = re.compile(r"hair|bang|fringe|ponytail|ahoge|braid|kami|wig", re.I)
VROID_MAT = re.compile(r"^N\d{2}_\d{3}_|_(SKIN|HAIR|CLOTH|FACE|EYE)(_\d+)?_Instance$")


def load_parts(path, posed=False):
    """Like body_audit.load_gltf, but filters by material name as well as node name, so hair, eyes and clothes in their own
    material are removed even when node names are generic (Object_7). Returns V, T, joints, info."""
    from check_pack import read_gltf
    g, chunk = read_gltf(path); bufs = BA._buffers(g, chunk, os.path.dirname(os.path.abspath(path)))
    nodes = g.get("nodes", []); mats = g.get("materials", [])
    parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}
    cache = {}
    def world(i):
        if i not in cache: cache[i] = (world(parent[i]) if i in parent else np.eye(4)) @ BA._mat(nodes[i])
        return cache[i]
    zup = lambda P: np.stack([P[:, 0], -P[:, 2], P[:, 1]], 1)
    Vs, Ts, off = [], [], 0
    info = {"prims": 0, "kept_prims": 0, "hair_prims": 0, "materials": [m.get("name", "") for m in mats][:40]}
    for i, n in enumerate(nodes):
        if "mesh" not in n: continue
        for prim in g["meshes"][n["mesh"]]["primitives"]:
            if "POSITION" not in prim.get("attributes", {}): continue
            info["prims"] += 1
            mname = mats[prim["material"]].get("name", "") if "material" in prim and prim["material"] < len(mats) else ""
            label = n.get("name", "") + " " + g["meshes"][n["mesh"]].get("name", "") + " " + mname
            if HAIR.search(label): info["hair_prims"] += 1
            if BA.SKIP_MESH.search(label) or HAIR.search(label): continue
            P = BA._accessor(g, bufs, prim["attributes"]["POSITION"]).astype(float)
            if "skin" not in n: P = (world(i) @ np.c_[P, np.ones(len(P))].T).T[:, :3]
            elif posed and "JOINTS_0" in prim["attributes"] and "WEIGHTS_0" in prim["attributes"]:
                sk = g["skins"][n["skin"]]
                ibm = BA._accessor(g, bufs, sk["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1) if "inverseBindMatrices" in sk else np.tile(np.eye(4), (len(sk["joints"]), 1, 1))
                Mj = np.stack([world(j) for j in sk["joints"]]) @ ibm
                JI = BA._accessor(g, bufs, prim["attributes"]["JOINTS_0"]).astype(int)
                WW = BA._accessor(g, bufs, prim["attributes"]["WEIGHTS_0"]).astype(float)
                acc = g["accessors"][prim["attributes"]["WEIGHTS_0"]]
                if acc.get("normalized") and acc["componentType"] == 5121: WW /= 255.0
                elif acc.get("normalized") and acc["componentType"] == 5123: WW /= 65535.0
                WW /= np.maximum(WW.sum(1, keepdims=True), 1e-9)
                Ph = np.c_[P, np.ones(len(P))]
                P = sum(WW[:, k:k + 1] * np.einsum("nij,nj->ni", Mj[JI[:, k]], Ph)[:, :3] for k in range(4))
            idx = BA._accessor(g, bufs, prim["indices"]).reshape(-1) if "indices" in prim else np.arange(len(P))
            if prim.get("mode", 4) != 4: continue
            Vs.append(zup(P)); Ts.append(idx.reshape(-1, 3).astype(int) + off); off += len(P); info["kept_prims"] += 1
    if not Vs: raise ValueError("no body mesh left after filtering")
    joints = {}
    for sk in g.get("skins", []):
        ibm = BA._accessor(g, bufs, sk["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1) if "inverseBindMatrices" in sk else None
        for k, j in enumerate(sk["joints"]):
            nd = nodes[j]; nm = nd.get("extras", {}).get("name") or nd.get("name", "")
            p = np.linalg.inv(ibm[k])[:3, 3] if (ibm is not None and not posed) else world(j)[:3, 3]
            joints[nm] = tuple(zup(p[None])[0])
    jn = list(joints)
    info["vroid"] = bool(sum(bool(VROID_MAT.search(m)) for m in info["materials"]) >= 2 or
                         any(re.match(r"J_(Bip|Sec|Adj)_", re.sub(r"_\d+$", "", n)) for n in jn) or
                         "vroid" in json.dumps(g.get("asset", {})).lower() or "VRM" in g.get("extensionsUsed", []))
    info["hair_separated"] = info["hair_prims"] > 0
    # strip the exporter's numeric suffix (Object_12 / ORG-forearm.L_114) so bone names can be recognised
    joints = {re.sub(r"_\d+$", "", n): v for n, v in joints.items()}
    if sum(n.startswith("DEF-") for n in joints) >= 10:      # Rigify: deform bones only (ORG/MCH/controls sit elsewhere)
        joints = {n: v for n, v in joints.items() if n.startswith("DEF-")}
        if "DEF-spine.006" in joints and "DEF-spine.004" in joints:   # Rigify human: spine.004/.005 neck, .006 head
            joints["head"] = joints.pop("DEF-spine.006"); joints["neck"] = joints.pop("DEF-spine.004")
            joints.pop("DEF-spine.005", None)
    return np.concatenate(Vs), np.concatenate(Ts), joints, info


def orient(V, J):
    Jc = BA.pick_joints(J) if J else {}
    R = BA.orientation(Jc) if Jc else None
    if R is not None:
        V = V @ R.T
        Jc = {k: np.array(R @ np.array(v)) for k, v in Jc.items()}
    else:
        Jc = {k: np.array(v) for k, v in Jc.items()}
    return V, Jc, R is not None


def forward_sign(V, Jc, zmin, H):
    """-1 when the character faces -Y. Uses foot -> toe joints, else the foot mesh around the ankles, else the nose."""
    votes = []
    for s in "LR":
        if f"foot_{s}" in Jc and f"toe_{s}" in Jc:
            d = Jc[f"toe_{s}"][1] - Jc[f"foot_{s}"][1]
            if abs(d) > 0.01 * H:
                votes.append(np.sign(d))
    if votes:
        return float(np.sign(sum(votes)) or -1), "toe joints"
    low = V[V[:, 2] < zmin + 0.03 * H]
    if len(low) > 20:
        ank = [Jc[f"foot_{s}"][1] for s in "LR" if f"foot_{s}" in Jc]
        c = float(np.mean(ank)) if ank else float(np.median(V[:, 1]))
        ext_pos, ext_neg = low[:, 1].max() - c, c - low[:, 1].min()
        if abs(ext_pos - ext_neg) > 0.01 * H:
            return (1.0 if ext_pos > ext_neg else -1.0), "foot mesh vs ankle"
    return -1.0, "default glTF forward"


def front_profile(V, T, z0, z1, xc, yc, r, fs, n=80):
    zs = np.linspace(z0, z1, n)
    out = []
    for z in zs:
        e = slice_pts(V, T, z, xc, yc, r)
        out.append(None if e is None else float((fs * e[:, 1]).max()))
    return zs, out


def slice_pts(V, T, z, xc, yc, r):
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    pts = []
    for p, q in ((a, b), (b, c), (c, a)):
        dz = q[:, 2] - p[:, 2]
        hit = ((p[:, 2] - z) * (q[:, 2] - z) <= 0) & (np.abs(dz) > 1e-12)
        if hit.any():
            t = (z - p[hit, 2]) / dz[hit]
            pts.append(p[hit, :2] + (q[hit, :2] - p[hit, :2]) * t[:, None])
    if not pts:
        return None
    P = np.concatenate(pts)
    P = P[(np.abs(P[:, 0] - xc) < r) & (np.abs(P[:, 1] - yc) < r)]
    return P if len(P) else None


def head_landmarks(V, T, Jc, zmin, H, fs):
    m = {}
    if "neck" in Jc:
        neck = Jc["neck"]; m["neck"] = "neck joint"
    elif "head" in Jc:
        neck = Jc["head"]; m["neck"] = "head joint"
    else:
        # unrigged: neck = narrowest torso slice between 0.78H and 0.92H
        best = None
        for f in np.linspace(0.78, 0.92, 29):
            P = slice_pts(V, T, zmin + f * H, 0.0, float(np.median(V[:, 1])), 0.12 * H)
            if P is None:
                continue
            w = P[:, 0].max() - P[:, 0].min()
            if best is None or w < best[0]:
                best = (w, np.array([float(np.median(P[:, 0])), float(np.median(P[:, 1])), zmin + f * H]))
        if best is None:
            return None, m
        neck = best[1]; m["neck"] = "narrowest slice (unrigged estimate)"
    xc, yc, nz = float(neck[0]), float(neck[1]), float(neck[2])
    r = 0.11 * H                     # head radius window around the neck axis
    sel = (np.abs(V[:, 0] - xc) < r) & (np.abs(V[:, 1] - yc) < r) & (V[:, 2] > nz)
    if sel.sum() < 50:
        return None, m
    top = float(V[sel, 2].max()); m["top"] = "highest vertex near the head axis"
    L = top - nz
    zs, f = front_profile(V, T, nz - 0.25 * L, nz + 0.55 * L, xc, yc, r, fs, n=120)
    f = np.array([np.nan if v is None else v for v in f], float)
    if np.isnan(f).sum() > 60:
        return None, m
    ok = ~np.isnan(f); f[~ok] = np.interp(zs[~ok], zs[ok], f[ok])
    fsm = np.convolve(np.pad(f, 2, mode="edge"), np.ones(5) / 5, mode="valid")
    df = np.diff(fsm)
    # the jaw underside is nearly horizontal, so the front profile jumps forward fastest there (neck -> chin);
    # only look below the nose region (the lower 60% of the window) so the nose itself is not taken
    lim = int(len(df) * 0.6)
    k = int(np.argmax(df[:lim]))
    if df[k] <= 0:
        return None, m
    j = k
    while j + 1 < len(df) and df[j + 1] > 0.2 * df[k]:
        j += 1
    chin = float(zs[j + 1])
    m["chin"] = "top of the steepest forward jump of the front profile (jaw underside -> chin tip)"
    return {"top": top, "chin": float(chin), "neck_z": nz, "xc": xc, "yc": yc}, m


def rig_agrees(V, J):
    if not (J and any(BA.canon(n)[0] for n in J)):
        return False
    Vt, Jt, _ = orient(np.asarray(V, float), J)
    zlo, zhi = float(Vt[:, 2].min()), float(Vt[:, 2].max())
    hj = Jt.get("head", Jt.get("neck"))
    return hj is not None and zlo + 0.7 * (zhi - zlo) <= hj[2] <= zhi


def measure_file(path):
    V, T, J, info = load_parts(path)
    posed = False
    if J and not rig_agrees(V, J):
        V2_, T2_, J2_, info2_ = load_parts(path, posed=True)
        if rig_agrees(V2_, J2_):
            V, T, J, info, posed = V2_, T2_, J2_, info2_, True
    rec = {"file": os.path.basename(path), "verts": int(len(V)), "flags": [], "methods": {}, "vroid": info["vroid"],
           "hair_separated": info["hair_separated"], "materials": info["materials"][:12], "skin_space": "node pose (bind pose disagreed)" if posed else "bind pose"}
    if info["vroid"]:
        rec["flags"].append("VRoid export: excluded (Sammy's rule, and every VRoid shares one base mesh)")
        return rec
    if not info["hair_separated"]:
        rec["flags"].append("hair not separable (no hair material/node): head top and H include hair")
    rigged = bool(J) and any(BA.canon(n)[0] for n in J)
    if rigged:
        Vt, Jt, _ = orient(np.asarray(V, float), J)
        zlo, zhi = float(Vt[:, 2].min()), float(Vt[:, 2].max())
        hj = Jt.get("head", Jt.get("neck"))
        if hj is None or not (zlo + 0.7 * (zhi - zlo) <= hj[2] <= zhi):
            rec["flags"].append("skeleton disagrees with the mesh (head joint not near the top): rig ignored")
            rigged = False
    if rigged:
        try:
            b = BA.measure(V, T, J, name=rec["file"])
            rec["body"] = b["metrics"]; rec["joints_found"] = b["joints_found"]
        except Exception as e:
            rec["flags"].append(f"body measure failed: {e}")
    V2, Jc, reoriented = orient(np.asarray(V, float), J if rigged else {})
    zmin, zmax = float(V2[:, 2].min()), float(V2[:, 2].max()); H = zmax - zmin
    fs, how = forward_sign(V2, Jc, zmin, H)
    rec["methods"]["forward"] = how
    lm, mm = head_landmarks(V2, np.asarray(T), Jc, zmin, H, fs)
    rec["methods"].update(mm)
    if lm is None:
        rec["flags"].append("head landmarks not found")
        return rec
    hh = lm["top"] - lm["chin"]
    rec["lm"] = {k: round(float(v), 5) for k, v in lm.items()}
    rec["fs"] = fs
    rec["H"] = H
    # keep only head-window triangles so arms/hands/props beside the head do not count
    r = 0.11 * H
    keepv = (np.abs(V2[:, 0] - lm["xc"]) < r) & (np.abs(V2[:, 1] - lm["yc"]) < r) & (V2[:, 2] > lm["chin"] - 0.3 * hh)
    Tk = np.asarray(T)[keepv[np.asarray(T)].all(1)]
    prof = HA.profile_from_mesh(V2, Tk.tolist(), lm["top"], lm["chin"], forward_sign=fs)
    rec["head"] = prof
    rec["heads_tall"] = round(H / hh, 3)
    rec["head_over_height"] = round(hh / H, 4)
    rec["chin_over_neck"] = round((lm["chin"] - lm["neck_z"]) / hh, 3)
    if not (5.0 <= H / hh <= 9.0):
        rec["flags"].append("heads_tall outside 5-9 (child/chibi, merged hair or bad landmark)")
    w = prof["width"].get("0.25")
    if w is None or not (0.4 <= w <= 0.85):
        rec["flags"].append("cranium width implausible (hair merged into the head mesh?)")
    if prof.get("skull_depth_0.3") is None or not (0.55 <= prof["skull_depth_0.3"] <= 1.1):
        rec["flags"].append("skull depth implausible")
    return rec


def main():
    d, out = sys.argv[1], sys.argv[2]
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(".glb"))
    res = []
    for i, f in enumerate(files):
        try:
            res.append(measure_file(os.path.join(d, f)))
        except Exception as e:
            res.append({"file": f, "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-400:]})
        print(i + 1, len(files), f, res[-1].get("heads_tall"), res[-1].get("flags") or res[-1].get("error", ""), flush=True)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
