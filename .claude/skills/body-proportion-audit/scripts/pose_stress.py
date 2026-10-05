#!/usr/bin/env python3
"""Pose stress and slider sweep for a skinned glTF, with linear blend skinning in numpy (no Blender needed).

    pose_stress.py poses  pack.glb [--json out.json]            bend/twist the main joints and measure the damage
    pose_stress.py sliders pack.glb [--prefix ID-] [--json ..]   push each shape key to 1 and check the surface
    exit 0 pass, 12 fail, 13 unknown, 2 usage

Each pose rotates one joint (and everything under it) about a pivot at the joint, then skins the rest vertices: v' = v + w_sub(v) * (M(v) - v),
where w_sub is the vertex weight on that joint's subtree. Measured on triangles that touch the blend zone (0.02 < w_sub < 0.98):
  stretch   99.9th percentile of posed/rest triangle area      (spikes = weights that pull a surface apart)
  collapse  0.1th percentile of posed/rest triangle area       (pinching / candy wrapper)
  area      total posed/rest area of the blend zone            (a cheap volume-loss proxy; bending legitimately changes it a little)
  folds     fraction of neighbouring triangle pairs whose normals turn from facing the same way to opposing (surface fold-overs)
  twist     forearm twist only: 10th percentile ring radius posed/rest near the wrist (1 = no pinching)
Slider sweep: stretch, collapse and flipped-triangle fraction of rest + target at weight 1 against the rest mesh.
Thresholds are GUESSES calibrated on a few real models, see LIMITS; self-intersection (limbs through the torso) needs Blender and is not checked."""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skin_io

EXIT_PASS, EXIT_FAIL, EXIT_UNKNOWN, EXIT_USAGE = 0, 12, 13, 2
# GUESS values, see calibration notes in the skill; (name, joint key, degrees, axis, distal joint, direction)
POSES = [("elbow_flex", "forearm", 90, "x", "hand", "forward"), ("knee_flex", "shin", 90, "x", "foot", "back"),
         ("hip_flex", "thigh", 90, "x", "shin", "forward"), ("shoulder_forward", "upper_arm", 80, "x", "forearm", "forward"),
         ("shoulder_raise", "upper_arm", 60, "y", "forearm", "up"), ("neck_twist", "neck", 45, "z", None, None), ("forearm_twist", "hand", 90, "bone", None, None)]
LIMITS = {"stretch": 10.0, "collapse": 0.05, "area": (0.6, 1.5), "folds": 0.05, "twist": 0.5,                      # poses
          "slider_stretch": 6.0, "slider_collapse": 0.1, "slider_flips": 0.002}                                  # sliders

def areas(V, T):
    return 0.5 * np.linalg.norm(np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]), axis=1)

def normals(V, T):
    n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]); l = np.linalg.norm(n, axis=1, keepdims=True); return n / np.maximum(l, 1e-18)

def adjacency(T):
    """Pairs of triangles sharing an edge, shape (K, 2)."""
    e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]); f = np.tile(np.arange(len(T)), 3)
    e.sort(1); k = e[:, 0].astype(np.int64) * (e.max() + 1) + e[:, 1]; o = np.argsort(k, kind="stable"); k, f = k[o], f[o]
    same = np.where(k[1:] == k[:-1])[0]; return np.stack([f[same], f[same + 1]], 1)

def rodrigues(axis, deg):
    a = np.asarray(axis, float); a = a / np.linalg.norm(a); t = np.radians(deg); K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K

def subtree(parents, j):
    S = np.zeros(len(parents), bool); S[j] = True
    changed = True
    while changed:
        changed = False
        for i, p in enumerate(parents):
            if p >= 0 and S[p] and not S[i]: S[i] = True; changed = True
    return S

