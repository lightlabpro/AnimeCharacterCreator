"""Blender side. Everything that touches `bpy` lives here; the rest of the package is pure Python.

Written for Blender 5.x (Z up, forward -Y, 1 unit = 1 m). Run it from the Text Editor or the Python
console; see blender/scripts/run_validators.py. The pure checks are unit-tested outside Blender, this
file is only exercised inside it.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

try:  # pragma: no cover - only available inside Blender
    import bpy
    from mathutils import Vector
except ImportError:  # keep the module importable for docs and tests
    bpy = None
    Vector = None

from .model import SceneInfo, Vec
from .spec import BODY_OBJECTS


def _v(p) -> Vec:
    return (float(p[0]), float(p[1]), float(p[2]))


def snapshot(kind: str, with_verts: bool = True, body_name: Optional[str] = None,
             armature_name: Optional[str] = None) -> SceneInfo:
    """Read the active scene into a SceneInfo using the evaluated (shape-key-applied) body mesh."""
    if bpy is None:
        raise RuntimeError("bpy_adapter.snapshot must run inside Blender")
    info = SceneInfo(kind=kind, source=bpy.data.filepath or "<unsaved>")
    default_arm, default_body = BODY_OBJECTS[kind]
    arm_name, body_name = armature_name or default_arm, body_name or default_body
    for ob in bpy.context.scene.objects:
        info.objects.add(ob.name)
        info.custom_props[ob.name] = {k: ob[k] for k in ob.keys() if isinstance(ob[k], (str, int, float))}
        if ob.name.startswith("LM-"):
            info.markers[ob.name] = _v(ob.matrix_world.translation)
        if ob.type == "MESH":
            info.transforms[ob.name] = {"scale": _v(ob.scale), "rotation": _v(ob.rotation_euler),
                                        "location": _v(ob.location)}
            if ob.data.shape_keys:
                info.shape_keys[ob.name] = [k.name for k in ob.data.shape_keys.key_blocks]
            info.tris[ob.name] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
            if ob.data.polygons:
                info.quad_ratio[ob.name] = sum(1 for p in ob.data.polygons if len(p.vertices) == 4) / len(ob.data.polygons)
    arm = bpy.data.objects.get(arm_name)
    if arm and arm.type == "ARMATURE":
        mw = arm.matrix_world
        for b in arm.data.bones:
            info.bones[b.name] = (_v(mw @ b.head_local), _v(mw @ b.tail_local))
            if b.use_deform:
                info.deform_bones.add(b.name)
    body = bpy.data.objects.get(body_name)
    if with_verts and body and body.type == "MESH":
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        mesh = ev.to_mesh()
        mw = ev.matrix_world
        info.body_verts = [_v(mw @ v.co) for v in mesh.vertices]
        ev.to_mesh_clear()
    return info


def mesh_arrays(body_name: str):
    """Evaluated world-space (verts Nx3, faces) of an object, for the geometry/hygiene checks."""
    import numpy as np
    ob = bpy.data.objects[body_name]
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    mw = ev.matrix_world
    verts = np.array([tuple(mw @ v.co) for v in me.vertices], dtype=np.float64)
    faces = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return verts, faces


def load_markers(scene, path: str) -> None:
    """Landmarks placed by hand for a reference model: {"Crown": [x, y, z], ...} in Blender world units."""
    import json
    with open(path, "r", encoding="utf-8") as fh:
        for k, v in json.load(fh).items():
            scene.markers[k if k.startswith("LM-") else f"LM-{k}"] = (float(v[0]), float(v[1]), float(v[2]))


def sweep(kind: str, controls: List[Tuple[str, str]], values=(0.0, 0.5, 1.0)) -> Dict[str, Dict[float, Dict[str, float]]]:
    """Measure the metrics with one control at a time set to each value.

    controls: (name, where) where where is "key:<object>" for a shape key or "prop:<object>" for a custom
    property on that object (armature length properties). The original value is restored afterwards.
    """
    from . import measure
    results: Dict[str, Dict[float, Dict[str, float]]] = {}
    for name, where in controls:
        mode, obj_name = where.split(":", 1)
        ob = bpy.data.objects[obj_name]
        if mode == "key":
            holder = ob.data.shape_keys.key_blocks[name]
            get, set_ = (lambda: holder.value), (lambda x: setattr(holder, "value", x))
        else:
            get, set_ = (lambda: ob[name]), (lambda x: ob.__setitem__(name, x))
        original = get()
        results[name] = {}
        try:
            for v in values:
                # Length properties run 0.85..1.15; map the 0..1 sweep onto that range.
                set_(v if mode == "key" else 0.85 + 0.30 * v)
                bpy.context.view_layer.update()
                vals, _, _ = measure.metrics(snapshot(kind))
                results[name][v] = vals
        finally:
            set_(original)
            bpy.context.view_layer.update()
    return results


def pixels_to_mask(image_name: str):
    """Foreground mask (numpy bool, row 0 = top) from a Blender image: alpha if it has any, else background difference."""
    import numpy as np
    from . import silhouette
    img = bpy.data.images[image_name]
    w, h = img.size
    arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1]
    if img.channels == 4 and arr[..., 3].min() < 0.99:
        return silhouette.mask_from_alpha(arr)
    return silhouette.mask_from_rgb(arr[..., :3])


def place_basic_markers() -> List[str]:
    """Create Crown/Chin/Floor empties from the head-weighted vertices so the modeler can then nudge them.

    Eye, mouth, nipple, navel and pubis markers still have to be placed by hand: they are the judgement calls
    the validators exist to check, so guessing them here would make the check circular.
    """
    body = bpy.data.objects.get("CHR_Body")
    if body is None:
        return []
    group_ids = {g.index for g in body.vertex_groups if "head" in g.name.lower() and "DEF" in g.name}
    zs = []
    mw = body.matrix_world
    for v in body.data.vertices:
        if any(g.group in group_ids and g.weight > 0.5 for g in v.groups):
            zs.append((mw @ v.co).z)
    allz = [(mw @ v.co).z for v in body.data.vertices]
    made = []
    for name, z in (("LM-Floor", min(allz)), ("LM-Crown", max(zs) if zs else max(allz)), ("LM-Chin", min(zs) if zs else None)):
        if z is None or name in bpy.data.objects:
            continue
        e = bpy.data.objects.new(name, None)
        e.location = (0.0, 0.0, z)
        e.empty_display_type = "PLAIN_AXES"
        e.empty_display_size = 0.03
        bpy.context.scene.collection.objects.link(e)
        made.append(name)
    return made
