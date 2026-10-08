"""MHS3 look on a new-head build, inside Sammy's Blender (uses the project's NG_ toon groups from blender/scripts/shaders.py).

    exec(open(r"...\\blender\\newhead\\apply_look.py").read(), {"NPZ": npz_path, "EYES": eyes_json, "TAG": "n41", "OFF_X": 1.8})

- Loads the head (npz: V, PL, PS, ear_dark) and the eyeball centres, as collection NEW_HEAD_<TAG>, offset OFF_X in x.
- Skin: NG_ToonSkin; Shadow Mask from a "shade" point attribute (1 lit, 0 forced shadow): ear bowl and rim groove,
  under the nose tip, the jaw underside and the neck right under the jaw (MHS3: the head shades the upper neck).
- Normals: face normals blended toward a head ellipsoid (one clean shadow shape, no nose/cheek noise); the neck toward
  its cylinder; ears and the eye/mouth rims keep their own.
- Eyes: UV sphere eyeballs, UVs projected from the front so the NG_Eye iris faces forward.
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
    return ob, col, V, D


def head_coords(V):
    return np.stack([V[:, 0] / S, V[:, 1] / S, (V[:, 2] - O) / S], 1)


def vertex_normals(me):
    n = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("normal", n)
    return n.reshape(-1, 3)


def shade_mask(me, P, D, N):
    x, y, z = np.abs(P[:, 0]), P[:, 1], P[:, 2]
    shade = np.ones(len(P))
    shade = np.minimum(shade, 1 - 0.75 * smooth(0.35, 0.60, D))                       # ear bowl + rim groove
    nose = (x < 0.035) & (y < -0.36) & (z < NOSE_Z + 0.004) & (z > NOSE_Z - 0.045) & (N[:, 2] < -0.25)
    shade = np.where(nose, 0.25, shade)                                              # under the nose tip
    under = smooth(-0.30, -0.55, N[:, 2]) * (1 - smooth(0.10, 0.16, z)) * (z > -0.05)
    shade = np.minimum(shade, 1 - 0.70 * under)                                       # jaw underside
    ra = np.hypot(P[:, 0] / 0.20, (y - NECK_Y) / (0.20 * 0.92))
    neck = (z < 0.24) & (z > -0.16) & (ra < 1.12)                                     # the whole neck under the head
    edge = 0.30 - 0.10 * np.clip(1 - (P[:, 0] / 0.2) ** 2, 0, 1)                         # up to the jaw floor (no lit collar)
    shade = np.where(neck, np.minimum(shade, 1 - 0.70 * smooth(edge - 0.02, edge + 0.02, z) * (1 - smooth(-0.12, -0.18, z))), shade)
    a = me.attributes.get("shade") or me.attributes.new("shade", "FLOAT", "POINT")
    a.data.foreach_set("value", shade.astype(np.float32))
    return shade


def custom_normals(me, P, D, N):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    c, r = np.array([0.0, -0.02, 0.47]), np.array([0.40, 0.46, 0.56])
    pe = (P - c) / r ** 2
    pe /= np.linalg.norm(pe, axis=1, keepdims=True)
    pc = np.stack([x, y - NECK_Y, np.zeros_like(x)], 1)
    pc /= np.maximum(np.linalg.norm(pc, axis=1, keepdims=True), 1e-9)
    w = 0.96 * smooth(0.04, 0.12, z)                                                  # whole head above the jaw (n41b: 0.8 front-only left a jagged edge)
    de = np.sqrt(((np.abs(x) - EYE_X) / (EYE_HW * 1.5)) ** 2 + ((z - EYE_Z) / (EYE_HH * 2.0)) ** 2)
    w *= 0.55 + 0.45 * smooth(0.9, 1.15, de)                                          # only the lid itself keeps some form
    dm = np.sqrt((x / (MOUTH_HW * 1.6)) ** 2 + ((z - MOUTH_Z) / 0.05) ** 2)
    w *= 0.8 + 0.2 * smooth(0.6, 1.0, dm)
    # MHS3 face plane: the front of the face is turned toward the viewer (lit), the shadow stays on the far cheek
    face = smooth(0.0, -0.25, y) * smooth(0.05, 0.15, z) * (1 - smooth(0.62, 0.75, z))
    pe = pe + np.array([0.0, -0.9, 0.0]) * face[:, None]
    pe /= np.linalg.norm(pe, axis=1, keepdims=True)
    w *= (D < 0.01) & (np.abs(x) < 0.33)                                              # ears keep their own
    wn = 0.8 * (1 - smooth(-0.02, 0.06, z)) * (z > -0.6)                               # neck column
    tgt = pe * w[:, None] + pc * wn[:, None]
    n = N * (1 - w - wn)[:, None] + tgt
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    me.normals_split_custom_set_from_vertices([tuple(v) for v in n])


def skin_material(tag):
    m = bpy.data.materials.get("MAT_NewSkin_" + tag) or bpy.data.materials.new("MAT_NewSkin_" + tag)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (400, 0)
    g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = bpy.data.node_groups["NG_ToonSkin"]
    g.inputs["skin_color"].default_value = SKIN
    g.inputs["blush_strength"].default_value = 0.0
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "shade"; at.location = (-300, -200)
    nt.links.new(at.outputs["Fac"], g.inputs["Shadow Mask"])
    nt.links.new(g.outputs["Shader"], out.inputs["Surface"])
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
        em.inputs["Color"].default_value = (0.30, 0.15, 0.10, 1)      # dark warm brown: a darker shade of the skin
    return m


EAR_ROOT = None


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
    for i in np.nonzero(comp != main)[0]:
        co = me.vertices[i].co
        loc, nrm, _, d = tree.find_nearest(co)
        if loc is not None and ((co - loc).dot(nrm) < 0.003):
            root[i] = True
    return root


def outline(ob, P, D):
    x, z = np.abs(P[:, 0]), P[:, 2]
    front = P[:, 1] < -0.15
    de = np.sqrt(((x - EYE_X) / (EYE_HW * 1.35)) ** 2 + ((z - EYE_Z) / (EYE_HH * 1.6)) ** 2)
    dm = np.sqrt((P[:, 0] / (MOUTH_HW * 1.6)) ** 2 + ((z - MOUTH_Z) / 0.05) ** 2)
    dn = np.sqrt((P[:, 0] / 0.06) ** 2 + ((z - (NOSE_Z + 0.03)) / 0.08) ** 2)
    w = np.ones(len(P))
    for dd, k in ((de, 1.35), (dm, 1.4), (dn, 1.3)):
        w = np.where(front, np.minimum(w, smooth(1.0, k, dd)), w)
    w = np.minimum(w, 1 - 0.5 * smooth(0.35, 0.6, D))                                # thinner inside the ear
    # no outline on the part of the ear that grows out of / sits inside the skull (its hull showed through the skin)
    w = np.where(EAR_ROOT, 0.0, w)
    vg = ob.vertex_groups.get("OutlineWeight") or ob.vertex_groups.new(name="OutlineWeight")
    for i, wi in enumerate(w):
        vg.add([i], float(wi), "REPLACE")
    md = ob.modifiers.get("Outline") or ob.modifiers.new("Outline", "SOLIDIFY")
    md.thickness = 0.0011
    md.offset = 1.0
    md.use_flip_normals = True
    md.use_rim = False
    md.use_even_offset = False
    md.material_offset = 1
    md.vertex_group = "OutlineWeight"
    md.thickness_vertex_group = 0.0


def eyes(col, eyes_json, off_x, tag):
    ej = json.load(open(eyes_json))
    R = ej["eye_r"]
    src = bpy.data.materials.get("MAT_Eye")
    m = bpy.data.materials.get("MAT_NewEye_" + tag)
    if m is None:
        m = src.copy(); m.name = "MAT_NewEye_" + tag
    g = next(n for n in m.node_tree.nodes if n.type == "GROUP")
    for k, v in (("iris_size", 0.66), ("pupil_size", 0.40), ("pupil_slit", 0.0), ("gaze_x", 0.0), ("gaze_y", 0.05),
                 ("iris_color", (0.09, 0.40, 0.11, 1)), ("Lid Shadow", 0.75)):
        g.inputs[k].default_value = v
    out = []
    for i, c in enumerate(ej["eyes"]):
        me = bpy.data.meshes.new("NewEye_%s_%s" % (tag, "LR"[i]))
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=R)
        uv = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            f.smooth = True
            for lp in f.loops:
                p = lp.vert.co
                lp[uv].uv = (0.5 + 0.5 * p.x / R, 0.5 + 0.5 * p.z / R)
        bm.to_mesh(me); bm.free()
        e = bpy.data.objects.new(me.name, me)
        e.location = (c[0] + off_x, c[1], c[2])
        me.materials.append(m)
        col.objects.link(e)
        out.append(e)
    return out


def _bvh(ob):
    from mathutils.bvhtree import BVHTree
    me = ob.data
    return BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])


def _strip(name, rows, mat, col, off_x):
    """rows: list of (inner, outer) world-space points (local to the head object); one quad strip."""
    me = bpy.data.meshes.new(name)
    vs, fs = [], []
    for a, b in rows:
        vs += [tuple(a), tuple(b)]
    for i in range(len(rows) - 1):
        fs.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    me.from_pydata(vs, [], fs); me.update()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); o.location.x = off_x
    col.objects.link(o)
    return o


def lashes_and_brows(ob, col, off_x, tag):
    """MHS3: a thick dark upper lash over the lid edge, heavier toward the outer corner and ending in a wing; a thin
    lower lash on the outer half; thick brush-stroke brows (hair colour) above. Strips sit on the skin, pushed out
    along the surface normal."""
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
    tree = _bvh(ob)
    lash_m = bpy.data.materials.get("MAT_Lash_Line")
    brow_m = bpy.data.materials.get("MAT_Hair_Brows") or lash_m
    made = []
    for side in (1, -1):
        cx, cz = side * EYE_X * S, O + EYE_Z * S
        bnd = [v for v in bm.verts if v.is_boundary and v.co.y < -0.03 and abs(v.co.x - cx) < EYE_HW * 1.6 * S
               and abs(v.co.z - cz) < EYE_HH * 2 * S]                    # front only: the ear root loop sits at eye height
        dist = {v: 0 for v in bnd}; cur = list(bnd)
        for k in range(1, 5):
            nxt = []
            for v in cur:
                for e in v.link_edges:
                    o_ = e.other_vert(v)
                    if o_ not in dist:
                        dist[o_] = k; nxt.append(o_)
            cur = nxt
        lid = [v for v, k in dist.items() if k == 4]                     # the lid edge (opening ring on the skin)
        ang = lambda v: math.atan2(v.co.z - cz, (v.co.x - cx) * side)    # 0 = outer corner, pi = inner corner
        # split the lid ring at its two corners; the upper lid is the arc between them that runs higher
        ring = sorted(lid, key=lambda v: math.atan2(v.co.z - cz, (v.co.x - cx) * side))
        ii = min(range(len(ring)), key=lambda i: (ring[i].co.x - cx) * side)          # inner corner
        oo = max(range(len(ring)), key=lambda i: (ring[i].co.x - cx) * side)          # outer corner
        arc1 = [ring[(oo + k) % len(ring)] for k in range((ii - oo) % len(ring) + 1)]  # outer -> inner, one way
        arc2 = [ring[(ii + k) % len(ring)] for k in range((oo - ii) % len(ring) + 1)]  # inner -> outer, other way
        mz = lambda arc: sum(v.co.z for v in arc) / len(arc)
        up_arc, low_arc = (arc1, arc2) if mz(arc1) > mz(arc2) else (arc2, arc1)
        up = sorted(up_arc, key=lambda v: (v.co.x - cx) * side)                       # inner -> outer
        low_ring = low_arc
        rows = []
        n_ = len(up)
        for i, v in enumerate(up):
            t = i / max(n_ - 1, 1)
            p = v.co.copy(); nrm = v.normal.copy()
            radial = Vector((p.x - cx, 0.0, p.z - cz)); radial.normalize()
            th = (0.010 + 0.020 * t ** 1.4) * S
            inner = p - radial * 0.004 * S + nrm * 0.0012
            outer = p + radial * th + nrm * 0.0016
            rows.append((inner, outer))
        # wing past the outer corner
        if len(rows) >= 2:
            a1, b1 = rows[-1]
            tang = (a1 - rows[-2][0]); tang.normalize()
            wing_dir = (tang + Vector((side * 0.6, 0, 0.55))).normalized()
            for k, f in ((1, 0.55), (2, 0.0)):
                a = a1 + wing_dir * (0.016 * k * S)
                b = a + (b1 - a1) * f + wing_dir * 0.002 * S
                hit = tree.find_nearest(a)
                if hit[0] is not None:
                    a = hit[0] + hit[1] * 0.0016; b = a + (b - a)
                rows.append((a, b))
        made.append(_strip("NewLashUp_%s_%s" % (tag, "LR"[side < 0]), rows, lash_m, col, off_x))
        # lower lash: outer half of the lower lid, thin
        low = sorted([v for v in low_ring if (v.co.x - cx) * side > 0.15 * EYE_HW * S], key=lambda v: (v.co.x - cx) * side)[:-1]
        rows = []
        for i, v in enumerate(low):
            t = i / max(len(low) - 1, 1)
            p = v.co.copy(); nrm = v.normal.copy()
            radial = Vector((p.x - cx, 0.0, p.z - cz)); radial.normalize()
            rows.append((p + nrm * 0.0012, p + radial * (0.003 + 0.006 * t) * S + nrm * 0.0014))
        if len(rows) >= 2:
            made.append(_strip("NewLashLow_%s_%s" % (tag, "LR"[side < 0]), rows, lash_m, col, off_x))
        # brow: thick at the inner end, tapering outward, a gentle arch
        rows = []
        for i in range(12):
            t = i / 11
            x = side * (EYE_X - 0.085 + 0.20 * t) * S
            z = O + (EYE_Z + EYE_HH + 0.060 + 0.022 * math.sin(math.pi * min(1.0, t * 1.15)) - 0.012 * t) * S
            th = (0.030 - 0.018 * t) * S
            res = []
            for zz in (z - th / 2, z + th / 2):
                loc, nrm, _, _ = tree.ray_cast(Vector((x, -1.0, zz)), Vector((0, 1, 0)))
                res.append(loc + nrm * 0.0015 if loc is not None else Vector((x, -0.12, zz)))
            rows.append((res[0], res[1]))
        made.append(_strip("NewBrow_%s_%s" % (tag, "LR"[side < 0]), rows, brow_m, col, off_x))
    bm.free()
    return made


def run(npz, eyes_json, tag, off_x):
    ob, col, V, D = load(npz, tag, off_x)
    me = ob.data
    P = head_coords(V)
    N = vertex_normals(me)
    sh = shade_mask(me, P, D, N)
    custom_normals(me, P, D, N)
    me.materials.append(skin_material(tag))
    me.materials.append(outline_material(tag))
    global EAR_ROOT
    EAR_ROOT = ear_root(ob, P)
    outline(ob, P, D)
    eyes(col, eyes_json, off_x, tag)
    lashes_and_brows(ob, col, off_x, tag)
    return ob, int((sh < 0.5).sum())


if "NPZ" in globals():
    _ob, _n = run(NPZ, EYES, TAG, OFF_X)
    print("look applied:", _ob.name, "forced-shadow verts", _n)
