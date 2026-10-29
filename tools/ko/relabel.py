"""Relabel the language line of a Korean olympiad paper, as IPhO and APhO label theirs: «Korean (Korea (Republic of))»
in Noto Sans 10 pt, right-aligned 4.5 pt above the header rule, and the rule itself 2 pt thick (some translations had
«한국어(번역본)», a hairline rule, or the label set off its place).

    python3 tools/ko/relabel.py <in.pdf> <out.pdf>

On every page: the label (any small text right of x 380 between the page code and the rule — «한국어(번역본)», a white
patch with the old label drawn over it, …) is taken out; the page code («Q1-2», «A1-1», …) shares its band and goes
with it, so it is set again in Noto Sans Bold where it was (a code drawn in a Type3 font sits above the label and is
left as it is); a rule thinner than 1.5 pt is replaced by the official 1.99 pt one (at 143.9 pt on the APhO papers,
as the official ones have it)."""
import os
import re
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(HERE, 'fonts', n)
LABEL = 'Korean (Korea (Republic of))'
REG, BOLD = pymupdf.Font(fontfile=F('NotoSans-Regular.ttf')), pymupdf.Font(fontfile=F('NotoSans-Bold.ttf'))
CODE = re.compile(r'^[A-Z]\d+[-‑]\d+$')


def rule_of(page):
    """The header rule: the first long horizontal line or thin bar in the top 200 pt."""
    for d in page.get_drawings():
        r = d['rect']
        if r.y0 < 200 and r.width > 300 and r.height < 2:
            w = d.get('width') or r.height
            return r, w, (r.y0 + r.y1) / 2
    return None, 0, None


def relabel(src, dst):
    doc = pymupdf.open(src)
    for page in doc:
        rule, rw, ry = rule_of(page)
        if rule is None:
            continue
        spans = [s for b in page.get_text('dict')['blocks'] for l in b.get('lines', []) for s in l['spans']
                 if s['text'].strip() and s['bbox'][0] > 380 and s['bbox'][1] < ry]
        codes = [s for s in spans if s['size'] > 40 and CODE.match(s['text'].strip())]
        labels = [s for s in spans if s['size'] < 13 and s['bbox'][3] > ry - 25]
        if not labels:
            continue
        box = pymupdf.Rect(labels[0]['bbox'])
        for s in labels[1:]:
            box |= pymupdf.Rect(s['bbox'])
        right = 536.0 if abs(box.x1 - 536) < 3 else round(box.x1, 1)
        box.y1 = min(box.y1, ry - 1.0)                     # never below the rule (the text under it stays)
        # a code whose box reaches into the label band goes with the label and is set again (Type3 codes sit higher)
        # (where the visible code is Type3 the Noto Sans one is only its hidden text layer: never set it visibly)
        type3 = any(s['font'].startswith('Type3') for s in codes)
        redo = [s for s in codes if not type3 and pymupdf.Rect(s['bbox']).intersects(box)]
        keep = [(s['text'].strip().replace('‑', '-'), s['origin'], s['size']) for s in redo]
        page.add_redact_annot(box)
        thin = rw < 1.5
        if thin:
            page.add_redact_annot(pymupdf.Rect(rule.x0 - 1, ry - 1.2, rule.x1 + 1, ry + 1.2))
            if type3 and abs(ry - 143.9) < 2:
                ry = 143.9                                 # where IPhO and APhO papers draw it (APhO 2026: 145.2)
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED)
        page.insert_font(fontname='nr', fontfile=F('NotoSans-Regular.ttf'))
        page.insert_font(fontname='nb', fontfile=F('NotoSans-Bold.ttf'))
        for text, (x, y), size in keep:
            page.insert_text((x, y), text, fontname='nb', fontsize=size)
        page.insert_text((right - REG.text_length(LABEL, fontsize=10), ry - 4.5), LABEL, fontname='nr', fontsize=10)
        if thin:
            page.draw_line((56.7, ry), (max(rule.x1, 538.6), ry), color=(0, 0, 0), width=1.9925)
    doc.subset_fonts()
    doc.save(dst, garbage=4, deflate=True)


if __name__ == '__main__':
    relabel(sys.argv[1], sys.argv[2])
