import json, os, sys, unittest
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from blender.validators import (accessory, archetype, beast, clothing, expression_map, face, quadruped, region_judge, regions,
                                rig, standard_mapper, standards)
from blender.validators.model import FAIL, INFO, PASS, SKIP, WARN, Finding, Report


class Standards(unittest.TestCase):
    def test_counts_match_the_specs(self):
        self.assertEqual(len(standards.VRM_HUMANOID), 55)            # VRM 1.0 humanoid spec
        self.assertEqual(sum(len(v) for v in standards.ARKIT_52.values()), 52)
        required = [k for k, (r, _) in standards.VRM_HUMANOID.items() if r]
        self.assertEqual(len(required), 15)                           # hips, spine, head, 2x(arm 3 + leg 3) = 15
        self.assertEqual(len(standards.OCULUS_VISEMES), 15)

    def test_every_region_in_the_standards_exists_in_the_registry_or_is_face_part(self):
        for r in ("brows", "eyes", "nose", "mouth", "cheeks", "jaw"):
            self.assertIn(r, regions.REGIONS)
        for _, (_, region) in standards.VRM_HUMANOID.items():
            self.assertIn(region, regions.REGIONS)


class Expressions(unittest.TestCase):
    def test_rules_cover_project_vrchat_and_standard_names(self):
        d = expression_map.deterministic
        self.assertEqual(d("PF-Blink_L"), "eyeBlinkLeft")
        self.assertEqual(d("vrc.v_aa"), "aa")
        self.assertEqual(d("jawOpen"), "jawOpen")
        self.assertEqual(d("Blink R"), "eyeBlinkRight")
        self.assertIsNone(d("Corrective_Elbow"))

    def test_oculus_visemes_are_recognised_and_not_listed_as_unmapped(self):
        m = expression_map.map_keys(["vrc.v_ch", "vrc.v_dd", "PF-VisFV", "Weird"], transport=None)
        self.assertEqual(m["vrc.v_ch"][1], "rule")
        self.assertEqual(m["Weird"][1], "unmapped")
        cov = expression_map.coverage(m)
        self.assertEqual(cov["visemes (Oculus 15)"][0], 3)  # CH, DD, FF

    def test_typesafe_fallback_needs_agreement_in_both_orders(self):
        calls = []

        def fake(payload):
            calls.append(payload)
            n = len(payload["questions"])
            first_region = "mouth" if len(calls) <= 2 else None
            ans = {}
            for i in range(n):
                crit = list(payload["questions"][f"i{i}"]["criteria"])
                pick = "mouth" if "mouth" in crit else ("aa" if "aa" in crit else crit[0])
                ans[f"i{i}"] = {"type": "choice", "choice": pick, "confidence": 0.9, "probabilities": {c: 0.0 for c in crit}}
            return {"answers": ans}
        out = standard_mapper.map_to_options(["MyOpenShape"], expression_map._region_options(), "facial shape key", fake)
        self.assertEqual(out["MyOpenShape"][1], "typesafe")
        self.assertEqual(len(calls), 4)  # region x2 orders, name x2 orders


class Rig(unittest.TestCase):
    def test_names_from_four_rig_conventions(self):
        v = rig.vrm_name
        self.assertEqual(v("Left arm"), "leftUpperArm")
        self.assertEqual(v("Left Leg"), "leftUpperLeg")
        self.assertEqual(v("DEF-spine"), "hips")
        self.assertEqual(v("Spine"), "spine")
        self.assertEqual(v("DEF-f_index.02.L"), "leftIndexIntermediate")
        self.assertEqual(v("Index finger_L.002"), "leftIndexDistal")
        self.assertEqual(v("mixamorig:LeftUpLeg"), "leftUpperLeg")
        self.assertEqual(v("mixamorig:LeftLeg"), "leftLowerLeg")
        self.assertIsNone(v("Left toe_end"))

    def test_missing_required_bones_and_duplicates_and_hierarchy(self):
        bones = ["Hips", "Spine", "Head", "Left arm", "Left elbow", "Left wrist", "Left eye", "LeftEye"]
        parents = {"Hips": None, "Spine": "Hips", "Head": "Spine", "Left arm": "Spine", "Left elbow": "Left arm", "Left wrist": "Left elbow",
                   "Left eye": "Head", "LeftEye": "Head"}
        m = rig.map_bones(bones)
        f = {x.check: x for x in rig.findings(m, parents, "t")}
        self.assertEqual(f["legs.rig.required"].severity, FAIL)          # no leg bones
        self.assertEqual(f["body.rig.duplicates"].severity, WARN)         # two left-eye bones
        self.assertEqual(f["body.rig.hierarchy"].severity, PASS)
        bad = dict(parents, **{"Left arm": "Head"})  # arm under head is wrong
        self.assertEqual({x.check: x for x in rig.findings(m, bad, "t")}["body.rig.hierarchy"].severity, FAIL)


