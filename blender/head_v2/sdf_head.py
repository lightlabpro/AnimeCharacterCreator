"""v2 head form (2026-10-16): a signed-distance sculpt of the MHS3 male head, meshed with marching cubes.

Sammy: "those look really bad. please, use all the skills, typesafe, and the book knowledge, and start a new 3d model".
Why a new model: the n56 head drew eyes, teeth and tongue as flat strips on the skin and bent them per camera angle.
v2 builds real form so turned views come out of the geometry:
  - head mass lofted from horizontal sections whose widths are the dataset medians (knowledge/head-targets-dataset.json,
    18 anime models) and whose depths follow the dataset's profile offsets behind the nose tip;
  - the face front is curved, not a flat plate: at the outer eye corner the surface turns ~45 degrees (Loomis' side
    plane starts at the outer eye corner; Graphic Novel p?? "eyes wrap around the head", TypeSafe 0.97), so an eye
    drawn on it foreshortens into the short profile wedge by itself;
  - a real nose (bridge, tip, alae), brow ridge, shallow eye recess, cheekbones, lips, chin, a jaw line cut by a plane
    from the jaw angle to the chin and a neck set back under the skull (neck width ~0.39 head width, skill notes).
Face measurements in D = pupil line to chin (Leo render, visual_judge_log p-series): eye width 0.33 D, pupil distance
0.72 D, nose bottom 0.49 D, mouth 0.64 D below the pupils and 0.49 D wide, chin flat ~0.37 D.

Run with the system python (numpy, scipy, scikit-image): python3 sdf_head.py OUT.npz [--vox 0.0012]
Coordinates: metres, z up, -y is the face front, x = character's left. H = head height (skull top to chin).
"""
import json
import os
import sys

import numpy as np
from scipy.interpolate import PchipInterpolator

H = 0.22
ZT = 1.685                       # skull top
P = {}                           # every knob, written next to the mesh

def knob(name, value):
    P.setdefault(name, value)
    return P[name]

# ---- head mass: sections (h = 0 skull top .. 1 chin, fractions of H) -------------------------------------------
# W half width, F front depth, B back depth (from y = 0), NF / NB superellipse exponents of the front / back half.
SECT = knob("SECT", [   # q30: cranium +0.025-0.03 H half-width, forehead top back 0.02, crown fuller (5 dataset heads, clay silhouette medians); q28: back depth below the ears 0.27 -> 0.12-0.25 (the lower skull flared past the neck like a skirt); top shortened front-to-back (depth at 0.1 H 0.65 -> ~0.59, dataset 0.55-0.58), lower back fuller (depth at 0.5 H 0.72 -> ~0.82, dataset 0.81-0.97)
    # h     W      F      B      NF    NB
    [0.00,  0.000, 0.000, 0.000, 2.2, 2.2],
    [0.01,  0.0980, 0.0996, 0.1258, 2.2, 2.2],
    [0.02,  0.1386, 0.1387, 0.1739, 2.2, 2.2],
    [0.05,  0.2220, 0.1780, 0.2450, 2.2, 2.2],
    [0.10,  0.2915, 0.2470, 0.3270, 2.25, 2.2],
    [0.15,  0.3345, 0.3110, 0.3850, 2.3, 2.2],
    [0.20,  0.3605, 0.3460, 0.4120, 2.35, 2.25],
    [0.25,  0.3790, 0.3790, 0.4330, 2.4, 2.25],
    [0.30,  0.3885, 0.3940, 0.4440, 2.4, 2.25],
    [0.35,  0.3915, 0.4050, 0.4480, 2.45, 2.25],    # q28: NF 2.6-3.0 -> 2.4-2.5 at the eyes (a boxy section drew a band across the face)
    [0.40,  0.3830, 0.4080, 0.4380, 2.5, 2.25],
    [0.45,  0.3770, 0.4020, 0.4300, 2.5, 2.25],
    [0.50,  0.3680, 0.3940, 0.4250, 2.45, 2.2],
    [0.55,  0.3580, 0.3930, 0.4100, 2.4, 2.2],
    [0.60,  0.3480, 0.3930, 0.3850, 2.3, 2.2],
    [0.65,  0.3400, 0.3900, 0.3500, 2.3, 2.2],
    [0.70,  0.3170, 0.3860, 0.3000, 2.3, 2.2],
    [0.75,  0.2980, 0.3820, 0.2620, 2.3, 2.2],
    [0.80,  0.2650, 0.376, 0.2180, 2.3, 2.2],
    [0.85,  0.2360, 0.364, 0.1920, 2.4, 2.2],      # q27 v6b: TypeSafe preferred this rounder chin over v5f's V (front) and over
    [0.90,  0.2000, 0.350, 0.1780, 2.6, 2.2],      #   v6c's dataset-median widths (square chin, "dented" 0.33 -> 0.50); sits just
    [0.95,  0.1760, 0.3300, 0.1720, 2.9, 2.2],      #   under the dataset p10 at 0.85-0.95 H - a deliberate MHS3-look deviation
    [1.00,  0.1120, 0.2950, 0.1700, 3.0, 2.2],
    [1.03,  0.0000, 0.000, 0.000, 2.4, 2.2],
])

