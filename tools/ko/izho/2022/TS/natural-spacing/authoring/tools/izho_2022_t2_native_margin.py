"""Restore one original native g above the original picture's white margin."""
from io import BytesIO
import hashlib
import numpy as np
import pymupdf as fitz
from pdf_native_inline_reposition import _traces
from pdf_native_glyph_promote import promote_native_glyphs
from pdf_moved_native_ink import source_outline_reference
from pdf_original_graphics_ink import graphics_control
from pdf_text_motion_ink import ink_envelope

def apply(raw):
    doc=fitz.open(stream=raw,filetype='pdf');page=doc[0]
    glyphs=[g for g in _traces(page)if g['c']=='𝑔'and abs(g['origin'][0]-355.3146667480469)<.001
            and abs(g['origin'][1]-498.5999755859375)<.001]
    if len(glyphs)!=1:raise ValueError('Reviewed native-g margin profile does not match this proof')
    glyph=glyphs[0]
    if glyph['font']!='CIDFont+F6'or glyph['trace_gid']!=1859 or abs(glyph['size']-11.259224891662598)>.0001:
        raise ValueError('Original native g font/GID/point size changed')
    def pixels(pg):
        p=pg.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
        return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)
    before=pixels(page);reference,source_match=source_outline_reference(page,[glyph],scale=4)
    missing=reference&(before.min(axis=2)>=220)
    control=fitz.open(stream=graphics_control(doc,page),filetype='pdf');old_graphics=pixels(control[0])
    if int(missing.sum())!=8 or not np.all(old_graphics[missing]==255):
        raise ValueError('Expected eight hidden pixels are not confined to the original white graphic margin')
    promoted,promotion=promote_native_glyphs(raw,1,glyphs)
    final=fitz.open(stream=promoted,filetype='pdf');after=pixels(final[0])
    after_control=fitz.open(stream=graphics_control(final,final[0]),filetype='pdf')
    changed=np.any(before!=after,axis=2);envelope,_=ink_envelope(final[0],[glyph['origin']],4)
    if np.any(changed&~envelope)or not np.all(old_graphics[changed]==255):
        raise ValueError('Native promotion changed anything except g over the original white margin')
    graphics_diff=int(np.any(old_graphics!=pixels(after_control[0]),axis=2).sum())
    if graphics_diff or np.any(reference&(after.min(axis=2)>=220)):
        raise ValueError('Native picture geometry changed or original g still loses actual ink')
    yy,xx=np.nonzero(changed)
    report=dict(profile='2022T2 original native g over an opaque original image white top margin; exact native paint promoted without x/y/font changes.',
        packed_source_sha256=hashlib.sha256(raw).hexdigest(),output_sha256=hashlib.sha256(promoted).hexdigest(),
        promoted_glyph=glyph,original_missing_deep_dark_pixels=8,final_missing_deep_dark_pixels=0,
        composited_white_margin_changed_pixels=int(changed.sum()),
        reviewed_white_margin_changed_pixel_coordinates_4x=[[int(x),int(y)]for x,y in zip(xx,yy)],
        all_changes_over_original_exact_white_graphics=True,actual_nontext_graphics_changed_pixels=graphics_diff,
        source_outline_match=source_match,native_promotion_qa=promotion,passed=True)
    after_control.close();final.close();control.close();doc.close()
    return promoted,report
