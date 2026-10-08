"""r1: animatable MHS3 eyes and brows (exec'd inside apply_look.py's namespace: bpy, bmesh, np, Vector, S, O, _mesh,
EYES_PATH are available).

Per eye: the head's eye opening (already shaped to eye_shape.opening_contour by build_head.py) with an eye-white
plate and a movable iris mesh behind it, a lid-line strip (with the short wing down the outer corner) and a faint
lower-rim strip on the skin, and a brow strip plus its inner-end shadow. Everything carries matching shape keys
(glTF morph targets) the character creator drives:
  head + lid strips:  PF-Blink_L / PF-Blink_R, PF-EyeWide, PF-EyeSad, PF-EyeAngry, PF-EyeHappy
  iris:               PF-LookLeft / PF-LookRight / PF-LookUp / PF-LookDown (character's left/right), PF-IrisSmall
  brows:              PF-BrowUp, PF-BrowDown, PF-BrowAngry, PF-BrowSad
Expressions are weight sets of these keys (EXPRESSIONS below, also written to docs/qa/newhead/expressions.json).
"""
import json
import os

NH_DIR = os.path.join(os.path.dirname(EYES_PATH), "..", "..", "..", "blender", "newhead")
ES = {}
exec(open(os.path.join(NH_DIR, "eye_shape.py")).read(), ES)
ET = {}
exec(open(os.path.join(NH_DIR, "eye_tex.py")).read(), ET)
for _k, _v in EYE_PAINT.items():          # knob overrides from look_knobs.json "paint"
    if _k in ES:
        ES[_k] = _v

EXPRESSIONS = {
    "neutral": {},
    "blink": {"PF-Blink_L": 1, "PF-Blink_R": 1},
    "wink_left": {"PF-Blink_L": 1, "PF-BrowDown": 0.3},
    "amazed": {"PF-EyeWide": 1, "PF-BrowUp": 1, "PF-IrisSmall": 1},
    "sad": {"PF-EyeSad": 1, "PF-BrowSad": 1, "PF-LookDown": 0.4},
    "angry": {"PF-EyeAngry": 1, "PF-BrowAngry": 1},
    "happy": {"PF-EyeHappy": 1, "PF-BrowUp": 0.35},
}
EYE_LIT_COLOR = (232, 197, 170)   # lit skin, sampled from the neutral render
EYE_DEPTH = 0.0020        # eye white behind the face surface (m); the iris sits 0.6 mm in front of it
LID_KEYS = {"Blink": "PF-Blink", "Wide": "PF-EyeWide", "Sad": "PF-EyeSad", "Angry": "PF-EyeAngry", "Happy": "PF-EyeHappy"}


def _lin(c):
    c = np.asarray(c, float) / 255.0
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)) + (1.0,)


def _to_m(side, X, Z):
    """eye-local (W2 units) -> head mesh coordinates (metres, before the object offset)."""
    w2 = ES["EYE_W2"]
    return side * (ES["EYE_CX"] + X * w2) * S, O + (ES["EYE_Z0"] + Z * w2) * S


def _from_m(side, x, z):
    w2 = ES["EYE_W2"]
    return (side * x / S - ES["EYE_CX"]) / w2, ((z - O) / S - ES["EYE_Z0"]) / w2


def _inpoly(px, pz, P):
    """Even-odd point-in-polygon for arrays of points against polygon P (k, 2)."""
    ins = np.zeros(len(px), bool)
    x0, z0 = P[:, 0], P[:, 1]; x1, z1 = np.roll(x0, -1), np.roll(z0, -1)
    for a, b, c, d in zip(x0, z0, x1, z1):
        cond = ((b > pz) != (d > pz)) & (px < (c - a) * (pz - b) / (d - b + 1e-12) + a)
        ins ^= cond
    return ins


