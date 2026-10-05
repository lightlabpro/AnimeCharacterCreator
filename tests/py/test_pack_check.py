"""python3 -m unittest discover -s tests/py"""
import json, pathlib, shutil, struct, subprocess, sys, tempfile, unittest

root = pathlib.Path(__file__).resolve().parents[2]
SK = root / ".claude/skills/library-pack-check/scripts"
CONTRACT = root / "knowledge/expected-contract.json"

def make(out, defect=None, pid="body_test"):
    cmd = [sys.executable, str(SK / "make_test_pack.py"), str(out), "--id", pid] + (["--defect", defect] if defect else [])
    r = subprocess.run(cmd, capture_output=True, text=True); assert r.returncode == 0, r.stderr

def check(path, *extra):
    r = subprocess.run([sys.executable, str(SK / "check_pack.py"), str(path), "--contract", str(CONTRACT), *extra], capture_output=True, text=True)
    return r.returncode, r.stdout

def lib(tmp, tree="humanoid", cat="bodies/adult", defect=None, pid="body_test"):
    out = pathlib.Path(tmp) / tree / cat / pid; make(out, defect, pid); return pathlib.Path(tmp), out

def to_glb(folder, with_image=False):
    g = json.load(open(folder / "body_test.gltf")); bin_ = (folder / "body_test.bin").read_bytes()
    g["buffers"][0].pop("uri")
    if with_image: g["images"] = [{"bufferView": 0, "mimeType": "image/png"}]
    js = json.dumps(g).encode(); js += b" " * ((-len(js)) % 4); bin_ += b"\0" * ((-len(bin_)) % 4)
    body = struct.pack("<I4s", len(js), b"JSON") + js + struct.pack("<I4s", len(bin_), b"BIN\0") + bin_
    (folder / "body_test.glb").write_bytes(b"glTF" + struct.pack("<II", 2, 12 + len(body)) + body)
    (folder / "body_test.gltf").unlink(); (folder / "body_test.bin").unlink()

class CleanPack(unittest.TestCase):
    def test_a_clean_pack_passes(self):
        with tempfile.TemporaryDirectory() as t:
            tmp, _ = lib(t); code, out = check(tmp); self.assertEqual(code, 0, out); self.assertIn("PACK_CHECK_OK", out)
            self.assertIn("19440 triangles", out); self.assertIn("height 1.72 m", out)

    def test_a_glb_without_textures_passes_and_with_textures_fails(self):
        with tempfile.TemporaryDirectory() as t:
            tmp, out = lib(t); to_glb(out); code, text = check(tmp); self.assertEqual(code, 0, text)
        with tempfile.TemporaryDirectory() as t:
            tmp, out = lib(t); to_glb(out, with_image=True); code, text = check(tmp)
            self.assertEqual(code, 12); self.assertIn("embedded_texture", text)

def edit(folder, fn):
    p = folder / "body_test.gltf"; g = json.load(open(p)); fn(g); json.dump(g, open(p, "w"))

