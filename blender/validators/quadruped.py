"""Quadruped dragon validators (full-beast body). From docs/anatomy-manual.md section 11 and the build prompt DRAGON SPECIES.

  - forelimbs carry about 60% of the weight (the dog figure the manual cites): centre of mass between the feet
  - default shoulder height 1.6 to 2.2 m (build prompt), already in spec.METRICS['shoulder_height_m']
  - elbows and knees sit near belly level; wrist height consistent front and back
  - wing roots sit behind and above the forelimbs
  - neck and tail are one spine with a smooth taper (reuses beast.radius_profile / taper_score)
Forward is -Y and Z is up, as everywhere in the library.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np

from . import beast
from .model import FAIL, INFO, PASS, SKIP, WARN, Finding
from .spec import Band

BANDS = {
    "fore_weight": Band(0.50, 0.70, 0.08),        # manual s11: ~60% on the forelimbs
    "elbow_belly": Band(0.0, 0.12, 0.08),          # manual s11: elbows and knees at belly level (|difference| / shoulder height)
    "wrist_match": Band(0.0, 0.10, 0.08),          # manual s11: front and hind wrist height consistent
    "wing_behind": Band(0.0, 0.6, 0.15),           # manual s11: wing roots behind the forelimbs (fraction of torso length behind the shoulder)
    "wing_above": Band(0.0, 1.0, 0.2),             # manual s11: ...and above (root height over shoulder, in shoulder heights, >= 0)
}


def surface_centroid(v: np.ndarray, faces: Sequence[Sequence[int]]) -> np.ndarray:
    """Triangle-area-weighted centroid: a stand-in for the centre of mass of a hollow shell."""
    tot, acc = 0.0, np.zeros(3)
    for f in faces:
        for k in range(1, len(f) - 1):
            a, b, c = v[f[0]], v[f[k]], v[f[k + 1]]
            ar = np.linalg.norm(np.cross(b - a, c - a)) / 2
            tot += ar
            acc += ar * (a + b + c) / 3
    return acc / (tot or 1)


def metrics(v: np.ndarray, faces: Sequence[Sequence[int]], lm: Dict[str, Sequence[float]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    need = ("FootFront_L", "FootFront_R", "FootHind_L", "FootHind_R")
    if all(k in lm for k in need):
        fore = (np.array(lm["FootFront_L"]) + np.array(lm["FootFront_R"])) / 2
        hind = (np.array(lm["FootHind_L"]) + np.array(lm["FootHind_R"])) / 2
        axis = fore[:2] - hind[:2]
        L = float(np.linalg.norm(axis))
        axis = axis / (L or 1)
        com = surface_centroid(v, faces)
        out["fore_weight_fraction"] = float(np.clip((com[:2] - hind[:2]) @ axis / (L or 1), -1, 2))
    height = None
    if "shoulder_L" in lm and "Floor" in lm:
        height = float(lm["shoulder_L"][2] - lm["Floor"][2])
        out["shoulder_height"] = height
    if height:
        if "Belly" in lm and "elbow_L" in lm:
            out["elbow_belly_gap"] = float(abs(lm["elbow_L"][2] - lm["Belly"][2]) / height)
        if "Belly" in lm and "knee_L" in lm:
            out["knee_belly_gap"] = float(abs(lm["knee_L"][2] - lm["Belly"][2]) / height)
        if "wrist_L" in lm and "ankle_hind_L" in lm:
            out["wrist_height_mismatch"] = float(abs((lm["wrist_L"][2] - lm["Floor"][2]) - (lm["ankle_hind_L"][2] - lm["Floor"][2])) / height)
        if "WingRoot_L" in lm and "shoulder_L" in lm:
            out["wing_root_above_shoulder"] = float((lm["WingRoot_L"][2] - lm["shoulder_L"][2]) / height)
            torso = abs(lm["FootHind_L"][1] - lm["FootFront_L"][1]) if "FootHind_L" in lm else 0
            if torso:
                out["wing_root_behind_shoulder"] = float((lm["WingRoot_L"][1] - lm["shoulder_L"][1]) / torso)  # +Y is toward the tail
    return out


def findings(m: Dict[str, float], label: str) -> List[Finding]:
    out: List[Finding] = []
    def g(feature, key, band, msg, expected, fix):
        if key in m:
            out.append(Finding(f"quadruped.{feature}.{key}", band.grade(m[key]), f"{label}: {msg}", m[key], expected, fix, "manual s11"))
    g("weight", "fore_weight_fraction", BANDS["fore_weight"], "share of weight carried by the forelimbs", "0.50..0.70", "Shift mass toward the shoulders and forelimbs (heavier chest, shorter back).")
    g("legs", "elbow_belly_gap", BANDS["elbow_belly"], "elbow height vs belly level (over shoulder height)", "<= 0.12", "Hide the elbow in the body: raise it to belly level.")
    g("legs", "knee_belly_gap", BANDS["elbow_belly"], "knee height vs belly level (over shoulder height)", "<= 0.12", "Hide the knee in the body: raise it to belly level.")
    g("legs", "wrist_height_mismatch", BANDS["wrist_match"], "front wrist height vs hind heel height (over shoulder height)", "<= 0.10", "Pick one stance (plantigrade/digitigrade/unguligrade) and keep front and hind consistent.")
    g("wings", "wing_root_above_shoulder", BANDS["wing_above"], "wing root height above the shoulder (shoulder heights)", ">= 0", "Move the wing root above the forelimb shoulder.")
    g("wings", "wing_root_behind_shoulder", BANDS["wing_behind"], "wing root position behind the shoulder (torso lengths)", "0..0.6", "Place the wing root behind the forelimb, on its own shoulder mass.")
    if "shoulder_height" in m:
        out.append(Finding("quadruped.legs.shoulder_height", INFO, f"{label}: shoulder height {m['shoulder_height']:.2f} (build prompt target 1.6 to 2.2 m at size 1)", m["shoulder_height"]))
    return out
