# -*- coding: utf-8 -*-
"""Draft a tools/ko_reflow source from an original PDF: one <div class="page"> per page, each prose block an
absolutely placed div at the original's position holding the English text (to be replaced by Korean), and
every figure, image, logo and pure-math display line as a stamp placeholder.

usage: python -I skeleton.py ORIGINAL.pdf OUT.html [first-last]
The draft is a starting point: the translator fixes block grouping, replaces the English and reviews stamps.
"""
import re, sys, statistics
import pymupdf

MATHFONT = re.compile(r'CMMI|CMSY|CMEX|CMBXTI|MSBM|MSAM|LMMath|TeX-math|MathDesign-CH-.*(Math|Symbol|Extension)|'
                      r'CambriaMath|Cambria Math|^Symbol|ESSTIX|BBOLD|rsfs|eufm|Wingdings', re.I)
OPS = {'sin', 'cos', 'tan', 'cot', 'exp', 'log', 'ln', 'det', 'tr', 'lim', 'max', 'min', 'sinh', 'cosh', 'tanh',
       'arctan', 'arcsin', 'arccos', 'const', 'Tr', 'Re', 'Im', 'erf', 'sgn', 'mod', 'and', 'for', 'with', 'if',
       'where', 'or', 'd'}


LABEL = re.compile(r'^\s*([•–▪·\-]|\(?[a-z]\)|\(?[ivx]+[.)]|\d+[.)]|[a-z]\.)\s')


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def clusters(rects, gap=6):
    rects = [pymupdf.Rect(r) for r in rects]
    out = []
    for r in rects:
        out.append(r)
    changed = True
    while changed:
        changed = False
        res = []
        while out:
            r = out.pop()
            hit = True
            while hit:
                hit = False
                for o in out[:]:
                    if (r + (-gap, -gap, gap, gap)).intersects(o):
                        r = r | o
                        out.remove(o)
                        hit = changed = True
            res.append(r)
        out = res
    return out


def page_items(pg):
    W, H = pg.rect.width, pg.rect.height
    area = W * H
    lines = []
    for b in pg.get_text('dict')['blocks']:
        if b['type'] != 0:
            continue
        for l in b['lines']:
            sp = [s for s in l['spans'] if s['text'].strip()]
            if not sp:
                continue
            lines.append({'bbox': pymupdf.Rect(l['bbox']), 'spans': sp,
                          'text': ''.join(s['text'] for s in l['spans']).strip()})
    gfx = []
    for d in pg.get_drawings():
        r = pymupdf.Rect(d['rect'])
        if r.width < 0.5 and r.height < 0.5:
            continue
        if r.width < 0.8:
            r.x0, r.x1 = r.x0 - 0.4, r.x1 + 0.4
        if r.height < 0.8:
            r.y0, r.y1 = r.y0 - 0.4, r.y1 + 0.4
        if r.get_area() > 0.6 * area:
            continue
        gfx.append(r)
    for im in pg.get_image_info():
        r = pymupdf.Rect(im['bbox']) & pg.rect
        if r.is_empty or r.get_area() > 0.6 * area:
            continue
        gfx.append(r)
    # horizontal rules wider than 60% of the page are kept as their own stamps, not merged with text
    figs = [f for f in clusters([r for r in gfx if not (r.height < 2.5 and r.width > 0.6 * W)]) if f.width > 1.5 or f.height > 1.5]
    rules = [r for r in gfx if r.height < 2.5 and r.width > 0.6 * W]
    return W, H, lines, figs, rules


def is_math(line, body):
    for s in line['spans']:
        if MATHFONT.search(s['font']):
            continue
        for w in re.findall(r'[A-Za-z]{3,}', s['text']):
            if w not in OPS:
                return False
    return True


