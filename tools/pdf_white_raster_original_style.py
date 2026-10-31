"""Fixed-baseline translation overlays for explicitly reviewed white scan prose.

Original images are never edited, resampled, replaced, or painted twice. White
PDF paths remove only reviewed language rectangles; explicitly protected maths
remain visible even inside those rectangles. New prose must pass fixed-size
fitting and a separate original non-language ink guard. No OCR text is trusted
or automatically classified by this module.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from pathlib import Path
import hashlib,json,math
import numpy as np
import cv2
import pymupdf as fitz
from pdf_original_style_fonts import subset_font
from pdf_original_style_audit import glyphs,key
from pdf_original_graphics_ink import graphics_control
from pdf_original_image_ink import resolved_images


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rectangle(value,page_rect):
    r=fitz.Rect(value)
    if r.is_empty or r.is_infinite or not page_rect.contains(r):raise ValueError('Invalid reviewed raster rectangle')
    return r


def _subtract(rect,protected):
    """Split white fill paths around an explicitly protected native rectangle."""
    hit=rect&protected
    if hit.is_empty:return[rect]
    candidates=[fitz.Rect(rect.x0,rect.y0,rect.x1,hit.y0),
        fitz.Rect(rect.x0,hit.y1,rect.x1,rect.y1),
        fitz.Rect(rect.x0,hit.y0,hit.x0,hit.y1),
        fitz.Rect(hit.x1,hit.y0,rect.x1,hit.y1)]
    return[r for r in candidates if not r.is_empty]


def fill_rectangles(regions,page_rect):
    """The exact old-language white paths; all region guards are global."""
    protected=[_rectangle(r,page_rect)for item in regions for r in item.get('protected_rects',[])]
    result=[]
    for item in regions:
        for value in item['erase_rects']:
            pieces=[_rectangle(value,page_rect)]
            for guard in protected:pieces=[part for r in pieces for part in _subtract(r,guard)]
            result.extend(pieces)
    return result,protected


def reviewed_backgrounds(regions,page_rect,source_sha256=None):
    """Classify explicit blank prose background without painting over it.

    This opt-in covers only reviewed scan dust under new prose. It is distinct
    from erasing original language, and every explicit native guard still wins.
    """
    result=[]
    for region in regions:
        for item in region.get('reviewed_blank_background_rects',[]):
            if (not isinstance(item,dict)or item.get('reviewed')is not True
                or not item.get('reason')or not item.get('evidence')
                or not item.get('source_sha256')or not item.get('source_ink_bbox')):
                raise ValueError('Blank prose background needs separate manual review and original-ink evidence')
            if source_sha256 is not None and item['source_sha256']!=source_sha256:
                raise ValueError('Reviewed blank prose background belongs to another source')
            _rectangle(item['rect'],page_rect);_rectangle(item['source_ink_bbox'],page_rect)
            result.append(dict(region_id=region['id'],**item))
    return result


def _box_mask(shape,rects,scale,margin=0):
    result=np.zeros(shape,bool)
    for value in rects:
        r=fitz.Rect(value)+(-margin,-margin,margin,margin)
        x0=max(0,math.floor(r.x0*scale));x1=min(shape[1],math.ceil(r.x1*scale))
        y0=max(0,math.floor(r.y0*scale));y1=min(shape[0],math.ceil(r.y1*scale))
        result[y0:y1,x0:x1]=True
    return result


def _rgb(page,scale):
    p=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
    return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)


def image_snapshot(doc,page):
    """Actual paint order/CTM, raw and decoded streams, Filters and alpha."""
    result=[]
    for info in resolved_images(doc,page):
        xref=info['xref'];kind,value=doc.xref_get_key(xref,'SMask')
        smask=int(value.split()[0])if kind=='xref'else None
        def stream_hash(n,raw=False):
            payload=doc.xref_stream_raw(n)if raw else doc.xref_stream(n)
            return hashlib.sha256(payload).hexdigest()
        result.append(dict(bbox=list(info['bbox']),transform=list(info['transform']),
            width=info['width'],height=info['height'],bpc=info['bpc'],colorspace=info['colorspace'],
            filter=doc.xref_get_key(xref,'Filter'),raw_sha256=stream_hash(xref,True),decoded_sha256=stream_hash(xref),
            smask_filter=doc.xref_get_key(smask,'Filter')if smask else None,
            smask_raw_sha256=stream_hash(smask,True)if smask else None,
            smask_decoded_sha256=stream_hash(smask)if smask else None))
    return result


def preflight(regions,page_rect):
    ids=[r['id']for r in regions]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate raster language region ID')
    metrics={};font_hashes={};placements=[]
    for item in regions:
        if item.get('reviewed')is not True or not item.get('source_text')or not item.get('erase_rects'):
            raise ValueError('Raster prose needs explicit original text, rectangles, and human review')
        if not item['text']:
            destination=item.get('translation_shifted_to')
            if destination==item['id']or not any(r['id']==destination and r['text']for r in regions):
                raise ValueError('An empty prose fragment needs an explicit nonempty translated destination region')
        for box in item['erase_rects']:_rectangle(box,page_rect)
        size=float(item['size']);x,y=map(float,item['point']);right=float(item['right'])
        if size<=0 or not 0<=x<right<=page_rect.x1 or not 0<y<page_rect.y1:
            raise ValueError('Invalid fixed prose size, baseline, or width')
        if '\n'in item['text']or '\r'in item['text']:raise ValueError('Raster slots may not reflow source lines')
        font_path=Path(item['font_path'])
        if font_path not in metrics:
            metrics[font_path]=fitz.Font(fontfile=str(font_path));font_hashes[font_path]=sha(font_path)
        font=metrics[font_path]
        missing=[c for c in item['text']if not font.has_glyph(ord(c))]
        if missing:raise ValueError(('Replacement face lacks requested glyphs',item['id'],missing))
        width=font.text_length(item['text'],fontsize=size)
        if width>right-x+.02:raise ValueError(('Fixed-size raster prose overflow',item['id'],width,right-x,item['text']))
        align=item.get('align','left')
        if align=='center':x=float(item.get('center',(x+right)/2))-width/2
        elif align=='right':x=right-width
        elif align!='left':raise ValueError('Unsupported raster prose alignment')
        if item.get('oblique_angle',0):raise ValueError('A scanned italic face needs a separately reviewed transform profile')
        placements.append(dict(id=item['id'],source_text=item['source_text'],text=item['text'],
            point=[x,y],source_baseline=float(item['point'][1]),size=size,width=width,available=right-float(item['point'][0]),
            align=align,font_path=str(font_path),font_sha256=font_hashes[font_path]))
    fill_rectangles(regions,page_rect)
    reviewed_backgrounds(regions,page_rect)
    return placements


def audit(source_path,source_page_1based,base_pdf,target_pdf,regions,placements,scale=4):
    with fitz.open(source_path)as source,fitz.open(base_pdf)as base,fitz.open(target_pdf)as output:
        if len(base)!=1 or len(output)!=1:raise ValueError('Raster overlay audit requires one-page proofs')
        a=source[source_page_1based-1];b=base[0];c=output[0]
        if a.rect!=b.rect or b.rect!=c.rect:raise ValueError('Original page geometry changed')
        before,after=_rgb(b,scale),_rgb(c,scale);difference=np.any(before!=after,axis=2)
        erase,explicit_protection=fill_rectangles(regions,a.rect)
        language=_box_mask(difference.shape,erase,scale)
        backgrounds=reviewed_backgrounds(regions,a.rect,sha(source_path))
        background=_box_mask(difference.shape,[item['rect']for item in backgrounds],scale)
        explicit=_box_mask(difference.shape,explicit_protection,scale)
        # Use the actually painted graphics. Raw image-alpha projection alone
        # misses PDF clips/white painting and can protect invisible phantom ink.
        with fitz.open(stream=graphics_control(source,a),filetype='pdf')as nontext:
            original_nontext=_rgb(nontext[0],scale).min(axis=2)<250
        actual_native=(original_nontext&~(language|background))|(original_nontext&explicit)
        guard=cv2.dilate(actual_native.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
        # New prose is deliberately a separate mask from erased old prose.
        new_rects=[]
        old=Counter(key(g)for g in glyphs(b));remaining=old.copy()
        for g in glyphs(c):
            token=key(g)
            if remaining[token]:remaining[token]-=1
            else:new_rects.append(g['bbox'])
        # The fixed placement geometry also covers blank text spaces. It
        # never weakens the separate original native graphics mask above.
        for row in placements:
            x,y=row['point'];new_rects.append([x,y-row['size']*1.3,x+row['width'],y+row['size']*.4])
        allowed=_box_mask(difference.shape,[*erase,*new_rects],scale,margin=1/scale)
        now=Counter(key(g)for g in glyphs(c))
        missing=sum((old-now).values())
        source_images=image_snapshot(source,a);base_images=image_snapshot(base,b);target_images=image_snapshot(output,c)
        checks=dict(base_native_text_glyphs_checked=sum(old.values()),base_native_text_glyphs_changed=missing,
            changed_pixels_outside_old_and_new_language=int((difference&~allowed).sum()),
            changed_original_actual_nonlanguage_ink_pixels=int((difference&actual_native).sum()),
            changed_original_nonlanguage_guard_pixels=int((difference&guard).sum()),
            changed_pixels_in_explicit_math_protection=int((difference&explicit).sum()),
            original_image_programs_and_raw_bytes_and_filters_and_smask_and_ctm_unchanged=source_images==base_images==target_images)
        result=dict(source_sha256=sha(source_path),source_page=source_page_1based,base_sha256=sha(base_pdf),
            proof_sha256=sha(target_pdf),scale=scale,graphics_ink_method='original Page/Group/FormBBox/Matrix/clip/image/SMask analysis control',
            original_language_mask='Only manually reviewed old-language rectangles, with every explicit math guard subtracted.',
            reviewed_blank_prose_backgrounds=backgrounds,
            reviewed_blank_backgrounds_painted_white=False,
            new_language_mask='Separate fixed-baseline prose areas; never excluded from native graphics protection.',
            source_native_image_paint_count=len(source_images),source_native_image_programs=source_images,
            native_guard_pixels=int(guard.sum()),old_language_region_count=len(regions),placements=placements,
            autoshrink=False,reflow=False,new_equation_images=0,original_image_replacement=False,checks=checks)
        result['passed']=all(value==0 for k,value in checks.items()if k.startswith('changed_')or k.endswith('_changed'))
        result['passed']&=checks['original_image_programs_and_raw_bytes_and_filters_and_smask_and_ctm_unchanged']
        if not result['passed']:
            bad=difference&(guard|explicit|~allowed)
            if bad.any():
                yy,xx=np.nonzero(bad);result['failure_bbox']=[float(xx.min()/scale),float(yy.min()/scale),float((xx.max()+1)/scale),float((yy.max()+1)/scale)]
        return result


def apply(source_path,source_page_1based,base_pdf,target_pdf,regions,font_cache):
    """Compose reviewed scanned prose and fail closed on changed native ink."""
    source_path=Path(source_path);base_pdf=Path(base_pdf);target_pdf=Path(target_pdf)
    if source_path.resolve()==target_pdf.resolve()or base_pdf.resolve()==target_pdf.resolve():
        raise ValueError('A reviewed source/control cannot be overwritten')
    with fitz.open(base_pdf)as doc:
        if len(doc)!=1 or doc[0].rotation:raise ValueError('Reviewed single unrotated source page required')
        page=doc[0];placements=preflight(regions,page.rect);fills,_=fill_rectangles(regions,page.rect)
        for r in fills:page.draw_rect(r,color=None,fill=(1,1,1),overlay=True)
        text_by_font=defaultdict(str)
        for item in regions:text_by_font[str(item['font_path'])]+=item['text']
        names={}
        for index,(font_path,text)in enumerate(text_by_font.items()):
            if not text:continue
            subset=subset_font(Path(font_path),text,font_cache);name=f'RasterTranslation{index}'
            if any(record[4]==name for record in page.get_fonts(full=True)):raise ValueError('Raster font alias already used')
            page.insert_font(fontname=name,fontfile=str(subset));names[font_path]=name
        for item,row in zip(regions,placements):
            if not item['text']:continue
            name=names[str(item['font_path'])];row['alias']=name
            page.insert_text(fitz.Point(*row['point']),item['text'],fontname=name,fontsize=row['size'],
                color=tuple(item.get('color',[0,0,0])),overlay=True)
        target_pdf.parent.mkdir(parents=True,exist_ok=True);doc.save(target_pdf,garbage=0,deflate=False)
    result=audit(source_path,source_page_1based,base_pdf,target_pdf,regions,placements)
    target_pdf.with_suffix('.raster-qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if not result['passed']:raise ValueError('Scanned prose changed native ink or original image programs')
    return result
