"""Read-only original PDF bitmap/SMask bounds and native-ink protection.

Word PDFs may use a 2x2 black image with a 128x128 soft mask, or a very
wide transparent caption image containing only one mathematical letter.
The mask's own dimensions, rather than the colour image dimensions, define
the nonzero-alpha bounds. No original stream or resource is modified.
"""
from collections import Counter
from pathlib import Path
import hashlib
from io import BytesIO
import pikepdf
import numpy as np
import pymupdf as fitz
import cv2


def resolved_images(doc,page):
    result=[dict(item)for item in page.get_image_info(xrefs=True)]
    if not result:return result
    # MuPDF may return a nonzero, wrong xref when equal colour streams have
    # different SMask resources. In particular, Word uses many identical 2x2
    # black images whose independent masks contain different math symbols.
    # Resolve every actual Do occurrence, not just a reported zero xref.
    painted=[];identity=(1.,0.,0.,1.,0.,0.);page_matrix=tuple(page.transformation_matrix)
    def multiply(a,b):
        x,y,z,w,e,f=a;A,B,C,D,E,F=b
        return(x*A+y*C,x*B+y*D,z*A+w*C,z*B+w*D,e*A+f*C+E,e*B+f*D+F)
    def bounds(matrix):
        a,b,c,d,e,f=matrix;points=[(a*x+c*y+e,b*x+d*y+f)for x,y in[(0,0),(1,0),(0,1),(1,1)]]
        return[min(p[0]for p in points),min(p[1]for p in points),max(p[0]for p in points),max(p[1]for p in points)]
    source=doc.name if doc.name and Path(doc.name).is_file()else BytesIO(doc.tobytes(garbage=0))
    with pikepdf.Pdf.open(source)as pdf:
        def walk(node,resources,ctm=identity,path=(),ancestors=()):
            if len(ancestors)>20:raise ValueError('Excessive image Form nesting')
            stack=[]
            for index,instruction in enumerate(pikepdf.parse_content_stream(node)):
                op=str(instruction.operator);operands=instruction.operands
                if op=='q':stack.append(ctm)
                elif op=='Q':
                    if not stack:raise ValueError('Unbalanced original image graphics state')
                    ctm=stack.pop()
                elif op=='cm':ctm=multiply(tuple(map(float,operands)),ctm)
                elif op=='Do':
                    child=resources.get('/XObject',{}).get(operands[0])
                    if child is None:raise ValueError('Missing original image/Form resource')
                    subtype=str(child.get('/Subtype'));current_path=path+(index,)
                    if subtype=='/Image':
                        painted.append(dict(xref=child.objgen[0],path=list(current_path),bbox=bounds(multiply(ctm,page_matrix)),width=int(child.Width),height=int(child.Height)))
                    elif subtype=='/Form':
                        if child.objgen in ancestors:raise ValueError('Recursive image Form')
                        walk(child,child.get('/Resources',resources),multiply(tuple(map(float,child.get('/Matrix',identity))),ctm),current_path,ancestors+(child.objgen,))
        p=pdf.pages[page.number];walk(p,p.Resources)
    if len(painted)!=len(result):raise ValueError('Image paint order cannot be proved')
    for item,original in zip(result,painted):
        if (item['width'],item['height'])!=(original['width'],original['height']):raise ValueError('Original image Do dimensions disagree with rendered occurrence')
        if max(abs(x-y)for x,y in zip(item['bbox'],original['bbox']))>.002:raise ValueError(('Original image Do CTM disagrees with rendered occurrence',original['path'],item['bbox'],original['bbox']))
        item['mupdf_cached_xref']=item['xref'];item['xref']=original['xref']
        item['original_paint_path']=original['path'];item['xref_resolved_from_original_Do']=True
    return result


