"""One entry point: snapshot -> anatomy + contract + references (+ silhouettes) (+ TypeSafe judge) -> report."""
from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional

from . import checks, judge, reference
from .model import Report, SceneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILES = os.path.normpath(os.path.join(HERE, "..", "references", "profiles"))


def evaluate(scene: SceneInfo, tag: str = "", profiles_dir: str = DEFAULT_PROFILES, use_judge: bool = False,
             transport: Optional[Callable[[dict], dict]] = None, silhouettes: Optional[Dict[str, tuple]] = None) -> Report:
    """silhouettes: {label: (candidate_mask, reference_mask)} for front/side comparisons made by the caller."""
    report = Report(kind=scene.kind, tag=tag)
    vals = checks.anatomy(scene, report)
    checks.contract(scene, report)
    report.add(*reference.compare(vals, reference.load_profiles(profiles_dir, scene.kind)))
    if silhouettes:
        from . import silhouette
        for label, (cand, ref) in silhouettes.items():
            report.add(*silhouette.compare(cand, ref, label))
    if use_judge:
        report.add(*judge.ask(report, transport or judge.http_transport))
    return report


def write(report: Report, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{report.kind}-{report.tag or 'latest'}.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(report.to_json())
    return path
