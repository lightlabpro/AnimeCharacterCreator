"""q33 MHS3 repaint of the VRoid face textures (Sammy: "they must resemble mhs3 models, but not exact copies ... a bit of
realism, but still anime, just like mhs3 ... I don't want the facial features to look like vroid").

    python3 mhs3_paint.py TEX_IN_DIR TEX_OUT_DIR [--mesh vroid_mesh.npz] [--knobs knobs.json]

Repaints, in the VRoid UV layouts (so any VRoid export can take them):
- EyeIris: MHS3 iris - light muted iris, darker upper band (lid shadow), thin dark rim, a lighter mid ring, faint
  radial strands, oval pupil, pale specks low in the iris. (VRoid: big flat iris with a gradient blob.)
- EyeHighlight: one small catch light + a tiny speck (VRoid: two big round white blobs - its signature).
- FaceEyeline: smooth thick upper lash line, thickest at the outer end, turning down round the outer corner, no
  flicks; thin light lower lid line; a thin crease line above (VRoid: spiky flicks, dots, a pale fold streak).
- FaceBrow: heavier, lower-set brush brows, a solid lower edge with hair strokes, inner end thick.
- Face: bandage removed; MHS3 nose = broad pale wedge down the lit side of the bridge + a warm brown wing shape under
  the tip; lower-lip shade; soft warm cheek; mouth line kept thin. Painted by 3D position (front projection) through
  the face mesh UVs (--mesh: vroid_mesh.npz from vr_dump.py).
Layout facts (measured on the VRoid textures): eyeline left half = one eye, outer corner at the LEFT (x~100-130 hook),
lid edge flat at row 119, lower lash rows 121-128; right half mirrored. Brow left half x 180-443 rows 81-155, inner end
at the right. Iris ovals centred (258, 260) and (765, 260), radii ~111 x 125 px. Highlight blobs at (172-232, 166-220)
and (228-302, 317-382) (left eye), mirrored.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

K = dict(
    iris=(146, 176, 124), iris_dark=(74, 104, 70), iris_rim=(38, 62, 40), pupil=(20, 34, 24), iris_ring=(196, 226, 170),
    lash=(42, 26, 20), lash_low=(150, 104, 84), crease=(168, 112, 92), brow=(74, 48, 32),
    nose_hl=(255, 236, 222), nose_tip=(196, 140, 112), lip=(198, 132, 108), mouth=(96, 52, 44), cheek=(232, 160, 140),
    lash_t_outer=36, lash_t_inner=18, brow_drop=10,
)


def load(p):
    return Image.open(p).convert("RGBA")


def iris(img):
    W, H = img.size
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = np.zeros((H, W, 4), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for cx in (258.0, 765.0):
        cy, rx, ry = 260.0, 111.0, 125.0
        u = (xx - cx) / rx; v = (yy - cy) / ry; r = np.hypot(u, v); th = np.arctan2(v, u)
        inside = r <= 1.0
        base = np.array(K["iris"], np.float32)
        # vertical: lighter low, darker top (lid shadow band, ~top 38%)
        top = np.clip((-v - 0.38) / 0.30, 0, 1) ** 0.8   # m11: a band only above the pupil (it merged with the pupil into a keyhole)
        col = base * (1 - top[..., None]) + np.array(K["iris_dark"], np.float32) * top[..., None]
        col = col * (1 + 0.10 * np.clip(v, 0, 1)[..., None]) * (1 - 0.22 * np.clip(-v, 0, 1)[..., None])   # brighter low, darker high
        # faint radial strands
        strands = 0.025 * np.sin(th * 26 + 1.3) * np.clip((r - 0.35) / 0.4, 0, 1) * np.clip((0.95 - r) / 0.2, 0, 1)
        col = col * (1 + strands[..., None])
        # lighter mid ring
        ring = np.exp(-((r - 0.60) / 0.07) ** 2) * 0.22   # m5: a crisp ring read as a VRoid/target iris
        col = col * (1 - ring[..., None]) + np.array(K["iris_ring"], np.float32) * ring[..., None]
        # dark rim
        rim = np.clip((r - 0.80) / 0.10, 0, 1)
        col = col * (1 - rim[..., None]) + np.array(K["iris_rim"], np.float32) * rim[..., None]
        # pupil (vertical oval, slightly high)
        pr = np.hypot((xx - cx) / (rx * 0.40), (yy - (cy + 12)) / (ry * 0.22))   # m12: the mesh stretches the top - short, low oval
        pm = np.clip((1.0 - pr) / 0.08, 0, 1)
        col = col * (1 - pm[..., None]) + np.array(K["pupil"], np.float32) * pm[..., None]
        # pale specks low in the iris
        for dx, dy, s in ((-0.45, 0.55, 0.07), (0.05, 0.68, 0.055), (0.42, 0.50, 0.05)):
            sm = np.exp(-(((u - dx) / s) ** 2 + ((v - dy) / s) ** 2))
            col = col * (1 - 0.7 * sm[..., None]) + np.array([235, 250, 220], np.float32) * 0.7 * sm[..., None]
        alpha = np.clip((1.0 - r) / 0.02, 0, 1) * 255
        a[inside, :3] = col[inside]; a[..., 3] = np.maximum(a[..., 3], alpha)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def iris3d(img, mesh):
    """m13: VRoid's iris mesh distorts its texture strongly (its own art is pre-distorted), so a circle painted in UV
    space rendered as a tall keyhole. Paint the iris by front-projected 3D position through the mesh UVs instead:
    a circle here renders as a circle."""
    W, H = img.size
    P = tex3d(mesh, "EyeIris_00_EYE", W, H)
    V = mesh["EyeIris_00_EYE__V"]
    a = np.zeros((H, W, 4), np.float32)
    ok = ~np.isnan(P[..., 0]); X = np.nan_to_num(P[..., 0]); Z = np.nan_to_num(P[..., 2])
    for sgn in (1, -1):
        vs = V[V[:, 0] * sgn > 0]
        cx, cz = vs[:, 0].mean(), vs[:, 2].mean()
        R = K.get("iris_R", 0.0128)
        u = (X - cx) / R; v = -(Z - cz) / R                 # v > 0 = below the centre
        r = np.hypot(u, v); th = np.arctan2(v, u)
        m = ok & (X * sgn > 0) & (r <= 1.0)
        base = np.array(K["iris"], np.float32)
        col = base[None, None] * np.ones((H, W, 1), np.float32)
        col = col * (1 + 0.12 * np.clip(v, 0, 1)[..., None]) * (1 - 0.30 * np.clip(-v, 0, 1)[..., None])
        top = np.clip((-v - 0.35) / 0.35, 0, 1)
        col = col * (1 - top[..., None]) + np.array(K["iris_dark"], np.float32) * top[..., None]
        col = col * (1 + (0.025 * np.sin(th * 26 + 1.3) * np.clip((r - 0.35) / 0.4, 0, 1))[..., None])
        ring = np.exp(-((r - 0.60) / 0.07) ** 2) * 0.22
        col = col * (1 - ring[..., None]) + np.array(K["iris_ring"], np.float32) * ring[..., None]
        rim = np.clip((r - 0.80) / 0.10, 0, 1)
        col = col * (1 - rim[..., None]) + np.array(K["iris_rim"], np.float32) * rim[..., None]
        pm = np.clip((1.0 - np.hypot(u / 0.34, (v + 0.02) / 0.40)) / 0.08, 0, 1)
        col = col * (1 - pm[..., None]) + np.array(K["pupil"], np.float32) * pm[..., None]
        for dx, dy, s in ((-0.45, 0.55, 0.08), (0.05, 0.68, 0.06), (0.42, 0.50, 0.06)):
            sm = np.exp(-(((u - dx) / s) ** 2 + ((v - dy) / s) ** 2)) * 0.7
            col = col * (1 - sm[..., None]) + np.array([235, 250, 220], np.float32) * sm[..., None]
        al = np.clip((1.0 - r) / 0.03, 0, 1) * 255
        a[m, :3] = col[m]; a[m, 3] = al[m]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def highlight3d(img, mesh):
    """Catch lights placed by 3D position: one soft white ellipse up and toward the lit side, a small one low."""
    W, H = img.size
    P = tex3d(mesh, "EyeHighlight_00_EYE", W, H); Vi = mesh["EyeIris_00_EYE__V"]
    a = np.zeros((H, W, 4), np.float32)
    ok = ~np.isnan(P[..., 0]); X = np.nan_to_num(P[..., 0]); Z = np.nan_to_num(P[..., 2])
    lit = K.get("lit_sign", -1.0); R = K.get("iris_R", 0.0128)
    for sgn in (1, -1):
        vs = Vi[Vi[:, 0] * sgn > 0]; cx, cz = vs[:, 0].mean(), vs[:, 2].mean()
        for (dx, dz, rx, rz, al) in ((0.38, 0.30, 0.20, 0.13, 255), (-0.25, -0.55, 0.09, 0.07, 220)):
            hx, hz = cx + lit * dx * R, cz + dz * R
            e = np.hypot((X - hx) / (rx * R), (Z - hz) / (rz * R))
            m = ok & (X * sgn > 0)
            a[..., :3] = np.where((m & (e < 1.2))[..., None], 255.0, a[..., :3])
            a[..., 3] = np.maximum(a[..., 3], np.where(m, np.clip((1.0 - e) / 0.25, 0, 1) * al, 0))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def highlight(img):
    W, H = img.size
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(out)
    # the mesh quads only cover the original blobs: keep the new marks inside them
    for (x0, x1, y0, y1), (x2, x3, y2, y3) in (((172, 232, 166, 220), (228, 302, 317, 382)),
                                               ((674, 731, 169, 223), (722, 796, 317, 382))):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        d.ellipse([cx - 16, cy - 11, cx + 16, cy + 11], fill=(255, 255, 255, 255))
        cx, cy = (x2 + x3) / 2, (y2 + y3) / 2
        d.ellipse([cx - 13, cy - 10, cx + 13, cy + 10], fill=(255, 255, 255, 240))   # m12: the top light hides under the lash
    return out.filter(ImageFilter.GaussianBlur(0.8))


def eyeline(img):
    W, H = img.size
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(out)
    for side in (0, 1):
        def X(x):                                   # x in left-half coords (outer at the left) -> texture x
            return x if side == 0 else W - 1 - x
        x_out, x_in, lid = 104, 470, 119
        top, bot = [], []
        for x in np.linspace(x_out + 6, x_in, 80):
            s = (x - x_out) / (x_in - x_out)          # 0 outer .. 1 inner
            t = K["lash_t_inner"] + (K["lash_t_outer"] - K["lash_t_inner"]) * (1 - s) ** 1.4
            t *= 1 - 0.75 * np.clip((s - 0.85) / 0.15, 0, 1)   # taper at the inner corner
            top.append((X(x), lid - t)); bot.append((X(x), lid + 1))
        # outer corner turns down (hook), smooth
        hook = [(X(x_out + 6), lid - K["lash_t_outer"] * 0.8), (X(x_out), lid - 6), (X(x_out + 4), lid + 6),
                (X(x_out + 12), lid + 9), (X(x_out + 22), lid + 3)]   # m3: the hook hung low like a flick
        d.polygon(top + bot[::-1], fill=K["lash"] + (255,))
        d.polygon(hook, fill=K["lash"] + (255,))
        # lower lid line, thin, light, outer two thirds
        pts = [(X(x), 124 - 2.2 * (1 - (x - 200) / 216)) for x in np.linspace(200, 416, 40)]
        pts2 = [(X(x), 124 + 0.8 + 1.2 * (1 - (x - 200) / 216)) for x in np.linspace(416, 200, 40)]
        d.polygon(pts + pts2, fill=K["lash_low"] + (230,))
        # crease line above the lid (MHS3 double-lid line), thin
        cr = [(X(x), 56 + 10 * ((x - 290) / 140) ** 2) for x in np.linspace(170, 420, 40)]
        d.line(cr, fill=K["crease"] + (200,), width=3)
    return out.filter(ImageFilter.GaussianBlur(0.6))


def brow(img):
    """MHS3 brow: one tapered brush stroke - thick, squared inner end low toward the nose, tapering to a point at the
    outer end, a slight arch; darker hair strokes inside following the stroke (m2/m3 boxes with a comb top read badly)."""
    W, H = img.size
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(out)
    for side in (0, 1):
        def X(x):
            return x if side == 0 else W - 1 - x
        # m6 (UV overlay): the brow mesh is a two-row strip - top row x 160-460 rows 68-128, lower row only x 280-460
        # rows 128-190 (the inner end). A flat-topped shape read as a block: both edges now slope down to the inner end.
        xs = np.linspace(185, 448, 80); s = (xs - 185) / 263            # 0 outer .. 1 inner
        # m8 (ray-cast check: the brow sits in front of the skin): the strip's lower row is tiny in 3D, so only the top
        # row (rows 68-128) shows - the whole brow is drawn inside it
        top = 86 - 8 * np.sin(np.pi * s) + 22 * s ** 1.6                # slight arch, then down toward the nose
        bot = 104 - 6 * np.sin(np.pi * s) + 48 * s ** 1.3               # thick inner end (VRoid's own brow: rows 81-155)
        d.polygon([(X(x), t) for x, t in zip(xs, top)] + [(X(x), b) for x, b in zip(xs[::-1], bot[::-1])],
                  fill=K["brow"] + (255,))
        # m10 TypeSafe brows_hatch 0.88 (Leia control 0.34): no stroke pattern - a solid stroke, darker along the lower edge
        dark = tuple(int(c * 0.72) for c in K["brow"])
        top2 = top + (bot - top) * 0.45
        d.polygon([(X(x), t) for x, t in zip(xs, top2)] + [(X(x), b) for x, b in zip(xs[::-1], bot[::-1])],
                  fill=dark + (255,))
    return out.filter(ImageFilter.GaussianBlur(1.0))


def eyewhite(img):
    """MHS3 sclera: grey-white, a broad cool lid shadow at the top (VRoid: bright white with a soft grey cap)."""
    a = np.asarray(img).astype(np.float32)
    H = a.shape[0]
    rows = np.arange(H, dtype=np.float32)[:, None]
    lum = a[..., :3].mean(-1, keepdims=True)
    base = np.array([198, 198, 208], np.float32)   # m10 white_bright 0.81 (control 0.61)
    shade = np.array([140, 142, 162], np.float32)
    t = np.clip((lum - 120) / 135, 0, 1)                    # the VRoid gradient: dark cap -> white
    col = shade * (1 - t) + base * t
    a[..., :3] = col
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def tex3d(mesh, key, W, H):
    """Per-texel 3D position (front-projected x, z, plus y) by rasterising the mesh's triangles in UV space."""
    V, T, UVT = mesh[key + "__V"], mesh[key + "__T"], mesh[key + "__UVT"]
    P = np.full((H, W, 3), np.nan, np.float32)
    for t in range(len(T)):
        uv = UVT[t] * np.array([W, H]); uv[:, 1] = H - uv[:, 1]
        x0, y0 = np.floor(uv.min(0)).astype(int); x1, y1 = np.ceil(uv.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W - 1), min(y1, H - 1)
        if x1 < x0 or y1 < y0:
            continue
        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1] + 0.5
        a, b, c = uv
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        w0 = ((b[1] - c[1]) * (xx - c[0]) + (c[0] - b[0]) * (yy - c[1])) / den
        w1 = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / den
        w2 = 1 - w0 - w1
        m = (w0 >= -0.01) & (w1 >= -0.01) & (w2 >= -0.01)
        p = (w0[..., None] * V[T[t, 0]] + w1[..., None] * V[T[t, 1]] + w2[..., None] * V[T[t, 2]])
        sub = P[y0:y1 + 1, x0:x1 + 1]; sub[m] = p[m]
    return P


