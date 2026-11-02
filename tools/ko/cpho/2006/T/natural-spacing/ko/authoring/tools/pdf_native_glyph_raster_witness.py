"""Analysis-only native encoded-CID witness for one top-level source glyph.

Reuse the exact original font resource, encoded CID and measured native paint
state captured by the reviewed native-paint helper. No Unicode mathematical
text is regenerated. Publication PDFs are never modified by this module.
"""
from io import BytesIO
from pathlib import Path
import hashlib
import pikepdf
import pymupdf as fitz
import numpy as np
from pdf_native_glyph_promote import promote_native_glyphs
from pdf_native_inline_reposition import _inverse_vector,_traces


def replay(source,page_number,glyph,dx=0):
    native,qa=promote_native_glyphs(source,page_number,[glyph])
    records=qa['promoted_native_paints']
    if len(records)!=1:raise ValueError('A native glyph witness requires one original encoded paint')
    record=records[0]
    with pikepdf.open(BytesIO(native))as pdf:
        page=pdf.pages[0]
        matches=[name for name,obj in page.Resources.XObject.items()if str(obj.get('/Subtype'))=='/Form'
            and hashlib.sha256(obj.read_bytes()).hexdigest()==record['form_sha256']]
        if len(matches)!=1:raise ValueError('The native encoded paint Form is not unique')
        with fitz.open(stream=native,filetype='pdf')as doc:matrix=tuple(doc[0].transformation_matrix)
        tx,ty=_inverse_vector(matrix,float(dx),0)
        page.Contents=pdf.make_stream(('q 1 0 0 1 %.12g %.12g cm %s Do Q'%(tx,ty,matches[0])).encode('ascii'))
        buf=BytesIO();pdf.save(buf,compress_streams=False);result=buf.getvalue()
    with fitz.open(stream=result,filetype='pdf')as doc:
        actual=[g for g in _traces(doc[0])if g['c'].strip()and g['trace_gid']>=0]
    if len(actual)!=1:raise ValueError('A native encoded glyph reference painted extra or missing glyphs')
    g=actual[0]
    if not(g['c']==glyph['c']and g['font']==glyph['font']and g['trace_gid']==glyph['trace_gid']
        and abs(g['size']-glyph['size'])<1e-5 and abs(g['origin'][0]-glyph['origin'][0]-dx)<.001
        and abs(g['origin'][1]-glyph['origin'][1])<.001):raise ValueError('Native source glyph witness metadata differs')
    return result,dict(method='Exact original encoded CID/font/Tf/Tm/paint state in an isolated native Form; source default glyph hinting retained.',
        **record,dx=dx,original_font_programs_unchanged=qa['original_font_programs_unchanged'],publication_PDF_modified=False)


def audit(source,page_number,target,glyph,dx=0,scale=4):
    raw,report=replay(source,page_number,glyph,dx)
    with fitz.open(stream=raw,filetype='pdf')as ref,fitz.open(target)as final:
        def rgb(p):
            p=p.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
            return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)
        expected=rgb(ref[0]).min(axis=2)<32;actual=rgb(final[0]).min(axis=2)
    report.update(scale=scale,native_reference_dark_pixels=int(expected.sum()),missing_native_CID_reference_pixels=int((expected&(actual>=220)).sum()))
    report.update(source_sha256=hashlib.sha256(bytes(source)if isinstance(source,(bytes,bytearray))else Path(source).read_bytes()).hexdigest(),
        proof_sha256=hashlib.sha256(Path(target).read_bytes()).hexdigest(),source_page=page_number)
    report['passed']=report['native_reference_dark_pixels']>0 and report['missing_native_CID_reference_pixels']==0
    return report
