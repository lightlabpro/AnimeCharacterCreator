"""q14 mouth rig: the MHS3 mouth as separate painted pieces with expression keys (exec'd in apply_look.py's globals
after face_strokes, so bpy, np, math, Vector, S, O, MOUTH_Z, MOUTH_HW, MOUTH_LINE_W, MOUTH_LINE, _bvh, _strip,
_emission, EXPRESSIONS, EYES_PATH are available).

Sammy: "start on facial expressions ... each element is separate (eyebrows, eyes, nose, mouth, etc.)". Before this the
mouth was one closed painted line and an under-lip shadow, with no keys. MHS3 draws the mouth as flat shapes on the
face: a dark top lip line, a dark interior when open (upper teeth as a white band under the top line, a red tongue at
the bottom), a thin lower lip line and the soft under-lip shadow (ref_face.png: Leo talking). Each is its own object
with the same PF-Mouth* keys, so the creator / app can drive the mouth independently (key names follow src/model/performance.ts where
the app already has the shape: PF-SmileClosed, PF-SmileOpenJaw, PF-Frown, PF-Smirk_L/R, PF-Pout, PF-VisAA, PF-VisOH,
PF-VisEE, PF-VisWide; new: PF-MouthWide, PF-MouthNarrow, PF-NoseSneer) of brows, eyes and nose:

  NewMouthLine_<tag>    top lip line (dark)                     NewMouthInside_<tag>  open-mouth interior (dark red)
  NewMouthTeeth_<tag>   upper teeth band (off-white)            NewMouthTongue_<tag>  tongue (red)
  NewMouthLower_<tag>   lower lip line (appears as it opens)    NewLipShadow_<tag>    under-lip shadow (moves down)

The closed basis collapses the interior, teeth, tongue and lower line to zero height on the top line, so nothing shows
until a key opens the mouth. Keys add: Smile + Open = an open smile, etc. All pieces follow the skin (front-most ray,
like the other face strokes) and stay out of the view-key remap (VIEW SKIP "NewMouth" / "NewLip").
"""
import json
import os

MOUTH_N = 25           # samples across the mouth
MOUTH_TEETH_H = 0.011  # H: upper teeth band height (capped at 45% of the opening)
MOUTH_TONGUE_H = 0.013  # H: tongue height (capped at 40% of the opening)
C_INSIDE = (0.20, 0.035, 0.035, 1)
C_TEETH = (0.88, 0.86, 0.82, 1)
C_TONGUE = (0.62, 0.20, 0.20, 1)

# each key: parameters of the mouth shape (anything not given stays at the closed default)
MOUTH_KEYS = {
    "PF-SmileClosed": dict(corner=0.024, mid=-0.004),
    "PF-Frown": dict(corner=-0.017, mid=0.004),
    "PF-Smirk_L": dict(corner_l=0.030, corner_r=-0.006),
    "PF-Smirk_R": dict(corner_r=0.030, corner_l=-0.006),
    "PF-MouthWide": dict(width=1.18),
    "PF-MouthNarrow": dict(width=0.80),
    "PF-Pout": dict(width=0.55, mid=0.007, corner=-0.012, open=0.006, shape="O"),
    "PF-VisAA": dict(width=0.86, open=0.050, up=0.003, shape="A"),
    "PF-VisOH": dict(width=0.46, open=0.042, up=0.010, shape="O"),
    "PF-VisEE": dict(width=1.10, open=0.022, corner=0.004, shape="E"),
    "PF-SmileOpenJaw": dict(width=1.02, open=0.044, corner=0.014, up=-0.002, shape="D"),
    "PF-VisWide": dict(width=0.96, open=0.064, corner=-0.010, up=0.006, shape="A"),
}
_PROFILE = {"A": 0.6, "O": 0.5, "E": 0.22, "D": 0.85}

