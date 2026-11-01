import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {normalizeImport,sourceId,questionId,applyImport,exportImportSql,sqlLiteral,readInlineAsset} from './store.mjs';

const digest='a'.repeat(64),span={page:2,bbox:[0.1,0.2,0.9,0.8]};
function fixture(){
  const source={drive_id:'drive-file-123',revision:'revision-1',title:'Private sample',mime_type:'application/pdf',sha256:digest,page_count:5,
    subjects:['classical_mechanics'],level:'undergraduate',source_language:'en',expected_question_count:1,extraction_complete:true};
  const question={source:{drive_id:source.drive_id,revision:source.revision},locator:'chapter-1/problem-2',original_number:'2',chapter:'1',spans:[structuredClone(span)],review_status:'verified',
    versions:[{language:'en',role:'original',text:'Find $x$.',review_status:'verified'}],assets:[{asset_id:'figure-1',role:'figure',private_object_key:'sources/private/figure-1.png',mime_type:'image/png',sha256:digest,spans:[structuredClone(span),{page:3,bbox:[0,0.1,1,0.5]}]}]};
  return {manifest:{version:1,sources:[source]},questions:{version:1,questions:[question]},source,question};
}
const db=()=>new DatabaseSync(':memory:');
const row=(database,sql)=>database.prepare(sql).get();

