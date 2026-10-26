"""Silhouette comparison of a model render against its reference view (parts workflow, stage 3 fixes).

    python3 sil_compare.py RENDER.png REFERENCE.png [--json out.json] [--side]

Both silhouettes are scaled to the same unit u = skull top -> eye line (eyes found as the darkest pixels inside the
head in the upper 60 %), so a render and a drawing of different size and framing compare. Prints, per row in u:
left and right edge (front/back views: half widths about the eye centre; --side: front edge and back edge), and
IoU of the two aligned masks. The model render needs an alpha channel; the reference has a flat background.
"""
import json
import sys

import numpy as np
from PIL import Image


def mask_of(path):
    im = Image.open(path)
    a = np.asarray(im.convert("RGBA")).astype(float)
    if a[..., 3].min() < 250:
        return a[..., 3] > 128, a[..., :3]
    rgb = a[..., :3]
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg = np.median(border, axis=0)
    return np.abs(rgb - bg).max(axis=2) > 30, rgb


def landmarks(m, rgb):
    ys, xs = np.nonzero(m)
    top = ys.min()
    h = ys.max() - top
    lum = rgb.mean(axis=2)
    band = np.zeros_like(m)
    band[top + int(0.15 * h): top + int(0.6 * h)] = True
    inside = m & band
    thr = np.percentile(lum[inside], 3)
    ey, ex = np.nonzero(inside & (lum <= thr))
    eye_y = np.median(ey)
    return top, eye_y, np.median(ex)


def norm(path, n=200, side=False):
    m, rgb = mask_of(path)
    top, ey, ex = landmarks(m, rgb)
    u = ey - top
    rows = {}
    for t in np.linspace(-0.1, 2.6, 28):
        y = int(round(top + t * u))
        if y < 0 or y >= m.shape[0]:
            continue
        xs = np.nonzero(m[y])[0]
        if len(xs) == 0:
            rows[round(float(t), 2)] = None
            continue
        rows[round(float(t), 2)] = [round(float((xs.min() - ex) / u), 3), round(float((xs.max() - ex) / u), 3)]
    # aligned mask for IoU: resample into a fixed grid in u units centred on the eye x
    gy, gx = np.mgrid[-0.2:2.6:n * 1j, -1.6:1.6:n * 1j]
    py = np.clip((top + gy * u).round().astype(int), 0, m.shape[0] - 1)
    px = np.clip((ex + gx * u).round().astype(int), 0, m.shape[1] - 1)
    return rows, m[py, px], u


def main():
    r, ref = sys.argv[1], sys.argv[2]
    side = "--side" in sys.argv
    a, ma, ua = norm(r, side=side)
    b, mb, ub = norm(ref, side=side)
    iou = float((ma & mb).sum() / max(1, (ma | mb).sum()))
    print("t(u)   render [l, r]        reference [l, r]     d_left  d_right")
    out = {"iou": round(iou, 4), "rows": {}}
    for t in a:
        ra, rb = a[t], b.get(t)
        if ra and rb:
            dl, dr = round(ra[0] - rb[0], 3), round(ra[1] - rb[1], 3)
            print("%5.2f  %-20s %-20s %+.3f  %+.3f" % (t, ra, rb, dl, dr))
            out["rows"][t] = {"render": ra, "ref": rb, "d": [dl, dr]}
        else:
            print("%5.2f  %-20s %-20s" % (t, ra, rb))
    print("IoU %.4f" % iou)
    if "--json" in sys.argv:
        json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)


if __name__ == "__main__":
    main()
