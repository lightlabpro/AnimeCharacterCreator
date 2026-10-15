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
ROOT_COL = (0.40, 0.25, 0.13, 1.0)            # linear; k2: Leo light warm brown (sRGB ~ 170,135,98 lit)
TIP_COL = (0.40, 0.25, 0.13, 1.0)
UNDER_COL = (0.20, 0.10, 0.045, 1.0)    # k11: hair shadow brown (k8 near-black gaps read as stripes)
OUTLINE_W = 0.0009
RADIAL_NORMAL = 0.55     # k11: more of each clump's own normal -> shadow shapes per clump
# judge knobs (look_knobs.json "hair" overrides)
VOL_SCALE = 1.0      # all clumps' lift off the scalp
TOP_EXTRA = 0.0      # extra lift (m) for clumps rooted near the crown (p0 < 20)
FRINGE_LEN = 1.0     # fringe length (polar span)
WID_SCALE = 1.0      # clump width
LIGHTNESS = 1.0      # hair colour brightness
SIDE_SCALE = 1.0     # k10: lift + flare of the side clumps (temples / over the ears)
HL_SHARE = 0.85       # k10: share of the outer clumps that carry highlight strokes


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


def _slerp(u, v, t):
    d = float(np.clip(np.dot(u, v), -1, 1)); om = math.acos(d)
    if om < 1e-6:
        return u
    return (math.sin((1 - t) * om) * u + math.sin(t * om) * v) / math.sin(om)


def clump_rings(sc, c, vol=1.0, wid=1.0, lng=1.0):
    """Ring vertices (SEG rings of RING + the tip point) of one clump spec c.
    k2 (2026-10-15): the path runs along the great circle from the root direction to the tip direction (slerp, so a
    clump from the crown can travel over the top to the fringe), with a sideways bend (S-curve); the lift rises from
    the root, peaks mid-way and falls toward the tip (a leaf lying on the head), or flicks out (side spikes); the
    cross-section is a flat blade (th ~0.3 x width) whose tip tapers late and asymmetrically (MHS3 leaf-shaped
    clumps with one straighter edge)."""
    vol = vol * VOL_SCALE * (SIDE_SCALE if c.get("side") else 1.0); wid = wid * WID_SCALE
    if c.get("fringe"):
        lng = lng * FRINGE_LEN
    u0 = _dir(c["a0"], c["p0"]); u1 = _dir(c["a1"], c["p1"])
    side_ax = np.cross(u0, u1); nrm_ = np.linalg.norm(side_ax)
    side_ax = side_ax / nrm_ if nrm_ > 1e-6 else np.array([1.0, 0.0, 0.0])
    pts, nrm = [], []
    for i in range(SEG + 1):
        t = i / SEG
        tt = t ** c.get("ease", 1.0)
        d = _slerp(u0, u1, tt * lng)                               # lng > 1 runs on past the tip direction
        bend = c.get("bend", 0.0) * math.sin(math.pi * t)          # S / C curve sideways (radians)
        d = d + side_ax * bend; d /= np.linalg.norm(d)
        lift = vol * c["vol"] * math.sin(math.pi * min(t / 0.5, 1.0) * 0.5)
        lift -= c.get("drop", 0.004) * max(0.0, (t - 0.55) / 0.45) ** 2
        lift += c.get("flick", 0.0) * vol * max(0.0, (t - 0.55) / 0.45) ** 2
        lift += (TOP_EXTRA if c["p0"] < 25 else 0.0) * math.sin(math.pi * min(t / 0.6, 1.0) * 0.5)
        r = sc.radius(d) + c.get("base", 0.0) - 0.002 * (1 - t) + lift
        pts.append(C + d * r); nrm.append(d)
    pts = np.array(pts); nrm = np.array(nrm)
    tan = np.gradient(pts, axis=0); tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    out = []
    asym = c.get("asym", 0.0)
    for i in range(SEG + 1):
        t = i / SEG
        env = (0.65 + 0.35 * min(1.0, t / 0.3)) * (1 - max(0.0, (t - c.get("taper", 0.5)) / (1 - c.get("taper", 0.5)))) ** c.get("tip", 1.1)
        w = c["w"] * wid * env
        th = max(w, 0.006) * c.get("th", 0.32)
        n = nrm[i] - tan[i] * np.dot(nrm[i], tan[i]); n /= np.linalg.norm(n)
        b = np.cross(tan[i], n)
        tw = math.radians(c.get("twist", 0.0)) * t
        b, n = b * math.cos(tw) + n * math.sin(tw), n * math.cos(tw) - b * math.sin(tw)
        ctr = pts[i] + b * (asym * c["w"] * wid * 0.35 * t * t)     # blade tip: the point drifts to one edge
        if i == SEG:
            out.append([ctr])
            continue
        ring = []
        for k in range(RING):
            th_ = 2 * math.pi * k / RING
            x = math.cos(th_) * w / 2
            y = math.sin(th_) * th / 2 * (1.0 if math.sin(th_) > 0 else 0.5)
            ring.append(ctr + b * x + n * y)
        out.append(ring)
    return out


