const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '..', 'arena.js'), 'utf8');
const deadline = 1796050800; // 2026-12-01 00:00 KST, exclusive submission cutoff.
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
const clone = value => JSON.parse(JSON.stringify(value));
const problem = {id:4, no:1, title:'Test problem', kind:'essay', subject:'Physics', level:10,
  points:100, closes_at:deadline, month:'2026-11', open:true, body:'Problem statement',
  attempts:{limit:3,used:0,remaining:3}, answerSheet:{version:'2026-11-v1',parts:[{id:'a',points:100,label_ko:'운동',label_en:'Motion'}]}};
const grade = {status:'graded',score:73,detail:{grader:'private-grader', evidenceIssue:true,
  scores:[{id:'private-id',name:'private-criterion',note:'private-note',got:73,max:100,decision:'partial',evidence:['private-evidence']}],
  feedback:[{kind:'fix',quote:'private-quote',note:'private-correction'}],note:'private-overall'}};
function app() {
  let now = (deadline-60)*1000, auth = 'owner-token', serial = 0;
  const storage = new Map(), listeners = new Map(), revoked = [];
  class AppDate extends Date {static now(){return now;}}
  const context = {lang:'ko',esc,Date:AppDate,cm:{me:{id:10,username:'student'}},cmBase:()=> 'https://api.test',cmTok:()=>auth,
    cmErr:error=>error?.code||'error',cmFull:()=> 'date',setTimeout:()=>1,clearTimeout(){},AbortController,Blob,FormData,
    localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},
    crypto:{randomUUID:()=> 'request-id'},URL:{createObjectURL:()=> 'blob:private-'+(++serial),revokeObjectURL:url=>revoked.push(url)},
    window:{addEventListener:(name,fn)=>{if(!listeners.has(name))listeners.set(name,new Set());listeners.get(name).add(fn);},removeEventListener:(name,fn)=>listeners.get(name)?.delete(fn)}};
  vm.createContext(context);vm.runInContext(source,context);context.arMath=()=>{};
  return {context,storage,revoked,setNow:value=>{now=value;},setAuth:value=>{auth=value;},emit:name=>{for(const fn of [...(listeners.get(name)||[])])fn();}};
}

test('monthly results reveal only total score until the exact release time, including stale cached details',()=>{
  const {context,setNow}=app();
  let html=context.arResult(grade,problem);
  assert.match(html,/73 \/ 100점/);assert.match(html,/2026\.12\.01 00:00 \(한국 시각\)/);
  assert.match(html,/마감 후/);assert.ok(!html.includes('private-'));assert.ok(!html.includes('artbl'));
  setNow(deadline*1000);
  html=context.arResult({...grade,feedback_held:false},problem);
  assert.match(html,/private-correction/);assert.match(html,/private-evidence/);
  html=context.arResult({...grade,feedback_held:true,feedback_available_at:deadline},problem);
  assert.ok(!html.includes('private-'),'the server can continue withholding a result');
});

test('server release flags cannot make cached monthly details visible before the problem deadline',()=>{
  const {context}=app();
  const html=context.arResult({...grade,feedback_held:false,feedback_available_at:deadline-1000},problem);
  assert.ok(!html.includes('private-'));assert.match(html,/73 \/ 100점/);
});

test('the immediate-feedback IPhO and legacy grading views remain available',()=>{
  const {context}=app();
  assert.match(context.arResult(grade,{points:100}),/private-correction/);
  assert.match(context.arResult({status:'graded',score:100,detail:{kind:'short',ok:true}},{points:100}),/정답입니다/);
});

test('suspected AI writing consumes an attempt without showing a zero or private assessment evidence',()=>{
  const {context,setNow}=app();setNow((deadline+100)*1000);
  const html=context.arResult({...grade,status:'ai_suspected',score:null},problem);
  assert.match(html,/AI 작성 의심/);assert.match(html,/제출 기회 1회 사용/);assert.match(html,/오판 가능성/);
  assert.ok(!html.includes('private-'));assert.ok(!html.includes('null'));assert.ok(!html.includes('/ 100'));
  assert.match(vm.runInContext('AT.ko.ai_suspected',context),/의심/);
  context.lang='en';assert.match(context.arResult({status:'ai_suspected',score:null},problem),/Suspected AI writing/);
});

test('both languages explain delayed corrections, false positives, handwritten work and server retention before submission',()=>{
  const {context}=app();
  const ko=context.arMonthlyAnswerHtml(problem,true);
  assert.match(ko,/총점만/);assert.match(ko,/2026\.12\.01 00:00/);assert.match(ko,/오판/);
  assert.match(ko,/본인이 직접 푼 손글씨/);assert.match(ko,/사진만으로 작성자를 확인할 수는 없습니다/);
  assert.match(ko,/답안과 업로드한 답안 사진은 서버에 보관/);
  assert.ok(ko.indexOf('AI 판별')<ko.indexOf('<form'));
  context.lang='en';const en=context.arMonthlyAnswerHtml(problem,true);
  assert.match(en,/total score/);assert.match(en,/false positives/);assert.match(en,/own handwritten solution/);
  assert.match(en,/stored on the server/);assert.match(en,/2026\.12\.01 00:00 KST/);
});

