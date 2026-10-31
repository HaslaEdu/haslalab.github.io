"""One opt-in original-prose deletion at an expanded graphics guard.

The source's 为 glyph touches one dilated guard pixel beside the8/21 fraction
line. The actual fraction-line ink is unchanged. This profile never removes a
rectangle from a protection mask and never permits new ink in the guard.
"""
import hashlib,json
import numpy as np
import pymupdf as fitz
import cpho_2013_original_extract as b
import pdf_original_graphics_ink as graphics
from pdf_original_text_ops import suppress_prose

EXPECTED_CHAR=dict(c='为',font='SimSun',size=10.5600004196167,origin=[127.5715103149414,174.25994873046875])
EXPECTED_PIXELS_XY=[[550,675]]

def rgb(page):
    pix=page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
    return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)

def pixels(mask):
    yy,xx=np.nonzero(mask);return [[int(x),int(y)]for y,x in zip(yy,xx)]

def audit(source,control,proof,selected):
    if hashlib.sha256(b.SOURCE.read_bytes()).hexdigest()!=b.SOURCE_SHA:raise ValueError('Prose-guard profile requires its exact original')
    matching=[g for g in selected if all(g[k]==v for k,v in EXPECTED_CHAR.items())]
    if len(matching)!=1:raise ValueError('The exact reviewed original 为 glyph is not selected prose')
    with fitz.open(source)as src,fitz.open(control)as ctl,fitz.open(proof)as target:
        nontext=fitz.open(stream=graphics.graphics_control(src,src[0]),filetype='pdf')
        actual=rgb(nontext[0]).min(axis=2)<250;guard=graphics.graphics_ink_mask(src,src[0],4)
        a,c,p=rgb(src[0]),rgb(ctl[0]),rgb(target[0])
        raw,n=suppress_prose(source,1,matching)
        if n!=1:raise ValueError('Isolated original-prose witness did not remove exactly one glyph')
        witness=fitz.open(stream=raw,filetype='pdf');one=rgb(witness[0])
        old_delta=np.any(a!=c,axis=2);new_delta=np.any(c!=p,axis=2);full_delta=np.any(a!=p,axis=2);single_delta=np.any(a!=one,axis=2)
        result=dict(profile='2013-p1-selected-wei-prose-only-guard-pixel',source_sha256=b.SOURCE_SHA,
            original_selected_glyph=EXPECTED_CHAR,expected_source_guard_pixels_xy=EXPECTED_PIXELS_XY,
            isolated_glyph_suppression_guard_pixels_xy=pixels(single_delta&guard),
            isolated_glyph_suppression_actual_nontext_changed=int((single_delta&actual).sum()),
            source_to_control_guard_pixels_xy=pixels(old_delta&guard),
            source_to_control_actual_nontext_changed=int((old_delta&actual).sum()),
            source_to_proof_guard_pixels_xy=pixels(full_delta&guard),
            source_to_proof_actual_nontext_changed=int((full_delta&actual).sum()),
            control_to_proof_guard_changed=int((new_delta&guard).sum()),
            control_to_proof_actual_nontext_changed=int((new_delta&actual).sum()),
            mask_rectangles_removed=0,source_actual_ink_threshold=250,dilation_guard_pixels=1,scale=4)
        result['passed']=(result['isolated_glyph_suppression_guard_pixels_xy']==EXPECTED_PIXELS_XY
            and result['source_to_control_guard_pixels_xy']==EXPECTED_PIXELS_XY
            and result['source_to_proof_guard_pixels_xy']==EXPECTED_PIXELS_XY
            and all(result[k]==0 for k in ['isolated_glyph_suppression_actual_nontext_changed','source_to_control_actual_nontext_changed',
                'source_to_proof_actual_nontext_changed','control_to_proof_guard_changed','control_to_proof_actual_nontext_changed']))
        witness.close();nontext.close()
    return result
