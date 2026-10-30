// Real bridge/poller and the real arena binding, with deterministic local fixtures.
// No user account, provider, camera or production API is contacted.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const Bridge=require('../sim/monthly-photo-bridge.js'),Network=require('../sim/exam-network.js');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const deferred=()=>{let resolve;return{promise:new Promise(done=>resolve=done),resolve:value=>resolve(value)};};
const id='11111111-1111-4111-8111-111111111111',capability='x'.repeat(43),apiBase='https://haslalab-community-edge.haslalab.workers.dev';
const session=(extra={})=>({id,problem_id:4,part_id:'a',open:true,created_at:1000,expires_at:2200,...extra});
const issued=()=>({session:session(),token:capability,now:1000});
const page=(photos=[],cursor=0,extra={})=>({session:session(),photos,cursor,has_more:false,...extra});
function timers(){let id=0;const pending=new Map();return{pending,setTimeout(fn,delay){pending.set(++id,{fn,delay});return id;},clearTimeout:id=>pending.delete(id),async fire(){const [id,next]=pending.entries().next().value||[];if(!next)return;pending.delete(id);await next.fn();}};}
function documentStub(){const events=new Map();return{hidden:false,events,addEventListener:(name,fn)=>events.set(name,fn),removeEventListener:(name,fn)=>{if(events.get(name)===fn)events.delete(name);},change(hidden){this.hidden=hidden;events.get('visibilitychange')?.();}};}
function container(){return{innerHTML:'',buttons:new Map(),querySelector(selector){const name=selector.match(/^\[([^\]]+)\]$/)?.[1];if(!name||!this.innerHTML.includes(name))return null;if(!this.buttons.has(selector))this.buttons.set(selector,{});return this.buttons.get(selector);}};}
function fixture({request:respond,onPhotos=()=>true}={}){
  const calls=[],qrLinks=[],copies=[],clock=timers(),doc=documentStub(),box=container(),state={owner:'A',blocked:false};
  let controller;
  const bridge=Bridge.create({container:box,problemId:4,partId:()=> 'b',language:'en',apiBase,siteUrl:'https://haslalab.org/#/monthly/p/4',
    request:async(method,path,body)=>{calls.push({method,path,body});return respond?respond(method,path,body):method==='POST'?issued():method==='GET'?page():{ok:true};},
    qr:async link=>{qrLinks.push(link);return'<svg aria-label="local fixture"></svg>';},
    createPoll:options=>controller=Network.createPoll({...options,...clock}),document:doc,clipboard:{writeText:async value=>copies.push(value)},now:()=>1000000,
    isCurrent:()=>state.owner==='A',blocked:()=>state.blocked,onPhotos});
  return{bridge,calls,qrLinks,copies,clock,doc,box,state,get controller(){return controller;}};
}

test('construction stays inert; explicit opening issues once and the upload capability appears only in the QR fragment',async()=>{
  const h=fixture();assert.equal(h.calls.length,0);assert.equal(h.clock.pending.size,0);
  h.state.blocked=true;await h.bridge.open();assert.equal(h.calls.length,0);
  h.state.blocked=false;await h.bridge.open();await tick();
  assert.equal(h.calls.filter(call=>call.method==='POST').length,1);assert.deepEqual(h.calls[0],{method:'POST',path:'/monthly/problems/4/scan',body:{part_id:'b'}});
  const link=new URL(h.qrLinks[0]);assert.equal(link.pathname,'/sim/monthly-scan.html');assert.equal(link.searchParams.get('lang'),'en');assert.equal(link.searchParams.has('token'),false);
  const fragment=new URLSearchParams(link.hash.slice(1));assert.equal(fragment.get('token'),capability);assert.equal(fragment.get('a'),apiBase);
  assert.doesNotMatch(h.qrLinks[0],/Bearer|account-token/);assert.ok(h.calls.every(call=>!call.path.includes(capability)&&!JSON.stringify(call.body||{}).includes(capability)));
  await h.box.querySelector('[data-phone-copy]').onclick();assert.equal(h.copies[0],h.qrLinks[0]);
  await h.bridge.open();await tick();assert.equal(h.calls.filter(call=>call.method==='POST').length,1,'reopening a live connection never creates a new capability');
  h.bridge.dispose();assert.equal(h.clock.pending.size,0);assert.equal(h.doc.events.size,0);
});

