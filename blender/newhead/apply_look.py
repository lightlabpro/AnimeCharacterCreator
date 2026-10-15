"""MHS3 look on a new-head build, inside Sammy's Blender (uses the project's NG_ toon groups from blender/scripts/shaders.py).

    exec(open(r"...\\blender\\newhead\\apply_look.py").read(), {"NPZ": npz_path, "EYES": eyes_json, "TAG": "n41", "OFF_X": 1.8})

- Loads the head (npz: V, PL, PS, ear_dark) and the eyeball centres, as collection NEW_HEAD_<TAG>, offset OFF_X in x.
- Skin: NG_ToonSkin; Shadow Mask from a "shade" point attribute (1 lit, 0 forced shadow): ear bowl and rim groove,
  under the nose tip, the jaw underside and the neck right under the jaw (MHS3: the head shades the upper neck).
- Normals: face normals blended toward a head ellipsoid (one clean shadow shape, no nose/cheek noise); the neck toward
  its cylinder; ears and the eye/mouth rims keep their own.
- Eyes (n45): painted, MHS3-style: a thin plate flush with the skin fills each lid opening and carries the NG_Eye
  iris (UVs projected from the front); lid lines and brows are flat painted strokes (emission), no eyeball depth.
- Outline: inverted hull (Solidify, flipped, outline slot); weight fades to 0 around the eyes, nose and mouth.
All positions in head units H (chin 0, skull top 1) mapped with S = 0.262 m, chin at z = 1.4826.
"""
import json
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

S, O = 0.262, 1.4826
EYE_X, EYE_Z, EYE_HW, EYE_HH = 0.178, 0.48, 0.102, 0.072
MOUTH_Z, MOUTH_HW = 0.165, 0.085
NOSE_Z = 0.246
NECK_Y = 0.03
SKIN = (0.807, 0.558, 0.402, 1)
# painted face strokes (MHS3 draws the nose and mouth as lines); 0 = off. Tuned by the reference-match judge.
NOSE_LINE = 1.0          # line down the shadow side of the nose bridge: thickness factor
NOSE_LINE_LEN = 1.15      # its length (1 = from under the brow to the nose tip)
NOSE_LINE_X = 0.012        # extra offset toward the shadow side (H)
NOSTRIL = 1.0            # nostril mark on the shadow side: size factor
MOUTH_LINE = 1.0         # painted mouth line: thickness factor
MOUTH_LINE_W = 1.40      # its width relative to the mouth opening (p1: 1.6 -> 1.4, MHS3 mouth 0.49 D wide)
EAR_CUT_X = 1.0          # s2: |x| where the head normal field starts handing over to the mesh normal (ears)
SKIN_SOFT = 0.002        # s4: toon terminator softness for the head (shared NG_ToonSkin uses 0.012)
PIXEL_NORMAL = 1         # s1: the face normal field evaluated per pixel in the shader (clean toon terminator)
FACE_FORWARD = 2.5       # how much the face normals turn toward the viewer (bigger = shadow only at the far edge)
OUTLINE_W = 0.0015       # outline width (m)
OUTLINE_DARK = 1.5       # outline darkness factor (1 = current colour)
CHIN_LIT = 1.0           # 0..1: lowers where the face plane / normal blend fade out, so the chin front is lit (g7)
LIP_SHADOW = 1.0         # short shadow stroke under the lower lip: thickness factor
EYE_W2 = 0.092           # painted eye half-width (H)
EYE_DZ = 0.0             # painted eye vertical offset (H)
EYE_DX = 0.0             # painted eye outward offset (H): + moves the eyes apart
HL_SAME_SIDE = 1         # highlight on the viewer's left in both eyes (MHS3 light direction), not mirrored
BROW_DZ = 0.0            # brow vertical offset (H)
BROW_TH = 0.040          # brow thickness (H)
BROW_DARK = 1.0          # brow colour divisor
BROW_GREY = 0.0          # brow colour mixed toward grey (less orange)
BROW_IN, BROW_OUT = 0.50, 0.62   # brow extent toward the nose / past the eye centre outward (x eye width)
BROW_ARCH = 0.010         # brow arch (H)
BROW_INNER = 0.0         # extra thickness at the brow's inner end (x)
BROW_TAPER = 0.30        # where the brow starts to thin (0..1 along it)
EYE_RIG = 1              # r1: animatable eyes/brows (face_rig.py): opening + eye white + iris + lid strips + shape keys
VIEW_KEYS = 1            # v1: camera-angle view keys (VW-Yaw_L/R, VW-Side_L/R; view_keys.py) keep the anime eye shape off-front
EYE_DECAL = 1            # q1: eyes painted into a texture decal on the skin (shape free of the mesh opening); 0 = old plate + strips
# ears (g12, reference-match judge knobs; 0 = off)
IRIS_RING_X = -0.15       # dark iris arcs only where px < this (x R)
IRIS_RING_Y = -0.45      # ... and py > this (x R)
IRIS_LOW = (0.05, -0.45, 0.55, 0.42)   # light lower iris area: centre x, y, radius x, y (x R)
IRIS_Y = -0.02            # iris centre above the eye centre (x eye half-height)
LID_OUTER = -0.002       # upper lid line thickness change at the outer end (negative = tapers)
LID_WRAP = 0.28          # share of the lower lid the upper line wraps around the outer corner
EAR_LIT = 2.0            # turns the ear normals toward the lit face direction (MHS3 ears read lit, not in shadow)
EAR_LINE = 1.5           # painted dark line on the inner side of the helix: 1 = on, higher = thicker
EAR_TINT = 1.0           # mauve tint in the concha shadow (n3: on; the MHS3 bowl reads mauve, not brown)
EAR_BOWL = 0.0           # grows (+) / shrinks (-) the forced concha shadow
# n-series (2026-10-15): nose, mouth and ear shapes redrawn from the MHS3 reference crop (measured in IPD units)
NOSE_STYLE = 2           # 2: one curved stroke from under the brow's inner end, thin/broken middle, heavy hooked tip
NOSE_SIDE = -1           # n1: the line on the lit (-x, viewer's left) side, the shadow lens reaching to the shadow side,
                         # as in the reference (face turned to the viewer's left, line on the far side, lens toward the near side)