class _Surf:
    """Face depth near one eye: a cubic fit of the front skin (fills the opening) and the real skin by ray cast."""

    def __init__(self, ob, side, tree):
        V = np.array([v.co[:] for v in ob.data.vertices])
        X, Z = _from_m(side, V[:, 0], V[:, 2])
        C = ES["opening_contour"]()
        sel = (X > -2.4) & (X < 2.0) & (Z > -1.6) & (Z < 1.8) & (V[:, 1] < -0.02) & ~_inpoly(X, Z, C * 1.08)
        self.side, self.tree, self.C = side, tree, C
        A = self._basis(X[sel], Z[sel])
        self.coef = np.linalg.lstsq(A, V[sel, 1], rcond=None)[0]

    @staticmethod
    def _basis(X, Z):
        return np.stack([np.ones_like(X), X, Z, X * X, X * Z, Z * Z, X ** 3, X * X * Z, X * Z * Z, Z ** 3], -1)

    def fit(self, X, Z):
        return self._basis(np.asarray(X, float), np.asarray(Z, float)) @ self.coef

    def skin(self, X, Z, tree=None, C=None):
        """Front-most of the fit and the real skin (the skin where it exists, the fit across the opening); tree / C
        give a deformed head (one shape key) and its opening outline."""
        X = np.asarray(X, float); Z = np.asarray(Z, float)
        tree = self.tree if tree is None else tree
        f = self.fit(X, Z)
        out = f.copy()
        x, z = _to_m(self.side, X, Z)
        ins = _inpoly(X, Z, self.C if C is None else C)
        for i in range(len(out)):
            hit = tree.ray_cast(Vector((x[i], -1.0, z[i])), Vector((0, 1, 0)))
            if hit[0] is None:
                continue
            if not ins[i]:
                out[i] = hit[0].y                       # real skin outside the opening
            elif hit[0].y < f[i]:
                out[i] = hit[0].y
        return out


def _rig_strip(name, pairs_by_key, surf, side, mat, col, off_x, lift, uv=None, rows=4, key_skin=None, over_fit=False):
    """Strip from (inner, outer) eye-local point pairs, `rows` quad rows across (so it follows the skin's curve);
    one entry per shape key (None = basis). key_skin[key] = (tree, contour) of the head deformed by that key."""
    def verts(inner, outer, key=None):
        n = len(inner)
        P = np.concatenate([inner + (outer - inner) * (r / rows) for r in range(rows + 1)])
        tc = (key_skin or {}).get(key, (None, None))
        y = surf.skin(P[:, 0], P[:, 1], *tc)
        if over_fit:                                     # also in front of the fitted face (lid keys pull skin up to it)
            y = np.minimum(y, surf.fit(P[:, 0], P[:, 1]))
        y = y - lift
        x, z = _to_m(side, P[:, 0], P[:, 1])
        return [Vector((x[k], y[k], z[k])) for k in range(len(P))], n
    base, n = verts(*pairs_by_key[None])
    faces = []
    for r in range(rows):
        for i in range(n - 1):
            a, b = r * n + i, (r + 1) * n + i
            q = (a, a + 1, b + 1, b)
            faces.append(q if side > 0 else q[::-1])
    uvs = [(i / (n - 1), r / rows) for r in range(rows + 1) for i in range(n)]
    o = _mesh(name, base, faces, uvs, mat, col, off_x)
    o.visible_shadow = False
    o.shape_key_add(name="Basis")
    for key, pr in pairs_by_key.items():
        if key is None:
            continue
        vs, _ = verts(*pr, key=key)
        sk = o.shape_key_add(name=key); sk.value = 0.0
        for i, v in enumerate(vs):
            sk.data[i].co = v
    return o


def _image(name, px):
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, px.shape[1], px.shape[0], alpha=True)
    img.colorspace_settings.name = "sRGB"
    img.pixels.foreach_set(px.ravel())
    img.pack()
    return img


