"""Serial whole-edition source/font/prose/independent math-union QA."""
from pathlib import Path
import sys,json,time,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
ROOT=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2025/p2-6-authoring/tools']
from pdf_memory_gate import page_worker
import cpho_2013_ts_compose as compose
compose.ROOT=ROOT;compose.BASE=B;compose.SOURCE=ROOT/'tmp/original-style-sources/CPhO_2013_Chinese_original.pdf'
import cpho_2013_original_extract as original
original.ROOT=ROOT;original.SOURCE=compose.SOURCE
import cpho_2013_ts_qa as qa
import cpho_2013_ts_generic_qa_adapter as generic
from qa_pages import math_visibility
from pdf_original_text_ops import widths
from izho_new_prose_outline_qa import trace_font_resources
import pikepdf,pymupdf as fitz
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
# 2025 QA reuse imports its compositor, whose historical shared.BASE side effect
# must be reset to the explicitly pinned TS-only output root before building.
compose.BASE=B;compose.ROOT=ROOT;compose.SOURCE=ROOT/'tmp/original-style-sources/CPhO_2013_Chinese_original.pdf'
out=B/'final-qa';out.mkdir(exist_ok=True);results=json.loads((B/'final-qa/whole-edition-results.json').read_text('utf8'));results=[r for r in results if r['source_page']!=10]
REBUILD={(n,'ko')for n in [5,7,8,10,13,14]}|{(n,'en')for n in [4,5,6,7,8,9,10,11,13,14]}

def positive_widths(pdf):
 with pikepdf.open(pdf)as doc,fitz.open(pdf)as mupdf:
  page=doc.pages[0];glyphs,_=trace_font_resources(doc,mupdf[0]);cache={};bad=[];checked=0
  for glyph in glyphs:
   name=glyph['font_alias']
   if not(name.startswith('/TSHeader')or name=='/TSScanBody')or glyph['c'].isspace():continue
   font=page.Resources.Font[name]
   if str(font.get('/Subtype'))!='/Type0'or str(font.get('/Encoding'))!='/Identity-H':raise ValueError('Unexpected authored prose encoding')
   desc=font.DescendantFonts[0]
   if str(desc.get('/CIDToGIDMap','/Identity'))!='/Identity':raise ValueError('Authored prose needs exact Identity CID/GID matching')
   if name not in cache:cache[name]=widths(font)
   mapping,default=cache[name];value=mapping.get(glyph['gid'],default);checked+=1
   if value is None or value<=0:bad.append(dict(c=glyph['c'],gid=glyph['gid'],font=name,actual_CID_width=value))
  return dict(actual_used_new_prose_CID_widths_checked=checked,nonpositive_actual_CID_widths=bad,passed=not bad)
for n in [10]:
 for language in ['ko','en']:
  try:
   with page_worker():
    if (n,language) in REBUILD:compose.build(n,language)
    stem=B/f'proofs/{language}/page{n:02d}';pdf=stem.with_suffix('.pdf');m=json.loads(stem.with_suffix('.composition.json').read_text('utf8'))
    if m['output_sha256']!=sha(pdf)or m['inline_math_replay'].get('stage')!='original-math replay before new prose':raise ValueError('Unreviewed proof or wrong paint order')
    a=qa.audit(n,language);g=generic.audit(n,language)
    union=math_visibility(stem.with_suffix('.pre-prose.pdf'),pdf,stem.with_suffix('.prose-only.pdf'),stem.with_suffix('.math-union-reference.pdf'))
    union.update(source_sha256=m['source_sha256'],source_page=n,proof_sha256=sha(pdf),language=language)
    stem.with_suffix('.math-union-qa.json').write_text(json.dumps(union,ensure_ascii=False,indent=2),'utf8')
    actual=positive_widths(pdf);stem.with_suffix('.actual-CID-widths.json').write_text(json.dumps(actual,ensure_ascii=False,indent=2),'utf8')
    record=dict(source_page=n,language=language,proof=str(pdf),proof_sha256=sha(pdf),source_qa=str(stem.with_suffix('.source-qa.json')),source_qa_sha256=sha(stem.with_suffix('.source-qa.json')),generic_qa=str(stem.with_suffix('.generic-scan-qa.json')),generic_qa_sha256=sha(stem.with_suffix('.generic-scan-qa.json')),math_union=str(stem.with_suffix('.math-union-qa.json')),math_union_sha256=sha(stem.with_suffix('.math-union-qa.json')),actual_CID_widths=str(stem.with_suffix('.actual-CID-widths.json')),actual_CID_widths_sha256=sha(stem.with_suffix('.actual-CID-widths.json')),passed=a['passed']and g['passed']and union['passed']and actual['passed'])
    results.append(record);print(json.dumps({k:record[k]for k in ['source_page','language','proof_sha256','passed']}), 'union',union['missing_original_replayed_math_ink'],union['new_prose_overlap_independent_math_union'],flush=True)
  except Exception as error:
   import traceback;traceback.print_exc();results.append(dict(source_page=n,language=language,passed=False,error=repr(error)));print('FAILED',n,language,repr(error),flush=True)
  (out/'whole-edition-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),'utf8');time.sleep(.6)
results.sort(key=lambda r:(r['source_page'],r['language']));(out/'whole-edition-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),'utf8');raise SystemExit(any(not r['passed']for r in results))
