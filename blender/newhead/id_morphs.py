"""p1: identity morphs (the creator's ID- sliders) and the baked default proportions for the new head.

exec'd inside apply_look.py's namespace (np, bpy, S, O, smooth, main_component, EYE_* ... available) after the rig,
the face strokes and the view keys exist. Two jobs, one set of spatial maps:

1. Bake (default proportions). Measured on the MHS3 Leo render and the game frame, in units of D = pupil line to chin
   bottom (independent of the skull and the hair): eye width 0.32-0.34 D, pupil distance 0.70-0.73 D, mouth line
   0.64 D under the pupils, mouth width 0.49 D, chin a short flat front (half width ~0.18 D at the bottom).
   n56 had eye width 0.43 D and pupil distance 0.82 D (eyes ~30 % too big and set wide) and a pointed V chin.
   The bake maps EVERY shape key block of the head and of every face part through the same smooth map, so the lid,
   brow and view keys stay consistent; the asset mesh keeps its topology.
2. ID- keys: the same maps with slider-sized amounts, added as new keys (value 0) on every object they move:
   ID-EyeSize(_Neg), ID-EyeSpacing(_Neg), ID-EyeHeight(_Neg), ID-MouthWidth(_Neg), ID-MouthHeight(_Neg),
   ID-JawWidth(_Neg), ID-ChinWidth(_Neg), ID-ChinLength(_Neg), ID-EarSize(_Neg), ID-EarOut.
   (Lash and brow thickness / length keys are built with the strips in face_rig.py.)

Eye map: the eye parts (eye white, iris, lid line, cover, brow, brow shade) move rigidly with their eye (similarity
about the eye centre); the skin follows with weight 1 over the eye-and-brow box and a smooth falloff outside it, 0 on
the face's centre line (the nose bridge stays put) and on the back half of the head.
"""
import os

EYE_SIZE_BAKE = 0.80        # eye (and brow) scale about the eye centre (x)
EYE_SIZE_BAKE_Z = 0.92      # ... vertical (the MHS3 opening is taller for its width than n56's: h/w ~0.6)
EYE_SPACING_BAKE = 0.89     # eye centre distance from the face centre line
EAR_OUT_BAKE = 2.0          # q5: TypeSafe ears_closer (agreed; Leo ears lie close); was 8 deg: ears swing further off the head (MHS3 front views show the inner ear)
CHIN_WIDE_BAKE = 0.065      # q4, q10: TypeSafe chin_wider (agreed both orders twice; measured ~0.33 vs Leo 0.37 D); H: the chin front widens by this at the bottom (flatter, squarer MHS3 male chin)
ID_AMOUNTS = {"EyeSize": (1.15, 0.87), "EyeSpacing": (1.08, 0.93), "EyeHeight": (0.025, -0.025),
              "MouthWidth": (1.15, 0.87), "MouthHeight": (0.02, -0.02), "JawWidth": (1.08, 0.93),
              "ChinWidth": (0.02, -0.015), "ChinLength": (0.03, -0.025), "EarSize": (1.15, 0.87), "EarOut": 12.0}

OUT_FALL = 0.42             # eye map falloff past the outer eye corner (W2)
SKIN_SLIDE = 1              # q1: moved skin slides on the pre-bake surface (no dent beside the eyes)
SLIDE_RIM = (0.004, 0.014)  # q1: m from the lid rim: below the first value the skin keeps its own depth
ORBIT_FILL = (1.0, 0.085, 0.10, 0.14)   # q1c: strength, brow-line / cheek-line offsets above / below the eye centre (S), region width past the outer corner (S)
REPROJECT = ("RigBrow_", "RigBrowShade_")   # parts that sit on skin outside the rigid box: depth re-fitted to the skin
EYE_PART_PREFIX = ("RigEyeWhite_", "RigIris_", "RigLidLine_", "RigLidCover_", "RigLowRim_", "RigBrow_", "RigBrowShade_")


