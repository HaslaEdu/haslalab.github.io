"""IPhO 2023 Korean theory solutions in the official solutions' design.

    python3 tools/ko/ipho2023/sol_style.py <ko.pdf> <official-en.pdf> <out.pdf>

The Korean solutions were printed with a plain header («이론 문제 풀이» and the page code in body type) and black
headings.  Each page is rebuilt: the official header (the IPhO 2023 logo, «Solutions to Theory Problems», the page
code and the rule) is taken from the official page with the same code (a Korean page past the official ones takes the
first page's logo and label, its own code and the rule), and the Korean page below its own header is set under the
rule, scaled by the few per cent that the taller official header needs.  The problem title and the Part headings are
set again in the official Noto Sans Bold, dark blue (#0000b3), at the official sizes (15.9 pt, 11 pt)."""
import os
import re
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, '..', 'fonts')
BLUE = (0, 0, 0xb3 / 255)
KO_HEAD = 62     # the Korean header lies above this
EN_HEAD = 77     # the official header, down to its rule (y 75.3)
TOP = 84         # the Korean body starts here
CODE_X = 420     # the page code lies right of this


def restyle_headings(page):
    heads = []
    for b in page.get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            chars = [c for s in l['spans'] for c in s['chars']]
            text = ''.join(c['c'] for c in chars).strip()
            size = max((s['size'] for s in l['spans']), default=0)
            if l['bbox'][1] > KO_HEAD and size > 10.3 and re.match(r'^(이론 문제 \d+\s*:|파트 [A-Z]\.)', text):
                heads.append((pymupdf.Rect(l['bbox']), l['spans'][0]['origin'], text, text.startswith('이론')))
    for r, *_ in heads:
        page.add_redact_annot(r + (-1, -1, 1, 1))
    if heads:
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
    page.insert_font(fontname='kb', fontfile=os.path.join(FONTS, 'NotoSansKR-Bold.ttf'))
    for r, (x, y), text, title in heads:
        page.insert_text((x, y + (3 if title else 0.5)), text, fontname='kb', fontsize=15.9 if title else 11, color=BLUE)


def code_of(page):
    for b in page.get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            if l['bbox'][1] < KO_HEAD:
                t = ''.join(c['c'] for s in l['spans'] for c in s['chars'])
                m = re.search(r'S\d+\s*[‒\-]\s*\d+', t)
                if m:
                    return re.sub(r'\s*[‒\-]\s*', '-', m.group(0))


def main(src, orig, dst):
    ko, en, out = pymupdf.open(src), pymupdf.open(orig), pymupdf.open()
    code_size = 28.3
    reg = pymupdf.Font(fontfile=os.path.join(FONTS, 'NotoSans-Regular.ttf'))
    for i, page in enumerate(ko):
        code = code_of(page)
        restyle_headings(page)
    for i, page in enumerate(ko):
        code = code_of(pymupdf.open(src)[i])
        W, H = page.rect.width, page.rect.height
        new = out.new_page(width=en[0].rect.width, height=en[0].rect.height)
        nw, nh = new.rect.width, new.rect.height
        # the Korean page below its own header, under the official rule
        k = (nh - TOP) / (H - KO_HEAD)
        new.show_pdf_page(pymupdf.Rect(0, TOP, W * k, nh), ko, i, clip=pymupdf.Rect(0, KO_HEAD, W, H))
        own = i < len(en)
        src_page = i if own else 0
        clip = pymupdf.Rect(0, 0, nw, EN_HEAD) if own else pymupdf.Rect(0, 0, CODE_X, 73)
        new.show_pdf_page(clip, en, src_page, clip=clip)
        if not own:
            rule = next(d for d in en[0].get_drawings() if d['rect'].width > 300 and d['rect'].y0 < EN_HEAD)
            new.draw_line((rule['rect'].x0, 75.3), (rule['rect'].x1, 75.3), width=rule.get('width') or 1.2)
            if code:
                new.insert_font(fontname='nr', fontfile=os.path.join(FONTS, 'NotoSans-Regular.ttf'))
                new.insert_text((539 - reg.text_length(code, fontsize=code_size), 68), code, fontname='nr', fontsize=code_size)
    out.save(dst, garbage=3, deflate=True)


if __name__ == '__main__':
    main(*sys.argv[1:4])
