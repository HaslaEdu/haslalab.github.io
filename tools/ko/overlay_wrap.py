"""Wrap Korean lines of an overlay paper that run past the right margin (IOAA 2025 solutions: one long Korean line set
where the English took two or three, so its end runs off the page).

The line (a q BT … [<glyph ids>]TJ ET Q block of the overlay form «fullpage», font kserif/kserifb, 2-byte glyph ids)
is cut at the last space that still ends left of the margin; the rest is set as a new line of the same font, size
and colour one leading lower, at the continuation indent. The new line goes only where the page is blank (checked on
the rendered page, after hiding the long line): the space the English lines left once the overlay's white box
covered them. It is drawn at the end of the overlay stream, after those boxes. Nothing else is moved.

    python3 tools/ko/overlay_wrap.py <ko.pdf> <out.pdf> [--right 540] [--trigger 552] [--lead 13.5] [--indent X]

--right: the margin the cut line must end before; --trigger: only lines ending past this x are wrapped (a line
ending just past the margin but short of the points box at the right is left alone).

--indent: x of the continuation line; default: the x of the English text that follows the item label on the English
line under it, else the line's own x.
Prints what it wrapped, and what it could not (no blank space below)."""
import argparse
import re
import sys

import pymupdf

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from overlay_redraw import overlay_xref  # noqa: E402

TEXT = re.compile(rb'q\nBT\n1 0 0 1 ([-\d.]+) ([-\d.]+) Tm\n/(kserif\w*) ([\d.]+) Tf ([^\n]*?)\[<([0-9a-f]+)>\]TJ\nET\nQ')


def blank(page, rect):
    pix = page.get_pixmap(dpi=100, clip=rect, colorspace=pymupdf.csGRAY)
    return min(pix.samples) > 235 if pix.samples else False


def run(src, dst, right=540.0, lead=13.5, indent=None, trigger=552.0):
    doc = pymupdf.open(src)
    report = []
    for pno, page in enumerate(doc):
        ov = overlay_xref(doc, page)
        if not ov:
            continue
        s = doc.xref_stream(ov)
        H = page.rect.height
        kor = [t for t in page.get_texttrace() if 'Batang' in t['font'] or 'kserif' in t['font']]
        edits, tails = [], []
        for tm in TEXT.finditer(s):
            x, base = float(tm.group(1)), H - float(tm.group(2))
            tr = [t for t in kor if abs(t['bbox'][3] - base) < 6 and abs(t['bbox'][0] - x) < 2 and t['bbox'][2] > trigger]
            if not tr:
                continue
            t = tr[0]
            gids = [tm.group(6)[i:i + 4] for i in range(0, len(tm.group(6)), 4)]
            if len(gids) != len(t['chars']):
                report.append((pno + 1, 'skip: glyph count', ''.join(chr(c[0]) for c in t['chars'])[:40]))
                continue
            ch = t['chars']
            # cut after the last space whose preceding glyph ends left of the margin
            cut = None
            for i, c in enumerate(ch):
                if c[0] == 32 and i > 0 and ch[i - 1][3][2] <= right:
                    cut = i
            if cut is None:
                continue
            rest = cut + 1
            while rest < len(ch) and ch[rest][0] == 32:
                rest += 1
            if rest >= len(ch):
                continue
            if indent is not None:
                nx = indent
            else:
                # the English text after the item label on the same line (e.g. «(D02.3d)  Using the graph…»)
                en = [sp['bbox'][0] for b in page.get_text('dict')['blocks'] if b['type'] == 0 for l in b['lines']
                      for sp in l['spans'] if 'Batang' not in sp['font'] and sp['text'].strip()
                      and abs(sp['origin'][1] - base) < 6 and x + 20 < sp['bbox'][0] < x + 80]
                nx = min(en) if en else x
                nx = round(nx, 2)
            width = ch[-1][3][2] - ch[rest][2][0]
            nb = base + lead
            size = float(tm.group(4))
            area = pymupdf.Rect(nx - 1, nb - size - 1, nx + width + 1, nb + size * 0.35)
            if nx + width > right + 1:
                report.append((pno + 1, 'skip: rest too long', ''.join(chr(c[0]) for c in ch)[:40]))
                continue
            # look at the page without the long line: hide it for the check
            probe = pymupdf.open()
            probe.insert_pdf(doc, from_page=pno, to_page=pno)
            pv = overlay_xref(probe, probe[0])
            probe.update_stream(pv, probe.xref_stream(pv).replace(tm.group(0), b''))
            if not blank(probe[0], area):
                report.append((pno + 1, 'skip: no blank space below', ''.join(chr(c[0]) for c in ch)[:40]))
                continue
            head = b''.join(gids[:cut])
            tail = b''.join(gids[rest:])
            new = b'q\nBT\n1 0 0 1 %s %s Tm\n/%s %s Tf %s[<%s>]TJ\nET\nQ' % (tm.group(1), tm.group(2), tm.group(3), tm.group(4), tm.group(5), head)
            # the continuation goes at the end of the stream, after the white boxes that hide the English lines there
            tails.append(b'q\nBT\n1 0 0 1 %.2f %.3f Tm\n/%s %s Tf %s[<%s>]TJ\nET\nQ' % (nx, H - nb, tm.group(3), tm.group(4), tm.group(5), tail))
            edits.append((tm.span(), new))
            s_ = ''.join(chr(c[0]) for c in ch)
            report.append((pno + 1, 'wrapped', s_[:cut].strip()[-25:] + ' / ' + s_[rest:][:25]))
        if edits:
            for (a, b), new in sorted(edits, key=lambda e: -e[0][0]):
                s = s[:a] + new + s[b:]
            doc.update_stream(ov, s.rstrip(b'\n') + b'\n \n' + b'\n \n'.join(tails) + b'\n')
    doc.save(dst, garbage=3, deflate=True)
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--right', type=float, default=540.0)
    ap.add_argument('--trigger', type=float, default=552.0)
    ap.add_argument('--lead', type=float, default=13.5)
    ap.add_argument('--indent', type=float)
    a = ap.parse_args()
    for r in run(a.src, a.dst, a.right, a.lead, a.indent, a.trigger):
        print(*r)
