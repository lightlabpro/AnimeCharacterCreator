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
  audit(prefix, out, exprs)         TypeSafe expression audit on the zoom() close-ups (rubric, pictures)
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
    for hc in bpy.data.collections:                      # h-series: the hair pieces render with the head
        if hc.name.startswith("NEW_HAIR_") and hc.name.endswith("_" + tag) and not hc.hide_render:
            keep |= set(hc.all_objects)
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


def zoom(name, exprs=("neutral", "blink", "wink_left", "amazed", "sad", "angry", "happy"), yaws=(0,), ortho=0.065, dx=0.0485):
    out = []
    for e in exprs:
        for y in yaws:
            out += shots(name, [("%s_y%03d" % (e, y % 360), y, ortho, dx, 1.612)], e, res=900)
    return out


def sweep(name, yaws=(0, 12, 30, 50, 70, 90), expr=None):
    return shots(name, [("y%03d" % (y % 360), y, 0.26, 0, 1.575) for y in yaws], expr, res=600)


def hair(style="leo", tag="n56"):
    """h-series: build the clump hair (blender/newhead/hair_nh.py) on the current (baked) head."""
    g = {"__name__": "hair_nh", "HAIR_PATH": os.path.join(NH, "hair_nh.py")}
    exec(open(os.path.join(NH, "hair_nh.py")).read(), g)
    return g["build_hair"](style, tag, OFF_X)


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


def audit(prefix, out, exprs=("neutral", "blink", "wink_left", "amazed", "sad", "angry", "happy"), yaw=0):
    """TypeSafe expression audit (blender/tools/typesafe_expr_audit.py) on the zoom(prefix) close-ups."""
    a = [os.path.join(TOOLS, "typesafe_expr_audit.py"), os.path.join(Q, out)]
    a += ["%s=%s" % (e, os.path.join(Q, "%s_%s_y%03d.png" % (prefix, e, yaw))) for e in exprs]
    a += ["reference=" + os.path.join(Q, "ref_eye_near.png")]      # calibration: the MHS3 eye scored the same way
    return _py(a)


for _f in (hair, audit, col, head, apply, shots, look, face, eyes, nose, ears, zoom, sweep, knobs, judge, box, set_state):
    ns[_f.__name__] = _f
ns["Q"], ns["NH"], ns["R"] = Q, NH, R
# ---- q12/q13 helpers: A/B variants, plain-shaded form renders, wireframe renders ----
import contextlib
import io
import shutil

AB = os.path.join(R, "_ab")


def ab_build(v, patches=(), base="now"):
    """Rebuild the head from a patched copy of the scripts in _ab/<v>/ (patches: [(file, old, new)], each old must
    occur once). base="morning" overlays _ab/morning_src/. Hair is hidden. Returns (seconds, log tail)."""
    import time
    root = os.path.join(AB, v); bn = os.path.join(root, "blender", "newhead"); dq = os.path.join(root, "docs", "qa", "newhead")
    os.makedirs(bn, exist_ok=True); os.makedirs(dq, exist_ok=True)
    for f in os.listdir(NH):
        if f.endswith((".py", ".json", ".npz")):
            shutil.copy(os.path.join(NH, f), bn)
    if base == "morning":
        src = os.path.join(AB, "morning_src")
        for f in os.listdir(src):
            shutil.copy(os.path.join(src, f), bn)
    for f in ("new_head_n56.npz", "new_head_n56_eyes.json"):
        shutil.copy(os.path.join(Q, f), dq)
    for fn, old, new in patches:
        p_ = os.path.join(bn, fn); t = open(p_, encoding="utf-8").read()
        assert t.count(old) == 1, (v, fn, old, t.count(old))
        open(p_, "w", encoding="utf-8").write(t.replace(old, new))
    for c in bpy.data.collections:
        if c.name.startswith(("NEW_HAIR_", "HAIR_")):
            c.hide_render = True
    g = {"NPZ": os.path.join(dq, "new_head_n56.npz"), "EYES": os.path.join(dq, "new_head_n56_eyes.json"),
         "TAG": "n56", "OFF_X": OFF_X, "__name__": "apply_look"}
    t0 = time.time(); buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(open(os.path.join(bn, "apply_look.py"), encoding="utf-8").read(), g)
    c = col("n56"); c.hide_render = False; c.hide_viewport = False
    ns["LOOK_G"] = g
    for o in bpy.data.objects:
        if o.name.startswith(("Hair_", "HAIR_")):
            o.hide_render = True
    return time.time() - t0, buf.getvalue()[-600:]


def _tmp_copies(tag, parts):
    c = col(tag); dg = bpy.context.evaluated_depsgraph_get(); out = []
    srcs = [head(tag)] + [o for o in c.objects if o.name.startswith("NEW_Ears")]
    if parts:
        srcs += [o for o in c.objects if o.name.startswith(("RigEyeWhite_", "RigIris_", "RigLidLine_", "RigBrow_"))]
    for o in srcs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        t = bpy.data.objects.new("TMP_" + o.name, me); t.matrix_world = o.matrix_world; c.objects.link(t)
        out.append((o, t))
    return out


