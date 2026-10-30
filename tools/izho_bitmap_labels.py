"""Translate explicitly reviewed bitmap-language labels as PDF-only overlays.

The source image objects and their transforms remain intact. Background paint
and Korean text are limited to declared language regions. Figure geometry and
visible non-language marks are audited separately from those regions.
"""
from __future__ import annotations
import io,json,math,hashlib
from pathlib import Path
import cv2
import numpy as np
import pymupdf as fitz
from PIL import Image
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from pdf_original_style_fonts import FONTS,korean_font
from pdf_original_style_audit import audit
from izho_early_fixed_style import native_image_programs,native_font_programs
from izho_bitmap_features import feature_masks


def rgb(page,scale=4):
    pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
    return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)


def glyph_bounds(path,text,size,x,y,rotate=0):
    font=TTFont(path);glyphs=font.getGlyphSet();cmap=font.getBestCmap();upem=font['head'].unitsPerEm
    boxes=[];cursor=x
    for char in text:
        name=cmap[ord(char)];pen=BoundsPen(glyphs);glyphs[name].draw(pen)
        if pen.bounds:
            a,b,c,d=pen.bounds;boxes.append(fitz.Rect(cursor+a*size/upem,y-d*size/upem,cursor+c*size/upem,y-b*size/upem))
        cursor+=font['hmtx'][name][0]*size/upem
    font.close();box=fitz.Rect(boxes[0])
    for item in boxes[1:]:box|=item
    if rotate:
        if rotate not in [90,180,270]:raise ValueError('Bitmap label rotation must be a right angle')
        box=(box+(-x,-y,-x,-y))*fitz.Matrix(-rotate)+(x,y,x,y)
    return box


def image_rect(info,rect):
    a,b,c,d,e,f=info['transform']
    if abs(b)>1e-8 or abs(c)>1e-8 or a<=0 or d<=0:raise ValueError('Review rotated/reflected bitmap transforms explicitly')
    x0,y0,x1,y1=rect
    return fitz.Rect(e+x0*a/info['width'],f+y0*d/info['height'],e+x1*a/info['width'],f+y1*d/info['height'])


def pixel_mask(target,rect,scale=4):
    x0=max(0,math.floor(rect.x0*scale));y0=max(0,math.floor(rect.y0*scale))
    x1=min(target.shape[1],math.ceil(rect.x1*scale));y1=min(target.shape[0],math.ceil(rect.y1*scale))
    target[y0:y1,x0:x1]=True


def subtract(rect,cut):
    rect=fitz.Rect(rect);hit=rect&cut
    if hit.is_empty:return [list(rect)]
    result=[]
    for r in [fitz.Rect(rect.x0,rect.y0,rect.x1,hit.y0),fitz.Rect(rect.x0,hit.y1,rect.x1,rect.y1),
              fitz.Rect(rect.x0,hit.y0,hit.x0,hit.y1),fitz.Rect(hit.x1,hit.y0,rect.x1,hit.y1)]:
        if not r.is_empty:result.append(list(r))
    return result


def local_background(pixels,box):
    """Fit the smooth dark background; robustly exclude text and bright marks."""
    h,w=pixels.shape[:2];x0,y0,x1,y1=box
    a=max(0,x0-6);b=max(0,y0-6);c=min(w,x1+6);d=min(h,y1+6)
    yy,xx=np.mgrid[b:d,a:c];x=(xx-(x0+x1)/2)/max(1,x1-x0);y=(yy-(y0+y1)/2)/max(1,y1-y0)
    basis=np.stack([np.ones_like(x),x,y,x*x,x*y,y*y],axis=-1).reshape(-1,6)
    colors=pixels[b:d,a:c].reshape(-1,3).astype(float)
    perimeter=((xx<x0-1)|(xx>=x1+1)|(yy<y0-1)|(yy>=y1+1)).reshape(-1)
    valid=perimeter&(colors.min(1)<135)
    if valid.sum()<12:raise ValueError('Insufficient clean bitmap background samples')
    for _ in range(4):
        coefficients=np.linalg.lstsq(basis[valid],colors[valid],rcond=None)[0]
        residual=np.sqrt(((basis@coefficients-colors)**2).sum(1))
        valid=perimeter&(colors.min(1)<135)&(residual<=max(6,float(np.quantile(residual[valid],.8))))
    yy,xx=np.mgrid[y0:y1,x0:x1];x=(xx-(x0+x1)/2)/max(1,x1-x0);y=(yy-(y0+y1)/2)/max(1,y1-y0)
    basis=np.stack([np.ones_like(x),x,y,x*x,x*y,y*y],axis=-1)
    return np.clip(basis@coefficients,0,255)