def _es():
    g = {}
    exec(open(os.path.join(os.path.dirname(EYES_PATH), "..", "..", "..", "blender", "newhead", "eye_shape.py")).read(), g)
    for k, v in EYE_PAINT.items():
        if k in g:
            g[k] = v
    return g


def _eye_weight(P, side, ES):
    """Skin weight of one eye's map (1 over the eye + brow box, smooth falloff, 0 on the centre line / back)."""
    w2 = ES["EYE_W2"] * S
    X = (side * P[:, 0] - ES["EYE_CX"] * S) / w2
    Z = (P[:, 2] - (O + ES["EYE_Z0"] * S)) / w2
    # the box covers the opening (outer corner at X 0.91) with weight 1; past the outer corner the falloff is short
    # (OUT_FALL), so the side of the face - its silhouette at 20-35 deg - does not move (p2 dented the cheek contour)
    dxi = np.maximum(-2.05 - X, 0.0) / 0.7
    dxo = np.maximum(X - 0.98, 0.0) / OUT_FALL
    dz = np.maximum(np.maximum(-1.25 - Z, Z - 1.35), 0.0) / 0.7
    w = 1 - smooth(0.0, 1.0, np.hypot(np.maximum(dxi, dxo), dz))
    w = w * smooth(0.0, 0.004, side * P[:, 0])          # 0 at and across the centre line
    w = w * smooth(-0.02, -0.055, P[:, 1])              # face front only (the opening reaches y -0.060)
    return w


def eye_map(P, rigid_side, size, spacing, dz, ES, size_z=None):
    """rigid_side: +1 / -1 for an eye part of that side (weight 1), None for skin-like objects, 0 = not moved."""
    out = P.copy()
    if rigid_side == 0:
        return out
    cz = O + ES["EYE_Z0"] * S
    for side in (1, -1):
        cx = side * ES["EYE_CX"] * S
        if rigid_side is None:
            w = _eye_weight(P, side, ES)
        else:
            w = np.full(len(P), 1.0 if rigid_side == side else 0.0)
        tx = cx * spacing + (P[:, 0] - cx) * size
        tz = cz + dz + (P[:, 2] - cz) * (size if size_z is None else size_z)
        out[:, 0] += w * (tx - P[:, 0])
        out[:, 2] += w * (tz - P[:, 2])
    return out


def mouth_map(P, sx, dz):
    zm = O + MOUTH_Z * S
    hw = MOUTH_HW * S * 2.2
    w = (1 - smooth(0.6, 1.6, np.hypot(P[:, 0] / hw, (P[:, 2] - zm) / (0.07 * S)))) * smooth(0.0, -0.05, P[:, 1])
    out = P.copy()
    out[:, 0] += w * (P[:, 0] * sx - P[:, 0])
    out[:, 2] += w * dz
    return out


def lower_map(P, jaw_sx, chin_b, chin_dz):
    """Lower face: jaw width (x scale fading in below the cheekbones), chin width (a front-only additive spread that
    is largest at the chin bottom) and chin length (the chin moves down / up)."""
    zh = (P[:, 2] - O) / S
    front = smooth(0.015, -0.035, P[:, 1])
    out = P.copy()
    wj = smooth(0.38, 0.12, zh) * smooth(-0.06, 0.02, zh)
    out[:, 0] += wj * (P[:, 0] * jaw_sx - P[:, 0])
    ra = np.hypot(P[:, 0] / S / 0.20, (P[:, 1] / S - NECK_Y) / (0.20 * 0.92))   # the neck column (shade_mask's)
    wc = smooth(0.20, 0.02, zh) * smooth(-0.05, 0.005, zh) * front * smooth(1.05, 1.25, ra)   # p7: not the neck
    out[:, 0] += chin_b * S * wc * np.tanh(P[:, 0] / 0.012)
    wl = smooth(0.24, 0.02, zh) * smooth(-0.08, 0.0, zh) * smooth(0.02, -0.05, P[:, 1])
    out[:, 2] -= chin_dz * S * wl
    return out


