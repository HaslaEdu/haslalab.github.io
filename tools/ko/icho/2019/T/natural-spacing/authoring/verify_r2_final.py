"""Final R2 verification plus exact page53 text/page45 answer-column amendments."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
B=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(B));import final_year_freeze as verifier
verifier.F=B/'final-code-freeze-r2.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_text('utf8'))
assert sha(verifier.F)=='81156ebe66c0872dd0301e5a22d0b72f8e29dd8ba56ed3eae60b87d3422ba49a'
freeze=read(verifier.F);amendment=B/'final-r2-page53-semantics-amendment.json';assert sha(amendment)=='95f51bb3527ea0f83202c4c071e01b884a09369c615b7de5cd628896b3083f39';amend=read(amendment)
assert amend['year']==2019 and amend['page']==53 and amend['base_freeze_sha256']==sha(verifier.F)and amend['source_sha256']==verifier.g.SOURCE_SHA
p=Path(amend['changed_input']).resolve();assert p==B/'page53.overrides.json'and sha(amend['before_copy'])==amend['before_sha256']
before=read(amend['before_copy']);expected=copy.deepcopy(before);approved={'p53:b3:l0:s3-3':'','p53:b3:l0:s5-5':'-이노시톨에서 유래한 우세 화합물의 분자식을. 이 시료에서','p53:b3:l1:s0-0':'관찰된 양성자 수와 일치해야 하며, 측정 자료는'}
assert amend['slot_edits']==approved
for id,text in approved.items():expected['__slot_edits__'].setdefault(id,{})['text']=text
assert read(p)==expected and sha(p)==amend['after_sha256']
pins={str(Path(e['path']).resolve()):e['sha256']for e in freeze['files']};assert pins[str(p)]==amend['before_sha256'];pins[str(p)]=amend['after_sha256']
columns_path=B/'final-r2-source-checkbox-columns-amendment.json';assert sha(columns_path)=='22eebd85186fae16a0c31ad8d3b23e8e67d5f015e2efd7eddbf730a0694faee7';columns=read(columns_path)
second_path=B/'final-r2-page51-second-answer-row-amendment.json';assert sha(second_path)=='cd50b0b21e8fba85c47bc79923453aab684d379676830d61c2ae98aa7e45a9f2';second=read(second_path)
assert columns['year']==2019 and columns['base_freeze_sha256']==sha(verifier.F)and columns['source_sha256']==verifier.g.SOURCE_SHA
assert [e['page']for e in columns['pages']]==[13,45,46,51]
baselines={13:[609.4299926757812],45:[735.219970703125,759.0960083007812],46:[83.15997314453125],51:[144.8599853515625,186.3800048828125]}
for entry in columns['pages']:
 cp=Path(entry['changed_input']).resolve();assert cp==B/f"page{entry['page']:02}.overrides.json"and sha(entry['before_copy'])==entry['before_sha256']
 ce=copy.deepcopy(read(entry['before_copy']));assert set(entry['scope_edits'])=={'fixed_prose_baselines','source_two_column_choice_review'if entry['page']==45 else'source_checkbox_columns_review'}
 assert entry['scope_edits']['fixed_prose_baselines']==baselines[entry['page']]
 assert entry['text_edits']==({'p51:b6:l0:s8-8:c0-22':'덜 안정함. 비교:','p51:b6:l0:s12-12':'착물.'}if entry['page']==51 else{})
 ce['__layout_scope__'].update(entry['scope_edits'])
 for sid,text in entry['text_edits'].items():ce['__slot_edits__'].setdefault(sid,{})['text']=text
 represented=Path(second['before_copy'])if entry['page']==51 else cp
 assert read(represented)==ce and sha(represented)==entry['after_sha256']
 assert pins[str(cp)]==entry['before_sha256'];pins[str(cp)]=entry['after_sha256']
assert second['year']==2019 and second['page']==51 and second['base_freeze_sha256']==sha(verifier.F)and second['source_sha256']==verifier.g.SOURCE_SHA
assert second['parent_checkbox_amendment_sha256']==sha(columns_path)
sp=Path(second['changed_input']).resolve();assert sp==B/'page51.overrides.json'and sha(second['before_copy'])==second['before_sha256']==pins[str(sp)]
se=copy.deepcopy(read(second['before_copy']));assert se['__layout_scope__']['fixed_prose_baselines']==[144.8599853515625,186.3800048828125]
se['__layout_scope__']['fixed_prose_baselines']=[144.8599853515625,165.6199951171875,186.3800048828125]
assert read(sp)==se and sha(sp)==second['after_sha256'];pins[str(sp)]=second['after_sha256']
steps_path=B/'final-r2-page54-starting-compound-amendment.json';assert sha(steps_path)=='fc26e9089730d02d6c03c7f052b194c6c5366548267ead8a2faba220250b8475';steps=read(steps_path)
assert steps['year']==2019 and steps['page']==54 and steps['base_freeze_sha256']==sha(verifier.F)and steps['source_sha256']==verifier.g.SOURCE_SHA
tp=Path(steps['changed_input']).resolve();assert tp==B/'page54.overrides.json'and sha(steps['before_copy'])==steps['before_sha256']==pins[str(tp)]
te=copy.deepcopy(read(steps['before_copy']));assert steps['slot_edits']=={'p54:b7:l0:s2-2':'는 화합물','p54:b7:l0:s4-4:c0-4':'에서'}
for sid,text in steps['slot_edits'].items():te['__slot_edits__'].setdefault(sid,{})['text']=text
assert read(tp)==te and sha(tp)==steps['after_sha256'];pins[str(tp)]=steps['after_sha256']
actual_changes=[dict(path=e['path'],before_sha256=e['sha256'],after_sha256=sha(e['path']))for e in freeze['files']if sha(e['path'])!=e['sha256']]
assert sorted(Path(e['path']).name for e in actual_changes)==[f'page{n:02}.overrides.json'for n in[13,45,46,51,53,54]]
assert len(freeze['files'])==197 and len(actual_changes)==6
assert sum(Path(e['path']).suffix=='.py'for e in freeze['files'])==69
def exact_inputs():
 errors=[path for path,h in pins.items()if not Path(path).is_file()or sha(path)!=h];assert not errors,dict(changed_undeclared_R2_inputs=errors)
 verifier.g.assert_protected_2024();assert sha(verifier.g.SOURCE)==verifier.g.SOURCE_SHA;return freeze
verifier.verify_inputs=exact_inputs;exact_inputs();assert verifier.verify_pages()
assert(B/'page53.diagnostic.json').stat().st_mtime>=datetime.datetime.fromisoformat(amend['created_utc'].replace('Z','+00:00')).timestamp()
for entry in columns['pages']:assert(B/f"page{entry['page']:02}.diagnostic.json").stat().st_mtime>=datetime.datetime.fromisoformat(entry['created_utc'].replace('Z','+00:00')).timestamp()
for m in[second,steps]:assert(B/f"page{m['page']:02}.diagnostic.json").stat().st_mtime>=datetime.datetime.fromisoformat(m['created_utc'].replace('Z','+00:00')).timestamp()
mode_counts={};mixed=[]
for n in range(1,61):
 q=read(verifier.g.PROOFS/f'page{n:02}.layout.json')
 assert q['vector_language_helper_sha256']==sha(B/'vector_language_icho2019.py')and q['actual_native_vector_coordinate_audit']['audit_code_sha256']==sha(B/'verify_native_vectors_icho2019.py')
 assert q['source_emphasis_meaning_review']['sha256']==sha(B/'source-emphasis-meaning-review.json')
 assert q['actual_prose_underline_coverage_and_style_audit']['measurement_code_sha256']==sha(B/'verify_prose_underline_and_style.py')
 for edit in q.get('reviewed_vector_prose_suppression_audit',[]):
  assert edit['only_reviewed_English_path_opacity_or_exact_clip_and_caption_x_translations_added']is True and edit['changed_pixels_outside_reviewed_label_scopes']==0
  for path in edit['paths']:
   mode=path['suppression_mode'];mode_counts[mode]=mode_counts.get(mode,0)+1
   if mode=='mixed-path-exact-English-clip':mixed.append(dict(page=n,id=path['id'],source_path=path['source_path'],reviewed_English_area_rect=path['reviewed_English_area_rect']))
assert mode_counts=={'pure-English-path-zero-opacity':76,'native-prefix-x-translation-only':10,'outside-English-scope-x-translation-only':5,'mixed-path-exact-English-clip':5}
report_path=B/'final-60-page-proof-verification.json';report=read(report_path);report.update(approved_page53_amendment_path=str(amendment),approved_page53_amendment_sha256=sha(amendment),source_checkbox_columns_amendment_path=str(columns_path),source_checkbox_columns_amendment_sha256=sha(columns_path),page51_second_answer_row_amendment_sha256=sha(second_path),page54_starting_compound_amendment_sha256=sha(steps_path),actual_changed_R2_inputs=actual_changes,other_R2_frozen_inputs_unchanged=191,all69_frozen_Python_programs_unchanged=True,final_revision_verifier_sha256=sha(__file__),outlined_path_mode_counts=mode_counts,exact_mixed_paths=mixed)
verifier.write(report_path,report);print(json.dumps(dict(passed=True,pages=60,proof_verification_sha256=sha(report_path),mode_counts=mode_counts)))
