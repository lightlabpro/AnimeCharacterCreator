"""Dataset pass 2: landmark check with TypeSafe Box (jev-1.14 images) instead of a yes/no question.

    python typesafe_landmark_box.py RENDER_DIR GATE_JSON

The yes/no "does the red line touch the chin?" question failed on thin lines (chin_ok < 0.6 on all 65, including
sheets Claude had verified by eye on 2026-10-07), so the landmark check is now a measurement: TypeSafe draws one box
around the head (skull top to chin tip, no neck, no hair) on the plain shape renders, and the measured landmark rows
must agree with the box edges within 4 % of the head height. Writes box_check into GATE_JSON per model.
"""
import json, os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import ask, image_asset  # noqa: E402

MODEL = "jev-1.14.0"


def main():
    rdir, gj = sys.argv[1], sys.argv[2]
    G = json.load(open(gj)); fr = json.load(open(os.path.join(rdir, "frames.json")))
    for u, rec in G.items():
        if "gate" not in rec or rec["gate"]["bare_head"] < 0.6 or "box_check" in rec or u not in fr or "ortho" not in fr[u]:
            continue
        f = fr[u]; res = f["res"]; mpp = f["ortho"] / res
        yt = (res / 2 - (f["top"] - f["zc"]) / mpp) / res; yc = (res / 2 - (f["chin"] - f["zc"]) / mpp) / res
        out = {}
        for view in ("sfront", "sside"):
            ph = "img-" + uuid.uuid4().hex
            q = {"head": {"type": "box", "instructions": "the head in `picture`, from the very top of the skull to the bottom tip of the chin (exclude the neck and anything below the chin)"},
                 "face_seen": {"type": "noul", "instructions": "Does `picture` show the front of a face (eyes, nose, mouth) rather than the back of a head?"}}
            r = ask(MODEL, {"picture": ph}, q, {ph: image_asset(os.path.join(rdir, "%s_%s.png" % (u, view)))}, True, False)["answers"]
            b = r["head"]["box"]
            out[view] = {"box": b, "conf": r["head"].get("confidence"), "face_seen": r["face_seen"]["noul"],
                         "top_err": round(abs(b["top"] - yt) / (yc - yt), 3), "chin_err": round(abs(b["bottom"] - yc) / (yc - yt), 3)}
        rec["box_check"] = out
        rec["landmarks_ok"] = all(v["top_err"] <= 0.04 and v["chin_err"] <= 0.04 for v in out.values())
        rec["front_is_face"] = out["sfront"]["face_seen"]
        print(u, rec["landmarks_ok"], {k: (v["top_err"], v["chin_err"]) for k, v in out.items()}, flush=True)
        json.dump(G, open(gj, "w"), indent=1)


if __name__ == "__main__":
    main()
