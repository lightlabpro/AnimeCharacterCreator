"""Strict regression gate v2 (q36c, Sammy: "make the validations even more strict and robust").

    py -3 mhs3_strict_gate.py OUT.json --cand RENDERS/m50_o --base RENDERS/m26_s,RENDERS/m48_1_o [--reps 3]
        [--views front,34,side,y70,eye_close,prof_close] [--sanity]

A candidate is judged with pictures by TypeSafe against EVERY baseline given (the version Sammy accepted and the best
version so far), on six renders, three times each (every typesafe_ab_compare call already asks both picture orders),
plus repeated yes-probability checks against three different official MHS3 characters:

1. A/B (per baseline, per view, `reps` runs; a run's winner counts only when both orders agree):
   - FAIL if `overall` or `head_shape` goes to the baseline in ANY run of ANY view (zero tolerance);
   - FAIL if `eyes`, `nose_mouth`, `jaw_chin`, `face_shading` or `clean` goes to the baseline in a majority of runs;
   - a view is WON when `overall` goes to the candidate in a majority of runs.
   PASS needs no fail and at least 2 views won against every baseline.
2. Anime check (typesafe_anime_check.py) on the front renders, `reps` runs x 3 references (Leo, Leia, Eleanor):
   FAIL if the candidate's mean drops below the baseline's mean for mhs3, eyes_anime, face_anime, shading_anime or
   polished by more than one standard error of the difference, and mhs3 must improve by > 2 standard errors over
   the best baseline (otherwise UNDECIDED - not a pass).
3. Defects (typesafe_defects.py, defects_vroid_mhs3.json, front, 2 runs): FAIL if a 'bad' statement rises or a 'good'
   statement falls by more than 0.05 against any baseline.
--sanity judges the first baseline against itself: the gate must find no winner (a check of the judge's noise; its
false-win rate is written to the report and must be 0 for the gate to be trusted).
Exit 0 PASS, 12 FAIL, 13 UNDECIDED.
"""
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
BAD = ("vroid_look", "too_anime", "eyes_vroid", "artifacts")
GOOD = ("eyes_mhs3", "brows_mhs3", "nose_mhs3", "mouth_mhs3", "face_adult", "skin_mhs3")
ANIME = ("mhs3", "eyes_anime", "face_anime", "shading_anime", "polished")
STRICT0 = ("overall", "head_shape")
MAJ = ("eyes", "nose_mouth", "jaw_chin", "face_shading", "clean", "hair")   # q37: hair


def run(args):
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("%s failed: %s" % (os.path.basename(args[0]), p.stderr[-800:]))
    return p


def mean_se(v):
    m = sum(v) / len(v)
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / max(len(v) - 1, 1))
    return m, sd / math.sqrt(len(v))


