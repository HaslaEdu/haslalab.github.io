# -*- coding: utf-8 -*-
"""Cut the NBPhO booklets into one PDF per problem, for practice mode.

    python tools/nbpho_split.py <folder with the booklets>

NBPhO publishes one booklet with every problem (theory and experimental) and one with every solution, laid out in
two to four columns on landscape pages.  For each year this finds the problem headings («5. CANDY-WRAPPER (8 points)»)
in reading order (page, column, top to bottom), takes each problem from its heading to the next one, column by
column, and stacks those pieces on pages of their own: pdfx/nbpho/NBPhO_<year>_P<n>_EN.pdf and NBPhO_<year>_P<n>S.pdf.
Each piece is the booklet's own page with everything outside the problem redacted away and the page cropped to it,
so text and figures stay vector; the fonts are cut down to the glyphs used.
The number of problems of a year comes from tools/theory/nbpho.json (its theory ids and the experimental problems in
its note); a booklet whose headings cannot all be found is reported and left whole.
Needs PyMuPDF and fontTools (pip install pymupdf fonttools).
"""
import json
import os
import re
import sys
from collections import Counter

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'pdfx', 'nbpho')
HEAD = re.compile(r'^(?:Problem\s+)?(\d{1,2})\s*\.(?:\s|$)')


def lines(doc):
    for pno, pg in enumerate(doc):
        for b in pg.get_text('dict')['blocks']:
            for k, l in enumerate(b.get('lines', [])):
                sp = l['spans']
                if not sp:
                    continue
                t = ''.join(s['text'] for s in sp).strip()
                if not t:
                    continue
                yield pno, l['bbox'], t, max(s['size'] for s in sp), any('Bold' in s['font'] or s['flags'] & 16 for s in sp), b, k


def columns(doc):
    """the left edges of the text columns, from where lines start"""
    xs = Counter(round(bb[0] / 4) * 4 for _, bb, *_ in lines(doc))
    total = sum(xs.values())
    starts = []
    for x, n in sorted(xs.items(), key=lambda kv: -kv[1]):
        if n < 0.04 * total:
            break
        if all(abs(x - s) > 90 for s in starts):
            starts.append(x)
    return sorted(starts)


def headings(doc, n, cols):
    """the headings of problems 1..n in reading order; some years number each of the two rounds from 1 (2016: 1–5, 1–5)"""
    for seq in [list(range(1, n + 1))] + [list(range(1, a + 1)) + list(range(1, n - a + 1)) for a in range(2, n - 1)]:
        h = headings_seq(doc, seq, cols)
        if h:
            return h
    return None


def headings_seq(doc, seq, cols):
    """the headings carrying the numbers of seq, in reading order: the best-scoring such sequence"""
    n = max(seq)
    cand = []
    for pno, bb, t, size, bold, b, k in lines(doc):
        m = HEAD.match(t)
        if not m or not 1 <= int(m.group(1)) <= n:
            continue
        ci = min(range(len(cols)), key=lambda i: abs(cols[i] - bb[0]))
        if abs(cols[ci] - bb[0]) > 14:
            continue
        near = ' '.join(''.join(s['text'] for s in l['spans']) for l in b['lines'][k:k + 3])
        score = size + (6 if bold else 0) + (5 if re.search(r'\(\s*\d+(?:[.,]\d+)?\s*(?:points?|pts?|p)\b', near, re.I) else 0) + (3 if k == 0 else 0)
        cand.append(((pno, ci, bb[1]), int(m.group(1)), score))
    cand.sort()
    best = {0: (0, [])}                                # best[i]: the best way to have found seq[:i]
    for pos, num, score in cand:                       # DP over seq, in reading order
        for i in range(len(seq), 0, -1):
            if seq[i - 1] != num or (i - 1) not in best:
                continue
            prev = best[i - 1]
            if prev[1] and prev[1][-1] >= pos:
                continue
            tot = prev[0] + score
            if i not in best or tot > best[i][0]:
                best[i] = (tot, prev[1] + [pos])
    return best[len(seq)][1] if len(seq) in best else None


def scanned(page):
    """a page that is mostly picture (a scan): pieces of it are drawn as pictures, else every piece keeps the whole image"""
    area = sum(r.get_area() for img in page.get_images() for r in page.get_image_rects(img[0]))
    return area > 0.3 * page.rect.get_area()