def _tex_mat(name, img, alpha=True):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = img; tx.extension = "CLIP"
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(tx.outputs["Color"], em.inputs["Color"])
    if alpha:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(tx.outputs["Alpha"], mx.inputs["Fac"])
        nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            m.blend_method = "BLEND"
    else:
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def _head_keys(ob, LID, surfs):
    """Lid shape keys on the head: each lid loop vertex follows its edge (upper / lower) of the edited contour, the
    lid rim behind it follows radially, the skin around follows with a falloff and stays on the face."""
    me = ob.data
    if me.shape_keys is None:
        ob.shape_key_add(name="Basis")
    V = np.array([v.co[:] for v in me.vertices])
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    Xg, U, L, _ = ES["base_curves"]()
    w2m = ES["EYE_W2"] * S
    per_side = {}
    out = {}
    for tagv, side in ((1, 1), (2, -1)):
        surf = surfs[side]
        li = np.nonzero(LID == tagv)[0]
        lx, lz = _from_m(side, V[li, 0], V[li, 2])
        mid = (np.interp(lx, Xg, U) + np.interp(lx, Xg, L)) / 2
        upper = lz > mid
        X, Z = _from_m(side, V[:, 0], V[:, 2])
        lyd = V[li, 1].max()
        # rim: BFS from the loop into the verts inside the opening outline (the lid turns in toward the eyeball)
        Cn = ES["opening_contour"]()
        cen = Cn.mean(0)
        inside = _inpoly(X, Z, cen + (Cn - cen) * 1.01) & (V[:, 1] > V[li, 1].min() - 0.002)
        Lset = set(li.tolist())
        rim = {int(i): int(i) for i in li}
        front_ = list(li)
        for _ in range(10):
            nxt = []
            for i in front_:
                for e in bm.verts[int(i)].link_edges:
                    q = e.other_vert(bm.verts[int(i)]).index
                    if q in rim or q in Lset or not inside[q]:
                        continue
                    rim[q] = rim[int(i)]; nxt.append(q)
            front_ = nxt
        win = (np.abs(X) < 2.6) & (Z > -1.8) & (Z < 1.9) & (V[:, 1] < lyd + 0.01) & ~inside
        skin = np.array([i for i in np.nonzero(win)[0] if i not in rim])
        per_side[side] = (li, lx, lz, upper, rim, skin, X, Z)
    bm.free()
    for name, key in LID_KEYS.items():
        variants = [(key + "_L", (1,)), (key + "_R", (-1,))] if name == "Blink" else [(key, (1, -1))]
        for kname, sides in variants:
            co = V.copy()
            for side in sides:
                surf = surfs[side]
                li, lx, lz, upper, rim, skin, X, Z = per_side[side]
                Cop0 = ES["opening_contour"]()
                cc_ = Cop0.mean(0)
                Cop = cc_ + (ES["opening_contour"](*ES["expression_offsets"]("Wide", Xg, U, L)) - cc_) * 1.25   # area the eye parts cover
                dU, dL = ES["expression_offsets"](name, Xg, U, L)
                d = np.where(upper, np.interp(lx, Xg, dU), np.interp(lx, Xg, dL))
                tz = lz + d
                ty_old = surf.fit(lx, lz); ty_new = surf.fit(lx, tz)
                dl = np.stack([np.zeros_like(d), ty_new - ty_old, d * w2m], 1)
                co[li] += dl
                # over the opening the lid skin lies on the face surface (it hides the eye white and iris)
                fy = surf.fit(lx, tz) - 0.0002
                co[li, 1] = np.minimum(co[li, 1], fy)
                idx_of = {int(i): k for k, i in enumerate(li)}
                for q, src in rim.items():
                    if q in idx_of:
                        continue
                    co[q] += dl[idx_of[src]]
                # skin falloff from the same-side edge
                for q in skin:
                    on_up = Z[q] > np.interp(X[q], Xg, (U + L) / 2)
                    grp = upper if on_up else ~upper
                    if not grp.any():
                        continue
                    dx = lx[grp] - X[q]; dz = lz[grp] - Z[q]
                    dist = np.hypot(dx, dz)
                    j = np.argsort(dist)[:3]
                    wts = 1 / np.maximum(dist[j], 1e-4)
                    dd = (d[grp][j] * wts).sum() / wts.sum()
                    R = 1.15 if on_up else 0.75
                    fall = max(0.0, 1 - dist[j[0]] / R) ** 2
                    if fall <= 0:
                        continue
                    nz = Z[q] + dd * fall
                    co[q, 2] += dd * fall * w2m
                    co[q, 1] += surf.fit(X[q], nz) - surf.fit(X[q], Z[q])
                    if _inpoly(np.array([X[q]]), np.array([nz]), Cop)[0]:
                        co[q, 1] = min(co[q, 1], float(surf.fit(X[q], nz)) - 0.0002)
            sk = ob.shape_key_add(name=kname); sk.value = 0.0
            sk.data.foreach_set("co", co.ravel())
            out[kname] = co
    return out


