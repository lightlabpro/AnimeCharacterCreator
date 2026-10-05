# Blender integration tests

These run the validator scripts in real Blender (headless) and check them against Blender's own numbers.

```
python3.11 -m venv bpyenv
bpyenv/bin/pip install numpy pillow bpy==5.0.1
bpyenv/bin/python -m unittest discover -s tests/blender          # 22 tests, about 25 s
BPY_PYTHON=$PWD/bpyenv/bin/python python3 -m unittest tests.py.test_e2e_pack   # also drives a Blender-exported pack through the real app
```

They skip themselves when `bpy` cannot be imported, so the normal `tests/py` run is unaffected. PyPI's newest `bpy` is 5.0.1;
the creator targets Blender 5.2, so rerun inside a 5.2 install when possible (Text Editor > open `test_blender.py` > Run Script).
