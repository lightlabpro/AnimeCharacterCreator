"""Per-region and per-feature report for a model.

    blender -b model.blend -P analyze_regions.py -- <name> <kind> <body_object> <armature_object|-> <landmarks.json> <out_dir> [typesafe]
Runs the face-feature, rig and expression-coverage validators, regroups every earlier finding by region, prints a region
table and writes <out_dir>/<name>.json. With the last argument "typesafe", unmatched shape keys and bones are mapped by
TypeSafe and each region is judged by TypeSafe (needs TYPESAFE_API_KEY on your PC).
"""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, __file__.rsplit("/blender/", 1)[0])
from blender.validators import bpy_adapter, checks, expression_map, face, judge, measure, regions, rig  # noqa: E402
from blender.validators.model import Report  # noqa: E402


def run(name, kind, body, arm, landmarks, out_dir, use_ts="0"):
    scene = bpy_adapter.snapshot(kind, body_name=body, armature_name=None if arm == "-" else arm)
    scene.parts = bpy_adapter.collect_parts(face.PART_ALIASES)
    meta = bpy_adapter.load_markers(scene, landmarks)
    transport = judge.http_transport if use_ts in ("1", "typesafe") else None
    report = Report(kind=kind, tag=name)
    checks.anatomy(scene, report)
    lm, _ = measure.landmarks(scene)
    bv = np.asarray(scene.body_verts, float) if scene.body_verts is not None else None
    fm = face.metrics({k: (np.asarray(v[0], float), v[1]) for k, v in scene.parts.items()}, bv, lm)
    report.add(*face.findings(fm, {k: 1 for k in scene.parts}, name))
    report.metrics.update({f"face.{k}": v for k, v in fm.items()})
    keys = scene.shape_keys.get(body, [])
    if keys:
        report.add(*expression_map.findings(expression_map.map_keys(keys, transport), name))
    if scene.bones:
        mapping = rig.map_bones(list(scene.bones), transport)
        report.add(*rig.findings(mapping, scene.bone_parents, name))
    rows = regions.region_table(report)
    print(f"{'region':14} {'fail':>4} {'warn':>4} {'pass':>4} {'skip':>4}")
    for rid, label, f, w, p, s in rows:
        print(f"{rid:14} {f:4d} {w:4d} {p:4d} {s:4d}  {label}")
    os.makedirs(out_dir, exist_ok=True)
    json.dump({"name": name, "regions": {r: [x.__dict__ for x in fs] for r, fs in regions.group_by_region(report.findings).items()},
               "face_metrics": fm}, open(os.path.join(out_dir, f"{name}.json"), "w"), indent=2, default=str)
    return report, fm


if __name__ == "__main__":
    run(*sys.argv[sys.argv.index("--") + 1:])
