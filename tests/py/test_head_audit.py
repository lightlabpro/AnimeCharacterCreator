"""python3 -m unittest discover -s tests/py   (needs numpy)"""
import importlib.util, pathlib, unittest
import numpy as np

root = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ha", root / ".claude/skills/head-shape-audit/scripts/head_audit.py")
ha = importlib.util.module_from_spec(spec); spec.loader.exec_module(ha)

def ellipsoid(c, r, n=40000, seed=1):
    u = np.random.default_rng(seed).normal(size=(n, 3)); u /= np.linalg.norm(u, axis=1)[:, None]
    return np.array(c) + u * np.array(r)

def blender_head(rx):
    h = 0.234
    R = (0.39 * h * rx, 0.43 * h, 0.42 * h)
    jawC, jawR = (0, -0.3 * h, 0.1 * h), (0.18 * h, 0.27 * h, 0.36 * h)
    chinC = (0, jawC[1] - jawR[1] * 0.72, jawC[2] + jawR[2] * 0.55); chinR = (0.09 * h, 0.085 * h, 0.095 * h)
    noseC, noseR = (0, -0.25 * h, 0.5 * h), (0.03 * h, 0.04 * h, 0.1 * h)
    pts = np.vstack([ellipsoid((0, 0, 0), R), ellipsoid(jawC, jawR), ellipsoid(chinC, chinR), ellipsoid(noseC, noseR, 5000)])
    return np.stack([pts[:, 0], -pts[:, 2], pts[:, 1]], 1), R[1], chinC[1] - chinR[1]

class HeadAudit(unittest.TestCase):
    def test_wide_cranium_is_flagged(self):
        pts, top, chin = blender_head(1.0)
        bad, _ = ha.verdict(ha.profile_from_points(pts, top, chin, -1))
        self.assertIn("cranium_wide", bad)

    def test_narrowing_the_skull_brings_the_temple_row_into_tolerance(self):
        wide = ha.profile_from_points(*blender_head(1.0)[:1], blender_head(1.0)[1], blender_head(1.0)[2], -1)
        narrow = ha.profile_from_points(*blender_head(0.84)[:1], blender_head(0.84)[1], blender_head(0.84)[2], -1)
        want = ha.TARGETS["width"]["0.25"]
        self.assertGreater(abs(wide["width"]["0.25"] - want), ha.TOL)
        self.assertLess(abs(narrow["width"]["0.25"] - want), ha.TOL)

    def test_pure_ellipsoid_skull_is_widest_too_low(self):
        # A plain ellipsoid bulges at 0.3H while the reference is flat-sided from 0.2H to 0.35H.
        prof = ha.profile_from_points(*blender_head(0.84)[:1], blender_head(0.84)[1], blender_head(0.84)[2], -1)
        self.assertGreater(prof["width"]["0.3"], prof["width"]["0.2"] + 0.03)

    def test_scale_and_units_do_not_matter(self):
        pts, top, chin = blender_head(0.84)
        a = ha.profile_from_points(pts, top, chin, -1)
        b = ha.profile_from_points(pts * 7.5, top * 7.5, chin * 7.5, -1)
        self.assertEqual(a["width"]["0.25"], b["width"]["0.25"])

if __name__ == "__main__":
    unittest.main()
