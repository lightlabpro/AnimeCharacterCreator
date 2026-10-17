"""Front-projected paint test (v2 form check only): eyes, brows, nose shade and mouth line drawn in Leo's proportions
(D = pupil line to chin: eye width 0.33 D, pupil distance 0.72 D, nose bottom 0.49 D, mouth 0.64 D, 0.49 D wide)
on a texture that the viewer projects from the front onto the curved face. Shows how drawn features foreshorten on
this surface in 3/4 and side. Image covers x in [-0.4, 0.4] H, h in [0.30, 1.00] H."""
import sys
from PIL import Image, ImageDraw
import numpy as np

S = 2048
def px(x, h):        # H units -> pixels
    return ((x + 0.4) / 0.8 * S, (h - 0.30) / 0.70 * S)

EYE_H, D = 0.50, 0.50
im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
dr = ImageDraw.Draw(im)
def poly(pts, fill):
    dr.polygon([px(*p) for p in pts], fill=fill)
for s in (1, -1):
    cx = s * 0.36 * D; w = 0.33 * D; hh = 0.42 * w
    t = np.linspace(0, 1, 40)
    xin, xout = cx - s * w / 2, cx + s * w / 2
    # almond: upper lid arc higher toward the outer third, lower lid flatter
    up = [(xin + (xout - xin) * u, EYE_H - hh * (np.sin(np.pi * u) ** 0.8) * (0.85 + 0.3 * u)) for u in t]
    lo = [(xin + (xout - xin) * u, EYE_H + 0.35 * hh * np.sin(np.pi * u) ** 1.2) for u in t[::-1]]
    poly(up + lo, (245, 245, 250, 255))
    # iris (cut by the upper lid): draw then re-mask by the almond
    ir = 0.50 * w * 0.5 * 1.25
    iris = Image.new("RGBA", (S, S), (0, 0, 0, 0)); di = ImageDraw.Draw(iris)
    c = px(cx - s * 0.02 * D, EYE_H - 0.12 * hh)
    rp = ir / 0.8 * S
    di.ellipse([c[0] - rp, c[1] - rp * 1.08, c[0] + rp, c[1] + rp * 1.08], fill=(70, 150, 80, 255))
    di.ellipse([c[0] - rp * 0.45, c[1] - rp * 0.5, c[0] + rp * 0.45, c[1] + rp * 0.5], fill=(20, 40, 25, 255))
    di.ellipse([c[0] - rp * 0.55 + rp * 0.35 * s, c[1] - rp * 0.7, c[0] - rp * 0.25 + rp * 0.35 * s, c[1] - rp * 0.4], fill=(255, 255, 255, 255))
    mask = Image.new("L", (S, S), 0); ImageDraw.Draw(mask).polygon([px(*p) for p in up + lo], fill=255)
    im.paste(iris, (0, 0), Image.composite(iris, Image.new("RGBA", (S, S)), mask).split()[3])
    # upper lash: thick dark band along the upper lid, thicker and winged at the outer end
    band = [(x, h - 0.010 - 0.012 * ((x - xin) / (xout - xin))) for x, h in up]
    wing = [(xout + s * 0.025, EYE_H - hh * 0.55)]
    poly(up + wing + band[::-1], (60, 35, 25, 255))
    # crease line
    cr = [(xin + (xout - xin) * u, EYE_H - hh * 1.45 * np.sin(np.pi * (0.1 + 0.85 * u)) ** 0.7 - 0.006) for u in t]
    dr.line([px(*p) for p in cr], fill=(150, 95, 75, 255), width=6)
    # brow: thick angled stroke (hair colour)
    b0, b1 = s * 0.05 * D * 1.4, s * 0.62 * D
    br = [(b0, EYE_H - 0.21 * D), (b0 + (b1 - b0) * 0.6, EYE_H - 0.255 * D), (b1, EYE_H - 0.22 * D),
          (b1, EYE_H - 0.205 * D), (b0 + (b1 - b0) * 0.6, EYE_H - 0.225 * D), (b0, EYE_H - 0.17 * D)]
    poly(br, (110, 75, 45, 255))
# nose shade (small triangle under the tip) and mouth line
nb = EYE_H + 0.49 * D
poly([(-0.035, nb - 0.006), (0.02, nb - 0.012), (0.03, nb), (-0.03, nb + 0.004)], (190, 120, 95, 255))
my = EYE_H + 0.64 * D; mw = 0.49 * D / 2
dr.line([px(-mw, my), px(0, my + 0.004), px(mw, my)], fill=(110, 60, 50, 255), width=10)
dr.line([px(-mw * 0.55, my + 0.05), px(mw * 0.55, my + 0.05)], fill=(205, 140, 115, 255), width=14)  # lower lip shade
im.save(sys.argv[1])
