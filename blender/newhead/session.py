"""Session helpers for the new-head work in Sammy's Blender (persisted so a Blender restart loses nothing).

    exec(open(r"<repo>\\blender\\newhead\\session.py").read())

Registers in bpy.app.driver_namespace (call them as ns["apply"](), ...):
  apply(tag="n56")                  rebuild the look (apply_look.py: rig, expressions, view keys) on new_head_<tag>.npz
  shots(name, views, expr, yaw...)  EEVEE renders of the collection only, written to docs/qa/newhead/<name>_<label>.png
  look(name) / face(name) / eyes(name) / nose(name) / ears(name)   preset framings (front, 3/4, side)
  zoom(name, exprs, yaws)           close-up of the character's left eye for each expression
  sweep(name, yaws)                 face at several camera yaws with the view keys set
  knobs(update)                     deep-merge into blender/newhead/look_knobs.json ("paint", "view" are dicts)
  judge(analysis, region, out, exclude="", images=None)   TypeSafe judge v2 (blender/tools/typesafe_visual_judge.py)
  box(image, out, targets, refine)  TypeSafe Box measurements (blender/tools/typesafe_box.py)
The system Python launcher `py` (3.13 with Pillow) runs the TypeSafe scripts; Blender's own Python has no Pillow.
"""
import json
import math
import os
import subprocess

import bpy
from mathutils import Vector

R = r"D:\Game Development\Tools\Anime Character Creator\AnimeCharacterCreator-main"
NH = os.path.join(R, "blender", "newhead")
Q = os.path.join(R, "docs", "qa", "newhead")
TOOLS = os.path.join(R, "blender", "tools")
OFF_X = 2.4
ns = bpy.app.driver_namespace


def col(tag="n56"):
    return bpy.data.collections["NEW_HEAD_" + tag]


def head(tag="n56"):
    return next(o for o in col(tag).objects if o.name.startswith("NEW_Head_"))


def apply(tag="n56", npz_tag=None):
    npz_tag = npz_tag or tag
    for c in bpy.data.collections:
        if c.name.startswith("NEW_HEAD_") and c.name != "NEW_HEAD_" + tag:
            c.hide_render = True; c.hide_viewport = True
    g = {"NPZ": os.path.join(Q, "new_head_%s.npz" % npz_tag), "EYES": os.path.join(Q, "new_head_%s_eyes.json" % npz_tag),
         "TAG": tag, "OFF_X": OFF_X, "__name__": "apply_look"}
    exec(open(os.path.join(NH, "apply_look.py")).read(), g)
    c = col(tag); c.hide_render = False; c.hide_viewport = False
    ns["LOOK_G"] = g
    return g


def set_state(c, expr=None, yaw=0.0):
    if "set_expression" in ns:
        ns["set_expression"](c, expr or "neutral")
    if "set_view" in ns:
        ns["set_view"](c, yaw)


