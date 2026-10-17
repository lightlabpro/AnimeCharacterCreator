"""Page-by-page prep of a book (PDF or EPUB) with PyMuPDF on the PC - q19.

    py -3 book_prep_pc.py BOOK.pdf|BOOK.epub OUT.zip [--h 1000] [--split 250]

Writes pages/p0001.jpg ... (every page, max --h px tall) and text.json ([{page, src, text}]) - the format
typesafe_book_reader.py reads and the cloud side reads for Claude. --split N writes OUT_partK.zip files of N pages
each (keeps each zip small enough to move). Nothing is skipped: blank pages are kept as pages.
"""
import io
import json
import os
import sys
import zipfile

import fitz  # PyMuPDF


def main():
    src, out = sys.argv[1], sys.argv[2]
    arg = lambda n, d: (type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d)
    H, split = arg("--h", 1000), arg("--split", 0)
    doc = fitz.open(src)
    if doc.is_reflowable:                       # EPUB: lay it out on a book-size page
        doc.layout(width=500, height=760, fontsize=11)
    n = doc.page_count
    parts = [(0, n)] if not split else [(a, min(n, a + split)) for a in range(0, n, split)]
    made = []
    for k, (a, b) in enumerate(parts):
        zp = out if len(parts) == 1 else out.replace(".zip", "_part%d.zip" % (k + 1))
        texts = []
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
            for i in range(a, b):
                p = doc.load_page(i)
                r = p.rect
                zoom = min(4.0, max(0.3, H / max(1.0, r.height)))
                pix = p.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                z.writestr("pages/p%04d.jpg" % (i + 1), pix.tobytes("jpeg", jpg_quality=75))
                t = p.get_text("text") or ""
                texts.append({"page": i + 1, "src": "text" if t.strip() else "none", "text": t.strip()})
            z.writestr("text.json", json.dumps(texts))
        made.append((zp, b - a, os.path.getsize(zp)))
    print(json.dumps({"book": os.path.basename(src), "pages": n, "parts": made}))


if __name__ == "__main__":
    main()
