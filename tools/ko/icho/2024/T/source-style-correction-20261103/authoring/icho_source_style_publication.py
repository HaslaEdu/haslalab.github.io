"""Publication checks for the finalized IChO2024 source-style correction."""
import hashlib
import json
import math
from pathlib import Path
from prose_decoration_publication import validate_contact
from icho2024_prose_decoration_publication import SOURCE,MEASUREMENT,CURVE_READER,MAPPING,SEMANTIC
import icho2024_native_d_publication as native_d
import assemble_icho2024_v3_checked as actual_assembly

PUBLISHED='78d869b01f48bd1e050f2b8697900c757f4987331b1895026173e4b3258fe024'
APPROVED='bc06cca28d8b2f3ed93b437a5c3ed12f37cc8dd40d096f174314e5e2dffa68b2'
FREEZE='fd600ecbd54dc70bf25033bf9eebf4a065ac3256175ecfdf3ff70954361625e4'
ASSEMBLY_WRAPPER='5110db69ac0faadd62dcc5baf903ce65dfdec79508b4ef1e4b1a105e8dae9fb7'
P32_PROOF='295d4bcd98d367c2cc0a140ba5d824fdf3345407500b03a127e04d1d2b159219'
P32_LAYOUT='1b5cdf8f40e8774344d024a5ccdbde997137be37a0f18027000619cfc2971eea'
P32_AUDITOR='71a4437ddf0a99abc9585ef3585c26c668e42fc891ee0148f7cf6e44f153f21b'
P32_STROKE='8756e7deb5c4dd9e6d470d9fc562f58398996bc4a34371ebcd759b4da9be9477'
P32_SUPPORT=[56.193,663.8417646507025,109.463,665.2402646461726]
P32_ROWS=[[114.19246673583984,475.7569580078125,267.2073256720969,490.3260498046875],
    [56.192962646484375,651.8989868164062,107.48416717546957,666.4680786132812]]
P32_ADMITTED=[[1328,215],[1328,216],[1328,217],[1329,215],[1329,216],[1329,217]]
QA3_PINS={
    'auditor_code_input_freeze':'cf9cbf12fc44e398d55869c8d0be416c85c6ec347a962567e14376fd406f4ffe',
    'continuation_code_input_freeze':'14461ddd3d1cde2dd46b3253ba397de18257feeec1602b8a40c569becf45d18a',
    'root_GO':'ae675aad54054e8392469c5371907a3936feb9a33df797516237203b0796f245',
    'actual_positive':'1badd547ccd6b1a0a8a624819469da05b5b28376389ae41a9df81c91e77ee382',
    'actual_negative_regressions':'ad132f31de1cb85bddfe3631efa3d12876084fc4a5eae216dc3e06399a5a6445',
    'auditor_program':P32_AUDITOR,
}

def validate_qa3_amendment(ready,profile,checked,read):
    """Retain the reviewed QA3 and continuation GO beside the producer freeze."""
    assert set(profile)==set(ready['qa_amendment'])==set(QA3_PINS)
    documents={};evidence=[]
    for key,digest in QA3_PINS.items():
        assert profile[key]['sha256']==ready['qa_amendment'][key]['sha256']==digest
        file=checked(profile[key]);checked(ready['qa_amendment'][key])
        if file.suffix=='.json':documents[key]=read(file);evidence.append(file)
    go=documents['root_GO']
    assert go['status']=='ROOT_GO_QA3_CONTINUATION_OF_FROZEN_FINAL62_V3'
    assert go['production_freeze_sha256']==FREEZE
    for key in ['auditor_code_input_freeze','continuation_code_input_freeze','actual_positive','actual_negative_regressions']:
        assert go[key+'_sha256']==QA3_PINS[key]
    for key,count in [('auditor_code_input_freeze',274),('continuation_code_input_freeze',648)]:
        table=documents[key]['program_and_input_sha256'];assert len(table)==count
        for path,digest in table.items():checked(dict(path=path,sha256=digest))
    positive=documents['actual_positive'];negative=documents['actual_negative_regressions']
    assert positive['proof_sha256']==P32_PROOF and positive['layout_sha256']==P32_LAYOUT
    assert positive['program_sha256']==P32_AUDITOR and positive['passed']is True
    assert negative['status']=='PASS'and negative['all_rejected']is True
    assert negative['actual_PDF_counterexamples']==3 and negative['additional_layout_binding_counterexamples']==1
    continuation=actual_assembly.O/'qa-amendments/p32-source-underline-support-v3/continuation'
    active={path:digest for path,digest in documents['continuation_code_input_freeze']['program_and_input_sha256'].items()
        if Path(path).resolve().parent==continuation and Path(path).suffix=='.py'}
    assert len(active)==6
    finalizer=Path(ready['program_path']).resolve()
    assert finalizer==continuation/'finalize_ready_qa2.py'
    assert active[str(finalizer)]==ready['program_sha256']
    required=set(active.values())|{P32_AUDITOR,'0735e1cca3fe0b681ee5e166596635ac8dc365547cb8ac548416d608c008fd8f'}
    return evidence,required

