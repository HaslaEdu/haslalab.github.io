"""Widen the clip windows of Korean answer sheets built from clips of the Korean paper (IPhO 2019 T1–T3 answer
sheets: each question box shows a piece of the translated paper page through a form «fzFrmN» whose /BBox is the
window and whose /fullpage child is the paper page). Several windows were sized for the English text, so the Korean
question is cut off at the right («그 순간의 다른 / 를 계산하시오.») or a line is cut at the top/bottom.

For every window, the question it shows is found in the paper: when the paper frames the question (a box around it),
the window is grown to hold everything in that frame (text and drawn formulas) right of the window's left edge,
minus the question label («A.6») and the points («0.8pt») that the answer box already prints; without a frame, to
hold entirely every paper line it partly shows (at least half its height and some of its width inside). The grown window is kept inside the question box
of the answer page and is not allowed to take in any other text; if it would, it is left alone and reported.
(Header windows, above y=160, are not touched.)

    python3 tools/ko/answer_clip_fix.py <ko_answer.pdf> <out.pdf>

Only /BBox entries of those forms change."""
import re
import sys

import pymupdf

QLABEL = re.compile(r'^\s*[A-Z]\.\d+\s*$')
POINTS = re.compile(r'^\s*\d+(\.\d+)?\s*(pt|점)\s*$')


def forms(doc, page):
    res = doc.xref_get_key(page.xref, 'Resources')
    rx = int(res[1].split()[0]) if res[0] == 'xref' else None
    txt = doc.xref_object(rx) if rx else doc.xref_object(page.xref)
    out = []
    for name, x in re.findall(r'/(fzFrm\d+) (\d+) 0 R', txt):
        o = doc.xref_object(int(x))
        m = re.search(r'/fullpage (\d+) 0 R', o)
        b = re.search(r'/BBox \[ *([-\d. ]+)\]', o)
        mt = re.search(r'/Matrix \[ *([-\d. ]+)\]', o)
        if m and b:
            out.append((name, int(x), [float(v) for v in b.group(1).split()],
                        [float(v) for v in mt.group(1).split()] if mt else [1, 0, 0, 1, 0, 0]))
    return out


def spans_through(doc, pno, fname, H):
    """text spans of the paper page as this form would place them, with the window opened to the whole page"""
    tmp = pymupdf.open()
    tmp.insert_pdf(doc, from_page=pno, to_page=pno)
    t = tmp[0]
    for name, x, b, m in forms(tmp, t):
        tmp.xref_set_key(x, 'BBox', '[-5000 -5000 5000 5000]' if name == fname else '[0 0 0 0]')   # xrefs differ in the copy
    out = []
    for blk in t.get_text('dict')['blocks']:
        for ln in blk.get('lines', []):
            for sp in ln['spans']:
                if sp['text'].strip():
                    out.append((pymupdf.Rect(sp['bbox']), sp['text'], ln['bbox']))
    return out, [dr['rect'] for dr in t.get_drawings()]


def own_spans(doc, pno):
    tmp = pymupdf.open()
    tmp.insert_pdf(doc, from_page=pno, to_page=pno)
    t = tmp[0]
    for name, x, b, m in forms(tmp, t):
        tmp.xref_set_key(x, 'BBox', '[0 0 0 0]')
    return [pymupdf.Rect(s['bbox']) for blk in t.get_text('dict')['blocks'] for ln in blk.get('lines', [])
            for s in ln['spans'] if s['text'].strip()], [d['rect'] for d in t.get_drawings()]