MOUTH_EXPRESSIONS = {
    # q14b: the default brows slope down toward the nose (identity: BROW_INNER_DROP), so TypeSafe read the neutral face
    # and most presets as "angry"; every non-angry preset now lifts the inner brow ends (PF-BrowInnerUp)
    "smile": {"PF-SmileClosed": 1, "PF-BrowInnerUp_L": 0.6, "PF-BrowInnerUp_R": 0.6, "PF-BrowUp": 0.2},
    "happy": {"PF-EyeHappy": 1, "PF-BrowInnerUp_L": 0.7, "PF-BrowInnerUp_R": 0.7, "PF-BrowUp": 0.4, "PF-SmileOpenJaw": 1},
    "laugh": {"PF-Blink_L": 1, "PF-Blink_R": 1, "PF-BrowInnerUp_L": 0.8, "PF-BrowInnerUp_R": 0.8, "PF-BrowUp": 0.6, "PF-SmileOpenJaw": 1, "PF-VisAA": 0.4},
    "amazed": {"PF-EyeWide": 1, "PF-BrowUp": 1, "PF-BrowInnerUp_L": 0.4, "PF-BrowInnerUp_R": 0.4, "PF-IrisSmall": 1, "PF-VisOH": 1},
    "sad": {"PF-EyeSad": 1, "PF-BrowSad": 1, "PF-BrowInnerUp_L": 0.5, "PF-BrowInnerUp_R": 0.5, "PF-LookDown": 0.4, "PF-Frown": 1},
    "angry": {"PF-EyeAngry": 1, "PF-BrowAngry": 1, "PF-Frown": 0.6, "PF-NoseSneer": 0.5},
    "shout": {"PF-EyeAngry": 1, "PF-BrowAngry": 1, "PF-VisWide": 1, "PF-NoseSneer": 0.6},
    "worried": {"PF-BrowInnerUp_L": 1, "PF-BrowInnerUp_R": 1, "PF-BrowSad": 0.5, "PF-EyeSad": 0.6, "PF-EyeWide": 0.3, "PF-Frown": 0.7, "PF-MouthNarrow": 0.4},
    "determined": {"PF-BrowAngry": 0.4, "PF-EyeAngry": 0.3, "PF-Smirk_L": 1, "PF-BrowRaise_R": 0.3},
    "skeptical": {"PF-BrowRaise_L": 1, "PF-BrowLower_R": 1, "PF-Smirk_R": 0.8, "PF-LookRight": 0.3},
    "pout": {"PF-Pout": 1, "PF-BrowSad": 0.6, "PF-BrowInnerUp_L": 0.5, "PF-BrowInnerUp_R": 0.5},
    "blink": {"PF-Blink_L": 1, "PF-Blink_R": 1, "PF-BrowInnerUp_L": 0.3, "PF-BrowInnerUp_R": 0.3},
    "talk_a": {"PF-VisAA": 0.6},
    "talk_o": {"PF-VisOH": 0.7},
    "talk_e": {"PF-VisEE": 0.8},
}


def mouth_shape(p):
    """Upper / lower edge of the mouth (H units) for one parameter set: arrays x, z_up, z_lo."""
    u = np.linspace(-1, 1, MOUTH_N)
    w = MOUTH_HW * MOUTH_LINE_W * p.get("width", 1.0)
    x = u * w
    z_up = MOUTH_Z + 0.004 - 0.010 * u ** 2                         # the closed line (as before)
    z_up = z_up + p.get("corner", 0.0) * np.abs(u) ** 3 + p.get("mid", 0.0) * (1 - u ** 2) + p.get("up", 0.0) * (1 - u ** 2)
    z_up = z_up + p.get("corner_l", 0.0) * np.clip(u, 0, 1) ** 3 + p.get("corner_r", 0.0) * np.clip(-u, 0, 1) ** 3
    op = p.get("open", 0.0)
    prof = (1 - u ** 2) ** _PROFILE.get(p.get("shape", "A"), 0.6)
    if p.get("shape") == "D":                                        # open smile: flat top, round deep bottom
        z_up = z_up + 0.006 * (1 - u ** 2) * (op / 0.044)
    z_lo = z_up - op * prof
    return x, z_up, z_lo


