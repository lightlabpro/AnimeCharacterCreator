"""MHS3 painted eye (q-series): the eye is drawn into an RGBA texture on a decal that lies on the skin, so its shape
is not limited by the head mesh's eye opening (TypeSafe kept flagging outline_shape; the corner knobs had no effect on
the mesh). Pure numpy; apply_look.py execs this file.

Eye-local units: W2 = eye half-width. X runs from the inner corner (-1) to the outer corner (+1), Z up, Z = 0 at the
eye's reference line (the middle of the painted eye sits on the hole centre).

The outline curves are measured from the MHS3 protagonist frame (near eye, 101 px wide): line-top and lower-lid edge
per column, normalised by the half-width. The knobs below scale or shift them; colours are sampled sRGB values."""
import numpy as np

# --- knobs (reference-match judge, menu blender/tools/visual_corrections/eyes_paint.json) ---
EYE_TOP = 1.0        # scales the upper lid height
EYE_LOW = 1.0        # scales the lower lid depth
EYE_TILT = 0.0       # + raises the outer corner (W2 per unit X)
LID_TH = 0.16        # upper lid line thickness (W2)
LID_OUT = 0.0        # extra thickness at the outer end (W2)
BAND = 0.26          # grey lid-shadow band under the upper line (W2)
IRIS_X, IRIS_Z = -0.08, -0.10
IRIS_RX, IRIS_RY = 0.45, 0.51
PUPIL_RX, PUPIL_RY = 0.12, 0.17
PUPIL_X, PUPIL_Z = 0.01, 0.06           # relative to the iris centre
HL_X, HL_Z, HL_RX, HL_RY = -0.54, -0.19, 0.14, 0.065
HL2 = 0.0            # second small highlight (0 = off)
RINGS = 1.0          # concentric iris arcs strength
LOW_RIM = 1.0        # thin warm-grey rim along the lower lid (no dark line in MHS3)
INNER_PINK = 0.0     # pink inner corner

C_LINE = (84, 64, 48)
C_LINE_TOP = (92, 60, 42)
C_SCLERA = (199, 197, 188)
C_BAND = (161, 159, 161)
C_IRIS_TOP = (88, 112, 84)
C_IRIS = (112, 141, 100)
C_IRIS_LIGHT = (162, 201, 149)
C_IRIS_LINE = (62, 70, 50)
C_PUPIL = (60, 63, 48)
C_LOW_RIM = (196, 186, 168)
C_PINK = (205, 160, 128)

# --- brow (q21): painted from the measured MHS3 brow edges (near brow, 157 px long), same eye-local units ---
BROW = 1             # paint the brow into the decal (the mesh brow strip is then skipped)
BROW_THICK = 1.0     # scales the brow thickness about its centre line
BROW_DZ = 0.0        # moves the brow up (+) / down (W2)
BROW_LEN = 1.0       # scales the brow length about its middle
BROW_SHADE = 1.0     # mauve shadow under the inner end
BROW_INNER = 1.0     # thickness multiplier for the inner third
BROW_VAL = 1.0       # brow colour brightness
BROW_GREY = 0.0      # brow colour toward grey
C_BROW = (122, 95, 71)
C_BROW_DARK = (92, 66, 45)
C_BROW_SHADE = (176, 128, 112)
BX = [-1.711, -1.417, -1.347, -1.001, -0.862, -0.481, -0.134, 0.213, 0.559, 0.906, 1.253, 1.391]
BT = [0.233, 0.623, 0.637, 0.707, 0.725, 0.775, 0.816, 0.86, 0.911, 0.938, 0.911, 0.85]
BB = [0.233, 0.31, 0.328, 0.393, 0.419, 0.487, 0.555, 0.623, 0.707, 0.775, 0.826, 0.85]
BS = [0.233, 0.099, 0.131, 0.3, 0.368, 0.487, 0.555, 0.623, 0.707, 0.775, 0.826, 0.85]   # lower edge incl. shadow

X_TOP = [-0.94, -0.90, -0.84, -0.78, -0.72, -0.66, -0.60, -0.54, -0.48, -0.42, -0.31, -0.15, 0.0, 0.11, 0.23, 0.29,
         0.39, 0.47, 0.55, 0.63, 0.70, 0.78, 0.86, 0.94, 1.0]
