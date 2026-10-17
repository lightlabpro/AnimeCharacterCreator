"""Sammy's Blender (5.2): bring the v2 head in from the cloud-built .blend and shade it with the shipped toon look.

    exec(open(r"<repo>\\blender\\head_v2\\pc_v2.py").read(), {"BLEND": r"...\\v2.blend", "TAG": "v2"})
    then bpy.app.driver_namespace["v2"]["shots"](name, expr)   # front / 3/4 / side, same cameras as n56 face()

- appends every object of BLEND into collection NEW_HEAD_<TAG> (replacing an older one), hides it from the n56
  renders and hides the n56 head from the v2 renders;
- skin: the n56 toon group (NG_ToonSkin_NewHead) with the n56 skin colour and no masks; painted pieces, teeth, tongue,
  cavity: flat emission (like the n56 rig pieces); outline: an inverted-hull Solidify with the n56 outline material.
"""
import math
import os

import bpy
from mathutils import Vector

BLEND = globals()["BLEND"]
TAG = globals().get("TAG", "v2")
R = globals().get("REPO") or r"D:\Game Development\Tools\Anime Character Creator\AnimeCharacterCreator-main"
Q = os.path.join(R, "docs", "qa", "head_v2")
ZT, H = 1.685, 0.22


def lin(c):
    c = c / 255.0
    return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92


def emission_mat(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission"); out = nt.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Color"].default_value = rgba; em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def skin_mat():
    """The n56 skin material itself (NG_ToonSkin_NewHead fed by n56's analytic normal: an ellipsoid plus a forward
    push over the face front, chin to forehead, mixed with the surface normal by 'an_w'), with its head-size
    constants moved to v2 (head height 0.262 -> H, base height 1.4826 -> chin ZT - H). Same light, same look."""
    name = "MAT_V2Skin_" + TAG
    old = bpy.data.materials.get(name)
    if old:
        bpy.data.materials.remove(old)
    m = bpy.data.materials["MAT_NewSkin_n56"].copy(); m.name = name
    for n in m.node_tree.nodes:
        if n.type == "MATH":
            for i in n.inputs[:2]:
                if i.is_linked:
                    continue
                if abs(i.default_value - 0.262) < 1e-4:
                    i.default_value = H
                elif abs(i.default_value - 1.4826) < 1e-4:
                    i.default_value = ZT - H
    return m


def import_blend():
    cname = "NEW_HEAD_" + TAG
    old = bpy.data.collections.get(cname)
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o)
        bpy.data.collections.remove(old)
    col = bpy.data.collections.new(cname); bpy.context.scene.collection.children.link(col)
    with bpy.data.libraries.load(BLEND, link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    for o in dst.objects:
        if o is None or o.type != "MESH":
            continue
        col.objects.link(o)
    return col


def shade(col):
    skin = skin_mat()
    outline = bpy.data.materials["MAT_Outline_NewHead_n56"]
    for o in col.objects:
        base = o.name.split(".")[0]
        if base == "V2_HeadNrmProxy":
            continue
        if base == "V2_Head":
            mats = list(o.data.materials)
            o.data.materials[0] = skin
            for i, m in enumerate(mats[1:], 1):
                c = m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
                o.data.materials[i] = emission_mat("MAT_%s_%s" % (m.name.split(".")[0], TAG), tuple(c))
            prox = next((p for p in col.objects if p.name.startswith("V2_HeadNrmProxy")), None)
            # Blender renders: drop the baked custom normals (they are carried through shape keys in noisy
            # per-face spaces -> speckles where the jaw moves) and take live normals from the smoothed proxy
            bpy.context.view_layer.objects.active = o
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
                bpy.ops.mesh.customdata_custom_splitnormals_clear()
            if prox is not None:
                prox.hide_render = True
                dt = o.modifiers.new("SmoothNormals", "DATA_TRANSFER"); dt.object = prox
                dt.use_loop_data = True; dt.data_types_loops = {"CUSTOM_NORMAL"}
                dt.loop_mapping = "POLYINTERP_NEAREST"; dt.vertex_group = "smooth_n"
            o.data.materials.append(outline)
            sm = o.modifiers.new("Outline", "SOLIDIFY"); sm.thickness = 0.0009; sm.offset = 1.0
            sm.use_flip_normals = True; sm.use_rim = False; sm.material_offset = len(o.data.materials) - 1
            o.data.name = "V2_Head_" + TAG; o.name = "V2_Head_" + TAG
        else:
            m = o.data.materials[0]
            c = m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
            o.data.materials[0] = emission_mat("MAT_%s_%s" % (base, TAG), tuple(c))
            if base.startswith(("V2Teeth", "V2Tongue")):
                o.data.materials.append(outline)
                sm = o.modifiers.new("Outline", "SOLIDIFY"); sm.thickness = 0.0004; sm.offset = 1.0
                sm.use_flip_normals = True; sm.use_rim = False; sm.material_offset = 1


def set_expr(col, expr):
    vals = {"neutral": {}, "jaw": {"PF-JawOpen": 1.0}, "jaw_half": {"PF-JawOpen": 0.5}}[expr]
    for o in col.objects:
        sk = o.data.shape_keys
        if sk:
            for kb in sk.key_blocks[1:]:
                kb.value = vals.get(kb.name, 0.0)


def shots(name, expr="neutral", views=(("front", 0), ("34", 35), ("side", 90)), ortho=0.30, cz=ZT - 0.62 * H,
          res=600, dx=0.0):
    sc = bpy.context.scene
    col = bpy.data.collections["NEW_HEAD_" + TAG]
    keep = set(col.objects)
    hidden = [o for o in sc.objects if o.type in ("MESH", "CURVE", "EMPTY") and o not in keep and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    ch = col.hide_render; col.hide_render = False
    old_cam, old = sc.camera, (sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath)
    cd = bpy.data.cameras.new("V2Cam"); cd.type = "ORTHO"; cd.ortho_scale = ortho
    cam = bpy.data.objects.new("V2Cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    sc.render.resolution_x = sc.render.resolution_y = res
    os.makedirs(Q, exist_ok=True)
    out = []
    try:
        set_expr(col, expr)
        for label, yaw in views:
            a = math.radians(yaw)
            tgt = Vector((dx * math.cos(a), dx * math.sin(a), cz))
            cam.location = tgt + Vector((math.sin(a), -math.cos(a), 0.0)) * 2.0
            cam.rotation_euler = (math.radians(90), 0.0, a)
            sc.render.filepath = os.path.join(Q, "%s_%s.png" % (name, label))
            bpy.context.view_layer.update()
            bpy.ops.render.render(write_still=True)
            out.append(sc.render.filepath)
    finally:
        set_expr(col, "neutral")
        sc.camera = old_cam
        sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath = old
        bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
        col.hide_render = ch
        for o in hidden:
            o.hide_render = False
    return out


col = import_blend()
shade(col)
col.hide_render = True                     # n56 renders stay as they were
bpy.app.driver_namespace["v2"] = {"shots": shots, "set_expr": set_expr, "col": col}
print("v2 imported:", len(col.objects), "objects")
