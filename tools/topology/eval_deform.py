"""How well do the deformation bands and the TypeSafe judge agree on known-good and known-bad meshes?

   python tools/topology/eval_deform.py [--no-typesafe]

Every body-part motion is run on one clean synthetic limb and on each defect (synth.DEFECTS); every shape-key region on one clean
patch and each key defect. The deterministic bands must pass the clean ones and fail the defective ones; TypeSafe, which sees only words,
is scored against the same labels and on whether its first-fix choice names the right metric.
"""
import argparse, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from blender.validators import deform_judge, deform_regions as dr, synth
from blender.validators.model import FAIL, PASS, WARN

EXPECT = {"hard_split": {"blend", "loops", "stretch", "shear", "worst_stretch", "weight_jump", "collapse", "flip"}, "narrow_blend": {"blend", "loops", "stretch", "shear"}, "one_loop": {"blend", "loops", "shear"},
          "weight_spike": {"weight_jump", "worst_stretch"}, "stray_ring": {"flip", "weight_jump", "stretch", "worst_stretch"},
          "fold": {"flip", "squash"}, "pinch": {"collapse", "squash", "stretch", "shear", "worst_stretch", "flip"},
          "spike": {"worst_stretch", "stretch", "shear"}, "over_stretch": {"stretch", "worst_stretch", "shear", "flip"}}


def cases():
    for region in ("arms", "legs", "shoulders", "hips", "neck", "waist", "chest", "hands", "feet", "mouth", "tail", "wings"):
        for m in dr.motions_for(region):
            for d in (None,) + synth.DEFECTS:
                c = synth.build(d, 3.5 if (d is None and dr.LOOPS.get(m.label, (0, 9))[1] <= 3) else None)
                yield f"{m.label}", region, d, dr.run_motion(m, c["verts"], c["faces"], synth.joint(c))
    for name, region in (("Blink", "eyes"), ("Brow_Up", "brows"), ("Nose_Wrinkle", "nose"), ("Mouth_Smile", "mouth"), ("Cheek_Puff", "cheeks")):
        for d in (None,) + synth.KEY_DEFECTS:
            r, p, f = synth.key(d)
            yield f"key {name}", region, d, dr.run_key(name, r, p, f)


def label(findings):
    sev = [f.severity for f in findings if f.check.startswith("deform.")]
    return "fail" if FAIL in sev else "warn" if WARN in sev else "pass"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--no-typesafe", action="store_true"); a = ap.parse_args()
    rows = list(cases())
    bands_ok = sum(1 for _, _, d, f in rows if (label(f) == "pass") == (d is None))
    print(f"bands: {bands_ok}/{len(rows)} cases classified right ({sum(1 for r in rows if r[2] is None)} clean, {sum(1 for r in rows if r[2])} defective)")
    miss = [(n, d) for n, _, d, f in rows if (label(f) == "pass") != (d is None)]
    for n, d in miss:
        print("  band disagreement:", n, d)
    if a.no_typesafe:
        sys.exit(0)

    def one(row):
        n, region, d, f = row
        got = deform_judge.group(f)
        if region not in got:
            return None
        ans = deform_judge.ask_region(region, got[region])
        v = {x.check.rsplit(".", 1)[-1]: x for x in deform_judge.verdict(region, ans)}
        return n, d, v

    with ThreadPoolExecutor(8) as ex:
        res = [r for r in ex.map(one, rows) if r]
    tp = fp = tn = fn = unsure = 0
    fix_hit = fix_total = 0
    for n, d, v in res:
        p = v["clean"].value if "clean" in v else None
        if p is None or abs(2 * p - 1) < 0.4:
            unsure += 1
            continue
        said_clean = p >= 0.6
        if d is None:
            tn, fp = (tn + 1, fp) if said_clean else (tn, fp + 1)
        else:
            tp, fn = (tp + 1, fn) if not said_clean else (tp, fn + 1)
        if d and "first_fix" in v and "fix first:" in v["first_fix"].message:
            fix_total += 1
            pick = v["first_fix"].message.split("fix first: ")[1].strip()
            fix_hit += pick in EXPECT[d]
            if pick not in EXPECT[d]:
                print("  first-fix miss:", n, d, "->", pick)
    n = tp + fp + tn + fn
    print(f"TypeSafe clean-vs-defective: {tp + tn}/{n} right (defects caught {tp}/{tp + fn}, clean passed {tn}/{tn + fp}), {unsure} uncertain, routed to a human")
    print(f"TypeSafe first-fix names a metric the defect really breaks: {fix_hit}/{fix_total}")
