"""What the creator app actually drives, read from its source, compared with what a Blender model provides.

The app's built-in bodies are placeholders that the Blender asset library replaces, so the library has to supply every shape key,
bone property, shader parameter and performance key the app's controls are wired to. src/model/controls.ts, src/model/performance.ts
and src/model/looks.ts are the source of truth for that; docs/CLAUDE_BUILD_PROMPT.md is a (shorter) description of it. This module
reads the app source, so the check follows the app when controls change.

Per body kind ('adult', 'child', 'robot', 'beast'; the library's quadruped dragon is 'beast') it returns the morph keys (positive and
the `_Neg` direction of bidirectional sliders), bone length properties, shader parameters and performance keys, each with the region
of the control it belongs to, so coverage can be reported per region.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from . import contract, regions, standard_mapper as sm, judge
from .model import FAIL, INFO, PASS, SKIP, WARN, Finding

HERE = os.path.dirname(os.path.abspath(__file__))
APP_SRC = os.path.normpath(os.path.join(HERE, "..", "..", "src", "model"))
_BODY_CONST = {"HUM": ["adult", "child"], "ADULT": ["adult"], "ALL_HUMANLIKE": ["adult", "child", "robot"]}
KIND_TO_APP = {"adult": "adult", "child": "child", "robot": "robot", "dragon": "beast", "beast": "beast"}


@dataclass
class Control:
    id: str
    region: str
    bodies: List[str]
    morph: Optional[str] = None
    morph_neg: Optional[str] = None
    bone: Optional[str] = None
    shader: Optional[str] = None


def _options_object(line: str) -> str:
    """The last argument of c(...): the {...} object at call depth 1 (nested {...} such as pathFor or needsLook stay inside it)."""
    depth, brace, start, quote = 0, 0, None, None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote and line[i - 1] != "\\":
                quote = None
            continue
        if ch in "'\"":
            quote = ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "{":
            if depth == 1 and brace == 0:
                start = i
            brace += 1
        elif ch == "}":
            brace -= 1
            if brace == 0 and start is not None:
                return line[start:i + 1]
    return ""


def parse_controls(path: Optional[str] = None) -> List[Control]:
    path = path or os.path.join(APP_SRC, "controls.ts")
    out: List[Control] = []
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\s*c\('([^']+)'", line)
        if not m:
            continue
        opts = _options_object(line)
        g = lambda k: (re.search(rf"\b{k}: '([^']+)'", opts) or [None, None])[1]
        b = re.search(r"bodies: (\[[^\]]*\]|[A-Z_]+)", opts)
        if b and b.group(1).startswith("["):
            bodies = re.findall(r"'(\w+)'", b.group(1))
        else:
            bodies = _BODY_CONST.get(b.group(1), ["adult", "child"]) if b else ["adult", "child"]
        bone = re.search(r"bone: \['([^']+)'", opts)
        out.append(Control(m.group(1), g("region") or "body", bodies, g("morph"), g("morphNeg"), bone.group(1) if bone else None, g("shader")))
    return out


def parse_pf_keys(path: Optional[str] = None) -> List[str]:
    """Performance keys, with the Left/Right pairs the `sides()` helper expands."""
    path = path or os.path.join(APP_SRC, "performance.ts")
    src = open(path, encoding="utf-8").read()
    keys = [f"{b}_{s}" for b in re.findall(r"\.\.\.sides\('([^']+)'", src) for s in ("L", "R")]
    keys += re.findall(r"key: '(PF-[A-Za-z_]+)'", src)
    return sorted(set(keys))


def required(kind: str, controls: Optional[List[Control]] = None) -> Dict[str, Dict[str, str]]:
    """{'morph': {key: region}, 'bone': {prop: region}, 'shader': {param: region}} for a library body kind."""
    app = KIND_TO_APP[kind]
    out: Dict[str, Dict[str, str]] = {"morph": {}, "bone": {}, "shader": {}}
    for c in controls or parse_controls():
        if app not in c.bodies:
            continue
        for k in (c.morph, c.morph_neg):
            if k:
                out["morph"][k] = c.region
        if c.bone:
            out["bone"][c.bone] = c.region
        if c.shader:
            out["shader"][c.shader] = c.region
    return out


def contract_gap(controls: Optional[List[Control]] = None) -> Dict[str, object]:
    """Keys the app drives that the build prompt's key list does not name, and the reverse."""
    controls = controls or parse_controls()
    app_morphs = {c.morph for c in controls if c.morph} | {c.morph_neg for c in controls if c.morph_neg}
    prompt = set(contract.ADULT_BODY_KEYS) | set(contract.ADULT_FACE_KEYS)
    missing = sorted(app_morphs - prompt)
    neg = [k for k in missing if k.endswith("_Neg") and k[:-4] in app_morphs]
    other = [k for k in missing if k not in neg]
    return {"app_morphs": len(app_morphs), "app_not_in_prompt": missing, "neg_counterparts": neg, "named_nowhere_in_prompt": other,
            "prompt_not_in_app": sorted(k for k in prompt if k not in app_morphs and k.startswith("ID-"))}


