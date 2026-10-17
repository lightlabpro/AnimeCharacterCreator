"""Measure a v2 head mesh (npz from sdf_head.py) against knowledge/head-targets-dataset.json (p10-p90 bands).
Exact slices of the triangles at each row (like head-shape-audit). Prints a table and writes JSON.
    python3 measure_v2.py MESH.npz [OUT.json]"""
import json
import os
import sys

import numpy as np

ZT, H = 1.685, 0.22
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def slice_pts(v, f, z):
    tri = v[f]
    zs = tri[:, :, 2]
    m = (zs.min(1) < z) & (zs.max(1) > z)
    out = []
    for t in tri[m]:
        pts = []
        for i in range(3):
            a, b = t[i], t[(i + 1) % 3]
            if (a[2] - z) * (b[2] - z) < 0:
                s = (z - a[2]) / (b[2] - a[2])
                pts.append(a + s * (b - a))
        out += pts
    return np.array(out)


def measure(v, f):
    res = {"width": {}, "behind_nose": {}}
    ztop = v[:, 2].max()
    # chin = lowest point of the face front (y < -0.2H), not the neck
    front = v[v[:, 1] < -0.2 * H]
    zchin = front[:, 2].min()
    Hm = ztop - zchin
    res["H_m"] = round(float(Hm), 4)
    rows = {}
    for hh in (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95):
        P = slice_pts(v, f, ztop - hh * Hm)
        rows[hh] = P
        if len(P):
            res["width"][str(hh)] = round(float((P[:, 0].max() - P[:, 0].min()) / Hm), 3)
    P = rows[0.3]
    res["skull_depth_0.3"] = round(float((P[:, 1].max() - P[:, 1].min()) / Hm), 3)
    res["width_to_depth"] = round(res["width"]["0.3"] / res["skull_depth_0.3"], 3)
    # nose tip = most forward point
    ytip = v[:, 1].min()
    for hh in (0.1, 0.2, 0.3, 0.4, 0.6, 0.8, 0.9):
        P = rows[hh]
        mid = P[np.abs(P[:, 0]) < 0.01 * Hm]
        if len(mid):
            res["behind_nose"][str(hh)] = round(float((mid[:, 1].min() - ytip) / Hm), 3)
    return res


def compare(res, bands):
    rows = []
    for grp in ("width", "behind_nose"):
        for k, val in res[grp].items():
            b = bands["head"][grp].get(k)
            if b:
                st = "ok" if b["p10"] <= val <= b["p90"] else ("LOW" if val < b["p10"] else "HIGH")
                rows.append((grp, k, val, b["median"], b["p10"], b["p90"], st))
    for k in ("skull_depth_0.3", "width_to_depth"):
        b = bands["head"][k]; val = res[k]
        st = "ok" if b["p10"] <= val <= b["p90"] else ("LOW" if val < b["p10"] else "HIGH")
        rows.append((k, "", val, b["median"], b["p10"], b["p90"], st))
    return rows


if __name__ == "__main__":
    d = np.load(sys.argv[1])
    res = measure(d["v"].astype(float), d["f"])
    bands = json.load(open(os.path.join(ROOT, "knowledge", "head-targets-dataset.json")))
    rows = compare(res, bands)
    print("H = %.4f m" % res["H_m"])
    for r in rows:
        print("%-16s %-5s %6.3f  med %.3f  [%.3f, %.3f]  %s" % r)
    if len(sys.argv) > 2:
        json.dump({"measure": res, "rows": rows}, open(sys.argv[2], "w"), indent=1)
