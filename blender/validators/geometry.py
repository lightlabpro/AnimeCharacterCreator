"""3D comparison and mesh hygiene, numpy only.

Chamfer distance and F1@threshold follow the PAniC-3D evaluation (_scripts/eval/measure.py: p2s / s2p, mean as
cd, F1 at fixed thresholds in a normalised box). Hygiene follows Meshy's printing check, which grades a mesh
healthy / warning / error on holes, non-manifold edges and degenerate faces, and TripoSG's removal of tiny
floating fragments.

Chamfer only means something between meshes of the SAME character (a Blender model vs the generated mesh it was
retopologised from, a slider at 0.5 vs the average of 0 and 1, a mesh vs its own mirror). Two different characters
will never overlap, so never use it as a correctness score against an unrelated reference.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .model import FAIL, INFO, PASS, WARN, Finding


def normalise(points: np.ndarray, height: Optional[float] = None) -> np.ndarray:
    """Centre on x/y, put the lowest point at z = 0, and scale so the height is 1 (so thresholds are ratios)."""
    p = np.asarray(points, dtype=np.float64)
    h = height if height else float(p[:, 2].max() - p[:, 2].min())
    out = p - np.array([(p[:, 0].max() + p[:, 0].min()) / 2, (p[:, 1].max() + p[:, 1].min()) / 2, p[:, 2].min()])
    return out / h


def _nn(a: np.ndarray, b: np.ndarray, chunk: int = 512) -> np.ndarray:
    out = np.empty(len(a))
    for i in range(0, len(a), chunk):
        d = ((a[i:i + chunk, None, :] - b[None, :, :]) ** 2).sum(-1)
        out[i:i + chunk] = np.sqrt(d.min(axis=1))
    return out


def subsample(p: np.ndarray, n: int = 3000, seed: int = 0) -> np.ndarray:
    if len(p) <= n:
        return p
    return p[np.random.default_rng(seed).choice(len(p), n, replace=False)]


def chamfer_f1(a: np.ndarray, b: np.ndarray, thresholds: Sequence[float] = (0.005, 0.01, 0.02)) -> Dict[str, float]:
    """a, b: Nx3 points already normalised (height 1). Returns cd and f1@t for each threshold."""
    a, b = subsample(a), subsample(b)
    p2s, s2p = _nn(a, b), _nn(b, a)
    res = {"cd": float((p2s.mean() + s2p.mean()) / 2)}
    for t in thresholds:
        prec, rec = float((p2s < t).mean()), float((s2p < t).mean())
        res[f"f1@{t:g}"] = 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)
    return res


def mirror_symmetry(verts: np.ndarray) -> float:
    """Chamfer between the mesh and its x-mirror, in height units. 0 = perfectly symmetric."""
    p = normalise(verts)
    m = p * np.array([-1, 1, 1])
    return chamfer_f1(p, m, ())["cd"]


def fidelity_findings(candidate: np.ndarray, source: np.ndarray, label: str,
                      f1_pass: float = 0.90, f1_warn: float = 0.75) -> List[Finding]:
    """Candidate vs the mesh it was made from (same character). F1 at 1% of height."""
    r = chamfer_f1(normalise(candidate, None), normalise(source, None))
    f1 = r["f1@0.01"]
    sev = PASS if f1 >= f1_pass else WARN if f1 >= f1_warn else FAIL
    return [Finding(f"geometry.{label}.f1", sev, f"{label}: surface within 1% of height of its source (F1)", f1,
                    f">= {f1_pass:.2f}", "Retopology drifted from the source; re-project or re-snap."),
            Finding(f"geometry.{label}.cd", INFO, f"{label}: chamfer distance, height = 1", r["cd"])]


def symmetry_finding(verts: np.ndarray, tol: float = 0.01) -> Finding:
    cd = mirror_symmetry(verts)
    sev = PASS if cd <= tol else WARN if cd <= 3 * tol else FAIL
    return Finding("geometry.symmetry", sev, "mesh vs its own mirror (chamfer, height = 1)", cd, f"<= {tol:g}",
                   "Mirror the modelled half or fix the asymmetric region (shape keys are exempt).")


def hygiene(verts: np.ndarray, faces: Sequence[Sequence[int]], min_component_frac: float = 0.01) -> Dict[str, object]:
    """verts Nx3, faces list of index tuples (tris/quads/ngons). Returns counts the findings are built from."""
    edge_count: Dict[Tuple[int, int], int] = {}
    used = np.zeros(len(verts), bool)
    degenerate = 0
    for f in faces:
        f = list(f)
        used[f] = True
        for i in range(len(f)):
            e = tuple(sorted((f[i], f[(i + 1) % len(f)])))
            edge_count[e] = edge_count.get(e, 0) + 1
        if len(set(f)) < len(f):
            degenerate += 1
            continue
        p = np.asarray(verts)[f]
        # polygon area through the vector area of a fan
        a = np.linalg.norm(sum(np.cross(p[i], p[(i + 1) % len(p)]) for i in range(len(p)))) / 2
        if a < 1e-12:
            degenerate += 1
    boundary = sum(1 for c in edge_count.values() if c == 1)
    nonmanifold = sum(1 for c in edge_count.values() if c > 2)
    # connected components by union-find over faces
    parent = list(range(len(verts)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for f in faces:
        r0 = find(f[0])
        for v in f[1:]:
            parent[find(v)] = r0
    sizes: Dict[int, int] = {}
    for v in np.nonzero(used)[0]:
        sizes[find(int(v))] = sizes.get(find(int(v)), 0) + 1
    total = sum(sizes.values()) or 1
    floaters = sum(1 for s in sizes.values() if s / total < min_component_frac)
    return {"edges": len(edge_count), "boundary_edges": boundary, "nonmanifold_edges": nonmanifold,
            "degenerate_faces": degenerate, "loose_vertices": int((~used).sum()), "components": len(sizes),
            "floaters": floaters}


def hygiene_findings(h: Dict[str, object], label: str, allow_open: bool = False, multi_part: bool = False) -> List[Finding]:
    """Meshy-style grade. Characters are open at wrists/ankles/neck by design, so boundary edges only warn.

    multi_part=True for hair, accessories and anything built from separate closed shells (Amshani's hair is 49
    clumps in one mesh); fragments are expected there, so that check is skipped."""
    out: List[Finding] = []
    bad = [k for k in ("nonmanifold_edges", "degenerate_faces") if h[k]]
    sev = FAIL if bad else PASS
    out.append(Finding(f"hygiene.{label}.topology", sev,
                       f"{label}: non-manifold edges {h['nonmanifold_edges']}, degenerate faces {h['degenerate_faces']}",
                       fix="Merge by distance, dissolve degenerate faces, fix edges shared by 3+ faces."))
    out.append(Finding(f"hygiene.{label}.loose", WARN if h["loose_vertices"] else PASS,
                       f"{label}: {h['loose_vertices']} vertices belong to no face", fix="Delete loose geometry."))
    if not multi_part:
        out.append(Finding(f"hygiene.{label}.floaters", WARN if h["floaters"] else PASS,
                           f"{label}: {h['floaters']} tiny disconnected fragment(s) among {h['components']} parts",
                           fix="Remove stray fragments (TripoSG drops components under a size cutoff)."))
    if not allow_open and h["boundary_edges"]:
        out.append(Finding(f"hygiene.{label}.holes", WARN, f"{label}: {h['boundary_edges']} open boundary edges"))
    return out
