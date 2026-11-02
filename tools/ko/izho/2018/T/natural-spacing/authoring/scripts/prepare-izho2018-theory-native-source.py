from pathlib import Path
import json,hashlib,shutil,sys
import pymupdf as f
P=Path('D:/CodexBuilds/Hasla-original-style-20261031')
B=P/'izho2018-theory-original';E=B/'engine';E.mkdir(parents=True,exist_ok=True)
C=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab')
for p in(P/'izho2020-complete-solutions/engine').glob('*.py'):
 target=E/p.name
 if target.exists():continue
 s=p.read_text('utf8').replace('izho2020-complete-solutions','izho2018-theory-original')
 if p.name=='source_slot_authoring.py':s=s.replace('XVI','XIV').replace('_{self.year}_TS.pdf','_{self.year}_T.pdf')
 target.write_text(s,'utf8')
source=B/'2018/source/IZhO_2018_T.pdf';source.parent.mkdir(parents=True,exist_ok=True)
old=C/'tmp/source-audit/IZhO_2018_T_EN.pdf'
assert hashlib.sha256(old.read_bytes()).hexdigest()=='0782ab2ced4c911ce92b550aa2fd86cb7f6c9a6e24d7a60f64b13275df1e38ba'
if not source.exists():shutil.copy2(old,source)
for folder in ['inspection','original_style','native-baseline']:(B/f'2018/{folder}').mkdir(exist_ok=True)
sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_initial_fixed_style import runs_of
from pdf_native_inline_reposition import _traces
with f.open(source)as d:
 assert len(d)==6
 for n,page in enumerate(d,1):
  runs={','.join(map(str,k)):{key:v[key]for key in ['text','font','size','flags','color','origin','bbox']}for k,v in runs_of(page).items()}
  for name,data in [('runs',runs),('glyphs',_traces(page)),('images',page.get_image_info()),('drawings',page.get_drawings())]:
   (B/f'2018/inspection/page{n:02}-{name}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n','utf8')
  lines=[f"{k} | {v['font']} {v['size']:.5f} @({v['origin'][0]:.2f},{v['origin'][1]:.2f}) | {v['text']}"for k,v in runs.items()]
  (B/f'2018/inspection/page{n:02}-runs.txt').write_text('\n'.join(lines)+'\n','utf8')
  print('NATIVE_SOURCE_PAGE',n,'runs',len(runs),'fonts',sorted({v['font']for v in runs.values()}),flush=True)
policy=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_url='https://izho.kz/wp-content/uploads/2018/01/IZhO-2018-Theory_eng.pdf',source_language='English',pages=6,semantic_translation=str(P/'izho-missing-editions/2018/T/semantic-translation-draft.json'),publication_ready=False,policy='All original six pages, physical source font points/roles, original native equations, variables, counters, grades, figures and source vector geometry. No justified word spacing, font shrinking, equation retyping or old math PNG re-use.')
(B/'source-policy.json').write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n','utf8')
print('ALL6_ORIGINAL_SOURCE_PAGES_INVENTORIED')
