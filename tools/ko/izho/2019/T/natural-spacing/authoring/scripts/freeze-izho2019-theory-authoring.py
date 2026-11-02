from pathlib import Path
import sys,json,hashlib,shutil,importlib,importlib.metadata
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original');E=B/'engine';P=Path('D:/CodexBuilds/Hasla-publish-20261031');F=B/'natural/2019/T';sys.path[:0]=[str(E),str(P/'tools')]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
qpath=B/'natural/editions/IZhO_2019_T_KO.ready.json';q=load(qpath);out=Path(q['authoring_snapshot']);pdf=Path(q['output']);assert sha(pdf)==q['sha256']and q['pages']==8
def copy(src,rel):
 src=Path(src);dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);assert sha(src)==sha(dest)
for p in E.glob('*.py'):copy(p,Path('tools')/p.name)
for name in['izho_natural_spacing_rebuild','izho_natural_spacing_qa','izho_initial_fixed_style','final_translation_font_audit','heading_source_alignment_audit','modern_new_prose_collision_audit','initial_bitmap_language_labels','izho_natural_spacing_ready']:importlib.import_module(name)
resolution={}
for name,module in list(sys.modules.items()):
 path=getattr(module,'__file__',None)
 if not path or not path.lower().endswith('.py'):continue
 src=Path(path).resolve()
 if src.parent!=E.resolve()and not src.is_relative_to(P/'tools'):continue
 rel=Path('tools')/src.name if src.parent==E.resolve()else Path('fallback-tools')/(name.replace('.','/')+'.py')
 copy(src,rel);resolution[name]=dict(resolved_path=str(src),frozen_path=rel.as_posix(),sha256=sha(src))
save(out/'runtime-import-resolution.json',resolution);save(out/'runtime-versions.json',dict(python=sys.version,packages={p:importlib.metadata.version(p)for p in['PyMuPDF','pikepdf','fonttools','numpy','Pillow']}))
sources={};proofs=[]
for n in range(1,9):
 plan=load(F/f'plans/page{n:02}.json');proof=F/f'page{n:02}.pdf';a=load(proof.with_suffix('.audit.json'));assert a['passed']and a['output_sha256']==sha(proof)
 for key,digestkey in[('source_base','source_base_sha256'),('original_english_source','original_english_source_sha256')]:
  source=Path(plan[key]);assert sha(source)==plan[digestkey];rel=Path('immutable-inputs')/plan[digestkey]/source.name
  if plan[digestkey]not in sources:copy(source,rel);sources[plan[digestkey]]=dict(path=rel.as_posix(),sha256=plan[digestkey],bytes=source.stat().st_size)
 for p in[F/f'plans/page{n:02}.json',B/f'2019/original_style/page{n}.json',B/f'2019/inspection/page{n:02}-runs.json',B/f'2019/native-baseline/page{n:02}.qa.json',B/f'2019/native-baseline/page{n:02}.audit-spec.json']:copy(p,Path('source-review')/str(n)/p.name)
 for suffix in['.pdf','.audit.json','.qa.json','.font-source-style.json','.source-alignment.json','.prose-collision.json']:
  p=proof.with_suffix(suffix);copy(p,Path('exact-reviewed-proofs')/p.name)
 for suffix in['.language-overlay.json']:
  p=proof.with_suffix(suffix)
  if p.exists():copy(p,Path('exact-reviewed-proofs')/p.name)
 copy(F/f'page{n:02}-preview.json',Path('visual-review')/f'page{n:02}-preview.json')
 proofs.append(dict(page=n,proof_sha256=sha(proof),original_source_sha256=plan['original_english_source_sha256'],actual_input_base_sha256=plan['source_base_sha256']))
for folder in[F/'negative-exact-picture-boundary',B/'natural/2019-native-design-negatives']:
 for p in folder.rglob('*'):
  if p.is_file()and p.suffix in['.json','.pdf']:copy(p,Path('negative-controls')/folder.name/p.relative_to(folder))
