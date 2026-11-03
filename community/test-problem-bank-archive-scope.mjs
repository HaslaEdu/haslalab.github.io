import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {createHash,webcrypto} from 'node:crypto';
import {problemBankRoute,problemBankIndexText,PROBLEM_BANK_SEARCH_SCHEMA} from './src/problem-bank.js';
import {BANK_REGISTRY_SCHEMA} from './src/problem-bank-model.js';
import {BANK_SOURCE_ALIASES,BANK_QUESTION_ALIASES} from './src/problem-bank-source-aliases.js';

if(!globalThis.crypto)globalThis.crypto=webcrypto;
const sha=x=>createHash('sha256').update(x).digest('hex');
const sid=x=>'src_'+sha(x),qid=(s,n)=>'q_'+sha(s+'\0'+n);
const schema=readFileSync(new URL('../tools/problem-bank/schema.sql',import.meta.url),'utf8');
const solutionSchema=readFileSync(new URL('../tools/problem-bank/solutions-schema.sql',import.meta.url),'utf8');
class D1 {
  constructor(db){this.db=db;this.calls=[];}
  prepare(sql){const owner=this;return {bind(...args){const prepare=()=>{owner.calls.push({sql,args});return owner.db.prepare(sql);};return {
    async first(){return prepare().get(...args)??null;},async all(){return {results:prepare().all(...args)};},async run(){return prepare().run(...args);}
  };}};}
}
function fixture(t){
  const registry=new DatabaseSync(':memory:'),bank=new DatabaseSync(':memory:'),search=new DatabaseSync(':memory:');
  t.after(()=>{registry.close();bank.close();search.close();});
  bank.exec(schema);bank.exec(solutionSchema);search.exec(PROBLEM_BANK_SEARCH_SCHEMA);registry.exec(BANK_REGISTRY_SCHEMA);
  registry.exec('CREATE TABLE bank_source_routes(source_id TEXT PRIMARY KEY,source_json TEXT,database_name TEXT); CREATE TABLE bank_solution_routes(solution_id TEXT PRIMARY KEY,question_id TEXT,database_name TEXT); CREATE TABLE bank_context_graph_edges(question_id TEXT,target_question_id TEXT,relation TEXT,metadata_json TEXT,proof_json TEXT,updated_at TEXT);');
  const env={BANK_REGISTRY:new D1(registry),BANK2:new D1(bank),BANK_SEARCH:new D1(search)};
  function source(name,kind,collection,{registered=true,database='haslalab-problem-bank-02',id:providedId}={}){
    const id=providedId??sid(name),metadata={id,title:name,subjects:['classical_mechanics'],source_language:'en',page_count:2,level:'undergraduate',expected_question_count:99,extraction_complete:false,catalogue:{kind,discipline:collection,...(kind==='contest'?{competition:'ipho',year:2000}:{})},local_path:'D:/private/secret.pdf',origin:{kind:kind==='course'?'url':'drive',url:'https://private.test/source'}};
    bank.prepare('INSERT INTO book_sources(id,drive_id,revision,title,mime_type,sha256,page_count,subjects_json,level,source_language,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)').run(id,id,'v1',name,'application/pdf',sha(name),2,'["classical_mechanics"]','undergraduate','en','now','now');
    if(registered)registry.prepare('INSERT INTO bank_source_routes VALUES(?,?,?)').run(id,JSON.stringify(metadata),database);
    return {id,kind,collection};
  }
  function question(source,n,collection=source.collection){
    const id=qid(source.id,n),text='A body moves in a gravitational field. Find its energy. '+n;
    bank.prepare('INSERT INTO bank_questions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)').run(id,source.id,n,n,null,'problem','["classical_mechanics"]','undergraduate','[]','pending',sha(id),'now','now');
    bank.prepare('INSERT INTO bank_question_context VALUES(?,?,?,?)').run(id,'en','{}','now');
    for(const [language,value] of [['en',text],['ko','중력장에 있는 물체의 에너지를 구하여라. '+n]]){
      bank.prepare('INSERT INTO bank_question_versions VALUES(?,?,?,?,?,?,?,1,?,?)').run('v_'+sha(id+language),id,language,language==='en'?'original':'translation',value,sha(value),'pending','now','now');
      search.prepare('INSERT INTO bank_search_documents(question_id,source_id,language,text,search_text,text_sha256,subjects_json,locator,original_number,chapter,level,source_title,review_status,unresolved_source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)').run(id,source.id,language,value,problemBankIndexText(value),sha(value),'["classical_mechanics"]',n,n,null,'undergraduate',source.id,'pending',n==='b1'?1:0);
    }
    search.prepare('INSERT INTO bank_question_facets VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)').run(id,source.id,collection,'["classical_mechanics"]',3,'provisional','low','["source_level"]','{"prerequisites":1,"integration":1,"mathematics":1,"reasoning":1}',sha(text),'rubric-v1','{}','now');
    search.prepare('INSERT INTO bank_question_catalogue VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)').run(id,source.id,source.kind,source.kind==='contest'?'ipho':null,null,null,'theory',n,'Title '+n,null,collection,source.id+'/'+n,sha(text),sha('meta'),'now');
    return id;
  }
  const books=source('Physics book','book','physics'),astro=source('Astronomy book','book','astronomy'),school=source('School paper','course','physics'),astroSchool=source('Astro school','course','astronomy'),contest=source('Contest','contest','physics');
  const unregistered=source('Unregistered','book','physics',{registered:false}),bad=source('Invalid binding','book','physics',{database:'untrusted-database'});
  source('Empty retained source','book','physics');
  const qs={b1:question(books,'b1'),b2:question(books,'b2'),mixed:question(books,'mixed','astronomy'),astro:question(astro,'astro'),school:question(school,'school'),astroSchool:question(astroSchool,'astro-school'),contest:question(contest,'contest'),unregistered:question(unregistered,'orphan'),bad:question(bad,'bad')};
  const sol='sol_'+sha('solution');
  bank.prepare('INSERT INTO bank_solution_sources VALUES(?,?,?,?,?,?)').run('ss','{}',sha('pdf'),sha('meta'),'now','now');
  bank.prepare('INSERT INTO bank_solutions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)').run(sol,qs.b1,'{}','b1','ss','s1','worked_solution','source_transcription','[]','{}',sha(sol),'pending',0,'now','now');
  registry.prepare('INSERT INTO bank_solution_routes VALUES(?,?,?)').run(sol,qs.b1,'haslalab-problem-bank-02');
  for(const language of ['en','ko']){const text='Explicit solution '+language;bank.prepare('INSERT INTO bank_solution_versions VALUES(?,?,?,?,?,?,?,1,?,?)').run('sv_'+sha(sol+language),sol,language,language==='en'?'original':'translation',text,sha(text),'pending','now','now');}
  const call=async(path,{method='GET',body,user=null,ocr=()=>assert.fail('OCR must not run')}={})=>{
    const url=new URL('https://bank.test/api/problem-bank'+path),multipart=body instanceof FormData;
    return problemBankRoute(new Request(url,{method,...(body?{body:multipart?body:JSON.stringify(body),headers:multipart?{}:{'Content-Type':'application/json'}}:{})}),env,url,{user,ocr});
  };
  const body=async path=>{const response=await call(path);assert.equal(response.status,200,await response.clone().text());return response.json();};
  const edge=(from,to,label)=>registry.prepare('INSERT INTO bank_context_graph_edges VALUES(?,?,?,?,?,?)').run(from,to,'required_shared_input',JSON.stringify({label}),'{}','now');
  return {registry,bank,search,env,qs,books,astro,school,call,body,edge,question,source};
}
const scope='kind=book&collection=physics';

