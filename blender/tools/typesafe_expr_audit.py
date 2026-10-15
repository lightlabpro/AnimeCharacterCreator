"""Expression audit with pictures (jev-1.14 danger-zone images): no reference exists for most expressions, so
TypeSafe checks each close-up against a short rubric instead of a reference (yes = good).

    python typesafe_expr_audit.py out.json neutral=zoom_neutral.png blink=zoom_blink.png ...

Per expression, one request with the picture and the neutral picture as the baseline:
  reads_as   - does it read clearly as that expression of an anime eye?
  clean      - are lid line, eye white, iris and skin edges clean and continuous (no gaps, slivers, jagged steps)?
  iris       - is the iris an undistorted round/oval shape where it shows (lids may cover part of it)?
  lid_line   - is the dark upper lid line smooth and even (no hooks, kinks, pinches or breaks)?
  same_style - does it keep the neutral eye's style (colours, line weight, proportions) apart from the expression?
Each question is asked twice (two requests with the questions in a different order) and averaged; under 0.4
confidence -> "needs a human". Results are evidence for Claude and Sammy, not a substitute for looking.

Calibration (2026-10-15): the MHS3 reference eye itself scored clean 0.25 and iris 0.15, so those two rubric
questions are not usable on their own. Pass reference=<MHS3 eye crop> and read every score RELATIVE to the
reference's score (column "vs_ref"); a question is only evidence where the reference scores high.
"""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import ask, image_asset, MIN_CONF  # noqa: E402

MODEL = "jev-1.14.0"
DESC = {"neutral": "a calm neutral open eye", "blink": "a closed eye (blink): only the lid line shows",
        "wink_left": "a closed eye (wink): only the lid line shows", "amazed": "a wide-open amazed eye with a small iris",
        "sad": "a sad eye: upper lid lowered toward the outer side, inner side raised",
        "angry": "an angry eye: upper lid lowered toward the nose (inner side), a frowning look",
        "happy": "a happy eye: lower lid pushed up into a smiling curve, the eye partly closed from below"}


def audit(name, img, base):
    pi, pb = "img-" + uuid.uuid4().hex, "base-" + uuid.uuid4().hex
    assets = {pi: image_asset(img)}
    state = {"expression": name, "meaning": DESC.get(name, name), "picture": pi}
    if base and name != "neutral":
        assets[pb] = image_asset(base); state["neutral_picture"] = pb
    q = {"reads_as": "Does the eye in `picture` read clearly as `meaning` in an anime style?",
         "clean": "In `picture`, are the edges between the dark lid line, the eye white, the iris and the skin clean and "
                  "continuous, with no gaps, skin-coloured slivers, specks or jagged steps?",
         "iris": "In `picture`, where the iris shows, is it an undistorted round or oval shape (the lids may cover part "
                 "of it; covered parts are fine)? Answer yes if no iris shows.",
         "lid_line": "In `picture`, is the dark upper lid line smooth and even, without hooks, kinks, pinches or breaks?"}
    if "neutral_picture" in state:
        q["same_style"] = ("Apart from the expression itself, does the eye in `picture` keep the style of "
                           "`neutral_picture` (colours, line weight, iris design, proportions)?")
    qs = {k: {"type": "noul", "instructions": v} for k, v in q.items()}
    r1 = ask(MODEL, state, qs, assets, True, False)["answers"]
    r2 = ask(MODEL, state, dict(reversed(list(qs.items()))), assets, True, False)["answers"]
    out = {}
    for k in qs:
        p = (r1[k]["noul"] + r2[k]["noul"]) / 2; c = abs(2 * p - 1)
        out[k] = {"p_yes": round(p, 3), "verdict": "needs a human" if c < MIN_CONF else ("ok" if p >= 0.6 else "flagged")}
    return out


def main():
    out = sys.argv[1]
    imgs = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
    ref = imgs.pop("reference", None)
    base = imgs.get("neutral")
    res = {n: audit(n, p, base) for n, p in imgs.items()}
    if ref:
        res["_reference"] = audit("neutral", ref, None)
        for n, r in res.items():
            if n == "_reference":
                continue
            for k, v in r.items():
                if k in res["_reference"]:
                    v["vs_ref"] = round(v["p_yes"] - res["_reference"][k]["p_yes"], 3)
    json.dump(res, open(out, "w"), indent=1)
    for n, r in res.items():
        print(n, {k: (v["p_yes"], v.get("vs_ref"), v["verdict"]) for k, v in r.items()})


if __name__ == "__main__":
    main()
