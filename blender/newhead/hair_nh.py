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


def _catmull(P, n):
    """n points along a Catmull-Rom spline through control points P (k x 3), evenly in parameter."""
    P = np.asarray(P, float)
    if len(P) == 2:
        return np.array([P[0] + (P[1] - P[0]) * i / (n - 1) for i in range(n)])
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    segs = len(P) - 1
    for i in range(n):
        s = i / (n - 1) * segs
        j = min(int(s), segs - 1); t = s - j
        p0, p1, p2, p3 = Q[j], Q[j + 1], Q[j + 2], Q[j + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)


def _resample(pts, n, length_scale=1.0):
    """n points along polyline pts by arc length, scaled to length_scale x its length (extrapolated past the end)."""
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)]); L = cum[-1]
    out = []
    for i in range(n):
        s = i / (n - 1) * L * length_scale
        if s <= L:
            j = min(np.searchsorted(cum, s, side="right") - 1, len(seg) - 1)
            f = (s - cum[j]) / max(seg[j], 1e-9)
            out.append(pts[j] + (pts[j + 1] - pts[j]) * f)
        else:
            d = pts[-1] - pts[-2]; d /= np.linalg.norm(d) + 1e-9
            out.append(pts[-1] + d * (s - L))
    return np.array(out)


def clump_path(sc, c, vol=1.0, lng=1.0):
    """Centre line (SEG+1 points) and outward reference normals of one clump spec c.
    Skull clumps (a0,p0 -> a1,p1): k2 slerp over the skull with lift / drop / flick, optionally continued by a free
    fall (c["fall"] m, m1: long hair, sidelocks). Free clumps (c["path"]: control points, m1: tails, braid lobes,
    buns): Catmull-Rom through the points; vol scales the spread of the points off the root->end line, lng the length."""
    if "path" in c:
        P = np.asarray(c["path"], float)
        if vol != 1.0:
            a, b = P[0], P[-1]; ab = b - a; ab2 = max(np.dot(ab, ab), 1e-12)
            P = np.array([a + ab * np.dot(p - a, ab) / ab2 + (p - a - ab * np.dot(p - a, ab) / ab2) * vol for p in P])
        dense = _catmull(P, 4 * SEG)
        pts = _resample(dense, SEG + 1, lng * c.get("lng_k", 1.0))
        if "nref" in c:
            nrm = np.tile(np.asarray(c["nref"], float), (SEG + 1, 1))
        else:
            nrm = pts - C; nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
        return pts, nrm
    vol = vol * VOL_SCALE * (SIDE_SCALE if c.get("side") else 1.0)
    if c.get("fringe"):
        lng = lng * FRINGE_LEN
    fall = c.get("fall", 0.0)
    skull_lng = lng if not fall else 1.0
    n_sk = SEG + 1 if not fall else max(5, int(round((SEG + 1) * c.get("skull_share", 0.45))))
    u0 = _dir(c["a0"], c["p0"]); u1 = _dir(c["a1"], c["p1"])
    side_ax = np.cross(u0, u1); nrm_ = np.linalg.norm(side_ax)
    side_ax = side_ax / nrm_ if nrm_ > 1e-6 else np.array([1.0, 0.0, 0.0])
    pts, nrm = [], []
    for i in range(n_sk):
        t = i / (n_sk - 1)
        tt = t ** c.get("ease", 1.0)
        d = _slerp(u0, u1, tt * skull_lng)                          # lng > 1 runs on past the tip direction
        bend = c.get("bend", 0.0) * math.sin(math.pi * t)           # S / C curve sideways (radians)
        d = d + side_ax * bend; d /= np.linalg.norm(d)
        if fall:
            lift = vol * c["vol"] * math.sin(math.pi * min(t / 0.5, 1.0) * 0.5)
        else:
            lift = vol * c["vol"] * math.sin(math.pi * min(t / 0.5, 1.0) * 0.5)
            lift -= c.get("drop", 0.004) * max(0.0, (t - 0.55) / 0.45) ** 2
            lift += c.get("flick", 0.0) * vol * max(0.0, (t - 0.55) / 0.45) ** 2
        lift += (TOP_EXTRA if c["p0"] < 25 else 0.0) * math.sin(math.pi * min(t / 0.6, 1.0) * 0.5)
        r = sc.radius(d) + c.get("base", 0.0) - 0.002 * (1 - t) + lift
        pts.append(C + d * r); nrm.append(d)
    if fall:
        # m1: free fall from the skull end - tangent bends to straight down; out pushes it off the head / shoulders
        p_end = pts[-1]; t_end = pts[-1] - pts[-2]; t_end /= np.linalg.norm(t_end)
        out = nrm[-1].copy(); out[2] = 0.0; out /= np.linalg.norm(out) + 1e-9
        L = fall * lng
        P = [p_end, p_end + t_end * L * 0.25 + out * c.get("fall_out", 0.01) * vol,
             p_end + np.array([0, 0, -L * 0.6]) + out * c.get("fall_out", 0.01) * 1.6 * vol,
             p_end + np.array([0, 0, -L]) + out * (c.get("fall_out", 0.01) * 1.8 * vol + c.get("flick", 0.0) * vol)]
        tail = _resample(_catmull(P, 3 * SEG), SEG + 2 - n_sk)[1:]
        for p in tail:
            pts.append(p); nrm.append(out * 0.7 + nrm[-1] * 0.3)
    pts = np.array(pts); nrm = np.array(nrm)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    return pts, nrm


