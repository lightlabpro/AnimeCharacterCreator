"""Per-feature faithfulness check (jev-1.14 pictures): which descriptions does TypeSafe think the pictures contradict?

    python typesafe_faithful_check.py analysis.json ours.png reference.png out.json

typesafe_visual_judge.py asks one global analysis_faithful question; when it stays low ("rewrite the analysis
(pictures disagree)") this asks, per feature and per side, "does this sentence describe `ours_image` /
`reference_image`?" so the misleading sentence can be rewritten instead of guessed at. Yes = faithful.
"""
import json, os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import ask, image_asset  # noqa: E402

MODEL = "jev-1.14.0"


def main():
    an, ours, ref, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    a = json.load(open(an))
    po, pr = "img-" + uuid.uuid4().hex, "img-" + uuid.uuid4().hex
    state = {"ours_image": po, "reference_image": pr, "subject": a.get("subject", "")}
    qs = {}
    for f, d in a["features"].items():
        qs["ours_" + f] = {"type": "noul", "instructions": "Does this sentence correctly describe the %s in `ours_image`? \"%s\"" % (f.replace("_", " "), d["ours"])}
        qs["ref_" + f] = {"type": "noul", "instructions": "Does this sentence correctly describe the %s in `reference_image`? \"%s\"" % (f.replace("_", " "), d["reference"])}
    r = ask(MODEL, state, qs, {po: image_asset(ours), pr: image_asset(ref)}, True, False)["answers"]
    res = {k: round(float(v["noul"]), 3) for k, v in r.items()}
    json.dump(res, open(out, "w"), indent=1)
    for f in a["features"]:
        print("%-12s ours %.2f  ref %.2f" % (f, res["ours_" + f], res["ref_" + f]))


if __name__ == "__main__":
    main()
