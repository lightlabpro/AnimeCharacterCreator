"""q17: export the n56 head (every face element its own mesh) as a pack the Anime Character Creator can import.

    exec(open(r"<repo>\\blender\\newhead\\export_head_pack.py").read(), {"TAG": "n56", "REPO": r"<repo>"})   # after apply()

Sammy (2026-10-15): "upload the model to the tool so we can also begin testing the tool with the model you made ... make
sure the elements are separated so the tool can tweak them precisely."

What it does (the working scene is not changed; everything happens on copies in a temporary collection that is removed
afterwards):
  - copies every mesh of NEW_HEAD_<tag> and renames it to a contract-style CHR_ name, one mesh per face element
    (head, ears, eye white / iris / lid line / lid cover / brow / brow shade per side, nose shade / highlight / line,
    mouth line / inside / teeth / tongue / lower lip line / lip shadow) - each keeps its own ID- / PF- shape keys
  - drops the old ear shell vertices (the head's SkinOnly mask) with the shape keys kept, and the Blender-only
    modifiers (solidify outline, ear thickness, subdivision) - the app draws its own outline
  - replaces the node materials with glTF-safe ones the app's toon shader understands: skin -> a lit "Skin" material,
    every painted element -> flat colour ("..._emiss": black base + emissive colour, the iris keeps its texture)
  - adds an armature with one DEF-Head bone (every mesh skinned to it) and SOC- sockets at the head (HeadTop,
    HairScalp, HairFront, HairSide_L/R, HairBack, Ear_L/R, Eyewear, Neck), moves the head to x = 0
  - VW- (camera-angle) keys are left out: the app has no view-angle driver yet, and they would only add morph memory
  - exports glTF Separate to library/humanoid/bodies/adult/<PACK_ID>/ with pack.json, updates library/manifest.json and
    runs check_pack.py. A head-only pack fails the body checks that need a full body (height, origin at the feet): that
    is expected and reported, the app still loads it as the body and hides the procedural one.
"""
import json
import os

import bpy
import numpy as np

TAG = globals().get("TAG", "n56")
R = globals().get("REPO") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PACK_ID = "head_mhs3_" + TAG
DISPLAY = "MHS3 head %s (test, head only)" % TAG
FOLDER = os.path.join(R, "library", "humanoid", "bodies", "adult", PACK_ID)
SKIN_SRGB = (232, 197, 170)
SHADE_SRGB = (173, 119, 100)   # q18: the painted nose / lip shadow as Blender renders it (toon shadow + NOSE_TINT, sampled
                               # on q17_expression_sheet); the shade material is a node group, and the old lookup took only
                               # its mauve tint, so the app drew a purple nose blob
CLEAR_NORMALS = True