def head_mesh():
    """Ellipsoid head, chin at z=0, crown at z=1, with a small nose bump on the front (-Y)."""
    u, v = np.meshgrid(np.linspace(0.05, np.pi - 0.05, 40), np.linspace(0, 2 * np.pi, 48, endpoint=False))
    p = np.stack([0.4 * np.sin(u) * np.cos(v), 0.4 * np.sin(u) * np.sin(v), 0.5 + 0.5 * np.cos(u)], -1).reshape(-1, 3)
    bump = (np.abs(p[:, 0]) < 0.05) & (np.abs(p[:, 2] - 0.3) < 0.05) & (p[:, 1] < 0)
    p[bump, 1] -= 0.06
    return p


class Face(unittest.TestCase):
    def sphere(self, c, r=0.04, n=200):
        rng = np.random.default_rng(3)
        d = rng.normal(size=(n, 3))
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        return np.asarray(c) + d * r

    def test_spherical_eyes_pass_and_flat_discs_fail_roundness(self):
        lm = {"Crown": (0, 0, 1.0), "Chin": (0, 0, 0.0), "EyeInner_L": (0.1, -0.3, 0.45), "EyeOuter_L": (0.2, -0.3, 0.45)}
        good = {"eye_L": (self.sphere((0.15, -0.3, 0.45)), []), "eye_R": (self.sphere((-0.15, -0.3, 0.45)), [])}
        m = face.metrics(good, head_mesh(), lm)
        self.assertGreater(m["eyeball_roundness"], 0.8)
        flat = {k: (v[0] * [1, 0.1, 1], []) for k, v in good.items()}
        m2 = face.metrics(flat, head_mesh(), lm)
        sev = {f.check: f.severity for f in face.findings(m2, flat, "t")}
        self.assertEqual(sev["eyes.eyeball.eyeball_roundness"], "fail")

    def test_eye_symmetry_ignores_head_yaw(self):
        lm = {"Crown": (0, 0, 1.0), "Chin": (0, 0, 0.0), "EyeInner_L": (0.1, -0.3, 0.45), "EyeOuter_L": (0.2, -0.3, 0.45)}
        parts = {"eye_L": (self.sphere((0.15, -0.34, 0.45)), []), "eye_R": (self.sphere((-0.15, -0.26, 0.45)), [])}  # yawed head
        m = face.metrics(parts, head_mesh(), lm)
        self.assertLess(m["eye_pair_asymmetry_z"], 0.01)
        self.assertGreater(m["head_yaw_degrees"], 5)

    def test_nose_protrusion_is_measured_against_the_face_plane(self):
        lm = {"Crown": (0, 0, 1.0), "Chin": (0, 0, 0.0), "EyeInner_L": (0.1, -0.3, 0.55), "EyeOuter_L": (0.2, -0.3, 0.55)}
        m = face.metrics({}, head_mesh(), lm)
        self.assertIn("nose_protrusion_over_head_height", m)
        self.assertGreater(m["nose_protrusion_over_head_height"], 0.02)

    def test_brow_geometry_needs_enough_vertices_per_side(self):
        lm = {"Crown": (0, 0, 1.0), "Chin": (0, 0, 0.0)}
        few = np.array([[0.1, -0.3, 0.6], [0.2, -0.3, 0.6], [-0.1, -0.3, 0.6], [-0.2, -0.3, 0.6]])
        m = face.metrics({"brows": (few, [])}, None, lm)
        self.assertEqual({f.check: f.severity for f in face.findings(m, {"brows": 1}, "t")}["brows.bendability.brow_verts_per_side"], "fail")


