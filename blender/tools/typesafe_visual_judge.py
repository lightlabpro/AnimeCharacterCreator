"""Reference-match judge: Claude looks, TypeSafe decides (words only, yes = good).

    python typesafe_visual_judge.py analysis.json corrections.json out.json [--exclude id1,id2]

Claude cannot be its own referee, and TypeSafe cannot see images. So the work is split:
1. Claude renders our model at the reference's framing and puts the two side by side, then writes analysis.json:
   for every feature of the region, one description of the REFERENCE and one of OURS, each written on its own
   (describe the reference first, then ours, in the same concrete terms: shape, size relative to the eye/head,
   colour, position, thickness). No verdicts, no "better/worse" words in the descriptions.
2. This script sends the descriptions to TypeSafe (jev-1.13.0) and asks, in one request:
   - analysis_usable: are the descriptions concrete and comparable? (no = Claude rewrites the analysis first)
   - one yes/no per feature: do the two descriptions describe the same look? (yes = good)
   - first_fix: which correction from the menu (corrections.json, each tied to a code setting) should be made first,
     with a "none" option, asked again with the options in reverse order.
3. Output: features ranked by how different TypeSafe judged them, the correction (only "agreed" when both option
   orders pick it), and anything under 0.4 confidence marked for a human. Deterministic checks (dataset bands etc.)
   stay authoritative: a correction is applied only if they still pass afterwards.
"""
import json
import os
import sys
import urllib.request

URL, MODEL = "https://api.typesafe.ai/v1/systemone", "jev-1.13.0"
MIN_CONF = 0.4


def key():
    k = os.environ.get("TYPESAFE_API_KEY")
    if not k and os.name == "nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
            k = winreg.QueryValueEx(h, "TYPESAFE_API_KEY")[0]
    if not k:
        raise SystemExit("TYPESAFE_API_KEY missing: no judgment faked.")
    return k


def post(payload):
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"content-type": "application/json", "authorization": "Bearer " + key()})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())


def main():
    an, menu, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
    feats = an["features"]
    state = {
        "subject": an.get("subject", ""),
        "reference_style": an.get("reference_style", "Monster Hunter Stories 3 (MHS3) anime toon style"),
        "features": {k: {"reference": v["reference"], "ours": v["ours"]} for k, v in feats.items()},
    }
    qs = {"analysis_usable": {"type": "noul", "instructions": (
        "Are the descriptions in `features` concrete, visual and comparable (each pair names the same properties: "
        "shape, relative size, colour, position or thickness), so that a modeler could act on the differences?")}}
    for k in feats:
        qs["same_" + k] = {"type": "noul", "instructions": (
            "For the feature `%s`, do `features.%s.reference` and `features.%s.ours` describe the same look, so that a "
            "viewer would not notice a difference in that feature?" % (k, k, k))}
    excl = set(sys.argv[sys.argv.index("--exclude") + 1].split(",")) if "--exclude" in sys.argv else set()
    menu["corrections"] = [c for c in menu["corrections"] if c["id"] not in excl]   # fixes that were tried and did not move
    fixes = {c["id"]: c["description"] for c in menu["corrections"]}
    fixes["none"] = "The two descriptions already match closely; nothing needs changing."
    answers = []
    for order in (0, 1):
        opts = list(fixes.items())
        if order:
            opts = opts[::-1]
        q = dict(qs, first_fix={"type": "choice", "instructions": (
            "Using `features`, which single correction would most reduce the visible difference between OURS and the "
            "REFERENCE? Pick the correction that fixes the biggest difference first."), "criteria": dict(opts)})
        answers.append(post({"model": MODEL, "state": state, "questions": q})["answers"])
    a0 = answers[0]
    res = {"region": an.get("region"), "subject": an.get("subject"), "features": [], "analysis": None, "first_fix": None}
    p = a0["analysis_usable"]["noul"]; c = abs(2 * p - 1)
    res["analysis"] = {"p_yes": round(p, 3), "confidence": round(c, 3),
                       "verdict": "needs a human" if c < MIN_CONF else ("usable" if p >= 0.6 else "rewrite the analysis")}
    for k in feats:
        p = a0["same_" + k]["noul"]; c = abs(2 * p - 1)
        res["features"].append({"feature": k, "p_same": round(p, 3), "confidence": round(c, 3),
                                "verdict": "needs a human" if c < MIN_CONF else ("matches" if p >= 0.6 else "off")})
    res["features"].sort(key=lambda r: r["p_same"])
    f0, f1 = answers[0]["first_fix"].get("choice"), answers[1]["first_fix"].get("choice")
    tie = None
    if f0 != f1 and f0 and f1:
        # tie-break: only the two candidates and "none", both orders; act only if they agree
        cand = {k: fixes[k] for k in (f0, f1, "none") if k in fixes}
        picks = []
        for order in (0, 1):
            opts = list(cand.items())
            if order:
                opts = opts[::-1]
            q = {"tie_break": {"type": "choice", "instructions": (
                "Using `features`, which of these corrections would most reduce the visible difference between OURS and "
                "the REFERENCE?"), "criteria": dict(opts)}}
            picks.append(post({"model": MODEL, "state": state, "questions": q})["answers"]["tie_break"].get("choice"))
        tie = {"candidates": [f0, f1], "order_a": picks[0], "order_b": picks[1]}
        if picks[0] == picks[1]:
            f0 = f1 = picks[0]
    sel = next((c for c in menu["corrections"] if c["id"] == f0), None)
    res["first_fix"] = {"order_a": f0, "order_b": f1, "agree": f0 == f1, "tie_break": tie,
                        "apply": f0 if (f0 == f1 and res["analysis"]["verdict"] == "usable") else None,
                        "setting": sel.get("setting") if sel and f0 == f1 else None}
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
