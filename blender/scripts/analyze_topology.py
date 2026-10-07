"""Topology report for a model: static structure, loops at joints, bend and shape-key deformation.

    blender -b model.blend -P analyze_topology.py -- <name> <body_object> <armature_object|-> <out_dir>
Writes <out_dir>/<name>.json (a topology profile that new work is compared with) and prints the findings.
Each region is bent to the end of its own range of motion (deform_regions.MOTIONS: elbow 145, knee 140, neck 45, finger 90, ...)
and judged on its weight-blend zone against that region's bands; the rig must have an armature modifier on the body.
Shape keys are applied at 1 and judged by the region the key belongs to (lids, lips, brows ...).
"""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, __file__.rsplit("/blender/", 1)[0])
from blender.validators import bpy_adapter, deform_regions, measure, topology  # noqa: E402
from blender.validators.model import Finding, Report  # noqa: E402



def run(name, body, arm, out_dir):
    # the rest pose must have every shape key at 0 (the library contract), whatever state the file was saved in
    me0 = bpy.data.objects[body].data
    saved = {kb.name: kb.value for kb in me0.shape_keys.key_blocks} if me0.shape_keys else {}
    for kb in (me0.shape_keys.key_blocks if me0.shape_keys else []):
        kb.value = 0.0
    bpy.context.view_layer.update()
    v, faces = bpy_adapter.mesh_arrays(body)
    edges, _ = topology.edges_of(faces)
    report = Report(kind="topology", tag=name)
    st = topology.stats(v, faces)
    report.add(*topology.static_findings(st, name))
    height = float(v[:, 2].max() - v[:, 2].min())
    out = {"name": name, "stats": {k: x for k, x in st.items() if k != "poles"}, "loops": {}, "bend": {}, "shape_keys": {}}
    if arm != "-":
        armature = bpy.data.objects[arm]
        names = [b.name for b in armature.pose.bones]
        mw = armature.matrix_world
        loops = {}
        out["regions"] = {}
        for m in deform_regions.MOTIONS:
            bn = measure.find_bone_name(names, m.role, "L")
            if not bn:
                continue
            pb = armature.pose.bones[bn]
            distal = np.array(tuple(mw @ (pb.children[0].head if pb.children else pb.tail)))
            weights, moving, head, axes, total = bpy_adapter.joint_weights(arm, body, bn)
            joint = deform_regions.Joint(weights, moving, head, axes, total, distal)
            fs = deform_regions.run_motion(m, v, faces, joint, edges)
            report.add(*fs)
            loops.update({m.label: int(f.value) for f in fs if f.check.endswith(".loops")})
            out["regions"].setdefault(m.region, {})[m.label] = {f.check.rsplit(".", 1)[-1]: [f.severity, f.value] for f in fs if f.value is not None}
    me = bpy.data.objects[body].data
    if me.shape_keys:
        for kb in me.shape_keys.key_blocks[1:]:
            posed = bpy_adapter.shape_key_verts(body, kb.name)
            fs = deform_regions.run_key(kb.name, v, posed, faces)
            report.add(*fs)
            out["shape_keys"][kb.name] = {"region": deform_regions.key_region(kb.name),
                                          **{f.check.rsplit(".", 1)[-1]: [f.severity, f.value] for f in fs if f.value is not None}}
    degenerate = 0
    if degenerate:
        report.add(Finding("hygiene.coincident", "warn" if degenerate > 0.005 * len(edges) else "info",
                           f"{degenerate} edges are shorter than 0.1% of the height (coincident vertices); excluded from deformation ratios",
                           float(degenerate), "0", "Merge by distance."))
    if arm != "-":
        out["loops"] = loops
    if os.environ.get("TYPESAFE_JUDGE"):
        from blender.validators import deform_judge
        for region, fs in deform_judge.judge_all(report.findings).items():
            report.add(*fs)
    for kname, val in saved.items():
        me0.shape_keys.key_blocks[kname].value = val
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{name}.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(report.to_text())
    return report, out


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    run(*a)
