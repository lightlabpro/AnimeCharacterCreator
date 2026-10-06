"""External standards the per-region validators check against. Each block names the page it was read from.

Fetched and read while building this file:
  VRM humanoid bones     https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md
  VRM preset expressions https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/expressions.md
  ARKit 52 blendshapes   names found on https://hinzka.hatenablog.com/entry/2021/12/02/005814 (Perfect Sync article)
  FACS action units      https://en.wikipedia.org/wiki/Facial_Action_Coding_System (action unit table)
  glTF structure         Khronos glTF-Validator (https://github.com/KhronosGroup/glTF-Validator), run through node
"""
from __future__ import annotations

from typing import Dict, List, Tuple

# ---- VRM humanoid: bone -> (required, region). Hierarchy is the spec's parent/child tree. ------------------------
VRM_HUMANOID: Dict[str, Tuple[bool, str]] = {
    "hips": (True, "hips"), "spine": (True, "waist"), "chest": (False, "chest"), "upperChest": (False, "chest"),
    "neck": (False, "neck"), "head": (True, "skull"), "leftEye": (False, "eyes"), "rightEye": (False, "eyes"),
    "jaw": (False, "mouth"),
}
for _s in ("left", "right"):
    VRM_HUMANOID.update({
        f"{_s}Shoulder": (False, "shoulders"), f"{_s}UpperArm": (True, "arms"), f"{_s}LowerArm": (True, "arms"),
        f"{_s}Hand": (True, "hands"), f"{_s}UpperLeg": (True, "legs"), f"{_s}LowerLeg": (True, "legs"),
        f"{_s}Foot": (True, "feet"), f"{_s}Toes": (False, "feet"),
    })
    for _f, _parts in (("Thumb", ("Metacarpal", "Proximal", "Distal")), ("Index", ("Proximal", "Intermediate", "Distal")),
                       ("Middle", ("Proximal", "Intermediate", "Distal")), ("Ring", ("Proximal", "Intermediate", "Distal")),
                       ("Little", ("Proximal", "Intermediate", "Distal"))):
        for _p in _parts:
            VRM_HUMANOID[f"{_s}{_f}{_p}"] = (False, "hands")

VRM_PARENT: Dict[str, str] = {
    "spine": "hips", "chest": "spine", "upperChest": "chest", "neck": "upperChest", "head": "neck", "leftEye": "head",
    "rightEye": "head", "jaw": "head",
}
for _s in ("left", "right"):
    VRM_PARENT.update({f"{_s}Shoulder": "upperChest", f"{_s}UpperArm": f"{_s}Shoulder", f"{_s}LowerArm": f"{_s}UpperArm",
                       f"{_s}Hand": f"{_s}LowerArm", f"{_s}UpperLeg": "hips", f"{_s}LowerLeg": f"{_s}UpperLeg",
                       f"{_s}Foot": f"{_s}LowerLeg", f"{_s}Toes": f"{_s}Foot"})

# ---- VRM preset expressions, by the region they move -------------------------------------------------------------
VRM_EXPRESSIONS: Dict[str, Tuple[str, ...]] = {
    "eyes": ("blink", "blinkLeft", "blinkRight", "lookUp", "lookDown", "lookLeft", "lookRight"),
    "mouth": ("aa", "ih", "ou", "ee", "oh"),
    "face": ("neutral", "happy", "angry", "sad", "relaxed", "surprised"),
}

# ---- ARKit 52 blendshapes by region (the 52 names on the Perfect Sync page, collapsed to base + Left/Right) -------
def _lr(*names: str) -> Tuple[str, ...]:
    return tuple(f"{n}{s}" for n in names for s in ("Left", "Right"))


ARKIT_52: Dict[str, Tuple[str, ...]] = {
    "brows": _lr("browDown", "browOuterUp") + ("browInnerUp",),
    "cheeks": ("cheekPuff",) + _lr("cheekSquint"),
    "eyes": _lr("eyeBlink", "eyeLookDown", "eyeLookIn", "eyeLookOut", "eyeLookUp", "eyeSquint", "eyeWide"),
    "jaw": ("jawForward", "jawLeft", "jawOpen", "jawRight"),
    "mouth": ("mouthClose", "mouthFunnel", "mouthLeft", "mouthPucker", "mouthRight", "mouthRollLower", "mouthRollUpper",
              "mouthShrugLower", "mouthShrugUpper") + _lr("mouthDimple", "mouthFrown", "mouthLowerDown", "mouthPress",
                                                         "mouthSmile", "mouthStretch", "mouthUpperUp"),
    "nose": _lr("noseSneer"),
    "tongue": ("tongueOut",),
}
assert sum(len(v) for v in ARKIT_52.values()) == 52

