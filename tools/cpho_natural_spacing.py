"""Natural same-size CPhO prose using reviewed original-style PDF editions.

The strict baseline PDFs and original translation journals remain immutable.
Only new D: proofs are written. Source diagrams/display equations are blocked;
eligible Korean regular serif Hangul uses Batang and native mathematics keeps
its original CID/font program/size/paint, with horizontal movement only.
"""
from __future__ import annotations
import argparse,hashlib,json,os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import pymupdf as fitz
from pdf_korean_natural_composer import compose_page
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
D=Path('D:/CodexBuilds/Hasla-original-style-20261031')
OUT=D/'cpho-natural-spacing'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def baseline(year,language):
    if language=='en' or year==2007:
        return D/f'english-face-repair/{year}/editions/CPhO_{year}_T_{language.upper()}.pdf'
    return ROOT/f'tmp/original-style-repair/{year}/editions/CPhO_{year}_T_{language.upper()}.pdf'


def original(year):return ROOT/f'tmp/source-audit/CPhO_{year}_T_ZH.pdf'


def source_plan(year,number):
    data=json.loads((ROOT/f'tmp/original-style-repair/{year}/slots.json').read_text('utf8'))
    return next(p for p in data['pages'] if p['source_page']==number)


def placements(year,language,number):
    journal=json.loads(baseline(year,language).with_suffix('.build.json').read_text('utf8'))
    slots={s['id']:s for s in source_plan(year,number)['slots']}
    rows=[]
    for row in journal['fit_report']:
        if row['page']!=number or not row['text'].strip():continue
        slot=slots[row['id']]
        rows.append(dict(row,point=row['origin'],source_font=slot['source_font'],
                         italic=slot.get('italic',False),
                         border_width=slot.get('line_width'),family=slot['family'],
                         overlay=slot.get('overlay',True),
                         align=slot.get('align'),source_rect=slot['source_rect']))
    # These language-only bitmap captions were already translated in the
    # immutable edition. Their source numbers and bitmap streams stay locked.
    raster=[]
    for item in journal.get('raster_caption_translation',[]):
        if item['page']!=number:continue
        raster.append(dict(item,id='raster-caption-'+str(item['number']),
            size=item['translation_font_size'],text=item['translation'],
            runs=[dict(origin=item['translation_origin'],text=item['translation'],angle=0)],
            source_ink_rect=item['source_ink'],effective_alignment='right'))
    raster.extend(v for v in journal.get('raster_label_translation',[]) if v['page']==number)
    with fitz.open(baseline(year,language)) as doc:
        from izho_natural_spacing import records,visible
        physical=visible(records(doc[number-1]))
        for item in raster:
            for i,run in enumerate(item['runs']):
                if run.get('angle',0):continue # A separate font-only rotated-label pass handles these.
                x,y=run['origin'];size=item['size']
                matched=[g for g in physical if abs(g['origin'][1]-y)<.02 and x-.03<=g['origin'][0]<=x+len(run['text'])*size+2]
                expected=''.join(c for c in run['text'] if not c.isspace())
                matched=sorted(matched,key=lambda g:g['origin'][0])[:len(expected)]
                if ''.join(g['c'] for g in matched)!=expected:raise ValueError(('Bitmap prose placement mismatch',item['id'],run['text']))
                width=max(g['bbox'][2] for g in matched)-x
                box=item['source_ink_rect'];alignment=item['effective_alignment']
                if alignment=='vertical':alignment='center'
                rows.append(dict(id=item['id']+'-'+str(i),page=number,text=run['text'],point=[x,y],origin=[x,y],
                    source_font='Song (raster ink inference; no font metadata)',font=matched[0]['font'],family='serif',
                    size=size,width=width,italic=False,border_width=None,overlay=True,align=alignment,
                    source_rect=box,raster_label=True,label_center=(box[0]+box[2])/2,label_right=box[2]))
    return rows


