"""Yes/no defect probe against a style reference (q32): which concrete statements about `image` are true?

    python typesafe_defects.py out.json IMG REF defects.json [--note "context for the judge"]

defects.json: {"id": "statement about `image` compared with `reference_image`", ...}. Each statement is asked as a
TypeSafe yes/no (noul) question twice (two requests, statement order reversed); the mean yes-probability is reported.
Use it after a 'culprit' answer to find WHAT about that element is off, then fix the highest one and re-ask.
"""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import ask, image_asset  # noqa: E402

MODEL = "jev-1.14.0"


def main():
    out, img, ref, dfile = sys.argv[1:5]
    defects = json.load(open(dfile))
    pi, pr = "img-" + uuid.uuid4().hex, "ref-" + uuid.uuid4().hex
    assets = {pi: image_asset(img), pr: image_asset(ref)}
    note = sys.argv[sys.argv.index("--note") + 1] if "--note" in sys.argv else (
        "image is a render being fixed; reference_image is the style target (a different character from "
        "the same kind of game). Judge form and style, not identity, hair style or clothes.")
    state = {"image": pi, "reference_image": pr, "note": note}
    votes = {k: [] for k in defects}
    for order in (0, 1):
        items = list(defects.items())
        if order:
            items = items[::-1]
        qs = {k: {"type": "noul", "instructions": t} for k, t in items}
        r = ask(MODEL, state, qs, assets, True, False)["answers"]
        for k in defects:
            votes[k].append(float(r[k]["noul"]))
    res = {k: round(sum(v) / 2, 3) for k, v in votes.items()}
    json.dump({"image": img, "ref": ref, "yes": res}, open(out, "w"), indent=1)
    for k, v in sorted(res.items(), key=lambda kv: -kv[1]):
        print("%.2f %s" % (v, k))


if __name__ == "__main__":
    main()
