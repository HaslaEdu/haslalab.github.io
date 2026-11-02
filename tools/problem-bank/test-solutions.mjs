import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {mkdtemp,readFile,unlink,rmdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {normalizeSolutions,applySolutions,readSolutionAsset,writeSolutionSql} from './solutions.mjs';
const hash=body=>createHash('sha256').update(body).digest('hex');
function fixture(){
 const source={drive_id:'synthetic-book-123',revision:'revision-exact-1',sha256:'a'.repeat(64),title:'Synthetic private book',page_count:12,source_language:'en',subjects:['classical_mechanics'],level:'undergraduate'};
 const reference={drive_id:source.drive_id,revision:source.revision},span={page:7,bbox:[.1,.2,.9,.7]},bytes=Buffer.alloc(70000,42);
 const question={source:reference,locator:'chapter-1/problem-2',original_number:'1.2'};
 const solution={question:{...question,source_sha256:source.sha256},source:reference,locator:'solutions/chapter-1/problem-2',kind:'worked_solution',authorship:'source_transcription',source_image_checked:true,review_status:'pending',publication_ready:false,spans:[span],context:{original_solution_number:'1.2'},versions:[{language:'en',role:'original',text:'Using $F=ma$, the acceleration is $a=F/m$.'},{language:'ko',role:'translation',text:'$F=ma$를 이용하면 가속도는 $a=F/m$이다.'}],assets:[{asset_key:'solution-1',role:'solution_crop',mime_type:'image/webp',sha256:hash(bytes),byte_length:bytes.length,spans:[span],inline_base64:bytes.toString('base64')}]};
 return {source,solution,bytes,input:{version:1,sources:[source],solutions:[solution]},index:{version:1,sources:[source],questions:[question]}};
}
test('solutions link to an exact canonical question while leaving question tables untouched',async()=>{
 const f=fixture(),db=new DatabaseSync(':memory:'),normalized=normalizeSolutions(f.input,f.index);
 try{
  db.exec('CREATE TABLE bank_questions(id TEXT PRIMARY KEY,text TEXT); INSERT INTO bank_questions VALUES(\'sentinel\',\'no answers here\');');
  await applySolutions(db,normalized);await applySolutions(db,normalized);
  assert.deepEqual({...db.prepare('SELECT * FROM bank_questions').get()},{id:'sentinel',text:'no answers here'});
  assert.equal(db.prepare('SELECT count(*) n FROM bank_solutions').get().n,1);
  assert.equal(db.prepare('SELECT count(*) n FROM bank_solution_versions WHERE active=1').get().n,2);
  assert.equal(db.prepare('SELECT publication_ready FROM bank_solutions').get().publication_ready,0);
  assert.deepEqual(readSolutionAsset(db,normalized.solutions[0].assets[0].id),f.bytes);
 }finally{db.close();}
});
test('wrong edition, missing question, changed PDF hash and partial language pairs fail before writes',()=>{
 const changes=[f=>f.solution.question.source.revision='different-edition',f=>f.solution.question.locator='chapter-1/problem-999',f=>f.solution.question.source_sha256='b'.repeat(64),f=>f.solution.question.original_number='1.3',f=>f.solution.versions.pop(),f=>f.solution.source_image_checked=false,f=>f.solution.publication_ready=true,f=>f.solution.review_status='verified'];
 for(const change of changes){const f=fixture();change(f);assert.throws(()=>normalizeSolutions(f.input,f.index));}
});
test('revised solutions retain previous text versions and replace only their own crop snapshot',async()=>{
 const f=fixture(),db=new DatabaseSync(':memory:');
 try{
  const first=normalizeSolutions(f.input,f.index);await applySolutions(db,first);
  f.solution.versions[1].text='외력이 일정하면 $a=F/m$이다.';f.solution.assets[0].asset_key='versioned-crop-2';
  const second=normalizeSolutions(f.input,f.index);await applySolutions(db,second);
  assert.equal(db.prepare('SELECT count(*) n FROM bank_solution_versions').get().n,3);
  assert.equal(db.prepare('SELECT count(*) n FROM bank_solution_versions WHERE active=1').get().n,2);
  assert.equal(db.prepare('SELECT count(*) n FROM bank_solution_assets').get().n,1);
  assert.equal(readSolutionAsset(db,first.solutions[0].assets[0].id),null);
  assert.deepEqual(readSolutionAsset(db,second.solutions[0].assets[0].id),f.bytes);
 }finally{db.close();}
});
test('worked solutions, answer keys, hints and original drafts retain distinct provenance',()=>{
 for(const kind of ['worked_solution','answer_only','hint']){
  const f=fixture();f.solution.kind=kind;const normalized=normalizeSolutions(f.input,f.index);assert.equal(normalized.solutions[0].kind,kind);
 }
 const f=fixture();f.solution.authorship='haslalab_original_draft';assert.throws(()=>normalizeSolutions(f.input,f.index),/authorship/);
 f.solution.context.generated_by='Codex';f.solution.context.source_role='problem_input_for_original_draft';f.solution.source_language='en';f.solution.assets[0].role='source_context';const normalized=normalizeSolutions(f.input,f.index);assert.equal(normalized.solutions[0].authorship,'haslalab_original_draft');assert.equal(normalized.solutions[0].review_status,'pending');
});
test('mixed-language sources preserve the actual original alongside EN and KO translations',()=>{
 const f=fixture();f.solution.source_language='et';f.solution.versions.forEach(v=>v.role='translation');
 assert.throws(()=>normalizeSolutions(f.input,f.index),/original solution language/);
 f.solution.versions.push({language:'et',role:'original',text:'Lahendus: kiirendus on $a=F/m$.'});
 const n=normalizeSolutions(f.input,f.index);assert.equal(n.solutions[0].versions.length,3);assert.equal(n.solutions[0].context.solution_source_language,'et');
});
test('a source answer and a Codex draft coexist under the same input PDF and locator',async()=>{
 const f=fixture(),db=new DatabaseSync(':memory:'),draft=structuredClone(f.solution);
 f.solution.kind='answer_only';draft.authorship='haslalab_original_draft';draft.context={generated_by:'Codex',source_role:'problem_input_for_original_draft'};draft.assets[0].role='source_context';
 draft.versions.forEach(v=>v.role=v.language==='ko'?'original':'translation');
 try{
  const n=normalizeSolutions({...f.input,solutions:[f.solution,draft]},f.index);
  assert.notEqual(n.solutions[0].id,n.solutions[1].id);
  await applySolutions(db,n);await applySolutions(db,n);
  const rows=db.prepare('SELECT authorship,kind,context_json FROM bank_solutions ORDER BY authorship').all();
  assert.equal(rows.length,2);assert.equal(rows.find(r=>r.authorship==='source_transcription').kind,'answer_only');assert.equal(rows.find(r=>r.authorship==='haslalab_original_draft').kind,'worked_solution');
  for(const solution of n.solutions){const roles=db.prepare('SELECT language,role FROM bank_solution_versions WHERE solution_id=? AND active=1 ORDER BY language').all(solution.id);assert.deepEqual(roles.map(r=>[r.language,r.role]),solution.authorship==='source_transcription'?[['en','original'],['ko','translation']]:[['en','translation'],['ko','original']]);}
  draft.assets[0].asset_key='revised-draft-input';const revision=normalizeSolutions({...f.input,solutions:[draft]},f.index);await applySolutions(db,revision);
  assert.deepEqual(readSolutionAsset(db,n.solutions[0].assets[0].id),f.bytes);
  assert.equal(readSolutionAsset(db,n.solutions[1].assets[0].id),null);
  assert.deepEqual(readSolutionAsset(db,revision.solutions[0].assets[0].id),f.bytes);
  assert.equal(db.prepare('SELECT count(*) n FROM bank_solution_assets').get().n,2);
 }finally{db.close();}
});
test('an original-language correction preserves old roles and deactivates omitted languages',async()=>{
 const f=fixture(),db=new DatabaseSync(':memory:'),estonian=structuredClone(f.input);
 estonian.solutions[0].source_language='et';estonian.solutions[0].versions.forEach(v=>v.role='translation');estonian.solutions[0].versions.push({language:'et',role:'original',text:'Lahendus.'});
 try{
  const before=normalizeSolutions(estonian,f.index),after=normalizeSolutions(f.input,f.index);assert.equal(before.solutions[0].id,after.solutions[0].id);
  await applySolutions(db,before);await applySolutions(db,after);
  const active=db.prepare('SELECT language,role FROM bank_solution_versions WHERE active=1 ORDER BY language').all();assert.deepEqual(active.map(r=>[r.language,r.role]),[['en','original'],['ko','translation']]);
  const history=db.prepare('SELECT language,role,active FROM bank_solution_versions').all();assert.equal(history.length,4);assert.equal(history.find(r=>r.language==='et').active,0);assert.equal(history.find(r=>r.language==='en'&&r.role==='translation').active,0);
 }finally{db.close();}
});
test('an original draft may be Korean even when its input PDF is Estonian',()=>{
 const f=fixture();f.source.source_language='et';f.solution.authorship='haslalab_original_draft';f.solution.context={generated_by:'Codex',source_role:'problem_input_for_original_draft'};f.solution.assets[0].role='source_context';
 f.solution.versions.forEach(v=>v.role=v.language==='ko'?'original':'translation');
 const n=normalizeSolutions(f.input,f.index);assert.equal(n.solutions[0].context.solution_source_language,'ko');assert.equal(n.solutions[0].versions.length,2);assert.equal(n.sources[0].source_language,'et');
});
test('changing the authorship under a preexisting normalized ID rolls back',async()=>{
 const f=fixture(),db=new DatabaseSync(':memory:'),n=normalizeSolutions(f.input,f.index);
 try{
  await applySolutions(db,n);const forged=structuredClone(n);forged.solutions[0].authorship='haslalab_original_draft';
  await assert.rejects(applySolutions(db,forged),/NOT NULL/);
  assert.equal(db.prepare('SELECT authorship FROM bank_solutions').get().authorship,'source_transcription');
 }finally{db.close();}
});
test('private exported SQL round-trips text, roles and all crop chunks',async()=>{
 const f=fixture(),db=new DatabaseSync(':memory:'),directory=await mkdtemp(join(tmpdir(),'haslalab-solutions-export-')),target=join(directory,'synthetic-solutions.sql');
 f.solution.versions[0].text="A quoted 'answer' with $F=ma$ and a literal question mark?";
 try{
  const n=normalizeSolutions(f.input,f.index);await writeSolutionSql(n,target);db.exec(await readFile(target,'utf8'));
  assert.equal(db.prepare("SELECT text FROM bank_solution_versions WHERE language='en' AND active=1").get().text,f.solution.versions[0].text);
  assert.deepEqual(readSolutionAsset(db,n.solutions[0].assets[0].id),f.bytes);
  assert.equal(db.prepare('SELECT publication_ready FROM bank_solutions').get().publication_ready,0);
 }finally{db.close();await unlink(target).catch(()=>{});await rmdir(directory);}
});
test('changing bytes under an existing source revision rolls back the whole solution import',async()=>{
 const f=fixture(),db=new DatabaseSync(':memory:');
 try{
  await applySolutions(db,normalizeSolutions(f.input,f.index));const changed=structuredClone(f.input);changed.sources[0].sha256='b'.repeat(64);changed.solutions[0].versions[1].text='This must not be stored.';
  await assert.rejects(applySolutions(db,normalizeSolutions(changed,f.index)),/NOT NULL/);
  assert.equal(db.prepare('SELECT count(*) n FROM bank_solution_versions').get().n,2);
  assert.equal(db.prepare('SELECT source_sha256 FROM bank_solution_sources').get().source_sha256,'a'.repeat(64));
 }finally{db.close();}
});
test('source bounds and corrupt or duplicate crop bytes cannot enter solution storage',()=>{
 const changes=[f=>f.solution.spans[0].page=13,f=>f.solution.spans[0].bbox=[0,0,0,1],f=>f.solution.assets[0].sha256='c'.repeat(64),f=>f.solution.assets[0].byte_length=2,f=>f.solution.assets.push(structuredClone(f.solution.assets[0]))];
 for(const change of changes){const f=fixture();change(f);assert.throws(()=>normalizeSolutions(f.input,f.index));}
});
test('stored solution bytes are checked against chunk and aggregate hashes',async()=>{
 const f=fixture(),db=new DatabaseSync(':memory:'),n=normalizeSolutions(f.input,f.index);
 try{
  await applySolutions(db,n);db.prepare('UPDATE bank_solution_asset_chunks SET payload=zeroblob(byte_length) WHERE chunk_index=1').run();
  assert.throws(()=>readSolutionAsset(db,n.solutions[0].assets[0].id),/integrity/);
 }finally{db.close();}
});
test('private solution exports reject the public checkout',async()=>{
 const f=fixture();await assert.rejects(writeSolutionSql(normalizeSolutions(f.input,f.index),fileURLToPath(new URL('./must-not-create.sql',import.meta.url))),/private content/);
});
