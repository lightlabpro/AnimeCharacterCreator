"""Reference profiles: measured metrics from a reference model, compared to a candidate.

A profile is `{"name", "kind", "source", "metrics": {key: value}}`. Build one from any reference
model (a .blend through bpy_adapter, or a glTF export) with `profile_from_scene`, save it under
blender/references/profiles/, and every later validation checks the new character against the
envelope of all profiles for that kind. Reference models must carry LM-* markers or DEF- bones.
"""
from __future__ import annotations

import glob
import json
import os
from statistics import median
from typing import Dict, List

from . import measure
from .model import INFO, PASS, SKIP, WARN, Finding, SceneInfo
from .spec import METRICS


def profile_from_scene(scene: SceneInfo, name: str, source: str = "") -> dict:
    vals, missing, _ = measure.metrics(scene)
    return {"name": name, "kind": scene.kind, "source": source or scene.source,
            "metrics": {k: round(v, 5) for k, v in vals.items()}, "missing": missing}


def save_profile(profile: dict, directory: str) -> str:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{profile['kind']}-{profile['name']}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2)
    return path


def load_profiles(directory: str, kind: str) -> List[dict]:
    out = []
    for p in sorted(glob.glob(os.path.join(directory, "*.json"))):
        try:
            with open(p, "r", encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        if d.get("kind") == kind and isinstance(d.get("metrics"), dict):
            if isinstance(d.get("vetted"), dict):  # keep only what TypeSafe confirmed (see vetting.py)
                d = dict(d, metrics={k: v for k, v in d["metrics"].items() if d["vetted"].get(k, {}).get("kept")})
            out.append(d)
    return out


def compare(candidate: Dict[str, float], profiles: List[dict]) -> List[Finding]:
    """Flag any metric outside [min - tol, max + tol] of the reference envelope."""
    if not profiles:
        return [Finding("reference.none", INFO, "no reference profiles for this body kind; compared with the manual only")]
    out: List[Finding] = []
    for key, v in candidate.items():
        m = METRICS.get(key)
        refs = [(p["name"], p["metrics"][key]) for p in profiles if key in p["metrics"]]
        if not m or not refs:
            continue
        if m.pose_dependent:  # references are in arbitrary poses (Amshani is a T-pose); pose metrics only gate the build
            continue
        lo, hi = min(r[1] for r in refs), max(r[1] for r in refs)
        mid = median(r[1] for r in refs)
        if lo - m.ref_tol <= v <= hi + m.ref_tol:
            out.append(Finding(f"reference.{key}", PASS, f"{m.label} is inside the {len(refs)}-model reference envelope",
                               v, f"{lo:.3f}..{hi:.3f}"))
        else:
            nearest = min(refs, key=lambda r: abs(r[1] - v))
            out.append(Finding(f"reference.{key}", WARN,
                               f"{m.label} is outside the reference envelope (closest: {nearest[0]} = {nearest[1]:.3f}, median {mid:.3f})",
                               v, f"{lo - m.ref_tol:.3f}..{hi + m.ref_tol:.3f}",
                               m.fix_low if v < lo else m.fix_high, f"{len(refs)} reference model(s)"))
    return out