def build_mouth(ob, col, off_x, tag):
    tree = _bvh(ob)

    def on_skin(x, z, lift):
        best = None
        for dz in (0.0, -0.006, 0.006, -0.012, 0.012, -0.02, 0.02):
            loc, nrm, _, _ = tree.ray_cast(Vector((x * S, -1.0, O + (z + dz) * S)), Vector((0, 1, 0)))
            if loc is not None and (best is None or loc.y < best.y - 0.0015):
                best = loc
        if best is None:
            return None
        return Vector((x * S, best.y, O + z * S)) + Vector((0, -1, 0)) * lift

    def rows_of(top, bot, lift):
        """top / bot: lists of (x, z) - one row per sample; a missing skin hit reuses the last good row."""
        rows, last = [], None
        for (xa, za), (xb, zb) in zip(top, bot):
            a_, b_ = on_skin(xa, za, lift), on_skin(xb, zb, lift)
            if a_ is None or b_ is None:
                a_, b_ = last if last else (Vector((xa * S, -0.05, O + za * S)), Vector((xb * S, -0.05, O + zb * S)))
            rows.append((a_, b_)); last = (a_, b_)
        return rows

    def line_rows(x, z, width, lift):
        top, bot = [], []
        for i in range(len(x)):
            j, k = min(i + 1, len(x) - 1), max(i - 1, 0)
            tx, tz = x[j] - x[k], z[j] - z[k]; L = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / L, tx / L
            top.append((x[i] - nx * width[i] / 2, z[i] - nz * width[i] / 2)); bot.append((x[i] + nx * width[i] / 2, z[i] + nz * width[i] / 2))
        return rows_of(top, bot, lift)

    def pieces(p):
        x, zu, zl = mouth_shape(p)
        t = np.linspace(0, 1, MOUTH_N); s = np.sin(np.pi * t)
        gap = np.maximum(zu - zl, 0.0)
        out = {}
        out["NewMouthLine"] = line_rows(x, zu, 0.006 * MOUTH_LINE * (0.25 + 0.75 * s), 0.0020)
        out["NewMouthInside"] = rows_of(list(zip(x, zu)), list(zip(x, zl)), 0.0013)
        th = np.minimum(MOUTH_TEETH_H, 0.45 * gap) * (np.abs(np.linspace(-1, 1, MOUTH_N)) < 0.8)
        out["NewMouthTeeth"] = rows_of(list(zip(x, zu)), list(zip(x, zu - th)), 0.0016)
        tg = np.minimum(MOUTH_TONGUE_H, 0.40 * gap) * np.clip(1 - np.linspace(-1, 1, MOUTH_N) ** 2 / 0.55, 0, 1)
        out["NewMouthTongue"] = rows_of(list(zip(x, zl + tg)), list(zip(x, zl)), 0.0015)
        lw = 0.0032 * np.clip(p.get("open", 0.0) / 0.02, 0, 1) * (0.2 + 0.8 * s)
        out["NewMouthLower"] = line_rows(x, zl, lw, 0.0018)
        # under-lip shadow: same lens as LIP_SHADOW (apply_look face_strokes), following the lower edge down
        ipd = 2 * EYE_X; wd, ht = LIP_SHADOW_W * ipd, 0.050 * ipd * LIP_SHADOW
        n = MOUTH_N; tt = np.linspace(-1, 1, n)
        drop = float(np.max(gap))
        sx = wd / 2 * tt; sz = MOUTH_Z - 0.040 - drop * 0.9 - 0.003 * (1 - tt ** 2)
        sw = ht * (0.1 + 0.9 * np.sin(np.pi * (tt + 1) / 2) ** 0.6)
        out["NewLipShadow"] = line_rows(sx, sz, sw, 0.0006)
        return out

    mats = {"NewMouthLine": _emission("MAT_PaintMouth_" + tag, (0.10, 0.025, 0.02, 1)),
            "NewMouthInside": _emission("MAT_MouthInside_" + tag, C_INSIDE),
            "NewMouthTeeth": _emission("MAT_MouthTeeth_" + tag, C_TEETH),
            "NewMouthTongue": _emission("MAT_MouthTongue_" + tag, C_TONGUE),
            "NewMouthLower": _emission("MAT_PaintMouth_" + tag, (0.10, 0.025, 0.02, 1))}
    old_shadow = col.objects.get("NewLipShadow_" + tag)
    mats["NewLipShadow"] = old_shadow.data.materials[0] if old_shadow and old_shadow.data.materials else mats["NewMouthInside"]
    for nm in mats:
        o = col.objects.get(nm + "_" + tag)
        if o is not None:
            me = o.data; bpy.data.objects.remove(o)
            if me.users == 0:
                bpy.data.meshes.remove(me)
    base = pieces({})
    keyed = {k: pieces(p) for k, p in MOUTH_KEYS.items()}
    made = []
    for nm, rows in base.items():
        o = _strip(nm + "_" + tag, rows, mats[nm], col, off_x)
        o.visible_shadow = False
        o.shape_key_add(name="Basis")
        for kname, kp in keyed.items():
            co = []
            for a_, b_ in kp[nm]:
                co += [tuple(a_), tuple(b_)]
            kb = o.shape_key_add(name=kname); kb.value = 0.0
            kb.data.foreach_set("co", np.asarray(co, np.float32).ravel())
        made.append(o)
    EXPRESSIONS.update(MOUTH_EXPRESSIONS)
    try:
        json.dump(EXPRESSIONS, open(os.path.join(os.path.dirname(EYES_PATH), "expressions.json"), "w"), indent=1)
    except Exception:
        pass
    print("q14 mouth rig: %d pieces, %d keys" % (len(made), len(MOUTH_KEYS)))
    return made


def shift_eye_parts(col, dy=0.0015):
    """q14: eye white and iris sit 1.5 mm further behind the skin (partial lid keys showed them below the lower lid)."""
    for o in col.objects:
        if o.name.startswith(("RigEyeWhite_", "RigIris_")):
            me = o.data
            blocks = list(me.shape_keys.key_blocks) if me.shape_keys else []
            for kb in blocks or [None]:
                d = kb.data if kb is not None else me.vertices
                co = np.empty(len(d) * 3, np.float32); d.foreach_get("co", co); co = co.reshape(-1, 3)
                co[:, 1] += dy; d.foreach_set("co", co.ravel())
            me.update()


def add_nose_keys(col, tag, up=0.0020, widen=1.14):
    """PF-NoseSneer: the nose strokes lift and the shadow lens widens (added last, on the baked strokes)."""
    for nm in ("NewNoseShade_", "NewNoseLine_", "NewNoseHL_"):            # HL moves with them (its tip showed)
        o = col.objects.get(nm + tag)
        if o is None:
            continue
        me = o.data
        co = np.array([v.co[:] for v in me.vertices])
        if not me.shape_keys:
            o.shape_key_add(name="Basis")
        k = co.copy(); k[:, 2] += up
        if nm == "NewNoseShade_":
            cx = co[:, 0].mean(); k[:, 0] = cx + (co[:, 0] - cx) * widen
        kb = o.shape_key_add(name="PF-NoseSneer"); kb.value = 0.0
        kb.data.foreach_set("co", k.astype(np.float32).ravel())
