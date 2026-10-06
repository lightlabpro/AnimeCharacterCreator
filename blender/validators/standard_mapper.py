"""Map free-form names (shape keys, bones) onto a standard vocabulary with TypeSafe.

Pattern from the TypeSafe docs: "select instead of generate" and "hierarchical classification": the answer space is a
closed set, the first request picks the region, the second picks the name inside that region (far fewer options), each
Choice is asked in two option orders and only an answer that agrees in both orders with enough confidence is accepted.
Everything else is returned unmapped for a human. Deterministic matching always runs first and is done by the callers.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Tuple

from . import judge

MIN_CONF = 0.5
Mapping = Dict[str, Tuple[Optional[str], str, float]]  # name -> (standard or None, how, confidence)


def _words(camel: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z0-9])", " ", camel).lower()


def _choice_q(instr: str, options: Dict[str, str], reverse: bool) -> dict:
    items = list(options.items())
    return {"type": "choice", "instructions": instr, "criteria": dict(items[::-1] if reverse else items)}


def _agreeing(a: dict, b: dict) -> Tuple[Optional[str], float]:
    if a.get("choice") == b.get("choice") and a.get("confidence", 0) >= MIN_CONF and b.get("confidence", 0) >= MIN_CONF:
        return a["choice"], min(a["confidence"], b["confidence"])
    return None, min(a.get("confidence", 0), b.get("confidence", 0))


def map_to_options(items: List[str], regions: Dict[str, Dict[str, str]], what: str,
                   transport: Callable[[dict], dict] = judge.http_transport, model: str = judge.MODEL,
                   context: str = "A 3D anime character rig. Names come from a modeling program.") -> Mapping:
    """regions: region id -> {standard name: description}. Returns name -> (standard|None, how, confidence)."""
    out: Mapping = {i: (None, "unmapped", 0.0) for i in items}
    if not items:
        return out
    region_opts = {r: f"{r}: " + ", ".join(list(opts)[:4]) + "..." for r, opts in regions.items()}
    region_opts["none"] = "Not a " + what + " at all (a helper, correction or unrelated name)."
    state = {"context": context, "naming_task": f"Match each {what} name to the standard vocabulary."}

    def qs(order: int):
        return {f"i{n}": _choice_q(f"Which region does the {what} named '{name}' belong to?", region_opts, bool(order))
                for n, name in enumerate(items)}
    try:
        a = transport({"model": model, "state": state, "questions": qs(0)})["answers"]
        b = transport({"model": model, "state": state, "questions": qs(1)})["answers"]
    except Exception:
        return out
    by_region: Dict[str, List[Tuple[str, float]]] = {}
    for n, name in enumerate(items):
        region, conf = _agreeing(a[f"i{n}"], b[f"i{n}"])
        if region and region != "none":
            by_region.setdefault(region, []).append((name, conf))
        elif region == "none":
            out[name] = (None, "typesafe:not-a-" + what.replace(" ", "-"), conf)
    for region, members in by_region.items():
        opts = {k: v for k, v in regions[region].items()}
        opts["none"] = "None of these fits"

        def q2(order: int):
            return {f"i{n}": _choice_q(f"Which standard {what} is the one named '{name}'?", opts, bool(order))
                    for n, (name, _) in enumerate(members)}
        try:
            a2 = transport({"model": model, "state": state, "questions": q2(0)})["answers"]
            b2 = transport({"model": model, "state": state, "questions": q2(1)})["answers"]
        except Exception:
            continue
        for n, (name, c1) in enumerate(members):
            std, c2 = _agreeing(a2[f"i{n}"], b2[f"i{n}"])
            if std and std != "none":
                out[name] = (std, "typesafe", min(c1, c2))
    return out
