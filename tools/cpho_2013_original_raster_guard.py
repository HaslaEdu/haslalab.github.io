"""Document-only witness for old scan prose beside the original circle.

No protection pixels are excluded. Coarse expanded-guard changes are reported
verbatim and must be reproduced by language-erasure-only control. New prose
must change zero actual native ink and zero expanded native guard pixels.
"""
from pathlib import Path
import hashlib,json
import cv2,numpy as np
import pymupdf as fitz
from pdf_white_raster_original_style import _rgb,_box_mask,fill_rectangles,reviewed_backgrounds,sha
from pdf_original_graphics_ink import graphics_control
import cpho_2013_original_extract as source

EXPECTED_GEOMETRY='6f9c90be4ae19c75edea5702742d3cfad179d095a7e71dd684a3cab43fc8bfbb'
EXPECTED_GUARD_PIXELS=[[667,688],[667,689],[667,690],[663,691],[664,691],[665,691],[666,691],[667,691],[663,692]]

def pixels(mask):
    yy,xx=np.nonzero(mask);return[[int(x),int(y)]for y,x in zip(yy,xx)]

def geometry_sha(regions):
    values=[{k:r[k]for k in ['id','erase_rects','protected_rects','reviewed_blank_background_rects']}for r in regions]
    return hashlib.sha256(json.dumps(values,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def control(base,output,regions):
    with fitz.open(base)as doc:
        fills,_=fill_rectangles(regions,doc[0].rect)
        for rect in fills:doc[0].draw_rect(rect,color=None,fill=(1,1,1),overlay=True)
        doc.save(output,garbage=0,deflate=False)

def audit(base,erasure_control,proof,regions):
    if sha(source.SOURCE)!=source.SOURCE_SHA:raise ValueError('Wrong scan source')
    with fitz.open(source.SOURCE)as src,fitz.open(base)as a,fitz.open(erasure_control)as c,fitz.open(proof)as p:
        fills,protection=fill_rectangles(regions,src[2].rect)
        before,erased,after=_rgb(a[0],4),_rgb(c[0],4),_rgb(p[0],4)
        original=fitz.open(stream=graphics_control(src,src[2]),filetype='pdf')
        ink=_rgb(original[0],4).min(2)<250;original.close()
        old=_box_mask(ink.shape,fills,4)
        background=_box_mask(ink.shape,[r['rect']for r in reviewed_backgrounds(regions,src[2].rect,source.SOURCE_SHA)],4)
        explicit=_box_mask(ink.shape,protection,4)
        native=(ink&~(old|background))|(ink&explicit)
        guard=cv2.dilate(native.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
        deletion=(before!=erased).any(2);new=(erased!=after).any(2);whole=(before!=after).any(2)
        result=dict(profile='2013-p3-scan-circle-old-prose-guard-witness',source_sha256=source.SOURCE_SHA,
            geometry_sha256=geometry_sha(regions),base_sha256=sha(base),erasure_control_sha256=sha(erasure_control),proof_sha256=sha(proof),
            old_language_erasure_guard_pixels_xy=pixels(deletion&guard),source_to_proof_coarse_guard_pixels_xy=pixels(whole&guard),
            old_language_erasure_actual_native_ink_changed=int((deletion&native).sum()),
            new_language_actual_native_ink_changed=int((new&native).sum()),new_language_expanded_guard_changed=int((new&guard).sum()),
            source_to_proof_actual_native_ink_changed=int((whole&native).sum()),
            original_circle_prose_resampling_junction='Original mixed antialias samples are retained. All remaining coarse changes must be deletions of original prose, never new letters.',
            scale=4)
        result['passed']=(result['geometry_sha256']==EXPECTED_GEOMETRY
            and result['old_language_erasure_guard_pixels_xy']==EXPECTED_GUARD_PIXELS
            and result['source_to_proof_coarse_guard_pixels_xy']==EXPECTED_GUARD_PIXELS
            and all(result[k]==0 for k in ['old_language_erasure_actual_native_ink_changed',
                'new_language_actual_native_ink_changed','new_language_expanded_guard_changed',
                'source_to_proof_actual_native_ink_changed']))
        return result
