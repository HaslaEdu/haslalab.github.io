import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {createHash,webcrypto} from 'node:crypto';
import {problemBankRoute,problemBankIndexText,PROBLEM_BANK_SEARCH_SCHEMA} from './src/problem-bank.js';
import {BANK_REGISTRY_SCHEMA} from './src/problem-bank-model.js';

if(!globalThis.crypto)globalThis.crypto=webcrypto;
const sha=x=>createHash('sha256').update(x).digest('hex');
const admin={id:1,role:'admin'},member={id:2,role:'user'};
const base='https://library.test/api/problem-bank';
const sid=n=>'src_'+sha('source-'+n),qid=(s,l)=>'q_'+sha(s+'\0'+l);
const S1=sid(1),S2=sid(2),S3=sid(3),Q1=qid(S1,'problem-1'),Q2=qid(S1,'problem-2'),Q3=qid(S2,'problem-3');
const PNG=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aXioAAAAASUVORK5CYII=','base64');
const A1='a_'+sha(Q1+'\0crop-1'),SOL='sol_'+sha('source-answer'),DRAFT='sol_'+sha('original-draft'),SA='sa_'+sha('generated-figure');
const statement='A block of mass 2 kg moves along a rough plane. Find its acceleration.';
const statement20=statement.replace('2 kg','20 kg');
const schema=readFileSync(new URL('../tools/problem-bank/schema.sql',import.meta.url),'utf8');
const solutionSchema=readFileSync(new URL('../tools/problem-bank/solutions-schema.sql',import.meta.url),'utf8');
class D1 {
  constructor(db){this.db=db;this.calls=[];}
  prepare(sql){
    const owner=this;
    return {bind(...args){
      const run=()=>{owner.calls.push({sql,args});return owner.db.prepare(sql);};
      return {async first(){return run().get(...args)??null;},async all(){return {results:run().all(...args)};},async run(){return run().run(...args);}};
    }};
  }
}
function fixture(t){
  const main=new DatabaseSync(':memory:'),b2=new DatabaseSync(':memory:'),b3=new DatabaseSync(':memory:'),index=new DatabaseSync(':memory:');
  t.after(()=>{for(const db of [main,b2,b3,index])db.close();});
  for(const db of [main,b2,b3])db.exec(schema);
  b2.exec(solutionSchema);index.exec(PROBLEM_BANK_SEARCH_SCHEMA);
  main.exec('CREATE TABLE bank_source_routes(source_id TEXT PRIMARY KEY,source_json TEXT,database_name TEXT); CREATE TABLE bank_solution_routes(solution_id TEXT PRIMARY KEY,question_id TEXT,database_name TEXT);');
  main.exec(BANK_REGISTRY_SCHEMA);
  function source(db,id){db.prepare(`INSERT INTO book_sources(id,drive_id,revision,title,mime_type,sha256,page_count,subjects_json,level,source_language,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)`).run(id,id,'v1','Synthetic source','application/pdf',sha('pdf'),2,'["classical_mechanics"]','undergraduate','en','now','now');}
  for(const db of [main,b2,b3])for(const s of [S1,S2,S3])source(db,s);
  for(const [s,name] of [[S1,'haslalab-problem-bank-02'],[S2,'haslalab-problem-bank-03']])main.prepare('INSERT INTO bank_source_routes VALUES(?,?,?)').run(s,JSON.stringify({id:s,title:'Synthetic source',subjects:['classical_mechanics'],page_count:2,level:'undergraduate',source_language:'en',expected_question_count:2,extraction_complete:true,local_path:'D:/private/source.pdf',origin:{url:'https://drive.google.com/private',license_identifier:'Private'}}),name);
  function question(db,id,s,loc,en=statement){
    db.prepare('INSERT INTO bank_questions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)').run(id,s,loc,loc,null,'problem','["classical_mechanics"]','undergraduate','[]','pending',sha(id),'now','now');
    db.prepare('INSERT INTO bank_question_context VALUES(?,?,?,?)').run(id,'en',JSON.stringify({topics:['mechanics'],unresolved_source:true,scientific_review_notes:['Check boundary condition.','Private path D:/private/secret.pdf'],source_author:'Synthetic Author',source_url:'https://drive.google.com/private',local_path:'D:/private/source.pdf',api_key:'topsecret'}),'now');
    for(const [lang,role,text] of [['en','original',en],['ko','translation','질량 2 kg인 물체가 거친 경사면을 움직인다. 가속도를 구하라.']])db.prepare('INSERT INTO bank_question_versions VALUES(?,?,?,?,?,?,?,1,?,?)').run('v_'+sha(id+lang),id,lang,role,text,sha(text),'pending','now','now');
  }
  question(b2,Q1,S1,'problem-1');question(b2,Q2,S1,'problem-2',statement20);question(b3,Q3,S2,'problem-3','A harmonic wave has angular frequency omega. Find its wavelength.');
  question(main,Q1,S1,'problem-1','WRONG RETAINED COPY');
  function doc(id,s,loc,en,lang='en'){
    index.prepare('INSERT INTO bank_search_documents(question_id,source_id,language,text,search_text,text_sha256,subjects_json,locator,original_number,chapter,level,source_title,review_status,unresolved_source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)').run(id,s,lang,en,problemBankIndexText(en),sha(en),'["classical_mechanics"]',loc,loc,null,'undergraduate','Synthetic source','pending',1);
  }
  for(const [id,s,loc,en] of [[Q1,S1,'problem-1',statement],[Q2,S1,'problem-2',statement20],[Q3,S2,'problem-3','A harmonic wave has angular frequency omega. Find its wavelength.']]){
    doc(id,s,loc,en);doc(id,s,loc,'질량 2 kg인 물체의 가속도를 구하라.','ko');
  }
  function questionAsset(db,id=A1,bytes=PNG){
    db.prepare('INSERT INTO bank_assets VALUES(?,?,?,?,?,?,?,?,?,?)').run(id,Q1,'crop-1','question_crop','private-secret-key','image/png',sha(bytes),'[]','now','now');
    db.prepare('INSERT INTO bank_asset_payloads VALUES(?,?,?,?)').run(id,bytes.length,sha(bytes),2);
    for(const [i,p] of [bytes.subarray(0,20),bytes.subarray(20)].entries())db.prepare('INSERT INTO bank_asset_chunks VALUES(?,?,?,?,?)').run(id,i,p.length,sha(p),p);
  }
  questionAsset(b2);questionAsset(main,A1,Buffer.from([...PNG.subarray(0,8),1,2,3,4,5,6,7,8,9,10,11,12,13,14]));
  b2.prepare('INSERT INTO bank_solution_sources VALUES(?,?,?,?,?,?)').run('ss',JSON.stringify({title:'Private source',local_path:'D:/private/sol.pdf'}),sha('source'),sha('meta'),'now','now');
  for(const [id,auth,orig] of [[SOL,'source_transcription','en'],[DRAFT,'haslalab_original_draft','ko']]){
    b2.prepare('INSERT INTO bank_solutions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)').run(id,Q1,'{}','problem-1','ss','solution-'+id,'worked_solution',auth,'[]',JSON.stringify({source_coverage:'partial',missing_subparts:['c'],generated_by:auth==='haslalab_original_draft'?'Codex':null,local_path:'D:/private/source'}),sha(id),'pending',0,'now','now');
    main.prepare('INSERT INTO bank_solution_routes VALUES(?,?,?)').run(id,Q1,'haslalab-problem-bank-02');
    for(const [lang,text] of [['en','A pending solution draft.'],['ko','검토 대기 중인 풀이 초안.']])b2.prepare('INSERT INTO bank_solution_versions VALUES(?,?,?,?,?,?,?,1,?,?)').run('sv_'+sha(id+lang),id,lang,lang===orig?'original':'translation',text,sha(text),'pending','now','now');
  }
  b2.prepare('INSERT INTO bank_solution_assets VALUES(?,?,?,?,?,?,?,?,?,?,?)').run(SA,DRAFT,'figure','figure','image/png',sha(PNG),PNG.length,1,'[]','now','now');
  b2.prepare('INSERT INTO bank_solution_asset_chunks VALUES(?,?,?,?,?)').run(SA,0,PNG.length,sha(PNG),PNG);
  const env={BANK_REGISTRY:new D1(main),BANK2:new D1(b2),BANK3:new D1(b3),BANK_SEARCH:new D1(index)};
  const call=async(path='',{user=admin,ocr,method='GET',body,headers={}}={})=>{
    const req=new Request(base+path,{method,body,headers});
    return problemBankRoute(req,env,new URL(req.url),{user,ocr});
  };
  return {env,main,b2,b3,index,call,doc,question};
}
function contextEdges(f,edges){
  f.main.exec(`CREATE TABLE bank_context_graph_edges(question_id TEXT,target_question_id TEXT,relation TEXT,metadata_json TEXT,proof_json TEXT,updated_at TEXT,PRIMARY KEY(question_id,target_question_id,relation));`);
  for(const {from,to,relation='required_shared_input',metadata={},proof={local_path:'D:/private/proof.pdf',api_key:'topsecret'}} of edges){
    f.main.prepare('INSERT INTO bank_context_graph_edges VALUES(?,?,?,?,?,?)').run(from,to,relation,JSON.stringify(metadata),JSON.stringify(proof),'now');
  }
}
function contextQuestion(f,n){
  const loc='context-'+n,id=qid(S1,loc),text='Canonical context '+n;
  f.question(f.b2,id,S1,loc,text);f.doc(id,S1,loc,text);f.doc(id,S1,loc,'문맥 '+n,'ko');return id;
}
function seedFacet(f,id,source,stars=3,collection='physics',subjects=['classical_mechanics']){
  const basis=f.index.prepare("SELECT text_sha256 FROM bank_search_documents WHERE question_id=? AND language='en'").get(id).text_sha256;
  f.index.prepare('INSERT INTO bank_question_facets VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)').run(id,source,collection,JSON.stringify(subjects),stars,'provisional','low','["source_level"]','{"prerequisites":1,"integration":1,"mathematics":1,"reasoning":1}',basis,'rubric-v1','{}','now');
}