def append_rects(doc,page,rects):
    if not rects:return
    stream=['q']
    for rect,color in rects:
        r=fitz.Rect(rect);y=page.rect.height-r.y1
        stream.append(f'{color[0]:.6f} {color[1]:.6f} {color[2]:.6f} rg {r.x0:.9f} {y:.9f} {r.width:.9f} {r.height:.9f} re f')
    stream.append('Q');xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,'\n'.join(stream).encode('ascii'))
    refs=page.get_contents()+[xref];doc.xref_set_key(page.xref,'Contents','['+' '.join(f'{r} 0 R'for r in refs)+']')


def protect_original_graphics(doc,page,original_contents,mask,language_ink):
    """Exclude visible source marks from all newly painted label content."""
    if not mask.any():return
    holes=cv2.dilate(mask.astype(np.uint8),np.ones((5,5),np.uint8)).astype(bool)&~language_ink
    commands=['q',f'0 0 {page.rect.width:.9f} {page.rect.height:.9f} re']
    for y,row in enumerate(holes):
        x=0
        while x<len(row):
            if not row[x]:x+=1;continue
            left=x
            while x<len(row)and row[x]:x+=1
            # Clockwise holes and counterclockwise page boundary form one
            # nonzero-winding clip, with no antialiased internal seams.
            commands.append(f'{left/4:.9f} {page.rect.height-y/4:.9f} {(x-left)/4:.9f} -.250000000 re')
    commands.append('W n');prefix=doc.get_new_xref();doc.update_object(prefix,'<<>>');doc.update_stream(prefix,'\n'.join(commands).encode('ascii'))
    suffix=doc.get_new_xref();doc.update_object(suffix,'<<>>');doc.update_stream(suffix,b'Q')
    refs=original_contents+[prefix]+[xref for xref in page.get_contents()if xref not in original_contents]+[suffix]
    doc.xref_set_key(page.xref,'Contents','['+' '.join(f'{r} 0 R'for r in refs)+']')


