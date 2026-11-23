"""Korean editions that keep the original pages: every prose block is covered and set again in Korean in the same box.

  python3 -I block_overlay.py dump ORIG.pdf BLOCKS.json      list the text blocks of every page (id, box, size, text)
  python3 -I block_overlay.py html ORIG.pdf KO.json OUT.html  page sources for build.py, which then takes OUT.src.pdf as ORIG

KO.json: {"<page>": {"<block id>": "한국어 ($math$ allowed)", ...}, ...} — a block id is "b<n>" from the dump; a value
may also be a list [text, {"x0":…, "y0":…, "x1":…, "y1":…, "size":…, "align":"center", "lines":[i,…]}]
to widen or move the box ("lines" takes the box of only those lines of the block).
Blocks left out (display equations, figures, tables of numbers, the running header) stay exactly as printed.
The Korean of each box starts at the original type size and shrinks (to 72 % at most) until it fits the box."""
import json, re, sys
import pymupdf


def blocks(page):
    out = []
    for i, b in enumerate(page.get_text('dict')['blocks']):
        if b.get('type') != 0:
            continue
        lines, lb, lbold = [], [], []
        size = nb = nc = 0
        color = None
        for l in b['lines']:
            t = ''.join(s['text'] for s in l['spans'])
            if t.strip():
                lines.append(t)
                lb.append([round(v, 1) for v in l['bbox']])
                lbold.append(all('Bold' in s['font'] or 'bx' in s['font'].lower() for s in l['spans'] if s['text'].strip()))
                size = max(size, max(s['size'] for s in l['spans']))
                for s in l['spans']:
                    k = len(s['text'].strip())
                    if k and color is None:
                        color = s.get('color', 0)
                    nc += k
                    nb += k if ('Bold' in s['font'] or 'bx' in s['font'].lower()) else 0
        if lines:
            out.append({'id': f'b{i}', 'bbox': [round(v, 1) for v in b['bbox']], 'size': round(size, 1),
                        'bold': nb > 0.6 * nc, 'text': '\n'.join(lines), 'lines': lb, 'lbold': lbold, 'color': color or 0})
    return out


