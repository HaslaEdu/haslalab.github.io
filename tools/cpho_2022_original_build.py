"""CPhO 2022 original-style problem editions, Korean / English.

All equations and original graphics remain native, at their source positions.
Only selected original prose text-show CIDs change. Fixed-size, fixed-baseline
translation slots are reviewed separately; no HTML, automatic shrinking,
paragraph merging, mathematical image insertion, or diagram replacement.
"""
from pathlib import Path
from collections import Counter,defaultdict
from io import BytesIO
import argparse,hashlib,json,re,os,xml.etree.ElementTree as ET
from fontTools.svgLib.path import parse_path
from fontTools.pens.transformPen import TransformPen
import numpy as np
import pymupdf as fitz
from PIL import Image,ImageDraw
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
import cpho_cjk_translate as cjk
from cpho_original_style import source_characters,glyph_key
from pdf_original_text_ops import suppress_prose
from pdf_original_style_fonts import subset_font
from cpho_original_latin_fonts import face as original_latin_face, verify_real_glyphs, word_gap as latin_word_gap, BUILD_ROOT as EN_REPAIR_ROOT
import cpho_2022_original_labels as raster_labels
from pdf_original_text_ops import native_form_glyphs

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'tmp/source-audit/CPhO_2022_T_ZH.pdf'
BASE=ROOT/'tmp/original-style-repair/2022'
AUTHOR=ROOT/'tools/ko/cpho/2022/original'
FONTS=ROOT/'tools/ko/fonts'
SOURCE_SHA='89d1718db8a92afebb741b755beadd4476ac11654b50a5b79d4eaa2d13b91e04'


def selected_glyphs(page):
    return [c for s in page['slots']if not s.get('retain_native')for c in s['source_characters']
            if not c['c'].isspace()and c['index']not in s.get('retained_source_indices',[])]


def translated_text(slot,value):
    if slot.get('retain_native'):return ''
    value=value.strip()
    if slot.get('native_prefix')and value.startswith((')','）')):value=value[1:].lstrip()
    return value


def glyph_ink_box(doc,page,char,font_cache):
    """Original outline bounds, used to keep native mathematical punctuation."""
    name=char['font']
    if name not in font_cache:
        record=next(item for item in page.get_fonts(full=True)if item[3].split('+')[-1]==name)
        font_cache[name]=TTFont(BytesIO(doc.extract_font(record[0])[3]))
    font=font_cache[name];glyphset=font.getGlyphSet();glyph=None
    for trace in page.get_texttrace():
        if trace['font']!=name:continue
        for cp,gid,origin,bbox in trace['chars']:
            if chr(cp)==char['c']and abs(origin[0]-char['origin'][0])<.02 and abs(origin[1]-char['origin'][1])<.02:
                glyph=gid;break
        if glyph is not None:break
    if glyph is None:raise ValueError('No native glyph outline for '+repr(char))
    pen=BoundsPen(glyphset);glyphset[font.getGlyphOrder()[glyph]].draw(pen)
    if pen.bounds is None:return fitz.Rect(char['bbox'])
    x0,y0,x1,y1=pen.bounds;factor=char['size']/font['head'].unitsPerEm;x,y=char['origin']
    return fitz.Rect(x+x0*factor,y-y1*factor,x+x1*factor,y-y0*factor)


def outline_boxes(page):
    root=ET.fromstring(page.get_svg_image(text_as_path=True));paths={e.get('id'):e.get('d')for e in root.iter()if e.tag.endswith('path')and e.get('id')};result=[]
    for e in root.iter():
        if not e.tag.endswith('use')or 'data-text'not in e.attrib:continue
        raw=e.get('transform','');m=re.search(r'matrix\(([^)]+)\)',raw)
        if not m:continue
        matrix=tuple(float(v)for v in m[1].replace(',',' ').split());name=e.get('{http://www.w3.org/1999/xlink}href','').lstrip('#')
        if name not in paths:continue
        pen=BoundsPen(None);parse_path(paths[name],TransformPen(pen,matrix))
        if pen.bounds:result.append({'c':e.get('data-text'),'origin':matrix[-2:],'bbox':list(pen.bounds)})
    return result


from pdf_original_image_ink import image_ink_regions as image_ink_rects


