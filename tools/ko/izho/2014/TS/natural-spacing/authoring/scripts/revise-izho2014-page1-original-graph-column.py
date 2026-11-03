from pathlib import Path
import hashlib,shutil,os,sys,subprocess
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/izho2014-complete-solutions';p=R/'author-izho2014-solutions-page1.py';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();text=p.read_text('utf8');history=B/'authoring-history'/sha(p)[:16];history.mkdir(parents=True,exist_ok=True);shutil.copy2(p,history/p.name);shutil.copy2(B/'2014/original_style/page1.json',history/'page1.json')
for a,b in[("'2,7,0':'제2단계와 제4단계는 '","'2,7,0':'제2·4단계는 단열 과정으로 본다. '"),("'2,8,0':'단열 과정으로 볼 수 있다. 증기 기관의 ('","'2,8,0':'증기 기관의 ('")]:assert text.count(a)==1;text=text.replace(a,b)
p.write_text(text,'utf8');env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
subprocess.run([sys.executable,'-u','-X','utf8',str(p)],env=env,check=True);subprocess.run([sys.executable,'-u','-X','utf8',str(R/'build-izho2014-solutions-baseline-page.py'),'1'],env=env,check=True)
prepare=R/'prepare-izho2014-solutions-natural.py';code=prepare.read_text('utf8');head,tail=code.split('sys.path[:0]=',1);prefix='\n'.join(head.splitlines()[:3])+'\n';sys.argv=[str(prepare),'1'];exec(compile(prefix+'sys.path[:0]='+tail,str(prepare)+'#reuse-reviewed-engine','exec'),{'__name__':'__main__'})
print('2014_GRAPH_COLUMN_PROSE_REVISED_AT_UNCHANGED_SOURCE_POINT_SIZE',flush=True)
