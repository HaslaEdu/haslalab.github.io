# -*- coding: utf-8 -*-
"""Find source ink that a Korean edition dropped: words of the source's text layer on rows without any Chinese
(display formulas, equation numbers, labels) whose centre lies in no stamp clip of that source page.

usage: python -I coverage.py SRC.html ORIGINAL.pdf FIRST-LAST
Scanned pages (no text layer) are skipped. Words reported here must be stamped, or deliberately retyped in the
Korean text (then they are listed for a look, not necessarily wrong).
"""
import re, sys, pathlib
import pymupdf
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from skeleton import text_rows, HAN


def main(src, orig, rng):
    sys.stdout.reconfigure(encoding='utf-8')
    html = pathlib.Path(src).read_text(encoding='utf-8')
    a, b = (int(x) for x in rng.split('-'))
    clips = {}
    for m in re.finditer(r'<span class="fig"[^>]*>', html):
        t = m.group(0)
        sp = re.search(r'data-srcpage="(\d+)"', t); cl = re.search(r'data-clip="([^"]+)"', t)
        if sp and cl:
            clips.setdefault(int(sp.group(1)), []).append(pymupdf.Rect(*map(float, cl.group(1).split(','))))
    doc = pymupdf.open(orig)
    total = 0
    for pno in range(a, b + 1):
        page = doc[pno - 1]
        rows = text_rows(page)
        if sum(len(HAN.findall(r[4])) for r in rows) < 40:
            continue
        cs = clips.get(pno, [])
        miss = []
        for r in rows:
            if HAN.search(r[4]):
                continue
            for w in page.get_text('words', clip=pymupdf.Rect(r[:4]) + (-1, -1, 1, 1)):
                c = pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
                if not w[4].strip() or any(c in k for k in cs):
                    continue
                miss.append((round(w[1]), round(w[0]), w[4]))
        if miss:
            total += len(miss)
            print(f'source page {pno}: ' + ' '.join(f'{t}@({x},{y})' for y, x, t in sorted(miss))[:400])
    print(f'{total} uncovered word(s)')


if __name__ == '__main__':
    main(*sys.argv[1:])
