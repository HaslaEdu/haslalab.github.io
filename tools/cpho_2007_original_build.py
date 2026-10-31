"""CPhO 2007 original-style problem and solution editions, Korean / English.

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

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'tmp/source-audit/CPhO_2007_T_ZH.pdf'
BASE=ROOT/'tmp/original-style-repair/2007'
AUTHOR=ROOT/'tools/ko/cpho/2007/original'
FONTS=ROOT/'tools/ko/fonts'
SOURCE_SHA='2e30b56ab9274363686cbf5bc1ef7532dcf579e0703de2c01098b003ab70cdd9'


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
            if allhei:
                owned=[c for c in chars if c['font']=='ºÚÌå+FPEF'and abs(c['origin'][1]-row['baseline'])<.04]
                if pi==0 and ri==2:owned=[c for c in owned if c['c']!='★']
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
                right=506
                for image in page.get_image_info():
                    box=fitz.Rect(image['bbox'])
                    if image['width']>20 and image['height']>20 and box.x0>r.x0 and box.y0<r.y1 and box.y1>r.y0:
                        right=min(right,box.x0-6)
                gap={'3-17-1':.15,'3-23-2':.4,'4-6-5':.1}.get(f'{pi+1}-{ri}-{si}',.65)
                right=min([right,*[c['bbox'][0]-gap for c in other]])
                src=''.join(c['c']for c in group);family='sans'if allhei else'serif'
                slot={'id':f'{pi+1}-{ri}-{si}','page':pi,'row':ri,'source':src,'source_font':first['font'],
                    'size':first['size'],'flags':first['flags'],'family':family,'bold':bool(first['flags']&16),
                    'italic':bool(first['flags']&2),'color':first['color'],'origin':list(first['origin']),
                    'source_rect':list(r),'right':right,'source_characters':group,
                    'allowed_rect':[r.x0,row['baseline']-first['size']*1.05,max(r.x1,right),row['baseline']+first['size']*.25]}
                matching=[t for t in traces if t['font']==first['font']and any(abs(o[0]-first['origin'][0])<.02 and abs(o[1]-first['origin'][1])<.02 for cp,gid,o,box in t['chars'])]
                types={t['type']for t in matching};slot['render_mode']=2 if types=={0,1}else next(iter(types),0)
                slot['line_width']=next((t['linewidth']for t in matching if t['type']==1),None);slot['miter_limit']=10
                if allhei and first['size']>14:
                    slot['align']='center';slot['right']=r.x1;slot['allowed_rect'][2]=r.x1
                if pi==0 and ri==1:
                    slot['align']='center';slot['right']=r.x1;slot['allowed_rect'][2]=r.x1
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
                if slot['id']=='4-18-1':
                    # Verified source ink ends at x=211.58; the 5.62pt
                    # genuine gap before this label permits a 4.2pt shift.
                    slot['en_origin_dx']=-4.2;slot['allowed_rect'][0]-=4.2
                if slot['id']=='3-23-2':
                    # Keep the full physical term at source size. Only the
                    # two ASCII word gaps change, by 0.4pt each.
                    slot['en_word_gap_adjustment']=-.4
                if src and all(c in '，．。；：！？、（）【】(),.;:!?[]'for c in src):
                    slot['retain_native']=True
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
        'provenance_notes':[{'page':18,'description':'The original recoil-approximation comparison glyph is an empty square / unmapped character. Its native glyph is retained without a printed editorial note.'}]}
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


def old_translations():
    raw=json.loads((ROOT/'tools/ko/cpho/2007/bilingual/raw-translation.json').read_text(encoding='utf8'))
    problems={}
    for line in (ROOT/'tools/ko/cpho/2007/problems.tsv').read_text(encoding='utf8').splitlines():
        key,ko,en=line.split('\t',2);problems[key]={'ko':ko,'en':en}
    theory=[{**e,**problems[e['id']]}for e in raw['entries']if e['page']<4]
    raw=json.loads((ROOT/'tmp/cpho-build/2007-solution/translation.json').read_text(encoding='utf8'))
    solutions={}
    for line in (ROOT/'tools/ko/cpho/2007/solutions.tsv').read_text(encoding='utf8').splitlines():
        key,ko,en=line.split('\t',2);solutions[key]={'ko':ko,'en':en}
    return theory+[{**e,**solutions[e['id']]}for e in raw['entries']]


def draft():
    data=json.loads((BASE/'slots.json').read_text(encoding='utf8'));old=old_translations();issues=[]
    punct={'，':',','．':'.','。':'.','；':';','（':'(', '）':')','、':',','：':':','！':'!','？':'?'}
    routine={'图':('그림','Fig.'),'表':('표','Table'),'图甲':('그림 (가)','Fig. (a)'),'图乙':('그림 (나)','Fig. (b)'),
        '即':('즉','That is,'),'或':('또는','or'),'或者':('또는','or'),'得':('따라서','giving'),
        '解得':('이를 풀면','Solving gives'),'所以':('따라서','Therefore'),'因此':('따라서','Thus'),
        '于是':('따라서','Hence'),'设':('다음과 같이 두자.','Let'),'代入数据，得':('값을 대입하면','Substituting the data gives')}
    for page in data['pages']:
        source_chars={c['index']:c for c in source_characters(fitz.open(SOURCE)[page['source_page']-1])}
        selected={c['index']for s in page['slots']for c in s['source_characters']if not c['c'].isspace()}
        entries=[e for e in old if e['page']==page['source_page']-1]
        for slot in page['slots']:
            han={c['index']for c in slot['source_characters']if cjk.HAN.search(c['c'])}
            candidates=[]
            for e in entries:
                baselines=e.get('source_row_baselines',[])
                if not any(abs(y-slot['origin'][1])<1.5 for y in baselines):continue
                region=fitz.Rect(e['rect'])
                score=sum(region.contains(fitz.Point(source_chars[idx]['origin']))for idx in han)
                if score:candidates.append((score,e))
            chosen=max(candidates,key=lambda pair:pair[0])[1]if candidates else None
            texts={'ko':'','en':''}
            if chosen:
                e=chosen;native=[];absorbed={};ignored=set()
                for mi,m in enumerate(e['math']):
                    indices=[i for i in m.get('source_char_indices',[])if i in source_chars]
                    glyphs=[source_chars[i]for i in indices if not source_chars[i]['c'].isspace()]
                    if glyphs and all(c['index']in selected for c in glyphs):
                        absorbed[mi]=''.join(c['c']for c in sorted(glyphs,key=lambda c:c['origin'][0]));continue
                    if glyphs and not any(abs(c['origin'][1]-slot['origin'][1])<18 for c in glyphs):ignored.add(mi);continue
                    box=fitz.Rect(m['source_rect']);native.append((mi,box))
                sr=fitz.Rect(slot['source_rect']);left=[(i,r)for i,r in native if r.x1<sr.x0+2]
                right=[(i,r)for i,r in native if r.x0>sr.x1-2]
                previous=max(left,key=lambda pair:pair[1].x1)[0]if left else None
                following=min(right,key=lambda pair:pair[1].x0)[0]if right else None
                for lang in ['ko','en']:
                    value=e[lang]
                    for mi,text in absorbed.items():value=value.replace(f'[[{mi}]]',text)
                    for mi in ignored:value=value.replace(f'[[{mi}]]','')
                    parts=re.split(r'\[\[(\d+)\]\]',value);chunks=[];prev=None
                    for j in range(0,len(parts),2):
                        after=int(parts[j+1])if j+1<len(parts)else None
                        chunks.append((prev,after,parts[j]));prev=after
                    exact=[s for a,b,s in chunks if a==previous and b==following]
                    if len(exact)==1:texts[lang]=exact[0]
                if not all(texts.values()):issues.append({'id':slot['id'],'old_id':e['id'],'previous':previous,'following':following,'note':'Manual source-slot review required'})
            src=slot['source'].strip()
            if src in routine:texts=dict(zip(['ko','en'],routine[src]))
            elif src and all(c in punct or c.isspace()for c in src):
                value=''.join(punct.get(c,c)for c in src);texts={'ko':value,'en':value}
            slot['draft_ko']=texts['ko'];slot['draft_en']=texts['en'];slot['old_entry_id']=chosen['id']if chosen else None
        path=AUTHOR/f'page{page["source_page"]:02}.tsv'
        if not path.exists():path.write_text('\n'.join(s['id']+'\t'+s['draft_ko']+'\t'+s['draft_en']for s in page['slots'])+'\n',encoding='utf8')
    (BASE/'draft-mapping.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    (BASE/'draft-issues.json').write_text(json.dumps(issues,ensure_ascii=False,indent=2),encoding='utf8')
    print('Drafted',sum(len(p['slots'])for p in data['pages']),'slots; mapping warnings',len(issues),flush=True)


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
    result={};cache=EN_REPAIR_ROOT/'2007'/'fonts';cache.mkdir(parents=True,exist_ok=True)
    for (family,bold),text in groups.items():
        if lang=='en':
            source=original_latin_face(2007,family,bold);verify_real_glyphs(source,text)
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
            word_gap=latin_word_gap(s,lang,2007)
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
            matches=list(re.finditer(pattern,text))if any(c['color']==16711935 for c in slot['source_characters'])else[]
            for match in matches:
                if position<match.start():runs.append((text[position:match.start()],0))
                runs.append((match[0],16711935));position=match.end()
            if position<len(text):runs.append((text[position:],0))
            x,y=r['origin']
            for part,color in runs:
                chunks=re.split('( )',part)if r['word_gap_adjustment']else[part]
                for chunk in chunks:
                    if not chunk:continue
                    mode=slot.get('render_mode',0);width=slot.get('line_width')or 0
                    target.insert_text(fitz.Point(x,y),chunk,fontsize=slot['size'],fontname=name,fontfile=str(path),
                        color=tuple(((color>>n)&255)/255 for n in [16,8,0]),fill=tuple(((color>>n)&255)/255 for n in [16,8,0]),
                        render_mode=mode,border_width=width/slot['size']if mode in [1,2]else.05,miter_limit=slot.get('miter_limit',10))
                    x+=font.text_length(chunk,fontsize=slot['size'])+(r['word_gap_adjustment']if chunk==' 'else 0)
    folder=Path(os.environ.get('CPHO_EN_REPAIR_DIR'if lang=='en'else'CPHO_KO_REPAIR_DIR',str(EN_REPAIR_ROOT/'2007'/('preview'if allow_draft else'editions'))));folder.mkdir(parents=True,exist_ok=True)
    part='T'if pages==list(range(1,5))else'TS'if pages==list(range(5,21))else'pages-'+'-'.join(map(str,pages))
    output=folder/f'CPhO_2007_{part}_{lang.upper()}.pdf';doc.save(output,garbage=0,deflate=False);doc.close()
    output.with_suffix('.build.json').write_text(json.dumps({'source_sha256':SOURCE_SHA,'source_pages':pages,'fit_report':rows},ensure_ascii=False,indent=2),encoding='utf8')
    print(output,flush=True);return output


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['extract','draft','preflight','build']);p.add_argument('--pages',nargs='+',type=int);p.add_argument('--lang',choices=['ko','en']);p.add_argument('--draft',action='store_true');args=p.parse_args()
    if args.command=='extract':extract()
    elif args.command=='draft':draft()
    elif args.command=='preflight':preflight(args.pages)
    else:
        for lang in ([args.lang]if args.lang else['ko','en']):
            for pages in ([args.pages]if args.pages else[list(range(1,5)),list(range(5,21))]):compose(lang,pages,args.draft)


if __name__=='__main__':main()
