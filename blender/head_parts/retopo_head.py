"""q41b head_base: clean quad head built from a generator head's SHAPE (Sammy chose "Generator shape + clean retopo").

Run inside Blender (Blender MCP exec or the Text Editor):
    exec(open(r"<repo>/blender/head_parts/retopo_head.py").read()); build(RADIAL, COLOR, knobs)

Input: RADIAL npz from radial_sample() below (first-hit ray distances R[phi, theta] from an inner centre c, theta 0 =
front (-y), so the ears drop out: rays hit the skull under them) and COLOR npz (base-colour texture at the same hits;
locates the painted eyes, brows and mouth). Output object HEAD_Base:
- all-quad grid (NV rows x NU columns, a triangle fan only at the skull top pole), open at the neck;
- painted-feature relief removed: ear specks replaced by a local median, then a separable Gaussian (sigma knob)
  everywhere except a nose mask (the nose shape is kept);
- an eye opening per side: the grid patch round the painted eye is replaced by K concentric rings from the patch
  border to the MHS3 eye-shape template curve (knowledge/mhs3_face_rules.json eye_shape_template), scaled to the
  painted eye's width, mirrored so both sides match; the inner rings dip inward (socket knob);
- dense rows/columns through the mouth area (the mouth part cuts its own loop later).
Nothing here paints the face: eyes, brows, lashes, mouth, teeth, ears and hair are separate objects (contract).
"""
import math

import numpy as np

K = {
    "NU": 128, "NV": 100,          # output grid
    "sigma": 1.6,                  # relief smoothing above the nose (radial-sample cells)
    "sigma_low_v": 2.2, "sigma_low_h": 1.0,   # below the nose: vertical smoothing removes stripes, keeps the chin
    "chin_row_frac": 0.10,
    "symmetric": True,
    "eyes_from_rules": True, "F1": 0.728, "F3": 0.43, "R1": 0.42,   # rulebook eye placement
    "band_ang": 0.75,
    "profile_ctrl": [(0.19, 0.0), (0.255, -0.014), (0.315, 0.004), (0.36, 0.016), (0.405, 0.010), (0.44, 0.0)],   # chin fwd, lip back, under-nose back (v2b)
    "feature_sigma": 6.0, "socket_zone": 1.1,         # rows below this fraction of the capsule rows = neck (z ~0.18 on v2b)
    "relax_iter": 8,               # tangential relax of the eye-patch vertices (then re-projected)
    "nose_keep_r": 7.0, "nose_soft": 0.5,            # cells round the nose tip kept unsmoothed (blended)
    "speck": 0.004, "speck_from": 0.9,   # ear speck threshold (m off the local median), only |theta| > 0.9 rad
    "eye_scale": 1.1,               # rulebook R1: eye width 0.42 IPD (painted width x 1.1 on v2b)              # opening width = painted eye width x this
    "eye_rings": 5, "socket": 0.012,
    "eye_rows": (0.45, 0.85), "nose_rows": (0.3, 0.75),
}
TEMPLATE_TOP = [-0.12, -0.2, -0.282, -0.31, -0.315, -0.299, -0.272, -0.232, -0.152]
TEMPLATE_BOT = [0.158, 0.243, 0.283, 0.305, 0.315, 0.305, 0.283, 0.236, 0.151]


def catmull(xc, yc, x):
    """monotone-in-x Catmull-Rom through (xc, yc), evaluated at x (xc increasing, end tangents zero)"""
    out = np.zeros_like(x, dtype=float)
    m = np.zeros_like(yc, dtype=float)
    m[1:-1] = (yc[2:] - yc[:-2]) / (xc[2:] - xc[:-2])
    for i in range(len(xc) - 1):
        sel = (x >= xc[i]) & (x <= xc[i + 1])
        h = xc[i + 1] - xc[i]; t = (x[sel] - xc[i]) / h
        h00 = 2 * t ** 3 - 3 * t ** 2 + 1; h10 = t ** 3 - 2 * t ** 2 + t; h01 = -2 * t ** 3 + 3 * t ** 2; h11 = t ** 3 - t ** 2
        out[sel] = h00 * yc[i] + h10 * h * m[i] + h01 * yc[i + 1] + h11 * h * m[i + 1]
    return out


