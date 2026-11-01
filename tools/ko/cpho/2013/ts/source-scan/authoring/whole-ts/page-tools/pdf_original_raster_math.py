"""Exact original bitmap ROI replay for manually reviewed inline mathematics.

No recognition, equation retyping, resampling or old-pixel erasure occurs here.
The caller supplies a one-page translated base with reviewed old ROIs erased.
Original image-only q/clip/cm/Do/Q bytes, encoded bitmap/mask/colour programs
and 1x scale are retained. Only an outer page-horizontal translation is added.
"""
from io import BytesIO
from pathlib import Path
from collections import Counter
import hashlib,json,math
import pikepdf
import pymupdf as fitz
import numpy as np
from pdf_native_inline_reposition import inspect_inline_groups,_raw_regions,_multiply

IDENTITY=(1.,0.,0.,1.,0.,0.)
ALLOWED={'q','Q','cm','re','m','l','h','W','W*','n','Do','gs','g','G','rg','RG','k','K','cs','CS','sc','scn','SC','SCN','ri'}
def sha(v):return hashlib.sha256(v if isinstance(v,bytes)else Path(v).read_bytes()).hexdigest()
def nums(v):return ' '.join(format(float(n),'.12f').rstrip('0').rstrip('.')or'0'for n in v)
def invert(m):
    a,b,c,d,e,f=map(float,m);det=a*d-b*c
    if abs(det)<1e-18:raise ValueError('Singular source matrix')
    return(d/det,-b/det,-c/det,a/det,(c*f-d*e)/det,(b*e-a*f)/det)
def foreign(out,original,v):return out.copy_foreign(v if v.is_indirect else original.make_indirect(v))
def program(v,seen=()):
    if isinstance(v,pikepdf.Stream):
        if v.objgen in seen:raise ValueError('Recursive image colour/mask program')
        try:decoded=sha(v.read_bytes())
        except pikepdf.PdfError:decoded='original compressed image decoder; exact raw bytes retained'
        return dict(raw=sha(v.read_raw_bytes()),decoded=decoded,dictionary={str(k):program(x,seen+(v.objgen,))for k,x in v.items()})
    if isinstance(v,pikepdf.Dictionary):return{str(k):program(x,seen)for k,x in v.items()}
    if isinstance(v,pikepdf.Array):return[program(x,seen)for x in v]
    if isinstance(v,pikepdf.String):return dict(string_hex=bytes(v).hex())
    return str(v)
def program_sha(v):return sha(json.dumps(program(v),sort_keys=True,separators=(',',':')).encode())
def original_image_instances(container,resources,entry=IDENTITY,ancestors=()):
    result=[];ctm=entry;stack=[]
    for op in pikepdf.parse_content_stream(container):
        name=str(op.operator)
        if name=='q':stack.append(ctm)
        elif name=='Q':ctm=stack.pop()
        elif name=='cm':ctm=_multiply(tuple(map(float,op.operands)),ctm)
        elif name=='Do':
            obj=resources.XObject[op.operands[0]];kind=str(obj.get('/Subtype'))
            if kind=='/Image':result.append((program_sha(obj),tuple(round(v,8)for v in ctm)))
            elif kind=='/Form':
                if obj.objgen in ancestors:raise ValueError('Recursive source Form')
                transform=_multiply(tuple(map(float,obj.get('/Matrix',IDENTITY))),ctm)
                result.extend(original_image_instances(obj,obj.get('/Resources',resources),transform,ancestors+(obj.objgen,)))
    if stack:raise ValueError('Unbalanced original image graphics-state stack')
    return Counter(result)
def clip_bytes(rect,page_matrix):
    r=fitz.Rect(rect);inv=~fitz.Matrix(page_matrix);points=[p*inv for p in(r.tl,r.tr,r.br,r.bl)]
    return(nums(points[0])+' m\n'+'\n'.join(nums(p)+' l'for p in points[1:])+'\nh W n\n').encode('ascii')
def geometry_copy(sp,page,out,original):
    for key in ['/MediaBox','/CropBox','/Rotate','/Group','/UserUnit']:
        v=sp.obj.get(key)
        if v is not None:page.obj[key]=foreign(out,original,v)if isinstance(v,(pikepdf.Array,pikepdf.Dictionary,pikepdf.Stream))else v
