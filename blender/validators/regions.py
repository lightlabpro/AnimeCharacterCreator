"""The region registry. Ids are the app's own Region type (src/model/types.ts) plus the extra element regions the
library needs. Every validator reports into a region and a feature, so the report reads per region and per feature.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .model import Finding, Report


@dataclass(frozen=True)
class Region:
    id: str
    label: str
    group: str                      # head | body | surface | element | clothing | accessory | quadruped
    features: Tuple[str, ...]
    bodies: Tuple[str, ...] = ("adult", "child")
    vertex_groups: Tuple[str, ...] = ()   # regexes over lower-case vertex group names that select this region
    vrm_bones: Tuple[str, ...] = ()


def _r(id, label, group, features, bodies=("adult", "child"), vertex_groups=(), vrm_bones=()):
    return Region(id, label, group, tuple(features), tuple(bodies), tuple(vertex_groups), tuple(vrm_bones))


REGIONS: Dict[str, Region] = {r.id: r for r in [
    # --- head (app Region ids)
    _r("skull", "Skull and head shape", "head", ("proportion", "forehead", "temple_width"), vertex_groups=(r"head", r"spine\.00[4-6]"), vrm_bones=("head",)),
    _r("face", "Face shape", "head", ("thirds", "profile")),
    _r("eyes", "Eyes", "head", ("eyeball", "placement", "spacing", "symmetry", "lashes", "performance"), vertex_groups=(r"eye", r"lid", r"lash"),
       vrm_bones=("leftEye", "rightEye")),
    _r("brows", "Eyebrows", "head", ("shape", "placement", "bendability", "performance"), vertex_groups=(r"brow",)),
    _r("nose", "Nose", "head", ("protrusion", "position", "performance"), vertex_groups=(r"nose",)),
    _r("mouth", "Mouth, lips, teeth, tongue", "head", ("placement", "teeth", "tongue", "visemes", "emotions"), vertex_groups=(r"lip", r"mouth", r"teeth", r"tongue", r"jaw"),
       vrm_bones=("jaw",)),
    _r("jaw", "Jaw and chin", "head", ("width", "chin")),
    _r("cheeks", "Cheeks", "head", ("fullness",)),
    _r("ears", "Ears", "head", ("size", "placement"), vertex_groups=(r"ear",)),
    _r("hair", "Hair", "head", ("clumps", "uv", "fit", "contract")),
    _r("facial_hair", "Facial hair", "head", ("pieces", "contract"), bodies=("adult",)),
    # --- body
    _r("neck", "Neck", "body", ("proportion",), vertex_groups=(r"neck", r"spine\.00[3-5]"), vrm_bones=("neck",)),
    _r("shoulders", "Shoulders", "body", ("width", "rig"), vertex_groups=(r"shoulder", r"clavicle"), vrm_bones=("leftShoulder", "rightShoulder")),
    _r("chest", "Chest", "body", ("lines",), vertex_groups=(r"chest", r"breast", r"spine\.00[1-2]"), vrm_bones=("chest", "upperChest")),
    _r("waist", "Waist", "body", ("lines",), vertex_groups=(r"spine$", r"waist"), vrm_bones=("spine",)),
    _r("hips", "Hips and pelvis", "body", ("width", "midpoint"), vertex_groups=(r"hips", r"pelvis"), vrm_bones=("hips",)),
    _r("arms", "Arms", "body", ("proportion", "rig"), vertex_groups=(r"arm", r"elbow"), vrm_bones=("leftUpperArm", "leftLowerArm", "rightUpperArm", "rightLowerArm")),
    _r("hands", "Hands and fingers", "body", ("size", "fingers"), vertex_groups=(r"hand", r"finger", r"thumb", r"palm"), vrm_bones=("leftHand", "rightHand")),
    _r("legs", "Legs", "body", ("proportion", "rig"), vertex_groups=(r"leg", r"thigh", r"shin", r"knee", r"calf"), vrm_bones=("leftUpperLeg", "leftLowerLeg", "rightUpperLeg", "rightLowerLeg")),
    _r("feet", "Feet", "body", ("size", "stance"), vertex_groups=(r"foot", r"ankle", r"toe"), vrm_bones=("leftFoot", "rightFoot", "leftToes", "rightToes")),
    _r("body", "Whole body", "body", ("height", "pose", "origin", "budget", "topology")),
    # --- humanoid beast elements (app look slots)
    _r("muzzle", "Muzzle or beak", "element", ("proportion", "mouth_corner", "visemes")),
    _r("tail", "Tail", "element", ("root", "length", "taper")),
    _r("wings", "Wings", "element", ("span", "root", "membrane")),
    _r("horns", "Horns", "element", ("symmetry", "base", "length")),
    _r("mane", "Mane, crest, feathers", "element", ("coverage", "clumps")),
    _r("frill", "Neck frill or gills", "element", ("size",)),
    _r("surface", "Surface (fur, scales, feathers, hide)", "surface", ("plates", "coverage", "pattern")),
    _r("archetype", "Archetype distinctness", "element", ("silhouette", "recipe")),
    # --- clothing and accessories (library accessory types)
    _r("clothing", "Clothing and armor", "clothing", ("fit", "coverage", "skinning", "contract")),
    _r("accessory", "Accessories", "accessory", ("socket", "scale", "contract"), bodies=("adult", "child", "robot")),
    # --- full-beast quadruped
    _r("quadruped", "Quadruped body", "quadruped", ("weight", "legs", "spine", "wings", "tail", "neck"), bodies=("dragon",)),
]}

# Existing finding prefixes -> region, so every earlier validator also shows up per region.
CHECK_TO_REGION: Dict[str, str] = {
    "anatomy.height_heads": "body", "anatomy.chin_line": "body", "anatomy.legs_fraction": "legs", "anatomy.nipple_line": "chest",
    "anatomy.navel_line": "waist", "anatomy.pubis_line": "hips", "anatomy.shoulder_width_heads": "shoulders",
    "anatomy.hip_width_heads": "hips", "anatomy.wrist_to_crotch_heads": "arms", "anatomy.elbow_to_navel_heads": "arms",
    "anatomy.thigh_shin_ratio": "legs", "anatomy.hand_length_heads": "hands", "anatomy.foot_vs_forearm": "feet",
    "anatomy.arm_angle_deg": "arms", "anatomy.eye_line_norm": "eyes", "anatomy.eye_gap_eye_widths": "eyes",
    "anatomy.eye_height_width": "eyes", "anatomy.mouth_norm": "mouth", "anatomy.temple_width_norm": "skull",
    "anatomy.neck_head_width": "neck", "anatomy.forehead_slope": "skull", "anatomy.shoulder_height_m": "quadruped",
    "anatomy.symmetry": "body", "contract.budget": "body", "contract.transforms": "body", "contract.origin": "body",
    "contract.forward": "body", "contract.quads": "body", "contract.sockets": "body",
}


def region_of_check(check: str) -> str:
    for prefix, region in CHECK_TO_REGION.items():
        if check.startswith(prefix):
            return region
    parts = check.split(".")
    if parts[0] in REGIONS:
        return parts[0]
    if parts[0] == "rig":
        return "body"
    if parts[0] in ("hair",):
        return "hair"
    if parts[0] == "deform" and len(parts) > 1 and parts[1] in REGIONS:
        return parts[1]
    if parts[0] in ("topology", "deform"):
        return "body"
    if parts[0] == "hygiene":
        return "body"
    if len(parts) > 1 and parts[0] in REGIONS:
        return parts[0]
    return "body"


def group_by_region(findings: Iterable[Finding]) -> Dict[str, List[Finding]]:
    out: Dict[str, List[Finding]] = {}
    for f in findings:
        out.setdefault(region_of_check(f.check), []).append(f)
    return out


def region_table(report: Report) -> List[Tuple[str, str, int, int, int, int]]:
    """(region id, label, fail, warn, pass, skip) rows for every region that has findings, in registry order."""
    grouped = group_by_region(report.findings)
    rows = []
    for rid, reg in REGIONS.items():
        fs = grouped.get(rid)
        if not fs:
            continue
        c = lambda s: sum(1 for f in fs if f.severity == s)
        rows.append((rid, reg.label, c("fail"), c("warn"), c("pass"), c("skip")))
    return rows


def select_vertices_by_group(group_names: Dict[int, str], region: str):
    """Group ids whose lower-case names match the region's vertex-group patterns."""
    pats = [re.compile(p) for p in REGIONS[region].vertex_groups]
    return {i for i, n in group_names.items() if any(p.search(n.lower()) for p in pats)}
