from pathlib import Path
import json,hashlib,shutil,datetime,sys,subprocess
B=Path(__file__).resolve().parents[1];O=B/'publication-contracts';F=B/'natural/2019/TS';E=B/'engine';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'));save=lambda p,x:Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
Q=B/'natural/editions/IZhO_2019_TS_KO.ready.json';q=load(Q);out=Path(q['authoring_snapshot']);before=sha(Q);history=B/'natural/ready-history'/before;history.mkdir(parents=True,exist_ok=True);shutil.copy2(Q,history/Q.name);assert sha(q['output'])==q['sha256']=='c7d834f413742293bcbd0a2fbf57ee17fc06f4fcd1566b507def840b470edeb5'
checks=load(O/'actual-artifact-contract-verification.json');assert checks['passed']and checks['actual_artifacts_checked']==71 and checks['total_positive_and_mutation_checks']==56 and not checks['copied_standalone_test_fixture_used'];bundle=load(O/'source-bound-native-contract.json')
def copy(src,relative):
 src=Path(src);dst=out/relative;dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists()or dst.read_bytes()!=src.read_bytes():shutil.copy2(src,dst)
 assert sha(src)==sha(dst);return dst
for p in E.glob('*.py'):copy(p,Path('tools')/p.name)
for p in(E/'history').rglob('*.py'):copy(p,Path('engine-history')/p.relative_to(E/'history'))
for n in range(1,13):copy(F/f'page{n:02}.old-source.pdf',Path('exact-reviewed-proofs')/f'page{n:02}.old-source.pdf')
copy(F/'page06.audit.json','exact-reviewed-proofs/page06.audit.json')
runtime=load(out/'runtime-import-resolution.json')
for name,row in runtime.items():
 p=Path(row['resolved_path']);assert p.is_file();row['sha256']=sha(p);copy(p,row['frozen_path'])
save(out/'runtime-import-resolution.json',runtime)
for row in q['audit_reports']:
 p=Path(row['path']);a=load(p);assert a['passed']and a['output_sha256']==q['exact_reviewed_page_inputs'][row['page']-1]['proof_sha256'];row['sha256']=sha(p)
q['page_audits'][5]['native_ink_reference_profile']=load(F/'page06.audit.json')['native_ink_reference_profile']
indexed={}
for p in out.rglob('*'):
 if p.is_file():indexed.setdefault(sha(p),p.relative_to(out).as_posix())
mapping={}
for a in bundle['artifacts']:
 src=Path(a['source_path']);assert sha(src)==a['sha256']and src.stat().st_size==a['bytes'];relative=indexed.get(a['sha256'])
 if relative is None:
  relative=(Path('publication-artifact-files')/a['sha256']/src.name).as_posix();copy(src,relative);indexed[a['sha256']]=relative
 assert sha(out/relative)==a['sha256'];mapping[a['id']]=dict(path=relative,sha256=a['sha256'],bytes=a['bytes'],role=a['role'])
save(O/'actual-frozen-artifact-map.json',mapping)
save(O/'contract-provenance.json',dict(original_source_sha256=q['original_source_sha256'],full_pdf_sha256=q['sha256'],source_contract_sha256=sha(O/'source-bound-native-contract.json'),helper_sha256=sha(O/'izho-2019-native-source-programs.cjs'),source_pins_sha256=sha(O/'izho-2019-native-source-pins.cjs'),mutation_cases_sha256=sha(O/'izho-2019-native-source-mutations.cjs'),actual_artifacts_pinned=71,actual_current_artifact_positive_and_adversarial_checks=56,original_full_raw_control_native_control_reviewed_proof_reference_program_and_negative_PDF_hashes_bound=True,rebased_GID_point_clip_dx_program_shape_or_missing_head_rejected=True,no_standalone_copied_fixture_public_tests=True,parent_binds_real_public_ledger_and_public_tests=True,original_shared_guard_unchanged=True,new_contracts_generated_on_C_only=True))
for p in O.iterdir():
 if p.is_file():copy(p,Path('publication-contracts')/p.name)
policy=load(out/'font-and-design-policy.json');policy.update(source_bound_publication_contract='publication-contracts/izho-2019-native-source-programs.cjs',source_bound_native_evidence='publication-contracts/source-bound-native-contract.json',source_bound_actual_artifact_map='publication-contracts/actual-frozen-artifact-map.json',actual_artifact_contract_checks=56,all71_original_full_control_proof_reference_program_negative_and_engine_files_pinned=True,actual_public_ledger_binding_owned_by_parent=True);save(out/'font-and-design-policy.json',policy)
q.update(source_bound_publication_contract='publication-contracts/izho-2019-native-source-programs.cjs',source_bound_native_evidence='publication-contracts/source-bound-native-contract.json',source_bound_actual_artifact_map='publication-contracts/actual-frozen-artifact-map.json',publication_contract_actual_artifacts_pinned=71,publication_contract_positive_and_adversarial_checks=56,public_actual_ledger_binding_owned_by_parent=True,publication_contract_no_copied_standalone_fixture_tests=True)
q['authoring_files']={p.relative_to(out).as_posix():sha(p)for p in sorted(out.rglob('*'))if p.is_file()};save(Q,q)
handoff=load(B/'natural/2019-private-ready-handoff.json');handoff.update(status='PRIVATE_READY_FROZEN_SOURCE_CONTRACTS_COMPLETE_FOR_PARENT_REVIEW',ready_sha256=sha(Q),authoring_files=len(q['authoring_files']),authoring_bytes=sum(p.stat().st_size for p in out.rglob('*')if p.is_file()),publication_contract=str(out/'publication-contracts/izho-2019-native-source-programs.cjs'),source_bound_native_evidence=str(out/'publication-contracts/source-bound-native-contract.json'),actual_frozen_artifact_map=str(out/'publication-contracts/actual-frozen-artifact-map.json'),publication_contract_checks_passed=56,actual_artifacts_bound=71,no_copied_standalone_public_fixture_tests=True,parent_owns_public_actual_ledger_binding=True,final_source_contract_sealed_utc=datetime.datetime.now(datetime.UTC).isoformat());save(B/'natural/2019-private-ready-handoff.json',handoff)
print('SOURCE2019_READY_RESEALED_WITH_FULL_SOURCE_BOUND_CONTRACTS',json.dumps(handoff),flush=True)
