from pathlib import Path
import sys,json,hashlib,shutil,subprocess,os,importlib.metadata
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');R=B.parents[2];M=B/'master-v1';F=M/'authoring-frozen';sys.path.insert(0,str(B/'engine'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
from pdf_memory_gate import page_worker
from cpho2007_ts_runtime import source_page
from cpho2007_ts_initial_native_baseline import translated_text
import pikepdf
source=B/'inputs/CPhO_2007_Chinese_original.pdf';assert sha(source)=='2e30b56ab9274363686cbf5bc1ef7532dcf579e0703de2c01098b003ab70cdd9'
review=B/'authoring/full144-visual-review-complete.json';visual=json.loads(review.read_text('utf8'));assert len(visual['pages'])==32 and all(v['passed']and v['full_original_and_current_proof_144dpi_visually_reviewed']for v in visual['pages'])
assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
assert not(M/'READY.json').exists();M.mkdir(exist_ok=True);copies=[]
def copy(src,dst):
 src=Path(src);dst=Path(dst);assert dst.resolve().is_relative_to(M.resolve());dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():assert sha(src)==sha(dst),('An existing private snapshot cannot be overwritten',src,dst)
 else:shutil.copy2(src,dst)
 assert sha(src)==sha(dst);copies.append(dict(original_path=str(src),frozen_path=str(dst),sha256=sha(dst),bytes=dst.stat().st_size))
for p in (B/'engine').glob('*.py'):copy(p,F/'engine'/p.name)
for p in R.glob('*cpho2007*.py'):copy(p,F/'drivers'/p.name)
for p in (B/'inputs').glob('*'):
 if p.is_file():copy(p,F/'inputs'/p.name)
for p in (B/'authoring').glob('*'):
 if p.is_file()and(p.name.startswith('page')or p.name in['full144-visual-review-complete.json','complete-inline-expressions-evidence.json','complete-inline-expressions-candidate.json','complete-inline-expressions-review.txt','retained-original-prose-punctuation-evidence.json']):copy(p,F/'authoring'/p.name)
copy(B/'tools/ko/cpho/2007/natural/atomic-inline.json',F/'tools/ko/cpho/2007/natural/atomic-inline.json')
current=[];font_names=set()
for v in visual['pages']:
 n=v['source_page'];lang=v['language'];proof=Path(v['proof']);audit=json.loads(proof.with_suffix('.audit.json').read_text('utf8'));assert audit['passed']and audit['output_sha256']==sha(proof)==v['proof_sha256']
 if n<20:
  assert audit['independent_actual_new_prose_native_text_ink']['passed'];auth=json.loads((B/f'authoring/page{n:02}-bilingual-prose.json').read_text('utf8'))['prose'];jpath=B/f'native-baseline/{lang}/page{n:02}-source-indexed.build.json';journal=json.loads(jpath.read_text('utf8'));assert {r['id']:r['text']for r in journal['fit_report']}=={s['id']:translated_text(s,auth[s['id']][lang])for s in source_page(n)['slots']};font_names.update(r['font']for r in journal['fit_report'])
  for p in (B/f'native-baseline/{lang}').glob(f'page{n:02}*'):
   if p.is_file():copy(p,F/p.relative_to(B))
 for p in proof.parent.glob(f'page{n:02}*'):
  if p.is_file()and p.suffix in['.pdf','.json']:copy(p,F/p.relative_to(B))
 copy(v['png'],F/'reviewed-proofs144'/lang/Path(v['png']).name);copy(v['source_png'],F/'source-renders'/Path(v['source_png']).name)
 current.append(dict(language=lang,source_page=n,proof_sha256=sha(proof),audit_sha256=sha(proof.with_suffix('.audit.json')),full144_visual_review_passed=True,strict_page_QA_passed=True))
for p in (B/'private-font-subsets').rglob('*'):
 if p.is_file()and p.name in font_names:copy(p,F/p.relative_to(B))
neg=B/'evidence/negative-controls-v2';names=['negative-control-manifest.json','page06-exact-radical-negative-control-manifest.json'];negative=[]
for name in names:
 q=json.loads((neg/name).read_text('utf8'));assert q['all_rejected'];copy(neg/name,F/'negative-controls'/name);negative.append(dict(path=str(F/'negative-controls'/name),sha256=sha(neg/name),controls=len(q['controls'])))
 for control in q['controls']:
  for key in['fixture','report']:
   value=control.get(key)
   if isinstance(value,str)and Path(value).is_file():copy(value,F/'negative-controls'/Path(value).name)
  if control.get('proof_sha256')and not control.get('fixture'):
   matches=[p for p in (B/'history').rglob('page05.pdf')if sha(p)==control['proof_sha256']];assert len(matches)==1;copy(matches[0],F/'negative-controls/real-rejected-page05-KO-original-comma-geometry.pdf')
