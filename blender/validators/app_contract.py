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
    bone_range: Optional[Tuple[float, float]] = None
    label: str = ""
    hint: str = ""
    group: str = ""            # the app's menu path, e.g. "Head > Eyes" (Elements, Age, Chassis...)
    bidirectional: bool = False
    needs_look: Optional[str] = None
    tab: str = "morphs"
    child_limit: Optional[int] = None


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


def _menu_paths(src: str) -> Dict[str, str]:
    """const FACE = ['Head', 'Face shape']  ->  {'FACE': 'Head > Face shape'}; EL('x') and MAT('x') become 'Elements > x' and 'Material > x'."""
    return {m.group(1): " > ".join(re.findall(r"'([^']+)'", m.group(2))) for m in re.finditer(r"^const ([A-Z_]+) = \[([^\]]*)\];", src, flags=re.M)}


def _menu_label(token: str, paths: Dict[str, str]) -> str:
    m = re.match(r"(EL|MAT)\('([^']+)'\)", token)
    if m:
        return ("Elements" if m.group(1) == "EL" else "Material") + " > " + m.group(2)
    return paths.get(token, token)


def parse_controls(path: Optional[str] = None) -> List[Control]:
    path = path or os.path.join(APP_SRC, "controls.ts")
    paths = _menu_paths(open(path, encoding="utf-8").read())
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
        bone = re.search(r"bone: \['([^']+)',\s*([\d.]+),\s*([\d.]+)\]", opts)
        strings = re.findall(r"'((?:[^'\\]|\\.)*)'", line[:line.find(opts)] if opts else line)
        label, hint = (strings[1], strings[2]) if len(strings) >= 3 else ("", "")
        grp = re.search(r",\s*((?:EL|MAT)\('[^']+'\)|[A-Z_]+)\s*,\s*\{", line)
        needs = re.search(r"needsLook: (?:notNone\('(\w+)'\)|\{ slot: '(\w+)')", opts)
        out.append(Control(m.group(1), g("region") or "body", bodies, g("morph"), g("morphNeg"), bone.group(1) if bone else None, g("shader"),
                           (float(bone.group(2)), float(bone.group(3))) if bone else None, label, hint, _menu_label(grp.group(1), paths) if grp else "",
                           "bi: true" in opts, (needs.group(1) or needs.group(2)) if needs else None, g("tab") or "morphs",
                           int(cl.group(1)) if (cl := re.search(r"childLimit: (\d+)", opts)) else None))
    return out


def _directions(hint: str) -> Tuple[Optional[str], Optional[str]]:
    """(negative-direction phrase, positive-direction phrase) from hints such as 'Droop to the left, upturn to the right.'"""
    left = right = None
    for seg in re.split(r",\s*|;\s*", hint.rstrip(".")):
        m = re.match(r"(.+?)\s+to the (left|right)$", seg.strip(), flags=re.I)
        if m:
            if m.group(2).lower() == "left":
                left = m.group(1).strip().lower()
            else:
                right = m.group(1).strip().lower()
    m = re.match(r"(.+?) to the (left|right), (.+?) to the (left|right)$", hint.rstrip("."), flags=re.I)
    return left, right


def describe(c: "Control", key: str) -> str:
    """One line saying what this single key does, for the contract documents (and checked by TypeSafe in the build step)."""
    neg, pos = _directions(c.hint)
    is_neg = key == c.morph_neg
    if c.morph_neg and neg and pos:
        return f"{c.label}: {neg if is_neg else pos}" + (f" (the other direction of {c.morph})" if is_neg else "")
    base = re.sub(r"\s+to the (left|right)$", "", c.hint.rstrip("."), flags=re.I)
    if c.morph_neg:
        return f"{c.label}, opposite direction of {c.morph}: {base}" if is_neg else f"{c.label}: {base}"
    return f"{c.label}: {base}"


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
            if k and not (kind == "child" and k in contract.CHILD_FORBIDDEN):  # the child restriction in the prompt wins over the app
                out["morph"][k] = c.region
        if c.bone:
            out["bone"][c.bone] = c.region
        if c.shader:
            out["shader"][c.shader] = c.region
    return out


def child_conflicts(controls: Optional[List[Control]] = None) -> List[Tuple[str, str]]:
    """App controls that reach the child body with a key the build prompt forbids on the child. (key, control id)."""
    out = []
    for c in controls or parse_controls():
        if "child" in c.bodies:
            for k in (c.morph, c.morph_neg):
                if k in contract.CHILD_FORBIDDEN:
                    out.append((k, c.id))
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
             "Generated by `python -m blender.validators app-contract --write <file>` from `src/model/controls.ts` and "
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


# ---- generators for docs/CLAUDE_BUILD_PROMPT.md and docs/ASSET_CONTRACT.md -----------------------------------------------------------

