const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const test = require('node:test'), assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../arena.js'), 'utf8');
const block = source.slice(source.indexOf('const AR_MODEL_PIPELINES ='));
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pipelines = ['gemini-gemini','gemini-deepseek','deepseek-deepseek'].map(id => ({id,available:true,ocr:{model:'ocr-model'},grading:{model:'grading-model'}}));
const entry = (id = 'kphe:2026-2:P1', extra = {}) => ({id,comp:'KPhE',year:'2026-2',task:'P1',kind:'problem',title:{ko:'2026 2차 문제 1',en:'2026 stage 2 problem 1'},paper:'문제 1.pdf',solution:'pdfx/solution.pdf',mark:'https://official.example/mark.pdf',referenceStatus:'published',...extra});
const deferred = () => { let resolve; const promise = new Promise(done => resolve = done); return {promise,resolve}; };
const tick = () => new Promise(done => setImmediate(done));
function element() {
  let html = '', text = '';
  return {hidden:false,disabled:false, get innerHTML(){return html;},set innerHTML(value){html=String(value);text='';},get textContent(){return text;},set textContent(value){text=String(value);html='';}};
}
function harness(options = {}) {
  const image = new Blob(['answer'],{type:'image/jpeg'}); image.name = 'answer.jpg';
  const fields = {mode:{value:'exam'},comp:{value:''},year:{value:''},entryId:{value:''},pipeline:{value:'gemini-deepseek'},problem:{value:'Client problem override'},rubric:{value:'Client rubric override'},points:{value:'999'},images:{files:[image]}};
  Object.defineProperty(fields.images,'value',{set(value){if(value==='')this.files=[];},get(){return this.files.length?'answer.jpg':'';}});
  const controls = {disabled:false}, form = {events:{},elements:{namedItem:name=>fields[name]},querySelector:()=>controls,addEventListener:(name,fn)=>form.events[name]=fn};
  const nodes = Object.fromEntries(['arModelStatus','arModelResults','arModelEmpty','arModelPhotos','arModelManualFields','arModelExamFields','arModelExamInfo','arModelRun'].map(id=>[id,element()]));
  nodes.arModelTestForm = form;
  const root = {innerHTML:'',querySelector:selector=>nodes[selector.slice(1)]};
  const config = {pipelines,examCompetitions:[{id:'KPhE',title:{ko:'한국물리대회',en:'KPhE'},years:['2026-2','2026-1',2025]},{id:'KMO',title:{ko:'한국수학올림피아드'},years:[2026,2025]}],reference:{available:true,provider:'gemini'},...options.config};
  const calls=[],posts=[],timers=new Map(),events=new Map(); let route=true,token='account-A',base='https://api.example',scannerCalls=0,timerId=0;
  const result = {pipeline:'gemini-deepseek',reference:{entry:entry(),cached:false,scoring:'official',provider:'gemini',model:'reference-model',ms:50},ocr:{text:'x=2',provider:'gemini',model:'ocr-model',ms:10},grading:{status:'graded',score:8,points:10,feedback:'Good',provider:'deepseek',model:'grading-model',ms:20},usage:{calls:3,total_tokens:30,stages:[],pricing:{status:'estimated',total_usd:0.003},pipeline_pricing:{status:'estimated',total_usd:0.002},reference_pricing:{status:'estimated',total_usd:0.001}},elapsed_ms:80};
  const context = {lang:options.language||'ko',cm:{me:{role:'admin'}},esc,sessionStorage:{setItem(){}},window:{addEventListener:(name,fn)=>events.set(name,fn),removeEventListener:name=>events.delete(name)},
    URL:class extends URL{static createObjectURL(){return 'blob:preview';}static revokeObjectURL(){}},cmBase:()=>base,cmTok:()=>token,
    cmApi:async(...args)=>{calls.push(args);return options.api?options.api(...args):args[1].includes('?')?{exams:options.exams||[entry()]}:config;},
    arLoadScanner:async()=>{scannerCalls++;return{encodeUpload:async file=>file};},btoa,Uint8Array,AbortController,
    setTimeout:(fn,ms)=>{const id=++timerId;timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id),
    fetch:async(url,request)=>{posts.push({url,request});return{ok:true,json:async()=>result};}};
  vm.createContext(context); vm.runInContext(block,context);
  return {context,root,nodes,fields,form,controls,config,calls,posts,timers,result,events,image,scannerCalls:()=>scannerCalls,current:()=>route,stop:()=>{route=false;},setToken:value=>{token=value;},setBase:value=>{base=value;},open:()=>context.arModelTest(root,()=>route),submit:()=>form.onsubmit({preventDefault(){}})};
}

