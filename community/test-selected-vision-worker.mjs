// Actual Worker + SQLite transactions. All provider/reference HTTP is a local fixture.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
import {MODEL_TEST_EXAMS} from './src/model-test-catalog.js';
import {VISION_MODELS} from './src/vision-provider.js';
import {ensureWeeklyContent} from './src/weekly-content.js';
import {normalizeMonthlyParts,guardMonthlyGrade} from './src/monthly-answers.js';
import {REG_VERSION} from './src/grading-rules.js';

const scan=Uint8Array.from([255,216,255,224,0,16,74,70,73,70,1,4,7,9,29,83]);
const digest=async value=>Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value))).toString('base64url');
const valueGraph={axes_labeled:true,axes_units:true,scale_ok:true,n_points:7,fit_line:true,slope_read:true,error_bars:true,title:true};
const pageReading={text:'',header:{task:'T1',sheet:'answer',page:1},legible:'good',confidence:.98,items:[]};
const visualGrade={items:[{id:'G',found:true,page:1,label:'G',score:2,decision:'met',rules:[],checks_met:['axes_labeled','fit_line'],note:'Visible graph and marked direction.',
  visual:{kind:'graph',box:[120,130,850,880],description:'A labelled graph with seven measurements and an upward fitted arrow.',graph:valueGraph}}],feedback:[],review:{summary:'Visible graph reviewed.',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}};

test('ordinary monthly theory photos earn only their matching server-validated visual marker',()=>{
  const problem={id:4,points:2},marker='[PHOTO:11111111-1111-4111-8111-111111111111:a]';
  const normalized=normalizeMonthlyParts(problem,{request_id:'photo-marker-theory'.padEnd(32,'x'),parts:[{id:'a',answer:marker,working:marker}]});
  const grade=()=>({score:2,detail:{scores:[{id:'a',max:2,got:2,evidence:[marker],note:'Visible graph.',decision:'met'}],feedback:[]}});
  assert.equal(guardMonthlyGrade(grade(),problem,normalized,'en').score,0,'pasted photo marker has no image authority');
  normalized.visualEvidence=new Map([['a',new Set([marker])]]);
  assert.equal(guardMonthlyGrade(grade(),problem,normalized,'en').score,2,'theory round supports owned graph photos too');
  normalized.visualEvidence=new Map([['b',new Set([marker])]]);
  assert.equal(guardMonthlyGrade(grade(),problem,normalized,'en').score,0,'another subquestion cannot lend its visual evidence');
});