def _seg_blur_axis(A, s, axis, thr, wrap):
    """1-D Gaussian along axis that never averages across a jump |dA| > thr (edge-aware, normalised weights)"""
    g = gauss1d(s); r = len(g) // 2
    B = np.moveaxis(A, axis, 1)                       # (other, n)
    n = B.shape[1]
    jump = np.abs(np.diff(B, axis=1, append=B[:, :1] if wrap else B[:, -1:])) > thr
    seg = np.concatenate([np.zeros((B.shape[0], 1), int), np.cumsum(jump[:, :-1], axis=1)], axis=1)
    num = np.zeros_like(B); den = np.zeros_like(B)
    for k in range(-r, r + 1):
        idx = np.arange(n) + k
        if wrap:
            idx = idx % n; valid = np.ones(n, bool)
        else:
            valid = (idx >= 0) & (idx < n); idx = np.clip(idx, 0, n - 1)
        same = (seg[:, idx] == seg) & valid[None, :]
        if wrap and k != 0:                           # a wrapped segment boundary at the seam: also compare via jumps
            same &= True
        w = g[k + r] * same
        num += w * B[:, idx]; den += w
    return np.moveaxis(num / np.maximum(den, 1e-9), 1, axis)


def eblur(A, sv, sh=None, thr=0.03):
    """edge-aware separable blur: sh along columns (theta, wraps), sv along rows"""
    sh = sv if sh is None else sh
    A = _seg_blur_axis(A, sh, 1, thr, True)
    return _seg_blur_axis(A, sv, 0, thr, False)


def gauss1d(s):
    r = int(3 * s) + 1
    x = np.arange(-r, r + 1)
    g = np.exp(-x * x / (2 * s * s))
    return g / g.sum()


def blur(A, s):
    g = gauss1d(s)
    r = len(g) // 2
    P = np.pad(A, ((0, 0), (r, r)), mode="wrap")          # theta wraps
    A = sum(g[k] * P[:, k:k + A.shape[1]] for k in range(len(g)))
    P = np.pad(A, ((r, r), (0, 0)), mode="edge")
    return sum(g[k] * P[k:k + A.shape[0], :] for k in range(len(g)))


def blur_v(A, sv, sh):
    """anisotropic: sv along rows (vertical), sh along columns"""
    gh = gauss1d(sh); r = len(gh) // 2
    P = np.pad(A, ((0, 0), (r, r)), mode="wrap")
    A = sum(gh[k] * P[:, k:k + A.shape[1]] for k in range(len(gh)))
    gv = gauss1d(sv); r = len(gv) // 2
    P = np.pad(A, ((r, r), (0, 0)), mode="edge")
    return sum(gv[k] * P[k:k + A.shape[0], :] for k in range(len(gv)))


def median5(A):
    P = np.pad(A, ((2, 2), (2, 2)), mode="edge")
    st = np.stack([P[i:i + A.shape[0], j:j + A.shape[1]] for i in range(5) for j in range(5)])
    return np.median(st, axis=0)


