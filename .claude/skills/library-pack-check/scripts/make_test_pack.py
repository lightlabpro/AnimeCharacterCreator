#!/usr/bin/env python3
"""Writes a small, valid, contract-conformant humanoid body pack (glTF + .bin + pack.json) for tests and as a worked example.

  python3 make_test_pack.py OUT_DIR [--id body_test] [--defect NAME]

The mesh is a crude boxy figure, 1.72 m tall with feet at y=0, skinned to DEF- bones, with ID- and PF- morph targets
that start at 0 and SOC- sockets. It exists to prove the pipeline (checker, importer, sliders), not to look good.

Defects, one at a time, to test the checker: embedded, nonzero_weights, no_targetnames, orphan_key, floating, tiny,
no_bones, no_sockets, missing_bin, bad_library, no_slot
"""
import argparse, base64, json, math, os, struct
import numpy as np

KEYS_ID = ["ID-FaceRound", "ID-EyeSize", "ID-BodyBulk", "ID-BodyLean", "ID-SkullWidth", "ID-SkullWidth_Neg"]
KEYS_PF = ["PF-Blink", "PF-Blink_L", "PF-Blink_R", "PF-JawOpen"]
def documented_sockets():
    """All SOC- names from the contract file when it can be found (so a clean test pack passes), else a small default set."""
    here = os.path.dirname(os.path.abspath(__file__))
    for up in range(2, 6):
        p = os.path.normpath(os.path.join(here, *[".."] * up, "knowledge", "expected-contract.json"))
        if os.path.exists(p):
            try: return json.load(open(p))["documented_sockets"]
            except Exception: pass
    return ["SOC-HairFront", "SOC-HairBack", "SOC-Eyewear", "SOC-Chest"]
SOCKETS = documented_sockets()
# Deliberately away from where the app's placeholder body keeps these sockets, so a test can tell which one an accessory attached to.
SOCKET_AT = {"SOC-HeadTop": (0.0, 2.2, 0.0), "SOC-Chest": (0.0, 1.3, 0.0)}
BONES = ["DEF-spine", "DEF-head", "DEF-upperarm.L", "DEF-upperarm.R"]
DEFECTS = {"no_poses", "embedded", "nonzero_weights", "no_targetnames", "orphan_key", "floating", "tiny", "no_bones", "no_sockets", "missing_bin", "bad_library", "no_slot"}

def box(cx, cy, cz, sx, sy, sz, n=18):
    """A box whose six faces are n x n grids, so the test mesh has a realistic triangle count (about 20k for the figure)."""
    v = []; f = []
    def face(origin, u, w):
        base = len(v)
        for i in range(n + 1):
            for j in range(n + 1): v.append(tuple(origin[k] + u[k] * i / n + w[k] * j / n for k in range(3)))
        for i in range(n):
            for j in range(n):
                a = base + i * (n + 1) + j; b2 = a + 1; c = a + n + 1; d = c + 1
                f.extend([(a, b2, d), (a, d, c)])
    x0, x1, y0, y1, z0, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz - sz / 2, cz + sz / 2
    face((x0, y0, z1), (sx, 0, 0), (0, sy, 0)); face((x1, y0, z0), (-sx, 0, 0), (0, sy, 0))
    face((x0, y0, z0), (0, 0, sz), (0, sy, 0)); face((x1, y0, z1), (0, 0, -sz), (0, sy, 0))
    face((x0, y1, z1), (sx, 0, 0), (0, 0, -sz)); face((x0, y0, z0), (sx, 0, 0), (0, 0, sz))
    return v, f

def figure(tiny=False, floating=False):
    scale = 0.05 if tiny else 1.0; lift = 0.4 if floating else 0.0
    parts = [box(0, 0.45, 0, 0.30, 0.9, 0.18), box(0, 1.15, 0, 0.42, 0.55, 0.24), box(0, 1.55, 0, 0.22, 0.34, 0.24),
             box(-0.34, 1.15, 0, 0.12, 0.6, 0.12), box(0.34, 1.15, 0, 0.12, 0.6, 0.12)]
    verts, faces, part_of = [], [], []
    for i, (v, f) in enumerate(parts):
        base = len(verts); verts += [(x * scale, (y + lift) * scale, z * scale) for x, y, z in v]; faces += [tuple(base + k for k in tri) for tri in f]; part_of += [i] * len(v)
    return np.array(verts, np.float32), np.array(faces, np.uint32), np.array(part_of)

def contract_keys():
    here = os.path.dirname(os.path.abspath(__file__))
    for up in range(2, 6):
        p = os.path.normpath(os.path.join(here, *[".."] * up, "knowledge", "expected-contract.json"))
        if os.path.exists(p):
            d = json.load(open(p)); return d["identity_shape_keys"], d["performance_shape_keys"]
    raise SystemExit("--all-keys needs knowledge/expected-contract.json next to the skill")

