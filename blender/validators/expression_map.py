"""Which standard expressions does a model's shape-key set cover, per face region?

Standards: VRM preset expressions, ARKit 52 blendshapes (see standards.py). Names the project defines
(PF-*), common avatar names (VRChat visemes) and exact standard names are matched in code; anything left goes to
TypeSafe (standard_mapper). Coverage is then counted per region against the standard set, so the report can say
"brows: 3/5 ARKit shapes, eyes: 8/14" instead of one number for the whole face.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from . import judge, standard_mapper as sm, standards as st
from .model import INFO, PASS, SKIP, WARN, FAIL, Finding

_SIDE = [(r"[._ -]l$|_l_|\.l\b|^l[._ -]|left", "Left"), (r"[._ -]r$|_r_|\.r\b|^r[._ -]|right", "Right")]


def normalise(name: str) -> str:
    n = re.sub(r"^(pf|id)[-_]", "", name, flags=re.I)
    return re.sub(r"[^a-z0-9]", "", n.lower())


def _standard_index() -> Dict[str, str]:
    return {normalise(n): n for n in st.all_standard_names()}


def deterministic(name: str) -> Optional[str]:
    if name in st.PROJECT_TO_STANDARD:
        return st.PROJECT_TO_STANDARD[name]
    if name in st.VRCHAT_VISEMES:
        return st.VRCHAT_VISEMES[name]
    idx = _standard_index()
    n = normalise(name)
    if n in idx:
        return idx[n]
    # side-suffixed project names: "PF-BrowInnerUp_L" -> browInnerUp (+ side handled by region only)
    base = re.sub(r"(left|right|l|r)$", "", n)
    if base and base in idx:
        return idx[base]
    return None


def oculus_viseme(name: str) -> Optional[str]:
    if name in st.PROJECT_TO_OCULUS:
        return st.PROJECT_TO_OCULUS[name]
    m = re.fullmatch(r"vrc\.v_(\w+)", name)
    if m:
        for v in st.OCULUS_VISEMES:
            if v.lower() == m.group(1).lower():
                return v
    if name in st.OCULUS_VISEMES:
        return name
    return None


def _region_options() -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for region, names in st.ARKIT_52.items():
        out[region] = {n: st._words(n) if hasattr(st, "_words") else sm._words(n) for n in names}
    for n in st.VRM_EXPRESSIONS["mouth"]:
        out["mouth"][n] = f"vowel viseme '{n}'"
    out["eyes"].update({n: n for n in ("blink", "blinkLeft", "blinkRight", "lookUp", "lookDown", "lookLeft", "lookRight")})
    out["face"] = {n: f"emotion '{n}'" for n in st.VRM_EXPRESSIONS["face"]}
    return out


def map_keys(keys: Iterable[str], transport: Optional[Callable[[dict], dict]] = None) -> sm.Mapping:
    """Deterministic first, TypeSafe for the rest. transport=None skips TypeSafe."""
    out: sm.Mapping = {}
    left: List[str] = []
    for k in keys:
        if k == "Basis":
            continue
        std = deterministic(k)
        ov = oculus_viseme(k)
        if std:
            out[k] = (std, "rule", 1.0)
        elif ov:
            out[k] = (f"oculus:{ov}", "rule", 1.0)
        else:
            left.append(k)
    if left and transport is not None:
        out.update(sm.map_to_options(left, _region_options(), "facial shape key", transport))
    else:
        out.update({k: (None, "unmapped", 0.0) for k in left})
    return out


def coverage(mapping: sm.Mapping) -> Dict[str, Tuple[int, int]]:
    """Per face region: (standard shapes covered, standard shapes in the set), counting Left/Right as separate shapes."""
    have = {m[0] for m in mapping.values() if m[0]}
    # a side-less project key covers both sides of its ARKit pair
    expanded = set(have)
    for h in have:
        if h.endswith("Left") or h.endswith("Right"):
            pass
    out = {}
    for region, names in st.ARKIT_52.items():
        got = sum(1 for n in names if n in expanded or (n[:-4] in expanded if n.endswith("Left") else n[:-5] in expanded if n.endswith("Right") else False))
        out[region] = (got, len(names))
    out["visemes (Oculus 15)"] = (len({oculus_viseme(k) for k in mapping} - {None}), len(st.OCULUS_VISEMES))
    vrm = st.VRM_EXPRESSIONS
    out["visemes (VRM aa ih ou ee oh)"] = (sum(1 for n in vrm["mouth"] if n in expanded), len(vrm["mouth"]))
    out["emotions (VRM)"] = (sum(1 for n in vrm["face"] if n in expanded), len(vrm["face"]))
    return out


def findings(mapping: sm.Mapping, label: str) -> List[Finding]:
    cov = coverage(mapping)
    out = []
    for region, (got, total) in cov.items():
        r = region.split()[0]
        frac = got / total
        out.append(Finding(f"{ {'visemes': 'mouth', 'emotions': 'face'}.get(r, r) }.performance.{region.split()[0]}", PASS if frac >= 0.8 else WARN if frac >= 0.4 else INFO,
                           f"{label}: {region} covers {got} of {total} standard expression shapes", frac, ">= 0.80",
                           "Add the missing shapes or map existing ones (see the unmapped list)."))
    unmapped = sorted(k for k, m in mapping.items() if m[0] is None and m[1] == "unmapped")
    if unmapped:
        out.append(Finding("face.performance.unmapped", INFO, f"{label}: {len(unmapped)} shape keys could not be matched to a standard shape: {', '.join(unmapped[:8])}"))
    return out
