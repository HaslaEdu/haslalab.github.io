'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const prefix='tools/ko/cpho/2011/t/native-original-v1';
const standalone=process.env.CPHO2011_STANDALONE_ROOT?path.resolve(process.env.CPHO2011_STANDALONE_ROOT):null;
const repo=path.resolve(process.env.CPHO2011_PUBLIC_ROOT||path.join(__dirname,'..')),root=standalone||path.join(repo,prefix);
const helper=require(standalone?path.join(root,'cpho2011-theory-native-publication.cjs'):path.join(repo,'tests/helpers/cpho2011-theory-native-publication.cjs'));
const original=JSON.parse(fs.readFileSync(path.join(root,'source-bound-theory-native-contract.json'),'utf8')),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),results=[];
function raw(a){const p=path.resolve(root,a.payload_relative);assert.ok(p.startsWith(root+path.sep));return fs.readFileSync(p);}
function fixture(){const bundle=JSON.parse(JSON.stringify(original)),overrides=new Map();return {bundle,overrides,json(id,fn){const a=bundle.artifacts.find(a=>a.id===id);assert.ok(a);const q=JSON.parse((overrides.get(id)||raw(a)).toString('utf8'));fn(q);const bytes=Buffer.from(JSON.stringify(q));overrides.set(id,bytes);a.sha256=sha(bytes);a.bytes=bytes.length;},read(a){return overrides.has(a.id)?overrides.get(a.id):raw(a);}};}
function attempt(name,body,reject=false){let error=null;try{body();}catch(e){error=e;}const intentional=error&&(error.code==='ERR_ASSERTION'||error.code==='INTENTIONALLY_MISSING_PUBLIC_PAYLOAD');const passed=reject?Boolean(intentional):!error;results.push({name,expected:reject?'reject coherent actual-artifact mutation':'accept actual current standalone/public bytes',passed,error:error?String(error):null});if(!passed)console.error('C11_T_CONTRACT_CASE_FAILED',name,error);}
function mutant(name,change){attempt(name,()=>{const f=fixture();change(f);helper.validateEdition(f.bundle,f.bundle.editions[0],{readArtifact:a=>f.read(a)});},true);}
for(const e of original.editions){attempt('actual-public-'+e.language,()=>helper.validateEdition(original,e,{readArtifact:raw}));if(standalone)attempt('actual-private-full-input-'+e.language,()=>helper.validateEdition(original,e,{readArtifact:raw,includePrivateRaw:true}));}
attempt('source-path-is-inventory-only',()=>{const f=fixture();for(const a of f.bundle.artifacts)a.source_path='X:/intentionally-unreadable-inventory-only';helper.validateEdition(f.bundle,f.bundle.editions[0],{readArtifact:a=>f.read(a)});});
attempt('literal-private-raw-boundary-never-read',()=>{const ids=new Set(helper.pins.PRIVATE.map(r=>r.id));helper.validateEdition(original,original.editions[0],{readArtifact:a=>{assert.ok(!ids.has(a.id),'Public validator attempted private raw input');return raw(a);}});});
mutant('wrong-original-source-SHA',f=>f.bundle.source_sha256='0'.repeat(64));
mutant('changed-ab04-guard-SHA',f=>f.bundle.guard_sha256='0'.repeat(64));
mutant('missing-original-theory-page',f=>f.bundle.classification.physical_source_pages.pop());
mutant('dishonest-TS-completion',f=>f.bundle.classification.solution_document_TS_pending=false);
mutant('wrong-final-page-count',f=>f.bundle.editions[0].pages=3);
mutant('altered-proof-pin',f=>f.bundle.proofs['p03-en']='0'.repeat(64));
mutant('altered-actual-immutable-plan-pin',f=>f.bundle.actual_producing_plans['p03-en']='0'.repeat(64));
mutant('CID-coverage-count-rebased',f=>f.bundle.actual_original_encoded_CIDs['p03-en']--);
mutant('new-glyph-coverage-count-rebased',f=>f.bundle.actual_new_donor_glyphs['p03-en']--);
mutant('missing-public-payload',f=>{f.read=a=>{if(a.id==='p03-en-proof'){const e=new Error('Deliberately missing required public proof');e.code='INTENTIONALLY_MISSING_PUBLIC_PAYLOAD';throw e;}return raw(a);};});
mutant('raw-public-payload-altered',f=>{const a=f.bundle.artifacts.find(a=>a.id==='p03-en-proof'),bytes=Buffer.from(raw(a));bytes[128]^=1;f.overrides.set(a.id,bytes);});
mutant('removed-public-ledger-entry',f=>f.bundle.artifacts.splice(f.bundle.artifacts.findIndex(a=>a.id==='p03-en-proof'),1));
mutant('duplicate-actual-artifact-ID',f=>f.bundle.artifacts.push({...f.bundle.artifacts[0]}));
mutant('payload-traversal-path',f=>f.bundle.artifacts[0].payload_relative='../outside-source.pdf');
mutant('private-ID-mutation',f=>f.bundle.private_raw_input_fixed_boundary[0].id+='-invented');
mutant('private-role-mutation',f=>f.bundle.private_raw_input_fixed_boundary[0].role='unreviewed-private');
mutant('private-hash-mutation',f=>f.bundle.private_raw_input_fixed_boundary[0].sha256='0'.repeat(64));
mutant('private-size-mutation',f=>f.bundle.private_raw_input_fixed_boundary[0].bytes++);
mutant('private-ledger-entry-removed',f=>f.bundle.private_raw_input_fixed_boundary.pop());
mutant('public-proof-reclassified-as-private',f=>{const a=f.bundle.artifacts.find(a=>a.id==='p03-en-proof');f.bundle.private_raw_input_fixed_boundary.push({id:a.id,role:a.role,sha256:a.sha256,bytes:a.bytes});});
mutant('private-raw-artifact-hash-rebased',f=>{const id=f.bundle.private_raw_input_fixed_boundary[0].id;f.bundle.artifacts.find(a=>a.id===id).sha256='0'.repeat(64);});
mutant('source-space-painted-glyph-assumption',f=>f.json('source-T-space-paint-proof',q=>q.all_actual_source_space_paint_zero=false));
mutant('original-CID-literal-Tf-rebased',f=>f.json('p03-en-CID',q=>q.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0].original_Tf+=.25));
mutant('original-CID-code-rebased',f=>f.json('p03-en-CID',q=>q.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0].original_encoded_CID_hex='ffff'));
mutant('original-native-GID-rebased',f=>f.json('p03-en-CID',q=>q.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0].source_glyphs[0].trace_gid++));
mutant('original-full-native-Tm-Y-rebased',f=>f.json('p03-en-CID',q=>q.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0].original_full_per_CID_Tm[5]+=.25));
mutant('original-CID-suppressed',f=>f.json('p03-en-CID',q=>q.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0].original_CID_Tf_Tm_font_GID_fractional_point_and_paint_exact=false));
mutant('unexpected-original-CID-program',f=>f.json('p03-en-CID',q=>q.unexpected_original_resource_CID_programs=1));
mutant('native-Y-tolerance-relaxed',f=>f.json('p03-en-CID',q=>q.position_measurement_tolerance_pt=.01));
mutant('lost-original-native-ink',f=>f.json('p03-en-native',q=>q.raw_original_input_native_ink.newly_missing_native_ink_pixels=1));
mutant('math-script-relative-geometry-failed',f=>f.json('p03-en-native',q=>q.original_native_script_relative_geometry.passed=false));
mutant('literal-native-vector-program-failed',f=>f.json('p03-en-native',q=>q.independent_original_native_geometry.literal_original_vector_path_programs[0].passed=false));
mutant('original-native-font-program-changed',f=>f.json('p03-en-native',q=>q.original_font_dictionary_and_programs[0].original_font_dictionary_and_programs_exact=false));
mutant('source-PageGroup-changed',f=>f.json('p03-en-native',q=>q.original_source_to_initial_and_final_Page_Group_exact=false));
mutant('ordinary-new-source-point-rebased',f=>f.json('p03-en-new-prose',q=>q.source_point_baseline_center_quarter_em_word_gap_and_literal_paint_rows[0].actual_original_source_point+=.25));
mutant('quarter-em-word-gap-rebased',f=>f.json('p03-en-new-prose',q=>q.source_point_baseline_center_quarter_em_word_gap_and_literal_paint_rows[0].expected_word_gap_pt+=.25));
mutant('new-source-baseline-rebased',f=>f.json('p03-en-new-prose',q=>q.source_point_baseline_center_quarter_em_word_gap_and_literal_paint_rows[0].actual_original_source_baseline+=.25));
mutant('native-actual-new-font-ink-missing',f=>f.json('p03-en-new-prose',q=>q.missing_actual_new_font_native_ink_pixels=1));
mutant('actual-new-font-subset-program-rebased',f=>f.json('p03-en-new-prose',q=>q.new_original_role_font_programs[0].actual_embedded_font_program_sha256='0'.repeat(64)));
mutant('used-full-donor-GID-rebased',f=>{const id=f.bundle.bindings['p03-en'].used_witnesses.SimSun;f.json(id,q=>{q.actual_used_glyphs[0].actual_original_donor_GID++;q.actual_used_glyphs[0].actual_embedded_subset_GID++;});});
mutant('used-full-donor-outline-rebased',f=>{const id=f.bundle.bindings['p03-en'].used_witnesses.SimSun;f.json(id,q=>q.actual_used_glyphs[0].source_donor_resolved_outline=[]);});
mutant('used-full-donor-hmtx-rebased',f=>{const id=f.bundle.bindings['p03-en'].used_witnesses.SimSun;f.json(id,q=>q.actual_used_glyphs[0].source_donor_hmtx[0]++);});
mutant('whole-math-expression-common-dx-rebased',f=>{const id=f.bundle.bindings['p02-ko'].whole_math_path_witness;f.json(id,q=>q.complete_original_math_expression_groups[0].actual_entire_expression_common_dx+=.1);});
mutant('whole-original-math-rule-paint-rebased',f=>{const id=f.bundle.bindings['p02-ko'].whole_math_path_witness;f.json(id,q=>q.complete_original_math_expression_groups[0].complete_original_rule_programs[0].original_literal_entry_state.paint.w+=.1);});
mutant('one-of-six-native-renderers-missing',f=>{const id=f.bundle.bindings['p02-ko'].whole_math_path_witness;f.json(id,q=>q.fullpage_six_actual_RGB_renderer_comparisons.pop());});
mutant('original-native-fullpage-RGB-one-pixel-damage',f=>{const id=f.bundle.bindings['p02-ko'].whole_math_path_witness;f.json(id,q=>q.fullpage_six_actual_RGB_renderer_comparisons[0].all_fullpage_RGB_different_pixels=1);});
mutant('raw-67-region-failure-hidden',f=>f.json('p02-ko-native',q=>q.nonselected_original_native_graphical_ink.changed_nonselected_native_graphical_pixels=0));
mutant('source-r25-point-rebased',f=>{const id=f.bundle.bindings['p01-ko'].source_background_witness;f.json(id,q=>q.source_literal_point=7.57);});
mutant('source-r25-original-CID-ID-rebased',f=>{const id=f.bundle.bindings['p01-ko'].source_background_witness;f.json(id,q=>q.original_four_CID_glyphs[0].source_trace_index--);});
mutant('source-r25-original-center-rebased',f=>{const id=f.bundle.bindings['p01-ko'].source_background_witness;f.json(id,q=>q.source_center+=.01);});
mutant('source-r25-actual-fullpage-background-damage',f=>{const id=f.bundle.bindings['p01-ko'].source_background_witness;f.json(id,q=>q.six_actual_renderer_comparisons[0].entire_fullpage_background_and_new_language_RGB_errors=1);});
mutant('source-r25-new-overlap-elsewhere-hidden',f=>{const id=f.bundle.bindings['p01-ko'].source_background_witness;f.json(id,q=>q.six_actual_renderer_comparisons[0].actual_overlap_outside_exact_source_r25_label=1);});
mutant('source-r25-white-only-failure-rebased-away',f=>f.json('p01-ko-new-prose',q=>q.nonwhite_actual_new_font_native_RGB_errors=0));
mutant('final-native-append-RGB-damage',f=>f.json('both-final-native-append',q=>q.checks[0].all_fullpage_RGB_different_pixels=1));
mutant('final-native-append-proof-substitution',f=>f.json('both-final-native-append',q=>q.checks[0].proof_sha256='0'.repeat(64)));
mutant('actual-damaged-PDF-falsely-accepted',f=>f.json('all9-actual-bad-PDFs',q=>q.actual_bad_PDFs[0].actual_bad_PDF_rejected=false));
mutant('actual-negative-positive-source-rebased',f=>f.json('all9-actual-bad-PDFs',q=>q.actual_bad_PDFs[0].positive_proof_sha256='0'.repeat(64)));
mutant('actual-valid-bad-PDF-transplanted-as-final-proof',f=>{const src=f.bundle.artifacts.find(a=>a.id==='actual-bad-PDF-3'),dst=f.bundle.artifacts.find(a=>a.id==='p03-en-proof'),bytes=raw(src);f.overrides.set(dst.id,bytes);dst.sha256=sha(bytes);dst.bytes=bytes.length;f.bundle.proofs['p03-en']=dst.sha256;});

