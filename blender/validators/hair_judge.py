"""TypeSafe judgments over a hair report, following the TypeSafe agent skill.

Numbers become word buckets in code; every question is one narrow judgment phrased so yes = good; all independent
questions go in one request; the Choice has a "none" outcome and is asked in two option orders; low confidence is
routed to a human. `style` (for example "bob" or "twin tails") is optional: when given, one extra question asks whether
the measured shape fits that style. The deterministic checks stay authoritative.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from . import judge
from .model import INFO, PASS, WARN, Finding

FIXES = {
    "clump_count": "Too few clumps: the hair reads as a few fat tubes or a sheet.",
    "clump_shape": "Clumps are flat ribbons or too thin/wide for chunky anime hair.",
    "tips": "Clump tips are not tapered to points.",
    "uv": "UV islands do not match the clumps or are not vertical.",
    "head_fit": "Hair sits inside the head, leaves the cranium bare, or covers ears it should clear.",
    "contract": "Socket, shader, volume/width controls or colours are missing.",
    "none": "Nothing needs fixing.",
}


def _count(n: float) -> str:
    return "very few" if n < 10 else "few" if n < 20 else "a good number" if n < 150 else "very many (strand-like)"


def _chunk(x: float) -> str:
    return "flat ribbons" if x < 0.3 else "slightly flat" if x < 0.45 else "chunky" if x <= 1.05 else "unclear"


def _width(x: float) -> str:
    return "thin" if x < 0.25 else "medium" if x <= 0.55 else "wide"


def _taper(x: float) -> str:
    return "strongly pointed" if x <= 0.5 else "tapered" if x <= 0.75 else "blunt"


def _share(x: float) -> str:
    return "none" if x <= 0.02 else "a little" if x <= 0.15 else "a lot"


def build_state(topo: dict, style: Optional[str] = None, contract: Optional[dict] = None) -> dict:
    s, fit = topo["summary"], topo["fit"]
    state = {
        "hair": {
            "clumps": _count(s["clump_count"]),
            "clump_chunkiness": _chunk(s["median_thick_over_width"]),
            "clump_width_relative_to_head": _width(s["median_width_over_head"]),
            "clump_tips": _taper(s["tip_over_root_median"]),
            "clump_sides_closed": "mostly" if s["tube_fraction"] >= 0.5 else "mostly open ribbons",
            "length": topo["length_bucket"],
            "buried_inside_head": _share(fit["inside_skull_fraction"]),
            "cranium_covered": "fully" if fit["cranium_coverage"] >= 0.9 else "partly" if fit["cranium_coverage"] >= 0.5 else "mostly bare",
            "creature_ears_equipped": bool(fit.get("ear_clear_required", 0.0)),
        },
        "target_look": "thick chunky clumps with pointed tips, flat painted shading, one highlight band per clump",
    }
    if fit.get("ear_clear_required"):  # covering ears is only a problem when creature ears are equipped
        state["hair"]["ears_covered"] = _share(fit.get("ear_covered_fraction", 0.0))
    if style:
        state["declared_style"] = style
    if contract is not None:
        state["library_controls"] = contract
    return state


def questions(state: dict, order: int = 0) -> dict:
    qs = {
        "chunky": {"type": "noul", "instructions": "Does `hair.clump_chunkiness` describe chunky clumps, not flat ribbons or fine strands?"},
        "enough_clumps": {"type": "noul", "instructions": "Is `hair.clumps` enough separate clumps to read as a thick anime hairstyle rather than a few fat tubes or one sheet?"},
        "pointed": {"type": "noul", "instructions": "Are the clump tips in `hair.clump_tips` tapered or pointed rather than blunt?"},
        "not_buried": {"type": "noul", "instructions": "Is `hair.buried_inside_head` none or only a little, meaning the hair sits on the head and not inside it?"},
        "cranium": {"type": "noul", "instructions": "Is the cranium in `hair.cranium_covered` covered by hair, as a full hairstyle should be?"},
        "quality": {"type": "score", "instructions":
            "Rate how well `hair` matches the `target_look` of chunky pointed anime hair clumps.",
            "criteria": ["Wrong: fine strands, flat ribbons or a single sheet", "Poor: some chunky clumps but mostly ribbons or blunt tubes",
                         "Acceptable: chunky clumps, tips only partly pointed", "Good: chunky tapered clumps in good number",
                         "Excellent: chunky pointed clumps, sits cleanly on the head, ready for the toon highlight"]},
    }
    if state["hair"]["creature_ears_equipped"]:
        qs["ears_clear"] = {"type": "noul", "instructions": "Are the ears in `hair.ears_covered` left visible (none covered), as required with creature ears equipped?"}
    if "declared_style" in state:
        qs["fits_style"] = {"type": "noul", "instructions":
            "Do `hair.length`, `hair.cranium_covered` and `hair.clumps` fit the hairstyle named in `declared_style`?"}
    if "library_controls" in state:
        qs["controls_ok"] = {"type": "noul", "instructions":
            "Does `library_controls` show the hair is parented to a hair socket and has volume and width controls and root, tip and highlight colour parameters?"}
    opts = list(FIXES.items())
    qs["first_fix"] = {"type": "choice", "instructions": "Which single problem should the modeler fix first?",
                       "criteria": dict(opts[::-1] if order else opts)}
    return qs


def ask(topo: dict, label: str, style: Optional[str] = None, contract: Optional[dict] = None,
        transport: Callable[[dict], dict] = judge.http_transport, model: str = judge.MODEL) -> List[Finding]:
    state = build_state(topo, style, contract)
    try:
        answers = [transport({"model": model, "state": state, "questions": questions(state, o)})["answers"] for o in (0, 1)]
    except Exception as e:
        return [Finding(f"hairjudge.{label}", "skip", f"TypeSafe unavailable ({e}); deterministic result stands")]
    out: List[Finding] = []
    for name, ans in answers[0].items():
        if "noul" in ans:
            p = ans["noul"]
            uncertain = abs(2 * p - 1) < judge.MIN_CONFIDENCE
            out.append(Finding(f"hairjudge.{label}.{name}", PASS if p >= 0.6 else INFO if uncertain else WARN,
                               f"TypeSafe: {name.replace('_', ' ')}" + (" (uncertain, needs a human look)" if uncertain else ""), p, ">= 0.60"))
    q = answers[0].get("quality", {})
    if q:
        c, s = q.get("confidence", 0.0), q.get("score", 0.0)
        out.append(Finding(f"hairjudge.{label}.quality", INFO if c < judge.MIN_CONFIDENCE else (PASS if s >= 2.5 else WARN),
                           f"TypeSafe hair quality (confidence {c:.2f})" + (" - low confidence, needs a human look" if c < judge.MIN_CONFIDENCE else ""),
                           s, ">= 2.5 of 4"))
    f0, f1 = answers[0].get("first_fix", {}), answers[1].get("first_fix", {})
    if f0 and f1:
        agree = f0.get("choice") == f1.get("choice")
        out.append(Finding(f"hairjudge.{label}.first_fix", INFO,
                           (f"TypeSafe says fix first: {f0['choice']} ({FIXES.get(f0['choice'], '')})" if f0["choice"] != "none" else "TypeSafe finds nothing to fix first")
                           if agree else f"TypeSafe's first-fix answer changed with option order ({f0['choice']} vs {f1['choice']}); treat as uncertain"))
    return out
