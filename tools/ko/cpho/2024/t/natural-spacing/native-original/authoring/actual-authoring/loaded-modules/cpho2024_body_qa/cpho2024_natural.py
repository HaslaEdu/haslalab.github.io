"""Original-native-object, horizontal-only 2024 bilingual composer.

Chinese prose is replaced at its original baseline and nominal point size.
Every mathematical glyph, bar and original picture remains an original PDF
object. Complete consecutive native math fragments preserve internal geometry.
No HTML, scaling, automatic line wrapping, equation input or rasterization.
"""
from pathlib import Path
from collections import Counter
from io import BytesIO
import hashlib,json,re,sys,os
import pymupdf as fitz
from fontTools.ttLib import TTFont
from pdf_original_style_fonts import subset_font
from pdf_native_inline_reposition import reposition_inline
from cpho2024_events import BASE

SOURCE=BASE/'source/CPhO_2024_Chinese_original.pdf'
REPO=Path(os.environ.get('HASLALAB_SOURCE_ROOT',r'C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab'))
FONT_ROOT=REPO/'tools/ko/fonts'
FACE_ROOT=Path(r'D:/CodexBuilds/Hasla-original-style-20261031')
PATTERN=re.compile(r'\{(m\d+)\}')
RICH=re.compile(r'\[([\d-]+)\|([^\]]*)\]')
LANGUAGE_ERASE={(2,'EN'):{'m37'}}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(number):return json.loads((BASE/f'authoring/T/page{number:02}.events.json').read_text('utf8'))
def translation(number,language):
    rows={}
    for line in (BASE/f'authoring/T/page{number:02}.natural.tsv').read_text('utf8').splitlines():
        if not line or line.startswith('#'):continue
        cells=line.split('\t')
        if len(cells)!=3:raise ValueError('TSV needs row, Korean and English: '+line)
        rows[int(cells[0])]=cells[1 if language=='KO'else 2]
    return rows

def font_source(style,language):
    family=style['actual_source_family'];bold=style.get('bold',False)
    if language=='KO':
        if family in ('DengXian','SimHei','Microsoft YaHei'):
            return FONT_ROOT/('NotoSansCJKkr-Bold.otf'if bold else'NotoSansCJKkr-Regular.otf')
        if bold:return FONT_ROOT/'NotoSerifCJKkr-Bold.otf'
        target=BASE/'fonts/Batang-Regular.ttf'
        if not target.exists():
            font=TTFont(r'C:/Windows/Fonts/batang.ttc',fontNumber=0,recalcTimestamp=False);font.save(target);font.close()
        return target
    if family=='DengXian':return BASE/'fonts'/('DENGB.TTF'if bold else'DENG.TTF')
    if family=='SimHei':return FACE_ROOT/'official-hans-fonts/faces/simhei.ttf'
    if family=='SimSun':return FACE_ROOT/'english-face-repair/font-faces/SimSun-5.24.ttf'
    raise ValueError('Unreviewed original prose font: '+family)

def style_of(row,data):
    slots=[s for s in data['source']['slots']if s['row']==row and not s.get('retain_native')]
    if not slots:raise ValueError('No source prose style for row '+str(row))
    roles={(s['actual_source_family'],s['bold'],s['italic'],round(s['size'],3),s.get('render_mode',0))for s in slots}
    # The only mixed-size/styles on one visual row are explicitly reviewed
    # caption/figure placements, which must be handled independently.
    if len(roles)!=1:
        primary=max(slots,key=lambda s:sum('\u4e00'<=c<='\u9fff'for c in s['source']))
        return primary,slots
    return slots[0],slots

def words_width(text,font,size):
    return sum(font.text_length(w,fontsize=size)for w in text.split(' '))+text.count(' ')*size*.25

