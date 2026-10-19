"""q37: original MHS3-style hair for the VRoid-based head - replaces the VRoid hair (Hair_00_HAIR, HairBack_00_HAIR).

Sammy (2026-10-18): "change the hairstyle, i dont want anything the same as vroid". So the VRoid hair meshes and their
texture are deleted and a new hairstyle is built from scratch on the (warped) skull, reusing the clump generator of the
earlier procedural head (blender/newhead/hair_nh.py: swept blade-shaped clumps hugging the skull, lifted roots,
pointed tips, an under layer and a cap shell):

    /home/claude/bpyenv/bin/python mhs3_hair.py IN.glb OUT.glb [--style crop] [--knobs hk.json] [--png DIR]

- scalp = Face_00_SKIN + the head part of Body_00_SKIN (VRoid splits the skull there), ears left out (face shell
  outside |x| 0.086 below the temple) so the side clumps lie on the skull, not on the ears;
- the clumps are painted into their own texture (one atlas cell per clump: flat base, a darker root where the clump
  above shades it, thin dark rims, pale highlight strokes on some clumps), so the render pipeline (vroid_toon.toon on
  every *_HAIR material, outline, locked MHS3 spec) is unchanged - only the model changes;
- normals blended toward the skull centre (big toon shadow shapes, not one per clump), exported as custom normals.

Style "crop" (original, not VRoid's shaggy cut with sidelocks over the ears and a mullet, not Leo's sweep either):
short layered cut, fringe parted on his left and swept to his right in pointed clumps ending above the brows, a few
lifted clumps on the crown, sides cut above the ears (ears show - MHS3 Leo / Rudy), short tapered nape.
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

# ---- the clump generator of the procedural head, re-used (front turned to +Y: this GLB faces +Y) -------------------
import importlib.util
_spec = importlib.util.spec_from_file_location("hair_nh", os.path.join(REPO, "blender", "newhead", "hair_nh.py"))
H = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(H)


def _dir_py(a, p):
    a, p = math.radians(a), math.radians(p)
    return np.array([-math.sin(p) * math.sin(a), math.sin(p) * math.cos(a), math.cos(p)])


H._dir = _dir_py
H.SEG = 22          # m59r: smoother clumps (hair_nh 14 rings drew faceted bends and blunt-looking tips)
H.RING = 10

K = dict(
    base=(128, 90, 70),
    tip=(138, 98, 76),            # lighter toward the tips
    root_len=0.38, under_k=0.9,          # lit hair sRGB (the toon shadow multiplies it by the locked hair tint)
    root=(100, 68, 54),           # root shade where the clump above covers it
    rim=(82, 54, 42),             # thin dark rim along each clump edge
    hl=(196, 160, 132),           # highlight strokes
    under=(92, 62, 48),           # cap / under-layer
    hl_band=(0.22, 0.55), hl_share=0.0,
    rim_w=0.0,                   # share of the half-ring painted as rim
    radial=0.40,                  # normal blend toward the skull centre
    cap_off=0.0022,
    hairline_a=(0, 30, 55, 75, 100, 130, 160, 180),       # cap edge: polar deg (from the top) per azimuth
    hairline_p=(62, 70, 86, 92, 98, 108, 114, 118),      # (front high, down round the ears, low at the nape)
    style="crop", over_ears=False,
    ao_rays=24, ao_dist=0.02, ao_cone=0.6, ao_lo=0.25, ao_hi=0.85, ao_k=0.0,   # baked depth between clumps
    vol=0.45, wid=1.05, lng=1.0, base_k=0.3, th_k=0.55, taper_k=0.8, tip_k=1.4, bend_k=1.0,
    c_dz=0.0,                     # skull centre offsets (m)
    c_dy=0.0,
)
CELLS = 16
TEX = 2048


def _side_crop(sc, P, sgn):
    """q37 sides (m59w): long parallel clumps from near the top of the head straight down the side, ending in pointed
    tips - a sideburn in front of the ear, tips over the upper ear, longer ones behind it. m59v had short side clumps
    meeting fringe clumps that wrapped round the temple and top clumps sweeping across them: the side view read as
    crossing clumps, dark wedges and outlines in every direction (TypeSafe culprit patches / tips / outline 0.8-0.9;
    the VRoid hair it is compared with flows in one direction down the side)."""
    rng, J = H._rng(P.get("seed", 13) + (sgn > 0))
    dp = P.get("len", 0.0)
    out = []
    for a1, p1, w in ((48, 104, 0.062), (60, 112, 0.060), (72, 106, 0.064), (84, 98, 0.080), (96, 96, 0.084),
                      (108, 104, 0.080), (120, 112, 0.070), (132, 116, 0.066)):
        pe = p1 + (dp if a1 >= 80 else min(dp, 8.0))   # in front of the ear stay short (no VRoid-style sidelocks)
        if 80 <= a1 <= 112 and not K.get("over_ears"):   # over the ear: the clumps follow the skull (ears excluded), so a longer
            pe = min(pe, 97.0)               # one would run under the ear shell and the ear would poke through
        out.append(dict(a0=sgn * (a1 - 14) + J(2), p0=P.get("root", 12) + J(2), a1=sgn * a1 + J(2), p1=pe + J(2),
                        w=w, vol=P.get("vol", 0.008), flick=0.002, drop=0.002, base=0.002, bend=0.0, asym=-sgn,
                        taper=0.62, tip=1.3, th=0.30, shade=0.0, side=1, ease=1.3))
    return out


H.REGION_VARIANTS["SideL"]["crop"] = lambda sc, P: _side_crop(sc, P, 1)
H.REGION_VARIANTS["SideR"]["crop"] = lambda sc, P: _side_crop(sc, P, -1)


def _top_flow(sc, P):
    """m59s top: one flow from the crown whorl outward and DOWN, every clump ending over the roots of the side / back
    clumps and pointing the same way they run (hair_nh 'layered' sweeps forward and sideways across the side clumps:
    crossing tips and outlines - TypeSafe culprit hair_patches / outline / noisy 0.6-0.9 in the side views)."""
    rng, J = H._rng(P.get("seed", 5)); ca, cp = H.CROWN
    out = []
    n = P.get("count", 15)
    for i in range(n):
        a1 = P.get("a_from", 50) + (P.get("a_to", 310) - P.get("a_from", 50)) * i / (n - 1)   # default all round but the fringe
        a1 = (a1 + 180) % 360 - 180
        s_ = abs(math.sin(math.radians(a1)))
        out.append(dict(a0=ca + J(10) + 0.25 * a1 * (abs(a1) < 120), p0=P.get("p0", cp - 14) + J(2), a1=a1 + J(3),
                        p1=P.get("len", 64) + 10 * s_ + J(3), w=0.085, vol=0.020 * P.get("vol", 1.0), drop=0.006,
                        flick=0.0, base=0.004, bend=J(0.05), asym=rng.choice([-1, 1]), taper=0.5, tip=1.2, th=0.30,
                        shade=0.0, ease=1.0))
    return out


H.REGION_VARIANTS["Top"]["flow"] = _top_flow


def _back_flow(sc, P):
    """m59s back: one row of wide clumps from under the crown straight down to a tapered nape, the middle ones the
    longest, a little volume over the occiput (culprit back_flat 0.72 in the side view; hair_nh 'layers' had two
    rows of 18 narrow clumps whose tips and outlines read as patches)."""
    rng, J = H._rng(P.get("seed", 19)); ca, cp = H.CROWN
    dp = P.get("len", 0.0); n = P.get("count", 11)
    out = []
    for i in range(n):
        f = i / (n - 1) * 2 - 1                                   # -1 .. 1 across the back
        a1 = 180 + 72 * f + J(2)
        a1 = (a1 + 180) % 360 - 180
        out.append(dict(a0=ca + 30 * f + J(4), p0=cp + 4 + J(3), a1=a1, p1=124 + dp - 8 * f * f + J(2), w=0.095,
                        vol=P.get("vol", 0.030) * (1 - 0.75 * f * f), drop=0.004, flick=0.002, base=0.003,
                        bend=0.03 * f, asym=1 if f < 0 else -1, taper=0.5, tip=1.2, th=0.30, shade=0.0))
    return out


H.REGION_VARIANTS["Back"]["flow"] = _back_flow


def _front_crop(sc, P):
    """Parted fringe (hair_nh 'part') plus one clump laid over the part line so the cap does not show as a dark
    wedge (m59g: TypeSafe-free eyeball check, the gap read as a hole in the front and 3/4 views)."""
    out = H._front_part(sc, P)
    pa = P.get("part", 0.0)
    for da, dp, w in ((-6, -6, 0.090), (8, -2, 0.070)):
        out.append(dict(a0=pa - 8, p0=6, a1=pa + da, p1=P.get("len", 88) + dp, w=w, vol=0.032, drop=0.012, base=0.009,
                        bend=0.05, asym=1, taper=0.5, tip=1.2, th=0.32, shade=0.15, fringe=1))
    return out


H.REGION_VARIANTS["Front"]["crop"] = _front_crop


def recipe(style):
    if style == "crop":
        return dict(
            Front=("crop", {"part": 20, "len": K.get("front_len", 100), "count_l": 3, "reach_l": 36, "count_r": 5, "reach_r": 56, "width": 0.95,
                            "seed": 71}),
            Top=("flow", {"vol": 0.7, "p0": 14, "a_from": 125, "a_to": 235, "count": 8, "seed": 73}),
            SideL=("crop", {"len": 26, "seed": 75}), SideR=("crop", {"len": 26, "seed": 77}),
            Back=("flow", {"len": 34, "vol": 0.046, "seed": 79}), Base=("none", {}), attach=[])
    return H.RECIPES[style]


def mesh_obj(name):
    return next(o for o in bpy.data.objects if o.type == "MESH" and o.data.materials and o.data.materials[0]
                and name in o.data.materials[0].name)


class Scalp:
    """Outer skin of the skull (face + head part of the body, ears removed) for H.clump_path's ray casts."""
    def __init__(self):
        V, P = [], []
        names = [("Face_00_SKIN", 0.0), ("Body_00_SKIN", 1.47)]
        if any(o.type == "MESH" and o.data.materials and o.data.materials[0] and "Body_01_SKIN_HeadBack" in o.data.materials[0].name
               for o in bpy.data.objects):
            names.append(("Body_01_SKIN_HeadBack", 1.47))          # q39 from-scratch head: skull back + neck object
        for nm, zmin in names:
            o = mesh_obj(nm); M = o.matrix_world
            co = np.array([tuple(M @ v.co) for v in o.data.vertices])
            b = len(V); V += [tuple(c) for c in co]
            keep = np.ones(len(co), bool)
            if nm == "Face_00_SKIN":                            # the ears are separate islands of the face mesh
                par = list(range(len(co)))
                def f(i):
                    while par[i] != i:
                        par[i] = par[par[i]]; i = par[i]
                    return i
                for e in o.data.edges:
                    a_, b_ = f(e.vertices[0]), f(e.vertices[1])
                    if a_ != b_:
                        par[a_] = b_
                root = np.array([f(i) for i in range(len(co))])
                keep = root == np.bincount(root).argmax()
                self._keep = keep
            for p in o.data.polygons:
                vs = co[list(p.vertices)]
                if vs[:, 2].min() < zmin or not keep[p.vertices[0]]:
                    continue
                P.append(tuple(b + i for i in p.vertices))
        self.V = np.array(V); self.P = P
        self.tree = BVHTree.FromPolygons(V, P)
        # m59y: optionally let the clumps ride over the ears (ears in the radius tree, not in the cap): with the ears
        # exposed TypeSafe preferred the VRoid hair for ears / ear_shape in 4 of 6 views
        self.ray_tree = self.tree
        if K.get("over_ears"):
            o = mesh_obj("Face_00_SKIN"); M = o.matrix_world
            b = len(V); EP = [tuple(b + i for i in p.vertices) for p in o.data.polygons if not self._keep[p.vertices[0]]]
            V2 = V + [tuple(M @ v.co) for v in o.data.vertices]
            self.ray_tree = BVHTree.FromPolygons(V2, P + EP)
        self.cache = {}

    def radius(self, d):
        key = tuple(np.round(d, 3))
        if key not in self.cache:
            far = Vector(tuple(H.C + d * 0.5))
            hit = self.ray_tree.ray_cast(far, Vector(tuple(-d)), 0.5)
            r = (0.5 - hit[3]) if hit[0] is not None else 0.09
            if K.get("over_ears") and self.ray_tree is not self.tree:
                # a blade is ~6 cm wide but the path samples one direction: take the highest skin in a small cone so
                # a clump crossing the ear rides over the whole ear shell instead of cutting through it
                t1 = np.cross(d, [0.0, 0.0, 1.0]); t1 /= np.linalg.norm(t1) + 1e-9; t2 = np.cross(d, t1)
                for e in (t1, -t1, t2, -t2):
                    d2 = d + 0.16 * e; d2 /= np.linalg.norm(d2)
                    h2 = self.ray_tree.ray_cast(Vector(tuple(H.C + d2 * 0.5)), Vector(tuple(-d2)), 0.5)
                    if h2[0] is not None:
                        r = max(r, (0.5 - h2[3]) * float(d2 @ d))
            self.cache[key] = r
        return self.cache[key]