def ear_map(P, ear, size, out_deg):
    out = P.copy()
    for side in (1, -1):
        m = ear & (np.sign(P[:, 0]) == side)
        if not m.any():
            continue
        E = P[m]
        root = np.array([E[:, 0].min() if side > 0 else E[:, 0].max(), E[:, 1].min(), E[:, 2].mean()])
        Q = root + (E - root) * size
        if out_deg:                                   # swing the back of the ear away from the head (about z)
            a = np.radians(out_deg)
            d = Q - root
            c, s_ = np.cos(a), np.sin(a)
            Q = root + np.stack([d[:, 0] * c + side * d[:, 1] * s_, -side * d[:, 0] * s_ + d[:, 1] * c, d[:, 2]], 1)
        out[m] = Q
    return out


def _objects(col):
    obs = []
    for o in col.objects:
        if o.type != "MESH" or o.name.startswith("NEW_Ears_"):
            continue
        side = None
        if o.name.startswith("NewNose"):
            side = 0                                     # on the centre line: the eye maps leave it (p9 bent the highlight)
        if o.name.startswith(EYE_PART_PREFIX):
            side = 1 if o.name.endswith("_L") else -1
        obs.append((o, side))
    return obs


def _blocks(o):
    ks = o.data.shape_keys
    return list(ks.key_blocks) if ks else []


def _get(kb_or_me):
    d = kb_or_me.data if hasattr(kb_or_me, "data") and not hasattr(kb_or_me, "vertices") else kb_or_me.vertices
    co = np.empty(len(d) * 3, np.float32); d.foreach_get("co", co)
    return co.reshape(-1, 3).astype(float)


def _set(target, P):
    d = target.data if hasattr(target, "data") and not hasattr(target, "vertices") else target.vertices
    d.foreach_set("co", P.astype(np.float32).ravel())


def _tree(P, head):
    from mathutils.bvhtree import BVHTree
    polys = [tuple(p.vertices) for p in head.data.polygons]
    return BVHTree.FromPolygons([tuple(v) for v in P], polys)


def _skin_y(tree, P):
    from mathutils import Vector
    y = np.full(len(P), np.nan)
    for i, p in enumerate(P):
        h = tree.ray_cast(Vector((p[0], -1.0, p[2])), Vector((0, 1, 0)))
        if h[0] is not None:
            y[i] = h[0].y
    return y