test('guests can browse digital statements and must explicitly request any stored solution',async t=>{
  const f=fixture(t);
  const status=await (await f.call('/status',{user:null,ocr:()=>assert.fail('paid call')})).json();assert.equal(status.access,'public');assert.equal(status.user,null);assert.equal(status.ocr_available,false);
  for(const user of [null,member]){
    const detail=await (await f.call('/questions/'+Q1+'?lang=en',{user})).json();assert.equal(detail.question.selected_version.text,statement);assert.deepEqual(detail.question.assets,[]);assert.equal(detail.question.can_view_source,false);
    assert.doesNotMatch(JSON.stringify(detail),/solution draft|bank_solution|A pending solution/);
    assert.equal((await f.call('/questions/'+Q1+'/solutions?lang=en',{user})).status,200);
    assert.equal((await f.call('/assets/'+A1,{user})).status,403);
  }
});

test('figure policies enforce question, hash and blocked-answer placement before returning bytes',async t=>{
  const f=fixture(t);f.b2.prepare("UPDATE bank_assets SET role='figure' WHERE id=?").run(A1);
  f.main.prepare('INSERT INTO bank_asset_display_policy VALUES(?,?,?,?,?,?,?)').run(A1,Q1,sha(PNG),'inline','source_verified','{}','now');
  let detail=await (await f.call('/questions/'+Q1,{user:null})).json();assert.equal(detail.question.assets[0].placement,'inline');
  assert.deepEqual(Buffer.from(await (await f.call('/assets/'+A1,{user:null})).arrayBuffer()),PNG);
  f.main.prepare("UPDATE bank_asset_display_policy SET placement='blocked'").run();
  detail=await (await f.call('/questions/'+Q1,{user:null})).json();assert.deepEqual(detail.question.assets,[]);
  detail=await (await f.call('/questions/'+Q1)).json();assert.equal(detail.question.assets[0].placement,'source_only');assert.equal((await f.call('/assets/'+A1,{user:null})).status,403);
  f.main.prepare("UPDATE bank_asset_display_policy SET placement='inline',sha256=?").run(sha('wrong'));assert.equal((await f.call('/assets/'+A1,{user:null})).status,403);
  assert.ok(!f.env.BANK2.calls.slice(-8).some(c=>c.sql.includes('bank_asset_chunks')));
  f.main.prepare('UPDATE bank_asset_display_policy SET sha256=?,question_id=?').run(sha(PNG),Q2);
  detail=await (await f.call('/questions/'+Q1,{user:null})).json();assert.deepEqual(detail.question.assets,[]);assert.equal((await f.call('/assets/'+A1,{user:null})).status,403);
});

