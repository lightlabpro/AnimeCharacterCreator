"""New head, built from scratch (iter30).

Shape: the low-frequency mean of 14 verified dataset anime heads (mean_head.py), chin at z=0, skull top at z=1
(units of head height H, forward -Y), with an under-jaw plane and a neck tube added where the radial map is not
defined. Topology: an original low-poly quad cage (subdivided cube, warped so the face gets more cells), eye
openings and the mouth as O-grid rings cut into the front face, a neck tube; Catmull-Clark level 2 gives the final
surface. The cage is fitted so its subdivision LIMIT surface lies on the target (Jacobi iterations).

python3 build_head.py OUT.npz [--levels 2]
"""
import math, sys, os
import numpy as np
import bpy, bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import surf

NX, NY, NZ = 14, 8, 14            # cube cells across x, y (depth), z
FRONT_ANGLE = math.radians(52)   # the front face holds the whole face
BACK_ANGLE = math.radians(100)   # the back face covers the back of the skull with large cells
LEVELS = 1

# dataset landmarks (fractions of H above the chin; forward = -y), from mean_head / topology_dataset
EYE_Z, EYE_X, EYE_HW, EYE_HH = 0.48, 0.175, 0.090, 0.050      # eye centre height, x, half width, half height
MOUTH_Z, MOUTH_HW = 0.165, 0.105
NOSE_Z, NOSE_FWD = 0.246, 0.470
CHIN_Y = -0.386
NECK_R, NECK_Y = 0.20, 0.03                                   # neck radius and centre (depth), H units
NECK_ON = False   # n29: the neck column is the analytic tube only; rays from C behind the neck hit the column
#                   far down and stacked back-wall cells inside the tube (a hidden fold sheet)
NAPE_Z = 0.20                                                 # skull base behind the neck (H)
EAR_TOP, EAR_BOT, EAR_FRONT, EAR_BACK = 0.56, 0.31, 0.07, 0.22  # ear box (H; y front/back of the head centre)
EYEBALL_R = 0.105                                             # eyeball radius (H)
NOSE_GAIN = 0.065                                            # nose ridge height at the tip (H)


# ------------------------------------------------------------------ target surface
def target_r_map():
    r = surf.R.copy()
    r = surf.smooth(r, 10)          # low frequency only: the averaged features are mush; the cage makes the features
    return r


R_LOW = None


def under_jaw_z(y):
    """Under-jaw line in side view (H units): flat under the chin, rising toward the jaw angle below the ear."""
    y0, y1 = CHIN_Y + 0.06, 0.03
    t = np.clip((y - y0) / (y1 - y0), 0, 1)
    return 0.0 + t * t * (3 - 2 * t) * 0.22


def g2(x, z, cx, cz, sx, sz):
    return np.exp(-(((x - cx) / sx) ** 2 + ((z - cz) / sz) ** 2))


def feature_bumps(x, z, r0):
    """Forward offsets (H units) for the authored facial forms, placed at the dataset landmarks: a nose ridge to the
    measured nose-tip height and depth, soft eye sockets, a brow ridge, the lips and the philtrum."""
    ax = np.abs(x)
    d = np.zeros_like(x)
    # nose: ridge from the nasion down to the tip, narrow, growing toward the tip
    t = np.clip((0.40 - z) / (0.40 - NOSE_Z), 0, 1)
    ridge = np.exp(-(x / (0.026 + 0.014 * t)) ** 2)
    prof = np.where(z >= NOSE_Z, t ** 1.4, np.exp(-((z - NOSE_Z) / 0.024) ** 2))   # continuous at the tip, tucks in (n30: 0.017 was finer than the mesh, jagged underside)
    d += NOSE_GAIN * prof * ridge
    d += 0.010 * g2(ax, z, 0.040, NOSE_Z + 0.005, 0.020, 0.018)                      # nostril wings
    # eye sockets and brow
    d -= 0.016 * g2(ax, z, EYE_X, EYE_Z, EYE_HW * 1.35, EYE_HH * 1.9)
    d += 0.004 * g2(ax, z, EYE_X * 0.9, EYE_Z + EYE_HH * 2.2, EYE_HW * 1.4, 0.035)
    # lips and philtrum
    d += 0.009 * g2(ax, z, 0.0, MOUTH_Z + 0.016, MOUTH_HW * 0.9, 0.014)
    d += 0.011 * g2(ax, z, 0.0, MOUTH_Z - 0.022, MOUTH_HW * 0.75, 0.016)
    d -= 0.004 * g2(ax, z, 0.0, MOUTH_Z - 0.052, MOUTH_HW * 0.9, 0.012)              # groove under the lower lip
    return d


