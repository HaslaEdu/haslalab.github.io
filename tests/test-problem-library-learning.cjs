const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const Runtime=require('../site-runtime.js');
const read=file=>fs.readFileSync(path.join(__dirname,'..',file),'utf8');
const main=[...read('index.html').matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].find(match=>match[1].includes('const REL ='))[1];

function app(){
  const nodes=new Map(),handlers={},observers=[],messages=[],calls={accounts:0};
  class Element{
    constructor(id=''){this.id=id;this.dataset={};this.style={};this.classList={toggle(){},add(){},remove(){}};this.listeners={};this.writes=0;this._html='';this.textContent='';}
    setAttribute(){}addEventListener(name,fn){this.listeners[name]=fn;}querySelectorAll(){return[];}querySelector(){return null;}
    set innerHTML(value){this._html=String(value);this.writes++;
      if(this.id==='view'){
        nodes.delete('learnLibraryFrame');nodes.delete('learnStudioFrame');
        const match=this._html.match(/<iframe id="(learnLibraryFrame|learnStudioFrame)"[^>]*src="([^"]+)"/);
        if(match){const frame=new Element(match[1]);frame.src=match[2];frame.contentWindow={postMessage(data,origin){messages.push({data:JSON.parse(JSON.stringify(data)),origin});}};nodes.set(match[1],frame);}
      }
    }
    get innerHTML(){return this._html;}
  }
  const node=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
  const frameId=id=>id==='learnLibraryFrame'||id==='learnStudioFrame';
  const context={window:{HL_RUNTIME:Runtime},URL,URLSearchParams,console,innerHeight:850,
    location:new URL('https://haslalab.org/#/learn/physics/library'),history:{replaceState(){}},
    document:{getElementById:id=>frameId(id)?nodes.get(id)||null:node(id),querySelector:selector=>selector==='.learn-library .phead'&&nodes.has('learnLibraryFrame')?node('libraryHeading'):selector==='.learn-studio .phead'&&nodes.has('learnStudioFrame')?node('studioHeading'):null,querySelectorAll:()=>[],documentElement:{dataset:{theme:'light'}},body:node('body')},
    localStorage:{getItem:key=>key==='hlCmTok'?'SYNTHETIC_PARENT_TOKEN':null,setItem(){}},sessionStorage:{getItem:()=>null,setItem(){}},
    addEventListener(name,fn){(handlers[name]??=[]).push(fn);},matchMedia:()=>({matches:false}),
    setTimeout(){},clearTimeout(){},requestAnimationFrame(){},cancelAnimationFrame(){},scrollTo(){},
    MutationObserver:class{constructor(callback){this.callback=callback;observers.push(this);}observe(target,options){this.target=target;this.options=options;}disconnect(){}},
    fetch:async()=>{throw Error('Learning parent must not fetch private bank content or credentials');}};
  vm.createContext(context);
  // Learning routes require no contest datasets or exam scripts.
  for(const file of ['site-catalogue.js','site-design.js'])vm.runInContext(read(file),context,{filename:file});
  context.HLexam=context.window.HLexam;
  vm.runInContext(main.replace(/render\(\);\s*$/,''),context,{filename:'index-main.js'});
  const run=code=>vm.runInContext(code,context);
  context.arChip=()=>calls.accounts++;
  run('buildRails=()=>{};paintSiteTheme=()=>{};mountHaslaAdFit=()=>{}');
  return{context,run,node,nodes,handlers,observers,messages,calls};
}

test('physics offers its existing studio and the native private library, without adding another login',()=>{
  const a=app();
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const physics=a.run('viewLearnSubject("physics")');
    assert.match(physics,/href="#\/learn\/physics\/studio"/);assert.match(physics,/href="#\/learn\/physics\/library"/);
    assert.match(physics,language==='ko'?/문제은행/:/Problem library/);
    assert.match(physics,language==='ko'?/관리자 전용/:/Administrators/);
    assert.doesNotMatch(physics,/<form|type="password"|workers\.dev/);
    assert.doesNotMatch(a.run('viewLearnSubject("chemistry")'),/learn\/physics\/library/);
    assert.deepEqual(Runtime.routeNeeds('#/learn/physics/library'),[]);
  }
});