def skull_centre(sc):
    V = sc.V[sc.V[:, 2] > 1.45]
    top = V[:, 2].max(); chin = mesh_obj("Face_00_SKIN")
    # chin = lowest FRONT face vertex (q39: the from-scratch head's skin mesh carries the neck too)
    zc = min(w[2] for w in (chin.matrix_world @ v.co for v in chin.data.vertices) if w[1] > 0.04)
    S = top - zc
    z = zc + 0.56 * S
    band = V[np.abs(V[:, 2] - z) < 0.01]
    y = 0.5 * (band[:, 1].min() + band[:, 1].max())
    return np.array([0.0, y + K["c_dy"], z + K["c_dz"]]), S


def _lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


CLUMPS = []


def occlusion(objs):
    """m59l: per clump ring, the share of short rays (a cone round the outward radial, AO_DIST) cast from the top
    centre of the blade that hit other hair or the skin - roots under the clump above, the inner layer and the gaps
    between clumps get dark; the outer surface of the mass stays lit (TypeSafe m59k: hair_flat 0.60, hair_helmet
    0.85 - one flat lit mass). Rays start on the blade's top surface (ring vertex RING/4), so a clump never shadows
    itself. Returns {object name: per-vertex value} (each ring's value copied to its vertices)."""
    vs, ps = [], []
    for o in objs:
        b = len(vs); me = o.data
        vs += [tuple(v.co) for v in me.vertices]; ps += [tuple(b + i for i in p.vertices) for p in me.polygons]
    tree = BVHTree.FromPolygons(vs, ps)
    rng = np.random.default_rng(5)
    dirs = rng.normal(size=(K["ao_rays"], 3)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    RING = H.RING
    occ = {}
    for o in objs:
        if not o.name.startswith("MHS3_Hair_"):
            continue
        V = np.array([v.co[:] for v in o.data.vertices]); out = np.zeros(len(V))
        for cl in [c for c in CLUMPS if c["name"] == o.name]:
            for i in range(cl["nr"] + 1):
                vi = cl["b"] + i * RING + (RING // 4 if i < cl["nr"] else 0)
                p = V[vi]; n = p - H.C; n /= np.linalg.norm(n)
                hit = 0
                for d0 in dirs:
                    d = n + K["ao_cone"] * d0; d = d / np.linalg.norm(d)
                    h = tree.ray_cast(Vector(tuple(p + n * 0.0008)), Vector(tuple(d)), K["ao_dist"])
                    hit += h[0] is not None
                a = cl["b"] + i * RING
                out[a: a + (RING if i < cl["nr"] else 1)] = hit / len(dirs)
        occ[o.name] = out
    allv = np.concatenate(list(occ.values()))
    print("occlusion percentiles 10/50/90:", np.percentile(allv, [10, 50, 90]).round(2))
    return occ


def paint_cell(img, ci, c, streak, rng, occ_grid=None):
    """One clump's atlas cell: u across the ring (0..0.5 top surface, 0.5..1 underside), v root -> tip.
    m59j (TypeSafe screen m59i: VRoid hair preferred for 'clean' in every view - the diagonal stroke pattern read as
    scratches, the hard root band and dark undersides as torn patches): a smooth root -> tip gradient, the underside
    a little darker, a thin rim line, and on a few clumps one long thin highlight stroke along the clump."""
    n = TEX // CELLS; x0, y0 = (ci % CELLS) * n, (ci // CELLS) * n
    u = (np.arange(n) + 0.5) / n; v = (np.arange(n) + 0.5) / n
    U, Vv = np.meshgrid(u, v)
    base = np.asarray(K["base"], float); root = np.asarray(K["root"], float); tip = np.asarray(K["tip"], float)
    g = np.clip(Vv / K["root_len"], 0, 1)[..., None] ** 1.5
    col = root + (base - root) * g
    col = col + (tip - base) * np.clip((Vv - 0.6) / 0.4, 0, 1)[..., None]
    if c.get("shade", 0.0) < 0:                                # under-layer clumps: darker all along
        col = col * 0.92
    under = (U > 0.5)[..., None]
    col = np.where(under, col * K["under_k"], col)
    if occ_grid is not None:                                  # (nr+1 rings incl. tip) x RING, bilinear, u wraps
        G = occ_grid; nrr, rr = G.shape
        fi = np.clip(Vv * (nrr - 1), 0, nrr - 1); i0 = np.floor(fi).astype(int); i1 = np.minimum(i0 + 1, nrr - 1); ti = fi - i0
        fk = U * rr; k0 = np.floor(fk).astype(int) % rr; k1 = (k0 + 1) % rr; tk = fk - np.floor(fk)
        o_ = (G[i0, k0] * (1 - tk) + G[i0, k1] * tk) * (1 - ti) + (G[i1, k0] * (1 - tk) + G[i1, k1] * tk) * ti
        dark = np.clip((o_ - K["ao_lo"]) / (K["ao_hi"] - K["ao_lo"]), 0, 1)
        col = col * (1 - K["ao_k"] * dark)[..., None]
    rim = (np.abs(U - 0.0) < K["rim_w"] * 0.5) | (np.abs(U - 0.5) < K["rim_w"] * 0.5) | (U > 1 - K["rim_w"] * 0.5)
    col[rim] = K["rim"]
    if streak:
        lo, hi = K["hl_band"]; u0 = rng.uniform(0.18, 0.32); sl = rng.uniform(-0.15, 0.15)
        uc = u0 + sl * (Vv - lo)
        w = 0.011 * np.clip(np.sin(np.pi * (Vv - lo) / (hi - lo)), 0, 1)       # tapered at both ends
        m = (Vv > lo) & (Vv < hi) & (np.abs(U - uc) < w)
        col[m] = K["hl"]
    img[y0:y0 + n, x0:x0 + n] = col


def build_piece(name, clumps, sc, img, ci0, mat, rng):
    verts, faces, fuv = [], [], []
    RING, SEG = H.RING, H.SEG
    n = 1.0 / CELLS; pad = 0.5 / (TEX / CELLS)
    for j, c in enumerate(clumps):
        ci = ci0 + j
        streak = c.get("shade", 0.0) >= 0 and rng.random() < K["hl_share"]
        cu, cv = (ci % CELLS) * n, (ci // CELLS) * n
        UV = lambda u, v: (cu + pad + u * (n - 2 * pad), 1.0 - (cv + pad + v * (n - 2 * pad)))   # image row 0 = top
        rings = H.clump_rings(sc, c, K["vol"], K["wid"], K["lng"])
        b = len(verts)
        for ring in rings:
            verts += [tuple(p) for p in ring]
        nr = len(rings) - 1
        CLUMPS.append(dict(ci=ci, c=c, streak=streak, name=name, b=b, nr=nr))
        for i in range(nr - 1):
            for k in range(RING):
                a_ = b + i * RING + k; b_ = b + i * RING + (k + 1) % RING
                faces.append((a_, a_ + RING, b_ + RING, b_))
                t0, t1 = i / nr, (i + 1) / nr
                fuv.append((UV(k / RING, t0), UV(k / RING, t1), UV((k + 1) / RING, t1), UV((k + 1) / RING, t0)))
        tip = b + nr * RING
        for k in range(RING):
            a_ = b + (nr - 1) * RING + k; b_ = b + (nr - 1) * RING + (k + 1) % RING
            faces.append((a_, tip, b_))
            t0 = (nr - 1) / nr
            fuv.append((UV(k / RING, t0), UV((k + 0.5) / RING, 1.0), UV((k + 1) / RING, t0)))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for p, uvs in zip(me.polygons, fuv):
        p.use_smooth = True
        for li, uv in zip(p.loop_indices, uvs):
            uvl.data[li].uv = uv
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    radial_normals(o)
    return o, ci0 + len(clumps)


def radial_normals(o):
    me = o.data
    V = np.array([v.co[:] for v in me.vertices])
    N = np.empty(len(V) * 3); me.vertices.foreach_get("normal", N); N = N.reshape(-1, 3)
    R = V - H.C; R /= np.linalg.norm(R, axis=1, keepdims=True)
    nn = K["radial"] * R + (1 - K["radial"]) * N; nn /= np.linalg.norm(nn, axis=1, keepdims=True)
    me.normals_split_custom_set_from_vertices([tuple(x) for x in nn])


def build_cap(sc, mat):
    """Shell over the scalp above the hairline (face + body faces pushed out along their normals)."""
    V = sc.V; rel = V - H.C
    p = np.degrees(np.arccos(np.clip(rel[:, 2] / np.linalg.norm(rel, axis=1), -1, 1)))
    a = np.degrees(np.arctan2(-rel[:, 0], rel[:, 1]))             # 0 = front (+Y)
    limit = np.interp(np.abs(a), K["hairline_a"], K["hairline_p"])
    inside = p < limit
    keep = [pl for pl in sc.P if all(inside[list(pl)])]
    used = sorted({i for pl in keep for i in pl}); rm = {v: k for k, v in enumerate(used)}
    me = bpy.data.meshes.new("tmpcap"); me.from_pydata([tuple(V[i]) for i in used], [], [tuple(rm[i] for i in pl) for pl in keep])
    me.update()
    N = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("normal", N); N = N.reshape(-1, 3)
    R = np.array([tuple(V[i]) for i in used]) - H.C; R /= np.linalg.norm(R, axis=1, keepdims=True)
    N = np.where((N * R).sum(1, keepdims=True) < 0, -N, N)        # outward
    co = np.array([tuple(V[i]) for i in used]) + N * K["cap_off"]
    me.vertices.foreach_set("co", co.astype(np.float32).ravel()); me.update()
    if (np.array([p_.normal[:] for p_ in me.polygons]) * (np.array([p_.center[:] for p_ in me.polygons]) - H.C)).sum(1).mean() < 0:
        me.flip_normals()
    uvl = me.uv_layers.new(name="UVMap")
    for d in uvl.data:
        d.uv = (0.5 / CELLS, 1.0 - (CELLS - 0.5) / CELLS)           # last atlas cell = flat under colour
    for p_ in me.polygons:
        p_.use_smooth = True
    me.name = "MHS3_HairCap"; me.materials.append(mat)
    o = bpy.data.objects.new("MHS3_HairCap", me); bpy.context.scene.collection.objects.link(o)
    return o


def coverage_map(sc):
    """What a ray from outside toward the skull centre hits first, per (azimuth, polar): '#' clump, 'c' cap (flat
    under colour shows), '.' skin (bald), ' ' nothing. Rows polar 0..120, columns azimuth -180..180 (0 = front,
    + = his left)."""
    trees = {}
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith("MHS3_Hair"):
            me = o.data
            trees[o.name] = BVHTree.FromPolygons([tuple(o.matrix_world @ v.co) for v in me.vertices],
                                                 [tuple(p.vertices) for p in me.polygons])
    rows = []
    for p in range(0, 121, 4):
        row = ""
        for a in range(-180, 181, 6):
            d = H._dir(a, p); o_ = Vector(tuple(H.C + d * 0.4)); dd = Vector(tuple(-d))
            best, ch = 9.0, " "
            h = sc.tree.ray_cast(o_, dd, 0.5)
            if h[0] is not None:
                best, ch = h[3], "."
            for nm, t in trees.items():
                h = t.ray_cast(o_, dd, 0.5)
                if h[0] is not None and h[3] < best:
                    best, ch = h[3], ("c" if "Cap" in nm else "#")
            row += ch
        rows.append("%3d %s" % (p, row))
    # thickness: outermost hair minus skull, per zone (q37 TypeSafe culprit: hair_bulky)
    zones = {"crown p<35": lambda a, p: p < 35, "top-side 35-70": lambda a, p: 35 <= p < 70 and 40 < abs(a) < 140,
             "temple 70-100": lambda a, p: 70 <= p < 100 and 40 < abs(a) < 80, "back 60-110": lambda a, p: 60 <= p < 110 and abs(a) > 140,
             "front 40-80": lambda a, p: 40 <= p < 80 and abs(a) < 30}
    th = {z: [] for z in zones}
    for p in range(0, 121, 4):
        for a in range(-180, 181, 6):
            d = H._dir(a, p); o_ = Vector(tuple(H.C + d * 0.4)); dd = Vector(tuple(-d))
            hs = sc.tree.ray_cast(o_, dd, 0.5)
            hh = [t.ray_cast(o_, dd, 0.5) for nm, t in trees.items() if "Cap" not in nm]
            hh = [h[3] for h in hh if h[0] is not None]
            if hs[0] is None or not hh:
                continue
            for z, f in zones.items():
                if f(a, p):
                    th[z].append(hs[3] - min(hh))
    print("hair thickness over the skull (mm, median / p90):",
          {z: (round(1000 * float(np.median(v)), 1), round(1000 * float(np.percentile(v, 90)), 1)) for z, v in th.items() if v})
    print("    " + "".join("|" if a % 90 == 0 else " " for a in range(-180, 181, 6)))
    print("\n".join(rows))


def main():
    src, out = sys.argv[1:3]
    arg = lambda n_, d=None: sys.argv[sys.argv.index(n_) + 1] if n_ in sys.argv else d
    if arg("--knobs"):
        K.update(json.load(open(arg("--knobs"))))
    if arg("--style"):
        K["style"] = arg("--style")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.import_scene.gltf(filepath=src)
    gone = [o for o in bpy.data.objects if o.type == "MESH" and o.data.materials and o.data.materials[0]
            and "_HAIR" in o.data.materials[0].name]
    print("removing VRoid hair:", [o.data.materials[0].name for o in gone], sum(len(o.data.vertices) for o in gone), "verts")
    for o in gone:
        bpy.data.objects.remove(o, do_unlink=True)
    for img in [i for i in bpy.data.images if i.users == 0]:
        bpy.data.images.remove(img)
    sc = Scalp()
    H.C, S = skull_centre(sc)
    print("skull centre", H.C.round(4), "head height", round(S, 4))
    rng = np.random.default_rng(37)
    img = np.zeros((TEX, TEX, 3)); img[:] = K["under"]
    pimg = bpy.data.images.new("MHS3_Hair_00_HAIR", TEX, TEX, alpha=True)
    mat = bpy.data.materials.new("MHS3_Hair_00_HAIR")              # "HAIR" -> vroid_toon gives it the locked hair toon
    mat.use_nodes = True; nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = pimg; tx.interpolation = "Linear"
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    spec = H.recipe_spec(sc, recipe(K["style"]))
    for clumps, _t in spec.values():                 # q37: the hair sat 5-8 mm thicker than the VRoid hair everywhere
        for c in clumps:                             # (TypeSafe culprit hair_bulky 0.6) - lower every clump's root
            c["base"] = c.get("base", 0.0) * K["base_k"]
            c["th"] = c.get("th", 0.32) * K["th_k"]     # blade thickness (hair_nh: ~0.3 x width = 17 mm on a side clump)
            if c.get("profile", "blade") == "blade":    # m59r: longer, finer points (culprit hair_tips: torn-looking ends)
                c["taper"] = c.get("taper", 0.5) * K["taper_k"]
                c["tip"] = c.get("tip", 1.1) * K["tip_k"]
            c["bend"] = c.get("bend", 0.0) * K["bend_k"]
    ci = 0; made = []
    for piece, (clumps, ties) in spec.items():
        o, ci = build_piece("MHS3_Hair_" + piece, clumps, sc, img, ci, mat, rng)
        made.append((o.name, len(clumps), len(o.data.vertices)))
    assert ci < CELLS * CELLS - 1, "too many clumps for the atlas"
    cap = build_cap(sc, mat)
    made.append((cap.name, 0, len(cap.data.vertices)))
    skin = bpy.data.objects.new("tmp_skin", bpy.data.meshes.new("tmp_skin"))
    skin.data.from_pydata([tuple(v) for v in sc.V], [], sc.P)
    objs = [bpy.data.objects[m[0]] for m in made] + [skin]
    occ = occlusion(objs) if K["ao_k"] > 0 else {}
    bpy.data.objects.remove(skin)
    for cl in CLUMPS:
        g = None
        if cl["name"] in occ:
            o_ = occ[cl["name"]]; RING = H.RING
            rows = [o_[cl["b"] + i * RING: cl["b"] + (i + 1) * RING] for i in range(cl["nr"])]
            rows.append(np.full(RING, o_[cl["b"] + cl["nr"] * RING]))
            g = np.array(rows)
        paint_cell(img, cl["ci"], cl["c"], cl["streak"], rng, g)
    rgba = np.concatenate([img / 255.0, np.ones((TEX, TEX, 1))], axis=2)[::-1]   # byte image: sRGB values; rows bottom-up
    pimg.pixels.foreach_set(rgba.astype(np.float32).ravel())
    pimg.file_format = "PNG"; pimg.pack()
    if arg("--png"):
        from PIL import Image
        Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(arg("--png"), "hair_atlas.png"))
    print("built", made, "clumps", ci)
    if "--map" in sys.argv:
        coverage_map(sc)
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_image_format="AUTO")
    print("wrote", out)


if __name__ == "__main__":
    main()
