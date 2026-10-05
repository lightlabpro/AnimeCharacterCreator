#!/usr/bin/env python3
"""Body proportion audit: measure reference models, derive targets, check candidates against them.

Reference models (the MHS3-style characters Sammy has) are measured with real numbers instead of eyeballing:
    measure            glTF/GLB, plain Python + numpy: joints from the skin, vertices from the mesh
    blender-measure    inside Blender (or the bpy module): any importable file (.fbx .glb .gltf .blend) or the open scene
    targets            several profiles -> knowledge/body-targets.json (min/max band per metric, widened)
    check              a candidate (GLB or profile json) against the targets. Exit 0 pass, 12 fail, 13 unknown, 2 usage.

Conventions: Z up, forward -Y, feet near z=0 (glTF Y-up is converted). Every length is divided by body height H
(top of the body mesh minus its lowest point), so units and scale do not matter. Joints are bone heads at rest.
Metrics are only compared when BOTH sides have them; a missing metric is UNKNOWN, never a pass.
"""
import argparse, base64, json, math, os, re, struct, sys

EXIT_PASS, EXIT_FAIL, EXIT_UNKNOWN, EXIT_USAGE = 0, 12, 13, 2
SKIP_MESH = re.compile(r"hair|brow|lash|eye|teeth|tongue|cloth|cape|weapon|sword|shield|accessor|wet|outline|hat|helmet|glasses", re.I)

# ---------------------------------------------------------------- names
JOINT_WORDS = {
    "head": "head", "neck": "neck", "hips": "pelvis", "pelvis": "pelvis", "spine": "spine", "chest": "spine", "upperchest": "spine",
    "thigh": "thigh", "upleg": "thigh", "upperleg": "thigh", "leg": "shin", "shin": "shin", "calf": "shin", "lowerleg": "shin",
    "foot": "foot", "toes": "toe", "toe": "toe", "toebase": "toe", "ball": "toe",
    "upperarm": "upper_arm", "arm": "upper_arm", "forearm": "forearm", "lowerarm": "forearm", "hand": "hand",
    "shoulder": "clavicle", "clavicle": "clavicle",
}
def canon(name):
    """'DEF-upper_arm.L' / 'mixamorig:LeftForeArm' / 'J_Bip_L_UpperArm' -> ('upper_arm', 'L'). Returns (None, None) if not a body joint."""
    s = name.split(":")[-1]
    s = re.sub(r"^(def|mch|org|tweak|ctrl|j_bip|j_adj)[-_.]", "", s, flags=re.I)
    s = re.sub(r"([a-z])([A-Z])", r"\1_\2", s)                       # CamelCase -> Camel_Case
    low = s.lower()
    side = None
    toks = [t for t in re.split(r"[._\-\s]+", low) if t]
    if toks and toks[0] in ("l", "left", "r", "right"):
        side, toks = ("L" if toks[0][0] == "l" else "R"), toks[1:]
    elif toks and toks[-1] in ("l", "left", "r", "right"):
        side, toks = ("L" if toks[-1][0] == "l" else "R"), toks[:-1]
    toks = [t for t in toks if not t.isdigit() and t not in ("j", "bip", "c", "g")]
    key = "".join(toks)
    j = JOINT_WORDS.get(key)
    return (j, side) if j else (None, None)

def pick_joints(raw):
    """raw: {authored bone name: (x,y,z)} -> {'upper_arm_L': xyz, 'head': xyz, ...}. Duplicates: first pick wins by lowest name,
    except spine (several bones): pelvis = hips/pelvis else the lowest spine bone, 'chest' = the highest."""
    out, spines = {}, []
    for name in sorted(raw):
        j, side = canon(name)
        if not j or "twist" in name.lower() or "roll" in name.lower(): continue
        p = tuple(float(v) for v in raw[name])
        if j == "spine": spines.append((p[2], p)); continue
        key = f"{j}_{side}" if side else j
        out.setdefault(key, p)
    if spines:
        spines.sort(); out.setdefault("pelvis", spines[0][1]); out["chest"] = spines[-1][1]
    return out

