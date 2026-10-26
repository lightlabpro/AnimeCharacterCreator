"""Stage-1 gate of the parts workflow: is a Midjourney reference sheet usable for Hunyuan 3D, and does it read as MHS3?

    py -3 parts_ref_gate.py SHEET.png OUTDIR [--views front,front2,side,back] [--front 0] [--skip hair_anime]

1. Splits the sheet into views (column runs that differ from the border background) and writes view_<name>.png.
2. Runs ai-3d-pipeline/scripts/prepare_reference.py on each view (exit 0 required) -> prep_<name>.png for Hunyuan.
3. TypeSafe anime check (blender/tools/typesafe_anime_check.py, images on, both orders) on the front view and on the
   calibrated MHS3 face controls face_leia_front.png and face_eleanor_front.png, all next to leo_ref_front.png.
   The rulebook's calibration rule applies: every metric >= the weaker control - 0.05 (knowledge/mhs3_face_rules.json,
   typesafe.note). Metrics that do not apply to the part (--skip) are listed, not passed.
Writes OUTDIR/gate.json. Exit 0 pass, 12 fail, 13 unknown (TypeSafe or prep could not run), 2 usage.
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, "blender", "tools")) and os.path.dirname(REPO) != REPO:
    REPO = os.path.dirname(REPO)  # works from the skill folder or a copy in blender/tools (the PC sync path)
PREP = os.path.join(REPO, ".claude", "skills", "ai-3d-pipeline", "scripts", "prepare_reference.py")
ANIME = os.path.join(REPO, "blender", "tools", "typesafe_anime_check.py")
LEO = os.path.join(REPO, "docs", "qa", "head_v2", "judge", "leo_ref_front.png")
CONTROLS = [os.path.join(REPO, "docs", "reference", "mhs3", n) for n in ("face_leia_front.png", "face_eleanor_front.png")]
MARGIN = 0.05


def split_views(img, min_frac=0.06, tol=30.0):
    a = np.asarray(img.convert("RGB")).astype(float)
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(border, axis=0)
    fg = np.abs(a - bg).max(axis=2) > tol
    col = fg.mean(axis=0) > 0.01
    runs, start = [], None
    for x, v in enumerate(list(col) + [False]):
        if v and start is None:
            start = x
        elif not v and start is not None:
            if x - start >= min_frac * a.shape[1]:
                runs.append((start, x))
            start = None
    return runs


def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    sheet, out = sys.argv[1], sys.argv[2]
    arg = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
    names = arg("--views", "").split(",") if arg("--views") else None
    front = int(arg("--front", "0"))
    skip = [s for s in arg("--skip", "").split(",") if s]
    os.makedirs(out, exist_ok=True)
    img = Image.open(sheet)
    runs = split_views(img)
    names = names or ["v%d" % i for i in range(len(runs))]
    rep = {"sheet": sheet, "views": [], "verdict": None}
    if len(runs) != len(names):
        rep["verdict"] = "fail"; rep["why"] = "found %d views, expected %d" % (len(runs), len(names))
        json.dump(rep, open(os.path.join(out, "gate.json"), "w"), indent=1); print(rep["why"]); return 12
    ok = True
    for (x0, x1), n in zip(runs, names):
        pad = int(0.02 * img.width)
        v = img.crop((max(0, x0 - pad), 0, min(img.width, x1 + pad), img.height))
        vp = os.path.join(out, "view_%s.png" % n); v.save(vp)
        pp = os.path.join(out, "prep_%s.png" % n)
        r = subprocess.run([sys.executable, PREP, vp, "--out", pp, "--json", pp + ".json"], capture_output=True, text=True)
        rep["views"].append({"name": n, "cols": [x0, x1], "prep_rc": r.returncode, "prep_out": r.stdout.strip()[-300:]})
        ok &= r.returncode == 0
        print(n, x0, x1, "prep rc", r.returncode, r.stdout.strip()[-160:])
    fv = os.path.join(out, "view_%s.png" % names[front])
    aj = os.path.join(out, "anime.json")
    r = subprocess.run([sys.executable, ANIME, aj, fv] + CONTROLS + ["--ref", LEO], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(aj):
        rep["verdict"] = "unknown"; rep["why"] = "TypeSafe did not run: " + (r.stderr or r.stdout)[-400:]
        json.dump(rep, open(os.path.join(out, "gate.json"), "w"), indent=1); print(rep["why"]); return 13
    res = json.load(open(aj))
    cand = res[fv]; ctrl = [res[c] for c in CONTROLS]
    rows = {}
    for k, v in cand.items():
        if k == "culprit":
            continue
        floor = round(min(c[k] for c in ctrl) - MARGIN, 3)
        rows[k] = {"value": v, "floor": floor, "pass": None if k in skip else v >= floor}
        if k not in skip:
            ok &= v >= floor
    rep["typesafe"] = rows; rep["culprit"] = cand["culprit"]; rep["controls"] = {os.path.basename(c): res[c] for c in CONTROLS}
    rep["verdict"] = "pass" if ok else "fail"
    json.dump(rep, open(os.path.join(out, "gate.json"), "w"), indent=1)
    for k, r_ in rows.items():
        print("%-14s %.3f floor %.3f %s" % (k, r_["value"], r_["floor"], "skip" if r_["pass"] is None else ("ok" if r_["pass"] else "FAIL")))
    print("culprit", cand["culprit"], "VERDICT", rep["verdict"])
    return 0 if ok else 12


if __name__ == "__main__":
    sys.exit(main())
