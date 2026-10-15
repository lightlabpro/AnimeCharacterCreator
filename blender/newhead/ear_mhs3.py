"""q13 ears: a clean anime ear rebuilt after the MHS3 Leo render (exec'd in apply_look.py's globals after split_ears).

Sammy: "The ears look horrible." The wireframe (wire_ep3_*) showed why: the old ear was a flat oval disc with a
two-level Subdivision (a dense, hole-speckled patch glued to the side of the head), and its toon paint was one round
mauve bowl. The MHS3 ear (docs/reference/mhs3/MHST3-Leo_Render_001.webp, crop docs/qa/newhead/ref_leo_ear_hr.png):
- a narrow ear (width ~0.5 x height), top at the brow line, lobe at the nose base, leaning back
- the helix rim rolls over along the top and back edge (lit, outlined)
- a dark crescent just inside the rim at the top (scapha / triangular fossa)
- the antihelix: a lit ridge between that crescent and the concha
- the concha: one deep dark bowl in the middle front, narrowing downward into the lobe like a "?" mark
- a small tragus bump on the front edge, a soft solid lobe

Built per side on a quad grid (square -> disk -> ear outline), with a relief along the ear normal, a Solidify for
thickness, one Subdivision level and the head's outline shell. The dark shapes go into the head material's own ear
attributes (ear_bowl = mauve recess, ear_f / ear_lw = thin line round the concha), so the ear uses the same toon skin.
Placement comes from the old ear (its centre, plane and long axis), so the ear keeps its position and the creator's
ID-EarSize / ID-EarSize_Neg / ID-EarOut keys are rebuilt on the new mesh (same amounts as id_morphs.ID_AMOUNTS).
"""
import math

import bmesh
import bpy
import numpy as np

EAR_N = 16              # grid cells per side (front face): 256 quads per ear before the Subdivision level
EAR_H_SCALE = 1.06      # new height / old ear height
EAR_WH = 0.52           # width / height
EAR_FWD = 0.0           # move the ear forward (+) / back (-) along the head, x height
EAR_THICK = 0.0030      # m
EAR_CUP = 0.0012        # m: rim stands off more than the centre (the ear is a shallow cup, open to the side)
EAR_FLARE_ADJ = 16.0    # deg: plane turn about the front edge (little effect: the per-vertex clearance sets the stand-off)
EAR_SUBDIV_NEW = 1
EAR_LINE_ON = 0.0      # q13: the thin line round the dark shapes drew a pale halo; off
EAR_LIT_K = 0.85       # q13d: share of the lit direction in the ear normals
EAR_AN_W = 0.0         # share of the head's smooth normal in the ear's shading (lit like the skin beside it)
EAR_STANDOFF = 0.020    # m: back edge off the skin at mid height (front view shows the ear like the old shell, ~20 mm)
EAR_BASE = 0.0045       # m: the ear plane's height over the skin just behind the attached front edge (the concha bowl sits ~5 mm deep)   # m: the back edge stands this far off the skin
EAR_TOP_CURL = 0.0      # m (q13c: off - the rounded stand-off replaces it)
EAR_SO_B0, EAR_SO_R = 0.15, 1.10   # stand-off profile over the height (ear units): widest a little above the middle
EAR_SINK = 0.0015      # m: the front edge sinks this far into the skin
EAR_RELIEF = 1.0        # scales the whole relief
EAR_DARK = 1.0          # scales the painted dark shapes


def _e_sm(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _e_win(th, a0, a1, soft):
    """Smooth window on the angle (degrees, 0 = front, 90 = top, 180 = back, 270 = bottom)."""
    return _e_sm(a0 - soft, a0 + soft, th) * (1 - _e_sm(a1 - soft, a1 + soft, th))


def ear_grid(n):
    """Quad grid on the unit disk (elliptical square-to-disk map): returns xy (N,2) and the quad index list."""
    s = np.linspace(-1, 1, n + 1)
    X, Y = np.meshgrid(s, s)
    dx = X * np.sqrt(1 - Y ** 2 / 2); dy = Y * np.sqrt(1 - X ** 2 / 2)
    xy = np.stack([dx.ravel(), dy.ravel()], 1)
    q = []
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            q.append((a, a + 1, a + n + 2, a + n + 1))
    return xy, q


# outline traced off the Leo ear (ref_leo_ear_hr.png), ear-plane units of half the height: a forward (toward the face),
# b up. Broad round top, nearly straight back edge, lobe narrowing toward the front, straight attached front edge.
EAR_OUTLINE = [(0.30, 0.78), (0.10, 0.98), (-0.14, 1.00), (-0.34, 0.88), (-0.46, 0.60), (-0.50, 0.25), (-0.46, -0.12),
               (-0.36, -0.48), (-0.20, -0.80), (0.00, -0.96), (0.16, -0.92), (0.26, -0.70), (0.30, -0.40), (0.33, -0.05),
               (0.34, 0.35)]
EAR_CENTRE = (-0.06, 0.05)


def _catmull_closed(P, n=24):
    P = np.asarray(P, float); m = len(P); out = []
    for i in range(m):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % m], P[(i + 2) % m]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)


