"""Fixed-size Korean replacement in exact source LaTeX prose slots.

Plans use one-based page and inclusive rawdict span ranges [block,line,s0,s1].
Optional char_start/char_end slice the flattened source span characters.
Only selected source text-show bytes are suppressed; source resources, page
geometry, equations, drawing/image objects and all unselected text stay native.
"""
from pathlib import Path
from io import BytesIO
from collections import Counter,defaultdict
import argparse,hashlib,json,math,re
import pikepdf
import pymupdf as fitz
import numpy as np
from fontTools import subset
from fontTools.ttLib import TTFont
import pdf_latex_text_ops as ops

BASE=Path(__file__).resolve().parents[1]
FONT_DIR=Path('D:/CodexBuilds/Hasla-publish-20261031/tools/ko/fonts')
FONTS={'serif':FONT_DIR/'NotoSerifCJKkr-Regular.otf','serif-bold':FONT_DIR/'NotoSerifCJKkr-Bold.otf',
       'sans':FONT_DIR/'NotoSansCJKkr-Regular.otf','sans-bold':FONT_DIR/'NotoSansCJKkr-Bold.otf'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def source_records(page,include_hidden=False):
    return [dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(origin),bbox=list(bbox))
            for t in page.get_texttrace()if include_hidden or t['type']!=3 for cp,gid,origin,bbox in t['chars']]

def canonical_selected(page,selected):
    """Map rawdict's distributed ligature chars to exact source trace records.

    MuPDF rawdict gives the i in fi an artificial x partway through the glyph;
    texttrace has the same logical Unicode sequence, with a gid=-1 zero-width
    continuation at the painted glyph's origin. Pair complete per-font source
    sequences and verify every identity, baseline and continuation bound.
    """
    traced=defaultdict(list);raw=defaultdict(list)
    for r in source_records(page):
        if not r['c'].isspace():traced[ops.family_name(r['font'])].append(r)
    for b in page.get_text('rawdict')['blocks']:
        if b['type']!=0:continue
        for line in b['lines']:
            for s in line['spans']:
                for c in s['chars']:
                    if not c['c'].isspace():raw[ops.family_name(s['font'])].append(dict(c,font=s['font'],size=s['size']))
    needed={ops.family_name(c['font'])for c in selected if not c['c'].isspace()};mapping=defaultdict(list)
    for family in needed:
        aa,bb=raw[family],traced[family]
        if len(aa)!=len(bb):raise ValueError('Rawdict/trace logical count differs for '+family)
        painted=None
        for a,b in zip(aa,bb):
            if a['c']!=b['c']or abs(a['size']-b['size'])>.00001 or abs(a['origin'][1]-b['origin'][1])>.00013:
                raise ValueError('Rawdict/trace logical source sequence differs for '+family)
            delta=abs(a['origin'][0]-b['origin'][0])
            if b['gid']>=0:painted=b
            if delta>.00013:
                # Type1 trace bbox uses the font's floored unit metric while
                # rawdict continuation x uses the rounded PDF advance. Allow
                # their documented two-font-unit quantization only here.
                if b['gid']!=-1 or painted is None or b['origin']!=painted['origin']or not painted['bbox'][0]-.00013<=a['origin'][0]<=painted['bbox'][2]+painted['size']*.002+.00013:
                    raise ValueError('Rawdict source position differs outside a verified ligature continuation: '+repr((a,b,painted)))
            mapping[ops.glyph_key(a)].append(b)
    result=[]
    for a in selected:
        if a['c'].isspace():continue
        candidates=mapping[ops.glyph_key(a)]
        if not candidates:raise ValueError('Selected source record is absent from verified rawdict/trace map')
        result.append(candidates.pop(0))
    return result

def compare_native(expected,actual,tolerance=.00013):
    groups=defaultdict(list)
    for r in actual:groups[(r['c'],r['gid'],r['font'],r['size'])].append(r)
    missing=[];max_delta=0
    for r in expected:
        candidates=groups[(r['c'],r['gid'],r['font'],r['size'])]
        if not candidates:missing.append(r);continue
        candidate=min(candidates,key=lambda z:max(abs(a-b)for a,b in zip(z['origin'],r['origin'])))
        delta=max(abs(a-b)for a,b in zip(candidate['origin'],r['origin']))
        if delta>tolerance:missing.append(r);continue
        max_delta=max(max_delta,delta);candidates.remove(candidate)
    return dict(missing=missing,extra=sum(map(len,groups.values())),max_delta_pt=max_delta)