# ---- face relief: one smooth height field R(x, h) (H units) pushed out along -y over the face front ----------------
# Profiles are (h, value) tables; cross-sections are smooth bells. Values from the books + Leo (see the module notes).
# Anime simplification (Sammy 2026-10-16: "you're deviating way far from it being an anime character"):
# small soft nose (a ridge and a tip, no alae), nearly flat lips, no sockets or cheekbones, smooth face plane.
NOSE = knob("NOSE", dict(
    height=[(0.52, 0.0), (0.60, 0.003), (0.635, 0.010), (0.660, 0.022), (0.680, 0.037), (0.693, 0.040),
            (0.706, 0.030), (0.717, 0.009), (0.727, 0.0)],                 # q28: the clay render showed a stick ridge; dataset noses are a small tip
    halfw=[(0.50, 0.036), (0.60, 0.036), (0.66, 0.040), (0.69, 0.046), (0.727, 0.042)],
    ala=(0.030, 0.703, 0.020, 0.018, 0.0)))
BROW = knob("BROW", dict(h=0.370, rh=0.050, halfw=0.26, A=0.0, glabella=0.0))   # q28: was a ridge band across the face
SOCKET = knob("SOCKET", dict(x=0.190, h=0.447, rx=0.100, rh=0.060, A=0.0))   # q28: was a trough across the face at eye level
CHEEK = knob("CHEEK", dict(x=0.240, h=0.590, rx=0.125, rh=0.090, A=0.0))
MUZZLE = knob("MUZZLE", dict(h=0.790, rx=0.185, rh=0.095, A=0.004))
LIPS = knob("LIPS", dict(line=0.800, up_h=0.783, up_rh=0.020, up_w=0.130, up_A=0.0022, bow=0.0,
                         lo_h=0.822, lo_rh=0.020, lo_w=0.105, lo_A=0.0028, groove_A=-0.0008, groove_rh=0.005))
CHIN = knob("CHIN", dict(h=0.94, rx=0.11, rh=0.05, A=0.008, labial_h=0.870, labial_A=0.0))
JAW = knob("JAW", dict(gonion=(0.050, 0.720), chin=(-0.290, 1.000), k=0.100, back_h=0.88, back_slope=0.20))   # q30: the lower back now tapers in SECT; the trim only near chin height (ledge at the nape)   # q28: underside behind the jaw slopes down into the neck (a flat cut left a shelf)   # q27: was (0.075, 0.80) - a long low "boat" jaw in 3/4 and side; MHS3 jaw rises steeply to the ear   # (y, h) points of the jaw line
NECK = knob("NECK", dict(c=(0.0, 0.085), rx=0.128, ry=0.125, h0=0.62, h1=1.40, k=0.130))   # q30: neck front was AHEAD of the head centre (Sammy: malformed side view); dataset necks sit back under the skull   # q27: slimmer, under the jaw; v6e: forward + softer join (v6d notch at the jaw/neck, TypeSafe dented 0.57)


