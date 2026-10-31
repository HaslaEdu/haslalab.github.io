const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function app(language='en'){
  let medalCalls=0;
  const context=vm.createContext({lang:language,cm:{me:{nickname:'Student'}},DATA:{},
    window:{labMedal:{load:async()=>{medalCalls++;return{}},estimate:()=>({}),html:()=>'<b>medal</b>'}},
    esc:x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),
    cmFull:()=> '2026-10-30 12:00',cmShort:()=> '10-30',URLSearchParams,encodeURIComponent});
  vm.runInContext(fs.readFileSync(require.resolve('../arena.js'),'utf8'),context);
  vm.runInContext('arMath=()=>{};arShopWire=()=>{}',context);
  return{context,medalCalls:()=>medalCalls,host:()=>({innerHTML:'',querySelector:()=>null,querySelectorAll:()=>[]})};
}
function qualitativeSession(){
  return{id:77,comp:'ortvay',year:2026,tasks:['T'],kind:'theory',review_only:true,status:'graded',score:null,points:null,
    started_at:1,pages:[],standing:{mine:99,rank:1,n:5,top_pct:1,avg:70,max:99,first:false},
    detail:{tasks:{T:{status:'graded',score:null,points:null,grading_mode:'qualitative_review',reference:'published_problem_only',official:false,items:[],
      evidence:[{page:1,quote:'F = ma',note:'State the force directions.'}],feedback:[{kind:'fix',note:'Define the coordinate axis.'}],
      review:{summary:'A promising argument with an unproved assumption.',strengths:['Clear free-body diagram.'],habits:[{habit:'Unstated assumptions',fix:'List assumptions before calculating.',pages:[1]}]}}}}};
}

test('qualitative review report shows grounded feedback without numerical score, ranking or medal',async()=>{
  const a=app(),s=qualitativeSession(),host=a.host();
  a.context.cmApi=async()=>({session:s});
  await a.context.arLabOne(host,()=>true,s.id);
  assert.ok(host.innerHTML.includes('Grading &amp; feedback')||host.innerHTML.includes('Grading & feedback'));
  assert.ok(host.innerHTML.includes('#/ortvay/review'));
  assert.ok(host.innerHTML.includes('Feedback complete · no score'));
  assert.ok(host.innerHTML.includes('No official solution or marking scheme'));
  assert.ok(host.innerHTML.includes('F = ma'));
  assert.ok(host.innerHTML.includes('State the force directions.'));
  assert.ok(host.innerHTML.includes('Define the coordinate axis.'));
  assert.ok(host.innerHTML.includes('A promising argument with an unproved assumption.'));
  assert.doesNotMatch(host.innerHTML,/null\s*\/|0\s*\/\s*0|99%|1 of 5|second sitting/);
  assert.equal(a.medalCalls(),0);
});

test('grading history distinguishes untimed submissions and retains a real zero score',async()=>{
  const a=app(),s=qualitativeSession(),host=a.host();
  const timed={id:78,comp:'ipho',year:2024,tasks:['E1'],review_only:false,status:'graded',score:0,points:20};
  const calls=[];
  a.context.cmApi=async(method,route)=>{calls.push(route);return route.startsWith('/lab/bootstrap?')?{user:{nickname:'Student'},active:null,tokens:2,parts:0,sessions:[s,timed]}:{};};
  await a.context.arLabList(host,()=>true);
  assert.ok(host.innerHTML.includes('Feedback complete · no score'));
  assert.ok(host.innerHTML.includes('Grading & feedback'));
  assert.ok(host.innerHTML.includes('Timed attempt'));
  assert.ok(host.innerHTML.includes('0 / 20'));
  assert.doesNotMatch(host.innerHTML,/null\s*\/|0\s*\/\s*0/);
  assert.equal(calls.filter(route=>route.startsWith('/lab/bootstrap?')).length,1);
  assert.ok(!calls.includes('/lab/tokens'),'The ledger waits until it is opened.');
});

test('scored review-only reports keep the earned score but suppress timed standing',async()=>{
  const a=app('ko'),s=qualitativeSession(),host=a.host();
  s.comp='opho';s.score=0;s.points=10;s.detail={tasks:{}};
  a.context.cmApi=async()=>({session:s});
  await a.context.arLabOne(host,()=>true,s.id);
  assert.ok(host.innerHTML.includes('채점·첨삭'));
  assert.ok(host.innerHTML.includes('0 / 10'));
  assert.ok(host.innerHTML.includes('접수번호'));
  assert.ok(host.innerHTML.includes('#/opho/review'));
  assert.doesNotMatch(host.innerHTML,/99%|5명 중 1위|다시 응시한 시험/);
  assert.equal(a.medalCalls(),0);
});

