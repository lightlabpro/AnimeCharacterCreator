"""Session helpers for Sammy's Blender (exec once after Blender starts; q30: they lived only in driver_namespace and
were lost when Blender closed).

    exec(open(r"<repo>\\blender\\head_v2\\pc_session.py", encoding="utf-8").read())

ns["v2it_safe"](tag, **knobs)  - import _ab/v2/v2_work.blend through pc_v2.py with the knobs as exec globals
                                 (OUTLINE_T, ELL_A, SKIN_SOFT, MASK_SOFT, KEY_FROM, HAIR_FIT, ...); ns["JOB"] = state
ns["ts_bg"](key, args)         - run `py -3 args...` in a thread (TypeSafe tools); ns[key] = {state, out, err}
"""
import os
import subprocess
import threading
import time

import bpy

R = r"D:\Game Development\Tools\Anime Character Creator\AnimeCharacterCreator-main"
ns = bpy.app.driver_namespace


def v2it_safe(tag, **kn):
    ns["JOB"] = {"state": "running"}
    t0 = time.time()
    try:
        g = {"__name__": "pc_v2", "BLEND": os.path.join(R, "_ab", "v2", "v2_work.blend"), "TAG": "v2", "REPO": R}
        g.update(kn)
        exec(open(os.path.join(R, "blender", "head_v2", "pc_v2.py"), encoding="utf-8").read(), g)
        ns["JOB"] = {"state": "done %.1fs" % (time.time() - t0), "tag": tag}
    except Exception as e:                                  # noqa: BLE001 - report, never hide
        import traceback
        ns["JOB"] = {"state": "error " + repr(e), "trace": traceback.format_exc()}
        print(ns["JOB"]["trace"])
    return ns["JOB"]


def ts_bg(key, args):
    ns[key] = {"state": "running", "out": "", "err": ""}

    def run():
        t0 = time.time()
        p = subprocess.run(["py", "-3"] + list(args), capture_output=True, text=True, cwd=R)
        ns[key] = {"state": "done %.0fs rc=%d" % (time.time() - t0, p.returncode), "out": p.stdout, "err": p.stderr}
    threading.Thread(target=run, daemon=True).start()


ns["v2it_safe"] = v2it_safe
ns["ts_bg"] = ts_bg
print("pc_session: v2it_safe, ts_bg ready")
