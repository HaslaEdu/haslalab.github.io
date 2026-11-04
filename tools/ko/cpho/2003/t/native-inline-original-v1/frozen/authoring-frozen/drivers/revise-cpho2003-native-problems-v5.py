from pathlib import Path
import json,hashlib,shutil
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=B/'authoring/native/page01-bilingual-prose.json';t=j.with_name('page01.tsv');p=B/'natural/2003/ko/page01.plan.json';history=B/'authoring/native/history-before-Newton-constant-v5';history.mkdir()
for src,name in [(j,j.name),(t,t.name),(p,'page01-ko.plan.json')]:shutil.copy2(src,history/name)
q=json.loads(j.read_text('utf8'))
for row in q['records']:
 if row['source_slot']=='1-11-1':assert row['translations']['en']=='and gravitational constant';row['translations']['en']="and Newton's constant"
j.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');t.write_text('\n'.join(r['source_slot']+'\t'+r['translations']['ko']+'\t'+r['translations']['en']for r in q['records'])+'\n','utf8')
plan=json.loads(p.read_text('utf8'));ko={r['source_slot']:r['translations']['ko']for r in q['records']};assert all(v['text']==ko[v['id']].strip()for v in plan['prose_placements']);plan['source_page_bilingual_prose_sha256']=sha(j);p.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
