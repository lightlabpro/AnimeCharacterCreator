"""Run inside Blender (Text Editor > Run Script, or `blender -b file.blend -P blender_render_views.py -- out_dir`).
Renders fixed, repeatable views of the active character for render-validator. Never edit cameras between iterations.
Edit TARGET / HEAD_Z to frame your character once, then leave them alone."""
import bpy, sys, math, os
from mathutils import Vector

OUT = (sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else bpy.path.abspath("//validator_renders"))
os.makedirs(OUT, exist_ok=True)
RES = 1024
# name: (azimuth degrees from front, elevation degrees, framing: "body" | "head")
VIEWS = {"front": (0, 0, "body"), "three_quarter": (35, 5, "body"), "side": (90, 0, "body"),
         "back": (180, 0, "body"), "face": (0, 0, "head"), "face_three_quarter": (30, 3, "head")}

def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.visible_get() and not o.name.endswith("_shadow")]
lo, hi = bounds(meshes)
height = hi.z - lo.z
centre = (lo + hi) / 2

scene = bpy.context.scene
scene.render.resolution_x = scene.render.resolution_y = RES
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
cam_data = bpy.data.cameras.new("validator_cam"); cam_data.type = "ORTHO"
cam = bpy.data.objects.new("validator_cam", cam_data); scene.collection.objects.link(cam)
scene.camera = cam

for name, (az, el, frame) in VIEWS.items():
    if frame == "head":
        target = Vector((centre.x, centre.y, lo.z + height * 0.88)); cam_data.ortho_scale = height * 0.26
    else:
        target = centre; cam_data.ortho_scale = height * 1.12
    d = height * 4
    a, e = math.radians(az), math.radians(el)
    cam.location = target + Vector((math.sin(a) * math.cos(e) * -d * -1, -math.cos(a) * math.cos(e) * d, math.sin(e) * d))
    direction = target - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(OUT, f"r_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", scene.render.filepath)

bpy.data.objects.remove(cam)