def face(img, mesh):
    W, H = img.size
    a = np.asarray(img).astype(np.float32)
    P = tex3d(mesh, "Face_00_SKIN", W, H)
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    ok = ~np.isnan(x)
    x, y, z = np.nan_to_num(x), np.nan_to_num(y), np.nan_to_num(z)
    z0, ipd = 1.6093, 0.0796                         # pupil line, pupil distance (metres) on the VRoid face
    lit = K.get("lit_sign", -1.0)                     # this export faces +Y: world -x = viewer's right = the lit side (m3)
    u = lit * x / ipd; dd = (z0 - z) / ipd            # IPD units: + toward the lit side / below the pupils
    front = ok & (y > 0.02)
    skin = np.median(a[front & (np.abs(u) < 0.3) & (dd > 0.2) & (dd < 0.4), :3], axis=0)

    warm = np.array(K.get("skin_warm", (1.04, 0.92, 0.82)), np.float32) * K.get("skin_scale", 0.86)
    a[..., :3] *= warm                               # m4/m7: warm skin baked in (Leo lit cheek 226,187,158) so the
    skin = skin * warm                               # shader tint stays neutral and pale highlights stay pale

    def blend(mask, col, alpha):
        m = (np.clip(mask, 0, 1) * alpha)[..., None]
        a[..., :3] = a[..., :3] * (1 - m) + np.array(col, np.float32) * m
    # bandage off (left cheek, a beige patch): paint skin over anything far from the skin colour on the cheeks
    cheek = front & (np.abs(u) > 0.25) & (dd > 0.15) & (dd < 0.95)
    diff = np.abs(a[..., :3] - skin).sum(-1)
    blend(cheek & (diff > 18), skin, 1.0)
    # soft warm cheek (MHS3 painted warmth, low)
    for s in (-1, 1):
        r = np.hypot((u - s * 0.60) / 0.24, (dd - 0.36) / 0.12)
        blend(front * np.exp(-r ** 2), K["cheek"], 0.10)   # m2: low and wide read as a pink jaw
    # nose: pale wedge down the lit side - narrow under the eye line, widening down the bridge, bottom edge slanting up
    # and out; soft 1-2 px edge (m5: a stepped hard strip, TypeSafe artifacts 0.92)
    t = np.clip((dd - 0.12) / 0.33, 0, 1)
    e_in = 0.020 + 0.025 * t; e_out = 0.055 + 0.105 * t
    bottom = 0.45 - 0.45 * np.clip(u - 0.06, 0, None)
    sdf_w = np.minimum.reduce([u - e_in, e_out - u, dd - 0.12, bottom - dd])
    wedge = front * np.clip(sdf_w / 0.006, 0, 1)
    blend(wedge, K["nose_hl"], 0.75)
    # m3: the wing read as a sharp boomerang bar -> MHS3: a small soft rounded shape under the tip, darker in the middle
    au = np.abs(u)
    r = np.hypot(u / 0.115, (dd - 0.505) / 0.030)
    tip = front * np.clip((1.0 - r) / 0.35, 0, 1)
    blend(tip, K["nose_tip"], 0.65)
    core = front * np.clip((1.0 - np.hypot(u / 0.05, (dd - 0.515) / 0.016)) / 0.5, 0, 1)
    blend(core, (170, 112, 92), 0.45)
    # erase VRoid's own mouth line (measured: dd 0.79-0.80, |u| < 0.22) before drawing ours on the same row
    lum = a[..., :3].mean(-1)
    old = front & (np.abs(u) < 0.26) & (np.abs(dd - 0.796) < 0.03) & (lum < skin.mean() - 12)
    blend(np.where(old, 1.0, 0.0), skin, 1.0)
    # mouth line: darker, wider than VRoid's (Leo 0.67 IPD), tapered ends, a touch heavier in the middle
    ml = front * np.exp(-((u / 0.30) ** 8)) * np.exp(-(((dd - 0.796) / (0.006 + 0.004 * np.exp(-(u / 0.15) ** 2))) ** 2))
    blend(ml, K["mouth"], 0.85)
    # q33 m15: MHS3 face shading is PAINTED - clean soft shapes that do not depend on the mesh normals (TypeSafe culprit
    # skin_shading on every dynamic-light variant). Shadow side = -u. (1) a band down the far side of the face, narrow
    # at the temple, wider over the cheek and jaw, soft inner edge; (2) the nose's shadow side + a small cast shadow
    # beside the tip; (3) a soft shade under the lower lip / chin dimple. Rendered with a near-frontal key light.
    if K.get("paint_shadow", False):   # m16: invisible in front view, no TypeSafe gain - off
        sh_col = skin * np.array(K.get("paint_shadow_tint", (0.82, 0.78, 0.82)), np.float32)
        edge = -(0.62 + 0.10 * np.clip((0.2 - dd) / 0.8, 0, 1) - 0.08 * np.clip((dd - 0.3) / 0.9, 0, 1))
        band = front * np.clip((edge - u) / 0.06, 0, 1) * (dd > -0.9)
        blend(band, sh_col, 1.0)
        nose_sh = front * np.clip((-u - 0.015) / 0.012, 0, 1) * np.clip((0.07 + 0.06 * np.clip((dd - 0.15) / 0.3, 0, 1) + u) / 0.02, 0, 1) \
            * np.clip((dd - 0.15) / 0.06, 0, 1) * np.clip((0.50 - dd) / 0.03, 0, 1)
        blend(nose_sh, sh_col, 0.55)
        chin_sh = front * np.exp(-((u / 0.16) ** 2)) * np.exp(-(((dd - 0.97) / 0.05) ** 2))
        blend(chin_sh, sh_col, 0.35)
    # lower-lip shade (mouth line at dd ~0.76)
    lip = front * np.exp(-((u / 0.19) ** 6)) * np.exp(-(((dd - 0.885) / 0.028) ** 2))
    blend(lip, K["lip"], 0.75)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    arg = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
    if arg("--knobs"):
        K.update(json.load(open(arg("--knobs"))))
    os.makedirs(dst, exist_ok=True)
    n = lambda k: os.path.join(src, "N00_000_00_%s.png" % k)
    o = lambda k: os.path.join(dst, "N00_000_00_%s.png" % k)
    iris(load(n("EyeIris_00_EYE"))).save(o("EyeIris_00_EYE"))
    highlight(load(n("EyeHighlight_00_EYE"))).save(o("EyeHighlight_00_EYE"))
    eyewhite(load(n("EyeWhite_00_EYE"))).save(o("EyeWhite_00_EYE"))
    eyeline(load(n("FaceEyeline_00_FACE"))).save(o("FaceEyeline_00_FACE"))
    brow(load(n("FaceBrow_00_FACE"))).save(o("FaceBrow_00_FACE"))
    if arg("--mesh"):
        mesh = np.load(arg("--mesh"))
        face(load(n("Face_00_SKIN")), mesh).save(o("Face_00_SKIN"))
        iris3d(load(n("EyeIris_00_EYE")), mesh).save(o("EyeIris_00_EYE"))          # replaces the UV-space iris
        # highlight3d: the highlight mesh only has quads where VRoid's blobs were - placed in 3D it mostly fell off them
        # (kept in UV space, highlight())
    print("painted ->", dst)


if __name__ == "__main__":
    main()
