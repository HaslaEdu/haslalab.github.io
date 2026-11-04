from pathlib import Path
import json,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native').resolve();history=B/'proof-history/page01-before-explicit-component-definitions-v6';assert not history.exists();history.mkdir(parents=True)
paths=[]
for lang in ['ko','en']:
 paths+=list((B/f'natural/2003/{lang}').glob('page01*'))+list((B/f'native-baseline/{lang}').glob('page01*'))+[B/f'initial-fixed-slot-staging/{lang}/page01',B/f'evidence/actual-style/{lang}-page01.json',B/f'evidence/source-native-ink/{lang}-page01.json']
paths += [B/'authoring/native/page01-bilingual-prose.json',B/'authoring/native/page01.tsv',B/'evidence/native-visual-review/ko-page01.json']
for p in paths:
 p=p.resolve();out=(history/p.relative_to(B)).resolve();assert p.is_relative_to(B)and out.is_relative_to(history)and p.exists()and not out.exists();out.parent.mkdir(parents=True,exist_ok=True);p.rename(out)
j=B/'authoring/native/page01-bilingual-prose.json';q=json.loads((history/j.relative_to(B)).read_text('utf8'))
for row in q['records']:
 if row['source_slot']=='1-3-2':row['translations']['en']='at rest in a hemispherical bowl of radius'
 if row['source_slot']=='1-15-0':row['translations']=dict(ko='각각 저항과 인덕턴스다. 휠과 축의 저항 및 회전 마찰은 무시한다.',en='These are resistance and inductance; ignore metal flywheel/axle resistance and friction.')
j.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');j.with_name('page01.tsv').write_text('\n'.join(r['source_slot']+'\t'+r['translations']['ko']+'\t'+r['translations']['en']for r in q['records'])+'\n','utf8')
