"""Rig completeness per body region, checked against the VRM humanoid bone specification (standards.VRM_HUMANOID).

Bone names are matched to VRM names by rule (Rigify DEF-, Mixamo, VRChat/Unity, plain "Left arm / Left elbow" names).
Names the rules cannot place are offered to TypeSafe (standard_mapper). Then each region reports whether its required
bones exist, how many optional bones (fingers, toes, eyes, jaw) are present, whether any VRM bone is claimed twice,
and whether parent/child order follows the spec's hierarchy.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Tuple

from . import standard_mapper as sm, standards as st
from .model import FAIL, INFO, PASS, SKIP, WARN, Finding

_FINGERS = {"thumb": "Thumb", "index": "Index", "middle": "Middle", "ring": "Ring", "little": "Little", "pinky": "Little", "pinkie": "Little"}


def _side(low: str) -> Optional[str]:
    if re.search(r"(^|[^a-z])left([^a-z]|$)|^left|[._ -]l(\b|$|[._ -])|_l$|\.l$|^l[._ -]", low):
        return "left"
    if re.search(r"(^|[^a-z])right([^a-z]|$)|^right|[._ -]r(\b|$|[._ -])|_r$|\.r$|^r[._ -]", low):
        return "right"
    return None


def vrm_name(bone: str) -> Optional[str]:
    """Rule-based VRM humanoid name for a bone, or None (also None for tip/end/twist helpers)."""
    orig = bone.lower()
    mixamo, rigify = orig.startswith("mixamorig"), orig.startswith("def-")
    low = bone.lower().replace("mixamorig:", "").replace("def-", "").replace("j_bip_c_", "").replace("j_bip_l_", "").replace("j_bip_r_", "")
    if re.search(r"(_end$|\bend$|twist|roll|corrective|tip$)", low):
        return None
    side = _side(low)
    pre = side or ""
    cap = (lambda s: s[:1].upper() + s[1:])
    # Rigify spine chain
    m = re.fullmatch(r"spine(?:\.(\d+))?", low)
    if m and rigify:
        i = int(m.group(1) or 0)
        return {0: "hips", 1: "spine", 2: "chest", 3: "upperChest", 4: "neck", 5: "neck", 6: "head"}.get(i)
    if re.fullmatch(r"(hips?|pelvis_root|root hips)", low):
        return "hips"
    if low == "spine":
        return "spine"
    if re.fullmatch(r"chest", low):
        return "chest"
    if re.fullmatch(r"upper ?chest", low):
        return "upperChest"
    if low == "neck":
        return "neck"
    if low == "head":
        return "head"
    if "jaw" in low:
        return "jaw"
    if re.search(r"eye", low) and not re.search(r"brow|lid|lash", low) and side:
        return f"{side}Eye"
    if not side:
        return None
    for key, fname in _FINGERS.items():
        if key in low:
            idx = re.search(r"(?:^|[ ._-])(\d)(?![\d])|\.0*(\d)|(\d)$", low.replace(" ", "."))
            n = None
            mm = re.search(r"\.0*(\d+)", low) or re.search(r"(\d)(?!.*\d)", low)
            if mm:
                n = int(mm.group(1))
            # Amshani style: base, .001, .002  -> 0,1,2 ; Rigify: .01 .02 .03 -> 1,2,3 ; Mixamo: 1,2,3
            base = 0 if re.search(r"\.\d{3}$", low) else None
            if re.search(r"\.\d{3}$", low):
                seg = int(low[-3:])
            elif re.search(r"\.\d{2}\b", low) or mm:
                seg = (n or 1) - 1
            else:
                seg = 0
            names = ("Metacarpal", "Proximal", "Distal") if fname == "Thumb" else ("Proximal", "Intermediate", "Distal")
            return f"{side}{fname}{names[min(max(seg, 0), 2)]}" if seg < 3 else None
    if re.search(r"shoulder|clavicle", low):
        return f"{side}Shoulder"
    if re.search(r"upper.?arm|^arm$|^arm[._ -]|(left|right)[ ._-]?arm$", low) and not re.search(r"fore|lower", low):
        return f"{side}UpperArm"
    if re.search(r"fore.?arm|lower.?arm|elbow", low):
        return f"{side}LowerArm"
    if re.search(r"^hand|[ ._-]hand|wrist", low) and not re.search(r"finger|thumb|index|middle|ring|pinky|little", low):
        return f"{side}Hand"
    if mixamo and re.search(r"(left|right)leg$", low):  # Mixamo: LeftUpLeg is the thigh, LeftLeg the shin
        return f"{side}LowerLeg"
    if re.search(r"up.?leg|upper.?leg|thigh|(left|right)[ ._-]?leg$", low) and not re.search(r"lower", low):
        return f"{side}UpperLeg"
    if re.search(r"lower.?leg|shin|calf|knee", low):
        return f"{side}LowerLeg"
    if re.search(r"foot|ankle", low):
        return f"{side}Foot"
    if re.search(r"toe", low):
        return f"{side}Toes"
    return None


def map_bones(bones: List[str], transport: Optional[Callable[[dict], dict]] = None) -> Dict[str, Tuple[Optional[str], str, float]]:
    out: Dict[str, Tuple[Optional[str], str, float]] = {}
    left = []
    for b in bones:
        v = vrm_name(b)
        if v:
            out[b] = (v, "rule", 1.0)
        elif re.search(r"(_end$|\bend$|twist|roll|corrective)", b.lower()):
            out[b] = (None, "helper", 1.0)
        else:
            left.append(b)
    if left and transport is not None:
        regions = {
            "torso_head": {n: n for n, (_, r) in st.VRM_HUMANOID.items() if r in ("hips", "waist", "chest", "neck", "skull", "eyes", "mouth")},
            "arm": {n: n for n, (_, r) in st.VRM_HUMANOID.items() if r in ("shoulders", "arms") },
            "leg": {n: n for n, (_, r) in st.VRM_HUMANOID.items() if r in ("legs", "feet")},
        }
        out.update(sm.map_to_options(left, regions, "humanoid bone", transport))
    else:
        out.update({b: (None, "unmapped", 0.0) for b in left})
    return out


def findings(mapping: Dict[str, Tuple[Optional[str], str, float]], parents: Dict[str, Optional[str]], label: str) -> List[Finding]:
    claimed: Dict[str, List[str]] = {}
    for bone, (std, how, _) in mapping.items():
        if std:
            claimed.setdefault(std, []).append(bone)
    out: List[Finding] = []
    # required bones and optional counts, per region
    by_region: Dict[str, List[str]] = {}
    for bone, (req, region) in st.VRM_HUMANOID.items():
        by_region.setdefault(region, []).append(bone)
    for region, names in by_region.items():
        req = [n for n in names if st.VRM_HUMANOID[n][0]]
        opt = [n for n in names if not st.VRM_HUMANOID[n][0]]
        miss = [n for n in req if n not in claimed]
        got_opt = [n for n in opt if n in claimed]
        if req:
            out.append(Finding(f"{region}.rig.required", FAIL if miss else PASS,
                               f"{label}: {len(req) - len(miss)}/{len(req)} required VRM humanoid bones" + (f"; missing {', '.join(miss)}" if miss else ""),
                               fix="Add or rename the bones to the VRM humanoid set (see docs/VALIDATORS.md)."))
        if opt:
            out.append(Finding(f"{region}.rig.optional", INFO, f"{label}: {len(got_opt)}/{len(opt)} optional VRM humanoid bones present"))
    dup = {k: v for k, v in claimed.items() if len(v) > 1}
    if dup:
        out.append(Finding("body.rig.duplicates", WARN, f"{label}: VRM bones claimed twice (humanoid bones must be unique): " +
                           "; ".join(f"{k} = {', '.join(v)}" for k, v in list(dup.items())[:4]), fix="Keep one bone per humanoid role."))
    # hierarchy: nearest mapped ancestor must be the spec's parent
    inv = {v[0]: k for k, v in claimed.items()}  # first claimant
    bad = []
    for std, bone_list in claimed.items():
        exp = st.VRM_PARENT.get(std)
        if exp is None:
            continue
        cur, anc = parents.get(bone_list[0]), None
        while cur:
            m = mapping.get(cur, (None,))[0]
            if m:
                anc = m
                break
            cur = parents.get(cur)
        # the spec lets optional parents be skipped: accept any ancestor that is the expected parent or its own spec ancestor
        chain, p = set(), exp
        while p:
            chain.add(p)
            p = st.VRM_PARENT.get(p)
        if anc is not None and anc not in chain:
            bad.append(f"{std} under {anc}")
    if parents:
        out.append(Finding("body.rig.hierarchy", FAIL if bad else PASS, f"{label}: bone hierarchy follows the VRM humanoid tree" + (f"; wrong: {', '.join(bad[:4])}" if bad else ""),
                           fix="Re-parent so hips > spine > chest > neck > head and the arm and leg chains match."))
    un = sorted(b for b, m in mapping.items() if m[0] is None and m[1] == "unmapped")
    if un:
        out.append(Finding("body.rig.unmapped", INFO, f"{label}: {len(un)} bones are not VRM humanoid bones (fine for extras): {', '.join(un[:8])}"))
    return out
