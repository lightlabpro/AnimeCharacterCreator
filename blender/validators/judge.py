"""TypeSafe judge: qualitative grading of the *measured* report.

TypeSafe (https://api.typesafe.ai, POST /v1/systemone) answers yes/no, score and choice questions about JSON
or text. It cannot see images or meshes, so we send it the numbers: the metrics, their target bands, the
reference-envelope result and the failing checks. It decides things a threshold cannot: whether a set of
borderline numbers will still read as a believable anime figure, and which problem to fix first.

It never overrides a deterministic FAIL. It can only add a failure when it is confident the figure is not
plausible even though every threshold passed.

Auth: the API key goes in the TYPESAFE_API_KEY environment variable. Inside Claude's cloud container the
proxy injects it, so no key is needed there.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Callable, Dict, List, Optional

from .model import FAIL, INFO, PASS, SKIP, WARN, Finding, Report
from .spec import METRICS

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"

AREAS = {
    "proportion": "Overall height in heads, leg length, torso lines, widths: the silhouette reads wrong.",
    "limbs": "Arm, hand, thigh/shin or foot ratios are off, or the A-pose is wrong.",
    "head_face": "Eye line, eye gap, mouth height, temple width, neck width or forehead lean are off.",
    "contract": "Names, sockets, shape keys, budgets, transforms or origin break the library contract.",
    "reference": "Metrics sit outside the reference model envelope while still inside the manual's bands.",
    "none": "Nothing needs fixing.",
}

Transport = Callable[[dict], dict]


def http_transport(payload: dict, timeout: float = 30.0) -> dict:
    headers = {"content-type": "application/json"}
    key = os.environ.get("TYPESAFE_API_KEY")
    if key:
        headers["authorization"] = f"Bearer {key}"
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def build_state(report: Report) -> dict:
    rows = []
    for key, v in report.metrics.items():
        m = METRICS.get(key)
        band = m.bands.get(report.kind) if m else None
        rows.append({"metric": key, "label": m.label if m else key, "value": round(v, 3),
                     "target": band.text() if band else "n/a", "per": m.denominator if m else ""})
    problems = [{"check": f.check, "severity": f.severity, "message": f.message,
                 "value": None if f.value is None else round(f.value, 3), "target": f.expected}
                for f in report.findings if f.severity in (FAIL, WARN)]
    return {
        "body_kind": report.kind,
        "style": "anime, Monster Hunter Stories 3 base: clean planes, believable skeleton underneath, simplified not broken",
        "adult_target_heads": "7-7.5" if report.kind == "adult" else None,
        "child_target_heads": "5-5.5" if report.kind == "child" else None,
        "metrics": rows,
        "problems": problems,
    }


def questions(kind: str) -> dict:
    return {
        "plausible": {
            "type": "noul",
            "instructions": (f"These are measurements of a stylised anime {kind} 3D character. Taken together, "
                             "would this body read as anatomically believable at front, three-quarter and side views, "
                             "with a skeleton that stays correct under the stylisation?"),
            "criteria": {"true": "Proportions and landmarks are coherent; deviations are small and mutually consistent.",
                         "false": "At least one deviation is large, or several deviations combine into a broken-looking figure."},
        },
        "quality": {
            "type": "score",
            "instructions": "Rate how well these measurements match the stated targets and a professional anime character.",
            "criteria": ["Broken: several metrics fail", "Poor: a major metric fails or many warn",
                         "Acceptable: only small warnings", "Good: all metrics inside their bands",
                         "Excellent: inside the bands and consistent with the reference models"],
        },
        "first_fix": {
            "type": "choice",
            "instructions": "Which single area should the modeler fix first?",
            "criteria": AREAS,
        },
    }


def ask(report: Report, transport: Transport = http_transport, model: str = MODEL) -> List[Finding]:
    payload = {"model": model, "state": build_state(report), "questions": questions(report.kind)}
    try:
        data = transport(payload)
    except (urllib.error.URLError, OSError, ValueError) as e:
        return [Finding("judge", SKIP, f"TypeSafe unavailable ({e}); deterministic result stands. "
                        "Set TYPESAFE_API_KEY to enable the judge.")]
    a = data.get("answers", {})
    out: List[Finding] = []
    p = a.get("plausible", {}).get("noul")
    q = a.get("quality", {})
    f = a.get("first_fix", {})
    det_ok = report.ok
    if p is not None:
        # A deterministic pass is overruled only by a confident 'implausible'.
        sev = PASS if p >= 0.6 else (FAIL if (det_ok and p < 0.3) else WARN)
        out.append(Finding("judge.plausible", sev, "TypeSafe: anatomically believable as a whole", p, ">= 0.60",
                           "See the first-fix area below." if sev != PASS else ""))
    if q:
        s = q.get("score", 0.0)
        sev = PASS if s >= 2.5 else WARN
        out.append(Finding("judge.quality", sev, f"TypeSafe quality score (confidence {q.get('confidence', 0):.2f})",
                           s, ">= 2.5 of 4"))
    if f and f.get("choice") not in (None, "none"):
        out.append(Finding("judge.first_fix", INFO, f"TypeSafe says fix first: {f['choice']} "
                           f"({AREAS.get(f['choice'], '')}) confidence {f.get('confidence', 0):.2f}"))
    report.extra["typesafe"] = {"model": data.get("model"), "usage": data.get("usage"), "answers": a}
    return out