def bake(col, head):
    ES = _es()
    ear = ~main_component(head.data)
    hb = head.data.shape_keys.key_blocks[0] if head.data.shape_keys else None
    t_old = _tree(_get(hb) if hb else _get(head.data), head)

    def full(P, o, side):
        P = eye_map(P, side, EYE_SIZE_BAKE, EYE_SPACING_BAKE, 0.0, ES, EYE_SIZE_BAKE_Z)
        if side in (None, 0):
            P2 = lower_map(P, 1.0, CHIN_WIDE_BAKE, 0.0)
            if o == head:
                P2[ear] = P[ear]
                if EAR_OUT_BAKE:
                    P2 = ear_map(P2, ear, 1.0, EAR_OUT_BAKE)
            P = P2
        return P
    obs = _objects(col)
    obs.sort(key=lambda t: t[0] != head)                 # head first (the re-projection needs its new surface)
    t_new = None
    # q1 (2026-10-15): the eye map moved the brow ridge and the cheek tops with the eye (x 0.80 / z 0.92 about the eye
    # centre) and they kept their depth, so at brow and cheek height the face's cross-section got a ~1 cm concave dent
    # beside each eye (Sammy: "like a doll's head pushed in"; face_study setback at 0.30 hh 0.16 -> 0.22 vs dataset
    # median 0.13-0.15). Now the moved skin slides ON the old surface (its depth is re-read from the pre-bake skin at
    # its new x/z), except at the lid rim, which keeps its own depth so the opening is unchanged.
    dy_head = None
    if SKIN_SLIDE and hb is not None:
        P0 = _get(hb); Q0 = full(P0, head, None)
        Qe = eye_map(P0, None, EYE_SIZE_BAKE, EYE_SPACING_BAKE, 0.0, ES, EYE_SIZE_BAKE_Z)      # q1b: only the eye map's moves
        moved = np.linalg.norm((Qe - P0)[:, [0, 2]], axis=1) > 1e-5
        lid = np.load(NPZ)["lid"].astype(bool) if "lid" in np.load(NPZ).files else np.zeros(len(P0), bool)
        if lid.any() and len(lid) == len(P0):
            from mathutils.kdtree import KDTree
            kd = KDTree(int(lid.sum()))
            for i, p in zip(np.nonzero(lid)[0], P0[lid]):
                kd.insert((p[0], 0.0, p[2]), int(i))
            kd.balance()
            dl = np.array([kd.find((p[0], 0.0, p[2]))[2] for p in P0])
        else:
            dl = np.full(len(P0), 1.0)
        wr = np.where(moved & ~ear, smooth(SLIDE_RIM[0], SLIDE_RIM[1], dl), 0.0)
        off = P0[:, 1] - _skin_y(t_old, P0)
        yn = _skin_y(t_old, Q0) + off
        ok = np.isfinite(yn) & np.isfinite(off) & (np.abs(off) < 0.002)     # q1b: front-most skin only (not undersides)
        dy_head = np.where(ok, wr * (yn - Q0[:, 1]), 0.0)
        if ORBIT_FILL:
            # q1c: the lateral orbit beside the (smaller) opening still sat ~1.5 cm behind the line from the brow ridge to
            # the cheek (face_study eye-level setback at 0.30 hh 0.215 vs dataset p10-p90 0.10-0.17, n=7 verified anime
            # heads) - the 3/4 silhouette notched in at the eye. Fill it to that line: per vertex, the skin depth above
            # (brow) and below (cheek) at the same x is read off the baked surface and the vertex is pulled forward to the
            # straight line between them (never pushed back), fading out at the region's edges and at the lid rim.
            Qb = Q0.copy(); Qb[:, 1] += dy_head
            tb = _tree(Qb, head)
            ez = O + ES["EYE_Z0"] * S
            xo = (ES["EYE_CX"] * EYE_SPACING_BAKE + 0.91 * ES["EYE_W2"] * EYE_SIZE_BAKE) * S      # outer corner after the bake
            zt, zb = ez + ORBIT_FILL[1] * S, ez - ORBIT_FILL[2] * S
            ax = np.abs(Qb[:, 0])
            reg = (ax > xo - 0.006) & (ax < xo + ORBIT_FILL[3] * S) & (Qb[:, 2] < zt) & (Qb[:, 2] > zb) & (Qb[:, 1] < -0.02) & ~ear
            idx = np.nonzero(reg)[0]
            if len(idx):
                Pt = Qb[idx].copy(); Pt[:, 2] = zt; Pb = Qb[idx].copy(); Pb[:, 2] = zb
                yt, yb = _skin_y(tb, Pt), _skin_y(tb, Pb)
                f = (Qb[idx, 2] - zb) / (zt - zb)
                yl = yb + (yt - yb) * f
                wx = smooth(xo - 0.006, xo + 0.002, ax[idx]) * smooth(xo + ORBIT_FILL[3] * S, xo + 0.5 * ORBIT_FILL[3] * S, ax[idx])
                wz = np.sin(np.pi * np.clip(f, 0, 1)) ** 0.5
                wl = smooth(0.002, 0.008, dl[idx])
                pull = np.where(np.isfinite(yl), np.minimum(yl - Qb[idx, 1], 0.0), 0.0) * ORBIT_FILL[0]
                dy_head[idx] += pull * wx * wz * wl
                print("q1c orbit fill: %d verts, max %.1f mm" % (len(idx), -1000 * (pull * wx * wz * wl).min()))
    for o, side in obs:
        rep = o.name.startswith(REPROJECT)
        for tgt in _blocks(o) + [o.data]:
            P = _get(tgt)
            Q = full(P, o, side)
            if o == head and dy_head is not None:
                Q[:, 1] += dy_head
            if rep and t_new is not None:
                off = P[:, 1] - _skin_y(t_old, P)        # how far in front of the skin it sat
                yn = _skin_y(t_new, Q) + off
                Q[:, 1] = np.where(np.isfinite(yn), yn, Q[:, 1])
            _set(tgt, Q)
        o.data.update()
        if o == head:
            t_new = _tree(_get(hb) if hb else _get(head.data), head)


