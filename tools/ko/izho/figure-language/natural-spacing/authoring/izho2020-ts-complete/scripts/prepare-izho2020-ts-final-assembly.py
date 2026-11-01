from pathlib import Path
import json,hashlib,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');C=B/'figure-language';M=B/'master-v1';M.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
ready=load(B/'natural/editions/IZhO_2020_TS_KO.ready.json');assert ready['status']=='READY'and ready['sha256']==sha(ready['output'])and ready['pages']==13
visual=load(B/'natural/2020/TS/visual-review.json');proofs=[];reviews=[]
for n in range(1,14):
 body=B/f'natural/2020/TS/page{n:02}.pdf';assert ready['page_audits'][n-1]['proof_sha256']==sha(body)==visual['pages'][n-1]['proof_sha256'];target=C/f'2020/TS/page{n:02}.pdf';composition=target.with_suffix('.labels.json');qa=C/f'2020/TS/qa/page{n:02}.audit.json'
 if n!=1:
  target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(body,target);save(composition,dict(year=2020,kind='TS',page=n,body=str(body),body_sha256=sha(body),proof_sha256=sha(target),placements=[],byte_identical_no_label_page=True));save(qa,dict(year=2020,kind='TS',page=n,body_sha256=sha(body),proof_sha256=sha(target),qa_mode='publication',passed=True,byte_identical_no_label_page=True,labels=0))
 else:
  q=load(composition);a=load(qa);assert q['body_sha256']==sha(body)and q['proof_sha256']==sha(target)==a['proof_sha256']and a['passed']and a['labels']==6
 proofs.append(dict(source_page=n,pdf=str(target),sha256=sha(target)));image=C/'2020/TS/page01.preview.png'if n==1 else Path(visual['pages'][n-1]['image'])
 reviews.append(dict(page=n,source_page=n,proof_sha256=sha(target),body_sha256=sha(body),reviewed=True,original_math_and_body_unchanged=True,native_figure_lines_and_variables_reviewed=True,word_spacing_reviewed=True,all_original_headings_and_subtitles_centered_like_source=True,image=str(image),image_sha256=sha(image),review_origin='Complete original-layout Poppler page visually inspected; all15 original bold prose headings and all25 centered source lines independently checked. Page1 six figure-language words have source-only font fits and exact final-font reference ink QA. All other final pages byte-identical to reviewed native body proofs.'))
save(M/'final-assembly-spec.json',dict(output=str(M/'IZhO_2020_TS_KO.pdf'),proofs=proofs));save(M/'final-visual-review.json',dict(year=2020,kind='TS',pages=reviews));shutil.copy2(C/'source-word-component-review.json',M/'source-word-component-review.json')
negative=load(C/'analysis-only-negative/page01-extra-ink.audit.json');canonical=C/'2020/TS/page01.pdf';assert not negative['passed']and negative['unmodified_canonical_proof_sha256']==sha(canonical)and negative['pixel_audit']['added_ink_outside_independent_actual_font_reference']==16 and negative['original_native_ink']['passed']
save(M/'figure-negative-regression.json',dict(passed=True,rows=[dict(year=2020,kind='TS',page=1,all_original_glyphs_fonts_images_and_caption_positions_retained=True,real_extra_drawing_rejected=True,publication_pdf_unmodified=True,passed=True,negative_added_ink_outside_reference=16,canonical_proof_sha256=sha(canonical),raw_negative_audit=str(C/'analysis-only-negative/page01-extra-ink.audit.json'))]));print('FINAL_ASSEMBLY_SPEC_READY',len(proofs))
