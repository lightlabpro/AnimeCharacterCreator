"""Blender integration tests for the validator scripts. Run with a Python that can import bpy:

    python -m venv bpyenv && bpyenv/bin/pip install numpy pillow bpy==5.0.1
    bpyenv/bin/python -m unittest discover -s tests/blender

(inside Blender itself, run this file from the Text Editor). Skipped automatically when bpy is not importable.
Tested on Blender 5.0.1. The creator targets 5.2; the APIs used here are stable across 4.2-5.x, but a 5.2 run is still worth doing."""
import importlib.util, json, os, pathlib, sys, tempfile, unittest

try:
    import bpy  # noqa: F401
    HAVE_BPY = True
except ImportError:
    HAVE_BPY = False

root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(pathlib.Path(__file__).parent))
SK = root / ".claude/skills"

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

@unittest.skipUnless(HAVE_BPY, "needs bpy")
class BlenderCase(unittest.TestCase):
    def setUp(self):
        import blender_fixtures as fx
        self.fx = fx; fx.reset()
        self.tmp = tempfile.TemporaryDirectory(); self.dir = pathlib.Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()

class ExportRoundTrip(BlenderCase):
    def export(self, **over):
        mod = load(SK / "library-pack-check/scripts/export_pack.py", "export_pack")
        mod.LIBRARY_ROOT = str(self.dir / "library"); mod.PACK_ID = "blender_body"; mod.CONTRACT = str(root / "knowledge/expected-contract.json")
        for k, v in over.items(): setattr(mod, k, v)
        return mod, mod.export_pack()

    def gltf(self):
        return json.load(open(self.dir / "library/humanoid/bodies/adult/blender_body/blender_body.gltf"))

    def test_shape_keys_are_exported_at_zero_and_restored(self):
        body, arm = self.fx.character(shape_key_value=0.7)
        mod, (folder, status) = self.export()
        g = self.gltf()
        self.assertEqual(g["meshes"][0]["weights"], [0, 0, 0, 0], "the exporter writes current key values as default weights")
        self.assertEqual(g["meshes"][0]["extras"]["targetNames"], ["ID-FaceRound", "ID-EyeSize", "PF-Blink", "PF-JawOpen"])
        self.assertEqual([round(k.value, 3) for k in body.data.shape_keys.key_blocks[1:]], [0.7] * 4, "values must be restored")
        self.assertNotEqual(status, "FAIL")

    def test_a_plain_export_with_keys_left_at_one_would_fail_the_checker(self):
        body, arm = self.fx.character(shape_key_value=1.0)
        out = self.dir / "plain"; out.mkdir()
        bpy.ops.export_scene.gltf(filepath=str(out / "plain.gltf"), export_format="GLTF_SEPARATE")
        (out / "pack.json").write_text(json.dumps({"id": "plain", "display_name": "p", "library": "humanoid", "slot": "body_adult"}))
        chk = load(SK / "library-pack-check/scripts/check_pack.py", "check_pack")
        rep = chk.check(str(self.dir), None)
        self.assertTrue(any(i["code"] == "nonzero_weights" for i in rep.items), "the checker must catch what a plain export does")

    def test_dotted_bones_sockets_pose_clips_and_extras_survive(self):
        self.fx.character(); self.export(); g = self.gltf()
        names = [n["name"] for n in g["nodes"]]
        self.assertIn("DEF-upper_arm.L", names)                                   # authored names stay dotted in the file
        self.assertIn("POSE-tpose", [a["name"] for a in g["animations"]])
        soc = next(n for n in g["nodes"] if n["name"] == "SOC-HeadTop")
        self.assertEqual(soc.get("extras", {}).get("socket_name"), "SOC-HeadTop")  # needs export_extras=True
        joints = {g["nodes"][j]["name"] for j in g["skins"][0]["joints"]}
        self.assertNotIn("MCH-helper", joints, "non-deform helper bones are left out")

    def test_pack_json_and_manifest_are_written_and_updated(self):
        self.fx.character(); mod, _ = self.export(); mod.export_pack()               # twice: the manifest must not duplicate
        pack = json.load(open(self.dir / "library/humanoid/bodies/adult/blender_body/pack.json"))
        self.assertEqual((pack["id"], pack["library"], pack["slot"]), ("blender_body", "humanoid", "body_adult"))
        manifest = json.load(open(self.dir / "library/manifest.json"))
        self.assertEqual([p["id"] for p in manifest["packs"]], ["blender_body"])
        self.assertEqual(manifest["packs"][0]["folder"], "humanoid/bodies/adult/blender_body")

    def test_the_selection_is_restored_and_helpers_are_not_exported(self):
        body, arm = self.fx.character()
        lm = bpy.data.objects.new("LM_top", None); self.fx.link(lm)
        for o in bpy.context.scene.objects: o.select_set(False)
        lm.select_set(True)
        self.export()
        self.assertTrue(lm.select_set is not None and lm.select_get(), "the user's selection comes back")
        self.assertNotIn("LM_top", [n["name"] for n in self.gltf()["nodes"]])

