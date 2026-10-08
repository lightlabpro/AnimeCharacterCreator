"""Textures for the animatable eye (r1): iris (moves with the iris mesh), eye white with the lid-shadow band, brow
strokes. Pure numpy; RGBA float arrays (rows bottom-up, Blender pixel order), sRGB 0..1. Colours sampled from the
MHS3 protagonist frame."""
import numpy as np

C_SCLERA = (199, 197, 188)
C_BAND = (161, 159, 161)
C_IRIS_TOP = (88, 112, 84)
C_IRIS = (112, 141, 100)
C_IRIS_LIGHT = (162, 201, 149)
C_IRIS_LINE = (58, 66, 46)
C_PUPIL = (60, 63, 48)
C_HL = (250, 250, 248)
C_BROW = (122, 95, 71)
C_BROW_DARK = (92, 66, 45)
RING_W = 0.042        # r1: thicker iris arcs (MHS3 frame; q-series 0.022)
RIM_W = 0.075         # dark iris outline width (share of the radius)
PUPIL = (0.02, 0.12, 0.27, 0.33)      # centre u, v and radii, iris-local
LIGHT = (0.0, -0.62, 0.95, 0.45)      # light crescent ellipse
HL = (-1.02, -0.18, 0.31, 0.13)       # highlight (iris-local; u mirrored for the viewer-right eye)
EXT = 1.40            # texture / mesh extent around the iris (the highlight overlaps the white)
BAND = 0.26


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
    tm = 0.6 * _sm(0.2, 0.9, V)[..., None]
    ic = ic * (1 - tm) + _c(C_IRIS_TOP) * tm
    lr = np.hypot((U - LIGHT[0]) / LIGHT[2], (V - LIGHT[1]) / LIGHT[3])
    ic = np.where((lr < 1)[..., None], _c(C_IRIS_LIGHT), ic)
    deg = np.degrees(np.arctan2(V, U))
    for rr, lo, hi in ((0.60, 95, 235), (0.79, 110, 215), (0.63, -55, 70)):
        ring = (np.abs(r - rr) < RING_W) & (deg > lo) & (deg < hi)
        ic = np.where(ring[..., None], _c(C_IRIS_LINE), ic)
    ic = np.where((r > 1 - RIM_W)[..., None], _c(C_IRIS_LINE), ic)
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
    strand = np.mod((X - 0.95 * Z) / 0.16, 1.0) < 0.30
    col = np.where(strand[..., None], _c(C_BROW_DARK), _c(C_BROW))
    return _down(col, np.ones(UU.shape), res[0], ss, res[1])


def _down(col, a, nx, ss, nz=None):
    nz = nx if nz is None else nz
    pm = (col * a[..., None]).reshape(nz, ss, nx, ss, 3).mean((1, 3))
    aa = a.reshape(nz, ss, nx, ss).mean((1, 3))
    c = pm / np.maximum(aa[..., None], 1e-6)
    return np.concatenate([c, aa[..., None]], -1).astype(np.float32)