test('native monthly provenance is absent from the header while other contest attribution remains',async()=>{
  const {context}=app();context.cm.me=null;context.arBindMonthlyAnswer=()=>{};
  const root={innerHTML:'',querySelector:()=>null};
  context.cmApi=async()=>({problem:{...problem,source:'xPhO 2026 Week 1 · Carina · 제공 자료 번역·웹 편집'},health:{ocr:false}});
  await context.arProblem(root,()=>true,4);assert.ok(!root.innerHTML.includes('Carina'));
  context.cmApi=async()=>({problem:{...problem,answerSheet:null,source:'Official contest attribution'},health:{ocr:false}});
  await context.arProblem(root,()=>true,4);assert.match(root.innerHTML,/Official contest attribution/);
});

function binding(context,p=clone(problem),ocr=false,withModes=false) {
  const fields=new Map(),previews=new Map(),button={disabled:false},out={innerHTML:''},counter={textContent:''},provider={value:'gemini',disabled:false};
  const typedPanel={hidden:false},photoPanel={hidden:true};
  const modes=['typed','photo'].map(sheetMode=>({dataset:{sheetMode},classList:{toggle(){}},setAttribute(name,value){this[name]=value;}}));
  for(const part of p.answerSheet.parts)for(const kind of ['answer','working']){
    fields.set(`${kind}:${part.id}`,{value:'',disabled:false,dataset:{[kind==='working'?'sheetWorking':'sheetAnswer']:part.id}});
    previews.set(`${kind}:${part.id}`,{innerHTML:''});
  }
  const form={photo_part:{value:'a'},querySelector(selector){
    if(selector==='button[type=submit]')return button;
    if(selector==='[data-vision-provider]')return provider;
    if(selector==='.arsheet-typed')return typedPanel;if(selector==='.arsheet-photo')return photoPanel;
    let match=/^\[data-sheet-(answer|working)="([^"]+)"\]$/.exec(selector);if(match)return fields.get(`${match[1]}:${match[2]}`);
    match=/^\[data-sheet-(answer|working)-preview="([^"]+)"\]$/.exec(selector);if(match)return previews.get(`${match[1]}:${match[2]}`);
    throw Error('Unexpected selector '+selector);
  },querySelectorAll:selector=>selector.startsWith('[data-sheet-answer]')?[...fields.values()]:selector==='[data-sheet-mode]'&&withModes?modes:[]};
  const root={querySelector:selector=>({'#arSheetF':form,'#arOut':out,'#arSheetAttempts':counter}[selector])};
  context.arBindMonthlyAnswer(root,p,()=>true,ocr);
  return {form,fields,button,out,p,modes,typedPanel,photoPanel,provider};
}

test('legacy photographed draft attachments remain deduplicated when reopened in LaTeX mode',async()=>{
  const {context,storage}=app();let request;
  storage.set(context.arSheetDraftKey(problem),JSON.stringify({version:problem.answerSheet.version,
    parts:[{id:'a',answer:'42',working:'Previously recognized work'}],photos:[{id:'photo-1',part_id:'a'},{id:'photo-1',part_id:'a'}]}));
  context.cmApi=async(_method,_path,body)=>{request=clone(body);return{status:'graded',score:73,feedback_held:true,feedback_available_at:deadline,attempts:{limit:3,used:1,remaining:2}};};
  const restored=binding(context,clone(problem),false);
  await restored.form.onsubmit({preventDefault(){}});
  assert.deepEqual(request.photo_ids,['photo-1']);assert.equal(request.parts[0].id,'a');
  assert.match(restored.out.innerHTML,/73 \/ 100점/);assert.match(restored.out.innerHTML,/마감 후/);
});

test('the monthly form allows the longer review and locks one accepted suspicion until an edit',async()=>{
  const {context}=app();let finish,calls=0;
  context.cmApi=()=>{calls++;return new Promise(resolve=>{finish=resolve;});};
  const f=binding(context);
  f.fields.get('answer:a').value='42';f.fields.get('working:a').value='My derivation';f.fields.get('working:a').oninput();
  const pending=f.form.onsubmit({preventDefault(){}});
  assert.match(f.out.innerHTML,/최대 2분/);assert.equal(f.button.disabled,true);
  finish({status:'ai_suspected',score:null,attempts:{limit:3,used:1,remaining:2}});await pending;
  assert.equal(f.button.disabled,true);assert.equal(f.p.attempts.remaining,2);assert.match(f.out.innerHTML,/제출 기회 1회 사용/);
  await f.form.onsubmit({preventDefault(){}});assert.equal(calls,1);
  f.fields.get('working:a').value+=' corrected';f.fields.get('working:a').oninput();assert.equal(f.button.disabled,false);
});