# ---------------------------------------------------------------- measuring
def _d(a, b): return math.dist(a, b)

def slice_width(V, T, z, axis):
    import numpy as np
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    pts = []
    for p, q in ((a, b), (b, c), (c, a)):
        dz = q[:, 2] - p[:, 2]
        hit = ((p[:, 2] - z) * (q[:, 2] - z) <= 0) & (np.abs(dz) > 1e-12)
        if hit.any():
            t = (z - p[hit, 2]) / dz[hit]
            pts.append(p[hit, axis] + (q[hit, axis] - p[hit, axis]) * t)
    if not pts: return None
    P = np.concatenate(pts)
    return float(P.max() - P.min())

def mirror_p95(V, n=1500):
    """95th percentile of the distance from a mirrored (x -> -x) sample point to the nearest surface vertex, in metres."""
    import numpy as np
    rng = np.random.default_rng(0)
    S = V[rng.choice(len(V), min(n, len(V)), replace=False)] * np.array([-1, 1, 1])
    W = V[rng.choice(len(V), min(4000, len(V)), replace=False)]
    d = np.concatenate([np.sqrt(((S[i:i + 250, None, :] - W[None]) ** 2).sum(-1)).min(1) for i in range(0, len(S), 250)])
    return float(np.percentile(d, 95))

def measure(V, T, raw_joints, name="model"):
    """Returns {'name', 'height', 'metrics': {...}, 'joints_found': [...], 'notes': [...]} with every length divided by height."""
    import numpy as np
    V = np.asarray(V, float); T = np.asarray(T, int)
    zmin, zmax = float(V[:, 2].min()), float(V[:, 2].max()); H = zmax - zmin
    J = pick_joints(raw_joints); m, notes = {}, []
    if H <= 0: raise ValueError("mesh has no height")
    zf = lambda k: (J[k][2] - zmin) / H if k in J else None
    def both(k, f):
        vals = [f(J[f"{k}_{s}"]) for s in "LR" if f"{k}_{s}" in J]
        return sum(vals) / len(vals) if vals else None
    z = lambda p: (p[2] - zmin) / H
    for key, jn in (("shoulder_z", "upper_arm"), ("elbow_z", "forearm"), ("wrist_z", "hand"), ("hip_z", "thigh"), ("knee_z", "shin"), ("ankle_z", "foot")):
        v = both(jn, z)
        if v is not None: m[key] = v
    if "neck" in J: m["neck_z"] = zf("neck"); m["head_to_top"] = 1.0 - zf("neck")
    elif "head" in J: m["neck_z"] = zf("head"); m["head_to_top"] = 1.0 - zf("head"); notes.append("neck joint missing, used the head joint")
    if "pelvis" in J: m["pelvis_z"] = zf("pelvis")
    for a, b, c, key in (("thigh", "shin", "foot", "thigh_over_shin"), ("upper_arm", "forearm", "hand", "upper_over_fore")):
        r = []
        for s in "LR":
            if all(f"{k}_{s}" in J for k in (a, b, c)):
                r.append(_d(J[f"{a}_{s}"], J[f"{b}_{s}"]) / max(_d(J[f"{b}_{s}"], J[f"{c}_{s}"]), 1e-9))
        if r: m[key] = sum(r) / len(r)
    arms = [(_d(J[f"upper_arm_{s}"], J[f"forearm_{s}"]) + _d(J[f"forearm_{s}"], J[f"hand_{s}"])) / H for s in "LR" if all(f"{k}_{s}" in J for k in ("upper_arm", "forearm", "hand"))]
    if arms: m["arm_length"] = sum(arms) / len(arms)
    for key, jn in (("shoulder_width", "upper_arm"), ("hip_width", "thigh"), ("ankle_width", "foot")):
        if f"{jn}_L" in J and f"{jn}_R" in J: m[key] = _d(J[f"{jn}_L"], J[f"{jn}_R"]) / H
    sym = []
    for jn in ("upper_arm", "forearm", "hand", "thigh", "shin", "foot"):
        if f"{jn}_L" in J and f"{jn}_R" in J:
            L, R = J[f"{jn}_L"], J[f"{jn}_R"]
            sym.append(max(abs(L[0] + R[0]), abs(L[1] - R[1]), abs(L[2] - R[2])) / H)
    if sym: m["rig_asymmetry"] = max(sym)
    # mesh slices at joint heights (width = x extent, depth = y extent), same fractions on every model
    def sl(zz, axis):
        w = slice_width(V, T, zmin + zz * H, axis); return None if w is None else w / H
    if "shoulder_z" in m and "hip_z" in m:
        waist = m["hip_z"] + 0.35 * (m["shoulder_z"] - m["hip_z"])
        for key, zz, ax in (("width_at_shoulder", m["shoulder_z"], 0), ("width_at_hip", m["hip_z"], 0), ("width_at_waist", waist, 0), ("depth_at_waist", waist, 1)):
            v = sl(zz, ax)
            if v is not None: m[key] = v
        if "width_at_waist" in m and "width_at_hip" in m: m["waist_over_hip"] = m["width_at_waist"] / m["width_at_hip"]
    if "ankle_z" in m:
        low = V[V[:, 2] < zmin + m["ankle_z"] * H]
        if len(low) > 10: m["foot_length"] = float(low[:, 1].max() - low[:, 1].min()) / H
    m["mirror_p95"] = mirror_p95(V) / H
    m["centre_offset"] = abs(float((V[:, 0].max() + V[:, 0].min()) / 2)) / H
    return {"name": name, "height": H, "metrics": {k: round(float(v), 5) for k, v in m.items() if v is not None},
            "joints_found": sorted(J), "notes": notes}

