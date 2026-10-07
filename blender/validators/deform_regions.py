"""Deformation checks per body part or element, each judged against its own range.

Why this exists. `topology.deformation_findings` judged the whole mesh with one set of thresholds. That is wrong twice:
  1. A bend only changes the faces in the weight-blend zone around the joint. Measured over the whole body, a collapsed
     elbow is a fraction of a percent of the edges and passes. Here only the zone is measured.
  2. Parts deform differently. A lid or lip stretches far more than a thigh and must never fold; hair clumps and rigid
     accessories must not deform at all; a knee is allowed to squash on the inside of the bend. Each region class has
     its own bands, and each joint is tested up to its own range of motion, not a fixed 90 degrees.

Everything is numpy only. The bend uses `topology.lbs_rotate` (linear blend skinning, as Blender's armature modifier).
Band values are calibrated on synthetic good and defective meshes (`synth.py`, tests/validators/test_deform_regions.py) and are
marked as heuristics: tighten them against production models as the library fills.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import topology
from .model import FAIL, INFO, PASS, SKIP, WARN, Finding

# ---- motion plan ------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Motion:
    """One bend test. `role` is the bone role (measure.find_bone_name), `axis` the bone-local axis rotated about, `max_deg` the
    joint's normal range of motion in the flexing direction, and `rev_deg` the range the other way (hyperextension).
    `toward` is a world-space unit direction (Blender axes, character faces -Y, Z up) that the distal end moves toward in the
    flexing direction: it fixes which sign of the axis is the flexing one, since bone-local axes differ between rigs."""
    region: str
    role: str
    axis: int
    max_deg: float
    rev_deg: float
    toward: Tuple[float, float, float]
    label: str
    cls: Optional[str] = None   # band class when the region's usual class does not describe a bent bone (the jaw, wing arms)


FRONT, BACK, UP, DOWN, OUT = (0, -1, 0), (0, 1, 0), (0, 0, 1), (0, 0, -1), (1, 0, 0)

# Normal active range of motion, degrees (AAOS joint-motion norms; Kapandji for the digits). Pose tests never go past these:
# a mesh is not at fault for folding at a pose the body cannot take.
MOTIONS: List[Motion] = [
    Motion("arms", "elbow", 0, 145, 5, FRONT, "elbow flexion"),
    Motion("legs", "knee", 0, 140, 5, BACK, "knee flexion"),
    Motion("shoulders", "shoulder", 0, 150, 40, FRONT, "arm raise forward"),
    Motion("shoulders", "shoulder", 2, 150, 20, OUT, "arm raise sideways"),
    Motion("hips", "hip", 0, 120, 20, FRONT, "hip flexion"),
    Motion("hips", "hip", 2, 45, 30, OUT, "leg out sideways"),
    Motion("neck", "neck", 0, 45, 55, FRONT, "neck nod"),
    Motion("neck", "neck", 2, 35, 35, OUT, "neck tilt"),
    Motion("waist", "spine", 0, 40, 20, FRONT, "bend forward"),
    Motion("chest", "chest", 2, 30, 30, OUT, "chest side bend"),
    Motion("hands", "wrist", 0, 70, 80, DOWN, "wrist flexion"),
    Motion("hands", "index_01", 0, 90, 0, DOWN, "finger base curl"),
    Motion("hands", "index_02", 0, 100, 0, DOWN, "finger middle curl"),
    Motion("feet", "ankle", 0, 50, 20, DOWN, "ankle point"),
    Motion("feet", "toe", 0, 60, 30, UP, "toe lift"),
    Motion("mouth", "jaw", 0, 30, 0, DOWN, "jaw open", "fine_hinge"),
    Motion("tail", "tail_01", 2, 45, 45, OUT, "tail swing"),
    Motion("wings", "wing_01", 0, 80, 20, UP, "wing flap", "limb_joint"),
]


def motions_for(region: str) -> List[Motion]:
    return [m for m in MOTIONS if m.region == region]


# ---- bands -----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Band:
    """warn / fail limits on a metric. `hi` metrics get worse upward, `lo` metrics get worse downward."""
    warn: float
    fail: float
    why: str = ""

    def grade(self, x: float, direction: str) -> str:
        if direction == "hi":
            return FAIL if x > self.fail else WARN if x > self.warn else PASS
        return FAIL if x < self.fail else WARN if x < self.warn else PASS


# Region class -> metric -> Band. Metrics (all measured only on the deformation zone):
#   stretch  : 99th percentile of posed/rest edge length            (hi)
#   squash   : 1st percentile of posed/rest edge length             (lo)
#   shear    : 95th percentile change of a quad corner angle, deg   (hi)
#   collapse : share of faces whose area shrinks below 0.2x         (hi)
#   flip     : share of faces whose normal flips                    (hi)
#   section  : cross-section footprint at the joint, posed/rest      (lo): the "candy wrapper" measure
#   worst_stretch: the single worst edge, which catches one stray weight (hi)
#   blend    : width of the weight-blend zone, in quad rows, that the joint needs to bend (lo): a hard weight split cannot bend
CLASSES: Dict[str, Dict[str, Band]] = {
    # elbow, knee, shoulder, hip, tested to ~145 deg: the inside of a bend squashes (a clean 3-radius blend still reaches ~0.4)
    "limb_joint": {"stretch": Band(2.0, 3.0, "outer side of a 145 deg bend, clean blend ~1.5"), "squash": Band(0.30, 0.15, "inner side, clean ~0.4"),
                   "shear": Band(50, 65, "clean ~43, hard split ~72"), "collapse": Band(0.02, 0.08), "flip": Band(0.0, 0.01),
                   "section": Band(0.5, 0.35, "candy wrapper; a plain linear-blend tube reaches ~0.63"), "blend": Band(2, 1),
                   "worst_stretch": Band(2.6, 3.4, "one bad vertex or edge"), "weight_jump": Band(0.3, 0.45, "clean ~0.04, a stray vertex ~0.55")},
    # wrist, ankle, fingers, toes, jaw: short segments with 2-3 loops per joint, tested to ~100 deg
    "fine_hinge": {"stretch": Band(1.9, 2.6), "squash": Band(0.35, 0.2), "shear": Band(70, 85, "a finger with two loops across a 100 deg curl shears ~63; shear does not separate good from bad here"), "collapse": Band(0.02, 0.08),
                   "flip": Band(0.0, 0.01), "section": Band(0.6, 0.45), "blend": Band(2, 1), "worst_stretch": Band(2.3, 3.0), "weight_jump": Band(0.3, 0.45)},
    # neck and spine: small angles over a long span, so they must be very smooth
    "column": {"stretch": Band(1.45, 1.9), "squash": Band(0.55, 0.4), "shear": Band(24, 40), "collapse": Band(0.01, 0.05),
               "flip": Band(0.0, 0.005), "section": Band(0.8, 0.65), "blend": Band(2, 1), "worst_stretch": Band(1.7, 2.1), "weight_jump": Band(0.3, 0.45)},
    # shape keys on lids, lips, brows, cheeks, nose: local edges stretch far, but a face must never fold or spike
    "face_soft": {"stretch": Band(2.5, 4.0, "a lid closing or a smile pulls edges; clean ~1"), "squash": Band(0.3, 0.15),
                  "shear": Band(40, 60), "collapse": Band(0.03, 0.10), "flip": Band(0.0, 0.01, "a folded lid or lip shows at once"),
                  "worst_stretch": Band(3.0, 5.0, "one vertex pulled away from the rest")},
    # hair clumps, horns, rigid accessories, armor plates: only rigid motion
    "rigid": {"stretch": Band(1.05, 1.2), "squash": Band(0.95, 0.85), "shear": Band(5, 15), "collapse": Band(0.0, 0.01),
              "flip": Band(0.0, 0.0), "worst_stretch": Band(1.1, 1.3)},
    # cloth and wing membranes follow the body but may stretch more and wrinkle
    "soft_cover": {"stretch": Band(2.0, 3.0), "squash": Band(0.4, 0.25), "shear": Band(40, 60), "collapse": Band(0.03, 0.10),
                   "flip": Band(0.0, 0.01), "worst_stretch": Band(3.0, 4.5)},
    # tail and other long tapering tubes: many small bends
    "tube": {"stretch": Band(1.5, 2.0), "squash": Band(0.5, 0.35), "shear": Band(28, 45), "collapse": Band(0.01, 0.05),
             "flip": Band(0.0, 0.005), "section": Band(0.75, 0.6), "blend": Band(2, 1), "worst_stretch": Band(1.8, 2.3), "weight_jump": Band(0.3, 0.45)},
}

REGION_CLASS: Dict[str, str] = {
    "arms": "limb_joint", "legs": "limb_joint", "shoulders": "limb_joint", "hips": "limb_joint",
    "hands": "fine_hinge", "feet": "fine_hinge", "mouth": "face_soft",
    "neck": "column", "waist": "column", "chest": "column", "body": "limb_joint",
    "eyes": "face_soft", "brows": "face_soft", "nose": "face_soft", "cheeks": "face_soft", "jaw": "face_soft", "skull": "face_soft",
    "ears": "face_soft", "face": "face_soft",
    "hair": "rigid", "facial_hair": "rigid", "horns": "rigid", "accessory": "rigid", "mane": "rigid",
    "clothing": "soft_cover", "wings": "soft_cover", "frill": "soft_cover", "surface": "soft_cover",
    "tail": "tube", "quadruped": "limb_joint", "muzzle": "face_soft", "archetype": "soft_cover",
}

# Edge loops that share the bend (partly weighted rings). Shoulder, elbow, knee: docs/anatomy-manual.md section 13. The rest are
# heuristics from the same logic (a joint needs two loops to bend and few enough to stay clean): tighten on production models.
LOOPS: Dict[str, Tuple[int, int]] = {"elbow flexion": (2, 4), "knee flexion": (4, 6), "arm raise forward": (3, 5), "arm raise sideways": (3, 5),
                                     "hip flexion": (3, 5), "leg out sideways": (3, 5), "neck nod": (3, 6), "neck tilt": (3, 6),
                                     "bend forward": (3, 6), "chest side bend": (3, 6), "wrist flexion": (2, 4), "ankle point": (2, 4),
                                     "toe lift": (2, 3), "finger base curl": (2, 3), "finger middle curl": (2, 3), "jaw open": (2, 4),
                                     "tail swing": (3, 8), "wing flap": (3, 6)}


def loop_finding(m: "Motion", met: Dict[str, float], label: str) -> Optional[Finding]:
    lo_hi = LOOPS.get(m.label)
    if not lo_hi or "loops" not in met:
        return None
    lo, hi = lo_hi
    n = int(met["loops"])
    sev = PASS if lo <= n <= hi else WARN if n >= lo - 1 and n <= hi + 2 else FAIL
    return Finding(f"deform.{m.region}.{label}.loops", sev, f"{m.region}: edge loops sharing the {m.label} ({'manual s13' if m.label in ('elbow flexion', 'knee flexion', 'arm raise forward') else 'heuristic'})",
                   float(n), f"{lo}..{hi}", "Add a loop pair across the joint." if n < lo else "Remove loops: too dense for a clean bend.")


METRIC_DIR = {"stretch": "hi", "squash": "lo", "shear": "hi", "collapse": "hi", "flip": "hi", "section": "lo", "blend": "lo",
              "worst_stretch": "hi", "weight_jump": "hi"}
METRIC_TEXT = {
    "stretch": "edge stretch (99th percentile of posed / rest length)",
    "squash": "edge squash (1st percentile of posed / rest length)",
    "shear": "quad corner angle change (95th percentile, degrees)",
    "collapse": "share of faces whose area shrinks below 0.2x",
    "flip": "share of faces whose normal flips",
    "section": "cross-section footprint at the joint (posed / rest)",
    "blend": "weight-blend width in quad rows",
    "worst_stretch": "single worst edge stretch (posed / rest length)",
    "weight_jump": "largest weight gap between a vertex and its neighbours",
    "loops": "edge loops sharing the bend",
}
METRIC_FIX = {
    "stretch": "Add edge loops across the bend or widen the weight blend so the stretch spreads over more faces.",
    "squash": "Add loops on the inside of the bend or add a corrective shape key; a single loop collapses.",
    "shear": "Relax the quads at the joint and keep loops perpendicular to the bend axis.",
    "collapse": "Faces collapse at the joint: more loops across the joint and smoother weights.",
    "flip": "The surface folds through itself: widen the weight blend and add loops; check for overlapping weights.",
    "section": "The limb pinches like a candy wrapper: add a loop pair at the joint, move weights to share the joint over two bones, or add a corrective key.",
    "blend": "The weights switch bones over fewer than two quad rows: paint a gradient across at least three loops.",
    "worst_stretch": "One edge or vertex is pulled far from its neighbours: look for a stray weight or a vertex moved by a key.",
    "weight_jump": "A vertex or ring has a weight far from its neighbours: smooth the weights across the joint (Blender: Weights > Smooth).",
    "loops": "Too few or too many edge loops share this bend: add a loop pair across the joint or remove extra loops.",
}


# Bands are calibrated at the class's reference bend; a smaller pose gets proportionally tighter limits, a larger one looser.
REF_DEG = {"limb_joint": 145.0, "fine_hinge": 100.0, "column": 45.0, "tube": 45.0}


# Smallest headroom a band may shrink to at small bends: a few degrees of noise must never fail a clean mesh.
FLOOR = {"stretch": 0.2, "worst_stretch": 0.35, "squash": 0.2, "section": 0.12, "shear": 9.0}
_CURVE: Dict[Tuple[str, int, float], float] = {}
CLEAN_ROWS = {"fine_hinge": 3.5}   # small joints are rigged with two loops, so their clean curve uses a narrower blend


def _clean_dev(metric: str, degrees: float, rows: Optional[float] = None) -> float:
    """How far a clean synthetic limb (synth.limb, three radii of blend) is from ideal for `metric` at `degrees`. Deformation
    is not linear in the angle (a bend past ~90 degrees folds the inner edge through itself), so band limits follow this curve."""
    from . import synth
    deg = int(round(min(max(abs(degrees), 5.0), 175.0) / 5.0) * 5)
    key = (metric, deg, rows or 0.0)
    if key not in _CURVE:
        c = synth.build(None, rows)
        posed = synth.bend(c, float(deg))
        zone = deformation_zone(c["faces"], c["weight"])
        m = measure(c["verts"], posed, c["faces"], zone, c["weight"], c["joint"], 2.0, c["axis"])
        ideal = 0.0 if metric == "shear" else 1.0
        _CURVE[key] = abs(m.get(metric, ideal) - ideal)
    return _CURVE[key]


def scaled(band: Band, metric: str, cls: str, degrees: Optional[float]) -> Band:
    """Bands are calibrated at the class's reference bend. At another bend each limit keeps the same headroom over the clean
    curve: its distance from ideal is scaled by (clean deviation at this angle / clean deviation at the reference angle)."""
    ref = REF_DEG.get(cls)
    if not ref or not degrees or metric in ("flip", "collapse", "blend", "weight_jump"):
        return band
    rows = CLEAN_ROWS.get(cls)
    base = max(_clean_dev(metric, ref, rows), 0.02)
    k = max(_clean_dev(metric, degrees, rows), 0.02) / base
    ideal = 0.0 if metric == "shear" else 1.0
    sign = 1.0 if band.warn >= ideal else -1.0
    floor = FLOOR[metric]
    warn = max(abs(band.warn - ideal) * k, floor)
    fail = max(abs(band.fail - ideal) * k, floor * 1.8)
    return Band(ideal + sign * warn, ideal + sign * fail, band.why)


def band_for(region: str, metric: str) -> Optional[Band]:
    return CLASSES.get(REGION_CLASS.get(region, "limb_joint"), {}).get(metric)


# ---- measurement -----------------------------------------------------------------------------------------


def _quad_corner_angles(v: np.ndarray, faces: Sequence[Sequence[int]]) -> np.ndarray:
    """(n_quads, 4) interior angles, degrees. Non-quads are skipped."""
    out = []
    for f in faces:
        if len(f) != 4:
            continue
        p = v[list(f)]
        e = [p[(k + 1) % 4] - p[k] for k in range(4)]
        ln = [np.linalg.norm(x) or 1e-12 for x in e]
        out.append([np.degrees(np.arccos(np.clip(np.dot(-e[k], e[(k + 1) % 4]) / (ln[k] * ln[(k + 1) % 4]), -1, 1))) for k in range(4)])
    return np.array(out).reshape(-1, 4)


def deformation_zone(faces: Sequence[Sequence[int]], weight: np.ndarray, region_mask: Optional[np.ndarray] = None,
                     rest: Optional[np.ndarray] = None, posed: Optional[np.ndarray] = None, eps: float = 1e-6) -> np.ndarray:
    """Indices of the faces that actually deform: those with a vertex whose moving-bone weight is strictly between 0 and 1
    (the blend zone), plus faces that join a fully moving vertex to a fully fixed one (a hard weight split). Faces wholly
    on the rigid side only rotate and say nothing about the topology. For a shape key (no weights) pass `rest` and `posed`:
    the zone is every face with a moved vertex."""
    if rest is not None and posed is not None:
        moved = np.linalg.norm(posed - rest, axis=1) > eps * max(float(np.ptp(rest[:, 2])), 1e-9)
        sel = [i for i, f in enumerate(faces) if moved[list(f)].any()]
    else:
        blend = (weight > 1e-4) & (weight < 1 - 1e-4)
        hi, lo = weight >= 1 - 1e-4, weight <= 1e-4
        sel = []
        for i, f in enumerate(faces):
            idx = list(f)
            if blend[idx].any() or (hi[idx].any() and lo[idx].any()):
                sel.append(i)
    sel = np.array(sel, dtype=int)
    if region_mask is not None and len(sel):
        sel = np.array([i for i in sel if region_mask[list(faces[i])].any()], dtype=int)
    return sel


def local_flips(rest: np.ndarray, posed: np.ndarray, zf: Sequence[Sequence[int]]) -> float:
    """Share of faces folded over relative to their neighbours: a face whose normal agreed with its neighbours at rest and now
    points against them. Unlike comparing normals with the rest pose, this does not call a face flipped just because the whole
    limb rotated past 90 degrees."""
    nr, npz = topology._normals(rest, zf), topology._normals(posed, zf)
    owner: Dict[Tuple[int, int], List[int]] = {}
    for i, f in enumerate(zf):
        for k in range(len(f)):
            a, b = f[k], f[(k + 1) % len(f)]
            owner.setdefault((a, b) if a < b else (b, a), []).append(i)
    nbrs: List[List[int]] = [[] for _ in zf]
    for fs in owner.values():
        if len(fs) == 2:
            nbrs[fs[0]].append(fs[1])
            nbrs[fs[1]].append(fs[0])
    flips, counted = 0, 0
    for i, nb in enumerate(nbrs):
        if not nb:
            continue
        counted += 1
        if float(nr[i] @ nr[nb].mean(axis=0)) > 0 and float(npz[i] @ npz[nb].mean(axis=0)) < 0:
            flips += 1
    return flips / max(counted, 1)


def kabsch_flips(rest: np.ndarray, posed: np.ndarray, zf: Sequence[Sequence[int]]) -> float:
    """Share of zone faces whose normal ends up more than 140 degrees from where the zone's best-fit rigid rotation would put it.
    A bend turns the two sides of a joint by at most the joint's range of motion, so a healthy face is off the average by well under 140 even at 150 degrees
    of bend (linear blend skinning distorts the fit); a reversed face is off by about 180."""
    used = sorted({i for f in zf for i in f})
    a, b = rest[used], posed[used]
    a0, b0 = a - a.mean(axis=0), b - b.mean(axis=0)
    u, _, vt = np.linalg.svd(a0.T @ b0)
    d = np.sign(np.linalg.det(vt.T @ u.T)) or 1.0
    rot = vt.T @ np.diag([1, 1, d]) @ u.T
    nr, npz = topology._normals(rest, zf) @ rot.T, topology._normals(posed, zf)
    return float(((nr * npz).sum(axis=1) < -0.77).mean())


def section_ratio(rest: np.ndarray, posed: np.ndarray, centre: Sequence[float], radius: float) -> float:
    """Cross-section footprint of the slab of vertices within `radius` of the joint, posed over rest. The slab is thin along the
    limb, so the two largest principal spreads are its cross-section; their product is rotation independent. A candy-wrapper
    collapse drives it toward 0; a clean bend keeps it near 1."""
    c = np.asarray(centre, float)
    sel = np.linalg.norm(rest - c, axis=1) <= radius
    if sel.sum() < 8:
        return 1.0

    def foot(p: np.ndarray) -> float:
        q = p[sel] - p[sel].mean(axis=0)
        ev = np.sort(np.linalg.eigvalsh(q.T @ q / max(len(q) - 1, 1)))[::-1]
        return float(np.sqrt(max(ev[0], 0) * max(ev[1], 0)))

    r = foot(rest)
    return foot(posed) / r if r > 1e-12 else 1.0


def weight_jump(weight: np.ndarray, edges: np.ndarray, zone_verts: np.ndarray) -> float:
    """Largest gap between a vertex's moving weight and the mean of its neighbours', over the zone. A smooth gradient keeps this small
    at any bend angle; a stray weight (one vertex or ring on the wrong bone) makes it large even where a small bend would hide it."""
    n = len(weight)
    total, count = np.zeros(n), np.zeros(n)
    for a, b in edges:
        total[a] += weight[b]
        count[a] += 1
        total[b] += weight[a]
        count[b] += 1
    nb = np.where(count > 0, total / np.where(count > 0, count, 1), weight)
    d = np.abs(weight - nb)[zone_verts]
    return float(d.max()) if len(d) else 0.0


def blend_loops(weight: np.ndarray, rest: np.ndarray, axis: Sequence[float], edges: np.ndarray) -> int:
    """Edge loops inside the weight-blend zone: distinct rings of partly weighted vertices along the limb axis. It counts the loops
    that actually share the bend, wherever the joint sits, instead of guessing a radius from the body height. One ring is not
    counted: the outermost partly weighted ring only eases the weight in, it does not carry the bend (heuristic)."""
    a = np.asarray(axis, float)
    a = a / (np.linalg.norm(a) or 1)
    blend = (weight > 1e-4) & (weight < 1 - 1e-4)
    if not blend.any():
        return 0
    t = np.sort(rest[blend] @ a)
    d = np.abs((rest[edges[:, 0]] - rest[edges[:, 1]]) @ a)
    d = d[d > 1e-9]
    tol = 0.35 * (float(np.median(d)) if len(d) else 1.0)
    rings = 1 + int(np.sum(np.diff(t) > tol))
    return max(rings - 1, 0)


def blend_rows(weight: np.ndarray, rest: np.ndarray, edges: np.ndarray, axis: Sequence[float]) -> float:
    """How many quad rows the weight takes to go from 0 to 1 along the limb axis: the span of vertices with partial weight over
    the median edge length measured along the axis. Zero means a hard split, which cannot bend smoothly."""
    a = np.asarray(axis, float)
    a = a / (np.linalg.norm(a) or 1)
    blend = (weight > 1e-4) & (weight < 1 - 1e-4)
    if not blend.any():
        return 0.0
    t = rest @ a
    span = float(t[blend].max() - t[blend].min())
    d = np.abs((rest[edges[:, 0]] - rest[edges[:, 1]]) @ a)
    d = d[d > 1e-9]
    step = float(np.median(d)) if len(d) else 1.0
    return span / step if step > 0 else 0.0


def measure(rest: np.ndarray, posed: np.ndarray, faces: Sequence[Sequence[int]], zone: np.ndarray,
            weight: Optional[np.ndarray] = None, joint: Optional[Sequence[float]] = None, radius: float = 0.0,
            axis: Optional[Sequence[float]] = None, edges: Optional[np.ndarray] = None) -> Dict[str, float]:
    """Metrics on the deformation zone only. See CLASSES for what each means."""
    if not len(zone):
        return {"zone_faces": 0.0}
    zf = [faces[i] for i in zone]
    zedges, _ = topology.edges_of(zf)
    height = float(np.ptp(rest[:, 2]) or 1.0)
    r = np.linalg.norm(rest[zedges[:, 0]] - rest[zedges[:, 1]], axis=1)
    p = np.linalg.norm(posed[zedges[:, 0]] - posed[zedges[:, 1]], axis=1)
    ok = r > 1e-3 * height
    ratio = p[ok] / r[ok] if ok.any() else np.ones(1)
    ar, ap = topology._face_areas(rest, zf), topology._face_areas(posed, zf)
    okf = ar > 1e-12
    arat = ap[okf] / ar[okf] if okf.any() else np.ones(1)
    a0, a1 = _quad_corner_angles(rest, zf), _quad_corner_angles(posed, zf)
    shear = float(np.percentile(np.abs(a1 - a0).max(axis=1), 95)) if len(a0) else 0.0
    out = {"zone_faces": float(len(zone)), "stretch": float(np.percentile(ratio, 99)), "squash": float(np.percentile(ratio, 1)),
           "shear": shear, "collapse": float((arat < 0.2).mean()), "flip": max(local_flips(rest, posed, zf), kabsch_flips(rest, posed, zf)),
           "worst_stretch": float(ratio.max()), "worst_squash": float(ratio.min())}
    if joint is not None and radius > 0:
        out["section"] = section_ratio(rest, posed, joint, radius)
    if weight is not None:
        zv = np.array(sorted({i for f in zf for i in f}), dtype=int)
        out["weight_jump"] = weight_jump(weight, edges if edges is not None else topology.edges_of(faces)[0], zv)
    if weight is not None and axis is not None:
        out["loops"] = float(blend_loops(weight, rest, axis, edges if edges is not None else topology.edges_of(faces)[0]))
        out["blend"] = blend_rows(weight, rest, edges if edges is not None else topology.edges_of(faces)[0], axis)
    return out


# ---- findings ---------------------------------------------------------------------------------------------


def findings(region: str, label: str, m: Dict[str, float], degrees: Optional[float] = None, cls: Optional[str] = None) -> List[Finding]:
    """One finding per metric against the region's class bands, scaled to the bend `degrees` (None for shape keys and rigid checks)."""
    cls = cls or REGION_CLASS.get(region, "limb_joint")
    if not m.get("zone_faces"):
        return [Finding(f"deform.{region}.{label}.zone", SKIP, f"{region}: nothing deforms in '{label}' (no weights or no moved vertices)")]
    out: List[Finding] = []
    for metric, direction in METRIC_DIR.items():
        band = CLASSES[cls].get(metric)
        if band is None or metric not in m:
            continue
        band = scaled(band, metric, cls, degrees)
        x = m[metric]
        sev = band.grade(x, direction)
        lim = f"{'<=' if direction == 'hi' else '>='} {band.warn:.3g}"
        out.append(Finding(f"deform.{region}.{label}.{metric}", sev, f"{region} ({cls}), {label}: {METRIC_TEXT[metric]}", x, lim,
                           METRIC_FIX[metric] if sev != PASS else ""))
    return out


