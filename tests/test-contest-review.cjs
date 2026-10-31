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
    assert.deepEqual(calls.map(c=>c.route),['/api/lab/bootstrap']);
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

test('queued OCR stays read-only and cannot be confirmed or submitted before it finishes',async()=>{
  const previous={document:global.document,window:global.window,location:global.location};let controller;
  global.location={href:'https://example.test/sim/contest-exam.html?id=kmo-example'};
  global.window={};global.document={hidden:false,addEventListener(){},removeEventListener(){}};
  try{
    let status='queued';const calls=[],session=()=>({id:12,examId:'kmo-example',status:'scanning',paid:true,scan_until:Date.now()/1000+1800,pages:[{id:34,no:1,task:'Q1',source:'scan',ocr_status:status,text:status==='done'?'Proof x = 1.':'',confirmed:false}]}),host=testHost();
    const fetch=async(url,opts)=>{calls.push({url,method:opts?.method});return url.endsWith('/img')?{ok:false}:{ok:true,json:async()=>({session:session(),tokens:2})};};
    controller=Review.mount(host,{id:'kmo-example',comp:'kmo',kind:'proof',questions:1},{session:session(),storage:{getItem:key=>key==='hlCmTok'?'test-token':null,setItem(){}},fetch});await new Promise(resolve=>setImmediate(resolve));
    assert.match(host.innerHTML,/판독을 진행 중/);assert.match(host.innerHTML,/data-cr-edit="34"[^>]*readonly[^>]*disabled/);assert.match(host.innerHTML,/data-cr-submit disabled/);
    await host.querySelector('[data-cr-submit]').onclick();assert.ok(calls.every(c=>c.method==='GET'));
    status='done';await controller.refresh();assert.ok(!host.innerHTML.includes('data-cr-submit disabled disabled'));assert.ok(!/data-cr-edit="34"[^>]*readonly/.test(host.innerHTML));
    host.querySelector('[data-cr-approved]').checked=true;host.querySelector('[data-cr-approved]').onchange({target:{checked:true}});await host.querySelector('[data-cr-submit]').onclick();
    assert.equal(calls.filter(c=>c.url.endsWith('/contest/sessions/12/confirm')).length,1);assert.equal(calls.filter(c=>c.url.endsWith('/submit')).length,1);assert.equal(calls.filter(c=>c.url.endsWith('/pay')).length,0);
  }finally{controller?.dispose();for(const[key,value]of Object.entries(previous)){if(value===undefined)delete global[key];else global[key]=value;}}
});

test('the account dashboard reads balances and sessions once and loads the ledger only when opened',async()=>{
  const vm=require('node:vm'),fs=require('node:fs'),calls=[],nodes=new Map(),host={innerHTML:'',querySelector(sel){return nodes.get(sel)||null;}},ledger={open:false,addEventListener(_name,fn){this.toggle=fn;}},ledgerBody={innerHTML:''};nodes.set('#lbLedger',ledger);nodes.set('#lbLedgerBody',ledgerBody);
  const context=vm.createContext({lang:'ko',cm:{me:{nickname:'Candidate'}},window:{},esc:x=>String(x??''),cmShort:()=>'',cmTok:()=> 'account-a',cmApi:async(method,path)=>{calls.push({method,path});return path.startsWith('/lab/bootstrap')?{user:{nickname:'Candidate'},tokens:4,parts:0,active:null,sessions:[]}:path==='/lab/tokens'?{ledger:[]}:{pay:null,paddle:null,ads:null};}});
  vm.runInContext(fs.readFileSync(require.resolve('../arena.js'),'utf8'),context);vm.runInContext('arShopWire=()=>{}',context);
  await context.arLabList(host,()=>true);assert.equal(calls.length,2);assert.ok(calls.some(c=>c.path==='/lab/bootstrap?include=sessions,health'));assert.ok(!calls.some(c=>c.path==='/lab/tokens'));
  ledger.open=true;await ledger.toggle();await ledger.toggle();assert.equal(calls.filter(c=>c.path==='/lab/tokens').length,1);
});

