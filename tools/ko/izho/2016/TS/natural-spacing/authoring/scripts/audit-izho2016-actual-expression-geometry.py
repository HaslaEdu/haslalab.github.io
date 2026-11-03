"""Independent actual output CIDs and source paths; journal is a locator only."""
from pathlib import Path
import hashlib,json,sys,re,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces,inspect_inline_groups
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def normalize(v,dx=0):
 if isinstance(v,f.Point):return[v.x+dx,v.y]
 if isinstance(v,f.Rect):return[v.x0+dx,v.y0,v.x1+dx,v.y1]
 if isinstance(v,f.Quad):return[normalize(x,dx)for x in[v.ul,v.ur,v.ll,v.lr]]
 if isinstance(v,(list,tuple)):return[normalize(x,dx)for x in v]
 if isinstance(v,float):return v
 return v
def equal(a,b):
 if isinstance(a,(int,float))and isinstance(b,(int,float)):return abs(a-b)<=.001
 if isinstance(a,list)and isinstance(b,list):return len(a)==len(b)and all(equal(x,y)for x,y in zip(a,b))
 if isinstance(a,dict)and isinstance(b,dict):return a.keys()==b.keys()and all(equal(a[k],b[k])for k in a)
 return a==b
def signature(d,dx=0):return {k:normalize(d.get(k),dx if k=='items'else 0)for k in['items','type','color','fill','width','closePath','dashes','lineCap','lineJoin','fill_opacity','stroke_opacity','even_odd']}
def audit(n,override=None,report=None):
 P=B/f'natural/2016/TS/plans/page{n:02}.json';p=json.loads(P.read_text('utf8'));pdf=Path(override)if override else P.parents[1]/f'page{n:02}.pdf';q=json.loads((P.parents[1]/f'page{n:02}.qa.json').read_text('utf8'))
 assert p['original_english_source_sha256']==sha(p['original_english_source'])=='19f23f790b5dd43bf2303f4b597da862c5d17a0267320fee3cca7f5f015a1df8'
 moves={glyph_key(g):s['dx']for s in q['native_shifts']for g in s['glyphs']};results=[]
 final_forms=inspect_inline_groups(str(pdf),1)['forms']if p.get('reviewed_complete_original_mathematical_form_bindings')else[]
 with f.open(p['original_english_source'])as source,f.open(pdf)as final:
  old=source[n-1];new=final[0];actual=_traces(new);original_drawings=old.get_drawings();target_drawings=new.get_drawings();target_signatures=[signature(d)for d in target_drawings]
  for a in p.get('explicit_native_math_atoms',[]):
   gs=a['source_native_glyphs'];values=[moves.get(glyph_key(g),0.)for g in gs];dx=values[0];missing=[]
   for g in gs:
    hits=[h for h in actual if all(normalize(h.get(k))==normalize(g.get(k))for k in['c','font','trace_gid','render_mode','color','opacity','direction','wmode'])and abs(h['size']-g['size'])<.001 and abs(h['origin'][1]-g['origin'][1])<.001 and abs(h['origin'][0]-g['origin'][0]-dx)<.001]
    if not hits:missing.append(g)
   box=f.Rect(a['rect']);paths=[d for d in original_drawings if box.contains(f.Rect(d['rect']))and(not a.get('source_grid_table_math')or(f.Rect(d['rect']).height<2 and f.Rect(d['rect']).width<box.width*.8))];pathrows=[]
   for path in paths:
    wanted=signature(path,dx);matches=[i for i,s in enumerate(target_signatures)if equal(s,wanted)]
    pathrows.append(dict(source_rect=list(path['rect']),expected_dx=dx,expected_final_rect=list(f.Rect(path['rect'])+(dx,0,dx,0)),actual_complete_path_matches=len(matches),passed=bool(matches)))
   formcheck=None
   if a.get('source_form_path')is not None:
    bindings=[b for b in p['reviewed_complete_original_mathematical_form_bindings']if b['path']==a['source_form_path']];assert len(bindings)==1;binding=bindings[0];bb=f.Rect(binding['original_form_bbox'])+(dx,0,dx,0)
    candidates=[v for v in final_forms if v['original_raw_sha256']==binding['original_form_program_sha256']and max(abs(x-y)for x,y in zip(v['native_page_bbox'],bb))<.001]
    formcheck=dict(original_source_Form_raw_program_sha256=binding['original_form_program_sha256'],original_source_Form_bbox=binding['original_form_bbox'],expected_final_Form_bbox=list(bb),actual_final_same_raw_program_and_exact_translated_CTM_matches=len(candidates),passed=bool(candidates))
   results.append(dict(label=a['reason'],source_rect=a['rect'],original_native_glyphs=len(gs),declared_dx=dx,actual_native_CID_font_GID_point_paint_Y_and_X_errors=missing,declared_glyph_dx_spread=max(values)-min(values),actual_original_paths=pathrows,complete_original_Form_program_and_actual_geometry=formcheck,passed=not missing and max(values)-min(values)<.001 and all(r['passed']for r in pathrows)and(formcheck is None or formcheck['passed'])))
  score_errors=[];score_count=0
  for region in p.get('stationary_table_math',[]):
   for g in region['native_glyphs']:
    score_count+=1
    if not any(all(normalize(h.get(k))==normalize(g.get(k))for k in['c','font','trace_gid','render_mode','color','opacity'])and abs(h['size']-g['size'])<.001 and max(abs(a-b)for a,b in zip(h['origin'],g['origin']))<.001 for h in actual):score_errors.append(g)
 result=dict(source_sha256=p['original_english_source_sha256'],proof_sha256=sha(pdf),plan_sha256=sha(P),source_page=n,method='Read actual final native CID/GID/font/point/paint/Y/X and every complete original source graphical path inside each human-reviewed expression bounds. Declared motion is only a coordinate locator; actual final path geometry and actual final native text must independently match the original transformed by exactly that one dx. Original score/separate-display glyphs independently checked at exact original x/y. No PDF changes or threshold changes.',groups=results,complete_groups_checked=len(results),native_glyphs_checked=sum(r['original_native_glyphs']for r in results),actual_source_graphical_paths_checked=sum(len(r['actual_original_paths'])for r in results),stationary_score_and_display_glyphs_checked=score_count,stationary_glyph_errors=score_errors,passed=all(r['passed']for r in results)and not score_errors)
 output=Path(report)if report else pdf.with_suffix('.actual-expression-geometry.json');output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');return result
if __name__=='__main__':
 for n in map(int,sys.argv[1:]):
  with page_worker():q=audit(n)
  print('IZHO2016_ACTUAL_EXPRESSION_GEOMETRY',n,q['passed'],q['complete_groups_checked'],q['native_glyphs_checked'],q['actual_source_graphical_paths_checked'],flush=True)
  assert q['passed']
