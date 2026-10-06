"""Turn a SceneInfo into the ratio metrics in spec.METRICS.

Landmarks come from `LM-*` markers first (explicit, placed by the modeler), then from
DEF- bones for the limbs. Anything that cannot be found is reported as skipped with the
name that is missing, never guessed silently.
"""
from __future__ import annotations

import math
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .model import SceneInfo, Vec

# Marker names a modeler places (empties named LM-<Name>); sides use _L / _R.
MARKERS = (
    "Crown", "Chin", "Floor", "Nipple", "Navel", "Pubis", "EyeInner_L", "EyeInner_R",
    "EyeOuter_L", "EyeOuter_R", "EyeTop_L", "EyeBottom_L", "Mouth", "HandTip_L", "HeelBack_L", "ToeTip_L",
)

def _side_re(side: str) -> str:
    s = side.lower()
    return rf"(?:[._\-]{s}(?![a-z])|{'left' if s == 'l' else 'right'})"


# Bone-name patterns per limb landmark. First match wins; order is specific to generic.
# Covers Rigify (upper_arm/forearm/thigh/shin), Mixamo/VRM (UpperArm/LowerArm/UpperLeg), and the plain
# "Left arm / Left elbow / Left wrist / Left Leg / Left knee / Left ankle" naming found on Amshani.
_BONE_PATTERNS = {
    "shoulder": [r"upper.?arm", r"^(?:left|right)[ ._-]?arm$", r"^arm[._-]"],
    "elbow": [r"fore.?arm", r"lower.?arm", r"elbow"],
    "wrist": [r"^(?:left|right)?[ ._-]?hand(?![a-z])", r"wrist", r"^hand[._-]"],
    "hip": [r"thigh", r"upper.?leg", r"^(?:left|right)[ ._-]?leg$"],
    "knee": [r"shin", r"calf", r"lower.?leg", r"knee"],
    "ankle": [r"foot(?!.*toe)", r"ankle"],
}


def _find_bone(bones: Dict[str, Tuple[Vec, Vec]], role: str, side: str) -> Optional[Tuple[Vec, Vec]]:
    sre = _side_re(side)
    for pat in _BONE_PATTERNS[role]:
        for name, ht in bones.items():
            low = name.lower()
            if re.search(pat, low) and re.search(sre, low):
                return ht
    return None


def find_bone_name(names, role: str, side: str) -> Optional[str]:
    """Name of the bone playing `role` (shoulder, elbow, wrist, hip, knee, ankle) on `side` (L or R)."""
    sre = _side_re(side)
    for pat in _BONE_PATTERNS[role]:
        for name in names:
            low = name.lower()
            if re.search(pat, low) and re.search(sre, low):
                return name
    return None


def _dist(a: Vec, b: Vec) -> float:
    return math.dist(a, b)


def landmarks(scene: SceneInfo) -> Tuple[Dict[str, Vec], List[str]]:
    """Returns (landmarks, notes). Notes list what was derived rather than marked."""
    lm: Dict[str, Vec] = {}
    notes: List[str] = []
    for k, v in scene.markers.items():
        lm[k[3:] if k.startswith("LM-") else k] = v
    for side in ("L", "R"):
        for role in ("shoulder", "elbow", "wrist", "hip", "knee", "ankle"):
            key = f"{role}_{side}"
            if key in lm:
                continue
            ht = _find_bone(scene.bones, role, side)
            if ht:
                lm[key] = ht[0]
                notes.append(f"{key} taken from bone head")
    if "HandTip_L" not in lm and "wrist_L" in lm:
        tips = [(n, ht) for n, ht in scene.bones.items()
                if re.search(r"middle|f_middle", n.lower()) and re.search(_side_re("l"), n.lower())]
        if tips:
            far = max(tips, key=lambda t: max(_dist(lm["wrist_L"], t[1][0]), _dist(lm["wrist_L"], t[1][1])))
            lm["HandTip_L"] = max(far[1], key=lambda p: _dist(lm["wrist_L"], p))
            notes.append(f"HandTip_L taken from the farthest middle-finger bone ({far[0]})")
    if "Floor" not in lm and scene.body_verts:
        lm["Floor"] = (0.0, 0.0, min(v[2] for v in scene.body_verts))
        notes.append("Floor taken from the lowest body vertex")
    if "Crown" not in lm and scene.body_verts:
        lm["Crown"] = (0.0, 0.0, max(v[2] for v in scene.body_verts))
        notes.append("Crown taken from the highest body vertex (hair excluded only if the body mesh has none)")
    return lm, notes


