"""Export the v2 head (.blend from build_v2.py) as an app pack: library/humanoid/bodies/adult/head_mhs3_v2.

    python(bpy) export_v2.py V2.blend REPO

Same conventions as blender/newhead/export_head_pack.py (n56): one mesh per face element with contract-style CHR_
names, the skin as a lit 'Skin' material, painted pieces as flat emission ('..._emiss'), DEF-Head armature with SOC-
sockets, glTF Separate, pack.json + manifest entry. Differences:
  - the head is split into CHR_Head, CHR_Ears (ear shells) and CHR_MouthInside (the real cavity + inner lip ring);
  - no VW- view keys: v2's turned views come from the geometry;
  - CHR_Head carries baked custom normals: n56's analytic face normal (ellipsoid + forward push on the face plane,
    apply_look._target_normals) in v2 head units, blended by an_w, so the app's toon light matches Blender.
New element names (inbox item): CHR_EyeWhiteShade, CHR_IrisTop, CHR_IrisRim, CHR_Pupil, CHR_EyeHighlight,
CHR_LidLower, CHR_LidCrease, CHR_EarInner, CHR_EarLine, CHR_TeethLower.
"""
import json
import os
import sys

import bpy
import bmesh  # noqa: E402  (bpy first: the bpy module provides bmesh)
import numpy as np

BLEND, R = sys.argv[sys.argv.index("--") + 1:][:2] if "--" in sys.argv else sys.argv[1:3]
ZT, H = 1.685, 0.22
S, O = H, ZT - H                       # head units: chin at 0, skull top at 1
PACK_ID = "head_mhs3_v2"
DISPLAY = "MHS3 head v2 (test, head only)"
FOLDER = os.path.join(R, "library", "humanoid", "bodies", "adult", PACK_ID)
SKIN_SRGB = (232, 197, 170)
FACE_FORWARD, CHIN_LIT = 2.5, 1.0      # n56 values (export_head_pack / apply_look)

NAMES = [  # (object prefix, export name) - longest prefixes first
    ("V2Eye_sclera_shade_", "CHR_EyeWhiteShade"), ("V2Eye_sclera_", "CHR_EyeWhite"),
    ("V2Eye_iris_top_", "CHR_IrisTop"), ("V2Eye_iris_rim_", "CHR_IrisRim"), ("V2Eye_iris_", "CHR_Iris"),
    ("V2Eye_pupil_", "CHR_Pupil"), ("V2Eye_highlight_", "CHR_EyeHighlight"),
    ("V2Eye_lash_low_", "CHR_LidLower"), ("V2Eye_lash_", "CHR_LidLine"), ("V2Eye_crease_", "CHR_LidCrease"),
    ("V2Brow_", "CHR_Brow"), ("V2NoseShade", "CHR_NoseShade"), ("V2NoseHL", "CHR_NoseHighlight"),
    ("V2MouthLine", "CHR_MouthLine"), ("V2LipShade", "CHR_LipShadow"),
    ("V2Ear_ear_in_", "CHR_EarInner"), ("V2Ear_ear_line_", "CHR_EarLine"),
    ("V2TeethUpper", "CHR_TeethUpper"), ("V2TeethLower", "CHR_TeethLower"), ("V2Tongue", "CHR_Tongue"),
]
ALIASES = [  # (app key, source key, factor) as in n56
    ("PF-VisSmall", "PF-VisAA", 0.35), ("PF-VisMid", "PF-VisAA", 0.65), ("PF-VisIH", "PF-VisEE", 0.6),
    ("PF-VisOO", "PF-VisOH", 0.75), ("PF-Surprise", "PF-VisOH", 0.8),
]
SOCKETS = {  # (x, y, z) in head units above the chin, y forward is -
    "SOC-HeadTop": (0.0, 0.02, 1.0), "SOC-HairScalp": (0.0, 0.05, 0.92), "SOC-HairFront": (0.0, -0.30, 0.80),
    "SOC-HairSide_L": (0.36, 0.05, 0.62), "SOC-HairSide_R": (-0.36, 0.05, 0.62), "SOC-HairBack": (0.0, 0.42, 0.62),
    "SOC-Ear_L": (0.40, 0.08, 0.44), "SOC-Ear_R": (-0.40, 0.08, 0.44), "SOC-Eyewear": (0.0, -0.40, 0.555),
    "SOC-Neck": (0.0, 0.10, -0.05),
}