ID_MORPHS = 1            # p1: id_morphs.py (bake + ID- keys)
NOSE_LINE_TOP = 0.40      # p1: head z where the nose line starts (Leo front: no line up the bridge, only near the tip)
NOSE_HL = 1.0            # p1: pale highlight lens on the nose bridge (Leo render), 0 = off
NOSE_FRONT_HIDE = 1      # p8: nose line hidden in the front view, shown by the yaw / side keys
NOSE_VIEW = 1            # n11: own view keys for the nose strokes (stroke_view_keys)
NOSE_RETRACT = 0.07      # n11: at 3/4 toward the line's side its top retracts to EYE_Z - this (H)
NOSE_SHADE = 1.0         # painted lens of shadow under the nose tip (replaces the vertex-mask rectangle); 0 = off
NOSE_TINT = 0.35         # mauve mixed into the painted nose / lip shadow (MHS3 shadows under the nose read pink-brown)
LIP_STYLE = 2            # 2: the under-lip mark is a soft shadow lens, not a thin dark line
EAR_STYLE = 2            # 2: ear paint from ear-plane coordinates: mauve bowl + a thin C line along its front-top edge
EAR_SPLIT = 1            # ear shells moved to their own object with a Subdivision modifier (smooth rim + outline)
EAR_SUBDIV = 2           # its render/viewport level
EAR_LINE_W = 0.028       # half width of the ear C line in the bowl field (bigger = thicker)


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def load(npz, tag, off_x):
    d = np.load(npz)
    V, PL, PS = d["V"], d["PL"], d["PS"]
    faces, o = [], 0
    for n in PS:
        faces.append([int(i) for i in PL[o:o + n]]); o += n
    col = bpy.data.collections.get("NEW_HEAD_" + tag) or bpy.data.collections.new("NEW_HEAD_" + tag)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    for ob in list(col.objects):
        bpy.data.objects.remove(ob)
    me = bpy.data.meshes.new("NEW_Head_" + tag)
    me.from_pydata(V.tolist(), [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("NEW_Head_" + tag, me)
    col.objects.link(ob)
    ob.location.x = off_x
    D = d["ear_dark"] if "ear_dark" in d.files else np.zeros(len(V))
    LID = d["lid"] if "lid" in d.files else np.zeros(len(V), np.int8)
    EL = d["ear_line"] if "ear_line" in d.files else np.zeros(len(V), np.float32)
    for nm, val in (("ear_line", EL), ("ear_bowl", smooth(0.35, 0.60, D))):
        a = me.attributes.get(nm) or me.attributes.new(nm, "FLOAT", "POINT")
        a.data.foreach_set("value", np.asarray(val, np.float32))
    return ob, col, V, D, LID


def head_coords(V):
    return np.stack([V[:, 0] / S, V[:, 1] / S, (V[:, 2] - O) / S], 1)


def vertex_normals(me):
    n = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("normal", n)
    return n.reshape(-1, 3)


def shade_mask(me, P, D, N):
    x, y, z = np.abs(P[:, 0]), P[:, 1], P[:, 2]
    shade = np.ones(len(P))
    if EAR_STYLE == 2 and EAR_B is not None:
        shade = np.minimum(shade, 1 - 0.75 * EAR_B)                                   # n3: the ear bowl from ear-plane coords
    else:
        shade = np.minimum(shade, 1 - 0.75 * smooth(0.35 - 0.08 * EAR_BOWL, 0.60 - 0.08 * EAR_BOWL, D))  # ear bowl + rim groove
    if not NOSE_SHADE:
        nose = (x < 0.035) & (y < -0.36) & (z < NOSE_Z + 0.004) & (z > NOSE_Z - 0.045) & (N[:, 2] < -0.25)
        shade = np.where(nose, 0.25, shade)                                          # under the nose tip (old: a hard rectangle)
    under = smooth(-0.30, -0.55, N[:, 2]) * (1 - smooth(0.10, 0.16, z)) * (z > -0.05)
    under = under * (1 - min(1.0, 2 * CHIN_LIT) * smooth(-0.18, -0.24, y))             # g9: chin front stays lit (MHS3: shadow falls on the neck)
    shade = np.minimum(shade, 1 - 0.70 * under)                                       # jaw underside
    ra = np.hypot(P[:, 0] / 0.20, (y - NECK_Y) / (0.20 * 0.92))
    neck = (z < 0.24) & (z > -0.16) & (ra < 1.12)                                     # the whole neck under the head
    edge = 0.30 - 0.10 * np.clip(1 - (P[:, 0] / 0.2) ** 2, 0, 1)                         # up to the jaw floor (no lit collar)
    shade = np.where(neck, np.minimum(shade, 1 - 0.70 * smooth(edge - 0.02, edge + 0.02, z) * (1 - smooth(-0.12, -0.18, z))), shade)
    a = me.attributes.get("shade") or me.attributes.new("shade", "FLOAT", "POINT")
    a.data.foreach_set("value", shade.astype(np.float32))
    return shade


def main_component(me):
    """True for vertices in the largest connected piece (the head skin); the ear shells are separate pieces."""
    n = len(me.vertices); E = np.zeros(len(me.edges) * 2, int); me.edges.foreach_get("vertices", E); E = E.reshape(-1, 2)
    par = np.arange(n)
    def root(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    for a, b in E:
        ra, rb = root(a), root(b)
        if ra != rb:
            par[ra] = rb
    r = np.array([root(i) for i in range(n)])
    return r == np.bincount(r).argmax()


def custom_normals(me, P, D, N):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    c, r = np.array([0.0, -0.02, 0.47]), np.array([0.40, 0.46, 0.56])
    pe = (P - c) / r ** 2
    pe /= np.linalg.norm(pe, axis=1, keepdims=True)
    pc = np.stack([x, y - NECK_Y, np.zeros_like(x)], 1)
    pc /= np.maximum(np.linalg.norm(pc, axis=1, keepdims=True), 1e-9)
    lo = 0.07 * CHIN_LIT
    w = 0.96 * smooth(0.04 - lo, 0.12 - lo, z)                                                  # whole head above the jaw (n41b: 0.8 front-only left a jagged edge)
    de = np.sqrt(((np.abs(x) - EYE_X) / (EYE_HW * 1.5)) ** 2 + ((z - EYE_Z) / (EYE_HH * 2.0)) ** 2)
    if not (EYE_DECAL or EYE_RIG):
        w *= 0.55 + 0.45 * smooth(0.9, 1.15, de)                                      # only the lid itself keeps some form
    dm = np.sqrt((x / (MOUTH_HW * 1.6)) ** 2 + ((z - MOUTH_Z) / 0.05) ** 2)
    w *= 0.8 + 0.2 * smooth(0.6, 1.0, dm)
    # MHS3 face plane: the front of the face is turned toward the viewer (lit), the shadow stays on the far cheek
    face = smooth(0.0, -0.25, y) * smooth(0.05 - lo, 0.15 - lo, z) * (1 - smooth(0.62, 0.75, z))
    pe = pe + np.array([0.0, -FACE_FORWARD, 0.0]) * face[:, None]
    pe /= np.linalg.norm(pe, axis=1, keepdims=True)
    # s2: ears keep their own normals, but the switch is a smooth ramp: the old hard cut (D < 0.01, |x| < 0.33) made
    # the toon terminator step along the mesh faces down the temples (seen at every yaw from 20 degrees)
    # s3: only the separate ear shells keep their own normals; the head skin round the ear root follows the head field
    # too (a mesh-normal zone there showed as a lit stripe inside the side shadow)
    w *= main_component(me) if EAR_CUT_X >= 1.0 else (1 - smooth(0.004, 0.03, D)) * (1 - smooth(EAR_CUT_X, EAR_CUT_X + 0.08, np.abs(x)))
    wn = 0.8 * (1 - smooth(-0.02, 0.06, z)) * (z > -0.6)                               # neck column
    tgt = pe * w[:, None] + pc * wn[:, None]
    n = N * (1 - w - wn)[:, None] + tgt
    a_ = me.attributes.get("an_w") or me.attributes.new("an_w", "FLOAT", "POINT")
    a_.data.foreach_set("value", np.clip(w, 0, 1).astype(np.float32))   # s1: weight of the per-pixel face normal
    if EAR_LIT:
        ear = ~main_component(me)                                                     # the ear shells only (e3: a box mask lit the skull)
        k = min(0.9, 0.45 * EAR_LIT) * ear
        lit = np.array([0.0, -1.0, 0.25]) / np.linalg.norm([0.0, -1.0, 0.25])
        n = n * (1 - k)[:, None] + lit * k[:, None]
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    me.normals_split_custom_set_from_vertices([tuple(v) for v in n])


def _smooth_nodes(B, e0, e1, x):
    t = B.m("MINIMUM", 1.0, B.m("MAXIMUM", 0.0, B.m("DIVIDE", B.m("SUBTRACT", x, e0), e1 - e0)))
    return B.m("MULTIPLY", B.m("MULTIPLY", t, t), B.m("SUBTRACT", 3.0, B.m("MULTIPLY", 2.0, t)))


def analytic_normal(nt):
    """s1: the custom-normal target (head ellipsoid + face plane turned to the viewer) evaluated per PIXEL from the object
    position, mixed over the stored normal by the 'an_w' weight. The stored per-vertex normals interpolate linearly across
    the faces, so the toon terminator followed the mesh (stair steps at the temple, specks where shape keys slide the
    skin); the analytic field gives one clean shadow shape and ignores how the faces are stretched."""
    B = _NB(nt)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sp.inputs[0])
    x = B.m("DIVIDE", sp.outputs[0], S); y = B.m("DIVIDE", sp.outputs[1], S); z = B.m("DIVIDE", B.m("SUBTRACT", sp.outputs[2], O), S)
    c, r = (0.0, -0.02, 0.47), (0.40, 0.46, 0.56)
    ex = B.m("DIVIDE", B.m("SUBTRACT", x, c[0]), r[0] ** 2)
    ey = B.m("DIVIDE", B.m("SUBTRACT", y, c[1]), r[1] ** 2)
    ez = B.m("DIVIDE", B.m("SUBTRACT", z, c[2]), r[2] ** 2)
    ln = B.m("SQRT", B.m("ADD", B.m("ADD", B.m("MULTIPLY", ex, ex), B.m("MULTIPLY", ey, ey)), B.m("MULTIPLY", ez, ez)))
    ex, ey, ez = (B.m("DIVIDE", v, ln) for v in (ex, ey, ez))
    lo = 0.07 * CHIN_LIT
    face = B.m("MULTIPLY", B.m("MULTIPLY", _smooth_nodes(B, 0.0, -0.25, y), _smooth_nodes(B, 0.05 - lo, 0.15 - lo, z)),
               B.m("SUBTRACT", 1.0, _smooth_nodes(B, 0.62, 0.75, z)))
    ey = B.m("SUBTRACT", ey, B.m("MULTIPLY", face, FACE_FORWARD))
    cmb = nt.nodes.new("ShaderNodeCombineXYZ")
    for k, v in enumerate((ex, ey, ez)):
        nt.links.new(v, cmb.inputs[k])
    vt = nt.nodes.new("ShaderNodeVectorTransform"); vt.vector_type = "NORMAL"
    vt.convert_from = "OBJECT"; vt.convert_to = "WORLD"
    nt.links.new(cmb.outputs[0], vt.inputs[0])
    nrm1 = nt.nodes.new("ShaderNodeVectorMath"); nrm1.operation = "NORMALIZE"; nt.links.new(vt.outputs[0], nrm1.inputs[0])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    aw = nt.nodes.new("ShaderNodeAttribute"); aw.attribute_name = "an_w"
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "VECTOR"
    nt.links.new(aw.outputs["Fac"], mx.inputs["Factor"])
    nt.links.new(geo.outputs["Normal"], mx.inputs[4]); nt.links.new(nrm1.outputs[0], mx.inputs[5])
    nrm2 = nt.nodes.new("ShaderNodeVectorMath"); nrm2.operation = "NORMALIZE"; nt.links.new(mx.outputs[1], nrm2.inputs[0])
    return nrm2.outputs[0]


def _head_toon_group():
    """s4: a head-only copy of NG_ToonSkin with a narrower terminator. The shared group's Softness (0.012) is in
    brightness units, and the smooth per-pixel face normal changes brightness slowly near the terminator, so the
    toon edge became a 10-20 px blur at the temple and the back of the skull. The copy keeps the shared asset as is."""
    base = bpy.data.node_groups["NG_ToonSkin"]
    name = "NG_ToonSkin_NewHead"
    g = bpy.data.node_groups.get(name)
    if g is None:
        g = base.copy(); g.name = name
    inner = next(n for n in g.nodes if n.type == "GROUP")
    if "Softness" in inner.inputs and not inner.inputs["Softness"].is_linked:
        inner.inputs["Softness"].default_value = SKIN_SOFT
    return g


def skin_material(tag):
    m = bpy.data.materials.get("MAT_NewSkin_" + tag) or bpy.data.materials.new("MAT_NewSkin_" + tag)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (400, 0)
    g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = _head_toon_group()
    g.inputs["skin_color"].default_value = SKIN
    g.inputs["blush_strength"].default_value = 0.0
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "shade"; at.location = (-300, -200)
    nt.links.new(at.outputs["Fac"], g.inputs["Shadow Mask"])
    if PIXEL_NORMAL:
        nt.links.new(analytic_normal(nt), g.inputs["Normal"])
    last = g.outputs["Shader"]
    if EAR_TINT:      # mauve concha
        ab = nt.nodes.new("ShaderNodeAttribute"); ab.attribute_name = "ear_bowl"
        mf = nt.nodes.new("ShaderNodeMath"); mf.operation = "MULTIPLY"; mf.inputs[1].default_value = min(0.9, 0.45 * EAR_TINT)
        gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.6667   # n3: crisp edge where the toon shadow edge is (shade 0.5)
        nt.links.new(ab.outputs["Fac"], gt.inputs[0]); nt.links.new(gt.outputs[0], mf.inputs[0])
        em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.26, 0.13, 0.14, 1)
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(mf.outputs[0], mx.inputs["Fac"]); nt.links.new(last, mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
        last = mx.outputs[0]
    if EAR_LINE and EAR_STYLE == 2:   # n3: thin C line = narrow band round the bowl edge (iso-line of a smooth field)
        af = nt.nodes.new("ShaderNodeAttribute"); af.attribute_name = "ear_f"
        aw = nt.nodes.new("ShaderNodeAttribute"); aw.attribute_name = "ear_lw"
        d = nt.nodes.new("ShaderNodeMath"); d.operation = "SUBTRACT"; d.inputs[1].default_value = 1.0
        nt.links.new(af.outputs["Fac"], d.inputs[0])
        ab_ = nt.nodes.new("ShaderNodeMath"); ab_.operation = "ABSOLUTE"; nt.links.new(d.outputs[0], ab_.inputs[0])
        hw = nt.nodes.new("ShaderNodeMath"); hw.operation = "MULTIPLY"; hw.inputs[1].default_value = EAR_LINE_W
        nt.links.new(aw.outputs["Fac"], hw.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.clamp = True
        mr.inputs["To Min"].default_value = 1.0; mr.inputs["To Max"].default_value = 0.0
        nt.links.new(ab_.outputs[0], mr.inputs["Value"]); nt.links.new(hw.outputs[0], mr.inputs["From Min"])
        hw2 = nt.nodes.new("ShaderNodeMath"); hw2.operation = "ADD"; hw2.inputs[1].default_value = 0.012
        nt.links.new(hw.outputs[0], hw2.inputs[0]); nt.links.new(hw2.outputs[0], mr.inputs["From Max"])
        em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.21, 0.09, 0.05, 1)
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(mr.outputs["Result"], mx.inputs["Fac"]); nt.links.new(last, mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
        last = mx.outputs[0]
    elif EAR_LINE:      # painted inner-helix line
        al = nt.nodes.new("ShaderNodeAttribute"); al.attribute_name = "ear_line"
        t0 = 0.62 - 0.12 * (EAR_LINE - 1)
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.clamp = True
        mr.inputs["From Min"].default_value = t0; mr.inputs["From Max"].default_value = t0 + 0.06
        nt.links.new(al.outputs["Fac"], mr.inputs["Value"])
        em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.21, 0.09, 0.05, 1)
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(mr.outputs["Result"], mx.inputs["Fac"]); nt.links.new(last, mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
        last = mx.outputs[0]
    nt.links.new(last, out.inputs["Surface"])
    return m


def outline_material(tag):
    src = bpy.data.materials.get("MAT_Outline_CHR_Body")
    name = "MAT_Outline_NewHead_" + tag
    m = bpy.data.materials.get(name)
    if m is None:
        m = src.copy() if src else bpy.data.materials.new(name)
        m.name = name
    m.use_backface_culling = True
    em = next((n for n in m.node_tree.nodes if n.type == "EMISSION"), None) if m.use_nodes else None
    if em:
        em.inputs["Color"].default_value = (0.30 / OUTLINE_DARK, 0.15 / OUTLINE_DARK, 0.10 / OUTLINE_DARK, 1)   # dark warm brown
    return m


EAR_ROOT = None
EAR_ROOT_D = None     # signed distance of ear verts to the skull (m)
EAR_TOP_LINE = 0.0    # n5 (TypeSafe ear_outline_close_top, tried at 0.6): no visible change - the gap is the hull facing away; off
EAR_B = None          # n3: per-vertex ear bowl (0..1) from ear_paint(); None = the old ear_dark field
EAR_BOWL_E = (0.18, 0.10, 0.50, 0.46, 0.72, 0.61)   # n10: TypeSafe ear_bowl_bigger (+0.06 radii)
#   # bowl centre u, v and radii front, back, up, down (ear-plane units)
EAR_LIT_E = (-0.06, -0.18, 0.38, 0.60)                # lit lower-back area cut out of the bowl: centre u, v, radii


def ear_paint(me, V, N):
    """n3: the MHS3 ear (reference crop): the inner ear reads as one mauve bowl from just under the helix to above the
    lobe, lit helix rim round the back and a lit lobe; one thin dark line runs along the bowl's FRONT-TOP edge (the
    helix crus coming down in front of the concha), not along the back. The ear builder's own fields put a short
    thick slash at the back and an oval blob in the middle. Here every ear vertex gets ear-plane coordinates (PCA of
    the shell: normal = least spread, b = long axis up, a = toward the face), u/v in -1..1 over the shell, and
      ear_f  = elliptic distance to the bowl centre (1 on the bowl edge; smooth, so a narrow band of it is a thin line)
      ear_lw = 1 along the front-top part of that edge (the line), 0 elsewhere
      bowl   = 1 inside the bowl, on the outer face only."""
    n = len(V)
    F, LW, B = np.full(n, 3.0), np.zeros(n), np.zeros(n)
    mc = main_component(me)
    u0, v0, rf, rb, ru, rd = EAR_BOWL_E
    for sd in (1, -1):
        E = np.nonzero((~mc) & (np.sign(V[:, 0]) == sd))[0]
        if len(E) < 10:
            continue
        X = V[E] - V[E].mean(0)
        w, vec = np.linalg.eigh(X.T @ X)
        nrm, bax = vec[:, 0], vec[:, 2]
        if nrm[0] * sd < 0:
            nrm = -nrm
        if bax[2] < 0:
            bax = -bax
        aax = np.cross(nrm, bax)
        if aax[1] > 0:
            aax = -aax
        a, b = X @ aax, X @ bax
        uu = (a - (a.max() + a.min()) / 2) / ((a.max() - a.min()) / 2)
        vv = (b - (b.max() + b.min()) / 2) / ((b.max() - b.min()) / 2)
        du, dv = uu - u0, vv - v0
        f = np.sqrt((du / np.where(du > 0, rf, rb)) ** 2 + (dv / np.where(dv > 0, ru, rd)) ** 2)
        out = (N[E] @ nrm) > 0.15
        phi = np.degrees(np.arctan2(dv / np.where(dv > 0, ru, rd), du / np.where(du > 0, rf, rb)))
        lw = smooth(-85.0, -60.0, phi) * (1 - smooth(100.0, 125.0, phi))
        F[E] = np.where(out, f, 3.0)
        LW[E] = np.where(out, lw, 0.0)
        # reference bowl is a crescent: the lower back (antihelix / concha floor) stays lit
        u2, v2, r2u, r2v = EAR_LIT_E
        f2 = np.sqrt(((uu - u2) / r2u) ** 2 + ((vv - v2) / r2v) ** 2)
        B[E] = np.where(out, smooth(1.20, 0.80, f) * smooth(0.80, 1.20, f2), 0.0)
    for nm, val in (("ear_f", F), ("ear_lw", LW), ("ear_bowl", B)):
        a_ = me.attributes.get(nm) or me.attributes.new(nm, "FLOAT", "POINT")
        a_.data.foreach_set("value", val.astype(np.float32))
    return B


def split_ears(ob, col, tag):
    """n2: the ear shells (24 spokes) drew a polygonal rim and outline in close-ups. They move to their own object with
    a Subdivision modifier, so the asset mesh keeps its low-poly topology. Both objects share one mesh layout: a Mask
    modifier on each (vertex group EarShell) keeps every index, shape key and custom normal intact; the ears do not
    move in any shape key (checked: 0.0 mm in all PF-/VW- keys)."""
    me = ob.data
    ear = ~main_component(me)
    vg = ob.vertex_groups.get("EarShell") or ob.vertex_groups.new(name="EarShell")
    vg.add([int(i) for i in np.nonzero(ear)[0]], 1.0, "REPLACE")
    name = "NEW_Ears_" + tag
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    e = ob.copy(); e.name = name
    col.objects.link(e)
    for md in list(e.modifiers):
        e.modifiers.remove(md)
    m1 = ob.modifiers.new("SkinOnly", "MASK"); m1.vertex_group = "EarShell"; m1.invert_vertex_group = True
    ob.modifiers.move(len(ob.modifiers) - 1, 0)          # mask first, then the outline
    m2 = e.modifiers.new("EarOnly", "MASK"); m2.vertex_group = "EarShell"
    sub = e.modifiers.new("Smooth", "SUBSURF"); sub.levels = sub.render_levels = EAR_SUBDIV
    if hasattr(sub, "use_custom_normals"):
        sub.use_custom_normals = True
    src = ob.modifiers.get("Outline")
    o = e.modifiers.new("Outline", "SOLIDIFY")
    for k in ("thickness", "offset", "use_flip_normals", "use_rim", "use_even_offset", "material_offset", "vertex_group",
              "thickness_vertex_group"):
        setattr(o, k, getattr(src, k))
    return e


def shade_material(tag):
    """n1: forced toon shadow of the skin (the same group, Shadow Mask 0), with NOSE_TINT mauve mixed in, for the
    painted shadow shapes under the nose and the lower lip."""
    m = bpy.data.materials.get("MAT_PaintShade_" + tag) or bpy.data.materials.new("MAT_PaintShade_" + tag)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = _head_toon_group()
    g.inputs["skin_color"].default_value = SKIN
    g.inputs["blush_strength"].default_value = 0.0
    g.inputs["Shadow Mask"].default_value = 0.0
    last = g.outputs["Shader"]
    if NOSE_TINT:
        em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.26, 0.13, 0.14, 1)
        mx = nt.nodes.new("ShaderNodeMixShader"); mx.inputs["Fac"].default_value = min(0.9, NOSE_TINT)
        nt.links.new(last, mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); last = mx.outputs[0]
    nt.links.new(last, out.inputs["Surface"])
    return m


def ear_root(ob, P):
    """Vertices of the ear shells (not the main skin component) that lie inside or within 3 mm of the skull."""
    from mathutils.bvhtree import BVHTree
    me = ob.data
    n = len(me.vertices)
    parent = list(range(n))

    def f_(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for p in me.polygons:
        r = f_(p.vertices[0])
        for v in p.vertices[1:]:
            parent[f_(v)] = r
    comp = np.array([f_(i) for i in range(n)])
    main = np.bincount(comp).argmax()
    polys = [tuple(p.vertices) for p in me.polygons if comp[p.vertices[0]] == main]
    tree = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], polys)
    root = np.zeros(n, bool)
    global EAR_ROOT_D
    EAR_ROOT_D = np.full(n, 1.0)
    for i in np.nonzero(comp != main)[0]:
        co = me.vertices[i].co
        loc, nrm, _, d = tree.find_nearest(co)
        if loc is not None:
            EAR_ROOT_D[i] = (co - loc).dot(nrm)
            if EAR_ROOT_D[i] < 0.003:
                root[i] = True
    return root


def outline(ob, P, D):
    x, z = np.abs(P[:, 0]), P[:, 2]
    front = P[:, 1] < -0.15
    de = np.sqrt(((x - EYE_X) / (EYE_HW * 1.35)) ** 2 + ((z - EYE_Z) / (EYE_HH * 1.6)) ** 2)
    dm = np.sqrt((P[:, 0] / (MOUTH_HW * 1.6)) ** 2 + ((z - MOUTH_Z) / 0.05) ** 2)
    dn = np.sqrt((P[:, 0] / 0.06) ** 2 + ((z - (NOSE_Z + 0.07)) / 0.13) ** 2)    # n1: whole bridge (a stray dash showed at 20-35 deg)
    w = np.ones(len(P))
    for dd, k in ((de, 1.35), (dm, 1.4), (dn, 1.3)):
        w = np.where(front, np.minimum(w, smooth(1.0, k, dd)), w)
    w = np.minimum(w, 1 - 0.5 * smooth(0.35, 0.6, D))                                # thinner inside the ear
    # no outline on the part of the ear that grows out of / sits inside the skull (its hull showed through the skin)
    w = np.where(EAR_ROOT, 0.0, w)
    if EAR_TOP_LINE and EAR_ROOT_D is not None:
        top = (P[:, 2] > EYE_Z + 0.02) & EAR_ROOT & (EAR_ROOT_D > 0.0006)
        w = np.where(top, EAR_TOP_LINE, w)          # the top of the ear where it curls into the head keeps its line
    vg = ob.vertex_groups.get("OutlineWeight") or ob.vertex_groups.new(name="OutlineWeight")
    for i, wi in enumerate(w):
        vg.add([i], float(wi), "REPLACE")
    md = ob.modifiers.get("Outline") or ob.modifiers.new("Outline", "SOLIDIFY")
    md.thickness = OUTLINE_W
    md.offset = 1.0
    md.use_flip_normals = True
    md.use_rim = False
    md.use_even_offset = False
    md.material_offset = 1
    md.vertex_group = "OutlineWeight"
    md.thickness_vertex_group = 0.0


def _bvh(ob):
    from mathutils.bvhtree import BVHTree
    me = ob.data
    return BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])