def clump_rings(sc, c, vol=1.0, wid=1.0, lng=1.0):
    """Ring vertices (SEG rings of RING + the tip point) of one clump spec c: a flat blade (th ~0.3 x width) along the
    clump path whose tip tapers late and asymmetrically (MHS3 leaf-shaped clumps with one straighter edge); m1:
    profile "leaf" (both ends pointed - braid lobes) and "blunt" (no point - blunt-cut bangs)."""
    wid = wid * WID_SCALE
    pts, nrm = clump_path(sc, c, vol, lng)
    tan = np.gradient(pts, axis=0); tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    out = []
    asym = c.get("asym", 0.0)
    prof = c.get("profile", "blade")
    for i in range(SEG + 1):
        t = i / SEG
        if prof == "leaf":
            env = max(0.12, math.sin(math.pi * min(max(t, 0.0), 1.0)) ** 0.7) if i < SEG else 0.0
        elif prof == "blunt":
            env = (0.75 + 0.25 * min(1.0, t / 0.3)) * (1 - 0.35 * max(0.0, (t - 0.85) / 0.15))
        else:
            env = (0.65 + 0.35 * min(1.0, t / 0.3)) * (1 - max(0.0, (t - c.get("taper", 0.5)) / (1 - c.get("taper", 0.5)))) ** c.get("tip", 1.1)
        w = c["w"] * wid * env
        th = max(w, 0.006) * c.get("th", 0.32)
        n = nrm[i] - tan[i] * np.dot(nrm[i], tan[i]); n /= np.linalg.norm(n) + 1e-9
        b = np.cross(tan[i], n)
        tw = math.radians(c.get("twist", 0.0)) * t
        b, n = b * math.cos(tw) + n * math.sin(tw), n * math.cos(tw) - b * math.sin(tw)
        ctr = pts[i] + b * (asym * c["w"] * wid * 0.35 * t * t)     # blade tip: the point drifts to one edge
        if i == SEG and prof != "blunt":
            out.append([ctr])
            continue
        if i == SEG:
            out.append([ctr + n * th * 0.1])
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

# ---------------------------------------------------------------------------------------------------------------
# m1 (2026-10-15): modular hair. A hairstyle is a RECIPE: one variant per REGION (Front, Top, SideL, SideR, Back,
# Base) plus any number of ATTACHMENTS (tails, braids, buns, ahoge). Every region / attachment is its own object
# (Hair_<Piece>_<recipe>, socket SOC-Hair<Piece>) with the same creator keys (ID-HairVolume/Width/Length + _Neg),
# so the creator mixes pieces and tunes each one instead of picking whole presets. Research behind the split:
# commercial anime hair kits ship front / back / side / ponytail / extra modules (e.g. Anime Modular Hair Builder:
# 49 front, 26 back, 25 side, 31 ponytail, 37 extras) and MHS3's own creator offers Front + Back packs with two-tone
# colour; braids are generated from one guide path (Braidify, Blender's Braid Hair Curves node group).
# Variant params (all optional) come from the recipe, so the same variant yields many cuts.
# ---------------------------------------------------------------------------------------------------------------


def _rng(seed):
    r = np.random.default_rng(seed)
    return r, (lambda s_: r.uniform(-s_, s_))


def _front_sweep(sc, P):
    """Leo fringe (k20-k31): wide overlapping sheet swept from one side (dir +1: from his right toward his left),
    longest point just above the upper lid, a thin strand over each clump (TypeSafe k25/k28 clumps_narrower)."""
    rng, J = _rng(P.get("seed", 5))
    s = P.get("dir", 1); dp = P.get("len", 0.0); wk = P.get("width", 1.0)
    out = []
    for a1, p1, w, bend, asym, a0 in ((-10, 97, 0.110, 0.10, 1, -32), (12, 86, 0.100, 0.10, 1, -8), (34, 81, 0.090, 0.08, 1, 14),
                                      (-36, 92, 0.100, 0.08, 1, -56), (56, 84, 0.070, 0.06, -1, 40),
                                      (4, 93, 0.054, 0.06, 1, -16), (-60, 92, 0.080, 0.04, 1, -76)):
        out.append(dict(a0=s * a0 + J(3), p0=4 + J(2), a1=s * a1 + J(2), p1=p1 + dp + J(1.5), w=w * wk,
                        vol=0.024 if abs(a1) < 30 else (0.016 if abs(a1) < 55 else 0.010), drop=0.014,
                        base=0.005, bend=s * bend, asym=s * asym, taper=0.42, tip=1.25, th=0.30, shade=0.32, fringe=1))
    for fc in list(out):
        off = rng.choice([-1, 1]) * rng.uniform(5, 9); d_ = rng.uniform(3, 7)
        out.append(dict(fc, a1=fc["a1"] + off, p1=fc["p1"] - d_, a0=fc["a0"] + off * 0.5, w=(0.026 + J(0.004)) * wk,
                        vol=fc["vol"] + 0.004, base=fc["base"] + 0.002, taper=0.35, tip=1.1, th=0.35,
                        shade=0.15, asym=-fc["asym"]))
    return out


