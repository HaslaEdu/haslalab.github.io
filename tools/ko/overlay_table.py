"""Rebuild table rows of a Korean overlay paper whose Korean was set as ONE line across the row (IOAA solutions:
«순위   안시 등급 (mV)   고유 이름   바이어 명칭» in the left of the header while the cells keep their boxes).

For each overlay line (q BT … TJ ET Q, font kserif/kserifb) whose text has gaps of two or more spaces and that lies
on a table row (vertical rules through it):
  * the cells are the gaps between the vertical rules; the English the line replaced is the original text under the
    white boxes painted for it (the boxes right before the line in the stream that overlap it);
  * the Korean segments (split at the gaps) are matched in order to the cells that hold such English; a segment that
    spells several cells («AV AK <I>») is split at its single spaces when that makes the counts agree;
  * a cell whose Korean is the English (numbers, symbols, names) gets nothing: the original stays visible;
  * any other cell gets a white box over its English words only and its Korean centred in the cell (left-aligned
    where the English is), on the English baseline (vertically centred for a two-line English header).
The old line and its row-wide boxes are removed. Rows that cannot be matched are reported and left alone.

    python3 tools/ko/overlay_table.py <ko.pdf> <out.pdf> [page,page,…]
"""
import re
import sys
import unicodedata

import pymupdf

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from overlay_redraw import overlay_xref  # noqa: E402

BLOCK = re.compile(rb'q\n([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) re\nh\n1 1 1 rg f\nQ'
                   rb'|q\nBT\n1 0 0 1 ([-\d.]+) ([-\d.]+) Tm\n/(kserif\w*) ([\d.]+) Tf ([^\n]*?)\[<([0-9a-f]+)>\]TJ\nET\nQ')
SUB = str.maketrans({'◦': '°', '″': '′′', '−': '-', '⁻': '-', '¹': '1', '²': '2', '': 'μ'})


def norm(s):
    s = unicodedata.normalize('NFKC', s.translate(SUB))
    return re.sub(r'\s+', '', s)


def cells_of(xs):
    xs = sorted(xs)
    out = []
    for a, b in zip(xs, xs[1:]):
        if b - a > 6:
            out.append((a, b))
    return out


def background(pix, x, y0, y1):
    """the fill colour of a cell: the commonest colour of a thin strip at its left inside edge (white if unsure)"""
    from collections import Counter
    k = 144 / 72
    cols = Counter()
    for yy in range(int(y0 * k), int(y1 * k)):
        for xx in (int(x * k), int(x * k) + 1, int(x * k) + 2):
            if 0 <= xx < pix.width and 0 <= yy < pix.height:
                cols[pix.pixel(xx, yy)[:3]] += 1
    if not cols:
        return (1, 1, 1)
    c, n = cols.most_common(1)[0]
    if n < 0.6 * sum(cols.values()) or min(c) < 150:
        return (1, 1, 1)
    return tuple(v / 255 for v in c)


def align(segs, idx, tr, full, cells):
    """match Korean segments to cells in order when the counts differ: a segment takes a cell whose English it equals,
    or (if it has Hangul) any cell; a cell may be skipped (its English stays)."""
    INF = 1e9
    txt = [''.join(chr(tr['chars'][i][0]) for i in sg if i is not None) for sg in segs]
    etx = [norm(' '.join(e[1] for e in full[c])) for c in idx]
    n, k = len(segs), len(idx)
    dp = [[INF] * (k + 1) for _ in range(n + 1)]
    bk = {}
    dp[0][0] = 0
    for i in range(n + 1):
        for j in range(k + 1):
            if dp[i][j] >= INF:
                continue
            if j < k and dp[i][j] + 1 < dp[i][j + 1]:
                dp[i][j + 1] = dp[i][j] + 1
                bk[(i, j + 1)] = (i, j, False)
            if i < n and j < k:
                if norm(txt[i]) == etx[j]:
                    c = 0
                elif re.search('[가-힣]', txt[i]):
                    ii = [q for q in segs[i] if q is not None]
                    a_, b_ = tr['chars'][ii[0]][3][0], tr['chars'][ii[-1]][3][2]
                    c0, c1 = cells[idx[j]]
                    c = 0.9 - 0.8 * max(0, min(b_, c1) - max(a_, c0)) / max(1, b_ - a_)   # prefer the cell it lies over
                else:
                    c = INF
                if dp[i][j] + c < dp[i + 1][j + 1]:
                    dp[i + 1][j + 1] = dp[i][j] + c
                    bk[(i + 1, j + 1)] = (i, j, True)
    if dp[n][k] >= INF:
        return None
    pairs, ij = [], (n, k)
    while ij != (0, 0):
        i, j, mt = bk[ij]
        if mt:
            pairs.append((segs[i], idx[j]))
        ij = (i, j)
    return pairs[::-1]