def to_h(z):
    return (ZT - z) / H


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def ellipsoid(p, c, r):
    q = (p - c) / r
    k0 = np.linalg.norm(q, axis=-1)
    k1 = np.linalg.norm(q / r, axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def capsule_cone(p, a, b, ra, rb):
    ba = b - a
    t = np.clip(((p - a) @ ba) / (ba @ ba), 0, 1)
    d = np.linalg.norm(p - (a + t[..., None] * ba), axis=-1)
    return d - (ra + (rb - ra) * t)


LOFT_SMOOTH = knob("LOFT_SMOOTH", 0.03)   # q28: Gaussian sigma (H) along h over the section table


class _Smooth:
    """q28 (clay renders vs 5 dataset heads): Pchip through the 0.05 H sections has curvature kinks at every row, which
    showed as horizontal ripples over the skull and forehead. Resample finely, Gaussian-smooth along h, interpolate."""
    def __init__(self, hs, vals, sigma):
        self.x = np.linspace(hs[0], hs[-1], 1201)
        y = PchipInterpolator(hs, vals)(self.x)
        if sigma > 0:
            st = self.x[1] - self.x[0]; r = int(4 * sigma / st)
            k = np.exp(-0.5 * (np.arange(-r, r + 1) * st / sigma) ** 2); k /= k.sum()
            yp = np.concatenate([np.full(r, y[0]), y, np.full(r, y[-1])])
            ys = np.convolve(yp, k, mode="valid")
            # keep the pole rows (skull top / chin closure) exact: blend in the smoothing away from the ends
            w = np.clip(np.minimum(self.x - hs[0], hs[-1] - self.x) / (2 * sigma), 0, 1)
            y = w * ys + (1 - w) * y
        self.y = y

    def __call__(self, h):
        return np.interp(h, self.x, self.y)


_CACHE = {}


def _interp():
    key = (json.dumps(SECT), LOFT_SMOOTH)
    if key not in _CACHE:
        S = np.array(SECT)
        _CACHE.clear()
        _CACHE[key] = (S[:, 0], [_Smooth(S[:, 0], S[:, i], LOFT_SMOOTH) for i in range(1, 6)])
    return _CACHE[key]


def front_y(x, h):
    hs, (fW, fF, fB, fNF, fNB) = _interp()
    W, F, n = float(fW(h)), float(fF(h)), float(fNF(h))
    u = min(abs(x) / W, 0.999)
    return -F * (1 - u ** n) ** (1.0 / n)


BACK_TAPER = knob("BACK_TAPER", ([0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0], [1.0, 0.988, 0.956, 0.909, 0.852, 0.79, 0.728, 0.671, 0.624, 0.592, 0.58, 0.58]))   # smoothstep 1 -> 0.58 over h 0.45-0.95 (a linear ramp creased at its start)


def loft(p):
    hs, (fW, fF, fB, fNF, fNB) = _interp()
    x, y, h = p[..., 0], p[..., 1], p[..., 2]
    hc = np.clip(h, hs[0], hs[-1])
    W = np.maximum(fW(hc), 1e-4); F = np.maximum(fF(hc), 1e-4); B = np.maximum(fB(hc), 1e-4)
    # q30: below the occiput the back half narrows into the neck (dataset heads); the jaw keeps the full width in front
    kb = np.interp(hc, BACK_TAPER[0], BACK_TAPER[1])
    u = np.clip(y / np.maximum(B, 1e-4) * 1.6, 0, 1); u = u * u * (3 - 2 * u)
    W = np.where(y > 0, W * (1 - (1 - kb) * u), W)
    n = np.where(y < 0, fNF(hc), fNB(hc))
    D = np.where(y < 0, F, B)
    rn = (np.abs(x / W) ** n + np.abs(y / D) ** n) ** (1.0 / n)
    scale = np.minimum(W, D)
    d = (rn - 1.0) * scale
    out = (h < hs[0]) | (h > hs[-1])
    return np.where(out, np.maximum(d, 0.02) + np.abs(h - hc), d)


# Ear: between the eye tops and the nose bottom (AnimeOutline ears; Leo), about 1/4 of the face tall, set back of the
# middle of the head depth, flared out ~18 degrees and leaned back ~12 degrees. Rim (helix) kept, inside recessed.
EAR = knob("EAR", dict(c=(0.0, 0.060, 0.525), a=0.060, b=0.128, top_flare=0.35, t=0.026, flare=14.0, lean=14.0,   # q30: Sammy "the ears look bad" - smaller, closer to the head (dataset ears), eye-to-nose level
                       recess=0.014, k=0.016, x_in=0.012))


def ear_sdf(p, side):
    e = EAR
    hs, (fW, fF, fB, fNF, fNB) = _interp()
    W = float(fW(e["c"][2]))
    c = np.array([side * (W - e["x_in"]), e["c"][1], e["c"][2]])
    q = p - c
    q = q * np.array([side, 1, 1])                                # mirror to the +x side
    fl, ln = np.radians(e["flare"]), np.radians(e["lean"])
    # local axes: u along the head (y back), v down (h), w out (x)
    u = q[..., 1] * np.cos(fl) - q[..., 0] * np.sin(fl)
    w = q[..., 1] * np.sin(fl) + q[..., 0] * np.cos(fl)
    v = q[..., 2] * np.cos(ln) - u * np.sin(ln)
    u = u * np.cos(ln) + q[..., 2] * np.sin(ln)
    a = e["a"] * (1 + e["top_flare"] * np.clip(-v / e["b"], -1, 1))   # wider at the top (v < 0 is up)
    r2 = np.sqrt((u / a) ** 2 + (v / e["b"]) ** 2)
    outline = (r2 - 1.0) * np.minimum(a, e["b"])
    slab = np.abs(w - e["t"] * 0.5) - e["t"] * 0.5
    d = smax(outline, slab, 0.008)
    # gentle bowl on the outer face (the inner ear forms are painted, MHS3-style: a smooth shell reads cleaner than
    # cut detail at this mesh density)
    bowl = (np.sqrt(((u + 0.012) / (a * 0.70)) ** 2 + ((v + 0.010) / (e["b"] * 0.70)) ** 2) - 1.0)
    d = d + e["recess"] * np.clip(-bowl, 0, 1) ** 2 * np.clip(1 - np.abs(w - e["t"]) / 0.02, 0, 1)
    return d


def _tab(t, h):
    t = np.array(t)
    return np.interp(h, t[:, 0], t[:, 1], left=t[0, 1], right=t[-1, 1])


def bell(u):
    return np.clip(1.0 - u * u, 0, None) ** 2


def relief(x, h):
    ax = np.abs(x)
    nh = _tab(NOSE["height"], h); nw = _tab(NOSE["halfw"], h)
    R = nh * bell(x / nw)
    axl, ahl, rx, rh, A = NOSE["ala"]
    R = np.maximum(R, A * bell(np.hypot((ax - axl) / rx, (h - ahl) / rh)))
    b = BROW
    R = R + b["A"] * bell((h - b["h"]) / b["rh"]) * bell(x / b["halfw"]) ** 0.5 \
          - b["glabella"] * bell(x / 0.06) * bell((h - b["h"] - 0.02) / 0.05)
    s_ = SOCKET
    R = R + s_["A"] * bell(np.hypot((ax - s_["x"]) / s_["rx"], (h - s_["h"]) / s_["rh"]))
    c = CHEEK
    R = R + c["A"] * bell(np.hypot((ax - c["x"]) / c["rx"], (h - c["h"]) / c["rh"]))
    m = MUZZLE
    R = R + m["A"] * bell(np.hypot(x / m["rx"], (h - m["h"]) / m["rh"]))
    L = LIPS
    up_c = L["up_h"] + L["bow"] * bell(x / 0.03)          # cupid's bow: the centre of the upper lip edge dips
    R = R + L["up_A"] * bell((h - up_c) / L["up_rh"]) * bell(x / L["up_w"]) ** 0.7
    R = R + L["lo_A"] * bell((h - L["lo_h"]) / L["lo_rh"]) * bell(x / L["lo_w"]) ** 0.7
    R = R + L["groove_A"] * bell((h - L["line"]) / L["groove_rh"]) * bell(x / (L["up_w"] * 1.05))
    ch = CHIN
    R = R + ch["A"] * bell(np.hypot(x / ch["rx"], (h - ch["h"]) / ch["rh"])) \
          + ch["labial_A"] * bell((h - ch["labial_h"]) / 0.02) * bell(x / 0.09)
    return R


# q31: hybrid head (Sammy: "you can even use the reference as a base model and rework it so it looks like mhs3").
# BASE = a reworked dataset head SDF grid (head_v3/base_head.py: CC BY "Autumn Girl" by Aryzus, re-proportioned to the
# dataset medians, eye sockets filled, smoothed). The skull above the brow stays our measured loft (dataset medians,
# smooth); face, ears, jaw and neck come from the base, blended across BASE_BLEND (which also hides the source's
# skull-shell seam). BASE None = the old all-procedural head.
_BASE_DEF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "head_v3", "base_grid_d60.npz")
BASE = knob("BASE", os.environ.get("HEAD_BASE", _BASE_DEF if os.path.exists(_BASE_DEF) else "") or None)   # HEAD_BASE= (empty) -> procedural
if BASE:                                          # the base's own ears (measured on the reworked mesh): painted ear pieces follow
    EAR = P["EAR"] = dict(EAR, c=(0.0, -0.060, 0.500), a=0.050, b=0.090)
