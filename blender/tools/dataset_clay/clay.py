"""Plain clay renders of normalised heads (no toon, no paint): smooth vertex normals, Lambert key from front-top-left,
z-buffer rasteriser in numpy. clay(npz, yaw_deg, size) -> RGB uint8."""
import numpy as np

def vnormals(v, f):
    t = v[f]; fn = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    n = np.zeros_like(v)
    for k in range(3):
        np.add.at(n, f[:, k], fn)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return n

def render(v, f, yaw=0.0, size=600, box=(-0.72, 0.72, -0.12, 1.32), light=(-0.45, -0.75, -0.5), cmap=None):
    a = np.radians(yaw)
    # rotate about the vertical axis (h is down); camera looks along +y
    R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    P = v @ R.T
    n = vnormals(v, f) @ R.T
    n = n * np.where(n[:, 1:2] > 0, -1.0, 1.0)          # mirrored axes / mixed winding: face the camera (-y)
    L = np.array(light, float); L /= np.linalg.norm(L)   # direction TO the light: -y toward camera, -h up
    sh = np.clip(-(n @ -L), 0, 1) if False else np.clip(n @ L, 0, 1)
    shade = 0.18 + 0.82 * sh
    if cmap is not None:
        shade = cmap
    x0, x1, h0, h1 = box
    W = size; Hh = int(size * (h1 - h0) / (x1 - x0))
    sx = (P[:, 0] - x0) / (x1 - x0) * (W - 1); sy = (P[:, 2] - h0) / (h1 - h0) * (Hh - 1)
    depth = P[:, 1]
    img = np.full((Hh, W), np.nan); zb = np.full((Hh, W), np.inf)
    T = f
    xs, ys, zs, cs = sx[T], sy[T], depth[T], shade[T]
    for i in range(len(T)):
        x, y, z, c = xs[i], ys[i], zs[i], cs[i]
        xmin, xmax = int(max(0, np.floor(x.min()))), int(min(W - 1, np.ceil(x.max())))
        ymin, ymax = int(max(0, np.floor(y.min()))), int(min(Hh - 1, np.ceil(y.max())))
        if xmin > xmax or ymin > ymax:
            continue
        gx, gy = np.meshgrid(np.arange(xmin, xmax + 1), np.arange(ymin, ymax + 1))
        d = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(d) < 1e-12:
            continue
        l0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / d
        l1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / d
        l2 = 1 - l0 - l1
        m = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not m.any():
            continue
        zz = l0 * z[0] + l1 * z[1] + l2 * z[2]
        cc = l0 * c[0] + l1 * c[1] + l2 * c[2]
        gy_, gx_ = gy[m], gx[m]; zz = zz[m]; cc = cc[m]
        upd = zz < zb[gy_, gx_]
        zb[gy_[upd], gx_[upd]] = zz[upd]; img[gy_[upd], gx_[upd]] = cc[upd]
    out = np.where(np.isnan(img), 0.93, img)
    rgb = np.stack([out * 0.95, out * 0.88, out * 0.80], -1)
    rgb[np.isnan(img)] = [0.93, 0.93, 0.95]
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
