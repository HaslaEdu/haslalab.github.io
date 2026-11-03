"""Actual new prose punctuation/Latin CIDs must not obscure original math/graphics."""
from pathlib import Path
import json,hashlib,pymupdf as f
from initial_prose_reading_order import journal
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from pdf_new_prose_native_text_overlap import audit as text_overlap
from pdf_new_hangul_graphics_overlap import audit as graphics_overlap
def audit(plan_path):
 plan_path=Path(plan_path);p=json.loads(plan_path.read_text('utf8'));pdf=plan_path.parents[1]/f"page{p['page']:02}.pdf";q=json.loads(pdf.with_suffix('.qa.json').read_text('utf8'));assert p['original_english_source_sha256']=='5e83000f5d2abe161186a6f81e5b9cd306a0758d2969744edbfb68fcad413da8'
 with f.open(p['source_base'])as old,f.open(pdf)as final:
  authored=journal(old[p['page']-1],p['prose_placements']);keys={glyph_key(g)for row in authored for g in row['glyphs']if g['c'].strip()};source=_traces(old[p['page']-1]);actual=_traces(final[0]);native=[g for g in source if g['c'].strip()and glyph_key(g)not in keys];selected=[g for g in source if glyph_key(g)in keys and g['c'].strip()and not(0xac00<=ord(g['c'])<=0xd7a3)];shifts={glyph_key(g):s['dx']for s in q['native_shifts']for g in s['glyphs']};target=[]
  for g in selected:
   dx=shifts.get(glyph_key(g),0.);hits=[a for a in actual if a['c']==g['c']and a['font']==g['font']and a['trace_gid']==g['trace_gid']and a['render_mode']==g['render_mode']and abs(a['size']-g['size'])<.001 and abs(a['origin'][1]-g['origin'][1])<.001 and abs(a['origin'][0]-g['origin'][0]-dx)<.001]
   if len(hits)!=1:raise ValueError(('Final authored punctuation/Latin CID does not resolve uniquely',g,dx,len(hits)))
   target.append(hits[0])
 text=text_overlap(pdf,native_glyphs=native,shifts=q['native_shifts'],prose_glyphs=target);graphics=graphics_overlap(pdf,new_glyphs=target);result=dict(source_sha256=p['original_english_source_sha256'],proof_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),new_non_Hangul_prose_glyphs=len(target),method='Exact authored initial prose suffix and actual final native-CID/GID/font/point/paint/baseline/motion identify every new prose punctuation/Latin glyph. Actual independent outline ink versus all retained native text and original clip-aware non-text graphics; strict zero overlap.',native_text_overlap=text,native_graphics_overlap=graphics,passed=text['passed']and graphics['passed']);pdf.with_suffix('.non-hangul-prose-collision.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');return result
