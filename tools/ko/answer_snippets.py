"""Fix the task statements cut short on the Korean answer sheets that show each task's text as a clipped piece of the
Korean question page (APhO 2018, 2023, 2024 …_A_KO.pdf).

Each answer box shows its statement through a form whose only content is «/fullpage Do» (the whole Korean question
page) and whose BBox is the area the ENGLISH statement took on the English page. The Korean text wraps differently,
so the clip cuts it: the end of a line is missing on the right (APhO 2018 T1 A «… 구하라. 그»), a last line is cut off
at the bottom, a first line at the top (APhO 2023 T2 A B.5 begins «계 전체의 …»).

For every such piece the task's frame on the question page (the stroked box around «C.5 … 1.6pt») is found and the
clip is widened to the whole of the frame's text column (between the task label and the points), trimmed to the ink.
The piece keeps its top-left corner on the answer sheet; if the larger piece would run into the next thing below it
in the answer box («답:» line, box border) or past the box's right edge, it is scaled down to fit.

The language line of the running header («Korean (Korea (Republic of))»), shown the same way, is given 2 pt more
room above and below when its glyphs touch the clip edge (APhO 2023: «of» read «ot»).

    python3 tools/ko/answer_snippets.py <ko.pdf> <out.pdf>

Only the BBox and Matrix of these forms are changed; nothing is re-typeset."""
import re
import sys

import numpy as np
import pymupdf

SNIP = re.compile(rb'^\s*q /(\w+) Do Q\s*$')
POINTS = re.compile(r'^\(?\s*[\d.]+\s*(pt|pts|점|points?)\s*\)?$')


def num_list(doc, xref, key, default=None):
    t, v = doc.xref_get_key(xref, key)
    return [float(x) for x in v.strip('[] ').split()] if t != 'null' else default


def snippets(doc, pno):
    page = doc[pno]
    names = {name: xref for xref, name, inv, _ in page.get_xobjects() if inv == 0}
    out = []
    for cx in page.get_contents():
        m = SNIP.match(doc.xref_stream(cx) or b'')
        fx = names.get(m.group(1).decode()) if m else None
        if not fx or (doc.xref_stream(fx) or b'').strip() != b'/fullpage Do':
            continue
        mt = num_list(doc, fx, 'Matrix', [1, 0, 0, 1, 0, 0])
        if mt[1] or mt[2] or mt[0] <= 0 or mt[0] != mt[3]:
            continue
        out.append(dict(cx=cx, fx=fx, bb=num_list(doc, fx, 'BBox'), m=mt))
    return out


def to_page(page, s, bb):
    """form-space box -> page rect (top-down)"""
    H = page.rect.height
    a, e, f = s['m'][0], s['m'][4], s['m'][5]
    return pymupdf.Rect(a * bb[0] + e, H - (a * bb[3] + f), a * bb[2] + e, H - (a * bb[1] + f))


def to_form(page, s, r):
    H = page.rect.height
    a, e, f = s['m'][0], s['m'][4], s['m'][5]
    return [(r.x0 - e) / a, (H - r.y1 - f) / a, (r.x1 - e) / a, (H - r.y0 - f) / a]


def isolated(src, pno, keep=None, drop=None, bbox=None):
    """a copy of the page showing only content stream `keep` (or everything but `drop`); bbox overrides keep's BBox"""
    d = pymupdf.open(src)
    p = d[pno]
    for cx in p.get_contents():
        if (keep and cx != keep['cx']) or (drop and cx == drop['cx']):
            d.update_stream(cx, b' ')
    if keep and bbox:
        d.xref_set_key(keep['fx'], 'BBox', '[%f %f %f %f]' % tuple(bbox))
    return d, d[pno]


def ink(page, clip, dpi=200, thr=210):
    """bounding rect (page coords) of dark pixels inside clip, or None"""
    clip = clip & page.rect
    if clip.is_empty:
        return None
    pix = page.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width) < thr
    if not a.any():
        return None
    k = 72.0 / dpi
    ys, xs = np.where(a.any(axis=1))[0], np.where(a.any(axis=0))[0]
    return pymupdf.Rect(clip.x0 + xs[0] * k, clip.y0 + ys[0] * k, clip.x0 + (xs[-1] + 1) * k, clip.y0 + (ys[-1] + 1) * k)


