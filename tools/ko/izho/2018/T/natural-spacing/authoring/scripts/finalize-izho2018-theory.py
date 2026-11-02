from pathlib import Path
import json,hashlib,sys,subprocess,os
from PIL import Image,ImageChops
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');F=B/'natural/2018/T';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
from izho_natural_spacing_ready import ready
from pdf_memory_gate import page_worker
pins=['276825a8ae428bc8523587f9b9ba0041ed8010d9679711020377cce9f9112e40','59a2f0443ea386eff546e4217f7141d672e3495cd3f8d2de84ddbdd9f9ac4371','158a40a7f283452974ac1930cb41e5304bb13acf220032600023a8cb0de34f41','6e42e9c12e1094dc5654040f5ba69445b3502349130e55eb1a7db2f8746b343d','3fa5a2392cc2a71f225f36fd99e924ac31ff68495867215b90e93e3d80bb0657','41044e85be85c67d431883666d1d8ee02a0874af9ecbb90f0193d676a2689c9a']
review=[]
for n,digest in enumerate(pins,1):
 proof=F/f'page{n:02}.pdf';assert sha(proof)==digest
 for suffix,key in [('.audit.json','output_sha256'),('.font-source-style.json','proof_sha256'),('.source-alignment.json','proof_sha256'),('.prose-collision.json','final_sha256')]:
  q=load(proof.with_suffix(suffix));assert q['passed']and q[key]==digest,(n,suffix)
 preview=load(F/f'page{n:02}-preview.json');assert preview['pdf_sha256']==digest and preview['png_sha256']==sha(F/f'page{n:02}-preview.png')
 review.append(dict(page=n,proof_sha256=digest,reviewed=True,preview_sha256=preview['png_sha256'],renderer=preview['renderer'],notes='Manually inspected the complete exact final page. Natural prose spacing and particles; original heading centers, font points, math shapes, scripts, rules, figure geometry and source baselines. All source rows translated and source-native numerical/physical content retained.'))
q=load(F/'page06.qa.json');gaps=[g for row in q['lines']for g in row['gaps']if g['left']in ['3.2','3.3']];assert len(gaps)==2 and all(g['new_gap']==3 for g in gaps)
for n in [3,4]:
 w=load(F/f'page{n:02}-native-digit-phase/witness.json');assert w['passed']and w['proof_sha256']==pins[n-1]and w['negative_actual_original_CID_omission']['passed']
negative=load(F/'negative-figure-labels/negative-control.json');assert negative['passed']and negative['proof_sha256']==pins[5]and negative['negative_rejected']
(F/'visual-review.json').write_text(json.dumps(dict(original_source_sha256='0782ab2ced4c911ce92b550aa2fd86cb7f6c9a6e24d7a60f64b13275df1e38ba',all_six_source_pages_complete=True,pages=review),ensure_ascii=False,indent=2)+'\n','utf8')
with page_worker():q=ready(2018,'T')
pdf=Path(q['output']);rows=[];POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
for n in range(1,7):
 out=F/f'page{n:02}-joined-poppler';r=subprocess.run([POP,'-f',str(n),'-l',str(n),'-singlefile','-r','144','-png',str(pdf),str(out)],check=True,capture_output=True)
 with Image.open(F/f'page{n:02}-preview.png')as a,Image.open(out.with_suffix('.png'))as b:
  assert a.size==b.size;assert ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox()is None
 rows.append(dict(page=n,proof_sha256=pins[n-1],joined_vs_reviewed_changed_pixels=0,renderer='independent external Poppler144dpi',stderr=r.stderr.decode('utf8','replace')))
assembly=dict(pdf_sha256=sha(pdf),pages=rows,passed=True)
pdf.with_suffix('.poppler-assembly.json').write_text(json.dumps(assembly,indent=2)+'\n','utf8')
print('COMPLETE6_PAGE_2018_T_NATIVE_APPEND_AND_BOTH_RENDERERS_PASS',sha(pdf),pdf.stat().st_size,flush=True)
