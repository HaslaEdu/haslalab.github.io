from pathlib import Path
import sys,json,hashlib,contextlib,subprocess,gc,os
from PIL import Image,ImageChops
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');F=B/'natural/2016/TS';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
from izho_natural_spacing_ready import ready
from pdf_memory_gate import page_worker
assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
review=load(F/'visual-review.json');assert len(review['pages'])==8 and review['all_eight_source_pages_and_all_grading_schemes_complete'];pins={r['page']:r['proof_sha256']for r in review['pages']};counts=[]
for n in range(1,9):
 proof=F/f'page{n:02}.pdf';assert sha(proof)==pins[n]
 for suffix,key in[('.audit.json','output_sha256'),('.font-source-style.json','proof_sha256'),('.source-alignment.json','proof_sha256'),('.prose-collision.json','final_sha256'),('.equation-counters.json','proof_sha256'),('.non-hangul-prose-collision.json','proof_sha256'),('.actual-expression-geometry.json','proof_sha256')]:
  q=load(proof.with_suffix(suffix));assert q['passed']and q[key]==pins[n],(n,suffix)
 counts.append(load(proof.with_suffix('.equation-counters.json')));p=load(F/f'page{n:02}-preview.json');assert p['pdf_sha256']==pins[n]and p['png_sha256']==sha(F/f'page{n:02}-preview.png')
assert sum(c['equation_counters_checked']for c in counts)==51 and sum(c['native_counter_glyphs_checked']for c in counts)==178
neg=load(B/'natural/2016-actual-geometry-negative-controls/summary.json');assert neg['passed']and neg['positive_proofs_unmodified']and neg['actual_fraction_rule_negative_rejected']and neg['actual_score_glyph_negative_rejected']and neg['page03_positive_sha256']==pins[3]and neg['page08_positive_sha256']==pins[8]
with(B/'final-assembly.log').open('w',encoding='utf8')as log,contextlib.redirect_stdout(log):q=ready(2016,'TS',serialize_page_renders=True)
pdf=Path(q['output']);rows=[];POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
for n in range(1,9):
 with page_worker():
  out=F/f'page{n:02}-joined-poppler';r=subprocess.run([POP,'-f',str(n),'-l',str(n),'-singlefile','-r','144','-png',str(pdf),str(out)],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  with Image.open(F/f'page{n:02}-preview.png')as a,Image.open(out.with_suffix('.png'))as b:assert a.size==b.size and ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox()is None
 rows.append(dict(page=n,proof_sha256=pins[n],joined_vs_reviewed_changed_pixels=0,renderer='independent external Poppler144dpi',stderr=r.stderr.decode('utf8','replace')));print('EXACT_CURRENT_2016_ASSEMBLY_POPPLER_PASS',n,flush=True);gc.collect()
pdf.with_suffix('.poppler-assembly.json').write_text(json.dumps(dict(pdf_sha256=sha(pdf),pages=rows,passed=True),indent=2)+'\n','utf8');print('COMPLETE8_PAGE_2016_TS_NATIVE_APPEND_MUPDF_POPPLER_ZERO_DIFF_ALL51_LABELS178_GLYPHS_389_SELECTIONS_AND_ACTUAL_BAD_PDF_CONTROLS_PASS',sha(pdf),pdf.stat().st_size,flush=True)