def source_recipe(source,number,path):
    path=list(path)
    if len(path)!=1:raise ValueError('Explicit top-level source image Do required')
    inv=inspect_inline_groups(source,number);images=[i for i in inv['images']if i['path']==path]
    if len(images)!=1:raise ValueError('Original image invocation not unique')
    image=images[0]
    if any(r is None for r in image['ancestor_clip_rects']):raise ValueError('Unknown source clip')
    groups=[g for g in inv['clip_groups']if g.get('image_paths')==[path]and not any(c['c'].strip()for c in g['glyphs'])and g['operator_indices'][0]<=path[0]<=g['operator_indices'][1]]
    if not groups:raise ValueError('No complete image-only original clipping group')
    group=min(groups,key=lambda g:g['operator_indices'][1]-g['operator_indices'][0])
    with pikepdf.open(source)as pdf:
        page=pdf.pages[number-1];raw,regions=_raw_regions(page);ops=list(pikepdf.parse_content_stream(page));first,last=group['operator_indices'];selected=ops[first:last+1]
        if any(str(op.operator)not in ALLOWED for op in selected):raise ValueError('Original image group includes another paint')
        dos=[op for op in selected if str(op.operator)=='Do']
        if len(dos)!=1:raise ValueError('Image group paints more than one object')
        alias=str(dos[0].operands[0]);obj=page.Resources.XObject[alias]
        if str(obj.get('/Subtype'))!='/Image':raise ValueError('Selected Do is not an image')
        local=IDENTITY;stack=[]
        for op in selected:
            name=str(op.operator)
            if name=='q':stack.append(local)
            elif name=='Q':local=stack.pop()
            elif name=='cm':local=_multiply(tuple(map(float,op.operands)),local)
            elif name=='Do':break
        ancestor=_multiply(invert(local),image['entry_ctm'])
        if max(abs(a-b)for a,b in zip(ancestor,IDENTITY))<1e-10:ancestor=IDENTITY
        segment=raw[regions[first][0]:regions[last][1]];prefix=b''if ancestor==IDENTITY else(nums(ancestor)+' cm\n').encode('ascii')
        return dict(image=image,alias=alias,operators=[first,last],content=prefix+segment,ancestor_ctm=ancestor,
            original_group_raw_sha256=sha(segment),image_raw_sha256=sha(obj.read_raw_bytes()),image_program_sha256=program_sha(obj))
def add_form(out,original,sp,recipe):
    rs=pikepdf.Dictionary(XObject=pikepdf.Dictionary({recipe['alias']:foreign(out,original,sp.Resources.XObject[recipe['alias']])}))
    for key in ['/ExtGState','/ColorSpace','/Pattern','/Properties']:
        if key in sp.Resources:rs[key]=foreign(out,original,sp.Resources[key])
    form=out.make_stream(recipe['content']);form.Type=pikepdf.Name.XObject;form.Subtype=pikepdf.Name.Form;form.FormType=1
    form.BBox=pikepdf.Array(list(sp.MediaBox));form.Resources=rs
    return form
def command(recipe,rect,dx,alias):
    matrix=recipe['image']['page_matrix'];dest=list(fitz.Rect(rect)+(dx,0,dx,0));inv=~fitz.Matrix(matrix);delta=fitz.Point(dx,0)*inv-fitz.Point(0,0)*inv
    return b'q\n/OriginalRasterReset gs\n'+clip_bytes(dest,matrix)+(nums([1,0,0,1,delta.x,delta.y])+' cm\n/'+alias+' Do\nQ\n').encode('ascii')
def reset_state():return pikepdf.Dictionary(Type=pikepdf.Name.ExtGState,ca=1,CA=1,BM=pikepdf.Name.Normal,SMask=pikepdf.Name('/None'))
def roundtrip(source,number,recipe,rect,scale=4):
    """Require exact actual source pixels, including its real clipping/masks."""
    with pikepdf.open(source)as original,pikepdf.Pdf.new()as ref:
        sp=original.pages[number-1];page=ref.add_blank_page(page_size=(float(sp.MediaBox[2]),float(sp.MediaBox[3])));geometry_copy(sp,page,ref,original)
        page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(OriginalRasterMath=add_form(ref,original,sp,recipe)),ExtGState=pikepdf.Dictionary(OriginalRasterReset=reset_state()))
        page.Contents=ref.make_stream(command(recipe,rect,0,'OriginalRasterMath'));buffer=BytesIO();ref.save(buffer,compress_streams=False)
    with fitz.open(source)as a,fitz.open(stream=buffer.getvalue(),filetype='pdf')as b:
        before=a[number-1].get_pixmap(matrix=fitz.Matrix(scale,scale),clip=fitz.Rect(rect),alpha=False,colorspace=fitz.csRGB)
        after=b[0].get_pixmap(matrix=fitz.Matrix(scale,scale),clip=fitz.Rect(rect),alpha=False,colorspace=fitz.csRGB)
        if(before.width,before.height)!=(after.width,after.height):raise ValueError('Replay crop geometry differs')
        changed=int(np.any(np.frombuffer(before.samples,dtype=np.uint8).reshape(-1,3)!=np.frombuffer(after.samples,dtype=np.uint8).reshape(-1,3),axis=1).sum())
        if changed:raise ValueError(('Original bitmap recipe differs from actual source',changed,rect))
    return dict(changed_pixels=0,scale=scale,actual_clipped_source_rgb_sha256=sha(before.samples))
