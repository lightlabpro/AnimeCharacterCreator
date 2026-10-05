"""A skinned humanoid glTF built in numpy for the anatomy and pose tests: tube limbs with a real bone hierarchy, smooth
or rigid weights, five fingers per hand, optional defects. Z up, forward -Y, 1.0 high, feet at z=0."""
import base64, json
import numpy as np

# name -> (parent, head xyz)
def skeleton(fingers=5, finger_segments=3):
    S = {"DEF-hips": (None, (0, 0, .53)), "DEF-spine": ("DEF-hips", (0, 0, .60)), "DEF-chest": ("DEF-spine", (0, 0, .70)),
         "DEF-neck": ("DEF-chest", (0, 0, .82)), "DEF-head": ("DEF-neck", (0, 0, .85))}
    for s, x in (("L", 1), ("R", -1)):
        S[f"DEF-upper_arm.{s}"] = ("DEF-chest", (x * .20, 0, .78)); S[f"DEF-forearm.{s}"] = (f"DEF-upper_arm.{s}", (x * .21, 0, .63))
        S[f"DEF-hand.{s}"] = (f"DEF-forearm.{s}", (x * .22, 0, .48))
        S[f"DEF-thigh.{s}"] = ("DEF-hips", (x * .09, 0, .53)); S[f"DEF-shin.{s}"] = (f"DEF-thigh.{s}", (x * .09, 0, .30))
        S[f"DEF-foot.{s}"] = (f"DEF-shin.{s}", (x * .09, 0, .07)); S[f"DEF-toe.{s}"] = (f"DEF-foot.{s}", (x * .09, -.09, .02))
        n = fingers if s == "L" else fingers                      # callers patch one side to make defects
        for k, f in enumerate(("thumb", "index", "middle", "ring", "little")[:n]):
            prev = f"DEF-hand.{s}"
            for seg in range(finger_segments):
                nm = f"DEF-{f}.{seg + 1:02d}.{s}"; S[nm] = (prev, (x * (.22 + .012 * (k - 2)), 0, .48 - .02 - .02 * seg)); prev = nm
    return S

def tube(path, radius, ring=8):
    """Rings of `ring` verts around a polyline; returns verts (Z-up) and triangles, open ended."""
    path = np.array(path, float); V, T = [], []
    for i, p in enumerate(path):
        d = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]; d /= np.linalg.norm(d)
        a = np.cross(d, [1, 0, 0] if abs(d[0]) < .9 else [0, 1, 0]); a /= np.linalg.norm(a); b = np.cross(d, a)
        r = radius(i) if callable(radius) else radius
        for k in range(ring):
            t = 2 * np.pi * k / ring; V.append(p + r * (np.cos(t) * a + np.sin(t) * b))
    for i in range(len(path) - 1):
        for k in range(ring):
            a0 = i * ring + k; a1 = i * ring + (k + 1) % ring; b0 = a0 + ring; b1 = a1 + ring
            T += [[a0, a1, b1], [a0, b1, b0]]
    return np.array(V), np.array(T)

