#!/usr/bin/env python3
"""Builds installable skill zips into bridge/skill-packages/ from .claude/skills/<name>/.

Each zip has the skill folder at its top level (SKILL.md inside), which is the layout the Claude
chat skill uploader expects. Re-run after editing any skill, then re-upload the zip in the chat.
"""
import pathlib, zipfile

root = pathlib.Path(__file__).resolve().parents[2]
out = root / "bridge" / "skill-packages"
out.mkdir(exist_ok=True)
for skill in sorted((root / ".claude" / "skills").iterdir()):
    if not (skill / "SKILL.md").exists():
        continue
    dest = out / f"{skill.name}.zip"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(skill.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
                z.write(f, f.relative_to(skill.parent).as_posix())
    print(f"built {dest.relative_to(root)} ({dest.stat().st_size} bytes)")