def replay(source,number,base,atoms):
    """Return (PDF bytes, journal); caller owns explicit old-ROI erasure."""
    if not atoms:raise ValueError('No reviewed inline bitmap atoms')
    source=Path(source);base=Path(base);recipes={};journal=[];ids=set()
    with fitz.open(source)as d:bounds=d[number-1].rect
    for atom in atoms:
        if atom.get('reviewed')is not True or not atom.get('reason'):raise ValueError('Manual review and reason required')
        if atom['id']in ids:raise ValueError('Duplicate atom id')
        ids.add(atom['id']);dx=float(atom['dx']);path=tuple(atom['image_path'])
        if not math.isfinite(dx):raise ValueError('Nonfinite bitmap shift')
        if path not in recipes:recipes[path]=source_recipe(source,number,path)
        recipe=recipes[path];rect=fitz.Rect(atom['rect']);dest=rect+(dx,0,dx,0)
        if rect.is_empty or not bounds.contains(dest):raise ValueError('Atom leaves original page')
        for boundary in[recipe['image']['bbox']]+recipe['image']['ancestor_clip_rects']:
            if not(fitz.Rect(boundary)+(-.0001,-.0001,.0001,.0001)).contains(rect):raise ValueError('Atom escapes original image/clip')
        if atom.get('image_raw_sha256')and atom['image_raw_sha256']!=recipe['image_raw_sha256']:raise ValueError('Pinned original bitmap differs')
        witness=roundtrip(source,number,recipe,rect)
        journal.append(dict(id=atom['id'],image_path=list(path),source_rect=list(rect),destination_rect=list(dest),dx=dx,
            source_image_ctm=recipe['image']['entry_ctm'],source_group_operators=recipe['operators'],linear_scale=1.,
            original_group_raw_sha256=recipe['original_group_raw_sha256'],image_raw_sha256=recipe['image_raw_sha256'],
            image_program_sha256=recipe['image_program_sha256'],source_recipe_roundtrip=witness,reason=atom['reason']))
    with pikepdf.open(source)as original,pikepdf.open(base)as out:
        if len(out.pages)!=1:raise ValueError('Translated base must be one page')
        sp=original.pages[number-1];page=out.pages[0]
        if list(page.MediaBox)!=list(sp.MediaBox):raise ValueError('Base page geometry differs')
        if original_image_instances(sp,sp.Resources)!=original_image_instances(page,page.Resources):raise ValueError('Base changed an original image/mask/ICC/palette program or original image CTM')
        if program(sp.obj.get('/Group'))!=program(page.obj.get('/Group')):raise ValueError('Base PageGroup differs')
        if '/XObject'not in page.Resources:page.Resources.XObject=pikepdf.Dictionary()
        if '/ExtGState'not in page.Resources:page.Resources.ExtGState=pikepdf.Dictionary()
        if '/OriginalRasterReset'in page.Resources.ExtGState:raise ValueError('Replay resource already exists')
        page.Resources.ExtGState.OriginalRasterReset=reset_state();aliases={}
        for index,(path,recipe)in enumerate(recipes.items()):
            name=f'OriginalRasterMath{index+1}'
            if '/'+name in page.Resources.XObject:raise ValueError('Replay resource already exists')
            page.Resources.XObject['/'+name]=add_form(out,original,sp,recipe);aliases[path]=name
        old=page.Contents if isinstance(page.Contents,pikepdf.Array)else[page.Contents]
        extra=b''.join(command(recipes[tuple(a['image_path'])],a['rect'],float(a['dx']),aliases[tuple(a['image_path'])])for a in atoms)
        page.Contents=pikepdf.Array([out.make_stream(b'q\n'),*old,out.make_stream(b'Q\n'+extra)])
        for path,name in aliases.items():
            obj=page.Resources.XObject['/'+name].Resources.XObject[recipes[path]['alias']]
            if program_sha(obj)!=recipes[path]['image_program_sha256']:raise ValueError('Original image/mask/palette/ICC program changed')
        buffer=BytesIO();out.save(buffer,compress_streams=False)
    result=buffer.getvalue()
    return result,dict(source=str(source),source_page=number,source_sha256=sha(source),base_sha256=sha(base),output_sha256=sha(result),atoms=journal,atom_count=len(journal),
        original_encoded_image_mask_palette_icc_programs_unchanged=True,original_clip_and_image_paint_tokens_unchanged=True,original_bitmap_scale_unchanged=True,
        note='Only explicit additional original-image region paints; no mathematical glyph or bitmap is regenerated.')
