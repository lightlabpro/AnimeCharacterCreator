"""Radial surface of the learned mean head: r(lon, lat) about C, bilinear lookup for any direction."""
import numpy as np, math
import os
S = os.environ.get("MEAN_HEAD_DIR", os.path.dirname(os.path.abspath(__file__)))   # median radial map only (no per-model data)
_d = np.load(S + "/mean_head.npz")
R, LON, LAT, C = _d["r"], _d["lon"], _d["lat"], _d["C"]
NLON, NLAT = len(LON), len(LAT)


def smooth(r, it=2):
    out = r.copy()
    for _ in range(it):
        p = np.pad(out, ((1, 1), (0, 0)), mode="edge")
        out = (np.roll(p, 1, 1) + np.roll(p, -1, 1) + p[2:] * 0 + p[:-2] * 0 + 2 * p)[1:-1] / 4 if False else \
            (p[:-2] + p[2:] + np.roll(p, 1, 1)[1:-1] + np.roll(p, -1, 1)[1:-1] + 4 * p[1:-1]) / 8
    return out


def radius(dirs, r=None):
    r = R if r is None else r
    d = dirs / np.maximum(np.linalg.norm(dirs, axis=-1, keepdims=True), 1e-12)
    d = np.nan_to_num(d, nan=0.0); d[np.all(d == 0, axis=-1)] = (0, -1, 0)
    lat = np.arcsin(np.clip(d[..., 2], -1, 1))
    lon = np.arctan2(d[..., 0], -d[..., 1])
    fi = (lat - LAT[0]) / (LAT[1] - LAT[0]); fi = np.clip(fi, 0, NLAT - 1.001)
    fj = (lon - LON[0]) / (LON[1] - LON[0]) % NLON
    i0 = np.floor(fi).astype(int); j0 = np.floor(fj).astype(int) % NLON
    ti, tj = fi - i0, fj - np.floor(fj)
    j1 = (j0 + 1) % NLON
    return (r[i0, j0] * (1 - ti) * (1 - tj) + r[i0 + 1, j0] * ti * (1 - tj) + r[i0, j1] * (1 - ti) * tj + r[i0 + 1, j1] * ti * tj)


def point(dirs, r=None):
    d = dirs / np.linalg.norm(dirs, axis=-1, keepdims=True)
    return C + d * radius(d, r)[..., None]
