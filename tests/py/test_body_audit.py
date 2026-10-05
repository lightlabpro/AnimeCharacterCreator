import base64, json, os, subprocess, sys, tempfile, unittest
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, ".claude", "skills", "body-proportion-audit", "scripts")
sys.path.insert(0, SCRIPTS)
import body_audit as ba

def box(c, s, n=4):
    """Closed box mesh centred at c with size s (Z-up), subdivided so slices have vertices."""
    V, T = [], []
    for ax in range(3):
        for sign in (-1, 1):
            u, w = [i for i in range(3) if i != ax]
            base = len(V)
            for a in np.linspace(-.5, .5, n + 1):
                for b in np.linspace(-.5, .5, n + 1):
                    p = [0, 0, 0]; p[ax] = sign * .5; p[u] = a; p[w] = b
                    V.append([c[i] + p[i] * s[i] for i in range(3)])
            for i in range(n):
                for k in range(n):
                    a0 = base + i * (n + 1) + k; T += [[a0, a0 + 1, a0 + n + 2], [a0, a0 + n + 2, a0 + n + 1]]
    return V, T

def body(scale=1.0, leg=1.0, arm=1.0):
    """1.0-high blocky figure. leg/arm scale those lengths in the rig only; mesh stays, so ratios shift."""
    parts = [((0, 0, .35), (.34, .20, .70)),       # legs+pelvis block
             ((0, 0, .72), (.40, .22, .30)),       # torso
             ((0, 0, .93), (.18, .18, .14)),       # head
             ((-.30, 0, .66), (.12, .12, .30)), ((.30, 0, .66), (.12, .12, .30))]
    V, T = [], []
    for c, s in parts:
        v, t = box(c, s); T += [[i + len(V) for i in tri] for tri in t]; V += v
    V = np.array(V) * scale
    J = {"DEF-spine": (0, 0, .45), "DEF-neck": (0, 0, .82), "DEF-head": (0, 0, .84)}
    for s, x in (("L", 1), ("R", -1)):
        J[f"DEF-thigh.{s}"] = (x * .09, 0, .47); J[f"DEF-shin.{s}"] = (x * .09, 0, .26 * leg + .0); J[f"DEF-foot.{s}"] = (x * .09, 0, .05)
        J[f"DEF-upper_arm.{s}"] = (x * .20, 0, .78); J[f"DEF-forearm.{s}"] = (x * .26, 0, .78 - .15 * arm); J[f"DEF-hand.{s}"] = (x * .30, 0, .78 - .30 * arm)
    return V * 1, np.array(T), {k: tuple(np.array(v) * scale) for k, v in J.items()}

def glb(V, T, joints, path):
    """Write a minimal glTF (Y-up) with embedded data: one skinned mesh and the joint nodes."""
    Vy = np.stack([V[:, 0], V[:, 2], -V[:, 1]], 1).astype(np.float32)
    idx = np.array(T, np.uint32).reshape(-1); pos = Vy.tobytes(); ib = idx.tobytes()
    buf = pos + ib
    nodes = [{"name": "CHR_Body", "mesh": 0, "skin": 0}]
    for name, p in joints.items():
        nodes.append({"name": name, "translation": [float(p[0]), float(p[2]), float(-p[1])]})
    g = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes,
         "skins": [{"joints": list(range(1, len(nodes)))}], "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
         "buffers": [{"byteLength": len(buf), "uri": "data:application/octet-stream;base64," + base64.b64encode(buf).decode()}],
         "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(pos)}, {"buffer": 0, "byteOffset": len(pos), "byteLength": len(ib)}],
         "accessors": [{"bufferView": 0, "componentType": 5126, "count": len(Vy), "type": "VEC3"},
                       {"bufferView": 1, "componentType": 5125, "count": len(idx), "type": "SCALAR"}]}
    with open(path, "w") as f: json.dump(g, f)