test('source revisions and source/locator question IDs are deterministic and separate',()=>{
  const f=fixture();assert.equal(sourceId(f.source),sourceId({...f.source,title:'renamed'}));assert.notEqual(sourceId(f.source),sourceId({...f.source,revision:'revision-2'}));
  assert.equal(questionId(f.source,f.question.locator),questionId(sourceId(f.source),f.question.locator));assert.notEqual(questionId(f.source,'2'),questionId(f.source,'3'));
});
test('the import plan orders source processing by page count, not byte size or title',()=>{
  const f=fixture(),short={...f.source,drive_id:'another-drive-file',page_count:2,expected_question_count:null,extraction_complete:false};
  const plan=normalizeImport({...f.manifest,sources:[f.source,short]});assert.equal(plan.sources[0].drive_id,short.drive_id);
});
test('replaying an import does not duplicate sources, questions, versions, multi-page figures or jobs',async()=>{
  const f=fixture(),plan=normalizeImport(f.manifest,f.questions),database=db();try{await applyImport(database,plan);await applyImport(database,plan);
    for(const table of ['book_sources','bank_questions','bank_question_versions','bank_assets'])assert.equal(row(database,`SELECT COUNT(*) AS n FROM ${table}`).n,1,table);
    assert.equal(row(database,'SELECT COUNT(*) AS n FROM bank_jobs').n,3);assert.equal(JSON.parse(row(database,'SELECT spans_json FROM bank_assets').spans_json).length,2);
  }finally{database.close();}
});
test('an English original never becomes an invented Korean version or a completed bilingual source',async()=>{
  const f=fixture(),database=db();try{const summary=await applyImport(database,normalizeImport(f.manifest,f.questions));
    assert.equal(row(database,"SELECT COUNT(*) AS n FROM bank_question_versions WHERE language='ko'").n,0);assert.equal(summary[0].ready,0);
    assert.equal(row(database,"SELECT status FROM bank_jobs WHERE stage='translate_ko'").status,'pending');
  }finally{database.close();}
});
test('bilingual readiness requires question review, verified EN and verified KO, and exact declared extraction count',async()=>{
  const f=fixture(),database=db();f.question.versions.push({language:'ko',role:'translation',text:'$x$를 구하여라.',review_status:'pending'});
  try{assert.equal((await applyImport(database,normalizeImport(f.manifest,f.questions)))[0].ready,0);
    f.question.versions[1].review_status='verified';const result=await applyImport(database,normalizeImport(f.manifest,f.questions));assert.equal(result[0].ready,1);assert.equal(result[0].bilingual_verified_questions,1);
  }finally{database.close();}
});
test('an updated pending translation retains its old version but cannot inherit the old verified status',async()=>{
  const f=fixture(),database=db();f.question.versions.push({language:'ko',role:'translation',text:'검수된 번역',review_status:'verified'});
  try{await applyImport(database,normalizeImport(f.manifest,f.questions));f.question.versions[1]={language:'ko',role:'translation',text:'아직 검수하지 않은 수정',review_status:'pending'};
    assert.equal((await applyImport(database,normalizeImport(f.manifest,f.questions)))[0].ready,0);
    const versions=database.prepare("SELECT active,review_status FROM bank_question_versions WHERE language='ko' ORDER BY active").all();
    assert.deepEqual(versions.map(v=>({...v})),[{active:0,review_status:'verified'},{active:1,review_status:'pending'}]);
  }finally{database.close();}
});
test('a stored draft completes translation work while independent review remains pending',async()=>{
  const f=fixture(),database=db();f.question.versions.push({language:'ko',role:'translation',text:'한국어 초안',review_status:'pending'});
  try{assert.equal((await applyImport(database,normalizeImport(f.manifest,f.questions)))[0].ready,0);
    assert.equal(row(database,"SELECT status FROM bank_jobs WHERE stage='translate_ko'").status,'done');
    assert.equal(row(database,"SELECT status FROM bank_jobs WHERE stage='review'").status,'pending');
  }finally{database.close();}
});
test('complete crop snapshots remove obsolete crops for only that question and text updates keep existing images',async()=>{
  const f=fixture(),database=db(),bytes=Buffer.from('private synthetic crop');
  f.question.assets[0].inline_base64=bytes.toString('base64');f.question.assets[0].sha256=createHash('sha256').update(bytes).digest('hex');
  f.question.assets.push({...f.question.assets[0],asset_id:'obsolete-crop'});f.question.assets_complete=true;
  const other=JSON.parse(JSON.stringify(f.question));other.locator='another-question';f.questions.questions.push(other);
  f.source.expected_question_count=2;
  try{await applyImport(database,normalizeImport(f.manifest,f.questions));assert.equal(row(database,'SELECT COUNT(*) n FROM bank_assets').n,4);
    f.question.assets.pop();await applyImport(database,normalizeImport(f.manifest,f.questions));
    assert.equal(row(database,'SELECT COUNT(*) n FROM bank_assets').n,3);
    assert.equal(row(database,'SELECT COUNT(*) n FROM bank_asset_payloads').n,3);
    f.question.assets=[];f.question.assets_complete=false;await applyImport(database,normalizeImport(f.manifest,f.questions));
    assert.equal(row(database,'SELECT COUNT(*) n FROM bank_assets').n,3);
  }finally{database.close();}
});
test('a multilingual compilation retains a question original language and both requested translations',async()=>{
  const f=fixture(),database=db();f.question.source_language='et';
  f.question.versions[0].role='translation';
  f.question.versions.push({language:'et',role:'original',text:'Algne ülesanne',review_status:'verified'},
    {language:'ko',role:'translation',text:'한국어 번역',review_status:'verified'});
  try{const normalized=normalizeImport(f.manifest,f.questions);await applyImport(database,normalized);
    assert.equal(database.prepare('SELECT source_language FROM bank_question_context').get().source_language,'et');
    assert.equal(database.prepare("SELECT language FROM bank_question_versions WHERE role='original'").get().language,'et');
  }finally{database.close();}
});
test('unresolved source flags and review notes survive import and prevent a false ready state',async()=>{
  const f=fixture(),database=db();f.question.versions.push({language:'ko',role:'translation',text:'한국어 번역',review_status:'verified'});
  f.question.context={unresolved_source:true,review_notes:['Source figure still requires review']};
  try{assert.equal((await applyImport(database,normalizeImport(f.manifest,f.questions)))[0].ready,0);
    assert.deepEqual(JSON.parse(database.prepare('SELECT context_json FROM bank_question_context').get().context_json),f.question.context);
    f.question.context.unresolved_source=false;
    assert.equal((await applyImport(database,normalizeImport(f.manifest,f.questions)))[0].ready,1);
  }finally{database.close();}
});
test('invalid pages, boxes, identities, subjects and fake language roles are rejected before writes',()=>{
  for(const mutate of [f=>f.question.spans=[],f=>f.question.spans[0].page=6,f=>f.question.spans[0].bbox=[0.9,0,0.1,1],f=>f.question.spans[0].bbox=[0,0,2,1],
    f=>delete f.source.revision,f=>f.source.subjects=['invented'],f=>f.question.versions[0].language='ko',f=>f.question.assets[0].private_object_key='https://public.example/image.png']){
    const f=fixture();mutate(f);assert.throws(()=>normalizeImport(f.manifest,f.questions));
  }
});
test('conflicting same-revision content rolls back an earlier source insert in the same import',async()=>{
  const f=fixture(),database=db();try{await applyImport(database,normalizeImport(f.manifest,f.questions));
    const other={...f.source,drive_id:'new-short-source',page_count:1,expected_question_count:null,extraction_complete:false};f.source.sha256='b'.repeat(64);
    await assert.rejects(applyImport(database,normalizeImport({...f.manifest,sources:[other,f.source]})),/NOT NULL/);
    assert.equal(row(database,'SELECT COUNT(*) AS n FROM book_sources').n,1);assert.equal(row(database,'SELECT sha256 FROM book_sources').sha256,digest);
  }finally{database.close();}
});
test('a false complete-extraction count fails atomically without overwriting prior metadata',async()=>{
  const f=fixture(),database=db();try{await applyImport(database,normalizeImport(f.manifest,f.questions));f.source.expected_question_count=2;f.source.title='should roll back';
    await assert.rejects(applyImport(database,normalizeImport(f.manifest,f.questions)),/NOT NULL/);assert.equal(row(database,'SELECT title FROM book_sources').title,'Private sample');
  }finally{database.close();}
});
test('D1 SQL export has no explicit transaction and safely quotes hostile source and question text',async()=>{
  const f=fixture(),database=db();f.source.title="O'Brien'); DROP TABLE bank_questions; --";f.question.versions[0].text="A '?' quote: '); DELETE FROM book_sources; --\n한국어 \\frac{1}{2}";
  try{const sql=await exportImportSql(normalizeImport(f.manifest,f.questions));assert.ok(!/^\s*(?:BEGIN|COMMIT)\b/im.test(sql));
    database.exec('PRAGMA foreign_keys=ON; BEGIN IMMEDIATE;');database.exec(sql);database.exec('COMMIT');
    assert.equal(row(database,'SELECT title FROM book_sources').title,f.source.title);assert.equal(row(database,'SELECT text FROM bank_question_versions').text,f.question.versions[0].text);
    assert.equal(sqlLiteral("a'b"),"'a''b'");assert.throws(()=>sqlLiteral(NaN));
  }finally{database.close();}
});
test('SQL import files roll back as a single transaction on a content-hash conflict',async()=>{
  const f=fixture(),database=db();try{await applyImport(database,normalizeImport(f.manifest,f.questions));f.source.sha256='c'.repeat(64);
    const sql=await exportImportSql(normalizeImport(f.manifest,f.questions));database.exec('BEGIN');assert.throws(()=>database.exec(sql),/NOT NULL/);database.exec('ROLLBACK');
    assert.equal(row(database,'SELECT sha256 FROM book_sources').sha256,digest);
  }finally{database.close();}
});
test('CLI writes only a private artifact and refuses content output under the public checkout',async()=>{
  const temp=await mkdtemp(path.join(tmpdir(),'hasla-bank-')),f=fixture(),script=fileURLToPath(new URL('./store.mjs',import.meta.url));
  try{const manifest=path.join(temp,'manifest.json'),questions=path.join(temp,'questions.json'),out=path.join(temp,'private.sql');await writeFile(manifest,JSON.stringify(f.manifest));await writeFile(questions,JSON.stringify(f.questions));
    const run=spawnSync(process.execPath,[script,'--manifest',manifest,'--questions',questions,'--out',out],{encoding:'utf8'});assert.equal(run.status,0,run.stderr);assert.equal(JSON.parse(run.stdout).server_imported,false);assert.ok(!run.stdout.includes('Find $x$'));assert.match(await readFile(out,'utf8'),/PRIVATE QUESTION-BANK IMPORT/);
    const refused=spawnSync(process.execPath,[script,'--manifest',manifest,'--out',fileURLToPath(new URL('./DO-NOT-CREATE.sql',import.meta.url))],{encoding:'utf8'});assert.notEqual(refused.status,0);assert.match(refused.stderr,/public Git checkout/);
  }finally{await rm(temp,{recursive:true,force:true});}
});
test('optional inline crops round-trip in small verified chunks and reject corrupt input or stored bytes',async()=>{
  const f=fixture(),database=db(),bytes=Buffer.alloc(90000,173),asset=f.question.assets[0];asset.sha256=createHash('sha256').update(bytes).digest('hex');asset.inline_base64=bytes.toString('base64');asset.byte_length=bytes.length;delete asset.private_object_key;
  try{const plan=normalizeImport(f.manifest,f.questions);await applyImport(database,plan);const assetId=plan.questions[0].assets[0].id;assert.deepEqual(readInlineAsset(database,assetId),bytes);
    assert.equal(row(database,'SELECT COUNT(*) AS n FROM bank_asset_chunks').n,3);assert.ok(row(database,'SELECT MAX(byte_length) AS n FROM bank_asset_chunks').n<=32768);
    const exported=await exportImportSql(plan);const copy=db();try{copy.exec('PRAGMA foreign_keys=ON; BEGIN');copy.exec(exported);copy.exec('COMMIT');assert.deepEqual(readInlineAsset(copy,assetId),bytes);}finally{copy.close();}
    asset.byte_length++;assert.throws(()=>normalizeImport(f.manifest,f.questions),/byte_length/);asset.byte_length--;asset.sha256=digest;assert.throws(()=>normalizeImport(f.manifest,f.questions),/hash mismatch/);
    database.prepare("UPDATE bank_asset_chunks SET payload=zeroblob(byte_length) WHERE chunk_index=0").run();assert.throws(()=>readInlineAsset(database,assetId),/integrity/);
  }finally{database.close();}
});
