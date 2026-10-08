"""Learn a mean anime head surface from the verified dataset models (measured only, no mesh copied).

Each head is put in a common frame (chin at z=0, skull top at z=1, forward -Y, centred on its head axis), then a
radial height map r(lon, lat) is ray-cast from C=(0,0,0.55) with Blender's BVH. The per-direction median over the
models is the learned surface; it is mirrored to be symmetric. Holes (eye openings) make single rays fall inward;
the median ignores them.
"""
import sys, os, json, math, numpy as np
sys.path.insert(0, "/home/claude/acc_wizard/.claude/skills/body-proportion-audit/scripts")
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import measure_dataset as MD

S = "/tmp/claude-0/-home-claude-animecharactercreator/464105bc-a977-5cf5-aba4-7fc9139186c6/scratchpad"
D = "/mnt/user-data/uploads/Anime Character Creator/datasets_work/glb_sel"
R = json.load(open(S + "/sheet_recs.json"))
bands = json.load(open(S + "/dataset_bands.json"))
files = bands["models"]
NLON, NLAT = 120, 90
lon = np.linspace(-math.pi, math.pi, NLON, endpoint=False)          # 0 = forward (-Y), +pi/2 = character's left (+X)
lat = np.linspace(-math.pi / 2 + 0.02, math.pi / 2 - 0.02, NLAT)
C = np.array([0.0, 0.0, 0.45])
dirs = np.zeros((NLAT, NLON, 3))
for i, la in enumerate(lat):
    for j, lo in enumerate(lon):
        dirs[i, j] = (math.cos(la) * math.sin(lo), -math.cos(la) * math.cos(lo), math.sin(la))
maps = []
for f in files:
    r = R[f]; lm = r["lm"]
    posed = (r.get("skin_space") or "").startswith("node")
    V, T, J, _ = MD.load_parts(os.path.join(D, f), posed=posed)
    V2, Jc, _ = MD.orient(np.asarray(V, float), J if MD.rig_agrees(V, J) else {})
    H = float(np.ptp(V2[:, 2])); fs, _ = MD.forward_sign(V2, Jc, float(V2[:, 2].min()), H)
    hh = lm["top"] - lm["chin"]
    # head depth centre at 0.3 H below the top
    # head depth centre: skull verts between 0.55 and 0.85 H above the chin, near the head axis (robust percentiles)
    zr = (V2[:, 2] - lm["chin"]) / hh
    band = V2[(zr > 0.55) & (zr < 0.85) & (np.abs(V2[:, 0] - lm["xc"]) < 0.3 * hh) & (np.abs(V2[:, 1] - lm["yc"]) < 0.8 * hh)]
    yc = 0.5 * (np.percentile(band[:, 1], 1) + np.percentile(band[:, 1], 99)) if len(band) > 50 else lm["yc"]
    P = np.stack([(V2[:, 0] - lm["xc"]) / hh, -fs * (V2[:, 1] - yc) / hh, (V2[:, 2] - lm["chin"]) / hh], 1)
    keep = (P[:, 2] > -0.6) & (np.abs(P[:, 0]) < 1.0) & (np.abs(P[:, 1]) < 1.0)
    Tk = T[keep[T].all(1)]
    bvh = BVHTree.FromPolygons([Vector(p) for p in P], [tuple(int(i) for i in t) for t in Tk])
    m = np.full((NLAT, NLON), np.nan)
    for i in range(NLAT):
        for j in range(NLON):
            d = dirs[i, j]
            o = C + d * 1.5
            hit = bvh.ray_cast(Vector(o), Vector(-d), 1.5)
            if hit[0] is not None:
                m[i, j] = 1.5 - hit[3]
    maps.append(m)
    print(f[-20:-9], "hits %.2f" % np.isfinite(m).mean(), "front r at eye level %.3f" % np.nanmedian(m[int(NLAT * 0.55), NLON // 2 - 2:NLON // 2 + 2]), flush=True)
M = np.array(maps)
# outlier rejection: a model whose map is far from the median everywhere (bad landmarks or frame) is dropped
use = np.ones(len(M), bool)
for _ in range(3):
    med = np.nanmedian(M[use], 0)
    face = np.abs(lat)[:, None] < 1.2
    dev = np.array([np.nanmedian(np.abs(m - med)[face.repeat(NLON, 1)]) for m in M])
    cut = max(0.03, 2.5 * np.median(dev[use]))
    use = dev < cut
print("kept", int(use.sum()), "of", len(M), "dev", np.round(dev, 3).tolist())
med = np.nanmedian(M[use], 0)
mir = med[:, ::-1]          # lon -> -lon: index j -> NLON - j  (lon grid is symmetric about 0 with endpoint False)
mir = np.roll(mir, 1, axis=1)
sym = np.nanmean(np.stack([med, mir]), 0)
np.savez(S + "/mean_head.npz", r=sym, lon=lon, lat=lat, C=C, all=M, files=np.array(files), use=use)
print("done", np.isnan(sym).sum(), "nan cells")