def fix(src, dst):
    doc = pymupdf.open(src)
    report = []
    for pno, page in enumerate(doc):
        H = page.rect.height
        fl = forms(doc, page)
        if not fl:
            continue
        mine, drawings = own_spans(doc, pno)
        boxes = [r for r in drawings if r.width > 400 and r.height > 40]     # the question boxes
        for name, x, b, m in fl:
            a, _, _, d, e, f = m
            if a <= 0 or d <= 0:
                continue
            # window in page coordinates (PDF y up -> fitz y down)
            win = pymupdf.Rect(a * b[0] + e, H - (d * b[3] + f), a * b[2] + e, H - (d * b[1] + f))
            if (win.width > 450 and win.height > 400) or win.y1 < 160:
                continue                                                   # copies of the page head (title, language line)
            box = [r for r in boxes if r.contains(pymupdf.Rect(win.x0 + 1, win.y0 + 1, win.x0 + 2, win.y0 + 2))]
            if not box:
                continue
            box = max(box, key=lambda r: r.get_area())         # the answer box, not a paper frame seen through a window
            sp, paths = spans_through(doc, pno, name, H)

            def is_label(r, t):                       # «A.6» left of the window, or the points; not «과제 B.2에서»
                return bool(POINTS.match(t)) or (bool(QLABEL.match(t)) and r.x1 <= win.x0 + 3)

            frame = [r for r in paths if r.width > 300 and r.height > 15 and r.contains(pymupdf.Point(win.x0 + 1, win.y0 + 1))
                     and r.contains(pymupdf.Point(win.x0 + 1, win.y1 - 1))]

            def grow(use_frame):
                take, other = [], []
                if use_frame:
                    # the paper's own frame around this question: everything in it but its label and points
                    fr = min(frame, key=lambda r: r.get_area())
                    inner = pymupdf.Rect(fr.x0 + 1, fr.y0 + 1, fr.x1 - 1, fr.y1 - 1)
                    for r, t, lb in sp:
                        (take if inner.contains(r) and not is_label(r, t) and r.x0 >= win.x0 - 1 else other).append(r)
                    labels = [r for r, t, lb in sp if is_label(r, t)]      # Type3 text also comes back as paths
                    pts = [r.x0 for r, t, lb in sp if POINTS.match(t) and inner.contains(r)]
                    limit = min(pts) - 8 if pts else inner.x1          # stay out of the points column
                    take = [r for r in take if r.x1 <= limit]
                    # formulas drawn as paths: take those that continue the text (gaps under 25pt), left of the points
                    cand = sorted((r for r in paths if inner.contains(r) and r.width < fr.width - 10 and r.x0 >= win.x0 - 1
                                   and r.x1 <= limit and not any(r.intersects(q) for q in labels)), key=lambda r: r.x0)
                    grew = True
                    while grew:
                        grew = False
                        for r in cand:
                            if r in take:
                                continue
                            if any(abs((r.y0 + r.y1) / 2 - (q.y0 + q.y1) / 2) < 12 and r.x0 - q.x1 < 25 and q.x0 - r.x1 < 25 for q in take):
                                take.append(r)
                                grew = True
                else:
                    # a line is shown when part of it is in the window: take all of it (but its label/points)
                    lines = {}
                    for r, t, lb in sp:
                        lines.setdefault(tuple(round(v, 1) for v in lb), []).append((r, t))
                    for lb, items in lines.items():
                        shown = any(min(r.y1, win.y1) - max(r.y0, win.y0) >= 0.5 * r.height and min(r.x1, win.x1) - max(r.x0, win.x0) > 0
                                    and not is_label(r, t) for r, t in items)
                        for r, t in items:
                            (take if shown and not is_label(r, t) else other).append(r)
                if not take:
                    return None, None
                new = pymupdf.Rect(win)
                for r in take:
                    new |= r
                new = pymupdf.Rect(new.x0 - 0.5, new.y0 - 0.5, new.x1 + 0.5, new.y1 + 0.5)
                if all(abs(u - v) < 0.6 for u, v in zip(new, win)):
                    return None, None
                if new.x1 > box.x1 - 2:
                    return None, ('too wide for the box', [round(v) for v in new])
                new.x0 = max(new.x0, box.x0 + 2)
                clash = [r for r in other if (r & new).get_area() > 0.3 * r.get_area() and not (r & win).get_area() > 0.3 * r.get_area()]
                clash += [r for r in mine if (r & new).get_area() > 1 and not r.intersects(win)]
                if clash:
                    return None, ('would take in other text', [round(v) for v in clash[0]], [round(v) for v in new])
                if new.y1 > box.y1 - 2 or new.y0 < box.y0:
                    return None, ('would leave the box', [round(v) for v in new])
                return new, None

            new, why = grow(True) if frame else (None, None)
            if new is None:
                new, why2 = grow(False)
                why = why2 or why
            if new is None:
                if why:
                    report.append((pno + 1, name, 'left alone:', *why))
                continue
            # back to form space
            nb = [(new.x0 - e) / a, (H - new.y1 - f) / d, (new.x1 - e) / a, (H - new.y0 - f) / d]
            doc.xref_set_key(x, 'BBox', '[%.4f %.4f %.4f %.4f]' % tuple(nb))
            report.append((pno + 1, name, 'window %s -> %s' % ([round(v) for v in win], [round(v) for v in new])))
    doc.save(dst, garbage=3, deflate=True)
    return report


if __name__ == '__main__':
    for r in fix(sys.argv[1], sys.argv[2]):
        print(*r)
