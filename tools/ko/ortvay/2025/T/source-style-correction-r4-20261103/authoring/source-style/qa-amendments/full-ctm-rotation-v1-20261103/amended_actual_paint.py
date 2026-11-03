"""Replay actual KO paint streams with actual resources, /W, Tm and TJ."""
from pathlib import Path
from collections import defaultdict
import hashlib,math,re
from io import BytesIO
import numpy as np
import pymupdf as f
import pikepdf

NUM=rb'[-+]?(?:\d+(?:\.\d*)?|\.\d+)'
SIX=rb'('+NUM+rb')\s+('+NUM+rb')\s+('+NUM+rb')\s+('+NUM+rb')\s+('+NUM+rb')\s+('+NUM+rb')'

def normalize_face(name):
    value=re.sub('[^a-z0-9]','',name.lower())
    return 'batang' if value=='batangregular' else value
def is_new_font(name):return name.startswith(('NotoSerifCJK','NotoSansCJK','Batang'))
def glyphs(page,new_only=None,include_spaces=False):
    result=[]
    for t in page.get_texttrace():
        if t['type']==3:continue
        if new_only is not None and is_new_font(t['font'])!=new_only:continue
        for cp,gid,origin,bbox in t['chars']:
            if not include_spaces and chr(cp).isspace():continue
            result.append(dict(cp=cp,gid=gid,font=t['font'],size=t['size'],origin=tuple(origin),bbox=tuple(bbox),
                               color=tuple(t['color']) if isinstance(t['color'],(list,tuple)) else t['color'],paint=t['type'],dir=tuple(t['dir']),opacity=t['opacity']))
    return result
def canonical_glyphs(values,with_bbox=True):
    keys=['cp','gid','font','size','origin','color','paint','dir','opacity']+(['bbox'] if with_bbox else [])
    return sorted(tuple(tuple(v[k]) if isinstance(v[k],list) else v[k] for k in keys) for v in values)

def _entry_states(page):
    """Fail-closed entry check for this producer's self-contained KO paints.

    Contents arrays share graphics state. Track only the inherited values that
    must remain canonical for the current producer; unsupported persistent
    styles are rejected, not simulated or silently dropped from replay.
    """
    state=dict(ctm=f.Matrix(1,0,0,1,0,0),fill_alpha=1.,stroke_alpha=1.,unsafe_styles={},clip=False,
               text={'Tc':0.,'Tw':0.,'Ts':0.,'Tz':100.,'Tr':0.})
    def clone(s):return dict(s,ctm=f.Matrix(s['ctm']),text=dict(s['text']),unsafe_styles=dict(s['unsafe_styles']))
    stack=[];entries=[]
    source=page.parent.name if page.parent.name else BytesIO(page.parent.tobytes())
    with pikepdf.Pdf.open(source) as pdf,pikepdf.Pdf.new() as holder:
        gs=pdf.pages[page.number].Resources.get('/ExtGState',{})
        for xref in page.get_contents():
            entry=clone(state);entry['ctm']=list(entry['ctm']);entries.append(entry)
            for operands,operator in pikepdf.parse_content_stream(pikepdf.Stream(holder,page.parent.xref_stream(xref))):
                op=str(operator)
                if op=='q':stack.append(clone(state))
                elif op=='Q':
                    assert stack,'Unbalanced page Contents graphics state';state=stack.pop()
                elif op=='cm':
                    assert len(operands)==6;state['ctm']=f.Matrix(*map(float,operands))*state['ctm']
                elif op=='gs':
                    assert len(operands)==1 and str(operands[0]) in gs
                    settings=gs[str(operands[0])]
                    for key,value in settings.items():
                        key=str(key)
                        if key=='/ca':state['fill_alpha']=float(value)
                        elif key=='/CA':state['stroke_alpha']=float(value)
                        elif key!='/Type':state['unsafe_styles'][key]=str(value)
                elif op in state['text']:
                    assert len(operands)==1;state['text'][op]=float(operands[0])
                elif op in ('W','W*'):state['clip']=True
        assert not stack,'Unclosed page Contents graphics state'
    return entries

