"""Slider sweeps: the contract says every key and length must work at 0, 0.5 and 1 without breaking.

`check` is pure (it takes already-measured metrics). The bpy driver that produces the metrics lives in
bpy_adapter.sweep. Wrist/crotch and landmark rules are relaxed 1.5x at the extremes of a control;
a control that is explicitly an arm-length slider is exempt from the wrist rule (manual s2).
"""
from __future__ import annotations

from typing import Dict, List

from .model import FAIL, PASS, WARN, Finding
from .spec import Band, METRICS

SWEEP_METRICS = ("height_heads", "legs_fraction", "wrist_to_crotch_heads", "shoulder_width_heads", "hip_width_heads",
                 "thigh_shin_ratio")
ARM_CONTROLS = ("upper_arm_length", "forearm_length", "hand_length", "ID-UpperArmBulk", "ID-ForeArmBulk")
RELAX = 1.5


def check(kind: str, results: Dict[str, Dict[float, Dict[str, float]]]) -> List[Finding]:
    """results[control][value] = metrics measured with only that control set to value."""
    out: List[Finding] = []
    for control, by_value in results.items():
        bad: List[str] = []
        worst = PASS
        for value, vals in sorted(by_value.items()):
            for key in SWEEP_METRICS:
                m = METRICS[key]
                band = m.bands.get(kind)
                if band is None or key not in vals:
                    continue
                if key == "wrist_to_crotch_heads" and control in ARM_CONTROLS:
                    continue
                wide = Band(band.lo - band.slack * (RELAX - 1), band.hi + band.slack * (RELAX - 1), band.slack * RELAX)
                sev = wide.grade(vals[key])
                if sev != PASS:
                    bad.append(f"{key}={vals[key]:.2f}@{value:g}")
                    worst = FAIL if (sev == FAIL or worst == FAIL) else WARN
        out.append(Finding(f"sweep.{control}", worst,
                           "stays inside the relaxed bands at 0, 0.5 and 1" if not bad else "leaves the bands: " + ", ".join(bad[:4]),
                           fix="Add or retune the corrective key / bone scaling for this control."))
    return out
