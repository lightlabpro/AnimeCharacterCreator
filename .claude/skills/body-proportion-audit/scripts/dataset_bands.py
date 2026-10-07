#!/usr/bin/env python3
"""Turn measure_dataset.py output into head and body bands (median, p10-p90) from the clean records only.

    python3 dataset_bands.py measured.json OUT_JSON [--min-heads 5.5]

Clean = not VRoid, rig agrees with the mesh, hair in its own material/node, no sanity flag.
Children/chibi are excluded numerically (heads_tall below --min-heads), not by the caption.
"""
import json, sys
import numpy as np


def clean(r, min_heads):
    return ("error" not in r and not r.get("vroid") and r.get("hair_separated") and not r.get("flags")
            and r.get("heads_tall") and r["heads_tall"] >= min_heads and "head" in r)


def band(vals):
    v = np.array([x for x in vals if x is not None], float)
    if len(v) < 3:
        return None
    return {"n": int(len(v)), "median": round(float(np.median(v)), 3), "p10": round(float(np.percentile(v, 10)), 3),
            "p90": round(float(np.percentile(v, 90)), 3), "p25": round(float(np.percentile(v, 25)), 3),
            "p75": round(float(np.percentile(v, 75)), 3)}


def main():
    src, out = sys.argv[1], sys.argv[2]
    min_heads = float(sys.argv[sys.argv.index("--min-heads") + 1]) if "--min-heads" in sys.argv else 5.5
    R = json.load(open(src))
    if "--only" in sys.argv:          # visually verified landmark list (a contact sheet was checked by eye)
        only = set(json.load(open(sys.argv[sys.argv.index("--only") + 1])))
        R = [r for r in R if r["file"] in only]
        for r in R:   # a verified landmark overrides the automatic plausibility flags, but not VRoid or rig problems
            r["flags"] = [f for f in r.get("flags", []) if f.startswith(("VRoid", "hair not separable"))]
    why = {"total": len(R), "error": 0, "vroid": 0, "hair_not_separated": 0, "flagged": 0, "below_min_heads": 0}
    C = []
    for r in R:
        if "error" in r: why["error"] += 1
        elif r.get("vroid"): why["vroid"] += 1
        elif not r.get("hair_separated"): why["hair_not_separated"] += 1
        elif r.get("flags") or "head" not in r: why["flagged"] += 1
        elif r["heads_tall"] < min_heads: why["below_min_heads"] += 1
        else: C.append(r)
    why["clean"] = len(C)
    head = {"heads_tall": band([r["heads_tall"] for r in C]),
            "skull_depth_0.3": band([r["head"]["skull_depth_0.3"] for r in C]),
            "width_to_depth": band([r["head"]["width_to_depth"] for r in C]),
            "width": {k: band([r["head"]["width"].get(k) for r in C]) for k in C[0]["head"]["width"]} if C else {},
            "behind_nose": {k: band([r["head"]["behind_nose"].get(k) for r in C]) for k in C[0]["head"]["behind_nose"]} if C else {}}
    keys = sorted({k for r in C for k in (r.get("body") or {})})
    body = {k: band([(r.get("body") or {}).get(k) for r in C]) for k in keys}
    res = {"source": "TexVerse sample (Sketchfab, CC BY / CC BY-SA), TypeSafe-ranked anime-style humanoids",
           "selection": why, "min_heads": min_heads, "head": head, "body": body,
           "models": [r["file"] for r in C]}
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(why))



if __name__ == "__main__":
    main()
