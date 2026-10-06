"""Does the placeholder read as an anime character?  TypeSafe judges it from word buckets measured against the anime references.

   python tools/placeholders/anime_look.py /tmp/claude-0/placeholder-adult-X.json [--json]

The numbers stay in code: each metric is compared with the Hina / Amshani envelope and sent to TypeSafe only as words
("much smaller than the anime references", "within them", ...). Questions are phrased so yes = good; the Choice (which feature looks
least anime) is asked in two option orders and a disagreement is reported as uncertain. Hair is judged by hair_judge elsewhere.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))
from blender.validators import judge
import measure

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "blender", "references")

# metric -> (feature, what it is); every one is a ratio, so it compares across models of any scale.
FEATURES = {
    "anatomy.eye_line_norm": ("eyes", "how low the eye line sits on the head (anime sits low)"),
    "anatomy.eye_gap_eye_widths": ("eyes", "the gap between the eyes in eye widths (anime eyes are big and close)"),
    "anatomy.eye_height_width": ("eyes", "how tall each eye is for its width"),
    "anatomy.mouth_norm": ("mouth", "how low the mouth sits on the head"),
    "face.nose_protrusion_over_head_height": ("nose", "how far the nose sticks out"),
    "face.jaw_width_over_temple_width": ("jaw", "jaw width against the temple width (anime tapers to a point)"),
    "anatomy.temple_width_norm": ("skull", "head width against head height"),
    "anatomy.neck_head_width": ("neck", "neck width against head width (anime necks are slim)"),
    "anatomy.height_heads": ("body", "body height in heads"),
    "anatomy.forehead_slope": ("skull", "how far the forehead leans back"),
}


def envelope():
    env = {}
    for fn in os.listdir(os.path.join(ROOT, "profiles")):
        for k, v in json.load(open(os.path.join(ROOT, "profiles", fn)))["metrics"].items():
            env.setdefault("anatomy." + k, []).append(v)
    for fn in os.listdir(os.path.join(ROOT, "regions")):
        for k, v in (json.load(open(os.path.join(ROOT, "regions", fn))).get("face_metrics") or {}).items():
            env.setdefault("face." + k, []).append(v)
    return {k: (min(v), max(v)) for k, v in env.items()}


def bucket(v, lo, hi):
    span = max(hi - lo, 0.12 * max(abs(lo), abs(hi), 1e-6))
    if lo - 0.5 * span <= v <= hi + 0.5 * span:
        return "within the anime references"
    d = (lo - v if v < lo else v - hi) / span
    return ("slightly " if d < 1.5 else "much ") + ("below" if v < lo else "above") + " the anime references"


ADULT_ONLY = {"anatomy.eye_gap_eye_widths", "anatomy.eye_height_width", "anatomy.height_heads"}  # the references are adults


def state(metrics, env, kind="adult"):
    rows = []
    for k, (feat, what) in FEATURES.items():
        if k in metrics and k in env and not (kind == "child" and k in ADULT_ONLY):
            rows.append({"feature": feat, "what": what, "reading": bucket(metrics[k], *env[k])})
    return {"subject": "A 3D character head and body, measured against anime reference models", "measurements": rows}


def questions(order, feats):
    opts = {"none": "Every feature reads as anime.", **{f: f"The {f} does not read as anime." for f in feats}}
    items = list(opts.items())
    return {
        "reads_anime": {"type": "noul", "instructions": "Do the `measurements` show a character that reads as an anime character, with every feature within the anime references?"},
        "face_anime": {"type": "noul", "instructions": "Do the eyes, mouth, nose and jaw measurements all read as an anime face?"},
        "quality": {"type": "score", "instructions": "How anime does this character read, from the `measurements`?",
                    "criteria": ["Not anime: most features are far from the references", "Barely anime: several features are far from them",
                                 "Partly anime: a few features are off", "Mostly anime: only slight deviations", "Fully anime: all features sit with the references"]},
        "least_anime": {"type": "choice", "instructions": "Which feature looks least like anime?", "criteria": dict(items[::-1] if order else items)},
    }


def judge_it(path, transport=judge.http_transport):
    rep, fm, _ = measure.run(path, quiet=True)
    m = {(k if k.startswith("face.") else "anatomy." + k): v for k, v in rep.metrics.items()}
    m.update({f"face.{k}": v for k, v in fm.items()})
    env = envelope()
    st = state({k: float(v) for k, v in m.items()}, env, rep.kind)
    feats = sorted({r["feature"] for r in st["measurements"]})
    ans = [transport({"model": judge.MODEL, "state": st, "questions": questions(o, feats)})["answers"] for o in (0, 1)]
    a, b = ans
    least = a["least_anime"]["choice"] if a["least_anime"]["choice"] == b["least_anime"]["choice"] else "uncertain (%s / %s)" % (a["least_anime"]["choice"], b["least_anime"]["choice"])
    return {"reads_anime": a["reads_anime"]["noul"], "face_anime": a["face_anime"]["noul"], "quality": a["quality"]["score"],
            "least_anime": least, "readings": {r["what"][:48]: r["reading"] for r in st["measurements"]}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("json"); ap.add_argument("--json", action="store_true", dest="as_json")
    a = ap.parse_args()
    r = judge_it(a.json)
    if a.as_json:
        print(json.dumps(r))
    else:
        print(f"TypeSafe anime look  reads_anime={r['reads_anime']:.2f} face={r['face_anime']:.2f} quality={r['quality']:.1f}/4  least anime: {r['least_anime']}")
        for k, v in r["readings"].items():
            print("   ", k.ljust(50), v)
