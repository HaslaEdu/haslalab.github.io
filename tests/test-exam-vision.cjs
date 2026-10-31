const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../sim/exam.html'),'utf8');
function fixture(){
 let identity='account-1';
 const select={value:'deepseek',disabled:false,isConnected:true};
 const notices=[],calls=[],context=vm.createContext({
  SES:null,BUSY:false,lang:'ko',ME:{tokens:4},$:()=>select,
  transport:{fingerprint:()=>identity},toast:value=>notices.push(value),t:()=>({err:{}}),
  api:async(method,path,body)=>{calls.push({method,path,body});return{session:{id:4,provider:body.provider,provider_locked:false}};},
  setSession(s){context.SES=s;},esc:String
 });
 const begin=html.indexOf('let VISION ='),end=html.indexOf('const srvNow',begin);
 vm.runInContext(html.slice(begin,end),context);
 return{context,select,calls,notices,identity:value=>{identity=value;},run:code=>vm.runInContext(code,context)};
}
test('exam offers exactly deepseek/gemini, honors capability availability and authoritative pin',()=>{
 const f=fixture();f.run('VISION={providers:[{id:"deepseek",available:true},{id:"gemini",available:false}]}');
 const rendered=f.run('providerHtml()');
 assert.equal((rendered.match(/<option/g)||[]).length,2);
 assert.match(rendered,/>deepseek<\/option>/);assert.match(rendered,/>gemini<\/option>/);
 assert.match(rendered,/<option value="gemini"[^>]*disabled/);
 f.context.SES={id:4,provider:'gemini',provider_locked:true};
 assert.equal(f.run('gradingProvider()'),'gemini');
 assert.match(f.run('providerHtml()'),/id="gradingProvider"[^>]*disabled/);
});
test('a free session can change provider, server pin prevents another request',async()=>{
 const f=fixture();f.context.SES={id:4,provider:'gemini'};f.run('VISION={providers:[{id:"deepseek",available:true}]}');
 f.run('bindProvider()');await f.select.onchange();
 assert.deepEqual(f.calls.map(c=>[c.method,c.path,c.body.provider]),[['POST','/lab/sessions/4/provider','deepseek']]);
 assert.equal(f.select.disabled,false);f.context.SES.provider_locked=true;
 await f.select.onchange();assert.equal(f.calls.length,1);
});
test('provider change response cannot overwrite another account/session',async()=>{
 const f=fixture();f.context.SES={id:4,provider:'gemini'};f.run('VISION={providers:[{id:"deepseek",available:true}]}');
 let finish;f.context.api=()=>new Promise(resolve=>{finish=resolve;});
 f.run('bindProvider()');const pending=f.select.onchange();
 f.identity('account-2');f.context.SES={id:8,provider:'gemini'};finish({session:{id:4,provider:'deepseek'}});
 await pending;assert.equal(f.context.SES.id,8);assert.equal(f.context.SES.provider,'gemini');
});
test('start, pay, submit and generic photo artifact requests carry selected provider/problem identity',()=>{
 for(const fragment of [
  html.slice(html.indexOf('async function startExam'),html.indexOf('/* ── the bench',html.indexOf('async function startExam'))),
  html.slice(html.indexOf('async function payNow'),html.indexOf('async function submitNow')),
  html.slice(html.indexOf('async function submitNow'),html.indexOf('/* ── the result'))
 ])assert.match(fragment,/provider/);
 const arena=fs.readFileSync(require.resolve('../arena.js'),'utf8');
 assert.match(arena,/problem_id=.*encodeURIComponent\(options\.problemId\)/);
 assert.match(arena,/\{problemId:id,provider:/);
});

test('typed-answer save and review hydration ignore an old account response before painting private data',async()=>{
 for(const name of ['saveTypedAnswers','scanView']){
  let identity='old',resolve,painted=0;
  const form={querySelectorAll:()=>[{dataset:{answer:'T1'},value:'Private old work'}]};
  const context=vm.createContext({SES:{id:1,status:'scanning'},typedDirty:true,REVIEW:true,
   transport:{fingerprint:()=>identity},$:()=>form,api:()=>new Promise(done=>resolve=done),
   setSession(value){painted++;context.SES=value;},paintPages(){painted++;},render(){painted++;}});
  const start=html.indexOf('async function '+name+'('),end=html.indexOf(name==='saveTypedAnswers'?'async function scanView(':'function scanUrl(',start);
  vm.runInContext(html.slice(start,end),context);const pending=context[name]();
  identity='new';context.SES={id:2,status:'scanning'};resolve({session:{id:1,pages:[{text:'Private old answer'}]}});await pending;
  assert.equal(context.SES.id,2);assert.equal(painted,0,name+' must check account/session before state or DOM updates');
 }
});

test('finishing an old exam cannot retry under the next account or overwrite its session',async()=>{
 let identity='old',reject,calls=0;
 const context=vm.createContext({SES:{id:1,status:'running'},finishing:false,tick:0,mirror:0,stations:[],PAPER:{},shown:'run',
  transport:{fingerprint:()=>identity},clearInterval(){},closePaper(){},t:()=>({darkH:'Done',darkB:''}),
  document:{createElement:()=>({remove(){}}),body:{append(){}}},setTimeout:fn=>{fn();},
  api(){calls++;return new Promise((resolve,fail)=>reject=fail);},setSession(s){context.SES=s;},render(){assert.fail('old finish must not render under the new account');}});
 const start=html.indexOf('async function finishExam('),end=html.indexOf('/* ── thirty minutes to scan',start);
 vm.runInContext(html.slice(start,end),context);const pending=context.finishExam();identity='new';context.SES={id:2,status:'running'};reject({code:'account_changed'});await pending;
 assert.equal(calls,1);assert.equal(context.SES.id,2);assert.equal(context.finishing,false);
});

function retryFixture(){
 let identity='owner',resolve,reject;const calls=[],button={disabled:false},info={textContent:''};
 const s={id:7,paid:true,status:'pending',provider:'deepseek',pages:[{id:8,ocr_status:'failed'}]};
 const context=vm.createContext({SES:s,BUSY:false,lang:'ko',shown:'done',transport:{fingerprint:()=>identity},
  $:id=>id==='retryOcr'?button:info,api:(method,path,body)=>{calls.push({method,path,body});return new Promise((yes,no)=>{resolve=yes;reject=no;});},
  errMsg:e=>e.code,setSession(value){context.SES=value;},render(){context.renders=(context.renders||0)+1;}});
 vm.runInContext(html.slice(html.indexOf('function bindOcrRetry('),html.indexOf('function doneView()')),context);
 context.bindOcrRetry(s);
 return{context,s,button,info,calls,identity:value=>identity=value,finish:value=>resolve(value),fail:value=>reject(value)};
}

test('exam failure retry is explicit, sends the pinned provider once and renders the queued session without paying',async()=>{
 const f=retryFixture();assert.equal(f.calls.length,0);
 const pending=f.button.onclick();await f.button.onclick();
 assert.equal(f.button.disabled,true);assert.equal(f.calls.length,1);
 assert.equal(f.calls[0].method,'POST');assert.equal(f.calls[0].path,'/lab/sessions/7/retry-ocr');assert.equal(f.calls[0].body.provider,'deepseek');
 f.finish({session:{...f.s,status:'grading'}});await pending;
 assert.equal(f.context.SES.status,'grading');assert.equal(f.context.renders,1);
 assert.ok(f.calls.every(c=>!c.path.includes('/pay')));
});

test('a failed OCR retry can be requested again, while stale account/session results never repaint',async()=>{
 const failed=retryFixture(),attempt=failed.button.onclick();failed.fail({code:'vision_provider_credits'});await attempt;
 assert.equal(failed.button.disabled,false);assert.equal(failed.info.textContent,'vision_provider_credits');
 for(const changed of ['account','session']){
  const f=retryFixture(),pending=f.button.onclick();
  if(changed==='account')f.identity('other');else f.context.SES={id:99};
  f.finish({session:{...f.s,status:'graded',nickname:'PRIVATE_LATE_DATA'}});await pending;
  assert.equal(f.context.renders,undefined);assert.notEqual(f.context.SES.nickname,'PRIVATE_LATE_DATA');assert.equal(f.calls.length,1);
 }
});
