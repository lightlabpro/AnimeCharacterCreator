"""v2 mouth: a real opening in the head with a cavity, curved tooth arches and a tongue (bpy, after remesh).

Sammy (q20): "fix the teeth and tongue, they look too flat and 2d (no depth)". In v2 the teeth are a curved band on an
arch behind the lips (Pavelec, Hellbeasts p101: the teeth sit on the rounded maxilla / mandible and wrap around it,
TypeSafe 0.96) inside a real cavity, so a turned camera shows parallax and the far inner wall by itself.
Leo: mouth 0.64 D below the pupils, 0.49 D wide (D = pupil line to chin = 0.5 H).

Steps on the remeshed head (V2_Head):
  1. delete a thin band of faces along the mouth line -> a slot; move the slot's rim onto the line (upper rim just
     above, lower rim just below): closed lips that can part;
  2. extrude the rim inward (lip thickness), then two rings that open into a pocket behind the lips, cap it:
     the cavity (its own material);
  3. upper / lower tooth arches (curved strips with thickness) and a tongue inside the cavity;
  4. PF-JawOpen: the mandible region, the lower teeth and the tongue rotate about the jaw joint.
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ZT, H = 1.685, 0.22
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from mouth_v2_line import EYE_H, D, MY, MW  # noqa: E402  (one face layout for every script)
M = dict(curve=0.006, sag=0.003, band=0.62, lip_in=0.0022, up_open=0.0060, lo_open=0.0075, depth1=0.0065,
         depth2=0.024, x2=0.78, jaw_pivot=(0.055, 0.600), jaw_deg=11.0, bowl=0.0065, teeth_back=0.0040, teeth_rx=0.80,
         teeth_ry=0.0120, teeth_up=0.0055, teeth_vis=0.0005, lip_lift=0.0036, teeth_lo=0.0022, teeth_t=0.0012)


def line_h(x):
    """Mouth line (h) at x (H units): corners slightly up (Leo's neutral line is nearly straight, a slight smile)."""
    u = np.clip(np.abs(x) / MW, 0, 1)
    return MY - M["curve"] * u ** 2 + M["sag"] * (1 - u ** 2) * 0.0


def to_xh(co):
    return co.x / H, (ZT - co.z) / H


def from_xh(x, h, y):
    return Vector((x * H, y, ZT - h * H))


def surface_y(tree, x, h):
    loc, nrm, idx, dist = tree.ray_cast(from_xh(x, h, -1.0), Vector((0, 1, 0)))
    return (loc.y, nrm) if loc is not None else (None, None)


def build_mouth(head, spacing):
    me = head.data
    bm0 = bmesh.new(); bm0.from_mesh(me); tree = BVHTree.FromBMesh(bm0); bm0.free()
    bm = bmesh.new(); bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    band = M["band"] * spacing / H
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        x, h = to_xh(c)
        if c.y > -0.15 * H or abs(x) > MW:
            continue
        u = abs(x) / MW
        if abs(h - line_h(x)) < band * max(0.35, (1 - u ** 4)):
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bnd = [e for e in bm.edges if e.is_boundary]
    rim = {v for e in bnd for v in e.verts}
    # classify and move the rim onto the line
    side = {}
    for v in rim:
        x, h = to_xh(v.co)
        xc = float(np.clip(x, -MW, MW))
        lh = float(line_h(xc))
        s = -1 if h < lh else 1                                  # -1 upper lip rim, +1 lower lip rim
        if abs(x) >= MW * 0.985:
            s = 0
        side[v] = s
        ht = lh + s * 0.0006
        y, n = surface_y(tree, xc, ht)
        if y is not None:
            v.co = from_xh(xc, ht, y)
    # relax the ring of faces next to the rim and put them back on the surface
    near = set()
    for v in rim:
        for e in v.link_edges:
            o = e.other_vert(v)
            if o not in rim:
                near.add(o)
    for _ in range(2):
        newco = {}
        for v in near:
            nb = [e.other_vert(v).co for e in v.link_edges]
            newco[v] = sum(nb, Vector()) / len(nb)
        for v, c in newco.items():
            x, h = to_xh(c)
            y, n = surface_y(tree, x, h)
            if y is not None:
                v.co = from_xh(x, h, y)
    # cavity rings
    def ring_from(edges, move):
        r = bmesh.ops.extrude_edge_only(bm, edges=edges)
        nv = [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]
        ne = [g for g in r["geom"] if isinstance(g, bmesh.types.BMEdge)]
        nf = [g for g in r["geom"] if isinstance(g, bmesh.types.BMFace)]
        return nv, ne, nf
    # map new verts to their source side via position match
    def side_of(v):
        x, h = to_xh(v.co)
        lh = float(line_h(np.clip(x, -MW, MW)))
        if abs(x) >= MW * 0.97:
            return 0
        return -1 if h < lh else 1
    cav_faces = []
    nv, ne, nf = ring_from(bnd, None)
    for v in nv:
        s = side[v] if v in side else side_of(v)
        side[v] = s
        v.co += Vector((0, M["lip_in"], 0))
    lip_in_faces = nf
    edges = ne
    for depth, xs, up, lo in ((M["depth1"], 1.0, M["up_open"], M["lo_open"]),
                               (M["depth2"], M["x2"], M["up_open"] * 0.9, M["lo_open"] * 0.9)):
        nv2, ne2, nf2 = ring_from(edges, None)
        for v in nv2:
            x, h = to_xh(v.co)
            s = side_of(v)
            # find the original side by nearest earlier vertex
            v.co = from_xh(x * xs, h + (s * (up if s < 0 else lo) * abs(s)) / H * max(0.0, 1 - (abs(x) / MW) ** 2) ** 0.5,
                           v.co.y + depth)
        cav_faces += nf2
        edges = ne2
    cap = bmesh.ops.contextual_create(bm, geom=edges)
    tri = bmesh.ops.triangulate(bm, faces=[f for f in cap["faces"]])
    cav_faces += list(tri["faces"])                      # tag after triangulating (it replaces the faces)
    for f in cav_faces:
        if f.is_valid:
            f.material_index = 1
    for f in lip_in_faces:
        if f.is_valid:
            f.material_index = 2
    bm.normal_update()
    bm.to_mesh(me); bm.free()
    me.update()
    return tree


def arch_strip(name, y_front, h_top, h_bot, rx, ry, t, n=40, upper=True):
    """Curved tooth band: an elliptical arch in plan (front at y_front, half width rx, depth ry), thickness t.
    The visible edge (bottom of the upper band, top of the lower) withdraws toward the ends: the side teeth curve
    back and disappear behind the cheeks (Pavelec p101) instead of ending in a white post at the mouth corner."""
    verts, faces = [], []
    a0 = math.radians(72)
    for i in range(n + 1):
        a = -a0 + 2 * a0 * i / n
        x = rx * math.sin(a); y = y_front + ry * (1 - math.cos(a))
        nx, ny = math.sin(a), -math.cos(a)                     # outward normal in plan
        k = 0.85 * (abs(a) / a0) ** 2.5
        he = h_bot + (h_top - h_bot) * k if upper else h_top + (h_bot - h_top) * k
        hb_, ht_ = (he, h_top) if upper else (h_bot, he)
        for (hh, off) in ((ht_, 0), (hb_, 0), (hb_, t), (ht_, t)):
            verts.append((x - nx * off, y - ny * off, ZT - hh * H))
    for i in range(n):
        a, b = 4 * i, 4 * (i + 1)
        for k in range(4):
            faces.append((a + k, a + (k + 1) % 4, b + (k + 1) % 4, b + k))
    faces.append((0, 3, 2, 1)); faces.append((4 * n, 4 * n + 1, 4 * n + 2, 4 * n + 3))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.validate()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def build_teeth_tongue(tree):
    y0, _ = surface_y(tree, 0.0, MY)
    yf = y0 + M["teeth_back"]
    rx = MW * H * M["teeth_rx"]
    # upper teeth: the band reaches up inside the cavity (hidden by the upper lip) and shows teeth_vis below the
    # line when the jaw drops; lower teeth: a short band that sits under the lower lip rim and travels with the jaw
    top = arch_strip("V2TeethUpper", yf, MY - M["teeth_up"] / H, MY + M["teeth_vis"] / H, rx, M["teeth_ry"],
                     M["teeth_t"])
    bot = arch_strip("V2TeethLower", yf + 0.0015, MY + 0.0030 / H, MY + (0.0030 + M["teeth_lo"]) / H, rx * 0.90,
                     M["teeth_ry"] * 0.95, M["teeth_t"], upper=False)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0)
    tg = bpy.context.object; tg.name = "V2Tongue"
    tg.scale = (rx * 0.78, 0.015, 0.0055)
    tg.location = (0.0, yf + 0.021, ZT - (MY + 0.0030 / H) * H)      # tip ~6 mm behind the lip surface; high enough to show over the lower lip when open
    bpy.ops.object.transform_apply(location=True, scale=True)
    bpy.ops.object.shade_smooth()
    return top, bot, tg