// Tiny deterministic PDFium facade exercises real bounded PNG encoding; the
// renderer has separate tests against real PDFium and official graphical PDFs.
function renderer(){
  const heap=new Uint8Array(2*1024*1024);let width,height;
  return {pdfium:{HEAPU8:heap,wasmExports:{malloc:()=>1,free(){}}},FPDF_LoadMemDocument:()=>1,FPDF_GetPageCount:()=>2,
    FPDF_LoadPage:()=>1,FPDF_GetPageWidthF:()=>72,FPDF_GetPageHeightF:()=>72,FPDFBitmap_Create:(w,h)=>{width=w;height=h;return 1;},
    FPDFBitmap_FillRect:()=>heap.fill(255,32768,32768+width*height*4),FPDF_RenderPageBitmap:()=>{for(let i=0;i<80;i++)heap.fill(0,32768+i*(width+1)*4,32768+i*(width+1)*4+4);},
    FPDFBitmap_GetBuffer:()=>32768,FPDFBitmap_GetStride:()=>width*4,FPDFBitmap_Destroy(){},FPDF_ClosePage(){},FPDF_CloseDocument(){}};
}
async function fixture(run){
  const sql=new DatabaseSync(':memory:');for(const f of readdirSync(new URL('./migrations/',import.meta.url)).filter(f=>/^\d{4}_.*\.sql$/.test(f)).sort())sql.exec(readFileSync(new URL('./migrations/'+f,import.meta.url),'utf8'));
  const DB={prepare(query){const st=sql.prepare(query),make=args=>({bind:(...args)=>make(args),async first(){return st.get(...args)||null;},async all(){return{results:st.all(...args)};},async run(){return this.executeSync();},executeSync(){if(st.columns().length)return{results:st.all(...args)};const result=st.run(...args);return{results:[],meta:{changes:result.changes,last_row_id:Number(result.lastInsertRowid)}};}});return make([]);},async batch(statements){sql.exec('BEGIN');try{const results=statements.map(st=>st.executeSync());sql.exec('COMMIT');return results;}catch(error){sql.exec('ROLLBACK');throw error;}}};
  await ensureWeeklyContent(DB,DB);
  const t=Math.floor(Date.now()/1000),tokens={},queue=[],calls=[];
  for(const id of [1,2,3]){tokens[id]=('vision_test_'+id).padEnd(48,'x');sql.prepare("INSERT INTO users(id,username,nickname,pw,created_at,exam_tokens)VALUES(?,?,?,'unused',?,5)").run(id,'vision'+id,'Vision '+id,t);sql.prepare('INSERT INTO sessions VALUES(?,?,?,?)').run(await digest(tokens[id]),id,t,t+86400);}
  const env={DB,GEMINI_API_KEY:'local-gemini',DEEPSEEK_API_KEY:'local-deepseek',UPSTAGE_API_KEY:'must-never-be-used',LAB_KEEP_HOURS:'off',REFERENCE_PDFIUM_LOAD:async()=>renderer(),LAB_JOBS:{async sendBatch(items){queue.push(...items);}}};
  let failProvider=false,beforeProvider=async()=>{};
  const old={fetch:globalThis.fetch,caches:globalThis.caches};globalThis.caches={default:{async match(){},async put(){}}};
  globalThis.fetch=async(input,init={})=>{
    const url=String(input);
    if(url.startsWith('https://github.com/')||url.startsWith('https://haslalab.org/pdfx/')||/https:\/\/www\.(kms|kmo)\.or\.kr\//.test(url))return new Response('%PDF-1.4\nSelected vision local reference fixture '+url);
    assert.ok(!url.includes('upstage'),'no production OCR request may reach Upstage');
    const body=JSON.parse(init.body),provider=url.includes('deepseek')?'deepseek':'gemini',parts=provider==='gemini'?body.contents[0].parts:body.messages[1].content;
    const text=parts.map(part=>part.text||'').join('\n');calls.push({provider,url,body,parts,text});
    const hook=beforeProvider;beforeProvider=async()=>{};await hook();
    if(failProvider)return new Response('{}',{status:503});
    let raw;
    if(text.includes('[TASK: read page]'))raw=pageReading;
    else if(text.includes('Review ONLY problem'))raw={problem_no:5,score:7,confidence:.98,verdict:'valid',summary:'Diagram supported argument.',strengths:[],gaps:[],evidence:[{page:1,quote:'',source:'image',box:[100,100,900,900],description:'A labelled geometric construction with direction arrows.',note:'Visible geometry checked.'}]};
    else if(text.includes('"task":"transcribe"'))raw={text:'',legible:true,confidence:.98,uncertainties:[],visuals:[{page:1,kind:'graph',description:'A graph and upward direction arrow.',box:[.1,.1,.9,.9]}]};
    else if(text.includes('[TASK: grade]'))raw=visualGrade;
    else {const marker=text.match(/\[PHOTO [a-f0-9-]+\]/)?.[0]||'';raw={scores:[{id:'G',got:2,note:'Visible direction.',decision:'met',evidence:[marker]}],feedback:[],confidence:.98};}
    return provider==='gemini'?Response.json({modelVersion:VISION_MODELS.gemini,candidates:[{finishReason:'STOP',content:{parts:[{text:JSON.stringify(raw)}]}}],usageMetadata:{promptTokenCount:100,candidatesTokenCount:50,cachedContentTokenCount:0}}):Response.json({model:VISION_MODELS.deepseek,choices:[{finish_reason:'stop',message:{content:JSON.stringify(raw)}}],usage:{prompt_tokens:100,completion_tokens:50,prompt_cache_hit_tokens:0,prompt_cache_miss_tokens:100}});
  };
  const api=async(path,{id=1,body,method=body===undefined?'GET':'POST',settings=env}={})=>{const response=await worker.fetch(new Request('https://vision.local/api'+path,{method,headers:{Authorization:'Bearer '+tokens[id],'Cache-Control':'no-cache',...(body===undefined?{}:{'Content-Type':'application/json'})},...(body===undefined?{}:{body:JSON.stringify(body)})}),settings);return{status:response.status,data:await response.json()};};
  const start=async(provider,id=1,review=true)=>api('/lab/start',{id,body:{comp:'ipho',year:2025,tasks:['T1'],review,...(provider?{provider}:{})}});
  const upload=async(token)=>{const response=await worker.fetch(new Request('https://vision.local/api/lab/up/pages?task=T1&kind=answer',{method:'PUT',headers:{'X-Lab-Token':token,'Content-Type':'image/jpeg'},body:scan}),env);return{status:response.status,data:await response.json()};};
  const drain=async()=>{let safety=0;while(queue.length){assert.ok(++safety<40);const item=queue.shift();sql.prepare('UPDATE lab_jobs SET available_at=0 WHERE id=?').run(item.body.jobId);await worker.queue({messages:[{body:item.body,ack(){},retry(){queue.push(item);}}]},env);}};
  const seedScheme=(sid,provider)=>{const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=[provider,VISION_MODELS[provider],REG_VERSION,entry.solution,entry.mark||''].join(':');sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:2,items:[{id:'G',points:2,type:'graph',sheet:'answer',what:'Label axes and fitted line with direction.',checks:[{check:'axes_labeled',points:1},{check:'fit_line',points:1}]}]}),'fixture:'+provider,t);};
  const problem=()=>{const r=sql.prepare("INSERT INTO problems(week,no,kind,subject,level,points,title_ko,title_en,body_ko,body_en,model_ko,model_en,rubric,opens_at,closes_at,created_at)VALUES('2098-W01',1,'essay','physics',1,2,'그래프','Graph','Graph task','Graph task','Direction','Direction',?,?,?,?)").run(JSON.stringify([{id:'G',name:'Direction',max:2,requirement:'Inspect actual graph direction.'}]),t-60,t+7200,t);return Number(r.lastInsertRowid);};
  const ocrPhoto=async(pid,provider,id=1)=>{const form=new FormData();form.append('image',new Blob([scan],{type:'image/jpeg'}),'graph.jpg');const response=await worker.fetch(new Request(`https://vision.local/api/ocr?mode=math&problem_id=${pid}${provider?'&provider='+provider:''}`,{method:'POST',headers:{Authorization:'Bearer '+tokens[id]},body:form}),env);return{status:response.status,data:await response.json()};};
  try{await run({sql,env,api,start,upload,drain,calls,seedScheme,problem,ocrPhoto,beforeProvider:fn=>{beforeProvider=fn;},fail:()=>{failProvider=true;}});}finally{Object.assign(globalThis,old);sql.close();}
}

