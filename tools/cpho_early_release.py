"""Assemble audited three-page original-layout editions; pin exact authoring bytes."""
from pathlib import Path
from datetime import datetime
import json,os,time,shutil,subprocess,hashlib
import pikepdf,numpy as np
from PIL import Image
import cpho_early_natural as a
from izho_natural_spacing_qa import fresh_render
from pdf_memory_gate import page_worker
POPPLER=Path('C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
EXTERNAL=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho-early-natural')

def dump(path,data):
 tmp=Path(path).with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf8');os.replace(tmp,path)
def poppler(path,page,prefix):
 subprocess.run([str(POPPLER),'-f',str(page),'-l',str(page),'-r','144','-singlefile','-png',str(path),str(prefix)],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
 with Image.open(str(prefix)+'.png')as im:return np.asarray(im.convert('RGB'))

def authoring(year):
 entries=[];manifest=json.loads((a.BASE/'engine-manifest.json').read_text('utf8'))
 for item in manifest['modules']:
  p=a.BASE/item['path']
  if a.core.sha(p)!=item['sha256']:raise ValueError('Frozen render engine changed')
  entries.append(dict(path=item['path'],sha256=item['sha256']))
 for name in('pdf_native_geometry_stroke_motion.py','test_native_stroke_motion.py','cpho_early_validation.py','cpho_early_release.py','cpho_2013_yttrium_revision.py'):
  source=EXTERNAL/'tools'/name;dest=a.BASE/'tools'/name
  if dest.exists()and dest.read_bytes()!=source.read_bytes():raise ValueError('QA extension snapshot already has different bytes')
  if not dest.exists():shutil.copy2(source,dest)
  entries.append(dict(path='tools/'+name,sha256=a.core.sha(dest)))
 data=[]
 def add(source,relative):
  dest=a.BASE/relative;dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists()and dest.read_bytes()!=Path(source).read_bytes():raise ValueError(('Authoring data byte conflict',relative))
  if not dest.exists():shutil.copy2(source,dest)
  data.append(dict(path=relative,sha256=a.core.sha(dest)))
 prefix=f'tools/ko/cpho/{year}/natural'
 add(a.BASE/f'immutable-input-journals/{year}/native-slots.json',f'tools/ko/cpho/{year}/original/native-slots.json')
 add(a.BASE/'prose-edits.json',prefix+'/prose-edits.json')
 add(a.BASE/f'authoring-root/tools/ko/cpho/{year}/natural/atomic-inline.json',prefix+'/atomic-inline.json')
 for lang in('ko','en'):
  for n in(1,2,3):add(a.BASE/f'immutable-input-journals/{year}/{lang}/page{n:02}.build.json',prefix+f'/immutable-input-journals/{lang}/page{n:02}.build.json')
  add(a.BASE/f'numeric-stage/{year}/{lang}/complete-source-number-faces.json',prefix+f'/numeric-face-stage/{lang}.json')
 add(a.BASE/'immutable-inputs.json','tools/ko/cpho/early-natural/immutable-inputs.json')
 add(a.BASE/'engine-manifest.json','tools/ko/cpho/early-natural/build-engine-manifest.json')
 add(EXTERNAL/'stroke-audit-regression/report.json','tools/ko/cpho/early-natural/stroke-audit-regression.json')
 if year==2013:
  add(EXTERNAL/'source-label-check/2013-laser-label.png',prefix+'/source-yttrium-label.png')
  add(a.BASE/'revision-yttrium-body/material-terminology.json',prefix+'/material-terminology-revision.json')
 return entries+data

def assemble(year,proof_root=None):
 files=[];allqa=[];folder=Path(proof_root)if proof_root else a.BASE/f'output/{year}';editions=folder/'editions';editions.mkdir(exist_ok=True)
 for lang in('ko','en'):
  root=folder/lang;target=editions/f'CPhO_{year}_T_{lang.upper()}.pdf';reports=[]
  with pikepdf.Pdf.new()as out:
   for n in(1,2,3):
    proof=root/f'page{n:02}.pdf';q=json.loads(proof.with_suffix('.audit.json').read_text('utf8'))
    if not q['passed']or q['output_sha256']!=a.core.sha(proof):raise ValueError(('Not an audited final page',year,lang,n))
    with pikepdf.open(proof)as src:out.pages.append(src.pages[0])
    reports.append(q)
   out.save(target,compress_streams=False)
  renders=root/'combined-render-qa';renders.mkdir(exist_ok=True)
  for n,q in enumerate(reports,1):
   proof=root/f'page{n:02}.pdf'
   with page_worker():
    before=fresh_render(proof,1,renders/f'proof-{n:02}.png');after=fresh_render(target,n,renders/f'combined-{n:02}.png');mu=int(np.any(before!=after,axis=2).sum())
   time.sleep(.6)
   with page_worker():
    before=poppler(proof,1,renders/f'poppler-proof-{n:02}');after=poppler(target,n,renders/f'poppler-combined-{n:02}');pp=int(np.any(before!=after,axis=2).sum())
   time.sleep(.6)
   if mu or pp:raise ValueError(('Combined PDF changed a verified proof',year,lang,n,mu,pp))
   q.update(combined_vs_proof_MuPDF_4x_changed_pixels=mu,combined_vs_proof_Poppler_144dpi_changed_pixels=pp)
   print('JOIN QA',year,lang,n,mu,pp,flush=True)
  qa=target.with_suffix('.qa.json');dump(qa,dict(passed=True,output_sha256=a.core.sha(target),pages=reports,visual_review='Each final page individually inspected; original figures, formula geometry, native faces, complete centered title/header/footer and ordinary prose spacing.'))
  files.append(dict(path=str(target),sha256=a.core.sha(target),bytes=target.stat().st_size,pages=3,language=lang.upper(),kind='T',qa=str(qa),qa_sha256=a.core.sha(qa),immutable_translation_input=str(a.baseline(year,lang)),immutable_translation_input_sha256=a.core.sha(a.baseline(year,lang))))
  allqa.extend(reports)
 authors=authoring(year)
 inventory=dict(status='READY_NATURAL_SPACING_ORIGINAL_RESOURCES',qa_schema='cpho-early-original-natural-v1',year=year,generated_at=datetime.now().isoformat(),source=str(a.original(year)),source_sha256=a.core.sha(a.original(year)),source_pages=[1,2,3],files=files,
  style_policy='Original Chinese-native layout and original figures. Native physical CID/font/GID/program/point-size/paint/y preserved, reviewed x motion only; full fractions/radicals move atomically with original bars. Regular Korean serif is Batang at original size; original sans/bold/italic roles retained. English source SimSun/official SimHei; source TNR numerical title/footer faces restored. Quarter-em word space, no font scaling or reflow.',
  checked_pages=6,original_physical_native_ink_missing_pixels=sum(q['original_physical_native_ink']['newly_missing_native_ink_pixels']for q in allqa),nonselected_native_graphics_changed_pixels=sum(q['native_graphics_motion_audit']['changed_nonselected_native_graphical_pixels']for q in allqa),changed_pixels_outside_text_and_declared_math_motion=sum(q['changed_pixels_outside_old_and_new_text_ink']for q in allqa),Hangul_visibility_components=sum(q['hangul_visibility']['flagged_components']for q in allqa),prose_over_native_text_dark_pixels=sum(q['prose_native_text_overlap']['dark_pixels']for q in allqa),
  original_expression_relative_geometry_preserved=all(q['original_native_expression_relative_geometry']['passed']for q in allqa),native_script_base_pairs_checked=sum(len(q['original_native_expression_relative_geometry']['script_base_pairs'])for q in allqa),complete_native_expressions_checked=sum(len(q['original_native_expression_relative_geometry']['reviewed_expression_groups'])for q in allqa),maximum_complete_expression_relative_x_error_pt=max([r['relative_x_spread_pt']for q in allqa for r in q['original_native_expression_relative_geometry']['reviewed_expression_groups']]+[0]),
  source_numeric_font_programs_and_GIDs_verified=all(q['source_numerical_prose_and_whole_heading_alignment']['passed']for q in allqa),maximum_whole_heading_alignment_error_pt=max([r['error_pt']for q in allqa for r in q['source_numerical_prose_and_whole_heading_alignment']['complete_heading_footer_lines']]+[0]),translation_style_violations=[r for q in allqa for r in q['independent_new_prose_style']['translation_style_violations']],translation_size_max_delta_pt=max(q['independent_new_prose_style']['translation_size_max_delta_pt']for q in allqa),translation_baseline_max_delta_pt=max(q['independent_new_prose_style']['translation_baseline_max_delta_pt']for q in allqa),
  image_palette_ICC_SMask_graphs_preserved=all(q['original_image_programs_retained']and all(r['full_palette_icc_mask_image_graph_preserved']for r in q['image_palette_icc_mask_and_motion_audits'])for q in allqa),combined_vs_proof_both_renderers_changed_pixels=0,no_added_edition_title_or_translator_note=True,
  original_printed_footer_total_preserved=('Original total 2 remains on all three source T pages, including page 3. No PDF erratum is added.'if year==2013 else None),figure_language_correction=({'original':'钒酸钇自倍频','ko':'바나듐산 이트륨','en':'Self-doubled yttrium vanadate','reason':'Source crop independently confirmed by parent; corrects prior OCR confusion with iridium.'}if year==2013 else None),
  source_snapshot=str(a.BASE),source_snapshot_authoring_hashes_verified=True,source_plan_snapshot=str(a.BASE/f'immutable-input-journals/{year}/native-slots.json'),source_plan_snapshot_sha256=a.core.sha(a.BASE/f'immutable-input-journals/{year}/native-slots.json'),authoring_files=authors,authoring_dependency_files=[])
 for entry in authors:
  if a.core.sha(a.BASE/entry['path'])!=entry['sha256']:raise ValueError('Authoring archive changed')
 dest=a.BASE/f'cpho_natural_{year}_inventory.json';dump(dest,inventory);print('FINAL_READY',year,str(dest),[(f['language'],f['sha256'])for f in files],flush=True)
 return inventory
