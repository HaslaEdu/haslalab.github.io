"""DRAFT independent exact-P1 delta plus unmodified master/CTM/ink checks.

This file is not a production GO. All PDF/font work is future shared-gate work.
"""
from pathlib import Path
from decimal import Decimal
import argparse, copy, hashlib, json, math, os, re, shutil, sys, traceback, uuid
sys.dont_write_bytecode=True
import postprocess_page07 as p


def validate_marker(marker,spec,receipt,freeze):
    runtime=p.HOME/'page07/repair-runtime-snapshot.json'
    expected=dict(schema='ortvay-page07-exact-row-postprocess-v1',numeric_spec=p.pin(p.SPEC),
        repair_code_input_freeze=p.pin(p.HOME/'REPAIR-CODE-INPUT-FROZEN.json'),root_GO=p.pin(p.HOME/'ROOT-GO.json'),
        postprocessor=p.pin(p.HOME/'postprocess_page07.py'),repair_runtime_snapshot=p.pin(runtime),
        base_failed_proof=spec['precontact_proof'],base_failed_layout=spec['precontact_layout'],
        slot_id=spec['selected_slot_id'],baseline=spec['selected_baseline'],point_size=spec['source_size_pt'],dx=3.3125,
        selected_stream_xrefs=[317,318,319,320],original_composer_is_base_provenance=True,
        inherited_QA_claims_require_fresh_independent_revalidation=True)
    assert marker==expected,'Repair authoring marker differs from exact source/code/GO/spec binding'
    snapshot=p.read(runtime)
    assert snapshot['numeric_spec']==p.pin(p.SPEC)
    assert snapshot['repair_code_input_freeze']==expected['repair_code_input_freeze'] and snapshot['root_GO']==expected['root_GO']
    assert snapshot['base_profile']==freeze['base_profile']
    assert snapshot['additional_runtime_count']==3 and snapshot['base_original_runtime_count']==46
    files=snapshot['files'];programs={v['path']:v['sha256']for v in freeze['additional_runtime_files']}
    assert set(files)==set(programs)
    for path,value in files.items():
        assert value['sha256']==programs[path]
        p.checked(dict(path=path,sha256=programs[path]))
        retained=p.checked(dict(path=value['retained_copy'],sha256=programs[path]))
        assert retained==p.HOME/'page07/runtime-sources/additional'/Path(path).name


def exact_delta(before, after, spec):
    assert len(before)==len(after)
    wanted=spec['selected_actual_trial']['actual_master_trace']
    changed=[];unchanged=0;maximum=0.
    for old,new in zip(before,after):
        matches=[g for g in wanted if old['cp']==ord(g['character']) and old['gid']==g['gid']
                 and list(old['origin'])==g['old_origin'] and old['size']==g['size']]
        if not matches:
            assert old==new,('Nonselected actual glyph changed',old,new);unchanged+=1;continue
        assert len(matches)==1 and old['font']=='Batang'
        expected=copy.deepcopy(old);expected['origin']=list(old['origin']);expected['bbox']=list(old['bbox']);expected['origin'][0]+=spec['dx']
        expected['bbox'][0]+=spec['dx'];expected['bbox'][2]+=spec['dx']
        for key in old:
            if key in ('origin','bbox'):
                for i,(a,b) in enumerate(zip(expected[key],new[key])):
                    if i%2:assert a==b,('Selected y/baseline changed',key,i)
                    else:maximum=max(maximum,abs(a-b));assert abs(a-b)<=.001
            else:assert old[key]==new[key],('Selected glyph identity/style changed',key)
        changed.append(old['gid'])
    assert changed==[9170,18350,10706,85]
    return unchanged,maximum