# ---------------------------------------------------------------- targets and check
ABS_CEILING = {"rig_asymmetry": 0.006, "mirror_p95": 0.012, "centre_offset": 0.01}   # properties, not reference-dependent
ONE_SIDED = set(ABS_CEILING)
MIN_MARGIN = 0.012      # never tighter than this in H (or ratio units): measurement noise from pose and mesh differences

FIX = {
    "head_to_top": ("head too small for the body (or body too tall)", "head too large for the body"),
    "neck_z": ("neck joint too low: shoulders/torso too short", "neck joint too high: torso too long"),
    "shoulder_z": ("shoulders too low", "shoulders too high"),
    "elbow_z": ("elbows too low: upper arm too long", "elbows too high: upper arm too short"),
    "wrist_z": ("wrists too low: arms too long", "wrists too high: arms too short"),
    "hip_z": ("hip joints too low: legs too short", "hip joints too high: legs too long"),
    "knee_z": ("knees too low", "knees too high"),
    "ankle_z": ("ankles too low: feet sunk or too flat", "ankles too high"),
    "pelvis_z": ("pelvis too low", "pelvis too high"),
    "thigh_over_shin": ("thigh short vs shin", "thigh long vs shin"),
    "upper_over_fore": ("upper arm short vs forearm", "upper arm long vs forearm"),
    "arm_length": ("arms too short", "arms too long"),
    "shoulder_width": ("shoulders too narrow", "shoulders too wide"),
    "hip_width": ("hips too narrow", "hips too wide"),
    "ankle_width": ("feet too close", "feet too far apart"),
    "width_at_shoulder": ("body too narrow at the shoulder line", "body too wide at the shoulder line"),
    "width_at_hip": ("body too narrow at the hips", "body too wide at the hips"),
    "width_at_waist": ("waist too narrow", "waist too wide"),
    "depth_at_waist": ("torso too shallow front to back", "torso too deep front to back"),
    "waist_over_hip": ("waist too small vs hips", "waist too big vs hips"),
    "foot_length": ("feet too short", "feet too long"),
    "rig_asymmetry": (None, "left and right joints are not mirrored: fix bone positions so L = mirror of R (x, y, z)"),
    "mirror_p95": (None, "mesh is not left/right symmetric: mirror the modeled half or run Symmetrize, check for stray vertices"),
    "centre_offset": (None, "body is off-centre: centre the mesh on x = 0 and apply transforms"),
}