CROWN = (180.0, 24.0)    # whorl at the top of the back of the head (a, p)


def _style_leo():
    """k2: Leo's short layered cut rebuilt from the MHS3 references (Leo render + game frame): big flat leaf-shaped
    clumps flowing from the crown whorl - over the top to a fringe that converges to a point between the brows with
    skin triangles beside it, down the temples with tips pointing down past the cheekbone line, short pointed layers
    at the back; an under layer in shadow fills the gaps. Each spec: root (a0, p0) -> tip (a1, p1) on the skull,
    w width (m), vol lift (m), drop / flick at the tip, bend, asym, shade (share of the clump from the root that sits
    in the shadow of the clump above, -1 = all)."""
    rng = np.random.default_rng(5)
    J = lambda s_: rng.uniform(-s_, s_)
    front, back = [], []
    ca, cp = CROWN
    # fringe (Front piece): from the front of the top, converging to the brows
    # k7: five big clumps converging on the forehead (Leo render: the longest ends between the brows) + two small
    # k20: the tips were at / below the pupil line (p 100 = pupil level on this skull, and FRINGE_LEN ran them on), so
    # the fringe hung over the eyes as separate spikes. Leo's fringe is a wide overlapping sheet swept from his right
    # (image left) toward his left, the longest point ending just above the inner brow (~0.12 D above the pupils,
    # p ~88), the rest at brow level, forehead showing above his left eye.
    for a1, p1, w, bend, asym, a0 in ((-10, 97, 0.110, 0.10, 1, -32), (12, 86, 0.100, 0.10, 1, -8), (34, 81, 0.090, 0.08, 1, 14),   # k22: +3-4 deg (k21 ended 0.27 D up); k25: Leo's longest point crosses the brow line to just above the upper lid
                                      (-36, 92, 0.100, 0.08, 1, -56), (56, 84, 0.070, 0.06, -1, 40),
                                      (4, 93, 0.054, 0.06, 1, -16), (-60, 92, 0.080, 0.04, 1, -76)):
        front.append(dict(a0=a0 + J(3), p0=4 + J(2), a1=a1 + J(2), p1=p1 + J(1.5), w=w,
                          vol=0.024 if abs(a1) < 30 else (0.016 if abs(a1) < 55 else 0.010), drop=0.014,   # k20: outer ones lie on the temples; k23: centre 0.040 -> 0.024 (profile: the fringe arced ~4 cm off the forehead, Leo's lies close)
                          base=0.005, bend=bend, asym=asym, taper=0.42, tip=1.25, th=0.30, shade=0.32, fringe=1))
    # k29: fine strands over the fringe sheet - TypeSafe (k25, k28, agreed both orders): "clumps narrower"; Leo's
    # fringe reads as many fine pointed strands grouped into clumps, so instead of only thinning the big clumps (gaps)
    # each one gets a thin strand on top, offset sideways and a little shorter, with its own pointed tip and rim line
    for fc in list(front):
        for off, dp in ((rng.choice([-1, 1]) * rng.uniform(5, 9), rng.uniform(3, 7)),):
            front.append(dict(fc, a1=fc["a1"] + off, p1=fc["p1"] - dp, a0=fc["a0"] + off * 0.5, w=0.026 + J(0.004),
                              vol=fc["vol"] + 0.004, base=fc["base"] + 0.002, taper=0.35, tip=1.1, th=0.35,
                              shade=0.15, asym=-fc["asym"]))
    # top (k11): more, narrower clumps sweeping from the crown forward and sideways; the front ones end in tips that
    # lift off the head, so the top outline is a row of points (the judge: "a smooth rounded cap")
    for a1, p1, fl in ((-16, 50, 0.006), (8, 46, 0.006), (30, 50, 0.008),   # k24: front flicks 0.012-0.014 -> 0.006 (with the flatter fringe they stuck out forward in profile)
                        (-38, 52, 0.010), (48, 54, 0.010), (-58, 56, 0.008),
                       (66, 54, 0.010), (-76, 56, 0.010), (92, 56, 0.006), (-100, 58, 0.006), (124, 52, 0.004), (-128, 52, 0.004),
                       (150, 46, 0.004), (-155, 46, 0.004)):
        back.append(dict(a0=ca + J(14), p0=cp - 8 + J(4), a1=a1 + J(4), p1=p1 + J(4), w=0.066,
                         vol=0.040 if abs(a1) < 40 else (0.022 if abs(a1) < 70 else 0.010), drop=0.0 if fl > 0.012 else 0.008, flick=fl,   # k18: thin at the sides (ref hair lies ~4 mm off the temples)
                         base=0.006, bend=J(0.12), asym=rng.choice([-1, 1]), taper=0.4, tip=1.3, th=0.32, shade=0.0))
    # k29: fine flyaway strands breaking the top outline (Leo render: thin strands fan up and out over the mass)
    # k30: shorter, near the top (k29 at p 30-50 flicked out sideways like whiskers)
    for a1, p1, fl in ((-60, 24, 0.012), (-30, 20, 0.014), (40, 22, 0.012), (70, 26, 0.010)):
        back.append(dict(a0=ca + J(10), p0=cp - 6 + J(3), a1=a1 + J(4), p1=p1 + J(3), w=0.022, vol=0.030, flick=fl, drop=0.0,
                         base=0.008, bend=J(0.15), asym=rng.choice([-1, 1]), taper=0.3, tip=1.0, th=0.35, shade=0.0))
    # ahoge-like spikes standing up at the top front (Leo render)
    # k16: two thin spikes standing up off the top (Leo render: they rise ~0.15 D above the hair mass) - TypeSafe kept
    # asking for a taller top while the measured mass height already matched, so the height comes from these
    for a1, p1, h in ((-10, 20, 0.050), (16, 24, 0.042)):   # k22: shorter - in profile they poked forward over the brow
        back.append(dict(a0=a1 + 175, p0=6, a1=a1, p1=p1, w=0.034, vol=0.030, flick=h, base=0.012, taper=0.25, tip=1.0,
                         th=0.35, shade=0.0, ease=0.7, bend=0.15 if a1 > 0 else -0.15))
    # sides: down the temples and over the top of the ears; k7: the outer ones flare out at the tip (jagged outline at
    # eye level in the Leo render)
    for sgn in (1, -1):
        for a1, p1, w, fl in ((64, 104, 0.054, 0.012), (80, 100, 0.058, 0.014), (97, 98, 0.058, 0.012), (114, 104, 0.054, 0.008)):
            back.append(dict(a0=sgn * (a1 - 40) + J(4), p0=40 + J(4), a1=sgn * a1 + J(3), p1=p1 + J(3), w=w, vol=0.016,
                             flick=fl, drop=0.0, base=0.001, bend=sgn * 0.06, asym=-sgn, taper=0.45, tip=1.25, th=0.30,
                             shade=0.0, side=1))
    # back: two rows of short pointed layers to the nape (k3: denser, no gap in the middle)
    for a1 in np.arange(120, 241, 12):
        back.append(dict(a0=ca + J(8), p0=cp + 8, a1=a1 + J(3), p1=128 + J(6), w=0.070, vol=0.022, drop=0.006, flick=0.003,
                         base=0.002, bend=J(0.08), asym=rng.choice([-1, 1]), taper=0.5, tip=1.2, th=0.32, shade=0.0))
    for a1 in np.arange(126, 236, 18):
        back.append(dict(a0=ca + J(8), p0=cp + 20, a1=a1 + J(3), p1=134 + J(5), w=0.060, vol=0.012, drop=0.004, flick=0.002,
                         base=0.0, bend=J(0.06), asym=rng.choice([-1, 1]), taper=0.5, tip=1.2, th=0.32, shade=-1))
    # under layer (in shadow): fills between the outer clumps all round
    for a1, p1 in ((0, 48), (30, 52), (-30, 52), (60, 80), (-60, 80), (90, 92), (-90, 92), (120, 108), (-120, 108),   # k12: front ones end under the top layer (dark stripes between fringe clumps)
                   (150, 118), (-150, 118), (180, 120)):
        back.append(dict(a0=ca + J(10), p0=cp + J(4), a1=a1 + J(5), p1=p1 + J(4), w=0.095, vol=0.016 if abs(a1) < 45 or abs(a1) > 135 else 0.006, drop=0.004,
                         base=0.0, taper=0.5, tip=1.1, th=0.30, shade=0.55 if abs(a1) < 100 else 0.2))
    return {"Front": front, "Back": back}


