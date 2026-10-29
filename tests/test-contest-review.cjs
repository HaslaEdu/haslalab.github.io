const test=require('node:test');
const assert=require('node:assert/strict');
const Review=require('../sim/contest-review.js');

function transport(){
  const calls=[];
  const client=Review.createClient({getBase:()=> 'https://example.test/',getToken:()=> 'test-only-token',fetch:async(url,options)=>{calls.push({url,...options});return{ok:true,json:async()=>({session:{id:12},tokens:4})};}});
  return{client,calls};
}

test('loading the review client never creates or charges a session',()=>{
  const {calls}=transport();assert.equal(calls.length,0);
});

test('a review start uses the review purpose and authoritative exam ID while sending the shared account token in a header',async()=>{
  const {client,calls}=transport();
  await client.start({examId:'kmo-2025-T2-s2',purpose:'exam',runId:'local-run-1'});
  assert.equal(calls[0].url,'https://example.test/api/lab/contest/start');
  assert.equal(calls[0].headers.Authorization,'Bearer test-only-token');
  assert.deepEqual(JSON.parse(calls[0].body),{examId:'kmo-2025-T2-s2',purpose:'review',runId:'local-run-1'});
  assert.ok(!calls[0].url.includes('test-only-token'));
});

test('typed local answers map to actual second-session question numbers and retain mathematical text',()=>{
  const entry={questions:4,questionOffset:4};
  assert.deepEqual(Review.taskNumbers(entry),[5,6,7,8]);
  assert.deepEqual(Review.mapAnswers(entry,{1:'Let x = 0.\nTherefore x² = 0.',2:' ',3:'증명 끝.',99:'unrelated'}),{5:'Let x = 0.\nTherefore x² = 0.',7:'증명 끝.'});
  assert.equal(Review.mapAnswers({questions:1},{1:'x'.repeat(51000)})[1].length,50000);
});

test('reading scanned work and final submission use separate endpoints after the explicit charge operation',async()=>{
  const {client,calls}=transport();
  await client.pay(12);await client.read(12);await client.confirm(12,34,'corrected OCR','Q5');await client.submit(12);
  assert.deepEqual(calls.map(c=>c.url.split('/api')[1]),['/lab/sessions/12/pay','/lab/contest/sessions/12/read','/lab/contest/sessions/12/pages/34/confirm','/lab/sessions/12/submit']);
  assert.deepEqual(JSON.parse(calls[2].body),{text:'corrected OCR',task:'Q5'});
  assert.deepEqual(JSON.parse(calls[3].body),{grade:true});
});

test('upload bytes stay binary and the scan code goes in its dedicated header',async()=>{
  const {client,calls}=transport(),blob=new Blob(['scan'],{type:'image/jpeg'});
  await client.upload('scan-test-code','Q6',blob);
  assert.equal(calls[0].method,'PUT');assert.equal(calls[0].body,blob);
  assert.equal(calls[0].headers['X-Lab-Token'],'scan-test-code');
  assert.equal(calls[0].headers['Content-Type'],'image/jpeg');
  assert.equal(calls[0].url,'https://example.test/api/lab/up/pages?task=Q6&kind=answer');
  assert.ok(!calls[0].url.includes('scan-test-code'));
});

test('invalid session IDs cannot reach the network and each local attempt keeps a distinct link',async()=>{
  const {client,calls}=transport();
  assert.throws(()=>client.get('../other-user'),e=>e.code==='bad_session');
  assert.throws(()=>client.confirm(12,'0','x','Q5'),e=>e.code==='bad_session');
  assert.equal(calls.length,0);
  assert.notEqual(Review.storageKey({id:'kmo-2025-T2-s2'},'run-a'),Review.storageKey({id:'kmo-2025-T2-s2'},'run-b'));
});

