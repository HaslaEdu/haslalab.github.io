"""Source-slot-bound physical shear, approved titles/row and new /W hooks."""
from pathlib import Path
import copy,hashlib,json,math,re
import pymupdf as fitz
from r4_guard import ROOT,rules,sha,validate_plan,validate_write
from r4_font_widths import capture_original_font_lineage,apply_in_memory,finalize_exact_serialization

def source_style_angle(base,plan,slot,style_first,first,role,text,angle):
    if not text or not angle:return angle
    cfg=rules(base)
    assert plan['source_sha256']==cfg['source_sha256']
    entries=[v for v in cfg['source_style_entries'] if v['source_slot_id']==slot['id']]
    if not entries:raise ValueError('Unlisted new prose style cannot change or retain a nonzero physical shear')
    expected=entries[0]
    normalized=dict(slot,text=text)
    assert normalized==expected['original_source_slot'],'Original source slot/target words changed'
    assert role==expected['font_role'] and angle==expected['actual_source_font_descriptor']['italic_angle']<0
    assert angle==expected['old_descriptor_angle']
    for actual,wanted in ((style_first,expected['original_selected_source_characters'][0] if not expected['source_style_reference'] else None),):
        if wanted is not None and not wanted['c'].strip():
            wanted=next(v for v in expected['original_selected_source_characters'] if v['c'].strip())
        if wanted is not None:
            for key in ('c','font','size','origin','bbox','color'):
                left,right=actual[key],wanted[key]
                if isinstance(left,(list,tuple)) and isinstance(right,(list,tuple)):left,right=tuple(left),tuple(right)
                assert left==right,('Source style anchor differs',slot['id'],key,left,right)
    assert style_first['font']==expected['actual_source_style_font']
    assert first['size']==expected['source_anchor']['size']
    assert sha(expected['master']['path'])==expected['master']['sha256']
    assert expected['master']['actual_master_post_italic_angle']==0 and not expected['master']['actual_master_os2_italic']
    return expected['desired_pdf_glyph_space_shear_angle']

def _style_entry(cfg,placement):
    entries=[v for v in cfg['source_style_entries'] if v['source_slot_id']==placement['id'] and
             abs(v['baseline_pt']-placement['baseline'])<.001 and v['target_text']==placement['text']]
    if entries:
        assert len(entries)==1
        return entries[0]
    return None

def contact_row_rule(year,page):
    if year!=2026 or page!=1:return None
    path=ROOT/'APPROVED-2026-P1-EXISTING-AA-CONTACT-ROW.json';value=json.loads(path.read_text('utf8'))
    assert value['status']=='ROOT_GO_ONE_NEW_KO_ROW_EXISTING_LOW_RESOLUTION_AA_CONTACT_CORRECTION'
    assert value['year']==year and value['page']==page
    assert value['baseline']==683.5799560546875 and value['dx']==-.5625
    assert abs(value['dx'])<=value['max_abs_dx_pt']==1.5 and abs(value['dx'])/value['source_size_pt']<=value['optical_em_limit']==.4
    assert value['source_sha256']==rules(ROOT/'2026')['source_sha256']
    for key in ('precontact_proof','precontact_layout','diagnosis','source_comparison'):
        assert sha(value[key]['path'])==value[key]['sha256']
    return value

