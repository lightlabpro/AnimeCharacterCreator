"""Face gate (q26): the standard check for every head / face element and expression, with TypeSafe looking at images.

    py -3 typesafe_face_gate.py RENDERS_DIR OUT.json --rules a.json,b.json,... --refs refs.json [--only eyes,mouth]
        [--prev PREV_RENDERS_DIR] [--min-rule-page 0.6]

Sammy (q26): "research the books about anime and manga ... all elements and expressions on the head and face. Validate
using typesafe image, compare with the mhs3 references and validate look with typesafe image. Make sure this process is
standard when generating the 3d model elements."

Three TypeSafe passes, all with pictures (jev-1.14 images feature); TypeSafe answers, Claude never grades itself:
  1. BOOK RULES - every rule from the anime/manga book reading (docs/reference/books/rules_*_face.json: id, page,
     element, rule, check, views) is asked against the render it applies to ("front", "34", "side",
     "expression:<name>" -> RENDERS_DIR/front.png, 34.png, side.png, expr_<name>.png): "does the render follow this?"
     Rules whose page check (typesafe_book_reader --only-rule-pages) scored below --min-rule-page are skipped
     (they are Claude readings the book page did not confirm) when a *_rules_ts.json score file is given in the rules
     entry as "rule_page_p".
  2. MHS3 LOOK - per element, the render and the matching MHS3 reference side by side (refs.json maps a view or
     expression name to reference images): "does this element look like the same art style as the reference?"
     plus one overall "same art style / same game" question per view.
  3. NO REGRESSION (with --prev) - per element, previous vs current render against the same reference
     ("which is closer to the reference, or a tie?"), asked in both orders.

Verdict per item: pass p >= 0.6, fail p <= 0.4, otherwise "uncertain" (never counted as a pass). The gate passes
only when no element has a failed rule or a failed MHS3-look question, and nothing regressed. Missing renders are
reported as "not measured" (never a pass). A missing key stops the run: no judgment is faked.
"""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import MODEL, ask, image_asset  # noqa: E402

ELEMENTS = ["head_shape", "face_by_type", "eyes", "brows", "nose", "mouth", "teeth_tongue", "ears", "jaw_chin_neck",
            "hair_framing", "face_shading"]
LOOK_ELEMENTS = {
    "head_shape": "the overall head and face outline (cranium, cheeks, jaw, chin)",
    "eyes": "the eyes (shape of the opening, lash line, iris size and colour bands, pupil, highlights)",
    "brows": "the eyebrows (thickness, length, angle, position above the eyes)",
    "nose": "the nose (how it is drawn: highlight, small shadow, line or none)",
    "mouth": "the mouth (line or opening shape, lips, teeth and tongue when open)",
    "ears": "the ears (size, position, inner forms)",
    "hair_framing": "how the hair frames the face (fringe, side hair, silhouette)",
    "face_shading": "the face shading (toon shadow shapes, edges, colours) and the outline",
}
PASS, FAIL = 0.6, 0.4
BATCH = 24


def verdict(p):
    return "pass" if p >= PASS else ("fail" if p <= FAIL else "uncertain")


def render_for(view, renders):
    name = {"front": "front.png", "34": "34.png", "side": "side.png"}.get(view)
    if view.startswith("expression:"):
        name = "expr_%s.png" % view.split(":", 1)[1]
    p = os.path.join(renders, name) if name else None
    return p if p and os.path.exists(p) else None


def load_rules(paths, min_page):
    rules = []
    for path in paths:
        for r in json.load(open(path)):
            if r.get("rule_page_p") is not None and r["rule_page_p"] < min_page:
                continue
            r["book"] = os.path.basename(path)
            rules.append(r)
    return rules


def pass_rules(rules, renders, only):
    """One request per (render, batch of <= BATCH rules)."""
    groups = {}
    out = []
    for r in rules:
        if only and r["element"] not in only and not (r["element"].startswith("expression") and "expressions" in only):
            continue
        views = r.get("views") or ["front"]
        img = None
        for v in views:
            img = render_for(v, renders)
            if img:
                break
        if not img:
            out.append({"id": r["id"], "element": r["element"], "verdict": "not measured", "views": views})
            continue
        groups.setdefault(img, []).append(r)
    for img, rs in groups.items():
        aid = "render-" + uuid.uuid4().hex
        assets = {aid: image_asset(img)}
        for s in range(0, len(rs), BATCH):
            chunk = rs[s:s + BATCH]
            state = {"render": aid, "subject": "a render of a 3D anime character head in a toon style (Monster "
                     "Hunter Stories 3 look); judge only what the picture shows"}
            qs = {r["id"]: {"type": "noul", "instructions": (
                "Look at the picture `render`. Anime/manga drawing rule from a book: \"%s\" Question: %s"
                % (r["rule"], r["check"]))} for r in chunk}
            ans = ask(MODEL, state, qs, assets, True, False)["answers"]
            for r in chunk:
                p = ans[r["id"]]["noul"]
                out.append({"id": r["id"], "element": r["element"], "book": r["book"], "page": r.get("page"),
                            "render": os.path.basename(img), "p_yes": round(p, 3), "verdict": verdict(p),
                            "rule": r["rule"]})
    return out


