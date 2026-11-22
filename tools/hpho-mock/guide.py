"""Writes the general instructions (G0) of an HPhO paper on the page of the author's own guide (original/guide-template.pdf),
so the header, margins, fonts and spacing are the template's. Only the header (hpho_pdf.py: the HPhO logo, no candidate
code, "Korean (Official)" / "English (Official)") and the text below it change.

  python3 -I tools/hpho-mock/guide.py mock-1

reads tools/hpho-mock/<set>/G-theory.<lang>.html and G-experiment.<lang>.html (the body: a title, a subtitle line, paragraphs,
<h3> headings and <ul> lists) and writes hpho/samples/<set>/<lang>/G-theory.pdf and G-experiment.pdf."""
import sys, re
from pathlib import Path
import pymupdf
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hpho_pdf import logo, header
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FONTS = ROOT / 'tools/ko/fonts'
LOGO = HERE / 'hpho-wordmark.png'
KIND = {'theory': ('Theoretical Exam', 'T'), 'experiment': ('Experimental Exam', 'E')}

# the template's measurements (pt): body 10 pt on 12 pt lines, 18 pt between paragraphs, bullets at 73.2, text at 81.6
CSS = """
@font-face{font-family:K;src:url(NotoSansKR-Regular.ttf)}
@font-face{font-family:K;src:url(NotoSansCJKkr-Bold.otf);font-weight:bold}
@font-face{font-family:L;src:url(NotoSans-Regular.ttf)}
@font-face{font-family:L;src:url(NotoSans-Bold.ttf);font-weight:bold}
body{font-family:FAMILY;font-size:10pt;line-height:11.95pt;color:#000;margin:0}
h1{font-size:15.9pt;line-height:16pt;color:#0000b3;font-weight:bold;margin:0 0 7pt}
p.sub{margin:0 0 26pt}
p{margin:0 0 6pt}
h3{font-size:10pt;font-weight:bold;margin:2pt 0 6pt}
ul{margin:0 0 6pt;padding-left:24.9pt}
li{margin:0 0 6pt}
"""


def build(set_name):
    src = HERE / set_name
    out_root = ROOT / 'hpho/samples' / set_name
    arch = pymupdf.Archive(str(FONTS))
    for kind in ('theory', 'experiment'):
        for lang in ('ko', 'en'):
            html_file = src / f'G-{kind}.{lang}.html'
            if not html_file.exists():
                continue
            doc = pymupdf.open(str(HERE / 'original/guide-template.pdf'))
            page = doc[0]
            logo(page)
            header(page, lang, {'Theoretical Exam': KIND[kind][0]})
            # the body: everything under the header goes, the new text is set in the same box
            body = pymupdf.Rect(56.0, 150.0, 539.5, 800.0)
            page.add_redact_annot(body)
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_REMOVE, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED)
            html = html_file.read_text()
            spare, _ = page.insert_htmlbox(pymupdf.Rect(56.7, 156.2, 538.6, 800.0), html, css=CSS.replace('FAMILY', 'K' if lang == 'ko' else 'L'), archive=arch)
            if spare < 0:
                sys.exit(f'{html_file.name}: the text does not fit on one page')
            out = out_root / lang / f'G-{kind}.pdf'
            out.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(out), garbage=3, deflate=True)
            print(out.relative_to(ROOT))


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'mock-1')
