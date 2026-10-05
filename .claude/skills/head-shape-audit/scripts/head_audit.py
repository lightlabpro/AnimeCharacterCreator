"""Head shape audit for Blender (also runs in plain Python for testing).

Measures the head mesh exactly (no renders, no guessing) and compares it with the reference head profile.
Run inside Blender: open the Text Editor, paste or open this file, set the names below, Run Script.
Blender convention: +Z up, forward = -Y, 1 unit = 1 m. The mesh must have its transforms applied or be evaluated.

Landmarks (create two empties, move them once, leave them alone):
    LM_top   at the highest point of the skull (not the hair)
    LM_chin  at the chin tip
Everything is divided by head height H = LM_top.z - LM_chin.z, so scale and units do not matter.

Targets come from knowledge/head-targets.json (measured from Sammy's reference head). If you can open
that reference mesh in Blender, run this script on it first and paste ITS output over TARGETS: exact beats
the screenshot-derived numbers below.
"""
import json, sys

HEAD_OBJECTS = ["CHR_Body", "CHR_Head"]       # meshes that carry the skull, jaw and nose (not hair, not eyes, not ears)
TOL = 0.04                                      # allowed difference, in head heights
BAND = 0.006                                    # half thickness of each slice, in head heights

TARGETS = {  # fractions of H, 0 = top of skull, 1 = chin tip
    "width": {"0.1": 0.479, "0.15": 0.550, "0.2": 0.579, "0.25": 0.579, "0.3": 0.570, "0.75": 0.410, "0.8": 0.372, "0.85": 0.289, "0.9": 0.266, "0.95": 0.189},
    "behind_nose": {"0.1": 0.225, "0.2": 0.144, "0.3": 0.111, "0.4": 0.087, "0.8": 0.057, "0.9": 0.114},
    "skull_depth_0.3": 0.799,
    "width_to_depth": 0.72,
}

FIX = {  # what to do when a row is out, in the order a modeler works
    "crown_wide": "Crown too wide at the top: round the top of the skull in, so the head is not a flat dome.",
    "crown_narrow": "Crown too narrow at the top (pointed egg): fill out the top of the skull at 0.1-0.15H so it reads as a round cranium.",
    "cranium_wide": "Cranium too wide: scale the skull in X only (proportional editing, falloff large), keep depth. Target width 0.58H at 0.25H down from the top.",
    "cranium_narrow": "Cranium too narrow: widen the temples at 0.2-0.3H, not the whole head.",
    "skull_shallow": "Skull too shallow front to back: push the back of the cranium out in Y. The head is deeper than it is wide (depth 0.80H, width 0.58H).",
    "skull_deep": "Skull too deep: pull the back of the cranium in.",
    "jaw_wide": "Jaw/chin too wide: pull the jaw corners in at 0.75-0.9H, keep the chin tip.",
    "jaw_narrow": "Jaw/chin too narrow: widen the jaw corners at 0.75-0.85H.",
    "forehead_back": "Forehead recedes: move the brow and forehead forward (-Y) at 0.2-0.3H until it is about 0.11H behind the nose tip.",
    "chin_back": "Chin recedes or nose is too long: bring the chin forward at 0.9H to about 0.11H behind the nose tip, or shorten the nose.",
    "chin_forward": "Chin juts out: pull the chin back.",
    "nose_short": "Forehead sits further forward than the reference relative to the nose: lengthen the nose or raise its bridge and tip forward (nose tip should stand about 0.11H ahead of the forehead at 0.3H), or flatten the brow.",
}

def profile_from_points(pts, top_z, chin_z, forward_sign=-1):
    """pts: iterable of (x, y, z) in head space. Returns the profile dict. forward_sign = -1 for Blender (-Y forward)."""
    import numpy as np
    P = np.asarray(pts, dtype=float)
    H = top_z - chin_z
    out = {"H": H, "width": {}, "behind_nose": {}}
    def band(f):
        z = top_z - f * H
        return P[np.abs(P[:, 2] - z) <= BAND * H]
    for f in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.75, 0.8, 0.85, 0.9, 0.95]:
        b = band(f)
        out["width"][str(f)] = round(float(b[:, 0].max() - b[:, 0].min()) / H, 3) if len(b) else None
    # nose tip: the most forward point between 0.5H and 0.85H
    mid = P[(P[:, 2] <= top_z - 0.5 * H) & (P[:, 2] >= top_z - 0.85 * H)]
    fwd = forward_sign * mid[:, 1]
    nose = float(fwd.max())
    for f in [0.1, 0.2, 0.3, 0.4, 0.6, 0.8, 0.9]:
        b = band(f)
        out["behind_nose"][str(f)] = round((nose - float((forward_sign * b[:, 1]).max())) / H, 3) if len(b) else None
    b = band(0.3)
    fz = forward_sign * b[:, 1]
    out["skull_depth_0.3"] = round(float(fz.max() - fz.min()) / H, 3) if len(b) else None
    w = np.mean([out["width"][k] for k in ("0.2", "0.25", "0.3") if out["width"][k]])
    out["width_to_depth"] = round(float(w) / out["skull_depth_0.3"], 3) if out["skull_depth_0.3"] else None
    return out

