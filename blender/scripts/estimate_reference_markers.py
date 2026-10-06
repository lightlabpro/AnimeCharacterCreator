"""Estimate LM-* landmarks for a reference model from its own geometry, and write a sidecar JSON.

Run inside Blender (or with the `bpy` module):
    blender -b model.blend -P estimate_reference_markers.py -- hina  out.json
    blender -b model.blend -P estimate_reference_markers.py -- amshani out.json

Every landmark is measured from the mesh, a vertex group, a shape key or a bone, never from the manual's targets,
so the validators do not compare a model with itself. Each entry in _meta.methods says how it was measured. These
are ESTIMATES: check them against the viewport (add LM-* empties to override) before trusting a reference.
"""
import json
import sys

import bpy
import numpy as np

sys.path.insert(0, __file__.rsplit("/blender/", 1)[0])
from blender.validators import bpy_adapter  # noqa: E402


def weighted_verts(ob, names, min_w=0.5):
    ids = {g.index for g in ob.vertex_groups if any(n.lower() == g.name.lower() for n in names)}
    return [i for i, v in enumerate(ob.data.vertices) if any(g.group in ids and g.weight > min_w for g in v.groups)]


def components(faces, n):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for f in faces:
        r = find(f[0])
        for w in f[1:]:
            parent[find(w)] = r
    out = {}
    for f in faces:
        out.setdefault(find(f[0]), set()).update(f)
    return [np.array(sorted(s)) for s in out.values()]


def crotch(v, zlo, zhi, height):
    """Lowest z where vertices reach the midline, i.e. where the legs join. Returns None if the legs touch all the
    way down (no gap to find), because then the crotch cannot be measured from the silhouette."""
    tol = 0.002 * height
    m = (np.abs(v[:, 0]) < tol) & (v[:, 2] > zlo) & (v[:, 2] < zhi)
    if not m.any():
        return None
    z = float(v[m, 2].min())
    return None if z <= zlo + 0.01 * height else z


def foot_extents(v, floor, height, left_sign, front_sign):
    m = (v[:, 2] < floor + 0.04 * height) & (np.sign(v[:, 0]) == left_sign)
    ys = v[m, 1]
    toe = ys.max() if front_sign > 0 else ys.min()
    heel = ys.min() if front_sign > 0 else ys.max()
    return float(heel), float(toe), float(v[m, 0].mean())


def shape_key_region(ob, key):
    """World-space coordinates (open-state) of the vertices a shape key moves."""
    kb = ob.data.shape_keys.key_blocks
    basis = np.array([tuple(d.co) for d in kb[0].data])
    other = np.array([tuple(d.co) for d in kb[key].data])
    moved = np.linalg.norm(other - basis, axis=1) > 1e-4
    mw = ob.matrix_world
    return np.array([tuple(mw @ bpy.data.objects[ob.name].data.vertices[i].co) for i in np.nonzero(moved)[0]])