test('polling follows the cursor and drains at most four ten-photo pages per cycle',async()=>{
  const imported=[];const h=fixture({request:async(method,url)=>{
    if(method==='POST')return issued();if(method!=='GET')return{ok:true};
    const after=Number(new URL(url,'https://fixture').searchParams.get('after'));
    return page(Array.from({length:10},(_,i)=>({photo_id:'photo-'+(after+i+1),part_id:'a',text:'Local work'})),after+10,{has_more:true});
  },onPhotos:rows=>{imported.push(...rows);return true;}});
  await h.bridge.open();await tick();assert.deepEqual(h.calls.filter(call=>call.method==='GET').map(call=>call.path),[0,10,20,30].map(cursor=>'/monthly/problems/4/scan/'+id+'?after='+cursor));
  assert.equal(imported.length,40);assert.equal(h.bridge.state().cursor,40);assert.equal(h.bridge.state().received,40);h.bridge.dispose();
});

test('an import blocked by editing does not advance its cursor, and malformed cursors never import photos',async()=>{
  let accept=false;const rows=[{photo_id:'one',part_id:'a',text:'Local working'}],h=fixture({request:async method=>method==='POST'?issued():method==='GET'?page(rows,1):{ok:true},onPhotos:()=>accept});
  await h.bridge.open();await tick();assert.equal(h.bridge.state().cursor,0);assert.equal(h.bridge.state().received,0);
  accept=true;await h.bridge.poll();assert.equal(h.bridge.state().cursor,1);assert.equal(h.bridge.state().received,1);h.bridge.dispose();
  let imports=0;const broken=fixture({request:async method=>method==='POST'?issued():page(rows,-1),onPhotos:()=>{imports++;}});
  await broken.bridge.open();await tick();assert.equal(imports,0);assert.equal(broken.bridge.state().cursor,0);assert.match(broken.box.innerHTML,/Could not connect/);broken.bridge.dispose();
});

test('closing or disposing during issuance revokes the late capability without drawing or polling it',async()=>{
  for(const action of ['close','dispose']){
    const gate=deferred(),h=fixture({request:async method=>method==='POST'?gate.promise:{ok:true}}),opening=h.bridge.open();
    h.bridge[action]();gate.resolve(issued());await opening;await tick();
    assert.equal(h.qrLinks.length,0);assert.equal(h.calls.filter(call=>call.method==='GET').length,0);
    assert.deepEqual(h.calls.filter(call=>call.method==='DELETE').map(call=>call.path),['/monthly/problems/4/scan/'+id]);assert.equal(h.bridge.state().open,false);
    assert.equal(h.clock.pending.size,0);if(action==='close')h.bridge.dispose();
  }
});

test('late polls cannot append work after close/dispose or an account change',async()=>{
  for(const action of ['close','dispose','owner']){
    const gate=deferred();let imports=0;const h=fixture({request:async method=>method==='POST'?issued():method==='GET'?gate.promise:{ok:true},onPhotos:()=>{imports++;return true;}});
    await h.bridge.open();if(action==='owner')h.state.owner='B';else h.bridge[action]();
    gate.resolve(page([{photo_id:'late',part_id:'a',text:'Late working'}],1));await tick();assert.equal(imports,0);assert.equal(h.bridge.state().cursor,0);
    const before=h.calls.length;await h.bridge.poll();assert.equal(h.calls.length,before);h.bridge.dispose();
  }
  const gate=deferred(),h=fixture({request:async method=>method==='POST'?gate.promise:{ok:true}}),opening=h.bridge.open();h.state.owner='B';gate.resolve(issued());await opening;
  assert.equal(h.qrLinks.length,0);assert.equal(h.calls.filter(call=>call.method==='DELETE').length,1);h.bridge.dispose();
});

