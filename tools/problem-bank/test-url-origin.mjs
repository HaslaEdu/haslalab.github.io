import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';
import {normalizeImport,sourceId,applyImport,exportImportSql} from './store.mjs';
import {expectedSnapshot,verificationSql,verifySnapshot} from './route-import.mjs';

function fixture(){
  const sha256='a'.repeat(64),origin={kind:'url',url:'https://ocw.example.edu/course/problem-set.pdf',
    attribution:'Synthetic author, synthetic course',license_identifier:'CC-BY-NC-SA-4.0',
    license_url:'https://creativecommons.org/licenses/by-nc-sa/4.0/'};
  const source={origin,revision:'sha256:'+sha256,title:'Synthetic URL problem set',sha256,page_count:2,
    subjects:['classical_mechanics'],level:'undergraduate',source_language:'en',expected_question_count:1,extraction_complete:true};
  const bytes=Buffer.from('synthetic private crop'),span={page:1,bbox:[0,0,1,1]};
  const question={source:{origin:{kind:'url',url:origin.url},revision:source.revision},locator:'problem-1',original_number:'1',
    spans:[span],assets_complete:true,versions:[{language:'en',role:'original',text:'Find $x$.'},{language:'ko',role:'translation',text:'$x$를 구하여라.'}],
    assets:[{asset_id:'crop',role:'question_crop',mime_type:'image/webp',sha256:createHash('sha256').update(bytes).digest('hex'),spans:[span],inline_base64:bytes.toString('base64')}]};
  return {source,question,manifest:{version:1,sources:[source]},questions:{version:1,questions:[question]}};
}
test('URL revisions preserve typed provenance and never claim a synthetic Drive ID',async()=>{
  const f=fixture(),normalized=normalizeImport(f.manifest,f.questions),database=new DatabaseSync(':memory:');
  try{
    assert.equal(normalized.sources[0].drive_id,null);
    await applyImport(database,normalized);await applyImport(database,normalized);
    assert.equal(database.prepare('SELECT count(*) n FROM book_sources').get().n,1);
    assert.equal(database.prepare('SELECT count(*) n FROM bank_questions').get().n,1);
    assert.equal(database.prepare('SELECT count(*) n FROM bank_question_versions').get().n,2);
    assert.equal(database.prepare('SELECT drive_id FROM book_sources').get().drive_id,f.source.origin.url);
    const provenance=database.prepare('SELECT origin_json FROM bank_source_origins').all();
    assert.equal(provenance.length,1);assert.deepEqual(JSON.parse(provenance[0].origin_json),f.source.origin);
    assert.equal(database.prepare('SELECT ready FROM bank_source_readiness').get().ready,0);
  }finally{database.close();}
});
test('URL identity ignores PDF page fragments and attribution edits but retains content revisions',()=>{
  const f=fixture(),id=sourceId(f.source);
  assert.equal(sourceId({...f.source,origin:{...f.source.origin,url:f.source.origin.url+'#page=2'}}),id);
  assert.equal(sourceId({...f.source,origin:{...f.source.origin,attribution:'Corrected attribution'}}),id);
  assert.notEqual(sourceId({...f.source,revision:'sha256:'+'b'.repeat(64)}),id);
});
test('archive members keep their real container URL and exact member provenance in storage',async()=>{
  const f=fixture();f.source.origin.url='https://archive.example.edu/course/materials.zip';
  f.source.origin.archive_member={container_sha256:'c'.repeat(64),member_path:'course/PSet01.pdf',member_sha256:f.source.sha256};
  f.question.source.origin.url=f.source.origin.url;
  const second=structuredClone(f.source);second.sha256='b'.repeat(64);second.revision='sha256:'+second.sha256;
  second.origin.archive_member={...second.origin.archive_member,member_path:'course/PSet02.pdf',member_sha256:second.sha256};
  const secondQuestion=structuredClone(f.question);secondQuestion.source.revision=second.revision;
  const normalized=normalizeImport({version:1,sources:[f.source,second]},{version:1,questions:[f.question,secondQuestion]}),database=new DatabaseSync(':memory:');
  try{
    await applyImport(database,normalized);
    const origin=JSON.parse(database.prepare('SELECT origin_json FROM bank_source_origins WHERE source_id=?').get(sourceId(f.source)).origin_json);
    assert.deepEqual(origin,f.source.origin);
    assert.equal(database.prepare('SELECT count(*) n FROM book_sources').get().n,2);
    assert.equal(database.prepare('SELECT count(*) n FROM bank_questions').get().n,2);
    assert.notEqual(sourceId(second),sourceId(f.source));
  }finally{database.close();}
});
test('archive provenance rejects unsafe member paths and unbound content hashes',()=>{
  const changes=[member=>member.member_path='../outside.pdf',member=>member.member_path='/absolute.pdf',
    member=>member.member_path='course\\outside.pdf',member=>member.container_sha256='invalid',member=>member.member_sha256='b'.repeat(64)];
  for(const change of changes){const f=fixture();f.source.origin.archive_member={container_sha256:'c'.repeat(64),member_path:'course/PSet01.pdf',member_sha256:f.source.sha256};change(f.source.origin.archive_member);assert.throws(()=>normalizeImport(f.manifest,f.questions));}
});
test('URL sources reject ambiguous origins, authenticated URL forms and unbound content revisions',()=>{
  const changes=[f=>f.source.drive_id='invented-drive-id',f=>f.source.revision='guessed-date',
    f=>f.source.sha256='b'.repeat(64),f=>f.source.origin.attribution='',f=>delete f.source.origin.license_identifier,
    ...['http://example.edu/problem.pdf','https://user:password@example.edu/problem.pdf','https://example.edu/problem.pdf?token=private','https://example.edu:8443/problem.pdf'].map(url=>f=>f.source.origin.url=url)];
  for(const change of changes){const f=fixture();change(f);assert.throws(()=>normalizeImport(f.manifest,f.questions));}
});
test('adding URL support upgrades a legacy database while preserving Drive IDs and rows',async()=>{
  const f=fixture(),drive={...f.source,drive_id:'drive-file-123',revision:'revision-1',expected_question_count:null,extraction_complete:false};delete drive.origin;
  assert.equal(sourceId(drive),'src_acaaca4cb093385813c6094913094702e3f9c71da260c88662e49eed8968fb95');
  const legacy=normalizeImport({version:1,sources:[drive]}),database=new DatabaseSync(':memory:');
  try{
    await applyImport(database,legacy);const before={...database.prepare('SELECT * FROM book_sources').get()};
    database.exec('DROP TABLE bank_source_origins');
    await applyImport(database,normalizeImport(f.manifest,f.questions));
    assert.deepEqual({...database.prepare('SELECT * FROM book_sources WHERE id=?').get(before.id)},before);
    assert.equal(database.prepare('SELECT count(*) n FROM book_sources').get().n,2);
    assert.equal(database.prepare('SELECT count(*) n FROM bank_source_origins').get().n,1);
  }finally{database.close();}
});
test('SQL export and copy fingerprints cover attribution and license provenance',async()=>{
  const f=fixture(),normalized=normalizeImport(f.manifest,f.questions),database=new DatabaseSync(':memory:');
  try{
    database.exec(await exportImportSql(normalized));
    const expected=expectedSnapshot(normalized,{name:'haslalab-problem-bank-04',id:'00000000-0000-0000-0000-000000000004'});
    const readback=()=>verificationSql(normalized.sources.map(s=>s.id)).split(';').filter(s=>s.trim()).map(sql=>({success:true,results:database.prepare(sql).all()}));
    assert.equal(verifySnapshot(expected,readback()).remote_metadata_verified,true);
    database.prepare('UPDATE bank_source_origins SET origin_json=?').run(JSON.stringify({...f.source.origin,license_identifier:'changed'}));
    assert.throws(()=>verifySnapshot(expected,readback()),/fingerprint mismatch/);
    database.exec('DELETE FROM bank_source_origins');
    assert.throws(()=>verifySnapshot(expected,readback()),/fingerprint mismatch/);
  }finally{database.close();}
});
