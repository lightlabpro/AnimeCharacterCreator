"""q40: bring any VRoid export into the frame of the reference export 3f8f0119 so the validated MHS3 pipeline
(mhs3_reshape.py / mhs3_paint.py / mhs3_hair.py, all measured in that frame) runs on it unchanged.

    bpyenv/bin/python vroid_normalize.py BASE.glb REF.glb OUT.glb

Every VRoid export shares the face mesh (Face_00_SKIN, 2266 verts) but glTF exports order them differently, so the
frame is solved by shape: the best of the 24 axis-aligned rotations (scale + translation from the face bounding box),
then scaled ICP (nearest-neighbour Umeyama iterations) of the base face onto the reference face; applied to the root
object(s). It fixes Sketchfab Y-up imports, models
facing -Y and exports at another scale (ea4402ae is 2.4 m tall). Prints the residual (face shape difference that
remains - the VRoid face sliders of that model).
"""
import sys

import bpy
import numpy as np
from mathutils import Matrix


def face_verts():
    o = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.data.materials and o.data.materials[0]
             and "Face_00_SKIN" in o.data.materials[0].name)
    M = np.array(o.matrix_world)
    co = np.array([v.co[:] for v in o.data.vertices])
    return (np.c_[co, np.ones(len(co))] @ M.T)[:, :3]


def umeyama(src, dst):
    ms, md = src.mean(0), dst.mean(0)
    s0, d0 = src - ms, dst - md
    U, S, Vt = np.linalg.svd(d0.T @ s0 / len(src))
    D = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        D[2, 2] = -1
    R = U @ D @ Vt
    c = (S * np.diag(D)).sum() / (s0 ** 2).sum() * len(src)
    t = md - c * R @ ms
    T = np.eye(4); T[:3, :3] = c * R; T[:3, 3] = t
    return T, c


def main():
    base, ref, out = sys.argv[-3:]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=ref)
    R = face_verts()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=base)
    B = face_verts()
    from scipy.spatial import cKDTree
    import itertools
    tree = cKDTree(R)
    best = None
    for perm in itertools.permutations(range(3)):
        for sg in itertools.product((1, -1), repeat=3):
            Rm = np.zeros((3, 3))
            for i in range(3):
                Rm[i, perm[i]] = sg[i]
            if np.linalg.det(Rm) < 0:
                continue
            P = B @ Rm.T
            s_ = (R.max(0) - R.min(0)).mean() / (P.max(0) - P.min(0)).mean()
            P = P * s_; P += (R.max(0) + R.min(0)) / 2 - (P.max(0) + P.min(0)) / 2
            d = tree.query(P)[0].mean()
            if best is None or d < best[0]:
                T0 = np.eye(4); T0[:3, :3] = s_ * Rm; T0[:3, 3] = P.mean(0) - (s_ * Rm @ B.T).T.mean(0)
                best = (d, T0)
    T = best[1]
    for _ in range(40):
        Bt = (np.c_[B, np.ones(len(B))] @ T.T)[:, :3]
        idx = tree.query(Bt)[1]
        T, scale = umeyama(B, R[idx])
    scale = np.cbrt(abs(np.linalg.det(T[:3, :3])))
    Bt = (np.c_[B, np.ones(len(B))] @ T.T)[:, :3]
    res = cKDTree(R).query(Bt)[0]
    print("scale %.4f  residual mean %.2f mm, max %.2f mm" % (scale, res.mean() * 1000, res.max() * 1000))
    Tm = Matrix(T.tolist())
    for o in [o for o in bpy.context.scene.objects if o.parent is None]:
        if o.type == "MESH" and o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o); continue
        o.matrix_world = Tm @ o.matrix_world
    bpy.context.view_layer.update()
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_image_format="AUTO")
    print("wrote", out)


if __name__ == "__main__":
    main()
