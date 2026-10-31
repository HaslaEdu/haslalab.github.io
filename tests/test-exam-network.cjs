const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const Network=require('../sim/exam-network.js');
const deferred=()=>{let resolve;return{promise:new Promise(r=>resolve=r),resolve:v=>resolve(v)};};
const response=value=>({ok:true,json:async()=>value});
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function timers(){let id=0;const pending=new Map();return{pending,setTimeout(fn,ms){pending.set(++id,{fn,ms});return id;},clearTimeout(id){pending.delete(id);},async fire(){const [id,next]=pending.entries().next().value||[];if(!next)return;pending.delete(id);await next.fn();},delay(){return pending.values().next().value?.ms;}};}
function documentStub(){const events=new Map();return{hidden:false,addEventListener:(n,fn)=>events.set(n,fn),removeEventListener:(n,fn)=>{if(events.get(n)===fn)events.delete(n);},change(hidden){this.hidden=hidden;events.get('visibilitychange')?.();},events};}

test('reading failures distinguish provider/account/response problems without exposing arbitrary error text',()=>{
  const cases={vision_provider_auth:/authentication/,vision_provider_credits:/API credit/,vision_provider_rate_limited:/request limit/,
    vision_model_unavailable:/model is unavailable/,vision_request_rejected:/rejected the image request/,
    vision_provider_failed:/server error/,vision_provider_timeout:/timed out/,vision_response_empty:/empty response/,
    vision_response_truncated:/cut off/,vision_response_blocked:/restricted/,vision_invalid_response:/decoded/,
    vision_response_schema:/fields/,ocr_bad_response:/fields/};
  for(const [code,pattern]of Object.entries(cases)){
    assert.match(Network.ocrErrorMessage(code,'en'),pattern);
    assert.ok(Network.ocrErrorMessage(code,'ko'));
    assert.doesNotMatch(Network.ocrErrorMessage(code,'en'),/retake|photograph it again/i,'a provider failure is not advice to photograph the page again');
  }
  for(const code of ['<img src=x onerror=alert(1)>','Bearer secret-key',{},null,'toString','__proto__'])assert.equal(Network.ocrErrorMessage(code),'');
  assert.match(Network.ocrErrorMessage('ocr_storage_limit','en'),/storage limit/);
});

test('a changed reading failure refreshes the same page without resetting account/session scope',()=>{
  const s={id:1,status:'scanning',paid:true,pages:[{id:3,ocr_status:'failed',ocr_error:'vision_provider_failed'}]};
  assert.notEqual(Network.sessionSignature(s),Network.sessionSignature({...s,pages:[{...s.pages[0],ocr_error:'vision_provider_credits'}]}));
});

test('the actual phone page shows the stored provider reason even with an old good-legibility value',()=>{
  const html=fs.readFileSync(require.resolve('../sim/scan.html'),'utf8'),source=html.slice(html.indexOf('function sentList()'),html.indexOf('function wireSent()'));
  const escape=value=>String(value).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const ctx=vm.createContext({NETWORK:Network,esc:escape,lang:'en',INFO:{open:true,pages:[{id:3,no:1,task:'T1',kind:'answer',ocr_status:'failed',ocr_error:'vision_provider_credits',legible:'good'}]},
    t:()=>({sentH:'Sent',answer:'Answer',working:'Working',del:'Remove',ocr:{failed:'Reading failed'},legS:{good:'Read well'},ocrFailed:'Generic failure',none:'None'})});
  vm.runInContext(source,ctx);const rendered=ctx.sentList();
  assert.match(rendered,/insufficient API credit/);assert.match(rendered,/class="s poor"/);assert.doesNotMatch(rendered,/Read well|retake/);
  ctx.INFO.pages[0].ocr_error='<script>private secret</script>';
  assert.doesNotMatch(ctx.sentList(),/private secret|<script>/);
});

