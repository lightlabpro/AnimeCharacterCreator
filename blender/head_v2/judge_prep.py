"""Frame a v2 front render like the Leo reference (D = pupil line to chin = 300 px, pupil line y 330, face centre x
400, 800 px) and measure the face outline in D (left half doubled, like the reference measurement).
    python3 judge_prep.py RENDER_front.png HEAD.npz OUT.png [--ortho 0.30 --cz 1.555]"""
import sys
import numpy as np
from PIL import Image

ZT, H = 1.685, 0.22
EYE_H = 0.445


def arg(n, d):
    return float(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def skin_mask(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return (r > 150) & (r - b > 35) & (g > 95) & (r > g) & (abs(r - g) < 90)


def main():
    render, npz, out = sys.argv[1:4]
    ortho, cz = arg("--ortho", 0.30), arg("--cz", 1.555)
    im = Image.open(render).convert("RGB"); W = im.width
    v = np.load(npz)["v"]
    chin_z = v[v[:, 1] < -0.2 * H][:, 2].min()
    pupil_z = ZT - EYE_H * H
    row = lambda z: W / 2 - (z - cz) / ortho * W
    pupil, chin, cx = row(pupil_z), row(chin_z), W / 2
    D = chin - pupil
    a = np.asarray(im); m = skin_mask(a)
    res = {}
    for f in (0.2, 0.35, 0.5, 0.64, 0.75, 0.85, 0.92, 0.97):
        y = int(pupil + f * D); r_ = np.nonzero(m[y, 10:int(cx)])[0]
        res[f] = round(2 * (cx - (r_.min() + 10)) / D, 3) if len(r_) else None
    print("D px %.1f  widths/D %s" % (D, res))
    s = 300.0 / D
    big = im.resize((int(W * s), int(W * s)), Image.LANCZOS)
    canvas = Image.new("RGB", (800, 800), tuple(a[2, 2]))
    x0, y0 = int(cx * s - 400), int(pupil * s - 330)
    canvas.paste(big, (-x0, -y0))
    canvas.save(out)


if __name__ == "__main__":
    main()