def object_delta(old,new,selected,expected_data):
    assert new.xref_length()>=old.xref_length()
    unchanged_objects=unchanged_streams=0;changes=[]
    for xref in range(1,old.xref_length()):
        if xref in selected:
            a,b=old.xref_stream(xref),new.xref_stream(xref)
            assert b==expected_data[xref],('Selected stream differs beyond exact approved Tm e',xref)
            # Only stream encoding/length may be reserialized for these four.
            keys=lambda d:set(d.xref_get_keys(xref))-{'Length','Filter','DecodeParms'}
            assert keys(old)==keys(new)
            assert all(old.xref_get_key(xref,k)==new.xref_get_key(xref,k)for k in keys(old))
            changes.append(dict(xref=xref,before_sha256=hashlib.sha256(a).hexdigest(),after_sha256=hashlib.sha256(b).hexdigest(),
                exact_decimal_Tm_e_delta='3.3125',all_other_decoded_bytes_identical=True))
        else:
            assert old.xref_object(xref)==new.xref_object(xref),('Nonselected effective object changed',xref)
            assert old.xref_is_stream(xref)==new.xref_is_stream(xref)
            if old.xref_is_stream(xref):
                assert old.xref_stream(xref)==new.xref_stream(xref)
                assert old.xref_stream_raw(xref)==new.xref_stream_raw(xref)
                unchanged_streams+=1
            unchanged_objects+=1
    for xref in range(old.xref_length(),new.xref_length()):
        assert re.search(r'/Type\s*/XRef\b',new.xref_object(xref)),('Unexpected new object',xref)
    assert len(changes)==4
    return dict(passed=True,selected_stream_count=4,selected_streams=changes,
        all_other_effective_objects_exact=True,all_other_raw_and_decoded_streams_exact=True,
        unchanged_effective_objects=unchanged_objects,unchanged_streams=unchanged_streams,
        font_programs_and_encoded_images_exact=True,extra_structural_xref_objects_only=True)


def raster(page,scale,fitz,np):
    pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
    return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,pix.n)


def read_only_native_verify(nv,target,layout,is_candidate):
    """Frozen nv.verify refreshes its adjacent JSON. Never give it an input.

    A retained, byte-identical scratch PDF/layout is the verified artifact.
    The source candidate PDF/layout hashes must remain exact even on failure.
    Only the native-audit field may differ semantically in scratch JSON.
    """
    before_pdf,before_layout=p.pin(target),p.pin(layout)
    label='candidate'if is_candidate else'positive'
    scratch=p.HOME/'audit-scratch'/f'{label}-{before_pdf["sha256"][:12]}-{uuid.uuid4().hex}'
    scratch.mkdir(parents=True,exist_ok=False)
    pdf=scratch/'page07.pdf';adjacent=scratch/'page07.layout.json';retained=scratch/'page07.layout.input.json'
    shutil.copyfile(target,pdf);shutil.copyfile(layout,adjacent);shutil.copyfile(layout,retained)
    assert p.sha(pdf)==before_pdf['sha256']and p.sha(adjacent)==p.sha(retained)==before_layout['sha256']
    before=p.read(retained);verifier=Path(nv.__file__).resolve();verifier_pin=p.pin(verifier)
    try:result=nv.verify(pdf)
    finally:
        assert p.pin(target)==before_pdf and p.pin(layout)==before_layout,'Native verifier mutated an original input'
        assert p.sha(pdf)==before_pdf['sha256']and p.sha(retained)==before_layout['sha256']
        assert p.pin(verifier)==verifier_pin,'Frozen native verifier changed'
    after=p.read(adjacent);expected=copy.deepcopy(before);expected['actual_native_vector_coordinate_audit']=result
    assert after==expected,'Native scratch refresh changed another body field'
    replay=dict(passed=True,input_pdf=before_pdf,input_layout=before_layout,input_pdf_after=p.pin(target),input_layout_after=p.pin(layout),
        scratch_pdf=p.pin(pdf),scratch_layout_input=p.pin(retained),scratch_layout_after=p.pin(adjacent),
        scratch_pdf_byte_identical_to_input=True,frozen_verifier_program=verifier_pin,
        only_refreshed_semantic_field='actual_native_vector_coordinate_audit',all_other_layout_fields_exact=True,
        frozen_native_math_and_tolerances_unchanged=True)
    p.write_new(scratch/'NATIVE-REPLAY.json',replay)
    return result,dict(replay,receipt=p.pin(scratch/'NATIVE-REPLAY.json'))


def pixels_with_actual_support(old_path,new_path,old_records,new_records,fitz,np,clone,scales=(2,4,8)):
    reports=[]
    with fitz.open(old_path)as old,fitz.open(new_path)as new,clone(old_path,old_records)as a,clone(new_path,new_records)as b:
        for scale in scales:
            left,right=raster(old[0],scale,fitz,np),raster(new[0],scale,fitz,np)
            aa,bb=raster(a[0],scale,fitz,np),raster(b[0],scale,fitz,np)
            assert left.shape==right.shape==aa.shape==bb.shape
            support=np.any(aa!=255,axis=2)|np.any(bb!=255,axis=2)
            difference=np.any(left!=right,axis=2)
            outside=int((difference&~support).sum());assert outside==0,('Pixels outside exact glyph ink support',scale,outside)
            reports.append(dict(scale=scale,total_changed_pixels=int(difference.sum()),actual_support_pixels=int(support.sum()),changed_pixels_outside_union=outside))
    return reports


