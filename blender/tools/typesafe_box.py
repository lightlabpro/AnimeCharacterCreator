"""Locate features in a picture with TypeSafe Box questions (jev-1.14, danger-zone images) - a measuring aid.

    python typesafe_box.py image.png out.json "near_eye=the eye nearer to the viewer, lids included" "far_eye=..."
        [--refine]

Each target gets one Box question (one bounding box: left/right/top/bottom as fractions of the picture) and one
Noul question "is it visible at all?" (a Box always answers, even when the target is absent). With --refine every
box is padded by 40 %, cropped and asked again on the crop (TypeSafe: small targets in big pictures are missed),
then converted back to full-picture fractions. Output: per target the box in fractions and pixels, its width,
height, centre, confidence and p_present. Boxes are measurements to check, not facts: compare them against the
pixel measurements and treat a low confidence or p_present as unknown.
"""
import io
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import ask, image_asset  # noqa: E402

MODEL = "jev-1.14.0"


def boxes(path, targets, model=MODEL):
    ph = "img-" + uuid.uuid4().hex
    qs = {}
    for name, desc in targets.items():
        qs["box_" + name] = {"type": "box", "instructions": "%s in `picture`" % desc}
        qs["seen_" + name] = {"type": "noul", "instructions": "Is %s visible in `picture`?" % desc}
    r = ask(model, {"picture": ph}, qs, {ph: image_asset(path)}, True, False)["answers"]
    return {n: {"box": r["box_" + n]["box"], "confidence": r["box_" + n].get("confidence"),
                "p_present": r["seen_" + n]["noul"]} for n in targets}


def refine(path, targets, first, pad=0.4):
    from PIL import Image
    im = Image.open(path).convert("RGB"); W, H = im.size
    out = {}
    for n, desc in targets.items():
        b = first[n]["box"]
        w, h = b["right"] - b["left"], b["bottom"] - b["top"]
        l, t = max(0.0, b["left"] - pad * w), max(0.0, b["top"] - pad * h)
        r_, bt = min(1.0, b["right"] + pad * w), min(1.0, b["bottom"] + pad * h)
        crop = im.crop((int(l * W), int(t * H), int(r_ * W), int(bt * H)))
        tmp = path + ".crop_%s.png" % n
        crop.save(tmp)
        try:
            c = boxes(tmp, {n: desc})[n]
        finally:
            os.remove(tmp)
        cb = c["box"]; cw, ch = r_ - l, bt - t
        out[n] = {"box": {"left": l + cb["left"] * cw, "right": l + cb["right"] * cw,
                          "top": t + cb["top"] * ch, "bottom": t + cb["bottom"] * ch},
                  "confidence": c["confidence"], "p_present": first[n]["p_present"], "refined": True}
    return out


def main():
    from PIL import Image
    path, out = sys.argv[1], sys.argv[2]
    targets = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)
    res = boxes(path, targets)
    if "--refine" in sys.argv:
        res = refine(path, targets, res)
    W, H = Image.open(path).size
    for n, v in res.items():
        b = v["box"]
        v["px"] = [round(b["left"] * W), round(b["top"] * H), round(b["right"] * W), round(b["bottom"] * H)]
        v["w_px"], v["h_px"] = v["px"][2] - v["px"][0], v["px"][3] - v["px"][1]
        v["centre"] = [round((b["left"] + b["right"]) / 2, 4), round((b["top"] + b["bottom"]) / 2, 4)]
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res))


if __name__ == "__main__":
    main()
