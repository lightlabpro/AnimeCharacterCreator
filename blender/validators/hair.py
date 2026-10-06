"""Hair validators, numpy only.

Targets come from the anime-character-modeling skill (measured on Hina and Amshani and on MHS3 frames), the
shading guide and the build prompt:
  - many chunky, closed clumps, not a few fat tubes and not fine strands or flat ribbons
  - clump cross-section thickness / width about 0.64 on Hina; a short cut needs 20+ clumps and thickness / width >= 0.45
  - clump width about 0.4 of the head height on Hina
  - sharp, pointed clump tips (tapered), one UV island per clump, islands taller than wide
  - hair sits on the skull (not inside it), covers the cranium, and leaves the ears visible when asked to
Heuristics that are not from those sources are labelled.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .model import FAIL, INFO, PASS, SKIP, WARN, Finding
from .spec import Band


def components(faces: Sequence[Sequence[int]], n: int) -> List[np.ndarray]:
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for f in faces:
        r = find(f[0])
        for w in f[1:]:
            parent[find(w)] = r
    groups: Dict[int, set] = {}
    for f in faces:
        groups.setdefault(find(f[0]), set()).update(f)
    return [np.array(sorted(s)) for s in groups.values()]


def _boundary_edges(faces: Sequence[Sequence[int]]) -> Dict[int, int]:
    """Boundary edge count per clump root is cheap to get per component below; here per mesh edge counts."""
    count: Dict[Tuple[int, int], int] = {}
    for f in faces:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            e = (a, b) if a < b else (b, a)
            count[e] = count.get(e, 0) + 1
    return count


def clump_stats(v: np.ndarray, faces: Sequence[Sequence[int]], min_verts: int = 8) -> List[Dict[str, float]]:
    """One dict per clump (connected component). Dimensions come from the principal axes of its vertices:
    length = longest axis, width = middle, thickness = shortest."""
    v = np.asarray(v, float)
    edge_count = _boundary_edges(faces)
    vert_boundary = set()
    for (a, b), c in edge_count.items():
        if c == 1:
            vert_boundary.update((a, b))
    out = []
    for comp in components(faces, len(v)):
        if len(comp) < min_verts:
            continue
        p = v[comp]
        c = p - p.mean(axis=0)
        w, vec = np.linalg.eigh(np.cov(c.T))
        order = np.argsort(w)[::-1]
        proj = c @ vec[:, order]
        ext = proj.max(axis=0) - proj.min(axis=0)
        L, W, T = float(ext[0]), float(ext[1]), float(ext[2])
        # taper: cross-section width (axis 2 extent) in the first and last 15% along the length
        t = proj[:, 0]
        lo, hi = t.min(), t.max()
        ends = []
        for sel in (t <= lo + 0.15 * (hi - lo), t >= hi - 0.15 * (hi - lo)):
            q = proj[sel]
            ends.append(float(q[:, 1].max() - q[:, 1].min()) if len(q) >= 2 else 0.0)
        root, tip = max(ends), min(ends)
        out.append({"verts": float(len(comp)), "length": L, "width": W, "thickness": T,
                    "thick_over_width": T / W if W > 1e-9 else 0.0,
                    "tip_over_root": tip / root if root > 1e-9 else 1.0,
                    "tube_like": float(not any((lo + 0.15 * (hi - lo)) < proj[k, 0] < (hi - 0.15 * (hi - lo))
                                               for k, i in enumerate(comp) if i in vert_boundary)),
                    "z_min": float(p[:, 2].min()), "z_max": float(p[:, 2].max()),
                    "centroid": p.mean(axis=0).tolist()})
    return out


def summarise(clumps: List[Dict[str, float]], head_h: float) -> Dict[str, float]:
    if not clumps:
        return {"clump_count": 0.0}
    g = lambda k: np.array([c[k] for c in clumps])
    return {
        "clump_count": float(len(clumps)),
        "median_verts": float(np.median(g("verts"))),
        "median_thick_over_width": float(np.median(g("thick_over_width"))),
        "median_width_over_head": float(np.median(g("width")) / head_h),
        "median_length_over_head": float(np.median(g("length")) / head_h),
        "tip_over_root_median": float(np.median(g("tip_over_root"))),
        "pointed_fraction": float((g("tip_over_root") <= 0.7).mean()),
        "tube_fraction": float(g("tube_like").mean()),
    }


def length_bucket(hair_min_z: float, crown_z: float, head_h: float) -> str:
    below = (crown_z - hair_min_z) / head_h  # heads below the crown
    return ("above the chin (crop or short)" if below <= 1.0 else "chin length (bob)" if below <= 1.35 else
            "shoulder length" if below <= 2.1 else "mid-back" if below <= 3.3 else "waist or longer")


def vertex_normals(v: np.ndarray, faces: Sequence[Sequence[int]]) -> np.ndarray:
    n = np.zeros_like(v)
    for f in faces:
        p = v[list(f)]
        fn = sum(np.cross(p[k], p[(k + 1) % len(p)]) for k in range(len(p)))
        for i in f:
            n[i] += fn
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.where(ln == 0, 1, ln)


def head_fit(hair_v: np.ndarray, body_v: np.ndarray, body_faces: Sequence[Sequence[int]], chin_z: float, crown_z: float,
             ear_clear: bool = False) -> Dict[str, float]:
    """Hair against the head. A hair vertex is 'inside the skull' when it lies more than 3% of the head height behind
    the nearest head surface vertex, measured along that vertex's outward normal (signed distance)."""
    head_h = crown_z - chin_z
    nrm = vertex_normals(body_v, body_faces)
    keep = np.nonzero(body_v[:, 2] >= chin_z)[0]
    skull, sn = body_v[keep], nrm[keep]
    # Some meshes (Hina's body) have inward-facing normals; orient them outward from the head centre first.
    if (((skull - skull.mean(axis=0)) * sn).sum(axis=1).mean()) < 0:
        sn = -sn
    hv = hair_v[hair_v[:, 2] >= chin_z]
    inside = 0
    for i in range(0, len(hv), 400):
        d = hv[i:i + 400, None, :] - skull[None, :, :]
        j = (d ** 2).sum(-1).argmin(axis=1)
        signed = ((hv[i:i + 400] - skull[j]) * sn[j]).sum(axis=1)
        near = np.linalg.norm(hv[i:i + 400] - skull[j], axis=1) < 0.25 * head_h  # only hair near the head counts
        inside += int(((signed < -0.03 * head_h) & near).sum())
    res = {"inside_skull_fraction": float(inside / max(len(hv), 1))}
    cap = skull[(skull[:, 2] >= chin_z + 0.62 * head_h)]
    sub = hair_v[::max(1, len(hair_v) // 4000)]
    res["cranium_coverage"] = float((np.sqrt(((cap[:, None, :] - sub[None]) ** 2).sum(-1)).min(axis=1) <= 0.12 * head_h).mean()) if len(cap) else 0.0
    band = skull[(skull[:, 2] >= chin_z + 0.30 * head_h) & (skull[:, 2] <= chin_z + 0.62 * head_h)]
    if len(band):
        xmax = np.abs(band[:, 0]).max()
        ears = band[np.abs(band[:, 0]) >= 0.93 * xmax]
        res["ear_covered_fraction"] = float((np.sqrt(((ears[:, None, :] - sub[None]) ** 2).sum(-1)).min(axis=1) <= 0.03 * head_h).mean())
    res["ear_clear_required"] = float(ear_clear)
    return res


def uv_islands(faces: Sequence[Sequence[int]], uv_per_face: Sequence[Sequence[Tuple[float, float]]]) -> List[Tuple[float, float]]:
    """Islands of faces that share UV points. Returns (width, height) of each island's UV bounding box."""
    key = lambda p: (round(p[0], 5), round(p[1], 5))
    parent = list(range(len(faces)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    first: Dict[Tuple[float, float], int] = {}
    for i, uvs in enumerate(uv_per_face):
        for p in uvs:
            k = key(p)
            if k in first:
                parent[find(i)] = find(first[k])
            else:
                first[k] = i
    boxes: Dict[int, List[float]] = {}
    for i, uvs in enumerate(uv_per_face):
        r = find(i)
        b = boxes.setdefault(r, [9e9, 9e9, -9e9, -9e9])
        for p in uvs:
            b[0], b[1], b[2], b[3] = min(b[0], p[0]), min(b[1], p[1]), max(b[2], p[0]), max(b[3], p[1])
    return [(b[2] - b[0], b[3] - b[1]) for b in boxes.values()]


# ---- findings ---------------------------------------------------------------------------------------------

BANDS = {
    "clump_count_short": Band(20, 400, 5),
    "thick_over_width": Band(0.45, 1.05, 0.1),   # a round tube is 1.0, the chunkiest clump
    "width_over_head": Band(0.25, 0.55, 0.1),
    "inside_skull": Band(0.0, 0.15, 0.15),    # calibrated: roots are tucked under the scalp on purpose (Hina 0.12, Amshani 0.0)
    "tip_over_root": Band(0.0, 0.75, 0.15),   # calibrated on Hina (median 0.61) and Amshani (0.64); not a published figure
    "tube_fraction": Band(0.5, 1.0, 0.2),      # heuristic: clump sides are not open ribbons
    "uv_vertical": Band(0.5, 1.0, 0.15),       # calibrated on Hina (0.63); the skill only says "vertical island per clump"
}


def findings(s: Dict[str, float], label: str, style_short: bool = True) -> List[Finding]:
    if not s.get("clump_count"):
        return [Finding(f"hair.{label}.clumps", FAIL, f"{label}: no clumps found (hair must be separate card or clump meshes)")]
    out = []

    def add(key, band, value, msg, expected, fix, src):
        out.append(Finding(f"hair.{label}.{key}", band.grade(value), f"{label}: {msg}", value, expected, fix, src))
    add("clumps", BANDS["clump_count_short"], s["clump_count"], "number of separate clumps", "20+ (short cut)",
        "Build the style from many thick clumps, not a few tubes or one sheet.", "skill: 20+ clumps for a short cut; Hina has 62")
    add("thick_over_width", BANDS["thick_over_width"], s["median_thick_over_width"], "clump thickness / width", ">= 0.45",
        "Thicken the clumps (chunky, not ribbons).",
        "skill: >= 0.45, Hina 0.64")
    add("width", BANDS["width_over_head"], s["median_width_over_head"], "clump width / head height", "0.25..0.55",
        "Clumps too thin: merge into thicker clumps." if s["median_width_over_head"] < 0.25 else "Clumps too wide: split them.",
        "skill: Hina about 0.4 H (band widened; heuristic)")
    add("tips", BANDS["tip_over_root"], s["tip_over_root_median"], "clump tip width / root width (taper)", "<= 0.75",
        "Taper the clump ends to points.", "skill: sharp clump tips; band calibrated on Hina and Amshani")
    add("tubes", BANDS["tube_fraction"], s["tube_fraction"], "share of clumps that are tube-like (sides not open)", ">= 0.50",
        "Close the clump sides; leave only the root open.", "skill: closed clumps; band is a heuristic")
    return out


def fit_findings(fit: Dict[str, float], label: str) -> List[Finding]:
    out = [
        Finding(f"hair.{label}.inside_skull", BANDS["inside_skull"].grade(fit["inside_skull_fraction"]),
                f"{label}: share of hair vertices buried more than 3% of the head height inside the head (calibrated heuristic)",
                fit["inside_skull_fraction"], "<= 0.15",
                "Hair roots are buried too deep or the style sits inside the head; move it outward."),
        Finding(f"hair.{label}.cranium", INFO, f"{label}: share of the upper cranium covered by hair", fit["cranium_coverage"]),
    ]
    if "ear_covered_fraction" in fit:
        need = fit["ear_clear_required"]
        cov = fit["ear_covered_fraction"]
        sev = PASS if cov <= 0.1 else (FAIL if need else INFO)
        out.append(Finding(f"hair.{label}.ears", sev, f"{label}: share of the ear area covered by hair" +
                           ("" if need else " (ears may be covered by this style)"), cov, "<= 0.10 when creature ears are equipped",
                           "Open a gap or add a corrective so the ears stay visible (build prompt: hair must clear creature ears)."))
    return out


def uv_findings(islands: List[Tuple[float, float]], n_clumps: int, label: str) -> List[Finding]:
    if not islands:
        return [Finding(f"hair.{label}.uv", SKIP, f"{label}: no UVs")]
    tall = sum(1 for w, h in islands if h >= 1.2 * w) / len(islands)
    ratio = len(islands) / max(n_clumps, 1)
    return [
        Finding(f"hair.{label}.uv_islands", PASS if 0.8 <= ratio <= 1.25 else WARN, f"{label}: UV islands per clump (skill: one vertical island per clump)",
                ratio, "0.8..1.25", "Unwrap each clump to its own island."),
        Finding(f"hair.{label}.uv_vertical", BANDS["uv_vertical"].grade(tall), f"{label}: share of islands taller than wide (the highlight band and root need a vertical island)",
                tall, ">= 0.50", "Orient each clump's island with the root at the bottom."),
    ]


CONTRACT_PROPS = ("root_color", "tip_color", "highlight_strength")


def contract_findings(name: str, info: dict) -> List[Finding]:
    """Build-prompt hair rules for one hair object: socket, shader, volume/width(/length) controls, colours."""
    out = []
    parent = info.get("parent") or ""
    out.append(Finding(f"hair.{name}.socket", PASS if parent.startswith("SOC-Hair") else FAIL,
                       f"{name}: parented to a SOC-Hair* socket ({parent or 'no parent'})", fix="Parent to SOC-HairScalp/Front/Side/Back/Extra."))
    mats = " ".join(info.get("materials", []))
    out.append(Finding(f"hair.{name}.shader", PASS if "NG_ToonHair" in mats else WARN, f"{name}: uses NG_ToonHair", fix="Assign the shared hair node group."))
    keys = " ".join(info.get("shape_keys", [])).lower() + " " + " ".join(info.get("props", [])).lower()
    for want in ("volume", "width"):
        out.append(Finding(f"hair.{name}.{want}", PASS if want in keys else WARN, f"{name}: has a {want} control (shape key, bone scale or property)",
                           fix=f"Add an ID- shape key or property for {want}."))
    miss = [p for p in CONTRACT_PROPS if p not in [x.lower() for x in info.get("props", [])]]
    out.append(Finding(f"hair.{name}.colours", PASS if not miss else WARN, f"{name}: root colour, tip colour and highlight strength" +
                       (f" missing: {', '.join(miss)}" if miss else ""), fix="Expose them as shader parameters / custom properties."))
    return out