def jaw_weights(head):
    """Weight per head vertex for the jaw rotation. Sharp split only across the lips (|x| < MW: the lower lip moves
    fully, the upper lip not at all); beside the corners the band widens so the cheeks stretch smoothly; the neck and
    throat stay. Rim / cavity verts are split by material and side."""
    me = head.data
    co = np.array([v.co[:] for v in me.vertices])
    x = co[:, 0] / H; h = (ZT - co[:, 2]) / H; y = co[:, 1] / H
    lh = line_h(np.clip(x, -MW, MW))
    ax = np.abs(x)
    band = 0.012 + 0.16 * np.clip((ax - 0.75 * MW) / (0.75 * MW), 0, 1)
    start = lh - 0.004 - 0.05 * np.clip((ax - 0.85 * MW) / (0.8 * MW), 0, 1)
    w = np.clip((h - start) / band, 0, 1)
    w = w * w * (3 - 2 * w)
    w *= 1 - np.clip((h - 0.93) / 0.10, 0, 1) * np.clip((y + 0.14) / 0.14, 0, 1)          # throat / neck stay
    w *= 1 - np.clip((y + 0.02) / 0.10, 0, 1)                                            # nothing behind the jaw
    for p in me.polygons:
        if p.material_index in (1, 2):
            for vi in p.vertices:
                w[vi] = 1.0 if h[vi] > lh[vi] else 0.0
    # corners: near the line the lower lip follows the jaw less toward the corners -> a bowl / lens opening, not a
    # box (MHS3 open mouths); a little below the line the full jaw weight returns
    u = np.clip(ax / MW, 0, 1)
    taper = np.clip((1 - u ** 2) / 0.45, 0, 1) ** 0.8
    below = np.clip((h - lh) / 0.07, 0, 1)
    below = below * below * (3 - 2 * below)
    near_mouth = ax < MW * 1.05
    w = np.where(near_mouth & (h >= lh - 0.0005), w * (taper + (1 - taper) * below), w)
    return w


