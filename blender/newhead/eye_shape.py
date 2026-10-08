"""MHS3 eye and brow shapes as smooth curves, plus their expression offsets (r1: animatable eyes).

Pure numpy, shared by build_head.py (the head's eye opening) and face_rig.py (eye white, iris, lid line, brow meshes
and their shape keys). Eye-local units: W2 = eye half-width; X from the inner corner (-1) to the outer corner (+1),
Z up; Z = 0 is the eye's reference line. The tables are the MHS3 protagonist's near eye and brow (measured column by
column, 101 px wide eye); every curve is resampled densely and Gaussian-smoothed so edges are round, not polygonal.
"""
import numpy as np

# --- placement on the head (head units H: chin 0, skull top 1) ---
EYE_CX = 0.2082      # eye centre x (|x|), q-series EYE_X + EYE_DX
EYE_Z0 = 0.5014      # z of the eye reference line
EYE_W2 = 0.110       # half-width

# --- shape knobs ---
EYE_TOP = 1.0
EYE_LOW = 1.0
EYE_TILT = 0.0
LID_TH = 0.16        # upper lid line thickness
WING = 0.16          # r1: the line runs down the outer corner along this share of the lower lid
WING_TH = 0.13       # its start thickness (tapers to 0)
LOW_RIM = 0.035      # faint warm-grey rim along the lower lid
IRIS_X, IRIS_Z, IRIS_RX, IRIS_RY = -0.08, -0.10, 0.45, 0.51
OPEN_EPS = 0.10      # the opening ends where it is this tall (the lid line covers the thin wedge beyond)
SMOOTH = 0.055       # Gaussian sigma (W2) along the curves

X_TOP = [-0.94, -0.90, -0.84, -0.78, -0.72, -0.66, -0.60, -0.54, -0.48, -0.42, -0.31, -0.15, 0.0, 0.11, 0.23, 0.29,
         0.39, 0.47, 0.55, 0.63, 0.70, 0.78, 0.86, 0.94, 1.0]
Z_TOP = [-0.15, 0.09, 0.21, 0.27, 0.31, 0.35, 0.39, 0.41, 0.43, 0.45, 0.47, 0.47, 0.47, 0.45, 0.43, 0.41, 0.39, 0.35,
         0.31, 0.27, 0.21, 0.15, 0.07, -0.05, -0.15]
X_LOW = [-0.94, -0.92, -0.88, -0.80, -0.72, -0.64, -0.48, -0.33, -0.09, 0.07, 0.23, 0.39, 0.55, 0.70, 0.86, 0.94, 1.0]
Z_LOW = [-0.15, -0.19, -0.27, -0.43, -0.50, -0.56, -0.64, -0.66, -0.70, -0.70, -0.68, -0.66, -0.58, -0.50, -0.35,
         -0.25, -0.15]
# brow (traced, q21)
BX = [-1.711, -1.417, -1.347, -1.001, -0.862, -0.481, -0.134, 0.213, 0.559, 0.906, 1.253, 1.391]
BT = [0.272, 0.647, 0.661, 0.728, 0.745, 0.793, 0.833, 0.875, 0.924, 0.95, 0.924, 0.865]
BB = [0.272, 0.346, 0.363, 0.426, 0.451, 0.516, 0.582, 0.647, 0.728, 0.793, 0.842, 0.865]
BROW_THICK = 1.0
BROW_DZ = 0.0