def _planes(doc, info):
    meta=doc.extract_image(info['xref']);smask=meta.get('smask')
    pix=fitz.Pixmap(doc, info['xref'])
    if pix.colorspace and pix.colorspace.n not in (1,3):pix=fitz.Pixmap(fitz.csRGB,pix)
    samples=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,pix.n)
    colour=samples[:,:,:pix.colorspace.n].min(axis=2)
    if smask:
        maskpix=fitz.Pixmap(doc,smask)
        alpha=np.frombuffer(maskpix.samples,np.uint8).reshape(maskpix.height,maskpix.width,maskpix.n)[:,:,0]
        if colour.shape!=alpha.shape:colour=cv2.resize(colour,(maskpix.width,maskpix.height),interpolation=cv2.INTER_NEAREST)
    else:alpha=np.full(colour.shape,255,np.uint8)
    return colour,alpha,smask


def image_ink_regions(doc,page):
    """Return each source image's nonzero-alpha bounding rectangle in pt."""
    result=[]
    for info in resolved_images(doc,page):
        colour,alpha,smask=_planes(doc,info);ys,xs=np.nonzero(alpha)
        if not len(xs):continue
        height,width=alpha.shape;a,b,c,d,e,f=info['transform']
        corners=[(x/width,y/height)for x in (xs.min(),xs.max()+1)for y in (ys.min(),ys.max()+1)]
        points=[(a*x+c*y+e,b*x+d*y+f)for x,y in corners]
        result.append({'xref':info['xref'],'smask':smask,'rect':list(info['bbox']),
            'ink_rect':[float(min(x for x,y in points)),float(min(y for x,y in points)),float(max(x for x,y in points)),float(max(y for x,y in points))],
            'mask_width':width,'mask_height':height,'image_width':info['width'],'image_height':info['height']})
    return result


def image_ink_mask(doc,page,scale=4,threshold=250,pad=1):
    """Page-sized boolean native visible-image ink mask, including SMask.

    A one-pixel guard covers raster antialiasing. The colour threshold omits
    white/JPEG background noise while retaining dark lines and grey objects.
    Alpha is tested at its full original resolution; glyphs are never inferred
    from a PDF text layer or the often misleading outer image rectangle.
    """
    width=int(np.ceil(page.rect.width*scale));height=int(np.ceil(page.rect.height*scale));result=np.zeros((height,width),np.uint8)
    for info in resolved_images(doc,page):
        colour,alpha,_=_planes(doc,info);visible=((alpha>0)&(colour<threshold)).astype(np.uint8)
        if not np.any(visible):continue
        h,w=visible.shape;a,b,c,d,e,f=info['transform']
        transform=np.array([[a/w*scale,c/h*scale,(e+.5*a/w+.5*c/h)*scale-.5],
                            [b/w*scale,d/h*scale,(f+.5*b/w+.5*d/h)*scale-.5]],np.float64)
        projected=cv2.warpAffine(visible,transform,(width,height),flags=cv2.INTER_NEAREST,borderValue=0)
        result|=projected
    if pad:result=cv2.dilate(result,np.ones((2*pad+1,2*pad+1),np.uint8))
    return result.astype(bool)


def image_programs(doc,page):
    """Position, colour-stream and SMask-stream identities, excluding xrefs."""
    records=[]
    for info in resolved_images(doc,page):
        xref=info['xref'];meta=doc.extract_image(xref);smask=meta.get('smask')
        records.append((tuple(info['bbox']),int(doc.xref_get_key(xref,'Width')[1]),int(doc.xref_get_key(xref,'Height')[1]),
            (int(doc.xref_get_key(smask,'Width')[1]),int(doc.xref_get_key(smask,'Height')[1]))if smask else None,
            hashlib.sha256(doc.xref_stream(xref)).hexdigest(),
            hashlib.sha256(doc.xref_stream(smask)).hexdigest()if smask else None,
            hashlib.sha256(doc.xref_stream_raw(xref)).hexdigest(),
            hashlib.sha256(doc.xref_stream_raw(smask)).hexdigest()if smask else None))
    return Counter(records)