def streams(page):
    """Parse graphics stack and text matrix at the actual single TJ paint.

    PDF cm concatenates the new matrix before the current CTM in MuPDF's
    row-vector representation. Text matrices are not part of q/Q graphics state.
    Original bytes are retained for complete-stream replay without re-embedding.
    """
    result=[];entries=_entry_states(page)
    with pikepdf.Pdf.new() as holder:
        for content_index,xref in enumerate(page.get_contents()):
            data=page.parent.xref_stream(xref)
            if not re.search(rb'/KO_Natural_[A-Za-z_]+',data):continue
            entry=entries[content_index]
            assert max(abs(a-b) for a,b in zip(entry['ctm'],[1,0,0,1,0,0]))<=1e-6,('Noncanonical inherited KO entry CTM',xref,entry)
            assert entry['fill_alpha']==entry['stroke_alpha']==1.,('Noncanonical inherited KO opacity',xref,entry)
            assert not entry['unsafe_styles'] and not entry['clip'],('Unplanned inherited KO graphics style or clip',xref,entry)
            assert entry['text']=={'Tc':0.,'Tw':0.,'Ts':0.,'Tz':100.,'Tr':0.},('Unplanned inherited KO text state',xref,entry)
            ctm=f.Matrix(1,0,0,1,0,0);tm=None;alias=None;size=None
            stack=[];paints=[];font_count=0;tm_count=0;in_text=False;operators=[]
            parsed=pikepdf.parse_content_stream(pikepdf.Stream(holder,data))
            for operands,operator in parsed:
                op=str(operator);operators.append(op)
                if op=='q':
                    assert not operands;stack.append((f.Matrix(ctm),alias,size))
                elif op=='Q':
                    assert not operands and stack,'Unbalanced source KO graphics stack'
                    ctm,alias,size=stack.pop()
                elif op=='cm':
                    assert len(operands)==6
                    ctm=f.Matrix(*map(float,operands))*ctm
                elif op=='BT':
                    assert not in_text and not operands;in_text=True;tm=f.Matrix(1,0,0,1,0,0)
                elif op=='ET':
                    assert in_text and not operands;in_text=False
                elif op=='Tm':
                    assert in_text and len(operands)==6;tm=f.Matrix(*map(float,operands));tm_count+=1
                elif op=='Tf':
                    assert in_text and len(operands)==2
                    alias=str(operands[0]).lstrip('/');size=float(operands[1]);font_count+=1
                    assert alias.startswith('KO_Natural_') and size>0
                elif op=='TJ':
                    assert in_text and len(operands)==1 and tm is not None and alias is not None
                    tokens=[]
                    for value in operands[0]:
                        if isinstance(value,pikepdf.String):tokens.append(bytes(value))
                        else:tokens.append(float(value))
                    paints.append((f.Matrix(tm),f.Matrix(ctm),alias,size,tokens))
                elif op in ('RG','rg'):
                    assert len(operands)==3
                elif op in ('Tc','Tw','Ts'):
                    assert len(operands)==1 and float(operands[0])==0,'Unplanned text spacing or rise'
                elif op=='Tz':
                    assert len(operands)==1 and float(operands[0])==100,'Unplanned text horizontal scale'
                elif op=='Tr':
                    assert len(operands)==1 and int(operands[0])==0,'Unplanned invisible/stroked text mode'
                else:raise AssertionError(('Unhandled KO actual paint operator',op,xref))
            assert not in_text and not stack,'Unclosed source KO text/graphics state'
            assert font_count==tm_count==len(paints)==1,('Unexpected non-self-contained KO paint stream',xref)
            tm,cm,alias,size,tokens=paints[0]
            effective=tm*cm;page_effective=effective*page.transformation_matrix
            anchor=f.Point(0,0)*page_effective
            length=math.hypot(page_effective.a,page_effective.b);assert length>0
            direction=[page_effective.a/length,page_effective.b/length]
            horizontal=abs(direction[1])<=1e-6 and abs(abs(direction[0])-1)<=1e-6
            result.append(dict(xref=xref,data=data,aliases=[alias],font_alias=alias,size=size,text_matrix=list(tm),
                cm=list(cm),composed_text_matrix_pdf=list(effective),composed_text_matrix_page=list(page_effective),
                actual_baseline=float(anchor.y),actual_first_origin=list(anchor),horizontal=horizontal,
                actual_baseline_direction=direction,parsed_operator_sequence=operators,tj_tokens=tokens,
                canonical_entry_graphics_state=entry,actual_fill_opacity=1.,actual_stroke_opacity=1.,
                raw_sha256=hashlib.sha256(data).hexdigest()))
    return result

