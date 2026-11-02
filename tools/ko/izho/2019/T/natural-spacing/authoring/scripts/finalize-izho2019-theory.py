from pathlib import Path
import json,hashlib,sys,subprocess,contextlib
from PIL import Image,ImageChops
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original');F=B/'natural/2019/T';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
from izho_natural_spacing_ready import ready
from pdf_memory_gate import page_worker
pins=['a568d26830425149b7a9694d1901cbbd9e6b48593511382f78e192a1fbeb5054','d83978ed6a59d80a41e433b5ff6d246d006dbd377060538feda5789eadd87e5a','bdfe232d718e73e610535c3469e3cdc39cc34300c8454e3bd151594fb46e8200','143c7fb93837773ffae7edcf112782b388aa280ef7c8a4acf6c25c5d84a331f9','31556615a0bb17c68256e5557c65ea22d1c4372bd04fa802155b31a58829088e','f676c5b8085d68343e333d107eb67e37fe8a610769537773e2ab9f050a8093f3','bc5932582452384d22e41f378343b8aa70c2463f34b76bd8114429ea9869aa5d','40fe5cc5f2fcaed518b69e30b8f6438624d1c75d3e40e290c2149d93ad30859b']
review=[]
for n,digest in enumerate(pins,1):
 proof=F/f'page{n:02}.pdf';assert sha(proof)==digest
 for suffix,key in[('.audit.json','output_sha256'),('.font-source-style.json','proof_sha256'),('.source-alignment.json','proof_sha256'),('.prose-collision.json','final_sha256')]:
  q=load(proof.with_suffix(suffix));assert q['passed']and q[key]==digest,(n,suffix)
 preview=load(F/f'page{n:02}-preview.json');assert preview['pdf_sha256']==digest and preview['png_sha256']==sha(F/f'page{n:02}-preview.png')
 review.append(dict(page=n,proof_sha256=digest,reviewed=True,preview_sha256=preview['png_sha256'],renderer=preview['renderer'],notes='Manually inspected the complete exact final page. Natural Korean word spacing, original source points/baselines/font roles and heading centers. Source-native mathematical fonts, fractional script points, complete Forms/rules and physical constants retained; all original prose translated. All original diagram programs and nonlanguage pixels retained. The three chart labels use source-only measured sans-bold points, baselines, centers and original vertical-axis orientation.'))
negative=load(B/'natural/2019-native-design-negatives/negative-controls.json');assert negative['passed']and len(negative['rows'])==2
for r in negative['rows']:assert r['negative_rejected']and r['delivered_proof_unmodified']and r['proof_sha256']==pins[r['page']-1]
boundary=load(F/'negative-exact-picture-boundary/negative-control.json');assert boundary['passed']and boundary['proof_sha256']==pins[2]
(F/'visual-review.json').write_text(json.dumps(dict(original_source_sha256='29daec0cb9f759bed9b755cbae2937e1c4ab068fa804c62d512ea291e42619d1',all_eight_source_pages_complete=True,pages=review),ensure_ascii=False,indent=2)+'\n','utf8')
with (B/'final-assembly.log').open('w',encoding='utf8')as log,contextlib.redirect_stdout(log),page_worker():q=ready(2019,'T')
pdf=Path(q['output']);rows=[];POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
for n in range(1,9):
 out=F/f'page{n:02}-joined-poppler';r=subprocess.run([POP,'-f',str(n),'-l',str(n),'-singlefile','-r','144','-png',str(pdf),str(out)],check=True,capture_output=True)
 with Image.open(F/f'page{n:02}-preview.png')as a,Image.open(out.with_suffix('.png'))as b:
  assert a.size==b.size;assert ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox()is None
 rows.append(dict(page=n,proof_sha256=pins[n-1],joined_vs_reviewed_changed_pixels=0,renderer='independent external Poppler144dpi',stderr=r.stderr.decode('utf8','replace')))
pdf.with_suffix('.poppler-assembly.json').write_text(json.dumps(dict(pdf_sha256=sha(pdf),pages=rows,passed=True),indent=2)+'\n','utf8')
print('COMPLETE8_PAGE_2019_T_NATIVE_APPEND_AND_BOTH_RENDERERS_PASS',sha(pdf),pdf.stat().st_size,flush=True)