def _emission(name, color, hatch=0.0):
    """Flat painted colour (no lighting), as MHS3 draws the lid lines and brows. hatch > 0 adds darker brush strokes
    along the strip (UV u)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (500, 0)
    em = nt.nodes.new("ShaderNodeEmission"); em.location = (300, 0)
    em.inputs["Color"].default_value = color
    if hatch > 0:
        uv = nt.nodes.new("ShaderNodeUVMap"); uv.location = (-500, 0)
        sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-320, 0)
        nt.links.new(uv.outputs[0], sep.inputs[0])
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 34.0
        add = nt.nodes.new("ShaderNodeMath"); add.operation = "MULTIPLY_ADD"; add.inputs[1].default_value = 7.0
        nt.links.new(sep.outputs[1], add.inputs[0]); nt.links.new(sep.outputs[0], mul.inputs[0])
        nt.links.new(mul.outputs[0], add.inputs[2])
        fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "FRACT"; nt.links.new(add.outputs[0], fr.inputs[0])
        st = nt.nodes.new("ShaderNodeMath"); st.operation = "GREATER_THAN"; st.inputs[1].default_value = 0.72
        nt.links.new(fr.outputs[0], st.inputs[0])
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.location = (100, 0)
        f = nt.nodes.new("ShaderNodeMath"); f.operation = "MULTIPLY"; f.inputs[1].default_value = hatch
        nt.links.new(st.outputs[0], f.inputs[0]); nt.links.new(f.outputs[0], mx.inputs["Factor"])
        mx.inputs["A"].default_value = color
        mx.inputs["B"].default_value = tuple(c * 0.55 for c in color[:3]) + (1,)
        nt.links.new(mx.outputs["Result"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


class _NB:
    """Tiny expression helper for building math node trees."""
    def __init__(self, nt):
        self.nt = nt
    def m(self, op, a, b=None, c=None):
        n = self.nt.nodes.new("ShaderNodeMath"); n.operation = op
        for k, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[k].default_value = v
            else:
                self.nt.links.new(v, n.inputs[k])
        return n.outputs[0]
    def mix(self, f, a, b):
        n = self.nt.nodes.new("ShaderNodeMix"); n.data_type = "RGBA"
        for sock, v in ((n.inputs["Factor"], f), (n.inputs["A"], a), (n.inputs["B"], b)):
            if isinstance(v, (int, float)) or (isinstance(v, tuple)):
                sock.default_value = v
            else:
                self.nt.links.new(v, sock)
        return n.outputs["Result"]
    def inside(self, d, r=1.0, soft=0.02):        # 1 inside d < r, smooth edge
        return self.m("SUBTRACT", 1.0, self.m("SMOOTH_MAX", 0.0, self.m("MINIMUM", 1.0, self.m("DIVIDE", self.m("SUBTRACT", d, r - soft), 2 * soft)), 0.0))
    def ell(self, px, py, cx, cy, rx, ry):
        a = self.m("DIVIDE", self.m("SUBTRACT", px, cx), rx)
        b = self.m("DIVIDE", self.m("SUBTRACT", py, cy), ry)
        return self.m("SQRT", self.m("ADD", self.m("MULTIPLY", a, a), self.m("MULTIPLY", b, b)))


def mhs3_eye_material(tag, iris=(0.10, 0.33, 0.12, 1), R=0.94):   # TypeSafe iris_smaller (r2, x5)
    """MHS3 painted iris (from the official frames): flat green, dark outline, two dark concentric arcs on the
    left, a big light-green area in the lower half, a darker top under the lid, a vertical oval pupil, one white
    highlight half outside the iris on the left and a small one low right; grey-blue sclera with a grey band under
    the upper lid. Emission (painted), on the plate's UVs (-1..1 = the eye's half height)."""
    name = "MAT_MHS3Eye_" + tag
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    b = _NB(nt)
    uv = nt.nodes.new("ShaderNodeUVMap")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(uv.outputs[0], sep.inputs[0])
    px = b.m("MULTIPLY_ADD", sep.outputs[0], 2.0, -1.0)
    py = b.m("MULTIPLY_ADD", sep.outputs[1], 2.0, -1.0)
    r = b.ell(px, py, 0.0, 0.0, R, R)
    dark = tuple(c * 0.28 for c in iris[:3]) + (1,)
    light = tuple(min(1.0, c * 1.4 + 0.12) for c in iris[:3]) + (1,)   # colours sampled from the MHS3 frame (linear)
    sclera = (0.60, 0.61, 0.63, 1)   # x1: TypeSafe sclera_greyer
    col = b.mix(b.m("MULTIPLY", b.m("GREATER_THAN", py, 0.30), 0.85), sclera, (0.42, 0.44, 0.51, 1))       # lid band
    ic = iris
    # light lower area
    lx, ly, lrx, lry = IRIS_LOW
    low = b.m("MULTIPLY", b.inside(b.ell(px, py, lx * R, ly * R, lrx * R, lry * R), 1.0, 0.04), 1.0)
    icol = b.mix(low, ic, light)
    # darker top under the lid
    icol = b.mix(b.m("MULTIPLY", b.m("GREATER_THAN", b.m("DIVIDE", py, R), 0.50), 0.55), icol, dark)
    # two thin dark concentric arcs on the left side
    for rr in (0.60, 0.80):
        ring = b.m("MULTIPLY", b.inside(r, rr + 0.035, 0.012), b.m("SUBTRACT", 1.0, b.inside(r, rr - 0.035, 0.012)))
        left = b.m("LESS_THAN", px, IRIS_RING_X * R)
        notlow = b.m("GREATER_THAN", py, IRIS_RING_Y * R)
        icol = b.mix(b.m("MULTIPLY", b.m("MULTIPLY", ring, left), notlow), icol, dark)
    # dark outline
    rim = b.m("SUBTRACT", 1.0, b.inside(r, 0.92, 0.02))
    icol = b.mix(rim, icol, dark)
    # pupil
    pup = b.inside(b.ell(px, py, 0.02 * R, 0.02 * R, 0.21 * R, 0.33 * R), 1.0, 0.06)
    icol = b.mix(pup, icol, (0.03, 0.05, 0.04, 1))
    col = b.mix(b.inside(r, 1.0, 0.015), col, icol)
    # highlights
    h1 = b.inside(b.ell(px, py, -0.72 * R, -0.08 * R, 0.24 * R, 0.13 * R), 1.0, 0.08)
    col = b.mix(h1, col, (1, 1, 1, 1))
    h2 = b.inside(b.ell(px, py, 0.40 * R, -0.45 * R, 0.07 * R, 0.05 * R), 1.0, 0.15)
    col = b.mix(b.m("MULTIPLY", h2, 0.85), col, (1, 1, 1, 1))
    em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(col, em.inputs["Color"])
    out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def _lid_loop(bm, LID, tag):
    """The lid edge loop (verts tagged at build time), walked in order."""
    vs = [v for v in bm.verts if LID[v.index] == tag]
    S_ = set(vs)
    loop, prev, cur = [vs[0]], None, vs[0]
    while True:
        nxt = [e.other_vert(cur) for e in cur.link_edges if e.other_vert(cur) in S_ and e.other_vert(cur) is not prev]
        if not nxt or nxt[0] is loop[0]:
            break
        prev, cur = cur, nxt[0]
        loop.append(cur)
    return loop


def _mesh(name, verts, faces, uvs, mat, col, off_x):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    lay = me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        p.use_smooth = True
        for li in p.loop_indices:
            lay.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); o.location.x = off_x
    col.objects.link(o)
    return o


def _strip(name, rows, mat, col, off_x):
    """rows: (inner, outer) points; one quad strip with UV u along, v across."""
    vs, uvs, fs = [], [], []
    n = len(rows)
    for i, (a, b) in enumerate(rows):
        vs += [a, b]; t = i / max(n - 1, 1); uvs += [(t, 0.0), (t, 1.0)]
    for i in range(n - 1):
        fs.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    return _mesh(name, vs, fs, uvs, mat, col, off_x)


EYE_PAINT = {}       # knob overrides for eye_paint.py (the judge loop sets them here)
EYE_VIEW = {}        # v1: knob overrides for view_keys.py (look_knobs.json "view")


def _target_normals(Ph):
    """The face normal the head uses (ellipsoid pushed toward the viewer on the face plane), head units in."""
    x, y, z = Ph[:, 0], Ph[:, 1], Ph[:, 2]
    c, r = np.array([0.0, -0.02, 0.47]), np.array([0.40, 0.46, 0.56])
    pe = (Ph - c) / r ** 2
    pe /= np.linalg.norm(pe, axis=1, keepdims=True)
    lo = 0.07 * CHIN_LIT
    face = smooth(0.0, -0.25, y) * smooth(0.05 - lo, 0.15 - lo, z) * (1 - smooth(0.62, 0.75, z))
    pe = pe + np.array([0.0, -FACE_FORWARD, 0.0]) * face[:, None]
    return pe / np.linalg.norm(pe, axis=1, keepdims=True)


def _skin_plate(o, nav):
    """Make the eye plate read as skin: lit shade mask, and the head's blended normal (the lid area keeps 45 % own form)."""
    me = o.data
    n = len(me.vertices)
    V = np.zeros(n * 3); me.vertices.foreach_get("co", V); V = V.reshape(-1, 3)
    a = me.attributes.get("shade") or me.attributes.new("shade", "FLOAT", "POINT")
    a.data.foreach_set("value", np.ones(n, np.float32))
    pe = _target_normals(head_coords(V))
    nv = np.array(nav[:])
    nn = 0.04 * nv[None] + 0.96 * pe
    nn /= np.linalg.norm(nn, axis=1, keepdims=True)
    me.normals_split_custom_set_from_vertices([tuple(v) for v in nn])


