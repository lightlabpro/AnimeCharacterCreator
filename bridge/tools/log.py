#!/usr/bin/env python3
"""Append a correctly formatted entry to bridge/LEARNINGS.md.

  python3 bridge/tools/log.py --side chat --topic "eye gap measured" \
     --finding "Eye gap is 1.31 eye widths on the approved head" \
     --evidence "qa_render measure on head_v7.blend" --status confirmed \
     --use "Code: set the default eye spacing slider to match"
"""
import argparse, datetime, pathlib, sys

ap = argparse.ArgumentParser()
ap.add_argument("--side", required=True, choices=["code", "chat"])
ap.add_argument("--topic", required=True)
ap.add_argument("--finding", required=True)
ap.add_argument("--evidence", required=True)
ap.add_argument("--status", default="unverified")
ap.add_argument("--use", required=True, help="what the other side should do with this")
a = ap.parse_args()
if not any(a.status.startswith(s) for s in ("confirmed", "unverified", "superseded-by")):
    sys.exit("status must start with confirmed, unverified or superseded-by")
path = pathlib.Path(__file__).resolve().parents[1] / "LEARNINGS.md"
entry = (f"\n## {datetime.date.today().isoformat()} [{a.side}] {a.topic}\n"
         f"- finding: {a.finding}\n- evidence: {a.evidence}\n- status: {a.status}\n- use: {a.use}\n")
with open(path, "a", encoding="utf-8") as f:
    f.write(entry)
print(f"logged to {path}")
