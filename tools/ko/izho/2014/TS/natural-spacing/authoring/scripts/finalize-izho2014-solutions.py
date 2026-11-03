from pathlib import Path
import sys,json,hashlib,contextlib,subprocess,gc
from PIL import Image,ImageChops
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2014-complete-solutions');F=B/'natural/2014/TS';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
from izho_natural_spacing_ready import ready
from pdf_memory_gate import page_worker
assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
review=load(F/'visual-review.json');assert len(review['pages'])==10 and review['all_ten_source_pages_and_all_grading_schemes_complete'];pins={r['page']:r['proof_sha256']for r in review['pages']};counts=[]
for n in range(1,11):
 proof=F/f'page{n:02}.pdf';assert sha(proof)==pins[n]
 for suffix,key in[('.audit.json','output_sha256'),('.font-source-style.json','proof_sha256'),('.source-alignment.json','proof_sha256'),('.prose-collision.json','final_sha256'),('.equation-counters.json','proof_sha256'),('.non-hangul-prose-collision.json','proof_sha256')]:
  q=load(proof.with_suffix(suffix));assert q['passed']and q[key]==pins[n],(n,suffix)
 c=load(proof.with_suffix('.equation-counters.json'));counts.append(c)
 p=load(F/f'page{n:02}-preview.json');assert p['pdf_sha256']==pins[n]and p['png_sha256']==sha(F/f'page{n:02}-preview.png')
assert sum(c['equation_counters_checked']for c in counts)==56 and sum(c['native_counter_glyphs_checked']for c in counts)==202
neg=load(B/'natural/2014-native-design-negatives-v2/negative-controls.json');assert neg['passed']and neg['all_actual_bad_PDFs_rejected']and len(neg['rows'])==3
for r in neg['rows']:assert r['negative_rejected']and r['delivered_proof_unmodified']and r['proof_sha256']==pins[r['page']]
with(B/'final-assembly.log').open('w',encoding='utf8')as log,contextlib.redirect_stdout(log):q=ready(2014,'TS',serialize_page_renders=True)
pdf=Path(q['output']);rows=[];POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
for n in range(1,11):
 with page_worker():
  out=F/f'page{n:02}-joined-poppler';r=subprocess.run([POP,'-f',str(n),'-l',str(n),'-singlefile','-r','144','-png',str(pdf),str(out)],check=True,capture_output=True)
  with Image.open(F/f'page{n:02}-preview.png')as a,Image.open(out.with_suffix('.png'))as b:assert a.size==b.size and ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox()is None
 rows.append(dict(page=n,proof_sha256=pins[n],joined_vs_reviewed_changed_pixels=0,renderer='independent external Poppler144dpi',stderr=r.stderr.decode('utf8','replace')));print('EXACT_CURRENT_2014_ASSEMBLY_POPPLER_PASS',n,flush=True);gc.collect()
pdf.with_suffix('.poppler-assembly.json').write_text(json.dumps(dict(pdf_sha256=sha(pdf),pages=rows,passed=True),indent=2)+'\n','utf8')
print('COMPLETE10_PAGE_2014_TS_NATIVE_APPEND_BOTH_RENDERERS_ALL56_COUNTERS_AND_ALL_ACTUAL_BAD_PDF_NEGATIVES_PASS',sha(pdf),pdf.stat().st_size,flush=True)