def neck_exit(d):
    """Distance from C along d to the far wall of the neck column (an elliptic cylinder), 0 where it misses."""
    px, py = surf.C[0], surf.C[1] - NECK_Y
    a = (d[:, 0] / NECK_R) ** 2 + (d[:, 1] / (NECK_R * 0.92)) ** 2
    b = 2 * (px * d[:, 0] / NECK_R ** 2 + py * d[:, 1] / (NECK_R * 0.92) ** 2)
    c = (px / NECK_R) ** 2 + (py / (NECK_R * 0.92)) ** 2 - 1
    disc = np.maximum(b * b - 4 * a * c, 0)
    t = (-b + np.sqrt(disc)) / np.maximum(2 * a, 1e-9)
    z = surf.C[2] + d[:, 2] * t
    return np.where((d[:, 2] < 0) & (z < 0.30), t, 0.0)


def target_point(d):
    """Target surface point for unit direction(s) d from surf.C: the mean head plus the authored facial forms, closed
    underneath by the under-jaw surface and joined smoothly to the neck column."""
    d = d / np.linalg.norm(d, axis=-1, keepdims=True)
    r = surf.radius(d, R_LOW)
    p0 = surf.C + d * r[:, None]
    front = np.clip(-d[:, 1] / 0.5, 0, 1)
    r = r + feature_bumps(p0[:, 0], p0[:, 2], r) * front / np.maximum(-d[:, 1], 0.3)
    lo, hi = np.zeros_like(r), r.copy()
    # the under-jaw floor only closes the head in front of the neck; behind it the mean head itself curves into the nape
    def below(t):
        y = surf.C[1] + d[:, 1] * t
        z = surf.C[2] + d[:, 2] * t
        floor = np.where(y < NECK_Y - 0.02, under_jaw_z(y), NAPE_Z)   # jaw floor in front, skull base behind
        return z < floor
    cut = below(r)
    for _ in range(30):
        mid = (lo + hi) / 2
        b_ = below(mid)
        hi = np.where(cut & b_, mid, hi)
        lo = np.where(cut & ~b_, mid, lo)
    r = np.where(cut, (lo + hi) / 2, r)
    if NECK_ON:
        rn = neck_exit(d)
        k = 22.0
        r = np.where(rn > 0, np.log(np.exp(k * r) + np.exp(k * rn)) / k, r)
    return surf.C + d * r[:, None]


# ------------------------------------------------------------------ cage
def cube_to_sphere(x, y, z):
    x2, y2, z2 = x * x, y * y, z * z
    return np.array([x * math.sqrt(max(0, 1 - y2 / 2 - z2 / 2 + y2 * z2 / 3)),
                     y * math.sqrt(max(0, 1 - z2 / 2 - x2 / 2 + z2 * x2 / 3)),
                     z * math.sqrt(max(0, 1 - x2 / 2 - y2 / 2 + x2 * y2 / 3))])


def warp(d):
    """Cube face boundaries at 45/135 deg from the front are moved to FRONT_ANGLE / BACK_ANGLE: the front face holds the
    whole face (eyes to mouth), the side cells between get denser, the back face spreads over the back of the skull
    (dataset: faces per area on the face half 1.6-5.8x the back half)."""
    d = d / np.linalg.norm(d)
    th = math.acos(np.clip(-d[1], -1, 1))
    if th < 1e-6 or th > math.pi - 1e-6:
        return d
    a, b = math.radians(45), math.radians(135)
    if th <= a:
        th2 = th / a * FRONT_ANGLE
    elif th <= b:
        th2 = FRONT_ANGLE + (th - a) / (b - a) * (BACK_ANGLE - FRONT_ANGLE)
    else:
        th2 = BACK_ANGLE + (th - b) / (math.pi - b) * (math.pi - BACK_ANGLE)
    r = math.hypot(d[0], d[2])
    return np.array([d[0] / r * math.sin(th2), -math.cos(th2), d[2] / r * math.sin(th2)])


