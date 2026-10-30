"""Reviewable bilingual CJK PDF translation with original mathematical glyphs.

Native Chinese prose is grouped by its visible baselines. Mathematical glyphs
are kept as source outlines, tokenized separately, and never OCR-transcribed.
All extracted entries need reviewed English/Korean text before a final build.
"""
from pathlib import Path
from collections import Counter
import argparse,copy,html,json,math,re,statistics
import pymupdf as fitz
from PIL import Image,ImageChops
import pdf_layout_translate as layout

ROOT=Path(__file__).resolve().parents[1]
HAN=re.compile('[\u3400-\u9fff]')
CJK_FONTS=('SimSun','SimHei','MS PMincho','MS-Mincho','MS-Gothic','MicrosoftYaHei','ËÎÌå')


def natural(ch):
    c=ch['c'];n=ord(c)
    return ch['size']>=9 and (bool(HAN.search(c)) or
        (ch['font'].startswith(CJK_FONTS) and
         (c.isspace() or c in '，。；：！？、（）【】《》“”‘’…—,.():;!?[]' or 0x3000<=n<=0x303f or 0xff00<=n<=0xffef)))


def characters(page):
    result=[]
    for bi,b in enumerate(page.get_text('rawdict')['blocks']):
        if b['type']!=0:continue
        for li,line in enumerate(b['lines']):
            for sp in line['spans']:
                for c in sp['chars']:
                    result.append({**c,'font':sp['font'],'size':sp['size'],'color':sp['color'],
                                   'block':bi,'line':li,'index':len(result)})
    return result


