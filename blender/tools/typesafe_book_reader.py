"""TypeSafe reads a drawing book page by page (jev-1.14, with pictures) - q19.

    python typesafe_book_reader.py BOOK.zip OUT.jsonl [--title "Book title"] [--notes notes.json] [--workers 4]

BOOK.zip (made by the cloud-side book prep): pages/p0001.jpg ... and text.json ([{page, src, text}]).
TypeSafe only answers questions (yes/no, choice), it does not write text, so "reading" here means: every page goes in
with its picture and its text, and TypeSafe answers
  - topic: what the page mainly teaches (a fixed topic menu, asked in both option orders),
  - head: does the page teach anything about drawing human heads / faces,
  - and, with --notes, one yes/no per rule Claude took from that page ("does this page state or show <rule>?"),
    so every rule in Claude's notes is checked against the page it came from.
Output: one JSON line per page (resumable: pages already in OUT.jsonl are skipped). Never fakes an answer: a missing
key stops the run (typesafe_visual_judge.key).
"""
import json
import os
import sys
import threading
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typesafe_visual_judge import ask, key  # noqa: E402

MODEL = "jev-1.14.0"
TOPICS = {
    "head_proportions": "proportions and construction of the human head and face (front, 3/4, side, tilted)",
    "eyes_brows": "drawing eyes, eyelids, irises or eyebrows",
    "nose": "drawing the nose",
    "mouth_teeth": "drawing mouths, lips, teeth or tongues",
    "ears": "drawing ears",
    "expressions": "facial expressions and emotions",
    "face_shading": "light and shadow on faces or heads",
    "hair": "drawing hair",
    "manga_anime_style": "manga or anime style conventions for characters",
    "body_anatomy": "human body anatomy, figure, gesture or poses (not the head)",
    "hands_feet": "hands or feet",
    "light_render": "light, shadow, values and rendering in general (not faces)",
    "perspective": "perspective, space and drawing objects in 3D",
    "character_design": "character design, costume or silhouette",
    "creatures": "animals, dragons, monsters or creatures",
    "environment": "landscapes, architecture, vehicles, machines or props",
    "story_writing": "story, writing, comics storytelling or the business of publishing",
    "tools_basics": "materials, tools, warm-ups or basic mark making",
    "front_matter": "cover, contents, index, credits, blank or advertising pages",
    "other": "anything else",
}


def page_q(notes_for_page):
    qs = {"head": {"type": "noul", "instructions": (
        "Does this page (its picture `page_image` and its text `page_text`) teach or show anything about drawing human "
        "heads or faces - proportions, eyes, nose, mouth, teeth, ears, jaw, expressions, turning the head, or shading "
        "a face?")}}
    for k, rule in notes_for_page:
        qs["rule_" + k] = {"type": "noul", "instructions": (
            "Does this page (picture `page_image` and text `page_text`) state or show the following? Answer yes only "
            "if the page itself supports it: " + rule)}
    return qs


def run_page(z_lock, zf, rec, title, notes, out_lock, out_fh):
    i = rec["page"]
    with z_lock:
        img = zf.read("pages/p%04d.jpg" % i)
    import base64
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(img)).convert("RGB")
    s = min(1.0, 1568 / max(im.size))
    if min(im.size) * s < 280:
        s = 280 / min(im.size)
    if s != 1.0:
        im = im.resize((round(im.width * s), round(im.height * s)))
    buf = io.BytesIO(); im.save(buf, "PNG")
    aid = "page-" + uuid.uuid4().hex
    assets = {aid: {"type": "image", "format": "png", "data_base64": base64.b64encode(buf.getvalue()).decode()}}
    text = rec["text"][:12000]
    state = {"book": title, "page_number": i, "page_text": text or "(no text on this page)", "page_image": aid}
    mine = [(n["id"], n["rule"]) for n in notes if int(n["page"]) == i]
    out = {"page": i, "src": rec["src"], "chars": len(rec["text"])}
    picks = []
    for order in (0, 1):
        opts = list(TOPICS.items())
        if order:
            opts = opts[::-1]
        qs = page_q(mine if order == 0 else [])
        qs["topic"] = {"type": "choice", "instructions": "What does this page mainly teach or show?", "criteria": dict(opts)}
        r = ask(MODEL, state, qs, assets, True, len(text) > 6000)["answers"]
        picks.append(r["topic"].get("choice"))
        if order == 0:
            out["head_p"] = round(r["head"]["noul"], 3)
            out["rules"] = {k: round(r["rule_" + k]["noul"], 3) for k, _ in mine}
    out["topic"] = picks[0] if picks[0] == picks[1] else None
    out["topic_orders"] = picks
    with out_lock:
        out_fh.write(json.dumps(out) + "\n"); out_fh.flush()
    return out


def main():
    zp, outp = sys.argv[1], sys.argv[2]
    arg = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
    title = arg("--title", os.path.splitext(os.path.basename(zp))[0])
    notes = json.load(open(arg("--notes"))) if arg("--notes") else []
    only_rules = "--only-rule-pages" in sys.argv
    key()                                                    # stops here if the key is missing
    zf = zipfile.ZipFile(zp)
    recs = json.loads(zf.read("text.json"))
    done = set()
    if os.path.exists(outp):
        for line in open(outp):
            try:
                done.add(json.loads(line)["page"])
            except Exception:
                pass
    rule_pages = {int(n["page"]) for n in notes}
    todo = [r for r in recs if r["page"] not in done and (not only_rules or r["page"] in rule_pages)]
    print("%s: %d pages, %d to do" % (title, len(recs), len(todo)), flush=True)
    z_lock, out_lock = threading.Lock(), threading.Lock()
    errs = []
    with open(outp, "a") as fh, ThreadPoolExecutor(int(arg("--workers", 4))) as ex:
        futs = [ex.submit(run_page, z_lock, zf, r, title, notes, out_lock, fh) for r in todo]
        for f in futs:
            try:
                f.result()
            except Exception as e:
                errs.append(str(e)[:300])
    print("done, %d errors" % len(errs), errs[:3], flush=True)


if __name__ == "__main__":
    main()