def post_layout(layout,base,font_metric,text_width,glyph_key,source_glyphs):
    cfg=rules(base);assert layout['source_sha256']==cfg['source_sha256']
    if cfg['year']==2026:
        addendum=ROOT/'EXPERIMENT-BATANG-PAINT-ADDENDUM-GO.json';go=json.loads(addendum.read_text('utf8'))
        assert go['status']=='ROOT_GO_EXACT_W_PLUS_NEW_BATANG_FULL_MASTER_GLYPH_ORIGIN_TM_RESET'
        assert go['input_ledger_sha256']==sha(ROOT/'input-ledger.json') and go['allowed_year']==2026
        assert go['reviewed_candidate_patch_sha256']==sha(ROOT/'candidates/2026-Batang-glyph-origin-reset.patch')
        assert go['renderer_integer_width_diagnosis_sha256']==sha(ROOT/'experiments/attempt-proto06/2026/page01.renderer-W-diagnosis-v2.json')
        assert go['original_native_operations_may_change'] is go['font_program_binary_may_change'] is False
        assert go['glyph_identity_or_point_size_or_baseline_may_change'] is go['authored_words_or_word_space_may_change'] is False
        layout['r4_new_Batang_origin_precision_paint']=dict(method='Precise glyph-by-glyph Tm origin reset to the original full-master metrics; exact W retained',
            master=cfg['new_Batang_W_precision'],authorization_path=str(addendum),authorization_sha256=sha(addendum),
            glyph_program_GID_size_baseline_words_and_ordinary_spaces_unchanged=True,
            old_Tm_TJ_paint_grouping_retained=False,only_new_Batang_actual_advance_geometry_corrected=True)
    titles=[]
    if layout['page']==1 and cfg['year']!=2023:
        selected={glyph_key(g) for g in layout['selected_glyphs']}
        with fitz.open(layout['source']) as source:
            page=source[0];original=source_glyphs(page)
            for spec in cfg['title_rows']:
                y=spec['baseline'];glyphs=sorted([g for g in original if g['c'].strip() and abs(g['origin'][1]-y)<.001],key=lambda g:g['origin'][0])
                assert len(glyphs)==spec['glyphs'] and ''.join(g['c'] for g in glyphs)==spec['source_text_no_spaces']
                assert all(g['font']==spec['source_font'] and abs(g['size']-spec['source_size_pt'])<=1e-6 and glyph_key(g) in selected for g in glyphs)
                bbox=[min(g['bbox'][0] for g in glyphs),min(g['bbox'][1] for g in glyphs),max(g['bbox'][2] for g in glyphs),max(g['bbox'][3] for g in glyphs)]
                assert max(abs(a-b) for a,b in zip(bbox,spec['source_bbox']))<=1e-6
                center=(bbox[0]+bbox[2])/2;assert abs(center-spec['source_center_pt'])<=1e-6
                placements=[p for p in layout['placements'] if abs(p['baseline']-y)<.0002]
                lines=[v for v in layout['line_reports'] if abs(v['baseline']-y)<.0002]
                assert placements and len(lines)==1 and all(t['kind']=='prose' for t in lines[0]['tokens'])
                assert not any(abs(g['origin'][1]-y)<.001 for shift in layout['native_shifts'] for g in shift['glyphs'])
                boxes=[]
                for p in placements:
                    assert p['angle']==0 and abs(p['size']-spec['source_size_pt'])<=1e-6 and abs(p['point'][1]-y)<=1e-6
                    metric=font_metric(Path(layout['new_font_paths'][p['font_role']]))
                    width=text_width(metric,p['text'],p['size']);assert abs(width-p['advance'])<=1e-5
                    boxes.append((p['point'][0],p['point'][0]+width))
                before=(min(v[0] for v in boxes)+max(v[1] for v in boxes))/2;dx=center-before
                assert min(v[0] for v in boxes)+dx>=0 and max(v[1] for v in boxes)+dx<=page.rect.width
                for p in placements:
                    p['point'][0]+=dx
                    if 'draw_point' in p:p['draw_point'][0]+=dx
                lines[0]['left']+=dx;lines[0]['right']+=dx
                for token in lines[0]['tokens']:token['new_x']+=dx
                titles.append(dict(spec,dx=dx,whole_row_horizontal_origin_translation_only=True))
    styles=[]
    for p in layout['placements']:
        entry=_style_entry(cfg,p)
        if entry:
            assert p['font_role']==entry['font_role'] and p['source_font']==entry['actual_source_style_font']
            assert p['angle']==entry['desired_pdf_glyph_space_shear_angle'] and p['size']==entry['point_size_pt']
            assert p['point']==entry['logical_point'],'Source-style correction changed a logical origin'
            styles.append(dict(source_slot_id=p['id'],target_text=p['text'],baseline=p['baseline'],
                original_descriptor_angle=entry['old_descriptor_angle'],physical_target_angle=p['angle'],
                physical_pdf_shear_c=math.tan(math.radians(p['angle'])),master_sha256=entry['master']['sha256'],
                original_point_size_and_logical_origin_unchanged=True))
        elif p['angle']:
            raise ValueError('A painted nonzero new prose shear is outside the source-style whitelist')
    body=None
    spec=cfg.get('approved_row')
    if spec and layout['page']==spec['page']:
        actual=[p for p in layout['placements'] if abs(p['baseline']-spec['baseline'])<.0002]
        assert len(actual)==len(spec['precontact_P0_placements'])
        for old,new in zip(spec['precontact_P0_placements'],actual):
            expected=copy.deepcopy(old)
            for field in ('point','draw_point'):
                if field in expected:expected[field][0]+=spec['dx']
            style=_style_entry(cfg,new)
            if style:expected['angle']=style['desired_pdf_glyph_space_shear_angle']
            assert expected==new,'Combined approved row changed beyond its origin/style whitelist'
        body=dict(page=spec['page'],baseline=spec['baseline'],dx_from_published_P0=spec['dx'],
            whole_row_horizontal_origin_shift_only=True,whole_row_bbox_translation_only=False,
            contains_source_style_bound_shear_change=True,italic_bbox_requires_actual_outline_and_matrix=True)
    layout['r4_source_style_corrections']=styles
    layout['r4_source_title_centers']=titles
    layout['r4_approved_combined_row']=body
    contact=contact_row_rule(cfg['year'],layout['page'])
    if contact:
        row=[p for p in layout['placements'] if abs(p['baseline']-contact['baseline'])<.001]
        assert len(row)==1 and row[0]==contact['precontact_logical_placement']
        assert not any(abs(g['origin'][1]-contact['baseline'])<.001 for shift in layout['native_shifts'] for g in shift['glyphs'])
        p=row[0];p['point'][0]+=contact['dx']
        if 'draw_point' in p:p['draw_point'][0]+=contact['dx']
        lines=[line for line in layout['line_reports'] if abs(line['baseline']-contact['baseline'])<.001]
        assert len(lines)==1 and all(t['kind']=='prose' for t in lines[0]['tokens'])
        lines[0]['left']+=contact['dx'];lines[0]['right']+=contact['dx']
        for token in lines[0]['tokens']:token['new_x']+=contact['dx']
        layout['r4_existing_AA_contact_KO_row_correction']=dict(baseline=contact['baseline'],dx=contact['dx'],
            source_slot_id=p['id'],source_size_pt=p['size'],whitelist_glyphs=len(contact['actual_nonspace_glyph_whitelist']),
            reason=contact['reason'],native_source_atoms_on_this_row=0,logical_KO_row_horizontal_translation_only=True,
            actual_bbox_also_includes_separately_verified_W_precision=True,
            authorization_path=str(ROOT/'APPROVED-2026-P1-EXISTING-AA-CONTACT-ROW.json'),
            authorization_sha256=sha(ROOT/'APPROVED-2026-P1-EXISTING-AA-CONTACT-ROW.json'))
    layout['font_policy']='Original approved full-font files/GIDs/physical sizes/baselines retained; source-slot-bound new Korean physical shear sign corrected. Only2026 newly inserted Batang CID W precision and its actual glyph-origin serialization are corrected; native source fonts/math/images remain unchanged.'
    layout['r4_actual_exception_policy']='Direct published P0 and approved P1 comparisons; only source-bound titles/2025 approved origin row/new prose shear/new Batang W+precise glyph origins/2026 p1 one KO row pre-existing AA-contact correction. Additional2026 precontact control comparison permits only that one row. No title-only global pixel-equivalence claim.'
    return layout

