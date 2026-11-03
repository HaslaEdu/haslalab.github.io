from pathlib import Path
import sys,json,hashlib,os,pikepdf,pymupdf as f,numpy as np,contextlib
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');F=B/'natural/2018/TS';O=B/'natural/2018-native-geometry-negatives';O.mkdir(exist_ok=True);sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups,reposition_inline,_traces,_raw_regions,_replace
from izho_2018_independent_original_math_geometry import audit,same,translated,infer
from izho_2018_equation_counters import source_counters,audit as counter_audit
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'));rows=[]
def profile8():return next(r for r in load(F/'plans/page08.json')['reviewed_independent_original_expression_geometry_profiles']if abs(r['logical_prose_baseline']-487.6299743652344)<.001)
def badcase(ident,n,make,check=audit):
 with page_worker():
  proof=F/f'page{n:02}.pdf';pin=sha(proof);out=O/ident;out.mkdir(parents=True,exist_ok=True);bad=out/proof.name
  if bad.exists():
   q=load(out/'independent-rejection.json');assert not q['passed']and q['proof_sha256']==sha(bad)and sha(bad)!=pin;rows.append(dict(id=ident,source_page=n,proof_sha256=pin,mutant_file=str(bad),mutant_sha256=sha(bad),independent_rejection_file=str(out/'independent-rejection.json'),negative_rejected=True,delivered_proof_unmodified=True,mutation=dict(reused_previously_inspected_actual_bad_PDF=True)));return
  note=make(proof,bad);assert bad.exists()and sha(bad)!=pin
  q=check(F/f'plans/page{n:02}.json',final_override=bad,report_override=out/'independent-rejection.json');assert not q['passed']and sha(proof)==pin
  rows.append(dict(id=ident,source_page=n,proof_sha256=pin,mutant_file=str(bad),mutant_sha256=sha(bad),independent_rejection_file=str(out/'independent-rejection.json'),negative_rejected=True,delivered_proof_unmodified=True,mutation=note))
 print('SOURCE2018_ACTUAL_BAD_NATIVE_PDF_REJECTED',ident,flush=True)
def fraction_bar_only(proof,bad):
 r=profile8()
 with f.open(proof)as doc:dx=infer(r['original_glyphs'],_traces(doc[0]))
 source=next(v for v in r['original_vector_paths']if 4<v['rect'][2]-v['rect'][0]<80 and v['rect'][3]-v['rect'][1]<2);inv=inspect_inline_groups(proof,1);hits=[v for v in inv['vector_paths']if translated(source['rect'],v['rect'],dx)and v['paint_operator']==source['paint_operator']];assert len(hits)==1;indices=hits[0]['operator_indices'];assert indices==list(range(min(indices),max(indices)+1))
 with pikepdf.open(proof)as doc:
  raw,regions=_raw_regions(doc.pages[0]);a,b=min(indices),max(indices);first=raw[regions[a][0]:regions[a][1]];last=raw[regions[b][0]:regions[b][1]];doc.pages[0].Contents=doc.make_stream(_replace(doc.pages[0],{a:b'q 1 0 0 1 6 0 cm '+first,b:last+b' Q'}));doc.save(bad,compress_streams=False)
 assert any(translated(hits[0]['rect'],v['rect'],6.)for v in inspect_inline_groups(bad,1)['vector_paths']);return dict(actual_native_fraction_bar_alone_shifted_pt=6.,source_rule=source,math_glyphs_and_metadata_unchanged=True)
