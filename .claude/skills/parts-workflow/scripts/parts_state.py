"""Keeps the parts workflow in order (parts-workflow skill). State: docs/qa/parts/state.json.

    python3 parts_state.py status              # which part and stage to work on now
    python3 parts_state.py set PART STAGE passed|failed [--note TEXT]
    python3 parts_state.py skip PART --note "Sammy: ..."   # only on Sammy's word

A part's stage can be set only when every earlier part is passed or skipped and every earlier stage of this part is
passed (exit 2 otherwise), so the order head -> torso -> arms/hands -> legs/feet cannot drift.
"""
import argparse
import datetime
import json
import os
import sys

# Sammy q41b (2026-10-25): "The face/head elements separately are: hair, eyes, eyebrows, hair, ears, mouth, teeth,
# facial hair." The nose stays part of head_base (bare head: skull, face skin, nose; no ears, no painted features).
PARTS = ["head_base", "hair", "eyes", "eyebrows", "ears", "mouth", "teeth", "facial_hair",
         "torso", "arms_hands", "legs_feet", "assembly", "texture", "rig", "toon", "unity"]
STAGES = {p: ["reference", "generate", "blender"] for p in PARTS[:11]}
STAGES.update({"assembly": ["blender"], "texture": ["blender"], "rig": ["blender"], "toon": ["blender"],
               "unity": ["unity"]})
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
PATH = os.path.join(ROOT, "docs", "qa", "parts", "state.json")


def load():
    if os.path.exists(PATH):
        return json.load(open(PATH))
    return {"parts": {p: {"skipped": False, "stages": {}} for p in PARTS}, "history": []}


def save(s):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    json.dump(s, open(PATH, "w"), indent=1)


def done(s, p):
    e = s["parts"][p]
    return e["skipped"] or all(e["stages"].get(st) == "passed" for st in STAGES[p])


def current(s):
    for p in PARTS:
        if not done(s, p):
            st = next(st for st in STAGES[p] if s["parts"][p]["stages"].get(st) != "passed")
            return p, st
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "set", "skip"])
    ap.add_argument("part", nargs="?")
    ap.add_argument("stage", nargs="?")
    ap.add_argument("result", nargs="?", choices=["passed", "failed"])
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    s = load()
    p, st = current(s)
    if a.cmd == "status":
        for q in PARTS:
            e = s["parts"][q]
            tag = "skipped" if e["skipped"] else " ".join("%s=%s" % (k, e["stages"].get(k, "-")) for k in STAGES[q])
            print("%-12s %s" % (q, tag))
        print("NOW:", p, st if p else "all done")
        return 0
    if a.part not in PARTS:
        print("unknown part", a.part); return 2
    if a.cmd == "skip":
        if not a.note:
            print("skip needs --note with Sammy's words"); return 2
        if a.part != p:
            print("can only skip the current part", p); return 2
        s["parts"][a.part]["skipped"] = True
    else:
        if a.stage not in STAGES[a.part] or a.result is None:
            print("usage: set PART STAGE passed|failed; stages:", STAGES[a.part]); return 2
        if a.part != p or a.stage != st:
            print("out of order: now is %s/%s" % (p, st)); return 2
        s["parts"][a.part]["stages"][a.stage] = a.result
    s["history"].append({"t": datetime.datetime.now().isoformat(timespec="seconds"), "cmd": a.cmd, "part": a.part,
                         "stage": a.stage, "result": a.result, "note": a.note})
    save(s)
    print("ok; now:", *current(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
