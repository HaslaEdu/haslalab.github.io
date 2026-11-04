"""Freeze only reviewed current C03TS inputs, then native append and seal after QA."""
from pathlib import Path
import sys,json,hashlib,shutil,platform,os,importlib.metadata as versions
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS';M=T/'master-v1';F=M/'authoring-frozen'
sys.path[:0]=[str(T/'engine'),str(B/'engine'),'D:/CodexBuilds']
from pdf_memory_gate import page_worker
SOURCE='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63';GUARD='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,q):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert json.loads(p.read_text('utf8'))==q,p;return
 p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
def copy(a,b):
 a=Path(a);b=Path(b);b.parent.mkdir(parents=True,exist_ok=True)
 assert b.resolve().is_relative_to(M.resolve())and a.resolve().is_relative_to(B.resolve())or str(a).startswith('D:')
 binary=a.suffix.lower()in ['.pdf','.png','.jpeg','.ttf']and a.resolve().is_relative_to(B.resolve())
 if b.exists():
  if sha(a)==sha(b):
   if binary and not os.path.samefile(a,b):
    assert not(M/'READY.json').exists()and b.resolve().is_relative_to(M.resolve());b.unlink();os.link(a,b)
   return
  assert not(M/'READY.json').exists()and b.resolve().is_relative_to(M.resolve())
  if a.suffix=='.py':
   history=F/'driver-bootstrap-history'/f'{b.stem}-{sha(b)}{b.suffix}';history.parent.mkdir(parents=True,exist_ok=True);assert not history.exists();b.replace(history)
  else:
   assert b.stat().st_size<a.stat().st_size,('Unexpected differing completed snapshot copy',a,b);b.unlink()
 if binary:os.link(a,b)
 else:shutil.copy2(a,b)
 assert sha(a)==sha(b)
def check_current():
 v=json.loads((T/'authoring/full144-visual-review-complete.json').read_text('utf8'));assert v['status']=='ALL14_CURRENT_FULL_PAGE_VISUALS_REVIEWED'and len(v['pages'])==14
 assert sha(B/'inputs/CPhO_2003_Chinese_original.pdf')==SOURCE
 for r in v['pages']:
  n=r['source_page'];lang=r['language'];p=T/f'proofs/{lang}/page{n:02}.pdf';assert sha(p)==r['proof_sha256']and sha(Path(r['png']))==r['png_sha256']
  for suffix,key in [('.source-qa.json','final_sha256'),('.poppler-qa.json','proof_sha256'),('.final-actual-donor-style.json','proof_sha256'),('.final-source-native-ink.json','output_sha256')]:
   q=json.loads(p.with_suffix(suffix).read_text('utf8'));assert q['passed']and q[key]==sha(p)
 neg=json.loads((T/'negative-controls-v1/negative-control-results.json').read_text('utf8'));assert neg['all_five_actual_bad_pdfs_rejected']and len(neg['cases'])==5
 assert json.loads((T/'authoring/final-auditor-import-closure.json').read_text('utf8'))['all14_current_positive_style_and_native_reports_verified']
 return v
