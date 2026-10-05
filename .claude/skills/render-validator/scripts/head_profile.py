#!/usr/bin/env python3
"""Head silhouette profiles, normalised by head height, to compare a head against a reference head.

Why: a head can pass colour and shading checks and still be the wrong shape (egg skull, V jaw, long nose,
receding chin). Toon lighting then looks wrong, because the light/shadow shapes follow the form.
This measures the form. Silhouettes only: needs numpy + Pillow.

  head_profile.py measure --front f.png --side s.png --front-chin-y 365 --side-chin-y 362 [--facing left] [--out p.json]
  head_profile.py compare --ref ref.json --cand cand.json [--tol 0.04]

Chin y is the pixel row of the chin tip (read it off the image, or project the chin vertex from Blender).
Heights are fractions of head height H = (chin y - top of skull). Ears, hair and neck distort some rows,
which are flagged and ignored by `compare`.
"""
import argparse, importlib.util, json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("validate", os.path.join(HERE, "validate.py"))
V = importlib.util.module_from_spec(spec); spec.loader.exec_module(V)

FRACS = [round(0.05 * i, 2) for i in range(1, 20)] + [0.97]
SKULL_ROWS = [f for f in FRACS if f <= 0.35]      # width here is the cranium, ears not yet in play
JAW_ROWS = [f for f in FRACS if f >= 0.75]        # width here is jaw and chin
EAR_ROWS = [f for f in FRACS if 0.35 < f < 0.75]  # ears and cheeks mix in, informational only

def mask_of(path):
    m = V.foreground(Image.open(path))[1]
    return V.dilate(V.erode(m, 1), 1)

def longest_run(row):
    best = (0, 0, 0); start = None
    for x, v in enumerate(list(row) + [False]):
        if v and start is None: start = x
        if not v and start is not None:
            if x - start > best[0]: best = (x - start, start, x - 1)
            start = None
    return best

def front_profile(m, chin_y):
    ys, _ = np.where(m); top = int(ys.min()); H = chin_y - top
    out = {}
    for f in FRACS:
        y = min(max(int(top + f * H), 0), m.shape[0] - 1)
        w, l, r = longest_run(m[y]); out[str(f)] = round(w / H, 3)
    return {"H_px": int(H), "width": out}

def side_profile(m, chin_y, facing):
    if facing == "right": m = m[:, ::-1]
    ys, xs = np.where(m); top = int(ys.min()); H = chin_y - top
    rows = {}
    for f in FRACS:
        y = min(max(int(top + f * H), 0), m.shape[0] - 1)
        xx = np.where(m[y])[0]
        rows[f] = int(xx.min()) if xx.size else None
    nose = min(v for v in rows.values() if v is not None)         # most forward point of the face
    forward = {str(f): (round((v - nose) / H, 3) if v is not None else None) for f, v in rows.items()}
    ytop = int(top + 0.3 * H); xx = np.where(m[ytop])[0]
    return {"H_px": int(H), "behind_nose": forward, "skull_depth_at_0.3": round((xx.max() - xx.min() + 1) / H, 3)}

def cmd_measure(a):
    prof = {"note": "fractions of head height H, 0 = top of skull, 1 = chin tip", "facing": a.facing}
    if a.front:
        prof["front"] = front_profile(mask_of(a.front), a.front_chin_y)
    if a.side:
        prof["side"] = side_profile(mask_of(a.side), a.side_chin_y, a.facing)
    if a.out:
        with open(a.out, "w") as f: json.dump(prof, f, indent=2)
    print(json.dumps(prof, indent=1))
    if "front" in prof:
        w = prof["front"]["width"]
        print(f"\nfront: cranium width (rows 0.20-0.30) {np.mean([w['0.2'], w['0.25'], w['0.3']]):.2f}H, jaw width at 0.8 {w['0.8']:.2f}H, at 0.9 {w['0.9']:.2f}H")
    if "side" in prof:
        b = prof["side"]["behind_nose"]
        print(f"side: forehead(0.3) is {b['0.3']:.2f}H behind the nose, chin(0.95) {b.get('0.95', b['0.97']):.2f}H behind the nose, skull depth {prof['side']['skull_depth_at_0.3']:.2f}H")

def cmd_compare(a):
    with open(a.ref) as fr, open(a.cand) as fc: ref, cand = json.load(fr), json.load(fc)
    bad = []
    def check(name, r, c, tol):
        if r is None or c is None: return
        d = c - r; flag = abs(d) > tol
        print(f"  {name:<28} ref {r:6.3f}  cand {c:6.3f}  delta {d:+.3f}  {'<-- OUT' if flag else 'ok'}")
        if flag: bad.append((name, d))
    if "front" in ref and "front" in cand:
        print("FRONT width / H (ear rows ignored)")
        for f in SKULL_ROWS + JAW_ROWS:
            check(f"width@{f}", ref["front"]["width"][str(f)], cand["front"]["width"][str(f)], a.tol)
    if "side" in ref and "side" in cand:
        print("SIDE distance behind the nose tip / H")
        for f in [0.1, 0.2, 0.3, 0.4, 0.6, 0.8, 0.9]:
            check(f"behind_nose@{f}", ref["side"]["behind_nose"].get(str(f)), cand["side"]["behind_nose"].get(str(f)), a.tol)
        check("skull_depth@0.3", ref["side"]["skull_depth_at_0.3"], cand["side"]["skull_depth_at_0.3"], a.tol)
    hints = []
    for n, d in bad:
        if n.startswith("width@0.") and float(n.split("@")[1]) <= 0.35: hints.append("cranium too " + ("wide" if d > 0 else "narrow"))
        if n.startswith("width@") and float(n.split("@")[1]) >= 0.75: hints.append("jaw/chin too " + ("wide" if d > 0 else "narrow"))
        if n.startswith("behind_nose@0.3") or n.startswith("behind_nose@0.2"): hints.append("forehead " + ("recedes behind the reference" if d > 0 else "sits further forward than the reference"))
        if n.startswith("behind_nose@0.9"): hints.append("chin " + ("recedes (weak chin or nose too long)" if d > 0 else "protrudes"))
    print("\nHEAD_SHAPE_FAIL: " + "; ".join(sorted(set(hints))) if bad else "\nHEAD_SHAPE_OK")
    sys.exit(1 if bad else 0)

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    m = s.add_parser("measure"); m.add_argument("--front"); m.add_argument("--side")
    m.add_argument("--front-chin-y", type=int); m.add_argument("--side-chin-y", type=int)
    m.add_argument("--facing", default="left", choices=["left", "right"]); m.add_argument("--out")
    c = s.add_parser("compare"); c.add_argument("--ref", required=True); c.add_argument("--cand", required=True); c.add_argument("--tol", type=float, default=0.04)
    a = p.parse_args()
    if a.cmd == "measure" and ((a.front and a.front_chin_y is None) or (a.side and a.side_chin_y is None)):
        sys.exit("give --front-chin-y / --side-chin-y (pixel row of the chin tip)")
    {"measure": cmd_measure, "compare": cmd_compare}[a.cmd](a)

if __name__ == "__main__":
    main()
