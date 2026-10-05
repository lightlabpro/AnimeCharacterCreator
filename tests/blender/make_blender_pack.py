"""Writes a pack exported by the real exporter script from a Blender-built character: python make_blender_pack.py LIBRARY_ROOT"""
import importlib.util, pathlib, sys
here = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(here))
import blender_fixtures as fx
spec = importlib.util.spec_from_file_location("export_pack", here.parents[1] / ".claude/skills/library-pack-check/scripts/export_pack.py")
ep = importlib.util.module_from_spec(spec); spec.loader.exec_module(ep)
fx.reset(); fx.character(shape_key_value=0.6)
ep.LIBRARY_ROOT = sys.argv[1]; ep.PACK_ID = "blender_body"; ep.CONTRACT = str(here.parents[1] / "knowledge/expected-contract.json")
print(ep.export_pack())
