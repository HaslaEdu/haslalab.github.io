from pathlib import Path
import sys,json,hashlib,shutil
import pymupdf as fitz
OLD=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-remaining-solutions/2020');B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');E=B/'engine';E.mkdir(parents=True,exist_ok=True)
source_engine=B.parent/'izho2010-complete-solutions/engine'
for p in source_engine.glob('*.py'):
 text=p.read_text('utf8').replace('izho2010-complete-solutions','izho2020-complete-solutions')
 (E/p.name).write_text(text,'utf8')
for name in ['source','prior-authoring']:
 shutil.copytree(OLD/name,B/'2020'/name,dirs_exist_ok=True)
for name in ['inspection','original_style','native-baseline']:(B/'2020'/name).mkdir(exist_ok=True)
sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_initial_fixed_style import runs_of
from pdf_native_inline_reposition import _traces
source=B/'2020/source/IZhO_2020_TS.pdf';digest=hashlib.sha256(source.read_bytes()).hexdigest();assert digest=='2b553d707456ac992698b78d2ef94bd1a81994833b4815a3a0a60884b88823e9'
with fitz.open(source)as doc:
 assert len(doc)==13
 for n,page in enumerate(doc,1):
  runs={','.join(map(str,k)):{key:v[key]for key in ['text','font','size','flags','color','origin','bbox']}for k,v in runs_of(page).items()}
  for name,data in [('runs',runs),('glyphs',_traces(page)),('images',page.get_image_info()),('drawings',page.get_drawings())]:
   # Drawings contain native Point/Rect objects; their repr is inspection-only.
   (B/f'2020/inspection/page{n:02}-{name}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n','utf8')
policy=dict(source=str(source),source_sha256=digest,source_url='https://izho.kz/wp-content/uploads/2020/01/IZhO-2020-Theory_eng_sol.pdf',source_language='English',pages=13,policy='Single complete official English solution source; retain original page count, all original native mathematics, counters, grades, original figures and source point/baseline/style roles. No target-box font fitting, equation retyping or generic justified spacing.')
(B/'source-policy.json').write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n','utf8');print('OFFICIAL_NATIVE_SOURCE_READY',13,digest)
