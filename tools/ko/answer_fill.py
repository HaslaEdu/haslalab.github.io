"""Fill the empty task boxes of the Korean answer sheets (APhO 2018, 2023, 2024 …_A_KO.pdf).

These sheets give every task a box (label and points in a grey header row, the task statement, a «답:» line). The
statement is a clip of the Korean question page; for some tasks no clip was made, so the box shows only the header
and the «답:» line although the task has a statement on the question page (APhO 2023 T2 C.4).

For every box with nothing between its header row and its «답:» line, the task's framed box is found on the Korean
question paper (its label at the left margin), the frame's text column (right of the label, left of the points) is
trimmed to its first paragraph (lines joined across gaps up to 6 pt, so a figure or an option list further down is
left out; --whole takes everything in the frame), and that area of the question page is shown in the answer box
(PyMuPDF show_pdf_page with a clip - a vector copy, nothing is re-typeset), at the same left edge and the same
distance below the header as the file's other statements, scaled down if needed to fit above the «답:» line
(not below 0.55 - then the box is reported and left alone).

    python3 tools/ko/answer_fill.py <answer_KO.pdf> <question_KO.pdf> <out.pdf> [--whole] [--only p:LABEL,...]"""
import re
import statistics
import sys

import numpy as np
import pymupdf

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from answer_snippets import snippets, to_page, frame_of  # noqa: E402

LABEL = re.compile(r'^[A-Z]?\d*\.\d+$|^[A-Z]\.\d+$')
POINTS = re.compile(r'^\(?\s*[\d.]+\s*(pt|pts|점|points?)\s*\)?$')


def boxes(page):
    """answer boxes of a page: (label, header rect, box rect, answer-line y)"""
    drs = page.get_drawings()
    heads = [d['rect'] for d in drs if d.get('fill') and abs(d['fill'][0] - 0.92) < 0.01 and 15 < d['rect'].height < 21]
    frames = [d['rect'] for d in drs if d['type'] == 's' and d['rect'].width > 400 and d['rect'].height > 30]
    greys = [d['rect'] for d in drs if d['type'] == 's' and d.get('color') and abs(d['color'][0] - 0.5) < 0.01
             and d['rect'].height < 1.5 and d['rect'].width > 300]
    words = page.get_text('words')
    out = []
    for h in heads:
        fr = [f for f in frames if abs(f.y0 - h.y0) < 1.5 and abs(f.x0 - h.x0) < 1.5]
        if not fr:
            continue
        fr = fr[0]
        lab = [w[4] for w in words if pymupdf.Rect(w[:4]).intersects(h) and LABEL.match(w[4])]
        ans = [g.y0 for g in greys if fr.y0 < g.y0 < fr.y1]
        if lab and ans:
            out.append((lab[0], h, fr, max(ans)))
    return out


def ink_rows(page, clip, dpi=144):
    pix = page.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width) < 210


def task_area(qdoc, label, whole=False):
    """(page number, rect) of the task statement in the question paper"""
    for pno, p in enumerate(qdoc):
        for w in p.get_text('words'):
            if w[4] != label or w[0] > 130:
                continue
            lw = pymupdf.Rect(w[:4])
            fr = frame_of(p, pymupdf.Rect(lw.x0, lw.y0, lw.x0 + 300, lw.y1))
            if fr is None or not fr.contains(lw):
                continue
            ws = [pymupdf.Rect(x[:4]) for x in p.get_text('words', clip=fr)
                  if pymupdf.Rect(x[:4]) != lw and not POINTS.match(x[4])]
            pts = [pymupdf.Rect(x[:4]) for x in p.get_text('words', clip=fr)
                   if POINTS.match(x[4]) and x[0] > (fr.x0 + fr.x1) / 2]
            if not ws:
                continue
            x0 = min(r.x0 for r in ws if r.x0 > lw.x1) - 1.5
            x1 = (min(r.x0 for r in pts) - 3) if pts else fr.x1 - 3
            col = pymupdf.Rect(x0, fr.y0 + 1.5, x1, fr.y1 - 1.5)
            a = ink_rows(p, col)
            rows = a.any(axis=1)
            if not rows.any():
                continue
            k = 72 / 144
            idx = np.where(rows)[0]
            top = bot = idx[0]
            if whole:
                bot = idx[-1]
            else:
                g = int(6 / k)
                while True:
                    dn = [i for i in idx if bot < i <= bot + g]
                    if not dn:
                        break
                    bot = dn[-1]
            xs = np.where(a[top:bot + 1].any(axis=0))[0]
            return pno, pymupdf.Rect(col.x0 + xs[0] * k - 1.5, col.y0 + top * k - 1.5,
                                     col.x0 + (xs[-1] + 1) * k + 1.5, col.y0 + (bot + 1) * k + 1.5)
    return None