test('server failures preserve the token and ownership error codes without inventing successful results',async()=>{
  const client=Review.createClient({fetch:async()=>({ok:false,status:409,json:async()=>({error:'no_tokens',tokens:0})})});
  await assert.rejects(client.pay(12),e=>e.code==='no_tokens'&&e.tokens===0&&e.status===409);
  const offline=Review.createClient({fetch:async()=>{throw Error('offline');}});
  await assert.rejects(offline.active(),e=>e.code==='network');
});

function testHost(){
  return{innerHTML:'',isConnected:true,classList:{add(){}},nodes:new Map(),querySelector(selector){
    const attr=selector.match(/^\[([^=\]]+)\]$/)?.[1];
    if(!attr||!this.innerHTML.includes(attr))return null;
    if(!this.nodes.has(selector))this.nodes.set(selector,testHost());
    return this.nodes.get(selector);
  },querySelectorAll(){return[];},insertAdjacentHTML(_where,html){this.innerHTML+=html;}};
}

test('mount and open preparation never spend tokens; only the explicit one-token button pays and reads',async()=>{
  const host=testHost(),calls=[],dialogs=[];
  const original={window:global.window,document:global.document,location:global.location};
  global.location={href:'https://example.test/sim/contest-exam.html?id=kmo-example'};
  global.window={qrcode:()=>({addData(){},make(){},createSvgTag:()=>'<svg></svg>'})};
  global.document={head:{append(){}},body:{append(d){dialogs.push(d);}},createElement:()=>Object.assign(testHost(),{open:false,showModal(){this.open=true;},close(){this.open=false;},remove(){}})};
  let paid=false,controller;
  const session=()=>({id:12,examId:'kmo-example',status:'scanning',paid,scan_until:Date.now()/1000+1800,now:Date.now()/1000,pages:[{id:34,no:1,task:'Q5',source:'typed',confirmed:true,text:'Proof',ocr_status:'done'}]});
  const storage={getItem:k=>k==='hlCmTok'?'test-only-token':null,setItem(){},removeItem(){}};
  const fetch=async(url,opts={})=>{
    const route=new URL(url).pathname;calls.push({route,method:opts.method||'GET'});
    if(route.endsWith('/img'))return{ok:false};
    if(route.endsWith('/pay'))paid=true;
    const value=route.endsWith('/active')?{tokens:3}:route.endsWith('/contest/start')?{session:session(),token:'test-scan-code',tokens:3}:{session:session(),tokens:paid?2:3};
    return{ok:true,json:async()=>value};
  };
  try{
    controller=Review.mount(host,{id:'kmo-example',comp:'kmo',kind:'proof',questions:4,questionOffset:4},{runId:'mock-run',storage,fetch,answers:{1:'Proof'}});
    await new Promise(resolve=>setImmediate(resolve));
    assert.deepEqual(calls.map(c=>c.route),['/api/lab/active']);
    await host.querySelector('[data-cr-start]').onclick();
    assert.ok(calls.some(c=>c.route.endsWith('/contest/start')));
    assert.ok(!calls.some(c=>c.route.endsWith('/pay')));
    await host.querySelector('[data-cr-pay]').onclick();
    assert.equal(dialogs.length,0);
    assert.equal(calls.filter(c=>c.route.endsWith('/pay')).length,1);
    assert.equal(calls.filter(c=>c.route.endsWith('/read')).length,1);
    assert.ok(!calls.some(c=>c.route.endsWith('/submit')));
  }finally{
    controller?.dispose();
    for(const [key,value]of Object.entries(original)){if(value===undefined)delete global[key];else global[key]=value;}
  }
});