def _eye_decal(ob, plate, cx, cz, side, tag, col, off_x):
    """A grid laid on the skin over the eye (ray cast from the front onto head + plate), carrying the painted eye."""
    import os
    from mathutils.bvhtree import BVHTree
    g = {}
    exec(open(os.path.join(os.path.dirname(EYES_PATH), "..", "..", "..", "blender", "newhead", "eye_paint.py")).read(), g)
    for k, v in EYE_PAINT.items():
        g[k] = v
    if HL_SAME_SIDE and side < 0:
        g["HL_X"] = 2 * g["IRIS_X"] - g["HL_X"]
    W2 = EYE_W2 * S                                       # metres
    ch, zh = cx + side * EYE_DX * S, cz + (-g["MID"]) * W2 + EYE_DZ * S        # eye reference line
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bm2 = bmesh.new(); bm2.from_mesh(plate.data)
    tmp = bpy.data.meshes.new("tmp_decal"); bm2.to_mesh(tmp); bm2.free()
    bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    tree = BVHTree.FromBMesh(bm); bm.free()
    NX, NZ = 52, 36
    verts, uvs, faces = [], [], []
    for j in range(NZ + 1):
        for i in range(NX + 1):
            u, v = i / NX, j / NZ
            X = g["X0"] + u * (g["X1"] - g["X0"]); Z = g["Z0"] + v * (g["Z1"] - g["Z0"])
            x = ch + side * X * W2; z = zh + Z * W2
            loc, nrm, _, _ = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
            if loc is not None:
                nr = nrm if nrm.y < 0 else -nrm                      # always toward the viewer (plate faces may face back)
                p = loc + nr * 0.0009 + Vector((0, -0.0003, 0))
            else:
                p = Vector((x, -0.10, z))
            verts.append(p); uvs.append((u, v))
    for j in range(NZ):
        for i in range(NX):
            a0 = j * (NX + 1) + i
            q = (a0, a0 + 1, a0 + NX + 2, a0 + NX + 1)
            faces.append(q if side > 0 else q[::-1])
    name = "NewEyeDecal_%s_%s" % (tag, "LR"[side < 0])
    img = bpy.data.images.get("IMG_" + name)
    if img:
        bpy.data.images.remove(img)
    rx = int(355 * (g["X1"] - g["X0"])); rz = int(355 * (g["Z1"] - g["Z0"]))
    px = g["paint"](rx, rz, 3)
    img = bpy.data.images.new("IMG_" + name, rx, rz, alpha=True)
    img.colorspace_settings.name = "sRGB"
    img.pixels.foreach_set(px.ravel())
    img.pack()
    m = bpy.data.materials.get("MAT_" + name) or bpy.data.materials.new("MAT_" + name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = img; tx.interpolation = "Linear"; tx.extension = "CLIP"
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tx.outputs["Color"], em.inputs["Color"])
    nt.links.new(tx.outputs["Alpha"], mx.inputs["Fac"])
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        m.blend_method = "BLEND"
    try:
        m.use_transparent_shadow = True
    except Exception:
        pass
    o = _mesh(name, verts, faces, uvs, m, col, off_x)
    o.visible_shadow = False
    if os.path.isdir(os.path.dirname(EYES_PATH)):
        img.filepath_raw = os.path.join(os.path.dirname(EYES_PATH), "eye_paint_%s.png" % tag)
        img.file_format = "PNG"
        try:
            img.save()
        except Exception:
            pass
    return o