class AppLimits(unittest.TestCase):
    def codes(self, fn):
        with tempfile.TemporaryDirectory() as t:
            tmp, out = lib(t); edit(out, fn); code, text = check(tmp); return code, text

    def test_draco_meshopt_and_ktx2_fail_because_the_app_has_no_decoders(self):
        for ext in ("KHR_draco_mesh_compression", "EXT_meshopt_compression", "KHR_texture_basisu"):
            code, text = self.codes(lambda g, e=ext: g.update({"extensionsUsed": [e], "extensionsRequired": [e]}))
            self.assertEqual(code, 12, ext); self.assertIn("unsupported_extension", text)

    def test_supported_extensions_are_fine(self):
        code, text = self.codes(lambda g: g.update({"extensionsUsed": ["KHR_materials_emissive_strength", "KHR_texture_transform", "KHR_mesh_quantization"]}))
        self.assertEqual(code, 0, text)

    def test_more_shape_keys_than_webgl2_guarantees_layers_for_fails(self):
        def many(g, n):
            m = g["meshes"][0]; p = m["primitives"][0]; base = len(p["targets"])
            p["targets"] += [p["targets"][i % base] for i in range(n - base)]
            m["extras"]["targetNames"] += [f"ID-Dummy{i}" for i in range(n - base)]; m["weights"] += [0.0] * (n - base)
        code, text = self.codes(lambda g: many(g, 300)); self.assertEqual(code, 12); self.assertIn("too_many_targets", text)
        code, text = self.codes(lambda g: many(g, 230)); self.assertEqual(code, 0, text); self.assertIn("many_targets", text)     # a warning only

    def test_the_gpu_memory_estimate_is_reported_and_large_ones_warn(self):
        code, text = self.codes(lambda g: None); self.assertIn("MB of GPU texture", text)
        def big(g): g["accessors"][g["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]["count"] = 4_000_000
        code, text = self.codes(big); self.assertIn("morph_memory", text)

    def test_more_than_four_bone_influences_warn(self):
        code, text = self.codes(lambda g: g["meshes"][0]["primitives"][0]["attributes"].update({"JOINTS_1": 0, "WEIGHTS_1": 0}))
        self.assertEqual(code, 0, text); self.assertIn("joint_influences", text)

class PoseClips(unittest.TestCase):
    def test_pose_clips_are_reported(self):
        with tempfile.TemporaryDirectory() as t:
            tmp, _ = lib(t); code, out = check(tmp)
            self.assertEqual(code, 0, out); self.assertIn("POSE-tpose", out); self.assertIn("POSE-hero", out)

    def test_a_pack_without_pose_clips_says_so(self):
        with tempfile.TemporaryDirectory() as t:
            tmp, _ = lib(t, defect="no_poses"); code, out = check(tmp)
            self.assertEqual(code, 0, out); self.assertIn("rest pose", out)

    def test_a_misnamed_pose_clip_is_a_warning(self):
        with tempfile.TemporaryDirectory() as t:
            tmp, out = lib(t); g = json.load(open(out / "body_test.gltf")); g["animations"][0]["name"] = "POSE-crouch"
            json.dump(g, open(out / "body_test.gltf", "w")); code, text = check(tmp)
            self.assertEqual(code, 0, text); self.assertIn("pose_name", text)

class Defects(unittest.TestCase):
    def expect(self, defect, code_name, level="FAIL", exit_code=12):
        with tempfile.TemporaryDirectory() as t:
            tmp, _ = lib(t, defect=defect); code, out = check(tmp)
            self.assertEqual(code, exit_code, out)
            self.assertTrue(any(l.startswith(level) and code_name in l for l in out.splitlines()), f"{defect}: expected {level} {code_name}\n{out}")
    def test_embedded_buffer(self): self.expect("embedded", "embedded_buffer")
    def test_nonzero_default_weights(self): self.expect("nonzero_weights", "nonzero_weights")
    def test_missing_target_names(self): self.expect("no_targetnames", "no_target_names")
    def test_orphan_key_is_only_a_warning(self): self.expect("orphan_key", "orphan_key", level="WARN", exit_code=0)
    def test_floating_body(self): self.expect("floating", "origin_not_at_feet")
    def test_wrong_scale(self): self.expect("tiny", "height")
    def test_no_bones(self): self.expect("no_bones", "no_skin")
    def test_no_sockets(self): self.expect("no_sockets", "no_sockets")
    def test_missing_bin_file(self): self.expect("missing_bin", "missing_file")
    def test_bad_library_tag(self): self.expect("bad_library", "library")
    def test_missing_slot(self): self.expect("no_slot", "pack_fields")

    def test_strict_turns_warnings_into_failures(self):
        with tempfile.TemporaryDirectory() as t:
            tmp, _ = lib(t, defect="orphan_key"); self.assertEqual(check(tmp, "--strict")[0], 12)

    def test_missing_bounds_is_unknown_not_pass(self):
        with tempfile.TemporaryDirectory() as t:
            tmp, out = lib(t); g = json.load(open(out / "body_test.gltf"))
            for a in g["accessors"]: a.pop("min", None); a.pop("max", None)
            json.dump(g, open(out / "body_test.gltf", "w"))
            code, text = check(tmp); self.assertEqual(code, 13, text); self.assertIn("UNKNOWN", text)

class LibraryRules(unittest.TestCase):
    def test_a_humanoid_pack_in_the_robot_tree_fails(self):
        with tempfile.TemporaryDirectory() as t:
            tmp, _ = lib(t, tree="robot", cat="body"); code, out = check(tmp)
            self.assertEqual(code, 12); self.assertIn("tree_mismatch", out)

    def test_unknown_category_folder_fails(self):
        with tempfile.TemporaryDirectory() as t:
            tmp, _ = lib(t, cat="stuff/adult"); code, out = check(tmp)
            self.assertEqual(code, 12); self.assertIn("is not a humanoid category folder", out)

    def test_manifest_mismatch_and_orphans(self):
        with tempfile.TemporaryDirectory() as t:
            tmp, _ = lib(t)
            json.dump({"packs": [{"id": "body_test", "library": "robot", "folder": "humanoid/bodies/adult/body_test"},
                                 {"id": "ghost", "library": "humanoid", "folder": "humanoid/bodies/adult/ghost"}]}, open(tmp / "manifest.json", "w"))
            code, out = check(tmp); self.assertEqual(code, 12)
            self.assertIn("manifest_library", out); self.assertIn("manifest_orphan", out)

    def test_accessory_socket_must_exist_on_some_body(self):
        with tempfile.TemporaryDirectory() as t:
            tmp, _ = lib(t)
            acc = tmp / "humanoid/accessories/hat1"; acc.mkdir(parents=True)
            json.dump({"id": "hat1", "display_name": "Hat", "library": "humanoid", "slot": "accessory", "socket": "SOC-HeadTop"}, open(acc / "pack.json", "w"))
            self.assertEqual(check(tmp)[0], 0)
            json.dump({"id": "hat1", "display_name": "Hat", "library": "humanoid", "slot": "accessory", "socket": "SOC-NotAThing"}, open(acc / "pack.json", "w"))
            code, out = check(tmp, "--strict"); self.assertEqual(code, 12); self.assertIn("unknown_socket", out)

    def test_duplicate_ids_fail(self):
        with tempfile.TemporaryDirectory() as t:
            tmp, _ = lib(t); make(pathlib.Path(t) / "humanoid/bodies/child/body_test", None, "body_test")
            code, out = check(tmp); self.assertEqual(code, 12); self.assertIn("duplicate_id", out)

    def test_an_empty_folder_is_a_failure_not_a_pass(self):
        with tempfile.TemporaryDirectory() as t:
            code, out = check(t); self.assertEqual(code, 12); self.assertIn("no_packs", out)

if __name__ == "__main__":
    unittest.main()