def lin(c):
    return tuple(((v / 255.0 + 0.055) / 1.055) ** 2.4 if v / 255.0 > 0.04045 else v / 255.0 / 12.92 for v in c)


def flat_material(name, colour):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Color"].default_value = tuple(colour[:3]) + (1,)
    b.inputs["Emission Strength"].default_value = 1.0
    m.use_backface_culling = False
    return m


def base_colour(mat):
    b = mat.node_tree.nodes.get("Principled BSDF")
    return tuple(b.inputs["Base Color"].default_value[:3])


def _sm(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def face_normals(co):
    Ph = np.stack([co[:, 0] / S, co[:, 1] / S, (co[:, 2] - O) / S], 1)
    y, z = Ph[:, 1], Ph[:, 2]
    c, r = np.array([0.0, -0.02, 0.47]), np.array([0.40, 0.46, 0.56])
    pe = (Ph - c) / r ** 2
    pe /= np.linalg.norm(pe, axis=1, keepdims=True)
    lo = 0.07 * CHIN_LIT
    face = _sm(0.0, -0.25, y) * _sm(0.05 - lo, 0.15 - lo, z) * (1 - _sm(0.62, 0.75, z))
    pe = pe + np.array([0.0, -FACE_FORWARD, 0.0]) * face[:, None]
    return pe / np.linalg.norm(pe, axis=1, keepdims=True)


def split_copy(src, keep_face):
    """Copy of src keeping only faces where keep_face(face) is True (shape keys kept)."""
    cp = src.copy(); cp.data = src.data.copy()
    bm = bmesh.new(); bm.from_mesh(cp.data)
    kill = [f for f in bm.faces if not keep_face(f)]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(cp.data); bm.free()
    return cp


EAR_W = ([0.38, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.76], [0.369, 0.365, 0.359, 0.354, 0.350, 0.342, 0.335, 0.326])


def is_ear(f):
    c = f.calc_center_median()
    x, h, y = abs(c.x) / H, (ZT - c.z) / H, c.y / H
    return 0.38 < h < 0.78 and -0.03 < y < 0.24 and x > np.interp(h, *EAR_W) + 0.004


def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    sc = bpy.context.scene
    head = bpy.data.objects["V2_Head"]
    for o in list(bpy.data.objects):
        if o.name.startswith("V2_HeadNrmProxy") or o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o)
    col = bpy.data.collections.new("EXPORT_" + PACK_ID); sc.collection.children.link(col)
    skin = bpy.data.materials.new("Skin_v2"); skin.use_nodes = True
    sb = skin.node_tree.nodes.get("Principled BSDF")
    sb.inputs["Base Color"].default_value = lin(SKIN_SRGB) + (1,); sb.inputs["Roughness"].default_value = 0.8
    made = []
    # head -> head / ears / mouth inside
    an_w = np.zeros(len(head.data.vertices), np.float32)
    head.data.attributes["an_w"].data.foreach_get("value", an_w)
    parts = [("CHR_Head", lambda f: f.material_index == 0 and not is_ear(f), "skin"),
             ("CHR_Ears", lambda f: f.material_index == 0 and is_ear(f), "skin"),
             ("CHR_MouthInside", lambda f: f.material_index in (1, 2), "flat")]
    for nm, keep, kind in parts:
        cp = split_copy(head, keep); cp.name = nm; cp.data.name = nm
        col.objects.link(cp)
        if nm == "CHR_Head":
            co = np.array([v.co[:] for v in cp.data.vertices])
            gn = np.array([v.normal[:] for v in cp.data.vertices])
            from mathutils.kdtree import KDTree
            kd = KDTree(len(head.data.vertices))
            for v in head.data.vertices:
                kd.insert(v.co, v.index)
            kd.balance()
            w = np.array([an_w[kd.find(v.co)[1]] for v in cp.data.vertices])
            nn = face_normals(co) * w[:, None] + gn * (1 - w[:, None])
            nn /= np.linalg.norm(nn, axis=1, keepdims=True)
            cp.data.normals_split_custom_set_from_vertices([tuple(v) for v in nn])
        if kind == "skin":
            cp.data.materials.clear(); cp.data.materials.append(skin)
        else:
            mats = [flat_material("%s_%d_emiss" % (nm, i), base_colour(m)) for i, m in enumerate(head.data.materials)]
            cp.data.materials.clear()
            for m in mats:
                cp.data.materials.append(m)
        made.append(cp)
    for o in list(bpy.data.objects):
        if o.type != "MESH" or o in made or o is head:
            continue
        spec = next((n for n in NAMES if o.name.startswith(n[0])), None)
        if spec is None:
            print("skip", o.name); continue
        side = "_L" if o.name.endswith("_L") else "_R" if o.name.endswith("_R") else ""
        cp = o.copy(); cp.data = o.data.copy(); cp.name = spec[1] + side; cp.data.name = spec[1] + side
        col.objects.link(cp)
        c = base_colour(o.data.materials[0])
        cp.data.materials.clear(); cp.data.materials.append(flat_material(cp.name + "_0_emiss", c))
        made.append(cp)
    # keys: the app test drives PF-VisAA etc. on the upper teeth too (they do not move: zero targets), aliases
    hk = [k.name for k in head.data.shape_keys.key_blocks[1:]]
    for cp in made:
        if cp.name == "CHR_TeethUpper":
            if cp.data.shape_keys is None:
                cp.shape_key_add(name="Basis")
            have = set(cp.data.shape_keys.key_blocks.keys())
            for k in hk:
                if k.startswith("PF-") and k not in have:
                    cp.shape_key_add(name=k, from_mix=False)
        ks = cp.data.shape_keys
        if ks:
            have = {k.name for k in ks.key_blocks}
            base = np.empty(len(cp.data.vertices) * 3, np.float32); ks.key_blocks[0].data.foreach_get("co", base)
            for app, srck, f in ALIASES:
                if srck in have and app not in have:
                    d = np.empty_like(base); ks.key_blocks[srck].data.foreach_get("co", d)
                    kb = cp.shape_key_add(name=app, from_mix=False); kb.data.foreach_set("co", base + f * (d - base))
            for kb in ks.key_blocks[1:]:
                kb.value = 0.0
        for m in list(cp.modifiers):
            cp.modifiers.remove(m)
        for a in [a.name for a in cp.data.attributes if a.name in ("ell_w", "toon_w", "an_w", "shade", "ear_f",
                                                                   "ear_lw", "ear_bowl")]:
            cp.data.attributes.remove(cp.data.attributes[a])
        for vg in list(cp.vertex_groups):
            cp.vertex_groups.remove(vg)
    # armature + sockets
    arm_d = bpy.data.armatures.new("CHR_Armature")
    arm = bpy.data.objects.new("CHR_Armature", arm_d); col.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    b = arm_d.edit_bones.new("DEF-Head"); b.head = (0, 0.03, O + 0.30 * S); b.tail = (0, 0.03, O + 0.95 * S)
    bpy.ops.object.mode_set(mode="OBJECT")
    for ob in made:
        vg = ob.vertex_groups.new(name="DEF-Head"); vg.add(range(len(ob.data.vertices)), 1.0, "REPLACE")
        md = ob.modifiers.new("Armature", "ARMATURE"); md.object = arm
        ob.parent = arm
    for name, (x, y, z) in SOCKETS.items():
        e = bpy.data.objects.new(name, None); col.objects.link(e)
        e.location = (x * S, y * S, O + z * S); e["socket_name"] = name
        e.parent = arm
    os.makedirs(FOLDER, exist_ok=True)
    for o in sc.objects:
        o.select_set(False)
    for o in col.objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(FOLDER, PACK_ID + ".gltf"), export_format="GLTF_SEPARATE",
                              use_selection=True, export_apply=False, export_yup=True, export_morph=True,
                              export_morph_normal=False, export_skins=True, export_def_bones=True, export_extras=True,
                              export_animations=False, export_cameras=False, export_lights=False)
    json.dump({"id": PACK_ID, "display_name": DISPLAY, "library": "humanoid", "slot": "body_adult", "socket": "SOC-Neck",
               "notes": "Head only (v2): new sculpted head - real mouth cavity, tooth arches and tongue; face pieces on "
                        "the curved face (no view keys). One mesh per element (CHR_*)."},
              open(os.path.join(FOLDER, "pack.json"), "w"), indent=2)
    man = os.path.join(R, "library", "manifest.json")
    data = json.load(open(man))
    data["packs"] = [p for p in data.get("packs", []) if p.get("id") != PACK_ID] + [
        {"id": PACK_ID, "library": "humanoid", "folder": "humanoid/bodies/adult/" + PACK_ID}]
    json.dump(data, open(man, "w"), indent=2)
    print("exported", PACK_ID, len(made), "meshes:", ", ".join(sorted(o.name for o in made)))


if __name__ == "__main__":
    main()
