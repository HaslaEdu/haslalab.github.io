"""Remove the sliver of a split line left at the foot of a page: when the HTML printer moved a line (or display
equation) to the next page, the top few tenths of a point of its glyphs, drawn as paths, can stay below the last
text line of the page, clipped by the page area, and print as grey specks (APhO 2025 T1 S p1, WoPhO 2011 T13 S p2).

The small filled shapes lying below the page's last text line (more than 8 pt below it, each under 20 pt high,
together under 14 pt high) are redacted - only after checking that no text, image or other drawing touches their area.
Check by eye that the whole line is at the top of the next page before using it.

    python3 tools/ko/foot_sliver.py <in.pdf> <out.pdf> <page> [<page> ...]      (pages 1-based)"""
import sys

import pymupdf


def fix(src, dst, pages):
    doc = pymupdf.open(src)
    for pg in pages:
        p = doc[pg - 1]
        ys = [l['bbox'][3] for b in p.get_text('dict')['blocks'] if b.get('type') == 0 for l in b['lines']
              if any(s['text'].strip() for s in l['spans'])]
        last = max(ys)
        drs = p.get_drawings()
        small = [d['rect'] for d in drs if d['rect'].y0 > last + 8 and d['rect'].height < 20
                 and d.get('fill') not in (None, (1.0, 1.0, 1.0))]
        if not small:
            print('p%d: nothing below the last line' % pg)
            continue
        R = pymupdf.Rect(small[0])
        for s in small:
            R |= s
        R = R + (-0.5, -0.5, 0.5, 0.5)
        others = [d for d in drs if d['rect'].intersects(R) and not any(d['rect'] == s for s in small)]
        if R.height > 14 or others or p.get_text('text', clip=R).strip() or \
                any(pymupdf.Rect(i['bbox']).intersects(R) for i in p.get_image_info()):
            print('p%d: area %s not clean - left as is' % (pg, [round(v, 1) for v in R]))
            continue
        p.add_redact_annot(R)
        p.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                           graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                           text=pymupdf.PDF_REDACT_TEXT_NONE)
        print('p%d: removed %d shapes in %s' % (pg, len(small), [round(v, 1) for v in R]))
    doc.save(dst, garbage=3, deflate=True)


if __name__ == '__main__':
    fix(sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3:]])
