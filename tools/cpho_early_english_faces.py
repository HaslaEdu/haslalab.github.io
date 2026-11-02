"""Restore official original SimHei prose in early English theory titles.
Only translated prose is replaced. Restored source-TNR numerical title runs
are retained as original CID text and keep their original intra-run spacing.
"""
from pathlib import Path
import hashlib,json,re
import pymupdf as fitz
from izho_natural_spacing import records,visible
from pdf_native_inline_reposition import reposition_inline
from pdf_original_style_fonts import subset_font
from cpho_original_latin_fonts import verify_real_glyphs
SIMHEI=Path('D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts/faces/simhei.ttf')
SHA='aa4560dd8fe5645745fed3ffa301c3ca4d6c03cbd738145b613303961ba733b8'
def glyph(g):return{k:g[k]for k in('c','font','size','origin')}
def prepare_english_faces(year,source,page_number,placements,folder):
    selected=[p for p in placements if p.get('source_font')=='SimHei']
    if not selected:return Path(source),page_number,placements,None
    if hashlib.sha256(SIMHEI.read_bytes()).hexdigest()!=SHA:raise ValueError('Official source SimHei SHA mismatch')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    text=''.join(p['text']for p in selected);verify_real_glyphs(SIMHEI,text)
    donor=subset_font(SIMHEI,text,folder/'fonts');metric=fitz.Font(fontfile=str(donor))
    with fitz.open(source)as doc:page=doc[page_number-1];rows=visible(records(page))
    erase=[];shifts=[];insertions=[];updates={};reports=[]
    for p in selected:
        x,y=p['point'];size=p['size'];expected=''.join(p['text'].split())
        found=sorted([g for g in rows if abs(g['origin'][1]-y)<.02 and x-.03<=g['origin'][0]<x+p['width']+.03],key=lambda g:g['origin'][0])
        if ''.join(g['c']for g in found)!=expected:raise ValueError(('Exact SimHei placement association',p['id'],expected,''.join(g['c']for g in found)))
        numbers=[g for g in found if g['c'].isdigit()]if p.get('original_role')in('title','header','footer')else[]
        if any(g['font']!='TimesNewRomanPSMT'for g in numbers):raise ValueError('Title numerals were not restored from actual source TNR')
        erase.extend(glyph(g)for g in found if g not in numbers)
        cursor=x;ni=0;actions=[]
        for part in re.split(r'(\d+| +)',p['text']):
            if not part:continue
            if part.isspace():cursor+=len(part)*size/4;continue
            if part.isdigit()and numbers:
                group=numbers[ni:ni+len(part)];ni+=len(part)
                if ''.join(g['c']for g in group)!=part:raise ValueError('Title numerical event mismatch')
                width=max(g['bbox'][2]for g in group)-group[0]['origin'][0]
                dx=cursor-group[0]['origin'][0]
                if abs(dx)>1e-5:shifts.append(dict(glyphs=[glyph(g)for g in group],dx=dx))
                actions.append(dict(kind='source-numerals',text=part,size=size,dx=dx));cursor+=width
            else:
                insertions.append(dict(text=part,point=[cursor,y],size=size,style=found[0],border_width=p.get('border_width')))
                actions.append(dict(kind='source-face-prose',text=part));cursor+=metric.text_length(part,fontsize=size)
        updates[p['id']]=dict(p,width=cursor-x,font='SimHei',word_gap_adjustment=-size/4)
        reports.append(dict(id=p['id'],source_face='SimHei',actual_face_version='5.03',size=size,baseline=y,actions=actions))
    raw,qa=reposition_inline(source,page_number,erased_glyphs=erase,shifts=shifts)
    with fitz.open(stream=raw,filetype='pdf')as out:
        page=out[0]
        for e in insertions:
            st=e['style'];color=st['color'];color=tuple(color)*3 if len(color)==1 else color
            stroke=st.get('stroke_color')or color;stroke=tuple(stroke)*3 if len(stroke)==1 else stroke
            mode=st.get('paint',0);width=e['border_width']or st.get('linewidth')or 0
            if mode==2 and width<=0:raise ValueError('Original title stroke width missing')
            page.insert_text(e['point'],e['text'],fontsize=e['size'],fontname='EarlyOriginalSimHei',fontfile=str(donor),
                color=stroke if mode==2 else color,fill=color,render_mode=mode,
                border_width=width/e['size']if mode==2 else 1,miter_limit=10)
        target=folder/f'page{page_number:02}-original-English-faces.pdf';out.save(target,garbage=0,deflate=False)
    report=dict(source=str(source),source_page=page_number,face_path=str(SIMHEI),face_sha256=SHA,
        glyphs_nonempty_outlines_checked=True,placements=reports,erasure_and_native_motion=qa,native_number_shifts=shifts)
    target.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    return target,1,[updates.get(p['id'],p)for p in placements],report