def build_cage():
    bm = bmesh.new()
    verts = {}

    def v(i, j, k):
        key = (i, j, k)
        if key not in verts:
            p = (-1 + 2 * i / NX, -1 + 2 * j / NY, -1 + 2 * k / NZ)
            d = warp(cube_to_sphere(*p))
            verts[key] = bm.verts.new(tuple(d))
            verts[key].tag = False
        return verts[key]
    F = {}
    for i in range(NX):
        for k in range(NZ):
            F["front", i, k] = bm.faces.new((v(i, 0, k), v(i + 1, 0, k), v(i + 1, 0, k + 1), v(i, 0, k + 1)))
            bm.faces.new((v(i + 1, NY, k), v(i, NY, k), v(i, NY, k + 1), v(i + 1, NY, k + 1)))
    for j in range(NY):
        for k in range(NZ):
            bm.faces.new((v(NX, j, k), v(NX, j + 1, k), v(NX, j + 1, k + 1), v(NX, j, k + 1)))
            bm.faces.new((v(0, j + 1, k), v(0, j, k), v(0, j, k + 1), v(0, j + 1, k + 1)))
    for i in range(NX):
        for j in range(NY):
            bm.faces.new((v(i, j, NZ), v(i + 1, j, NZ), v(i + 1, j + 1, NZ), v(i, j + 1, NZ)))
            F["bottom", i, j] = bm.faces.new((v(i + 1, j, 0), v(i, j, 0), v(i, j + 1, 0), v(i + 1, j + 1, 0)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, verts, F


def front_uv(co):
    """Front-view coordinates of a cage point after projection (x, z in H units)."""
    return co[0], co[2]


def ordered_loop(edges):
    nxt = {}
    for e in edges:
        a, b = e.verts
        nxt.setdefault(a, []).append(b); nxt.setdefault(b, []).append(a)
    start = edges[0].verts[0]; loop = [start]; prev = None; cur = start
    while True:
        c = [q for q in nxt[cur] if q is not prev]
        if not c or c[0] is start:
            break
        prev, cur = cur, c[0]; loop.append(cur)
    return loop


def region_boundary(faces):
    fs = set(faces)
    return [e for f in faces for e in f.edges if sum(1 for lf in e.link_faces if lf in fs) == 1]


def orient_ccw(loop, c):
    """Counter-clockwise seen from the front (x right, z up)."""
    a = sum((p.co.x - c[0]) * (q.co.z - c[1]) - (q.co.x - c[0]) * (p.co.z - c[1]) for p, q in zip(loop, loop[1:] + loop[:1]))
    return loop if a > 0 else loop[::-1]


def almond(t, cx, cz, hw, hh, tilt=0.012):
    """Anime eye opening, t in [0,1): 0 = inner corner (toward the nose), going over the top. Flat upper lid that
    peaks toward the inner third, fuller lower lid, outer corner a little higher."""
    th = 2 * math.pi * t
    c, s_ = -math.cos(th), math.sin(th)           # c: -1 inner .. +1 outer (for the left eye, +x outward)
    x = hw * c
    a = abs(c)
    z = hh * (1 - a ** 3.0) ** 0.55 * (1 + 0.08 * c) if s_ >= 0 else -0.78 * hh * (1 - a ** 2.0) ** 0.85
    return x, z + tilt * c * 0.5


def front_cells(F, fn):
    """Rectangular block of front cells spanning every cell that satisfies fn (an O-grid needs a rectangle)."""
    ids = [(i, k) for i in range(NX) for k in range(NZ) if F["front", i, k].is_valid and fn(F["front", i, k])]
    i0, i1 = min(i for i, _ in ids), max(i for i, _ in ids)
    k0, k1 = min(k for _, k in ids), max(k for _, k in ids)
    return [F["front", i, k] for i in range(i0, i1 + 1) for k in range(k0, k1 + 1)]


def rings_from_hole(bm, hole, n):
    """Rings outward from a hole loop, each ordered like the hole: ring[k][m] is the spoke partner of ring[k-1][m]."""
    out = [list(hole)]
    seen = set(hole)
    for _ in range(n):
        nxt = []
        for q in out[-1]:
            cand = [e.other_vert(q) for e in q.link_edges if e.other_vert(q) not in seen]
            nxt.append(cand[0] if cand else None)
        seen |= set(nxt)
        out.append(nxt)
    return out


def cut_eye(bm, F, side):
    """O-grid eye: the block of front cells around the eye becomes concentric rings around an almond opening."""
    ex = side * EYE_X
    blk = front_cells(F, lambda f: abs(f.calc_center_median().x - ex) < EYE_HW * 1.6 and abs(f.calc_center_median().z - EYE_Z) < EYE_HH * 1.6)
    outer = orient_ccw(ordered_loop(region_boundary(blk)), (ex, EYE_Z))
    rings = [outer]
    for th in (0.0, 0.0, 0.0):                      # three new rings; positions are set below
        bmesh.ops.inset_region(bm, faces=blk, thickness=0.001, use_even_offset=True)
        rings.append(orient_ccw(ordered_loop(region_boundary(blk)), (ex, EYE_Z)))
    inner = {q for f in blk for q in f.verts} - set(rings[-1])
    bmesh.ops.delete(bm, geom=list(inner), context="VERTS")
    left = [f for f in blk if f.is_valid]
    if left:
        bmesh.ops.delete(bm, geom=left, context="FACES_ONLY")
    chains = rings_from_hole(bm, rings[-1], 3)[::-1]      # outer .. hole, aligned spoke by spoke
    if orient_ccw(chains[0], (ex, EYE_Z)) is not chains[0]:
        chains = [c[::-1] for c in chains]
    outer = chains[0]
    n = len(outer)
    # angular start: inner corner = outer vertex closest to the nose side at eye height
    m0 = min(range(n), key=lambda m: (side * (outer[m].co.x - ex)) + 3 * abs(outer[m].co.z - EYE_Z))
    order = [(m0 - side * i) % n for i in range(n)]   # CCW chains; the almond runs over the top first
    # opening on the almond with even steps; lid rings blend from the almond to the outer block
    for step, m in enumerate(order):
        t = step / n
        ax, az = almond(t, 0, 0, EYE_HW, EYE_HH)
        o = outer[m].co
        for k, blend in ((3, 0.0), (2, 0.28), (1, 0.62)):
            px = ex + side * ax * (1 + 0.10 * (k < 3)) * (1 - blend) + (o.x - ex) * blend
            pz = EYE_Z + az * (1 + 0.14 * (k < 3)) * (1 - blend) + (o.z - EYE_Z) * blend
            chains[k][m].co = Vector((px, 0.0, pz))
            chains[k][m].tag = True
    return chains


def cut_mouth(bm, F):
    blk = front_cells(F, lambda f: abs(f.calc_center_median().x) < MOUTH_HW * 1.25 and abs(f.calc_center_median().z - MOUTH_Z) < 0.05)
    outer = orient_ccw(ordered_loop(region_boundary(blk)), (0, MOUTH_Z))
    rings = [outer]
    for _ in range(2):
        bmesh.ops.inset_region(bm, faces=blk, thickness=0.001, use_even_offset=True)
        rings.append(orient_ccw(ordered_loop(region_boundary(blk)), (0, MOUTH_Z)))
    inner = {q for f in blk for q in f.verts} - set(rings[-1])
    bmesh.ops.delete(bm, geom=list(inner), context="VERTS")
    left = [f for f in blk if f.is_valid]
    if left:
        bmesh.ops.delete(bm, geom=left, context="FACES_ONLY")
    chains = rings_from_hole(bm, rings[-1], 2)[::-1]
    outer = chains[0]
    n = len(outer)
    if orient_ccw(chains[0], (0, MOUTH_Z)) is not chains[0]:
        chains = [c[::-1] for c in chains]
    outer = chains[0]
    m0 = max(range(n), key=lambda m: outer[m].co.x - 3 * abs(outer[m].co.z - MOUTH_Z))   # right... +x corner
    seg = [(outer[(m + 1) % n].co - outer[m].co).length for m in range(n)]
    tot = sum(seg)
    tpar = {}
    acc = 0.0
    for i in range(n):
        m = (m0 + i) % n
        tpar[m] = acc / tot
        acc += seg[m]
    for m in range(n):
        ang = 2 * math.pi * tpar[m]          # even arc length round the block -> even angle round the mouth
        c, s_ = math.cos(ang), math.sin(ang)
        # lips outline (ring 1) and the lip line (ring 2, a slit)
        xl = (MOUTH_HW + 0.012) * math.copysign(abs(c) ** 0.8, c)
        zl = MOUTH_Z + (0.022 if s_ > 0 else -0.034) * abs(s_) ** 0.9
        xs = MOUTH_HW * math.copysign(abs(c) ** 0.7, c)
        zs = MOUTH_Z + 0.002 * math.copysign(abs(s_) ** 0.5, s_)
        chains[1][m].co = Vector((xl, 0.0, zl)); chains[2][m].co = Vector((xs, 0.0, zs))
        chains[1][m].tag = chains[2][m].tag = True
    return chains


def project_front(bm, verts_list, depth=0.0):
    """Put front-view (x, z) points onto the target surface (ray straight back from the front)."""
    for q in verts_list:
        x, z = q.co.x, q.co.z
        # find the direction from C whose target point has this x, z: iterate on the direction
        d = np.array([x, -0.45, z - surf.C[2]])
        for _ in range(12):
            p = target_point(d[None])[0]
            d = d + np.array([x - p[0], 0.0, z - p[2]]) * 1.0
        p = target_point(d[None])[0]
        q.co = Vector((x, p[1] + depth, z))


def jaw_floor(bm, verts):
    """Bottom-face vertices: Laplacian in the floor plane between the head outline, then onto the under-jaw line."""
    bot = [verts[i, j, 0] for i in range(NX + 1) for j in range(NY + 1)]
    edge = {verts[i, j, 0] for i in range(NX + 1) for j in range(NY + 1) if i in (0, NX) or j in (0, NY)}
    inner = [q for q in bot if q not in edge]
    for _ in range(200):
        for q in inner:
            nb = [e.other_vert(q).co for e in q.link_edges]
            q.co.x = sum(c.x for c in nb) / len(nb); q.co.y = sum(c.y for c in nb) / len(nb)
    for q in inner:
        q.co.z = float(under_jaw_z(np.array([q.co.y]))[0])


def neck(bm, verts, F):
    """Neck tube: the floor cells inside the neck circle open into a tube going down."""
    # iter n23: the hole is a RECTANGLE of floor cells (a staircase of cells snapped to a circle made 60-80 deg quads at
    # the jaw/neck join), then one inset ring turns the rectangle into the round neck (O-grid, as the eyes)
    # every cage face (bottom or back face of the cube) sitting inside the neck footprint opens into the tube
    def in_neck(f, k=0.80):
        c = f.calc_center_median()
        return c.z < 0.30 and math.hypot(c.x, (c.y - NECK_Y) * 1.1) < NECK_R * k
    blk = [f for f in bm.faces if in_neck(f)]
    print("neck hole faces", len(blk))
    ins = bmesh.ops.inset_region(bm, faces=blk, thickness=0.02, depth=0.0, use_even_offset=True)
    hole = blk
    loop = ordered_loop(region_boundary(hole))
    bmesh.ops.delete(bm, geom=hole, context="FACES")
    # start the loop at its front-centre vertex (x = 0, most forward), so the even spacing is mirror-symmetric
    st = min(range(len(loop)), key=lambda m: (abs(loop[m].co.x) > 1e-4, loop[m].co.y))
    loop = loop[st:] + loop[:st]
    n = len(loop)
    c = np.array([0.0, NECK_Y])
    angs = [math.atan2(q.co.y - c[1], q.co.x - c[0]) for q in loop]
    # even spacing on the neck circle, keeping the loop's order
    a0 = angs[0]; sgn = 1 if (angs[1] - angs[0]) % (2 * math.pi) < math.pi else -1
    top = []
    for m, q in enumerate(loop):
        a = a0 + sgn * 2 * math.pi * m / n
        x, y = c[0] + NECK_R * math.cos(a), c[1] + NECK_R * 0.92 * math.sin(a)
        q.co = Vector((x, y, float(under_jaw_z(np.array([y]))[0]) + 0.01))
    # relax the floor between the head outline and the neck circle in its own plane (the staircase of cells around
    # the hole folds otherwise), then put it back on the floor height
    edge = {verts[i, j, 0] for i in range(NX + 1) for j in range(NY + 1) if i in (0, NX) or j in (0, NY)}
    floor_v = [verts[i, j, 0] for i in range(NX + 1) for j in range(NY + 1)]
    fixed = edge | set(loop)
    ring_v = {q for f in ins["faces"] if f.is_valid for q in f.verts}
    movable = [q for q in set(floor_v) | ring_v if q.is_valid and q not in fixed and q.link_edges]
    for _ in range(300):
        for q in movable:
            nb = [e.other_vert(q).co for e in q.link_edges]
            q.co.x = sum(c.x for c in nb) / len(nb); q.co.y = sum(c.y for c in nb) / len(nb)
    for q in loop:
        q.tag = True           # n25: the neck's top loop stays analytic too (radial rays behind the neck graze the column and dragged it down)
    prev = loop
    for zz in (-0.12, -0.30, -0.48):
        ring = [bm.verts.new((q.co.x * 1.04, q.co.y, zz)) for q in loop]
        for m in range(n):
            try:
                bm.faces.new((prev[m], prev[(m + 1) % n], ring[(m + 1) % n], ring[m]))
            except ValueError:
                pass
        prev = ring
        for q in ring:
            q.tag = True       # the tube below the floor stays analytic (radial rays from C run along its axis)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return prev


def fit_limit(bm, levels, iters=45):
    """Move untagged cage vertices so the subdivision limit surface sits on the target."""
    me = bpy.data.meshes.new("cage"); bm.to_mesh(me)
    ob = bpy.data.objects.new("cage", me); bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("s", "SUBSURF"); mod.levels = levels; mod.render_levels = levels
    n = len(me.vertices)
    free = np.array([not v.tag for v in bm.verts])
    for it in range(iters):
        print('  it', it, flush=True) if False else None
        dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg); m2 = ev.to_mesh()
        L = np.array([m2.vertices[i].co[:] for i in range(n)])
        ev.to_mesh_clear()
        d = L - surf.C
        T = target_point(d)
        delta = (T - L) * free[:, None]
        delta = np.nan_to_num(delta)
        mag = np.linalg.norm(delta, axis=1, keepdims=True)
        delta = delta * np.minimum(1.0, 0.05 / np.maximum(mag, 1e-9))
        co = np.array([v.co[:] for v in me.vertices]) + delta * 0.9
        me.vertices.foreach_set("co", co.ravel()); me.update()
        if it == iters - 1:
            mm = np.linalg.norm(delta, axis=1)
            bad = np.argsort(-mm)[:6]
            print("fit residual max %.4f mean %.4f" % (np.abs(delta).max(), mm.mean()))
            for b_ in bad:
                print("   worst", np.round(L[b_], 3), "->", np.round(T[b_], 3))
    for v, c in zip(bm.verts, me.vertices):
        v.co = c.co.copy()
    return ob


def surface_x_H(y, z, s):
    """x of the target surface seen straight from the side at (y, z) (H units)."""
    d = np.array([s * 0.4, y - surf.C[1], z - surf.C[2]])
    for _ in range(14):
        p = target_point(d[None])[0]
        d = d + np.array([0.0, y - p[1], z - p[2]])
    return float(target_point(d[None])[0][0])


def add_ears(bmf):
    """Build the ear shells with ears3d (metres) on this head and append them (H units)."""
    sys.path.insert(0, "/home/claude/acc_head/scripts")
    import importlib, face_features as FF
    import ears_nh as ears3d
    importlib.reload(ears3d)
    S_, O_ = 0.262, 1.4826
    FF.EAR_TOP, FF.EAR_BOT = O_ + EAR_TOP * S_, O_ + EAR_BOT * S_
    FF.EAR_FRONT, FF.EAR_BACK = EAR_FRONT * S_, EAR_BACK * S_
    FF.surface_x = lambda y, z, s, *a, **k: surface_x_H(y / S_, (z - O_) / S_, s) * S_
    for s_ in (1, -1):
        eb = ears3d.build_one(s_)
        me = bpy.data.meshes.new("ear"); eb.to_mesh(me); eb.free()
        for v in me.vertices:
            v.co = Vector((v.co.x / S_, v.co.y / S_, (v.co.z - O_) / S_))
        bmf.from_mesh(me)


def symmetrize(bm, tol=0.02):
    """Average every vertex with its mirror twin (x -> -x); centre-line vertices get x = 0."""
    from mathutils.kdtree import KDTree
    vs = list(bm.verts)
    kd = KDTree(len(vs))
    for i, v in enumerate(vs):
        kd.insert(v.co, i)
    kd.balance()
    new = {}
    for v in vs:
        co, j, dist = kd.find(Vector((-v.co.x, v.co.y, v.co.z)))
        if dist < tol:
            t = vs[j].co
            new[v] = Vector(((v.co.x - t.x) / 2, (v.co.y + t.y) / 2, (v.co.z + t.z) / 2))
    for v, c in new.items():
        v.co = c
    for v in vs:
        if abs(v.co.x) < 1e-4:
            v.co.x = 0.0


def eye_rim(bm, chains, side):
    """Lid thickness: the opening edge turns into the head toward the eyeball, two short rings, order kept."""
    opening = chains[-1]
    n = len(opening)
    ec = eyeball_centre(side)
    edges = [bm.edges.get((opening[m], opening[(m + 1) % n])) for m in range(n)]
    crease = bm.edges.layers.float.get("crease_edge")
    for e in edges:
        e[crease] = 0.75                       # the almond keeps its corners through subdivision
    prev = opening
    for depth, shrink in ((0.012, 0.97), (0.024, 0.93)):
        ex = bmesh.ops.extrude_edge_only(bm, edges=edges)
        nv = [g for g in ex["geom"] if isinstance(g, bmesh.types.BMVert)]
        # map new verts to their source by position (extrude copies positions)
        src = {}
        for q in nv:
            src[q] = min(prev, key=lambda p: (p.co - q.co).length)
        ring = []
        for p in prev:
            q = next(k for k, v in src.items() if v is p)
            ring.append(q)
            q.co = Vector((ec[0] + (p.co.x - ec[0]) * shrink, p.co.y + depth, ec[2] + (p.co.z - ec[2]) * shrink))
            q.tag = True
        edges = [bm.edges.get((ring[m], ring[(m + 1) % n])) for m in range(n)]
        prev = ring
    return prev


def eyeball_centre(side):
    """Behind the opening: the front of the ball sits just behind the lid line."""
    x, z = side * EYE_X, EYE_Z
    d = np.array([x, -0.45, z - surf.C[2]])
    for _ in range(12):
        p = target_point(d[None])[0]
        d = d + np.array([x - p[0], 0.0, z - p[2]])
    p = target_point(d[None])[0]
    return (x, p[1] + EYEBALL_R + 0.022, z)


def mouth_bag(bm, slit):
    n = len(slit)
    edges = [bm.edges.get((slit[m], slit[(m + 1) % n])) for m in range(n)]
    prev = slit
    for depth, open_ in ((0.02, 0.006), (0.07, 0.02)):
        ex = bmesh.ops.extrude_edge_only(bm, edges=edges)
        nv = [g for g in ex["geom"] if isinstance(g, bmesh.types.BMVert)]
        src = {q: min(prev, key=lambda p: (p.co - q.co).length) for q in nv}
        ring = []
        for p in prev:
            q = next(k for k, v in src.items() if v is p)
            q.co = Vector((p.co.x * 0.92, p.co.y + depth, p.co.z + open_ * (1 if p.co.z > MOUTH_Z else -1)))
            q.tag = True
            ring.append(q)
        edges = [bm.edges.get((ring[m], ring[(m + 1) % n])) for m in range(n)]
        prev = ring
    bm.faces.new(prev)                         # back of the bag (one n-gon, hidden inside the head)
    return prev


def square_cage(bm, iters=40, factor=0.5):
    """Quad-squaring relaxation of the cage on the (smooth) target: each quad pulls its corners toward the best-fit
    square, neighbours average, everything snaps back radially onto the target. Tagged feature vertices stay."""
    vs = list(bm.verts)
    idx = {v: i for i, v in enumerate(vs)}
    co = np.array([v.co[:] for v in vs])
    free = np.array([(not v.tag) and (not v.is_boundary) for v in vs])
    quads = np.array([[idx[v] for v in f.verts] for f in bm.faces if len(f.verts) == 4])
    cnt = np.bincount(quads.ravel(), minlength=len(vs)).astype(float)
    sq = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], float)
    fi = np.nonzero(free & (cnt > 0))[0]
    # vertices of the neck tube / floor below the jaw keep their shape (rays from C graze there)
    fi = fi[co[fi, 2] > 0.06]
    for _ in range(iters):
        P = co[quads]; c = P.mean(1, keepdims=True); Q = P - c
        nrm = np.cross(Q[:, 2] - Q[:, 0], Q[:, 3] - Q[:, 1]); nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        u = Q[:, 1] - Q[:, 0] + Q[:, 2] - Q[:, 3]; u -= nrm * np.sum(u * nrm, 1)[:, None]
        u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-12); w = np.cross(nrm, u)
        a2 = np.stack([np.sum(Q * u[:, None], 2), np.sum(Q * w[:, None], 2)], -1)
        num = np.sum(sq[None, :, 0] * a2[:, :, 1] - sq[None, :, 1] * a2[:, :, 0], 1)
        den = np.sum(sq[None, :, 0] * a2[:, :, 0] + sq[None, :, 1] * a2[:, :, 1], 1)
        th = np.arctan2(num, den); sc = np.sqrt(np.sum(a2 ** 2, (1, 2)) / 8.0)
        ct, st_ = np.cos(th), np.sin(th)
        tx = (sq[None, :, 0] * ct[:, None] - sq[None, :, 1] * st_[:, None]) * sc[:, None]
        ty = (sq[None, :, 0] * st_[:, None] + sq[None, :, 1] * ct[:, None]) * sc[:, None]
        target = c + tx[..., None] * u[:, None] + ty[..., None] * w[:, None]
        acc = np.zeros_like(co); np.add.at(acc, quads.ravel(), target.reshape(-1, 3))
        goal = acc[fi] / cnt[fi][:, None]
        co[fi] = co[fi] + (goal - co[fi]) * factor
        co[fi] = target_point(co[fi] - surf.C)
    for v, c_ in zip(vs, co):
        v.co = Vector(c_)


