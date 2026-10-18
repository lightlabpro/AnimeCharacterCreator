"""q32 VRoid-standard base, MHS3 toon look (Sammy 2026-10-17: "anime models are standardized on the industry ... what you
made doesnt even look like anime"; he lifted the no-VRoid rule for this).

Run inside Blender (PC, MCP execute_blender_code):
    exec(open(r"<repo>\\blender\\head_vroid\\vroid_toon.py", encoding="utf-8").read())
    vt_import(key, glb_path)          # new scene VT_<key> with the GLB (Sketchfab VRoid export)
    vt_setup(key, rot180=True)        # toon materials, outlines, sun; rot180 for exports that face +Y
    vt_skin(key, tint=(0.90, 0.80, 0.74), ramp=(0.24, 0.36))
    vt_iris_hue(key, hue=0.72, sat=0.85, val=1.15)   # e.g. brown -> green, keeps the painted iris
    vt_facenrm(key, w=0.7)            # face normals blended toward an ellipsoid (clean anime shadow shapes)
    vt_shoot(key, tag, yaw0=180)      # front / 34 / side PNGs into datasets_work/vroid_male/renders

Base used first: 3f8f0119 "Anime Boy for Blender." by Zarya (Sketchfab, CC BY; credit in docs/reference/ATTRIBUTION.md).
All VRoid exports share one face mesh (4232 faces) and one UV layout, so face / eye textures are interchangeable -
but swapping 0fe1676a's face + iris onto 3f8f0119 scored worse (TypeSafe polished 0.50 -> 0.25), so each model keeps
its own textures and colours are changed in the shader.
The Sketchfab exports carry no shape keys: expressions must be rebuilt on the VRoid face.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Euler, Vector

DW = r"D:\Game Development\Tools\Anime Character Creator\datasets_work\vroid_male"
OUT = os.path.join(DW, "renders")
ns = bpy.app.driver_namespace


def lin(c):
    return tuple(((x / 255 + 0.055) / 1.055) ** 2.4 if x / 255 > 0.04045 else x / 255 / 12.92 for x in c)


def vt_import(key, path):
    main = bpy.context.window.scene
    sc = bpy.data.scenes.get("VT_" + key) or bpy.data.scenes.new("VT_" + key)
    bpy.context.window.scene = sc
    bpy.ops.import_scene.gltf(filepath=path)
    sc.render.resolution_x = sc.render.resolution_y = 800
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("VTW"); w.use_nodes = True; sc.world = w
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    cd = bpy.data.cameras.new("VTC"); cd.type = "ORTHO"; cd.ortho_scale = 0.36
    cam = bpy.data.objects.new("VTC", cd); sc.collection.objects.link(cam); sc.camera = cam
    bpy.context.window.scene = main
    return sc


def toon(m, shadow_tint, thr=0.30, soft=0.06, kind="skin"):
    """Texture colour lit / texture x shadow_tint in shadow (Diffuse -> Shader to RGB -> ramp), emission out; alpha
    from the texture. kind='unlit' for eyes, brows, lash lines, mouth (MToon draws these unlit)."""
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type not in ("TEX_IMAGE", "OUTPUT_MATERIAL"):
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    tx = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None)
    col = tx.outputs["Color"] if tx else None
    alpha = tx.outputs["Alpha"] if tx else None
    em = nt.nodes.new("ShaderNodeEmission")
    if kind == "unlit":
        if col:
            nt.links.new(col, em.inputs["Color"])
    else:
        dif = nt.nodes.new("ShaderNodeBsdfDiffuse"); s2r = nt.nodes.new("ShaderNodeShaderToRGB")
        nt.links.new(dif.outputs[0], s2r.inputs[0])
        ramp = nt.nodes.new("ShaderNodeValToRGB"); r = ramp.color_ramp
        r.elements[0].position = thr - soft; r.elements[0].color = (0, 0, 0, 1)
        r.elements[1].position = thr + soft; r.elements[1].color = (1, 1, 1, 1)
        bw = nt.nodes.new("ShaderNodeRGBToBW"); nt.links.new(s2r.outputs[0], bw.inputs[0]); nt.links.new(bw.outputs[0], ramp.inputs[0])
        sh = nt.nodes.new("ShaderNodeMix"); sh.data_type = "RGBA"; sh.blend_type = "MULTIPLY"; sh.inputs[0].default_value = 1.0
        if col:
            nt.links.new(col, sh.inputs[6])
        sh.inputs[7].default_value = tuple(shadow_tint) + (1,)
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; nt.links.new(ramp.outputs[0], mx.inputs[0])
        nt.links.new(sh.outputs[2], mx.inputs[6])
        if col:
            nt.links.new(col, mx.inputs[7])
        nt.links.new(mx.outputs[2], em.inputs["Color"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); ms = nt.nodes.new("ShaderNodeMixShader")
    if alpha:
        nt.links.new(alpha, ms.inputs[0])
    else:
        ms.inputs[0].default_value = 1
    nt.links.new(tr.outputs[0], ms.inputs[1]); nt.links.new(em.outputs[0], ms.inputs[2]); nt.links.new(ms.outputs[0], out.inputs["Surface"])
    m.surface_render_method = "DITHERED"          # BLENDED hid the iris behind the eye white (sorting)


def outline_mat():
    m = bpy.data.materials.get("VT_Outline")
    if m:
        return m
    m = bpy.data.materials.new("VT_Outline"); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = lin((92, 58, 44)) + (1,)
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"]); m.use_backface_culling = True
    return m


def _mats(sc, key):
    return [m for o in sc.objects if o.type == "MESH" for m in o.data.materials if m and key in m.name]


def vt_setup(key, rot180=False, light=(0.72, -0.5, 0.48), outline=0.0012):
    sc = bpy.data.scenes["VT_" + key]
    if rot180 and not sc.get("rotated"):
        for o in [o for o in sc.objects if o.parent is None and o.type not in ("CAMERA", "LIGHT")]:
            o.rotation_euler.rotate(Euler((0, 0, math.pi)))
        sc["rotated"] = 1
    for o in sc.objects:
        if o.type != "MESH":
            continue
        for m in o.data.materials:
            if not m or m.name == "VT_Outline" or m.get("vt_toon"):
                continue
            n = m.name
            if "SKIN" in n:
                toon(m, (0.62, 0.58, 0.66))           # Leo-sampled shadow / lit ratio
            elif "HAIR" in n:
                toon(m, (0.55, 0.50, 0.58), thr=0.35)
            elif "CLOTH" in n:
                toon(m, (0.5, 0.5, 0.6))
            else:
                toon(m, (1, 1, 1), kind="unlit")
            m["vt_toon"] = 1
        m0 = o.data.materials[0].name if o.data.materials and o.data.materials[0] else ""
        if any(s in m0 for s in ("Face_00_SKIN", "HAIR", "Body")) and "Outline" not in o.modifiers:
            om = outline_mat(); o.data.materials.append(om)
            md = o.modifiers.new("Outline", "SOLIDIFY"); md.thickness = outline; md.offset = 1
            md.use_flip_normals = True; md.material_offset = len(o.data.materials) - 1
    sun = bpy.data.objects.get("VT_Sun_" + key)
    if not sun:
        ld = bpy.data.lights.new("VT_Sun_" + key, "SUN"); ld.energy = 3.0; ld.angle = math.radians(0.5)
        sun = bpy.data.objects.new("VT_Sun_" + key, ld); sc.collection.objects.link(sun)
    sun.rotation_euler = Vector(light).normalized().to_track_quat('Z', 'Y').to_euler()
    for o in sc.objects:
        if o.type == "ARMATURE":
            o.data.pose_position = "REST"
    return sc


def vt_skin(key, tint=(0.90, 0.80, 0.74), ramp=(0.24, 0.36)):
    sc = bpy.data.scenes["VT_" + key]
    for m in set(_mats(sc, "Face_00_SKIN") + _mats(sc, "Body_00_SKIN")):
        nt = m.node_tree
        if not nt.nodes.get("VT_Tint"):
            tx = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
            links = [l for l in nt.links if l.from_socket == tx.outputs["Color"]]
            mul = nt.nodes.new("ShaderNodeMix"); mul.name = "VT_Tint"; mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
            mul.inputs[0].default_value = 1
            nt.links.new(tx.outputs["Color"], mul.inputs[6])
            for l in links:
                to = l.to_socket; nt.links.remove(l); nt.links.new(mul.outputs[2], to)
        nt.nodes["VT_Tint"].inputs[7].default_value = tuple(tint) + (1,)
        for n in nt.nodes:
            if n.type == "VALTORGB":
                n.color_ramp.elements[0].position, n.color_ramp.elements[1].position = ramp


def vt_iris_hue(key, hue=0.72, sat=0.85, val=1.15):
    sc = bpy.data.scenes["VT_" + key]
    for m in _mats(sc, "EyeIris"):
        nt = m.node_tree
        if not nt.nodes.get("VT_Hue"):
            tx = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
            links = [l for l in nt.links if l.from_socket == tx.outputs["Color"]]
            hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.name = "VT_Hue"
            nt.links.new(tx.outputs["Color"], hs.inputs["Color"])
            for l in links:
                to = l.to_socket; nt.links.remove(l); nt.links.new(hs.outputs[0], to)
        hs = nt.nodes["VT_Hue"]
        hs.inputs["Hue"].default_value, hs.inputs["Saturation"].default_value, hs.inputs["Value"].default_value = hue, sat, val


def _face(sc):
    return next(o for o in sc.objects if o.type == "MESH" and any("Face_00_SKIN" in (m.name if m else "") for m in o.data.materials))


def vt_facenrm(key, w=0.7):
    """Custom normals = w * ellipsoid normal (bbox of the face mesh) + (1 - w) * the mesh normal. A heavily smoothed
    proxy + data transfer was tried first: it shrank unevenly and gave blotchy shading."""
    me = _face(bpy.data.scenes["VT_" + key]).data
    if "vt_orig_n" not in me:
        me["vt_orig_n"] = np.array([v.normal[:] for v in me.vertices]).flatten().tolist()
    n0 = np.array(me["vt_orig_n"]).reshape(-1, 3)
    co = np.array([v.co[:] for v in me.vertices])
    c = (co.min(0) + co.max(0)) / 2; r = (co.max(0) - co.min(0)) / 2
    e = (co - c) / (r ** 2); e /= np.linalg.norm(e, axis=1, keepdims=True)
    n = w * e + (1 - w) * n0; n /= np.linalg.norm(n, axis=1, keepdims=True)
    me.normals_split_custom_set_from_vertices([tuple(x) for x in n])


def vt_shoot(key, tag, yaw0=0, light=(0.72, -0.5, 0.48), scale=0.36):
    main = bpy.context.window.scene
    sc = bpy.data.scenes["VT_" + key]; bpy.context.window.scene = sc; sc.render.film_transparent = True
    sun = bpy.data.objects["VT_Sun_" + key]
    a0 = math.radians(yaw0); kx, ky, kz = light
    sun.rotation_euler = Vector((kx * math.cos(a0) - ky * math.sin(a0), kx * math.sin(a0) + ky * math.cos(a0), kz)) \
        .normalized().to_track_quat('Z', 'Y').to_euler()
    f = _face(sc); c = sum((f.matrix_world @ Vector(b) for b in f.bound_box), Vector()) / 8
    cam = sc.camera; cam.data.ortho_scale = scale; outs = []
    for lab, yaw in (("front", 0), ("34", 35), ("side", 90)):
        a = math.radians(yaw0 + yaw)
        cam.location = c + Vector((math.sin(a), -math.cos(a), 0)) * 3; cam.location.z = c.z - 0.02
        cam.rotation_euler = (math.radians(90), 0, a)
        sc.render.filepath = os.path.join(OUT, "%s_%s_%s.png" % (key, tag, lab))
        bpy.ops.render.render(write_still=True); outs.append(sc.render.filepath)
    bpy.context.window.scene = main
    return outs


ns.update(vt_import=vt_import, vt_setup=vt_setup, vt_skin=vt_skin, vt_iris_hue=vt_iris_hue, vt_facenrm=vt_facenrm,
          vt_shoot=vt_shoot, vt_toon=toon)
print("vroid_toon: vt_import, vt_setup, vt_skin, vt_iris_hue, vt_facenrm, vt_shoot ready")
