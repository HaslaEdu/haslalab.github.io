from pathlib import Path
import sys,json,hashlib,shutil,importlib,importlib.metadata
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2013-complete-solutions');E=B/'engine';PD=Path('D:/CodexBuilds/Hasla-publish-20261031');F=B/'natural/2013/TS';R=Path('D:/CodexBuilds');sys.path[:0]=[str(E),str(PD/'tools')];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
qpath=B/'natural/editions/IZhO_2013_TS_KO.ready.json';q=load(qpath);out=Path(q['authoring_snapshot']);pdf=Path(q['output']);assert q['pages']==10 and sha(pdf)==q['sha256']=='c10de130ef446380f7fadf35cf287f562259f14ca6fb63ff30cf51fddd3addae'and q['original_source_sha256']=='2804ded48ad009bf58884b871f0f4817c64762b8a0f586e42056908fc4be10f1';assembly=load(pdf.with_suffix('.poppler-assembly.json'));assert assembly['passed']and assembly['pdf_sha256']==q['sha256']and len(assembly['pages'])==10
def save(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
def copy(src,rel):
 src=Path(src);dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists()and dest.read_bytes()==src.read_bytes():return
 shutil.copy2(src,dest);assert sha(src)==sha(dest)
for p in E.glob('*.py'):copy(p,Path('tools')/p.name)
for name in['izho_natural_spacing_rebuild','izho_natural_spacing_qa','izho_initial_fixed_style','final_translation_font_audit','heading_source_alignment_audit','modern_new_prose_collision_audit','izho_2013_equation_counters','izho_2013_inline_clips','izho_2013_non_hangul_prose_collision','izho_2013_prose_bitmap_overlap_reference','izho_2013_offset_row_native_ownership','source_prose_paint','izho_natural_spacing_ready']:importlib.import_module(name)
resolution={}
for name,module in list(sys.modules.items()):
 path=getattr(module,'__file__',None)
 if not path or not path.lower().endswith('.py'):continue
 src=Path(path).resolve()
 if src.parent!=E.resolve()and not src.is_relative_to(PD/'tools'):continue
 rel=Path('tools')/src.name if src.parent==E.resolve()else Path('fallback-tools')/(name.replace('.','/')+'.py');copy(src,rel);resolution[name]=dict(resolved_path=str(src),frozen_path=rel.as_posix(),sha256=sha(src))
save(out/'runtime-import-resolution.json',resolution);save(out/'runtime-versions.json',dict(python=sys.version,packages={p:importlib.metadata.version(p)for p in['PyMuPDF','pikepdf','fonttools','numpy','Pillow']}))
sources={};proofs=[];counter_count=counter_glyphs=0;prose_selections=0
for n in range(1,11):
 plan=load(F/f'plans/page{n:02}.json');proof=F/f'page{n:02}.pdf';a=load(proof.with_suffix('.audit.json'));assert a['passed']and a['output_sha256']==sha(proof)
 for key,digestkey in[('source_base','source_base_sha256'),('original_english_source','original_english_source_sha256')]:
  source=Path(plan[key]);assert sha(source)==plan[digestkey];rel=Path('immutable-inputs')/plan[digestkey]/source.name
  if plan[digestkey]not in sources:copy(source,rel);sources[plan[digestkey]]=dict(path=rel.as_posix(),sha256=plan[digestkey],bytes=source.stat().st_size)
 authored=B/f'2013/original_style/page{n}.json';prose_selections+=len(load(authored)['slots'])
 for p in[F/f'plans/page{n:02}.json',authored,B/f'2013/inspection/page{n:02}-runs.json',B/f'2013/native-baseline/page{n:02}.qa.json',B/f'2013/native-baseline/page{n:02}.audit-spec.json']:copy(p,Path('source-review')/str(n)/p.name)
 for suffix in['.pdf','.native-control.pdf','.audit.json','.qa.json','.font-source-style.json','.source-alignment.json','.prose-collision.json','.equation-counters.json','.non-hangul-prose-collision.json']:
  p=proof.with_suffix(suffix);copy(p,Path('exact-reviewed-proofs')/p.name)
 order=F/f'page{n:02}-actual-native-prose-order-audit.json'
 if order.exists():assert load(order)['passed']and load(order)['pdf_sha256']==sha(proof);copy(order,Path('exact-reviewed-proofs')/order.name)
 c=load(proof.with_suffix('.equation-counters.json'));assert c['passed']and c['proof_sha256']==sha(proof);counter_count+=c['equation_counters_checked'];counter_glyphs+=c['native_counter_glyphs_checked']
 for suffix in['.json','.png']:copy(F/f'page{n:02}-preview{suffix}',Path('visual-review')/f'page{n:02}-preview{suffix}')
 proofs.append(dict(page=n,proof_sha256=sha(proof),original_source_sha256=plan['original_english_source_sha256'],actual_input_base_sha256=plan['source_base_sha256']))
assert(counter_count,counter_glyphs,prose_selections)==(49,177,444)
for p in(B/'2013/reviewed-original-prose-bitmap-overlap').glob('*'):
 if p.is_file():copy(p,Path('original-prose-bitmap-overlap-reference')/p.name)
for p in(B/'natural/2013-native-design-negatives').rglob('*'):
 if p.is_file()and p.suffix in['.json','.pdf','.log']:copy(p,Path('negative-controls')/p.relative_to(B/'natural/2013-native-design-negatives'))
for p in[B/'engine-copy-and-source-policy.json',F/'visual-review.json',pdf.with_suffix('.poppler-assembly.json'),B/'2013-reviewed-prose-revisions.json',B/'2013-reviewed-native-title-sequence-revisions.json']:copy(p,Path('edition-review')/p.name)
prefixes=('author-','build-','prepare-','revise-','refine-','bind-','check-','audit-','record-','finalize-','freeze-','enable-','negative-')
for p in R.glob('*izho2013*.py'):
 if p.name.startswith(prefixes)or p.name=='izho2013_authoring.py':copy(p,Path('scripts')/p.name)
copy(PD/'tools/stage_natural_ready_v2.py','scripts/stage_natural_ready_v2.py')
neg=load(B/'natural/2013-native-design-negatives/negative-controls.json');assert neg['passed']and len(neg['rows'])==3 and all(r['negative_rejected']and r['delivered_proof_unmodified']for r in neg['rows'])
guard=sha(E/'pdf_native_inline_reposition.py');assert guard=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
save(out/'font-and-design-policy.json',dict(original_source_language='English',source_sha256=q['original_source_sha256'],all10_original_source_pages_prose_and_grading_complete=True,explicit_source_prose_selections=444,original_math_fonts_GIDs_points_paint_scripts_and_complete_expression_geometry_preserved=True,existing_original_mathematical_bitmaps_retained_byte_for_byte=True,original_prose_roles_points_baselines_paint_and_title_table_centers_independently_verified=True,regular_serif_Hangul='Batang',original_two_line_main_title='Actual15.96pt source bold italic role; source italic shear retained.',native_math_and_graphics_retyped_or_newly_rasterized=False,fonts_shrunk_to_fit=False,paragraph_word_spaces='quarter-em with normal Korean particle and compound attachment',original_source_counter_labels=49,original_native_counter_glyphs=177,original_selected_English_descender_overlap='Only the exact original English p in vaporized is removed from an independent reference control. All13 changed pixels inside the next bitmap envelope become pure white without that prose glyph; all other full-bitmap-region pixels still require exact equality. An actual damaged bitmap PDF is rejected.',offset_source_rows='Original3pt Y offset retained; trailing Korean clause starts3pt after the preceding source-condition endpoint. Every original x=0 CID belongs to its original640.87pt row exactly once, with one common dx. No native glyph is excluded from final audits.',native_prose_reference_order='Actual spatial CID/Hangul order checked for original title numerals/parentheses and original N/S table references.',all_actual_bad_PDF_controls_rejected=True,native_guard_sha256=guard,commercial_full_font_files_redistributed=False,note='Original source spelling/numbering/numerical mistakes, Latin/Cyrillic units and decimal comma/point conventions are retained literally.'))
q.update(complete_original_source_pages=10,all_original_source_prose_translated=True,all_original_grading_schemes_translated=True,all_source_inputs=list(sources.values()),exact_reviewed_page_inputs=proofs,all_final_Hangul_actual_outlines_source_roles_points_baselines_colors_and_actual_paint_verified=True,final_Hangul_occurrences_checked=sum(load(F/f'page{n:02}.font-source-style.json')['hangul_glyphs_checked']for n in range(1,11)),original_source_heading_and_table_centers_verified=True,original_source_heading_and_table_centers_checked=sum(load(F/f'page{n:02}.source-alignment.json')['headings_and_captions_checked']for n in range(1,11)),all_original_display_equation_counter_positions_verified=True,original_display_equation_counters_checked=counter_count,original_counter_native_glyphs_checked=counter_glyphs,all_new_body_Hangul_and_non_Hangul_prose_ink_collisions_zero=True,actual_counter_drift_covered_native_counter_and_math_bitmap_damage_negatives_rejected=True,independent_poppler_native_page_append_verified=True,actual_frozen_import_resolution='runtime-import-resolution.json',authoring_capture_note='Exact producing private engine/import closure, all immutable content-versioned inputs, complete original10-page English source,444explicit selected prose ranges, all reviewed proofs and font-point-paint/heading/counter/natural-word-spacing/collision audits and full-page previews. Source-specific original English descender overlap and original3pt-offset row ownership are independently verified with no glyph omission. Three actual bad PDFs are rejected. Shared native guard and every global ink/geometry threshold unchanged.')
q['authoring_files']={p.relative_to(out).as_posix():sha(p)for p in sorted(out.rglob('*'))if p.is_file()};save(qpath,q);print('FROZEN_COMPLETE10_PAGE_IZHO2013_NATIVE_SOLUTIONS',q['sha256'],q['final_Hangul_occurrences_checked'],len(q['authoring_files']),sum(p.stat().st_size for p in out.rglob('*')if p.is_file()),flush=True)