def main(out, levels=LEVELS):
    global R_LOW
    R_LOW = target_r_map()
    bm, verts, F = build_cage()
    bm.edges.layers.float.new("crease_edge")      # before any edge is referenced (a new layer invalidates refs)
    bm.verts.ensure_lookup_table()
    for vv in bm.verts:
        d = np.array(vv.co[:])
        vv.co = Vector(target_point(d[None])[0])
    jaw_floor(bm, verts)
    eyes = [cut_eye(bm, F, s) for s in (1, -1)]
    mouth = cut_mouth(bm, F)
    feat = [q for ch in eyes for ring in ch[1:] for q in ring] + [q for ring in mouth[1:] for q in ring]
    project_front(bm, feat)
    neck(bm, verts, F)
    symmetrize(bm)
    for s_, ch in zip((1, -1), eyes):
        eye_rim(bm, ch, s_)
    mouth_bag(bm, mouth[-1])
    symmetrize(bm, tol=0.01)
    square_cage(bm)
    symmetrize(bm, tol=0.01)
    ob = fit_limit(bm, levels)
    save(bm, out.replace(".npz", "_cage.npz"))
    # final mesh = applied subdivision
    me = ob.data; bm.to_mesh(me)
    dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg); m2 = ev.to_mesh()
    bmf = bmesh.new(); bmf.from_mesh(m2); ev.to_mesh_clear()
    # soften the corner where the skull meets the skull base / jaw floor behind the jaw (a crease, not a form)
    zone = [v for v in bmf.verts if v.co.y > NECK_Y - 0.12 and 0.08 < v.co.z < 0.36 and not v.is_boundary]
    for _ in range(12):
        new = {}
        for v in zone:
            nb = [e.other_vert(v).co for e in v.link_edges]
            new[v] = v.co * 0.5 + sum(nb, Vector()) / len(nb) * 0.5
        for v, c in new.items():
            v.co = c
    # final_square(bmf)  # n22: made the neck join and eye corners worse (BVH projection across creases)
    # ears: the O-grid ear shells (rim, antihelix, concha relief), placed on this head's side surface
    add_ears(bmf)
    save(bmf, out)
    import json
    json.dump({"eyes": [[c * 0.262 + o for c, o in zip(eyeball_centre(s_), (0, 0, 1.4826))] for s_ in (1, -1)],
               "eye_r": EYEBALL_R * 0.262}, open(out.replace(".npz", "_eyes.json"), "w"))
    print("cage faces", len(bm.faces), "final faces", len(bmf.faces))
    return bm