def bowl_offset(co):
    """Open-mouth lower lip sags in the middle (MHS3 open mouths: flat top, rounded bowl bottom)."""
    x = co.x / H; h = (ZT - co.z) / H
    if abs(x) > MW * 1.1 or h < float(line_h(np.clip(x, -MW, MW))) - 0.001:
        return Vector()
    u = min(abs(x) / MW, 1.0)
    f = math.exp(-((h - float(line_h(np.clip(x, -MW, MW)))) / 0.05) ** 2)
    return Vector((0.0, -0.0015, -M["bowl"])) * (1 - u * u) * f


def lip_lift(co):
    """Open mouth: the upper lip lifts a little in the middle so the upper teeth show as a band (Leo's open mouth)."""
    x = co.x / H; h = (ZT - co.z) / H
    lh = float(line_h(np.clip(x, -MW, MW)))
    if abs(x) > MW * 1.1 or h > lh + 0.0005:
        return Vector()
    u = min(abs(x) / MW, 1.0)
    return Vector((0.0, 0.0, M["lip_lift"])) * (1 - u * u) * math.exp(-((lh - h) / 0.035) ** 2)


def add_jaw_key(head, extra):
    ang = math.radians(M["jaw_deg"])
    py, ph = M["jaw_pivot"]
    pivot = Vector((0.0, py * H, ZT - ph * H))
    R = Matrix.Rotation(ang, 3, "X")                           # +angle about x: the chin goes down and back
    if head.data.shape_keys is None:
        head.shape_key_add(name="Basis")
    k = head.shape_key_add(name="PF-JawOpen"); k.value = 0.0
    w = jaw_weights(head)
    for i, v in enumerate(head.data.vertices):
        p = v.co - pivot
        k.data[i].co = v.co.lerp(pivot + R @ p, float(w[i])) + bowl_offset(v.co) * float(w[i]) \
            + lip_lift(v.co) * (1.0 - float(w[i]))
    for ob in extra:
        if ob.data.shape_keys is None:
            ob.shape_key_add(name="Basis")
        kk = ob.shape_key_add(name="PF-JawOpen"); kk.value = 0.0
        for i, v in enumerate(ob.data.vertices):
            kk.data[i].co = pivot + R @ (v.co - pivot)
    return k