def pass_look(renders, refs, only):
    out = []
    for view, ref_list in refs.items():
        img = render_for(view, renders)
        if not img:
            out.append({"view": view, "verdict": "not measured"})
            continue
        for ref in ref_list:
            if not os.path.exists(ref):
                continue
            ao, ar = "ours-" + uuid.uuid4().hex, "ref-" + uuid.uuid4().hex
            assets = {ao: image_asset(img), ar: image_asset(ref)}
            state = {"ours_image": ao, "reference_image": ar, "reference_style": "Monster Hunter Stories 3 (MHS3) "
                     "official art / in-game render", "note": "The reference may be a different character: judge "
                     "the style of each element, not the identity."}
            els = {k: v for k, v in LOOK_ELEMENTS.items() if not only or k in only}
            if view.startswith("expression:"):
                els = {k: v for k, v in els.items() if k in ("eyes", "brows", "mouth", "face_shading")}
            qs = {"look_" + k: {"type": "noul", "instructions": (
                "Look at both pictures. Is %s in `ours_image` drawn in the same art style as in `reference_image`, so "
                "that it would not look out of place in that game?" % d)} for k, d in els.items()}
            qs["same_style"] = {"type": "noul", "instructions": (
                "Overall, does `ours_image` look like it belongs to the same game and art style as `reference_image` "
                "(an anime toon character render of that quality)?")}
            if view.startswith("expression:"):
                qs["same_expression"] = {"type": "noul", "instructions": (
                    "Does `ours_image` show the same emotion as `reference_image`, readable at a glance?")}
            ans = ask(MODEL, state, qs, assets, True, False)["answers"]
            for q in qs:
                p = ans[q]["noul"]
                out.append({"view": view, "ref": os.path.basename(ref), "question": q, "p_yes": round(p, 3),
                            "verdict": verdict(p)})
    return out


def pass_prev(renders, prev, refs, only):
    out = []
    for view, ref_list in refs.items():
        a, b = render_for(view, prev), render_for(view, renders)
        if not (a and b and ref_list and os.path.exists(ref_list[0])):
            continue
        votes = []
        for order in (0, 1):
            x, y = (a, b) if order == 0 else (b, a)
            ia, ib, ir = ("img-" + uuid.uuid4().hex for _ in range(3))
            assets = {ia: image_asset(x), ib: image_asset(y), ir: image_asset(ref_list[0])}
            state = {"first": ia, "second": ib, "reference_image": ir}
            qs = {"closer": {"type": "choice", "instructions": (
                "Which of `first` and `second` is closer to the art style of `reference_image` (an anime toon look), "
                "judging the face elements (eyes, brows, nose, mouth, outline, shading)?"),
                "criteria": {"first": "first is closer", "second": "second is closer", "tie": "no visible difference"}}}
            c = ask(MODEL, state, qs, assets, True, False)["answers"]["closer"].get("choice")
            votes.append({"first": "prev", "second": "current"}.get(c, "tie") if order == 0 else
                         {"first": "current", "second": "prev"}.get(c, "tie"))
        res = votes[0] if votes[0] == votes[1] else "disagree"
        out.append({"view": view, "votes": votes, "result": res})
    return out


def main():
    renders, out_path = sys.argv[1], sys.argv[2]
    arg = lambda n, d=None: (sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d)
    rules = load_rules([p for p in (arg("--rules", "") or "").split(",") if p], float(arg("--min-rule-page", 0.6)))
    refs = json.load(open(arg("--refs"))) if arg("--refs") else {}
    only = set(arg("--only").split(",")) if arg("--only") else set()
    rep = {"model": MODEL, "renders": renders, "rules": pass_rules(rules, renders, only),
           "look": pass_look(renders, refs, only)}
    if arg("--prev"):
        rep["no_regression"] = pass_prev(renders, arg("--prev"), refs, only)
    # summary per element
    summ = {}
    for r in rep["rules"]:
        e = r["element"]
        s = summ.setdefault(e, {"pass": 0, "fail": 0, "uncertain": 0, "not measured": 0, "failed_rules": []})
        s[r["verdict"]] += 1
        if r["verdict"] == "fail":
            s["failed_rules"].append(r["id"])
    look_fail = [x for x in rep["look"] if x.get("verdict") == "fail"]
    regress = [x for x in rep.get("no_regression", []) if x["result"] == "prev"]
    rep["summary"] = summ
    rep["gate"] = {"rule_failures": sum(s["fail"] for s in summ.values()), "look_failures": len(look_fail),
                   "regressions": len(regress),
                   "verdict": "pass" if not look_fail and not regress and all(s["fail"] == 0 for s in summ.values())
                   else "fail"}
    json.dump(rep, open(out_path, "w"), indent=1)
    print(json.dumps({"gate": rep["gate"], "summary": {k: {kk: vv for kk, vv in v.items() if kk != "failed_rules"}
                                                         for k, v in summ.items()},
                      "look_fail": [(x["view"], x["question"], x["p_yes"]) for x in look_fail],
                      "regressions": regress}, indent=1))


if __name__ == "__main__":
    main()
