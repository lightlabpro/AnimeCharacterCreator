import json, os, subprocess, sys, tempfile, unittest
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, ".claude", "skills", "body-proportion-audit", "scripts")
sys.path.insert(0, SCRIPTS); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skin_io, anatomy_rules as ar, pose_stress as ps, skinned_fixture as fx

def load(m, tmp, name="m.gltf"):
    p = os.path.join(tmp, name); fx.write_glb(m, p, True); return skin_io.orient(skin_io.load(p))

class Base(unittest.TestCase):
    def setUp(self): self._t = tempfile.TemporaryDirectory(); self.tmp = self._t.name
    def tearDown(self): self._t.cleanup()
    def rules(self, m): st, rows = ar.run(load(m, self.tmp)); return st, {r[0]: r for r in rows}

class Loader(Base):
    def test_orients_any_axis_and_forward(self):
        m = fx.build(); I = m["names"].index
        a = load(m, self.tmp)
        self.assertTrue(a["oriented"]); self.assertLess(a["jpos"][a["key"]["toe_L"]][1], a["jpos"][a["key"]["foot_L"]][1])    # toes in front = -Y
        self.assertGreater(a["jpos"][a["key"]["head"]][2], a["jpos"][a["key"]["foot_L"]][2])

    def test_sparse_accessor_decodes(self):
        g = {"accessors": [{"bufferView": 0, "componentType": 5126, "count": 4, "type": "VEC3",
                            "sparse": {"count": 2, "indices": {"bufferView": 1, "componentType": 5123}, "values": {"bufferView": 2}}}],
             "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 48}, {"buffer": 0, "byteOffset": 48, "byteLength": 4}, {"buffer": 0, "byteOffset": 52, "byteLength": 24}]}
        buf = np.zeros(12, np.float32).tobytes() + np.array([1, 3], np.uint16).tobytes() + np.array([[1, 2, 3], [4, 5, 6]], np.float32).tobytes()
        out = skin_io._read(g, [buf], 0)
        self.assertEqual(out.tolist(), [[0, 0, 0], [1, 2, 3], [0, 0, 0], [4, 5, 6]])

class Rules(Base):
    def test_good_figure_passes(self):
        st, r = self.rules(fx.build()); self.assertEqual(st, "pass", [v for v in r.values() if v[1] != "ok"])

    def test_four_fingers_fail(self):
        st, r = self.rules(fx.build(fingers=4)); self.assertEqual(r["fingers"][1], "fail"); self.assertIn("missing", r["fingers"][2])

    def test_unweighted_vertices_fail(self):
        st, r = self.rules(fx.build(drop_weights=5)); self.assertEqual(r["unweighted"][1], "fail"); self.assertEqual(st, "fail")

    def test_weights_not_summing_to_one_fail(self):
        m = fx.build(); m["W"] = m["W"] * 0.7
        st, r = self.rules(m); self.assertEqual(r["weight_sum"][1], "fail")

    def test_more_than_four_influences_fail(self):
        st, r = self.rules(fx.build(five_influences=True)); self.assertEqual(r["influences"][1], "fail")

    def test_cross_side_weights_fail(self):
        st, r = self.rules(fx.build(cross_side=True)); self.assertEqual(r["cross_side"][1], "fail")

    def test_finger_bleed_fails(self):
        st, r = self.rules(fx.build(finger_bleed=True)); self.assertEqual(r["finger_bleed"][1], "fail")

    def test_broken_chain_fails(self):
        m = fx.build(); i = m["names"].index
        m["parents"][i("DEF-shin.L")] = i("DEF-hips")
        st, r = self.rules(m); self.assertEqual(r["chain_order"][1], "fail"); self.assertIn("shin_L is not a child of thigh_L", r["chain_order"][2])

    def test_missing_neck_and_asymmetric_bones_fail(self):
        m = fx.build(); i = m["names"].index
        m["names"][i("DEF-neck")] = "DEF-bogus"; m["names"][i("DEF-forearm.R")] = "DEF-forearm_extra.R"
        st, r = self.rules(m); self.assertEqual(r["required_joints"][1], "fail"); self.assertEqual(r["bone_symmetry"][1], "fail")

    def test_no_skeleton_names_is_unknown_not_pass(self):
        m = fx.build(); m["names"] = [f"bone{i}" for i in range(len(m["names"]))]
        st, r = self.rules(m); self.assertEqual(r["required_joints"][1], "fail"); self.assertEqual(r["chain_order"][1], "unknown"); self.assertNotEqual(st, "pass")

    def test_finger_names_across_rigs(self):
        for n, want in (("Index finger_L.001", ("index", "L")), ("IndexFinger1_L_053", ("index", "L")), ("if2.L", ("index", "L")), ("t1.R", ("thumb", "R")),
                        ("Thumb0_L_050", ("thumb", "L")), ("Little finger_R.002", ("little", "R")), ("Index finger_L.002_end", None), ("DEF-hand.L", None), ("sf3.L", ("little", "L"))):
            self.assertEqual(ar.finger_of(n), want, n)

class Poses(Base):
    def test_smooth_weights_pass_elbow_and_knee_rigid_fail(self):
        good = ps.run_poses(load(fx.build(smooth=True), self.tmp))[1]; bad = ps.run_poses(load(fx.build(smooth=False), self.tmp, "r.gltf"))[1]
        pick = lambda rows, p: [r for r in rows if r[0].startswith(p)]
        for p in ("elbow_flex", "knee_flex"):
            self.assertTrue(all(r[1] == "ok" for r in pick(good, p)), pick(good, p)); self.assertTrue(all(r[1] == "fail" for r in pick(bad, p)), pick(bad, p))

    def test_joints_without_mesh_over_them_are_unknown(self):
        rows = ps.run_poses(load(fx.build(), self.tmp))[1]
        self.assertTrue(any(r[0].startswith("hip_flex") and r[1] == "unknown" for r in rows))

    def test_pose_direction_bends_the_right_way(self):
        m = load(fx.build(), self.tmp); k = m["key"]; p = m["jpos"][k["forearm_L"]]; d = m["jpos"][k["hand_L"]]
        R = ps.rodrigues([1, 0, 0], 90); moved = R @ (d - p)
        self.assertTrue(abs(moved[1]) > 0.1)                                    # rotation about x moves the hand along y

    def test_slider_sweep(self):
        st, rows = ps.run_sliders(load(fx.build(), self.tmp)); r = {x[0]: x for x in rows}
        self.assertEqual(r["ID-BodyBulk"][1], "ok"); self.assertEqual(r["ID-Inverted"][1], "fail"); self.assertEqual(r["ID-Spike"][1], "fail"); self.assertEqual(st, "fail")

    def test_slider_sweep_without_targets_is_unknown(self):
        m = load(fx.build(), self.tmp); m["targets"] = {}
        self.assertEqual(ps.run_sliders(m)[0], "unknown")

class Cli(Base):
    def run_cli(self, script, *a): return subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *a], capture_output=True, text=True)

    def test_exit_codes(self):
        good, bad = os.path.join(self.tmp, "g.gltf"), os.path.join(self.tmp, "b.gltf")
        fx.write_glb(fx.build(), good, True); fx.write_glb(fx.build(fingers=4), bad, True)
        self.assertEqual(self.run_cli("anatomy_rules.py", "check", good).returncode, 0)
        self.assertEqual(self.run_cli("anatomy_rules.py", "check", bad).returncode, 12)
        self.assertEqual(self.run_cli("anatomy_rules.py", "check", os.path.join(self.tmp, "none.gltf")).returncode, 2)
        self.assertEqual(self.run_cli("pose_stress.py", "sliders", good).returncode, 12)
        self.assertEqual(self.run_cli("pose_stress.py", "bogus", good).returncode, 2)

if __name__ == "__main__":
    unittest.main()
