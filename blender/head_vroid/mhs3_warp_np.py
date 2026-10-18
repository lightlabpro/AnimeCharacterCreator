"""Apply mhs3_reshape.warp to the raw VRoid mesh (vroid_mesh.npz) without Blender, for fast measure loops (q36).

    python3 mhs3_warp_np.py vroid_mesh.npz OUT.npz [--knobs knobs.json]

Same warp as the GLB export (seat_brows is skipped; brows are not part of the profile rules)."""
import json
import os
import sys
import types

import numpy as np

sys.modules.setdefault("bpy", types.ModuleType("bpy"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mhs3_reshape as R  # noqa: E402


def main():
    src, out = sys.argv[1:3]
    if "--knobs" in sys.argv:
        R.K.update(json.load(open(sys.argv[sys.argv.index("--knobs") + 1])))
    d = np.load(src); o = {}
    for k in d.files:
        if k.endswith("__V"):
            key = k[:-3].replace("N00_000_00_", "").replace("N00_000_", "")
            o[k] = R.warp(d[k].astype(float), key)
        else:
            o[k] = d[k]
    np.savez(out, **o)


if __name__ == "__main__":
    main()