for p in(B/'2019/inspection').glob('page02-label-*-measurement.json'):copy(p,Path('original-bitmap-label-measurements')/p.name)
copy(B/'2019/inspection/page02-raw-graph.png','original-bitmap-label-measurements/unchanged-source-image.png')
for p in[B/'source-policy.json',F/'visual-review.json',pdf.with_suffix('.poppler-assembly.json')]:copy(p,Path('edition-review')/p.name)
names=['prepare-izho2019-theory-native-source.py','build-izho2019-theory-baseline-page.py','prepare-izho2019-theory-natural.py','build-izho2019-theory-natural-page.py','render-izho2019-theory-preview.py','negative-izho2019-exact-picture-boundary.py','measure-izho2019-graph-labels.py','author-izho2019-graph-labels.py','negative-izho2019-native-design.py','refine-izho2019-page07-source-expression-membership.py','audit-izho2019-final-fonts-and-headings.py','finalize-izho2019-theory.py','freeze-izho2019-theory-authoring.py']+[f'author-izho2019-theory-page{n}.py'for n in range(1,9)]
for name in names:copy(Path('D:/CodexBuilds')/name,Path('scripts')/name)
copy(P/'tools/stage_natural_ready_v2.py','scripts/stage_natural_ready_v2.py')
negative=load(B/'natural/2019-native-design-negatives/negative-controls.json');assert negative['passed']and all(r['negative_rejected']for r in negative['rows'])
guard=sha(E/'pdf_native_inline_reposition.py');assert guard=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
save(out/'font-and-design-policy.json',dict(original_source_language='English',source_sha256=q['original_source_sha256'],all8_source_pages_complete=True,original_native_math_fonts_GIDs_fractional_points_baselines_and_expression_geometry_preserved=True,source_font_role_points_baselines_colors_and_orientation_independently_verified=True,regular_serif_Hangul='Batang',bold_serif_Hangul='NotoSerifCJKkr-Bold',sans_Hangul='NotoSansCJKkr source weight',source_bitmap_labels='Three isolated original chart labels; source-only raster font/point/baseline estimates, original ink centers and vertical90degree writing orientation retained. Korean text is not used to fit size. Original graph pixels outside old/new actual language ink remain protected at zero difference.',full_commercial_font_files_redistributed=False,math_retyped=False,math_rasterized=False,fonts_shrunk_to_fit=False,native_guard_sha256=guard,paragraph_word_spaces='quarter-em with Korean particle attachment',note='Original Ohm notation and source decimal commas are retained. A ragged final English paragraph line is composed within that original full-width paragraph. Picture QA samples pixels whose centers lie inside the exact source rectangle, with zero threshold and an actual picture alteration negative.'))
q.update(complete_original_source_pages=8,all_original_source_prose_translated=True,all_source_inputs=list(sources.values()),exact_reviewed_page_inputs=proofs,all_final_Hangul_actual_outlines_source_roles_points_baselines_colors_and_orientation_verified=True,final_Hangul_occurrences_checked=sum(load(F/f'page{n:02}.font-source-style.json')['hangul_glyphs_checked']for n in range(1,9)),original_source_heading_centers_verified=True,original_source_heading_and_caption_centers_checked=sum(load(F/f'page{n:02}.source-alignment.json')['headings_and_captions_checked']for n in range(1,9)),actual_missing_original_fraction_rule_negative_rejected=True,actual_nonlanguage_figure_alteration_negative_rejected=True,independent_poppler_native_page_append_verified=True,english_bitmap_figure_words_translated=3,actual_frozen_import_resolution='runtime-import-resolution.json',authoring_capture_note='Exact producing fork, resolved local imports, every actual initial8p/5p/4p/2p input version, original English source, per-page explicit source slots and immutable reviewed proofs, font/heading/collision QA, source-only chart label measurements and actual content-damage negative controls. Commercial font donors are recorded by hashes and actual embedded-outline comparisons.')
q['authoring_files']={p.relative_to(out).as_posix():sha(p)for p in sorted(out.rglob('*'))if p.is_file()};save(qpath,q);print('FROZEN_COMPLETE_NATIVE_SOURCE_EDITION',q['sha256'],q['pages'],q['final_Hangul_occurrences_checked'],len(q['authoring_files']),sum(p.stat().st_size for p in out.rglob('*')if p.is_file()),flush=True)
