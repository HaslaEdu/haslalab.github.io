"""DRAFT mixed-origin machine/read/copy/READY bridge; never assembles/publishes.

The nine original pages already exist and are read-only. Their frozen producer,
machine/read manifests, snapshots and all embedded paths remain unchanged.
"""
from pathlib import Path
import argparse, copy, hashlib, json, shutil, sys
sys.dont_write_bytecode=True
import postprocess_page07 as p
PRODUCTION=p.R4/'production-continuation/full-ctm-v1-20261103'
NINE=p.R4/'experiments/resume-original-2026-pages08-10-20261104/UNCHANGED-NINE-PAGES-READ-HANDOFF.json'
NINE_SHA='1f449999106262b64622bfb090f7ae69e6bbbd1d86e87f97a42ee9e9cee8a100'
ARTIFACTS=('proof','layout','png','independent_audit','effective_plan','runtime_snapshot')
BASE_FIELDS=('qa_profile_freeze','qa_profile_root_go','qa_profile_actual_regressions',
    'qa_profile_post_freeze_guard','code_input_freeze','original_code_input_freeze','original_runtime_freeze')
NEGATIVES=('old_failed_P1_no_shift','dx_3.1875_two_x_contact','wrong_upper_row_moved',
    'only_three_of_four_glyphs_shifted','other_KO_glyph_moved','original_native_glyph_changed','font_program_or_W_changed')
BINDINGS=('wrong_or_stale_repair_root_GO','wrong_runtime_program_sha','wrong_copy_origin_or_copy_SHA','wrong_page_origin_mapping')


def validate_copy(origin,copied):
    left,right=p.checked(origin),p.checked(copied)
    assert origin['sha256']==copied['sha256'] and left.read_bytes()==right.read_bytes()
    return True


def profile(freeze):
    out=p.HOME/'page07';positive=out/'independent-qa.json';negative=p.HOME/'regressions/actual-negative-regressions.json'
    a,n=p.read(positive),p.read(negative)
    assert a['passed']is True and a['status']=='PAGE07_ADDITIVE_REPAIR_ALL_STRICT_CHECKS_PASS'
    assert (a['year'],a['page'])==(2026,7)
    assert n['status']=='ALL_REQUIRED_ACTUAL_PDF_AND_BINDING_NEGATIVES_REJECTED'
    assert n['repair_code_input_freeze']==p.pin(p.HOME/'REPAIR-CODE-INPUT-FROZEN.json')
    assert n['numeric_spec']==p.pin(p.SPEC)
    rows=n['cases'];assert len(rows)==len(NEGATIVES)+len(BINDINGS)
    assert {r['name']for r in rows}==set(NEGATIVES+BINDINGS)
    for row in rows:
        assert row['rejected']is True and row['expected_guard'] and row['actual_error']
        if row['name']in NEGATIVES:
            proof,layout=p.checked(row['candidate_proof']),p.checked(row['candidate_layout'])
            assert row['fresh_layout_output_sha_matches_candidate_pdf']is True
            assert p.read(layout)['output_sha256']==p.sha(proof)
    return dict(schema='ortvay-one-page-postprocess-profile-v1',year=2026,page=7,numeric_spec=p.pin(p.SPEC),
        repair_code_input_freeze=p.pin(p.HOME/'REPAIR-CODE-INPUT-FROZEN.json'),root_GO=p.pin(p.HOME/'ROOT-GO.json'),
        base_failed_proof=a['base_failed_proof'],base_failed_layout=a['base_failed_layout'],
        failed_metadata=p.pin(PRODUCTION/'pages/2026/page07/FAILED.json'),
        base_failed_runtime_snapshot=freeze['base_failed_runtime_snapshot'],
        base_original_build_snapshot=freeze['base_original_build_snapshot'],
        repair_runtime_snapshot=p.pin(out/'repair-runtime-snapshot.json'),additional_runtime_files=freeze['additional_runtime_files'],
        actual_positive=p.pin(positive),actual_negative_regressions=p.pin(negative))


