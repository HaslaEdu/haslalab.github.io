from pathlib import Path
import hashlib,subprocess,sys,os
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/izho2014-complete-solutions';source_sha=hashlib.sha256((B/'2014/source/IZhO_2014_TS.pdf').read_bytes()).hexdigest()
template=R/'prepare-izho2013-solutions-natural.py';text=template.read_text('utf8').replace('2013','2014').replace('2804ded48ad009bf58884b871f0f4817c64762b8a0f586e42056908fc4be10f1',source_sha)
a="new=\"RANGES={1:[],2:[],3:[1],4:range(1,12),5:range(12,18),6:range(18,30),7:[],8:range(1,10),9:range(10,20),10:[]}\"";b="new=\"RANGES={1:range(1,5),2:[],3:[],4:[1],5:range(2,16),6:range(16,26),7:range(1,8),8:range(8,22),9:range(22,28),10:[]}\"";assert text.count(a)==1;text=text.replace(a,b)
assert text.count("if not m or run['origin'][0]<490:continue")==1
text=text.replace("if not m or run['origin'][0]<490:continue","if not m or not (run['origin'][0]>=490 or (plan['source_page']==1 and tuple(at)==(5,7,0))):continue")
assert text.count("r['text'].strip()=='Description'")==1;text=text.replace("r['text'].strip()=='Description'","r['text'].strip()in['Description','Content']")
a="  if d['page']==3 and all(bi==4 for bi,li in ats):rect[2]=402.89";b="  if d['page']==1 and all((bi==2 and li>=3)or(bi==6 and li in[0,1])for bi,li in ats):rect[2]=322.7";assert text.count(a)==1;text=text.replace(a,b)
a="right=402.89 if d['page']==3 and all(bi==4 for bi,li in ats)else 555.94";b="right=322.7 if d['page']==1 and all((bi==2 and li>=3)or(bi==6 and li in[0,1])for bi,li in ats)else 555.94";assert text.count(a)==1;text=text.replace(a,b)
dest=R/'prepare-izho2014-solutions-natural.py';assert not dest.exists();dest.write_text(text,'utf8')
for name in ['build-izho2013-solutions-natural-page.py','check-and-preview-izho2013-extra-prose.py','render-izho2013-reviewed-previews.py','build-izho2013-natural-pages-and-checks.py']:
 target=R/name.replace('2013','2014');assert not target.exists();target.write_text((R/name).read_text('utf8').replace('2013','2014'),'utf8')
source=B.with_name('izho2013-complete-solutions')/'engine/izho_2013_non_hangul_prose_collision.py';target=B/'engine/izho_2014_non_hangul_prose_collision.py';text=source.read_text('utf8').replace('2013','2014').replace('2804ded48ad009bf58884b871f0f4817c64762b8a0f586e42056908fc4be10f1',source_sha);assert not target.exists();target.write_text(text,'utf8')
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
subprocess.run([sys.executable,'-u','-X','utf8',str(dest),*map(str,range(1,11))],env=env,check=True)
print('ALL10_2014_NATIVE_NATURAL_PLANS_PREPARED_56_ORIGINAL_DISPLAY_LABELS_EXPECTED',source_sha,flush=True)
