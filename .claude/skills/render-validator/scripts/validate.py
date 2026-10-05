#!/usr/bin/env python3
"""Render validator: compares Blender renders to reference images and refuses to pass until the
renders AND an independent visual review both clear every criterion.

Only needs numpy + Pillow. Subcommands:
  init     create a validation workspace
  measure  score renders against references (objective metrics + hard gates), build a contact sheet
  gate     combine the latest measurement with a structured visual review and return PASS/ITERATE
  report   write report.md: iteration history, stages, failing checks, how far each render moved

Exit codes (same convention as Meshy's agent CLI checks): 0 pass, 12 a check FAILED (keep iterating),
13 UNKNOWN (something required was not measured, which is never a pass), 2 usage error.

Scope: this measures renders and the mesh stats you supply. A render cannot show topology flow, edge loops,
deformation or watertightness; mesh stats cover counts and health, and the independent review covers the rest.
"""
import argparse, hashlib, json, os, sys, time
import numpy as np
from PIL import Image, ImageDraw

SIZE = 256
EXIT_FAIL, EXIT_UNKNOWN, EXIT_USAGE = 12, 13, 2
DEFAULTS = {
    "require_mesh": False,
    "require_head": False,          # init --require-head: UNKNOWN until --head-audit is supplied
    "micro_change_px": 1.0,         # a failing view that moved less than this since last iteration was only tweaked          # init --require-mesh: measure reports UNKNOWN until mesh stats are supplied
    "mesh": {                       # mesh health gates. A key missing from the stats file is UNKNOWN, not a pass
        "tri_budget": [18000, 28000],   # nude base body, from docs/CLAUDE_BUILD_PROMPT.md
        "max_non_manifold_edges": 0,
        "max_zero_area_faces": 0,
        "max_loose_parts": 8,
        "max_ngon_share": 0.02,
    },
    "consistency_tolerance": 0.04,  # body views (front/three_quarter/side/back) must be the same height within this fraction
    "min_iterations": 3,            # gate refuses PASS before this many measured iterations
    "plateau_window": 3,            # iterations compared for plateau detection
    "plateau_delta": 0.02,          # min improvement of the margin score across the window
    "regression_eps": 0.03,         # a previously passing metric may not drop more than this
    "review_floor": 2,              # every review criterion must score >= this (0-3)
    "min_evidence_chars": 20,
    "floors": {                     # reference-based, per view with a reference. CALIBRATE on your own renders
        "sil_iou": 0.75,            # weak separator (margin about 0.03 on real heads), kept as a secondary check
        "edge_f": 0.60,             # perturbed copies >= 0.65 (even heavily blurred clay), different heads <= 0.54
        "palette": 0.60,            # separates style (clay vs toon 0.01-0.03), not shape
    },
    "ceilings": {                   # lower is better
        "contour_px": 7.0,          # perturbed copies <= 4.2, different heads >= 9.7 (normalised 256 px frame)
    },
    "hard": {                       # render-only gates, every view
        "coverage": [0.03, 0.90],
        "touches_border": False,
        "magenta_frac": 0.001,
        "shadow_chroma_min": 8.0,   # MHS3 refs 4-40, median 15; Lab chroma of the darkest quarter of the figure: warm, never grey
        "tone_levels": [3, 14],     # dominant luminance bands; MHS3 refs measure 5-14
        "hard_edge_ratio_min": 0.15,# MHS3 refs 0.18-0.57; share of shading transitions that are sharp steps, not smooth gradients
        "outline_ring_min": 0.15,
        "skin_shadow_chroma_min": 10.0,   # shadowed skin must stay saturated; all 14 measured MHS3 stills are >= 10.3, most 19+
        "skin_shadow_hue": [30, 75],      # orange-brown; MHS3 stills 35-69 degrees. Grey or green-ish shadow fails   # MHS3 refs 0.04-0.92; share of silhouette ring that is darker than the surface inside it
    },
}
REVIEW_CRITERIA = [
    "proportions_match_reference", "silhouette_reads_like_reference", "face_structure",
    "eyes_lash_highlights", "brows", "hair_clumps_and_tones", "shading_hard_warm_shadows",
    "outlines_thin_and_coloured", "colour_palette_match", "no_artifacts_or_melted_parts",
    "thumbnail_squint_test",
]

# ---------------------------------------------------------------- image helpers
def load(path):
    im = Image.open(path)
    im.load()
    return im

def rgb2lab(rgb):
    c = rgb.astype(np.float64) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

