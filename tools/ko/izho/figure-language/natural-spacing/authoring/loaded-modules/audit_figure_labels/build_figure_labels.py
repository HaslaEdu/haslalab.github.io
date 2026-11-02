"""Translate only the remaining reviewed English figure words in2010/2011."""
from pathlib import Path
import sys,json,math,hashlib,shutil
import pymupdf as fitz,pikepdf
from fontTools.ttLib import TTFont
sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools')
from pdf_native_inline_reposition import reposition_inline,_traces,inspect_inline_groups
from pdf_original_text_ops import glyph_key
from pdf_original_style_fonts import subset_font
from pdf_memory_gate import page_worker
from measure_source_labels import FIELDS
B=Path(__file__).resolve().parents[1]
OLD=B.parent/'izho-natural-spacing';PUB=Path('D:/CodexBuilds/Hasla-publish-20261031')
BATANG=B.parent/'cpho2024-original-natural/fonts/Batang-Regular.ttf'
SANS=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab/tools/ko/fonts/NotoSansCJKkr-Bold.otf')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
def native_word(gs,text,x,y):
 row=sorted([g for g in gs if g['c'].strip()and abs(g['origin'][1]-y)<.001 and g['origin'][0]>=x-.001],key=lambda g:g['origin'][0])
 result=row[:len(text)];assert ''.join(g['c']for g in result)==text,(text,result)
 assert abs(result[0]['origin'][0]-x)<.001
 return result
