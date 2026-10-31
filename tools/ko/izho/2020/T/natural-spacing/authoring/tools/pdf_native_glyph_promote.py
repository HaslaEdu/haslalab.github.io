"""Explicitly promote original native glyph paint above a later white panel.

The input must already have its final x coordinates. This copies the original
encoded CID, font resource, Tf, text-matrix linear part, CTM and active native
paint state into a tiny Form. The earlier CID paint becomes its exact TJ
advance. No Unicode text insertion, font regeneration or raster is used.
Caller must independently prove the overlapped source graphic is blank.
"""
from io import BytesIO
from pathlib import Path
import hashlib
import pikepdf
import pymupdf as fitz
from pdf_native_inline_reposition import (
    inspect_inline_groups,reposition_inline,_traces,_raw_regions,_multiply,
    _inverse_vector,_number,_font_programs,_verify_glyphs,
)
from pdf_original_text_ops import glyph_key,family_name

PAINT_STATE={'g','G','rg','RG','k','K','cs','CS','sc','SC','scn','SCN',
             'gs','w','J','j','M','d','ri','i'}


def _inverse(m):
    a,b,c,d,e,f=m;det=a*d-b*c
    if abs(det)<1e-14:raise ValueError('Singular native CTM')
    return(d/det,-b/det,-c/det,a/det,(c*f-d*e)/det,(b*e-a*f)/det)


def _point_inverse(matrix,x,y):
    return _inverse_vector(matrix,x-matrix[4],y-matrix[5])


