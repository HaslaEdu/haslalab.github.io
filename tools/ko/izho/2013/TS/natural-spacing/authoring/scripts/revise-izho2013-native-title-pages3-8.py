from pathlib import Path
import hashlib,json,os,subprocess,sys,shutil
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/izho2013-complete-solutions';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');receipt=[]
for n,at,num in[(3,'7,0,0','2'),(8,'2,0,0','3')]:
 path=R/f'author-izho2013-solutions-page{n}.py';text=path.read_text('utf8');a=f"around(p,'{at}',['문제 ',' (','점) '],['{num}','10'])";b=f"around(p,'{at}',['문제 ','점',' '],['{num} (10 ',')'])";assert text.count(a)==1
 history=B/'authoring-history'/sha(path)[:16];history.mkdir(parents=True,exist_ok=True);shutil.copy2(path,history/path.name);shutil.copy2(B/f'2013/original_style/page{n}.json',history/f'page{n}.json');path.write_text(text.replace(a,b),'utf8')
 if n==3:
  folder=B/'natural/2013/TS';files=sorted(p for p in folder.glob('page03*')if p.is_file());version=hashlib.sha256(''.join(p.name+sha(p)for p in files).encode()).hexdigest()[:16];saved=folder/'history'/f'positive-before-title-order-review-{version}';saved.mkdir(parents=True,exist_ok=True)
  for p in files:
   target=saved/p.name;assert p.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve());assert not target.exists();digest=sha(p);p.rename(target);assert sha(target)==digest
  receipt.append(dict(page=n,preserved_prior_proof=str(saved),reason='Full-page visual review found original numeral2 and10 remained one native text group while inserted Korean punctuation fell after both numerals. Protect original complete2 (10 sequence, then translate only points; keep original native glyph programs and physical center.'))
 subprocess.run([sys.executable,'-u','-X','utf8',str(path)],env=env,check=True)
 subprocess.run([sys.executable,'-u','-X','utf8',str(R/'build-izho2013-solutions-baseline-page.py'),str(n)],env=env,check=True)
 prepare=R/'prepare-izho2013-solutions-natural.py';code=prepare.read_text('utf8');head,tail=code.split('sys.path[:0]=',1);prefix='\n'.join(head.splitlines()[:3])+'\n';assert 'numbers=set(map(int,sys.argv[1:]))'in prefix
 assert not(B/f'natural/2013/TS/page{n:02}.pdf').exists(),'A proof became active before preparation; preserve it explicitly before replacing its plan.'
 sys.argv=[str(prepare),str(n)];exec(compile(prefix+'sys.path[:0]='+tail,str(prepare)+'#reuse-reviewed-engine','exec'),{'__name__':'__main__'})
 receipt.append(dict(page=n,author_before=sha(history/path.name),author_after=sha(path),original_native_title_sequence=f'{num} (10 ',translated_sequence=f'문제 {num} (10점)'))
(B/'2013-reviewed-native-title-sequence-revisions.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n','utf8');print('SOURCE_NATIVE_TITLE_ORDER_PAGES3_8_REVIEWED',flush=True)