test('photo mode is a separate exam scanner workspace and submits only its server-owned capture',async()=>{
  const {context}=app();let hooks,request;
  const scan={id:'capture-1',open:true,status:'scanning',revision:1,pages:[{id:'photo-1',ocr_status:'done'}],photo_ids:['photo-1'],parts:[{id:'a',answer:'99',working:'Recognized work'}]};
  context.arBindMonthlyCapture=(_form,_p,_alive,options)=>{hooks=options;return{snapshot:()=>scan,start(){hooks.onChange(scan);},resume(){},pause(){},refresh(){},setBusy(value){hooks.onBusy(value);}};};
  context.cmApi=async(_method,_path,payload)=>{request=clone(payload);return{...clone(grade),feedback_held:true,attempts:{limit:3,used:1,remaining:2}};};
  const f=binding(context,clone(problem),true,true);f.fields.get('answer:a').value='42';f.fields.get('working:a').value='Typed derivation';
  f.modes[1].onclick();assert.equal(f.typedPanel.hidden,true);assert.equal(f.photoPanel.hidden,false);assert.equal(f.button.disabled,false);
  await f.form.onsubmit({preventDefault(){}});
  assert.equal(request.scan_id,'capture-1');assert.equal(request.parts,undefined);assert.equal(request.photo_ids,undefined);assert.equal(request.via_ocr,undefined);
  assert.equal(f.fields.get('answer:a').value,'42','photo mode never overwrites the typed draft');
  assert.equal(f.button.disabled,true);f.modes[0].onclick();assert.equal(f.typedPanel.hidden,false);assert.equal(f.photoPanel.hidden,true);assert.equal(f.button.disabled,false);
});

test('a restored photo draft never creates a new phone grant until an explicit photo action',()=>{
  const {context,storage}=app();let starts=0,restores=0,resumes=0;
  storage.set(context.arSheetDraftKey(problem),JSON.stringify({version:problem.answerSheet.version,mode:'photo',scan_id:'saved-capture',
    parts:[{id:'a',answer:'Typed draft',working:'Preserved typed derivation'}]}));
  context.arBindMonthlyCapture=(_form,_p,_alive,options)=>{
    assert.equal(options.scanId,'saved-capture');
    return{snapshot:()=>null,start(){starts++;},restore(){restores++;},resume(){resumes++;},pause(){},setBusy(){}};
  };
  context.cmApi=()=>{throw Error('restoring a draft must not create a grant');};
  const f=binding(context,clone(problem),true,true);
  assert.equal(f.photoPanel.hidden,false);assert.equal(f.typedPanel.hidden,true);
  assert.equal(starts,0);assert.equal(restores,1);assert.equal(resumes,0);
  assert.equal(f.fields.get('answer:a').value,'Typed draft');
  f.modes[1].onclick();assert.equal(resumes,1,'only clicking the photo action resumes or creates a phone link');
  assert.equal(starts,0);
});

test('photo network retries retain the accepted request key even after the server closes the capture',async()=>{
  const {context}=app();let hooks,calls=0;const requests=[];
  const scan={id:'capture-1',open:true,status:'scanning',pages:[{id:'photo-1',ocr_status:'done'}],photo_ids:['photo-1'],parts:[{id:'a',answer:'99',working:'Recognized work'}]};
  context.arBindMonthlyCapture=(_f,_p,_a,options)=>{hooks=options;return{snapshot:()=>scan,start(){hooks.onChange(scan);},pause(){},resume(){},refresh(){},setBusy(value){hooks.onBusy(value);}};};
  context.cmApi=async(_m,_p,payload)=>{requests.push(clone(payload));if(++calls===1){scan.open=false;scan.status='submitted';hooks.onChange(scan);throw{code:'network'};}return{...clone(grade),attempts:{limit:3,used:1,remaining:2}};};
  const f=binding(context,clone(problem),true,true);f.modes[1].onclick();await f.form.onsubmit({preventDefault(){}});assert.equal(f.button.disabled,false);
  await f.form.onsubmit({preventDefault(){}});assert.equal(requests.length,2);assert.equal(requests[0].request_id,requests[1].request_id);assert.equal(requests[1].scan_id,'capture-1');
});

test('a late hidden photo poll cannot reset a LaTeX submission retry key',async()=>{
  const {context}=app();let hooks;const requests=[];
  const scan={id:'capture-1',open:true,status:'scanning',pages:[{ocr_status:'done'}],photo_ids:['photo-1'],parts:[{id:'a',answer:'99',working:'Recognized work'}]};
  context.arBindMonthlyCapture=(_f,_p,_a,options)=>{hooks=options;return{snapshot:()=>scan,start(){hooks.onChange(scan);},pause(){},resume(){},refresh(){},setBusy(){}};};
  context.cmApi=async(_m,_p,payload)=>{requests.push(clone(payload));if(requests.length===1)throw{code:'network'};return{...clone(grade),attempts:{limit:3,used:1,remaining:2}};};
  const f=binding(context,clone(problem),true,true);f.fields.get('answer:a').value='42';f.fields.get('working:a').value='Typed derivation';
  f.modes[1].onclick();f.modes[0].onclick();await f.form.onsubmit({preventDefault(){}});
  hooks.onChange({...scan,parts:[{id:'a',answer:'100',working:'Late uploaded work'}]});await f.form.onsubmit({preventDefault(){}});
  assert.equal(requests[0].request_id,requests[1].request_id);assert.equal(requests[1].scan_id,undefined);assert.equal(requests[1].parts[0].answer,'42');
});