def verify(candidate_pdf=None,candidate_layout=None):
    freeze,go,spec=p.authorization();out=p.HOME/'page07'
    receipt=p.read(out/'postprocess-receipt.json')
    is_candidate=candidate_pdf is not None
    if is_candidate:
        target=Path(candidate_pdf).resolve();candidate_layout=Path(candidate_layout).resolve()
        assert target.is_relative_to(p.HOME/'regressions') and candidate_layout==target.with_suffix('.layout.json')
        assert target.is_file() and candidate_layout.is_file()
    else:
        assert candidate_layout is None;target=p.checked(receipt['proof'])
    old_path=p.checked(spec['precontact_proof']);old_body=p.read(p.checked(spec['precontact_layout']))
    draft=p.read(candidate_layout if is_candidate else p.checked(receipt['draft_layout']));marker=draft.pop('r4_page07_exact_row_postprocess')
    expected=p.expected_body(old_body,spec);expected['output_sha256']=p.sha(target);assert draft==expected
    assert marker['dx']==spec['dx']==3.3125 and marker['numeric_spec']==p.pin(p.SPEC)
    assert marker['base_failed_proof']==p.pin(old_path) and marker['base_failed_layout']==spec['precontact_layout']
    assert marker['repair_code_input_freeze']==p.pin(p.HOME/'REPAIR-CODE-INPUT-FROZEN.json')
    assert marker['root_GO']==p.pin(p.HOME/'ROOT-GO.json')
    assert marker['postprocessor']==p.pin(p.HOME/'postprocess_page07.py')
    validate_marker(marker,spec,receipt,freeze)
    q=dict(draft,r4_page07_exact_row_postprocess=marker)
    # Legacy body has no new-glyph audit branch. No stale/fabricated new branch
    # is introduced: fresh master/CTM/outline evidence stays in this sidecar.
    assert 'new_korean_glyph_and_geometry_audit'not in old_body
    final_layout=candidate_layout if is_candidate else out/'page07.layout.json'
    if not is_candidate:
        assert not final_layout.exists();shutil.copyfile(p.checked(receipt['draft_layout']),final_layout)
    effective=p.checked(dict(path=q['effective_plan_path'],sha256=q['effective_plan_sha256']))
    if not is_candidate:shutil.copyfile(effective,out/'page07.effective-plan.json')
    sys.path.insert(0,str(p.R4/'common'));sys.path.insert(0,str(p.QA))
    import pymupdf as fitz
    import numpy as np
    import r4_guard as g
    import run_amended_audit as original_qa
    from amended_actual_paint import streams,glyphs,clone_with_streams,actual_row_ink,actual_native_contact
    from amended_independent_qa import expected_glyphs,match_expected,reference_comparison
    from transform_guard import verify_physical_streams
    from amended_outline_qa import audit as outline_audit
    g.assert_runtime_frozen();original_qa.check_external_freeze()
    base_build=freeze['base_original_build_snapshot'];p.checked(base_build)
    os.environ['R4_RUNTIME_SNAPSHOT']=base_build['path'];os.environ['R4_OUTPUT_DIRECTORY']=str(out)
    g.assert_runtime_snapshot();e,nv,kernel,vector_path=original_qa.load_kernel(2026);cfg=g.rules(p.R4/'2026')
    with fitz.open(old_path)as old,fitz.open(target)as new:
        old_records,new_records=streams(old[0]),streams(new[0])
        selected=[s for s in old_records if abs(s['actual_baseline']-spec['selected_baseline'])<.001]
        assert len(selected)==4 and sorted(s['xref']for s in selected)==marker['selected_stream_xrefs']==[317,318,319,320]
        # Independently parse both Tm operands; no producer patch function call.
        number=rb'[-+]?(?:\d+(?:\.\d*)?|\.\d+)';pattern=re.compile(rb'(?<!\S)'+rb'\s+'.join([b'('+number+b')']*6)+rb'\s+Tm\b')
        expected_data={}
        for s in selected:
            before=old.xref_stream(s['xref']);after=new.xref_stream(s['xref'])
            a,b=list(pattern.finditer(before)),list(pattern.finditer(after));assert len(a)==len(b)==1
            a,b=a[0],b[0];assert Decimal(b.group(5).decode())-Decimal(a.group(5).decode())==Decimal('3.3125'),'Exact approved Decimal Tm e delta required'
            assert before[:a.start(5)]==after[:b.start(5)] and before[a.end(5):]==after[b.end(5):]
            expected_data[s['xref']]=before[:a.start(5)]+b.group(5)+before[a.end(5):]
        objects=object_delta(old,new,set(expected_data),expected_data)
        assert target.read_bytes().startswith(old_path.read_bytes());objects['original_PDF_prefix_exact']=True
        all_before,all_after=glyphs(old[0],None,True),glyphs(new[0],None,True)
        unchanged,residual=exact_delta(all_before,all_after,spec)
        assert glyphs(old[0],False,True)==glyphs(new[0],False,True)
        matched,geometry=match_expected(expected_glyphs(e,q,2026),new[0])
        matched_all,all_geometry=match_expected(expected_glyphs(e,q,2026,True),new[0],True)
        old_matched,_=match_expected(expected_glyphs(e,old_body,2026),old[0])
        assert e.original_helpers.font_programs(old,old[0])==e.original_helpers.font_programs(new,new[0])
        assert e.original_helpers.encoded_images(old,old[0])==e.original_helpers.encoded_images(new,new[0])
        assert e.original_helpers.native_images(old[0])==e.original_helpers.native_images(new[0])
    physical=verify_physical_streams(target,q,cfg,matched_all)
    outline=outline_audit(target,matched,cfg)
    native,native_replay=read_only_native_verify(nv,target,final_layout,is_candidate)
    kk=actual_row_ink(target,q,[(spec['selected_baseline']-10.6719970703125,spec['selected_baseline'])]);assert kk['passed']
    contact=actual_native_contact(target);assert contact['passed']
    selected_new=[s for s in new_records if s['xref']in expected_data]
    p1_pixels=pixels_with_actual_support(old_path,target,selected,selected_new,fitz,np,clone_with_streams)
    p0=next(v for v in cfg['reference_pages']if v['page']==7)['P0']
    inherited=reference_comparison(e,old_body,old_path,cfg,old_matched,'P0_current_published',p0['proof_path'],p0['layout_path'])
    with fitz.open(p0['proof_path'])as doc:p0_records=streams(doc[0])
    p0_pixels=pixels_with_actual_support(p0['proof_path'],target,p0_records,new_records,fitz,np,clone_with_streams)
    # Native contact is checked independently of either pixel union, at every
    # fixed scale. Both controls retain the exact target resource dictionary.
    multiscale=[]
    with clone_with_streams(target,new_records)as only_ko,fitz.open(target)as only_native:
        for s in new_records:only_native.update_stream(s['xref'],b'')
        for scale in (2,4,8):
            gray=lambda pg:pg.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False)
            aa,bb=gray(only_ko[0]),gray(only_native[0])
            a=np.frombuffer(aa.samples,np.uint8).reshape(aa.height,aa.width);b=np.frombuffer(bb.samples,np.uint8).reshape(bb.height,bb.width)
            count=int(((a<220)&(b<180)).sum());assert count==0
            multiscale.append(dict(scale=scale,threshold=180,contact_pixels=count))
    contact['fixed_multiscale_native_contact']=multiscale
    contact['contact_pixels_by_scale']={str(v['scale']):v['contact_pixels']for v in multiscale}
    contact['KO_threshold']=220;contact['native_threshold']=180
    p1=dict(passed=True,reference_proof=p.pin(old_path),reference_layout=spec['precontact_layout'],
        all_visible_glyphs_including_spaces=len(all_before),selected_new_KO_glyphs=4,
        nonselected_new_KO_glyphs_including_spaces=physical['all_KO_glyphs_including_spaces_verified']-4,
        nonselected_glyph_attributes_bit_exact=True,original_native_glyphs_bit_exact=True,
        selected_GIDs=[9170,18350,10706,85],exact_decimal_Tm_e_delta='3.3125',
        max_actual_selected_dx_residual_pt=residual,selected_y_size_font_GID_color_opacity_paint_direction_exact=True,
        pixel_union_by_scale=[dict(scale=x['scale'],changed_pixels_outside_exact_old_new_row_ink_union=x['changed_pixels_outside_union'],total_changed_pixels=x['total_changed_pixels'])for x in p1_pixels])
    p0_report=dict(passed=True,P0=dict(path=p0['proof_path'],sha256=p0['proof_sha256']),failed_P1=p.pin(old_path),target=p.pin(target),
        inherited_base_comparison=inherited,P0_origin_bit_exact_claimed=False,native_fonts_images_exact=True,
        actual_pixel_mask_scope='all_actual_P0_and_target_KO_stream_RGB_ink_support',
        exact_exception_mask_claimed=False,change_scope_independently_restricted_by=['unmodified_P0_to_failed_P1_reference_contract','exact_failed_P1_to_target_four_glyph_and_object_contract'],
        pixel_union_by_scale=[dict(scale=x['scale'],changed_pixels_outside_actual_P0_target_all_KO_ink_support=x['changed_pixels_outside_union'],total_changed_pixels=x['total_changed_pixels'])for x in p0_pixels])
    value=dict(schema='ortvay-2026-page07-additive-repair-audit-v1',status='PAGE07_ADDITIVE_REPAIR_ALL_STRICT_CHECKS_PASS',passed=True,year=2026,page=7,
        proof_sha256=p.sha(target),target=p.pin(target),proof=p.pin(target),layout=p.pin(final_layout),
        numeric_spec=p.pin(p.SPEC),base_profile=freeze['base_profile'],repair_code_input_freeze=p.pin(p.HOME/'REPAIR-CODE-INPUT-FROZEN.json'),root_GO=p.pin(p.HOME/'ROOT-GO.json'),
        base_failed_proof=p.pin(old_path),base_failed_layout=spec['precontact_layout'],base_failed_runtime_snapshot=freeze['base_failed_runtime_snapshot'],
        base_original_build_snapshot=base_build,repair_runtime_snapshot=marker['repair_runtime_snapshot'],
        original_full_master_geometry=geometry,actual_including_space_glyph_geometry=all_geometry,
        actual_full_Tm_CTM_physical_transform_audit=physical,actual_target_physical_shear=physical['source_bound_italic_streams'],
        actual_outline_and_encoded_W_audit_pending=False,actual_outline_and_encoded_W_audit=outline,
        actual_native_vector_coordinate_audit=native,actual_stream_interrow_ink=kk,actual_target_language_vs_native_ink=contact,
        native_vector_readonly_replay=native_replay,
        P1_failed_exact_delta_comparison=p1,P0_inherited_W_precision_plus_exact_repair_union_comparison=p0_report,
        decoded_object_and_stream_preservation=objects,auditor_program=p.pin(__file__))
    if not is_candidate:
        p.write_new(out/'independent-qa.json',value)
        assert not (out/'page07.png').exists()
        with fitz.open(target)as doc:doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(out/'page07.png')
    p.preserved(freeze)
    return value