test('desktop queued photos retain unconfirmed originals through mode changes until explicit A4 corner confirmation',async()=>{
  const fs=require('node:fs'),vm=require('node:vm'),source=fs.readFileSync(require.resolve('../sim/contest-review.js'),'utf8');
  // Execute the actual queue renderer/controller with an injected scanner. No
  // browser image decoder or provider is needed to verify the transport intent.
  const code=source.slice(source.indexOf('    function queueHTML()'),source.indexOf('    function inspectQueue('))+
    source.slice(source.indexOf('    async function rebuildQueue('),source.indexOf('    function bindQueue('));
  const calls=[],encoded=[],revoked=[],corners=[{x:0,y:0},{x:400,y:0},{x:0,y:250},{x:400,y:250}];let urls=0;
  const original=new Blob(['original card pixels'],{type:'image/png'}),corrected=new Blob(['confirmed A4 pixels'],{type:'image/png'});
  const item={name:'answer.png',url:'blob:initial',task:'Q5',mode:'clean',source:original,blob:original,scan:{blob:original,baseUrl:'data:original',corners,method:'page',autoScore:.98,cornersReliable:false,paperStatus:'aspect_mismatch',a4WarpApplied:false,quality:{ok:true}}};
  const scanner={MARKER_INSET:{left:.045},async reprocess(...args){calls.push(args);return{blob:corrected};},async encodeUpload(blob,options){encoded.push({blob,options});return blob;}};
  const context=vm.createContext({scannerLibrary:async()=>scanner,MAX_IMAGE:1850000,queue:[item],busy:'',tr:(_ko,en)=>en,taskOptions:()=>'',escape:value=>String(value),
    URL:{revokeObjectURL:url=>revoked.push(url),createObjectURL:()=>`blob:rebuilt-${++urls}`}});
  vm.runInContext(code+'\nglobalThis.queueController={rebuildQueue,queueHTML};',context);const ui=context.queueController;
  assert.match(ui.queueHTML(),/original image is retained/);
  for(const mode of ['mono','original','clean']) {
    await ui.rebuildQueue(item,{mode});const args=calls.at(-1);
    assert.equal(args[0],'data:original');assert.equal(args[1],corners);assert.equal(args[2],mode);assert.equal(args[5].preserveOriginal,true);
    assert.equal(item.scan.a4WarpApplied,false);assert.equal(item.scan.paperStatus,'aspect_mismatch');assert.equal(item.scan.method,'page','a mode change is not manual corner confirmation');
    assert.equal(item.scan.cornersReliable,false);assert.match(ui.queueHTML(),/original image is retained/);
  }
  const confirmed=corners.map(point=>({...point}));await ui.rebuildQueue(item,{corners:confirmed,marker:false,pageFormat:'a4'});
  assert.equal(calls.at(-1)[5].preserveOriginal,false);assert.equal(item.scan.cornersReliable,true);assert.equal(item.scan.autoScore,1);
  assert.equal(item.scan.paperStatus,'manual_a4');assert.equal(item.scan.a4WarpApplied,true);assert.equal(item.scan.method,'manual');
  assert.equal(item.scan.warpApplied,true);assert.equal(item.scan.outputFormat,'a4');assert.equal(calls.at(-1)[5].pageFormat,'a4');
  assert.doesNotMatch(ui.queueHTML(),/original image is retained|Check the corners and adjust/);
  await ui.rebuildQueue(item,{mode:'mono'});assert.equal(calls.at(-1)[5].preserveOriginal,false);assert.equal(item.scan.paperStatus,'manual_a4');assert.equal(item.scan.method,'manual');
  assert.ok(encoded.every(call=>call.options.maxBytes===1850000));assert.equal(revoked.length,5);
  item.scan={...item.scan,a4WarpApplied:undefined,paperStatus:undefined,cornersReliable:false,autoScore:.99};assert.match(ui.queueHTML(),/Check the corners and adjust/,'high geometry scores do not hide uncertain-corner warnings');
  item.scan.cornersReliable=true;assert.doesNotMatch(ui.queueHTML(),/Check the corners and adjust/);
  item.scan={...item.scan,warpApplied:true,a4WarpApplied:false,outputFormat:'auto'};assert.doesNotMatch(ui.queueHTML(),/original image is retained/,'auto-aspect correction is a valid completed warp');
});

