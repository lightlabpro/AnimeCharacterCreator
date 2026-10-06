"""Measure the creator app's procedural placeholder bodies with the same validators used on Blender assets.

tools/placeholders/export.mjs builds a placeholder in the browser and writes its joints and mesh parts as JSON (Blender axes: Z up, forward -Y).
This module turns that JSON into a SceneInfo with landmarks, so the anatomy, face-feature, hair and region validators run on it unchanged.
The placeholders are replaced by the Blender asset library; this keeps them from looking wrong in the meantime.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import face, hair as hairmod
from .model import SceneInfo

SKIN_REGIONS = ("skull", "jaw", "cheeks", "nose", "ears", "neck")


def _cat(parts: List[dict]) -> Tuple[np.ndarray, list]:
    verts, faces, off = [], [], 0
    for p in parts:
        v = np.asarray(p["verts"], float)
        if not len(v):
            continue
        verts.append(v)
        faces += [tuple(i + off for i in f) for f in p["faces"]]
        off += len(v)
    return (np.vstack(verts) if verts else np.zeros((0, 3))), faces


def load(path: str) -> Tuple[SceneInfo, dict]:
    data = json.load(open(path, encoding="utf-8"))
    kind = {"beast": "dragon"}.get(data["kind"], data["kind"])
    by_region: Dict[str, List[dict]] = {}
    named: Dict[str, List[dict]] = {}
    for name, items in data["parts"].items():
        for it in items:
            by_region.setdefault(it["region"], []).append(it)
            named.setdefault(name, []).append(it)
    sc = SceneInfo(kind=kind, source=path)
    lm: Dict[str, Tuple[float, float, float]] = {}
    J = {k: tuple(v) for k, v in data.get("joints", {}).items()}
    for k in ("shoulder_L", "shoulder_R", "elbow_L", "elbow_R", "wrist_L", "wrist_R", "hip_L", "hip_R", "knee_L", "knee_R", "ankle_L", "ankle_R"):
        if k in J:
            lm[k] = J[k]
    skin = [it for r in SKIN_REGIONS for it in by_region.get(r, [])]
    body_v, body_f = _cat(skin)
    legs_feet = [it for r in ("legs", "feet") for it in by_region.get(r, [])]
    lv, _ = _cat(legs_feet)
    if len(lv):
        lm["Floor"] = (0.0, 0.0, float(lv[:, 2].min()))
    skull = _cat(by_region.get("skull", []))[0]
    jaw = _cat(by_region.get("jaw", []))[0]
    if len(skull):
        lm["Crown"] = (0.0, 0.0, float(skull[:, 2].max()))
        lm["Chin"] = (0.0, 0.0, float(min(skull[:, 2].min(), jaw[:, 2].min() if len(jaw) else 9e9)))
    eyes = {}
    for side in ("L", "R"):
        for it in named.get(f"CHR_Eye_{side}", []):
            v = np.asarray(it["verts"], float)
            eyes[side] = v
            x0, x1 = float(v[:, 0].min()), float(v[:, 0].max())
            inner, outer = (x0, x1) if side == "L" else (x1, x0)
            z = float(v[:, 2].mean())
            y = float(v[:, 1].mean())
            lm[f"EyeInner_{side}"], lm[f"EyeOuter_{side}"] = (inner, y, z), (outer, y, z)
            lm[f"EyeTop_{side}"], lm[f"EyeBottom_{side}"] = ((x0 + x1) / 2, y, float(v[:, 2].max())), ((x0 + x1) / 2, y, float(v[:, 2].min()))
    for it in named.get("CHR_Mouth", []):
        v = np.asarray(it["verts"], float)
        lm["Mouth"] = (float(v[:, 0].mean()), float(v[:, 1].mean()), float(v[:, 2].mean()))
    hips = _cat(by_region.get("hips", []))[0]
    if len(hips):
        lm["Pubis"] = (0.0, 0.0, float(hips[:, 2].min()))
        zh = float((hips[:, 2].min() + hips[:, 2].max()) / 2)
        lm["HipOuter_L"], lm["HipOuter_R"] = (float(hips[:, 0].max()), 0.0, zh), (float(hips[:, 0].min()), 0.0, zh)
    sh = _cat(by_region.get("shoulders", []))[0]
    if len(sh):
        zs = float(J["shoulder_L"][2]) if "shoulder_L" in J else float(sh[:, 2].mean())
        lm["ShoulderOuter_L"], lm["ShoulderOuter_R"] = (float(sh[:, 0].max()), 0.0, zs), (float(sh[:, 0].min()), 0.0, zs)
    fv = _cat(by_region.get("feet", []))[0]
    if len(fv):
        left = fv[fv[:, 0] > 0]
        if len(left):
            fx = float(left[:, 0].mean())
            lm["HeelBack_L"], lm["ToeTip_L"] = (fx, float(left[:, 1].max()), float(left[:, 2].min())), (fx, float(left[:, 1].min()), float(left[:, 2].min()))
    hv_ = _cat(by_region.get("hands", []))[0]
    if len(hv_) and "wrist_L" in lm:
        left = hv_[hv_[:, 0] > 0]
        w = np.array(lm["wrist_L"])
        if len(left):
            lm["HandTip_L"] = tuple(left[np.linalg.norm(left - w, axis=1).argmax()])
    sc.markers = {f"LM-{k}": v for k, v in lm.items()}
    sc.body_verts = [tuple(p) for p in body_v]
    sc.objects = set(data["parts"])
    parts = {}
    for role, aliases in face.PART_ALIASES.items():
        for n in aliases:
            if n in named:
                parts[role] = _cat(named[n])
                break
    sc.parts = parts
    extra = {"body_faces": body_f, "hair": _cat([it for n, its in named.items() if n.startswith("CHR_Hair") for it in its]),
             "units": data.get("units", {}), "archetype": data.get("archetype")}
    return sc, extra
