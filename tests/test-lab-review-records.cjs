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

test('a report is shown in the language the exam was sat in, whatever the page language, and the page language comes back',async()=>{
  const a=app('en'),s=qualitativeSession(),host=a.host();
  s.lang='ko';s.comp='ipho';s.review_only=false;s.score=1;s.points=2;
  s.detail={tasks:{T:{status:'graded',score:1,points:2,items:[{id:'A.1',what:'번역된 요구 사항',points:2,got:1,decision:'partial',by:'model',rules:[],note:'한국어 첨삭'}],feedback:[]}}};
  a.context.cmApi=async()=>({session:s});
  await a.context.arLabOne(host,()=>true,s.id);
  assert.ok(host.innerHTML.includes('실전 응시'),'labels in Korean for a Korean sitting');
  assert.ok(host.innerHTML.includes('부분'),'decisions in Korean');
  assert.ok(!host.innerHTML.includes('Timed attempt'));
  await Promise.resolve();
  assert.equal(a.context.lang,'en','the page keeps its own language after the report is drawn');
  const b=app('ko'),t=qualitativeSession(),host2=b.host();t.lang='en';
  b.context.cmApi=async()=>({session:t});
  await b.context.arLabOne(host2,()=>true,t.id);
  assert.ok(host2.innerHTML.includes('Grading & feedback')&&!host2.innerHTML.includes('채점·첨삭'),'an English sitting reads in English on a Korean page');
  await Promise.resolve();assert.equal(b.context.lang,'ko');
});

test('a sitting that is still being read or graded offers cancelling, and cancelling posts once after a no-refund confirmation',async()=>{
  const a=app('ko'),s=qualitativeSession(),nodes=new Map(),calls=[];
  s.status='grading';s.lang='ko';s.detail={tasks:{}};
  const node=key=>{if(!nodes.has(key))nodes.set(key,{disabled:false});return nodes.get(key);};
  const host={innerHTML:'',querySelector:node,querySelectorAll:()=>[]};
  let confirmed='';a.context.confirm=text=>{confirmed=text;return true;};a.context.cmToast=()=>{};
  a.context.cmApi=async(method,path)=>{calls.push(method+' '+path);return{session:{...s,status:'cancelled'}};};
  await a.context.arLabOne(host,()=>true,s.id,s);
  assert.ok(host.innerHTML.includes('채점 취소'));
  await node('#arLabCancel').onclick();
  assert.match(confirmed,/돌려받을 수 없습니다/);assert.deepEqual(calls,['POST /lab/sessions/77/cancel']);
  assert.ok(host.innerHTML.includes('채점 취소됨'));assert.ok(!host.innerHTML.includes('id="arLabCancel"'),'a cancelled sitting offers no second cancel');
});

test('developers alone see each grading\'s AI tokens, cost and time, by step, by task and per call',async()=>{
  const a=app('ko'),s=qualitativeSession(),host=a.host();
  a.context.cmApi=async()=>({session:s});
  await a.context.arLabOne(host,()=>true,s.id);
  assert.doesNotMatch(host.innerHTML,/개발자 전용/,'a student never sees the cost section');
  a.context.cm.me={nickname:'Admin',role:'admin'};
  await a.context.arLabOne(host,()=>true,s.id);
  assert.match(host.innerHTML,/개발자 전용: 이 채점의 AI 토큰 · 비용 · 시간/);
  const calls=[{id:1,task:'T',page_id:5,step:'ocr',provider:'gemini',model:'gemini-3.5-flash-lite',in_tok:1700,cached_tok:0,out_tok:900,usd:.0028,ms:3800,ok:1},
    {id:2,task:'T',page_id:null,step:'grade',provider:'gemini',model:'gemini-3.5-flash-lite',in_tok:22000,cached_tok:4000,out_tok:3000,usd:.0145,ms:19000,ok:1}];
  a.context.cmApi=async(method,route)=>{assert.equal(route,'/admin/lab/77/calls');return{calls,total:{calls:2,failed:0,in_tok:23700,cached_tok:4000,out_tok:3900,usd:.0173,unknown_cost:0,ms:22800},
    by_step:{ocr:{calls:1,failed:0,in_tok:1700,cached_tok:0,out_tok:900,usd:.0028,unknown_cost:0,ms:3800},grade:{calls:1,failed:0,in_tok:22000,cached_tok:4000,out_tok:3000,usd:.0145,unknown_cost:0,ms:19000}},
    by_task:{T:{calls:2,failed:0,in_tok:23700,cached_tok:4000,out_tok:3900,usd:.0173,unknown_cost:0,ms:22800}}};};
  const box={innerHTML:'',textContent:'',className:''};
  await a.context.arLabDevCalls(box,77,'ko');
  for(const text of ['총 비용','$0.0173','23,700 / 4,000 / 3,900','22.8 s','단계별','과제별','호출 전체 (2)','gemini:gemini-3.5-flash-lite','T · p5'])assert.ok(box.innerHTML.includes(text),text);
});
