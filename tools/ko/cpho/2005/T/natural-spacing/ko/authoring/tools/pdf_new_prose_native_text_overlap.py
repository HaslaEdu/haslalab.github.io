"""Read-only collision test for translated prose and original native math text.

This complements pdf_new_hangul_graphics_overlap: unchanged black math ink
can still be illegible if new black prose is painted through it. A math-only
control retains the exact native CIDs/clips/painting; no math is retyped.
"""
from collections import Counter,defaultdict
from pathlib import Path
import hashlib
import numpy as np
import pymupdf as fitz
from pdf_native_inline_reposition import _traces,reposition_inline
from pdf_native_script_motion_audit import _key,_id
from pdf_moved_native_ink import source_outline_reference
from pdf_original_graphics_ink import graphics_control


def audit(path,*,page_number=1,native_glyphs,shifts=None,prose_glyphs=None,
          scale=4,tolerance_pt=.001):
    """Compare actual native-text dark ink with independent new-prose outlines.

    native_glyphs is the physical glyph list in the immutable input and shifts
    is its displacement journal. By default every other visible final glyph
    is treated as prose. That reviewed profile requires it to be top-level;
    erasure inside a private/clipped Form fails closed. Callers with such Forms
    must supply their complete, explicitly identified prose_glyphs list.
    """
    offsets=defaultdict(list)
    for s in shifts or[]:
        for g in s['glyphs']:offsets[_key(g)].append(s['dx'])
    with fitz.open(path)as doc:
        page=doc[page_number-1];rows=_traces(page)
        visible=[g for g in rows if g['c'].strip()and g['trace_gid']>=0 and g['render_mode']!=3]
        buckets=defaultdict(list)
        for i,g in enumerate(visible):buckets[_id(g)].append((i,g))
        keep=set()
        for g in native_glyphs:
            if not g['c'].strip()or g.get('trace_gid',g.get('gid',-1))<0 or g.get('render_mode')==3:continue
            values=offsets.get(_key(g),[0.])
            if max(values)-min(values)>tolerance_pt:raise ValueError('Conflicting original native displacement')
            expected=[g['origin'][0]+values[0],g['origin'][1]]
            candidates=[(i,h)for i,h in buckets[_id(g)]if i not in keep]
            if not candidates:raise ValueError('Original native glyph signature missing in final collision control')
            i,h=min(candidates,key=lambda v:sum(abs(a-b)for a,b in zip(v[1]['origin'],expected)))
            if max(abs(a-b)for a,b in zip(h['origin'],expected))>tolerance_pt:
                raise ValueError('Original native glyph position missing in final collision control')
            keep.add(i)
        if prose_glyphs is None:prose=[g for i,g in enumerate(visible)if i not in keep]
        else:
            wanted=Counter(_key(g)for g in prose_glyphs);prose=[]
            for i,g in enumerate(visible):
                if wanted[_key(g)]:
                    if i in keep:raise ValueError('A prose collision mask selected original native mathematics')
                    wanted[_key(g)]-=1;prose.append(g)
            if any(wanted.values()):raise ValueError('A declared translated prose glyph was not found')
        mask,match=source_outline_reference(page,prose,scale=scale)
        raw,erasure=reposition_inline(path,page_number,erased_glyphs=prose)
        with fitz.open(stream=raw,filetype='pdf')as native:
            p=native[0].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
            math_rgb=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()
        with fitz.open(stream=graphics_control(doc,page),filetype='pdf')as graphics:
            p=graphics[0].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
            graphics_rgb=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)
            # Non-text foreground is checked separately. This difference
            # isolates real font ink, including its original clipping.
            native_text=(math_rgb.min(axis=2)<80)&(graphics_rgb.min(axis=2)>=80)
            overlap=mask&native_text
    q=dict(path=str(path),sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),page=page_number,
        method='Independent prose glyph outlines versus exact native-CID control minus clip-aware non-text control.',
        scale=scale,native_physical_glyphs=len(keep),translated_prose_glyphs=len(prose),
        prose_outline_match=match,native_control_erasure_qa=erasure,
        dark_prose_pixels_over_native_text=int(overlap.sum()),passed=match['passed']and not overlap.any())
    if overlap.any():
        yy,xx=np.nonzero(overlap);q['overlap_bbox']=[float(xx.min()/scale),float(yy.min()/scale),float((xx.max()+1)/scale),float((yy.max()+1)/scale)]
    return q