test('cursor browse reaches every canonical row beyond offset300 without duplicates and filters use facets',async t=>{
  const f=fixture(t);
  for(let n=0;n<315;n++){const loc='browse-'+n,id=qid(S1,loc);f.doc(id,S1,loc,'Synthetic browse row');seedFacet(f,id,S1,1+n%5,n%2?'physics':'astronomy',n%2?['special_relativity']:['general_relativity']);}
  const seen=new Set();let cursor=null;
  for(let page=0;page<20;page++){
    const out=await (await f.call('/search?lang=en&limit=30'+(cursor?'&cursor='+cursor:''),{user:null})).json();
    assert.ok(out.items.length);for(const item of out.items){assert.ok(!seen.has(item.id));seen.add(item.id);}cursor=out.next_cursor;if(!out.has_more)break;assert.ok(cursor);
  }
  assert.equal(seen.size,318);
  const filtered=await (await f.call('/search?lang=en&collection=astronomy&stars=2&subject=general_relativity',{user:null})).json();assert.ok(filtered.items.length);assert.ok(filtered.items.every(i=>i.collection==='astronomy'&&i.stars===2&&i.subjects.includes('general_relativity')));
});
test('admitted figure metadata exposes only bounded safe labels and partial-source flags',async t=>{
  const f=fixture(t);
  for(const [n,label] of [[1,'Fig. 1.16 · input portion only'],[2,'D:/private/source-proof.pdf']])f.main.prepare('INSERT INTO bank_figure_variants VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)').run('f_'+sha('figure'+n),Q1,S1,sha('pdf'),A1,sha(PNG),'[]','figures/'+sha(PNG)+'.png','image/png',sha(PNG),PNG.length,1,1,1,JSON.stringify({figure_label:label,partial_source_figure:true,monochrome:n===1,private_path:'D:/private/secret',api_key:'topsecret'}),'now');
  const detail=await (await f.call('/questions/'+Q1,{user:null})).json();assert.equal(detail.question.figures.length,2);
  assert.ok(detail.question.figures.some(a=>a.figure_label==='Fig. 1.16 · input portion only'));assert.ok(detail.question.figures.some(a=>a.figure_label===null));assert.ok(detail.question.figures.every(a=>a.partial_source_figure===true));
  assert.doesNotMatch(JSON.stringify(detail),/D:\/private|topsecret|private_path|proof_json/);
  assert.equal(detail.question.figures.filter(a=>a.monochrome===true).length,1);
});

