"""Shrink a piece of vector content (an equation drawn as paths) that runs past its column, keeping it as vectors.

    python3 tools/ko/shrink_region.py <in.pdf> <out.pdf> <page> <x0> <y0> <x1> <y1> <right> [--keep x0,y0,x1,y1 ...]

The rectangle (page coordinates, 1-based page) holds the overflowing content. Everything in it is removed from the
page and drawn again from a copy of the page, scaled down uniformly so that its right edge comes to <right>, its left
edge staying where it was and its middle staying at the same height. Text in the --keep rectangles (e.g. the points
«0.3 pts» that the equation ran over) is kept out of the scaled copy and drawn again unscaled where it was.
Table rules crossing the rectangle stay on the page (only paths lying wholly inside it are removed) and are left out
of the scaled copy."""
import argparse

import pymupdf


def run(src, dst, pno, rect, right, keeps):
    doc = pymupdf.open(src)
    page = doc[pno - 1]
    r = pymupdf.Rect(rect)
    # 1. a copy holding only the equation: without the kept text
    eq = pymupdf.open(src)
    ep = eq[pno - 1]
    for k in keeps:
        ep.add_redact_annot(k)
    if keeps:
        ep.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                            text=pymupdf.PDF_REDACT_TEXT_REMOVE)
    # ... and without the table rules running through the rectangle: each rule is removed by touching it where it
    # leaves the rectangle (above or below), so no glyph near it is hit
    for d in ep.get_drawings():
        q = d['rect']
        if q.width < 2 and q.height > r.height and q.x0 > r.x0 and q.x1 < r.x1 and q.y0 < r.y0 and q.y1 > r.y1:
            y = q.y0 if r.y0 - q.y0 > 1 else q.y1
            t = pymupdf.Rect(q.x0 - 0.2, (q.y0 + r.y0) / 2 - 0.3, q.x1 + 0.2, (q.y0 + r.y0) / 2 + 0.3) if r.y0 - q.y0 > 1 \
                else pymupdf.Rect(q.x0 - 0.2, (q.y1 + r.y1) / 2 - 0.3, q.x1 + 0.2, (q.y1 + r.y1) / 2 + 0.3)
            ep.add_redact_annot(t)
    ep.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                        text=pymupdf.PDF_REDACT_TEXT_NONE)
    # 2. a copy holding only the kept text: the paths in the rectangle removed, text kept
    kt = pymupdf.open(src)
    kp = kt[pno - 1]
    kp.add_redact_annot(r)
    kp.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                        text=pymupdf.PDF_REDACT_TEXT_NONE)
    # 3. clear the rectangle on the page itself (text and the paths wholly inside it)
    page.add_redact_annot(r)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                          text=pymupdf.PDF_REDACT_TEXT_REMOVE)
    # 4. the equation, scaled
    s = (right - r.x0) / r.width
    h = r.height * s
    cy = (r.y0 + r.y1) / 2
    target = pymupdf.Rect(r.x0, cy - h / 2, right, cy + h / 2)
    page.show_pdf_page(target, eq, pno - 1, clip=r)
    # 5. the kept text, unscaled
    for k in keeps:
        page.show_pdf_page(k, kt, pno - 1, clip=k)
    doc.save(dst, garbage=3, deflate=True)
    return s


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('page', type=int)
    ap.add_argument('rect', type=float, nargs=4)
    ap.add_argument('right', type=float)
    ap.add_argument('--keep', action='append', default=[])
    a = ap.parse_args()
    keeps = [pymupdf.Rect(*map(float, k.split(','))) for k in a.keep]
    print('scale %.3f' % run(a.src, a.dst, a.page, a.rect, a.right, keeps))