def fill(src, qsrc, dst, whole=False, only=None):
    doc, qdoc = pymupdf.open(src), pymupdf.open(qsrc)
    # where the file's existing statements sit relative to their box header
    lefts, gaps = [], []
    for pno, page in enumerate(doc):
        bx = boxes(page)
        for s in snippets(doc, pno):
            r = to_page(page, s, s['bb'])
            for lab, h, fr, ay in bx:
                if fr.contains(pymupdf.Point(r.x0 + 1, r.y0 + 1)):
                    a = ink_rows(page, r)
                    if not a.any():
                        continue
                    k = 72 / 144                                # where the statement's ink starts
                    lefts.append(r.x0 + np.where(a.any(axis=0))[0][0] * k)
                    gaps.append(r.y0 + np.where(a.any(axis=1))[0][0] * k - h.y1)
    left, gap = statistics.median(lefts), statistics.median(gaps)
    log, todo = [], []
    for pno, page in enumerate(doc):
        for lab, h, fr, ay in boxes(page):
            if only and '%d:%s' % (pno + 1, lab) not in only:
                continue
            body = pymupdf.Rect(fr.x0 + 2, h.y1 + 1, fr.x1 - 2, ay - 14)
            if ink_rows(page, body).any():
                continue                                       # the box has its statement
            t = task_area(qdoc, lab, whole)
            if t is None:
                log.append('p%d %s: empty, task not found in the question paper - left as is' % (pno + 1, lab))
                continue
            qpno, clip = t
            room_w, room_h = fr.x1 - 4 - left, ay - 14 - (h.y1 + gap)
            k = min(1.0, room_w / clip.width, room_h / clip.height)
            if k < 0.55:
                log.append('p%d %s: statement (%.0fx%.0f) does not fit the box (scale %.2f) - left as is'
                           % (pno + 1, lab, clip.width, clip.height, k))
                continue
            x, y = left - 1.5 * k, h.y1 + gap - 1.5 * k             # the clip has a 1.5 pt margin round its ink
            todo.append((pno, lab, pymupdf.Rect(x, y, x + clip.width * k, y + clip.height * k), qpno, clip, k))
    # a copy of the question paper without the images that none of the clips shows (they would be copied along
    # with the page otherwise - the 2018 figures are 6828x4800 pixels)
    light = pymupdf.open(qsrc)
    for qpno in sorted({t[3] for t in todo}):
        qp = light[qpno]
        clips = [t[4] for t in todo if t[3] == qpno]
        for info in qp.get_image_info():
            b = pymupdf.Rect(info['bbox'])
            if not any(b.intersects(c) for c in clips):
                qp.add_redact_annot(b & qp.rect)
        qp.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_REMOVE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                            text=pymupdf.PDF_REDACT_TEXT_NONE)
    for pno, lab, tgt, qpno, clip, k in todo:
        doc[pno].show_pdf_page(tgt, light, qpno, clip=clip)
        log.append('p%d %s: statement from question p%d %s, scale %.2f' % (
            pno + 1, lab, qpno + 1, [round(v) for v in clip], k))
    doc.save(dst, garbage=3, deflate=True)
    return log


if __name__ == '__main__':
    a = sys.argv[1:]
    whole = '--whole' in a
    only = None
    if '--only' in a:
        only = set(a[a.index('--only') + 1].split(','))
        del a[a.index('--only'):a.index('--only') + 2]
    a = [x for x in a if x != '--whole']
    for line in fill(a[0], a[1], a[2], whole, only):
        print(line)