def numerator_only(proof,bad):
 r=profile8()
 with f.open(proof)as doc:
  actual=_traces(doc[0]);dx=infer(r['original_glyphs'],actual);source=next(g for g in r['original_glyphs']if g['c']=='𝑝'and abs(g['origin'][0]-198.65)<.01 and g['size']<10);gs=[h for h in actual if same(source,h)and abs(h['origin'][0]-source['origin'][0]-dx)<.001];assert len(gs)==1;g=gs[0]
 inv=inspect_inline_groups(proof,1,include_text_shows=True);matches=[s for s in inv['top_level_text_shows']if any(glyph_key(h)==glyph_key(g)for p in s['parts']for h in p['glyphs'])];assert len(matches)==1;show=matches[0];assert sum(len(p['glyphs'])for p in show['parts'])==1;i=show['operator_index']
 with pikepdf.open(proof)as doc:
  raw,regions=_raw_regions(doc.pages[0]);original=raw[regions[i][0]:regions[i][1]];doc.pages[0].Contents=doc.make_stream(_replace(doc.pages[0],{i:b'q 1 0 0 1 -6 0 cm '+original+b' Q'}));doc.save(bad,compress_streams=False)
 with f.open(bad)as doc:assert any(same(g,h)and abs(h['origin'][0]-g['origin'][0]+6)<.001 for h in _traces(doc[0]))
 return dict(actual_native_fraction_numerator_only_drift_pt=-6.,native_font_GID_fractional_point_paint_Y_unchanged=True,whole_expression_geometry_deliberately_broken=True)
def form_point_damage(proof,bad):
 inv=inspect_inline_groups(proof,1);v=next(v for v in inv['forms']if v['original_raw_sha256']=='666a17a58619bd070f911acee1ef41eb56e506fe081cd31e05fb3dd0c6a39df5')
 with pikepdf.open(proof)as doc:
  node=doc.pages[0]
  for i in v['path']:op=pikepdf.parse_content_stream(node)[i];node=node.Resources.XObject[op.operands[0]]
  ops=pikepdf.parse_content_stream(node);i=next(i for i,v in enumerate(ops)if str(v.operator)=='Tf');args=list(ops[i].operands);before=float(args[1]);args[1]=before+1.5;ops[i]=pikepdf.ContentStreamInstruction(args,pikepdf.Operator('Tf'));node.write(pikepdf.unparse_content_stream(ops));doc.save(bad,compress_streams=False)
 return dict(actual_original_MathType_Form_Tf_increment=1.5,original_Tf=before,full_original_Tm_and_encoded_CIDs_unchanged=True)
def counter_drift(proof,bad):
 gs=source_counters(load(F/'plans/page01.json'))[0]['glyphs'];raw,guard=reposition_inline(proof,1,shifts=[dict(glyphs=gs,dx=-12.)]);bad.write_bytes(raw);return dict(actual_native_display_counter_drift_pt=-12.,native_font_GID_point_paint_Y_unchanged=True)