def precise_prose_text(page,point,text,fontname,size,color,angle):
    """Same text/glyphs/Tf, source-correct physical shear about the same origin."""
    shear=math.tan(math.radians(angle));morph=(point,fitz.Matrix(1,0,shear,1,0,0)) if angle else None
    previous=page.get_contents();page.insert_text(point,text,fontname=fontname,fontsize=size,color=color,morph=morph)
    added=[xref for xref in page.get_contents() if xref not in previous and b'/'+fontname.encode()+b' ' in page.parent.xref_stream(xref)]
    assert len(added)==1
    xref=added[0];data=page.parent.xref_stream(xref);pdfpoint=point*~page.transformation_matrix
    num=rb'[-+]?(?:\d+(?:\.\d*)?|\.\d+)'
    if angle:
        data,count=re.subn(rb'1 0 '+num+rb' 1 '+num+rb' '+num+rb' cm',f'1 0 {shear:.12f} 1 {-shear*pdfpoint.y:.12f} 0 cm'.encode(),data)
        assert count==1
    data,count=re.subn(rb'1 0 0 1 '+num+rb' '+num+rb' Tm',f'1 0 0 1 {pdfpoint.x:.12f} {pdfpoint.y:.12f} Tm'.encode(),data)
    assert count==1;page.parent.update_stream(xref,data)

def capture_width_lineage(page):return capture_original_font_lineage(page)
def fix_widths(page,layout,base,snapshot,doc_role):
    cfg=rules(base);assert cfg['year']==2026 and cfg['new_Batang_W_precision']
    return apply_in_memory(page,layout,cfg['new_Batang_W_precision'],snapshot,doc_role)
def finalize_widths(target,layout,base):
    cfg=rules(base)
    if cfg['year']!=2026:return None
    return finalize_exact_serialization(target,layout,cfg['new_Batang_W_precision'],layout['r4_new_batang_width_audits'])
