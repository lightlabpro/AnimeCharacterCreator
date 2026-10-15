"""Reference-match judge: Claude looks and measures, TypeSafe decides (yes = good).

    python typesafe_visual_judge.py analysis.json corrections.json out.json [--exclude id1,id2]
        [--images ours.png,reference.png] [--model jev-1.14.0] [--long-context]

v2 (jev-1.14): TypeSafe can now see images ("danger zone" feature, header TypeSafe-Danger-Zone-Images). The words
stay the primary channel (models are weaker on images than on text, per TypeSafe), and the pictures are used to
CHECK the words, so Claude no longer grades its own descriptions:
1. Claude renders ours at the reference's framing, builds the board, measures, and writes analysis.json:
   {"region", "subject", "reference_style", "features": {name: {"reference": "...", "ours": "..."}}} - each side
   described on its own in the same concrete terms, measured numbers inside the sentences, no verdict words.
2. In one request (asked twice, with the menu in both orders) TypeSafe answers:
   - analysis_usable: are the descriptions concrete and comparable?
   - with --images: analysis_faithful (do the OURS descriptions match the `ours_image`, the REFERENCE descriptions the
     `reference_image`?) and per feature look_<f> (in the pictures alone, does that feature look the same?)
   - same_<f>: from the words, does the feature look the same? (yes = good)
   - first_fix: one correction from the menu, or "none".
   Both requests answer every yes/no question; the two answers are averaged.
3. Verdicts: a feature "matches" only when the words say so and (with images) the pictures do not contradict them;
   words and pictures disagreeing strongly -> "needs a human"; anything under 0.4 confidence -> "needs a human".
   first_fix.apply is set only when both menu orders (or the tie-break) agree, the analysis is usable and, with
   images, not contradicted by the pictures. Deterministic checks (dataset bands, topology, skew) stay authoritative.
"""
import base64
import io
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.14.0"          # v2: pinned (1.13.0 is still served; the aliases move)
FALLBACK = "jev-1.13.0"
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


def post(payload, images=False, long_context=False):
    h = {"content-type": "application/json", "authorization": "Bearer " + key()}
    if images:
        h["TypeSafe-Danger-Zone-Images"] = "true"
    if long_context:
        h["TypeSafe-Danger-Zone-Long-Context"] = "true"
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers=h)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError("TypeSafe HTTP %d: %s" % (e.code, e.read().decode("utf-8", "replace")[:800]))