def main(src, out, rng=None):
    d = pymupdf.open(src)
    for p in d:
        if p.rotation:
            p.remove_rotation()
    pages = range(len(d))
    if rng:
        a, b = map(int, rng.split('-'))
        pages = range(a - 1, b)
    # body font/size: most characters
    cnt = {}
    for p in d:
        for b in p.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    k = (s['font'], round(s['size'], 1))
                    cnt[k] = cnt.get(k, 0) + len(s['text'])
    body = max(cnt, key=cnt.get) if cnt else ('?', 11)
    S = body[1]
    L = round(S * 1.21, 1)
    W0, H0 = d[0].rect.width, d[0].rect.height
    o = [f'<!doctype html><html><head><meta name="page" content="{W0:g},{H0:g}">', '<style>',
         f'/* drafted by skeleton.py from {src.split("/")[-1]}; body font {body[0]} {S}pt */',
         f'body{{font-size:{S}pt;line-height:{L}pt}}',
         '.a{position:absolute}', '.a>p{text-indent:0}', '.f{position:absolute;line-height:0}',
         '</style></head><body>', '']
    for pn in pages:
        pg = d[pn]
        W, H, lines, figs, rules = page_items(pg)
        o.append(f'<!-- {pn + 1} -->')
        o.append('<div class="page">')
        if not lines and not figs:
            o.append('<!-- no text layer: scanned page; read the render and place text by hand -->')
        # lines inside a figure cluster belong to the figure
        fl = []
        prose = []
        for ln in lines:
            r = ln['bbox']
            host = None
            for f in figs:
                inter = (f + (-3, -3, 3, 3)) & r
                if not inter.is_empty and inter.get_area() > 0.5 * r.get_area():
                    host = f
                    break
            if host is not None:
                fl.append(ln)
            else:
                prose.append(ln)
        items = []
        for f in figs:
            items.append(('fig', f, None))
        for r in rules:
            items.append(('fig', r + (0, -0.5, 0, 0.5), 'rule'))
        # merge prose lines into paragraphs
        prose.sort(key=lambda l: (round(l['bbox'].y0), l['bbox'].x0))
        # join lines on the same baseline
        rows = []
        for ln in prose:
            if rows and abs(rows[-1]['bbox'].y1 - ln['bbox'].y1) < 2 and 0 <= ln['bbox'].x0 - rows[-1]['bbox'].x1 < 18:
                rows[-1] = {'bbox': rows[-1]['bbox'] | ln['bbox'], 'spans': rows[-1]['spans'] + ln['spans'],
                            'text': rows[-1]['text'] + ' ' + ln['text']}
            else:
                rows.append(ln)
        blocks = []
        for ln in rows:
            m = is_math(ln, body)
            if blocks:
                b = blocks[-1]
                last = b['lines'][-1]['bbox']
                gap = ln['bbox'].y0 - last.y1
                sz = max(s['size'] for s in ln['spans'])
                dx = ln['bbox'].x0 - b['lines'][-1]['bbox'].x0
                aligned = abs(dx) < 3 or (len(b['lines']) == 1 and -40 < dx < 30) or m
                if b['math'] == m and gap < (0.6 * sz if not m else 0.35 * sz) and aligned and not LABEL.match(ln['text']):
                    b['lines'].append(ln)
                    continue
            blocks.append({'math': m, 'lines': [ln]})
        for b in blocks:
            r = pymupdf.Rect(b['lines'][0]['bbox'])
            for ln in b['lines']:
                r |= ln['bbox']
            if b['math']:
                items.append(('fig', r + (-1, -1, 1, 1), 'math: ' + ' / '.join(l['text'] for l in b['lines'])))
            else:
                items.append(('text', r, b))
        items.sort(key=lambda it: (it[1].y0, it[1].x0))
        for kind, r, extra in items:
            if kind == 'fig':
                note = f' <!-- {esc(extra)[:150]} -->' if extra else ''
                if r.height < 0.6:
                    r = r + (0, -0.4, 0, 0.4)
                o.append(f'<div class="f" style="left:{r.x0:.1f}pt;top:{r.y0:.1f}pt"><span class="fig" '
                         f'data-srcpage="{pn + 1}" data-clip="{r.x0:.1f},{r.y0:.1f},{r.x1:.1f},{r.y1:.1f}"></span></div>{note}')
                continue
            b = extra
            ln0 = b['lines'][0]
            sz = statistics.median([s['size'] for l in b['lines'] for s in l['spans']])
            base = ln0['spans'][0]['origin'][1]
            bold = all(s['flags'] & 16 or 'Bold' in s['font'] or 'BX' in s['font'] for s in ln0['spans'])
            if len(b['lines']) > 1:
                lh = (b['lines'][-1]['spans'][0]['origin'][1] - base) / (len(b['lines']) - 1)
            else:
                lh = L if abs(sz - S) < 0.3 else round(sz * 1.21, 1)
            top = base - (lh - sz) / 2 - 0.78 * sz
            x0 = min(l['bbox'].x0 for l in b['lines'])
            x1 = max(l['bbox'].x1 for l in b['lines'])
            ind = ln0['bbox'].x0 - x0
            style = f'left:{x0:.1f}pt;top:{top:.1f}pt;width:{x1 - x0:.1f}pt'
            if abs(sz - S) > 0.3:
                style += f';font-size:{sz:.1f}pt'
            if abs(lh - L) > 0.3:
                style += f';line-height:{lh:.1f}pt'
            if bold:
                style += ';font-weight:bold'
            eng = '\n'.join(esc(l['text']) for l in b['lines'])
            pin = f' style="text-indent:{ind:.1f}pt"' if ind > 3 else ''
            o.append(f'<div class="a" style="{style}"><p{pin}>{eng}</p></div>')
        o.append('</div>')
        o.append('')
    o.append('</body></html>')
    open(out, 'w', encoding='utf-8', newline='\n').write('\n'.join(o) + '\n')
    print(out, len(pages), 'pages; body', body)


if __name__ == '__main__':
    main(*sys.argv[1:4])
