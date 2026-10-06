import os, subprocess, sys, tempfile, unittest
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, ".claude", "skills", "ai-3d-pipeline", "scripts", "prepare_reference.py")
sys.path.insert(0, os.path.dirname(SCRIPT))
import prepare_reference as pr

def figure(size=(600, 800), box=(200, 100, 400, 700), bg=(30, 120, 200), mode="RGB"):
    im = Image.new("RGB", size, bg); ImageDraw.Draw(im).ellipse(box, fill=(240, 200, 80)); return im

class Prepare(unittest.TestCase):
    def test_flat_background_is_prepared_to_ratio_on_gray(self):
        out, r = pr.prepare(figure(), ratio=0.85, size=512)
        self.assertEqual(r["status"], "usable", r); self.assertEqual(out.size, (512, 512))
        a = np.asarray(out).astype(int); fg = (np.abs(a - 128).sum(2) > 30)
        ys, xs = np.where(fg); side = max(ys.max() - ys.min(), xs.max() - xs.min()) + 1
        self.assertAlmostEqual(side / 512, 0.85, delta=0.03)                                  # the subject's long side is 85% of the canvas
        self.assertEqual(tuple(a[2, 2]), (128, 128, 128))                                     # grey 0.5 background
        self.assertLess(abs((xs.min() + xs.max()) / 2 - 255.5), 4); self.assertLess(abs((ys.min() + ys.max()) / 2 - 255.5), 4)   # centred

    def test_white_background(self):
        out, r = pr.prepare(figure(), bg="white", size=256); self.assertEqual(tuple(np.asarray(out)[1, 1]), (255, 255, 255))

    def test_rgba_cutout_uses_alpha_even_on_busy_colours(self):
        rgb = np.random.default_rng(1).integers(0, 255, (600, 450, 3), np.uint8); a = np.zeros((600, 450), np.uint8); a[100:500, 80:360] = 255
        out, r = pr.prepare(Image.fromarray(np.dstack([rgb, a]), "RGBA"), size=256)
        self.assertEqual(r["status"], "usable", r); self.assertIn("used the alpha channel", r["notes"])

    def test_fully_opaque_rgba_is_not_a_cutout(self):
        im = figure().convert("RGBA"); self.assertFalse(pr.valid_alpha(np.asarray(im)[..., 3]))
        out, r = pr.prepare(im); self.assertEqual(r["status"], "usable")                      # falls back to the flat background

    def test_cut_off_subject_fails(self):
        out, r = pr.prepare(figure(box=(200, 100, 400, 800)))
        self.assertEqual(r["status"], "not_usable"); self.assertTrue(any("cut off" in p for p in r["problems"]))

    def test_tiny_subject_fails(self):
        out, r = pr.prepare(figure(size=(300, 300), box=(140, 140, 170, 170)))
        self.assertEqual(r["status"], "not_usable"); self.assertTrue(any("too small" in p for p in r["problems"]))

    def test_busy_background_is_unknown_never_guessed(self):
        noise = np.random.default_rng(2).integers(0, 255, (400, 400, 3), np.uint8)
        out, r = pr.prepare(Image.fromarray(noise)); self.assertEqual(r["status"], "unknown"); self.assertIsNone(out)

    def test_empty_image_fails(self):
        out, r = pr.prepare(Image.new("RGB", (400, 400), (10, 10, 10))); self.assertEqual(r["status"], "not_usable")

    def test_speckles_do_not_change_the_crop(self):
        im = figure(); d = ImageDraw.Draw(im); d.point((20, 20), fill=(255, 0, 0)); d.point((560, 760), fill=(255, 0, 0))
        out, r = pr.prepare(im); self.assertEqual(r["status"], "usable", r); self.assertEqual(r["subject_px"][1] // 10, 60)      # ~600 px tall, not the whole frame

    def test_big_image_is_downscaled(self):
        out, r = pr.prepare(figure(size=(3000, 4000), box=(1000, 500, 2000, 3500)), size=256); self.assertTrue(any("downscaled" in n for n in r["notes"]))

    def test_bad_ratio_is_a_usage_error(self):
        with self.assertRaises(ValueError): pr.prepare(figure(), ratio=2.0)

class Cli(unittest.TestCase):
    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            ok, cut, busy = (os.path.join(d, n) for n in ("ok.png", "cut.png", "busy.png"))
            figure().save(ok); figure(box=(200, 100, 400, 800)).save(cut)
            Image.fromarray(np.random.default_rng(3).integers(0, 255, (300, 300, 3), np.uint8)).save(busy)
            run = lambda *a: subprocess.run([sys.executable, SCRIPT, *a], capture_output=True, text=True).returncode
            self.assertEqual(run(ok, "--out", os.path.join(d, "o.png")), 0); self.assertTrue(os.path.exists(os.path.join(d, "o.png")))
            self.assertEqual(run(cut), 12); self.assertEqual(run(busy), 13)
            self.assertEqual(run(os.path.join(d, "none.png")), 2); self.assertEqual(run(ok, "--ratio", "5"), 2)

if __name__ == "__main__":
    unittest.main()
