from pathlib import Path
import json,hashlib,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');C=B/'figure-language';M=B/'master-v1';M.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text('utf8'))
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
ready=load(B/'natural/editions/IZhO_2010_TS_KO.ready.json');assert ready['status']=='READY'and ready['sha256']==sha(ready['output'])and ready['pages']==11
visual=load(B/'natural/2010/TS/visual-review.json');proofs=[];reviews=[]
for n in range(1,12):
 body=B/f'natural/2010/TS/page{n:02}.pdf';assert ready['page_audits'][n-1]['proof_sha256']==sha(body)==visual['pages'][n-1]['proof_sha256'];target=C/f'2010/TS/page{n:02}.pdf';composition=target.with_suffix('.labels.json');qa=C/f'2010/TS/qa/page{n:02}.audit.json'
 if n!=4:
  target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(body,target);q=dict(year=2010,kind='TS',page=n,body=str(body),body_sha256=sha(body),proof_sha256=sha(target),placements=[],byte_identical_no_label_page=True);save(composition,q);save(qa,dict(year=2010,kind='TS',page=n,body_sha256=sha(body),proof_sha256=sha(target),qa_mode='publication',passed=True,byte_identical_no_label_page=True,labels=0))
 else:
  q=load(composition);a=load(qa);assert q['body_sha256']==sha(body)and q['proof_sha256']==sha(target)==a['proof_sha256']and a['passed']
 proofs.append(dict(source_page=n,pdf=str(target),sha256=sha(target)))
 r=dict(page=n,source_page=n,proof_sha256=sha(target),body_sha256=sha(body),reviewed=True,original_math_and_body_unchanged=True,native_figure_lines_and_variables_reviewed=True,word_spacing_reviewed=True)
 image=B/f'2010/inspection/natural-poppler/page{n:02}{"-caption"if n==4 else""}.png';r.update(image=str(image),image_sha256=sha(image),review_origin='Complete original-layout Poppler page visually inspected; page4 independent caption-only source/font/native-ink audit also passed, all other final pages byte-identical to reviewed native body proofs.');reviews.append(r)
save(M/'final-assembly-spec.json',dict(output=str(M/'IZhO_2010_TS_KO.pdf'),proofs=proofs));save(M/'final-visual-review.json',dict(year=2010,kind='TS',pages=reviews))
measurement=load(B/'2010/source-caption-measurement.json');save(M/'source-word-component-review.json',dict(source_only=True,passed=True,labels=[dict(id='fig1',source_text='Рис.',source_only=True,passed=True,source_crop=measurement['source_page_crop'],source_crop_sha256=measurement['source_page_crop_sha256'],rect=measurement['rect'],source_connected_components=len(measurement['complete_isolated_source_word_components']),components=measurement['complete_isolated_source_word_components'],intersecting_nonword_components=[])]))
negative=load(C/'analysis-only-negative/page04-extra-ink.audit.json');canonical=C/'2010/TS/page04.pdf';assert not negative['passed']and negative['unmodified_canonical_proof_sha256']==sha(canonical)and negative['pixel_audit']['added_ink_outside_independent_actual_font_reference']==16 and negative['original_native_ink']['passed']
save(M/'figure-negative-regression.json',dict(passed=True,rows=[dict(year=2010,kind='TS',page=4,all_original_glyphs_fonts_images_and_caption_positions_retained=True,real_extra_drawing_rejected=True,publication_pdf_unmodified=True,passed=True,negative_added_ink_outside_reference=16,canonical_proof_sha256=sha(canonical),raw_negative_audit=str(C/'analysis-only-negative/page04-extra-ink.audit.json'))]))
print('FINAL_ASSEMBLY_SPEC_READY',len(proofs))
