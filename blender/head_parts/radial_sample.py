"""q41b: ray sampling of a generator head (run in Blender), four bands bottom -> top so the surface parameter is
monotone and nothing is seen edge-on:
  1. neck cylinder: horizontal rays from the vertical axis (x=0, y=yc) at z_lo..z_a
  2. jaw fan: rays from the axis point at z_jaw, elevation -e_low..0 (covers the jaw underside and the chin smoothly;
     horizontal rows met the jaw edge at a different row per column and made a staircase, q41b v3k)
  3. face cylinder: horizontal rays at z_jaw..z_cap (face, ears drop out: first hit = skin under the ear)
  4. skull cap: rays from the axis point at z_cap, elevation 0..elev_max
theta 0 = front (-y). Writes npz: R, COL (base colour at the hit), th, O (row origins), E (row elevations),
rowlen (physical row spacing), Z (front-hit z per row).

    exec(open(r"<repo>/blender/head_parts/radial_sample.py").read()); sample_head("head_base_v2b", OUT, ...)
"""
import math

import numpy as np


def sample_head(objname, out, yc=-0.01, z_lo=0.07, z_jaw=None, e_low=1.21, neck_r=0.085, z_cap=None, NU=192,
                NN=0, NF=34, NL=80, NC=40, elev_max=1.50):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    o = bpy.data.objects[objname]; me = o.data; me.calc_loop_triangles(); M = o.matrix_world
    V = [M @ v.co for v in me.vertices]; tris = [tuple(t.vertices) for t in me.loop_triangles]
    bvh = BVHTree.FromPolygons(V, tris)
    Vn = np.array([v[:] for v in V]); tv = np.array(tris)
    uvl = me.uv_layers.active.data
    tuv = np.array([[uvl[l].uv[:] for l in t.loops] for t in me.loop_triangles], np.float32)
    img = None
    for n in me.materials[0].node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED" and n.inputs["Base Color"].links:
            img = n.inputs["Base Color"].links[0].from_node.image
    w, h = img.size; px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
    zmin, zmax = Vn[:, 2].min(), Vn[:, 2].max()
    z_cap = zmax - 0.30 * (zmax - zmin) if z_cap is None else z_cap
    z_jaw = zmin + 0.27 * (zmax - zmin) if z_jaw is None else z_jaw
    z_a = z_jaw - neck_r * math.tan(e_low)
    th = np.linspace(-math.pi, math.pi, NU, endpoint=False)
    O, E = [], []
    for z in np.linspace(z_lo, z_a, NN, endpoint=False):
        O.append((0.0, yc, z)); E.append(0.0)
    for e in np.linspace(-e_low, 0, NF, endpoint=False):
        O.append((0.0, yc, z_jaw)); E.append(float(e))
    for z in np.linspace(z_jaw, z_cap, NL):
        O.append((0.0, yc, z)); E.append(0.0)
    for e in np.linspace(0, elev_max, NC + 1)[1:]:
        O.append((0.0, yc, z_cap)); E.append(float(e))
    O = np.array(O); E = np.array(E); NV = len(E)
    kind = np.array([0] * NN + [1] * NF + [2] * NL + [3] * NC)
    R = np.full((NV, NU), np.nan, np.float32); COL = np.zeros((NV, NU, 3), np.float32)
    for i in range(NV):
        oc = Vector(O[i].tolist()); ce = math.cos(E[i]); se = math.sin(E[i])
        for j, t in enumerate(th):
            d = Vector((math.sin(t) * ce, -math.cos(t) * ce, se))
            hit = bvh.ray_cast(oc, d)
            if hit[0] is None:
                continue
            loc, nrm, fi, dist = hit
            R[i, j] = dist
            a, b, c = Vn[tv[fi]]; v0 = b - a; v1 = c - a; v2 = np.array(loc[:]) - a
            d00 = v0 @ v0; d01 = v0 @ v1; d11 = v1 @ v1; d20 = v2 @ v0; d21 = v2 @ v1; den = d00 * d11 - d01 * d01
            bv = (d11 * d20 - d01 * d21) / den; bw = (d00 * d21 - d01 * d20) / den; bu = 1 - bv - bw
            uv = bu * tuv[fi, 0] + bv * tuv[fi, 1] + bw * tuv[fi, 2]
            COL[i, j] = px[int(np.clip(uv[1] * (h - 1), 0, h - 1)), int(np.clip(uv[0] * (w - 1), 0, w - 1)), :3]
    j0 = int(np.argmin(np.abs(th)))
    Z = O[:, 2] + np.sin(E) * R[:, j0]
    Rm = np.nanmean(R, axis=1)
    rowlen = np.zeros(NV)
    for i in range(NV):
        if kind[i] == 0:
            rowlen[i] = (z_a - z_lo) / NN
        elif kind[i] == 2:
            rowlen[i] = (z_cap - z_jaw) / (NL - 1)
        elif kind[i] == 1:
            rowlen[i] = Rm[i] * (e_low / NF)
        else:
            rowlen[i] = Rm[i] * (elev_max / NC)
    np.savez_compressed(out, R=R, COL=COL, th=th, O=O, E=E, rowlen=rowlen, Z=Z, kind=kind)
    return {"nan": int(np.isnan(R).sum()), "z_a": z_a, "z_jaw": z_jaw, "z_cap": z_cap, "rows": NV}