def build_targets(profiles, style="", rel=0.06):
    names, out = [p["name"] for p in profiles], {}
    for k in sorted({k for p in profiles for k in p["metrics"]} - ONE_SIDED):
        vals = [p["metrics"][k] for p in profiles if k in p["metrics"]]
        lo, hi, mean = min(vals), max(vals), sum(vals) / len(vals)
        mg = max(rel * abs(mean), 0.25 * (hi - lo), MIN_MARGIN if k.endswith(("_z", "width", "_length", "to_top")) or "width" in k or "depth" in k else 0.03)
        out[k] = {"lo": round(lo - mg, 5), "hi": round(hi + mg, 5), "mean": round(mean, 5), "n": len(vals)}
    return {"note": "bands are fractions of body height H (ratios for *_over_*). Built from measured reference models; "
                    "n=1 uses a +-%d%% band. Regenerate with body_audit.py targets." % round(rel * 100),
            "style": style, "references": names, "metrics": out, "ceilings": ABS_CEILING}

def check(profile, targets):
    """-> (status, rows). status 'pass' | 'fail' | 'unknown'. Rows: (metric, value or None, lo, hi, state, message)."""
    rows, bad, unk = [], 0, 0
    m = profile["metrics"]
    for k, t in sorted(targets["metrics"].items()):
        v = m.get(k)
        if v is None:
            rows.append((k, None, t["lo"], t["hi"], "unknown", "not measurable on this model (missing joint or slice)")); unk += 1; continue
        if v < t["lo"]: rows.append((k, v, t["lo"], t["hi"], "fail", FIX.get(k, ("too low", "too high"))[0])); bad += 1
        elif v > t["hi"]: rows.append((k, v, t["lo"], t["hi"], "fail", FIX.get(k, ("too low", "too high"))[1])); bad += 1
        else: rows.append((k, v, t["lo"], t["hi"], "ok", ""))
    for k, c in sorted(targets.get("ceilings", ABS_CEILING).items()):
        v = m.get(k)
        if v is None: rows.append((k, None, 0, c, "unknown", "not measured")); unk += 1
        elif v > c: rows.append((k, v, 0, c, "fail", FIX[k][1])); bad += 1
        else: rows.append((k, v, 0, c, "ok", ""))
    return ("fail" if bad else "unknown" if unk else "pass"), rows

def format_report(profile, status, rows):
    L = [f"BODY PROPORTIONS {profile['name']}: {status.upper()}  (H = {profile['height']:.3f} units)"]
    for k, v, lo, hi, st, msg in rows:
        L.append(f"  {st.upper():7s} {k:18s} {'-' if v is None else f'{v:.3f}':>7s}  band {lo:.3f}..{hi:.3f}  {msg}")
    return "\n".join(L)

# ---------------------------------------------------------------- glTF loader (no Blender)
_COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

def _buffers(g, bin_chunk, base):
    out = []
    for b in g.get("buffers", []):
        u = b.get("uri")
        if u is None: out.append(bin_chunk)
        elif u.startswith("data:"): out.append(base64.b64decode(u.split(",", 1)[1]))
        else:
            with open(os.path.join(base, u), "rb") as f: out.append(f.read())
    return out

