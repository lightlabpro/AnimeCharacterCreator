"""Local / PC Blender helper for the v2 head: load the SDF mesh (npz), remesh to quads, render fixed views.

    blender-python view_v2.py MESH.npz OUTPREFIX [--quads 12000] [--views front,34,side] [--res 700] [--blend out.blend]

Views match blender/newhead/session.face(): orthographic, yaw 0 / 35 / 90 degrees (camera on the -y side turning
toward +x), so v2 boards line up with the n56 boards.
"""
import math
import sys

import bpy
import numpy as np
from mathutils import Vector

ZT, H = 1.685, 0.22
VIEWS = {"front": 0.0, "34": 35.0, "side": 90.0, "back": 180.0, "top34": 35.0}


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def load(npz, name="V2_Head"):
    d = np.load(npz)
    v, f = d["v"], d["f"]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v.tolist(), [], f.tolist())
    me.validate()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def remesh(ob, quads, voxel=None):
    """Voxel quad remesh at a size that gives about `quads` faces, then shrinkwrap back onto the exact SDF surface.
    (QuadriFlow in Blender 5.0.1 kept rejecting these meshes as "not manifold" though bmesh found no bad edge, at
    every decimation tried - so it is not used.)"""
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    if quads > 0:
        src = ob.copy(); src.data = ob.data.copy(); bpy.context.scene.collection.objects.link(src)
        area = sum(p.area for p in ob.data.polygons)
        ob.data.remesh_voxel_size = voxel or (area / quads) ** 0.5
        bpy.ops.object.voxel_remesh()
        m = ob.modifiers.new("sw", "SHRINKWRAP"); m.target = src; m.wrap_method = "NEAREST_SURFACEPOINT"
        bpy.ops.object.modifier_apply(modifier="sw")
        # relax: even out the projected voxel quads, then back onto the surface (uneven quads shade as speckles
        # once a shape key moves them, because Blender keeps custom normals relative to the face normals)
        for _ in range(3):
            m = ob.modifiers.new("rl", "SMOOTH"); m.factor = 0.5; m.iterations = 4
            bpy.ops.object.modifier_apply(modifier="rl")
            m = ob.modifiers.new("sw", "SHRINKWRAP"); m.target = src; m.wrap_method = "NEAREST_SURFACEPOINT"
            bpy.ops.object.modifier_apply(modifier="sw")
        bpy.data.objects.remove(src)
        print("voxel quads", len(ob.data.polygons), "size", round(ob.data.remesh_voxel_size * 1000, 2), "mm")
    bpy.ops.object.shade_smooth()


def scene_setup(res, engine="CYCLES"):
    """Form-check lighting: a key sun from upper front-left plus a soft fill, plain matte skin. Cycles on the CPU
    (Workbench / EEVEE need a GPU, which the cloud box does not have)."""
    sc = bpy.context.scene
    sc.render.engine = engine
    if engine == "CYCLES":
        sc.cycles.device = "CPU"; sc.cycles.samples = 24; sc.cycles.use_denoising = False
        sc.cycles.max_bounces = 2
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.view_settings.view_transform = "Standard"
    w = sc.world or bpy.data.worlds.new("W"); sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.36, 0.45, 0.55, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    sun = bpy.data.lights.new("Key", "SUN"); sun.energy = 3.2; sun.angle = math.radians(3)
    so = bpy.data.objects.new("Key", sun); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-30))
    m = bpy.data.materials.new("FormSkin"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.80, 0.55, 0.42, 1); b.inputs["Roughness"].default_value = 0.7
    return m


def add_decal(mat, image_path):
    """Front projection of a paint image (x in [-0.4, 0.4] H, h in [0.30, 1.00] H) over the material's base colour."""
    nt = mat.node_tree; N = nt.nodes; Lk = nt.links
    b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); com = N.new("ShaderNodeCombineXYZ")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / (0.8 * H), 1 / (0.7 * H), 1)
    mp.inputs["Location"].default_value = (0.5, -(ZT - H) / (0.7 * H), 0)
    img = N.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(image_path); img.extension = "CLIP"
    front = N.new("ShaderNodeMath"); front.operation = "LESS_THAN"; front.inputs[1].default_value = -0.03
    mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs[6].default_value = b.inputs["Base Color"].default_value
    Lk.new(tc.outputs["Object"], sep.inputs[0])
    Lk.new(sep.outputs["X"], com.inputs["X"]); Lk.new(sep.outputs["Z"], com.inputs["Y"])
    Lk.new(com.outputs[0], mp.inputs[0]); Lk.new(mp.outputs[0], img.inputs[0])
    Lk.new(sep.outputs["Y"], front.inputs[0])
    Lk.new(img.outputs["Alpha"], mul.inputs[0]); Lk.new(front.outputs[0], mul.inputs[1])
    Lk.new(mul.outputs[0], mix.inputs[0]); Lk.new(img.outputs["Color"], mix.inputs[7])
    Lk.new(mix.outputs[2], b.inputs["Base Color"])


