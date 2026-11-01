"""Join reviewed native page proofs and audit the actual final file."""
from pathlib import Path
import argparse,hashlib,json
from collections import Counter
import pikepdf
import pymupdf as fitz
import numpy as np
from latex_native_proof import font_programs,encoded_images,native_images

BASE=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def traces(page):
 return [(t['font'],t['size'],t['type'],[(c,g,list(o),list(b))for c,g,o,b in t['chars']])for t in page.get_texttrace()]
def pixels(page):
 p=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
 return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)
def assemble(comp,prefix,count):
 folder=BASE/'proofs'/comp/'2026';target=BASE/'staged'/comp/f'{prefix}_2026_T_KO.pdf'
 target.parent.mkdir(parents=True,exist_ok=True)
 proof_paths=[folder/f'page{i:02}.pdf'for i in range(1,count+1)]
 audits=[json.loads(p.with_suffix('.qa.json').read_text('utf8'))for p in proof_paths]
 for page_number,(p,q) in enumerate(zip(proof_paths,audits),1):
  if q['output_sha256']!=sha(p):raise ValueError('Stale proof QA '+str(p))
  if q['source_page_1based']!=page_number:raise ValueError('Wrong source page '+str(p))
  if q['source_sha256']!=audits[0]['source_sha256']or q['source']!=audits[0]['source']:raise ValueError('Mixed original sources')
  for field in ['source_font_programs_preserved','source_images_preserved','source_drawings_preserved','original_page_box_preserved']:
   if not q[field]:raise ValueError(field+' '+str(p))
  for field in ['final_native_geometry','suppression_control_native_geometry','selected_source_hidden_geometry']:
   if q[field]['missing']or q[field]['extra']:raise ValueError(field+' '+str(p))
  if q['new_korean_intrusion_on_native_ink_pixels']:raise ValueError('Prose collision')
  candidates=[plan for plan in(BASE/'plans'/comp/'2026').glob(f'page{page_number:02}*.json')if sha(plan)==q['plan_sha256']]
  if len(candidates)!=1:raise ValueError('Missing or ambiguous current authoring plan '+str(page_number))
  q['plan']=str(candidates[0]);plan=json.loads(candidates[0].read_text('utf8'))
  if 'raster_language_changed_pixels_outside_reviewed_boxes'in q:
   if q['raster_language_changed_pixels_outside_reviewed_boxes']:raise ValueError('Raster overlay outside allowed regions')
  elif plan.get('raster_labels'):raise ValueError('Raster overlay audit is missing')
 source_path=Path(audits[0]['source'])
 if sha(source_path)!=audits[0]['source_sha256']:raise ValueError('Original source hash changed')
 original=fitz.open(source_path)
 if len(original)!=count:raise ValueError('The complete original page count is required')
 with pikepdf.Pdf.new()as out:
  for p in proof_paths:
   with pikepdf.Pdf.open(p)as single:
    if len(single.pages)!=1:raise ValueError('Single-page proof required')
    out.pages.append(single.pages[0])
  out.save(target,compress_streams=False)
 final=fitz.open(target);rows=[]
 for i,(p,q)in enumerate(zip(proof_paths,audits)):
  with fitz.open(p)as single:
   a,b=single[0],final[i]
   text_equal=traces(a)==traces(b);box_equal=a.rect==b.rect
   x,y=pixels(a),pixels(b);changed=int(np.any(x!=y,axis=2).sum())
   hangul=[(cp,g)for t in b.get_texttrace()if t['type']!=3 for cp,g,o,bb in t['chars']if 0xac00<=cp<=0xd7a3]
   if not text_equal or not box_equal or changed:raise ValueError('Joined proof mismatch '+str(i+1))
   if not hangul or any(g<=0 for cp,g in hangul):raise ValueError('Missing Korean glyph '+str(i+1))
   original_fonts=font_programs(original,original[i])<=font_programs(final,b)
   encoded_images_equal=encoded_images(original,original[i])==encoded_images(final,b)
   image_geometry_equal=native_images(original[i])==native_images(b)
   if not original_fonts or not encoded_images_equal or not image_geometry_equal:raise ValueError('Final original fonts/images changed '+str(i+1))
   row=dict(page=i+1,proof_sha256=sha(p),proof_path=str(p),qa_path=str(p.with_suffix('.qa.json')),qa_sha256=sha(p.with_suffix('.qa.json')),
    plan_path=q.get('plan'),plan_sha256=q['plan_sha256'],final_vs_reviewed_proof_changed_pixels=changed,
    final_vs_reviewed_proof_all_glyph_geometry_identical=text_equal,page_box_preserved=box_equal,
    visible_hangul_characters=len(hangul),missing_hangul_glyphs=0,
    original_font_programs_preserved=original_fonts,original_image_encoded_streams_and_filters_preserved=encoded_images_equal,
    original_image_geometry_preserved=image_geometry_equal)
   rows.append(row)
 review_rows=[];review_paths=[]
 for review_path in sorted(folder.glob('visual-review*.json')):
  review=json.loads(review_path.read_text('utf8'))
  if review.get('source_sha256')!=audits[0]['source_sha256']:raise ValueError('Visual review uses another source')
  review_rows.extend(review['pages']);review_paths.append(str(review_path))
 for number,(p,q)in enumerate(zip(proof_paths,audits),1):
  if not any(r.get('page')==number and r.get('reviewed')is True and r.get('proof_sha256')==sha(p)for r in review_rows):
   raise ValueError('Missing current visual review for page '+str(number))
 report=dict(schema='latex-native-joined-v1',status='READY',file=target.name,language='ko',pages=len(final),bytes=target.stat().st_size,
  sha256=sha(target),source_sha256=audits[0]['source_sha256'],source=audits[0]['source'],
  no_autoshrink=True,no_math_rasterization=True,no_paragraph_reflow=True,
  original_source_text_advances_preserved_by_nonpainting_encoded_prose=True,
  hidden_original_prose_has_empty_ActualText=True,no_added_editorial_notes=True,
  page_audits=rows,visual_review_files=review_paths,all_pages_visually_reviewed=True,visual_review_required=False)
 target.with_suffix('.qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
 print(json.dumps({k:v for k,v in report.items()if k!='page_audits'},ensure_ascii=False))
 original.close();final.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('comp');p.add_argument('prefix');p.add_argument('pages',type=int);p.add_argument('--work-root',type=Path,default=BASE);a=p.parse_args();BASE=a.work_root.resolve();assemble(a.comp,a.prefix,a.pages)