def clone_with_streams(target,selected,output=None):
    doc=f.open(target);pg=doc[0];xref=doc.get_new_xref();doc.update_object(xref,'<<>>')
    doc.update_stream(xref,b'\n'.join(v['data'] for v in selected));pg.set_contents(xref)
    if output:doc.save(output,garbage=0,deflate=False)
    return doc

def assert_same_glyphs(expected,actual,tolerance=.001):
    group=defaultdict(list)
    for v in actual:group[(v['cp'],v['gid'],normalize_face(v['font']),round(v['size'],4),v['color'],v['paint'])].append(v)
    maximum=0.0
    for v in expected:
        key=(v['cp'],v['gid'],normalize_face(v['font']),round(v['size'],4),v['color'],v['paint']);candidates=group[key]
        assert candidates,('Missing glyph in actual-stream replay',key,v)
        j=min(range(len(candidates)),key=lambda j:max(abs(a-b) for a,b in zip(v['origin'],candidates[j]['origin'])))
        got=candidates.pop(j);delta=max(abs(a-b) for a,b in zip(v['origin'],got['origin']));maximum=max(maximum,delta)
        assert delta<=tolerance,('Actual stream origin differs from target',v,got)
        assert v['opacity']==got['opacity']==1.,('Actual/replayed KO opacity differs from approved opaque paint',v,got)
        assert max(abs(a-b) for a,b in zip(v['bbox'],got['bbox']))<=tolerance
    assert not any(group.values()),'Extra glyph in actual-stream replay'
    return maximum