def shots(name, views, expr=None, tag="n56", view_keys=True, res=700):
    """views: [(label, yaw_deg, ortho, dx, cz)] - dx shifts the target sideways from the head centre (m)."""
    sc = bpy.context.scene
    c = col(tag); h = head(tag)
    keep = set(c.all_objects)
    hidden = [o for o in sc.objects if o.type in ("MESH", "CURVE", "EMPTY") and o not in keep and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    ch = c.hide_render; c.hide_render = False
    old_cam, old = sc.camera, (sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath)
    cd = bpy.data.cameras.new("SessCam"); cd.type = "ORTHO"
    cam = bpy.data.objects.new("SessCam", cd); sc.collection.objects.link(cam); sc.camera = cam
    sc.render.resolution_x = sc.render.resolution_y = res
    out = []
    try:
        for label, yaw, ortho, dx, cz in views:
            set_state(c, expr, yaw if view_keys else 0.0)
            a = math.radians(yaw)
            cd.ortho_scale = ortho
            tgt = Vector((h.location.x + dx * math.cos(a), dx * math.sin(a), cz))
            cam.location = tgt + Vector((math.sin(a), -math.cos(a), 0.0)) * 2.0
            cam.rotation_euler = (math.radians(90), 0.0, a)
            sc.render.filepath = os.path.join(Q, "%s_%s.png" % (name, label))
            bpy.context.view_layer.update()
            bpy.ops.render.render(write_still=True)
            out.append(sc.render.filepath)
    finally:
        set_state(c, None, 0.0)
        sc.camera = old_cam
        sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath = old
        bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
        c.hide_render = ch
        for o in hidden:
            o.hide_render = False
    return out


def look(name, expr=None):
    return shots(name, [("front", 0, 0.40, 0, 1.60), ("34", 35, 0.40, 0, 1.60), ("side", 90, 0.40, 0, 1.60)], expr)


def face(name, expr=None):
    return shots(name, [("front", 0, 0.26, 0, 1.575), ("34", 35, 0.26, 0, 1.575), ("side", 90, 0.26, 0, 1.575)], expr, res=600)


def eyes(name, expr=None):
    return shots(name, [("front", 0, 0.19, 0, 1.608), ("34", 35, 0.19, 0, 1.608)], expr)


def nose(name, expr=None):
    return shots(name, [("front", 0, 0.12, 0, 1.53), ("34", 35, 0.12, 0, 1.53), ("side", 90, 0.12, 0, 1.53)], expr)


def ears(name, expr=None):
    return shots(name, [("side", 90, 0.14, 0.0, 1.60), ("34b", 135, 0.18, 0.0, 1.60), ("front", 0, 0.30, 0, 1.60)], expr)


def zoom(name, exprs=("neutral", "blink", "wink_left", "amazed", "sad", "angry", "happy"), yaws=(0,), ortho=0.075):
    out = []
    for e in exprs:
        for y in yaws:
            out += shots(name, [("%s_y%03d" % (e, y % 360), y, ortho, 0.0545, 1.612)], e, res=900)
    return out


def sweep(name, yaws=(0, 12, 30, 50, 70, 90), expr=None):
    return shots(name, [("y%03d" % (y % 360), y, 0.26, 0, 1.575) for y in yaws], expr, res=600)


def knobs(update):
    p = os.path.join(NH, "look_knobs.json")
    k = json.load(open(p)) if os.path.exists(p) else {}
    for a, b in update.items():
        if isinstance(b, dict) and isinstance(k.get(a), dict):
            k[a].update(b)
        elif b is None:
            k.pop(a, None)
        else:
            k[a] = b
    json.dump(k, open(p, "w"), indent=1)
    return k


def _py(args, timeout=900):
    r = subprocess.run(["py", "-3"] + args, capture_output=True, text=True, timeout=timeout)
    return (r.stdout + ("\nERR " + r.stderr[-2000:] if r.returncode else "")).strip()


def judge(analysis, region, out, exclude="", images=None, model=None):
    a = [os.path.join(TOOLS, "typesafe_visual_judge.py"), os.path.join(Q, analysis) if not os.path.isabs(analysis) else analysis,
         os.path.join(TOOLS, "visual_corrections", region + ".json"), os.path.join(Q, out) if not os.path.isabs(out) else out]
    if exclude:
        a += ["--exclude", exclude]
    if images:
        a += ["--images", ",".join(os.path.join(Q, i) if not os.path.isabs(i) else i for i in images)]
    if model:
        a += ["--model", model]
    return _py(a)


def box(image, out, targets, refine=False):
    a = [os.path.join(TOOLS, "typesafe_box.py"), os.path.join(Q, image) if not os.path.isabs(image) else image,
         os.path.join(Q, out)] + ["%s=%s" % kv for kv in targets.items()]
    if refine:
        a.append("--refine")
    return _py(a)


for _f in (col, head, apply, shots, look, face, eyes, nose, ears, zoom, sweep, knobs, judge, box, set_state):
    ns[_f.__name__] = _f
ns["Q"], ns["NH"], ns["R"] = Q, NH, R
print("session helpers ready")