def shift_or(mask, r, op):
    h, w = mask.shape
    pad = np.pad(mask, r, constant_values=(op is np.logical_and))
    out = mask.copy() if op is np.logical_or else np.ones_like(mask)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out = op(out, pad[r + dy:r + dy + h, r + dx:r + dx + w])
    return out

def dilate(m, r): return shift_or(m, r, np.logical_or)
def erode(m, r): return shift_or(m, r, np.logical_and)

def background_rows(lab, strip=0.05, jump=10.0):
    """Background colour for every row, so flat colours AND vertical gradients (the creator's own backdrop) work.
    Takes the median of the left and right edge strips per row. Where the two disagree, or the value jumps
    from the row above, the figure is touching that edge (shoulders), so the previous row's colour is kept."""
    h, w, _ = lab.shape
    k = max(int(w * strip), 2)
    left = np.median(lab[:, :k], axis=1)
    right = np.median(lab[:, -k:], axis=1)
    out = np.zeros((h, 3))
    prev = (np.median(lab[:3, :k], axis=(0, 1)) + np.median(lab[:3, -k:], axis=(0, 1))) / 2
    for y in range(h):
        cand = left[y] if np.linalg.norm(left[y] - right[y]) < jump else None
        if cand is None:
            near = [c for c in (left[y], right[y]) if np.linalg.norm(c - prev) < jump]
            cand = near[0] if near else prev
        elif np.linalg.norm(cand - prev) >= jump:
            cand = prev
        out[y] = prev = cand
    return out

def foreground(im):
    """Return (rgb uint8, mask bool). Uses alpha if it carries information, else the border colour."""
    if im.mode in ("RGBA", "LA", "PA"):
        rgba = np.asarray(im.convert("RGBA"))
        if rgba[..., 3].min() < 250:
            return rgba[..., :3].copy(), rgba[..., 3] > 16
    rgb = np.asarray(im.convert("RGB"))
    lab = rgb2lab(rgb)
    bg = background_rows(lab)
    mask = np.linalg.norm(lab - bg[:, None, :], axis=-1) > 12
    mask = erode(dilate(mask, 2), 2)           # close pin-holes
    return rgb.copy(), mask

def normalise(im):
    """Crop to the figure, pad to square, resize. Returns rgb(SIZE,SIZE,3), mask(SIZE,SIZE), info."""
    rgb, mask = foreground(im)
    mask = dilate(erode(mask, 1), 1)            # drop stray pixels so one speck cannot stretch the crop
    ys, xs = np.where(mask)
    info = {"coverage": float(mask.mean()), "empty": ys.size == 0}
    if ys.size == 0:
        return np.full((SIZE, SIZE, 3), 255, np.uint8), np.zeros((SIZE, SIZE), bool), info
    info["touches_border"] = bool(mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any())
    info["aspect"] = float((xs.max() - xs.min() + 1) / (ys.max() - ys.min() + 1))
    info["bbox_h"] = int(ys.max() - ys.min() + 1); info["bbox_w"] = int(xs.max() - xs.min() + 1); info["img_h"] = int(mask.shape[0])
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgb, mask = rgb[y0:y1, x0:x1], mask[y0:y1, x0:x1]
    s = max(rgb.shape[:2])
    pr, pc = (s - rgb.shape[0]) // 2, (s - rgb.shape[1]) // 2
    canvas = np.full((s, s, 3), 255, np.uint8); mcanvas = np.zeros((s, s), bool)
    canvas[pr:pr + rgb.shape[0], pc:pc + rgb.shape[1]] = rgb
    mcanvas[pr:pr + rgb.shape[0], pc:pc + rgb.shape[1]] = mask
    t = int(SIZE * 0.92); off = (SIZE - t) // 2
    img = Image.fromarray(canvas).resize((t, t), Image.LANCZOS)
    msk = Image.fromarray((mcanvas * 255).astype(np.uint8)).resize((t, t), Image.BILINEAR)
    out = np.full((SIZE, SIZE, 3), 255, np.uint8); om = np.zeros((SIZE, SIZE), bool)
    out[off:off + t, off:off + t] = np.asarray(img); om[off:off + t, off:off + t] = np.asarray(msk) > 127
    return out, om, info

def gray(rgb): return rgb.astype(np.float64) @ np.array([0.299, 0.587, 0.114])

def gradmag(g):
    p = np.pad(g, 1, mode="edge")
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])
    return np.hypot(gx, gy)

def edges(rgb, mask):
    gm = gradmag(gray(rgb))
    e = (gm > 60) & dilate(mask, 2)
    return e

# ---------------------------------------------------------------- metrics
def sil_iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0

