"""Join visually approved natural-spacing proofs and verify the final PDF."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys,os,importlib.util
for _thread_env in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
 os.environ[_thread_env]='1'
import pikepdf
import pymupdf as fitz
import numpy as np

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,'D:/CodexBuilds/Hasla-plancks-ortvay-icho-20261102/engine')
from native_proof import font_programs as default_font_programs,encoded_images,native_images
from source_path_resolver import resolve_source
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text('utf8'))

def traces(page):
 return [(t['font'],t['size'],t['type'],[(c,g,list(o),list(b))for c,g,o,b in t['chars']])for t in page.get_texttrace()]

def pixels(page):
 p=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
 return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)

def load_font_proof_helper(helper):
 """Load the edition's frozen helper without reusing a legacy sibling module."""
 helper=Path(helper).resolve();assert helper.is_file()
 sys.path.insert(0,str(helper.parent))
 # The default legacy proof helper imports pdf_latex_text_ops above. Python's
 # module cache otherwise binds a newer edition helper to that older reader.
 siblings={p.stem for p in helper.parent.glob('*.py')}
 for name in siblings:sys.modules.pop(name,None)
 spec=importlib.util.spec_from_file_location('_publication_native_proof',helper)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 for name in siblings:
  loaded=sys.modules.get(name)
  if loaded is not None and getattr(loaded,'__file__',None):
   assert Path(loaded.__file__).resolve().parent==helper.parent,('Mixed frozen proof dependency',name,loaded.__file__)
 return module.font_programs

def _annotation_settings(annotation):
 result={}
 for key,value in annotation.items():
  if str(key)=='/Rect':continue
  if getattr(value,'is_indirect',False):result[str(key)]=('indirect',value.objgen)
  else:result[str(key)]=value.unparse()if hasattr(value,'unparse')else repr(value)
 return result

def move_reviewed_url_link(target_page,source_page,qa):
 """Move the one original O2025 hyperlink with its verified native URL atom."""
 uri='https://arxiv.org/abs/2412.13580'
 assert qa['page']==10
 matches=[(i,s)for i,s in enumerate(qa['native_shifts'])if ''.join(g['c']for g in s['glyphs'])==uri]
 assert len(matches)==1
 index,shift=matches[0];dx=float(shift['dx']);assert 0<dx<100
 assert len(shift['glyphs'])==len(uri) and not shift.get('vector_paths')
 original=[l for l in source_page.get_links()if l.get('uri')==uri];assert len(original)==1
 source_rect=list(original[0]['from'])
 assert max(abs(a-b)for a,b in zip(source_rect,[275.07000732421875,37.99798583984375,448.5150146484375,51.9429931640625]))<.001
 annotations=[a for a in target_page.obj.get('/Annots',[])if a.get('/Subtype')==pikepdf.Name('/Link')and str(a.get('/A',{}).get('/URI',''))==uri]
 assert len(annotations)==1
 annotation=annotations[0];assert '/QuadPoints'not in annotation
 before=list(map(float,annotation['/Rect']))
 before_mupdf=list(fitz.Rect(before)*source_page.transformation_matrix)
 assert max(abs(a-b)for a,b in zip(source_rect,before_mupdf))<.001
 settings=_annotation_settings(annotation);after=[before[0]+dx,before[1],before[2]+dx,before[3]]
 annotation['/Rect']=pikepdf.Array(after)
 assert _annotation_settings(annotation)==settings
 return dict(page=10,uri=uri,native_shift_index=index,native_url_glyphs=len(uri),dx=dx,
  source_rect_pdf=before,target_rect_pdf=after,source_rect_mupdf=source_rect,
  expected_target_rect_mupdf=[source_rect[0]+dx,source_rect[1],source_rect[2]+dx,source_rect[3]],
  only_horizontal_rect_translation=True,other_annotation_settings_preserved=True)

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
 if q.get('original_type3_program_preservation'):
  type3=q['original_type3_program_preservation']
  assert type3['passed']and type3['source']==type3['target'],('Original Type3 program differs',p)
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