test('the embedded library is same-origin and receives the current language and theme in its initial URL',()=>{
  const a=app();
  for(const language of ['ko','en'])for(const theme of ['light','dark']){
    a.run(`lang=${JSON.stringify(language)}`);a.context.document.documentElement.dataset.theme=theme;
    const html=a.run('viewLearnLibrary()'),src=/id="learnLibraryFrame"[^>]*src="([^"]+)"/.exec(html)[1],url=new URL(src,a.context.location);
    assert.equal(url.origin,a.context.location.origin);assert.equal(url.pathname,'/problem-bank/public/index.html');
    assert.equal(url.searchParams.get('embed'),'1');assert.equal(url.searchParams.get('lang'),language);assert.equal(url.searchParams.get('theme'),theme);
    assert.doesNotMatch(url.href,/token|Bearer|username|password/i);assert.match(html,/referrerpolicy="same-origin"/);
  }
});

test('the router mounts the native bank once and language, theme and auth-chip updates preserve its state',()=>{
  const a=app();a.node('acct').innerHTML='NATIVE ACCOUNT';a.run('render()');
  const frame=a.nodes.get('learnLibraryFrame'),src=frame.src,writes=a.node('view').writes;
  assert.ok(frame);assert.equal(typeof frame.listeners.load,'function');assert.match(a.context.document.title,/문제은행/);
  frame.searchState={query:'saved search',selectedQuestion:'synthetic-qid'};
  frame.listeners.load();assert.equal(a.messages.at(-1).data.type,'hl-bank-settings');
  a.run('setLang("en")');
  assert.equal(a.nodes.get('learnLibraryFrame'),frame);assert.equal(a.node('view').writes,writes);assert.equal(frame.src,src);
  assert.equal(frame.title,'Problem library');assert.match(a.context.document.title,/Problem library/);assert.match(a.node('nav').innerHTML,/<a href="#\/learn" class="on">/);
  a.context.document.documentElement.dataset.theme='dark';
  for(const observer of a.observers)if(observer.target===a.context.document.documentElement)observer.callback([]);
  for(const fn of a.handlers.resize)fn();
  for(const fn of a.handlers.storage)fn({key:'hlCmTok'});
  assert.equal(a.nodes.get('learnLibraryFrame'),frame);assert.equal(a.node('view').writes,writes);assert.deepEqual(frame.searchState,{query:'saved search',selectedQuestion:'synthetic-qid'});
  assert.equal(a.node('acct').innerHTML,'NATIVE ACCOUNT');assert.ok(a.calls.accounts>=3);
  assert.deepEqual(a.messages.at(-1),{origin:'https://haslalab.org',data:{type:'hl-bank-settings',lang:'en',theme:'dark',viewportHeight:850}});
  for(const message of a.messages){assert.equal(message.origin,'https://haslalab.org');assert.deepEqual(Object.keys(message.data).sort(),['lang','theme','type','viewportHeight']);assert.doesNotMatch(JSON.stringify(message),/SYNTHETIC_PARENT_TOKEN|Bearer|password|username/);}
});

test('height messages require the current iframe window and exact origin and accept only bounded finite numeric sizes',()=>{
  const a=app();a.run('render()');const frame=a.nodes.get('learnLibraryFrame');frame.style.height='1050px';
  const send=overrides=>{for(const fn of a.handlers.message)fn({origin:a.context.location.origin,source:frame.contentWindow,data:{type:'hl-bank-height',height:901.2},...overrides});};
  for(const overrides of [{origin:'https://evil.invalid'},{source:{}},{data:{type:'hl-bank-height',height:'900'}},{data:{type:'hl-bank-height',height:Infinity}},{data:{type:'hl-bank-height',height:NaN}},{data:{type:'hl-studio-height',height:900}}]){send(overrides);assert.equal(frame.style.height,'1050px');}
  send();assert.equal(frame.style.height,'902px');send({data:{type:'hl-bank-height',height:1}});assert.equal(frame.style.height,'600px');
  send({data:{type:'hl-bank-height',height:1e9}});assert.equal(frame.style.height,'30000px');
  a.nodes.delete('learnLibraryFrame');send({data:{type:'hl-bank-height',height:1000}});assert.equal(frame.style.height,'30000px');
});

test('navigating away releases the embedded bank rather than preserving it in another learning page',()=>{
  const a=app();a.run('render()');const old=a.nodes.get('learnLibraryFrame');
  a.context.location.hash='#/learn/physics';a.run('render()');assert.equal(a.nodes.has('learnLibraryFrame'),false);
  a.context.location.hash='#/learn/physics/library';a.run('render()');assert.notEqual(a.nodes.get('learnLibraryFrame'),old);
});