def validate_p32_pixel_audit(q,pixel):
    """The external auditor repairs only the fixed original stroke support."""
    assert q['page']==pixel['page']==32 and q['output_sha256']==P32_PROOF
    assert pixel['proof_sha256']==pixel['certified_full_font_curve_proof_sha256']==P32_PROOF
    assert pixel['layout_sha256']==pixel['certified_original_layout_sha256']==P32_LAYOUT
    assert pixel['program_sha256']==P32_AUDITOR
    assert pixel['frozen_pixel_auditor_sha256']=='da97a0ca5a5e425f2dbcb640f274ae48610c4ee55780837e9c71150c1c28e37e'
    assert pixel['source_semantic_mapping_sha256']==MAPPING
    assert pixel['source_mapping_index']==34 and pixel['source_stroke_program_sha256']==P32_STROKE
    assert pixel['source_operator_indices']==[392,393,394]
    assert pixel['anti_alias_support_pad_pt']==.5 and pixel['original_source_stroke_support_rect']==P32_SUPPORT
    assert pixel['source_bound_changed_row_baselines']==[486.906982421875,663.0490112304688]
    assert pixel['source_bound_row_rects']==P32_ROWS
    assert pixel['unchanged_frozen_mask_original_outside_pixels']==6 and pixel['changed_pixels_outside_named_source_rows']==0
    assert pixel['admitted_original_underline_tail_pixel_yx']==P32_ADMITTED
    assert pixel['all_admitted_pixels_exact_original_source_and_P0_stroke_erasure']is True
    assert pixel['all_actual_glyphs_equal_to_full_font_curve_audited_immutable_proof']is True
    assert pixel['glyph_tolerance_pt']==.001 and pixel['native_vector_tolerance_pt']==1e-7
    samples=pixel['actual32x_vertical_stroke_samples']
    assert [s['fraction']for s in samples]==[.1,.25,.5,.75,.9]
    for sample in samples:
        assert sample['byte_identical']is True and sample['source']==sample['candidate']
        assert sample['source'][1] and min(sample['source'][1])<220
    kk=pixel['kk']
    assert kk['actual_embedded_subset_fonts']is True and kk['unchanged_word_space_size_shear_paints']is True
    spec=[s for s in q['prose_vector_decorations']if s['semantic_mapping_index']==34]
    assert len(spec)==1
    spec=spec[0];program=spec['source_program']
    assert program['source_construction_and_paint_fragment_sha256']==P32_STROKE
    assert program['source_operator_indices']==[392,393,394] and program['source_operator_names']==['m','l','S']
    fragment=program['source_construction_and_paint_fragment_latin1'].encode('latin1')
    assert hashlib.sha256(fragment).hexdigest()==P32_STROKE
    assert spec['source_rect']==[56.693,664.5410146484376,108.963,664.5410146484376]

def validate_assembly_receipt(receipt,qa,pdf_pin,ready_pin,bridge_pin,check_pin=None):
    """Bind the current reviewed assembly program to its actual receipt."""
    with Path(actual_assembly.__file__).open('rb')as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==ASSEMBLY_WRAPPER
    assert receipt['wrapper']['sha256']==ASSEMBLY_WRAPPER
    source_path=actual_assembly.O/'frozen/source/IChO_2024_T_EN.pdf'
    source_pins=[p for p in receipt['input_files']if Path(p['path']).resolve()==source_path]
    assert len(source_pins)==1 and source_pins[0]['sha256']==SOURCE,'Missing actual assembly source PDF pin'
    return actual_assembly.validate_receipt(receipt,qa,pdf_pin,ready_pin,bridge_pin,
        actual_assembly.checked if check_pin is None else check_pin)

