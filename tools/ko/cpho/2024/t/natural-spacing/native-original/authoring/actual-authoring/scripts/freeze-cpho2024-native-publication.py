"""Freeze the actual authoring inputs, private engines, and current raw QA."""
from pathlib import Path
import json,hashlib,shutil,sys,subprocess,platform,importlib.metadata
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2024-original-natural')
E=B/'engine';P=Path('D:/CodexBuilds/Hasla-publish-20261031')
out=B/'master-v1/authoring-frozen'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
def copy(src,rel):
 dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(dst)==sha(src)
def reference(p):return dict(path=str(p),sha256=sha(p))
for f in sorted(E.glob('*.py')):copy(f,Path('engine')/f.name)
for folder in ['source','authoring/T']:
 for f in sorted((B/folder).rglob('*')):
  if f.is_file()and f.suffix.lower()in['.pdf','.json','.tsv','.txt']:copy(f,f.relative_to(B))
for f in sorted((B/'inspection').glob('*.json')):copy(f,f.relative_to(B))
for folder in ['figure-language-roi-review']:
 for f in sorted((B/'inspection'/folder).glob('*')):
  if f.is_file()and f.suffix.lower()in['.json','.png']:copy(f,f.relative_to(B))
for f in sorted((B/'inspection/final-page-review').glob('*')):
 if f.suffix=='.json'or f.name.endswith('-review.png'):copy(f,f.relative_to(B))
for f in sorted((B/'fonts').glob('*.json')):copy(f,f.relative_to(B))
scripts=['prepare-cpho2024-final-assembly.py','freeze-cpho2024-native-publication.py','assemble-scanned-proof-edition.py','revise-cpho2024-average-brackets.py','shorten-cpho2024-mean-energy-clause.py','revise-cpho2024-page3-caption-wrap.py','review-cpho2024-label-rois.py','review-cpho2024-label-native-components.py','inspect-cpho2024-shared-label-components.py','check-cpho2024-label-components.py','render-cpho2024-final-pages.py']
for name in scripts:
 p=Path('D:/CodexBuilds')/name
 if p.is_file():copy(p,Path('scripts')/name)
contexts={}
for stage in ['cpho2024_natural','cpho2024_events','cpho2024_body_qa','cpho2024_font_style_qa','cpho2024_bitmap_fonts','cpho2024_figure_labels','cpho2024_figure_label_qa','assembly']:
 # Fresh processes capture each entry point's real import resolution, including
 # helpers which adjust sys.path. Do not guess that the top-level helper won.
 code="""import sys,json,importlib,importlib.util
from pathlib import Path
sys.path.insert(0,sys.argv[1])
if sys.argv[2]=='assembly':
 spec=importlib.util.spec_from_file_location('actual_assembler',sys.argv[3]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
else:importlib.import_module(sys.argv[2])
rows={}
for k,v in list(sys.modules.items()):
 p=getattr(v,'__file__',None)
 if p and str(p).lower().endswith('.py') and ('codexbuilds' in str(p).lower()or 'hasla ' in str(p).lower()):rows[k]=str(Path(p).resolve())
print(json.dumps(rows))
"""
 result=subprocess.run([sys.executable,'-X','utf8','-c',code,str(E),stage,'D:/CodexBuilds/assemble-scanned-proof-edition.py'],capture_output=True,text=True,encoding='utf8',check=True)
 paths=json.loads(result.stdout);mapping={}
 assert stage=='assembly'or paths.get(stage)==str((E/(stage+'.py')).resolve())
 for name,source in sorted(paths.items()):
  rel=Path('loaded-modules')/stage/(name.replace('.','/')+'.py');copy(source,rel)
  mapping[name]=dict(actual_original_path=source,frozen_path=rel.as_posix(),sha256=sha(source))
 contexts[stage]=mapping
