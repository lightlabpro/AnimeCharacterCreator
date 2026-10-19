"""quick local preview: workbench renders (front, 3/4, side) of a glb's head region.
    bpyenv/bin/python blender/head_scratch/preview.py IN.glb OUT_PREFIX [z_center] [size]"""
import bpy, sys, math
from mathutils import Vector, Euler
a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
src, pre = a[0], a[1]; zc = float(a[2]) if len(a) > 2 else 1.62; size = float(a[3]) if len(a) > 3 else 0.32
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
sc.display.shading.show_cavity = False; sc.display.shading.show_object_outline = True
sc.render.resolution_x = sc.render.resolution_y = 700
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = size
for name, yaw in (("front", 0), ("34", 35), ("side", 90)):
    r = 1.0; ang = math.radians(yaw)
    cam.location = Vector((r * math.sin(ang), r * math.cos(ang), zc))
    cam.rotation_euler = Euler((math.radians(90), 0, math.radians(180) - ang))
    sc.render.filepath = "%s_%s.png" % (pre, name)
    bpy.ops.render.render(write_still=True)
print("ok")