def _accessor(g, bufs, i):
    import numpy as np
    a = g["accessors"][i]; bv = g["bufferViews"][a["bufferView"]]
    fmt, size = _COMP[a["componentType"]]; n = _NCOMP[a["type"]]
    stride = bv.get("byteStride") or size * n
    data = bufs[bv["buffer"]]; off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    dt = np.dtype(fmt).newbyteorder("<")
    arr = np.ndarray((a["count"], n), dtype=dt, buffer=data, offset=off, strides=(stride, size)) if stride != size * n else \
        np.frombuffer(data, dtype=dt, count=a["count"] * n, offset=off).reshape(a["count"], n)
    return np.array(arr)

def _mat(n):
    import numpy as np
    if "matrix" in n: return np.array(n["matrix"], float).reshape(4, 4).T
    t = n.get("translation", [0, 0, 0]); q = n.get("rotation", [0, 0, 0, 1]); s = n.get("scale", [1, 1, 1])
    x, y, z, w = q
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R * np.array(s); M[:3, 3] = t
    return M

def load_gltf(path):
    """-> (V Nx3 Z-up, T Mx3, {bone name: xyz}) for the body meshes. Skips meshes whose node name matches SKIP_MESH."""
    import numpy as np
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "library-pack-check", "scripts"))
    from check_pack import read_gltf
    g, chunk = read_gltf(path); bufs = _buffers(g, chunk, os.path.dirname(os.path.abspath(path)))
    nodes = g.get("nodes", []); parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}
    cache = {}
    def world(i):
        if i not in cache: cache[i] = (world(parent[i]) if i in parent else np.eye(4)) @ _mat(nodes[i])
        return cache[i]
    zup = lambda P: np.stack([P[:, 0], -P[:, 2], P[:, 1]], 1)           # glTF Y-up -> Blender Z-up
    Vs, Ts, off = [], [], 0
    for i, n in enumerate(nodes):
        if "mesh" not in n or SKIP_MESH.search(n.get("name", "")): continue
        for prim in g["meshes"][n["mesh"]]["primitives"]:
            if "POSITION" not in prim.get("attributes", {}): continue
            P = _accessor(g, bufs, prim["attributes"]["POSITION"]).astype(float)
            if "skin" not in n: P = (world(i) @ np.c_[P, np.ones(len(P))].T).T[:, :3]
            idx = _accessor(g, bufs, prim["indices"]).reshape(-1) if "indices" in prim else np.arange(len(P))
            Vs.append(zup(P)); Ts.append(idx.reshape(-1, 3).astype(int) + off); off += len(P)
    if not Vs: raise ValueError("no body mesh found (every mesh was filtered out or has no POSITION)")
    names = {j for s in g.get("skins", []) for j in s["joints"]} or set(range(len(nodes)))
    joints = {}
    for j in names:
        n = nodes[j]; nm = n.get("extras", {}).get("name") or n.get("name", "")
        joints[nm] = tuple(zup(world(j)[:3, 3][None])[0])
    return np.concatenate(Vs), np.concatenate(Ts), joints

# ---------------------------------------------------------------- Blender
def blender_collect(meshes=None):
    """Rest-pose, shape-keys-at-zero evaluated body mesh in world space plus bone heads for every armature in the scene."""
    import bpy, numpy as np
    arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    saved = [(a, a.data.pose_position) for a in arms]; keys = []
    for a in arms: a.data.pose_position = "REST"
    for o in bpy.context.scene.objects:
        if o.type == "MESH" and o.data.shape_keys:
            for kb in o.data.shape_keys.key_blocks[1:]: keys.append((kb, kb.value)); kb.value = 0.0
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    Vs, Ts, off = [], [], 0
    shapes = {pb.custom_shape for a in arms if a.pose for pb in a.pose.bones if pb.custom_shape}   # Blender's glTF importer adds an Icosphere as the bone shape
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or o in shapes: continue
        if meshes and o.name not in meshes: continue
        if not meshes and SKIP_MESH.search(o.name): continue
        e = o.evaluated_get(dg); me = e.to_mesh(); me.calc_loop_triangles()
        P = np.array([o.matrix_world @ v.co for v in me.vertices]); T = np.array([t.vertices for t in me.loop_triangles], int).reshape(-1, 3)
        e.to_mesh_clear()
        if len(P): Vs.append(P); Ts.append(T + off); off += len(P)
    joints = {b.name: tuple(a.matrix_world @ b.head_local) for a in arms for b in a.data.bones}
    for a, p in saved: a.data.pose_position = p
    for kb, v in keys: kb.value = v
    if not Vs: raise ValueError("no body meshes in the scene")
    return np.concatenate(Vs), np.concatenate(Ts), joints