def metrics(font,text,size):return fitz.Font(fontfile=str(font)).text_length(text,fontsize=size)
def build(year,number):
 baseline_json=PUB/f'tools/ko/izho/{year}/T/natural-spacing/publication.json'
 baseline=json.loads(baseline_json.read_text('utf8'));old=OLD/f'{year}/T/page{number:02}.pdf'
 expected=next(p for p in baseline['page_proofs']if p['page']==number)['proof_sha256'];assert sha(old)==expected
 folder=B/f'{year}/T';folder.mkdir(parents=True,exist_ok=True);target=folder/f'page{number:02}.pdf';placements=[];erase=[];shifts=[];bitmap=[];native=[]
 for field in FIELDS if year==2010 else[]:
  if field['page']!=number:continue
  measurement_file=B/f"source-label-measurements/{field['id']}.json";measurement=json.loads(measurement_file.read_text('utf8'))
  # One coherent source serif family across the same source diagram. Cambria
  # improves the low-resolution floor word by only .006IoU; retain the clear
  # Times family supported by the other source words, without fitting targets.
  fit=measurement['best_by_face']['TimesNewRoman']if field['role']=='serif'else measurement['top20'][0]
  size=fit['size'];font=BATANG if field['role']=='serif'else SANS;angle=0.
  if field['role']=='sans-bold-italic':
   ft=TTFont(fit['font_file']);angle=-float(ft['post'].italicAngle);ft.close()
  src=measurement['source_page_crop'];x0,y0,x1,y1=field['rect'];ox,oy=measurement['source_crop_device_origin'];rect=[(ox+x0)/2,(oy+y0)/2,(ox+x1)/2,(oy+y1)/2]
  source_width=metrics(fit['font_file'],field['text'],size);width=metrics(font,field['ko'],size)
  x=fit['origin'][0]
  if field['align']=='center':x+=(source_width-width)/2
  elif field['align']=='right':x+=source_width-width
  origin=[x,fit['origin'][1]]
  row=dict(id=field['id'],source_text=field['text'],text=field['ko'],source_kind='bitmap-source-measured',source_word_rect_pt=rect,source_font_measurement=measurement,source_measurement_file=str(measurement_file),source_measurement_sha256=sha(measurement_file),source_chosen_fit=fit,source_face_prior_reason='Same source serif diagram family; near-tied raster fits do not justify changing family.'if field['role']=='serif'else'Best original English raster fit; independent source words select the same bold italic face.',font_source=str(font),font_source_sha256=sha(font),point_size=size,baseline=origin[1],origin=origin,source_italic_angle_degrees=angle,source_point_size_is_estimate=True,target_point_size_fitted=False)
  bitmap.append(row);placements.append(row)
 with fitz.open(old)as doc:
  gs=[g for g in _traces(doc[0])if g['c'].strip()]
  if year==2011 and number==3:
   for ident,text,ko,x,y in [('ion','ion','이온',108.72,536.28),('electron','electron','전자',220.56,660.72)]:
    selected=native_word(gs,text,x,y);erase+=selected;size=selected[0]['size'];assert all(abs(g['size']-size)<1e-6 for g in selected)
    left=min(g['bbox'][0]for g in selected);right=max(g['bbox'][2]for g in selected);width=metrics(BATANG,ko,size);origin=[(left+right-width)/2,y]
    row=dict(id=ident,source_text=text,text=ko,source_kind='native-source-metadata',source_glyphs=selected,font_source=str(BATANG),font_source_sha256=sha(BATANG),point_size=size,baseline=y,origin=origin,source_italic_angle_degrees=0.,source_point_size_is_estimate=False,target_point_size_fitted=False)
    native.append(row);placements.append(row)
   for ident,x,y,index in [('fig1',92.64,252.,'1'),('fig2',104.64,693.,'2')]:
    selected=native_word(gs,'Fig.',x,y);digits=[g for g in gs if g['c']==index and abs(g['origin'][1]-y)<.001 and selected[-1]['origin'][0]<g['origin'][0]<selected[-1]['origin'][0]+15]
    assert len(digits)==1;digit=digits[0]
    erase+=selected;size=selected[0]['size'];width=metrics(BATANG,'그림',size);digit_width=digit['bbox'][2]-digit['bbox'][0];source_center=(selected[0]['bbox'][0]+digit['bbox'][2])/2
    left=source_center-(width+size/4+digit_width)/2;digit_x=left+width+size/4;shifts.append(dict(glyphs=[digit],dx=digit_x-digit['origin'][0]))
    row=dict(id=ident,source_text='Fig.',text='그림',source_kind='native-source-metadata',source_glyphs=selected,original_digit=digit,original_digit_dx=shifts[-1]['dx'],whole_caption_original_center=source_center,font_source=str(BATANG),font_source_sha256=sha(BATANG),point_size=size,baseline=y,origin=[left,y],source_italic_angle_degrees=0.,source_point_size_is_estimate=False,target_point_size_fitted=False)
    native.append(row);placements.append(row)
 if not placements:
  shutil.copy2(old,target);save(target.with_suffix('.labels.json'),dict(year=year,page=number,body=str(old),body_sha256=sha(old),proof_sha256=sha(target),placements=[],byte_identical_no_label_page=True));return
 control=folder/f'page{number:02}.native-control.pdf'
 stationary=[]
 if year==2011 and number==3:
  inv=inspect_inline_groups(old,1)
  for rect in [[85.05,236.7,166.05,260.3],[97.05,677.7,178.05,701.3]]:
   matches=[v for v in inv['vector_paths']if max(abs(a-b)for a,b in zip(v['rect'],rect))<.001]
   assert len(matches)==1;stationary.append(dict(matches[0],review_reason='The unchanged original white caption box and black border contain the original caption text. Only its native digit moves horizontally with the translated word; the box is separately protected by nontext ink QA.'))
 if erase or shifts:
  raw,move=reposition_inline(old,1,erased_glyphs=erase,shifts=shifts,reviewed_stationary_vector_paths=stationary,position_tolerance_pt=.001);control.write_bytes(raw)
 else:shutil.copy2(old,control);move=dict(passed=True,no_native_text_changed=True)
 erased=folder/f'page{number:02}.erased-only.pdf'
 with pikepdf.open(control)as doc:
  page=doc.pages[0];height=float(page.MediaBox[3])-float(page.MediaBox[1]);program=[]
  for r in bitmap:
   x0,y0,x1,y1=r['source_word_rect_pt'];program.append('q 1 1 1 rg %.9f %.9f %.9f %.9f re f Q\n'%(x0,height-y1,x1-x0,y1-y0))
  contents=page.Contents;old_contents=list(contents)if isinstance(contents,pikepdf.Array)else[contents]
  if program:page.Contents=pikepdf.Array(old_contents+[pikepdf.Stream(doc,''.join(program).encode('ascii'))])
  doc.save(erased,compress_streams=False)
 overlay=folder/f'page{number:02}.text-overlay.pdf'
 with fitz.open(old)as source,fitz.open()as text:
  page=text.new_page(width=source[0].rect.width,height=source[0].rect.height);fonts={}
  for row in placements:
   font=Path(row['font_source'])
   if font not in fonts:
    alias='TranslatedFigure'+str(len(fonts));subset=subset_font(font,[r['text']for r in placements if Path(r['font_source'])==font],cache_dir=B/'font-subsets');page.insert_font(fontname=alias,fontfile=str(subset));fonts[font]=(alias,subset)
   alias,subset=fonts[font];row.update(font_resource=alias,embedded_font=str(subset),embedded_font_sha256=sha(subset));kwargs={}
   if row['source_italic_angle_degrees']:kwargs['morph']=(fitz.Point(*row['origin']),fitz.Matrix(1,0,math.tan(math.radians(row['source_italic_angle_degrees'])),1,0,0))
   page.insert_text(row['origin'],row['text'],fontname=alias,fontsize=row['point_size'],**kwargs)
  text.save(overlay,garbage=0,deflate=False)
 with pikepdf.open(erased)as doc,pikepdf.open(overlay)as text:doc.pages[0].add_overlay(text.pages[0]);doc.save(target,compress_streams=False)
 report=dict(year=year,page=number,body=str(old),body_sha256=sha(old),proof_sha256=sha(target),native_control=str(control),native_control_sha256=sha(control),erased_only=str(erased),erased_only_sha256=sha(erased),text_overlay=str(overlay),text_overlay_sha256=sha(overlay),placements=placements,erased_native_word_glyphs=erase,original_caption_digit_shifts=shifts,reviewed_stationary_caption_frames=stationary,native_move_qa=move,body_and_equation_fonts_not_changed=True,original_encoded_images_not_modified=True,no_new_diagram_geometry=True,point_sizes_not_fitted=True)
 save(target.with_suffix('.labels.json'),report);print(year,number,len(placements),sha(target),flush=True)
if __name__=='__main__':
 with page_worker():build(int(sys.argv[1]),int(sys.argv[2]))
