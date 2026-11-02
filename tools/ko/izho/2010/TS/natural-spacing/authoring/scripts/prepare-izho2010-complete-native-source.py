"""Use the complete official11-page Russian solutions as the canonical source."""
from pathlib import Path
import shutil,json,hashlib,sys
import pymupdf as fitz
OLD=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-remaining-solutions')
B=OLD.parent/'izho2010-complete-solutions';E=B/'engine';E.mkdir(parents=True,exist_ok=True)
C=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab');PUB=Path('D:/CodexBuilds/Hasla-publish-20261031')
for src in (OLD/'engine').glob('*.py'):
 dest=E/src.name
 if not dest.exists():
  raw=src.read_text('utf8')
  for part in ['natural','fonts','']:
   before=OLD/part if part else OLD;after=B/part if part else B
   raw=raw.replace(repr(str(before)),repr(str(after)))
  dest.write_text(raw,'utf8')
source=B/'2010/source/IZhO_2010_TS_RU.pdf';source.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(C/'tmp/source-audit/IZhO_2010_TS_RU.pdf',source)
assert hashlib.sha256(source.read_bytes()).hexdigest()=='7b05288bf9480392aa2b945b589f00e6034de6d3739da4dd06f01d6d1118f114'
for kind,name in [('TS','translation.raw.json'),('TS','translation.json'),('T3S','translation.json')]:
 src=C/f'tools/ko/izho/2010/{kind}/{name}';dest=B/f'2010/prior-authoring/{kind}-{name}';dest.parent.mkdir(exist_ok=True);shutil.copy2(src,dest)
sys.path[:0]=[str(E),str(PUB/'tools')]
from izho_initial_fixed_style import runs_of
from pdf_native_inline_reposition import _traces
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
with fitz.open(source)as doc:
 assert len(doc)==11
 for n,page in enumerate(doc,1):
  rows={','.join(map(str,k)):{key:s[key]for key in['text','font','size','flags','color','origin','bbox']}for k,s in runs_of(page).items()}
  save(B/f'2010/inspection/page{n:02}-runs.json',rows);save(B/f'2010/inspection/page{n:02}-glyphs.json',_traces(page))
  save(B/f'2010/inspection/page{n:02}-images.json',page.get_image_info())
save(B/'source-policy.json',dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_url='https://izho.kz/wp-content/uploads/2018/12/IZhO-2010-Theory_rus_sol_f.pdf',source_language='Russian',pages=11,complete_original_questions=[1,2,3],source_selection_reason='Official English7-page solutions omit theoretical question3. Use the complete official Russian11-page original consistently, preserving its original page count, headers, typography, all diagrams, mathematics and marking schemes. Prior English layout work is an unpublished engine prototype only.',english_prototype=str(OLD/'2010'),original_page_fragments_not_erased_or_combined=True))
print('Complete canonical source ready:',source,'11 original pages',flush=True)
