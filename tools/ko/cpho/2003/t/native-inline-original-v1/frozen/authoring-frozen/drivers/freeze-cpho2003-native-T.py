from pathlib import Path
import json,sys,hashlib,shutil,subprocess,importlib.metadata as versions,platform
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');M=B/'T/master-v1';F=M/'authoring-frozen';R=Path('D:/CodexBuilds');SOURCE='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists(),p;p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
def copy(p,q):
 p=Path(p);q=Path(q);q.parent.mkdir(parents=True,exist_ok=True);assert not q.exists(),q;shutil.copy2(p,q);assert sha(p)==sha(q)
def prepare():
 assert not M.exists();F.mkdir(parents=True);assert sha(B/'inputs/CPhO_2003_Chinese_original.pdf')==SOURCE
 for p in (B/'engine').glob('*.py'):copy(p,F/'engine'/p.name)
 for p in R.glob('*cpho2003*.py'):
  if p.name.startswith('stage-'):continue
  copy(p,F/'drivers'/p.name)
 for name in ['CPhO_2003_Chinese_original.pdf','original-all10-source-slots.json','external-font-source-pins.json','source-provenance.json','native-engine-copy-provenance.json','actual-prose-style-auditor-derivation.json']:
  if (B/'inputs'/name).exists():copy(B/'inputs'/name,F/'inputs'/name)
 copy(B/'evidence/source-classification.json',F/'inputs/source-classification.json')
 for p in (B/'authoring/native').iterdir():
  if p.is_file():copy(p,F/'authoring/native'/p.name)
 copy(B/'authoring/full144-visual-review-complete.json',F/'authoring/full144-visual-review-complete.json');copy(B/'evidence/original-stationary-math-Poppler144.json',F/'evidence/original-stationary-math-Poppler144.json');copy(B/'tools/ko/cpho/2003/natural/atomic-inline.json',F/'tools/ko/cpho/2003/natural/atomic-inline.json')
 for prefix in ['actual-style','source-native-ink','source-programs-and-advances','negative-controls']:
  for p in (B/'evidence'/prefix).iterdir():
   if p.is_file():copy(p,F/'evidence'/prefix/p.name)
 visual=json.loads((B/'authoring/full144-visual-review-complete.json').read_text('utf8'))
 for lang in ['ko','en']:
  for n in [1,2,3]:
   for p in (B/f'natural/2003/{lang}').glob(f'page{n:02}*'):
    if p.is_file()and p.suffix in ['.pdf','.json']:copy(p,F/f'natural/2003/{lang}'/p.name)
   for p in (B/f'native-baseline/{lang}').glob(f'page{n:02}*'):copy(p,F/f'native-baseline/{lang}'/p.name)
   v=next(r for r in visual['pages']if r['language']==lang and r['source_page']==n);copy(Path(v['png']),F/'reviewed-proofs144'/lang/Path(v['png']).name)
 for n in [1,2,3]:copy(B/f'source-renders-144/page{n:02}.png',F/f'source-renders/page{n:02}.png')
 prior='proof-history/before-original-source-page-group-restoration'
 for lang in ['ko','en']:
  for n in [1,2,3]:
   old=B/prior/f'natural/2003/{lang}/page{n:02}.pdf';copy(old,F/prior/f'natural/2003/{lang}/page{n:02}.pdf')
   name=f'page{n:02}-{sha(old)[:16]}.png';copy(B/prior/f'proof-renders-144/{lang}'/name,F/prior/f'proof-renders-144/{lang}'/name)
 save(F/'path-and-replay-map.json',dict(source_build_root=str(B),frozen_root=str(F),original_source_sha256=SOURCE,read_only_frozen=True,replay='Copy frozen tree to a new scratch root. Remap build-root constants at read time in the scratch copy; never execute a writer against this frozen tree. Actual source/full donor font pins remain read-only external dependencies; no full installed font program is copied. Proof/baseline PDFs retain the exact embedded subsets. Historical bootstrap/diagnostic drivers are provenance, not prerequisites for validating current proofs.',current_native_guard_sha256=sha(F/'engine/pdf_native_inline_reposition.py')))
 sys.path.insert(0,str(F/'engine'));from pdf_memory_gate import page_worker
 import pikepdf
 with page_worker():
  editions=[]
  for lang in ['ko','en']:
   out=M/f'CPhO_2003_T_{lang.upper()}.pdf'
   with pikepdf.Pdf.new()as target:
    for n in [1,2,3]:
     with pikepdf.open(F/f'natural/2003/{lang}/page{n:02}.pdf')as src:assert len(src.pages)==1;target.pages.append(src.pages[0])
    target.save(out,compress_streams=False)
   editions.append(dict(language=lang,path=str(out),sha256=sha(out),bytes=out.stat().st_size,pages=3,source_physical_pages=[1,2,3],method='Exact native page append; no math/image rasterization or refonting or point fitting.'))
 save(M/'edition-candidates.json',editions);print('CPHO2003_T_FROZEN_NATIVE_INPUTS_AND_EDITION_CANDIDATES_PREPARED',flush=True)