def prepare(year,language,number,input_path=None,input_page=None,prose_placements=None):
    input_path=Path(input_path or baseline(year,language));source=original(year);data=source_plan(year,number)
    journal=prose_placements or placements(year,language,number);by_y=defaultdict(list)
    for p in journal:
        y=round(p['point'][1],3);near=[v for v in by_y if abs(v-y)<.12]
        by_y[near[0] if near else y].append(p)
    with fitz.open(source) as doc:
        page=doc[number-1]
        images=[list(info['bbox']) for info in page.get_image_info() if info['width']>8 and info['height']>8]
        # The last 2007 apparatus is native paths, not a bitmap. Its source
        # u/theta/z variables and laser-arrow geometry are a stationary figure.
        if (year,number)==(2007,4):images.append([163,560,430,625])
        # Source Word drawings outside an image can include its axis/arrows.
        # Expanding only horizontally catches those native labels without
        # swallowing separate captions below the image's blank bottom margin.
        excluded=[list(fitz.Rect(r)+(-4,0,4,0)) for r in images]
        content=[min(24.,min(p['point'][0] for p in journal)),{2006:513.2,2007:508.,2022:561.7}[year]]
        regions=[];centers=[];caption_regions=[];picture_labels=[]
        for y,items in sorted(by_y.items()):
            inside=[];outside=[]
            for item in items:
                (inside if item.get('raster_label') or any(fitz.Rect(r).contains(fitz.Point(item['point'])) for r in images) else outside).append(item)
            for item in inside:
                size=item['size'];x=item['point'][0]
                picture_labels.append(dict(rect=[x-size,y-.85*size,x+item['width']+size,y+.32*size],
                    baseline=y,placements=[item['id']],caption=False,alignment=item.get('align') or 'left',
                    center=item.get('label_center',x+item['width']/2),right=item.get('label_right')))
            items=outside
            if not items:continue
            size=max(p['size'] for p in items)
            x0,x1=content
            title=any((p.get('align')=='center' and p['size']>=12) or(p['size']>=14 and y<130) for p in items)
            is_caption=all(p.get('align') in ['center','right'] and p['size']<12 for p in items)
            if is_caption:
                for item in items:
                    cx=item['point'][0]+item['width']/2
                    caption_regions.append(dict(rect=[cx-65,y-.85*item['size'],cx+65,y+.32*item['size']],
                        baseline=y,placements=[item['id']],caption=True,alignment=item['align'],center=cx))
                continue
            if title:
                # The original heading/date center, measured from its actual
                # original line, rather than a guessed left prose slot.
                x0,x1=24.,page.rect.width-24.
                center=page.rect.width/2
                centers.append(dict(baseline=y,center=center))
            if not title and not is_caption:
                for r in excluded:
                    if r[1]<y+size*.2 and r[3]>y-size*.85:
                        if all(p['point'][0]+p['width']<=r[0]+.1 for p in items):x1=min(x1,r[0])
                        elif all(p['point'][0]>=r[2]-.1 for p in items):x0=max(x0,r[2])
            rect=[x0,y-.85*size,x1,y+.32*size]
            entry=dict(rect=rect,baseline=y,placements=[p['id'] for p in items],caption=is_caption)
            (caption_regions if is_caption else regions).append(entry)
        if (year,number)==(2022,1):
            # Fig. 2a's caption shares a physical row with the body at left.
            # Its three prose slots and native 2a./b form one right-hand
            # caption, not three overlapping line rectangles.
            caption_regions=[r for r in caption_regions if abs(r['baseline']-526.51)>.03]
            picture_labels=[r for r in picture_labels if abs(r['baseline']-526.51)>.03]
            caption_regions.append(dict(rect=[400,517.534,562,529.89],baseline=526.51,
                placements=['1-25-6','1-25-7','1-25-8'],caption=True,alignment='center',
                center=(412.75+557.5038452148438)/2))
        return dict(year=year,language=language,page=number,input=str(input_path),input_page=input_page or number,input_sha256=sha(input_path),
                    original=str(source),original_sha256=sha(source),regions=regions,
                    caption_regions=caption_regions,picture_label_regions=picture_labels,centered_lines=centers,
                    excluded_figure_rects=excluded,prose_placements=journal)


def native_records(year,number,input_path,input_page):
    def key(g):return(g['c'],g['font'],g['trace_gid'],round(g['size'],5),round(g['origin'][0],4),round(g['origin'][1],4))
    with fitz.open(original(year)) as source,fitz.open(input_path) as current:
        counter=Counter(key(g) for g in _traces(source[number-1]));out=[]
        for g in _traces(current[input_page-1]):
            if counter[key(g)]:counter[key(g)]-=1;out.append(g)
        return out


