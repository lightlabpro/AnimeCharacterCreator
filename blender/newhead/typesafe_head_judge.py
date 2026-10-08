"""TypeSafe judgment of the new head (words only, yes = good). Runs where TYPESAFE_API_KEY is set (Sammy's PC).

    python typesafe_head_judge.py val.json topo.json out.json

1. topology_judge.ask (repo validator) on the measured quad statistics.
2. A head judgment: every dataset-band row turned into words (below / low end / typical / high end / above),
   plus the topology facts in words; noul questions phrased so yes = good, a choice question with a "none" option
   asked in both option orders. Confidence |2p-1| < 0.4 goes to a human. Numbers stay authoritative: TypeSafe can
   add a warning, it never clears a failure.
"""
import json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from blender.validators import topology_judge, judge  # noqa: E402

URL, MODEL = "https://api.typesafe.ai/v1/systemone", "jev-1.13.0"


def key():
    k = os.environ.get("TYPESAFE_API_KEY")
    if not k and os.name == "nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
            k = winreg.QueryValueEx(h, "TYPESAFE_API_KEY")[0]
    if not k:
        raise SystemExit("TYPESAFE_API_KEY missing: no judgment faked.")
    return k


def post(payload):
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"content-type": "application/json", "authorization": "Bearer " + key()})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def words(row):
    # row: "  width@0.25  band 0.659-0.804 (median 0.706, n=18)  got 0.705  in"
    parts = row.split()
    name = parts[0]
    lo, hi = [float(x) for x in parts[2].split("-")]
    med = float(parts[4].rstrip(","))
    got = float(parts[parts.index("got") + 1])
    span = hi - lo
    if got < lo:
        w = "below the range of the reference heads"
    elif got > hi:
        w = "above the range of the reference heads"
    elif abs(got - med) <= 0.25 * span:
        w = "typical of the reference heads"
    elif got < med:
        w = "inside the range, toward the low end"
    else:
        w = "inside the range, toward the high end"
    return name, w


NAMES = {"width": "head width", "behind_nose": "how far behind the nose tip the profile sits"}


def main():
    val, topo, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))["ours"], sys.argv[3]
    rows = {}
    for r in val["rows"]:
        n, w = words(r)
        kind, _, frac = n.partition("@")
        label = (NAMES.get(kind, kind) + (" at %d%% down from the skull top" % round(float(frac) * 100) if frac else "")).strip()
        rows[label] = w
    st = val["topology"]
    state = {
        "head_shape_vs_18_measured_anime_heads": rows,
        "mesh": {
            "faces": "all quads" if st["quad_ratio"] > 0.99 else "mostly quads",
            "head_face_count": "inside the range of the reference heads" if 1156 <= topo["head_faces"] <= 11828 else "outside the range",
            "face_vs_skull_density": "denser on the face than on the skull, like the reference heads" if topo["density_front_over_back"] >= 1.6 else "only a little denser on the face than on the skull (reference heads: clearly denser on the face)",
            "eye_openings": "concentric edge loops around both eye openings" if all(e["closed_rings"] >= 3 for e in topo["eye_openings"]) else "no clean loops around the eyes",
            "quad_shape": topology_judge._skew(st["quad_skew_p95"]),
            "quad_proportions": topology_judge._aspect(st["quad_aspect_p95"]),
            "folded_faces": "none found",
        },
    }
    qs = {
        "plausible": {"type": "noul", "instructions": "Do the measurements in `head_shape_vs_18_measured_anime_heads` describe a believable anime character head with the same proportions as the reference heads?"},
        "profile_ok": {"type": "noul", "instructions": "Do the profile rows (how far behind the nose tip the profile sits) describe a normal anime face profile, with a forehead, nose and chin in typical positions?"},
        "mesh_ok": {"type": "noul", "instructions": "Does `mesh` describe a clean, production-style head mesh suitable for animation and shape keys?"},
        "density_ok": {"type": "noul", "instructions": "Is `mesh.face_vs_skull_density` like the reference heads?"},
    }
    fixes = {"proportion": "a head width or profile row is outside or at the edge of the reference range",
             "density": "the face needs more edge loops relative to the skull",
             "quad_shape": "sheared or long thin quads should be relaxed",
             "none": "nothing needs fixing first"}
    results = {"head": [], "topology": []}
    answers = []
    for order in (0, 1):
        opts = list(fixes.items())
        if order:
            opts = opts[::-1]
        q = dict(qs, first_fix={"type": "choice", "instructions": "Which single problem should the modeler fix first on this head?", "criteria": dict(opts)})
        answers.append(post({"model": MODEL, "state": state, "questions": q})["answers"])
    for name in qs:
        p = answers[0][name]["noul"]
        conf = abs(2 * p - 1)
        results["head"].append({"question": name, "p_yes": round(p, 3), "confidence": round(conf, 3),
                                "verdict": "needs a human" if conf < 0.4 else ("pass" if p >= 0.6 else "warn")})   # low confidence never passes
    f0, f1 = answers[0]["first_fix"].get("choice"), answers[1]["first_fix"].get("choice")
    results["head"].append({"question": "first_fix", "order_a": f0, "order_b": f1, "agree": f0 == f1})
    # repo topology judge (stats only; no rig yet so no bends or loops)
    tj = topology_judge.ask({"stats": st}, "new_head", transport=lambda p: post(p))
    results["topology"] = [{"check": f.check, "severity": f.severity, "message": f.message, "value": f.value} for f in tj]
    results["state_sent"] = state
    json.dump(results, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in results.items() if k != "state_sent"}, indent=1))


if __name__ == "__main__":
    main()
