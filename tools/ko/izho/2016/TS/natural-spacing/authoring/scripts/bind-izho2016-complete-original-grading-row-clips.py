from pathlib import Path
import json,hashlib,sys,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_native_inline_reposition import inspect_inline_groups,_traces
from pdf_original_text_ops import glyph_key
from pdf_memory_gate import page_worker
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ys={7:[653.02,667.66,682.18,696.82,713.14,734.26],8:[124.46,145.7,168.26,209.9,250.58,298.61,316.49,334.49,370.01,407.69,464.47,498.67,513.31,527.83]}
for n in map(int,sys.argv[1:]):
 P=B/f'natural/2016/TS/plans/page{n:02}.json';p=json.loads(P.read_text('utf8'));history=P.parent/'history'/sha(P);history.mkdir(parents=True,exist_ok=True);(history/P.name).write_bytes(P.read_bytes())
 with page_worker():
  inv=inspect_inline_groups(p['source_base'],n)
  with f.open(p['original_english_source'])as source:original={glyph_key(g)for g in _traces(source[n-1])if g['c'].strip()}
 bindings=[]
 for y in ys[n]:
  matches=[c for c in inv['clip_groups']if c.get('known_rectangular_clips')and len(c['clip_rects'])==1 and 110<c['clip_rects'][0][0]<113 and 456<c['clip_rects'][0][2]<459 and c['clip_rects'][0][1]<y<c['clip_rects'][0][3]and f.Rect(c['clip_rects'][0]).height<85];assert matches,(n,y)
  c=min(matches,key=lambda c:c['operator_indices'][0]);gs=[g for g in c['glyphs']if g['c'].strip()];assert gs and all(glyph_key(g)in original for g in gs),(n,y)
  a=next(a for a in p['explicit_native_math_atoms']if abs(a['baseline']-y)<.02);a.update(rect=c['clip_rects'][0],source_native_glyphs=gs,use_complete_original_clip=True,source_complete_clip_operator_indices=c['operator_indices'])
  for key in['source_form_path','source_form_bbox','source_reference_preserve_original_glyph_advance','source_form_program_sha256']:a.pop(key,None)
  a['reason']='Full original2016 source rubric visually read. One complete original OUTER Word content-row clip includes the native(n) reference and every original formula CID/script/fraction/root path. They share one horizontal dx after the translated Korean label. Exact source raw clip coordinates and operator indices are pinned, preserving source clipping/paint/programs and physical math, while no tight ancestor is stranded. No source grade/column motion or global tolerance change.'
  bindings.append(dict(baseline=y,source_clip=c['clip_rects'][0],outer_original_operator_indices=c['operator_indices'],complete_original_native_glyphs=len(gs)))
 p['reviewed_complete_original_grading_row_clips']=bindings;P.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8');print('IZHO2016_COMPLETE_ORIGINAL_GRADING_ROW_CLIPS_BOUND',n,len(bindings),flush=True)
