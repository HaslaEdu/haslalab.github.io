"""Bring back inside its table what a Korean solution set (as HTML, printed by Chromium) let run over a column rule.

    python3 -I tools/ko/fit_fix.py SPEC.json SRC_DIR OUT_DIR

SPEC: {"<file>.pdf": [op, …]}, ops applied in order, pages 1-based, coordinates in PDF points from the top left:

  {"page": 3, "rect": [x0, y0, x1, y1], "right": X, "foreign": F}
      the content of rect (an equation, a data table: every text block and painted path whose centre lies in rect) is
      drawn again scaled down uniformly so that its right edge comes to X, its left edge and the middle of rect's
      height staying where they were.  Text blocks beginning at or right of F (the points written in the next column,
      which the content ran over) and the table rules running out of rect are not part of it: they stay as they were.
      The objects are moved by editing the page's content stream (tools/ko/content_blocks.py), so nothing next to
      rect is cut.  "foreign_paths": true counts glyphs drawn as outlines (Cambria Math) starting right of F as foreign
      too; "keep": [[x0, y0, x1, y1], …] leaves out the text and glyphs (not the rules) centred in those rectangles.

  {"page": "all", "columns": [[x0, x1], …], "match": REGEX, "scale": s}
      every text block whose text matches REGEX and lies in one of the columns (its centre between x0 and x1) is set
      at s times its size, centred in its column on its own baseline (the narrow «Marks» columns of IPhO 2017 T2,
      whose numbers ran over the rules between them).

Nothing else on the page changes; the result is checked by tools/ko/fit_check.py.
"""
import json, os, re, sys
import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from content_blocks import Blocks


def is_rule(o, R):
    """a table rule: a thin path reaching more than 2 pt out of the region, or lying along its edge"""
    r = o['rect']
    if o['kind'] != 'path' or not (r.width < 1.6 or r.height < 1.6) or max(r.width, r.height) < 6:
        return False                     # not thin, or a dot
    out = not (r.x0 > R.x0 - 2 and r.x1 < R.x1 + 2 and r.y0 > R.y0 - 2 and r.y1 < R.y1 + 2)
    edge = (r.height < 1.6 and min(abs(r.y0 - R.y0), abs(r.y1 - R.y1)) < 3) or (r.width < 1.6 and min(abs(r.x0 - R.x0), abs(r.x1 - R.x1)) < 3)
    return out or edge


def fit(doc, pno, R, right, foreign, foreign_paths=False, keep=()):
    page = doc[pno]
    B = Blocks(doc, page)
    # what is redrawn: every text block and painted path whose centre lies in R, but the rules and the foreign text
    inside = lambda o: R.contains((o['rect'].tl + o['rect'].br) / 2)
    def far(o):
        r = o['rect']
        thin = o['kind'] == 'path' and (r.width < 1.6 or r.height < 1.6) and max(r.width, r.height) >= 6
        if not thin and any(pymupdf.Rect(k).contains((r.tl + r.br) / 2) for k in keep):
            return True
        if foreign is None or r.x0 < foreign - 0.5:
            return False
        # text, and (foreign_paths) glyphs drawn as outlines — a thin path there is a rule of the content itself
        return o['kind'] == 'text' or (foreign_paths and not thin)
    members = B.select(lambda o: inside(o) and not is_rule(o, R) and not far(o), kinds=('text', 'path'))
    full = pymupdf.Rect(R)
    for i in members:
        full |= B.objs[i]['rect']
    # scaled about the left edge and the middle of R's height (their extent may pass R a little), in place in the
    # page's own stream: no copy of the page, no new resources
    s = (right - full.x0) / full.width
    cy = (R.y0 + R.y1) / 2
    T = pymupdf.Matrix(1, 0, 0, 1, -full.x0, -cy) * pymupdf.Matrix(s, 0, 0, s, 0, 0) * pymupdf.Matrix(1, 0, 0, 1, full.x0, cy)
    B.save_stream(B.transformed({i: T for i in members}))
    return s, len(members)


def columns(doc, pno, cols, match, scale):
    page = doc[pno]
    B = Blocks(doc, page)
    rx = re.compile(match)
    changes = {}
    for bl in B.blocks:
        r, t = bl['rect'], bl['text'].strip()
        if r.is_empty or not rx.fullmatch(t):
            continue
        cx = (r.x0 + r.x1) / 2
        for x0, x1 in cols:
            if x0 < cx < x1:
                by = bl['base']
                nx0 = (x0 + x1) / 2 - r.width * scale / 2
                # page-space map: scale about (r.x0, baseline), then move the left edge to nx0
                changes[bl['i']] = pymupdf.Matrix(1, 0, 0, 1, -r.x0, -by) * pymupdf.Matrix(scale, 0, 0, scale, 0, 0) * pymupdf.Matrix(1, 0, 0, 1, nx0, by)
                break
    if changes:
        B.save_stream(B.transformed(changes))
    return len(changes)


def run(spec, src, out):
    for name, todo in spec.items():
        doc = pymupdf.open(os.path.join(src, name))
        for op in todo:
            pages = range(len(doc)) if op['page'] == 'all' else [op['page'] - 1]
            for pno in pages:
                if 'rect' in op:
                    s, n = fit(doc, pno, pymupdf.Rect(op['rect']), op['right'], op.get('foreign'), op.get('foreign_paths', False), op.get('keep', ()))
                    print(f'{name} p{pno + 1} {op["rect"]}: {n} objects redrawn at {s:.3f}')
                else:
                    n = columns(doc, pno, op['columns'], op['match'], op['scale'])
                    print(f'{name} p{pno + 1}: {n} column blocks set at {op["scale"]}')
        doc.save(os.path.join(out, name), garbage=3, deflate=True)


if __name__ == '__main__':
    run(json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3])
