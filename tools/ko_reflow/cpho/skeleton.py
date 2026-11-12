# -*- coding: utf-8 -*-
"""Draft a page-for-page HTML skeleton for a Korean CPhO edition from a Chinese original.

usage: python -I skeleton.py ORIGINAL.pdf FIRST-LAST OUT.html [--ocr]

For every source page in FIRST-LAST (1-based, inclusive) it finds the rows of Chinese prose
(text layer, or RapidOCR for scanned pages with --ocr / automatically when a page has no text),
masks them out, and turns every remaining patch of ink (display formulas, equation numbers,
figures, tables, page numbers) into a stamp: <span class="fig" data-srcpage data-clip>.
Prose rows are grouped into paragraph blocks positioned where the source paragraph starts;
each block carries the Chinese text in data-zh and a TODO paragraph to be translated.
Inline math in the prose is NOT stamped: it is to be retyped as KaTeX ($...$) in the
translation. Coordinates are PDF points of the source page.
"""
import re, sys, html
import numpy as np, cv2, pymupdf

CJK = re.compile(r'[㐀-鿿豈-﫿　-〿！-｠]')
HAN = re.compile(r'[㐀-鿿]')
DPI = 144
K = DPI / 72.0
_ocr = None


def ocr_rows(page):
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    pix = page.get_pixmap(dpi=DPI)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3]
    res, _ = _ocr(img)
    rows = []
    for box, text, conf in res or []:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        rows.append([min(xs) / K, min(ys) / K, max(xs) / K, max(ys) / K, text])
    return merge_rows(rows)


def text_rows(page):
    frags = []
    for b in page.get_text('dict')['blocks']:
        if b['type'] != 0:
            continue
        for l in b['lines']:
            for s in l['spans']:
                t = s['text']
                if t.strip():
                    x0, y0, x1, y1 = s['bbox']
                    frags.append([x0, y0, x1, y1, t])
    return merge_rows(frags)


def merge_rows(frags, hgap=24):
    """Join fragments that share a text row (vertical overlap of their middles) and sit within hgap pt of
    each other; text in another column on the same row (a caption beside the prose) stays separate."""
    frags = sorted(frags, key=lambda f: ((f[1] + f[3]) / 2, f[0]))
    bands = []
    for f in frags:
        cy = (f[1] + f[3]) / 2
        for r in bands:
            if r[1] - 1 <= cy <= r[3] + 1 and (f[3] - f[1]) < 2.5 * (r[3] - r[1] + 1):
                r[1] = min(r[1], f[1]); r[3] = max(r[3], f[3]); r[4].append(f)
                break
        else:
            bands.append([None, f[1], None, f[3], [f]])
    out = []
    for band in bands:
        parts = sorted(band[4], key=lambda f: f[0])
        cur = None
        for f in parts:
            if cur and f[0] - cur[2] <= hgap:
                cur[0] = min(cur[0], f[0]); cur[1] = min(cur[1], f[1]); cur[2] = max(cur[2], f[2]); cur[3] = max(cur[3], f[3])
                cur[4] += f[4]
            else:
                cur = [f[0], f[1], f[2], f[3], f[4]]
                out.append(cur)
    out.sort(key=lambda r: (r[1], r[0]))
    return out


def ink_mask(page):
    pix = page.get_pixmap(dpi=DPI)
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3].astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    dark = (a.mean(axis=2) < 200)
    reddish = (r - (g + b) / 2) > 40          # compiler watermark / red headers are not content ink
    return (dark & ~reddish).astype(np.uint8), (reddish & (a.mean(axis=2) < 230)).astype(np.uint8)


