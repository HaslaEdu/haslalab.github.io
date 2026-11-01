"""Text blocks (BT … ET) of a page typeset by Chromium (the Korean solutions laid out as HTML and printed), with where
each one lands on the page — so that a piece of the page can be redrawn without the text of a neighbouring column that
overlaps it, or a column's text can be set smaller where it overruns its rules.

    from content_blocks import Blocks
    b = Blocks(doc, page)            # parses the page's largest content stream (the body)
    b.objs                           # text blocks and painted paths: {i, kind, start, end, rect (page space)}
    b.blocks                         # the text blocks only (rect from the page's own text trace, text, baseline)
    b.without(sel) / b.only(sel)     # the body stream without / with only the objects in sel
    b.transformed({i: matrix})       # text blocks drawn under an extra page-space transformation

Only q/Q/cm, path construction and the text-positioning operators are interpreted; everything else is kept as written.
"""
import re
import pymupdf

NUM = re.compile(rb'[-+]?(?:\d+\.?\d*|\.\d+)')
DELIM = b'()<>[]{}/%'
WS = b' \t\r\n\x0c\x00'
PAINT = {b'f', b'F', b'f*', b'S', b's', b'B', b'B*', b'b', b'b*'}
CONSTRUCT = {b'm', b'l', b'c', b'v', b'y', b're', b'h'}


def tokens(s):
    """(kind, value, start, end): kind num | name | str | hex | arr | dict | op"""
    i, n = 0, len(s)
    while i < n:
        c = s[i:i + 1]
        if c in WS:
            i += 1
            continue
        if c == b'%':
            j = s.find(b'\n', i)
            i = n if j < 0 else j + 1
            continue
        st = i
        if c == b'(':
            depth, i = 0, i
            while i < n:
                ch = s[i:i + 1]
                if ch == b'\\':
                    i += 2
                    continue
                if ch == b'(':
                    depth += 1
                elif ch == b')':
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
            yield ('str', s[st:i], st, i)
        elif s[i:i + 2] == b'<<':
            depth = 0
            while i < n:
                if s[i:i + 2] == b'<<':
                    depth += 1; i += 2
                elif s[i:i + 2] == b'>>':
                    depth -= 1; i += 2
                    if depth == 0:
                        break
                elif s[i:i + 1] == b'(':
                    for t in tokens(s[i:]):
                        i += t[3]; break
                else:
                    i += 1
            yield ('dict', s[st:i], st, i)
        elif c == b'<':
            j = s.index(b'>', i)
            i = j + 1
            yield ('hex', s[st:i], st, i)
        elif c == b'[':
            depth = 0
            while i < n:
                ch = s[i:i + 1]
                if ch == b'[':
                    depth += 1
                elif ch == b']':
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                elif ch == b'(':
                    for t in tokens(s[i:]):
                        i += t[3] - 1; break
                i += 1
            yield ('arr', s[st:i], st, i)
        elif c == b'/':
            i += 1
            while i < n and s[i:i + 1] not in WS and s[i:i + 1] not in DELIM:
                i += 1
            yield ('name', s[st:i], st, i)
        else:
            while i < n and s[i:i + 1] not in WS and s[i:i + 1] not in DELIM:
                i += 1
            w = s[st:i]
            yield ('num' if NUM.fullmatch(w) else 'op', w, st, i)


def ops(s):
    """(operator, operands, start, end) — start at the first operand"""
    args, st = [], None
    for kind, v, a, b in tokens(s):
        if kind == 'op':
            yield v, args, (a if st is None else st), b
            args, st = [], None
        else:
            if st is None:
                st = a
            args.append((kind, v))


def M(a):
    return pymupdf.Matrix(*[float(x[1]) for x in a])