test('member feedback upserts one self-report per question without changing difficulty or ratings',async t=>{
  const f=fixture(t);seedFacet(f,Q1,S1,3);
  const post=(body,user=member)=>f.call('/questions/'+Q1+'/feedback',{method:'POST',user,body:JSON.stringify(body),headers:{'Content-Type':'application/json'}});
  assert.equal((await post({stars:2,outcome:'solved'},null)).status,401);
  assert.equal((await post({stars:2,outcome:'solved',evidence:'verified_grade'})).status,400);
  assert.equal((await post({stars:2,outcome:'solved',minutes:10})).status,200);
  assert.equal((await post({stars:4,outcome:'partial',minutes:null})).status,200);
  const summary=await (await f.call('/questions/'+Q1+'/feedback',{user:member})).json();assert.equal(summary.count,1);assert.equal(summary.mean_stars,4);assert.deepEqual(summary.own,{stars:4,outcome:'partial',minutes:null});assert.equal(summary.evidence,'self_report');
  assert.equal((await (await f.call('/questions/'+Q1+'/feedback',{user:null})).json()).own,null);
  assert.equal(f.index.prepare('SELECT stars FROM bank_question_facets WHERE question_id=?').get(Q1).stars,3);
  f.main.prepare('UPDATE bank_feedback_limits SET n=100').run();assert.equal((await post({stars:2,outcome:'solved'})).status,429);
});

test('administrator rubric review requires the current canonical statement hash and full context acknowledgement',async t=>{
  const f=fixture(t);seedFacet(f,Q1,S1,3);
  const rubric={prerequisites:2,integration:2,mathematics:2,reasoning:2},post=(body,user=admin)=>f.call('/questions/'+Q1+'/difficulty-review',{method:'POST',user,body:JSON.stringify(body),headers:{'Content-Type':'application/json'}});
  const body={rubric,basis_text_sha256:sha(statement),all_required_context_read:true};
  assert.equal((await post(body,member)).status,403);assert.equal((await post({...body,all_required_context_read:false})).status,400);assert.equal((await post({...body,basis_text_sha256:sha('stale')})).status,409);
  assert.equal((await post(body)).status,200);assert.equal(f.index.prepare('SELECT difficulty_status FROM bank_question_facets WHERE question_id=?').get(Q1).difficulty_status,'reviewed');
});

test('unrelated paths return null and private auth precedes reading a body or database',async t=>{
  const f=fixture(t);
  assert.equal(await problemBankRoute(new Request('https://x/api/other'),{},new URL('https://x/api/other')),null);
  for(const [user,status] of [[null,401],[member,403]]){
    const req=new Proxy(new Request(base+'/identify',{method:'POST',body:'unread'}),{get(target,key){if(['body','text','json','formData','arrayBuffer'].includes(key))throw Error('body accessed before auth');const v=Reflect.get(target,key,target);return typeof v==='function'?v.bind(target):v;}});
    const res=await problemBankRoute(req,f.env,new URL(req.url),{user,ocr:()=>assert.fail('unauthorized OCR')});
    assert.equal(res.status,status);assert.equal(res.headers.get('cache-control'),'private, no-store');
  }
  assert.equal(Object.values(f.env).reduce((n,db)=>n+db.calls.length,0),0);
});

test('status counts the canonical search corpus once, not retained shard copies',async t=>{
  const f=fixture(t),body=await (await f.call('/status')).json();
  assert.equal(body.questions,3);assert.equal(body.language_bodies,6);assert.equal(body.sources_registered,2);
  assert.equal(body.ocr_available,false);assert.equal(body.publication_ready,false);assert.equal(body.review_status,'pending');
  const enabled=await (await f.call('/status',{ocr:()=>{}})).json();assert.equal(enabled.ocr_available,true);
});

test('sources and detail exclude private origins, paths and secrets, preserving digital roles and flags',async t=>{
  const f=fixture(t),sources=await (await f.call('/sources')).json();
  assert.equal(sources.sources.length,2);assert.doesNotMatch(JSON.stringify(sources),/drive\.google|D:\/private|topsecret/);
  const res=await f.call('/questions/'+Q1+'?lang=en'),body=await res.json();
  assert.equal(res.status,200);assert.equal(body.question.selected_version.text,statement);
  assert.equal(body.question.selected_version.role,'original');assert.equal(body.question.versions.find(v=>v.language==='ko').role,'translation');
  assert.equal(body.question.context.unresolved_source,true);assert.deepEqual(body.question.context.scientific_review_notes,['Check boundary condition.']);
  assert.equal(body.question.assets[0].url,'/api/problem-bank/assets/'+A1);assert.equal(body.publication_ready,false);
  assert.doesNotMatch(JSON.stringify(body),/WRONG RETAINED COPY|private-secret-key|D:\/private|drive\.google|topsecret/);
});

test('unregistered and malformed IDs never resolve through old copies',async t=>{
  const f=fixture(t);assert.equal((await f.call('/questions/not-a-qid')).status,400);
  assert.equal((await f.call('/questions/q_'+sha('absent'))).status,404);
  f.main.prepare('DELETE FROM bank_source_routes WHERE source_id=?').run(S1);
  assert.equal((await f.call('/questions/'+Q1)).status,404);
});

test('missing additive context schema returns empty references without runtime writes',async t=>{
  const f=fixture(t),detail=await (await f.call('/questions/'+Q1)).json();
  assert.deepEqual(detail.question.context_links,[]);
  const res=await f.call('/questions/'+Q1+'/context'),body=await res.json();
  assert.equal(res.status,200);assert.deepEqual(body.contexts,[]);assert.deepEqual(body.cycles,[]);assert.equal(body.truncated,false);
  assert.equal(body.visibility,'public');assert.equal(body.publication_ready,false);
  assert.equal(res.headers.get('cache-control'),'private, no-store');
  const queries=Object.values(f.env).flatMap(db=>db.calls).map(c=>c.sql);
  assert.ok(queries.some(sql=>sql.includes('sqlite_master')&&sql.includes('bank_context_graph_edges')));
  assert.ok(!queries.some(sql=>/FROM bank_context_graph_edges|CREATE|INSERT|UPDATE|DELETE/.test(sql)));
});

