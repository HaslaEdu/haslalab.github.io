"""Korean editions that keep the original pages: every prose block is covered and set again in Korean in the same box.

  python3 -I block_overlay.py dump ORIG.pdf BLOCKS.json      list the text blocks of every page (id, box, size, text)
  python3 -I block_overlay.py html ORIG.pdf KO.json OUT.html  page sources for build.py, which then takes OUT.src.pdf as ORIG

KO.json: {"<page>": {"<block id>": "한국어 ($math$ allowed)", ...}, ...} — a block id is "b<n>" from the dump; a value
may also be a list [text, {"x0":…, "y0":…, "x1":…, "y1":…, "size":…, "align":"center", "lines":[i,…]}]
to widen or move the box ("lines" takes the box of only those lines of the block).
Blocks left out (display equations, figures, tables of numbers, the running header) stay exactly as printed.
The Korean of each box starts at the original type size and shrinks (to 72 % at most) until it fits the box.
A "lines" box inside a ruled table cell is set in the whole cell (between its rules, clear of the other printed lines in
it), with its first baseline on the original's and the original line pitch, shrinking (to 70 % at most) until its ink
stays clear of the rules; Korean lines with inline math keep the original pitch too (the math does not open the lines)."""
import json, re, sys
import pymupdf


def blocks(page):
    out = []
    for i, b in enumerate(page.get_text('dict')['blocks']):
        if b.get('type') != 0:
            continue
        lines, lb, lbold, lbase, lsize = [], [], [], [], []
        size = nb = nc = 0
        color = None
        for l in b['lines']:
            t = ''.join(s['text'] for s in l['spans'])
            if t.strip():
                lines.append(t)
                lb.append([round(v, 1) for v in l['bbox']])
                lbold.append(all('Bold' in s['font'] or 'bx' in s['font'].lower() for s in l['spans'] if s['text'].strip()))
                main = max((s for s in l['spans'] if s['text'].strip()), key=lambda s: len(s['text'].strip()))   # the line's text, not a sub/superscript
                lbase.append(round(main['origin'][1], 2))
                lsize.append(round(main['size'], 2))
                size = max(size, max(s['size'] for s in l['spans']))
                for s in l['spans']:
                    k = len(s['text'].strip())
                    if k and color is None:
                        color = s.get('color', 0)
                    nc += k
                    nb += k if ('Bold' in s['font'] or 'bx' in s['font'].lower()) else 0
        if lines:
            out.append({'id': f'b{i}', 'bbox': [round(v, 1) for v in b['bbox']], 'size': round(size, 1),
                        'bold': nb > 0.6 * nc, 'text': '\n'.join(lines), 'lines': lb, 'lbold': lbold, 'lbase': lbase,
                        'lsize': lsize, 'color': color or 0})
    return out


