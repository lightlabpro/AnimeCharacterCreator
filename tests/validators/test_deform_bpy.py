"""End to end in real Blender (pip install bpy): a synthetic armature + weighted tube and a shape-key patch go through
blender/scripts/analyze_topology.py. Skipped when bpy is not installed."""
import importlib.util, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
try:
    import bpy  # noqa: F401
    HAVE_BPY = True
except ImportError:
    HAVE_BPY = False

from blender.validators import synth  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def load_script():
    spec = importlib.util.spec_from_file_location("analyze_topology", os.path.join(ROOT, "blender", "scripts", "analyze_topology.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(HAVE_BPY, "bpy not installed")
class RealBlender(unittest.TestCase):
    def arm(self, defect):
        import bpy
        bpy.ops.wm.read_factory_settings(use_empty=True)
        c = synth.build(defect)
        v = c["verts"] * 0.04
        me = bpy.data.meshes.new("body")
        me.from_pydata([tuple(x) for x in v], [], c["faces"])
        me.update()
        ob = bpy.data.objects.new("body", me)
        bpy.context.scene.collection.objects.link(ob)
        arm = bpy.data.armatures.new("rig")
        ao = bpy.data.objects.new("rig", arm)
        bpy.context.scene.collection.objects.link(ao)
        bpy.context.view_layer.objects.active = ao
        bpy.ops.object.mode_set(mode="EDIT")
        a = arm.edit_bones.new("upperarm.L")
        a.head, a.tail = (0, 0, v[:, 2].min()), (0, 0, 0)
        b = arm.edit_bones.new("forearm.L")
        b.head, b.tail, b.parent, b.use_connect = (0, 0, 0), (0, 0, v[:, 2].max()), a, True
        bpy.ops.object.mode_set(mode="OBJECT")
        ga, gb = ob.vertex_groups.new(name="upperarm.L"), ob.vertex_groups.new(name="forearm.L")
        for i, w in enumerate(c["weight"]):
            ga.add([i], 1 - float(w), "REPLACE")
            gb.add([i], float(w), "REPLACE")
        ob.modifiers.new("Armature", "ARMATURE").object = ao
        bpy.context.view_layer.update()

    def test_clean_elbow_passes_and_bad_weights_fail(self):
        script = load_script()
        with tempfile.TemporaryDirectory() as out:
            self.arm(None)
            rep, data = script.run("clean", "body", "rig", out)
            self.assertEqual([f.check for f in rep.findings if f.severity == "fail"], [])
            self.assertIn("elbow flexion", data["regions"]["arms"])
            for defect in ("hard_split", "weight_spike"):
                self.arm(defect)
                rep, _ = script.run(defect, "body", "rig", out)
                self.assertTrue(any(f.severity == "fail" and f.check.startswith("deform.arms.") for f in rep.findings), defect)

    def test_shape_keys_are_judged_even_if_saved_at_value_one(self):
        import bpy
        script = load_script()
        with tempfile.TemporaryDirectory() as out:
            for defect, expect_fail in ((None, False), ("fold", True), ("spike", True)):
                bpy.ops.wm.read_factory_settings(use_empty=True)
                r, p, f = synth.key(defect)
                me = bpy.data.meshes.new("body")
                me.from_pydata([tuple(x) for x in r], [], f)
                me.update()
                ob = bpy.data.objects.new("body", me)
                bpy.context.scene.collection.objects.link(ob)
                ob.shape_key_add(name="Basis")
                k = ob.shape_key_add(name="Blink_L")
                for i, x in enumerate(p):
                    k.data[i].co = tuple(x)
                k.value = 1.0  # saved with the key on: the rest pose must still be the basis
                rep, data = script.run(f"k_{defect}", "body", "-", out)
                self.assertEqual(data["shape_keys"]["Blink_L"]["region"], "eyes")
                self.assertEqual(any(x.severity == "fail" and x.check.startswith("deform.eyes.") for x in rep.findings), expect_fail, defect)
                self.assertEqual(k.value, 1.0)  # restored


if __name__ == "__main__":
    unittest.main()