NAMES = [  # (prefix of the scene object, export name, material kind, colour fallback sRGB)
    ("NEW_Head_", "CHR_Head", "skin", SKIN_SRGB),
    ("NEW_Ears_", "CHR_Ears", "skin", SKIN_SRGB),
    ("RigEyeWhite_", "CHR_EyeWhite", "flat", (236, 236, 236)),
    ("RigIris_", "CHR_Iris", "flat", (120, 190, 120)),
    ("RigLidLine_", "CHR_LidLine", "flat", (50, 34, 28)),
    ("RigLidCover_", "CHR_LidCover", "flat", SKIN_SRGB),
    ("RigBrowShade_", "CHR_BrowShade", "flat", (200, 160, 130)),
    ("RigBrow_", "CHR_Brow", "flat", (122, 95, 71)),
    ("NewNoseShade_", "CHR_NoseShade", "flat", (190, 130, 105)),
    ("NewNoseHL_", "CHR_NoseHighlight", "flat", (245, 222, 205)),
    ("NewNoseLine_", "CHR_NoseLine", "flat", (150, 100, 80)),
    ("NewMouthLine_", "CHR_MouthLine", "flat", (90, 40, 35)),
    ("NewMouthInside_", "CHR_MouthInside", "flat", (96, 56, 56)),
    ("NewMouthTeeth_", "CHR_TeethUpper", "flat", (240, 238, 232)),
    ("NewMouthTongue_", "CHR_Tongue", "flat", (210, 115, 95)),
    ("NewMouthThroat_", "CHR_MouthThroat", "flat", (128, 60, 56)),        # q19
    ("NewMouthTeethShade_", "CHR_TeethShade", "flat", (200, 198, 214)),   # q19
    ("NewMouthDeep_", "CHR_MouthDeep", "flat", (60, 30, 30)),            # q20 (only when MOUTH_DEEP > 0)
    ("NewUpperLip_", "CHR_UpperLipShade", "flat", (190, 130, 105)),      # q20 (only when UPPER_LIP_SHADE > 0)
    ("NewMouthLower_", "CHR_MouthLower", "flat", (90, 40, 35)),
    ("NewLipShadow_", "CHR_LipShadow", "flat", (190, 130, 105)),
]
ALIASES = [  # (app key, source key, factor): the app drives these names (knowledge/expected-contract.json)
    ("PF-BrowRaise", "PF-BrowUp", 1.0), ("PF-BrowLower", "PF-BrowDown", 1.0), ("PF-BrowFurrow", "PF-BrowAngry", 1.0),
    ("PF-Squint", "PF-EyeHappy", 1.0), ("PF-LidUpperDown", "PF-EyeSad", 1.0),
    ("PF-VisSmall", "PF-VisAA", 0.35), ("PF-VisMid", "PF-VisAA", 0.65), ("PF-VisIH", "PF-VisEE", 0.6),
    ("PF-VisOO", "PF-VisOH", 0.75), ("PF-Surprise", "PF-VisOH", 0.8),
]
SOCKETS = {  # name: (x, y, z) in head units above the chin (S = 0.262 m), y forward is -
    "SOC-HeadTop": (0.0, 0.02, 1.0), "SOC-HairScalp": (0.0, 0.05, 0.92), "SOC-HairFront": (0.0, -0.30, 0.80),
    "SOC-HairSide_L": (0.36, 0.05, 0.62), "SOC-HairSide_R": (-0.36, 0.05, 0.62), "SOC-HairBack": (0.0, 0.42, 0.62),
    "SOC-Ear_L": (0.40, 0.04, 0.42), "SOC-Ear_R": (-0.40, 0.04, 0.42), "SOC-Eyewear": (0.0, -0.40, 0.47),
    "SOC-Neck": (0.0, 0.03, -0.05),
}
S, O = 0.262, 1.4826


FACE_NORMALS = True
EXPORT_VIEW_KEYS = True   # q18: VW-Yaw_L/R, VW-Side_L/R ride along for the app to drive from the camera yaw (inbox item); the app ignores them until then
FACE_FORWARD, CHIN_LIT = 2.5, 1.0        # apply_look.py values