test('archive status counts actual admitted bilingual questions, not expected source totals or retained rows',async t=>{
  const f=fixture(t);
  for(const [query,questions,sources] of [[scope,2,1],['kind=book&collection=astronomy',2,2],['kind=course&collection=physics',1,1],['kind=course&collection=astronomy',1,1],['kind=contest&collection=physics',1,1],['kind=book',4,2],['collection=astronomy',3,3],['kind=book&collection=chemistry',0,0]]){
    const out=await f.body('/status?'+query);
    assert.equal(out.questions,questions,query);assert.equal(out.language_bodies,questions*2,query);assert.equal(out.sources_registered,sources,query);assert.equal(out.sources_with_documents,sources,query);assert.equal(out.user,null);assert.equal(out.ocr_available,false);
  }
  const physics=await f.body('/status?'+scope);assert.equal(physics.unresolved_questions,1);
  const legacy=await f.body('/status');assert.equal(legacy.questions,9);assert.equal(legacy.language_bodies,18);assert.equal(legacy.sources_registered,7);
  assert.ok(Object.values(f.env).every(db=>db.calls.every(c=>!/^\s*(?:INSERT|UPDATE|DELETE|CREATE|DROP)/i.test(c.sql))));
});

test('source filters apply before keyset pagination and expose actual matched source counts only',async t=>{
  const f=fixture(t),ids=[],counts=new Map();let cursor=null;
  do{
    const out=await f.body('/sources?kind=book&collection=astronomy&source_limit=1'+(cursor?'&after='+cursor:''));
    assert.equal(out.sources.length,1);const source=out.sources[0];ids.push(source.id);counts.set(source.id,source.question_count);
    assert.equal(source.language_bodies,source.question_count*2);assert.equal(source.expected_question_count,99);
    assert.doesNotMatch(JSON.stringify(out),/D:\/private|https:\/\/private|source_json|database_name|proof_json/);
    cursor=out.next_cursor;assert.equal(out.has_more,!!cursor);assert.ok(ids.length<=2);
  }while(cursor);
  assert.deepEqual(ids,[f.books.id,f.astro.id].sort());assert.deepEqual([...counts.values()],[1,1]);
  const physics=await f.body('/sources?'+scope);assert.deepEqual(physics.sources.map(s=>s.id),[f.books.id]);assert.equal(physics.sources[0].question_count,2);
  const empty=await f.body('/sources?kind=course&collection=chemistry');assert.deepEqual(empty.sources,[]);assert.equal(empty.has_more,false);assert.equal(empty.next_cursor,null);
  const legacy=await f.body('/sources');assert.equal(legacy.sources.length,6); // Invalid binding remains excluded.
});

