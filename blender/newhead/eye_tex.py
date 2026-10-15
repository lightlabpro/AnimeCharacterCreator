"""Textures for the animatable eye (r1): iris (moves with the iris mesh), eye white with the lid-shadow band, brow
strokes. Pure numpy; RGBA float arrays (rows bottom-up, Blender pixel order), sRGB 0..1. Colours sampled from the
MHS3 protagonist frame."""
import numpy as np

C_SCLERA = (230, 228, 227)      # q3: Leo face reference sample (was 199,197,188)
C_BAND = (198, 200, 208)        # q3: faint cool shade under the lid (was a heavy grey band)
C_IRIS_TOP = (39, 64, 39)       # q3: Leo dark top under the lid
C_IRIS = (120, 165, 112)        # q3: Leo mid green ~(145,187,139) with the top shade blended in
C_IRIS_LIGHT = (168, 214, 146)  # q3: lighter lower crescent
C_IRIS_LINE = (42, 72, 46)      # q3
C_PUPIL = (36, 58, 38)          # q3
C_HL = (250, 250, 248)
C_BROW = (122, 95, 71)
C_BROW_DARK = (92, 66, 45)
RING_W = 0.042        # r1: thicker iris arcs (MHS3 frame; q-series 0.022)
RIM_W = 0.075         # dark iris outline width (share of the radius)
PUPIL = (0.0, 0.26, 0.30, 0.44)       # q3: tall oval set high (Leo)      # centre u, v and radii, iris-local
LIGHT = (0.0, -0.62, 0.95, 0.45)      # light crescent ellipse
HL = (1.02, -0.10, 0.31, 0.13)        # q3: on the viewer-right (Leo: light from the image right); highlight (iris-local; u mirrored for the viewer-right eye)
EXT = 1.40            # texture / mesh extent around the iris (the highlight overlaps the white)
BAND = 0.12          # q3: thinner lid shade band
BROW_STROKES = 2      # p1: 2 = irregular thin hair strokes (MHS3), 1 = the old regular stripes


def _c(t):
    return np.array(t, float) / 255.0