def actual_row_ink(target,layout,special_pairs=()):
    target=Path(target)
    with f.open(target) as source:
        page=source[0];records=streams(page);full_new=glyphs(page,True)
        horizontal=[v for v in records if v['horizontal']]
        orthogonal=[v for v in records if not v['horizontal']]
        # Prove no KO glyph disappeared because it was inside an unhandled Form.
        with clone_with_streams(target,records) as all_new:
            assert_same_glyphs(full_new,glyphs(all_new[0],True))
        grouped=[]
        for record in sorted(horizontal,key=lambda v:v['actual_baseline']):
            if not grouped or abs(grouped[-1][0]['actual_baseline']-record['actual_baseline'])>.001:grouped.append([])
            grouped[-1].append(record)
        rows=[]
        for values in grouped:
            y=values[0]['actual_baseline'];expected=[v for v in full_new if abs(v['origin'][1]-y)<.001 and abs(v['dir'][1])<.00001]
            with clone_with_streams(target,values) as rowdoc:
                actual=glyphs(rowdoc[0],True)
                assert_same_glyphs(expected,actual)
            rows.append(dict(baseline=y,size=max(v['size'] for v in values),streams=values,glyphs=len(expected)))
        pairs=[];unions={}
        for i,up in enumerate(rows):
            for j in range(i+1,len(rows)):
                down=rows[j];gap=down['baseline']-up['baseline'];size=max(up['size'],down['size'])
                if gap>=size*1.1:continue
                clip=f.Rect(0,math.floor(up['baseline']-size*1.5),page.rect.width,math.ceil(down['baseline']+size*.5))
                pairs.append((i,j,gap,clip))
                for index in (i,j):unions[index]=unions[index]|clip if index in unions else f.Rect(clip)
        cache={};negative=0
        for index,clip in unions.items():
            with clone_with_streams(target,rows[index]['streams']) as rowdoc:
                pix=rowdoc[0].get_pixmap(matrix=f.Matrix(2,2),colorspace=f.csGRAY,alpha=False,clip=clip)
                pixels=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width).copy()
                cache[index]=(pixels,pix.x,pix.y)
                if not negative:negative=int((pixels<220).sum())
        results=[]
        for i,j,gap,clip in pairs:
            rect=((clip&page.rect)*f.Matrix(2,2)).irect
            def crop(index):
                array,x,y=cache[index]
                return array[rect.y0-y:rect.y1-y,rect.x0-x:rect.x1-x]
            a,b=crop(i),crop(j);assert a.shape==b.shape
            contact=int(((a<220)&(b<220)).sum())
            results.append(dict(upper_baseline=rows[i]['baseline'],lower_baseline=rows[j]['baseline'],gap_pt=gap,contact_pixels_2x=contact))
        if cache:assert negative>0
        multi=[]
        for upy,downy in special_pairs:
            upper=[v for v in records if v['horizontal'] and abs(v['actual_baseline']-upy)<.001]
            lower=[v for v in records if v['horizontal'] and abs(v['actual_baseline']-downy)<.001]
            assert upper and lower
            size=max(v['size'] for v in upper+lower);clip=f.Rect(0,math.floor(upy-size*1.5),page.rect.width,math.ceil(downy+size*.5));counts={}
            for scale in (2,4,8):
                arrays=[]
                for values in (upper,lower):
                    with clone_with_streams(target,values) as rd:
                        pix=rd[0].get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csGRAY,alpha=False,clip=clip)
                        arrays.append(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width).copy())
                counts[str(scale)]=int(((arrays[0]<220)&(arrays[1]<220)).sum())
            multi.append(dict(upper_baseline=upy,lower_baseline=downy,contact_pixels_by_scale=counts))
        failures=[v for v in results if v['contact_pixels_2x']]
        failures += [v for v in multi if any(v['contact_pixels_by_scale'].values())]
        return dict(passed=not failures,method='Actual target self-contained KO content streams with exact target font resources/W/Tm/TJ',
            rows=len(rows),stream_count=len(records),all_target_KO_glyphs_accounted_for=True,each_extracted_row_glyph_trace_matches_target=True,
            threshold=220,scale=2,same_row_tolerance_pt=.001,close_row_selection_em=1.1,tested_close_row_pairs=len(pairs),pairs=results,
            corrected_special_pair_multiscale=multi,failures=failures,negative_same_row_overlap_pixels=negative,
            orthogonal_streams_excluded_from_horizontal_pairs=[dict(xref=v['xref'],aliases=v['aliases'],tm=v['text_matrix']) for v in orthogonal])

def actual_native_contact(target):
    with f.open(target) as source:
        page=source[0];ko=streams(page);koids={v['xref'] for v in ko}
        rest=[dict(data=source.xref_stream(xref)) for xref in page.get_contents() if xref not in koids]
        with clone_with_streams(target,ko) as language,clone_with_streams(target,rest) as native:
            assert_same_glyphs(glyphs(page,True),glyphs(language[0],True))
            a=language[0].get_pixmap(matrix=f.Matrix(2,2),colorspace=f.csGRAY,alpha=False)
            b=native[0].get_pixmap(matrix=f.Matrix(2,2),colorspace=f.csGRAY,alpha=False)
            aa=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width)
            bb=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width)
            hits=(aa<220)&(bb<180)
            count=int(hits.sum())
            return dict(passed=count==0,actual_KO_vs_original_remaining_ink_contact_pixels_2x=count,
                method='Actual final target streams split into KO-language-only and retained source/vector/white-mask control; no font re-embedding',
                original_font_resources_preserved_in_both_controls=True)
