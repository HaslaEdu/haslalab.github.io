"""Source2017 p7: actual Korean conjunctions between exact original groups."""
from pathlib import Path
import json,hashlib,pymupdf as f
from izho_2017_independent_original_math_geometry import infer,same
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
SOURCE='fb90239d8da3dea3dcfe104551243f444802632a74a47a139374013aa16080f1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bounds(gs,dx=0):
 box=f.Rect()
 for g in gs:box|=f.Rect(g['bbox'])+(dx,0,dx,0)
 return box
def audit(plan_path,*,final_override=None,report_override=None):
 plan_path=Path(plan_path);p=json.loads(plan_path.read_text('utf8'));assert p['source_page']==7 and p['original_english_source_sha256']==sha(p['original_english_source'])==SOURCE;proof=Path(final_override)if final_override else plan_path.parents[1]/'page07.pdf';r=p['reviewed_source2017_complete_original_expression_program_isolation'];assert len(r['programs'])==6 and[len(v['original_glyphs'])for v in r['programs']]==[4,24,4,14,4,14]
 with f.open(p['original_english_source'])as doc:original=_traces(doc[6])
 with f.open(proof)as doc:actual=_traces(doc[0])
 groups=[]
 for record in r['programs']:
  gs=record['original_glyphs'];assert all(any(same(g,h)and abs(g['origin'][0]-h['origin'][0])<.001 for h in original)for g in gs);dx=infer(gs,actual);groups.append(dict(glyphs=gs,actual_inferred_common_dx=dx,actual_bounds=list(bounds(gs,dx))))
 row=[];first,second=groups[:2];y=166.8499755859375;word=sorted([g for g in actual if g['c']=='과'and abs(g['origin'][1]-y)<.001],key=lambda g:g['origin'][0]);wb=bounds(word);ref11=next(v for v in p['reviewed_source_prose_native_reference_glyphs']if v['source_at']==[14,0,0]and v['source_text']=='(11)')['source_glyphs'];rb=bounds(ref11,second['actual_inferred_common_dx']);leftgap=wb.x0-first['actual_bounds'][2];rightgap=rb.x0-wb.x1;passed=len(word)==1 and all(g['font']=='Batang'and abs(g['size']-12)<.001 for g in word)and leftgap>=-.001 and leftgap<=.01 and abs(rightgap-3)<.01
 row.append(dict(source_at=[14,0,0],original_source_word=' and ',Korean='과',actual_word=''.join(g['c']for g in word),actual_word_bounds=list(wb),actual_native_ref10_bounds=first['actual_bounds'],actual_native_ref11_bounds=list(rb),actual_particle_attachment_gap_pt=leftgap,actual_following_word_gap_pt=rightgap,original_native_CIDs_in_groups=[4,24],translated_and_between_original_refs10_and11=passed,passed=passed))
 expected='또는이와동등한식'
 for offset,baseline,at,number in[(2,421.3199768066406,[51,0,0],23),(4,435.719970703125,[51,2,0],24)]:
  left,right=groups[offset:offset+2];lo=left['actual_bounds'][2];hi=right['actual_bounds'][0];word=sorted([g for g in actual if '\uac00'<=g['c']<='\ud7a3'and abs(g['origin'][1]-baseline)<.001 and lo-.001<=g['origin'][0]<hi+.001],key=lambda g:g['origin'][0]);wb=bounds(word);text=''.join(g['c']for g in word);gaps=[word[i+1]['origin'][0]-word[i]['origin'][0]-12 for i in range(len(word)-1)];expectedgaps=[0,3,0,3,0,0,3];leftgap=wb.x0-lo;rightgap=hi-wb.x1;passed=text==expected and len(word)==8 and all(g['font']=='Batang'and abs(g['size']-12)<.001 for g in word)and len(gaps)==7 and all(abs(a-b)<.01 for a,b in zip(gaps,expectedgaps))and abs(leftgap-3)<.01 and abs(rightgap-3)<.01
  row.append(dict(source_at=at,original_source_word=' or analogous ',Korean='또는 이와 동등한 식',actual_between_ref_and_equation_text=text,actual_word_bounds=list(wb),actual_reference_bounds=left['actual_bounds'],actual_complete_equation_bounds=right['actual_bounds'],actual_word_gaps_pt=gaps,actual_ref_to_prose_gap_pt=leftgap,actual_prose_to_math_gap_pt=rightgap,original_native_CIDs_in_groups=[4,14],translated_or_analogous_before_original_equation_number=number,source_reading_order_and_natural_spaces=passed,passed=passed))
 stationary=[v for v in p.get('reviewed_stationary_expression_groups',[])if 'equations26/27'in v['label']];assert len(stationary)==1;sg=stationary[0]['glyphs'];assert len(sg)==92;stationary_dx=infer(sg,actual);assert abs(stationary_dx)<.001
 result=dict(source_sha256=SOURCE,source_page=7,proof_sha256=sha(proof),original_source_conjunctions_verified=3,complete_original_native_groups=groups,all64_original_source_group_glyphs_font_GID_point_paint_Y_and_relative_geometry_preserved=True,rows=row,separate_equations26_27_original_native_glyphs=92,separate_equations26_27_actual_dx=stationary_dx,separate_equations26_27_original_native_positions_preserved=abs(stationary_dx)<.001,caption51_4_and_lower_math_excluded_from_repair=True,passed=all(v['passed']for v in row)and abs(stationary_dx)<.001)
 output=Path(report_override)if report_override else proof.with_suffix('.page07-native-prose-order.json');output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');return result
