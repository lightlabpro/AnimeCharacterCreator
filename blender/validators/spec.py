"""Anatomy targets, in one place, with the source of every number.

Every metric is a ratio with a stated denominator, so it survives any body_size.
Bands: `lo..hi` passes, within `slack` of the band warns, beyond that fails.
Numbers come from docs/anatomy-manual.md (sections cited) and from the measured
reference notes in the anime-character-modeling skill (Hina/Amshani, MHS3 frames).
Where those two disagree the band is widened to cover both and the source says so.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .model import FAIL, PASS, WARN


@dataclass(frozen=True)
class Band:
    lo: float
    hi: float
    slack: float

    def grade(self, v: float) -> str:
        if self.lo <= v <= self.hi:
            return PASS
        if self.lo - self.slack <= v <= self.hi + self.slack:
            return WARN
        return FAIL

    def text(self) -> str:
        return f"{self.lo:g}..{self.hi:g} (warn within {self.slack:g})"


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    denominator: str
    bands: Dict[str, Band]
    source: str
    fix_low: str
    fix_high: str
    ref_tol: float  # allowed gap to a reference model's value, in the metric's own units
    pose_dependent: bool = False  # only comparable between models in the same pose (e.g. both A-pose)


def _m(key, label, denom, bands, source, fix_low, fix_high, ref_tol, pose_dependent=False):
    return Metric(key, label, denom, bands, source, fix_low, fix_high, ref_tol, pose_dependent)


METRICS: Dict[str, Metric] = {m.key: m for m in [
    _m("height_heads", "Height in heads", "crown-to-chin head height",
       {"adult": Band(7.0, 7.5, 0.3), "child": Band(5.0, 5.5, 0.3)},
       "manual s2 (adult 7-7.5), s5 (child 5-5.5); MHS3 male 6.7 / female 7.3 incl. hair",
       "Body too short for the head: raise torso_length / leg_length or lower head_scale.",
       "Body too tall for the head: lower leg_length / torso_length or raise head_scale.", 0.35),
    _m("legs_fraction", "Pubis height / total height", "total height",
       {"adult": Band(0.46, 0.52, 0.03), "child": Band(0.38, 0.46, 0.03)},
       "manual s2 (pubis is the midpoint), s5 (child midpoint above hips); MHS3 legs ~48%",
       "Legs too short: raise leg_length / thigh_length / shin_length.",
       "Legs too long: lower leg_length or lengthen torso_length.", 0.03),
    _m("chin_line", "Chin line", "total height from crown",
       {"adult": Band(0.115, 0.15, 0.02)}, "manual s2 table: head line 1 (1/8 = 0.125, 1/7 = 0.143)",
       "Head too small (check head_scale).", "Head too large (check head_scale).", 0.02),
    _m("nipple_line", "Nipple line", "total height from crown",
       {"adult": Band(0.24, 0.30, 0.035)}, "manual s2 table: head line 2",
       "Chest sits too high: lengthen neck_length or lower the shoulders.",
       "Chest sits too low: shorten neck_length / torso_length.", 0.03),
    _m("navel_line", "Navel line", "total height from crown",
       {"adult": Band(0.36, 0.43, 0.04)}, "manual s2 table: head line 3",
       "Navel too high: lengthen torso_length.", "Navel too low: shorten torso_length.", 0.03),
    _m("pubis_line", "Pubis line", "total height from crown",
       {"adult": Band(0.47, 0.54, 0.03)}, "manual s2 table: head line 4, the body midpoint",
       "Crotch too high: lengthen leg_length.", "Crotch too low: shorten leg_length.", 0.03),
    _m("shoulder_width_heads", "Shoulder width", "head height",
       {"adult": Band(1.8, 2.4, 0.2), "child": Band(1.2, 1.8, 0.2)},
       "manual s2 (about 2, Loomis 2 1/3), s5 (child about 1.5)",
       "Shoulders too narrow: raise shoulder_width / ID-BroadShoulders.",
       "Shoulders too wide: lower shoulder_width / ID-BroadShoulders.", 0.2),
    _m("hip_width_heads", "Hip width", "head height",
       {"adult": Band(1.2, 1.8, 0.2), "child": Band(0.9, 1.5, 0.2)},
       "manual s2 (about 1.5); feminine presets run wider (s3)",
       "Hips too narrow: raise hip_width / ID-WideHips.", "Hips too wide: lower hip_width / ID-WideHips.", 0.2),
    _m("wrist_to_crotch_heads", "Hanging wrist vs crotch", "head height, signed (+ = wrist higher); arm length hung straight down from the shoulder, so pose does not matter",
       {"adult": Band(-0.3, 0.3, 0.2), "child": Band(-0.4, 0.4, 0.25)},
       "manual s2: hanging wrists reach the crotch line",
       "Arms too long: lower upper_arm_length / forearm_length.",
       "Arms too short: raise upper_arm_length / forearm_length.", 0.25),
    _m("elbow_to_navel_heads", "Hanging elbow vs navel/waist", "head height, signed (+ = elbow higher); upper-arm length hung straight down",
       {"adult": Band(-0.35, 0.35, 0.2), "child": Band(-0.45, 0.45, 0.25)},
       "manual s2: elbows at the waist and navel",
       "Upper arm too long.", "Upper arm too short.", 0.25),
    _m("thigh_shin_ratio", "Thigh / lower leg", "lower-leg length",
       {"adult": Band(0.85, 1.15, 0.15), "child": Band(0.8, 1.2, 0.2)},
       "manual s2: the thigh roughly equals the lower leg",
       "Thigh too short: raise thigh_length or lower shin_length.", "Thigh too long: lower thigh_length.", 0.15),
    _m("hand_length_heads", "Hand length", "head height",
       {"adult": Band(0.6, 0.85, 0.1), "child": Band(0.5, 0.8, 0.1)},
       "manual s2: hand about as long as the face (chin to hairline, ~3/4 head)",
       "Hands too small: raise hand_length / ID-HandSize.", "Hands too big: lower hand_length / ID-HandSize.", 0.1),
    _m("foot_vs_forearm", "Foot / forearm", "forearm length",
       {"adult": Band(0.85, 1.2, 0.15), "child": Band(0.8, 1.25, 0.2)},
       "manual s2: foot about as long as the forearm",
       "Feet too short: raise foot_length / ID-FootSize.", "Feet too long: lower foot_length / ID-FootSize.", 0.15),
    _m("arm_angle_deg", "A-pose arm angle", "degrees from straight down",
       {"adult": Band(15.0, 50.0, 10.0), "child": Band(15.0, 50.0, 10.0)},
       "build prompt MESH RULES: relaxed A-pose",
       "Arms too close to the body: rotate the arms out toward A-pose.",
       "Arms too raised: lower them toward A-pose.", 12.0, pose_dependent=True),
    # Head and face, normalised by skull height H (chin = 0, crown = 1).
    _m("eye_line_norm", "Eye line", "skull height H, chin = 0",
       {"adult": Band(0.34, 0.52, 0.04), "child": Band(0.28, 0.45, 0.04)},
       "skill (Hina/Amshani eye line ~0.37); manual s8 (realistic midpoint 0.5); manual s5 (child: low eyes)",
       "Eyes too low: raise ID-EyeHeight.", "Eyes too high: lower ID-EyeHeight.", 0.05),
    _m("eye_gap_eye_widths", "Gap between eyes", "single eye width",
       {"adult": Band(0.55, 1.45, 0.15), "child": Band(0.55, 1.6, 0.2)},
       "manual s8 (one eye-width apart), skill (MHS3 ~1.25 widths) and Amshani measured 0.66 (anime eyes sit close); band covers all",
       "Eyes too close: raise ID-EyeSpacing.", "Eyes too far apart: lower ID-EyeSpacing.", 0.15),
    _m("eye_height_width", "Eye height / width", "eye width",
       {"adult": Band(0.50, 0.80, 0.07), "child": Band(0.55, 0.95, 0.1)},
       "skill (~0.56, MHS3 ~0.62) and Amshani measured 0.73 (taller anime eyes); child eyes are rounder (manual s5)",
       "Eyes too narrow: raise ID-EyeSize / ID-EyeRound.", "Eyes too tall: lower ID-EyeSize.", 0.07),
    _m("mouth_norm", "Mouth height", "skull height H, chin = 0",
       {"adult": Band(0.10, 0.25, 0.05), "child": Band(0.08, 0.25, 0.05)},
       "skill (MHS3: mouth close to the chin); manual s8 (mouth close under the nose)",
       "Mouth too low: raise ID-MouthHeight.", "Mouth too high: lower ID-MouthHeight.", 0.05),
    _m("temple_width_norm", "Head width at the temples", "skull height H",
       {"adult": Band(0.76, 0.95, 0.06), "child": Band(0.76, 1.0, 0.06)},
       "skill (measured on Hina/Amshani: ~0.80 H, pass >= 0.76 H); child cranium is large (manual s5)",
       "Head too narrow: raise ID-FaceRound / ID-Cheekbone.", "Head too wide: lower ID-FaceRound.", 0.06),
    _m("neck_head_width", "Neck width / head width", "head width at the temples",
       {"adult": Band(0.30, 0.45, 0.05), "child": Band(0.25, 0.42, 0.05)},
       "skill (refs 0.37-0.41, pass <= 0.45); manual s5 (thin child neck)",
       "Neck too thin: raise ID-NeckThickness.", "Neck too thick: lower ID-NeckThickness.", 0.05),
    _m("forehead_slope", "Forehead lean", "skull height H (front-surface offset, eye line to 0.8 H)",
       {"adult": Band(0.0, 0.03, 0.03), "child": Band(0.0, 0.04, 0.03)},
       "skill: forehead vertical within 0.03 H; a receding forehead reads amateur",
       "", "Forehead recedes: pull the brow plane forward (ID-BrowRidge) or flatten the face plane.", 0.03),
    # Dragon
    _m("shoulder_height_m", "Dragon shoulder height", "metres at body_size 1",
       {"dragon": Band(1.6, 2.2, 0.2)}, "build prompt DRAGON SPECIES: default shoulder height 1.6-2.2 m",
       "Raise body_size or leg_length.", "Lower body_size or leg_length.", 0.2),
]}

# Required objects per kind (build prompt NAMING). Robot/dragon bodies use their own names.
BODY_OBJECTS = {
    "adult": ("CHR_Armature", "CHR_Body"),
    "child": ("CHR_Armature_Child", "CHR_Body_Child"),
    "robot": ("CHR_Armature_Robot", "CHR_Body_Robot"),
    "dragon": ("CHR_Armature_Dragon", "CHR_Body_Dragon"),
}

# Poly budgets in triangles (build prompt MESH RULES and species sections).
TRI_BUDGET = {"adult": (18_000, 28_000), "child": (14_000, 22_000), "robot": (20_000, 35_000), "dragon": (30_000, 45_000)}


def band_for(metric: Metric, kind: str) -> Optional[Band]:
    return metric.bands.get(kind)


def bucket(key: str, value: float, kind: str) -> str:
    """Named bucket for a metric. Jev reads words better than numbers (docs: 'Jev is not a calculator'), so
    the judge and vetting steps send these labels; the numeric grade stays in the deterministic checks."""
    m = METRICS.get(key)
    band = m.bands.get(kind) if m else None
    if band is None:
        return "unknown"
    width = max(band.hi - band.lo, band.slack, 1e-9)
    if value < band.lo - band.slack:
        return "far too low"
    if value < band.lo:
        return "slightly low"
    if value <= band.hi:
        return "in range"
    if value <= band.hi + band.slack:
        return "slightly high"
    return "far too high"
