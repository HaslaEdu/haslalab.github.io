# -*- coding: utf-8 -*-
"""Flag regions where the source page has ink and the Korean page is blank (a dropped figure or formula).

usage: python -I missing.py OUT.pdf ORIGINAL.pdf FIRST [PNGDIR]
Both pages are rendered at 36 dpi, reduced to 6-pt cells; a cell is "ink" when it holds dark (non-red) pixels.
Source ink cells with no ink within one cell in the Korean page are grouped; groups of 6+ cells are reported
(and, with PNGDIR, drawn in red on a side-by-side image) for a look. Text that moved a line or two is tolerated.
"""
import sys, pathlib
import numpy as np, cv2, pymupdf

DPI = 36
CELL = 3   # px at 36 dpi = 6 pt


def ink(page):
    pix = page.get_pixmap(dpi=DPI)
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3].astype(int)
    m = (a.mean(axis=2) < 170) & ~((a[:, :, 0] - (a[:, :, 1] + a[:, :, 2]) / 2) > 40)
    h, w = m.shape
    m = m[:h - h % CELL, :w - w % CELL]
    return m.reshape(m.shape[0] // CELL, CELL, m.shape[1] // CELL, CELL).sum(axis=(1, 3)) >= 2, pix


def main(out, orig, first, pngdir=None):
    a = pymupdf.open(out); b = pymupdf.open(orig); first = int(first)
    total = 0
    for i, pg in enumerate(a):
        s, spix = ink(b[first - 1 + i]); k, kpix = ink(pg)
        h = min(s.shape[0], k.shape[0]); w = min(s.shape[1], k.shape[1])
        s, k = s[:h, :w], k[:h, :w]
        near = cv2.dilate(k.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        lost = (s & ~near).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(lost, np.ones((2, 2), np.uint8)), 8)
        boxes = []
        for j in range(1, n):
            x, y, ww, hh, area = st[j]
            cnt = int(lost[y:y + hh, x:x + ww].sum())
            if cnt >= 6:
                boxes.append((x * 6, y * 6, (x + ww) * 6, (y + hh) * 6, cnt))
        if boxes:
            total += len(boxes)
            print(f'page {i + 1}: ' + '; '.join(f'({x0},{y0})-({x1},{y1}) {c} cells' for x0, y0, x1, y1, c in boxes))
            if pngdir:
                from PIL import Image, ImageDraw
                d = 72  # side-by-side for a look
                pa = b[first - 1 + i].get_pixmap(dpi=d); pk = pg.get_pixmap(dpi=d)
                im = Image.new('RGB', (pa.w + pk.w + 6, pa.h), (128, 128, 128))
                im.paste(Image.frombytes('RGB', (pa.w, pa.h), pa.samples), (0, 0))
                im.paste(Image.frombytes('RGB', (pk.w, pk.h), pk.samples), (pa.w + 6, 0))
                dr = ImageDraw.Draw(im)
                for x0, y0, x1, y1, _ in boxes:
                    for off in (0, pa.w + 6):
                        dr.rectangle((x0 + off, y0, x1 + off, y1), outline=(255, 0, 0), width=2)
                pathlib.Path(pngdir).mkdir(parents=True, exist_ok=True)
                im.save(pathlib.Path(pngdir) / f'm{i + 1:02d}.png')
    print(f'{total} region(s) to look at')


if __name__ == '__main__':
    main(*sys.argv[1:])