def occlusion(ident,n,rect,expected):
 import izho_natural_spacing_qa as qa
 with page_worker():
  proof=F/f'page{n:02}.pdf';pin=sha(proof);root=O/ident;folder=root/'2018/TS';(folder/'plans').mkdir(parents=True,exist_ok=True);bad=folder/proof.name;plan=load(F/f'plans/page{n:02}.json');comp=load(proof.with_suffix('.qa.json'))
  if not bad.exists():
   with f.open()as doc:p=doc.new_page(width=595.32,height=841.92);p.draw_rect(f.Rect(rect),fill=(1,1,1),color=None,width=0);overlay=folder/'actual-white-occlusion.pdf';doc.save(overlay)
   with pikepdf.open(proof)as doc,pikepdf.open(overlay)as over:doc.pages[0].add_overlay(over.pages[0]);doc.save(bad,compress_streams=False)
  assert sha(bad)!=pin
  if n==10:bad.with_suffix('.language-overlay.json').write_bytes(proof.with_suffix('.language-overlay.json').read_bytes())
  comp['output_sha256']=sha(bad);bad.with_suffix('.qa.json').write_text(json.dumps(comp,ensure_ascii=False,indent=2),'utf8');(folder/'plans'/f'page{n:02}.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),'utf8');prior=qa.BUILD;qa.BUILD=root
  with(folder/'actual-occluded-ink-audit.log').open('w',encoding='utf8')as log,contextlib.redirect_stdout(log):
   try:qa.audit(2018,'TS',n)
   except ValueError:pass
   else:raise AssertionError('Actual original ink damage accepted')
   finally:qa.BUILD=prior
  q=load(bad.with_suffix('.audit.json'));assert not q['passed']and sha(proof)==pin
  if expected=='math':assert q['actual_native_math_visible_ink_audit']['missing_actual_native_pixels']>0
  else:assert sum(r['changed_pixels']for r in q['figure_pixel_audits'])==1 and q['native_graphics_motion_audit']['changed_nonselected_native_graphical_pixels']==1
  rows.append(dict(id=ident,source_page=n,proof_sha256=pin,mutant_file=str(bad),mutant_sha256=sha(bad),independent_rejection_file=str(bad.with_suffix('.audit.json')),negative_rejected=True,delivered_proof_unmodified=True,all_original_font_GID_point_Y_and_image_bytes_CTM_metadata_unchanged=True,missing_actual_native_ink_pixels=q['actual_native_math_visible_ink_audit']['missing_actual_native_pixels'],changed_original_figure_pixels=sum(r['changed_pixels']for r in q['figure_pixel_audits'])))
 print('SOURCE2018_ACTUAL_BAD_OCCLUDED_PDF_REJECTED',ident,flush=True)
def label_overlap():
 from initial_bitmap_language_labels import masks
 paths=[p for p in(F/'history').glob('rejected-10-*/page10.pdf')if sha(p)=='2d3ad11a4c039a52784714c36c65b1e80f8067060e6c1a4059fd6e0ca7196d61'];assert len(paths)==1;bad=paths[0];plan=load(bad.parent/'current-plan-at-archive.json')
 with page_worker():
  with f.open(plan['original_english_source'])as doc:p=doc[9].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False);rgb=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()
  try:masks(plan,bad,rgb,4)
  except ValueError as e:
   assert isinstance(e.args[0],tuple)and e.args[0][0]=='New label covers original nonlanguage picture ink';report=e.args[0][1];assert report['new_label_over_original_nonlanguage_foreground_pixels']==96
  else:raise AssertionError('Original-centre wider Korean label overlap accepted')
  out=O/'actual-Korean-label-covers-source-Sun-disc.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');rows.append(dict(id='actual-Korean-label-covers-source-Sun-disc',source_page=10,proof_sha256=sha(F/'page10.pdf'),mutant_file=str(bad),mutant_sha256=sha(bad),independent_rejection_file=str(out),negative_rejected=True,delivered_proof_unmodified=True,actual_new_label_over_original_nonlanguage_foreground_pixels=96))
 print('SOURCE2018_ACTUAL_BAD_LABEL_OVERLAP_REJECTED',flush=True)
if __name__=='__main__':
 assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
 badcase('actual-fraction-bar-only-motion',8,fraction_bar_only);badcase('actual-fraction-numerator-only-drift',8,numerator_only);badcase('actual-native-MathType-Form-point-damage',2,form_point_damage);badcase('actual-native-displayed-counter-drift',1,counter_drift,counter_audit)
 with f.open(F/'page08.pdf')as doc:
  actual=_traces(doc[0]);r=profile8();dx=infer(r['original_glyphs'],actual);g=next(g for g in r['original_glyphs']if g['c']=='𝑅');rect=list(f.Rect(g['bbox'])+(dx-.3,-.3,dx+.3,.3))
 occlusion('actual-native-math-covered-metadata-unchanged',8,rect,'math');occlusion('actual-one-pixel-source-Sun-disc-graphic-damage',10,[312.,178.,312.25,178.25],'graphic');label_overlap()
 out=O/'negative-controls.json';out.write_text(json.dumps(dict(rows=rows,passed=len(rows)==7 and all(r['negative_rejected']and r['delivered_proof_unmodified']for r in rows),all_actual_bad_PDFs_rejected=True),indent=2)+'\n','utf8');print('ALL_SEVEN_ACTUAL_BAD_PDF_CONTROLS_REJECTED',sha(out),flush=True)
