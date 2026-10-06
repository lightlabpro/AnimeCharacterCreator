"""Archetype distinctness with TypeSafe (Choice).

Phase 11 gate: rabbit, dinosaur, rhino, lizard and tiger must be distinct from each other. The element looks and the measured traits
of a character are turned into words, and one Choice (asked in two option orders) names which of the archetypes it reads as. If the
declared archetype is not the answer, or the runner-up is close (top-to-second ratio, the measure the TypeSafe docs recommend for
close calls), the preset is not distinct enough. Descriptions come from the per-archetype sheet in docs/anatomy-manual.md section 10.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from . import judge
from .model import FAIL, INFO, PASS, WARN, Finding

SHEET: Dict[str, str] = {
    "human": "Flat face, no muzzle, human ears and hands, no tail, skin.",
    "tiger": "Short broad muzzle with cheek ruff, rounded ears, long thick ringed tail, short fur with vertical stripes.",
    "lion": "Short broad muzzle, small rounded ears hidden by a mane, tufted tail, plain tawny short fur.",
    "fish": "Wide lipless mouth, fin-like ear fans, webbed hands, caudal fin tail, overlapping scales.",
    "dog": "Long muzzle with a stop, upright or floppy ears, medium brushy tail, fur with masks or saddle.",
    "dragon": "Long reptile snout with horns, frills or fins for ears, long tapering tail, large plates, wings.",
    "bird": "Beak cone, feather tufts, feathered wings, scaly digitigrade legs, tail feathers, feathers.",
    "frog": "Wide flat head, huge mouth line, bulging eyes high on the head, long jumping legs, no tail, thin smooth skin.",
    "serpent": "Narrow wedge head, no external ears, slit pupils, very long tail as the main feature, fine scales.",
    "rabbit": "Short muzzle, very long narrow ears, big hind feet, short puff tail, soft fur.",
    "dinosaur": "Deep skull with big jaw, hole-only ears, strong digitigrade legs, heavy counterbalancing tail, crest, pebbled scales, short arms.",
    "rhino": "Long heavy head with nasal horn or horns, small ears, near-hoofed pillar legs, short thin tail, thick folded hide.",
    "lizard": "Flat triangular head with small snout, ear holes, sprawling legs, long tapering tail, small scales, optional neck frill.",
}

DESCRIPTORS = {
    "muzzle": {"none": "no muzzle", "feline": "a short broad cat muzzle", "canine": "a long dog muzzle", "reptile": "a long reptile snout", "fish": "a wide lipless fish mouth",
               "bird": "a beak", "frog": "a wide flat frog mouth", "lagomorph": "a short rabbit muzzle", "heavy": "a long heavy head"},
    "ears": {"human": "human ears", "round": "round ears", "pointed": "pointed ears", "long": "very long narrow ears", "fin": "fin-like ears", "feathered": "feather tufts for ears", "none": "no external ears"},
    "tail": {"none": "no tail", "feline": "a long thick cat tail", "canine": "a medium brushy tail", "lizard": "a long tapering lizard tail", "fish": "a fish tail fin",
             "bird": "tail feathers", "serpent": "a very long serpent tail", "puff": "a short puff tail"},
    "surface": {"skin": "bare skin", "shortFur": "short fur", "longFur": "long fur", "scales": "scales", "feathers": "feathers", "amphibian": "thin smooth moist skin", "thickHide": "thick folded hide"},
    "horns": {"none": "no horns", "straight": "a straight pair of horns", "curved": "curved horns", "swept": "swept back horns", "nose": "a horn on the nose"},
    "wings": {"none": "no wings", "feathered": "feathered wings", "membrane": "membrane wings", "fin": "fin wings"},
    "mane": {"none": "no mane or crest", "mane": "a mane", "crest": "a crest", "feathers": "head feathers"},
    "pattern": {"plain": "a plain coat", "stripes": "vertical stripes", "spots": "spots", "plates": "plates"},
    "feet": {"human": "human feet", "paw": "paws", "webbed": "webbed feet", "talon": "talons"},
    "legs": {"plantigrade": "plantigrade legs", "digitigrade": "digitigrade legs"},
}


# What a slot means when a recipe leaves it unset: absent traits must be stated, or the judge cannot tell a lizard from a dragon.
DEFAULTS = {"muzzle": "none", "ears": "human", "tail": "none", "surface": "skin", "horns": "none", "wings": "none", "mane": "none",
            "pattern": "plain", "feet": "human", "legs": "plantigrade"}


def describe(looks: Dict[str, str]) -> Dict[str, object]:
    """looks: slot -> look id; the optional key "extra" holds free-text traits that are not look slots (docs recipes)."""
    full = {**DEFAULTS, **{k: v for k, v in looks.items() if k != "extra"}}
    out: Dict[str, object] = {slot: DESCRIPTORS[slot].get(v, v) for slot, v in full.items() if slot in DESCRIPTORS}
    if looks.get("extra"):
        out["other_traits"] = looks["extra"]
    return out


def classify(looks: Dict[str, str], declared: str, transport: Callable[[dict], dict] = judge.http_transport,
             model: str = judge.MODEL) -> List[Finding]:
    state = {"character_traits": describe(looks)}
    crit = dict(SHEET)
    def q(rev):
        items = list(crit.items())
        return {"archetype": {"type": "choice", "instructions": "Which archetype do `character_traits` describe? Judge by the traits only.",
                              "criteria": dict(items[::-1] if rev else items)}}
    try:
        a = transport({"model": model, "state": state, "questions": q(False)})["answers"]["archetype"]
        b = transport({"model": model, "state": state, "questions": q(True)})["answers"]["archetype"]
    except Exception as e:
        return [Finding("archetype.silhouette.skip", "skip", f"TypeSafe unavailable ({e})")]
    pa, pb = a["probabilities"], b["probabilities"]
    avg = {k: (pa[k] + pb[k]) / 2 for k in pa}
    ranked = sorted(avg.items(), key=lambda kv: -kv[1])
    top, second = ranked[0], ranked[1]
    ratio = top[1] / max(second[1], 1e-6)
    agree = a["choice"] == b["choice"]
    out = []
    if not agree:
        out.append(Finding("archetype.silhouette.order", WARN, f"archetype answer changed with option order ({a['choice']} vs {b['choice']}); the traits are ambiguous"))
    if top[0] == declared and ratio >= 2.0:
        sev, msg = PASS, f"reads clearly as {declared} (next closest: {second[0]})"
    elif top[0] == declared:
        sev, msg = WARN, f"reads as {declared} but {second[0]} is close (top/second ratio {ratio:.1f}); add a distinguishing element"
    else:
        sev, msg = FAIL, f"declared {declared} but the traits read as {top[0]} (next: {second[0]}); change the element mix"
    out.append(Finding("archetype.silhouette.distinct", sev, f"{declared}: {msg}", top[1], "declared archetype is top and >= 2x the runner-up",
                       "Use the recipe for this archetype (docs/CHARACTER_MAKER.md) so it differs from its neighbours.", "TypeSafe choice, two option orders"))
    return out
