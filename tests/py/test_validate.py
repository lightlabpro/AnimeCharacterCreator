"""python3 -m unittest discover -s tests/py   (needs numpy and Pillow)"""
import json, pathlib, subprocess, sys, tempfile, unittest
from PIL import Image, ImageDraw

root = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = root / ".claude/skills/render-validator/scripts/validate.py"
MESH = root / ".claude/skills/render-validator/scripts/mesh_stats.py"
CRITERIA = ["proportions_match_reference", "silhouette_reads_like_reference", "face_structure", "eyes_lash_highlights", "brows",
            "hair_clumps_and_tones", "shading_hard_warm_shadows", "outlines_thin_and_coloured", "colour_palette_match",
            "no_artifacts_or_melted_parts", "thumbnail_squint_test"]

def figure(path, flat=False, tweak=0):
    im = Image.new("RGB", (400, 600), (230, 235, 240)); d = ImageDraw.Draw(im)
    skin, shade, hair = ((150, 150, 150), (150, 150, 150), (120, 120, 120)) if flat else ((240, 200, 170), (200, 130, 90), (60, 40, 120))
    o = None if flat else (70, 40, 30)
    d.ellipse([120, 200, 280, 420], fill=hair, outline=o, width=3)
    d.ellipse([140, 150, 260, 330], fill=skin, outline=o, width=3)
    if not flat: d.ellipse([190, 150, 260, 330], fill=shade, outline=o, width=3)
    d.ellipse([125, 100, 275, 260], fill=hair, outline=o, width=3)
    d.rectangle([160, 330, 240, 520], fill=skin, outline=o, width=3)
    if tweak: im.putpixel((5 + tweak, 5), (9, 9, 9 + tweak))
    im.save(path)

def run(*args):
    p = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

def review(path, render_hash, reviewer="independent", score=2, drop=None):
    crit = {c: {"score": score, "evidence": "A concrete visible observation about the sheet."} for c in CRITERIA if c != drop}
    path.write_text(json.dumps({"reviewer": reviewer, "render_hash": render_hash, "defects_fixed_since_last": ["x"], "criteria": crit}))

def last_hash(ws):
    return json.loads((ws / "state.json").read_text())["iterations"][-1]["render_hash"]

