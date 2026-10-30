"""Verify recovered KPhC answer bytes, glyph excerpts and grading boundaries."""
import hashlib,json,sys
from pathlib import Path
import numpy as np,cv2,pymupdf as fitz
root=Path(__file__).resolve().parents[1];work=root/'tmp/kphc_answers_research'
audit=json.loads((root/'tools/kphc_answer_sources.json').read_text(encoding='utf8'))
keys=json.loads((root/'tools/kphc_official_keys.json').read_text(encoding='utf8'))
manifest=json.loads((root/'tools/theory/kphc.json').read_text(encoding='utf8'))
assert all('keys' not in y for y in manifest['years'])
assert keys['not_for_automatic_grading'] is True
files=audit['files'];assert len(files)==10
assert len({r['source_sha256'] for r in files if r['source_type']=='preserved_official_answer'})==6
for row in files:
    path=root/row['local'];data=path.read_bytes()
    assert hashlib.sha256(data).hexdigest()==row['sha256']
    pdf=fitz.open(path);assert len(pdf)==row['pages']
    if row['source_type']=='preserved_official_answer':
        source=work/'privatenote-archive-0'/row['archive_member']
        assert data==source.read_bytes()
    assert len([y for y in manifest['years'] if y['y']==row['year'] and any(f.get('file')==row['file'] for f in y['files'])])==1
reports=[]
for year in(2020,2021):
    source=fitz.open(work/f'privatenote-archive-0/물올 기출/{year}PA.pdf')
    target=fitz.open(root/f'pdfx/kphe/KPhC_{year}_TK.pdf')
    assert len(target)==2
    for i,page in enumerate(target):
        assert abs(page.rect.width-595.276)<.01 and abs(page.rect.height-841.89)<.01
        assert '학습용' not in page.get_text()
        page.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csRGB,alpha=False).save(work/f'{year}-final-page-{i+1}.png')
    for answer in keys['years'][str(year)]['parts']['T']['answers']:
        def render(document,page,rect):
            p=document[page-1].get_pixmap(matrix=fitz.Matrix(3,3),clip=fitz.Rect(rect),colorspace=fitz.csRGB,alpha=False)
            return np.frombuffer(p.samples,dtype='uint8').reshape(p.height,p.width,3).copy()
        raw=render(source,answer['source_page'],answer['source_rect'])
        out=render(target,answer['excerpt_pdf_page'],answer['excerpt_pdf_rect'])
        if out.shape!=raw.shape:out=cv2.resize(out,(raw.shape[1],raw.shape[0]))
        a=np.min(raw,axis=2)<220;b=np.min(out,axis=2)<220
        assert np.any(a) and np.any(b)
        distance=cv2.distanceTransform((~b).astype('uint8'),cv2.DIST_L2,3)
        reverse=cv2.distanceTransform((~a).astype('uint8'),cv2.DIST_L2,3)
        recall=float(np.mean(distance[a]<=1.5));precision=float(np.mean(reverse[b]<=1.5))
        report={'year':year,'number':answer['number'],'recall_1_5_pixels':round(recall,6),'precision_1_5_pixels':round(precision,6)}
        assert recall>=.97 and precision>=.97,report
        reports.append(report)
assert len(reports)==60
assert sum(part['answer_count'] for y in keys['years'].values() for part in y['parts'].values())==250
assert keys['years']['2015']['parts']['T1']['answers'][1]['answer_type']=='full_credit'
assert keys['years']['2019']['parts']['T']['answers'][6]['accepted_responses']==[[3],[4]]
assert keys['years']['2019']['parts']['T']['answers'][27]['accepted_responses']==[[1,5]]
sys.path.insert(0,str((root/'tools').resolve()))
import theory_build
catalog,bad,_,_=theory_build.load()
assert not bad,bad[:5]
for year in manifest['years']:
    current=catalog['kphe'][str(year['y'])]
    assert 'k' not in current
    for part in [p['id'] for p in year['problems']]:assert current['f'][part]['key'].endswith('K.pdf')
result={'status':'passed','original_answer_sources_unchanged':6,'public_download_entries':10,
    'structured_answers':250,'inline_native_clips_verified':60,
    'min_recall_1_5_pixels':min(r['recall_1_5_pixels'] for r in reports),
    'min_precision_1_5_pixels':min(r['precision_1_5_pixels'] for r in reports),
    'no_legacy_omr_keys_added':True,'clips':reports}
(work/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=1)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='clips'},ensure_ascii=False,indent=2))
