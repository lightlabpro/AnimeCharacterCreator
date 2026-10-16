"""Section-by-section reference match with pictures (jev-1.14).

    python typesafe_section_judge.py out.json ours.png ref.png --lm-ours cx,eye_y,mouth_y,chin_y --lm-ref cx,eye_y,mouth_y,chin_y
        [--sections brows,eyes,nose,mouth,jaw_chin,lower_face] [--size 600]

q15 (Sammy: "deeply analyze with typesafe, subdivide face into sections for analysis and comparison with references"):
the whole-face questions mix many differences into one answer. This cuts both images into the same face sections from
four landmarks (face centre x, eye line, mouth line and chin tip, in pixels of the image resized to --size) - so a
section is the same part of the face in both crops whatever the framing - and asks per section:
  - same:  does this section look like the reference's (shape, size, placement; same style)?   (yes = good)
  - issue: the biggest difference, a choice over that section's menu + "none", in both option orders; it counts only
           when both orders agree.
Section boxes are in units of D = chin_y - eye_y (the eye-line-to-chin distance).
"""
import io
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import ask, image_asset  # noqa: E402

MODEL = "jev-1.14.0"
# (x half-width, y top, y bottom) in D; y is relative to the eye line ("e"), the mouth line ("m") or the chin ("c")
BOXES = {
    "brows": (0.85, ("e", -0.45), ("e", -0.06)),
    "eyes": (0.85, ("e", -0.17), ("e", 0.17)),
    "nose": (0.28, ("e", 0.05), ("e", 0.60)),
    "mouth": (0.42, ("m", -0.14), ("m", 0.18)),
    "jaw_chin": (0.80, ("m", -0.22), ("c", 0.08)),
    "lower_face": (1.00, ("e", 0.05), ("c", 0.10)),
    "mouth_open": (0.42, ("m", -0.16), ("m", 0.22)),      # q17: open-mouth style (teeth, interior, tongue, outline)
}
MENUS = {
    "brows": ["thicker", "thinner", "longer", "shorter", "more angled down toward the nose", "flatter", "higher",
              "lower", "darker", "lighter"],
    "eyes": ["bigger", "smaller", "taller opening", "flatter opening", "further apart", "closer together",
             "bigger iris", "smaller iris", "thicker upper lid line", "thinner upper lid line"],
    "nose": ["longer", "shorter", "wider shadow under the tip", "narrower shadow", "stronger bridge highlight",
             "weaker bridge highlight", "higher", "lower"],
    "mouth": ["wider", "narrower", "higher", "lower", "thicker lip line", "thinner lip line", "bigger under-lip shadow",
              "smaller under-lip shadow"],
    "jaw_chin": ["narrower jaw", "wider jaw", "longer chin", "shorter chin", "pointier chin", "rounder chin",
                 "more angular jaw corner", "softer jaw corner"],
    "mouth_open": ["open wider (taller opening)", "less open", "wider mouth", "narrower mouth", "rounder bottom edge (D shape)",
                   "straighter top edge", "thinner upper teeth band", "thicker upper teeth band", "bigger tongue",
                   "smaller tongue", "darker mouth interior", "lighter mouth interior", "no dark line along the bottom edge",
                   "heavier dark line along the top edge", "softer, rounder mouth corners", "lower lip shade closer under the mouth"],
    "lower_face": ["narrower lower face", "wider lower face", "longer lower face", "shorter lower face",
                   "fuller cheeks", "flatter cheeks", "straighter jaw line", "more curved jaw line"],
}
WHAT = {"brows": "eyebrows", "eyes": "eyes (opening, iris, lid line)", "nose": "nose (bridge highlight, tip shadow)",
        "mouth": "mouth (lip line and the shadow under the lower lip)", "jaw_chin": "jaw and chin",
        "lower_face": "lower half of the face: cheeks, jaw line and chin outline",
        "mouth_open": "open mouth (its outline, the opening shape, upper teeth, dark interior, tongue and the lip shade under it)"}


