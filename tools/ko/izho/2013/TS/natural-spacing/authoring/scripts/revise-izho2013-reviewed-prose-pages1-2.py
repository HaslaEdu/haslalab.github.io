from pathlib import Path
import hashlib,json,os,subprocess,sys,shutil
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/izho2013-complete-solutions'
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
changes={1:[("'15,0,0':'이고, 그 사이 한쪽 끝의 작은 변위를 '","'15,0,0':'이고, 그 사이 한쪽 끝이 움직인 '"),("'16,0,0':' '","'16,0,0':'작은 거리를 '"),("'28,1,0':'맨 위점부터 오른쪽에 있는 줄에 아주 짧은 시간 '","'28,1,0':'에너지 보존을 적용한다. 고려하는 짧은 시간 간격은 '"),("['',' 항목 ','과 같은 방법으로 에너지 보존을 적용한다. ']","['',' 항목 ','과 같은 방법으로, 맨 위점부터 줄의 오른쪽 부분에 ']")],2:[("'16,0,0':'다음을 얻는다: '","'16,0,0':'다음을 얻는다 '")]}
receipt=[]
for n,replacements in changes.items():
 path=R/f'author-izho2013-solutions-page{n}.py';old=path.read_text('utf8');new=old
 for a,b in replacements:assert new.count(a)==1,(n,a);new=new.replace(a,b)
 history=B/'authoring-history'/sha(path)[:16];history.mkdir(parents=True,exist_ok=True);shutil.copy2(path,history/path.name)
 plan=B/f'2013/original_style/page{n}.json'
 if plan.exists():shutil.copy2(plan,history/plan.name)
 path.write_text(new,'utf8');receipt.append(dict(page=n,author_before=sha(history/path.name),author_after=sha(path),changes=replacements))
folder=B/'natural/2013/TS'
files=sorted(p for p in folder.glob('page01*')if p.is_file())
if files:
 version=hashlib.sha256(''.join(p.name+sha(p)for p in files).encode()).hexdigest()[:16]
 history=folder/'history'/f'positive-before-prose-review-{version}';history.mkdir(parents=True,exist_ok=True)
 for p in files:
  target=history/p.name;assert p.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve())
  assert not target.exists();digest=sha(p);p.rename(target);assert sha(target)==digest
 receipt.append(dict(preserved_page1_proof=str(history),files=len(files)))
(B/'2013-reviewed-prose-revisions.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n','utf8')
for n in changes:
 subprocess.run([sys.executable,'-u','-X','utf8',str(R/f'author-izho2013-solutions-page{n}.py')],env=env,check=True)
 subprocess.run([sys.executable,'-u','-X','utf8',str(R/'build-izho2013-solutions-baseline-page.py'),str(n)],env=env,check=True)
prepare=R/'prepare-izho2013-solutions-natural.py';code=prepare.read_text('utf8');head,tail=code.split("sys.path[:0]=",1)
prefix='\n'.join(head.splitlines()[:3])+'\n';assert 'numbers=set(map(int,sys.argv[1:]))'in prefix
sys.argv=[str(prepare),'1','2']
exec(compile(prefix+'sys.path[:0]='+tail,str(prepare)+'#reuse-reviewed-engine','exec'),{'__name__':'__main__'})
print('REVISED_2013_PROSE_PAGES1_2_PRESERVED_ALL_PRIOR_EVIDENCE_AND_ACTIVE_ENGINE',flush=True)