def _outline_r(th_deg):
    C = _catmull_closed(EAR_OUTLINE) - np.array(EAR_CENTRE)
    ang = np.degrees(np.arctan2(C[:, 1], C[:, 0])) % 360.0
    r = np.hypot(C[:, 0], C[:, 1])
    o = np.argsort(ang); ang, r = ang[o], r[o]
    ang = np.concatenate([ang - 360, ang, ang + 360]); r = np.concatenate([r, r, r])
    return np.interp(th_deg, ang, r)


def ear_shape(xy):
    """Disk point -> ear-plane coords (a forward, b up; units of half height) + relief h (x height) + dark (0..1)."""
    rho = np.hypot(xy[:, 0], xy[:, 1])
    th = np.degrees(np.arctan2(xy[:, 1], xy[:, 0])) % 360.0
    R = _outline_r(th)
    a = EAR_CENTRE[0] + rho * R * np.cos(np.radians(th)) * EAR_WH / 0.42
    b = EAR_CENTRE[1] + rho * R * np.sin(np.radians(th))
    h = np.zeros(len(xy))
    rim = _e_win(th, 35, 255, 15)                                  # helix: from the front-top over the top, down the back
    h += 0.030 * np.exp(-((rho - 0.93) / 0.07) ** 2) * rim         # helix roll (lit, outlined)
    fos = np.exp(-((rho - 0.75) / 0.075) ** 2) * _e_win(th, 70, 175, 16)       # upper crescent (scapha / fossa)
    h -= 0.022 * fos
    anti = np.exp(-((rho - 0.56) / 0.09) ** 2) * _e_win(th, 70, 250, 25)      # antihelix ridge (lit)
    h += 0.016 * anti
    # concha: a narrow upright bowl in front of the antihelix, curving down and forward toward the lobe ("?" shape)
    def _blob(a0, b0, ra, rb):
        return np.exp(-((((a - a0) / ra) ** 2 + ((b - b0) / rb) ** 2)) ** 1.6)
    con = np.maximum(_blob(-0.04, 0.12, 0.21, 0.36), 0.95 * _blob(0.07, -0.22, 0.14, 0.24))   # upper bowl toward the back, tail curving forward and down
    h -= 0.065 * con
    h += 0.022 * _blob(0.30, -0.16, 0.09, 0.12)                   # tragus
    lobe = np.clip(-(b - EAR_CENTRE[1]) - 0.55, 0, 1) / 0.45
    h += 0.012 * lobe * (1 - rho)                                   # fuller lobe
    h *= EAR_RELIEF
    dark = np.clip(np.maximum(1.25 * con, 1.15 * fos) * EAR_DARK, 0, 1)
    return a, b, h, dark, rho, th


EAR_TILT_KEEP = 0.35    # share of the old ear's downward facing kept (MHS3 ears face sideways)
EAR_LEAN = 15.0         # deg: the ear's long axis leans back from vertical (side view)


def _e_frame(P):
    """Old ear centre and plane normal (PCA); the up axis is rebuilt: world up in the ear plane, leaning back."""
    c = P.mean(0)
    U, S_, Vt = np.linalg.svd(P - c, full_matrices=False)
    nrm = Vt[2]
    if nrm[0] * np.sign(c[0]) < 0:
        nrm = -nrm
    nrm = nrm * np.array([1.0, 1.0, EAR_TILT_KEEP]); nrm /= np.linalg.norm(nrm)   # q13: the old shell faced ~22 deg down
    z = np.array([0.0, 0.0, 1.0])
    up = z - nrm * (z @ nrm); up /= np.linalg.norm(up)
    back = np.cross(nrm, up)                       # in-plane horizontal
    if back[1] < 0:
        back = -back                               # +y is the back of the head
    lean = math.radians(EAR_LEAN)
    up = up * math.cos(lean) + back * math.sin(lean)
    fwd = np.cross(up, nrm)
    if fwd[1] > 0:
        fwd = -fwd
    return c, up, fwd, nrm