test('a later lower score shows the latest grade alongside the unchanged problem record',()=>{
  const {context}=app();const html=context.arResult({...clone(grade),score:88,best:90},problem);
  assert.match(html,/88 \/ 100점/);assert.match(html,/문제 기록 \(최고점\)/);assert.match(html,/90 \/ 100점/);assert.ok(!html.includes('private-'));
});

test('a capture revision conflict refreshes the photographed answer without consuming the old request key',async()=>{
  const {context}=app();let hooks,refreshes=0,serial=0;const requests=[];
  context.crypto.randomUUID=()=>`request-${++serial}`;
  let scan={id:'capture-1',open:true,status:'scanning',pages:[{ocr_status:'done'}],photo_ids:['photo-1'],parts:[{id:'a',answer:'99',working:'Recognized work'}]};
  context.arBindMonthlyCapture=(_f,_p,_a,options)=>{hooks=options;return{snapshot:()=>scan,start(){hooks.onChange(scan);},pause(){},resume(){},
    refresh(){refreshes++;scan={...scan,photo_ids:['photo-2'],parts:[{id:'a',answer:'100',working:'Updated captured work'}]};hooks.onChange(scan);},setBusy(value){hooks.onBusy(value);}};};
  context.cmApi=async(_m,_p,payload)=>{requests.push(clone(payload));if(requests.length===1)throw{code:'capture_changed'};return{...clone(grade),attempts:{limit:3,used:1,remaining:2}};};
  const f=binding(context,clone(problem),true,true);f.modes[1].onclick();await f.form.onsubmit({preventDefault(){}});
  assert.equal(f.p.attempts.used,0);assert.equal(refreshes,1);assert.match(f.out.innerHTML,/촬영 답안이 변경/);assert.equal(f.button.disabled,false);
  await f.form.onsubmit({preventDefault(){}});assert.notEqual(requests[0].request_id,requests[1].request_id);assert.equal(requests[1].scan_id,'capture-1');
});

test('unreadable or incomplete photographed parts cannot be sent as an invented zero',()=>{
  const {context}=app();const scan={pages:[{ocr_status:'done'}],parts:[{id:'a',answer:'42',working:'Derivation'},{id:'b',answer:'',working:''}]};
  assert.equal(context.arMonthlyCaptureReady(scan),true);scan.pages[0].ocr_status='failed';assert.equal(context.arMonthlyCaptureReady(scan),false);
  scan.pages[0].ocr_status='done';scan.parts[0].working='';assert.equal(context.arMonthlyCaptureReady(scan),false);
  assert.equal(context.arMonthlyCaptureReady({pages:[],parts:scan.parts}),false);
});

test('monthly reward notices state highest-score totals, 9/6/3 rewards and delayed finalization in both languages',()=>{
  const {context}=app();const reward={eligible:true,status:'awaiting_grading',announcement_at:deadline};
  let html=context.arMonthlyRewardNotice(reward,'2026-11');assert.match(html,/최고 점수/);assert.match(html,/1위 9개 · 2위 6개 · 3위 3개/);assert.match(html,/남은 채점/);
  assert.equal(context.arMonthlyRewardNotice(reward,'2026-W44'),'');assert.equal(context.arMonthlyRewardNotice({eligible:false},'2026-11'),'');
  context.lang='en';html=context.arMonthlyRewardNotice({...reward,status:'published'},'2026-11');assert.match(html,/highest score/);assert.match(html,/9, 6 and 3 exam tokens/);assert.match(html,/tokens credited/);
  assert.match(context.arSheetT().bestOnly,/only your highest score/);
});

