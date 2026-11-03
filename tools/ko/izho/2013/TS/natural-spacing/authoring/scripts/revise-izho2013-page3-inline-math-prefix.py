from pathlib import Path
import json,sys,os,hashlib,shutil,subprocess
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/izho2013-complete-solutions';F=B/'natural/2013/TS';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();p=R/'author-izho2013-solutions-page3.py';text=p.read_text('utf8');old="'4,21,0':' '";assert text.count(old)==1
saved=B/'authoring-history'/sha(p)[:16];saved.mkdir(parents=True,exist_ok=True);shutil.copy2(p,saved/p.name);shutil.copy2(B/'2013/original_style/page3.json',saved/'page3.json');p.write_text(text.replace(old,"'4,21,0':'그 거리는 '"),'utf8')
files=sorted(p for p in F.glob('page03*')if p.is_file());version=hashlib.sha256(''.join(p.name+sha(p)for p in files).encode()).hexdigest()[:16];archive=F/'history'/f'preserved-before-original-inline-prefix-review-{version}';archive.mkdir(parents=True,exist_ok=True)
for item in files:
 target=archive/item.name;assert item.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve());assert not target.exists();digest=sha(item);item.rename(target);assert sha(target)==digest
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
subprocess.run([sys.executable,'-u','-X','utf8',str(p)],env=env,check=True);subprocess.run([sys.executable,'-u','-X','utf8',str(R/'build-izho2013-solutions-baseline-page.py'),'3'],env=env,check=True)
prepare=R/'prepare-izho2013-solutions-natural.py';code=prepare.read_text('utf8');head,tail=code.split('sys.path[:0]=',1);prefix='\n'.join(head.splitlines()[:3])+'\n';sys.argv=[str(prepare),'3'];exec(compile(prefix+'sys.path[:0]='+tail,str(prepare)+'#reuse-reviewed-engine','exec'),{'__name__':'__main__'})
print('SOURCE_2013_PAGE3_MEANINGFUL_INLINE_PREFIX_REVIEWED',flush=True)