def coverage(model_keys: Iterable[str], model_props: Iterable[str], kind: str, controls: Optional[List[Control]] = None) -> Dict[str, Dict[str, Tuple[int, int, List[str]]]]:
    """Per region: how many of the app's morphs / bone props / shader params the model provides. Returns
    {region: {'morph': (have, total, missing), 'bone': ..., 'shader': ...}}."""
    req = required(kind, controls)
    keys, props = set(model_keys), set(model_props)
    out: Dict[str, Dict[str, Tuple[int, int, List[str]]]] = {}
    for what, have in (("morph", keys), ("bone", props), ("shader", props)):
        per: Dict[str, List[str]] = {}
        for name, region in req[what].items():
            per.setdefault(region, []).append(name)
        for region, names in per.items():
            miss = sorted(n for n in names if n not in have)
            out.setdefault(region, {})[what] = (len(names) - len(miss), len(names), miss)
    return out


def findings(model_keys: Iterable[str], model_props: Iterable[str], kind: str, label: str, controls: Optional[List[Control]] = None) -> List[Finding]:
    out: List[Finding] = []
    cov = coverage(model_keys, model_props, kind, controls)
    for region, parts in sorted(cov.items()):
        for what, (have, total, miss) in parts.items():
            frac = have / total
            reg = region if region in regions.REGIONS else "body"
            out.append(Finding(f"{reg}.app.{what}", PASS if frac == 1 else WARN if frac >= 0.5 else FAIL,
                               f"{label}: {have}/{total} of the app's {what} controls for '{region}' exist in the model" + (f"; missing {', '.join(miss[:6])}{'...' if len(miss) > 6 else ''}" if miss else ""),
                               frac, "1.00", "The app's slider is dead until the model provides it.", "src/model/controls.ts"))
    pf = parse_pf_keys()
    have_pf = {k for k in model_keys if k.startswith("PF-")}
    if kind in ("adult", "child") and pf:
        miss = [k for k in pf if k not in have_pf]
        out.append(Finding("face.app.performance", PASS if not miss else WARN if len(miss) <= len(pf) // 2 else FAIL,
                           f"{label}: {len(pf) - len(miss)}/{len(pf)} of the app's performance keys exist" + (f"; missing {', '.join(miss[:6])}{'...' if len(miss) > 6 else ''}" if miss else ""),
                           1 - len(miss) / len(pf), "1.00", "Add the PF- keys the play bar drives.", "src/model/performance.ts"))
    return out


def suggest_renames(model_keys: Sequence[str], missing: Dict[str, str], transport: Callable[[dict], dict] = judge.http_transport) -> sm.Mapping:
    """Model keys the app does not use, matched to app keys the model lacks (same control, different name). TypeSafe picks
    from the missing app keys of one region at a time; only an answer that holds in both option orders is returned."""
    by_region: Dict[str, Dict[str, str]] = {}
    for key, region in missing.items():
        by_region.setdefault(region, {})[key] = sm._words(key.replace("ID-", "").replace("_Neg", " negative direction"))
    extras = [k for k in model_keys if k.startswith("ID-") and k not in missing and k not in {m for m in missing}]
    return sm.map_to_options(extras, by_region, "shape key of the app's control list", transport,
                             context="Shape keys of a 3D character library. Match a key to the app control it is probably meant to drive.") if by_region and extras else {}


def markdown() -> str:
    """A readable list of what the app drives, per body kind and region, and where it differs from the build prompt."""
    cs = parse_controls()
    gap = contract_gap(cs)
    lines = ["# App contract (generated)", "",
             "Generated by `python -m blender.validators app-contract --write docs/APP_CONTRACT.md` from `src/model/controls.ts` and "
             "`src/model/performance.ts`. The app's built-in bodies are placeholders; the Blender library must provide everything below "
             "or the matching slider does nothing. A slider from -100 to 100 drives `<key>` for positive values and `<key>_Neg` for negative "
             "ones (src/viewport/gltfPacks.ts); without the `_Neg` key the negative half is ignored.", ""]
    for kind in ("adult", "child", "robot", "dragon"):
        r = required(kind, cs)
        lines += [f"## {kind}", f"{len(r['morph'])} shape keys, {len(r['bone'])} bone length properties, {len(r['shader'])} shader parameters.", ""]
        per: Dict[str, List[str]] = {}
        for k, region in r["morph"].items():
            per.setdefault(region, []).append(k)
        for region in sorted(per):
            lines.append(f"- **{region}**: " + ", ".join(sorted(per[region])))
        lines += ["", f"Bone properties: {', '.join(sorted(r['bone']))}", f"Shader parameters: {', '.join(sorted(r['shader']))}", ""]
    lines += ["## Differences from docs/CLAUDE_BUILD_PROMPT.md", "",
              f"The app drives {gap['app_morphs']} shape-key names. {len(gap['app_not_in_prompt'])} are not in the prompt's key list: "
              f"{len(gap['neg_counterparts'])} are the `_Neg` direction of a listed or unlisted key, {len(gap['named_nowhere_in_prompt'])} are not named at all.", "",
              "Not named in the prompt: " + ", ".join(gap["named_nowhere_in_prompt"]), "",
              "In the prompt but not driven by the app: " + (", ".join(gap["prompt_not_in_app"]) or "none"), "",
              "Performance keys the app drives: " + ", ".join(parse_pf_keys()), ""]
    return "\n".join(lines)
