"""Extract normalised head meshes (h = 0 skull top .. 1 chin; x, y in head heights; face toward -y) from the verified
dataset models (measured.json landmarks) and our built head. Run with bpyenv python."""
import json, sys, os, re
import numpy as np
import bpy
OUT = sys.argv[1]
D = json.load(open('/mnt/user-data/uploads/Anime Character Creator/datasets_work/measured.json'))
VER = json.load(open('/home/claude/acc_wizard/knowledge/dataset-pass2/verified_shape.json'))
G = '/mnt/user-data/uploads/Anime Character Creator/datasets_work/glb_sel/'
SKIP = re.compile(r'hair|outline|glass|eye|lash|brow|tooth|teeth|tongue|cloth|armor|metal|belt|boot|glove|sock', re.I)

def mesh_tris(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    V, F, keep = [], [], []
    for o in objs:
        ev = o.evaluated_get(dg); me = ev.to_mesh(); me.calc_loop_triangles()
        mw = o.matrix_world
        off = len(V)
        V += [tuple(mw @ v.co) for v in me.vertices]
        mats = [m.name if m else '' for m in me.materials] or ['']
        for t in me.loop_triangles:
            mn = mats[t.material_index] if t.material_index < len(mats) else ''
            F.append([off + i for i in t.vertices]); keep.append(not SKIP.search(mn))
        ev.to_mesh_clear()
    return np.array(V), np.array(F), np.array(keep)

def norm_save(name, V, F, keep, top, chin, xc, yc):
    H = top - chin
    P = np.stack([(V[:, 0] - xc) / H, (V[:, 1] - yc) / H, (top - V[:, 2]) / H], 1)
    tri = P[F]
    c = tri.mean(1)
    sel = keep & (c[:, 2] > -0.05) & (c[:, 2] < 1.25) & (np.abs(c[:, 0]) < 0.6) & (np.abs(c[:, 1]) < 0.8)
    F2 = F[sel]
    # face toward -y: the nose / face front (h 0.55-0.8, |x| < 0.08) must be the minimum-y side
    m = (np.abs(P[:, 0]) < 0.08) & (P[:, 2] > 0.55) & (P[:, 2] < 0.8)
    used = np.unique(F2)
    mm = np.zeros(len(P), bool); mm[used] = True; m &= mm
    if m.sum() and np.percentile(P[m, 1], 2) > -np.percentile(P[m, 1], 98):
        P[:, 1] *= -1; P[:, 0] *= -1
    np.savez_compressed(os.path.join(OUT, name + '.npz'), v=P.astype(np.float32), f=F2.astype(np.int32))
    print(name, 'tris', len(F2), 'H', round(H, 4))

for e in D:
    hid = next((v for v in VER if v in e['file']), None)
    if not hid:
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=G + e['file'])
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    V, F, keep = mesh_tris(objs)
    lm = e['lm']
    norm_save('ref_' + hid[:8], V, F, keep, lm['top'], lm['chin'], lm['xc'], lm['yc'])

# ours: the built v2 head (basis shape)
if len(sys.argv) > 2:
    for blend in sys.argv[2:]:
        bpy.ops.wm.open_mainfile(filepath=blend)
        o = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('V2_Head') and 'Proxy' not in o.name)
        for kb in (o.data.shape_keys.key_blocks if o.data.shape_keys else []):
            kb.value = 0.0
        V, F, keep = mesh_tris([o])
        keep[:] = True
        top = V[:, 2].max()
        Hn = 0.22
        fr = (np.abs(V[:, 0]) < 0.03 * Hn) & (V[:, 1] < -0.15 * Hn) & (V[:, 2] < top - 0.7 * Hn)
        chin = V[fr, 2].min()
        norm_save('ours_' + os.path.basename(blend).split('.')[0], V, F, keep, top, chin, 0.0, 0.0)