def units(text,parts,font,size):
    values=[];end=0
    for match in PATTERN.finditer(text):
        if match.start()>end:values.append(dict(kind='prose',text=text[end:match.start()]))
        values.append(dict(kind='math',parts=[parts[match.group(1)]]));end=match.end()
    if end<len(text):values.append(dict(kind='prose',text=text[end:]))
    # Preserve original relative geometry of adjacent native fragments. The
    # intervening source whitespace belongs to the equation, not word spacing.
    merged=[];i=0
    while i<len(values):
        v=values[i];i+=1
        if v['kind']=='math':
            while i<len(values):
                if values[i]['kind']=='math':v['parts']+=values[i]['parts'];i+=1
                elif values[i]['kind']=='prose'and not values[i]['text'].strip()and i+1<len(values)and values[i+1]['kind']=='math':
                    v['parts']+=values[i+1]['parts'];i+=2
                else:break
            rects=[p['rect']for p in v['parts']];v['rect']=[min(r[0]for r in rects),min(r[1]for r in rects),max(r[2]for r in rects),max(r[3]for r in rects)]
            v['width']=v['rect'][2]-v['rect'][0]
        else:v['width']=words_width(v['text'],font,size)
        merged.append(v)
    return merged

def rich_units(text,parts,style,fonts,language,by_id):
    out=[];end=0
    def fragment(value,st):
        face=font_source(st,language);font=fonts[face]
        for u in units(value,parts,font['metric'],st['size']):
            if u['kind']=='prose':u.update(source_style=st,font_path=str(font['path']),size=st['size'],baseline=st['origin'][1])
            out.append(u)
    for m in RICH.finditer(text):
        fragment(text[end:m.start()],style);fragment(m.group(2),by_id[m.group(1)]);end=m.end()
    fragment(text[end:],style)
    return out

def row_bounds(row,data,parts,slots,objects):
    n=data['page'];rid=row['row'];y=row['baseline']
    source_items=[s['source_rect']for s in slots]+[p['rect']for p in parts]
    x0=min(r[0]for r in source_items);x1=541.32
    center=None
    if n==1 and rid in (0,1):x0=20.;x1=575.32;center=297.60
    if rid==data['rows'][-1]['row']:x0=20.;x1=575.32;center=297.60
    # Captions/figure-local prose are centered at their original source span;
    # running body text keeps the source column and its first-line indentation.
    caption=(n,rid)in{(1,11),(2,18),(2,29),(2,38),(3,13),(3,32),(3,43),(4,10)}
    if caption:
        r=[min(q[0]for q in source_items),min(q[1]for q in source_items),max(q[2]for q in source_items),max(q[3]for q in source_items)]
        center=(r[0]+r[2])/2;x0=max(20,center-130);x1=min(575.32,center+130)
    else:
        far=max(r[2]for r in source_items)
        for image in objects['images']:
            r=image['bbox']
            if r[1]<y+3 and r[3]>y-10 and far<=r[0]+1:x1=min(x1,r[0]-4)
        # Word retains its wrapped column for the entire paragraph alongside
        # the nuclear-spectrum figure, even below the first raster strip.
        if n==1 and 2<=rid<=10:x1=383.0
        # The first optical figure's caption extends below its bitmap. Word's
        # left paragraph remains wrapped beside that caption on source row14.
        if n==3 and rid==14:x1=289.4
    return x0,x1,center

