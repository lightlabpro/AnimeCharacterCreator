"""q39 (Sammy: "start again with a new model" -> "Build head from scratch"): a new head modelled in Blender from
nothing - no VRoid face mesh. Clean all-quad topology from smooth parametric curves, MHS3 proportions taken from the
measured rulebook (knowledge/mhs3_face_rules.json), smooth curve-built eye openings, lashes, brows and mouth.

    bpyenv/bin/python blender/head_scratch/build_head.py BASE.glb OUT.glb [--knobs k.json] [--keep-hair]

BASE.glb supplies the body, rig and clothes (VRoid 3f8f0119); its face, eye, brow, lash, mouth meshes (and hair unless
--keep-hair) are removed and the body's own head is cut off at the neck. Material names follow the VRoid keys
(Face_00_SKIN, EyeWhite, EyeIris, EyeHighlight, FaceEyeline, FaceBrow, FaceMouth) so the existing renderer setup, the
measure scripts and the strict gate work unchanged.

Head construction
- The head is a stack of horizontal cross-sections (z rows) x 128 columns around (theta = 0 is the front, +y).
  Each section is two half super-ellipses: front half (width Wf, depth F - y0, exponent pf) and back half (width Wb,
  depth y0 - B, exponent pb), blended at the sides. All of Wf, Wb, F, B, y0, pf, pb are smooth splines of z built
  from MHS3 numbers (profile 'behind nose tip' table, face widths at fractions of D, IPD, nose / mouth / chin heights).
- The nose is a local displacement on the front (narrow ridge + rounded tip); lips are a small lip-roll field.
- Each eye: a rectangular patch of the grid round the eye is replaced by concentric rings from the patch border to
  the eye-opening curve (MHS3 eye-shape template, closed periodic spline) - the opening is a smooth curve with clean
  radial / loop topology (what an artist models), and every ring vertex is put back on the head surface.
"""
import json
import math
import os
import sys

import bpy  # noqa: E402  (bpy before bmesh / mathutils)
import bmesh
import numpy as np
from mathutils import Vector
from scipy.interpolate import CubicSpline, PchipInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

# ---------------------------------------------------------------------------------------------------------------
# knobs: all lengths in metres, world space of the VRoid base (front +y, up +z)
K = {
    "z_top": 1.752, "z_chin": 1.4915, "D": 0.112,          # skull top, chin bottom, pupil line -> chin (rulebook D)
    "ipd": 0.728,                                          # F1: IPD in D
    "nose_tip_D": 0.43, "mouth_D": 0.627,                  # F3 / F2: below the pupil line, in D
    "tip_y": 0.0905,                                       # nose tip depth (y)
    "ncols": 128,
    # eye opening (R1 width, R2 height in IPD; template from Leo)
    "eye_w_ipd": 0.398, "eye_h_scale": 1.07, "eye_dx": 0.0008, "eye_dz": -0.0008, "eye_tilt": 0.06,
    "socket": 0.0012,                                      # how far the skin dips into the opening edge
    "eyeball_r": 0.0125, "eyeball_back": 0.0016,           # eyeball radius, its front behind the opening plane
    "iris_r": 0.0112, "iris_aspect": 1.10, "iris_dish": 0.003,
    "lash_th": (0.0016, 0.0034), "lash_wing": 0.0028, "lowline_th": 0.00035,
    "brow_th": 0.0052, "brow_len": 0.050,
    "mouth_w": 0.046, "mouth_th": 0.0009,
    "skin": (228, 190, 160), "brow_col": (80, 53, 37), "lash_col": (42, 24, 18), "mouth_col": (120, 52, 44),
    "iris_col": (118, 160, 104), "iris_dark": (44, 80, 46),
}


def set_knobs(path):
    if path:
        K.update(json.load(open(path)))


# ---------------------------------------------------------------------------------------------------------------
# profile tables (z -> value).  Built from the rulebook targets; see the module notes.
def tables():
    """smooth (C2) splines of z for the face/cranium part, a separate neck, blended across the jaw underside.
    Per-quantity: (face control points, neck value)."""
    zt, zc, D = K["z_top"], K["z_chin"], K["D"]
    H = zt - zc
    tip = K["tip_y"]
    zp = zc + D                                              # pupil line
    ipd = K["ipd"] * D
    def bh(fr, behind_H):                                    # 'behind nose tip' at fraction fr of H from the top
        return (zt - fr * H, tip - behind_H * H)
    # midline front WITHOUT nose and lips (nose_field / lip_field add them locally)
    F = [(zt, -0.012), (zt - 0.006, 0.016), (zt - 0.016, 0.036), bh(0.1, 0.1757), bh(0.2, 0.094),
         bh(0.3, 0.053), bh(0.4, 0.039), bh(0.5, 0.050), bh(0.6, 0.052),
         (zp - 0.30 * D, tip - 0.052 * H - 0.0003), (zp - 0.45 * D, tip - 0.137 * D),
         (zp - 0.62 * D, tip - 0.168 * D), (zp - 0.78 * D, tip - 0.205 * D), (zp - 0.955 * D, tip - 0.23 * D),
         (zc + 0.0005, tip - 0.29 * D), (zc - 0.002, tip - 0.45 * D)]
    B = [(zt, -0.022), (zt - 0.012, -0.050), (zt - 0.03, -0.072), (zt - 0.06, -0.087), (zt - 0.10, -0.094),
         (zt - 0.14, -0.091), (zt - 0.175, -0.080), (zt - 0.205, -0.066), (zt - 0.235, -0.056), (zc, -0.0515),
         (zc - 0.002, -0.0510)]
    Wf = [(zt, 0.004), (zt - 0.006, 0.040), (zt - 0.016, 0.062), (zt - 0.04, 0.080), (zt - 0.08, 0.0866),
          (zp + 0.022, 0.0864), (zp, K.get("w_eye", 0.0835)), (zp - 0.25 * D, K.get("w_cheek", 0.0715)),
          (zp - 0.48 * D, K.get("w_cheek2", 0.0615)), (zp - 0.70 * D, K.get("w_jaw", 0.0500)),
          (zp - 0.88 * D, K.get("w_jaw2", 0.0365)), (zc + 0.001, K.get("w_chin", 0.019)), (zc - 0.002, K.get("w_chin", 0.019) - 0.003)]
    Wb = [(zt, 0.004), (zt - 0.006, 0.040), (zt - 0.016, 0.062), (zt - 0.04, 0.080), (zt - 0.08, 0.0866),
          (zp + 0.022, 0.0866), (zp, 0.0855), (zp - 0.30 * D, 0.078), (zp - 0.60 * D, 0.062),
          (zp - 0.85 * D, 0.045), (zc, 0.0375), (zc - 0.002, 0.0368)]
    Y0 = [(zt, -0.017), (zt - 0.06, -0.009), (zp, -0.006), (zp - 0.5 * D, -0.010), (zc, -0.016), (zc - 0.002, -0.016)]
    PF = [(zt, 2.0), (zt - 0.05, 2.15), (zp + 0.03, 2.5), (zp, 2.65), (zp - 0.4 * D, 2.55), (zp - 0.65 * D, 2.2),
          (zp - 0.88 * D, K.get("pf_jaw", 1.9)), (zc, K.get("pf_chin", 1.8)), (zc - 0.002, K.get("pf_chin", 1.8))]
    PB = [(zt, 2.0), (zc - 0.002, 2.0)]
    neck = {"F": K.get("neck_front", 0.010), "B": -0.050, "Wf": 0.0355, "Wb": 0.0360, "Y0": -0.016, "PF": 2.0, "PB": 2.0}
    jaw0, jaw1 = zc + K.get("jaw_blend_top", 0.0012), zc - K.get("jaw_blend_bot", 0.0075)
    class Q:
        def __init__(self, tab, nv):
            t = sorted(tab); zs = np.array([a for a, _ in t]); vs = np.array([b for _, b in t])
            self.cs = CubicSpline(zs, vs, bc_type="natural"); self.nv = nv
        def __call__(self, z):
            z = np.asarray(z, float)
            sb = np.clip((jaw0 - z) / (jaw0 - jaw1), 0, 1); sb = sb * sb * (3 - 2 * sb)
            return self.cs(np.maximum(z, jaw1)) * (1 - sb) + self.nv * sb
    return {k: Q(v, neck[k]) for k, v in (("F", F), ("B", B), ("Wf", Wf), ("Wb", Wb), ("Y0", Y0), ("PF", PF), ("PB", PB))}


