"""Topology analysis, numpy only: static structure, edge loops at joints, and deformation between two poses.

Static metrics read the mesh as it is. Deformation metrics compare a rest mesh with the same mesh bent (bone pose)
or shaped (shape key at 1): edge stretch and squash, face-area change and flipped normals are what a bad loop
layout or bad weighting produces. Thresholds are practical heuristics (marked as such), not from a paper.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .model import FAIL, INFO, PASS, WARN, Finding

Faces = Sequence[Sequence[int]]


def edges_of(faces: Faces) -> Tuple[np.ndarray, Dict[Tuple[int, int], int]]:
    count: Dict[Tuple[int, int], int] = {}
    for f in faces:
        n = len(f)
        for i in range(n):
            a, b = f[i], f[(i + 1) % n]
            e = (a, b) if a < b else (b, a)
            count[e] = count.get(e, 0) + 1
    return np.array(sorted(count), dtype=np.int64).reshape(-1, 2), count


def _normals(v: np.ndarray, faces: Faces) -> np.ndarray:
    n = np.zeros((len(faces), 3))
    for i, f in enumerate(faces):
        p = v[list(f)]
        n[i] = sum(np.cross(p[k], p[(k + 1) % len(p)]) for k in range(len(p)))
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.where(ln == 0, 1, ln)


def stats(v: np.ndarray, faces: Faces) -> Dict[str, object]:
    v = np.asarray(v, dtype=np.float64)
    edges, count = edges_of(faces)
    sizes = np.array([len(f) for f in faces])
    n_faces = max(len(faces), 1)
    valence = np.zeros(len(v), dtype=int)
    for a, b in edges:
        valence[a] += 1
        valence[b] += 1
    boundary_v = set()
    for (a, b), c in count.items():
        if c == 1:
            boundary_v.update((a, b))
    all_quads = np.ones(len(v), bool)  # vertices whose every face is a quad
    used = np.zeros(len(v), bool)
    for f in faces:
        used[list(f)] = True
        if len(f) != 4:
            all_quads[list(f)] = False
    interior = used & ~np.isin(np.arange(len(v)), list(boundary_v))
    pole_mask = interior & all_quads & ((valence == 3) | (valence >= 5))
    el = np.linalg.norm(v[edges[:, 0]] - v[edges[:, 1]], axis=1) if len(edges) else np.zeros(1)
    # quad skew (worst angle deviation from 90 degrees) and aspect ratio
    skew, aspect, warp = [], [], []
    for f in faces:
        if len(f) != 4:
            continue
        p = v[list(f)]
        e = [p[(k + 1) % 4] - p[k] for k in range(4)]
        L = [np.linalg.norm(x) or 1e-12 for x in e]
        ang = [np.degrees(np.arccos(np.clip(np.dot(-e[k], e[(k + 1) % 4]) / (L[k] * L[(k + 1) % 4]), -1, 1))) for k in range(4)]
        skew.append(max(abs(a - 90) for a in ang))
        aspect.append(max(L) / max(min(L), 1e-12))
        n = np.cross(p[1] - p[0], p[2] - p[0])
        nn = np.linalg.norm(n) or 1e-12
        warp.append(abs(np.dot(p[3] - p[0], n / nn)) / (np.mean(L) or 1e-12))
    hist = {int(k): int(c) for k, c in zip(*np.unique(valence[interior], return_counts=True))}
    return {
        "faces": len(faces), "tris": int((sizes == 3).sum()), "quads": int((sizes == 4).sum()), "ngons": int((sizes > 4).sum()),
        "quad_ratio": float((sizes == 4).sum() / n_faces), "tri_ratio": float((sizes == 3).sum() / n_faces),
        "ngon_ratio": float((sizes > 4).sum() / n_faces),
        "valence_hist": hist,
        "pole_fraction": float(pole_mask.sum() / max(interior.sum(), 1)),
        "poles": np.nonzero(pole_mask)[0].tolist(),
        "edge_len_cv": float(el.std() / (el.mean() or 1)),
        "quad_skew_p95": float(np.percentile(skew, 95)) if skew else 0.0,
        "quad_aspect_p95": float(np.percentile(aspect, 95)) if aspect else 1.0,
        "quad_warp_p95": float(np.percentile(warp, 95)) if warp else 0.0,
    }


def ring_count(v: np.ndarray, edges: np.ndarray, center: Sequence[float], axis: Sequence[float], radius: float,
               lateral: Optional[float] = None) -> int:
    """Edge loops that circle the limb around `axis`, within `radius` of `center` along the axis and within `lateral`
    (default 3x radius) of the axis sideways, so a limb thicker than the zone is still counted.

    A loop edge is one that runs around the limb (roughly perpendicular to the axis). Edges are grouped by their
    position along the axis; a group of at least 4 edges is one ring. Heuristic: reliable on quad limbs."""
    a = np.asarray(axis, float)
    a = a / (np.linalg.norm(a) or 1)
    c = np.asarray(center, float)
    p, q = v[edges[:, 0]], v[edges[:, 1]]
    mid, d = (p + q) / 2, q - p
    ln = np.linalg.norm(d, axis=1)
    rel = mid - c
    side = np.linalg.norm(rel - np.outer(rel @ a, a), axis=1)
    ok = (np.abs(rel @ a) <= radius * 1.2) & (side <= (lateral or 3 * radius)) & (ln > 0)
    ok &= np.abs((d / np.where(ln == 0, 1, ln)[:, None]) @ a) < 0.5
    if ok.sum() < 4:
        return 0
    t = (mid[ok] - c) @ a
    keep = np.abs(t) <= radius
    t = np.sort(t[keep])
    if len(t) < 4:
        return 0
    tol = 0.35 * float(np.median(ln[ok]))
    groups, cur = [], [t[0]]
    for x in t[1:]:
        if x - cur[-1] <= tol:
            cur.append(x)
        else:
            groups.append(cur)
            cur = [x]
    groups.append(cur)
    return sum(1 for g in groups if len(g) >= 4)


def deformation(rest: np.ndarray, posed: np.ndarray, faces: Faces, edges: Optional[np.ndarray] = None,
                min_edge_frac: float = 1e-3) -> Dict[str, object]:
    """Compare a rest mesh with the same mesh bent. Ratios are posed/rest, so 1.0 = unchanged.

    Edges shorter than min_edge_frac of the mesh height (coincident vertices) are ignored: their ratio is meaningless
    and they are a hygiene problem, reported separately."""
    if edges is None:
        edges, _ = edges_of(faces)
    r = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    p = np.linalg.norm(posed[edges[:, 0]] - posed[edges[:, 1]], axis=1)
    ok = r > min_edge_frac * float(rest[:, 2].max() - rest[:, 2].min() or 1.0)
    ratio = p[ok] / r[ok]
    area_r = _face_areas(rest, faces)
    area_p = _face_areas(posed, faces)
    okf = area_r > 1e-12
    arat = area_p[okf] / area_r[okf]
    dots = (_normals(rest, faces) * _normals(posed, faces)).sum(axis=1)
    worst = np.nonzero(ok)[0][np.argsort(np.abs(np.log(np.clip(ratio, 1e-6, None))))[-5:]]
    return {
        "ignored_degenerate_edges": int((~ok).sum()),
        "frac_stretch_gt_2": float((ratio > 2.0).mean()), "frac_squash_lt_half": float((ratio < 0.5).mean()),
        "edge_stretch_max": float(ratio.max()), "edge_squash_min": float(ratio.min()),
        "edge_ratio_p01": float(np.percentile(ratio, 1)), "edge_ratio_p99": float(np.percentile(ratio, 99)),
        "area_ratio_p01": float(np.percentile(arat, 1)), "area_ratio_p99": float(np.percentile(arat, 99)),
        "flipped_fraction": float((dots < 0).mean()),
        "worst_locations": ((rest[edges[worst, 0]] + rest[edges[worst, 1]]) / 2).tolist(),
    }


def lbs_rotate(v: np.ndarray, weights: Dict[str, Tuple[np.ndarray, np.ndarray]], moving: Sequence[str],
               head: Sequence[float], axis: Sequence[float], degrees: float,
               total: Optional[np.ndarray] = None) -> np.ndarray:
    """Linear blend skinning of one joint bend, as Blender's armature modifier computes it.

    weights: group name -> (vertex indices, weights). `moving` lists the joint bone and all its descendants; they
    rotate by `degrees` about `axis` through `head`. Vertices weighted only to other bones stay at rest, and any
    weight not given to a moving bone stays at rest too. Used instead of depsgraph posing so it is deterministic.

    `total` is each vertex's summed weight over ALL deform bones. Blender normalises by it (a vertex weighted 0.3 to
    the elbow and 0.3 to the shoulder is 50/50, not 30/70), so pass it when available.
    """
    a = np.asarray(axis, float)
    a = a / (np.linalg.norm(a) or 1)
    th = np.radians(degrees)
    h = np.asarray(head, float)
    rel = v - h
    rotated = (rel * np.cos(th) + np.cross(a, rel) * np.sin(th) + np.outer(rel @ a, a) * (1 - np.cos(th))) + h
    w = np.zeros(len(v))
    for g in moving:
        if g in weights:
            idx, ww = weights[g]
            np.add.at(w, idx, ww)
    if total is not None:
        w = np.where(total > 0, w / np.where(total > 0, total, 1), 0.0)
    w = np.clip(w, 0, 1)[:, None]
    return v + w * (rotated - v)


def _face_areas(v: np.ndarray, faces: Faces) -> np.ndarray:
    out = np.zeros(len(faces))
    for i, f in enumerate(faces):
        p = v[list(f)]
        out[i] = np.linalg.norm(sum(np.cross(p[k], p[(k + 1) % len(p)]) for k in range(len(p)))) / 2
    return out


# ---- findings ---------------------------------------------------------------------------------------------

LOOP_TARGETS = {"shoulder": (3, 5), "elbow": (2, 4), "knee": (4, 6)}  # docs/anatomy-manual.md section 13


def static_findings(s: Dict[str, object], label: str) -> List[Finding]:
    out = [
        Finding(f"topology.{label}.quads", PASS if s["quad_ratio"] >= 0.9 else WARN if s["quad_ratio"] >= 0.8 else FAIL,
                f"{label}: quads (manual s13: quads throughout)", s["quad_ratio"], ">= 0.90",
                f"{s['tris']} triangles and {s['ngons']} n-gons: retopologise them out of bend areas."),
        Finding(f"topology.{label}.ngons", PASS if s["ngon_ratio"] == 0 else WARN,
                f"{label}: n-gons (5+ sided) break subdivision and shape keys", s["ngon_ratio"], "0",
                "Split n-gons into quads."),
        Finding(f"topology.{label}.skew", PASS if s["quad_skew_p95"] <= 30 else WARN if s["quad_skew_p95"] <= 45 else FAIL,
                f"{label}: 95th-percentile quad corner deviation from 90 degrees (heuristic)", s["quad_skew_p95"], "<= 30 deg",
                "Relax/grid-fill the sheared quads."),
        Finding(f"topology.{label}.aspect", PASS if s["quad_aspect_p95"] <= 4 else WARN,
                f"{label}: 95th-percentile quad aspect ratio (heuristic)", s["quad_aspect_p95"], "<= 4",
                "Long thin quads stretch under bends; add loops or merge."),
        Finding(f"topology.{label}.warp", PASS if s["quad_warp_p95"] <= 0.15 else WARN,
                f"{label}: 95th-percentile quad non-planarity (heuristic)", s["quad_warp_p95"], "<= 0.15"),
        Finding(f"topology.{label}.poles", INFO, f"{label}: {len(s['poles'])} poles ({s['pole_fraction'] * 100:.1f}% of interior vertices); "
                "manual s13: keep them on flat, low-motion areas"),
    ]
    return out


def loop_findings(counts: Dict[str, int], label: str) -> List[Finding]:
    out = []
    for joint, n in counts.items():
        lo, hi = LOOP_TARGETS.get(joint, (None, None))
        if lo is None:
            out.append(Finding(f"topology.{label}.loops.{joint}", INFO, f"{label}: {n} loops at {joint}", float(n)))
            continue
        sev = PASS if lo <= n <= hi else WARN if n >= lo - 1 else FAIL
        out.append(Finding(f"topology.{label}.loops.{joint}", sev, f"{label}: edge loops at the {joint} (manual s13)", float(n),
                           f"{lo}..{hi}", "Add loops with an arc on the inside of the bend." if n < lo else "Remove loops; too dense for a clean bend."))
    return out


def deformation_findings(d: Dict[str, object], label: str, local: bool = False) -> List[Finding]:
    """local=True for shape keys: small regions (lids, lips) legitimately stretch a few edges a lot, so judge the
    share of edges beyond 2x/0.5x and the flipped faces, not the single worst edge."""
    smax, smin, fl = d["edge_stretch_max"], d["edge_squash_min"], d["flipped_fraction"]
    if local:
        bad = d["frac_stretch_gt_2"] + d["frac_squash_lt_half"]
        return [
            Finding(f"deform.{label}.extreme_edges", PASS if bad <= 0.01 else WARN if bad <= 0.03 else FAIL,
                    f"{label}: share of edges stretched past 2x or squashed under 0.5x (heuristic)", bad, "<= 0.01",
                    "Spread the key over more loops or reduce its strength."),
            Finding(f"deform.{label}.flips", PASS if fl <= 0.002 else WARN if fl <= 0.01 else FAIL,
                    f"{label}: faces whose normal flips", fl, "<= 0.002", "The key folds the surface through itself."),
        ]
    extreme = d["frac_stretch_gt_2"] + d["frac_squash_lt_half"]
    return [
        Finding(f"deform.{label}.extreme_edges", PASS if extreme <= 0.005 else WARN if extreme <= 0.02 else FAIL,
                f"{label}: share of edges stretched past 2x or squashed under 0.5x (heuristic)", extreme, "<= 0.005",
                "Add loops or retune weights where edges stretch or collapse."),
        Finding(f"deform.{label}.flips", PASS if fl <= 0.002 else WARN if fl <= 0.01 else FAIL,
                f"{label}: faces whose normal flips vs rest", fl, "<= 0.002", "Fix weights/topology where the surface folds through itself."),
        Finding(f"deform.{label}.worst_edge", INFO,
                f"{label}: single worst edge stretches {smax:.1f}x and squashes to {smin:.2f}x (isolated spikes are normal; judge by the share above)"),
    ]
