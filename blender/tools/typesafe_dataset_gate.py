"""Dataset pass 2 (2026-10-15): picture gate for reference models with TypeSafe jev-1.14 (danger-zone images).

    python typesafe_dataset_gate.py RENDER_DIR OUT_JSON [--boxes]

Pass 1 (2026-10-07) ranked candidates on name, tags and caption only, and Claude checked the landmark sheets by eye
(19 of 65 kept). TypeSafe can now see pictures, so each candidate is asked, with three pictures:
  full  - the textured model as imported            -> humanoid_anime, adult
  shape - the measured geometry, front + side, with the measured skull-top and chin rows as red lines
                                                     -> bare_head, top_ok, chin_ok
  face  - the textured head from the front          -> face_front
All noul questions are yes = good. A model enters the bands only when every answer is >= 0.6; anything between 0.4
and 0.6 is "needs a human" (Claude looks), below 0.4 it is out. With --boxes, models that pass get TypeSafe Box
questions on `face` (eyes, brows, mouth, nose, ears) for feature measurements, refined on crops by typesafe_box.py.
Pictures are judged, never copied into the library.
"""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import ask, image_asset  # noqa: E402

MODEL = "jev-1.14.0"
Q = {
    "humanoid_anime": "Is `full` a single humanoid character (human or human-like beast person) drawn in an anime or manga style (stylised, large eyes, simplified forms), not a realistic, chibi or western-cartoon style?",
    "adult": "Does the character in `full` have adult or older-teen proportions (not a child or toddler)?",
    "bare_head": "Is the grey mesh in `shape` a bare head and neck (no hat, helmet, hood or hair mass over the skull), shown from the front on the left and from the side on the right?",
    "top_ok": "In `shape`, does the upper red line touch the top of the bare skull in both views (within a small margin)?",
    "chin_ok": "In `shape`, does the lower red line touch the bottom tip of the chin in both views (within a small margin)?",
    "face_front": "Does `face` show the character's face from the front with both eyes, the nose and the mouth visible?",
}
BOX = {
    "eye_r": "the eye on the left side of `face` (the character's right eye), lids and lashes included",
    "eye_l": "the eye on the right side of `face` (the character's left eye), lids and lashes included",
    "brow_r": "the eyebrow on the left side of `face`",
    "brow_l": "the eyebrow on the right side of `face`",
    "mouth": "the mouth in `face`",
    "nose": "the nose in `face`",
    "face": "the face from hairline to chin and cheek to cheek in `face` (not the hair)",
}


def gate(rdir, uid):
    ph = {k: "img-" + uuid.uuid4().hex for k in ("full", "shape", "face")}
    assets = {ph["full"]: image_asset(os.path.join(rdir, uid + "_full.png")),
              ph["shape"]: image_asset(os.path.join(rdir, uid + "_shape.png")),
              ph["face"]: image_asset(os.path.join(rdir, uid + "_face.png"))}
    qs = {k: {"type": "noul", "instructions": v} for k, v in Q.items()}
    r = ask(MODEL, {"full": ph["full"], "shape": ph["shape"], "face": ph["face"]}, qs, assets, True, False)
    return {k: round(float(r["answers"][k]["noul"]), 3) for k in Q}


def boxes(rdir, uid):
    ph = "img-" + uuid.uuid4().hex
    qs = {"box_" + k: {"type": "box", "instructions": "%s" % v} for k, v in BOX.items()}
    r = ask(MODEL, {"face": ph}, qs, {ph: image_asset(os.path.join(rdir, uid + "_face.png"))}, True, False)["answers"]
    return {k: {"box": r["box_" + k]["box"], "confidence": r["box_" + k].get("confidence")} for k in BOX}


def main():
    rdir, out = sys.argv[1], sys.argv[2]
    res = json.load(open(out)) if os.path.exists(out) else {}
    uids = sorted({f.split("_")[0] for f in os.listdir(rdir) if f.endswith("_shape.png")})
    for u in uids:
        if u in res and "gate" in res[u] and ("--boxes" not in sys.argv or "boxes" in res[u] or not res[u].get("pass")):
            continue
        try:
            rec = res.get(u) or {}
            if "gate" not in rec:
                rec["gate"] = gate(rdir, u)
            g = rec["gate"]
            rec["pass"] = all(v >= 0.6 for v in g.values())
            rec["needs_human"] = [k for k, v in g.items() if 0.4 <= v < 0.6]
            if "--boxes" in sys.argv and (rec["pass"] or (g["humanoid_anime"] >= 0.6 and g["face_front"] >= 0.6)):
                rec["boxes"] = boxes(rdir, u)
            res[u] = rec
        except Exception as e:
            res[u] = {"error": repr(e)[:400]}
        print(u, res[u].get("pass"), res[u].get("gate"), flush=True)
        json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