def parse_pf_defs(path: Optional[str] = None) -> List[Dict[str, str]]:
    """Performance keys with group, region and label, in app order (sides() pairs expanded)."""
    path = path or os.path.join(APP_SRC, "performance.ts")
    src = open(path, encoding="utf-8").read()
    out: List[Dict[str, str]] = []
    for m in re.finditer(r"\.\.\.sides\('([^']+)', '([^']+)', '(\w+)', '(\w+)'\)|\{ key: '(PF-[A-Za-z_]+)', label: '([^']+)', group: '(\w+)', region: '(\w+)' \}", src):
        if m.group(1):
            for side, word in (("L", "left"), ("R", "right")):
                out.append({"key": f"{m.group(1)}_{side}", "label": f"{m.group(2)} {word}", "group": m.group(3), "region": m.group(4)})
        else:
            out.append({"key": m.group(5), "label": m.group(6), "group": m.group(7), "region": m.group(8)})
    return out


KIND_TITLE = {"adult": "ADULT HUMANOID", "child": "CHILD HUMANOID", "robot": "ROBOT", "dragon": "QUADRUPED DRAGON"}
PROMPT_BEGIN = "[generated from src/model/controls.ts and performance.ts by: python -m blender.validators app-contract --update docs/CLAUDE_BUILD_PROMPT.md. Edit those files, not this block.]"
PROMPT_END = "[end of generated block]"
MD_BEGIN, MD_END = "<!-- begin generated: app keys (python -m blender.validators app-contract --update docs/ASSET_CONTRACT.md) -->", "<!-- end generated: app keys -->"


def _by_region(keys: Dict[str, str]) -> Dict[str, List[str]]:
    order = list(regions.REGIONS)
    per: Dict[str, List[str]] = {}
    for k, r in keys.items():
        per.setdefault(r, []).append(k)
    return {r: sorted(per[r]) for r in sorted(per, key=lambda x: order.index(x) if x in order else 99)}


def _ranges(controls: List[Control], kind: str) -> Dict[str, Tuple[float, float]]:
    app = KIND_TO_APP[kind]
    return {c.bone: c.bone_range for c in controls if app in c.bodies and c.bone and c.bone_range}


PROMPT_PROSE = [
        "APP CONTROL KEYS",
        "The creator app is the consumer of this library. Its built-in bodies are placeholders that your meshes replace, and its sliders are wired to the shape keys, bone properties and shader parameters listed here. Author every one of them: a name that is missing leaves a dead slider. Where this list differs from the key lists above, this list wins. The full table with a description for each key is docs/ASSET_CONTRACT.md.",
        "Slider rule: a slider runs from -100 to 100. A positive value drives the key at weight value/100. A negative value drives that slider's opposite key at weight -value/100, and does nothing when the opposite key does not exist. The opposite key is written <Key>_Neg unless this list names a different one (for example ID-CheekHollow is the opposite of ID-CheekFull). Every key runs 0 to 1 from the Basis and rests at 0. Child sliders use narrower ranges. A control whose element look is none is hidden by the app, but its keys must still exist."
]


def render_prompt_block(controls: Optional[List[Control]] = None) -> str:
    """The regenerated part of the prompt's APP CONTROL KEYS section, from the begin marker to the end marker."""
    cs = controls or parse_controls()
    adult = required("adult", cs)
    lines = [PROMPT_BEGIN, ""]
    for kind in ("adult", "child", "robot", "dragon"):
        r = required(kind, cs)
        lines.append(f"{KIND_TITLE[kind]} KEYS")
        if kind == "child":
            drop = sorted(set(adult["morph"]) - set(r["morph"]))
            add = sorted(set(r["morph"]) - set(adult["morph"]))
            lines.append("Same as the adult list except. Omit: " + ", ".join(drop) + "." + (" Child only: " + ", ".join(add) + "." if add else ""))
        else:
            for region, ks in _by_region(r["morph"]).items():
                lines.append(f"{region}: " + ", ".join(ks))
        rg = _ranges(cs, kind)
        if kind != "child":
            lines.append("Bone length properties (default 1): " + ", ".join(f"{b} {lo:g} to {hi:g}" for b, (lo, hi) in sorted(rg.items())) +
                         ("; also " + ", ".join(sorted(set(r["bone"]) - set(rg))) if set(r["bone"]) - set(rg) else "") + ".")
            lines.append("Shader parameters: " + ", ".join(sorted(r["shader"])) + ".")
        else:
            lines.append("Bone properties and shader parameters: the adult ones that apply: " + ", ".join(sorted(r["bone"])) + "; shader " + ", ".join(sorted(r["shader"])) + ".")
        lines.append("")
    pf = parse_pf_defs()
    lines.append("PERFORMANCE KEYS (adult and child face; robot and dragon use the names that fit the part)")
    for grp in dict.fromkeys(d["group"] for d in pf):
        lines.append(f"{grp}: " + ", ".join(d["key"] for d in pf if d["group"] == grp))
    lines += ["", PROMPT_END]
    return "\n".join(lines)


