"""Seal verified inputs/proofs/evidence, preserving every prior reviewed version."""
from pathlib import Path
import sys,json,hashlib,os,shutil
B=Path(__file__).resolve().parents[1];sys.path.insert(0,str(B/'engine'))
from cpho2008_atomic_authoring import atomic_text
S='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d';G='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
    return h.hexdigest()
read=lambda p:json.loads(Path(p).read_text('utf8'))
assert sha(B/'source/CPhO_2008_original_combined_ZH.pdf')==S and sha(B/'engine/pdf_native_inline_reposition.py')==G
append=read(B/'editions/all4-native-append-render-checks.json');assert append['passed']and len(append['editions'])==4
visual=read(B/'inspection/current-full-page-visual-review.json');assert visual['all42_current_pages_approved']and len(visual['pages'])==42
contracts=B/'publication-contracts';test=read(contracts/'actual-source-native-contract-verification.json');assert test['all_passed']and all(r['passed']for r in test['tests']);assert test['contract_sha256']==sha(contracts/'source-bound-native-bilingual-design-contract.json')
negative=read(B/'actual-negative-PDF-controls/all7-actual-source-native-design-negatives.json');assert negative['passed']and len(negative['actual_unique_bad_PDFs'])==7
contract=read(contracts/'source-bound-native-bilingual-design-contract.json')
for r in contract['artifacts']:assert sha(r['source_path'])==r['sha256']and Path(r['source_path']).stat().st_size==r['bytes'],r['id']
engine={str(p.relative_to(B)):dict(sha256=sha(p),bytes=p.stat().st_size)for p in sorted((B/'engine').glob('*.py'))}
ready=dict(kind='cpho2008-complete-original-native-bilingual-private-ready-v1',original_source_sha256=S,unchanged_original_native_guard_sha256=G,classification=contract['classification'],editions=contract['editions'],all21_original_source_pages_full_visual_read=True,all42_current_native_CID_font_point_math_clip_graphics_prose_and_collision_checks_passed=True,all42_current_full_source_proof_visuals_approved=True,visual_review_sha256=sha(B/'inspection/current-full-page-visual-review.json'),seven_unique_actual_bad_PDFs_rejected=[dict(kind=r['kind'],sha256=r['actual_bad_PDF_sha256'])for r in negative['actual_unique_bad_PDFs']],source_bound_public_contract_sha256=sha(contracts/'source-bound-native-bilingual-design-contract.json'),source_bound_public_contract_actual_artifacts=len(contract['artifacts']),actual_artifact_resolver_and_rebased_mutation_tests=len(test['tests']),contract_verification_sha256=sha(contracts/'actual-source-native-contract-verification.json'),frozen_private_engine_import_closure=engine,private_only_no_publication_or_Git_performed=True,ready=True)
ready_path=B/'READY.json';assert not ready_path.exists();atomic_text(ready_path,json.dumps(ready,ensure_ascii=False,indent=2)+'\n')
# Select first, so the capture cannot recursively include itself. All original
# and rejected history, source inputs, producing plans and active controls stay.
snapshot=B/'frozen-complete-native-bilingual-authoring';assert not snapshot.exists()
files=sorted(p for p in B.rglob('*')if p.is_file()and not p.is_relative_to(snapshot))
records=[];binary={'.pdf','.png','.jpg','.jpeg','.ttf','.otf','.ttc','.bin','.svg'}
snapshot.mkdir()
for source in files:
    rel=source.relative_to(B);target=snapshot/rel;assert target.resolve().is_relative_to(snapshot.resolve());target.parent.mkdir(parents=True,exist_ok=True);digest=sha(source)
    if source.suffix.lower()in binary:
        os.link(source,target);storage='byte-identical-finalized-binary-hardlink'
    else:shutil.copy2(source,target);storage='verified-byte-copy'
    assert sha(target)==digest and sha(source)==digest
    records.append(dict(source_relative_path=rel.as_posix(),path=str(target),sha256=digest,bytes=target.stat().st_size,storage=storage))
manifest=dict(kind='cpho2008-complete-original-native-bilingual-frozen-input-proof-evidence-v1',original_source_sha256=S,READY_sha256=sha(ready_path),files=records,file_count=len(records),logical_bytes=sum(r['bytes']for r in records),all_inputs_proofs_original_and_rejected_history_preserved=True,binary_hardlinks_are_sealed_do_not_edit_in_place=True)
manifest_path=snapshot/'FROZEN-manifest.json';atomic_text(manifest_path,json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
handoff=dict(READY_path=str(snapshot/'READY.json'),READY_sha256=sha(snapshot/'READY.json'),frozen_manifest_path=str(manifest_path),frozen_manifest_sha256=sha(manifest_path),files=len(records),logical_bytes=manifest['logical_bytes'],editions=contract['editions'],source_bound_public_contract_path=str(snapshot/'publication-contracts/source-bound-native-bilingual-design-contract.json'),source_bound_public_contract_sha256=sha(snapshot/'publication-contracts/source-bound-native-bilingual-design-contract.json'),no_Git_upload_or_public_index_changes=True)
atomic_text(B/'FINAL-private-handoff.json',json.dumps(handoff,ensure_ascii=False,indent=2)+'\n');print('C08_COMPLETE_FROZEN_READY',json.dumps(handoff,ensure_ascii=False))
