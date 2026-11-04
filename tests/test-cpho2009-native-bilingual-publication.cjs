"use strict";
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(process.env.CPHO2009_PUBLIC_ROOT||path.join(__dirname,'..')),helper=require('./helpers/cpho-2009-source-native-design.cjs'),bridge=require('./helpers/cpho2009-native-bilingual-publication.cjs'),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const items=JSON.parse(fs.readFileSync(path.join(root,'tools/original_style_publication.json'),'utf8')).filter(r=>r.audit_schema==='cpho2009-native-bilingual-original-v1');assert.equal(items.length,4);const qas=items.map(i=>JSON.parse(fs.readFileSync(path.join(root,i.qa),'utf8'))),link=qas[0].source_native_contract,bundle=JSON.parse(bridge.readBound(root,link).toString('utf8')),tests=[],privateIDs=new Set(helper.privateInputIds),privateAttempts=[],records=new Map(link.artifact_bindings.map(a=>[a.id,{...a,actual_path:path.resolve(root,a.path)}]));let maxPublicBuffer=0;
const read=a=>{if(privateIDs.has(a.id)){privateAttempts.push(a.id);throw new Error('No public private-font/program reader');}const r=records.get(a.id);assert.ok(r,a.id);const raw=bridge.readBound(root,r);maxPublicBuffer=Math.max(maxPublicBuffer,raw.length);return raw;};
function pass(name,fn){fn();tests.push({test:name,actual_artifact_bytes_used:true,passed:true});console.log('C09_PUBLIC_LEDGER_TEST',tests.length,name);}
for(let i=0;i<items.length;i++)pass('actual-ledger-'+items[i].file,()=>assert.equal(bridge(root,qas[i],items[i]),true));
const item=bundle.editions[0];function reject(name,edit,reader=read){const b=structuredClone(bundle);edit(b);assert.throws(()=>helper.validateEdition(b,item,{readArtifact:reader}),name);tests.push({test:name,actual_artifact_bytes_used:true,passed:true});console.log('C09_ACTUAL_CONTRACT_TEST',tests.length,name);}
pass('reject-no-actual-ledger-byte-reader',()=>assert.throws(()=>helper.validateEdition(bundle,item),/Resolve actual/));
pass('actual-reader-ignores-every-private-source-path',()=>{const b=structuredClone(bundle);for(const a of b.artifacts)a.source_path='Z:/ignored-detached-source-path';assert.equal(helper.validateEdition(b,item,{readArtifact:read}),true);});
reject('reject-missing-source16',b=>b.classification.TS_source_pages.pop());reject('reject-swapped-language-proof',b=>b.proofs['p01-ko']=b.proofs['p01-en']);reject('reject-new-source-profile',b=>b.original_source_sha256='0'.repeat(64));reject('reject-new-full-edition-pin',b=>b.editions[0].sha256='1'.repeat(64));
function mutant(name,id,edit){const actual=records.get(id);assert.ok(actual);assert.ok(!privateIDs.has(id));const raw=fs.readFileSync(actual.actual_path),data=JSON.parse(raw.toString('utf8'));edit(data);const changed=Buffer.from(JSON.stringify(data));reject(name,b=>{const a=b.artifacts.find(a=>a.id===id);a.sha256=sha(changed);a.bytes=changed.length;},a=>a.id===id?changed:read(a));Object.assign(tests.at(-1),{mutated_actual_artifact:id,artifact_SHA_and_byte_pins_rebased:true,mutated_actual_artifact_sha256:sha(changed)});}
const encoded=r=>r.actual_original_top_level_encoded_CID_states.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0];
mutant('reject-rebased-original-encoded-CID','p01-ko-native',r=>encoded(r).original_encoded_CID_hex='ffff');
mutant('reject-rebased-original-font-resource','p01-ko-native',r=>encoded(r).font_resource='/NotOriginal');
mutant('reject-rebased-source-GID','p01-ko-native',r=>encoded(r).source_glyphs[0].trace_gid++);
mutant('reject-rebased-fractional-Tf','p01-ko-native',r=>encoded(r).original_Tf+=.125);
mutant('reject-rebased-literal-Tm','p01-ko-native',r=>encoded(r).original_literal_Tm[4]+=.25);
mutant('reject-rebased-per-CID-Tm','p01-ko-native',r=>encoded(r).actual_full_per_CID_Tm[4]+=.25);
mutant('reject-rebased-original-ancestor-clip','p01-ko-native',r=>encoded(r).actual_literal_ancestor_clip_programs.push({rect:[0,0,1,1],clip_operator:'W'}));
mutant('reject-rebased-original-Form-programme','p15-ko-native',r=>r.actual_original_active_Form_programmes[0].actual_programme_sha256='3'.repeat(64));
mutant('reject-rebased-fraction-rule-geometry','p15-ko-native',r=>r.actual_original_vector_and_fraction_paints[0].actual.rect[0]+=2);
mutant('reject-rebased-PageGroup-identity','p01-ko-native',r=>{const g=r.source_to_initial_and_final_pageGroup_resources_closure.find(g=>g.stage==='actual_final'&&g.key==='/Group');g.actual['/I']=true;});
mutant('reject-rebased-false-zero-native-RGB','p01-ko-native',r=>r.actual_native_control_nonwhite_RGB_differences=1);
mutant('reject-rebased-false-zero-graphics-RGB','p12-ko-native',r=>r.actual_original_source_image_and_figure_pixel_scopes[0].original_to_final_RGB_changes=1);
mutant('reject-rebased-source-point','p01-ko-prose',r=>r.source_point_paint_baseline_center_gap_rows[0].actual_original_source_point+=.25);
mutant('reject-rebased-source-baseline','p01-ko-prose',r=>r.source_point_paint_baseline_center_gap_rows[0].actual_original_source_baseline+=.25);
mutant('reject-rebased-natural-word-gap','p01-ko-prose',r=>r.source_point_paint_baseline_center_gap_rows[0].regular_word_gap_pt+=1);
mutant('reject-rebased-actual-new-font-programme','p01-ko-prose',r=>r.new_source_role_programmes[0].actual_embedded_programme_sha256='4'.repeat(64));
mutant('reject-rebased-source-physical-stroke','p01-ko-prose',r=>r.source_stroke_programme_controls[0].w*=2);
mutant('reject-rebased-kept-ink-font-closure','p01-ko-kept',r=>r.source_and_known_new_font_resource_closure.push('/UnreviewedFont'));
mutant('reject-rebased-new-over-old-ink','p01-ko-kept',r=>r.actual_original_vs_new_glyph_any_nonwhite_overlap_pixels=1);
mutant('reject-rebased-source-script-relative-motion','p07-ko-scripts',r=>r.closed_original_body_script_base_pairs[0].passed=false);
mutant('reject-rebased-actual-untranslated-Han','p16-ko-Han-coverage',r=>r.actual_final_native_Han.push({c:'能',gid:14125}));
mutant('reject-rebased-original-prose-word-order','p03-en-plan',r=>r.rows[1].en='Changed original condition '+r.rows[1].en);
mutant('reject-rebased-source13-native-zero-GID','source13-closed-original-native0-premotion',r=>r.original_native0[0].trace_gid++);
mutant('reject-rebased-source13-fractional-point','source13-closed-original-native0-premotion',r=>r.original_native0[0].size+=.125);
mutant('reject-rebased-source13-literal-Tf','source13-closed-original-native0-premotion',r=>r.original_Tf+=.125);
mutant('reject-rebased-source13-removed-prose-CID','source13-closed-original-native0-premotion',r=>r.original_source_prose_CID_hex='0861');
mutant('reject-rebased-source13-new-programme','source13-closed-original-native0-premotion',r=>r.new_Form_programme_sha256='5'.repeat(64));
mutant('reject-rebased-source13-false-premotion-zero','source13-closed-original-native0-premotion',r=>r.pre_motion_checks[0].actual_original_native0_RGB_changes=1);
mutant('reject-rebased-source13-false-Poppler-zero','source13-closed-original-native0-premotion',r=>r.Poppler144.changed_pixels_outside_exact_original_prose_ink=1);
mutant('reject-rebased-source13-changed-direct-input','p13-ko-composition',r=>r.actual_direct_native_input_sha256='6'.repeat(64));
mutant('reject-rebased-SimHei-English-nameID6','actual-SimHei-donor-and-subset-name-table',r=>r[1].names[0].text='FakeHei');
mutant('reject-rebased-source-whitespace-nonzero-outline','source-SimSun-GID3-degenerate-programme',r=>r.profiles[0].actual_decomposed_outline_commands[0][1][0][0]=1);
mutant('reject-rebased-source-whitespace-GID','all16-literal-original-whitespace-GID-inventory',r=>r.profiles[2].original_GID=1318);
mutant('reject-rebased-source12-clause-punctuation-GID','p12-ko-plan',r=>r.exact_original_prose_clause_separator_reclassification.exact_original_prose_glyph.trace_gid++);
mutant('reject-rebased-source12-diagram-column','p12-ko-plan',r=>r.rows[4].allowed_horizontal[1]=516);
mutant('reject-rebased-source16-body-tail-erasure','p16-ko-plan',r=>r.rows[1].erase_glyphs=r.rows[1].erase_glyphs.filter(g=>g.source_trace_index!==42));
mutant('reject-rebased-actual-negative-accepted','all13-actual-negative-PDFs',r=>r.actual_unique_bad_PDFs[0].actual_PDF_rejected=false);
mutant('reject-rebased-fake-bar-only-CID-identity','single-bar-all-actual-CID-identity',r=>r.all_actual_glyphs_original_and_new_Fonts_GIDs_CIDs_fractional_points_origins_paints_and_bboxes_exact=false);
mutant('reject-rebased-final-native-RGB','all4-final-native-append',r=>r.editions[0].pages[0].native_MuPDF4x_changed_RGB_pixels=1);
mutant('reject-rebased-final-resource-identity','all4-final-native-append',r=>r.editions[0].pages[0].all_original_and_new_resource_streams_encoded_decoded_and_dictionaries_exact=false);
const privateID=helper.privateInputIds[0];reject('reject-mutated-literal-private-role',b=>b.artifacts.find(a=>a.id===privateID).role='generic-private-exemption');reject('reject-mutated-literal-private-SHA',b=>b.artifacts.find(a=>a.id===privateID).sha256='7'.repeat(64));
for(const id of['original-source',item.file]){const raw=Buffer.from(fs.readFileSync(records.get(id).actual_path));raw[raw.length-17]^=1;reject('reject-actual-one-byte-'+id,()=>{},a=>a.id===id?raw:read(a));reject('reject-rebased-one-byte-'+id,b=>{const a=b.artifacts.find(a=>a.id===id);a.sha256=sha(raw);},a=>a.id===id?raw:read(a));}
assert.deepEqual(privateAttempts,[]);pass('public-reader-never-opens-raw-private-fonts-or-Python',()=>assert.equal(privateAttempts.length,0));

const result={schema:'cpho2009-native-bilingual-original-v1',actual_ledger_root:root,actual_ledger_sha256:sha(fs.readFileSync(path.join(root,'tools/original_style_publication.json'))),actual_contract_sha256:sha(bridge.readBound(root,link)),actual_public_artifact_ids:records.size,private_literal_metadata_ids:privateIDs.size,public_private_raw_reads:privateAttempts.length,maximum_public_buffer_bytes:maxPublicBuffer,maximum_parsed_JSON_cache_input_bytes:helper.maximumParsedJSONCacheInputBytes,tests,all_passed:true};
if(process.env.CPHO2009_PUBLIC_TEST_RESULT){assert.ok(!fs.existsSync(process.env.CPHO2009_PUBLIC_TEST_RESULT));fs.writeFileSync(process.env.CPHO2009_PUBLIC_TEST_RESULT,JSON.stringify(result,null,2)+'\n');}
console.log('C09_ACTUAL_PUBLIC_LEDGER_TESTS_PASS',tests.length,records.size);