def sphere_body(r=0.5, n=40):
    u, v = np.meshgrid(np.linspace(0.05, np.pi - 0.05, n), np.linspace(0, 2 * np.pi, n * 2, endpoint=False))
    p = np.stack([r * np.sin(u) * np.cos(v), r * np.sin(u) * np.sin(v), r * np.cos(u)], -1).reshape(-1, 3)
    faces = []
    W = n * 2
    for i in range(n - 1):
        for j in range(W):
            a, b = i * W + j, i * W + (j + 1) % W
            faces.append((a, (i + 1) * W + j, (i + 1) * W + (j + 1) % W, b))
    return p, faces


class Clothing(unittest.TestCase):
    def test_garment_outside_vs_inside_the_body(self):
        body, faces = sphere_body()
        outside = body * 1.03
        inside = body * 0.9
        self.assertLess(clothing.fit(outside, body, faces, 1.0)["penetration_fraction"], 0.05)
        self.assertGreater(clothing.fit(inside, body, faces, 1.0)["penetration_fraction"], 0.9)
        self.assertEqual({f.check: f.severity for f in clothing.findings("c", clothing.fit(inside, body, faces, 1.0), None, None, "t")}["clothing.fit.penetration"], "fail")

    def test_skinning_agreement_and_unweighted(self):
        s = clothing.skin_agreement(["arm", "arm", None, "leg"], ["arm", "arm", "leg", "leg"], np.array([0, 1, 2, 3]))
        self.assertAlmostEqual(s["unweighted_fraction"], 0.25)
        self.assertEqual(s["skin_match"], 1.0)

    def test_manifest_contract(self):
        full = {k: "x" for k in clothing.CONTRACT_FIELDS}
        full.update({"type": "deform", "follows_shape_keys": ["ID-Chest"], "socket": "SOC-Chest"})
        self.assertTrue(all(f.severity == PASS for f in clothing.contract_findings(full, "g", ["ID-Chest"])))
        bad = clothing.contract_findings({"id": "g", "type": "replacement"}, "g")
        self.assertTrue(any(f.severity == FAIL for f in bad))
        self.assertEqual([f for f in clothing.contract_findings(dict(full, follows_shape_keys=["ID-Nope"]), "g", ["ID-Chest"]) if f.check.endswith("follows")][0].severity, FAIL)


class Accessories(unittest.TestCase):
    lm = {"Crown": (0, 0, 1.7), "Chin": (0, 0, 1.45), "Floor": (0, 0, 0), "EyeInner_L": (0.03, -0.1, 1.58), "EyeOuter_L": (0.07, -0.1, 1.58),
          "HeelBack_L": (0, 0.05, 0), "ToeTip_L": (0, -0.2, 0), "wrist_R": (-0.5, 0, 0.8)}

    def box(self, c, e, n=60):
        rng = np.random.default_rng(0)
        return np.asarray(c) + (rng.random((n, 3)) - 0.5) * e

    def test_eyewear_on_the_eye_line_passes_and_on_the_forehead_fails(self):
        ok = accessory.metrics("eyewear", self.box((0, -0.11, 1.58), (0.15, 0.03, 0.04)), self.lm, 0.16)
        bad = accessory.metrics("eyewear", self.box((0, -0.11, 1.68), (0.15, 0.03, 0.04)), self.lm, 0.16)
        self.assertTrue(all(f.severity == PASS for f in accessory.findings("eyewear", ok, "g", "SOC-Eyewear")))
        self.assertNotEqual({f.check: f.severity for f in accessory.findings("eyewear", bad, "g", "SOC-Eyewear")}["accessory.scale.centre_vs_eye_line"], PASS)

    def test_socket_parent_is_checked(self):
        f = accessory.findings("belt", {}, "b", "CHR_Body")
        self.assertEqual(f[0].severity, FAIL)

    def test_weapon_grip_distance_from_the_hand(self):
        near = accessory.metrics("weapon_melee", self.box((-0.5, 0, 0.9), (0.05, 0.05, 0.6)), self.lm)
        far = accessory.metrics("weapon_melee", self.box((0.6, 0, 0.9), (0.05, 0.05, 0.6)), self.lm)
        self.assertLess(near["nearest_point_to_hand_over_head"], far["nearest_point_to_hand_over_head"])


