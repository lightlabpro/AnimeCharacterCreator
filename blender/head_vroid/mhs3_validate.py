"""Strict MHS3 validator for a head version (q36). Combines every check into one verdict:

  1. mesh rules   - mhs3_measure.py on the GLB / npz (profile, proportions; real vertices per part)
  2. render rules - blender/tools/mhs3_render_measure.py on the locked-spec front render (eyes, jaw widths, shader)
  3. TypeSafe     - JSON outputs of typesafe_defects.py / typesafe_anime_check.py (images on, both orders) per set
                    in knowledge/mhs3_face_rules.json "typesafe"
  4. regression   - against the last approved report (--prev): no rule may get worse by more than 0.25 tol

    python3 mhs3_validate.py OUT.json --mesh meas.json --render front.png [--ts DIR] [--prev approved.json]

--mesh takes the JSON mhs3_measure.py wrote. --ts DIR holds <set>.json files named after the rule sets
(defects_vroid_mhs3.json, defects_eyes.json, defects_profile.json, anime_check.json).
Exit 0 = every rule passes; 12 = a rule failed; 13 = something was not measured (missing TypeSafe = unknown, never a
pass). Prints a table, worst first. Skill: mhs3-master-loop.
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def render_metrics(png, rules=None):
    out = os.path.splitext(png)[0] + "_rm.json"
    subprocess.run([sys.executable, os.path.join(REPO, "blender", "tools", "mhs3_render_measure.py"), out, png],
                   check=True, capture_output=True)
    r = json.load(open(out))["render"]
    m = {}
    eyes = [e for e in (r.get("eye_l"), r.get("eye_r")) if e]
    if eyes:
        m["eye_w"] = float(np.mean([e["w"] for e in eyes])); m["eye_h"] = float(np.mean([e["h"] for e in eyes]))
        m["eye_aspect"] = m["eye_w"] / max(m["eye_h"], 1e-6)
        m["eye_white_frac"] = float(np.mean([e["white_frac"] for e in eyes]))
        for q in ("pupil_frac", "iris_lum", "white_warm", "lash_gap", "lash_th", "brow_gap", "brow_th"):
            v = [e[q] for e in eyes if e.get(q) is not None]
            if v:
                m[q] = float(np.mean(v))
    tpl = (rules or {}).get("eye_shape_template")
    if eyes and tpl:
        errs = []
        for e in eyes:
            for k_, t_ in (("shape_top", tpl["top"]), ("shape_bot", tpl["bot"])):
                errs += [(a_ - b_) for a_, b_ in zip(e.get(k_, []), t_) if a_ is not None]
        if errs:
            m["eye_shape_rms"] = float(np.sqrt(np.mean(np.square(errs))))
        m["corner_tilt"] = float(np.mean([e["corner_tilt"] for e in eyes]))
    if r.get("mouth"):
        m["mouth_w"] = r["mouth"]["w_D"]; m["mouth_y"] = r["mouth"]["y_D"]
    for k, v in r["widths_ipd"].items():
        if v is not None:
            m["w_%s" % k] = v
    for k, v in (r.get("widths_D") or {}).items():
        if v is not None:
            m["wD_%s" % k] = v
    if r.get("D_ipd"):
        m["D_ipd"] = r["D_ipd"]
    s = r.get("shading") or {}
    if s:
        m["shadow_ratio"] = s["shadow_ratio"]; m["shadow_warmth"] = s["shadow_warmth"]; m["deep_frac"] = s["deep_frac"]
        m["lit_r"], m["lit_g"], m["lit_b"] = s["lit_rgb"]
        m["shadow_area"] = s["shadow_area"]; m["terminator_soft"] = s["terminator_soft"]
    return m


def main():
    out = sys.argv[1]
    arg = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
    rules = json.load(open(arg("--rules") or os.path.join(REPO, "knowledge", "mhs3_face_rules.json")))
    vals = {}
    if arg("--mesh"):
        vals.update(json.load(open(arg("--mesh")))["metrics"])
    if arg("--render"):
        vals.update(render_metrics(arg("--render"), rules))
    rows = {}
    for rid, r in rules["rules"].items():
        v = vals.get(r["metric"])
        if v is None or (isinstance(v, float) and not np.isfinite(v)):
            rows[rid] = {"status": "unknown", "region": r["region"], "kind": r["kind"]}; continue
        e = abs(v - r["target"]) / r["tol"]
        adv = r.get("advisory", False)
        rows[rid] = {"status": ("pass" if e <= 1.0 else ("advisory" if adv else "FAIL")), "value": round(float(v), 4), "target": r["target"],
                     "tol": r["tol"], "err_tol": round(float(e), 2), "region": r["region"], "kind": r["kind"]}
    tsd = arg("--ts")
    for sname, sd in rules["typesafe"]["sets"].items():
        f = os.path.join(tsd, sname if sname.endswith(".json") else sname + ".json") if tsd else None
        data = None
        if f and os.path.exists(f):
            d = json.load(open(f))
            data = d.get("yes") if "yes" in d else (next(iter(d.values())) if d else None)
        for side, lim in (("max", sd.get("max", {})), ("min", sd.get("min", {}))):
            for k, t in lim.items():
                rid = "TS_%s_%s" % (sname.replace("defects_", "").replace(".json", ""), k)
                if data is None or k not in data:
                    rows[rid] = {"status": "unknown", "region": "typesafe", "kind": "typesafe"}; continue
                v = float(data[k]); ok = v <= t if side == "max" else v >= t
                rows[rid] = {"status": "pass" if ok else "FAIL", "value": round(v, 3), "target": ("<=" if side == "max" else ">=") + str(t),
                             "err_tol": round(max(0.0, (v - t) if side == "max" else (t - v)) / 0.05, 2), "region": "typesafe", "kind": "typesafe"}
    prev = arg("--prev")
    if prev and os.path.exists(prev):
        p = json.load(open(prev))["rows"]
        for rid, r in rows.items():
            if "err_tol" in r and rid in p and "err_tol" in p[rid] and r["err_tol"] > p[rid]["err_tol"] + 0.25:
                r["regressed_from"] = p[rid]["err_tol"]
                r["status"] = "FAIL"
    errs = [r["err_tol"] for rid, r in rows.items() if "err_tol" in r and r["status"] != "advisory"
            and not rules["rules"].get(rid, {}).get("advisory")]
    nfail = sum(r["status"] == "FAIL" for r in rows.values()); nunk = sum(r["status"] == "unknown" for r in rows.values())
    rms = float(np.sqrt(np.mean(np.square(errs)))) if errs else None
    verdict = "PASS" if nfail == 0 and nunk == 0 and rms is not None and rms <= rules["pass"]["rms_err_tol_max"] else (
        "FAIL" if nfail else "UNKNOWN")
    rep = {"verdict": verdict, "fails": nfail, "unknown": nunk, "rms_err_tol": round(rms, 3) if rms is not None else None,
           "worst_err_tol": max(errs) if errs else None, "rows": rows, "values": vals}
    json.dump(rep, open(out, "w"), indent=1)
    print("VERDICT %s  fails %d  unknown %d  rms %.2f  worst %.2f" % (verdict, nfail, nunk, rms or 0, max(errs) if errs else 0))
    for rid, r in sorted(rows.items(), key=lambda kv: -kv[1].get("err_tol", 99 if kv[1]["status"] == "unknown" else 0)):
        if r["status"] == "unknown":
            print("  ????  %-34s not measured" % rid)
        else:
            print("  %-5s %-34s %-9s target %-8s err %.2f%s" % (r["status"], rid, r["value"], r["target"], r["err_tol"],
                  "  (regressed from %.2f)" % r["regressed_from"] if "regressed_from" in r else ""))
    sys.exit(0 if verdict == "PASS" else (12 if nfail else 13))


if __name__ == "__main__":
    main()
