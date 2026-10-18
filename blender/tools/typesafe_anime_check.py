"""Does a render read as anime at all? (q32, Sammy: "what you made doesnt even look like anime")

    python typesafe_anime_check.py out.json IMG1.png [IMG2.png ...] --ref docs/qa/head_v2/judge/leo_ref_front.png

Each image is judged on its own, next to one MHS3 style reference, with yes/no questions (TypeSafe "noul" = yes
probability) and one choice: which single element most stops it reading as a Japanese anime / JRPG character.
Run the MHS3 references themselves through it too: their scores are the ceiling the renders are measured against.
"""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import ask, image_asset  # noqa: E402

MODEL = "jev-1.14.0"
YES = {
    "anime": "Does `image` look like a character from a Japanese anime or JRPG (anime art style), rather than a western "
             "cartoon, a vector clip-art drawing or a realistic face?",
    "mhs3": "Could `image` pass as a character from the same game as `reference_image` (same art style: painted anime "
            "look, eye drawing, soft shading, hair rendering)?",
    "eyes_anime": "Are the eyes in `image` drawn the way anime eyes are drawn (large glossy iris with soft gradient and "
                  "highlights, bold upper lash line)?",
    "hair_anime": "Is the hair in `image` styled and shaded like anime hair (clean clumps, smooth silhouette, glossy "
                  "highlights)?",
    "face_anime": "Is the face shape in `image` an anime face shape (soft, smooth, small nose and mouth, clean jaw line)?",
    "shading_anime": "Is the skin shading in `image` like anime cel / painted shading?",
    "polished": "Does `image` look like a polished professional character, not an amateur or placeholder model?",
}
CULPRITS = {
    "eyes": "the eyes", "brows": "the eyebrows", "nose": "the nose", "mouth": "the mouth",
    "face_shape": "the face / head shape", "hair": "the hair", "skin_shading": "the skin colour and shading",
    "outline": "the outlines", "ears_neck": "the ears or the neck", "nothing": "nothing - it already reads as anime",
}


def main():
    out = sys.argv[1]
    arg = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
    imgs = [a for a in sys.argv[2:] if not a.startswith("--") and a != arg("--ref")]
    pr = "ref-" + uuid.uuid4().hex
    res = {}
    for path in imgs:
        pi = "img-" + uuid.uuid4().hex
        assets = {pi: image_asset(path), pr: image_asset(arg("--ref"))}
        votes = {k: [] for k in YES}
        culprit = []
        for order in (0, 1):
            opts = list(CULPRITS.items())
            if order:
                opts = opts[::-1]
            qs = {k: {"type": "noul", "instructions": t} for k, t in YES.items()}
            qs["culprit"] = {"type": "choice", "instructions": "Which ONE element of `image` most stops it from looking "
                             "like an anime / JRPG character in the style of `reference_image`?",
                             "criteria": {k: v for k, v in opts}}
            state = {"image": pi, "reference_image": pr,
                     "note": "image is the picture being judged; reference_image is an official Monster Hunter Stories 3 "
                             "character render (style target, a different character)."}
            r = ask(MODEL, state, qs, assets, True, False)["answers"]
            for k in YES:
                votes[k].append(float(r[k]["noul"]))
            culprit.append(r["culprit"].get("choice"))
        res[path] = {k: round(sum(v) / 2, 3) for k, v in votes.items()}
        res[path]["culprit"] = culprit
        print(os.path.basename(os.path.dirname(path)) + "/" + os.path.basename(path), json.dumps(res[path]))
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
