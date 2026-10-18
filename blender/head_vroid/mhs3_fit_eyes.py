"""Fit the eye-opening knobs to the Leo eye-shape template (q36 eye-shape standard).

    python3 mhs3_fit_eyes.py vroid_mesh.npz BASE_knobs.json OUT_knobs.json [--bias render_rm.json]

Uses the mesh proxy (mhs3_eye_proxy) - optionally bias-corrected with the last render of BASE (render outline minus
proxy outline) - and Nelder-Mead over eye_tilt, lid_up, lid_up_c, lid_up_w, lid_low, lid_low_out, eye_sx_out.
Objective: outline RMS vs eye_shape_template + tilt rule + keep the opening aspect at the rule target. The result
must still pass the render validator (mhs3_validate.py) - the proxy is only a guide."""
import json
import os
import sys
import types

import numpy as np

sys.modules.setdefault("bpy", types.ModuleType("bpy"))
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mhs3_reshape as R  # noqa: E402
from mhs3_eye_proxy import opening  # noqa: E402
from mhs3_measure import load_parts  # noqa: E402
from scipy.optimize import least_squares  # noqa: E402

RULES = json.load(open(os.path.join(HERE, "..", "..", "knowledge", "mhs3_face_rules.json")))
T = RULES["eye_shape_template"]
NAMES = ["eye_tilt", "lid_up", "lid_up_c", "lid_up_w", "lid_low", "lid_low_out", "eye_sx_out", "lid_in_drop", "lid_out_up"]


def run(src, base, p):
    R.K.clear(); R.K.update(base); R.K.update(dict(zip(NAMES, p)))
    parts = {}
    for k, (V, F) in src.items():
        if any(s in k for s in ("Face_00_SKIN", "EyeIris")):
            parts[k] = (R.warp(V.astype(float), k.replace("N00_000_00_", "").replace("N00_000_", "")), F)
    return opening(parts)


def main():
    src = load_parts(sys.argv[1]); base = json.load(open(sys.argv[2])); out = sys.argv[3]
    full = dict(R.K); full.update(base); base = full
    p0 = np.array([base.get(n, d) for n, d in zip(NAMES, (0.0, 0.0026, -0.25, 0.5, 0.0004, 0.0, 0.80, 0.0, 0.0))])
    bt = np.zeros(9); bb = np.zeros(9); btilt = 0.0; basp = 1.0
    o0 = run(src, base, p0)
    if "--bias" in sys.argv:
        r = json.load(open(sys.argv[sys.argv.index("--bias") + 1]))["render"]
        eyes = [r["eye_l"], r["eye_r"]]
        bt = np.mean([e["shape_top"] for e in eyes], 0) - np.array(o0["shape_top"])
        bb = np.mean([e["shape_bot"] for e in eyes], 0) - np.array(o0["shape_bot"])
        btilt = np.mean([e["corner_tilt"] for e in eyes]) - o0["corner_tilt"]
        basp = np.mean([e["w"] / e["h"] for e in eyes]) / (o0["w_mm"] / o0["h_mm"])
    asp_t = RULES["rules"]["R3_eye_aspect"]["target"]; tilt_t = RULES["rules"]["ES1_eye_tilt"]["target"]
    h0 = o0["h_mm"]

    def pred(p):
        o = run(src, base, p)
        top = np.array(o["shape_top"]) + bt; bot = np.array(o["shape_bot"]) + bb
        return o, top, bot, o["corner_tilt"] + btilt, o["w_mm"] / o["h_mm"] * basp

    SC = np.array((0.0015, 0.0010, 0.25, 0.2, 0.0006, 0.0010, 0.05, 0.0015, 0.0015))

    def resid(q):
        p = p0 + q * SC
        try:
            o, top, bot, tilt, asp = pred(p)
        except Exception as ex:                   # noqa: BLE001 - opening lost
            print("resid error", repr(ex)); return np.full(30, 10.0)
        e = np.r_[top - T["top"], bot - T["bot"]] / 0.03 / np.sqrt(18)
        return np.r_[e, (tilt - tilt_t) / 0.04, (asp - asp_t) / 0.08, (o["h_mm"] - h0) / 3.0,
                     0.05 * q]                     # mild pull toward the start (no wild knobs)
    # pattern search (the rasterised proxy is piecewise constant: gradient methods stall)
    q = np.zeros(9); best = float(np.sum(resid(q) ** 2)); step = 1.0
    while step > 0.06:
        moved = False
        for i in range(9):
            for sgn in (1, -1):
                t_ = q.copy(); t_[i] += sgn * step; c_ = float(np.sum(resid(t_) ** 2))
                if c_ < best - 1e-6:
                    q, best, moved = t_, c_, True
                    break
        if not moved:
            step *= 0.5

    class _r:
        x = q
    r_ = _r()
    class _R:
        x = p0 + r_.x * SC
    res = _R()
    o, top, bot, tilt, asp = pred(res.x)
    e = np.r_[top - T["top"], bot - T["bot"]]
    print("predicted: outline rms %.4f (tol 0.03)  tilt %.3f  aspect %.3f  h %.1f mm" % (np.sqrt(np.mean(e ** 2)), tilt, asp, o["h_mm"]))
    k = dict(json.load(open(sys.argv[2]))); k.update({n: round(float(v), 5) for n, v in zip(NAMES, res.x)})
    json.dump(k, open(out, "w"), indent=0)
    print({n: round(float(v), 5) for n, v in zip(NAMES, res.x)})


if __name__ == "__main__":
    main()
