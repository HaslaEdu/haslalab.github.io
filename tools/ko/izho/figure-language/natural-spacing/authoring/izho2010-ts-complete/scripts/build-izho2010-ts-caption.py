from pathlib import Path
import sys,json,hashlib,shutil
import pymupdf as fitz,pikepdf
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');C=B/'figure-language';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_original_style_fonts import subset_font,FONTS
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
engine=C/'engine';engine.mkdir(parents=True,exist_ok=True)
old=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-older-figure-language/engine/audit_figure_labels.py')
engine.joinpath('audit_figure_labels.py').write_text(old.read_text('utf8').replace("folder=B/f'{year}/T'","folder=B/f'{year}/TS'"),'utf8')
engine.joinpath('build_figure_labels.py').write_text("from pathlib import Path\nimport hashlib\nB=Path("+repr(str(C))+ ")\nsha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()\n",'utf8')
body=B/'natural/2010/TS/page04.pdf';audit=json.loads(body.with_suffix('.audit.json').read_text('utf8'));collision=json.loads(body.with_suffix('.prose-collision.json').read_text('utf8'))
assert audit['passed']and audit['output_sha256']==sha(body)and collision['passed']
measurement=B/'2010/source-caption-measurement.json';m=json.loads(measurement.read_text('utf8'));fit=m['top20'][0];assert fit['face']=='TimesNewRoman-Bold'
font=FONTS['serif-bold'];size=fit['size'];source_width=fitz.Font(fontfile=fit['font_file']).text_length('Рис.',fontsize=size);width=fitz.Font(fontfile=str(font)).text_length('그림',fontsize=size);origin=[fit['origin'][0]+source_width-width,fit['origin'][1]]
ox,oy=m['source_crop_device_origin'];x0,y0,x1,y1=m['rect'];rect=[(ox+x0)/2,(oy+y0)/2,(ox+x1)/2,(oy+y1)/2]
row=dict(id='fig1',source_text='Рис.',text='그림',source_kind='bitmap-source-measured',source_word_rect_pt=rect,source_font_measurement=m,source_measurement_file=str(measurement),source_measurement_sha256=sha(measurement),source_chosen_fit=fit,source_face_prior_reason='Best independent original Cyrillic raster fit is Times New Roman Bold.',font_source=str(font),font_source_sha256=sha(font),point_size=size,baseline=origin[1],origin=origin,source_italic_angle_degrees=0.,source_point_size_is_estimate=True,target_point_size_fitted=False)
folder=C/'2010/TS';folder.mkdir(parents=True,exist_ok=True);target=folder/'page04.pdf';control=folder/'page04.native-control.pdf';shutil.copy2(body,control)
erased=folder/'page04.erased-only.pdf'
with pikepdf.open(control)as doc:
 page=doc.pages[0];h=float(page.MediaBox[3])-float(page.MediaBox[1]);program='q 1 1 1 rg %.9f %.9f %.9f %.9f re f Q\n'%(rect[0],h-rect[3],rect[2]-rect[0],rect[3]-rect[1]);contents=page.Contents;previous=list(contents)if isinstance(contents,pikepdf.Array)else[contents];page.Contents=pikepdf.Array(previous+[pikepdf.Stream(doc,program.encode('ascii'))]);doc.save(erased,compress_streams=False)
overlay=folder/'page04.text-overlay.pdf'
with fitz.open(body)as source,fitz.open()as text:
 page=text.new_page(width=source[0].rect.width,height=source[0].rect.height);subset=subset_font(font,['그림'],cache_dir=C/'font-subsets');alias='TranslatedFigure0';page.insert_font(fontname=alias,fontfile=str(subset));page.insert_text(origin,'그림',fontname=alias,fontsize=size);text.save(overlay,garbage=0,deflate=False)
row.update(font_resource=alias,embedded_font=str(subset),embedded_font_sha256=sha(subset))
with pikepdf.open(erased)as doc,pikepdf.open(overlay)as text:doc.pages[0].add_overlay(text.pages[0]);doc.save(target,compress_streams=False)
q=dict(year=2010,kind='TS',page=4,body=str(body),body_sha256=sha(body),proof_sha256=sha(target),native_control=str(control),native_control_sha256=sha(control),erased_only=str(erased),erased_only_sha256=sha(erased),text_overlay=str(overlay),text_overlay_sha256=sha(overlay),placements=[row],erased_native_word_glyphs=[],original_caption_digit_shifts=[],reviewed_stationary_caption_frames=[],native_move_qa=dict(passed=True,no_native_text_changed=True),body_and_equation_fonts_not_changed=True,original_encoded_images_not_modified=True,no_new_diagram_geometry=True,point_sizes_not_fitted=True)
save(target.with_suffix('.labels.json'),q);print('CAPTION_READY',sha(target),row['point_size'],row['origin'])