T = None


def spow(c, p):
    return np.sign(c) * np.abs(c) ** (2.0 / p)


def section(z, th):
    """point(s) on the head surface at height z (scalar) and column angle(s) th (front = 0, +x at +pi/2)"""
    F, B, Wf, Wb, y0 = T["F"](z), T["B"](z), T["Wf"](z), T["Wb"](z), T["Y0"](z)
    pf, pb = T["PF"](z), T["PB"](z)
    th = np.asarray(th, float)
    s, c = np.sin(th), np.cos(th)
    front = c >= 0
    # blend widths across the sides so the silhouette has no kink at theta = 90 deg
    wblend = 0.5 + 0.5 * np.tanh(-c / 0.18)                   # 0 at front, 1 at back
    W = Wf + (Wb - Wf) * wblend
    p = np.where(front, pf, pb)
    x = W * spow(s, p)
    y = np.where(front, y0 + (F - y0) * spow(c, pf), y0 + (y0 - B) * spow(c, pb))
    return x, y


def nose_field(x, z):
    """nose ridge + tip as forward displacement (front only)"""
    D = K["D"]; zp = K["z_chin"] + D; zt_ = zp - K["nose_tip_D"] * D
    z_root = zp - 0.02 * D
    t = np.clip((z_root - z) / (z_root - zt_), 0, 1.2)        # 0 at the root .. 1 at the tip
    base_tip = K["tip_y"] - (T["F"](zt_))                       # how far the tip stands out of the face plane
    rise = base_tip * np.where(t <= 1, t ** 1.6, 0.0)
    under = np.where(t > 1, base_tip * np.clip(1 - (t - 1) / 0.13, 0, 1) ** 1.5, 0.0)
    h = rise + under
    w = 0.0032 + 0.0042 * np.clip(t, 0, 1) ** 1.5              # ridge half width grows towards the tip
    return h * np.exp(-(x / w) ** 2)


def lip_field(x, z):
    D = K["D"]; zp = K["z_chin"] + D; zm = zp - K["mouth_D"] * D
    hw = K["mouth_w"] / 2 + 0.004
    across = np.exp(-(x / hw) ** 4)
    up = K.get("lip_up", 0.0048) * np.exp(-((z - (zm + 0.0068)) / 0.0062) ** 2)
    low = K.get("lip_low", 0.0030) * np.exp(-((z - (zm - 0.0050)) / 0.0042) ** 2)
    line = -0.0010 * np.exp(-((z - zm) / 0.0012) ** 2)
    return across * (up + low + line)


def eye_centers():
    """centres of the eye OPENINGS (offset outward / up from the pupils by eye_dx / eye_dz)"""
    D = K["D"]; zp = K["z_chin"] + D; half = K["ipd"] * D / 2
    return [np.array([s * (half + K["eye_dx"]), zp + K["eye_dz"]]) for s in (-1, 1)]


def pupil_centers():
    D = K["D"]; zp = K["z_chin"] + D; half = K["ipd"] * D / 2
    return [np.array([s * half, zp]) for s in (-1, 1)]


def socket_field(x, z):
    out = np.zeros_like(np.asarray(x, float))
    ew = K["eye_w_ipd"] * K["ipd"] * K["D"]
    for c in eye_centers():
        r = np.hypot((x - c[0]) / (0.62 * ew), (z - c[1]) / (0.48 * ew))
        out = out - K["socket"] * np.exp(-r ** 2 * 1.2)
    return out


def surf_front(x, z):
    """head surface y at (x, z) on the front half (bisection on theta) incl. nose / lips / socket"""
    lo, hi = -math.pi / 2, math.pi / 2
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        xm, _ = section(z, mid)
        if xm < x:
            lo = mid
        else:
            hi = mid
    th = 0.5 * (lo + hi)
    _, y = section(z, th)
    return float(y) + float(nose_field(x, z)) + float(lip_field(x, z)) + float(socket_field(x, z))