def _front_part(sc, P):
    """Parted fringe: clumps fall away from a part line at azimuth `part` (0 = centre), curving outward, tips at
    `len` (polar deg; 90 ~ brow), `count` clumps per side."""
    rng, J = _rng(P.get("seed", 7))
    part = P.get("part", 0.0); tip = P.get("len", 90.0); n = P.get("count", 4); wk = P.get("width", 1.0)
    counts = {-1: P.get("count_r", n), 1: P.get("count_l", n)}       # m2: asymmetric side part (Leia)
    reach = {-1: P.get("reach_r", 62.0), 1: P.get("reach_l", 62.0)}
    out = []
    for side in (-1, 1):
        for i in range(counts[side]):
            f = (i + 0.5) / counts[side]
            a1 = part + side * (8 + reach[side] * f) + J(3)
            out.append(dict(a0=part + side * (2 + 10 * f) + J(2), p0=6 + J(2), a1=a1, p1=tip + 6 * f + J(2),
                            w=(0.085 - 0.02 * f) * wk, vol=0.022 if f < 0.5 else 0.012, drop=0.012, base=0.005,
                            bend=side * 0.10, asym=side, taper=0.45, tip=1.2, th=0.30, shade=0.3, fringe=1))
            out.append(dict(out[-1], a1=a1 + side * rng.uniform(4, 8), p1=out[-1]["p1"] - rng.uniform(3, 6),
                            w=0.026 * wk, vol=out[-1]["vol"] + 0.004, base=0.007, taper=0.35, tip=1.1, th=0.35,
                            shade=0.15, asym=-side))
    return out


def _front_blunt(sc, P):
    """Blunt-cut bangs: many clumps with tips on one line (`len`), squared ends with a slight point (`point` 0-1)."""
    rng, J = _rng(P.get("seed", 9))
    tip = P.get("len", 92.0); n = P.get("count", 9); wk = P.get("width", 1.0); pt = P.get("point", 0.4)
    out = []
    for i in range(n):
        f = i / (n - 1) * 2 - 1
        a1 = 62 * f + J(2)
        c = dict(a0=a1 * 0.4 + J(3), p0=5 + J(2), a1=a1, p1=tip + 4 * abs(f) ** 2 + J(1.0), w=0.075 * wk,
                 vol=0.020 if abs(f) < 0.6 else 0.012, drop=0.010, base=0.005, bend=J(0.03), asym=rng.choice([-1, 1]),
                 th=0.30, shade=0.3, fringe=1)
        if pt < 0.5:
            c.update(profile="blunt")
        else:
            c.update(taper=0.7, tip=1.0)
        out.append(c)
    return out


def _top_layered(sc, P):
    """Leo top (k11-k30): narrow clumps from the crown sweeping forward and sideways with lifted tips, a few
    flyaway strands over the top, two thin standing spikes (`spikes` 0 removes them)."""
    rng, J = _rng(P.get("seed", 5)); ca, cp = CROWN
    vk = P.get("vol", 1.0); fk = P.get("flick", 1.0)
    out = []
    for a1, p1, fl in ((-16, 50, 0.006), (8, 46, 0.006), (30, 50, 0.008), (-38, 52, 0.010), (48, 54, 0.010), (-58, 56, 0.008),
                       (66, 54, 0.010), (-76, 56, 0.010), (92, 56, 0.006), (-100, 58, 0.006), (124, 52, 0.004), (-128, 52, 0.004),
                       (150, 46, 0.004), (-155, 46, 0.004)):
        out.append(dict(a0=ca + J(14), p0=cp - 8 + J(4), a1=a1 + J(4), p1=p1 + J(4), w=0.066,
                        vol=vk * (0.040 if abs(a1) < 40 else (0.022 if abs(a1) < 70 else 0.010)),
                        drop=0.0 if fl > 0.012 else 0.008, flick=fl * fk,
                        base=0.006, bend=J(0.12), asym=rng.choice([-1, 1]), taper=0.4, tip=1.3, th=0.32, shade=0.0))
    if P.get("flyaways", 1):
        for a1, p1, fl in ((-60, 24, 0.012), (-30, 20, 0.014), (40, 22, 0.012), (70, 26, 0.010)):
            out.append(dict(a0=ca + J(10), p0=cp - 6 + J(3), a1=a1 + J(4), p1=p1 + J(3), w=0.022, vol=0.030, flick=fl * fk, drop=0.0,
                            base=0.008, bend=J(0.15), asym=rng.choice([-1, 1]), taper=0.3, tip=1.0, th=0.35, shade=0.0))
    if P.get("spikes", 1):
        for a1, p1, h in ((-10, 20, 0.050), (16, 24, 0.042)):
            out.append(dict(a0=a1 + 175, p0=6, a1=a1, p1=p1, w=0.034, vol=0.030, flick=h * P.get("spikes", 1), base=0.012,
                            taper=0.25, tip=1.0, th=0.35, shade=0.0, ease=0.7, bend=0.15 if a1 > 0 else -0.15))
    return out


def _top_slick(sc, P):
    """Slicked back: clumps from the front hairline over the top to the back, lying close."""
    rng, J = _rng(P.get("seed", 11))
    out = []
    for i in range(11):
        a = -75 + 15 * i + J(3)
        out.append(dict(a0=a * 0.8, p0=58 + J(3), a1=180 - a * 0.35 + J(4), p1=70 + abs(a) * 0.25 + J(3), w=0.070,
                        vol=0.016 * P.get("vol", 1.0), drop=0.004, base=0.004, bend=J(0.05), asym=rng.choice([-1, 1]),
                        taper=0.55, tip=1.2, th=0.30, shade=0.0))
    return out


def _side_temple(sc, P, sgn):
    """Leo sides (k7-k18): down the temples over the top of the ears, outer tips flaring a little."""
    rng, J = _rng(P.get("seed", 13) + (sgn > 0))
    dp = P.get("len", 0.0)
    out = []
    for a1, p1, w, fl in ((64, 104, 0.054, 0.012), (80, 100, 0.058, 0.014), (97, 98, 0.058, 0.012), (114, 104, 0.054, 0.008)):
        out.append(dict(a0=sgn * (a1 - 40) + J(4), p0=40 + J(4), a1=sgn * a1 + J(3), p1=p1 + dp + J(3), w=w, vol=0.016,
                        flick=fl, drop=0.0, base=0.001, bend=sgn * 0.06, asym=-sgn, taper=0.45, tip=1.25, th=0.30,
                        shade=0.0, side=1))
    return out