def painted_eyes(ob, col, LID, off_x, tag):
    """MHS3 eyes are flat colour on the face, not a ball in a socket: each lid opening is filled with a thin plate
    flush with the skin (just behind the lid edge, following the face's curve) carrying the NG_Eye iris, and the lid
    lines and brows are flat painted strokes on the skin."""
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
    em = mhs3_eye_material(tag)
    lash_m = _emission("MAT_PaintLash_" + tag, (0.07, 0.03, 0.018, 1))
    low_m = _emission("MAT_PaintLowLid_" + tag, (0.21, 0.09, 0.05, 1))
    bc = np.array([0.18, 0.09, 0.035]) / BROW_DARK
    bc = bc * (1 - BROW_GREY) + bc.mean() * BROW_GREY                      # q18: less orange
    brow_m = _emission("MAT_PaintBrow_" + tag, (float(bc[0]), float(bc[1]), float(bc[2]), 1), hatch=0.5)
    made = []
    for tagv, side in ((1, 1), (2, -1)):
        loop = _lid_loop(bm, LID, tagv)
        P = [v.co.copy() for v in loop]
        Nm = [v.normal.copy() for v in loop]
        n = len(P)
        c = sum(P, Vector()) / n
        nav = sum(Nm, Vector()); nav.normalize()
        xs = [p.x for p in P]; zs = [p.z for p in P]
        cx, cz = (max(xs) + min(xs)) / 2, (max(zs) + min(zs)) / 2
        hh = (max(zs) - min(zs)) / 2
        # plate: the lid ring 0.6 mm behind, 4 inner rings toward the middle with a slight forward bulge, a centre
        verts = [p - nav * 0.0006 for p in P]
        faces = []
        for k, s_ in enumerate((0.8, 0.6, 0.4, 0.2)):
            for p in P:
                q = c + (p - c) * s_ - nav * 0.0006 + nav * 0.0010 * (1 - s_ * s_)
                verts.append(q)
            r0, r1 = k * n, (k + 1) * n
            for m in range(n):
                faces.append((r0 + m, r0 + (m + 1) % n, r1 + (m + 1) % n, r1 + m))
        verts.append(c + nav * 0.0004)
        ctr = len(verts) - 1
        r0 = 4 * n
        for m in range(n):
            faces.append((r0 + m, r0 + (m + 1) % n, ctr))
        if EYE_DECAL:
            # an outer skirt tucked behind the lid rim, so no gap between the rim and the plate shows
            base = len(verts)
            for p in P:
                verts.append(c + (p - c) * 1.25 - nav * 0.0030)
            for m in range(n):
                faces.append((base + m, base + (m + 1) % n, (m + 1) % n, m))
        uvs = [(0.5 + (q.x - cx) / (2 * hh * 0.80), 0.5 + (q.z - (cz + IRIS_Y * hh)) / (2 * hh)) for q in verts]   # tall oval iris, cut by the upper lid
        if EYE_DECAL:
            # the plate becomes skin (closes the opening); the eye is painted on a decal above it
            plate = _mesh("NewEyePlate_%s_%s" % (tag, "LR"[side < 0]), verts, faces, uvs, skin_material(tag), col, off_x)
            _skin_plate(plate, nav)
            made.append(plate)
            made.append(_eye_decal(ob, plate, cx, cz, side, tag, col, off_x))
        else:
            made.append(_mesh("NewEyePlate_%s_%s" % (tag, "LR"[side < 0]), verts, faces, uvs, em, col, off_x))
        # split the lid loop at the corners
        ii = min(range(n), key=lambda i: (P[i].x - cx) * side)
        oo = max(range(n), key=lambda i: (P[i].x - cx) * side)
        arc1 = [(oo + k) % n for k in range((ii - oo) % n + 1)]
        arc2 = [(ii + k) % n for k in range((oo - ii) % n + 1)]
        mz = lambda arc: sum(P[i].z for i in arc) / len(arc)
        up_arc, low_arc = (arc1, arc2) if mz(arc1) > mz(arc2) else (arc2, arc1)
        up = sorted(up_arc, key=lambda i: (P[i].x - cx) * side)          # inner -> outer
        low = sorted(low_arc, key=lambda i: -(P[i].x - cx) * side)        # outer -> inner

        def row(i, th, inset=0.0025):
            p, nr = P[i], Nm[i]
            rad = Vector((p.x - cx, 0.0, (p.z - cz) * 1.6)); rad.normalize()
            return (p - rad * inset * S + nr * 0.0006, p + rad * th * S + nr * 0.0006)
        # upper lid line: thin at the open inner corner, ~0.014 H across, heavier at the outer end, then it wraps
        # down around the outer corner onto the lower lid and tapers out
        rows = []
        for k, i in enumerate(up):
            t = k / max(len(up) - 1, 1)
            th = 0.003 + 0.011 * smooth(0.0, 0.3, np.array(t)) + 0.0 * t * t + LID_OUTER * float(smooth(0.85, 1.0, np.array(t)))   # TypeSafe upper_lid_line_even (x3, x2 re-aimed: LID_OUTER/LID_WRAP)
            rows.append(row(i, float(th), inset=0.006))
        wrap = low[1:max(3, int(len(low) * LID_WRAP))]
        for k, i in enumerate(wrap):
            t = (k + 1) / (len(wrap) + 1)
            th0 = 0.014 + LID_OUTER   # continue from the end thickness of the upper line
            rows.append(row(i, th0 * (1 - t) + 0.003 * t, inset=0.006 * (1 - t) + 0.0005 * t))
        if not EYE_DECAL:
            made.append(_strip("NewLidLine_%s_%s" % (tag, "LR"[side < 0]), rows, lash_m, col, off_x))
        # lower lid line: thin, lighter brown, from the wrap to near the inner corner
        seg = low[max(3, int(len(low) * LID_WRAP)) - 1: int(len(low) * 0.95)]   # TypeSafe lower_lid_line_full
        rows = []
        for k, i in enumerate(seg):
            t = k / max(len(seg) - 1, 1)
            rows.append(row(i, 0.0055 * (1 - 0.6 * t), inset=0.0005))
        if len(rows) >= 2 and not EYE_DECAL:
            made.append(_strip("NewLowLid_%s_%s" % (tag, "LR"[side < 0]), rows, low_m, col, off_x))
        # brow: blunt and thick at the inner end, angling up to a peak at ~65%, tapering out (MHS3 male)
        tree = _bvh(ob)
        w = max(xs) - min(xs)
        ztop = max(zs)
        rows = []
        for k in range(14):
            t = k / 13
            x = cx + side * (-BROW_IN + (BROW_IN + BROW_OUT) * t) * w
            zc = ztop + S * (BROW_DZ + 0.046 * t - 0.016 * t * t + BROW_ARCH * math.sin(math.pi * t))   # rising outward; TypeSafe brow_arch
            th = S * (BROW_TH * (1 - float(smooth(BROW_TAPER, 1.0, np.array(t)))) + 0.0015)
            th *= 1 + BROW_INNER * (1 - float(smooth(0.0, 0.30, np.array(t))))   # heavier inner end (q8)   # thick for a third, then tapering
            lo, hi = zc - th * 0.45, zc + th * 0.55
            if k == 0:
                lo = lo + th * 0.55                                       # inner end cut on a diagonal
            pair = []
            for xx, zz in ((x, lo), (x + side * (0.0 if k else 0.012 * S), hi)):
                loc, nrm, _, _ = tree.ray_cast(Vector((xx, -1.0, zz)), Vector((0, 1, 0)))
                pair.append(loc + nrm * 0.0008 if loc is not None else Vector((xx, -0.12, zz)))
            rows.append(tuple(pair))
        if not (EYE_DECAL and EYE_PAINT.get("BROW", 1)):                 # q21: the brow is painted in the eye decal
            made.append(_strip("NewBrow_%s_%s" % (tag, "LR"[side < 0]), rows, brow_m, col, off_x))
    bm.free()
    return made