STYLES = {"leo": _style_leo}


SHADOW_SIDE = 1          # k26: darker hair on the side away from the key light (TypeSafe k25 colour: 'almost no shadow side')
SHADOW_L = np.array([-0.6, -0.5, 0.62]) / np.linalg.norm([-0.6, -0.5, 0.62])   # k27: painted light direction (towards the light)
HAIR_SHADOW_TINT = (0.50, 0.42, 0.40)   # k28: hair-only toon shadow tint (linear multiplier)
SHADOW_T = -0.15         # dot below this = shadow side
CAST_SHADOW = False      # k5: the toon terminator reads Shader-to-RGB, so cast shadows darkened most clumps
HAIR_SHADER = 2         # 2: k3 toon (head's skin toon group recoloured) + painted highlight strokes; 1: NG_ToonHair
BASE_SRGB = (168, 128, 88)       # Leo lit hair (render median 155,118,82 incl. shadow; lit areas ~165-175)
HL_SRGB = (222, 186, 140)        # pale highlight strokes
EDGE_SRGB = (96, 62, 40)         # darker clump edges
EDGE_T = (0.72, 0.84)            # k13: only a thin line at the clump rims (0.52-0.62 drew wide dark wedges - stripes)
HL_BAND = (0.22, 0.40)           # highlight band along each clump (v from the root)


