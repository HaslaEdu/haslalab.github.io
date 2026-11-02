"""Audit deliberate x movement of complete native mathematical graphics.

Only actual non-text ink inside an explicitly moved original Form/clip/vector
group is a motion region. All other native graphical pixels must be identical.
The source images, fraction paths and source Form programs remain native.
"""
from pathlib import Path
import math
import cv2
import numpy as np
import pymupdf as fitz
from pdf_native_inline_reposition import inspect_inline_groups
from pdf_original_text_ops import glyph_key
from pdf_original_graphics_ink import graphics_control

def _pixels(page,scale):
    p=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
    return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)

def audit(source,target,shifts,scale=4):
    inv=inspect_inline_groups(source,1);regions=[]
    def keys(glyphs):return{glyph_key(g)for g in glyphs if g['c'].strip()}
    for shift in shifts:
        selected=keys(shift['glyphs']);dx=shift['dx'];found=[]
        for group in inv['clip_groups']:
            members=keys(group['glyphs'])
            if members and members<=selected and group.get('known_rectangular_clips'):
                for rect in group.get('clip_rects',[]):
                    if rect is not None and fitz.Rect(rect).height<70:
                        found.append(dict(kind='complete original clip',rect=rect,operator_indices=group['operator_indices']))
        if 'form_path'in shift:
            matches=[g for g in inv['forms']if g['path']==shift['form_path']]
            if len(matches)!=1:raise ValueError('A moved native mathematical Form cannot be identified exactly')
            group=matches[0]
            if not keys(group['glyphs'])<=selected:raise ValueError('Incomplete mathematical Form geometry motion')
            r=fitz.Rect(group.get('native_page_bbox',[]))
            if r.is_empty:
                for g in group['glyphs']:
                    if g['c'].strip():r|=fitz.Rect(g['bbox'])
                r+=(-1,-1,1,1)
            if r.width>350 or r.height>100:
                raise ValueError('A moved native Form is not a reviewed inline-sized mathematical object')
            # The actual original Form/BBox is transformed through its entry
            # CTM. It includes native fraction/radical paths and bitmaps beyond
            # text glyph metrics, while the mask below still uses painted ink.
            found.append(dict(kind='complete original Form',rect=list(r),form_path=group['path'],
                painted_image_rects=group.get('painted_image_rects',[])))
        if 'image_path'in shift:
            matches=[g for g in inv.get('images',[])if g['path']==shift['image_path']]
            if len(matches)!=1:raise ValueError('A moved original mathematical image invocation cannot be identified exactly')
            image=matches[0];r=fitz.Rect(image['bbox'])
            if len(image['path'])!=1 or r.width>350 or r.height>100:
                raise ValueError('An original inline image needs a complete reviewed native mathematical container')
            found.append(dict(kind='complete original image invocation',rect=list(r),image_path=image['path'],
                original_raw_sha256=image['original_raw_sha256'],painted_image_rects=[list(r)]))
        for path in shift.get('vector_paths',[]):
            found.append(dict(kind='explicit original mathematical path',rect=path['rect'],operator_indices=path['operator_indices']))
        for item in found:regions.append(dict(item,dx=dx))
    with fitz.open(source)as src,fitz.open(target)as dst:
        a=fitz.open(stream=graphics_control(src,src[0]),filetype='pdf')
        b=fitz.open(stream=graphics_control(dst,dst[0]),filetype='pdf')
        old=_pixels(a[0],scale);new=_pixels(b[0],scale)
        old_area=np.zeros(old.shape[:2],bool);new_area=np.zeros(new.shape[:2],bool)
        for region in regions:
            r=fitz.Rect(region['rect'])
            for area,rect in[(old_area,r),(new_area,r+(region['dx'],0,region['dx'],0))]:
                x0,y0,x1,y1=[math.floor(v*scale)for v in rect]
                area[max(0,y0):min(area.shape[0],y1+2),max(0,x0):min(area.shape[1],x1+2)]=True
        # Only painted source/target graphical samples count. White background
        # or a large rectangle of prose is never silently made mutable.
        old_ink=(old.min(axis=2)<255)&old_area;new_ink=(new.min(axis=2)<255)&new_area
        motion=cv2.dilate((old_ink|new_ink).astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
        changed=np.any(old!=new,axis=2)
        report=dict(method='Original raw-token non-text controls; complete mathematical Form/clip/path membership and actual painted ink only.',
            selected_native_math_groups=regions,changed_actual_inline_math_graphical_pixels=int((changed&motion).sum()),
            changed_nonselected_native_graphical_pixels=int((changed&~motion).sum()),
            original_native_math_actual_graphics_pixels=int(old_ink.sum()),new_native_math_actual_graphics_pixels=int(new_ink.sum()))
        a.close();b.close()
    return motion,report
