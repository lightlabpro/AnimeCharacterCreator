"""Compare hair tuning variants: export each, run the hair validators, ask the TypeSafe hair judge, rank.
   python tools/placeholders/tune_hair.py [adult|child]           (dev server on :5173, node tools/placeholders/export.mjs works)"""
import json, os, subprocess, sys
import numpy as np
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, ROOT)
from blender.validators import hair, hair_judge, placeholder, judge, measure

VARIANTS = {
    "A baseline": dict(widthScale=1.0, minThickRatio=0.0, taperScale=1.0, countScale=1.0, fringeLen=1.0),
    "B chunky":   dict(widthScale=1.6, minThickRatio=0.5, taperScale=0.6, countScale=0.8, fringeLen=0.6),
    "C chunkier": dict(widthScale=2.0, minThickRatio=0.55, taperScale=0.55, countScale=0.7, fringeLen=0.55),
    "D bold":     dict(widthScale=2.4, minThickRatio=0.6, taperScale=0.5, countScale=0.6, fringeLen=0.5),
    "E round":    dict(widthScale=1.9, minThickRatio=0.7, taperScale=0.7, countScale=0.7, fringeLen=0.55),
    "F heavy":    dict(widthScale=2.2, minThickRatio=0.7, taperScale=0.45, countScale=0.55, fringeLen=0.5),
}

def measure_variant(kind, tuning):
    path = f"/tmp/claude-0/hairvar-{kind}.json"
    subprocess.run(["node", os.path.join(ROOT, "tools/placeholders/export.mjs"), "/tmp/claude-0", kind, "--tag", "hairvar", "--hair", json.dumps(tuning)], check=True, capture_output=True)
    sc, extra = placeholder.load(f"/tmp/claude-0/placeholder-{kind}-hairvar.json")
    lm, _ = measure.landmarks(sc)
    bv = np.asarray(sc.body_verts, float)
    hv, hf = extra["hair"]
    hd = lm["Crown"][2] - lm["Chin"][2]
    s = hair.summarise(hair.clump_stats(hv, hf), hd)
    fit = hair.head_fit(hv, bv, extra["body_faces"], lm["Chin"][2], lm["Crown"][2])
    topo = {"summary": s, "fit": fit, "length_bucket": hair.length_bucket(float(hv[:, 2].min()), lm["Crown"][2], hd)}
    f = hair.findings(s, "hair") + hair.fit_findings(fit, "hair")
    passes = sum(1 for x in f if x.severity == "pass"); n = sum(1 for x in f if x.severity in ("pass", "warn", "fail"))
    ts = hair_judge.ask(topo, "v", "short layered with a swept fringe")
    q = [x for x in ts if x.check.endswith(".quality")]
    score = q[0].value if q and q[0].value is not None else None
    return s, fit, passes, n, score, ts

if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "adult"
    rows = []
    for name, t in VARIANTS.items():
        s, fit, passes, n, ts, _ = measure_variant(kind, t)
        comp = 0.5 * passes / n + (0.5 * ts / 4 if ts is not None else 0.25)
        rows.append((comp, name, s, passes, n, ts))
        print(f"{name:11} clumps {s['clump_count']:4.0f}  T/W {s['median_thick_over_width']:.2f}  width/head {s['median_width_over_head']:.2f}  tip/root {s['tip_over_root_median']:.2f}  validators {passes}/{n}  TypeSafe {'n/a' if ts is None else f'{ts:.2f}/4'}  -> {comp:.2f}")
    best = max(rows)
    print("best:", best[1], VARIANTS[best[1]])
