"""Build and independently audit natural-spacing 2021/2022 IZhO pages."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pikepdf
import pymupdf as fitz
from izho_2021_2022_natural_spacing import ROOT,OUT,policy,sha
from izho_2021_2022_header_spacing import apply as pack_header
from pdf_korean_natural_composer import compose_page
from pdf_text_motion_ink import ink_envelope as native_ink_neighborhood
from izho_early_fixed_style import native_font_programs,native_image_programs
from pdf_hangul_visibility import audit as hangul_audit
from izho_new_prose_outline_qa import outline_results
from pdf_native_inline_reposition import reposition_inline,_traces
from pdf_native_geometry_motion import audit as native_geometry_motion
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_original_text_ops import glyph_key

def _pixels(page):
    p=page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
    return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)

def new_outlines(path):
    with pikepdf.open(path)as pdf,fitz.open(path)as doc:
        fonts=pdf.pages[0].Resources.Font
        if '/KO_Natural_Batang'not in fonts:return dict(checked=0,empty=[])
        desc=fonts['/KO_Natural_Batang'].DescendantFonts[0].FontDescriptor
        raw=desc.FontFile2.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        rows=[]
        for t in doc[0].get_texttrace():
            if t['font']!='Batang':continue
            for cp,gid,origin,bbox in t['chars']:
                if 0xac00<=cp<=0xd7a3:rows.append(dict(c=chr(cp),gid=gid,font='Batang',size=t['size'],origin=list(origin)))
        checked=outline_results(dict(raw=raw,sha=digest,kind='/FontFile2',subtype=None),rows,{})
        return dict(checked=len(checked),empty=[g for g in checked if g['outline_empty']],font_program_sha256=digest)

def audit_native_existing(year,kind,number):
    folder=OUT/str(year)/kind;target=folder/f'batang-page{number}.pdf'
    path=target.with_suffix('.qa.json');qa=json.loads(path.read_text('utf8'))
    if sha(target)!=qa['output_sha256']:raise ValueError('The reviewed proof changed')
    composition=qa['composition'];control_path=folder/f'batang-page{number}.native-control.pdf'
    if not control_path.exists():
        opts=dict(allow_white_background_panels=year==2022)
        if(year,kind,number)==(2022,'T',4):
            with fitz.open(qa['source'])as doc:
                if not all(d['type']=='f'and d.get('fill')==(1.,1.,1.)and d.get('color')is None
                           for d in doc[0].get_drawings()if d['rect'].y0>60):raise ValueError('White column profile changed')
            opts['reject_vector_overlap']=False
        raw,native=reposition_inline(qa['source'],1,erased_glyphs=composition['erased_hangul_glyphs'],
            shifts=composition['native_shifts'],**opts)
        control_path.write_bytes(raw)
    with fitz.open(control_path)as control,fitz.open(target)as final:
        origins=[list(c[2])for tr in control[0].get_texttrace()for c in tr['chars']if c[2][1]>60 and c[1]>=0 and chr(c[0]).strip()]
        mask,uses=native_ink_neighborhood(control[0],origins,4)
        cp=_pixels(control[0]);fp=_pixels(final[0]);visible=mask&(cp.min(axis=2)<80)
        result=dict(method='Native movement control actual clip-aware retained body glyph ink versus final rendered proof.',
            native_control_sha256=sha(control_path),resolved_outline_uses=uses,
            protected_actual_native_pixels=int(visible.sum()),missing_actual_native_pixels=int((visible&(fp.min(axis=2)>170)).sum()))
    qa['actual_native_math_visible_ink_audit']=result
    qa['native_ink_audit_authoring_sha256']={name:sha(ROOT/'tools'/name)for name in[
        'izho_2021_2022_batang_rebuild.py','pdf_text_motion_ink.py','pdf_native_inline_reposition.py']}
    qa['passed']=qa['passed']and result['missing_actual_native_pixels']==0
    path.write_text(json.dumps(qa,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(dict(year=year,kind=kind,page=number,actual_native_ink=result),ensure_ascii=False),flush=True)
    if result['missing_actual_native_pixels']:raise ValueError('Actual native/math ink disappeared')

def build(year,kind,number):
    spec=policy(year,kind,number);folder=OUT/str(year)/kind;folder.mkdir(parents=True,exist_ok=True)
    old=ROOT/f'tmp/original-style-repair/{year}/{kind}/page{number}.pdf'
    placements=json.loads(old.with_suffix('.qa.json').read_text('utf8'))['placements']
    regions=[r['rect']for r in spec['regions']]
    centers=[dict(c,rect=r['rect'])for r in spec['regions']for c in r['centered_lines']]
    move_options=dict(allow_white_background_panels=year==2022)
    column_background_profile=None
    if(year,kind,number)==(2022,'T',4):
        with fitz.open(old)as inspected:
            body_paths=[d for d in inspected[0].get_drawings()if d['rect'].y0>60]
            if not all(d['type']=='f'and d.get('fill')==(1.,1.,1.)and d.get('color')is None for d in body_paths):
                raise ValueError('The reviewed white-only column background profile no longer matches the source')
            column_background_profile=dict(profile='Reviewed 2022T4 existing white paragraph-column backgrounds; all paths stay stationary.',
                source_sha256=sha(old),body_paths=[list(d['rect'])for d in body_paths])
        move_options['reject_vector_overlap']=False
    control_path=folder/f'batang-page{number}.native-control.pdf'
    raw,composition=compose_page(old,1,allowed_line_rects=regions,prose_placements=placements,
        excluded_figure_rects=spec['excluded_figure_rects'],centered_lines=centers,
        native_move_options=move_options,native_control_output=control_path,
        baseline_tolerance_pt=.75 if kind=='TS'else.12)
    raw,header=pack_header(raw,spec['original_plan'],placements)
    margin=None
    if(year,kind,number)==(2022,'T',2):
        from izho_2022_t2_native_margin import apply as restore_native_margin
        raw,margin=restore_native_margin(raw)
    target=folder/f'batang-page{number}.pdf';target.write_bytes(raw)
    target.with_suffix('.plan.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),'utf8')
    qa=dict(output=str(target),output_sha256=sha(target),source=str(old),source_sha256=sha(old),
        original_source_sha256=spec['source_sha256'],page=number,year=year,kind=kind,
        composition=composition,header=header,publication_ready=False,visual_review_required=True)
    if column_background_profile:qa['reviewed_stationary_column_backgrounds']=column_background_profile
    if margin:qa['native_white_image_margin_promotion']=margin
    with fitz.open(old)as source,fitz.open(target)as final:
        a=_pixels(source[0]);b=_pixels(final[0]);changed=np.any(a!=b,axis=2)
        old_origins=[g['origin']for g in composition['erased_hangul_glyphs']]
        new_origins=[]
        for s in composition['native_shifts']:
            old_origins.extend(g['origin']for g in s['glyphs'])
            new_origins.extend([g['origin'][0]+s['dx'],g['origin'][1]]for g in s['glyphs'])
        for line in header['lines']:
            for token in line['tokens']:
                if not token.get('dx'):continue
                old_origins.extend(g['origin']for g in token['glyphs'])
                new_origins.extend([g['origin'][0]+token['dx'],g['origin'][1]]for g in token['glyphs'])
        for t in final[0].get_texttrace():
            if t['font']=='Batang':new_origins.extend(list(c[2])for c in t['chars'])
        old_ink,old_uses=native_ink_neighborhood(source[0],old_origins,4)
        new_ink,new_uses=native_ink_neighborhood(final[0],new_origins,4)
        geometry_mask,geometry_qa=native_geometry_motion(old,target,composition['native_shifts'])
        qa['native_graphics_motion_audit']=geometry_qa
        qa['original_and_new_actual_outline_uses_checked']=[old_uses,new_uses]
        qa['changed_pixels_outside_old_and_new_text_ink']=int((changed&~(old_ink|new_ink|geometry_mask)).sum())
        qa['figure_pixel_audits']=[]
        reviewed_overlay=np.zeros(changed.shape,bool)
        if margin:
            for x,y in margin['reviewed_white_margin_changed_pixel_coordinates_4x']:reviewed_overlay[y,x]=True
        for r in spec['excluded_figure_rects']+spec.get('locked_display_equation_rects',[]):
            x0,y0,x1,y1=[int(v*4)for v in r]
            area=changed[y0:y1,x0:x1];allowed=reviewed_overlay[y0:y1,x0:x1]
            qa['figure_pixel_audits'].append(dict(rect=r,changed_pixels=int(area.sum()),
                reviewed_native_over_white_margin_pixels=int((area&allowed).sum()),
                changed_visible_figure_ink_or_unreviewed_pixels=int((area&~allowed).sum())))
        with fitz.open(control_path)as control:
            native_origins=[list(c[2])for tr in control[0].get_texttrace()for c in tr['chars']if c[2][1]>60 and c[1]>=0 and chr(c[0]).strip()]
            native_envelope,uses=native_ink_neighborhood(control[0],native_origins,4)
            control_pixels=_pixels(control[0])
            visible_native=(native_envelope|geometry_mask)&(control_pixels.min(axis=2)<80)
            qa['actual_native_math_visible_ink_audit']=dict(
                method='After native x movement, before new Hangul insertion: actual clip-aware retained-body glyph ink versus final rendered proof; original clips/Form/vector programs also verified by native movement QA.',
                native_control_sha256=sha(control_path),resolved_outline_uses=uses,
                protected_actual_native_pixels=int(visible_native.sum()),
                missing_actual_native_pixels=int((visible_native&(b.min(axis=2)>170)).sum()))
        qa['original_font_programs_and_names_retained']=all(row in native_font_programs(target,1)for row in native_font_programs(old,1))
        qa['original_image_programs_retained']=all(row in native_image_programs(target,1)for row in native_image_programs(old,1))
        with pikepdf.open(old)as src,pikepdf.open(target)as dst:
            qa['page_group_preserved']=str(src.pages[0].get('/Group'))==str(dst.pages[0].get('/Group'))
        final[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(target.with_suffix('.png'))
    qa['new_batang_outlines']=new_outlines(target)
    qa['hangul_visibility']=hangul_audit(target)
    with fitz.open(old)as original:
        shifted_keys={glyph_key(g)for s in composition['native_shifts']for g in s['glyphs']}
        protected=[g for g in _traces(original[0])if glyph_key(g)in shifted_keys and g['trace_gid']>=0]
    qa['original_source_requested_dx_ink_audit']=audit_moved_native_ink(old,1,target,
        shifts=composition['native_shifts'],erased_glyphs=composition['erased_hangul_glyphs'],protected_glyphs=protected,scale=4)
    qa['authoring_sha256']={name:sha(ROOT/'tools'/name)for name in[
        'izho_2021_2022_batang_rebuild.py','izho_2021_2022_natural_spacing.py','izho_2021_2022_header_spacing.py',
        'izho_native_atomic_tokens.py','izho_natural_spacing.py','pdf_korean_natural_composer.py','pdf_native_inline_reposition.py','pdf_text_motion_ink.py','pdf_native_geometry_motion.py','pdf_moved_native_ink.py']}
    qa['passed']=all([composition['native_move_qa']['passed'],header['passed'],
        qa['changed_pixels_outside_old_and_new_text_ink']==0,
        not any(r.get('changed_visible_figure_ink_or_unreviewed_pixels',r['changed_pixels'])for r in qa['figure_pixel_audits']),
        qa['original_font_programs_and_names_retained'],qa['original_image_programs_retained'],qa['page_group_preserved'],
        not qa['new_batang_outlines']['empty'],not qa['hangul_visibility']['flagged_components']])
    qa['passed']=qa['passed']and qa['actual_native_math_visible_ink_audit']['missing_actual_native_pixels']==0 and qa['native_graphics_motion_audit']['changed_nonselected_native_graphical_pixels']==0
    qa['passed']=qa['passed']and qa['original_source_requested_dx_ink_audit']['passed']
    target.with_suffix('.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(dict(output=str(target),sha256=qa['output_sha256'],passed=qa['passed'],
        replaced=composition['replaced_hangul_glyphs'],outside=qa['changed_pixels_outside_old_and_new_text_ink'],
        hangul_loss=qa['hangul_visibility']['flagged_components'],new_outline_empty=len(qa['new_batang_outlines']['empty'])),ensure_ascii=False),flush=True)
    if not qa['passed']:raise ValueError('Independent Batang natural-spacing audit failed')
    return target,qa

if __name__=='__main__':
    from pdf_memory_gate import page_worker
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int,choices=[2021,2022]);p.add_argument('kind',choices=['T','TS']);p.add_argument('page',type=int);p.add_argument('--audit-existing',action='store_true');a=p.parse_args()
    with page_worker():
        if a.audit_existing:audit_native_existing(a.year,a.kind,a.page)
        else:build(a.year,a.kind,a.page)
