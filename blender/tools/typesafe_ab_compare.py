"""A/B regression check with pictures (jev-1.14): did a change make the render better or worse?

    python typesafe_ab_compare.py out.json A=a.png B=b.png REF=reference.png [--aspects head_shape,eyes,...]

Sammy (2026-10-15): "the head looks worse now" - the reference-match judge asks "what is off", not "is this version
better than the last one", so a round can drift away from what looked right. This asks TypeSafe, per aspect, which
of two renders of the same head (same camera, same lighting) looks more like a well-made adult anime head in the
reference's style. Each question is asked twice with the two pictures swapped (slot `first_image` / `second_image`)
and the options reversed; a winner counts only when both orders pick the same picture. Yes/no questions about defects
(dent, lumps, odd lines) are asked about each picture on its own.
Output per aspect: {"winner": "A" | "B" | "tie" | "disagree", "orders": [..]}.
"""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import ask, image_asset  # noqa: E402

MODEL = "jev-1.14.0"
ASPECTS = {
    "overall": "the whole head and face: which looks more like a polished, appealing adult anime character head in the "
               "style of `reference_image`",
    "head_shape": "the head and face silhouette (skull, cheeks, jaw, chin): which reads as a natural, convex, adult anime "
                  "head like the reference, without dents, flat spots or a pushed-in look",
    "eyes": "the eyes (opening shape, whites, iris, pupil, highlight, lid line): which looks more like the reference's eyes",
    "brows": "the eyebrows (shape, angle, thickness, colour): which looks more like natural anime brows in the "
             "reference's style",
    "nose_mouth": "the nose and mouth marks and the shading under them: which looks cleaner and closer to the reference",
    "jaw_chin": "the jaw and chin: which has a jaw and chin shape closer to the reference's adult male face",
    "ears": "the ears: which looks more natural for this head in the reference's style",
    "eye_layout": "where the two eyes sit in this turned view: the spacing between them, how much skin shows between "
                  "the far eye and the nose line and between the far eye and the face edge, and the far eye's size "
                  "against the near eye: which matches `reference_image` more closely",
    "ear_shape": "the ear's outline, rim, inner shapes and how it sits on the head: which looks more like the ear in "
                 "`reference_image`",
    "expression": "how clearly and appealingly the face shows the intended expression in the reference style (brows, "
                  "eyes and mouth working together)",
    "clean": "drawing quality: which has fewer stray lines, broken outlines, odd shadow shapes or artifacts",
}
DEFECTS = {
    "dented": "Does the face in this picture look dented or pushed in anywhere (beside the eyes, cheeks, temples)?",
    "artifacts": "Does this picture show stray lines, broken outlines or odd shadow patches on the face that would "
                 "not be drawn on a finished anime character?",
    "adult": "Does this face read as an adult (not a child)?",
}


def main():
    out = sys.argv[1]
    kv = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a and not a.startswith("--"))
    arg = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
    aspects = arg("--aspects").split(",") if arg("--aspects") else list(ASPECTS)
    pa, pb, pr = "a-" + uuid.uuid4().hex, "b-" + uuid.uuid4().hex, "ref-" + uuid.uuid4().hex
    assets = {pa: image_asset(kv["A"]), pb: image_asset(kv["B"]), pr: image_asset(kv["REF"])}
    picks = {k: [] for k in aspects}
    defects = {}
    for order in (0, 1):
        first, second = (pa, pb) if order == 0 else (pb, pa)
        state = {"first_image": first, "second_image": second, "reference_image": pr,
                 "note": "first_image and second_image are two renders of the same 3D head with the same camera and "
                         "lighting; only the modelling/painting differs. reference_image is the target style (it may "
                         "be a different character, may have hair and an open mouth): compare style and form, not "
                         "identity, hair or expression."}
        qs = {}
        for k in aspects:
            crit = {"first": "`first_image` is better for this aspect.", "second": "`second_image` is better for this aspect.",
                    "same": "Neither: they look about the same for this aspect."}
            opts = list(crit.items())
            if order:
                opts = opts[::-1]
            qs["ab_" + k] = {"type": "choice", "instructions": "Compare %s." % ASPECTS[k], "criteria": dict(opts)}
        for d, txt in DEFECTS.items():
            qs["first_" + d] = {"type": "noul", "instructions": "Look only at `first_image`. " + txt}
            qs["second_" + d] = {"type": "noul", "instructions": "Look only at `second_image`. " + txt}
        r = ask(MODEL, state, qs, assets, True, False)["answers"]
        for k in aspects:
            c = r["ab_" + k].get("choice")
            picks[k].append({"first": "A" if order == 0 else "B", "second": "B" if order == 0 else "A"}.get(c, "tie"))
        for d in DEFECTS:
            for slot, lab in (("first", "A" if order == 0 else "B"), ("second", "B" if order == 0 else "A")):
                defects.setdefault(lab + "_" + d, []).append(float(r[slot + "_" + d]["noul"]))
    res = {"A": kv["A"], "B": kv["B"], "REF": kv["REF"], "aspects": {}, "defects": {}}
    for k, p in picks.items():
        res["aspects"][k] = {"winner": p[0] if p[0] == p[1] else "disagree", "orders": p}
    for k, v in defects.items():
        res["defects"][k] = round(sum(v) / len(v), 3)
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps({k: v["winner"] for k, v in res["aspects"].items()}))
    print(json.dumps(res["defects"]))


if __name__ == "__main__":
    main()
