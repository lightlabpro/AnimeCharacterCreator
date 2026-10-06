#!/usr/bin/env python3
"""Checks exported asset-library packs against the creator app's contract, before the app ever sees them.

  python3 check_pack.py LIBRARY_ROOT_OR_PACK_FOLDER [--contract knowledge/expected-contract.json] [--json report.json] [--strict]

Pure Python (no Blender, no numpy). Mirrors the app importer (src/library/importer.ts) and the glTF loader
(src/viewport/gltfPacks.ts), and adds checks the importer never makes: morph target names and start weights,
embedded buffers, bone and socket names, triangle budget, feet-on-floor and height.

Findings are FAIL (the pack will not work), WARN (works but loses something) or UNKNOWN (could not be measured, which is
never a pass). Exit codes: 0 pass, 12 any FAIL (or WARN with --strict), 13 UNKNOWN and no FAIL, 2 usage.
"""
import argparse, json, math, os, re, struct, sys

LIBRARIES = ("humanoid", "robot", "full_beast")
CATEGORY_ROOTS = {
    "humanoid": ["bodies", "morphs", "hair", "facial_hair", "elements", "outfits", "accessories", "materials", "motions", "presets"],
    "robot": ["body", "parts", "materials", "motions"],
    "full_beast": ["body", "elements", "accessories", "materials", "motions", "presets"],
}
SOCKETED = ("hair", "facial_hair", "elements", "accessories", "parts")
NO_MESH_OK = ("materials", "motions", "presets", "morphs")
UNSUPPORTED_EXT = {
    "KHR_draco_mesh_compression": "Export with Draco compression turned off.",
    "EXT_meshopt_compression": "Export without meshopt compression.",
    "KHR_texture_basisu": "Export textures as PNG or JPEG, not KTX2.",
}
MORPH_LAYERS_WARN, MORPH_LAYERS_MAX = 220, 256      # three.js stores each target as a layer of one array texture; WebGL2 guarantees 256 layers
MORPH_MB_WARN, MORPH_MB_MAX = 256, 1024             # float32 RGBA texels: vertices x (1 position + 1 if normals) x 16 bytes x targets
TRI_HARD = (500, 120000)          # outside this a mesh is almost certainly wrong
TRI_BODY_SOFT = (18000, 28000)    # nude base body, docs/CLAUDE_BUILD_PROMPT.md
HEIGHT = {"adult": (1.5, 2.2), "child": (1.0, 1.6)}

class Report:
    def __init__(self): self.items = []
    def add(self, level, pack, code, msg): self.items.append({"level": level, "pack": pack, "code": code, "message": msg})
    def fail(self, p, c, m): self.add("FAIL", p, c, m)
    def warn(self, p, c, m): self.add("WARN", p, c, m)
    def unknown(self, p, c, m): self.add("UNKNOWN", p, c, m)
    def count(self, level): return sum(1 for i in self.items if i["level"] == level)

def read_json(path):
    with open(path, encoding="utf-8") as fh: return json.load(fh)

def norm(p): return p.replace("\\", "/").rstrip("/")

def locate_tree(path):
    segs = norm(os.path.abspath(path)).split("/")
    for i in range(len(segs) - 1, -1, -1):
        if segs[i] in LIBRARIES: return segs[i], "/".join(segs[i + 1:])
    return None, ""

def read_gltf(path):
    """Returns (json, bin_chunk_or_None). Handles .gltf and .glb."""
    with open(path, "rb") as f: raw = f.read()
    if path.lower().endswith(".glb"):
        if raw[:4] != b"glTF": raise ValueError("not a GLB file (bad magic)")
        off, js, bn = 12, None, None
        while off + 8 <= len(raw):
            ln, typ = struct.unpack_from("<I4s", raw, off); body = raw[off + 8: off + 8 + ln]
            if typ == b"JSON": js = json.loads(body.decode("utf-8"))
            elif typ == b"BIN\0": bn = body
            off += 8 + ln + ((-ln) % 4)
        if js is None: raise ValueError("GLB has no JSON chunk")
        return js, bn
    return json.loads(raw.decode("utf-8")), None

def matmul(a, b): return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def trs(n):
    if "matrix" in n:
        m = n["matrix"]; return [[m[c * 4 + r] for c in range(4)] for r in range(4)]   # column-major
    t = n.get("translation", [0, 0, 0]); q = n.get("rotation", [0, 0, 0, 1]); s = n.get("scale", [1, 1, 1])
    x, y, z, w = q
    R = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return [[R[0][0] * s[0], R[0][1] * s[1], R[0][2] * s[2], t[0]], [R[1][0] * s[0], R[1][1] * s[1], R[1][2] * s[2], t[1]], [R[2][0] * s[0], R[2][1] * s[1], R[2][2] * s[2], t[2]], [0, 0, 0, 1]]

