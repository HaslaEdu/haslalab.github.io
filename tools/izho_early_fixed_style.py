"""Reviewed, fixed-baseline IZhO prose replacement; source math stays native.

Each JSON slot explicitly names source spans (nonempty-span indices). No prose
classifier is used for publication. No shrinking, wrapping, line movement,
paragraph merging, source font subsetting, or equation rasterization occurs.
"""
from pathlib import Path
from collections import defaultdict
import argparse,hashlib,json,math,re
import pikepdf
import pymupdf as fitz
from pdf_original_text_ops import suppress_prose,glyph_key,family_name,cmap,widths,native_form_glyphs
from pdf_original_style_fonts import korean_font,source_font_role
from pdf_original_style_audit import audit

ROOT=Path(__file__).resolve().parents[1]

def runs_of(page):
    names={t['font']for t in page.get_texttrace()};result={}
    for bi,b in enumerate(page.get_text('rawdict')['blocks']):
        if b['type']:continue
        for li,line in enumerate(b['lines']):
            si=0
            for span in line['spans']:
                text=''.join(c['c']for c in span['chars'])
                if not text.strip():continue
                name=span['font']
                if name not in names:
                    matches=[v for v in names if v.startswith(name)]
                    if len(matches)!=1:raise ValueError(('Unresolved source font',name,matches))
                    name=matches[0]
                result[bi,li,si]={**span,'text':text,'font':name};si+=1
    return result

def characters(span):return [dict(c,font=span['font'],size=span['size'])for c in span['chars']]

def slot_source(spec,runs):
    first=tuple(spec['at']);last=tuple(spec.get('through',first))
    if first[:2]!=last[:2]:raise ValueError('A slot may not merge source lines')
    group=[runs[(first[0],first[1],i)]for i in range(first[2],last[2]+1)]
    if max(abs(s['origin'][1]-group[0]['origin'][1])for s in group)>.02:raise ValueError('Mixed source baselines')
    selected=[c for span in group for c in characters(span)]
    if 'substring'in spec:
        if first!=last:raise ValueError('Substring slot must be a single source span')
        text=group[0]['text'];start=text.index(spec['substring']);selected=selected[start:start+len(spec['substring'])]
    if 'range'in spec:selected=selected[spec['range'][0]:spec['range'][1]]
    if not selected:raise ValueError('Empty selected source slot')
    text=''.join(c['c']for c in selected)
    if 'source_text'in spec and spec['source_text']!=text:raise ValueError(('Stale reviewed slot',spec['at'],spec['source_text'],text))
    rect=fitz.Rect(selected[0]['bbox'])
    for ch in selected[1:]:rect|=fitz.Rect(ch['bbox'])
    if 'right'in spec:
        if spec['right']<rect.x1-.02:raise ValueError('Reviewed slot may not truncate original source')
        rect.x1=spec['right']
    return group[0],selected,rect,(selected[0]['origin'][0],group[0]['origin'][1])

def font_catalog(source,page_number,trace_names):
    result=defaultdict(list)
    with pikepdf.Pdf.open(source)as pdf:
        for name,font in pdf.pages[page_number-1].Resources.Font.items():
            encoding=str(font.get('/Encoding'))
            if encoding not in ['/WinAnsiEncoding','/Identity-H']:continue
            full=family_name(bytes(font.get('/BaseFont')).decode('latin1'))
            aliases=[full]if full in trace_names else [n for n in trace_names if full.startswith(n)or n.startswith(full)]
            if len(aliases)!=1:continue
            ws,default=widths(font);mapping=cmap(font);inverse={}
            for code,char in mapping.items():
                if len(char)==1:inverse.setdefault(char,code)
            descriptor=font.get('/FontDescriptor')
            if descriptor is None and '/DescendantFonts'in font:descriptor=font.DescendantFonts[0].get('/FontDescriptor')
            angle=float(descriptor.get('/ItalicAngle',-15))if descriptor is not None else -15
            result[aliases[0]].append(dict(alias=str(name).lstrip('/'),encoding=inverse,widths=ws,default=default,
                bytes=1 if encoding=='/WinAnsiEncoding'else 2,angle=angle))
    for values in result.values():values.sort(key=lambda v:v['bytes'])
    return result

def latin_profile(catalog,font,text):
    for profile in catalog[font]:
        if all(ch in profile['encoding']and profile['widths'].get(profile['encoding'][ch],profile['default'])is not None for ch in text):return profile
    raise ValueError(('No source-native encoding for prose',font,text))

def split_parts(part,style,catalog,metrics):
    """Use the original Latin font; use the matched CJK face for Hangul only."""
    text=part['text'];chunks=[];groups=[]
    for char in text:
        native=ord(char)<128 or (not '\uac00'<=char<='\ud7a3'and any(char in p['encoding']and p['widths'].get(p['encoding'][char],p['default'])is not None for p in catalog[style['font']]))
        if groups and groups[-1][0]==native:groups[-1][1]+=char
        else:groups.append([native,char])
    for native,value in groups:
        if native:
            profile=latin_profile(catalog,style['font'],value)
            codes=[profile['encoding'][c]for c in value]
            advance=sum(profile['widths'].get(c,profile['default'])for c in codes)*style['size']/1000
            chunks.append(dict(text=value,native=True,profile=profile,codes=codes,advance=advance,style=style))
        else:
            role=source_font_role(style['font'],style['flags']);metric=metrics[role]
            chunks.append(dict(text=value,native=False,role=role,advance=metric.text_length(value,fontsize=style['size']),style=style))
    return chunks

