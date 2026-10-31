"""Set the header of a Korean paper in the IPhO/APhO style exactly where the official English paper has it.

    python3 tools/ko/ipho_header.py <ko.pdf> <en.pdf> <out.pdf>

Some Korean papers were printed from HTML with their own header: «Experiment»/«Theory», the page code and the language
a few points off the official places, and a hairline under them (APhO 2023: the code 10 pt higher, a 0.7 pt rule).
On every page the header band (above the rule, right of the logo and the kind label) is cleared — the logo image stays
— and set again from the English first page: the kind label in Noto Sans Bold at its origin, the page's own code
(«Q1-2», read from the Korean page) right-aligned where the English code ends, «Korean (Korea (Republic of))» where
«English (Official)» ends, and the rule at the English height and weight."""
import os
import re
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(HERE, 'fonts', n)
REG, BOLD = pymupdf.Font(fontfile=F('NotoSans-Regular.ttf')), pymupdf.Font(fontfile=F('NotoSans-Bold.ttf'))
LABEL = 'Korean (Korea (Republic of))'
CODE = re.compile(r'^[A-Z]{1,2}\d*[-‑]\d+$')


def spans(page):
    return [s for b in page.get_text('dict')['blocks'] for l in b.get('lines', []) for s in l['spans'] if s['text'].strip()]


def reference(en):
    p = en[0]
    rule = next(d for d in p.get_drawings() if d['rect'].y0 < 200 and d['rect'].width > 300)
    ry = (rule['rect'].y0 + rule['rect'].y1) / 2
    sp = [s for s in spans(p) if s['bbox'][1] < ry]
    code = next(s for s in sp if s['size'] > 40 and CODE.match(s['text'].strip()))
    lab = next(s for s in sp if 'Official' in s['text'] or 'English' in s['text'])
    kind = next((s for s in sp if s['size'] > 12 and s['size'] < 20 and s['bbox'][0] < 200), None)
    return {'ry': ry, 'rx': (rule['rect'].x0, rule['rect'].x1), 'rw': rule.get('width') or rule['rect'].height,
            'code': (code['bbox'][2], code['origin'][1], code['size']), 'lab': (lab['bbox'][2], lab['origin'][1]),
            'kind': (kind['text'].strip(), kind['origin'], kind['size']) if kind else None}


def fix(src, orig, dst):
    ref, doc = reference(pymupdf.open(orig)), pymupdf.open(src)
    for page in doc:
        codes = [''.join(chr(c[0]) for c in t['chars']).strip() for t in page.get_texttrace()
                 if t['size'] > 40 and t['bbox'][1] < ref['ry']]
        code = next((c for c in codes if CODE.match(c)), None)
        if not code:
            continue
        # clear the band right of the logo (x > 150) above the rule, the kind label, and the old rule
        page.add_redact_annot(pymupdf.Rect(150, 20, page.rect.width - 20, ref['ry'] + 2.2))
        page.add_redact_annot(pymupdf.Rect(40, 20, 150, 81.5))
        page.add_redact_annot(pymupdf.Rect(40, ref['ry'] - 1, 150, ref['ry'] + 2.2))
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED)
        page.insert_font(fontname='nr', fontfile=F('NotoSans-Regular.ttf'))
        page.insert_font(fontname='nb', fontfile=F('NotoSans-Bold.ttf'))
        if ref['kind']:
            text, (x, y), size = ref['kind']
            page.insert_text((x, y), text, fontname='nb', fontsize=size)
        x1, y, size = ref['code']
        code = code.replace('‑', '-')
        page.insert_text((x1 - BOLD.text_length(code, fontsize=size), y), code, fontname='nb', fontsize=size)
        x1, y = ref['lab']
        page.insert_text((x1 - REG.text_length(LABEL, fontsize=10), y), LABEL, fontname='nr', fontsize=10)
        page.draw_line((ref['rx'][0], ref['ry']), (ref['rx'][1], ref['ry']), color=(0, 0, 0), width=ref['rw'])
    doc.subset_fonts()
    doc.save(dst, garbage=4, deflate=True)


if __name__ == '__main__':
    fix(*sys.argv[1:4])