def apply(source,source_page,base,target,labels):
    source=Path(source);base=Path(base);target=Path(target)
    original=fitz.open(source);source_pg=original[source_page-1]
    before_doc=fitz.open(base);before=rgb(before_doc[0]);doc=fitz.open(base);page=doc[0]
    info=source_pg.get_image_info(xrefs=True,hashes=True)
    allowed=np.zeros(before.shape[:2],bool);graphics=np.zeros(before.shape[:2],bool);language_ink=np.zeros(before.shape[:2],bool)
    image_cache={};font_cache={};rectangles=[];placements=[];language_rects=[]
    original_contents=page.get_contents()
    by_role={}
    for label in labels:by_role[label['role']]=by_role.get(label['role'],'')+label['text']
    for role,text in by_role.items():
        _,fontpath=korean_font('',0,text,override=role,cache_dir=Path(__file__).resolve().parents[1]/'tmp/izho-original-style/fonts')
        alias='KO_BITMAP_'+role.replace('-','_');page.insert_font(fontname=alias,fontfile=str(fontpath))
        font_cache[role]=(alias,fitz.Font(fontfile=str(FONTS[role])))
    for label in labels:
        image=info[label['image']];index=image['xref']
        if index not in image_cache:
            raw=original.extract_image(index)['image'];image_cache[index]=np.asarray(Image.open(io.BytesIO(raw)).convert('RGB'))
        pixels=image_cache[index];height,width=pixels.shape[:2]
        assert width==image['width']and height==image['height']
        a,b,c,d,e,f=image['transform'];px,py=label['point_px'];point=fitz.Point(e+px*a/width,f+py*d/height)
        alias,font=font_cache[label['role']];textwidth=font.text_length(label['text'],fontsize=label['size'])
        rotate=label.get('rotate',0)
        if rotate not in [0,90,180,270]:raise ValueError('Bitmap label rotation must be a right angle')
        if label.get('align')=='right':
            if rotate==0:point.x-=textwidth
            else:
                angle=math.radians(rotate);point.x-=textwidth*math.cos(angle);point.y+=textwidth*math.sin(angle)
        new_bounds=glyph_bounds(FONTS[label['role']],label['text'],label['size'],point.x,point.y,rotate=rotate)
        old=label['source_ink_rect_px'];pad=label.get('erase_padding_px',2)
        if not isinstance(pad,int)or not 0<=pad<=4:raise ValueError('Bitmap erase padding requires a reviewed integer from0 to4 pixels')
        x0=max(0,old[0]-pad);y0=max(0,old[1]-pad);x1=min(width,old[2]+pad);y1=min(height,old[3]+pad)
        erase=image_rect(image,[x0,y0,x1,y1]);language=(erase|new_bounds)+(-.75,-.75,.75,.75)
        language_rects.append(language);pixel_mask(allowed,language)
        restore_count=0;protected_count=0
        if label['background']=='white':
            rectangles.append((erase,(1,1,1)));restore_count=(x1-x0)*(y1-y0)
            # Every visible original mark outside the original word's rectangle
            # stays protected, including lines/points that share the new label ROI.
            roi=[max(0,int((language.x0-e)*width/a)),max(0,int((language.y0-f)*height/d)),
                 min(width,math.ceil((language.x1-e)*width/a)),min(height,math.ceil((language.y1-f)*height/d))]
            for iy in range(roi[1],roi[3]):
                for ix in range(roi[0],roi[2]):
                    if x0<=ix<x1 and y0<=iy<y1:continue
                    if pixels[iy,ix].min()<220:
                        pixel_mask(graphics,image_rect(image,[ix,iy,ix+1,iy+1]));protected_count+=1
        elif label['background']=='local_polynomial_ink':
            background=local_background(pixels,[x0,y0,x1,y1]);crop=pixels[y0:y1,x0:x1].astype(float);difference=crop-background
            ink=(difference[:,:,0]>8)&(difference[:,:,1]>6)&(difference[:,:,2]>3)
            ink=cv2.dilate(ink.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)&(difference[:,:,0]>2)&(difference[:,:,1]>1)
            visible_graphic=(difference[:,:,1]>20)&(difference[:,:,0]<12)&(crop[:,:,1]-crop[:,:,0]>35)&~ink
            visible_graphic=cv2.dilate(visible_graphic.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)&~ink
            for iy,ix in zip(*np.where(np.ones(ink.shape,bool))):
                color=np.rint(background[iy,ix]).astype(int)/255
                # Slight overlap prevents antialiased seams between background
                # cells from revealing the erased source letters underneath.
                rectangles.append((image_rect(image,[x0+ix,y0+iy,x0+ix+1,y0+iy+1])+(-.26,-.26,.26,.26),tuple(color)));restore_count+=1
            for iy,ix in zip(*np.where(visible_graphic)):
                rect=image_rect(image,[x0+ix,y0+iy,x0+ix+1,y0+iy+1]);pixel_mask(graphics,rect);protected_count+=1
            # The visible pale glyphs are prose, including pixels produced by
            # interpolation between a white letter and a nearby coloured curve.
            prose_region=np.zeros(before.shape[:2],bool);pixel_mask(prose_region,erase)
            pixels_before=before.astype(np.int16)
            language_ink|=prose_region&(pixels_before[:,:,0]>40)&(pixels_before[:,:,0]>=pixels_before[:,:,1]-15)
        else:raise ValueError('Unsupported reviewed bitmap background')
        placements.append(dict(**label,language_rect_pdf=list(language),korean_ink_rect_pdf=list(new_bounds),
            original_image_rect_pdf=list(image['bbox']),original_image_digest=image['digest'].hex(),
            baseline_pdf=point.y,korean_start_pdf=list(point),restored_source_pixel_cells=restore_count,
            visible_graphic_source_pixel_cells_protected=protected_count))
    # Reviewed picture-wide masks include planet disks, neutral asteroid dots
    # and coloured orbit strokes, even when they touch a language-region edge.
    mandatory=np.zeros(before.shape[:2],bool);feature_reports=[]
    for label in labels:
        profile=label.get('protect_features')
        if not profile:continue
        image=info[label['image']];pixels=image_cache[image['xref']]
        boxes=[row['source_ink_rect_px']for row in labels if row['image']==label['image']]
        for kind,source_mask in feature_masks(pixels,profile,boxes).items():
            page_mask=np.zeros(before.shape[:2],bool)
            for iy,ix in zip(*np.where(source_mask)):
                pixel_mask(page_mask,image_rect(image,[ix,iy,ix+1,iy+1]))
            mandatory|=page_mask
            feature_reports.append(dict(image=label['image'],kind=kind,source_pixel_cells=int(source_mask.sum()),
                page_pixels=int(page_mask.sum()),page_pixels_inside_language_regions=int((page_mask&allowed).sum())))
    language_ink&=~mandatory;graphics|=mandatory
    append_rects(doc,page,rectangles)
    for row in placements:
        alias,_=font_cache[row['role']];page.insert_text(row['korean_start_pdf'],row['text'],fontname=alias,fontsize=row['size'],color=row['color'],rotate=row.get('rotate',0))
    graphics&=~language_ink
    protect_original_graphics(doc,page,original_contents,graphics,language_ink)
    doc.save(target,garbage=4,deflate=False);doc.close();final=fitz.open(target);after=rgb(final[0]);delta=np.any(before!=after,axis=2)
    outside=int((delta&~allowed).sum());hidden_graphics=int((delta&graphics).sum())
    spec=json.loads(base.with_suffix('.audit-spec.json').read_text('utf8'))
    spec['allowed_rects'].extend([list(r)for r in language_rects]);protected=spec.get('protected_rects',[])
    for region in language_rects:protected=[piece for rect in protected for piece in subtract(rect,region)]
    spec['protected_rects']=protected;spec['raster_language_rects']=[list(r)for r in language_rects]
    target.with_suffix('.audit-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    result=audit(source,target,spec)
    def drawings(pg):return [{k:v for k,v in row.items()if k!='seqno'}for row in pg.get_drawings()]
    original_drawings=drawings(source_pg);new_drawings=drawings(final[0]);original_vectors_preserved=original_drawings==new_drawings[:len(original_drawings)]
    def image_geometry(pg):return sorted((im['digest'].hex(),tuple(im['bbox']),tuple(im['transform']))for im in pg.get_image_info(hashes=True))
    original_images=image_geometry(source_pg);final_images=image_geometry(final[0])
    image_unchanged=original_images==final_images and native_image_programs(source,source_page)==native_image_programs(target,1)
    fonts_unchanged=all(row in native_font_programs(target,1)for row in native_font_programs(source,source_page))
    result.update(source_font_programs_and_names_unchanged=fonts_unchanged,source_images_bytes_and_rects_unchanged=image_unchanged,
        source_vector_drawings_unchanged=original_drawings==new_drawings,source_original_vector_drawings_preserved=original_vectors_preserved,
        raster_language_overlays=placements,raster_language_region_count=len(labels),raster_added_background_paths=len(new_drawings)-len(original_drawings),
        changed_pixels_outside_raster_language_regions=outside,changed_pixels_in_visible_raster_graphics=hidden_graphics,
        original_bitmap_visual_pixels_unchanged_outside_language_regions=not outside,
        additional_clipped_reuses_of_unchanged_original_image=0,no_new_bitmap_pixel_data=True,
        original_visible_raster_graphics_excluded_from_new_paint=bool(graphics.any()),
        native_picture_feature_masks=feature_reports,
        changed_native_picture_feature_pixels_inside_language_regions=int((delta&mandatory&allowed).sum()),
        changed_native_picture_feature_pixels_outside_language_regions=int((delta&mandatory&~allowed).sum()),
        raster_font_metadata_note='The bitmap supplies no font metadata. Family, size and baseline are measured estimates recorded in the source plan.',
        full_figure_pixels_unchanged=False)
    if hidden_graphics:
        yy,xx=np.where(delta&graphics);errors=np.abs(before[yy,xx].astype(int)-after[yy,xx].astype(int))
        result['visible_raster_graphic_max_rgb_delta']=int(errors.max())
        result['visible_raster_graphic_delta_samples']=[dict(point=[float(x/4),float(y/4)],before=before[y,x].tolist(),after=after[y,x].tolist())for y,x in zip(yy[:40],xx[:40])]
    final[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(target.with_name(target.stem+'-proof.png'))
    final.close();before_doc.close();original.close()
    if outside or hidden_graphics or result['native_glyphs_changed']or result['protected_glyphs_selected_for_erasure']or result['changed_pixels_in_native_glyph_neighborhood']or result['changed_pixels_outside_prose']or not image_unchanged or not fonts_unchanged or not original_vectors_preserved:
        target.with_suffix('.raster-failure.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        raise ValueError('Bitmap-language overlay changed protected original content')
    return result
