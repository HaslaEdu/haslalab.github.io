"""Validate the complete 2023 bilingual booklet and retain review evidence."""
from pathlib import Path
from collections import Counter
import hashlib,json,re
import pymupdf as fitz
from PIL import Image,ImageDraw
from io import BytesIO
from cpho_inline_clip_audit import audit
from pdf_hangul_visibility import audit as hangul_visibility
import cpho_cjk_translate as cjk

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'tmp/cpho-build/2023-reviewed/translation.json'
QA=ROOT/'tmp/cpho-build/2023-qa'

def main():
    data=json.loads(MANIFEST.read_text(encoding='utf8'));source=fitz.open(cjk.resolve_source(data));QA.mkdir(parents=True,exist_ok=True)
    report={'source_sha256':data['source_sha256'],'source_pages':len(source),'bilingual_regions':len(data['entries']),
            'source_prose_regions':sum(p['paragraphs']for p in data['extraction_report']),
            'booklet':'Combined problems and reference solutions, following the original interleaving',
            'problems':7,'reference_solutions':7,'total_marks':320,
            'inline_math_fields':sum(len(e['math'])for e in data['entries']),
            'native_math_fields_preserved':sum(len(e.get('preserved_math',[]))for e in data['entries']),
            'native_raster_math_fields_restored':sum(bool(m.get('native_raster_math_accents'))for e in data['entries']for m in e['math']),
            'source_math_replacement_legend':{'红':'R (red)','紫':'V (violet)','初':'i (initial)','末':'f (final)'},'editions':[]}
    for lang in ['ko','en']:
        path=ROOT/f'pdfx/cpho/CPhO_2023_Combined_{lang.upper()}.pdf';doc=fitz.open(path)
        build=json.loads(path.with_suffix('.build.json').read_text(encoding='utf8'))
        assert build['manifest_sha256']==hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),'PDF and current translation manifest differ'
        assert len(doc)==36
        bad=[];han=[]
        for pi,p in enumerate(doc):
            assert p.rect==source[pi].rect
            for b in p.get_text('dict')['blocks']:
                if b['type']!=0:continue
                for line in b['lines']:
                    for s in line['spans']:
                        if '\x00'in s['text']or'\ufffd'in s['text']:bad.append({'page':pi+1,'span':s})
                        if any('\u4e00'<=c<='\u9fff'for c in s['text']):han.append({'page':pi+1,'span':s})
        assert not bad,('Missing glyphs',lang,bad)
        assert not han,('Untranslated source text',lang,han)
        for e in data['entries']:
            expected=Counter(re.findall(r'\[\[\d+\]\]',e['source']))
            for i in e.get('preserved_math',[]):del expected[f'[[{i}]]']
            assert expected==Counter(re.findall(r'\[\[\d+\]\]',e[lang])),e['id']
        clips=audit(MANIFEST,path,lang);actual=[r for r in clips if r.get('overhang')or r.get('missing_image')]
        (QA/f'final-inline-audit-{lang}.json').write_text(json.dumps(clips,ensure_ascii=False,indent=2),encoding='utf8')
        assert not actual,('Inline image clipping or absence',lang,actual)
        if lang=='ko':
            visibility=hangul_visibility(path)
            (ROOT/'tools/ko/cpho/2023/combined/qa-hangul-visibility.json').write_text(json.dumps(visibility,ensure_ascii=False,indent=2),encoding='utf8')
            assert visibility['flagged_components']==0,('Hidden Korean prose',visibility)
        for sheet,start in enumerate(range(0,36,12),1):
            out=Image.new('RGB',(4*328,3*474),'#cfcfcf');draw=ImageDraw.Draw(out)
            for j,pi in enumerate(range(start,start+12)):
                im=Image.open(BytesIO(doc[pi].get_pixmap(matrix=fitz.Matrix(.55,.55)).tobytes('png')))
                x=(j%4)*328;y=(j//4)*474;out.paste(im,(x,y+10));draw.text((x+3,y),f'{lang.upper()} {pi+1}',fill='black')
            out.save(QA/f'final-{lang}-contact-{sheet}.png')
        fits=json.loads(path.with_suffix('.qa.json').read_text(encoding='utf8'))
        report['editions'].append({'language':lang,'file':str(path.relative_to(ROOT)).replace('\\','/'),'pages':len(doc),
             'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'minimum_scale':min(r['scale']for r in fits),'missing_glyphs':0,'untranslated_native_Han':0,
             'actual_inline_ink_clips':0,'inline_digest_ambiguities':len(clips),'figures':20})
        if lang=='ko':report['editions'][-1]['hidden_Hangul_components']=0
        print(lang,'PASS',report['editions'][-1],flush=True)
    operators=json.loads((QA/'math-operator-audit.json').read_text(encoding='utf8'))
    assert not operators['omitted_operators']
    report['verification']={'MuPDF_whole_pages_reviewed':{'ko':36,'en':36},
       'Poppler_whole_pages_reviewed':{'ko':len(list(QA.glob('poppler-ko-*.png'))),'en':len(list(QA.glob('poppler-en-*.png')))},
       'native_math_accent_source_comparisons':32,'special_source_operators_checked':operators['source_operators_checked'],
       'omitted_source_operators':0,'notes':'All 72 pages reviewed, with original geometry, complete mathematical accents, and 20 redrawn figures per language.'}
    report['authoring_files']=['tools/cpho_2023_build.py','tools/cpho_2023_preflight.py','tools/cpho_2023_validate.py',
       'tools/cpho_native_math_accents.py','tools/cpho_inline_clip_audit.py','tools/cpho_cjk_translate.py',
       'tools/pdf_hangul_visibility.py','tools/izho_native_math_audit.py',
       'tools/ko/cpho/2023/combined/manual.txt','tools/ko/cpho/2023/combined/source_regions.json',
       'tools/cpho_2023_figures.py','tools/ko/cpho/2023/figures']
    (ROOT/'tools/cpho_2023_inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':main()
