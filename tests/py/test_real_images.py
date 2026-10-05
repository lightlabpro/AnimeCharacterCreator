"""Real-image regression tests: the shipped floors against actual heads (tests/fixtures/validator).

The fixtures are 320px crops of Sammy's comparison image (reference head, two clay attempts, the toon attempt,
the MHS3 still) and two screenshots of the creator itself on its gradient backdrop.
"""
import importlib.util, pathlib, subprocess, sys, unittest
from PIL import Image

root = pathlib.Path(__file__).resolve().parents[2]
SK = root / ".claude/skills/render-validator/scripts"
FX = root / "tests/fixtures/validator"

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, SK / file); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
V = load("validate", "validate.py"); CAL = load("calibrate", "calibrate.py")
IM = {n: Image.open(FX / f"{n}.png") for n in ("ref_front", "old_front", "now_front", "toon_front", "mhs3", "app_face", "app_q")}

def passes_all(m):
    f, c = V.DEFAULTS["floors"], V.DEFAULTS["ceilings"]
    return all(m[k] >= f[k] for k in f) and m["contour_px"] <= c["contour_px"]

class Segmentation(unittest.TestCase):
    def test_creator_gradient_backdrop_is_not_mistaken_for_the_figure(self):
        for n in ("app_face", "app_q"):
            cov = V.normalise(IM[n])[2]["coverage"]
            self.assertTrue(0.25 < cov < 0.6, f"{n} coverage {cov:.2f}")

    def test_flat_backdrops_still_work(self):
        for n in ("ref_front", "now_front", "toon_front", "mhs3"):
            cov = V.normalise(IM[n])[2]["coverage"]
            self.assertTrue(0.25 < cov < 0.7, f"{n} coverage {cov:.2f}")

class ShippedFloorsOnRealHeads(unittest.TestCase):
    def test_perturbed_copies_of_a_head_pass(self):
        for base in ("ref_front", "now_front", "toon_front", "mhs3"):
            for kind, im in CAL.perturbations(IM[base]).items():
                m = CAL.measure(IM[base], im)
                self.assertTrue(passes_all(m), f"{base} {kind} wrongly failed: {m}")

    def test_different_heads_fail(self):
        for a, b in (("ref_front", "old_front"), ("ref_front", "now_front"), ("ref_front", "toon_front"),
                     ("ref_front", "mhs3"), ("toon_front", "mhs3"), ("now_front", "toon_front")):
            m = CAL.measure(IM[a], IM[b])
            self.assertFalse(passes_all(m), f"{a} vs {b} wrongly passed: {m}")

    def test_contour_distance_separates_better_than_iou(self):
        pos = [CAL.measure(IM[b], im) for b in ("ref_front", "now_front", "toon_front", "mhs3") for im in CAL.perturbations(IM[b]).values()]
        neg = [CAL.measure(IM[a], IM[b]) for a, b in (("ref_front", "old_front"), ("ref_front", "now_front"), ("ref_front", "toon_front"), ("ref_front", "mhs3"))]
        self.assertLess(max(p["contour_px"] for p in pos), min(n["contour_px"] for n in neg))
        self.assertGreater(min(p["edge_f"] for p in pos), max(n["edge_f"] for n in neg))

