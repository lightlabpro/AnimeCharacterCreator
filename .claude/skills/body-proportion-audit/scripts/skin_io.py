"""Loads a skinned glTF/GLB for the anatomy and pose tools: vertices, triangles, JOINTS/WEIGHTS, bone names and hierarchy, bind
positions (from the inverse bind matrices), morph targets (sparse accessors included). Then orients the model from its skeleton
(up = +Z, left/right on x, forward = -Y) so every check can use plain world axes."""
import os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..", "library-pack-check", "scripts"))
import body_audit as ba
from check_pack import read_gltf

def _read(g, bufs, i):
    a = g["accessors"][i]; fmt, size = ba._COMP[a["componentType"]]; n = ba._NCOMP[a["type"]]; dt = np.dtype(fmt).newbyteorder("<")
    arr = np.array(ba._accessor(g, bufs, i)) if "bufferView" in a else np.zeros((a["count"], n), dt)
    sp = a.get("sparse")
    if sp:
        bi, bv = sp["indices"], g["bufferViews"][sp["indices"]["bufferView"]]; vv = g["bufferViews"][sp["values"]["bufferView"]]
        idt = np.dtype(ba._COMP[bi["componentType"]][0]).newbyteorder("<")
        idx = np.frombuffer(bufs[bv["buffer"]], idt, sp["count"], bv.get("byteOffset", 0) + bi.get("byteOffset", 0))
        val = np.frombuffer(bufs[vv["buffer"]], dt, sp["count"] * n, vv.get("byteOffset", 0) + sp["values"].get("byteOffset", 0)).reshape(-1, n)
        arr[idx] = val
    if a.get("normalized"): arr = arr.astype(np.float32) / float(np.iinfo(dt).max)
    return arr

def load(path, mesh_filter=None):
    """-> dict V, T, J (N,K) joint indices, W (N,K) weights, names, parents, jpos, targets {name: (N,3) deltas}, mesh_names. Z-up, not yet oriented."""
    g, chunk = read_gltf(path); bufs = ba._buffers(g, chunk, os.path.dirname(os.path.abspath(path)))
    nodes = g.get("nodes", []); parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}; cache = {}
    def world(i):
        if i not in cache: cache[i] = (world(parent[i]) if i in parent else np.eye(4)) @ ba._mat(nodes[i])
        return cache[i]
    zup = lambda P: np.stack([P[:, 0], -P[:, 2], P[:, 1]], 1)
    names, parents, jpos, base = [], [], [], {}
    for si, sk in enumerate(g.get("skins", [])):
        base[si] = len(names); at = {j: k for k, j in enumerate(sk["joints"])}
        ibm = _read(g, bufs, sk["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1) if "inverseBindMatrices" in sk else None
        for k, j in enumerate(sk["joints"]):
            n = nodes[j]; names.append(n.get("extras", {}).get("name") or n.get("name", ""))
            parents.append(base[si] + at[parent[j]] if parent.get(j) in at else -1)
            jpos.append(np.linalg.inv(ibm[k])[:3, 3] if ibm is not None else world(j)[:3, 3])
    Vs, Ts, Js, Ws, tgt, meshes, off = [], [], [], [], [], [], 0
    for i, n in enumerate(nodes):
        if "mesh" not in n or "skin" not in n: continue
        if mesh_filter and not re.search(mesh_filter, n.get("name", ""), re.I): continue
        meshes.append(n.get("name", ""))
        tn = g["meshes"][n["mesh"]].get("extras", {}).get("targetNames", [])
        for prim in g["meshes"][n["mesh"]]["primitives"]:
            at = prim.get("attributes", {})
            if "POSITION" not in at or "JOINTS_0" not in at or "WEIGHTS_0" not in at: continue
            P = _read(g, bufs, at["POSITION"]).astype(float); N = len(P)
            idx = _read(g, bufs, prim["indices"]).reshape(-1) if "indices" in prim else np.arange(N)
            Jk = [_read(g, bufs, at[f"JOINTS_{k}"]).astype(int) for k in range(8) if f"JOINTS_{k}" in at]
            Wk = [_read(g, bufs, at[f"WEIGHTS_{k}"]).astype(float) for k in range(8) if f"WEIGHTS_{k}" in at]
            Vs.append(zup(P)); Ts.append(idx.reshape(-1, 3).astype(int) + off)
            Js.append(np.concatenate(Jk, 1) + base[n["skin"]]); Ws.append(np.concatenate(Wk, 1))
            tgt.append((off, N, [(tn[t] if t < len(tn) else f"target{t}", zup(_read(g, bufs, tt["POSITION"]).astype(float)))
                                 for t, tt in enumerate(prim.get("targets", [])) if "POSITION" in tt]))
            off += N
    if not Vs: raise ValueError("no skinned mesh with JOINTS_0 and WEIGHTS_0 found")
    K = max(j.shape[1] for j in Js)
    pad = lambda A, v: np.pad(A, ((0, 0), (0, K - A.shape[1])), constant_values=v)
    V = np.concatenate(Vs); targets = {}
    for o, N, lst in tgt:
        for nm, D in lst:
            full = targets.setdefault(nm, np.zeros_like(V)); full[o:o + N] = D
    return dict(V=V, T=np.concatenate(Ts), J=np.concatenate([pad(j, 0) for j in Js]), W=np.concatenate([pad(w, 0.0) for w in Ws]), names=names,
                parents=parents, jpos=zup(np.array(jpos)) if jpos else np.zeros((0, 3)), targets=targets, mesh_names=meshes)

def orient(m):
    """Rotates the model (in place, returns it) so +Z is up, x is left/right and forward is -Y. Adds m['key'] = {'forearm_L': bone index, ...}
    and m['oriented'] = False when the skeleton could not be recognised (the checks then say unknown)."""
    names = m["names"]; pos = {n: m["jpos"][i] for i, n in reversed(list(enumerate(names)))}
    pick = ba.pick_names(names, lambda n: float(pos[n][2])); first = {n: i for i, n in reversed(list(enumerate(names)))}
    m["key"] = {k: first[n] for k, n in pick.items()}
    J = {k: tuple(m["jpos"][i]) for k, i in m["key"].items()}; R = ba.orientation(J)
    m["oriented"] = R is not None
    if R is None: return m
    f = None
    if "toe_L" in J and "foot_L" in J: f = np.array(J["toe_L"]) - np.array(J["foot_L"])
    elif "toe_R" in J and "foot_R" in J: f = np.array(J["toe_R"]) - np.array(J["foot_R"])
    f = None if f is None else R @ f
    if f is None or np.hypot(f[0], f[1]) < 1e-9:              # no toes: the foot mesh sticks out in front of the ankle
        a = m["jpos"][m["key"]["foot_L"]] if "foot_L" in m["key"] else None
        if a is not None:
            low = m["V"] @ R.T; low = low[low[:, 2] < (R @ a)[2] - 1e-6]
            if len(low): f = low.mean(0) - R @ a
    if f is not None and f[1] > 0: R = np.diag([-1.0, -1.0, 1.0]) @ R
    m["V"] = m["V"] @ R.T; m["jpos"] = m["jpos"] @ R.T
    m["targets"] = {k: D @ R.T for k, D in m["targets"].items()}; m["R"] = R
    return m
