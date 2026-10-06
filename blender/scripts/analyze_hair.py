"""Hair report for a model.

    blender -b model.blend -P analyze_hair.py -- <name> <hair_spec> <body_object> <landmarks.json> <out_dir> [ear_clear]
hair_spec is an object name, or  body:<object>:<vertex_group>:<material_index>  for hair baked into the body mesh
(faces of that material whose vertices are mostly weighted to the group).
Writes <out_dir>/<name>.json (a hair profile) and prints the findings.
"""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, __file__.rsplit("/blender/", 1)[0])
from blender.validators import bpy_adapter, hair  # noqa: E402
from blender.validators.model import Finding, Report  # noqa: E402


def isolate(spec):
    if not spec.startswith("body:"):
        v, f, uv = bpy_adapter.hair_arrays(spec)
        return v, f, uv, bpy_adapter.hair_object_info(spec)
    _, obj, group, mat = spec.split(":")
    ob = bpy.data.objects[obj]
    v, faces = bpy_adapter.mesh_arrays(obj)
    gi = ob.vertex_groups[group].index
    w = np.zeros(len(v))
    for vert in ob.data.vertices:
        for g in vert.groups:
            if g.group == gi:
                w[vert.index] = g.weight
    mi = np.array([p.material_index for p in ob.data.polygons])
    keep = [i for i, f in enumerate(faces) if mi[i] == int(mat) and np.mean(w[list(f)] > 0.5) >= 0.8]
    sub = [faces[i] for i in keep]
    used = sorted({x for f in sub for x in f})
    remap = {o: n for n, o in enumerate(used)}
    layer = ob.data.uv_layers.active
    uv = []
    if layer is not None:
        polys = ob.data.polygons
        uv = [[tuple(layer.data[k].uv) for k in range(polys[i].loop_start, polys[i].loop_start + polys[i].loop_total)] for i in keep]
    return v[used], [tuple(remap[x] for x in f) for f in sub], uv, {"parent": ob.parent.name if ob.parent else "", "materials": [], "shape_keys": [], "props": []}


def run(name, spec, body, landmarks, out_dir, ear_clear="0"):
    lm = {k: v for k, v in json.load(open(landmarks)).items() if not k.startswith("_")}
    meta = json.load(open(landmarks)).get("_meta", {})
    flip = -1.0 if meta.get("forward") == "+Y" else 1.0
    hv, hf, uv, info = isolate(spec)
    bv, bf = bpy_adapter.mesh_arrays(body)
    if flip < 0:
        hv, bv = hv * [1, -1, 1], bv * [1, -1, 1]
    crown, chin = lm["Crown"][2], lm["Chin"][2]
    head_h = crown - chin
    clumps = hair.clump_stats(hv, hf)
    s = hair.summarise(clumps, head_h)
    report = Report(kind="hair", tag=name)
    report.add(*hair.findings(s, name))
    fit = hair.head_fit(hv, bv, bf, chin, crown, ear_clear == "1")
    report.add(*hair.fit_findings(fit, name))
    if uv:
        report.add(*hair.uv_findings(hair.uv_islands(hf, uv), len(clumps), name))
    bucket = hair.length_bucket(float(hv[:, 2].min()), crown, head_h)
    report.add(Finding(f"hair.{name}.length", "info", f"{name}: hair length reads as {bucket}"))
    out = {"name": name, "summary": s, "fit": fit, "length_bucket": bucket, "verts": int(len(hv)), "clumps": len(clumps)}
    os.makedirs(out_dir, exist_ok=True)
    json.dump(out, open(os.path.join(out_dir, f"{name}.json"), "w"), indent=2)
    print(report.to_text())
    print("SUMMARY", {k: round(x, 3) for k, x in s.items()})
    print("FIT", {k: round(x, 3) for k, x in fit.items()})
    return report, out


if __name__ == "__main__":
    run(*sys.argv[sys.argv.index("--") + 1:])
