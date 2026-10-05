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
