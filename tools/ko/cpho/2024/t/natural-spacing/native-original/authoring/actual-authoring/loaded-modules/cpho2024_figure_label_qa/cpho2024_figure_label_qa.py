"""Original body/bitmap preservation and actual new label-font/ink checks."""
from pathlib import Path
from collections import Counter
import json,hashlib,subprocess,sys,os,gc
import numpy as np,pikepdf,pymupdf as fitz
from PIL import Image
from cpho2024_natural import BASE,sha
from cpho2024_body_qa import semantic
from cpho2024_font_style_qa import font_data,outline,prose_family
from pdf_native_inline_reposition import _traces,inspect_inline_groups
from pdf_moved_native_ink import source_outline_reference
from izho_new_prose_outline_qa import trace_font_resources,outline_results
from pdf_memory_gate import page_worker
from pdf_original_text_ops import widths as pdf_widths

def fresh(path,out):
 code="import sys,pymupdf as f;d=f.open(sys.argv[1]);d[0].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False).save(sys.argv[2])"
 subprocess.run([sys.executable,'-X','utf8','-c',code,str(path),str(out)],check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
 with Image.open(out)as im:return np.asarray(im.convert('RGB')).copy()

def audit(number,language,*,analysis_target=None,analysis_report=None):
 folder=BASE/'T/figure-language';canonical=folder/f'page{number:02}-{language}.pdf';q=json.loads(canonical.with_suffix('.labels.json').read_text('utf8'));target=Path(analysis_target)if analysis_target else canonical;body=Path(q['source_body']);assert sha(body)==q['source_body_sha256']and sha(canonical)==q['output_sha256']
 report_folder=folder/'qa';report_folder.mkdir(exist_ok=True);render=report_folder/f'page{number:02}-{language}';render.mkdir(exist_ok=True)
 with fitz.open(body)as before,fitz.open(target)as final,pikepdf.open(body)as old_pdf,pikepdf.open(target)as new_pdf:
  a=_traces(before[0]);b=_traces(final[0]);assert len(b)>=len(a)
  for source,actual in zip(a,b):
   for key in ['c','font','trace_gid','render_mode','color','opacity','linewidth','direction']:assert source[key]==actual[key],(key,source['c'],source[key],actual[key])
   assert abs(source['size']-actual['size'])<1e-6 and max(abs(x-y)for x,y in zip(source['origin'],actual['origin']))<=.001
  before_programs={(r[3],hashlib.sha256(before.extract_font(r[0])[3]).hexdigest())for r in before[0].get_fonts(full=True)}
  after_programs={(r[3],hashlib.sha256(final.extract_font(r[0])[3]).hexdigest())for r in final[0].get_fonts(full=True)}
  assert before_programs<=after_programs
  old_images={str(k):semantic(v)for k,v in old_pdf.pages[0].Resources.get('/XObject',{}).items()if str(v.get('/Subtype'))=='/Image'}
  new_images={str(k):semantic(v)for k,v in new_pdf.pages[0].Resources.get('/XObject',{}).items()if str(v.get('/Subtype'))=='/Image'}
  assert old_images==new_images
  assert semantic(old_pdf.pages[0].get('/Group'))==semantic(new_pdf.pages[0].get('/Group'))
  assert semantic(old_pdf.pages[0].Resources.get('/ColorSpace'))==semantic(new_pdf.pages[0].Resources.get('/ColorSpace'))
  mapped,programs=trace_font_resources(new_pdf,final[0]);new=[g for g in mapped if g['font_alias'].startswith('/FigureLanguage')and g['c'].strip()and g['gid']>=0]
  expected=Counter(c for r in q['label_records']for p in r['placements']for c in p['text']if not c.isspace());assert Counter(g['c']for g in new)==expected
  actual_data={digest:font_data(programs[digest]['raw'])for digest in{g['font_program_sha256']for g in new}};donors={};cache={};glyph_checks=[];cursor=0;font_widths={};seen_resources=set()
  def find_widths(resources):
   if resources.objgen!=(0,0):
    if resources.objgen in seen_resources:return
    seen_resources.add(resources.objgen)
   for alias,font in resources.get('/Font',{}).items():
    if not str(alias).startswith('/FigureLanguage'):continue
    descriptor=font.get('/DescendantFonts',[font])[0].get('/FontDescriptor',{})
    stream=next(descriptor[k]for k in ['/FontFile2','/FontFile3']if k in descriptor);digest=hashlib.sha256(stream.read_bytes()).hexdigest();font_widths[digest,str(alias)]=pdf_widths(font)
   for child in resources.get('/XObject',{}).values():
    if str(child.get('/Subtype'))=='/Form':find_widths(child.get('/Resources',resources))
  find_widths(new_pdf.pages[0].Resources)
  for row in q['label_records']:
   path=Path(row['target_font_source']);assert sha(path)==row['target_font_source_sha256']
   if path not in donors:donors[path]=font_data(path.read_bytes())
   donor=donors[path];metric=fitz.Font(fontfile=row['embedded_font_file']);size=row['estimated_original_source_point_size'];assert not row['point_size_fitted_to_translation']
   for placement in row['placements']:
    x,y=placement['origin'];rotation=placement['rotate']
    for word in placement['text'].split(' '):
     prefix='';pdf_advance=0
     for c in word:
      g=new[cursor];cursor+=1;actual=actual_data[g['font_program_sha256']];position=[x,y-pdf_advance]if rotation==90 else[x+pdf_advance,y]
      assert g['c']==c and g['font_alias']=='/'+row['font_alias']and abs(g['size']-size)<1e-6 and max(abs(v-w)for v,w in zip(g['origin'],position))<.002,(row['source_label']['id'],c,g['c'],g['font_alias'],row['font_alias'],g['size'],size,g['origin'],position)
      assert g['render_type']==(2 if row['estimated_original_source_stroke_width_pt']else 0)
      assert prose_family(actual['name'])==prose_family(donor['name'])
      signature=(g['font_program_sha256'],g['gid'],str(path),c)
      if signature not in cache:
       expected_outline=outline(donor,donor['cmap'][ord(c)]);actual_outline=outline(actual,actual['order'][g['gid']]);assert expected_outline and expected_outline==actual_outline;cache[signature]=True
      values,default=font_widths[g['font_program_sha256'],g['font_alias']];encoded_width=values.get(g['encoded_code'],default);donor_width=metric.text_length(c,fontsize=1000)
      # These new TrueType PDF Widths are floored to integer1/1000em.
      # Verify that quantization against the complete donor, then use the
      # actual encoded Widths to prove zero added tracking or text scaling.
      assert encoded_width is not None and -.001<=donor_width-encoded_width<=1.001,(c,encoded_width,donor_width)
      glyph_checks.append(dict(label=row['source_label']['id'],c=c,actual_gid=g['gid'],actual_font=actual['name'],source_measured_point_size=size,actual_point_size=g['size'],source_measured_position=position,actual_position=g['origin'],actual_embedded_outline_matches_full_role_donor=True,actual_PDF_width_1000em=encoded_width,complete_donor_width_1000em=donor_width,PDF_width_integer_quantization_verified=True));prefix+=c;pdf_advance+=encoded_width*size/1000
     amount=metric.text_length(word,fontsize=size)+size/4
     if rotation==90:y-=amount
     else:x+=amount
  assert cursor==len(new)
  empty=[]
  for digest in actual_data:
   checks=outline_results(dict(programs[digest],sha=digest),[g for g in new if g['font_program_sha256']==digest],{});empty.extend(g for g in checks if g['outline_empty'])
  assert not empty
  shape,shape_match=source_outline_reference(final[0],b[len(a):],scale=4)if new else(None,dict(passed=True))
  for data in list(donors.values())+list(actual_data.values()):
   if data.get('font'):data['font'].close()
 old_inv=inspect_inline_groups(body,1);new_inv=inspect_inline_groups(target,1);patches=q['reviewed_original_bitmap_symbol_reuse'];assert len(new_inv['images'])==len(old_inv['images'])+len(patches)
 for original,current in zip(old_inv['images'],new_inv['images']):
  assert original['original_raw_sha256']==current['original_raw_sha256']and max(abs(a-b)for a,b in zip(original['entry_ctm'],current['entry_ctm']))<.002
 patch_checks=[]
 for patch,actual in zip(patches,new_inv['images'][len(old_inv['images']):]):
  source=old_inv['images'][patch['source_image_index']];expected=list(source['entry_ctm']);expected[4]+=patch['dx'];assert actual['original_raw_sha256']==source['original_raw_sha256']==patch['original_image_raw_sha256']and max(abs(a-b)for a,b in zip(actual['entry_ctm'],expected))<.002
  clips=[g for g in new_inv['clip_groups']if actual['path']in g.get('image_paths',[])and g.get('known_rectangular_clips')];wanted=list(fitz.Rect(patch['source_clip_rect_pt'])+(patch['dx'],0,patch['dx'],0));assert any(any(max(abs(a-b)for a,b in zip(r,wanted))<.002 for r in g['clip_rects']if r)for g in clips)
  patch_checks.append(dict(source_character=patch['original_character'],source_original_raw_image_bytes_identical=True,original_CTM_scale_and_y_unchanged=True,requested_dx=patch['dx'],source_native_clipping_preserved=True,passed=True))
 if not q['label_records']:
  assert body.read_bytes()==target.read_bytes();pixel=dict(changed_pixels_outside_source_words_new_labels_and_reviewed_symbol_motion=0,new_label_over_preserved_original_dark_ink=0,new_actual_font_label_ink_missing=0,nonlanguage_pixels_preserved=True,byte_identical_no_label_page=True)
 else:
  original=fresh(body,render/'before.png');white=fresh(q['original_word_erasure_only'],render/'white-erasure.png');control=fresh(q['erased_only'],render/'native-control.png');actual=fresh(target,render/'final.png')
  old_mask=np.any(original!=white,axis=2);motion=np.any(white!=control,axis=2);new_mask=np.any(actual!=control,axis=2);changed=np.any(original!=actual,axis=2)
  # Image source-word erasures must be confined to the reviewed word rectangles.
  allowed=np.zeros(old_mask.shape,bool)
  for row in q['label_records']:
   for rect in row['erased_source_word_rects_pt']:
    x0,y0,x1,y1=[int(np.floor(v*4))for v in rect];allowed[max(0,y0-1):y1+2,max(0,x0-1):x1+2]=True
  assert not np.any(old_mask&~allowed)
  assert shape_match['passed']and shape is not None
  collision=int((shape&(control.min(axis=2)<80)).sum())
  # The saved text-only overlay is an independent exact native-font/CID
  # reference, avoiding unhinted-SVG versus TrueType-hint phase assumptions.
  reference_pdf=folder/f'page{number:02}-{language}.text-overlay.pdf'
  # Independently tie the allowable final added-ink mask to only the actual
  # reviewed label glyphs. Observed final/control differences are diagnostic,
  # never an allow-list: that would also accept an unrelated new drawing.
  with fitz.open(reference_pdf)as ref_doc,pikepdf.open(reference_pdf)as ref_pdf:
   ref_glyphs,ref_programs=trace_font_resources(ref_pdf,ref_doc[0]);ref_glyphs=[g for g in ref_glyphs if g['c'].strip()and g['gid']>=0]
   assert len(ref_glyphs)==len(new)
   for g,h in zip(new,ref_glyphs):
    for key in ['c','gid','font_program_sha256','render_type']:assert g[key]==h[key]
    assert abs(g['size']-h['size'])<1e-6 and max(abs(x-y)for x,y in zip(g['origin'],h['origin']))<=.001
   assert not ref_doc[0].get_images(full=True)and not ref_doc[0].get_drawings()
  reference=fresh(reference_pdf,render/'actual-font-label-reference.png')
  expected_ink=reference.min(axis=2)<160;missing=int((expected_ink&(actual.min(axis=2)>=220)).sum())
  permitted_motion=np.zeros(old_mask.shape,bool)
  for patch in patches:
   r=fitz.Rect(patch['source_clip_rect_pt'])
   for rect in [r,r+(patch['dx'],0,patch['dx'],0)]:
    x0,y0,x1,y1=[int(np.floor(v*4))for v in rect];permitted_motion[max(0,y0-1):y1+2,max(0,x0-1):x1+2]=True
  motion_outside=int((motion&~permitted_motion).sum())
  expected_new_mask=np.any(reference<255,axis=2)
  outside_added=int((new_mask&~expected_new_mask).sum())
  outside=int((changed&~(old_mask|permitted_motion|expected_new_mask)).sum())
  pixel=dict(changed_pixels_outside_source_words_new_labels_and_reviewed_symbol_motion=outside,new_label_over_preserved_original_dark_ink=collision,new_actual_font_label_ink_missing=missing,added_ink_outside_independent_actual_font_reference=outside_added,native_symbol_motion_outside_reviewed_source_and_destination_clips=motion_outside,independent_reference_contains_only_verified_actual_label_glyphs=True,reference_sha256=sha(reference_pdf),old_source_word_ink_changed_pixels=int(old_mask.sum()),new_label_actual_ink_pixels=int(new_mask.sum()),original_native_symbol_motion_pixels=int(motion.sum()),exact_actual_font_reference_ink_pixels=int(expected_ink.sum()),source_outline_metadata_match=shape_match,nonlanguage_pixels_preserved=outside==0 and outside_added==0 and motion_outside==0,actual_source_word_regions_only=True)
  if collision:
   yy,xx=np.nonzero(shape&(control.min(axis=2)<80));pixel['collision_bbox']=[float(xx.min()/4),float(yy.min()/4),float((xx.max()+1)/4),float((yy.max()+1)/4)]
 result=dict(page=number,language=language,proof_sha256=sha(target),body_sha256=sha(body),qa_mode='analysis-only-negative-clone'if analysis_target else'publication',unmodified_canonical_proof_sha256=sha(canonical),labels=len(q['label_records']),original_body_glyphs_and_font_point_paint_positions_checked=len(a),original_body_glyph_metadata_unchanged=True,all_original_font_programs_unchanged=True,all_original_image_palette_ICC_mask_graphs_unchanged=True,all_original_image_CTMs_unchanged=True,original_page_group_and_colorspace_unchanged=True,new_label_actual_nonspace_glyphs_checked=len(new),new_label_actual_empty_outlines=empty,new_label_glyph_style_checks=glyph_checks,reviewed_original_native_bitmap_symbol_reuse=patch_checks,pixel_audit=pixel,source_font_measurement_is_estimate=True,translation_font_sizes_fitted=False,no_original_mathematical_text_retyped=True,passed=not pixel['changed_pixels_outside_source_words_new_labels_and_reviewed_symbol_motion']and not pixel.get('added_ink_outside_independent_actual_font_reference',0)and not pixel.get('native_symbol_motion_outside_reviewed_source_and_destination_clips',0)and not pixel['new_label_over_preserved_original_dark_ink']and not pixel['new_actual_font_label_ink_missing'])
 out=Path(analysis_report)if analysis_report else report_folder/f'page{number:02}-{language}.audit.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=1)+'\n','utf8');print('FIGURE_LABEL_QA',number,language,result['passed'],pixel,flush=True)
 if not result['passed']:raise ValueError(('Original figure label audit failed',number,language))
 return result

if __name__=='__main__':
 with page_worker():audit(int(sys.argv[1]),sys.argv[2])
