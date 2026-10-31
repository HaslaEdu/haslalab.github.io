"""Fix two faults of the Korean papers made by laying a translation over the original page (a form «fullpage» that
paints a white box over each English line and writes the Korean on it, fonts «kserif»/«kserifb»):

1. a white box painted after a Korean line that it partly overlaps hides the bottom (or top) of that line's glyphs
   (APhO 2003 E1: «경고: …»). The box is trimmed back to the line's edge — it still covers the English it was for.
2. the middle item of the running header (APhO 2003: «실험 경연» between the olympiad and the date) is set where the
   English left it, off the middle; it is centred where the original's centre is.

    python3 tools/ko/overlay_fix.py <ko.pdf> <original.pdf> <out.pdf>

Only the overlay's own content stream is edited (its «re» and «Tm» operands); the original page under it is not
touched."""
import re
import sys

import pymupdf

HANGUL = lambda s: any('가' <= c <= '힣' for c in s)
RECT = re.compile(rb'(?m)^([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) re\nh\n1 1 1 rg f$')
TEXT = re.compile(rb'1 0 0 1 ([-\d.]+) ([-\d.]+) Tm\n/(\w+) ([\d.]+) Tf [^\n]*?\[<([0-9a-f]+)>\]TJ')


def fix(src, orig, dst):
    doc, en = pymupdf.open(src), pymupdf.open(orig)
    changed = 0
    for pno, page in enumerate(doc):
        # the overlay stream of this page: the form named fullpage reachable from the page's resources
        res = doc.xref_object(page.xref) + ''.join(doc.xref_object(int(x)) for x in re.findall(r'(\d+) 0 R', doc.xref_object(page.xref)))
        xs = [int(x) for x in re.findall(r'/fzFrm\d+ (\d+) 0 R', res)]
        ov = None
        for x in xs:
            m = re.search(r'/fullpage (\d+) 0 R', doc.xref_object(x))
            if m:
                ov = int(m.group(1))
        if not ov:
            continue
        s = doc.xref_stream(ov)
        H = page.rect.height
        # Korean lines in stream order, with their glyph boxes from the rendered page (texttrace, same order)
        kor = [t for t in page.get_texttrace() if HANGUL(''.join(chr(c[0]) for c in t['chars']))]
        rects = [(m.start(), m) for m in RECT.finditer(s)]
        texts = [(m.start(), m) for m in TEXT.finditer(s)]
        edits = []
        # 1. a white box painted after a Korean line it partly overlaps
        for ti, (tpos, tm) in enumerate(texts):
            ty = H - float(tm.group(2))                        # baseline in page coordinates
            box = [t for t in kor if abs(t['bbox'][3] - ty) < 6 and abs(t['bbox'][0] - float(tm.group(1))) < 2]
            if not box:
                continue
            g = pymupdf.Rect(box[0]['bbox'])
            for rpos, rm in rects:
                if rpos < tpos:
                    continue
                x, y, w, h = (float(v) for v in rm.groups())
                r = pymupdf.Rect(x, H - y - h, x + w, H - y)
                ov_h = min(r.y1, g.y1) - max(r.y0, g.y0)
                if ov_h <= 0.3 or min(r.x1, g.x1) - max(r.x0, g.x0) <= 1 or ov_h > 0.6 * g.height:
                    continue
                if r.y0 > g.y0:                               # the box is below the line: start it under the glyphs
                    r.y0 = g.y1 + 0.3
                else:                                         # above: end it over them
                    r.y1 = g.y0 - 0.3
                if r.height > 1:
                    edits.append((rm.span(), b'%.2f %.2f %.2f %.2f re\nh\n1 1 1 rg f' % (r.x0, H - r.y1, r.width, r.height)))
        # 2. the middle item of the running header, centred as in the original
        # (a running header: two long rules no more than 20 pt apart within the top 60 pt — not a table near the top)
        box = [d['rect'] for d in page.get_drawings() if d['rect'].y1 < 60 and d['rect'].width > 300 and d['rect'].height < 1.5]
        if len(box) >= 2 and max(r.y1 for r in box) - min(r.y0 for r in box) <= 20 and pno < len(en):
            top, bot = min(r.y0 for r in box), max(r.y1 for r in box)
            mid = (box[0].x0 + box[0].x1) / 2
            ech = [c for b in en[pno].get_text('rawdict')['blocks'] if b['type'] == 0 for l in b['lines'] for sp in l['spans']
                   for c in sp['chars'] if top < c['bbox'][1] < bot and c['c'].strip()]
            emid = [c for c in ech if abs((c['bbox'][0] + c['bbox'][2]) / 2 - mid) < 90]
            for tpos, tm in texts:
                ty = H - float(tm.group(2))
                if not (top < ty < bot + 2):
                    continue
                k = [t for t in kor if abs(t['bbox'][0] - float(tm.group(1))) < 2 and abs(t['bbox'][3] - ty) < 6]
                if not k or not emid:
                    continue
                kb = pymupdf.Rect(k[0]['bbox'])
                if abs((kb.x0 + kb.x1) / 2 - mid) > 90:     # the left or right item
                    continue
                ec = (min(c['bbox'][0] for c in emid) + max(c['bbox'][2] for c in emid)) / 2
                nx = ec - kb.width / 2
                if abs(nx - kb.x0) > 1:
                    a, b = tm.span(1)
                    edits.append(((a, b), b'%.2f' % nx))
        if not edits:
            continue
        for (a, b), new in sorted(edits, key=lambda e: -e[0][0]):
            s = s[:a] + new + s[b:]
        doc.update_stream(ov, s)
        changed += len(edits)
    doc.save(dst, garbage=3, deflate=True)
    return changed


if __name__ == '__main__':
    print(fix(*sys.argv[1:4]), 'edits')
