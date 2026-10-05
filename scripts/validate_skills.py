#!/usr/bin/env python3
"""Validates the project's Claude skills, the way the Meshy agent repo validates its own.

Checks, per skill in .claude/skills/<name>/:
  - SKILL.md has frontmatter with name == folder name and a non-empty description
  - SKILL.md stays short (<= 300 lines); detail belongs in references/
  - every relative markdown link resolves inside the skill folder
  - every script a skill names exists, and every .py compiles
  - no symlinks, no stray bytecode
  - the zip in bridge/skill-packages/ matches the source (no drift between what the chat installs and what Code uses)
And repo-wide: knowledge/expected-contract.json is current.
Run: python3 scripts/validate_skills.py
"""
import pathlib, py_compile, re, subprocess, sys, tempfile, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
PACKAGES = ROOT / "bridge" / "skill-packages"
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SCRIPT_REF = re.compile(r"`?(?:scripts/[\w./-]+\.(?:py|mjs|js))`?")
CROSS_REF = re.compile(r"<([\w-]+)>/(scripts/[\w./-]+\.(?:py|mjs|js))")   # a script owned by another skill, written <skill>/scripts/x.py

errors = []
def need(cond, msg):
    if not cond: errors.append(msg)

def frontmatter(text):
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not m: return None
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1); meta[k.strip()] = v.strip().strip('"')
    return meta

def check_skill(folder):
    entry = folder / "SKILL.md"
    need(entry.exists(), f"{folder.name}: no SKILL.md")
    if not entry.exists(): return
    text = entry.read_text(encoding="utf-8")
    meta = frontmatter(text)
    need(meta is not None, f"{folder.name}: missing frontmatter")
    if meta is None: return
    need(meta.get("name") == folder.name, f"{folder.name}: frontmatter name {meta.get('name')!r} does not match the folder")
    need(len(meta.get("description", "")) >= 40, f"{folder.name}: description missing or too short to trigger on")
    need(len(text.splitlines()) <= 300, f"{folder.name}: SKILL.md over 300 lines, move detail into references/")
    for f in folder.rglob("*"):
        if "__pycache__" in f.parts: continue   # local cache, gitignored and never packaged
        need(not f.is_symlink(), f"{f}: symlink inside a skill")
        if f.suffix == ".py" and f.is_file():
            try: py_compile.compile(str(f), doraise=True, cfile=str(pathlib.Path(tempfile.gettempdir()) / "skillcheck.pyc"))
            except py_compile.PyCompileError as e: errors.append(f"{f}: does not compile: {e.msg}")
    for md in folder.rglob("*.md"):
        content = md.read_text(encoding="utf-8")
        for target in LINK.findall(content):
            if re.match(r"[a-z]+://|#|mailto:", target): continue
            resolved = (md.parent / target.split("#")[0]).resolve()
            need(resolved.is_relative_to(folder.resolve()) and resolved.exists(), f"{md.relative_to(ROOT)}: link {target} does not resolve inside the skill")
    for other, rel in set(CROSS_REF.findall(text)):
        need((SKILLS / other / rel).exists(), f"{folder.name}: SKILL.md names {other}/{rel} but that skill has no such file")
        need("`" + other + "`" in text, f"{folder.name}: uses {other}/{rel}, so it must say the `{other}` skill has to be installed too")
    for ref in set(SCRIPT_REF.findall(CROSS_REF.sub("", text))):
        rel = ref.strip("`")
        need((folder / rel).exists(), f"{folder.name}: SKILL.md names {rel} but it does not exist")

def check_package(folder):
    z = PACKAGES / f"{folder.name}.zip"
    need(z.exists(), f"{folder.name}: no installable zip. Run python3 bridge/tools/package_skills.py")
    if not z.exists(): return
    with zipfile.ZipFile(z) as zf:
        packed = {n: zf.read(n) for n in zf.namelist() if not n.endswith("/")}
    expected = {}
    for f in sorted(folder.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
            expected[f.relative_to(folder.parent).as_posix()] = f.read_bytes()
    need(set(packed) == set(expected), f"{folder.name}: zip file list differs from source. Run python3 bridge/tools/package_skills.py")
    for name in set(packed) & set(expected):
        need(packed[name] == expected[name], f"{folder.name}: zip is stale for {name}. Run python3 bridge/tools/package_skills.py")

def main():
    folders = sorted(p for p in SKILLS.iterdir() if p.is_dir())
    need(folders, "no skills found")
    for f in folders:
        check_skill(f); check_package(f)
    r = subprocess.run([sys.executable, str(ROOT / "bridge" / "tools" / "export_contract.py"), "--check"], capture_output=True, text=True)
    need(r.returncode == 0, (r.stdout + r.stderr).strip() or "contract check failed")
    if errors:
        print("\n".join(f"FAIL {e}" for e in errors), file=sys.stderr)
        raise SystemExit(1)
    print(f"Validated {len(folders)} skills, their zips and the contract.")

if __name__ == "__main__":
    main()