def build(year,language,number):
    spec=prepare(year,language,number);folder=OUT/str(year)/language;folder.mkdir(parents=True,exist_ok=True)
    target=folder/f'page{number:02}.pdf'
    if language=='en':
        from cpho_natural_english_fonts import prepare_english_faces
        newinput,newpage,newplacements,faceqa=prepare_english_faces(year,spec['input'],number,spec['prose_placements'],folder/'font-stage')
        spec=prepare(year,language,number,newinput,newpage,newplacements);spec['english_face_stage']=faceqa
    if language=='ko':
        from cpho_natural_prose_edits import prepare_korean_prose
        newinput,newpage,newplacements,proseqa=prepare_korean_prose(year,spec['input'],number,spec['prose_placements'],folder/'prose-stage')
        if proseqa:
            spec=prepare(year,language,number,newinput,newpage,newplacements);spec['reviewed_Korean_prose_stage']=proseqa
    target.with_suffix('.plan.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),'utf8')
    kwargs={}
    from cpho_natural_atoms import explicit_atoms
    atoms=explicit_atoms(spec)
    if atoms:kwargs['native_atomic_tokens']=atoms
    if language=='en':
        original_keys={glyph_key(g) for g in native_records(year,number,spec['input'],spec['input_page'])}
        kwargs['prose_trace_predicate']=lambda rows:any(r['c'].strip() and glyph_key(r) not in original_keys for r in rows)
    import pdf_korean_natural_composer as composer
    saved_inject=composer.inject_atomic_tokens
    if (year,language,number)==(2007,'ko',1):
        def korean_first_clause(lines,atoms):
            lines=saved_inject(lines,atoms)
            from izho_natural_spacing import token
            for line in lines:
                if abs(line['baseline']-196.80188)>.03:continue
                items=line['tokens'];prose=next((t for t in items if t['kind']=='korean' and '작은 세 강체구가' in t['text']),None)
                if prose is None:raise ValueError('Reviewed Korean first-clause wording changed')
                native=[t for t in items if t['kind']=='native']
                if len(native)!=1:raise ValueError('Reviewed A/B/C native list is not one complete token')
                split=prose['text'].index('가 매끈한')
                a=token(prose['glyphs'][:split],'korean');b=token(prose['glyphs'][split:],'korean')
                if 'placement' in prose:a['placement']=b['placement']=prose['placement']
                a['x0']=min(t['x0'] for t in items)
                line['tokens']=[a,native[0],b]
            return lines
        composer.inject_atomic_tokens=korean_first_clause
    try:
        raw,qa=compose_page(spec['input'],spec['input_page'],allowed_line_rects=[r['rect'] for r in spec['regions']],
                           prose_placements=spec['prose_placements'],excluded_figure_rects=spec['excluded_figure_rects'],
                           centered_lines=spec['centered_lines'],**kwargs)
    finally:composer.inject_atomic_tokens=saved_inject
    if (year,language,number)==(2007,'ko',1):qa['semantic_order']='작은 세 강체구 A,B,C가 …; same original characters, only horizontal native/prose order changed.'
    # Strict 2007 English figure prose already uses the documented quarter-em
    # SimSun word space. Keep its label anchors/paint order exactly unchanged.
    label_regions=([] if year==2007 and language=='en' else spec['picture_label_regions'])+spec['caption_regions']
    if label_regions:
        body_path=folder/f'page{number:02}-before-labels.pdf';body_path.write_bytes(raw)
        centers=[dict(baseline=r['baseline'],center=r['center'],rect=r['rect']) for r in label_regions if r['alignment']=='center']
        rights=[]
        from izho_natural_spacing import records,visible
        with fitz.open(body_path) as body:
            rows=visible(records(body[0]))
            for r in label_regions:
                if r['alignment']!='right':continue
                matched=[g for g in rows if abs(g['origin'][1]-r['baseline'])<2 and fitz.Rect(r['rect']).contains(fitz.Point(g['origin']))]
                rights.append(dict(baseline=r['baseline'],right=r.get('right') or max(g['bbox'][2] for g in matched),rect=r['rect']))
        label_kwargs={}
        if language=='en':
            sourcekeys={glyph_key(g) for g in native_records(year,number,body_path,1)}
            label_kwargs['prose_trace_predicate']=lambda rows:any(r['c'].strip() and glyph_key(r) not in sourcekeys for r in rows)
        raw,labelqa=compose_page(body_path,1,allowed_line_rects=[r['rect'] for r in label_regions],
            prose_placements=spec['prose_placements'],excluded_figure_rects=[],centered_lines=centers,right_aligned_lines=rights,
            font_resource_name=f'KO_Natural_BatangLabels{number}',**label_kwargs)
        qa['picture_language_and_caption_stage']=labelqa
        qa['native_shifts']+=labelqa['native_shifts'];qa['erased_hangul_glyphs']+=labelqa['erased_hangul_glyphs']
        qa['replaced_hangul_glyphs']+=labelqa['replaced_hangul_glyphs']
        qa['new_batang_placements']+=labelqa['new_batang_placements']
        qa['new_batang_runs']+=labelqa['new_batang_runs']
        qa['lines']+=labelqa['lines'];qa['output_sha256']=labelqa['output_sha256']
    target.write_bytes(raw)
    qa.update(input_sha256=spec['input_sha256'],original_sha256=spec['original_sha256'],
              prototype=True,caption_regions_pending=[],picture_and_caption_regions_processed=label_regions)
    with fitz.open(stream=raw,filetype='pdf') as doc:
        doc[0].get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False).save(target.with_suffix('.png'))
    target.with_suffix('.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(dict(output=str(target),sha256=sha(target),lines=len(qa['lines']),
                          replaced_hangul_glyphs=qa['replaced_hangul_glyphs'],native_qa=qa['native_move_qa']),ensure_ascii=False))
    return target


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int,choices=[2006,2007,2022])
    p.add_argument('language',choices=['ko','en']);p.add_argument('page',type=int);p.add_argument('--plan-only',action='store_true');a=p.parse_args()
    if a.plan_only:print(json.dumps(prepare(a.year,a.language,a.page),ensure_ascii=False,indent=2))
    else:
        from pdf_memory_gate import page_worker
        with page_worker():build(a.year,a.language,a.page)