def _sm(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def _gauss1d(z, sig_pts):
    if sig_pts < 0.5:
        return z
    k = int(3 * sig_pts) + 1
    w = np.exp(-0.5 * (np.arange(-k, k + 1) / sig_pts) ** 2); w /= w.sum()
    return np.convolve(np.pad(z, k, mode="edge"), w, mode="valid")


def curve(xs, zs, n=400, x0=None, x1=None):
    """Dense smoothed curve z(X) on [x0, x1]."""
    x0 = xs[0] if x0 is None else x0; x1 = xs[-1] if x1 is None else x1
    X = np.linspace(x0, x1, n)
    Z = np.interp(X, xs, zs)
    return X, _gauss1d(Z, SMOOTH / ((x1 - x0) / (n - 1)))


def base_curves(n=400):
    """Upper opening edge U(X) (= under the lid line), lower edge L(X), lid-line top T(X), all on one X grid."""
    X, T = curve(X_TOP, Z_TOP, n, -0.94, 1.0)
    _, L = curve(X_LOW, Z_LOW, n, -0.94, 1.0)
    T = T * EYE_TOP + EYE_TILT * X
    L = L * EYE_LOW + EYE_TILT * X
    th = LID_TH * (0.45 + 0.55 * _sm(-0.94, -0.70, X))
    U = np.maximum(T - th, L)
    return X, U, L, T


def open_range(X, U, L, eps=0.02):
    """Indices where the opening is actually open (U above L); the corners are where it closes."""
    ok = np.nonzero(U - L > eps)[0]
    return ok[0], ok[-1]


def expression_offsets(name, X, U, L):
    """(dU, dL) offsets of the upper / lower opening edge for one expression key (W2 units), given U, L on X."""
    w = np.clip(1 - X ** 2, 0, 1) ** 0.6                 # corners stay attached
    if name == "Blink":
        C = L + 0.22 * (U - L)
        return C - U, C - L
    if name == "Wide":
        return 0.14 * w, -0.07 * w
    if name == "Sad":
        return (-0.12 * X - 0.06) * w, 0.05 * w
    if name == "Angry":
        return (0.12 * X - 0.10) * w, 0.06 * w
    if name == "Happy":
        return -0.06 * w, 0.32 * w
    return 0 * X, 0 * X


def opening_contour(dU=None, dL=None, n=400, m=160):
    """Closed smooth contour of the eye opening (inner corner, over the top to the outer corner, back along the
    bottom), m points by arc length."""
    X, U, L, _ = base_curves(n)
    U0 = U
    if dU is not None:
        U = np.maximum(U + dU, L + dL); L = L + dL
    i0, i1 = open_range(X, U0, base_curves(n)[2], eps=OPEN_EPS)
    top = np.stack([X[i0:i1 + 1], U[i0:i1 + 1]], 1)
    bot = np.stack([X[i0:i1 + 1][::-1], L[i0:i1 + 1][::-1]], 1)[1:-1]
    P = np.concatenate([top, bot])
    return resample_closed(P, m)


def resample_closed(P, m, sig=None):
    seg = np.linalg.norm(np.roll(P, -1, 0) - P, axis=1)
    s = np.concatenate([[0], np.cumsum(seg)]); tot = s[-1]
    t = np.linspace(0, tot, m, endpoint=False)
    Q = np.stack([np.interp(t, s, np.append(P[:, k], P[0, k])) for k in range(2)], 1)
    sig = SMOOTH if sig is None else sig
    sp = sig / (tot / m)
    if sp >= 0.5:                                         # circular Gaussian: rounds the corners a little
        k = int(3 * sp) + 1
        wts = np.exp(-0.5 * (np.arange(-k, k + 1) / sp) ** 2); wts /= wts.sum()
        Q = np.stack([np.convolve(np.concatenate([Q[-k:, j], Q[:, j], Q[:k, j]]), wts, mode="valid") for j in range(2)], 1)
    return Q


def lid_ribbon(dU=None, dL=None, n=400, samples=100, wing=1.0):
    """The upper lid line as (inner, outer) point pairs along the upper edge from the inner corner to the outer corner,
    then a short wing down the outer corner along the lower edge, thickness tapering to 0."""
    X, U, L, _ = base_curves(n)
    i0, i1 = open_range(X, U, L, eps=OPEN_EPS)
    if dU is not None:
        U = np.maximum(U + dU, L + dL); L = L + dL
    th = LID_TH * (0.45 + 0.55 * _sm(X[i0], X[i0] + 0.25, X))
    up = np.stack([X[i0:i1 + 1], U[i0:i1 + 1]], 1)
    xc = X[i1]; xw = xc - 2.0 * WING
    tu = th[i0:i1 + 1] * (1 - (1 - wing) * _sm(xc - 0.30, xc, X[i0:i1 + 1]))   # closed eye: the line tapers off
    j = np.nonzero((X <= xc) & (X >= xw))[0][::-1]       # outer corner -> inward along the lower edge
    lo = np.stack([X[j], L[j]], 1)[1:]
    tl = np.interp(X[j], [xw, xc], [0.0, WING_TH])[1:] * max(wing, 1e-3)
    path = np.concatenate([up, lo]); thick = np.concatenate([tu, tl])
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1); s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], samples)
    Pp = np.stack([np.interp(t, s, path[:, k]) for k in range(2)], 1)
    Th = _gauss1d(np.interp(t, s, thick), 2.0)
    Pp = np.stack([_gauss1d(Pp[:, 0], 1.5), _gauss1d(Pp[:, 1], 1.5)], 1)
    d = np.gradient(Pp, axis=0); d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    nrm = np.stack([-d[:, 1], d[:, 0]], 1)
    nrm = np.stack([_gauss1d(nrm[:, 0], 3.0), _gauss1d(nrm[:, 1], 3.0)], 1)   # turn smoothly round the corner
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    inner = Pp - nrm * 0.03                              # tuck under the skin edge (covers the mesh chords)
    outer = Pp + nrm * Th[:, None]
    return inner, outer, Th