def world_bounds(g, mesh_index_filter=None):
    """Axis-aligned bounds of all mesh POSITION accessors through node transforms. None if min/max are missing.
    A skinned mesh node's own transform is IGNORED (glTF spec: the joints place it, and at the bind pose skin matrices are identity), so a file with
    an export root rotation (Sketchfab, FBX-converted) is not misread as rotated or mis-sized."""
    nodes = g.get("nodes", []); parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []): parent[c] = i
    def world(i):
        m = trs(nodes[i])
        while i in parent: i = parent[i]; m = matmul(trs(nodes[i]), m)
        return m
    lo, hi = [math.inf] * 3, [-math.inf] * 3; found = False
    for i, n in enumerate(nodes):
        if "mesh" not in n: continue
        W = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]] if "skin" in n else world(i)
        for prim in g["meshes"][n["mesh"]].get("primitives", []):
            acc = g["accessors"][prim["attributes"]["POSITION"]] if "POSITION" in prim.get("attributes", {}) else None
            if not acc or "min" not in acc or "max" not in acc: return None
            for cx in (acc["min"][0], acc["max"][0]):
                for cy in (acc["min"][1], acc["max"][1]):
                    for cz in (acc["min"][2], acc["max"][2]):
                        p = [sum(W[r][c] * v for c, v in enumerate((cx, cy, cz, 1))) for r in range(3)]
                        for k in range(3): lo[k] = min(lo[k], p[k]); hi[k] = max(hi[k], p[k])
                        found = True
    return (lo, hi) if found else None

def tri_count(g):
    total = 0
    for m in g.get("meshes", []):
        for prim in m.get("primitives", []):
            if prim.get("mode", 4) != 4: continue
            if "indices" in prim: total += g["accessors"][prim["indices"]]["count"] // 3
            elif "POSITION" in prim.get("attributes", {}): total += g["accessors"][prim["attributes"]["POSITION"]]["count"] // 3
    return total