def add_id_keys(col, head):
    ES = _es()
    ear = ~main_component(head.data)
    A = ID_AMOUNTS
    for o, side in _objects(col):
        bl = _blocks(o)
        B = _get(bl[0]) if bl else _get(o.data)
        keys = {}
        for nm, (pos, neg) in (("EyeSize", A["EyeSize"]), ("EyeSpacing", A["EyeSpacing"])):
            keys["ID-" + nm] = eye_map(B, side, pos if nm == "EyeSize" else 1.0, pos if nm == "EyeSpacing" else 1.0, 0.0, ES)
            keys["ID-" + nm + "_Neg"] = eye_map(B, side, neg if nm == "EyeSize" else 1.0, neg if nm == "EyeSpacing" else 1.0, 0.0, ES)
        keys["ID-EyeHeight"] = eye_map(B, side, 1.0, 1.0, A["EyeHeight"][0] * S, ES)
        keys["ID-EyeHeight_Neg"] = eye_map(B, side, 1.0, 1.0, A["EyeHeight"][1] * S, ES)
        if side in (None, 0):
            keys["ID-MouthWidth"] = mouth_map(B, A["MouthWidth"][0], 0.0)
            keys["ID-MouthWidth_Neg"] = mouth_map(B, A["MouthWidth"][1], 0.0)
            keys["ID-MouthHeight"] = mouth_map(B, 1.0, A["MouthHeight"][0] * S)
            keys["ID-MouthHeight_Neg"] = mouth_map(B, 1.0, A["MouthHeight"][1] * S)
            keys["ID-JawWidth"] = lower_map(B, A["JawWidth"][0], 0.0, 0.0)
            keys["ID-JawWidth_Neg"] = lower_map(B, A["JawWidth"][1], 0.0, 0.0)
            keys["ID-ChinWidth"] = lower_map(B, 1.0, A["ChinWidth"][0], 0.0)
            keys["ID-ChinWidth_Neg"] = lower_map(B, 1.0, A["ChinWidth"][1], 0.0)
            keys["ID-ChinLength"] = lower_map(B, 1.0, 0.0, A["ChinLength"][0])
            keys["ID-ChinLength_Neg"] = lower_map(B, 1.0, 0.0, A["ChinLength"][1])
            if o == head:
                for k in list(keys):
                    keys[k][ear] = B[ear]
                keys["ID-EarSize"] = ear_map(B, ear, A["EarSize"][0], 0.0)
                keys["ID-EarSize_Neg"] = ear_map(B, ear, A["EarSize"][1], 0.0)
                keys["ID-EarOut"] = ear_map(B, ear, 1.0, A["EarOut"])
        if not bl:
            o.shape_key_add(name="Basis")
        made = 0
        for k, P in keys.items():
            if np.abs(P - B).max() < 1e-6:
                continue                                  # this object is not moved by that slider
            kb = o.shape_key_add(name=k); kb.value = 0.0
            _set(kb, P); made += 1
        if made == 0 and not bl:
            o.shape_key_clear()