test('detail, explicit solutions and all question subreads reject a foreign category or collection',async t=>{
  const f=fixture(t);
  for(const suffix of ['','/solutions','/context','/recommendations','/feedback']){
    assert.equal((await f.call('/questions/'+f.qs.b1+suffix+'?'+scope+'&lang=en')).status,200,suffix);
    for(const foreign of [f.qs.astro,f.qs.school,f.qs.mixed]){
      const response=await f.call('/questions/'+foreign+suffix+'?'+scope+'&lang=en');assert.equal(response.status,404,suffix);assert.equal((await response.json()).error,'question_not_found');
    }
  }
  const solution=await f.body('/questions/'+f.qs.b1+'/solutions?'+scope+'&lang=en');assert.equal(solution.solutions[0].selected_version.text,'Explicit solution en');
  const detail=await f.body('/questions/'+f.qs.b1+'?'+scope+'&lang=en');assert.doesNotMatch(JSON.stringify(detail),/Explicit solution/);
  assert.equal((await f.call('/questions/'+f.qs.astro+'?lang=en')).status,200); // Old deep-link resolver stays usable.
});

test('scoped graph traversal hides foreign edges and bodies while preserving same-bank cycles',async t=>{
  const f=fixture(t);f.edge(f.qs.b1,f.qs.b2,'same bank');f.edge(f.qs.b1,f.qs.astro,'FOREIGN astronomy label');f.edge(f.qs.b1,f.qs.school,'FOREIGN school label');f.edge(f.qs.b2,f.qs.b1,'cycle');
  const detail=await f.body('/questions/'+f.qs.b1+'?'+scope);assert.deepEqual(detail.question.context_links.map(x=>x.question_id),[f.qs.b2]);
  const out=await f.body('/questions/'+f.qs.b1+'/context?'+scope+'&lang=en');assert.deepEqual(out.contexts.map(x=>x.id),[f.qs.b2]);assert.equal(out.cycles.length,1);assert.equal(out.unavailable_links,2);
  assert.doesNotMatch(JSON.stringify(out),/FOREIGN|Astronomy book|School paper/);
  const legacy=await f.body('/questions/'+f.qs.b1+'/context?lang=en');assert.equal(legacy.contexts.length,3);
});

test('both recommendation pools and the top-level recommendation endpoint retain the requested archive scope',async t=>{
  const f=fixture(t);
  const related=await f.body('/questions/'+f.qs.b1+'/recommendations?'+scope+'&lang=en');assert.deepEqual(related.items.map(x=>x.id),[f.qs.b2]);
  const general=await f.body('/recommendations?'+scope+'&lang=en');assert.ok(general.items.length);assert.ok(general.items.every(x=>[f.qs.b1,f.qs.b2].includes(x.id)));
  const astro=await f.body('/questions/'+f.qs.astro+'/recommendations?kind=book&collection=astronomy&lang=en');assert.deepEqual(astro.items.map(x=>x.id),[f.qs.mixed]);
});

