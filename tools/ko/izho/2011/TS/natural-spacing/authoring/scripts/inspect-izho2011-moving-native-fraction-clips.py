from pathlib import Path
import sys,json,hashlib
import pymupdf as f
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from pdf_native_inline_reposition import inspect_inline_groups,_traces
from pdf_original_text_ops import glyph_key
F=B/'natural/2011/TS';result=[]
for n in range(1,11):
 p=json.loads((F/f'plans/page{n:02}.json').read_text('utf8'));q=json.loads((F/f'page{n:02}.qa.json').read_text('utf8'));inv=inspect_inline_groups(p['source_base'],n)
 with f.open(p['original_english_source'])as original:original_keys={glyph_key(g)for g in _traces(original[n-1])if g['c'].strip()}
 shifts={glyph_key(g):s['dx']for s in q['native_shifts']for g in s['glyphs']}
 for clip in inv['clip_groups']:
  rects=clip.get('clip_rects',[])
  if not clip.get('known_rectangular_clips')or len(rects)!=1:continue
  box=f.Rect(rects[0]);gs=[g for g in clip['glyphs']if g['c'].strip()and g.get('trace_gid',g.get('gid',-1))>=0]
  if not gs or box.height>70 or box.width>490 or any(glyph_key(g)not in original_keys for g in gs):continue
  paths=[v for v in inv['vector_paths']if box.contains(f.Rect(v['rect']))and f.Rect(v['rect']).width>1 and f.Rect(v['rect']).height<2]
  if not paths:continue
  values=[shifts.get(glyph_key(g),0.)for g in gs]
  if max(abs(x)for x in values)<.001:continue
  row=dict(page=n,source_base=p['source_base'],source_base_sha256=p['source_base_sha256'],clip_rect=rects[0],clip_operator_indices=clip['operator_indices'],source_text=''.join(g['c']for g in sorted(gs,key=lambda g:(g['origin'][0],g['origin'][1]))),native_glyphs=gs,fraction_paths=paths,minimum_declared_glyph_dx=min(values),maximum_declared_glyph_dx=max(values),source_clip_glyph_dx_spread=max(values)-min(values))
  result.append(row);print('MOVING_ORIGINAL_NATIVE_FRACTION_CLIP',n,rects[0],len(gs),len(paths),round(min(values),5),round(max(values),5),row['source_text'],flush=True)
(B/'2011/inspection/moving-original-native-fraction-clips.json').write_text(json.dumps(dict(source_sha256='ecc4a34a50fade6a08fd5f629480bebfa20ec418cdc19fa87915f6c0465ee008',source_only_clip_membership_inventory=True,review_required=True,rows=result),ensure_ascii=False,indent=2)+'\n','utf8');print('NATIVE_FRACTION_CLIPS_REQUIRING_EXPLICIT_REVIEW',len(result),flush=True)
