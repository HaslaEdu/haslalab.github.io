from pathlib import Path
import json,hashlib,sys,subprocess,contextlib
from PIL import Image,ImageChops
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');F=B/'natural/2011/TS';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
from izho_natural_spacing_ready import ready
from izho_2011_equation_counters import audit as counters
from pdf_memory_gate import page_worker
pins=['22ca3add78b2449ad628e35448a9e0f7f3ace74dccdda37dc22746ff48d648b8','e9cc8af19c2cc195bbc2fa70b487e66c7e8a0507ad226b65db8a2156b80a3feb','e65a352074d893cac71f3d886316e15d0e803e47f19cf272b97f287bcff10152','693974b1d04fbbf88a979b31d55b387980d1eb508327ebf16de8e541ca0af25e','e5b5cb6adc827f46172c69dfa78de90034b1bd090daa6a1be501bdd433a64510','d85b71a79588f23cb55e2f9f6b0230b64503b43f79f269d5df7a599b72973256','b5d8af6ce5c5921f94278fddd5371a3a1e2202c3f1680d3dbe0770ce336040c6','28f6e931dadbd0400e0c90c4c82496f5a4ffb64841cfa014e30b8b6764077d96','1df1b663981f242b30ed681f96846ecf2a75f7fe4d86aaa009cb4e01f2e50a53','a050bd311f6af082ff6fe051ec4c3798a0bb3bc3fd62fd86ceb15955f600d7b1']
review=[];counter_count=0;counter_glyphs=0
for n,digest in enumerate(pins,1):
 proof=F/f'page{n:02}.pdf';assert sha(proof)==digest
 for suffix,key in[('.audit.json','output_sha256'),('.font-source-style.json','proof_sha256'),('.source-alignment.json','proof_sha256'),('.prose-collision.json','final_sha256')]:
  q=load(proof.with_suffix(suffix));assert q['passed']and q[key]==digest,(n,suffix)
 c=counters(F/f'plans/page{n:02}.json');assert c['passed']and c['proof_sha256']==digest;counter_count+=c['equation_counters_checked'];counter_glyphs+=c['native_counter_glyphs_checked']
 preview=load(F/f'page{n:02}-preview.json');assert preview['pdf_sha256']==digest and preview['png_sha256']==sha(F/f'page{n:02}-preview.png')
 review.append(dict(page=n,proof_sha256=digest,reviewed=True,preview_sha256=preview['png_sha256'],renderer=preview['renderer'],notes='Manually inspected the complete final page against original source typography and diagram context. Source font roles/points/baselines and source heading/cell/caption centers; natural Korean spacing, original mathematical fonts/GIDs/fractional script points, complete original fraction rules, original display equation-label x/y, all source diagram/plot geometry and native scoring punctuation retained. All source prose, solutions and grading schemes translated.'))
assert counter_count==69 and counter_glyphs==246
row=next(r for r in load(F/'page03.qa.json')['lines']if abs(r['baseline']-84.84)<.02);assert len(row['gaps'])==2 and all(g['new_gap']==0 for g in row['gaps'])
for n,expressions,rules in[(4,1,1),(8,2,3)]:
 q=load(F/f'page{n:02}.inline-fractions.json');assert q['passed']and q['proof_sha256']==pins[n-1]and q['reviewed_complete_expressions']==expressions and q['original_fraction_rules_checked']==rules
 bad=load(F/f'negative-glyph-only-fraction-motion/{n}/actual-missing-common-fraction-rule-motion.json');assert not bad['passed']
bad=load(F/'negative-display-equation-counter-drift/actual-source-counter-drift-negative.json');assert not bad['passed']and any(r['number']==3 and not r['passed']for r in bad['rows'])
negative=load(B/'natural/2011-native-design-negatives/negative-controls.json');assert negative['passed']and len(negative['rows'])==2
for r in negative['rows']:assert r['negative_rejected']and r['delivered_proof_unmodified']and r['proof_sha256']==pins[r['page']-1]
(F/'visual-review.json').write_text(json.dumps(dict(original_source_sha256='ecc4a34a50fade6a08fd5f629480bebfa20ec418cdc19fa87915f6c0465ee008',all_ten_source_pages_and_all_grading_schemes_complete=True,original_display_equation_counters_checked=counter_count,original_counter_native_glyphs_checked=counter_glyphs,pages=review),ensure_ascii=False,indent=2)+'\n','utf8')
with(B/'final-assembly.log').open('w',encoding='utf8')as log,contextlib.redirect_stdout(log),page_worker():q=ready(2011,'TS')
pdf=Path(q['output']);rows=[];POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
for n in range(1,11):
 out=F/f'page{n:02}-joined-poppler';r=subprocess.run([POP,'-f',str(n),'-l',str(n),'-singlefile','-r','144','-png',str(pdf),str(out)],check=True,capture_output=True)
 with Image.open(F/f'page{n:02}-preview.png')as a,Image.open(out.with_suffix('.png'))as b:
  assert a.size==b.size;assert ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox()is None
 rows.append(dict(page=n,proof_sha256=pins[n-1],joined_vs_reviewed_changed_pixels=0,renderer='independent external Poppler144dpi',stderr=r.stderr.decode('utf8','replace')))
pdf.with_suffix('.poppler-assembly.json').write_text(json.dumps(dict(pdf_sha256=sha(pdf),pages=rows,passed=True),indent=2)+'\n','utf8')
print('COMPLETE10_PAGE_2011_TS_SOURCE_NATIVE_APPEND_BOTH_RENDERERS_AND_ALL69_EQUATION_COUNTERS_PASS',sha(pdf),pdf.stat().st_size,flush=True)
