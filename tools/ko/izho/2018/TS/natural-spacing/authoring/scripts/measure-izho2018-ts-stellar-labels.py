from pathlib import Path
import json,hashlib,sys,os
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_raster_font_measure import reference_outline
from fontTools.ttLib import TTFont
import pymupdf as f,numpy as np,cv2
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
SOURCE='f338dd0093628b658df3f02ca40a34b97e6ecd8fa431cf8517f08aa4eb14ff49'
font=Path('C:/Windows/Fonts/timesi.ttf');source=B/'2018/source/IZhO_2018_TS.pdf';assert sha(source)==SOURCE
specs=[('Star','별',[625,83,704,122],'S',[628,89,651,118]),('Sun','태양',[268,332,340,371],'S',[273,337,296,366]),('Earth','지구',[151,405,260,444],'E',[158,411,186,439])]
with page_worker():
 with f.open(source)as doc:
  info=doc[9].get_image_info(xrefs=True)[2];assert (info['width'],info['height'])==(743,464)
  pix=f.Pixmap(doc,info['xref']);a=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,pix.n)[:,:,:3];x0,y0,x1,y1=info['bbox'];sx=(x1-x0)/pix.width;sy=(y1-y0)/pix.height
  labels=[];measures=[];s_masks=[]
  ft=TTFont(font);angle=-float(ft['post'].italicAngle);ft.close()
  for word,ko,roi,char,wanted in specs:
   rx0,ry0,rx1,ry1=roi;ink=(a[ry0:ry1,rx0:rx1].min(2)<180).astype('uint8');count,components,stats,centres=cv2.connectedComponentsWithStats(ink,8)
   matches=[i for i,(x,y,w,h,z)in enumerate(stats[1:],1)if [rx0+int(x),ry0+int(y),rx0+int(x+w),ry0+int(y+h)]==wanted];assert len(matches)==1
   component=components==matches[0];bounds=reference_outline(char,font_path=font);l,b,r,t=bounds['outline_bounds_units'];units=bounds['units_per_em'];size=(wanted[3]-wanted[1])*sy*units/(t-b);baseline=y0+wanted[3]*sy+b*size/units
   yy,xx=np.nonzero(ink);word_ink=[rx0+int(xx.min()),ry0+int(yy.min()),rx0+int(xx.max())+1,ry0+int(yy.max())+1]
   measure=dict(source_pdf_sha256=SOURCE,source_page=10,source_image_index=2,source_image_xref=info['xref'],source_image_extracted_sha256=hashlib.sha256(doc.extract_image(info['xref'])['image']).hexdigest(),source_image_raw_stream_sha256=hashlib.sha256(doc.xref_stream_raw(info['xref'])).hexdigest(),source_image_bbox=info['bbox'],source_image_ctm=info['transform'],source_image_dimensions=[pix.width,pix.height],source_word=word,source_word_roi_px=roi,source_word_actual_ink_rect_px=word_ink,source_capital=char,independently_named_original_connected_component_rect_px=wanted,actual_capital_component_pixels=int(component.sum()),reference=bounds,measured_source_size_pt=size,measured_source_baseline_pt=baseline,estimated_serif_italic_role='source bitmap visually compared with explicit Times New Roman Italic reference; exact original font metadata is unavailable',source_italic_slant_reference_degrees=angle,source_only_measurement=True,translation_used_in_measurement=False,point_size_fitted_to_korean=False,limitation='Raster source has no recoverable native font metadata. Size/baseline are capital-outline estimates, and slant is the explicit visually matching reference-face estimate, not a claim of recovered original font identity.')
   measures.append(measure);labels.append(dict(reviewed=True,source_sha256=SOURCE,image_index=2,source_label=word,text=ko,source_word_ink_rect_px=word_ink,source_background_sample_px=[rx0,ry0],source_background_rgb=list(map(int,a[ry0,rx0])),measured_source_font_role='serif',measured_source_size_pt=size,measured_source_baseline_pt=baseline,measured_source_italic_slant_degrees=angle,source_measurement_index=len(measures)-1,source_point_size_is_estimate=True,point_size_fitted=False,reason='Translate only this isolated actual English word. Complete original image bytes/palette/CTM, all mathematical labels, geometry and every nonlanguage pixel remain protected. Source serif italic role retained using an honestly measured outline estimate.'))
   if char=='S':
    yy,xx=np.nonzero(component);s_masks.append(component[yy.min():yy.max()+1,xx.min():xx.max()+1])
  assert np.array_equal(*s_masks),'Repeated original capital S must independently confirm equal source raster typography'
  q=dict(source_sha256=SOURCE,source_page=10,source_only_capital_measurements=measures,repeated_Star_Sun_capital_S_actual_ink_masks_identical=True,reviewed_bitmap_language_labels=labels,source_original_image_modified=False)
  out=B/'2018/inspection/page10-stellar-label-source-measurements.json';out.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
  print('SOURCE_ONLY_STELLAR_LABEL_MEASUREMENT_READY',sha(out),[(r['source_label'],r['measured_source_size_pt'],r['measured_source_baseline_pt'])for r in labels],flush=True)
