#!/usr/bin/env python3
"""One gate over every character check. Runs the other skills' validators on the SAME file, then makes them check each other.

    run_gate.py PATH [--targets knowledge/body-targets.json] [--contract knowledge/expected-contract.json]
                     [--head-audit head_audit.json] [--mesh-stats mesh_stats.json] [--manifest r_manifest.json]
                     [--require head_audit mesh_stats manifest] [--skip NAME ...] [--out gate_report.json]
    PATH is a library or pack folder (pack check runs too) or one .glb/.gltf. Exit 0 pass, 12 fail, 13 unknown, 2 usage.

Checks (each is pass / fail / unknown / skipped; a skill that is not installed is UNKNOWN, never a pass):
  pack_check         library-pack-check: contract names, tree, counts, bounds         (pack folders only)
  anatomy_rules      body-proportion-audit: rig and skin-weight rules
  pose_stress        body-proportion-audit: deformation at the main joints
  slider_sweep       body-proportion-audit: every ID- shape key at 1
  body_proportions   body-proportion-audit: measured ratios against knowledge/body-targets.json (UNKNOWN until targets exist)
  head_audit         head-shape-audit result file, when supplied or required
  mesh_stats         render-validator mesh gates on a mesh_stats.json, when supplied or required
Cross-checks (the validators validating each other; all must agree):
  height_bounds      glTF accessor bounds (library-pack-check code) vs mesh height (body-proportion-audit loader)
  triangle_count     triangle count from the glTF header vs the loader, and vs mesh_stats.json
  shape_keys         target names in the glTF vs targets the loader found
  sockets_vs_joints  SOC- nodes sit where the skeleton says (head top above the head, hand sockets at the hands, ...)
  def_prefix         bones the anatomy rules matched as body joints carry the contract's DEF- prefix
  head_vs_body       head height from the head audit fits inside the neck-to-top height from the body audit
  manifest_height    the renders' character height (r_manifest.json) is the height of this mesh
The report (gate_report.json, schema creator-gate/1) records the file's sha256, so the render-validator can refuse a render gate pass
built on a different mesh (`validate.py measure --gate-report`)."""
import argparse, hashlib, importlib.util, json, math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.environ.get("CREATOR_SKILLS") or os.path.abspath(os.path.join(HERE, "..", ".."))
EXIT_PASS, EXIT_FAIL, EXIT_UNKNOWN, EXIT_USAGE = 0, 12, 13, 2
SCHEMA = "creator-gate/1"
HEIGHT_TOL, TRI_TOL, MANIFEST_TOL = 0.03, 0.01, 0.05          # GUESS tolerances between independent measurements of the same thing
HEAD_FIT = (0.55, 1.0)                                         # GUESS: head height / (neck joint to top of mesh)
SOCKETS = {  # socket -> (joint key, max distance in body heights) or ("above", joint key)
    "SOC-HeadTop": ("above", "head"), "SOC-Neck": ("neck", 0.12), "SOC-Chest": ("between", "pelvis", "neck"),
    **{f"SOC-{n}_{s}": (j, d) for s in "LR" for n, j, d in (("Hand", f"hand_{s}", .2), ("Foot", f"foot_{s}", .2), ("Shoulder", f"upper_arm_{s}", .15), ("UpperArm", f"upper_arm_{s}", .2),
                                                           ("ForeArm", f"forearm_{s}", .2), ("Thigh", f"thigh_{s}", .2), ("Shin", f"shin_{s}", .2), ("Hip", f"thigh_{s}", .2))}}   # GUESS distances

class Missing(Exception): pass