BASE_BLEND = knob("BASE_BLEND", dict(face_y=-0.05, face_dy=0.10, h0=0.28, h1=0.44, chin_h=0.97, side_x=0.30,
                                      ear_box=((0.33, 0.62), (-0.17, 0.05), (0.40, 0.63)), ear_seat_mode=False,
                                      # q31 h8/h9: ear moved down x1.3 and re-seated (face gate: eyelid -> nose bottom) drew a
                                      # jagged outline in the ear/cheek crease; TypeSafe A/B preferred the h6 ear in all views
                                      ear_side=(0.394, 0.344), ear_seat=0.016, ear_cut=0.006, ear_k=0.03, ear_r=(0.085, 0.135),
                                      ear_move=((-0.060, 0.500), (-0.060, 0.565), 1.30),
                                      front_scale=0.94,
                                      eye_c=(0.18, 0.47), eye_r=(0.21, 0.15),
                                      jaw_narrow=(0.58, 0.78, 0.90), nose=(0.53, 0.75, 0.09, 0.0)))
# jaw_narrow: x scale 1 -> 0.90 over h 0.58-0.78 (Leo 0.97 D wide at the mouth, h5 1.12 D; TypeSafe A/B h6 > h5).
# nose: h0, h1, half-width, share of our small nose (q31 h7: 0.5 lost the TypeSafe A/B to 0).