test('exam selection defaults to canonical competition/year/task without PDF or AI requests', async () => {
  const h=harness(); await h.open();
  assert.equal(h.calls.length,2); assert.equal(h.calls[1][1],'/admin/lab/model-test?comp=KPhE&year=2026-2');
  assert.equal(h.fields.entryId.value,'kphe:2026-2:P1'); assert.equal(h.fields.problem.disabled,true); assert.equal(h.fields.problem.required,false);
  assert.match(h.root.innerHTML,/기출 선택/); assert.match(h.root.innerHTML,/고급 · 직접 입력/); assert.match(h.root.innerHTML,/最大|최대/);
  assert.match(h.nodes.arModelExamInfo.innerHTML,/https:\/\/haslalab-pdf.haslalab.workers.dev\/pdf\/%/);
  assert.match(h.nodes.arModelExamInfo.innerHTML,/https:\/\/haslalab.org\/pdfx\/solution.pdf/);
  assert.equal(h.posts.length,0); assert.equal(h.scannerCalls(),0);
  h.fields.images.onchange(); assert.equal(h.posts.length,0); assert.equal(h.calls.length,2);
});

test('explicit exam run sends only the canonical entry, pipeline and images', async () => {
  const h=harness(); await h.open(); await h.submit();
  assert.equal(h.posts.length,1); const request=JSON.parse(h.posts[0].request.body);
  assert.deepEqual(Object.keys(request).sort(),['entryId','images','lang','mode','pipeline']);
  assert.equal(request.mode,'exam'); assert.equal(request.entryId,'kphe:2026-2:P1'); assert.equal(request.images[0].data,'YW5zd2Vy');
  assert.equal(h.posts[0].request.headers.Authorization,'Bearer account-A'); assert.equal(h.controls.disabled,false);
  const html=h.nodes.arModelResults.innerHTML;
  for(const text of ['8 / 10','예상 총비용','OCR·채점 비용','공통 기준 준비 비용','$0.003','$0.002','$0.001']) assert.ok(html.includes(text),text);
});

test('localized paper and printable answer-sheet links open safely without AI execution', async () => {
  const selected=entry('localized',{paper:'Original_EN.pdf',paperKo:'문제_KO.pdf',answerSheets:['pdfx/answers/sheet-1.pdf','https://official.example/sheet-2.pdf']});
  const ko=harness({exams:[selected]}); await ko.open();
  const html=ko.nodes.arModelExamInfo.innerHTML;
  assert.ok(html.includes(encodeURIComponent('문제_KO.pdf'))); assert.doesNotMatch(html,/Original_EN.pdf/);
  assert.match(html,/href="https:\/\/haslalab.org\/pdfx\/answers\/sheet-1.pdf"[^>]*>답안지 1</);
  assert.match(html,/href="https:\/\/official.example\/sheet-2.pdf"[^>]*>답안지 2</);
  assert.equal(ko.posts.length,0); assert.equal(ko.scannerCalls(),0);
  const en=harness({language:'en',exams:[{...selected,answerSheets:['Answer.pdf','javascript:alert(1)']}]}); await en.open();
  assert.match(en.nodes.arModelExamInfo.innerHTML,/Original_EN.pdf/); assert.match(en.nodes.arModelExamInfo.innerHTML,/>Answer sheet 1</);
  assert.doesNotMatch(en.nodes.arModelExamInfo.innerHTML,/javascript:|문제_KO.pdf/); assert.equal(en.posts.length,0);
  const single=harness({exams:[{...selected,answerSheets:['Answer.pdf']}]}); await single.open();
  assert.match(single.nodes.arModelExamInfo.innerHTML,/>답안지</); assert.doesNotMatch(single.nodes.arModelExamInfo.innerHTML,/>답안지 1</);
});

test('pipeline changes retain comparisons and photos; exam and mode changes clear them', async () => {
  const h=harness({exams:[entry(),entry('next',{task:'P2'})]}); await h.open(); await h.submit();
  const previous=h.nodes.arModelResults.innerHTML; h.fields.pipeline.value='deepseek-deepseek'; h.form.events.input({target:{name:'pipeline'}});
  assert.equal(h.nodes.arModelResults.innerHTML,previous); assert.equal(h.fields.images.files.length,1);
  h.fields.entryId.value='next'; h.fields.entryId.onchange(); assert.equal(h.nodes.arModelResults.innerHTML,''); assert.equal(h.fields.images.files.length,0);
  h.fields.images.files=[h.image]; h.fields.mode.value='manual'; h.fields.mode.onchange();
  assert.equal(h.fields.images.files.length,0); assert.equal(h.fields.problem.disabled,false); assert.equal(h.fields.problem.required,true);
  assert.equal(h.nodes.arModelExamFields.hidden,true); assert.equal(h.nodes.arModelManualFields.hidden,false);
  h.fields.images.files=[h.image]; await h.submit(); const request=JSON.parse(h.posts.at(-1).request.body);
  assert.equal(request.problem,'Client problem override'); assert.equal(request.points,999); assert.equal(request.mode,undefined); assert.equal(request.entryId,undefined);
});