def pose_one(m, name, jk, deg, axis, distal, direction):
    """-> dict of metrics for one pose, or None if the joints are missing."""
    key = m["key"]; H = float(m["V"][:, 2].max() - m["V"][:, 2].min())
    cands = [f"{jk}_{s}" for s in "LR" if f"{jk}_{s}" in key] or ([jk] if jk in key else [])
    out = {}
    for ck in cands:
        j = key[ck]; p = m["jpos"][j]; V, T, W, J = m["V"], m["T"], m["W"], m["J"]
        sub = subtree(m["parents"], j); wsub = (W * sub[J]).sum(1)
        if name == "forearm_twist":
            elbow = m["jpos"][key[ck.replace("hand", "forearm")]]; ax = p - elbow; axis_v = ax / np.linalg.norm(ax); Rm = rodrigues(axis_v, deg)
        else:
            axis_v = {"x": [1, 0, 0], "y": [0, -1, 0], "z": [0, 0, 1]}[axis]; Rm = rodrigues(axis_v, deg)
            if distal:
                d = m["jpos"][key[ck.replace(jk, distal)]]; want = {"forward": [0, -1, 0], "back": [0, 1, 0], "up": [0, 0, 1]}[direction]
                if (Rm @ (d - p) - (d - p)) @ want < (rodrigues(axis_v, -deg) @ (d - p) - (d - p)) @ want: Rm = rodrigues(axis_v, -deg)
        P = (V - p) @ Rm.T + p; Vp = V + wsub[:, None] * (P - V)
        ws = wsub[T]; zone = (ws.max(1) > 0.02) & (ws.min(1) < 0.98)          # triangles that straddle the moving part and the still part
        a0, a1 = areas(V, T), areas(Vp, T); ok = a0 > 1e-12; r = np.where(ok, a1 / np.where(ok, a0, 1), 1.0)
        res = {"zone_faces": int(zone.sum())}
        if zone.sum() < 4: res["note"] = "no triangle crosses this joint (no mesh over it, or separate meshes)"; res["stretch"] = res["collapse"] = None
        else:
            rz = r[zone & ok]; res["stretch"] = float(np.percentile(rz, 99.9)); res["collapse"] = float(np.percentile(rz, 0.1))
            res["area"] = float(a1[zone].sum() / max(a0[zone].sum(), 1e-18))
        adj = adjacency(T); n0, n1 = normals(V, T), normals(Vp, T)
        if len(adj):
            z2 = zone[adj[:, 0]] | zone[adj[:, 1]]; same = (n0[adj[:, 0]] * n0[adj[:, 1]]).sum(1) > 0.5; opp = (n1[adj[:, 0]] * n1[adj[:, 1]]).sum(1) < -0.2
            res["folds"] = float((same & opp & z2).sum() / max(z2.sum(), 1))
        if name == "forearm_twist":
            s = ((V - elbow) @ axis_v) / np.linalg.norm(p - elbow); rad = lambda X: np.linalg.norm((X - elbow) - np.outer((X - elbow) @ axis_v, axis_v), axis=1)
            sel = (s > 0.6) & (s < 1.0) & (rad(V) < 0.1 * H)     # forearm-to-wrist ring
            own = (W * (sub | np.isin(np.arange(len(m['names'])), [key[ck.replace('hand', 'forearm')]]))[J]).sum(1) > 0.9
            sel &= own
            if sel.sum() >= 8: res["twist"] = float(np.percentile(rad(Vp[sel]), 10) / max(np.percentile(rad(V[sel]), 10), 1e-12))
            else: res["twist"] = None
        out[ck] = res
    return out

def verdict_pose(res):
    bad = []
    if res.get("stretch") is not None and res["stretch"] > LIMITS["stretch"]: bad.append(f"stretch {res['stretch']:.1f} > {LIMITS['stretch']}")
    if res.get("collapse") is not None and res["collapse"] < LIMITS["collapse"]: bad.append(f"collapse {res['collapse']:.2f} < {LIMITS['collapse']}")
    if res.get("area") is not None and not LIMITS["area"][0] <= res["area"] <= LIMITS["area"][1]: bad.append(f"zone area x{res['area']:.2f} outside {LIMITS['area']}")
    if res.get("folds", 0) > LIMITS["folds"]: bad.append(f"{res['folds']:.2%} of surface edges fold over")
    if res.get("twist") is not None and res["twist"] < LIMITS["twist"]: bad.append(f"twist pinches the wrist to {res['twist']:.2f} of its radius")
    return bad

