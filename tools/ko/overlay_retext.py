"""Small, explicit edits of the Korean lines of an overlay paper (form «fullpage», fonts kserif/kserifb), driven by a
JSON list of operations. Text is set with the fonts already embedded in the file (tools/ko/kfont.py): a character
whose glyph is not in the subset is refused, nothing is substituted.

    python3 tools/ko/overlay_retext.py <ko.pdf> <out.pdf> <ops.json>

Operations (pages 1-based; a line is found by its text: «find» must equal it or start it, «nth» picks among repeats):
  {"page": 3, "find": "Tsys 값 2.0 이득이 맞음 2.0", "set": "Tsys 값"}           replace the line's text
  {"page": 3, "find": "…", "delete": true}                                         remove the line
  {"page": 3, "find": "…", "x": 163.4, "base": 330.5}                              move it (page coordinates)
  {"page": 3, "find": "…", "size": 9.5}                                            change its size
  {"page": 3, "add": "이득이 맞음", "x": 120, "base": 340, "size": 10,
   "font": "kserif", "box": [x0, y0, x1, y1], "color": [1, 0, 0]}                  new line at the end of the overlay,
                                                                                    after an optional white box
  {"page": 3, "box": [x0, y0, x1, y1], "fill": [1, 1, 1]}                          a box at the end (covers what is under)
  {"page": 3, "unbox": [x0, y0, x1, y1]}                                          remove the overlay's white boxes
                                                                                    lying inside that rect
  {"page": 3, "rich": [["(G01.5b) v"], {"sup": "obs", "sub": "지구"}, ["(ℓ)와 …"]], "x": 114, "base": 583,
   "size": 10}                                                                      a line with super/subscripts
                                                                                    (stacked at 0.65 × size)
  {"page": 3, "reflow": ["first line…", "second line…"], "text": "…" (optional, else the lines joined),
   "x": 115, "indent": 163.4, "right": 538.6, "base": 177.2, "pitch": 13.5, "size": 10}
      remove those lines and set the text again, wrapped at spaces between x/indent and right, one line per pitch
  {"page": 3, "find": "…", "boxes_from_here": true} with "set"/"delete"            also drop the white boxes painted
                                                                                    right before the line
  {"page": 3, "replace_en": [x0, y0, x1, y1], "text": "이득이 맞음", "size": 10}    hide the original (English) text
      spans inside the rect (white box, or "fill") and set the Korean at the first span's start and baseline;
      "text" may hold "\n" for a second line (set on the English second line's baseline, or 1.2 × size lower);
      "align": "center" centres each line in "cell": [x0, x1]
Prints what it did; stops on the first operation it cannot do."""
import json
import re
import sys

import pymupdf

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from kfont import KFont, font_xref  # noqa: E402
from overlay_redraw import overlay_xref  # noqa: E402

TEXT = re.compile(rb'q\nBT\n1 0 0 1 ([-\d.]+) ([-\d.]+) Tm\n/(kserif\w*) ([\d.]+) Tf ([^\n]*?)\[<([0-9a-f]*)>\]TJ\nET\nQ')
RECT = re.compile(rb'q\n([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) re\nh\n[\d. ]+ rg f\nQ')