test('account grading payment sends the selected provider and cannot continue under a changed account',async()=>{
  const a=app(),s=qualitativeSession(),nodes=new Map(),calls=[];let auth='owner-A',finish;
  s.status='ended';s.provider='gemini';s.provider_locked=false;s.vision={providers:[{id:'deepseek',available:true,model:'PRIVATE_MODEL'},{id:'gemini',available:true}]};
  a.context.cmBase=()=> 'https://api.test';a.context.cmTok=()=>auth;a.context.cm.me.id=1;
  const node=key=>{if(!nodes.has(key))nodes.set(key,{value:'gemini',disabled:false,textContent:''});return nodes.get(key);};
  const host={innerHTML:'',querySelector:node,querySelectorAll:()=>[]};
  a.context.cmApi=(method,path,body)=>{calls.push({method,path,body});return new Promise(resolve=>finish=resolve);};
  await a.context.arLabOne(host,()=>true,s.id,s);assert.ok(!host.innerHTML.includes('PRIVATE_MODEL'));
  node('[data-vision-provider]').value='deepseek';const pending=node('#arLabPay').onclick();assert.equal(calls[0].body.provider,'deepseek');assert.equal(node('[data-vision-provider]').disabled,true);
  auth='owner-B';finish({});await pending;assert.equal(calls.length,1,'a completed old payment cannot refresh or initiate another action for the new account');
});

test('failed owner OCR retries only on an explicit click using the saved provider and no payment request',async()=>{
  const a=app('ko'),s=qualitativeSession(),nodes=new Map(),calls=[];let resolve;
  Object.assign(s,{status:'pending',paid:true,provider:'deepseek',provider_locked:true,pages:[{id:8,no:1,task:'T',kind:'answer',ocr_status:'failed',ocr_error:'vision_provider_failed'}]});
  a.context.cm.me.id=1;a.context.cm.me.tokens=7;a.context.cmBase=()=> 'https://api.test';a.context.cmTok=()=> 'owner';
  const node=id=>{if(!nodes.has(id))nodes.set(id,{disabled:false,textContent:''});return nodes.get(id);};
  const host={innerHTML:'',querySelector:node,querySelectorAll:()=>[]};
  a.context.cmApi=(method,path,body)=>{calls.push({method,path,body});return new Promise(done=>resolve=done);};
  await a.context.arLabOne(host,()=>true,s.id,s);
  assert.match(host.innerHTML,/실패한 판독 다시 시도 · 추가 토큰 없음/);assert.equal(calls.length,0);
  const button=node('#arLabRetryOcr'),first=button.onclick();await button.onclick();
  assert.equal(button.disabled,true);assert.equal(calls.length,1);
  assert.equal(calls[0].path,'/lab/sessions/77/retry-ocr');assert.equal(calls[0].method,'POST');assert.equal(calls[0].body.provider,'deepseek');
  resolve({session:{...s,status:'grading',pages:s.pages.map(p=>({...p,ocr_status:'queued'}))},tokens:7});await first;
  assert.doesNotMatch(host.innerHTML,/id="arLabRetryOcr"/);assert.equal(a.context.cm.me.tokens,7);assert.equal(calls.length,1);
});

test('unpaid, active, completed or provider-less records do not offer a no-token OCR retry',async()=>{
  for(const change of [{paid:false},{status:'running'},{status:'scanning'},{status:'grading'},{status:'graded'},{provider:null},{pages:[]}]){
    const a=app(),s={...qualitativeSession(),status:'pending',paid:true,provider:'deepseek',pages:[{id:8,no:1,task:'T',ocr_status:'failed'}],...change},host=a.host();
    a.context.cmApi=async()=>assert.fail('opening a record cannot retry or charge');
    await a.context.arLabOne(host,()=>true,s.id,s);
    assert.doesNotMatch(host.innerHTML,/id="arLabRetryOcr"/,JSON.stringify(change));
  }
});

test('an owner OCR retry result cannot render after account or route changes, and failures allow an explicit retry',async()=>{
  for(const leave of ['account','route','error']){
    const a=app(),s={...qualitativeSession(),status:'error',paid:true,provider:'deepseek',pages:[{id:8,no:1,task:'T',ocr_status:'failed'}]},nodes=new Map();let auth='owner',alive=true,finish,reject,calls=0;
    a.context.cm.me.id=1;a.context.cmBase=()=> 'https://api.test';a.context.cmTok=()=>auth;
    const node=id=>{if(!nodes.has(id))nodes.set(id,{disabled:false,textContent:''});return nodes.get(id);};
    const host={innerHTML:'',querySelector:node,querySelectorAll:()=>[]};
    a.context.cmApi=()=>{calls++;return new Promise((resolve,no)=>{finish=resolve;reject=no;});};
    await a.context.arLabOne(host,()=>alive,s.id,s);const before=host.innerHTML,pending=node('#arLabRetryOcr').onclick();
    if(leave==='account')auth='other';
    if(leave==='route')alive=false;
    if(leave==='error'){reject({code:'vision_provider_credits'});await pending;assert.equal(node('#arLabRetryOcr').disabled,false);assert.match(node('#arLabRetryOcrMsg').textContent,/API credit/);}
    else {finish({session:{...s,status:'graded',nickname:'LATE_PRIVATE_DATA'}});await pending;assert.equal(host.innerHTML,before);assert.doesNotMatch(host.innerHTML,/LATE_PRIVATE_DATA/);}
    assert.equal(calls,1);
  }
});
