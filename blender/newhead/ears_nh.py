"""Anime ears as their own sculpted shells, joined into CHR_Body (iter23).

Sammy: "the ears look bad". The old ear was the head patch pushed out - a flat plate with a dent. This builds the ear
from the drawing rules (Proko / Life Drawing Academy / Clip Studio ear guides, otoplasty measurements):
- top at the brow line, lobe at the nose base; long axis leaning back ~17 deg, parallel to the jaw's back edge
- width ~0.55 x height; rim (helix) rolled over at the top and back, open at the front (tragus side)
- a Y-shaped antihelix ridge inside the rim, a concha bowl in the middle third, a solid lobe in the bottom third
- stands off the skull at the back edge (~0.2 x height at the top, ~0.3 at the middle), hinged at the front
The shell is a radial mesh (rings x spokes) with a height field across the ear plane, then a thin back skin."""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import face_features as FF
import face_layout as L

N_R, N_T = 6, 20   # iter26: dataset topology - whole anime heads median 2.8k faces; the old 9 x 40 ear pair alone was 1.5k
LEAN = math.radians(17.0)          # long axis leans back
FLARE = math.radians(24.0)         # angle between the ear and the side of the head
THICK = 0.0026
EAR_GRID = 6           # iter26: O-grid, 6 x 6 centre + 4 rings of 24 (132 quads per ear face)


def _outline(t, H, W):
    """Ear outline point for spoke angle t (0 = back, pi/2 = top, pi = front, 3pi/2 = bottom), ear-plane (a, b)
    with a forward (toward the face) and b up. Wider at the top, narrow lobe, flattened front."""
    c, s = math.cos(t), math.sin(t)
    b = s * H / 2
    w = W / 2 * (0.62 + 0.38 * (s + 1) / 2)            # narrow lobe, broad top
    a = -c * w
    if c < 0:                                           # front edge: straighter (attached to the head)
        a *= 0.80
    return a, b


def _height(r, t, a, b, H, W):
    """Out-of-plane relief (towards the viewer of the ear's outer face)."""
    c, s = math.cos(t), math.sin(t)
    front = max(0.0, -c) ** 2 * (1 - max(0.0, -s))     # front side (tragus), not the lobe
    rim_mask = 1.0 - front
    lobe = max(0.0, -s) ** 3                           # bottom third
    h = 0.0
    h += 0.0024 * math.exp(-((r - 0.88) / 0.09) ** 2) * rim_mask * (1 - 0.6 * lobe)      # helix roll
    h -= 0.0010 * math.exp(-((r - 0.74) / 0.05) ** 2) * rim_mask * (1 - lobe)            # scapha groove
    ah = math.exp(-((r - 0.56) / 0.08) ** 2) * (1 - lobe) * (1 - front)                   # antihelix
    fork = math.exp(-((t - math.radians(70)) / 0.45) ** 2)                               # its upper fork
    h += 0.0016 * ah * (1 + 0.5 * fork)
    # concha bowl, slightly forward of centre in the middle third
    h -= 0.0042 * math.exp(-(((a - 0.10 * W) / (0.24 * W)) ** 2 + ((b + 0.02 * H) / (0.20 * H)) ** 2))
    # tragus: a small bump on the front edge at mid height
    h += 0.0016 * math.exp(-(((a - 0.40 * W) / (0.10 * W)) ** 2 + ((b + 0.05 * H) / (0.08 * H)) ** 2))
    h += 0.0010 * lobe * (1 - r)                       # fuller lobe
    # toon shadow shapes (MHS3 ear: the concha and the groove under the rim read as one warm dark shape)
    conc = math.exp(-(((a - 0.10 * W) / (0.24 * W)) ** 2 + ((b + 0.00 * H) / (0.24 * H)) ** 2))
    groove = math.exp(-((r - 0.76) / 0.045) ** 2) * rim_mask * (1 - lobe) * max(0.0, s + 0.35)
    _height.dark = max(conc, 0.9 * groove)
    return h


