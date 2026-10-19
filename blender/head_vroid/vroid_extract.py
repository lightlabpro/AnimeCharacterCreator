"""q40: dump a VRoid export for the MHS3 pipeline - its textures (TEX_DIR/<material base name>.png, what
mhs3_reshape.py and mhs3_paint.py read) and vroid_mesh.npz (per mesh key: world vertices __V, triangles __T, per-corner
UVs __UVT - what mhs3_paint.tex3d rasterises; the format the q33 dump of 3f8f0119 used).

    bpyenv/bin/python vroid_extract.py IN.glb TEX_DIR MESH.npz
"""
import os
import sys

import bpy
import numpy as np


def key_of(mat_name):
    return mat_name.split("_Instance")[0].split(" (Instance")[0].replace("N00_000_00_", "").replace("N00_000_", "")


def main():
    src, texd, out = sys.argv[-3:]
    os.makedirs(texd, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    data = {}
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or not o.data.materials or not o.data.materials[0]:
            continue
        m = o.data.materials[0]
        base = m.name.split("_Instance")[0].split(" (Instance")[0]
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image is not None:
                img = n.image
                path = os.path.join(texd, base + ".png")
                img.filepath_raw = path; img.file_format = "PNG"; img.save()
                break
        me = o.data; me.calc_loop_triangles()
        M = np.array(o.matrix_world)
        co = np.array([v.co[:] for v in me.vertices])
        V = (np.c_[co, np.ones(len(co))] @ M.T)[:, :3]
        T = np.array([t.vertices[:] for t in me.loop_triangles], np.int32)
        uvl = me.uv_layers.active
        UVT = np.array([[uvl.data[li].uv[:] for li in t.loops] for t in me.loop_triangles], np.float32)
        k = key_of(m.name)
        data[k + "__V"] = V.astype(np.float32); data[k + "__T"] = T; data[k + "__UVT"] = UVT
        print(k, len(V), len(T))
    np.savez_compressed(out, **data)
    print("wrote", out, "and", texd)


if __name__ == "__main__":
    main()