def check_gltf(R, pid, folder, main, pack, category, contract):
    ext = os.path.splitext(main)[1].lower()
    try: g, _ = read_gltf(os.path.join(folder, main))
    except Exception as e: R.fail(pid, "gltf_unreadable", f"{main}: {e}"); return
    if str(g.get("asset", {}).get("version")) != "2.0": R.fail(pid, "gltf_version", f"{main}: glTF version must be 2.0")
    # embedded data and missing files
    for b in g.get("buffers", []):
        uri = b.get("uri")
        if uri is None:
            if ext == ".gltf": R.fail(pid, "buffer_no_uri", f"{main}: a buffer has no uri")
        elif uri.startswith("data:"): R.fail(pid, "embedded_buffer", f"{main}: geometry is embedded as a data URI. Export glTF Separate (.gltf + .bin).")
        elif not os.path.exists(os.path.join(folder, uri)): R.fail(pid, "missing_file", f"{main}: buffer file {uri} is missing from the pack folder")
    for im in g.get("images", []):
        uri = im.get("uri")
        if uri is None:
            if ext == ".glb": R.fail(pid, "embedded_texture", f"{main}: textures are packed inside the .glb. The app's loader breaks these: export GLTF_SEPARATE.")
        elif uri.startswith("data:"): R.fail(pid, "embedded_texture", f"{main}: a texture is embedded as a data URI. Export textures as separate files.")
        elif not os.path.exists(os.path.join(folder, uri)): R.fail(pid, "missing_file", f"{main}: texture {uri} is missing from the pack folder")
    # extensions the app cannot decode: its glTF loader has no Draco, Meshopt or KTX2 decoder set
    for ext in sorted(set(g.get("extensionsRequired", [])) | set(g.get("extensionsUsed", []))):
        if ext in UNSUPPORTED_EXT:
            R.fail(pid, "unsupported_extension", f"{main}: uses {ext}. The app has no decoder for it and the pack will not load. {UNSUPPORTED_EXT[ext]}")
    # morph targets
    known_id = set(contract.get("identity_shape_keys", [])) if contract else set()
    known_pf = set(contract.get("performance_shape_keys", [])) if contract else set()
    all_names = []
    for m in g.get("meshes", []):
        tcount = max((len(p.get("targets", [])) for p in m.get("primitives", [])), default=0)
        if not tcount: continue
        names = (m.get("extras") or {}).get("targetNames")
        if not names: R.fail(pid, "no_target_names", f"mesh {m.get('name')}: has {tcount} morph targets but no extras.targetNames, so the app cannot find any ID- or PF- key. Enable Shape Keys with names when exporting."); continue
        if len(names) != tcount: R.fail(pid, "target_names_mismatch", f"mesh {m.get('name')}: {tcount} targets but {len(names)} names")
        if any(abs(w) > 1e-6 for w in m.get("weights", [])): R.fail(pid, "nonzero_weights", f"mesh {m.get('name')}: shape keys must start at 0, found non-zero default weights")
        all_names += names
        prim = m["primitives"][0]
        verts = g["accessors"][prim["attributes"]["POSITION"]]["count"] if "POSITION" in prim.get("attributes", {}) else 0
        has_normals = any("NORMAL" in t for t in prim.get("targets", []))
        mb = verts * (2 if has_normals else 1) * 16 * tcount / 1048576
        R.add("INFO", pid, "morph_memory", f"mesh {m.get('name')}: {tcount} morph targets x {verts} vertices{' with normals' if has_normals else ''} = about {mb:.0f} MB of GPU texture (and the same again in memory while it uploads)")
        if tcount > MORPH_LAYERS_MAX: R.fail(pid, "too_many_targets", f"mesh {m.get('name')}: {tcount} shape keys exceeds {MORPH_LAYERS_MAX}, the number of array texture layers WebGL2 guarantees. Some GPUs will fail to render it. Split the keys across meshes or remove unused ones.")
        elif tcount > MORPH_LAYERS_WARN: R.warn(pid, "many_targets", f"mesh {m.get('name')}: {tcount} shape keys is close to the {MORPH_LAYERS_MAX} layer limit")
        if mb > MORPH_MB_MAX: R.fail(pid, "morph_memory", f"mesh {m.get('name')}: morph targets need about {mb:.0f} MB of GPU texture, over {MORPH_MB_MAX} MB. Reduce vertices or keys, or export without morph normals.")
        elif mb > MORPH_MB_WARN: R.warn(pid, "morph_memory", f"mesh {m.get('name')}: morph targets need about {mb:.0f} MB of GPU texture. Exporting without morph normals halves it.")
        if any("JOINTS_1" in p.get("attributes", {}) for p in m["primitives"]): R.warn(pid, "joint_influences", f"mesh {m.get('name')}: more than 4 bone influences per vertex. The app's skinning reads 4, the rest are ignored. Limit influences to 4 when exporting.")
        for nme in names:
            if not nme.startswith(("ID-", "PF-")): R.warn(pid, "unprefixed_key", f"shape key '{nme}' has no ID- or PF- prefix. The app ignores it.")
            elif contract and nme.startswith("ID-") and nme not in known_id: R.warn(pid, "orphan_key", f"'{nme}' is not an identity key the app reads. It will do nothing.")
            elif contract and nme.startswith("PF-") and nme not in known_pf: R.warn(pid, "orphan_key", f"'{nme}' is not a performance key the app reads. It will do nothing.")
    is_body = category.split("/")[0] in ("bodies", "body")
    nid = sum(1 for n in all_names if n.startswith("ID-") and (not contract or n in known_id)); npf = sum(1 for n in all_names if n.startswith("PF-") and (not contract or n in known_pf))
    if is_body:
        if not all_names: R.warn(pid, "body_no_keys", "a body pack with no shape keys: no slider will move it")
        elif contract:
            R.add("INFO", pid, "coverage", f"implements {nid} of {len(known_id)} identity keys and {npf} of {len(known_pf)} performance keys the app drives")
            if nid == 0: R.warn(pid, "no_identity_keys", "none of the identity (ID-) keys the app reads are present")
    # pose clips: POSE-<pose> animations are applied to the body when that pose is picked
    poses = ("apose", "relaxed", "tpose", "hero", "wave", "sit")
    squash = lambda n: re.sub(r"[^a-z]", "", n.lower())
    clips = [a.get("name", "") for a in g.get("animations", [])]
    if clips:
        good = [c for c in clips if squash(c) in {"pose" + p for p in poses}]
        stray = [c for c in clips if squash(c).startswith("pose") and c not in good]
        R.add("INFO", pid, "pose_clips", f"{len(clips)} animations; pose clips the app uses: {', '.join(good) or 'none'}")
        for c in stray: R.warn(pid, "pose_name", f"animation '{c}' looks like a pose but is not one of POSE-{{{'|'.join(poses)}}}, so the app ignores it")
    elif is_body: R.add("INFO", pid, "pose_clips", "no POSE-<pose> clips: the body stays in its rest pose when a pose is picked")
    # bones and sockets
    bones = set()
    for s in g.get("skins", []):
        for j in s.get("joints", []): bones.add(g["nodes"][j].get("name", ""))
    sockets = {n.get("name", "") for n in g.get("nodes", []) if n.get("name", "").startswith("SOC-")}
    if is_body:
        if not bones: R.fail(pid, "no_skin", "a body pack needs a skin with DEF- bones, otherwise height, limb lengths and posing do nothing")
        elif not any(b.startswith("DEF-") for b in bones): R.fail(pid, "no_def_bones", "the skin has no DEF- bones. The app only drives DEF- bones.")
        else:
            other = sorted(b for b in bones if not b.startswith("DEF-"))
            if other: R.warn(pid, "non_def_bones", f"{len(other)} skinned bones are not DEF- and will not be driven: {', '.join(other[:5])}")
        if not sockets: R.fail(pid, "no_sockets", "a body pack needs SOC- socket nodes, otherwise hair, accessories and outfits have nowhere to attach")
        elif contract:
            doc = contract.get("documented_sockets", [])
            miss = [s for s in doc if s not in sockets]
            if miss: R.warn(pid, "sockets_missing", f"{len(miss)} of the {len(doc)} sockets in docs/CLAUDE_BUILD_PROMPT.md are missing: {', '.join(miss[:8])}{' ...' if len(miss) > 8 else ''}")
            else: R.add("INFO", pid, "sockets", f"all {len(doc)} documented SOC- sockets present")
    R.provided = getattr(R, "provided", {})
    if is_body: R.provided.setdefault(pack.get("library"), set()).update(sockets)
    # triangle budget
    tris = tri_count(g)
    if tris < TRI_HARD[0] and is_body or tris > TRI_HARD[1]: R.fail(pid, "tri_count", f"{tris} triangles is outside the sane range {TRI_HARD}")
    elif is_body and not (TRI_BODY_SOFT[0] <= tris <= TRI_BODY_SOFT[1]): R.warn(pid, "tri_budget", f"{tris} triangles; the body target is {TRI_BODY_SOFT[0]}-{TRI_BODY_SOFT[1]}")
    else: R.add("INFO", pid, "tris", f"{tris} triangles")
    # size and origin
    if is_body:
        b = world_bounds(g)
        if b is None: R.unknown(pid, "bounds", "POSITION accessors have no min/max, so height and origin could not be checked")
        else:
            h = b[1][1] - b[0][1]; foot = b[0][1]
            if abs(foot) > 0.03: R.fail(pid, "origin_not_at_feet", f"lowest point is at y={foot:.3f} m. The origin must be on the floor between the feet.")
            kind = "child" if "child" in category or "child" in pack.get("slot", "") else "adult"
            lo, hi = HEIGHT[kind] if library_of(pack) == "humanoid" else (0.3, 6.0)
            if not lo <= h <= hi: R.fail(pid, "height", f"height {h:.2f} m is outside {lo}-{hi} m for this body. Scale is 1 unit = 1 m with transforms applied.")
            else: R.add("INFO", pid, "height", f"height {h:.2f} m, feet at y={foot:.3f}")
    R.add("INFO", pid, "materials", "materials: " + ", ".join(m.get("name", "?") for m in g.get("materials", [])[:8]))

