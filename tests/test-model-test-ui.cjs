const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../arena.js'),'utf8');
const block=source.slice(source.indexOf('const AR_MODEL_PIPELINES ='));
const escape=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pipelines=['gemini-gemini','gemini-deepseek','deepseek-deepseek'].map(id=>({id,available:true,ocr:{provider:id.split('-')[0],model:'ocr-model'},grading:{provider:id.split('-')[1],model:'grading-model'}}));
function harness(role='admin'){
  const fields={pipeline:{value:'gemini-deepseek'},problem:{value:'Find x.'},rubric:{value:'x=2 is worth 10.'},points:{value:'10'},images:{files:[new Blob(['test'],{type:'image/jpeg'})]}};
  const controls={disabled:false},form={elements:{namedItem:n=>fields[n]},events:{},querySelector:()=>controls,addEventListener:(n,f)=>form.events[n]=f};
  const nodes={arModelTestForm:form,arModelStatus:{},arModelResults:{innerHTML:''},arModelEmpty:{},arModelPhotos:{innerHTML:''}};
  const root={innerHTML:'',querySelector:q=>nodes[q.slice(1)]};
  const calls=[],posts=[];let alive=true;
  const result={pipeline:'gemini-deepseek',ocr:{text:'<script>OCR</script>',provider:'gemini',model:'ocr-model',ms:10},grading:{status:'graded',score:8,points:10,feedback:'<img onerror=alert(1)>',provider:'deepseek',model:'grading-model',ms:20},usage:{calls:2,input_tokens:20,output_tokens:30,cached_tokens:0},elapsed_ms:30};
  const context={lang:'ko',cm:{me:role?{role}:null},esc:escape,sessionStorage:{setItem(){}},window:{addEventListener(){},removeEventListener(){}},
    URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},cmApi:async(...args)=>{calls.push(args);return{pipelines};},cmBase:()=> 'https://example.com',cmTok:()=> 'session-token',
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
  console.log('Developer UI: role gate, three choices, explicit submit, image payload, escaping, comparison reset, partial OCR and stale-account guards PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
