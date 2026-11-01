"""Document-independent source-aware scan/replayed-math/new-prose pixel audit.

Caller owns reviewed language/math ROI journals, source font calibration, actual
new prose outlines/styles and semantic translation review. Run under page_worker.
The math control must be the exact pre-prose stage (original-math-first), while
prose_reference contains only the newly authored prose on an empty white page.
No source image is changed and no original mathematical symbol is retyped here.
"""
from pathlib import Path
import hashlib,math
from collections import Counter
import numpy as np
import pymupdf as fitz
import pikepdf
from pdf_original_raster_math import original_image_instances,program,program_sha
from pdf_native_inline_reposition import _multiply


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def render(path,page=1,scale=4):
    with fitz.open(path)as doc:
        pix=doc[page-1].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False)
    return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width).copy()
def include(mask,rect,scale,pad=0):
    x0,y0,x1,y1=rect
    a=max(0,math.floor(x0*scale)-pad);b=max(0,math.floor(y0*scale)-pad)
    c=min(mask.shape[1],math.ceil(x1*scale)+pad);d=min(mask.shape[0],math.ceil(y1*scale)+pad)
    mask[b:d,a:c]=True
def summary(mask,scale):
    yy,xx=np.nonzero(mask)
    return dict(pixels=int(mask.sum()),bbox=None if not len(xx)else[int(xx.min())/scale,int(yy.min())/scale,(int(xx.max())+1)/scale,(int(yy.max())+1)/scale])

def audit_scan_page(source_path,source_page_1based,final_pdf,math_control_pdf,prose_reference_pdf,*,
        language_erase_rects,new_prose_rects,original_inline_math_rects=(),moved_inline_math_rects=(),
        protected_source_rects=(),native_header_change_rects=(),replayed_math_records=(),reviewed_blank_records=(),scale=4):
    if scale!=4:raise ValueError('Production audit uses exactly four-times source page rendering')
    before=render(source_path,source_page_1based,scale);after=render(final_pdf,1,scale)
    control=render(math_control_pdf,1,scale);prose=render(prose_reference_pdf,1,scale)
    if not(before.shape==after.shape==control.shape==prose.shape):raise ValueError('Audit page geometries differ')
    allowed=np.zeros(before.shape,bool);language=np.zeros(before.shape,bool);old_math=np.zeros(before.shape,bool)
    for rect in language_erase_rects:include(language,rect,scale,1);include(allowed,rect,scale,1)
    for rect in original_inline_math_rects:include(old_math,rect,scale,1);include(allowed,rect,scale,1)
    for rect in list(new_prose_rects)+list(moved_inline_math_rects):include(allowed,rect,scale,1)
    native_headers=np.zeros(before.shape,bool)
    for rect in native_header_change_rects:include(native_headers,rect,scale,3);include(allowed,rect,scale,3)
    protected=np.zeros(before.shape,bool)
    for rect in protected_source_rects:include(protected,rect,scale)
    outside=(before!=after)&~allowed
    stationary=(before<160)&(after>240)&~language&~old_math&~native_headers
    protected_loss=(before<160)&(after>240)&protected
    existing=control<180;new=prose<180
    collision=existing&new;blank=np.zeros(before.shape,bool)
    for record in reviewed_blank_records:
        if record.get('reviewed')is not True or not record.get('evidence')or record.get('source_sha256')!=sha(source_path):raise ValueError('Blank background needs reviewed original-source evidence and exact source hash')
        include(blank,record['rect'],scale)
    for rect in list(protected_source_rects)+list(original_inline_math_rects)+list(moved_inline_math_rects):
        mask=np.zeros(before.shape,bool);include(mask,rect,scale);blank[mask]=False
    collision_after=collision&~blank;missing_new=new&(after>240)
    with pikepdf.open(source_path)as src,pikepdf.open(final_pdf)as final:
        source_page=src.pages[source_page_1based-1];page=final.pages[0]
        expected=original_image_instances(source_page,source_page.Resources)
        with fitz.open(source_path)as doc:inverse=~doc[source_page_1based-1].transformation_matrix
        for atom in replayed_math_records:
            delta=fitz.Point(atom['dx'],0)*inverse-fitz.Point(0,0)*inverse
            ctm=_multiply(tuple(atom['source_image_ctm']),(1,0,0,1,delta.x,delta.y))
            expected[(atom['image_program_sha256'],tuple(round(v,8)for v in ctm))]+=1
        images_unchanged=original_image_instances(page,page.Resources)==expected
        old_fonts=source_page.Resources.get('/Font',{})
        new_fonts=page.Resources.get('/Font',{})
        font_changes=[str(name)for name,font in old_fonts.items()if name not in new_fonts or program_sha(font)!=program_sha(new_fonts[name])]
        group_same=program(source_page.obj.get('/Group'))==program(page.obj.get('/Group'))
    report=dict(source=str(source_path),source_sha256=sha(source_path),source_page=source_page_1based,
        final=str(final_pdf),final_sha256=sha(final_pdf),math_control_sha256=sha(math_control_pdf),prose_reference_sha256=sha(prose_reference_pdf),render_scale=scale,
        original_encoded_image_programs_masks_palettes_icc_and_declared_ctms_retained=images_unchanged,original_native_font_program_changes=font_changes,original_pagegroup_unchanged=group_same,
        outside_declared_language_and_math_motion=summary(outside,scale),stationary_original_dark_ink_lost=summary(stationary,scale),independent_protected_source_ink_lost=summary(protected_loss,scale),
        new_prose_overlap_original_or_replayed_nonlanguage_ink=summary(collision_after,scale),raw_collision_including_reviewed_scan_background=summary(collision,scale),
        new_prose_expected_dark_pixels_missing=summary(missing_new,scale),reviewed_blank_background_records=list(reviewed_blank_records),
        thresholds=dict(source_deep_dark=160,new_prose_and_existing_ink=180,actual_missing_white=240),
        note='Only declared language and inline mathematical motion may change; source display/figure rects remain independently protected. Blank records never white-fill anything and exclude every protected/math region. New-prose final visibility is independently required.',
        passed=images_unchanged and not font_changes and group_same and not any(mask.any()for mask in[outside,stationary,protected_loss,collision_after,missing_new]))
    return report