def eye_curve(c, n):
    """closed eye-opening curve (x, z) with n points, counter-clockwise from the inner corner"""
    rb = json.load(open(os.path.join(REPO, "knowledge", "mhs3_face_rules.json")))["eye_shape_template"]
    ew = K["eye_w_ipd"] * K["ipd"] * K["D"]
    side = np.sign(c[0])                                     # +1: viewer-left?  inner corner is towards x = 0
    fr = np.linspace(0.06, 0.94, 9)
    top, bot = np.array(rb["top"]), np.array(rb["bot"])
    hs = K["eye_h_scale"]; tilt = K["eye_tilt"]
    # parameter u around the curve: inner corner u=0, top to the outer corner u=0.5, bottom back to 1
    pts = [(0.0, 0.0, 0.0 + 0.0)]
    for f, t_ in zip(fr, top):
        pts.append((f, -t_ * hs + tilt * f, 0))
    pts.append((1.0, tilt, 0))
    for f, b_ in zip(fr[::-1], bot[::-1]):
        pts.append((f, -b_ * hs + tilt * f, 0))
    P = np.array([(p[0], p[1]) for p in pts])
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1))]
    u = seg / seg[-1]
    Pc = np.vstack([P, P[:1]])
    cs = CubicSpline(u, Pc, bc_type="periodic")
    uu = np.linspace(0, 1, n, endpoint=False)
    Q = cs(uu)                                               # (f, up) in units of eye width
    xs = c[0] + side * (Q[:, 0] - 0.5) * ew                  # inner corner (f=0) nearest the midline
    zs = c[1] + Q[:, 1] * ew
    return np.stack([xs, zs], 1)


# ---------------------------------------------------------------------------------------------------------------
def build_head_mesh():
    zt, zc = K["z_top"], K["z_chin"]
    zs = np.r_[np.linspace(zt - 0.0015, 1.60, 38, endpoint=False), np.linspace(1.60, 1.50, 44, endpoint=False),
               np.linspace(1.50, 1.484, 12, endpoint=False), np.linspace(1.484, zc - 0.07, 12)]
    N = K["ncols"]
    th = np.linspace(0, 2 * np.pi, N, endpoint=False)
    rows = []
    for z in zs:
        x, y = section(z, th)
        front = np.cos(th) > -0.2
        y = y + np.where(front, nose_field(x, z) + lip_field(x, z) + socket_field(x, z), 0)
        rows.append(np.stack([x, y, np.full(N, z)], 1))
    V = np.array(rows)                                       # (R, N, 3)
    R = len(zs)
    verts = [tuple(p) for row in V for p in row]
    idx = lambda r, k: r * N + (k % N)
    faces = []
    for r in range(R - 1):
        for k in range(N):
            faces.append((idx(r, k), idx(r, k + 1), idx(r + 1, k + 1), idx(r + 1, k)))
    # top cap: pole vertex
    pole = len(verts); verts.append((0.0, float(T["Y0"](zt)), zt))
    for k in range(N):
        faces.append((pole, idx(0, k + 1), idx(0, k)))
    me = bpy.data.meshes.new("Head")
    me.from_pydata(verts, [], faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    vl = bm.verts.layers.int.new("gid"); fl = bm.faces.layers.int.new("gid")
    for v in bm.verts:
        v[vl] = v.index
    for f in bm.faces:
        f[fl] = f.index
    # --- eye patches: delete a rectangle of faces round each eye, rebuild with concentric rings ---
    ew = K["eye_w_ipd"] * K["ipd"] * K["D"]
    for c in eye_centers():
        # choose rows / cols whose verts fall in the patch box
        box_x = (c[0] - 0.78 * ew, c[0] + 0.78 * ew); box_z = (c[1] - 0.56 * ew, c[1] + 0.56 * ew)
        r_in = [r for r in range(R) if box_z[0] <= zs[r] <= box_z[1]]
        r0, r1 = min(r_in), max(r_in)
        xr = V[(r0 + r1) // 2, :, 0]
        k_in = [k for k in range(N) if np.cos(th[k]) > 0 and box_x[0] <= xr[k] <= box_x[1]]
        k0, k1 = min(k_in), max(k_in)
        want = {r * N + k for r in range(r0, r1) for k in range(k0, k1)}
        del_faces = [f for f in bm.faces if f[fl] in want]
        # border loop (ordered): top row k0->k1, right col r0->r1, bottom row k1->k0, left col r1->r0
        border = [idx(r0, k) for k in range(k0, k1)] + [idx(r, k1) for r in range(r0, r1)] + \
                 [idx(r1, k) for k in range(k1, k0, -1)] + [idx(r, k0) for r in range(r1, r0, -1)]
        inner_v = {idx(r, k) for r in range(r0 + 1, r1) for k in range(k0 + 1, k1)}
        bmesh.ops.delete(bm, geom=del_faces, context="FACES_ONLY")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v[vl] in inner_v], context="VERTS")
        bm.verts.ensure_lookup_table()
        n = len(border)
        bco = np.array([V.reshape(-1, 3)[i] for i in border])
        byid = {v[vl]: v for v in bm.verts}
        bv = [byid[i] for i in border]
        # eye curve with the same count, aligned by polar angle round the centre
        E = eye_curve(c, n)
        ang_b = np.arctan2(bco[:, 2] - c[1], bco[:, 0] - c[0])
        ang_e = np.arctan2(E[:, 1] - c[1], E[:, 0] - c[0])
        # same orientation?
        def winding(a):
            d = np.diff(np.unwrap(np.r_[a, a[0]]))
            return np.sign(d.sum())
        if winding(ang_b) != winding(ang_e):
            E = E[::-1]; ang_e = ang_e[::-1]
        sh = int(np.argmin([np.abs(np.angle(np.exp(1j * (ang_e[(np.arange(n) + s) % n] - ang_b)))).sum()
                            for s in range(n)]))
        E = E[(np.arange(n) + sh) % n]
        nring = K.get("eye_rings", 5)
        rings = [bv]
        for j in range(1, nring + 1):
            t = j / nring
            tt = t ** 0.85
            ring = []
            for i in range(n):
                bx, bz = bco[i, 0], bco[i, 2]
                ex, ez = E[i]
                x = bx + (ex - bx) * tt; z = bz + (ez - bz) * tt
                y = surf_front(x, z)
                nv = bm.verts.new((x, y, z)); nv[vl] = -1; ring.append(nv)
            rings.append(ring)
        for j in range(nring):
            a, b = rings[j], rings[j + 1]
            for i in range(n):
                i2 = (i + 1) % n
                try:
                    bm.faces.new((a[i], a[i2], b[i2], b[i]))
                except ValueError:
                    pass
        bm.verts.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    # make normals point outward
    ob = bpy.data.objects.new("Head", me); bpy.context.scene.collection.objects.link(ob)
    return ob



# ---------------------------------------------------------------------------------------------------------------
# textures
TEXDIR = None


def tex(name, img):
    path = os.path.join(TEXDIR, name + ".png"); img.save(path)
    im = bpy.data.images.load(path); im.pack()
    return im


