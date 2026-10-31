"""Reject overlapping new prose words and black-on-black native math cover.

An ink-loss test alone cannot distinguish an intact equation from new black
prose printed over its original black strokes. This read-only check intersects
independent new Hangul outlines with original mathematical outlines AND the
actual pre-Hangul native control, retaining the source's clipping behaviour.
"""
from io import BytesIO
from pathlib import Path
import hashlib
import pikepdf
import pymupdf as fitz
import numpy as np
from PIL import Image
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from pdf_moved_native_ink import source_outline_reference,_key

def word_overlaps(proof,composition,tolerance_y=.75):
    with pikepdf.open(proof)as pdf:
        resource=pdf.pages[0].Resources.Font.get('/KO_Natural_Batang')
        if resource is None:return dict(passed=True,words_checked=0,overlapping_word_advances=[])
        raw=resource.DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()
    font=fitz.Font(fontbuffer=raw);runs=[]
    for i,p in enumerate(composition['new_batang_placements']):
        x,y=p['point'];size=p['style']['size']
        width=sum(size/4 if c.isspace()else font.text_length(c,fontsize=size)for c in p['text'])
        runs.append(dict(index=i,text=p['text'],x=x,y=y,right=x+width,size=size))
    overlaps=[]
    for i,a in enumerate(runs):
        for b in runs[i+1:]:
            if abs(a['y']-b['y'])>tolerance_y:continue
            amount=min(a['right'],b['right'])-max(a['x'],b['x'])
            if amount>.1:overlaps.append(dict(first=a,second=b,overlap_pt=amount))
    return dict(method='New fixed-size Batang word advance intervals on the same physical prose row must not overlap.',
        words_checked=len(runs),row_tolerance_pt=tolerance_y,overlapping_word_advances=overlaps,passed=not overlaps)

def audit(proof,old_source,old_page,english_source,english_page,composition,control_png,scale=4):
    words=word_overlaps(proof,composition)
    with fitz.open(old_source)as old,fitz.open(english_source)as english,fitz.open(proof)as final:
        physical={(glyph_key(g),g['trace_gid'],g['render_mode'])for g in _traces(english[english_page-1])
            if g['c'].strip()and g['trace_gid']>=0 and g['render_mode']!=3}
        protected=[g for g in _traces(old[old_page-1])
            if(glyph_key(g),g['trace_gid'],g['render_mode'])in physical and g['c'].strip()and g['trace_gid']>=0]
        offsets={_key(g):s['dx']for s in composition['native_shifts']for g in s['glyphs']}
        new=[g for g in _traces(final[0])if g['font']=='Batang'and len(g['c'])==1 and 0xac00<=ord(g['c'])<=0xd7a3 and g['trace_gid']>=0]
        math,math_meta=source_outline_reference(old[old_page-1],protected,offsets,scale)
        text,text_meta=source_outline_reference(final[0],new,scale=scale)
    if not math_meta['passed']or not text_meta['passed']:
        return dict(passed=False,word_advance_audit=words,source_math_outline=math_meta,new_hangul_outline=text_meta)
    with Image.open(control_png)as image:control=np.array(image.convert('RGB'))
    if control.shape[:2]!=math.shape or text.shape!=math.shape:raise ValueError('Native control render dimensions differ')
    overlap=math&text&(control.min(axis=2)<80)
    result=dict(method='Independent original physical math outlines at requested dx intersect independent new Hangul outlines and actual clipped pre-Hangul control ink; black overprint is rejected even when no original black pixels disappear.',
        scale=scale,word_advance_audit=words,source_math_outline=math_meta,new_hangul_outline=text_meta,
        native_control_png=str(control_png),native_control_png_sha256=hashlib.sha256(Path(control_png).read_bytes()).hexdigest(),
        new_hangul_pixels_over_original_mathematical_text=int(overlap.sum()),passed=words['passed']and not overlap.any())
    if overlap.any():
        yy,xx=np.nonzero(overlap);result['overlap_bbox']=[float(xx.min()/scale),float(yy.min()/scale),float((xx.max()+1)/scale),float((yy.max()+1)/scale)]
    return result
