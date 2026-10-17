"""Write TypeSafe's page check back into the face rules (q26).

    python face_rules_merge.py RULES.json PAGECHECK.jsonl [PAGECHECK2.jsonl ...]

PAGECHECK is typesafe_book_reader.py --notes RULES.json --only-rule-pages output: one line per page with
"rules": {rule_id: p}. Each rule gets "rule_page_p" (the best score over its pages; None if its page was not read).
typesafe_face_gate.py skips rules under --min-rule-page (default 0.6). Prints the confirmed / partly / unsupported
counts per element.
"""
import json
import sys
from collections import defaultdict


def main():
    rules_p, checks = sys.argv[1], sys.argv[2:]
    best = {}
    for c in checks:
        for line in open(c):
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            for rid, p in (rec.get("rules") or {}).items():
                best[rid] = max(best.get(rid, 0.0), p)
    rules = json.load(open(rules_p))
    stat = defaultdict(lambda: [0, 0, 0, 0])
    for r in rules:
        p = best.get(r["id"])
        r["rule_page_p"] = None if p is None else round(p, 3)
        s = stat[r["element"]]
        s[3 if p is None else 0 if p >= 0.6 else 1 if p >= 0.4 else 2] += 1
    json.dump(rules, open(rules_p, "w"), indent=1)
    tot = [sum(v[i] for v in stat.values()) for i in range(4)]
    print("%s: confirmed %d, partly %d, unsupported %d, unread %d" % (rules_p, *tot))
    for e, v in sorted(stat.items()):
        print("  %-24s confirmed %2d  partly %2d  unsupported %2d  unread %2d" % (e, *v))


if __name__ == "__main__":
    main()
