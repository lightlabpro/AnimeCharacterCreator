#!/usr/bin/env python3
"""Prepare a reference image for an image-to-3D generator (or for your own modeling) the way TripoSR and TripoSG do,
and say whether the image is usable. Pillow and numpy only.

    prepare_reference.py ref.png --out ref_prepared.png [--ratio 0.85] [--bg gray|white] [--size 1024] [--json report.json]
    exit 0 usable, 12 not usable (cut off, too small, empty), 13 unknown (background could not be separated), 2 usage

Steps (from TripoSR `resize_foreground` and TripoSG `load_image`):
  1. longest side is capped at 2000 px
  2. the subject mask is the alpha channel when it is real (at least 1% of pixels near 0 and 1% near 255, TripoSG's test),
     otherwise it is estimated from a flat background (border pixels); a busy background is UNKNOWN: remove it first
     (rembg or RMBG-1.4), do not guess
  3. speckles are removed (morphological opening), the subject is cropped to its bounding box and padded to a square
  4. the subject is scaled so its long side is `ratio` of the canvas (TripoSR default 0.85; TripoSG pads 10% a side)
  5. composited on a flat grey (0.5, TripoSR) or white (TripoSG) background
Checks: subject touching the image border (cut off) fails, subject under 256 px on its long side fails, subject covering under 2% fails."""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageFilter

EXIT_PASS, EXIT_FAIL, EXIT_UNKNOWN, EXIT_USAGE = 0, 12, 13, 2
MAX_SIDE, MIN_SUBJECT, MIN_COVER = 2000, 256, 0.02

def valid_alpha(a, min_ratio=0.01):
    """TripoSG's rule: a real cut-out has both clearly transparent and clearly opaque pixels."""
    low = (a < 256 / 20).mean(); high = (a >= 256 - 256 / 20).mean()
    return bool(low >= min_ratio and high >= min_ratio)

def border_background(rgb, tol=28.0, max_spread=18.0):
    """Estimates a flat background from the border. Returns (mask or None, note)."""
    h, w, _ = rgb.shape; b = max(2, min(h, w) // 50)
    ring = np.concatenate([rgb[:b].reshape(-1, 3), rgb[-b:].reshape(-1, 3), rgb[:, :b].reshape(-1, 3), rgb[:, -b:].reshape(-1, 3)]).astype(float)
    bg = np.median(ring, 0); spread = np.percentile(np.linalg.norm(ring - bg, axis=1), 90)
    if spread > max_spread: return None, f"background is not flat (border colour spread {spread:.0f} > {max_spread:.0f})"
    dist = np.linalg.norm(rgb.astype(float) - bg, axis=2)
    return dist > tol, f"flat background {bg.round().astype(int).tolist()}"

def clean(mask):
    """Opening removes speckles; hole-filling is left to the generator."""
    im = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    return np.asarray(im) > 127

def prepare(img, ratio=0.85, bg="gray", size=1024):
    """-> (PIL image or None, report dict). report['status'] is usable / not_usable / unknown."""
    r = {"status": "usable", "problems": [], "notes": []}
    if not 0.3 <= ratio <= 1.0: raise ValueError("ratio must be between 0.3 and 1.0")
    s = MAX_SIDE / max(img.size)
    if s < 1: img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS); r["notes"].append(f"downscaled to {img.size}")
    rgba = np.asarray(img.convert("RGBA")); rgb, alpha = rgba[..., :3], rgba[..., 3]
    if img.mode in ("RGBA", "LA") and valid_alpha(alpha): mask = alpha > 127; r["notes"].append("used the alpha channel")
    else:
        mask, note = border_background(rgb); r["notes"].append(note)
        if mask is None: r["status"] = "unknown"; r["problems"].append(note + "; remove the background first (rembg, RMBG-1.4) and pass an RGBA image"); return None, r
    mask = clean(mask)
    if not mask.any(): r["status"] = "not_usable"; r["problems"].append("no subject found"); return None, r
    ys, xs = np.where(mask); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1; h, w = y1 - y0, x1 - x0
    r.update(subject_px=[int(w), int(h)], coverage=round(float(mask.mean()), 4))
    touches = [n for n, t in (("left", x0 == 0), ("right", x1 == mask.shape[1]), ("top", y0 == 0), ("bottom", y1 == mask.shape[0])) if t]
    if touches: r["problems"].append("subject touches the image edge (" + ", ".join(touches) + "): it is cut off, use an image with margin")
    if max(w, h) < MIN_SUBJECT: r["problems"].append(f"subject is only {max(w, h)} px on its long side (< {MIN_SUBJECT}): too small")
    if mask.mean() < MIN_COVER: r["problems"].append(f"subject covers {mask.mean():.1%} of the image (< {MIN_COVER:.0%})")
    if r["problems"]: r["status"] = "not_usable"
    fg = np.dstack([rgb[y0:y1, x0:x1], (mask[y0:y1, x0:x1] * 255).astype(np.uint8)]); side = max(h, w)
    sq = np.zeros((side, side, 4), np.uint8); sq[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = fg
    tgt = int(round(size * ratio)); sub = Image.fromarray(sq).resize((tgt, tgt), Image.LANCZOS)
    col = (128, 128, 128) if bg == "gray" else (255, 255, 255); canvas = Image.new("RGBA", (size, size), col + (255,))
    off = (size - tgt) // 2; canvas.alpha_composite(sub, (off, off))
    r.update(output=[size, size], foreground_ratio=ratio, background=bg)
    return canvas.convert("RGB"), r

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image"); ap.add_argument("--out"); ap.add_argument("--ratio", type=float, default=0.85); ap.add_argument("--bg", choices=["gray", "white"], default="gray")
    ap.add_argument("--size", type=int, default=1024); ap.add_argument("--json")
    try: a = ap.parse_args(argv)
    except SystemExit as e: return EXIT_USAGE if e.code else 0
    try: out, rep = prepare(Image.open(a.image), a.ratio, a.bg, a.size)
    except (OSError, ValueError) as e: print(f"error: {e}", file=sys.stderr); return EXIT_USAGE
    print(f"REFERENCE {os.path.basename(a.image)}: {rep['status'].upper()}")
    for p in rep["problems"]: print("  PROBLEM", p)
    for n in rep["notes"]: print("  note", n)
    if out is not None and a.out: out.save(a.out); print("  wrote", a.out)
    if a.json:
        with open(a.json, "w") as f: json.dump(rep, f, indent=1)
    return {"usable": EXIT_PASS, "not_usable": EXIT_FAIL, "unknown": EXIT_UNKNOWN}[rep["status"]]

if __name__ == "__main__":
    sys.exit(main())
