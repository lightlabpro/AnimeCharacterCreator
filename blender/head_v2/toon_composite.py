"""Combine the albedo and normal renders from view_v2.py --toon into a toon preview:
flat albedo, one hard shadow (warm, saturated: MHS3 orange-brown, shading-style guide) where N.L < T, a thin
coloured outline from silhouette and normal breaks.   python3 toon_composite.py PREFIX view [view...]"""
import sys
import numpy as np
from PIL import Image, ImageFilter

L = np.array([-0.35, -0.85, 0.40])          # key light from the front, upper camera-left: the face is mostly lit (MHS3 frames)
T = 0.10
SHADOW = np.array([0.80, 0.62, 0.55])        # multiply
BG = np.array([143, 168, 194]) / 255.0


def comp(prefix, view):
    a = np.asarray(Image.open("%s_alb_%s.png" % (prefix, view)).convert("RGBA")).astype(float) / 255
    n = np.asarray(Image.open("%s_nrm_%s.png" % (prefix, view)).convert("RGBA")).astype(float) / 255
    alpha = a[..., 3:4]
    N = n[..., :3] * 2 - 1
    N /= np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-6)
    Ld = L / np.linalg.norm(L)
    nl = N @ Ld
    lit = (nl > T)[..., None]
    col = a[..., :3] * np.where(lit, 1.0, SHADOW)
    # outline: alpha edge + strong normal change
    gx = np.abs(np.diff(N, axis=1, prepend=N[:, :1])).sum(-1)
    gy = np.abs(np.diff(N, axis=0, prepend=N[:1])).sum(-1)
    edge = ((gx + gy) > 0.9) & (alpha[..., 0] > 0.5)
    sil = np.asarray(Image.fromarray((alpha[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.FIND_EDGES)) > 60
    line = edge | sil
    line = np.asarray(Image.fromarray((line * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0
    col = np.where(line[..., None], np.array([0.42, 0.27, 0.22]), col)
    out = col * alpha + BG * (1 - alpha)
    out = np.where(line[..., None] & (alpha < 0.5), np.array([0.42, 0.27, 0.22]), out)
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save("%s_toon_%s.png" % (prefix, view))


if __name__ == "__main__":
    for v in sys.argv[2:]:
        comp(sys.argv[1], v)