def _sm(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def iris(res=512, hl_sign=1.0, ss=3):
    """Iris-local square u, v in [-EXT, EXT] (u outward from the nose, v up); unit circle = iris edge."""
    n = res * ss
    u = (np.arange(n) + 0.5) / n * 2 * EXT - EXT
    U, V = np.meshgrid(u, u)
    r = np.hypot(U, V)
    col = np.zeros(U.shape + (3,)); a = np.zeros(U.shape)
    ic = _c(C_IRIS) * np.ones_like(col)
    tm = 0.85 * _sm(0.25, 0.75, V)[..., None]    # q3: darker top
    ic = ic * (1 - tm) + _c(C_IRIS_TOP) * tm
    lr = np.hypot((U - LIGHT[0]) / LIGHT[2], (V - LIGHT[1]) / LIGHT[3])
    ic = np.where((lr < 1)[..., None], _c(C_IRIS_LIGHT), ic)
    deg = np.degrees(np.arctan2(V, U))
    # q4: Leo's iris has the two thin dark arcs on ONE upper side only - the highlight side (TypeSafe q4: iris off)
    dside = deg if hl_sign > 0 else np.degrees(np.arctan2(V, -U))
    for rr, lo, hi in ((0.62, -10, 75), (0.80, 5, 70)):
        ring = (np.abs(r - rr) < RING_W) & (dside > lo) & (dside < hi)
        ic = np.where(ring[..., None], _c(C_IRIS_LINE), ic)
    ic = np.where((r > 1 - RIM_W)[..., None], _c(C_IRIS_LINE), ic)
    # q3: two small light cross sparkles in the lower half (Leo face reference)
    for su in (-0.42, 0.42):
        du, dv = U - su, V + 0.30
        near = np.hypot(du, dv) < 0.16
        cross = near & ((np.abs(du - dv) < 0.035) | (np.abs(du + dv) < 0.035))
        ic = np.where(cross[..., None], _c((190, 236, 170)), ic)
    pr = np.hypot((U - PUPIL[0]) / PUPIL[2], (V - PUPIL[1]) / PUPIL[3])
    ic = np.where((pr < 1)[..., None], _c(C_PUPIL), ic)
    inside = r < 1
    col = np.where(inside[..., None], ic, col); a = inside.astype(float)
    hr = np.hypot((U - hl_sign * HL[0]) / HL[2], (V - HL[1]) / HL[3])
    hl = hr < 1
    col = np.where(hl[..., None], _c(C_HL), col); a = np.maximum(a, hl)
    return _down(col, a, res, ss)


def sclera(X0, X1, Z0, Z1, Xc, Uc, res=(512, 384), ss=2):
    """Eye white in eye-local coordinates, with the grey band under the (neutral) upper opening edge Uc(Xc)."""
    nx, nz = res[0] * ss, res[1] * ss
    X = X0 + (np.arange(nx) + 0.5) / nx * (X1 - X0)
    Z = Z0 + (np.arange(nz) + 0.5) / nz * (Z1 - Z0)
    XX, ZZ = np.meshgrid(X, Z)
    Ut = np.interp(XX, Xc, Uc)
    band = _sm(Ut - BAND - 0.02, Ut - BAND + 0.02, ZZ)[..., None]
    col = _c(C_SCLERA) * (1 - band) + _c(C_BAND) * band
    return _down(col, np.ones(XX.shape), res[0], ss, res[1])


def brow(BXs, Bb, Bt, res=(1024, 128), ss=2):
    """Brow strokes in brow UV (u along from the inner tip, v from the bottom edge to the top edge)."""
    nx, nz = res[0] * ss, res[1] * ss
    u = (np.arange(nx) + 0.5) / nx; v = (np.arange(nz) + 0.5) / nz
    UU, VV = np.meshgrid(u, v)
    X = BXs[0] + UU * (BXs[-1] - BXs[0])
    Z = np.interp(X, BXs, Bb) + VV * (np.interp(X, BXs, Bt) - np.interp(X, BXs, Bb))
    if BROW_STROKES == 2:
        # p1 (Leo render): thin dark hair strokes running from the lower inner side up and outward at a shallow angle,
        # irregular spacing and length, plus a darker lower edge; not a regular stripe pattern
        rng = np.random.default_rng(7)
        ph = (X - 1.7 * (Z - np.interp(X, BXs, Bb))) / 0.11
        ph = ph + 0.30 * np.sin(2.3 * X + 0.7) + 0.18 * np.sin(5.1 * X)
        k = np.floor(ph).astype(int)
        jit = rng.random(4096)
        duty = 0.10 + 0.12 * jit[np.mod(k, 4096)]
        on = np.mod(ph, 1.0) < duty
        # strokes start and stop at different heights (brush hairs, not full-height bars)
        lo_ = 0.55 * jit[np.mod(k * 7 + 3, 4096)]
        hi_ = 0.65 + 0.35 * jit[np.mod(k * 13 + 5, 4096)]
        on &= (VV > lo_ * 0.6) & (VV < hi_)
        edge = VV < 0.10 + 0.05 * np.sin(9.0 * UU)
        strand = on | edge
    else:
        strand = np.mod((X - 0.95 * Z) / 0.16, 1.0) < 0.30
    col = np.where(strand[..., None], _c(C_BROW_DARK), _c(C_BROW))
    return _down(col, np.ones(UU.shape), res[0], ss, res[1])


def _down(col, a, nx, ss, nz=None):
    nz = nx if nz is None else nz
    pm = (col * a[..., None]).reshape(nz, ss, nx, ss, 3).mean((1, 3))
    aa = a.reshape(nz, ss, nx, ss).mean((1, 3))
    c = pm / np.maximum(aa[..., None], 1e-6)
    return np.concatenate([c, aa[..., None]], -1).astype(np.float32)
