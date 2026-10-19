"""Fit the profile knobs of mhs3_reshape.py to the mesh rules of knowledge/mhs3_face_rules.json (q36).

    python3 mhs3_fit_profile.py vroid_mesh.npz OUT_knobs.json [--start knobs.json]

Nelder-Mead over nose_back, root_lift and the lower-face forward table (upper lip, lower lip, chin), minimising the
sum of squared err_tol of every mesh rule (profile + proportions). Prints the per-rule result; the knobs still go
through the full validator (renders + TypeSafe) before a version counts.
"""
import json
import os
import sys
import types

import numpy as np

sys.modules.setdefault("bpy", types.ModuleType("bpy"))
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mhs3_reshape as R  # noqa: E402
import mhs3_measure as M  # noqa: E402
from scipy.optimize import minimize  # noqa: E402

RULES = json.load(open(os.path.join(HERE, "..", "..", "knowledge", "mhs3_face_rules.json")))
MESH = {k: r for k, r in RULES["rules"].items() if r["kind"] == "mesh"}
BASE = dict(R.K)


EXT = "--ext" in sys.argv          # q40: other VRoid bases (ea4402ae) need the nose tip in the fit too
CAP = 0.005 if EXT else 0.003


def knobs(p):
    nb, rl, l0, l1, l2, l3 = p[:6]
    k = {"nose_back": nb, "root_lift": rl,
         "lowface_fwd": [[0.62, 0.0], [0.76, l0], [0.88, l1], [1.02, l2], [1.30, l3], [1.70, 0.0]]}
    if EXT:
        k["nose_tip_back"] = p[6]
        k["nose_tip_up"] = p[7]
        k["chin_fwd"] = p[8]
        k["bridge_back"] = p[9]
    return k


def evaluate(src, k):
    R.K.clear(); R.K.update(BASE); R.K.update(k)
    parts = {}
    for p, (V, T) in src.items():
        key = p.replace("N00_000_00_", "").replace("N00_000_", "")
        parts[p] = (R.warp(V.astype(float), key), T)
    m, _ = M.measure(parts)
    err = {rid: abs(m[r["metric"]] - r["target"]) / r["tol"] for rid, r in MESH.items() if r["metric"] in m}
    return m, err


def main():
    src = M.load_parts(sys.argv[1]); out = sys.argv[2]
    M.ORIG = M.part(src, "Face_00_SKIN")[0]
    p0 = np.array([0.0063, 0.0027, 0.001, 0.0, 0.0, -0.0025])
    if "--start" in sys.argv:
        s = json.load(open(sys.argv[sys.argv.index("--start") + 1]))
        BASE.update(s)        # q40: evaluate on the FULL start knobs (jaw / nose / chin tables), not on the defaults
        p0 = np.array([s.get("nose_back", 0.0055), s.get("root_lift", 0.005)] + [v for _, v in s["lowface_fwd"][1:5]]
                      if "lowface_fwd" in s else [s.get("nose_back", 0.0055), s.get("root_lift", 0.005), 0, 0, 0, 0])

    if EXT:
        p0 = np.r_[p0, json.load(open(sys.argv[sys.argv.index("--start") + 1])).get("nose_tip_back", 0.0) if "--start" in sys.argv else 0.0, 0.0025, BASE.get("chin_fwd", 0.0045), 0.002]
    n = len(p0)

    def f(p):
        _, e = evaluate(src, knobs(p))
        # squared errors, extra weight on anything outside tolerance + small knob regulariser (stay near the base)
        return sum(x * x + 4 * max(0.0, x - 1.0) ** 2 for x in e.values()) + 1e6 * float(np.sum(np.square(np.maximum(0, np.abs(p[2:6]) - CAP)))) + 2e5 * float(np.sum(np.square(np.diff(np.r_[0, p[2:6], 0], 2))))
    r = minimize(f, p0, method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-3, "maxiter": 300,
                                                       "initial_simplex": [p0] + [p0 + np.eye(n)[i] * 0.0015 for i in range(n)]})
    k = knobs(r.x); m, e = evaluate(src, k)
    json.dump({kk: (round(v, 5) if isinstance(v, float) else [[a, round(b, 5)] for a, b in v]) for kk, v in k.items()},
              open(out, "w"), indent=1)
    print("knobs", json.dumps(json.load(open(out))))
    for rid, x in sorted(e.items(), key=lambda kv: -kv[1]):
        print("%-5s %-22s %.4f target %.4f err %.2f" % ("PASS" if x <= 1 else "FAIL", rid, m[MESH[rid]["metric"]], MESH[rid]["target"], x))


if __name__ == "__main__":
    main()