def _base_interp():
    if "base" not in _CACHE:
        from scipy.interpolate import RegularGridInterpolator
        g = np.load(BASE)
        _CACHE["base"] = RegularGridInterpolator((g["xs"], g["ys"], g["hs"]), g["D"].astype(np.float32),
                                                 bounds_error=False, fill_value=0.2)
    return _CACHE["base"]


def _sstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def _box(v, lo, hi, soft):
    return _sstep((v - lo) / soft) * (1 - _sstep((v - hi) / soft))


def _our_side(h):
    """half-width of our head (no ears) along the ear line y = ear target y, by bisection, cached on an h table."""
    if "side" not in _CACHE:
        ty = BASE_BLEND.get("ear_move", ((0, 0), (0, -0.06), 1))[1][0]
        hh = np.linspace(0.30, 0.85, 56)
        lo, hi = np.full_like(hh, 0.15), np.full_like(hh, 0.65)
        for _ in range(30):
            mid = (lo + hi) / 2
            dm = sdf_proc(np.stack([mid, np.full_like(hh, ty), hh], -1), ears=False)
            lo, hi = np.where(dm < 0, mid, lo), np.where(dm < 0, hi, mid)
        _CACHE["side"] = (hh, (lo + hi) / 2)
    hh, w = _CACHE["side"]
    return np.interp(h, hh, w)