class Beast(unittest.TestCase):
    def test_manual_numbers(self):
        self.assertAlmostEqual(beast.mouth_corner_reach((0, 0, 0), (2, 0, 0), (3, 0, 0)), 2 / 3, places=6)
        self.assertEqual(beast.BANDS["mouth_corner_reach"].grade(2 / 3), PASS)
        self.assertLess(beast.heel_ratio((0, 0, 0.0), (0.2, 0, 0), 0.0), 0.12)            # plantigrade
        self.assertGreater(beast.heel_ratio((0, 0, 0.12), (0.2, 0, 0), 0.0), 0.25)         # digitigrade: raised heel

    def test_taper_and_symmetry_and_base(self):
        t = np.linspace(0, 1, 400)
        cone = np.stack([(1 - 0.8 * t) * np.cos(t * 80), (1 - 0.8 * t) * np.sin(t * 80), t * 5], -1)
        self.assertGreater(beast.taper_score(beast.radius_profile(cone, (0, 0, 0), (0, 0, 5))), 0.85)
        bulge = np.stack([(1 + np.sin(t * 12)) * np.cos(t * 80), (1 + np.sin(t * 12)) * np.sin(t * 80), t * 5], -1)
        self.assertLess(beast.taper_score(beast.radius_profile(bulge, (0, 0, 0), (0, 0, 5))), 0.8)
        left = np.random.default_rng(1).random((200, 3))
        right = left * [-1, 1, 1]
        self.assertLess(beast.pair_symmetry(left, right, 1.0), 1e-6)
        self.assertGreater(beast.pair_symmetry(left, right + [0.3, 0, 0], 1.0), 0.1)

    def test_recipes_and_findings(self):
        self.assertEqual(beast.recipe_findings("rabbit", {"ears": "long", "muzzle": "lagomorph", "tail": "puff"})[0].severity, PASS)
        self.assertEqual(beast.recipe_findings("rabbit", {"ears": "human", "muzzle": "lagomorph", "tail": "puff"})[0].severity, FAIL)
        f = {x.check: x for x in beast.findings({"heel_ratio": 0.02}, "t", "digitigrade")}
        self.assertEqual(f["feet.stance.heel_ratio"].severity, FAIL)  # digitigrade needs a raised heel


class Quadruped(unittest.TestCase):
    def build(self, fore_heavy):
        # a box torso plus a head mass over the fore or hind feet
        torso = np.array([[x, y, z] for x in (-0.5, 0.5) for y in np.linspace(-1, 1, 9) for z in (1.0, 2.0)], float)
        faces = [(i, i + 1, i + 3, i + 2) for i in range(0, len(torso) - 3, 2)]
        heavy = np.array([[x, y, z] for x in (-0.3, 0.3) for y in (-1.2 if fore_heavy else 1.2, -1.1 if fore_heavy else 1.1) for z in (1.0, 1.5)], float)
        v = np.vstack([torso, heavy] * (4 if fore_heavy else 1))
        f = faces + [(len(torso) + i, len(torso) + i + 1, len(torso) + i + 3, len(torso) + i + 2) for i in range(0, len(heavy) - 3, 2)]
        return v, f

    def test_weight_bias_follows_the_mass(self):
        lm = {"FootFront_L": (0.4, -0.9, 0), "FootFront_R": (-0.4, -0.9, 0), "FootHind_L": (0.4, 0.9, 0), "FootHind_R": (-0.4, 0.9, 0),
              "shoulder_L": (0.4, -0.8, 1.8), "Floor": (0, 0, 0)}
        v, f = self.build(True)
        heavy_front = quadruped.metrics(v, f, lm)["fore_weight_fraction"]
        v2, f2 = self.build(False)
        heavy_back = quadruped.metrics(v2, f2, lm)["fore_weight_fraction"]
        self.assertGreater(heavy_front, heavy_back)

    def test_leg_and_wing_checks(self):
        lm = {"FootFront_L": (0.4, -0.9, 0), "FootFront_R": (-0.4, -0.9, 0), "FootHind_L": (0.4, 0.9, 0), "FootHind_R": (-0.4, 0.9, 0),
              "shoulder_L": (0.4, -0.8, 2.0), "Floor": (0, 0, 0), "Belly": (0, 0, 1.0), "elbow_L": (0.4, -0.8, 1.05), "knee_L": (0.4, 0.8, 1.4),
              "wrist_L": (0.4, -0.9, 0.5), "ankle_hind_L": (0.4, 0.9, 0.55), "WingRoot_L": (0.3, -0.2, 2.3)}
        m = quadruped.metrics(*self.build(True), lm)
        sev = {f.check.split(".")[-1]: f.severity for f in quadruped.findings(m, "t")}
        self.assertEqual(sev["elbow_belly_gap"], PASS)
        self.assertNotEqual(sev["knee_belly_gap"], PASS)       # knee well above the belly line
        self.assertEqual(sev["wrist_height_mismatch"], PASS)
        self.assertEqual(sev["wing_root_above_shoulder"], PASS)


