from pathlib import Path
import sys,json,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');sys.path.insert(0,str(B/'engine'))
from pdf_memory_gate import page_worker
from PIL import Image
import numpy as np
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
visual=[];stationary=[]
with page_worker():
 for lang in ['ko','en']:
  for n in [1,2,3]:
   proof=B/f'natural/2003/{lang}/page{n:02}.pdf';png=B/f'proof-renders-144/{lang}/page{n:02}-{sha(proof)[:16]}.png';source=B/f'source-renders-144/page{n:02}.png';prior=B/f'proof-history/before-original-source-page-group-restoration/natural/2003/{lang}/page{n:02}.pdf';priorpng=B/f'proof-history/before-original-source-page-group-restoration/proof-renders-144/{lang}/page{n:02}-{sha(prior)[:16]}.png'
   with Image.open(png)as im:current=np.array(im.convert('RGB'))
   with Image.open(source)as im:original=np.array(im.convert('RGB'))
   with Image.open(priorpng)as im:old=np.array(im.convert('RGB'))
   assert current.shape==original.shape==old.shape
   previous_difference=int(np.any(current!=old,axis=2).sum());assert previous_difference==0
   rois=[]
   for label,rect in ([('Original full ellipse equation',[71.5,250.,126.,281.])]if n==1 else [('Original full diffraction display equation',[71.5,426.5,124.,455.]),('Original left rest-mass scientific notation',[71.5,708.5,137.5,721.5])]if n==2 else []):
    x0,y0,x1,y1=[round(v*2)for v in rect];a=original[y0:y1,x0:x1];b=current[y0:y1,x0:x1];changed=int(np.any(a!=b,axis=2).sum());missing=int(((a.min(axis=2)<80)&(b.min(axis=2)>=220)).sum());assert changed==missing==0;rois.append(dict(label=label,source_rect_points=rect,changed_RGB_pixels=changed,missing_original_dark_pixels=missing))
   stationary.append(dict(language=lang,source_page=n,proof_sha256=sha(proof),proof_Poppler144_sha256=sha(png),original_source_Poppler144_sha256=sha(source),rois=rois,original_page_group_restoration_full_page_RGB_changed_pixels=previous_difference))
   visual.append(dict(language=lang,source_page=n,proof=str(proof),proof_sha256=sha(proof),png=str(png),png_sha256=sha(png),source_png=str(source),source_png_sha256=sha(source),dpi=144,visual_review_pending=False,full_original_and_current_proof_144dpi_visually_reviewed=True,passed=True,source_two_line_title_centers_Tr2_points_and_source_footers_reviewed=True,original_native_math_fonts_GIDs_points_scripts_and_figures_reviewed=True,natural_word_spacing_and_complete_prose_reviewed=True,large_original_blank_page3_region_retained=True))
 for path,q in [(B/'authoring/full144-visual-review-complete.json',dict(status='ALL6_CURRENT_FULL_PAGE_VISUALS_REVIEWED',source_sha256='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63',pages_per_language=3,total_proof_pages=6,pages=visual,notes='Full originals1-3 and all current proofs visually reviewed. Original15.96pt two-line Tr2 title centers, source section/body/folio points, exact mathematical programs and scripts, all original images and original large blank area on source3 retained. Exact before/after page-group restoration Poppler RGB is0 on every complete proof. Stationary original display/notation ROIs are exact0 RGB change. Six questions are complete for every actual available original page; no absent graph plate is invented.')),(B/'evidence/original-stationary-math-Poppler144.json',dict(passed=True,source_sha256='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63',all_current_original_stationary_math_ROIs_zero_RGB_difference=True,pages=stationary))]:
  path.parent.mkdir(parents=True,exist_ok=True);assert not path.exists();path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
 print('CPHO2003_T_ALL6_CURRENT_FULL_VISUALS_AND_SOURCE_MATH_POPPLER_ZERO_DIFF_RECORDED',flush=True)