def edge_f(ea, eb, tol=3):
    """Tolerant edge F-score: edges match if within `tol` px of each other (robust to small offsets)."""
    if not ea.any() or not eb.any(): return 0.0
    prec = (ea & dilate(eb, tol)).sum() / ea.sum()
    rec = (eb & dilate(ea, tol)).sum() / eb.sum()
    return float(2 * prec * rec / (prec + rec)) if prec + rec else 0.0

def contour_px(ma, mb, cap=40):
    """Mean distance between the two silhouette outlines, in pixels of the normalised 256 frame (lower is better).
    Calibrated on real heads: perturbed copies of one image stay under 4.2 px, different heads start at 9.7 px.
    Far more discriminating than silhouette IoU, which separated the same sets by only about 0.03."""
    def contour(m): return m & ~erode(m, 1)
    ca, cb = contour(ma), contour(mb)
    if not ca.any() or not cb.any(): return float(cap)
    def dist(c):
        d = np.full(c.shape, float(cap)); d[c] = 0; seen = c.copy(); frontier = c.copy()
        for r in range(1, cap):
            nxt = dilate(frontier, 1) & ~seen
            if not nxt.any(): break
            d[nxt] = r; seen |= nxt; frontier = nxt
        return d
    return float((dist(cb)[ca].mean() + dist(ca)[cb].mean()) / 2)

def palette_sim(ra, ma, rb, mb):
    """Histogram intersection of figure pixels in coarse Lab bins. Tolerates pose and layout changes."""
    def hist(r, m):
        lab = rgb2lab(r[m])
        idx = np.clip(((lab - np.array([0, -64, -64])) / np.array([100 / 8, 128 / 8, 128 / 8])).astype(int), 0, 7)
        h = np.bincount(idx[:, 0] * 64 + idx[:, 1] * 8 + idx[:, 2], minlength=512).astype(float)
        return h / max(h.sum(), 1)
    if not ma.any() or not mb.any(): return 0.0
    return float(np.minimum(hist(ra, ma), hist(rb, mb)).sum())

def ssim_info(ra, rb):
    """Informational only (pose-sensitive). Global SSIM on 64px grayscale."""
    a = np.asarray(Image.fromarray(ra).convert("L").resize((64, 64)), np.float64)
    b = np.asarray(Image.fromarray(rb).convert("L").resize((64, 64)), np.float64)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    ma, mb, va, vb = a.mean(), b.mean(), a.var(), b.var()
    cov = ((a - ma) * (b - mb)).mean()
    return float(((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma ** 2 + mb ** 2 + c1) * (va + vb + c2)))

def skin_shadow(rgb, mask):
    """Colour of the shadowed skin, from skin-like pixels only (hue 25-95 deg, chroma > 8), so coats and fur
    cannot pollute it. Returns None when the view shows too little skin to judge.
    Real MHS3 stills (14 measured): shadow chroma 10-52 (mostly 19+), hue 35-69 deg, usually shifting toward red vs the lit skin."""
    lab = rgb2lab(rgb); L = lab[..., 0]
    hue = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])); ch = np.hypot(lab[..., 1], lab[..., 2])
    sk = mask & (hue > 25) & (hue < 95) & (ch > 8) & (L > 30) & (L < 92)
    if sk.sum() < 300: return None
    Ls = L[sk]
    dark = sk & (L <= np.percentile(Ls, 30)); lit = sk & (L >= np.percentile(Ls, 70))
    def col(k): return float(np.hypot(lab[k][:, 1], lab[k][:, 2]).mean()), float(np.degrees(np.arctan2(lab[k][:, 2].mean(), lab[k][:, 1].mean())))
    (dc, dh), (lc, lh) = col(dark), col(lit)
    return {"chroma": dc, "hue": dh, "hue_shift": dh - lh, "pixels": int(sk.sum())}

def toon_stats(rgb, mask):
    out = {}
    if mask.sum() < 50: return {"shadow_chroma": 0.0, "tone_levels": 0, "hard_edge_ratio": 0.0, "outline_ring": 0.0}
    lab = rgb2lab(rgb)
    L = lab[..., 0]
    fg = L[mask]
    dark = mask & (L <= np.percentile(fg, 25))
    out["shadow_chroma"] = float(np.hypot(lab[dark][:, 1], lab[dark][:, 2]).mean())
    hist, _ = np.histogram(fg, bins=20, range=(0, 100))
    share = hist / hist.sum()
    out["tone_levels"] = int((share > 0.04).sum())
    gm = gradmag(L)[erode(mask, 3)]
    trans = gm[gm > 4]
    out["hard_edge_ratio"] = float((trans > 40).sum() / max(trans.size, 1))
    ring = mask & ~erode(mask, 2)
    inner = erode(mask, 6)
    if ring.any() and inner.any():
        out["outline_ring"] = float((L[ring] < np.median(L[inner]) - 8).mean())
    else:
        out["outline_ring"] = 0.0
    return out