def font_programs(doc,page):
    return {(item[3],hashlib.sha256(doc.extract_font(item[0])[3]).hexdigest())for item in page.get_fonts(full=True)}

def native_images(page):
    return Counter((x['digest'].hex(),tuple(x['bbox']),tuple(x['transform']))for x in page.get_image_info(hashes=True))

def encoded_images(doc,page):
    result=Counter()
    for image in page.get_images(full=True):
        xref,smask=image[:2]
        for role,ref in(('image',xref),('softmask',smask)):
            if not ref:continue
            result[(role,hashlib.sha256(doc.xref_stream_raw(ref)).hexdigest(),doc.xref_get_key(ref,'Filter'))]+=1
    return result

def drawings(page):
    return [{k:v for k,v in d.items()if k!='seqno'}for d in page.get_drawings()]

def font_metadata(path,page_index):
    result={}
    with pikepdf.Pdf.open(path)as q:
        visited=set()
        def walk(resources,trail):
            for alias,f in resources.get('/Font',{}).items():
                desc=f.get('/DescendantFonts',[f])[0].get('/FontDescriptor',{})
                family=ops.family_name(str(f.BaseFont));angle=float(desc.get('/ItalicAngle',0))
                item=dict(alias=str(alias),angle=angle,resource_path=trail+'/'+str(alias),font_object=list(f.objgen))
                if family in result:
                    if result[family]['angle']!=angle:raise ValueError('Ambiguous original nested font slant '+family)
                    result[family].setdefault('equivalent_angle_resources',[]).append(item)
                else:result[family]=item
            for alias,obj in resources.get('/XObject',{}).items():
                if str(obj.get('/Subtype'))!='/Form'or obj.objgen in visited:continue
                visited.add(obj.objgen)
                walk(obj.get('/Resources',resources),trail+'/'+str(alias))
        walk(q.pages[page_index].Resources,'page')
    return result

def role(name):
    sans=bool(re.search('Arial|Helvetica|CMSS|Sans',name,re.I))
    bold=bool(re.search('Bold|CMBX|CMSSBX|SFBX',name,re.I))
    return ('sans'if sans else'serif')+('-bold'if bold else'')