def preflight(number,language):
    data=read(number);texts=translation(number,language);parts={p['id']:p for p in data['native_parts']}
    objects=json.loads((BASE/f'inspection/page{number:02}-objects.json').read_text('utf8'))
    if set(texts)!=set(r['row']for r in data['rows']):raise ValueError('Missing or extra translated rows')
    extra_erase=LANGUAGE_ERASE.get((number,language),set())
    wanted=[p['id']for p in parts.values()if p['row']is not None and p['id']not in extra_erase]
    supplied=[s for text in texts.values()for s in PATTERN.findall(text)]
    if Counter(supplied)!=Counter(wanted):raise ValueError('Native fragment coverage mismatch: '+str((Counter(wanted)-Counter(supplied),Counter(supplied)-Counter(wanted))))
    by_face={};styles={};by_id={s['id']:s for s in data['source']['slots']}
    for row in data['rows']:
        style,slots=style_of(row['row'],data);face=font_source(style,language)
        styles[row['row']]=(style,slots,face)
        raw=texts[row['row']]
        for m in RICH.finditer(raw):
            st=by_id[m.group(1)];by_face.setdefault(font_source(st,language),[]).append(m.group(2))
        by_face.setdefault(face,[]).append(PATTERN.sub('',RICH.sub('',raw)))
    fonts={}
    for face,tt in by_face.items():
        path=subset_font(face,tt,cache_dir=BASE/'fonts/subsets');fonts[face]=dict(path=path,metric=fitz.Font(fontfile=str(path)))
    rows=[]
    for row in data['rows']:
        rid=row['row'];style,slots,face=styles[rid];font=fonts[face]['metric'];size=style['size'];text=texts[rid]
        for mid in PATTERN.findall(text):
            if parts[mid]['row']!=rid:raise ValueError('Native fragment may not change baseline/row: '+mid)
        us=rich_units(text,parts,style,fonts,language,by_id);selected=[parts[k]for k in PATTERN.findall(text)]
        left,right,center=row_bounds(row,data,selected,slots,objects);width=sum(v['width']for v in us)
        start=center-width/2 if center is not None else left
        if number==3 and rid==10:
            # The inequality wraps onto an unchanged native-only line. Keep
            # the first half fixed too; language fills the preceding space.
            right=parts['m25']['rect'][2];start=right-width
        x=start
        for v in us:v['x']=x;x+=v['width']
        segment_reports=[]
        if number==2 and rid==36:
            # Three independent subcaptions retain one baseline and remain
            # under their original optical elements. The fast-axis bitmap is
            # an exact original image+clip, never typed or reconstructed.
            segments=text.split('||')
            if len(segments)!=3:raise ValueError('Three reviewed optical subcaptions required')
            positions=[236.,308.5,438. if language=='KO' else 436.5]
            limits=[306.,435.5,541.32]
            us=[]
            for part,pos,limit in zip(segments,positions,limits):
                uu=rich_units(part,parts,style,fonts,language,by_id);xx=pos
                for u in uu:u['x']=xx;xx+=u['width']
                us+=uu;segment_reports.append(dict(left=pos,right=limit,end=xx,overflow=max(0,xx-limit)))
            left=positions[0];right=541.32;start=left;x=max(s['end']for s in segment_reports);center=None
        if number==5 and rid==6:
            segments=text.split('||')
            if len(segments)!=2:raise ValueError('The body and separate Fig.6a caption require independent scopes')
            us=[]
            for index,part in enumerate(segments):
                uu=rich_units(part,parts,style,fonts,language,by_id);w=sum(q['width']for q in uu)
                pos=54. if index==0 else (408.12750244140625+431.29315185546875)/2-w/2
                limit=323.84 if index==0 else 500.
                xx=pos
                for u in uu:u['x']=xx;xx+=u['width']
                us+=uu;segment_reports.append(dict(left=pos,right=limit,end=xx,overflow=max(0,xx-limit)))
            left=54.;right=500.;start=left;x=max(s['end']for s in segment_reports);center=None
        rows.append(dict(row=rid,baseline=row['baseline'],text=text,units=us,source_style=style,
            font_path=str(fonts[face]['path']),font_source=str(face),size=size,start=start,end=x,
            left=left,right=right,center=center,segments=segment_reports,
            overflow=max([left-start,x-right,0]+[s['overflow']for s in segment_reports])))
    return data,rows

