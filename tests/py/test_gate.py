import copy, importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile, unittest
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
SK = ROOT / ".claude/skills"
GATE = SK / "character-gate/scripts/run_gate.py"
VALIDATE = SK / "render-validator/scripts/validate.py"
MAKE_PACK = SK / "library-pack-check/scripts/make_test_pack.py"
sys.path.insert(0, str(pathlib.Path(__file__).parent)); sys.path.insert(0, str(SK / "body-proportion-audit/scripts"))
import skinned_fixture as fx
import body_audit as ba

def run(script, *args, env=None):
    p = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True, env={**os.environ, **(env or {})})
    return p.returncode, p.stdout + p.stderr

class GateCase(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory(); self.d = pathlib.Path(self._t.name)
        m = fx.build(bad_targets=False); self.path = self.d / "body.gltf"; fx.write_glb(m, self.path, True, sockets=fx.default_sockets(m))
        prof = ba.measure(*ba.load_gltf(str(self.path)), "ref"); self.targets = self.d / "targets.json"
        self.targets.write_text(json.dumps(ba.build_targets([prof])))
    def tearDown(self): self._t.cleanup()
    def gate(self, path=None, *extra, env=None):
        code, out = run(GATE, path or self.path, "--targets", self.targets, "--skip", "pack_check", "--out", self.d / "gate.json", *extra, env=env)
        return code, out, (json.loads((self.d / "gate.json").read_text()) if (self.d / "gate.json").exists() else None)
    def write(self, name, m, sockets=True, targets=True):
        p = self.d / name; fx.write_glb(m, p, targets, sockets=fx.default_sockets(m) if sockets is True else sockets); return p
    def status(self, rep, name):
        return next(c["status"] for c in rep["checks"] + rep["cross_checks"] if c["name"] == name)

class Passing(GateCase):
    def test_good_figure_passes_every_check_and_cross_check(self):
        code, out, rep = self.gate(); self.assertEqual(code, 0, out)
        self.assertEqual(rep["schema"], "creator-gate/1"); self.assertEqual(len(rep["subject_sha"]), 64)
        for n in ("anatomy_rules", "pose_stress", "slider_sweep", "body_proportions", "height_bounds", "triangle_count", "shape_keys", "sockets_vs_joints", "def_prefix"):
            self.assertEqual(self.status(rep, n), "pass", n)

class Failing(GateCase):
    def test_each_defect_is_caught_by_the_right_check(self):
        cases = (("anatomy_rules", dict(fingers=4)), ("pose_stress", dict(smooth=False)), ("slider_sweep", dict(bad_targets=True)))
        for check, kw in cases:
            m = fx.build(**{"bad_targets": False, **kw}); p = self.write(f"{check}.gltf", m)
            code, out, rep = self.gate(p); self.assertEqual(code, 12, (check, out)); self.assertEqual(self.status(rep, check), "fail", check)

    def test_pack_check_cannot_see_what_anatomy_sees(self):
        """A valid minimal pack passes the pack check, and the gate still fails it: its rig has no arms or legs."""
        pack = self.d / "library/humanoid/bodies/p"; code, out = run(MAKE_PACK, pack.parent, "--id", "body_test")
        self.assertEqual(code, 0, out)
        code, out = run(GATE, self.d / "library", "--contract", ROOT / "knowledge/expected-contract.json", "--out", self.d / "g2.json", "--skip", "pose_stress", "slider_sweep")
        rep = json.loads((self.d / "g2.json").read_text()); self.assertEqual(code, 12, out)
        self.assertEqual(self.status(rep, "pack_check"), "pass"); self.assertEqual(self.status(rep, "anatomy_rules"), "fail")

    def test_sockets_in_the_wrong_place_fail_the_cross_check(self):
        m = fx.build(bad_targets=False); s = fx.default_sockets(m); s["SOC-Hand_L"] = (np.array(s["SOC-Hand_L"][0]) + [.5, 0, .4], "DEF-hand.L")
        code, out, rep = self.gate(self.write("sock.gltf", m, sockets=s)); self.assertEqual(code, 12); self.assertEqual(self.status(rep, "sockets_vs_joints"), "fail")
        self.assertEqual(self.status(rep, "anatomy_rules"), "pass")       # every single-skill check is still happy

    def test_missing_def_prefix_fails(self):
        m = fx.build(bad_targets=False); m["names"][m["names"].index("DEF-hand.L")] = "hand.L"
        code, out, rep = self.gate(self.write("nodef.gltf", m, sockets=False)); self.assertEqual(self.status(rep, "def_prefix"), "fail")

    def test_renders_of_another_model_fail(self):
        man = self.d / "man.json"; man.write_text(json.dumps({"character_height": 1.72}))        # this mesh is 0.99 high
        code, out, rep = self.gate(None, "--manifest", man); self.assertEqual(code, 12); self.assertEqual(self.status(rep, "manifest_height"), "fail")
        man.write_text(json.dumps({"character_height": 0.99})); code, out, rep = self.gate(None, "--manifest", man); self.assertEqual(code, 0, out)

    def test_head_audit_from_another_mesh_fails(self):
        ha = self.d / "h.json"; ha.write_text(json.dumps({"status": "pass", "ok": True, "bad": [], "unknown": [], "profile": {"H": 0.9}}))   # head as tall as the body
        code, out, rep = self.gate(None, "--head-audit", ha); self.assertEqual(self.status(rep, "head_vs_body"), "fail")
        ha.write_text(json.dumps({"status": "pass", "ok": True, "bad": [], "unknown": [], "profile": {"H": 0.16}})); code, out, rep = self.gate(None, "--head-audit", ha); self.assertEqual(code, 0, out)

    def test_a_failed_head_audit_fails_the_gate(self):
        ha = self.d / "h.json"; ha.write_text(json.dumps({"status": "fail", "ok": False, "bad": ["Cranium too wide"], "unknown": [], "profile": {"H": 0.16}}))
        code, out, rep = self.gate(None, "--head-audit", ha); self.assertEqual(code, 12); self.assertEqual(self.status(rep, "head_audit"), "fail")

    def test_mesh_stats_for_another_mesh_fails(self):
        ms = self.d / "ms.json"; ms.write_text(json.dumps({"tris": 99999, "non_manifold_edges": 0, "zero_area_faces": 0, "loose_parts": 1, "ngon_share": 0}))
        code, out, rep = self.gate(None, "--mesh-stats", ms); self.assertEqual(self.status(rep, "triangle_count"), "fail"); self.assertEqual(code, 12)

class Unknown(GateCase):
    def test_no_sockets_and_no_targets_are_unknown_not_pass(self):
        p = self.write("nosock.gltf", fx.build(bad_targets=False), sockets=False)
        code, out, rep = self.gate(p); self.assertEqual(code, 13); self.assertEqual(self.status(rep, "sockets_vs_joints"), "unknown")
        code, out = run(GATE, p, "--skip", "pack_check", "sockets_vs_joints"); self.assertEqual(code, 13); self.assertIn("no body targets", out)

    def test_required_but_missing_file_is_unknown(self):
        code, out, rep = self.gate(None, "--require", "head_audit"); self.assertEqual(code, 13); self.assertEqual(self.status(rep, "head_audit"), "unknown")

    def test_missing_sibling_skill_is_unknown_never_a_pass(self):
        lone = self.d / "skills"; shutil.copytree(SK / "character-gate", lone / "character-gate", ignore=shutil.ignore_patterns("__pycache__"))
        code, out = run(lone / "character-gate/scripts/run_gate.py", self.path, "--skip", "pack_check", "--out", self.d / "g3.json", env={"CREATOR_SKILLS": str(lone)})
        self.assertEqual(code, 13, out); self.assertIn("not installed", out)

    def test_unusable_input_is_a_usage_error(self):
        self.assertEqual(run(GATE, self.d / "nope.glb")[0], 2); empty = self.d / "empty"; empty.mkdir(); self.assertEqual(run(GATE, empty)[0], 2)

class RenderValidatorTakesTheGate(unittest.TestCase):
    def setUp(self):
        from test_validate import figure
        self._t = tempfile.TemporaryDirectory(); self.d = pathlib.Path(self._t.name)
        for i, n in enumerate(("ref", "a", "b", "c")): figure(self.d / f"{n}.png", tweak=i)
        self.ws = self.d / "ws"
    def tearDown(self): self._t.cleanup()
    def init(self, *extra): run(VALIDATE, "init", self.ws, "--ref", f"front={self.d/'ref.png'}", *extra)
    def measure(self, img, *extra): return run(VALIDATE, "measure", self.ws, "--view", f"front={self.d/img}", *extra)
    def gate(self, name, status, **facts):
        p = self.d / name; p.write_text(json.dumps({"schema": "creator-gate/1", "status": status, "subject_sha": "ab" * 32, "facts": facts, "checks": [{"name": "anatomy_rules", "status": status}] if status != "pass" else [], "cross_checks": []})); return p

    def test_required_gate_missing_is_unknown(self):
        self.init("--require-gate"); code, out = self.measure("a.png"); self.assertEqual(code, 13); self.assertIn("gate:report not supplied", out)

    def test_failed_gate_blocks_the_render(self):
        self.init(); code, out = self.measure("a.png", "--gate-report", self.gate("f.json", "fail")); self.assertEqual(code, 12); self.assertIn("gate:structure", out); self.assertIn("anatomy_rules", out)

    def test_unknown_gate_is_unknown(self):
        self.init(); code, out = self.measure("a.png", "--gate-report", self.gate("u.json", "unknown")); self.assertEqual(code, 13); self.assertIn("gate:report is unknown", out)

    def test_passing_gate_does_not_block_and_is_recorded(self):
        self.init(); code, out = self.measure("a.png", "--gate-report", self.gate("p.json", "pass"))
        self.assertNotIn("gate:", out); st = json.loads((self.ws / "state.json").read_text())["iterations"][-1]; self.assertEqual(st["gate_report"]["status"], "pass")

    def test_gate_and_mesh_stats_must_describe_the_same_mesh(self):
        ms = self.d / "ms.json"; ms.write_text(json.dumps({"tris": 5000}))
        self.init(); code, out = self.measure("a.png", "--gate-report", self.gate("p.json", "pass", tris=24000, height=1.7), "--mesh-stats", ms)
        self.assertEqual(code, 12); self.assertIn("different mesh", out)

    def test_gate_and_render_manifest_must_agree_on_height(self):
        man = self.d / "man.json"; man.write_text(json.dumps({"blender": "5", "engine": "CYCLES", "resolution": 64, "view_transform": "Standard", "character_height": 2.5, "head_height": 0.3, "views": {}}))
        self.init(); code, out = self.measure("a.png", "--gate-report", self.gate("p.json", "pass", tris=1, height=1.7), "--manifest", man)
        self.assertEqual(code, 12); self.assertIn("different model", out)

    def test_not_a_gate_file_is_unknown(self):
        bad = self.d / "x.json"; bad.write_text("{}"); self.init(); code, out = self.measure("a.png", "--gate-report", bad); self.assertEqual(code, 13); self.assertIn("not a creator-gate/1 file", out)

if __name__ == "__main__":
    unittest.main()
