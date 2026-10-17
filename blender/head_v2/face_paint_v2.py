"""v2 face pieces: eyes, lashes, crease, brows (and a temporary mouth line) as thin meshes that lie ON the v2 head.

Each piece is drawn in 2D in Leo's proportions (front view, H units; D = pupil line to chin = 0.50 H: eye width
0.33 D, pupil distance 0.72 D), triangulated finely, then every vertex is projected along +y onto the exact SDF surface
(sdf_head.sdf) and lifted along the surface normal by a small per-layer offset. Because the pieces follow the curved
face, a turned view foreshortens them the way the books draw it (far eye shorter behind the bridge, profile eye a short
wedge set back from the profile line) - no per-angle keys.

Leo's eye (MHST3-Leo_Render_001, read at 4x): round almond ~0.57 tall:wide; thick dark-brown upper lash heaviest across
the top and outer corner; thin lower lid line on the outer 2/3; grey-white sclera with a grey band under the lid; large
iris cut by the lid (darker top band, dark rim, oval pupil); one white highlight on the same world side in both eyes;
thick brows angled down toward the inner end.

    python3 face_paint_v2.py OUT.npz
"""
import json
import sys

import numpy as np
import triangle
from shapely.geometry import Polygon, Point, LineString
from shapely import affinity
from shapely.ops import unary_union

import sdf_head as S

H = S.H
from mouth_v2_line import EYE_H, D, NB as _NB  # one face layout for every script
E = 0.33 * D             # eye width
CX = 0.36 * D            # eye centre |x|
COL = dict(sclera=(238, 240, 246), sclera_shade=(196, 200, 216), iris=(96, 168, 98), iris_top=(56, 118, 66),
           iris_rim=(40, 86, 48), pupil=(24, 52, 30), highlight=(255, 255, 255), lash=(58, 34, 26),
           lash_low=(128, 84, 66), crease=(186, 128, 106), brow=(104, 70, 44), mouth=(84, 44, 38),
           nose_shade=(196, 132, 106), lip_shade=(205, 146, 122), nose_hl=(250, 228, 210),
           ear_in=(214, 160, 146), ear_line=(166, 112, 100))
# q25: layers 0.05-0.1 mm apart (0.02-0.04 mm z-fought in EEVEE: mottled iris / sclera, specks in the nose shade)
LIFT = dict(sclera=0.00030, sclera_shade=0.00040, iris=0.00050, iris_top=0.00060, iris_rim=0.00068, pupil=0.00076,
            highlight=0.00090, lash=0.00100, lash_low=0.00090, crease=0.00035, brow=0.00045, mouth=0.00055,
            nose_shade=0.00045, lip_shade=0.00040, nose_hl=0.00050, ear_in=0.00035, ear_line=0.00045)

UPPER = [(0.0, 0.02), (0.10, 0.17), (0.30, 0.30), (0.50, 0.34), (0.70, 0.32), (0.88, 0.22), (1.0, 0.06)]
LOWER = [(1.0, 0.06), (0.90, -0.10), (0.70, -0.20), (0.50, -0.23), (0.30, -0.20), (0.12, -0.10), (0.0, 0.02)]


def smooth_curve(pts, n=40):
    """Catmull-Rom through the points."""
    P = np.array(pts, float)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n // (len(P) - 3) + 2)[:-1]:
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


def eye_to_xh(uw, side):
    uw = np.asarray(uw, float)
    x = side * (CX + (uw[..., 0] - 0.5) * E)
    h = EYE_H - uw[..., 1] * E
    return np.stack([x, h], -1)