def render_markdown_block(controls: Optional[List[Control]] = None) -> str:
    cs = controls or parse_controls()
    out: List[str] = []
    for kind in ("adult", "child", "robot", "dragon"):
        app = KIND_TO_APP[kind]
        r = required(kind, cs)
        out += [f"### {KIND_TITLE[kind].title()}", "",
                f"{len(r['morph'])} shape keys, {len(r['bone'])} bone length properties, {len(r['shader'])} shader parameters.", "",
                "| Region | App menu | Control | Shape key (opposite key) | Bone property (range) | Shader parameter | Child range | Shown when | What it does |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for c in cs:
            if app not in c.bodies:
                continue
            keys = f"`{c.morph}`" + (f" / `{c.morph_neg}`" if c.morph_neg else "") if c.morph else ""
            bone = f"`{c.bone}` ({c.bone_range[0]:g}-{c.bone_range[1]:g})" if c.bone and c.bone_range else (f"`{c.bone}`" if c.bone else "")
            shader = f"`{c.shader}`" if c.shader else ""
            if not c.morph:
                desc = c.hint.rstrip(".")
            elif c.morph_neg and _directions(c.hint)[0] and _directions(c.hint)[1]:
                desc = f"+: {describe(c, c.morph).split(': ', 1)[-1]}; -: {describe(c, c.morph_neg).split(': ', 1)[-1].split(' (the other')[0]}"
            elif c.morph_neg:  # the hint does not say which direction is which: the negative key is the reverse of the positive one
                desc = f"+: {describe(c, c.morph).split(': ', 1)[-1][:1].lower() + describe(c, c.morph).split(': ', 1)[-1][1:]}; -: the reverse of {c.morph}"
            else:
                desc = describe(c, c.morph)
            child = f"-{c.child_limit} to {c.child_limit}" if (app == "child" and c.child_limit) else ("-100 to 100" if (app == "child" and c.bidirectional) else ("0 to 100" if app == "child" else ""))
            out.append(f"| {c.region} | {c.group.replace(chr(39), '')} | {c.label} | {keys} | {bone} | {shader} | {child} | {('look: ' + c.needs_look) if c.needs_look else ''} | {desc} |")
        out.append("")
    pf = parse_pf_defs()
    conf = child_conflicts(cs)
    if conf:
        out += ["### Conflicts to resolve in the app", "",
                "The build prompt forbids these adult body-shape keys on the child body (the child is a clothed, general-audience species). "
                "The app still wires them to a child control, so a child library built to the prompt leaves that control without a key: " +
                ", ".join(f"`{k}` (control `{cid}`)" for k, cid in conf) +
                ". Recommended fix: show the control on the adult only, or drive the child's hip width with the `hip_width` bone property alone. The contract keeps the prompt's rule.", ""]
    out += ["### Performance keys", "", "| Group | Key | What it does |", "| --- | --- | --- |"]
    out += [f"| {d['group']} | `{d['key']}` | {d['label']} ({d['region']}) |" for d in pf]
    return "\n".join(out)


def update_prompt(path: str) -> bool:
    """Write the APP CONTROL KEYS section: fixed prose once (before PHASE GATES), regenerated key lists between the markers."""
    text = open(path, encoding="utf-8").read()
    gen = render_prompt_block()
    if PROMPT_BEGIN in text and PROMPT_END in text:
        a, b = text.index(PROMPT_BEGIN), text.index(PROMPT_END) + len(PROMPT_END)
        out = text[:a] + gen + text[b:]
    else:
        anchor = "PHASE GATES\nFinish in this order."
        if anchor not in text:
            raise ValueError("PHASE GATES anchor not found in the prompt")
        out = text.replace(anchor, "\n".join(PROMPT_PROSE) + "\n" + gen + "\n\n" + anchor, 1)
    if out != text:
        open(path, "w", encoding="utf-8").write(out)
    return out != text


def update_markdown(path: str) -> bool:
    text = open(path, encoding="utf-8").read()
    gen = MD_BEGIN + "\n\n" + render_markdown_block() + "\n\n" + MD_END
    if MD_BEGIN in text and MD_END in text:
        a, b = text.index(MD_BEGIN), text.index(MD_END) + len(MD_END)
        out = text[:a] + gen + text[b:]
    else:
        out = text.rstrip() + "\n\n" + gen + "\n"
    if out != text:
        open(path, "w", encoding="utf-8").write(out)
    return out != text


def update_block(path: str, begin: str, end: str, body: str, insert_before: Optional[str] = None) -> bool:
    """Replace the text between begin and end markers (inclusive of the end marker's line), or insert it before `insert_before`.
    Returns True if the file changed."""
    text = open(path, encoding="utf-8").read()
    new_block = body
    if begin in text and end in text:
        a, b = text.index(begin), text.index(end) + len(end)
        # the block in the prompt starts at its heading line, which is before `begin`; callers pass begin = first line of the block
        out = text[:a] + new_block + text[b:]
    elif insert_before and insert_before in text:
        i = text.index(insert_before)
        out = text[:i] + new_block + "\n\n" + text[i:]
    else:
        raise ValueError(f"cannot place the block in {path}")
    if out != text:
        open(path, "w", encoding="utf-8").write(out)
    return out != text