class Blocks:
    def __init__(self, doc, page):
        self.doc, self.page = doc, page
        xs = page.get_contents()
        self.xref = max(xs, key=lambda x: len(doc.xref_stream(x)))
        self.s = doc.xref_stream(self.xref)
        self.base = page.transformation_matrix          # PDF space -> page space
        self._parse()
        self._place()

    def _parse(self):
        """text blocks (BT … ET) and painted paths (construction ops … painting op), each with where it starts and ends
        in the stream; a clipping path («W n») is neither and always stays"""
        ctm, stack = pymupdf.Matrix(1, 0, 0, 1, 0, 0), []
        self.blocks, self.objs, self.dos = [], [], []
        cur = path = None
        for op, args, a, b in ops(self.s):
            if cur is None and op in CONSTRUCT:
                if path is None:
                    path = {'kind': 'path', 'start': a, 'pts': [], 'ctm': ctm}
                v = [float(x[1]) for x in args]
                if op == b're':
                    x, y, w, h = v
                    path['pts'] += [pymupdf.Point(x, y) * ctm * self.base, pymupdf.Point(x + w, y + h) * ctm * self.base]
                else:
                    path['pts'] += [pymupdf.Point(v[k], v[k + 1]) * ctm * self.base for k in range(0, len(v) - 1, 2)]
                continue
            if path is not None and op in (b'W', b'W*'):
                path['clip'] = True
                continue
            if path is not None and (op in PAINT or op == b'n'):
                if op != b'n' and not path.get('clip'):
                    r = pymupdf.Rect(path['pts'][0], path['pts'][0])
                    for q in path['pts'][1:]:
                        r |= q
                    self.objs.append({'i': len(self.objs), 'kind': 'path', 'start': path['start'], 'end': b, 'rect': r, 'ctm': path['ctm']})
                path = None
                continue
            if op == b'q':
                stack.append(ctm)
            elif op == b'Q':
                ctm = stack.pop() if stack else ctm
            elif op == b'cm':
                ctm = M(args) * ctm
            elif op == b'Do' and cur is None:
                self.dos.append((a, b))
            elif op == b'BT':
                tlm = pymupdf.Matrix(1, 0, 0, 1, 0, 0)
                cur = {'i': len(self.objs), 'kind': 'text', 'start': a, 'runs': [], 'ctm': ctm}
                self.objs.append(cur); self.blocks.append(cur)
            elif op == b'Tm' and cur is not None:
                tlm = M(args)
            elif op in (b'Td', b'TD') and cur is not None:
                tlm = pymupdf.Matrix(1, 0, 0, 1, float(args[0][1]), float(args[1][1])) * tlm
            elif op in (b'Tj', b'TJ', b"'", b'"') and cur is not None:
                cur['runs'].append(pymupdf.Point(0, 0) * tlm * ctm * self.base)
            elif op == b'ET' and cur is not None:
                cur['end'] = b
                cur = None

    def _place(self):
        spans = [(pymupdf.Point(sp['chars'][0][2]), pymupdf.Rect(sp['bbox']), sp) for sp in self.page.get_texttrace() if sp['chars']]
        for bl in self.blocks:
            hit = [(rect, sp) for p in bl['runs'] for o, rect, sp in spans if abs(o.x - p.x) < 0.6 and abs(o.y - p.y) < 0.6]
            r = pymupdf.Rect()
            for rect, sp in hit:
                r |= rect
            bl['rect'] = r
            bl['text'] = ''.join(chr(c[0]) for rect, sp in hit for c in sp['chars'])
            bl['base'] = bl['runs'][0].y if bl['runs'] else None
            bl['size'] = max((sp['size'] for rect, sp in hit), default=0)

    def select(self, pred, kinds=('text',)):
        return {o['i'] for o in self.objs if o['kind'] in kinds and not o['rect'].is_empty and pred(o)}

    def _cut(self, spans):
        out, last = [], 0
        for a, b in sorted(spans):
            if a < last:
                continue
            out.append(self.s[last:a]); last = b
        out.append(self.s[last:])
        return b''.join(out)

    def without(self, sel, images=True):
        """the body without the selected objects (and, images=False, without its images — the watermark)"""
        return self._cut([(self.objs[i]['start'], self.objs[i]['end']) for i in sel] + ([] if images else self.dos))

    def only(self, sel):
        """the body with only the selected objects (text blocks, painted paths): no other text, paths or images"""
        return self._cut([(o['start'], o['end']) for o in self.objs if o['i'] not in sel] + self.dos)

    def transformed(self, changes):
        """the body with each object i in changes (a text block or a painted path) drawn under the extra page-space
        matrix changes[i], wrapped in its own q … Q"""
        out, last = [], 0
        for o in sorted((self.objs[i] for i in changes), key=lambda o: o['start']):
            # page-space T  ->  user space at the object: U = C·T·C⁻¹ with C = ctm·base
            C = o['ctm'] * self.base
            U = C * changes[o['i']] * ~C
            out.append(self.s[last:o['start']])
            out.append(b'q %.6f %.6f %.6f %.6f %.5f %.5f cm\n' % tuple(U))
            out.append(self.s[o['start']:o['end']])
            out.append(b'\nQ\n')
            last = o['end']
        out.append(self.s[last:])
        return b''.join(out)

    def save_stream(self, data):
        self.doc.update_stream(self.xref, data)