def prepare(plan):
    source=Path(plan['source']);doc=fitz.open(source)
    if plan.get('source_sha256')and sha(source)!=plan['source_sha256']:raise ValueError('Source SHA256 changed')
    pi=plan['page']-1
    if plan.get('source_page_1based',pi+1)!=pi+1:raise ValueError('Conflicting page numbering')
    page=doc[pi];blocks=page.get_text('rawdict')['blocks'];meta=font_metadata(source,pi)
    selected=[];rows=[];claimed=Counter()
    metrics={key:fitz.Font(fontfile=str(value))for key,value in FONTS.items()}
    for s in plan['slots']:
        if s.get('skip'):continue
        if s.get('text')is None:raise ValueError('Untranslated slot '+s['id'])
        b,l,a,z=s['at'];line=blocks[b]['lines'][l]
        if list(line.get('dir',(1,0)))!=[1,0]:raise ValueError('Nonhorizontal source needs a separately reviewed profile')
        spans=line['spans'][a:z+1]
        flat=[dict(c,font=sp['font'],size=sp['size'],color=sp['color'])for sp in spans for c in sp['chars']]
        chars=flat[s.get('char_start',0):s.get('char_end')]
        if not chars:raise ValueError('Empty source selection '+s['id'])
        actual=''.join(c['c']for c in chars)
        if actual!=s['source']:raise ValueError(f"Source guard mismatch {s['id']}: {actual!r} != {s['source']!r}")
        first=next((c for c in chars if not c['c'].isspace()),chars[0])
        if any(c['font']!=first['font']or abs(c['size']-first['size'])>.001 or abs(c['origin'][1]-first['origin'][1])>.001 or c['color']!=first['color']for c in chars if not c['c'].isspace()):
            raise ValueError('Slot crosses source style/baseline boundary '+s['id'])
        rect=fitz.Rect(first['bbox'])
        for c in chars[1:]:rect|=fitz.Rect(c['bbox'])
        for c in chars:
            if c['c'].isspace():continue
            key=ops.glyph_key(c)
            # A repeated key inside ffi is legal; the same source characters
            # selected by distinct slots are not.
            if claimed[key]:raise ValueError('Overlapping source slots '+s['id'])
        claimed.update(ops.glyph_key(c)for c in chars if not c['c'].isspace())
        selected.extend(chars)
        family=s.get('font_role',role(first['font']));metric=metrics[family]
        for c in s['text']:
            if not c.isspace()and not metric.has_glyph(ord(c)):raise ValueError(f"Unsupported Korean glyph {c!r} at {s['id']}")
        point=list(first['origin']);right=float(s.get('extend_to',rect.x1))
        width=metric.text_length(s['text'],fontsize=first['size']);available=right-point[0]
        if width>available+.01:raise ValueError(f"Overflow {s['id']}: {width:.3f} > {available:.3f} pt; edit Korean wording or explicitly review extend_to")
        if s.get('align')=='center':point[0]+=(available-width)/2
        elif s.get('align')=='right':point[0]=right-width
        angle=meta[ops.family_name(first['font'])]['angle']
        rows.append(dict(id=s['id'],text=s['text'],source_font=first['font'],font_role=family,size=first['size'],point=point,
                         source_baseline=first['origin'][1],source_size=first['size'],advance=width,available=available,
                         source_rect=list(rect),angle=angle,color=first['color']))
    return doc,page,selected,rows

def subset_buffer(path,text):
    digest=hashlib.sha256(path.read_bytes()+text.encode('utf8')).hexdigest()[:20]
    target=BASE/'engine/font-cache'/(path.stem+'-'+digest+path.suffix)
    if target.exists():return target.read_bytes()
    target.parent.mkdir(parents=True,exist_ok=True)
    font=TTFont(path,recalcTimestamp=False);options=subset.Options();options.retain_gids=True
    options.name_IDs=['*'];options.name_languages=['*']
    sub=subset.Subsetter(options=options);sub.populate(text=text);sub.subset(font)
    buf=BytesIO();font.save(buf);font.close();target.write_bytes(buf.getvalue());return buf.getvalue()

def prepare_raster_labels(plan,page):
    result=[];images=page.get_image_info(hashes=True)
    for i,label in enumerate(plan.get('raster_labels',[])):
        if not label.get('source_text'):raise ValueError('Raster label needs its reviewed source_text')
        r=fitz.Rect(label['rect']);point=list(label['point']);size=float(label['size']);family=label.get('font_role','serif')
        if size<=0 or r.is_empty:raise ValueError('Invalid raster source-label geometry')
        matches=[im for im in images if abs((fitz.Rect(im['bbox'])&r).get_area()-r.get_area())<.01]
        if not matches:raise ValueError('Raster source-label mask is not inside an original image')
        for protected in [*plan.get('raster_protected_rects',[]),*label.get('protected_rects',[])]:
            if r.intersects(fitz.Rect(protected)):raise ValueError('Raster label mask intersects protected native math/diagram area')
        metric=fitz.Font(fontfile=str(FONTS[family]));text=label['text']
        for c in text:
            if not c.isspace()and not metric.has_glyph(ord(c)):raise ValueError('Unsupported raster-label Korean glyph '+repr(c))
        width=metric.text_length(text,fontsize=size)
        if label.get('align')=='right':point[0]-=width
        elif label.get('align')=='center':point[0]-=width/2
        allowed=fitz.Rect(label.get('allowed_rect',[min(r.x0,point[0]),min(r.y0,point[1]-size*1.2),max(r.x1,point[0]+width),max(r.y1,point[1]+size*.4)]))
        if point[0]+width>allowed.x1+.01:raise ValueError('Raster Korean label exceeds reviewed allowed_rect')
        result.append(dict(label,id=label.get('id',f'raster-label-{i+1}'),text=text,font_role=family,size=size,point=point,
                           source_rect=list(r),allowed_rect=list(allowed),advance=width,angle=float(label.get('angle',0)),color=label.get('color',0),
                           source_font_size_is_inferred=True,source_image_digest_md5=[im['digest'].hex()for im in matches]))
    return result

