"""Native PDF text over reviewed original bitmap-word regions only."""
from pathlib import Path
from collections import Counter
import json,hashlib,gc,sys
import numpy as np,pikepdf,pymupdf as fitz
from fontTools.ttLib import TTFont
from cpho2024_natural import BASE,REPO,sha
from cpho2024_figure_label_plan import LABELS
from pdf_original_style_fonts import subset_font
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups

def single_face(path):
 path=Path(path)
 if path.suffix.lower()!='.ttc':return path
 out=BASE/'fonts'/('label-source-'+path.stem+'-face0.ttf')
 if not out.exists():
  font=TTFont(path,fontNumber=0,recalcTimestamp=False);font.save(out);font.close()
  out.with_suffix('.provenance.json').write_text(json.dumps(dict(source=str(path),source_sha256=sha(path),source_face_index=0,extracted=str(out),sha256=sha(out),system_font_not_modified=True),indent=2)+'\n','utf8')
 return out

def font_path(measurement,language):
 selected=measurement['selected_source_font'];face=selected['face']
 if language=='EN':return single_face(selected['font_file'])
 sans=face.startswith(('DengXian','SimHei','MicrosoftYaHei'));bold='Bold'in face
 if sans:return REPO/'tools/ko/fonts'/('NotoSansCJKkr-Bold.otf'if bold else'NotoSansCJKkr-Regular.otf')
 if bold:return REPO/'tools/ko/fonts/NotoSerifCJKkr-Bold.otf'
 return BASE/'fonts/Batang-Regular.ttf'

def width(text,font,size):return sum(font.text_length(word,fontsize=size)for word in text.split(' '))+text.count(' ')*size/4

def insert(page,point,text,font,size,alias,fontfile,*,rotation=0,color=(0,0,0),stroke=0):
 page.insert_font(fontname=alias,fontfile=str(fontfile));x,y=point
 for word in text.split(' '):
  if word:
   page.insert_text((x,y),word,fontname=alias,fontsize=size,color=color,fill=color,rotate=rotation,render_mode=2 if stroke else 0,border_width=stroke/size if stroke else 1,overlay=True)
   advance=font.text_length(word,fontsize=size)
  else:advance=0
  advance+=size/4
  if rotation==90:y-=advance
  else:x+=advance