def face_strokes(ob, col, off_x, tag):
    """MHS3 nose and mouth as flat painted strokes on the skin (each off at 0)."""
    tree = _bvh(ob)
    made = []

    def on_skin(x, z, lift=0.0008):
        # front-most skin around the point: rays that fall into the mouth opening land deep inside it
        best = None
        for dz in (0.0, -0.006, 0.006, -0.012, 0.012):
            loc, nrm, _, _ = tree.ray_cast(Vector((x * S, -1.0, O + (z + dz) * S)), Vector((0, 1, 0)))
            if loc is not None and (best is None or loc.y < best[0].y - 0.0015):
                best = (loc, nrm)
        if best is None:
            return None
        loc, nrm = best
        return Vector((x * S, loc.y, O + z * S)) + Vector((0, -1, 0)) * lift

    def stroke(name, pts, widths, mat, lift=0.0008):
        rows = []
        for i, ((x, z), w) in enumerate(zip(pts, widths)):
            j = min(i + 1, len(pts) - 1); k = max(i - 1, 0)
            tx, tz = pts[j][0] - pts[k][0], pts[j][1] - pts[k][1]
            L = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / L, tx / L
            a_ = on_skin(x - nx * w / 2, z - nz * w / 2, lift); b_ = on_skin(x + nx * w / 2, z + nz * w / 2, lift)
            if a_ is not None and b_ is not None:
                rows.append((a_, b_))
        if len(rows) >= 2:
            made.append(_strip(name + "_" + tag, rows, mat, col, off_x))
    line_m = _emission("MAT_PaintFaceLine_" + tag, (0.12, 0.05, 0.03, 1))
    mouth_m = _emission("MAT_PaintMouth_" + tag, (0.10, 0.025, 0.02, 1))
    shade_m = shade_material(tag) if (NOSE_SHADE or LIP_STYLE == 2) else None
    if NOSE_SHADE:
        # n1: lens under the tip (reference: 0.25 IPD wide, 0.08 IPD tall, just under the hook; IPD = 2 EYE_X)
        ipd = 2 * EYE_X
        n = 11; cx, wd, ht = 0.008 * NOSE_SHADE, 0.25 * ipd * NOSE_SHADE, 0.08 * ipd * NOSE_SHADE
        pts = [(cx - wd / 2 + wd * i / (n - 1), NOSE_Z - 0.006 - ht * 0.45 - 0.004 * (1 - (-1 + 2 * i / (n - 1)) ** 2))
               for i in range(n)]
        wid = [ht * (0.15 + 0.85 * math.sin(math.pi * i / (n - 1)) ** 0.7) for i in range(n)]
        stroke("NewNoseShade", pts, wid, shade_m, lift=0.0011)
    if NOSE_HL:
        # p1 (Leo render): a pale elongated lens down the lit side of the bridge, no dark line there
        hl_m = _emission("MAT_PaintNoseHL_" + tag, (0.86, 0.70, 0.58, 1))
        n = 11; z0_, z1_ = 0.415, 0.300
        pts = [(-0.010 + 0.004 * (i / (n - 1)), z0_ + (z1_ - z0_) * i / (n - 1)) for i in range(n)]
        wid = [0.024 * NOSE_HL * math.sin(math.pi * (0.04 + 0.92 * i / (n - 1))) ** 0.8 * (0.75 + 0.25 * i / (n - 1)) for i in range(n)]
        stroke("NewNoseHL", pts, wid, hl_m, lift=0.0007)
    if NOSE_LINE > 0 and NOSE_STYLE == 2:
        # n1: reference: starts under the brow's inner end, bends in toward the bridge, runs down thin (nearly broken
        # in the middle), heavy at the bottom where it hooks in under the tip into the top of the shadow lens
        ctrl = [(0.048, NOSE_LINE_TOP), (0.046, NOSE_LINE_TOP - 0.04), (0.043, NOSE_LINE_TOP - 0.085),
                (0.040, NOSE_Z + 0.012), (0.034, NOSE_Z - 0.002), (0.018, NOSE_Z - 0.008)]   # p1: from NOSE_LINE_TOP only
        n = 26; pts = []
        for i in range(n):
            t = i / (n - 1) * (len(ctrl) - 1); k = min(int(t), len(ctrl) - 2); f = t - k
            p0, p1 = ctrl[max(k - 1, 0)], ctrl[k]; p2, p3 = ctrl[k + 1], ctrl[min(k + 2, len(ctrl) - 1)]
            cr = lambda a, b, c, d: 0.5 * (2 * b + (c - a) * f + (2 * a - 5 * b + 4 * c - d) * f * f + (3 * b - a - 3 * c + d) * f ** 3)
            pts.append((NOSE_SIDE * cr(p0[0], p1[0], p2[0], p3[0]), cr(p0[1], p1[1], p2[1], p3[1])))
        wid = []
        for i in range(n):
            t = i / (n - 1)
            w_ = 0.0020 * (1 - smooth(0.05, 0.25, t)) + 0.0008 + 0.0042 * smooth(0.62, 0.86, t) * (1 - 0.6 * smooth(0.93, 1.0, t))
            wid.append(w_ * NOSE_LINE)
        stroke("NewNoseLine", pts, wid, line_m)
    elif NOSE_LINE > 0:
        n = 10
        z0, z1 = EYE_Z + 0.02, EYE_Z - (EYE_Z - NOSE_Z - 0.01) * NOSE_LINE_LEN
        pts = [(0.040 + NOSE_LINE_X - 0.012 * (i / (n - 1)) ** 1.5, z0 + (z1 - z0) * i / (n - 1)) for i in range(n)]
        wid = [0.0035 * NOSE_LINE * (0.4 + 0.6 * math.sin(math.pi * min(1.0, 0.15 + i / (n - 1)))) for i in range(n)]
        stroke("NewNoseLine", pts, wid, line_m)
    if NOSTRIL > 0 and NOSE_STYLE != 2:      # n1: the hooked line end is the nostril now
        pts = [(0.012, NOSE_Z - 0.010), (0.022, NOSE_Z - 0.014), (0.030, NOSE_Z - 0.010)]
        stroke("NewNostril", pts, [0.004 * NOSTRIL, 0.006 * NOSTRIL, 0.003 * NOSTRIL], line_m)
    if MOUTH_LINE > 0:
        n = 13
        w = MOUTH_HW * MOUTH_LINE_W
        pts = [(-w + 2 * w * i / (n - 1), MOUTH_Z + 0.004 - 0.010 * ((-1 + 2 * i / (n - 1)) ** 2)) for i in range(n)]
        wid = [0.006 * MOUTH_LINE * (0.25 + 0.75 * math.sin(math.pi * i / (n - 1))) for i in range(n)]
        stroke("NewMouthLine", pts, wid, mouth_m, lift=0.0018)   # clears the lip bulge (it hid the line in dashes)
    if LIP_SHADOW > 0 and LIP_STYLE == 2:
        # n1: reference under-lip shadow: a lens 0.35 IPD wide, ~0.07 IPD tall (open mouth; less for a closed one)
        ipd = 2 * EYE_X
        n = 13; wd, ht = 0.33 * ipd, 0.050 * ipd * LIP_SHADOW
        pts = [(-wd / 2 + wd * i / (n - 1), MOUTH_Z - 0.040 - 0.003 * (1 - (-1 + 2 * i / (n - 1)) ** 2)) for i in range(n)]
        wid = [ht * (0.1 + 0.9 * math.sin(math.pi * i / (n - 1)) ** 0.6) for i in range(n)]
        stroke("NewLipShadow", pts, wid, shade_m, lift=0.0006)
    elif LIP_SHADOW > 0:
        n = 7
        pts = [(-0.03 + 0.06 * i / (n - 1), MOUTH_Z - 0.040 - 0.004 * (1 - (-1 + 2 * i / (n - 1)) ** 2)) for i in range(n)]
        wid = [0.004 * LIP_SHADOW * math.sin(math.pi * i / (n - 1)) + 0.0005 for i in range(n)]
        stroke("NewLipShadow", pts, wid, line_m)
    return made