def build_one(s, H=None, W=None):
    """s = +1 his left, -1 his right. Returns a bmesh in body space."""
    H = H or (FF.EAR_TOP - FF.EAR_BOT) * 1.02
    W = W or H * 0.56
    zc = (FF.EAR_TOP + FF.EAR_BOT) / 2
    yc = (FF.EAR_FRONT + FF.EAR_BACK) / 2 + 0.0005
    xs = abs(FF.surface_x(yc, zc, s))
    bm = bmesh.new()
    dl = bm.verts.layers.float.new("ear_dark")
    # iter26: the shell is an O-grid: a square quad grid in the middle (concha and antihelix) and quad rings out to the
    # outline (helix). All quads, no radial pole and no 180-degree corner quads (dataset topology check).
    ca, sa = math.cos(LEAN), math.sin(LEAN)
    M, RINGS, S0 = EAR_GRID, 4, 0.55

    def place(du, dv):
        r = min(1.0, math.hypot(du, dv))
        t = math.atan2(dv, -du) % (2 * math.pi)       # 0 = back (a < 0), pi/2 = top
        a0, b0 = _outline(t, H, W)
        a, b = a0 * r, b0 * r
        h = _height(max(r, 1e-3), t, a, b, H, W)
        aa = a * ca + b * sa
        bb = -a * sa + b * ca
        y = yc - aa
        z = zc + bb
        out = 0.0015 + max(0.0, (W / 2 - aa)) * math.tan(FLARE) * 0.95 + h
        vv = bm.verts.new((s * (abs(FF.surface_x(y, z, s)) + out), y, z))
        vv[dl] = _height.dark
        return vv

    def addq(q):
        bm.faces.new(q if s > 0 else q[::-1])

    # iter n21: the O-grid is laid out directly in the ear plane (a forward, b up), where the ear is ~0.5 as wide as
    # tall: a 4 x 8 rectangle in the middle (near-square cells there), 4 rings out to the outline, the outline points
    # spaced by arc length; then a 2-D relax that pulls every quad toward a square (Procrustes target, as topo_relax)
    # with the outline fixed. Placement maps (a, b) back to the ring/spoke (r, t) the relief function uses.
    MU, MV, RINGS = 4, 8, 4
    ts = np.linspace(0, 2 * math.pi, 2000, endpoint=False)
    OL = np.array([_outline(t, H, W) for t in ts])
    seg = np.linalg.norm(np.roll(OL, -1, 0) - OL, axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
    amax, bmax = np.abs(OL[:, 0]).max(), np.abs(OL[:, 1]).max()
    ia, ib = 0.42 * amax, 0.50 * bmax
    pts, faces2, gid = [], [], {}
    for i in range(MU + 1):
        for j in range(MV + 1):
            gid[i, j] = len(pts); pts.append([-ia + 2 * ia * i / MU, -ib + 2 * ib * j / MV])
    for i in range(MU):
        for j in range(MV):
            faces2.append((gid[i, j], gid[i + 1, j], gid[i + 1, j + 1], gid[i, j + 1]))
    sq = [(i, 0) for i in range(MU)] + [(MU, j) for j in range(MV)] + [(i, MV) for i in range(MU, 0, -1)] + [(0, j) for j in range(MV, 0, -1)]
    prev = [gid[k] for k in sq]
    n_ = len(prev)
    # outline points: start at the direction of the first square corner, even arc length
    t0 = math.atan2(pts[prev[0]][1] / bmax, -pts[prev[0]][0] / amax) % (2 * math.pi)
    L0 = np.interp(t0, ts, cum[:-1]); tot = cum[-1]
    # walk direction: the square goes -a..+a along the bottom (i rises = a rises = toward the front, t falls from 3pi/2)
    outl = []
    for m in range(n_):
        Lm = (L0 - tot * m / n_) % tot
        k = int(np.searchsorted(cum, Lm, side="right") - 1) % len(ts)
        fr = (Lm - cum[k]) / max(seg[k], 1e-12)
        outl.append(OL[k] + (OL[(k + 1) % len(ts)] - OL[k]) * fr)
    for k in range(1, RINGS + 1):
        f = k / RINGS
        ring = []
        for m, q in enumerate(prev):
            u0, v0 = pts[gid[sq[m]]]
            ue, ve = outl[m]
            ring.append(len(pts)); pts.append([u0 + (ue - u0) * f, v0 + (ve - v0) * f])
        for m in range(n_):
            faces2.append((prev[m], prev[(m + 1) % n_], ring[(m + 1) % n_], ring[m]))
        prev = ring
    P2 = np.array(pts); fixed = np.zeros(len(P2), bool); fixed[prev] = True
    Q = np.array(faces2)
    # orientation: make every quad CCW in (a, b)
    ar = lambda P: 0.5 * np.sum(P[:, :, 0] * np.roll(P[:, :, 1], -1, 1) - np.roll(P[:, :, 0], -1, 1) * P[:, :, 1], 1)
    flip = ar(P2[Q]) < 0
    Q[flip] = Q[flip][:, ::-1]
    nbr = [[] for _ in range(len(P2))]
    for fc in Q:
        for t in range(4):
            nbr[fc[t]] += [fc[(t + 1) % 4], fc[(t - 1) % 4]]
    for _ in range(60):
        P2 = np.where(fixed[:, None], P2, np.array([P2[nb].mean(0) for nb in nbr]))
    sqr = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], float)
    cnt = np.bincount(Q.ravel(), minlength=len(P2)).astype(float)
    for _ in range(300):
        P = P2[Q]; c = P.mean(1, keepdims=True); D = P - c
        num = np.sum(sqr[None, :, 0] * D[:, :, 1] - sqr[None, :, 1] * D[:, :, 0], 1)
        den = np.sum(sqr[None, :, 0] * D[:, :, 0] + sqr[None, :, 1] * D[:, :, 1], 1)
        th = np.arctan2(num, den); sc = np.sqrt(np.sum(D ** 2, (1, 2)) / 8.0)
        ct, st_ = np.cos(th), np.sin(th)
        tgt = c + np.stack([sqr[None, :, 0] * ct[:, None] - sqr[None, :, 1] * st_[:, None],
                            sqr[None, :, 0] * st_[:, None] + sqr[None, :, 1] * ct[:, None]], -1) * sc[:, None, None]
        acc = np.zeros_like(P2); np.add.at(acc, Q.ravel(), tgt.reshape(-1, 2))
        goal = acc / np.maximum(cnt, 1)[:, None]
        lap = np.array([P2[nb].mean(0) for nb in nbr])
        P2n = P2 + 0.5 * (0.85 * (goal - P2) + 0.15 * (lap - P2))
        # outline vertices slide along the outline (nearest point of the dense outline), never off it
        oi = np.nonzero(fixed)[0]
        dd = ((P2n[oi][:, None, :] - OL[None]) ** 2).sum(-1)
        P2n[oi] = OL[dd.argmin(1)]
        P2 = P2n
    build_one.last2d = (P2, Q)

    def place_ab(a, b):
        # (a, b) -> spoke t and fraction r of the outline along it
        t = math.atan2(b / bmax, -a / amax) % (2 * math.pi)
        oa, ob = _outline(t, H, W)
        r = min(1.0, math.hypot(a, b) / max(math.hypot(oa, ob), 1e-9))
        h = _height(max(r, 1e-3), t, a, b, H, W)
        aa = a * ca + b * sa
        bb = -a * sa + b * ca
        y = yc - aa
        z = zc + bb
        out = 0.0015 + max(0.0, (W / 2 - aa)) * math.tan(FLARE) * 0.95 + h
        vv = bm.verts.new((s * (abs(FF.surface_x(y, z, s)) + out), y, z))
        vv[dl] = _height.dark
        return vv
    vv_ = [place_ab(float(u), float(v)) for u, v in P2]
    for fc in Q:
        addq(tuple(vv_[t] for t in fc))
    # back skin: duplicate pushed toward the head, joined at the rim
    front_faces = list(bm.faces)
    bmesh.ops.recalc_face_normals(bm, faces=front_faces)
    # make the outer face point away from the head (+x for s > 0)
    avg_n = sum((f.normal for f in front_faces), Vector()) / len(front_faces)
    if avg_n.x * s < 0:
        bmesh.ops.reverse_faces(bm, faces=front_faces)
    ret = bmesh.ops.solidify(bm, geom=front_faces, thickness=THICK)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = True
    return bm


def build(body):
    """Flatten the old head-patch ear into the skull and join the new shells into the body."""
    me_list = []
    for s in (1, -1):
        bm = build_one(s)
        me = bpy.data.meshes.new("CHR_Ear_tmp")
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new("CHR_Ear_tmp", me)
        bpy.context.scene.collection.objects.link(ob)
        for m in body.data.materials:
            me.materials.append(m)
        me_list.append(ob)
    with bpy.context.temp_override(active_object=body, selected_editable_objects=[body] + me_list,
                                   object=body, selected_objects=[body] + me_list):
        bpy.ops.object.join()
    return len(me_list)