def make_mat(name, image, alpha=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = image
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha:
        nt.links.new(tx.outputs["Alpha"], bsdf.inputs["Alpha"]); m.blend_method = "HASHED" if hasattr(m, "blend_method") else None
    bsdf.inputs["Roughness"].default_value = 1.0
    return m


def flat_img(col, size=8, a=255):
    from PIL import Image
    return Image.new("RGBA", (size, size), tuple(col) + (a,))


def mouth_curve_pts(n=81):
    D = K["D"]; zm = K["z_chin"] + D - K["mouth_D"] * D; hw = K["mouth_w"] / 2
    xs = np.linspace(-hw, hw, n)
    zz = zm - K.get("mouth_curve", 0.0006) * (xs / hw) ** 2
    tw = K["mouth_th"] * (1 - 0.55 * (xs / hw) ** 4)
    return xs, zz, tw


def skin_img(back=False):
    """skin base: flat tone, soft blush, lower-lip warmth, and the mouth line (drawn here, not as a floating mesh:
    F6 no mesh may poke out of the skin). Drawn at 2x and downsampled for clean anti-aliased curves."""
    from PIL import Image, ImageDraw, ImageFilter
    S0 = K.get("skin_res", 2048); S = 2 * S0
    im = Image.new("RGBA", (S, S), tuple(K["skin"]) + (255,))
    ov = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    def P(x, z):
        return (S * (0.5 + x / UVW), S * (1 - (z - UVZ0) / UVH))
    sx_m = S / UVW; sz_m = S / UVH                         # px per metre
    D = K["D"]; zp = K["z_chin"] + D
    for sx in ((-1, 1) if not back else ()):                 # soft blush under the eyes
        cx, cz = P(sx * 0.046, zp - 0.30 * D)
        d.ellipse((cx - 0.016 * sx_m, cz - 0.0075 * sz_m, cx + 0.016 * sx_m, cz + 0.0075 * sz_m), fill=(235, 125, 112, 28))
    mx, mz = P(0, zp - K["mouth_D"] * D - 0.0048)            # lower-lip warmth
    d.ellipse((mx - 0.012 * sx_m, mz - 0.0028 * sz_m, mx + 0.012 * sx_m, mz + 0.0028 * sz_m), fill=(212, 125, 108, 55))
    ov = ov.filter(ImageFilter.GaussianBlur(0.004 * sx_m))
    im.alpha_composite(ov)
    # MHS3 face paint (Leo): nose = pale highlight streak down the lit side of the bridge + a small darker tip
    # shadow; lower lip = soft pink shape with a shadow under it; lid crease arc; warm socket shade under the brow
    # by the inner corner; neck under the jaw in shadow
    pt = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dp = ImageDraw.Draw(pt)
    zt_ = zp - K["nose_tip_D"] * D
    lit = K.get("light_side", 1)                            # viewer's left = the lit side in the locked rig
    hl = [P(lit * 0.0010, zp - 0.05 * D), P(lit * 0.0050, zt_ + 0.011), P(lit * 0.0060, zt_ + 0.0025),
          P(lit * 0.0030, zt_ + 0.0012), P(lit * 0.0002, zp - 0.10 * D)]
    dp.polygon(hl, fill=tuple(K.get("nose_hl", (248, 222, 200))) + (K.get("nose_hl_a", 150),))
    sh = [P(-lit * 0.0005, zt_ + 0.002), P(-lit * 0.0050, zt_ - 0.0005), P(-lit * 0.0030, zt_ - 0.0032),
          P(lit * 0.0020, zt_ - 0.0034)]
    dp.polygon(sh, fill=tuple(K.get("nose_sh", (204, 152, 128))) + (120,))
    zm = zp - K["mouth_D"] * D
    dp.ellipse(P(-0.0085, zm - 0.0012) + P(0.0085, zm - 0.0058), fill=(214, 140, 128, 120))      # lower lip
    dp.ellipse(P(-0.0070, zm - 0.0060) + P(0.0070, zm - 0.0084), fill=(196, 146, 124, 90))       # under-lip shadow
    for sx in (-1, 1):
        ce = np.array([sx * (K["ipd"] * D / 2 + K["eye_dx"]), zp + K["eye_dz"]])
        ewm = K["eye_w_ipd"] * K["ipd"] * D
        arc = [P(ce[0] + sx * (f - 0.45) * ewm * 1.02, ce[1] + ewm * (0.42 + 0.10 * math.sin(math.pi * f)))
               for f in np.linspace(0.12, 0.95, 30)]
        dp.line(arc, fill=tuple(K.get("crease_col", (176, 112, 92))) + (150,), width=max(2, int(0.00045 * sz_m)))
        so = [P(ce[0] - sx * 0.62 * ewm, ce[1] + 0.25 * ewm), P(ce[0] - sx * 0.30 * ewm, ce[1] + 0.62 * ewm),
              P(ce[0] - sx * 0.70 * ewm, ce[1] + 0.85 * ewm), P(ce[0] - sx * 0.85 * ewm, ce[1] + 0.40 * ewm)]
        dp.polygon(so, fill=(206, 150, 128, K.get("socket_a", 0)))
    zc_ = K["z_chin"]
    if back:                                                 # back / neck object: only the shadow under the jaw
        pt = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dp = ImageDraw.Draw(pt)
        dp.polygon([P(-0.05, zc_ + 0.002), P(0.05, zc_ + 0.002), P(0.05, zc_ - 0.030), P(-0.05, zc_ - 0.030)],
                   fill=tuple(K.get("neck_sh", (176, 128, 108))) + (230,))
        im.alpha_composite(pt.filter(ImageFilter.GaussianBlur(0.002 * sx_m)))
        return im.resize((S0, S0), Image.LANCZOS)
    im.alpha_composite(pt.filter(ImageFilter.GaussianBlur(0.0005 * sx_m)))
    # chin line: the under-chin edge gets no outline from the hull (the jaw runs straight into the neck) - MHS3 draws
    # it, and the render measure finds the chin by it
    cl = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dc = ImageDraw.Draw(cl)
    cw = K.get("chin_line_w", 0.020)
    xs_ = np.linspace(-cw, cw, 60)
    top_ = [P(x, zc_ + 0.0004 + 0.0012 * (x / cw) ** 2) for x in xs_]
    bot_ = [P(x, zc_ - 0.0004 + 0.0012 * (x / cw) ** 2) for x in xs_[::-1]]
    dc.polygon(top_ + bot_, fill=tuple(K.get("chin_line_col", (96, 56, 44))) + (255,))
    im.alpha_composite(cl.filter(ImageFilter.GaussianBlur(0.6)))
    ln = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dl = ImageDraw.Draw(ln)
    xs, zz, tw = mouth_curve_pts()
    top = [P(x, z + t / 2) for x, z, t in zip(xs, zz, tw)]; bot = [P(x, z - t / 2) for x, z, t in zip(xs, zz, tw)]
    dl.polygon(top + bot[::-1], fill=tuple(K["mouth_col"]) + (255,))
    im.alpha_composite(ln.filter(ImageFilter.GaussianBlur(0.6)))
    return im.resize((S0, S0), Image.LANCZOS)


UVW, UVZ0, UVH = 0.26, 1.40, 0.38


def uv_front(me):
    uv = me.uv_layers.new(name="UVMap")
    co = np.array([v.co[:] for v in me.vertices])
    for l in me.loops:
        x, y, z = co[l.vertex_index]
        uv.data[l.index].uv = (0.5 + x / UVW, (z - UVZ0) / UVH)


def white_img():
    from PIL import Image
    S = 256; a = np.zeros((S, S, 4), np.uint8)
    v = np.linspace(1, 0, S)[:, None] * np.ones((1, S))      # 1 top .. 0 bottom
    top = K.get("white_top", (196, 190, 192)); base = K.get("white_base", (242, 239, 236))
    t = np.clip((v - 0.58) / 0.12, 0, 1)                      # grey lid-shadow band over the top
    for i in range(3):
        a[..., i] = (base[i] + (top[i] - base[i]) * t).astype(np.uint8)
    a[..., 3] = 255
    return Image.fromarray(a, "RGBA")


def iris_img():
    """MHS3 iris (Leo): base colour, darker upper third (lid shadow), large dark pupil, dark rim, lighter lower area,
    a thin darker ring band. Square UV: centre (0.5, 0.5), radius 0.5 = iris edge."""
    from PIL import Image, ImageFilter
    S = 512; yy, xx = np.mgrid[0:S, 0:S]
    u = (xx + 0.5) / S - 0.5; v = 0.5 - (yy + 0.5) / S          # v up
    r = np.hypot(u, v) / 0.5
    base = np.array(K["iris_col"], float); dark = np.array(K["iris_dark"], float)
    light = np.minimum(base * 1.35 + 20, 255)
    col = np.ones((S, S, 3)) * base
    lo = np.clip((-v - 0.05) / 0.35, 0, 1)[..., None]           # lighter lower half
    col = col + (light - col) * lo * 0.75
    hi = np.clip((v - 0.02) / 0.25, 0, 1)[..., None]            # darker top (lid shadow)
    col = col + (dark - col) * hi * 0.85
    ring = np.exp(-((r - 0.62) / 0.05) ** 2)[..., None]         # faint ring band
    col = col + (dark - col) * ring * 0.35
    rim = np.clip((r - 0.86) / 0.10, 0, 1)[..., None]           # dark outer rim
    col = col + (np.array([20, 40, 26.0]) - col) * rim
    pup = (np.hypot(u / 0.52, v / 0.62) / 0.5) < K.get("pupil_r", 0.30)
    col[pup] = (24, 36, 28)
    a = np.zeros((S, S, 4), np.uint8); a[..., :3] = np.clip(col, 0, 255); a[..., 3] = 255
    return Image.fromarray(a, "RGBA").filter(ImageFilter.GaussianBlur(1.2))


def highlight_img():
    from PIL import Image, ImageDraw, ImageFilter
    S = 256; im = Image.new("RGBA", (S, S), (255, 255, 255, 0)); d = ImageDraw.Draw(im)
    d.ellipse((S * 0.05, S * 0.05, S * 0.95, S * 0.95), fill=(255, 255, 255, 255))
    return im.filter(ImageFilter.GaussianBlur(2))


# ---------------------------------------------------------------------------------------------------------------
def add_obj(name, verts, faces, mat, uvs=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    for p in me.polygons:
        p.use_smooth = True
    if uvs is not None:
        uv = me.uv_layers.new(name="UVMap")
        for l in me.loops:
            uv.data[l.index].uv = tuple(uvs[l.vertex_index])
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def ribbon(P, Nrm, w_in, w_out, depth, close=False, drape=False):
    """quad strip along polyline P (n,3) with in-plane outward normals Nrm (n,3); widths per point.
    drape: lay the outer edge on the skin (the skin rises away from the eye opening and buried the lash)"""
    verts, faces, uvs = [], [], []
    n = len(P)
    for i in range(n):
        a = P[i] - Nrm[i] * w_in[i]; b = P[i] + Nrm[i] * w_out[i]
        if drape:
            b[1] = max(b[1], surf_front(b[0], b[2]))
            a[1] = max(a[1], surf_front(a[0], a[2]))
        a = a + np.array([0, depth, 0]); b = b + np.array([0, depth, 0])
        verts += [a, b]; uvs += [(i / max(n - 1, 1), 0.0), (i / max(n - 1, 1), 1.0)]
    m = n if close else n - 1
    for i in range(m):
        j = (i + 1) % n
        faces.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    return verts, faces, uvs


def on_skin(x, z, lift):
    """point on the face surface (front) lifted along +y"""
    return np.array([x, surf_front(x, z) + lift, z])


def eye_parts():
    ew = K["eye_w_ipd"] * K["ipd"] * K["D"]
    white_m = make_mat("N00_000_00_EyeWhite_00_EYE", tex("EyeWhite", white_img()))
    iris_m = make_mat("N00_000_00_EyeIris_00_EYE", tex("EyeIris", iris_img()))
    hl_m = make_mat("N00_000_00_EyeHighlight_00_EYE", tex("EyeHighlight", highlight_img()), alpha=True)
    lash_m = make_mat("N00_000_00_FaceEyeline_00_FACE", tex("FaceEyeline", flat_img(K["lash_col"])))
    brow_m = make_mat("N00_000_00_FaceBrow_00_FACE", tex("FaceBrow", flat_img(K["brow_col"])))
    mouth_m = make_mat("N00_000_00_FaceMouth_00_FACE", tex("FaceMouth", flat_img(K["mouth_col"])))
    W_v, W_f, W_uv, I_v, I_f, I_uv, H_v, H_f, H_uv, L_v, L_f, L_uv, B_v, B_f, B_uv = ([] for _ in range(15))
    lift = K.get("line_lift", 0.0003)
    for c_open, c in zip(eye_centers(), pupil_centers()):
        side = np.sign(c[0])
        E = eye_curve(c_open, 160)
        yo = surf_front(c_open[0], c_open[1])
        R = K["eyeball_r"]; cen = np.array([c[0], yo - K["eyeball_back"] - R, c[1]])
        # --- eyeball: a flattened ellipsoid that covers the whole opening (a sphere left the corners empty and
        # the opening read narrow: R1 0.29 vs 0.42); sclera = ellipsoid with a hole where the iris sits
        rx, ry, rz = K.get("eye_rx", 0.6 * ew), K.get("eye_ry", 0.0085), K.get("eye_rz", 0.46 * ew)
        cen = np.array([c_open[0], yo - K["eyeball_back"] - ry, c_open[1]])
        def ell_y(x, z):
            q = 1 - ((x - cen[0]) / rx) ** 2 - ((z - cen[2]) / rz) ** 2
            return cen[1] + ry * math.sqrt(max(q, 0.0))
        ir = K["iris_r"]; asp = K["iris_aspect"]
        nr, ns = 16, 72
        base = len(W_v)
        for i in range(nr + 1):
            for j in range(ns):
                ph = 2 * math.pi * j / ns
                cp, sp = math.cos(ph), math.sin(ph)
                rho_i = 1.0 / math.sqrt((cp * rx / (ir * 0.97)) ** 2 + (sp * rz / (ir * asp * 0.97)) ** 2)
                rho = rho_i + (0.985 - rho_i) * (i / nr) ** 0.9
                x = cen[0] + rx * rho * cp; z = cen[2] + rz * rho * sp
                p = np.array([x, ell_y(x, z), z])
                W_v.append(p); W_uv.append((0.5 + (p[0] - c[0]) / (2.4 * ew), 0.5 + (p[2] - c[1]) / (1.6 * ew)))
        for i in range(nr):
            for j in range(ns):
                j2 = (j + 1) % ns
                W_f.append((base + i * ns + j, base + i * ns + j2, base + (i + 1) * ns + j2, base + (i + 1) * ns + j))
        # --- iris: concave disc; rim on the ellipsoid, centre iris_dish behind the rim
        base = len(I_v); nri, nsi = 10, 64
        rim_y = ell_y(c[0] + ir, c[1])
        # E9: the dish is measured rim minus centre, so put the centre iris_dish behind the rim (not the front)
        I_v.append(np.array([c[0], rim_y - K["iris_dish"], c[1]])); I_uv.append((0.5, 0.5))
        for i in range(1, nri + 1):
            t = i / nri
            for j in range(nsi):
                ph = 2 * math.pi * j / nsi
                x = c[0] + ir * t * math.cos(ph); z = c[1] + ir * asp * t * math.sin(ph)
                y = rim_y - K["iris_dish"] * (1 - t * t) + 0.00015
                I_v.append(np.array([x, y, z])); I_uv.append((0.5 + 0.5 * t * math.cos(ph), 0.5 + 0.5 * t * math.sin(ph)))
        for j in range(nsi):
            I_f.append((base, base + 1 + j, base + 1 + (j + 1) % nsi))
        for i in range(nri - 1):
            for j in range(nsi):
                j2 = (j + 1) % nsi
                a0 = base + 1 + i * nsi; a1 = base + 1 + (i + 1) * nsi
                I_f.append((a0 + j, a0 + j2, a1 + j2, a1 + j))
        rim_y = cen[1] + ry
        # --- highlights: big oval upper (towards the light side, same world side both eyes) + small dot low
        for (ox, oz, rx, rz) in K.get("hl", [(-0.42, 0.42, 0.30, 0.20), (0.40, -0.45, 0.12, 0.10)]):
            base = len(H_v); n_ = 20
            cx_ = c[0] + ox * ir; cz_ = c[1] + oz * ir * asp
            yh = ell_y(cx_, cz_) + 0.0004
            H_v.append(np.array([cx_, yh, cz_])); H_uv.append((0.5, 0.5))
            for j in range(n_):
                ph = 2 * math.pi * j / n_
                H_v.append(np.array([cx_ + rx * ir * math.cos(ph), yh, cz_ + rz * ir * math.sin(ph)]))
                H_uv.append((0.5 + 0.5 * math.cos(ph), 0.5 + 0.5 * math.sin(ph)))
            for j in range(n_):
                H_f.append((base, base + 1 + j, base + 1 + (j + 1) % n_))
        # --- lash line (upper, thick, wing) + thin lower line, along the opening curve
        P3 = np.array([on_skin(x, z, 0) for x, z in E])
        ctr = P3.mean(0)
        tan = np.roll(P3, -1, 0) - np.roll(P3, 1, 0)
        nrm = np.cross(tan, [0, 1, 0]); nrm[:, 1] = 0; nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
        od = P3 - ctr; od[:, 1] = 0
        nrm *= np.sign((nrm * od).sum(1))[:, None]
        n = len(E)
        # E starts at the inner corner (u = 0) and reaches the outer corner at u = 0.5 (top first)
        top_idx = np.arange(0, n // 2 + 1)
        f = top_idx / (n // 2)                                  # 0 inner .. 1 outer
        th0, th1 = K["lash_th"]
        wout = th0 + (th1 - th0) * np.sin(np.clip(f, 0, 1) * math.pi * 0.62) ** 1.2
        wout *= np.clip(f / 0.06, 0.25, 1)
        win = np.full(len(f), K.get("lash_in", 0.0006))
        Pt = P3[top_idx].copy(); Nt = nrm[top_idx].copy()
        # wing: continue past the outer corner along the curve tangent, curving slightly up, tapering
        tdir = P3[n // 2] - P3[n // 2 - 2]; tdir[1] = 0; tdir /= np.linalg.norm(tdir)
        up = np.array([0, 0, 1.0])
        wing = []
        for k_ in range(1, 9):
            t = k_ / 8
            q = P3[n // 2] + tdir * K["lash_wing"] * t + up * K["lash_wing"] * 0.25 * t * t
            q[1] = surf_front(q[0], q[2])
            wing.append(q)
        Pt = np.vstack([Pt, wing]); Nt = np.vstack([Nt, np.repeat(Nt[-1:], 8, 0)])
        wout = np.r_[wout, wout[-1] * (1 - np.linspace(1, 8, 8) / 8) ** 0.8 + 0.00005]
        win = np.r_[win, win[-1] * (1 - np.linspace(1, 8, 8) / 8)]
        v_, f_, uv_ = ribbon(Pt, Nt, win, wout, lift, drape=True)
        off = len(L_v); L_v += v_; L_f += [tuple(i + off for i in q) for q in f_]; L_uv += uv_
        # lower line: outer 70% of the bottom, thin
        bot_idx = np.arange(n // 2, n)                          # outer -> inner along the bottom
        fb = 1 - (bot_idx - n // 2) / (n // 2)                  # 1 outer .. 0 inner
        sel = fb > 0.28
        bi = bot_idx[sel]; fbs = fb[sel]
        wl = K["lowline_th"] * np.clip((fbs - 0.28) / 0.25, 0, 1) ** 0.7 * np.clip((1.02 - fbs) / 0.08, 0.2, 1)
        v_, f_, uv_ = ribbon(P3[bi], nrm[bi], np.full(len(bi), K.get("low_in", 0.0002)), wl, lift, drape=True)
        off = len(L_v); L_v += v_; L_f += [tuple(i + off for i in q) for q in f_]; L_uv += uv_
        # --- brow: angled thick stroke, inner end lower (stern MHS3 male), tapered tail
        bk = K.get("brow", [(-0.60, 0.46, 1.00), (-0.22, 0.555, 0.98), (0.20, 0.64, 0.85), (0.58, 0.655, 0.55),
                            (0.86, 0.59, 0.18)])
        bpts = []
        for (fx, fz, wt) in bk:                                 # fx: -inner .. +outer, in eye widths
            x = c[0] + side * fx * ew * 1.0 * -1 * -1
            bpts.append((c[0] + side * fx * ew, c[1] + fz * ew, wt))
        bp = np.array(bpts)
        tt = np.linspace(0, 1, 40); tk = np.linspace(0, 1, len(bp))
        bx = CubicSpline(tk, bp[:, 0])(tt); bz = CubicSpline(tk, bp[:, 1])(tt); bw = np.clip(CubicSpline(tk, bp[:, 2])(tt), 0.05, 1.2)
        BP = np.array([on_skin(x, z, 0) for x, z in zip(bx, bz)])
        tb = np.gradient(BP, axis=0); nb = np.stack([-tb[:, 2], np.zeros(len(tb)), tb[:, 0]], 1) * side * -1
        nb /= np.linalg.norm(nb, axis=1, keepdims=True)
        nb *= np.sign(nb[:, 2])[:, None]                       # +z = up
        th_b = K["brow_th"] * bw
        v_, f_, uv_ = ribbon(BP, nb, th_b * 0.45, th_b * 0.55, lift, drape=True)
        off = len(B_v); B_v += v_; B_f += [tuple(i + off for i in q) for q in f_]; B_uv += uv_
    objs = [add_obj("EyeWhite", W_v, W_f, white_m, W_uv), add_obj("EyeIris", I_v, I_f, iris_m, I_uv),
            add_obj("EyeHighlight", H_v, H_f, hl_m, H_uv), add_obj("FaceEyeline", L_v, L_f, lash_m, L_uv),
            add_obj("FaceBrow", B_v, B_f, brow_m, B_uv)]
    # --- mouth line (a hidden mesh just under the skin for the measure scripts; the visible line is in the skin
    # texture)
    xs, zz, tw = mouth_curve_pts(41)
    MP = np.array([on_skin(x, z, 0) for x, z in zip(xs, zz)])
    Nm = np.tile([0, 0, 1.0], (len(xs), 1))
    v_, f_, uv_ = ribbon(MP, Nm, tw * 0.5, tw * 0.5, K.get("mouth_lift", -0.0004))
    objs.append(add_obj("FaceMouth", v_, f_, mouth_m, uv_))
    return objs


def ear_parts(face_mat):
    """parametric ear per side: rim, concha dip, lobe; closed (front + back shell), skin material"""
    D = K["D"]; zp = K["z_chin"] + D
    eh, ewid = K.get("ear_h", 0.054), K.get("ear_w", 0.027)
    ztop = zp + K.get("ear_top", 0.022); yc = K.get("ear_y", -0.012)
    verts, faces, uvs = [], [], []
    nu, nv = 48, 8
    for sx in (-1, 1):
        # outline in (y, z): a rounded shape, wider at the top, narrow lobe
        U = np.linspace(0, 2 * np.pi, nu, endpoint=False)
        oy = yc + 0.5 * ewid * np.cos(U) * (0.75 + 0.25 * np.sin(U))
        oz = ztop - eh / 2 + 0.5 * eh * np.sin(U)
        cy, cz = yc + 0.002, ztop - eh * 0.45
        base = len(verts)
        def head_x(y, z):
            lo, hi = 0.05, math.pi - 0.05                      # bisection on theta for the side point at y
            for _ in range(40):
                mid = 0.5 * (lo + hi); _, ym = section(z, mid)
                if ym > y:
                    lo = mid
                else:
                    hi = mid
            x, _ = section(z, 0.5 * (lo + hi)); return float(x)
        for layer in (0, 1):                                    # 0 front (outer) surface, 1 back surface
            for i in range(nv + 1):
                s = i / nv                                      # 0 centre .. 1 rim
                for j in range(nu):
                    y = cy + (oy[j] - cy) * s; z = cz + (oz[j] - cz) * s
                    hx = head_x(y, z)
                    back_frac = np.clip((yc + 0.5 * ewid - y) / ewid, 0, 1)   # 0 front edge .. 1 back edge
                    stand = K.get("ear_base", 0.0055) + K.get("ear_out", 0.0085) * back_frac ** 1.2
                    if layer == 0:
                        h = stand + 0.0022 * s ** 6 - 0.0018 * math.exp(-((s - 0.45) / 0.22) ** 2) * (z > cz - eh * 0.25)
                    else:                                       # back shell sinks into the head (no gap)
                        h = min(stand - 0.0025, -0.0015 + 0.004 * back_frac) - 0.002 * (1 - s ** 2)
                    verts.append((sx * (hx + h), y, z)); uvs.append((0.5 + sx * 0.45, 0.5))
        L = (nv + 1) * nu
        for layer in (0, 1):
            o = base + layer * L
            for i in range(nv):
                for j in range(nu):
                    j2 = (j + 1) % nu
                    q = (o + i * nu + j, o + i * nu + j2, o + (i + 1) * nu + j2, o + (i + 1) * nu + j)
                    faces.append(q if (layer == 0) == (sx > 0) else q[::-1])
        # stitch the rims
        for j in range(nu):
            j2 = (j + 1) % nu
            a0 = base + nv * nu; a1 = base + L + nv * nu
            q = (a0 + j, a1 + j, a1 + j2, a0 + j2)
            faces.append(q if sx > 0 else q[::-1])
    return verts, faces, uvs


def proxy_normals(ob):
    """toon faces need one clean shadow shape: blend the head's normals towards those of a smooth ellipsoid proxy
    (Hina keeps a 'normals' group for the same thing; VRoid ships custom normals). Nose and ears keep more of their
    own normals so they still cast their small shadow shapes."""
    me = ob.data
    co = np.array([v.co[:] for v in me.vertices])
    me.update()
    vn = np.array([v.normal[:] for v in me.vertices])
    c = np.array(K.get("prox_c", (0.0, -0.02, 1.612))); r = np.array(K.get("prox_r", (0.14, 0.075, 0.14)))
    g = (co - c) / r ** 2; g /= np.linalg.norm(g, axis=1, keepdims=True) + 1e-12
    w = K.get("prox_w", 0.85) * np.ones(len(co))
    # less on the nose ridge, none on the ears (|x| beyond the skull) and on the neck
    nose = np.exp(-(co[:, 0] / 0.008) ** 2) * (co[:, 2] < K["z_chin"] + K["D"] - 0.004) * (co[:, 2] > K["z_chin"] + 0.04) * (co[:, 1] > 0.05)
    w *= 1 - 0.6 * nose
    w *= (np.abs(co[:, 0]) < 0.0875)
    w *= np.clip((co[:, 2] - K["z_chin"] + 0.004) / 0.012, 0, 1)
    n = vn * (1 - w[:, None]) + g * w[:, None]
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    me.normals_split_custom_set_from_vertices([tuple(x) for x in n])


def assemble(base_glb, out_glb, keep_hair=False):
    global TEXDIR
    TEXDIR = os.path.join(os.path.dirname(os.path.abspath(out_glb)), os.path.splitext(os.path.basename(out_glb))[0] + "_tex")
    os.makedirs(TEXDIR, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=base_glb)
    arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    head_bone = next(b.name for b in arm.data.bones if "C_Head" in b.name)
    neck_bone = next(b.name for b in arm.data.bones if "C_Neck" in b.name)
    kill = ("Face_00_SKIN", "EyeWhite", "EyeIris", "EyeHighlight", "FaceEyeline", "FaceBrow", "FaceMouth")
    if not keep_hair:
        kill = kill + ("HAIR",)
    body = None
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH" or not o.data.materials or not o.data.materials[0]:
            continue
        mn = o.data.materials[0].name
        if any(k in mn for k in kill):
            bpy.data.objects.remove(o)
        elif "Body_00_SKIN" in mn:
            body = o
    if body is not None:                                       # cut the body's own head off at the neck
        bm = bmesh.new(); bm.from_mesh(body.data); M = body.matrix_world
        cut = K.get("body_cut", 1.497)
        dv = [v for v in bm.verts if (M @ v.co).z > cut]
        bmesh.ops.delete(bm, geom=dv, context="VERTS"); bm.to_mesh(body.data); bm.free()
    head = build_head_mesh()
    ev, ef, euv = ear_parts(None)
    bm = bmesh.new(); bm.from_mesh(head.data)
    nv0 = len(bm.verts)
    vv = [bm.verts.new(v) for v in ev]
    for q in ef:
        try:
            bm.faces.new([vv[i] for i in q])
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)          # ears came out inside-out (dark discs)
    bm.to_mesh(head.data); bm.free()
    for p in head.data.polygons:
        p.use_smooth = True
    uv_front(head.data)
    proxy_normals(head)
    skin_tex = tex("Face_00_SKIN", skin_img())
    back_tex = tex("Body_01_SKIN_HeadBack", skin_img(back=True))
    face_m = make_mat("N00_000_00_Face_00_SKIN", skin_tex)
    head.data.materials.append(face_m)
    nf_head = len(head.data.polygons) - len(ef)               # faces before the ears were added
    # split like VRoid: the face object is the front mask (+ ears); the back of the skull and the neck are another
    # skin object. The locked renderer (vt_facenrm) sets the face normals from an ellipsoid fitted to the FACE
    # object's bounding box - with the neck and the whole skull in it the ellipsoid sat low and big and half the
    # face fell into shadow (S6 shadow area 0.28 vs 0.16)
    back = head.copy(); back.data = head.data.copy(); bpy.context.scene.collection.objects.link(back)
    back.name = "HeadBack"
    zc = K["z_chin"]; sy = K.get("split_y", -0.052)
    def is_face(p):
        if p.index >= nf_head:
            return True                                        # ears
        c = p.center
        return c.y > sy and c.z > zc - K.get("split_chin", 0.0025)
    for ob, keep_face in ((head, True), (back, False)):
        bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table()
        me_polys = ob.data.polygons
        kill = [bm.faces[p.index] for p in me_polys if is_face(p) != keep_face]
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        bm.to_mesh(ob.data); bm.free()
    back_m = make_mat("N00_000_00_Body_01_SKIN_HeadBack", back_tex)   # 'Body' -> outline, 'SKIN' -> toon,
    back.data.materials.clear(); back.data.materials.append(back_m)  # not 'Body_00_SKIN' -> no body tint
    parts = [head, back] + eye_parts()
    for o in parts:
        o.parent = arm
        vg = o.vertex_groups.new(name=head_bone); vn = o.vertex_groups.new(name=neck_bone)
        for v in o.data.vertices:
            z = v.co.z
            w = float(np.clip((z - K.get("neck_w0", 1.468)) / 0.03, 0, 1)); w = w * w * (3 - 2 * w)
            vg.add([v.index], w, "REPLACE")
            if w < 1:
                vn.add([v.index], 1 - w, "REPLACE")
        md = o.modifiers.new("Armature", "ARMATURE"); md.object = arm
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format="GLB", export_image_format="AUTO")
    print("wrote", out_glb, "head verts", len(head.data.vertices))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if "--knobs" in argv:
        set_knobs(argv[argv.index("--knobs") + 1])
    T = tables()
    glbs = [a for a in argv if a.endswith(".glb")]
    if len(glbs) >= 2:
        assemble(glbs[0], glbs[1], keep_hair="--keep-hair" in argv)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        ob = build_head_mesh()
        print("head verts", len(ob.data.vertices), "faces", len(ob.data.polygons))
        if glbs:
            bpy.ops.export_scene.gltf(filepath=glbs[-1], export_format="GLB")
            print("wrote", glbs[-1])