def prepare():
 v=check_current();assert not(M/'READY.json').exists();F.mkdir(parents=True,exist_ok=True)
 for p in (B/'engine').glob('*.py'):copy(p,F/'engine-base'/p.name)
 for p in (T/'engine').glob('*.py'):copy(p,F/'engine-ts'/p.name)
 for p in (T/'engine-history').glob('*.py'):copy(p,F/'engine-history'/p.name)
 assert sha(F/'engine-base/pdf_native_inline_reposition.py')==GUARD
 for p in (B/'drivers').glob('*cpho2003*.py'):copy(p,F/'drivers'/p.name)
 for name in ['build-cpho2003-scanned-TS-page.py','verify-cpho2003-scanned-TS-page.py','author-cpho2003-TS-page04.py','author-cpho2003-TS-page05.py','author-cpho2003-TS-page06.py','author-cpho2003-TS-page10.py','inspect-cpho2003-scanned-TS-math-atlas.py','prepare-cpho2003-scanned-TS-engine.py']:
  copy(Path('D:/CodexBuilds')/name,F/'drivers'/name)
 for name in ['CPhO_2003_Chinese_original.pdf','original-all10-source-slots.json','external-font-source-pins.json','source-provenance.json']:
  if (B/'inputs'/name).exists():copy(B/'inputs'/name,F/'inputs'/name)
 copy(B/'evidence/source-classification.json',F/'inputs/source-classification.json');copy(T/'inputs/native-slots.json',F/'inputs/native-slots.json')
 for n in range(4,11):
  for suffix in ['.json','-layout.json','-source-semantics.json']:
   p=T/f'authoring/page{n:02}{suffix}'
   if p.exists():copy(p,F/'authoring'/p.name)
  copy(B/f'source-renders-144/page{n:02}.png',F/f'source-renders/page{n:02}.png')
 for name in ['full144-visual-review-complete.json','final-auditor-import-closure.json']:copy(T/'authoring'/name,F/'authoring'/name)
 for p in (T/'authoring/source-prose-outer-ink-inspection').iterdir():
  if p.is_file():copy(p,F/'evidence/source-prose-outer-ink-inspection'/p.name)
 for p in (T/'source-image-reading').iterdir():
  if p.is_file()and(p.suffix=='.jpeg'or any(s in p.name for s in ['manual-math-atlas','coordinate-reading','atom-boundaries','complete-delay','image-reading-index'])):copy(p,F/'source-image-reading'/p.name)
 paper=[]
 for n in range(4,11):
  layout=json.loads((T/f'authoring/page{n:02}-layout.json').read_text('utf8'))
  for r in layout.get('reviewed_blank_background_rects',[]):
   if r.get('source_crop'):
    p=Path(r['source_crop']);assert sha(p)==r['source_crop_sha256'];target=F/'evidence/reviewed-original-paper'/p.name
    if not target.exists():copy(p,target)
    paper.append(dict(source_page=n,original_source_crop_path=str(p),frozen_path=target.relative_to(M).as_posix(),sha256=sha(p),bytes=p.stat().st_size,source_sha256=SOURCE))
 save(F/'reviewed-original-paper-map.json',paper)
 font_files={};build_closure=[]
 for lang in ['ko','en']:
  for n in range(4,11):
   prefix=f'page{n:02}'
   for p in (T/f'proofs/{lang}').glob(prefix+'*'):
    if p.is_file()and p.suffix in ['.pdf','.json']:copy(p,F/f'proofs/{lang}'/p.name)
   for p in (T/f'proofs/{lang}/{prefix}-poppler').iterdir():
    if p.is_file():copy(p,F/f'proofs/{lang}/{prefix}-poppler'/p.name)
   comp=json.loads((T/f'proofs/{lang}/{prefix}.composition.json').read_text('utf8'))
   def fonts(x):
    if isinstance(x,dict):
     if 'subset'in x:
      p=Path(x['subset']);assert sha(p)==x['subset_sha256'];font_files[str(p.resolve())]=p
     for value in x.values():fonts(value)
    elif isinstance(x,list):
     for value in x:fonts(value)
   fonts(comp)
   mods=json.loads((T/f'proofs/{lang}/{prefix}.build-loaded-modules.json').read_text('utf8'))
   for mod in mods:
    original=Path(mod['path']);target=(F/'engine-ts'/original.name)if original.parent.resolve()==(T/'engine').resolve()else F/'engine-base'/original.name
    if sha(target)!=mod['sha256']:
     matches=[p for p in (F/'engine-history').glob('*.py')if sha(p)==mod['sha256']];assert len(matches)==1,mod;target=matches[0]
    build_closure.append(dict(language=lang,source_page=n,module=mod['module'],original_loaded_path=mod['path'],sha256=mod['sha256'],frozen_path=target.relative_to(M).as_posix()))
 for p in font_files.values():copy(p,F/'embedded-new-font-subsets'/p.name)
 for p in (T/'negative-controls-v1').iterdir():
  if p.is_file():copy(p,F/'evidence/negative-controls'/p.name)
 save(F/'actual-build-import-closure.json',dict(source_sha256=SOURCE,all_actual_build_loaded_module_hashes_resolved=True,modules=build_closure))
 save(F/'path-and-replay-map.json',dict(source_build_root=str(B),source_solutions_root=str(T),frozen_root=str(F),read_only_frozen=True,source_original_sha256=SOURCE,current_native_guard_sha256=GUARD,full_installed_font_programs_copied=False,replay='Copy frozen files to a new scratch root and remap source build constants at read time only. Never execute a writer against this immutable snapshot. Current authored JSON plans are authoritative reviewed inputs; bootstrap drivers and old exact engine variants are provenance. Full donor font programs remain hash-pinned read-only external dependencies; final PDFs and frozen cache retain only their exact embedded subsets.'))
 links=[]
 for p in F.rglob('*'):
  if p.is_file()and p.suffix.lower()in ['.pdf','.png','.jpeg','.ttf']:
   st=p.stat();links.append(dict(frozen_path=p.relative_to(M).as_posix(),sha256=sha(p),bytes=st.st_size,ntfs_link_count=st.st_nlink))
 save(F/'storage-provenance.json',dict(byte_identical_finalized_binary_payloads_shared_by_NTFS_hardlinks=True,no_source_or_history_removed=True,no_binary_payload_writers_authorized_after_freeze=True,frozen_manifest_and_all_leaf_bytes_independently_hashed=True,reversible_without_changing_file_content=True,files=links))
 import pikepdf
 with page_worker():
  editions=[]
  for lang in ['ko','en']:
   out=M/f'CPhO_2003_TS_{lang.upper()}.pdf'
   with pikepdf.Pdf.new()as d:
    for n in range(4,11):
     with pikepdf.open(F/f'proofs/{lang}/page{n:02}.pdf')as p:assert len(p.pages)==1;d.pages.append(p.pages[0])
    d.save(out,compress_streams=False)
   editions.append(dict(language=lang,path=str(out),sha256=sha(out),bytes=out.stat().st_size,pages=7,source_physical_pages=list(range(4,11)),method='Exact native page append, retaining complete original image/font/form/clip/Group programs and blank regions.'))
 save(M/'edition-candidates.json',editions);print('CPHO2003_TS_REVIEWED_FROZEN_INPUTS_AND_NATIVE_EDITIONS_PREPARED',flush=True)