def eye_shapes(side):
    up = smooth_curve(UPPER); lo = smooth_curve(LOWER)
    sclera = Polygon(np.vstack([up, lo[1:-1]]))
    sh = {}
    sh["sclera"] = sclera
    shade_edge = up - np.array([0, 0.11]) * np.array([[1, 1]])
    sh["sclera_shade"] = Polygon(np.vstack([up, shade_edge[::-1]])).buffer(0).intersection(sclera)
    # iris: on the world side the light comes from, the highlight; iris centre a touch toward the nose
    ic = (0.47, 0.03); irx, irz = 0.27, 0.33
    iris = affinity.scale(Point(ic).buffer(1.0, 64), irx, irz)
    sh["iris"] = iris.intersection(sclera)
    sh["iris_top"] = iris.intersection(Polygon([(-1, 0.13), (2, 0.13), (2, 1), (-1, 1)])).intersection(sclera)
    rim = iris.difference(affinity.scale(Point(ic).buffer(1.0, 64), irx * 0.86, irz * 0.88))
    sh["iris_rim"] = rim.intersection(sclera)
    sh["pupil"] = affinity.scale(Point((ic[0], ic[1] + 0.02)).buffer(1.0, 48), 0.085, 0.14).intersection(sclera)
    hx = ic[0] + side * 0.11                                  # same world side (+x) in both eyes
    hl = affinity.rotate(affinity.scale(Point((hx, ic[1] + 0.12)).buffer(1.0, 32), 0.075, 0.032), 20)
    hl2 = affinity.scale(Point((ic[0] - side * 0.10, ic[1] - 0.13)).buffer(1.0, 24), 0.032, 0.026)   # q25: small second catchlight
    sh["highlight"] = hl.union(hl2).intersection(sclera)
    # upper lash: thick along the top, thickest at the outer third, short wing past the outer corner
    t = 0.060 + 0.060 * np.clip((up[:, 0] - 0.1) / 0.65, 0, 1) * (1 - np.clip((up[:, 0] - 0.85) / 0.15, 0, 1) * 0.4)
    outer = up + np.stack([np.zeros_like(t), t], -1)
    wing = np.array([[1.10, 0.09]])
    sh["lash"] = Polygon(np.vstack([up, wing, outer[::-1]])).buffer(0)
    # lower lid line, outer two thirds, tapering
    lo_part = lo[lo[:, 0] > 0.30]
    tl = 0.022 * np.clip((lo_part[:, 0] - 0.30) / 0.4, 0.2, 1)
    sh["lash_low"] = Polygon(np.vstack([lo_part, (lo_part - np.stack([np.zeros_like(tl), tl], -1))[::-1]])).buffer(0)
    # crease (double eyelid) above the lash
    cr = up[(up[:, 0] > 0.08) & (up[:, 0] < 0.60)] + np.array([0, 0.15])   # q26: fold over the inner part only (Crilley p.15-ish rule)
    sh["crease"] = LineString(cr).buffer(0.008, cap_style=1)
    return sh


def brow_shape(side):
    # world (x, h) in H units: thick inner end low and close to the eye top, rising outward, tapering (Leo)
    top = [(0.044, 0.355), (0.111, 0.328), (0.200, 0.315), (0.289, 0.321), (0.353, 0.341)]
    bot = [(0.357, 0.349), (0.289, 0.343), (0.200, 0.347), (0.111, 0.365), (0.050, 0.391)]
    P = np.vstack([smooth_curve(top, 24), smooth_curve(bot, 24)])
    P[:, 0] *= side
    return Polygon(P).buffer(0)


def tri_poly(poly, max_area):
    polys = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
    V, F = [], []
    for pg in polys:
        if pg.is_empty or pg.area < 1e-9:
            continue
        ext = np.array(pg.exterior.coords)[:-1]
        segs = [(i, (i + 1) % len(ext)) for i in range(len(ext))]
        verts = list(ext); seg = list(segs); holes = []
        for ring in pg.interiors:
            r = np.array(ring.coords)[:-1]; o = len(verts)
            verts += list(r); seg += [(o + i, o + (i + 1) % len(r)) for i in range(len(r))]
            holes.append(np.array(Polygon(r).representative_point().coords[0]))
        A = dict(vertices=np.array(verts), segments=np.array(seg))
        if holes:
            A["holes"] = np.array(holes)
        T = triangle.triangulate(A, "pqa%g" % max_area)
        o = sum(len(v) for v in V)
        V.append(T["vertices"]); F.append(T["triangles"] + o)
    return np.vstack(V), np.vstack(F)


