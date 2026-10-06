import base64, json, os, struct, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from blender.validators import checks, gltf, judge, packs, reference, runner, sweep, vetting
from blender.validators.model import FAIL, PASS, WARN, Report, SceneInfo


def adult(height_heads=7.25, head=0.235):
    h = height_heads * head
    s = SceneInfo(kind="adult")
    m = s.markers
    m["LM-Floor"] = (0, 0, 0); m["LM-Crown"] = (0, 0, h); m["LM-Chin"] = (0, 0, h - head)
    m["LM-Nipple"] = (0, 0, h * 0.73); m["LM-Navel"] = (0, 0, h * 0.61); m["LM-Pubis"] = (0, 0, h * 0.5)
    m["LM-EyeInner_L"] = (0.02, -0.1, h - head * 0.55); m["LM-EyeInner_R"] = (-0.02, -0.1, h - head * 0.55)
    m["LM-EyeOuter_L"] = (0.06, -0.1, h - head * 0.55); m["LM-Mouth"] = (0, -0.1, h - head * 0.84)
    m["LM-shoulder_L"] = (0.235, 0, h * 0.8); m["LM-shoulder_R"] = (-0.235, 0, h * 0.8)
    m["LM-hip_L"] = (0.176, 0, h * 0.52); m["LM-hip_R"] = (-0.176, 0, h * 0.52)
    import math
    sx, sz = 0.235, h * 0.8
    m["LM-elbow_L"] = (sx + 0.30 * math.sin(math.radians(30)), 0, sz - 0.30 * math.cos(math.radians(30)))
    m["LM-wrist_L"] = (sx + 0.57 * math.sin(math.radians(30)), 0, sz - 0.57 * math.cos(math.radians(30)))
    m["LM-knee_L"] = (0.1, 0, h * 0.27); m["LM-ankle_L"] = (0.1, 0, h * 0.04)
    return s


class Anatomy(unittest.TestCase):
    def run_checks(self, s):
        r = Report(kind=s.kind); checks.anatomy(s, r); return r

    def test_good_adult_has_no_fail(self):
        r = self.run_checks(adult())
        self.assertTrue(r.ok, r.to_text())
        self.assertAlmostEqual(r.metrics["height_heads"], 7.25, places=2)

    def test_tall_adult_fails_with_fix(self):
        r = self.run_checks(adult(height_heads=8.6))
        f = [x for x in r.findings if x.check == "anatomy.height_heads"][0]
        self.assertEqual(f.severity, FAIL)
        self.assertIn("head_scale", f.fix)

    def test_child_height_band(self):
        s = adult(5.2); s.kind = "child"
        f = [x for x in self.run_checks(s).findings if x.check == "anatomy.height_heads"][0]
        self.assertEqual(f.severity, PASS)

    def test_missing_landmarks_are_skipped_not_guessed(self):
        s = SceneInfo(kind="adult"); s.markers["LM-Floor"] = (0, 0, 0)
        r = self.run_checks(s)
        self.assertTrue(any(f.severity == "skip" for f in r.findings))


class Contract(unittest.TestCase):
    def test_missing_sockets_and_keys_fail(self):
        s = SceneInfo(kind="adult", objects={"CHR_Armature", "CHR_Body"}, shape_keys={"CHR_Body": ["Basis", "ID-BodyBulk", "Bad"]},
                      tris={"CHR_Body": 22000})
        r = Report(kind="adult"); checks.contract(s, r)
        by = {f.check: f for f in r.findings}
        self.assertEqual(by["contract.sockets"].severity, FAIL)
        self.assertEqual(by["contract.key_prefix"].severity, FAIL)
        self.assertEqual(by["contract.keys"].severity, FAIL)
        self.assertEqual(by["contract.budget"].severity, PASS)

    def test_child_rejects_adult_keys(self):
        s = SceneInfo(kind="child", objects={"CHR_Armature_Child", "CHR_Body_Child"},
                      shape_keys={"CHR_Body_Child": ["Basis", "ID-MuscleAbs"]})
        r = Report(kind="child"); checks.contract(s, r)
        self.assertEqual({f.check: f for f in r.findings}["contract.child_keys"].severity, FAIL)


