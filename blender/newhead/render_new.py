"""Clay render of an npz mesh with bpy (Cycles CPU): python3 render.py mesh.npz out.png"""
import sys, math, numpy as np, bpy
npz, out = sys.argv[1], sys.argv[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
d = np.load(npz); V = d["V"]; PL, PS = d["PL"], d["PS"]
faces, o = [], 0
for n in PS: faces.append(list(PL[o:o + n])); o += n
me = bpy.data.meshes.new("m"); me.from_pydata(V.tolist(), [], faces); me.update()
for p in me.polygons: p.use_smooth = True
ob = bpy.data.objects.new("m", me); bpy.context.scene.collection.objects.link(ob)
try:
    ob.shadow_terminator_geometry_offset = 0.6   # Cycles terminator artifact on coarse smooth-shaded quads
except AttributeError:
    pass
import os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "scripts"))
import json as _json
_ej = npz.replace(".npz", "_eyes.json")
if _os.path.exists(_ej):
    _e = _json.load(open(_ej))
    for c in _e["eyes"]:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=_e["eye_r"], location=c, segments=32, ring_count=16)
        bpy.ops.object.shade_smooth()
mat = bpy.data.materials.new("clay"); mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1); mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
me.materials.append(mat)
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.cycles.device = "CPU"
sc.render.resolution_x = 520; sc.render.resolution_y = 620
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.25, 0.25, 0.27, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
for rot, en in (((50, 0, -35), 3.0), ((60, 0, 140), 1.2)):
    l = bpy.data.lights.new("s", "SUN"); l.energy = en; lo = bpy.data.objects.new("s", l); lo.rotation_euler = [math.radians(a) for a in rot]; sc.collection.objects.link(lo)
cam = bpy.data.cameras.new("c"); cam.type = "ORTHO"; cam.ortho_scale = 0.36
co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co); sc.camera = co
imgs = []
import os
for nm, yaw in (("front", 0), ("34", 40), ("side", 90)):
    a = math.radians(yaw)
    co.location = (math.sin(a) * 1.0, -math.cos(a) * 1.0, 1.60)
    co.rotation_euler = (math.radians(90), 0, a)
    p = out.replace(".png", f"_{nm}.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True); imgs.append(p)
from PIL import Image
ims = [Image.open(p) for p in imgs]; W_ = sum(i.width for i in ims); c = Image.new("RGB", (W_, ims[0].height))
x = 0
for i in ims: c.paste(i, (x, 0)); x += i.width
c.save(out)