def seal():
 assert M.exists()and not(M/'READY.json').exists();v=json.loads((F/'authoring/full144-visual-review-complete.json').read_text('utf8'));editions=json.loads((M/'edition-candidates.json').read_text('utf8'));checks=[]
 for e in editions:
  assert sha(Path(e['path']))==e['sha256']
  for n in range(4,11):
   p=M/f'verification/{e["language"]}-page{n:02}.json';q=json.loads(p.read_text('utf8'));assert q['passed']and q['edition_sha256']==e['sha256']and q['reviewed_proof_sha256']==sha(F/f'proofs/{e["language"]}/page{n:02}.pdf');checks.append(q)
 save(M/'verification/summary.json',dict(passed=True,pages=14,native_content_font_glyph_image_and_page_group_programs_identical=True,MuPDF4x_RGB_difference_pixels=0,Poppler144_RGB_difference_pixels=0,versions={p:versions.version(p)for p in ['PyMuPDF','pikepdf','fonttools','Pillow','numpy']},python=platform.python_version(),individual_pages=checks))
 files=[dict(path=p.relative_to(M).as_posix(),sha256=sha(p),bytes=p.stat().st_size)for p in sorted(M.rglob('*'))if p.is_file()]
 save(M/'snapshot-manifest.json',dict(status='COMPLETE_PRIVATE_CPHO2003_SCANNED_TS_BILINGUAL_SNAPSHOT',source_sha256=SOURCE,files=files))
 ready=dict(status='READY_PRIVATE_FOR_PARENT_PUBLICATION',schema='cpho2003-scanned-solutions-original-v1',source_sha256=SOURCE,source_physical_pages=list(range(4,11)),question_numbers=list(range(1,7)),editions=editions,snapshot_manifest_sha256=sha(M/'snapshot-manifest.json'),snapshot_files=len(files),all14_full_original_and_current_proof_144dpi_visuals_reviewed=True,all14_strict_source_and_Poppler_QA_passed=True,all14_actual_full_donor_outline_point_baseline_and_unscaled_advance_audits_passed=True,all14_direct_original_native_ink_audits_passed=True,all14_final_native_append_both_renderers_zero_difference=True,all5_actual_bad_PDF_controls_rejected=True,actual_new_translated_nonspace_glyphs_checked=v['actual_new_nonspace_glyphs_checked'],actual_original_native_glyphs_checked=v['actual_source_native_glyphs_checked'],actual_single_original_image_expression_controls=v['actual_single_original_image_expression_controls'],all_original_encoded_image_palette_mask_icc_and_form_programs_preserved=True,all_original_native_font_names_ToUnicode_and_programs_preserved=True,actual_original_source_page_groups_retained=True,original_folios_and_final_large_blank_retained=True,original_source_O_label_before_P_equations_retained=True,unavailable_referenced_problem3_curve_plate_not_invented=True,full_installed_font_programs_exported=False,added_editorial_notes=0,original_math_retyped=False,original_math_resampled=False,original_math_y_changed=False,translated_point_sizes_fitted=False,repository_or_external_publication_mutation_performed=False)
 save(M/'READY.json',ready)
 for r in files:assert sha(M/r['path'])==r['sha256']and(M/r['path']).stat().st_size==r['bytes']
 print(json.dumps(dict(ready_sha256=sha(M/'READY.json'),master_manifest_sha256=ready['snapshot_manifest_sha256'],master_files=len(files),editions=editions),ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':{'prepare':prepare,'seal':seal}[sys.argv[1]]()
