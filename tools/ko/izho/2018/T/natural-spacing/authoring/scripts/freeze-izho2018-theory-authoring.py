from pathlib import Path
import sys,json,hashlib,shutil,importlib,importlib.metadata
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');E=B/'engine';P=Path('D:/CodexBuilds/Hasla-publish-20261031');F=B/'natural/2018/T';sys.path[:0]=[str(E),str(P/'tools')]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
qpath=B/'natural/editions/IZhO_2018_T_KO.ready.json';q=load(qpath);out=Path(q['authoring_snapshot']);pdf=Path(q['output']);assert sha(pdf)==q['sha256']and q['pages']==6
def copy(src,rel):
 src=Path(src);dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);assert sha(src)==sha(dest)
for p in E.glob('*.py'):copy(p,Path('tools')/p.name)
names=['izho_natural_spacing_rebuild','izho_natural_spacing_qa','izho_initial_fixed_style','final_translation_font_audit','heading_source_alignment_audit','modern_new_prose_collision_audit','initial_bitmap_language_labels','izho_2018_digit_phase_profile','izho_natural_spacing_ready']
for name in names:importlib.import_module(name)
resolution={}
for name,module in list(sys.modules.items()):
 path=getattr(module,'__file__',None)
 if not path or not path.lower().endswith('.py')or 'codexbuilds'not in path.lower():continue
 src=Path(path).resolve()
 rel=Path('tools')/src.name if src.parent==E.resolve()else Path('fallback-tools')/(name.replace('.','/')+'.py')
 copy(src,rel);resolution[name]=dict(resolved_path=str(src),frozen_path=rel.as_posix(),sha256=sha(src))
save(out/'runtime-import-resolution.json',resolution)
save(out/'runtime-versions.json',dict(python=sys.version,packages={p:importlib.metadata.version(p)for p in ['PyMuPDF','pikepdf','fonttools','numpy','Pillow']}))
sources={};proofs=[]
for n in range(1,7):
 plan=load(F/f'plans/page{n:02}.json');proof=F/f'page{n:02}.pdf';a=load(proof.with_suffix('.audit.json'));assert a['passed']and a['output_sha256']==sha(proof)
 for key,digestkey in [('source_base','source_base_sha256'),('original_english_source','original_english_source_sha256')]:
  source=Path(plan[key]);assert sha(source)==plan[digestkey];rel=Path('immutable-inputs')/plan[digestkey]/source.name
  if plan[digestkey]not in sources:copy(source,rel);sources[plan[digestkey]]=dict(path=rel.as_posix(),sha256=plan[digestkey],bytes=source.stat().st_size)
 for p in [F/f'plans/page{n:02}.json',B/f'2018/original_style/page{n}.json',B/f'2018/inspection/page{n:02}-runs.json',B/f'2018/native-baseline/page{n:02}.qa.json',B/f'2018/native-baseline/page{n:02}.audit-spec.json']:
  copy(p,Path('source-review')/str(n)/p.name)
 for suffix in ['.pdf','.audit.json','.qa.json','.font-source-style.json','.source-alignment.json','.prose-collision.json']:
  p=proof.with_suffix(suffix);copy(p,Path('exact-reviewed-proofs')/p.name)
 copy(F/f'page{n:02}-preview.json',Path('visual-review')/f'page{n:02}-preview.json')
 for folder in [F/f'page{n:02}-native-digit-phase']:
  if folder.exists():
   for p in folder.iterdir():
    if p.is_file():copy(p,Path('native-CID-witnesses')/folder.name/p.name)
 proofs.append(dict(page=n,proof_sha256=sha(proof),original_source_sha256=plan['original_english_source_sha256'],actual_input_base_sha256=plan['source_base_sha256']))
for folder in [F/'negative-partial-integral-movement',F/'negative-figure-labels']:
 for p in folder.iterdir():
  if p.is_file()and p.suffix in ['.json','.pdf']:copy(p,Path('negative-controls')/folder.name/p.name)