def _e_rot(v, axis, ang):
    axis = axis / np.linalg.norm(axis)
    return v * math.cos(ang) + np.cross(axis, v) * math.sin(ang) + axis * np.dot(axis, v) * (1 - math.cos(ang))


def build_side(P_old, tag_side, tree=None):
    c, up, fwd, nrm = _e_frame(P_old)
    d = P_old - c
    H0 = np.ptp(d @ up); fmax = (d @ fwd).max()
    H = H0 * EAR_H_SCALE
    xy, quads = ear_grid(EAR_N)
    a, b, h, dark, rho, th = ear_shape(xy)
    # the new ear's front edge stays where the old one was (attached to the head); the flare turns about that edge
    a_front = (a.max()) * H / 2
    hinge = c + fwd * (fmax + EAR_FWD * H)
    if EAR_FLARE_ADJ:
        nrm = _e_rot(nrm, up, math.radians(EAR_FLARE_ADJ) * np.sign(c[0]))
        fwd = np.cross(up, nrm); fwd = fwd if fwd[1] < 0 else -fwd
    org = hinge - fwd * a_front
    A, B = a * H / 2, b * H / 2
    cup = EAR_CUP * np.clip(rho, 0, 1) ** 2 * (1 - 0.6 * np.clip(a / EAR_WH, 0, 1))   # front edge stays at the head
    cup -= EAR_TOP_CURL * _e_sm(0.55, 1.0, b) * _e_sm(0.6, 1.0, rho)                 # q13: the top curls toward the head
    att = -0.002 * _e_sm(0.80, 1.0, a / a.max()) * (1 - np.clip(-np.sin(np.radians(th)), 0, 1))   # front edge sinks in
    N_out = h * H + cup + att
    P = org[None] + A[:, None] * fwd[None] + B[:, None] * up[None] + N_out[:, None] * nrm[None]
    if tree is not None:
        # q13b: sit on the skull - the back of the ear stands off the skin (EAR_STANDOFF at the back edge), the front
        # edge sinks EAR_SINK into it (attached, no gap, no buried rim)
        from mathutils import Vector
        Pf = P - N_out[:, None] * nrm[None]                       # the flat ear plane (relief added back on top)
        hgt = np.full(len(P), np.nan)
        for i, p in enumerate(Pf):
            hit = tree.ray_cast(Vector(p + nrm * 0.06), Vector(-nrm), 0.2)
            if hit[0] is not None:
                hgt[i] = (p - np.array(hit[0])) @ nrm
        af = np.clip((a.max() - a) / (a.max() - a.min()), 0, 1)          # 0 at the front edge, 1 at the back edge
        ell = np.sqrt(np.clip(1 - ((b - EAR_SO_B0) / EAR_SO_R) ** 2, 0, 1))      # q13c: rounded front-view silhouette
        clr = -EAR_SINK + (EAR_BASE + EAR_SINK) * _e_sm(0.0, 0.18, af) + EAR_STANDOFF * ell * _e_sm(0.15, 0.95, af)
        ok = np.isfinite(hgt)
        if ok.any():
            # q13c: per vertex, the ear plane keeps its clearance over the skull (smooth: both fields are smooth)
            fill = np.interp(np.arange(len(P)), np.nonzero(ok)[0], (clr - hgt)[ok])
            P = P + nrm[None] * fill[:, None]
    root = hinge
    return P, quads, dark, a, b, rho, th, root, up, nrm