# ---- FACS action units (numbers and names from the Wikipedia table) by region ------------------------------------
FACS_AU: Dict[str, Dict[int, str]] = {
    "brows": {1: "Inner brow raiser", 2: "Outer brow raiser", 4: "Brow lowerer"},
    "eyes": {5: "Upper lid raiser", 7: "Lid tightener", 41: "Lid droop", 42: "Slit", 43: "Eyes closed", 44: "Squint", 45: "Blink", 46: "Wink"},
    "cheeks": {6: "Cheek raiser", 33: "[Cheek] blow", 34: "[Cheek] puff", 35: "[Cheek] suck"},
    "nose": {9: "Nose wrinkler", 38: "Nostril dilator", 39: "Nostril compressor"},
    "mouth": {10: "Upper lip raiser", 12: "Lip corner puller", 13: "Sharp lip puller", 14: "Dimpler", 15: "Lip corner depressor",
              16: "Lower lip depressor", 17: "Chin raiser", 18: "Lip pucker", 20: "Lip stretcher", 22: "Lip funneler",
              23: "Lip tightener", 24: "Lip pressor", 25: "Lips part", 28: "Lip suck"},
    "jaw": {26: "Jaw drop", 27: "Mouth stretch", 29: "Jaw thrust", 30: "Jaw sideways", 31: "Jaw clencher"},
    "tongue": {19: "Tongue show", 36: "[Tongue] bulge"},
}

# ---- the project's own names (docs/CLAUDE_BUILD_PROMPT.md) mapped to the standards ------------------------------
# Deterministic first; anything unmatched goes to the TypeSafe mapper (expression_map.py).
PROJECT_TO_STANDARD: Dict[str, str] = {
    "PF-Blink_L": "eyeBlinkLeft", "PF-Blink_R": "eyeBlinkRight", "PF-EyeWide_L": "eyeWideLeft", "PF-EyeWide_R": "eyeWideRight",
    "PF-Squint_L": "eyeSquintLeft", "PF-Squint_R": "eyeSquintRight", "PF-JawOpen": "jawOpen",
    "PF-VisAA": "aa", "PF-VisEE": "ee", "PF-VisIH": "ih", "PF-VisOH": "oh", "PF-VisOO": "ou", "PF-VisMBP": "mouthClose",
    "PF-SmileClosed": "mouthSmileLeft", "PF-Frown": "mouthFrownLeft", "PF-Pout": "mouthPucker", "PF-Press": "mouthPressLeft",
    "PF-Surprise": "surprised", "PF-BrowInnerUp": "browInnerUp", "PF-BrowOuterUp": "browOuterUpLeft", "PF-BrowLower": "browDownLeft",
    "PF-Disgust": "noseSneerLeft", "PF-Cry": "sad",
}
# Common names seen on real avatars (Amshani uses VRChat viseme names).
VRCHAT_VISEMES: Dict[str, str] = {
    "vrc.v_aa": "aa", "vrc.v_e": "ee", "vrc.v_ih": "ih", "vrc.v_oh": "oh", "vrc.v_ou": "ou", "vrc.v_pp": "mouthClose",
    "vrc.v_sil": "neutral", "Blink L": "eyeBlinkLeft", "Blink R": "eyeBlinkRight", "Blink": "blink",
}


def all_standard_names() -> List[str]:
    names = {n for v in ARKIT_52.values() for n in v}
    for v in VRM_EXPRESSIONS.values():
        names.update(v)
    return sorted(names)


def region_of_standard(name: str) -> str:
    for region, items in ARKIT_52.items():
        if name in items:
            return region
    for region, items in VRM_EXPRESSIONS.items():
        if name in items:
            return "mouth" if region == "mouth" else region
    return "face"


# ---- Oculus/Meta 15 lip-sync visemes. VRChat's `vrc.v_*` shape keys use exactly these (suffix = viseme). ---------------
OCULUS_VISEMES = ("sil", "PP", "FF", "TH", "DD", "kk", "CH", "SS", "nn", "RR", "aa", "E", "I", "O", "U")
PROJECT_TO_OCULUS: Dict[str, str] = {
    "PF-VisMBP": "PP", "PF-VisFV": "FF", "PF-VisTH": "TH", "PF-VisL": "nn", "PF-VisSZ": "SS", "PF-VisAA": "aa",
    "PF-VisEE": "E", "PF-VisIH": "I", "PF-VisOH": "O", "PF-VisOO": "U",
}
