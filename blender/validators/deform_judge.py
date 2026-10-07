"""TypeSafe judgments over the per-region deformation findings (deform_regions).

Follows the TypeSafe agent skill. The numbers stay in code: each region's tests are sent as words relative to that region's own
bands ("inside the range", "past the warn limit", "past the fail limit"), so one question reads the same for a lid and a thigh.
Yes = good in every question, the Choice has a "none" outcome and is asked in two option orders, low confidence goes to a human,
and the deterministic bands stay authoritative: TypeSafe can add a warning, never clear a failure.
"""
from __future__ import annotations

from typing import Callable, Dict, Iterable, List

from . import deform_regions as dr, judge
from .model import FAIL, INFO, PASS, SKIP, WARN, Finding

WORD = {PASS: "inside the range", WARN: "past the warn limit", FAIL: "past the fail limit"}
BEHAVIOUR = {
    "limb_joint": "a large joint that bends to the end of its range: the inside may squash and the outside may stretch, but it must not pinch, fold or have a hard weight edge",
    "fine_hinge": "a small hinge (wrist, ankle, finger, toe or jaw): short segments that must keep their volume",
    "column": "a neck or spine segment that bends a little over a long span: it must look smooth",
    "face_soft": "a face region moved by a shape key: edges may stretch a lot but the surface must never fold or spike",
    "rigid": "a rigid piece that must only move, never deform",
    "soft_cover": "a cloth or membrane that follows the body and may wrinkle a little",
    "tube": "a tapering tube such as a tail that bends in many small steps",
}


def group(findings: Iterable[Finding]) -> Dict[str, Dict[str, Dict[str, str]]]:
    """region -> test label -> metric -> severity, from the `deform.<region>.<test>.<metric>` findings."""
    out: Dict[str, Dict[str, Dict[str, str]]] = {}
    for f in findings:
        p = f.check.split(".")
        if len(p) == 4 and p[0] == "deform" and f.severity in (PASS, WARN, FAIL):
            out.setdefault(p[1], {}).setdefault(p[2], {})[p[3]] = f.severity
    return out


def build_state(region: str, tests: Dict[str, Dict[str, str]]) -> dict:
    cls = dr.REGION_CLASS.get(region, "limb_joint")
    rows = []
    for label, metrics in tests.items():
        bad = {m: s for m, s in metrics.items() if s != PASS}
        rows.append({"test": label.replace("_", " "),
                     "overall": WORD[FAIL] if FAIL in bad.values() else WORD[WARN] if bad else WORD[PASS],
                     "problems": {dr.METRIC_TEXT.get(m, m): WORD[s] for m, s in bad.items()} or "none"})
    return {"region": region, "this_region_is": BEHAVIOUR.get(cls, ""), "tests": rows}


def questions(region: str, tests: Dict[str, Dict[str, str]], order: int = 0) -> dict:
    metrics = sorted({m for t in tests.values() for m in t})
    opts = {"none": "Nothing needs fixing.", **{m: dr.METRIC_FIX.get(m, m) for m in metrics}}
    items = list(opts.items())
    return {
        "clean": {"type": "noul", "instructions": "Given what `this_region_is`, would every test in `tests` deform cleanly, with no test past a limit?"},
        "no_fold": {"type": "noul", "instructions": "Is every test free of folded faces and free of a surface that collapses or pinches?"},
        "quality": {"type": "score", "instructions": "Rate how cleanly this region deforms, using `tests`.",
                    "criteria": ["Broken: several tests are past the fail limit", "Poor: a test is past the fail limit",
                                 "Acceptable: only warn-limit problems", "Good: every test is inside the range with one borderline",
                                 "Production ready: every test is inside the range"]},
        "first_fix": {"type": "choice", "instructions": "Which problem should the modeler fix first in this region?",
                      "criteria": dict(items[::-1] if order else items)},
    }


def ask_region(region: str, tests: Dict[str, Dict[str, str]], transport: Callable[[dict], dict] = judge.http_transport,
               model: str = judge.MODEL) -> dict:
    """Raw answers (order 0 and 1) for one region; `verdict()` turns them into findings."""
    state = build_state(region, tests)
    return {"state": state, "answers": [transport({"model": model, "state": state, "questions": questions(region, tests, o)})["answers"] for o in (0, 1)]}


def verdict(region: str, got: dict) -> List[Finding]:
    a, b = got["answers"]
    out: List[Finding] = []
    for name in ("clean", "no_fold"):
        x = a.get(name)
        if x and "noul" in x:
            p = x["noul"]
            unsure = abs(2 * p - 1) < judge.MIN_CONFIDENCE
            out.append(Finding(f"deformjudge.{region}.{name}", PASS if p >= 0.6 else INFO if unsure else WARN,
                               f"TypeSafe: {region} deforms {'cleanly' if name == 'clean' else 'without folds'}" + (" (uncertain, needs a human look)" if unsure else ""), p, ">= 0.60"))
    q = a.get("quality", {})
    if q:
        c, s = q.get("confidence", 0.0), q.get("score", 0.0)
        out.append(Finding(f"deformjudge.{region}.quality", INFO if c < judge.MIN_CONFIDENCE else PASS if s >= 2.5 else WARN,
                           f"TypeSafe {region} deformation quality {s:.1f}/4 (confidence {c:.2f})" + (" - low confidence, needs a human look" if c < judge.MIN_CONFIDENCE else ""), s, ">= 2.5"))
    f0, f1 = a.get("first_fix", {}), b.get("first_fix", {})
    if f0 and f1:
        agree = f0.get("choice") == f1.get("choice")
        out.append(Finding(f"deformjudge.{region}.first_fix", INFO,
                           (f"TypeSafe says fix first: {f0['choice']}" if f0["choice"] != "none" else "TypeSafe finds nothing to fix first") if agree
                           else f"first-fix answer changed with option order ({f0['choice']} vs {f1['choice']}); uncertain"))
    return out


def judge_all(findings: Iterable[Finding], transport: Callable[[dict], dict] = judge.http_transport, model: str = judge.MODEL) -> Dict[str, List[Finding]]:
    out: Dict[str, List[Finding]] = {}
    for region, tests in group(findings).items():
        try:
            out[region] = verdict(region, ask_region(region, tests, transport, model))
        except Exception as e:  # network, auth, size: the bands stand
            out[region] = [Finding(f"deformjudge.{region}.skip", SKIP, f"TypeSafe unavailable ({e}); the bands stand")]
    return out
