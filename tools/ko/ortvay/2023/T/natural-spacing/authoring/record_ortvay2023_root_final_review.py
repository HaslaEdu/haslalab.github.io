"""Pin the root's all-page source/target review to the final O2023 proofs."""
from pathlib import Path
import hashlib,json
B=Path(__file__).resolve().parents[1]
F=B/'proofs/ortvay/2023'
read=lambda p:json.loads(p.read_text('utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SOURCE='c0a5117145c67edc2dfe8953dcc7865438f65e099fe6e73b2ec19616ab27b5f7'
COMPOSER='733a37d56fc7274d28ca8f2b9b8742d039996ef0e1324d40bdc62bdba7dc046c'

def main():
 ready_path=B/'staged/ortvay2023-READY.json';ready=read(ready_path)
 assert ready['status']=='READY_FOR_ROOT_INDEPENDENT_REVIEW_AND_ASSEMBLY'
 assert ready['pages']==13 and ready['source_sha256']==SOURCE and ready['composer_sha256']==COMPOSER
 source_review=B/'source-review/ortvay2023/root-original-pages-read.json'
 source=read(source_review);assert source['source_sha256']==SOURCE
 assert [p['page']for p in source['pages']]==list(range(1,14))
 for row in source['pages']:assert sha(Path(row['png']))==row['png_sha256']
 old_review=read(F/'root-independent-candidate-review.json')
 old={p['page']:p for p in old_review['pages']}
 body_path=F/'title-fix-body-replay-regression.json';body=read(body_path)
 assert body['passed']and body['composer_sha256']==COMPOSER
 assert [p['page']for p in body['pages']]==[2,3,4,5,6,7,8,10]
 for row in body['pages']:
  assert row['canonical_all_glyph_traces_identical']and row['changed_pixels']==0
  assert row['old_png_sha256']==row['png_sha256']
  if row['page']in {2,3,4,5,6}:assert row['png_sha256']==old[row['page']]['files']['render']['sha256']
 rows=[]
 for p in ready['proofs']:
  n=p['page'];pdf=Path(p['proof_path']);png=Path(p['png_path']);layout=F/f'page{n:02}.layout.json';q=read(layout)
  assert p['proof_sha256']==sha(pdf)==q['output_sha256']
  assert p['png_sha256']==sha(png)and p['layout_sha256']==sha(layout)
  assert q['source_sha256']==SOURCE and q['composer_sha256']==COMPOSER==sha(Path(q['composer_path']))
  assert p['reviewed']and q['new_korean_glyph_and_geometry_audit']['passed']
  rows.append(dict(page=n,reviewed=True,proof_sha256=sha(pdf),png_sha256=sha(png),layout_sha256=sha(layout),
   source_and_target_visually_read=True,review_method='Final PNG read'if n in {1,7,8,9,10,11,12,13}else'Root-read candidate PNG retained byte-for-byte; independent final body replay also passed'))
 center_path=F/'original-title-center-independent-audit.json';center=read(center_path)
 assert center['passed']and center['proof_sha256']==rows[0]['proof_sha256']
 assert center['program_sha256']==sha(B/'composer/audit_ortvay2023_title_centers.py')
 assert len(center['rows'])==4 and all(r['center_error_pt']<=.001 for r in center['rows'])
 row_path=F/'korean-inter-row-ink-audit.json';inter=read(row_path)
 assert inter['passed']and inter['stale_pages']==[]and len(inter['pages'])==13
 count=0
 for row in inter['pages']:
  assert row['proof_sha256']==rows[row['page']-1]['proof_sha256']and row['passed']and row['failures']==[]
  assert len(row['pairs'])==row['tested_close_row_pairs']and all(p['contact_pixels_2x']==0 for p in row['pairs'])
  count+=row['tested_close_row_pairs']
 assert count==337
 link_path=B/'experiments/ortvay2023-link-subsets/regression.json';links=read(link_path)
 assert links['status']=='PASS'and links['changed_pixels']==0 and len(links['negative_regressions'])==6
 assert all(r['proof_sha256']==rows[r['page']-1]['proof_sha256']and r['layout_sha256']==rows[r['page']-1]['layout_sha256']for r in links['pages'])
 evidence=[ready_path,source_review,body_path,center_path,row_path,link_path]
 report=dict(status='PASS',source_sha256=SOURCE,composer_sha256=COMPOSER,program_sha256=sha(Path(__file__)),
  pages=rows,korean_interrow_pairs=count,all_original_and_final_pages_visually_read=True,
  title_centers_source_measured=True,original_math_figures_font_sizes_baselines_and_native_identifiers_retained=True,
  evidence=[dict(path=str(p),sha256=sha(p))for p in evidence],
  notes=['Title four source centers restored without font shrink or letter-spacing changes.',
   'All33 questions and source author credits/page numbers/source end-document artifact retained.',
   'p9 distance-a and force-expansion clauses read in their final corrected order.',
   'p11 complete proper-time fuel-fraction conditions, p12 current ground state/SU(2) arguments and p13 allfour questions compared with original.'])
 target=B/'staged/ortvay/review-2023/root-independent-final-review.json';target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
 print('ROOT_ORIGINAL_AND_FINAL13_PAGE_REVIEW_PASS',sha(target),flush=True)

if __name__=='__main__':main()
