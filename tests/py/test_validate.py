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

def review(path, render_hash, reviewer="independent", score=2, drop=None):  # scores alternate score, score+1 so the review is not uniform
    crit = {c: {"score": score + (i % 2), "evidence": f"Observation {i} about {c.replace('_', ' ')} visible on the contact sheet."} for i, c in enumerate(CRITERIA) if c != drop}
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


class StricterGate(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = pathlib.Path(self.t.name)
        for i, n in enumerate(("ref", "g1", "g2", "g3")): figure(self.d / f"{n}.png", tweak=i)
        self.ws = self.d / "ws"
        run("init", self.ws, "--ref", f"front={self.d/'ref.png'}")
        for n in ("g1", "g2", "g3"): run("measure", self.ws, "--view", f"front={self.d/(n + '.png')}")
        self.h = last_hash(self.ws)
    def tearDown(self): self.t.cleanup()
    def gate(self, crit): 
        (self.d / "r.json").write_text(json.dumps({"reviewer": "independent", "render_hash": self.h, "defects_fixed_since_last": ["x"], "criteria": crit}))
        return run("gate", self.ws, "--review", self.d / "r.json")

    def test_uniform_review_is_a_rubber_stamp(self):
        code, out = self.gate({c: {"score": 3, "evidence": f"Unique remark number {i} about this criterion on the sheet."} for i, c in enumerate(CRITERIA)})
        self.assertEqual(code, 12); self.assertIn("same score", out)

    def test_repeated_evidence_is_rejected(self):
        code, out = self.gate({c: {"score": 2 + i % 2, "evidence": "The whole sheet looks acceptable to me overall."} for i, c in enumerate(CRITERIA)})
        self.assertEqual(code, 12); self.assertIn("repeats", out)

    def test_short_evidence_is_rejected(self):
        code, out = self.gate({c: {"score": 2 + i % 2, "evidence": f"fine {i} ok yes"} for i, c in enumerate(CRITERIA)})
        self.assertEqual(code, 12); self.assertIn("too short", out)

    def test_tiny_change_with_a_failing_view_is_called_a_tweak(self):
        figure(self.d / "flat.png", flat=True)
        ws = self.d / "ws2"; run("init", ws, "--ref", f"front={self.d/'ref.png'}")
        run("measure", ws, "--view", f"front={self.d/'flat.png'}")
        figure(self.d / "flat2.png", flat=True, tweak=4)
        code, out = run("measure", ws, "--view", f"front={self.d/'flat2.png'}")
        self.assertEqual(code, 12); self.assertIn("MICRO-CHANGE", out)

    def test_head_audit_gate(self):
        ws = self.d / "ws3"; run("init", ws, "--ref", f"front={self.d/'ref.png'}", "--require-head")
        code, out = run("measure", ws, "--view", f"front={self.d/'g1.png'}")
        self.assertEqual(code, 13); self.assertIn("head:audit", out)
        (self.d / "bad.json").write_text(json.dumps({"ok": False, "bad": ["Cranium too wide: scale the skull in X only."]}))
        code, out = run("measure", ws, "--view", f"front={self.d/'g2.png'}", "--head-audit", self.d / "bad.json")
        self.assertEqual(code, 12); self.assertIn("head:shape", out)
        (self.d / "ok.json").write_text(json.dumps({"ok": True, "bad": []}))
        code, out = run("measure", ws, "--view", f"front={self.d/'g3.png'}", "--head-audit", self.d / "ok.json")
        self.assertEqual(code, 0, out)

    def test_report_lists_every_iteration(self):
        code, out = run("report", self.ws)
        self.assertEqual(code, 0); self.assertIn("3 iterations", out); self.assertTrue((self.ws / "report.md").exists())


class TwoReviewers(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = pathlib.Path(self.t.name)
        for i, n in enumerate(("ref", "g1", "g2", "g3")): figure(self.d / f"{n}.png", tweak=i)
        self.ws = self.d / "ws"
        run("init", self.ws, "--ref", f"front={self.d/'ref.png'}", "--reviews", "2")
        for n in ("g1", "g2", "g3"): run("measure", self.ws, "--view", f"front={self.d/(n + '.png')}")
        self.h = last_hash(self.ws)
    def tearDown(self): self.t.cleanup()
    def rev(self, name, rid, scores=None, who="independent"):
        crit = {c: {"score": (scores or {}).get(c, 2 + i % 2), "evidence": f"{name} saw detail {i} about {c.replace('_', ' ')} on the sheet."} for i, c in enumerate(CRITERIA)}
        (self.d / f"{name}.json").write_text(json.dumps({"reviewer": who, "reviewer_id": rid, "render_hash": self.h, "defects_fixed_since_last": ["x"], "criteria": crit}))
        return self.d / f"{name}.json"
    def gate(self, *paths):
        args = []
        for p in paths: args += ["--review", p]
        return run("gate", self.ws, *args)

    def test_one_review_is_not_enough_when_two_are_required(self):
        code, out = self.gate(self.rev("a", "r1")); self.assertEqual(code, 12); self.assertIn("needs 2", out)

    def test_two_distinct_reviewers_pass(self):
        code, out = self.gate(self.rev("a", "r1"), self.rev("b", "r2")); self.assertEqual(code, 0, out); self.assertIn("2 independent", out)

    def test_the_same_reviewer_cannot_count_twice(self):
        code, out = self.gate(self.rev("a", "r1"), self.rev("b", "r1")); self.assertEqual(code, 12); self.assertIn("distinct reviewer_id", out)

    def test_large_disagreement_blocks_the_pass(self):
        code, out = self.gate(self.rev("a", "r1", {"brows": 3}), self.rev("b", "r2", {"brows": 1}))
        self.assertEqual(code, 12); self.assertIn("disagree on 'brows'", out)

    def test_either_reviewer_scoring_low_blocks(self):
        code, out = self.gate(self.rev("a", "r1"), self.rev("b", "r2", {"face_structure": 1}))
        self.assertEqual(code, 12); self.assertIn("[review 2]", out)


class Consistency(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = pathlib.Path(self.t.name)
        self.ws = self.d / "ws"
    def tearDown(self): self.t.cleanup()
    def sized(self, name, h):
        im = Image.new("RGB", (400, 600), (230, 235, 240)); d = ImageDraw.Draw(im); top = 300 - h // 2
        d.ellipse([140, top, 260, top + h // 3], fill=(240, 200, 170), outline=(70, 40, 30), width=3)
        d.ellipse([190, top, 260, top + h // 3], fill=(200, 130, 90), outline=(70, 40, 30), width=3)
        d.rectangle([160, top + h // 3, 240, top + h], fill=(240, 200, 170), outline=(70, 40, 30), width=3)
        im.save(self.d / name)
    def test_same_height_views_pass_and_a_shorter_one_fails(self):
        for n, h in (("f.png", 420), ("s.png", 424), ("b.png", 418), ("short.png", 340)):
            self.sized(n, h)
        run("init", self.ws)
        code, out = run("measure", self.ws, "--view", f"front={self.d/'f.png'}", "--view", f"side={self.d/'s.png'}", "--view", f"back={self.d/'b.png'}")
        self.assertNotIn("height_consistency <FAIL", out)
        ws2 = self.d / "ws2"; run("init", ws2)
        code, out = run("measure", ws2, "--view", f"front={self.d/'f.png'}", "--view", f"side={self.d/'short.png'}")
        self.assertEqual(code, 12); self.assertIn("height_consistency", out)

    def test_a_single_view_has_nothing_to_compare(self):
        self.sized("f.png", 420); run("init", self.ws)
        code, out = run("measure", self.ws, "--view", f"front={self.d/'f.png'}")
        self.assertNotIn("height_consistency", out)


class HashIntegrity(unittest.TestCase):
    def test_render_hash_is_a_16_char_digest_and_multi_view_reruns_are_caught(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t)
            figure(d / "a.png"); figure(d / "b.png", tweak=1); figure(d / "ref.png")
            ws = d / "ws"; run("init", ws, "--ref", f"front={d/'ref.png'}")
            views = ["--view", f"front={d/'a.png'}", "--view", f"side={d/'b.png'}"]
            code, out = run("measure", ws, *views)
            h = last_hash(ws)
            self.assertRegex(h, r"^[0-9a-f]{16}$")
            self.assertIn(f"render_hash {h}", out)
            code, out = run("measure", ws, *views)          # identical second run with several views
            self.assertEqual(code, 12); self.assertIn("NO_CHANGE", out)

    def test_close_up_views_may_crop_the_shoulders(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t)
            im = Image.new("RGB", (400, 400), (230, 235, 240)); dr = ImageDraw.Draw(im)
            dr.ellipse([120, 60, 280, 260], fill=(240, 200, 170), outline=(70, 40, 30), width=3)
            dr.ellipse([200, 60, 280, 260], fill=(200, 130, 90), outline=(70, 40, 30), width=3)
            dr.rectangle([60, 250, 340, 400], fill=(60, 110, 70), outline=(30, 40, 30), width=3)   # shoulders run off the bottom edge
            im.save(d / "face.png"); im.save(d / "front.png")
            ws = d / "ws"; run("init", ws)
            _, out = run("measure", ws, "--view", f"face={d/'face.png'}", "--view", f"front={d/'front.png'}")
            self.assertIn("front:touches_border", out); self.assertNotIn("face:touches_border", out)


class SkillsInSync(unittest.TestCase):
    def test_skills_zips_and_contract_validate(self):
        r = subprocess.run([sys.executable, str(root / "scripts/validate_skills.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

if __name__ == "__main__":
    unittest.main()