def insert_words(page,row,resources):
    reports=[]
    for u in row['units']:
        if u['kind']!='prose':continue
        font=fitz.Font(fontfile=u['font_path']);size=u['size'];style=u['source_style'];mode=style.get('render_mode',0)
        width=(style.get('line_width')or 0)/size if mode in(1,2)else 0
        color=style.get('color',0);color=((color>>16&255)/255,(color>>8&255)/255,(color&255)/255)
        resource=resources.setdefault(u['font_path'],'TranslatedProse'+str(len(resources)))
        x=u['x'];offset=0
        for word in u['text'].split(' '):
            if word:
                point=[x,u.get('baseline',row['baseline'])]
                page.insert_text(point,word,fontname=resource,fontfile=u['font_path'],fontsize=size,
                    color=color,fill=color,render_mode=mode,border_width=width,miter_limit=style.get('miter_limit',10),overlay=True)
                reports.append(dict(text=word,origin=point,size=size,font_resource=resource,source_font=style['source_font'],
                    actual_source_family=style['actual_source_family'],render_mode=mode,color=color,border_width=width))
                x+=font.text_length(word,fontsize=size)
            x+=size*.25
    return reports

def build(number,language,draft=False):
    data,rows=preflight(number,language)
    if not draft and any(r['overflow']>.01 for r in rows):
        raise ValueError('Natural row exceeds original column: '+str([(r['row'],round(r['overflow'],2))for r in rows if r['overflow']>.01]))
    shifts=[]
    objects=json.loads((BASE/f'inspection/page{number:02}-objects.json').read_text('utf8'))
    for row in rows:
        for u in row['units']:
            if u['kind']!='math':continue
            glyphs=[g for p in u['parts']for g in p['glyphs']];paths=[v for p in u['parts']for v in p['vector_paths']]
            # A complete delimiter/fraction expression may contain a native
            # path between separate CID clusters. Carry all source paths in
            # this explicit full expression frame, including zero-width bars.
            frame=fitz.Rect(u['rect'])+(-1,-1,1,1)
            seen={tuple(v['operator_indices'])for v in paths}
            for v in objects['vector_paths']:
                r=v['rect']
                if frame.x0<=r[0]and frame.y0<=r[1]and frame.x1>=r[2]and frame.y1>=r[3]and tuple(v['operator_indices'])not in seen:
                    paths.append(v);seen.add(tuple(v['operator_indices']))
            images=[p['image_path']for p in u['parts']if p.get('image_path')]
            if len(images)>1:raise ValueError('Several independently clipped images need separate reviewed atoms')
            shifts.append(dict(glyphs=glyphs,dx=u['x']-u['rect'][0],
                **(dict(vector_paths=paths)if paths else{}),**(dict(image_path=images[0])if images else{})))
    extra_erase=LANGUAGE_ERASE.get((number,language),set())
    erased=data['erased_glyphs']+[g for p in data['native_parts']if p['id']in extra_erase for g in p['glyphs']]
    raw,qa=reposition_inline(SOURCE,number,erased_glyphs=erased,shifts=shifts,position_tolerance_pt=.001)
    doc=fitz.open(stream=raw,filetype='pdf');page=doc[0];placements=[];font_resources={}
    for row in rows:placements+=insert_words(page,row,font_resources)
    target=BASE/f'T/pages/page{number:02}-{language}{"-draft"if draft else""}.pdf'
    doc.save(target,garbage=0,deflate=False);doc.close()
    report=dict(source=str(SOURCE),source_sha256=sha(SOURCE),source_page=number,language=language,
        output=str(target),output_sha256=sha(target),source_native_move=qa,
        no_scaling=True,no_math_retyping=True,no_automatic_wrap=True,rows=rows,placements=placements,shifts=shifts,
        erased_glyphs=erased,language_only_native_erasure=sorted(extra_erase))
    target.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=1),'utf8')
    return target,report

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('page',type=int);ap.add_argument('language',choices=['KO','EN']);ap.add_argument('--draft',action='store_true');ap.add_argument('--preflight',action='store_true');a=ap.parse_args()
    if a.preflight:
        data,rows=preflight(a.page,a.language)
        print(json.dumps([dict(row=r['row'],overflow=round(r['overflow'],2),width=round(r['end']-r['start'],2),available=round(r['right']-r['left'],2),text=r['text'])for r in rows if r['overflow']>.01],ensure_ascii=False,indent=1))
    else:
        from pdf_memory_gate import page_worker
        with page_worker():path,qa=build(a.page,a.language,a.draft)
        print(path)