def sdf_hybrid(p):
    """q31 v2: the base head (reworked dataset mesh) gives only the face front and the ears. Our measured head gives
    skull, back of the head, jaw sides and neck (clay: the base's back was cut flat, 0.08 H short of the dataset
    median), and fills the base's eye sockets (eyes are painted pieces: the face must be closed there)."""
    b = BASE_BLEND
    h0j, h1j, sj = b.get("jaw_narrow", (0.6, 0.8, 1.0))
    sx = 1 - (1 - sj) * _sstep((p[..., 2] - h0j) / (h1j - h0j))
    p = np.stack([p[..., 0] / sx, p[..., 1], p[..., 2]], -1)
    x, y, h = p[..., 0], p[..., 1], p[..., 2]
    q = p.copy()
    q[..., 1] = np.where(y < 0, y / b["front_scale"], y)            # face less forward (a flatter MHS3 front)
    db = _base_interp()(q.reshape(-1, 3)).reshape(p.shape[:-1]) * np.where(y < 0, b["front_scale"], 1.0)
    dp = sdf_proc(p, ears=False)
    face = _sstep((b["face_y"] - y) / b["face_dy"]) * _sstep((h - b["h0"]) / (b["h1"] - b["h0"])) \
        * (1 - _sstep((h - b["chin_h"]) / 0.09)) * (1 - _sstep((np.abs(x) - b["side_x"]) / 0.08))
    ex, eh = b["eye_c"]; rx, rh = b["eye_r"]
    m = (1 - _sstep(np.hypot((np.abs(x) - ex) / rx, (h - eh) / rh) - 0.5)) * _sstep(-y / 0.1)
    face = face * (1 - m)                                            # sockets closed with our smooth front
    n0, n1, nw, nk = b.get("nose", (0.5, 0.75, 0.1, 0.0))            # q31 TypeSafe nose_mouth: the base nose is long/sharp
    face = face * (1 - nk * _box(h, n0, n1, 0.04) * (1 - _sstep(np.abs(x) / nw)))
    d = dp * (1 - face) + db * face
    (x0, x1), (y0, y1), (h0, h1) = b["ear_box"]
    ear = _box(np.abs(x), x0, x1, 0.03) * _box(y, y0, y1, 0.03) * _box(h, h0, h1, 0.03)
    if not b.get("ear_seat_mode"):                                   # h6: the base ear with the base side around it
        return smin(d, db + (1 - ear) * 0.2, 0.012) * sx
    # the base ear alone (the base's head side cut away: x_side), scaled about its centre, moved down and re-seated on
    # our head side (moving the whole base side with it left a plate with a flat top - clay h8a)
    (sy, sh), (ty, th), es = b["ear_move"]
    hsrc = sh + (h - th) / es
    xs0, xs1 = b["ear_side"]
    x_side = xs0 + (xs1 - xs0) * np.clip((hsrc - 0.40) / 0.20, 0, 1.2)
    ax = np.abs(x) - (_our_side(h) - x_side) - b["ear_seat"]
    qe = np.stack([ax, sy + (y - ty) / es, hsrc], -1)
    de = _base_interp()(qe.reshape(-1, 3)).reshape(p.shape[:-1])
    de = smax(de, x_side + b["ear_cut"] - ax, 0.006) * es
    ry, rh = b["ear_r"]                                              # nothing of the base but the ear itself
    de = np.maximum(de, (np.hypot((y - ty) / ry, (h - th) / rh) - 1.0) * min(ry, rh))
    return smin(d, de + (1 - ear) * 0.2, b["ear_k"]) * sx


