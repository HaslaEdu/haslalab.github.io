from pathlib import Path
import sys,json,hashlib,shutil,subprocess,importlib.metadata
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');E=B/'engine';PUB=Path('D:/CodexBuilds/Hasla-publish-20261031');sys.path[:0]=[str(E),str(PUB/'tools')]
from izho_natural_spacing_ready import ready
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text('utf8'))
f=B/'natural/2010/TS';extra=load(f/'final-extra-checks.json');assert extra['passed']and len(extra['pages'])==11
for n,row in enumerate(extra['pages'],1):
 proof=f/f'page{n:02}.pdf';assert row['passed']and row['font_source_style']['proof_sha256']==row['all_new_prose']['proof_sha256']==sha(proof)
 assert row['equation_numbers']['passed']and row['source_language']['passed']
 assert row['original_source_heading_alignment']['passed']and row['original_source_heading_alignment']['proof_sha256']==sha(proof)
 image=f/f'page{n:02}.native-math-images.json'
 if n==9:assert load(image)['passed']and load(image)['final_sha256']==sha(proof)
assert load(B/'2010/native-image-negative/regression.json')['independent_display_geometry_rejected']
assert load(B/'2010/heading-alignment-negative/regression.json')['independent_source_center_rejected']
m=ready(2010,'TS',serialize_page_renders=True);snapshot=Path(m['authoring_snapshot'])
def copy(src,rel):
 dst=snapshot/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst)
for p in E.glob('*.py'):copy(p,Path('tools')/p.name)
for n in range(1,12):
 for p in (B/'2010/original_style').glob(f'page{n}.json'):copy(p,Path('initial-native-baseline-authoring/plans')/p.name)
 for p in (B/'2010/native-baseline').glob(f'page{n:02}.*'):
  if p.suffix in ['.pdf','.json']:copy(p,Path('initial-native-baseline-authoring/proofs')/p.name)
 for p in f.glob(f'page{n:02}.*'):
  if p.suffix=='.json':copy(p,Path('independent-additional-audits/pages')/p.name)
 copy(f/f'page{n:02}.pdf',Path('reviewed-native-body-proofs')/f'page{n:02}.pdf')
for p in (B/'2010/inspection').glob('page??-*.json'):copy(p,Path('original-source-coordinate-inspection')/p.name)
for row in load(f/'visual-review.json')['pages']:
 p=Path(row['image']);assert row['reviewed']and sha(p)==row['image_sha256'];copy(p,Path('visual-review')/p.name)
for p in [B/'source-policy.json',f/'final-extra-checks.json',f/'visual-review.json',B/'2010/native-image-negative/regression.json',B/'2010/native-image-negative/page09-display-shift.audit.json',B/'2010/immutable-baseline-revision.json']:copy(p,Path('independent-additional-audits')/p.name)
for p in (B/'2010/native-baseline').glob('*.component-shas.json'):copy(p,Path('initial-native-baseline-authoring/immutable-baseline-components')/p.name)
copy(B/'2010/heading-alignment-negative/regression.json','independent-additional-audits/heading-alignment-regression.json')
copy(B/'2010/heading-alignment-negative/page04-heading-left8pt.audit.json','independent-additional-audits/heading-alignment-negative-audit.json')
copy(Path('D:/CodexBuilds/negative-izho2010-heading-center.py'),'scripts/negative-izho2010-heading-center.py')
copy(Path('D:/CodexBuilds/heading_source_alignment_audit.py'),'scripts/heading_source_alignment_audit.py')
for p in [Path('D:/CodexBuilds')/f'author-izho2010-complete-page{n}.py'for n in range(1,12)]+[Path('D:/CodexBuilds')/name for name in ['prepare-izho2010-complete-native-source.py','prepare-izho2010-complete-natural.py','build-izho2010-complete-baseline-page.py','build-izho2010-complete-natural-page.py','audit-izho2010-complete-final-fonts.py','negative-izho2010-ts-display-image.py','finalize-izho2010-ts-body.py']]:copy(p,Path('scripts')/p.name)
for row in m['input_archives']:copy(row['path'],Path('input-bases')/row['sha256']/Path(row['path']).name)
code="""import sys,json,importlib
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[2]]
for name in ['izho_natural_spacing_ready','izho_natural_spacing_rebuild','izho_natural_spacing_qa','modern_new_prose_collision_audit','initial_final_prose_outline_audit','final_translation_font_audit','reviewed_native_math_images','heading_source_alignment_audit']:importlib.import_module(name)
print(json.dumps({k:str(Path(v.__file__).resolve())for k,v in list(sys.modules.items())if getattr(v,'__file__',None)and str(v.__file__).lower().endswith('.py')and 'codexbuilds'in str(v.__file__).lower()}))
"""
r=subprocess.run([sys.executable,'-X','utf8','-c',code,str(E),str(PUB/'tools')],capture_output=True,text=True,encoding='utf8',check=True);imports={}
for name,source in sorted(json.loads(r.stdout).items()):
 rel=Path('actual-loaded-modules')/(name.replace('.','/')+'.py');copy(source,rel);imports[name]=dict(original_path=source,frozen_path=rel.as_posix(),sha256=sha(source))
copy_report=snapshot/'runtime-import-resolution.json';copy_report.write_text(json.dumps(imports,ensure_ascii=False,indent=2)+'\n','utf8')
(snapshot/'runtime-versions.json').write_text(json.dumps(dict(python=sys.version,packages={p:importlib.metadata.version(p)for p in ['PyMuPDF','pikepdf','fonttools','numpy','Pillow']}),indent=2)+'\n','utf8')
m.update(source_language='Russian',source_policy='Official single complete11-page Russian source. All3 problems and original rubrics/counters retained; no mixed-page composition or source-content erasure.',intermediate_body_for_reviewed_figure_language=True,all_new_hangul_source_font_role_point_baseline_and_actual_donor_outlines_verified=True,all_new_hangul_glyphs_checked=sum(r['font_source_style']['hangul_glyphs_checked']for r in extra['pages']),source_language_words_unselected=0,new_prose_dark_pixels_over_original_native_text=0,new_prose_dark_pixels_over_native_graphics=0,original_display_equation_markers_checked=sum(r['equation_numbers']['original_display_equation_markers']for r in extra['pages']),native_mathematical_images_independently_audited=True,actual_displaced_display_bitmap_negative_rejected=True)
m['authoring_files']={p.relative_to(snapshot).as_posix():sha(p)for p in sorted(snapshot.rglob('*'))if p.is_file()}
m.update(original_source_heading_centers_verified=True,actual_heading_alignment_negative_rejected=True,original_source_heading_and_caption_centers_checked=sum(r['original_source_heading_alignment']['headings_and_captions_checked']for r in extra['pages']))
Path(m['output']).with_suffix('.ready.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n','utf8');print('BODY_READY',m['output'],m['sha256'],m['bytes'],len(m['authoring_files']),flush=True)
