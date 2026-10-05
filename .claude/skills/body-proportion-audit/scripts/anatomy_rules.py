#!/usr/bin/env python3
"""Hard anatomy rules for a skinned character glTF: exact checks that need no reference model.

    anatomy_rules.py check pack.glb [--json out.json]        exit 0 pass, 12 fail, 13 unknown, 2 usage

Rules (fail unless stated):
  required_joints    head, neck, a spine bone, and upper arm / forearm / hand / thigh / shin / foot on both sides
  bone_symmetry      every left bone has a right twin (names compared with the side swapped and numeric suffixes dropped)
  chain_order        forearm below upper arm in the hierarchy, hand below forearm, foot below shin below thigh; legs run downwards
  fingers            at most 5 per hand, and if any finger bones exist all 5 with 2-4 segments, same on both hands
  unweighted         vertices with no weight at all
  weight_sum         vertices whose weights do not add to 1
  influences         more than 4 influences per vertex (the creator reads 4)
  cross_side         vertices on one side of the body mostly weighted to bones of the other side
  finger_bleed       vertices owned by a finger bone but far from that hand
  lr_balance         (warning only) very different weight mass on a left bone and its right twin
Thresholds marked GUESS were not measured on a corpus; calibrate them on real models before trusting a borderline result."""
import argparse, json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skin_io, body_audit as ba

EXIT_PASS, EXIT_FAIL, EXIT_UNKNOWN, EXIT_USAGE = 0, 12, 13, 2
REQUIRED = ("head", "neck") + tuple(f"{j}_{s}" for j in ("upper_arm", "forearm", "hand", "thigh", "shin", "foot") for s in "LR")
FINGERS = {"thumb": "thumb", "t": "thumb", "th": "thumb", "index": "index", "if": "index", "ind": "index", "middle": "middle", "mf": "middle",
           "mid": "middle", "ring": "ring", "rf": "ring", "little": "little", "pinky": "little", "pinkie": "little", "sf": "little", "lf": "little"}
SUM_TOL, SUM_FRAC = 0.02, 0.001           # GUESS: a vertex is off if |sum-1| > 2%; fail when more than 0.1% of vertices are
CROSS_X, CROSS_W, CROSS_FRAC = 0.03, 0.5, 0.001   # GUESS: >3% H on the wrong side with >50% weight on the other side's bones; >0.1% of vertices
BLEED_D = 0.15                             # GUESS: finger-owned vertex farther than 15% H from its hand joint
BALANCE = 0.35                             # GUESS

def finger_of(name):
    """'Index finger_L.002', 'IndexFinger1_L_053', 'if2.L', 't1.R' -> ('index', 'L'); None for non-finger bones and *_end markers."""
    s = name.split(":")[-1]
    if re.search(r"(^|[._\-])end$", s, re.I): return None
    s = re.sub(r"^(def|mch|org|tweak|ctrl)[-_.]", "", s, flags=re.I)
    s = re.sub(r"([a-z])([A-Z])", r"\1_\2", s); s = re.sub(r"([A-Za-z])(\d)", r"\1_\2", s)
    toks = [t for t in re.split(r"[._\-\s]+", s.lower()) if t]; side = None; keep = []
    for t in toks:
        if t in ("l", "left", "r", "right"): side = "L" if t[0] == "l" else "R"
        elif t.isdigit() or t in ("finger", "bone", "j", "bip"): continue
        else: keep.append(t)
    key = "".join(keep)
    return (FINGERS[key], side) if key in FINGERS and side else None

def normalise(name):
    s = re.sub(r"_\d{2,}$", "", name.split(":")[-1])
    s = re.sub(r"(?<![A-Za-z])(Left|Right|left|right)(?![a-z])", "S", s)
    s = re.sub(r"(?<![A-Za-z])[LR](?![A-Za-z])", "S", s)
    return re.sub(r"(?<=[a-z0-9])(?:[LR])$", "S", s)