def _side_long(sc, P, sgn):
    """Sidelocks: two or three clumps from the temple down in front of the ear, then a free fall of `len` m."""
    rng, J = _rng(P.get("seed", 17) + (sgn > 0))
    L = P.get("len", 0.10); n = P.get("count", 3)
    out = []
    for i in range(n):
        a1 = sgn * (70 + 12 * i) + J(2)
        out.append(dict(a0=sgn * (30 + 10 * i) + J(3), p0=30 + J(3), a1=a1, p1=100 + J(2), w=0.060 - 0.008 * i,
                        vol=0.012, base=0.002, fall=L * (1 - 0.18 * i), fall_out=0.012, skull_share=0.5, flick=P.get("flick", 0.0),
                        bend=sgn * 0.04, asym=-sgn, taper=0.55, tip=1.2, th=0.32, shade=0.0, side=1))
    return out


def _back_layers(sc, P):
    """Leo back (k3): two rows of short pointed layers to the nape."""
    rng, J = _rng(P.get("seed", 19)); ca, cp = CROWN
    dp = P.get("len", 0.0)
    out = []
    for a1 in np.arange(120, 241, 12):
        out.append(dict(a0=ca + J(8), p0=cp + 8, a1=a1 + J(3), p1=128 + dp + J(6), w=0.070, vol=0.022, drop=0.006, flick=0.003,
                        base=0.002, bend=J(0.08), asym=rng.choice([-1, 1]), taper=0.5, tip=1.2, th=0.32, shade=0.0))
    for a1 in np.arange(126, 236, 18):
        out.append(dict(a0=ca + J(8), p0=cp + 20, a1=a1 + J(3), p1=134 + dp + J(5), w=0.060, vol=0.012, drop=0.004, flick=0.002,
                        base=0.0, bend=J(0.06), asym=rng.choice([-1, 1]), taper=0.5, tip=1.2, th=0.32, shade=-1))
    return out


def _back_long(sc, P):
    """Long back hair: clumps down the back of the skull to the nape, then falling `len` m (shoulder ~0.18)."""
    rng, J = _rng(P.get("seed", 23)); ca, cp = CROWN
    L = P.get("len", 0.20); n = P.get("count", 14)
    out = []
    for i in range(n):
        a1 = 105 + 150 * i / (n - 1) + J(3)
        out.append(dict(a0=ca + J(10), p0=cp + J(4), a1=a1, p1=118 + J(3), w=0.075, vol=0.018, base=0.003,
                        fall=L * (0.85 + 0.15 * math.sin(math.radians(a1 - 180) + 1.57)) + J(0.015), fall_out=0.016,
                        skull_share=0.4, bend=J(0.06), asym=rng.choice([-1, 1]), taper=0.6, tip=1.2, th=0.30, shade=0.0))
    return out


def _back_tied(sc, P):
    """Pulled back into a tie at anchor (a, p): clumps from the hairline all round converge on the anchor."""
    rng, J = _rng(P.get("seed", 29))
    aa, ap = P.get("anchor", (180.0, 80.0))
    out = []
    n = P.get("count", 24)
    for i in range(n):
        a0 = -165 + 330 * i / (n - 1) + J(4)
        p0 = P.get("hairline", 58) + 50 * (abs(a0) / 180.0) ** 1.5
        out.append(dict(a0=a0, p0=p0 + J(3), a1=aa + J(2), p1=ap + J(2), w=0.090, vol=0.012 * P.get("vol", 1.0), drop=0.0, base=0.003,
                        bend=J(0.04), asym=rng.choice([-1, 1]), taper=0.7, tip=1.0, th=0.28, shade=0.0, ease=0.9))
    return out


def _base_under(sc, P):
    """Under layer in shadow (k12): fills between the outer clumps all round."""
    rng, J = _rng(P.get("seed", 31)); ca, cp = CROWN
    out = []
    for a1, p1 in ((0, 48), (30, 52), (-30, 52), (60, 80), (-60, 80), (90, 92), (-90, 92), (120, 108), (-120, 108),
                   (150, 118), (-150, 118), (180, 120)):
        out.append(dict(a0=ca + J(10), p0=cp + J(4), a1=a1 + J(5), p1=p1 + J(4), w=0.095,
                        vol=0.016 if abs(a1) < 45 or abs(a1) > 135 else 0.006, drop=0.004,
                        base=0.0, taper=0.5, tip=1.1, th=0.30, shade=0.55 if abs(a1) < 100 else 0.2))
    return out


REGION_VARIANTS = {
    "Front": {"sweep": _front_sweep, "part": _front_part, "blunt": _front_blunt, "none": lambda sc, P: []},
    "Top": {"layered": _top_layered, "slick": _top_slick, "none": lambda sc, P: []},
    "SideL": {"temple": lambda sc, P: _side_temple(sc, P, 1), "long": lambda sc, P: _side_long(sc, P, 1), "none": lambda sc, P: []},
    "SideR": {"temple": lambda sc, P: _side_temple(sc, P, -1), "long": lambda sc, P: _side_long(sc, P, -1), "none": lambda sc, P: []},
    "Back": {"layers": _back_layers, "long": _back_long, "tied": _back_tied, "none": lambda sc, P: []},
    "Base": {"under": _base_under, "none": lambda sc, P: []},
}


# ---- attachments (free-path clumps) ------------------------------------------------------------------------------

def _anchor(sc, a, p, lift=0.0):
    d = _dir(a, p)
    return C + d * (sc.radius(d) + lift), d