# ---------------------------------------------------------------- workspace
def _usage(msg):
    print(msg, file=sys.stderr)
    return EXIT_USAGE

def state_path(ws): return os.path.join(ws, "state.json")
def load_state(ws):
    with open(state_path(ws)) as f: return json.load(f)
def save_state(ws, st):
    with open(state_path(ws), "w") as f: json.dump(st, f, indent=2)

def parse_views(items):
    out = {}
    for it in items or []:
        name, _, path = it.partition("=")
        if not path: sys.exit(_usage(f"bad view '{it}', use name=path"))
        out[name] = path
    return out

def sha(paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        with open(p, "rb") as f: h.update(f.read())
    return h.hexdigest()[:16]

def cmd_init(a):
    os.makedirs(a.workspace, exist_ok=True)
    refs = parse_views(a.ref)
    for n, p in refs.items():
        if not os.path.exists(p): sys.exit(_usage(f"missing reference {p}"))
    cfg = json.loads(json.dumps(DEFAULTS))
    if a.config:
        with open(a.config) as f: user = json.load(f)
        for k, v in user.items():
            if isinstance(v, dict) and k in cfg: cfg[k].update(v)
            else: cfg[k] = v
    cfg["require_mesh"] = bool(a.require_mesh)
    cfg["require_head"] = bool(a.require_head)
    cfg["reviews_required"] = a.reviews
    cfg["required_views"] = list(a.require_view) if a.require_view else list(refs)
    save_state(a.workspace, {"refs": refs, "config": cfg, "iterations": [], "created": time.time()})
    print(f"workspace ready: {a.workspace}\nreferences: {', '.join(refs) or '(none, render-only gates)'}")

def check_mesh(stats, cfg, contract):
    """Returns (checks, unknown, orphans). Each check: {value, ok(True/False/None=unknown), limit}."""
    m = cfg["mesh"]; checks, unknown = {}, []
    def put(key, value, ok, limit):
        checks[key] = {"value": value, "ok": ok, "limit": limit}
        if ok is None: unknown.append(f"mesh:{key}")
    tris = stats.get("tris")
    lo, hi = m["tri_budget"]
    put("tris", tris, None if tris is None else lo <= tris <= hi, [lo, hi])
    for key, limit_key in (("non_manifold_edges", "max_non_manifold_edges"), ("zero_area_faces", "max_zero_area_faces"),
                           ("loose_parts", "max_loose_parts"), ("ngon_share", "max_ngon_share")):
        v = stats.get(key)
        put(key, v, None if v is None else v <= m[limit_key], m[limit_key])
    orphans = []
    if contract:
        known = set(contract.get("identity_shape_keys", [])) | set(contract.get("performance_shape_keys", [])) | set(contract.get("sockets", []))
        for name in stats.get("shape_keys", []) + stats.get("sockets", []):
            if name.startswith(("ID-", "PF-", "SOC-")) and name not in known: orphans.append(name)
        implemented = [n for n in stats.get("shape_keys", []) if n in known]
        checks["contract_keys_implemented"] = {"value": len(implemented), "ok": True, "limit": f"of {len(known)} the app reads"}
    return checks, unknown, orphans

def margin_score(per_view):
    """Smallest normalised margin across all checked metrics. >=0 means every floor is cleared."""
    ms = [m["margin"] for v in per_view.values() for m in v["checks"].values() if m["margin"] is not None]
    return min(ms) if ms else -1.0

def cmd_measure(a):
    st = load_state(a.workspace); cfg = st["config"]
    views = parse_views(a.view)
    if not views: sys.exit(_usage("give at least one --view name=render.png"))
    for p in views.values():
        if not os.path.exists(p): sys.exit(_usage(f"missing render {p}"))
    h = sha(views.values())
    its = st["iterations"]
    if its and its[-1]["render_hash"] == h:
        print("NO_CHANGE: these renders are byte-identical to the previous iteration. Change the model, then re-render.")
        sys.exit(EXIT_FAIL)
    n = len(its) + 1
    idir = os.path.join(a.workspace, f"iter_{n:02d}"); os.makedirs(idir, exist_ok=True)
    per_view, tiles = {}, []
    for name, path in views.items():
        rgb, mask, info = normalise(load(path))
        checks = {}
        def add(key, val, ok, floor, kind, margin):
            checks[key] = {"value": round(val, 4) if isinstance(val, float) else val, "ok": bool(ok), "limit": floor, "kind": kind,
                           "margin": None if margin is None else round(float(margin), 4)}
        hd = cfg["hard"]
        lo, hi = hd["coverage"]
        add("coverage", info["coverage"], lo <= info["coverage"] <= hi, [lo, hi], "hard", min(info["coverage"] - lo, hi - info["coverage"]) / max(lo, 1e-6))
        if info.get("empty"): add("empty_render", True, False, "figure must be visible", "hard", -1)
        tb = bool(info.get("touches_border", True))
        add("touches_border", tb, not tb, "figure must not be clipped", "hard", -1 if tb else 0)
        raw = np.asarray(load(path).convert("RGB")).astype(int)
        mag = float(((raw[..., 0] > 240) & (raw[..., 1] < 20) & (raw[..., 2] > 240)).mean())
        add("magenta_frac", mag, mag <= hd["magenta_frac"], hd["magenta_frac"], "hard", (hd["magenta_frac"] - mag) / max(hd["magenta_frac"], 1e-6))
        ts = toon_stats(rgb, mask)
        add("shadow_chroma", ts["shadow_chroma"], ts["shadow_chroma"] >= hd["shadow_chroma_min"], hd["shadow_chroma_min"], "toon", (ts["shadow_chroma"] - hd["shadow_chroma_min"]) / hd["shadow_chroma_min"])
        lo, hi = hd["tone_levels"]
        add("tone_levels", ts["tone_levels"], lo <= ts["tone_levels"] <= hi, [lo, hi], "toon", min(ts["tone_levels"] - lo, hi - ts["tone_levels"]) / max(hi - lo, 1) )
        add("hard_edge_ratio", ts["hard_edge_ratio"], ts["hard_edge_ratio"] >= hd["hard_edge_ratio_min"], hd["hard_edge_ratio_min"], "toon", (ts["hard_edge_ratio"] - hd["hard_edge_ratio_min"]) / hd["hard_edge_ratio_min"])
        add("outline_ring", ts["outline_ring"], ts["outline_ring"] >= hd["outline_ring_min"], hd["outline_ring_min"], "toon", (ts["outline_ring"] - hd["outline_ring_min"]) / hd["outline_ring_min"])
        ss = skin_shadow(rgb, mask)
        if ss is not None:
            smin = hd["skin_shadow_chroma_min"]; hlo, hhi = hd["skin_shadow_hue"]
            add("skin_shadow_chroma", ss["chroma"], ss["chroma"] >= smin, smin, "toon", (ss["chroma"] - smin) / smin)
            add("skin_shadow_hue", ss["hue"], hlo <= ss["hue"] <= hhi, [hlo, hhi], "toon", min(ss["hue"] - hlo, hhi - ss["hue"]) / (hhi - hlo))
        ref_tile = None
        if name in st["refs"]:
            rr, rm, rinfo = normalise(load(st["refs"][name]))
            fl = cfg["floors"]
            iou = sil_iou(mask, rm); ef = edge_f(edges(rgb, mask), edges(rr, rm)); pal = palette_sim(rgb, mask, rr, rm)
            for key, val in (("sil_iou", iou), ("edge_f", ef), ("palette", pal)):
                add(key, val, val >= fl[key], fl[key], "reference", (val - fl[key]) / fl[key])
            cp = contour_px(mask, rm); ceil = cfg["ceilings"]["contour_px"]
            add("contour_px", cp, cp <= ceil, ceil, "reference", (ceil - cp) / ceil)
            per_view_ssim = ssim_info(rgb, rr)
            ref_tile = (rr, rm)
        else:
            per_view_ssim = None
        change = None
        prev_mask = os.path.join(a.workspace, f"iter_{n - 1:02d}", f"mask_{name}.png") if n > 1 else None
        if prev_mask and os.path.exists(prev_mask):
            change = round(contour_px(mask, np.asarray(Image.open(prev_mask)) > 127), 2)
        Image.fromarray((mask * 255).astype(np.uint8)).save(os.path.join(idir, f"mask_{name}.png"))
        per_view[name] = {"checks": checks, "ssim_info_only": per_view_ssim, "aspect": info.get("aspect"), "change_px": change,
                          "skin_shadow": ss, "bbox_h_frac": (info["bbox_h"] / info["img_h"]) if info.get("bbox_h") else None}
        tiles.append((name, rgb, mask, ref_tile))
    body = [v for v in per_view if v in ("front", "three_quarter", "side", "back") and per_view[v]["bbox_h_frac"]]
    if len(body) > 1:
        hs = [per_view[v]["bbox_h_frac"] for v in body]; mean = sum(hs) / len(hs); tol = cfg["consistency_tolerance"]
        for v, h in zip(body, hs):
            dev = abs(h - mean) / mean
            per_view[v]["checks"]["height_consistency"] = {"value": round(dev, 4), "ok": dev <= tol, "limit": tol, "kind": "consistency", "margin": round((tol - dev) / tol, 4)}
    failing = [f"{v}:{k}" for v, d in per_view.items() for k, c in d["checks"].items() if not c["ok"]]
    score = margin_score(per_view)
    unknown = [f"view:{v}" for v in cfg.get("required_views", []) if v not in views]
    mesh_checks, orphans = None, []
    if a.mesh_stats:
        with open(a.mesh_stats) as fh: stats = json.load(fh)
        contract = None
        if a.contract:
            with open(a.contract) as fh: contract = json.load(fh)
        mesh_checks, mu, orphans = check_mesh(stats, cfg, contract)
        unknown += mu
        failing += [f"mesh:{k}" for k, c in mesh_checks.items() if c["ok"] is False]
    elif cfg.get("require_mesh"):
        unknown.append("mesh:not supplied")
    head = None
    if a.head_audit:
        with open(a.head_audit) as fh: head = json.load(fh)
        if not head.get("ok"): failing.append("head:shape (" + "; ".join(head.get("bad", [])[:3]) + ")")
    elif cfg.get("require_head"):
        unknown.append("head:audit not supplied")
    rec = {"n": n, "render_hash": h, "views": per_view, "failing": failing, "unknown": unknown, "margin_score": round(score, 4),
           "time": time.time(), "renders": views, "stage": a.stage, "mesh": mesh_checks, "orphan_names": orphans,
           "mesh_stats_hash": sha([a.mesh_stats]) if a.mesh_stats else None, "head_audit": head}
    its.append(rec); save_state(a.workspace, st)
    sheet = build_sheet(tiles)
    sheet_path = os.path.join(idir, "sheet.png"); sheet.save(sheet_path)
    with open(os.path.join(idir, "metrics.json"), "w") as f: json.dump(rec, f, indent=2)
    # regression and plateau
    notes = []
    if n > 1:
        best = max(i["margin_score"] for i in its[:-1])
        prev = its[-2]
        for v, d in per_view.items():
            for k, c in d["checks"].items():
                pc = prev["views"].get(v, {}).get("checks", {}).get(k)
                if pc and pc["ok"] and not c["ok"]:
                    notes.append(f"REGRESSION: {v}:{k} passed last iteration and fails now. Revert or fix before anything else.")
        if score < best - cfg["regression_eps"]:
            notes.append(f"WORSE than best iteration (margin {score:.3f} vs best {best:.3f}). Consider reverting to iteration {max(its[:-1], key=lambda i: i['margin_score'])['n']}.")
    w = cfg["plateau_window"]
    if n >= w + 1:
        recent = [i["margin_score"] for i in its[-w:]]
        if max(recent) - its[-w - 1]["margin_score"] < cfg["plateau_delta"] and score < 0:
            notes.append(f"PLATEAU: no meaningful gain in {w} iterations. Revert to best, narrow scope to ONE failing criterion, change strategy (different technique, not a bigger tweak), or ask the human.")
    print(f"iteration {n}  stage {a.stage or '-'}  render_hash {h}")
    print(f"contact sheet: {sheet_path}   (left to right per view: reference | render | edge overlay red=ref cyan=render | silhouette diff)")
    for v, d in per_view.items():
        ch = d.get("change_px")
        if ch is not None and ch < cfg["micro_change_px"] and any(not c["ok"] for c in d["checks"].values()):
            notes.append(f"MICRO-CHANGE: [{v}] moved only {ch} px since the last iteration and still fails. That was a tweak, not a fix. Take the biggest named defect and change the form.")
    for v, d in per_view.items():
        line = "  ".join(f"{k}={c['value']}{'' if c['ok'] else ' <FAIL'}" for k, c in d["checks"].items())
        print(f"[{v}] {line}")
    for t in notes: print(t)
    if mesh_checks:
        print("[mesh] " + "  ".join(f"{k}={c['value']}{'' if c['ok'] is True else (' <FAIL' if c['ok'] is False else ' <UNKNOWN')}" for k, c in mesh_checks.items()))
    if orphans:
        print(f"WARNING: {len(orphans)} ID-/PF-/SOC- names are not in the app contract and will do nothing there: " + ", ".join(orphans[:8]) + (" ..." if len(orphans) > 8 else ""))
    print("SCOPE: renders and supplied mesh stats only. This cannot see edge-loop flow, deformation or hand detail.")
    if failing:
        print("MEASURE_FAIL: " + ", ".join(failing))
        print("Look at the sheet, name each defect in plain words, fix the model, re-render, run measure again.")
        sys.exit(EXIT_FAIL)
    if unknown:
        print("MEASURE_UNKNOWN: not measured, so not a pass: " + ", ".join(unknown))
        sys.exit(EXIT_UNKNOWN)
    print("MEASURE_OK: objective gates pass. Now run the visual review (see SKILL.md), then `gate`.")

def build_sheet(tiles):
    rows = []
    for name, rgb, mask, ref in tiles:
        if ref is None:
            ref_img = np.full_like(rgb, 235); em = np.zeros_like(rgb); diff = np.zeros_like(rgb) + 235
            overlay = np.full_like(rgb, 255)
        else:
            rr, rm = ref
            ref_img = rr
            er, eg = edges(rr, rm), edges(rgb, mask)
            overlay = np.full_like(rgb, 255)
            overlay[er] = (230, 40, 40); overlay[eg] = (30, 190, 220); overlay[er & eg] = (20, 20, 20)
            diff = np.full_like(rgb, 255)
            diff[rm & mask] = (190, 190, 190); diff[rm & ~mask] = (230, 40, 40); diff[~rm & mask] = (30, 190, 220)
        row = np.concatenate([ref_img, rgb, overlay, diff], axis=1)
        im = Image.fromarray(row); d = ImageDraw.Draw(im); d.text((4, 4), name, fill=(0, 0, 0))
        rows.append(np.asarray(im))
    return Image.fromarray(np.concatenate(rows, axis=0))

def review_problems(rev, last, cfg, n_iters, tag=""):
    """Everything wrong with one review file. `tag` prefixes messages when several reviews are combined."""
    why = []
    if rev.get("render_hash") != last["render_hash"]:
        why.append(f"{tag}review is not bound to the latest renders (needs render_hash {last['render_hash']}). Review the current sheet.")
    if rev.get("reviewer") != "independent":
        why.append(f'{tag}review must come from an independent reviewer (reviewer: "independent"), not the model author. Spawn a reviewer agent that has not seen your reasoning.')
    crit = rev.get("criteria", {})
    low = []
    for c in REVIEW_CRITERIA:
        e = crit.get(c)
        if not e: why.append(f"{tag}review missing criterion '{c}'"); continue
        if e.get("score", 0) < cfg["review_floor"]: low.append(f"{c}={e.get('score')}")
        if len(str(e.get("evidence", "")).strip()) < cfg["min_evidence_chars"]:
            why.append(f"{tag}criterion '{c}' needs a concrete visual evidence sentence")
    ev = [" ".join(str(e.get("evidence", "")).lower().split()) for e in crit.values() if e]
    if len(set(ev)) < len(ev): why.append(f"{tag}evidence repeats between criteria. Each criterion needs its own observation of the sheet.")
    if any(len(x.split()) < 6 for x in ev): why.append(f"{tag}evidence is too short: write what is visible (6+ words), not a verdict.")
    scores = {e.get("score") for e in crit.values() if e}
    if len(crit) >= len(REVIEW_CRITERIA) and len(scores) == 1: why.append(f"{tag}every criterion has the same score. Score the weakest area honestly; a uniform review is a rubber stamp.")
    if low: why.append(f"{tag}criteria below floor: " + ", ".join(low) + ". Each needs a named defect and a targeted fix.")
    if n_iters > 1 and not rev.get("defects_fixed_since_last"):
        why.append(f"{tag}list defects_fixed_since_last: every iteration must be tied to a named defect.")
    return why

def cmd_gate(a):
    st = load_state(a.workspace); cfg = st["config"]; its = st["iterations"]
    if not its: print("ITERATE: nothing measured yet. Run measure first."); sys.exit(EXIT_FAIL)
    last = its[-1]; why = []
    if last.get("unknown"):
        print("UNKNOWN: required checks were not measured, which is never a pass: " + ", ".join(last["unknown"]))
        print("Supply the missing views or mesh stats, run measure again, then gate.")
        sys.exit(EXIT_UNKNOWN)
    if last["failing"]: why.append("objective gates still failing: " + ", ".join(last["failing"]))
    if len(its) < cfg["min_iterations"]:
        why.append(f"only {len(its)} measured iteration(s); at least {cfg['min_iterations']} are required. A first draft is never final.")
    revs = []
    for path in a.review:
        try:
            with open(path) as f: revs.append(json.load(f))
        except Exception as e:
            print(f"ITERATE: cannot read review file {path} ({e}). Create it as described in SKILL.md."); sys.exit(EXIT_FAIL)
    need = cfg.get("reviews_required", 1)
    if len(revs) < need:
        why.append(f"this workspace needs {need} independent reviews, got {len(revs)}. Use one reviewer per --review, each with its own reviewer_id.")
    for i, rev in enumerate(revs):
        why += review_problems(rev, last, cfg, len(its), tag=f"[review {i + 1}] " if len(revs) > 1 else "")
    if len(revs) > 1:
        ids = [r.get("reviewer_id") for r in revs]
        if any(not x for x in ids) or len(set(ids)) < len(ids):
            why.append("with several reviews every one needs a distinct reviewer_id, so one reviewer cannot be counted twice.")
        for c in REVIEW_CRITERIA:
            sc = [r.get("criteria", {}).get(c, {}).get("score") for r in revs]
            sc = [x for x in sc if isinstance(x, (int, float))]
            if len(sc) > 1 and max(sc) - min(sc) >= 2:
                why.append(f"reviewers disagree on '{c}' ({min(sc)} vs {max(sc)}). Re-examine the sheet for that criterion before gating again.")
    if why:
        print("ITERATE")
        for w in why: print(" - " + w)
        sys.exit(EXIT_FAIL)
    print(f"PASS after {len(its)} iterations with {len(revs)} independent review(s) (final render_hash {last['render_hash']}). Show the user the final sheet.")

def cmd_report(a):
    st = load_state(a.workspace); its = st["iterations"]
    lines = [f"# Validation report: {os.path.basename(os.path.abspath(a.workspace))}", "",
             f"{len(its)} iterations. Required views: {', '.join(st['config'].get('required_views', [])) or '-'}.", "",
             "| # | stage | failing | unknown | margin | contour px (per view) | moved px |", "|---|---|---|---|---|---|---|"]
    for r in its:
        cp = ", ".join(f"{v}:{d['checks']['contour_px']['value']}" for v, d in r["views"].items() if "contour_px" in d["checks"]) or "-"
        mv = ", ".join(f"{v}:{d['change_px']}" for v, d in r["views"].items() if d.get("change_px") is not None) or "-"
        lines.append(f"| {r['n']} | {r.get('stage') or '-'} | {len(r['failing'])} | {len(r.get('unknown', []))} | {r['margin_score']} | {cp} | {mv} |")
    if its:
        last = its[-1]
        lines += ["", "## Latest", f"- failing: {', '.join(last['failing']) or 'none'}", f"- unknown: {', '.join(last.get('unknown', [])) or 'none'}",
                  f"- orphan contract names: {', '.join(last.get('orphan_names', [])) or 'none'}", f"- render hash: {last['render_hash']}"]
        best = max(its, key=lambda r: r["margin_score"]); lines.append(f"- best iteration so far: {best['n']} (margin {best['margin_score']})")
    lines += ["", "Scope: renders and supplied stats only. Edge-loop flow, deformation and hand detail are not measured."]
    out = os.path.join(a.workspace, "report.md")
    with open(out, "w") as f: f.write("\n".join(lines) + "\n")
    print("\n".join(lines)); print(f"\nwritten to {out}")

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    i = sp.add_parser("init"); i.add_argument("workspace"); i.add_argument("--ref", action="append", help="view=reference.png (repeatable)"); i.add_argument("--config"); i.add_argument("--require-mesh", action="store_true", help="UNKNOWN until --mesh-stats is supplied"); i.add_argument("--require-head", action="store_true", help="UNKNOWN until --head-audit is supplied"); i.add_argument("--reviews", type=int, default=1, help="independent reviews the gate requires (2 is recommended for a final pass)"); i.add_argument("--require-view", action="append", help="view that must be measured (default: every reference)")
    m = sp.add_parser("measure"); m.add_argument("workspace"); m.add_argument("--view", action="append", help="view=render.png (repeatable)"); m.add_argument("--stage", help="pipeline stage tag for lineage, e.g. blockout, head, shading"); m.add_argument("--mesh-stats", help="JSON from mesh_stats.py"); m.add_argument("--head-audit", help="head_audit.json written by head-shape-audit/scripts/head_audit.py"); m.add_argument("--contract", help="knowledge/expected-contract.json, to flag names the app does not read")
    r = sp.add_parser("report"); r.add_argument("workspace")
    g = sp.add_parser("gate"); g.add_argument("workspace"); g.add_argument("--review", required=True, action="append", help="review JSON, repeat for several reviewers (each needs a distinct reviewer_id)")
    a = p.parse_args()
    {"init": cmd_init, "measure": cmd_measure, "gate": cmd_gate, "report": cmd_report}[a.cmd](a)

if __name__ == "__main__":
    main()