def _eye_lit(ob, tag, key_co=None):
    """The skin around the eyes is always lit in the MHS3 look; when the lid keys stretch faces, their stored custom
    normals rotate and toon shadow specks appear. An 'eye_lit' attribute (1 near the eyes, fading out) mixes the toon
    skin with the plain lit skin colour (sampled from the neutral render)."""
    me = ob.data
    V = np.array([v.co[:] for v in me.vertices])
    # only skin the lid keys actually move (static skin keeps its toon shading, e.g. the temple shadow in 3/4)
    disp = np.zeros(len(V))
    for co in (key_co or {}).values():
        disp = np.maximum(disp, np.linalg.norm(co - V, axis=1))
    w = np.clip(disp / 0.0004, 0, 1)
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    for _ in range(2):                                   # grow by two rings so the edge of the moving area is covered
        w2 = w.copy()
        for v in bm.verts:
            if w[v.index] < 1:
                nb = [w[e.other_vert(v).index] for e in v.link_edges]
                w2[v.index] = max(w[v.index], 0.6 * max(nb) if nb else 0)
        w = w2
    bm.free()
    a = me.attributes.get("eye_lit") or me.attributes.new("eye_lit", "FLOAT", "POINT")
    a.data.foreach_set("value", w.astype(np.float32))
    m = me.materials[0]
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    src = out.inputs["Surface"].links[0].from_socket
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "eye_lit"
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = _lin(EYE_LIT_COLOR)
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(at.outputs["Fac"], mx.inputs["Fac"])
    nt.links.new(src, mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])