class Reference(unittest.TestCase):
    def test_envelope_flags_outlier(self):
        refs = [{"name": "a", "metrics": {"height_heads": 7.2}}, {"name": "b", "metrics": {"height_heads": 7.4}}]
        out = reference.compare({"height_heads": 8.2}, refs)
        self.assertEqual(out[0].severity, WARN)
        self.assertEqual(reference.compare({"height_heads": 7.3}, refs)[0].severity, PASS)

    def test_vetted_profile_keeps_only_confirmed_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            prof = {"name": "ref", "kind": "adult", "metrics": {"height_heads": 7.2, "legs_fraction": 0.48}}

            def fake(payload):  # confirms height, rejects legs
                return {"answers": {k: {"type": "noul", "noul": 0.9 if k == "height_heads" else 0.1}
                                    for k in payload["questions"]}}
            v = vetting.vet_profile(prof, fake)
            self.assertTrue(v["vetted"]["height_heads"]["kept"])
            self.assertFalse(v["vetted"]["legs_fraction"]["kept"])
            reference.save_profile(v, d)
            loaded = reference.load_profiles(d, "adult")
            self.assertEqual(list(loaded[0]["metrics"]), ["height_heads"])

    def test_hard_fail_never_kept_even_if_typesafe_says_yes(self):
        prof = {"name": "x", "kind": "adult", "metrics": {"height_heads": 12.0}}
        v = vetting.vet_profile(prof, lambda p: {"answers": {k: {"noul": 1.0} for k in p["questions"]}})
        self.assertFalse(v["vetted"]["height_heads"]["kept"])


class Judge(unittest.TestCase):
    def test_offline_is_skip(self):
        import urllib.error
        def boom(_): raise urllib.error.URLError("offline")
        r = Report(kind="adult", metrics={"height_heads": 7.2})
        self.assertEqual(judge.ask(r, boom)[0].severity, "skip")

    def test_confident_implausible_overrules_a_deterministic_pass(self):
        r = Report(kind="adult", metrics={"height_heads": 7.2})
        t = lambda p: {"answers": {"plausible": {"noul": 0.1}, "quality": {"score": 1.0, "confidence": 0.9},
                                   "first_fix": {"choice": "proportion", "confidence": 0.8}}}
        sev = {f.check: f.severity for f in judge.ask(r, t)}
        self.assertEqual(sev["judge.plausible"], FAIL)


class Sweep(unittest.TestCase):
    def test_arm_slider_exempt_from_wrist_rule(self):
        res = {"upper_arm_length": {1.0: {"wrist_to_crotch_heads": -0.9}}, "ID-BodyBulk": {1.0: {"wrist_to_crotch_heads": -0.9}}}
        by = {f.check: f.severity for f in sweep.check("adult", res)}
        self.assertEqual(by["sweep.upper_arm_length"], PASS)
        self.assertEqual(by["sweep.ID-BodyBulk"], FAIL)


class Packs(unittest.TestCase):
    def test_library_rules(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "humanoid", "hair", "bob"); os.makedirs(p)
            json.dump({"id": "hair-bob", "display_name": "Rathalos Bob", "library": "robot", "slot": "hair"}, open(os.path.join(p, "pack.json"), "w"))
            json.dump({"packs": []}, open(os.path.join(d, "manifest.json"), "w"))
            r = Report(kind="library"); packs.validate_library(d, r)
            checks_ = {f.check for f in r.findings if f.severity == FAIL}
            self.assertTrue({"pack.library", "pack.manifest", "pack.gltf", "pack.names"} <= checks_)


class Gltf(unittest.TestCase):
    def test_reads_markers_bones_and_tris(self):
        doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0, 1]}],
               "nodes": [{"name": "LM-Crown", "translation": [0, 1.7, 0]}, {"name": "CHR_Body", "mesh": 0}],
               "meshes": [{"name": "CHR_Body", "extras": {"targetNames": ["ID-BodyBulk"]},
                           "primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
               "accessors": [{"bufferView": 0, "count": 3, "componentType": 5126, "type": "VEC3"},
                         {"count": 6, "componentType": 5123, "type": "SCALAR"}],
               "bufferViews": [{"buffer": 0, "byteLength": 36}],
               "buffers": [{"byteLength": 36, "uri": "data:application/octet-stream;base64," +
                            base64.b64encode(struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)).decode()}]}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a.gltf"); json.dump(doc, open(path, "w"))
            s = gltf.scene_from_gltf(path, "adult")
            self.assertEqual(s.markers["LM-Crown"], (0, 0, 1.7))  # glTF +Y becomes Blender +Z
            self.assertEqual(s.tris["CHR_Body"], 2)
            self.assertEqual(len(s.body_verts), 3)
            self.assertEqual(s.shape_keys["CHR_Body"], ["Basis", "ID-BodyBulk"])


class Silhouette(unittest.TestCase):
    def test_wider_shoulders_reported(self):
        import numpy as np
        from blender.validators import silhouette
        ref = np.zeros((200, 120), bool); ref[:, 55:65] = True; ref[30:50, 40:80] = True
        cand = ref.copy(); cand[30:50, 20:100] = True
        out = silhouette.compare(cand, ref, "front")
        self.assertTrue(any("wider" in f.message for f in out))
        self.assertEqual(silhouette.compare(ref, ref, "front")[0].severity, PASS)


