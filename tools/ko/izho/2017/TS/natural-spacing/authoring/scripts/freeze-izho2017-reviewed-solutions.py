from pathlib import Path
import sys,json,hashlib,shutil,importlib,importlib.metadata,datetime
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2017-complete-solutions');F=B/'natural/2017/TS';E=B/'engine';PD=Path('D:/CodexBuilds/Hasla-publish-20261031');R=Path('D:/CodexBuilds');C=B.parent;sys.path[:0]=[str(E),str(PD/'tools')];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
Q=B/'natural/editions/IZhO_2017_TS_KO.ready.json';q=load(Q);pdf=Path(q['output']);out=Path(q['authoring_snapshot']);assert q['pages']==14 and q['original_source_sha256']=='fb90239d8da3dea3dcfe104551243f444802632a74a47a139374013aa16080f1';assert sha(pdf)==q['sha256'];assert not(out/'FROZEN-COMPLETE.json').exists(),'Never amend a sealed authoring closure';assembly=load(pdf.with_suffix('.poppler-assembly.json'));assert assembly['passed']and len(assembly['pages'])==14 and assembly['pdf_sha256']==q['sha256']
def save(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
def copy(src,rel):
 src=Path(src);dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);pin=sha(src)
 if dest.exists()and sha(dest)==pin:return
 shutil.copy2(src,dest);assert sha(dest)==sha(src)==pin
for p in E.glob('*.py'):copy(p,Path('tools')/p.name)
modules=['izho_natural_spacing_rebuild','izho_natural_spacing_qa','izho_natural_spacing_ready','izho_initial_fixed_style','final_translation_font_audit','heading_source_alignment_audit','modern_new_prose_collision_audit','izho_2017_equation_counters','izho_2017_independent_original_math_geometry','izho_2017_non_hangul_prose_collision','izho_2017_inline_lambda_native_phase','izho_2017_original_formula_conjunction_order','izho_2017_page07_original_conjunction_order']
for name in modules:importlib.import_module(name)
resolution={}
for name,module in list(sys.modules.items()):
 path=getattr(module,'__file__',None)
 if not path or not path.lower().endswith('.py'):continue
 src=Path(path).resolve()
 if src.parent!=E.resolve()and not src.is_relative_to(PD/'tools'):continue
 rel=Path('tools')/src.name if src.parent==E.resolve()else Path('fallback-tools')/(name.replace('.','/')+'.py');copy(src,rel);resolution[name]=dict(resolved_path=str(src),frozen_path=rel.as_posix(),sha256=sha(src))
save(out/'runtime-import-resolution.json',resolution);save(out/'runtime-versions.json',dict(python=sys.version,packages={p:importlib.metadata.version(p)for p in ['PyMuPDF','pikepdf','fonttools','numpy','Pillow']}))
sources={};proofs=[];counters=glyphs=slots=0;active_program_dirs=set()
for n in range(1,15):
 plan=load(F/f'plans/page{n:02}.json');proof=F/f'page{n:02}.pdf';audit=load(proof.with_suffix('.audit.json'));assert audit['passed']and audit['output_sha256']==sha(proof)
 for key,digestkey in [('source_base','source_base_sha256'),('original_english_source','original_english_source_sha256')]:
  src=Path(plan[key]);pin=plan[digestkey];assert sha(src)==pin
  if pin not in sources:
   rel=Path('immutable-inputs')/pin/src.name;copy(src,rel);sources[pin]=dict(path=rel.as_posix(),sha256=pin,bytes=src.stat().st_size)
 authored=B/f'2017/original_style/page{n}.json';slots+=len(load(authored)['slots'])
 for p in [F/f'plans/page{n:02}.json',authored,B/f'2017/inspection/page{n:02}-runs.json',B/f'2017/inspection/page{n:02}-original-native-inline-inventory.json',B/f'2017/native-baseline/page{n:02}.qa.json',B/f'2017/native-baseline/page{n:02}.audit-spec.json']:
  if p.exists():copy(p,Path('source-review')/str(n)/p.name)
 for p in F.glob(f'page{n:02}*'):
  if p.is_file()and p.suffix in ['.pdf','.json','.png','.log']and not p.name.endswith(('.old-source.pdf','.native-control.pdf')):copy(p,Path('exact-reviewed-proofs')/p.name)
 # The one-page raw source, native paint-only control, final proof and each
 # active original-program reference are separate immutable artifact roles.
 assert proof.with_suffix('.old-source.pdf').exists()and proof.with_suffix('.native-control.pdf').exists()
 for suffix in ['.old-source.pdf','.native-control.pdf']:copy(proof.with_suffix(suffix),Path('raw-and-native-controls')/proof.with_suffix(suffix).name)
 c=load(proof.with_suffix('.equation-counters.json'));assert c['passed']and c['proof_sha256']==sha(proof);counters+=c['equation_counters_checked'];glyphs+=c['native_counter_glyphs_checked']
 if plan.get('native_ink_witness'):active_program_dirs.add(Path(plan['native_ink_witness']).parent)
 base=Path(plan['source_base'])
 if base.is_relative_to(B)and 'native-baseline'not in base.parts:active_program_dirs.add(base.parent)
 proofs.append(dict(page=n,proof_sha256=sha(proof),original_source_sha256=plan['original_english_source_sha256'],actual_input_base_sha256=plan['source_base_sha256']))