def run_poses(m):
    rows = []
    if not m.get("oriented"): return "unknown", [("poses", "unknown", "skeleton not recognised, cannot pose")]
    for name, jk, deg, axis, distal, direction in POSES:
        r = pose_one(m, name, jk, deg, axis, distal, direction)
        if not r: rows.append((name, "unknown", "joint missing")); continue
        for ck, res in r.items():
            bad = verdict_pose(res)
            if res.get("stretch") is None and res.get("twist") is None: rows.append((f"{name} {ck}", "unknown", res.get("note", "not measurable")))
            else:
                bits = " ".join(f"{k}={res[k]:.2f}" if k not in ("folds",) else f"folds={res[k]:.2%}" for k in ("stretch", "collapse", "area", "folds", "twist") if res.get(k) is not None)
                rows.append((f"{name} {ck}", "fail" if bad else "ok", ("; ".join(bad) + " | " if bad else "") + bits))
    st = "fail" if any(r[1] == "fail" for r in rows) else "unknown" if any(r[1] == "unknown" for r in rows) else "pass"
    return st, rows

def run_sliders(m, prefix="ID-"):
    V, T = m["V"], m["T"]; a0 = areas(V, T); ok = a0 > 1e-12; n0 = normals(V, T); rows = []
    ts = {k: D for k, D in m["targets"].items() if k.startswith(prefix)}
    if not ts: return "unknown", [("sliders", "unknown", f"no morph targets starting with {prefix!r}")]
    for k, D in sorted(ts.items()):
        if not np.any(D): rows.append((k, "warn", "target moves nothing")); continue
        Vp = V + D; a1 = areas(Vp, T); r = np.where(ok, a1 / np.where(ok, a0, 1), 1.0); flips = float((np.sum(n0 * normals(Vp, T), 1) < 0).mean())
        st, co = float(np.percentile(r[ok], 99.9)), float(np.percentile(r[ok], 0.1)); bad = []
        if st > LIMITS["slider_stretch"]: bad.append(f"stretch {st:.1f}")
        if co < LIMITS["slider_collapse"]: bad.append(f"collapse {co:.2f}")
        if flips > LIMITS["slider_flips"]: bad.append(f"{flips:.2%} triangles flipped")
        rows.append((k, "fail" if bad else "ok", ("; ".join(bad) + " | " if bad else "") + f"stretch={st:.2f} collapse={co:.2f} flips={flips:.2%}"))
    return ("fail" if any(r[1] == "fail" for r in rows) else "pass"), rows

def report(title, st, rows):
    return "\n".join([f"{title}: {st.upper()}"] + [f"  {s.upper():7s} {r:26s} {msg}" for r, s, msg in rows])

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["poses", "sliders"]); ap.add_argument("file"); ap.add_argument("--prefix", default="ID-"); ap.add_argument("--json")
    try: a = ap.parse_args(argv)
    except SystemExit as e: return EXIT_USAGE if e.code else 0
    try:
        m = skin_io.orient(skin_io.load(a.file)); st, rows = run_poses(m) if a.cmd == "poses" else run_sliders(m, a.prefix)
    except (OSError, ValueError, KeyError) as e: print(f"error: {e}", file=sys.stderr); return EXIT_USAGE
    print(report(f"POSE STRESS {os.path.basename(a.file)}" if a.cmd == "poses" else f"SLIDER SWEEP {os.path.basename(a.file)}", st, rows))
    if a.json:
        with open(a.json, "w") as f: json.dump({"status": st, "rows": rows}, f, indent=1)
    return {"pass": EXIT_PASS, "fail": EXIT_FAIL, "unknown": EXIT_UNKNOWN}[st]

if __name__ == "__main__":
    sys.exit(main())