def dump(orig, out):
    d = pymupdf.open(orig)
    json.dump({str(n + 1): blocks(p) for n, p in enumerate(d)}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


FIT = """<script>addEventListener('load',()=>{for(const e of document.querySelectorAll('.kb')){let s=parseFloat(e.dataset.s),m=s*0.72;
e.style.fontSize=s+'pt';while((e.scrollHeight>e.clientHeight+s*0.5||e.scrollWidth>e.clientWidth+0.5)&&s>m){s-=0.2;e.style.fontSize=s+'pt';}}});</script>"""


def html(orig, ko, out):
    d = pymupdf.open(orig)
    tr = json.load(open(ko, encoding='utf-8'))
    W, H = d[0].rect.width, d[0].rect.height
    parts = [f'<!doctype html><html><head><meta name="page" content="{W:g},{H:g}"><style>'
             '.a{position:absolute}'
             '.kb{position:absolute;background:#fff;overflow:hidden;font-family:CM,KB,serif;line-height:1.22;text-align:justify;'
             'word-break:keep-all;overflow-wrap:anywhere}'
             '.kb.b{font-weight:bold}.kb.c{text-align:center}.kb.r{text-align:right}'
             '</style></head><body>']
    red = {}
    for n, p in enumerate(d):
        pn = str(n + 1)
        B = {b['id']: b for b in blocks(p)}
        parts.append(f'<div class="page"><div class="a" style="left:0;top:0"><span class="fig" data-srcpage="{n + 1}" '
                     f'data-clip="0,0,{p.rect.width:g},{p.rect.height:g}"></span></div>')
        for bid, val in tr.get(pn, {}).items():
            text, opt = (val, {}) if isinstance(val, str) else (val[0], val[1])
            text = re.sub(r'\$[^$]*\$', lambda m: m.group(0).replace('<', '\\lt ').replace('>', '\\gt '), text)   # no stray tags
            b = B.get(bid.split('.')[0])        # "b19.2": a second box taken from the same block
            if ':' in bid.split('.')[0]:        # "b13:b20": one box over a run of one-line blocks
                lo, hi = (int(v[1:]) for v in bid.split('.')[0].split(':'))
                run = [B[f'b{i}'] for i in range(lo, hi + 1) if f'b{i}' in B]
                b = {'bbox': [min(r['bbox'][0] for r in run), min(r['bbox'][1] for r in run), max(r['bbox'][2] for r in run),
                              max(r['bbox'][3] for r in run)], 'size': run[0]['size'], 'bold': False,
                     'lines': [l for r in run for l in r['lines']], 'lbold': [x for r in run for x in r.get('lbold', [])], 'color': run[0].get('color', 0)}
            if not b and not opt:
                sys.exit(f'page {pn}: no block {bid}')
            x0, y0, x1, y1 = b['bbox'] if b else (0, 0, 0, 0)
            if 'lines' in opt:                      # only some lines of the block (a table row next to its points)
                L = b['lines'] if opt['lines'] == 'all' else [b['lines'][i] for i in opt['lines']]
                x0, y0, x1, y1 = min(l[0] for l in L), min(l[1] for l in L), max(l[2] for l in L), max(l[3] for l in L)
            x0, y0, x1, y1 = opt.get('x0', x0), opt.get('y0', y0), opt.get('x1', x1), opt.get('y1', y1)
            size = opt.get('size', b['size'] if b else 10)
            y1 = max(y1, y0 + size * 1.4)          # one line of Korean needs a little more height than one line of Latin
            boldcell = 'lines' in opt and b.get('lbold') and all(b['lbold'][i] for i in (range(len(b['lines'])) if opt['lines'] == 'all' else opt['lines']))
            cls = 'kb ov' + (' b' if (b and (b['bold'] or boldcell) and opt.get('bold', True)) or opt.get('bold') else '') + (' c' if opt.get('align') == 'center' else ' r' if opt.get('align') == 'right' else '')
            lines = L if 'lines' in opt else (b['lines'] if b else [])
            tops = sorted(l[1] for l in lines)
            gaps = sorted(q - p for p, q in zip(tops, tops[1:]) if q - p > size * 0.8)
            pitch = gaps[len(gaps) // 2] if gaps else size * 1.22       # the original line spacing, kept in Korean
            color = opt.get('color', (b or {}).get('color', 0))
            ink = f'color:#{color:06x};' if color else ''
            if 'lines' in opt:          # a table cell: paint the English out, put the rules back, set the Korean clear
                red.setdefault(n, []).extend(pymupdf.Rect(max(l[0], x0) - 0.5, l[1] - 2, min(l[2], x1) + 0.5, l[3] + 1.2) for l in L)
                if any(k in opt for k in ('y0', 'y1')):   # a cell stretched past its lines: paint that out too
                    red[n].append(pymupdf.Rect(x0, y0, x1, y1))
                first = L[0][3] - L[0][1]
                l, t, w, h, pad, bg = x0, y0 - (pitch - first) / 2, x1 - x0, y1 - y0 + (pitch - first) / 2, '0 0 0 0.6pt', 'background:none;'
            else:
                l, t, w, h, pad, bg = x0 - 1.2, y0 - 1.5, x1 - x0 + 2.4, y1 - y0 + 2, '1pt 1.2pt 0', ''
            parts.append(f'<div class="{cls}" data-s="{size}" style="{bg}{ink}line-height:{pitch:.2f}pt;left:{l:.1f}pt;top:{t:.1f}pt;'
                         f'width:{w:.1f}pt;height:{h:.1f}pt;padding:{pad};box-sizing:border-box">{text}</div>')
        parts.append('</div>')
    parts.append(FIT + '</body></html>')
    open(out, 'w', encoding='utf-8').write('\n'.join(parts))
    for n, rs in red.items():                   # OUT.src.pdf: the original with those lines painted out; give it to build.py
        pg = d[n]
        paths = [q for q in pg.get_drawings() if any((q['rect'] + (-1, -1, 1, 1)).intersects(r) for r in rs)]
        shades = [q for q in pg.get_drawings() if q.get('fill') and min(q['rect'].width, q['rect'].height) > 5]
        for r in rs:                            # paint with the cell's own shading if it has one
            under = [q for q in shades if q['rect'].contains((r.tl + r.br) / 2)]
            pg.draw_rect(r, color=None, fill=under[-1]['fill'] if under else (1, 1, 1), overlay=True)
        sh = pg.new_shape()                    # then the rules of the table go back on top: straight level or upright
        for q in paths:                        # lines and outlined boxes only, not the slanted lines of figures
            items = [it for it in q['items'] if
                     (it[0] == 'l' and ((abs(it[1].x - it[2].x) < 0.5 and abs(it[1].y - it[2].y) > 8) or (abs(it[1].y - it[2].y) < 0.5 and abs(it[1].x - it[2].x) > 25)))
                     or (it[0] == 're' and (min(it[1].width, it[1].height) < 2.5 or not q.get('fill')) and max(it[1].width, it[1].height) > 4)]
            if not items:
                continue
            for it in items:
                if it[0] == 'l':
                    sh.draw_line(it[1], it[2])
                else:
                    sh.draw_rect(it[1])
            sh.finish(color=q.get('color'), fill=q.get('fill'), width=q.get('width') or 1, closePath=q.get('closePath', False),
                      even_odd=q.get('even_odd', False), fill_opacity=q.get('fill_opacity') or 1, stroke_opacity=q.get('stroke_opacity') or 1)
        sh.commit(overlay=True)
    d.save(out[:-5] + '.src.pdf')


if __name__ == '__main__':
    {'dump': dump, 'html': html}[sys.argv[1]](*sys.argv[2:])