def dump(orig, out):
    d = pymupdf.open(orig)
    json.dump({str(n + 1): blocks(p) for n, p in enumerate(d)}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def rules(page):
    """The straight rules of the page: level ones as (y, x0, x1), upright ones as (x, y0, y1)."""
    hr, vr = [], []
    for q in page.get_drawings():
        for it in q['items']:
            if it[0] == 'l':
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 0.5 and abs(a.x - b.x) > 8:
                    hr.append(((a.y + b.y) / 2, min(a.x, b.x), max(a.x, b.x)))
                elif abs(a.x - b.x) < 0.5 and abs(a.y - b.y) > 4:
                    vr.append(((a.x + b.x) / 2, min(a.y, b.y), max(a.y, b.y)))
            elif it[0] == 're':
                r = it[1]
                if r.height < 2.5 and r.width > 8:
                    hr.append(((r.y0 + r.y1) / 2, r.x0, r.x1))
                elif r.width < 2.5 and r.height > 4:
                    vr.append(((r.x0 + r.x1) / 2, r.y0, r.y1))
                elif not q.get('fill') and r.width > 8 and r.height > 4:      # an outlined box
                    hr += [(r.y0, r.x0, r.x1), (r.y1, r.x0, r.x1)]
                    vr += [(r.x0, r.y0, r.y1), (r.x1, r.y0, r.y1)]
    return hr, vr


def cell(L, base, size, opt, hr, vr, others):
    """The box for Korean set over lines L of a ruled table cell: (x0, y0, x1, y1) between the cell's rules and clear of
    the other printed lines in it (others: (bbox, baseline, size)), or None when L is not inside a ruled cell."""
    b0, b1 = base[0], base[-1]
    tx0, tx1 = min(l[0] for l in L), min(max(l[2] for l in L), opt.get('x1', 1e9))
    ym, xm = (b0 + b1) / 2 - 0.3 * size, (tx0 + tx1) / 2
    lv = [x for x, ya, yb in vr if x <= tx0 + 1 and ya - 1 <= ym <= yb + 1]
    rv = [x for x, ya, yb in vr if x >= tx1 - 1 and ya - 1 <= ym <= yb + 1]
    up = [y for y, xa, xb in hr if y < b0 - 0.5 * size and xa - 1 <= xm <= xb + 1]
    dn = [y for y, xa, xb in hr if y > b1 + 0.1 * size and xa - 1 <= xm <= xb + 1]
    if not (lv and rv and up and dn):
        return None
    left, right, top, bot = max(lv), min(rv), max(up), min(dn)
    if bot - top > 400 or right - left < 10:
        return None
    if opt.get('align') in ('center', 'right'):
        x0, x1 = left + 1.5, right - 1.5
    else:                                   # the original's inset from the left rule, on both sides
        x0, x1 = tx0, right - max(tx0 - left, 1.5)
    x0, x1 = max(opt.get('x0', x0), left + 1), min(opt.get('x1', x1), right - 1)
    for (ox0, oy0, ox1, oy1), ob, osz in others:        # printed text beside the lines in the same row: keep off it
        if ob - 0.7 * osz < b1 + 0.2 * size and ob + 0.2 * osz > b0 - 0.7 * size and top < ob < bot:
            if ox0 >= tx1 - 1:
                x1 = min(x1, ox0 - 3)
            elif ox1 <= tx0 + 1:
                x0 = max(x0, ox1 + 3)
    for (ox0, oy0, ox1, oy1), ob, osz in others:        # printed text above or below in the same cell
        if ox1 <= x0 or ox0 >= x1 or not top < ob < bot:     # (a baseline past the rule is the next row's)
            continue
        if ob < b0 - 0.6 * size:              # (a sub/superscript or fraction part of the lines' own rows is no obstacle)
            top = max(top, ob + 0.25 * osz)
        elif ob > b1 + 0.6 * size:
            bot = min(bot, ob - 0.8 * osz)
    return x0, top + 0.2, x1, bot - 0.2


FIT = """<script>addEventListener('load',()=>{for(const e of document.querySelectorAll('.kb:not(.cell)')){let s=parseFloat(e.dataset.s),m=s*0.72;
e.style.fontSize=s+'pt';while((e.scrollHeight>e.clientHeight+s*0.5||e.scrollWidth>e.clientWidth+0.5)&&s>m){s-=0.2;e.style.fontSize=s+'pt';}}
const PT=4/3,c=0.6*PT;  // a table cell: first baseline on the original's; ink clear of the rules, else a smaller size
for(const e of document.querySelectorAll('.kb.cell')){const s0=+e.dataset.s,p0=+e.dataset.p,want=+e.dataset.bl*PT,H=e.clientHeight,
W=e.clientWidth,inr=e.firstElementChild,mk=inr.querySelectorAll(':scope>.bl');for(let s=s0;;s=Math.max(s0*0.7,s-0.1)){
e.style.fontSize=s+'pt';inr.style.lineHeight=(p0*s/s0)+'pt';inr.style.top='0px';const et=e.getBoundingClientRect().top,
b0=mk[0].getBoundingClientRect().bottom-et,b1=mk[mk.length-1].getBoundingClientRect().bottom-et;let t=b0-0.81*s*PT,b=b1+0.22*s*PT;
for(const k of inr.querySelectorAll('.katex-html>.base')){const r=k.getBoundingClientRect();t=Math.min(t,r.top-et);b=Math.max(b,r.bottom-et);}
let sh=Math.min(Math.max(want-b0,c-t),H-c-b);const fits=t+sh>=c-0.05&&b+sh<=H-c+0.05&&inr.scrollWidth<=W+0.5;
if(fits||s<=s0*0.7+1e-6){if(!fits){sh=c-t;e.dataset.overflow='1';}inr.style.top=sh+'px';break;}}}});</script>"""


def html(orig, ko, out):
    d = pymupdf.open(orig)
    tr = json.load(open(ko, encoding='utf-8'))
    W, H = d[0].rect.width, d[0].rect.height
    parts = [f'<!doctype html><html><head><meta name="page" content="{W:g},{H:g}"><style>'
             '.a{position:absolute}'
             '.kb{position:absolute;background:#fff;overflow:hidden;font-family:CM,KB,serif;line-height:1.22;text-align:justify;'
             'word-break:normal;line-break:strict;overflow-wrap:anywhere}'   # Hangul may break between syllables, so justified lines keep even spaces
             '.kb .w{white-space:nowrap}'
             '.kb .katex{line-height:0}'          # inline math must not open the line pitch (its struts still count)
             '.kb.cell{background:none;overflow:visible}.kb.cell .in{position:relative}.kb .bl{display:inline-block;width:0;height:0}'
             '.kb.b{font-weight:bold}.kb.c{text-align:center}.kb.r{text-align:right}'
             '</style></head><body>']
    red = {}
    for n, p in enumerate(d):
        pn = str(n + 1)
        B = {b['id']: b for b in blocks(p)}
        hr, vr = rules(p)
        erased = set()                          # lines only painted out (an entry with no text) do not hold a cell's Korean back
        for bid, val in tr.get(pn, {}).items():
            eb = B.get(bid.split('.')[0])
            if eb and not isinstance(val, str) and not val[0].strip() and 'lines' in val[1]:
                erased.update(tuple(eb['lines'][i]) for i in (range(len(eb['lines'])) if val[1]['lines'] == 'all' else val[1]['lines']))
        printed = [(tuple(l), bl, sz) for b in B.values() for l, bl, sz in zip(b['lines'], b['lbase'], b['lsize']) if tuple(l) not in erased]
        parts.append(f'<div class="page"><div class="a" style="left:0;top:0"><span class="fig" data-srcpage="{n + 1}" '
                     f'data-clip="0,0,{p.rect.width:g},{p.rect.height:g}"></span></div>')
        for bid, val in tr.get(pn, {}).items():
            text, opt = (val, {}) if isinstance(val, str) else (val[0], val[1])
            text = re.sub(r'\$[^$]*\$', lambda m: m.group(0).replace('<', '\\lt ').replace('>', '\\gt '), text)   # no stray tags
            text = re.sub(r'[^\s<>$]*(?:\$[^$]*\$[^\s<>$(]*)+', lambda m: f'<span class="w">{m.group(0)}</span>', text)   # math and its word together
            b = B.get(bid.split('.')[0])        # "b19.2": a second box taken from the same block
            if ':' in bid.split('.')[0]:        # "b13:b20": one box over a run of one-line blocks
                lo, hi = (int(v[1:]) for v in bid.split('.')[0].split(':'))
                run = [B[f'b{i}'] for i in range(lo, hi + 1) if f'b{i}' in B]
                b = {'bbox': [min(r['bbox'][0] for r in run), min(r['bbox'][1] for r in run), max(r['bbox'][2] for r in run),
                              max(r['bbox'][3] for r in run)], 'size': run[0]['size'], 'bold': False,
                     'lines': [l for r in run for l in r['lines']], 'lbold': [x for r in run for x in r.get('lbold', [])], 'color': run[0].get('color', 0),
                     'lbase': [x for r in run for x in r['lbase']], 'lsize': [x for r in run for x in r['lsize']]}
            if not b and not opt:
                sys.exit(f'page {pn}: no block {bid}')
            x0, y0, x1, y1 = b['bbox'] if b else (0, 0, 0, 0)
            if 'lines' in opt:                      # only some lines of the block (a table row next to its points)
                idx = range(len(b['lines'])) if opt['lines'] == 'all' else opt['lines']
                L, LB = [b['lines'][i] for i in idx], [b['lbase'][i] for i in idx]
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
                lr = [pymupdf.Rect(max(l[0], x0) - 0.5, l[1] - 2, min(l[2], x1) + 0.5, l[3] + 1.2) for l in L]
                red.setdefault(n, []).extend(lr)
                gone = pymupdf.Rect()
                if any(k in opt for k in ('y0', 'y1')):   # a cell stretched past its lines: paint that out too
                    gone = pymupdf.Rect(x0, y0, x1, y1)
                    lr.append(gone)
                    red[n].append(gone)
                others = [o for o in printed if o[0] not in map(tuple, L) and not (gone + (-1.5, -2.5, 1.5, 1.5)).contains(pymupdf.Rect(o[0]))]
                box = cell(L, LB, size, opt, hr, vr, others)
                if box and text.strip():    # set in the whole ruled cell, first baseline where the original's was
                    cx0, cy0, cx1, cy1 = box
                    gone.y0 = min(gone.y0, L[0][1] - 2) if not gone.is_empty else gone.y0
                    for r in lr:        # paint inside the cell only: a radical or bar of the next row may reach up to the rule
                        r.y0, r.y1, r.x1 = max(r.y0, cy0 - 0.4), min(r.y1, cy1 + 0.4), r.x1 + 1.5    # (and an italic's overhang)
                    parts.append(f'<div class="{cls} cell" data-s="{size}" data-p="{pitch:.2f}" data-bl="{LB[0] - cy0:.2f}" '
                                 f'style="{ink}left:{cx0:.1f}pt;top:{cy0:.1f}pt;width:{cx1 - cx0:.1f}pt;height:{cy1 - cy0:.1f}pt">'
                                 f'<div class="in"><span class="bl"></span>{text}<span class="bl"></span></div></div>')
                    continue
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
