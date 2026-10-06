"""Run the validators on an exported placeholder.   python tools/placeholders/measure.py /tmp/placeholder-adult-base.json [--typesafe]"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from blender.validators import checks, face, hair, judge, measure, placeholder, region_judge, regions
from blender.validators.model import Report


def run(path, use_ts=False, quiet=False):
    sc, extra = placeholder.load(path)
    rep = Report(kind=sc.kind, tag=os.path.basename(path))
    checks.anatomy(sc, rep)
    lm, _ = measure.landmarks(sc)
    bv = np.asarray(sc.body_verts, float)
    fm = face.metrics({k: (np.asarray(v[0], float), v[1]) for k, v in sc.parts.items()}, bv, lm)
    rep.add(*face.findings(fm, {k: 1 for k, _ in sc.parts.items()}, "placeholder"))
    rep.metrics.update({f"face.{k}": v for k, v in fm.items()})
    hv, hf = extra["hair"]
    hs = None
    if len(hv) and "Chin" in lm and "Crown" in lm:
        hd = lm["Crown"][2] - lm["Chin"][2]
        hs = hair.summarise(hair.clump_stats(hv, hf), hd)
        rep.add(*hair.findings(hs, "hair"))
        rep.add(*hair.fit_findings(hair.head_fit(hv, bv, extra["body_faces"], lm["Chin"][2], lm["Crown"][2]), "hair"))
    if not quiet:
        print(rep.summary())
        print("anatomy:", {k: round(v, 3) for k, v in rep.metrics.items() if not k.startswith("face.")})
        print("face   :", {k: round(v, 3) for k, v in fm.items()})
        if hs:
            print("hair   :", {k: round(v, 3) for k, v in hs.items()})
        for f in rep.worst_first():
            if f.severity in ("fail", "warn"):
                print(" ", f.severity.upper().ljust(4), f.check, "" if f.value is None else round(f.value, 3), "|", f.message[:90])
    if use_ts:
        env = region_judge.load_envelope(os.path.join(os.path.dirname(__file__), "..", "..", "blender", "references", "regions"))
        for region, out in region_judge.judge_all(rep.findings, env).items():
            q = [x for x in out if x.check.endswith("quality")]
            ff = [x.message for x in out if "first_fix" in x.check]
            print(f"  TypeSafe {region:9}", f"quality {q[0].value:.1f}/4" if q and q[0].value is not None else "", "|", ff[0][:60] if ff else "")
    return rep, fm, hs


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("json"); ap.add_argument("--typesafe", action="store_true")
    a = ap.parse_args(); run(a.json, a.typesafe)
