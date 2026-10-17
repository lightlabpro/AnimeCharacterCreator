"""Sammy's Blender (5.2): bring the v2 head in from the cloud-built .blend and shade it with the shipped toon look.

    exec(open(r"<repo>\\blender\\head_v2\\pc_v2.py").read(), {"BLEND": r"...\\v2.blend", "TAG": "v2"})
    then bpy.app.driver_namespace["v2"]["shots"](name, expr)   # front / 3/4 / side, same cameras as n56 face()

- appends every object of BLEND into collection NEW_HEAD_<TAG> (replacing an older one), hides it from the n56
  renders and hides the n56 head from the v2 renders;
- skin: the n56 toon group (NG_ToonSkin_NewHead) with the n56 skin colour and no masks; painted pieces, teeth, tongue,
  cavity: flat emission (like the n56 rig pieces); outline: an inverted-hull Solidify with the n56 outline material.
"""
import math
import os

import bpy
from mathutils import Vector

BLEND = globals()["BLEND"]
TAG = globals().get("TAG", "v2")
R = globals().get("REPO") or r"D:\Game Development\Tools\Anime Character Creator\AnimeCharacterCreator-main"
Q = os.path.join(R, "docs", "qa", "head_v2")
ZT, H = 1.685, 0.22


def lin(c):
    c = c / 255.0
    return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92


def emission_mat(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission"); out = nt.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Color"].default_value = rgba; em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def skin_mat():
    """The n56 skin material itself (NG_ToonSkin_NewHead fed by n56's analytic normal: an ellipsoid plus a forward
    push over the face front, chin to forehead, mixed with the surface normal by 'an_w'), with its head-size
    constants moved to v2 (head height 0.262 -> H, base height 1.4826 -> chin ZT - H). Same light, same look."""
    name = "MAT_V2Skin_" + TAG
    old = bpy.data.materials.get(name)
    if old:
        bpy.data.materials.remove(old)
    m = bpy.data.materials["MAT_NewSkin_n56"].copy(); m.name = name
    for n in m.node_tree.nodes:
        if n.type == "MATH":
            for i in n.inputs[:2]:
                if i.is_linked:
                    continue
                if abs(i.default_value - 0.262) < 1e-4:
                    i.default_value = H
                elif abs(i.default_value - 1.4826) < 1e-4:
                    i.default_value = ZT - H
    # q23 TypeSafe face_shadow_smaller: the menu's push 2.5 -> 3.2 moved ~500 px (8.0 only ~1200), so the far-cheek band
    # is narrowed with the analytic ellipsoid's x radius instead (n56 a 0.40 -> 0.50 H; x / a^2 in the 'Math.005' divide)
    # q24 TypeSafe cheek_shadow_softer: menu x2 (0.002 -> 0.004) was invisible; Leo's band edge is painted soft ->
    # v2 gets its own copy of the skin group with toon boundary softness SKIN_SOFT (n56 keeps the shared one)
    grp = next((n for n in m.node_tree.nodes if n.type == "GROUP"), None)
    if grp is not None:
        grp.node_tree = grp.node_tree.copy(); grp.node_tree.name = "NG_ToonSkin_" + TAG
        surf = next((n for n in grp.node_tree.nodes if n.type == "GROUP" and n.node_tree.name.startswith("NG_ToonSurface")), None)
        if surf is not None:
            surf.inputs["Softness"].default_value = SKIN_SOFT
            # q29 TypeSafe first_fix skin_soft_shadows (v7b vs Leo, both orders): MHS3's face shadows are painted with soft
            # edges; ours were razor hard, and the baked fringe band a jagged hard edge. v2 gets its own surface group
            # with a wider forced-shadow ramp (the 'shade' mask edge 0.45 +- 0.03 -> +- MASK_SOFT)
            surf.node_tree = surf.node_tree.copy(); surf.node_tree.name = "NG_ToonSurface_" + TAG
            for n in surf.node_tree.nodes:
                if n.type == "MATH" and len(n.inputs) > 1 and abs(n.inputs[0].default_value - 0.45) < 1e-4 \
                        and abs(n.inputs[1].default_value - 0.03) < 1e-4:
                    n.inputs[1].default_value = MASK_SOFT
    add_blush(m)
    nd = m.node_tree.nodes.get("Math.005")
    if nd and nd.operation == "DIVIDE" and abs(nd.inputs[1].default_value - 0.16) < 1e-4:
        nd.inputs[1].default_value = ELL_A * ELL_A
    return m