def promote_native_glyphs(source,page_number,glyphs):
    """Return (one-page bytes, QA) for reviewed top-level native CID promotion.

    Every exact coincident paint of a selected key moves to the final paint
    layer. Glyph positions and original fonts/styles remain unchanged. Tight
    clips, unknown clip shapes, nested-Form glyph selection and nonopaque or
    stroked glyphs deliberately fail closed in this first reviewed profile.
    """
    raw=bytes(source) if isinstance(source,(bytes,bytearray)) else Path(source).read_bytes()
    doc=fitz.open(stream=raw,filetype='pdf');page=doc[page_number-1]
    keys={glyph_key(dict(g,font=family_name(g['font']))) for g in glyphs}
    if not keys:raise ValueError('No native glyphs selected for paint promotion')
    inventory=inspect_inline_groups(raw,page_number,include_text_shows=True)
    recipes=[];found=set()
    for show in inventory['top_level_text_shows']:
        for part in show['parts']:
            partkeys={glyph_key(g) for g in part['glyphs']}
            if not keys&partkeys:continue
            if not partkeys<=keys:raise ValueError('Promotion must select the complete encoded native CID cluster')
            if show['operator'] not in ['Tj','TJ']:raise ValueError('Quoted native show promotion needs a separate profile')
            painted=[g for g in part['glyphs'] if g['trace_gid']>=0]
            if len(painted)!=1:raise ValueError('Promotion requires one physical glyph per original CID')
            g=painted[0]
            if g['render_mode']!=0 or abs(g['opacity']-1)>1e-8:
                raise ValueError('This reviewed promotion profile requires opaque native fill')
            box=fitz.Rect(g['bbox'])+(-2,-2,2,2)
            for clip in show['state']['clips']:
                if clip['rect'] is None or not fitz.Rect(clip['rect']).contains(box):
                    raise ValueError('Promotion would discard a potentially active tight/unknown native clip')
            recipes.append(dict(show=show,part=part,glyph=g,box=box));found.update(partkeys)
    if found!=keys:raise ValueError('Promotion selection is not exact top-level native CID paint')
    erased,erase_qa=reposition_inline(raw,page_number,erased_glyphs=glyphs)
    with pikepdf.Pdf.open(BytesIO(raw)) as source_pdf,pikepdf.Pdf.open(BytesIO(erased)) as pdf:
        src=source_pdf.pages[page_number-1];target=pdf.pages[0]
        content,regions=_raw_regions(src);instructions=pikepdf.parse_content_stream(src)
        old_resources=target.Resources;new_resources=pikepdf.Dictionary(old_resources)
        new_resources.XObject=pikepdf.Dictionary(old_resources.get('/XObject',{}))
        new_resources.ExtGState=pikepdf.Dictionary(old_resources.get('/ExtGState',{}))
        alias_index=0
        def alias(prefix,table):
            nonlocal alias_index
            while True:
                name=pikepdf.Name('/'+prefix+str(alias_index));alias_index+=1
                if name not in table:return name
        reset=alias('NativePaintReset',new_resources.ExtGState)
        new_resources.ExtGState[reset]=pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name.ExtGState,ca=1,CA=1,BM=pikepdf.Name.Normal,SMask=pikepdf.Name('/None'),OP=False,op=False,OPM=0,AIS=False))
        inverse_end=_inverse(inventory['final_ctm'])
        append=[('q '+' '.join(_number(v) for v in inverse_end)+' cm '+str(reset)+' gs '
                 '0 g 0 G 1 w 0 J 0 j 10 M [] 0 d\n').encode('ascii')]
        report=[];page_matrix=tuple(page.transformation_matrix)
        for recipe in recipes:
            show=recipe['show'];st=show['state'];glyph=recipe['glyph'];part=recipe['part']
            history=[];stack=[]
            for index,instruction in enumerate(instructions[:show['operator_index']]):
                op=str(instruction.operator)
                if op=='q':stack.append(list(history))
                elif op=='Q':
                    if not stack:raise ValueError('Unbalanced native paint history')
                    history=stack.pop()
                elif op in PAINT_STATE:
                    if op=='gs':
                        state=src.Resources.get('/ExtGState',{}).get(instruction.operands[0],{})
                        if '/Font' in state or str(state.get('/SMask','/None'))!='/None':
                            raise ValueError('Native promotion does not accept font/soft-mask ExtGState')
                    a,z,_=regions[index];history.append(content[a:z])
            combined=_multiply(st['ctm'],page_matrix)
            x,y=_point_inverse(combined,*glyph['origin']);tm=list(show['text_matrix'])
            tm[4]=x-tm[2]*st['ts'];tm[5]=y-tm[3]*st['ts']
            body=[('q '+' '.join(_number(v) for v in st['ctm'])+' cm\n').encode('ascii'),*history]
            body.append(('\nBT '+st['active']+' '+_number(st['tf'])+' Tf '+_number(st['tc'])+' Tc '
                         +_number(st['tw'])+' Tw '+_number(st['th']*100)+' Tz '+str(st['tr'])+' Tr '
                         +_number(st['ts'])+' Ts '+' '.join(_number(v) for v in tm)+' Tm '
                         +'<'+part['raw_hex']+'> Tj ET Q').encode('ascii'))
            form=pdf.make_stream(b'\n'.join(body));form.Type=pikepdf.Name.XObject;form.Subtype=pikepdf.Name.Form
            points=[_point_inverse(page_matrix,x,y) for x,y in[(recipe['box'].x0,recipe['box'].y0),(recipe['box'].x1,recipe['box'].y1)]]
            form.BBox=pikepdf.Array([min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)])
            form.Resources=old_resources;name=alias('NativePaint',new_resources.XObject)
            new_resources.XObject[name]=form;append.append((str(name)+' Do\n').encode('ascii'))
            report.append(dict(c=glyph['c'],font=glyph['font'],gid=glyph['trace_gid'],size=glyph['size'],
                               origin=list(glyph['origin']),source_encoded_cid_hex=part['raw_hex'],
                               source_font_resource=st['active'],source_Tf=st['tf'],
                               source_Tm_linear=show['text_matrix'][:4],form_sha256=hashlib.sha256(form.read_bytes()).hexdigest()))
        append.append(b'Q');target.Resources=new_resources
        streams=list(target.Contents) if isinstance(target.Contents,pikepdf.Array) else[target.Contents]
        target.Contents=pikepdf.Array(streams+[pdf.make_stream(b''.join(append))])
        before_programs=_font_programs(src)
        buffer=BytesIO();pdf.save(buffer,compress_streams=False);result=buffer.getvalue()
        with pikepdf.Pdf.open(BytesIO(result)) as final:programs_unchanged=before_programs==_font_programs(final.pages[0])
    qa=_verify_glyphs(page,result,set(),{},tolerance=.001)
    qa.update(api='native-glyph-paint-promotion-v1',promoted_native_paints=report,
              no_new_unicode_or_font_program=True,original_font_programs_unchanged=programs_unchanged,
              native_encoded_CIDs_preserved=True,positions_unchanged=True,
              source_sha256=hashlib.sha256(raw).hexdigest(),output_sha256=hashlib.sha256(result).hexdigest(),
              white_graphic_margin_witness_required=True)
    qa['passed']=not qa['native_glyph_mismatches'] and not qa['unexpected_glyphs'] and programs_unchanged
    doc.close()
    if not qa['passed']:raise ValueError('Native paint promotion invariant failed: '+repr(qa))
    return result,qa
