"""One TypeSafe judgment per region, following the TypeSafe agent skill.

For each region the judge gets only that region's state (the docs warn that unrelated state costs accuracy): the target look
for the region in words, and its checks as words. Numbers never go in. Graded checks are sent as passes / borderline / fails; measured-
only checks are sent relative to the reference models ("within / below / above the references") when references exist, else as
"measured, no target". Questions are phrased so yes = good; the Choice has a "none" outcome and is asked in two option orders;
low confidence is routed to a human. The numeric checks stay authoritative.
"""
from __future__ import annotations

import json
import os
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from . import judge, regions as rg
from .model import FAIL, INFO, PASS, SKIP, WARN, Finding

RUBRIC: Dict[str, str] = {
    "skull": "A full cranium with a vertical forehead, about 0.8 of the head height wide at the temples; the head sits on a slim neck.",
    "face": "A clean face with eyes about the middle of the head, features low on the face for a young look.",
    "eyes": "Medium-large glossy eyes: near-spherical eyeballs set in sockets, level and evenly spaced about one eye-width apart, the eye line about 0.37 to 0.45 of the head height.",
    "brows": "Thin tapered brow strips above the eyes with enough geometry to bend, matching left to right.",
    "nose": "A small wedge nose with little protrusion, the tip somewhere around the middle of eyes-to-chin (higher on anime faces).",
    "mouth": "A mouth close under the nose and near the chin, with teeth and tongue inside it, and the closed, small, mid and open visemes.",
    "jaw": "A defined jaw angle running to a rounded chin.",
    "cheeks": "Soft cheeks that can fill or hollow without noisy normals.",
    "ears": "Ears at mid-head height between the brow and the nose base, sized to the head.",
    "hair": "Many chunky closed clumps with pointed tips, one UV island per clump, sitting on the head and clearing creature ears.",
    "facial_hair": "Separate moustache, sideburn and beard pieces with length and bulk controls and their own colour.",
    "neck": "A slim neck about 0.4 of the head width, long enough to show a jaw-to-neck angle.",
    "shoulders": "Shoulders about two heads wide with the clavicle and acromion visible.",
    "chest": "The nipple line about two heads below the crown on an eight-head figure.",
    "waist": "A navel line about three heads below the crown; the torso reads as three even parts.",
    "hips": "The pubis at the body midpoint on an adult; the pelvis wider on the feminine preset.",
    "arms": "Hanging wrists reach the crotch line and elbows sit at the waist; limb lengths scale along the bone.",
    "hands": "A hand about as long as the face, with five fingers whose knuckles form an arc peaking at the middle finger.",
    "legs": "A thigh about as long as the lower leg and legs about half the body height.",
    "feet": "A wedge-shaped foot about as long as the forearm, with the ankle bone higher on the inside; digitigrade beasts have a raised heel.",
    "body": "A body of 7 to 7.5 heads (child 5 to 5.5) with a clean topology: almost all quads, loops at joints, and no folds when bent.",
    "muzzle": "A prism or cone attached to the cranium, mouth corner about two-thirds of the way toward the eye, with closed, small, mid and open visemes.",
    "tail": "A continuation of the spine at the sacrum, as wide at the base as the sacrum and tapering smoothly.",
    "wings": "Wings on their own shoulder mass behind and above the arms, with a membrane or feather layout that folds along the back.",
    "horns": "Horns that grow from the skull surface and mirror left to right, as keratin over bone.",
    "mane": "A mane or crest as clumps whose tips form the silhouette.",
    "frill": "A neck frill or gills of a believable size and flare.",
    "surface": "Large graphic scale plates, fur clumps without strands, feathers as shingled tiles, thick folded hide.",
    "archetype": "Each archetype is identifiable from its elements alone and distinct from its neighbours.",
    "clothing": "Garments that sit just off the skin without poking through, skinned like the body, covering their zone, with the accessory manifest complete.",
    "accessory": "Accessories parented to the right socket, scaled to the body and placed where the slot belongs.",
    "quadruped": "Forelimbs carry about 60% of the weight, elbows and knees near belly level, wings rooted behind and above the forelimbs, smooth neck and tail taper.",
}


def load_envelope(directory: str) -> Dict[str, Tuple[float, float]]:
    """Min/max of every `face.*` and `<metric>` measured on the reference models (blender/references/regions/*.json)."""
    env: Dict[str, List[float]] = {}
    if not os.path.isdir(directory):
        return {}
    for fn in os.listdir(directory):
        if not fn.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(directory, fn), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for k, v in (d.get("face_metrics") or {}).items():
            env.setdefault(k, []).append(float(v))
    return {k: (min(v), max(v)) for k, v in env.items() if len(v) >= 1}


