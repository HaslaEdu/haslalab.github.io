"""Prepare reviewed CPhO 2007 translations while retaining source equations.

The 20-page source contains four problem pages and sixteen solution pages.
No solution edition is published until its separate prose review is complete.
"""
from pathlib import Path
from collections import Counter
import argparse,copy,json,re,hashlib,shutil
import pymupdf as fitz
import cpho_cjk_translate as cjk
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'tools/ko/cpho/2007/bilingual'

def prepare():
    data=json.loads((FOLDER/'translation.json').read_text(encoding='utf8'))
    raw=FOLDER/'raw-translation.json'
    if not raw.exists():raw.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    else:data=json.loads(raw.read_text(encoding='utf8'))
    source=ROOT/'tmp/source-audit/CPhO_2007_T_ZH.pdf'
    if not source.exists():raise FileNotFoundError('Download the original CPhO_2007_T_ZH.pdf into tmp/source-audit before rebuilding')
    if hashlib.sha256(source.read_bytes()).hexdigest()!='2e30b56ab9274363686cbf5bc1ef7532dcf579e0703de2c01098b003ab70cdd9':
        raise ValueError('The source PDF differs from the reviewed 2007 edition')
    data['source']=str(source.resolve())
    rows={}
    for line in (FOLDER.parent/'problems.tsv').read_text(encoding='utf8').splitlines():
        key,ko,en=line.split('\t');rows[key]=(ko,en)
    by_id={e['id']:e for e in data['entries']}
    # The original PDF stores the trailing kV / in another text object. Include
    # those native glyphs in the same source crop rather than duplicating units.
    original=fitz.open(data['source']);page=original[1];entry=by_id['2-20']
    chars=cjk.characters(page);old=entry['math'][2]
    included=set(old['source_char_indices'])
    units=[c for c in chars if 686<c['origin'][1]<709 and c['origin'][0]>475 and not c['c'].isspace()]
    glyphs=[c for c in chars if c['index'] in included]+units
    bounds=fitz.Rect(glyphs[0]['bbox'])
    for ch in glyphs[1:]:bounds|=fitz.Rect(ch['bbox'])
    cluster={'chars':glyphs,'rect':list(bounds),'y':703.681884765625,'text':'Ek = 135 kV /'}
    entry['math'][2]=cjk.math_image(page.get_svg_image(text_as_path=True),cluster,FOLDER/'2-20-unit-fixed.png')
    entry['rect'][2]=max(entry['rect'][2],bounds.x1)
    for key,(ko,en) in rows.items():
        entry=by_id[key];entry['ko']=ko;entry['en']=en
        entry['color']=0
        if key in ['3-9','3-10','3-12']:
            entry['preserved_math']={'3-9':[1],'3-10':[3],'3-12':[5]}[key]
        expected=Counter(re.findall(r'\[\[\d+\]\]',entry['source']))
        for mi in entry.get('preserved_math',[]):del expected[f'[[{mi}]]']
        for lang in ['ko','en']:
            actual=Counter(re.findall(r'\[\[\d+\]\]',entry[lang]))
            if actual!=expected:raise ValueError(f'{key}/{lang}: expected {expected}, got {actual}')
        # Only one prose entry overlaps an unrelated heading punctuation glyph.
        if key=='3-9':entry['math_reviewed']=True
        if key in ['2-18','2-19']:
            r=fitz.Rect(entry['rect']);entry['insert_rect']=list(r+(-10,-3,10,3))
        if key in ['2-15','2-16','2-17']:
            r=fitz.Rect(entry['rect']);entry['en_insert_rect']=list(r+(0,-3,75,4))
        if key in ['4-19','4-20']:
            r=fitz.Rect(entry['rect']);entry['en_insert_rect']=list(r+(-10,-3,45,4))
    groups=[(1,4,9),(1,10,12),(1,14,22),(1,24,26),
            (2,0,7),(2,9,14),(2,20,22),
            (3,1,5),(3,6,7),(3,9,14),(3,15,16),(3,17,20),
            (3,21,22),(3,23,25),
            (4,1,5),(4,6,7),(4,9,10),(4,12,16),(4,17,18)]
    removed=set();merged={}
    for page,first,last in groups:
        members=[by_id[f'{page}-{n}'] for n in range(first,last+1)]
        entry=copy.deepcopy(members[0]);entry['math']=[];entry['preserved_math']=[]
        entry['erase_rects']=[e['rect'] for e in members]
        entry['review_uncovered_math']=[];entry['math_reviewed']=True
        box=fitz.Rect(members[0]['rect'])
        for member in members[1:]:box|=fitz.Rect(member['rect'])
        entry['rect']=list(box);entry['insert_rect']=list(box)
        texts={kind:[] for kind in ['source','ko','en']}
        for member in members:
            offset=len(entry['math'])
            entry['preserved_math'].extend(offset+mi for mi in member.get('preserved_math',[]))
            for kind in texts:
                texts[kind].append(re.sub(r'\[\[(\d+)\]\]',lambda m:f'[[{int(m[1])+offset}]]',member[kind]))
            entry['math'].extend(member['math'])
        for kind in texts:entry[kind]=' '.join(texts[kind]).strip()
        merged[entry['id']]=entry
        removed.update(e['id'] for e in members[1:])
    data['entries']=[merged.get(e['id'],e) for e in data['entries'] if e['id'] not in removed]
    (FOLDER/'translation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    return data

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-problems',action='store_true')
    args=parser.parse_args()
    prepare()
    inventory=[]
    for lang in ['ko','en']:
        target=ROOT/f'tmp/cpho-build/2007-{lang}-problems-preview.pdf'
        if target.exists():target.unlink()
        cjk.build(FOLDER,target,lang,pages=[1,2,3,4])
        from cpho_2007_figures import replace
        replace(target,lang)
        if args.publish_problems:
            name=f'CPhO_2007_T_{"KO" if lang=="ko" else "BAUPC_EN"}.pdf'
            canonical=ROOT/'pdfx/cpho'/name;canonical.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(target,canonical)
            doc=fitz.open(canonical)
            text=''.join(p.get_text() for p in doc)
            if re.search('[\u3400-\u9fff]',text):raise ValueError('Untranslated Chinese text remains')
            missing=[]
            for pi,page in enumerate(doc):
                for block in page.get_text('dict')['blocks']:
                    if block['type']!=0:continue
                    for line in block['lines']:
                        for span in line['spans']:
                            if ('NotoSansKR' in span['font'] or 'Droid' in span['font']) and any(c in span['text'] for c in ['\x00','�']):missing.append({'page':pi+1,'text':span['text']})
            if missing:raise ValueError(str(missing))
            inventory.append({'file':name,'pages':len(doc),'bytes':canonical.stat().st_size,'sha256':hashlib.sha256(canonical.read_bytes()).hexdigest(),'missing_glyph_spans':missing})
    if args.publish_problems:
        source=ROOT/'tmp/source-audit/CPhO_2007_T_ZH.pdf'
        report={'year':2007,'source':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'source_pages':[1,2,3,4],'source_total_pages':20,'problems':7,'translated_source_rows':97,
                'typeset_regions':38,'redrawn_figures':7,'figure_languages':['ko','en'],'files':inventory,
                'review':'All four pages in each language visually reviewed; source math glyphs and problem geometry retained.'}
        (ROOT/'tools/cpho_2007_inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print(json.dumps(inventory))
