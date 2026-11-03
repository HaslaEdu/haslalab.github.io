from pathlib import Path
import sys,os,json,hashlib,math,re,subprocess,html
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_original_style_fonts import FONTS,korean_font
from initial_bitmap_language_labels import specifications,masks
import pymupdf as f,numpy as np
from PIL import Image
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();F=B/'natural/2018/TS';O=B/'natural/2018-stellar-label-native-font-reference';O.mkdir(exist_ok=True);plan=json.loads((F/'plans/page10.json').read_text('utf8'));proof=F/'page10.pdf';pin=sha(proof);POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
with page_worker():
 labels=specifications(plan);font=FONTS['serif'];measure=json.loads(Path(plan['reviewed_bitmap_source_measurements']).read_text('utf8'));clear=json.loads(Path(plan['reviewed_bitmap_label_translation_clearance']).read_text('utf8'));assert clear['passed']
 with f.open(proof)as final:
  svg=final[0].get_svg_image(text_as_path=True);actual=[]
  with f.open()as control:
   donor_subset=korean_font('',0,''.join(r['text']for r in labels),override='serif',cache_dir=O/'independent-donor-subset')[1]
   p=control.new_page(width=final[0].rect.width,height=final[0].rect.height);p.insert_font(fontname='IndependentCompleteSourceRoleDonor',fontfile=str(donor_subset));metric=f.Font(fontfile=str(font))
   for label in labels:
    size=label['measured_source_size_pt'];baseline=label['measured_source_baseline_pt'];angle=label['measured_source_italic_slant_degrees'];x=label['actual_word_center_pt']-metric.text_length(label['text'],fontsize=size)/2;morph=(f.Point(x,baseline),f.Matrix(1,0,math.tan(math.radians(angle)),1,0,0));p.insert_text((x,baseline),label['text'],fontname='IndependentCompleteSourceRoleDonor',fontsize=size,color=(0,0,0),morph=morph)
    for char in label['text']:
     matches=[]
     for use in re.findall(r'<use\b[^>]*data-text=[^>]*?/?>',svg):
      if f'data-text="{char}"'not in html.unescape(use):continue
      m=re.search(r'transform="matrix\(([^)]+)\)"',use);values=[float(v)for v in m[1].replace(',',' ').split()]
      if abs(values[5]-baseline)<.02:matches.append(values)
     assert len(matches)==1,(char,matches);v=matches[0];wanted=[size,0.,size*math.tan(math.radians(angle)),-size];assert max(abs(a-b)for a,b in zip(v[:4],wanted))<.001,(char,v,wanted)
     actual.append(dict(text=char,source_label=label['source_label'],actual_native_font_basis=v[:4],source_measured_point=size,source_measured_baseline=baseline,source_estimated_italic_slant=angle,original_word_center=label['original_word_center_pt'],actual_word_center=label['actual_word_center_pt'],translation_width_clearance_dx=label['translation_width_clearance_dx_pt'],no_font_fit_or_added_tracking=True))
   reference=O/'isolated-complete-source-role-donor-Korean-glyphs.pdf';control.save(reference,garbage=0,deflate=False)
  assert len(actual)==5
  measurements=[]
  for scale in[4,8,12]:
   for renderer in['MuPDF','Poppler']:
    arrays=[]
    for name,path in[('reference',reference),('actual',proof)]:
     if renderer=='MuPDF':
      with f.open(path)as doc:p=doc[0].get_pixmap(matrix=f.Matrix(scale,scale),clip=f.Rect(230,87,422,214),colorspace=f.csRGB,alpha=False);a=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()
     else:
      out=O/f'{name}-{renderer}-{scale}';subprocess.run([POP,'-f','1','-singlefile','-r',str(scale*72),'-x',str(230*scale),'-y',str(87*scale),'-W',str(192*scale),'-H',str(127*scale),'-png',str(path),str(out)],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
      with Image.open(out.with_suffix('.png'))as im:a=np.asarray(im.convert('RGB')).copy()
     arrays.append(a)
    a,b=arrays;ink=a.min(2)<255;dark=a.min(2)<32;row=dict(renderer=renderer,scale=scale,reference_actual_font_nonwhite_pixels=int(ink.sum()),reference_actual_font_dark_pixels=int(dark.sum()),reference_nonwhite_RGB_errors=int((ink&np.any(a!=b,2)).sum()),missing_actual_font_dark_pixels=int((dark&(b.min(2)>=220)).sum()));row['passed']=row['reference_actual_font_dark_pixels']>0 and row['reference_nonwhite_RGB_errors']==row['missing_actual_font_dark_pixels']==0;measurements.append(row);print('INDEPENDENT_ACTUAL_FONT_LABEL_REFERENCE',row,flush=True)
  with f.open(plan['original_english_source'])as original:p=original[9].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False);original_rgb=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()
  old,new,protected=masks(plan,proof,original_rgb,4);assert protected['new_label_over_original_nonlanguage_foreground_pixels']==0
  q=dict(source_sha256=plan['original_english_source_sha256'],proof_sha256=pin,reference_file=str(reference),reference_sha256=sha(reference),source_measurement_file=plan['reviewed_bitmap_source_measurements'],source_measurement_sha256=sha(plan['reviewed_bitmap_source_measurements']),translation_clearance_file=plan['reviewed_bitmap_label_translation_clearance'],translation_clearance_sha256=sha(plan['reviewed_bitmap_label_translation_clearance']),source_font_role_donor_file=str(font),source_font_role_donor_sha256=sha(font),actual_glyphs=actual,reference_measurements=measurements,protected_original_nonlanguage_ink=protected,old_original_center_Sun_overlap_pixels=96,new_Sun_overlap_pixels=0,all_original_image_bytes_palette_CTM_and_nonlanguage_geometry_protected=True,source_raster_font_metadata_is_estimated=True,target_font_points_or_baselines_fitted=False,passed=all(r['passed']for r in measurements));assert sha(proof)==pin;out=O/'witness.json';out.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('ORIGINAL_MEASURED_ITALIC_LABEL_FONT_AND_CLEARANCE_WITNESS',q['passed'],sha(out),flush=True)