test('grading mode spends its token when the sitting opens: the provider is pinned then, and an unpaid start leaves nothing open',async()=>fixture(async({api,start,sql,calls})=>{
  const before=sql.prepare('SELECT exam_tokens,exam_half FROM users WHERE id=1').get();
  const none=await start();assert.equal(none.data.error,'provider_required');
  assert.equal(sql.prepare('SELECT COUNT(*) n FROM lab_sessions WHERE user_id=1').get().n,0,'a start that could not be paid for is removed');
  const a=(await start('deepseek')).data,sid=a.session.id;assert.equal(a.session.paid,true);assert.equal(a.session.provider,'deepseek');assert.equal(a.session.provider_locked,true);
  assert.equal(sql.prepare("SELECT count(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n,1);
  assert.notDeepEqual(sql.prepare('SELECT exam_tokens,exam_half FROM users WHERE id=1').get(),before,'the token is spent at the first press');
  const again=(await start('deepseek')).data;assert.equal(again.session.id,sid);assert.equal(again.resumed,true);
  assert.equal(sql.prepare("SELECT count(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n,1,'coming back does not spend again');
  assert.equal((await api(`/lab/sessions/${sid}/provider`,{body:{provider:'gemini'}})).data.error,'provider_locked');assert.equal(calls.length,0);
}));

test('free choice is owner-only and editable; first paid operation atomically pins one concurrent provider',async()=>fixture(async({api,start,upload,sql,calls})=>{
  const a=(await start(undefined,1,false)).data,sid=a.session.id;assert.equal(a.session.provider,null);await upload(a.token);
  assert.equal((await api(`/lab/sessions/${sid}/pay`,{body:{}})).data.error,'provider_required');
  assert.equal(sql.prepare('SELECT charged FROM lab_sessions WHERE id=?').get(sid).charged,0);assert.equal(calls.length,0);
  assert.equal((await api(`/lab/sessions/${sid}/provider`,{id:2,body:{provider:'gemini'}})).status,404);
  assert.equal((await api(`/lab/sessions/${sid}/provider`,{body:{provider:'gemini'}})).data.session.provider_locked,false);
  assert.equal((await api(`/lab/sessions/${sid}/provider`,{body:{provider:'deepseek'}})).data.session.provider,'deepseek');
  const results=await Promise.all(['gemini','deepseek'].map(provider=>api(`/lab/sessions/${sid}/pay`,{body:{provider}})));
  assert.equal(results.filter(r=>r.status===200).length,1);assert.equal(results.find(r=>r.status!==200).data.error,'provider_locked');
  const saved=(await api(`/lab/sessions/${sid}`)).data.session;assert.equal(saved.provider_locked,true);
  assert.equal((await api(`/lab/sessions/${sid}/provider`,{body:{provider:saved.provider}})).data.session.provider_locked,true,'stale free save must not clear the pin');
  assert.equal(sql.prepare("SELECT count(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n,1);assert.equal(calls.length,0,'payment only schedules IDs');
}));

test('a previously paid legacy session requires an explicit first provider and pins it without another charge',async()=>fixture(async({api,start,sql,calls})=>{
  const a=(await start(undefined,1,false)).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET charged=1,sources=json_set(sources,'$._legacy','preserved') WHERE id=?").run(sid);
  sql.prepare("INSERT INTO lab_ledger(user_id,delta,reason,note,session_id,created_at)VALUES(1,-1,'grade','legacy',?,?)").run(sid,Math.floor(Date.now()/1000));
  assert.equal((await api(`/lab/sessions/${sid}/provider`,{body:{}})).data.error,'provider_required');
  const selected=await api(`/lab/sessions/${sid}/provider`,{body:{provider:'deepseek'}});
  assert.equal(selected.status,200);assert.equal(selected.data.session.provider,'deepseek');assert.equal(selected.data.session.provider_locked,true);
  assert.equal((await api(`/lab/sessions/${sid}/provider`,{body:{provider:'gemini'}})).data.error,'provider_locked');
  assert.equal(sql.prepare("SELECT count(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n,1);
  assert.equal(JSON.parse(sql.prepare('SELECT sources FROM lab_sessions WHERE id=?').get(sid).sources)._legacy,'preserved');assert.equal(calls.length,0);
}));

for(const provider of ['gemini','deepseek'])test(`${provider}: empty graph transcript still reaches the same original-image grader and code validates visual evidence`,async()=>fixture(async({api,start,upload,drain,calls,seedScheme,sql})=>{
  const a=(await start(provider)).data,sid=a.session.id;seedScheme(sid,provider);await upload(a.token);
  assert.equal((await api(`/lab/sessions/${sid}/pay`,{body:{provider}})).status,200);await drain();
  assert.equal((await api(`/lab/sessions/${sid}`)).data.session.pages[0].text,'','a graphical answer may have no text');
  await api(`/lab/sessions/${sid}/submit`,{body:{provider}});await drain();
  const done=(await api(`/lab/sessions/${sid}`)).data.session;assert.equal(done.status,'graded');assert.equal(done.score,2);
  const result=done.detail.tasks.T1;assert.equal(result.items[0].evidence.source,'image');assert.equal(result.items[0].evidence.page,1);
  assert.ok(calls.length>=2);assert.ok(calls.every(call=>call.provider===provider));
  const grade=calls.find(call=>call.text.includes('[TASK: grade]'));assert.ok(grade);const json=JSON.stringify(grade.body);assert.ok(json.includes(Buffer.from(scan).toString('base64')),'original bytes, not only transcript');
  if(provider==='deepseek'){assert.ok(!json.includes('application/pdf'));assert.ok(json.includes('data:image/png;base64,'),'canonical graphical reference is rendered to image');}
  else assert.ok(json.includes('application/pdf'),'canonical problem/solution including diagrams reaches Gemini');
  assert.equal(sql.prepare("SELECT count(*) n FROM lab_calls WHERE provider<>?").get(provider).n,0);
}));

test('a selected-provider outage cannot contact the other configured provider or revive legacy Upstage OCR',async()=>fixture(async({api,start,upload,drain,calls,fail,sql})=>{
  const a=(await start('deepseek')).data;await upload(a.token);await api(`/lab/sessions/${a.session.id}/pay`,{body:{provider:'deepseek'}});fail();await drain();
  assert.ok(calls.length>0);assert.ok(calls.every(call=>call.provider==='deepseek'));
  const page=sql.prepare('SELECT ocr_status FROM lab_pages WHERE session_id=?').get(a.session.id);assert.equal(page.ocr_status,'failed');
  assert.equal((await api(`/lab/sessions/${a.session.id}/provider`,{body:{provider:'gemini'}})).data.error,'provider_locked');
}));

for(const provider of ['gemini','deepseek'])test(`${provider}: generic OCR retains owner-bound original photo for graph-only final grading`,async()=>fixture(async({api,problem,ocrPhoto,calls,sql})=>{
  const pid=problem();assert.equal((await ocrPhoto(pid,null)).data.error,'provider_required');assert.equal(calls.length,0);
  const photo=await ocrPhoto(pid,provider);assert.equal(photo.status,200);assert.equal(photo.data.text,'');assert.ok(photo.data.photo_id);
  assert.equal((await api(`/problems/${pid}/submit`,{id:2,body:{provider,answer:'',photo_ids:[photo.data.photo_id]}})).status,404);
  assert.equal((await api(`/problems/${pid}/submit`,{body:{provider:provider==='gemini'?'deepseek':'gemini',answer:'',photo_ids:[photo.data.photo_id]}})).data.error,'provider_locked');
  const r=await api(`/problems/${pid}/submit`,{body:{provider,answer:'',photo_ids:[photo.data.photo_id],via_ocr:true}});assert.equal(r.status,200);assert.equal(r.data.status,'graded');assert.equal(r.data.score,2);
  assert.ok(calls.every(call=>call.provider===provider));assert.ok(JSON.stringify(calls.at(-1).body).includes(Buffer.from(scan).toString('base64')));
  assert.equal(sql.prepare('SELECT count(*) n FROM submissions').get().n,1,'foreign or mismatched evidence consumes no attempt');
  sql.prepare('UPDATE vision_photo_evidence SET expires_at=0').run();const count=calls.length;
  assert.equal((await api(`/problems/${pid}/submit`,{body:{provider,answer:'graph',photo_ids:[photo.data.photo_id]}})).data.error,'photo_not_found');assert.equal(calls.length,count);
}));

for(const provider of ['gemini','deepseek'])test(`${provider}: KMO image-only geometric work receives two independent same-provider reviews`,async()=>fixture(async({api,drain,calls,sql})=>{
  const a=await api('/lab/contest/start',{body:{provider,examId:'kmo-2025-T2-s2',runId:'visual-kmo-local'}});assert.equal(a.status,200);
  const sid=a.data.session.id;
  sql.prepare(`INSERT INTO lab_pages(session_id,no,task,kind,mime,data,ocr,ocr_status,text,edited,read,legible,created_at)
    VALUES(?,1,'Q5','answer','image/jpeg',?,'','done','',1,?,'good',?)`).run(sid,scan,JSON.stringify(pageReading),Math.floor(Date.now()/1000));
  assert.equal((await api(`/lab/sessions/${sid}/submit`,{body:{provider}})).status,200);await drain();
  const final=(await api(`/lab/sessions/${sid}`)).data.session,proof=final.detail.tasks.Q5;
  assert.equal(final.status,'graded');assert.equal(proof.score,7);assert.equal(proof.verification.passes,2);
  assert.equal(proof.feedback[0].source,'image');assert.equal(calls.length,2);assert.ok(calls.every(call=>call.provider===provider));
  for(const call of calls){const body=JSON.stringify(call.body);assert.ok(body.includes(Buffer.from(scan).toString('base64')));assert.ok(!body.includes('Diagram supported argument.'),'second pass never receives first judgment');
    assert.ok(provider==='gemini'?body.includes('application/pdf'):body.includes('data:image/png;base64,'));}
  assert.equal(sql.prepare("SELECT count(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n,1);
}));

test('oversized combined legacy photographs are rejected before another OCR or final grading call',async()=>fixture(async({api,ocrPhoto,problem,calls,sql})=>{
  const pid=problem(),photo=await ocrPhoto(pid,'gemini');assert.equal(photo.status,200);
  sql.prepare('UPDATE vision_photo_evidence SET bytes=?').run(12*1024*1024);
  const before=calls.length,r=await ocrPhoto(pid,'gemini');assert.equal(r.status,413);assert.equal(r.data.error,'photo_storage_limit');assert.equal(calls.length,before);
  sql.prepare('UPDATE vision_photo_evidence SET bytes=bytes+1').run();
  const grade=await api(`/problems/${pid}/submit`,{body:{provider:'gemini',answer:'Graph',photo_ids:[photo.data.photo_id]}});
  assert.equal(grade.status,413);assert.equal(grade.data.error,'scan_too_large');assert.equal(calls.length,before);assert.equal(sql.prepare('SELECT count(*) n FROM submissions').get().n,0);
}));

test('an OCR finishing after account deletion cannot recreate private legacy photo bytes',async()=>fixture(async({api,ocrPhoto,problem,beforeProvider,sql})=>{
  const pid=problem();beforeProvider(async()=>{assert.equal((await api('/me',{method:'DELETE'})).status,200);});
  const result=await ocrPhoto(pid,'gemini');assert.equal(result.status,401);assert.equal(result.data.error,'login_required');
  assert.equal(sql.prepare('SELECT count(*) n FROM vision_photo_evidence').get().n,0);assert.equal(sql.prepare('SELECT count(*) n FROM vision_photo_chunks').get().n,0);
}));