class MeshStatsMatchesBlender(BlenderCase):
    def stats(self, obj):
        ms = load(SK / "render-validator/scripts/mesh_stats.py", "mesh_stats")
        me = obj.data
        return ms.stats_from_arrays([tuple(v.co) for v in me.vertices], [list(p.vertices) for p in me.polygons])

    def blender_truth(self, obj):
        import bmesh
        bm = bmesh.new(); bm.from_mesh(obj.data)
        tris = sum(len(f.verts) - 2 for f in bm.faces)
        boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
        nonman = sum(1 for e in bm.edges if len(e.link_faces) > 2)
        parent = {v.index: v.index for v in bm.verts}
        def find(a):
            while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
            return a
        for f in bm.faces:
            vs = [v.index for v in f.verts]
            for a, b in zip(vs, vs[1:]): parent[find(a)] = find(b)
        used = {v.index for f in bm.faces for v in f.verts}
        out = {"tris": tris, "boundary": boundary, "nonman": nonman, "parts": len({find(i) for i in used}),
               "zero": sum(1 for f in bm.faces if f.calc_area() < 1e-12), "ngons": sum(1 for f in bm.faces if len(f.verts) > 4)}
        bm.free(); return out

    def check(self, obj):
        s, t = self.stats(obj), self.blender_truth(obj)
        self.assertEqual((s["tris"], s["boundary_edges"], s["non_manifold_edges"], s["loose_parts"], s["zero_area_faces"], s["ngons"]),
                         (t["tris"], t["boundary"], t["nonman"], t["parts"], t["zero"], t["ngons"]), obj.name)

    def test_primitives(self):
        fx = self.fx
        for name, op in (("cube", bpy.ops.mesh.primitive_cube_add), ("sphere", bpy.ops.mesh.primitive_uv_sphere_add),
                         ("plane", bpy.ops.mesh.primitive_plane_add), ("cone", bpy.ops.mesh.primitive_cone_add), ("torus", bpy.ops.mesh.primitive_torus_add)):
            op(); o = bpy.context.active_object; o.name = name; self.check(o)

    def test_odd_topology(self):
        fx = self.fx
        # three triangles sharing one edge (non-manifold), a zero-area triangle, a hexagon n-gon, and two loose pieces
        self.check(fx.mesh_object("nonmanifold", [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1)], [(0, 1, 2), (0, 1, 3), (0, 1, 4)]))
        self.check(fx.mesh_object("zero", [(0, 0, 0), (1, 0, 0), (2, 0, 0)], [(0, 1, 2)]))
        hexa = [(math.cos(i * math.pi / 3), math.sin(i * math.pi / 3), 0) for i in range(6)] if False else None
        import math as m
        self.check(fx.mesh_object("hex", [(m.cos(i * m.pi / 3), m.sin(i * m.pi / 3), 0) for i in range(6)], [tuple(range(6))]))
        self.check(fx.mesh_object("two", [(0, 0, 0), (1, 0, 0), (0, 1, 0), (5, 5, 5), (6, 5, 5), (5, 6, 5)], [(0, 1, 2), (3, 4, 5)]))

    def test_the_character_body(self):
        body, _ = self.fx.character(); self.check(body)

