import os, sys, unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from blender.validators import deform_judge, deform_regions as dr, regions, synth, topology  # noqa: E402
from blender.validators.model import FAIL, PASS, WARN, Finding  # noqa: E402


def worst(findings):
    sev = [f.severity for f in findings if f.severity in (PASS, WARN, FAIL)]
    return FAIL if FAIL in sev else WARN if WARN in sev else PASS


def clean(motion):
    return synth.build(None, 3.5 if dr.LOOPS.get(motion.label, (0, 9))[1] <= 3 else None)


class BandsPerRegion(unittest.TestCase):
    def test_every_region_has_a_band_class(self):
        for r in regions.REGIONS:
            self.assertIn(dr.REGION_CLASS.get(r), dr.CLASSES, r)

    def test_every_motion_is_inside_a_human_range_and_has_a_loop_target(self):
        for m in dr.MOTIONS:
            self.assertLessEqual(m.max_deg, 150, m.label)
            self.assertIn(m.label, dr.LOOPS, m.label)
            self.assertIn(m.region, regions.REGIONS, m.region)

    def test_clean_limb_passes_and_every_defect_fails_in_every_region(self):
        for m in dr.MOTIONS:
            c = clean(m)
            self.assertEqual(worst(dr.run_motion(m, c["verts"], c["faces"], synth.joint(c))), PASS, f"clean {m.label}")
            for d in synth.DEFECTS:
                c = synth.build(d)
                self.assertEqual(worst(dr.run_motion(m, c["verts"], c["faces"], synth.joint(c))), FAIL, f"{d} on {m.label}")

    def test_tests_stop_at_the_joints_range_of_motion(self):
        m = dr.motions_for("arms")[0]
        c = clean(m)
        labels = {f.check.split(".")[2] for f in dr.run_motion(m, c["verts"], c["faces"], synth.joint(c))}
        self.assertIn("elbow_flexion_145deg", labels)
        self.assertIn("elbow_flexion_(reverse)_5deg", labels)
        self.assertFalse(any("150deg" in x or "180deg" in x for x in labels))

    def test_the_same_deformation_is_fine_in_a_lip_and_a_failure_in_a_neck_or_a_hair_clump(self):
        m = {"zone_faces": 40.0, "stretch": 2.4, "squash": 0.4, "shear": 22.0, "collapse": 0.0, "flip": 0.0, "worst_stretch": 2.9}
        self.assertEqual(worst(dr.findings("mouth", "smile", m)), PASS)
        self.assertEqual(worst(dr.findings("neck", "nod", m, 45)), FAIL)
        self.assertEqual(worst(dr.findings("hair", "clump", m)), FAIL)
        self.assertNotEqual(worst(dr.findings("clothing", "sleeve", m)), FAIL)  # cloth may stretch more than a neck

    def test_rigid_pieces_may_move_but_not_deform(self):
        r, f = synth.patch()
        rot = np.array([[0.0, -1, 0], [1, 0, 0], [0, 0, 1]])
        self.assertEqual(worst(dr.rigid_check("hair", "clump", r, r @ rot.T + [1, 2, 3], f)), PASS)
        stretched = r.copy()
        stretched[:, 0] *= 1.3
        self.assertEqual(worst(dr.rigid_check("hair", "clump", r, stretched, f)), FAIL)
        self.assertEqual(worst(dr.rigid_check("clothing", "sleeve", r, stretched, f)), PASS)  # cloth follows the body

    def test_shape_keys_are_judged_by_the_region_they_belong_to(self):
        for name, region in (("Blink_L", "eyes"), ("Brow_Up", "brows"), ("Mouth_Smile", "mouth"), ("viseme_aa", "mouth"), ("Cheek_Puff", "cheeks"),
                             ("Nose_Wrinkle", "nose"), ("Jaw_Open", "jaw")):
            self.assertEqual(dr.key_region(name), region, name)
        r, p, f = synth.key(None)
        self.assertEqual(worst(dr.run_key("Blink", r, p, f)), PASS)
        for d in synth.KEY_DEFECTS:
            r, p, f = synth.key(d)
            self.assertEqual(worst(dr.run_key("Blink", r, p, f)), FAIL, d)

    def test_findings_land_in_their_own_region(self):
        self.assertEqual(regions.region_of_check("deform.hands.finger_base_curl_90deg.shear"), "hands")
        self.assertEqual(regions.region_of_check("deform.eyes.key_Blink.flip"), "eyes")