def edges(page, r):
    pix = page.get_pixmap(dpi=200, clip=r, colorspace=pymupdf.csGRAY)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width) < 210
    return dict(L=a[:, :2].any(), R=a[:, -2:].any(), T=a[:2].any(), B=a[-2:].any())


def paragraph(page, col, r, gap=6.0, dpi=144):
    """ink box of the run of text lines in `col` that overlaps r, lines joined across blank gaps up to `gap` pt
    (so a figure or a list further down the task box is left out)"""
    col = col & page.rect
    pix = page.get_pixmap(dpi=dpi, clip=col, colorspace=pymupdf.csGRAY)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width) < 210
    rows = a.any(axis=1)
    k = 72.0 / dpi
    lo = max(0, int((r.y0 - col.y0) / k))
    hi = min(len(rows) - 1, int((r.y1 - col.y0) / k))
    inked = [i for i in range(lo, hi + 1) if rows[i]]
    if not inked:
        return None
    g = int(gap / k)
    top, bot = inked[0], inked[-1]
    while True:
        up = [i for i in range(max(0, top - g), top) if rows[i]]
        if not up:
            break
        top = up[0]
    while True:
        dn = [i for i in range(bot + 1, min(len(rows), bot + 1 + g)) if rows[i]]
        if not dn:
            break
        bot = dn[-1]
    xs = np.where(a[top:bot + 1].any(axis=0))[0]
    return pymupdf.Rect(col.x0 + xs[0] * k, col.y0 + top * k, col.x0 + (xs[-1] + 1) * k, col.y0 + (bot + 1) * k)


def frame_of(page, r):
    """the task's box around the centre of r on the question page: nearest long horizontal rules above and below it
    and nearest vertical rules left and right of it (stroked boxes, filled hairline rects or lines)"""
    c = pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
    hs, vs = [], []
    for dr in page.get_drawings():
        segs = []
        for it in dr['items']:
            if it[0] == 're':
                R = pymupdf.Rect(it[1])
                if dr['type'] == 'f' and min(R.width, R.height) > 1.6:
                    continue
                if dr['type'] == 'f':
                    segs.append(R)
                else:
                    segs += [pymupdf.Rect(R.x0, R.y0, R.x1, R.y0), pymupdf.Rect(R.x0, R.y1, R.x1, R.y1),
                             pymupdf.Rect(R.x0, R.y0, R.x0, R.y1), pymupdf.Rect(R.x1, R.y0, R.x1, R.y1)]
            elif it[0] == 'l' and dr['type'] != 'f':
                segs.append(pymupdf.Rect(it[1], it[2]).normalize())
        for R in segs:
            if R.height <= 1.6 and R.width > 200:
                hs.append(R)
            elif R.width <= 1.6 and R.height > 8:
                vs.append(R)
    above = [R.y1 for R in hs if R.y1 <= r.y0 + 2 and R.x0 <= c.x <= R.x1]
    below = [R.y0 for R in hs if R.y0 >= r.y1 - 2 and R.x0 <= c.x <= R.x1]
    if not above or not below:
        return None
    top, bot = max(above), min(below)
    mid = (top + bot) / 2
    left = [R.x1 for R in vs if R.x1 <= r.x0 and R.y0 <= mid <= R.y1]
    right = [R.x0 for R in vs if R.x0 >= c.x and R.y0 <= mid <= R.y1]
    if not left or not right:
        return None
    return pymupdf.Rect(max(left), top, min(right), bot)


