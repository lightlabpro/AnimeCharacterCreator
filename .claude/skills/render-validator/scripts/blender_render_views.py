"""Fixed, repeatable renders of the character for render-validator. Run inside Blender
(Text Editor > Run Script, or `blender -b file.blend -P blender_render_views.py -- out_dir`).

Renders front, three_quarter, side, back, face and face_three_quarter with orthographic cameras on a transparent
background (Standard view transform), writes r_<view>.png plus r_manifest.json, and then restores every scene setting it
touched, so your .blend is unchanged. The manifest records the camera set-up so `validate.py measure --manifest` can fail
an iteration whose cameras moved: never change cameras between iterations.

Framing: body views fit the visible character. If the head landmark empties LM_top and LM_chin exist (the same ones the
head-shape-audit skill uses), face views frame the head from them, otherwise from a proportion of the body height.
Objects whose name contains one of EXCLUDE (floors, backdrops, helpers) never affect framing.
"""
import json, math, os, sys, tempfile

RES = 1024
EXCLUDE = ("floor", "ground", "backdrop", "plane", "grid", "light", "camera", "lm_", "_shadow", "validator_cam")
# name: (azimuth degrees from the front, elevation degrees, framing "body" or "head")
VIEWS = {"front": (0, 0, "body"), "three_quarter": (35, 5, "body"), "side": (90, 0, "body"),
         "back": (180, 0, "body"), "face": (0, 0, "head"), "face_three_quarter": (30, 3, "head")}

def default_out(bpy):
    """Next to the .blend when it is saved, otherwise a folder in the home directory (an unsaved file has no '//')."""
    if bpy.data.filepath: return bpy.path.abspath("//validator_renders")
    return os.path.join(os.path.expanduser("~"), "validator_renders")

def framing(bpy):
    """Returns (centre, height, head_centre_z, head_height, used_landmarks) in world metres."""
    from mathutils import Vector
    bpy.context.view_layer.update()      # objects created or moved by a script have a stale matrix_world until this
    meshes = [o for o in bpy.context.scene.objects
              if o.type == "MESH" and o.visible_get() and not any(k in o.name.lower() for k in EXCLUDE)]
    if not meshes: raise SystemExit("No visible mesh objects to frame (names containing %s are ignored)." % ", ".join(EXCLUDE))
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    height = hi.z - lo.z
    top, chin = bpy.data.objects.get("LM_top"), bpy.data.objects.get("LM_chin")
    if top and chin and top.matrix_world.translation.z > chin.matrix_world.translation.z:
        tz, cz = top.matrix_world.translation.z, chin.matrix_world.translation.z
        return (lo + hi) / 2, height, (tz + cz) / 2, tz - cz, True
    return (lo + hi) / 2, height, lo.z + height * 0.90, height * 0.15, False

def render_views(out_dir, views=VIEWS, res=RES):
    import bpy
    from mathutils import Vector
    scene = bpy.context.scene; r = scene.render
    saved = {"x": r.resolution_x, "y": r.resolution_y, "pct": r.resolution_percentage, "transp": r.film_transparent,
             "fmt": r.image_settings.file_format, "mode": r.image_settings.color_mode, "path": r.filepath,
             "view": scene.view_settings.view_transform, "cam": scene.camera}
    os.makedirs(out_dir, exist_ok=True)
    centre, height, head_z, head_h, landmarks = framing(bpy)
    cam_data = bpy.data.cameras.new("validator_cam"); cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("validator_cam", cam_data); scene.collection.objects.link(cam)
    manifest = {"blender": bpy.app.version_string, "engine": r.engine, "resolution": res, "view_transform": "Standard",
                "head_from_landmarks": landmarks, "character_height": round(height, 5), "head_height": round(head_h, 5), "views": {}}
    try:
        r.resolution_x = r.resolution_y = res; r.resolution_percentage = 100
        r.film_transparent = True; r.image_settings.file_format = "PNG"; r.image_settings.color_mode = "RGBA"
        scene.view_settings.view_transform = "Standard"; scene.camera = cam
        for name, (az, el, frame) in views.items():
            if frame == "head":
                target = Vector((centre.x, centre.y, head_z)); scale = head_h * 1.9
            else:
                target = centre.copy(); scale = height * 1.12
            cam_data.ortho_scale = scale
            a, e = math.radians(az), math.radians(el)
            d = height * 4
            cam.location = target + Vector((math.sin(a) * math.cos(e) * d, -math.cos(a) * math.cos(e) * d, math.sin(e) * d))
            cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
            r.filepath = os.path.join(out_dir, f"r_{name}.png")
            bpy.ops.render.render(write_still=True)
            manifest["views"][name] = {"azimuth": az, "elevation": el, "frame": frame, "ortho_scale": round(scale, 5),
                                       "target": [round(v, 5) for v in target], "file": f"r_{name}.png"}
            print("rendered", r.filepath)
    finally:
        r.resolution_x, r.resolution_y, r.resolution_percentage = saved["x"], saved["y"], saved["pct"]
        r.film_transparent = saved["transp"]; r.image_settings.file_format = saved["fmt"]; r.image_settings.color_mode = saved["mode"]
        r.filepath = saved["path"]; scene.view_settings.view_transform = saved["view"]; scene.camera = saved["cam"]
        bpy.data.objects.remove(cam); bpy.data.cameras.remove(cam_data)
    with open(os.path.join(out_dir, "r_manifest.json"), "w") as f: json.dump(manifest, f, indent=2)
    return manifest

def main():
    import bpy
    out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else default_out(bpy)
    render_views(out)

if __name__ == "__main__":
    main()