def build_rig(ob, col, LID, off_x, tag):
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new(); bm.from_mesh(ob.data); tree = BVHTree.FromBMesh(bm); bm.free()
    surfs = {s: _Surf(ob, s, tree) for s in (1, -1)}
    made = []
    # lid keys on the head first: the strips' key shapes sit on the head deformed by the same key
    key_co = _head_keys(ob, LID, surfs)
    polys = [tuple(p.vertices) for p in ob.data.polygons]
    key_tree = {k: BVHTree.FromPolygons([tuple(v) for v in co], polys) for k, co in key_co.items()}
    Xg0, U0, L0, _ = ES["base_curves"]()

    def key_skin_for(side):
        d = {}
        for name, key in LID_KEYS.items():
            kname = key + ("_L" if side > 0 else "_R") if name == "Blink" else key
            dU, dL = ES["expression_offsets"](name, Xg0, U0, L0)
            d[kname] = (key_tree[kname], ES["opening_contour"](dU, dL))
        return d
    Xg, U, L, _ = ES["base_curves"]()
    line_m = _emission("MAT_RigLidLine_" + tag, _lin((84, 64, 48)))
    rim_m = _emission("MAT_RigLowRim_" + tag, _lin((196, 186, 168)))
    shade_m = _emission("MAT_RigBrowShade_" + tag, _lin((176, 128, 112)))
    # textures
    X0, X1, Z0, Z1 = -1.15, 1.20, -0.95, 0.70
    scl = _image("IMG_RigSclera_" + tag, ET["sclera"](X0, X1, Z0, Z1, Xg, U))
    scl_m = _tex_mat("MAT_RigSclera_" + tag, scl, alpha=False)
    lo, hi = ES["brow_ribbon"]()
    brow_img = _image("IMG_RigBrow_" + tag, ET["brow"](lo[:, 0], lo[:, 1], hi[:, 1]))
    brow_m = _tex_mat("MAT_RigBrow_" + tag, brow_img, alpha=False)
    for side in (1, -1):
        sfx = "%s_%s" % (tag, "LR"[side < 0])
        surf = surfs[side]
        # eye white: a grid over the eye box, just behind the skin (the opening shows it)
        nx_, nz_ = 40, 28
        gx = np.linspace(X0, X1, nx_ + 1); gz = np.linspace(Z0, Z1, nz_ + 1)
        GX, GZ = np.meshgrid(gx, gz); GX = GX.ravel(); GZ = GZ.ravel()
        Cn = ES["opening_contour"]()
        cen = Cn.mean(0)
        Cbig = cen + (ES["opening_contour"](*ES["expression_offsets"]("Wide", Xg, U, L)) - cen) * 1.12

        def plate_y(X, Z):
            # inside the opening: behind the fitted face; outside: behind the real skin
            X = np.asarray(X, float); Z = np.asarray(Z, float)
            f = surf.fit(X, Z) + EYE_DEPTH
            x, z = _to_m(side, X, Z)
            ins = _inpoly(X, Z, Cn)
            out = f.copy()
            for i in range(len(X)):
                if ins[i]:
                    continue
                hit = surf.tree.ray_cast(Vector((x[i], -1.0, z[i])), Vector((0, 1, 0)))
                if hit[0] is not None:
                    out[i] = max(f[i], hit[0].y + EYE_DEPTH)
            return out
        py = plate_y(GX, GZ)
        x, z = _to_m(side, GX, GZ)
        verts = [Vector((x[k], py[k], z[k])) for k in range(len(GX))]
        keep = _inpoly(GX, GZ, Cbig)
        faces = []
        for j in range(nz_):
            for i in range(nx_):
                a = j * (nx_ + 1) + i; q = (a, a + 1, a + nx_ + 2, a + nx_ + 1)
                if not any(keep[list(q)]):
                    continue
                faces.append(q if side > 0 else q[::-1])
        uvs = [((GX[k] - X0) / (X1 - X0), (GZ[k] - Z0) / (Z1 - Z0)) for k in range(len(GX))]
        plate = _mesh("RigEyeWhite_" + sfx, verts, faces, uvs, scl_m, col, off_x)
        plate.visible_shadow = False
        made.append(plate)

        # iris: a disc in front of the white (still behind the skin), texture incl. the highlight
        ix, iz, rx, ry = ES["IRIS_X"], ES["IRIS_Z"], ES["IRIS_RX"], ES["IRIS_RY"]
        ext = ET["EXT"]
        nr, na = 8, 40

        def iris_pts(dx=0.0, dz=0.0, sc=1.0):
            pts = [(ix + dx, iz + dz)]
            for r in range(1, nr + 1):
                for a in range(na):
                    t = 2 * np.pi * a / na
                    pts.append((ix + dx + np.cos(t) * rx * ext * sc * r / nr, iz + dz + np.sin(t) * ry * ext * sc * r / nr))
            P = np.array(pts)
            y = plate_y(P[:, 0], P[:, 1]) - 0.0006
            xx, zz = _to_m(side, P[:, 0], P[:, 1])
            return [Vector((xx[k], y[k], zz[k])) for k in range(len(P))], P
        ivs, IP = iris_pts()
        ifaces = []
        for a in range(na):
            b = (a + 1) % na
            tri = (0, 1 + a, 1 + b)
            ifaces.append(tri if side > 0 else tri[::-1])
        for r in range(1, nr):
            for a in range(na):
                b = (a + 1) % na
                q = (1 + (r - 1) * na + a, 1 + r * na + a, 1 + r * na + b, 1 + (r - 1) * na + b)
                ifaces.append(q if side > 0 else q[::-1])
        iuv = [(0.5 + (p[0] - ix) / (2 * rx * ext), 0.5 + (p[1] - iz) / (2 * ry * ext)) for p in IP]
        hl_sign = 1.0 if (side > 0 or not HL_SAME_SIDE) else -1.0
        iimg = _image("IMG_RigIris_" + sfx, ET["iris"](512, hl_sign))
        iris = _mesh("RigIris_" + sfx, ivs, ifaces, iuv, _tex_mat("MAT_RigIris_" + sfx, iimg), col, off_x)
        iris.visible_shadow = False
        iris.shape_key_add(name="Basis")
        looks = {"PF-LookLeft": (side * 0.32, 0.0), "PF-LookRight": (-side * 0.32, 0.0),
                 "PF-LookUp": (0.0, 0.16), "PF-LookDown": (0.0, -0.14)}
        for kname, (dx, dz) in looks.items():
            vs, _ = iris_pts(dx, dz)
            sk = iris.shape_key_add(name=kname); sk.value = 0.0
            for i, v in enumerate(vs):
                sk.data[i].co = v
        vs, _ = iris_pts(sc=0.82)
        sk = iris.shape_key_add(name="PF-IrisSmall"); sk.value = 0.0
        for i, v in enumerate(vs):
            sk.data[i].co = v
        made.append(iris)
        # lid line and lower rim strips with the lid keys
        lid_pairs, rim_pairs = {None: ES["lid_ribbon"]()[:2]}, {None: ES["low_rim_ribbon"]()}
        for name, key in LID_KEYS.items():
            kname = key + ("_L" if side > 0 else "_R") if name == "Blink" else key
            dU, dL = ES["expression_offsets"](name, Xg, U, L)
            lid_pairs[kname] = ES["lid_ribbon"](dU, dL, wing=0.0 if name == "Blink" else 1.0)[:2]
            rim_pairs[kname] = ES["low_rim_ribbon"](dU, dL)
        made.append(_rig_strip("RigLidLine_" + sfx, lid_pairs, surf, side, line_m, col, off_x, 0.0010, key_skin=key_skin_for(side)))
        if ES["LOW_RIM"] > 0:
            made.append(_rig_strip("RigLowRim_" + sfx, rim_pairs, surf, side, rim_m, col, off_x, 0.0008, key_skin=key_skin_for(side)))
        # brow + inner-end shadow
        brow_pairs, shade_pairs = {None: ES["brow_ribbon"]()}, {}
        for kname, fn in ES["BROW_KEYS"].items():
            brow_pairs["PF-" + kname] = ES["brow_ribbon"](d=fn)

        def shade_of(pair):
            bot, _ = pair
            n = len(bot); t = np.linspace(0, 1, n)
            k = int(n * 0.45)
            sb = bot[:k].copy(); depth = 0.17 * np.sin(np.pi * np.clip(t[:k] / 0.45, 0, 1)) ** 0.7
            lower = sb - np.stack([np.zeros(k) - 0.02, depth], 1)
            return sb + np.array([0.0, 0.02]), lower
        shade_pairs = {k: shade_of(v) for k, v in brow_pairs.items()}
        made.append(_rig_strip("RigBrow_" + sfx, brow_pairs, surf, side, brow_m, col, off_x, 0.0012, over_fit=True))
        made.append(_rig_strip("RigBrowShade_" + sfx, shade_pairs, surf, side, shade_m, col, off_x, 0.0010, over_fit=True))
    _eye_lit(ob, tag, key_co)
    try:
        json.dump(EXPRESSIONS, open(os.path.join(os.path.dirname(EYES_PATH), "expressions.json"), "w"), indent=1)
    except Exception:
        pass
    return made


def set_expression(col, name, weights=None):
    """Set every PF- key in the collection to the expression's weights (others to 0)."""
    w = EXPRESSIONS.get(name, {}) if weights is None else weights
    for o in col.objects:
        ks = o.data.shape_keys if o.type == "MESH" else None
        if not ks:
            continue
        for kb in ks.key_blocks[1:]:
            kb.value = float(w.get(kb.name, 0.0))