class WhatTheOldCheckMissed(unittest.TestCase):
    def test_a_collapsed_joint_in_a_big_mesh_failed_the_old_whole_mesh_check_to_see(self):
        c = synth.build("hard_split")
        rest = np.vstack([c["verts"], c["verts"][:, :] + [10, 0, 0]])
        faces = list(c["faces"]) + [tuple(i + len(c["verts"]) for i in f) for f in c["faces"]] * 1
        weights = np.concatenate([c["weight"], np.zeros(len(c["weight"]))])
        big = np.vstack([rest] + [rest + [20 * k, 0, 0] for k in range(1, 40)])
        bigfaces = [tuple(i + len(rest) * k for i in f) for k in range(40) for f in faces]
        bigw = np.concatenate([weights] + [np.zeros(len(rest))] * 39)   # only the first tube has a joint
        joint = dr.Joint({"m": (np.arange(len(big)), bigw)}, ["m"], c["joint"], [[1, 0, 0], [0, 0, 1], [0, 1, 0]], None, [0, 0, 2])
        posed = topology.lbs_rotate(big, joint.weights, ["m"], c["joint"], [1, 0, 0], 145)
        old = topology.deformation(big, posed, bigfaces)
        self.assertEqual(topology.deformation_findings(old, "body")[0].severity, PASS)   # diluted: looks fine
        mot = dr.motions_for("arms")[0]
        self.assertEqual(worst(dr.run_motion(mot, big, bigfaces, joint)), FAIL)            # zone check sees it

    def test_a_bend_past_90_degrees_is_not_a_flip(self):
        c = synth.build(None)
        zone = dr.deformation_zone(c["faces"], c["weight"])
        self.assertEqual(dr.measure(c["verts"], synth.bend(c, 145), c["faces"], zone)["flip"], 0.0)

    def test_flexing_sign_follows_the_distal_end(self):
        c = synth.build(None)
        j = synth.joint(c)
        up = dr.Motion("t", "x", 0, 90, 0, (0, -1, 0), "t")
        down = dr.Motion("t", "x", 0, 90, 0, (0, 1, 0), "t")
        self.assertEqual(dr.flexing_sign(up, c["verts"], j), -dr.flexing_sign(down, c["verts"], j))


class DeformJudge(unittest.TestCase):
    def test_state_is_words_not_numbers(self):
        c = synth.build("hard_split")
        f = dr.run_motion(dr.motions_for("arms")[0], c["verts"], c["faces"], synth.joint(c))
        state = deform_judge.build_state("arms", deform_judge.group(f)["arms"])
        text = str(state)
        for f_ in f:
            if f_.value is not None and f_.value > 9:
                self.assertNotIn(f"{f_.value:.3f}", text)
        self.assertIn("past the fail limit", text)

    def test_judge_reads_the_answers_and_keeps_the_band_authoritative(self):
        def fake(payload):
            a = {"clean": {"noul": 0.05}, "no_fold": {"noul": 0.9}, "quality": {"score": 0.4, "confidence": 0.9}, "first_fix": {"choice": "blend"}}
            return {"answers": a}
        c = synth.build("hard_split")
        f = dr.run_motion(dr.motions_for("arms")[0], c["verts"], c["faces"], synth.joint(c))
        out = deform_judge.judge_all(f, fake)["arms"]
        by = {x.check.rsplit(".", 1)[-1]: x for x in out}
        self.assertEqual(by["clean"].severity, WARN)
        self.assertEqual(by["quality"].severity, WARN)
        self.assertIn("blend", by["first_fix"].message)

    def test_judge_survives_a_failing_network(self):
        def boom(_):
            raise OSError("offline")
        c = synth.build(None)
        f = dr.run_motion(dr.motions_for("arms")[0], c["verts"], c["faces"], synth.joint(c))
        self.assertEqual(deform_judge.judge_all(f, boom)["arms"][0].severity, "skip")


if __name__ == "__main__":
    unittest.main()
