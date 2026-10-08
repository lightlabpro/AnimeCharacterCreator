"""v1: camera-angle view keys - the anime cheat for off-front views (exec'd in apply_look.py's globals after
build_rig / face_strokes, so bpy, bmesh, np, Vector, S, O, ES, _Surf, _from_m, EYE_VIEW are available).

Why: the eyes and brows lie on the curved face, so a 3/4 view wraps them like real anatomy - the far eye shrinks to
a third of its width and its outer half slides behind the cheek silhouette, the near eye stretches, and in profile
the near eye stays wide. Anime (and MHS3, docs/reference/mhs3/09-old-man.png) draws the far eye at about 3/4 of the
near eye's width, fully visible between the nose line and the cheek edge, the irises stay round, and in profile the
eye becomes a narrow wedge. Games get this with corrective shape keys driven by the camera angle (e.g. the CamKeys
add-on: front / three-quarter / side shapes).

Keys (glTF morph targets, prefix VW-): VW-Yaw_L / VW-Yaw_R (camera VIEW["Y34"] degrees toward the character's left /
right), VW-Side_L / VW-Side_R (90 degrees). The app drives them from the camera's yaw around the head with
view_weights(yaw) below. Each key slides the eye parts, brows and the skin around them ALONG the face surface (front
x re-solved so the camera sees the target position, depth re-read from the surface, each part's layer offset kept),
so nothing leaves the face and the opening, eye white, iris and lid line stay stacked.
"""
import math

VIEW = dict(
    Y34=35.0,          # angle of the VW-Yaw keys (degrees)
    NEAR_C=0.95,       # near eye: screen width / front width at Y34 (now about 1.27: the outer half faces the camera)
    FAR_GAP_IN=0.10,   # far eye: inner corner gap to the nose-bridge line (eye half-widths)
    FAR_GAP_OUT=0.12,  # far eye: outer corner gap to the cheek silhouette
    BROW_GAP_IN=0.00,  # far brow: inner tip gap to the nose-bridge line
    BROW_GAP_OUT=0.04, # far brow: outer end gap to the silhouette
    IRIS_NEAR=1.0,     # iris screen width / front width (near eye, Y34) - irises stay round in anime
    IRIS_FAR=0.85,
    SIDE_C=0.50,       # profile: near eye screen width / front width (now about 0.79)
    IRIS_SIDE=0.55,
    SIDE_GAP=0.10,     # profile: the eye keeps this gap behind the front silhouette
    SOFT=0.10,         # soft clamp width at the bridge / silhouette (eye half-widths)
    R_IN=0.14, R_OUT=0.6, R_V=0.45, R_UP=0.8,   # skin falloff around the eye+brow box (eye half-widths)
    LIT_MM=0.0010, LIT_Y=-0.060, PUSH=0.0015, VIEW_LIT=1, MIN_SLOPE=0.35, BOX_FADE=0.3, FIT_DEPTH=0, PUSH_BACK=0.0035,     # v2: skin moved this far (m) by a view key is drawn fully lit (eye_lit)
    Y_FACE=-0.075, Y_SIDE=-0.035,    # v2: skin moves fully in front of Y_FACE (m), not at all behind Y_SIDE (temple, ear)
)
for _k, _v in EYE_VIEW.items():
    if _k in VIEW:
        VIEW[_k] = _v
VIEW_KEYS_NAMES = ("VW-Yaw_L", "VW-Yaw_R", "VW-Side_L", "VW-Side_R")


