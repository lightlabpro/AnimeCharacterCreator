"""Per-feature face validators: eyes, eyebrows, nose, mouth and teeth, ears, jaw.

Inputs are the head mesh, the separate part objects when they exist, and the landmarks. A metric gets a Band only where the
manual, the modeling skill or the build prompt gives a figure; the others are reported with their reference envelope
(references/profiles) and read by the TypeSafe region judge, never graded against a number invented here.
Forward is -Y, Z is up (SceneInfo.flip_forward() makes +Y references conform).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from .model import FAIL, INFO, PASS, SKIP, WARN, Finding
from .spec import Band

PART_ALIASES: Dict[str, Tuple[str, ...]] = {
    "eye_L": ("CHR_Eye_L", "eye.l", "eye_l", "Eye_L"), "eye_R": ("CHR_Eye_R", "eye.r", "eye_r", "Eye_R"),
    "brows": ("CHR_Brows", "eyebrows", "brows", "eyebrow"), "lashes": ("CHR_Lashes", "lashes", "eyelashes"),
    "teeth_upper": ("CHR_TeethUpper", "teeth.t", "teeth_upper", "teethupper"), "teeth_lower": ("CHR_TeethLower", "teeth.b", "teeth_lower", "teethlower"),
    "tongue": ("CHR_Tongue", "tongue"),
}

BANDS = {
    "eyeball_roundness": Band(0.7, 1.0, 0.1),       # build prompt: "spheres or slight ovals"
    "nose_tip_fraction": Band(0.40, 0.85, 0.12),     # manual s8: about halfway (0.5) on a realistic face; Hina 0.77 and Amshani 0.74 sit higher (anime)
    "brow_verts_per_side": Band(6, 400, 2),          # build prompt: brows need "enough geometry to bend"; Hina has 7 per side
    "symmetry": Band(0.0, 0.025, 0.03),              # heuristic: paired parts match within 2.5% of head height (Hina: eyes 0.021, brows 0.018)
}


def _bbox(v: np.ndarray) -> np.ndarray:
    return v.max(axis=0) - v.min(axis=0)


def _centre(v: np.ndarray) -> np.ndarray:
    return (v.max(axis=0) + v.min(axis=0)) / 2


def metrics(parts: Dict[str, Tuple[np.ndarray, list]], body_v: Optional[np.ndarray], lm: Dict[str, Tuple[float, float, float]]) -> Dict[str, float]:
    """Feature metrics, all in head heights (H) or as ratios. Only what can be measured is returned."""
    out: Dict[str, float] = {}
    if "Crown" not in lm or "Chin" not in lm:
        return out
    chin, crown = lm["Chin"][2], lm["Crown"][2]
    H = crown - chin
    eye_z = None
    zs = [lm[k][2] for k in ("EyeInner_L", "EyeInner_R", "EyeOuter_L", "EyeOuter_R") if k in lm]
    if zs:
        eye_z = float(np.mean(zs))
    P = {k: np.asarray(v[0], float) for k, v in parts.items() if len(v[0])}
    # the head's own midline (references are not centred on x = 0)
    mid = 0.0
    if body_v is not None and len(body_v):
        hh = body_v[(body_v[:, 2] >= chin + 0.3 * H)]
        if len(hh):
            mid = float((hh[:, 0].min() + hh[:, 0].max()) / 2)
    # --- eyes
    if "eye_L" in P and "eye_R" in P:
        a, b = P["eye_L"], P["eye_R"]
        da, db = _bbox(a), _bbox(b)
        out["eyeball_over_head_height"] = float(np.mean([da.max(), db.max()]) / H)
        out["eyeball_roundness"] = float(np.mean([da.min() / da.max(), db.min() / db.max()]))
        ca, cb = _centre(a), _centre(b)
        # Rotation-proof symmetry: eye height difference and size ratio. The head may be yawed (Hina is about 7 degrees),
        # so x/y mirror offsets are not meaningful; the yaw itself is reported.
        out["eye_pair_asymmetry_z"] = float(abs(ca[2] - cb[2]) / H)
        out["eye_pair_size_ratio"] = float(min(da.max(), db.max()) / max(da.max(), db.max()))
        out["head_yaw_degrees"] = float(abs(np.degrees(np.arctan2(ca[1] - cb[1], abs(ca[0] - cb[0]) or 1e-9))))
        eye_z = float((ca[2] + cb[2]) / 2)
    # --- brows
    if "brows" in P:
        v = P["brows"]
        left, right = v[v[:, 0] >= mid], v[v[:, 0] < mid]
        if len(left) and len(right):
            out["brow_verts_per_side"] = float(min(len(left), len(right)))
            out["brow_asymmetry"] = float(abs(left[:, 2].mean() - right[:, 2].mean()) / H)
            lw = float(np.mean([_bbox(left)[0], _bbox(right)[0]]))
            out["brow_length_over_head_width"] = float(lw / (_bbox(body_v[body_v[:, 2] >= chin])[0] if body_v is not None else H))
            out["brow_thickness_over_length"] = float(np.mean([_bbox(left)[2], _bbox(right)[2]]) / max(lw, 1e-9))
            if eye_z is not None and "eye_L" in P:
                out["brow_gap_over_head_height"] = float((v[:, 2].mean() - P["eye_L"][:, 2].max()) / H)
    # --- nose, ears, jaw from the head surface
    if body_v is not None and len(body_v):
        head = body_v[body_v[:, 2] >= chin]
        if eye_z is not None:
            slab = head[(np.abs(head[:, 0]) < 0.08 * H) & (head[:, 2] > chin + 0.12 * H) & (head[:, 2] < eye_z)]
            def front_at(z, tol=0.04):
                m = head[(np.abs(head[:, 0] - mid) < 0.08 * H) & (np.abs(head[:, 2] - z) < tol * H)]
                return float(m[:, 1].min()) if len(m) else None
            if len(slab):
                tip = slab[slab[:, 1].argmin()]
                out["nose_tip_fraction"] = float((tip[2] - chin) / (eye_z - chin))
                # face plane: straight line from the forehead (just above the eyes) to the chin front
                top_z, bot_z = eye_z + 0.12 * H, chin + 0.04 * H
                ft, fb = front_at(top_z), front_at(bot_z)
                if ft is not None and fb is not None:
                    plane_y = fb + (ft - fb) * (tip[2] - bot_z) / (top_z - bot_z)
                    out["nose_protrusion_over_head_height"] = float((plane_y - tip[1]) / H)
                if "Mouth" in lm:
                    out["mouth_fraction_nose_to_chin"] = float((lm["Mouth"][2] - chin) / (tip[2] - chin))
        band = head[(head[:, 2] >= chin + 0.25 * H) & (head[:, 2] <= chin + 0.70 * H)]
        if len(band):
            xmax = float(np.abs(band[:, 0]).max())
            ear = band[np.abs(band[:, 0]) >= 0.93 * xmax]
            out["ear_height_over_head_height"] = float((ear[:, 2].max() - ear[:, 2].min()) / H)
            if eye_z is not None:
                out["ear_centre_vs_eye_line"] = float((ear[:, 2].mean() - eye_z) / H)
        jaw = head[np.abs(head[:, 2] - (chin + 0.2 * H)) < 0.03 * H]
        temple = head[np.abs(head[:, 2] - (chin + 0.6 * H)) < 0.03 * H]
        if len(jaw) and len(temple):
            out["jaw_width_over_temple_width"] = float(_bbox(jaw)[0] / _bbox(temple)[0])
    # --- mouth parts
    if "teeth_upper" in P and "teeth_lower" in P:
        u, l = P["teeth_upper"], P["teeth_lower"]
        out["teeth_gap_over_head_height"] = float((u[:, 2].min() - l[:, 2].max()) / H)
        out["teeth_width_over_head_width"] = float(max(_bbox(u)[0], _bbox(l)[0]) / (_bbox(body_v[body_v[:, 2] >= chin])[0] if body_v is not None else H))
    if "tongue" in P and "teeth_lower" in P:
        out["tongue_inside_teeth_depth"] = float((P["tongue"][:, 1].min() - P["teeth_lower"][:, 1].min()) / H)
    return out


def findings(m: Dict[str, float], parts: Dict[str, object], label: str) -> List[Finding]:
    out: List[Finding] = []

    def band(region, feature, key, band_key, msg, expected, fix, source):
        if key in m:
            out.append(Finding(f"{region}.{feature}.{key}", BANDS[band_key].grade(m[key]), f"{label}: {msg}", m[key], expected, fix, source))

    def info(region, feature, key, msg):
        if key in m:
            out.append(Finding(f"{region}.{feature}.{key}", INFO, f"{label}: {msg}", m[key]))

    band("eyes", "eyeball", "eyeball_roundness", "eyeball_roundness", "eyeball is a sphere or slight oval (shortest / longest side)", ">= 0.70",
         "Eyeballs should be near-spherical so the iris shader stays round.", "build prompt: eyes are spheres or slight ovals")
    info("eyes", "eyeball", "eyeball_over_head_height", "eyeball size relative to head height")
    band("eyes", "symmetry", "eye_pair_asymmetry_z", "symmetry", "left/right eye height difference (head heights)", "<= 0.02", "Level the eyes.", "heuristic")
    info("eyes", "symmetry", "eye_pair_size_ratio", "smaller eye / larger eye (1 = identical)")
    info("eyes", "symmetry", "head_yaw_degrees", "head turn implied by the eye axis (degrees); mirror checks need a front-facing head")
    if "eye_L" not in parts or "eye_R" not in parts:
        out.append(Finding("eyes.eyeball.parts", SKIP, f"{label}: no separate eyeball objects (CHR_Eye_L / CHR_Eye_R)"))
    band("brows", "bendability", "brow_verts_per_side", "brow_verts_per_side", "vertices per eyebrow (needs enough geometry to bend)", ">= 6",
         "Add loops along the brow so it can bend for expressions.", "build prompt: brows need enough geometry to bend; Hina has 7 per side")
    band("brows", "shape", "brow_asymmetry", "symmetry", "left/right brow height difference (head heights)", "<= 0.02", "Mirror the brows.", "heuristic")
    for key, msg in (("brow_length_over_head_width", "brow length relative to head width"), ("brow_thickness_over_length", "brow thickness relative to length (skill: thin brows)"),
                     ("brow_gap_over_head_height", "gap between brow and eye (head heights; a small gap reads more mature, manual s4)")):
        info("brows", "placement", key, msg)
    if "brows" not in parts:
        out.append(Finding("brows.shape.parts", SKIP, f"{label}: no separate brow object (CHR_Brows)"))
    band("nose", "position", "nose_tip_fraction", "nose_tip_fraction", "nose tip height between chin (0) and eye line (1)", "0.40..0.85",
         "Move the nose tip toward the middle of the eye-to-chin distance.", "manual s8 (halfway) widened to the anime references (0.74-0.77)")
    info("nose", "protrusion", "nose_protrusion_over_head_height", "nose protrusion past the cheek plane (head heights; Stories keeps the nose small)")
    info("mouth", "placement", "mouth_fraction_nose_to_chin", "mouth height between chin (0) and nose tip (1)")
    for key, msg in (("teeth_gap_over_head_height", "gap between upper and lower teeth"), ("teeth_width_over_head_width", "teeth width relative to head width"),
                     ("tongue_inside_teeth_depth", "tongue depth behind the lower teeth")):
        info("mouth", "teeth" if "teeth" in key else "tongue", key, msg)
    for k in ("teeth_upper", "teeth_lower", "tongue"):
        if k not in parts:
            out.append(Finding(f"mouth.{'tongue' if k == 'tongue' else 'teeth'}.parts", SKIP, f"{label}: no {k.replace('_', ' ')} object"))
    info("ears", "size", "ear_height_over_head_height", "ear height relative to head height")
    info("ears", "placement", "ear_centre_vs_eye_line", "ear centre vs the eye line (head heights, + = above)")
    info("jaw", "width", "jaw_width_over_temple_width", "jaw width relative to temple width")
    return out
