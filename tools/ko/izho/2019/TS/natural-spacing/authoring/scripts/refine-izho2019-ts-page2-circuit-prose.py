from pathlib import Path
import hashlib,json,subprocess,sys,os,shutil
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');R=Path('D:/CodexBuilds');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in[B/'2019/original_style/page2.json',B/'natural/2019/TS/plans/page02.json',B/'natural/2019/TS/page02-build.log',R/'author-izho2019-ts-page2.py']:
 h=B/'rejected-evidence'/sha(p);h.mkdir(parents=True,exist_ok=True);dst=h/p.name
 if dst.exists():assert dst.read_bytes()==p.read_bytes()
 else:shutil.copy2(p,dst)
p=R/'author-izho2019-ts-page2.py';t=p.read_text('utf8');t=t.replace("'28,0,0':'축전기에 코일을 직렬로 연결하고 그 인덕턴스를 '","'28,0,0':'코일을 축전기에 직렬로 연결하면 위상차를 없앨 수 있다. '").replace("'28,1,0':'다음과 같이 정하면 위상차는 영이 된다 '","'28,1,0':'그 조건은 '");p.write_text(t,'utf8')
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
subprocess.run([sys.executable,'-u','-X','utf8',str(p)],env=env,check=True)
subprocess.run([sys.executable,'-u','-X','utf8',str(R/'build-izho2019-ts-baseline-page.py'),'2'],env=env,check=True)
# Preserve the old immutable combined native input; only this page's derived
# plan points at the new complete12p native-baseline assembly.
p=B/'2019/inspection/page02-combined-baseline-native-groups.json';h=B/'rejected-evidence'/sha(p);h.mkdir(parents=True,exist_ok=True);shutil.move(str(p),str(h/p.name))
subprocess.run([sys.executable,'-u','-X','utf8',str(R/'prepare-izho2019-ts-natural.py'),'2'],env=env,check=True)
print('SOURCE2019_P2_CIRCUIT_PROSE_SHORTENED_WITH_ALL_NATIVE_FRACTIONS_AND_ORIGINAL_COLUMN_WIDTH_UNCHANGED',flush=True)
