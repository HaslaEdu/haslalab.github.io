import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Synthetic metadata only. No statements from the private corpus belong here.
const src=(n,extra={})=>({id:'src_'+String(n).repeat(64),title:'Source '+n,...extra});
const sources=[src(1,{kind:'book',collection:'physics'}),src(2,{kind:'course',collection:'physics'}),src(3,{kind:'contest',competition:'example',year:2024,collection:'physics'}),src(4,{kind:'contest',competition:'example',year:2025,collection:'physics'}),src(5,{kind:'book',collection:'astronomy'})];
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function browser(){
  const nodes=new Map(),calls=[];
  class Element{
    constructor(){this.value='';this.hidden=false;this.disabled=false;this.dataset={};this.isConnected=true;this.listeners={};this.attributes={};this.children=[];this.selectors=new Map();this.style={};this.classList={toggle(){},add(){},remove(){}};}
    set innerHTML(value){this.html=String(value);this.children=[];}get innerHTML(){return this.html||'';}
    set textContent(value){this.text=String(value);this.html='';this.children=[];}get textContent(){return this.text||'';}
    addEventListener(name,callback){this.listeners[name]=callback;}setAttribute(name,value){this.attributes[name]=value;}
    querySelector(selector){if(!this.selectors.has(selector))this.selectors.set(selector,new Element());return this.selectors.get(selector);}querySelectorAll(){return [];}
    reset(){}append(child){this.children.push(child);}focus(){}getBoundingClientRect(){return {height:600};}
  }
  const node=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);},storage={getItem(){return '';},setItem(){},removeItem(){}};
  const sandbox={console,URL,URLSearchParams,AbortController,DOMException,FormData,Blob,Set,Map,Number,String,Object,Promise,localStorage:storage,sessionStorage:storage,matchMedia:()=>({matches:false}),window:{location:new URL('https://library.test/'),parent:null,addEventListener(){},history:{replaceState(_state,_title,url){sandbox.window.location=new URL(url);}}},document:{documentElement:{dataset:{}},body:node('body'),getElementById:node,querySelector:()=>node('main'),querySelectorAll:()=>[],createElement:()=>new Element()},fetch:(path,opts)=>new Promise((resolve,reject)=>calls.push({path,opts,resolve,reject}))};
  vm.createContext(sandbox);const code=readFileSync(new URL('./public/app.js',import.meta.url),'utf8').replace(/restoreSession\(\);\s*$/,'');
  vm.runInContext(code+'\nglobalThis.ui={state,params,orderedSources,loadSources,renderSources,renderSourceList,sourceMatches,chooseKind,renderResults,search,identify,changePage,selectQuestion,closeQuestion,showSolutions,showRecommendations,signOut};',sandbox);
  return {...sandbox.ui,node,calls,window:sandbox.window};
}
function question(id='q_test'){return {question:{id,source_id:sources[0].id,source:sources[0],original_number:'2.1',selected_version:{text:'A synthetic body with $x=2$.'},subjects:[],context:{},assets:[]}};}