class HeadAuditAccuracy(BlenderCase):
    def audit(self):
        ha = load(SK / "head-shape-audit/scripts/head_audit.py", "head_audit"); return ha

    def make(self, segments, rings, radii=(0.075, 0.10, 0.105)):
        o = self.fx.ellipsoid("CHR_Head", (0, 0, 0.12), radii, segments, rings)
        zs = [v.co.z for v in o.data.vertices]
        for n, z in (("LM_top", max(zs)), ("LM_chin", min(zs))):
            e = bpy.data.objects.new(n, None); self.fx.link(e); e.location = (0, 0, z)
        return o

    def analytic(self, f, radii, ):
        a, b, c = radii; H = 2 * c; z = c - f * H     # height above the ellipsoid centre
        return 2 * a * (1 - (z / c) ** 2) ** 0.5 / H, 2 * b * (1 - (z / c) ** 2) ** 0.5 / H

    def test_widths_match_the_analytic_ellipsoid(self):
        radii = (0.075, 0.10, 0.105); o = self.make(96, 64, radii); ha = self.audit()
        verts, faces = ha.collect_mesh(bpy, ["CHR_Head"])
        top = max(v[2] for v in verts); chin = min(v[2] for v in verts)
        prof = ha.profile_from_mesh(verts, faces, top, chin, -1)
        for f in (0.1, 0.3, 0.5 if False else 0.25, 0.85):
            self.assertAlmostEqual(prof["width"][str(f)], self.analytic(f, radii)[0], delta=0.012, msg=f"width at {f}")

    def test_the_result_does_not_depend_on_how_the_mesh_is_tessellated(self):
        ha = self.audit(); res = []
        for seg, ring in ((24, 16), (48, 32), (128, 96)):
            self.fx.reset(); self.make(seg, ring)
            v, f = ha.collect_mesh(bpy, ["CHR_Head"]); res.append(ha.profile_from_mesh(v, f, max(p[2] for p in v), min(p[2] for p in v), -1))
        for row in ("0.1", "0.2", "0.25", "0.3", "0.85", "0.9"):
            vals = [r["width"][row] for r in res]
            self.assertLess(max(vals) - min(vals), 0.03, f"row {row}: {vals}")
            self.assertTrue(all(v is not None for v in vals), "no row may be dropped on a coarse mesh")

    def test_run_in_blender_writes_a_status_file(self):
        self.make(48, 32); ha = self.audit()
        bpy.ops.wm.save_as_mainfile(filepath=str(self.dir / "head.blend"))
        status = ha.run_in_blender()
        self.assertIn(status, ("pass", "fail"))
        data = json.load(open(self.dir / "head_audit.json"))
        self.assertEqual(data["status"], status); self.assertEqual(data["unknown"], [])

    def test_landmarks_created_by_a_script_are_read_at_their_new_position(self):
        self.make(48, 32); ha = self.audit()
        bpy.data.objects["LM_top"].location.z += 0.05          # moved by script, no manual view layer refresh
        bpy.ops.wm.save_as_mainfile(filepath=str(self.dir / "h.blend"))
        ha.run_in_blender()
        prof = json.load(open(self.dir / "head_audit.json"))["profile"]
        self.assertAlmostEqual(prof["H"], 0.21 + 0.05, places=2)     # ellipsoid 0.21 m tall plus the 5 cm the top landmark moved

    def test_a_sparse_mesh_is_measured_not_dropped(self):
        ha = self.audit(); self.make(8, 6)                       # 8x6 sphere: almost no vertices near the 0.2H and 0.9H rows
        v, f = ha.collect_mesh(bpy, ["CHR_Head"])
        prof = ha.profile_from_mesh(v, f, max(p[2] for p in v), min(p[2] for p in v), -1)
        self.assertTrue(all(x is not None for x in prof["width"].values()), prof["width"])

