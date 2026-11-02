from pathlib import Path
import json,hashlib,shutil,ast,sys,time
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025');P=B/'p6-authoring';OUT=B/'master-v1';OUT.mkdir(exist_ok=True)
D=Path('D:/CodexBuilds');C=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab');TS=B.parent/'cpho2013/TS/tools';PUB=D/'Hasla-publish-20261031/tools'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cp(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst)
def save(path,q):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
proofs=[];snapshots=[]
p1=json.loads((B/'p1-final-v1/page01.ready.json').read_text('utf8'))
snapshots.append(dict(name='page01',root=p1['authoring_snapshot'],files=p1['authoring_files']))
for r in p1['proofs']:proofs.append(dict(source_page=1,language=r['language'],pdf=r['pdf'],sha256=r['sha256'],qa=r['qa'],qa_sha256=r['qa_sha256'],ready=str(B/'p1-final-v1/page01.ready.json'),reviewed=True))
for page in [2,3,4,5]:
 ready=B/f'p2-6-authoring/ready/page{page:02}-READY.json';q=json.loads(ready.read_text('utf8'));assert q['status']=='IMMUTABLE_REVIEWED_PAGE_READY'
 root=Path(q['authoring_snapshot_root']);files={Path(r['snapshot']).relative_to(root).as_posix():r['sha256']for r in q['authoring_files']}
 if q.get('plan_snapshot'):files[Path(q['plan_snapshot']).relative_to(root).as_posix()]=sha(q['plan_snapshot'])
 snapshots.append(dict(name=f'page{page:02}',root=str(root),files=files))
 for r in q['editions']:
  review=json.loads(Path(r['visual_review']).read_text('utf8'));assert review['reviewed']and review['proof_sha256']==r['sha256']
  proofs.append(dict(source_page=page,language=r['language'],pdf=r['pdf'],sha256=r['sha256'],qa=r['qa'],qa_sha256=r['qa_sha256'],ready=str(ready),visual_review=r['visual_review'],reviewed=True))
# Freeze p6 inputs and all local code actually resolved by the two producers.
snap=OUT/'authoring-page06'
for name in ['prepare-cpho2025-p6.py','crop-cpho2025-p6.py','review-cpho2025-p6-plan.py','grid-cpho2025-p6.py','components-cpho2025-p6.py','correct-cpho2025-p6-contact.py','refine-cpho2025-p6-prose.py','refine-cpho2025-p6-prose2.py','apply-cpho2025-p6-reviewed-math-components.py','refine-cpho2025-p6-final-atoms.py','calibrate-cpho2025-p6-footer.py','finalize-cpho2025-p6-plan.py','assemble-scanned-proof-edition.py','prepare-cpho2025-assembly.py']:
 cp(D/name,snap/'authoring-tools'/name)
for p in(P/'tools').glob('*.py'):cp(p,snap/'page-tools'/p.name)
for p in(P/'plans').glob('*.json'):cp(p,snap/'plans'/p.name)
for name in ['component-bounds.json','preflight.json','page06-footer-source-calibration.json']:cp(P/name,snap/'source-review'/name)
def capture(namespace,priorities,seeds):
 todo=list(seeds);seen=set()
 while todo:
  name=todo.pop();p=next((r/(name+'.py')for r in priorities if(r/(name+'.py')).is_file()),None)
  if p is None or p in seen:continue
  seen.add(p);cp(p,snap/namespace/(name+'.py'))
  for n in ast.walk(ast.parse(p.read_text('utf8'))):
   if isinstance(n,ast.Import):todo.extend(a.name.split('.')[0]for a in n.names)
   elif isinstance(n,ast.ImportFrom)and n.module:todo.append(n.module.split('.')[0])
capture('build-engine',[P/'tools',TS,C/'tools'],['compose_pages'])
capture('audit-engine',[P/'tools',TS,C/'tools'],['qa_pages'])
files={p.relative_to(snap).as_posix():sha(p)for p in snap.rglob('*')if p.is_file()};snapshots.append(dict(name='page06',root=str(snap),files=files))
for lang in ['ko','en']:
 p=P/f'proofs/{lang}/page06.pdf';qa=p.with_suffix('.qa.json');q=json.loads(qa.read_text('utf8'));assert q['passed']and q['final_sha256']==sha(p)
 review=dict(source_page=6,language=lang,reviewed=True,proof_sha256=sha(p),source_math_atoms_reviewed=True,notes='Entire final page manually compared with source and all64 original-math crop contacts. Actual source serif point10.24 and footer8.4 kept; footer3-glyph median baseline measured; complete original k left edge corrected and rechecked. No overflow, font fitting, math resampling or changed math y.')
 save(p.with_suffix('.visual-review.json'),review)
 proofs.append(dict(source_page=6,language=lang,pdf=str(p),sha256=sha(p),qa=str(qa),qa_sha256=sha(qa),visual_review=str(p.with_suffix('.visual-review.json')),reviewed=True))
# One additional independent Korean actual-glyph visibility audit for page1.
sys.path[:0]=[str(PUB),str(TS)]
from pdf_memory_gate import page_worker
from pdf_hangul_visibility import audit
first=next(r for r in proofs if r['source_page']==1 and r['language']=='ko')
with page_worker():
 result=audit(Path(first['pdf']));assert result['flagged_components']==0;save(OUT/'page01-ko-hangul-visibility.json',result)
time.sleep(.6)
for row in proofs:
 assert sha(row['pdf'])==row['sha256']and sha(row['qa'])==row['qa_sha256']
 dest=OUT/f'proofs/{row["language"]}/page{row["source_page"]:02}.pdf';cp(row['pdf'],dest);row['pdf']=str(dest)
 for label in ['qa','visual_review','ready']:
  if label in row:
   dest=OUT/f'evidence/{row["language"]}/page{row["source_page"]:02}-{label}.json';cp(row[label],dest);row[label]=str(dest)
for snapshot in snapshots:
 for rel,digest in snapshot['files'].items():assert sha(Path(snapshot['root'])/rel)==digest
spec=dict(year=2025,kind='T',source_original_sha256='b7c3ff8e024d4805306b7cd7e11bb22dd487ff1ee1aa6a504f096a1676296957',source_audited_sha256='c9562e8f6053b454391083289b179f28ed29f7d9024723a34a2a8b0e663bd306',proofs=sorted(proofs,key=lambda r:(r['language'],r['source_page'])),authoring_snapshots=snapshots,page01_ko_hangul_qa=str(OUT/'page01-ko-hangul-visibility.json'))
save(OUT/'assembly-master-input.json',spec)
for lang in ['ko','en']:
 save(OUT/f'assembly-{lang}-input.json',dict(output=str(OUT/f'editions/CPhO_2025_T_{lang.upper()}.pdf'),proofs=[r for r in spec['proofs']if r['language']==lang]))
print(json.dumps(dict(status='ALL12_REVIEWED_PROOFS_FROZEN_READY_FOR_ASSEMBLY',proofs=[dict(page=r['source_page'],language=r['language'],sha256=r['sha256'])for r in spec['proofs']],authoring_files=sum(len(s['files'])for s in snapshots)),ensure_ascii=False),flush=True)