def _sm(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def _face_normals(Ph):
    """apply_look._target_normals: the ellipsoid normal pushed toward the viewer on the face plane (head units)."""
    y, z = Ph[:, 1], Ph[:, 2]
    c, r = np.array([0.0, -0.02, 0.47]), np.array([0.40, 0.46, 0.56])
    pe = (Ph - c) / r ** 2
    pe /= np.linalg.norm(pe, axis=1, keepdims=True)
    lo = 0.07 * CHIN_LIT
    face = _sm(0.0, -0.25, y) * _sm(0.05 - lo, 0.15 - lo, z) * (1 - _sm(0.62, 0.75, z))
    pe = pe + np.array([0.0, -FACE_FORWARD, 0.0]) * face[:, None]
    return pe / np.linalg.norm(pe, axis=1, keepdims=True)


def _lin(c):
    return tuple(((v / 255.0 + 0.055) / 1.055) ** 2.4 for v in c)


def _emission_of(mat, fallback):
    """The flat colour a painted material shows: its Emission colour, else its base colour, else the fallback."""
    if mat and mat.name.startswith("MAT_PaintShade"):
        return _lin(SHADE_SRGB), None
    if mat and mat.node_tree:
        for n in mat.node_tree.nodes:
            if n.type == "EMISSION" and not n.inputs["Color"].is_linked:
                return tuple(n.inputs["Color"].default_value[:3]), None
            if n.type == "EMISSION" and n.inputs["Color"].is_linked:
                src = n.inputs["Color"].links[0].from_node
                if src.type == "TEX_IMAGE":
                    return (1.0, 1.0, 1.0), src.image
            if n.type == "RGB":
                return tuple(n.outputs[0].default_value[:3]), None
    return _lin(fallback), None


def _flat_material(name, colour, image=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1)
    bsdf.inputs["Emission Color"].default_value = tuple(colour) + (1,)
    bsdf.inputs["Emission Strength"].default_value = 1.0
    if image is not None:
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = image
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    m.use_backface_culling = False
    return m


def _skin_material():
    m = bpy.data.materials.new("Skin_" + TAG)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = _lin(SKIN_SRGB) + (1,)
    b.inputs["Roughness"].default_value = 0.8
    return m


def _drop_masked(ob):
    """Delete the vertices the SkinOnly mask hid (old ear shell), keeping every shape key."""
    import bmesh
    mods = [m for m in ob.modifiers if m.type == "MASK"]
    if not mods:
        return 0
    md = mods[0]
    vg = ob.vertex_groups.get(md.vertex_group)
    if vg is None:
        return 0
    inside = np.zeros(len(ob.data.vertices), bool)
    for v in ob.data.vertices:
        for g in v.groups:
            if g.group == vg.index and g.weight > md.threshold:
                inside[v.index] = True
    drop = inside if md.invert_vertex_group else ~inside
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in np.nonzero(drop)[0]], context="VERTS")
    bm.to_mesh(ob.data); bm.free()
    return int(drop.sum())


HELD = []


def _hold(name):
    """A scene object already called <name> (Sammy's character file has CHR_Tongue, CHR_Armature ...) gets a temporary
    name so the export copy keeps the exact contract name; restored after the export."""
    o = bpy.data.objects.get(name)
    if o is not None:
        o.name = name + "__held"
        HELD.append((o, name))