class RenderViews(BlenderCase):
    def setUp(self):
        super().setUp()
        self.body, self.arm = self.fx.character()
        sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 1; sc.cycles.device = "CPU"
        self.mod = load(SK / "render-validator/scripts/blender_render_views.py", "blender_render_views")
        self.mod.RES = 256

    def test_views_manifest_and_a_clean_scene_afterwards(self):
        sc = bpy.context.scene
        before = (sc.render.resolution_x, sc.render.film_transparent, sc.view_settings.view_transform, sc.camera, sc.render.filepath, len(bpy.data.cameras))
        m = self.mod.render_views(str(self.dir / "r"), res=256)
        after = (sc.render.resolution_x, sc.render.film_transparent, sc.view_settings.view_transform, sc.camera, sc.render.filepath, len(bpy.data.cameras))
        self.assertEqual(before, after, "the scene must be left exactly as it was")
        self.assertEqual(sorted(m["views"]), sorted(["front", "three_quarter", "side", "back", "face", "face_three_quarter"]))
        for v in m["views"].values(): self.assertTrue((self.dir / "r" / v["file"]).exists())
        self.assertTrue((self.dir / "r/r_manifest.json").exists())
        self.assertAlmostEqual(m["character_height"], 1.72, places=2)

    def test_body_views_have_the_same_scale_and_alpha(self):
        from PIL import Image
        import numpy as np
        self.mod.render_views(str(self.dir / "r"), res=256)
        heights = {}
        for v in ("front", "side", "back"):
            a = np.asarray(Image.open(self.dir / f"r/r_{v}.png").convert("RGBA"))[..., 3]
            self.assertEqual((a.min(), a.max()), (0, 255)); ys = np.where((a > 16).any(axis=1))[0]; heights[v] = ys.max() - ys.min()
        mean = sum(heights.values()) / 3
        self.assertTrue(all(abs(h - mean) / mean < 0.04 for h in heights.values()), heights)

    def test_the_side_view_is_narrower_than_the_front_for_a_flat_figure(self):
        from PIL import Image
        import numpy as np
        self.mod.render_views(str(self.dir / "r"), res=256)
        w = {}
        for v in ("front", "side"):
            a = np.asarray(Image.open(self.dir / f"r/r_{v}.png").convert("RGBA"))[..., 3]; xs = np.where((a > 16).any(axis=0))[0]; w[v] = xs.max() - xs.min()
        self.assertLess(w["side"], w["front"] * 0.7, w)

    def test_landmarks_frame_the_face_and_are_recorded(self):
        top = bpy.data.objects.new("LM_top", None); chin = bpy.data.objects.new("LM_chin", None)
        for o, z in ((top, 1.72), (chin, 1.38)): self.fx.link(o); o.location = (0, 0, z)
        m = self.mod.render_views(str(self.dir / "r"), res=256)
        self.assertTrue(m["head_from_landmarks"]); self.assertAlmostEqual(m["head_height"], 0.34, places=2)
        self.assertAlmostEqual(m["views"]["face"]["target"][2], 1.55, places=2)

    def test_floors_and_helpers_do_not_change_the_framing(self):
        base = self.mod.render_views(str(self.dir / "a"), res=64)["character_height"]
        floor = self.fx.mesh_object("Floor", [(-10, -10, -0.5), (10, -10, -0.5), (10, 10, -0.5), (-10, 10, -0.5)], [(0, 1, 2, 3)])
        self.assertAlmostEqual(self.mod.render_views(str(self.dir / "b"), res=64)["character_height"], base, places=4)

    def test_default_output_folder_for_an_unsaved_file_is_writable(self):
        self.assertFalse(bpy.data.filepath); p = self.mod.default_out(bpy)
        self.assertNotEqual(p, "/validator_renders"); self.assertTrue(os.path.isabs(p))


