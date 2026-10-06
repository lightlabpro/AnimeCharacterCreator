"""Validate library/ the way the creator's importer (src/library/importer.ts) will read it."""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List

from .model import FAIL, INFO, PASS, WARN, Finding, Report

LIBRARIES = ("humanoid", "robot", "full_beast")
REQUIRED = ("id", "display_name", "library", "slot")
# Naming rules from the build prompt: assets must not carry game trademarks.
TRADEMARK = re.compile(r"monster.?hunter|mhs3?\b|capcom|rathalos|palico|breath.?of.?fire|mega.?man|rockman", re.I)


def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh), None
    except (OSError, ValueError) as e:
        return None, str(e)


def library_of(path: str) -> str:
    segs = path.replace("\\", "/").split("/")
    for s in reversed(segs):
        if s in LIBRARIES:
            return s
    return ""


def validate_library(root: str, report: Report) -> Dict[str, dict]:
    packs: Dict[str, dict] = {}
    manifest, err = _read_json(os.path.join(root, "manifest.json"))
    if manifest is None:
        report.add(Finding("pack.manifest", WARN, f"manifest.json unreadable: {err}"))
        manifest_ids: Dict[str, dict] = {}
    else:
        manifest_ids = {p.get("id"): p for p in manifest.get("packs", []) if isinstance(p, dict)}

    for dirpath, _dirs, files in os.walk(root):
        if "pack.json" not in files:
            continue
        rel = os.path.relpath(dirpath, root)
        raw, err = _read_json(os.path.join(dirpath, "pack.json"))
        if raw is None:
            report.add(Finding("pack.json", FAIL, f"{rel}: unreadable pack.json ({err})"))
            continue
        pid = raw.get("id", rel)
        packs[pid] = raw
        miss = [k for k in REQUIRED if not raw.get(k)]
        if miss:
            report.add(Finding("pack.fields", FAIL, f"{rel}: missing {', '.join(miss)}"))
        lib = library_of(rel)
        if raw.get("library") and lib and raw["library"] != lib:
            report.add(Finding("pack.library", FAIL, f"{rel}: library '{raw['library']}' but folder is in '{lib}/'",
                               fix="Humanoid, robot and full_beast assets never mix."))
        if raw.get("library") not in LIBRARIES:
            report.add(Finding("pack.library", FAIL, f"{rel}: library must be one of {', '.join(LIBRARIES)}"))
        if manifest is not None:
            m = manifest_ids.get(pid)
            if m is None:
                report.add(Finding("pack.manifest", FAIL, f"{pid}: not listed in manifest.json",
                                   fix="Update library/manifest.json whenever a pack is added."))
            elif m.get("library") and m["library"] != raw.get("library"):
                report.add(Finding("pack.manifest", FAIL, f"{pid}: manifest says {m['library']}, pack.json says {raw.get('library')}"))
        gltfs = [f for f in files if f.lower().endswith((".gltf", ".glb"))]
        blends = [f for f in files if f.lower().endswith(".blend")]
        if not gltfs:
            report.add(Finding("pack.gltf", FAIL, f"{rel}: no glTF export next to the source",
                               fix="Export GLTF_SEPARATE so the app can import without Blender."))
        if not blends:
            report.add(Finding("pack.blend", WARN, f"{rel}: no .blend source in the pack folder"))
        if raw.get("slot") and raw["slot"] not in ("body", "head") and not raw.get("socket"):
            report.add(Finding("pack.socket", WARN, f"{pid}: slot '{raw['slot']}' has no socket"))
        for text in (str(raw.get("id", "")), str(raw.get("display_name", ""))):
            if TRADEMARK.search(text):
                report.add(Finding("pack.names", FAIL, f"{pid}: '{text}' uses a trademarked name",
                                   fix="Asset identity must be original; rename it."))
        report.add(Finding("pack.ok", PASS, f"{pid} ({rel})"))
    for pid in manifest_ids:
        if pid not in packs:
            report.add(Finding("pack.manifest", WARN, f"{pid}: in manifest.json but no pack.json found"))
    report.extra["packs"] = sorted(packs)
    if not packs:
        report.add(Finding("pack.empty", INFO, "no packs yet"))
    return packs