class Names(unittest.TestCase):
    def test_rigs(self):
        for n, want in (("DEF-upper_arm.L", ("upper_arm", "L")), ("DEF-upperarm.R", ("upper_arm", "R")), ("mixamorig:LeftForeArm", ("forearm", "L")),
                        ("mixamorig:LeftUpLeg", ("thigh", "L")), ("mixamorig:RightLeg", ("shin", "R")), ("J_Bip_L_UpperArm", ("upper_arm", "L")),
                        ("DEF-spine.001", ("spine", None)), ("Hips", ("pelvis", None)), ("HeadTop_End", (None, None)), ("LeftHandIndex1", (None, None))):
            self.assertEqual(ba.canon(n), want, n)

class Measure(unittest.TestCase):
    def test_ratios_and_gltf_roundtrip(self):
        V, T, J = body(); prof = ba.measure(V, T, J, "ref")
        m = prof["metrics"]
        self.assertAlmostEqual(prof["height"], 1.0, places=2)
        self.assertAlmostEqual(m["hip_z"], .47, places=1); self.assertLess(m["mirror_p95"], 0.01); self.assertLess(m["rig_asymmetry"], 1e-6)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.glb.gltf"); glb(V, T, J, p)
            V2, T2, J2 = ba.load_gltf(p)
            self.assertTrue(np.allclose(sorted(map(tuple, np.round(V2, 5))), sorted(map(tuple, np.round(V, 5))), atol=1e-4))
            self.assertAlmostEqual(J2["DEF-hand.L"][2], J["DEF-hand.L"][2], places=4)
            m2 = ba.measure(V2, T2, J2, "ref")["metrics"]
            for k in m: self.assertAlmostEqual(m[k], m2[k], places=3, msg=k)

    def test_scale_invariant(self):
        a = ba.measure(*body(1.0), "a")["metrics"]; b = ba.measure(*body(1.72), "b")["metrics"]
        for k in a: self.assertAlmostEqual(a[k], b[k], places=3, msg=k)

class Targets(unittest.TestCase):
    def setUp(self):
        self.ref = ba.measure(*body(), "ref"); self.t = ba.build_targets([self.ref])

    def test_reference_passes_itself(self):
        st, rows = ba.check(self.ref, self.t); self.assertEqual(st, "pass", [r for r in rows if r[4] != "ok"])

    def test_long_legs_and_arms_fail(self):
        prof = ba.measure(*body(leg=1.5, arm=1.8), "bad")        # rig joints moved, mesh unchanged
        st, rows = ba.check(prof, self.t)
        self.assertEqual(st, "fail"); bad = {r[0] for r in rows if r[4] == "fail"}
        self.assertTrue({"knee_z", "wrist_z"} & bad, bad)

    def test_asymmetric_rig_fails_ceiling(self):
        V, T, J = body(); J["DEF-hand.L"] = (J["DEF-hand.L"][0], 0.05, J["DEF-hand.L"][2])
        st, rows = ba.check(ba.measure(V, T, J, "x"), self.t)
        self.assertIn("rig_asymmetry", {r[0] for r in rows if r[4] == "fail"})

    def test_asymmetric_mesh_fails(self):
        V, T, J = body(); V = V.copy(); V[V[:, 0] > 0.28, 0] += 0.15
        st, rows = ba.check(ba.measure(V, T, J, "x"), self.t)
        self.assertIn("mirror_p95", {r[0] for r in rows if r[4] == "fail"})

    def test_missing_joints_are_unknown_not_pass(self):
        V, T, J = body(); J = {k: v for k, v in J.items() if "forearm" not in k}
        st, rows = ba.check(ba.measure(V, T, J, "x"), self.t)
        self.assertEqual(st, "unknown")

class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, "body_audit.py"), *args], capture_output=True, text=True)

    def test_end_to_end_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            ref, bad, tg = (os.path.join(d, n) for n in ("ref.gltf", "bad.gltf", "t.json"))
            glb(*body(), ref); glb(*body(leg=1.5, arm=1.8), bad)
            r = self.run_cli("targets", ref, "--out", tg); self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(self.run_cli("check", ref, "--targets", tg).returncode, 0)
            self.assertEqual(self.run_cli("check", bad, "--targets", tg).returncode, 12)
            self.assertEqual(self.run_cli("check", os.path.join(d, "nope.gltf"), "--targets", tg).returncode, 2)
            self.assertEqual(self.run_cli("bogus").returncode, 2)

if __name__ == "__main__":
    unittest.main()