class ValidatorPipelineOnRealBlenderOutput(BlenderCase):
    """Blender-produced files go through the real validate.py: mesh stats, head audit, render manifest, camera drift."""
    VALIDATE = SK / "render-validator/scripts/validate.py"

    def run_validate(self, *args):
        import subprocess
        r = subprocess.run([sys.executable, str(self.VALIDATE), *map(str, args)], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def render(self, out, engine="CYCLES"):
        sc = bpy.context.scene; sc.render.engine = engine; sc.cycles.samples = 1; sc.cycles.device = "CPU"
        mod = load(SK / "render-validator/scripts/blender_render_views.py", "blender_render_views"); mod.render_views(str(out), res=192)

    def test_mesh_stats_from_blender_feed_the_validator_and_orphans_are_flagged(self):
        body, arm = self.fx.character()
        body.data.shape_keys.key_blocks[1].name = "ID-NotInTheApp"
        bpy.ops.wm.save_as_mainfile(filepath=str(self.dir / "c.blend"))
        load(SK / "render-validator/scripts/mesh_stats.py", "mesh_stats").run_in_blender()
        stats = json.load(open(self.dir / "mesh_stats.json"))
        self.assertIn("ID-NotInTheApp", stats["shape_keys"]); self.assertIn("DEF-upper_arm.L", stats["bones"]); self.assertIn("SOC-HeadTop", stats["sockets"])
        self.render(self.dir / "r")
        self.assertEqual(self.run_validate("init", self.dir / "ws", "--require-mesh")[0], 0)
        code, out = self.run_validate("measure", self.dir / "ws", "--view", f"front={self.dir/'r/r_front.png'}", "--mesh-stats", self.dir / "mesh_stats.json",
                                      "--contract", root / "knowledge/expected-contract.json")
        self.assertIn("ID-NotInTheApp", out)                                        # the name the app will ignore
        self.assertIn("mesh:tris", out)                                              # 1.7k triangles is under the 18k body budget

    def test_manifest_from_the_real_renderer_detects_camera_drift(self):
        self.fx.character(); a, b = self.dir / "a", self.dir / "b"
        self.render(a); self.render(b)
        self.run_validate("init", self.dir / "ws"); views = lambda d: sum([["--view", f"{v}={d/('r_'+v+'.png')}"] for v in ("front", "side", "back")], [])
        self.run_validate("measure", self.dir / "ws", *views(a), "--manifest", a / "r_manifest.json")
        code, out = self.run_validate("measure", self.dir / "ws", *views(b), "--manifest", b / "r_manifest.json")
        self.assertNotIn("cameras:changed", out)                                     # identical set-up
        # change the camera rules: a different view list resolution, as someone editing the script would
        m = json.load(open(b / "r_manifest.json")); m["views"]["front"]["elevation"] = 12; json.dump(m, open(b / "r_manifest.json", "w"))
        c = self.dir / "c"; self.render(c)
        import shutil; shutil.copy(b / "r_manifest.json", c / "r_manifest.json")
        code, out = self.run_validate("measure", self.dir / "ws", *views(c), "--manifest", c / "r_manifest.json")
        self.assertIn("cameras:changed", out)

    def test_head_audit_json_from_blender_is_understood_by_the_validator(self):
        ha = load(SK / "head-shape-audit/scripts/head_audit.py", "head_audit")
        body, arm = self.fx.character()
        head = self.fx.ellipsoid("CHR_Head", (0, 0, 0.12), (0.075, 0.10, 0.105), 48, 32)
        zs = [v.co.z for v in head.data.vertices]
        for n, z in (("LM_top", max(zs)), ("LM_chin", min(zs))):
            e = bpy.data.objects.new(n, None); self.fx.link(e); e.location = (0, 0, z)
        ha.HEAD_OBJECTS = ["CHR_Head"]
        bpy.ops.wm.save_as_mainfile(filepath=str(self.dir / "c.blend")); status = ha.run_in_blender()
        self.render(self.dir / "r"); self.run_validate("init", self.dir / "ws", "--require-head")
        code, out = self.run_validate("measure", self.dir / "ws", "--view", f"front={self.dir/'r/r_front.png'}", "--head-audit", self.dir / "head_audit.json")
        self.assertEqual("head:shape" in out, status == "fail")
        self.assertNotIn("head:audit not supplied", out)

if __name__ == "__main__":
    unittest.main()