def validate_page(q,pixel,reference_proof_sha256,inline_atom=None):
    assert q['source_sha256']==SOURCE
    glyph=q['new_korean_glyph_and_geometry_audit'];actual=glyph['actual_glyphs']
    assert glyph['passed']is True and glyph['planned_glyphs']==actual
    assert glyph['geometry_errors']==glyph['missing_or_notdef_glyphs']==[]
    assert 0<=glyph['max_position_error_pt']<=.001 and 0<glyph['position_tolerance_pt']<=.001
    audit=q['actual_prose_underline_coverage_and_style_audit']
    assert audit['passed']is True and audit['proof_sha256']==q['output_sha256']
    assert audit['page']==q['page']and audit['source_sha256']==SOURCE
    assert audit['measurement_code_sha256']==MEASUREMENT and audit['actual_curve_reader_sha256']==CURVE_READER
    assert audit['all_authored_glyphs_verified']==actual
    assert audit['all_actual_curve_bboxes_match_requested_full_font_and_matrix']is True
    assert audit['protected_native_ink_contact_pixels']==0
    assert len(audit['authored_word_style_samples'])==actual
    assert 0<audit['actual_shear_tangent_tolerance']<=1e-9
    for sample in audit['authored_word_style_samples']:
        assert sample['actual_glyph']['gid']>0 and sample['actual_glyph']['c']!='\ufffd'
        assert 0<=sample['actual_curve_bbox_error_pt']<=.001
        assert abs(sample['actual_pdf_shear_tangent']-sample['expected_pdf_shear_tangent'])<=1e-9
        assert abs(sample['expected_pdf_shear_tangent']-math.tan(math.radians(sample['authored_pdf_shear_angle'])))<=1e-9
        if sample['original_source_descriptor_ItalicAngle']:
            assert sample['authored_pdf_shear_angle']==abs(sample['original_source_descriptor_ItalicAngle'])
        if sample['original_source_descriptor_ItalicAngle'] or any(word in sample['original_source_font'].lower()for word in('italic','oblique','slanted')):
            assert sample['authored_pdf_shear_angle']>0
    semantic=q['independent_source_semantic_style_audit']
    assert semantic['passed']is True and semantic['proof_sha256']==q['output_sha256']
    assert semantic['source_sha256']==SOURCE and semantic['mapping_sha256']==MAPPING
    assert semantic['approved_source_clause_manifest_sha256']==APPROVED and semantic['program_sha256']==SEMANTIC
    assert semantic['all_expected_Korean_nonspace_characters_preserved_once']==actual
    for key in ['all_requested_font_roles_bound_to_actual_original_source_styles','exact_original_sizes_and_raw_prose_baseline_pool_membership_preserved','no_other_bold_or_italic_changes']:
        assert semantic[key]is True
    for contact in q.get('intentional_prose_decoration_contacts',[]):validate_contact(q,contact)
    assert len(audit['underline_rows'])==len(semantic['semantic_mappings'])==len(q['prose_vector_decorations'])
    assert pixel['passed']is True and pixel['proof_sha256']==q['output_sha256']
    assert pixel['page']==q['page']and pixel['protected_source_sha256']==SOURCE
    assert pixel['reference_proof_sha256']==reference_proof_sha256
    assert pixel['pixel_scale']==2 and pixel['anti_alias_support_pad_pt']<=.5
    assert pixel['changed_pixels_outside_named_source_rows']==0
    assert pixel['visible_glyph_geometry_outside_rows_exactly_equal']is True
    assert pixel['source_font_programs_images_and_image_placements_preserved']is True
    kk=pixel['kk'];assert kk['passed']is True and kk['proof_sha256']==q['output_sha256']
    assert kk['scale']==2 and kk['threshold']==220
    assert len(kk['pairs'])==kk['tested_close_row_pairs']
    assert all(pair['contact_pixels_2x']==0 for pair in kk['pairs'])
    vector=q['actual_native_vector_coordinate_audit']
    assert vector['coordinate_errors']==[]and 0<vector['max_coordinate_tolerance_pt']<=1e-7
    if q['page']==32:validate_p32_pixel_audit(q,pixel)
    if q['page']==39:
        assert inline_atom and inline_atom['passed']is True and inline_atom['page']==39
        assert inline_atom['proof_sha256']==q['output_sha256']and inline_atom['source_sha256']==SOURCE
        assert inline_atom['source_profile_sha256']=='60f010c33b97f27a5347f187c141dddc46e740bb3023cb98ba66f43413f5153e'
        assert inline_atom['comparison_scale']==4 and inline_atom['actual_grayscale_pixels_different']==0
        assert inline_atom['nonempty_original_native_atom_ink_pixels']>0
        assert inline_atom['expected_image_sha256']==inline_atom['candidate_image_sha256']
        assert inline_atom['source_glyph_font_size_baselines_and_both_native_graphic_programs_compared']is True
        assert inline_atom['program_sha256']=='df0a8297cf4d0ea4142f07e31d49881c0301a20656f7e883b03d4edd06634e44'

