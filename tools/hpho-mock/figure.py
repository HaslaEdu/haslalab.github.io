"""Cut a figure out of a source PDF page as SVG (all text drawn as outlines, so it looks the same everywhere) or PNG.

  python3 -I tools/hpho-mock/figure.py SRC.pdf PAGE --list
      prints the page's text spans (with boxes, sizes) and the union of its drawings, to choose a crop box
  python3 -I tools/hpho-mock/figure.py SRC.pdf PAGE x0 y0 x1 y1 OUT.svg|OUT.png [--labels LABELS.json]
      crops the box (PDF points, top-left origin). With --labels the listed labels are wiped and redrawn first:
      [{"find": "정수압", "text": "hydrostatic"}                       exact span text, redrawn centred on it
       {"find": "깊이", "text": "depth", "align": "left"}              or left-aligned at its start
       {"box": [x0,y0,x1,y1], "lines": ["empty ring", "width ~d/2"], "size": 7, "align": "left"}]
      A "box" entry wipes every text character inside the box (math too) and writes the lines; write math there
      in plain Unicode (e.g. "~d/2"). Sizes default to the original span's size."""
import sys, json, re, pymupdf
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
REG, BOLD = str(ROOT / 'tools/ko/fonts/NotoSans-Regular.ttf'), str(ROOT / 'tools/ko/fonts/NotoSans-Bold.ttf')
src, pno = sys.argv[1], int(sys.argv[2])
doc = pymupdf.open(src); p = doc[pno - 1]
def spans():
    for b in p.get_text('dict')['blocks']:
        if b['type'] != 0: continue
        for l in b['lines']:
            for s in l['spans']:
                if s['text'].strip(): yield s
if sys.argv[3] == '--list':
    print('page', [round(v) for v in p.rect])
    for s in spans(): print('span', [round(v, 1) for v in s['bbox']], 'size', round(s['size'], 1), repr(s['text']))
    for b in p.get_text('dict')['blocks']:
        if b['type'] == 1: print('image', [round(v) for v in b['bbox']])
    ds = p.get_drawings()
    if ds:
        r = pymupdf.Rect(ds[0]['rect'])
        for d in ds: r |= d['rect']
        print('drawings', len(ds), 'union', [round(v) for v in r])
    sys.exit()
x0, y0, x1, y1 = map(float, sys.argv[3:7]); out = sys.argv[7]
labels = json.load(open(sys.argv[sys.argv.index('--labels') + 1])) if '--labels' in sys.argv else []
writes = []
for lab in labels:
    if 'find' in lab:
        hit = [s for s in spans() if re.sub(r'\s', '', s['text']) == re.sub(r'\s', '', lab['find']) and pymupdf.Rect(s['bbox']).intersects((x0, y0, x1, y1))]
        if not hit: sys.exit(f'label not found in the crop: {lab["find"]!r}')
        for s in hit:
            r = pymupdf.Rect(s['bbox']); p.add_redact_annot(r)
            writes.append((r, [lab['text']], lab.get('size', s['size']), lab.get('align', 'center'), s['color'], bool(s['flags'] & 16)))
    else:
        r = pymupdf.Rect(lab['box']); p.add_redact_annot(r)
        writes.append((r, lab['lines'], lab.get('size', 7), lab.get('align', 'left'), 0, lab.get('bold', False)))
if labels:
    p.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE, text=pymupdf.PDF_REDACT_TEXT_REMOVE)
    for r, lines, size, align, color, bold in writes:
        f = pymupdf.Font(fontfile=BOLD if bold else REG)
        rgb = tuple(((color >> k) & 255) / 255 for k in (16, 8, 0)) if isinstance(color, int) else (0, 0, 0)
        cy = (r.y0 + r.y1) / 2 - (len(lines) - 1) * size * 0.6
        for i, t in enumerate(lines):
            w = f.text_length(t, fontsize=size)
            x = r.x0 if align == 'left' else (r.x1 - w if align == 'right' else (r.x0 + r.x1 - w) / 2)
            p.insert_text((x, cy + size * 0.35 + i * size * 1.2), t, fontsize=size, fontname='F' + ('b' if bold else 'r'), fontfile=BOLD if bold else REG, color=rgb)
clip = pymupdf.Rect(x0, y0, x1, y1)
if out.endswith('.png'):
    p.get_pixmap(clip=clip, dpi=300).save(out)
else:
    svg = p.get_svg_image(text_as_path=True)
    svg = re.sub(r'viewBox="[^"]*"', f'viewBox="{x0} {y0} {x1-x0} {y1-y0}"', svg, count=1)
    svg = re.sub(r'width="[^"]*" height="[^"]*"', f'width="{x1-x0}pt" height="{y1-y0}pt"', svg, count=1)
    open(out, 'w').write(svg)
print(out)
