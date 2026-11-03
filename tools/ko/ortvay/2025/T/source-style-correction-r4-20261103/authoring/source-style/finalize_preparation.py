"""Rebind root-read identical PNGs; activate root's conditional final48 GO."""
from pathlib import Path
import datetime,json,sys
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'common'))
import r4_guard as g
def main():
    freeze_path=ROOT/'PROTOTYPE-RUNTIME-FROZEN.json';freeze=json.loads(freeze_path.read_text('utf8'))
    for name,digest in freeze['runtime_sha256'].items():assert g.sha(name)==digest
    results_path=ROOT/'FIVE-FROZEN-PROTOTYPE-RESULTS.json';results=json.loads(results_path.read_text('utf8'))
    assert results['status']=='FIVE_SAME_FROZEN_RUNTIME_STRICT_REPRESENTATIVES_PASS'
    assert results['runtime_freeze']['sha256']==g.sha(freeze_path)
    negative=json.loads(Path(results['negative_controls']['path']).read_text('utf8'))
    assert negative['passed'] and negative['negative_controls']>=15 and g.sha(results['negative_controls']['path'])==results['negative_controls']['sha256']
    auth_path=ROOT/'FINAL48-CONDITIONAL-AUTHORIZATION.json';auth=json.loads(auth_path.read_text('utf8'))
    assert auth['status']=='ROOT_CONDITIONAL_GO_FINAL48_AFTER_FROZEN_FIVE_AND_NEGATIVES_AND_PROTECTION'
    assert auth['expected_input_ledger_sha256']==g.sha(ROOT/'input-ledger.json')
    reviews={};review_files=[]
    for name,key in [('ROOT-THREE-PROTOTYPE-REVIEW.json','root_three_prototype_review_sha256'),('ROOT-2026-TWO-PROTOTYPE-REVIEW.json','root_2026_two_prototype_review_sha256')]:
        p=ROOT/'experiments'/name;assert g.sha(p)==auth[key];value=json.loads(p.read_text('utf8'));assert value['passed']
        review_files.append(dict(path=str(p),sha256=g.sha(p)))
        for row in value['pages']:reviews[(row['year'],row['page'])]=(row,p)
    bindings=[]
    for row in results['page_results']:
        assert (row['year'],row['page']) in g.FIVE
        for key in ('proof','layout','png','effective_plan','independent_audit'):assert g.sha(row[key]['path'])==row[key]['sha256']
        audit=json.loads(Path(row['independent_audit']['path']).read_text('utf8'))
        assert audit['passed'] and audit['proof_sha256']==row['proof']['sha256']
        assert audit['actual_outline_and_encoded_W_audit_pending'] is False
        assert audit['actual_outline_and_encoded_W_audit']['passed'] and audit['actual_stream_interrow_ink']['passed']
        assert all(v['passed'] and v['changed_pixels_outside_explicit_glyph_union']==0 for v in audit['direct_reference_comparisons'])
        previous,review_path=reviews[(row['year'],row['page'])]
        assert previous['passed'] and row['png']['sha256']==previous['png_sha256'],'Final representative PNG differs from the one root actually read'
        bindings.append(dict(year=row['year'],page=row['page'],root_actual_read_record_path=str(review_path),root_record_sha256=g.sha(review_path),
            previously_read_png_sha256=previous['png_sha256'],final_png=row['png'],new_actual_proof=row['proof'],new_layout=row['layout'],new_independent_audit=row['independent_audit'],
            actual_PNG_bytes_identical=True,no_claim_that_new_PDF_or_layout_SHA_was_previously_read=True))
    assert {(v['year'],v['page']) for v in bindings}==g.FIVE
    protection=g.assert_all_inputs()
    output=ROOT/'PREPARATION-FROZEN.json';assert not output.exists()
    value=dict(schema='ortvay-r4-frozen-source-style-correction-preparation-v1',
        status='FROZEN_FIVE_ACTUAL_PROTOTYPES_NEGATIVES_AND_ROOT_IDENTICAL_PNG_BINDINGS_PASS',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),input_ledger_sha256=g.sha(ROOT/'input-ledger.json'),
        runtime_sha256=freeze['runtime_sha256'],runtime_code_sha256=freeze['runtime_code_sha256'],runtime_input_sha256=freeze['runtime_input_sha256'],
        runtime_freeze=dict(path=str(freeze_path),sha256=g.sha(freeze_path)),five_results=dict(path=str(results_path),sha256=g.sha(results_path)),
        page_results=results['page_results'],negative_controls=results['negative_controls'],root_visual_rebindings=bindings,
        root_conditional_authorization=dict(path=str(auth_path),sha256=g.sha(auth_path)),protection_rehashed=protection,
        correction_scope='Original2023titles retained; source4titlecenters2024/25/26; approved2025p1KOrow+.75pt with source-bound corrected italic; all45 source-bound new-prose physical shears; only new2026Batang exact master W and precise glyph-origin Tm; only2026p1declared KOrow-.5625pt for pre-existing low-resolution AA contact. Native source glyph/font/math/image programs, source sizes/baselines/row heights/words/ordinary spaces unchanged.',
        root_expected_assembler_sha256='098286bc8fa1a3ac5805006b95484c5dd279a6fac4e1fc5c109e86e7f976954f',
        full48_output_and_human_read_still_required=True)
    output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')
    token=ROOT/'FINAL48-GO.json';assert not token.exists()
    token.write_text(json.dumps(dict(status='ROOT_GO_FINAL48_SOURCE_STYLE_CORRECTION',input_ledger_sha256=g.sha(ROOT/'input-ledger.json'),
        preparation_sha256=g.sha(output),conditional_root_authorization_path=str(auth_path),conditional_root_authorization_sha256=g.sha(auth_path),
        conditions_fully_verified=True,root_did_not_require_another_confirmation=True),ensure_ascii=False,indent=2)+'\n','utf8')
    g.assert_runtime_frozen();g.assert_all_inputs()
    print(json.dumps(dict(path=str(output),sha256=g.sha(output),final48_GO_sha256=g.sha(token),conditions_verified=True)),flush=True)
if __name__=='__main__':main()