def _plain_render(name, views, res, tag, mode, parts):
    sc = bpy.context.scene; c = col(tag); sh = sc.display.shading; eng = sc.render.engine
    old = (sh.light, sh.color_type, tuple(sh.single_color), sh.show_cavity)
    hc = [x for x in bpy.data.collections if x.name.startswith(("NEW_HAIR_", "HAIR_")) and not x.hide_render]
    for x in hc:
        x.hide_render = True
    hid = [o for o in c.all_objects if not o.hide_render]
    for o in hid:
        o.hide_render = True
    tmp = []
    for o, t in _tmp_copies(tag, parts):
        tmp.append(t)
        if mode == "form":
            with bpy.context.temp_override(object=t, active_object=t, selected_objects=[t]):
                try:
                    bpy.ops.mesh.customdata_custom_splitnormals_clear()
                except Exception:
                    pass
            for p_ in t.data.polygons:
                p_.use_smooth = True
        elif o.name.startswith(("NEW_Head", "NEW_Ears")):
            t.color = (0.78, 0.78, 0.78, 1)
            w = bpy.data.objects.new("TMP_w_" + o.name, t.data); w.matrix_world = o.matrix_world; c.objects.link(w)
            m = w.modifiers.new("wf", "WIREFRAME"); m.thickness = 0.00025; m.use_replace = True
            w.color = (0.08, 0.08, 0.1, 1); tmp.append(w)
        else:
            t.color = (0.3, 0.6, 0.3, 1) if o.name.startswith("RigIris_") else (
                (0.95, 0.95, 0.95, 1) if o.name.startswith("RigEyeWhite_") else (0.35, 0.22, 0.15, 1))
    sc.render.engine = "BLENDER_WORKBENCH"
    if mode == "form":
        sh.light = "STUDIO"; sh.color_type = "SINGLE"; sh.single_color = (0.8, 0.8, 0.8)
    else:
        sh.light = "FLAT"; sh.color_type = "OBJECT"
    sh.show_cavity = False
    try:
        return shots(name, views, res=res, view_keys=False)
    finally:
        sc.render.engine = eng
        for o in hid:
            o.hide_render = False
        for x in hc:
            x.hide_render = False
        meshes = {t.data for t in tmp}
        for t in tmp:
            bpy.data.objects.remove(t)
        for me in meshes:
            if me.users == 0:
                bpy.data.meshes.remove(me)
        sh.light, sh.color_type = old[0], old[1]; sh.single_color = old[2]; sh.show_cavity = old[3]


def formshots(name, views, res=600, tag="n56"):
    """q13: the real form - Workbench studio light, custom normals cleared, no toon paint, no outline shell."""
    return _plain_render(name, views, res, tag, "form", False)


def wireshots(name, views, res=900, tag="n56", parts=True):
    """q13: flat grey faces + wireframe (eye white / iris / lid / brow flat-coloured) - see every face."""
    return _plain_render(name, views, res, tag, "wire", parts)


def wire_view(name, yaw, ortho, dx, cz, res=900, tag="n56"):
    """Wireframe with the view keys set for this yaw (how the eye parts actually deform off-front)."""
    c = col(tag); set_state(c, None, yaw); bpy.context.view_layer.update()
    try:
        return wireshots(name, [("y%03d" % yaw, yaw, ortho, dx, cz)], res=res, tag=tag)
    finally:
        set_state(c, None, 0.0)


def mk(out, prefix, sfx):
    """Side-by-side pair _ab/ab_<out>_pair.png from docs/qa/newhead/<prefix>_<sfx>.png (600 px each)."""
    code = ("import sys\nfrom PIL import Image\nQ, AB, out, prefix = sys.argv[1:5]\nsfx = sys.argv[5:]\n"
            "b = Image.new('RGB', (600 * len(sfx), 600), 'white')\n"
            "for j, s in enumerate(sfx):\n    b.paste(Image.open(Q + '/%s_%s.png' % (prefix, s)).convert('RGB').resize((600, 600)), (j * 600, 0))\n"
            "b.save(AB + '/ab_%s_pair.png' % out)\n")
    os.makedirs(AB, exist_ok=True)
    pth = os.path.join(AB, "mkpair2.py"); open(pth, "w").write(code)
    return _py([pth, Q, AB, out, prefix] + list(sfx))


def ab2(a, b, ref="ref_pair", aspects=None):
    """TypeSafe A/B (typesafe_ab_compare.py) of _ab/ab_<a>_pair.png vs ab_<b>_pair.png against _ab/<ref>.png."""
    out = os.path.join(AB, "ts_%s_vs_%s.json" % (a, b))
    args = [os.path.join(TOOLS, "typesafe_ab_compare.py"), out, "A=" + os.path.join(AB, "ab_%s_pair.png" % a),
            "B=" + os.path.join(AB, "ab_%s_pair.png" % b), "REF=" + os.path.join(AB, ref + ".png")]
    if aspects:
        args += ["--aspects", aspects]
    return _py(args, timeout=300)


for _f in (ab_build, formshots, wireshots, wire_view, mk, ab2):
    ns[_f.__name__] = _f
print("session helpers ready")