def build(plan_path,target):
    plan_path=Path(plan_path);data=json.loads(plan_path.read_text('utf8'));source=ROOT/data['source'];pi=data['page']
    original=fitz.open(source);page=original[pi]
    if page.rotation:raise ValueError('Rotated source needs a reviewed page transform')
    runs=runs_of(page);selected=[];work=[];all_text=defaultdict(str)
    for spec in data['slots']:
        anchor,chars,rect,point=slot_source(spec,runs);selected.extend(chars)
        parts=spec.get('parts',[{'text':spec.get('text','')}])
        for part in parts:
            style=runs[tuple(part.get('style_from',spec['at']))]
            if abs(style['size']-anchor['size'])>.001:raise ValueError('Mixed-size slot requires separate source slots')
            all_text[source_font_role(style['font'],style['flags'])]+=part['text']
        work.append((spec,anchor,chars,rect,point,parts))
    selected_keys=[glyph_key(c)for c in selected if c['c'].strip()]
    if len(set(selected_keys))!=len(selected_keys):raise ValueError('Overlapping reviewed source slots')
    # Mandatory human-reviewed formula protection can be added independently
    # of prose slots. Selection touching any protected glyph is a hard failure.
    form_glyphs=native_form_glyphs(source,pi+1)
    protected=form_glyphs+[c for span in runs.values()if re.search(r'Cambria.?Math|Symbol|MT.?Extra',span['font'],re.I) for c in characters(span)if c['c'].strip()]
    for key in data.get('protected_runs',[]):protected.extend(c for c in characters(runs[tuple(key)])if c['c'].strip())
    for query in data.get('protect_text',[]):
        hits=page.search_for(query)
        if not hits:raise ValueError(('Protected native formula not found',query))
        for span in runs.values():
            for c in characters(span):
                if c['c'].strip()and any(fitz.Rect(c['bbox']).intersects(r)for r in hits):protected.append(c)
    if set(selected_keys)&{glyph_key(c)for c in protected}:raise ValueError('Reviewed prose selection touches protected math')
    untranslated=[]
    for key,span in runs.items():
        if re.search(r'Cambria.?Math|Symbol|MT.?Extra',span['font'],re.I):continue
        remaining=''.join(c['c']if glyph_key(c)not in selected_keys and not any(c['font']==g['font']and abs(c['origin'][0]-g['origin'][0])<.0001 and abs(c['origin'][1]-g['origin'][1])<.0001 for g in form_glyphs)else ' 'for c in characters(span))
        words=re.findall(r'[A-Za-z]{3,}',remaining)
        if words and list(key)not in data.get('native_text_exceptions',[]):untranslated.append(dict(at=key,remaining=remaining))
    if untranslated:raise ValueError('Unreviewed English source prose: '+repr(untranslated))
    buffers={};metrics={}
    for role,text in all_text.items():
        _,path=korean_font('',0,text,override=role,cache_dir=ROOT/'tmp/izho-original-style/fonts')
        buffers[role]=path;metrics[role]=fitz.Font(fontfile=str(path))
    raw,count=suppress_prose(source,pi+1,selected);outdoc=fitz.open(stream=raw,filetype='pdf');out=outdoc[0];out.wrap_contents()
    for role,path in buffers.items():out.insert_font(fontname='KO_'+role.replace('-','_'),fontfile=str(path))
    catalog=font_catalog(source,pi+1,{t['font']for t in page.get_texttrace()});placements=[];allowed=[];overflows=[]
    for spec,anchor,chars,rect,point,parts in work:
        chunks=[]
        for part in parts:chunks.extend(split_parts(part,runs[tuple(part.get('style_from',spec['at']))],catalog,metrics))
        width=sum(c['advance']for c in chunks)
        if width>rect.width+.05:
            overflows.append(dict(at=spec['at'],width=width,available=rect.width,text=''.join(p['text']for p in parts)));continue
        x,y=point
        if spec.get('align')=='center':x=(rect.x0+rect.x1-width)/2
        start=x;placement_parts=[]
        for chunk in chunks:
            style=chunk['style'];size=style['size'];color=tuple(((style['color']>>n)&255)/255 for n in [16,8,0])
            if chunk['native']:
                profile=chunk['profile'];pdfpoint=fitz.Point(x,y)*~out.transformation_matrix
                encoded=b''.join(code.to_bytes(profile['bytes'],'big')for code in chunk['codes']).hex()
                stream=f'q BT /{profile["alias"]} {size:.9f} Tf 0 Tc 0 Tw 0 Tr {color[0]:.6f} {color[1]:.6f} {color[2]:.6f} rg 1 0 0 1 {pdfpoint.x:.8f} {pdfpoint.y:.8f} Tm <{encoded}> Tj ET Q'.encode('ascii')
                xref=outdoc.get_new_xref();outdoc.update_object(xref,'<<>>');outdoc.update_stream(xref,stream)
                refs=out.get_contents()+[xref];outdoc.xref_set_key(out.xref,'Contents','['+' '.join(f'{r} 0 R'for r in refs)+']')
                font=style['font'];angle=0
            else:
                angle=abs(catalog[style['font']][0]['angle'])if style['flags']&2 else 0
                morph=(fitz.Point(x,y),fitz.Matrix(1,0,math.tan(math.radians(angle)),1,0,0))if angle else None
                font='KO_'+chunk['role'].replace('-','_');out.insert_text((x,y),chunk['text'],fontname=font,fontsize=size,color=color,morph=morph)
            placement_parts.append(dict(text=chunk['text'],font=font,source_font=style['font'],size=size,point=[x,y],oblique_angle=angle))
            x+=chunk['advance']
        # Source ink may exceed its font's declared bbox; one point contains
        # original italic overhang without extending into another native slot.
        allowed.append(list(rect+(-1,-1,1,1)))
        allowed.append([rect.x0-2,y-anchor['size']-1,rect.x1+2,y+anchor['size']*.32])
        placements.append(dict(at=spec['at'],source_text=''.join(c['c']for c in chars),text=''.join(p['text']for p in parts),
            source_font=anchor['font'],size=anchor['size'],source_baseline=anchor['origin'][1],point=[start,y],width=width,available=rect.width,parts=placement_parts))
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    if overflows:
        target.with_suffix('.overflow.json').write_text(json.dumps(overflows,ensure_ascii=False,indent=2),'utf8');outdoc.close()
        raise ValueError('Fixed-size Korean overflows: '+json.dumps(overflows,ensure_ascii=False))
    outdoc.save(target,garbage=4,deflate=True);outdoc.close()
    spec=dict(source_page=pi+1,proof_page=1,allowed_rects=allowed,erased_glyph_origins=[list(c['origin'])for c in selected if c['c'].strip()],
        protected_glyph_origins=[list(c['origin'])for c in protected],protected_glyphs=protected,
        protected_rects=[list(info['bbox'])for info in page.get_image_info()])
    target.with_suffix('.audit-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),'utf8')
    result=audit(source,target,spec);result.update(removed_prose_glyphs=count,placements=placements,autoshrink=False,reflow=False,equation_images=0,
        plan=str(plan_path.relative_to(ROOT))if plan_path.is_absolute()else str(plan_path),plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest())
    target.with_suffix('.qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    final=fitz.open(target)
    def font_programs(doc,pg):
        return [(resource,name,kind,encoding,hashlib.sha256(doc.extract_font(xref)[3]).hexdigest())
                for xref,extension,kind,name,resource,encoding,*rest in pg.get_fonts(full=True)]
    source_fonts=font_programs(original,page);target_fonts=font_programs(final,final[0])
    result['source_font_programs_and_names_unchanged']=all(row in target_fonts for row in source_fonts)
    def image_objects(pg):return sorted((im['digest'].hex(),tuple(im['bbox']))for im in pg.get_image_info(hashes=True))
    result['source_images_bytes_and_rects_unchanged']=image_objects(page)==image_objects(final[0])
    # seqno counts preceding text paints; deleting prose changes that counter,
    # while every path command/style/coordinate and vector order stays native.
    def drawings(pg):return [{k:v for k,v in row.items()if k!='seqno'}for row in pg.get_drawings()]
    result['source_vector_drawings_unchanged']=drawings(page)==drawings(final[0])
    result['unreviewed_english_prose_runs']=untranslated
    for name,pg in [('source',page),('proof',final[0])]:pg.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(target.with_name(target.stem+'-'+name+'.png'))
    final.close();original.close()
    target.with_suffix('.qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps({k:v for k,v in result.items()if k not in ['placements','native_glyphs_changed']},ensure_ascii=False),flush=True)
    if result['native_glyphs_changed']or result['protected_glyphs_selected_for_erasure']or result['changed_pixels_outside_prose']or result['changed_pixels_in_native_glyph_neighborhood']or not result['source_font_programs_and_names_unchanged']or not result['source_images_bytes_and_rects_unchanged']or not result['source_vector_drawings_unchanged']:raise ValueError('Native original-style audit failed')
    return result

def inventory(source,page_number,target):
    doc=fitz.open(source);runs=runs_of(doc[page_number-1]);data={','.join(map(str,k)):{key:s[key]for key in ['text','font','size','flags','color','origin','bbox']}for k,s in runs.items()}
    Path(target).parent.mkdir(parents=True,exist_ok=True);Path(target).write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf8');doc.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--inventory',type=Path);p.add_argument('--page',type=int,default=1);a=p.parse_args()
    if a.inventory:inventory(a.inventory,a.page,a.out)
    else:build(a.plan,a.out)