save(out/'runtime-import-resolution.json',contexts)
save(out/'runtime-versions.json',dict(python=sys.version,platform=platform.platform(),packages={p:importlib.metadata.version(p)for p in['PyMuPDF','pikepdf','fonttools','numpy','Pillow']}))
copy(B/'T/source-caption-background-regression/regression.json','regression/caption-background.json')
copy(B/'T/source-caption-background-regression/negative.audit.json','regression/negative-audit.json')
copy(B/'T/final-label-mask-regression/regression.json','regression/final-label-mask.json')
copy(B/'T/final-label-mask-regression/negative.audit.json','regression/final-label-mask-negative-audit.json')
save(out/'font-and-design-policy.json',dict(source_sha256=sha(B/'source/CPhO_2024_Chinese_original.pdf'),body_original_font_size_paint_and_baseline_from_embedded_metadata=True,english_original_body_families=['SimSun','SimHei','DengXian','DengXian-Bold'],korean_original_serif_role='Batang',korean_original_sans_roles='NotoSansCJKkr regular/bold with original paint/stroke',original_math_and_math_descriptive_subscripts_retained_as_native=True,bitmap_figure_label_font_and_point_sizes_are_source_only_estimates=True,target_text_not_used_for_font_fitting=True,source_shared_bitmap_components_partitioned_only_in_four_explicit_reviewed_word_regions=True,commercial_full_font_files_not_redistributed=True,new_drawn_diagram_geometry=False))
save(out/'provenance-notes.json',dict(purpose='Exact producing code, source, translations, source-only label measurements, reviewed source-word partitions and actual import resolution. Full private helpers are retained; no shared engine was overwritten.',reproduction='Use frozen engine with this original source/authoring/inspection tree. Consult runtime-import-resolution.json to resolve external helper contexts exactly, and original font SHA/face metadata in raw QA. Full font donors require independently available licensed fonts. Original runtime paths remain in raw historical records.',visual_review='All ten full final Poppler pages and both contact sheets were actually inspected. Body source metadata and final actual font/GID outlines are independently audited. Bitmap font estimates are not claimed as exact original metadata.',native_math='Original mathematical descriptors such as interference and left/right subscripts remain unchanged source glyphs, with meanings translated in surrounding prose.'))
files={f.relative_to(out).as_posix():sha(f)for f in sorted(out.rglob('*'))if f.is_file()}
editions=[]
for lang in ['KO','EN']:
 pdf=B/f'master-v1/CPhO_2024_T_{lang}.pdf';a=json.loads(pdf.with_suffix('.assembly-qa.json').read_text('utf8'))
 assert a['passed']and a['sha256']==sha(pdf)and len(a['pages'])==5
 proofs=[]
 for n in range(1,6):
  final=B/f'T/figure-language/page{n:02}-{lang}.pdf';body=B/f'T/pages/page{n:02}-{lang}.pdf'
  bodyqa=B/f'T/body-qa/page{n:02}-{lang}.audit.json';style=B/f'T/body-qa/page{n:02}-{lang}.font-style.json';label=B/f'T/figure-language/qa/page{n:02}-{lang}.audit.json'
  qa=json.loads(bodyqa.read_text('utf8'));st=json.loads(style.read_text('utf8'));la=json.loads(label.read_text('utf8'))
  assert qa['passed']and st['passed']and la['passed']
  assert qa['proof_sha256']==st['proof_sha256']==la['body_sha256']==sha(body)
  assert la['proof_sha256']==sha(final)==a['pages'][n-1]['proof_sha256']
  for k in ['mupdf_4x_changed_pixels','poppler_144dpi_changed_pixels']:assert a['pages'][n-1][k]==0
  row=dict(page=n,source_page=n,pdf=str(final),sha256=sha(final),body_sha256=sha(body),body_qa=reference(bodyqa),actual_style_qa=reference(style),figure_language_qa=reference(label),body_composition=reference(body.with_suffix('.json')),figure_composition=reference(final.with_suffix('.labels.json')))
  if la['labels']:
   reference_pdf=B/f'T/figure-language/page{n:02}-{lang}.text-overlay.pdf'
   assert sha(reference_pdf)==la['pixel_audit']['reference_sha256']
   row['label_reference_pdf']=reference(reference_pdf)
  proofs.append(row)
 editions.append(dict(output=str(pdf),sha256=sha(pdf),bytes=pdf.stat().st_size,pages=5,language=lang.lower(),proofs=proofs,visual_review=reference(B/f'master-v1/{lang}-visual-review.json'),assembly_qa=reference(pdf.with_suffix('.assembly-qa.json'))))
ready=dict(status='READY',schema='native-original-preserved-v1',year=2024,kind='T',competition='cpho',source_original_sha256=sha(B/'source/CPhO_2024_Chinese_original.pdf'),original_math_retyped=False,original_math_resampled=False,original_math_y_changed=False,translated_point_sizes_fitted=False,added_editorial_notes=0,authoring_snapshots=[dict(name='actual-authoring',root=str(out),files=files)],source_word_component_review=reference(B/'inspection/figure-language-roi-review/source-component-review.json'),caption_background_negative_control=reference(B/'T/source-caption-background-regression/regression.json'),label_mask_negative_control=reference(B/'T/final-label-mask-regression/regression.json'),editions=editions)
save(B/'master-v1/CPhO_2024_T_READY.json',ready)
print(json.dumps(dict(status='READY',frozen_files=len(files),frozen_bytes=sum((out/r).stat().st_size for r in files),editions=[dict(file=Path(e['output']).name,bytes=e['bytes'],sha256=e['sha256'])for e in editions])))
