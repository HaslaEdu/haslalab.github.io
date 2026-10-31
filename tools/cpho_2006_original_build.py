"""CPhO 2006 original-style problem editions, Korean / English.

All equations and original graphics remain native, at their source positions.
Only selected original prose text-show CIDs change. Fixed-size, fixed-baseline
translation slots are reviewed separately; no HTML, automatic shrinking,
paragraph merging, mathematical image insertion, or diagram replacement.
"""
from pathlib import Path
from collections import Counter,defaultdict
from io import BytesIO
import argparse,hashlib,json,re,os
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
import cpho_2006_original_captions as raster_captions

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'tmp/source-audit/CPhO_2006_T_ZH.pdf'
BASE=ROOT/'tmp/original-style-repair/2006'
AUTHOR=ROOT/'tools/ko/cpho/2006/original'
FONTS=ROOT/'tools/ko/fonts'
SOURCE_SHA='4ca77258299918a44f26320027466b81cc70c97e7e467ee190282be0f4516042'


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
        record=next(item for item in page.get_fonts(full=True)if item[3]==name)
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


def extract():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Source SHA mismatch')
    doc=fitz.open(SOURCE);pages=[];report=[];font_cache={}
    for pi,page in enumerate(doc):
        chars=source_characters(page);rows=cjk.prose_rows(chars);slots=[];textrows=[]
        traces=page.get_texttrace();render_types=Counter(t['type']for t in traces)
        for ri,row in enumerate(rows):
            owned=list(row['chars']);allhei=all(c['font']=='ºÚÌå+FPEF'for c in owned)
            # A long blank answer field must not bridge unrelated prose
            # groups on its two sides.
            owned=[c for c in owned if not c['c'].isspace()]
            if allhei:
                owned=[c for c in chars if c['font']=='ºÚÌå+FPEF'and abs(c['origin'][1]-row['baseline'])<.04]
            locked=[c for c in chars if c['index']not in {g['index']for g in owned}and not c['c'].isspace()
                and c['bbox'][1]<row['baseline']+row['size']*.2 and c['bbox'][3]>row['baseline']-row['size']]
            groups=[]
            for ch in sorted(owned,key=lambda c:c['origin'][0]):
                blocked=groups and any(groups[-1][-1]['origin'][0]+.1<c['origin'][0]<ch['origin'][0]-.1 for c in locked)
                if groups and not blocked and ch['origin'][0]-groups[-1][-1]['bbox'][2]<3:groups[-1].append(ch)
                else:groups.append([ch])
            if allhei:groups=[owned]
            for si,group in enumerate(groups):
                visible=[c for c in group if not c['c'].isspace()]
                if visible:group=visible
                first=group[0];r=fitz.Rect(first['bbox'])
                for c in group[1:]:r|=fitz.Rect(c['bbox'])
                other=[c for c in locked if c['origin'][0]>group[-1]['origin'][0]+.1]
                right=511.2  # measured original body-column edge, all four pages
                for image in page.get_image_info():
                    box=fitz.Rect(image['bbox'])
                    if image['width']>20 and image['height']>20 and box.x0>r.x0 and box.y0<r.y1 and box.y1>r.y0:
                        right=min(right,box.x0-6)
                gap=.3
                right=min([right,*[c['bbox'][0]-gap for c in other]])
                src=''.join(c['c']for c in group);family='sans'if allhei else'serif'
                slot={'id':f'{pi+1}-{ri}-{si}','page':pi,'row':ri,'source':src,'source_font':first['font'],
                    'size':first['size'],'flags':first['flags'],'family':family,'bold':bool(first['flags']&16),
                    'italic':bool(first['flags']&2),'color':first['color'],'origin':list(first['origin']),
                    'source_rect':list(r),'right':right,'source_characters':group,
                    'allowed_rect':[r.x0,row['baseline']-first['size']*1.05,max(r.x1,right),row['baseline']+first['size']*.25]}
                # The original answer rules start within these baselines.
                # Their blank writing areas remain entirely available.
                answer_right={'1-20-0':114,'3-8-0':317,'3-13-0':233,'3-15-0':173}.get(slot['id'])
                if answer_right is not None:slot['right']=min(slot['right'],answer_right)
                matching=[t for t in traces if t['font']==first['font']and any(abs(o[0]-first['origin'][0])<.02 and abs(o[1]-first['origin'][1])<.02 for cp,gid,o,box in t['chars'])]
                types={t['type']for t in matching};slot['render_mode']=2 if types=={0,1}else next(iter(types),0)
                slot['line_width']=next((t['linewidth']for t in matching if t['type']==1),None);slot['miter_limit']=10
                if allhei and first['size']>14:
                    slot['align']='center';slot['right']=r.x1;slot['allowed_rect'][2]=r.x1
                if first['color']==16711680:
                    center=(r.x0+r.x1)/2
                    slot['align']='center';slot['origin'][0]=90;slot['right']=2*center-90
                    slot['allowed_rect'][0]=90;slot['allowed_rect'][2]=506
                    # The source footer precedes the large fragmented page-2
                    # illustration. Keep its original occlusion/paint order.
                    if pi==1 and first['origin'][1]>700:slot['overlay']=False
                if src.strip()=='图':
                    # A caption's figure number stays native. Translate its
                    # Chinese word in the blank immediately to its left.
                    slot['align']='right';slot['origin'][0]-=30;slot['right']=min(r.x1,right)
                    slot['allowed_rect'][0]-=30
                if src.strip()=='表':
                    slot['align']='right';slot['origin'][0]-=30;slot['right']=min(r.x1,right);slot['allowed_rect'][0]-=30
                if re.fullmatch('图[甲乙]',src.strip()):
                    center=(r.x0+r.x1)/2;slot['align']='center';slot['origin'][0]=center-50;slot['right']=center+50
                    slot['allowed_rect'][0]=min(r.x0,center-50);slot['allowed_rect'][2]=max(r.x1,center+50)
                if src and all(c in '，．。；：！？、（）【】(),.;:!?[]'for c in src):
                    slot['retain_native']=True
                if slot['id']=='3-10-5':
                    # An action-clause comma is language punctuation, not a
                    # mathematical delimiter. Korean needs its object marker
                    # on the next original baseline instead.
                    slot['retain_native']=False
                if slot['id']=='2-24-2':slot['en_word_gap_adjustment']=-.6
                if slot['id']=='1-1-0':
                    # Source 3 ink ends at 204.49pt (+0.151pt stroke), with
                    # a genuine 4.78pt gap before 届. Use it for the ordinal.
                    slot['en_origin_dx']=-4;slot['allowed_rect'][0]-=4
                slots.append(slot)
            baseline=row['baseline'];part=[c for c in chars if abs(c['origin'][1]-baseline)<3.5]
            textrows.append({'row':ri,'baseline':baseline,'source':' '.join(''.join(c['c']for c in sorted(part,key=lambda c:c['origin'][0])).split()),
                             'slots':[s['id']for s in slots if s['row']==ri]})
        pending=0
        for slot in slots:
            if slot.get('retain_native'):
                pending+=sum(slot['source'].count(c)for c in '（(')-sum(slot['source'].count(c)for c in '）)');pending=max(pending,0)
            elif pending and slot['source'].startswith(('）',')')):
                prefix=slot['source_characters'][0];ink=glyph_ink_box(doc,page,prefix,font_cache)
                slot['retained_source_indices']=[prefix['index']];slot['native_prefix']=prefix['c']
                # Use real ink, not the full-width metric cell. Its blank
                # right bearing can accommodate translated prose safely.
                slot['origin'][0]=max(slot['origin'][0],ink.x1+.6)
                pending-=1
        pages.append({'source_page':pi+1,'page_rect':list(page.rect),'slots':slots,'rows':textrows,
                      'magenta_figure_references':any(c['c']=='图'and c['color']==16711935 for c in chars)})
        report.append({'page':pi+1,'rows':len(rows),'slots':len(slots),'prose_glyphs':len(selected_glyphs(pages[-1])),'source_text_render_types':dict(render_types)})
    data={'source':str(SOURCE.resolve()),'source_sha256':SOURCE_SHA,'pages':pages,'extraction_report':report,
        'provenance_notes':[{'page':2,'description':'The original gravitational-acceleration unit has exponent -1. It is retained exactly without an editorial note or correction.'},
            {'page':2,'description':'The source illustration obscures part of the red footer. Translation preserves that original stacking order.'},
            {'page':4,'description':'A 6pt native exponent-minus glyph maps to Chinese 一 in the source text layer. Its mathematical shape is retained unchanged.'}]}
    BASE.mkdir(parents=True,exist_ok=True);AUTHOR.mkdir(parents=True,exist_ok=True)
    (BASE/'slots.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    lines=[]
    for page in pages:
        lines.append(f'\nPAGE {page["source_page"]}')
        for row in page['rows']:
            lines.append(f'ROW {row["row"]} | {row["source"]}')
            for s in page['slots']:
                if s['row']==row['row']:lines.append(f'{s["id"]}\t{s["source"]}\t{s["right"]-s["origin"][0]:.2f}')
    (BASE/'source-slots.txt').write_text('\n'.join(lines),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False),flush=True);return data


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
    groups[('serif',False)]+='도'if lang=='ko'else'Fig.'
    result={};cache=EN_REPAIR_ROOT/'2006'/'fonts'if lang=='en'else BASE/'fonts';cache.mkdir(parents=True,exist_ok=True)
    for (family,bold),text in groups.items():
        if lang=='en':
            source=original_latin_face(2006,family,bold);verify_real_glyphs(source,text)
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
            word_gap=latin_word_gap(s,lang,2006)
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
        source,n=native_page(data,page);native=fitz.open(source);doc.insert_pdf(native);native.close();target=doc[-1]
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
    original=fitz.open(SOURCE)
    caption_report=raster_captions.apply(doc,original,lang,fonts[('serif',False)],pages)
    original.close()
    folder=Path(os.environ.get('CPHO_EN_REPAIR_DIR',str(EN_REPAIR_ROOT/'2006'/('preview'if allow_draft else'editions'))))if lang=='en'else BASE/('preview'if allow_draft else'editions');folder.mkdir(parents=True,exist_ok=True)
    part='T'if pages==list(range(1,5))else'TS'if pages==list(range(5,21))else'pages-'+'-'.join(map(str,pages))
    output=folder/f'CPhO_2006_{part}_{lang.upper()}.pdf';doc.save(output,garbage=0,deflate=False);doc.close()
    output.with_suffix('.build.json').write_text(json.dumps({'source_sha256':SOURCE_SHA,'source_pages':pages,'fit_report':rows,'raster_caption_translation':caption_report},ensure_ascii=False,indent=2),encoding='utf8')
    print(output,flush=True);return output


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['extract','preflight','build']);p.add_argument('--pages',nargs='+',type=int);p.add_argument('--lang',choices=['ko','en']);p.add_argument('--draft',action='store_true');args=p.parse_args()
    if args.command=='extract':extract()
    elif args.command=='preflight':preflight(args.pages)
    else:
        for lang in ([args.lang]if args.lang else['ko','en']):
            for pages in ([args.pages]if args.pages else[list(range(1,5))]):compose(lang,pages,args.draft)


if __name__=='__main__':main()
