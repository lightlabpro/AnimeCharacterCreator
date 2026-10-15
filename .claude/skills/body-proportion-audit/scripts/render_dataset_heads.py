"""Render reference GLBs for the picture checks (dataset pass 2, 2026-10-15). Run with Blender's Python (bpy module):

    python3 render_dataset_heads.py GLB_DIR MEASURED_JSON OUT_DIR

Two kinds of picture per model, because the measurement frame (measure_dataset.py: skinned vertices in bind space,
skeleton-based orientation) and Blender's import frame (node transforms, armature scale) do not always agree:
  <uid>_full.png   the textured model as Blender imports it, framed by its own bounding box (style / age / humanoid
                   check); <uid>_face.png the textured head, framed on the top of the bounding box (feature Boxes)
  <uid>_shape.png  the MEASURED geometry (hair, eyes, clothes removed as in the measurement) rebuilt as a plain mesh,
                   front and side, with the measured skull-top and chin rows drawn as red lines (landmark check)
frames.json records the pixel mapping of the shape renders.
"""
import json, os, re, sys
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_dataset as MD     # noqa: E402

RES = 560


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"; sh.color_type = "TEXTURE"
    sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.55, 0.6, 0.66)
    return sc


def cam(sc, loc, rot, ortho, res=(RES, RES)):
    for o in [o for o in sc.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(o)
    cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cd.ortho_scale = ortho
    c = bpy.data.objects.new("c", cd); sc.collection.objects.link(c); sc.camera = c
    c.location = loc; c.rotation_euler = rot
    sc.render.resolution_x, sc.render.resolution_y = res


def shot(sc, path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def world_verts(sc):
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in sc.objects:
        if o.type != "MESH":
            continue
        e = o.evaluated_get(dg); me = e.to_mesh()
        if len(me.vertices):
            co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3); M = np.array(o.matrix_world)
            out.append(co @ M[:3, :3].T + M[:3, 3])
        e.to_mesh_clear()
    return np.concatenate(out) if out else None


def main():
    d, mj, out = sys.argv[-3], sys.argv[-2], sys.argv[-1]
    os.makedirs(out, exist_ok=True)
    meas = {m["file"]: m for m in json.load(open(mj))}
    frames = {}
    for f in sorted(os.listdir(d)):
        m = meas.get(f)
        if not f.endswith(".glb") or not m:
            continue
        uid = f.split("__")[-1].split("_")[0]
        fr = {"file": f}
        try:
            # 1) textured, Blender's own frame
            sc = reset()
            bpy.ops.import_scene.gltf(filepath=os.path.join(d, f))
            W = world_verts(sc)
            lo, hi = W.min(0), W.max(0); Hb = hi[2] - lo[2]
            top = W[W[:, 2] > hi[2] - 0.12 * Hb]
            xh, yh = float(np.median(top[:, 0])), float(np.median(top[:, 1]))
            cam(sc, ((lo[0] + hi[0]) / 2, lo[1] - 3 * Hb, (lo[2] + hi[2]) / 2), (1.5708, 0, 0), 1.05 * max(Hb, hi[0] - lo[0]), (420, 560))
            shot(sc, os.path.join(out, uid + "_full.png"))
            cam(sc, (xh, lo[1] - 3 * Hb, hi[2] - 0.09 * Hb), (1.5708, 0, 0), 0.19 * Hb)
            shot(sc, os.path.join(out, uid + "_face.png"))
            fr["bbox_h"] = float(Hb)
            # 2) measured geometry, measurement frame
            if "lm" in m:
                posed = m.get("skin_space", "").startswith("node")
                V, T, J, info = MD.load_parts(os.path.join(d, f), posed=posed)
                rig = bool(J) and any(MD.BA.canon(n)[0] for n in J) and "skeleton disagrees" not in " ".join(m["flags"])
                V2, Jc, _ = MD.orient(np.asarray(V, float), J if rig else {})
                lm, fs = m["lm"], m["fs"]
                hh = lm["top"] - lm["chin"]
                sel = (np.abs(V2[:, 0] - lm["xc"]) < 0.9 * hh) & (np.abs(V2[:, 1] - lm["yc"]) < 0.9 * hh) & (V2[:, 2] > lm["chin"] - 0.6 * hh)
                Tk = np.asarray(T)[sel[np.asarray(T)].all(1)]
                sc = reset(); sc.display.shading.color_type = "SINGLE"
                me = bpy.data.meshes.new("m"); me.from_pydata(V2.tolist(), [], Tk.tolist()); me.update()
                ob = bpy.data.objects.new("m", me); sc.collection.objects.link(ob)
                zc = (lm["top"] + lm["chin"]) / 2; ortho = 1.7 * hh
                ang = 0.0 if fs < 0 else 3.14159
                cam(sc, (lm["xc"], lm["yc"] + fs * 3.0, zc), (1.5708, 0, ang), ortho)
                shot(sc, os.path.join(out, uid + "_sfront.png"))
                cam(sc, (lm["xc"] + 3.0, lm["yc"], zc), (1.5708, 0, 1.5708), ortho)
                shot(sc, os.path.join(out, uid + "_sside.png"))
                fr.update({"ortho": ortho, "zc": zc, "top": lm["top"], "chin": lm["chin"], "res": RES})
        except Exception as e:
            fr["error"] = repr(e)
        frames[uid] = fr
        print(uid, fr.get("error", "ok"), flush=True)
        json.dump(frames, open(os.path.join(out, "frames.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
