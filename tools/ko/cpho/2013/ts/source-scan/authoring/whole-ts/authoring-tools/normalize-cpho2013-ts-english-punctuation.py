from pathlib import Path
import json,hashlib,re,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
out=B/'english-punctuation-revision';out.mkdir(exist_ok=True)
records=[]
def normalize(text):
 parts=re.split(r'(\[\[[^\]]+\]\])',text)
 return ''.join(p if p.startswith('[[') else p.translate(str.maketrans({'’':"'",'‘':"'",'–':'-','—':'-','“':'"','”':'"'})) for p in parts)
for n in range(4,15):
 p=B/f'authoring/page{n:02}-layout.json';q=json.loads(p.read_text('utf8'));old=sha(p);changed=[]
 for row in q['rows']:
  before=row['en'];after=normalize(before)
  if before!=after:changed.append(dict(row=row['id'],before=before,after=after));row['en']=after
 if changed:
  backup=out/p.name
  if not backup.exists():shutil.copy2(p,backup)
  p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
 records.append(dict(source_page=n,path=str(p),before_sha256=old,after_sha256=sha(p),changes=changed,original_math_atoms_modified=False,point_sizes_modified=False,baselines_modified=False))
 p=B/f'authoring/page{n:02}.json';q=json.loads(p.read_text('utf8'));old=sha(p);changed=[]
 for row in q['native_headers']:
  before=row['translations']['en'];after=normalize(before)
  if before!=after:changed.append(dict(source_slot=row['source_slot'],before=before,after=after));row['translations']['en']=after
 if changed:
  backup=out/p.name
  if not backup.exists():shutil.copy2(p,backup)
  p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
 records.append(dict(source_page=n,path=str(p),before_sha256=old,after_sha256=sha(p),changes=changed))
(out/'revision.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n','utf8')
print('Updated authored English punctuation only:',sum(len(r['changes'])for r in records),'strings')
source=Path('D:/CodexBuilds/rebuild-and-final-audit-cpho2013-ts.py').read_text('utf8')
source=source.replace("results=[]", "results=json.loads((out/'whole-edition-results.json').read_text('utf8'))")
source=source.replace("for language in ['ko','en']:","for language in ['en']:\n  results=[r for r in results if (r['source_page'],r['language'])!=(n,language)]")
source=source.replace("if (n,language) in REBUILD:compose.build(n,language)","compose.build(n,language)")
Path('D:/CodexBuilds/rebuild-cpho2013-ts-english-punctuation.py').write_text(source,'utf8')