test('scoped read admission fails closed when required additive classification tables are absent',async t=>{
  const f=fixture(t);f.search.exec('DROP TABLE bank_question_catalogue');
  for(const path of ['/status','/sources','/questions/'+f.qs.b1,'/questions/'+f.qs.b1+'/solutions','/questions/'+f.qs.b1+'/context','/questions/'+f.qs.b1+'/recommendations'])assert.equal((await f.call(path+'?'+scope)).status,503,path);
  for(const path of ['/status','/sources','/questions/'+f.qs.b1,'/questions/'+f.qs.b1+'/solutions'])assert.equal((await f.call(path)).status,200,path);
  const byFacet=await f.body('/status?collection=astronomy');assert.equal(byFacet.questions,3);
  f.search.exec('DROP TABLE bank_question_facets');assert.equal((await f.call('/sources?collection=astronomy')).status,503);
});

test('invalid archive scopes are rejected without querying the databases',async t=>{
  const f=fixture(t);
  for(const path of ['/status?kind=school','/sources?collection=astro','/questions/'+f.qs.b1+'?kind=invalid','/sources?kind=book&source_limit=0','/sources?kind=book&after=bad'])assert.equal((await f.call(path)).status,400,path);
  assert.ok(Object.values(f.env).every(db=>db.calls.length===0));
});

test('scoped feedback writes reject foreign questions before any rating or rate-limit mutation',async t=>{
  const f=fixture(t),user={id:9,role:'user'},body={stars:3,outcome:'partial',minutes:12};
  for(const id of [f.qs.astro,f.qs.school,f.qs.mixed])assert.equal((await f.call('/questions/'+id+'/feedback?'+scope,{method:'POST',body,user})).status,404);
  assert.equal(f.registry.prepare('SELECT count(*) AS n FROM bank_question_feedback').get().n,0);assert.equal(f.registry.prepare('SELECT count(*) AS n FROM bank_feedback_limits').get().n,0);
  assert.equal((await f.call('/questions/'+f.qs.b1+'/feedback?'+scope,{method:'POST',body,user})).status,200);
  assert.equal(f.registry.prepare('SELECT count(*) AS n FROM bank_question_feedback').get().n,1);assert.equal(f.registry.prepare('SELECT n FROM bank_feedback_limits WHERE user_id=?').get(user.id).n,1);
  assert.equal((await f.call('/questions/'+f.qs.astro+'/feedback?'+scope,{method:'POST',body})).status,401);
});

test('text identification keeps query scope during EN/KO fallback and preserves body-only legacy filters',async t=>{
  const f=fixture(t),body={text:'A body moves in a gravitational field. Find its energy.',lang:'ko'};
  const response=await f.call('/identify?'+scope,{method:'POST',body});assert.equal(response.status,200);const out=await response.json();
  assert.deepEqual(out.searched_languages,['ko','en']);assert.ok(out.items.length);assert.ok(out.items.every(x=>[f.qs.b1,f.qs.b2].includes(x.id)&&x.source_kind==='book'&&x.collection==='physics'));
  const legacy=await f.call('/identify',{method:'POST',body:{...body,kind:'course',collection:'astronomy'}});assert.equal(legacy.status,200);assert.deepEqual((await legacy.json()).items.map(x=>x.id),[f.qs.astroSchool]);
  const before=Object.values(f.env).reduce((n,db)=>n+db.calls.length,0);
  for(const conflict of [{kind:'course'},{collection:'astronomy'},{kind:''}]){
    const bad=await f.call('/identify?'+scope,{method:'POST',body:{...body,...conflict}});assert.equal(bad.status,400);assert.equal((await bad.json()).error,'archive_scope_mismatch');
  }
  assert.equal(Object.values(f.env).reduce((n,db)=>n+db.calls.length,0),before);
});

test('photo identification rejects a conflicting archive scope before invoking the authorized OCR adapter',async t=>{
  const f=fixture(t),png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aXioAAAAASUVORK5CYII=','base64');let calls=0;
  const form=new FormData();form.set('image',new File([png],'question.png',{type:'image/png'}));form.set('kind','course');
  const response=await f.call('/identify?'+scope,{method:'POST',body:form,user:{id:1,role:'admin'},ocr:()=>{calls++;return 'gravitational field';}});
  assert.equal(response.status,400);assert.equal((await response.json()).error,'archive_scope_mismatch');assert.equal(calls,0);
});

