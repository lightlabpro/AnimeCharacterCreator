"""q31 base head: rework a CC BY dataset anime head into the MHS3 adult-male head as a signed-distance grid that the
v2 pipeline (face_paint_v2 / build_v2 / measure_v2 via sdf_head.sdf) uses in place of the lofted sections.

Sammy (2026-10-17): "you can even use the reference as a base model and rework it so it looks like mhs3".
Base: "Autumn Girl" by Aryzus (Sketchfab, CC Attribution 4.0; TexVerse uid d60fb442...) - credit kept in
docs/reference/ATTRIBUTION.md. Only the head / neck skin is used, then reworked:
  1. vertical remap of the landmarks onto the adult-male layout (pupil line, nose bottom, mouth; the base is a
     big-cranium girl head: eyes at h 0.62, mouth 0.865)
  2. width / depth changes by height (male jaw and chin wider, cranium a touch narrower)
  3. signed distance by fast winding number (fills the eye holes and the open neck), Gaussian-smoothed so the
     modelled brows / tear marks / lip lines melt into a clean painted-style surface

    python3 base_head.py REF.npz OUT_grid.npz [--vox 0.006]
REF.npz: normalised head (x, y in head heights, face toward -y; h = 0 skull top .. 1 chin) from dataset_clay/extract_heads.py
"""
import json
import sys

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter

# landmark remap (base h -> target h); target layout: pupil 0.50, nose bottom 0.73, mouth 0.82 (adult male anime)
H_PINS = [(0.0, 0.0), (0.30, 0.265), (0.47, 0.395), (0.62, 0.50), (0.76, 0.73), (0.865, 0.82), (1.0, 1.0), (1.30, 1.30)]
# half-width scale by target h (male: wider jaw / chin, cheeks a touch fuller; cranium slightly narrower)
SX = [(0.0, 0.96), (0.30, 0.96), (0.50, 0.98), (0.65, 1.03), (0.80, 1.10), (0.90, 1.14), (1.0, 1.10), (1.08, 1.0), (1.3, 1.0)]
# depth scale by target h (front half y<0 / back half y>0)
SYF = [(0.0, 1.0), (0.5, 1.0), (0.75, 1.02), (0.95, 1.04), (1.3, 1.0)]
SYB = [(0.0, 1.0), (1.3, 1.0)]
SMOOTH = 0.014          # Gaussian sigma in head heights (0.008 left the source model's facets as bands)
SOCKET_FILL = 0.06       # wider than the socket (0.025 left it open)
EYE_C = (0.17, 0.50)       # target eye centre |x|, h (H_PINS puts the base eyes at h 0.50)
EYE_R = (0.14, 0.10)
WIND_T = 0.40           # inside when |winding number| > this (open shells read ~0.5 inside)


def tab(t):
    t = np.array(t, float)
    return PchipInterpolator(t[:, 0], t[:, 1], extrapolate=True)


def warp(v):
    fh = tab(H_PINS)
    h2 = fh(v[:, 2])
    sx, syf, syb = tab(SX)(h2), tab(SYF)(h2), tab(SYB)(h2)
    x2 = v[:, 0] * sx
    y2 = np.where(v[:, 1] < 0, v[:, 1] * syf, v[:, 1] * syb)
    return np.stack([x2, y2, h2], 1)


def cap_holes(v, f):
    """Close every boundary loop (eye holes, the open neck) with a fan round its centroid, oriented like the faces next
    to it, so the winding number fills them (q31: the eye holes stayed open sockets)."""
    from collections import defaultdict
    cnt = defaultdict(int)
    for a, b, c in f:
        for e in ((a, b), (b, c), (c, a)):
            cnt[(min(e), max(e))] += 1
    nxt = {}
    for a, b, c in f:
        for e in ((a, b), (b, c), (c, a)):
            if cnt[(min(e), max(e))] == 1:
                nxt[e[0]] = e[1]                              # directed as in its face
    loops, seen = [], set()
    for s0 in list(nxt):
        if s0 in seen:
            continue
        lp = [s0]; seen.add(s0); cur = nxt[s0]
        while cur != s0 and cur in nxt and cur not in seen:
            lp.append(cur); seen.add(cur); cur = nxt[cur]
        if cur == s0 and len(lp) >= 3:
            loops.append(lp)
    V = [v]; F = [f]; n = len(v)
    for lp in loops:
        lp = np.asarray(lp)
        if len(lp) < 3:
            continue
        c = v[lp].mean(0)
        V.append(c[None]); ci = n; n += 1
        tri = np.stack([np.full(len(lp), ci), np.roll(lp, -1), lp], 1)
        F.append(tri)
    return np.vstack(V), np.vstack(F).astype(np.int64)


def grid(v, f, vox):
    import igl
    lo = np.array([-0.62, -0.62, -0.06]); hi = np.array([0.62, 0.56, 1.28])
    xs, ys, hs = (np.arange(lo[i], hi[i] + vox, vox) for i in range(3))
    X, Y, Z = np.meshgrid(xs, ys, hs, indexing="ij")
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    # q31: no capping (separate shells - face, skull, ears - each open; capping scrambled them); the eyeballs are kept
    # in the source mesh and fill the sockets
    w = igl.fast_winding_number(v.astype(np.float64), f.astype(np.int64), P.astype(np.float64))
    # exact unsigned distance to the triangles (q31: point-sampled distances left the surface bumpy)
    d2 = igl.point_mesh_squared_distance(P.astype(np.float64), v.astype(np.float64), f.astype(np.int64))[0]
    dist = np.sqrt(d2)
    sgn = np.where(np.abs(w) > WIND_T, -1.0, 1.0)          # the normalised mesh is mirrored (h runs down): w is -1 inside
    D = (sgn * dist).reshape(X.shape).astype(np.float32)
    if SMOOTH > 0:
        D = gaussian_filter(D, SMOOTH / vox)
    # q31: fill the eye sockets flush (our eyes are painted pieces on the surface, MHS3-style): in a soft mask round
    # each eye take min(D, heavily blurred D) - the blur of a concavity is lower than the concavity itself
    Db = gaussian_filter(D, SOCKET_FILL / vox)
    Xc, Yc, Hc = X, Y, Z
    m = np.zeros_like(D)
    for sx in (1, -1):
        r = np.sqrt(((Xc - sx * EYE_C[0]) / EYE_R[0]) ** 2 + ((Hc - EYE_C[1]) / EYE_R[1]) ** 2)
        m = np.maximum(m, np.clip(1.6 - r, 0, 1))
    m = m * np.clip((-Yc - 0.15) / 0.10, 0, 1)
    D = D * (1 - m) + np.minimum(D, Db) * m
    return xs, ys, hs, D


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    vox = float(sys.argv[sys.argv.index("--vox") + 1]) if "--vox" in sys.argv else 0.006
    d = np.load(src); v, f = d["v"].astype(np.float64), d["f"]
    used = np.unique(f)
    v2 = warp(v)
    xs, ys, hs, D = grid(v2, f, vox)
    np.savez_compressed(out, xs=xs, ys=ys, hs=hs, D=D,
                        knobs=json.dumps(dict(H_PINS=H_PINS, SX=SX, SYF=SYF, SYB=SYB, SMOOTH=SMOOTH, vox=vox, src=src)))
    print("grid", D.shape, "inside voxels", int((D < 0).sum()))
