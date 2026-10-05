"""Builders used by the Blender integration tests. Needs bpy (pip install bpy==5.0.1 in Python 3.11, or run inside Blender)."""
import math
import bpy      # must come before bmesh when Blender runs as a module
import bmesh
from mathutils import Matrix, Vector

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def link(o): bpy.context.scene.collection.objects.link(o); return o

def mesh_object(name, verts, faces):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    return link(bpy.data.objects.new(name, me))

def ellipsoid(name, centre, radii, segments=32, rings=24):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2])) + Vector(centre)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return link(bpy.data.objects.new(name, me))

def character(shape_key_value=0.0):
    """A skinned 1.72 m body in Blender convention (+Z up, forward -Y, feet at z=0) with the pieces the creator contract needs:
    ID-/PF- shape keys, Rigify-style dotted DEF- bones plus a non-deform helper bone, SOC- empties parented to a bone with a
    socket_name custom property, and a POSE-tpose action."""
    bm = bmesh.new()
    for cx, cz, sx, sz in [(0, 0.45, 0.30, 0.9), (0, 1.15, 0.42, 0.55), (0, 1.55, 0.22, 0.34)]:
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((cx, 0, cz)) @ Matrix.Diagonal((sx, 0.2, sz, 1)))
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=6, use_grid_fill=True)
    me = bpy.data.meshes.new("CHR_Body"); bm.to_mesh(me); bm.free()
    body = link(bpy.data.objects.new("CHR_Body", me))
    body.shape_key_add(name="Basis")
    for k in ("ID-FaceRound", "ID-EyeSize", "PF-Blink", "PF-JawOpen"):
        sk = body.shape_key_add(name=k)
        for v in sk.data:
            if v.co.z > 1.4: v.co.x *= 1.05
        sk.value = shape_key_value
    ad = bpy.data.armatures.new("CHR_Armature"); arm = link(bpy.data.objects.new("CHR_Armature", ad))
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="EDIT")
    for name, head, tail, deform in (("DEF-spine", (0, 0, 0.9), (0, 0, 1.4), True), ("DEF-head", (0, 0, 1.4), (0, 0, 1.72), True),
                                     ("DEF-upper_arm.L", (0.25, 0, 1.4), (0.6, 0, 1.4), True), ("DEF-upper_arm.R", (-0.25, 0, 1.4), (-0.6, 0, 1.4), True),
                                     ("MCH-helper", (0, 0, 0.5), (0, 0, 0.7), False)):
        b = ad.edit_bones.new(name); b.head = head; b.tail = tail; b.use_deform = deform
    bpy.ops.object.mode_set(mode="OBJECT")
    for n in ("DEF-spine", "DEF-head"): body.vertex_groups.new(name=n)
    for v in me.vertices: body.vertex_groups["DEF-head" if v.co.z > 1.4 else "DEF-spine"].add([v.index], 1.0, "REPLACE")
    body.modifiers.new("Armature", "ARMATURE").object = arm; body.parent = arm
    for sn, loc in (("SOC-HeadTop", (0, 0, 1.78)), ("SOC-Chest", (0, 0, 1.3)), ("SOC-HairFront", (0, -0.1, 1.7))):
        e = link(bpy.data.objects.new(sn, None)); e.parent = arm; e.parent_type = "BONE"; e.parent_bone = "DEF-head"
        e.matrix_world.translation = Vector(loc); e["socket_name"] = sn
    arm.animation_data_create(); act = bpy.data.actions.new("POSE-tpose"); arm.animation_data.action = act
    bpy.ops.object.mode_set(mode="POSE"); pb = arm.pose.bones["DEF-upper_arm.L"]; pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = (1, 0, 0, 0); pb.keyframe_insert("rotation_quaternion", frame=1)
    pb.rotation_quaternion = (math.cos(math.radians(45)), 0, math.sin(math.radians(45)), 0); pb.keyframe_insert("rotation_quaternion", frame=2)
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.animation_data.action = None
    return body, arm
