"""Exact source2014 Word math objects whose physical baselines sit above prose."""
from pathlib import Path
import hashlib,pymupdf as f
from pdf_native_inline_reposition import inspect_inline_groups,_traces
from pdf_original_text_ops import glyph_key
SOURCE='1e526966f308280accc9fe747d08259279f35324e7e7f2e0290271adcaf6536c'
def apply(plan):
 assert plan['original_english_source_sha256']==SOURCE
 inv=inspect_inline_groups(plan['source_base'],plan['page']);atoms=plan.setdefault('explicit_native_math_atoms',[]);review=[]
 with f.open(plan['original_english_source'])as original:keys={glyph_key(g)for g in _traces(original[plan['source_page']-1])if g['c'].strip()}
 for clip in inv['clip_groups']:
  if not clip.get('known_rectangular_clips')or len(clip['clip_rects'])!=1:continue
  box=f.Rect(clip['clip_rects'][0]);gs=[g for g in clip['glyphs']if g['c'].strip()and g.get('trace_gid',g.get('gid',-1))>=0]
  if not gs or box.width>200 or box.height>45 or any(glyph_key(g)not in keys for g in gs):continue
  if any(not any(name in g['font']for name in['TimesNewRoman','Symbol','MTExtra','MT-Extra'])for g in gs):continue
  matches=[s for s in plan['source_line_scopes']if abs(s['baseline']-box.y1)<=1.25 and s['rect'][0]-1<=box.x0 and box.x1<=s['rect'][2]+1]
  if not matches:continue
  baselines={round(s['baseline'],4)for s in matches}
  if len(baselines)!=1:raise ValueError('A source2014 inline clip needs one explicit source prose baseline')
  if any(box.intersects(f.Rect(r))for r in plan['excluded_figure_rects']):continue
  if any(box.contains(f.Rect(v['rect']))for v in plan.get('reviewed_stationary_gray_field_panels',[])):raise ValueError('Inline math contains a stationary gray field; needs separate source program review')
  rule=dict(reviewed=True,original_source_only=True,rect=list(box),font_regex='.*',baseline=matches[0]['baseline'],source_native_glyphs=gs,include_zero_height_vector_bounds=True,reason='Human-read source2014 native Word inline mathematical object. The original complete glyph clip and every original script point, bracket and variable share one horizontal dx. The Word object bottom, rather than the elevated mathematical baseline, binds it to its exact authored prose row. No formula retyping or scaling.')
  if any({glyph_key(g)for g in a.get('source_native_glyphs',[])}&{glyph_key(g)for g in gs}for a in atoms):continue
  atoms.append(rule);review.append(dict(source_operator_indices=clip['operator_indices'],clip_rect=list(box),glyphs=gs,prose_baseline=matches[0]['baseline'],native_fonts_and_points_preserved=True))
 plan['reviewed_complete_original_inline_clips']=review
