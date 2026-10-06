"""Clothing and armor validators (library types: clothing, armor, replacement; accessory contract in the build prompt).

Geometry (numpy): how the garment sits on the body (penetration, gap, coverage), whether it is skinned like the body, and
the manifest contract. Bands marked heuristic are not from a published source and are calibrated on Hina's clothes where noted.
Contract fields come from docs/CLAUDE_BUILD_PROMPT.md ACCESSORY CONTRACT.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .hair import vertex_normals
from .model import FAIL, INFO, PASS, SKIP, WARN, Finding
from .spec import Band

CONTRACT_FIELDS = ("id", "display_name", "slot", "socket", "type", "hides_body_groups", "follows_shape_keys", "color_slots", "damage_masks")
TYPES = ("rigid", "deform", "replacement", "prop", "creature")
BANDS = {
    "penetration": Band(0.0, 0.03, 0.07),     # heuristic: share of garment vertices more than 0.3% of body height inside the body
    "skin_match": Band(0.7, 1.0, 0.2),        # heuristic: garment vertices whose main bone matches the nearest body vertex
    "unweighted": Band(0.0, 0.02, 0.05),      # deforming garments must be weighted
}


def fit(garment_v: np.ndarray, body_v: np.ndarray, body_faces: Sequence[Sequence[int]], height: float, chunk: int = 300) -> Dict[str, float]:
    """Signed distance of garment vertices to the nearest body vertex along its outward normal (units: body height)."""
    nrm = vertex_normals(body_v, body_faces)
    if ((body_v - body_v.mean(axis=0)) * nrm).sum(axis=1).mean() < 0:
        nrm = -nrm
    signed = np.empty(len(garment_v))
    nearest = np.empty(len(garment_v), dtype=int)
    for i in range(0, len(garment_v), chunk):
        d = ((garment_v[i:i + chunk, None, :] - body_v[None, :, :]) ** 2).sum(-1)
        j = d.argmin(axis=1)
        nearest[i:i + chunk] = j
        signed[i:i + chunk] = ((garment_v[i:i + chunk] - body_v[j]) * nrm[j]).sum(axis=1)
    dist = np.linalg.norm(garment_v - body_v[nearest], axis=1)
    near = dist < 0.05 * height  # only vertices that lie on the body (not a flowing cape) count for fit
    s = signed[near] / height if near.any() else np.array([0.0])
    return {"on_body_fraction": float(near.mean()), "penetration_fraction": float((s < -0.003).mean()),
            "gap_median": float(np.median(s)), "gap_p05": float(np.percentile(s, 5)), "gap_p95": float(np.percentile(s, 95)),
            "nearest": nearest}


def coverage(garment_v: np.ndarray, body_v: np.ndarray, height: float, floor: float, zones: Dict[str, Tuple[float, float]],
             radius: float = 0.03, chunk: int = 400) -> Dict[str, float]:
    """Share of body vertices within `radius` (of height) of the garment, per height zone (fractions of height)."""
    covered = np.zeros(len(body_v), bool)
    for i in range(0, len(body_v), chunk):
        d = ((body_v[i:i + chunk, None, :] - garment_v[None, ::max(1, len(garment_v) // 3000), :]) ** 2).sum(-1)
        covered[i:i + chunk] = np.sqrt(d.min(axis=1)) <= radius * height
    out = {"overall": float(covered.mean())}
    for name, (lo, hi) in zones.items():
        m = (body_v[:, 2] >= floor + lo * height) & (body_v[:, 2] < floor + hi * height)
        out[name] = float(covered[m].mean()) if m.any() else 0.0
    return out


def skin_agreement(g_dom: Sequence[Optional[str]], b_dom: Sequence[Optional[str]], nearest: np.ndarray) -> Dict[str, float]:
    """g_dom / b_dom: dominant bone name per vertex (None = unweighted)."""
    unw = sum(1 for g in g_dom if g is None) / max(len(g_dom), 1)
    same = [g == b_dom[j] for g, j in zip(g_dom, nearest) if g is not None and b_dom[j] is not None]
    return {"unweighted_fraction": float(unw), "skin_match": float(np.mean(same)) if same else 0.0}


def findings(slot: str, fit_m: Dict[str, float], cov: Optional[Dict[str, float]], skin: Optional[Dict[str, float]], label: str,
             deforming: bool = True) -> List[Finding]:
    out = [
        Finding(f"clothing.fit.penetration", BANDS["penetration"].grade(fit_m["penetration_fraction"]),
                f"{label}: share of garment vertices pushed inside the body", fit_m["penetration_fraction"], "<= 0.03",
                "Offset the garment outward or add a push-out corrective (do not Boolean it into the body).", "heuristic"),
        Finding("clothing.fit.gap", INFO, f"{label}: garment sits {fit_m['gap_median'] * 100:.2f}% of body height off the skin (median); 5-95% range "
                f"{fit_m['gap_p05'] * 100:.2f}..{fit_m['gap_p95'] * 100:.2f}%", fit_m["gap_median"]),
        Finding("clothing.fit.on_body", INFO, f"{label}: {fit_m['on_body_fraction'] * 100:.0f}% of the garment lies on the body (the rest hangs free)", fit_m["on_body_fraction"]),
    ]
    if cov:
        for k, v in cov.items():
            out.append(Finding(f"clothing.coverage.{k}", INFO, f"{label}: covers {v * 100:.0f}% of the body in zone '{k}'", v))
    if skin is not None and deforming:
        out.append(Finding("clothing.skinning.unweighted", BANDS["unweighted"].grade(skin["unweighted_fraction"]),
                           f"{label}: garment vertices with no bone weights", skin["unweighted_fraction"], "<= 0.02", "Weight every vertex of a deforming garment.", "heuristic"))
        out.append(Finding("clothing.skinning.match", BANDS["skin_match"].grade(skin["skin_match"]),
                           f"{label}: garment moves with the same main bone as the body beneath it", skin["skin_match"], ">= 0.70",
                           "Transfer weights from the body to the garment.", "heuristic, calibrated on Hina (0.75)"))
    return out


def contract_findings(manifest: dict, label: str, body_keys: Sequence[str] = ()) -> List[Finding]:
    out = []
    miss = [k for k in CONTRACT_FIELDS if k not in manifest]
    out.append(Finding("clothing.contract.fields", FAIL if miss else PASS, f"{label}: accessory manifest fields" + (f" missing: {', '.join(miss)}" if miss else " present"),
                       fix="Add the missing fields to the collection's custom properties and docs/ASSET_CONTRACT.md."))
    t = manifest.get("type")
    if t is not None:
        out.append(Finding("clothing.contract.type", PASS if t in TYPES else FAIL, f"{label}: type '{t}' is one of {', '.join(TYPES)}"))
    if t == "deform":
        follows = manifest.get("follows_shape_keys") or []
        gone = [k for k in follows if body_keys and k not in body_keys]
        out.append(Finding("clothing.contract.follows", FAIL if (not follows or gone) else PASS,
                           f"{label}: deform assets carry the body shape keys of the region they cover" +
                           (" (none listed)" if not follows else f"; not on the body: {', '.join(gone)}" if gone else ""),
                           fix="List the ID- keys the garment shares with the body and give it the same key names."))
    if t == "replacement" and not manifest.get("hides_body_groups"):
        out.append(Finding("clothing.contract.hides", FAIL, f"{label}: replacement assets must name the body groups they hide"))
    if str(manifest.get("socket", "")).startswith("SOC-") is False and manifest.get("socket"):
        out.append(Finding("clothing.contract.socket", FAIL, f"{label}: socket '{manifest.get('socket')}' is not a SOC- name"))
    return out