def run(src, dst, ops):
    doc = pymupdf.open(src)
    fonts = {}
    for op in ops:
        page = doc[op['page'] - 1]
        H = page.rect.height
        ov = overlay_xref(doc, page)
        s = doc.xref_stream(ov)

        def kf(name):
            if name not in fonts:
                fonts[name] = KFont(doc, font_xref(doc, page, name))
            return fonts[name]

        def enc(name, text):
            hx, miss = kf(name).encode(text)
            if miss:
                raise SystemExit('page %d: no glyph for %r in %s (text %r)' % (op['page'], ''.join(miss), name, text))
            return hx

        if 'find' in op:
            hits = []
            for m in TEXT.finditer(s):
                f = kf(m.group(3).decode())
                c2u = {v: k for k, v in f.u2c.items()} if not hasattr(f, 'c2u') else f.c2u
                f.c2u = c2u
                t = ''.join(c2u.get(int(m.group(6)[i:i + 4], 16), '?') for i in range(0, len(m.group(6)), 4))
                if t == op['find'] or t.startswith(op['find']):
                    hits.append(m)
            if not hits or len(hits) <= op.get('nth', 0):
                raise SystemExit('page %d: line not found: %r' % (op['page'], op['find']))
            m = hits[op.get('nth', 0)]
            a, b = m.span()
            if op.get('boxes_from_here'):
                # the white boxes painted right before the line, as long as they lie on its height
                ly = float(m.group(2))
                lz = float(m.group(4))
                cut = []
                pos = a
                while True:
                    prev = s[:pos].rstrip(b'\n \n')
                    r = [q for q in RECT.finditer(prev)]
                    if not (r and r[-1].end() == len(prev)):
                        break
                    q = r[-1]
                    by, bh = float(q.group(2)), float(q.group(4))
                    if by < ly + 0.8 * lz and by + bh > ly - 0.4 * lz:
                        cut.append(q.span())
                    pos = q.start()
                for c0, c1 in cut:                                   # later ones first: offsets stay valid
                    s = s[:c0] + s[c1:]
                    a -= c1 - c0
                    b -= c1 - c0
            if op.get('delete'):
                new = b''
            else:
                x = op.get('x')
                base = op.get('base')
                xs = b'%.3f' % x if x is not None else m.group(1)
                ys = b'%.3f' % (H - base) if base is not None else m.group(2)
                size = b'%s' % str(op['size']).encode() if 'size' in op else m.group(4)
                font = op.get('font', m.group(3).decode()).encode()
                hx = enc(font.decode(), op['set']) if 'set' in op else m.group(6)
                new = b'q\nBT\n1 0 0 1 %s %s Tm\n/%s %s Tf %s[<%s>]TJ\nET\nQ' % (xs, ys, font, size, m.group(5), hx)
                if op.get('boxes_from_here'):
                    new = new
            s = s[:a] + new + s[b:]
            print(op['page'], 'edited' if not op.get('delete') else 'deleted', repr(op['find'][:40]), '->', repr(op.get('set', '')[:40]))
        elif 'unbox' in op:
            area = pymupdf.Rect(op['unbox'])
            n = 0
            for q in reversed(list(RECT.finditer(s))):
                x0, y0, w, h = (float(v) for v in q.groups())
                if area.contains(pymupdf.Rect(x0, H - y0 - h, x0 + w, H - y0)):
                    s = s[:q.start()] + s[q.end():]
                    n += 1
            print(op['page'], 'removed %d boxes' % n)
        elif 'rich' in op:
            font = op.get('font', 'kserif')
            size = op.get('size', 10)
            x = op['x']
            add = b''
            for part in op['rich']:
                if isinstance(part, list):
                    t = part[0]
                    add += b'q\nBT\n1 0 0 1 %.3f %.3f Tm\n/%s %s Tf 0 0 0 RG 0 0 0 rg [<%s>]TJ\nET\nQ\n \n' % (
                        x, H - op['base'], font.encode(), str(size).encode(), enc(font, t))
                    x += kf(font).width(t, size)
                else:
                    zs = round(size * 0.65, 2)
                    w = 0
                    for key, dy in (('sup', -0.42 * size), ('sub', 0.25 * size)):
                        if key in part:
                            add += b'q\nBT\n1 0 0 1 %.3f %.3f Tm\n/%s %s Tf 0 0 0 RG 0 0 0 rg [<%s>]TJ\nET\nQ\n \n' % (
                                x, H - op['base'] - dy, font.encode(), str(zs).encode(), enc(font, part[key]))
                            w = max(w, kf(font).width(part[key], zs))
                    x += w + 0.5
            s = s.rstrip(b'\n') + b'\n \n' + add
            print(op['page'], 'rich line ending at x=%.1f' % x)
        elif 'reflow' in op:
            texts = []
            for want in op['reflow']:
                hit = None
                for m in TEXT.finditer(s):
                    f = kf(m.group(3).decode())
                    if not hasattr(f, 'c2u'):
                        f.c2u = {v: k for k, v in f.u2c.items()}
                    t = ''.join(f.c2u.get(int(m.group(6)[i:i + 4], 16), '?') for i in range(0, len(m.group(6)), 4))
                    if t == want or t.startswith(want):
                        hit = (m, t)
                        break
                if not hit:
                    raise SystemExit('page %d: line not found: %r' % (op['page'], want))
                m, t = hit
                font = m.group(3).decode()
                texts.append(t.strip())
                s = s[:m.start()] + s[m.end():]
            text = op.get('text', ' '.join(texts))
            font = op.get('font', font)
            size = op.get('size', 10)
            words = text.split(' ')
            lines, cur = [], ''
            for w in words:
                lim = op['right'] - (op['x'] if not lines else op.get('indent', op['x']))
                trial = (cur + ' ' + w) if cur else w
                if cur and kf(font).width(trial, size) > lim:
                    lines.append(cur)
                    cur = w
                else:
                    cur = trial
            if cur:
                lines.append(cur)
            add = b''
            if 'box' in op:
                x0, y0, x1, y1 = op['box']
                add += b'q\n%.2f %.2f %.2f %.2f re\nh\n1 1 1 rg f\nQ\n \n' % (x0, H - y1, x1 - x0, y1 - y0)
            for li, line in enumerate(lines):
                x = op['x'] if li == 0 else op.get('indent', op['x'])
                base = op['bases'][li] if 'bases' in op else op['base'] + li * op.get('pitch', 1.2 * size)
                add += b'q\nBT\n1 0 0 1 %.3f %.3f Tm\n/%s %s Tf 0 0 0 RG 0 0 0 rg [<%s>]TJ\nET\nQ\n \n' % (
                    x, H - base, font.encode(), str(size).encode(), enc(font, line))
            s = s.rstrip(b'\n') + b'\n \n' + add
            print(op['page'], 'reflowed into %d lines' % len(lines), repr(text[:40]))
            if op.get('max_lines') and len(lines) > op['max_lines']:
                raise SystemExit('page %d: reflow needs %d lines, only %d fit' % (op['page'], len(lines), op['max_lines']))
        elif 'replace_en' in op:
            area = pymupdf.Rect(op['replace_en'])
            sp = [(pymupdf.Rect(x['bbox']), x['origin'][1], x['size']) for b in page.get_text('dict')['blocks'] if b['type'] == 0 for l in b['lines']
                  for x in l['spans'] if 'Batang' not in x['font'] and x['text'].strip() and area.contains(pymupdf.Rect(x['bbox']).tl + (0.5, 0.5))
                  and area.contains(pymupdf.Rect(x['bbox']).br - (0.5, 0.5))]
            if not sp:
                raise SystemExit('page %d: no English text in %s' % (op['page'], op['replace_en']))
            u = pymupdf.Rect(sp[0][0])
            for r, _, _ in sp:
                u |= r
            box = op.get('boxrect') or [u.x0 - 0.8, u.y0 - 0.3, u.x1 + 0.8, u.y1 + 0.3]
            fill = op.get('fill', [1, 1, 1])
            big = max(z for _, _, z in sp)
            bases = []
            for o in sorted(round(o, 1) for _, o, z in sp if z > 0.8 * big):        # main text, not super/subscripts
                if not bases or o - bases[-1] > 0.8 * big:
                    bases.append(o)
            font = op.get('font', 'kserif')
            size = op.get('size', 10)
            col = op.get('color', [0, 0, 0])
            add = b'q\n%.2f %.2f %.2f %.2f re\nh\n%.3f %.3f %.3f rg f\nQ\n \n' % (box[0], H - box[3], box[2] - box[0], box[3] - box[1], *fill)
            for li, line in enumerate(op['text'].split('\n')):
                base = bases[li] if li < len(bases) else bases[-1] + 1.2 * size * (li - len(bases) + 1)
                if 'base' in op:
                    base = op['base'] + 1.2 * size * li
                x = op.get('x', u.x0)
                if op.get('align') == 'center':
                    c0, c1 = op['cell']
                    x = (c0 + c1) / 2 - kf(font).width(line, size) / 2
                add += b'q\nBT\n1 0 0 1 %.3f %.3f Tm\n/%s %s Tf %.3f %.3f %.3f RG %.3f %.3f %.3f rg [<%s>]TJ\nET\nQ\n \n' % (
                    x, H - base, font.encode(), str(size).encode(), *col, *col, enc(font, line))
            s = s.rstrip(b'\n') + b'\n \n' + add
            print(op['page'], 'replaced English', ' '.join(sorted({str(round(r.x0)) for r, _, _ in sp}))[:30], '->', repr(op['text'][:40]))
        else:
            add = b''
            if 'box' in op:
                x0, y0, x1, y1 = op['box']
                fill = op.get('fill', [1, 1, 1])
                add += b'q\n%.2f %.2f %.2f %.2f re\nh\n%.3f %.3f %.3f rg f\nQ\n \n' % (x0, H - y1, x1 - x0, y1 - y0, *fill)
            if 'add' in op:
                font = op.get('font', 'kserif')
                col = op.get('color', [0, 0, 0])
                hx = enc(font, op['add'])
                add += b'q\nBT\n1 0 0 1 %.3f %.3f Tm\n/%s %s Tf %.3f %.3f %.3f RG %.3f %.3f %.3f rg [<%s>]TJ\nET\nQ\n' % (
                    op['x'], H - op['base'], font.encode(), str(op.get('size', 10)).encode(), *col, *col, hx)
            s = s.rstrip(b'\n') + b'\n \n' + add
            print(op['page'], 'added', repr(op.get('add', 'box')[:40]))
        doc.update_stream(ov, s)
    doc.save(dst, garbage=3, deflate=True)


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], json.load(open(sys.argv[3])))
