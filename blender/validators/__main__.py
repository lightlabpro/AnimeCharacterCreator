"""python -m blender.validators <command>   (run from the repository root, no Blender needed)

  pack  <library_dir>                  validate pack.json / manifest.json / glTF presence
  gltf  <file.glb> --kind adult        run anatomy + contract on an exported model
  vet   <profile.json>                 have TypeSafe vet a saved reference profile (3 passes)
  app-contract [--write F | --update F]   what the creator app drives vs the build prompt; --update regenerates the key block in the prompt or ASSET_CONTRACT.md
  ref   <file.glb> --kind adult --name hina   save a reference profile from a model
"""
from __future__ import annotations

import argparse
import sys

from . import gltf, packs, reference, runner
from .model import Report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="validators")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack"); p.add_argument("root")
    g = sub.add_parser("gltf"); g.add_argument("path"); g.add_argument("--kind", default="adult")
    g.add_argument("--judge", action="store_true"); g.add_argument("--out")
    r = sub.add_parser("ref"); r.add_argument("path"); r.add_argument("--kind", default="adult"); r.add_argument("--name", required=True)
    r.add_argument("--dir", default=runner.DEFAULT_PROFILES)
    v = sub.add_parser("vet"); v.add_argument("profile")
    ac = sub.add_parser("app-contract"); ac.add_argument("--write"); ac.add_argument("--update", help="regenerate the app-key block in a prompt or contract file")
    a = ap.parse_args(argv)
    if a.cmd == "pack":
        rep = Report(kind="library", tag=a.root)
        packs.validate_library(a.root, rep)
    elif a.cmd == "gltf":
        rep = runner.evaluate(gltf.scene_from_gltf(a.path, a.kind), tag=a.path.rsplit("/", 1)[-1], use_judge=a.judge)
        if a.out:
            runner.write(rep, a.out)
    elif a.cmd == "app-contract":
        from . import app_contract
        if a.update:
            fn = app_contract.update_prompt if "PROMPT" in a.update.upper() else app_contract.update_markdown
            print(("updated " if fn(a.update) else "already current: ") + a.update)
            return 0
        text = app_contract.markdown()
        if a.write:
            open(a.write, "w", encoding="utf-8").write(text)
            print("wrote", a.write)
        else:
            print(text)
        return 0
    elif a.cmd == "vet":
        from . import vetting
        res = vetting.vet_file(a.profile)
        for k, d in res["vetted"].items():
            print(f"{'keep' if d['kept'] else 'DROP'} {k}: {d['score']}")
        return 0
    else:
        prof = reference.profile_from_scene(gltf.scene_from_gltf(a.path, a.kind), a.name)
        print(reference.save_profile(prof, a.dir)); print(prof["metrics"]); return 0
    print(rep.to_text())
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