def regressions():
    """Seven genuine PDF mutations plus four separately labelled bindings.

    Each PDF control has an adjacent fresh-hash layout and runs the same
    read-only candidate core. Only AssertionError invariant failures count.
    Other exceptions abort and preserve partial controls without a PASS.
    """
    freeze,go,spec=p.authorization();positive=p.HOME/'page07';root=p.HOME/'regressions'
    assert not root.exists();root.mkdir()
    protected={str(x):p.sha(x)for x in positive.rglob('*')if x.is_file()}
    original=positive/'page07.pdf';layout=positive/'page07.layout.json'
    assert p.read(positive/'independent-qa.json')['passed']is True
    sys.path.insert(0,str(p.QA))
    import pymupdf as fitz
    from amended_actual_paint import streams,clone_with_streams
    import continue_and_bridge_2026 as bridge
    with fitz.open(original)as doc:records=streams(doc[0])
    lower=[s for s in records if s['xref']in [317,318,319,320]]
    upper=[s for s in records if abs(s['actual_baseline']-410.8339538574219)<.001]
    other=next(s for s in records if s not in lower and s not in upper)
    number=rb'[-+]?(?:\d+(?:\.\d*)?|\.\d+)'
    pattern=re.compile(rb'(?<!\S)'+rb'\s+'.join([b'('+number+b')']*6)+rb'\s+Tm\b')
    def move(doc,selected,delta):
        for record in selected:
            data=doc.xref_stream(record['xref']);matches=list(pattern.finditer(data));assert len(matches)==1
            match=matches[0];replacement=format(Decimal(match.group(5).decode())+Decimal(str(delta)),'.12f').encode()
            doc.update_stream(record['xref'],data[:match.start(5)]+replacement+data[match.end(5):],compress=False)
    def native_inside(doc):
        ko={s['xref']for s in records}
        native=next(x for x in doc[0].get_contents()if x not in ko and b'BT'in doc.xref_stream(x))
        # A retained native stream receives an opaque black mark inside the
        # selected-row glyph support. It must fail native/object preservation
        # even though a row-only raster mask could otherwise cover this pixel.
        import numpy as np
        with clone_with_streams(original,lower)as isolated:
            mask=isolated[0].get_pixmap(matrix=fitz.Matrix(8,8),colorspace=fitz.csGRAY,alpha=False)
            pixels=np.frombuffer(mask.samples,np.uint8).reshape(mask.height,mask.width)
            hits=np.argwhere(pixels<220);assert len(hits)
            iy,ix=map(int,hits[len(hits)//2]);intensity=int(pixels[iy,ix])
        x=ix/8;y=doc[0].rect.height-(iy+1)/8
        data=doc.xref_stream(native)+f'\nq 0 0 0 rg {x:.12f} {y:.12f} 0.125 0.125 re f Q\n'.encode()
        doc.update_stream(native,data,compress=False)
        return dict(native_stream_xref=native,inside_actual_selected_row_mask_pixel_8x=[ix,iy],original_row_pixel_intensity=intensity)
    def width(doc):
        font=next(v for v in doc[0].get_fonts(full=True)if v[4]=='KO_Natural_serif')
        child=int(re.search(r'(\d+)\s+0\s+R',doc.xref_get_key(font[0],'DescendantFonts')[1]).group(1))
        old=doc.xref_get_key(child,'DW');value='987'if old[1]!='987'else'986'
        doc.xref_set_key(child,'DW',value)
    specs=[('old_failed_P1_no_shift',lambda d:move(d,lower,-3.3125),'exact_Decimal_Tm_e_delta'),
        ('dx_3.1875_two_x_contact',lambda d:move(d,lower,-.125),'exact_Decimal_Tm_e_delta'),
        ('wrong_upper_row_moved',lambda d:move(d,upper,3.3125),'nonselected_effective_object_or_stream_exact'),
        ('only_three_of_four_glyphs_shifted',lambda d:move(d,lower[-1:],-3.3125),'exact_Decimal_Tm_e_delta'),
        ('other_KO_glyph_moved',lambda d:move(d,[other],.25),'nonselected_effective_object_or_stream_exact'),
        ('original_native_glyph_changed',native_inside,'native_effective_object_or_stream_exact'),
        ('font_program_or_W_changed',width,'font_resource_effective_object_exact')]
    rows=[]
    def rejection(error):
        frame=traceback.extract_tb(error.__traceback__)[-1]
        return dict(exception_type='AssertionError',message=str(error)or frame.line,
                    stage=f'{Path(frame.filename).name}:{frame.name}:{frame.lineno}')
    for name,mutate,guard in specs:
        folder=root/name;folder.mkdir();candidate=folder/'page07.pdf';qpath=candidate.with_suffix('.layout.json')
        shutil.copyfile(original,candidate)
        with fitz.open(candidate)as doc:mutation=mutate(doc);assert doc.can_save_incrementally();doc.saveIncr()
        q=p.read(layout);q['output_sha256']=p.sha(candidate);p.write_new(qpath,q)
        assert p.read(qpath)['output_sha256']==p.sha(candidate)
        try:verify(candidate,qpath)
        except AssertionError as error:
            frame=traceback.extract_tb(error.__traceback__)[-1]
            expected_function='verify'if guard=='exact_Decimal_Tm_e_delta'else'object_delta'
            assert Path(frame.filename).name=='audit_page07_repair.py'and frame.name==expected_function,('Unexpected rejection stage, not a genuine PDF invariant',name,frame)
            if expected_function=='verify':assert str(error)=='Exact approved Decimal Tm e delta required'
            row=dict(name=name,candidate_proof=p.pin(candidate),candidate_layout=p.pin(qpath),
                fresh_layout_output_sha_matches_candidate_pdf=True,rejected=True,expected_guard=guard,actual_error=rejection(error),binding_only=False)
            if name=='original_native_glyph_changed':
                row['actual_mutation']='Native retained content stream black mark inside selected-row ink support; native content change, not a text retyping operation.'
                row['mutation_details']=mutation
            rows.append(row);p.write_new(folder/'REJECTED.json',row)
        else:raise AssertionError('Actual PDF control was accepted: '+name)
    receipt=p.read(positive/'postprocess-receipt.json');marker=p.read(layout)['r4_page07_exact_row_postprocess']
    def bad_go():
        value=copy.deepcopy(marker);value['root_GO']['sha256']='0'*64;validate_marker(value,spec,receipt,freeze)
    def bad_program():
        value=copy.deepcopy(marker);value['postprocessor']['sha256']='0'*64;validate_marker(value,spec,receipt,freeze)
    def bad_copy():
        value=p.pin(original);value['sha256']='0'*64;bridge.validate_copy(p.pin(original),value)
    def bad_page():
        nine=p.read(bridge.NINE)['page_results'][0];bridge.origin_row(nine['machine_result'],nine['visual_review'],2)
    for name,call in [('wrong_or_stale_repair_root_GO',bad_go),('wrong_runtime_program_sha',bad_program),
                      ('wrong_copy_origin_or_copy_SHA',bad_copy),('wrong_page_origin_mapping',bad_page)]:
        try:call()
        except AssertionError as error:rows.append(dict(name=name,rejected=True,binding_only=True,expected_guard=name,actual_error=rejection(error)))
        else:raise AssertionError('Binding control accepted: '+name)
    # Earlier rejecting fixtures never reach the frozen native verifier. A
    # valid candidate must traverse that path and still leave both supplied
    # files and the complete original positive artifact tree unchanged.
    valid_dir=root/'valid-candidate-read-only';valid_dir.mkdir()
    valid_pdf=valid_dir/'page07.pdf';valid_layout=valid_pdf.with_suffix('.layout.json')
    shutil.copyfile(original,valid_pdf);shutil.copyfile(layout,valid_layout)
    valid_before=dict(proof=p.pin(valid_pdf),layout=p.pin(valid_layout))
    successful=verify(valid_pdf,valid_layout)
    valid_after=dict(proof=p.pin(valid_pdf),layout=p.pin(valid_layout))
    assert valid_before==valid_after
    assert protected=={str(x):p.sha(x)for x in positive.rglob('*')if x.is_file()}
    valid_report=dict(status='VALID_CANDIDATE_FULL_AUDIT_PASS_INPUTS_AND_POSITIVE_TREE_UNCHANGED',passed=True,
        before=valid_before,after=valid_after,candidate_core_passed=True,positive_tree_sha256_before=protected,
        positive_tree_sha256_after={str(x):p.sha(x)for x in positive.rglob('*')if x.is_file()},
        native_vector_readonly_replay=successful['native_vector_readonly_replay'],
        repair_code_input_freeze=p.pin(p.HOME/'REPAIR-CODE-INPUT-FROZEN.json'),program=p.pin(__file__))
    p.write_new(valid_dir/'VALID-CANDIDATE-PASS.json',valid_report)
    assert len(rows)==11 and protected=={str(x):p.sha(x)for x in positive.rglob('*')if x.is_file()}
    p.preserved(freeze)
    p.write_new(root/'actual-negative-regressions.json',dict(schema='ortvay-2026-page07-actual-repair-negative-regressions-v1',
        status='ALL_REQUIRED_ACTUAL_PDF_AND_BINDING_NEGATIVES_REJECTED',numeric_spec=p.pin(p.SPEC),
        repair_code_input_freeze=p.pin(p.HOME/'REPAIR-CODE-INPUT-FROZEN.json'),root_GO=p.pin(p.HOME/'ROOT-GO.json'),
        actual_positive=p.pin(positive/'independent-qa.json'),cases=rows,positive_files_rehashed_unchanged=protected,
        valid_candidate_read_only_control=p.pin(valid_dir/'VALID-CANDIDATE-PASS.json'),
        no_missing_file_or_import_failure_counted=True,program=p.pin(__file__)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['positive','regressions'])
    command=parser.parse_args().command
    if command=='positive':verify()
    else:regressions()
