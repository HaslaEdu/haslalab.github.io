"""Move equation numbers that overprint their equation (APhO 2021 T3 S: the Korean typesetting draws the displayed
equations - as paths - wider than the English, but the number «(A-3)» stayed at the English position, on top of the
boxed equation).

For every text span that is only an equation number «(A-3)» / «(B-10)» and that touches drawn ink, the ink of its
line (paths overlapping the number's height, starting left of it) is measured and the number is set again just right
of it: its right edge goes to max(old right edge, ink right + gap + width), never past the text column's right edge
(the widest body line of the page). If it cannot fit there it is left alone and reported. The old number is removed
by a text-only redaction (drawings untouched) and re-typed in Times at the same size and baseline.

    python3 tools/ko/eq_label_fix.py <ko.pdf> <out.pdf>"""
import re
import sys

import pymupdf

LABEL = re.compile(r'\s*\([A-Z]-\d+[a-z]?\)\s*')


def fix(src, dst, gap=8.0):
    doc = pymupdf.open(src)
    log = []
    for pno, page in enumerate(doc):
        dct = page.get_text('dict')
        right = max(l['bbox'][2] for b in dct['blocks'] if b.get('type') == 0 for l in b['lines'])
        drs = [d for d in page.get_drawings() if d.get('fill') != (1.0, 1.0, 1.0) and d['rect'].width < 450]
        moves = []
        for b in dct['blocks']:
            if b.get('type') != 0:
                continue
            for l in b['lines']:
                for s in l['spans']:
                    if not LABEL.fullmatch(s['text']):
                        continue
                    lb = pymupdf.Rect(s['bbox'])
                    core = lb + (1, 1, -1, -1)
                    if not any(d['rect'].intersects(core) for d in drs):
                        continue
                    txt = s['text'].strip()
                    w = pymupdf.get_text_length(txt, fontname='tiro', fontsize=s['size'])
                    # push the number right until its box (plus the gap) is clear of every drawing on its line
                    ink_r = max(d['rect'].x1 for d in drs if d['rect'].intersects(core))
                    while True:
                        x1 = max(lb.x1, ink_r + gap + w)
                        test = pymupdf.Rect(x1 - w - gap, lb.y0 + 1, x1, lb.y1 - 1)
                        hit = [d['rect'].x1 for d in drs if d['rect'].intersects(test)]
                        if not hit or max(hit) <= ink_r:
                            break
                        ink_r = max(hit)
                    if x1 > right + 0.5:
                        log.append('p%d %s: no room right of the equation (ink to %.1f) - left as is' % (pno + 1, txt, ink_r))
                        continue
                    others = [t for t in page.get_text('words', clip=lb) if t[4].strip() != txt]
                    if others:
                        log.append('p%d %s: other text in its box %s - left as is' % (pno + 1, txt, others))
                        continue
                    moves.append((txt, lb, s['origin'], s['size'], x1 - w, ink_r))
        for txt, lb, org, size, x0, ink_r in moves:
            page.add_redact_annot(lb)
        if moves:
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                                  text=pymupdf.PDF_REDACT_TEXT_REMOVE)
        for txt, lb, org, size, x0, ink_r in moves:
            page.insert_text((x0, org[1]), txt, fontname='tiro', fontsize=size, color=(0, 0, 0))
            log.append('p%d %s: x %.1f -> %.1f (equation ink ends at %.1f)' % (pno + 1, txt, lb.x0, x0, ink_r))
    doc.save(dst, garbage=3, deflate=True)
    return log


if __name__ == '__main__':
    for line in fix(sys.argv[1], sys.argv[2]):
        print(line)
