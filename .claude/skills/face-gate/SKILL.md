---
name: face-gate
description: Standard check for every head and face element and every expression of a 3D anime head (eyes, brows, nose, mouth, teeth, ears, jaw, hair framing, face shading, outline). Use whenever a head, face piece or facial expression is generated or changed, before showing it to the user and before exporting a pack. It renders a fixed view set, asks TypeSafe with the images whether the render follows every rule read from the anime/manga books, whether each element looks like the Monster Hunter Stories 3 references, and whether anything regressed against the last approved version; character-gate takes its report.
---

# Face gate: book rules + MHS3 look + no regression, judged by TypeSafe with images

Sammy (q26, 2026-10-17): "research the books about anime and manga and look for the parts on all elements and
expressions on the head and face. Validate using typesafe image, compare with the mhs3 references and validate look
with typesafe image. Make sure this process is standard when generating the 3d model elements."

So this is **the standard step after generating or changing any head / face element or expression**. Claude does not
grade its own renders: TypeSafe (pinned `jev-1.14.0`, images header on) answers every question, a missing
`TYPESAFE_API_KEY` stops the run (no judgment is faked), and an unanswered or uncertain item is never counted as a pass.

## Inputs
- **Book rules** (`docs/reference/books/rules_*_face.json`): read page by page from the anime/manga books -
  *The Complete Guide to Drawing Action Manga* (`actionanime`), *The Complete Guide to Drawing Manga & Anime*
  (13-week course, `mangaguide13`), *Mastering Manga with Mark Crilley* (`crilley`). Each rule: `id`, `page`,
  `element`, `rule` (paraphrased), `check` (a yes/no question about a render, yes = follows the rule), `views`.
  Each rule is first checked against its own book page with `blender/tools/typesafe_book_reader.py
  --only-rule-pages`; the score is written back as `rule_page_p`, and rules under 0.6 are not used by the gate
  (they are Claude's reading, not confirmed by the page). Notes per book: `notes_*_face.md`.
- **MHS3 references** (`blender/tools/visual_corrections/face_gate_refs.json`): front (Leo, Leia face crops), 3/4
  (Eleanor), and expression frames (smile, laugh, talk, grit) in `docs/reference/mhs3/`.
- **Renders**: `pc_v2.gate_shots(tag)` in Blender writes `docs/qa/head_v2/gate/<tag>/front.png`, `34.png`, `side.png`
  and `expr_<name>.png` (happy, laugh, angry, sad, surprised, talk_aa, smile_open, blink), framed on the face.

## Run (Sammy's PC, `py -3`)
```
py -3 blender/tools/typesafe_face_gate.py docs/qa/head_v2/gate/<tag> docs/qa/head_v2/gate/<tag>/face_gate.json ^
    --rules docs/reference/books/rules_actionanime_face.json,docs/reference/books/rules_mangaguide13_face.json,docs/reference/books/rules_crilley_face.json ^
    --refs blender/tools/visual_corrections/face_gate_refs.json --prev docs/qa/head_v2/gate/<approved_tag>
```
Passes, all with pictures:
1. **Book rules** - every rule asked against the render it applies to: pass p >= 0.6, fail p <= 0.4, else uncertain.
2. **MHS3 look** - per element, render and reference side by side: "same art style?" plus "same game?" (and "same
   emotion?" for expressions).
3. **No regression** (`--prev`) - previous approved vs current against the reference, both orders; "prev" in both
   orders is a regression.

The report (`face_gate.json`) has a per-element summary, every failed rule with its book and page, every MHS3-look
failure, and `gate.verdict`. Feed it to the `character-gate` skill: `run_gate.py ... --face-gate face_gate.json` (add
`--require face_gate` for head packs).

## How to act on it
- A failed rule names an element and a book page: open the page (books/<book>/pages), fix that element, re-render,
  re-run the gate. Fix the element the most failures point at first.
- Where the books and the MHS3 references disagree, the MHS3 look wins for the target style, and Sammy's own picks win
  over both (q25: he preferred the bigger-eyed v2 face over the Leo-matched v3x, so the approved version is the
  `--prev` baseline, not the last judged one).
- Use the `reference-match-judge` skill (`typesafe_visual_judge.py` with `--images`) when one element is off and you need TypeSafe
  to pick the correction from a menu; the face gate tells you which element, the judge tells you how to fix it.
- Never mark the work done with gate.verdict "fail", or with elements only "uncertain" / "not measured" without saying
  so to Sammy.