def stroke_view_keys(col, tag):
    """n11: the nose strokes skip the view-key remap (it made them jagged) and get their own VW- keys instead:
    - camera toward the side the line is on (VW-*_L with NOSE_SIDE -1): the line is on the far side, where the far
      eye's view key slides the eye in toward the nose; its upper part retracts to EYE_Z - NOSE_RETRACT so the line
      no longer crosses the far eye (TypeSafe asked for the higher start, which is right from the front only)
    - camera toward the other side: no key (the line is then on the near side)."""
    far = "L" if NOSE_SIDE < 0 else "R"
    near = "R" if far == "L" else "L"
    zcut = O + (EYE_Z - NOSE_RETRACT) * S
    hl = col.objects.get("NewNoseHL_" + tag)
    if hl is not None:                              # p3: the bridge highlight folds away toward the profile views
        co = np.array([v.co[:] for v in hl.data.vertices])
        rows = co.reshape(-1, 2, 3); mid = rows.mean(1, keepdims=True)
        flat = (mid + (rows - mid) * 0.0).reshape(-1, 3)
        hl.shape_key_add(name="Basis")
        for base in ("VW-Side_L", "VW-Side_R"):
            kb = hl.shape_key_add(name=base); kb.value = 0.0
            kb.data.foreach_set("co", flat.astype(np.float32).ravel())
    for nm in ("NewNoseLine_", "NewNoseShade_"):
        o = col.objects.get(nm + tag)
        if o is None:
            continue
        me = o.data
        co = np.array([v.co[:] for v in me.vertices])
        o.shape_key_add(name="Basis")
        mir = co.copy(); mir[:, 0] *= -1
        ret = co.copy()
        if nm == "NewNoseLine_":
            rows = co.reshape(-1, 2, 3)
            k = next((i for i in range(len(rows)) if rows[i, :, 2].mean() <= zcut), 0)
            r2 = rows.copy(); r2[:k] = rows[k]
            ret = r2.reshape(-1, 3)
        keys = [(far, ret)]                         # n12: no mirror keys (the blend swept the strokes through the nose)
        if nm == "NewNoseLine_" and NOSE_FRONT_HIDE:
            # p8 (TypeSafe nose_line_off, Leo front: no dark line on the nose): the line has zero width in the front
            # view and grows in with the yaw / side keys (both sides)
            rows = co.reshape(-1, 2, 3); mid = rows.mean(1, keepdims=True)
            flat = np.repeat(mid, 2, 1).reshape(-1, 3)
            o.data.shape_keys.key_blocks[0].data.foreach_set("co", flat.astype(np.float32).ravel())
            me.vertices.foreach_set("co", flat.astype(np.float32).ravel())
            keys = [(far, ret), (near, co)]
        for kind, arr in keys:
            for base in ("VW-Yaw_", "VW-Side_"):
                kb = o.shape_key_add(name=base + kind); kb.value = 0.0
                kb.data.foreach_set("co", arr.astype(np.float32).ravel())