test('context links select admitted canonical shards and languages without exposing graph metadata or proofs',async t=>{
  const f=fixture(t);
  contextEdges(f,[{from:Q1,to:Q2,metadata:{label:'Shared setup',question_id:Q3,local_path:'D:/private/input.pdf',api_key:'topsecret'}},
    {from:Q1,to:Q3,metadata:{label:'D:/private/secret.pdf'}},{from:Q3,to:Q1}]);
  const detail=await (await f.call('/questions/'+Q1+'?lang=en')).json();
  assert.deepEqual(new Set(detail.question.context_links.map(x=>x.question_id)),new Set([Q2,Q3]));
  assert.deepEqual(detail.question.context_links.find(x=>x.question_id===Q2),{question_id:Q2,relation:'required_shared_input',label:'Shared setup'});
  assert.equal('label' in detail.question.context_links.find(x=>x.question_id===Q3),false);
  const en=await (await f.call('/questions/'+Q3+'/context?lang=en')).json();
  const canonical=en.contexts.find(x=>x.id===Q1);
  assert.equal(canonical.selected_version.text,statement);assert.equal(canonical.selected_version.language,'en');
  assert.deepEqual(canonical.source,{title:'Synthetic source'});assert.equal(canonical.assets[0].url,'/api/problem-bank/assets/'+A1);
  const ko=await (await f.call('/questions/'+Q1+'/context?lang=ko')).json();
  assert.ok(ko.contexts.every(x=>x.selected_version.language==='ko'&&x.selected_version.role==='translation'));
  assert.doesNotMatch(JSON.stringify({detail,en,ko}),/WRONG RETAINED COPY|private-secret-key|D:\/private|drive\.google|topsecret|proof_json|metadata_json/);
  assert.ok(!f.env.BANK_REGISTRY.calls.some(c=>c.sql.includes('FROM bank_context_graph_edges')&&c.sql.includes('proof_json')));
});

test('context traversal includes the root in visited and reports actual cycles at bounded depth',async t=>{
  const f=fixture(t);contextEdges(f,[{from:Q1,to:Q2},{from:Q2,to:Q1},{from:Q2,to:Q3},{from:Q3,to:Q2}]);
  const body=await (await f.call('/questions/'+Q1+'/context?lang=en')).json();
  assert.deepEqual(body.contexts.map(x=>x.id),[Q2,Q3]);assert.deepEqual(body.contexts.map(x=>x.depth),[1,2]);
  assert.ok(!body.contexts.some(x=>x.id===Q1));assert.ok(body.cycles.length>0);assert.equal(body.truncated,false);
  assert.ok(body.cycles.some(x=>x.from_question_id===Q2&&x.to_question_id===Q1));
  assert.deepEqual(body.contexts.find(x=>x.id===Q3).context_links,[{question_id:Q2,relation:'required_shared_input'}]);
});

test('shared descendants are deduplicated rather than reported as cycles, while sibling cycles are found',async t=>{
  const f=fixture(t),q4=contextQuestion(f,4);
  contextEdges(f,[{from:Q1,to:Q2},{from:Q1,to:Q3},{from:Q2,to:q4},{from:Q3,to:q4}]);
  let body=await (await f.call('/questions/'+Q1+'/context')).json();
  assert.deepEqual(new Set(body.contexts.map(x=>x.id)),new Set([Q2,Q3,q4]));assert.deepEqual(body.cycles,[]);
  assert.equal(body.contexts.filter(x=>x.id===q4).length,1);assert.equal(body.contexts.find(x=>x.id===q4).depth,2);
  f.main.prepare('INSERT INTO bank_context_graph_edges VALUES(?,?,?,?,?,?)').run(Q2,Q3,'required_shared_input','{}','{}','now');
  f.main.prepare('INSERT INTO bank_context_graph_edges VALUES(?,?,?,?,?,?)').run(Q3,Q2,'required_shared_input','{}','{}','now');
  body=await (await f.call('/questions/'+Q1+'/context')).json();assert.ok(body.cycles.length>0);
});

test('context depth and node limits truncate bounded traversal and reject invalid limits before queries',async t=>{
  const f=fixture(t),q4=contextQuestion(f,4);
  contextEdges(f,[{from:Q1,to:Q2},{from:Q2,to:Q3},{from:Q3,to:q4}]);
  let body=await (await f.call('/questions/'+Q1+'/context')).json();
  assert.deepEqual(body.contexts.map(x=>x.id),[Q2,Q3]);assert.equal(body.truncated,true);
  assert.equal(body.depth_limit,2);assert.equal(body.context_limit,8);assert.deepEqual(body.contexts[1].context_links,[]);
  body=await (await f.call('/questions/'+Q1+'/context?depth=1')).json();
  assert.deepEqual(body.contexts.map(x=>x.id),[Q2]);assert.equal(body.truncated,true);
  for(const db of Object.values(f.env))db.calls=[];
  for(const query of ['depth=3','depth=0','depth=-1','depth=nope','limit=9','limit=0','limit=-1'])assert.equal((await f.call('/questions/'+Q1+'/context?'+query)).status,400,query);
  assert.equal(Object.values(f.env).reduce((n,db)=>n+db.calls.length,0),0);
});