def blender_import(path):
    import bpy
    ext = os.path.splitext(path)[1].lower()
    if ext == ".blend": bpy.ops.wm.open_mainfile(filepath=path)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if ext in (".glb", ".gltf"): bpy.ops.import_scene.gltf(filepath=path)
        elif ext == ".fbx": bpy.ops.import_scene.fbx(filepath=path)
        elif ext == ".obj": bpy.ops.wm.obj_import(filepath=path)
        else: raise ValueError(f"cannot import {ext}")

# ---------------------------------------------------------------- CLI
def _load_profile(path, name=None):
    if path.lower().endswith(".json"):
        with open(path) as f: return json.load(f)
    V, T, J = load_gltf(path); return measure(V, T, J, name or os.path.splitext(os.path.basename(path))[0])

def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("measure"); p.add_argument("file"); p.add_argument("--name"); p.add_argument("--out")
    p = sub.add_parser("blender-measure"); p.add_argument("--file"); p.add_argument("--name", default="reference"); p.add_argument("--out"); p.add_argument("--meshes", help="comma separated object names (default: all but hair, eyes, clothes, props)")
    p = sub.add_parser("targets"); p.add_argument("profiles", nargs="+"); p.add_argument("--out", default="knowledge/body-targets.json"); p.add_argument("--style", default=""); p.add_argument("--rel", type=float, default=0.06)
    p = sub.add_parser("check"); p.add_argument("candidate"); p.add_argument("--targets", default="knowledge/body-targets.json"); p.add_argument("--json")
    try: a = ap.parse_args(argv)
    except SystemExit as e: return EXIT_USAGE if e.code else 0
    try:
        if a.cmd == "measure":
            V, T, J = load_gltf(a.file); prof = measure(V, T, J, a.name or os.path.splitext(os.path.basename(a.file))[0])
        elif a.cmd == "blender-measure":
            if a.file: blender_import(a.file)
            V, T, J = blender_collect(set(a.meshes.split(",")) if a.meshes else None); prof = measure(V, T, J, a.name)
        elif a.cmd == "targets":
            profs = [_load_profile(x) for x in a.profiles]
            t = build_targets(profs, a.style, a.rel)
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            with open(a.out, "w") as f: json.dump(t, f, indent=2)
            print(f"wrote {a.out}: {len(t['metrics'])} metrics from {len(profs)} reference(s)"); return EXIT_PASS
        else:
            with open(a.targets) as f: targets = json.load(f)
            prof = _load_profile(a.candidate); status, rows = check(prof, targets)
            print(format_report(prof, status, rows))
            if a.json:
                with open(a.json, "w") as f: json.dump({"status": status, "profile": prof, "rows": rows}, f, indent=1)
            return {"pass": EXIT_PASS, "fail": EXIT_FAIL, "unknown": EXIT_UNKNOWN}[status]
    except (OSError, ValueError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr); return EXIT_USAGE
    text = json.dumps(prof, indent=2)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as f: f.write(text)
        print(f"wrote {a.out}")
    else: print(text)
    return EXIT_PASS

if __name__ == "__main__":
    sys.exit(main())