def machine():
    freeze,go,spec=p.authorization();out=p.HOME/'page07';repair=profile(freeze)
    audit=p.read(p.checked(repair['actual_positive']))
    assert audit['target']==p.pin(out/'page07.pdf') and audit['layout']==p.pin(out/'page07.layout.json')
    result=dict(schema='ortvay-one-page-postprocess-machine-result-v1',status='PAGE_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_HUMAN_REVIEW',
        year=2026,page=7,qa_lineage='external_full_ctm_v1_plus_exact_row_postprocess',human_read_pending=True,
        proof=p.pin(out/'page07.pdf'),layout=p.pin(out/'page07.layout.json'),png=p.pin(out/'page07.png'),
        independent_audit=repair['actual_positive'],effective_plan=p.pin(out/'page07.effective-plan.json'),
        runtime_snapshot=freeze['base_original_build_snapshot'],base_failed_runtime_snapshot=freeze['base_failed_runtime_snapshot'],
        repair_runtime_snapshot=repair['repair_runtime_snapshot'],audit_runtime_snapshot=repair['repair_runtime_snapshot'],
        production_runtime_snapshot=repair['repair_runtime_snapshot'],page_repair_profile=repair,
        base46_is_provenance_not_a_claim_of_old_only_execution=True,**freeze['base_profile'])
    for key in ARTIFACTS:p.checked(result[key])
    p.write_new(out/'result.json',result);p.preserved(freeze)


def record_read(reviewer,notes,evidence):
    freeze,go,spec=p.authorization();out=p.HOME/'page07';result=p.read(out/'result.json')
    assert result['human_read_pending']is True and result['page']==7
    assert reviewer and notes and evidence,'Actual source/candidate reading and concrete observations are required'
    body=p.read(p.checked(result['layout']));images=[p.pin(Path(x).resolve())for x in evidence]
    assert any(x['sha256']==result['png']['sha256']for x in images),'Include the actual final candidate PNG'
    read=dict(schema='ortvay-page07-actual-repair-PNG-read-v1',status='ACTUAL_FINAL_PNG_ORIGINAL_RESOLUTION_READ_PASS',
        year=2026,page=7,reviewer=reviewer,notes=notes,artifacts={k:result[k]for k in ARTIFACTS},
        machine_result=p.pin(out/'result.json'),composer=dict(path=body['composer_path'],sha256=body['composer_sha256']),
        additional_authoring_lineage=result['page_repair_profile'],actual_read_evidence=images)
    p.write_new(out/'visual-read.json',read);p.preserved(freeze)


def origin_row(machine_path,read_path,page):
    original=p.read(p.checked(machine_path));review=p.read(p.checked(read_path))
    assert original['year']==review['year']==2026 and original['page']==review['page']==page
    assert original['human_read_pending']is True and original['status']=='PAGE_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_HUMAN_REVIEW'
    assert review.get('passed')is True or review.get('status')=='ACTUAL_FINAL_PNG_ORIGINAL_RESOLUTION_READ_PASS'
    assert review['reviewer'] and review['notes']
    artifacts=review.get('artifacts',review.get('artifact_pins'))
    for key in ARTIFACTS:
        assert artifacts[key]==original[key];p.checked(original[key])
    assert review['machine_result']==machine_path
    body=p.read(original['layout']['path']);assert body['output_sha256']==original['proof']['sha256']
    composer=dict(path=body['composer_path'],sha256=body['composer_sha256']);p.checked(composer)
    assert review['composer']==composer
    row=copy.deepcopy(original);row.update(reviewed=True,human_read_pending=False,machine_result=machine_path,visual_review=read_path,
        composer=composer,composer_path=composer['path'],composer_sha256=composer['sha256'])
    return row,review,body