def _lin(c):
    c = np.asarray(c, float) / 255.0
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)) + (1.0,)


def _material(style):
    name = "MAT_Hair_" + style
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if HAIR_SHADER == 1:
        g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = bpy.data.node_groups["NG_ToonHair"]
        g.inputs["root_color"].default_value = ROOT_COL
        g.inputs["tip_color"].default_value = TIP_COL
        g.inputs["secondary_color"].default_value = TIP_COL
        g.inputs["highlight_strength"].default_value = 0.6
        g.inputs["streak_amount"].default_value = 0.6
        for nm, inp in (("hair_streak", "Streak Mask"), ("hair_line", "Clump Line Mask"), ("hair_shade", "Shadow Mask")):
            a = nt.nodes.new("ShaderNodeAttribute"); a.attribute_name = nm
            nt.links.new(a.outputs["Fac"], g.inputs[inp])
        nt.links.new(g.outputs["Shader"], out.inputs["Surface"])
        return m
    # k3: the head's toon group (hard terminator, warm shadow tint) with the hair colour; MHS3 hair is lit like the
    # skin - flat base, darker warm shadow shapes - plus thin pale strokes in a band a third down each clump
    grp = bpy.data.node_groups.get("NG_ToonSkin_NewHead") or bpy.data.node_groups["NG_ToonSkin"]
    if HAIR_SHADOW_TINT is not None:
        # k28: a hair copy of the group with a deeper, less orange shadow (Leo: shadow ~(110,75,52) vs lit (152,112,80);
        # the skin tint (0.62,0.48,0.40) gave the hair a saturated orange-red shadow)
        hg = bpy.data.node_groups.get(grp.name + "_Hair")
        if hg is None:
            hg = grp.copy(); hg.name = grp.name + "_Hair"
            for n in hg.nodes:
                if n.type == "GROUP" and "Shadow Tint" in n.inputs:
                    n.node_tree = n.node_tree.copy(); n.node_tree.name = n.node_tree.name.split(".")[0] + "_Hair"
        for n in hg.nodes:
            if n.type == "GROUP" and "Shadow Tint" in n.inputs:
                n.inputs["Shadow Tint"].default_value = tuple(HAIR_SHADOW_TINT) + (1.0,)
                if "Shadow 2 Tint" in n.inputs:
                    n.inputs["Shadow 2 Tint"].default_value = tuple(c * 0.85 for c in HAIR_SHADOW_TINT) + (1.0,)
        grp = hg
    g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = grp
    base = tuple(min(1.0, c * LIGHTNESS) for c in _lin(BASE_SRGB)[:3]) + (1.0,)
    g.inputs["skin_color"].default_value = base
    if "blush_strength" in g.inputs:
        g.inputs["blush_strength"].default_value = 0.0
    ash = nt.nodes.new("ShaderNodeAttribute"); ash.attribute_name = "hair_shade"
    nt.links.new(ash.outputs["Fac"], g.inputs["Shadow Mask"])
    geo = nt.nodes.new("ShaderNodeNewGeometry")            # k4: the group's Normal input is not used unlinked (all shadow)
    nt.links.new(geo.outputs["Normal"], g.inputs["Normal"])
    last = g.outputs[0]
    # darker clump edges (the lens rims)
    ale = nt.nodes.new("ShaderNodeAttribute"); ale.attribute_name = "hair_line"
    mre = nt.nodes.new("ShaderNodeMapRange"); mre.inputs["From Min"].default_value = EDGE_T[0]; mre.inputs["From Max"].default_value = EDGE_T[1]
    nt.links.new(ale.outputs["Fac"], mre.inputs["Value"])
    eme = nt.nodes.new("ShaderNodeEmission"); eme.inputs["Color"].default_value = _lin(EDGE_SRGB)
    mxe = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mre.outputs["Result"], mxe.inputs["Fac"]); nt.links.new(last, mxe.inputs[1]); nt.links.new(eme.outputs[0], mxe.inputs[2])
    last = mxe.outputs[0]
    # highlight strokes: UV band x diagonal stripes x streak clumps x lit side (shadow mask)
    uv = nt.nodes.new("ShaderNodeUVMap")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(uv.outputs[0], sep.inputs[0])
    def M(op, a, b=None):
        n_ = nt.nodes.new("ShaderNodeMath"); n_.operation = op
        for k_, v_ in enumerate((a, b)):
            if v_ is None:
                continue
            if isinstance(v_, (int, float)):
                n_.inputs[k_].default_value = v_
            else:
                nt.links.new(v_, n_.inputs[k_])
        return n_.outputs[0]
    v = sep.outputs[1]; u = sep.outputs[0]
    band = M("MULTIPLY", M("GREATER_THAN", v, HL_BAND[0]), M("LESS_THAN", v, HL_BAND[1]))
    stripe = M("LESS_THAN", M("FRACT", M("ADD", M("MULTIPLY", u, 3.0), M("MULTIPLY", v, 9.0))), 0.22)
    ast = nt.nodes.new("ShaderNodeAttribute"); ast.attribute_name = "hair_streak"
    hl = M("MULTIPLY", M("MULTIPLY", band, stripe), M("MULTIPLY", ast.outputs["Fac"], ash.outputs["Fac"]))
    emh = nt.nodes.new("ShaderNodeEmission"); emh.inputs["Color"].default_value = _lin(HL_SRGB)
    mxh = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(hl, mxh.inputs["Fac"]); nt.links.new(last, mxh.inputs[1]); nt.links.new(emh.outputs[0], mxh.inputs[2])
    nt.links.new(mxh.outputs[0], out.inputs["Surface"])
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


