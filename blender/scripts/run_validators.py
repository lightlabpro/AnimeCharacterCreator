"""Paste into Blender's Text Editor (or run: blender -b file.blend -P run_validators.py -- adult tag).

Set KIND to adult | child | robot | dragon. Results print to the system console and are written to
docs/qa/validation/. Set TYPESAFE_API_KEY in the environment to enable the TypeSafe judge.
"""
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath or __file__))))
for cand in (ROOT, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
    if os.path.isdir(os.path.join(cand, "blender", "validators")) and cand not in sys.path:
        sys.path.insert(0, cand)
    elif os.path.isdir(os.path.join(cand, "validators")) and os.path.dirname(cand) not in sys.path:
        sys.path.insert(0, os.path.dirname(cand))

import importlib

try:
    from blender.validators import bpy_adapter, runner
except ImportError:
    from validators import bpy_adapter, runner  # when blender/ itself is on sys.path

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = args[0] if args else "adult"
TAG = args[1] if len(args) > 1 else "latest"

for m in (bpy_adapter, runner):
    importlib.reload(m)

report = runner.evaluate(bpy_adapter.snapshot(KIND), tag=TAG, use_judge=bool(os.environ.get("TYPESAFE_API_KEY")))
print(report.to_text())
out = os.path.join(ROOT, "docs", "qa", "validation")
print("written:", runner.write(report, out))
