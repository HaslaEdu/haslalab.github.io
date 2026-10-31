"""Rebuild the unbranded vector stationery from the official 2026 paper.

Only fixed elements are retained. Real redaction removes changing titles and
page numbers, so old years/numbers cannot survive in PDF search text.
"""
from pathlib import Path
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'tmp/kphe_archive/originals/KPhE_2026_T2c_KO.pdf'
if not source.exists():
    source = ROOT / 'pdfx/kphe/KPhE_2026_T2c_KO.pdf'
original = fitz.open(source)
doc = fitz.open()
page = doc.new_page(width=728, height=1031)
for coordinates in [(0, 0, 728, 86), (363.60, 89.90, 364.04, 967.36), (328, 970, 410, 986)]:
    rect = fitz.Rect(coordinates)
    page.show_pdf_page(rect, original, 0, clip=rect, keep_proportion=False)
page.add_redact_annot(fitz.Rect(170, 27, 680, 80), fill=(1, 1, 1))
page.add_redact_annot(fitz.Rect(367.4, 970, 410, 986), fill=(1, 1, 1))
page.apply_redactions(images=0, graphics=0, text=0)
if page.get_text().strip() != '페이지':
    raise ValueError('Unexpected text survives in fixed stationery')
doc.subset_fonts()
doc.set_metadata({'title': '한국물리학회 2026 문항 서식의 고정 요소',
                  'subject': '원문 로고·가로선·중간선·페이지 글자; 가변 제목과 숫자는 제거'})
doc.save(ROOT / 'tools/kphe_template_assets.pdf', garbage=4, deflate=True)
print('Fixed KPS vector stationery rebuilt; no old year or page number remains.')
