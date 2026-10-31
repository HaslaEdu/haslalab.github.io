"""Replay one original complete Form, retaining native programs and clipping.

This is a read-only diagnostic reference. It never edits a publication PDF.
The selected original Form stream and resources are copied without rewriting;
only other painting on its ancestor invocation paths is suppressed. Original
ancestor graphics state, clipping and Page/Group remain in effect.
"""
from io import BytesIO
from pathlib import Path
import hashlib
import pikepdf
import pymupdf as fitz
import numpy as np
from pdf_native_inline_reposition import inspect_inline_groups,_inverse_vector,_traces

PATH_PAINT={'S','s','f','F','f*','B','B*','b','b*'}
SHOW={'Tj','TJ',"'",'"'}

def replay(source,page_number,form_path,dx):
    inventory=inspect_inline_groups(source,page_number)
    matches=[g for g in inventory['forms']if g['path']==list(form_path)]
    if len(matches)!=1:raise ValueError('A single original native Form invocation is required')
    original=matches[0]
    with pikepdf.open(source)as document:
        def ancestor(container,resources,path):
            parsed=list(pikepdf.parse_content_stream(container));parts=[];found=False
            private=pikepdf.Dictionary(resources)
            private.XObject=pikepdf.Dictionary(resources.get('/XObject',pikepdf.Dictionary()))
            for index,entry in enumerate(parsed):
                if not hasattr(entry,'operator'):raise ValueError('Inline images in ancestors need explicit review')
                op=str(entry.operator);args=entry.operands
                if op=='Tr'and int(args[0])>=4:raise ValueError('Ancestor text clipping needs explicit review')
                if op=='Do':
                    if index!=path[0]:continue
                    obj=resources.XObject[args[0]]
                    if str(obj.get('/Subtype'))!='/Form':raise ValueError('The selected invocation is not a Form')
                    found=True
                    if len(path)>1:
                        child,child_resources=ancestor(obj,obj.get('/Resources',resources),path[1:])
                        clone=document.make_stream(child)
                        for key,value in obj.items():
                            if str(key)not in('/Length','/Filter','/DecodeParms','/Resources'):clone[key]=value
                        clone.Resources=child_resources
                        private.XObject[args[0]]=clone
                    elif hashlib.sha256(obj.read_raw_bytes()).hexdigest()!=original['original_raw_sha256']:
                        # The inspection helper's isolated page copy may have
                        # renumbered indirect objects. The exact encoded
                        # original stream is the stable identity.
                        raise ValueError('Source Form raw program identity changed')
                elif op in SHOW:
                    # A Form's geometry depends on the graphics CTM, not the
                    # outside text matrix. No ancestor prose is painted.
                    if op in("'",'"'):raise ValueError('Quoted ancestor text shows need explicit review')
                    parts.append(b'[] TJ\n');continue
                elif op in PATH_PAINT:
                    parts.append(b'n\n');continue
                elif op=='sh':continue
                parts.append(pikepdf.unparse_content_stream([entry])+b'\n')
            if not found:raise ValueError('Original Form path was not found')
            return b''.join(parts),private
        page=document.pages[page_number-1]
        program,resources=ancestor(page,page.Resources,list(form_path))
        with fitz.open(source)as native:
            matrix=tuple(native[page_number-1].transformation_matrix)
        tx,ty=_inverse_vector(matrix,float(dx),0)
        page.Resources=resources
        page.Contents=document.make_stream(('q 1 0 0 1 %.12g %.12g cm\n'%(tx,ty)).encode()+program+b'\nQ')
        with pikepdf.Pdf.new()as single:
            single.pages.append(page);buffer=BytesIO();single.save(buffer,compress_streams=False)
        raw=buffer.getvalue()
    with pikepdf.open(BytesIO(raw))as copied:
        preserved=any(isinstance(obj,pikepdf.Stream)and str(obj.get('/Subtype'))=='/Form'
            and hashlib.sha256(obj.read_raw_bytes()).hexdigest()==original['original_raw_sha256']for obj in copied.objects)
        if not preserved:raise ValueError('Saving the native witness changed the original Form raw program')
    with fitz.open(stream=raw,filetype='pdf')as witness:
        actual=_traces(witness[0])
        expected=[g for g in original['glyphs']if g['c'].strip()and g.get('trace_gid',g.get('gid',-1))>=0]
        visible=[g for g in actual if g['c'].strip()and g['trace_gid']>=0]
        if len(expected)!=len(visible):raise ValueError('Native Form witness glyph count changed')
        remaining=list(visible)
        for g in expected:
            hits=[i for i,h in enumerate(remaining)if g['c']==h['c']and g['font']==h['font']
                and abs(g['size']-h['size'])<1e-6
                and g.get('trace_gid',g.get('gid'))==h['trace_gid']
                and all(g.get(k)==h.get(k)for k in('render_mode','color','opacity','linewidth','stroke_color','stroke_opacity'))
                and abs(g['origin'][0]+dx-h['origin'][0])<=.001
                and abs(g['origin'][1]-h['origin'][1])<=.001]
            if not hits:raise ValueError('Native Form witness changed original glyph/style/position')
            remaining.pop(hits[0])
    return raw,dict(source=str(source),source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        source_page=page_number,source_form_path=list(form_path),source_form=original,
        dx=dx,source_native_form_raw_program_retained=True,source_ancestor_ctm_and_clip_preserved=True,
        replay_glyphs=len(visible),font_gid_size_baseline_and_requested_dx_verified=True)

def audit(source,page_number,form_path,dx,target,*,pixels=(),scale=4):
    raw,report=replay(source,page_number,form_path,dx)
    with fitz.open(stream=raw,filetype='pdf')as native,fitz.open(target)as final:
        def rgb(page):
            p=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
            return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)
        a=rgb(native[0]);b=rgb(final[0]);lost=(a.min(2)<32)&(b.min(2)>=220)
        report.update(scale=scale,reference='Exact original complete Form native program, resources and original ancestor clips, with requested dx; other original page painting suppressed.',
            actual_original_native_replay_missing_dark_pixels=int(lost.sum()),passed=not lost.any(),
            diagnostic_pixels=[dict(pixel=list(p),native_rgb=a[p[1],p[0]].tolist(),final_rgb=b[p[1],p[0]].tolist())for p in pixels])
        if lost.any():
            yy,xx=np.nonzero(lost);report['missing_bbox']=[float(xx.min()/scale),float(yy.min()/scale),float((xx.max()+1)/scale),float((yy.max()+1)/scale)]
    return raw,report