test('a context fan-out returns at most eight referenced nodes and never performs unbounded graph reads',async t=>{
  const f=fixture(t),children=Array.from({length:10},(_,i)=>contextQuestion(f,i+10));
  contextEdges(f,children.map(to=>({from:Q1,to})));
  const body=await (await f.call('/questions/'+Q1+'/context')).json();
  assert.equal(body.contexts.length,8);assert.equal(new Set(body.contexts.map(x=>x.id)).size,8);assert.equal(body.truncated,true);
  const queries=f.env.BANK_REGISTRY.calls.filter(c=>c.sql.includes('FROM bank_context_graph_edges'));
  assert.ok(queries.every(c=>c.sql.includes('LIMIT ?')&&c.args.at(-1)===9));
  assert.ok(f.env.BANK_SEARCH.calls.length<=9);
  assert.ok(!Object.values(f.env).flatMap(db=>db.calls).some(c=>/CREATE|INSERT|UPDATE|DELETE/.test(c.sql)));
});

test('invalid, stale and unadmitted graph targets never expose retained copies or target metadata',async t=>{
  const f=fixture(t),absent=qid(S3,'unregistered');f.question(f.b3,absent,S3,'unregistered','Private stale source');f.doc(absent,S3,'unregistered','Private stale source');
  contextEdges(f,[{from:Q3,to:Q1},{from:Q3,to:absent},{from:Q3,to:'not-a-qid'},
    {from:Q3,to:Q2,relation:'D:/private/relation'},{from:Q3,to:qid(S1,'deleted')}]);
  f.main.prepare('DELETE FROM bank_source_routes WHERE source_id=?').run(S1);
  const detail=await (await f.call('/questions/'+Q3)).json();assert.deepEqual(detail.question.context_links,[]);
  const res=await f.call('/questions/'+Q3+'/context'),body=await res.json();
  assert.equal(res.status,200);assert.deepEqual(body.contexts,[]);assert.deepEqual(body.context_links,[]);assert.deepEqual(body.cycles,[]);
  assert.ok(body.unavailable_links>0);assert.doesNotMatch(JSON.stringify(body),new RegExp(Q1+'|'+absent+'|D:/private|Private stale|not-a-qid'));
});

test('guests and members read public context, while corrupt canonical versions fail closed',async t=>{
  const f=fixture(t);contextEdges(f,[{from:Q1,to:Q2}]);
  for(const user of [null,member]){const res=await f.call('/questions/'+Q1+'/context',{user});assert.equal(res.status,200);assert.ok((await res.json()).contexts.every(c=>c.assets.length===0));}
  assert.equal((await f.call('/questions/not-a-qid/context')).status,400);
  f.b2.prepare("UPDATE bank_question_versions SET text='corrupt D:/private/provider-key' WHERE question_id=? AND language='en'").run(Q2);
  const res=await f.call('/questions/'+Q1+'/context'),body=await res.json();
  assert.equal(res.status,503);assert.equal(body.error,'problem_bank_integrity_error');assert.doesNotMatch(JSON.stringify(body),/D:\/private|provider-key|SELECT/);
});