test('KMO selection sends only provider IDs through start, payment, OCR and final review, then obeys the server lock',async()=>{
  const prior={window:global.window,document:global.document,location:global.location};let controller;
  global.location={href:'https://example.test/sim/contest-exam.html?id=kmo-example'};
  global.window={qrcode:()=>({addData(){},make(){},createSvgTag:()=>'<svg></svg>'})};global.document={head:{append(){}},body:{append(){}},createElement:testHost};
  const host=testHost(),calls=[],vision={default:'gemini',providers:[{id:'deepseek',available:true,model:'PRIVATE_MODEL_A'},{id:'gemini',available:true,model:'PRIVATE_MODEL_B'}]};let paid=false,selected='gemini';
  const session=()=>({id:12,examId:'kmo-example',status:'scanning',paid,provider:selected,provider_locked:paid,scan_until:Date.now()/1000+1800,pages:[{id:34,no:1,task:'Q1',source:'typed',confirmed:true,text:'Proof',ocr_status:'done'}]});
  const fetch=async(url,options)=>{const route=new URL(url).pathname,body=options.body?JSON.parse(options.body):null;calls.push({route,body});
    if(route.endsWith('/bootstrap'))return{ok:true,json:async()=>({tokens:3,health:{vision}})};
    if(route.endsWith('/start'))selected=body.provider;if(route.endsWith('/pay')){paid=true;selected=body.provider;}
    return{ok:true,json:async()=>({session:session(),vision,token:route.endsWith('/start')?'server-upload-grant':undefined,tokens:3})};};
  try {
    controller=Review.mount(host,{id:'kmo-example',comp:'kmo',kind:'proof',questions:1},{storage:{getItem:key=>key==='hlCmTok'?'owner-token':null,setItem(){}},fetch});await new Promise(done=>setImmediate(done));
    assert.deepEqual([...host.innerHTML.matchAll(/<option[^>]*>([^<]+)<\/option>/g)].map(match=>match[1]),['deepseek','gemini']);assert.ok(!host.innerHTML.includes('PRIVATE_MODEL_'));
    const field=host.querySelector('[data-cr-provider]');assert.equal(field.value,'gemini');field.value='deepseek';field.onchange();assert.equal(calls.length,1,'choosing a provider cannot run OCR or use tokens');
    await host.querySelector('[data-cr-start]').onclick();assert.equal(calls.find(call=>call.route.endsWith('/start')).body.provider,'deepseek');
    await host.querySelector('[data-cr-pay]').onclick();assert.equal(host.querySelector('[data-cr-provider]').disabled,true);
    const locked=host.querySelector('[data-cr-provider]');locked.value='gemini';locked.onchange();assert.equal(locked.value,'deepseek');
    host.querySelector('[data-cr-approved]').onchange({target:{checked:true}});await host.querySelector('[data-cr-submit]').onclick();
    for(const suffix of ['/pay','/read','/submit'])assert.equal(calls.find(call=>call.route.endsWith(suffix)).body.provider,'deepseek',suffix);
    assert.ok(calls.filter(call=>call.route.includes('/qr')).every(call=>!call.body?.provider),'QRs retain the authoritative server session rather than a client override');
  } finally {controller?.dispose();for(const[key,value]of Object.entries(prior)){if(value===undefined)delete global[key];else global[key]=value;}}
});

test('a stale KMO payment completion cannot start OCR after account switching or route disposal',async()=>{
  for(const leave of ['account','route']) {
    const prior={window:global.window,document:global.document,location:global.location};let controller,finish,auth='owner-A';const calls=[];
    global.location={href:'https://example.test/sim/contest-exam.html?id=kmo-example'};global.window={};global.document={head:{append(){}},body:{append(){}},createElement:testHost};
    const session={id:12,examId:'kmo-example',status:'scanning',paid:false,provider:'deepseek',provider_locked:false,scan_until:Date.now()/1000+1800,pages:[{id:34,no:1,task:'Q1',source:'typed',confirmed:true,text:'Proof',ocr_status:'done'}]};
    const vision={providers:[{id:'deepseek',available:true},{id:'gemini',available:true}]},host=testHost();
    const fetch=async(url,options)=>{calls.push({url,options});if(url.endsWith('/pay'))return new Promise(resolve=>finish=()=>resolve({ok:true,json:async()=>({session:{...session,paid:true,provider_locked:true},vision})}));return{ok:true,json:async()=>({session,vision,tokens:3})};};
    try {
      controller=Review.mount(host,{id:'kmo-example',comp:'kmo',kind:'proof',questions:1},{session,storage:{getItem:key=>key==='hlCmTok'?auth:null,setItem(){}},fetch});await new Promise(done=>setImmediate(done));
      const pending=host.querySelector('[data-cr-pay]').onclick();await new Promise(done=>setImmediate(done));assert.equal(typeof finish,'function');
      if(leave==='account')auth='owner-B';else controller.dispose();finish();await pending;
      assert.equal(calls.filter(call=>call.url.endsWith('/read')).length,0);assert.equal(calls.find(call=>call.url.endsWith('/pay')).options.headers.Authorization,'Bearer owner-A');
      assert.equal(JSON.parse(calls.find(call=>call.url.endsWith('/pay')).options.body).provider,'deepseek');
    } finally {controller?.dispose();for(const[key,value]of Object.entries(prior)){if(value===undefined)delete global[key];else global[key]=value;}}
  }
});
