"""Best-alignment silhouette IoU between a model render and its reference view (parts workflow, stage-2 geometry).

    python3 sil_iou.py RENDER.png REFERENCE.png [--mirror] [--png overlay.png]

Masks: render alpha (or flat background), reference flat background. Both are cropped to their bounding box and
put on a grid of height 256; the render is then scaled (0.80..1.20) and shifted to maximise IoU with the reference
(a similarity fit, no shape change). Prints the best IoU, scale and shift. Why not TypeSafe here: on render-vs-drawing
pairs the side/back TypeSafe questions did not separate the right sheet from a wrong one (q41 discrimination test).
"""
import sys

import numpy as np
from PIL import Image

N = 256


def mask(path):
    a = np.asarray(Image.open(path).convert("RGBA")).astype(float)
    if a[..., 3].min() < 250:
        m = a[..., 3] > 128
    else:
        rgb = a[..., :3]
        border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        m = np.abs(rgb - np.median(border, axis=0)).max(axis=2) > 30
    ys, xs = np.nonzero(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def grid(m, h):
    w = max(1, int(round(m.shape[1] * h / m.shape[0])))
    im = Image.fromarray((m * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    return np.asarray(im) > 127


def place(m, H=int(N * 1.6), W=int(N * 1.6), dy=0, dx=0):
    c = np.zeros((H, W), bool)
    y0 = (H - m.shape[0]) // 2 + dy
    x0 = (W - m.shape[1]) // 2 + dx
    ys, xs = max(0, y0), max(0, x0)
    ye, xe = min(H, y0 + m.shape[0]), min(W, x0 + m.shape[1])
    if ye > ys and xe > xs:
        c[ys:ye, xs:xe] = m[ys - y0:ye - y0, xs - x0:xe - x0]
    return c


def best(r, f):
    F = place(grid(f, N))
    top = (0.0, None)
    for s in np.linspace(0.80, 1.20, 17):
        R = grid(r, int(N * s))
        for dy in range(-24, 25, 4):
            for dx in range(-24, 25, 4):
                P = place(R, dy=dy, dx=dx)
                iou = (P & F).sum() / max(1, (P | F).sum())
                if iou > top[0]:
                    top = (iou, (s, dy, dx), P, F)
    return top


def main():
    r, f = mask(sys.argv[1]), mask(sys.argv[2])
    if "--mirror" in sys.argv:
        r = r[:, ::-1]
    iou, (s, dy, dx), P, F = best(r, f)
    print("IoU %.4f scale %.2f dy %d dx %d" % (iou, s, dy, dx))
    if "--png" in sys.argv:
        o = np.zeros(P.shape + (3,), np.uint8)
        o[P & F] = (200, 200, 200); o[P & ~F] = (230, 60, 60); o[~P & F] = (60, 120, 230)
        Image.fromarray(o).save(sys.argv[sys.argv.index("--png") + 1])


if __name__ == "__main__":
    main()