test('the real shared poller suspends hidden tabs and stops on a closed session',async()=>{
  let closed=false;const h=fixture({request:async method=>method==='POST'?issued():method==='GET'?page([],0,closed?{session:session({open:false,closed_reason:'submitted'})}:{}):{ok:true}});
  await h.bridge.open();await tick();const count=h.calls.filter(call=>call.method==='GET').length;assert.equal(h.clock.pending.size,1);
  h.doc.change(true);assert.equal(h.clock.pending.size,0);await h.clock.fire();assert.equal(h.calls.filter(call=>call.method==='GET').length,count);
  closed=true;h.doc.change(false);await tick();assert.equal(h.calls.filter(call=>call.method==='GET').length,count+1);assert.equal(h.bridge.state().open,false);assert.equal(h.clock.pending.size,0);assert.match(h.box.innerHTML,/ended when an answer was submitted/);assert.doesNotMatch(h.box.innerHTML,/#token=/);h.bridge.dispose();
});

function arenaFixture(){
  const records=[],store=new Map(),events=new Map(),controls=new Map(),calls=[],phoneCalls=[],photosBox=container(),modeBox={hidden:true},out={innerHTML:''},attempts={textContent:''},submit={disabled:false};
  const fields=[];
  for(const id of ['a','b'])for(const type of ['answer','working']){
    const field={value:'',dataset:{[type==='answer'?'sheetAnswer':'sheetWorking']:id},disabled:false};controls.set(`[data-sheet-${type}="${id}"]`,field);fields.push(field);
    controls.set(`[data-sheet-${type}-preview="${id}"]`,{innerHTML:''});
  }
  const modes=['typed','photo'].map(sheetMode=>({dataset:{sheetMode},classList:{toggle(){}},setAttribute(){}}));
  const form={photo_part:{value:'a'},querySelector(selector){return selector==='button[type=submit]'?submit:selector==='[data-monthly-phone]'?photosBox:selector==='.arsheet-photo'?modeBox:controls.get(selector)||null;},querySelectorAll(selector){return selector==='[data-sheet-mode]'?modes:selector==='[data-sheet-answer], [data-sheet-working]'?fields:[];}};
  const root={querySelector:selector=>selector==='#arSheetF'?form:selector==='#arOut'?out:selector==='#arSheetAttempts'?attempts:null},state={token:'local-account-token',base:apiBase,alive:true};let importedOptions,serial=0;
  const context={lang:'en',cm:{me:{id:1}},window:{addEventListener:(name,fn)=>events.set(name,fn),removeEventListener:(name,fn)=>{if(events.get(name)===fn)events.delete(name);}},location:{href:'https://haslalab.org/#/monthly/p/4',hash:'#/monthly/p/4'},URL,URLSearchParams,console,
    esc:value=>String(value),document:{},localStorage:{getItem:key=>store.get(key)||null,setItem:(key,value)=>store.set(key,value)},setTimeout(){return 1;},clearTimeout(){},crypto:{randomUUID:()=> 'local-request-'+(++serial)},
    cmBase:()=>state.base,cmTok:()=>state.token,cmApi:async(method,path,body)=>{calls.push({method,path,body});return{status:'graded',attempts:{limit:3,used:calls.filter(call=>call.path.endsWith('/submit')).length,remaining:3-calls.filter(call=>call.path.endsWith('/submit')).length}};}};
  vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../arena.js'),'utf8'),context);
  context.arMath=()=>{};context.arSheetFinalPreview=value=>value;context.arSheetWorkingPreview=value=>value;context.arResult=()=>'<p>Local grade</p>';context.arBindAnswerPhoto=()=>{};
  context.arLoadMonthlyScan=async()=>({network:{createPoll(){}},bridge:{create(options){importedOptions=options;return{async open(){phoneCalls.push('open');},close(){phoneCalls.push('close');},dispose(){phoneCalls.push('dispose');}};}}});
  const problem={id:4,points:100,attempts:{limit:3,used:0,remaining:3},answerSheet:{version:'local-v1',parts:[{id:'a'},{id:'b'}]}};
  context.arBindMonthlyAnswer(root,problem,()=>state.alive,true);
  return{context,problem,root,form,fields,modes,controls,calls,phoneCalls,store,state,events,out,submit,records,get options(){return importedOptions;},async photo(){modes[1].onclick();await tick();},receive:rows=>importedOptions.onPhotos(rows)};
}

test('the arena creates a phone connection only after the explicit photo action and ignores duplicate/wrong-part imports',async()=>{
  const h=arenaFixture();assert.equal(h.options,undefined);assert.equal(h.calls.length,0);h.modes[0].onclick();assert.equal(h.phoneCalls.length,0);
  await h.photo();assert.deepEqual(h.phoneCalls,['open']);assert.equal(h.options.problemId,4);assert.equal(h.options.partId(),'a');
  const a=h.controls.get('[data-sheet-working="a"]');a.value='Existing own working';
  const first={photo_id:'local-photo-A',part_id:'a',text:'Recognized A'};h.receive([first,first,{photo_id:'invalid',part_id:'other-problem',text:'Wrong part'}]);h.receive([first]);
  assert.equal(a.value,'Existing own working\n\nRecognized A');assert.equal(a.value.includes('Wrong part'),false);
  h.receive([{photo_id:'local-photo-B',part_id:'b',text:'Recognized B'}]);assert.equal(h.controls.get('[data-sheet-working="b"]').value,'Recognized B');
  const draft=JSON.parse([...h.store.values()][0]);assert.deepEqual(draft.photos,[{id:'local-photo-A',part_id:'a'},{id:'local-photo-B',part_id:'b'}]);assert.equal(draft.via_ocr,true);
  h.modes[0].onclick();assert.equal(h.phoneCalls.at(-1),'close');h.context.cm.me={id:2};assert.equal(h.options.isCurrent(),false);assert.equal(h.receive([{photo_id:'stale',part_id:'a',text:'Other account work'}]),false);assert.equal(a.value.includes('Other account work'),false);
});

test('phone attachments stay in the monthly submit payload while exactly three accepted attempts remain enforced',async()=>{
  const h=arenaFixture();await h.photo();h.receive([{photo_id:'local-photo-A',part_id:'a',text:'Recognized working'}]);const answer=h.controls.get('[data-sheet-answer="a"]');answer.value='Final answer';
  const submit=()=>h.form.onsubmit({preventDefault(){}});
  await submit();assert.equal(h.calls.length,1);assert.equal(h.calls[0].path,'/problems/4/submit');assert.deepEqual(Array.from(h.calls[0].body.photo_ids),['local-photo-A']);assert.equal(h.calls[0].body.via_ocr,true);assert.equal(h.calls[0].body.sheet_version,'local-v1');assert.equal(h.problem.attempts.remaining,2);assert.equal(h.phoneCalls.at(-1),'close');
  await submit();assert.equal(h.calls.length,1,'a repeat click after acceptance is inert');
  for(let attempt=2;attempt<=3;attempt++){answer.value='Revised final answer '+attempt;answer.oninput();await submit();}
  assert.equal(h.calls.length,3);assert.equal(h.problem.attempts.remaining,0);assert.equal(h.submit.disabled,true);assert.equal(new Set(h.calls.map(call=>call.body.request_id)).size,3);
  answer.value='Fourth answer';answer.oninput();await submit();assert.equal(h.calls.length,3);
  h.context.arMonthlyScanModule=null;h.context.cm.me={id:2};await submit();assert.equal(h.calls.length,3);
});

test('disposing the arena page rejects late photo callbacks and releases its phone binding',async()=>{
  const h=arenaFixture();await h.photo();h.events.get('hashchange')();assert.equal(h.phoneCalls.at(-1),'dispose');assert.equal(h.options.isCurrent(),false);
  assert.equal(h.receive([{photo_id:'late',part_id:'a',text:'Late old route work'}]),false);assert.equal(h.controls.get('[data-sheet-working="a"]').value,'');
});
