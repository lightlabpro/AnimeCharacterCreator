"""Stage-2 gate of the parts workflow: does the Hunyuan model match its reference sheet, view by view?

    py -3 parts_gen_gate.py OUT.json --pair front RENDER.png SHEET_VIEW.png [--pair side ...] --control A.png B.png

For each pair TypeSafe (jev-1.14, images on, both orders) answers yes/no questions about `model_render` versus
`reference_view`. The control pair is two drawings of the same head from the same sheet (e.g. the sheet's two front
views): its scores are the ceiling, and each pair must score >= control - 0.05 on every question (the rulebook's
calibration rule; a question the control itself cannot pass is reported, not used). Exit 0 pass, 12 fail, 13 unknown.
"""
import json
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, "blender", "tools")) and os.path.dirname(REPO) != REPO:
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, "blender", "tools"))
from typesafe_visual_judge import ask, image_asset  # noqa: E402

MODEL = "jev-1.14.0"
MARGIN = 0.05
QS = {
    "same_head": "Do `model_render` and `reference_view` show the same character's head from the same direction (same "
                 "skull shape, face and proportions)?",
    "ears": "Are the ears in `model_render` the same size, shape and angle as the ears in `reference_view`?",
    "face": "Are the eyes, nose, mouth and jaw in `model_render` placed and proportioned like in `reference_view`?",
    "silhouette": "Does the outline of the head and neck in `model_render` match the outline in `reference_view`?",
    "clean": "Is `model_render` free of stray fragments, holes, lumps or other generation artifacts?",
}


def judge(a, b):
    pa, pb = "img-" + uuid.uuid4().hex, "img-" + uuid.uuid4().hex
    votes = {k: [] for k in QS}
    for order in (0, 1):
        state = {"model_render": pa, "reference_view": pb} if order == 0 else {"reference_view": pb, "model_render": pa}
        state["note"] = "model_render is a render of a 3D model; reference_view is the drawing it was generated from."
        r = ask(MODEL, state, {k: {"type": "noul", "instructions": t} for k, t in QS.items()},
                {pa: image_asset(a), pb: image_asset(b)}, True, False)["answers"]
        for k in QS:
            votes[k].append(float(r[k]["noul"]))
    return {k: round(sum(v) / 2, 3) for k, v in votes.items()}


def main():
    out = sys.argv[1]
    pairs, ctrl, i = [], None, 2
    while i < len(sys.argv):
        if sys.argv[i] == "--pair":
            pairs.append(sys.argv[i + 1:i + 4]); i += 4
        elif sys.argv[i] == "--control":
            ctrl = sys.argv[i + 1:i + 3]; i += 3
        else:
            print(__doc__); return 2
    if not pairs or not ctrl:
        print(__doc__); return 2
    try:
        c = judge(*ctrl)
        res = {name: judge(r, s) for name, r, s in pairs}
    except SystemExit as e:
        json.dump({"verdict": "unknown", "why": str(e)}, open(out, "w")); print("UNKNOWN", e); return 13
    ok, rows = True, {}
    for name in res:
        for k, v in res[name].items():
            floor = round(c[k] - MARGIN, 3)
            p = v >= floor
            rows["%s.%s" % (name, k)] = {"value": v, "floor": floor, "pass": p}
            ok &= p
            print("%-18s %.3f floor %.3f %s" % (name + "." + k, v, floor, "ok" if p else "FAIL"))
    rep = {"control": c, "pairs": res, "rows": rows, "verdict": "pass" if ok else "fail"}
    json.dump(rep, open(out, "w"), indent=1)
    print("control", c, "VERDICT", rep["verdict"])
    return 0 if ok else 12


if __name__ == "__main__":
    sys.exit(main())
