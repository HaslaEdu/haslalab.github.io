"""Pack translated CPhO2023 lines at original size with native mathematics.

Inputs are the reviewed original-layout proofs, not the superseded reflowed
translation. Page coordinates below derive from the original prose baselines
and the separately reviewed original figure inventory.
"""
from pathlib import Path
import argparse,json,hashlib,copy,re
import pymupdf as fitz
import pdf_korean_natural_composer as composer
from pdf_memory_gate import page_worker

ROOT=Path(__file__).resolve().parents[1]
BUILD=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2023')
BASE=BUILD/'immutable-slot-baselines'
OUT=BUILD/'natural-layout'/'pages'
SLOTS=ROOT/'tmp/original-style-repair/2023/slots.json'
FIGURES=ROOT/'tools/ko/cpho/2023/original-labels/source-survey.json'

def plan(number):
    page=json.loads(SLOTS.read_text('utf8'))['pages'][number-1]
    figures=[r['rect']for r in json.loads(FIGURES.read_text('utf8'))['figures']if r['page']==number]
    layout_figures=copy.deepcopy(figures)
    for label in page['slots']:
        if label['source'].strip()!='图':continue
        x,y=label['origin']
        if any(fig[0]<=x<=fig[2]and 0<y-fig[3]<20 for fig in figures):
            layout_figures.append([x-.5,y-label['size']*.9,label['rect'][2]+35,y+label['size']*.4])
    grouped={}
    for slot in page['slots']:
        key=slot['id']if 'caption'in slot['id']else slot['id'].rsplit('-',1)[0]
        grouped.setdefault(key,[]).append(slot)
    rects=[];rect_baselines=[];centers=[];witnesses=[]
    original=fitz.open(ROOT/'tmp/source-audit/CPhO_2023_T_ZH.pdf')
    for key,slots in grouped.items():
        y=slots[0]['origin'][1];size=max(s['size']for s in slots)
        left=min(89.,min(s['origin'][0]for s in slots)-.3);right=505.9
        if len(slots)==1 and slots[0]['source'].strip()=='图':
            left=slots[0]['origin'][0]-.5;right=slots[0]['rect'][2]+35
        elif 'caption'in key:
            left=min(s['origin'][0]for s in slots)-8
            right=max(s['rect'][2]for s in slots)+8
            centers.append(dict(baseline=y,center=(min(s['rect'][0]for s in slots)+max(s['rect'][2]for s in slots))/2))
        elif number==1 and y<130:
            left=35.;right=560.;centers.append(dict(baseline=y,center=page['page_rect'][2]/2))
        else:
            for fig in layout_figures:
                if y+.32*size>fig[1]and y-.9*size<fig[3]:
                    if all(fig[0]-.1<=s['origin'][0]<=fig[2]+.1 for s in slots):
                        left=min(s['origin'][0]for s in slots)-.3
                    if fig[0]>min(s['origin'][0]for s in slots):
                        # Image bboxes include blank paper. Measure that paper
                        # before permitting a line to use its first few points;
                        # no figure ink or original image is moved or erased.
                        import numpy as np
                        sample=fitz.Rect(fig[0],max(fig[1],y-size),min(fig[2],fig[0]+14),min(fig[3],y+.4*size))
                        pix=original[number-1].get_pixmap(matrix=fitz.Matrix(4,4),clip=sample,colorspace=fitz.csGRAY)
                        a=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)
                        columns=np.flatnonzero((a<220).any(axis=0))
                        first=(pix.x+int(columns[0]))/4 if len(columns)else sample.x1
                        edge=min(fig[0]+12,first-1)
                        right=min(right,max(fig[0]-.6,edge))
                        witnesses.append(dict(baseline=y,figure=fig,sample_rect=list(sample),first_native_ink_x=first,right=right))
        rect=[left,y-.72*size,right,y+.32*size]
        for center in centers:
            if 'rect'not in center:center['rect']=rect
        previous=next((old for old,base in zip(rects,rect_baselines)
                       if abs(base-y)<.12 and max(old[0],rect[0])<min(old[2],rect[2])),None)
        if previous is not None:
            previous[:]=[min(previous[0],rect[0]),min(previous[1],rect[1]),max(previous[2],rect[2]),max(previous[3],rect[3])]
            for center in centers:
                if center['rect']is rect:center['rect']=previous
        else:rects.append(rect);rect_baselines.append(y)
    original.close()
    return dict(page=number,allowed_line_rects=rects,centered_lines=centers,excluded_figure_rects=figures,figure_white_margin_witnesses=witnesses)

