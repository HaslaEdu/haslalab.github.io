"""The header of the author's papers on the English pages, so the English papers carry the same header as the Korean ones.

  python3 -I tools/hpho-mock/stamp_en.py header IN.pdf OUT.pdf ID Q|A|S
      IN is a page set rendered by build.mjs with an empty header band. The header band of the original's first Q page
      (A: first A page; S: first page of ID's solution in original/solutions.pdf) is copied onto every page, with the
      HPhO logo, no candidate code, "English (Official)", and its own page label (Q1-1, Q1-2, ... or A1-1 ...).
  python3 -I tools/hpho-mock/stamp_en.py writing OUT.pdf ID
      the Korean writing sheets (hpho/samples/mock-1/ko/ID-writing.pdf), with the English label."""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pymupdf
from hpho_pdf import logo, header, FONTS

HERE = Path(__file__).resolve().parent
BAND = pymupdf.Rect(0, 0, 595.28, 152)
PROBLEM = {'T1': 'T-1', 'T2': 'T-2', 'T3': 'T-3', 'E1': 'E-1', 'E2': 'E-2'}


def big(page):
    return next((s for b in page.get_text('dict')['blocks'] if b['type'] == 0 for l in b['lines'] for s in l['spans'] if s['size'] > 50), None)


def pages_of(doc, letter):
    return [p.number for p in doc if (s := big(p)) and s['text'].strip().startswith(letter)]


def template(pid, kind):
    if kind == 'S':
        doc = pymupdf.open(str(HERE / 'original/solutions.pdf'))
        code = PROBLEM[pid]
        first = next(p.number for p in doc if re.search(r'[A-Z]{3}-S-\d+ ' + code + r' ', p.get_text()))
    else:
        doc = pymupdf.open(str(HERE / f'original/{pid}.pdf'))
        first = pages_of(doc, kind)[0]
    doc.select([first])
    page = doc[0]
    label = big(page)
    logo(page)
    header(page, 'en', {label['text'].strip(): ''})
    # keep only the header band: white out the body so nothing of it shows through the copy
    page.add_redact_annot(pymupdf.Rect(0, BAND.y1, page.rect.x1, page.rect.y1))
    page.apply_redactions()
    return doc, label


def stamp(src, out, pid, kind):
    base, label = template(pid, kind)
    prefix = re.match(r'([QA]\d+)-', label['text'].strip()).group(1)
    font = str(FONTS / 'NotoSans-Bold.ttf')
    f = pymupdf.Font(fontfile=font)
    c = label['color']
    rgb = ((c >> 16 & 255) / 255, (c >> 8 & 255) / 255, (c & 255) / 255)
    doc = pymupdf.open(src)
    for page in doc:
        page.show_pdf_page(BAND, base, 0, clip=BAND)
        text = f'{prefix}-{page.number + 1}'
        x = label['bbox'][2] - f.text_length(text, fontsize=label['size'])
        page.insert_text((x, label['origin'][1]), text, fontsize=label['size'], fontname='big', fontfile=font, color=rgb)
    doc.save(out, garbage=3, deflate=True)


def writing(out, pid):
    """the corrected Korean writing sheets (relogo.py output) with the English label"""
    doc = pymupdf.open(str(HERE.parents[1] / f'hpho/samples/mock-1/ko/{pid}-writing.pdf'))
    for page in doc:
        header(page, 'en')
    doc.save(out, garbage=3, deflate=True)


if __name__ == '__main__':
    if sys.argv[1] == 'header':
        stamp(*sys.argv[2:6])
    elif sys.argv[1] == 'writing':
        writing(*sys.argv[2:4])
    else:
        sys.exit(__doc__)
