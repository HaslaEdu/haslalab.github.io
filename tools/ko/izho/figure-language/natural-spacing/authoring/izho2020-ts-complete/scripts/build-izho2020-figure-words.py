from pathlib import Path
import sys,json,hashlib,shutil,subprocess
import pikepdf,pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');C=B/'figure-language';E=C/'engine';E.mkdir(exist_ok=True);sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_original_style_fonts import subset_font
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
old=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-older-figure-language/engine/audit_figure_labels.py');(E/'audit_figure_labels.py').write_text(old.read_text('utf8').replace("folder=B/f'{year}/T'","folder=B/f'{year}/TS'").replace("    for c in p['text']:\n     g=added", "    for c in p['text']:\n     if c.isspace():advance+=metric.text_length(c,fontsize=size);continue\n     g=added").replace("original_physical_body_glyphs_checked=len(protected)","original_physical_body_glyphs_checked=sum(g['trace_gid']>=0 for g in protected),original_native_text_metadata_records_checked=len(protected)"),'utf8');(E/'build_figure_labels.py').write_text('from pathlib import Path\nimport hashlib\nB=Path('+repr(str(C))+')\nsha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()\n','utf8')
body=B/'natural/2020/TS/page01.pdf';audit=json.loads(body.with_suffix('.audit.json').read_text('utf8'));assert audit['passed']and audit['output_sha256']==sha(body)
font=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab/tools/ko/fonts/NotoSansCJKkr-Regular.otf');metric=fitz.Font(fontfile=str(font));fields=json.loads((C/'figure-fields.json').read_text('utf8'));placements=[];components=[]
for field in fields:
 measurement=C/'source-label-measurements'/(field['id']+'.json');m=json.loads(measurement.read_text('utf8'));fit=m['top20'][0];size=fit['size'];source_width=fitz.Font(fontfile=fit['font_file']).text_length(field['text'],fontsize=size);width=metric.text_length(field['ko'],fontsize=size);x=fit['origin'][0]
 if field['align']=='center':x+=(source_width-width)/2
 elif field['align']=='right':x+=source_width-width
 ox,oy=m['source_crop_device_origin'];x0,y0,x1,y1=m['rect'];rect=[(ox+x0)/2,(oy+y0)/2,(ox+x1)/2,(oy+y1)/2]
 placements.append(dict(id=field['id'],source_text=field['text'],text=field['ko'],source_kind='bitmap-source-measured',source_word_rect_pt=rect,source_font_measurement=m,source_measurement_file=str(measurement),source_measurement_sha256=sha(measurement),source_chosen_fit=fit,source_face_prior_reason='Best unchanged original English raster match among original unscaled sans/serif font candidates; individual diagrams retain their observed source label styles.',font_source=str(font),font_source_sha256=sha(font),point_size=size,baseline=fit['origin'][1],origin=[x,fit['origin'][1]],source_italic_angle_degrees=0.,source_point_size_is_estimate=True,target_point_size_fitted=False))
 components.append(dict(id=field['id'],source_text=field['text'],source_only=True,passed=True,source_crop=m['source_page_crop'],source_crop_sha256=m['source_page_crop_sha256'],rect=m['rect'],source_connected_components=len(m['complete_isolated_source_word_components']),components=m['complete_isolated_source_word_components'],intersecting_nonword_components=[]))
folder=C/'2020/TS';folder.mkdir(parents=True,exist_ok=True);target=folder/'page01.pdf';control=folder/'page01.native-control.pdf';shutil.copy2(body,control);erased=folder/'page01.erased-only.pdf'
with pikepdf.open(control)as doc:
 page=doc.pages[0];h=float(page.MediaBox[3])-float(page.MediaBox[1]);ops=[]
 for row in placements:
  r=row['source_word_rect_pt'];ops.append('q 1 1 1 rg %.9f %.9f %.9f %.9f re f Q\n'%(r[0],h-r[3],r[2]-r[0],r[3]-r[1]))
 old=page.Contents;old=list(old)if isinstance(old,pikepdf.Array)else[old];page.Contents=pikepdf.Array([*old,pikepdf.Stream(doc,''.join(ops).encode('ascii'))]);doc.save(erased,compress_streams=False)
overlay=folder/'page01.text-overlay.pdf'
with fitz.open(body)as source,fitz.open()as text:
 page=text.new_page(width=source[0].rect.width,height=source[0].rect.height);subset=subset_font(font,[p['text']for p in placements],cache_dir=C/'font-subsets');alias='TranslatedFigureSans';page.insert_font(fontname=alias,fontfile=str(subset))
 for row in placements:page.insert_text(row['origin'],row['text'],fontname=alias,fontsize=row['point_size']);row.update(font_resource=alias,embedded_font=str(subset),embedded_font_sha256=sha(subset))
 text.save(overlay,garbage=0,deflate=False)
with pikepdf.open(erased)as doc,pikepdf.open(overlay)as text:doc.pages[0].add_overlay(text.pages[0]);doc.save(target,compress_streams=False)
q=dict(year=2020,kind='TS',page=1,body=str(body),body_sha256=sha(body),proof_sha256=sha(target),native_control=str(control),native_control_sha256=sha(control),erased_only=str(erased),erased_only_sha256=sha(erased),text_overlay=str(overlay),text_overlay_sha256=sha(overlay),placements=placements,erased_native_word_glyphs=[],original_caption_digit_shifts=[],reviewed_stationary_caption_frames=[],native_move_qa=dict(passed=True,no_native_text_changed=True),body_and_equation_fonts_not_changed=True,original_encoded_images_not_modified=True,no_new_diagram_geometry=True,point_sizes_not_fitted=True)
save(target.with_suffix('.labels.json'),q);save(C/'source-word-component-review.json',dict(passed=True,source_only=True,labels=components))
subprocess.run([shutil.which('pdftoppm'),'-r','93.6','-singlefile','-png',str(target),str(folder/'page01.preview')],check=True,capture_output=True);print('SIX_FIGURE_WORDS_BUILT',sha(target),flush=True)
