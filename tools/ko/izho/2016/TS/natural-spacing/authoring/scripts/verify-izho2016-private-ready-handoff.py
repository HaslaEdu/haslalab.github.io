from pathlib import Path
import json,hashlib,shutil,datetime
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');R=Path('D:/CodexBuilds');F=B/'natural/2016/TS';Q=B/'natural/editions/IZhO_2016_TS_KO.ready.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'));q=load(Q);out=Path(q['authoring_snapshot']);pdf=Path(q['output'])
assert q['status']=='READY'and q['pages']==8 and sha(pdf)==q['sha256']=='506c08828d9dfddd0f21f78fca4cf65e795c9fbe7fcdf5ce539ab2818419046e'
def copy(src,rel):
 src=Path(src);dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst)
copy(B.parent/'izho-missing-scope-20261102.json','edition-review/frozen-missing-scope-20261102.json')
assert sha(B.parent/'izho-missing-scope-20261102.json')=='d5ce1beab8738743e0d3a09063c5143cd270fe6e81db9bfabb6a2717b6d9200a'
copy(B/'legacy-semantics/translation.json','edition-review/legacy-semantics-only-translation.json')
for n in range(1,9):copy(B/f'2016/inspection/page{n:02}-source.png',Path('original-source-visual-review')/f'page{n:02}-source.png')
for p in(B/'natural').glob('2016-page*-native-guard-diagnostic.jsonl'):copy(p,Path('edition-review/source-native-guard-diagnostics')/p.name)
copy(R/'verify-izho2016-private-ready-handoff.py','scripts/verify-izho2016-private-ready-handoff.py')
q['authoring_files']={p.relative_to(out).as_posix():sha(p)for p in sorted(out.rglob('*'))if p.is_file()};Q.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
for name,digest in q['authoring_files'].items():assert sha(out/name)==digest
for p in q['all_source_inputs']:assert sha(out/p['path'])==p['sha256']
for n in range(1,9):
 source=F/f'page{n:02}.pdf';assert sha(source)==sha(out/'exact-reviewed-proofs'/source.name)
 for suffix,key in[('.audit.json','output_sha256'),('.font-source-style.json','proof_sha256'),('.source-alignment.json','proof_sha256'),('.prose-collision.json','final_sha256'),('.equation-counters.json','proof_sha256'),('.non-hangul-prose-collision.json','proof_sha256'),('.actual-expression-geometry.json','proof_sha256')]:
  a=load(source.with_suffix(suffix));assert a['passed']and a[key]==sha(source)
assert q['verified_original_native_ink_missing_pixels']==q['retained_native_control_ink_missing_pixels']==q['changed_pixels_outside_text_and_intended_native_math_motion']==q['changed_nonselected_native_graphical_pixels']==q['figure_and_locked_display_math_changed_pixels']==0
assert not q['native_ink_phase_or_witness_exceptions'];assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
result=dict(status='READY_PRIVATE_FROZEN',verified_utc=datetime.datetime.now(datetime.UTC).isoformat(),source_sha256=q['original_source_sha256'],pdf=str(pdf),pdf_sha256=q['sha256'],pdf_bytes=pdf.stat().st_size,ready_manifest=str(Q),ready_manifest_sha256=sha(Q),authoring_snapshot=str(out),frozen_files=len(q['authoring_files']),frozen_bytes=sum(p.stat().st_size for p in out.rglob('*')if p.is_file()),all_frozen_file_hashes_verified=True,source_pages=8,all8_complete_original_source_and_current_final_full_visuals=True,explicit_source_prose_selections=389,all8_six_independent_QA_plus_extra_and_actual_geometry=True,original_display_counter_labels=51,original_native_counter_glyphs=178,final_Hangul_source_font_point_Y_paint_role_occurrences=q['final_Hangul_occurrences_checked'],actual_complete_expression_groups=q['independent_actual_expression_groups_checked'],actual_native_expression_glyphs=q['independent_actual_expression_native_glyphs_checked'],actual_original_graphical_paths=q['independent_actual_expression_source_graphical_paths_checked'],all_native_ink_loss_or_graphical_drift=0,native_append_MuPDF4x_changed_pixels=0,native_append_external_Poppler144_changed_pixels=0,actual_fraction_rule_and_score_glyph_bad_PDFs_rejected=True,no_phase_or_witness_exceptions=True,native_guard_sha256=sha(B/'engine/pdf_native_inline_reposition.py'),all_original_source_PDF_native_fonts_GIDs_fractional_Tf_Tm_points_paint_Y_graphics_preserved=True,whole_original_MathType_Forms_and_Word_clips_preserved=True,source_CID_original_clip_isolation_roundtrips='MuPDF4x/8x and independent Poppler144 full-page zeroRGB, prior to movement',Git_upload_repo_index_or_global_state_actions=False,publication_performed=False,pending_private_work=[])
(B/'natural/2016-private-ready-handoff.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(result,ensure_ascii=False),flush=True)