def build(plan_path,target):
    plan=json.loads(plan_path.read_text('utf8'));source,page,selected,rows=prepare(plan)
    selected=canonical_selected(page,selected)
    labels=prepare_raster_labels(plan,page)
    original=source_records(page);to_remove=Counter(ops.glyph_key(c)for c in selected if not c['c'].isspace());remaining=[]
    for c in original:
        k=ops.glyph_key(c)
        if to_remove[k]:to_remove[k]-=1
        else:remaining.append(c)
    if any(to_remove.values()):raise ValueError('Selected rawdict characters do not exactly match original trace')
    raw,removed=ops.suppress_prose(Path(plan['source']),plan['page'],selected)
    control=fitz.open(stream=raw,filetype='pdf');output=fitz.open(stream=raw,filetype='pdf');out=output[0]
    korean_only=fitz.open();korean_page=korean_only.new_page(width=page.rect.width,height=page.rect.height)
    for family in sorted({r['font_role']for r in [*rows,*labels]}):
        text=''.join(r['text']for r in [*rows,*labels]if r['font_role']==family)
        buffer=subset_buffer(FONTS[family],text)
        for pg in(out,korean_page):pg.insert_font(fontname='KO_'+family.replace('-','_'),fontbuffer=buffer)
    for r in rows:
        color=tuple(((r['color']>>n)&255)/255 for n in(16,8,0));point=fitz.Point(r['point'])
        morph=(point,fitz.Matrix(1,0,math.tan(math.radians(r['angle'])),1,0,0))if r['angle']else None
        for pg in(out,korean_page):pg.insert_text(point,r['text'],fontname='KO_'+r['font_role'].replace('-','_'),fontsize=r['size'],color=color,morph=morph)
    body_reference=fitz.open(stream=output.tobytes(garbage=0,deflate=False),filetype='pdf')if labels else None
    for r in labels:
        fill=r.get('fill',(1,1,1))
        for pg in(out,control[0]):pg.draw_rect(fitz.Rect(r['rect']),color=None,fill=fill,width=0,overlay=True)
        color=r['color'];color=tuple(((color>>n)&255)/255 for n in(16,8,0))if isinstance(color,int)else tuple(color)
        point=fitz.Point(r['point']);morph=(point,fitz.Matrix(1,0,math.tan(math.radians(r['angle'])),1,0,0))if r['angle']else None
        for pg in(out,korean_page):pg.insert_text(point,r['text'],fontname='KO_'+r['font_role'].replace('-','_'),fontsize=r['size'],color=color,morph=morph)
    target.parent.mkdir(parents=True,exist_ok=True);output.save(target,garbage=0,deflate=False);output.close()
    final=fitz.open(target);fp=final[0]
    final_native=[r for r in source_records(fp)if not r['font'].startswith(('NotoSerifCJK','NotoSansCJK'))]
    ctrl=compare_native(remaining,source_records(control[0]));geometry=compare_native(remaining,final_native)
    source_selected=[];select_counts=Counter(ops.glyph_key(c)for c in selected if not c['c'].isspace())
    for c in original:
        if select_counts[ops.glyph_key(c)]:source_selected.append(c);select_counts[ops.glyph_key(c)]-=1
    hidden=[dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(origin),bbox=list(bbox))for t in fp.get_texttrace()if t['type']==3 for cp,gid,origin,bbox in t['chars']]
    hidden_qa=compare_native(source_selected,hidden)
    def gray(pg):
        pix=pg.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csGRAY,alpha=False)
        return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)
    native_gray=gray(control[0]);korean_gray=gray(korean_page)
    intrusion=(native_gray<180)&(korean_gray<220)
    collision=int(intrusion.sum());collision_bounds=None
    collision_slots=[]
    if collision:
        ys,xs=np.nonzero(intrusion);collision_bounds=[float(xs.min()/2),float(ys.min()/2),float((xs.max()+1)/2),float((ys.max()+1)/2)]
        for r in [*rows,*labels]:
            x,y=r['point'];size=r['size'];x0=max(0,int((x-size*.3)*2));x1=min(intrusion.shape[1],math.ceil((x+r['advance']+size*.3)*2))
            y0=max(0,int((y-size*1.1)*2));y1=min(intrusion.shape[0],math.ceil((y+size*.3)*2))
            local=intrusion[y0:y1,x0:x1]
            if local.any():
                ly,lx=np.nonzero(local);collision_slots.append(dict(id=r['id'],pixels=int(local.sum()),bounds=[float((lx.min()+x0)/2),float((ly.min()+y0)/2),float((lx.max()+x0+1)/2),float((ly.max()+y0+1)/2)]))
    raster_outside=0
    if labels:
        before=gray(body_reference[0]);after=gray(fp);allowed=np.zeros(before.shape,bool)
        for r in labels:
            box=fitz.Rect(r['allowed_rect']);x0=max(0,math.floor(box.x0*2));x1=min(allowed.shape[1],math.ceil(box.x1*2));y0=max(0,math.floor(box.y0*2));y1=min(allowed.shape[0],math.ceil(box.y1*2));allowed[y0:y1,x0:x1]=True
        raster_outside=int(((before!=after)&~allowed).sum())
        target.with_suffix('.body.pdf').write_bytes(body_reference.tobytes(garbage=0,deflate=False));body_reference.close()
    report=dict(schema='latex-native-invisible-advance-proof-v1',source=str(Path(plan['source']).resolve()),source_sha256=sha(plan['source']),
                source_page_1based=plan['page'],plan_sha256=sha(plan_path),output=str(target.resolve()),output_sha256=sha(target),
                removed_logical_characters=removed,placements=rows,no_autoshrink=True,no_math_rasterization=True,
                source_font_programs_preserved=font_programs(source,page)<=font_programs(final,fp),
                source_images_preserved=native_images(page)==native_images(fp),source_drawings_preserved=drawings(page)==drawings(fp)[:len(drawings(page))]and len(drawings(fp))==len(drawings(page))+len(labels),
                original_image_encoded_stream_bytes_and_filters_preserved=encoded_images(source,page)==encoded_images(final,fp),
                suppression_control_native_geometry=ctrl,final_native_geometry=geometry,
                selected_source_hidden_geometry=hidden_qa,invisible_source_strategy='original encoded bytes in Tr3 with empty ActualText; original Tr restored',
                new_korean_intrusion_on_native_ink_pixels=collision,collision_bounds_pdf_pt=collision_bounds,
                collision_slots=collision_slots,
                raster_labels=labels,raster_language_changed_pixels_outside_reviewed_boxes=raster_outside,
                original_page_box_preserved=page.rect==fp.rect,visual_review_required=True)
    target.with_suffix('.qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    target.with_suffix('.control.pdf').write_bytes(control.tobytes(garbage=0,deflate=False)if labels else raw)
    if collision or raster_outside or any(c[k]for c in(ctrl,geometry,hidden_qa)for k in('missing','extra'))or not all(report[k]for k in('source_font_programs_preserved','source_images_preserved','source_drawings_preserved','original_page_box_preserved','original_image_encoded_stream_bytes_and_filters_preserved')):
        raise ValueError('Native preservation proof failed; see QA')
    fp.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(target.with_suffix('.png'))
    source.close();control.close();final.close();korean_only.close()
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if args.check:
        plan=json.loads(args.plan.read_text('utf8'));d,p,s,rows=prepare(plan);labels=prepare_raster_labels(plan,p);d.close();print(json.dumps({'slots':len(rows),'raster_labels':len(labels),'fits':True}))
    else:
        r=build(args.plan,args.output);print(json.dumps({k:v for k,v in r.items()if k!='placements'},ensure_ascii=False))