def library_of(pack): return pack.get("library")

def find_packs(root):
    out = []
    for d, _, files in os.walk(root):
        if "pack.json" in files: out.append(d)
    return sorted(out)

def check(root, contract, R=None):
    R = R or Report()
    root = norm(os.path.abspath(root))
    folders = find_packs(root)
    if not folders: R.fail("-", "no_packs", f"no pack.json found under {root}"); return R
    manifest = None; mpath = os.path.join(root, "manifest.json")
    entries = {}
    if os.path.exists(mpath):
        try:
            manifest = read_json(mpath)
            for e in manifest.get("packs", []):
                if not isinstance(e, dict) or not e.get("folder"): R.fail("manifest", "manifest_entry", f"entry without a folder: {e}"); continue
                entries[norm(os.path.join(root, e["folder"]))] = e
        except Exception as e: R.fail("manifest", "manifest_json", f"manifest.json is not valid JSON ({e})")
    seen = set()
    for folder in folders:
        rel = norm(os.path.relpath(folder, root)); pid = rel
        try: pack = read_json(os.path.join(folder, "pack.json"))
        except Exception as e: R.fail(pid, "pack_json", f"pack.json is not valid JSON ({e})"); continue
        missing = [k for k in ("id", "display_name", "library", "slot") if not isinstance(pack.get(k), str) or not pack.get(k, "").strip()]
        if missing: R.fail(pid, "pack_fields", f"pack.json is missing {', '.join(missing)}"); continue
        pid = pack["id"]
        if pid in seen: R.fail(pid, "duplicate_id", "another pack in this folder already uses this id")
        seen.add(pid)
        lib = pack["library"]
        if lib not in LIBRARIES: R.fail(pid, "library", f"library '{lib}' is not humanoid, robot or full_beast"); continue
        tree, category = locate_tree(folder)
        if tree is None: R.unknown(pid, "tree", "the folder is not inside a humanoid, robot or full_beast tree, so the library folder could not be checked")
        else:
            if tree != lib: R.fail(pid, "tree_mismatch", f"pack.json says {lib} but the folder is inside the {tree} tree. Humanoid, robot and full_beast never mix.")
            top = category.split("/")[0]
            if top not in CATEGORY_ROOTS[lib]: R.fail(pid, "category", f"'{top or '(tree root)'}' is not a {lib} category folder. Use one of: {', '.join(CATEGORY_ROOTS[lib])}")
        cat = category or ""
        R.wanted = getattr(R, "wanted", [])
        if pack.get("socket") and cat.split("/")[0] not in ("bodies", "body"): R.wanted.append((pid, lib, pack["socket"]))
        if cat.split("/")[0] in SOCKETED and not pack.get("socket"): R.warn(pid, "no_socket", "no socket in pack.json: it will attach at the default point for its slot")
        e = entries.get(folder)
        if e:
            if e.get("library") and e["library"] != lib: R.fail(pid, "manifest_library", f"manifest.json lists it as {e['library']} but pack.json says {lib}")
            if e.get("id") and e["id"] != pack["id"]: R.warn(pid, "manifest_id", f"manifest id '{e['id']}' differs from pack id '{pack['id']}'")
        elif entries: R.warn(pid, "not_in_manifest", "not listed in manifest.json (the app adds it anyway)")
        files = sorted(os.listdir(folder))
        mains = [f for f in files if f.lower().endswith(".glb")] or [f for f in files if f.lower().endswith(".gltf")]
        top = cat.split("/")[0]
        if not mains:
            if top not in NO_MESH_OK and top: R.warn(pid, "no_mesh", "no .glb or .gltf in the pack folder: the app shows its placeholder")
            continue
        if len(mains) > 1: R.warn(pid, "several_meshes", f"several mesh files ({', '.join(mains)}); the app loads the first")
        check_gltf(R, pid, folder, mains[0], pack, cat, contract)
    known = set(contract.get("sockets", [])) | set(contract.get("documented_sockets", [])) if contract else set()
    for pid, lib, sock in getattr(R, "wanted", []):
        provided = getattr(R, "provided", {}).get(lib, set())
        if sock not in known | provided:
            R.warn(pid, "unknown_socket", f"pack.json socket '{sock}' is not documented, not used by the app and not provided by any body pack in this check, so nothing will carry it")
        elif not provided and not contract: R.unknown(pid, "socket_target", f"no body pack in this check provides socket '{sock}', so the attachment could not be verified")
    for f, e in entries.items():
        if f not in folders: R.fail(e.get("id") or e.get("folder"), "manifest_orphan", "listed in manifest.json but the folder has no pack.json")
    return R

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path"); ap.add_argument("--contract"); ap.add_argument("--json"); ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(a.path): print(f"not a folder: {a.path}", file=sys.stderr); sys.exit(2)
    contract = None
    if a.contract:
        try: contract = read_json(a.contract)
        except Exception as e: print(f"cannot read contract: {e}", file=sys.stderr); sys.exit(2)
    R = check(a.path, contract)
    order = {"FAIL": 0, "UNKNOWN": 1, "WARN": 2, "INFO": 3}
    for it in sorted(R.items, key=lambda i: (order[i["level"]], i["pack"])):
        print(f"{it['level']:<8} {it['pack']:<22} {it['code']:<20} {it['message']}")
    nf, nu, nw = R.count("FAIL"), R.count("UNKNOWN"), R.count("WARN")
    print(f"\n{nf} fail, {nu} unknown, {nw} warn.")
    print("SCOPE: file structure, names, counts and bounds. It cannot see how the mesh deforms, edge-loop quality, or whether the art is good.")
    if a.json:
        with open(a.json, "w") as f: json.dump({"fail": nf, "unknown": nu, "warn": nw, "items": R.items}, f, indent=2)
    if nf or (a.strict and nw): print("PACK_CHECK_FAIL"); sys.exit(12)
    if nu: print("PACK_CHECK_UNKNOWN: not measured, so not a pass"); sys.exit(13)
    print("PACK_CHECK_OK")

if __name__ == "__main__":
    main()