test('search uses escaped FTS terms, exact numeric factors and deterministic ranking',async t=>{
  const f=fixture(t),body=await (await f.call('/search?lang=en&q='+encodeURIComponent('block mass 2 kg'))).json();
  assert.equal(body.items[0].id,Q1);assert.equal(body.items[0].matched_numeric_factors,1);
  assert.ok(body.items[0].score>body.items.find(x=>x.id===Q2).score);
  const odd=await f.call('/search?lang=en&q='+encodeURIComponent('" OR NEAR(block, "* - : ; DROP TABLE bank_questions'));
  assert.equal(odd.status,200);assert.equal(f.b2.prepare('SELECT count(*) n FROM bank_questions').get().n,2);
  const query=f.env.BANK_SEARCH.calls.filter(x=>x.sql.includes(' MATCH ')).at(-1);
  assert.ok(query.sql.includes(' MATCH ?'));assert.ok(!query.sql.includes('DROP TABLE'));assert.match(query.args[0],/^"/);
  assert.equal((await (await f.call('/search?lang=en&q='+encodeURIComponent('block mass 2 kg'))).json()).items[0].id,Q1);
});

test('numeric normalization preserves arbitrarily large adjacent factors and decimal equivalence',()=>{
  assert.notEqual(problemBankIndexText('mass 9007199254740992'),problemBankIndexText('mass 9007199254740993'));
  assert.equal(problemBankIndexText('2.500e3'),problemBankIndexText('2500'));
  assert.notEqual(problemBankIndexText('-2'),problemBankIndexText('2'));
  assert.match(problemBankIndexText('ω'),/omega/);
});

test('bounded quoted Korean prefixes match attached particles and remain syntax safe',async t=>{
  const f=fixture(t),text='기체의 온도를 측정하고 온도를 구하여라.';
  f.index.prepare('UPDATE bank_search_documents SET text=?,search_text=? WHERE question_id=? AND language=?').run(text,problemBankIndexText(text),Q3,'ko');
  const res=await f.call('/search?lang=ko&q='+encodeURIComponent('온도')),body=await res.json();
  assert.equal(res.status,200);assert.equal(body.items[0].id,Q3);assert.ok(body.items[0].score>=5);
  let query=f.env.BANK_SEARCH.calls.filter(x=>x.sql.includes(' MATCH ')).at(-1);assert.equal(query.args[0],'"온도"*');
  const injected=await f.call('/search?lang=ko&q='+encodeURIComponent('온도"* OR NEAR(가속도) : --'));
  assert.equal(injected.status,200);query=f.env.BANK_SEARCH.calls.filter(x=>x.sql.includes(' MATCH ')).at(-1);
  assert.ok(!query.args[0].includes('NEAR('));assert.ok(!query.sql.includes('가속도'));
});

test('FTS triggers remove stale body tokens when the importer updates a version',async t=>{
  const f=fixture(t);
  f.index.prepare('UPDATE bank_search_documents SET text=?,search_text=? WHERE question_id=? AND language=?').run('Unique replacement quasar',problemBankIndexText('Unique replacement quasar'),Q1,'en');
  const out=await (await f.call('/search?lang=en&q=quasar')).json();assert.deepEqual(out.items.map(x=>x.id),[Q1]);
  const old=await (await f.call('/search?lang=en&q=rough')).json();assert.ok(!old.items.some(x=>x.id===Q1));
});

test('query bounds, filters and methods reject invalid requests before querying',async t=>{
  const f=fixture(t);
  for(const path of ['/search?limit=31','/search?offset=301','/search?offset=-1','/search?lang=fr','/search?subject=anything','/search?source=wrong','/search?q='+'x'.repeat(601)])assert.equal((await f.call(path)).status,400,path);
  assert.equal((await f.call('/search',{method:'DELETE'})).status,405);
  assert.equal(Object.values(f.env).reduce((n,db)=>n+db.calls.length,0),0);
  const found=await (await f.call('/search?lang=en&source='+S2+'&subject=classical_mechanics')).json();assert.deepEqual(found.items.map(x=>x.id),[Q3]);
});

test('search excludes stale index sources absent from the canonical registry',async t=>{
  const f=fixture(t),id=qid(S3,'old');f.doc(id,S3,'old','block mass 2 kg');
  const result=await (await f.call('/search?lang=en&q=block')).json();assert.ok(!result.items.some(x=>x.id===id));
});
test('search display names use the canonical presentation while an older derived title is being refreshed',async t=>{
  const f=fixture(t);f.main.prepare('INSERT INTO bank_source_presentations VALUES(?,?,?,?,?,?,?,?,?,?,?)').run(S1,'Published Mechanics','정식 교재명','Published Mechanics · Synthetic Author','Synthetic Author','author',null,'physics',sha('pdf'),'{}','now');
  const out=await (await f.call('/search?lang=en&source='+S1,{user:null})).json();assert.ok(out.items.length);assert.ok(out.items.every(i=>i.source_title==='Published Mechanics · Synthetic Author'));
  assert.equal(f.index.prepare('SELECT source_title FROM bank_search_documents WHERE question_id=? LIMIT 1').get(Q1).source_title,'Synthetic source');
});

test('recommendations use provisional difficulty and exclude input and unresolved candidates',async t=>{
  const f=fixture(t);seedFacet(f,Q1,S1,3);seedFacet(f,Q2,S1,3);f.index.prepare('UPDATE bank_search_documents SET unresolved_source=0 WHERE question_id=?').run(Q2);
  const browse=await (await f.call('/recommendations?lang=en',{user:null})).json();assert.deepEqual(browse.items.map(i=>i.id),[Q2]);
  const body=await (await f.call('/questions/'+Q1+'/recommendations?lang=en')).json();
  assert.equal(body.method,'subject_difficulty_novelty_diversity');assert.ok(body.items.some(x=>x.id===Q2));assert.ok(!body.items.some(x=>x.id===Q1||x.id===Q3));
  f.main.prepare("INSERT INTO bank_question_feedback VALUES(?,?,?,?,?,'self_report',?)").run(Q2,member.id,3,'solved',10,'1999-01-01');
  const rated=await (await f.call('/questions/'+Q1+'/recommendations?lang=en',{user:member})).json();assert.ok(!rated.items.some(x=>x.id===Q2));
});

test('source solutions and original drafts retain distinct authorship, roles and partial coverage',async t=>{
  const f=fixture(t),body=await (await f.call('/questions/'+Q1+'/solutions?lang=ko')).json();
  assert.equal(body.solutions.length,2);
  const source=body.solutions.find(x=>x.id===SOL),draft=body.solutions.find(x=>x.id===DRAFT);
  assert.equal(source.authorship,'source_transcription');assert.equal(source.selected_version.role,'translation');
  assert.equal(draft.authorship,'haslalab_original_draft');assert.equal(draft.selected_version.role,'original');
  assert.equal(source.context.source_coverage,'partial');assert.deepEqual(source.context.missing_subparts,['c']);
  assert.equal(draft.assets[0].role,'figure');assert.equal(source.publication_ready,false);
  assert.doesNotMatch(JSON.stringify(body),/D:\/private|topsecret|drive\.google/);
});

test('question and solution body corruption fails closed',async t=>{
  const f=fixture(t);f.b2.prepare("UPDATE bank_question_versions SET text='corrupt' WHERE question_id=? AND language='en'").run(Q1);
  assert.equal((await f.call('/questions/'+Q1)).status,503);
  f.b2.prepare("UPDATE bank_solution_versions SET text='corrupt' WHERE solution_id=? AND language='en'").run(SOL);
  assert.equal((await f.call('/questions/'+Q1+'/solutions')).status,503);
});

test('canonical image chunk assembly preserves exact bytes, MIME and privacy headers',async t=>{
  const f=fixture(t),res=await f.call('/assets/'+A1);
  assert.equal(res.status,200);assert.deepEqual(Buffer.from(await res.arrayBuffer()),PNG);
  assert.equal(res.headers.get('content-type'),'image/png');assert.equal(res.headers.get('content-length'),String(PNG.length));
  assert.equal(res.headers.get('x-content-type-options'),'nosniff');assert.equal(res.headers.get('cache-control'),'private, no-store');
  const sol=await f.call('/assets/'+SA);assert.equal(sol.status,200);assert.deepEqual(Buffer.from(await sol.arrayBuffer()),PNG);
});

test('missing chunks, corrupt payload and unsupported SVG never return binary content',async t=>{
  const f=fixture(t);
  f.b2.prepare('UPDATE bank_asset_chunks SET payload=? WHERE asset_id=? AND chunk_index=0').run(Buffer.alloc(20),A1);
  let res=await f.call('/assets/'+A1);assert.equal(res.status,503);assert.equal((await res.json()).error,'asset_integrity_error');
  f.b2.prepare("UPDATE bank_assets SET mime_type='image/svg+xml' WHERE id=?").run(A1);
  assert.equal((await f.call('/assets/'+A1)).status,415);
  f.b2.prepare('DELETE FROM bank_solution_asset_chunks WHERE asset_id=?').run(SA);
  assert.equal((await f.call('/assets/'+SA)).status,503);
});

test('text identification is bounded, provider-free and returns candidates without certifying a match',async t=>{
  const f=fixture(t),res=await f.call('/identify',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({text:statement,lang:'en'}),ocr:()=>assert.fail('text path invoked OCR')});
  const body=await res.json();assert.equal(res.status,200);assert.equal(body.candidates[0].id,Q1);assert.equal(body.ocr_used,false);assert.equal(body.automatic_match_confirmed,false);assert.equal(body.recognized_text,statement);
  for(const input of [{text:'x'}, {text:'x'.repeat(12001)}, {text:statement,images:['private']}])assert.equal((await f.call('/identify',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(input)})).status,400);
  assert.equal((await f.call('/identify',{method:'POST',headers:{'content-type':'application/json'},body:'x'.repeat(20001)})).status,413);
});