class EndToEnd(unittest.TestCase):
    def test_evaluate_with_reference_and_judge(self):
        with tempfile.TemporaryDirectory() as d:
            reference.save_profile(reference.profile_from_scene(adult(7.2), "good"), d)
            t = lambda p: {"answers": {"plausible": {"noul": 0.9}, "quality": {"score": 3.0, "confidence": 0.9},
                                       "first_fix": {"choice": "none", "confidence": 0.9}}}
            r = runner.evaluate(adult(7.3), "t", profiles_dir=d, use_judge=True, transport=t)
            self.assertTrue(any(f.check.startswith("reference.") and f.severity == PASS for f in r.findings))
            self.assertTrue(any(f.check == "judge.plausible" and f.severity == PASS for f in r.findings))


class Geometry(unittest.TestCase):
    def cube(self, off=0.0):
        import numpy as np
        v = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], float) + off
        f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        return v, f

    def test_closed_cube_is_healthy(self):
        from blender.validators import geometry
        v, f = self.cube()
        h = geometry.hygiene(v, f)
        self.assertEqual((h["boundary_edges"], h["nonmanifold_edges"], h["components"]), (0, 0, 1))

    def test_three_faces_on_one_edge_is_nonmanifold_and_floater_found(self):
        import numpy as np
        from blender.validators import geometry
        v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0, -1, 0], [5, 5, 5], [6, 5, 5], [5, 6, 5]], float)
        f = [(0, 1, 2), (0, 1, 3), (0, 1, 4)] + [(5, 6, 7)] * 0
        h = geometry.hygiene(v, f + [(5, 6, 7)], min_component_frac=0.5)
        self.assertEqual(h["nonmanifold_edges"], 1)
        self.assertEqual(h["floaters"], 1)
        multi = {x.check for x in geometry.hygiene_findings(h, "hair", multi_part=True)}
        self.assertNotIn("hygiene.hair.floaters", multi)

    def test_f1_perfect_and_shifted(self):
        import numpy as np
        from blender.validators import geometry
        rng = np.random.default_rng(1)
        p = rng.random((800, 3)) * [0.4, 0.2, 1.0]
        self.assertGreater(geometry.chamfer_f1(geometry.normalise(p), geometry.normalise(p))["f1@0.01"], 0.99)
        shifted = p + [0.0, 0.0, 0.0]
        shifted[:, 0] *= 1.5
        self.assertLess(geometry.chamfer_f1(geometry.normalise(p), geometry.normalise(shifted))["f1@0.01"], 0.9)

    def test_mirror_symmetry_detects_asymmetry(self):
        import numpy as np
        from blender.validators import geometry
        rng = np.random.default_rng(2)
        half = rng.random((600, 3)) * [0.3, 0.2, 1.0]
        sym = np.vstack([half, half * [-1, 1, 1]])
        self.assertLess(geometry.mirror_symmetry(sym), 0.01)
        lopsided = np.vstack([sym, sym[:200] + [0.4, 0, 0]])
        self.assertGreater(geometry.mirror_symmetry(lopsided), 0.01)


class VrmAndBuckets(unittest.TestCase):
    def test_vrm0_humanoid_map_gives_exact_landmarks(self):
        doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}],
               "nodes": [{"name": "Hips", "children": [1, 2]}, {"name": "x", "translation": [0.1, 1.3, 0]},
                         {"name": "y", "translation": [0.1, 0.9, 0]}],
               "extensions": {"VRM": {"humanoid": {"humanBones": [{"bone": "leftUpperArm", "node": 1},
                                                                    {"bone": "leftUpperLeg", "node": 2}]}}}}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a.vrm.gltf")
            with open(path, "w") as fh:
                json.dump(doc, fh)
            s = gltf.scene_from_gltf(path, "adult")
        self.assertAlmostEqual(s.markers["LM-shoulder_L"][2], 1.3)
        self.assertAlmostEqual(s.markers["LM-hip_L"][2], 0.9)

    def test_buckets_use_words(self):
        from blender.validators.spec import bucket
        self.assertEqual(bucket("height_heads", 7.2, "adult"), "in range")
        self.assertEqual(bucket("height_heads", 8.6, "adult"), "far too high")
        self.assertEqual(bucket("height_heads", 7.6, "adult"), "slightly high")
        st = judge.build_state(Report(kind="adult", metrics={"height_heads": 8.6}))
        self.assertEqual(st["readings"][0]["reading"], "far too high")
        self.assertNotIn("8.6", json.dumps(st))

    def test_low_confidence_score_is_routed_not_decided(self):
        r = Report(kind="adult", metrics={"height_heads": 7.2})
        t = lambda p: {"answers": {"plausible": {"noul": 0.9}, "quality": {"score": 1.0, "confidence": 0.1},
                                   "first_fix": {"choice": "none", "confidence": 0.9}}}
        checks_ = {f.check: f.severity for f in judge.ask(r, t)}
        self.assertEqual(checks_["judge.review"], "info")
        self.assertNotIn("judge.quality", checks_)


if __name__ == "__main__":
    unittest.main()
