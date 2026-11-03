from pathlib import Path
import hashlib,subprocess,os,sys
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/izho2014-complete-solutions';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
for n in range(1,11):subprocess.run([sys.executable,'-u','-X','utf8',str(R/f'author-izho2014-solutions-page{n}.py')],env=env,check=True)
template=R/'prepare-izho2013-private-engine.py';code=template.read_text('utf8').replace('2013','2014').replace('2804ded48ad009bf58884b871f0f4817c64762b8a0f586e42056908fc4be10f1',sha(B/'2014/source/IZhO_2014_TS.pdf'))
dest=R/'prepare-izho2014-private-engine.py';assert not dest.exists();dest.write_text(code,'utf8');subprocess.run([sys.executable,'-u','-X','utf8',str(dest)],env=env,check=True)
builder=R/'build-izho2014-solutions-baseline-page.py';assert not builder.exists();builder.write_text((R/'build-izho2013-solutions-baseline-page.py').read_text('utf8').replace('2013','2014'),'utf8')
for n in range(1,11):subprocess.run([sys.executable,'-u','-X','utf8',str(builder),str(n)],env=env,check=True)
print('ALL10_PRIVATE_IZHO2014_NATIVE_SOURCE_BASELINES_BUILT',flush=True)