Z_TOP = [-0.15, 0.09, 0.21, 0.27, 0.31, 0.35, 0.39, 0.41, 0.43, 0.45, 0.47, 0.47, 0.47, 0.45, 0.43, 0.41, 0.39, 0.35,
         0.31, 0.27, 0.21, 0.15, 0.07, -0.05, -0.15]
X_LOW = [-0.94, -0.92, -0.88, -0.80, -0.72, -0.64, -0.48, -0.33, -0.09, 0.07, 0.23, 0.39, 0.55, 0.70, 0.86, 0.94, 1.0]
Z_LOW = [-0.15, -0.19, -0.27, -0.43, -0.50, -0.56, -0.64, -0.66, -0.70, -0.70, -0.68, -0.66, -0.58, -0.50, -0.35,
         -0.25, -0.15]
X0, X1, Z0, Z1 = -1.85, 1.60, -1.0, 1.25         # decal extent (W2); q21: includes the brow
MID = -0.115                                      # middle of the painted eye (placed on the hole centre)


def _sm(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def _curve(xs, zs, X, smooth_n=41):
    xx = np.linspace(-1.0, 1.0, 801)
    zz = np.interp(xx, xs, zs)
    k = np.ones(smooth_n) / smooth_n
    zz = np.convolve(np.pad(zz, smooth_n // 2, mode="edge"), k, mode="valid")
    return np.interp(X, xx, zz)


def paint(nx=960, nz=640, ss=3):
    """RGBA float array (nz, nx, 4), row 0 = bottom (Blender pixel order), sRGB 0..1."""
    X = X0 + (np.arange(nx * ss) + 0.5) / (nx * ss) * (X1 - X0)
    Z = Z0 + (np.arange(nz * ss) + 0.5) / (nz * ss) * (Z1 - Z0)
    XX, ZZ = np.meshgrid(X, Z)
    xc = np.clip(XX, -0.94, 1.0)
    top = _curve(X_TOP, Z_TOP, xc) * EYE_TOP + EYE_TILT * xc
    low = _curve(X_LOW, Z_LOW, xc) * EYE_LOW + EYE_TILT * xc
    inside_x = (XX >= -0.94) & (XX <= 1.0)
    eye = inside_x & (ZZ < top) & (ZZ > low)
    th = (LID_TH + LID_OUT * _sm(0.3, 1.0, xc)) * (0.45 + 0.55 * _sm(-0.94, -0.70, xc))
    line = eye & (ZZ > top - th)
    col = np.zeros(XX.shape + (3,)); a = np.zeros(XX.shape)
    c = lambda t: np.array(t, float) / 255.0
    # sclera with the grey band under the upper line
    col[:] = c(C_SCLERA)
    band = _sm(top - th - BAND - 0.02, top - th - BAND + 0.02, ZZ)
    col = col * (1 - band[..., None]) + c(C_BAND) * band[..., None]
    # iris
    ix, iz = IRIS_X, IRIS_Z
    r = np.sqrt(((XX - ix) / IRIS_RX) ** 2 + ((ZZ - iz) / IRIS_RY) ** 2)
    iris = r < 1.0
    ic = c(C_IRIS) * np.ones_like(col)
    tmix = 0.6 * _sm(iz + 0.10, iz + 0.45, ZZ)[..., None]
    ic = ic * (1 - tmix) + c(C_IRIS_TOP) * tmix
    lr = np.sqrt(((XX - ix) / (IRIS_RX * 0.95)) ** 2 + ((ZZ - (iz - IRIS_RY * 0.62)) / (IRIS_RY * 0.45)) ** 2)
    light = lr < 1.0
    ic = np.where(light[..., None], c(C_IRIS_LIGHT), ic)
    if RINGS > 0:
        ang = np.arctan2(ZZ - iz, XX - ix)
        deg = np.degrees(ang)
        for rr, lo_, hi_ in ((0.60, 95, 235), (0.78, 110, 215), (0.62, -55, 70)):
            on = (deg > lo_) & (deg < hi_) if lo_ > 0 else (deg > lo_) & (deg < hi_)
            ring = (np.abs(r - rr) < 0.022 * RINGS) & on
            ic = np.where(ring[..., None], c(C_IRIS_LINE), ic)
    ic = np.where((r > 0.95)[..., None], c(C_IRIS_LINE), ic)
    pr = np.sqrt(((XX - ix - PUPIL_X) / PUPIL_RX) ** 2 + ((ZZ - iz - PUPIL_Z) / PUPIL_RY) ** 2)
    ic = np.where((pr < 1.0)[..., None], c(C_PUPIL), ic)
    ic = np.where(band[..., None] > 0.5, ic * 0.86, ic)          # the lid shadow darkens the iris top too
    col = np.where(iris[..., None], ic, col)
    # highlight(s)
    hr = np.sqrt(((XX - HL_X) / HL_RX) ** 2 + ((ZZ - HL_Z) / HL_RY) ** 2)
    col = np.where((hr < 1.0)[..., None], c((250, 250, 248)), col)
    if HL2 > 0:
        h2 = np.sqrt(((XX - (ix + IRIS_RX * 0.45)) / (0.05 * HL2)) ** 2 + ((ZZ - (iz - IRIS_RY * 0.55)) / (0.05 * HL2)) ** 2)
        col = np.where((h2 < 1.0)[..., None], c((240, 245, 240)), col)
    # lower rim, inner corner
    if LOW_RIM > 0:
        rim = eye & (ZZ < low + 0.035 * LOW_RIM)
        col = np.where(rim[..., None], c(C_LOW_RIM), col)
    if INNER_PINK > 0:
        pk = (_sm(-0.80, -0.95, XX) * INNER_PINK)[..., None]
        col = col * (1 - pk) + c(C_PINK) * pk
    # upper lid line (darker along its top edge)
    lc = np.where((ZZ > top - th * 0.35)[..., None], c(C_LINE_TOP), c(C_LINE))
    col = np.where(line[..., None], lc, col)
    a = eye.astype(float)
    if BROW:
        mid_x = (BX[0] + BX[-1]) / 2
        bxs = [mid_x + (b - mid_x) * BROW_LEN for b in BX]
        inb = (XX > bxs[0]) & (XX < bxs[-1])
        bt = np.interp(XX, bxs, BT); bb = np.interp(XX, bxs, BB); bs = np.interp(XX, bxs, BS)
        cm = (bt + bb) / 2
        tk = BROW_THICK * (1 + (BROW_INNER - 1) * (1 - _sm(bxs[0] + 0.3, bxs[0] + 1.1, XX)))
        bt2 = cm + (bt - cm) * tk + BROW_DZ; bb2 = cm + (bb - cm) * tk + BROW_DZ
        brow = inb & (ZZ < bt2) & (ZZ > bb2)
        shade = inb & (ZZ <= bb2) & (ZZ > bs + BROW_DZ) & (BROW_SHADE > 0) & ~eye
        # brush hatching: strands along the brow, slightly diagonal
        v = (ZZ - bb2) / np.maximum(bt2 - bb2, 1e-3)
        strand = np.mod((XX - 0.95 * ZZ) / 0.16, 1.0) < 0.30      # steep diagonal brush strokes
        def bcol(t):
            v = c(t) * BROW_VAL
            return v * (1 - BROW_GREY) + v.mean() * BROW_GREY
        bc = np.where(strand[..., None], bcol(C_BROW_DARK), bcol(C_BROW))
        col = np.where(brow[..., None], bc, col)
        col = np.where(shade[..., None], c(C_BROW_SHADE), col)
        a = np.maximum(a, (brow | shade).astype(float))
    # supersample down
    pm = (col * a[..., None]).reshape(nz, ss, nx, ss, 3).mean((1, 3))
    a = a.reshape(nz, ss, nx, ss).mean((1, 3))
    col = pm / np.maximum(a[..., None], 1e-6)          # straight colour from the covered sub-samples only
    out = np.concatenate([col, a[..., None]], -1)
    return out.astype(np.float32)