assert(counters,glyphs,slots)==(82,301,562)
for folder in sorted(active_program_dirs):
 assert folder.is_relative_to(B)
 for p in folder.rglob('*'):
  if p.is_file()and '__pycache__'not in p.parts and p.suffix in ['.pdf','.json','.png','.bin','.py','.log']:copy(p,Path('active-original-native-program-evidence')/folder.relative_to(B)/p.relative_to(folder))
negative=B/'natural/2017-native-design-negatives';neg=load(negative/'negative-controls.json');assert neg['passed']and len(neg['rows'])==5
for p in negative.rglob('*'):
 if p.is_file()and p.suffix in ['.pdf','.json','.log']:copy(p,Path('negative-controls')/p.relative_to(negative))
repair=B/'page07-conjunction-repair'
if repair.exists():
 for p in repair.rglob('*'):
  if p.is_file()and '__pycache__'not in p.parts and p.suffix in ['.pdf','.json','.png','.bin','.py','.cjs','.log']:copy(p,Path('source-page07-conjunction-repair')/p.relative_to(repair))
for p in (B/'publication-contracts').rglob('*'):
 if p.is_file()and '__pycache__'not in p.parts and not p.name.startswith('private-'):copy(p,Path('publication-contracts')/p.relative_to(B/'publication-contracts'))