def build(smooth=True, blend=.05, fingers=5, drop_weights=0, cross_side=False, five_influences=False, finger_bleed=False, shin_under_thigh=True):
    """Returns dict V, T, J(N,4), W(N,4), names, parents, jpos(bind), plus a morph target dict for slider tests."""
    skel = skeleton(fingers)
    names = list(skel); idx = {n: i for i, n in enumerate(names)}
    parents = [idx[skel[n][0]] if skel[n][0] else -1 for n in names]; jpos = np.array([skel[n][1] for n in names], float)
    parts = []   # (verts, tris, chain of (bone, z/s boundary))
    def limb(path, r, chain, ring=8):
        V, T = tube(path, r, ring); parts.append((V, T, chain, np.array(path)))
    # chain: list of bones along the path; joint k sits at the path vertex index chain[k][1] where the next bone starts
    for s, x in (("L", 1), ("R", -1)):
        limb([(x * .20, 0, .78 - .0125 * i * 0 - i * .15 / 6) for i in range(7)] + [(x * .21, 0, .63 - i * .15 / 6) for i in range(1, 7)] + [(x * .22, 0, .48 - i * .04 / 2) for i in range(1, 3)],
             .035, [(f"DEF-upper_arm.{s}", 6), (f"DEF-forearm.{s}", 12), (f"DEF-hand.{s}", 14)])
        limb([(x * .09, 0, .53 - i * .23 / 8) for i in range(9)] + [(x * .09, 0, .30 - i * .23 / 8) for i in range(1, 9)], .05, [(f"DEF-thigh.{s}", 8), (f"DEF-shin.{s}", 16)])
        limb([(x * .09, -.01 * i, .07 - i * .0125 * 2) for i in range(3)], .035, [(f"DEF-foot.{s}", 2)])
        for k, f in enumerate(("thumb", "index", "middle", "ring", "little")[:fingers]):
            fx = x * (.22 + .012 * (k - 2)); path = [(fx, 0, .48 - .02 - i * .02) for i in range(4)]
            limb(path, .006, [(f"DEF-{f}.{seg + 1:02d}.{s}", seg + 1) for seg in range(3)], ring=4)
    limb([(0, 0, .53 + i * .29 / 8) for i in range(9)], .12, [("DEF-hips", 2), ("DEF-spine", 4), ("DEF-chest", 8)])
    limb([(0, 0, .82 + i * .18 / 6) for i in range(7)], .08, [("DEF-neck", 1), ("DEF-head", 6)])
    Vs, Ts, Js, Ws, off = [], [], [], [], 0
    for V, T, chain, path in parts:
        ring = len(V) // len(path); n = len(V); J = np.zeros((n, 4), int); W = np.zeros((n, 4))
        for vi in range(n):
            ri = vi // ring; b = 0
            while b < len(chain) - 1 and ri >= chain[b][1]: b += 1
            # joint rings sit at chain[b-1][1]; blend over `blend` units of path length on both sides when smooth
            bone = chain[b][0]; J[vi, 0] = idx[bone]; W[vi, 0] = 1.0
            if smooth and b > 0:
                jr = chain[b - 1][1]; seg = np.linalg.norm(path[min(jr + 1, len(path) - 1)] - path[jr]) or 1
                dist = (ri - jr) * seg; t = np.clip(.5 + dist / (2 * blend), 0, 1)
                if t < 1: J[vi, 1] = idx[chain[b - 1][0]]; W[vi, 1] = 1 - t; W[vi, 0] = t
            if smooth and b < len(chain) - 1:
                jr = chain[b][1]; seg = np.linalg.norm(path[min(jr + 1, len(path) - 1)] - path[jr]) or 1
                dist = (ri - jr) * seg; t = np.clip(.5 - dist / (2 * blend), 0, 1)       # t = share of the current bone
                if t < 1: J[vi, 1] = idx[chain[b + 1][0]]; W[vi, 1] = 1 - t; W[vi, 0] = t
        Vs.append(V); Ts.append(T + off); Js.append(J); Ws.append(W); off += n
    V = np.concatenate(Vs); T = np.concatenate(Ts); J = np.concatenate(Js); W = np.concatenate(Ws)
    if drop_weights: W[:drop_weights] = 0
    J1 = W1 = None
    if five_influences:                                    # first 3 vertices: 4 influences of 0.2 plus a fifth in JOINTS_1 (sums to 1)
        J1 = np.zeros((len(V), 4), int); W1 = np.zeros((len(V), 4))
        for v in range(3):
            J[v] = [idx[b] for b in ("DEF-hips", "DEF-spine", "DEF-chest", "DEF-neck")]; W[v] = .2; J1[v, 0] = idx["DEF-head"]; W1[v, 0] = .2
    if cross_side:                                         # a few right-thigh vertices hang on the left thigh bone
        sel = np.where((V[:, 0] < -.07) & (V[:, 2] < .45) & (V[:, 2] > .35))[0][:6]; J[sel, 0] = idx["DEF-thigh.L"]; W[sel] = 0; W[sel, 0] = 1
    if finger_bleed:                                       # chest vertices weighted to the left index finger
        sel = np.where((np.abs(V[:, 0]) < .1) & (V[:, 2] > .6) & (V[:, 2] < .7))[0][:5]; J[sel, 0] = idx["DEF-index.01.L"]; W[sel] = 0; W[sel, 0] = 1
    morph = {}
    for nm, f in (("ID-BodyBulk", lambda P: P * [1.1, 1.1, 1]), ("ID-Inverted", lambda P: P * [1, 1, -1] + [0, 0, 1]), ("ID-Spike", None)):
        if f is None:
            D = np.zeros_like(V); D[100] = [0, 0, .5]            # one vertex pulled out far: a spike
        else: D = f(V) - V
        morph[nm] = D
    return dict(J1=J1, W1=W1, V=V, T=T, J=J, W=W, names=names, parents=parents, jpos=jpos, targets=morph)

