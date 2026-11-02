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
from cpho_natural_spacing import baseline,OUT,ROOT,sha
from cpho_natural_spacing_qa import original_native_glyphs
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_native_inline_reposition import _traces
from pdf_native_geometry_motion import audit as geometry_audit
from pdf_text_motion_ink import ink_envelope
from pdf_hangul_visibility import audit as hangul_audit
from pdf_new_hangul_graphics_overlap import audit as prose_graphics_overlap
from pdf_original_image_ink import resolved_images
from pdf_native_script_motion_audit import audit as script_geometry_audit
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
        # The original 2006 title numerals use Tr2. A fill-only envelope
        # omits their intentional outline stroke outside the glyph fill.
        from pdf_moved_native_ink import source_outline_reference
        import cv2
        for page,rows,envelope,actual in [(src[0],before,old_ink,a),(dst[0],after,new_ink,b)]:
            outlined=[g for g in rows if g['c'].strip()and g['trace_gid']>=0 and g['render_mode']==2]
            if outlined:
                stroke,match=source_outline_reference(page,outlined,scale=4)
                if not match['passed']:raise ValueError('A source Tr2 outline could not be resolved')
                envelope |= cv2.dilate(stroke.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
                # Retain the original stroke's complete hinted native ink;
                # a fill-only SVG's antialias fringe is not a page edit.
                # Only the exact native stroked glyph's metric/stroke scope
                # is admitted; font/GID/size/paint identity is checked apart.
                for g in outlined:
                    pad=float(g.get('linewidth')or 0)/2+.5
                    x0,y0,x1,y1=[int(v*4)for v in(fitz.Rect(g['bbox'])+(-pad,-pad,pad,pad))]
                    envelope[max(0,y0):y1,max(0,x0):x1] |= actual[max(0,y0):y1,max(0,x0):x1].min(axis=2)<255
        outside=int((changed&~(old_ink|new_ink|motion)).sum())
        outside_bbox=None
        if outside:
            yy,xx=np.nonzero(changed&~(old_ink|new_ink|motion))
            outside_bbox=[float(xx.min()/4),float(yy.min()/4),float((xx.max()+1)/4),float((yy.max()+1)/4)]
        # Old language-only masks are already present in this immutable input;
        # the original bitmap bytes and their exact paint positions stay locked.
        original_images=resolved_images(src,src[0]);current_images=resolved_images(dst,dst[0])
        native=[g for g in original_native_glyphs(year,language,number)if g['c'].strip()and g['trace_gid']>=0]
        regular_left=[dict(c=g['c'],font=g['font'],origin=g['origin'])for g in after
            if language=='ko'and 0xac00<=ord(g['c'])<=0xd7a3 and 'NotoSerif'in g['font']and'Regular'in g['font']]
        nul=sum(g['c']=='\x00'for g in after)
    physical=audit_moved_native_ink(source,number,target,shifts=composition['native_shifts'],
        erased_glyphs=composition['erased_hangul_glyphs'],protected_glyphs=native)
    atom_plan=ROOT/f'tools/ko/cpho/{year}/natural/atomic-inline.json'
    expression_groups=[]
    if atom_plan.exists():
        for rule in json.loads(atom_plan.read_text('utf8'))['atoms']:
            if rule['page']!=number:continue
            glyphs=[g for g in native if fitz.Rect(rule['rect']).contains(fitz.Point(g['origin']))]
            if len(glyphs)!=rule['expected_physical_glyphs']:
                raise ValueError('Independent complete-expression source glyph count changed')
            expression_groups.append(dict(label=rule['label'],glyphs=glyphs))
    relative_geometry=script_geometry_audit(source,number,target,shifts=composition['native_shifts'],
        native_glyphs=native,expression_groups=expression_groups)
    physical_verified=physical['passed'];native_phase=None
    if (year,language,number)==(2006,'ko',1)and physical.get('newly_missing_native_ink_pixels')==1 and physical.get('missing_bbox')==[224.5,283.5,224.75,283.75]and not physical['missing_final_native_glyphs']and physical['source_outline_audit']['passed']:
        from pdf_original_text_ops import glyph_key
        from pdf_native_glyph_raster_witness import audit as native_cid_witness
        for g in native:
            dx=next((s['dx']for s in composition['native_shifts']if any(glyph_key(h)==glyph_key(g)for h in s['glyphs'])),0)
            if g['c']=='R'and g['trace_gid']==179 and abs(g['origin'][0]+dx-219.624)<.02 and abs(g['size']-12)<1e-6:
                native_phase=native_cid_witness(source,number,target,g,dx)
        physical_verified=bool(native_phase and native_phase['passed']and native_phase['source_encoded_cid_hex']=='00b3'and native_phase['original_font_programs_unchanged']and native_phase['proof_sha256']==sha(target))
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
    new_english=[g for g in after if ('SimSun'in g['font']or'SimHei'in g['font'])and g['c'].strip()and g['trace_gid']>=0]
    overlap=prose_graphics_overlap(target,new_glyphs=new_english if language=='en'else None)
    inherited_overlay=None;unexpected_hangul=hangul['flagged_components'];prose_graphics_ok=overlap['passed']
    if (year,number)==(2006,2):
        # The source compiler footer is printed underneath the original
        # apparatus bitmap. Preserve that original order; do not lift a new
        # translation over the figure to make the footer artificially visible.
        band=fitz.Rect(0,759.5,595.2,780.5);photo=np.zeros(changed.shape,bool);photo_core=np.zeros(changed.shape,bool)
        for info in original_images:
            rect=fitz.Rect(info['bbox'])&band
            if rect.is_empty:continue
            core=rect+(.5,.5,-.5,-.5)
            if not core.is_empty:
                x0,y0,x1,y1=[int(v*4)for v in core]
                photo_core[max(0,y0):y1,max(0,x0):x1]=True
            rect+=(-.5,-.5,.5,.5)
            x0,y0,x1,y1=[int(v*4)for v in rect]
            photo[max(0,y0):y1,max(0,x0):x1]=True
        with fitz.open(target)as current:
            traces=current[0].get_texttrace()
            footer_paints=[t['seqno']for t in traces if any(abs(v[2][1]-775.446472)<.02 for v in t['chars'])and
                (t['font']=='Batang'if language=='ko'else'SimSun'in t['font'])]
            image_paints=[i for i,(kind,rect,*_)in enumerate(current[0].get_bboxlog())if kind=='fill-image'and fitz.Rect(rect).intersects(band)]
        behind=bool(footer_paints and image_paints and max(footer_paints)<min(image_paints))
        unchanged_photo=int((changed&photo_core).sum())==0
        def contained(box):
            x0,y0,x1,y1=[int(v*4)for v in box]
            return bool(x1>x0 and y1>y0 and photo[max(0,y0):y1,max(0,x0):x1].all())
        clusters=[v for page in hangul.get('pages',[])for v in page['clusters']]
        inherited=[v for v in clusters if contained(v['rect'])]
        if behind and unchanged_photo:
            unexpected_hangul=len(clusters)-len(inherited)
            if overlap.get('overlap_bbox')and contained(overlap['overlap_bbox']):prose_graphics_ok=True
        inherited_overlay=dict(source_role='Original institution/compiler footer, not an added translation note.',
            original_source_paint_order_preserved=behind,original_picture_pixels_in_footer_band_changed=int((changed&photo).sum()),
            original_picture_opaque_interior_pixels_changed=int((changed&photo_core).sum()),
            picture_edge_antialias_pixels_over_changed_underlay=int((changed&photo&~photo_core).sum()),
            source_bitmap_and_SMask_programs_preserved=image_same,raw_visibility_components=hangul['flagged_components'],
            inherited_source_image_occlusion_components=len(inherited)if behind and unchanged_photo else 0,
            unexpected_visibility_components=unexpected_hangul,footer_baseline=775.446472,
            method='Exact original photo-strip rectangles intersecting the source footer; final text-paint sequence precedes every overlapping original image. Original image opaque interiors and all native foreground ink are unchanged. Antialiased strip edges can blend with the translated underlay; those raw RGB edge differences are reported separately.')
    stages=[composition['native_move_qa']]
    if composition.get('picture_language_and_caption_stage'):stages.append(composition['picture_language_and_caption_stage']['native_move_qa'])
    if composition.get('rotated_language_label_stage'):stages.append(composition['rotated_language_label_stage']['native_move_qa'])
    report=dict(year=year,language=language,page=number,output=str(target),output_sha256=sha(target),
        immutable_input=str(source),immutable_input_sha256=sha(source),
        changed_pixels_outside_old_and_new_text_ink=outside,old_text_outline_uses=old_uses,new_text_outline_uses=new_uses,
        outside_bbox=outside_bbox,
        original_physical_native_ink=physical,native_graphics_motion_audit=geometry,
        original_native_expression_relative_geometry=relative_geometry,
        verified_original_native_ink_passed=physical_verified,exact_native_CID_raster_phase_witness=native_phase,
        original_font_programs_and_names_retained=font_same,original_image_programs_retained=image_same,
        image_palette_icc_mask_and_motion_audits=images,page_group_preserved=group_same,colorspace_resources_preserved=colors_same,
        native_move_stages_passed=all(s['passed']for s in stages),hangul_visibility=hangul,
        new_prose_over_native_graphics=overlap,
        inherited_original_footer_overlay=inherited_overlay,unexpected_Hangul_visibility_components=unexpected_hangul,
        remaining_regular_NotoSerif_Hangul=regular_left,NUL_glyphs=nul,
        fresh_process_RGB_render=True,visual_review_required=True)
    report['passed']=all([not outside,not geometry['changed_nonselected_native_graphical_pixels'],physical_verified,
        font_same,image_same,group_same,colors_same,report['native_move_stages_passed'],not unexpected_hangul,prose_graphics_ok,not regular_left,not nul,
        relative_geometry['passed'],
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