bundle=load(B/'publication-contracts/source-bound-native-design-contract.json');assert bundle['full_pdf_sha256']==q['sha256']and len(bundle['artifacts'])==123
artifact_map=load(B/'publication-contracts/actual-native-design-artifact-map.json');by_id={a['id']:a for a in artifact_map};existing={sha(p):p.relative_to(out).as_posix()for p in out.rglob('*')if p.is_file()};bindings=[]
for a in bundle['artifacts']:
 pinned=by_id[a['id']];assert pinned['sha256']==a['sha256']and pinned['bytes']==a['bytes'];src=Path(pinned['source_path']);assert sha(src)==a['sha256']and src.stat().st_size==a['bytes']
 assert src.is_relative_to(B)or src.is_relative_to(Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2017-complete-solutions'))or(src.suffix=='.py'and(src.parent==R or src.is_relative_to(PD/'tools'))),src
 if a['sha256']not in existing:
  rel=Path('source-native-contract-artifacts')/a['sha256']/src.name;copy(src,rel);existing[a['sha256']]=rel.as_posix()
 bindings.append(dict(id=a['id'],path=existing[a['sha256']],sha256=a['sha256'],bytes=a['bytes']))
save(out/'actual-frozen-native-design-artifact-map.json',bindings)
for p in [F/'visual-review.json',pdf.with_suffix('.poppler-assembly.json'),B/'engine-copy-and-source-policy.json',B/'new-output-location-copy-receipt.json',B/'2017-source-display-counter-inventory.json',B/'2017/inspection/all14-original-native-whitespace-GID-inventory.json']:
 if p.exists():copy(p,Path('edition-review')/p.name)
for p in list(R.glob('*izho2017*.py'))+list(C.glob('*izho2017*.py')):
 if p.is_file():copy(p,Path('scripts')/p.name)
copy(PD/'tools/stage_natural_ready_v2.py','scripts/stage_natural_ready_v2.py')
guard=sha(E/'pdf_native_inline_reposition.py');assert guard=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
save(out/'font-and-design-policy.json',dict(source_sha256=q['original_source_sha256'],all14_original_pages_prose_and_grading_complete=True,explicit_source_prose_selections=562,original_display_counters=82,original_native_counter_glyphs=301,original_native_math_fonts_GIDs_fractional_points_Tf_Tm_clips_rules_paint_scripts_and_complete_expression_geometry_preserved=True,native_mathematical_ink_omitted=False,mathematical_text_retyped_or_newly_rasterized=False,fonts_shrunk_to_fit=False,paragraph_word_spaces='Natural quarter-em Korean word spaces, with correct source word/formula reading order.',source_page6_original_programs='Two complete original9/6-CID expressions and original fraction rule retain all ancestor clips in ordinary native Forms; source page transparency group remains at original single level; pre-motion original/modified pageRGB identical in MuPDF4/8 and Poppler144.',source_page11_original_program='All7 exact original native CIDs and complete original MathType Form, fonts and root strokes at measured whole-Form CTM; all6nativeRGB comparisons and croppedSVG4/8/12 have zero loss. Raw1pixel fullpageunhinted edge diagnostic retained, proof unchanged, no global threshold changed.',native_guard_sha256=guard,all5_root_actual_bad_PDF_controls_rejected=True,commercial_full_font_files_redistributed=False,original_source_errors_and_numbering_retained_literally=True,current_audited_private_runtime_and_exact_content_versioned_inputs_and_proofs_captured=True))
q.update(complete_original_source_pages=14,all_original_source_prose_translated=True,all_original_grading_schemes_translated=True,all_source_inputs=list(sources.values()),exact_reviewed_page_inputs=proofs,all_final_Hangul_actual_outlines_source_roles_points_baselines_colors_and_actual_paint_verified=True,final_Hangul_occurrences_checked=sum(load(F/f'page{n:02}.font-source-style.json')['hangul_glyphs_checked']for n in range(1,15)),original_source_heading_and_table_centers_verified=True,original_source_heading_and_table_centers_checked=sum(load(F/f'page{n:02}.source-alignment.json')['headings_and_captions_checked']for n in range(1,15)),all_original_display_equation_counter_positions_verified=True,original_display_equation_counters_checked=counters,original_counter_native_glyphs_checked=glyphs,all_new_body_Hangul_and_non_Hangul_prose_ink_collisions_zero=True,independent_poppler_native_page_append_verified=True,all5_root_actual_bad_PDF_controls_rejected=True,actual_frozen_import_resolution='runtime-import-resolution.json',authoring_capture_note='Current audited source-specific runtime and import closure; exact immutable source/base input versions, all14 raw outline controls/native paint controls/final proofs, all562 explicit original prose selections, actual font/point/paint/heading/counter/natural-spacing/collision/math-program audits and fullpage previews, active full-original-program references and all actual rejected design PDFs. Original D authoring remains unchanged; new substantive output generation on C. No mathematical ink, physical native source glyph or complete expression is omitted; shared guard and every global tolerance unchanged.')
files={p.relative_to(out).as_posix():sha(p)for p in sorted(out.rglob('*'))if p.is_file()and p.name!='FROZEN-COMPLETE.json'};q['authoring_files']=files;save(Q,q)
for rel,pin in files.items():assert sha(out/rel)==pin
seal=dict(status='FROZEN_COMPLETE_SOURCE2017_TS',ready_manifest_sha256=sha(Q),pdf_sha256=q['sha256'],files=len(files),bytes=sum((out/rel).stat().st_size for rel in files),all_files_rehashed=True,all14_raw_native_controls_and_active_source_program_references_frozen=True,checked_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat());save(out/'FROZEN-COMPLETE.json',seal);print('FROZEN_COMPLETE_SOURCE2017_TS',json.dumps(seal),flush=True)