def math_clusters(chars,vertical_limit=15.6,horizontal_limit=3.4):
    """Connect neighboring mathematical characters, including fraction levels."""
    chars=[c for c in chars if not natural(c) and not c['c'].isspace()]
    parent=list(range(len(chars)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    cells={}
    for i,c in enumerate(chars):
        x,y=c['origin'];key=(int(x//18),int(y//18));r=fitz.Rect(c['bbox'])
        for gx in range(key[0]-2,key[0]+3):
            for gy in range(key[1]-1,key[1]+2):
                for j in cells.get((gx,gy),[]):
                    b=chars[j];bx,by=b['origin'];br=fitz.Rect(b['bbox'])
                    horizontal=max(r.x0,br.x0)-min(r.x1,br.x1)
                    if (abs(y-by)<5 and horizontal<horizontal_limit) or (abs(y-by)<vertical_limit and horizontal<-.4):
                        parent[root(i)]=root(j)
        cells.setdefault(key,[]).append(i)
    groups={}
    for i,c in enumerate(chars):groups.setdefault(root(i),[]).append(c)
    result=[]
    for group in groups.values():
        bounds=fitz.Rect(group[0]['bbox'])
        for c in group[1:]:bounds|=fitz.Rect(c['bbox'])
        result.append({'chars':group,'rect':list(bounds),
           'x':min(c['origin'][0] for c in group),'y':statistics.median(c['origin'][1] for c in group),
           'text':''.join(c['c'] for c in sorted(group,key=lambda c:(round(c['origin'][1]/5)*5,c['origin'][0])))})
    return result


def prose_rows(chars):
    rows=[]
    for c in sorted((c for c in chars if natural(c) and HAN.search(c['c'])),key=lambda c:(c['origin'][1],c['origin'][0])):
        x,y=c['origin'];row=next((r for r in rows[-4:] if abs(r['baseline']-y)<1.3),None)
        if row is None:row={'baseline':y,'chars':[]};rows.append(row)
        row['chars'].append(c)
    # Natural punctuation belongs to the matching visible Chinese baseline.
    used={c['index'] for r in rows for c in r['chars']}
    for c in chars:
        if c['index'] in used or not natural(c):continue
        x,y=c['origin'];candidates=[r for r in rows if abs(r['baseline']-y)<1.3 and
           (any(z['block']==c['block'] and z['line']==c['line'] for z in r['chars']) or
            min(z['origin'][0] for z in r['chars'])-32<=x<=max(z['bbox'][2] for z in r['chars'])+18)]
        if candidates:min(candidates,key=lambda r:abs(r['baseline']-y))['chars'].append(c)
    for row in rows:
        row['chars'].sort(key=lambda c:c['origin'][0]);row['math']=[]
        bounds=fitz.Rect(row['chars'][0]['bbox'])
        for c in row['chars'][1:]:bounds|=fitz.Rect(c['bbox'])
        row['rect']=list(bounds);row['size']=statistics.median(c['size'] for c in row['chars'])
        row['plain']=''.join(c['c'] for c in row['chars']).strip()
    return sorted(rows,key=lambda r:(r['baseline'],r['rect'][0]))


def attach_math(rows,chars):
    # Assign glyphs to the gaps between Chinese words before joining fraction
    # levels. Otherwise vertically adjacent math in two prose lines can merge.
    selected={id(row):[] for row in rows};blocks={}
    for ch in chars:
        if not natural(ch) and not ch['c'].isspace():blocks.setdefault(ch['block'],[]).append(ch)
    def eligible(row,items):
        if row['plain'] in {'提示：','参考解答：'}:return False
        for ch in items:
            x,y=ch['origin'];width=min(ch['size']*1.1,fitz.Rect(ch['bbox']).width);cx=x+width*.4
            if abs(row['baseline']-y)>20 or not row['rect'][0]-100<=x<=min(528,row['rect'][2]+45):return False
            if any(c['bbox'][0]+.4<cx<c['bbox'][2]-.4 for c in row['chars'] if HAN.search(c['c'])):return False
        return True
    ordered=sorted(blocks.items(),key=lambda pair:(
        not any(c['block']==pair[0] for r in rows for c in r['chars']),
        -max(c['size'] for c in pair[1])))
    for block,items in ordered:
        owners=[row for row in rows if any(c['block']==block for c in row['chars'])]
        # First connect only within a native PDF block. Different prose lines
        # must not bridge through raised/lowered script characters. Each local
        # expression is then assigned atomically to a Chinese baseline.
        portions=[c['chars'] for c in math_clusters(items,vertical_limit=14)] if owners else [items]
        for portion in portions:
            choices=[row for row in (owners or rows) if eligible(row,portion)]
            if not owners:
                choices=[row for row in choices if max(c['size'] for c in portion)>=row['size']*.85 or
                    any(abs(c['origin'][0]-p['origin'][0])<20 and abs(c['origin'][1]-p['origin'][1])<9
                        for c in portion for p in selected[id(row)])]
            if choices:
                row=min(choices,key=lambda row:abs(row['baseline']-statistics.median(ch['origin'][1] for ch in portion)))
                selected[id(row)].extend(portion)
    for row in rows:
        fields=math_clusters(selected[id(row)],vertical_limit=28,horizontal_limit=5)
        fields.sort(key=lambda m:m['rect'][0]);joined=[]
        for field in fields:
            previous=joined[-1] if joined else None
            if previous:
                gap=field['rect'][0]-previous['rect'][2]
                separated=any(previous['rect'][2]-.5<(c['bbox'][0]+c['bbox'][2])/2<field['rect'][0]+.5
                              for c in row['chars'])
                if gap<12 and not separated:
                    previous['chars'].extend(field['chars'])
                    previous['rect']=list(fitz.Rect(previous['rect'])|fitz.Rect(field['rect']))
                    previous['text']+=' '+field['text'];continue
            joined.append(field)
        for m in joined:
            row['math'].append(m);rect=fitz.Rect(m['rect'])
            if rect.height>50:rect=fitz.Rect(rect.x0,m['y']-25,rect.x1,m['y']+20)
            row['rect']=list(fitz.Rect(row['rect'])|rect)


def paragraphs(rows):
    groups=[]
    for row in rows:
        candidates=[g for g in groups if 0<row['baseline']-g[-1]['baseline']<row['size']*1.9 and
                    abs(row['rect'][0]-g[-1]['rect'][0])<25]
        previous=max(candidates,key=lambda g:g[-1]['baseline'])[-1] if candidates else None
        hard_start=bool(re.match(r'^(?:[一二三四五六七八九十]+、|[（(]|参考解答|评分参考|第[（(]|【)',row['plain']))
        combine=previous is not None and not hard_start and \
            0<row['baseline']-previous['baseline']<row['size']*1.9 and \
            abs(row['rect'][0]-previous['rect'][0])<25 and \
            not (previous['rect'][2]<400 and row['rect'][2]>450)
        if combine:next(g for g in groups if g[-1] is previous).append(row)
        else:groups.append([row])
    return groups


def math_image(svg,cluster,target):
    allowed=[c['origin'] for c in cluster['chars']]
    def keep(m):
        transform=re.search(r'transform="matrix\(([^)]+)\)"',m[0])
        if not transform:return ''
        values=[float(x) for x in transform[1].split(',')]
        return m[0] if any(abs(values[-2]-x)<.025 and abs(values[-1]-y)<.025 for x,y in allowed) else ''
    # SVG→PDF currently mishandles some Word auxiliary-image soft masks.
    # Mathematical symbols are native glyphs/paths; raster figures do not
    # belong in inline math sprites.
    image_ids=re.findall(r'<image\b[^>]*\bid="([^"]+)"',svg)
    filtered=re.sub(r'<image\b[^>]*?/?>','',svg)
    filtered=re.sub(r'<path\b[^>]*fill="#ffffff"[^>]*?/?>','',filtered)
    for image_id in image_ids:
        filtered=re.sub(r'<use\b[^>]*href="#'+re.escape(image_id)+r'"[^>]*?/?>','',filtered)
    filtered=re.sub(r'<use\b[^>]*data-text=[^>]*?/?>',keep,filtered)
    rect=fitz.Rect(cluster['rect']);cy=cluster['y']
    if rect.height>50:rect=fitz.Rect(rect.x0,cy-18,rect.x1,cy+12)
    rect+=(-1,-5,1,7)
    filtered=re.sub(r'width="[^"]+"',f'width="{rect.width}"',filtered,count=1)
    filtered=re.sub(r'height="[^"]+"',f'height="{rect.height}"',filtered,count=1)
    filtered=re.sub(r'viewBox="[^"]+"',f'viewBox="{rect.x0} {rect.y0} {rect.width} {rect.height}"',filtered,count=1)
    picture=fitz.open(stream=filtered.encode('utf8'),filetype='svg')
    pdf=fitz.open(stream=picture.convert_to_pdf(),filetype='pdf');pix=pdf[0].get_pixmap(matrix=fitz.Matrix(4,4),alpha=True)
    image=Image.frombytes('RGBA',[pix.width,pix.height],pix.samples)
    mask=image.convert('RGB').convert('L').point(lambda v:255 if v<170 else 0)
    # Ignore nearly transparent Word object-boundary hairlines when finding
    # visible ink. They otherwise make a single digit look 20 points tall.
    alpha=image.getchannel('A').point(lambda v:255 if v>60 else 0)
    mask=ImageChops.multiply(mask,alpha);ink=mask.getbbox()
    if ink:
        box=(max(0,ink[0]-2),max(0,ink[1]-2),min(image.width,ink[2]+2),min(image.height,ink[3]+2))
        rect.x0+=box[0]/4;rect.y0+=box[1]/4;rect.x1=rect.x0+(box[2]-box[0])/4;rect.y1=rect.y0+(box[3]-box[1])/4
        image=image.crop(box)
    image.save(target)
    return {'file':target.name,'width':image.width/4,'height':image.height/4,
            'source_rect':list(rect),'source_text':cluster['text'],'glyph_origins':allowed,
            'source_char_indices':[c['index'] for c in cluster['chars']]}


def extract(source,folder,pages=None,regions=None):
    folder.mkdir(parents=True,exist_ok=True);doc=fitz.open(source);entries=[];report=[]
    exclusions=json.loads(regions.read_text(encoding='utf8')).get('exclude',[]) if regions else []
    for pi,page in enumerate(doc):
        if pages and pi+1 not in pages:continue
        chars=characters(page)
        omitted=[fitz.Rect(r['rect']) for r in exclusions if r['page']==pi+1]
        chars=[c for c in chars if not any(r.contains(fitz.Point(c['origin'])) for r in omitted)]
        rows=prose_rows(chars);attach_math(rows,chars)
        svg=page.get_svg_image(text_as_path=True);groups=paragraphs(rows)
        for gi,group in enumerate(groups):
            maths=[];source_rows=[];bounds=fitz.Rect(group[0]['rect'])
            for row in group:
                bounds|=fitz.Rect(row['rect']);pieces=[(c['origin'][0],c['c']) for c in row['chars']]
                for m in row['math']:
                    index=len(maths);name=f'{pi+1}-{gi}-m{index}.png'
                    maths.append(math_image(svg,m,folder/name));pieces.append((m['x'],f'[[{index}]]'))
                source_rows.append(''.join(t for x,t in sorted(pieces,key=lambda z:z[0])))
            entry={'id':f'{pi+1}-{gi}','page':pi,'rect':list(bounds),'size':group[0]['size'],
                   'source':' '.join(source_rows),'math':maths,'ko':'','en':'',
                   'color':Counter(c['color'] for row in group for c in row['chars']).most_common(1)[0][0],
                   'source_row_baselines':[r['baseline'] for r in group]}
            taken={idx for m in maths for idx in m['source_char_indices']}
            entry['review_uncovered_math']=[{'text':c['c'],'origin':c['origin'],'font':c['font'],'size':c['size']}
                for c in chars if not natural(c) and not c['c'].isspace() and c['index'] not in taken and bounds.contains(fitz.Point(c['origin']))]
            entries.append(entry)
        report.append({'page':pi+1,'prose_rows':len(rows),'paragraphs':len(groups),
           'inline_math_clusters':sum(len(r['math']) for r in rows),'main_chinese_characters':sum(bool(HAN.search(c['c'])) and natural(c) for c in chars)})
        print(f'{pi+1}/{len(doc)}: {len(rows)} prose rows, {len(groups)} paragraphs',flush=True)
    data={'source':str(source.resolve()),'page_count':len(doc),'source_mode':'native_with_math_restoration',
          'source_exclusions':exclusions,'entries':entries,'extraction_report':report}
    (folder/'translation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    (folder/'source.txt').write_text('\n'.join(f'{e["id"]}|{e["source"]}' for e in entries),encoding='utf8')
    return data


def restore_math(page,original,source_chars,excluded):
    """Restore original mathematical outlines deleted by oversized metrics.

    Native raster soft masks and vector rules stay in the original PDF. Only
    untranslated mathematical glyph paths are copied, without SVG images.
    """
    remaining={}
    for c in characters(page):remaining.setdefault(c['c'],[]).append(c['origin'])
    allowed=[c['origin'] for c in source_chars if not natural(c) and not c['c'].isspace() and c['index'] not in excluded
       and not any(abs(c['origin'][0]-x)<.025 and abs(c['origin'][1]-y)<.025 for x,y in remaining.get(c['c'],[]))]
    if not allowed:return
    svg=original.get_svg_image(text_as_path=True);defs=re.search(r'<defs>[\s\S]*?</defs>',svg)[0]
    defs=re.sub(r'<image\b[^>]*?/?>','',defs)
    uses=[]
    for item in re.findall(r'<use\b[^>]*data-text=[^>]*?/?>',svg):
        trans=re.search(r'transform="matrix\(([^)]+)\)"',item)
        if not trans:continue
        v=[float(x) for x in trans[1].split(',')]
        if any(abs(v[-2]-x)<.025 and abs(v[-1]-y)<.025 for x,y in allowed):uses.append(item)
    picture=f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{page.rect.width}" height="{page.rect.height}" viewBox="0 0 {page.rect.width} {page.rect.height}">{defs}'+''.join(uses)+'</svg>'
    shape=fitz.open(stream=picture.encode('utf8'),filetype='svg');vector=fitz.open(stream=shape.convert_to_pdf(),filetype='pdf')
    page.show_pdf_page(page.rect,vector,0)


def build(folder,target,lang,pages=None):
    data=json.loads((folder/'translation.json').read_text(encoding='utf8'));entries=data['entries']
    if pages:entries=[e for e in entries if e['page']+1 in pages]
    elif {p['page'] for p in data['extraction_report']}!=set(range(1,data['page_count']+1)):
        raise ValueError('Partial extraction: specify preview --pages or extract every source page')
    missing=[e['id'] for e in entries if not e.get(lang,'').strip()]
    if missing:raise ValueError('Missing translations: '+', '.join(missing))
    unresolved=[e['id'] for e in entries if e.get('review_uncovered_math') and not e.get('math_reviewed')]
    if unresolved:raise ValueError('Review uncovered source math before building: '+', '.join(unresolved))
    original=fitz.open(data['source']);doc=fitz.open(data['source']);archive=fitz.Archive(str(folder.resolve()))
    for asset_root in data.get('asset_roots',[]):archive.add(asset_root)
    archive.add(str(layout.FONT.parent));body_font='NotoSansKR-Regular.ttf'
    serif=Path('C:/Windows/Fonts/times.ttf')
    if lang=='en' and serif.exists():archive.add(str(serif.parent));body_font=serif.name
    css=f'''@font-face{{font-family:Body;src:url({body_font});}}
      @font-face{{font-family:Korean;src:url(NotoSansKR-Regular.ttf);}}
      *{{font-family:Body,Korean;color:#000;}}body,p{{margin:0;padding:0;}}img{{vertical-align:middle;}}'''
    report=[]
    for pi,page in enumerate(doc):
        if pages and pi+1 not in pages:continue
        active=[e for e in entries if e['page']==pi]
        for e in active:
            for rect in e.get('erase_rects',[e['rect']]):page.add_redact_annot(fitz.Rect(rect),fill=e.get('fill',(1,1,1)))
        page.apply_redactions(images=0,graphics=0)
        excluded={i for e in active for mi,m in enumerate(e['math']) if mi not in e.get('preserved_math',[])
                  for i in m.get('source_char_indices',[])}
        restore_math(page,original[pi],characters(original[pi]),excluded)
        for e in active:
            expected=Counter(re.findall(r'\[\[\d+\]\]',e['source']));actual=Counter(re.findall(r'\[\[\d+\]\]',e[lang]))
            for mi in e.get('preserved_math',[]):del expected[f'[[{mi}]]']
            if expected!=actual:raise ValueError(f'Math token mismatch {e["id"]}/{lang}')
            text=html.escape(e[lang]);maths=e['math'];max_height=0
            for mi,m in enumerate(maths):
                if mi in e.get('preserved_math',[]):continue
                factor=min(1,e.get('math_cap',26)/m['height']);w,h=m['width']*factor,m['height']*factor;max_height=max(max_height,h)
                text=text.replace(f'[[{mi}]]',f'<img src="{m["file"]}" width="{w}" height="{h}">')
            height=e.get('line_height',max(1.25,(max_height+2)/e['size']))
            rect=fitz.Rect(e.get(f'{lang}_insert_rect',e.get('insert_rect',e['rect'])));rect.y0-=.7;rect.y1+=1
            color=e.get('color',0);color=f'#{color:06x}' if isinstance(color,int) else color
            spare,scale=page.insert_htmlbox(rect,f'<p style="font-size:{e["size"]}pt;line-height:{height};color:{color};text-align:{e.get("align","left")}">{text}</p>',
                 css=css,archive=archive,scale_low=.7)
            report.append({'id':e['id'],'scale':scale,'spare':spare})
            if spare<0:raise ValueError(f'Text does not fit {e["id"]}/{lang}')
    if pages:doc.select([n-1 for n in pages])
    target.parent.mkdir(parents=True,exist_ok=True);doc.save(target,garbage=4,deflate=True)
    target.with_suffix('.qa.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(f'Built {target}: {len(report)} regions, minimum scale {min(e["scale"] for e in report):.3f}')


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('extract');a.add_argument('source',type=Path);a.add_argument('folder',type=Path);a.add_argument('--pages',type=int,nargs='*');a.add_argument('--regions',type=Path)
    a=sub.add_parser('build');a.add_argument('folder',type=Path);a.add_argument('target',type=Path);a.add_argument('--lang',choices=['ko','en'],required=True);a.add_argument('--pages',type=int,nargs='*')
    args=p.parse_args()
    if args.command=='extract':extract(args.source,args.folder,args.pages,args.regions)
    else:build(args.folder,args.target,args.lang,args.pages)