def project(xh, lift):
    """Project (x, h) along +y onto the SDF surface; lift along the normal (metres)."""
    x, h = xh[:, 0], xh[:, 1]
    y = np.full(len(x), -0.70)
    step = 0.004
    prev = S.sdf(np.stack([x, y, h], -1))
    lo = y.copy(); hi = y.copy(); found = np.zeros(len(x), bool)
    for _ in range(int(0.9 / step)):
        y2 = y + step
        d = S.sdf(np.stack([x, y2, h], -1))
        hit = (~found) & (d < 0) & (prev >= 0)
        lo[hit] = y[hit]; hi[hit] = y2[hit]; found |= hit
        y, prev = y2, d
        if found.all():
            break
    for _ in range(30):
        m = 0.5 * (lo + hi)
        d = S.sdf(np.stack([x, m, h], -1))
        out = d > 0
        lo = np.where(out, m, lo); hi = np.where(out, hi, m)
    p = np.stack([x, 0.5 * (lo + hi), h], -1)
    e = 1e-4
    g = np.stack([(S.sdf(p + np.array(v) * e) - S.sdf(p - np.array(v) * e)) for v in np.eye(3)], -1)
    g[:, 2] *= -1                                          # h runs down
    n = g / np.linalg.norm(g, axis=1, keepdims=True)
    P = np.stack([p[:, 0] * H, p[:, 1] * H, S.ZT - p[:, 2] * H], -1) + n * lift
    return P


def project_side(yh, side, lift):
    """Project (y, h) points along -x (from the character's side) onto the outermost SDF surface - the ear."""
    y, h = yh[:, 0], yh[:, 1]
    x = np.full(len(y), side * 0.60)
    step = -side * 0.003
    prev = S.sdf(np.stack([x, y, h], -1))
    lo = x.copy(); hi = x.copy(); found = np.zeros(len(y), bool)
    for _ in range(250):
        x2 = x + step
        d = S.sdf(np.stack([x2, y, h], -1))
        hit = (~found) & (d < 0) & (prev >= 0)
        lo[hit] = x[hit]; hi[hit] = x2[hit]; found |= hit
        x, prev = x2, d
        if found.all():
            break
    for _ in range(30):
        m = 0.5 * (lo + hi)
        d = S.sdf(np.stack([m, y, h], -1))
        out = d > 0
        lo = np.where(out, m, lo); hi = np.where(out, hi, m)
    p = np.stack([0.5 * (lo + hi), y, h], -1)
    e = 1e-4
    g = np.stack([(S.sdf(p + np.array(v) * e) - S.sdf(p - np.array(v) * e)) for v in np.eye(3)], -1)
    g[:, 2] *= -1
    n = g / np.linalg.norm(g, axis=1, keepdims=True)
    return np.stack([p[:, 0] * H, p[:, 1] * H, S.ZT - p[:, 2] * H], -1) + n * lift


def ear_shapes():
    """Painted inner ear (MHS3 / Leo: a mauve inner shadow and a rim line, AnimeOutline ears: rim, bump, opening),
    in side-view (y, h), on the SDF ear (EAR centre / size)."""
    e = S.EAR
    cy, ch = e["c"][1], e["c"][2]
    a, b = e["a"], e["b"]
    t = np.linspace(np.radians(200), np.radians(-60), 40)        # C-shaped rim line: front-top, over, down the back
    rim = np.stack([cy + 0.62 * a * np.cos(t) * 1.15, ch - 0.70 * b * np.sin(t)], -1)
    line = LineString(rim).buffer(0.0038, cap_style=1)
    inner = affinity.scale(Point((cy - 0.010, ch + 0.020)).buffer(1.0, 48), 0.30 * a, 0.30 * b)
    return line, inner


# ---- expression keys for the painted pieces (2D transforms, re-projected onto the face) ---------------------------
def _lids():
    up = smooth_curve(UPPER); lo = smooth_curve(LOWER)[::-1]          # both inner -> outer
    U = lambda u: np.interp(u, up[:, 0], up[:, 1])
    L = lambda u: np.interp(u, lo[:, 0], lo[:, 1])
    return U, L