def worst_reading(m: Dict[str, float], region: str, degrees: Optional[float] = None, cls: Optional[str] = None) -> Tuple[str, str]:
    """Which metric is furthest past its band, and as a word, for the TypeSafe state."""
    cname = cls or REGION_CLASS.get(region, "limb_joint")
    cls = CLASSES[cname]
    worst, score = "none", 0.0
    for metric, direction in METRIC_DIR.items():
        b = cls.get(metric)
        if b is None or metric not in m:
            continue
        b = scaled(b, metric, cname, degrees)
        x = m[metric]
        over = (x - b.warn) / max(abs(b.fail - b.warn), 1e-9) if direction == "hi" else (b.warn - x) / max(abs(b.warn - b.fail), 1e-9)
        if over > score:
            worst, score = metric, over
    word = "inside the range" if score <= 0 else "past the warn limit" if score < 1 else "past the fail limit"
    return worst, word


# ---- running the plan -------------------------------------------------------------------------------------


@dataclass
class Joint:
    """What a bend test needs about one bone: skin weights and geometry in world space (see bpy_adapter.joint_weights)."""
    weights: Dict[str, Tuple[np.ndarray, np.ndarray]]
    moving: Sequence[str]
    head: Sequence[float]
    axes: Sequence[Sequence[float]]
    total: Optional[np.ndarray]
    distal: Sequence[float]     # where the next bone down the chain starts: its motion fixes the flexing sign