def load_script(skill, script):
    path = os.path.join(SKILLS, skill, "scripts", script)
    if not os.path.exists(path): raise Missing(f"skill '{skill}' is not installed next to character-gate (looked for {path})")
    d = os.path.dirname(path)
    if d not in sys.path: sys.path.insert(0, d)
    spec = importlib.util.spec_from_file_location(f"{skill}_{script[:-3]}".replace("-", "_"), path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def worst(states):
    s = [x for x in states if x != "skipped"]
    return "fail" if "fail" in s else "unknown" if "unknown" in s else "pass" if s else "skipped"

def res(name, status, summary, rows=None, required=True): return {"name": name, "status": status, "summary": summary, "rows": rows or [], "required": required}

def sha(paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        with open(p, "rb") as f: h.update(f.read())
    return h.hexdigest()

def find_files(path):
    if os.path.isfile(path): return [path]
    out = []
    for dp, _, fs in os.walk(path):
        out += [os.path.join(dp, f) for f in fs if f.lower().endswith((".glb", ".gltf"))]
    return sorted(out)

# ------------------------------------------------------------------ checks on one skinned file
def per_file(path, a, facts):
    out, cross = [], []
    try: skin_io = load_script("body-proportion-audit", "skin_io.py")
    except Missing as e:
        msg = str(e)
        return [res(n, "unknown", msg) for n in ("anatomy_rules", "pose_stress", "slider_sweep", "body_proportions")], [res("cross_checks", "unknown", msg)], None
    try: m = skin_io.orient(skin_io.load(path))
    except (ValueError, KeyError) as e:
        return [res(n, "skipped", f"{os.path.basename(path)}: {e}", required=False) for n in ("anatomy_rules", "pose_stress", "slider_sweep", "body_proportions")], [], None
    ar = load_script("body-proportion-audit", "anatomy_rules.py"); ps = load_script("body-proportion-audit", "pose_stress.py"); ba = load_script("body-proportion-audit", "body_audit.py")
    if "anatomy_rules" not in a.skip:
        st, rows = ar.run(m); out.append(res("anatomy_rules", st, f"{sum(r[1] == 'fail' for r in rows)} failing rule(s)", rows))
    if "pose_stress" not in a.skip:
        st, rows = ps.run_poses(m); out.append(res("pose_stress", st, f"{sum(r[1] == 'fail' for r in rows)} failing pose(s)", rows))
    if "slider_sweep" not in a.skip:
        st, rows = ps.run_sliders(m); out.append(res("slider_sweep", st, f"{sum(r[1] == 'fail' for r in rows)} failing slider(s)", rows))
    prof = None
    try:
        V, T, J = ba.load_gltf(path); prof = ba.measure(V, T, J, os.path.basename(path)); facts.setdefault("height", prof["height"]); facts.setdefault("tris", len(T))
        facts.setdefault("metrics", prof["metrics"])
    except (ValueError, KeyError) as e: prof = None; facts.setdefault("measure_error", str(e))
    if "body_proportions" not in a.skip:
        if prof is None: out.append(res("body_proportions", "unknown", "mesh could not be measured"))
        elif not a.targets or not os.path.exists(a.targets): out.append(res("body_proportions", "unknown", "no body targets file (build knowledge/body-targets.json from measured references with body_audit.py targets)"))
        else:
            with open(a.targets) as f: targets = json.load(f)
            st, rows = ba.check(prof, targets); out.append(res("body_proportions", st, f"{sum(r[4] == 'fail' for r in rows)} proportion(s) out of band", [list(r) for r in rows]))
    cross += cross_file(path, m, prof, a, facts)
    return out, cross, m

def cross_file(path, m, prof, a, facts):
    rows = []
    cp = load_script("library-pack-check", "check_pack.py")
    g, _ = cp.read_gltf(path); wb = cp.world_bounds(g)
    if "height_bounds" not in a.skip:
        if wb is None or prof is None: rows.append(res("height_bounds", "unknown", "accessor bounds or measurement missing"))
        else:
            hb = wb[1][1] - wb[0][1]; hm = prof["height"]; d = abs(hb - hm) / max(hb, 1e-9)
            rows.append(res("height_bounds", "fail" if d > HEIGHT_TOL else "pass", f"accessor bounds say {hb:.4f}, the loader measures {hm:.4f} ({d:.1%} apart)" + ("; one of them applies node transforms differently" if d > HEIGHT_TOL else "")))
    nodes = g.get("nodes", [])
    skinned = [n for n in nodes if "mesh" in n and "skin" in n]
    if "triangle_count" not in a.skip:
        header = cp.tri_count(g); skin_only = sum(sum(g["accessors"][p["indices"]]["count"] // 3 if "indices" in p else g["accessors"][p["attributes"]["POSITION"]]["count"] // 3
                                                      for p in g["meshes"][n["mesh"]]["primitives"] if p.get("mode", 4) == 4) for n in skinned)
        loader = len(m["T"]); facts["tris_header"] = header
        if skin_only != loader: rows.append(res("triangle_count", "fail", f"glTF header counts {skin_only} skinned triangles, the loader read {loader}"))
        else:
            msg = f"{header} triangles (header) = {loader} skinned (loader)"
            if a.mesh_stats_data and a.mesh_stats_data.get("tris") is not None:
                d = abs(a.mesh_stats_data["tris"] - header) / max(header, 1)
                rows.append(res("triangle_count", "fail" if d > TRI_TOL else "pass", msg + f"; mesh_stats.json says {a.mesh_stats_data['tris']} ({d:.1%} apart)" if d > TRI_TOL else msg + f"; matches mesh_stats.json ({a.mesh_stats_data['tris']})"))
            else: rows.append(res("triangle_count", "pass", msg))
    if "shape_keys" not in a.skip:
        names = set(); [names.update(g["meshes"][n["mesh"]].get("extras", {}).get("targetNames", [])) for n in skinned]
        if not names and not m["targets"]: rows.append(res("shape_keys", "unknown", "no morph targets on the skinned meshes"))
        else: rows.append(res("shape_keys", "pass" if names == set(m["targets"]) else "fail", f"{len(names)} target names in the glTF, loader found {len(m['targets'])}" + ("" if names == set(m["targets"]) else f"; differ: {sorted(names ^ set(m['targets']))[:4]}")))
    if "sockets_vs_joints" not in a.skip: rows.append(sockets_check(g, m, facts))
    if "def_prefix" not in a.skip:
        if not m.get("oriented"): rows.append(res("def_prefix", "unknown", "skeleton not recognised"))
        else:
            bad = sorted(m["names"][i] for k, i in m["key"].items() if k not in ("pelvis", "chest") and not m["names"][i].startswith("DEF-"))
            rows.append(res("def_prefix", "fail" if bad else "pass", f"{len(bad)} body bone(s) without the DEF- prefix the contract requires: {', '.join(bad[:5])}" if bad else "every matched body bone is a DEF- bone"))
    if a.head_audit_data is not None and "head_vs_body" not in a.skip and prof is not None:
        H = (a.head_audit_data.get("profile") or {}).get("H"); tt = prof["metrics"].get("head_to_top")
        if not H or tt is None: rows.append(res("head_vs_body", "unknown", "head audit has no H or the body has no neck joint"))
        else:
            r = H / (tt * prof["height"]); ok = HEAD_FIT[0] <= r <= HEAD_FIT[1]
            rows.append(res("head_vs_body", "pass" if ok else "fail", f"head audit head height {H:.3f} is {r:.0%} of the neck-to-top height {tt * prof['height']:.3f} (expected {HEAD_FIT[0]:.0%}-{HEAD_FIT[1]:.0%}); " + ("consistent" if ok else "the head audit and the body audit are looking at different meshes or units")))
    if a.manifest_data is not None and "manifest_height" not in a.skip and prof is not None:
        ch = a.manifest_data.get("character_height")
        if not ch: rows.append(res("manifest_height", "unknown", "r_manifest.json has no character_height"))
        else:
            d = abs(ch - prof["height"]) / prof["height"]; rows.append(res("manifest_height", "fail" if d > MANIFEST_TOL else "pass", f"renders were framed for height {ch:.3f}, this mesh is {prof['height']:.3f} ({d:.1%} apart)" + ("; the renders show a different model" if d > MANIFEST_TOL else "")))
    return rows

def sockets_check(g, m, facts):
    import numpy as np
    nodes = g.get("nodes", []); parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}; ba = load_script("body-proportion-audit", "body_audit.py"); cache = {}
    def world(i):
        if i not in cache: cache[i] = (world(parent[i]) if i in parent else np.eye(4)) @ ba._mat(nodes[i])
        return cache[i]
    soc = {n["name"]: world(i)[:3, 3] for i, n in enumerate(nodes) if n.get("name", "").startswith("SOC-")}
    if not soc: return res("sockets_vs_joints", "unknown", "no SOC- nodes in this file")
    if not m.get("oriented"): return res("sockets_vs_joints", "unknown", "skeleton not recognised")
    zup = lambda p: np.array([p[0], -p[2], p[1]]); R = m.get("R", np.eye(3)); H = float(m["V"][:, 2].max() - m["V"][:, 2].min()); J = {k: m["jpos"][i] for k, i in m["key"].items()}
    bad, ok = [], 0
    for name, w in sorted(soc.items()):
        rule = SOCKETS.get(name)
        if not rule: continue
        p = R @ zup(w)
        try:
            if rule[0] == "above":
                if p[2] < J[rule[1]][2]: bad.append(f"{name} is below the {rule[1]} joint")
                else: ok += 1
            elif rule[0] == "between":
                lo, hi = sorted((J[rule[1]][2], J[rule[2]][2]))
                if not lo - 0.05 * H <= p[2] <= hi + 0.05 * H: bad.append(f"{name} is not between the {rule[1]} and {rule[2]} joints")
                else: ok += 1
            else:
                d = np.linalg.norm(p - J[rule[0]]) / H
                if d > rule[1]: bad.append(f"{name} is {d:.0%} of the body height from {rule[0]} (limit {rule[1]:.0%})")
                else: ok += 1
        except KeyError as e: bad.append(f"{name}: skeleton has no {e.args[0]}")
    if not bad and ok == 0: return res("sockets_vs_joints", "unknown", "none of the SOC- nodes has a placement rule")
    return res("sockets_vs_joints", "fail" if bad else "pass", "; ".join(bad[:4]) if bad else f"{ok} socket(s) sit where the skeleton says")

# ------------------------------------------------------------------ gate
def run(a):
    checks, cross, skipped, facts = [], [], [], {}
    files = find_files(a.path); pack_mode = os.path.isdir(a.path)
    if not files: raise ValueError(f"no .glb or .gltf under {a.path}")
    if pack_mode and "pack_check" not in a.skip:
        try:
            cp = load_script("library-pack-check", "check_pack.py"); contract = None
            if a.contract:
                with open(a.contract) as f: contract = json.load(f)
            R = cp.check(a.path, contract); nf, nu, nw = R.count("FAIL"), R.count("UNKNOWN"), R.count("WARN")
            checks.append(res("pack_check", "fail" if nf else "unknown" if nu else "pass", f"{nf} fail, {nu} unknown, {nw} warn", [[i["level"], i["pack"], i["code"], i["message"]] for i in R.items if i["level"] in ("FAIL", "UNKNOWN")]))
        except Missing as e: checks.append(res("pack_check", "unknown", str(e)))
    elif pack_mode: skipped.append("pack_check (by request)")
    a.mesh_stats_data = a.manifest_data = a.head_audit_data = None
    for attr, p in (("mesh_stats_data", a.mesh_stats), ("manifest_data", a.manifest), ("head_audit_data", a.head_audit)):
        if p:
            with open(p) as f: setattr(a, attr, json.load(f))
    per, anyskin = {}, False
    for fpath in files:
        c, x, m = per_file(fpath, a, facts)
        if m is None and all(r["status"] == "skipped" for r in c): continue
        anyskin = True; per[fpath] = (c, x)
    if not anyskin: checks.append(res("anatomy_rules", "unknown", "no skinned mesh found in any file: nothing to anatomy-check"))
    for name in ("anatomy_rules", "pose_stress", "slider_sweep", "body_proportions"):
        rs = [r for fp, (c, _) in per.items() for r in c if r["name"] == name]
        if rs:
            st = worst([r["status"] for r in rs]); rows = [r for r2 in rs for r in r2["rows"]]
            checks.append(res(name, st, "; ".join(r["summary"] for r in rs) + (f" ({len(per)} files)" if len(per) > 1 else ""), rows))
        elif anyskin and name not in a.skip: pass
    for n in ("anatomy_rules", "pose_stress", "slider_sweep", "body_proportions"):
        if n in a.skip: skipped.append(f"{n} (by request)")
    xs = [r for fp, (_, x) in per.items() for r in x]
    for name in sorted({r["name"] for r in xs}):
        rs = [r for r in xs if r["name"] == name]; cross.append(res(name, worst([r["status"] for r in rs]), " | ".join(dict.fromkeys(r["summary"] for r in rs))))
    if a.head_audit_data is not None or "head_audit" in a.require:
        if a.head_audit_data is None: checks.append(res("head_audit", "unknown", "required but no --head-audit file supplied"))
        else:
            h = a.head_audit_data; st = h.get("status") or ("pass" if h.get("ok") else "fail")
            checks.append(res("head_audit", st, "; ".join(h.get("bad", [])[:3]) or ("unmeasured: " + ", ".join(h.get("unknown", [])[:4]) if st == "unknown" else "head within the reference")))
    if a.mesh_stats_data is not None or "mesh_stats" in a.require:
        if a.mesh_stats_data is None: checks.append(res("mesh_stats", "unknown", "required but no --mesh-stats file supplied"))
        else:
            try:
                v = load_script("render-validator", "validate.py"); contract = None
                if a.contract:
                    with open(a.contract) as f: contract = json.load(f)
                mc, mu, _ = v.check_mesh(a.mesh_stats_data, v.DEFAULTS, contract); failing = [k for k, c in mc.items() if c["ok"] is False]
                checks.append(res("mesh_stats", "fail" if failing else "unknown" if mu else "pass", ("failing: " + ", ".join(failing)) if failing else ("unmeasured: " + ", ".join(mu[:4]) if mu else "mesh gates pass")))
            except Missing as e: checks.append(res("mesh_stats", "unknown", str(e)))
    if "manifest" in a.require and a.manifest_data is None: cross.append(res("manifest_height", "unknown", "required but no --manifest file supplied"))
    status = worst([c["status"] for c in checks + cross])
    if status == "skipped": status = "unknown"
    return {"schema": SCHEMA, "status": status, "subject": os.path.abspath(a.path), "subject_sha": sha(files), "files": [os.path.relpath(f, a.path if pack_mode else os.path.dirname(a.path)) for f in files],
            "time": time.time(), "facts": {k: v for k, v in facts.items() if k in ("height", "tris", "tris_header")}, "checks": checks, "cross_checks": cross, "skipped": skipped}

def report_text(r):
    L = [f"CHARACTER GATE {os.path.basename(r['subject'])}: {r['status'].upper()}  (sha {r['subject_sha'][:12]})"]
    for title, items in (("checks", r["checks"]), ("cross-checks", r["cross_checks"])):
        L.append(f"  {title}:")
        for c in items:
            L.append(f"    {c['status'].upper():8s} {c['name']:18s} {c['summary']}")
            if c["status"] in ("fail", "unknown"):
                for row in c["rows"][:6]:
                    if (isinstance(row, (list, tuple)) and len(row) >= 3 and row[1] in ("fail", "unknown")): L.append(f"             - {row[0]}: {row[2]}")
                    elif isinstance(row, (list, tuple)) and len(row) >= 6 and row[4] in ("fail", "unknown"): L.append(f"             - {row[0]}: {row[5]}")
                    elif isinstance(row, (list, tuple)) and len(row) == 4: L.append(f"             - {row[0]} {row[2]}: {row[3]}")
    if r["skipped"]: L.append("  skipped: " + ", ".join(r["skipped"]))
    return "\n".join(L)

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path"); ap.add_argument("--targets"); ap.add_argument("--contract"); ap.add_argument("--head-audit"); ap.add_argument("--mesh-stats"); ap.add_argument("--manifest")
    ap.add_argument("--require", nargs="*", default=[], choices=["head_audit", "mesh_stats", "manifest"]); ap.add_argument("--skip", nargs="*", default=[]); ap.add_argument("--out")
    try: a = ap.parse_args(argv)
    except SystemExit as e: return EXIT_USAGE if e.code else 0
    if not os.path.exists(a.path): print(f"error: {a.path} does not exist", file=sys.stderr); return EXIT_USAGE
    try: r = run(a)
    except (OSError, ValueError, KeyError) as e: print(f"error: {e}", file=sys.stderr); return EXIT_USAGE
    print(report_text(r))
    if a.out:
        with open(a.out, "w") as f: json.dump(r, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return {"pass": EXIT_PASS, "fail": EXIT_FAIL, "unknown": EXIT_UNKNOWN}[r["status"]]

if __name__ == "__main__":
    sys.exit(main())