def _x_extent(verts: Iterable[Vec], z: float, tol: float, y_max: Optional[float] = None) -> Optional[float]:
    xs = [v[0] for v in verts if abs(v[2] - z) <= tol and (y_max is None or v[1] <= y_max)]
    return (max(xs) - min(xs)) if len(xs) >= 2 else None


def _front_y(verts: Iterable[Vec], z: float, tol: float) -> Optional[float]:
    ys = [v[1] for v in verts if abs(v[2] - z) <= tol]
    return min(ys) if ys else None


def metrics(scene: SceneInfo) -> Tuple[Dict[str, float], List[str], List[str]]:
    """Returns (metrics, missing_landmarks, notes)."""
    lm, notes = landmarks(scene)
    out: Dict[str, float] = {}
    missing: List[str] = []

    def need(*names: str) -> bool:
        gone = [n for n in names if n not in lm]
        for n in gone:
            if n not in missing:
                missing.append(n)
        return not gone

    if scene.kind == "dragon":
        sh = [lm[k] for k in ("shoulder_L", "shoulder_R") if k in lm]
        if sh and "Floor" in lm:
            out["shoulder_height_m"] = sum(p[2] for p in sh) / len(sh) - lm["Floor"][2]
        else:
            missing += [n for n in ("shoulder_L", "Floor") if n not in lm]
        return out, missing, notes

    if need("Crown", "Chin", "Floor"):
        head_h = lm["Crown"][2] - lm["Chin"][2]
        height = lm["Crown"][2] - lm["Floor"][2]
        out["height_heads"] = height / head_h
        out["chin_line"] = (lm["Crown"][2] - lm["Chin"][2]) / height
        for name, key in (("Nipple", "nipple_line"), ("Navel", "navel_line"), ("Pubis", "pubis_line")):
            if name in lm:
                out[key] = (lm["Crown"][2] - lm[name][2]) / height
            else:
                missing.append(name)
        if "Pubis" in lm:
            out["legs_fraction"] = (lm["Pubis"][2] - lm["Floor"][2]) / height

        # Outer points (acromion, greater trochanter) when marked; otherwise joint centres, which checks.anatomy reports but does not grade.
        sl, sr = lm.get("ShoulderOuter_L", lm.get("shoulder_L")), lm.get("ShoulderOuter_R", lm.get("shoulder_R"))
        hl, hr = lm.get("HipOuter_L", lm.get("hip_L")), lm.get("HipOuter_R", lm.get("hip_R"))
        if sl and sr:
            out["shoulder_width_heads"] = abs(sl[0] - sr[0]) / head_h
        else:
            missing += [n for n in ("shoulder_L", "shoulder_R") if n not in lm]
        if hl and hr:
            out["hip_width_heads"] = abs(hl[0] - hr[0]) / head_h
        else:
            missing += [n for n in ("hip_L", "hip_R") if n not in lm]
        # Pose-independent: hang the measured limb lengths straight down from the shoulder joint.
        if "shoulder_L" in lm and "elbow_L" in lm:
            upper = _dist(lm["shoulder_L"], lm["elbow_L"])
            if "Navel" in lm:
                out["elbow_to_navel_heads"] = (lm["shoulder_L"][2] - upper - lm["Navel"][2]) / head_h
            if "Pubis" in lm and "wrist_L" in lm:
                arm = upper + _dist(lm["elbow_L"], lm["wrist_L"])
                out["wrist_to_crotch_heads"] = (lm["shoulder_L"][2] - arm - lm["Pubis"][2]) / head_h
        if "hip_L" in lm and "knee_L" in lm and "ankle_L" in lm:
            shin = _dist(lm["knee_L"], lm["ankle_L"])
            if shin > 0:
                out["thigh_shin_ratio"] = _dist(lm["hip_L"], lm["knee_L"]) / shin
        if "wrist_L" in lm and "HandTip_L" in lm:
            out["hand_length_heads"] = _dist(lm["wrist_L"], lm["HandTip_L"]) / head_h
        if "HeelBack_L" in lm and "ToeTip_L" in lm and "elbow_L" in lm and "wrist_L" in lm:
            fa = _dist(lm["elbow_L"], lm["wrist_L"])
            if fa > 0:
                out["foot_vs_forearm"] = abs(lm["ToeTip_L"][1] - lm["HeelBack_L"][1]) / fa
        if "shoulder_L" in lm and "wrist_L" in lm:
            d = [lm["wrist_L"][i] - lm["shoulder_L"][i] for i in range(3)]
            n = math.sqrt(sum(c * c for c in d))
            if n > 0:
                out["arm_angle_deg"] = math.degrees(math.acos(max(-1.0, min(1.0, -d[2] / n))))

        # Face, normalised by skull height H = head_h (chin = 0).
        chin_z = lm["Chin"][2]
        eyes_z = [lm[k][2] for k in ("EyeInner_L", "EyeInner_R", "EyeOuter_L", "EyeOuter_R") if k in lm]
        if eyes_z:
            out["eye_line_norm"] = (sum(eyes_z) / len(eyes_z) - chin_z) / head_h
        else:
            missing.append("EyeInner_L/R + EyeOuter_L/R")
        if "EyeInner_L" in lm and "EyeInner_R" in lm and "EyeOuter_L" in lm:
            w = _dist(lm["EyeInner_L"], lm["EyeOuter_L"])
            if w > 0:
                out["eye_gap_eye_widths"] = _dist(lm["EyeInner_L"], lm["EyeInner_R"]) / w
                if "EyeTop_L" in lm and "EyeBottom_L" in lm:
                    out["eye_height_width"] = _dist(lm["EyeTop_L"], lm["EyeBottom_L"]) / w
        if "Mouth" in lm:
            out["mouth_norm"] = (lm["Mouth"][2] - chin_z) / head_h
        else:
            missing.append("Mouth")

        verts = scene.body_verts
        if verts:
            tol = 0.02 * head_h
            ys = [v[1] for v in verts if v[2] >= chin_z]
            if ys:
                depth_cut = min(ys) + 0.6 * (max(ys) - min(ys))  # keep the face side, drop ears
                temple = _x_extent(verts, chin_z + 0.6 * head_h, tol, depth_cut)
                if temple:
                    out["temple_width_norm"] = temple / head_h
                    neck = _x_extent(verts, chin_z - 0.12 * head_h, 0.05 * head_h)  # wide slab: neck meshes can be sparse
                    if neck:
                        out["neck_head_width"] = neck / temple
            eye_z = chin_z + out.get("eye_line_norm", 0.45) * head_h
            y_eye = _front_y(verts, eye_z, tol)
            y_up = _front_y(verts, chin_z + 0.8 * head_h, tol)
            if y_eye is not None and y_up is not None:
                # Forward is -Y, so a receding forehead has a larger (less negative) y higher up.
                out["forehead_slope"] = max(0.0, (y_up - y_eye)) / head_h
        else:
            notes.append("no body vertices: head-width, neck and forehead checks skipped")
    return out, missing, notes