test('the actual exam page prioritizes a failed provider result and refreshes changed error categories',()=>{
  const html=fs.readFileSync(require.resolve('../sim/exam.html'),'utf8'),source=html.slice(html.indexOf('function paintPages(s)'),html.indexOf('async function thumb('));
  const nodes=new Map([['pages',{innerHTML:'',querySelectorAll:()=>[]}],['sub',{}]]);
  const escape=value=>String(value).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const ctx=vm.createContext({$:id=>nodes.get(id)||null,esc:escape,EXAM_NETWORK:Network,pagesSeen:'',lang:'en',
    t:()=>({pagesH:'Pages',paid:'Paid',submit:'Submit',noEdit:'No editing',readH:'Reading',nothing:'No text',answer:'Answer',working:'Working',ocrFailed:'Generic failure',leg:{good:'Read well'}})});
  vm.runInContext(source,ctx);const page={id:3,no:1,task:'T1',kind:'answer',ocr_status:'failed',ocr_error:'vision_response_truncated',legible:'good'};
  const session={paid:true,tasks:['T1'],pages:[page]};ctx.paintPages(session);
  assert.match(nodes.get('pages').innerHTML,/response was cut off/);assert.doesNotMatch(nodes.get('pages').innerHTML,/Read well/);
  page.ocr_error='vision_provider_credits';ctx.paintPages(session);
  assert.match(nodes.get('pages').innerHTML,/insufficient API credit/);
});

test('identical in-flight GETs share one request, while accounts, bases and mutations remain isolated',async()=>{
  let token='account-a',base='https://a.test',calls=[];const first=deferred();
  const transport=Network.createTransport({getToken:()=>token,getBase:()=>base,fetch:async(url,opts)=>{calls.push({url,...opts});return calls.length===1?first.promise:response({n:calls.length});}});
  const a=transport.request('GET','/lab/active'),b=transport.request('GET','/lab/active');assert.equal(a,b);assert.equal(calls.length,1);
  first.resolve(response({n:1}));await a;
  await transport.request('POST','/lab/sessions/1/pay',{});await transport.request('GET','/lab/active');
  token='account-b';await transport.request('GET','/lab/active');base='https://b.test';await transport.request('GET','/lab/active');
  assert.equal(calls.length,5);assert.equal(calls[3].headers.Authorization,'Bearer account-b');assert.match(calls[4].url,/^https:\/\/b.test/);
});

test('a response arriving after an account change is rejected instead of attaching private state',async()=>{
  let token='a';const result=deferred(),transport=Network.createTransport({getBase:()=> 'https://a.test',getToken:()=>token,fetch:()=>result.promise});
  const old=transport.request('GET','/lab/sessions/1');token='b';result.resolve(response({session:{id:1}}));
  await assert.rejects(old,e=>e.code==='account_changed');
});

test('unchanged exam polling backs off from 5 to 10, 20 and 30 seconds and stops at terminal state',async()=>{
  const clock=timers(),doc=documentStub();let active=true,count=0;
  const poll=Network.createPoll({...clock,document:doc,active:()=>active,task:async()=>{count++;return false;}});poll.start();
  assert.equal(clock.delay(),5000);await clock.fire();assert.equal(clock.delay(),10000);await clock.fire();assert.equal(clock.delay(),20000);await clock.fire();assert.equal(clock.delay(),30000);
  active=false;await clock.fire();assert.equal(count,3);assert.equal(clock.pending.size,0);poll.dispose();assert.equal(doc.events.size,0);
});

test('hidden tabs send no polling requests and one visible wake cannot overlap an existing request',async()=>{
  const clock=timers(),doc=documentStub(),gate=deferred();let count=0;
  const poll=Network.createPoll({...clock,document:doc,task:async()=>{count++;await gate.promise;return true;}});poll.start();doc.change(true);assert.equal(clock.pending.size,0);assert.equal(count,0);
  doc.change(false);assert.equal(count,1);poll.wake();poll.wake();assert.equal(count,1);gate.resolve();await flush();assert.equal(clock.pending.size,1);assert.equal(clock.delay(),5000);
  poll.dispose();assert.equal(clock.pending.size,0);
});

test('server timestamps alone do not reset backoff and OCR queue statuses stay unfinished',()=>{
  const a={id:3,status:'scanning',now:1,pages:[{id:4,ocr_status:'queued'}]},b={...a,now:2};
  assert.equal(Network.sessionSignature(a),Network.sessionSignature(b));assert.equal(Network.reading(a.pages[0]),true);
  assert.equal(Network.reading({ocr_status:'reading'}),true);assert.equal(Network.reading({ocr_status:'done'}),false);assert.equal(Network.reading({source:'typed',ocr_status:'queued'}),false);
});