def main():
    out = sys.argv[1]
    arg = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
    cand = arg("--cand"); bases = arg("--base").split(","); reps = int(arg("--reps", "3"))
    views = arg("--views", "front,34,side,y70,eye_close,prof_close").split(",")
    repo = arg("--repo", os.path.abspath(os.path.join(HERE, "..", "..")))
    ref = lambda *p: os.path.join(repo, *p)
    leo = ref("docs", "qa", "head_v2", "judge", "leo_ref_front.png")
    prof = ref("docs", "reference", "mhs3", "profile", "face_profile_04.png")
    refs_front = [leo, ref("docs", "reference", "mhs3", "face_leia_front.png"),
                  ref("docs", "reference", "mhs3", "face_eleanor_front.png")]
    vref = {"front": leo, "34": leo, "eye_close": leo, "side": prof, "y70": prof, "prof_close": prof}
    if "--sanity" in sys.argv:
        cand = bases[0]; bases = bases[:1]
    wd = os.path.splitext(out)[0] + "_work"; os.makedirs(wd, exist_ok=True)
    # q36c pipeline-drift check: the stored baseline must equal a fresh render of the same model made now with the
    # same spec (the m26_s baseline used all morning had been rendered with a different shading - every side-view
    # verdict against it was invalid). --base-fresh PREFIX (fresh render of bases[0]).
    drift = {}
    if arg("--base-fresh"):
        import numpy as np
        from PIL import Image
        for v in views:
            a = np.asarray(Image.open("%s_%s.png" % (bases[0], v)).convert("RGBA")).astype(float)
            b = np.asarray(Image.open("%s_%s.png" % (arg("--base-fresh"), v)).convert("RGBA")).astype(float)
            drift[v] = round(float(np.abs(a - b).mean()), 3)
        if max(drift.values()) > 1.0:
            json.dump({"verdict": "REFUSED", "why": "baseline render drifted from the current pipeline", "drift": drift},
                      open(out, "w"), indent=1)
            print("REFUSED: baseline drift", drift); sys.exit(13)
    if arg("--cand-fresh"):                    # the candidate too: two renders in this session must match
        import numpy as np
        from PIL import Image
        for v in views:
            a = np.asarray(Image.open("%s_%s.png" % (cand, v)).convert("RGBA")).astype(float)
            b = np.asarray(Image.open("%s_%s.png" % (arg("--cand-fresh"), v)).convert("RGBA")).astype(float)
            drift["cand_" + v] = round(float(np.abs(a - b).mean()), 3)
        if max(v_ for k_, v_ in drift.items() if k_.startswith("cand_")) > 1.0:
            json.dump({"verdict": "REFUSED", "why": "candidate render not reproducible", "drift": drift}, open(out, "w"), indent=1)
            print("REFUSED: candidate drift", drift); sys.exit(13)
    elif "--sanity" not in sys.argv and "--screen" not in sys.argv:
        print("REFUSED: give --cand-fresh (a second render of the candidate made now)"); sys.exit(13)
    if "--sanity" not in sys.argv and "--screen" not in sys.argv and not arg("--base-fresh"):
        print("REFUSED: give --base-fresh (a fresh render of the baseline) - a stale baseline invalidates the A/B")
        sys.exit(13)
    # q36c spec check: every render's sidecar (<prefix>_spec.json, written by vroid_toon.vt_go2) must carry the same
    # spec and vroid_toon.py hash, equal to the rulebook's locked shader spec
    specs = {}
    for p_ in [cand] + bases + [x for x in (arg("--base-fresh"), arg("--cand-fresh")) if x]:
        f_ = p_ + "_spec.json"
        if not os.path.exists(f_):
            if "--sanity" in sys.argv or "--screen" in sys.argv:
                continue
            print("REFUSED: no render spec sidecar for", p_); sys.exit(13)
        specs[os.path.basename(p_)] = json.load(open(f_))
    if specs:
        rules = json.load(open(os.path.join(repo, "knowledge", "mhs3_face_rules.json")))["shader"]["spec"]
        want = {"light": rules["light"], "skin_shadow": rules["skin_shadow_tint_linear"], "skin_deep": rules["skin_deep"],
                "cast_shadows": rules["cast_shadows"], "ramp": rules["ramp"]}
        bad = []
        for n_, sp in specs.items():
            for k_, v_ in want.items():
                got = sp["spec"].get(k_)
                if (list(got) if isinstance(got, (list, tuple)) else got) != v_:
                    bad.append("%s %s=%s (locked %s)" % (n_, k_, got, v_))
        shas = {sp.get("vroid_toon_sha1") for sp in specs.values()}
        if len(shas) > 1:
            bad.append("renders made with different vroid_toon.py versions: %s" % shas)
        if bad:
            json.dump({"verdict": "REFUSED", "why": "render spec mismatch", "bad": bad}, open(out, "w"), indent=1)
            print("REFUSED: render spec mismatch", bad); sys.exit(13)
    rep = {"cand": cand, "bases": bases, "reps": reps, "views": views, "ab": {}, "anime": {}, "defects": {},
           "fails": [], "notes": [], "drift": drift}

    jobs = []
    for b in bases:
        for v in views:
            for r in range(reps):
                o = os.path.join(wd, "ab_%s_%s_%d.json" % (os.path.basename(b), v, r))
                jobs.append((b, v, r, o, [os.path.join(HERE, "typesafe_ab_compare.py"), o, "A=%s_%s.png" % (b, v),
                                          "B=%s_%s.png" % (cand, v), "REF=" + vref[v]]))
    screen = "--screen" in sys.argv          # A/B only, for diagnosis - never a PASS
    for b in ([] if screen else [cand] + bases):
        for i, rf in enumerate(refs_front):
            for r in range(reps):
                o = os.path.join(wd, "anime_%s_%d_%d.json" % (os.path.basename(b), i, r))
                jobs.append(("anime", b, (i, r), o, [os.path.join(HERE, "typesafe_anime_check.py"), o,
                                                       b + "_front.png", "--ref", rf]))
        for r in range(2):
            o = os.path.join(wd, "def_%s_%d.json" % (os.path.basename(b), r))
            jobs.append(("def", b, r, o, [os.path.join(HERE, "typesafe_defects.py"), o, b + "_front.png", leo,
                                          os.path.join(HERE, "visual_corrections", "defects_vroid_mhs3.json")]))
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(lambda j: run(j[4]), jobs))

    # 1. A/B
    for b in bases:
        bn = os.path.basename(b); rep["ab"][bn] = {}
        won = 0
        for v in views:
            tally = {}
            for r in range(reps):
                d = json.load(open(os.path.join(wd, "ab_%s_%s_%d.json" % (bn, v, r))))
                for k, a in d["aspects"].items():
                    t = tally.setdefault(k, {"A": 0, "B": 0, "other": 0})
                    t[a["winner"] if a["winner"] in ("A", "B") else "other"] += 1
            rep["ab"][bn][v] = tally
            for k in STRICT0:
                if tally.get(k, {}).get("A", 0) > 0:
                    rep["fails"].append("vs %s %s %s: baseline preferred in %d/%d runs" % (bn, v, k, tally[k]["A"], reps))
            for k in MAJ:
                if tally.get(k, {}).get("A", 0) * 2 > reps:
                    rep["fails"].append("vs %s %s %s: baseline preferred in most runs" % (bn, v, k))
            if tally.get("overall", {}).get("B", 0) * 2 > reps:
                won += 1
        rep["ab"][bn]["views_won"] = won
        if won < 2:
            rep["notes"].append("vs %s: only %d views won (need 2)" % (bn, won))
    if screen:
        rep["verdict"] = "SCREEN-FAIL" if rep["fails"] else "SCREEN-OK"
        json.dump(rep, open(out, "w"), indent=1); print(json.dumps({k: rep[k] for k in ("verdict", "fails", "notes")}, indent=1))
        sys.exit(13)
    # 2. anime check
    vals = {}
    for b in [cand] + bases:
        bn = os.path.basename(b); vals[bn] = {k: [] for k in ANIME}
        for i in range(len(refs_front)):
            for r in range(reps):
                d = json.load(open(os.path.join(wd, "anime_%s_%d_%d.json" % (bn, i, r))))
                row = next(iter(d.values()))
                for k in ANIME:
                    vals[bn][k].append(float(row[k]))
    cn = os.path.basename(cand); undecided = False
    for k in ANIME:
        cm, cse = mean_se(vals[cn][k]); rep["anime"][k] = {cn: [round(cm, 3), round(cse, 3)]}
        best = None
        for b in bases:
            bn = os.path.basename(b); bm, bse = mean_se(vals[bn][k]); rep["anime"][k][bn] = [round(bm, 3), round(bse, 3)]
            sed = math.sqrt(cse ** 2 + bse ** 2)
            if cm < bm - sed:
                rep["fails"].append("%s: %.3f vs %s %.3f (drop > 1 SE)" % (k, cm, bn, bm))
            if k == "mhs3":
                best = max(best or -1, bm)
                if cm - bm <= 2 * sed:
                    undecided = True; rep["notes"].append("mhs3 not > 2 SE above %s (%.3f vs %.3f)" % (bn, cm, bm))
    # 3. defects
    dv = {}
    for b in [cand] + bases:
        bn = os.path.basename(b); acc = {}
        for r in range(2):
            for k, v in json.load(open(os.path.join(wd, "def_%s_%d.json" % (bn, r))))["yes"].items():
                acc.setdefault(k, []).append(v)
        dv[bn] = {k: sum(v) / len(v) for k, v in acc.items()}
    rep["defects"] = {k: {bn: round(dv[bn].get(k, float("nan")), 3) for bn in dv} for k in BAD + GOOD}
    for b in bases:
        bn = os.path.basename(b)
        for k in BAD:
            if dv[cn][k] > dv[bn][k] + 0.05:
                rep["fails"].append("defect %s rose %.2f -> %.2f vs %s" % (k, dv[bn][k], dv[cn][k], bn))
        for k in GOOD:
            if dv[cn][k] < dv[bn][k] - 0.05:
                rep["fails"].append("%s fell %.2f -> %.2f vs %s" % (k, dv[bn][k], dv[cn][k], bn))
    if "--sanity" in sys.argv:
        wins = sum(t.get("overall", {}).get("B", 0) + t.get("overall", {}).get("A", 0)
                   for v, t in rep["ab"][os.path.basename(bases[0])].items() if isinstance(t, dict))
        rep["sanity_false_wins"] = wins
        rep["verdict"] = "SANITY-OK" if wins == 0 else "SANITY-NOISY"
    else:
        won_all = all(rep["ab"][os.path.basename(b)]["views_won"] >= 2 for b in bases)
        rep["verdict"] = "FAIL" if rep["fails"] else ("PASS" if won_all and not undecided else "UNDECIDED")
    json.dump(rep, open(out, "w"), indent=1)
    print(json.dumps({k: rep[k] for k in ("verdict", "fails", "notes")}, indent=1))
    sys.exit({"PASS": 0, "SANITY-OK": 0, "FAIL": 12}.get(rep["verdict"], 13))


if __name__ == "__main__":
    main()
