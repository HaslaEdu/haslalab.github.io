import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {normalizeImport,sourceId,questionId,applyImport,applyContextTextOverlays,readContextTextOverlays} from './store.mjs';

const sha=s=>createHash('sha256').update(s).digest('hex');
const tool=file=>fileURLToPath(new URL(file,import.meta.url));
function fixture(){
  const source={drive_id:'synthetic-overlay-source',revision:'v1',title:'Synthetic',sha256:'a'.repeat(64),page_count:1,
    subjects:['quantum_mechanics'],level:'undergraduate',source_language:'et'};
  const question={source:{drive_id:source.drive_id,revision:source.revision},locator:'part-1/problem-2',original_number:'2',
    spans:[{page:1,bbox:[0,0,1,1]}],context:{source_image_checked:true,unresolved_source:true},source_language:'et',assets_complete:false,
    versions:[{language:'et',role:'original',text:'Algne küsimus.',review_status:'verified'},
      {language:'en',role:'translation',text:'Find the quantity.',review_status:'verified'},
      {language:'ko',role:'translation',text:'물리량을 구하여라.',review_status:'verified'}],assets:[]};
  const manifest={version:1,sources:[source]},questions={version:1,questions:[question]};
  const overlay={version:1,items:['en','ko'].map(language=>{
    const base=question.versions.find(v=>v.language===language).text,text=base+'\n\n'+(language==='en'?'Given $x=2$.':'주어진 값은 $x=2$이다.');
    return {question_id:questionId(source,question.locator),source_id:sourceId(source),source_sha256:source.sha256,
      locator:question.locator,language,base_text_sha256:sha(base),text_sha256:sha(text),text,review_status:'pending'};
  })};
  return {source,question,manifest,questions,overlay};
}

test('explicit overlays preserve immutable inputs, source identity, assets, roles and a third-language original',()=>{
  const f=fixture(),before=structuredClone(f),result=normalizeImport(f.manifest,f.questions,{contextTextOverlays:f.overlay}),q=result.questions[0];
  assert.deepEqual(f,before);assert.equal(q.id,f.overlay.items[0].question_id);assert.equal(q.source_id,sourceId(f.source));
  assert.equal(q.source_language,'et');assert.equal(q.versions[0].text,'Algne küsimus.');assert.equal(q.versions[0].role,'original');
  assert.equal(q.versions[0].review_status,'verified');
  for(const item of f.overlay.items){const version=q.versions.find(v=>v.language===item.language);assert.equal(version.text,item.text);assert.equal(version.text_sha256,item.text_sha256);assert.equal(version.role,'translation');assert.equal(version.review_status,'pending');}
  assert.deepEqual(q.assets,[]);assert.deepEqual(q.context,f.question.context);assert.equal(q.review_status,'pending');
  assert.equal(normalizeImport(f.manifest,f.questions).questions[0].versions[1].text,'Find the quantity.');
});

test('replaying a frozen draft with the overlay preserves all old SQL versions and activates only recovered text',async()=>{
  const f=fixture(),database=new DatabaseSync(':memory:');
  try{
    await applyImport(database,normalizeImport(f.manifest,f.questions));
    const recovered=normalizeImport(f.manifest,f.questions,{contextTextOverlays:f.overlay});
    await applyImport(database,recovered);await applyImport(database,recovered);
    assert.equal(database.prepare('SELECT count(*) n FROM bank_question_versions').get().n,5);
    assert.equal(database.prepare('SELECT count(*) n FROM bank_question_versions WHERE active=1').get().n,3);
    for(const item of f.overlay.items){
      const current=database.prepare('SELECT text,text_sha256,review_status FROM bank_question_versions WHERE question_id=? AND language=? AND active=1').get(item.question_id,item.language);
      assert.equal(current.text,item.text);assert.equal(current.text_sha256,item.text_sha256);assert.equal(current.review_status,'pending');
      assert.equal(database.prepare('SELECT active FROM bank_question_versions WHERE question_id=? AND language=? AND text_sha256=?').get(item.question_id,item.language,item.base_text_sha256).active,0);
    }
  }finally{database.close();}
});