def fix(src, dst):
    doc = pymupdf.open(src)
    log = []
    for pno in range(doc.page_count):
        page = doc[pno]
        W, H = page.rect.width, page.rect.height
        for s in snippets(doc, pno):
            r = to_page(page, s, s['bb'])
            if r.width > W - 20:
                continue
            _, ip = isolated(src, pno, keep=s)
            e = edges(ip, r)
            if r.y1 < 160 and not any(e.values()):
                continue
            if r.y1 < 160:                                    # running header: language line
                if e['T'] or e['B']:
                    # grow the clip up/down only as far as the line's own glyphs reach (stop at the first blank row)
                    big = list(s['bb'])
                    big[1] -= 4 / s['m'][0]
                    big[3] += 4 / s['m'][0]
                    _, hp = isolated(src, pno, keep=s, bbox=big)
                    R = to_page(page, s, big)
                    pix = hp.get_pixmap(dpi=288, clip=R, colorspace=pymupdf.csGRAY)
                    rows = (np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width) < 250).any(axis=1)
                    i0, i1 = int(round((r.y0 - R.y0) * 4)), int(round((r.y1 - R.y0) * 4)) - 1
                    while i0 > 0 and rows[i0 - 1]:
                        i0 -= 1
                    while i1 < len(rows) - 1 and rows[i1 + 1]:
                        i1 += 1
                    ny0, ny1 = R.y0 + i0 / 4 - 0.3, R.y0 + (i1 + 1) / 4 + 0.3
                    nb = to_form(page, s, pymupdf.Rect(r.x0, min(ny0, r.y0), r.x1, max(ny1, r.y1)))
                    doc.xref_set_key(s['fx'], 'BBox', '[%f %f %f %f]' % tuple(nb))
                    log.append('p%d header language line: clip %.1f-%.1f -> %.1f-%.1f' % (pno + 1, r.y0, r.y1, min(ny0, r.y0), max(ny1, r.y1)))
                continue
            # the whole question page under this piece, placed as on the answer sheet
            big = [s['bb'][0] - 2000, s['bb'][1] - 2000, s['bb'][2] + 2000, s['bb'][3] + 2000]
            _, fp = isolated(src, pno, keep=s, bbox=big)
            fr = frame_of(fp, r)
            if fr is None:
                log.append('p%d piece %s: cut (%s) but no task frame found - left as is'
                           % (pno + 1, [round(v) for v in r], ''.join(x for x, v in e.items() if v)))
                continue
            x1 = fr.x1 - 3
            for t in fp.get_texttrace():
                b = pymupdf.Rect(t['bbox'])
                txt = ''.join(chr(ch[0]) for ch in t['chars']).strip()
                if b.intersects(fr) and b.x1 > fr.x1 - 70 and b.x0 > r.x1 - 20 and POINTS.match(txt):
                    x1 = min(x1, b.x0 - 3)
            col = pymupdf.Rect(r.x0 - 1, fr.y0 + 1.5, max(x1, r.x1), fr.y1 - 1.5)
            got = paragraph(fp, col, r)
            if got is None:
                continue
            new = pymupdf.Rect(min(r.x0, got.x0 - 1.5), got.y0 - 1.5, max(r.x1, got.x1 + 1.5), got.y1 + 1.5) & col
            new.x0 = r.x0
            if new.x1 <= r.x1 + 0.5 and new.y0 >= r.y0 - 0.5 and new.y1 <= r.y1 + 0.5:
                continue                                      # the statement is whole already
            # room on the answer sheet: first ink of everything else below / right of the piece's top-left corner
            _, rest = isolated(src, pno, drop=s)
            below = ink(rest, pymupdf.Rect(r.x0, r.y0 + 1, r.x0 + new.width, H))
            right = ink(rest, pymupdf.Rect(r.x0 + 1, r.y0 + 1, W, r.y0 + new.height))
            room_h = (below.y0 - 3 - r.y0) if below else H - 40 - r.y0
            room_w = (right.x0 - 3 - r.x0) if right else W - 40 - r.x0
            k = min(1.0, room_h / new.height, room_w / new.width)
            if k < 0.7:
                log.append('p%d piece %s: cut (%s); the whole statement (%.0fx%.0f) does not fit the box (scale %.2f) - left as is'
                           % (pno + 1, [round(v) for v in r], ''.join(x for x, v in e.items() if v), new.width, new.height, k))
                continue
            a = s['m'][0] * k
            nb = to_form(page, s, new)                       # in form space (old matrix)
            # keep the top-left corner where it was: page point (r.x0, r.y0)
            e_ = r.x0 - a * nb[0]
            f_ = (H - r.y0) - a * nb[3]
            doc.xref_set_key(s['fx'], 'BBox', '[%f %f %f %f]' % tuple(nb))
            doc.xref_set_key(s['fx'], 'Matrix', '[%f 0 0 %f %f %f]' % (a, a, e_, f_))
            log.append('p%d piece at y%.0f: cut at %s; clip %.0fx%.0f -> %.0fx%.0f, scale %.2f' % (
                pno + 1, r.y0, ''.join(x for x, v in e.items() if v) or 'line ends (lines hidden)', r.width, r.height, new.width, new.height, k))
    doc.save(dst, garbage=3, deflate=True)
    return log


if __name__ == '__main__':
    for line in fix(sys.argv[1], sys.argv[2]):
        print(line)