function captureFixture(context) {
  const renew={},refresh={},newButton={},qr={innerHTML:'',querySelector:()=>renew},info={hidden:true};
  const removed=[];
  const pages={innerHTML:'',querySelector:selector=>selector==='[data-capture-refresh]'?refresh:pages.innerHTML.includes('data-capture-new')?newButton:null,
    querySelectorAll:selector=>selector==='[data-capture-remove]'?[...pages.innerHTML.matchAll(/data-capture-remove="([^"]+)"/g)].map(match=>{const button={dataset:{captureRemove:match[1]}};removed.push(button);return button;}):[]};
  const box={querySelector:selector=>({'[data-capture-qr]':qr,'[data-capture-pages]':pages,'[data-capture-info]':info}[selector])};
  context.URL=URL;context.URLSearchParams=URLSearchParams;context.document={baseURI:'https://haslalab.org/',hidden:false};context.arLoad=async()=>{};context.arBindMonthlyPhotos=()=>{};
  const urls=[];context.window.qrcode=()=>({addData:value=>urls.push(value),make(){},createSvgTag:()=>'<svg data-qr="1"></svg>'});
  return{root:{querySelector:()=>box},qr,pages,info,renew,refresh,newButton,removed,urls};
}

test('the exam-style capture controller restores its owner session, renders a scoped scanner QR and removes pages without grading',async()=>{
  const {context}=app(),ui=captureFixture(context),requests=[];
  let scan={id:'capture-1',token:'opaque-upload-grant',open:true,status:'scanning',revision:1,photo_ids:['photo-1'],
    pages:[{id:'photo-1',page_no:1,ocr_status:'done',text:'<script>private</script>'}],parts:[{id:'a',answer:'42',working:'Original derivation'}]};
  context.cmApi=async(method,path,body)=>{requests.push({method,path,body});if(method==='DELETE')scan={...scan,revision:2,pages:[],parts:[],photo_ids:[]};return{scan:clone(scan)};};
  const controller=context.arBindMonthlyCapture(ui.root,clone(problem),()=>true,{scanId:'capture-1'});
  assert.equal(requests.length,0,'constructing the capture view does not create a grant');await controller.start();
  assert.equal(requests[0].path,'/monthly/problems/4/scan');assert.equal(requests[0].body.scan_id,'capture-1');
  const url=new URL(ui.urls[0]),hash=new URLSearchParams(url.hash.slice(1));assert.equal(url.pathname,'/sim/monthly-scan.html');assert.equal(hash.get('c'),'opaque-upload-grant');assert.equal(hash.get('a'),'https://api.test');
  assert.ok(!ui.qr.innerHTML.includes('owner-token'));assert.ok(!ui.pages.innerHTML.includes('<script>'));assert.match(ui.pages.innerHTML,/&lt;script&gt;/);assert.ok(!ui.pages.innerHTML.includes('<textarea'));
  await ui.removed[0].onclick();assert.equal(requests[1].method,'DELETE');assert.equal(requests[1].path,'/monthly/problems/4/scan/pages/photo-1?scan_id=capture-1');
  assert.equal(requests[2].method,'GET');assert.ok(requests.every(request=>!request.path.includes('/submit')));assert.equal(controller.snapshot().pages.length,0);
  controller.dispose();assert.equal(ui.qr.innerHTML,'');assert.equal(ui.pages.innerHTML,'');
});

test('a late scanner grant is hidden and revoked with original credentials after account, API or page disposal changes',async()=>{
  for(const change of ['account','api','dispose']){
    const {context,setAuth}=app(),ui=captureFixture(context),cleanup=[];let finish;
    context.fetch=async(url,options)=>{cleanup.push({url,options});return{ok:true};};
    context.cmApi=()=>new Promise(resolve=>{finish=()=>resolve({scan:{id:'private',token:'private-upload-grant',open:true,pages:[],parts:[]}});});
    const controller=context.arBindMonthlyCapture(ui.root,clone(problem),()=>true),pending=controller.start();
    if(change==='account'){context.cm.me={id:20,username:'other'};setAuth('another-owner');}
    if(change==='api')context.cmBase=()=> 'https://another-api.test';
    if(change==='dispose')controller.dispose();
    finish();await pending;
    assert.equal(ui.qr.innerHTML,'');assert.equal(ui.pages.innerHTML,'');assert.deepEqual(ui.urls,[]);
    assert.equal(cleanup.length,1);
    assert.equal(cleanup[0].url,'https://api.test/api/monthly/problems/4/scan?scan_id=private');
    assert.equal(cleanup[0].options.method,'DELETE');assert.equal(cleanup[0].options.headers.Authorization,'Bearer owner-token');
    assert.equal(cleanup[0].options.cache,'no-store');assert.equal(cleanup[0].options.referrerPolicy,'no-referrer');
    assert.ok(!cleanup[0].url.includes('owner-token')&&!cleanup[0].url.includes('private-upload-grant'));
  }
});

function scannerForm() {
  const capture=new Blob(['capture'],{type:'image/jpeg'}),clean=new Blob(['clean'],{type:'image/png'});
  const file={files:[capture],value:'',click(){}},info={hidden:true},destination={value:'',maxLength:16000,dataset:{sheetWorking:'a'},focus(){}},buttons={};
  for(const key of ['original','clean','new','cancel','read'])buttons[key]={dataset:{photo:key}};
  const box={hidden:true,innerHTML:'',querySelector:selector=>({'[data-new-photo]':buttons.new,'[data-cancel-photo]':buttons.cancel,'[data-read-photo]':buttons.read}[selector]),querySelectorAll:()=>[buttons.original,buttons.clean]};
  const form={math:{checked:true},querySelector:selector=>({'input[type=file]':file,'.arinfo':info,'.arshot':box,'textarea':destination}[selector])};
  return {form,file,info,destination,buttons,capture,clean};
}

test('monthly OCR sends the selected scan and a separately preserved capture with bearer authorization',async()=>{
  const {context}=app(),fixture=scannerForm(),encoded=[];let request,result;
  context.testScanner={canProcess:()=>true,processShot:async()=>({blob:fixture.clean}),encodeUpload:async blob=>{encoded.push(blob);return blob;}};
  vm.runInContext('arScanner=Promise.resolve(testScanner)',context);
  context.fetch=async(url,options)=>{request={url,options};return{ok:true,json:async()=>({text:'recognized',photo_id:'photo-1',part_id:'a'})};};
  context.arBindAnswerPhoto(fixture.form,()=>true,vm.runInContext('arT()',context),(text,destination,response)=>{result={text,destination,response};destination.value=text;},
    {target:()=>fixture.destination,request:destination=>({path:'/monthly/problems/4/photos',fields:{part_id:destination.dataset.sheetWorking},original:true})});
  await fixture.file.onchange();await fixture.buttons.read.onclick();
  assert.equal(request.url,'https://api.test/api/monthly/problems/4/photos?mode=math&provider=gemini');
  assert.equal(request.options.headers.Authorization,'Bearer owner-token');assert.ok(!request.url.includes('owner-token'));
  assert.equal(await request.options.body.get('image').text(),'clean');
  assert.equal(await request.options.body.get('original_image').text(),'capture');
  assert.equal(request.options.body.get('part_id'),'a');assert.equal(encoded.length,2);
  assert.equal(result.response.photo_id,'photo-1');assert.equal(result.destination,fixture.destination);
});

test('photo reading does not attach a response to a different signed-in account',async()=>{
  const {context,setAuth}=app(),fixture=scannerForm();let finish,read=false;
  context.testScanner={canProcess:()=>true,processShot:async()=>({blob:fixture.clean}),encodeUpload:async blob=>blob};
  vm.runInContext('arScanner=Promise.resolve(testScanner)',context);
  context.fetch=()=>new Promise(resolve=>{finish=()=>resolve({ok:true,json:async()=>({text:'private answer'})});});
  context.arBindAnswerPhoto(fixture.form,()=>true,vm.runInContext('arT()',context),()=>{read=true;});
  await fixture.file.onchange();const pending=fixture.buttons.read.onclick();
  await new Promise(resolve=>setImmediate(resolve));setAuth('different-account-token');finish();await pending;
  assert.equal(read,false);
});

test('legacy photo OCR keeps its existing endpoint and sends no monthly capture attachment',async()=>{
  const {context}=app(),fixture=scannerForm();let request;
  context.testScanner={canProcess:()=>true,processShot:async()=>({blob:fixture.clean}),encodeUpload:async blob=>blob};
  vm.runInContext('arScanner=Promise.resolve(testScanner)',context);
  context.fetch=async(url,options)=>{request={url,options};return{ok:true,json:async()=>({text:'legacy working'})};};
  context.arBindAnswerPhoto(fixture.form,()=>true,vm.runInContext('arT()',context),(text,destination)=>{(destination||fixture.destination).value=text;});
  await fixture.file.onchange();await fixture.buttons.read.onclick();
  assert.equal(request.url,'https://api.test/api/ocr?mode=math&provider=gemini');assert.equal(request.options.body.has('original_image'),false);
  assert.equal(fixture.destination.value,'legacy working');
});

test('explicit photo OCR sends and pins the selected available provider without model names or cross-account requests',async()=>{
  const {context,setAuth}=app(),fixture=scannerForm(),capabilities={vision:{providers:[{id:'deepseek',available:true,model:'private-model'},{id:'gemini',available:true}]}};let request,pinned;
  context.testScanner={canProcess:()=>true,processShot:async()=>({blob:fixture.clean}),encodeUpload:async blob=>blob};vm.runInContext('arScanner=Promise.resolve(testScanner)',context);
  context.fetch=async(url,options)=>{request={url,options};return{ok:true,json:async()=>({text:'Visible graph and answer',provider:'deepseek'})};};
  context.arBindAnswerPhoto(fixture.form,()=>true,vm.runInContext('arT()',context),text=>{fixture.destination.value=text;},{provider:()=> 'deepseek',capabilities,onProviderPinned:value=>pinned=value});
  await fixture.file.onchange();assert.equal(request,undefined,'file choice is local only');await fixture.buttons.read.onclick();
  assert.match(request.url,/provider=deepseek$/);assert.equal(request.options.body.get('provider'),'deepseek');assert.equal(pinned,'deepseek');assert.equal(fixture.destination.value,'Visible graph and answer');
  const stale=scannerForm();let encode,network=0;context.testScanner.encodeUpload=()=>new Promise(resolve=>encode=resolve);context.fetch=async()=>{network++;return{ok:true,json:async()=>({text:'stale'})};};
  context.arBindAnswerPhoto(stale.form,()=>true,vm.runInContext('arT()',context),()=>assert.fail('stale OCR rendered'),{provider:()=> 'deepseek',capabilities});
  await stale.file.onchange();const pending=stale.buttons.read.onclick();await new Promise(done=>setImmediate(done));setAuth('new-owner');encode(stale.clean);await pending;assert.equal(network,0);
});

test('graph-only photo evidence reaches the callback without invented transcription or an empty OCR failure',async()=>{
  const {context}=app(),fixture=scannerForm();let received,request;
  context.testScanner={canProcess:()=>true,processShot:async()=>({blob:fixture.clean}),encodeUpload:async blob=>blob};vm.runInContext('arScanner=Promise.resolve(testScanner)',context);
  context.fetch=async(url)=>{request=url;return{ok:true,json:async()=>({text:'',photo_id:'owned-photo',visuals:[{page:1,kind:'direction',description:'blue arrow'}]})};};
  context.arBindAnswerPhoto(fixture.form,()=>true,vm.runInContext('arT()',context),(text,_target,result)=>{received={text,result};},{problemId:7});
  await fixture.file.onchange();await fixture.buttons.read.onclick();
  assert.equal(request,'https://api.test/api/ocr?mode=math&provider=gemini&problem_id=7');
  assert.equal(received.text,'');assert.equal(received.result.photo_id,'owned-photo');assert.match(fixture.info.textContent,/그림 답안/);
  assert.match(context.arSheetWorkingPreview('[PHOTO:11111111-1111-4111-8111-111111111111:a]'),/사진의 그래프/);
});

test('monthly QR grants use the chosen server provider and renewal cannot override it in the URL',async()=>{
  const {context}=app(),ui=captureFixture(context),requests=[],p=clone(problem);let choice='deepseek';p.vision={providers:[{id:'deepseek',available:true},{id:'gemini',available:true}]};
  const scan={id:'capture-provider',token:'opaque-grant',provider:'deepseek',provider_locked:true,open:true,status:'scanning',revision:1,pages:[],parts:[]};
  context.cmApi=async(method,path,body)=>{requests.push({method,path,body:clone(body)});return{scan:clone(scan)};};
  const controller=context.arBindMonthlyCapture(ui.root,p,()=>true,{provider:()=>choice});await controller.start();assert.equal(requests[0].body.provider,'deepseek');
  choice='gemini';await controller.start();assert.equal(requests[1].body.provider,'deepseek','renewing an existing grant uses its server-stored provider');
  for(const value of ui.urls){const hash=new URLSearchParams(new URL(value).hash.slice(1));assert.equal(hash.has('provider'),false);assert.equal(hash.get('c'),'opaque-grant');}
  controller.dispose();
});

test('photo answer submission locks to the provider already stored by the capture',async()=>{
  const {context}=app(),p=clone(problem);p.vision={providers:[{id:'deepseek',available:true},{id:'gemini',available:true}]};let hooks,body;
  const scan={id:'capture-deepseek',provider:'deepseek',provider_locked:true,open:true,status:'scanning',pages:[{id:'page',ocr_status:'done'}],parts:[{id:'a',answer:'42',working:'Drawn graph'}]};
  context.arBindMonthlyCapture=(_form,_p,_alive,options)=>{hooks=options;return{snapshot:()=>scan,start(){hooks.onChange(scan);},resume(){},pause(){},refresh(){},setBusy(value){hooks.onBusy(value);}};};
  context.cmApi=async(_method,_path,payload)=>{body=clone(payload);return{status:'pending',attempts:{remaining:2}};};
  const f=binding(context,p,true,true);f.provider.value='deepseek';f.modes[1].onclick();assert.equal(f.provider.value,'deepseek');assert.equal(f.provider.disabled,true);
  await f.form.onsubmit({preventDefault(){}});assert.equal(body.provider,'deepseek');assert.equal(body.scan_id,'capture-deepseek');assert.equal(body.parts,undefined);
});

test('original photos are fetched privately, remain owner-scoped and release blob URLs on navigation',async()=>{
  const {context,revoked,emit}=app();let request;
  const image={hidden:true,removeAttribute(name){delete this[name];}},info={hidden:true};
  const box={querySelector:selector=>selector==='img'?image:info};
  const button={dataset:{monthlyPhoto:'photo/private'},parentElement:box};
  context.fetch=async(url,options)=>{request={url,options};return{ok:true,blob:async()=>new Blob(['capture'],{type:'image/jpeg'})};};
  context.arBindMonthlyPhotos({querySelectorAll:()=>[button]},()=>true);await button.onclick();
  assert.equal(request.url,'https://api.test/api/monthly/photos/photo%2Fprivate');
  assert.equal(request.options.headers.Authorization,'Bearer owner-token');assert.equal(image.src,'blob:private-1');
  emit('hashchange');assert.deepEqual(revoked,['blob:private-1']);assert.equal(image.src,undefined);assert.equal(image.hidden,true);
});

test('an original-photo fetch finishing after account switching is never displayed',async()=>{
  const {context,revoked,setAuth}=app();let finish;
  const image={hidden:true,removeAttribute(name){delete this[name];}},info={hidden:true};
  const button={dataset:{monthlyPhoto:'photo-1'},parentElement:{querySelector:selector=>selector==='img'?image:info}};
  context.fetch=()=>new Promise(resolve=>{finish=()=>resolve({ok:true,blob:async()=>new Blob(['private'],{type:'image/jpeg'})});});
  context.arBindMonthlyPhotos({querySelectorAll:()=>[button]},()=>true);const pending=button.onclick();
  setAuth('different-owner');finish();await pending;
  assert.equal(image.src,undefined);assert.equal(image.hidden,true);assert.deepEqual(revoked,[]);
});

test('monthly badges distinguish Theory and Experiment while legacy answer-type badges remain intact',async()=>{
  const {context}=app();context.arLevel=()=>'';context.cm.me=null;
  const root={innerHTML:''},theory={...clone(problem),round:'theory',opens_at:deadline-86400,users:0,solvers:0};
  const experiment={...theory,id:99,no:5,title:'Experiment problem',round:'experiment'};
  for(const language of ['ko','en']) {
    context.lang=language;
    await context.arWeekly(root,()=>true,'2026-11',{period:'2026-11',problems:[theory,experiment],months:[],top:[],now:deadline-60});
    assert.match(root.innerHTML,/data-round="theory">Theory<\/span>/);
    assert.match(root.innerHTML,/data-round="experiment">Experiment<\/span>/);
    assert.ok(!/<span class="arkind[^>]*>(?:서술|Written)<\/span>/.test(root.innerHTML));
    assert.match(context.arProblemKindBadge({week:'2026-11',kind:'essay'}),/>Theory<\/span>/,'older monthly APIs default to theory');
    assert.match(context.arProblemKindBadge({week:'2026-W43',kind:'essay'}),language==='ko'?/>서술<\/span>/:/>Written<\/span>/);
    assert.match(context.arProblemKindBadge({week:'2026-W43',kind:'short'}),language==='ko'?/>단답<\/span>/:/>Short answer<\/span>/);
  }
});

test('letter labels replace greenhouse legacy numbers across forms, validation, saved answers and released criteria',()=>{
  const {context,setNow}=app(),p={...clone(problem),id:7,no:4,subject:'astronomy',round:'theory',answerSheet:{version:'2026-11-v1',parts:[
    {id:'16',displayId:'a',label_ko:'복사 평형',label_en:'Radiative equilibrium',points:40},
    {id:'20a',displayId:'e',label_ko:'대기층',label_en:'Atmospheric layer',points:60},
  ]}};
  const html=context.arMonthlyAnswerHtml(p,true);
  assert.match(html,/<legend>\(a\) 복사 평형/);assert.match(html,/<legend>\(e\) 대기층/);
  assert.match(html,/data-sheet-answer="16"/);assert.match(html,/data-sheet-working="20a"/,'canonical payload fields remain compatible');
  const saved=context.arMonthlySavedAnswer({answer_sheet:{parts:[{id:'16',answer:'T',working:'Derivation'}]},photo_attachments:[{id:'photo-16',part_id:'16'}]},p);
  assert.match(saved,/<h4>\(a\)<\/h4>/);assert.match(saved,/촬영 원본 보기 · \(a\)/);assert.ok(!saved.includes('<h4>16</h4>'));
  setNow((deadline+1)*1000);
  const released=context.arResult({status:'graded',score:40,detail:{scores:[{id:'16',name:'Radiative equilibrium',got:40,max:40,evidence:[],note:'Correct'}]}},p);
  assert.match(released,/<b>\(a\)<\/b>/);assert.ok(!released.includes('<b>16</b>'));
  const data={'16':{answer:'T',working:''},'20a':{answer:'',working:''}};
  assert.throws(()=>context.arSheetParts(p,{querySelector:selector=>{const [,kind,id]=/data-sheet-(answer|working)="([^"]+)"/.exec(selector);return{value:data[id][kind]};}}),error=>error.sheetMessage.includes('(a):'));
});

test('problem headers and criterion summaries use monthly rounds and display letters without exposing old numbering',async()=>{
  const {context}=app();context.cm.me=null;context.arBindMonthlyAnswer=()=>{};
  const root={innerHTML:'',querySelector:()=>null},p={...clone(problem),id:7,no:4,subject:'astronomy',round:'experiment',criteria:[{id:'16',name:'Radiative equilibrium',max:100}],
    answerSheet:{version:'2026-11-v1',parts:[{id:'16',displayId:'a',label_ko:'복사 평형',label_en:'Radiative equilibrium',points:100}]},
    mine:[{status:'graded',score:73,created_at:1,answer_sheet:{parts:[{id:'16',answer:'T',working:'Derivation'}]}}]};
  context.cmApi=async()=>({problem:p,health:{ocr:false}});
  await context.arProblem(root,()=>true,7);
  assert.match(root.innerHTML,/data-round="experiment">Experiment<\/span>/);assert.match(root.innerHTML,/<span>astronomy<\/span>/);
  assert.match(root.innerHTML,/<div class="arcrit"><span><b>\(a\)<\/b>/);assert.match(root.innerHTML,/<h4>\(a\)<\/h4>/);
  assert.ok(!root.innerHTML.includes('<b>16</b>'));assert.ok(!root.innerHTML.includes('<h4>16</h4>'));
});

test('read-only captured parts use display letters while their server-owned IDs remain unchanged',async()=>{
  const {context}=app(),ui=captureFixture(context),p={...clone(problem),answerSheet:{version:'2026-11-v1',parts:[{id:'16',displayId:'a',points:100}]}};
  const scan={id:'scan-letters',open:true,status:'scanning',revision:1,pages:[{id:'photo-1',page_no:1,ocr_status:'done',text:'Captured original'}],parts:[{id:'16',answer:'T',working:'Captured derivation'}]};
  context.cmApi=async()=>({scan:clone(scan)});
  const controller=context.arBindMonthlyCapture(ui.root,p,()=>true);await controller.start();
  assert.match(ui.pages.innerHTML,/<h4>\(a\)<\/h4>/);assert.ok(!ui.pages.innerHTML.includes('<h4>16</h4>'));
  assert.equal(controller.snapshot().parts[0].id,'16');controller.dispose();
});