test('already-applied input is idempotent, including matching context metadata',()=>{
  const f=fixture();for(const item of f.overlay.items)item.context_overlay={unresolved_source:false,review_notes:['Synthetic source correction.']};
  const once=applyContextTextOverlays(f.manifest,f.questions,f.overlay),twice=applyContextTextOverlays(f.manifest,once,f.overlay);
  assert.deepEqual(once,twice);assert.deepEqual(once.questions[0].context,f.overlay.items[0].context_overlay);
  assert.notEqual(once.questions[0].context,f.overlay.items[0].context_overlay);
  const changed=normalizeImport(f.manifest,once);assert.equal(changed.questions[0].context.unresolved_source,false);
});

test('wrong question/source/PDF/base/new hashes and duplicate languages fail before changing input',()=>{
  const mutations=[
    f=>f.overlay.items[0].question_id='q_'+'0'.repeat(64),
    f=>f.overlay.items[0].source_id='src_'+'0'.repeat(64),
    f=>f.overlay.items[0].source_sha256='b'.repeat(64),
    f=>f.overlay.items[0].locator='part-1/problem-other',
    f=>f.overlay.items[0].base_text_sha256='b'.repeat(64),
    f=>f.overlay.items[0].text+=' corrupt',
    f=>f.overlay.items[0].text_sha256='b'.repeat(64),
    f=>f.overlay.items.push(structuredClone(f.overlay.items[0])),
    f=>f.overlay.items[0].review_status='verified',
    f=>f.overlay.items[0].language='fr',
    f=>f.question.versions.push({...f.question.versions[1]}),
    f=>{f.overlay.items[0].context_overlay={unresolved_source:false};f.overlay.items[1].context_overlay={unresolved_source:true};},
    f=>f.overlay.items[0].context_overlay={large:'x'.repeat(20001)},
    f=>f.manifest.sources.push({...f.source,sha256:'b'.repeat(64)}),
  ];
  for(const mutate of mutations){const f=fixture();mutate(f);const before=structuredClone(f);assert.throws(()=>applyContextTextOverlays(f.manifest,f.questions,f.overlay));assert.deepEqual(f,before);}
});

test('scoped imports allow unrelated canonical entries but still check all declared text hashes',()=>{
  const f=fixture(),other=structuredClone(f.overlay.items[0]);other.locator='part-2/problem-20';other.question_id=questionId(other.source_id,other.locator);f.overlay.items.push(other);
  assert.equal(normalizeImport(f.manifest,f.questions,{contextTextOverlays:f.overlay}).questions.length,1);
  other.text+=' tampered';assert.throws(()=>normalizeImport(f.manifest,f.questions,{contextTextOverlays:f.overlay}),/text hash mismatch/);
});

test('a matching canonical ID still requires admission of its exact source revision',()=>{
  const f=fixture();f.manifest.sources=[];
  assert.throws(()=>applyContextTextOverlays(f.manifest,f.questions,f.overlay),/unregistered question source/);
});

test('URL sources use the official canonical identity and exact PDF hash gates',()=>{
  const f=fixture();delete f.source.drive_id;f.source.origin={kind:'url',url:'https://example.edu/course/test.pdf',attribution:'Synthetic source',license_identifier:'CC0-1.0',license_url:'https://example.edu/license'};
  f.source.revision='sha256:'+f.source.sha256;f.question.source={origin:{kind:'url',url:f.source.origin.url},revision:f.source.revision};
  for(const item of f.overlay.items){item.source_id=sourceId(f.source);item.question_id=questionId(f.source,f.question.locator);}
  assert.equal(normalizeImport(f.manifest,f.questions,{contextTextOverlays:f.overlay}).questions[0].id,f.overlay.items[0].question_id);
  f.source.sha256='b'.repeat(64);assert.throws(()=>normalizeImport(f.manifest,f.questions,{contextTextOverlays:f.overlay}),/source PDF hash mismatch/);
});