def moving_weight(n: int, joint: Joint) -> np.ndarray:
    w = np.zeros(n)
    for g in joint.moving:
        if g in joint.weights:
            idx, ww = joint.weights[g]
            np.add.at(w, idx, ww)
    if joint.total is not None:
        w = np.where(joint.total > 0, w / np.where(joint.total > 0, joint.total, 1), 0.0)
    return np.clip(w, 0, 1)


def flexing_sign(m: Motion, rest: np.ndarray, joint: Joint) -> int:
    """+1 or -1: the sign of the bone-local axis rotation that moves the distal end toward `m.toward`."""
    probe = topology.lbs_rotate(np.asarray([joint.distal], float), {"d": (np.array([0]), np.array([1.0]))}, ["d"], joint.head,
                                joint.axes[m.axis], 5.0)
    move = probe[0] - np.asarray(joint.distal, float)
    return 1 if float(move @ np.asarray(m.toward, float)) >= 0 else -1


def run_motion(m: Motion, rest: np.ndarray, faces: Sequence[Sequence[int]], joint: Joint,
               edges: Optional[np.ndarray] = None, region_mask: Optional[np.ndarray] = None) -> List[Finding]:
    """Bend one joint to the end of its range of motion, both ways, and judge the zone against the region's bands."""
    if edges is None:
        edges, _ = topology.edges_of(faces)
    w = moving_weight(len(rest), joint)
    height = float(np.ptp(rest[:, 2]) or 1.0)
    sign = flexing_sign(m, rest, joint)
    axis = np.asarray(joint.axes[m.axis], float)
    limb_axis = np.asarray(joint.distal, float) - np.asarray(joint.head, float)
    out: List[Finding] = []
    for name, deg in ((m.label, sign * m.max_deg), (m.label + " (reverse)", -sign * m.rev_deg)):
        if abs(deg) < 1e-6:
            continue
        posed = topology.lbs_rotate(rest, joint.weights, joint.moving, joint.head, axis, deg, joint.total)
        zone = deformation_zone(faces, w, region_mask)
        met = measure(rest, posed, faces, zone, w, joint.head, 0.06 * height, limb_axis, edges)
        lab = f"{name} {abs(deg):g}deg".replace(" ", "_")
        out += findings(m.region, lab, met, abs(deg), m.cls)
        if name == m.label:
            lf = loop_finding(m, met, lab)
            if lf:
                out.append(lf)
    return out


def key_region(name: str) -> str:
    n = name.lower()
    for pat, region in (("lid|blink|wink|eye", "eyes"), ("brow", "brows"), ("nose|nostril", "nose"), ("cheek|puff", "cheeks"),
                        ("jaw|chin", "jaw"), ("ear", "ears"), ("mouth|lip|smile|frown|pucker|viseme|_aa|_oh|_ou|_ee|_ih|kiss|tongue|teeth", "mouth")):
        import re
        if re.search(pat, n):
            return region
    return "face"


def run_key(name: str, rest: np.ndarray, posed: np.ndarray, faces: Sequence[Sequence[int]]) -> List[Finding]:
    region = key_region(name)
    zone = deformation_zone(faces, np.zeros(len(rest)), rest=rest, posed=posed)
    return findings(region, f"key_{name}", measure(rest, posed, faces, zone))


def rigid_check(region: str, label: str, rest: np.ndarray, posed: np.ndarray, faces: Sequence[Sequence[int]]) -> List[Finding]:
    """For hair clumps, horns and rigid accessories: the whole piece should only move, never deform."""
    zone = np.arange(len(faces))
    return findings(region, label, measure(rest, posed, faces, zone))