def finalize():
    freeze,go,spec=p.authorization();repair=profile(freeze)
    assert p.sha(NINE)==NINE_SHA;handoff=p.read(NINE)
    assert handoff['pages']==[1,2,3,4,5,6,8,9,10]
    nine={v['page']:v for v in handoff['page_results']};rows=[];bodies=[];reads=[]
    for n in range(1,11):
        if n==7:machine_path,read_path=p.pin(p.HOME/'page07/result.json'),p.pin(p.HOME/'page07/visual-read.json')
        else:machine_path,read_path=nine[n]['machine_result'],nine[n]['visual_review']
        row,review,body=origin_row(machine_path,read_path,n)
        if n!=7:
            assert row['qa_lineage']=='external_full_ctm_v1'
            for key in BASE_FIELDS:assert row[key]==freeze['base_profile'][key]
        else:assert row['qa_lineage']=='external_full_ctm_v1_plus_exact_row_postprocess' and row['page_repair_profile']==repair
        rows.append(row);reads.append(review);bodies.append(body)
    assert len({q['composer_sha256']for q in bodies})==1 and len({q['source_sha256']for q in bodies})==1
    assert not p.MIXED.exists();(p.MIXED/'proofs').mkdir(parents=True)
    copies=[];assembly=[]
    for row in rows:
        copied={}
        for key,suffix in [('proof','.pdf'),('layout','.layout.json'),('effective_plan','.effective-plan.json')]:
            origin=row[key];source=p.checked(origin);target=p.MIXED/'proofs'/f'page{row["page"]:02}{suffix}'
            assert not target.exists();shutil.copyfile(source,target);value=p.pin(target);assert validate_copy(origin,value)
            copied[key]=value;copies.append(dict(page=row['page'],key=key,origin=origin,copied=value,byte_equal=True,bytes=target.stat().st_size,
                origin_machine=row['machine_result'],origin_visual_read=row['visual_review']))
        assembly.append(dict(page=row['page'],origin_artifacts={k:row[k]for k in copied},copied_artifacts=copied,historical_body_paths_rewritten=False))
    copy_path=p.MIXED/'ASSEMBLY-COPY-RECEIPT.json'
    receipt=dict(schema='ortvay-mixed-origin-proof-copy-receipt-v1',status='ALL10_ORIGIN_TO_ASSEMBLY_COPIES_BYTE_IDENTICAL',
        year=2026,pages=10,assembly_proof_dir=str(p.MIXED/'proofs'),base_profile=freeze['base_profile'],page_repair_profile=repair,
        copies=copies,body_embedded_paths_rewritten=False,intended_READY_output_path=str(p.MIXED/'READY.json'),
        intended_normalized_visual_output_path=str(p.MIXED/'visual-review-mixed-normalized.json'))
    p.write_new(copy_path,receipt)
    for row in assembly:row['copy_receipt']=p.pin(copy_path)
    visual=[]
    for row,copy_row,review,body in zip(rows,assembly,reads,bodies):
        c=copy_row['copied_artifacts'];visual.append(dict(page=row['page'],reviewed=True,proof_path=c['proof']['path'],proof_sha256=c['proof']['sha256'],
            layout_path=c['layout']['path'],layout_sha256=c['layout']['sha256'],effective_plan_path=body['effective_plan_path'],effective_plan_sha256=body['effective_plan_sha256'],
            composer=row['composer'],composer_sha256=row['composer_sha256'],machine_result=row['machine_result'],visual_review=row['visual_review'],
            render_image=row['png']['path'],render_image_sha256=row['png']['sha256'],review=review['notes'],qa_lineage=row['qa_lineage'],
            assembly_copy_receipt=p.pin(copy_path),origin_artifacts=copy_row['origin_artifacts'],assembly_effective_plan_copy=c['effective_plan'],
            **({'page_repair_profile':repair}if row['page']==7 else{})))
    normalized=p.MIXED/'visual-review-mixed-normalized.json'
    p.write_new(normalized,dict(source_sha256=bodies[0]['source_sha256'],year=2026,pages=visual,assembly_copy_receipt=p.pin(copy_path),
        original_machine_read_body_paths_and_snapshots_unchanged=True))
    rules=p.read(p.R4/'2026/rules.json');composer=rows[0]['composer']
    ready=dict(schema='ortvay-source-style-width-correction-ready-v3-mixed-ctm-page-repair',status='YEAR_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW',
        competition='Ortvay',year=2026,pages=10,source=dict(path=rules['source_path'],sha256=rules['source_sha256']),source_sha256=rules['source_sha256'],
        composer=composer,composer_path=composer['path'],composer_sha256=composer['sha256'],preparation=p.pin(p.R4/'PREPARATION-FROZEN.json'),
        runtime_freeze=p.pin(p.R4/'PROTOTYPE-RUNTIME-FROZEN.json'),final48_go=p.pin(p.R4/'FINAL48-GO.json'),input_ledger=p.pin(p.R4/'input-ledger.json'),
        base_profile=freeze['base_profile'],**freeze['base_profile'],base_profile_runtime_count=46,page_repair_profile=repair,
        page_results=rows,assembly_page_results=assembly,assembly_proof_dir=str(p.MIXED/'proofs'),assembly_copy_receipt=p.pin(copy_path),
        visual_review_normalized=p.pin(normalized),all_pages_actual_original_resolution_png_read=True,human_read_pending=False,
        assembly_stage_publication_owned_by_root=True,bridge_program=p.pin(__file__),unchanged_nine_handoff=p.pin(NINE))
    p.preserved(freeze);p.write_new(p.MIXED/'READY.json',ready)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('machine');sub.add_parser('finalize')
    read=sub.add_parser('record-read');read.add_argument('--reviewer',required=True);read.add_argument('--notes',required=True);read.add_argument('--evidence',action='append',required=True)
    args=parser.parse_args()
    if args.command=='machine':machine()
    elif args.command=='finalize':finalize()
    else:record_read(args.reviewer,args.notes,args.evidence)