test('private overlay reader rejects public checkout files and resolves private paths',async()=>{
  const directory=await mkdtemp(path.join(tmpdir(),'hasla-overlay-reader-'));
  try{
    const filename=path.join(directory,'overlays.json');await writeFile(filename,JSON.stringify(fixture().overlay));
    assert.equal((await readContextTextOverlays(filename)).version,1);
    await assert.rejects(readContextTextOverlays(tool('README.md')),/outside the public Git checkout/);
    await assert.rejects(readContextTextOverlays(directory),/explicit private JSON file/);
  }finally{await rm(directory,{recursive:true,force:true});}
});

test('store CLI applies private overlays and an invalid overlay leaves prior output untouched',async()=>{
  const directory=await mkdtemp(path.join(tmpdir(),'hasla-overlay-store-'));
  try{
    const f=fixture(),manifest=path.join(directory,'manifest.json'),questions=path.join(directory,'questions.json'),overlays=path.join(directory,'overlays.json'),out=path.join(directory,'import.sql');
    for(const [filename,value] of [[manifest,f.manifest],[questions,f.questions],[overlays,f.overlay]])await writeFile(filename,JSON.stringify(value));
    const args=[tool('store.mjs'),'--manifest',manifest,'--questions',questions,'--out',out,'--context-text-overlays',overlays];
    const result=spawnSync(process.execPath,args,{encoding:'utf8'});assert.equal(result.status,0,result.stderr);
    const sql=await readFile(out,'utf8');assert.ok(sql.includes(f.overlay.items[0].text));assert.ok(!sql.includes('verified_server_snapshot'));
    f.overlay.items[0].base_text_sha256='b'.repeat(64);await writeFile(overlays,JSON.stringify(f.overlay));
    const failure=spawnSync(process.execPath,args,{encoding:'utf8'});assert.notEqual(failure.status,0);assert.match(failure.stderr,/base text hash mismatch/);
    assert.equal(await readFile(out,'utf8'),sql);
  }finally{await rm(directory,{recursive:true,force:true});}
});

test('routing CLI overlays full copies and rejects stale input before any routed outputs',async()=>{
  const directory=await mkdtemp(path.join(tmpdir(),'hasla-overlay-route-'));
  try{
    const f=fixture(),bytes=Buffer.from('synthetic crop');f.question.assets_complete=true;
    f.question.assets=[{asset_id:'crop',role:'question_crop',mime_type:'image/webp',sha256:sha(bytes),spans:f.question.spans,inline_base64:bytes.toString('base64')}];
    const plan={version:1,registry_database:'haslalab-problem-bank',databases:[{name:'haslalab-problem-bank',id:'00000000-0000-0000-0000-000000000001'}],source_routes:[{source_id:sourceId(f.source),database:'haslalab-problem-bank',question_count:1}]};
    for(const [name,value] of [['manifest',f.manifest],['questions',f.questions],['overlays',f.overlay],['routes',plan]])await writeFile(path.join(directory,name+'.json'),JSON.stringify(value));
    const output=path.join(directory,'routed'),args=[tool('route-import.mjs'),'--manifest',path.join(directory,'manifest.json'),'--questions',path.join(directory,'questions.json'),'--routes',path.join(directory,'routes.json'),'--out-dir',output,'--context-text-overlays',path.join(directory,'overlays.json')];
    let result=spawnSync(process.execPath,args,{encoding:'utf8'});assert.equal(result.status,0,result.stderr);
    const filename=path.join(output,'haslalab-problem-bank.sql'),sql=await readFile(filename,'utf8');assert.ok(sql.includes(f.overlay.items[0].text));
    f.overlay.items[0].text_sha256='b'.repeat(64);await writeFile(path.join(directory,'overlays.json'),JSON.stringify(f.overlay));
    result=spawnSync(process.execPath,args,{encoding:'utf8'});assert.notEqual(result.status,0);assert.equal(await readFile(filename,'utf8'),sql);
  }finally{await rm(directory,{recursive:true,force:true});}
});