def merge_continuations(doc, pages, report):
    """A table entry the overlay set on two Korean lines inside one cell (the second line often only the points):
    join the second line onto the first (one space between) and move its white boxes next to the first line's, so
    the entry is rebuilt as a whole."""
    for pno, page in enumerate(doc):
        if pages and pno + 1 not in pages:
            continue
        ov = overlay_xref(doc, page)
        if not ov:
            continue
        H = page.rect.height
        hrules = [d['rect'] for d in page.get_drawings() if d['rect'].height < 2 and d['rect'].width > 15]
        vrules = [d['rect'] for d in page.get_drawings() if d['rect'].width < 2 and d['rect'].height > 4]
        while True:
            s = doc.xref_stream(ov)
            blocks = list(BLOCK.finditer(s))
            kor = [t for t in page.get_texttrace() if 'Batang' in t['font'] or 'kserif' in t['font']]
            lines = []
            for bi, m in enumerate(blocks):
                if not m.group(5):
                    continue
                x, base = float(m.group(5)), H - float(m.group(6))
                tr = [t for t in kor if abs(t['bbox'][3] - base) < 6 and abs(t['bbox'][0] - x) < 2]
                if tr:
                    lines.append((bi, m, pymupdf.Rect(tr[0]['bbox']), float(m.group(8))))
            done = False
            for i, (b1, m1, r1, z1) in enumerate(lines):
                for b2, m2, r2, z2 in lines:
                    if b2 == b1:
                        continue
                    if not (0.4 * z1 < r2.y1 - r1.y1 < 1.8 * z1 and -3 < r2.x0 - r1.x0 < 60 and m1.group(7) == m2.group(7)):
                        continue
                    ux0, ux1 = min(r1.x0, r2.x0), max(r1.x1, r2.x1)
                    span = lambda h: min(h.x1, ux1) - max(h.x0, ux0) > 0.5 * (min(r1.width, r2.width))
                    if any(span(h) and (r1.y0 + r1.y1) / 2 < (h.y0 + h.y1) / 2 < (r2.y0 + r2.y1) / 2 for h in hrules):
                        continue                                    # a rule between them: two rows
                    ab = [h.y1 for h in hrules if span(h) and h.y1 <= r1.y0 + 1]
                    be = [h.y0 for h in hrules if span(h) and h.y0 >= r2.y1 - 1]
                    if not ab or not be or min(be) - max(ab) > 4.5 * z1:
                        continue                                    # not a table cell
                    ym = (r1.y1 + r2.y0) / 2
                    if len({round(v.x0) for v in vrules if v.y0 < ym < v.y1}) < 3:
                        continue                                    # a framed paragraph, not a table
                    # the boxes painted for line 2
                    bx = []
                    j = b2 - 1
                    while j >= 0 and blocks[j].group(1):
                        bx.append(blocks[j])
                        j -= 1
                    joined = m1.group(10) + b'0005' + m2.group(10)
                    new1 = s[m1.start():m1.start(10)] + joined + s[m1.end(10):m1.end()]
                    run = b''.join(q.group(0) + b'\n \n' for q in reversed(bx))
                    cuts = sorted([(m1.start(), m1.end(), run + new1), (m2.start(), m2.end(), b'')] +
                                  [(q.start(), q.end(), b'') for q in bx], key=lambda c: -c[0])
                    t = s
                    for a, b, n in cuts:
                        t = t[:a] + n + t[b:]
                    doc.update_stream(ov, t)
                    report.append((pno + 1, 'joined', '%r + %r' % (round(r1.y0), round(r2.y0))))
                    done = True
                    break
                if done:
                    break
            if not done:
                break