def sdf(p):
    """p: (..., 3) in H units with the third component h (down)."""
    if BASE:
        return sdf_hybrid(p)
    return sdf_proc(p)


def sdf_proc(p, ears=True):
    d = loft(p)
    # jaw line: keep the half-space above the plane through the jaw angle and the chin bottom (side view)
    (yg, hg), (yc, hc) = JAW["gonion"], JAW["chin"]
    nrm = np.array([hc - hg, -(yc - yg)])            # normal in (y, h), pointing below/behind the jaw line
    nrm = nrm / np.linalg.norm(nrm)
    if nrm[1] < 0:
        nrm = -nrm
    plane = (p[..., 1] - yg) * nrm[0] + (p[..., 2] - hg) * nrm[1]
    # q28: the infinite plane also sliced the back of the skull once the jaw corner was raised (clay side view: a
    # diagonal from behind the ear to the chin). Behind the jaw corner the head is only trimmed at JAW["back_h"].
    back = p[..., 2] - (JAW.get("back_h", 0.86) + JAW.get("back_slope", 0.0) * np.maximum(p[..., 1] - yg, 0))
    t = np.clip((p[..., 1] - yg + 0.04) / 0.20, 0, 1); t = t * t * (3 - 2 * t)
    plane = plane * (1 - t) + back * t
    d = smax(d, plane, JAW["k"])
    # face relief, faded out toward the sides of the head
    hs, (fW, fF, fB, fNF, fNB) = _interp()
    F = np.maximum(fF(np.clip(p[..., 2], hs[0], hs[-1])), 1e-3)
    w = np.clip((-p[..., 1] / F - 0.25) / 0.35, 0, 1)
    w = w * w * (3 - 2 * w)
    d = d - relief(p[..., 0], p[..., 2]) * w
    # neck: elliptic column set back under the skull, smooth-joined (throat angle) and cut flat at the bottom
    q = np.stack([p[..., 0] / NECK["rx"], (p[..., 1] - NECK["c"][1]) / NECK["ry"]], -1)
    neck = (np.linalg.norm(q, axis=-1) - 1.0) * min(NECK["rx"], NECK["ry"])
    neck = np.maximum(neck, np.maximum(NECK["h0"] - p[..., 2], p[..., 2] - NECK["h1"]))
    d = smin(d, neck, NECK["k"])
    for side in (1, -1) if ears else ():
        d = smin(d, ear_sdf(p, side), EAR["k"])
    return d


def build(vox=0.0012):
    from skimage.measure import marching_cubes
    lo = np.array([-0.45, -0.62, -0.06]); hi = np.array([0.45, 0.55, 1.56])      # H units, h down
    st = vox / H
    xs, ys, hs = (np.arange(lo[i], hi[i] + st, st) for i in range(3))
    vol = np.empty((len(xs), len(ys), len(hs)), np.float32)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    for k, h in enumerate(hs):
        p = np.stack([X, Y, np.full_like(X, h)], -1)
        vol[:, :, k] = sdf(p)
    v, f, _, _ = marching_cubes(vol, 0.0, spacing=(st, st, st))
    v = v + lo
    P_m = np.stack([v[:, 0] * H, v[:, 1] * H, ZT - v[:, 2] * H], 1)
    f = f[:, ::-1]                                    # h runs down: flip the winding back to outward normals
    return P_m.astype(np.float32), f.astype(np.int32)


if __name__ == "__main__":
    out = sys.argv[1]
    vox = float(sys.argv[sys.argv.index("--vox") + 1]) if "--vox" in sys.argv else 0.0012
    if "--base" in sys.argv:
        P["BASE"] = BASE = sys.argv[sys.argv.index("--base") + 1]
    if "--knobs" in sys.argv:
        P.update(json.load(open(sys.argv[sys.argv.index("--knobs") + 1])))
    v, f = build(vox)
    np.savez_compressed(out, v=v, f=f, knobs=json.dumps(P))
    print("verts", len(v), "faces", len(f), "z", v[:, 2].min(), v[:, 2].max())