def add_blush(m):
    """q26 books (Manga Guide 13 'finished faces carry a soft pink blush on the cheeks just under the eyes'; Crilley joy
    blush): the contract's blush_strength as a mask in the skin shader (CLAUDE_BUILD_PROMPT 'IDENTITY SURFACE': shader
    parameters, not extra textures). Two soft ellipses under the outer half of each eye, front-facing only, mixed over
    the toon skin as a flat pink; the value node 'BlushStrength' is the parameter (set_expr raises it for happy/laugh)."""
    EYE_H = 0.445; D = 1.0 - EYE_H                        # mouth_v2_line.py layout (pupil line, pupil-to-chin)
    nt = m.node_tree; N = nt.nodes.new; L = nt.links.new
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    src = out.inputs["Surface"].links[0].from_socket
    geo = N("ShaderNodeNewGeometry"); sep = N("ShaderNodeSeparateXYZ"); L(geo.outputs["Position"], sep.inputs[0])
    sepn = N("ShaderNodeSeparateXYZ"); L(geo.outputs["Normal"], sepn.inputs[0])
    def mth(op, a, b=None, clamp=False):
        n = N("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]
    cx, cz = BLUSH_X * D * H, ZT - (EYE_H + BLUSH_DH * D) * H
    dx = mth("DIVIDE", mth("SUBTRACT", mth("ABSOLUTE", sep.outputs["X"]), cx), BLUSH_RX * D * H)
    dz = mth("DIVIDE", mth("SUBTRACT", sep.outputs["Z"], cz), BLUSH_RZ * D * H)
    r2 = mth("ADD", mth("MULTIPLY", dx, dx), mth("MULTIPLY", dz, dz))
    mr = N("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"
    L(r2, mr.inputs["Value"]); mr.inputs["From Min"].default_value = 0.15; mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value = 1.0; mr.inputs["To Max"].default_value = 0.0
    front = mth("MULTIPLY", mth("SUBTRACT", mth("MULTIPLY", sepn.outputs["Y"], -1.0), 0.25), 2.5, clamp=True)
    bv = N("ShaderNodeValue"); bv.name = bv.label = "BlushStrength"; bv.outputs[0].default_value = BLUSH
    fac = mth("MULTIPLY", mth("MULTIPLY", mr.outputs[0], front), bv.outputs[0], clamp=True)
    em = N("ShaderNodeEmission"); em.inputs["Color"].default_value = tuple(lin(c) for c in BLUSH_RGB) + (1.0,)
    mix = N("ShaderNodeMixShader"); L(fac, mix.inputs[0]); L(src, mix.inputs[1]); L(em.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs["Surface"])


BLUSH = globals().get("BLUSH", 0.12)                       # resting blush; q27: 0.30 read childish beside Leo (none visible)
BLUSH_RGB = (236, 140, 132)
BLUSH_X, BLUSH_DH, BLUSH_RX, BLUSH_RZ = 0.42, 0.24, 0.13, 0.055   # D units: centre |x|, below eye line, radii


# shading knobs, overridable from the exec globals (q24: A = v2 look used 0.0009 / 0.40 / 0.002)
OUTLINE_T = globals().get("OUTLINE_T", 0.0016)
ELL_A = globals().get("ELL_A", 0.50)
SKIN_SOFT = globals().get("SKIN_SOFT", 0.03)
MASK_SOFT = globals().get("MASK_SOFT", 0.03)


def import_blend():
    cname = "NEW_HEAD_" + TAG
    old = bpy.data.collections.get(cname)
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o)
        bpy.data.collections.remove(old)
    col = bpy.data.collections.new(cname); bpy.context.scene.collection.children.link(col)
    with bpy.data.libraries.load(BLEND, link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    for o in dst.objects:
        if o is None or o.type != "MESH":
            continue
        col.objects.link(o)
    return col


def shade(col):
    skin = skin_mat()
    outline = bpy.data.materials["MAT_Outline_NewHead_n56"]
    for o in col.objects:
        base = o.name.split(".")[0]
        if base == "V2_HeadNrmProxy":
            continue
        if base == "V2_Head":
            mats = list(o.data.materials)
            o.data.materials[0] = skin
            for i, m in enumerate(mats[1:], 1):
                c = m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
                o.data.materials[i] = emission_mat("MAT_%s_%s" % (m.name.split(".")[0], TAG), tuple(c))
            prox = next((p for p in col.objects if p.name.startswith("V2_HeadNrmProxy")), None)
            # Blender renders: drop the baked custom normals (they are carried through shape keys in noisy
            # per-face spaces -> speckles where the jaw moves) and take live normals from the smoothed proxy
            bpy.context.view_layer.objects.active = o
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
                bpy.ops.mesh.customdata_custom_splitnormals_clear()
            if prox is not None:
                prox.hide_render = True
                dt = o.modifiers.new("SmoothNormals", "DATA_TRANSFER"); dt.object = prox
                dt.use_loop_data = True; dt.data_types_loops = {"CUSTOM_NORMAL"}
                dt.loop_mapping = "POLYINTERP_NEAREST"; dt.vertex_group = "smooth_n"
            o.data.materials.append(outline)
            sm = o.modifiers.new("Outline", "SOLIDIFY"); sm.thickness = OUTLINE_T; sm.offset = 1.0   # q23 outline_thicker 0.0009 -> 0.0016
            sm.use_flip_normals = True; sm.use_rim = False; sm.material_offset = len(o.data.materials) - 1
            o.data.name = "V2_Head_" + TAG; o.name = "V2_Head_" + TAG
        else:
            m = o.data.materials[0]
            c = m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
            o.data.materials[0] = emission_mat("MAT_%s_%s" % (base, TAG), tuple(c))
            if base.startswith(("V2Teeth", "V2Tongue")):
                o.data.materials.append(outline)
                sm = o.modifiers.new("Outline", "SOLIDIFY"); sm.thickness = 0.0004; sm.offset = 1.0
                sm.use_flip_normals = True; sm.use_rim = False; sm.material_offset = 1


EXPR = {
    "neutral": {}, "jaw": {"PF-JawOpen": 1.0}, "jaw_half": {"PF-JawOpen": 0.5},
    # the app's e2e presets (scripts/e2e_head_pack.cjs) and a few readable expressions
    "smile_open": {"PF-SmileOpenJaw": 1.0, "PF-JawOpen": 0.35}, "talk_aa": {"PF-VisAA": 0.8},
    "blink": {"PF-Blink_L": 1.0, "PF-Blink_R": 1.0},
    # q26 presets from the book rules (face gate): happy = closed smile, cheeks up, eyes narrowed into curves;
    # laugh = open D smile, eyes closed into upward arcs; angry = brows down hard, lids lowered, teeth bared;
    # sad = brows rising to the centre, heavy lids, small frown; surprised = eyes wide, brows up, small round mouth
    # v5b (gate on v5a): happy regressed vs v4l and failed "open smile, eyes narrowed into curves"; laugh failed "eyes
    # squeezed shut into ^ arcs + blush"; angry failed "mouth open showing teeth"; brow keys were too weak (face_paint)
    "happy": {"PF-SmileOpenJaw": 0.6, "PF-JawOpen": 0.12, "PF-Squeeze": 0.45, "PF-LidLowerUp": 0.7, "PF-BrowRaise": 0.35,
              "_blush": 0.55},
    "laugh": {"PF-SmileOpenJaw": 1.0, "PF-JawOpen": 0.45, "PF-Squeeze": 1.0, "PF-BrowRaise": 0.5, "_blush": 0.75},
    "angry": {"PF-BrowFurrow": 1.0, "PF-BrowLower": 0.8, "PF-LidUpperDown": 0.40, "PF-Squint": 0.45, "PF-Grimace": 1.0},
    "sad": {"PF-BrowSad": 1.0, "PF-BrowInnerUp": 0.5, "PF-Frown": 0.8, "PF-LidUpperDown": 0.85},   # irises tucked under the lids
    "surprised": {"PF-EyeWide": 1.0, "PF-BrowRaise": 1.0, "PF-VisOH": 0.8},
    "talk_oh": {"PF-VisOH": 0.9}, "talk_ee": {"PF-VisEE": 0.9},
}


def set_expr(col, expr):
    vals = EXPR[expr] if isinstance(expr, str) else expr
    m = bpy.data.materials.get("MAT_V2Skin_" + TAG)
    bn = m.node_tree.nodes.get("BlushStrength") if m else None
    if bn is not None:                                      # contract blush_strength: a skin shader parameter
        bn.outputs[0].default_value = vals.get("_blush", BLUSH)
    for o in col.objects:
        sk = o.data.shape_keys
        if sk:
            for kb in sk.key_blocks[1:]:
                kb.value = vals.get(kb.name, 0.0)


def shots(name, expr="neutral", views=(("front", 0), ("34", 35), ("side", 90)), ortho=0.30, cz=ZT - 0.62 * H,
          res=600, dx=0.0):
    sc = bpy.context.scene
    col = bpy.data.collections["NEW_HEAD_" + TAG]
    keep = set(col.objects)
    hidden = [o for o in sc.objects if o.type in ("MESH", "CURVE", "EMPTY") and o not in keep and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    ch = col.hide_render; col.hide_render = False
    old_cam, old = sc.camera, (sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath)
    cd = bpy.data.cameras.new("V2Cam"); cd.type = "ORTHO"; cd.ortho_scale = ortho
    cam = bpy.data.objects.new("V2Cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    sc.render.resolution_x = sc.render.resolution_y = res
    os.makedirs(Q, exist_ok=True)
    out = []
    lights = mhs3_lights()
    try:
        set_expr(col, expr)
        for label, yaw in views:
            a = math.radians(yaw)
            tgt = Vector((dx * math.cos(a), dx * math.sin(a), cz))
            cam.location = tgt + Vector((math.sin(a), -math.cos(a), 0.0)) * 2.0
            cam.rotation_euler = (math.radians(90), 0.0, a)
            sc.render.filepath = os.path.join(Q, "%s_%s.png" % (name, label))
            bpy.context.view_layer.update()
            bpy.ops.render.render(write_still=True)
            out.append(sc.render.filepath)
    finally:
        lights()
        set_expr(col, "neutral")
        sc.camera = old_cam
        sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath = old
        bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
        col.hide_render = ch
        for o in hidden:
            o.hide_render = False
    return out


# q27 TypeSafe first_fix face_side_shadow (v5f vs Leo, both menu orders): the face rendered as one flat colour. The scene's
# KeySun came from the front-left almost straight on, FillSun lit the other side from behind (summed into the same
# toon diffuse, so no side ever fell under the threshold) and neither cast shadows (no hair shadow on the forehead).
# MHS3 Leo: key from the viewer's right, above and in front -> a broad shadow down the left cheek, a hard cast shadow
# of the fringe on the forehead. The board lights are set only while rendering and restored afterwards.
KEY_FROM = globals().get("KEY_FROM", (0.72, -0.50, 0.48))   # q27: k2 of 3 tried gave the outer-cheek band (Leo)
#   # direction TO the light (x right on the front view, -y front)
KEY_ANGLE = globals().get("KEY_ANGLE", 0.5)                  # sun angle in degrees (hard edged cast shadows)
FILL_ENERGY = globals().get("FILL_ENERGY", 0.0)


def mhs3_lights():
    """Set the MHS3 board lighting; returns a function that restores the scene."""
    sc = bpy.context.scene
    key = sc.objects.get("KeySun"); fill = sc.objects.get("FillSun")
    saved = []
    if key is not None:
        saved.append((key, key.rotation_euler.copy(), key.data.use_shadow, key.data.angle))
        d = Vector(KEY_FROM).normalized()
        key.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        key.data.use_shadow = True; key.data.angle = math.radians(KEY_ANGLE)
    fe = None
    if fill is not None:
        fe = fill.data.energy; fill.data.energy = FILL_ENERGY
    om = bpy.data.materials.get("MAT_Outline_NewHead_n56")
    ob = None
    if om is not None and hasattr(om, "use_backface_culling_shadow"):
        ob = om.use_backface_culling_shadow; om.use_backface_culling_shadow = True   # the hull must not shadow the face

    def restore():
        for o, r, sh, an in saved:
            o.rotation_euler = r; o.data.use_shadow = sh; o.data.angle = an
        if fill is not None and fe is not None:
            fill.data.energy = fe
        if ob is not None:
            om.use_backface_culling_shadow = ob
    return restore


FRINGE_SHADOW = globals().get("FRINGE_SHADOW", True)
FRINGE_FROM = globals().get("FRINGE_FROM", (0.30, -0.45, 1.0))   # steep: the painted MHS3 band under the fringe
FRINGE_REACH = globals().get("FRINGE_REACH", 0.05)                # metres from the skin to the hair along the ray
FRINGE_LOW = globals().get("FRINGE_LOW", 0.40)                    # lowest shadowed point, H below the skull top
FRINGE_BLUR = globals().get("FRINGE_BLUR", 6)


def bake_fringe_shadow(col):
    """q27 (TypeSafe face_side_shadow; Leo has a hard darker band across the forehead under the fringe): the fringe
    hugs the forehead, so a real sun shadow barely shows - MHS3 paints it. Bake it into the head's forced-shadow
    attribute 'shade' (NG_ToonSurface: < ~0.42 forced shadow, < ~0.1 the deeper tint): from every front-facing head
    vertex cast a ray toward FRINGE_FROM; a hit on the hair within FRINGE_REACH puts the vertex in shadow."""
    from mathutils.bvhtree import BVHTree
    head = next(o for o in col.objects if o.name.startswith("V2_Head_"))
    hair = [o for o in col.objects if o.name.startswith("Hair_")]
    if not hair:
        return 0
    verts, polys = [], []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in hair:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        off = len(verts); mw = o.matrix_world
        verts += [mw @ v.co for v in me.vertices]
        polys += [[off + i for i in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    bvh = BVHTree.FromPolygons(verts, polys)
    me = head.data
    att = me.attributes.get("shade")
    if att is None:
        att = me.attributes.new("shade", "FLOAT", "POINT")
        for d in att.data:
            d.value = 1.0
    L = Vector(FRINGE_FROM).normalized()
    mw = head.matrix_world
    zmin = ZT - FRINGE_LOW * H                            # forehead / temples only (q27c: side hair spotted the cheek)
    hitv = [0.0] * len(me.vertices)
    for v in me.vertices:
        nw = (mw.to_3x3() @ v.normal).normalized()
        if nw.y > -0.2 or nw.dot(L) <= 0.0 or (mw @ v.co).z < zmin:
            continue
        p = mw @ v.co + nw * 0.0006
        if bvh.ray_cast(p, L, FRINGE_REACH)[0] is not None:
            hitv[v.index] = 1.0
    # q27c: per-vertex hits stair-stepped the edge -> blur over the mesh, then threshold softly in the shader
    nb = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices; nb[a].append(b); nb[b].append(a)
    for _ in range(FRINGE_BLUR):
        hitv = [0.5 * h + 0.5 * (sum(hitv[j] for j in nb[i]) / len(nb[i]) if nb[i] else h) for i, h in enumerate(hitv)]
    n = 0
    for d, h in zip(att.data, hitv):
        if h > 0.0:
            d.value = min(d.value, 1.0 - 0.75 * min(1.0, 2.0 * h)); n += int(h > 0.5)
    me.update()
    return n


def attach_hair(col, style="leo", src_tag="n56", k=0.90, dz=-0.004):   # q23 TypeSafe hair_fit_lower_wider
    """Copy an n56 hair style onto v2 for the boards (MHS3 heads are read through their hair): every hair object is
    moved from the n56 head (x 2.4, chin 1.4826, head height 0.262) onto v2 (x 0, chin ZT - H, H) and scaled by
    H / 0.262 ~ 0.845 about the skull middle. Same materials / outline."""
    from mathutils import Matrix
    src = bpy.data.collections.get("NEW_HAIR_%s_%s" % (style, src_tag))
    if src is None:
        return 0
    c0 = Vector((2.4, 0.0, 1.4826 + 0.5 * 0.262)); c1 = Vector((0.0, 0.006, ZT - 0.5 * H + dz))
    # q27 TypeSafe first_fix hair_fuller (v6g vs Leo, both orders): Leo's hair rises ~1.07 D above the pupils with
    # full volume, ours 0.79 D hugging the skull -> extra height / width about the skull middle
    sz, sxy = globals().get("HAIR_SZ", 1.0), globals().get("HAIR_SXY", 1.0)
    Sm = Matrix.Diagonal((k * sxy, k * sxy, k * sz, 1.0))
    M = Matrix.Translation(c1) @ Sm @ Matrix.Translation(-c0)
    n = 0
    for o in list(src.all_objects):   # snapshot: linking copies while iterating crashed Blender 5.2 (Collection_all_objects_next)
        if o.type != "MESH":
            continue
        cp = o.copy(); cp.data = o.data.copy(); cp.name = o.name.replace(src_tag, TAG) + "_v2"
        cp.matrix_world = M @ o.matrix_world
        cp.visible_shadow = True                          # q27: MHS3 fringe casts a hard shadow on the forehead
        cp.hide_render = False; cp.hide_viewport = True   # render-only: showing ~all hair copies in the viewport froze Blender (q23)
        col.objects.link(cp); n += 1
    return n


HAIR_HL_BAND = globals().get("HAIR_HL_BAND", (0.12, 0.55))
HAIR_STROKES = globals().get("HAIR_STROKES", (4.0, 1.3, 0.09))    # u / v frequency, width; v7e (7, 15) drew diagonal zebra hatching
HAIR_PLANE = globals().get("HAIR_PLANE", 0.45)                     # strength of the lighter third tone


def hair_paint(m):
    """q29 TypeSafe first_fix hair_painted_streaks (v7d vs Leo, both orders + tie-break): Leo's hair carries many thin
    pale painted streaks and three tones; hair_nh's strokes were a few wide stripes in a narrow band (u*3 + v*9, 0.22).
    Thinner, denser strokes over a longer band, plus a soft lighter plane on the lit side of each clump."""
    if m is None or not m.use_nodes:
        return
    nt = m.node_tree
    fu, fv, wd = HAIR_STROKES
    for n in nt.nodes:
        if n.type != "MATH":
            continue
        a = n.inputs[1].default_value if len(n.inputs) > 1 else None
        if n.operation == "MULTIPLY" and a is not None and abs(a - 3.0) < 1e-6:
            n.inputs[1].default_value = fu
        elif n.operation == "MULTIPLY" and a is not None and abs(a - 9.0) < 1e-6:
            n.inputs[1].default_value = fv
        elif n.operation == "LESS_THAN" and a is not None and abs(a - 0.22) < 1e-6:
            n.inputs[1].default_value = wd
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    src = out.inputs["Surface"].links[0].from_socket
    uv = nt.nodes.new("ShaderNodeUVMap"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(uv.outputs[0], sep.inputs[0])
    ash = next((n for n in nt.nodes if n.type == "ATTRIBUTE" and n.attribute_name == "hair_shade"), None)
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"
    nt.links.new(sep.outputs[1], mr.inputs["Value"])
    mr.inputs["From Min"].default_value = 0.05; mr.inputs["From Max"].default_value = 0.30
    mr2 = nt.nodes.new("ShaderNodeMapRange"); mr2.interpolation_type = "SMOOTHSTEP"
    nt.links.new(sep.outputs[1], mr2.inputs["Value"])
    mr2.inputs["From Min"].default_value = 0.70; mr2.inputs["From Max"].default_value = 0.35
    across = nt.nodes.new("ShaderNodeMath"); across.operation = "SINE"              # strongest across the clump middle
    mu = nt.nodes.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = math.pi
    nt.links.new(sep.outputs[0], mu.inputs[0]); nt.links.new(mu.outputs[0], across.inputs[0])
    f1 = nt.nodes.new("ShaderNodeMath"); f1.operation = "MULTIPLY"; nt.links.new(mr.outputs[0], f1.inputs[0]); nt.links.new(mr2.outputs[0], f1.inputs[1])
    f2 = nt.nodes.new("ShaderNodeMath"); f2.operation = "MULTIPLY"; nt.links.new(f1.outputs[0], f2.inputs[0]); nt.links.new(across.outputs[0], f2.inputs[1])
    f3 = nt.nodes.new("ShaderNodeMath"); f3.operation = "MULTIPLY"; f3.use_clamp = True
    nt.links.new(f2.outputs[0], f3.inputs[0])
    if ash is not None:
        nt.links.new(ash.outputs["Fac"], f3.inputs[1])
    else:
        f3.inputs[1].default_value = 1.0
    f4 = nt.nodes.new("ShaderNodeMath"); f4.operation = "MULTIPLY"; f4.inputs[1].default_value = HAIR_PLANE
    nt.links.new(f3.outputs[0], f4.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = tuple(lin(c) for c in (196, 156, 108)) + (1.0,)
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(f4.outputs[0], mx.inputs[0]); nt.links.new(src, mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])


def build_fitted_hair(col, style="leo"):
    """q29: the boards wore the n56 hair moved and scaled onto v2 (attach_hair), built for another skull - gaps, a
    shell off the scalp and blotchy fringe shadows. Rebuild the hair with blender/newhead/hair_nh.py ON the v2 skull:
    a temporary copy of the v2 head is scaled to the n56 head size / chin height (hair_nh's clump sizes and offsets
    are tuned in metres for it), the clumps are fitted to that scalp by ray casts, then mapped back onto v2."""
    from mathutils import Matrix
    head = next(o for o in col.objects if o.name.startswith("V2_Head_"))
    me = head.data
    kb = me.shape_keys.key_blocks[0] if me.shape_keys else None
    co = [kb.data[i].co.copy() if kb else v.co.copy() for i, v in enumerate(me.vertices)]
    top = max(c.z for c in co)
    chin = min(c.z for c in co if abs(c.x) < 0.006 and c.y < -0.03 and c.z < top - 0.15)
    Hh = top - chin
    s = 0.262 / Hh
    A = Matrix.Translation((0, 0, 1.4826)) @ Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation((0, 0, -chin))
    tmp_me = bpy.data.meshes.new("NEW_Head_fit")
    tmp_me.from_pydata([tuple(A @ c) for c in co], [], [tuple(p_.vertices) for p_ in me.polygons]); tmp_me.update()
    tmp = bpy.data.objects.new("NEW_Head_fit", tmp_me)
    tcol = bpy.data.collections.get("NEW_HEAD_fit") or bpy.data.collections.new("NEW_HEAD_fit")
    if tcol.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(tcol)
    for o in list(tcol.objects):
        bpy.data.objects.remove(o)
    tcol.objects.link(tmp)
    hp = os.path.join(R, "blender", "newhead", "hair_nh.py")
    g = {"__name__": "hair_nh", "HAIR_PATH": hp}
    exec(open(hp, encoding="utf-8").read(), g)
    g["HAIR_CAST"] = 0                                    # v2 bakes its own fringe band (bake_fringe_shadow)
    g["HL_BAND"] = HAIR_HL_BAND
    hcol, made = g["build_hair"](style, tag="fit", off_x=0.0)
    hair_paint(bpy.data.materials.get("MAT_Hair_" + style))
    om = bpy.data.materials.get("MAT_Outline_NewHead_n56")
    Ainv = A.inverted()
    n = 0
    for o in made:
        o.matrix_world = Ainv @ o.matrix_world
        if om is not None and not any(m_.type == "SOLIDIFY" for m_ in o.modifiers):
            g["_outline"](o, om)
            for m_ in o.modifiers:
                if m_.type == "SOLIDIFY":
                    m_.thickness = m_.thickness / s
        o.name = o.name + "_v2"; o.visible_shadow = True
        o.hide_render = False; o.hide_viewport = True
        hcol.objects.unlink(o); col.objects.link(o); n += 1
    bpy.data.objects.remove(tmp)
    return n


GATE_EXPR = ("happy", "laugh", "angry", "sad", "surprised", "talk_aa", "smile_open", "blink")


def gate_shots(tag, exprs=GATE_EXPR, res=800):
    """q26 face gate render set (typesafe_face_gate.py reads it): docs/qa/head_v2/gate/<tag>/front.png, 34.png,
    side.png and expr_<name>.png, framed on the face (ortho 0.24 about the mid face) so features are readable."""
    out = os.path.join(Q, "gate", tag); os.makedirs(out, exist_ok=True)
    cz = ZT - 0.55 * H
    shots("gate_tmp", "neutral", views=(("front", 0), ("34", 35), ("side", 90)), ortho=0.24, cz=cz, res=res)
    for v in ("front", "34", "side"):
        os.replace(os.path.join(Q, "gate_tmp_%s.png" % v), os.path.join(out, "%s.png" % v))
    for e in exprs:
        if e not in EXPR:
            continue
        shots("gate_tmp", e, views=(("front", 0),), ortho=0.24, cz=cz, res=res)
        os.replace(os.path.join(Q, "gate_tmp_front.png"), os.path.join(out, "expr_%s.png" % e))
    return out


col = import_blend()
shade(col)
if globals().get("HAIR_FIT", True) and globals().get("HAIR", "leo"):
    print("fitted hair objects:", build_fitted_hair(col, globals().get("HAIR", "leo")))
elif globals().get("HAIR", "leo"):
    print("hair objects:", attach_hair(col, globals().get("HAIR", "leo"), k=globals().get("HAIR_K", 0.90), dz=globals().get("HAIR_DZ", -0.004)))
if globals().get("HAIR", "leo") and FRINGE_SHADOW:
    print("fringe shadow verts:", bake_fringe_shadow(col))
col.hide_render = True                     # n56 renders stay as they were
bpy.app.driver_namespace["v2"] = {"shots": shots, "set_expr": set_expr, "col": col, "gate_shots": gate_shots}
print("v2 imported:", len(col.objects), "objects")