def crop(path, lm, sec, size):
    from PIL import Image
    im = Image.open(path).convert("RGB").resize((size, size))
    cx, ey, my, cy = lm
    D = cy - ey
    hw, (ra, oa), (rb, ob) = BOXES[sec]
    ref = {"e": ey, "m": my, "c": cy}
    box = (int(cx - hw * D), int(ref[ra] + oa * D), int(cx + hw * D), int(ref[rb] + ob * D))
    c = im.crop(tuple(max(0, v) if i < 2 else v for i, v in enumerate(box)))
    s = max(1.0, 320 / min(c.size))
    c = c.resize((int(c.size[0] * s), int(c.size[1] * s)))
    p = os.path.join(os.path.dirname(os.path.abspath(path)), "_sec_%s_%s.png" % (sec, uuid.uuid4().hex[:6]))
    c.save(p)
    return p


def main():
    out, ours, ref = sys.argv[1:4]
    arg = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
    lo = [float(v) for v in arg("--lm-ours").split(",")]
    lr = [float(v) for v in arg("--lm-ref").split(",")]
    size = int(arg("--size") or 600)
    secs = arg("--sections").split(",") if arg("--sections") else list(BOXES)
    res = {"ours": ours, "ref": ref, "sections": {}}
    for sec in secs:
        po_, pr_ = crop(ours, lo, sec, size), crop(ref, lr, sec, size)
        po, pr = "ours-" + uuid.uuid4().hex, "ref-" + uuid.uuid4().hex
        assets = {po: image_asset(po_), pr: image_asset(pr_)}
        state = {"ours_image": po, "reference_image": pr,
                 "note": "Both pictures show the same part of an anime character's face (%s), cut at the same face "
                         "landmarks. reference_image is the target style (Monster Hunter Stories 3); it may be a "
                         "different character, may have hair over it and an open mouth. Compare shape, size and "
                         "placement in the style, not identity, hair, background or lighting." % WHAT[sec]}
        menu = {("m%d" % i): "Make ours: %s." % t for i, t in enumerate(MENUS[sec])}
        menu["none"] = "Nothing: ours already matches the reference closely."
        picks, ps = [], []
        for order in (0, 1):
            opts = list(menu.items())
            if order:
                opts = opts[::-1]
            qs = {"same": {"type": "noul", "instructions": "Look only at the %s. Does the %s in `ours_image` look like the "
                           "%s in `reference_image` in shape, size and placement?" % (WHAT[sec], WHAT[sec], WHAT[sec])},
                  "issue": {"type": "choice", "instructions": "Which single change would make the %s in `ours_image` "
                            "look most like `reference_image`?" % WHAT[sec], "criteria": dict(opts)}}
            r = ask(MODEL, state, qs, assets, True, False)["answers"]
            picks.append(r["issue"].get("choice")); ps.append(float(r["same"]["noul"]))
        for p_ in (po_, pr_):
            try:
                os.remove(p_)
            except OSError:
                pass
        name = lambda k: (MENUS[sec][int(k[1:])] if k and k.startswith("m") else k)
        agree = picks[0] == picks[1]
        res["sections"][sec] = {"p_same": round(sum(ps) / 2, 3), "issue": name(picks[0]) if agree else None,
                                "orders": [name(p) for p in picks]}
        print("%-10s same %.2f  issue %s" % (sec, sum(ps) / 2, res["sections"][sec]["issue"] or ("(disagree: %s)" % res["sections"][sec]["orders"])))
    vals = [v["p_same"] for v in res["sections"].values()]
    res["mean_p_same"] = round(sum(vals) / len(vals), 3)
    json.dump(res, open(out, "w"), indent=1)
    print("mean p_same %.3f" % res["mean_p_same"])


if __name__ == "__main__":
    main()
