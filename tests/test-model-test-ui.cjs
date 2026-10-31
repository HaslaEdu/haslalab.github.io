const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../arena.js'),'utf8');
const block=source.slice(source.indexOf('const AR_MODEL_PIPELINES ='));
const escape=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pipelines=['gemini-gemini','gemini-deepseek','deepseek-deepseek'].map(id=>({id,available:true,ocr:{provider:id.split('-')[0],model:'ocr-model'},grading:{provider:id.split('-')[1],model:'grading-model'}}));
function harness(role='admin'){
  const fields={mode:{value:'manual'},pipeline:{value:'gemini-deepseek'},problem:{value:'Find x.'},rubric:{value:'x=2 is worth 10.'},points:{value:'10'},images:{files:[new Blob(['test'],{type:'image/jpeg'})]}};
  const controls={disabled:false},form={elements:{namedItem:n=>fields[n]},events:{},querySelector:()=>controls,addEventListener:(n,f)=>form.events[n]=f};
  const nodes={arModelTestForm:form,arModelStatus:{},arModelResults:{innerHTML:''},arModelEmpty:{},arModelPhotos:{innerHTML:''},arModelManualFields:{},arModelRun:{}};
  const root={innerHTML:'',querySelector:q=>nodes[q.slice(1)]};
  const calls=[],posts=[];let alive=true;
  const result={pipeline:'gemini-deepseek',ocr:{text:'<script>OCR</script>',provider:'gemini',model:'ocr-model',ms:10},grading:{status:'graded',score:8,points:10,feedback:'<img onerror=alert(1)>',provider:'deepseek',model:'grading-model',ms:20},usage:{calls:2,input_tokens:20,output_tokens:30,cached_tokens:0},elapsed_ms:30};
  const context={lang:'ko',cm:{me:role?{role}:null},esc:escape,sessionStorage:{setItem(){}},window:{addEventListener(){},removeEventListener(){}},
    URL:class extends URL{static createObjectURL(){return 'blob:test';}static revokeObjectURL(){}},cmApi:async(...args)=>{calls.push(args);return{pipelines};},cmBase:()=> 'https://example.com',cmTok:()=> 'session-token',
    arLoadScanner:async()=>({encodeUpload:async file=>file}),btoa,Uint8Array,AbortController,setTimeout,clearTimeout,
    fetch:async(url,options)=>{posts.push({url,options});return{ok:true,json:async()=>result};}};
  vm.createContext(context);vm.runInContext(block,context);
  return{context,root,nodes,fields,form,controls,calls,posts,result,current:()=>alive,stop:()=>{alive=false;}};
}
(async()=>{
  for(const role of [null,'user']){
    const a=harness(role);await a.context.arModelTest(a.root,a.current);assert.equal(a.calls.length,0);assert.ok(a.root.innerHTML.includes('개발자 계정만'));
  }
  const a=harness();await a.context.arModelTest(a.root,a.current);
  assert.equal(a.calls.length,1);assert.equal(a.calls[0][1],'/admin/lab/model-test');
  for(const label of ['1. Gemini OCR + Gemini 채점','2. Gemini OCR + DeepSeek 채점','3. DeepSeek OCR + DeepSeek 채점'])assert.ok(a.root.innerHTML.includes(label));
  a.fields.images.onchange();assert.equal(a.posts.length,0,'selecting a file must not make paid requests');
  await a.form.onsubmit({preventDefault(){}});
  assert.equal(a.posts.length,1);const request=JSON.parse(a.posts[0].options.body);
  assert.equal(request.pipeline,'gemini-deepseek');assert.equal(request.points,10);assert.equal(request.images[0].mime,'image/jpeg');assert.equal(request.images[0].data,'dGVzdA==');
  assert.ok(a.nodes.arModelResults.innerHTML.includes('&lt;script&gt;OCR&lt;/script&gt;'));
  assert.ok(!a.nodes.arModelResults.innerHTML.includes('<img onerror'));
  assert.ok(a.nodes.arModelResults.innerHTML.includes('8 / 10'));assert.equal(a.controls.disabled,false);
  const previous=a.nodes.arModelResults.innerHTML;a.form.events.input({target:{name:'pipeline'}});assert.equal(a.nodes.arModelResults.innerHTML,previous);
  a.form.events.input({target:{name:'problem'}});assert.equal(a.nodes.arModelResults.innerHTML,'');
  a.context.fetch=async()=>({ok:false,json:async()=>({error:'model_test_provider_failed',stage:'grading',provider:'deepseek',model:'deepseek-flash',ocr:{provider:'gemini',model:'ocr-model',text:'x=2',ms:10}})});
  await a.form.onsubmit({preventDefault(){}});
  assert.ok(a.nodes.arModelResults.innerHTML.includes('x=2'));assert.ok(a.nodes.arModelResults.innerHTML.includes('채점 미완료'));assert.ok(!a.nodes.arModelResults.innerHTML.includes('0 / 10'));
  const stale=harness();await stale.context.arModelTest(stale.root,stale.current);
  stale.context.fetch=async()=>{stale.stop();return{ok:true,json:async()=>stale.result};};
  await stale.form.onsubmit({preventDefault(){}});assert.equal(stale.nodes.arModelResults.innerHTML,'','stale route must not receive another result');
  const changed=harness();await changed.context.arModelTest(changed.root,changed.current);
  changed.context.fetch=async()=>{changed.context.cm.me={role:'user'};return{ok:true,json:async()=>changed.result};};
  await changed.form.onsubmit({preventDefault(){}});assert.equal(changed.nodes.arModelResults.innerHTML,'','changed account must not receive another result');
  const {priceModelTestStage,summarizeModelTestPricing}=await import('../community/src/model-test-pricing.js');
  const ocr={stage:'ocr',provider:'gemini',model:'gemini-flash-latest',resolved_model:'gemini-2.5-flash',calls:1,
    started_at:'2026-10-30T15:00:00.000Z',finished_at:'2026-10-30T15:00:00.500Z',ms:500,
    input_tokens:400,cached_tokens:100,uncached_input_tokens:300,output_tokens:60,reasoning_tokens:10,total_tokens:460,output_tokens_per_second:120,ok:true,usage_known:true};
  const grading={...ocr,stage:'grading',provider:'deepseek',model:'deepseek-flash',resolved_model:'deepseek-flash',
    input_tokens:900,cached_tokens:0,uncached_input_tokens:900,output_tokens:100,reasoning_tokens:40,total_tokens:1000,ms:800,output_tokens_per_second:125};
  const stages=[ocr,grading].map(stage=>({...stage,pricing:priceModelTestStage(stage)}));
  const usage={calls:2,input_tokens:1300,cached_tokens:100,uncached_input_tokens:1200,output_tokens:160,reasoning_tokens:50,total_tokens:1460,
    stages,pricing:summarizeModelTestPricing(stages)};
  const labels=a.context.arModelTestLabels();
  const detailed={...a.result,usage};
  const completeHtml=a.context.arModelTestResult(detailed,labels);
  for(const label of ['예상 총비용','단계별 시간·토큰·단가','요청 모델','응답 모델','비캐시 입력','생각 · 출력의 일부','100만 토큰당','1토큰당','단계 합계','공식 단가','2026-10-30'])assert.ok(completeHtml.includes(label),label);
  assert.ok(completeHtml.includes('gemini-flash-latest'));assert.ok(completeHtml.includes('gemini-2.5-flash'));
  assert.ok(completeHtml.includes('1,460'));assert.ok(completeHtml.includes('캐시 입력은 입력에'));
  assert.ok(completeHtml.includes('https://ai.google.dev/gemini-api/docs/pricing'));
  const missingStage={...grading,ok:false,usage_known:false,input_tokens:null,cached_tokens:null,uncached_input_tokens:null,output_tokens:null,reasoning_tokens:null,total_tokens:null};
  missingStage.pricing=priceModelTestStage(missingStage);
  const partialUsage={calls:2,total_tokens:null,incomplete:true,known_tokens:{total_tokens:460},stages:[stages[0],missingStage],pricing:summarizeModelTestPricing([stages[0],missingStage])};
  const partialHtml=a.context.arModelTestResult({...detailed,usage:partialUsage},labels);
  assert.ok(partialHtml.includes('확인된 부분합'));assert.ok(partialHtml.includes('총액 미확정'));assert.ok(partialHtml.includes('460 + ?'));
  const unknownHtml=a.context.arModelTestResult({...detailed,usage:{calls:1,total_tokens:null,incomplete:true,stages:[],pricing:{status:'unknown',incomplete:true,known_usd:0,priced_calls:0,total_usd:null}}},labels);
  assert.ok(unknownHtml.includes('미확정'));assert.ok(!unknownHtml.includes('$0'),'unknown total must not become zero dollars');
  const peak={...grading,started_at:'2026-10-30T02:00:00Z'};peak.pricing=priceModelTestStage(peak);
  const rangeHtml=a.context.arModelTestResult({...detailed,usage:{...usage,stages:[peak],pricing:summarizeModelTestPricing([peak])}},labels);
  assert.ok(rangeHtml.includes('예상 비용 범위'));assert.ok(rangeHtml.includes(' – $'));
  for(const unsafe of ['javascript:alert(1)','https://evil.test/','https://ai.google.dev@evil.test/','https://ai.google.dev.evil.test/'])assert.equal(a.context.arModelTestPriceLink(unsafe),'');
  assert.equal(a.context.arModelTestPriceLink('https://api-docs.deepseek.com/quick_start/pricing'),'https://api-docs.deepseek.com/quick_start/pricing');
  const unsafeSource={...stages[0],pricing:{...stages[0].pricing,source_url:'javascript:alert(1)'}};
  assert.ok(!a.context.arModelTestStage(unsafeSource,labels).includes('href="javascript:'));
  const failed=harness();await failed.context.arModelTest(failed.root,failed.current);
  const failedOcr={...missingStage,stage:'ocr',provider:'gemini',model:'gemini-flash-latest',ms:null};
  failedOcr.pricing=priceModelTestStage(failedOcr);
  failed.context.fetch=async()=>({ok:false,json:async()=>({error:'model_test_provider_auth',stage:'ocr',provider:'gemini',model:'gemini-flash-latest',
    usage:{calls:1,total_tokens:null,incomplete:true,stages:[failedOcr],pricing:summarizeModelTestPricing([failedOcr])},elapsed_ms:2000})});
  await failed.form.onsubmit({preventDefault(){}});
  assert.ok(failed.nodes.arModelResults.innerHTML.includes('data-model-result="gemini-deepseek"'));
  assert.ok(failed.nodes.arModelResults.innerHTML.includes('테스트 미완료'));assert.ok(failed.nodes.arModelResults.innerHTML.includes('총액 미확정'));
  assert.ok(failed.nodes.arModelResults.innerHTML.includes('반환된 OCR 결과가 없습니다.'));assert.ok(!failed.nodes.arModelResults.innerHTML.includes('0 / 10'));
  a.context.lang='en';assert.ok(a.context.arModelTestResult(detailed,a.context.arModelTestLabels()).includes('Estimated total · USD'));
  console.log('Developer UI: role gate, image flow, XSS, stale account, partial OCR, detailed timing/tokens/prices, unknown/range/partial costs and OCR-failure metrics PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
