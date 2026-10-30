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

function binding(context,p=clone(problem),ocr=false) {
  const fields=new Map(),previews=new Map(),button={disabled:false},out={innerHTML:''},counter={textContent:''};
  for(const part of p.answerSheet.parts)for(const kind of ['answer','working']){
    fields.set(`${kind}:${part.id}`,{value:'',disabled:false,dataset:{[kind==='working'?'sheetWorking':'sheetAnswer']:part.id}});
    previews.set(`${kind}:${part.id}`,{innerHTML:''});
  }
  const form={photo_part:{value:'a'},querySelector(selector){
    if(selector==='button[type=submit]')return button;
    let match=/^\[data-sheet-(answer|working)="([^"]+)"\]$/.exec(selector);if(match)return fields.get(`${match[1]}:${match[2]}`);
    match=/^\[data-sheet-(answer|working)-preview="([^"]+)"\]$/.exec(selector);if(match)return previews.get(`${match[1]}:${match[2]}`);
    throw Error('Unexpected selector '+selector);
  },querySelectorAll:selector=>selector.startsWith('[data-sheet-answer]')?[...fields.values()]:[]};
  const root={querySelector:selector=>({'#arSheetF':form,'#arOut':out,'#arSheetAttempts':counter}[selector])};
  context.arBindMonthlyAnswer(root,p,()=>true,ocr);
  return {form,fields,button,out,p};
}

test('verified photo IDs are deduplicated, restored with the account draft and submitted with their part',async()=>{
  const {context,storage}=app();let read,options,request;
  context.arBindAnswerPhoto=(_f,_alive,_T,onRead,opts)=>{read=onRead;options=opts;};
  const form=binding(context,clone(problem),true);
  assert.equal(options.request(form.fields.get('working:a')).path,'/monthly/problems/4/photos');
  assert.equal(options.request(form.fields.get('working:a')).fields.part_id,'a');
  assert.equal(options.request(form.fields.get('working:a')).original,true);
  const dest=form.fields.get('working:a');
  read('my handwritten work',dest,{photo_id:'photo-1',part_id:'a'});
  read('continued work',dest,{photo_id:'photo-1',part_id:'a'});
  read('wrong association',dest,{photo_id:'photo-wrong',part_id:'b'});
  form.fields.get('answer:a').value='42';form.fields.get('answer:a').oninput();
  const draft=JSON.parse([...storage.values()][0]);assert.deepEqual(draft.photos,[{id:'photo-1',part_id:'a'}]);
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
  assert.equal(request.url,'https://api.test/api/monthly/problems/4/photos?mode=math');
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
  assert.equal(request.url,'https://api.test/api/ocr?mode=math');assert.equal(request.options.body.has('original_image'),false);
  assert.equal(fixture.destination.value,'legacy working');
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
