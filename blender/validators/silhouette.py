"""Compare a candidate silhouette to a reference silhouette (needs numpy, which Blender ships).

Masks are 2D boolean arrays, row 0 = top. Both are cropped to the bounding box, scaled to the same
height, centred on the horizontal centre of mass, and compared. The width profile tells you *where*
the shapes differ (head, shoulders, hips...) which is the part a modeler can act on.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from .model import FAIL, PASS, WARN, Finding

# Height bands, as fractions of total height from the top, with the landmark they cover.
BANDS = (
    (0.00, 0.13, "head"), (0.13, 0.19, "neck and shoulders"), (0.19, 0.38, "chest and arms"),
    (0.38, 0.52, "waist and hips"), (0.52, 0.75, "thighs and knees"), (0.75, 1.00, "shins and feet"),
)


def mask_from_rgb(rgb: np.ndarray, threshold: float = 0.12) -> np.ndarray:
    """Foreground = pixels that differ from the corner background colour. rgb is HxWx3 (0..1)."""
    corners = np.array([rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]])
    bg = np.median(corners, axis=0)
    return np.linalg.norm(rgb[..., :3] - bg, axis=-1) > threshold


def mask_from_alpha(rgba: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    return rgba[..., 3] > threshold


def normalise(mask: np.ndarray, height: int = 256) -> np.ndarray:
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        raise ValueError("empty mask")
    crop = mask[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1]
    scale = height / crop.shape[0]
    width = max(1, int(round(crop.shape[1] * scale)))
    yi = np.minimum((np.arange(height) / scale).astype(int), crop.shape[0] - 1)
    xi = np.minimum((np.arange(width) / scale).astype(int), crop.shape[1] - 1)
    out = crop[np.ix_(yi, xi)]
    cx = int(round(np.nonzero(out)[1].mean()))
    canvas_w = height  # square canvas; enough for any humanoid pose
    canvas = np.zeros((height, canvas_w), dtype=bool)
    shift = canvas_w // 2 - cx
    x0 = max(0, shift)
    src0 = max(0, -shift)
    n = min(out.shape[1] - src0, canvas_w - x0)
    if n > 0:
        canvas[:, x0: x0 + n] = out[:, src0: src0 + n]
    return canvas


def iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter) / float(union) if union else 0.0


def width_profile(mask: np.ndarray) -> np.ndarray:
    """Row width as a fraction of total height (so it is scale-free)."""
    return mask.sum(axis=1) / mask.shape[0]


def compare(candidate: np.ndarray, reference: np.ndarray, label: str,
            iou_pass: float = 0.80, iou_warn: float = 0.65, band_tol: float = 0.06) -> List[Finding]:
    a, b = normalise(candidate), normalise(reference)
    score = iou(a, b)
    sev = PASS if score >= iou_pass else WARN if score >= iou_warn else FAIL
    out = [Finding(f"silhouette.{label}.iou", sev, "overlap with the reference silhouette (same height, centred)",
                   score, f">= {iou_pass:.2f}")]
    pa, pb = width_profile(a), width_profile(b)
    h = len(pa)
    for lo, hi, name in BANDS:
        sl = slice(int(lo * h), max(int(hi * h), int(lo * h) + 1))
        d = float(pa[sl].mean() - pb[sl].mean())
        if abs(d) > band_tol:
            word = "wider" if d > 0 else "narrower"
            out.append(Finding(f"silhouette.{label}.{name.replace(' ', '_')}", WARN,
                               f"{name} are {abs(d) / max(pb[sl].mean(), 1e-6) * 100:.0f}% {word} than the reference",
                               d, f"within +/-{band_tol}",
                               f"Adjust the {name} proportions; compare front and side."))
    return out