def final_square(bmf, iters=60, hold=5):
    """Quad squaring on the subdivided skin (TypeSafe's first fix: quad shape). Vertices slide on the surface they are
    on (BVH nearest point of the pre-pass mesh), so the form does not change; the eye/mouth openings and the
    lids/lips (rings within `hold` of a boundary) stay where they are; the result is mirrored."""
    from mathutils.bvhtree import BVHTree
    from mathutils.kdtree import KDTree
    bmf.verts.ensure_lookup_table()
    n = len(bmf.verts)
    co = np.array([v.co[:] for v in bmf.verts])
    bvh = BVHTree.FromBMesh(bmf)
    dist = np.full(n, 99)
    cur = [v.index for v in bmf.verts if v.is_boundary]
    for k in range(hold + 1):
        nxt = []
        for i in cur:
            if dist[i] <= k:
                continue
            dist[i] = k
            nxt += [e.other_vert(bmf.verts[i]).index for e in bmf.verts[i].link_edges]
        cur = [i for i in nxt if dist[i] > k + 1]
    free = dist > hold
    quads = np.array([[v.index for v in f.verts] for f in bmf.faces if len(f.verts) == 4])
    cnt = np.bincount(quads.ravel(), minlength=n).astype(float)
    adj = [[e.other_vert(v).index for e in v.link_edges] for v in bmf.verts]
    kd = KDTree(n)
    for i, c in enumerate(co):
        kd.insert(Vector(c), i)
    kd.balance()
    mir = np.array([kd.find(Vector((-c[0], c[1], c[2])))[1] for c in co])
    mid = np.abs(co[:, 0]) < 1e-5
    idx = np.nonzero(free)[0]
    sq = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], float)
    for _ in range(iters):
        P = co[quads]; c = P.mean(1, keepdims=True); Q = P - c
        nrm = np.cross(Q[:, 2] - Q[:, 0], Q[:, 3] - Q[:, 1]); nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        u = Q[:, 1] - Q[:, 0] + Q[:, 2] - Q[:, 3]; u -= nrm * np.sum(u * nrm, 1)[:, None]
        u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-12); w = np.cross(nrm, u)
        a2 = np.stack([np.sum(Q * u[:, None], 2), np.sum(Q * w[:, None], 2)], -1)
        num = np.sum(sq[None, :, 0] * a2[:, :, 1] - sq[None, :, 1] * a2[:, :, 0], 1)
        den = np.sum(sq[None, :, 0] * a2[:, :, 0] + sq[None, :, 1] * a2[:, :, 1], 1)
        th = np.arctan2(num, den); sc = np.sqrt(np.sum(a2 ** 2, (1, 2)) / 8.0)
        ct, st = np.cos(th), np.sin(th)
        tx = (sq[None, :, 0] * ct[:, None] - sq[None, :, 1] * st[:, None]) * sc[:, None]
        ty = (sq[None, :, 0] * st[:, None] + sq[None, :, 1] * ct[:, None]) * sc[:, None]
        tgt = c + tx[..., None] * u[:, None] + ty[..., None] * w[:, None]
        acc = np.zeros_like(co); np.add.at(acc, quads.ravel(), tgt.reshape(-1, 3))
        goal = acc[idx] / np.maximum(cnt[idx], 1)[:, None]
        avg = np.array([co[adj[i]].mean(0) for i in idx])
        new = co[idx] + 0.5 * (0.8 * (goal - co[idx]) + 0.2 * (avg - co[idx]))
        for k, i in enumerate(idx):
            hit = bvh.find_nearest(Vector(new[k]))
            if hit[0] is not None:
                new[k] = hit[0][:]
        co[idx] = new
        tw = co[mir] * np.array([-1.0, 1.0, 1.0])
        co[idx] = (co[idx] + tw[idx]) / 2
        co[idx[mid[idx]], 0] = 0.0
    for v in bmf.verts:
        v.co = Vector(co[v.index])
    return int(free.sum())


def save(bm, out):
    V = np.array([v.co[:] for v in bm.verts])
    idx = {v: i for i, v in enumerate(bm.verts)}
    PL, PS = [], []
    for f in bm.faces:
        PL += [idx[v] for v in f.verts]; PS.append(len(f.verts))
    np.savez(out, V=V * 0.262 + np.array([0, 0, 1.4826]), PL=np.array(PL), PS=np.array(PS), T=np.zeros((0, 3), int))


if __name__ == "__main__":
    main(sys.argv[1])
