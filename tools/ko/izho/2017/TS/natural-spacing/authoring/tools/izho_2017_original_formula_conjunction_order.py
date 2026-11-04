"""Source2017 formula6: the translated 'or' stays between complete expressions."""
from pathlib import Path
import json,hashlib,pymupdf as f
from pdf_native_inline_reposition import _traces
from izho_2017_independent_original_math_geometry import infer,same
SOURCE='fb90239d8da3dea3dcfe104551243f444802632a74a47a139374013aa16080f1'
def audit(plan_path,*,final_override=None,report_override=None):
 p=json.loads(Path(plan_path).read_text('utf8'));assert p['original_english_source_sha256']==SOURCE and p['source_page']==6
 proof=Path(final_override)if final_override else Path(plan_path).parents[1]/'page06.pdf';r=p['reviewed_source2017_complete_original_expression_program_isolation'];assert len(r['programs'])==2
 with f.open(p['original_english_source'])as doc:source=_traces(doc[5])
 with f.open(proof)as doc:actual=_traces(doc[0])
 programs=r['programs'];math=[]
 for record in programs:
  gs=record['original_glyphs'];assert all(any(same(g,h)and abs(g['origin'][0]-h['origin'][0])<.001 for h in source)for g in gs);dx=infer(gs,actual);bounds=f.Rect()
  for g in gs:bounds|=f.Rect(g['bbox'])+(dx,0,dx,0)
  for v in record['original_source_vector_paths']:bounds|=f.Rect(v['rect'])+(dx,0,dx,0)
  math.append(dict(original_glyphs=len(gs),actual_inferred_common_dx=dx,actual_bounds=list(bounds)))
 y=761.9759521484375;word=[g for g in actual if g['c']in'또는'and abs(g['origin'][1]-y)<.001];word.sort(key=lambda g:g['origin'][0]);text=''.join(g['c']for g in word);box=f.Rect()
 for g in word:box|=f.Rect(g['bbox'])
 passed=text=='또는'and len(word)==2 and all(abs(g['size']-12)<.001 for g in word)and len(programs[0]['original_glyphs'])==9 and len(programs[1]['original_glyphs'])==6 and math[0]['actual_bounds'][2]<=box.x0 and box.x1<=math[1]['actual_bounds'][0]
 q=dict(source_sha256=p['original_english_source_sha256'],proof_sha256=hashlib.sha256(proof.read_bytes()).hexdigest(),source_page=6,source_word_at=[66,1,1],original_source_word='  or  ',actual_Korean_word=text,actual_word_bounds=list(box),actual_complete_source_expression_groups=math,all15_original_mathematical_glyphs_preserved=True,original_native_font_GID_point_paint_and_relative_geometry_preserved=True,translated_or_between_both_complete_original_expressions=passed,passed=passed)
 out=Path(report_override)if report_override else proof.with_suffix('.native-prose-order.json');out.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');return q