def run(model, out_path):
    meta = {"estimated": True, "methods": {}}
    lm = {}
    if model == "hina":
        ob = bpy.data.objects["body"]
        v, f = bpy_adapter.mesh_arrays("body")
        front = +1
        meta["forward"] = "+Y"
        left_sign = -1  # a +Y-facing character's left is -X
        floor, crown = float(v[:, 2].min()), float(v[:, 2].max())
        lm["Floor"], lm["Crown"] = [0, 0, floor], [0, 0, crown]
        meta["methods"]["Crown"] = "highest body vertex; hair is a separate object so this is the skull top"
        # chin: walk down the central profile from the mouth until the front surface recedes into the neck
        head_w = 0.2
        mouth_z = float(np.mean([bpy.data.objects[n].matrix_world.translation.z for n in ("teeth.t", "teeth.b")]))
        central = np.abs(v[:, 0]) < 0.03
        def front_y(z):
            m = central & (np.abs(v[:, 2] - z) < 0.005)
            return float(v[m, 1].max()) if m.any() else None
        ref = front_y(mouth_z)
        z, chin = mouth_z, mouth_z
        while z > mouth_z - 0.12:
            fy = front_y(z)
            if fy is not None and fy >= ref - 0.15 * head_w:
                chin = z
            elif fy is not None:
                break
            z -= 0.005
        lm["Chin"] = [0, 0, chin - 0.0025]
        meta["methods"]["Chin"] = "lowest z where the central front surface is still within 15% of head width of the mouth-level front"
        lm["Mouth"] = [0, 0, mouth_z]
        meta["methods"]["Mouth"] = "mean z of the upper and lower teeth objects"
        # eyes from the eyeball objects (the eyeball, not the lid opening: an approximation)
        for name, side in (("eye.l", "L"), ("eye.r", "R")):
            e = bpy.data.objects[name]
            pts = np.array([tuple(e.matrix_world @ c.co) for c in e.data.vertices])
            lm[f"EyeTop_{side}"] = [float(pts[:, 0].mean()), float(pts[:, 1].mean()), float(pts[:, 2].max())]
            lm[f"EyeBottom_{side}"] = [float(pts[:, 0].mean()), float(pts[:, 1].mean()), float(pts[:, 2].min())]
            lm[f"_x_{side}"] = [float(pts[:, 0].min()), float(pts[:, 0].max())]
        xs = {k: lm.pop(k) for k in list(lm) if k.startswith("_x_")}
        centers = {s: sum(xs[f"_x_{s}"]) / 2 for s in "LR"}
        for s in "LR":
            lo, hi = xs[f"_x_{s}"]
            inner_is_hi = centers[s] < 0  # the eye on the -X side has its inner corner toward +X
            inner, outer = (hi, lo) if inner_is_hi else (lo, hi)
            ez = lm[f"EyeTop_{s}"][2] / 2 + lm[f"EyeBottom_{s}"][2] / 2
            lm[f"EyeInner_{s}"] = [inner, lm[f"EyeTop_{s}"][1], ez]
            lm[f"EyeOuter_{s}"] = [outer, lm[f"EyeTop_{s}"][1], ez]
        meta["methods"]["Eye*"] = "bounding box of the eyeball objects; corners are the eyeball extents, so eye width is slightly overstated"
        # chest line: centroid of the breast vertex groups
        br = weighted_verts(ob, ["DEF-breast.L", "DEF-breast.R"])
        if br:
            lm["Nipple"] = [0, 0, float(v[br, 2].mean())]
            meta["methods"]["Nipple"] = "centroid z of the DEF-breast vertex groups"
        pub = crotch(v, 0.3 * (crown - floor), 0.6 * (crown - floor), crown - floor)
        if pub is None:
            meta["not_measurable"] = {"Pubis": "Hina's thighs touch down to the knees, so there is no leg gap to find the crotch from"}
        else:
            lm["Pubis"] = [0, 0, pub]
            meta["methods"]["Pubis"] = "lowest vertex on the midline between 30% and 60% of height, where the legs join"
        height = crown - floor
        heel, toe, fx = foot_extents(v, floor, height, left_sign, front)
        lm["HeelBack_L"], lm["ToeTip_L"] = [fx, heel, floor], [fx, toe, floor]
        meta["methods"]["HeelBack_L/ToeTip_L"] = "y extremes of the left foot vertices below 4% of height"
        meta["unreliable_metrics"] = ["eye_gap_eye_widths", "eye_height_width"]
        meta["methods"]["unreliable_metrics"] = "eye gap and eye height/width need the eye OPENING; Hina only has eyeball objects"
        meta["skipped"] = "Navel, shoulder/elbow/wrist/hip/knee/ankle, HandTip: Hina has no armature, so joints cannot be measured"
    else:  # amshani
        ob = bpy.data.objects["da body"]
        v, f = bpy_adapter.mesh_arrays("da body")
        front = -1
        meta["forward"] = "-Y"
        left_sign = +1
        mat = np.array([p.material_index for p in ob.data.polygons])
        skin_faces = [fc for fc, mi in zip(f, mat) if mi == 0]
        shells = components(skin_faces, len(v))
        head = max(shells, key=lambda s: v[s, 2].max())
        floor = float(v[:, 2].min())
        lm["Floor"] = [0, 0, floor]
        lm["Crown"] = [0, 0, float(v[head, 2].max())]
        lm["Chin"] = [0, 0, float(v[head, 2].min())]
        meta["methods"]["Crown/Chin"] = "top and bottom of the skin-material head shell (the hair, a different material, reaches 23.3)"
        for side, key, sign in (("L", "Blink L", +1), ("R", "Blink R", -1)):
            pts = shape_key_region(ob, key)
            lm[f"EyeInner_{side}"] = [float(pts[:, 0].min() if sign > 0 else pts[:, 0].max()), float(pts[:, 1].mean()), float(pts[:, 2].mean())]
            lm[f"EyeOuter_{side}"] = [float(pts[:, 0].max() if sign > 0 else pts[:, 0].min()), float(pts[:, 1].mean()), float(pts[:, 2].mean())]
            lm[f"EyeTop_{side}"] = [float(pts[:, 0].mean()), float(pts[:, 1].mean()), float(pts[:, 2].max())]
            lm[f"EyeBottom_{side}"] = [float(pts[:, 0].mean()), float(pts[:, 1].mean()), float(pts[:, 2].min())]
        meta["methods"]["Eye*"] = "extent of the vertices the Blink shape keys move (lid and lash region, open state)"
        pts = np.vstack([shape_key_region(ob, k) for k in ("vrc.v_pp", "vrc.v_oh")])
        lm["Mouth"] = [0, float(pts[:, 1].mean()), float(np.median(pts[:, 2]))]
        meta["methods"]["Mouth"] = "median z of the vertices the PP and OH viseme keys move"
        skin = np.array(sorted({w for fc in skin_faces for w in fc}))
        h = float(lm["Crown"][2] - floor)
        pub = crotch(v[skin], 0.3 * h, 0.6 * h, h)
        if pub is None:
            meta["not_measurable"] = {"Pubis": "no leg gap found"}
        else:
            lm["Pubis"] = [0, 0, pub]
            meta["methods"]["Pubis"] = "lowest skin vertex on the midline between 30% and 60% of height, where the legs join"
        heel, toe, fx = foot_extents(v, floor, float(lm["Crown"][2] - floor), left_sign, front)
        lm["HeelBack_L"], lm["ToeTip_L"] = [fx, heel, floor], [fx, toe, floor]
        meta["methods"]["HeelBack_L/ToeTip_L"] = "y extremes of the left foot vertices below 4% of height"
        meta["pose"] = "T"
        meta["skipped"] = "Navel, Nipple: the torso is covered by clothing in this model, so they are not measurable"
    lm["_meta"] = meta
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(lm, fh, indent=2)
    print("wrote", out_path)
    for k, val in lm.items():
        if not k.startswith("_"):
            print(f"  {k:14} {[round(x, 3) for x in val]}")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[-2:]
    run(args[0], args[1])
