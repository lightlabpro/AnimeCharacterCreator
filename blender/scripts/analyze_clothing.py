"""Clothing and accessory report for a model.

    blender -b model.blend -P analyze_clothing.py -- <name> <body_object> <landmarks.json> <out_dir> <garment:object> [accessory:slot:object ...]
garment: a deforming garment (fit, coverage, skinning). accessory: a rigid accessory checked for placement in its slot
(eyewear, bandana, shoes, belt, cape, weapon_melee, weapon_ranged).
"""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, __file__.rsplit("/blender/", 1)[0])
from blender.validators import accessory, bpy_adapter, clothing, measure, regions  # noqa: E402
from blender.validators.model import Report  # noqa: E402


def run(name, body, landmarks, out_dir, *specs):
    meta = json.load(open(landmarks)).get("_meta", {})
    flip = [1, -1, 1] if meta.get("forward") == "+Y" else [1, 1, 1]
    bv, bf = bpy_adapter.mesh_arrays(body)
    bv = bv * flip
    lm = {k[3:] if False else k: v for k, v in json.load(open(landmarks)).items() if not k.startswith("_")}
    lm = {k: (v[0] * 1, v[1] * flip[1], v[2]) for k, v in lm.items()}
    height = lm["Crown"][2] - lm["Floor"][2]
    report = Report(kind="clothing", tag=name)
    head_w = float((bv[bv[:, 2] >= lm["Chin"][2]][:, 0].max() - bv[bv[:, 2] >= lm["Chin"][2]][:, 0].min()))
    for spec in specs:
        kind, *rest = spec.split(":")
        if kind == "garment":
            g = rest[0]
            gv, _ = bpy_adapter.mesh_arrays(g)
            gv = gv * flip
            fm = clothing.fit(gv, bv, bf, height)
            cov = clothing.coverage(gv, bv, height, lm["Floor"][2], {"legs": (0.0, 0.47), "torso": (0.47, 0.82), "head_neck": (0.82, 1.0)})
            skin = clothing.skin_agreement(bpy_adapter.dominant_bones(g), bpy_adapter.dominant_bones(body), fm["nearest"])
            report.add(*clothing.findings("clothing", fm, cov, skin, g))
            print(g, {k: round(v, 3) for k, v in {**{k: v for k, v in fm.items() if k != "nearest"}, **cov, **skin}.items()})
        elif kind == "accessory":
            slot, obj = rest
            av, _ = bpy_adapter.mesh_arrays(obj)
            av = av * flip
            m = accessory.metrics(slot, av, lm, head_w)
            report.add(*accessory.findings(slot, m, obj, bpy_adapter.hair_object_info(obj)["parent"]))
            print(obj, slot, {k: round(v, 3) for k, v in m.items()})
    print(report.to_text())
    os.makedirs(out_dir, exist_ok=True)
    json.dump({"name": name, "regions": {r: [x.__dict__ for x in fs] for r, fs in regions.group_by_region(report.findings).items()}},
              open(os.path.join(out_dir, f"{name}-clothing.json"), "w"), indent=2, default=str)


if __name__ == "__main__":
    run(*sys.argv[sys.argv.index("--") + 1:])