class Archetype(unittest.TestCase):
    def fake(self, top, second="dragon", p_top=0.8, p_second=0.1):
        def f(payload):
            crit = list(payload["questions"]["archetype"]["criteria"])
            probs = {c: (1 - p_top - p_second) / (len(crit) - 2) for c in crit}
            probs[top], probs[second] = p_top, p_second
            return {"answers": {"archetype": {"type": "choice", "choice": top, "confidence": 0.8, "probabilities": probs}}}
        return f

    def test_absent_traits_are_stated(self):
        d = archetype.describe({"muzzle": "reptile", "tail": "lizard"})
        self.assertEqual(d["horns"], "no horns")
        self.assertEqual(d["wings"], "no wings")

    def test_verdicts(self):
        self.assertEqual(archetype.classify({"muzzle": "reptile"}, "lizard", self.fake("lizard"))[-1].severity, PASS)
        self.assertEqual(archetype.classify({"muzzle": "reptile"}, "lizard", self.fake("dragon", "lizard"))[-1].severity, FAIL)
        self.assertEqual(archetype.classify({"muzzle": "reptile"}, "lizard", self.fake("lizard", "dragon", 0.45, 0.35))[-1].severity, WARN)


class RegionsAndJudge(unittest.TestCase):
    def test_every_check_routes_to_a_region_and_the_table_counts(self):
        r = Report(kind="adult")
        r.add(Finding("anatomy.eye_gap_eye_widths", FAIL, "m"), Finding("hair.x.clumps", PASS, "m"), Finding("brows.shape.parts", SKIP, "m"),
              Finding("topology.x.quads", WARN, "m"), Finding("clothing.fit.penetration", PASS, "m"))
        rows = {x[0]: x for x in regions.region_table(r)}
        self.assertEqual(rows["eyes"][2], 1)
        self.assertIn("hair", rows)
        self.assertIn("brows", rows)
        self.assertIn("clothing", rows)
        self.assertEqual(rows["body"][3], 1)

    def test_region_state_has_words_not_numbers_and_choice_has_none(self):
        fs = [Finding("nose.protrusion.nose_protrusion_over_head_height", INFO, "t: nose protrusion", 0.109),
              Finding("anatomy.height_heads", PASS, "t: height", 7.2)]
        env = {"nose_protrusion_over_head_height": (0.10, 0.12)}
        st = region_judge.build_state("nose", fs[:1], env)
        s = json.dumps(st)
        self.assertNotIn("0.109", s)
        self.assertIn("within the reference models", s)
        qs = region_judge.questions("nose", fs[:1])
        self.assertIn("none", qs["first_fix"]["criteria"])
        self.assertEqual(list(region_judge.questions("nose", fs[:1], 1)["first_fix"]["criteria"]), list(qs["first_fix"]["criteria"])[::-1])

    def test_uncertain_and_low_confidence_become_review(self):
        fs = [Finding("eyes.eyeball.x", FAIL, "t: x", 0.2, "<= 1")]
        out = region_judge.judge_region("eyes", fs, {}, lambda p: {"answers": {"region_ok": {"noul": 0.5}, "matches_target": {"noul": 0.95},
              "quality": {"score": 1.0, "confidence": 0.1}, "first_fix": {"choice": "none", "confidence": 1.0}}})
        sev = {x.check.split(".")[-1]: x.severity for x in out}
        self.assertEqual(sev["region_ok"], "info")
        self.assertEqual(sev["matches_target"], "pass")
        self.assertEqual(sev["quality"], "info")