def load_paint(npz):
    """Face pieces from face_paint_v2.py: one object per piece, flat colour material (Principled base colour, so the
    toon preview treats it like albedo)."""
    d = np.load(npz)
    names = sorted({k.rsplit("__", 1)[0] for k in d.files})
    mats = []
    for n in names:
        v, f, c = d[n + "__v"], d[n + "__f"], d[n + "__c"]
        me = bpy.data.meshes.new(n); me.from_pydata(v.tolist(), [], f.tolist()); me.validate()
        ob = bpy.data.objects.new(n, me); bpy.context.scene.collection.objects.link(ob)
        for poly in me.polygons:
            poly.use_smooth = True
        m = bpy.data.materials.new("M_" + n); m.use_nodes = True
        col = [((ci / 255.0 + 0.055) / 1.055) ** 2.4 if ci / 255.0 > 0.04045 else ci / 255.0 / 12.92 for ci in c]
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*col, 1)
        me.materials.append(m); mats.append(m)
    return mats


def toon_setup(mat):
    """Toon preview without a GPU: the material emits either its albedo (skin + decal) or its world normal packed as a
    colour; toon_composite() turns the two renders into flat colour + one hard warm shadow + outline (numpy)."""
    nt = mat.node_tree; N = nt.nodes; Lk = nt.links
    b = N["Principled BSDF"]; out = N["Material Output"]
    em = N.new("ShaderNodeEmission")
    src = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].links else None
    if src is not None:
        Lk.new(src, em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = b.inputs["Base Color"].default_value
    geo = N.new("ShaderNodeNewGeometry")
    vm = N.new("ShaderNodeVectorMath"); vm.operation = "MULTIPLY_ADD"
    vm.inputs[1].default_value = (0.5, 0.5, 0.5); vm.inputs[2].default_value = (0.5, 0.5, 0.5)
    Lk.new(geo.outputs["Normal"], vm.inputs[0])
    emn = N.new("ShaderNodeEmission"); Lk.new(vm.outputs[0], emn.inputs["Color"])
    return em, emn, out


def render_toon(prefix, views, mat, ortho=0.30, res=700):
    import numpy as _np
    sc = bpy.context.scene
    sc.cycles.samples = 4; sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    mats = mat if isinstance(mat, list) else [mat]
    setups = [(m, toon_setup(m)) for m in mats]
    paths = {}
    for kind, idx in (("alb", 0), ("nrm", 1)):
        for m, (em, emn, out) in setups:
            m.node_tree.links.new((em, emn)[idx].outputs[0], out.inputs["Surface"])
        if kind == "nrm":
            sc.view_settings.view_transform = "Raw" if "Raw" in [i.identifier for i in
                sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Standard"
        paths[kind] = render(prefix + "_" + kind, views, ortho=ortho, res=res)
        sc.view_settings.view_transform = "Standard"
    return paths


def render(prefix, views, ortho=0.30, cz=None, res=700):
    sc = bpy.context.scene
    cz = ZT - 0.62 * H if cz is None else cz
    cd = bpy.data.cameras.new("V2Cam"); cd.type = "ORTHO"; cd.ortho_scale = ortho
    cam = bpy.data.objects.new("V2Cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    out = []
    for v in views:
        a = math.radians(VIEWS[v])
        tilt = math.radians(-15) if v == "top34" else 0.0
        cam.location = Vector((0.0, 0.0, cz)) + Vector((math.sin(a) * math.cos(tilt), -math.cos(a) * math.cos(tilt),
                                                         -math.sin(tilt))) * 2.0
        cam.rotation_euler = (math.radians(90) + tilt, 0.0, a)
        sc.render.filepath = "%s_%s.png" % (prefix, v)
        bpy.ops.render.render(write_still=True)
        out.append(sc.render.filepath)
    bpy.data.objects.remove(cam)
    return out


if __name__ == "__main__" and "--" not in sys.argv[:1]:
    npz, prefix = sys.argv[1], sys.argv[2]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    res = int(arg("--res", 700))
    mat = scene_setup(res)
    ob = load(npz)
    ob.data.materials.append(mat)
    if arg("--decal"):
        add_decal(mat, arg("--decal"))
    remesh(ob, int(arg("--quads", 12000)))
    print("faces", len(ob.data.polygons), "verts", len(ob.data.vertices))
    views = arg("--views", "front,34,side").split(",")
    allm = [mat]
    if arg("--paint"):
        allm += load_paint(arg("--paint"))
    if "--toon" in sys.argv:
        render_toon(prefix, views, allm, ortho=float(arg("--ortho", 0.30)), res=res)
    else:
        render(prefix, views, res=res, ortho=float(arg("--ortho", 0.30)))
    if arg("--blend"):
        bpy.ops.wm.save_as_mainfile(filepath=arg("--blend"))
