"""Grade metrics against spec bands and the contract in the build prompt."""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from . import measure
from .contract import CHILD_FORBIDDEN, SOCKETS_BY_KIND, REQUIRED_OBJECTS, required_keys
from .model import FAIL, INFO, PASS, SKIP, WARN, Finding, Report, SceneInfo
from .spec import BODY_OBJECTS, METRICS, TRI_BUDGET


def anatomy(scene: SceneInfo, report: Report, relax: float = 1.0) -> Dict[str, float]:
    vals, missing, notes = measure.metrics(scene)
    ungraded = measure.joint_based(scene)
    for key, v in vals.items():
        m = METRICS[key]
        band = m.bands.get(scene.kind)
        if band is None:
            continue
        if key in ungraded:
            report.add(Finding(f"anatomy.{key}", INFO, f"{m.label} measured between joint centres, not graded; place "
                               f"LM-{'shoulder' if 'shoulder' in key else 'hip'}_L/R at the outer points to grade it", v))
            continue
        if relax != 1.0:
            from .spec import Band
            band = Band(band.lo, band.hi, band.slack * relax)
        sev = band.grade(v)
        fix = m.fix_low if v < band.lo else m.fix_high
        report.add(Finding(f"anatomy.{key}", sev, f"{m.label} (per {m.denominator})", v, band.text(), fix, m.source))
    for name in missing:
        report.add(Finding("anatomy.landmark", SKIP, f"landmark '{name}' not found; add an empty named LM-{name} "
                           f"or name the DEF- bones so the validator can find them"))
    for n in notes:
        report.add(Finding("anatomy.note", INFO, n))
    asym = measure.per_side_asymmetry(scene)
    if asym is not None:
        sev = PASS if asym <= 0.05 else WARN if asym <= 0.12 else FAIL
        report.add(Finding("anatomy.symmetry", sev, "left/right joint height difference", asym, "<= 0.05 head",
                           "Mirror the rig or fix the offset joint."))
    report.metrics.update(vals)
    return vals


def contract(scene: SceneInfo, report: Report) -> None:
    kind = scene.kind
    arm, body = BODY_OBJECTS[kind]
    for name in REQUIRED_OBJECTS.get(kind, (arm, body)):
        report.add(Finding("contract.object", PASS if name in scene.objects else FAIL,
                           f"object {name}" + ("" if name in scene.objects else " is missing")))

    # Sockets
    want = SOCKETS_BY_KIND.get(kind, ())
    have = scene.socket_names()
    missing = [s for s in want if s not in have]
    report.add(Finding("contract.sockets", FAIL if missing else PASS,
                       f"{len(want) - len(missing)}/{len(want)} sockets present" +
                       (f"; missing {', '.join(missing[:8])}{'...' if len(missing) > 8 else ''}" if missing else "")))
    bad_prop = [s for s in have if scene.custom_props.get(s, {}).get("socket_name") not in (None, s)]
    nop = [s for s in have if scene.custom_props and "socket_name" not in scene.custom_props.get(s, {})]
    if bad_prop or nop:
        report.add(Finding("contract.socket_name", WARN,
                           f"{len(bad_prop) + len(nop)} sockets lack a matching socket_name property"))

    # Bones
    stray = sorted(b for b in scene.deform_bones if not b.startswith("DEF-"))
    report.add(Finding("contract.bone_prefix", FAIL if stray else PASS,
                       "all deform bones use DEF-" if not stray else f"deform bones without DEF-: {', '.join(stray[:6])}"))

    # Shape keys
    keys = set(scene.shape_keys.get(body, []))
    if scene.shape_keys.get(body) is not None:
        stray_keys = sorted(k for k in keys if k != "Basis" and not k.startswith(("ID-", "PF-")))
        report.add(Finding("contract.key_prefix", FAIL if stray_keys else PASS,
                           "shape keys use ID-/PF-" if not stray_keys else f"unprefixed keys: {', '.join(stray_keys[:6])}"))
        req = required_keys(kind)
        gone = sorted(req - keys)
        report.add(Finding("contract.keys", FAIL if gone else PASS,
                           f"{len(req) - len(gone)}/{len(req)} required keys present" +
                           (f"; missing {', '.join(gone[:10])}{'...' if len(gone) > 10 else ''}" if gone else "")))
        if kind == "child":
            bad = sorted(keys & set(CHILD_FORBIDDEN))
            report.add(Finding("contract.child_keys", FAIL if bad else PASS,
                               "no adult-only keys on the child" if not bad else f"adult-only keys on child: {', '.join(bad)}",
                               fix="Delete these keys; the child has no presentation, muscle or facial-hair controls."))
    else:
        report.add(Finding("contract.keys", SKIP, f"no shape-key data for {body}"))

    # Budget
    lo, hi = TRI_BUDGET[kind]
    t = scene.tris.get(body)
    if t is None:
        report.add(Finding("contract.budget", SKIP, f"no triangle count for {body}"))
    else:
        sev = PASS if lo <= t <= hi else WARN if lo * 0.85 <= t <= hi * 1.1 else FAIL
        report.add(Finding("contract.budget", sev, f"{body} triangles", float(t), f"{lo}..{hi}",
                           "Add density in face/hands/joints." if t < lo else "Decimate flat areas; keep the loops."))
    q = scene.quad_ratio.get(body)
    if q is not None:
        report.add(Finding("contract.quads", PASS if q >= 0.9 else WARN if q >= 0.8 else FAIL,
                           "quad ratio (manual s13: quads throughout)", q, ">= 0.90",
                           "Retopologise triangles/n-gons out of bend areas."))

    # Transforms applied, origin, forward axis
    tr = scene.transforms.get(body)
    if tr:
        s_off = max(abs(c - 1.0) for c in tr["scale"])
        r_off = max(abs(c) for c in tr["rotation"])
        report.add(Finding("contract.transforms", PASS if s_off < 1e-3 and r_off < 1e-3 else FAIL,
                           f"{body} scale/rotation applied", max(s_off, r_off), "0", "Ctrl+A > All Transforms on the base mesh."))
    verts = scene.body_verts
    if verts:
        zmin = min(v[2] for v in verts)
        cx = (min(v[0] for v in verts) + max(v[0] for v in verts)) / 2
        cy = (min(v[1] for v in verts) + max(v[1] for v in verts)) / 2
        ok = abs(zmin) <= 0.01 and abs(cx) <= 0.05 and abs(cy) <= 0.15
        report.add(Finding("contract.origin", PASS if ok else FAIL,
                           f"origin at the floor between the feet (lowest z {zmin:.3f}, centre x {cx:.3f})",
                           fix="Move the mesh so soles sit on z=0 and the feet are centred on x=0."))
        lm, _ = measure.landmarks(scene)
        eyes = [lm[k][1] for k in ("EyeInner_L", "EyeInner_R") if k in lm]
        if eyes and kind in ("adult", "child"):
            head = [v[1] for v in verts if "Chin" in lm and v[2] >= lm["Chin"][2]]
            if head:
                mid = (min(head) + max(head)) / 2
                report.add(Finding("contract.forward", PASS if sum(eyes) / len(eyes) < mid else FAIL,
                                   "character faces -Y", fix="Rotate 180 degrees about Z and apply."))
