"""Independent page QA for the CPhO natural-spacing repair batch.

The immutable strict translation is the input. Native physical glyphs are
identified separately against the Chinese source, so translated headings do
not masquerade as original mathematics in the independent visibility audit.
"""
from pathlib import Path
from collections import Counter
import argparse,json,os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1')
import numpy as np
import pikepdf
import pymupdf as fitz
from cpho_natural_spacing import baseline,OUT,sha
from cpho_natural_spacing_qa import original_native_glyphs
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_native_inline_reposition import _traces
from pdf_native_geometry_motion import audit as geometry_audit
from pdf_text_motion_ink import ink_envelope
from pdf_hangul_visibility import audit as hangul_audit
from izho_natural_spacing_qa import fresh_render,semantic,image_rect_motion
from izho_early_fixed_style import native_image_programs
import hashlib


def native_font_programs(path,page_number):
    """Keep original raw PDF names; older Chinese names are not UTF-8."""
    rows=[]
    with pikepdf.open(path)as pdf:
        def walk(resources,prefix,ancestors=()):
            for name,font in resources.get('/Font',{}).items():
                face=font.get('/DescendantFonts',[font])[0];descriptor=face.get('/FontDescriptor',{})
                programs=tuple((key,hashlib.sha256(descriptor[key].read_bytes()).hexdigest())for key in ['/FontFile','/FontFile2','/FontFile3']if key in descriptor)
                unicode_sha=hashlib.sha256(font.ToUnicode.read_bytes()).hexdigest()if'/ToUnicode'in font else None
                base=font.get('/BaseFont');base=bytes(base).hex()if base is not None else None
                rows.append((prefix,str(name),base,str(font.get('/Subtype')),str(font.get('/Encoding')),unicode_sha,programs))
            for name,child in resources.get('/XObject',{}).items():
                if str(child.get('/Subtype'))=='/Form'and'/Resources'in child:
                    if child.objgen in ancestors:raise ValueError('Recursive font graph')
                    walk(child.Resources,prefix+'/'+str(name),ancestors+(child.objgen,))
        walk(pdf.pages[page_number-1].Resources,'Page')
    return rows


def audit(year,language,number):
    folder=OUT/str(year)/language;target=folder/f'page{number:02}.pdf'
    composition=json.loads(target.with_suffix('.qa.json').read_text('utf8'))
    if composition['output_sha256']!=sha(target):raise ValueError('Page changed after composition')
    source=baseline(year,language);old=folder/f'page{number:02}-immutable-input.pdf'
    with pikepdf.open(source)as original,pikepdf.Pdf.new()as single:
        single.pages.append(original.pages[number-1]);single.save(old,compress_streams=False)
    renders=folder/'qa-renders';renders.mkdir(exist_ok=True)
    a=fresh_render(old,1,renders/f'{number:02}-old.png')
    b=fresh_render(target,1,renders/f'{number:02}-new.png')
    changed=np.any(a!=b,axis=2)
    motion,geometry=geometry_audit(old,target,composition['native_shifts'])
    with fitz.open(old)as src,fitz.open(target)as dst:
        before=_traces(src[0]);after=_traces(dst[0])
        old_ink,old_uses=ink_envelope(src[0],[g['origin']for g in before if g['c'].strip()],4)
        new_ink,new_uses=ink_envelope(dst[0],[g['origin']for g in after if g['c'].strip()],4)
        outside=int((changed&~(old_ink|new_ink|motion)).sum())
        # Old language-only masks are already present in this immutable input;
        # the original bitmap bytes and their exact paint positions stay locked.
        original_images=src[0].get_image_info(xrefs=True);current_images=dst[0].get_image_info(xrefs=True)
        native=[g for g in original_native_glyphs(year,language,number)if g['c'].strip()and g['trace_gid']>=0]
        regular_left=[dict(c=g['c'],font=g['font'],origin=g['origin'])for g in after
            if language=='ko'and 0xac00<=ord(g['c'])<=0xd7a3 and 'NotoSerif'in g['font']and'Regular'in g['font']]
        nul=sum(g['c']=='\x00'for g in after)
    physical=audit_moved_native_ink(source,number,target,shifts=composition['native_shifts'],
        erased_glyphs=composition['erased_hangul_glyphs'],protected_glyphs=native)
    font_same=all(v in native_font_programs(target,1)for v in native_font_programs(old,1))
    image_same=all(v in native_image_programs(target,1)for v in native_image_programs(old,1))
    images=[]
    with pikepdf.open(old)as src,pikepdf.open(target)as dst:
        group_same=semantic(src.pages[0].get('/Group'))==semantic(dst.pages[0].get('/Group'))
        colors_same=semantic(src.pages[0].Resources.get('/ColorSpace'))==semantic(dst.pages[0].Resources.get('/ColorSpace'))
        if len(original_images)!=len(current_images):raise ValueError('Image paint count changed')
        for i,(x,y)in enumerate(zip(original_images,current_images)):
            images.append(dict(image=i,**image_rect_motion(x['bbox'],y['bbox'],geometry),
                full_palette_icc_mask_image_graph_preserved=semantic(src.get_object((x['xref'],0)))==semantic(dst.get_object((y['xref'],0)))))
    hangul=hangul_audit(target)if language=='ko'else dict(flagged_components=0,pages=[])
    stages=[composition['native_move_qa']]
    if composition.get('picture_language_and_caption_stage'):stages.append(composition['picture_language_and_caption_stage']['native_move_qa'])
    report=dict(year=year,language=language,page=number,output=str(target),output_sha256=sha(target),
        immutable_input=str(source),immutable_input_sha256=sha(source),
        changed_pixels_outside_old_and_new_text_ink=outside,old_text_outline_uses=old_uses,new_text_outline_uses=new_uses,
        original_physical_native_ink=physical,native_graphics_motion_audit=geometry,
        original_font_programs_and_names_retained=font_same,original_image_programs_retained=image_same,
        image_palette_icc_mask_and_motion_audits=images,page_group_preserved=group_same,colorspace_resources_preserved=colors_same,
        native_move_stages_passed=all(s['passed']for s in stages),hangul_visibility=hangul,
        remaining_regular_NotoSerif_Hangul=regular_left,NUL_glyphs=nul,
        fresh_process_RGB_render=True,visual_review_required=True)
    report['passed']=all([not outside,not geometry['changed_nonselected_native_graphical_pixels'],physical['passed'],
        font_same,image_same,group_same,colors_same,report['native_move_stages_passed'],not hangul['flagged_components'],not regular_left,not nul,
        all((v['rect_preserved']or v['rect_matches_declared_native_math_dx'])and v['full_palette_icc_mask_image_graph_preserved']for v in images)])
    target.with_suffix('.audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(dict(year=year,language=language,page=number,passed=report['passed'],outside=outside,
        native_missing=physical.get('newly_missing_native_ink_pixels'),graphics_changed=geometry['changed_nonselected_native_graphical_pixels'],
        Hangul_missing=hangul['flagged_components'],old_regular_left=len(regular_left)),ensure_ascii=False),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int);p.add_argument('language',choices=['ko','en']);p.add_argument('page',type=int);a=p.parse_args()
    from pdf_memory_gate import page_worker
    with page_worker():raise SystemExit(not audit(a.year,a.language,a.page)['passed'])