EYE_KEYS = {
    # name: (new upper lid as f(U, L, u), new lower lid)            (eye-width units, w up)
    "PF-Blink": (lambda U, L, u: 0.62 * L + 0.38 * U - 0.05 * np.sin(np.pi * u),
                 lambda U, L, u: 0.62 * L + 0.38 * U - 0.05 * np.sin(np.pi * u)),
    "PF-Squint": (lambda U, L, u: U - 0.04, lambda U, L, u: L + 0.45 * (U - L)),
    "PF-EyeWide": (lambda U, L, u: U + 0.07, lambda U, L, u: L - 0.03),
    "PF-LidUpperDown": (lambda U, L, u: U - 0.35 * (U - L), lambda U, L, u: L),
    "PF-LidLowerUp": (lambda U, L, u: U, lambda U, L, u: L + 0.25 * (U - L)),
}


def eye_key_uw(name, uw, key):
    """Remap a piece's (u, w) for an eye key: lash / lower line / crease ride their lid, the rest is squeezed
    between the new lids (closed eye = the lash line, curved down: anime closed eye)."""
    U, L = _lids()
    fu, fl = EYE_KEYS[key]
    u = np.clip(uw[:, 0], 0, 1); w = uw[:, 1]
    u0, l0 = U(u), L(u)
    u1, l1 = fu(u0, l0, u), fl(u0, l0, u)
    out = uw.copy()
    if name == "lash":
        out[:, 1] = w + (u1 - u0)
    elif name == "lash_low":
        out[:, 1] = w + (l1 - l0)
    elif name == "crease":
        out[:, 1] = w + 0.55 * (u1 - u0)
    else:
        t = np.clip((w - l0) / np.maximum(u0 - l0, 1e-6), 0, 1)
        out[:, 1] = l1 + t * (u1 - l1)
    return out


BROW_KEYS = {   # world (x, h) offsets as f(t) where t = 0 inner end .. 1 outer end; h down is +
    "PF-BrowInnerUp": lambda t: (0.0, -0.030 * (1 - t) ** 1.5),
    "PF-BrowRaise": lambda t: (0.0, -0.024 + 0 * t),
    "PF-BrowLower": lambda t: (0.0, 0.012 + 0.006 * (1 - t)),
    "PF-BrowFurrow": lambda t: (-0.010 * (1 - t), 0.016 * (1 - t) ** 1.2),
    "PF-BrowSad": lambda t: (0.0, -0.026 * (1 - t) ** 1.5 + 0.008 * t),
    "PF-BrowOuterUp": lambda t: (0.0, -0.022 * t ** 1.5),
}
SIDED = ("PF-Blink", "PF-Squint", "PF-BrowInnerUp", "PF-BrowRaise", "PF-BrowLower", "PF-BrowFurrow")


