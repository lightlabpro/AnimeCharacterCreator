"""Ear close-ups: python3 render_ear.py mesh.npz out.png  (env OS, TY, TZ; views side, back34, front, top)"""
import sys, math, os, numpy as np, bpy
from mathutils import Vector
npz, out = sys.argv[1], sys.argv[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
d = np.load(npz); V = d["V"]; PL, PS = d["PL"], d["PS"]
faces, o = [], 0
for n in PS: faces.append(list(PL[o:o + n])); o += n
me = bpy.data.meshes.new("m"); me.from_pydata(V.tolist(), [], faces); me.update()
for p in me.polygons: p.use_smooth = True
ob = bpy.data.objects.new("m", me); bpy.context.scene.collection.objects.link(ob)
ob.shadow_terminator_geometry_offset = 0.6
mat = bpy.data.materials.new("clay"); mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1)
me.materials.append(mat)
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 24
sc.render.resolution_x = 420; sc.render.resolution_y = 420
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.25, 0.25, 0.27, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
for rot, en in (((50, 0, 60), 3.0), ((60, 0, -140), 1.2)):
    l = bpy.data.lights.new("s", "SUN"); l.energy = en; lo = bpy.data.objects.new("s", l); lo.rotation_euler = [math.radians(a) for a in rot]; sc.collection.objects.link(lo)
cam = bpy.data.cameras.new("c"); cam.type = "ORTHO"; cam.ortho_scale = float(os.environ.get("OS", "0.12"))
co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co); sc.camera = co
T = Vector((0.085, float(os.environ.get("EAR_TY", "0.035")), float(os.environ.get("EAR_TZ", "1.595"))))
imgs = []
for nm, dirv in (("side", (1, 0, 0)), ("back34", (0.7, 0.7, 0.1)), ("front", (0.25, -1, 0)), ("top", (0.3, 0.1, 1))):
    dv = Vector(dirv).normalized()
    co.location = T + dv * 1.0
    co.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
    p = out.replace(".png", f"_{nm}.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True); imgs.append(p)
from PIL import Image
ims = [Image.open(p) for p in imgs]; c = Image.new("RGB", (sum(i.width for i in ims), ims[0].height)); x = 0
for i in ims: c.paste(i, (x, 0)); x += i.width
c.save(out)
