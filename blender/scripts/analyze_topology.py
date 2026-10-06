"""Topology report for a model: static structure, loops at joints, bend and shape-key deformation.

    blender -b model.blend -P analyze_topology.py -- <name> <body_object> <armature_object|-> <out_dir>
Writes <out_dir>/<name>.json (a topology profile that new work is compared with) and prints the findings.
Bend tests rotate each joint about its local X and Z by +/-BEND degrees and keep the worst result; the rig must have
an armature modifier on the body. Shape keys are applied at 1.
"""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, __file__.rsplit("/blender/", 1)[0])
from blender.validators import bpy_adapter, measure, topology  # noqa: E402
from blender.validators.model import Finding, Report  # noqa: E402

BEND = {"shoulder": 60, "elbow": 90, "knee": 90, "hip": 60}
ROLE_BONE = {"shoulder": "shoulder", "elbow": "elbow", "knee": "knee", "hip": "hip"}


def run(name, body, arm, out_dir):
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
        for role in ("shoulder", "elbow", "knee"):
            bn = measure.find_bone_name(names, ROLE_BONE[role], "L")
            if not bn:
                continue
            pb = armature.pose.bones[bn]
            # axis along the limb: from this joint toward the next bone down the chain
            child = pb.children[0] if pb.children else None
            head = np.array(tuple(mw @ pb.head))
            tail = np.array(tuple(mw @ (child.head if child else pb.tail)))
            loops[role] = topology.ring_count(v, edges, head, tail - head, 0.03 * height)
        report.add(*topology.loop_findings(loops, name))
        out["loops"] = loops
        for role, deg in BEND.items():
            bn = measure.find_bone_name(names, ROLE_BONE[role], "L")
            if not bn:
                continue
            worst = None
            weights, moving, head, axes, total = bpy_adapter.joint_weights(arm, body, bn)
            for axis in (0, 2):
                for sign in (1, -1):
                    posed = topology.lbs_rotate(v, weights, moving, head, axes[axis], sign * deg, total)
                    d = topology.deformation(v, posed, faces, edges)
                    d.pop("worst_locations")
                    score = max(d["edge_stretch_max"], 1 / max(d["edge_squash_min"], 1e-6)) + 100 * d["flipped_fraction"]
                    if worst is None or score > worst[0]:
                        worst = (score, d, f"{bn} local {'XYZ'[axis]} {sign * deg:+d} deg")
            report.add(*topology.deformation_findings(worst[1], f"{role}[{worst[2]}]"))
            out["bend"][role] = {"worst": worst[2], **worst[1]}
    me = bpy.data.objects[body].data
    if me.shape_keys:
        for kb in me.shape_keys.key_blocks[1:]:
            d = topology.deformation(v, bpy_adapter.shape_key_verts(body, kb.name), faces, edges)
            d.pop("worst_locations")
            out["shape_keys"][kb.name] = d
        bad = {k: d for k, d in out["shape_keys"].items()
               if d["flipped_fraction"] > 0.002 or d["frac_stretch_gt_2"] + d["frac_squash_lt_half"] > 0.01}
        report.add(Finding("deform.shape_keys", "warn" if bad else "pass",
                           f"{len(out['shape_keys']) - len(bad)}/{len(out['shape_keys'])} shape keys apply cleanly (no folds, <1% extreme edges)"
                           + (f"; check: {', '.join(sorted(bad, key=lambda k: -(bad[k]['frac_stretch_gt_2'] + bad[k]['frac_squash_lt_half']))[:4])}" if bad else "")))
    degenerate = next((d.get("ignored_degenerate_edges", 0) for d in out["bend"].values()), 0)
    if degenerate:
        report.add(Finding("hygiene.coincident", "warn" if degenerate > 0.005 * len(edges) else "info",
                           f"{degenerate} edges are shorter than 0.1% of the height (coincident vertices); excluded from deformation ratios",
                           float(degenerate), "0", "Merge by distance."))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{name}.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(report.to_text())
    return report, out


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    run(*a)