test('English scan text finds English original even when the UI requests Korean',async t=>{
  const f=fixture(t),res=await f.call('/identify',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({text:'A harmonic wave has angular frequency omega. Find its wavelength.',lang:'ko'})});
  const body=await res.json();assert.equal(res.status,200);assert.equal(body.candidates[0].id,Q3);assert.equal(body.candidates[0].language,'en');assert.equal(body.requested_language,'ko');assert.deepEqual(body.searched_languages,['ko','en']);
});

test('photo identification invokes only the existing authenticated OCR adapter after validation',async t=>{
  const f=fixture(t),form=new FormData();form.set('image',new Blob([PNG],{type:'image/png'}),'scan.png');form.set('lang','en');
  let calls=0;const res=await f.call('/identify',{method:'POST',body:form,ocr:async(image,req)=>{calls++;assert.equal(image.type,'image/png');assert.equal(new URL(req.url).pathname,'/api/problem-bank/identify');return {text:statement,confidence:.93};}});
  const body=await res.json();assert.equal(res.status,200);assert.equal(calls,1);assert.equal(body.ocr_used,true);assert.equal(body.ocr_confidence,.93);assert.equal(body.candidates[0].id,Q1);assert.equal(body.recognized_text,statement);
  assert.equal(f.env.BANK_SEARCH.calls.some(c=>/INSERT|UPDATE|DELETE/.test(c.sql)),false);
});

test('invalid photo/filter and missing adapter prevent paid OCR calls; provider diagnostics are sanitized',async t=>{
  const f=fixture(t);
  const form=(bytes=PNG,type='image/png')=>{const x=new FormData();x.set('image',new Blob([bytes],{type}),'scan');return x;};
  assert.equal((await f.call('/identify',{method:'POST',body:form()})).status,503);
  let calls=0;const ocr=()=>{calls++;throw Object.assign(Error('topsecret D:/private/api-key'),{status:429});};
  assert.equal((await f.call('/identify',{method:'POST',body:form(Buffer.from('bad')),ocr})).status,400);
  const bad=form();bad.set('lang','fr');assert.equal((await f.call('/identify',{method:'POST',body:bad,ocr})).status,400);assert.equal(calls,0);
  const res=await f.call('/identify',{method:'POST',body:form(),ocr});assert.equal(res.status,429);assert.doesNotMatch(await res.text(),/topsecret|private\/api|api-key/);
});

test('unexpected database errors return no SQL or private diagnostics',async()=>{
  const env={BANK_SEARCH:{prepare(){throw Error('SELECT secret FROM D:/private/key');}}};
  const req=new Request(base+'/status'),res=await problemBankRoute(req,env,new URL(req.url),{user:admin});
  assert.equal(res.status,503);assert.equal((await res.json()).error,'problem_bank_unavailable');
});