font_sources=[Path('C:/Windows/Fonts/batang.ttc'),B.parents[1]/'english-face-repair/font-faces/SimSun-5.24.ttf',B.parents[1]/'official-hans-fonts/faces/simhei.ttf',Path('D:/CodexBuilds/Hasla-publish-20261031/tools/ko/fonts/NotoSerifCJKkr-Regular.otf'),Path('D:/CodexBuilds/Hasla-publish-20261031/tools/ko/fonts/NotoSansCJKkr-Regular.otf')]
(F/'external-font-source-pins.json').write_text(json.dumps([dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size,full_font_copied=False)for p in font_sources],ensure_ascii=False,indent=2)+'\n','utf8')
(F/'path-and-replay-map.json').write_text(json.dumps(dict(source_sha256=sha(source),historical_frozen_source_paths_unchanged=True,old_workspace_prefix='C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab',current_workspace_prefix='C:/Users/andre/CodexWork/HaslaLab/haslalab',actual_private_authoring_root=str(B),frozen_root=str(F),maps=['inputs -> inputs','authoring -> authoring','engine -> engine','native-baseline -> native-baseline','natural/2007 -> natural/2007','tools/ko/cpho/2007/natural -> tools/ko/cpho/2007/natural','proof-renders-144 -> reviewed-proofs144'],replay_instruction='Keep this snapshot immutable. Copy its inputs,authoring,tools,native-baseline,natural into a separately named scratch directory. Import the exact frozen engine first; before configure/audit set cpho2007_ts_runtime.B to that scratch root and SOURCE to its pinned inputs/CPhO_2007_Chinese_original.pdf. All heavy audit/render calls must hold pdf_memory_gate.page_worker. The external full font pins are required only for regeneration; native PDFs contain the exact subsets used by inspection and renderer QA.'),ensure_ascii=False,indent=2)+'\n','utf8')
(F/'copy-provenance.json').write_text(json.dumps(copies,ensure_ascii=False,indent=2)+'\n','utf8')
editions=[]
with page_worker():
 for lang in['ko','en']:
  target=M/f'CPhO_2007_TS_{lang.upper()}.pdf'
  if not target.exists():
   with pikepdf.Pdf.new()as dst:
    for n in range(5,21):
     with pikepdf.open(F/f'natural/2007/{lang}/page{n:02}.pdf')as src:assert len(src.pages)==1;dst.pages.append(src.pages[0])
    dst.save(target,compress_streams=False)
  with pikepdf.open(target)as pdf:assert len(pdf.pages)==16
  editions.append(dict(language=lang,path=str(target),sha256=sha(target),bytes=target.stat().st_size,pages=16,source_physical_pages=list(range(5,21)),method='Native page append; no rasterization, redraw, refonting, text fitting, retypeset mathematics, or changed page boxes.'))
(M/'edition-candidates.json').write_text(json.dumps(editions,ensure_ascii=False,indent=2)+'\n','utf8');print('PRIVATE_NATIVE_CPHO2007_TS_EDITIONS_APPENDED',editions,flush=True)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf8',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');reports=[]
for lang in['ko','en']:
 for n in range(5,21):
  report=M/f'verification/{lang}-page{n:02}.json'
  if not report.exists():subprocess.run([sys.executable,str(R/'verify-cpho2007-ts-combined-page.py'),lang,str(n)],env=env,check=True)
  q=json.loads(report.read_text('utf8'));assert q['passed']and q['edition_sha256']==next(e['sha256']for e in editions if e['language']==lang);reports.append(q)
assert len(reports)==32 and all(r['fresh_separate_process_MuPDF4x_RGB_difference_pixels']==r['Poppler144_RGB_difference_pixels']==0 for r in reports)
versions={}
for package in['PyMuPDF','pikepdf','fonttools','Pillow','numpy','opencv-python']:
 try:versions[package]=importlib.metadata.version(package)
 except importlib.metadata.PackageNotFoundError:versions[package]='not-distribution-named'
(M/'verification/summary.json').write_text(json.dumps(dict(passed=True,pages=32,MuPDF4x_RGB_difference_pixels=0,Poppler144_RGB_difference_pixels=0,native_content_font_glyph_and_image_programs_identical=True,versions=versions,python=sys.version,individual_pages=current),ensure_ascii=False,indent=2)+'\n','utf8')
files=[dict(path=str(p.relative_to(M)),sha256=sha(p),bytes=p.stat().st_size)for p in M.rglob('*')if p.is_file()and p.name not in['snapshot-manifest.json','READY.json']]
manifest=M/'snapshot-manifest.json';manifest.write_text(json.dumps(dict(status='COMPLETE_PRIVATE_NATIVE_CPHO2007_TS_BILINGUAL_SNAPSHOT',source_sha256=sha(source),files=files),ensure_ascii=False,indent=2)+'\n','utf8')
ready=dict(status='READY_PRIVATE_FOR_PARENT_PUBLICATION',source_sha256=sha(source),source_physical_pages=list(range(5,21)),editions=editions,full_original_and_current_proof_144dpi_visual_review_pages=32,visual_review_manifest_sha256=sha(review),native_script_graphics_original_font_image_and_actual_prose_over_math_ink_audits_passed=True,negative_controls=negative,all5_actual_negative_controls_rejected=True,combined_fresh_MuPDF4x_RGB_difference_pixels=0,combined_Poppler144_RGB_difference_pixels=0,combined_verified_pages=32,original_blank_final_folio20_retained=True,original_unmapped_comparison_square_on_source18_retained=True,original_math_CID_font_point_paint_Y_and_graphic_programs_preserved=True,new_Hangul_font_roles='Windows Batang source-size body and NotoSansCJKkr source-size SimHei-role title/section; new English uses actual original SimSun5.24/SimHei5.03; original math/Latin CID programs remain native.',snapshot_manifest=str(manifest),snapshot_manifest_sha256=sha(manifest),snapshot_files=len(files),external_publication_or_repository_mutation_performed=False)
(M/'READY.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2)+'\n','utf8');print('CPHO2007_TS_PRIVATE_READY',json.dumps(ready,ensure_ascii=False),flush=True)
