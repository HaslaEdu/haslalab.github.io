from pathlib import Path
import sys,json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_source_prose_reference_forms import promote
from pdf_native_inline_reposition import inspect_inline_groups,_traces
from pdf_original_text_ops import glyph_key
from pdf_memory_gate import page_worker
import pymupdf as f
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for n in map(int,sys.argv[1:]):
 plan=json.loads((B/f'natural/2012/TS/plans/page{n:02}.json').read_text('utf8'));assert plan['original_english_source_sha256']=='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db'
 base=Path(plan['source_base']);assert sha(base)==plan['source_base_sha256'];inv=inspect_inline_groups(base,n)
 with f.open(base)as doc:actual={glyph_key(g):g for g in _traces(doc[n-1])if g['c'].strip()}
 groups=[]
 for literal in plan['reviewed_source_prose_native_reference_glyphs']:
  resolved=[]
  for g in literal['source_glyphs']:
   if not g['c'].strip():continue
   hit=actual.get(glyph_key(g))
   if hit is None:
    matches=[a for a in actual.values()if a['c']==g['c']and a['font']==g['font']and abs(a['size']-g['size'])<.0001 and max(abs(x-y)for x,y in zip(a['origin'],g['origin']))<.0001]
    if len(matches)!=1:raise ValueError(('Exact original reference glyph not resolved within existing native float32 tolerance',n,literal,g))
    hit=matches[0]
   resolved.append(hit)
  keys={glyph_key(g)for g in resolved}
  if not keys or any(actual[k]['font']!='CambriaMath'or actual[k]['render_mode']!=0 for k in keys):continue
  clips=[c for c in inv['clip_groups']if c.get('known_rectangular_clips')and len(c['clip_rects'])==1 and f.Rect(c['clip_rects'][0]).height<100 and keys<={glyph_key(g)for g in c['glyphs']if g['c'].strip()}]
  unclipped=(n==7 and literal['source_at']==[35,2,0]and literal['source_text']in['(18)','(19)'])
  if not clips and not unclipped:continue
  groups.append(dict(source_at=literal['source_at'],source_text=literal['source_text'],glyphs=resolved,reviewed_unclipped_original_prose_reference=unclipped))
 if not groups:print('NO_CLIPPED_GRAY_FIELD_REFERENCES_REQUIRE_ISOLATION',n,flush=True);continue
 out=B/'2012/native-reference-isolation'/plan['source_base_sha256'][:16];out.mkdir(parents=True,exist_ok=True);pdf=out/f'page{n:02}.pdf'
 engine_sha=sha(B/'engine/pdf_source_prose_reference_forms.py')
 if pdf.exists()and pdf.with_suffix('.native-cid-qa.json').exists():
  previous=json.loads(pdf.with_suffix('.native-cid-qa.json').read_text('utf8'))
  assert previous['passed']and previous['output_sha256']==sha(pdf)and previous['source_sha256']==sha(base)
  assert[(v['source_at'],v['source_text'])for v in previous['reference_groups']]==[(v['source_at'],v['source_text'])for v in groups]
  if previous.get('actual_native_reference_engine_sha256')==engine_sha:print('EXISTING_EXACT_REFERENCE_FORM_PROOF_PRESERVED',n,pdf,flush=True);continue
  history=out/'history'/sha(pdf)[:16];history.mkdir(parents=True,exist_ok=True)
  for old in out.glob(f'page{n:02}*'):
   if old.is_file()and not(history/old.name).exists():(history/old.name).write_bytes(old.read_bytes())
 with page_worker():raw,qa=promote(base,n,groups,sum(len(p['parts'])for p in plan['prose_placements']))
 qa['actual_native_reference_engine_sha256']=engine_sha
 pdf.write_bytes(raw);pdf.with_suffix('.native-cid-qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n','utf8')
 with f.open(base)as a,f.open(pdf)as b:
  if a[n-1].get_text()!=b[0].get_text():print('TRACE_ORDER_CHANGED_TO_EXPLICIT_NATIVE_FORM_PAINT_LAYER',n,flush=True)
 print('EXACT_ORIGINAL_CLIPPED_NATIVE_REFERENCE_FORMS_PREPARED',n,len(groups),qa['passed'],pdf,flush=True)
