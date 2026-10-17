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

MOUTH_N = 33           # samples across the mouth
MOUTH_TEETH_H = 0.007  # H: upper teeth band height (capped at MOUTH_TEETH_CAP of the opening); q16 0.013 -> 0.009 (Sammy: buckteeth at 3/4)
MOUTH_TEETH_CAP = 0.30
MOUTH_LIFT = dict(inside=0.0010, tongue=0.0015, teeth=0.0019, lower=0.0023, line=0.0026)   # q16: halving them brought the jagged tongue edge back   # q15: m off the skin per layer (was 0.0013 / 0.0015 / 0.0016 / 0.0018 / 0.0020: the layers z-fought into jagged tongue and teeth edges)
MOUTH_TONGUE_H = 0.030  # H: tongue height (capped at MOUTH_TONGUE_CAP of the opening)
MOUTH_TONGUE_CAP = 0.40
MOUTH_TONGUE_W = 0.62      # q18: half-width of the tongue hump (share of the mouth half-width)
MOUTH_TONGUE_INSET = 0.10  # q18: lift of the tongue off the bottom edge (share of the opening)
MOUTH_TONGUE_MODE = 1      # q18b: 1 = the tongue fills the bottom of the bowl up to a gentle arc (MHS3 m02 / m08), 0 = the k1 hump
MOUTH_TONGUE_FRAC = 0.40   # q18b: arc height at the centre (share of the centre opening)
MOUTH_TONGUE_DROOP = 0.25  # q18b: how far the arc falls toward the corners (share of the centre opening at |u| = 1)
MOUTH_TEETH_W = 0.75       # q18b: teeth band half-width (share of the mouth half-width; was 0.88); MHS3 front laughs show little or no teeth
MOUTH_CORNER_DIP = 0.007   # q18b: the open top edge curls down at the ends (H at full open) - rounded corners, no flared tips
MOUTH_CORNER_DIP_D = 0.0   # q18b: the same for the open smile (D); 0.007 made laugh read "sad" at 3/4 (TypeSafe)
MOUTH_SHADOW_OPEN = 1.0    # q18b: an open mouth pulls the under-lip shadow up toward its bottom edge and narrows it (MHS3: short, close)
MOUTH_U_SINE = 1       # q17: 1 = sample the mouth width sine-spaced (dense at the corners: no straight end segments)


def _mu():
    t = np.linspace(-1, 1, MOUTH_N)
    return np.sin(0.5 * np.pi * t) if MOUTH_U_SINE else t
C_INSIDE = (0.117, 0.040, 0.040, 1)   # q17: MHS3 sampled (96,56,56) sRGB
C_TEETH = (0.88, 0.86, 0.82, 1)
C_TONGUE = (0.644, 0.171, 0.115, 1)   # q17: MHS3 sampled (210,115,95) sRGB
C_THROAT = (0.216, 0.045, 0.04, 1)   # q19: MHS3 m02 / m08: a medium red-brown band at the back of the tongue, (128,60,56) sRGB
C_TEETH_SHADE = (0.578, 0.565, 0.672, 1)   # q19: MHS3 m08 / m03: the lower part and the ends of the teeth band in a cool grey, (200,198,214) sRGB
MOUTH_THROAT = 0.0        # q19: height of the throat band over the tongue arc (share of the centre opening); 0 = off
MOUTH_TEETH_SHADE = 0.0   # q19: share of the teeth band (from its lower edge) drawn in C_TEETH_SHADE; 0 = off
MOUTH_DEEP = 0.0          # q20: darker band at the top of the interior under the teeth (share of the opening); 0 = off
C_DEEP = (0.045, 0.014, 0.014, 1)   # q20: (60,30,30) sRGB
UPPER_LIP_SHADE = 0.0     # q20: thin shade band over the top line (upper lip plane); 0 = off
LIP_SHADOW_RAW = 1        # q20: under-lip shadow follows the exact skin depth (no float / spike in profile)
MOUTH_TEETH_TAPER = 0.5   # q19: exponent of the teeth band's end taper (0.5 round ends, 1.0+ pointed, thinner toward the corners)

