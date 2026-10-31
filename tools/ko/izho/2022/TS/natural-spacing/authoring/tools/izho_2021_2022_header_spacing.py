"""Reviewed IZhO running-header compaction with an unchanged underline.

Only the left running header is packed. The separate page counter and all
body content stay fixed. A narrow original underline may intersect font metric
boxes; its actual pixels must nevertheless remain completely unchanged.
"""
import json,math
from pathlib import Path
import numpy as np
import pymupdf as fitz
from izho_natural_spacing import plan_page
from pdf_native_inline_reposition import reposition_inline,_traces
from pdf_original_text_ops import glyph_key
import izho_early_fixed_style as legacy
from pdf_original_graphics_ink import graphics_control
from pdf_text_motion_ink import ink_envelope

def apply(base_pdf,original_plan,placements):
    data=json.loads(Path(original_plan).read_text('utf8'))
    source=legacy.ROOT/data['source']
    original=fitz.open(source);fitz.TOOLS.set_small_glyph_heights(True)
    runs=legacy.runs_of(original[data['page']]);head=runs[(0,0,0)]
    baseline=head['origin'][1];size=head['size'];box=fitz.Rect(head['bbox'])
    if baseline>=60 or box.width<150 or box.x1>original[data['page']].rect.width*.7:
        raise ValueError('Not a reviewed single-column left running header')
    raw=bytes(base_pdf)if isinstance(base_pdf,(bytes,bytearray))else Path(base_pdf).read_bytes()
    doc=fitz.open(stream=raw,filetype='pdf');page=doc[0]
    rect=[box.x0-1,baseline-size,box.x1+1,baseline+.45*size]
    spec=plan_page(page,allowed_line_rects=[rect],prose_placements=placements)
    trace={glyph_key(c):c for c in _traces(page)};crossed=[]
    for drawing in page.get_drawings():
        r=fitz.Rect(drawing['rect']);pad=max(float(drawing.get('width')or 0)/2,.1)
        guard=r+(-pad,-pad,pad,pad)
        intersects=False
        for shift in spec['shifts']:
            for c in shift['glyphs']:
                bb=fitz.Rect(trace[glyph_key(c)]['bbox']);swept=bb|(bb+(shift['dx'],0,shift['dx'],0))
                if swept.intersects(guard):intersects=True
        if not intersects:continue
        is_underline=r.width>page.rect.width*.5 and r.height<3 and r.y0>=baseline-.1 and r.y1<baseline+4
        if not is_underline:raise ValueError('Header motion intersects a path other than the original thin running rule')
        crossed.append(list(r))
    # This opt-in is limited by the path classification above and followed by
    # strict actual-pixel verification; it does not authorize math exceptions.
    result,qa=reposition_inline(raw,1,shifts=spec['shifts'],reject_vector_overlap=False,text_shift_mode='ctm')
    final=fitz.open(stream=result,filetype='pdf')
    def pixels(pg):
        p=pg.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
        return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)
    a=pixels(page);b=pixels(final[0]);changed=np.any(a!=b,axis=2)
    outside=changed.copy();r=fitz.Rect(rect)+(-1,-1,1,1)
    x0,y0,x1,y1=[int(v*4)for v in r];outside[y0:y1,x0:x1]=False
    old_origins=[c['origin']for s in spec['shifts']for c in s['glyphs']]
    new_origins=[[c['origin'][0]+s['dx'],c['origin'][1]]for s in spec['shifts']for c in s['glyphs']]
    old_ink,_=ink_envelope(page,old_origins,4);new_ink,_=ink_envelope(final[0],new_origins,4)
    old_graphics=fitz.open(stream=graphics_control(doc,page),filetype='pdf')
    new_graphics=fitz.open(stream=graphics_control(final,final[0]),filetype='pdf')
    rules=[]
    for rect in crossed:
        r=fitz.Rect(rect);x0,y0,x1,y1=[math.floor(v*4)for v in r]
        def crop(pg):
            p=pg.get_pixmap(matrix=fitz.Matrix(4,4),clip=r,colorspace=fitz.csRGB,alpha=False)
            return np.frombuffer(p.samples,np.uint8)
        native_diff=int(np.any(crop(old_graphics[0]).reshape(-1,3)!=crop(new_graphics[0]).reshape(-1,3),axis=1).sum())
        composite=changed[y0:y1+1,x0:x1+1]
        ink=(old_ink|new_ink)[y0:y1+1,x0:x1+1]
        rules.append(dict(rect=list(r),composited_changed_pixels=int(composite.sum()),
            changed_pixels_outside_actual_old_and_new_header_text=int((composite&~ink).sum()),
            original_nontext_rule_changed_pixels=native_diff))
    old_graphics.close();new_graphics.close()
    qa.update(profile='Reviewed thin running-header underline; original geometry and all actual rule pixels unchanged.',
        changed_pixels_outside_header_band=int(outside.sum()),original_header_rules=rules,
        changed_page_counter_pixels=0,lines=spec['lines'])
    qa['passed']=qa['passed']and not outside.any()and not any(
        r['original_nontext_rule_changed_pixels']or r['changed_pixels_outside_actual_old_and_new_header_text']for r in rules)
    final.close();doc.close();original.close()
    if not qa['passed']:raise ValueError(('Actual header-rule or non-header pixels changed',
        dict(outside=qa['changed_pixels_outside_header_band'],rules=rules)))
    return result,qa