def load_knobs(eyes_json):
    """Tuned values from blender/newhead/look_knobs.json override the defaults above (the judge loop writes them);
    "paint" holds eye_paint.py overrides."""
    import os
    p = os.path.join(os.path.dirname(eyes_json), "..", "..", "..", "blender", "newhead", "look_knobs.json")
    if not os.path.exists(p):
        return {}
    k = json.load(open(p))
    for name, val in k.items():
        if name == "paint":
            EYE_PAINT.update(val)
        elif name == "view":
            EYE_VIEW.update(val)
        elif name in globals():
            globals()[name] = val
    return k


def run(npz, eyes_json, tag, off_x):
    global EYE_X, EYE_Z, EYE_HW, EYE_HH, MOUTH_Z, MOUTH_HW, NOSE_Z
    load_knobs(eyes_json)
    ej = json.load(open(eyes_json))
    EYE_X, EYE_Z = ej.get("eye_x", EYE_X), ej.get("eye_z", EYE_Z)
    EYE_HW, EYE_HH = ej.get("eye_hw", EYE_HW), ej.get("eye_hh", EYE_HH)
    MOUTH_Z, MOUTH_HW, NOSE_Z = ej.get("mouth_z", MOUTH_Z), ej.get("mouth_hw", MOUTH_HW), ej.get("nose_z", NOSE_Z)
    ob, col, V, D, LID = load(npz, tag, off_x)
    me = ob.data
    P = head_coords(V)
    N = vertex_normals(me)
    global EAR_B
    EAR_B = ear_paint(me, V, N) if EAR_STYLE == 2 else None
    sh = shade_mask(me, P, D, N)
    custom_normals(me, P, D, N)
    me.materials.append(skin_material(tag))
    me.materials.append(outline_material(tag))
    global EAR_ROOT
    EAR_ROOT = ear_root(ob, P)
    outline(ob, P, D)
    if EYE_RIG:
        import os
        exec(open(os.path.join(os.path.dirname(eyes_json), "..", "..", "..", "blender", "newhead", "face_rig.py")).read(), globals())
        build_rig(ob, col, LID, off_x, tag)
        bpy.app.driver_namespace["set_expression"] = set_expression
        bpy.app.driver_namespace["EXPRESSIONS"] = EXPRESSIONS
    else:
        painted_eyes(ob, col, LID, off_x, tag)
    face_strokes(ob, col, off_x, tag)
    if EYE_RIG and VIEW_KEYS:
        exec(open(os.path.join(os.path.dirname(eyes_json), "..", "..", "..", "blender", "newhead", "view_keys.py")).read(), globals())
        add_view_keys(ob, col, tag)
        bpy.app.driver_namespace["view_weights"] = view_weights
        bpy.app.driver_namespace["set_view"] = set_view
        if NOSE_VIEW:
            stroke_view_keys(col, tag)
    if ID_MORPHS:                                  # p1: baked default proportions + the creator's ID- keys
        exec(open(os.path.join(os.path.dirname(eyes_json), "..", "..", "..", "blender", "newhead", "id_morphs.py")).read(), globals())
        bake(col, ob)
        add_id_keys(col, ob)
    if EAR_SPLIT:
        split_ears(ob, col, tag)
    return ob, int((sh < 0.5).sum())


if "NPZ" in globals():
    EYES_PATH = EYES
    _ob, _n = run(NPZ, EYES, TAG, OFF_X)
    print("look applied:", _ob.name, "forced-shadow verts", _n)