def clean_r(R, COL, th, zrows=None, O=None, E=None):
    med = median5(R)
    side = (np.abs(np.angle(np.exp(1j * th))) > K["speck_from"])[None, :]   # ears / neck notch only: never the nose
    R = np.where(side & (np.abs(R - med) > K["speck"]), med, R)
    NV, NU = R.shape
    j0 = int(np.argmin(np.abs(th)))
    # symmetric head: average with the mirror image about the front column (theta -> -theta)
    if K["symmetric"]:
        mirror_cols = (2 * j0 - np.arange(NU)) % NU
        R = 0.5 * (R + R[:, mirror_cols])
    # painted features (eyes, brows, mouth) left relief: heavy smoothing inside their (dilated) footprint; the generator
    # also carved 3D sockets wider than the painted eyes, so an enlarged ellipse round each painted eye is flattened too
    if K["feature_sigma"]:
        fm = feature_mask(COL, th).astype(float)
        if K["symmetric"]:
            fm = np.maximum(fm, fm[:, (2 * j0 - np.arange(NU)) % NU])
        fm = np.clip(blur(fm, 2.5) * 3.0, 0, 1)
        _, raw = eye_blobs(COL, th)
        yy0, xx0 = np.mgrid[0:NV, 0:NU]
        ez = np.zeros((NV, NU))
        for e in raw:
            for cj in (e["cj"], (2 * j0 - e["cj"]) % NU):
                dd = np.hypot((xx0 - cj) / (K["socket_zone"] * e["w"]), (yy0 - e["ci"]) / (K["socket_zone"] * e["h"]))
                ez = np.maximum(ez, np.clip(1.5 - dd, 0, 1))
        fm = np.maximum(fm, ez)
        # only above the nose: below it the mask catches the neck shadow and the smoothing erased the chin (q41b j)
        prot0 = R - blur(R, 6.0)
        lo0, hi0 = int(NV * K["nose_rows"][0]), int(NV * K["nose_rows"][1])
        nrow = lo0 + int(np.argmax(prot0[lo0:hi0, j0]))
        t0 = np.clip((yy0 - (nrow + 2)) / 4.0, 0, 1)
        fm = fm * (t0 * t0 * (3 - 2 * t0))
        R = R * (1 - fm) + eblur(R, K["feature_sigma"]) * fm
    i_lo, i_hi = int(NV * K["nose_rows"][0]), int(NV * K["nose_rows"][1])
    prot = R - blur(R, 6.0)                                 # local protrusion: the nose, not the chin
    win = prot[i_lo:i_hi, j0 - 6:j0 + 7]
    ii, jj = np.unravel_index(np.argmax(win), win.shape)
    ni, nj = ii + i_lo, jj + j0 - 6
    yy, xx = np.mgrid[0:NV, 0:NU]
    d = np.hypot((yy - ni) * 1.0, (xx - nj) * 1.2)
    m = np.clip(1 - d / K["nose_keep_r"], 0, 1) ** 2
    Rn = R * (1 - K["nose_soft"]) + eblur(R, 1.2) * K["nose_soft"]      # softened nose (N2 tip angle)
    Rs = eblur(R, K["sigma"])
    # below the nose (mouth, chin, jaw, neck) only light smoothing: the strong one erased the chin (q41b v3c)
    Rw = eblur(R, K["sigma_low_v"], K["sigma_low_h"])                  # stripes are horizontal: smooth more vertically
    t = np.clip((yy - ni) / 6.0, 0, 1); up = t * t * (3 - 2 * t)        # 0 below the nose row, 1 from 6 rows above
    Rs = Rs * up + Rw * (1 - up)
    # neck (below the chin): strong smoothing removes the generator's neck seam ridge
    yv_, zv_ = front_profile(R, th, O, E)
    cz = chin_bottom_z(R, th, O, E)
    tn = np.clip((cz - 0.015 - zv_) / 0.03, 0, 1)[:, None] * np.ones((1, NU)); neck = tn * tn * (3 - 2 * tn)
    Rs = Rs * (1 - neck) + eblur(R, 2.5) * neck
    # lower-face profile curve (rulebook P5 under-nose, P7 lower lip, P8 chin; the generator's lower face is one straight
    # slope): a smooth Catmull-Rom offset d(z) through control points (z, metres back; - = forward), fading to the sides
    if zrows is not None:
        zc = np.array([p[0] for p in K["profile_ctrl"]]); dc = np.array([p[1] for p in K["profile_ctrl"]])
        zz = zrows
        dz = np.zeros_like(zz)
        inside = (zz > zc[0]) & (zz < zc[-1])
        dz[inside] = catmull(zc, dc, zz[inside])
        ang = np.abs(np.angle(np.exp(1j * th)))[None, :]
        ta = np.clip(1 - ang / K["band_ang"], 0, 1); ba = 0.5 - 0.5 * np.cos(np.pi * ta)
        Rs = Rs - dz[:, None] * ba
    return Rs * (1 - m) + Rn * m, (ni, nj)


