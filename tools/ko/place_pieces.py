"""Set a sentence of a Korean overlay page again around pieces of the original's inline math, keeping the math as it
was drawn (vectors/glyphs copied from the original page) and moving it to where it falls in the Korean sentence.

    python3 tools/ko/place_pieces.py <ko.pdf> <original.pdf> <out.pdf> <spec.json>

spec: a list of blocks
  {"page": 2, "delete": ["start of an overlay line", …],        overlay lines to remove (tools/ko/overlay_retext.py)
   "cover": [x0, y0, x1, y1],                                   white box over the original sentence (math included)
   "size": 9.5, "font": "kserif", "gap": 2.4,
   "lines": [ {"base": 232.5, "x": 121, "items": ["한글 …", {"math": [x0, y0, x1, y1], "base": 264.0}, "을 …"]}, … ]}
Korean items are written with the overlay's embedded font; a {"math": rect} item is the original page's content in
that rectangle, copied (as vectors) to the running x position; give its own baseline as "base" when it moves to
another line. Prints the right end of each line.
"""
import json
import os
import sys
import tempfile

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kfont import KFont, font_xref  # noqa: E402
import overlay_retext  # noqa: E402


def run(src, orig, dst, spec):
    # 1. overlay edits: delete old lines, cover the sentence, write the Korean pieces
    doc = pymupdf.open(src)
    ops, moves = [], []
    for blk in spec:
        pno = blk['page']
        font = blk.get('font', 'kserif')
        size = blk.get('size', 9.5)
        gap = blk.get('gap', 2.4)
        kf = KFont(doc, font_xref(doc, doc[pno - 1], font))
        for t in blk.get('delete', []):
            ops.append({'page': pno, 'find': t, 'delete': True})
        if 'cover' in blk:
            ops.append({'page': pno, 'box': blk['cover']})
        for ln in blk['lines']:
            x = ln['x']
            for i, it in enumerate(ln['items']):
                if i:
                    x += gap if not (isinstance(it, str) and it[:1] in ',.') else 0.3
                if isinstance(it, str):
                    ops.append({'page': pno, 'add': it, 'x': x, 'base': ln['base'], 'size': size, 'font': font})
                    x += kf.width(it, size)
                else:
                    r = pymupdf.Rect(it['math'])
                    dy = ln['base'] - it.get('base', ln['base'])        # from the math's own line to this one
                    moves.append((pno, r, pymupdf.Rect(x, r.y0 + dy, x + r.width, r.y1 + dy)))
                    x += r.width
            print('page %d line %.1f ends at %.1f' % (pno, ln['base'], x))
    tmp = tempfile.mkdtemp()
    j = os.path.join(tmp, 'ops.json')
    json.dump(ops, open(j, 'w'), ensure_ascii=False)
    mid = os.path.join(tmp, 'mid.pdf')
    overlay_retext.run(src, mid, ops)
    # 2. the math pieces, copied from the original page on top of everything
    out = pymupdf.open(mid)
    for pno, r, t in moves:
        # a copy of the original page holding only what lies in the rectangle (so no other text comes along)
        o = pymupdf.open(orig)
        op = o[pno - 1]
        W, H = op.rect.width, op.rect.height
        for q in (pymupdf.Rect(0, 0, W, r.y0), pymupdf.Rect(0, r.y1, W, H),
                  pymupdf.Rect(0, r.y0, r.x0, r.y1), pymupdf.Rect(r.x1, r.y0, W, r.y1)):
            if not q.is_empty:
                op.add_redact_annot(q)
        op.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_REMOVE, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                            text=pymupdf.PDF_REDACT_TEXT_REMOVE)
        out[pno - 1].show_pdf_page(t, o, pno - 1, clip=r)
    out.save(dst, garbage=3, deflate=True)


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], sys.argv[3], json.load(open(sys.argv[4])))
