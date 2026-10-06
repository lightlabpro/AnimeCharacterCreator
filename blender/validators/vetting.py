"""Vet reference profiles with TypeSafe before the validators trust them.

A reference model's dimensions are just numbers (a profile). Here TypeSafe makes several independent
passes over each profile, each with a different framing, and scores every metric. A metric is *kept* only
if the spec band does not hard-fail it and the mean TypeSafe score is >= KEEP. The result is stored in the
profile (`vetted`), and `reference.load_profiles` then uses only kept metrics, so a mis-measured or
off-model reference cannot loosen the envelope.
"""
from __future__ import annotations

import urllib.error
from statistics import mean
from typing import Callable, Dict, List

from . import judge
from .model import FAIL
from .spec import METRICS, bucket

KEEP = 0.5
FRAMINGS = (
    "Is this value anatomically correct for a human figure drawn from reference, ignoring stylisation?",
    "Is this value acceptable for a stylised anime character (clean, believable skeleton underneath)?",
    "Is this value consistent with the other measurements of the same model, i.e. not a measuring error?",
)


def _questions(kind: str, profile: dict, framing: str) -> dict:
    qs = {}
    for key, v in profile["metrics"].items():
        m = METRICS.get(key)
        band = m.bands.get(kind) if m else None
        if not m or band is None:
            continue
        # State carries the word reading; the number stays in code (Jev is weak at numeric comparison).
        qs[key] = {"type": "noul",
                   "instructions": f"{framing} Look at `readings.{key}`: the {m.label} reads '{bucket(key, v, kind)}' "
                                   f"against its target range."}
    return qs


def vet_profile(profile: dict, transport: Callable[[dict], dict] = judge.http_transport, passes: int = 3) -> dict:
    kind = profile["kind"]
    state = {"model": profile.get("name"), "body_kind": kind,
             "readings": {k: bucket(k, x, kind) for k, x in profile["metrics"].items() if k in METRICS}}
    scores: Dict[str, List[float]] = {}
    for framing in FRAMINGS[:passes]:
        qs = _questions(kind, profile, framing)
        if not qs:
            break
        data = transport({"model": judge.MODEL, "state": state, "questions": qs})
        for key, ans in data.get("answers", {}).items():
            if "noul" in ans:
                scores.setdefault(key, []).append(ans["noul"])
    vetted = {}
    for key, v in profile["metrics"].items():
        band = METRICS[key].bands.get(kind) if key in METRICS else None
        s = mean(scores[key]) if scores.get(key) else None
        hard_fail = band is not None and band.grade(v) == FAIL
        vetted[key] = {"score": None if s is None else round(s, 3), "passes": len(scores.get(key, [])),
                       "kept": (s is not None and s >= KEEP and not hard_fail)}
    out = dict(profile)
    out["vetted"] = vetted
    out["vetted_by"] = f"typesafe:{judge.MODEL}"
    return out


def vet_file(path: str, transport: Callable[[dict], dict] = judge.http_transport, passes: int = 3) -> dict:
    import json
    with open(path, "r", encoding="utf-8") as fh:
        prof = json.load(fh)
    try:
        vetted = vet_profile(prof, transport, passes)
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise RuntimeError(f"TypeSafe unavailable, profile left unvetted: {e}")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(vetted, fh, indent=2)
    return vetted
