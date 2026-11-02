from pathlib import Path
from collections import defaultdict
import sys,json,hashlib,subprocess,time

B=Path('D:/CodexBuilds/Hasla-original-style-20261031/heading-alignment-v1')
P=Path('D:/CodexBuilds/Hasla-publish-20261031')
load=lambda p:json.loads(Path(p).read_text('utf8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
groups=defaultdict(list)
for r in load(B.parent/'published-izho-heading-detail-20261102.json')['candidates_requiring_review']:
 if abs(r['actual_center_error'])>.001:groups[r['file']].append(r)
producer=sha('D:/CodexBuilds/review-izho-heading-alignment.py')
accepted_producers={producer}|{sha(p)for p in (B/'producer-versions').glob('*.py')if p.stem==sha(p)}
for filename,rows in sorted(groups.items()):
 item=next(r for r in load(P/'tools/original_style_publication.json')if r['file']==filename)
 folder=B/filename.removesuffix('.pdf');affected={r['published_page']for r in rows}
 deadline=time.monotonic()+1800
 while True:
  okay=True
  for n in affected:
   report=folder/f'page{n:02}.alignment.json'
   if not report.exists():okay=False;break
   q=load(report)
   if not q['passed']or q['producer_sha256']not in accepted_producers:okay=False;break
  if okay:break
  if time.monotonic()>deadline:raise TimeoutError(filename)
  time.sleep(5)
 proofs=[]
 for n in range(1,item['pages']+1):
  changed=n in affected;file=folder/f'page{n:02}.pdf'if changed else Path(item['generated_file'])
  digest=sha(file);assert digest==(load(folder/f'page{n:02}.alignment.json')['proof_sha256']if changed else item['sha256'])
  proofs.append(dict(pdf=str(file),sha256=digest,source_page=n,proof_index=1 if changed else n))
 spec=dict(output=str(B/'editions'/filename),baseline_item=item,proofs=proofs,affected_pages=sorted(affected));specfile=folder/'assembly-spec.json';specfile.write_text(json.dumps(spec,indent=2)+'\n','utf8')
 with(folder/'assembly.log').open('w',encoding='utf8')as log:
  subprocess.run([sys.executable,'-X','utf8','D:/CodexBuilds/assemble-heading-alignment-edition.py',str(specfile)],check=True,stdout=log,stderr=subprocess.STDOUT,cwd=P)
 print('ASSEMBLED',filename,item['pages'],flush=True)
print('ALL15_ASSEMBLED',flush=True)
