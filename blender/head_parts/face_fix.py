"""q41c: fix a generator head's face in Blender without bending its geometry around (run in Blender).

The Hunyuan head from Sammy's reference set (69bade68 tile 3) has a clean skull, ears and neck but an invented bulbous,
upturned nose and puffy lips. Deforming them in place (setbacks, rotations) left creases and a frown (q41c HEAD_fix,
rejected by eye although every rule passed). What worked (HEAD_v4c):
  1. decimate the raw head to ~30K tris (Decimate COLLAPSE, triangulate) - smoothing is ineffective at 500K;
  2. flatten(): vectorised Laplacian smoothing inside soft ellipses on the face front (nose+mouth zone, brow band),
     wide falloff (0.8) so no rim crease;
  3. taubin(): light shrink-free smoothing everywhere (clears decimation zigzags);
  4. nose_add(): a parametric nose (bridge rising root -> tip, rounded tip, short underside to the subnasale,
     Gaussian width) displaced along -y on the front; its 4 numbers are searched so that the rulebook profile
     P1-P6 and the nose rules N1/N2 (head_probe.py) all land within tolerance and the tip stays at nose height.
World space: +Z up, front = -Y (bake the import rotation into the mesh first: me.transform(matrix_world)).
"""
import itertools

import numpy as np

TARGETS = {0.3: (0.053, 0.01), 0.4: (0.039, 0.008), 0.5: (0.05, 0.01), 0.6: (0.052, 0.012),
           0.8: (0.045, 0.01), 0.9: (0.088, 0.01)}


def _copy(src, dst):
    import bpy
    s = bpy.data.objects[src]
    if dst in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[dst])
    o = s.copy(); o.data = s.data.copy(); o.name = dst; bpy.context.scene.collection.objects.link(o)
    return o


def _edges(me):
    E = np.empty(len(me.edges) * 2, int); me.edges.foreach_get("vertices", E); return E.reshape(-1, 2)


def flatten(src, dst, regions=((0.41, 0.14, 0.14, 0.8), (0.60, 0.20, 0.08, 0.8), (0.655, 0.19, 0.04, 0.8)),
            iters=200, lam=0.6, front_y=-0.22):
    o = _copy(src, dst); me = o.data; n = len(me.vertices)
    co = np.empty(n * 3); me.vertices.foreach_get("co", co); P = co.reshape(-1, 3).copy()
    E = _edges(me); deg = np.bincount(E.ravel(), minlength=n).astype(float)
    wt = np.zeros(n)
    for cz, rx, rz, fo in regions:
        r = np.hypot(P[:, 0] / rx, (P[:, 2] - cz) / rz); w = np.clip((1 - r) / fo, 0, 1); w = w * w * (3 - 2 * w)
        wt = np.maximum(wt, w * (P[:, 1] < front_y))
    act = wt > 0
    for _ in range(iters):
        S = np.zeros_like(P); np.add.at(S, E[:, 0], P[E[:, 1]]); np.add.at(S, E[:, 1], P[E[:, 0]])
        avg = S / np.maximum(deg, 1)[:, None]
        P[act] += (avg[act] - P[act]) * (lam * wt[act])[:, None]
    me.vertices.foreach_set("co", P.ravel()); me.update(); return o


def taubin(name, iters=10, lam=0.5, mu=-0.53):
    import bpy, bmesh
    o = bpy.data.objects[name]; me = o.data; n = len(me.vertices)
    co = np.empty(n * 3); me.vertices.foreach_get("co", co); P = co.reshape(-1, 3)
    E = _edges(me); deg = np.bincount(E.ravel(), minlength=n).astype(float)
    bm = bmesh.new(); bm.from_mesh(me); bnd = np.zeros(n, bool); bnd[[v.index for v in bm.verts if v.is_boundary]] = True; bm.free()
    for _ in range(iters):
        for f in (lam, mu):
            S = np.zeros_like(P); np.add.at(S, E[:, 0], P[E[:, 1]]); np.add.at(S, E[:, 1], P[E[:, 0]])
            d = S / np.maximum(deg, 1)[:, None] - P; d[bnd] = 0; P += f * d
    me.vertices.foreach_set("co", P.ravel()); me.update()


def nose_add(src, dst, z_root=0.555, z_tip=0.455, z_sub=0.425, h_tip=0.035, w_root=0.012, w_tip=0.024):
    o = _copy(src, dst); me = o.data
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); W = co.reshape(-1, 3)
    z = W[:, 2]
    t = np.clip((z_root - z) / (z_root - z_tip), 0, 1); bridge = h_tip * (0.25 + 0.75 * (t * t * (3 - 2 * t)))
    u = np.clip((z_tip - z) / (z_tip - z_sub), 0, 1); under = h_tip * (1 - u * u * (3 - 2 * u))
    h = np.where(z >= z_tip, bridge, under) * (z <= z_root + 0.02) * (z >= z_sub - 0.005)
    tp = np.clip((z_root + 0.02 - z) / 0.03, 0, 1); h *= tp * tp * (3 - 2 * tp)
    w = w_root + (w_tip - w_root) * np.clip((z_root - z) / (z_root - z_sub), 0, 1)
    W[:, 1] -= h * np.exp(-0.5 * (W[:, 0] / w) ** 2) * np.clip((-W[:, 1] - 0.28) / 0.04, 0, 1)
    me.vertices.foreach_set("co", W.ravel()); me.update(); return o


def fit_nose(src, dst, probe, grid=None):
    """probe = head_probe module dict (measure, nose). Returns the best (max err/tol, rms, params, measures)."""
    import bpy
    grid = grid or dict(h=(0.028, 0.032, 0.036), zt=(0.45, 0.455, 0.46), zs=(0.435, 0.44, 0.445), zr=(0.54, 0.555))
    res = []
    for h, zt, zs, zr in itertools.product(grid["h"], grid["zt"], grid["zs"], grid["zr"]):
        if zs >= zt - 0.008:
            continue
        nose_add(src, "_nose_try", z_root=zr, z_tip=zt, z_sub=zs, h_tip=h)
        m = probe["measure"]("_nose_try"); n = probe["nose"]("_nose_try")
        e = [abs(m["P"][k] - v) / t for k, (v, t) in TARGETS.items()] + [abs(n["N1_down_deg"] - 9) / 6,
                                                                         abs(n["N2_tip_deg"] - 108) / 6]
        if not 0.44 <= m["tip"][0] <= 0.47:
            e.append(9)
        res.append((max(e), float(np.sqrt(np.mean(np.square(e)))), dict(h_tip=h, z_tip=zt, z_sub=zs, z_root=zr), m, n))
    bpy.data.objects.remove(bpy.data.objects["_nose_try"])
    res.sort(key=lambda r: (r[0], r[1]))
    nose_add(src, dst, **res[0][2])
    return res[0]
