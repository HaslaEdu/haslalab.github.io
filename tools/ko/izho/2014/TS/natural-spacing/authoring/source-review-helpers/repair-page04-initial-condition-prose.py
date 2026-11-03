from pathlib import Path
import json,hashlib,shutil,subprocess,sys,os
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/izho2014-complete-solutions';F=B/'natural/2014/TS';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();n=4
progress=json.loads((B/'natural/2014-private-page-progress.json').read_text('utf8'));assert any(r['page']==n for r in progress),'Initial root page4 process must have finished'
path=B/'2014/original_style/page4.json';d=json.loads(path.read_text('utf8'));saved=B/'2014/original_style/history'/('page4-before-child-prose-order-'+sha(path)[:16]);saved.mkdir(parents=True,exist_ok=True);shutil.copy2(path,saved/path.name)
changes={'따라서 초기 조건을 적용하여 식 ':'따라서 식 ','을 풀면 ':'에 초기 조건 ','일 때 ':' ('}
for old,new in changes.items():
 candidates=[s for s in d['slots']if s['text']==old and s['at']in[[6,26,0],[6,31,0]]];assert len(candidates)==1,(old,candidates);candidates[0]['text']=new
assert [6,34,0]in d['protected_runs'];d['protected_runs'].remove([6,34,0]);d['reviewed_formula_protection_evidence']=[e for e in d['reviewed_formula_protection_evidence']if e['at']!=[6,34,0]]
d['slots'].append(dict(at=[6,34,0],source_text=', ',text=')를 적용하면 '));d['source_visual_review_note']+=' Child full-page review: clarify the source initial-condition sentence as 식(1)에 초기 조건 m=m0(v=0)를 적용하면. Only the original12pt English prose comma after the condition is translated into Korean sentence punctuation/words. Every original m/m0/v/0/operator/script glyph, point, paint and baseline remains source-native.'
path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
files=sorted(p for p in F.glob('page04*')if p.is_file());version=hashlib.sha256(''.join(p.name+sha(p)for p in files).encode()).hexdigest()[:16];archive=F/'history'/f'page04-positive-before-initial-condition-prose-review-{version}';archive.mkdir(parents=True,exist_ok=True)
for item in files:
 target=archive/item.name;assert item.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve());assert not target.exists();digest=sha(item);item.rename(target);assert sha(target)==digest
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');subprocess.run([sys.executable,'-u','-X','utf8',str(R/'build-izho2014-solutions-baseline-page.py'),'4'],env=env,check=True)
prepare=R/'prepare-izho2014-solutions-natural.py';code=prepare.read_text('utf8');head,tail=code.split('sys.path[:0]=',1);prefix='\n'.join(head.splitlines()[:3])+'\n';sys.argv=[str(prepare),'4'];exec(compile(prefix+'sys.path[:0]='+tail,str(prepare)+'#child-reuse-current-engines','exec'),{'__name__':'__main__'})
assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f';print('2014_PAGE4_INITIAL_CONDITION_KOREAN_PROSE_REPAIRED_NATIVE_MATH_UNCHANGED',flush=True)
