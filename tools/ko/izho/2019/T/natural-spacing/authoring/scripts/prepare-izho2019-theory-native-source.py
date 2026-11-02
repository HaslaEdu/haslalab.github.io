from pathlib import Path
import json,hashlib,shutil,sys
import pymupdf as f
OLD=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original');E=B/'engine';E.mkdir(parents=True,exist_ok=True)
assert str(B.resolve()).lower().startswith(str(Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102').resolve()).lower())
for p in(OLD/'engine').glob('*.py'):
 dest=E/p.name
 if dest.exists():continue
 s=p.read_text('utf8').replace(OLD.as_posix(),B.as_posix()).replace(repr(str(OLD))[1:-1],repr(str(B))[1:-1])
 if p.name=='source_slot_authoring.py':s=s.replace('XIV','XV')
 dest.write_text(s,'utf8')
source=B/'2019/source/IZhO_2019_T.pdf';source.parent.mkdir(parents=True,exist_ok=True);old=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab/tmp/source-audit/IZhO_2019_T_EN.pdf');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();digest='29daec0cb9f759bed9b755cbae2937e1c4ab068fa804c62d512ea291e42619d1';assert sha(old)==digest
if not source.exists():shutil.copy2(old,source)
assert sha(source)==digest
for name in ['inspection','original_style','native-baseline']:(B/f'2019/{name}').mkdir(exist_ok=True)
sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_initial_fixed_style import runs_of
from pdf_native_inline_reposition import _traces
with f.open(source)as d:
 assert len(d)==8
 for n,page in enumerate(d,1):
  runs={','.join(map(str,k)):{key:v[key]for key in ['text','font','size','flags','color','origin','bbox']}for k,v in runs_of(page).items()}
  for name,data in [('runs',runs),('glyphs',_traces(page)),('images',page.get_image_info()),('drawings',page.get_drawings())]:
   (B/f'2019/inspection/page{n:02}-{name}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n','utf8')
  lines=[f"{k} | {v['font']} {v['size']:.5f} @({v['origin'][0]:.2f},{v['origin'][1]:.2f}) | {v['text']}"for k,v in runs.items()]
  (B/f'2019/inspection/page{n:02}-runs.txt').write_text('\n'.join(lines)+'\n','utf8');print('ORIGINAL2019_T_SOURCE_PAGE',n,'runs',len(runs),'fonts',sorted({v['font']for v in runs.values()}),flush=True)
 assert sha(E/'pdf_native_inline_reposition.py')==sha(OLD/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
q=dict(source=str(source),source_sha256=digest,source_url='https://izho.kz/wp-content/uploads/2019/01/IZhO-2019-Theory_eng.pdf',pages=8,source_language='English',original_source_native_math_only=True,publication_ready=False,policy='All8original source pages; retain original fonts/points/paint/baselines/figures/math. Explicit reviewed Korean prose slots, natural quarter-em spaces; no old mathPNG reuse or font fitting.')
(B/'source-policy.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('PREPARED_ALL8_SOURCE_PAGES_PRIVATE',B,flush=True)