class AppContract(unittest.TestCase):
    def test_scanner_keeps_morphs_before_a_nested_brace(self):
        from blender.validators import app_contract as ac
        line = "  c('x', 'L', 'h', P, { bi: true, region: 'eyes', morph: 'ID-A', morphNeg: 'ID-A_Neg', pathFor: { adult: PRES }, needsLook: { slot: 's', not: ['none'] } }),"
        o = ac._options_object(line)
        self.assertIn("ID-A_Neg", o)
        self.assertTrue(o.startswith("{") and o.endswith("}"))

    def test_reads_the_real_app_source(self):
        from blender.validators import app_contract as ac
        cs = ac.parse_controls()
        self.assertGreater(len(cs), 100)
        morphs = {c.morph for c in cs if c.morph} | {c.morph_neg for c in cs if c.morph_neg}
        for key in ("ID-FaceRound", "ID-NarrowWaist_Neg", "ID-SkullWidth", "ID-MuzzleLength_Neg", "ID-EarElSize"):  # one before a nested brace, one after
            self.assertIn(key, morphs)
        req = ac.required("adult", cs)
        self.assertEqual(req["morph"]["ID-SkullWidth"], "skull")
        self.assertNotIn("ID-SnoutLong", req["morph"])              # beast-only
        self.assertIn("ID-SnoutLong", ac.required("dragon", cs)["morph"])
        self.assertIn("PF-Blink_L", ac.parse_pf_keys())

    def test_gap_and_coverage_for_a_library_built_exactly_to_the_prompt(self):
        from blender.validators import app_contract as ac, contract
        gap = ac.contract_gap()
        self.assertIn("ID-SkullWidth", gap["named_nowhere_in_prompt"])
        self.assertIn("ID-Chest_Neg", gap["neg_counterparts"])
        keys = set(contract.ADULT_BODY_KEYS) | set(contract.ADULT_FACE_KEYS) | set(contract.PERFORMANCE_KEYS)
        cov = ac.coverage(keys, set(), "adult")
        self.assertEqual(cov["skull"]["morph"][0], 0)            # the prompt names no skull keys
        self.assertEqual(cov["muzzle"]["morph"][0], 0)
        f = {x.check: x for x in ac.findings(keys, set(), "adult", "t")}
        self.assertEqual(f["skull.app.morph"].severity, FAIL)
        full = {k for k in ac.required("adult")["morph"]} | set(ac.parse_pf_keys())
        self.assertTrue(all(x.severity == PASS for x in ac.findings(full, {"head_scale"}, "adult", "t") if x.check.endswith(".morph")))

    def test_rename_suggestions_come_only_from_agreeing_typesafe_answers(self):
        from blender.validators import app_contract as ac

        def fake(payload):
            ans = {}
            for qid, q in payload["questions"].items():
                crit = list(q["criteria"])
                pick = "ID-BrowThick" if "ID-BrowThick" in crit else "brows" if "brows" in crit else crit[0]
                ans[qid] = {"type": "choice", "choice": pick, "confidence": 0.9, "probabilities": {c: 0.0 for c in crit}}
            return {"answers": ans}
        out = ac.suggest_renames(["ID-BrowThickness"], {"ID-BrowThick": "brows", "ID-NoseLarge": "nose"}, fake)
        self.assertEqual(out["ID-BrowThickness"][0], "ID-BrowThick")


if __name__ == "__main__":
    unittest.main()
