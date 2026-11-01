from pathlib import Path
import sys,json,hashlib
import pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_native_inline_reposition import reposition_inline,_traces
from pdf_native_script_motion_audit import audit
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
f=B/'natural/2020/TS';out=B/'2020/expression-negative';out.mkdir(exist_ok=True);rows=[]
for n,x,y in [(8,175.32000732421875,450.8399963378906),(9,300.3599853515625,105.719970703125)]:
 plan=json.loads((f/f'plans/page{n:02}.json').read_text('utf8'));q=json.loads((f/f'page{n:02}.qa.json').read_text('utf8'));target=f/f'page{n:02}.pdf';source=f/f'page{n:02}.old-source.pdf'
 groups=[dict(label=a['reviewed_reason'],glyphs=a['glyphs'])for a in q.get('reviewed_explicit_native_math_atoms',[])]+plan.get('reviewed_stationary_expression_groups',[])+plan.get('reviewed_native_expression_groups',[])
 with fitz.open(source)as doc:
  source_glyphs=_traces(doc[0]);g=next(v for v in source_glyphs if v['trace_gid']>=0 and v['font']=='CambriaMath'and abs(v['origin'][0]-x)<.01 and abs(v['origin'][1]-y)<.01)if n==8 else next(v for a in q['reviewed_explicit_native_math_atoms']if 'numerical pressure expression'in a['reviewed_reason']for v in a['glyphs']if v['c']=='1'and v['trace_gid']>=0)
 old_moves={glyph_key(v):s['dx']for s in q['native_shifts']for v in s['glyphs']};dx=old_moves.get(glyph_key(g),0.)
 with fitz.open(target)as doc:actual=next(v for v in _traces(doc[0])if v['c']==g['c']and v['font']==g['font']and v['trace_gid']==g['trace_gid']and abs(v['origin'][0]-g['origin'][0]-dx)<.001 and abs(v['origin'][1]-g['origin'][1])<.001)
 try:raw,move=reposition_inline(target,1,shifts=[dict(glyphs=[actual],dx=.5)])
 except ValueError as error:
  if n!=9 or str(error)!='Native shift would leave an unchanged clip; select its complete clip group':raise
  rows.append(dict(page=n,canonical_proof_sha256=sha(target),publication_pdf_unmodified=True,attempted_source_math_glyph=g,attempted_partial_glyph_shift_pt=.5,native_encoder_rejected_partial_clip_motion=True,rejection=str(error),analysis_clone_created=False,passed=True));print('PARTIAL_MATH_CLIP_MOTION_REJECTED',n,flush=True);continue
 negative=out/f'page{n:02}-one-math-piece-right-halfpoint.pdf';negative.write_bytes(raw)
 protected=json.loads((f/f'page{n:02}.audit.json').read_text('utf8'))['native_script_motion_audit']['source_physical_glyphs']
 with fitz.open(plan['original_english_source'])as original:
  physical_keys={(glyph_key(v),v['trace_gid'],v['render_mode'])for v in _traces(original[n-1])if v['c'].strip()and v['trace_gid']>=0}
 physical=[v for v in source_glyphs if(glyph_key(v),v['trace_gid'],v['render_mode'])in physical_keys and v['c'].strip()];assert len(physical)==protected
 shifts=[]
 for s in q['native_shifts']:
  gs=[v for v in s['glyphs']if glyph_key(v)!=glyph_key(g)]
  if gs:shifts.append(dict(s,glyphs=gs))
 shifts.append(dict(glyphs=[g],dx=dx+.5))
 r=audit(source,1,negative,shifts=shifts,native_glyphs=physical,expression_groups=groups,excluded_script_origins=plan.get('reviewed_script_exclusions',[]));assert not r['passed']and not r['glyph_signature_or_position_errors']and any(not a['passed']and abs(a['relative_x_spread_pt']-.5)<.001 for a in r['reviewed_expression_groups'])
 report=out/f'page{n:02}-math-piece.audit.json';report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf8')
 rows.append(dict(page=n,canonical_proof_sha256=sha(target),publication_pdf_unmodified=True,actual_one_source_math_glyph_shift_pt=.5,all_original_fonts_gids_points_baselines_and_graphics_retained=move['passed']and move['font_programs_unchanged']and move['original_image_streams_unchanged']and move['native_vector_path_bytes_preserved'],all_changed_glyphs_honestly_reported_in_negative_journal=True,native_glyph_signature_position_errors=0,independent_complete_expression_geometry_rejected=True,raw_negative_audit=str(report),raw_negative_audit_sha256=sha(report),native_move_qa=move,passed=True));print('REAL_MATH_PIECE_NEGATIVE_REJECTED',n,flush=True)
(out/'regression.json').write_text(json.dumps(dict(passed=True,rows=rows),ensure_ascii=False,indent=2)+'\n','utf8')