def _sm1(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def view_weights(yaw):
    """VW- key weights for a camera yaw (degrees around the head's up axis, + = toward the character's left)."""
    a = abs(float(yaw)); sd = "L" if yaw >= 0 else "R"
    y34 = VIEW["Y34"]
    w34 = _sm1(0, y34, a) if a <= y34 else 1 - _sm1(y34, 90, a)
    ws = 0.0 if a <= y34 else (_sm1(y34, 90, a) if a <= 90 else 1 - _sm1(90, 150, a))
    if a > 90:
        w34 = 0.0
    w = {k: 0.0 for k in VIEW_KEYS_NAMES}
    w["VW-Yaw_" + sd] = w34; w["VW-Side_" + sd] = ws
    return w


def set_view(col, yaw):
    w = view_weights(yaw)
    for o in col.objects:
        ks = o.data.shape_keys if o.type == "MESH" else None
        if ks:
            for kb in ks.key_blocks:
                if kb.name in w:
                    kb.value = w[kb.name]


class _Grid:
    """Front-most face depth y(x, z) on a grid (front rays on the basis head; the eye openings filled by the face fit)."""

    def __init__(self, ob, surfs, tree):
        w2m = ES["EYE_W2"] * S
        ze = O + ES["EYE_Z0"] * S
        self.xs = np.linspace(-0.15, 0.15, 601)
        self.zs = np.arange(ze - 1.7 * w2m, ze + 1.9 * w2m, 0.0005)
        Y = np.full((len(self.zs), len(self.xs)), np.nan)
        for j, z in enumerate(self.zs):
            for i, x in enumerate(self.xs):
                h = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
                if h[0] is not None:
                    Y[j, i] = h[0].y
        GX, GZ = np.meshgrid(self.xs, self.zs)
        C = ES["opening_contour"]()
        cen = C.mean(0)
        for side in (1, -1):
            X, Z = _from_m(side, GX.ravel(), GZ.ravel())
            ins = _inpoly(X, Z, cen + (C - cen) * 1.03) & (side * GX.ravel() > 0)
            f = surfs[side].fit(X[ins], Z[ins])
            flat = Y.ravel()
            flat[ins] = np.where(np.isnan(flat[ins]), f, np.minimum(flat[ins], f))
            Y = flat.reshape(Y.shape)
        self.valid = ~np.isnan(Y)                          # misses stay out of the visibility branches (v2 fix)
        for j in range(len(self.zs)):                      # misses (off the head): nearest valid value in the row
            r = Y[j]; ok = ~np.isnan(r)
            if ok.any():
                Y[j] = np.interp(self.xs, self.xs[ok], r[ok])
        self.Y = Y

    def mirrored(self):
        g = _Grid.__new__(_Grid)
        g.xs, g.zs, g.Y = self.xs, self.zs, self.Y[:, ::-1].copy()
        g.valid = self.valid[:, ::-1].copy()
        return g

    def _rc(self, z):
        r = np.clip((np.asarray(z, float) - self.zs[0]) / (self.zs[1] - self.zs[0]), 0, len(self.zs) - 1.001)
        j = np.floor(r).astype(int); return j, r - j

    def y(self, x, z):
        j, t = self._rc(z)
        a = np.array([np.interp(x[k], self.xs, self.Y[j[k]]) for k in range(len(x))])
        b = np.array([np.interp(x[k], self.xs, self.Y[j[k] + 1]) for k in range(len(x))])
        return a * (1 - t) + b * t

    def rows_u(self, th):
        return self.xs[None, :] * math.cos(th) + self.Y * math.sin(th)

    def u(self, x, z, th):
        return np.asarray(x) * math.cos(th) + self.y(np.asarray(x, float), z) * math.sin(th)

    def branches(self, th):
        """Per row: the visible front branch (far silhouette -> near silhouette), made monotone."""
        U = np.where(self.valid, self.rows_u(th), np.nan)
        out = []
        for j in range(len(self.zs)):
            ok = np.nonzero(self.valid[j])[0]
            if len(ok) < 2:
                ok = np.arange(len(self.xs)); U[j] = self.rows_u(th)[j]
            i0, i1 = int(np.nanargmin(U[j])), int(np.nanargmax(U[j]))
            if i1 <= i0:
                i1 = int(ok[-1])
            idx = ok[(ok >= i0) & (ok <= i1)]
            ub = np.maximum.accumulate(U[j, idx])
            out.append((ub + np.arange(len(ub)) * 1e-9, self.xs[idx], U[j, i0], U[j, i1]))
        return out

    def inv(self, ut, z, br):
        """Front x whose surface point the camera sees at screen u = ut (row z)."""
        j, t = self._rc(z)
        a = np.array([np.interp(ut[k], br[j[k]][0], br[j[k]][1]) for k in range(len(ut))])
        b = np.array([np.interp(ut[k], br[j[k] + 1][0], br[j[k] + 1][1]) for k in range(len(ut))])
        return a * (1 - t) + b * t

    def sil(self, z, br):
        j, t = self._rc(np.array([z]))
        return br[j[0]][2] * (1 - t[0]) + br[j[0] + 1][2] * t[0]


def _soft_lo(u, lo, k):
    """Smooth monotone lower clamp: about u above lo + k, flattening onto lo below."""
    return lo + k * np.logaddexp(0.0, (u - lo) / k)


def _soft_hi(u, hi, k):
    return -_soft_lo(-u, -hi, k)


def _objects(col, head):
    """(object, role, side): role eye / iris / brow / skin."""
    out = []
    for o in col.objects:
        if o.type != "MESH":
            continue
        n = o.name
        side = 1 if n.endswith("_L") else (-1 if n.endswith("_R") else 0)
        if n.startswith("RigIris_"):
            out.append((o, "iris", side))
        elif n.startswith(("RigEyeWhite_", "RigLidLine_", "RigLowRim_")):
            out.append((o, "eye", side))
        elif n.startswith(("RigBrow_", "RigBrowShade_")):
            out.append((o, "brow", side))
        else:
            out.append((o, "skin", 0))
    return out


def _basis(o):
    ks = o.data.shape_keys
    src = ks.key_blocks[0].data if ks else o.data.vertices
    return np.array([v.co[:] for v in src])


def _maps(g, br, th, near_only):
    """Screen-u target maps per side (character side in the computed frame; +1 faces the camera): {side: {role: f}}."""
    w2m = ES["EYE_W2"] * S
    cx = ES["EYE_CX"] * S
    ze = O + ES["EYE_Z0"] * S
    zi = ze + ES["IRIS_Z"] * w2m
    zb = ze + 0.75 * w2m
    k = VIEW["SOFT"] * w2m
    ixr = ES["IRIS_X"]
    side_view = th > math.radians(60)
    def make(s):
        x_in = s * (cx - 0.94 * w2m); x_out = s * (cx + 1.0 * w2m); x_ic = s * (cx + ixr * w2m)
        x_bi = s * (cx + ES["BX"][0] * w2m); x_bo = s * (cx + ES["BX"][-1] * w2m)
        bridge = lambda z: g.u(np.zeros(np.size(z)), np.atleast_1d(z), th)
        if s == 1 and not side_view:                       # near eye, 3/4: even compression about the iris
            u_ic = float(g.u(np.array([x_ic]), np.array([zi]), th)[0])
            c = VIEW["NEAR_C"]

            def fe(x, z, u_ic=u_ic, c=c):
                return _soft_lo(u_ic + c * (x - x_ic), bridge(z) + 0.5 * VIEW["FAR_GAP_IN"] * w2m, k)
            fb = fe
            ci = VIEW["IRIS_NEAR"]
            fi = (lambda x, z, fe=fe, ci=ci, x_ic=x_ic: fe(np.full(np.size(x), x_ic), z) + ci * (x - x_ic))
        elif s == 1:                                       # near eye, profile: narrow wedge behind the front line
            u_in = float(g.u(np.array([x_in]), np.array([ze]), th)[0])
            c = VIEW["SIDE_C"]

            def fe(x, z, u_in=u_in, c=c):
                lo = np.array([g.sil(zz, br) for zz in np.atleast_1d(z)]) + VIEW["SIDE_GAP"] * w2m
                return _soft_lo(u_in + c * (x - x_in), lo, k)
            fb = fe
            ci = VIEW["IRIS_SIDE"]
            fi = (lambda x, z, fe=fe, ci=ci, x_ic=x_ic: fe(np.full(np.size(x), x_ic), z) + ci * (x - x_ic))
        elif not near_only:                                # far eye, 3/4: between the nose line and the cheek edge
            u_oc = g.sil(ze, br) + VIEW["FAR_GAP_OUT"] * w2m
            u_it = float(bridge(ze)[0]) - VIEW["FAR_GAP_IN"] * w2m
            c = (u_it - u_oc) / (x_in - x_out)
            ub_o = g.sil(zb, br) + VIEW["BROW_GAP_OUT"] * w2m
            ub_i = float(bridge(zb)[0]) - VIEW["BROW_GAP_IN"] * w2m
            cb = (ub_i - ub_o) / (x_bi - x_bo)

            def clamp(u, z):
                z = np.atleast_1d(z)
                lo = np.array([g.sil(zz, br) for zz in z]) + 0.5 * VIEW["FAR_GAP_OUT"] * w2m
                return _soft_lo(_soft_hi(u, bridge(z) - 0.5 * VIEW["FAR_GAP_IN"] * w2m, k), lo, k)

            def fe(x, z, c=c, u_oc=u_oc):
                return clamp(u_oc + c * (x - x_out), z)

            def fb(x, z, cb=cb, ub_o=ub_o):
                return clamp(ub_o + cb * (x - x_bo), z)
            ci = VIEW["IRIS_FAR"]
            fi = (lambda x, z, fe=fe, ci=ci, x_ic=x_ic: fe(np.full(np.size(x), x_ic), z) + ci * (x - x_ic))
        else:
            return None
        return {"eye": fe, "brow": fb, "iris": fi}
    M = {}
    for s in (1, -1):
        m = make(s)
        if m is not None:
            M[s] = m
    return M


def _skin_w(s, x, z):
    X, Z = _from_m(s, x, z)
    dxi = np.maximum(0, -1.75 - X); dxo = np.maximum(0, X - 1.45)
    dzu = np.maximum(0, Z - 1.2); dzd = np.maximum(0, -1.0 - Z)
    sm = lambda e, x_: np.clip(x_ / e, 0, 1) ** 2 * (3 - 2 * np.clip(x_ / e, 0, 1))
    w = (1 - sm(VIEW["R_IN"], dxi)) * (1 - sm(VIEW["R_OUT"], dxo)) * (1 - sm(VIEW["R_UP"], dzu)) * (1 - sm(VIEW["R_V"], dzd))
    return np.where(s * x > 0, w, 0.0), Z


def _key_coords(objs, g, th, mirror, near_only):
    """New coordinates per object for one view key (computed with the camera toward +x; mirror flips x)."""
    gg = g.mirrored() if mirror else g
    br = gg.branches(th)
    M = _maps(gg, br, th, near_only)
    res = {}
    for o, role, side in objs:
        B = _basis(o)
        x = -B[:, 0] if mirror else B[:, 0].copy()
        y, z = B[:, 1], B[:, 2]
        s_obj = -side if mirror else side
        off = y - gg.y(x, z)
        xt = x.copy(); w = np.zeros(len(x))
        if role in ("eye", "iris", "brow"):
            if s_obj not in M:
                continue
            ut = M[s_obj][role](x, z)
            xt = gg.inv(ut, z, br); w[:] = 1.0
        else:
            # v10: the skin map is built per row on a fine x grid and made monotone (slope >= MIN_SLOPE), so the
            # falloff between moved and fixed skin stretches instead of folding (folds showed the outline shell)
            fr = np.nonzero(off < 0.012)[0]               # face skin only (not the back of the skull at the same x, z)
            if len(fr):
                zb = np.round(z[fr] / 0.0005).astype(int)
                xs = np.linspace(-0.13, 0.13, 521)
                for zi_ in np.unique(zb):
                    zz = zi_ * 0.0005
                    ww, xtr = _skin_row(gg, br, M, xs, zz)
                    if not ww.any():
                        continue
                    xnr = xs + ww * (xtr - xs)
                    ms = VIEW["MIN_SLOPE"] * (xs[1] - xs[0])
                    for i in range(1, len(xnr)):
                        if xnr[i] < xnr[i - 1] + ms:
                            xnr[i] = xnr[i - 1] + ms
                    idx = fr[zb == zi_]
                    xt[idx] = np.interp(x[idx], xs, xnr)
                    w[idx] = (np.interp(x[idx], xs, ww) > 0) | (np.abs(xt[idx] - x[idx]) > 1e-6)
        if not w.any():
            continue
        xn = np.where(w > 0, x + (xt - x) * (1.0 if role == "skin" else w), x)
        yn = np.where(w > 0, gg.y(xn, z) + off, y)
        if w.any():
            # v11: inside the eye box the depth follows the smooth face fit (the opening filled), so the slid skin edge,
            # eye white, iris and lid strips keep their layer offsets exactly (the real skin's bumps made the lower
            # edge of the white notched)
            xr0 = -x if mirror else x; xr1 = -xn if mirror else xn
            yf0 = _fit_y(g.surfs, xr0, z); yf1 = _fit_y(g.surfs, xr1, z)
            b = _box_w(xr0, z) * (w > 0) * VIEW["FIT_DEPTH"]
            yn = np.where(b > 0, b * (yf1 + (y - yf0)) + (1 - b) * yn, yn)
        if o.name.startswith(("RigEyeWhite_", "RigIris_")) and w.any():
            # v12: the eye white and iris step away from this view's camera (invisible in its projection) so the lids
            # still cover them when an expression key is added on top of a view key (the two add their offsets)
            xn = xn - math.sin(th) * VIEW["PUSH_BACK"] * w
            yn = yn + math.cos(th) * VIEW["PUSH_BACK"] * w
        if o.name.startswith(("RigLidLine_", "RigLowRim_", "RigBrow")) and w.any():
            # v7: line strips also step toward this view's camera (invisible in its projection) so the slid skin's
            # chords cannot poke through them at the curved corners
            xn = xn + math.sin(th) * VIEW["PUSH"] * w
            yn = yn - math.cos(th) * VIEW["PUSH"] * w
        co = np.stack([-xn if mirror else xn, yn, z], 1)
        res[o.name] = (o, co)
    return res


def _fit_y(surfs, xr, z):
    """Smooth face depth (the per-side cubic fit) at real head coordinates."""
    out = np.zeros(len(xr))
    for sd in (1, -1):
        m = (xr * sd) >= 0
        if m.any():
            X, Z = _from_m(sd, xr[m], z[m])
            out[m] = surfs[sd].fit(X, Z)
    return out


def _box_w(xr, z):
    """1 inside the eye + brow box (either side), fading to 0 over 0.3 eye half-widths."""
    w = np.zeros(len(xr))
    for sd in (1, -1):
        X, Z = _from_m(sd, xr, z)
        d = np.maximum.reduce([np.zeros(len(X)), -1.6 - X, X - 1.25, Z - 1.15, -0.95 - Z])
        w = np.maximum(w, np.clip(1 - d / VIEW["BOX_FADE"], 0, 1) * ((xr * sd) >= 0))
    return w


def _skin_row(gg, br, M, xs, zz):
    """Skin weight and target front x along one row (z = zz) of the face surface."""
    zr = np.full(len(xs), zz)
    ys = gg.y(xs, zr)
    yy = np.clip((ys - VIEW["Y_FACE"]) / (VIEW["Y_SIDE"] - VIEW["Y_FACE"]), 0, 1)
    yf = 1 - yy * yy * (3 - 2 * yy)                       # fade out toward the temple / ear (they stay put)
    Xa = np.maximum(*[_from_m(s_, xs, zr)[0] * (s_ * xs > 0) for s_ in (1, -1)])
    core = 1 - np.clip((Xa - 1.15) / 0.30, 0, 1)          # never inside the eye box (the opening edge follows the eye)
    core = core * np.clip((-0.035 - ys) / 0.015, 0, 1)     # ... on the face front only
    front = np.maximum(yf, core)
    ww = np.zeros(len(xs)); xt = xs.copy()
    for s in M:
        ws, Z = _skin_w(s, xs, zr)
        ws = ws * front
        sel = ws > 0
        if not sel.any():
            continue
        t = np.clip((Z[sel] - 0.55) / 0.30, 0, 1); t = t * t * (3 - 2 * t)   # lid skin follows the eye map
        ut = (1 - t) * M[s]["eye"](xs[sel], zr[sel]) + t * M[s]["brow"](xs[sel], zr[sel])
        xt[sel] = gg.inv(ut, zr[sel], br); ww[sel] = ws[sel]
    return ww, xt


def add_view_keys(ob, col, tag):
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new(); bm.from_mesh(ob.data); tree = BVHTree.FromBMesh(bm); bm.free()
    surfs = {s: _Surf(ob, s, tree) for s in (1, -1)}
    g = _Grid(ob, surfs, tree)
    g.surfs = surfs
    objs = _objects(col, ob)
    th34, th90 = math.radians(VIEW["Y34"]), math.radians(90.0)
    report = {}
    for kname, th, mirror, near_only in (("VW-Yaw_L", th34, False, False), ("VW-Yaw_R", th34, True, False),
                                         ("VW-Side_L", th90, False, True), ("VW-Side_R", th90, True, True)):
        res = _key_coords(objs, g, th, mirror, near_only)
        for name, (o, co) in res.items():
            if o.data.shape_keys is None:
                o.shape_key_add(name="Basis")
            sk = o.shape_key_add(name=kname); sk.value = 0.0
            sk.data.foreach_set("co", co.astype(np.float32).ravel())
            d = np.linalg.norm(co - _basis(o), axis=1)
            report.setdefault(kname, {})[name] = round(float(d.max()) * 1000, 1)
    if VIEW["VIEW_LIT"]:
        _view_lit(ob)
    print("view keys (max move mm):", report)
    return report


def _view_lit(ob):
    """v2: skin the view keys slide gets the same 'eye_lit' mix as the lid keys (stored custom normals rotate with
    the moved faces and leave toon shadow specks on the cheek otherwise)."""
    me = ob.data
    kb = me.shape_keys.key_blocks
    B = np.array([v.co[:] for v in kb[0].data])
    disp = np.zeros(len(B))
    for k in VIEW_KEYS_NAMES:
        if k in kb:
            K = np.array([v.co[:] for v in kb[k].data])
            disp = np.maximum(disp, np.linalg.norm(K - B, axis=1))
    w = np.clip((disp - 0.0003) / VIEW["LIT_MM"], 0, 1)
    yy = np.clip((B[:, 1] - VIEW["LIT_Y"]) / 0.01, 0, 1)
    w = w * (1 - yy)                                     # front of the face only: the temple shadow keeps its edge
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    for _ in range(1):
        w2 = w.copy()
        for v in bm.verts:
            if w[v.index] < 1:
                nb = [w[e.other_vert(v).index] for e in v.link_edges]
                w2[v.index] = max(w[v.index], 0.6 * max(nb) if nb else 0)
        w = w2
    bm.free()
    a = me.attributes.get("eye_lit")
    if a is None:
        return
    old = np.zeros(len(B), np.float32); a.data.foreach_get("value", old)
    a.data.foreach_set("value", np.maximum(old, w).astype(np.float32))


def view_render(col, out, yaws=(0, 20, 35, 60, 90), ortho=0.40, cz=1.60, ty=0.0, res=700, keys=True):
    """EEVEE renders of the collection at several camera yaws with the view keys set (keys=False: all 0)."""
    sc = bpy.context.scene
    head = next(o for o in col.objects if o.name.startswith("NEW_Head_"))
    keep = set(col.objects)
    hidden = [o for o in sc.objects if o.type in ("MESH", "CURVE", "EMPTY") and o not in keep and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    ch = col.hide_render; col.hide_render = False
    old_cam, old = sc.camera, (sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath)
    cd = bpy.data.cameras.new("ViewCam"); cd.type = "ORTHO"; cd.ortho_scale = ortho
    cam = bpy.data.objects.new("ViewCam", cd); sc.collection.objects.link(cam); sc.camera = cam
    sc.render.resolution_x = sc.render.resolution_y = res
    tgt = Vector((head.location.x, ty, cz))
    paths = []
    try:
        for yaw in yaws:
            set_view(col, yaw if keys else 0.0) if keys else set_view(col, 0.0)
            a = math.radians(yaw)
            cam.location = tgt + Vector((math.sin(a), -math.cos(a), 0.0)) * 2.0
            cam.rotation_euler = (math.radians(90), 0.0, a)
            sc.render.filepath = "%s_y%03d.png" % (out, int(round(yaw)) % 360)
            bpy.ops.render.render(write_still=True)
            paths.append(sc.render.filepath)
    finally:
        set_view(col, 0.0)
        sc.camera = old_cam
        sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath = old
        bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
        col.hide_render = ch
        for o in hidden:
            o.hide_render = False
    return paths
