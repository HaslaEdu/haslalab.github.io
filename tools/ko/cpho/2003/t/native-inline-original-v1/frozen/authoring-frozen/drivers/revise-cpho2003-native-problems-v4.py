from pathlib import Path
import json,shutil,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
updates={'1-3-3':'.','1-11-0':'launch energy, given Earth mass','1-11-1':'and gravitational constant','1-11-2':'. Ignore other celestial bodies.','1-15-0':'Ignore metal flywheel/axle resistance and rotational friction.','1-28-1':'axis the uniform field is','1-28-3':'axis it is'}
history=B/'authoring/native/history-before-full-source-v4';assert not history.exists();history.mkdir()
j=B/'authoring/native/page01-bilingual-prose.json';t=j.with_name('page01.tsv');shutil.copy2(j,history/j.name);shutil.copy2(t,history/t.name);q=json.loads(j.read_text('utf8'));old_ko={r['source_slot']:r['translations']['ko']for r in q['records']}
for r in q['records']:
 if r['source_slot']in updates:r['translations']['en']=updates.pop(r['source_slot'])
assert not updates
j.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');t.write_text('\n'.join(r['source_slot']+'\t'+r['translations']['ko']+'\t'+r['translations']['en']for r in q['records'])+'\n','utf8')
# The Korean PDF and all Korean placements are unchanged. Refresh only its
# bilingual source-file provenance after verifying every Korean source slot.
plan=B/'natural/2003/ko/page01.plan.json';previous=sha(plan);shutil.copy2(plan,history/'page01-ko.plan.json');p=json.loads(plan.read_text('utf8'))
assert all(v['text']==old_ko[v['id']].strip()for v in p['prose_placements'])
p['source_page_bilingual_prose_sha256']=sha(j);plan.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8')
report=dict(passed=True,Korean_pdf_unmodified=True,Korean_all_authored_slot_texts_unchanged=True,Korean_plan_old_sha256=previous,Korean_plan_new_sha256=sha(plan),bilingual_source_sha256=sha(j),Korean_proof_sha256=sha(B/'natural/2003/ko/page01.pdf'),reason='English-only full-source review restores the explicit name of G, flywheel terminology, y-axis wording and the first sentence period. Korean source slots/point/paint/positions and PDF bytes are unchanged; only the bilingual-file provenance hash is refreshed.')
(B/'evidence/native-visual-review/ko-page01-bilingual-provenance-refresh.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
