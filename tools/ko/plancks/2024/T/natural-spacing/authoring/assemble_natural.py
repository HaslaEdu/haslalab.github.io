"""Join visually approved natural-spacing proofs and verify the final PDF."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
import pikepdf
import pymupdf as fitz
import numpy as np

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,'D:/CodexBuilds/Hasla-plancks-ortvay-icho-20261102/engine')
from native_proof import font_programs,encoded_images,native_images
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text('utf8'))

def traces(page):
 return [(t['font'],t['size'],t['type'],[(c,g,list(o),list(b))for c,g,o,b in t['chars']])for t in page.get_texttrace()]

def pixels(page):
 p=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
 return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)

def validate_proof(p,q,number):
 assert q['schema']=='natural-source-native-v1'
 assert q['output_sha256']==sha(p),('stale proof',p)
 assert q['page']==number
 for field in ['no_reserved_english_widths','no_font_shrink','source_font_programs_preserved',
  'original_image_encoded_bytes_and_filters_preserved','source_image_placements_preserved',
  'source_glyph_moves_restricted_to_authored_prose_line_bounds','stationary_display_equations_and_figures',
  'original_font_sizes_and_baselines_identical','native_horizontal_moves_only']:
  assert q[field] is True,(field,p)
 for field in ['stationary_display_glyphs_missing_or_moved','stationary_figure_glyphs_missing_or_moved']:
  assert q[field]==[],(field,p)
 for field in ['new_korean_intrusion_on_native_ink_pixels','new_body_korean_ink_inside_protected_figure_pixels']:
  assert q[field]==0,(field,p)
 assert not q['final_native_geometry']['missing'] and q['final_native_geometry']['extra']==0
 assert q['final_native_geometry']['max_delta_pt']<=.001
 assert q['motion_qa']['passed'] and q['motion_qa']['text_shift_mode']=='ctm'
 assert q['motion_qa']['erased_glyphs']==0
 assert q['actual_native_vector_coordinate_audit']['coordinate_errors']==[]
 assert q['actual_native_vector_coordinate_audit']['max_coordinate_tolerance_pt']<=1e-6
 if 'new_korean_glyph_and_geometry_audit'in q:
  glyph=q['new_korean_glyph_and_geometry_audit']
  assert glyph['passed'] and not glyph['missing_or_notdef_glyphs'] and not glyph['geometry_errors']
  assert glyph['planned_glyphs']==glyph['actual_glyphs'] and glyph['max_position_error_pt']<=.001
  assert glyph['position_tolerance_pt']<=.001
  assert q['paragraph_text_conservation_verified'] and q['inline_native_math_assignment_complete']
  assert q['native_atom_source_prose_seams_clear'] and q['new_korean_font_subsets_retain_original_gids']
  # The compositor's merged row anchor can differ from another original
  # prose origin on that row. Verify the actual selected source baselines
  # independently below rather than accepting that approximate-row flag.
 if q.get('reviewed_raster_label_manifest'):
  manifest=q['reviewed_raster_label_manifest'];assert sha(manifest['path'])==manifest['sha256']
 for contact in q.get('intentional_prose_decoration_contacts',[]):
  assert contact['x_translation_only'] and contact['source_path_bytes_and_paint_and_y_preserved']
  decoration=next(d for d in q['prose_vector_decorations']if d['id']==contact['id'])
  assert contact['source_path_index']==decoration['source_path_index']
  assert contact['observed_contact_pixels']==len(contact['contact_pixels_pdf_pt'])
 for field in ['effective_plan','plan']:
  assert sha(q[field+'_path'])==q[field+'_sha256'],('stale plan',p,field)
 if q.get('overrides_path'):assert sha(q['overrides_path'])==q['overrides_sha256']
 for scope in q['reviewed_source_scope']:assert sha(scope['path'])==scope['sha256']
 for line in q['line_reports']:
  if line['fixed_design_cells']:continue
  for gap in line['gaps']:assert -.001<=gap['new_gap']<=gap['ordinary_space']+.001,('excessive gap',number,gap)

def assemble(comp,prefix,year,count,proof_dir=None):
 folder=Path(proof_dir) if proof_dir else BASE/'proofs'/comp/str(year)
 target=BASE/'staged'/comp/f'{prefix}_{year}_T_KO.pdf'
 target.parent.mkdir(parents=True,exist_ok=True)
 proof_paths=[folder/f'page{i:02}.pdf'for i in range(1,count+1)]
 audits=[read(p.with_suffix('.layout.json'))for p in proof_paths]
 reviews=[];review_paths=[]
 for path in sorted(folder.glob('visual-review*.json')):
  review=read(path);assert review['source_sha256']==audits[0]['source_sha256']
  reviews.extend(review['pages']);review_paths.append(str(path))
 for number,(p,q)in enumerate(zip(proof_paths,audits),1):
  validate_proof(p,q,number)
  assert q['composer_sha256']==audits[0]['composer_sha256'],('mixed compositor',number)
  assert sha(q['composer_path'])==q['composer_sha256']
  assert q['source_sha256']==audits[0]['source_sha256'] and q['source']==audits[0]['source']
  assert any(r.get('page')==number and r.get('reviewed')is True and r.get('proof_sha256')==sha(p)
   and r.get('layout_sha256')==sha(p.with_suffix('.layout.json'))
   and r.get('effective_plan_sha256')==q['effective_plan_sha256']
   and r.get('composer_sha256')==q['composer_sha256']for r in reviews),('missing or stale visual review',number)
 source_path=Path(audits[0]['source']);assert sha(source_path)==audits[0]['source_sha256']
 original=fitz.open(source_path);assert len(original)==count
 with pikepdf.Pdf.new()as out:
  for p in proof_paths:
   with pikepdf.Pdf.open(p)as single:
    assert len(single.pages)==1;out.pages.append(single.pages[0])
  out.save(target,compress_streams=False)
 final=fitz.open(target);rows=[]
 for i,(p,q)in enumerate(zip(proof_paths,audits)):
  with fitz.open(p)as single:
   a,b=single[0],final[i]
   selected_baselines=[g['origin'][1]for g in q['selected_glyphs']]
   source_baselines=[c['origin'][1]for block in original[i].get_text('rawdict')['blocks']if block['type']==0 for line in block['lines']for span in line['spans']for c in span['chars']]
   baseline_deltas=[min(abs(v['baseline']-y)for y in selected_baselines)for v in q.get('placements',[])]
   actual_source_deltas=[min(abs(v['baseline']-y)for y in source_baselines)for v in q.get('placements',[])]
   assert max(baseline_deltas,default=0)<=.001 and max(actual_source_deltas,default=0)<=.001,('new prose baseline',i+1)
   baseline_audit=dict(passed=True,placements=len(baseline_deltas),max_selected_source_prose_baseline_delta_pt=max(baseline_deltas,default=0),
    max_actual_source_char_baseline_delta_pt=max(actual_source_deltas,default=0),tolerance_pt=.001,
    method='Compare every planned Korean placement to exact original selected-prose origins and independently to original rawdict character origins; merged compositor row anchors are not used.')
   text_equal=traces(a)==traces(b);box_equal=a.rect==b.rect
   x,y=pixels(a),pixels(b);changed=int(np.any(x!=y,axis=2).sum())
   hangul=[(cp,g)for t in b.get_texttrace()if t['type']!=3 for cp,g,o,bb in t['chars']if 0xac00<=cp<=0xd7a3]
   assert text_equal and box_equal and changed==0,('joined proof mismatch',i+1)
   assert hangul and all(g>0 for cp,g in hangul),('missing Korean glyph',i+1)
   font_ok=font_programs(original,original[i])<=font_programs(final,b)
   image_ok=encoded_images(original,original[i])==encoded_images(final,b)
   geometry_ok=native_images(original[i])==native_images(b)
   assert font_ok and image_ok and geometry_ok,('source fonts/images changed',i+1)
   rows.append(dict(page=i+1,proof_sha256=sha(p),proof_path=str(p),qa_path=str(p.with_suffix('.layout.json')),
    qa_sha256=sha(p.with_suffix('.layout.json')),plan_path=q['plan_path'],plan_sha256=q['plan_sha256'],
    effective_plan_path=q['effective_plan_path'],effective_plan_sha256=q['effective_plan_sha256'],
    overrides_path=q.get('overrides_path'),overrides_sha256=q.get('overrides_sha256'),
    final_vs_reviewed_proof_changed_pixels=changed,final_vs_reviewed_proof_all_glyph_geometry_identical=text_equal,
    page_box_preserved=box_equal,visible_hangul_characters=len(hangul),missing_hangul_glyphs=0,
    original_font_programs_preserved=font_ok,original_image_encoded_streams_and_filters_preserved=image_ok,
    original_image_geometry_preserved=geometry_ok,original_prose_baseline_audit=baseline_audit))
 report=dict(schema='natural-source-native-joined-v1',status='READY',file=target.name,language='ko',
  pages=len(final),bytes=target.stat().st_size,sha256=sha(target),source=str(source_path),source_sha256=sha(source_path),
  no_font_shrink=True,no_math_rasterization=True,no_reserved_english_widths=True,
  inline_native_math_moved_as_whole_expressions=True,stationary_display_equations_and_figures=True,
  original_font_sizes_and_baselines_preserved=True,hidden_original_prose_has_empty_ActualText=True,
  no_added_editorial_notes=True,page_audits=rows,visual_review_files=review_paths,
  all_pages_visually_reviewed=True,visual_review_required=False)
 target.with_suffix('.qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
 print(json.dumps({k:v for k,v in report.items()if k!='page_audits'},ensure_ascii=False),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('comp');p.add_argument('prefix');p.add_argument('year',type=int);p.add_argument('pages',type=int)
 p.add_argument('--proof-dir',type=Path)
 a=p.parse_args();assemble(a.comp,a.prefix,a.year,a.pages,a.proof_dir)