if(!standalone){
 const registryPath=process.env.CPHO2011_REGISTRY_ITEMS?path.resolve(process.env.CPHO2011_REGISTRY_ITEMS):path.join(repo,'tools/original_style_publication.json');
 const items=JSON.parse(fs.readFileSync(registryPath,'utf8')).filter(i=>i.audit_schema==='cpho2011-theory-original-native-v1').sort((a,b)=>a.language==='ko'?-1:1);assert.equal(items.length,2);
 for(const item of items){const qa=JSON.parse(fs.readFileSync(path.join(repo,item.qa),'utf8'));attempt('actual-publication-frame-'+item.language,()=>assert.equal(helper(repo,qa,item).passed,true));}
 const item=items[0],actualQA=JSON.parse(fs.readFileSync(path.join(repo,item.qa),'utf8'));
 for(const[k,v]of[['schema','legacy'],['status','DRAFT'],['competition','izho'],['year',2010],['kind','TS'],['language','en'],['pages',3],['bytes',1],['sha256','0'.repeat(64)],['source_original_sha256','0'.repeat(64)],['original_math_retyped',true],['original_math_y_changed',true],['translated_point_sizes_fitted',true],['whole_TS21_complete',true],['full_fonts_and_private_Python_bytes_publicly_exported',true],['original_Y_tolerance_pt',.01],['actual_public_raw_payloads',272],['literal_private_raw_input_metadata',55]])attempt('publication-frame-'+k,()=>{const q=JSON.parse(JSON.stringify(actualQA));q[k]=v;helper(repo,q,item);},true);
 attempt('publication-unknown-private-extra-field',()=>{const q=JSON.parse(JSON.stringify(actualQA));q.private_extra_blob='unlisted';helper(repo,q,item);},true);
 attempt('publication-shared-path-traversal',()=>{const q=JSON.parse(JSON.stringify(actualQA));q.shared.contract.path='../'+q.shared.contract.path;helper(repo,q,item);},true);
 attempt('publication-shared-contract-hash-rebase',()=>{const q=JSON.parse(JSON.stringify(actualQA));q.shared.contract.sha256='0'.repeat(64);helper(repo,q,item);},true);
}

const report={kind:'cpho2011-theory-actual-standalone-or-public-coherent-artifact-contract-tests-v1',source_sha256:original.source_sha256,standalone:!!standalone,actual_contract_file_sha256:sha(fs.readFileSync(path.join(root,'source-bound-theory-native-contract.json'))),actual_raw_payload_count:original.raw_payload_count,actual_public_raw_payload_count:original.public_raw_payload_count,literal_private_raw_payloads:original.private_raw_input_fixed_boundary.length,raw_source_paths_never_resolved:true,all_mutations_rebase_declared_artifact_SHA_and_bytes_to_actual_mutated_data:true,cases:results.length,tests:results,all_passed:results.every(r=>r.passed)};
if(process.env.CPHO2011_PUBLIC_RESULT)fs.writeFileSync(process.env.CPHO2011_PUBLIC_RESULT,JSON.stringify(report,null,2)+'\n');
console.log('C11_T_COHERENT_ACTUAL_ARTIFACT_CONTRACT_TESTS',results.length,report.all_passed);if(!report.all_passed)process.exitCode=1;