def run(m):
    """m = skin_io.orient(skin_io.load(path)). Returns (status, rows); a row is (rule, state, message) with state ok/fail/warn/unknown."""
    rows = []; add = lambda rule, st, msg: rows.append((rule, st, msg))
    names, parents, key = m["names"], m["parents"], m.get("key", {})
    # --- joints
    miss = [k for k in REQUIRED if k not in key]
    if not any(k in key for k in ("pelvis", "chest")): miss.append("spine")
    add("required_joints", "fail" if miss else "ok", "missing bones: " + ", ".join(miss) if miss else "all required joints found")
    # --- left/right bone sets: body joints and fingers must mirror exactly; costume bones (hair, sleeves, ...) only warn
    from collections import Counter
    is_body = lambda n: bool(ba.canon(n)[0] or finger_of(n))
    isL = lambda n: bool(re.search(r"(^|[._\-\s])(l|left)($|[._\-\s\d])|[a-z](Left|L)(_\d+)?$", n, re.I)) and not re.search(r"(^|[._\-\s])(r|right)($|[._\-\s\d])", n, re.I)
    isR = lambda n: bool(re.search(r"(^|[._\-\s])(r|right)($|[._\-\s\d])|[a-z](Right|R)(_\d+)?$", n, re.I)) and not re.search(r"(^|[._\-\s])(l|left)($|[._\-\s\d])", n, re.I)
    side_of = lambda n: ba.canon(n)[1] or (finger_of(n) or (None, None))[1]
    def twins(pred):
        cl = Counter(normalise(n) for n in names if isL(n) and pred(n)); cr = Counter(normalise(n) for n in names if isR(n) and pred(n))
        return cl, cr, sorted(set(cl) ^ set(cr)) + sorted(k for k in set(cl) & set(cr) if cl[k] != cr[k])
    cl, cr, diff = twins(is_body)
    if not cl and not cr: add("bone_symmetry", "unknown", "no side-marked body bones (.L/.R, Left/Right) to compare")
    else: add("bone_symmetry", "fail" if diff else "ok", f"{len(diff)} body bone(s) without a matching twin: " + ", ".join(diff[:8]) if diff else f"{sum(cl.values())} left body bones mirror {sum(cr.values())} right")
    _, _, other = twins(lambda n: not is_body(n))
    if other: add("bone_symmetry_other", "warn", f"{len(other)} costume/helper bone(s) have no twin: " + ", ".join(other[:6]))
    # --- chain order
    if not m.get("oriented"): add("chain_order", "unknown", "skeleton not recognised, cannot orient")
    else:
        def below(child, anc):
            i = key.get(child); a = key.get(anc)
            while i is not None and i >= 0:
                i = parents[i]
                if i == a: return True
            return False
        prob = []
        for s in "LR":
            for c, a in ((f"forearm_{s}", f"upper_arm_{s}"), (f"hand_{s}", f"forearm_{s}"), (f"shin_{s}", f"thigh_{s}"), (f"foot_{s}", f"shin_{s}")):
                if c in key and a in key and not below(c, a): prob.append(f"{c} is not a child of {a}")
            z = lambda k: m["jpos"][key[k]][2] if k in key else None
            if None not in (z(f"thigh_{s}"), z(f"shin_{s}"), z(f"foot_{s}")) and not z(f"thigh_{s}") > z(f"shin_{s}") > z(f"foot_{s}"): prob.append(f"leg {s} joints are not ordered hip > knee > ankle in height")
        if "head" in key and "neck" in key and m["jpos"][key["head"]][2] < m["jpos"][key["neck"]][2]: prob.append("head bone is below the neck bone")
        add("chain_order", "fail" if prob else "ok", "; ".join(prob) if prob else "limb chains and heights in order")
    # --- fingers
    cnt = {}
    for n in names:
        f = finger_of(n)
        if f: cnt[f] = cnt.get(f, 0) + 1
    per = {s: {f: c for (f, ss), c in cnt.items() if ss == s} for s in "LR"}
    if not cnt: add("fingers", "unknown", "no finger bones found (hands without fingers are not checked)")
    else:
        prob = []
        for s in "LR":
            if len(per[s]) > 5: prob.append(f"{s} hand has {len(per[s])} fingers")
            elif per[s] and len(per[s]) < 5: prob.append(f"{s} hand has only {len(per[s])} fingers ({', '.join(sorted(set(FINGERS.values()) - set(per[s])))} missing)")
            if not per[s]: prob.append(f"{s} hand has no finger bones but the other has")
            prob += [f"{s} {f} finger has {c} bone(s), expected 2-4" for f, c in per[s].items() if not 2 <= c <= 4]
        if per["L"] and per["R"] and per["L"] != per["R"]: prob.append("left and right finger segment counts differ")
        add("fingers", "fail" if prob else "ok", "; ".join(prob) if prob else "5 fingers per hand, matching")
    # --- weights
    W, J = m["W"], m["J"]; N = len(W); s = W.sum(1)
    un = int((s < 1e-4).sum()); add("unweighted", "fail" if un else "ok", f"{un} vertices have no weights ({un / N:.2%})" if un else "every vertex is weighted")
    off = int(((s >= 1e-4) & (np.abs(s - 1) > SUM_TOL)).sum())
    add("weight_sum", "fail" if off > SUM_FRAC * N else "ok", f"{off} vertices ({off / N:.2%}) have weights not summing to 1 (e.g. {s[(s >= 1e-4) & (np.abs(s - 1) > SUM_TOL)][:3].round(2).tolist()})" if off else "weights sum to 1")
    inf = int(((W > 1e-3).sum(1) > 4).sum())
    add("influences", "fail" if inf else "ok", f"{inf} vertices use more than 4 influences; the creator reads 4. Limit to 4 and normalise in Blender (Weights > Limit Total)" if inf else "at most 4 influences per vertex")
    if not m.get("oriented"):
        for r in ("cross_side", "finger_bleed"): add(r, "unknown", "skeleton not recognised, cannot orient")
    else:
        V = m["V"]; H = float(V[:, 2].max() - V[:, 2].min())
        sidebones = np.zeros((len(names), 2), bool)                      # [is left, is right]
        for i, n in enumerate(names):
            sd = side_of(n); sidebones[i] = (sd == "L", sd == "R")
        wl = (W * sidebones[J][..., 0]).sum(1); wr = (W * sidebones[J][..., 1]).sum(1)
        sl = np.sign(np.mean([m["jpos"][key[k]][0] for k in ("thigh_L", "upper_arm_L") if k in key]) or 1.0)
        xs = V[:, 0] * sl
        badc = int((((wl > CROSS_W) & (xs < -CROSS_X * H)) | ((wr > CROSS_W) & (xs > CROSS_X * H))).sum())
        add("cross_side", "fail" if badc > CROSS_FRAC * N else "ok", f"{badc} vertices sit on one side of the body but are mostly weighted to the other side's bones" if badc else "no cross-side weights")
        bleed = 0; fb = {}
        for i, n in enumerate(names):
            f = finger_of(n)
            if f: fb[i] = f[1]
        if fb:
            dom = J[np.arange(N), np.argmax(W, 1)]; isf = np.isin(dom, list(fb))
            for v in np.where(isf)[0]:
                hand = key.get(f"hand_{fb[dom[v]]}")
                if hand is not None and np.linalg.norm(V[v] - m["jpos"][hand]) > BLEED_D * H: bleed += 1
            add("finger_bleed", "fail" if bleed else "ok", f"{bleed} vertices are owned by a finger bone but sit more than {BLEED_D:.0%} H from the hand" if bleed else "finger weights stay on the hands")
        else: add("finger_bleed", "unknown", "no finger bones")
        mass = np.zeros(len(names)); np.add.at(mass, J.reshape(-1), W.reshape(-1))
        warn = []
        for k, i in key.items():
            if k.endswith("_L") and k[:-2] + "_R" in key:
                a, b = mass[i], mass[key[k[:-2] + "_R"]]
                if max(a, b) > 0 and abs(a - b) / max(a, b) > BALANCE: warn.append(f"{k[:-2]} {a:.1f} vs {b:.1f}")
        add("lr_balance", "warn" if warn else "ok", "weight mass differs between left and right: " + ", ".join(warn) if warn else "left and right weight mass balanced")
    st = "fail" if any(r[1] == "fail" for r in rows) else "unknown" if any(r[1] == "unknown" for r in rows) else "pass"
    return st, rows

def report(name, st, rows):
    return "\n".join([f"ANATOMY RULES {name}: {st.upper()}"] + [f"  {s.upper():7s} {r:16s} {msg}" for r, s, msg in rows])

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check"]); ap.add_argument("file"); ap.add_argument("--json")
    try: a = ap.parse_args(argv)
    except SystemExit as e: return EXIT_USAGE if e.code else 0
    try: m = skin_io.orient(skin_io.load(a.file)); st, rows = run(m)
    except (OSError, ValueError, KeyError) as e: print(f"error: {e}", file=sys.stderr); return EXIT_USAGE
    print(report(os.path.basename(a.file), st, rows))
    if a.json:
        with open(a.json, "w") as f: json.dump({"status": st, "rows": rows}, f, indent=1)
    return {"pass": EXIT_PASS, "fail": EXIT_FAIL, "unknown": EXIT_UNKNOWN}[st]

if __name__ == "__main__":
    sys.exit(main())
