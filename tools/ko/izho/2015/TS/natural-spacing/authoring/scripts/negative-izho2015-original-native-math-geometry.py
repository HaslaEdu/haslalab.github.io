from pathlib import Path
import sys,json,hashlib,pikepdf,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');F=B/'natural/2015/TS';O=B/'natural/2015-native-geometry-negatives';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups,reposition_inline,_traces,_raw_regions,_replace
from izho_2015_independent_original_math_geometry import audit,same,translated
from izho_2015_equation_counters import source_counters,audit as counter_audit
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'));rows=[]
def badcase(ident,n,make,check=audit):
 with page_worker():
  proof=F/f'page{n:02}.pdf';pin=sha(proof);out=O/ident;out.mkdir(parents=True,exist_ok=True);bad=out/proof.name;assert not bad.exists()
  note=make(proof,bad);assert bad.exists()and sha(bad)!=pin
  q=check(F/f'plans/page{n:02}.json',final_override=bad,report_override=out/'independent-rejection.json');assert not q['passed']and sha(proof)==pin
  rows.append(dict(id=ident,source_page=n,proof_sha256=pin,mutant_sha256=sha(bad),negative_rejected=True,delivered_proof_unmodified=True,mutation=note))
 print('ORIGINAL2015_ACTUAL_BAD_NATIVE_PDF_REJECTED',ident,flush=True)
def fraction_bar_only(proof,bad):
 p=load(F/'plans/page05.json');q=load(proof.with_suffix('.independent-original-math-geometry.json'));r=p['reviewed_independent_original_expression_geometry_profiles'][4];dx=q['profiles'][4]['independently_inferred_common_dx'];source=next(v for v in r['original_vector_paths']if 8<v['rect'][2]-v['rect'][0]<80 and v['rect'][3]-v['rect'][1]<2);inv=inspect_inline_groups(proof,1);hits=[v for v in inv['vector_paths']if translated(source['rect'],v['rect'],dx)and v['paint_operator']==source['paint_operator']];assert len(hits)==1
 # The production helper correctly rejects an empty-glyph path-only group.
 # This deliberate bad-PDF control therefore wraps only the literal original
 # native bar program; no production helper or guard is changed.
 indices=hits[0]['operator_indices'];assert len(indices)==2 and indices[1]==indices[0]+1
 with pikepdf.open(proof)as doc:
  raw,regions=_raw_regions(doc.pages[0]);a,b=indices;first=raw[regions[a][0]:regions[a][1]];last=raw[regions[b][0]:regions[b][1]];doc.pages[0].Contents=doc.make_stream(_replace(doc.pages[0],{a:b'q 1 0 0 1 6 0 cm '+first,b:last+b' Q'}));doc.save(bad,compress_streams=False)
 actual=inspect_inline_groups(bad,1);assert any(translated(hits[0]['rect'],v['rect'],6.)for v in actual['vector_paths'])
 return dict(actual_native_fraction_rule_alone_shifted_pt=6.,source_rule=source,all_math_glyphs_and_motion_metadata_unchanged=True)
def fraction_glyphs_without_bars(proof,bad):
 p=load(F/'plans/page05.json');q=load(proof.with_suffix('.independent-original-math-geometry.json'));r=p['reviewed_independent_original_expression_geometry_profiles'][4];dx=q['profiles'][4]['independently_inferred_common_dx']
 with f.open(proof)as doc:actual=_traces(doc[0])
 gs=[]
 numerator=next(g for g in r['original_glyphs']if g['c']=='𝑝'and g['size']<10)
 chosen=[g for g in r['original_glyphs']if abs(g['origin'][1]-numerator['origin'][1])<3 and numerator['origin'][0]-.01<=g['origin'][0]<=numerator['origin'][0]+8 and g['c']in['𝑝','0']]
 for g in chosen:
  hits=[a for a in actual if same(g,a)and abs(a['origin'][0]-g['origin'][0]-dx)<.001];assert len(hits)==1;gs.append(hits[0])
 raw,motion=reposition_inline(proof,1,shifts=[dict(glyphs=gs,dx=-6.)]);bad.write_bytes(raw);(bad.parent/'guarded-mutation.json').write_text(json.dumps(motion,indent=2),'utf8');return dict(actual_original_fraction_numerator_glyphs_shifted_pt=-6.,whole_expression_relative_geometry_broken=True,mathematical_fonts_GIDs_points_paint_Y_unchanged=True)