def build(out, pid, defect, all_keys=False):
    os.makedirs(out, exist_ok=True)
    V, F, part = figure(defect == "tiny", defect == "floating")
    N = np.zeros_like(V); N[:, 2] = 1
    targets = {}
    names = (sum(contract_keys(), []) if all_keys else (KEYS_ID + KEYS_PF)) + (["ID-NotInTheApp"] if defect == "orphan_key" else [])
    for k in names:
        d = np.zeros_like(V)
        if "Bulk" in k: d[part <= 1, 0] = np.sign(V[part <= 1, 0]) * 0.03
        elif "Round" in k or "SkullWidth" in k: d[part == 2, 0] = np.sign(V[part == 2, 0]) * 0.02
        elif "Lean" in k: d[part <= 1, 0] = -np.sign(V[part <= 1, 0]) * 0.02
        else: d[part == 2, 1] = 0.01
        targets[k] = d.astype(np.float32)
    nb = len(BONES) if defect != "no_bones" else 0
    joints = np.zeros((len(V), 4), np.uint16); weights = np.zeros((len(V), 4), np.float32); weights[:, 0] = 1
    joints[:, 0] = np.where(part == 2, 1, 0)
    ibm = np.tile(np.eye(4, dtype=np.float32).T.reshape(-1), (max(nb, 1), 1))
    chunks, views, accs = [], [], []
    def add(arr, comp, typ, count, target=None, minmax=False):
        data = arr.tobytes(); pad = (-len(data)) % 4
        views.append({"buffer": 0, "byteOffset": sum(len(c) for c in chunks), "byteLength": len(data), **({"target": target} if target else {})})
        chunks.append(data + b"\0" * pad)
        a = {"bufferView": len(views) - 1, "componentType": comp, "count": count, "type": typ}
        if minmax: a["min"] = [float(x) for x in arr.min(axis=0)]; a["max"] = [float(x) for x in arr.max(axis=0)]
        accs.append(a); return len(accs) - 1
    pos = add(V, 5126, "VEC3", len(V), 34962, True); nor = add(N, 5126, "VEC3", len(V), 34962)
    idx = add(F.reshape(-1), 5125, "SCALAR", F.size, 34963)
    prim = {"attributes": {"POSITION": pos, "NORMAL": nor}, "indices": idx, "mode": 4, "material": 0}
    if nb: prim["attributes"]["JOINTS_0"] = add(joints, 5123, "VEC4", len(V), 34962); prim["attributes"]["WEIGHTS_0"] = add(weights, 5126, "VEC4", len(V), 34962)
    prim["targets"] = [{"POSITION": add(targets[k], 5126, "VEC3", len(V), 34962, True)} for k in names]
    mesh = {"name": "CHR_Body", "primitives": [prim], "weights": [0.0] * len(names)}
    if defect == "nonzero_weights": mesh["weights"][0] = 0.5
    if defect != "no_targetnames": mesh["extras"] = {"targetNames": names}
    nodes = [{"name": "CHR_Body", "mesh": 0, **({"skin": 0} if nb else {})}]
    root_children = [0]
    skin = None
    if nb:
        first = len(nodes)
        for b in BONES: nodes.append({"name": b, "translation": [0, 0, 0]})
        nodes.append({"name": "CHR_Armature", "children": list(range(first, first + nb))}); root_children.append(len(nodes) - 1)
        skin = {"joints": list(range(first, first + nb)), "inverseBindMatrices": add(ibm.astype(np.float32), 5126, "MAT4", nb)}
    if defect != "no_sockets":
        for s in SOCKETS: nodes.append({"name": s, "translation": list(SOCKET_AT.get(s, (0, 1.0, 0)))}); root_children.append(len(nodes) - 1)
    nodes.append({"name": "Root", "children": root_children}); root = len(nodes) - 1
    animations = []
    if nb and defect != "no_poses":
        # Pose clips, one rotation key on DEF-upperarm.L: POSE-tpose raises the arm 90 degrees, POSE-hero 30. The app plays POSE-<pose> when that pose is picked.
        arm = 1 + BONES.index("DEF-upperarm.L")
        for pose, deg in (("tpose", 90.0), ("hero", 30.0)):
            t = np.array([0.0, 0.04], np.float32); a = math.radians(deg) / 2
            q = np.array([[0, 0, math.sin(a), math.cos(a)]] * 2, np.float32)
            ti = add(t.reshape(-1, 1), 5126, "SCALAR", 2, minmax=True); qi = add(q, 5126, "VEC4", 2)
            animations.append({"name": f"POSE-{pose}", "samplers": [{"input": ti, "output": qi, "interpolation": "LINEAR"}], "channels": [{"sampler": 0, "target": {"node": arm, "path": "rotation"}}]})
    blob = b"".join(chunks)
    gltf = {"asset": {"version": "2.0", "generator": "make_test_pack.py"}, "scene": 0, "scenes": [{"nodes": [root]}], "nodes": nodes, "meshes": [mesh],
            "materials": [{"name": "Body_Skin", "pbrMetallicRoughness": {"baseColorFactor": [0.9, 0.75, 0.65, 1.0]}}],
            "accessors": accs, "bufferViews": views, "buffers": [{"byteLength": len(blob)}]}
    if skin: gltf["skins"] = [skin]
    if animations: gltf["animations"] = animations
    if defect == "embedded": gltf["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(blob).decode()
    else:
        gltf["buffers"][0]["uri"] = f"{pid}.bin"
        if defect != "missing_bin":
            with open(os.path.join(out, f"{pid}.bin"), "wb") as fh: fh.write(blob)
    with open(os.path.join(out, f"{pid}.gltf"), "w") as fh: json.dump(gltf, fh, indent=1)
    pack = {"id": pid, "display_name": "Test body", "library": "bad_library" if defect == "bad_library" else "humanoid", "slot": "body_adult", "socket": "SOC-Chest"}
    if defect == "no_slot": pack.pop("slot")
    with open(os.path.join(out, "pack.json"), "w") as fh: json.dump(pack, fh, indent=2)
    return out

def build_accessory(out, pid, socket):
    """A small box 'hat' with its own SOC- node at the origin, to test attachment to the body's socket."""
    os.makedirs(out, exist_ok=True)
    V, F = box(0, 0.05, 0, 0.2, 0.1, 0.2, n=2)
    V = np.array(V, np.float32); F = np.array(F, np.uint32)
    N = np.zeros_like(V); N[:, 1] = 1
    data = [V.tobytes(), N.tobytes(), F.reshape(-1).tobytes()]
    blob = b"".join(d + b"\0" * ((-len(d)) % 4) for d in data)
    offs = [0, len(data[0]) + (-len(data[0])) % 4]; offs.append(offs[1] + len(data[1]) + (-len(data[1])) % 4)
    gltf = {"asset": {"version": "2.0", "generator": "make_test_pack.py"}, "scene": 0, "scenes": [{"nodes": [2]}],
            "nodes": [{"name": "CHR_Hat", "mesh": 0}, {"name": socket, "translation": [0, 0, 0]}, {"name": "Root", "children": [0, 1]}],
            "meshes": [{"name": "CHR_Hat", "primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1}, "indices": 2, "mode": 4, "material": 0}]}],
            "materials": [{"name": "Hat_Cloth", "pbrMetallicRoughness": {"baseColorFactor": [0.4, 0.2, 0.6, 1.0]}}],
            "accessors": [{"bufferView": 0, "componentType": 5126, "count": len(V), "type": "VEC3", "min": [float(x) for x in V.min(axis=0)], "max": [float(x) for x in V.max(axis=0)]},
                          {"bufferView": 1, "componentType": 5126, "count": len(V), "type": "VEC3"},
                          {"bufferView": 2, "componentType": 5125, "count": F.size, "type": "SCALAR"}],
            "bufferViews": [{"buffer": 0, "byteOffset": offs[0], "byteLength": len(data[0])}, {"buffer": 0, "byteOffset": offs[1], "byteLength": len(data[1])},
                            {"buffer": 0, "byteOffset": offs[2], "byteLength": len(data[2])}],
            "buffers": [{"byteLength": len(blob), "uri": f"{pid}.bin"}]}
    with open(os.path.join(out, f"{pid}.bin"), "wb") as fh: fh.write(blob)
    with open(os.path.join(out, f"{pid}.gltf"), "w") as fh: json.dump(gltf, fh)
    with open(os.path.join(out, "pack.json"), "w") as fh: json.dump({"id": pid, "display_name": "Test hat", "library": "humanoid", "slot": "accessory", "socket": socket}, fh, indent=2)
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out"); ap.add_argument("--id", default="body_test"); ap.add_argument("--defect", choices=sorted(DEFECTS))
    ap.add_argument("--all-keys", action="store_true", help="a morph target for every ID- and PF- key the app drives (a realistic, heavy body)"); ap.add_argument("--kind", choices=["body", "accessory"], default="body"); ap.add_argument("--socket", default="SOC-HeadTop")
    a = ap.parse_args()
    print("wrote", build_accessory(a.out, a.id, a.socket) if a.kind == "accessory" else build(a.out, a.id, a.defect, a.all_keys))

if __name__ == "__main__":
    main()