def group_prose_slots(page,slots):
    """Manually approved same-line language groups only: score labels,
    figure reference codes, and prose split by Word spacing. No paragraphs
    or scientific variables/equations are joined or repositioned.
    """
    groups=json.loads((AUTHOR/'prose-groups.json').read_text(encoding='utf8'));allchars=source_characters(page);byid={s['id']:s for s in slots}
    for ids in groups:
        if ids[0]not in byid:continue
        parts=[byid[k]for k in ids];first=parts[0];last=parts[-1]
        left=min(s['source_rect'][0]for s in parts);right=max(s['source_rect'][2]for s in parts)
        chars=[c for c in allchars if left-.05<=c['origin'][0]<right+.05 and abs(c['origin'][1]-first['origin'][1])<1.5 and not c['c'].isspace()]
        r=fitz.Rect(chars[0]['bbox'])
        for c in chars[1:]:r|=fitz.Rect(c['bbox'])
        first.update(source_characters=chars,source=''.join(c['c']for c in sorted(chars,key=lambda c:c['origin'][0])),source_rect=list(r),right=last['right'],same_line_prose_groups=ids)
        first.pop('retained_source_indices',None);first.pop('native_prefix',None)
        first['allowed_rect']=[min(left,first['origin'][0]),first['origin'][1]-first['size']*1.05,max(r.x1,last['right']),first['origin'][1]+first['size']*.25]
        if first['origin'][1]>770:
            # Footers are ordinary language, retaining their original centre.
            center=(left+right)/2;first['align']='center';first['origin'][0]=center-70;first['right']=center+70;first['allowed_rect'][0]=center-70;first['allowed_rect'][2]=center+70
        for k in ids[1:]:slots.remove(byid[k])
    spacing=json.loads((AUTHOR/'word-spacing.json').read_text(encoding='utf8'))
    for slot in slots:
        for lang,values in spacing.items():
            if slot['id']in values:slot[lang+'_word_gap_adjustment']=values[slot['id']]
    offsets=json.loads((AUTHOR/'translation-offsets.json').read_text(encoding='utf8'))
    for slot in slots:slot.update(offsets.get(slot['id'],{}))
    return slots


