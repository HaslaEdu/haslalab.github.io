from pathlib import Path
import json,hashlib,shutil,ast
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS');D=Path('D:/CodexBuilds');OUT=B/'master-v1';OUT.mkdir(exist_ok=True)
PUB=D/'Hasla-publish-20261031';OTHER=B.parents[1]/'cpho2025/p2-6-authoring/tools'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
def cp(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst)
records=json.loads((B/'final-qa/whole-edition-results.json').read_text('utf8'))
assert len(records)==22 and {(r['source_page'],r['language'])for r in records}=={(n,l)for n in range(4,15)for l in ['ko','en']}
proofs=[]
for r in records:
 assert r['passed'] and sha(r['proof'])==r['proof_sha256']
 for key in ['source_qa','generic_qa','math_union','actual_CID_widths']:
  assert sha(r[key])==r[key+'_sha256'];assert json.loads(Path(r[key]).read_text('utf8'))['passed']
 stem=Path(r['proof']);composition=stem.with_suffix('.composition.json');q=json.loads(composition.read_text('utf8'))
 assert q['output_sha256']==r['proof_sha256'] and q['inline_math_replay']['stage']=='original-math replay before new prose'
 scan=json.loads(Path(r['generic_qa']).read_text('utf8'));ordinary=json.loads(Path(r['source_qa']).read_text('utf8'))
 assert scan['final_sha256']==ordinary['proof_sha256']==r['proof_sha256']
 dest=OUT/f"proofs/{r['language']}/page{r['source_page']:02}.pdf";cp(r['proof'],dest)
 row=dict(source_page=r['source_page'],language=r['language'],pdf=str(dest),sha256=r['proof_sha256'],evidence={})
 for key in ['source_qa','generic_qa','math_union','actual_CID_widths']:
  dest=OUT/f"evidence/{r['language']}/page{r['source_page']:02}-{key}.json";cp(r[key],dest);row['evidence'][key]=str(dest)
 for suffix in ['.composition.json']:
  dest=OUT/f"evidence/{r['language']}/page{r['source_page']:02}{suffix}";cp(stem.with_suffix(suffix),dest)
 proofs.append(row)
snap=OUT/'authoring-whole-ts'
for folder in ['authoring','background-evidence','residual-contact-review','math-union-contact-review','source-atom-final-review','font-calibration','english-punctuation-revision']:
 for p in (B/folder).rglob('*'):
  if p.is_file() and p.suffix in ['.json','.py','.png','.log','.txt']:cp(p,snap/folder/p.relative_to(B/folder))
for p in(B/'fonts-source').glob('*.json'):cp(p,snap/'font-provenance'/p.name)
for name in ['fonts-provenance.json']:
 p=B.parents[1]/'official-hans-fonts'/name
 if p.exists():cp(p,snap/'font-provenance'/name)
for p in(B/'tools').glob('*.py'):cp(p,snap/'page-tools'/p.name)
for name in ['rebuild-and-final-audit-cpho2013-ts.py','rebuild-cpho2013-ts-page10-only.py','refine-cpho2013-ts-math-padding.py','refine-cpho2013-ts-residuals.py','review-cpho2013-source-atoms.py','final-audit-cpho2013-ts.py','complete-cpho2013-ts-paint-order.py','correct-cpho2013-ts-final-pages.py','finish-cpho2013-ts-final-pages.py','normalize-cpho2013-ts-english-punctuation.py','rebuild-cpho2013-ts-english-punctuation.py','prepare-cpho2013-ts-assembly.py','finalize-cpho2013-ts-ready.py','assemble-scanned-proof-edition.py']:
 cp(D/name,snap/'authoring-tools'/name)
priorities=[B/'tools',PUB/'tools',OTHER]
todo=['cpho_2013_ts_compose','cpho_2013_ts_qa','cpho_2013_ts_generic_qa_adapter','qa_pages','pdf_memory_gate'];seen=set()
while todo:
 name=todo.pop();p=next((root/(name+'.py')for root in priorities if(root/(name+'.py')).is_file()),None)
 if p is None or p in seen:continue
 seen.add(p);cp(p,snap/'resolved-engine'/(name+'.py'))
 for n in ast.walk(ast.parse(p.read_text('utf8'))):
  if isinstance(n,ast.Import):todo.extend(a.name.split('.')[0]for a in n.names)
  elif isinstance(n,ast.ImportFrom)and n.module:todo.append(n.module.split('.')[0])
cp(PUB/'tools/ko/cpho/2013/original/native-slots.json',snap/'tools/ko/cpho/2013/original/native-slots.json')
snapshot=dict(name='whole-ts',root=str(snap),files={p.relative_to(snap).as_posix():sha(p)for p in snap.rglob('*')if p.is_file()})
q=dict(year=2013,kind='TS',source_original_sha256='612d676f525ddc35ad3b417a8f25141d3467f48309d52dfdbcab7bd222201d68',source_audited_sha256='612d676f525ddc35ad3b417a8f25141d3467f48309d52dfdbcab7bd222201d68',proofs=sorted(proofs,key=lambda r:(r['language'],r['source_page'])),authoring_snapshots=[snapshot])
save(OUT/'assembly-master-input.json',q)
for lang in ['ko','en']:save(OUT/f'assembly-{lang}-input.json',dict(output=str(OUT/f'editions/CPhO_2013_TS_{lang.upper()}.pdf'),proofs=[r for r in q['proofs']if r['language']==lang]))
print('FROZEN',len(proofs),'proofs;',len(snapshot['files']),'authoring/evidence files',flush=True)
