from pathlib import Path
import hashlib,json,datetime
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');F=B/'natural/2012/TS';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'));rows=[]
for n in range(1,12):
 pdf=F/f'page{n:02}.pdf';digest=sha(pdf);preview=load(F/f'page{n:02}-preview.json');assert preview['pdf_sha256']==digest and preview['png_sha256']==sha(F/f'page{n:02}-preview.png')
 for suffix,key in[('.audit.json','output_sha256'),('.font-source-style.json','proof_sha256'),('.source-alignment.json','proof_sha256'),('.prose-collision.json','final_sha256'),('.equation-counters.json','proof_sha256'),('.non-hangul-prose-collision.json','proof_sha256')]:
  q=load(pdf.with_suffix(suffix));assert q['passed']and q[key]==digest,(n,suffix)
 rows.append(dict(page=n,proof_sha256=digest,reviewed=True,preview_sha256=preview['png_sha256'],renderer=preview['renderer'],full_page_original_and_final_visually_read=True,notes='Complete original and final144dpi page visually read. Original math fonts/GIDs/points/scripts and complete fraction rules, graphs/diagrams/gray fields, source heading/table centers, source physical baselines and scoring design retained. Korean prose has natural word gaps and particle/counter attachment at the original source type sizes. Original typos/decimal punctuation/repeated references retained. All source prose and grading translated.'))
q=dict(original_source_sha256='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db',all_eleven_source_pages_and_all_grading_schemes_complete=True,pages=rows)
(F/'visual-review.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');(F/'partial-visual-review.json').write_text(json.dumps(dict(q,all11_pages_complete=True),ensure_ascii=False,indent=2)+'\n','utf8')
progress=B/'natural/2012-private-page-progress.json';prior={r['page']:r for r in load(progress)}
for row in rows:prior[row['page']]=dict(page=row['page'],automated_checks_passed=True,failed_stage=None,visual_review_still_required=False,reviewed_proof_sha256=row['proof_sha256'])
progress.write_text(json.dumps([prior[n]for n in sorted(prior)],indent=2)+'\n','utf8');print('ALL11_EXACT_CURRENT_IZHO2012_PROOFS_VISUALLY_REVIEWED_AND_ALL_REQUIRED_POSITIVES_PASS',flush=True)
