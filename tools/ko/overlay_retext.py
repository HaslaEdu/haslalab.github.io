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
  {"page": 3, "find": "…", "boxes_from_here": true} with "set"/"delete"            also drop the white boxes painted
                                                                                    right before the line
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
                while True:
                    prev = s[:a].rstrip(b'\n \n')
                    r = [q for q in RECT.finditer(prev)]
                    if r and r[-1].end() == len(prev):
                        a = r[-1].start()
                    else:
                        break
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
