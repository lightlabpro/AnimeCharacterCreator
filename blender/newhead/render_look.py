"""EEVEE look renders of one new-head collection in Sammy's Blender (front, 3/4, side), everything else hidden for
the render and restored after.

    exec(open(r"...\\blender\\newhead\\render_look.py").read(), {"TAG": "n41", "OUT": r"...\\docs\\qa\\newhead\\look_n41"})
"""
import math

import bpy
from mathutils import Vector


def render(tag, out, ortho=0.40, cz=1.60, res=700):
    sc = bpy.context.scene
    col = bpy.data.collections["NEW_HEAD_" + tag]
    head = next(o for o in col.objects if o.name.startswith("NEW_Head_"))
    keep = set(col.objects)
    hidden = []
    for o in sc.objects:
        if o.type in ("MESH", "CURVE", "EMPTY") and o not in keep and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    old_cam, old = sc.camera, (sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath, sc.render.film_transparent)
    cd = bpy.data.cameras.new("LookCam"); cd.type = "ORTHO"; cd.ortho_scale = ortho
    cam = bpy.data.objects.new("LookCam", cd); sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.film_transparent = False
    tgt = Vector((head.location.x, 0.0, cz))
    paths = []
    try:
        for nm, yaw in (("front", 0), ("34", 35), ("side", 90)):
            a = math.radians(yaw)
            cam.location = tgt + Vector((math.sin(a), -math.cos(a), 0.0)) * 2.0
            cam.rotation_euler = (math.radians(90), 0.0, a)
            sc.render.filepath = "%s_%s.png" % (out, nm)
            bpy.ops.render.render(write_still=True)
            paths.append(sc.render.filepath)
    finally:
        sc.camera = old_cam
        sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath, sc.render.film_transparent = old
        bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
        for o in hidden:
            o.hide_render = False
    return paths


if "TAG" in globals():
    print(render(TAG, OUT))
