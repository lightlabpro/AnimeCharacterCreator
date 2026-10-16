"""Expression recognition check with pictures (jev-1.14): does each render read as the expression it is meant to show?

    python typesafe_expr_check.py out.json label=image.png [label=image.png ...] [--labels a,b,c]

q14: the face is rigged per element (brows, lids, irises, nose, mouth); a preset only works if a viewer reads the
intended emotion from the combination. For each image TypeSafe answers one choice question ("which expression does
this face show?") over all labels plus "neutral" and "unclear", asked twice with the label order reversed, and one
yes/no question ("does this face clearly show <label>?"). A render counts as recognised when both orders pick its
label. Output: per image the two picks, p_clear, and the overall recognition rate.
"""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import ask, image_asset  # noqa: E402

MODEL = "jev-1.14.0"
DESC = {
    "neutral": "a calm, neutral face", "smile": "a gentle closed-mouth smile", "happy": "a happy open-mouth smile",
    "laugh": "laughing", "amazed": "amazed / surprised", "sad": "sad", "angry": "angry (mouth closed)",
    "shout": "shouting angrily", "worried": "worried / anxious", "determined": "determined / confident smirk",
    "skeptical": "skeptical (one brow raised)", "pout": "pouting", "talk_a": "talking, saying 'ah'",
    "talk_o": "talking, saying 'oh'", "talk_e": "talking, saying 'eh'", "blink": "eyes closed (blinking)",
}


def main():
    out = sys.argv[1]
    items = [a.split("=", 1) for a in sys.argv[2:] if "=" in a and not a.startswith("--") and "," not in a.split("=")[0]]
    arg = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
    labels = sorted(set(arg("--labels").split(",")) if arg("--labels") else ({k.split("@")[0] for k, _ in items} | {"neutral"}))
    crit = {k: "The face shows %s." % DESC.get(k, k) for k in labels}
    crit["unclear"] = "The expression is unclear or does not match any of these."
    res = {"items": {}}
    for key, path in items:
        lab = key.split("@")[0]               # "pout@p1=..." scores variant p1 of pout
        pid = "img-" + uuid.uuid4().hex
        picks = []
        for order in (0, 1):
            opts = list(crit.items())
            if order:
                opts = opts[::-1]
            qs = {"which": {"type": "choice", "instructions": "Look at the anime character's face in `face_image`. Which "
                            "expression does it show? Judge the brows, eyes and mouth together.", "criteria": dict(opts)},
                  "clear": {"type": "noul", "instructions": "Look at `face_image`. Does the face clearly show %s?" % DESC.get(lab, lab)}}
            r = ask(MODEL, {"face_image": pid}, qs, {pid: image_asset(path)}, True, False)["answers"]
            picks.append((r["which"].get("choice"), float(r["clear"]["noul"])))
        res["items"][key] = {"picks": [p[0] for p in picks], "recognised": picks[0][0] == picks[1][0] == lab,
                             "p_clear": round((picks[0][1] + picks[1][1]) / 2, 3)}
        print(key, res["items"][key])
    n = len(res["items"]); k = sum(v["recognised"] for v in res["items"].values())
    res["recognition_rate"] = round(k / max(n, 1), 3)
    res["mean_p_clear"] = round(sum(v["p_clear"] for v in res["items"].values()) / max(n, 1), 3)
    json.dump(res, open(out, "w"), indent=1)
    print("recognised %d/%d, mean p_clear %.3f" % (k, n, res["mean_p_clear"]))


if __name__ == "__main__":
    main()