def extract():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Source SHA mismatch')
    doc=fitz.open(SOURCE);pages=[];report=[];font_cache={}
    for pi,page in enumerate(doc):
        chars=source_characters(page);rows=cjk.prose_rows(chars);slots=[];textrows=[]
        inks=outline_boxes(page);image_inks=image_ink_rects(doc,page)
        def ink(c):
            candidates=[x['bbox']for x in inks if x['c']==c['c']and abs(x['origin'][0]-c['origin'][0])<.03 and abs(x['origin'][1]-c['origin'][1])<.03]
            return candidates[0]if candidates else c['bbox']
        forms=native_form_glyphs(SOURCE,pi+1)
        for ri,row in enumerate(rows):
            owned=[c for c in row['chars']if not c['c'].isspace()]
            if not owned:continue
            isheading=pi==0 and row['baseline']<80
            if isheading:
                # The original title and date are prose lines. Preserve their
                # heading role, point size and CJK baseline, including numbers.
                owned=[c for c in chars if abs(c['origin'][1]-row['baseline'])<.3 and not c['c'].isspace()]
            indices={c['index']for c in owned}
            locked=[c for c in chars if c['index']not in indices and not c['c'].isspace()
                and c['bbox'][1]<row['baseline']+row['size']*.2 and c['bbox'][3]>row['baseline']-row['size']]
            groups=[]
            for ch in sorted(owned,key=lambda c:c['origin'][0]):
                blocked=groups and any(groups[-1][-1]['origin'][0]+.1<c['origin'][0]<ch['origin'][0]-.1 for c in locked)
                if groups and not blocked and ch['origin'][0]-groups[-1][-1]['bbox'][2]<3:groups[-1].append(ch)
                else:groups.append([ch])
            if isheading:groups=[sorted(owned,key=lambda c:c['origin'][0])]
            for si,group in enumerate(groups):
                first=next((c for c in group if c['font'].startswith('ºÚÌå')),group[0])if isheading else group[0]
                r=fitz.Rect(group[0]['bbox'])
                for c in group[1:]:r|=fitz.Rect(c['bbox'])
                right=559.7
                # Large original diagrams are obstacles; their original bytes
                # remain untouched. Formula images/forms are retained natively.
                for image in page.get_image_info():
                    box=fitz.Rect(image['bbox'])
                    if image['width']>300 and image['height']>250 and box.x0>r.x0 and box.y0<r.y1 and box.y1>r.y0:right=min(right,box.x0-.5)
                other=[c for c in locked if c['origin'][0]>group[-1]['origin'][0]+.1]
                right=min([right,*[ink(c)[0]-.3 for c in other]])
                for image in image_inks:
                    box=fitz.Rect(image['ink_rect'])
                    if box.x0>group[-1]['origin'][0]+.1 and box.y0<r.y1 and box.y1>r.y0:right=min(right,box.x0-.3)
                src=''.join(c['c']for c in group);family='sans'if first['font'].startswith('ºÚÌå')else'serif'
                slot={'id':f'{pi+1}-{ri}-{si}','page':pi,'row':ri,'source':src,'source_font':first['font'],
                    'size':first['size'],'flags':first['flags'],'family':family,'bold':bool(first['flags']&16),'italic':bool(first['flags']&2),
                    'color':first['color'],'origin':list(group[0]['origin']),'source_rect':list(r),'right':right,'source_characters':group,
                    'render_mode':0,'line_width':None,'miter_limit':10,
                    'allowed_rect':[r.x0,row['baseline']-first['size']*1.05,max(r.x1,right),row['baseline']+first['size']*.25]}
                if src=='图':
                    slot['align']='right';slot['origin'][0]-=20;slot['allowed_rect'][0]-=20
                if isheading:
                    center=(r.x0+r.x1)/2;slot['align']='center';slot['origin']=[36,row['baseline']];slot['right']=2*center-36
                    slot['allowed_rect']=[36,row['baseline']-first['size']*1.05,slot['right'],row['baseline']+first['size']*.25]
                if src and all(c in '，．。；：！？、（）【】(),.;:!?[]'for c in src):slot['retain_native']=True
                if src in ['。','；']:slot['retain_native']=False
                if slot['id']=='4-0-0':slot['right']=58.0
                if slot['id']=='1-21-5':slot['right']=408.8
                if pi==1 and ri<=10 and r.x0<335:slot['right']=min(slot['right'],333.5)
                if pi==0 and (ri==10 or 21<=ri<=26)and r.x0<409:slot['right']=min(slot['right'],408.0)
                if slot['id']=='1-21-5':slot['right']=408.8
                slots.append(slot)
            part=[c for c in chars if abs(c['origin'][1]-row['baseline'])<3.5]
            textrows.append({'row':ri,'baseline':row['baseline'],'source':' '.join(''.join(c['c']for c in sorted(part,key=lambda c:c['origin'][0])).split()),'slots':[s['id']for s in slots if s['row']==ri]})
        slots=group_prose_slots(page,slots)
        pending=0
        for slot in slots:
            if slot.get('retain_native'):
                pending+=sum(slot['source'].count(c)for c in '（(')-sum(slot['source'].count(c)for c in '）)');pending=max(pending,0)
            elif pending and slot['source'].startswith(('）',')')):
                prefix=slot['source_characters'][0];ink=glyph_ink_box(doc,page,prefix,font_cache)
                slot['retained_source_indices']=[prefix['index']];slot['native_prefix']=prefix['c'];slot['origin'][0]=max(slot['origin'][0],ink.x1+.6);pending-=1
        pages.append({'source_page':pi+1,'page_rect':list(page.rect),'slots':slots,'rows':textrows,'native_form_glyphs':forms,'image_ink_rects':image_inks})
        report.append({'page':pi+1,'rows':len(rows),'slots':len(slots),'prose_glyphs':len(selected_glyphs(pages[-1]))})
    data={'source':str(SOURCE.resolve()),'source_sha256':SOURCE_SHA,'pages':pages,'provenance_notes':[
        {'page':2,'description':'Original Chinese centrifugal/Coriolis force and torque subscripts in native formula Forms are mathematical labels and remain exactly as printed. Surrounding prose definitions are translated.'}]}
    BASE.mkdir(parents=True,exist_ok=True);AUTHOR.mkdir(parents=True,exist_ok=True)
    (BASE/'slots.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    lines=[]
    for page in pages:
        lines.append(f'\nPAGE {page["source_page"]}')
        for row in page['rows']:
            lines.append(f'ROW {row["row"]} | {row["source"]}')
            for slot in page['slots']:
                if slot['row']==row['row']:lines.append(f'{slot["id"]}\t{slot["source"]}\t{slot["right"]-slot["origin"][0]:.2f}')
    (BASE/'source-slots.txt').write_text('\n'.join(lines),encoding='utf8');print(json.dumps(report),flush=True);return data


def translations(data):
    result={}
    for page in data['pages']:
        file=AUTHOR/f'page{page["source_page"]:02}.tsv'
        for line in file.read_text(encoding='utf8').splitlines():
            if not line.strip():continue
            key,ko,en=line.split('\t',2);result[key]={'ko':ko,'en':en}
    required={s['id']for p in data['pages']for s in p['slots']}
    if set(result)!=required:raise ValueError('Translation/source slot IDs differ')
    return result


def prepare_fonts(data,texts,lang,subset_files=True,pages=None):
    groups=defaultdict(str)
    for page in data['pages']:
        if pages and page['source_page']not in pages:continue
        for s in page['slots']:groups[(s['family'],s['bold'])]+=translated_text(s,texts[s['id']][lang])
    groups[('serif',False)]+=''.join(label[lang]for label in raster_labels.data()['labels'])
    result={};cache=EN_REPAIR_ROOT/'2022'/'fonts'if lang=='en'else BASE/'fonts';cache.mkdir(parents=True,exist_ok=True)
    for (family,bold),text in groups.items():
        if lang=='en':
            source=original_latin_face(2022,family,bold);verify_real_glyphs(source,text)
            path=subset_font(source,text,cache)if subset_files else source
        else:
            name=('NotoSerifCJKkr'if family=='serif'else'NotoSansCJKkr')+('-Bold'if bold else'-Regular')+'.otf'
            path=subset_font(FONTS/name,text,cache)if subset_files else FONTS/name
        result[(family,bold)]=path
    return result


def fitting(data,texts,lang,font_files,pages=None):
    fonts={k:fitz.Font(fontfile=str(v))for k,v in font_files.items()};report=[]
    for page in data['pages']:
        if pages and page['source_page']not in pages:continue
        for s in page['slots']:
            text=translated_text(s,texts[s['id']][lang]);font=fonts[(s['family'],s['bold'])]
            word_gap=latin_word_gap(s,lang,2022)
            width=font.text_length(text,fontsize=s['size'])+text.count(' ')*word_gap
            available=s['right']-s['origin'][0];point=list(s['origin'])
            if lang=='en'and not s.get('align'):
                later=[q['origin'][0]-.3 for q in page['slots']if q['id']!=s['id']and abs(q['origin'][1]-s['origin'][1])<.3 and q['origin'][0]>s['origin'][0]+.1 and translated_text(q,texts[q['id']][lang])]
                if later:available=min(available,min(later)-s['origin'][0])
            if s.get(lang+'_origin_dx'):
                dx=s[lang+'_origin_dx'];point[0]+=dx;available-=dx
            if s.get('align')=='center':point[0]+=(available-width)/2
            if s.get('align')=='right':point[0]=s['right']-width
            if not s.get('align')and not s.get('native_prefix')and s['source'].startswith(('（','）'))and text:
                marker='('if s['source'].startswith('（')else')'
                inset=(s['size']-font.text_length(marker,fontsize=s['size']))/2 if text.startswith(marker)else 2
                point[0]+=inset;available-=inset
            report.append({'id':s['id'],'page':page['source_page'],'source':s['source'],'text':text,'width':width,'available':available,
                'overflow':max(0,width-available),'font':font_files[(s['family'],s['bold'])].name,'size':s['size'],'origin':point,
                'word_gap_adjustment':word_gap})
    return report


def preflight(pages=None):
    data=json.loads((BASE/'slots.json').read_text(encoding='utf8'));texts=translations(data);report=[]
    for lang in ['ko','en']:
        fonts=prepare_fonts(data,texts,lang,False,pages);rows=fitting(data,texts,lang,fonts,pages)
        for r in rows:r['lang']=lang
        report.extend(rows);print(lang,'overflows',sum(r['overflow']>.02 for r in rows),flush=True)
    target=BASE/('preflight'+(''.join('-'+str(n)for n in pages)if pages else'')+'.json')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report


def native_page(data,page):
    selected=selected_glyphs(page)
    key=hashlib.sha256(json.dumps([glyph_key(c)for c in selected],ensure_ascii=False).encode('utf8')).hexdigest()
    folder=BASE/'native';folder.mkdir(parents=True,exist_ok=True);path=folder/f'page{page["source_page"]:02}.pdf';meta=path.with_suffix('.json')
    core_sha=hashlib.sha256((ROOT/'tools/pdf_original_text_ops.py').read_bytes()).hexdigest()
    if path.exists()and meta.exists():
        cached=json.loads(meta.read_text(encoding='utf8'))
        if cached.get('source_sha256')==SOURCE_SHA and cached.get('selection_sha256')==key and cached.get('suppressor_sha256')==core_sha:return path,cached['removed']
    raw,n=suppress_prose(SOURCE,page['source_page'],selected);path.write_bytes(raw)
    meta.write_text(json.dumps({'source_sha256':SOURCE_SHA,'selection_sha256':key,'removed':n,'suppressor_sha256':core_sha},indent=2),encoding='utf8')
    return path,n


def compose(lang,pages,allow_draft=False):
    data=json.loads((BASE/'slots.json').read_text(encoding='utf8'));texts=translations(data)
    reviewed_file=AUTHOR/'reviewed-pages.json';reviewed=json.loads(reviewed_file.read_text(encoding='utf8'))if reviewed_file.exists()else[]
    if not allow_draft and any(n not in reviewed for n in pages):raise ValueError('Unreviewed page translations; use preview mode while editing')
    fonts=prepare_fonts(data,texts,lang,pages=pages);rows=fitting(data,texts,lang,fonts,pages);bad=[r for r in rows if r['overflow']>.02]
    (BASE/f'fit-{lang}.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
    if bad:raise ValueError('Overflow: '+', '.join(r['id']for r in bad))
    byid={r['id']:r for r in rows};doc=fitz.open()
    for page in data['pages']:
        if page['source_page']not in pages:continue
        source,n=native_page(data,page);native=fitz.open(source);doc.insert_pdf(native);target=doc[-1]
        group_type,group_value=native.xref_get_key(native[0].xref,'Group')
        if group_type=='dict':doc.xref_set_key(target.xref,'Group',group_value)
        elif group_type!='null':raise ValueError('Review indirect native page transparency group before copying')
        native.close()
        for slot in page['slots']:
            r=byid[slot['id']];text=r['text']
            if not text:continue
            path=fonts[(slot['family'],slot['bold'])];name='Translation'+slot['family']+('Bold'if slot['bold']else'Regular')
            font=fitz.Font(fontfile=str(path));runs=[];position=0
            pattern=(r'그림(?:\s*(?:\([가나]\)|[가나]))?'if lang=='ko'else r'Fig\.\s*(?:\(?[ab12]\)?)?|\b(?:figure|shown|drawn)\b')
            matches=list(re.finditer(pattern,text))if page.get('magenta_figure_references')else[]
            for match in matches:
                if position<match.start():runs.append((text[position:match.start()],slot['color']))
                runs.append((match[0],16711935));position=match.end()
            if position<len(text):runs.append((text[position:],slot['color']))
            x,y=r['origin']
            for part,color in runs:
                chunks=re.split('( )',part)if r['word_gap_adjustment']else[part]
                for chunk in chunks:
                    if not chunk:continue
                    mode=slot.get('render_mode',0);width=slot.get('line_width')or 0
                    target.insert_text(fitz.Point(x,y),chunk,fontsize=slot['size'],fontname=name,fontfile=str(path),
                        color=tuple(((color>>n)&255)/255 for n in [16,8,0]),fill=tuple(((color>>n)&255)/255 for n in [16,8,0]),
                        render_mode=mode,border_width=width/slot['size']if mode in [1,2]else.05,miter_limit=slot.get('miter_limit',10),overlay=slot.get('overlay',True))
                    x+=font.text_length(chunk,fontsize=slot['size'])+(r['word_gap_adjustment']if chunk==' 'else 0)
    label_report=raster_labels.apply(doc,lang,fonts[('serif',False)],pages)
    folder=Path(os.environ.get('CPHO_EN_REPAIR_DIR',str(EN_REPAIR_ROOT/'2022'/('preview'if allow_draft else'editions'))))if lang=='en'else BASE/('preview'if allow_draft else'editions');folder.mkdir(parents=True,exist_ok=True)
    part='T'if pages==list(range(1,5))else'TS'if pages==list(range(5,21))else'pages-'+'-'.join(map(str,pages))
    output=folder/f'CPhO_2022_{part}_{lang.upper()}.pdf';doc.save(output,garbage=0,deflate=False);doc.close()
    output.with_suffix('.build.json').write_text(json.dumps({'source_sha256':SOURCE_SHA,'source_pages':pages,'fit_report':rows,'raster_label_translation':label_report},ensure_ascii=False,indent=2),encoding='utf8')
    print(output,flush=True);return output


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['extract','preflight','build']);p.add_argument('--pages',nargs='+',type=int);p.add_argument('--lang',choices=['ko','en']);p.add_argument('--draft',action='store_true');args=p.parse_args()
    if args.command=='extract':extract()
    elif args.command=='preflight':preflight(args.pages)
    else:
        for lang in ([args.lang]if args.lang else['ko','en']):
            for pages in ([args.pages]if args.pages else[list(range(1,5))]):compose(lang,pages,args.draft)


if __name__=='__main__':main()
