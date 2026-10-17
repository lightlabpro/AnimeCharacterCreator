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
SECT = knob("SECT", [   # q28: back depth below the ears 0.27 -> 0.12-0.25 (the lower skull flared past the neck like a skirt); top shortened front-to-back (depth at 0.1 H 0.65 -> ~0.59, dataset 0.55-0.58), lower back fuller (depth at 0.5 H 0.72 -> ~0.82, dataset 0.81-0.97)
    # h     W      F      B      NF    NB
    [0.00,  0.000, 0.000, 0.000, 2.2, 2.2],
    [0.01,  0.0880, 0.1056, 0.1178, 2.2, 2.2],
    [0.02,  0.1236, 0.1487, 0.1659, 2.2, 2.2],
    [0.05,  0.1920, 0.2000, 0.2250, 2.2, 2.2],
    [0.10,  0.2615, 0.2720, 0.3150, 2.25, 2.2],
    [0.15,  0.3065, 0.3350, 0.3850, 2.3, 2.2],
    [0.20,  0.3345, 0.3620, 0.4200, 2.35, 2.25],
    [0.25,  0.3530, 0.395, 0.445, 2.4, 2.25],
    [0.30,  0.3625, 0.400, 0.450, 2.4, 2.25],
    [0.35,  0.3675, 0.405, 0.448, 2.45, 2.25],    # q28: NF 2.6-3.0 -> 2.4-2.5 at the eyes (a boxy section drew a band across the face)
    [0.40,  0.3670, 0.408, 0.438, 2.5, 2.25],
    [0.45,  0.3630, 0.4020, 0.4300, 2.5, 2.25],
    [0.50,  0.3570, 0.3940, 0.4250, 2.45, 2.2],
    [0.55,  0.3520, 0.3930, 0.4100, 2.4, 2.2],
    [0.60,  0.3480, 0.3930, 0.3850, 2.3, 2.2],
    [0.65,  0.3400, 0.3900, 0.3500, 2.3, 2.2],
    [0.70,  0.3170, 0.3860, 0.3000, 2.3, 2.2],
    [0.75,  0.2980, 0.3820, 0.2500, 2.3, 2.2],
    [0.80,  0.2650, 0.376, 0.1850, 2.3, 2.2],
    [0.85,  0.2360, 0.364, 0.1450, 2.4, 2.2],      # q27 v6b: TypeSafe preferred this rounder chin over v5f's V (front) and over
    [0.90,  0.2000, 0.350, 0.1250, 2.6, 2.2],      #   v6c's dataset-median widths (square chin, "dented" 0.33 -> 0.50); sits just
    [0.95,  0.1600, 0.330, 0.1200, 2.9, 2.2],      #   under the dataset p10 at 0.85-0.95 H - a deliberate MHS3-look deviation
    [1.00,  0.1000, 0.295, 0.1200, 3.0, 2.2],
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
JAW = knob("JAW", dict(gonion=(0.050, 0.720), chin=(-0.290, 1.000), k=0.060, back_h=0.74, back_slope=0.45))   # q28: underside behind the jaw slopes down into the neck (a flat cut left a shelf)   # q27: was (0.075, 0.80) - a long low "boat" jaw in 3/4 and side; MHS3 jaw rises steeply to the ear   # (y, h) points of the jaw line
NECK = knob("NECK", dict(c=(0.0, 0.070), rx=0.140, ry=0.185, h0=0.62, h1=1.40, k=0.100))   # q27: slimmer, under the jaw; v6e: forward + softer join (v6d notch at the jaw/neck, TypeSafe dented 0.57)


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


def loft(p):
    hs, (fW, fF, fB, fNF, fNB) = _interp()
    x, y, h = p[..., 0], p[..., 1], p[..., 2]
    hc = np.clip(h, hs[0], hs[-1])
    W = np.maximum(fW(hc), 1e-4); F = np.maximum(fF(hc), 1e-4); B = np.maximum(fB(hc), 1e-4)
    n = np.where(y < 0, fNF(hc), fNB(hc))
    D = np.where(y < 0, F, B)
    rn = (np.abs(x / W) ** n + np.abs(y / D) ** n) ** (1.0 / n)
    scale = np.minimum(W, D)
    d = (rn - 1.0) * scale
    out = (h < hs[0]) | (h > hs[-1])
    return np.where(out, np.maximum(d, 0.02) + np.abs(h - hc), d)


# Ear: between the eye tops and the nose bottom (AnimeOutline ears; Leo), about 1/4 of the face tall, set back of the
# middle of the head depth, flared out ~18 degrees and leaned back ~12 degrees. Rim (helix) kept, inside recessed.
EAR = knob("EAR", dict(c=(0.0, 0.070, 0.515), a=0.072, b=0.150, top_flare=0.30, t=0.030, flare=24.0, lean=12.0,   # q27: Leo ear top at the brow, bottom 0.38 D under the pupils, 0.56 D tall, clear of the head
                       recess=0.010, k=0.018, x_in=0.008))


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


def sdf(p):
    """p: (..., 3) in H units with the third component h (down)."""
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
    for side in (1, -1):
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
    if "--knobs" in sys.argv:
        P.update(json.load(open(sys.argv[sys.argv.index("--knobs") + 1])))
    v, f = build(vox)
    np.savez_compressed(out, v=v, f=f, knobs=json.dumps(P))
    print("verts", len(v), "faces", len(f), "z", v[:, 2].min(), v[:, 2].max())