def per_side_asymmetry(scene: SceneInfo) -> Optional[float]:
    """Max left/right height difference of paired landmarks, in head heights. A sanity check."""
    lm, _ = landmarks(scene)
    if "Crown" not in lm or "Chin" not in lm:
        return None
    head_h = lm["Crown"][2] - lm["Chin"][2]
    gaps = [abs(lm[f"{r}_L"][2] - lm[f"{r}_R"][2]) for r in ("shoulder", "elbow", "wrist", "hip", "knee", "ankle")
            if f"{r}_L" in lm and f"{r}_R" in lm]
    return max(gaps) / head_h if gaps else None


def joint_based(scene: SceneInfo) -> set:
    """Width metrics measured between joint centres (from bones) rather than between acromion / trochanter markers.
    Joint centres sit well inside the outer widths the spec bands describe, so these are reported but not graded."""
    keys = set()
    if not ({"LM-shoulder_L", "LM-shoulder_R"} <= set(scene.markers) or {"LM-ShoulderOuter_L", "LM-ShoulderOuter_R"} <= set(scene.markers)):
        keys.add("shoulder_width_heads")
    if not ({"LM-hip_L", "LM-hip_R"} <= set(scene.markers) or {"LM-HipOuter_L", "LM-HipOuter_R"} <= set(scene.markers)):
        keys.add("hip_width_heads")
    # joint centres passed as shoulder_L / hip_L come from bones; only explicit outer markers count as measured
    if "LM-ShoulderOuter_L" not in scene.markers:
        keys.add("shoulder_width_heads")
    if "LM-HipOuter_L" not in scene.markers:
        keys.add("hip_width_heads")
    return keys