def prepare(comp,year,pdf,qa,config_path,root,base):
    def sha(path):
        with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    def checked(pin):
        path=Path(pin['path']).resolve();assert path.is_file()and sha(path)==pin['sha256'],('Stale IChO style evidence',path)
        if 'bytes'in pin:assert path.stat().st_size==pin['bytes']
        return path
    assert comp=='icho'and year==2024
    config=read(config_path);config_sha=sha(config_path)
    assert config['schema']=='icho2024-source-style-publication-config-v1'
    assert config['publication_subdir']=='source-style-correction-20261103'
    assert config['output_sha256']==qa['sha256']==sha(pdf)and qa['source_sha256']==SOURCE and qa['pages']==62
    old_item=next(row for row in read(root/'tools/original_style_publication.json')if row['file']==Path(pdf).name)
    assert old_item['sha256']==PUBLISHED
    old_path=root/old_item['qa'];old=read(old_path)
    assert old['sha256']==PUBLISHED and old['source_sha256']==SOURCE and old['pages']==62
    assert config['pins']
    for pin in config['pins']:checked(pin)
    freeze_path=checked(config['freeze']);assert sha(freeze_path)==FREEZE
    freeze=read(freeze_path)
    assert freeze['approved_source_clause_manifest_sha256']==APPROVED
    assert freeze['source_semantic_mapping_sha256']==MAPPING
    for path,digest in freeze['current_program_and_input_sha256'].items():assert sha(path)==digest
    atom_profile=checked(config['inline_atom_profile'])
    assert sha(atom_profile)=='60f010c33b97f27a5347f187c141dddc46e740bb3023cb98ba66f43413f5153e'
    prefix_profile_path=checked(config['native_prefix_profile'])
    assert sha(prefix_profile_path)==native_d.PROFILE
    prefix_profile=read(prefix_profile_path)
    evidence=[freeze_path,checked(config['ready']),checked(config['approved_clauses']),atom_profile,prefix_profile_path]
    assert sha(config['approved_clauses']['path'])==APPROVED
    ready=read(config['ready']['path'])
    assert ready['year']==2024 and ready['pages']==62 and ready['source']['sha256']==SOURCE
    assert ready['status']=='YEAR_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW'
    assert len(config['pages'])==len(qa['page_audits'])==len(ready['page_results'])==62
    qa3_evidence,qa3_runtime=validate_qa3_amendment(ready,config['qa_amendment'],checked,read)
    evidence.extend(qa3_evidence)
    receipt_path=checked(config['assembly_receipt'])
    original_receipt=Path(pdf).resolve().with_suffix('.assembly-receipt.json')
    assert sha(original_receipt)==config['assembly_receipt']['sha256']
    receipt=read(original_receipt)
    assert checked(config['assembler'])==actual_assembly.ASM
    assert config['assembler']['sha256']==receipt['assembler']['sha256']==actual_assembly.ASM_SHA
    assert checked(receipt['ready'])==actual_assembly.F/'READY.json'
    assert receipt['ready']['sha256']==config['ready']['sha256']
    bridge_pin=receipt['visual_bridge'];checked(bridge_pin)
    assert Path(bridge_pin['path']).resolve()==Path(ready['normalized_visual_bridge']['path']).resolve()
    assert bridge_pin['sha256']==ready['normalized_visual_bridge']['sha256']
    validate_assembly_receipt(receipt,qa,actual_assembly.pin(pdf),receipt['ready'],bridge_pin,checked)
    evidence.append(receipt_path)
    rows=[];underlines=italics=edits=0
    for index,(pin,page,ready_page)in enumerate(zip(config['pages'],qa['page_audits'],ready['page_results'])):
        assert pin['page']==page['page']==ready_page['page']==index+1
        assert ready_page['proof']['sha256']==page['proof_sha256']
        assert ready_page['layout']['sha256']==page['qa_sha256']
        checked(ready_page['proof']);checked(ready_page['layout'])
        assert sha(page['qa_path'])==page['qa_sha256'];body=read(page['qa_path'])
        assert body['page']==index+1 and body['output_sha256']==page['proof_sha256']
        pixel_path=checked(pin['pixel_audit']);pixel=read(pixel_path)
        if index==31:assert page['qa_sha256']==P32_LAYOUT
        atom_path=checked(pin['inline_atom_audit'])if index==38 else None
        atom=read(atom_path)if atom_path else None
        if atom:
            assert atom['layout_sha256']==page['qa_sha256'];evidence.append(atom_path)
        prefix_path=checked(pin['native_prefix_audit'])if index==56 else None
        if prefix_path:
            native_d.validate(body,read(prefix_path),prefix_profile,page['qa_sha256'])
            evidence.append(prefix_path)
        validate_page(body,pixel,old['page_audits'][index]['proof_sha256'],atom)
        assert body['output_sha256']==page['proof_sha256']
        evidence.append(pixel_path)
        semantic=body['independent_source_semantic_style_audit']
        underlines+=len(semantic['semantic_mappings']);italics+=semantic['new_Korean_italic_placements'];edits+=semantic['exact_approved_text_edits']
        rows.append(dict(page=index+1,proof_sha256=page['proof_sha256'],layout_sha256=page['qa_sha256'],
                         pixel_audit_source=str(pixel_path),pixel_audit_sha256=sha(pixel_path)))
        if atom_path:rows[-1].update(inline_atom_audit_source=str(atom_path),inline_atom_audit_sha256=sha(atom_path))
        if prefix_path:rows[-1].update(native_prefix_audit_source=str(prefix_path),native_prefix_audit_sha256=sha(prefix_path))
    assert underlines==68 and italics==9 and edits==54
    for pin in config['evidence']:evidence.append(checked(pin))
    runtime=[];destinations={}
    for pin in config['runtime_files']:
        path=checked(pin);relative=Path(pin['relative_path'])
        assert path.suffix=='.py'and not relative.is_absolute()and'..'not in relative.parts
        key=relative.as_posix().casefold()
        assert key not in destinations or destinations[key]==pin['sha256'],('Conflicting runtime destination',relative)
        destinations[key]=pin['sha256']
        runtime.append(dict(path=str(path),sha256=pin['sha256'],relative_path=relative.as_posix()))
    required={MEASUREMENT,CURVE_READER,SEMANTIC,native_d.AUDITOR};assert required<={pin['sha256']for pin in runtime}
    frozen_programs={digest for path,digest in freeze['current_program_and_input_sha256'].items()if Path(path).suffix=='.py'}
    assert frozen_programs<={pin['sha256']for pin in runtime},'Missing frozen source-style runtime program'
    assert qa3_runtime<={pin['sha256']for pin in runtime},'Missing reviewed QA3/continuation runtime program'
    assert {p['sha256']for p in receipt['assembly_dependencies']}<={p['sha256']for p in runtime},'Missing actual assembler dependency'
    names={}
    for path in evidence:
        assert path.suffix=='.json'
        assert path.name not in names or names[path.name]==sha(path),('Evidence basename collision',path)
        names[path.name]=sha(path)
    manifest=dict(schema='icho2024-source-style-publication-v1',year=2024,source_sha256=SOURCE,
        original_published_sha256=PUBLISHED,reference_publication=dict(path=old_item['qa'],sha256=sha(old_path)),
        ready_source=config['ready']['path'],ready_sha256=config['ready']['sha256'],
        freeze_source=str(freeze_path),freeze_sha256=FREEZE,
        approved_clauses_source=config['approved_clauses']['path'],approved_clauses_sha256=APPROVED,pages=rows)
    manifest.update(inline_atom_profile_source=str(atom_profile),inline_atom_profile_sha256=sha(atom_profile))
    manifest.update(native_prefix_profile_source=str(prefix_profile_path),native_prefix_profile_sha256=sha(prefix_profile_path))
    manifest['qa_amendment']=config['qa_amendment']
    manifest.update(assembly_receipt_source=str(receipt_path),assembly_receipt_sha256=sha(receipt_path))
    assert sha(config_path)==config_sha
    return dict(kind='source_style',config=config,manifest=manifest,evidence=list(dict.fromkeys(evidence)),programs=[Path(__file__),Path(native_d.__file__),Path(actual_assembly.__file__),actual_assembly.ASM],runtime_files=runtime)