def _mesh_from(name, clumps_rings, col, off_x, mats, streak, shades=None):
    verts, faces, uvs, attr_s, attr_l, attr_h = [], [], [], [], [], []
    rng = np.random.default_rng(17)
    for ci, rings in enumerate(clumps_rings):
        base = len(verts)
        sh = shades[ci] if shades else 0.0
        jit = rng.uniform(-0.05, 0.05)
        for i, ring in enumerate(rings):
            t = i / (len(rings) - 1)
            hv = 0.0 if sh < 0 else (1.0 if t > sh + jit else 0.0)    # k2: the root part sits in the shadow of the clump above
            for k, p in enumerate(ring):
                verts.append(tuple(p))
                # k26: shadow side - the hair on the far side from the key light (+x, image right) sits in toon shadow
                # except the tips (Leo render: one side of the mass clearly darker, lit strand tips breaking the edge)
                # k27: by the direction from the head centre against a painted light (front-top, from image left) rather
                # than a flat x split (k26: a hard vertical seam at the back, the whole profile dark)
                dd = np.asarray(p) - C; dd = dd / (np.linalg.norm(dd) + 1e-9)
                lit = float(np.dot(dd, SHADOW_L)) + 0.05 * math.sin(41.0 * p[2] + 3.0 * ci)
                hk = 0.0 if (SHADOW_SIDE and lit < SHADOW_T and t < 0.82) else hv
                attr_s.append(streak[ci]); attr_l.append(len(ring) > 1 and abs(math.sin(2 * math.pi * k / RING)) < 0.2); attr_h.append(hk)   # k14: not the tip point (dark tips)
        nr = len(rings) - 1
        for i in range(nr - 1):
            for k in range(RING):
                a = base + i * RING + k; b = base + i * RING + (k + 1) % RING
                faces.append((a, a + RING, b + RING, b))     # k6: outward winding (was inward: shaded as back faces)
        tip = base + nr * RING
        for k in range(RING):
            a = base + (nr - 1) * RING + k; b = base + (nr - 1) * RING + (k + 1) % RING
            faces.append((a, tip, b))
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
    for nm, val in (("hair_streak", attr_s), ("hair_line", attr_l), ("hair_shade", attr_h)):
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
        streak = [1.0 if (c.get("shade", 0.0) >= 0 and rng.random() < HL_SHARE) else 0.0 for c in clumps]
        o = _mesh_from("Hair_%s_%s" % (piece, style), rings, col, off_x, [hm], streak, [c.get("shade", 0.0) for c in clumps])
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
        o.visible_shadow = CAST_SHADOW                  # k5: the clumps shadowed each other into one dark mass
        made.append(o)
    cap = _cap(sc, head, col, off_x, style, cm); cap.visible_shadow = False
    made.append(cap)
    return col, made