def verdict(prof, targets=TARGETS, tol=TOL):
    bad, rows = [], []
    def chk(name, got, want, fix_if_pos, fix_if_neg, t=tol):
        if got is None or want is None: return
        d = got - want
        rows.append(f"  {name:<22} target {want:6.3f}  got {got:6.3f}  {d:+.3f}  {'OUT' if abs(d) > t else 'ok'}")
        if abs(d) > t: bad.append(fix_if_pos if d > 0 else fix_if_neg)
    for f in ("0.1", "0.15"):
        chk(f"width@{f}", prof["width"].get(f), targets["width"].get(f), "crown_wide", "crown_narrow")
    for f in ("0.2", "0.25", "0.3"):
        chk(f"width@{f}", prof["width"].get(f), targets["width"].get(f), "cranium_wide", "cranium_narrow")
    for f in ("0.75", "0.8", "0.85", "0.9", "0.95"):
        chk(f"width@{f}", prof["width"].get(f), targets["width"].get(f), "jaw_wide", "jaw_narrow")
    chk("skull_depth@0.3", prof["skull_depth_0.3"], targets["skull_depth_0.3"], "skull_deep", "skull_shallow")
    for f in ("0.2", "0.3"):
        chk(f"behind_nose@{f}", prof["behind_nose"].get(f), targets["behind_nose"].get(f), "forehead_back", "nose_short")
    chk("behind_nose@0.9", prof["behind_nose"].get("0.9"), targets["behind_nose"].get("0.9"), "chin_back", "chin_forward")
    chk("width:depth", prof["width_to_depth"], targets["width_to_depth"], "cranium_wide", "skull_shallow", 0.08)
    return bad, rows

def report(prof):
    bad, rows = verdict(prof)
    print("HEAD AUDIT  (fractions of head height, 0 = skull top, 1 = chin)")
    print("\n".join(rows))
    if bad:
        print("\nHEAD_SHAPE_FAIL. Fix in this order:")
        for k in dict.fromkeys(bad): print(" - " + FIX[k])
        print("Do not judge shading, outlines or colour until this passes: lighting follows the form.")
    else:
        print("\nHEAD_SHAPE_OK")
    print("\nBRIDGE-ENTRY\nside: chat\nkind: learning\ntopic: head audit\nfinding: " + ("fail: " + ", ".join(dict.fromkeys(bad)) if bad else "pass") + "\nevidence: " + json.dumps({k: prof[k] for k in ("width_to_depth", "skull_depth_0.3")}) + "\nstatus: confirmed\nuse: Code, none unless the targets need re-measuring")
    return not bad

def run_in_blender():
    import bpy
    from mathutils import Vector
    top, chin = bpy.data.objects.get("LM_top"), bpy.data.objects.get("LM_chin")
    if not top or not chin: raise SystemExit("Create two empties named LM_top (skull top) and LM_chin (chin tip), then run again.")
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for name in HEAD_OBJECTS:
        o = bpy.data.objects.get(name)
        if not o: continue
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        pts += [tuple(ev.matrix_world @ v.co) for v in me.vertices]
        ev.to_mesh_clear()
    if not pts: raise SystemExit(f"None of {HEAD_OBJECTS} found. Edit HEAD_OBJECTS at the top of the script.")
    # keep only the head region: above the chin landmark minus a little for the jaw underside
    H = top.matrix_world.translation.z - chin.matrix_world.translation.z
    pts = [p for p in pts if p[2] >= chin.matrix_world.translation.z - 0.02 * H]
    prof = profile_from_points(pts, top.matrix_world.translation.z, chin.matrix_world.translation.z, -1)
    print(json.dumps(prof, indent=1)); ok = report(prof)
    bad, _ = verdict(prof)
    out = bpy.path.abspath("//head_audit.json")
    with open(out, "w") as f: json.dump({"ok": ok, "bad": [FIX[k] for k in dict.fromkeys(bad)], "profile": prof}, f, indent=2)
    print("wrote", out, "for validate.py measure --head-audit")

if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
        run_in_blender()
    except ImportError:
        print("Not inside Blender. Import profile_from_points / report to use the pure functions.")
