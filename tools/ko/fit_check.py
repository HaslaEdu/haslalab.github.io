"""Find what runs over a table's column rule in a PDF: ink just left or right of a vertical rule, on rows where no
horizontal rule meets it (cells keep a few points of padding, so ink touching a rule is content that overran it).

    python3 -I tools/ko/fit_check.py FILE.pdf [...]

Prints (page, rule x, y from, y to) for each run of such rows; nothing printed after a file means it is clean.  Double
rules (an answer sheet's 0.5 pt pairs) show up as two hits 1.4 pt apart on every row of a box: those are not overruns.
"""
import sys
import numpy as np
import pymupdf

Z = 4


def scan(path):
    doc, out = pymupdf.open(path), []
    for pno, page in enumerate(doc):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(Z, Z), colorspace=pymupdf.csGRAY)
        ink = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width) < 110
        hits = {}
        for r in (d['rect'] for d in page.get_drawings() if d['rect'].width < 1.5 and d['rect'].height > 15):
            y0, y1 = int((r.y0 + 1.5) * Z), int((r.y1 - 1.5) * Z)
            if y1 <= y0:
                continue
            band = lambda u, v: ink[y0:y1, max(0, int(u * Z)):int(v * Z)].any(1)
            touch = band(r.x0 - 1.9, r.x0 - 0.5) | band(r.x1 + 0.5, r.x1 + 1.9)
            across = band(r.x0 - 9, r.x0 - 7) & band(r.x1 + 7, r.x1 + 9)       # a horizontal rule meeting it
            for y in np.nonzero(touch & ~across)[0]:
                hits.setdefault(round(r.x0, 1), []).append((y + y0) / Z)
        for x, ys in sorted(hits.items()):
            ys.sort()
            runs = [[ys[0], ys[0]]]
            for y in ys[1:]:
                if y - runs[-1][1] < 4:
                    runs[-1][1] = y
                else:
                    runs.append([y, y])
            out += [(pno + 1, x, round(a, 1), round(b, 1)) for a, b in runs if b - a >= 0.5]
    return out


if __name__ == '__main__':
    for f in sys.argv[1:]:
        found = scan(f)
        print(f, len(found))
        for h in found:
            print('  page %d  rule x=%.1f  y %.1f–%.1f' % h)