class ReferenceUsability(unittest.TestCase):
    LIM = V.DEFAULTS["reference_isolation"]
    def test_isolated_character_references_are_usable(self):
        for n in ("ref_front", "toon_front", "mhs3", "now_front"):
            self.assertTrue(V.reference_isolation(IM[n], self.LIM)[0], n)

    def test_a_full_game_screenshot_is_not_a_usable_reference(self):
        usable, cov, border = V.reference_isolation(Image.open(root / "docs/style_dataset/images/ref-01.png"), self.LIM)
        self.assertFalse(usable, f"coverage {cov:.2f} border {border:.2f}")

    def test_an_unusable_reference_makes_the_comparison_unknown_not_failed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            ws = pathlib.Path(t) / "ws"
            subprocess.run([sys.executable, str(SK / "validate.py"), "init", str(ws), "--ref", f"face={root / 'docs/style_dataset/images/ref-01.png'}"], capture_output=True)
            r = subprocess.run([sys.executable, str(SK / "validate.py"), "measure", str(ws), "--view", f"face={FX / 'toon_front.png'}"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 13, r.stdout); self.assertIn("not an isolated character", r.stdout)
            self.assertNotIn("contour_px", r.stdout)


class SkinShadow(unittest.TestCase):
    def check(self, rgb, mask):
        ss = V.skin_shadow(rgb, mask)
        if ss is None: return None
        hd = V.DEFAULTS["hard"]; lo, hi = hd["skin_shadow_hue"]
        return ss["chroma"] >= hd["skin_shadow_chroma_min"] and lo <= ss["hue"] <= hi

    def test_all_measured_mhs3_stills_with_skin_pass(self):
        import glob
        paths = sorted(glob.glob(str(root / "docs/reference/mhs3/*.p*")) + glob.glob(str(root / "docs/style_dataset/images/*")))
        judged = 0
        for p in paths:
            rgb, m, _ = V.normalise(Image.open(p)); r = self.check(rgb, m)
            if r is None: continue
            judged += 1; self.assertTrue(r, f"{p} fails the skin shadow gate: {V.skin_shadow(rgb, m)}")
        self.assertGreaterEqual(judged, 12)

    def test_the_good_toon_shader_passes_and_the_official_still_passes(self):
        for n in ("toon_front", "mhs3"):
            rgb, m, _ = V.normalise(IM[n]); self.assertTrue(self.check(rgb, m), n)

    def test_grey_clay_has_no_skin_to_judge(self):
        for n in ("ref_front", "now_front"):
            rgb, m, _ = V.normalise(IM[n]); self.assertIsNone(V.skin_shadow(rgb, m))

    def test_a_grey_shadow_on_skin_is_caught_by_the_whole_figure_gate(self):
        # The skin gate only sees skin-coloured pixels, so a grey shadow drops out of it. The whole-figure gate catches grey.
        import numpy as np
        img = np.zeros((200, 200, 3), np.uint8); img[:] = (230, 235, 240)
        img[40:160, 60:140] = (240, 200, 170); img[40:160, 100:140] = (165, 160, 155)
        rgb, m, _ = V.normalise(Image.fromarray(img))
        self.assertLess(V.toon_stats(rgb, m)["shadow_chroma"], V.DEFAULTS["hard"]["shadow_chroma_min"])

    def test_known_gap_a_green_or_blue_shadow_on_skin_passes_both_gates(self):
        # Documented limitation: it needs the independent review (shading_hard_warm_shadows). If this ever starts failing, a gate improved: update the docs.
        import numpy as np
        img = np.zeros((200, 200, 3), np.uint8); img[:] = (230, 235, 240)
        img[40:160, 60:140] = (240, 200, 170); img[40:160, 100:140] = (150, 185, 150)
        rgb, m, _ = V.normalise(Image.fromarray(img))
        self.assertGreaterEqual(V.toon_stats(rgb, m)["shadow_chroma"], V.DEFAULTS["hard"]["shadow_chroma_min"])

class CalibrationTool(unittest.TestCase):
    def test_reports_separation_and_proposes_floors(self):
        r = subprocess.run([sys.executable, str(SK / "calibrate.py"), "--ref", str(FX / "ref_front.png"), "--augment",
                            "--bad", str(FX / "old_front.png"), "--bad", str(FX / "mhs3.png")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("contour_px", r.stdout); self.assertIn("proposed", r.stdout)

    def test_flags_metrics_that_cannot_tell_two_near_identical_heads_apart(self):
        # Sammy's two clay attempts differ by under 1 px of outline, so calibrating one against the other must not pretend to separate them.
        r = subprocess.run([sys.executable, str(SK / "calibrate.py"), "--ref", str(FX / "old_front.png"), "--augment",
                            "--bad", str(FX / "now_front.png")], capture_output=True, text=True)
        self.assertIn("NOT USEFUL", r.stdout)
        self.assertIn('"floors": {}', r.stdout)

class RealIterationChange(unittest.TestCase):
    def test_the_last_clay_revision_was_a_tweak_not_a_fix(self):
        """The chat's 'last version' and 'now' clay heads. Both were judged bad against the reference, and they barely differ."""
        a, _, _ = V.normalise(IM["old_front"]); b, _, _ = V.normalise(IM["now_front"])
        ma, mb = V.normalise(IM["old_front"])[1], V.normalise(IM["now_front"])[1]
        self.assertLess(V.contour_px(ma, mb), V.DEFAULTS["micro_change_px"] * 1.5)

if __name__ == "__main__":
    unittest.main()
