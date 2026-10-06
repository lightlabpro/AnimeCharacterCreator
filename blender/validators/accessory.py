"""Accessory placement validators for the library's accessory slots (docs/CLAUDE_BUILD_PROMPT.md ACCESSORY CONTRACT).

One check per slot, from the landmarks. The bands are heuristics (the prompt names the sockets and the types, not sizes) and are
labelled as such; the contract itself (socket, type, hidden groups) is checked in clothing.contract_findings.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from .model import FAIL, INFO, PASS, SKIP, WARN, Finding
from .spec import Band

SLOT_SOCKET = {"bandana": "SOC-HeadTop", "eyewear": "SOC-Eyewear", "shoes": ("SOC-Foot_L", "SOC-Foot_R"), "belt": "SOC-Waist",
               "cape": "SOC-Cape", "weapon_melee": "SOC-Weapon_R", "weapon_ranged": "SOC-Weapon_L", "organic": "SOC-OrganicForeArm_L"}


def _ext(v: np.ndarray) -> np.ndarray:
    return v.max(axis=0) - v.min(axis=0)


def metrics(slot: str, v: np.ndarray, lm: Dict[str, Tuple[float, float, float]], head_width: Optional[float] = None) -> Dict[str, float]:
    """Slot-specific placement ratios (all relative to body or head size)."""
    out: Dict[str, float] = {}
    if "Crown" not in lm or "Floor" not in lm:
        return out
    height = lm["Crown"][2] - lm["Floor"][2]
    head_h = lm["Crown"][2] - lm["Chin"][2] if "Chin" in lm else height / 7.25
    e, c = _ext(v), (v.max(axis=0) + v.min(axis=0)) / 2
    eye_z = np.mean([lm[k][2] for k in ("EyeInner_L", "EyeOuter_L") if k in lm]) if "EyeInner_L" in lm else None
    if slot == "eyewear":
        if eye_z is not None:
            out["centre_vs_eye_line"] = float((c[2] - eye_z) / head_h)
        if head_width:
            out["width_over_head_width"] = float(e[0] / head_width)
    elif slot == "bandana":
        out["centre_height_in_head"] = float((c[2] - lm["Chin"][2]) / head_h) if "Chin" in lm else 0.0
        if head_width:
            out["width_over_head_width"] = float(e[0] / head_width)
    elif slot == "shoes":
        if "HeelBack_L" in lm and "ToeTip_L" in lm:
            foot = abs(lm["ToeTip_L"][1] - lm["HeelBack_L"][1])
            out["length_over_foot_length"] = float(e[1] / foot) if foot > 0 else 0.0
        out["top_height_over_body"] = float((v[:, 2].max() - lm["Floor"][2]) / height)
    elif slot == "belt":
        out["centre_height_over_body"] = float((c[2] - lm["Floor"][2]) / height)
        out["thickness_over_head_height"] = float(e[2] / head_h)
    elif slot == "cape":
        shoulder_z = np.mean([lm[k][2] for k in ("shoulder_L", "shoulder_R") if k in lm]) if "shoulder_L" in lm else lm["Crown"][2] - 1.5 * head_h
        out["top_vs_shoulder"] = float((v[:, 2].max() - shoulder_z) / head_h)
        out["length_over_body"] = float(e[2] / height)
    elif slot in ("weapon_melee", "weapon_ranged"):
        out["longest_side_over_body"] = float(e.max() / height)
        key = "wrist_R" if slot == "weapon_melee" else "wrist_L"
        if key in lm:
            d = np.linalg.norm(v - np.array(lm[key]), axis=1).min()
            out["nearest_point_to_hand_over_head"] = float(d / head_h)
    return out


BANDS: Dict[str, Dict[str, Tuple[Band, str, str]]] = {
    "eyewear": {"centre_vs_eye_line": (Band(-0.12, 0.12, 0.1), "lens centre sits on the eye line", "Move the frame to the eyes."),
                "width_over_head_width": (Band(0.9, 1.4, 0.2), "frame width relative to head width", "Scale the frame to the head.")},
    "bandana": {"width_over_head_width": (Band(0.95, 1.5, 0.3), "bandana width relative to head width", "Fit the band around the head.")},
    "shoes": {"length_over_foot_length": (Band(1.0, 1.5, 0.2), "shoe length relative to the foot", "Scale the shoe to the foot."),
              "top_height_over_body": (Band(0.0, 0.40, 0.1), "shoe top height as a fraction of body height", "Shoes should not reach above the knee.")},
    "belt": {"centre_height_over_body": (Band(0.45, 0.65, 0.07), "belt height as a fraction of body height (waist to hips)", "Place the belt at the waist.")},
    "cape": {"top_vs_shoulder": (Band(-0.5, 0.6, 0.3), "cape top relative to the shoulders (head heights)", "Attach the cape at the shoulders.")},
    "weapon_melee": {"nearest_point_to_hand_over_head": (Band(0.0, 0.35, 0.3), "weapon grip distance from the right hand (head heights)", "Align the grip with SOC-Weapon_R."),
                     "longest_side_over_body": (Band(0.2, 0.9, 0.2), "weapon length relative to body height", "Scale the weapon to a one-handed size.")},
    "weapon_ranged": {"nearest_point_to_hand_over_head": (Band(0.0, 0.35, 0.3), "weapon grip distance from the left hand (head heights)", "Align the grip with SOC-Weapon_L."),
                      "longest_side_over_body": (Band(0.1, 0.6, 0.2), "weapon length relative to body height", "Scale to a compact ranged weapon.")},
}


def findings(slot: str, m: Dict[str, float], label: str, parent: str = "") -> List[Finding]:
    out: List[Finding] = []
    want = SLOT_SOCKET.get(slot)
    if want and parent is not None:
        ok = parent in (want if isinstance(want, tuple) else (want,))
        out.append(Finding("accessory.socket.parent", PASS if ok else FAIL, f"{label}: parented to {want if isinstance(want, str) else ' or '.join(want)} ({parent or 'no parent'})",
                           fix="Parent the accessory to its socket; do not parent it to the body."))
    for key, (band, msg, fix) in BANDS.get(slot, {}).items():
        if key in m:
            out.append(Finding(f"accessory.scale.{key}", band.grade(m[key]), f"{label}: {msg}", m[key], band.text(), fix, "heuristic"))
    return out
