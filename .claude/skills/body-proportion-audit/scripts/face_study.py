#!/usr/bin/env python3
"""Face form study on reference GLBs (dataset pass 2, 2026-10-15) - what makes a face read full instead of pushed in.

    python3 face_study.py GLB_DIR MEASURED_JSON OUT_JSON

Uses the landmarks of measure_dataset.py (MEASURED_JSON: top, chin, head axis, forward sign) and slices the head with
horizontal planes. For each level (fraction of head height hh from the skull top: brow 0.42, eye 0.50, cheek 0.62,
mouth 0.76, jaw 0.86) it records, in hh units:
  width      full width of the slice
  setback_k  how far the front of the face at |x| = k*hh lies behind the front at the centre line (0 = flat front,
             large = the sides fall away fast). Averaged over both sides.
  front      front of the centre line relative to the forehead front at 0.30 (positive = ahead of the forehead)
A face that looks "pushed in" has the centre (nose/mouth/chin) set back against the forehead and cheeks, or cheeks
that fall away late and then drop (a concave cross-section): `concave_k` = setback at k minus the straight line from
the centre to the side wall (negative = the cross-section bows inward).
Meshes are only measured; nothing is copied or saved.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_dataset as MD     # noqa: E402

LEVELS = {"brow": 0.42, "eye": 0.50, "cheek": 0.62, "mouth": 0.76, "jaw": 0.86}
KS = (0.10, 0.20, 0.30)


def front_at(P, x, fs, band):
    sel = np.abs(P[:, 0] - x) < band
    return None if not sel.any() else float((fs * P[sel, 1]).max())


def study(V, T, lm, fs):
    hh = lm["top"] - lm["chin"]; xc, yc = lm["xc"], lm["yc"]
    r = 0.75 * hh
    out = {}
    ref = MD.slice_pts(V, T, lm["top"] - 0.30 * hh, xc, yc, r)
    f30 = None if ref is None else front_at(ref, xc, fs, 0.02 * hh)
    for name, f in LEVELS.items():
        P = MD.slice_pts(V, T, lm["top"] - f * hh, xc, yc, r)
        if P is None:
            continue
        c = front_at(P, xc, fs, 0.02 * hh)
        if c is None:
            continue
        row = {"width": round(float(P[:, 0].max() - P[:, 0].min()) / hh, 3)}
        if f30 is not None:
            row["front"] = round((c - f30) / hh, 3)
        half = (P[:, 0].max() - P[:, 0].min()) / 2
        for k in KS:
            vals = [front_at(P, xc + s * k * hh, fs, 0.015 * hh) for s in (-1, 1)]
            vals = [v for v in vals if v is not None]
            if vals and k * hh < half * 0.95:
                sb = (c - float(np.mean(vals))) / hh
                row["setback_%.2f" % k] = round(sb, 3)
        out[name] = row
    return out


def main():
    d, mj, out = sys.argv[1], sys.argv[2], sys.argv[3]
    meas = {m["file"]: m for m in json.load(open(mj))}
    res = []
    for f in sorted(os.listdir(d)):
        m = meas.get(f)
        if not f.endswith(".glb") or not m or "lm" not in m:
            continue
        try:
            V, T, J, info = MD.load_parts(os.path.join(d, f), posed=(m.get("skin_space", "").startswith("node")))
            rig = bool(J) and any(MD.BA.canon(n)[0] for n in J)
            V2, Jc, _ = MD.orient(np.asarray(V, float), J if rig and "skeleton disagrees" not in " ".join(m["flags"]) else {})
            res.append({"file": f, "heads_tall": m.get("heads_tall"), "flags": m["flags"], "face": study(V2, np.asarray(T), m["lm"], m["fs"])})
        except Exception as e:
            res.append({"file": f, "error": repr(e)})
        print(len(res), f, res[-1].get("face", {}).get("cheek"), flush=True)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
