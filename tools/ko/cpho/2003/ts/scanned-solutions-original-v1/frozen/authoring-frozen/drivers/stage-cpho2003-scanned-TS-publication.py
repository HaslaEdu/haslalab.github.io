"""Faithful private staging; raw page receipts remain untouched and incomplete-page flags honest."""
from pathlib import Path
import sys,json,hashlib,shutil,os
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');M=B/'TS/master-v1';F=M/'authoring-frozen'
SCHEMA='cpho2003-scanned-solutions-original-v1';SOURCE='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63'
MASTER='2663cd24c0db3fd834f467cd97e6b71281c1881b3cc6a065718013a33b0b213a';READY='0183b2bf27f612a175fea6f5dd87eb7257fde0c4b8768c9a6ab365060b977017';COUNT=1431
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists(),p;p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
def stage(root):
 root=Path(root).resolve();assert not(root/'.git').exists()and root!=M.resolve()and not root.is_relative_to(M.resolve());base=root/'tools/ko/cpho/2003/ts/scanned-solutions-original-v1';assert not base.exists()
 assert sha(M/'snapshot-manifest.json')==MASTER and sha(M/'READY.json')==READY
 manifest=json.loads((M/'snapshot-manifest.json').read_text('utf8'));leaves={r['path'].replace('\\','/'):r for r in manifest['files']};assert len(leaves)==COUNT
 for rel,row in leaves.items():assert(M/rel).stat().st_size==row['bytes']and sha(M/rel)==row['sha256'],rel
 copied={}
 def ref(p):
  p=Path(p);rel=p.relative_to(M).as_posix();row=leaves[rel];assert sha(p)==row['sha256']and p.stat().st_size==row['bytes']
  if rel in copied:return copied[rel]
  out=base/'frozen'/rel;out.parent.mkdir(parents=True,exist_ok=True)
  if p.suffix.lower()in ['.pdf','.png','.jpeg','.ttf']:os.link(p,out)
  else:shutil.copy2(p,out)
  assert sha(out)==row['sha256'];copied[rel]=dict(path=out.relative_to(root).as_posix(),sha256=row['sha256'],bytes=row['bytes'],frozen_path=rel);return copied[rel]
 def extra(p,name):
  out=base/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out);return dict(path=out.relative_to(root).as_posix(),sha256=sha(out),bytes=out.stat().st_size)
 shared=dict(schema=SCHEMA,master_manifest=extra(M/'snapshot-manifest.json','snapshot-manifest.json'),native_ready=extra(M/'READY.json','native-ready.json'),source_original_pdf=ref(F/'inputs/CPhO_2003_Chinese_original.pdf'),source_slots=ref(F/'inputs/native-slots.json'),original_all10_source_slots=ref(F/'inputs/original-all10-source-slots.json'),source_classification=ref(F/'inputs/source-classification.json'),font_source_pins=ref(F/'inputs/external-font-source-pins.json'),visual_review=ref(F/'authoring/full144-visual-review-complete.json'),assembly_summary=ref(M/'verification/summary.json'),actual_build_import_closure=ref(F/'actual-build-import-closure.json'),final_auditor_import_closure=ref(F/'authoring/final-auditor-import-closure.json'),negative_manifest=ref(F/'evidence/negative-controls/negative-control-results.json'),reviewed_paper_map=ref(F/'reviewed-original-paper-map.json'),authoring_closure=[],embedded_new_font_subsets=[],source_scans=[],papers=[],negative_controls=[])
 for prefix in ['engine-base','engine-ts','engine-history','drivers','driver-bootstrap-history','authoring']:
  for p in sorted((F/prefix).rglob('*')):
   if p.is_file()and p.suffix in ['.py','.json','.txt','.tsv']:shared['authoring_closure'].append(ref(p))
 for p in sorted((F/'embedded-new-font-subsets').glob('*.ttf')):shared['embedded_new_font_subsets'].append(ref(p))
 for p in sorted((F/'source-image-reading').glob('*.jpeg')):shared['source_scans'].append(ref(p))
 for r in json.loads((F/'reviewed-original-paper-map.json').read_text('utf8')):shared['papers'].append(dict(original_source_crop_path=r['original_source_crop_path'],source_crop=ref(M/r['frozen_path'])))
 neg=json.loads((F/'evidence/negative-controls/negative-control-results.json').read_text('utf8'))
 for r in neg['cases']:
  name=r['case'];raw=name+('.raw-native-ink.json'if 'native-subscript'in name else'.raw-source-qa.json'if name in ['missing-stationary-original-equation','new-prose-over-original-math']else'.json')
  shared['negative_controls'].append(dict(case=name,fixture=ref(F/f'evidence/negative-controls/{name}.pdf'),receipt=ref(F/f'evidence/negative-controls/{name}.json'),raw=ref(F/'evidence/negative-controls'/raw)))
 ready=json.loads((M/'READY.json').read_text('utf8'));items=[];fonts=[]
 # All source/readable current originals are shared once across both editions.
 for n in range(4,11):ref(F/f'source-renders/page{n:02}.png')
 for lang in ['ko','en']:
  for n in range(4,11):ref(F/f'proofs/{lang}/page{n:02}-poppler/final.png')
 save(base/'shared.json',shared);sr=dict(path=(base/'shared.json').relative_to(root).as_posix(),sha256=sha(base/'shared.json'),bytes=(base/'shared.json').stat().st_size)
 for e in ready['editions']:
  lang=e['language'];pages=[]
  for n in range(4,11):
   stem=F/f'proofs/{lang}/page{n:02}'
   pages.append(dict(page=n-3,source_page=n,proof=ref(stem.with_suffix('.pdf')),composition=ref(stem.with_suffix('.composition.json')),source_QA=ref(stem.with_suffix('.source-qa.json')),Poppler_QA=ref(stem.with_suffix('.poppler-qa.json')),actual_style=ref(stem.with_suffix('.final-actual-donor-style.json')),source_native_ink=ref(stem.with_suffix('.final-source-native-ink.json')),visual_native_ink=ref(stem.with_suffix('.original-source-native-ink-v2.json')),layout=ref(F/f'authoring/page{n:02}-layout.json'),native_header_plan=ref(F/f'authoring/page{n:02}.json'),build_loaded_modules=ref(stem.with_suffix('.build-loaded-modules.json')),assembly=ref(M/f'verification/{lang}-page{n:02}.json'),assembly_loaded_modules=ref(M/f'verification/{lang}-page{n:02}-loaded-modules.json'),source_png=ref(F/f'source-renders/page{n:02}.png'),proof_png=ref(F/f'proofs/{lang}/page{n:02}-poppler/final.png')))
  file=f'CPhO_2003_TS_{lang.upper()}.pdf';assert leaves[file]['sha256']==e['sha256']
  q=dict(status='READY',schema=SCHEMA,competition='cpho',year=2003,kind='TS',language=lang,file=file,sha256=e['sha256'],bytes=e['bytes'],pages=7,source_original_sha256=SOURCE,source_physical_pages=list(range(4,11)),question_numbers=list(range(1,7)),original_math_retyped=False,original_math_resampled=False,original_math_y_changed=False,translated_point_sizes_fitted=False,original_figures_redrawn=False,full_installed_font_programs_exported=False,added_editorial_notes=0,original_source_folios_and_last_large_blank_retained=True,original_source_page_groups_retained=True,source_O_label_before_P_equations_retained=True,unavailable_referenced_curve_plate_not_invented=True,shared=sr,page_proofs=pages)
  out=base/lang/'publication.json';save(out,q);items.append(dict(file=file,language=lang,pages=7,bytes=e['bytes'],sha256=e['sha256'],qa=out.relative_to(root).as_posix(),generated_file=str(M/file),audit_schema=SCHEMA));fonts.append(dict(file=file,pages=7,bytes=e['bytes'],sha256=e['sha256'],missing_glyph_spans=[],original_style=True,natural_spacing=True,native_original_preserved=True))
 save(root/'registry-items.json',items);save(root/'font-validation-items.json',fonts);save(root/'staging-summary.json',dict(status='PRIVATE_STAGED_FOR_PARENT_INTEGRATION',schema=SCHEMA,master_files=COUNT,copied_frozen_leaves=len(copied),master_manifest_sha256=MASTER,source_original_sha256=SOURCE,all_private_master_leaves_reverified=True,finalized_binary_payloads_shared_by_NTFS_hardlinks=True,no_binary_mutations_authorized=True,full_installed_font_programs_exported=False,PNEW_or_registry_or_Git_or_upload_modified=False));print('CPHO2003_TS_PUBLIC_EVIDENCE_STAGED',len(copied),flush=True)
if __name__=='__main__':stage(sys.argv[1])