def image_asset(path, max_side=1568, min_side=280):
    """PNG asset inside TypeSafe's limits. The docs say each side 256..1568 px, but the API (probed 2026-10-14) rejects
    sides under 280 px, so 280 is the floor; 78,400..2,458,624 px in total. Larger boards are
    scaled down, small crops scaled up."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    s = min(1.0, max_side / max(w, h))
    if min(w, h) * s < min_side:
        s = min_side / min(w, h)
    if (w * s) * (h * s) < 80000:                     # also at least 78,400 pixels in total
        s = (80000 / (w * h)) ** 0.5
    if s != 1.0:
        im = im.resize((min(max_side, max(min_side, round(w * s))), min(max_side, max(min_side, round(h * s)))),
                       Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "PNG")
    return {"type": "image", "format": "png", "data_base64": base64.b64encode(buf.getvalue()).decode()}


def ask(model, state, questions, assets, images, long_context):
    p = {"model": model, "state": state, "questions": questions}
    if assets:
        p["assets"] = assets
    return post(p, images, long_context)


def main():
    an, menu, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
    arg = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
    model = arg("--model") or MODEL
    long_context = "--long-context" in sys.argv
    feats = an["features"]
    state = {
        "subject": an.get("subject", ""),
        "reference_style": an.get("reference_style", "Monster Hunter Stories 3 (MHS3) anime toon style"),
        "features": {k: {"reference": v["reference"], "ours": v["ours"]} for k, v in feats.items()},
    }
    assets = {}
    imgs = arg("--images")
    if imgs:
        ours_p, ref_p = imgs.split(",")
        po, pr = "ours-" + uuid.uuid4().hex, "ref-" + uuid.uuid4().hex
        assets = {po: image_asset(ours_p), pr: image_asset(ref_p)}
        state["ours_image"] = po
        state["reference_image"] = pr
    qs = {"analysis_usable": {"type": "noul", "instructions": (
        "Are the descriptions in `features` concrete, visual and comparable (each pair names the same properties: "
        "shape, relative size, colour, position or thickness), so that a modeler could act on the differences?")}}
    if imgs:
        qs["analysis_faithful"] = {"type": "noul", "instructions": (
            "Do the `ours` descriptions in `features` describe what `ours_image` shows, and the `reference` "
            "descriptions what `reference_image` shows (judge shapes, positions and colours; ignore exact numbers "
            "you cannot check)?")}
    for k in feats:
        qs["same_" + k] = {"type": "noul", "instructions": (
            "For the feature `%s`, do `features.%s.reference` and `features.%s.ours` describe the same look, so that a "
            "viewer would not notice a difference in that feature?" % (k, k, k))}
        if imgs:
            qs["look_" + k] = {"type": "noul", "instructions": (
                "Look only at the pictures. For the feature `%s` (what `features.%s` talks about), does it look the "
                "same in `ours_image` as in `reference_image`, so that a viewer would not notice a difference in that "
                "feature? The reference may be a different character: compare the style of the feature, not identity."
                % (k, k))}
    excl = set(arg("--exclude").split(",")) if arg("--exclude") else set()
    menu["corrections"] = [c for c in menu["corrections"] if c["id"] not in excl]
    fixes = {c["id"]: c["description"] for c in menu["corrections"]}
    fixes["none"] = "The two already match closely; nothing needs changing."
    answers = []
    used = model
    for order in (0, 1):
        opts = list(fixes.items())
        if order:
            opts = opts[::-1]
        q = dict(qs, first_fix={"type": "choice", "instructions": (
            "Using `features`%s, which single correction would most reduce the visible difference between OURS and the "
            "REFERENCE? Pick the correction that fixes the biggest difference first." %
            (" and the pictures `ours_image` / `reference_image`" if imgs else "")), "criteria": dict(opts)})
        try:
            r = ask(used, state, q, assets, bool(imgs), long_context)
        except RuntimeError as e:
            if used != FALLBACK and not imgs and "model" in str(e).lower():
                used = FALLBACK
                r = ask(used, state, q, assets, False, long_context)
            else:
                raise
        answers.append(r["answers"])
    a0, a1 = answers
    res = {"region": an.get("region"), "subject": an.get("subject"), "model": used, "images": bool(imgs),
           "features": [], "analysis": None, "first_fix": None}

    def avg(name):
        return (a0[name]["noul"] + a1[name]["noul"]) / 2

    p = avg("analysis_usable"); c = abs(2 * p - 1)
    verdict = "needs a human" if c < MIN_CONF else ("usable" if p >= 0.6 else "rewrite the analysis")
    res["analysis"] = {"p_yes": round(p, 3), "confidence": round(c, 3), "verdict": verdict}
    if imgs:
        pf = avg("analysis_faithful")
        res["analysis"]["faithful_p"] = round(pf, 3)
        if pf < 0.3 and verdict == "usable":
            res["analysis"]["verdict"] = verdict = "rewrite the analysis (pictures disagree)"
    for k in feats:
        p = avg("same_" + k); c = abs(2 * p - 1)
        row = {"feature": k, "p_same": round(p, 3), "confidence": round(c, 3)}
        v = "needs a human" if c < MIN_CONF else ("matches" if p >= 0.6 else "off")
        if imgs:
            pl = avg("look_" + k); row["p_look"] = round(pl, 3)
            if v == "matches" and pl < 0.3:
                v = "needs a human"          # words say same, pictures say different
            elif v == "off" and pl > 0.85:
                v = "needs a human"          # pictures say same, words say different
        row["verdict"] = v
        res["features"].append(row)
    res["features"].sort(key=lambda r: r["p_same"])
    f0, f1 = a0["first_fix"].get("choice"), a1["first_fix"].get("choice")
    tie = None
    if f0 != f1 and f0 and f1:
        cand = {k: fixes[k] for k in (f0, f1, "none") if k in fixes}
        picks = []
        for order in (0, 1):
            opts = list(cand.items())
            if order:
                opts = opts[::-1]
            q = {"tie_break": {"type": "choice", "instructions": (
                "Using `features`%s, which of these corrections would most reduce the visible difference between OURS "
                "and the REFERENCE?" % (" and the pictures" if imgs else "")), "criteria": dict(opts)}}
            picks.append(ask(used, state, q, assets, bool(imgs), long_context)["answers"]["tie_break"].get("choice"))
        tie = {"candidates": [f0, f1], "order_a": picks[0], "order_b": picks[1]}
        if picks[0] == picks[1]:
            f0 = f1 = picks[0]
    sel = next((c for c in menu["corrections"] if c["id"] == f0), None)
    res["first_fix"] = {"order_a": f0, "order_b": f1, "agree": f0 == f1, "tie_break": tie,
                        "apply": f0 if (f0 == f1 and verdict == "usable") else None,
                        "setting": sel.get("setting") if sel and f0 == f1 else None}
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps({"model": used, "analysis": res["analysis"], "first_fix": res["first_fix"]}))
    print([(r["feature"], r["p_same"], r.get("p_look"), r["verdict"]) for r in res["features"]])


if __name__ == "__main__":
    main()
