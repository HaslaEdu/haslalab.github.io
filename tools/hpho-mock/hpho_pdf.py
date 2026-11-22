"""Header changes on the author's papers (IPhO exam tools layout), shared by relogo.py and guide.py.

  logo(page)            the source logo (a raster image near the top left) out, the HPhO wordmark in, fitted to its box
  header(page, lang)    the header text redrawn: the candidate code (e.g. "KOR-S-01 T-1 Q-1") and the answer-sheet QR code
                        that encodes it are removed, the language label becomes "Korean (Official)" / "English (Official)",
                        every other header span is put back where it was, in its own font and size
Nothing under the header is touched."""
import re
from pathlib import Path
import pymupdf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FONTS = ROOT / 'tools/ko/fonts'
LOGO = HERE / 'hpho-wordmark.png'          # 2400 x 850 render of logo/brand/hpho-wordmark-light.svg
LOGO_PX = (2400, 850)
LOGO_BOX = pymupdf.Rect(56.9, 96.8, 164.8, 142.8)   # where the source papers put their logo
LABEL = {'ko': 'Korean (Official)', 'en': 'English (Official)'}
CODE = re.compile(r'^[A-Z]{3}-S-\d+\b')
HEADER_BOTTOM = 150                         # the header rule sits at y = 147.5 to 149.6 pt


def _remove(page, rect, images):
    page.add_redact_annot(rect)
    page.apply_redactions(images=images, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE, text=pymupdf.PDF_REDACT_TEXT_NONE)


def logo(page):
    found = False
    for im in page.get_images(full=True):
        xref, w, h = im[0], im[2], im[3]
        for r in page.get_image_rects(xref):
            if r.y1 > HEADER_BOTTOM + 5:
                continue
            if (700 <= w <= 1100 and 2.0 <= w / h <= 2.8 or (w, h) == LOGO_PX) and r.x0 < 120:   # the logo (or ours, to resize it)
                box = LOGO_BOX if (w, h) == LOGO_PX else r
                _remove(page, r, pymupdf.PDF_REDACT_IMAGE_REMOVE)
                # the source logo's box is 108 x 46 pt; the wordmark is wider, so it takes the full height and runs on
                # to the right, well clear of the page label
                page.insert_image(pymupdf.Rect(box.x0, box.y0, box.x0 + box.height * 480 / 170, box.y1), filename=str(LOGO), keep_proportion=True)
                found = True
            elif abs(w - h) < 2 and r.x0 > 200:                                 # the QR code of the candidate code
                _remove(page, r, pymupdf.PDF_REDACT_IMAGE_REMOVE)
    return found


def header(page, lang, extra=None):
    spans = [s for b in page.get_text('dict')['blocks'] if b['type'] == 0 for l in b['lines'] for s in l['spans']
             if s['text'].strip() and s['bbox'][3] < HEADER_BOTTOM + 15 and s['bbox'][1] < HEADER_BOTTOM - 5]
    for s in spans:
        page.add_redact_annot(pymupdf.Rect(s['bbox']))
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
    changes = {'Korean (Republic of Korea)': LABEL[lang], 'Korean (Official)': LABEL[lang], 'English (Official)': LABEL[lang], **(extra or {})}
    for i, s in enumerate(spans):
        old = s['text'].strip()
        if CODE.match(old):
            continue
        text = changes.get(old, old)
        if not text:
            continue
        font = 'NotoSans-Bold.ttf' if 'Bold' in s['font'] or 'Black' in s['font'] else 'NotoSans-Regular.ttf'
        f = pymupdf.Font(fontfile=str(FONTS / font))
        x, y = s['origin']
        if s['bbox'][2] > 400 and text != old:          # right-aligned in the template: keep the right edge
            x = s['bbox'][2] - f.text_length(text, fontsize=s['size'])
        c = s['color']
        page.insert_text((x, y), text, fontsize=s['size'], fontname=f'h{i}', fontfile=str(FONTS / font),
                         color=((c >> 16 & 255) / 255, (c >> 8 & 255) / 255, (c & 255) / 255))
