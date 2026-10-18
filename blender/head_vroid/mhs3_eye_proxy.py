"""Front-view eye opening of a warped VRoid face, without rendering (q36 eye-shape standard).

Rasterises the face-skin triangles (orthographic front view) around the +x eye: the opening is the region round
the pupil that no skin covers (the lid's inner skin covers too, as in the render). Returns the same outline
descriptors as mhs3_render_measure.eye_box (shape_top / shape_bot inner->outer in units of the opening width,
corner_tilt), so knobs can be fitted against eye_shape_template before a render checks them."""
import numpy as np
from scipy import ndimage


def opening(parts, res=0.00015):
    FV, FT = next(v for k, v in parts.items() if "Face_00_SKIN" in k)
    IR = next(v for k, v in parts.items() if "EyeIris" in k)[0]
    p = IR[IR[:, 0] > 0].mean(0)
    x0, x1, z0, z1 = p[0] - 0.03, p[0] + 0.03, p[2] - 0.02, p[2] + 0.02
    xs = np.arange(x0, x1, res); zs = np.arange(z0, z1, res)
    X, Z = np.meshgrid(xs, zs)
    cov = np.zeros(X.shape, bool)
    A, B, C = FV[FT[:, 0]], FV[FT[:, 1]], FV[FT[:, 2]]
    near = (np.maximum.reduce([A[:, 0], B[:, 0], C[:, 0]]) > x0) & (np.minimum.reduce([A[:, 0], B[:, 0], C[:, 0]]) < x1) & \
           (np.maximum.reduce([A[:, 2], B[:, 2], C[:, 2]]) > z0) & (np.minimum.reduce([A[:, 2], B[:, 2], C[:, 2]]) < z1) & \
           (np.minimum.reduce([A[:, 1], B[:, 1], C[:, 1]]) > p[1] - 0.03)
    for a, b, c in zip(A[near], B[near], C[near]):
        v0 = b - a; v1 = c - a
        den = v0[0] * v1[2] - v1[0] * v0[2]
        if abs(den) < 1e-14:
            continue
        i0 = np.searchsorted(xs, min(a[0], b[0], c[0])); i1 = np.searchsorted(xs, max(a[0], b[0], c[0]))
        j0 = np.searchsorted(zs, min(a[2], b[2], c[2])); j1 = np.searchsorted(zs, max(a[2], b[2], c[2]))
        if i1 <= i0 or j1 <= j0:
            continue
        px = X[j0:j1, i0:i1] - a[0]; pz = Z[j0:j1, i0:i1] - a[2]
        u = (px * v1[2] - v1[0] * pz) / den; v = (v0[0] * pz - px * v0[2]) / den
        cov[j0:j1, i0:i1] |= (u >= 0) & (v >= 0) & (u + v <= 1)
    lab, n = ndimage.label(~cov)
    k = lab[np.searchsorted(zs, p[2]), np.searchsorted(xs, p[0])]
    m = lab == k
    jj, ii = np.where(m)
    wpx = ii.max() - ii.min(); yc = 0.5 * (jj.min() + jj.max())
    top, bot = [], []
    for f in np.linspace(0.06, 0.94, 9):            # +x eye: inner corner at small x
        c_ = int(round(ii.min() + f * wpx)); col = np.where(m[:, c_])[0]
        # z grows upward; image rows grow downward -> flip signs so + = down like the render
        top.append(-(col.max() - yc) / wpx); bot.append(-(col.min() - yc) / wpx)
    inner = jj[ii <= ii.min() + 2].mean(); outer = jj[ii >= ii.max() - 2].mean()
    top_abs = []
    for c_ in range(ii.min(), ii.max() + 1, 4):
        col = np.where(m[:, c_])[0]
        if len(col):
            top_abs.append((float(xs[c_]), float(zs[col.max()])))
    return {"shape_top": top, "shape_bot": bot, "corner_tilt": (outer - inner) / wpx,
            "w_mm": wpx * res * 1000, "h_mm": (jj.max() - jj.min()) * res * 1000, "top_abs": top_abs}