def build(number,language='ko'):
    OUT.mkdir(parents=True,exist_ok=True)
    source=BASE/f'CPhO_2023_p{number}_{language.upper()}_proof.pdf'
    qa_path=ROOT/f'tmp/original-style-repair/2023/CPhO_2023_p{number}_{language.upper()}_proof.qa.json'
    if language=='en':
        source=BUILD/f'strict-en/proofs/CPhO_2023_p{number}_EN_proof.pdf'
        qa_path=source.with_suffix('.qa.json')
    qa=json.loads(qa_path.read_text('utf8'))
    prose_edits=[]
    english_edits={
        5:('5-0-4','of a uniform rigid rod.Its','; uniform thin rigid rod.','的匀质刚性细杆'),
        27:('27-13-0','flow makes current. Steady-state current density is','flow creates current. Steady current density is','将会运动形成电流。若稳定后金属内的电流密度表示为')}
    if language=='en'and number in english_edits:
        # Rephrase only authored prose; the original Chinese mathematical
        # objects keep their encoded glyphs and complete geometry.
        from pdf_original_text_ops import suppress_prose
        from izho_natural_spacing import records,visible
        from pdf_original_style_fonts import subset_font
        edit_id,expected,after,original_prose=english_edits[number]
        p=next(p for p in qa['placements']if p['id']==edit_id)
        before=p['text'];assert before==expected
        x,y=p['origin'];size=p['size']
        with fitz.open(source)as d:
            candidates=sorted([g for g in visible(records(d[0]))if abs(g['origin'][1]-y)<.02 and g['origin'][0]>=x-.03],key=lambda g:g['origin'][0])
        selected=candidates[:len(composer._plain(before))]
        assert ''.join(g['c']for g in selected)==composer._plain(before)
        raw,_=suppress_prose(source,1,selected)
        d=fitz.open(stream=raw,filetype='pdf')
        face=subset_font(Path(p['fonts'][0]),after,BUILD/'natural-layout/reviewed-en-fonts')
        metric=fitz.Font(fontfile=str(face));cursor=x
        width=sum(metric.text_length(word,fontsize=size)for word in after.split())+after.count(' ')*size/4
        limits=[r for r in plan(number)['allowed_line_rects']if r[0]-.02<=x<=r[2]+.02 and r[1]<=y<=r[3]]
        assert len(limits)==1 and x+width<=limits[0][2]+.02,('Edited prose must fit the reviewed original column before packing',edit_id,x+width,limits)
        for fragment in re.split('( +)',after):
            if not fragment:continue
            if fragment.isspace():cursor+=len(fragment)*size/4;continue
            d[0].insert_text((cursor,y),fragment,fontfile=str(face),fontname='ReviewedEnglishProse',fontsize=size,color=(0,0,0),
                             render_mode=p['render_mode'],border_width=p['border_width']/size,miter_limit=10)
            cursor+=metric.text_length(fragment,fontsize=size)
        source=BUILD/f'natural-layout/CPhO_2023_p{number}_EN_reviewed_prose.pdf'
        d.save(source,garbage=0,deflate=False);d.close()
        p['text']=after
        prose_edits.append(dict(id=p['id'],before=before,after=after,source=original_prose,point_size=size,baseline=y))
    if number==1:
        from cpho_2023_natural_heading import apply
        source=apply(source,language,BUILD/f'natural-layout/CPhO_2023_p1_{language.upper()}_heading_proof.pdf')
        # The title is now one complete centred run, so its old split-slot
        # journals must not claim the newly positioned characters.
        qa['placements']=[p for p in qa['placements']if not p['id'].startswith('1-0-')]
    profile=plan(number)
    right_aligned=[]
    if language=='en'and number==9:
        right_aligned.append(dict(baseline=236.65997314453125,right=505.9))
    prose_predicate=None
    if language=='en':
        from izho_natural_spacing import records,visible
        from pdf_original_text_ops import glyph_key
        keys=set()
        with fitz.open(source)as d:
            rows=visible(records(d[0]))
            placements=composer.normalize_placements(d[0],qa['placements'])
            for p in placements:
                if not p.get('point'):continue
                x,y=p['point'];expected=composer._plain(p['text'])
                candidates=sorted([g for g in rows if abs(g['origin'][1]-y)<.02 and g['origin'][0]>=x-.03],key=lambda g:g['origin'][0])
                selected=candidates[:len(expected)]
                if ''.join(g['c']for g in selected)!=expected:
                    raise ValueError(('English prose journal does not match exact input glyph sequence',p['id'],expected,''.join(g['c']for g in selected)))
                keys.update(glyph_key(g)for g in selected)
            if number==1:keys.update(glyph_key(g)for g in rows if abs(g['origin'][1]-88.0999755859375)<.02)
        def prose_predicate(rs):
            ink=[g for g in rs if g['c'].strip()]
            return bool(ink)and all(glyph_key(g)in keys for g in ink)
    stationary=[]
    from pdf_native_inline_reposition import inspect_inline_groups
    from pdf_original_text_ops import glyph_key
    form_inventory=inspect_inline_groups(source,1)['forms']
    reviewed_native_atoms=[]
    native_plan=json.loads((ROOT/'tools/ko/cpho/2023/natural-inline-groups.json').read_text('utf8')).get(str(number),[])
    for item in native_plan:
        assert item['reviewed']
        form=next(f for f in form_inventory if f['path']==item['form_path'])
        glyphs=[dict(g,gid=g.get('trace_gid',-1))for g in form['glyphs']]
        assert ''.join(g['c']for g in glyphs if g['c'].strip())==item['expected_text']
        assert max(abs(x-y)for x,y in zip(form['native_page_bbox'],item['bbox']))<.001
        box=fitz.Rect(form['native_page_bbox'])
        for g in glyphs:
            if g['c'].strip():box|=fitz.Rect(g['bbox'])
        reviewed_native_atoms.append(dict(kind='native',text=item['expected_text']or'\ufffc',glyphs=glyphs,
            x0=box.x0,x1=box.x1,y=item['baseline'],size=10.5600004196167,fonts=sorted({g['font']for g in glyphs}),
            bbox=list(box),shift_kwargs=dict(form_path=form['path']),atomic_native_group='reviewed complete original Form'))
    labels=json.loads((ROOT/'tools/ko/cpho/2023/original-labels/label-plan.json').read_text('utf8'))['labels']
    translated_language={glyph_key(g)for label in labels if label['page']==number and label['kind']=='native-form-language'for g in label['source_glyphs']}
    explicit=[1478]if number==6 else[1091]if number==7 else None
    for form in form_inventory:
        contains_original_language=any(glyph_key(g)in translated_language for g in form['glyphs'])
        if form['path']!=explicit and not contains_original_language:continue
        box=fitz.Rect()
        for g in form['glyphs']:box|=fitz.Rect(g['bbox'])
        if contains_original_language and box.height>100:continue
        profile['excluded_figure_rects'].append(list(box))
        stationary.append(dict(form_path=form['path'],bbox=list(box),reason='Original display equation with a condition or translated language overlay; preserve the complete equation and overlay at their original positions.'))
    original_units=composer._units
    original_boundary=composer.boundary_gap
    original_move=composer.reposition_inline
    import izho_native_atomic_tokens as atomic_module
    original_atomic=atomic_module.atomic_tokens
    corrections=[]
    def corrected_units(item,placements,metric):
        placement=placements[item['placement']]if 'placement'in item else{}
        if language=='ko'and placement.get('id')=='5-0-4':
            rows=sorted(composer.visible(item['glyphs']),key=lambda r:r['origin'][0])
            if ''.join(r['c']for r in rows)!='인균일한강체막대는':raise ValueError('Unexpected rod-condition source translation')
            text='인 균일하고 가는 강체 막대는'
            corrections.append(dict(id='5-0-4',before=placement['text'],after=text,source='的匀质刚性细杆'))
            return[dict(kind='batang',text=text,glyphs=rows,old_x=item['x0'],
                         width=sum(metric.text_length(word,fontsize=rows[0]['size'])for word in text.split())+text.count(' ')*rows[0]['size']/4,style=composer._style(rows[0],placement))]
        units=original_units(item,placements,metric)
        if language=='ko'and placement.get('id')=='2-9-1':
            for index,unit in enumerate(units):
                if unit.get('kind')=='batang'and unit.get('text')=='바로':
                    unit['text']='';unit['width']=0
                    if index+1<len(units)and units[index+1]['kind']=='space':units[index+1]['width']=0
                    corrections.append(dict(id='2-9-1',before='가장자리 바로 옆에',after='가장자리 옆에',source='虹的边缘紧邻...'))
        if language=='ko'and placement.get('id')=='19-10-1':
            for unit in units:
                if unit.get('kind')=='batang'and unit.get('text')=='나머지':
                    unit['text']='다른';unit['width']=metric.text_length('다른',fontsize=unit['style']['size'])
                    corrections.append(dict(id='19-10-1',before='나머지',after='다른',source='按照爱因斯坦的假设，其...'))
        return units
    composer._units=corrected_units
    def reference_gap(left,right,*args,**kwargs):
        if (left['kind']=='korean'and right['kind']=='native'
            and re.search(r'(?:^|[\s(（])(?:도|그림|표|식)$',left['text'].rstrip())
            and re.match(r'[0-9①-⑳]',right['text'].lstrip())):return 0
        return original_boundary(left,right,*args,**kwargs)
    composer.boundary_gap=reference_gap
    def grouped_move(source,page_number,**kwargs):
        from natural_spacing_form_groups import atomic_shifts
        try:kwargs['shifts']=atomic_shifts(source,page_number,kwargs.get('shifts',[]))
        except ValueError:
            (OUT/f'page{number:02}-{language}-pending-shifts.json').write_text(json.dumps(dict(source=str(source),**kwargs),ensure_ascii=False,indent=2),'utf8')
            raise
        return original_move(source,page_number,**kwargs)
    composer.reposition_inline=grouped_move
    def complete_fraction_atoms(source,page_number,rect,baselines,excluded=None):
        from pdf_original_text_ops import glyph_key
        from izho_natural_spacing import baseline_lines,visible
        from pdf_native_inline_reposition import inspect_inline_groups
        atoms=original_atomic(source,page_number,rect,baselines,excluded)
        claimed={glyph_key(g)for a in atoms for g in a['glyphs']}
        with fitz.open(source)as d:
            lines=baseline_lines(d[page_number-1],allowed_line_rects=[rect],excluded_figure_rects=excluded,prose_trace_predicate=prose_predicate)
        selected={glyph_key(g):line['baseline']for line in lines for token in line['tokens']if token['kind']=='native'for g in token['glyphs']}
        inventory=inspect_inline_groups(source,page_number)
        for form in sorted(inventory['forms'],key=lambda f:-len(f['glyphs'])):
            keys={glyph_key(g)for g in form['glyphs']}
            overlap=keys&selected.keys()
            if not overlap or keys&claimed:continue
            rows=[dict(g,gid=g.get('trace_gid',-1))for g in form['glyphs']]
            ink=visible(rows);bounds=fitz.Rect()
            for g in ink:bounds|=fitz.Rect(g['bbox'])
            if form.get('native_page_bbox'):bounds|=fitz.Rect(form['native_page_bbox'])
            if not ink or bounds.height>45 or bounds.x0<rect[0]or bounds.x1>rect[2]:continue
            if any(bounds.intersects(fitz.Rect(r))for r in excluded or[]):continue
            ys={selected[k]for k in overlap}
            if len(ys)!=1:raise ValueError('Native expression crosses two prose baselines')
            y=ys.pop();size=max(b['size']for b in baselines if abs(b['baseline']-y)<.12)
            atoms.append(dict(text=''.join(g['c']for g in sorted(ink,key=lambda g:(g['origin'][0],g['origin'][1]))),kind='native',glyphs=rows,
                x0=bounds.x0,x1=bounds.x1,y=y,size=size,fonts=sorted({g['font']for g in ink}),
                shift_kwargs=dict(form_path=form['path']),atomic_native_group='form',bbox=list(bounds)))
            claimed.update(keys)
        return atoms
    atomic_module.atomic_tokens=complete_fraction_atoms
    try:
        with fitz.open(source)as doc:
            panels=[list(p['rect'])for p in doc[0].get_drawings()
                    if p.get('fill')==(1.,1.,1.)and p.get('color')is None
                    and p.get('fill_opacity',1)==1 and len(p['items'])==1 and p['items'][0][0]=='re']
        for attempt in range(20):
            corrections.clear()
            try:
                raw,report=composer.compose_page(source,1,allowed_line_rects=profile['allowed_line_rects'],
                    prose_placements=qa['placements'],excluded_figure_rects=profile['excluded_figure_rects'],
                    centered_lines=profile['centered_lines'],right_aligned_lines=right_aligned,prose_trace_predicate=prose_predicate,
                    native_atomic_tokens=reviewed_native_atoms,native_move_options={'reviewed_white_panel_rects':panels})
                break
            except ValueError as error:
                detail=error.args[0]
                if not(isinstance(detail,tuple)and detail[0]=='Natural fixed-size line overflows reviewed rectangle'):raise
                _,baseline,left,right,rect=detail;excess=right-rect[2]
                if excess<=0 or left-excess<rect[0]or any(abs(v['baseline']-baseline)<.02 for v in profile['centered_lines']+right_aligned):raise
                # A display expression followed by prose may have spare space
                # before its source indent. Move the whole line together;
                # never shrink fonts or compress native mathematical advances.
                right_aligned.append(dict(baseline=baseline,right=rect[2],rect=rect,reason='Use the existing leading indentation to fit the complete native formula and translation at original sizes.'))
        else:raise ValueError('Too many unresolved source line alignments')
    finally:
        composer._units=original_units
        composer.boundary_gap=original_boundary
        composer.reposition_inline=original_move
        atomic_module.atomic_tokens=original_atomic
    target=OUT/f'CPhO_2023_p{number}_{language.upper()}_natural.pdf'
    target.write_bytes(raw)
    report.update(document='CPhO2023 combined',document_page=number,language=language,reviewed_line_profile=profile,
                  semantic_condition_corrections=corrections,reviewed_english_prose_edits=prose_edits,reviewed_inline_native_groups=native_plan,
                  stationary_display_equations=stationary,right_aligned_lines=right_aligned,ready=False)
    target.with_suffix('.qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return target,report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--page',type=int,required=True);p.add_argument('--language',choices=['ko','en'],default='ko')
    a=p.parse_args()
    with page_worker():
        path,qa=build(a.page,a.language)
        print(json.dumps(dict(output=str(path),sha256=qa['output_sha256'],hangul=qa['replaced_hangul_glyphs'],lines=len(qa['lines'])),ensure_ascii=False),flush=True)