test('source contents expose only scoped chapter metadata in natural order, including unchaptered questions',async t=>{
  const f=fixture(t);
  f.search.prepare('UPDATE bank_search_documents SET chapter=? WHERE question_id=?').run('Chapter 10',f.qs.b1);
  f.search.prepare('UPDATE bank_search_documents SET chapter=? WHERE question_id=?').run('Chapter 2',f.qs.b2);
  const unchaptered=f.question(f.books,'without-chapter');
  const out=await f.body('/sources/'+f.books.id+'/contents?'+scope+'&lang=en');
  assert.equal(out.source_id,f.books.id);assert.equal(out.source.id,f.books.id);assert.equal(out.question_count,3);
  assert.deepEqual(out.chapters,[{chapter:'',title:'Uncategorized',question_count:1},{chapter:'Chapter 2',title:'Chapter 2',question_count:1},{chapter:'Chapter 10',title:'Chapter 10',question_count:1}]);
  assert.doesNotMatch(JSON.stringify(out),/gravitational field|Explicit solution|snippet|selected_version|D:\/private|source_json|database_name/);
  assert.equal((await f.call('/sources/'+f.astro.id+'/contents?'+scope)).status,404);
  assert.equal((await f.call('/sources/'+sid('absent')+'/contents?'+scope)).status,404);
  const loose=await f.body('/search?'+scope+'&source='+f.books.id+'&chapter=&sort=source&lang=en');
  assert.deepEqual(loose.items.map(x=>x.id),[unchaptered]);
});

test('chapter browsing stays bounded and cursor pagination never crosses chapter or bank scope',async t=>{
  const f=fixture(t),ids=[];
  for(let n=1;n<=35;n++){const id=f.question(f.books,'c2-'+n);ids.push(id);f.search.prepare('UPDATE bank_search_documents SET chapter=? WHERE question_id=?').run('2',id);}
  const base='/search?'+scope+'&source='+f.books.id+'&chapter=2&sort=source&limit=20&lang=en';
  const one=await f.body(base);assert.equal(one.items.length,20);assert.equal(one.has_more,true);assert.ok(one.next_cursor);
  const two=await f.body(base+'&cursor='+encodeURIComponent(one.next_cursor));assert.equal(two.items.length,15);assert.equal(two.has_more,false);assert.equal(two.next_cursor,null);
  const seen=[...one.items,...two.items].map(x=>x.id);assert.equal(new Set(seen).size,35);assert.deepEqual([...seen].sort(),ids.sort());assert.ok([...one.items,...two.items].every(x=>x.chapter==='2'&&x.source_id===f.books.id));
  for(const bad of ['/search?chapter=2','/search?source='+f.books.id+'&chapter='+encodeURIComponent('x\u0000y'),'/search?source='+f.books.id+'&chapter='+'a'.repeat(241)]){
    const before=Object.values(f.env).reduce((n,db)=>n+db.calls.length,0);assert.equal((await f.call(bad)).status,400);assert.equal(Object.values(f.env).reduce((n,db)=>n+db.calls.length,0),before);
  }
});

test('detail reuses one schema snapshot per binding and combines admission with the facet read',async t=>{
  const f=fixture(t),out=await f.body('/questions/'+f.qs.b1+'?'+scope+'&lang=en');assert.equal(out.question.id,f.qs.b1);
  const queries=Object.values(f.env).flatMap(db=>db.calls).map(call=>call.sql);
  assert.ok(queries.length<=10,'bounded detail SQL count: '+queries.length);
  assert.equal(f.env.BANK_REGISTRY.calls.filter(call=>call.sql.includes('sqlite_master')).length,1);
  assert.equal(f.env.BANK_SEARCH.calls.filter(call=>call.sql.includes('sqlite_master')).length,1);
  assert.ok(!queries.some(sql=>/^SELECT \* FROM bank_question_facets/.test(sql)));
  assert.doesNotMatch(JSON.stringify(out),/Explicit solution/);
});

test('capability-only status verifies current role without scanning source or question tables',async t=>{
  const f=fixture(t),response=await f.call('/status?capabilities=1',{user:{id:7,role:'admin',nickname:'Admin'},ocr:()=>assert.fail('must not invoke OCR')});
  assert.equal(response.status,200);const out=await response.json();assert.equal(out.user.role,'admin');assert.equal(out.ocr_available,true);assert.equal(out.access,'public');assert.equal(out.questions,undefined);
  assert.ok(Object.values(f.env).every(db=>db.calls.length===0));
  assert.equal((await f.call('/status?capabilities=all')).status,400);assert.ok(Object.values(f.env).every(db=>db.calls.length===0));
});