def build():
    pieces = {}
    for side, tag in ((1, "L"), (-1, "R")):
        for name, poly in eye_shapes(side).items():
            if poly.is_empty:
                continue
            uv, f = tri_poly(poly, 0.0004)
            xh = eye_to_xh(uv, side)
            if side < 0:
                f = f[:, ::-1]
            keys = {}
            for kname in EYE_KEYS:
                P = project(eye_to_xh(eye_key_uw(name, uv, kname), side), LIFT[name])
                keys[kname] = P
                if kname in SIDED:
                    keys["%s_%s" % (kname, tag)] = P
            pieces["V2Eye_%s_%s" % (name, tag)] = (project(xh, LIFT[name]), f, COL[name], keys)
        poly = brow_shape(side)
        xy, f = tri_poly(poly, 0.00002)
        if side < 0:
            f = f[:, ::-1]
        t = np.clip((np.abs(xy[:, 0]) - 0.044) / (0.357 - 0.044), 0, 1)
        keys = {}
        for kname, fn in BROW_KEYS.items():
            d = np.array([fn(ti) for ti in t])
            xy2 = xy + np.stack([side * d[:, 0], d[:, 1]], -1)
            P = project(xy2, LIFT["brow"])
            keys[kname] = P
            if kname in SIDED:
                keys["%s_%s" % (kname, tag)] = P
        pieces["V2Brow_%s" % tag] = (project(xy, LIFT["brow"]), f, COL["brow"], keys)
    line, inner = ear_shapes()
    for side, tag in ((1, "L"), (-1, "R")):
        for nm, poly in (("ear_in", inner), ("ear_line", line)):
            yh, f = tri_poly(poly, 0.00002)
            if side > 0:
                f = f[:, ::-1]
            pieces["V2Ear_%s_%s" % (nm, tag)] = (project_side(yh, side, LIFT[nm]), f, COL[nm])
    # Leo's painted marks (MHS3 nose = a small darker shape under the tip; a short lower-lip shade; a light bridge
    # highlight on the lit side) - the toon light alone does not draw them
    nb = _NB                                                # nose bottom
    ns_ = Polygon(smooth_curve([(-0.040, nb - 0.004), (-0.012, nb - 0.016), (0.020, nb - 0.018), (0.042, nb - 0.006),
                                (0.030, nb + 0.004), (-0.030, nb + 0.004)], 30)).buffer(0)
    xy, f = tri_poly(ns_, 0.00002)
    pieces["V2NoseShade"] = (project(xy, LIFT["nose_shade"]), f, COL["nose_shade"])
    my = EYE_H + 0.64 * D
    ls = Polygon(smooth_curve([(-0.060, my + 0.045), (0.0, my + 0.040), (0.060, my + 0.045), (0.050, my + 0.058),
                               (0.0, my + 0.062), (-0.050, my + 0.058)], 30)).buffer(0)
    xy, f = tri_poly(ls, 0.00002)
    pieces["V2LipShade"] = (project(xy, LIFT["lip_shade"]), f, COL["lip_shade"])
    hl = Polygon(smooth_curve([(-0.012, 0.51), (-0.004, 0.505), (-0.006, 0.645), (-0.022, 0.665), (-0.020, 0.58)], 30)).buffer(0)
    xy, f = tri_poly(hl, 0.00002)
    pieces["V2NoseHL"] = (project(xy, LIFT["nose_hl"]), f, COL["nose_hl"])
    # mouth line (Leo: a thin dark-brown line, a touch heavier in the middle, ends fading), drawn just above the
    # geometry slit so it rides on the upper lip; it hides the slit's uneven rim when the mouth is closed
    import mouth_v2_line as ML
    xs = np.linspace(-1.03, 1.03, 64)   # q25: just past the slit corners (dark cavity wedges showed at the ends)
    # mouth-line fix (q24): ends kept >= ~0.0045 H thick (sub-pixel ends rendered as dots), lifted to 0.50 mm
    # q25: drawn-line shape - heavier in the middle third, tapering to rounded ends (was an even bar)
    def th(u):
        au = abs(u)
        corner = 0.0048 * np.exp(-((au - 0.97) / 0.045) ** 2)       # q25: small rounded corner accents (cover the
        return 0.0034 + 0.0042 * (1 - np.clip(au, 0, 1) ** 2) ** 1.5 + corner   # dark corner bridge faces at rest)
    top = [(u * ML.MW, ML.line(u * ML.MW) - 0.42 * th(u) - 0.0010) for u in xs]
    bot = [(u * ML.MW, ML.line(u * ML.MW) + 0.58 * th(u) - 0.0010) for u in xs[::-1]]
    xy, f = tri_poly(Polygon(top + bot).buffer(0), 0.000004)
    pieces["V2MouthLine"] = (project(xy, LIFT["mouth"]), f, COL["mouth"])
    return pieces


if __name__ == "__main__":
    pieces = build()
    out = {}
    for k, val in pieces.items():
        v, f, c = val[:3]
        out[k + "__v"] = v.astype(np.float32); out[k + "__f"] = f.astype(np.int32); out[k + "__c"] = np.array(c)
        for kn, P in (val[3] if len(val) > 3 else {}).items():
            out[k + "__k" + kn] = P.astype(np.float32)
    np.savez_compressed(sys.argv[1], **out)
    print(len(pieces), "pieces:", ", ".join(sorted(pieces)))
