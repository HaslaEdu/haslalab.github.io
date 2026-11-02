const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const Runtime=require('../site-runtime.js');
const read=file=>fs.readFileSync(path.join(__dirname,'..',file),'utf8');
const main=[...read('index.html').matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].find(match=>match[1].includes('const REL ='))[1];
function app(){
  const nodes=new Map(),handlers={},observers=[],messages=[];
  class Element{
    constructor(id=''){this.id=id;this.dataset={};this.style={};this.classList={toggle(){},add(){},remove(){}};this.listeners={};this.writes=0;this._html='';}
    setAttribute(){}addEventListener(name,fn){this.listeners[name]=fn;}querySelectorAll(){return[];}querySelector(){return null;}
    set innerHTML(value){this._html=String(value);this.writes++;if(this.id==='view'){nodes.delete('learnSearchFrame');const match=this._html.match(/<iframe id="learnSearchFrame"[^>]*src="([^"]+)"/);if(match){const frame=new Element('learnSearchFrame');frame.src=match[1];frame.contentWindow={postMessage(data,origin){messages.push({data:JSON.parse(JSON.stringify(data)),origin});}};nodes.set(frame.id,frame);}}}
    get innerHTML(){return this._html;}
  }
  const node=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
  const frames=new Set(['learnSearchFrame','learnStudioFrame','learnLibraryFrame']);
  const context={window:{HL_RUNTIME:Runtime},URL,URLSearchParams,console,innerHeight:850,
    location:new URL('https://haslalab.org/#/learn/physics/search'),history:{replaceState(){}},
    document:{getElementById:id=>frames.has(id)?nodes.get(id)||null:node(id),querySelector:selector=>selector==='.learn-search .phead'&&nodes.has('learnSearchFrame')?node('searchHeading'):null,querySelectorAll:()=>[],documentElement:{dataset:{theme:'light'}},body:node('body')},
    localStorage:{getItem:key=>key==='hlCmTok'?'SYNTHETIC_PARENT_TOKEN':null,setItem(){}},sessionStorage:{getItem:()=>null,setItem(){}},
    addEventListener(name,fn){(handlers[name]??=[]).push(fn);},matchMedia:()=>({matches:false}),setTimeout(){},clearTimeout(){},requestAnimationFrame(){},cancelAnimationFrame(){},scrollTo(){},
    MutationObserver:class{constructor(callback){this.callback=callback;observers.push(this);}observe(target){this.target=target;}disconnect(){}},
    fetch:async()=>{throw Error('Learning parent must not fetch bank content or credentials');}};
  vm.createContext(context);for(const file of ['site-catalogue.js','site-design.js'])vm.runInContext(read(file),context,{filename:file});
  context.HLexam=context.window.HLexam;vm.runInContext(main.replace(/render\(\);\s*$/,''),context,{filename:'index-main.js'});
  const run=code=>vm.runInContext(code,context);context.arChip=()=>{};run('buildRails=()=>{};paintSiteTheme=()=>{};mountHaslaAdFit=()=>{}');
  return{context,run,node,nodes,handlers,observers,messages};
}
test('home and Studio route to search with no figure-creation tile',()=>{
  const a=app();for(const language of ['ko','en']){a.run('lang='+JSON.stringify(language));const home=a.run('viewHomeStudio()');assert.match(home,/href="#\/learn\/physics\/search"/);assert.doesNotMatch(home,/mode=restore/);assert.match(a.run('learnStudioHeading()'),language==='ko'?/문제 검색/:/Problem search/);}
  assert.match(read('studio.html'),/id="problemSearchLink"[^>]*target="_top"/);assert.match(read('studio.html'),/<label hidden data-legacy-mode>/);
  assert.deepEqual(Runtime.routeNeeds('#/learn/physics/search'),[]);
});
test('search iframe receives cosmetic state, and language/theme/auth changes preserve the selected result',()=>{
  const a=app();a.run('render()');const frame=a.nodes.get('learnSearchFrame'),writes=a.node('view').writes,src=frame.src,url=new URL(src,a.context.location);
  assert.equal(url.origin,a.context.location.origin);assert.equal(url.pathname,'/problem-search.html');assert.equal(url.searchParams.get('embed'),'1');assert.doesNotMatch(url.href,/token|Bearer|password/i);
  frame.searchState={query:'angular momentum',selectedQuestion:'synthetic-qid'};frame.listeners.load();
  a.run('setLang("en")');a.context.document.documentElement.dataset.theme='dark';for(const observer of a.observers)if(observer.target===a.context.document.documentElement)observer.callback([]);
  for(const fn of a.handlers.resize)fn();for(const fn of a.handlers.storage)fn({key:'hlCmTok'});
  assert.equal(a.nodes.get('learnSearchFrame'),frame);assert.equal(frame.src,src);assert.equal(a.node('view').writes,writes);assert.deepEqual(frame.searchState,{query:'angular momentum',selectedQuestion:'synthetic-qid'});assert.equal(frame.title,'Search problems');assert.match(a.context.document.title,/Search problems/);
  assert.deepEqual(a.messages.at(-1),{origin:'https://haslalab.org',data:{type:'hl-problem-search-settings',lang:'en',theme:'dark',viewportHeight:850}});
  for(const message of a.messages)assert.doesNotMatch(JSON.stringify(message),/SYNTHETIC_PARENT_TOKEN|Bearer|password|username/);
});
test('search height bridge rejects other frames, origins and malformed heights; leaving search unmounts it',()=>{
  const a=app();a.run('render()');const frame=a.nodes.get('learnSearchFrame');frame.style.height='1000px';
  const send=overrides=>{for(const fn of a.handlers.message)fn({origin:a.context.location.origin,source:frame.contentWindow,data:{type:'hl-problem-search-height',height:901.2},...overrides});};
  for(const invalid of [{origin:'https://evil.invalid'},{source:{}},{data:{type:'hl-problem-search-height',height:'900'}},{data:{type:'hl-problem-search-height',height:Infinity}},{data:{type:'hl-bank-height',height:900}}]){send(invalid);assert.equal(frame.style.height,'1000px');}
  send();assert.equal(frame.style.height,'902px');send({data:{type:'hl-problem-search-height',height:1e9}});assert.equal(frame.style.height,'30000px');
  a.context.location.hash='#/learn/physics';a.run('render()');assert.equal(a.nodes.has('learnSearchFrame'),false);
});