def boxes(mask, kx, ky, min_area=6):
    if not mask.any():
        return []
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (max(1, int(kx * K)), max(1, int(ky * K))))
    d = cv2.dilate(mask, k)
    n, lab, st, _ = cv2.connectedComponentsWithStats(d, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        sub = mask[y:y + h, x:x + w]
        if sub.sum() < min_area:
            continue
        ys, xs = np.nonzero(sub)
        out.append([(x + xs.min()) / K, (y + ys.min()) / K, (x + xs.max() + 1) / K, (y + ys.max() + 1) / K])
    return out


def merge_boxes(bs, pad=2.0):
    bs = [list(b) for b in bs]
    changed = True
    while changed:
        changed = False
        for i in range(len(bs)):
            for j in range(i + 1, len(bs)):
                a, b = bs[i], bs[j]
                if a[0] - pad < b[2] and b[0] - pad < a[2] and a[1] - pad < b[3] and b[1] - pad < a[3]:
                    bs[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    del bs[j]
                    changed = True
                    break
            if changed:
                break
    return sorted(bs, key=lambda b: (b[1], b[0]))


def paragraphs(rows, left_margin):
    """Group prose rows into blocks: a new block starts after a vertical gap, at an indented row, or
    when the horizontal extent changes (text beside a figure vs full width)."""
    blocks = []
    for r in rows:
        h = r[3] - r[1]
        if blocks:
            b = blocks[-1]
            last = b['rows'][-1]
            gap = r[1] - last[3]
            indent = r[0] - left_margin > 12
            same_span = abs(r[0] - b['x0']) < 25 and abs(r[2] - last[2]) < 60 or (r[2] < last[2] + 4 and abs(r[0] - b['x0']) < 25)
            if gap < 1.6 * h + 4 and not indent and same_span and last[2] > b['x1'] - 40:
                b['rows'].append(r)
                b['x1'] = max(b['x1'], r[2])
                continue
        blocks.append({'x0': r[0], 'x1': r[2], 'rows': [r]})
    return blocks


def page_skeleton(doc, pno, force_ocr):
    page = doc[pno]
    rows = text_rows(page)
    han = sum(len(HAN.findall(r[4])) for r in rows)
    use_ocr = force_ocr or han < 40
    if use_ocr:
        rows = ocr_rows(page)
    prose = [r for r in rows if HAN.search(r[4])]
    ink, red = ink_mask(page)
    left = min([r[0] for r in prose] or [72])
    paras = paragraphs(prose, left)
    m = ink.copy()
    rects = []
    for p in paras:
        x0 = p['x0']; x1 = p['x1']; y0 = min(r[1] for r in p['rows']); y1 = max(r[3] for r in p['rows'])
        rects.append((x0, y0, x1, y1))
        m[max(0, int((y0 - 2) * K)):int((y1 + 2) * K), max(0, int((x0 - 2) * K)):int((x1 + 3) * K)] = 0
    for r in prose:
        m[max(0, int(r[1] * K) - 2):int(r[3] * K) + 3, max(0, int(r[0] * K) - 2):int(r[2] * K) + 3] = 0
    stamps = []
    for s_ in merge_boxes(boxes(m, 14, 5), pad=3):
        w_, h_ = s_[2] - s_[0], s_[3] - s_[1]
        if w_ * h_ <= 6:
            continue
        near = any(s_[0] < x1 + 8 and x0 - 8 < s_[2] and s_[1] < y1 + 8 and y0 - 8 < s_[3] for x0, y0, x1, y1 in rects)
        if near and w_ < 14 and h_ < 14:
            continue          # a stray piece of inline math (superscript, fraction part): retyped with the prose
        stamps.append(s_)
    return page, paras, stamps, use_ocr


def fmt(v):
    return f'{v:.1f}'.rstrip('0').rstrip('.')


def main(src, rng, out, *flags):
    doc = pymupdf.open(src)
    a, b = (int(x) for x in rng.split('-'))
    w, h = doc[a - 1].rect.width, doc[a - 1].rect.height
    lines = [f'<!doctype html><html><head><meta name="page" content="{fmt(w)},{fmt(h)}">',
             '<style>', CSS, '</style></head><body>', '']
    for pno in range(a - 1, b):
        page, paras, stamps, used_ocr = page_skeleton(doc, pno, '--ocr' in flags)
        lines.append(f'<div class="page"><!-- source page {pno + 1}{" (OCR)" if used_ocr else ""} -->')
        items = []
        for s in stamps:
            x0, y0, x1, y1 = s[0] - 1, s[1] - 1, s[2] + 1, s[3] + 1
            items.append((y0, f'<div class="fa" style="left:{fmt(x0)}pt;top:{fmt(y0)}pt">'
                              f'<span class="fig" data-srcpage="{pno + 1}" data-clip="{fmt(x0)},{fmt(y0)},{fmt(x1)},{fmt(y1)}"></span></div>'))
        for p in paras:
            y0 = p['rows'][0][1]
            y1 = p['rows'][-1][3]
            zh = ''.join(r[4] for r in p['rows'])
            red = ''
            items.append((y0, f'<div class="a" style="left:{fmt(p["x0"])}pt;top:{fmt(y0 - 1)}pt;width:{fmt(p["x1"] - p["x0"] + 2)}pt" '
                              f'data-h="{fmt(y1 - y0 + 2)}" data-zh="{html.escape(zh, quote=True)}"><p class="ni">TODO</p></div>'))
        for _, t in sorted(items, key=lambda t: t[0]):
            lines.append(t)
        lines.append('</div>')
        lines.append('')
    lines.append('</body></html>')
    with open(out, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('\n'.join(lines) + '\n')
    print(out, b - a + 1, 'pages')


CSS = """/* CPhO (Word/SimSun 10.5pt originals): Korean body in Batang at the source size */
body{font-size:10.5pt;line-height:15.6pt}
.a{position:absolute}
.fa{position:absolute}
.ctr{text-align:center}
.red{color:#e00}
h1{font-size:16pt;font-weight:bold;margin:0;line-height:20pt;text-align:center}
p{text-indent:0}
p.in{text-indent:21pt}"""

if __name__ == '__main__':
    main(*sys.argv[1:])