def feature_mask(COL, th):
    """painted non-skin pixels on the face: eyes (blue / white / dark), brows and mouth (darker, less saturated than
    skin), limited to the front half"""
    r, g, b = COL[..., 0], COL[..., 1], COL[..., 2]
    lum = COL.mean(2); sat = COL.max(2) - COL.min(2)
    skin = np.median(COL[(lum > 0.5)], axis=0)
    dist = np.linalg.norm(COL - skin, axis=2)
    front = (np.abs(np.angle(np.exp(1j * th))) < 1.0)[None, :]
    return (dist > 0.12) & front


def eye_blobs(COL, th):
    r, g, b = COL[..., 0], COL[..., 1], COL[..., 2]
    lum = COL.mean(2)
    sat = COL.max(2) - COL.min(2)
    skin_like = (r > b + 0.12) & (sat > 0.08)
    eye = ((b > r + 0.02) | ((lum > 0.80) & (sat < 0.10)) | (lum < 0.30)) & ~skin_like
    NV, NU = eye.shape
    j0 = int(np.argmin(np.abs(th)))
    out = []
    for side in (-1, 1):
        cols = np.arange(j0, j0 + side * NU // 5, side)
        sub = np.zeros_like(eye)
        lo, hi = int(NV * K["eye_rows"][0]), int(NV * K["eye_rows"][1])
        sub[lo:hi, np.sort(cols)] = eye[lo:hi, np.sort(cols)]
        ii, jj = np.nonzero(sub)
        out.append({"ci": float(np.median(ii)), "cj": float(np.median(jj)),
                    "w": float(np.percentile(jj, 97) - np.percentile(jj, 3)),
                    "h": float(np.percentile(ii, 97) - np.percentile(ii, 3)), "n": int(len(ii))})
    # mirror: same row and size, symmetric about the front column
    ci = (out[0]["ci"] + out[1]["ci"]) / 2
    dj = (abs(out[0]["cj"] - j0) + abs(out[1]["cj"] - j0)) / 2
    w = (out[0]["w"] + out[1]["w"]) / 2
    h = (out[0]["h"] + out[1]["h"]) / 2
    return [{"ci": ci, "cj": j0 - dj, "w": w, "h": h}, {"ci": ci, "cj": j0 + dj, "w": w, "h": h}], out


def front_profile(R, th, O, E):
    """front (theta 0) hit points per row: y (forward = -y) and z"""
    j0 = int(np.argmin(np.abs(th)))
    r = R[:, j0]
    y = O[:, 1] - np.cos(E) * r
    z = O[:, 2] + np.sin(E) * r
    return y, z


def chin_bottom_z(R, th, O, E):
    """lowest profile point clearly forward of the neck (halfway between the neck front and the face front)"""
    y, z = front_profile(R, th, O, E)
    neck_y = np.nanmedian(y[:5]); face_y = np.nanmin(y)
    sel = y < 0.5 * (neck_y + face_y)
    return float(np.nanmin(z[sel]))


def eyes_from_rules(Rm, th, O, E, nose):
    """Eye openings placed by the MHS3 rulebook instead of the painted eyes: F3 nose tip 0.43 D below the pupil line,
    F1 IPD 0.728 D, R1 opening width 0.42 IPD (D = pupil line -> chin bottom). Rows/columns of the capsule sample."""
    NV, NU = Rm.shape
    j0 = int(np.argmin(np.abs(th)))
    yv, zr = front_profile(Rm, th, O, E)
    chin_z = chin_bottom_z(Rm, th, O, E)
    lower = np.ones(len(E), bool)
    li = np.arange(len(E))
    tip_z = zr[nose[0]]
    pupil_z = (tip_z - K["F3"] * chin_z) / (1 - K["F3"])
    D = pupil_z - chin_z
    ipd = K["F1"] * D
    face_rows = np.nonzero((E == 0) & (zr > chin_z))[0]
    ci = float(np.interp(pupil_z, zr[face_rows], face_rows))
    rr = float(Rm[int(round(ci)), (j0 + 10) % NU])
    dth = math.asin(min(0.99, ipd / 2 / rr))
    dj = dth / (2 * math.pi / NU)
    wcols = K["R1"] * ipd / (rr * 2 * math.pi / NU)
    return [{"ci": ci, "cj": j0 - dj, "w": wcols / K["eye_scale"], "h": wcols * 0.6},
            {"ci": ci, "cj": j0 + dj, "w": wcols / K["eye_scale"], "h": wcols * 0.6}]


def template_curve(n, w, flip):
    """n points of the eye opening (param units: columns, rows), inner corner first, counter-clockwise in (j, i)."""
    # closed outline: inner corner (closing point just beyond the first fraction), top inner->outer, outer corner,
    # bottom outer->inner; smoothed with a periodic Catmull-Rom spline, then resampled to n points by arc length
    fr = np.linspace(0, 1, 9)
    ctrl = [(-0.035, 0.0)] + [(f, t) for f, t in zip(fr, TEMPLATE_TOP)] + [(1.035, 0.0)] + \
           [(f, b) for f, b in zip(fr[::-1], TEMPLATE_BOT[::-1])]
    C = np.array([((f - 0.5) * w, -h * w) for f, h in ctrl])           # rows grow UP, template + = down
    m = len(C); dense = []
    for i in range(m):
        p0, p1, p2, p3 = C[(i - 1) % m], C[i], C[(i + 1) % m], C[(i + 2) % m]
        for t in np.linspace(0, 1, 24, endpoint=False):
            t2, t3 = t * t, t * t * t
            dense.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    dense = np.array(dense)
    seg = np.linalg.norm(np.diff(np.vstack([dense, dense[:1]]), axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    tgt = np.linspace(0, cum[-1], n, endpoint=False)
    closed = np.vstack([dense, dense[:1]])
    P = np.stack([np.interp(tgt, cum, closed[:, 0]), np.interp(tgt, cum, closed[:, 1])], 1)
    if flip:
        P[:, 0] *= -1
    return P


def sample(Rm, u, v):
    NV, NU = Rm.shape
    u = u % NU
    i0 = np.clip(np.floor(v).astype(int), 0, NV - 2); fi = np.clip(v - i0, 0, 1)
    j0 = np.floor(u).astype(int) % NU; fj = u - np.floor(u); j1 = (j0 + 1) % NU
    return ((1 - fi) * (1 - fj) * Rm[i0, j0] + (1 - fi) * fj * Rm[i0, j1] + fi * (1 - fj) * Rm[i0 + 1, j0]
            + fi * fj * Rm[i0 + 1, j1])


def build_topology(Rm, th, O, E, rowlen, eyes, NU, NV, nose_row=None):
    """Returns verts (N,3) and faces (list of tuples). Grid params (u in sample columns, v in sample rows)."""
    SNV, SNU = Rm.shape
    j0s = int(np.argmin(np.abs(th)))
    us = (np.arange(NU) - NU // 2) * SNU / NU + j0s                     # column NU/2 = the front column
    vs = np.linspace(0, SNV - 1, NV)
    if nose_row is not None:                                             # shift rows so one passes the nose tip
        k = int(np.argmin(np.abs(vs - nose_row))); vs = np.clip(vs + (nose_row - vs[k]) * np.clip(1 - np.abs(vs - nose_row) / 12.0, 0, 1), 0, SNV - 1)
    idx = -np.ones((NV, NU), int)
    params = []
    holes = []
    for e in eyes:
        # patch: grid cells whose centre is within a box round the eye (2.2 x width, 2.4 x height)
        holes.append((e, e["cj"] - 1.15 * e["w"], e["cj"] + 1.15 * e["w"], e["ci"] - 1.0 * e["w"], e["ci"] + 1.0 * e["w"]))

    def in_hole(u, v):
        for k, (e, u0, u1, v0, v1) in enumerate(holes):
            if u0 < u < u1 and v0 < v < v1:
                return k
        return -1
    for i in range(NV):
        for j in range(NU):
            idx[i, j] = len(params); params.append((us[j], vs[i]))
    faces = []
    patch_faces = {0: [], 1: []}
    for i in range(NV - 1):
        for j in range(NU):
            j2 = (j + 1) % NU
            uc = (us[j] + (us[j2] if j2 else SNU)) / 2; vc = (vs[i] + vs[i + 1]) / 2
            k = in_hole(uc, vc)
            f = (idx[i, j], idx[i, j2], idx[i + 1, j2], idx[i + 1, j])
            if k >= 0:
                patch_faces[k].append(f)
            else:
                faces.append(f)
    params = [list(p) for p in params]
    ring_info = []
    for k in (0, 1):
        # boundary loop of the removed patch, ordered
        edges = {}
        for f in patch_faces[k]:
            for a, b in zip(f, f[1:] + f[:1]):
                key = (min(a, b), max(a, b))
                edges[key] = edges.get(key, 0) + 1
        bnd = [e for e, n in edges.items() if n == 1]
        nxt = {}
        for a, b in bnd:
            nxt.setdefault(a, []).append(b); nxt.setdefault(b, []).append(a)
        loop = [bnd[0][0]]; prev = None
        while True:
            cand = [x for x in nxt[loop[-1]] if x != prev]
            if not cand or cand[0] == loop[0]:
                break
            prev = loop[-1]; loop.append(cand[0])
        e = holes[k][0]
        cu, cv = e["cj"], e["ci"]
        ang = [math.atan2(params[p][1] - cv, params[p][0] - cu) for p in loop]
        if np.sum(np.diff(np.unwrap(ang))) < 0:
            loop = loop[::-1]; ang = ang[::-1]
        s = int(np.argmin([abs(math.atan2(math.sin(a - (math.pi if k == 0 else 0.0)), math.cos(a - (math.pi if k == 0 else 0.0)))) for a in ang]))
        loop = loop[s:] + loop[:s]
        n = len(loop)
        curve = template_curve(n, e["w"] * K["eye_scale"], flip=(k == 1))
        # rows are physically shorter than columns: scale the template's heights into row units
        col_len = 2 * math.pi / SNU * float(np.nanmean(Rm[int(round(cv))])) * math.cos(float(np.interp(cv, np.arange(SNV), E)))
        row_len = float(np.interp(cv, np.arange(SNV), rowlen))
        curve[:, 1] *= col_len / row_len
        # order the curve counter-clockwise starting nearest to the same angle as loop[0]
        ca = np.arctan2(curve[:, 1], curve[:, 0])
        if np.sum(np.diff(np.unwrap(ca))) < 0:
            curve = curve[::-1]; ca = ca[::-1]
        a0 = math.atan2(params[loop[0]][1] - cv, params[loop[0]][0] - cu)
        s2 = int(np.argmin(np.abs(np.angle(np.exp(1j * (ca - a0))))))
        curve = np.roll(curve, -s2, axis=0)
        rings = [loop]
        KR = K["eye_rings"]
        for r in range(1, KR + 1):
            t = r / KR
            tt = 1 - (1 - t) ** 1.6
            ring = []
            for q, p in enumerate(loop):
                pu, pv = params[p]
                qu, qv = cu + curve[q, 0], cv + curve[q, 1]
                params.append([pu + (qu - pu) * tt, pv + (qv - pv) * tt])
                ring.append(len(params) - 1)
            rings.append(ring)
        for r in range(KR):
            A, B = rings[r], rings[r + 1]
            for q in range(n):
                q2 = (q + 1) % n
                faces.append((A[q], A[q2], B[q2], B[q]))
        ring_info.append({"rings": rings, "n": n})
    P = np.array(params)
    # relax the in-between ring vertices in parameter space (Laplacian over the quad faces), border and opening fixed
    fixed = set()
    for info in ring_info:
        fixed.update(info["rings"][0]); fixed.update(info["rings"][-1])
    movable = sorted({v for info in ring_info for ring in info["rings"][1:-1] for v in ring})
    nb = {v: set() for v in movable}
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            if a in nb: nb[a].add(b)
            if b in nb: nb[b].add(a)
    for _ in range(K["relax_iter"]):
        Pn = P.copy()
        for v in movable:
            ns_ = list(nb[v]); Pn[v] = 0.5 * P[v] + 0.5 * P[ns_].mean(0)
        P = Pn
    R = sample(Rm, P[:, 0], P[:, 1])
    # socket: inner rings dip inward
    for info in ring_info:
        KR = len(info["rings"]) - 1
        for r, ring in enumerate(info["rings"]):
            if r == 0:
                continue
            R[ring] *= 1 - K["socket"] * (r / KR) ** 2
    thv = -math.pi + P[:, 0] * 2 * math.pi / SNU
    ev = np.interp(P[:, 1], np.arange(SNV), E)
    Ov = np.stack([np.interp(P[:, 1], np.arange(SNV), O[:, k]) for k in range(3)], 1)
    D = np.stack([np.sin(thv) * np.cos(ev), -np.cos(thv) * np.cos(ev), np.sin(ev)], 1)
    V = Ov + D * R[:, None]
    # top pole fan: pole straight above the axis point, at the top ring's mean height plus the ring radius x tan(rest)
    top = idx[NV - 1]
    ring = V[top]
    rr = float(np.mean(np.hypot(ring[:, 0] - O[-1, 0], ring[:, 1] - O[-1, 1])))
    pole = np.array([O[-1, 0], O[-1, 1], float(ring[:, 2].mean()) + rr * math.tan((math.pi / 2 - E[-1]) / 2)])
    V = np.vstack([V, pole])
    pi = len(V) - 1
    for j in range(NU):
        faces.append((top[j], top[(j + 1) % NU], pi))
    return V, faces, ring_info


def build(radial_npz, color_npz, knobs=None, name="HEAD_Base"):
    import bpy
    if knobs:
        K.update(knobs)
    d = np.load(radial_npz)
    R, th, O, E, rowlen = d["R"], d["th"], d["O"], d["E"], d["rowlen"]
    COL = d["COL"] if color_npz is None else np.load(color_npz)["COL"]
    Zf = d["Z"] if "Z" in d.files else O[:, 2]
    zrows = np.where(E < 0.01, Zf, -10.0)          # skull-cap rows: far from any face band
    Rm, nose = clean_r(R, COL, th, zrows, O, E)
    eyes, raw = eye_blobs(COL, th)
    if K["eyes_from_rules"]:
        eyes = eyes_from_rules(Rm, th, O, E, nose)
    V, F, rings = build_topology(Rm, th, O, E, rowlen, eyes, K["NU"], K["NV"], nose_row=nose[0])
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name])
    me = bpy.data.meshes.new(name)
    me.from_pydata(V.tolist(), [], [list(f) for f in F])
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return {"verts": len(V), "faces": len(F), "tris": sum(len(f) - 2 for f in F), "eyes": eyes, "raw_eyes": raw,
            "nose_cell": nose, "eye_loop_n": [r["n"] for r in rings]}
