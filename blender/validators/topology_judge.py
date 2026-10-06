"""TypeSafe judgments over a topology report (the dict analyze_topology.py writes).

Follows the TypeSafe agent skill: numbers are turned into concrete word buckets in code (Jev is weak at numeric
comparison), each question is one narrow judgment, all independent questions go in one request, Choice has a
"none" outcome and is asked in two option orders (Jev leans to the first option), and low confidence is routed to a
human instead of being acted on. The deterministic checks stay authoritative; this layer reads the geometry the way
a rigger would and says which joint to fix first.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from . import judge
from .model import FAIL, INFO, PASS, WARN, Finding

JOINTS = ("shoulder", "elbow", "knee", "hip")
FIXES = {
    "triangles_and_ngons": "Many triangles or n-gons in the surface (quad ratio).",
    "distorted_quads": "Sheared, long thin or non-planar quads.",
    "joint_loops": "Too few or too many edge loops around the shoulder, elbow or knee.",
    "joint_weights": "A joint folds, pinches or stretches when bent (weights or loops).",
    "shape_keys": "A shape key folds or over-stretches its region.",
    "coincident_vertices": "Many coincident vertices (zero-length edges).",
    "none": "Nothing needs fixing.",
}


def _stretch(x: float) -> str:
    return "none" if x <= 1.5 else "mild" if x <= 2.0 else "strong" if x <= 4.0 else "severe"


def _squash(x: float) -> str:
    return "none" if x >= 0.5 else "mild" if x >= 0.3 else "strong" if x >= 0.15 else "severe"


def _flips(x: float) -> str:
    return "none" if x <= 0.002 else "a few faces" if x <= 0.01 else "many faces"


def _share(x: float) -> str:
    return "almost none" if x <= 0.001 else "a small share" if x <= 0.01 else "a noticeable share" if x <= 0.03 else "a large share"


def _ratio(q: float) -> str:
    return "almost all quads" if q >= 0.95 else "mostly quads" if q >= 0.9 else "many triangles" if q >= 0.8 else "dominated by triangles"


def _skew(x: float) -> str:
    return "clean" if x <= 30 else "somewhat sheared" if x <= 45 else "badly sheared"


def _aspect(x: float) -> str:
    return "even" if x <= 4 else "some long thin quads" if x <= 8 else "many long thin quads"


def build_state(topo: dict) -> dict:
    s = topo["stats"]
    state: dict = {
        "surface": {
            "quads": _ratio(s["quad_ratio"]),
            "quad_shape": _skew(s["quad_skew_p95"]),
            "quad_proportions": _aspect(s["quad_aspect_p95"]),
            "ngons": "none" if s["ngon_ratio"] == 0 else "a few",
        },
        "joint_loops": {j: {"count": n, "manual_target": "2 to 4" if j == "elbow" else "3 to 5" if j == "shoulder" else "4 to 6"}
                        for j, n in topo.get("loops", {}).items()},
        "bends": {},
        "shape_keys": {},
        "notes": {"coincident_edges_ignored": "many" if topo.get("bend") and next(iter(topo["bend"].values())).get("ignored_degenerate_edges", 0) > 1000 else "few"},
    }
    for j, d in topo.get("bend", {}).items():
        widespread = d["frac_stretch_gt_2"] + d["frac_squash_lt_half"]
        iso = " but isolated" if widespread <= 0.005 else " and widespread"
        state["bends"][j] = {"worst_bend": d["worst"],
                             "how_widespread_is_extreme_stretch_or_squash": _share(widespread),
                             "single_worst_edge_stretch": _stretch(d["edge_stretch_max"]) + iso,
                             "single_worst_edge_squash": _squash(d["edge_squash_min"]) + iso,
                             "flipped_faces": _flips(d["flipped_fraction"])}
    keys = topo.get("shape_keys", {})
    if keys:
        folded = [k for k, d in keys.items() if d["flipped_fraction"] > 0.002]
        extreme = [k for k, d in keys.items() if d["frac_stretch_gt_2"] + d["frac_squash_lt_half"] > 0.01]
        state["shape_keys"] = {"total": len(keys), "keys_that_fold": folded or "none", "keys_with_extreme_edges": extreme or "none"}
    return state


def questions(topo: dict, order: int = 0) -> dict:
    qs: dict = {}
    for j in topo.get("bend", {}):
        qs[f"bend_clean_{j}"] = {"type": "noul", "instructions":
            f"Looking at `bends.{j}`, would the {j} bend cleanly in animation, with no folded surface, no widespread "
            f"pinching and no widespread stretching? An isolated single stretched edge does not make a bend unclean."}
        qs[f"bend_no_folds_{j}"] = {"type": "noul", "instructions":
            f"Is `bends.{j}` free of faces folding through themselves, meaning flipped faces are none or only a few?"}
    qs["quads_ok"] = {"type": "noul", "instructions":
        "Is the surface described in `surface` clean enough for animation, meaning almost all quads and no n-gons?"}
    qs["quad_shape_ok"] = {"type": "noul", "instructions":
        "Are the quads in `surface` well shaped for deformation (not sheared, not long and thin)?"}
    if topo.get("loops"):
        qs["loops_ok"] = {"type": "noul", "instructions":
            "Does every joint in `joint_loops` have a number of edge loops inside its manual target range?"}
    if topo.get("shape_keys"):
        qs["keys_ok"] = {"type": "noul", "instructions":
            "Do the shape keys in `shape_keys` apply cleanly, with no key folding and no key over-stretching its region?"}
    qs["quality"] = {"type": "score", "instructions":
        "Rate how suitable this topology is for clean deformation in animation, using `surface`, `joint_loops`, `bends` and `shape_keys`.",
        "criteria": [
            "Unusable: surfaces fold or collapse at several joints and most of the mesh is triangles.",
            "Poor: at least one joint folds or stretches strongly, or many triangles sit in bend areas.",
            "Acceptable: joints bend with mild pinching only; quads are mostly clean.",
            "Good: every joint bends cleanly and the surface is almost all quads.",
            "Production ready: clean bends, correct loop counts, almost all quads, shape keys clean."]}
    opts = list(FIXES.items())
    if order:
        opts = opts[::-1]
    qs["first_fix"] = {"type": "choice", "instructions":
        "Which single problem should the modeler fix first to improve deformation?", "criteria": dict(opts)}
    return qs


def ask(topo: dict, label: str, transport: Callable[[dict], dict] = judge.http_transport,
        model: str = judge.MODEL) -> List[Finding]:
    state = build_state(topo)
    out: List[Finding] = []
    answers = []
    try:
        for order in (0, 1):
            answers.append(transport({"model": model, "state": state, "questions": questions(topo, order)})["answers"])
    except Exception as e:  # network, auth, size: the deterministic result stands
        return [Finding(f"topojudge.{label}", "skip", f"TypeSafe unavailable ({e}); deterministic result stands")]
    a = answers[0]
    for name, ans in a.items():
        if ans.get("type") == "noul" or "noul" in ans:
            p = ans["noul"]
            conf = abs(2 * p - 1)  # docs: confidence for a noul is the distance from 0.5
            sev = PASS if p >= 0.6 else (INFO if conf < judge.MIN_CONFIDENCE else WARN)
            out.append(Finding(f"topojudge.{label}.{name}", sev,
                               f"TypeSafe: {name.replace('_', ' ')}" + (" (uncertain, needs a human look)" if conf < judge.MIN_CONFIDENCE else ""),
                               p, ">= 0.60"))
    q = a.get("quality", {})
    if q:
        s, c = q.get("score", 0.0), q.get("confidence", 0.0)
        if c < judge.MIN_CONFIDENCE:
            out.append(Finding(f"topojudge.{label}.review", INFO, f"TypeSafe topology score {s:.1f}/4 has low confidence ({c:.2f}); needs a human or Claude look"))
        else:
            out.append(Finding(f"topojudge.{label}.quality", PASS if s >= 2.5 else WARN, f"TypeSafe topology quality (confidence {c:.2f})", s, ">= 2.5 of 4"))
    f0, f1 = a.get("first_fix", {}), answers[1].get("first_fix", {})
    if f0 and f1:
        agree = f0.get("choice") == f1.get("choice")
        top = f0["choice"] if agree else None
        out.append(Finding(f"topojudge.{label}.first_fix", INFO,
                           f"TypeSafe says fix first: {top} ({FIXES.get(top, '')})" if agree and top != "none" else
                           ("TypeSafe finds nothing to fix first" if agree else
                            f"TypeSafe's first-fix answer changed with option order ({f0['choice']} vs {f1['choice']}); treat as uncertain")))
    return out
