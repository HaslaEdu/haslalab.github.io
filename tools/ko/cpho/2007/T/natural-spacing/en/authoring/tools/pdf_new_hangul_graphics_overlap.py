"""Detect newly inserted Hangul covering actual native diagram/math ink."""
from pathlib import Path
import numpy as np
import pymupdf as fitz
from pdf_native_inline_reposition import _traces
from pdf_moved_native_ink import source_outline_reference
from pdf_original_graphics_ink import graphics_control

def audit(path,*,page_number=1,new_glyphs=None,scale=4):
    with fitz.open(path)as doc:
        page=doc[page_number-1]
        if new_glyphs is None:
            new_glyphs=[g for g in _traces(page)if g['font']=='Batang'and len(g['c'])==1
                        and 0xac00<=ord(g['c'])<=0xd7a3 and g['trace_gid']>=0]
        reference,matched=source_outline_reference(page,new_glyphs,scale=scale)
        control=fitz.open(stream=graphics_control(doc,page),filetype='pdf')
        p=control[0].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
        rgb=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)
        # Dark native foreground is protected. A pale table/background fill is
        # not mistaken for a mathematical stroke behind readable black prose.
        overlap=reference&(rgb.min(axis=2)<80)
        report=dict(method='Independent new Hangul outline reference versus clip-aware actual native non-text foreground.',
            scale=scale,new_glyphs=len(new_glyphs),new_reference_threshold=32,native_foreground_threshold=80,
            new_hangul_dark_pixels_over_native_foreground=int(overlap.sum()),source_outline_match=matched,
            passed=matched['passed']and not overlap.any())
        if overlap.any():
            yy,xx=np.nonzero(overlap);report['overlap_bbox']=[float(xx.min()/scale),float(yy.min()/scale),float((xx.max()+1)/scale),float((yy.max()+1)/scale)]
        control.close();return report