def _frame(axis):
    axis = np.asarray(axis, float); axis /= np.linalg.norm(axis)
    ref = np.array([0.0, 0.0, 1.0]) if abs(axis[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(axis, ref); u /= np.linalg.norm(u)
    v = np.cross(axis, u)
    return u, v


def _att_tail(sc, P):
    """Ponytail / pigtail: a tie at anchor (a, p); `count` clumps leave the tie outward and fall `len` m with
    gravity, splaying by `splay`; `lift` raises the arc (high ponytail)."""
    rng, J = _rng(P.get("seed", 37))
    a, p = P.get("anchor", (180.0, 80.0))
    root, n = _anchor(sc, a, p, 0.010)
    L = P.get("len", 0.22); N = P.get("count", 12); w = P.get("width", 0.056); spl = P.get("splay", 0.035)
    rise = P.get("lift", 0.02); rt = P.get("tie_r", 0.016)
    u, v = _frame(n)
    down = np.array([0.0, 0.0, -1.0])
    out_h = n.copy(); out_h[2] = 0.0; out_h /= np.linalg.norm(out_h) + 1e-9
    clumps = []
    for i in range(N):
        th_ = 2 * math.pi * i / N + J(0.2)
        radial = u * math.cos(th_) + v * math.sin(th_)
        r0 = root + radial * rt * 0.6
        lk = 1.0 + J(0.12)
        # m2: a short rise off the tie, then back and down (m1's control points overshot ~12 cm up)
        path = [r0,
                r0 + n * 0.018 + np.array([0, 0, rise]) + radial * 0.010,
                r0 + n * 0.022 + out_h * 0.035 + down * L * 0.35 * lk + radial * spl * 0.9,
                r0 + out_h * 0.045 + down * L * lk + radial * spl + np.array([J(0.01), J(0.01), 0])]
        clumps.append(dict(path=path, nref=radial, w=w * (0.9 + J(0.15)), th=0.45, taper=0.55, tip=1.2,
                           asym=rng.choice([-1, 1]), shade=0.25 if i % 2 else 0.0))
    ties = [dict(center=root + n * 0.004, axis=n, R=rt + 0.003, r=0.0035)]
    if P.get("tie") == "bow":
        ties.append(dict(bow=_bow(root + n * 0.016, n, P.get("bow_size", 0.035), rng)))
    return clumps, ties


def _bow(ctr, axis, size, rng):
    """m2: ribbon bow over a tie (Leia's ponytail): two flat loops and two short hanging tails, as tie-material
    clumps (flat leaf / blade profiles)."""
    up = np.array([0.0, 0.0, 1.0]); a = np.asarray(axis, float)
    side = np.cross(a, up); side = side / (np.linalg.norm(side) + 1e-9) if np.linalg.norm(side) > 1e-6 else np.array([1.0, 0, 0])
    vert = np.cross(side, a); vert /= np.linalg.norm(vert)
    cl = []
    for s in (1, -1):
        p0 = ctr; tip = ctr + side * s * size + vert * size * 0.25
        path = [p0, p0 + side * s * size * 0.35 + vert * size * 0.45, tip + vert * size * 0.15, tip - vert * size * 0.35,
                p0 + side * s * size * 0.30 - vert * size * 0.25, p0 + side * s * 0.002]
        cl.append(dict(path=path, nref=a, w=size * 0.55, th=0.22, profile="leaf", shade=0.0))
        cl.append(dict(path=[p0, p0 + side * s * size * 0.25 - vert * size * 0.6, p0 + side * s * size * 0.45 - vert * size * 1.2],
                       nref=a, w=size * 0.38, th=0.22, taper=0.6, tip=0.8, asym=s, shade=0.3))
    return cl


def _braid_lobes(cp, wB, n_lobes, out_ref, tilt=38.0):
    """m1 braid: alternating tilted leaf lobes along the centre path cp (the anime three-strand look: a chain of
    chevrons), as free-path clumps."""
    dense = _resample(_catmull(cp, 6 * SEG), 200)
    tan = np.gradient(dense, axis=0); tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    L = np.sum(np.linalg.norm(np.diff(dense, axis=0), axis=1)); step = L / n_lobes
    lobes = []
    for k in range(n_lobes):
        s = (k + 0.55) / n_lobes; j = int(s * 199)
        ctr = dense[j]; t = tan[j]
        nn = out_ref - t * np.dot(out_ref, t); nn /= np.linalg.norm(nn) + 1e-9
        b = np.cross(t, nn)
        side = 1 if k % 2 == 0 else -1
        ang = math.radians(tilt) * side
        d = t * math.cos(ang) - b * math.sin(ang)
        c0 = ctr + b * side * wB * 0.22
        half = step * 0.95
        path = [c0 - d * half, c0 - d * half * 0.3 + nn * wB * 0.10, c0 + d * half * 0.3 + nn * wB * 0.10, c0 + d * half]
        lobes.append(dict(path=path, nref=nn, w=wB * 0.62, th=0.62, profile="leaf", shade=0.0 if side > 0 else 0.35))
    return lobes, dense[-1], tan[-1]


def _att_braid(sc, P):
    """Braid hanging from anchor (a, p): `len` m, `width`, lobe count from the length; tie + short tuft at the end.
    Braided ponytail = a tail anchor with braid=1 (no separate pass)."""
    rng, J = _rng(P.get("seed", 41))
    a, p = P.get("anchor", (120.0, 105.0))
    root, n = _anchor(sc, a, p, 0.008)
    L = P.get("len", 0.24); wB = P.get("width", 0.036)
    out_h = n.copy(); out_h[2] = 0.0; out_h /= np.linalg.norm(out_h) + 1e-9
    cp = [root, root + out_h * 0.02 + np.array([0, 0, -0.04]), root + out_h * 0.035 + np.array([0, 0, -L * 0.6]),
          root + out_h * 0.04 + np.array([0, 0, -L])]
    lobes, end, t_end = _braid_lobes(cp, wB, max(4, int(round(L / (wB * 0.75)))), out_h)
    tuft = []
    u, v = _frame(t_end)
    for i in range(4):
        th_ = 2 * math.pi * i / 4 + 0.4
        rad = u * math.cos(th_) + v * math.sin(th_)
        r0 = end + t_end * 0.004
        tuft.append(dict(path=[r0, r0 + t_end * 0.03 + rad * 0.008, r0 + t_end * 0.065 + rad * 0.018],
                         nref=rad, w=wB * 0.55, th=0.4, taper=0.3, tip=1.1, shade=0.0))
    ties = [dict(center=end - t_end * 0.002, axis=t_end, R=wB * 0.24, r=0.0035)]
    return lobes + tuft, ties


def _att_bun(sc, P):
    """Bun at anchor (a, p), radius `r`: clumps wrapped round a sphere in different planes, tie at its base."""
    rng, J = _rng(P.get("seed", 43))
    a, p = P.get("anchor", (180.0, 40.0))
    root, n = _anchor(sc, a, p, 0.0)
    R = P.get("r", 0.040)
    ctr = root + n * R * 0.85
    clumps = []
    for i in range(P.get("count", 9)):
        ax = rng.normal(size=3); ax /= np.linalg.norm(ax)
        u, v = _frame(ax)
        start = rng.uniform(0, 2 * math.pi)
        path = [ctr + R * (u * math.cos(start + s) + v * math.sin(start + s)) for s in np.linspace(0, 1.6 * math.pi, 6)]
        clumps.append(dict(path=path, w=R * 0.85, th=0.40, taper=0.6, tip=1.1, asym=rng.choice([-1, 1]),
                           shade=0.0 if i % 3 else 0.4, nref_center=ctr))
    for c in clumps:            # thickness direction = out from the bun centre (approximated at the path middle)
        mid = np.asarray(c["path"][2]); c["nref"] = (mid - ctr) / np.linalg.norm(mid - ctr)
        del c["nref_center"]
    ties = [dict(center=root + n * 0.006, axis=n, R=R * 0.55, r=0.004)]
    return clumps, ties


def _att_ahoge(sc, P):
    """Ahoge: one big curled spike standing off the top."""
    a, p = P.get("anchor", (0.0, 18.0))
    root, n = _anchor(sc, a, p, 0.004)
    h = P.get("len", 0.07); f = _dir(a, 90.0)
    path = [root, root + n * h * 0.5 + f * 0.01, root + n * h * 0.9 + f * h * 0.4, root + n * h * 0.7 + f * h * 0.75]
    return [dict(path=path, nref=f, w=0.030, th=0.35, taper=0.2, tip=1.0, shade=0.0)], []


ATTACH = {"tail": _att_tail, "braid": _att_braid, "bun": _att_bun, "ahoge": _att_ahoge}


RECIPES = {
    # MHS3 Leo (k31), now as modules
    "leo": dict(Front=("sweep", {}), Top=("layered", {}), SideL=("temple", {}), SideR=("temple", {}),
                Back=("layers", {}), Base=("under", {}), attach=[]),
    # creator demos built only from the same parts + params
    "ponytail": dict(Front=("part", {"part": 18, "len": 86}), Top=("layered", {"spikes": 0, "flyaways": 0, "vol": 0.6}),
                     SideL=("long", {"len": 0.05, "count": 2}), SideR=("long", {"len": 0.05, "count": 2}),
                     Back=("tied", {"anchor": (180, 62)}), Base=("under", {}),
                     attach=[("Tail", "tail", {"anchor": (180, 62), "len": 0.26, "lift": 0.03})]),
    "twintails": dict(Front=("blunt", {"len": 90}), Top=("layered", {"spikes": 0, "vol": 0.7}),
                      SideL=("long", {"len": 0.08}), SideR=("long", {"len": 0.08}),
                      Back=("tied", {"anchor": (180, 90)}), Base=("under", {}),
                      attach=[("TailL", "tail", {"anchor": (112, 62), "len": 0.30, "splay": 0.05}),
                              ("TailR", "tail", {"anchor": (-112, 62), "len": 0.30, "splay": 0.05, "seed": 38})]),
    "braids": dict(Front=("part", {"part": 0, "len": 88, "count": 3}), Top=("layered", {"spikes": 0, "flyaways": 0, "vol": 0.6}),
                   SideL=("temple", {}), SideR=("temple", {}),
                   Back=("long", {"len": 0.10}), Base=("under", {}),
                   attach=[("BraidL", "braid", {"anchor": (118, 108), "len": 0.26}),
                           ("BraidR", "braid", {"anchor": (-118, 108), "len": 0.26, "seed": 42})]),
    # MHS3 Leia (render): high ponytail with a purple ribbon bow, fringe parted on her right and swept across,
    # long wispy sidelocks with flicked ends, the rest pulled back smooth
    "leia": dict(Front=("part", {"part": -38, "len": 96, "count_r": 2, "reach_r": 40, "count_l": 5, "reach_l": 100, "width": 1.0}),
                 Top=("none", {}), SideL=("long", {"len": 0.13, "count": 3, "flick": 0.015}),
                 SideR=("long", {"len": 0.14, "count": 3, "flick": 0.015}),
                 Back=("tied", {"anchor": (180, 36), "hairline": 56, "vol": 0.6}), Base=("under", {}),   # m5: TypeSafe m4 smoother_top
                 attach=[("Tail", "tail", {"anchor": (180, 36), "len": 0.22, "lift": 0.015, "splay": 0.045, "tie": "bow",
                                            "bow_size": 0.050})],
                 colour={"tie": (78, 64, 168)}),
    "bun": dict(Front=("sweep", {"dir": -1, "len": -4}), Top=("slick", {}), SideL=("long", {"len": 0.04, "count": 1}),
                SideR=("long", {"len": 0.04, "count": 1}), Back=("tied", {"anchor": (180, 42)}), Base=("under", {}),
                attach=[("Bun", "bun", {"anchor": (180, 42), "r": 0.042}), ("Ahoge", "ahoge", {})]),
}
REGIONS = ("Front", "Top", "SideL", "SideR", "Back", "Base")


def recipe_spec(sc, name):
    """{piece: (clumps, ties)} for a recipe name (RECIPES) or a recipe dict."""
    R = RECIPES[name] if isinstance(name, str) else name
    spec = {}
    for reg in REGIONS:
        var, P = R.get(reg, ("none", {}))
        cl = REGION_VARIANTS[reg][var](sc, P)
        if cl:
            spec[reg] = (cl, [])
    for piece, kind, P in R.get("attach", []):
        spec[piece] = ATTACH[kind](sc, P)
    return spec




SEC_SRGB = None          # m1: two-tone - secondary colour (None = same as the base; MHS3 creator: 2 colours)
SEC_MODE = "tips"        # m1: where the secondary goes: "tips" (gradient to the ends), "strands" (SEC_SHARE of clumps), "inner" (Base region)
SEC_START = 0.65         # m1: tips mode - share along each clump where the gradient starts
SEC_SHARE = 0.0          # m1: strands mode - share of clumps in the secondary colour
TIE_SRGB = (150, 40, 36) # m1: hair-tie colour (recipes may override: "tie_srgb")
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
    if SEC_SRGB is not None:
        # m1: two-tone - base -> secondary by the hair_sec attribute (tips gradient / chosen strands / inner layer)
        sec = tuple(min(1.0, c * LIGHTNESS) for c in _lin(SEC_SRGB)[:3]) + (1.0,)
        asec = nt.nodes.new("ShaderNodeAttribute"); asec.attribute_name = "hair_sec"
        mixc = nt.nodes.new("ShaderNodeMix"); mixc.data_type = "RGBA"
        mixc.inputs[6].default_value = base; mixc.inputs[7].default_value = sec
        nt.links.new(asec.outputs["Fac"], mixc.inputs[0])
        nt.links.new(mixc.outputs[2], g.inputs["skin_color"])
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


def _sec_value(piece, flag, t):
    if SEC_MODE == "strands":
        return flag
    if SEC_MODE == "inner":
        return 1.0 if piece == "Base" else 0.0
    return min(1.0, max(0.0, (t - SEC_START) / max(1e-6, 1.0 - SEC_START)))


def _mesh_from(name, clumps_rings, col, off_x, mats, streak, shades=None, sec=None):
    verts, faces, uvs, attr_s, attr_l, attr_h, attr_c = [], [], [], [], [], [], []
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
                attr_s.append(streak[ci]); attr_l.append(len(ring) > 1 and abs(math.sin(2 * math.pi * k / RING)) < 0.2); attr_h.append(hk)
                attr_c.append(sec(ci, t) if sec else 0.0)   # k14: not the tip point (dark tips)
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
    for nm, val in (("hair_streak", attr_s), ("hair_line", attr_l), ("hair_shade", attr_h), ("hair_sec", attr_c)):
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


def _tie_mesh(name, ties, col, off_x, mat):
    """Hair ties (torus rings) for tails / braids / buns - own object so the creator can recolour or hide them."""
    verts, faces = [], []
    NU, NV = 16, 6
    for t in ties:
        u, v = _frame(t["axis"]); b0 = len(verts)
        for i in range(NU):
            a = 2 * math.pi * i / NU
            d = u * math.cos(a) + v * math.sin(a)
            for j in range(NV):
                bb = 2 * math.pi * j / NV
                verts.append(tuple(t["center"] + d * (t["R"] + t["r"] * math.cos(bb)) + np.asarray(t["axis"]) / np.linalg.norm(t["axis"]) * t["r"] * math.sin(bb)))
        for i in range(NU):
            for j in range(NV):
                a_ = b0 + i * NV + j; b_ = b0 + ((i + 1) % NU) * NV + j
                c_ = b0 + ((i + 1) % NU) * NV + (j + 1) % NV; d_ = b0 + i * NV + (j + 1) % NV
                faces.append((a_, b_, c_, d_))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); o.location.x = off_x
    col.objects.link(o)
    return o


def _tie_material(style):
    name = "MAT_HairTie_" + style
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    grp = bpy.data.node_groups.get("NG_ToonSkin_NewHead_Hair") or bpy.data.node_groups.get("NG_ToonSkin_NewHead")
    g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = grp
    g.inputs["skin_color"].default_value = _lin(TIE_SRGB)
    if "blush_strength" in g.inputs:
        g.inputs["blush_strength"].default_value = 0.0
    nt.links.new(g.outputs["Shader"], out.inputs["Surface"])
    return m


def build_hair(style="leo", tag="n56", off_x=2.4, recipe=None):
    """m1: build a recipe (RECIPES name, or a recipe dict via `recipe`) into one object per region / attachment."""
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
    R = recipe if recipe is not None else RECIPES.get(style, {})
    global BASE_SRGB, TIE_SRGB, SEC_SRGB
    for k_, g_ in (("base", "BASE_SRGB"), ("tie", "TIE_SRGB"), ("sec", "SEC_SRGB")):      # m2: per-recipe colours
        if k_ in R.get("colour", {}):
            globals()[g_] = R["colour"][k_]
    spec = recipe_spec(sc, R if recipe is not None else style)
    hm = _material(style); cm = _cap_material(style); tm = _tie_material(style)
    om = bpy.data.materials.get("MAT_Outline_NewHead_" + tag)
    rng = np.random.default_rng(11)
    made = []
    for piece, (clumps, ties) in spec.items():
        rings = [clump_rings(sc, c) for c in clumps]
        streak = [1.0 if (c.get("shade", 0.0) >= 0 and rng.random() < HL_SHARE) else 0.0 for c in clumps]
        sec_flag = [1.0 if rng.random() < SEC_SHARE else 0.0 for c in clumps]
        o = _mesh_from("Hair_%s_%s" % (piece, style), rings, col, off_x, [hm], streak, [c.get("shade", 0.0) for c in clumps],
                       sec=(lambda ci, t, _p=piece, _f=sec_flag: _sec_value(_p, _f[ci], t)))
        o["socket"] = "SOC-Hair" + piece
        o["hair_region"] = piece
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
        bows = [b for t in ties if "bow" in t for b in t["bow"]]
        ties = [t for t in ties if "bow" not in t]
        if bows:
            br = [clump_rings(sc, c) for c in bows]
            bo = _mesh_from("Hair_%sBow_%s" % (piece, style), br, col, off_x, [tm], [0.0] * len(bows), [c.get("shade", 0.0) for c in bows])
            bo["socket"] = "SOC-Hair" + piece; bo["hair_region"] = piece + "Bow"
            _radial_normals(bo)
            if om:
                _outline(bo, om)
            bo.visible_shadow = False
            made.append(bo)
        if ties:
            to = _tie_mesh("Hair_%sTie_%s" % (piece, style), ties, col, off_x, tm)
            to["socket"] = "SOC-Hair" + piece; to["hair_region"] = piece + "Tie"
            if om:
                _outline(to, om)
            to.visible_shadow = False
            made.append(to)
    cap = _cap(sc, head, col, off_x, style, cm); cap.visible_shadow = False
    made.append(cap)
    if HAIR_CAST:
        _hair_cast(head, [o for o in made if o.get("hair_region") in ("Front", "Top", "SideL", "SideR")])
    return col, made


HAIR_CAST = 1                      # q6: the fringe casts a hard toon shadow on the forehead (MHS3; TypeSafe q6 first fix)
HAIR_CAST_LIGHT = (-0.504, -0.646, 0.574)   # towards the KeySun (scene light), so the band agrees with the face's terminator
HAIR_CAST_REACH = 0.030            # q7: m - only hair this close casts (a band under the fringe edge, not a long shadow)
HAIR_CAST_ZMIN = 1.628             # q7: no cast below the brows (eyes stay clean)
HAIR_CAST_SOFT = 0.5               # 0..1 - share of the vertex ring that must be in shadow before the vertex goes dark


def _hair_cast(head, pieces):
    """q6: per head vertex, is the path to the key light blocked by the hair? -> point attribute "hair_cast" (1 lit,
    0 shadowed), multiplied into the head material's Shadow Mask. Neighbour-averaged once so the band edge follows
    the clump tips instead of single vertices."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    vs, ps = [], []
    for o in pieces:
        e = o.evaluated_get(dg); me = e.to_mesh(); M = o.matrix_world
        b = len(vs)
        vs += [tuple(M @ v.co) for v in me.vertices]
        ps += [tuple(b + i for i in p.vertices) for p in me.polygons]
        e.to_mesh_clear()
    if not ps:
        return
    tree = BVHTree.FromPolygons(vs, ps)
    me = head.data; M = head.matrix_world
    L = Vector(HAIR_CAST_LIGHT).normalized()
    lit = np.ones(len(me.vertices))
    for v in me.vertices:
        p = M @ v.co
        if (v.co.z < HAIR_CAST_ZMIN) or (v.normal.y > 0.3):     # q7: forehead / temples only (q6 reached the eyes)
            continue
        hit = tree.ray_cast(p + L * 0.0008, L, HAIR_CAST_REACH)
        if hit[0] is not None:
            lit[v.index] = 0.0
    # one neighbour average, then a soft threshold
    nb = [[] for _ in me.vertices]
    for e_ in me.edges:
        a, b = e_.vertices; nb[a].append(b); nb[b].append(a)
    avg = np.array([(lit[i] + sum(lit[j] for j in nb[i])) / (1 + len(nb[i])) for i in range(len(lit))])
    val = (avg > HAIR_CAST_SOFT).astype(np.float32)
    at = me.attributes.get("hair_cast") or me.attributes.new("hair_cast", "FLOAT", "POINT")
    at.data.foreach_set("value", val)
    for mat in me.materials:
        if not mat or not mat.use_nodes:
            continue
        nt = mat.node_tree
        if nt.nodes.get("HairCastMul"):
            continue
        for n in nt.nodes:
            if n.type == "GROUP" and "Shadow Mask" in n.inputs and n.inputs["Shadow Mask"].is_linked:
                src = n.inputs["Shadow Mask"].links[0].from_socket
                ah = nt.nodes.new("ShaderNodeAttribute"); ah.attribute_name = "hair_cast"
                mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.name = "HairCastMul"
                nt.links.new(src, mul.inputs[0]); nt.links.new(ah.outputs["Fac"], mul.inputs[1])
                nt.links.new(mul.outputs[0], n.inputs["Shadow Mask"])
                break
    print("hair cast: %d of %d head verts shadowed" % (int((val < 0.5).sum()), len(val)))