# each key: parameters of the mouth shape (anything not given stays at the closed default)
MOUTH_KEYS = {
    "PF-SmileClosed": dict(corner=0.024, mid=-0.004),
    "PF-Frown": dict(corner=-0.017, mid=0.004),
    "PF-Smirk_L": dict(corner_l=0.030, corner_r=-0.006),
    "PF-Smirk_R": dict(corner_r=0.030, corner_l=-0.006),
    "PF-MouthWide": dict(width=1.18),
    "PF-MouthNarrow": dict(width=0.80),
    "PF-Pout": dict(width=0.55, mid=0.007, corner=-0.012, open=0.006, shape="O", shadow_up=0.010, shadow_w=0.8, shadow_h=1.2),   # q16: small pucker + raised fuller lip shadow (TypeSafe p_clear 0.57, first "pout" vote)   # q16: closed, small, pushed-out lower lip (was a small open O that read sad)
    "PF-VisAA": dict(width=0.86, open=0.080, up=0.003, shape="A"),   # q16: 0.86 -> 0.98 (section judge at 3/4 vs Leo talking: "wider")
    "PF-VisOH": dict(width=0.46, open=0.042, up=0.010, shape="O"),
    "PF-VisEE": dict(width=0.98, open=0.065, corner=0.004, shape="E"),
    "PF-SmileOpenJaw": dict(width=0.95, open=0.068, corner=0.0, up=-0.002, shape="D"),
    "PF-JawOpen": dict(width=0.97, open=0.032, shape="A"),   # q15: the painted opening of the jaw drop (add_jaw_key moves the chin)
    "PF-VisWide": dict(width=0.92, open=0.074, corner=-0.006, up=0.010, shape="S"),   # q15: was a flat lens (A, 0.064): squarer, taller shout
}
_PROFILE = {"A": 0.9, "O": 0.5, "E": 0.8, "D": 1.2, "S": 0.75}   # q17: MHS3 bowl / lens shapes (TypeSafe mouth_open vs 5 MHS3 refs: p_same 0.19 -> 0.31)
MOUTH_SUPER = {}       # q17: superellipse exponent per shape (None = the old (1-u^2)^k profile)
MOUTH_OPEN_LINE = 0.6  # q17: how much the top line thins as the mouth opens (MHS3 open mouths: the interior is the edge)
MOUTH_LOWER_OPEN = 0.0 # q17: dark line along the bottom edge of an open mouth (MHS3: none; the pout lip arc is separate)
MOUTH_TOP_FLAT = 1.0   # q17: share of the closed line's downward curve removed when the mouth opens (MHS3: flat top edge)
MOUTH_D_BULGE = 0.0  # q17: the D shape's upward bulge of the top edge (H at open 0.044)   # q16: S 0.3 -> 0.45 (box-like square ends at 3/4)