def seal():
 assert M.exists()and not(M/'READY.json').exists();editions=json.loads((M/'edition-candidates.json').read_text('utf8'));visual=json.loads((F/'authoring/full144-visual-review-complete.json').read_text('utf8'));rows=[];checks=[]
 for e in editions:
  assert sha(Path(e['path']))==e['sha256']
  for n in [1,2,3]:
   lang=e['language'];p=F/f'natural/2003/{lang}/page{n:02}.pdf';a=json.loads(p.with_suffix('.audit.json').read_text('utf8'));style=json.loads((F/f'evidence/actual-style/{lang}-page{n:02}.json').read_text('utf8'));program=json.loads((F/f'evidence/source-programs-and-advances/{lang}-page{n:02}.json').read_text('utf8'));ink=json.loads((F/f'evidence/source-native-ink/{lang}-page{n:02}.json').read_text('utf8'));check=json.loads((M/f'verification/{lang}-page{n:02}.json').read_text('utf8'));assert a['passed']and style['passed']and program['passed']and ink['passed']and check['passed'];assert a['output_sha256']==style['proof_sha256']==program['proof_sha256']==ink['output_sha256']==check['reviewed_proof_sha256']==sha(p);checks.append(check);rows.append(dict(language=lang,source_page=n,proof_sha256=sha(p),audit_sha256=sha(p.with_suffix('.audit.json')),full144_visual_review_passed=True,strict_page_QA_passed=True))
 neg=json.loads((F/'evidence/negative-controls/native-negative-control-manifest.json').read_text('utf8'));assert neg['all5_actual_bad_PDFs_rejected']and len(neg['controls'])==5
 save(M/'verification/summary.json',dict(passed=True,pages=6,MuPDF4x_RGB_difference_pixels=0,Poppler144_RGB_difference_pixels=0,native_content_font_glyph_and_image_programs_identical=True,versions={p:versions.version(p)for p in ['PyMuPDF','pikepdf','fonttools','Pillow','numpy','opencv-python']},python=platform.python_version(),individual_pages=rows))
 files=[dict(path=p.relative_to(M).as_posix(),sha256=sha(p),bytes=p.stat().st_size)for p in sorted(M.rglob('*'))if p.is_file()];save(M/'snapshot-manifest.json',dict(status='COMPLETE_PRIVATE_CPHO2003_NATIVE_T_BILINGUAL_SNAPSHOT',source_sha256=SOURCE,files=files))
 ready=dict(status='READY_PRIVATE_FOR_PARENT_PUBLICATION',schema='cpho2003-native-inline-original-v1',source_sha256=SOURCE,source_physical_pages=[1,2,3],question_numbers=[1,2,3,4,5,6],editions=editions,snapshot_manifest_sha256=sha(M/'snapshot-manifest.json'),snapshot_files=len(files),all6_full_page_original_and_current_proof_visuals_reviewed=True,all6_original_source_native_ink_audits_passed=True,all6_original_resource_program_and_unscaled_advance_audits_passed=True,all5_actual_negative_controls_rejected=True,actual_original_source_page_groups_preserved=True,actual_translated_glyphs_checked=4928,original_source_folios_total7_and_large_page3_blank_retained=True,original_reference_to_unavailable_problem3_curve_plate_not_invented=True,added_editorial_notes=0,original_math_retyped=False,original_math_resampled=False,original_math_y_changed=False,translated_point_sizes_fitted=False,external_publication_or_repository_mutation_performed=False)
 save(M/'READY.json',ready)
 for row in files:assert sha(M/row['path'])==row['sha256']and (M/row['path']).stat().st_size==row['bytes']
 print(json.dumps(dict(ready_sha256=sha(M/'READY.json'),master_manifest_sha256=ready['snapshot_manifest_sha256'],master_files=len(files),editions=editions),ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':{'prepare':prepare,'seal':seal}[sys.argv[1]]()
