"""Render-side measurements against an MHS3 front reference (q36): pupil-aligned face widths, eye opening, mouth,
and the cel-shading numbers (lit / shadow skin colour, shadow ratio, how hard the terminator is, shadow area).

    python3 mhs3_render_measure.py OUT.json RENDER_front.png [--ref docs/qa/head_v2/judge/leo_ref_front.png]

Units: IPD of the reference after aligning the render's pupils onto the reference pupils (pupil_align_board).
The same function measures the reference, so every number has a reference value next to it.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pupil_align_board import REFP, align  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def skin_mask(a):
    a = a.astype(int); r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r > 120) & (r - b > 25) & (r - b < 120) & (g > 80) & (r >= g) & (g > b)


def lum(a):
    a = a.astype(float); return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def widths(m, cx, cy, ipd, levels):
    out = {}
    for t in levels:
        y = int(round(cy + t * ipd)); row = m[y]; x = int(cx)
        if not row[max(x - 3, 0):x + 4].any():
            out["%.2f" % t] = None; continue
        l = x
        while l > 0 and row[max(l - 5, 0):l].any():
            l -= 1
        r = x
        while r < len(row) - 1 and row[r + 1:r + 6].any():
            r += 1
        out["%.2f" % t] = round((r - l) / ipd, 3)
    return out


def shading(a, m, cx, cy, ipd):
    """Skin pixels on the cheeks / lower face (below the eyes, inside the jaw)."""
    H, W = m.shape; yy, xx = np.mgrid[0:H, 0:W]
    box = (yy > cy + 0.25 * ipd) & (yy < cy + 1.25 * ipd) & (np.abs(xx - cx) < 0.75 * ipd) & m
    L = lum(a)[box]; C = a[box].astype(float)
    if len(L) < 200:
        return {}
    lo, hi = np.percentile(L, 5), np.percentile(L, 95)
    for _ in range(20):                                  # 2-means on luminance
        t = 0.5 * (lo + hi); s, l = L < t, L >= t
        if not s.any() or not l.any():
            break
        lo, hi = L[s].mean(), L[l].mean()
    t = 0.5 * (lo + hi)
    lit, sh = C[L >= t].mean(0), C[L < t].mean(0)
    band = (L > lo + 0.2 * (hi - lo)) & (L < hi - 0.2 * (hi - lo))
    # histogram view (q36): lit peak, the main cel shadow band (0.68-0.90 of lit) and deep accents (< 0.68 of lit)
    lp = float(np.median(L[L >= np.percentile(L, 60)]))
    main_sh = (L < 0.90 * lp) & (L >= 0.68 * lp); deep = L < 0.68 * lp
    return {"lit_rgb": [round(float(x), 1) for x in lit], "shadow_rgb": [round(float(x), 1) for x in sh],
            "shadow_ratio_2means": round(float(lum(sh[None])[0] / max(lum(lit[None])[0], 1)), 3),
            "shadow_ratio_rgb": [round(float(s_ / max(l_, 1)), 3) for s_, l_ in zip(sh, lit)],
            "lit_peak": round(lp, 1),
            "shadow_ratio": round(float(np.median(L[main_sh]) / lp), 3) if main_sh.any() else None,
            "shadow_warmth": round(float(_warm(C, L, main_sh, lp)), 3) if main_sh.any() else None,
            "shadow_area": round(float((L < 0.90 * lp).mean()), 3),
            "deep_frac": round(float(deep.mean()), 3),
            "terminator_soft": round(float(band.mean()), 3),
            "lit_texture_sd": round(float(L[L >= t + 0.15 * (hi - lo)].std()), 2)}


def _warm(C, L, main_sh, lp):
    """Hue of the cel shadow: (R ratio) - mean(G, B ratio) of the main shadow band against the lit peak pixels."""
    litpx = C[np.abs(L - lp) < 6].mean(0); shp = C[main_sh].mean(0); r = shp / np.maximum(litpx, 1)
    return r[0] - 0.5 * (r[1] + r[2])


def eye_box(a, m, px, py, ipd):
    """Eye opening = non-skin pixels around the pupil that are eye white, iris or lash (the hair fringe excluded by
    staying below the brow line)."""
    y0, y1 = int(py - 0.20 * ipd), int(py + 0.18 * ipd); x0, x1 = int(px - 0.36 * ipd), int(px + 0.36 * ipd)
    sub = a[y0:y1, x0:x1].astype(int); sk = m[y0:y1, x0:x1]
    L = lum(sub); sat = (sub.max(-1) - sub.min(-1)) / (sub.max(-1) + 1)
    white = (L > 150) & (sat < 0.22) & ~sk
    iris = (sat > 0.15) & ~sk & (L < 200) & (sub[..., 1] >= sub[..., 0] - 4)   # green / grey irises (brows are brown)
    dark = L < 70
    e = white | (iris & ~dark)
    from scipy import ndimage
    lab, n = ndimage.label(e)
    if n == 0:
        return None
    cyx = (int(py) - y0, int(px) - x0)
    e = ndimage.binary_closing(e, iterations=2)
    lab, n = ndimage.label(e)
    k = lab[cyx] if lab[cyx] else np.argmax(ndimage.sum(e, lab, range(1, n + 1))) + 1
    ys, xs = np.where(lab == k)
    wy, wx = np.where((lab == k) & white)
    comp = lab == k
    ir = comp & iris
    bb = np.zeros_like(comp); bb[ys.min():ys.max() + 1, xs.min():xs.max() + 1] = True
    irm = float(np.median(L[ir])) if ir.any() else 120.0
    iy, ix = np.where(ir) if ir.any() else (np.array([cyx[0]]), np.array([cyx[1]]))
    icy, icx = iy.mean(), ix.mean(); iR = max(np.sqrt(len(iy) / np.pi), 1.0)
    yy_, xx_ = np.mgrid[0:L.shape[0], 0:L.shape[1]]
    core = np.hypot(yy_ - icy, xx_ - icx) < 0.62 * iR             # inside the iris, away from rim and lash
    pu = core & (L < 0.42 * irm) & ~sk & ~white   # pupil: much darker than the iris (Leo's is dark green, not black)
    out = {"w": round((xs.max() - xs.min()) / ipd, 3), "h": round((ys.max() - ys.min()) / ipd, 3),
           "white_frac": round(float(len(wy)) / max(len(ys), 1), 3),
           "pupil_frac": round(float(pu.sum()) / max(float(np.pi * iR * iR), 1.0), 3),
           "iris_lum": round(float(L[ir].mean()), 1) if ir.any() else None,
           "white_warm": round(float((sub[..., 0] - sub[..., 2])[comp & white].mean()), 1) if (comp & white).any() else None,
           "top": int(ys.min()) + y0}
    # walking up the pupil column from the top of the white/iris: [gap] lash run, skin, brow run (IPD units)
    colL = lum(a[max(int(py - 0.6 * ipd), 0):out["top"] + 1, int(px) - 2:int(px) + 3].astype(int)).mean(1)[::-1]
    dk = colL < 125; runs = []; i = 0; n = len(dk)
    while i < n:
        j = i
        while j < n and dk[j] == dk[i]:
            j += 1
        runs.append((bool(dk[i]), i, j)); i = j
    dr = [r for r in runs if r[0] and r[2] - r[1] >= 2]
    if dr:
        out["lash_gap"] = round(dr[0][1] / ipd, 3); out["lash_th"] = round((dr[0][2] - dr[0][1]) / ipd, 3)
    if len(dr) > 1:
        out["brow_gap"] = round((dr[1][1] - dr[0][2]) / ipd, 3); out["brow_th"] = round((dr[1][2] - dr[1][1]) / ipd, 3)
    # q36 eye-shape standard (Sammy: 'the eye shape is not matching the mhs3 one ... this is also a standard'):
    # the opening outline sampled at 9 fractions across its width - top and bottom edge heights relative to the
    # pupil, in units of the opening width; corner heights give the tilt. Leo is measured by the same code.
    comp_f = ndimage.binary_fill_holes(ndimage.binary_closing(comp, iterations=2))
    x0c, x1c = xs.min(), xs.max(); wpx = max(x1c - x0c, 1); yc = 0.5 * (ys.min() + ys.max())
    side = -1 if px < a.shape[1] / 2 else 1          # viewer-left eye: its outer corner is on the image left
    fr = np.linspace(0.06, 0.94, 9)
    if side == -1:
        fr = fr[::-1]                                  # always sample inner corner -> outer corner
    top, bot = [], []
    for f in fr:
        cx_ = int(round(x0c + f * wpx)); tt, bb_ = [], []
        for dc in range(-3, 4):                       # median over 7 columns: lash notches / catch lights
            cc = min(max(cx_ + dc, 0), comp_f.shape[1] - 1); col_ = np.where(comp_f[:, cc])[0]
            if len(col_):
                tt.append(col_.min()); bb_.append(col_.max())
        top.append(round(float(np.median(tt) - yc) / wpx, 3) if tt else None)
        bot.append(round(float(np.median(bb_) - yc) / wpx, 3) if bb_ else None)
    out["shape_top"], out["shape_bot"] = top, bot     # inner -> outer, units of opening width, + = down
    inner = ys[xs <= x0c + 2] if side == 1 else ys[xs >= x1c - 2]
    outer = ys[xs >= x1c - 2] if side == 1 else ys[xs <= x0c + 2]
    out["corner_tilt"] = round(float(np.mean(inner) - np.mean(outer)) / wpx, 3)   # > 0: outer corner higher
    out["side"] = side
    return out


def measure_img(im, ref_name, ref):
    if im is ref:
        a = np.asarray(ref.convert("RGB")); pr = np.array(REFP[ref_name], float)
    else:
        al, pr, po, s = align(im, ref, ref_name); a = np.asarray(al)
    cx, cy = pr.mean(0); ipd = np.linalg.norm(pr[1] - pr[0]); m = skin_mask(a)
    L = lum(a); col = L[:, int(round(cx))]
    ys = [y for y in range(int(cy + 0.9 * ipd), min(int(cy + 1.8 * ipd), len(col))) if col[y] < 95]
    chin = ys[0] if ys else None                                   # the chin outline on the centre column
    out = {"widths_ipd": widths(m, cx, cy, ipd, [0.6, 0.75, 0.9, 1.05, 1.2]), "D_ipd": round((chin - cy) / ipd, 3) if chin else None}
    if chin:
        D = chin - cy                                              # widths at fractions of D (pupils .. chin), in D
        out["widths_D"] = widths(m, cx, cy, D, [0.40, 0.48, 0.56, 0.72, 0.80])   # skips the mouth row (0.64)
    out["shading"] = shading(a, m, cx, cy, ipd)
    if chin:
        lp = out["shading"].get("lit_peak", 190)
        y0, y1 = int(cy + 0.55 * D), int(cy + 0.75 * D); x0, x1 = int(cx - 0.45 * D), int(cx + 0.45 * D)
        dk = L[y0:y1, x0:x1] < 0.72 * lp
        r = int(np.argmax(dk.sum(1))); row = dk[max(r - 1, 0):r + 2].any(0)
        c = int(round(cx)) - x0
        if row[max(c - 6, 0):c + 7].any():
            l = c; rr = c
            while l > 0 and row[max(l - 6, 0):l].any():
                l -= 1
            while rr < len(row) - 1 and row[rr + 1:rr + 7].any():
                rr += 1
            out["mouth"] = {"w_D": round((rr - l) / D, 3), "y_D": round((y0 + r - cy) / D, 3)}
    for nm, p in (("eye_l", pr[0]), ("eye_r", pr[1])):
        out[nm] = eye_box(a, m, p[0], p[1], ipd)
    return out


def main():
    out, img = sys.argv[1], sys.argv[2]
    rp = sys.argv[sys.argv.index("--ref") + 1] if "--ref" in sys.argv else os.path.join(REPO, "docs/qa/head_v2/judge/leo_ref_front.png")
    ref = Image.open(rp).convert("RGB"); rn = os.path.basename(rp)
    res = {"render": measure_img(Image.open(img), rn, ref), "ref": measure_img(ref, rn, ref), "ref_path": rp}
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
