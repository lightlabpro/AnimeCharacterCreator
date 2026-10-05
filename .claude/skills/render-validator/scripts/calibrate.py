#!/usr/bin/env python3
"""Calibrates the validator's reference floors from images you have already judged.

Positives = renders that should PASS against the reference: perturbed copies of the reference itself
(--augment, free) plus any real renders you judge good (--good).
Negatives = renders that should FAIL: renders you judge bad, other characters (--bad).
For every metric it reports how far apart the two groups are and proposes a floor between them.
A metric whose groups overlap or nearly touch is reported as NOT USEFUL, so you do not trust it.

  python3 calibrate.py --ref ref_front.png --augment --bad now_front.png --bad old_front.png --write thresholds.json
  python3 validate.py init work/x --ref front=ref_front.png --config thresholds.json

Needs numpy + Pillow. This is how the shipped floors were set (see knowledge/validator-calibration.json).
"""
import argparse, importlib.util, io, json, os, sys
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("validate", os.path.join(HERE, "validate.py"))
V = importlib.util.module_from_spec(spec); spec.loader.exec_module(V)

HIGHER = ["sil_iou", "edge_f", "palette"]   # higher is better: positives must stay above a floor
LOWER = ["contour_px"]                       # lower is better: positives must stay under a ceiling

def perturbations(im):
    im = im.convert("RGB"); w, h = im.size; bg = im.getpixel((2, 2)); out = {}
    out["shift"] = im.transform(im.size, Image.AFFINE, (1, 0, -w * 0.025, 0, 1, h * 0.015), fillcolor=bg)
    s = 1.06; c = im.resize((int(w * s), int(h * s))); ox, oy = int(w * (s - 1) / 2), int(h * (s - 1) / 2)
    out["scale"] = c.crop((ox, oy, ox + w, oy + h))
    out["blur"] = im.filter(ImageFilter.GaussianBlur(1.6))
    out["bright"] = ImageEnhance.Brightness(im).enhance(1.12)
    out["rotate"] = im.rotate(2.5, fillcolor=bg)
    b = io.BytesIO(); im.save(b, "JPEG", quality=55); out["jpeg"] = Image.open(b).convert("RGB")
    return out

def measure(ref_im, cand_im):
    ra, ma, _ = V.normalise(ref_im); rb, mb, _ = V.normalise(cand_im)
    return {"sil_iou": V.sil_iou(mb, ma), "edge_f": V.edge_f(V.edges(rb, mb), V.edges(ra, ma)),
            "palette": V.palette_sim(rb, mb, ra, ma), "contour_px": V.contour_px(mb, ma)}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", required=True); ap.add_argument("--augment", action="store_true")
    ap.add_argument("--good", action="append", default=[]); ap.add_argument("--bad", action="append", default=[])
    ap.add_argument("--write")
    a = ap.parse_args()
    ref = Image.open(a.ref); pos, neg = [], []
    if a.augment: pos += [measure(ref, im) for im in perturbations(ref).values()]
    pos += [measure(ref, Image.open(p)) for p in a.good]
    neg += [measure(ref, Image.open(p)) for p in a.bad]
    if not pos or not neg: sys.exit("need positives (--augment and/or --good) and negatives (--bad)")
    print(f"{len(pos)} positives, {len(neg)} negatives")
    floors, ceilings, useful = {}, {}, {}
    for k in HIGHER + LOWER:
        P = np.array([m[k] for m in pos]); N = np.array([m[k] for m in neg])
        if k in HIGHER: worst_pos, best_neg = P.min(), N.max(); gap = worst_pos - best_neg; mid = (worst_pos + best_neg) / 2
        else: worst_pos, best_neg = P.max(), N.min(); gap = best_neg - worst_pos; mid = (worst_pos + best_neg) / 2
        scale = max(abs(worst_pos), abs(best_neg), 1e-6); rel = gap / scale
        verdict = "NOT USEFUL (groups overlap)" if gap <= 0 else ("thin margin, do not rely on it alone" if rel < 0.15 else "good separator")
        useful[k] = gap > 0
        print(f"  {k:<11} worst positive {worst_pos:7.3f}   best negative {best_neg:7.3f}   gap {gap:+7.3f} ({rel:+.0%})   -> {verdict}")
        if gap > 0:
            (floors if k in HIGHER else ceilings)[k] = round(float(mid), 3)
    cfg = {"floors": floors, "ceilings": ceilings}
    print("proposed:", json.dumps(cfg))
    if a.write:
        with open(a.write, "w") as f: json.dump(cfg, f, indent=2)
        print("wrote", a.write)

if __name__ == "__main__":
    main()