def rebuild_ears(head, col, tag):
    me0 = head.data
    vg = head.vertex_groups.get("EarShell")
    ear = np.zeros(len(me0.vertices), bool)
    for v in me0.vertices:
        for g in v.groups:
            if g.group == vg.index and g.weight > 0.5:
                ear[v.index] = True
    co = np.empty(len(me0.vertices) * 3); me0.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    # local coordinates only (the head's matrix_world is not updated yet while apply_look runs)
    verts, faces, dark, fline, keys = [], [], [], [], {"ID-EarSize": [], "ID-EarSize_Neg": [], "ID-EarOut": []}
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    mods = [(m, m.show_viewport) for m in head.modifiers if m.type == "SOLIDIFY"]
    for m, _ in mods:
        m.show_viewport = False
    dg.update()
    ev = head.evaluated_get(dg); emesh = ev.to_mesh()     # the skin without its outline shell (old ear masked away)
    tree = BVHTree.FromPolygons([tuple(v.co) for v in emesh.vertices], [tuple(p.vertices) for p in emesh.polygons])
    ev.to_mesh_clear()                                    # local coordinates (FromObject gave world ones)
    for m, v in mods:
        m.show_viewport = v
    for side in (1, -1):
        m = ear & (np.sign(co[:, 0]) == side)
        if m.sum() < 10:
            continue
        Pl = co[m]
        P, quads, dk, a, b, rho, th, root, up, nrm = build_side(Pl, side, tree)
        base = len(verts)
        verts += [tuple(p) for p in P]
        faces += [tuple(base + i for i in q) for q in quads]
        dark += list(dk)
        con_edge = dk                      # the line field: 1 at the edge of the dark shapes
        fline += list(np.clip(con_edge / 0.55, 0, 2))
        for kname, f in (("ID-EarSize", lambda p: root + (p - root) * 1.15), ("ID-EarSize_Neg", lambda p: root + (p - root) * 0.87),
                         ("ID-EarOut", lambda p: root + _e_rot(p - root, up, math.radians(12.0) * side))):
            keys[kname] += [tuple(f(p)) for p in P]
    name = "NEW_Ears_" + tag
    old = bpy.data.objects.get(name)
    mats = list(old.data.materials) if old else list(head.data.materials)
    if old:
        om = old.data; bpy.data.objects.remove(old)
        if om.users == 0:
            bpy.data.meshes.remove(om)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces); me.update()
    # outward normals per ear (the two frames differ in handedness): flip a whole side if it faces into the head
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    for sd in (1, -1):
        fs = [f for f in bm.faces if np.sign(f.calc_center_median().x) == sd]
        if fs and np.mean([f.normal.x * sd for f in fs]) < 0:
            for f in fs:
                f.normal_flip()
    bm.to_mesh(me); bm.free(); me.update()
    for p in me.polygons:
        p.use_smooth = True
    # q13d: lit like the MHS3 ear (and the old shell, apply_look EAR_LIT): normals mostly turned to the lit front
    # direction, a little of the ear's own form kept; the head-normal blend (an_w) put a toon shadow blotch on it
    me.update()
    gn = np.array([v.normal[:] for v in me.vertices])
    lit = np.array([0.0, -1.0, 0.25]) / np.linalg.norm([0.0, -1.0, 0.25])
    nn = gn * (1 - EAR_LIT_K) + lit * EAR_LIT_K
    nn /= np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-9)
    me.normals_split_custom_set_from_vertices([tuple(v) for v in nn])
    for mt in mats:
        me.materials.append(mt)
    n = len(verts)
    for nm, vals in (("shade", np.ones(n)), ("an_w", np.full(n, EAR_AN_W)), ("ear_bowl", np.array(dark)), ("ear_line", np.zeros(n)),
                     ("ear_f", np.array(fline) * EAR_LINE_ON), ("ear_lw", np.ones(n) * 0.6)):
        at = me.attributes.new(nm, "FLOAT", "POINT"); at.data.foreach_set("value", np.asarray(vals, np.float32))
    e = bpy.data.objects.new(name, me)
    col.objects.link(e)
    e.location = head.location.copy(); e.rotation_euler = head.rotation_euler.copy(); e.scale = head.scale.copy()
    if head.parent:
        e.parent = head.parent; e.matrix_parent_inverse = head.matrix_parent_inverse.copy()
    vgo = e.vertex_groups.new(name="OutlineWeight"); vgo.add(list(range(n)), 1.0, "REPLACE")
    e.shape_key_add(name="Basis")
    for kname, pts in keys.items():
        kb = e.shape_key_add(name=kname); kb.value = 0.0
        kb.data.foreach_set("co", np.asarray(pts, np.float32).ravel())
    t = e.modifiers.new("Thick", "SOLIDIFY"); t.thickness = EAR_THICK; t.offset = -1.0; t.use_rim = True; t.use_even_offset = True
    sub = e.modifiers.new("Smooth", "SUBSURF"); sub.levels = sub.render_levels = EAR_SUBDIV_NEW
    if hasattr(sub, "use_custom_normals"):
        sub.use_custom_normals = True
    src = head.modifiers.get("Outline")
    o = e.modifiers.new("Outline", "SOLIDIFY")
    for k in ("thickness", "offset", "use_flip_normals", "use_rim", "use_even_offset", "material_offset", "vertex_group",
              "thickness_vertex_group"):
        setattr(o, k, getattr(src, k))
    print("q13 ears rebuilt: %d verts, %d quads" % (n, len(faces)))
    return e
