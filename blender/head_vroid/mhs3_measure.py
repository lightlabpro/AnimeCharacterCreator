"""Measure a reshaped VRoid head (GLB) against the MHS3 rulebook (q36).

    bpyenv/bin/python mhs3_measure.py HEAD.glb OUT.json [--rules knowledge/mhs3_face_rules.json]

Reads the real vertices per part (Face skin, eye white, iris, brow, eyeline, mouth), measures every rule in the
rulebook in D units (D = pupil line to chin bottom, front view) and writes the per-rule value, target, tolerance,
error (in tolerances) and pass/fail. Exit 0 when every rule passes, 12 otherwise.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def load_parts(path):
    """{part: (V world, F tris)} from a GLB via bpy, or from an npz (keys PART__V, PART__T)."""
    if path.endswith(".npz"):
        d = np.load(path); out = {}
        for k in d.files:
            if k.endswith("__V"):
                p = k[:-3]; out[p] = (d[k], d[p + "__T"])
        return out
    import bpy
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.import_scene.gltf(filepath=path)
    out = {}
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or not o.data.materials:
            continue
        key = o.data.materials[0].name.split("_Instance")[0]
        mw = np.array(o.matrix_world); co = np.array([v.co[:] for v in o.data.vertices])
        W = (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3]
        o.data.calc_loop_triangles()
        T = np.array([t.vertices[:] for t in o.data.loop_triangles])
        out[key] = (W, T)
    return out


def part(parts, name):
    for k, v in parts.items():
        if name in k:
            return v
    raise KeyError(name)


def profile(V, T, zs, xw=0.004):
    """Front-most y of the mesh surface on the midline at each height z (ray cast along -y, x = 0)."""
    A, B, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    out = []
    for zq in zs:
        best = -np.inf
        for x in (0.0,):
            v0, v1 = B - A, C - A; p = np.array([x, 0, zq])
            v2 = p - A
            d00 = v0[:, 0] ** 2 + v0[:, 2] ** 2; d01 = v0[:, 0] * v1[:, 0] + v0[:, 2] * v1[:, 2]
            d11 = v1[:, 0] ** 2 + v1[:, 2] ** 2
            d20 = v2[:, 0] * v0[:, 0] + v2[:, 2] * v0[:, 2]; d21 = v2[:, 0] * v1[:, 0] + v2[:, 2] * v1[:, 2]
            den = d00 * d11 - d01 ** 2; den[np.abs(den) < 1e-16] = np.nan
            b = (d11 * d20 - d01 * d21) / den; c = (d00 * d21 - d01 * d20) / den; a = 1 - b - c
            hit = (a >= -1e-9) & (b >= -1e-9) & (c >= -1e-9)
            if hit.any():
                best = max(best, (a * A[:, 1] + b * B[:, 1] + c * C[:, 1])[hit].max())
        out.append(best)
    return np.array(out)


ORIG = None


def measure(parts):
    FV, FT = part(parts, "Face_00_SKIN")
    EW, _ = part(parts, "EyeWhite")
    IR, _ = part(parts, "EyeIris")
    MO = part(parts, "FaceMouth")[0]
    # pupils: iris centroid per side
    pl, pr = IR[IR[:, 0] > 0].mean(0), IR[IR[:, 0] < 0].mean(0)
    zp = 0.5 * (pl[2] + pr[2]); ipd = abs(pl[0] - pr[0])
    # chin bottom: lowest face-skin vertex near the midline in front of the neck
    front = FV[:, 1] > np.percentile(FV[:, 1], 40)
    mid = (np.abs(FV[:, 0]) < 0.01) & front
    zs = np.linspace(zp + 0.06, zp - 0.16, 441)
    prof = profile(FV, FT, zs)
    ok = np.isfinite(prof)
    # chin bottom = where the midline profile, walking down from the mouth, turns sharply back (under-chin)
    # use the front-view silhouette: lowest z where the front profile is still within 25 mm of the nose tip
    tip_i = np.nanargmax(np.where(ok & (zs < zp - 0.02) & (zs > zp - 0.08), prof, -np.inf))
    ztip, ytip = zs[tip_i], prof[tip_i]
    below = (zs < ztip - 0.03) & ok
    dy = np.gradient(np.where(ok, prof, np.nan), zs)
    # under-chin: profile y drops fast going down (dy/dz large positive)
    cand = np.where(below & (dy > 1.2))[0]
    zchin = zs[cand[0]] if len(cand) else FV[mid, 2].min()
    D = zp - zchin
    def at(dD):
        z = zp - dD * D; i = np.argmin(np.abs(zs - z)); return prof[i]
    # landmarks along the profile (in D, below the pupils)
    sub_i = tip_i + np.argmin(np.where(ok[tip_i:tip_i + 60], prof[tip_i:tip_i + 60], np.inf))  # subnasale dip
    zsub = zs[min(sub_i, len(zs) - 1)]
    # lips / mouth line from the mouth mesh height
    zm = np.median(MO[:, 2]) if len(MO) else zp - 0.64 * D
    seg = (zs < zsub - 0.002) & (zs > zchin + 0.004) & ok
    i_seg = np.where(seg)[0]
    # upper lip = first local max of profile below subnasale, chin = last local max above under-chin
    yy = prof[i_seg]
    lm = [i_seg[k] for k in range(1, len(i_seg) - 1) if yy[k] >= yy[k - 1] and yy[k] >= yy[k + 1]]
    ulip = lm[0] if lm else i_seg[0]
    chin = lm[-1] if lm else i_seg[-1]
    eye_front = EW[:, 1].max()
    m = {
        "D_m": D, "ipd_D": ipd / D,
        "nose_tip_below_D": (zp - ztip) / D,
        "subnasale_below_D": (zp - zsub) / D,
        "chin_below_D": 1.0,
        "brow_behind_tip_D": (ytip - at(-0.10)) / D,
        "eye_level_behind_tip_D": (ytip - at(0.0)) / D,
        "bridge_behind_tip_D": (ytip - at(0.18)) / D,
        "subnasale_behind_tip_D": (ytip - prof[sub_i]) / D,
        "upper_lip_behind_tip_D": (ytip - prof[ulip]) / D,
        "mouth_line_behind_tip_D": (ytip - at((zp - zm) / D)) / D,
        "lower_lip_behind_tip_D": (ytip - at(0.72)) / D,
        "chin_behind_tip_D": (ytip - np.nanmax(np.where((zs <= zp - 0.80 * D) & (zs >= zp - 0.95 * D) & ok, prof, -np.inf))) / D,
        "eye_white_front_behind_tip_D": (ytip - eye_front) / D,
        "mouth_below_D": (zp - zm) / D,
        "chin_front_below_D": (zp - zs[chin]) / D,
    }
    # q36 MHS3-04 view: 70 deg yaw silhouette ahead of the near iris centre (s = y sin a - x cos a, near eye = +x)
    a = np.radians(70.0); S = FV[:, 1] * np.sin(a) - FV[:, 0] * np.cos(a)
    s_eye = pl[1] * np.sin(a) - pl[0] * np.cos(a)
    def sil(dD, band=0.012):
        z = zp - dD * D; k = np.abs(FV[:, 2] - z) < band * D
        return float((S[k].max() - s_eye) / D) if k.any() else float("nan")
    for nm, dD in (("eye", 0.0), ("upper_nose", 0.28), ("tip", None), ("mouth", None), ("lower_lip", 0.70),
                   ("chin_front", 0.85)):
        if nm == "tip":
            m["y70_tip_ahead_D"] = max(sil(t) for t in np.linspace(0.3, 0.55, 26))
        elif nm == "mouth":
            m["y70_mouth_ahead_D"] = sil((zp - zm) / D)
        else:
            m["y70_%s_ahead_D" % nm] = sil(dD)
    # dataset bands (knowledge/head-targets-dataset.json): fractions of H = skull top (face skin) .. chin bottom
    SK = np.vstack([v for k, (v, _) in parts.items() if "SKIN" in k])
    ztop = SK[:, 2].max(); H = ztop - zchin
    def hband(t, band=0.01):
        z = ztop - t * H; k = np.abs(SK[:, 2] - z) < band * H
        return SK[k] if k.any() else None
    s3 = hband(0.3)
    m["H_m"] = H
    m["heads_D_per_H"] = D / H
    if s3 is not None:
        m["skull_depth_0.3_H"] = (s3[:, 1].max() - s3[:, 1].min()) / H
        m["nose_ahead_of_forehead_0.3_H"] = (ytip - s3[:, 1].max()) / H
    TS = [(v, t) for k, (v, t) in parts.items() if "SKIN" in k]
    for t in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        z = ztop - t * H
        yf = max(float(profile(v, tt, [z])[0]) for v, tt in TS)
        if np.isfinite(yf):
            m["behind_nose_%.1f_H" % t] = (ytip - yf) / H
    # lash vs lid: the lowest upper eyeline vertex over the pupil must sit on the top edge of the eye hole (q36: m30
    # floated 1 mm above it - a skin band between lash and white)
    try:
        EL = part(parts, "FaceEyeline")[0]
        E = {}
        for t in FT:
            for a_, b_ in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k_ = (min(a_, b_), max(a_, b_)); E[k_] = E.get(k_, 0) + 1
        pts = []
        for (a_, b_), c_ in E.items():
            if c_ == 1:
                for s_ in np.linspace(0, 1, 5):
                    p_ = FV[a_] * (1 - s_) + FV[b_] * s_
                    if abs(p_[0] - pl[0]) < 0.0015 and abs(p_[2] - pl[2]) < 0.02:
                        pts.append(p_[2])
        el = EL[(np.abs(EL[:, 0] - pl[0]) < 0.004) & (EL[:, 0] > 0)][:, 2]
        m["lash_gap_mm"] = (el[el > pl[2]].min() - max(pts)) * 1000
    except (KeyError, ValueError):
        pass
    # q36 artifacts: nothing of the mouth interior may stand in front of the face skin (it showed as grey patches)
    try:
        MV = part(parts, "FaceMouth")[0]
        sub = MV[::3]
        A_, B_, C_ = FV[FT[:, 0]], FV[FT[:, 1]], FV[FT[:, 2]]
        worst = 0.0
        for pnt in sub:
            v0, v1 = B_ - A_, C_ - A_; v2 = np.array([pnt[0], 0, pnt[2]]) - A_
            d00 = v0[:, 0] ** 2 + v0[:, 2] ** 2; d01 = v0[:, 0] * v1[:, 0] + v0[:, 2] * v1[:, 2]; d11 = v1[:, 0] ** 2 + v1[:, 2] ** 2
            d20 = v2[:, 0] * v0[:, 0] + v2[:, 2] * v0[:, 2]; d21 = v2[:, 0] * v1[:, 0] + v2[:, 2] * v1[:, 2]
            den = d00 * d11 - d01 ** 2; den[np.abs(den) < 1e-16] = np.nan
            bb_ = (d11 * d20 - d01 * d21) / den; cc_ = (d00 * d21 - d01 * d20) / den; aa_ = 1 - bb_ - cc_
            hit = (aa_ >= 0) & (bb_ >= 0) & (cc_ >= 0)
            if hit.any():
                ys_ = (aa_ * A_[:, 1] + bb_ * B_[:, 1] + cc_ * C_[:, 1])[hit]
                front = ys_.max()
                if np.abs(pnt[0]) < 0.03 and pnt[1] > front - 0.002:      # only where the skin is the outer surface
                    worst = max(worst, (pnt[1] - front) * 1000)
        m["mouth_poke_mm"] = worst
    except KeyError:
        pass
    # ears: the face-skin shell outside the head side (|x| > 0.088 m before / after the warp)
    sel = (np.abs(FV[:, 0]) > 0.088) & (FV[:, 1] < 0.005)
    if ORIG is not None and len(ORIG) == len(FV):            # ear vertices picked on the unwarped mesh, tracked
        sel = (np.abs(ORIG[:, 0]) > 0.088) & (ORIG[:, 1] < 0.005)
    ear = FV[sel]
    if len(ear):
        m["ear_top_above_D"] = (ear[:, 2].max() - zp) / D
        m["ear_bottom_below_D"] = (zp - ear[:, 2].min()) / D
    # front widths
    def width_at(dD, V=FV):
        z = zp - dD * D; s = V[np.abs(V[:, 2] - z) < 0.002]
        return (s[:, 0].max() - s[:, 0].min()) / D if len(s) else float("nan")
    # q38 iris dish (Sammy: the MHS3 iris is concave): rim (outer 20 % of radius) forward of the centre, mm, per eye
    dish = []
    for sgn in (1, -1):
        I = IR[IR[:, 0] * sgn > 0]
        if len(I) > 10:
            cx, cz = I[:, 0].mean(), I[:, 2].mean()
            rn = np.hypot((I[:, 0] - cx) / max(np.abs(I[:, 0] - cx).max(), 1e-6), (I[:, 2] - cz) / max(np.abs(I[:, 2] - cz).max(), 1e-6))
            if (rn > 0.8).any() and (rn < 0.3).any():
                dish.append((I[rn > 0.8, 1].mean() - I[rn < 0.3, 1].mean()) * 1000)
    if dish:
        m["iris_dish_mm"] = float(np.mean(dish))
    m["face_width_eye_D"] = width_at(0.0)
    m["face_width_mouth_D"] = width_at(m["mouth_below_D"])
    m["face_width_chin85_D"] = width_at(0.85)
    side = EW[EW[:, 0] > 0]
    m["mesh_eyewhite_w_D"] = (side[:, 0].max() - side[:, 0].min()) / D
    m["mesh_eyewhite_h_D"] = (side[:, 2].max() - side[:, 2].min()) / D
    m["mesh_eyewhite_aspect"] = m["mesh_eyewhite_w_D"] / max(m["mesh_eyewhite_h_D"], 1e-6)
    return {k: float(round(v, 4)) for k, v in m.items()}, (zs, prof, zp, D, ytip)


def check(m, rules):
    res = {}; worst = 0.0
    for rid, r in rules["rules"].items():
        if r.get("metric") not in m:
            res[rid] = {"status": "unknown"}; continue
        v = m[r["metric"]]; t = r["target"]; tol = r["tol"]
        err = abs(v - t) / tol
        res[rid] = {"value": v, "target": t, "tol": tol, "err_tol": round(err, 2), "pass": bool(err <= 1.0),
                    "region": r.get("region"), "why": r.get("why", "")}
        worst = max(worst, err)
    score = float(np.sqrt(np.mean([x["err_tol"] ** 2 for x in res.values() if "err_tol" in x]))) if res else 0
    return res, worst, score


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if "--" in sys.argv:
        a = sys.argv[sys.argv.index("--") + 1:]
        a = [x for x in a if not x.startswith("--")]
    src, out = a[0], a[1]
    rp = os.path.join(REPO, "knowledge", "mhs3_face_rules.json")
    if "--rules" in sys.argv:
        rp = sys.argv[sys.argv.index("--rules") + 1]
    parts = load_parts(src)
    global ORIG
    if "--orig" in sys.argv:
        ORIG = part(load_parts(sys.argv[sys.argv.index("--orig") + 1]), "Face_00_SKIN")[0]
    m, (zs, prof, zp, D, ytip) = measure(parts)
    rep = {"src": src, "metrics": m}
    code = 0
    if os.path.exists(rp):
        rules = json.load(open(rp))
        geo = {"rules": {k: v for k, v in rules["rules"].items() if v.get("kind", "mesh") == "mesh"}}
        res, worst, score = check(m, geo)
        rep.update(results=res, worst_err_tol=round(worst, 2), rms_err_tol=round(score, 3))
        code = 0 if all(r.get("pass") for r in res.values()) else 12
    rep["profile"] = {"z_below_D": [round(float((zp - z) / D), 3) for z in zs[::5]],
                      "behind_tip_D": [None if not np.isfinite(p) else round(float((ytip - p) / D), 4) for p in prof[::5]]}
    json.dump(rep, open(out, "w"), indent=1)
    for k, v in m.items():
        print("%-32s %s" % (k, v))
    if "results" in rep:
        print("--- rules (err in tolerances) worst %.2f rms %.3f" % (rep["worst_err_tol"], rep["rms_err_tol"]))
        for k, r in sorted(rep["results"].items(), key=lambda kv: -kv[1].get("err_tol", 0)):
            if "err_tol" in r:
                print("%-5s %-28s %.3f target %.3f +-%.3f  err %.2f" % ("PASS" if r["pass"] else "FAIL", k, r["value"],
                                                                       r["target"], r["tol"], r["err_tol"]))
    sys.exit(code)


if __name__ == "__main__":
    main()