test('archive HTML has unique stable controls, real labels and a collapsed reading view',()=>{
  const html=readFileSync(new URL('./public/index.html',import.meta.url),'utf8'),ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);
  assert.equal(new Set(ids).size,ids.length);
  for(const id of ['kindNav','sourceList','competition','year','type','catalogView','readerView','backToList','accountLogin'])assert(ids.includes(id));
  assert.match(html,/id="readerView"[^>]*hidden/);
  assert.equal((html.match(/<option\b/g)||[]).length,(html.match(/<\/option>/g)||[]).length);
  assert(!html.includes('q_'+ '1'.repeat(64)));
});
test('source navigation never guesses kinds or invents corpus counts from titles',()=>{
  const b=browser();b.state.sources=[src(1,{title:'IPhO 2026 book-looking filename',expected_question_count:999})];b.renderSources();
  assert.match(b.node('sourceList').innerHTML,/IPhO 2026/);assert.doesNotMatch(b.node('sourceList').innerHTML,/999/);
  b.state.kind='contest';b.renderSources();assert.doesNotMatch(b.node('sourceList').innerHTML,/IPhO 2026/);
  assert.match(b.node('sourceList').innerHTML,/조건에 맞는 자료/);
});
test('the complete source directory and dropdown share natural kind, competition, year and title ordering',()=>{
  const b=browser(),list=[src(1,{kind:'book',title:'Book 10'}),src(2,{kind:'book',title:'Book 2'}),src(3,{kind:'contest',competition:'zeta',year:2025}),src(4,{kind:'contest',competition:'alpha',year:2024}),src(5,{kind:'contest',competition:'alpha',year:2025}),src(6,{kind:'course',title:'Course'})];b.state.sources=list;b.renderSources();
  const ids=Array.from(b.orderedSources(list),s=>s.id);assert.deepEqual(ids,[list[4].id,list[3].id,list[2].id,list[1].id,list[0].id,list[5].id]);
  const menu=Array.from(b.node('source').innerHTML.matchAll(/value="(src_[a-f0-9]+)"/g),x=>x[1]),rail=Array.from(b.node('sourceList').innerHTML.matchAll(/data-source="(src_[a-f0-9]+)"/g),x=>x[1]);assert.deepEqual(menu,ids);assert.deepEqual(rail,ids);
});
test('source metadata follows all bounded pages, deduplicates IDs and remains compatible with legacy responses',async()=>{
  const b=browser(),done=b.loadSources();assert.equal(b.calls[0].path,'/api/problem-bank/sources');b.calls[0].resolve(Response.json({sources:[sources[0],sources[1]],has_more:true,next_cursor:sources[1].id}));await tick();
  const second=new URL(b.calls[1].path,'https://library.test');assert.equal(second.searchParams.get('after'),sources[1].id);assert.equal(second.searchParams.get('source_limit'),'200');b.calls[1].resolve(Response.json({sources:[sources[1],sources[2]],has_more:false}));const result=await done;assert.equal(result.length,3);assert.equal(new Set(result.map(s=>s.id)).size,3);
  const legacy=b.loadSources();b.calls[2].resolve(Response.json({sources:[sources[0]]}));assert.equal((await legacy).length,1);assert.equal(b.calls.length,3);
});
test('source pagination rejects repeated or invalid cursors and stale sessions before publishing data',async()=>{
  const b=browser(),done=b.loadSources();b.calls[0].resolve(Response.json({sources:[],has_more:true,next_cursor:sources[0].id}));await tick();b.calls[1].resolve(Response.json({sources:[],has_more:true,next_cursor:sources[0].id}));await assert.rejects(done,/Invalid source pagination/);
  const invalid=b.loadSources();b.calls[2].resolve(Response.json({sources:[],has_more:true,next_cursor:'https://evil.test'}));await assert.rejects(invalid,/Invalid source pagination/);
  let current=true;const stale=b.loadSources(()=>current);current=false;b.calls[3].resolve(Response.json({sources:[sources[0]],has_more:true,next_cursor:sources[0].id}));await assert.rejects(stale,error=>error.name==='AbortError');assert.equal(b.calls.length,4);
});
test('source loading has a hard page bound even when every returned cursor is new',async()=>{
  const b=browser(),done=b.loadSources();for(let page=0;page<100;page++){const call=b.calls[page];assert(call);call.resolve(Response.json({sources:[],has_more:true,next_cursor:'src_'+(page+1).toString(16).padStart(64,'0')}));if(page<99)await tick();}await assert.rejects(done,/Invalid source pagination/);assert.equal(b.calls.length,100);
});
test('identification retains contest filters in JSON and multipart without browse cursors or sort options',async()=>{
  for(const photo of [false,true]){const b=browser();b.state.kind='contest';b.state.ocrAvailable=photo;b.state.cursor='sc_synthetic';b.node('competition').value='example';b.node('year').value='2025';b.node('type').value='theory';b.node('source').value=sources[3].id;b.node('query').value='';
    const done=b.identify(photo?null:'Synthetic identification text',photo?new Blob(['synthetic'],{type:'image/png'}):null),body=photo?Object.fromEntries(b.calls[0].opts.body.entries()):JSON.parse(b.calls[0].opts.body);
    for(const [key,value] of Object.entries({kind:'contest',competition:'example',year:'2025',type:'theory'}))assert.equal(body[key],value);for(const key of ['sort','cursor','offset'])assert.equal(Object.hasOwn(body,key),false);
    b.calls[0].resolve(Response.json({candidates:[]}));await done;
  }
});
test('book and course browsing use explicit kinds and preserve collection/source filters',()=>{
  const b=browser();b.state.sources=sources;b.state.kind='book';b.node('collection').value='astronomy';b.node('source').value=sources[4].id;b.renderSources();
  assert.equal(b.node('source').value,sources[4].id);assert.match(b.node('sourceList').innerHTML,/Source 5/);assert.doesNotMatch(b.node('sourceList').innerHTML,/Source [1234]/);
  b.state.kind='course';b.node('collection').value='physics';b.renderSources();assert.equal(b.node('source').value,'');assert.match(b.node('sourceList').innerHTML,/Source 2/);assert.doesNotMatch(b.node('sourceList').innerHTML,/Source [1345]/);
});
test('competition and year navigation derives only returned metadata and sends the exact filter contract',()=>{
  const b=browser();b.state.sources=sources;b.state.kind='contest';b.node('competition').value='example';b.node('year').value='2024';b.node('type').value='theory';b.node('stars').value='3';b.renderSources();
  assert.equal(b.node('contestFilters').hidden,false);assert.match(b.node('yearNav').innerHTML,/data-year="2024"/);assert.match(b.node('yearNav').innerHTML,/data-year="2025"/);assert.doesNotMatch(b.node('yearNav').innerHTML,/2026/);
  assert.match(b.node('sourceList').innerHTML,/Source 3/);assert.doesNotMatch(b.node('sourceList').innerHTML,/Source 4/);
  const params=b.params();assert.equal(params.get('kind'),'contest');assert.equal(params.get('competition'),'example');assert.equal(params.get('year'),'2024');assert.equal(params.get('type'),'theory');assert.equal(params.get('stars'),'3');
});
test('switching source kind resets incompatible paper filters and retains the selected discipline',async()=>{
  const b=browser();b.state.sources=sources;b.node('source').value=sources[2].id;b.node('collection').value='physics';for(const key of ['competition','year','type'])b.node(key).value='old';
  assert.equal(b.chooseKind('invalid'),undefined);assert.equal(b.calls.length,0);
  const done=b.chooseKind('book');assert.equal(b.state.kind,'book');for(const key of ['source','competition','year','type'])assert.equal(b.node(key).value,'');assert.equal(b.node('collection').value,'physics');
  assert.equal(new URL(b.calls[0].path,'https://library.test').searchParams.get('kind'),'book');b.calls[0].resolve(Response.json({items:[],has_more:false}));await done;
});
test('only actual added disciplines extend the collection menu, and their subject labels are readable',()=>{
  const b=browser();b.state.sources=[...sources,src(6,{kind:'contest',competition:'example-chemistry',collection:'chemistry'})];b.renderSources();
  assert.match(b.node('collection').innerHTML,/<option value="chemistry">화학<\/option>/);assert.doesNotMatch(b.node('collection').innerHTML,/value="biology"/);
  b.node('collection').value='chemistry';b.renderSources();assert.equal(b.node('collection').value,'chemistry');assert.match(b.node('sourceList').innerHTML,/Source 6/);assert.doesNotMatch(b.node('sourceList').innerHTML,/Source [12345]/);
  assert.match(b.node('subject').innerHTML,/일반상대론/);assert.match(b.node('subject').innerHTML,/지구과학/);
});
test('source browsing preserves an opaque server cursor across pages while text search retains ranked order',async()=>{
  const b=browser();b.node('source').value=sources[0].id;const first=b.search(true);assert.equal(new URL(b.calls[0].path,'https://library.test').searchParams.get('sort'),'source');
  const opaque='sc_example.opaque+cursor/with=encoded-data';b.calls[0].resolve(Response.json({items:[{id:'q_first',original_number:'1',source_title:'Synthetic',snippet:'Text'}],has_more:true,next_cursor:opaque}));await first;
  assert.equal(b.state.nextCursor,opaque);const second=b.changePage(1),query=new URL(b.calls[1].path,'https://library.test').searchParams;assert.equal(query.get('cursor'),opaque);assert.equal(query.get('sort'),'source');b.calls[1].resolve(Response.json({items:[],has_more:false}));await second;
  b.node('query').value='energy';assert.equal(b.params().has('sort'),false);assert.equal(b.params().has('cursor'),false);assert.equal(b.params().get('offset'),'1');
});
test('source titles and snippets cannot inject HTML or event attributes',()=>{
  const b=browser();b.state.sources=[src(1,{title:'<img src=x onerror=alert(1)>',primary_author:'<script>bad</script>'})];b.renderSources();
  assert.doesNotMatch(b.node('sourceList').innerHTML,/<img|<script>/);assert.match(b.node('sourceList').innerHTML,/&lt;img/);
  b.renderResults([{id:'q_synthetic',source_title:'<svg onload=x>',original_number:'<b>1</b>',snippet:'<iframe>bad</iframe>',title_ko:'<script>bad</script>'}]);assert.doesNotMatch(b.node('results').innerHTML,/<svg|<iframe|<script>|<b>1/);
});
test('reading view is explicit, preserves list filters and never requests solutions on selection',async()=>{
  const b=browser();b.node('query').value='synthetic';b.node('stars').value='2';b.state.cursor='q_cursor';
  const done=b.selectQuestion('q_test');assert.equal(b.node('catalogView').hidden,true);assert.equal(b.node('readerView').hidden,false);assert.equal(b.calls.length,1);assert.doesNotMatch(b.calls[0].path,/solutions|feedback/);
  b.calls[0].resolve(Response.json(question()));await done;assert.match(b.node('detail').innerHTML,/class="question-title"/);
  b.closeQuestion();assert.equal(b.node('catalogView').hidden,false);assert.equal(b.node('readerView').hidden,true);assert.equal(b.node('query').value,'synthetic');assert.equal(b.node('stars').value,'2');assert.equal(b.state.cursor,'q_cursor');assert.equal(b.node('detail').textContent,'');assert.equal(b.calls.length,1);
});
test('closing a pending solution disclosure prevents a delayed answer from appearing',async()=>{
  const b=browser();b.state.question='q_test';const showing=b.showSolutions('q_test');assert.equal(b.calls.length,1);assert.match(b.calls[0].path,/\/solutions\?/);assert.equal(b.state.solutionsOpen,true);
  await b.showSolutions('q_test');assert.equal(b.state.solutionsOpen,false);assert.equal(b.node('related').textContent,'');assert.equal(b.calls.length,1);
  b.calls[0].resolve(Response.json({solutions:[{authorship:'source_transcription',kind:'answer_only',selected_version:{text:'HIDDEN ANSWER'},assets:[]}]}));await showing;
  assert.doesNotMatch(b.node('related').innerHTML,/HIDDEN ANSWER/);assert.equal(b.node('showSolutions').attributes['aria-expanded'],'false');
});
test('returning to the catalog invalidates an in-flight question and clears reader text at sign-out',async()=>{
  const b=browser(),reading=b.selectQuestion('q_test');b.closeQuestion();b.calls[0].resolve(Response.json(question()));await reading;
  assert.equal(b.node('readerView').hidden,true);assert.equal(b.node('detail').innerHTML,'');
  b.node('detail').textContent='ADMIN-ONLY SYNTHETIC SOURCE';b.node('readerBreadcrumb').textContent='PRIVATE';b.node('readerView').hidden=false;b.signOut(false,false);
  assert.equal(b.node('readerView').hidden,true);assert.equal(b.node('catalogView').hidden,false);assert.equal(b.node('detail').textContent,'');assert.equal(b.node('readerBreadcrumb').textContent,'');assert.equal(b.node('accountLogin').hidden,false);
});
