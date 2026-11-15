"""Emit page divs that stamp whole original pages and lay Korean over chosen English lines.
usage: python -I mkans.py ORIG.pdf MAP.json
MAP: {"pages":[3,4], "map":{"English line":"한국어"}, "boxes":{"3":[[x0,y0,x1,y1,"한국어"],...]}}
A value starting with ^ is centred in the covered box."""
import sys, json, pymupdf
d = pymupdf.open(sys.argv[1]); cfg = json.load(open(sys.argv[2], encoding='utf-8'))
m = cfg.get('map', {}); used = set(); fs = cfg.get('scale', 0.88)
def ov(x0, y0, x1, y1, sz, ko):
    c = ';text-align:center' if ko.startswith('^') else ''
    bold = ko.startswith('^') or sz >= 13.5
    ko = ko.lstrip('^')
    if bold and ko: ko = f'<b>{ko}</b>'
    return (f'<div class="ov" style="left:{x0-1:.1f}pt;top:{y0+1:.1f}pt;min-width:{x1-x0+2:.1f}pt;height:{y1-y0:.1f}pt;'
            f'font-size:{sz*fs:.1f}pt;line-height:{y1-y0-2:.1f}pt{c}">{ko}</div>')
for pn in cfg['pages']:
    p = d[pn-1]; W, H = p.rect.width, p.rect.height
    out = ['<div class="page">', f'<div class="a" style="left:0;top:0"><span class="fig" data-srcpage="{pn}" data-clip="0,0,{W:g},{H:g}"></span></div>']
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ' '.join(''.join(s['text'] for s in l['spans']).split())
            if t in m:
                used.add(t)
                out.append(ov(*l['bbox'], max(s['size'] for s in l['spans']), m[t]))
    for x0, y0, x1, y1, ko, *sz in cfg.get('boxes', {}).get(str(pn), []):
        out.append(ov(x0, y0, x1, y1, sz[0] if sz else 12, ko))
    out.append('</div>')
    print('\n'.join(out))
miss = set(m) - used
if miss: print('UNUSED', miss, file=sys.stderr)