def form_point_damage(proof,bad):
 p=load(F/'plans/page01.json');r=p['reviewed_independent_original_expression_geometry_profiles'][0]['original_form'];inv=inspect_inline_groups(proof,1);matches=[v for v in inv['forms']if v['original_raw_sha256']==r['original_raw_sha256']];assert len(matches)==1;path=matches[0]['path']
 with pikepdf.open(proof)as doc:
  node=doc.pages[0]
  for index in path:
   ops=pikepdf.parse_content_stream(node);inst=ops[index];assert str(inst.operator)=='Do';node=node.Resources.XObject[inst.operands[0]]
  ops=pikepdf.parse_content_stream(node);index=next(i for i,v in enumerate(ops)if str(v.operator)=='Tf');args=list(ops[index].operands);before=float(args[1]);args[1]=before+1.5;ops[index]=pikepdf.ContentStreamInstruction(args,pikepdf.Operator('Tf'));node.write(pikepdf.unparse_content_stream(ops));doc.save(bad,compress_streams=False)
 return dict(literal_original_Form_program_modified=True,actual_original_Tf_increment=1.5,original_Tf=before,original_Tm_linear_unchanged=True,mathematical_point_style_corrupted=True)
def counter_drift(proof,bad):
 p=load(F/'plans/page09.json');g=source_counters(p)[0]['glyphs'];raw,motion=reposition_inline(proof,1,shifts=[dict(glyphs=g,dx=-12.)]);bad.write_bytes(raw);return dict(actual_native_display_counter_drift_pt=-12.,original_fonts_GIDs_points_paint_Y_unchanged=True)
def covered_math():
 import izho_natural_spacing_qa as qa,contextlib
 with page_worker():
  proof=F/'page05.pdf';pin=sha(proof);root=O/'actual-native-math-covered-metadata-unchanged';folder=root/'2015/TS';(folder/'plans').mkdir(parents=True,exist_ok=True);bad=folder/proof.name;assert not bad.exists();plan=load(F/'plans/page05.json');comp=load(proof.with_suffix('.qa.json'));profile=plan['reviewed_independent_original_expression_geometry_profiles'][4];dx=load(proof.with_suffix('.independent-original-math-geometry.json'))['profiles'][4]['independently_inferred_common_dx'];g=next(g for g in profile['original_glyphs']if g['c']=='𝑥'and g['size']==12);box=f.Rect(g['bbox'])+(dx-.3,-.3,dx+.3,.3)
  with f.open()as doc:p=doc.new_page(width=595.32,height=841.92);p.draw_rect(box,fill=(1,1,1),color=None,width=0);overlay=folder/'actual-white-math-occlusion.pdf';doc.save(overlay)
  with pikepdf.open(proof)as doc,pikepdf.open(overlay)as over:doc.pages[0].add_overlay(over.pages[0]);doc.save(bad,compress_streams=False)
  comp['output_sha256']=sha(bad);bad.with_suffix('.qa.json').write_text(json.dumps(comp,ensure_ascii=False,indent=2),'utf8');(folder/'plans/page05.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),'utf8');prior=qa.BUILD;qa.BUILD=root
  with(folder/'actual-covered-ink-audit.log').open('w',encoding='utf8')as log,contextlib.redirect_stdout(log):
   try:qa.audit(2015,'TS',5)
   except ValueError:pass
   else:raise AssertionError('Actual original mathematical ink damage was accepted')
   finally:qa.BUILD=prior
  q=load(bad.with_suffix('.audit.json'));assert not q['passed']and q['actual_native_math_visible_ink_audit']['missing_actual_native_pixels']>0 and sha(proof)==pin
  rows.append(dict(id='actual-native-math-covered-metadata-unchanged',source_page=5,proof_sha256=pin,mutant_sha256=sha(bad),negative_rejected=True,delivered_proof_unmodified=True,all_original_glyph_font_GID_point_Y_metadata_unchanged=True,missing_actual_native_ink_pixels=q['actual_native_math_visible_ink_audit']['missing_actual_native_pixels']))
if __name__=='__main__':
 assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
 badcase('fraction-bar-only-motion',5,fraction_bar_only)
 badcase('actual-fraction-numerator-only-drift',5,fraction_glyphs_without_bars)
 badcase('actual-native-Form-mathematical-point-damage',1,form_point_damage)
 badcase('actual-native-displayed-counter-drift',9,counter_drift,counter_audit)
 covered_math()
 (O/'negative-controls.json').write_text(json.dumps(dict(rows=rows,passed=all(v['negative_rejected']and v['delivered_proof_unmodified']for v in rows),all_actual_bad_PDFs_rejected=True),indent=2)+'\n','utf8')
