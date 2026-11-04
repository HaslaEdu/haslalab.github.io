from pathlib import Path
import json,shutil
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native')
updates={'1-13-0':'The shown wheel has','1-15-0':'Ignore metal wheel/axle resistance and rotational friction.','1-26-0':'All links correct: full credit. Fewer correct links: partial credit. Any wrong link: zero.','2-5-0':'the field is vacuum; ignore gravity and interaction between','2-24-1':'. In the equatorial annulus to over','2-26-1':'. In the uniform equatorial field, orbit radius is'}
history=B/'authoring/native/history-before-concise-v3';assert not history.exists();history.mkdir()
for n in [1,2,3]:
 j=B/f'authoring/native/page{n:02}-bilingual-prose.json';t=j.with_name(f'page{n:02}.tsv');shutil.copy2(j,history/j.name);shutil.copy2(t,history/t.name);q=json.loads(j.read_text('utf8'))
 for r in q['records']:
  if r['source_slot']in updates:r['translations']['en']=updates.pop(r['source_slot'])
 j.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');t.write_text('\n'.join(r['source_slot']+'\t'+r['translations']['ko']+'\t'+r['translations']['en']for r in q['records'])+'\n','utf8')
assert not updates
