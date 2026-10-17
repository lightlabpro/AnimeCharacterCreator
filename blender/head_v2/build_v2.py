"""Build the v2 head scene (bpy): SDF mesh -> quad remesh -> real mouth -> face pieces -> keys; save + preview renders.

    python(bpy) build_v2.py HEAD.npz PAINT.npz OUTPREFIX [--quads 20000] [--res 600] [--blend out.blend]
                [--expr neutral,jaw] [--views front,34,side]
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_argv = sys.argv
sys.argv = ["x"]
import view_v2 as V          # noqa: E402
import mouth_v2 as MO        # noqa: E402
sys.argv = _argv


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def flat_mat(name, srgb):
    m = bpy.data.materials.new(name); m.use_nodes = True
    col = [((c / 255.0 + 0.055) / 1.055) ** 2.4 if c / 255.0 > 0.04045 else c / 255.0 / 12.92 for c in srgb]
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*col, 1)
    return m


def identity_keys(head, eyes, ears_pieces):
    """ID- keys the app's sliders drive (contract): eye size, mouth width, jaw width, ear size.
    Head deformations are smooth fields; eye pieces scale about their eye centre and are put back on the skin."""
    import numpy as np
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    import bmesh
    me = head.data
    if me.shape_keys is None:
        head.shape_key_add(name="Basis")
    co = np.array([v.co[:] for v in me.vertices])
    x = co[:, 0] / V.H; h = (V.ZT - co[:, 2]) / V.H; y = co[:, 1] / V.H
    def add(name, newco):
        k = head.shape_key_add(name=name); k.value = 0.0
        k.data.foreach_set("co", newco.astype(np.float32).ravel())
    m = np.exp(-((x / (MO.MW * 1.6)) ** 2 + ((h - MO.MY) / 0.07) ** 2)) * (y < -0.18)
    c2 = co.copy(); c2[:, 0] *= 1 + 0.16 * m; add("ID-MouthWidth", c2)
    c2 = co.copy(); c2[:, 0] *= 1 - 0.12 * m; add("ID-MouthWidth_Neg", c2)
    jw = np.clip((h - 0.62) / 0.15, 0, 1) * np.clip((1.02 - h) / 0.05, 0, 1) * (1 - np.clip((y - 0.05) / 0.1, 0, 1))
    c2 = co.copy(); c2[:, 0] *= 1 + 0.10 * jw; add("ID-JawWidth", c2)
    c2 = co.copy(); c2[:, 0] *= 1 - 0.08 * jw; add("ID-JawWidth_Neg", c2)
    ec_y, ec_h = 0.080, 0.540                      # sdf_head.EAR centre (y, h) - bpy has no scipy to import it
    ear = (np.abs(x) > 0.33) * np.exp(-(((h - ec_h) / 0.20) ** 2 + ((y - ec_y) / 0.14) ** 2))
    root = np.stack([np.sign(x) * 0.34 * V.H, np.full_like(x, (ec_y + 0.0) * V.H),
                     np.full_like(x, V.ZT - ec_h * V.H)], 1)
    for nm, sc in (("ID-EarSize", 1.22), ("ID-EarSize_Neg", 0.82)):
        c2 = co + (co - root) * (sc - 1) * ear[:, None]; add(nm, c2)
    # eye pieces: scale about each eye's centre in x/z, then back onto the skin (ray along +y)
    bm = bmesh.new(); bm.from_mesh(me); tree = BVHTree.FromBMesh(bm); bm.free()
    for side in ("L", "R"):
        grp = [o for o in eyes if o.name.endswith("_" + side)]
        sc = [o for o in grp if "_sclera_" in o.name]
        if not sc:
            continue
        P = np.array([v.co[:] for v in sc[0].data.vertices]); cen = P.mean(0)
        for nm, s_ in (("ID-EyeSize", 1.15), ("ID-EyeSize_Neg", 0.88)):
            for o in grp:
                if o.data.shape_keys is None:
                    o.shape_key_add(name="Basis")
                k = o.shape_key_add(name=nm); k.value = 0.0
                for i, v in enumerate(o.data.vertices):
                    q = v.co.copy()
                    q.x = cen[0] + (q.x - cen[0]) * s_; q.z = cen[2] + (q.z - cen[2]) * s_
                    loc, n, idx, dist = tree.ray_cast(Vector((q.x, -1.0, q.z)), Vector((0, 1, 0)))
                    lift = (v.co - Vector(tuple(sc[0].data.vertices[0].co))).length * 0 + 0.0004
                    k.data[i].co = (loc + n * lift) if loc is not None else q


def follow_keys(head, pieces, upper_only=False):
    """Painted pieces ride on the skin: each piece vertex copies the shape-key offset of the nearest head vertex (skin
    faces only), for every key on the head. upper_only: candidates above the mouth line only (the mouth line rides
    on the upper lip; otherwise half of it latches onto the lower lip and curtains the open mouth)."""
    from mathutils.kdtree import KDTree
    me = head.data
    if not me.shape_keys:
        return
    skin = set()
    for p in me.polygons:
        if p.material_index == 0:
            skin.update(p.vertices)
    if upper_only:
        skin = {i for i in skin if (V.ZT - me.vertices[i].co.z) / V.H
                < float(MO.line_h(max(-MO.MW, min(MO.MW, me.vertices[i].co.x / V.H)))) - 0.0002}
    kd = KDTree(len(skin))
    for i in skin:
        kd.insert(me.vertices[i].co, i)
    kd.balance()
    base = me.shape_keys.key_blocks[0]
    for ob in pieces:
        idx = [kd.find(v.co)[1] for v in ob.data.vertices]
        if ob.data.shape_keys is None:
            ob.shape_key_add(name="Basis")
        have = set(ob.data.shape_keys.key_blocks.keys())
        for kb in me.shape_keys.key_blocks[1:]:
            if kb.name in have:
                continue
            k = ob.shape_key_add(name=kb.name); k.value = 0.0
            for j, v in enumerate(ob.data.vertices):
                i = idx[j]
                k.data[j].co = v.co + (kb.data[i].co - base.data[i].co)


def set_toon_normals(head, ell_mix=0.90):
    """Custom normals for toon shading (skill: transfer smooth normals from an ellipsoid proxy so the face gets one
    clean shadow shape). Per vertex: the normal of a 25x-smoothed copy blended with the normal of a broad ellipsoid
    around the head (mix ell_mix on the face, less toward ears / mouth). The geometry keeps its real curvature (the
    eye wrap that makes turned views read right); only the lighting is simplified, as anime models do.
    Mouth rim, cavity and ears keep their own normals (vertex group 'smooth_n' = how much of the toon normal)."""
    import numpy as np
    me = head.data
    prox = head.copy(); prox.data = me.copy(); bpy.context.scene.collection.objects.link(prox)
    if prox.data.shape_keys:
        prox.shape_key_clear()
    m = prox.modifiers.new("sm", "SMOOTH"); m.factor = 1.0; m.iterations = 25
    bpy.context.view_layer.objects.active = prox
    for o in bpy.context.selected_objects:
        o.select_set(False)
    prox.select_set(True)
    bpy.ops.object.modifier_apply(modifier="sm")
    ns = np.array([v.normal[:] for v in prox.data.vertices])
    bpy.data.objects.remove(prox)
    co = np.array([v.co[:] for v in me.vertices])
    gn = np.array([v.normal[:] for v in me.vertices])
    c = np.array([0.0, 0.03 * V.H, V.ZT - 0.55 * V.H]); r = np.array([0.58, 0.50, 0.66]) * V.H
    en = (co - c) / r ** 2
    en /= np.linalg.norm(en, axis=1, keepdims=True)
    x = co[:, 0] / V.H; h = (V.ZT - co[:, 2]) / V.H
    lh = MO.line_h(np.clip(x, -MO.MW, MO.MW))
    near_mouth = np.exp(-((h - lh) / 0.008) ** 2) * (np.abs(x) < MO.MW * 1.05)
    ears = np.clip((np.abs(x) - 0.33) / 0.03, 0, 1) * (np.abs(h - 0.58) < 0.2)
    neck = np.clip((h - 1.0) / 0.1, 0, 1)
    w_toon = np.clip(1 - near_mouth, 0, 1) * (1 - ears)
    w_ell = ell_mix * (1 - neck) * w_toon
    tn = ns * (1 - w_ell[:, None]) + en * w_ell[:, None]
    tn /= np.linalg.norm(tn, axis=1, keepdims=True)
    out = gn * (1 - w_toon[:, None]) + tn * w_toon[:, None]
    bad = set()
    for p in me.polygons:
        if p.material_index in (1, 2):
            bad.update(p.vertices)
    for i in bad:
        out[i] = gn[i]
    out /= np.linalg.norm(out, axis=1, keepdims=True)
    me.normals_split_custom_set_from_vertices([tuple(v) for v in out])     # baked: for the app export (static)
    # for Blender renders (live under shape keys): weights the shader / normal transfer use
    n = len(co)
    # the n56 skin material reads these: an_w (analytic-normal weight), shade (1 = lit), ear_f / ear_lw / ear_bowl
    # (ear line paint: the line shows where |ear_f - 1| < ear_lw, so ear_f = 0 means no line). v2 paints its ear
    # forms separately.
    an_w = np.clip(1 - near_mouth, 0, 1) * (1 - ears) * (1 - neck)
    for nm, arr in (("ell_w", w_ell), ("toon_w", w_toon), ("an_w", an_w), ("shade", np.ones(n)),
                    ("ear_f", np.zeros(n)), ("ear_lw", np.zeros(n)), ("ear_bowl", np.zeros(n))):
        a = me.attributes.get(nm) or me.attributes.new(nm, "FLOAT", "POINT")
        a.data.foreach_set("value", np.asarray(arr, np.float32))
    vg = head.vertex_groups.get("smooth_n") or head.vertex_groups.new(name="smooth_n")
    for i, wi in enumerate(w_toon):
        vg.add([i], 0.0 if i in bad else float(wi), "REPLACE")
    # smoothed proxy that keeps the shape keys (Smooth modifier live): its normals follow the jaw
    prox = head.copy(); prox.data = me.copy(); prox.name = "V2_HeadNrmProxy"; prox.data.name = "V2_HeadNrmProxy"
    bpy.context.scene.collection.objects.link(prox)
    m = prox.modifiers.new("sm", "SMOOTH"); m.factor = 1.0; m.iterations = 25
    prox.hide_render = True


def main():
    head_npz, paint_npz, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    res = int(arg("--res", 600))
    skin = V.scene_setup(res)
    head = V.load(head_npz)
    V.remesh(head, int(arg("--quads", 20000)))
    spacing = head.data.remesh_voxel_size
    head.data.materials.append(skin)
    head.data.materials.append(flat_mat("V2_MouthCavity", (92, 40, 42)))
    head.data.materials.append(flat_mat("V2_LipInner", (70, 34, 32)))       # reads as the mouth line when closed
    tree = MO.build_mouth(head, spacing)
    top, bot, tg = MO.build_teeth_tongue(tree)
    top.data.materials.append(flat_mat("V2_Teeth", (246, 246, 250)))
    bot.data.materials.append(top.data.materials[0])
    tg.data.materials.append(flat_mat("V2_Tongue", (196, 96, 88)))
    mats = [m for m in bpy.data.materials]
    pmats = V.load_paint(paint_npz)
    # V2MouthLine (painted, dark) stays: drawn just above the slit so it rides on the upper lip (follow_keys)
    MO.add_jaw_key(head, [bot, tg])
    MO.add_mouth_keys(head, [bot, tg])
    identity_keys(head, [o for o in bpy.data.objects if o.name.startswith("V2Eye_")],
                  [o for o in bpy.data.objects if o.name.startswith("V2Ear")])
    follow_keys(head, [o for o in bpy.data.objects if o.name.startswith(("V2Eye_", "V2Brow_", "V2Nose", "V2Lip", "V2Ear"))])
    follow_keys(head, [o for o in bpy.data.objects if o.name.startswith("V2MouthLine")], upper_only=True)
    set_toon_normals(head)
    if arg("--blend"):
        bpy.ops.wm.save_as_mainfile(filepath=arg("--blend"))
    views = arg("--views", "front,34,side").split(",")
    allm = [m for m in bpy.data.materials if m.users]
    for expr in arg("--expr", "neutral").split(","):
        val = 1.0 if expr == "jaw" else 0.0
        for ob in (head, bot, tg):
            if ob.data.shape_keys and "PF-JawOpen" in ob.data.shape_keys.key_blocks:
                ob.data.shape_keys.key_blocks["PF-JawOpen"].value = val
        V.render_toon("%s_%s" % (prefix, expr), views, allm, ortho=float(arg("--ortho", 0.30)), res=res)
        # reset material outputs to Principled for the next pass is not needed: render_toon relinks each time


if __name__ == "__main__":
    main()
