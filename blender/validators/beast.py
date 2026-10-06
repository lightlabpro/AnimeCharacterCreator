"""Humanoid-beast trait validators: muzzle, digitigrade legs, tail, wings, horns, plus the archetype recipes.

Numbers come from docs/anatomy-manual.md section 10 where it gives one (mouth corner two-thirds of the way toward the eye, a raised
heel on a digitigrade leg, tail at the sacrum) and from the library prompt's archetype recipes. Everything else is reported
without a band and read by the TypeSafe region judge. All inputs are plain arrays so they can come from Blender or glTF.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import geometry
from .model import FAIL, INFO, PASS, SKIP, WARN, Finding
from .spec import Band

# Recipes from docs/CLAUDE_BUILD_PROMPT.md and docs/CHARACTER_MAKER.md: look slots each archetype is built from.
RECIPES: Dict[str, Dict[str, str]] = {
    "rabbit": {"ears": "long", "muzzle": "lagomorph", "tail": "puff"},
    "dinosaur": {"muzzle": "reptile", "mane": "crest", "surface": "scales", "tail": "lizard", "legs": "digitigrade",
                 "extra": "a thick heavy tail that counterbalances the body, short arms"},
    "rhino": {"muzzle": "heavy", "horns": "nose", "surface": "thickHide", "extra": "pillar legs"},
    "lizard": {"muzzle": "reptile", "surface": "scales", "tail": "lizard", "extra": "sprawling legs, optional neck frill"},
    "tiger": {"muzzle": "feline", "tail": "feline", "surface": "shortFur", "pattern": "stripes"},
    "lion": {"muzzle": "feline", "mane": "mane", "tail": "feline", "surface": "shortFur"},
    "dog": {"muzzle": "canine", "tail": "canine", "surface": "shortFur"},
    "bird": {"muzzle": "bird", "wings": "feathered", "surface": "feathers"},
    "fish": {"muzzle": "fish", "tail": "fish", "surface": "scales"},
    "frog": {"muzzle": "frog", "surface": "amphibian"},
    "serpent": {"tail": "serpent", "surface": "scales"},
    "dragon": {"muzzle": "reptile", "horns": "curved", "wings": "membrane", "surface": "scales", "tail": "lizard"},
}

BANDS = {
    "mouth_corner_reach": Band(0.55, 0.80, 0.12),   # manual s10: about two-thirds of the way toward the eye
    "plantigrade_heel": Band(0.0, 0.12, 0.08),       # manual s10: plantigrade = whole sole on the ground
    "digitigrade_heel": Band(0.25, 1.5, 0.1),        # manual s10: digitigrade = heel permanently raised (heuristic cut-off)
    "tail_root_height": Band(-0.05, 0.30, 0.1),      # manual s10: tail continues the spine at the coccyx (pubis to just above)
    "taper": Band(0.85, 1.0, 0.1),                   # heuristic: neck and tail narrow smoothly (manual s11)
    "symmetry": Band(0.0, 0.015, 0.02),              # heuristic: paired horns / ears mirror within 1.5% of the head height
    "base_on_skull": Band(0.0, 0.03, 0.04),          # heuristic: horns grow from the skull surface
}


def mouth_corner_reach(nose_tip: Sequence[float], mouth_corner: Sequence[float], eye: Sequence[float]) -> float:
    """Side-view distance from the muzzle tip to the mouth corner, over the distance from the tip to the eye (manual: ~2/3)."""
    t, c, e = np.array(nose_tip), np.array(mouth_corner), np.array(eye)
    ax = e - t
    return float(np.dot(c - t, ax) / np.dot(ax, ax))


def heel_ratio(heel_back: Sequence[float], toe_tip: Sequence[float], floor_z: float) -> float:
    foot = float(np.linalg.norm(np.array(toe_tip) - np.array(heel_back)))
    return float((heel_back[2] - floor_z) / foot) if foot > 0 else 0.0


def radius_profile(v: np.ndarray, root: Sequence[float], tip: Sequence[float], slices: int = 12) -> np.ndarray:
    """Cross-section radius of a tail/neck/horn along its axis (root to tip)."""
    ax = np.array(tip) - np.array(root)
    L = np.linalg.norm(ax)
    ax = ax / (L or 1)
    t = (v - np.array(root)) @ ax / (L or 1)
    side = np.linalg.norm((v - np.array(root)) - np.outer((v - np.array(root)) @ ax, ax), axis=1)
    out = []
    for k in range(slices):
        m = (t >= k / slices) & (t < (k + 1) / slices)
        out.append(float(side[m].max()) if m.any() else np.nan)
    return np.array(out)


def taper_score(profile: np.ndarray) -> float:
    """Share of consecutive slices whose radius does not grow by more than 15% (1.0 = smooth taper)."""
    p = profile[~np.isnan(profile)]
    if len(p) < 3:
        return 0.0
    return float(np.mean(p[1:] <= p[:-1] * 1.15))


def pair_symmetry(left: np.ndarray, right: np.ndarray, head_h: float, mid_x: float = 0.0) -> float:
    """Chamfer distance (in head heights) between one side and the mirror of the other about x = mid_x. 0 = mirrored."""
    mirrored = right.copy()
    mirrored[:, 0] = 2 * mid_x - mirrored[:, 0]
    return float(geometry.chamfer_f1(left / head_h, mirrored / head_h, ())["cd"])


def base_on_skull(horn: np.ndarray, skull: np.ndarray, head_h: float) -> float:
    base = horn[horn[:, 2] <= np.percentile(horn[:, 2], 10)]
    d = np.sqrt(((base[:, None, :] - skull[None, ::max(1, len(skull) // 3000), :]) ** 2).sum(-1)).min(axis=1)
    return float(np.median(d) / head_h)


def findings(m: Dict[str, float], label: str, stance: str = "plantigrade") -> List[Finding]:
    out: List[Finding] = []
    def g(region, feature, key, band, msg, expected, fix, source):
        if key in m:
            out.append(Finding(f"{region}.{feature}.{key}", band.grade(m[key]), f"{label}: {msg}", m[key], expected, fix, source))
    g("muzzle", "mouth_corner", "mouth_corner_reach", BANDS["mouth_corner_reach"], "mouth corner reaches this fraction of the way from the muzzle tip to the eye", "0.55..0.80",
      "Lengthen or shorten the mouth line toward two-thirds of the way to the eye.", "manual s10")
    if "heel_ratio" in m:
        band = BANDS["digitigrade_heel" if stance == "digitigrade" else "plantigrade_heel"]
        g("feet", "stance", "heel_ratio", band, f"heel height over foot length ({stance})", band.text(),
          "Raise the heel for a digitigrade leg." if stance == "digitigrade" else "Lower the heel for a plantigrade foot.", "manual s10")
    g("tail", "root", "tail_root_height", BANDS["tail_root_height"], "tail root height above the pubis (head heights)", "-0.05..0.30", "Root the tail at the sacrum.", "manual s10")
    g("tail", "taper", "tail_taper", BANDS["taper"], "share of tail slices that narrow smoothly", ">= 0.85", "Taper the tail without bulges.", "manual s11 (heuristic)")
    g("horns", "symmetry", "horn_symmetry", BANDS["symmetry"], "left/right horn mirror error (head heights)", "<= 0.015", "Mirror the horns.", "heuristic")
    g("horns", "base", "horn_base_gap", BANDS["base_on_skull"], "horn base distance from the skull surface (head heights)", "<= 0.03", "Seat the horn base on the skull.", "heuristic")
    for key, region, feat, msg in (("tail_length_over_height", "tail", "length", "tail length relative to body height"), ("wing_span_over_height", "wings", "span", "wing span relative to body height"),
                                   ("muzzle_length_over_head_height", "muzzle", "proportion", "muzzle length relative to head height")):
        if key in m:
            out.append(Finding(f"{region}.{feat}.{key}", INFO, f"{label}: {msg}", m[key]))
    return out


def recipe_findings(archetype: str, looks: Dict[str, str]) -> List[Finding]:
    """Does the equipped element set contain the archetype's recipe? (docs/CHARACTER_MAKER.md recipes)"""
    rec = RECIPES.get(archetype)
    if rec is None:
        return [Finding("archetype.recipe.known", SKIP, f"no recipe recorded for '{archetype}'")]
    miss = {k: v for k, v in rec.items() if k != "extra" and looks.get(k) != v}
    return [Finding("archetype.recipe.elements", FAIL if miss else PASS,
                    f"{archetype}: element recipe " + ("complete" if not miss else "differs: " + ", ".join(f"{k} should be {v} (is {looks.get(k, 'unset')})" for k, v in miss.items())),
                    fix="Set the missing element looks; a preset must still leave every slot editable.")]