# ---- mouth expression keys (contract PF- names) ------------------------------------------------------------------
MOUTH_KEYS = {
    # name: jaw fraction, smile, frown, wide, round, side (+1 L only, -1 R only, 0 both)
    "PF-SmileClosed": dict(jaw=0.0, smile=1.0),
    "PF-SmileOpenJaw": dict(jaw=0.45, smile=0.9),
    "PF-Frown": dict(frown=1.0),
    "PF-FrownOpen": dict(jaw=0.35, frown=0.9),
    "PF-VisAA": dict(jaw=0.62, wide=0.25),
    "PF-VisOH": dict(jaw=0.42, round=1.0),
    "PF-VisEE": dict(jaw=0.16, wide=1.0, smile=0.15),
    "PF-Pout": dict(round=0.7),
    "PF-Smirk_L": dict(smile=0.9, side=1),
    "PF-Smirk_R": dict(smile=0.9, side=-1),
}


def _jaw_positions(head, frac):
    """Head vertex positions for the jaw opened by frac of the full PF-JawOpen (rotation + bowl + lip lift)."""
    ang = math.radians(M["jaw_deg"]) * frac
    py, ph = M["jaw_pivot"]
    pivot = Vector((0.0, py * H, ZT - ph * H))
    R = Matrix.Rotation(ang, 3, "X")
    w = jaw_weights(head)
    out = []
    for i, v in enumerate(head.data.vertices):
        p = v.co - pivot
        out.append(v.co.lerp(pivot + R @ p, float(w[i])) + bowl_offset(v.co) * float(w[i]) * frac
                   + lip_lift(v.co) * (1.0 - float(w[i])) * frac)
    return out, R, pivot


def _mouth_offsets(co, smile=0.0, frown=0.0, wide=0.0, round=0.0, side=0):
    x = co.x / H; h = (ZT - co.z) / H; y = co.y / H
    if y > -0.18:
        return Vector()
    sx = 1.0 if x >= 0 else -1.0
    if side and sx != side:
        return Vector()
    ax = abs(x)
    c = math.exp(-(((ax - MW) / 0.065) ** 2 + ((h - MY) / 0.055) ** 2))          # mouth corner
    m = math.exp(-((x / (MW * 1.1)) ** 2 + ((h - MY) / 0.06) ** 2))                # whole mouth
    ck = math.exp(-(((ax - 0.19) / 0.085) ** 2 + ((h - 0.62) / 0.07) ** 2))         # cheek
    d = Vector()
    if smile:
        d += Vector((sx * 0.007 * c, 0.009 * c - 0.002 * ck, 0.021 * c + 0.007 * ck)) * (smile * H)   # world z: up
    if frown:
        d += Vector((0.0, 0.002 * c, -0.016 * c)) * (frown * H)
    if wide:
        d += Vector((sx * 0.011 * c, 0.003 * c, 0.002 * c)) * (wide * H)
    if round:
        d += Vector((-sx * 0.30 * ax * m, -0.007 * m, 0.0)) * (round * H) + Vector((-sx * 0.0, 0, 0))
        d.x = -sx * 0.30 * ax * m * round * H
    return d


def add_mouth_keys(head, lower_parts):
    """PF- mouth keys on the head (and the jaw part on the lower teeth / tongue)."""
    if head.data.shape_keys is None:
        head.shape_key_add(name="Basis")
    for name, prm in MOUTH_KEYS.items():
        frac = prm.get("jaw", 0.0)
        pos, R, pivot = _jaw_positions(head, frac)
        k = head.shape_key_add(name=name); k.value = 0.0
        for i, v in enumerate(head.data.vertices):
            k.data[i].co = pos[i] + _mouth_offsets(v.co, prm.get("smile", 0), prm.get("frown", 0), prm.get("wide", 0),
                                                   prm.get("round", 0), prm.get("side", 0))
        for ob in lower_parts:
            if ob.data.shape_keys is None:
                ob.shape_key_add(name="Basis")
            kk = ob.shape_key_add(name=name); kk.value = 0.0
            for i, v in enumerate(ob.data.vertices):
                kk.data[i].co = pivot + R @ (v.co - pivot)
