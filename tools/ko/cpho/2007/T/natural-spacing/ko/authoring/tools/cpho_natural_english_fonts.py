"""Original SimHei prose-face repair before natural English line packing.

Full licensed font stays in the D: official acquisition cache. Only subsets
are embedded. Original mathematics is never selected. Actual Calibri numeric
runs in the 2022 heading/date retain their original CID bytes and move only.
"""
from pathlib import Path
import hashlib,json,re
import pymupdf as fitz
from izho_natural_spacing import records,visible
from pdf_native_inline_reposition import reposition_inline
from pdf_original_style_fonts import subset_font
from cpho_original_latin_fonts import verify_real_glyphs

SIMHEI=Path('D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts/faces/simhei.ttf')
SIMHEI_SHA='aa4560dd8fe5645745fed3ffa301c3ca4d6c03cbd738145b613303961ba733b8'
NEW_TEXT={
    (2007,'1-0-0'):'24th National Secondary School Physics Competition: Final Problems',
    (2007,'1-1-0'):'Ningbo, November 2007',
    (2022,'1-0-0'):'39th National Secondary School Physics Competition: Final Theory Paper',
}


def _glyph(r):return{k:r[k] for k in('c','font','size','origin')}


def prepare_english_faces(year,source,page_number,placements,folder):
    selected=[p for p in placements if p['family']=='sans'] if year in(2007,2022) else[]
    if not selected:return Path(source),page_number,placements,None
    if hashlib.sha256(SIMHEI.read_bytes()).hexdigest()!=SIMHEI_SHA:raise ValueError('Official SimHei acquisition SHA changed')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    alltext=''.join(NEW_TEXT.get((year,p['id']),p['text']) for p in selected)
    verify_real_glyphs(SIMHEI,alltext)
    donor=subset_font(SIMHEI,alltext,folder/'fonts');metric=fitz.Font(fontfile=str(donor))
    doc=fitz.open(source);page=doc[page_number-1];rows=visible(records(page))
    erase=[];shifts=[];insertions=[];updated={};journals=[]
    for p in selected:
        x,y=p['point'];oldtext=p['text'];size=p['size'];desired=NEW_TEXT.get((year,p['id']),oldtext)
        candidates=sorted([r for r in rows if abs(r['origin'][1]-y)<.02 and x-.03<=r['origin'][0]<x+p['width']+.03],key=lambda r:r['origin'][0])
        expected=''.join(c for c in oldtext if not c.isspace())
        if ''.join(r['c'] for r in candidates)!=expected:
            raise ValueError(('Exact English prose placement association failed',p['id'],expected,''.join(r['c'] for r in candidates)))
        physical=[];index=0
        for i,c in enumerate(oldtext):
            if c.isspace():continue
            physical.append((i,candidates[index]));index+=1
        keep=[]
        if year==2022:
            for match in re.finditer(r'\d[\d:]*',oldtext):
                chars=[r for i,r in physical if match.start()<=i<match.end()]
                keep.append(dict(text=match[0],glyphs=chars,width=max(r['bbox'][2] for r in chars)-chars[0]['origin'][0]))
            if [m[0] for m in re.finditer(r'\d[\d:]*',desired)]!=[v['text'] for v in keep]:
                raise ValueError('Actual Calibri numeric run order changed')
        preserved={id(r) for item in keep for r in item['glyphs']}
        erase.extend(_glyph(r) for r in candidates if id(r) not in preserved)
        parts=[];pos=0;ki=0
        for match in re.finditer(r'\d[\d:]*',desired) if keep else[]:
            if pos<match.start():parts.append(dict(kind='new',text=desired[pos:match.start()]))
            parts.append(dict(kind='native',**keep[ki]));ki+=1;pos=match.end()
        if pos<len(desired):parts.append(dict(kind='new',text=desired[pos:]))
        if not parts:parts=[dict(kind='new',text=desired)]
        actions=[]
        for part in parts:
            if part['kind']=='native':actions.append(part);continue
            for word in re.split('( )',part['text']):
                if not word:continue
                actions.append(dict(kind='space' if word==' ' else'new',text=word,
                                    width=size/4 if word==' ' else metric.text_length(word,fontsize=size)))
        width=sum(a['width'] for a in actions)
        center=page.rect.width/2 if p.get('align')=='center' or (page_number==1 and p['size']>=14 and y<130) else None
        cursor=center-width/2 if center is not None else x;start=cursor
        trace=candidates[0];color=trace.get('color',(0,0,0))
        for action in actions:
            if action['kind']=='native':
                dx=cursor-action['glyphs'][0]['origin'][0]
                shifts.append(dict(glyphs=[_glyph(r) for r in action['glyphs']],dx=dx))
            elif action['kind']=='new':insertions.append(dict(text=action['text'],point=[cursor,y],size=size,color=color))
            cursor+=action['width']
        updated[p['id']]=dict(p,text=desired,point=[start,y],origin=[start,y],width=width,
                             font=donor.name,word_gap_adjustment=-size/4)
        journals.append(dict(id=p['id'],source_text=oldtext,text=desired,source_face='SimHei400',
                             actual_Calibri_numeric_runs_retained=[v['text'] for v in keep],
                             size=size,baseline=y,point=[start,y],width=width,center=center))
    raw,moveqa=reposition_inline(source,page_number,erased_glyphs=erase,shifts=shifts)
    out=fitz.open(stream=raw,filetype='pdf');target=out[0]
    for entry in insertions:
        color=entry['color'];color=tuple(color)*3 if len(color)==1 else color
        target.insert_text(entry['point'],entry['text'],fontsize=entry['size'],fontname='NaturalSourceSimHei',
                           fontfile=str(donor),color=color,fill=color,render_mode=0)
    path=folder/f'page{page_number:02}-original-English-faces.pdf'
    out.save(path,garbage=0,deflate=False);out.close();doc.close()
    newplacements=[updated.get(p['id'],p) for p in placements]
    report=dict(input=str(source),input_page=page_number,output=str(path),font='Official Microsoft SimHei5.03 Regular400',
                font_acquisition_sha256=SIMHEI_SHA,embedded_subset=str(donor),original_math_unchanged=True,
                rewritten_prose=journals,erasure_and_native_number_move_qa=moveqa)
    path.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    return path,1,newplacements,report
