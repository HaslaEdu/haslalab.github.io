"""Closed, exact original native-program edge controls. No thresholds/exclusions."""
from pathlib import Path
import hashlib,json,pymupdf as f
from pdf_native_inline_reposition import _traces
from izho_2018_independent_original_math_geometry import same
from izho2018_ts_literal_form_program import read_form
SOURCE='f338dd0093628b658df3f02ca40a34b97e6ecd8fa431cf8517f08aa4eb14ff49'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(result,plan,path,w):
 try:
  config=Path(__file__).resolve().parents[1]/'2018/inspection/closed-native-program-phase-contract.json';assert sha(config)=='b459f6ef64ea5eae25762860a42fb5e8ec9b8a1916f590f3ed40ae755d34a4da';cfg=json.loads(config.read_text('utf8'));assert cfg['source_sha256']==SOURCE;case=cfg['cases'][str(plan['source_page'])];raw=result['original_input_outline_native_ink_audit'];n=plan['source_page']
  assert plan['original_english_source_sha256']==sha(plan['original_english_source'])==SOURCE and sha(path)==case['witness_sha256']
  assert result['output_sha256']==sha(result['output'])==w['proof_sha256']==sha(w['proof'])==case['proof_sha256']
  assert w['kind']==case['kind']and w['source_page']==n and w['original_source_sha256']==SOURCE and w['passed']and w['proof_unmodified']and not w['mathematics_retyped']and not w['source_font_programs_substituted']
  assert w['source_reference_sha256']==sha(w['source_reference_file'])==case['reference_sha256']and w['original_input_page_sha256']==raw['source_sha256']==case['raw_control_sha256']
  assert raw['protected_native_glyphs']==case['raw_control_glyphs']and raw['newly_missing_native_ink_pixels']==1 and raw['missing_bbox']==case['raw_missing_bbox']and not raw['missing_requested_source_glyphs']and not raw['missing_final_native_glyphs']and raw['source_outline_audit']['passed']
  assert result['actual_native_math_visible_ink_audit']['missing_actual_native_pixels']==0
  gs=w['complete_original_expression_glyphs'];assert len(gs)==w['complete_original_visible_native_glyphs_checked']==case['native_glyphs'];dx=w['independently_inferred_whole_original_expression_dx']
  with f.open(plan['original_english_source'])as original,f.open(result['output'])as final:
   selected=[g for g in _traces(original[n-1])if g['c'].strip()and f.Rect(case['source_expression_rect']).contains(f.Point(g['origin']))];actual=_traces(final[0]);assert len(selected)==len(gs)
   for g in selected:
    assert sum(same(g,h)and max(abs(a-b)for a,b in zip(g['origin'],h['origin']))<.001 for h in gs)==1
    assert sum(same(g,h)and abs(h['origin'][0]-g['origin'][0]-dx)<.001 for h in actual)==1
  assert w['source_math_expression_point_sizes']==sorted({g['size']for g in selected})
  records=w['independent_exact_original_visible_glyph_records'];assert len(records)==len(gs)and all(r['all_original_native_font_GID_fractional_points_paint_and_Y_preserved']and r['requested_dx']==dx and same(r['source_glyph'],r['actual_target_glyph'])and abs(r['actual_target_glyph']['origin'][0]-r['source_glyph']['origin'][0]-dx)<.001 for r in records)
  if n==2:
   programs=w['exact_original_Form_CID_Tf_fullTm_programs'];assert programs['all_raw_programs_and_font_resources_identical']and programs['original']==programs['reference']==programs['actual'];program=programs['original'];assert program['literal_Form_raw_sha256']==case['literal_Form_raw_sha256'];entries=program['all_encoded_CID_Tf_fullTm_programs'];assert len(entries)==w['complete_original_encoded_Form_CIDs_checked']==21 and all(r['encoded_CID_hex']and len(r['full_Tm'])==6 and float(r['Tf'])>0 for r in entries)
  else:
   fields=['encoded_CID_hex','code','font_resource','Tf','Tm','Tc','Tw','Th','Ts','Tr'];programs=w['exact_original_CID_programs'];assert len(programs)==len(gs)
   for r in programs:
    a,b,c=r['source_encoded_program'],r['reference_encoded_program'],r['actual_encoded_program'];assert r['all_original_CID_font_Tf_fullTm_and_paint_preserved']and r['requested_dx']==dx and all(a[k]==b[k]==c[k]for k in fields)and b['CTM']==c['CTM']
   guard=w['source_native_reference_guard'];assert guard['passed']and guard['font_programs_unchanged']and guard['original_form_streams_unchanged']and guard['original_image_streams_unchanged']and guard['native_vector_path_bytes_preserved']
  measure=w['native_original_program_reference_measurements'];assert len(measure)==6 and {(m['renderer'],m['scale'])for m in measure}=={(r,s)for r in['MuPDF','Poppler']for s in[4,8,12]}and all(m['passed']and m['reference_original_program_deep_dark_pixels']>0 and m['missing_original_native_program_pixels']==m['actual_reference_nonwhite_RGB_errors']==0 for m in measure)
  svg=w['svg_reference_scales'];assert set(svg)=={'4','8','12'}and all(q['passed']and q['protected_native_glyphs']==len(gs)and q['newly_missing_native_ink_pixels']==0 for q in svg.values())
  envelope=w['native_reference_crop_contains_complete_original_expression_actual_outline_envelope'];assert envelope['contains_all_selected_original_mathematical_ink']and envelope['source_outline_uses']==len(gs)and envelope['crop']==w['same_integer_page_crop']==case['crop'];R=case['crop'];E=envelope['source_native_expression_ink_envelope_after_common_dx'];assert R[0]<=E[0]and R[1]<=E[1]and E[2]<=R[2]and E[3]<=R[3]
  controls=Path(cfg['negative_controls_file']);assert sha(controls)==cfg['negative_controls_sha256'];bad=json.loads(controls.read_text('utf8'));assert bad['passed']and bad['all_actual_bad_PDFs_rejected']and len(bad['rows'])==7 and all(r['negative_rejected']and r['delivered_proof_unmodified']and sha(r['mutant_file'])==r['mutant_sha256']for r in bad['rows'])
 except Exception as e:
  import traceback
  result['native_phase_witness_rejected_conditions']=[repr(e),f'private verifier line {traceback.extract_tb(e.__traceback__)[-1].lineno}'];return False
 result['native_ink_reference_profile']=dict(kind='source2018-complete-original-native-program-v1',source_page=n,method='Exact whole original native mathematical program, every original CID/font/GID/fractional point/Tf/fullTm/paint/Y and complete fraction/clip geometry independently checked. Both native renderers4x/8x/12x have exact nonwhite RGB equality; all croppedSVG scales show zero missing ink and the crop contains the complete original actual ink envelope. Raw full-page1pixel diagnostic remains visible. No mathematical ink excluded, no threshold changed.',original_4x_svg_dark_pixel_delta=1,exact_original_native_expression_glyphs=len(gs),exact_original_encoded_CIDs_checked=len(gs),native_original_reference_missing_pixels=0,native_reference_nonwhite_RGB_errors=0,native_reference_renderers=['MuPDF','Poppler'],native_reference_scales=[4,8,12],cropped_SVG_reference_scales=[4,8,12],cropped_SVG_native_ink_missing_pixels=0,witness=str(path),witness_sha256=sha(path),raw_control_source_sha256=case['raw_control_sha256'],full_original_source_sha256=SOURCE,proof_unmodified=True,mathematical_ink_excluded=False,actual_bad_PDF_controls=7)
 result['verified_original_native_ink_missing_pixels']=0;return True