test('sign-in return is saved only on the explicit login click and an expired login shows that link again',async()=>{
  const prior={location:global.location,sessionStorage:global.sessionStorage},stored=new Map();
  global.location={href:'https://example.test/sim/contest-exam.html?id=kmo-example'};
  global.sessionStorage={setItem:(key,value)=>stored.set(key,value)};
  let controller;
  try{
    const host=testHost();
    controller=Review.mount(host,{id:'kmo-example',comp:'kmo',kind:'proof',questions:4},{storage:{getItem:()=> 'expired-token'},fetch:async()=>({ok:false,status:401,json:async()=>({error:'login_required'})})});
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(stored.size,0);
    assert.ok(host.innerHTML.includes('../#/community/login'));
    host.querySelector('[data-cr-login]').onclick();
    assert.equal(stored.get('hlCmBack'),'#/kmo/exam');
    assert.equal(stored.get('hlContestReviewBack'),global.location.href);
  }finally{
    controller?.dispose();
    for(const [key,value]of Object.entries(prior)){if(value===undefined)delete global[key];else global[key]=value;}
  }
});

test('a returned server review opens without a local attempt or new charge and cannot attach a different exam',async()=>{
  const prior=global.location;
  let controller;
  try{
    global.location={href:'https://example.test/sim/contest-exam.html?id=kmo-example&review=37'};
    const calls=[],entry={id:'kmo-example',comp:'kmo',kind:'proof',questions:4},host=testHost();
    let serverExam='kmo-example';
    const options={storage:{getItem:key=>key==='hlCmTok'?'test-token':null,setItem(){}},fetch:async(url,opts)=>{
      calls.push({url,method:opts.method});
      return{ok:true,json:async()=>url.endsWith('/active')?{tokens:3}:{tokens:3,session:{id:37,examId:serverExam,status:'pending',pages:[]}}};
    }};
    controller=Review.mount(host,entry,options);
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(controller.getSession().id,37);
    assert.equal(controller.getSession().examId,entry.id);
    assert.ok(calls.some(c=>c.url.endsWith('/lab/sessions/37')));
    assert.ok(calls.every(c=>c.method==='GET'));
    controller.dispose();
    serverExam='kmo-other';
    controller=Review.mount(host,entry,{...options,reviewId:37});
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(controller.getSession().examId,undefined);
    assert.ok(host.innerHTML.includes('cr-alert'));
    controller.dispose();calls.length=0;
    controller=Review.mount(host,entry,{...options,reviewId:'37/other'});
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(calls.length,0);
  }finally{controller?.dispose();if(prior===undefined)delete global.location;else global.location=prior;}
});

test('account records reopen contest review and show math-review rules instead of experimental-physics payment',async()=>{
  const vm=require('node:vm'),fs=require('node:fs'),context=vm.createContext({lang:'ko',cm:{me:{nickname:'Test'}},DATA:{},window:{},
    esc:x=>String(x??''),cmFull:()=> '2026-10-30 12:00',URLSearchParams,encodeURIComponent});
  vm.runInContext(fs.readFileSync(require.resolve('../arena.js'),'utf8'),context);
  vm.runInContext('arMath=()=>{}',context);
  const session={id:37,comp:'kmo',purpose:'review',examId:'kmo-example',year:2025,tasks:['Q5'],kind:'theory',status:'ended',
    started_at:1,pages:[],regulation:{version:'kmo-proof-review-1',rules:[{id:'M4',ko:'OCR 원본을 대조합니다.'}]},detail:{tasks:{}}};
  context.cmApi=async()=>({session});
  const host=testHost();await context.arLabOne(host,()=>true,37);
  assert.ok(host.innerHTML.includes('sim/contest-exam.html?id=kmo-example&review=37&lang=ko'));
  assert.ok(host.innerHTML.includes('공식 KMO 채점이 아닙니다'));
  assert.ok(host.innerHTML.includes('관리자 검토'));
  assert.ok(!host.innerHTML.includes('id="arLabPay"'));
  assert.ok(!host.innerHTML.includes('sim/exam.html'));
  assert.equal(context.arLabHref({entry:'?c=ipho&y=2024'}),'sim/exam.html?c=ipho&y=2024&lang=ko');
});