MOUTH_EXPRESSIONS = {
    # q14b: the default brows slope down toward the nose (identity: BROW_INNER_DROP), so TypeSafe read the neutral face
    # and most presets as "angry"; every non-angry preset now lifts the inner brow ends (PF-BrowInnerUp)
    "smile": {"PF-SmileClosed": 1, "PF-BrowInnerUp_L": 0.6, "PF-BrowInnerUp_R": 0.6, "PF-BrowUp": 0.2},
    "happy": {"PF-EyeHappy": 1, "PF-BrowInnerUp_L": 0.7, "PF-BrowInnerUp_R": 0.7, "PF-BrowUp": 0.4, "PF-SmileOpenJaw": 1, "PF-JawOpen": 0.35},   # q15: + JawOpen (TypeSafe: smile/happy split -> happy both orders)
    "laugh": {"PF-Blink_L": 1, "PF-Blink_R": 1, "PF-BrowInnerUp_L": 0.8, "PF-BrowInnerUp_R": 0.8, "PF-BrowUp": 0.6, "PF-SmileOpenJaw": 1, "PF-VisAA": 0.2, "PF-JawOpen": 0.6},
    "amazed": {"PF-EyeWide": 1, "PF-BrowUp": 1, "PF-BrowInnerUp_L": 0.4, "PF-BrowInnerUp_R": 0.4, "PF-IrisSmall": 1, "PF-VisOH": 0.8, "PF-JawOpen": 0.5},
    "sad": {"PF-EyeSad": 1, "PF-BrowSad": 1, "PF-BrowInnerUp_L": 0.5, "PF-BrowInnerUp_R": 0.5, "PF-LookDown": 0.4, "PF-Frown": 1},
    "angry": {"PF-EyeAngry": 1, "PF-BrowAngry": 1, "PF-Frown": 0.6, "PF-NoseSneer": 0.5},
    "shout": {"PF-EyeAngry": 1, "PF-BrowAngry": 1, "PF-VisWide": 0.8, "PF-JawOpen": 0.7, "PF-NoseSneer": 0.4},
    "worried": {"PF-BrowInnerUp_L": 1, "PF-BrowInnerUp_R": 1, "PF-BrowSad": 0.5, "PF-EyeSad": 0.6, "PF-EyeWide": 0.3, "PF-Frown": 0.7, "PF-MouthNarrow": 0.4},
    "determined": {"PF-BrowAngry": 0.4, "PF-EyeAngry": 0.3, "PF-Smirk_L": 1, "PF-BrowRaise_R": 0.3, "PF-SmileClosed": 0.3},   # q15: + SmileClosed (determined both orders)
    "skeptical": {"PF-BrowRaise_L": 1, "PF-BrowLower_R": 1, "PF-Smirk_R": 0.8, "PF-LookRight": 0.3},
    "pout": {"PF-Pout": 1, "PF-Frown": 0.5, "PF-EyeAngry": 0.3, "PF-LookLeft": 0.4, "PF-BrowInnerUp_L": 0.5, "PF-BrowInnerUp_R": 0.5},   # q16: sulky, eyes aside
    "blink": {"PF-Blink_L": 1, "PF-Blink_R": 1, "PF-BrowInnerUp_L": 0.3, "PF-BrowInnerUp_R": 0.3},
    "talk_a": {"PF-VisAA": 0.6},
    "talk_o": {"PF-VisOH": 0.7},
    "talk_e": {"PF-VisEE": 0.8},
}


def mouth_shape(p):
    """Upper / lower edge of the mouth (H units) for one parameter set: arrays x, z_up, z_lo."""
    u = _mu()
    w = MOUTH_HW * MOUTH_LINE_W * p.get("width", 1.0)
    x = u * w
    z_up = MOUTH_Z + 0.004 - 0.010 * u ** 2                         # the closed line (as before)
    z_up = z_up + p.get("corner", 0.0) * np.abs(u) ** 3 + p.get("mid", 0.0) * (1 - u ** 2) + p.get("up", 0.0) * (1 - u ** 2)
    z_up = z_up + p.get("corner_l", 0.0) * np.clip(u, 0, 1) ** 3 + p.get("corner_r", 0.0) * np.clip(-u, 0, 1) ** 3
    z_up = z_up + p.get("flat", 0.0) * 0.010 * u ** 2                 # q16: 1 cancels the closed line's downward curve
    op = p.get("open", 0.0)
    prof = (1 - u ** 2) ** _PROFILE.get(p.get("shape", "A"), 0.6)
    n_sup = MOUTH_SUPER.get(p.get("shape", "A"))
    if n_sup:                                                        # q17: superellipse - blunt corners, round bottom (MHS3)
        prof = np.clip(1 - np.abs(u) ** n_sup, 0, 1) ** (1.0 / n_sup)
    if p.get("shape") == "D":                                        # open smile: flat top, round deep bottom
        z_up = z_up + MOUTH_D_BULGE * (1 - u ** 2) * (op / 0.044)
    if p.get("shape") != "S":                                        # q17: the shout keeps its downturned corners
        z_up = z_up + MOUTH_TOP_FLAT * 0.010 * u ** 2 * min(1.0, op / 0.03)
    dip = MOUTH_CORNER_DIP_D if p.get("shape") == "D" else MOUTH_CORNER_DIP      # q18b: smiles keep their corners up
    z_up = z_up - dip * np.abs(u) ** 6 * min(1.0, op / 0.03)
    z_lo = z_up - op * prof
    return x, z_up, z_lo


