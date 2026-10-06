"""Build a reference profile (metrics) from a model plus its landmark sidecar.

    blender -b model.blend -P make_reference_profile.py -- <name> <body_object> <armature_object|-> <landmarks.json> <out_dir>
Then vet it:  python -m blender.validators vet <out_dir>/adult-<name>.json
"""
import sys

import bpy

sys.path.insert(0, __file__.rsplit("/blender/", 1)[0])
from blender.validators import bpy_adapter, reference  # noqa: E402


def run(name, body, arm, landmarks, out_dir, kind="adult"):
    scene = bpy_adapter.snapshot(kind, body_name=body, armature_name=None if arm == "-" else arm)
    meta = bpy_adapter.load_markers(scene, landmarks)
    prof = reference.profile_from_scene(scene, name, source=f"{bpy.data.filepath.rsplit('/', 1)[-1]} (landmarks estimated)")
    for k in meta.get("unreliable_metrics", []):
        prof["metrics"].pop(k, None)
    prof["unreliable_metrics"] = meta.get("unreliable_metrics", [])
    prof["landmarks_estimated"] = bool(meta.get("estimated"))
    prof["pose"] = meta.get("pose", "unknown")
    print(reference.save_profile(prof, out_dir))
    print(prof["metrics"])
    print("missing:", prof["missing"])
    return prof


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    run(*a)