def fix(src, dst, pages=None):
    doc = pymupdf.open(src)
    report = []
    merge_continuations(doc, pages, report)
    for pno, page in enumerate(doc):
        if pages and pno + 1 not in pages:
            continue
        ov = overlay_xref(doc, page)
        if not ov:
            continue
        s = doc.xref_stream(ov)
        H = page.rect.height
        blocks = list(BLOCK.finditer(s))
        kor = [t for t in page.get_texttrace() if 'Batang' in t['font'] or 'kserif' in t['font']]
        en = [(pymupdf.Rect(sp['bbox']), sp['text'], sp['origin'][1], sp['size']) for b in page.get_text('dict')['blocks'] if b['type'] == 0
              for l in b['lines'] for sp in l['spans'] if 'Batang' not in sp['font'] and sp['text'].strip()]
        rules = [d['rect'] for d in page.get_drawings() if d['rect'].width < 2 and d['rect'].height > 4]
        drop, add, keep, seen = [], [], {}, set()
        hrules = [d['rect'] for d in page.get_drawings() if d['rect'].height < 2 and d['rect'].width > 15]
        pix = page.get_pixmap(dpi=144)
        for bi, m in enumerate(blocks):
            if not m.group(5):
                continue
            x, base = float(m.group(5)), H - float(m.group(6))
            tr = [t for t in kor if abs(t['bbox'][3] - base) < 6 and abs(t['bbox'][0] - x) < 2]
            if not tr:
                continue
            tr = tr[0]
            text = ''.join(chr(c[0]) for c in tr['chars'])
            multi = bool(re.search(r'\S {2,}\S', text))
            if not text.strip():
                continue
            kb = pymupdf.Rect(tr['bbox'])
            vx = [r.x0 for r in rules if r.y0 < kb.y1 - 1 and r.y1 > kb.y0 + 1]
            if len(vx) < 3:
                continue
            cells = cells_of(vx)
            # white boxes painted for this line: the run of boxes right before it that touch it
            mine = []
            j = bi - 1
            while j >= 0 and blocks[j].group(1):
                bx, by, bw, bh = (float(v) for v in blocks[j].group(1, 2, 3, 4))
                r = pymupdf.Rect(bx, H - by - bh, bx + bw, H - by)
                if r.intersects(kb):
                    mine.append((blocks[j], r))
                j -= 1
            if not mine:
                continue
            covered = [r for _, r in mine]
            if not multi:
                # a single cell entry: only when its box runs over a rule of the table (cut rules, a row set as one line)
                if not (any(min(h.x1, r.x1) - max(h.x0, r.x0) > 5 and r.y0 + 0.6 < (h.y0 + h.y1) / 2 < r.y1 - 0.6
                            for h in hrules for r in covered) or
                        any(r.x0 + 0.6 < v.x0 < r.x1 - 0.6 and min(v.y1, r.y1) - max(v.y0, r.y0) > 2 for v in rules for r in covered)):
                    continue
                rows_ok = False
                for r in covered:
                    ab = [h.y1 for h in hrules if min(h.x1, r.x1) - max(h.x0, r.x0) > 0.6 * r.width and h.y1 <= kb.y1 + 2]
                    be = [h.y0 for h in hrules if min(h.x1, r.x1) - max(h.x0, r.x0) > 0.6 * r.width and h.y0 >= kb.y0 - 2]
                    if ab and be and min(be) - max(ab) < 3.2 * float(m.group(8)):
                        rows_ok = True
                if not rows_ok:
                    continue
                key = (round(x, 1), round(base, 1), m.group(10))
                if key in seen:
                    drop += [m] + [b for b, _ in mine]                  # a second copy of the same entry
                    continue
                seen.add(key)
            enl = [e for e in en if any(r.contains(pymupdf.Point((e[0].x0 + e[0].x1) / 2, (e[0].y0 + e[0].y1) / 2)) for r in covered)
                   and cells[0][0] < (e[0].x0 + e[0].x1) / 2 < cells[-1][1]]
            # units: (row, column) of the table, row by row
            def rowkey(e, c):
                ecy = (e[0].y0 + e[0].y1) / 2
                ab = [h.y1 for h in hrules if min(h.x1, c[1]) - max(h.x0, c[0]) > 0.8 * (c[1] - c[0]) and h.y1 <= ecy]
                return round(max(ab), 1) if ab else -1
            units = {}
            for e in enl:
                for ci_, c in enumerate(cells):
                    if c[0] < (e[0].x0 + e[0].x1) / 2 < c[1]:
                        units.setdefault((rowkey(e, c), ci_), []).append(e)
            ukeys = sorted(units)
            if not multi and len({k[0] for k in ukeys}) > 1 and not re.search(r'[가-힣]\S* +-?\d+(\.\d+)? +\S*[가-힣]', text):
                cy = (covered[0].y0 + covered[0].y1) / 2                   # one entry: the row its box is about
                best = min(ukeys, key=lambda k: min(abs((e[0].y0 + e[0].y1) / 2 - cy) for e in units[k]))
                ukeys = [k for k in ukeys if k[0] == best[0]]
            full = [units[k] for k in ukeys]
            ucells = [cells[k[1]] for k in ukeys]
            idx = list(range(len(full)))
            # Korean segments with their glyph ranges
            gl = [m.group(10)[i:i + 4] for i in range(0, len(m.group(10)), 4)]
            if len(gl) != len(tr['chars']):
                report.append((pno + 1, 'skip (glyph count)', text[:40]))
                continue
            segs, cur, sp = [], [], 0
            for i, c in enumerate(tr['chars']):
                if c[0] == 32:
                    sp += 1
                    continue
                if sp >= 2 and cur:
                    segs.append(cur)
                    cur = []
                elif sp == 1 and cur:
                    cur.append(None)                                   # single space inside a segment
                sp = 0
                cur.append(i)
            if cur:
                segs.append(cur)
            new = []
            for sg in segs:
                st = ''.join(chr(tr['chars'][i][0]) for i in sg if i is not None)
                if not re.search('[가-힣]', st) or len(segs) >= len(idx):
                    new.append(sg)
                    continue
                words, depth = [[]], 0
                for i in sg:
                    if i is None:
                        words.append([])
                    else:
                        words[-1].append(i)
                cur2 = []
                wts = [''.join(chr(tr['chars'][i][0]) for i in w) for w in words]
                for wi, w in enumerate(words):
                    wt = wts[wi]
                    nxt = wts[wi + 1] if wi + 1 < len(wts) else None
                    isnum = re.fullmatch(r'-?\d+(\.\d+)?', wt) and depth == 0 and (nxt is None or re.search('[가-힣]', nxt))
                    depth += wt.count('(') - wt.count(')')
                    if isnum:
                        if cur2:
                            new.append(cur2)
                        new.append(list(w))
                        cur2 = []
                    else:
                        cur2 = cur2 + ([None] if cur2 else []) + list(w)
                if cur2:
                    new.append(cur2)
            segs = new
            if len(segs) != len(idx):
                # split a segment spelling several cells at its single spaces
                new = []
                k = 0
                for sg in segs:
                    words = [[]]
                    for i in sg:
                        if i is None:
                            words.append([])
                        else:
                            words[-1].append(i)
                    st = norm(''.join(chr(tr['chars'][i][0]) for i in sg if i is not None))
                    done = False
                    for n in range(2, len(words) + 1):
                        if k + n <= len(idx) and len(words) == n and st == ''.join(norm(''.join(e[1] for e in full[idx[k + q]])) for q in range(n)):
                            new += [[i for i in w] for w in words]
                            k += n
                            done = True
                            break
                    if not done:
                        new.append(sg)
                        k += 1
                segs = new
            if len(segs) < len(idx):
                etxs = {norm(' '.join(e[1] for e in f)) for f in full if f}
                new = []
                for sg in segs:
                    if None in sg:
                        cut = len(sg) - 1 - sg[::-1].index(None)
                        tail = ''.join(chr(tr['chars'][i][0]) for i in sg[cut + 1:])
                        if norm(tail) in etxs and re.search('[가-힣]', ''.join(chr(tr['chars'][i][0]) for i in sg[:cut] if i is not None)):
                            new += [sg[:cut], sg[cut + 1:]]
                            continue
                    new.append(sg)
                segs = new
            pairs = list(zip(segs, idx)) if len(segs) == len(idx) else align(segs, idx, tr, full, ucells)
            if pairs is None:
                report.append((pno + 1, 'skip (%d segments, %d cells)' % (len(segs), len(idx)), text[:50]))
                continue
            size = float(m.group(8))
            pre = m.group(9)
            out = []
            overflow = False
            kbc = (kb.y0 + kb.y1) / 2
            vr = [r for r in rules if r.y0 <= kbc <= r.y1 and cells[0][0] - 1 <= r.x0 <= cells[-1][1] + 1]
            band = pymupdf.Rect(cells[0][0], min(r.y0 for r in vr), cells[-1][1], max(r.y1 for r in vr))
            # the whole table: every rule connected to this row
            allr = rules + hrules
            grown = True
            while grown:
                grown = False
                for r in allr:
                    if r.intersects(band + (-1.5, -1.5, 1.5, 1.5)) and not band.contains(r):
                        band |= r
                        grown = True
            band = band + (-1.5, -1.5, 1.5, 1.5)
            for sg, ci in pairs:
                ii = [i for i in sg if i is not None]
                ktxt = ''.join(chr(tr['chars'][i][0]) for i in range(ii[0], ii[-1] + 1))
                ens = full[ci]
                etxt = ' '.join(e[1] for e in ens)
                if norm(ktxt) == norm(etxt):
                    continue                                            # same in Korean: keep the original
                hexs = b''.join(gl[i] for i in range(ii[0], ii[-1] + 1))
                w = tr['chars'][ii[-1]][3][2] - tr['chars'][ii[0]][3][0]
                eb = pymupdf.Rect(ens[0][0])
                for e in ens:
                    eb |= e[0]
                c0, c1 = ucells[ci]
                ecy = (eb.y0 + eb.y1) / 2
                above = [h.y1 for h in hrules if min(h.x1, c1) - max(h.x0, c0) > 0.8 * (c1 - c0) and h.y1 <= ecy]   # table rules, not underlines
                below = [h.y0 for h in hrules if min(h.x1, c1) - max(h.x0, c0) > 0.8 * (c1 - c0) and h.y0 >= ecy]
                top = max(above) + 0.8 if above else band.y0
                bot = min(below) - 0.8 if below else band.y1
                box = pymupdf.Rect(max(eb.x0 - 0.8, c0 + 1.2), max(eb.y0 - 0.3, top), min(eb.x1 + 0.8, c1 - 1.2), min(eb.y1 + 0.3, bot))
                centred = abs((eb.x0 - c0) - (c1 - eb.x1)) < 8 and eb.width < 0.7 * (c1 - c0)   # English in the middle of its cell
                lines = sorted({round(e[2]) for e in ens})
                nb = ens[0][2] if len(lines) == 1 else ecy + 0.35 * size
                parts = [(ii[0], ii[-1])]
                if w > c1 - c0 - 3:
                    # two lines: cut at the space nearest the middle
                    sp_ = [i for i in range(ii[0], ii[-1]) if tr['chars'][i][0] == 32]
                    if sp_:
                        midx = (tr['chars'][ii[0]][3][0] + tr['chars'][ii[-1]][3][2]) / 2
                        k = min(sp_, key=lambda i: abs(tr['chars'][i][3][0] - midx))
                        parts = [(ii[0], k - 1), (k + 1, ii[-1])]
                        box = pymupdf.Rect(box.x0, max(min(box.y0, ecy - 1.15 * size), top), box.x1, min(max(box.y1, ecy + 1.15 * size), bot))
                bg = background(pix, c0 + 1.5, top + 0.5, bot - 0.5)
                out.append(b'q\n%.2f %.2f %.2f %.2f re\nh\n%.3f %.3f %.3f rg f\nQ' % (box.x0, H - box.y1, box.width, box.height, *bg))
                for pi, (a_, b_) in enumerate(parts):
                    hx = b''.join(gl[i] for i in range(a_, b_ + 1))
                    ww = tr['chars'][b_][3][2] - tr['chars'][a_][3][0]
                    px = (c0 + c1) / 2 - ww / 2 if (centred or len(parts) > 1) else eb.x0
                    if ww > c1 - c0 - 1:
                        overflow = True
                        px = c0 + 1.5
                    pb = nb if len(parts) == 1 else ecy + (-0.25 + 1.2 * pi) * size
                    out.append(b'q\nBT\n1 0 0 1 %.2f %.3f Tm\n/%s %s Tf %s[<%s>]TJ\nET\nQ' % (px, H - pb, m.group(7), m.group(8), pre, hx))
            if overflow:
                report.append((pno + 1, 'skip (text wider than its cell)', text.strip()[:50]))
                continue
            # the line's own boxes: keep what they hide outside this row
            for b, r in mine:
                pieces = [pymupdf.Rect(r.x0, r.y0, r.x1, min(r.y1, band.y0)), pymupdf.Rect(r.x0, max(r.y0, band.y1), r.x1, r.y1),
                          pymupdf.Rect(r.x0, max(r.y0, band.y0), min(r.x1, band.x0), min(r.y1, band.y1)),
                          pymupdf.Rect(max(r.x0, band.x1), max(r.y0, band.y0), r.x1, min(r.y1, band.y1))]
                # inside the table, go on hiding the English of other rows this box was over
                done_ = {id(e) for _, ci in pairs for e in full[ci]}
                for e in en:
                    if id(e) not in done_ and e[0].intersects(r) and band.contains(e[0]):
                        q = r & (e[0] + (-0.6, -0.4, 0.6, 0.4))
                        pieces.append(q)
                keep[b] = b'\n \n'.join(b'q\n%.2f %.2f %.2f %.2f re\nh\n1 1 1 rg f\nQ' % (q.x0, H - q.y1, q.width, q.height)
                                         for q in pieces if q.width > 0.5 and q.height > 0.5)
            drop += [m]
            add += out
            report.append((pno + 1, 'rebuilt', text.strip()[:60]))
        if drop:
            for b in sorted(set(drop) | set(keep), key=lambda b: -b.start()):
                s = s[:b.start()] + keep.get(b, b'') + s[b.end():]
            s = s.rstrip(b'\n') + b'\n \n' + b'\n \n'.join(add) + b'\n'
            doc.update_stream(ov, s)
    doc.save(dst, garbage=3, deflate=True)
    return report


if __name__ == '__main__':
    pages = {int(p) for p in sys.argv[3].split(',')} if len(sys.argv) > 3 else None
    for r in fix(sys.argv[1], sys.argv[2], pages):
        print(*r)
