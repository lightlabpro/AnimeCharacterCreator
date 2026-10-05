"""Exports the character from Blender as an asset-library pack the Anime Character Creator can import, then checks it.
Run in Blender (Text Editor > Run Script) or `blender -b file.blend -P export_pack.py`. Edit the CONFIG block first.

What it does that a plain File > Export does not:
  - zeroes every shape key value for the export (the exporter writes the CURRENT slider values as the default morph weights, so a
    key left at 1.0 arrives in the app already applied) and puts your values back afterwards
  - exports glTF Separate (.gltf + .bin + textures), shape key names (`extras.targetNames`), skins and one clip per action,
    deform bones only, custom properties (so `socket_name` survives), modifiers NOT applied (the armature and shape keys must survive)
  - writes pack.json, updates manifest.json at the library root, and runs check_pack.py on the result
Nothing is deleted or overwritten outside the pack folder and manifest.json.
"""
import json, os, sys

# ----------------------------------------------------------------------------- CONFIG
LIBRARY_ROOT = "//library"                     # the folder that holds humanoid/ robot/ full_beast/ (// = next to the .blend)
LIBRARY = "humanoid"                            # humanoid, robot or full_beast
CATEGORY = "bodies/adult"                       # folder under the library tree, e.g. bodies/adult, hair/front, accessories
PACK_ID = "body_adult_v1"
DISPLAY_NAME = "Adult body"
SLOT = "body_adult"                             # body_adult, body_child, hair_front, accessory, outfit ...
SOCKET = "SOC-Chest"                            # where this pack attaches (bodies: any documented socket)
EXPORT_PREFIXES = ("CHR_", "SOC-")              # objects whose names start like this are exported, plus every armature
CONTRACT = None                                 # path to knowledge/expected-contract.json (optional, enables name checks)
# -----------------------------------------------------------------------------

def export_objects(bpy):
    objs = [o for o in bpy.context.scene.objects if o.type == "ARMATURE" or o.name.startswith(EXPORT_PREFIXES)]
    if not any(o.type == "MESH" for o in objs): raise SystemExit(f"No mesh named {EXPORT_PREFIXES}* found. Name the character meshes CHR_<name>.")
    return objs

def exporter_settings(path):
    return dict(filepath=path, export_format="GLTF_SEPARATE", use_selection=True, export_apply=False, export_yup=True,
                export_morph=True, export_skins=True, export_def_bones=True, export_extras=True,
                export_animations=True, export_animation_mode="ACTIONS", export_cameras=False, export_lights=False)

def read_json(path):
    with open(path, encoding="utf-8") as fh: return json.load(fh)

def update_manifest(root, entry):
    path = os.path.join(root, "manifest.json")
    data = {"packs": []}
    if os.path.exists(path):
        try: data = read_json(path)
        except Exception: raise SystemExit(f"{path} is not valid JSON. Fix or move it, then run again.")
    packs = [p for p in data.get("packs", []) if p.get("id") != entry["id"]]
    packs.append(entry); data["packs"] = packs
    with open(path, "w") as f: json.dump(data, f, indent=2)

def find_checker():
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    p = os.path.join(here, "check_pack.py")
    return p if os.path.exists(p) else None

def export_pack():
    import bpy
    root = bpy.path.abspath(LIBRARY_ROOT)
    if LIBRARY not in ("humanoid", "robot", "full_beast"): raise SystemExit("LIBRARY must be humanoid, robot or full_beast")
    folder = os.path.join(root, LIBRARY, *CATEGORY.split("/"), PACK_ID); os.makedirs(folder, exist_ok=True)
    objs = export_objects(bpy)
    # 1. zero every shape key, remembering the values
    saved = []
    for o in bpy.data.objects:
        if o.type == "MESH" and o.data.shape_keys:
            for kb in o.data.shape_keys.key_blocks[1:]:
                if kb.value != 0.0: saved.append((kb, kb.value)); kb.value = 0.0
    selection = [o for o in bpy.context.scene.objects if o.select_get()]
    try:
        for o in bpy.context.scene.objects: o.select_set(False)
        for o in objs: o.select_set(True)
        bpy.ops.export_scene.gltf(**exporter_settings(os.path.join(folder, PACK_ID + ".gltf")))
    finally:
        for kb, v in saved: kb.value = v
        for o in bpy.context.scene.objects: o.select_set(o in selection)
    with open(os.path.join(folder, "pack.json"), "w") as f:
        json.dump({"id": PACK_ID, "display_name": DISPLAY_NAME, "library": LIBRARY, "slot": SLOT, "socket": SOCKET}, f, indent=2)
    update_manifest(root, {"id": PACK_ID, "library": LIBRARY, "folder": "/".join([LIBRARY, *CATEGORY.split("/"), PACK_ID])})
    print(f"exported {PACK_ID} to {folder}" + (f" (zeroed {len(saved)} shape keys for the export, values restored)" if saved else ""))
    checker = find_checker()
    if not checker:
        print("check_pack.py not found next to this script. Run: python3 check_pack.py", root); return folder, None
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_pack", checker); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    contract = read_json(CONTRACT) if CONTRACT and os.path.exists(CONTRACT) else None
    rep = mod.check(folder, contract)
    for it in sorted(rep.items, key=lambda i: {"FAIL": 0, "UNKNOWN": 1, "WARN": 2, "INFO": 3}[i["level"]]): print(f"{it['level']:<8} {it['code']:<20} {it['message']}")
    status = "FAIL" if rep.count("FAIL") else ("UNKNOWN" if rep.count("UNKNOWN") else "OK")
    print(f"PACK_CHECK_{status}: {rep.count('FAIL')} fail, {rep.count('UNKNOWN')} unknown, {rep.count('WARN')} warn")
    return folder, status

if __name__ == "__main__":
    export_pack()
