from pathlib import Path
import sys,json,hashlib,shutil,subprocess,importlib.metadata
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');E=B/'engine';PUB=Path('D:/CodexBuilds/Hasla-publish-20261031');sys.path[:0]=[str(E),str(PUB/'tools')]
from izho_natural_spacing_ready import ready
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'));f=B/'natural/2020/TS';extra=load(f/'final-extra-checks.json');assert extra['passed']and len(extra['pages'])==13
centers=headings=glyphs=0
for n,row in enumerate(extra['pages'],1):
 proof=f/f'page{n:02}.pdf';assert row['passed']and row['font_source_style']['proof_sha256']==row['all_new_prose']['proof_sha256']==sha(proof)
 assert row['equation_numbers']['passed']and row['source_language']['passed'];h=row['original_source_heading_alignment'];assert h['passed']and h['proof_sha256']==sha(proof)and h['original_bold_prose_heading_coverage']['passed']
 assert load(proof.with_suffix('.audit.json'))['passed']and load(proof.with_suffix('.prose-collision.json'))['passed'];centers+=h['headings_and_captions_checked'];headings+=h['original_bold_prose_heading_coverage']['headings_checked'];glyphs+=row['font_source_style']['hangul_glyphs_checked']
print('INDEPENDENT_TOTALS',centers,headings,glyphs,flush=True)
assert headings==15 and glyphs>4000 and centers>=15
assert load(B/'2020/heading-alignment-negative/regression.json')['independent_source_center_rejected']and load(B/'2020/heading-alignment-negative/coverage-regression.json')['original_source_heading_inventory_rejected_missing_intent']
negative=load(B/'2020/expression-negative/regression.json');assert negative['passed']and len(negative['rows'])==2 and negative['rows'][0]['independent_complete_expression_geometry_rejected']and negative['rows'][1]['native_encoder_rejected_partial_clip_motion']
m=ready(2020,'TS',serialize_page_renders=True);snapshot=Path(m['authoring_snapshot'])
def copy(src,rel):
 src=Path(src);dst=snapshot/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst)
for p in E.glob('*.py'):copy(p,Path('tools')/p.name)
for n in range(1,14):
 copy(B/f'2020/original_style/page{n}.json',Path('initial-native-baseline-authoring/plans')/f'page{n}.json')
 for p in (B/'2020/native-baseline').glob(f'page{n:02}.*'):
  if p.suffix in ['.pdf','.json']:copy(p,Path('initial-native-baseline-authoring/proofs')/p.name)
 for p in f.glob(f'page{n:02}.*'):
  if p.suffix=='.json':copy(p,Path('independent-additional-audits/pages')/p.name)
 copy(f/f'page{n:02}.pdf',Path('reviewed-native-body-proofs')/f'page{n:02}.pdf')
for row in load(f/'visual-review.json')['pages']:
 p=Path(row['image']);assert row['reviewed']and sha(p)==row['image_sha256'];copy(p,Path('visual-review')/p.name)
for p in (B/'2020/inspection').glob('page??-*.json'):copy(p,Path('original-source-coordinate-inspection')/p.name)
for p in [f/'final-extra-checks.json',f/'visual-review.json',B/'2020/source-language-coverage.json',B/'2020/natural_spacing-overrides.json']:copy(p,Path('independent-additional-audits')/p.name)
for name,folder in [('heading',B/'2020/heading-alignment-negative'),('expression',B/'2020/expression-negative')]:
 for p in folder.glob('*.json'):
  if p.name.endswith('.audit.json')or p.name in ['regression.json','coverage-regression.json']:copy(p,Path('independent-additional-audits/negative-controls')/name/p.name)
for n,folder in [(2,f/'parenthesis-native-reference'),(3,f/'page03-parentheses-native-reference')]:
 copy(f/f'page{n:02}.old-source.pdf',Path('native-CID-reference-witnesses')/f'page{n:02}'/'original-input-page.pdf')
 for p in folder.iterdir():
  if p.suffix in ['.json','.pdf']:copy(p,Path('native-CID-reference-witnesses')/f'page{n:02}'/p.name)
names=[f'author-izho2020-complete-page{n}.py'for n in range(1,14)]+['prepare-izho2020-complete-native-source.py','prepare-izho2020-complete-natural.py','build-izho2020-complete-baseline-page.py','build-izho2020-complete-natural-page.py','audit-izho2020-complete-final-fonts.py','izho2020-p2-native-parenthesis-witness.py','izho2020-p3-native-parentheses-witness.py','negative-izho2020-native-expression-groups.py','negative-izho2020-heading-centers.py','review-izho2020-complete-visuals.py','finalize-izho2020-ts-body.py']
for name in names:copy(Path('D:/CodexBuilds')/name,Path('scripts')/name)
for row in m['input_archives']:copy(row['path'],Path('input-bases')/row['sha256']/Path(row['path']).name)
code="""import sys,json,importlib
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[2]]
for name in ['izho_natural_spacing_ready','izho_natural_spacing_rebuild','izho_natural_spacing_qa','modern_new_prose_collision_audit','initial_final_prose_outline_audit','final_translation_font_audit','initial_source_language_coverage','heading_source_alignment_audit','pdf_native_script_motion_audit','pdf_native_glyph_raster_witness']:importlib.import_module(name)
print(json.dumps({k:str(Path(v.__file__).resolve())for k,v in list(sys.modules.items())if getattr(v,'__file__',None)and str(v.__file__).lower().endswith('.py')and 'codexbuilds'in str(v.__file__).lower()}))
"""
r=subprocess.run([sys.executable,'-X','utf8','-c',code,str(E),str(PUB/'tools')],capture_output=True,text=True,encoding='utf8',check=True);imports={}
for name,source in sorted(json.loads(r.stdout).items()):
 rel=Path('actual-loaded-modules')/(name.replace('.','/')+'.py');copy(source,rel);imports[name]=dict(original_path=source,frozen_path=rel.as_posix(),sha256=sha(source))
(snapshot/'runtime-import-resolution.json').write_text(json.dumps(imports,ensure_ascii=False,indent=2)+'\n','utf8');(snapshot/'runtime-versions.json').write_text(json.dumps(dict(python=sys.version,packages={p:importlib.metadata.version(p)for p in ['PyMuPDF','pikepdf','fonttools','numpy','Pillow']}),indent=2)+'\n','utf8')
m.update(source_language='English',source_policy='Official single complete13-page2020 English solutions. All3 problems, original rubrics, grade values and mixed-font page counters retained.',intermediate_body_for_reviewed_figure_language=True,all_new_hangul_source_font_role_point_baseline_and_actual_donor_outlines_verified=True,all_new_hangul_glyphs_checked=glyphs,source_language_words_unselected=0,new_prose_dark_pixels_over_original_native_text=0,new_prose_dark_pixels_over_native_graphics=0,original_display_equation_markers_checked=sum(r['equation_numbers']['original_display_equation_markers']for r in extra['pages']),original_source_heading_centers_verified=True,original_source_heading_and_caption_centers_checked=centers,all_original_bold_prose_headings_inventoried_and_centered=True,original_bold_prose_headings_checked=headings,actual_heading_alignment_negative_rejected=True,missing_subtitle_intent_negative_rejected=True,actual_fraction_piece_motion_negative_rejected=True,partial_native_math_clip_motion_rejected=True)
m['authoring_files']={p.relative_to(snapshot).as_posix():sha(p)for p in sorted(snapshot.rglob('*'))if p.is_file()};Path(m['output']).with_suffix('.ready.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n','utf8');print('BODY_READY',m['output'],m['sha256'],m['bytes'],len(m['authoring_files']),flush=True)
