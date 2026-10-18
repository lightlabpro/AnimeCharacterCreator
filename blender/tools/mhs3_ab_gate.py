"""Regression gate against the last version Sammy accepted (q36b). Runs on the PC (TypeSafe key there).

    py -3 mhs3_ab_gate.py OUT.json --base RENDERS/m26_s --cand RENDERS/m47_s [--repo REPO]

Sammy (2026-10-18): "you made it look worse... are you really validating or hallucinating?" - m46 passed every measured
rule while TypeSafe, asked afterwards, preferred the older m26 in the side and 3/4 views and scored it lower for MHS3
look and shading. So no version is shown until it beats the accepted one, judged with pictures:

- typesafe_ab_compare.py for the front, 3/4 and side renders (A = base, B = candidate; each aspect asked twice with
  the pictures swapped, a winner counts only when both orders agree);
- typesafe_anime_check.py on both front renders (yes-probabilities).

FAIL if, in any view, `overall` or `head_shape` goes to the base; or if the candidate's mhs3 / face_anime /
shading_anime / polished drops more than 0.02 below the base. PASS needs no loss and at least one `overall` win.
Otherwise UNDECIDED (draws only) - not a pass. Exit 0 pass, 12 fail, 13 undecided.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    out = sys.argv[1]
    arg = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
    base, cand = arg("--base"), arg("--cand")
    repo = arg("--repo", os.path.abspath(os.path.join(HERE, "..", "..")))
    leo = os.path.join(repo, "docs", "qa", "head_v2", "judge", "leo_ref_front.png")
    prof = os.path.join(repo, "docs", "reference", "mhs3", "profile", "face_profile_04.png")
    wd = os.path.splitext(out)[0] + "_work"; os.makedirs(wd, exist_ok=True)
    rep = {"base": base, "cand": cand, "views": {}, "anime": {}, "fails": []}
    views = arg("--views", "front,34,side").split(",")         # screening may use one view; a PASS needs all three
    for view, ref in [(v, r) for v, r in (("front", leo), ("34", leo), ("side", prof)) if v in views]:
        o = os.path.join(wd, "ab_%s.json" % view)
        subprocess.run([sys.executable, os.path.join(HERE, "typesafe_ab_compare.py"), o, "A=%s_%s.png" % (base, view),
                        "B=%s_%s.png" % (cand, view), "REF=" + ref], check=True, capture_output=True, text=True)
        d = json.load(open(o)); w = {k: v["winner"] for k, v in d["aspects"].items()}
        rep["views"][view] = {k: w.get(k) for k in ("overall", "head_shape", "eyes", "nose_mouth", "jaw_chin",
                                                     "face_shading", "clean") if k in w}
        for k in ("overall", "head_shape"):
            if w.get(k) == "A":
                rep["fails"].append("%s %s: base preferred" % (view, k))
    if "--no-anime" in sys.argv:
        rep["verdict"] = "SCREEN-FAIL" if rep["fails"] else "SCREEN-OK"
        json.dump(rep, open(out, "w"), indent=1); print(json.dumps(rep, indent=1)); sys.exit(13)
    o = os.path.join(wd, "anime.json")
    subprocess.run([sys.executable, os.path.join(HERE, "typesafe_anime_check.py"), o, base + "_front.png",
                    cand + "_front.png", "--ref", leo], check=True, capture_output=True, text=True)
    a = json.load(open(o)); vb = a[base + "_front.png"]; vc = a[cand + "_front.png"]   # keyed by the path given
    for k in ("mhs3", "face_anime", "shading_anime", "polished"):
        rep["anime"][k] = {"base": vb[k], "cand": vc[k]}
        if vc[k] < vb[k] - 0.02:
            rep["fails"].append("%s dropped %.3f -> %.3f" % (k, vb[k], vc[k]))
    wins = sum(v.get("overall") == "B" for v in rep["views"].values())
    rep["verdict"] = "FAIL" if rep["fails"] else ("PASS" if wins >= 1 and len(views) == 3 else "UNDECIDED")
    json.dump(rep, open(out, "w"), indent=1)
    print(json.dumps(rep, indent=1))
    sys.exit({"PASS": 0, "FAIL": 12}.get(rep["verdict"], 13))


if __name__ == "__main__":
    main()