def write_glb(m, path, with_targets=False):
    """Writes the model as Y-up glTF with skin, IBM, hierarchy, JOINTS_0/WEIGHTS_0 and optional morph targets."""
    names, parents, jpos = m["names"], m["parents"], m["jpos"]
    yup = lambda P: np.stack([P[:, 0], P[:, 2], -P[:, 1]], 1).astype(np.float32)
    blobs, views, acc = [], [], []
    def add(arr, comp, typ, target=None, minmax=False):
        raw = np.ascontiguousarray(arr).tobytes(); pad = (-sum(len(b) for b in blobs)) % 4
        if pad: blobs.append(b"\0" * pad)
        off = sum(len(b) for b in blobs); blobs.append(raw)
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(raw), **({"target": target} if target else {})})
        a = {"bufferView": len(views) - 1, "componentType": comp, "count": len(arr), "type": typ}
        if minmax: a["min"] = arr.min(0).tolist(); a["max"] = arr.max(0).tolist()
        acc.append(a); return len(acc) - 1
    P = yup(m["V"]); attrs = {"POSITION": add(P, 5126, "VEC3", 34962, True), "JOINTS_0": add(m["J"].astype(np.uint16), 5123, "VEC4", 34962),
                              "WEIGHTS_0": add(m["W"].astype(np.float32), 5126, "VEC4", 34962)}
    if m.get("J1") is not None:
        attrs["JOINTS_1"] = add(m["J1"].astype(np.uint16), 5123, "VEC4", 34962); attrs["WEIGHTS_1"] = add(m["W1"].astype(np.float32), 5126, "VEC4", 34962)
    prim = {"attributes": attrs, "indices": add(m["T"].astype(np.uint32).reshape(-1), 5125, "SCALAR", 34963)}
    extras = {}
    if with_targets and m["targets"]:
        prim["targets"] = [{"POSITION": add(yup(D), 5126, "VEC3")} for D in m["targets"].values()]; extras = {"targetNames": list(m["targets"])}
    ibm = np.zeros((len(names), 4, 4), np.float32)
    for i, p in enumerate(jpos):
        M = np.eye(4); M[:3, 3] = yup(p[None])[0]; ibm[i] = np.linalg.inv(M).T            # column-major
    nodes = [{"name": "CHR_Body", "mesh": 0, "skin": 0}]
    kids = {}
    for i, p in enumerate(parents): kids.setdefault(p + 1 if p >= 0 else -1, []).append(i + 1)
    for i, n in enumerate(names):
        pos = yup(jpos[i][None])[0] - (yup(jpos[parents[i]][None])[0] if parents[i] >= 0 else 0)
        node = {"name": n, "translation": pos.tolist()}
        if i + 1 in kids: node["children"] = kids[i + 1]
        nodes.append(node)
    nodes[0]["children"] = []                                                              # mesh node is a sibling
    skin = {"joints": list(range(1, len(names) + 1)), "inverseBindMatrices": add(ibm.reshape(-1, 16), 5126, "MAT4")}
    buf = b"".join(blobs); roots = [1 + i for i, p in enumerate(parents) if p < 0]
    g = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0] + roots}], "nodes": nodes, "skins": [skin],
         "meshes": [{"primitives": [prim], **({"extras": extras} if extras else {})}], "buffers": [{"byteLength": len(buf), "uri": "data:application/octet-stream;base64," + base64.b64encode(buf).decode()}],
         "bufferViews": views, "accessors": acc}
    with open(path, "w") as f: json.dump(g, f)