def build_mouth(ob, col, off_x, tag):
    tree = _bvh(ob)

    def _raw(x, z):
        best = None
        for dz in (0.0, -0.006, 0.006, -0.012, 0.012, -0.02, 0.02):
            loc, nrm, _, _ = tree.ray_cast(Vector((x * S, -1.0, O + (z + dz) * S)), Vector((0, 1, 0)))
            if loc is not None and (best is None or loc.y < best.y - 0.0015):
                best = loc
        return None if best is None else best.y

    # q15: one smoothed skin-depth field shared by every mouth layer. Per-point ray hits jumped between the lip groove
    # and the lip surface, so neighbouring samples (and the layers) crossed: jagged tongue and teeth edges.
    gx = np.arange(-0.20, 0.2001, 0.004); gz = np.arange(MOUTH_Z - 0.10, MOUTH_Z + 0.04, 0.004)
    G = np.full((len(gz), len(gx)), np.nan)
    for i, zz in enumerate(gz):
        for j, xx in enumerate(gx):
            y = _raw(xx, zz)
            if y is not None:
                G[i, j] = y
    ok = np.isfinite(G)
    if ok.any():
        G[~ok] = np.nanmax(G)
        for _ in range(3):
            Gp = np.pad(G, 1, mode="edge")
            G = np.minimum(G, sum(Gp[1 + di:1 + di + G.shape[0], 1 + dj:1 + dj + G.shape[1]] for di in (-1, 0, 1) for dj in (-1, 0, 1)) / 9.0)

    def on_skin(x, z, lift):
        if not ok.any():
            return None
        fi = np.clip((z - gz[0]) / 0.004, 0, len(gz) - 1.001); fj = np.clip((x - gx[0]) / 0.004, 0, len(gx) - 1.001)
        i0, j0 = int(fi), int(fj); ti, tj = fi - i0, fj - j0
        y = (G[i0, j0] * (1 - ti) * (1 - tj) + G[i0 + 1, j0] * ti * (1 - tj) + G[i0, j0 + 1] * (1 - ti) * tj + G[i0 + 1, j0 + 1] * ti * tj)
        return Vector((x * S, float(y), O + z * S)) + Vector((0, -1, 0)) * lift

    def on_skin_raw(x, z, lift):
        loc, _, _, _ = tree.ray_cast(Vector((x * S, -1.0, O + z * S)), Vector((0, 1, 0)))   # q20: one ray, no neighbour search
        y = None if loc is None else loc.y
        return None if y is None else Vector((x * S, float(y), O + z * S)) + Vector((0, -1, 0)) * lift

    def rows_of(top, bot, lift, raw=False):
        """top / bot: lists of (x, z) - one row per sample; a missing skin hit reuses the last good row."""
        rows, last = [], None
        f = on_skin_raw if raw else on_skin
        for (xa, za), (xb, zb) in zip(top, bot):
            a_, b_ = f(xa, za, lift), f(xb, zb, lift)
            if a_ is None or b_ is None:
                a_, b_ = last if last else (Vector((xa * S, -0.05, O + za * S)), Vector((xb * S, -0.05, O + zb * S)))
            rows.append((a_, b_)); last = (a_, b_)
        return rows

    def line_rows(x, z, width, lift, raw=False):
        top, bot = [], []
        for i in range(len(x)):
            j, k = min(i + 1, len(x) - 1), max(i - 1, 0)
            tx, tz = x[j] - x[k], z[j] - z[k]; L = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / L, tx / L
            top.append((x[i] - nx * width[i] / 2, z[i] - nz * width[i] / 2)); bot.append((x[i] + nx * width[i] / 2, z[i] + nz * width[i] / 2))
        return rows_of(top, bot, lift, raw)

    def pieces(p):
        x, zu, zl = mouth_shape(p)
        t = np.linspace(0, 1, MOUTH_N); s = np.sin(np.pi * t)
        gap = np.maximum(zu - zl, 0.0)
        out = {}
        thin = 1 - MOUTH_OPEN_LINE * min(1.0, p.get("open", 0.0) / 0.03)
        out["NewMouthLine"] = line_rows(x, zu, 0.006 * MOUTH_LINE * thin * (0.25 + 0.75 * s), MOUTH_LIFT["line"])
        out["NewMouthInside"] = rows_of(list(zip(x, zu)), list(zip(x, zl)), MOUTH_LIFT["inside"])
        uu = np.abs(_mu())
        # q15: smooth end taper (the hard cut at |u| 0.8 left white spikes at the band ends); the top sits just under the lip line
        th = np.minimum(MOUTH_TEETH_H, MOUTH_TEETH_CAP * gap) * np.clip(1 - (uu / MOUTH_TEETH_W) ** 2, 0, 1) ** MOUTH_TEETH_TAPER   # q16: rounded band ends
        tt0 = zu - np.minimum(0.0015, 0.2 * gap)
        out["NewMouthTeeth"] = rows_of(list(zip(x, tt0)), list(zip(x, tt0 - th)), MOUTH_LIFT["teeth"])
        ts = th * MOUTH_TEETH_SHADE                                    # q19: shaded lower part of the teeth (zero rows when off)
        out["NewMouthTeethShade"] = rows_of(list(zip(x, tt0 - th + ts)), list(zip(x, tt0 - th)), 0.5 * (MOUTH_LIFT["teeth"] + MOUTH_LIFT["lower"]))
        # q20: undershadow - the top of the interior under the teeth band is darker (the upper lip and teeth overhang it;
        # Kistler / Hogarth: the part under an overhang takes the deepest value). Zero rows when MOUTH_DEEP is 0.
        dp = MOUTH_DEEP * gap * np.clip(1 - (uu / 0.95) ** 2, 0, 1) ** 0.5
        deep_rows = (x, tt0 - th * 0.95, tt0 - th - dp)   # starts just under the teeth band (from mid-band it showed as a dark line through the teeth)                # finished after the throat (its bottom stays above the throat band)
        # q20: upper lip - a thin shade band over the top line (the upper lip's lower plane faces down, away from the light;
        # Buscema: the upper lip has its own plane and sits forward). Follows the top edge as the mouth opens.
        ul = 0.010 * UPPER_LIP_SHADE * np.clip(1 - (uu / 0.85) ** 2, 0, 1) ** 0.8 * (0.55 + 0.45 * (1 - np.exp(-((uu - 0.35) / 0.3) ** 2)))
        if UPPER_LIP_SHADE:
            out["NewUpperLip"] = rows_of(list(zip(x, zu + 0.6 * 0.006 * MOUTH_LINE * thin + ul)), list(zip(x, zu)), 0.5 * MOUTH_LIFT["inside"])
        uu_t = np.abs(_mu()) / MOUTH_TONGUE_W
        hump = np.sqrt(np.clip(1 - uu_t ** 2, 0, 1))                   # q18: a rounded hump in the middle (MHS3), not a band
        tg = np.minimum(MOUTH_TONGUE_H, MOUTH_TONGUE_CAP * gap) * hump
        # q18: the tongue sits inside the opening - the dark interior shows below and beside it
        tb = zl + np.minimum(0.0012, 0.15 * gap) + MOUTH_TONGUE_INSET * gap * hump
        if MOUTH_TONGUE_MODE == 1:                                     # q18b: bottom of the bowl filled up to a soft arc
            g0 = float(gap[MOUTH_N // 2]); z0 = float(zl[MOUTH_N // 2])
            tb = zl + np.minimum(0.0008, 0.10 * gap)
            ttop = z0 + g0 * (MOUTH_TONGUE_FRAC - MOUTH_TONGUE_DROOP * _mu() ** 2)
            ttop = np.minimum(ttop, zu - 0.35 * gap)                   # never over the teeth / upper interior
            tg = np.maximum(ttop - tb, 0.0)
        out["NewMouthTongue"] = rows_of(list(zip(x, tb + tg)), list(zip(x, tb)), MOUTH_LIFT["tongue"])
        # q19: throat band - the same arc raised by MOUTH_THROAT of the opening, under the tongue, over the dark interior
        g0_ = float(gap[MOUTH_N // 2])
        on_t = np.clip(tg / max(0.12 * g0_, 1e-6), 0, 1)              # only over the tongue (no red rim up the sides)
        thr = np.minimum(tb + tg + MOUTH_THROAT * g0_ * on_t, zu - 0.30 * gap)
        thr = np.maximum(thr, tb)
        out["NewMouthThroat"] = rows_of(list(zip(x, thr)), list(zip(x, tb)), MOUTH_LIFT["inside"] + 0.00015)
        if MOUTH_DEEP:                                                 # q20: no overlap with the throat (0.1 mm layers z-fight into blocks)
            dx_, dt_, db_ = deep_rows
            db_ = np.minimum(np.maximum(db_, thr + 0.0004), dt_)
            out["NewMouthDeep"] = rows_of(list(zip(dx_, dt_)), list(zip(dx_, db_)), MOUTH_LIFT["inside"] + 0.0003)
        lw = 0.0032 * MOUTH_LOWER_OPEN * np.clip(p.get("open", 0.0) / 0.02, 0, 1) * (0.2 + 0.8 * s)
        zlw = zl
        if p.get("lip"):                                               # q16: closed-mouth lower lip (pout): a short arc under the line
            lw = 0.0026 * np.clip(1 - (uu / 0.7) ** 2, 0, 1) ** 0.7
            zlw = float(zu[MOUTH_N // 2]) - p["lip"] * (0.35 + 0.65 * (1 - uu ** 2))   # a "u" under the line, deepest in the middle
        out["NewMouthLower"] = line_rows(x, zlw, lw, MOUTH_LIFT["lower"])
        # under-lip shadow: same lens as LIP_SHADOW (apply_look face_strokes), following the lower edge down
        ipd = 2 * EYE_X; wd, ht = LIP_SHADOW_W * ipd, 0.050 * ipd * LIP_SHADOW
        n = MOUTH_N; tt = np.linspace(-1, 1, n)
        drop = float(np.max(gap))
        fo = MOUTH_SHADOW_OPEN * min(1.0, drop / 0.06)
        sx = wd / 2 * tt * p.get("shadow_w", 1.0) * (1 - 0.35 * fo)
        sz = MOUTH_Z - 0.040 + p.get("shadow_up", 0.0) - drop * 0.9 + 0.016 * fo - 0.003 * (1 - tt ** 2)
        sw = ht * p.get("shadow_h", 1.0) * (0.1 + 0.9 * np.sin(np.pi * (tt + 1) / 2) ** 0.6)   # q16: pout raises a fuller, shorter lip shadow
        # q20: exact skin depth (the smoothed field takes the front-most neighbour, so in the hollow under the lower
        # lip the shadow floated in front of the skin and showed as a spike past the profile)
        out["NewLipShadow"] = line_rows(sx, sz, sw, 0.0006, raw=LIP_SHADOW_RAW)
        return out

    mats = {"NewMouthLine": _emission("MAT_PaintMouth_" + tag, (0.10, 0.025, 0.02, 1)),
            "NewMouthInside": _emission("MAT_MouthInside_" + tag, C_INSIDE),
            "NewMouthTeeth": _emission("MAT_MouthTeeth_" + tag, C_TEETH),
            "NewMouthTongue": _emission("MAT_MouthTongue_" + tag, C_TONGUE),
            "NewMouthThroat": _emission("MAT_MouthThroat_" + tag, C_THROAT),
            "NewMouthTeethShade": _emission("MAT_MouthTeethShade_" + tag, C_TEETH_SHADE),
            "NewMouthDeep": _emission("MAT_MouthDeep_" + tag, C_DEEP),
            "NewMouthLower": _emission("MAT_PaintMouth_" + tag, (0.10, 0.025, 0.02, 1))}
    old_shadow = col.objects.get("NewLipShadow_" + tag)
    mats["NewLipShadow"] = old_shadow.data.materials[0] if old_shadow and old_shadow.data.materials else mats["NewMouthInside"]
    mats["NewUpperLip"] = mats["NewLipShadow"]                         # q20: the same soft lens colour as the under-lip shadow
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


JAW_THETA = 0.10       # q15: PF-JawOpen hinge rotation (rad) of the skin below the mouth line


MOUTH_YAW_SHIFT = 0.0   # q16: off - TypeSafe recognition at 3/4 fell with 0.003 (determined 0.725 -> 0.43, happy 0.62 -> 0.59); was   # q16: m the mouth pieces move toward the far cheek at 3/4 (VW-Yaw keys; Leo 3/4: far / near half of the
                          # mouth from the nose tip 45 / 65 px, ours 35 / 75)


def add_mouth_view_keys(col, tag, shift=MOUTH_YAW_SHIFT):
    """q16: VW-Yaw_L / VW-Yaw_R on the mouth pieces and the lip shadow (set_view drives them by name with the head's)."""
    if not shift:
        return
    from mathutils.bvhtree import BVHTree
    head = col.objects.get("NEW_Head_" + tag)
    hk = head.data.shape_keys.key_blocks[0]
    HP = np.empty(len(hk.data) * 3, np.float32); hk.data.foreach_get("co", HP); HP = HP.reshape(-1, 3)
    tree = BVHTree.FromPolygons([tuple(v) for v in HP], [tuple(f.vertices) for f in head.data.polygons])

    def skin_y(p_):                                   # front-most skin within +-3 mm (the lip groove does not count)
        ys = [h[0].y for dz in (0.0, -0.0015, 0.0015, -0.003, 0.003)
              for h in [tree.ray_cast(Vector((float(p_[0]), -1.0, float(p_[2]) + dz)), Vector((0, 1, 0)))] if h[0] is not None]
        return min(ys) if ys else float(p_[1])
    for nm in ("NewMouthLine", "NewMouthInside", "NewMouthTeeth", "NewMouthTeethShade", "NewMouthTongue", "NewMouthThroat",
               "NewMouthLower", "NewLipShadow", "NewMouthDeep", "NewUpperLip"):
        o = col.objects.get(nm + "_" + tag)
        if o is None or not o.data.shape_keys:
            continue
        kb0 = o.data.shape_keys.key_blocks[0]
        P = np.empty(len(kb0.data) * 3, np.float32); kb0.data.foreach_get("co", P); P = P.reshape(-1, 3)
        for kname, sgn in (("VW-Yaw_L", -1.0), ("VW-Yaw_R", 1.0)):     # VW-Yaw_L is the camera on the character's left
            far = np.clip(sgn * P[:, 0], 0, None)                     # distance out on the far side
            Q = P.copy(); Q[:, 0] += sgn * shift * (1 - 0.7 * smooth(0.010, 0.026, far))   # the far corner stays inside the cheek line
            Q[:, 1] += np.array([skin_y(q) - skin_y(p_) for p_, q in zip(P, Q)])   # keep the height over the skin
            kb = o.shape_key_add(name=kname, from_mix=False); kb.value = 0.0
            kb.data.foreach_set("co", Q.ravel())


def add_jaw_key(col, tag, theta=JAW_THETA):
    """q15: PF-JawOpen on the head - the skin below the mouth line turns down and back about a hinge under the ear
    (0 at the mouth line and at the neck); the mouth strips carry the matching painted opening (MOUTH_KEYS)."""
    head = col.objects.get("NEW_Head_" + tag)
    if head is None or not head.data.shape_keys:
        return
    kb0 = head.data.shape_keys.key_blocks[0]
    P = np.empty(len(kb0.data) * 3, np.float32); kb0.data.foreach_get("co", P); P = P.reshape(-1, 3).astype(float)
    zh = (P[:, 2] - O) / S
    ra = np.hypot(P[:, 0] / S / 0.20, (P[:, 1] / S - NECK_Y) / (0.20 * 0.92))
    w = smooth(MOUTH_Z - 0.012, MOUTH_Z - 0.045, zh) * smooth(1.0, 1.3, ra) * smooth(0.05, -0.01, P[:, 1])
    hy, hz = 0.005, O + 0.33 * S
    a = theta * w
    dy, dz = P[:, 1] - hy, P[:, 2] - hz
    Q = P.copy()
    Q[:, 1] = hy + dy * np.cos(a) - dz * np.sin(a)
    Q[:, 2] = hz + dy * np.sin(a) + dz * np.cos(a)
    kb = head.shape_key_add(name="PF-JawOpen", from_mix=False); kb.value = 0.0
    kb.data.foreach_set("co", Q.astype(np.float32).ravel())
    print("q15 PF-JawOpen: %d verts, chin drop %.1f mm" % (int((w > 0.01).sum()), 1000 * (P[:, 2] - Q[:, 2]).max()))
    add_mouth_view_keys(col, tag)
    add_cheek_view_keys(col, tag)


CHEEK_VIEW_PUSH = 0.0     # q19: m the far cheek / jaw line moves out at 3/4 (VW-Yaw keys) so the mouth sits inside the face
CHEEK_X = (0.026, 0.050)  # q19: m from the centre line on the far side: no move inside (mouth / nose skin), full at the cheek edge
CHEEK_Z = (0.02, 0.12, 0.20, 0.50)   # q19: H above the chin: fade in, full band, fade out (chin tip and eye box stay)
CHEEK_SIL = 0.0           # q19: |normal . view| above which the skin stays (0 = off; e.g. 0.5 moves only near the outline)
CHEEK_SMOOTH = 0           # q19: neighbour-average passes over the push weight
CHEEK_Y = (0.04, 0.0)     # q19: m depth: full in front of y 0, nothing behind 0.04 (ear, back of the head)


def add_cheek_view_keys(col, tag, push=None):
    """q19: MHS3 3/4 frames keep the far mouth corner about 0.6 mouth widths inside the far cheek line (ours ~0.2: the
    corner met the jaw outline). The far cheek and jaw skin slide out in the camera's screen direction on the VW-Yaw
    keys, growing toward the silhouette, so the painted mouth and nose (which stay) end up well inside the face."""
    push = CHEEK_VIEW_PUSH if push is None else push
    if not push:
        return
    head = col.objects.get("NEW_Head_" + tag)
    ks = head.data.shape_keys if head is not None else None
    if ks is None:
        return
    P = np.empty(len(ks.key_blocks[0].data) * 3, np.float32); ks.key_blocks[0].data.foreach_get("co", P)
    P = P.reshape(-1, 3).astype(float)
    zh = (P[:, 2] - O) / S
    z0, z1, z2, z3 = CHEEK_Z
    wz = smooth(z0, z1, zh) * (1 - smooth(z2, z3, zh))
    wy = smooth(CHEEK_Y[0], CHEEK_Y[1], P[:, 1])
    th = math.radians(35.0)
    N = np.empty(len(head.data.vertices) * 3, np.float32); head.data.vertices.foreach_get("normal", N)
    N = N.reshape(-1, 3).astype(float)
    n = 0
    for kname, sgn in (("VW-Yaw_L", -1.0), ("VW-Yaw_R", 1.0)):    # VW-Yaw_L: camera on the character's left, far side -x
        kb = ks.key_blocks.get(kname)
        if kb is None:
            continue
        K = np.empty(len(kb.data) * 3, np.float32); kb.data.foreach_get("co", K); K = K.reshape(-1, 3).astype(float)
        far = np.clip(sgn * P[:, 0], 0, None)
        w = smooth(CHEEK_X[0], CHEEK_X[1], far) * wz * wy
        if CHEEK_SIL:                                              # q19: only skin near this view's silhouette moves (a
            v = np.array([-sgn * math.sin(th), -math.cos(th), 0.0])  # moved front-facing cheek showed as a lump at 20 deg)
            w = w * (1 - smooth(0.0, CHEEK_SIL, np.abs(N @ v)))
        if CHEEK_SMOOTH:                                           # q19: spread the weight over the mesh (single moved
            E = np.empty(len(head.data.edges) * 2, np.int64); head.data.edges.foreach_get("vertices", E)   # verts made thorns)
            E = E.reshape(-1, 2)
            deg = np.bincount(E.ravel(), minlength=len(w)).astype(float) + 1.0
            for _ in range(CHEEK_SMOOTH):
                acc = w.copy()
                np.add.at(acc, E[:, 0], w[E[:, 1]]); np.add.at(acc, E[:, 1], w[E[:, 0]])
                w = acc / deg
        # screen "away from the near side" for this camera: (-cos th, -sin th) mirrored by side
        d = np.stack([sgn * math.cos(th) * np.ones(len(P)), -math.sin(th) * np.ones(len(P)), np.zeros(len(P))], 1)
        K = K + push * w[:, None] * d
        kb.data.foreach_set("co", K.astype(np.float32).ravel())
        n = int((w > 0.01).sum())
    print("q19 cheek view keys: %d verts, push %.1f mm" % (n, push * 1000))


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


# q20: look_knobs.json "mouth" overrides any constant above (load_knobs stores them in MOUTH_OVR before this file runs)
for _k, _v in globals().get("MOUTH_OVR", {}).items():
    if _k in globals():
        globals()[_k] = _v
