"""Why does TypeSafe prefer one render? (q37) - after an A/B loss, ask which concrete differences make B worse.

    python typesafe_ab_culprit.py out.json A=base.png B=cand.png REF=reference.png items.json

items.json: {"id": "a property, phrased so it can be true of one picture more than the other", ...}, e.g.
"the hair has jagged, torn-looking clump tips". Each item is asked as a yes/no in both picture orders:
"Compared with <the other picture>, <this picture> shows this more: <item>". Reported per item:
B_worse = mean yes-probability that B shows it more than A, A_worse likewise; delta = B_worse - A_worse.
Sort by delta to find what to fix first. Diagnosis only - never a pass/fail by itself.
"""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import ask, image_asset  # noqa: E402

MODEL = "jev-1.14.0"


def main():
    out = sys.argv[1]
    kv = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a and not a.startswith("--"))
    items = json.load(open([a for a in sys.argv[2:] if a.endswith(".json")][-1]))
    pa, pb, pr = "a-" + uuid.uuid4().hex, "b-" + uuid.uuid4().hex, "ref-" + uuid.uuid4().hex
    assets = {pa: image_asset(kv["A"]), pb: image_asset(kv["B"]), pr: image_asset(kv["REF"])}
    votes = {k: {"A": [], "B": []} for k in items}
    for order in (0, 1):
        first, second = (pa, pb) if order == 0 else (pb, pa)
        lab = {"first": "A" if order == 0 else "B", "second": "B" if order == 0 else "A"}
        state = {"first_image": first, "second_image": second, "reference_image": pr,
                 "note": "first_image and second_image are two renders of the same 3D head, same camera and lighting; "
                         "reference_image is the target style (Monster Hunter Stories 3)."}
        qs = {}
        for k, t in items.items():
            qs["f_" + k] = {"type": "noul", "instructions": "Compared with `second_image`, does `first_image` show this "
                                                            "more: %s?" % t}
            qs["s_" + k] = {"type": "noul", "instructions": "Compared with `first_image`, does `second_image` show this "
                                                            "more: %s?" % t}
        r = ask(MODEL, state, qs, assets, True, False)["answers"]
        for k in items:
            votes[k][lab["first"]].append(float(r["f_" + k]["noul"]))
            votes[k][lab["second"]].append(float(r["s_" + k]["noul"]))
    res = {}
    for k, v in votes.items():
        a, b = sum(v["A"]) / len(v["A"]), sum(v["B"]) / len(v["B"])
        res[k] = {"A_worse": round(a, 3), "B_worse": round(b, 3), "delta": round(b - a, 3)}
    json.dump({"A": kv["A"], "B": kv["B"], "items": res}, open(out, "w"), indent=1)
    for k, v in sorted(res.items(), key=lambda kv_: -kv_[1]["delta"]):
        print("%+.2f  %s" % (v["delta"], k))


if __name__ == "__main__":
    main()
