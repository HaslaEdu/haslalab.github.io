# -*- coding: utf-8 -*-
"""Check a built Korean CPhO edition against its source and write side-by-side review images.

usage: python -I review.py SRC.html OUT.pdf ORIGINAL.pdf FIRST [PNGDIR [DPI]]

FIRST is the 1-based source page that OUT page 1 corresponds to. Reports, per page:
  - text that collides with a stamped figure/formula, or with other text (overlapping blocks),
  - text running past the bottom margin, page-size mismatches, leftover TODO/Chinese characters.
With PNGDIR, writes pNN.png = source (left) | Korean (right) for visual review.
"""
import re, sys, pathlib
import pymupdf

HAN = re.compile(r'[㐀-鿿]')


def stamps(html):
    pages = re.split(r'<div class="page"', html)[1:]
    out = []
    for ph in pages:
        rs = []
        for m in re.finditer(r'<div class="fa[^"]*" style="([^"]*)"[^>]*>\s*<span class="fig"[^>]*data-clip="([^"]+)"[^>]*>', ph):
            st = dict(kv.split(':', 1) for kv in m.group(1).replace(' ', '').split(';') if ':' in kv)
            if 'left' not in st or 'top' not in st:
                continue
            x, y = float(st['left'].rstrip('pt')), float(st['top'].rstrip('pt'))
            x0, y0, x1, y1 = map(float, m.group(2).split(','))
            sc = re.search(r'data-scale="([\d.]+)"', m.group(0))
            sc = float(sc.group(1)) if sc else 1
            sp = re.search(r'data-srcpage="(\d+)"', m.group(0))
            rs.append((pymupdf.Rect(x, y, x + (x1 - x0) * sc, y + (y1 - y0) * sc), int(sp.group(1)) if sp else None,
                       pymupdf.Rect(x0, y0, x1, y1), sc))
        out.append(rs)
    return out


def main(src, out, orig, first, pngdir=None, dpi='60'):
    sys.stdout.reconfigure(encoding='utf-8')
    html = pathlib.Path(src).read_text(encoding='utf-8')
    a = pymupdf.open(out); b = pymupdf.open(orig); first = int(first)
    st = stamps(html)
    problems = 0
    if 'TODO' in html:
        print('TODO left in source'); problems += 1
    for i, pg in enumerate(a):
        sp = b[first - 1 + i]
        issues = []
        if abs(pg.rect.width - sp.rect.width) > 0.5 or abs(pg.rect.height - sp.rect.height) > 0.5:
            issues.append(f'size {pg.rect} vs source {sp.rect}')
        own = []          # words that belong to the stamped source pieces themselves
        for f, spn, clip, sc in (st[i] if i < len(st) else []):
            for w in b[(spn or first + i) - 1].get_text('words', clip=clip):
                own.append((w[4], f.x0 + (w[0] - clip.x0) * sc, f.y0 + (w[1] - clip.y0) * sc))
        words = [w for w in pg.get_text('words') if w[4].strip().strip('​')
                 and not any(t == w[4] and abs(x - w[0]) < 2 and abs(y - w[1]) < 2 for t, x, y in own)]
        rs = [pymupdf.Rect(w[:4]) for w in words]
        for w, r in zip(words, rs):
            if HAN.search(w[4]):
                issues.append(f'Chinese left: {w[4]!r}')
            if r.y1 > pg.rect.height - 30 and not w[4].strip().isdigit():
                issues.append(f'below bottom margin: {w[4]!r} y={r.y1:.0f}')
            for f, *_ in (st[i] if i < len(st) else []):
                inter = r & f
                if not inter.is_empty and inter.get_area() > 0.25 * r.get_area():
                    issues.append(f'text on stamp at {f.round()}: {w[4]!r} y={r.y0:.0f}')
                    break
        for j in range(len(rs)):
            for k in range(j + 1, len(rs)):
                inter = rs[j] & rs[k]
                if not inter.is_empty and inter.get_area() > 0.3 * min(rs[j].get_area(), rs[k].get_area()) > 0:
                    issues.append(f'text overlaps text: {words[j][4]!r} / {words[k][4]!r} y={rs[j].y0:.0f}')
        seen = set()
        for s in issues:
            if s not in seen:
                seen.add(s); print(f'page {i + 1}: {s}')
        problems += len(seen)
        if pngdir:
            from PIL import Image
            d = int(dpi)
            pa = pg.get_pixmap(dpi=d); pb = sp.get_pixmap(dpi=d)
            im = Image.new('RGB', (pa.w + pb.w + 8, max(pa.h, pb.h)), (128, 128, 128))
            im.paste(Image.frombytes('RGB', (pb.w, pb.h), pb.samples), (0, 0))
            im.paste(Image.frombytes('RGB', (pa.w, pa.h), pa.samples), (pb.w + 8, 0))
            pathlib.Path(pngdir).mkdir(parents=True, exist_ok=True)
            im.save(pathlib.Path(pngdir) / f'p{i + 1:02d}.png')
    print(f'{len(a)} pages, {problems} issue(s)')
    return problems


if __name__ == '__main__':
    sys.exit(1 if main(*sys.argv[1:]) else 0)
