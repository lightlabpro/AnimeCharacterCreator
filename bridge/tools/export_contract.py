#!/usr/bin/env python3
"""Regenerates knowledge/expected-contract.json from the app source.

The creator drives these names at runtime. If a pack does not carry them, the matching slider or
expression silently does nothing. Run after changing src/model/controls.ts, performance.ts or the
viewport rig code, and commit the result so the chat builds to the current contract.
"""
import json, re, pathlib, datetime

root = pathlib.Path(__file__).resolve().parents[2]
src = root / "src"
controls = (src / "model" / "controls.ts").read_text(encoding="utf-8")

sliders = []
for line in controls.splitlines():
    m = re.match(r"\s*c\('([\w.]+)',\s*'((?:[^'\\]|\\.)*)',", line)
    if not m:
        continue
    cid, label = m.group(1), m.group(2)
    opts = line[line.index(", {", m.end()) + 3:line.rindex("})")] if ", {" in line[m.end():] and "})" in line else ""
    morph = re.search(r"morph:\s*'([^']+)'", opts)
    neg = re.search(r"morphNeg:\s*'([^']+)'", opts)
    bone = re.search(r"bone:\s*\['(\w+)',\s*([\d.]+),\s*([\d.]+)\]", opts)
    bodies = re.search(r"bodies:\s*(\w+)", opts)
    sliders.append({
        "id": cid, "label": label,
        "bipolar": "bi: true" in opts,
        "shape_key": morph.group(1) if morph else None,
        "shape_key_negative": neg.group(1) if neg else None,
        "bone_property": ({"name": bone.group(1), "lo": float(bone.group(2)), "hi": float(bone.group(3))} if bone else None),
        "bodies": bodies.group(1) if bodies else "HUM",
    })

all_src = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in src.rglob("*.ts*"))
pf = sorted(set(re.findall(r"'(PF-[A-Za-z0-9_]+)'", all_src)))
soc = sorted(set(re.findall(r"'(SOC-[A-Za-z0-9_]+)'", all_src)))
id_keys = sorted({s["shape_key"] for s in sliders if s["shape_key"]} | {s["shape_key_negative"] for s in sliders if s["shape_key_negative"]})

out = {
    "generated": datetime.date.today().isoformat(),
    "note": "Names the app drives at runtime. A pack missing a name means that control does nothing on that pack.",
    "pack_json_required": ["id", "display_name", "library", "slot"],
    "libraries": ["humanoid", "robot", "full_beast"],
    "category_folders": {
        "humanoid": ["bodies", "morphs", "hair", "facial_hair", "elements", "outfits", "accessories", "materials", "motions", "presets"],
        "robot": ["body", "parts", "materials", "motions"],
        "full_beast": ["body", "elements", "accessories", "materials", "motions", "presets"],
    },
    "identity_shape_keys": id_keys,
    "performance_shape_keys": pf,
    "sockets": soc,
    "sliders": sliders,
    "counts": {"sliders": len(sliders), "identity_shape_keys": len(id_keys), "performance_shape_keys": len(pf), "sockets": len(soc)},
}
dest = root / "knowledge" / "expected-contract.json"
if "--check" in __import__("sys").argv:
    old = json.loads(dest.read_text(encoding="utf-8"))
    old.pop("generated", None); new = {k: v for k, v in out.items() if k != "generated"}
    if old != new:
        raise SystemExit("knowledge/expected-contract.json is stale. Run: python3 bridge/tools/export_contract.py")
    print("contract is current")
else:
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {dest.relative_to(root)}: {out['counts']}")