def cut(doc, heads, cols, out_name, nums):
    W, H = doc[0].rect.width, doc[0].rect.height
    edges = cols + [W + 6]
    slots = [(p, c) for p in range(doc.page_count) for c in range(len(cols))]
    rect = lambda p, c, y0, y1: pymupdf.Rect(max(0, edges[c] - 6), max(0, y0), min(W, edges[c + 1] - 6), min(H, y1))
    made = {}
    for i, n in enumerate(nums):
        (p, c, y) = heads[i]
        end = heads[i + 1] if i + 1 < len(heads) else (doc.page_count - 1, len(cols) - 1, H)
        pieces = []
        for s in slots[slots.index((p, c)):slots.index(end[:2]) + 1]:
            y0 = y - 2 if s == (p, c) else 0
            y1 = end[2] - 3 if s == end[:2] else H
            r = rect(s[0], s[1], y0, y1)
            if r.height > 8 and (doc[s[0]].get_text('text', clip=r).strip() or doc[s[0]].get_drawings() and any(r.intersects(d['rect']) for d in doc[s[0]].get_drawings())):
                pieces.append((s[0], r))
        if not pieces:
            continue
        o = pymupdf.open()
        for pno, r in pieces:                               # each piece a page of its own: what lies outside is removed
            if scanned(doc[pno]):                           # a scanned page: the piece as a picture, at 150 dpi
                pix = doc[pno].get_pixmap(clip=r, dpi=150)
                pg = o.new_page(width=r.width, height=r.height)
                pg.insert_image(pg.rect, stream=pix.tobytes('jpeg', jpg_quality=72))
                continue
            o.insert_pdf(doc, from_page=pno, to_page=pno)
            pg = o[-1]
            full = pg.rect
            for z in (pymupdf.Rect(full.x0, full.y0, full.x1, r.y0), pymupdf.Rect(full.x0, r.y1, full.x1, full.y1),
                      pymupdf.Rect(full.x0, r.y0, r.x0, r.y1), pymupdf.Rect(r.x1, r.y0, full.x1, r.y1)):
                if z.width > 0.5 and z.height > 0.5:
                    pg.add_redact_annot(z)
            pg.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED)
            box = (pymupdf.Rect(r) * pg.derotation_matrix).normalize() & pg.mediabox   # in unrotated page space
            if not box.is_empty:
                pg.set_cropbox(box)
        try:
            o.rewrite_images(dpi_threshold=160, dpi_target=130, quality=72)   # photographs at screen resolution
        except Exception as e:
            print('images kept', out_name(n), e)
        try:
            o.subset_fonts()
        except Exception as e:
            print('fonts not subset', out_name(n), e)
        name = out_name(n)
        o.save(os.path.join(OUT, name), garbage=4, deflate=True, clean=True)
        made[n] = name
    return made


def main(src):
    os.makedirs(OUT, exist_ok=True)
    man = json.load(open(os.path.join(ROOT, 'tools', 'theory', 'nbpho.json'), encoding='utf-8'))
    index, report = {}, []
    for y in man['years']:
        year = y['y']
        theory = [int(p['id'][1:]) for p in y['problems']]
        exp = [int(x) for x in re.findall(r'(\d+) \(', y.get('note', '').split('experimental')[0])]
        n = max(theory + exp)
        titles = {int(p['id'][1:]): p['title'] for p in y['problems']}
        for x, t in re.findall(r'(\d+) \(([^)]*)\)', y.get('note', '')):
            titles.setdefault(int(x), t)
        entry = {'n': n, 'exp': exp, 'titles': {str(k): v for k, v in sorted(titles.items())}, 'paper': {}, 'sol': {}}
        for kind, names, fmt in (('paper', ['T_EN', 'E_EN'], 'NBPhO_%d_P%%d_EN.pdf'), ('sol', ['TS', 'S'], 'NBPhO_%d_P%%dS.pdf')):
            path = next((os.path.join(src, 'NBPhO_%d_%s.pdf' % (year, k)) for k in names if os.path.exists(os.path.join(src, 'NBPhO_%d_%s.pdf' % (year, k)))), None)
            if not path:
                report.append('%d %s: no booklet' % (year, kind))
                continue
            doc = pymupdf.open(path)
            cols = columns(doc)
            heads = headings(doc, n, cols) if cols else None
            if not heads:
                report.append('%d %s: headings not all found (%d problems, columns %s)' % (year, kind, n, cols))
                continue
            made = cut(doc, heads, cols, lambda k, f=fmt % year: f % k, list(range(1, n + 1)))
            entry[kind] = {str(k): v for k, v in made.items()}
        index[str(year)] = entry
    json.dump(index, open(os.path.join(OUT, 'index.json'), 'w'), ensure_ascii=False, indent=1, sort_keys=True)
    print('\n'.join(report) or 'every booklet cut')
    print(sum(len(e['paper']) + len(e['sol']) for e in index.values()), 'files')


if __name__ == '__main__':
    main(sys.argv[1])