test('Zangwill editions form one source, hide only duplicate questions and retain geometry and old-only problems',async t=>{
  const f=fixture(t),baseline=await f.body('/status'),[older,current]=Object.entries(BANK_SOURCE_ALIASES)[0];
  const one=f.source('Modern Electrodynamics 2013','book','physics',{id:current}),old=f.source('Modern Electrodynamics 2012','book','physics',{id:older});
  const add=(source,locator,chapter)=>{const id=f.question(source,locator);f.search.prepare('UPDATE bank_search_documents SET chapter=? WHERE question_id=?').run(chapter,id);f.bank.prepare('UPDATE bank_questions SET chapter=? WHERE id=?').run(chapter,id);return id;};
  const original=add(one,'chapter-01/problem-01','1'),oldOriginal=add(old,'chapter-01/problem-01','1');
  const geometry=add(one,'chapter-02/problem-13','2'),oldGeometry=add(old,'chapter-02/problem-13','2');
  const shifted=add(one,'chapter-03/problem-17','3'),oldShifted=add(old,'chapter-03/problem-18','3'),extra=add(old,'chapter-03/problem-17','3');
  assert.equal(BANK_QUESTION_ALIASES[oldOriginal],original);assert.equal(BANK_QUESTION_ALIASES[oldShifted],shifted);assert.equal(BANK_QUESTION_ALIASES[oldGeometry],undefined);assert.equal(BANK_QUESTION_ALIASES[extra],undefined);
  const status=await f.body('/status');assert.equal(status.questions,baseline.questions+5);assert.equal(status.language_bodies,baseline.language_bodies+10);assert.equal(status.sources_registered,baseline.sources_registered+1);assert.equal(status.sources_with_documents,baseline.sources_with_documents+1);
  for(const path of ['/sources','/sources?'+scope]){const out=await f.body(path);assert.equal(out.sources.filter(s=>s.id===current).length,1);assert.equal(out.sources.some(s=>s.id===older),false);assert.deepEqual(out.sources.find(s=>s.id===current).aliases,[older]);}
  const scoped=await f.body('/sources?'+scope);assert.equal(scoped.sources.find(s=>s.id===current).question_count,5);
  for(const id of [current,older]){const out=await f.body('/sources/'+id+'/contents?'+scope+'&lang=en');assert.equal(out.source_id,current);assert.equal(out.question_count,5);assert.deepEqual(out.chapters.map(c=>[c.chapter,c.question_count]),[['1',1],['2',2],['3',2]]);}
  const base='/search?'+scope+'&source='+older+'&sort=source&summary=1&lang=en&limit=2';
  const seen=[];let cursor=null;do{const page=await f.body(base+(cursor?'&cursor='+encodeURIComponent(cursor):''));assert.ok(page.items.length<=2);seen.push(...page.items);cursor=page.next_cursor;}while(cursor);
  assert.deepEqual(seen.map(q=>q.chapter),['1','2','2','3','3']);assert.deepEqual(seen.map(q=>q.id).sort(),[original,geometry,oldGeometry,shifted,extra].sort());assert.ok(seen.every(q=>q.display_source_id===current));
  for(const id of [oldGeometry,extra]){const item=seen.find(q=>q.id===id);assert.equal(item.edition_label,'2012 source');assert.match(item.edition_original_number,/^(?:2\.13|3\.17)$/);const detail=await f.body('/questions/'+id+'?'+scope+'&lang=en');assert.equal(detail.question.display_source_id,current);assert.equal(detail.question.source_id,older);assert.equal(detail.question.canonical_id,undefined);assert.doesNotMatch(JSON.stringify(detail),/Explicit solution/);}
  const legacy=await f.body('/questions/'+oldOriginal+'?'+scope);assert.equal(legacy.question.id,oldOriginal);assert.equal(legacy.question.canonical_id,original);
  f.registry.prepare('DELETE FROM bank_source_routes WHERE source_id=?').run(older);
  const contents=await f.body('/sources/'+current+'/contents?'+scope);assert.equal(contents.question_count,3);
  const remaining=await f.body('/search?'+scope+'&source='+current+'&chapter=3&sort=source&lang=en');assert.deepEqual(remaining.items.map(q=>q.id),[shifted]);
});