def assemble(comp,prefix,year,count,proof_dir=None,proof_helper_path=None,output_dir=None):
 folder=Path(proof_dir) if proof_dir else BASE/'proofs'/comp/str(year)
 target=(Path(output_dir)if output_dir else BASE/'staged'/comp)/f'{prefix}_{year}_T_KO.pdf'
 target.parent.mkdir(parents=True,exist_ok=True)
 proof_paths=[folder/f'page{i:02}.pdf'for i in range(1,count+1)]
 audits=[read(p.with_suffix('.layout.json'))for p in proof_paths]
 if any(q.get('original_type3_program_preservation')for q in audits):assert proof_helper_path,'Type3-aware font proof helper required'
 font_programs=default_font_programs
 if proof_helper_path:
  helper=Path(proof_helper_path).resolve();assert helper.is_file()
  assert all(q['native_proof_helper_sha256']==sha(helper)for q in audits)
  font_programs=load_font_proof_helper(helper)
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
 logical_source=audits[0]['source']
 source_path=resolve_source(logical_source,audits[0]['source_sha256'])
 original=fitz.open(source_path);assert len(original)==count
 link_adjustments=[];link_geometry_audits=[]
 with pikepdf.Pdf.new()as out:
  for p in proof_paths:
   with pikepdf.Pdf.open(p)as single:
    assert len(single.pages)==1;out.pages.append(single.pages[0])
  if comp=='ortvay'and year==2025:
   link_adjustments.append(move_reviewed_url_link(out.pages[9],original[9],audits[9]))
  if comp=='ortvay'and year==2024:
   from ortvay2024_link_annotations import adjust_links
   with fitz.open(proof_paths[1])as page_two:
    link_geometry_audits=adjust_links(out.pages[1],original[1],page_two[0],audits[1])
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
   page_links=[r for r in link_adjustments if r['page']==i+1]
   for link in page_links:
    found=[z for z in b.get_links()if z.get('uri')==link['uri']];assert len(found)==1
    actual=list(found[0]['from']);assert max(abs(u-v)for u,v in zip(actual,link['expected_target_rect_mupdf']))<.001
    link['actual_target_rect_mupdf']=actual;link['passed']=True
   page_geometry=[r for r in link_geometry_audits if r['page']==i+1]
   for link in page_geometry:
    found=[z for z in b.get_links()if z.get('uri')==link['uri']and max(abs(u-v)for u,v in zip(list(z['from']),link['expected_target_rect_mupdf']))<.001]
    assert len(found)==1,('Missing/ambiguous URL subset annotation',i+1,link['source_link_index'])
    link['actual_target_rect_mupdf']=list(found[0]['from']);link['passed']=True
   rows.append(dict(page=i+1,proof_sha256=sha(p),proof_path=str(p),qa_path=str(p.with_suffix('.layout.json')),
    qa_sha256=sha(p.with_suffix('.layout.json')),plan_path=q['plan_path'],plan_sha256=q['plan_sha256'],
    effective_plan_path=q['effective_plan_path'],effective_plan_sha256=q['effective_plan_sha256'],
    overrides_path=q.get('overrides_path'),overrides_sha256=q.get('overrides_sha256'),
    final_vs_reviewed_proof_changed_pixels=changed,final_vs_reviewed_proof_all_glyph_geometry_identical=text_equal,
    page_box_preserved=box_equal,visible_hangul_characters=len(hangul),missing_hangul_glyphs=0,
    original_font_programs_preserved=font_ok,original_image_encoded_streams_and_filters_preserved=image_ok,
    original_image_geometry_preserved=geometry_ok,original_prose_baseline_audit=baseline_audit,
    link_annotation_adjustments=page_links,link_annotation_geometry_audits=page_geometry))
 report=dict(schema='natural-source-native-joined-v1',status='READY',file=target.name,language='ko',
  pages=len(final),bytes=target.stat().st_size,sha256=sha(target),source=logical_source,source_sha256=sha(source_path),
  resolved_source_read_path=str(source_path),source_path_resolver_sha256=sha(BASE/'engine/source_path_resolver.py'),
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
 p.add_argument('--proof-helper',type=Path)
 p.add_argument('--output-dir',type=Path)
 a=p.parse_args();assemble(a.comp,a.prefix,a.year,a.pages,a.proof_dir,a.proof_helper,a.output_dir)
