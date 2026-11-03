"""Closed2019 source profile for literal U+0020 CambriaMath GID1318 ink.

This is an original arrowhead CID, not a nonpainting prose space. No Unicode,
font, drawing, clipping or shared native guard is modified. Complete original
program Forms/Word clips already move the paint. Include its exact original
motion in the journal so the ordinary ink-envelope audit sees that paint.
"""
from pathlib import Path
from io import BytesIO
import hashlib,json,pymupdf as f
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
SOURCE='5e83000f5d2abe161186a6f81e5b9cd306a0758d2969744edbfb68fcad413da8'
COUNTS={4:14,5:4,6:10,7:4}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def expected_heads(plan,composition):
 assert plan['original_english_source_sha256']==sha(plan['original_english_source'])==SOURCE
 n=plan['source_page']
 with f.open(plan['original_english_source'])as original,f.open(plan['source_base'])as source:
  official=[g for g in _traces(original[n-1])if g['c']==' 'and g['font']=='CambriaMath'and g['trace_gid']==1318]
  rows=_traces(source[plan['page']-1]);heads=[g for g in rows if g['c']==' 'and g['font']=='CambriaMath'and g['trace_gid']==1318]
 assert len(official)==len(heads)==COUNTS.get(n,0)
 shifts={glyph_key(g):s['dx']for s in composition['native_shifts']for g in s['glyphs']if g['c'].strip()};result=[]
 for head in heads:
  assert head['size']==12 and head['render_mode']==0 and head['opacity']==1
  matches=[g for g in official if all(g.get(k)==head.get(k)for k in['c','font','trace_gid','render_mode','color','opacity','direction'])and abs(g['size']-head['size'])<.0001 and max(abs(a-b)for a,b in zip(g['origin'],head['origin']))<.0001];assert len(matches)==1
  owners=[a for a in plan.get('explicit_native_math_atoms',[])if f.Rect(a['rect']).contains(f.Point(head['origin']))];assert len(owners)<=1
  owner=owners[0]if owners else None;values=[shifts.get(glyph_key(g),0.)for g in owner['source_native_glyphs']]if owner else[0.];assert max(values)-min(values)<.001;dx=values[0]
  if abs(dx)>.000001:
   assert owner and(owner.get('use_complete_original_clip')or(n==4 and owner.get('source_form_path')is not None and plan.get('reviewed_complete_original_painted_space_arrow_programs'))),'A painted arrowhead must move only in its complete original source program or complete original Word clip'
  result.append(dict(glyph=head,official_source_glyph=matches[0],dx=dx,owner_source_form_path=owner.get('source_form_path')if owner else None,owner_original_clip_operator_indices=owner.get('source_complete_clip_operator_indices')if owner else None,literal_U0020_and_GID1318_preserved=True))
 return result
def annotate(plan,composition,raw):
 expected=expected_heads(plan,composition)
 with f.open(stream=raw,filetype='pdf')as doc:actual=_traces(doc[0])
 records=[];existing={glyph_key(g)for s in composition['native_shifts']for g in s['glyphs']}
 for row in expected:
  g=row['glyph'];hits=[h for h in actual if all(h.get(k)==g.get(k)for k in['c','font','trace_gid','render_mode','color','opacity','direction'])and abs(h['size']-g['size'])<.001 and abs(h['origin'][1]-g['origin'][1])<.001 and abs(h['origin'][0]-g['origin'][0]-row['dx'])<.001];assert len(hits)==1,(g,row['dx'],hits)
  if abs(row['dx'])>.000001 and glyph_key(g)not in existing:
   composition['native_shifts'].append(dict(glyphs=[g],dx=row['dx'],reviewed_literal_original_U0020_GID1318_arrowhead=True,paint_already_moved_in_complete_original_Form_or_Word_clip=True));existing.add(glyph_key(g))
  records.append(dict(row,actual_final_glyph=hits[0],actual_native_CID_font_GID_point_paint_X_Y_passed=True))
 composition['reviewed_original_painted_arrowhead_CID_motion']=dict(source_sha256=SOURCE,source_page=plan['source_page'],literal_original_U0020_CIDs_checked=len(expected),literal_original_painted_space_GID=1318,actual_native_physical_glyphs_and_source_program_ownership_verified=True,ordinary_ink_envelope_uses_these_actual_CID_origins=True,rows=records,no_PDF_paint_modified_by_this_journal_annotation=True)
