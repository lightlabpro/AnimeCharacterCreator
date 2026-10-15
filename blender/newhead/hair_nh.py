"""h-series: MHS3-style hair for the new head, built as chunky clumps (no strands), split into creator slots.

exec'd in Blender after apply_look (session.py: ns["hair"](style)). Needs the baked head NEW_Head_<tag> (its basis is
the scalp the clumps are fitted to).

Reference: MHS3 Leo render (docs/reference/mhs3/MHST3-Leo_Render_001.webp) - short layered brown hair: a fringe of
long pointed clumps falling to the brows, slightly parted, a full top with a few clumps standing up and back, sides
that stop above the ears, short pointed layers at the nape; flat base colour, darker lines between clumps, a few
sharp light streaks, the outline in a darker brown.

Build (anime-character-modeling skill: Hina 62 clumps, thickness ~0.64 x width; Ito: overlapping roof tiles + cap):
- every clump is a swept lens-shaped tube along a path that hugs the skull: spherical angles from the skull centre
  C (azimuth a: 0 front, +90 character's left; polar p from the top), radius = skull surface (ray cast on the head)
  + an offset that rises off the scalp (volume) and dips back at the tip (layers); width tapers to a point
- a cap shell (the head's scalp faces pushed out 2.5 mm) under the clumps, in the under colour, so no skin shows
- pieces (creator slots): Hair_Front_<style> (SOC-HairFront), Hair_Back_<style> (SOC-HairBack; crown, top, back,
  sides and the cap); every clump is its own UV island (u across, v root -> tip) for NG_ToonHair
- ID- keys per piece (value 0): ID-HairVolume(_Neg), ID-HairWidth(_Neg), ID-HairLength(_Neg)
- normals: blended toward the skull-centre radial so the toon shadow reads as a few big shapes, not per clump
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

S, O = 0.262, 1.4826
C = np.array([0.0, -0.004, O + 0.56 * S])     # skull centre for the spherical frame
RING = 8                                      # vertices round a clump
SEG = 14                                      # rings along a clump
CAP_OFF = 0.0025
ROOT_COL = (0.30, 0.18, 0.09, 1.0)            # linear; Leo brown (sRGB ~ 150,104,62 at the tip)
TIP_COL = (0.33, 0.20, 0.10, 1.0)
UNDER_COL = (0.12, 0.07, 0.04, 1.0)
OUTLINE_W = 0.0012
RADIAL_NORMAL = 0.75
# judge knobs (look_knobs.json "hair" overrides)
VOL_SCALE = 1.0      # all clumps' lift off the scalp
TOP_EXTRA = 0.0      # extra lift (m) for clumps rooted near the crown (p0 < 20)
FRINGE_LEN = 1.0     # fringe length (polar span)
WID_SCALE = 1.0      # clump width
LIGHTNESS = 1.0      # hair colour brightness


def _dir(a, p):
    a, p = math.radians(a), math.radians(p)
    return np.array([math.sin(p) * math.sin(a), -math.sin(p) * math.cos(a), math.cos(p)])


class Scalp:
    def __init__(self, head):
        me = head.data
        kb = me.shape_keys.key_blocks[0] if me.shape_keys else None
        co = [tuple(v.co) for v in (kb.data if kb else me.vertices)]
        vg = head.vertex_groups.get("EarShell")
        ear = np.zeros(len(co), bool)
        if vg is not None:
            gi = vg.index
            for v in me.vertices:
                if any(g.group == gi for g in v.groups):
                    ear[v.index] = True
        polys = [tuple(p.vertices) for p in me.polygons if not ear[p.vertices[0]]]   # skull only (no ears)
        self.V = np.array(co)
        self.tree = BVHTree.FromPolygons(co, polys)
        self.cache = {}

    def radius(self, d):
        key = tuple(np.round(d, 3))
        if key in self.cache:
            return self.cache[key]
        far = Vector(tuple(C + d * 0.5))
        hit = self.tree.ray_cast(far, Vector(tuple(-d)), 0.5)     # from outside inward: the outer skin
        r = (0.5 - hit[3]) if hit[0] is not None else 0.11
        self.cache[key] = r
        return r


def clump_rings(sc, c, vol=1.0, wid=1.0, lng=1.0):
    """Ring vertices (SEG x RING + tip) of one clump spec c."""
    a0, p0, a1, p1 = c["a0"], c["p0"], c["a1"], c["p1"]
    vol = vol * VOL_SCALE; wid = wid * WID_SCALE
    if c.get("fringe"):
        lng = lng * FRINGE_LEN
    a1 = a0 + (a1 - a0) * lng; p1 = p0 + (p1 - p0) * lng
    pts, nrm = [], []
    for i in range(SEG + 1):
        t = i / SEG
        tt = t ** c.get("ease", 1.0)
        a = a0 + (a1 - a0) * tt; p = p0 + (p1 - p0) * tt
        d = _dir(a, p)
        off = -0.002 + (vol * c["vol"] + (TOP_EXTRA if p0 < 20 else 0.0)) * (math.sin(math.pi * min(t / 0.45, 1.0) * 0.5)) - c.get("drop", 0.004) * max(0.0, (t - 0.65) / 0.35) ** 2
        off += c.get("flick", 0.0) * max(0.0, (t - 0.7) / 0.3) ** 2 * vol
        r = sc.radius(d) + off
        pts.append(C + d * r); nrm.append(d)
    pts = np.array(pts); nrm = np.array(nrm)
    tan = np.gradient(pts, axis=0); tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    out = []
    for i in range(SEG + 1):
        t = i / SEG
        w = c["w"] * wid * (1 - t) ** c.get("tip", 0.85) * (0.75 + 0.25 * math.sin(math.pi * min(1.0, t * 2.2)))
        th = w * c.get("th", 0.55)
        n = nrm[i] - tan[i] * np.dot(nrm[i], tan[i]); n /= np.linalg.norm(n)
        b = np.cross(tan[i], n)
        tw = math.radians(c.get("twist", 0.0)) * t
        b, n = b * math.cos(tw) + n * math.sin(tw), n * math.cos(tw) - b * math.sin(tw)
        if i == SEG:
            out.append([pts[i]])
            continue
        ring = []
        for k in range(RING):
            th_ = 2 * math.pi * k / RING
            x = math.cos(th_) * w / 2
            y = math.sin(th_) * th / 2 * (1.0 if math.sin(th_) > 0 else 0.45)   # flatter underside (lens)
            ring.append(pts[i] + b * x + n * y)
        out.append(ring)
    return out


def _style_leo():
    """Leo-like short layered cut. Returns {piece: [clump specs]}. h2: more volume, fewer wider clumps, a longer
    asymmetric fringe, a covered crown and staggered nape layers (h1 read as a flat comb-striped helmet)."""
    rng = np.random.default_rng(3)
    front, back = [], []
    # fringe: big pointed clumps from the front of the top down past the brows, swept to the character's left
    # h3: fewer, bigger fringe clumps; one dominant clump falls diagonally across the forehead (Leo)
    fr = [(-60, 86, 0.062, 0), (-38, 97, 0.078, 6), (-12, 100, 0.084, 14), (14, 104, 0.090, 22), (38, 96, 0.078, 10),
          (60, 86, 0.062, 4)]
    for a, p1, w, sw in fr:
        front.append(dict(a0=a * 0.45 - 6, p0=14 + 6 * rng.random(), a1=a + sw + rng.uniform(-3, 3), p1=p1 + rng.uniform(-3, 3),
                          w=w, vol=0.034 + 0.006 * rng.random(), th=0.55, drop=0.012, ease=1.2, twist=rng.uniform(-15, 15), fringe=1))
    for a, p1 in ((-25, 88), (27, 90)):                     # short in-between tips (layering at the hairline)
        front.append(dict(a0=a * 0.5, p0=24, a1=a + 6, p1=p1, w=0.050, vol=0.028, th=0.5, drop=0.006, ease=1.1))
    # top front (under the fringe roots): covers the crown-to-fringe gap
    for a in np.arange(-50, 51, 25):
        back.append(dict(a0=a * 0.6 + 180, p0=6, a1=a, p1=34, w=0.075, vol=0.040, th=0.6, drop=0.0, ease=0.9))
    # crown spikes standing up and back (Leo: a messy crown with a few clumps up)
    for a, p1 in ((140, 40), (165, 34), (190, 38), (215, 36), (240, 44), (120, 46)):
        back.append(dict(a0=a, p0=8, a1=a + rng.uniform(-12, 12), p1=p1, w=0.075, vol=0.040, flick=0.016, th=0.6, drop=0.0, tip=0.6))
    # top layer radiating from the crown
    for a in np.arange(0, 360, 22):                     # h5: denser (h4 left a gap at the side of the crown)
        if abs(((a + 180) % 360) - 180) < 55:
            continue
        back.append(dict(a0=a + rng.uniform(-6, 6), p0=8 + 6 * rng.random(), a1=a + rng.uniform(-10, 10), p1=70 + 10 * rng.random(),
                         w=0.080, vol=0.036, th=0.62, drop=0.024))   # h4: tips come back to the scalp (narrower sides)
    # sides: stop above the ears, tips forward-down at the temples
    for s_ in (1, -1):
        for a, p1, w in ((58, 96, 0.060), (75, 92, 0.064), (93, 88, 0.064), (112, 98, 0.064)):
            back.append(dict(a0=s_ * (a - 14), p0=34, a1=s_ * (a - 6 + rng.uniform(-4, 4)), p1=p1 + rng.uniform(-3, 3),
                             w=w, vol=0.016, th=0.58, drop=0.0, flick=0.008))
    # back: two staggered rows of pointed layers to the nape
    for a in np.arange(122, 240, 16):
        back.append(dict(a0=a, p0=38, a1=a + rng.uniform(-8, 8), p1=112 + 14 * rng.random(), w=0.072, vol=0.020, th=0.6,
                         drop=0.010))
    for a in np.arange(112, 250, 19):
        back.append(dict(a0=a + 8, p0=72, a1=a + 8 + rng.uniform(-8, 8), p1=128 + 12 * rng.random(), w=0.060, vol=0.014, th=0.55,
                         drop=0.006, flick=0.004))
    return {"Front": front, "Back": back}


STYLES = {"leo": _style_leo}


def _material(style):
    name = "MAT_Hair_" + style
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = bpy.data.node_groups["NG_ToonHair"]
    g.inputs["root_color"].default_value = ROOT_COL
    g.inputs["tip_color"].default_value = TIP_COL
    g.inputs["secondary_color"].default_value = TIP_COL
    g.inputs["highlight_strength"].default_value = 0.6
    g.inputs["streak_amount"].default_value = 0.6
    for nm, inp in (("hair_streak", "Streak Mask"), ("hair_line", "Clump Line Mask")):
        a = nt.nodes.new("ShaderNodeAttribute"); a.attribute_name = nm
        nt.links.new(a.outputs["Fac"], g.inputs[inp])
    nt.links.new(g.outputs["Shader"], out.inputs["Surface"])
    return m


def _cap_material(style):
    name = "MAT_HairCap_" + style
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = UNDER_COL
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def _mesh_from(name, clumps_rings, col, off_x, mats, streak):
    verts, faces, uvs, attr_s, attr_l = [], [], [], [], []
    for ci, rings in enumerate(clumps_rings):
        base = len(verts)
        for i, ring in enumerate(rings):
            for k, p in enumerate(ring):
                verts.append(tuple(p))
                attr_s.append(streak[ci]); attr_l.append(abs(math.sin(math.pi * k / RING)) < 0.4)
        nr = len(rings) - 1
        for i in range(nr - 1):
            for k in range(RING):
                a = base + i * RING + k; b = base + i * RING + (k + 1) % RING
                faces.append((a, b, b + RING, a + RING))
        tip = base + nr * RING
        for k in range(RING):
            a = base + (nr - 1) * RING + k; b = base + (nr - 1) * RING + (k + 1) % RING
            faces.append((a, b, tip))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces); me.update()
    uvl = me.uv_layers.new(name="UVMap")
    # u across (ring index), v root -> tip
    vi_uv = []
    for ci, rings in enumerate(clumps_rings):
        for i, ring in enumerate(rings):
            for k, _ in enumerate(ring):
                vi_uv.append((k / RING if len(ring) > 1 else 0.5, i / (len(rings) - 1)))
    for p in me.polygons:
        p.use_smooth = True
        for li in p.loop_indices:
            uvl.data[li].uv = vi_uv[me.loops[li].vertex_index]
    for nm, val in (("hair_streak", attr_s), ("hair_line", attr_l)):
        at = me.attributes.new(nm, "FLOAT", "POINT"); at.data.foreach_set("value", np.asarray(val, np.float32))
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me); o.location.x = off_x
    col.objects.link(o)
    return o


def _radial_normals(o):
    me = o.data
    V = np.array([v.co[:] for v in me.vertices])
    N = np.empty(len(V) * 3); me.vertices.foreach_get("normal", N); N = N.reshape(-1, 3)
    R = V - C; R /= np.linalg.norm(R, axis=1, keepdims=True)
    n = RADIAL_NORMAL * R + (1 - RADIAL_NORMAL) * N
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    me.normals_split_custom_set_from_vertices([tuple(x) for x in n])


def _outline(o, outline_mat):
    o.data.materials.append(outline_mat)
    md = o.modifiers.new("Outline", "SOLIDIFY")
    md.thickness = OUTLINE_W; md.offset = 1.0; md.use_flip_normals = True; md.use_rim = False
    md.material_offset = len(o.data.materials) - 1


def _cap(sc, head, col, off_x, style, mat):
    """Scalp shell under the clumps (head faces above the hairline, pushed out)."""
    me = head.data
    V = sc.V
    rel = V - C
    p = np.degrees(np.arccos(np.clip(rel[:, 2] / np.linalg.norm(rel, axis=1), -1, 1)))
    a = np.degrees(np.arctan2(rel[:, 0], -rel[:, 1]))
    limit = 62 + 55 * (np.abs(a) / 180.0) ** 1.5           # hairline: high at the front, low at the nape
    inside = p < limit
    keep = [pl for pl in me.polygons if all(inside[list(pl.vertices)])]
    used = sorted({i for pl in keep for i in pl.vertices}); rm = {v: k for k, v in enumerate(used)}
    N = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("normal", N); N = N.reshape(-1, 3)
    verts = [tuple(V[i] + N[i] * CAP_OFF) for i in used]
    faces = [tuple(rm[i] for i in pl.vertices) for pl in keep]
    m2 = bpy.data.meshes.new("Hair_Cap_" + style); m2.from_pydata(verts, [], faces); m2.update()
    m2.materials.append(mat)
    o = bpy.data.objects.new("Hair_Cap_" + style, m2); o.location.x = off_x
    col.objects.link(o)
    return o


def load_knobs():
    import json, os
    p = os.path.join(os.path.dirname(os.path.abspath(HAIR_PATH)), "look_knobs.json") if "HAIR_PATH" in globals() else None
    if p and os.path.exists(p):
        for k, v in json.load(open(p)).get("hair", {}).items():
            if k in globals():
                globals()[k] = v


def build_hair(style="leo", tag="n56", off_x=2.4):
    global ROOT_COL, TIP_COL
    load_knobs()
    ROOT_COL = tuple(min(1.0, c * LIGHTNESS) for c in ROOT_COL[:3]) + (1.0,)
    TIP_COL = tuple(min(1.0, c * LIGHTNESS) for c in TIP_COL[:3]) + (1.0,)
    head = next(o for o in bpy.data.collections["NEW_HEAD_" + tag].objects if o.name.startswith("NEW_Head_"))
    cname = "NEW_HAIR_%s_%s" % (style, tag)
    col = bpy.data.collections.get(cname) or bpy.data.collections.new(cname)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    for o in list(col.objects):
        bpy.data.objects.remove(o)
    sc = Scalp(head)
    spec = STYLES[style]()
    hm = _material(style); cm = _cap_material(style)
    om = bpy.data.materials.get("MAT_Outline_NewHead_" + tag)
    rng = np.random.default_rng(11)
    made = []
    for piece, clumps in spec.items():
        rings = [clump_rings(sc, c) for c in clumps]
        streak = [1.0 if rng.random() < 0.35 else 0.0 for _ in clumps]
        o = _mesh_from("Hair_%s_%s" % (piece, style), rings, col, off_x, [hm], streak)
        o["socket"] = "SOC-Hair" + piece
        _radial_normals(o)
        o.shape_key_add(name="Basis")
        for kname, kw in (("ID-HairVolume", dict(vol=1.45)), ("ID-HairVolume_Neg", dict(vol=0.55)),
                          ("ID-HairWidth", dict(wid=1.25)), ("ID-HairWidth_Neg", dict(wid=0.8)),
                          ("ID-HairLength", dict(lng=1.18)), ("ID-HairLength_Neg", dict(lng=0.82))):
            kr = [clump_rings(sc, c, **kw) for c in clumps]
            flat = np.array([p for rr in kr for ring in rr for p in ring], np.float32)
            kb = o.shape_key_add(name=kname); kb.value = 0.0
            kb.data.foreach_set("co", flat.ravel())
        if om:
            _outline(o, om)
        made.append(o)
    made.append(_cap(sc, head, col, off_x, style, cm))
    return col, made