def build(number,language):
 labels=[l for l in LABELS if l['page']==number];body=BASE/f'T/pages/page{number:02}-{language}.pdf';folder=BASE/'T/figure-language';folder.mkdir(exist_ok=True)
 target=folder/f'page{number:02}-{language}.pdf'
 if not labels:
  target.write_bytes(body.read_bytes());result=dict(source_body=str(body),source_body_sha256=sha(body),output=str(target),output_sha256=sha(target),erased_only=str(body),erased_only_sha256=sha(body),original_word_erasure_only=str(body),original_word_erasure_only_sha256=sha(body),original_encoded_images_not_modified=True,original_mathematical_text_not_retyped=True,new_geometry_drawn=False,label_records=[],reviewed_original_bitmap_symbol_reuse=[],language=language,page=number,prose_word_space_em=.25,no_label_page_byte_identical_to_reviewed_body=True)
  target.with_suffix('.labels.json').write_text(json.dumps(result,indent=1)+'\n','utf8');print('FIGURE_LABEL_PROOF',number,language,0,sha(target),flush=True);return target,result
 measurements={l['id']:json.loads((BASE/f"authoring/T/figure-label-measurements/{l['id']}.json").read_text('utf8'))for l in labels}
 fonts={};full_fonts={}
 for l in labels:
  path=font_path(measurements[l['id']],language);full_fonts[l['id']]=path;fonts.setdefault(path,[]).append(l[language.lower()])
 subset={path:subset_font(path,texts,cache_dir=BASE/'fonts/figure-label-subsets')for path,texts in fonts.items()}
 metrics={path:fitz.Font(fontfile=str(p))for path,p in subset.items()};aliases={path:'FigureLanguage'+str(i)for i,path in enumerate(fonts)}
 eraser=fitz.open();text_doc=fitz.open()
 with fitz.open(body)as src:
  ep=eraser.new_page(width=src[0].rect.width,height=src[0].rect.height);tp=text_doc.new_page(width=src[0].rect.width,height=src[0].rect.height)
 inv=json.loads((BASE/'inspection/image-ink-inventory.json').read_text('utf8'));reports=[];native_patches=[]
 for l in labels:
  m=measurements[l['id']];chosen=m['selected_source_font'];meta=next(x for x in inv if x['page']==number and x['index']==l['image_index']);box=fitz.Rect(meta['bbox']);iw,ih=meta['dimensions'];sx=box.width/iw;sy=box.height/ih
  from PIL import Image
  with Image.open(BASE/f"inspection/image-p{number}-{l['image_index']}.png")as im:a=np.asarray(im.convert('RGB'))
  selected=np.zeros(a.shape[:2],bool)
  for region in l.get('source_word_regions_px',[l['source_word_roi_px']]):
   x0,y0,x1,y1=region;selected[y0:y1,x0:x1]=True
  roi_pixels=a[selected];background=Counter(tuple(map(int,c))for c in roi_pixels).most_common(1)[0][0];sample=np.argwhere(selected&np.all(a==background,axis=2))[0]
  ink=selected&(a.min(axis=2)<160);yy,xx=np.nonzero(ink);assert len(xx)
  source_ink=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
  actual_rects=[]
  for x0,y0,x1,y1 in l.get('source_word_regions_px',[l['source_word_roi_px']]):
   rect=[box.x0+x0*sx,box.y0+y0*sy,box.x0+x1*sx,box.y0+y1*sy];ep.draw_rect(fitz.Rect(rect),color=None,fill=tuple(c/255 for c in background),width=0);actual_rects.append(rect)
  path=full_fonts[l['id']];font=metrics[path];size=chosen['size'];text=l[language.lower()];alias=aliases[path];advance=width(text,font,size)
  if language=='EN'and l.get('english_original_closing_parenthesis_reuse'):
   reuse=l['english_original_closing_parenthesis_reuse'];x0,y0,x1,y1=reuse['source_clip_rect_px'];rect=[box.x0+x0*sx,box.y0+y0*sy,box.x0+x1*sx,box.y0+y1*sy]
   ep.draw_rect(fitz.Rect(rect),color=None,fill=tuple(c/255 for c in background),width=0);actual_rects.append(rect)
   native_patches.append(dict(**reuse,source_clip_rect_pt=rect,dx=advance-size,source_original_unit_point_estimate=size,new_unit_advance_pt=advance,source_native_symbol_not_retyped=True))
  colors=a[ink];shade=int(np.percentile(colors.min(axis=1),5));color=(shade/255,)*3
  stroke=2*chosen['pixel_spread']/m['scale_px_per_pt'];placements=[]
  if l['rotation']=='stack':
   chars=m['stacked_original_characters'];target_chars=list(text)
   for old,c in zip(chars,target_chars):
    p=old['source_font_measurement']['origin'];cx=box.x0+(source_ink[0]+source_ink[2])/2*sx;point=[cx-font.text_length(c,fontsize=size)/2,p[1]]
    insert(tp,point,c,font,size,alias,subset[path],color=color,stroke=stroke);placements.append(dict(text=c,origin=point,rotate=0))
   if len(target_chars)>len(chars):raise ValueError('A stack needs an explicit source-line journal')
  elif l['rotation']==90:
   center=box.y0+(source_ink[1]+source_ink[3])/2*sy;point=[chosen['origin'][0],center+advance/2]
   insert(tp,point,text,font,size,alias,subset[path],rotation=90,color=color,stroke=stroke);placements.append(dict(text=text,origin=point,rotate=90))
  else:
   left=box.x0+source_ink[0]*sx;right=box.x0+source_ink[2]*sx;center=(left+right)/2
   x=left if l['alignment']=='left'else right-advance if l['alignment']=='right'else center-advance/2;point=[x,chosen['origin'][1]]
   insert(tp,point,text,font,size,alias,subset[path],color=color,stroke=stroke);placements.append(dict(text=text,origin=point,rotate=0))
  reports.append(dict(source_label=l,source_ink_bbox_px=source_ink,erased_source_word_rects_pt=actual_rects,source_background_rgb=background,source_background_sample_px=[int(sample[1]),int(sample[0])],source_raster_foreground_gray_estimate=shade,source_font_measurement_file=str(BASE/f"authoring/T/figure-label-measurements/{l['id']}.json"),source_font_measurement_sha256=sha(BASE/f"authoring/T/figure-label-measurements/{l['id']}.json"),estimated_original_source_point_size=size,point_size_fitted_to_translation=False,original_font_metadata_available=False,estimated_original_source_stroke_width_pt=stroke,target_font_source=str(path),target_font_source_sha256=sha(path),embedded_font_file=str(subset[path]),embedded_font_file_sha256=sha(subset[path]),font_alias=alias,target_text=text,placements=placements))
 erased_overlay=folder/f'page{number:02}-{language}.erase-overlay.pdf';text_overlay=folder/f'page{number:02}-{language}.text-overlay.pdf';erased=folder/f'page{number:02}-{language}.erased-only.pdf';eraser.save(erased_overlay,garbage=0,deflate=False);text_doc.save(text_overlay,garbage=0,deflate=False);eraser.close();text_doc.close()
 with pikepdf.open(body)as src,pikepdf.open(erased_overlay)as over:src.pages[0].add_overlay(over.pages[0]);src.save(erased,compress_streams=False)
 white_erased=erased
 if native_patches:
  inventory=inspect_inline_groups(body,1);state=inspect_inline_groups(erased,1)['final_ctm'];assert max(abs(a-b)for a,b in zip(state,[1,0,0,1,0,0]))<.00001,state
  with pikepdf.open(erased)as doc:
   page=doc.pages[0];height=float(page.MediaBox[3])-float(page.MediaBox[1]);program=[]
   for patch in native_patches:
    original=inventory['images'][patch['source_image_index']];digest=original['original_raw_sha256'];matches=[(k,v)for k,v in page.Resources.get('/XObject',{}).items()if str(v.get('/Subtype'))=='/Image'and hashlib.sha256(v.read_raw_bytes()).hexdigest()==digest];assert len(matches)==1
    name,image=matches[0];x0,y0,x1,y1=patch['source_clip_rect_pt'];ctm=original['entry_ctm'];dx=patch['dx']
    program.append('q 1 0 0 1 %.9f 0 cm %.9f %.9f %.9f %.9f re W n %s cm %s Do Q\n'%(dx,x0,height-y1,x1-x0,y1-y0,' '.join('%.9f'%v for v in ctm),str(name)))
    patch.update(original_image_raw_sha256=digest,original_image_entry_CTM=ctm,original_image_resource=str(name),requested_source_CTM_scale_and_all_y_retained=True)
   content=page.Contents;old=list(content)if isinstance(content,pikepdf.Array)else[content];page.Contents=pikepdf.Array(old+[pikepdf.Stream(doc,''.join(program).encode('ascii'))]);native_erased=erased.with_name(erased.stem+'-native-symbols.pdf');doc.save(native_erased,compress_streams=False)
  erased=native_erased
 with pikepdf.open(erased)as src,pikepdf.open(text_overlay)as over:src.pages[0].add_overlay(over.pages[0]);src.save(target,compress_streams=False)
 result=dict(source_body=str(body),source_body_sha256=sha(body),output=str(target),output_sha256=sha(target),erased_only=str(erased),erased_only_sha256=sha(erased),original_word_erasure_only=str(white_erased),original_word_erasure_only_sha256=sha(white_erased),original_encoded_images_not_modified=True,original_mathematical_text_not_retyped=True,new_geometry_drawn=False,label_records=reports,reviewed_original_bitmap_symbol_reuse=native_patches,language=language,page=number,prose_word_space_em=.25)
 target.with_suffix('.labels.json').write_text(json.dumps(result,ensure_ascii=False,indent=1)+'\n','utf8');print('FIGURE_LABEL_PROOF',number,language,len(reports),sha(target),flush=True);fitz.TOOLS.store_shrink(100);gc.collect();return target,result

if __name__=='__main__':
 with page_worker():build(int(sys.argv[1]),sys.argv[2])