def build():
    src = bpy.data.collections["NEW_HEAD_" + TAG]
    tmp = bpy.data.collections.new("EXPORT_" + PACK_ID)
    bpy.context.scene.collection.children.link(tmp)
    off = None
    made = []
    skin = _skin_material()
    for ob in list(src.all_objects):
        if ob.type != "MESH":
            continue
        spec = next((n for n in NAMES if ob.name.startswith(n[0])), None)
        if spec is None:
            print("skip", ob.name); continue
        prefix, ename, kind, fb = spec
        side = "_L" if ob.name.endswith("_L") else "_R" if ob.name.endswith("_R") else ""
        cp = ob.copy(); cp.data = ob.data.copy(); tmp.objects.link(cp)
        _hold(ename + side)
        cp.name = ename + side
        for ca in list(cp.data.color_attributes):         # shade / ear masks are Blender-shader data; glTF would
            cp.data.color_attributes.remove(ca)           # turn them into vertex colours (pink blotches in the app)
        cp.data.name = ename + side
        if off is None:
            off = ob.location.copy()
        cp.location = ob.location - off
        if ename == "CHR_Head":
            print("dropped %d masked ear-shell verts" % _drop_masked(cp))
        if ename == "CHR_Head" and FACE_NORMALS:
            # q18: the Blender look shades the face with an analytic normal field (head ellipsoid, face plane turned
            # toward the viewer: apply_look._target_normals) evaluated per pixel. Baked here as custom normals, so the
            # app's toon light gives the same clean MHS3 shadow (only at the far edge) instead of shading the raw form
            co = np.empty(len(cp.data.vertices) * 3, np.float32); cp.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
            Ph = np.stack([co[:, 0] / S, co[:, 1] / S, (co[:, 2] - O) / S], 1)
            nn = _face_normals(Ph)
            cp.data.normals_split_custom_set_from_vertices([tuple(v) for v in nn])
        elif kind == "skin" and CLEAR_NORMALS and cp.data.has_custom_normals:
            # the Blender look bends the skin normals toward a lit direction for its own toon pass; the app lights the
            # real form, and those bent normals drew pink shadow blotches at the temples and the neck
            with bpy.context.temp_override(object=cp, active_object=cp, selected_objects=[cp]):
                bpy.ops.mesh.customdata_custom_splitnormals_clear()
            for poly in cp.data.polygons:
                poly.use_smooth = True
        for m in list(cp.modifiers):
            cp.modifiers.remove(m)
        ks = cp.data.shape_keys
        if ks:                                            # app-name aliases (scaled copies of our keys)
            have = {k.name for k in ks.key_blocks}
            base = np.empty(len(cp.data.vertices) * 3, np.float32); ks.key_blocks[0].data.foreach_get("co", base)
            for app, srck, f in ALIASES:
                if srck in have and app not in have:
                    d = np.empty_like(base); ks.key_blocks[srck].data.foreach_get("co", d)
                    kb = cp.shape_key_add(name=app, from_mix=False); kb.data.foreach_set("co", base + f * (d - base))
        if ks:                                            # VW- keys out, every key at 0
            for kb in list(ks.key_blocks[1:]):
                if kb.name.startswith("VW-") and not EXPORT_VIEW_KEYS:
                    cp.shape_key_remove(kb)
                else:
                    kb.value = 0.0
        if kind == "skin":
            cp.data.materials.clear(); cp.data.materials.append(skin)
        else:
            mats = []
            for i, mt in enumerate(ob.data.materials):
                col, img = _emission_of(mt, fb)
                mats.append(_flat_material("%s%s_%d_emiss" % (ename, side, i), col, img))
            cp.data.materials.clear()
            for mt in mats:
                cp.data.materials.append(mt)
        made.append(cp)
    # armature + sockets
    arm_d = bpy.data.armatures.new("CHR_Armature")
    _hold("CHR_Armature")
    arm = bpy.data.objects.new("CHR_Armature", arm_d); tmp.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    b = arm_d.edit_bones.new("DEF-Head"); b.head = (0, 0.03, O + 0.30 * S); b.tail = (0, 0.03, O + 0.95 * S)
    bpy.ops.object.mode_set(mode="OBJECT")
    for ob in made:
        vg = ob.vertex_groups.new(name="DEF-Head"); vg.add(range(len(ob.data.vertices)), 1.0, "REPLACE")
        md = ob.modifiers.new("Armature", "ARMATURE"); md.object = arm
        ob.parent = arm
    for name, (x, y, z) in SOCKETS.items():
        _hold(name)
        e = bpy.data.objects.new(name, None); tmp.objects.link(e)
        e.location = (x * S, y * S, O + z * S); e["socket_name"] = name
        e.parent = arm
    return tmp, made, arm


def export():
    tmp, made, arm = build()
    os.makedirs(FOLDER, exist_ok=True)
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in tmp.objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(FOLDER, PACK_ID + ".gltf"), export_format="GLTF_SEPARATE",
                              use_selection=True, export_apply=False, export_yup=True, export_morph=True,
                              export_morph_normal=False, export_skins=True, export_def_bones=True, export_extras=True,
                              export_animations=False, export_cameras=False, export_lights=False)
    json.dump({"id": PACK_ID, "display_name": DISPLAY, "library": "humanoid", "slot": "body_adult", "socket": "SOC-Neck",
               "notes": "Head only (q17 test pack): every face element is its own mesh (CHR_*), ID-/PF- keys per element."},
              open(os.path.join(FOLDER, "pack.json"), "w"), indent=2)
    man = os.path.join(R, "library", "manifest.json")
    data = json.load(open(man)) if os.path.exists(man) else {"packs": []}
    data["packs"] = [p for p in data.get("packs", []) if p.get("id") != PACK_ID] + [
        {"id": PACK_ID, "library": "humanoid", "folder": "humanoid/bodies/adult/" + PACK_ID}]
    json.dump(data, open(man, "w"), indent=2)
    # clean up the copies
    for o in list(tmp.objects):
        d = o.data
        bpy.data.objects.remove(o)
        if d is not None and d.users == 0:
            (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.armatures).remove(d)
    bpy.data.collections.remove(tmp)
    for o, name in HELD:
        o.name = name
    HELD.clear()
    print("exported %s: %d meshes -> %s" % (PACK_ID, len(made), FOLDER))
    return FOLDER


if __name__ in ("__main__", "export_head_pack") or globals().get("RUN", True):
    export()
