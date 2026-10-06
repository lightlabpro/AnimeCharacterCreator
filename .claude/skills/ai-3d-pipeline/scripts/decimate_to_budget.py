"""Reduce a mesh to a triangle budget in Blender, the way TripoSG's `--faces` does: merge close vertices first, then quadric edge collapse.
Run inside Blender (or the bpy module):

    blender -b scene.blend -P decimate_to_budget.py -- --object GeneratedBody --tris 24000 [--merge 0.0001] [--protect FaceGroup] [--out out.blend]

Rules (a failed rule exits 12, nothing is changed):
  - refuses a mesh with shape keys (Blender cannot apply Decimate to them): decimate the base mesh BEFORE adding ID-/PF- keys
  - refuses when the budget is not below the current triangle count after merging
  - --protect names a vertex group; its vertices keep detail (face, hands, joints) while the rest collapses
Reports triangles before and after. Quadric decimation keeps UVs and vertex weights approximately; check UV stretch and skinning afterwards.
It is a reduction tool, not a retopology tool: edge flow around eyes, mouth and joints still needs hand retopology (see ai-3d-pipeline stage 3)."""
import sys

def tri_count(obj):
    import bpy
    dg = bpy.context.evaluated_depsgraph_get(); e = obj.evaluated_get(dg); me = e.to_mesh(); me.calc_loop_triangles(); n = len(me.loop_triangles); e.to_mesh_clear(); return n

def decimate(obj, target, merge=1e-4, protect=None):
    """Returns (before, after). Raises ValueError for the refusals above."""
    import bpy, bmesh
    if obj.type != "MESH": raise ValueError(f"{obj.name} is not a mesh")
    if obj.data.shape_keys and len(obj.data.shape_keys.key_blocks) > 0:
        raise ValueError(f"{obj.name} has shape keys; decimate the base mesh before adding ID-/PF- keys")
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=merge); bm.to_mesh(obj.data); bm.free(); obj.data.update()
    before = tri_count(obj)
    if target >= before: raise ValueError(f"budget {target} is not below the current {before} triangles")
    mod = obj.modifiers.new("DecimateToBudget", "DECIMATE"); mod.decimate_type = "COLLAPSE"; mod.ratio = max(0.001, target / before); mod.use_collapse_triangulate = True
    if protect:
        if protect not in obj.vertex_groups: raise ValueError(f"vertex group {protect!r} not found")
        mod.vertex_group = protect; mod.invert_vertex_group = True; mod.vertex_group_factor = 1.0      # weight 1 = collapse most, so invert: weight 1 = keep
    bpy.context.view_layer.objects.active = obj
    with bpy.context.temp_override(object=obj, active_object=obj): bpy.ops.object.modifier_apply(modifier=mod.name)
    return before, tri_count(obj)

def main():
    import argparse, bpy
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument("--object", required=True); ap.add_argument("--tris", type=int, required=True)
    ap.add_argument("--merge", type=float, default=1e-4); ap.add_argument("--protect"); ap.add_argument("--out")
    a = ap.parse_args(argv)
    obj = bpy.data.objects.get(a.object)
    if obj is None: print(f"error: no object named {a.object}", file=sys.stderr); return 2
    try: before, after = decimate(obj, a.tris, a.merge, a.protect)
    except ValueError as e: print(f"DECIMATE FAILED: {e}"); return 12
    print(f"DECIMATE_OK {a.object}: {before} -> {after} triangles (budget {a.tris})")
    if a.out: bpy.ops.wm.save_as_mainfile(filepath=a.out)
    return 0

if __name__ == "__main__":
    sys.exit(main())
