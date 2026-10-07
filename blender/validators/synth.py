"""Synthetic limbs for calibrating and testing the deformation bands.

A tube along +Z with a joint in the middle, rotated by linear blend skinning. `good` builds the layout a rigger would make
(several loops across the joint and a smooth weight gradient); each named defect is one thing that goes wrong in real assets.
Scale free: the ratios the bands use do not depend on the tube's size.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from . import topology

DEFECTS = ("hard_split", "narrow_blend", "one_loop", "weight_spike", "stray_ring")


def _smooth(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def limb(rings: int = 11, seg: int = 12, radius: float = 1.0, spacing: float = 0.6, blend_rows: float = 5.0,
         spike: bool = False, taper: float = 0.0) -> Tuple[np.ndarray, List[Tuple[int, ...]], np.ndarray, np.ndarray]:
    """(verts, faces, moving weight, joint point). Joint at the middle ring; axis is X."""
    z = (np.arange(rings) - (rings - 1) / 2) * spacing * radius
    verts, w = [], []
    for r, zz in enumerate(z):
        rad = radius * (1 + taper * (zz / (z.max() or 1)))
        for k in range(seg):
            th = 2 * np.pi * k / seg
            verts.append([rad * np.cos(th), rad * np.sin(th), zz])
            width = max(blend_rows, 1e-6) * spacing * radius
            w.append(float(_smooth(np.array([(zz / width) + 0.5]))[0]) if blend_rows > 0 else float(zz > 1e-9))
    verts = np.array(verts)
    w = np.array(w)
    if spike:
        w[rings // 2 * seg + seg // 4] = 1.0  # one vertex pulled all the way to the far bone
        w[(rings // 2 - 1) * seg + seg // 4] = 0.0
    faces = [(r * seg + k, r * seg + (k + 1) % seg, (r + 1) * seg + (k + 1) % seg, (r + 1) * seg + k) for r in range(rings - 1) for k in range(seg)]
    return verts, faces, w, np.zeros(3)


def build(defect: Optional[str] = None, blend_rows: Optional[float] = None) -> dict:
    """`blend_rows` overrides the clean weight-blend width (5 rows = 4 loops; small joints such as fingers use fewer)."""
    kw: Dict[str, object] = {} if blend_rows is None else {"blend_rows": blend_rows}
    deg_scale = 1.0
    if defect == "hard_split":
        kw["blend_rows"] = 0.0
    elif defect == "narrow_blend":
        kw["blend_rows"] = 1.0
    elif defect == "one_loop":
        kw.update(rings=5, spacing=1.4, blend_rows=1.2)
    elif defect == "weight_spike":
        kw.update(spike=True)
    v, f, w, j = limb(**kw)
    if defect == "stray_ring":
        seg = 12
        w[(len(w) // seg // 2 - 1) * seg:(len(w) // seg // 2) * seg] = 1.0  # one ring weighted fully to the far bone, inside the blend
    return {"verts": v, "faces": f, "weight": w, "joint": j, "deg_scale": deg_scale, "axis": np.array([0.0, 0.0, 1.0])}


def bend(case: dict, degrees: float) -> np.ndarray:
    n = len(case["verts"])
    weights = {"moving": (np.arange(n), case["weight"])}
    return topology.lbs_rotate(case["verts"], weights, ["moving"], case["joint"], [1.0, 0.0, 0.0], degrees * case["deg_scale"])


# ---- shape-key patch (lid, lip, brow) --------------------------------------------------------------------

KEY_DEFECTS = ("fold", "pinch", "spike", "over_stretch")


def patch(rows: int = 8, cols: int = 10) -> Tuple[np.ndarray, List[Tuple[int, ...]]]:
    """A flat grid in XZ facing -Y, 1 wide and 0.5 tall, standing in for a lid or lip region."""
    v = np.array([[c / (cols - 1), 0.0, 0.5 * r / (rows - 1)] for r in range(rows) for c in range(cols)])
    f = [(r * cols + c, r * cols + c + 1, (r + 1) * cols + c + 1, (r + 1) * cols + c) for r in range(rows - 1) for c in range(cols - 1)]
    return v, f


def key(defect: Optional[str] = None, rows: int = 8, cols: int = 10, amount: float = 0.4):
    """(rest, posed, faces): a shape key that closes the top of the patch (the upper edge travels `amount` of the height)."""
    v, f = patch(rows, cols)
    p = v.copy()
    t = np.array([r / (rows - 1) for r in range(rows) for _ in range(cols)])
    arc = np.array([np.sin(np.pi * (c / (cols - 1))) for _ in range(rows) for c in range(cols)])
    p[:, 2] -= 0.5 * amount * (0.35 * t + 0.65 * _smooth(t)) * (0.55 + 0.45 * arc)
    p[:, 1] -= 0.04 * _smooth(t)
    if defect == "fold":
        p[:, 2] -= 0.5 * 1.4 * _smooth(t)  # top rows pushed through the bottom ones
    elif defect == "pinch":
        mid = (rows // 2) * cols
        p[mid + 2: mid + cols - 2, 0] = p[mid + cols // 2, 0]  # a row of vertices dragged into one point
    elif defect == "spike":
        p[(rows - 2) * cols + cols // 2, 1] -= 1.5
    elif defect == "over_stretch":
        p[:, 2] -= 0.5 * 2.6 * _smooth(t) * 0.0
        p[(rows - 1) * cols:, 0] = v[(rows - 1) * cols:, 0] * 4.0
    return v, p, f


def joint(case: dict):
    """A deform_regions.Joint for a synthetic limb. Bone-local axes follow Blender: X and Z are across the bone, Y runs along it
    (here along the tube, world Z)."""
    from .deform_regions import Joint
    n = len(case["verts"])
    return Joint({"moving": (np.arange(n), case["weight"])}, ["moving"], case["joint"], [[1, 0, 0], [0, 0, 1], [0, 1, 0]], None,
                 [0.0, 0.0, 2.0])
