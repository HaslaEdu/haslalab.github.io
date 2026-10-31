"""Repaint Korean lines of an overlay paper that a later white box partly hides — without uncovering the English.

The papers made by laying a translation over the original page (a form «fullpage» that paints a white box over each
English line and writes the Korean on it, fonts «kserif»/«kserifb») sometimes paint a box AFTER a Korean line it
partly overlaps, cutting the tops or bottoms of that line's glyphs. tools/ko/overlay_fix.py trims such a box, which is
right when the box has nothing else to hide; when lines are set tightly (IOAA 2025) the trimmed strip uncovers bits of
the English under it. This script instead moves each such Korean text block (q BT … ET Q, unchanged) to the end of
the overlay stream, so the whole line is drawn on top of every box while all boxes stay as they were.

    python3 tools/ko/overlay_redraw.py <ko.pdf> <out.pdf> [page,page,…]   (1-based pages; default: all)

Prints the lines it repainted. Only the overlay's own content stream is edited (text blocks reordered)."""
import re
import sys

import pymupdf

RECT = re.compile(rb'q\n([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) re\nh\n1 1 1 rg f\nQ')
TEXT = re.compile(rb'q\nBT\n1 0 0 1 ([-\d.]+) ([-\d.]+) Tm\n/(kserif\w*) [\d.]+ Tf [^\n]*TJ\nET\nQ')


def overlay_xref(doc, page):
    res = doc.xref_object(page.xref) + ''.join(doc.xref_object(int(x)) for x in re.findall(r'(\d+) 0 R', doc.xref_object(page.xref)))
    ov = None
    for x in re.findall(r'/fzFrm\d+ (\d+) 0 R', res):       # the last form with a «fullpage» child is the overlay
        m = re.search(r'/fullpage (\d+) 0 R', doc.xref_object(int(x)))
        if m:
            ov = int(m.group(1))
    return ov


def fix(src, dst, pages=None):
    doc = pymupdf.open(src)
    done = []
    for pno, page in enumerate(doc):
        if pages and pno + 1 not in pages:
            continue
        ov = overlay_xref(doc, page)
        if not ov:
            continue
        s = doc.xref_stream(ov)
        H = page.rect.height
        kor = [t for t in page.get_texttrace() if t['font'].startswith('HCR Batang') or 'kserif' in t['font']]
        texts = list(TEXT.finditer(s))
        rects = [(m.start(), pymupdf.Rect(float(m.group(1)), H - float(m.group(2)) - float(m.group(4)),
                                          float(m.group(1)) + float(m.group(3)), H - float(m.group(2)))) for m in RECT.finditer(s)]
        add = []
        for tm in texts:
            x, ty = float(tm.group(1)), H - float(tm.group(2))
            box = [t for t in kor if abs(t['bbox'][3] - ty) < 6 and abs(t['bbox'][0] - x) < 2]
            if not box:
                continue
            g = pymupdf.Rect(box[0]['bbox'])
            for rpos, r in rects:
                if rpos < tm.start():
                    continue
                ov_h = min(r.y1, g.y1) - max(r.y0, g.y0)
                if ov_h > 0.3 and min(r.x1, g.x1) - max(r.x0, g.x0) > 1 and ov_h < 0.9 * g.height:
                    add.append(tm)
                    done.append((pno + 1, ''.join(chr(c[0]) for c in box[0]['chars'])[:50]))
                    break
        if add:
            blocks = [m.group(0) for m in add]
            for m in reversed(add):
                s = s[:m.start()] + s[m.end():]
            doc.update_stream(ov, s.rstrip(b'\n') + b'\n \n' + b'\n \n'.join(blocks) + b'\n')
    doc.save(dst, garbage=3, deflate=True)
    return done


if __name__ == '__main__':
    pages = {int(p) for p in sys.argv[3].split(',')} if len(sys.argv) > 3 else None
    for p, t in fix(sys.argv[1], sys.argv[2], pages):
        print(p, t)