class Validator(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = pathlib.Path(self.t.name)
        figure(self.d / "ref.png"); figure(self.d / "good.png", tweak=1); figure(self.d / "good2.png", tweak=2)
        figure(self.d / "good3.png", tweak=3); figure(self.d / "bad.png", flat=True)
        self.ws = self.d / "ws"
    def tearDown(self): self.t.cleanup()
    def init(self, *extra): return run("init", self.ws, "--ref", f"front={self.d/'ref.png'}", *extra)

    def test_bad_render_fails_with_12(self):
        self.init(); code, out = run("measure", self.ws, "--view", f"front={self.d/'bad.png'}")
        self.assertEqual(code, 12); self.assertIn("MEASURE_FAIL", out); self.assertIn("front:shadow_chroma", out)

    def test_identical_render_is_refused(self):
        self.init(); run("measure", self.ws, "--view", f"front={self.d/'good.png'}")
        code, out = run("measure", self.ws, "--view", f"front={self.d/'good.png'}")
        self.assertEqual(code, 12); self.assertIn("NO_CHANGE", out)

    def test_missing_required_view_is_unknown_not_ok(self):
        self.init("--require-view", "front", "--require-view", "side")
        code, out = run("measure", self.ws, "--view", f"front={self.d/'good.png'}")
        self.assertEqual(code, 13); self.assertIn("view:side", out); self.assertNotIn("MEASURE_OK", out)

    def test_mesh_stats_missing_is_unknown_when_required(self):
        self.init("--require-mesh"); code, out = run("measure", self.ws, "--view", f"front={self.d/'good.png'}")
        self.assertEqual(code, 13); self.assertIn("mesh:not supplied", out)

    def test_mesh_budget_failure_beats_unknown(self):
        self.init("--require-mesh")
        (self.d / "stats.json").write_text(json.dumps({"tris": 90000, "non_manifold_edges": 0}))  # over budget, other keys missing
        code, out = run("measure", self.ws, "--view", f"front={self.d/'good.png'}", "--mesh-stats", self.d / "stats.json")
        self.assertEqual(code, 12); self.assertIn("mesh:tris", out)

    def test_missing_stat_key_is_unknown(self):
        self.init("--require-mesh")
        (self.d / "stats.json").write_text(json.dumps({"tris": 20000}))
        code, out = run("measure", self.ws, "--view", f"front={self.d/'good.png'}", "--mesh-stats", self.d / "stats.json")
        self.assertEqual(code, 13); self.assertIn("mesh:non_manifold_edges", out)

    def test_orphan_contract_names_are_flagged(self):
        self.init("--require-mesh")
        (self.d / "stats.json").write_text(json.dumps({"tris": 20000, "non_manifold_edges": 0, "zero_area_faces": 0, "loose_parts": 1, "ngon_share": 0.0,
                                                       "shape_keys": ["ID-EyeSize", "ID-NotARealKey"]}))
        code, out = run("measure", self.ws, "--view", f"front={self.d/'good.png'}", "--mesh-stats", self.d / "stats.json",
                        "--contract", root / "knowledge/expected-contract.json")
        self.assertEqual(code, 0, out); self.assertIn("ID-NotARealKey", out); self.assertNotIn("ID-EyeSize,", out)

    def test_gate_needs_three_iterations_and_an_independent_review(self):
        self.init()
        for i, f in enumerate(("good.png", "good2.png")):
            self.assertEqual(run("measure", self.ws, "--view", f"front={self.d/f}", "--stage", f"s{i}")[0], 0)
        review(self.d / "r.json", last_hash(self.ws))
        code, out = run("gate", self.ws, "--review", self.d / "r.json")
        self.assertEqual(code, 12); self.assertIn("at least 3", out)
        run("measure", self.ws, "--view", f"front={self.d/'good3.png'}")
        review(self.d / "r.json", last_hash(self.ws), reviewer="self")
        code, out = run("gate", self.ws, "--review", self.d / "r.json")
        self.assertEqual(code, 12); self.assertIn("independent", out)
        review(self.d / "r.json", last_hash(self.ws))
        code, out = run("gate", self.ws, "--review", self.d / "r.json"); self.assertEqual(code, 0, out); self.assertIn("PASS", out)

    def test_stale_or_low_review_does_not_pass(self):
        self.init()
        for f in ("good.png", "good2.png", "good3.png"): run("measure", self.ws, "--view", f"front={self.d/f}")
        review(self.d / "r.json", "0000000000000000")
        self.assertEqual(run("gate", self.ws, "--review", self.d / "r.json")[0], 12)
        review(self.d / "r.json", last_hash(self.ws), score=1)
        code, out = run("gate", self.ws, "--review", self.d / "r.json"); self.assertEqual(code, 12); self.assertIn("below floor", out)
        review(self.d / "r.json", last_hash(self.ws), drop="brows")
        self.assertIn("brows", run("gate", self.ws, "--review", self.d / "r.json")[1])

    def test_gate_is_unknown_while_required_view_missing(self):
        self.init("--require-view", "front", "--require-view", "side")
        run("measure", self.ws, "--view", f"front={self.d/'good.png'}")
        review(self.d / "r.json", last_hash(self.ws))
        self.assertEqual(run("gate", self.ws, "--review", self.d / "r.json")[0], 13)

class MeshStats(unittest.TestCase):
    def test_cube_and_open_plane(self):
        for name, text, boundary in (("cube", "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nv 0 0 1\nv 1 0 1\nv 1 1 1\nv 0 1 1\nf 1 2 3 4\nf 5 8 7 6\nf 1 5 6 2\nf 2 6 7 3\nf 3 7 8 4\nf 4 8 5 1\n", 0),
                                     ("plane", "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n", 4)):
            with tempfile.TemporaryDirectory() as t:
                p = pathlib.Path(t) / f"{name}.obj"; p.write_text(text)
                st = json.loads(subprocess.run([sys.executable, str(MESH), str(p)], capture_output=True, text=True).stdout)
                self.assertEqual(st["boundary_edges"], boundary); self.assertEqual(st["non_manifold_edges"], 0); self.assertEqual(st["loose_parts"], 1)

    def test_degenerate_and_loose_geometry(self):
        with tempfile.TemporaryDirectory() as t:
            p = pathlib.Path(t) / "bad.obj"
            p.write_text("v 0 0 0\nv 1 0 0\nv 2 0 0\nv 5 5 5\nv 6 5 5\nv 5 6 5\nv 9 9 9\nf 1 2 3\nf 4 5 6\n")
            st = json.loads(subprocess.run([sys.executable, str(MESH), str(p)], capture_output=True, text=True).stdout)
            self.assertEqual(st["zero_area_faces"], 1); self.assertEqual(st["loose_parts"], 2); self.assertEqual(st["loose_verts"], 1)


class SkillsInSync(unittest.TestCase):
    def test_skills_zips_and_contract_validate(self):
        r = subprocess.run([sys.executable, str(root / "scripts/validate_skills.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

if __name__ == "__main__":
    unittest.main()
