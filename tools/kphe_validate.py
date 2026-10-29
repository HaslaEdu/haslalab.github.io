"""Verify original-paper fidelity, 2023 transcription links and removal of blank sheets."""
import hashlib
import json
import re
import sys
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'tools/theory/kphe.json').read_text(encoding='utf-8'))
overlay=json.loads((ROOT/'tools/kphe_print.json').read_text(encoding='utf-8'))['kphe']
cache=ROOT/'tmp/kphe_archive/originals'
assert len(manifest['years'])==8
exams=questions=originals=0
official_files=set()
for year in manifest['years']:
    y=str(year['y']);current=int(y[:4])>=2024
    expected=set('abcd') if current else set('bc' if y=='2023-1' else 'bcd')
    assert {p[-1] for p in year['keys']}==expected,(y,'missing levels')
    edition=overlay[y]
    for part,key in year['keys'].items():
        files=edition['f'][part]
        assert 'paper' in files and 'key' in files,(y,part)
        assert 'answer' not in files,(y,part,'blank answer sheet remains')
        if '--require-solutions' in sys.argv: assert 'sol' in files,(y,part,'missing explanation')
        assert all(isinstance(a,int) and 1<=a<=5 for k in key for a in (k if isinstance(k,list) else [k]))
        if current:
            source=next(f for f in year['files'] if f['part']==part and f['kind']=='paper')
            original=cache/source['file'];public=ROOT/files['paper']
            assert hashlib.sha256(original.read_bytes()).digest()==hashlib.sha256(public.read_bytes()).digest(),(y,part,'official paper was edited')
            originals+=1
        regions=edition['questionRegions'][part]
        assert len(regions)==len(key),(y,part,'question count')
        doc=fitz.open(ROOT/files['paper'])
        for number,region in enumerate(regions,1):
            segments=region if isinstance(region,list) else [region];content=''
            for segment in segments:
                page=doc[segment['page']-1];x0,y0,x1,y1=segment['rect']
                assert 0<=x0<x1<=1 and 0<=y0<y1<=1
                clip=fitz.Rect(x0*page.rect.width,y0*page.rect.height,x1*page.rect.width,y1*page.rect.height)
                content+=page.get_text(clip=clip)
            assert re.search(r'(?m)^\s*%d\s*[.．]'%number,content),(y,part,number,content[:60])
        exams+=1;questions+=len(key)
    for f in year['files']:
        if current and f['kind'] in ('paper','key'):official_files.add(f['file'])
assert originals==24 and exams==29 and questions==572,(originals,exams,questions)
assert not list((ROOT/'pdfx/kphe').glob('KPhE_*A.pdf')),'blank answer PDFs remain'
for pdf in (ROOT/'pdfx/kphe').glob('*.pdf'):
    for page in fitz.open(pdf):
        if pdf.name in official_files:
            assert abs(page.rect.width/page.rect.height-210/297)<.01,pdf.name
        else:
            assert abs(page.rect.width-595)<1 and abs(page.rect.height-842)<1,pdf.name
        assert page.get_text().strip(),pdf.name
        assert not page.rotation,pdf.name
print(f'Validated {exams} exams / {questions} questions; {originals} official papers byte-identical; no blank answer sheets.')
