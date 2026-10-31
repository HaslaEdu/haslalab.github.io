"""Small reviewed Korean grammar corrections before same-size line packing."""
from pathlib import Path
import json,re
import pymupdf as fitz
from pdf_native_inline_reposition import reposition_inline
from pdf_original_style_fonts import subset_font
from izho_natural_spacing import records,visible
from cpho_natural_spacing import ROOT,native_records
from pdf_original_text_ops import glyph_key

EDITS={(2007,1):{
    '1-5-1':('이며, 비신축 줄의 길이는','이며, 비신축 줄(길이'),
    '1-6-0':('그림처럼 잇고',')로 연결된다.'),
},(2022,1):{
    '1-6-0':('가는 막대를 움직이면 충분한 시간 뒤 평형 위치에 멈춘다. 이때 막대와 수평 방향의',
        '가는 막대를 움직인 뒤 충분히 오래 두면 평형에 멈춘다. 이때 막대와 수평선의'),
},(2022,2):{
    '2-12-0':('과 코리올리 힘을 ‘느낀다’. 원환을 미소요소의 집합으로 보고 모든 요소가 받는 원심력의 합력',
        '과 코리올리 힘을 받는다. 원환을 미소요소로 나누어 각 요소가 받는 원심력의 합력'),
},(2022,4):{
    '4-0-0':('이때','여기서'),
}}
EN_EDITS={(2006,1):{'1-20-0':('Ans:','A:')},(2022,1):{
    '1-4-2':('of this thin uniform rod have small round holes for wire; smooth fit.',
        'each have one small round hole on the wire; very smooth contact.'),
},(2022,2):{
    '2-19-0':('4.(60pts) A free-electron laser uses free relativistic electrons to turn beam K.E. into coherent radiation.',
        '4. (60 pts) A free-electron laser converts free relativistic electron-beam K.E. to coherent radiation.'),
},(2022,3):{
    '3-11-0':('5. (50 pts) Uniaxial crystal optics is anisotropic. Polarizations:',
        '5. (50 pts) Uniaxial crystal optics is anisotropic. Polarization:'),
    '3-31-1':('A key crystal use: frequency conversion. Doubling turns two equal-frequency fundamental photons into a',
        'A key use: frequency conversion. Doubling turns two equal-frequency fundamental photons into a'),
    '3-32-1':('gives photon momentum','sets photon momentum'),
},(2022,4):{
    '4-17-8':('2nd derivative; etc.','2nd deriv.; etc.'),
}}


def prepare_korean_prose(year,source,page_number,placements,folder,language='ko',input_page=None):
    input_page=input_page or page_number
    edits=EDITS.get((year,page_number),{})if language=='ko'else EN_EDITS.get((year,page_number),{})
    if not edits:return Path(source),input_page,placements,None
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    with fitz.open(source)as doc:
        rows=visible(records(doc[input_page-1]))
    physical={glyph_key(g)for g in native_records(year,page_number,source,input_page)}
    erase=[];inserts=[];updated={};journal=[]
    if language=='en':
        from cpho_original_latin_fonts import simsun
        font=simsun()
    else:font=ROOT/'tools/ko/fonts/NotoSerifCJKkr-Regular.otf'
    donor=subset_font(font,''.join(v[1]for v in edits.values()),folder/'fonts')
    metric=fitz.Font(fontfile=str(donor))
    for p in placements:
        if p['id']not in edits:continue
        before,text=edits[p['id']]
        if p['text']!=before:raise ValueError('Reviewed Korean wording changed')
        x,y=p['point'];size=p['size'];expected=''.join(c for c in before if not c.isspace())
        candidates=sorted([g for g in rows if abs(g['origin'][1]-y)<.02 and x-.03<=g['origin'][0]<x+p['width']+.03],key=lambda g:g['origin'][0])
        if ''.join(g['c']for g in candidates)!=expected:raise ValueError('Korean prose edit CID association mismatch')
        if any(glyph_key(g)in physical for g in candidates):raise ValueError('A prose edit selected original physical mathematics')
        erase.extend({k:g[k]for k in('c','font','size','origin')}for g in candidates)
        cursor=x;color=candidates[0]['color']
        for word in re.split('( )',text):
            if word==' ':cursor+=size/4
            elif word:
                inserts.append(dict(text=word,point=[cursor,y],size=size,color=color))
                cursor+=metric.text_length(word,fontsize=size)
        updated[p['id']]=dict(p,text=text,width=cursor-x)
        journal.append(dict(id=p['id'],before=before,after=text,point_size=size,baseline=y,
            reason=('Complete Korean syntax around the unchanged native rope-length l; light/flexible properties and figure reference remain in the following original prose slot.'if year==2007 else'Complete Korean wording retaining every physical condition and quantity, including sufficient settling time or all microelement force contributions; original column geometry and point size are retained.')if language=='ko'else('Answer label uses A: to fit the original printed-answer-blank cell, retaining actual SimSun face/size and the unchanged blank geometry.'if year==2006 else'Faithful concise English within the original prose column; physical conditions, categories, quantities and meaning are retained at the same point size and baseline.')))
    raw,qa=reposition_inline(source,input_page,erased_glyphs=erase)
    out=fitz.open(stream=raw,filetype='pdf');page=out[0]
    for item in inserts:
        color=item['color'];color=tuple(color)*3 if len(color)==1 else color
        page.insert_text(item['point'],item['text'],fontsize=item['size'],fontfile=str(donor),fontname='ReviewedKoreanProse',color=color)
    path=folder/f'page{page_number:02}-reviewed-Korean.pdf';out.save(path,garbage=0,deflate=False);out.close()
    report=dict(source=str(source),source_page=page_number,edits=journal,erasure_qa=qa,
        physical_native_glyphs_selected=0,no_point_size_or_baseline_change=True)
    path.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    return path,1,[updated.get(p['id'],p)for p in placements],report