function examSyncContext(api,identity=()=> 'test-account'){
  const source=fs.readFileSync(require.resolve('../sim/exam.html'),'utf8'),part=source.slice(source.indexOf('let syncPromise=null'),source.indexOf('\nasync function introView()'));
  const context=vm.createContext({transport:{fingerprint:identity},requestEpoch:0,SES:null,ME:null,SKEW:0,LABOK:null,REG:null,VISION:null,selectedProvider: "gemini",shown:'',pagesSeen:'',imgCache:new Map(),imgPending:new Map(),URL:{revokeObjectURL(){}},stopTimers(){},OK_EXAM:true,REVIEW:false,KEY:'ipho2024',EX:{tasks:['E1']},tok:()=>identity(),api,document:{hidden:false,addEventListener(){}},addEventListener(){},poller:null,render(){context.renders=(context.renders||0)+1;},setSession(s){context.SES=s;},Date,encodeURIComponent});
  vm.runInContext(part,context);return context;
}

test('the real exam sync hydrates identity, balance, health and active clock in one deduplicated request',async()=>{
  const calls=[],gate=deferred(),context=examSyncContext((method,path)=>{calls.push({method,path});return gate.promise;});
  const a=context.sync(),b=context.sync();assert.equal(a,b);assert.equal(calls.length,1);assert.match(calls[0].path,/^\/lab\/bootstrap\?include=health,pages$/);
  gate.resolve({user:{nickname:'Candidate'},tokens:4,parts:0,active:{id:2,exam_key:'ipho2024',tasks:['E1'],status:'running',started_at:100},health:{lab:true,lab_reg:{version:'test'}},now:Math.floor(Date.now()/1000)+30});await a;
  assert.equal(context.ME.nickname,'Candidate');assert.equal(context.ME.tokens,4);assert.equal(context.SES.id,2);assert.equal(context.LABOK,true);assert.ok(context.SKEW>=29&&context.SKEW<=31);assert.equal(context.renders,1);
});

test('the real exam sync ignores an old account response after sign-out',async()=>{
  let identity='a';const gate=deferred(),context=examSyncContext(()=>gate.promise,()=>identity),old=context.sync();identity='';
  gate.resolve({user:{nickname:'Old account'},tokens:9,active:{id:2},health:{lab:true}});await old;
  assert.equal(context.ME,null);assert.equal(context.SES,null);assert.equal(context.renders,undefined);
});

test('the actual phone scanner suspends hidden polling and stops requesting once the upload window closes',async()=>{
  const html=fs.readFileSync(require.resolve('../sim/scan.html'),'utf8'),script=html.match(/<script type="module">([\s\S]*?)<\/script>/)[1].replace(/^import .*?;\s*$/m,'');
  const doc=documentStub(),clock=timers(),nodes=new Map();let calls=0,open=true;
  const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',style:{},classList:{toggle(){}},querySelectorAll:()=>[],click(){}});return nodes.get(id);};
  Object.assign(doc,{getElementById:node,querySelector:node,querySelectorAll:()=>[],documentElement:{},createElement:()=>node('element'),body:{append(){}}});
  const context=vm.createContext({document:doc,window:{HLExamNetwork:{...Network,createTransport:options=>Network.createTransport({...options,fetch:async()=>{calls++;return response({comp:'kmo',year:2025,tasks:['Q1'],status:'scanning',open,now:100,scan_until:200,pages:[]});}}),createPoll:options=>Network.createPoll({...options,...clock})}},URL,URLSearchParams,location:{hash:'#c=test-upload-code',pathname:'/sim/scan.html'},history:{replaceState(){}},navigator:{language:'ko'},sessionStorage:{setItem(){},getItem:()=>null,removeItem(){}},localStorage:{getItem:()=>null},setInterval(){},setTimeout:clock.setTimeout,clearTimeout:clock.clearTimeout});
  vm.runInContext(script+'\npaint=()=>{};globalThis.phone={refresh,dispose:()=>phonePoll.dispose()};',context);await flush();assert.equal(calls,1);
  doc.change(true);assert.equal(clock.pending.size,0);await clock.fire();assert.equal(calls,1);
  doc.change(false);await flush();assert.equal(calls,2);
  open=false;await context.phone.refresh();await clock.fire();doc.change(true);doc.change(false);await flush();assert.equal(calls,3);assert.equal(clock.pending.size,0);context.phone.dispose();
});