test('older config without exam metadata keeps the manual request contract', async () => {
  const h=harness({config:{examCompetitions:undefined}}); await h.open(); await h.submit();
  assert.equal(h.calls.length,1); assert.equal(h.fields.problem.disabled,false); assert.equal(h.posts.length,1);
  const request=JSON.parse(h.posts[0].request.body); assert.equal(request.rubric,'Client rubric override'); assert.equal(request.mode,undefined);
});

test('whole-paper tasks and independent references are explicit and escaped', async () => {
  const h=harness({exams:[entry('whole',{task:'T',wholePaper:true,title:{ko:'<img onerror=bad>'},referenceStatus:'problem-only',paper:'javascript:alert(1)',solution:null,mark:null})]}); await h.open();
  assert.match(h.fields.entryId.innerHTML,/시험지 전체/); assert.match(h.nodes.arModelExamInfo.innerHTML,/&lt;img onerror=bad&gt;/);
  assert.match(h.nodes.arModelExamInfo.innerHTML,/점수 없이 정성 피드백/); assert.doesNotMatch(h.nodes.arModelExamInfo.innerHTML,/href="javascript:/);
  for(const value of ['javascript:alert(1)','http://official.example/a.pdf','https://user:pass@official.example/a.pdf','//evil.example/x','../x.pdf','pdfx/../x.pdf']) assert.equal(h.context.arModelTestSourceLink(value),'');
  assert.equal(h.context.arModelTestSourceLink('paper.pdf'),'https://haslalab-pdf.haslalab.workers.dev/pdf/paper.pdf');
  assert.equal(h.context.arModelTestSourceLink('https://official.example/a.pdf'),'https://official.example/a.pdf');
});

test('out-of-order year selections cannot replace the newest selected exam', async () => {
  const pending=new Map(), h=harness(); await h.open();
  h.context.cmApi=async(method,url)=>{h.calls.push([method,url]);const d=deferred();pending.set(url,d);return d.promise;};
  h.fields.year.value='2026-1'; const older=h.fields.year.onchange(); h.fields.year.value='2025'; const newer=h.fields.year.onchange();
  pending.get('/admin/lab/model-test?comp=KPhE&year=2025').resolve({exams:[entry('newest')]}); await newer;
  pending.get('/admin/lab/model-test?comp=KPhE&year=2026-1').resolve({exams:[entry('older')]}); await older;
  assert.equal(h.fields.entryId.value,'newest'); assert.equal(h.posts.length,0); assert.equal(h.fields.images.files.length,0);
});

test('changing the selected exam aborts a pending run and suppresses its stale result', async () => {
  const h=harness({exams:[entry(),entry('next')]}); await h.open(); const pending=deferred(); let signal;
  h.context.fetch=async(url,request)=>{signal=request.signal;return pending.promise;};
  const run=h.submit(); await tick(); assert.equal(signal.aborted,false);
  h.fields.entryId.value='next'; h.fields.entryId.onchange(); assert.equal(signal.aborted,true);
  pending.resolve({ok:true,json:async()=>h.result}); await run;
  assert.equal(h.nodes.arModelResults.innerHTML,''); assert.equal(h.nodes.arModelStatus.textContent,''); assert.equal(h.controls.disabled,false);
});

test('selection changes during photo preparation prevent the paid request', async () => {
  const h=harness({exams:[entry(),entry('next')]}); await h.open(); const pending=deferred(); h.context.arLoadScanner=()=>pending.promise;
  const run=h.submit(); h.fields.entryId.value='next'; h.fields.entryId.onchange(); pending.resolve({encodeUpload:async file=>file}); await run;
  assert.equal(h.posts.length,0); assert.equal(h.nodes.arModelResults.innerHTML,'');
});

test('account, language and route changes suppress delayed selection and run completions', async () => {
  for(const change of [h=>h.setToken('account-B'),h=>{h.context.lang='en';},h=>h.stop(),h=>h.setBase('https://other.example')]) {
    const pending=deferred(), h=harness(); h.context.cmApi=()=>pending.promise;
    const opening=h.open(); change(h); pending.resolve(h.config); await opening; assert.equal(h.root.innerHTML,'');
    const a=harness(); await a.open(); const response=deferred(); a.context.fetch=()=>response.promise;
    const running=a.submit(); await tick(); change(a); response.resolve({ok:true,json:async()=>a.result}); await running;
    assert.equal(a.nodes.arModelResults.innerHTML,'');
  }
});

test('unavailable reference preparation blocks exam execution but leaves manual mode usable', async () => {
  const h=harness({config:{reference:{available:false,provider:'gemini'}}}); await h.open(); assert.equal(h.nodes.arModelRun.disabled,true);
  await h.submit(); assert.equal(h.posts.length,0); assert.match(h.nodes.arModelStatus.textContent,/Gemini/); assert.match(h.nodes.arModelExamInfo.innerHTML,/Gemini/);
  h.fields.mode.value='manual'; h.fields.mode.onchange(); h.fields.images.files=[h.image]; await h.submit(); assert.equal(h.posts.length,1);
});

test('qualitative and reused reference results never invent zero scores or preparation charges', async () => {
  const h=harness(); await h.open(); h.result.reference={...h.result.reference,cached:true,scoring:'qualitative'};
  h.result.grading={status:'needs_review',score:null,points:null,feedback:'Qualitative'};
  h.result.usage={...h.result.usage,calls:2,reference_pricing:{status:'unknown',total_calls:0}}; await h.submit();
  const html=h.nodes.arModelResults.innerHTML; assert.match(html,/공통 기준 재사용/); assert.match(html,/정성 피드백/); assert.doesNotMatch(html,/0 \/|공통 기준 준비 비용/);
  const forged=h.context.arModelTestResult({...h.result,grading:{status:'graded',score:0,points:10}},h.context.arModelTestLabels()); assert.doesNotMatch(forged,/0 \/ 10/);
  const penalty=h.context.arModelTestResult({...h.result,reference:{...h.result.reference,scoring:'official'},grading:{status:'graded',score:-1,points:50}},h.context.arModelTestLabels());
  assert.match(penalty,/-1 \/ 50/,'server-verified wrong-answer penalties must remain visible');
});

test('reference-stage failure retains known usage and reports no fabricated grading score', async () => {
  const h=harness(); await h.open(); h.context.fetch=async()=>({ok:false,json:async()=>({error:'model_test_reference_source',stage:'reference',provider:'gemini',model:'reference-model',elapsed_ms:400,
    usage:{calls:1,total_tokens:null,incomplete:true,stages:[{stage:'reference',provider:'gemini',model:'reference-model',calls:1,ms:400,pricing:{status:'unknown'}}],pricing:{status:'incomplete',incomplete:true,priced_calls:0}}})});
  await h.submit(); const html=h.nodes.arModelResults.innerHTML;
  assert.match(html,/공통 기준 준비/); assert.match(html,/테스트 미완료/); assert.match(html,/총액 미확정/); assert.doesNotMatch(html,/0 \/|\$0/);
});

test('explicit runs use the 240-second timeout and retain image-count limits', async () => {
  const h=harness(); await h.open(); const pending=deferred(); let signal;
  h.context.fetch=async(url,request)=>{signal=request.signal;return pending.promise;}; const run=h.submit(); await tick();
  const timeout=[...h.timers.values()].find(x=>x.ms===240000); assert.ok(timeout); timeout.fn(); assert.equal(signal.aborted,true);
  pending.resolve({ok:false,json:async()=>({error:'model_test_timeout'})}); await run; assert.match(h.nodes.arModelStatus.textContent,/초과/); assert.equal(h.timers.size,0);
  assert.match(h.context.arModelTestError({code:'model_test_reference_timeout',stage:'reference'},h.context.arModelTestLabels()),/공통 기준 준비.*초과/);
  const a=harness(); await a.open(); a.fields.images.files=Array(4).fill(a.image); await a.submit(); assert.equal(a.posts.length,0); assert.match(a.nodes.arModelStatus.textContent,/최대 3장/);
});

test('selection errors and empty catalogs leave explicit execution disabled', async () => {
  const empty=harness({exams:[]}); await empty.open(); assert.equal(empty.nodes.arModelRun.disabled,true); await empty.submit(); assert.equal(empty.posts.length,0);
  const h=harness(); h.context.cmApi=async(method,url)=>{if(url.includes('?'))throw new Error('private detail');return h.config;}; await h.open();
  assert.equal(h.nodes.arModelRun.disabled,true); assert.match(h.nodes.arModelExamInfo.textContent,/다시 선택/); assert.doesNotMatch(h.nodes.arModelExamInfo.textContent,/private detail/);
});