def low_rim_ribbon(dU=None, dL=None, n=400, samples=60):
    X, U, L, _ = base_curves(n)
    i0, i1 = open_range(X, U, L, eps=OPEN_EPS)
    if dU is not None:
        L = L + dL
    xw = X[i1] - 2.0 * WING
    sel = (X >= X[i0]) & (X <= xw + 0.08)
    P = np.stack([X[sel], L[sel]], 1)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], samples)
    P = np.stack([np.interp(t, s, P[:, k]) for k in range(2)], 1)
    taper = _sm(0.0, 0.12, t / s[-1]) * _sm(1.0, 0.85, t / s[-1])
    return P + np.array([0, 0.02]), P - np.stack([np.zeros(samples), LOW_RIM * taper], 1)


def brow_ribbon(samples=60, d=None):
    """Brow as (bottom, top) pairs along its length; d(t) adds a vertical offset (expression), t 0 inner -> 1 outer."""
    X = np.linspace(BX[0], BX[-1], samples)
    T = np.interp(X, BX, BT); B = np.interp(X, BX, BB)
    T = _gauss1d(T, 1.2); B = _gauss1d(B, 1.2)
    T[0] = B[0] = (BT[0] + BB[0]) / 2
    cm = (T + B) / 2
    T = cm + (T - cm) * BROW_THICK + BROW_DZ; B = cm + (B - cm) * BROW_THICK + BROW_DZ
    if d is not None:
        t = (X - X[0]) / (X[-1] - X[0]); off = d(t); T = T + off; B = B + off
    return np.stack([X, B], 1), np.stack([X, T], 1)


BROW_KEYS = {
    "BrowUp": lambda t: 0.22 + 0.06 * np.sin(np.pi * t),
    "BrowDown": lambda t: -0.14 + 0 * t,
    "BrowAngry": lambda t: -0.30 * (1 - t) ** 1.5 + 0.06 * t,
    "BrowSad": lambda t: 0.30 * (1 - t) ** 1.5 - 0.10 * t,
}
EYE_KEYS = ["Blink", "Wide", "Sad", "Angry", "Happy"]
IRIS_KEYS = {"LookLeft": (-0.32, 0.0), "LookRight": (0.32, 0.0), "LookUp": (0.0, 0.16), "LookDown": (0.0, -0.14)}
