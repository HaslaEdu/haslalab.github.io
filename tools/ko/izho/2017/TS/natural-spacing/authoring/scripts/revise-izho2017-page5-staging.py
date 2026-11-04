"""Fix an off-page staging-only clause without changing six audited inputs."""
from pathlib import Path
import json,shutil,hashlib,sys,pikepdf
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text('utf8'))
plans=B/'natural/2017/T/plans';history=B/'2017/translation-row-revision-3';history.mkdir(exist_ok=True)
if sys.argv[1]=='prepare':
 old=load(plans/'page05.json');source=Path(old['source_base']);digest=old['source_base_sha256'];assert sha(source)==digest
 archive=B/'natural/input-bases'/digest/source.name;archive.parent.mkdir(parents=True,exist_ok=True)
 if not archive.exists():shutil.copyfile(source,archive)
 assert sha(archive)==digest
 for pp in plans.glob('page*.json'):
  p=load(pp)
  if p['source_base_sha256']==digest:p['source_base']=str(archive);pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8')
 path=B/'2017/original_style/page5.json';q=load(path);backup=history/path.name
 if not backup.exists():shutil.copyfile(path,backup)
 changes={(10,0,2):'다음 계수의 수치값을 구하라: ',(10,4,0):', 단, '};revisions=[]
 for at,text in changes.items():
  slot=next(s for s in q['slots']if tuple(s['at'])==at);revisions.append(dict(at=at,before=slot['text'],after=text));slot['text']=text
 path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
 (history/'history.json').write_text(json.dumps(dict(old_baseline_sha256=digest,old_baseline_archive=str(archive),revisions=revisions,reason='Complete numerical-value instruction moved into its two original prose slots at unchanged original font size/baseline; no source math changed. The final clause in the old staging PDF extended beyond the page boundary.'),ensure_ascii=False,indent=2)+'\n','utf8')
elif sys.argv[1]=='join':
 out=history/'IZhO_2017_T_KO_native-baseline.pdf'
 with pikepdf.Pdf.new()as joined:
  for n in range(1,8):
   with pikepdf.open(B/f'2017/native-baseline/page{n:02}.pdf')as doc:joined.pages.append(doc.pages[0])
  joined.save(out,compress_streams=False)
 digest=sha(out);archive=B/'natural/input-bases'/digest/out.name;archive.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(out,archive)
 p=load(plans/'page05.json');p.update(source_base=str(archive),source_base_sha256=digest,prose_placements=load(B/'2017/native-baseline/page05.qa.json')['placements'])
 (plans/'page05.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8');print('NEW_PAGE5_INPUT',digest)
else:raise ValueError(sys.argv[1])