def _feature(check: str) -> str:
    parts = check.split(".")
    return parts[1] if len(parts) >= 2 else "general"


def _metric_key(check: str) -> str:
    return check.split(".")[-1]


def reading(f: Finding, env: Dict[str, Tuple[float, float]]) -> str:
    if f.severity == "pass":
        return "passes"
    if f.severity == "warn":
        return "borderline"
    if f.severity == "fail":
        return "fails"
    if f.severity == "skip":
        return "not measurable (part missing)"
    if f.value is not None and _metric_key(f.check) in env:
        lo, hi = env[_metric_key(f.check)]
        pad = 0.15 * max(hi - lo, 1e-9)
        return "within the reference models" if lo - pad <= f.value <= hi + pad else ("below the reference models" if f.value < lo else "above the reference models")
    return "measured, no target"


def build_state(region: str, findings: List[Finding], env: Dict[str, Tuple[float, float]]) -> dict:
    return {"region": rg.REGIONS[region].label, "target_look": RUBRIC.get(region, ""),
            "checks": [{"feature": _feature(f.check), "what": f.message.split(": ", 1)[-1][:110], "result": reading(f, env)}
                       for f in findings if f.severity != "info" or f.value is not None][:30]}


def questions(region: str, findings: List[Finding], order: int = 0) -> dict:
    feats = sorted({_feature(f.check) for f in findings})
    opts = {"none": "Nothing needs fixing.", **{f: f"The {f.replace('_', ' ')} checks need work." for f in feats}}
    items = list(opts.items())
    return {
        "region_ok": {"type": "noul", "instructions": "Do the `checks` show this region is built correctly, with no failing check and no serious borderline check?"},
        "matches_target": {"type": "noul", "instructions": "Does the region described by `checks` match `target_look`?"},
        "quality": {"type": "score", "instructions": "Rate how well this region meets `target_look`, using `checks`.",
                    "criteria": ["Broken: several checks fail", "Poor: a check fails or many are borderline", "Acceptable: only borderline checks",
                                 "Good: checks pass and measured values sit with the references", "Excellent: all checks pass and it matches the target look"]},
        "first_fix": {"type": "choice", "instructions": "Which feature of this region should the modeler fix first?",
                      "criteria": dict(items[::-1] if order else items)},
    }


def judge_region(region: str, findings: List[Finding], env: Dict[str, Tuple[float, float]],
                 transport: Callable[[dict], dict] = judge.http_transport, model: str = judge.MODEL) -> List[Finding]:
    state = build_state(region, findings, env)
    try:
        ans = [transport({"model": model, "state": state, "questions": questions(region, findings, o)})["answers"] for o in (0, 1)]
    except Exception as e:
        return [Finding(f"{region}.judge.skip", SKIP, f"TypeSafe unavailable ({e}); numeric result stands")]
    out: List[Finding] = []
    for name in ("region_ok", "matches_target"):
        a = ans[0].get(name)
        if a and "noul" in a:
            p = a["noul"]
            unsure = abs(2 * p - 1) < judge.MIN_CONFIDENCE
            out.append(Finding(f"{region}.judge.{name}", PASS if p >= 0.6 else INFO if unsure else WARN,
                               f"TypeSafe: {name.replace('_', ' ')}" + (" (uncertain, needs a human look)" if unsure else ""), p, ">= 0.60"))
    q = ans[0].get("quality", {})
    if q:
        c, s = q.get("confidence", 0.0), q.get("score", 0.0)
        out.append(Finding(f"{region}.judge.quality", INFO if c < judge.MIN_CONFIDENCE else (PASS if s >= 2.5 else WARN),
                           f"TypeSafe quality {s:.1f}/4 (confidence {c:.2f})" + (" - low confidence, needs a human look" if c < judge.MIN_CONFIDENCE else ""), s, ">= 2.5"))
    f0, f1 = ans[0].get("first_fix", {}), ans[1].get("first_fix", {})
    if f0 and f1:
        agree = f0.get("choice") == f1.get("choice")
        out.append(Finding(f"{region}.judge.first_fix", INFO, (f"TypeSafe says fix first: {f0['choice']}" if f0["choice"] != "none" else "TypeSafe finds nothing to fix first")
                           if agree else f"first-fix answer changed with option order ({f0['choice']} vs {f1['choice']}); uncertain"))
    return out


def judge_all(report_findings: Iterable[Finding], env: Dict[str, Tuple[float, float]], transport: Callable[[dict], dict] = judge.http_transport,
              model: str = judge.MODEL) -> Dict[str, List[Finding]]:
    grouped = rg.group_by_region(report_findings)
    return {r: judge_region(r, fs, env, transport, model) for r, fs in grouped.items() if r in rg.REGIONS and any(f.severity != "info" or f.value is not None for f in fs)}
