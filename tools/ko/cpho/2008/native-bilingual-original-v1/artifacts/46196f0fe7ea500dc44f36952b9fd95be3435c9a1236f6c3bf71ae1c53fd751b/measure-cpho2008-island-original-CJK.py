"""Source-only four-character bitmap measurements, never translation fitting."""
from pathlib import Path
from io import BytesIO
import sys,json,hashlib
import numpy as np,pikepdf,pymupdf as f
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
B=Path(__file__).resolve().parents[1];S=B/'source/CPhO_2008_original_combined_ZH.pdf';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_original_image_ink import resolved_images
from cpho2008_prose_outline_primitives import trace_font_resources
SHA='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d';sha=lambda data:hashlib.sha256(data).hexdigest()
ROIS=[[[282,77,323,120],[325,77,361,119],[360,79,399,120],[401,77,436,120]],[[230,221,271,265],[274,221,310,264],[309,223,349,265],[352,221,389,265]]]
with page_worker():
 assert sha(S.read_bytes())==SHA
 with f.open(S)as source,pikepdf.open(S)as encoded:
  page=source[3];mapped,programs=trace_font_resources(encoded,page);refs={}
  for char in '单电子岛':
   g=next(g for g in mapped if g['c']==char and g['font']=='ËÎÌå+FPEF');raw=programs[g['font_program_sha256']]['raw']
   with TTFont(BytesIO(raw))as tt:
    name=tt.getGlyphOrder()[g['gid']];gs=tt.getGlyphSet();pen=BoundsPen(gs);gs[name].draw(pen)
    refs[char]=dict(original_native_glyph=g,font_program_sha256=sha(raw),units_per_em=tt['head'].unitsPerEm,outline_bounds_units=list(pen.bounds),original_hmtx_advance=tt['hmtx'][name][0],reference_weight_class=tt['OS/2'].usWeightClass if'OS/2'in tt else None)
  images=resolved_images(source,page);labels=[]
  for index,rois in enumerate(ROIS):
   info=images[index];pix=f.Pixmap(source,info['xref'])
   if pix.colorspace.n!=3:pix=f.Pixmap(f.csRGB,pix)
   array=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,pix.n);plane=array[:,:,:3].min(2);a,b,c,d,e,g=info['transform'];assert b==c==0 and a>0 and d>0;records=[]
   for char,roi in zip('单电子岛',rois):
    x0,y0,x1,y1=roi;mask=plane[y0:y1,x0:x1]<180
    assert mask.any()and not(mask[0].any()or mask[-1].any()or mask[:,0].any()or mask[:,-1].any()),(index,char,roi)
    yy,xx=np.nonzero(mask);bounds=[x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max())+1,y0+int(yy.max())+1];physical=[e+a*bounds[0]/pix.width,g+d*bounds[1]/pix.height,e+a*bounds[2]/pix.width,g+d*bounds[3]/pix.height]
    ref=refs[char];left,bottom,right,top=ref['outline_bounds_units'];em=ref['units_per_em'];point=(physical[3]-physical[1])*em/(top-bottom);baseline=physical[3]+bottom*point/em
    records.append(dict(character=char,manually_named_original_glyph_roi_px=roi,source_ink_bounds_px=bounds,source_ink_bounds_pt=physical,source_glyph_ink_pixels=int(mask.sum()),source_reference=ref,source_height_only_point_estimate=point,source_height_only_baseline_estimate=baseline))
   # Independent horizontal font-unit regression uses source Chinese glyphs
   # and real source advances only; no replacement word enters this fit.
   design=[];observed=[];advance=0.
   for r in records:
    ref=r['source_reference'];em=ref['units_per_em'];left,bottom,right,top=ref['outline_bounds_units'];design.extend([[1.,advance+left/em],[1.,advance+right/em]]);observed.extend([r['source_ink_bounds_pt'][0],r['source_ink_bounds_pt'][2]]);advance+=ref['original_hmtx_advance']/em
   matrix=np.asarray(design);actual=np.asarray(observed);origin,point=np.linalg.lstsq(matrix,actual,rcond=None)[0];errors=(matrix@np.array([origin,point])-actual).tolist();baseline=float(np.median([r['source_ink_bounds_pt'][3]+r['source_reference']['outline_bounds_units'][1]*point/r['source_reference']['units_per_em']for r in records]));old=[min(r['source_ink_bounds_px'][0]for r in records),min(r['source_ink_bounds_px'][1]for r in records),max(r['source_ink_bounds_px'][2]for r in records),max(r['source_ink_bounds_px'][3]for r in records)]
   labels.append(dict(source_image_index=index,source_image_xref=info['xref'],source_image_dimensions=[pix.width,pix.height],source_image_transform=list(info['transform']),source_image_extracted_sha256=sha(source.extract_image(info['xref'])['image']),named_source_characters=records,source_word_ink_bounds_px=old,source_only_horizontal_point_estimate=float(point),source_only_horizontal_origin_estimate=float(origin),source_only_common_baseline_estimate=baseline,source_reference_point_residuals_pt=errors,source_only_median_height_point_estimate=float(np.median([r['source_height_only_point_estimate']for r in records])),source_inferred_role='Song/serif with bold or stroked raster weight; actual bitmap metadata unavailable',source_only_independent_visual_review='Thin horizontal strokes versus vertical stems and triangular/wedge terminals in both original raw CJK crops. Independently confirmed by peer authoring agent; SimHei is a poor visual prior.',translation_used_in_measurement=False,point_fitted_to_translation_or_box=False))
  out=dict(original_source_sha256=SHA,source_page=4,method='Four manually identified original bitmap Chinese characters versus actual original embedded native Song glyph/font/GID outlines and advances. All values are source-only estimates; raster font/weight/point metadata is not recovered.',labels=labels)
  path=B/'inspection/page04-original-island-CJK-source-measurements.json';assert not path.exists();path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n','utf8');print('C08_SOURCE_ONLY_CJK_LABEL_MEASUREMENTS',[(x['source_image_index'],x['source_only_horizontal_point_estimate'],x['source_only_median_height_point_estimate'],x['source_only_common_baseline_estimate'],x['source_reference_point_residuals_pt'])for x in labels],flush=True)
