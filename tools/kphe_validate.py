"""Validate archive coverage, A4 outputs and exact question crops before deployment."""
import json
import re
import sys
from pathlib import Path
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'tools/theory/kphe.json').read_text(encoding='utf-8'))
overlay = json.loads((ROOT / 'tools/kphe_print.json').read_text(encoding='utf-8'))['kphe']
assert len(manifest['years']) == 6
exams = questions = 0
for year in manifest['years']:
    y = str(year['y'])
    assert len(year['problems']) == 4
    assert len(year['files']) == 8
    assert len(year['keys']) == 4
    edition = overlay[y]
    for part, key in year['keys'].items():
        f = edition['f'][part]
        assert all(k in f for k in ('paper', 'key', 'answer'))
        if '--require-solutions' in sys.argv:
            assert 'sol' in f, f'Missing explanations: {y} {part}'
        for answer in key:
            assert all(isinstance(a, int) and 1 <= a <= 5 for a in (answer if isinstance(answer, list) else [answer]))
        regions = edition['questionRegions'][part]
        assert len(regions) == len(key), (y, part)
        doc = fitz.open(ROOT / f['paper'])
        for number, region in enumerate(regions, 1):
            page = doc[region['page'] - 1]
            x0, y0, x1, y1 = region['rect']
            assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1
            clip = fitz.Rect(x0 * page.rect.width, y0 * page.rect.height, x1 * page.rect.width, y1 * page.rect.height)
            content = page.get_text(clip=clip).strip()
            assert re.match(r'^%d\s*[.．]' % number, content), (y, part, number, content[:60])
        exams += 1
        questions += len(key)
for pdf in (ROOT / 'pdfx/kphe').glob('*.pdf'):
    doc = fitz.open(pdf)
    for page in doc:
        assert abs(page.rect.width - 595) < 1 and abs(page.rect.height - 842) < 1, pdf.name
        assert page.get_text().strip(), pdf.name
        assert not page.rotation, pdf.name
print(f'Validated {exams} exams / {questions} questions; all local PDFs are portrait A4.')