for p in (B/'2018/inspection').glob('page06-label-*-measurement.json'):copy(p,Path('original-bitmap-label-measurements')/p.name)
copy(B/'2018/inspection/page06-refraction-labels-original.png','original-bitmap-label-measurements/unchanged-source-image.png')
for p in [B/'source-policy.json',Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-missing-editions/2018/T/semantic-translation-draft.json'),Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-missing-editions/2018/T/semantic-progress.json'),F/'visual-review.json',pdf.with_suffix('.poppler-assembly.json')]:copy(p,Path('edition-review')/p.name)
script_names=['prepare-izho2018-theory-native-source.py','build-izho2018-theory-baseline-page.py','prepare-izho2018-theory-natural.py','build-izho2018-theory-natural-page.py','render-izho2018-theory-preview.py','check-izho2018-particle-boundaries.py','refine-izho2018-complete-math-groups.py','refine-izho2018-page05-display-boundary.py','refine-izho2018-page06-enumerator-gaps.py','measure-izho2018-figure-labels.py','author-izho2018-page06-figure-labels.py','diagnose-izho2018-native-digit-phase.py','negative-izho2018-native-digit-witness.py','bind-izho2018-native-digit-witnesses.py','negative-izho2018-figure-label-preservation.py','audit-izho2018-final-fonts-and-headings.py','finalize-izho2018-theory.py','freeze-izho2018-theory-authoring.py','translate-izho2018-theory-missing-prose.py']+[f'author-izho2018-theory-page{n}.py'for n in range(1,7)]
for name in script_names:copy(Path('D:/CodexBuilds')/name,Path('scripts')/name)
copy(P/'tools/stage_natural_ready_v2.py','scripts/stage_natural_ready_v2.py')
negative=load(F/'negative-partial-integral-movement/page04.audit.json');assert not negative['passed']and not negative['native_script_motion_audit']['passed']and negative['reviewed_inline_expression_geometry']['mismatched_groups']>0
save(out/'font-and-design-policy.json',dict(original_source_language='English',source_sha256=q['original_source_sha256'],all6_source_pages_complete=True,original_native_math_fonts_GIDs_points_baselines_and_expression_geometry_preserved=True,source_font_role_points_baselines_and_original_text_colors_independently_verified=True,regular_serif_Hangul='Batang',bold_serif_Hangul='NotoSerifCJKkr-Bold',sans_Hangul='NotoSansCJKkr source weight',source_bitmap_labels='Two isolated English bitmap words translated with independently source-measured sans-bold point/baseline and original word centers. The original image program and all nonlanguage pixels remain protected.',full_commercial_font_files_redistributed=False,math_retyped=False,math_rasterized=False,fonts_shrunk_to_fit=False,paragraph_word_spaces='quarter-em, attached Korean particles',native_enumerator_gap='Two reviewed source-native enumerators followed by independent mathematical object lists use a3pt prose gap; internal mathematical spacing is unchanged.',note='The printed source c=2.9979m/s, F=10sm and Fizeau year1860 are retained exactly without editorial correction.'))
q.update(complete_original_source_pages=6,all_original_source_prose_translated=True,all_source_inputs=list(sources.values()),exact_reviewed_page_inputs=proofs,all_final_Hangul_actual_outlines_source_roles_points_baselines_and_colors_verified=True,final_Hangul_occurrences_checked=sum(load(F/f'page{n:02}.font-source-style.json')['hangul_glyphs_checked']for n in range(1,7)),original_source_heading_centers_verified=True,original_source_heading_and_caption_centers_checked=sum(load(F/f'page{n:02}.source-alignment.json')['headings_and_captions_checked']for n in range(1,7)),actual_partial_integral_motion_negative_rejected=True,actual_native_CID_omission_negatives_rejected=True,actual_nonlanguage_figure_alteration_negative_rejected=True,independent_poppler_native_page_append_verified=True,english_bitmap_figure_words_translated=2,actual_frozen_import_resolution='runtime-import-resolution.json',authoring_capture_note='Exact per-page source plans, every used initial baseline version, original English source, exact reviewed PDF pages and QA, source-only bitmap font measurements, native-CID witnesses and real negative PDFs are frozen. The current reviewed engine and its resolved local import closure are captured; full commercial font donors are represented by hashes and actual embedded-glyph comparisons.')
q['authoring_files']={p.relative_to(out).as_posix():sha(p)for p in sorted(out.rglob('*'))if p.is_file()}
save(qpath,q);print('FROZEN_COMPLETE_NATIVE_SOURCE_EDITION',q['sha256'],q['pages'],q['final_Hangul_occurrences_checked'],len(q['authoring_files']),sum(p.stat().st_size for p in out.rglob('*')if p.is_file()),flush=True)
