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
import { SCHEME_VERSION as REG_VERSION } from './src/grading-rules.js';

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
  let mathpixText='$v_0 = I_0 / M$ (mathpix)',failProvider=false,emptyWithTools=false,truncateReads=0,beforeProvider=async()=>{},limitModel=null,gradeReply=null,moderateReply=null;
  const old={fetch:globalThis.fetch,caches:globalThis.caches};globalThis.caches={default:{async match(){},async put(){}}};
  globalThis.fetch=async(input,init={})=>{
    const url=String(input);
    if(url.startsWith('https://github.com/')||url.startsWith('https://haslalab.org/pdfx/')||/https:\/\/www\.(kms|kmo)\.or\.kr\//.test(url))return new Response('%PDF-1.4\nSelected vision local reference fixture '+url);
    assert.ok(!url.includes('upstage'),'no production OCR request may reach Upstage');
    if(url.startsWith('https://api.mathpix.com/')){calls.push({provider:'mathpix',url,body:JSON.parse(init.body),parts:[],text:''});return Response.json({text:mathpixText,confidence:.9});}
    const body=JSON.parse(init.body),provider=url.includes('deepseek')?'deepseek':'gemini',parts=provider==='gemini'?body.contents[0].parts:body.messages[1].content;
    const text=parts.map(part=>part.text||'').join('\n');calls.push({provider,url,body,parts,text});
    const hook=beforeProvider;beforeProvider=async()=>{};await hook();
    if(failProvider)return new Response('{}',{status:503});
    if(emptyWithTools&&body.tools&&text.includes('[TASK: grade]'))return Response.json({model:body.model,choices:[{finish_reason:'stop',message:{content:''}}],usage:{prompt_tokens:100,completion_tokens:0}});
    if(limitModel&&url.includes('/'+limitModel+':'))return new Response('{}',{status:429});
    let raw;
    if(text.includes('[TASK: read page]')&&truncateReads>0){truncateReads--;return Response.json({modelVersion:VISION_MODELS.gemini,candidates:[{finishReason:'MAX_TOKENS',content:{parts:[{text:'{"text":"x x x'}]}}],usageMetadata:{promptTokenCount:100,candidatesTokenCount:6144}});}
    if(text.includes('[TASK: notation]'))raw={symbols:[{symbol:'\\sigma',meaning:'surface tension',unit:'N/m'},{symbol:'\\xi^*',meaning:'optimal ratio'}]};
    else if(text.includes('[TASK: proofread page]'))raw={fixes:[{from:'9.31 mm',to:'0.31 \\mu m'},{from:'not in the transcript',to:'x'}]};
    else if(text.includes('[TASK: read page]'))raw=pageReading;
    else if(text.includes('Review ONLY problem'))raw={problem_no:5,score:7,confidence:.98,verdict:'valid',summary:'Diagram supported argument.',strengths:[],gaps:[],evidence:[{page:1,quote:'',source:'image',box:[100,100,900,900],description:'A labelled geometric construction with direction arrows.',note:'Visible geometry checked.'}]};
    else if(text.includes('"task":"transcribe"'))raw={text:'',legible:true,confidence:.98,uncertainties:[],visuals:[{page:1,kind:'graph',description:'A graph and upward direction arrow.',box:[.1,.1,.9,.9]}]};
    else if(text.includes('[TASK: moderate]'))raw=moderateReply||{items:[{id:'R',found:true,page:1,score:1,rules:[],note:'',quote:''}]};
    else if(text.includes('[TASK: analyse solution]'))raw={parts:[{id:'G',points:2,results:[{expression:'v = sqrt(2 g h)'}],milestones:['energy conservation'],accepted_forms:['v^2 = 2 g h']}]};
    else if(text.includes('[TASK: build marking scheme]'))raw={points:2,items:[{id:'G',points:2,type:'derivation',role:'result',sheet:'answer',what:'v = sqrt(2 g h); accept v^2 = 2 g h'}],parts:[],total:2};
    else if(text.includes('[TASK: zoom read]'))raw={reads:[{id:'N',written:'1.59 · 10^18',value:1.59e18,sure:true,alternatives:[]},{id:'K',written:'7.9',value:7.9,sure:true,alternatives:[]}]};
    else if(text.includes('[TASK: grade]'))raw=gradeReply||visualGrade;
    else {const marker=text.match(/\[PHOTO [a-f0-9-]+\]/)?.[0]||'';raw={scores:[{id:'G',got:2,note:'Visible direction.',decision:'met',evidence:[marker]}],feedback:[],confidence:.98};}
    return provider==='gemini'?Response.json({modelVersion:url.match(/\/models\/([^/:]+):/)?.[1]||VISION_MODELS.gemini,candidates:[{finishReason:'STOP',content:{parts:[{text:JSON.stringify(raw)}]}}],usageMetadata:{promptTokenCount:100,candidatesTokenCount:50,cachedContentTokenCount:0}}):Response.json({model:body.model||VISION_MODELS.deepseek,choices:[{finish_reason:'stop',message:{content:JSON.stringify(raw)}}],usage:{prompt_tokens:100,completion_tokens:50,prompt_cache_hit_tokens:0,prompt_cache_miss_tokens:100}});
  };
  const api=async(path,{id=1,body,method=body===undefined?'GET':'POST',settings=env}={})=>{const response=await worker.fetch(new Request('https://vision.local/api'+path,{method,headers:{Authorization:'Bearer '+tokens[id],'Cache-Control':'no-cache',...(body===undefined?{}:{'Content-Type':'application/json'})},...(body===undefined?{}:{body:JSON.stringify(body)})}),settings);return{status:response.status,data:await response.json()};};
  const start=async(provider,id=1,review=true)=>api('/lab/start',{id,body:{comp:'ipho',year:2025,tasks:['T1'],review,...(provider?{provider}:{})}});
  const upload=async(token)=>{const response=await worker.fetch(new Request('https://vision.local/api/lab/up/pages?task=T1&kind=answer',{method:'PUT',headers:{'X-Lab-Token':token,'Content-Type':'image/jpeg'},body:scan}),env);return{status:response.status,data:await response.json()};};
  const drain=async()=>{let safety=0;while(queue.length){assert.ok(++safety<40);const item=queue.shift();sql.prepare('UPDATE lab_jobs SET available_at=0 WHERE id=?').run(item.body.jobId);await worker.queue({messages:[{body:item.body,ack(){},retry(){queue.push(item);}}]},env);}};
  const seedScheme=(sid,provider)=>{const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=[provider,VISION_MODELS[provider],REG_VERSION,entry.solution,entry.mark||''].join(':');sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:2,items:[{id:'G',points:2,type:'graph',sheet:'answer',what:'Label axes and fitted line with direction.',checks:[{check:'axes_labeled',points:1},{check:'fit_line',points:1}]}]}),'fixture:'+provider,t);};
  const problem=()=>{const r=sql.prepare("INSERT INTO problems(week,no,kind,subject,level,points,title_ko,title_en,body_ko,body_en,model_ko,model_en,rubric,opens_at,closes_at,created_at)VALUES('2098-W01',1,'essay','physics',1,2,'그래프','Graph','Graph task','Graph task','Direction','Direction',?,?,?,?)").run(JSON.stringify([{id:'G',name:'Direction',max:2,requirement:'Inspect actual graph direction.'}]),t-60,t+7200,t);return Number(r.lastInsertRowid);};
  const ocrPhoto=async(pid,provider,id=1)=>{const form=new FormData();form.append('image',new Blob([scan],{type:'image/jpeg'}),'graph.jpg');const response=await worker.fetch(new Request(`https://vision.local/api/ocr?mode=math&problem_id=${pid}${provider?'&provider='+provider:''}`,{method:'POST',headers:{Authorization:'Bearer '+tokens[id]},body:form}),env);return{status:response.status,data:await response.json()};};
  try{await run({sql,env,api,start,upload,drain,calls,seedScheme,problem,ocrPhoto,beforeProvider:fn=>{beforeProvider=fn;},fail:()=>{failProvider=true;},emptyTools:()=>{emptyWithTools=true;},mathpix:t=>{mathpixText=t;},truncate:n=>{truncateReads=n;},limit:m=>{limitModel=m;},replies:(g,mod)=>{gradeReply=g;moderateReply=mod;}});}finally{Object.assign(globalThis,old);sql.close();}
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

test('the language chosen when grading is requested is the report language, whatever the start or later site language',async()=>fixture(async({api,start,upload,drain,calls,seedScheme,sql})=>{
  const a=(await start('gemini')).data,sid=a.session.id;seedScheme(sid,'gemini');await upload(a.token);
  sql.prepare("UPDATE lab_sessions SET lang='en' WHERE id=?").run(sid);
  await api(`/lab/sessions/${sid}/pay?lang=ko`,{body:{provider:'gemini',lang:'ko'}});await drain();
  await api(`/lab/sessions/${sid}/submit?lang=en`,{body:{provider:'gemini',lang:'en'}});await drain();
  const done=(await api(`/lab/sessions/${sid}`)).data.session;
  assert.equal(done.status,'graded');
  const grade=calls.find(call=>call.text.includes('[TASK: grade]'));
  assert.ok(grade.text.includes('Write every note in English.'),'the language at 채점하기 (submit) wins over the one at payment');
  assert.equal(sql.prepare('SELECT lang FROM lab_sessions WHERE id=?').get(sid).lang,'en');
  await api(`/lab/sessions/${sid}/submit?lang=ko`,{body:{provider:'gemini',lang:'ko'}});
  assert.equal(sql.prepare('SELECT lang FROM lab_sessions WHERE id=?').get(sid).lang,'en','a graded sitting keeps its report language');
}));

test('a printed header read by the model never refiles a page: the student\'s task and sheet stand',async()=>fixture(async({api,start,upload,drain,sql})=>{
  const a=(await start('gemini')).data,sid=a.session.id;await upload(a.token);
  sql.prepare("UPDATE lab_pages SET kind='working' WHERE session_id=?").run(sid);   // filed as a working sheet; the model reads «answer»
  await api(`/lab/sessions/${sid}/pay`,{body:{provider:'gemini'}});await drain();
  const page=sql.prepare('SELECT task,kind,ocr_status,read FROM lab_pages WHERE session_id=?').get(sid);
  assert.equal(page.ocr_status,'done');
  assert.equal(JSON.parse(page.read).header.sheet,'answer','the header is kept for reference');
  assert.deepEqual([page.task,page.kind],['T1','working']);
}));

test('a page read caught in a repetition loop is capped and read once more, warmer (0.8), instead of failing the page',async()=>fixture(async({api,start,upload,drain,calls,sql,truncate})=>{
  const a=(await start('gemini')).data,sid=a.session.id;truncate(1);await upload(a.token);
  await api(`/lab/sessions/${sid}/pay`,{body:{provider:'gemini'}});await drain();
  const reads=calls.filter(c=>c.text.includes('[TASK: read page]'));
  assert.equal(reads.length,2);
  assert.deepEqual(reads.map(c=>c.body.generationConfig.maxOutputTokens),[32768,32768],'Gemini: its thinking shares the output budget');
  assert.deepEqual(reads.map(c=>c.body.generationConfig.temperature),[0,0.8]);
  assert.equal(sql.prepare('SELECT ocr_status FROM lab_pages WHERE session_id=?').get(sid).ocr_status,'done');
}));
test('bench read.boxes: the reader is asked for the box of every value as well, and only then',async()=>fixture(async({api,start,upload,drain,calls,sql,env})=>{
  env.LAB_PIPELINE='mixed';
  const a=(await start('deepseek')).data,sid=a.session.id;
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  const page=sql.prepare('SELECT id FROM lab_pages WHERE session_id=?').get(sid);
  sql.exec(`CREATE TABLE IF NOT EXISTS lab_bench (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, spec TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', output TEXT, created_at INTEGER NOT NULL DEFAULT (unixepoch()), finished_at INTEGER)`);
  const bench=async spec=>{const b=sql.prepare('INSERT INTO lab_bench(session_id,spec)VALUES(?,?)').run(sid,JSON.stringify(spec)).lastInsertRowid;
    const j=sql.prepare("INSERT INTO lab_jobs(job_key,kind,session_id,page_id,status,available_at,created_at,updated_at)VALUES(?,'bench',?,?,'pending',0,0,0)").run('bench:'+b,sid,b).lastInsertRowid;
    await env.LAB_JOBS.sendBatch([{body:{v:1,jobId:Number(j)}}]);await drain();return sql.prepare('SELECT * FROM lab_bench WHERE id=?').get(b);};
  for(const boxes of [true,false]){calls.length=0;
    const r=await bench({stage:'read',page_id:page.id,read:{provider:'gemini',model:'gemini-3.1-flash-lite',thinking:'low',boxes}});
    assert.equal(r.status,'done',r.output);
    const read=calls.find(c=>c.text.includes('[TASK: read page]'));
    assert.equal(read.text.includes('and for every value item the line where its number is written'),boxes);
    assert.equal(read.text.includes('Give box only for graphs'),!boxes);}
}));
test('LAB_KEEP_HOURS off keeps every photo: the cron purge removes nothing, and a number of hours still removes them',async()=>fixture(async({api,start,upload,drain,sql,env})=>{
  const a=(await start('deepseek')).data,sid=a.session.id;
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  sql.prepare("UPDATE lab_sessions SET status='graded',graded_at=? WHERE id=?").run(Math.floor(Date.now()/1000)-30*86400,sid);
  const cron=async()=>{const work=[];await worker.scheduled({scheduledTime:0},env,{waitUntil:p=>work.push(p)});await Promise.all(work);};
  const purged=()=>sql.prepare('SELECT count(*) n FROM lab_pages WHERE session_id=? AND purged_at IS NOT NULL').get(sid).n;
  env.LAB_KEEP_HOURS='off';await cron();assert.equal(purged(),0,'«off» keeps them');
  env.LAB_KEEP_HOURS='2';await cron();assert.equal(purged(),1,'two hours after grading they go');
}));
test('the admin model bench runs a stage with other models and keeps the result apart from the sitting',async()=>fixture(async({api,start,upload,drain,calls,sql,env})=>{
  env.LAB_PIPELINE='mixed';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:3,items:[
    {id:'G',points:2,type:'graph',sheet:'answer',what:'Label axes and fitted line with direction.',checks:[{check:'axes_labeled',points:1},{check:'fit_line',points:1}]},
    {id:'R',points:1,type:'derivation',role:'result',sheet:'answer',what:'Expression of the velocity'}]}),'fixture',Math.floor(Date.now()/1000));
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  const page=sql.prepare('SELECT id,read FROM lab_pages WHERE session_id=?').get(sid),metered=sql.prepare('SELECT count(*) n FROM lab_calls').get().n;
  sql.exec(`CREATE TABLE IF NOT EXISTS lab_bench (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, spec TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', output TEXT, created_at INTEGER NOT NULL DEFAULT (unixepoch()), finished_at INTEGER)`);
  const bench=async spec=>{const b=sql.prepare('INSERT INTO lab_bench(session_id,spec)VALUES(?,?)').run(sid,JSON.stringify(spec)).lastInsertRowid;
    const j=sql.prepare("INSERT INTO lab_jobs(job_key,kind,session_id,page_id,status,available_at,created_at,updated_at)VALUES(?,'bench',?,?,'pending',0,0,0)").run('bench:'+b,sid,b).lastInsertRowid;
    await env.LAB_JOBS.sendBatch([{body:{v:1,jobId:Number(j)}}]);await drain();return sql.prepare('SELECT * FROM lab_bench WHERE id=?').get(b);};
  calls.length=0;
  const read=await bench({stage:'read',page_id:page.id,read:{provider:'gemini',model:'gemini-3.6-flash',thinking:'low'}});
  assert.equal(read.status,'done');assert.equal(calls.length,1);
  assert.match(calls[0].url,/\/gemini-3\.6-flash:generateContent$/);assert.deepEqual(calls[0].body.generationConfig.thinkingConfig,{thinkingLevel:'low'});
  assert.equal(JSON.parse(read.output).calls[0].model,'gemini-3.6-flash');
  calls.length=0;
  const graded=await bench({stage:'grade',task:'T1',grade:{provider:'deepseek',model:'deepseek-v4-pro',images:false},moderate:{provider:'gemini',model:'gemini-2.5-flash'},reads:{[page.id]:Number(read.id)}});
  assert.equal(graded.status,'done',graded.output);
  const grade=calls.find(c=>c.text.includes('[TASK: grade]')),mod=calls.find(c=>c.text.includes('[TASK: moderate]'));
  assert.equal(grade.body.model,'deepseek-v4-pro');assert.ok(!grade.parts.some(part=>part.type==='image_url'),'a text-only grader is sent no photo');
  assert.match(mod.url,/\/gemini-2\.5-flash:generateContent$/);assert.deepEqual(mod.body.generationConfig.thinkingConfig,{thinkingBudget:0});
  assert.ok(JSON.stringify(mod.body).includes('inline_data')||JSON.stringify(mod.body).includes('inlineData'),'the moderator still sees the photo');
  const out=JSON.parse(graded.output);assert.equal(out.points,3);assert.ok(out.items.some(i=>i.id==='R'&&i.moderated));
  assert.equal(sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail,null,'the sitting is untouched');
  assert.equal(sql.prepare('SELECT read FROM lab_pages WHERE id=?').get(page.id).read,page.read,'its pages too');
  assert.equal(sql.prepare('SELECT count(*) n FROM lab_calls').get().n,metered,'and its metering');
}));
test('theory pages are read with the paper\'s notation and proofread: only the passages the proofreader corrects change',async()=>fixture(async({api,start,upload,drain,calls,sql,env})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-flash-lite';env.LAB_READ_NOTATION='on';env.LAB_PROOF_MODEL='gemini-3.1-pro-preview';env.LAB_PROOF_THINKING='low';
  const saved={...pageReading};Object.assign(pageReading,{text:'A.2 a_c = 9.31 mm\nA.3 K = 1.04 \\cdot 10^{-4}',items:[{label:'A.2',kind:'value',text:'a_c = 9.31 mm',crossed_out:false,value:9.31,unit:'mm'}]});
  try{
    const a=(await start('deepseek')).data,sid=a.session.id;
    sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
    await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
    const step=c=>['notation','proofread page','read page'].find(k=>c.text.includes('[TASK: '+k+']'));
    const notation=calls.filter(c=>step(c)==='notation'),read=calls.find(c=>step(c)==='read page'),proof=calls.find(c=>step(c)==='proofread page');
    assert.equal(notation.length,1);assert.match(notation[0].url,/gemini-3\.1-pro-preview/);assert.ok(JSON.stringify(notation[0].body).includes('application/pdf'),'built from the problem paper');
    assert.match(read.url,/gemini-3\.1-flash-lite/);assert.match(read.text,/\\sigma \(surface tension, N\/m\)/,'the reader sees the paper\'s symbols');
    assert.match(proof.url,/gemini-3\.1-pro-preview/);assert.deepEqual(proof.body.generationConfig.thinkingConfig,{thinkingLevel:'low'});assert.match(proof.text,/a_c = 9\.31 mm/);
    const page=sql.prepare('SELECT ocr,read FROM lab_pages WHERE session_id=?').get(sid),r=JSON.parse(page.read);
    assert.equal(page.ocr,'A.2 a_c = 0.31 \\mu m\nA.3 K = 1.04 \\cdot 10^{-4}','the misread passage is corrected, the rest kept');
    assert.equal(r.items[0].text,'a_c = 0.31 \\mu m');assert.equal(r.items[0].value,0.31);
    assert.equal(sql.prepare("SELECT count(*) n FROM lab_schemes WHERE source LIKE 'notation:%'").get().n,1,'the notation is kept for the next page and sitting');
  }finally{for(const k of Object.keys(pageReading))delete pageReading[k];Object.assign(pageReading,saved);}
}));
test('experiments go through the same pipeline: Gemini reads (red ink left out), DeepSeek grades, Gemini moderates',async()=>fixture(async({api,start,upload,drain,calls,sql,env})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';env.LAB_MODERATE_MODEL='gemini-3.1-flash-lite';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','experiment') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:3,items:[
    {id:'G',points:2,type:'graph',sheet:'answer',what:'Label axes and fitted line with direction.',checks:[{check:'axes_labeled',points:1},{check:'fit_line',points:1}]},
    {id:'R',points:1,type:'derivation',role:'result',sheet:'answer',what:'Expression of the velocity'}]}),'fixture',Math.floor(Date.now()/1000));
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  const step=c=>c.text.includes('[TASK: read page]')?'read':c.text.includes('[TASK: moderate]')?'moderate':c.text.includes('[TASK: grade]')?'grade':'other';
  const reads=calls.filter(c=>step(c)==='read'),grades=calls.filter(c=>step(c)==='grade'),mods=calls.filter(c=>step(c)==='moderate');
  assert.ok(reads.length&&reads.every(c=>/gemini-3\.1-pro-preview/.test(c.url)&&/red ink/.test(c.text)),'Gemini Pro reads and leaves red ink out');
  assert.ok(grades.length===1&&grades[0].provider==='deepseek','DeepSeek grades the experiment');
  assert.ok(mods.length===1&&/gemini-3\.1-flash-lite/.test(mods[0].url),'Gemini moderates what DeepSeek marked down');
  assert.match(grades[0].text,/R14\. Marks in red ink/,'the regulation tells the grader to ignore red marks');
  assert.equal((await api(`/lab/sessions/${sid}`)).data.session.status,'graded');
}));
test('Gemini 3.8 Flash grades alone: no moderation, and no papers beside the readings and photos',async()=>fixture(async({api,start,upload,drain,calls,sql,env})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:3,items:[
    {id:'G',points:2,type:'graph',sheet:'answer',what:'Label axes and fitted line with direction.',checks:[{check:'axes_labeled',points:1},{check:'fit_line',points:1}]},
    {id:'R',points:1,type:'derivation',role:'result',sheet:'answer',what:'Expression of the velocity'}]}),'fixture',Math.floor(Date.now()/1000));
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  const grades=calls.filter(c=>c.text.includes('[TASK: grade]')),mods=calls.filter(c=>c.text.includes('[TASK: moderate]'));
  assert.ok(grades.length===1&&/\/gemini-3\.8-flash:generateContent$/.test(grades[0].url),'3.8 Flash grades');
  assert.deepEqual(grades[0].body.generationConfig.thinkingConfig,{thinkingLevel:'low'});
  assert.equal(mods.length,0,'nothing moderates');
  assert.ok(!JSON.stringify(grades[0].body).includes('application/pdf'),'the grader works from the scheme, the readings and the photos');
  assert.equal((await api(`/lab/sessions/${sid}`)).data.session.status,'graded');
}));
test('Math-Verify in code: a final expression that is not the official one yet has full marks is looked at once more, with that fact',async()=>fixture(async({api,start,upload,drain,calls,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:3,items:[
    {id:'F',points:1.6,type:'derivation',sheet:'answer',what:'F = 2gLh^2(rho_1-rho_0)^2/(k^2 rho_1)',expr:'2*g*L*h^2*(rho_1-rho_0)^2/(k^2*rho_1)'},
    {id:'S',points:1.4,type:'derivation',sheet:'answer',what:'S = rho_1 g h',expr:'rho_1*g*h'}]}),'fixture',Math.floor(Date.now()/1000));   // S without a role, as DeepSeek writes them
  const item=(id,score,expr)=>({id,found:true,page:1,label:id,score,rules:[],note:'',quote:'',expr});
  replies({items:[item('F',1.6,'2*rho_1*g*h^2/k^2*(1-rho_0/rho_1)^2'),item('S',1.4,'g*h*rho_1')],feedback:[],review:{summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}},
    {items:[{id:'F',found:true,page:1,score:0,rules:[],note:'L is missing',quote:''}]});
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  const grade=calls.find(c=>c.text.includes('[TASK: grade]')),mods=calls.filter(c=>c.text.includes('[TASK: moderate]'));
  assert.match(grade.text,/expr: for an item whose scheme entry has expr/,'the grader is asked for the candidate\'s expression');
  assert.equal(mods.length,1,'one look at the doubted item');assert.match(mods[0].url,/gemini-3\.8-flash/,'by the grader\'s own model');
  assert.match(mods[0].text,/missing L/);assert.ok(!mods[0].text.includes('"id":"S"'),'an equivalent expression with its marks is not doubted');
  const items=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(items,/"id":"F"[^}]*"got":0/);assert.match(items,/"id":"S"[^}]*"got":1\.4/);
}));
test('LAB_GRADE_TOOLS: the DeepSeek grader gets the tools, and a paper it leaves unanswered with them is graded once more without',async()=>fixture(async({api,start,upload,drain,calls,sql,env,emptyTools})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='deepseek';env.LAB_MODERATE_PROVIDER='none';env.LAB_GRADE_TOOLS='on';emptyTools();
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:3,items:[
    {id:'G',points:2,type:'graph',sheet:'answer',what:'Label axes and fitted line with direction.',checks:[{check:'axes_labeled',points:1},{check:'fit_line',points:1}]},
    {id:'R',points:1,type:'derivation',role:'result',sheet:'answer',what:'Expression of the velocity'}]}),'fixture',Math.floor(Date.now()/1000));
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  const grades=calls.filter(c=>c.text.includes('[TASK: grade]'));
  assert.equal(grades.length,2,'with tools, then once without');
  assert.ok(grades[0].body.tools&&/call compare_expressions/.test(grades[0].text),'the first call offers the tools');
  assert.ok(!grades[1].body.tools&&!/call compare_expressions/.test(grades[1].text),'the second has neither tools nor their note');
  assert.equal((await api(`/lab/sessions/${sid}`)).data.session.status,'graded');
}));
test('LAB_FOCUS_READ: a value the code marks wrong is read once more by Mathpix; a misread power of ten is replaced',async()=>fixture(async({api,start,upload,drain,calls,sql,env,replies,mathpix})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='deepseek';env.LAB_MODERATE_PROVIDER='none';env.LAB_FOCUS_READ='on';env['mathpix_client-ID']='mp-id';env['mathpix_client-secret']='mp-secret';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:2,items:[
    {id:'N',points:0.6,type:'value',sheet:'answer',what:'n_c',ref:'1.59e18',unit:'m^-3'},
    {id:'K',points:1.4,type:'value',sheet:'answer',what:'k',ref:'4.2',unit:'m'}]}),'fixture',Math.floor(Date.now()/1000));
  const item=(id,value)=>({id,found:true,page:1,label:id,score:0,rules:[],note:'',quote:'',value,unit_ok:true});
  replies({items:[item('N',1.59e13),item('K',7.9)],feedback:[],review:{summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}});
  mathpix('C.3 Numerical value: $n_{c} \\approx 1,59 \\cdot 10^{18}$\nK: $k=7.9 \\mathrm{~m}$');
  const text=pageReading.text;pageReading.text='N: n_c = 1.59 × 10^{13} m^-3\nK: k = 7.9 m';
  try{
    await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
    await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  }finally{pageReading.text=text;}
  assert.equal(calls.filter(c=>c.provider==='mathpix').length,1,'one Mathpix call for the page');
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"N"[^}]*"got":0\.6/,'10^13 read again as 10^18');
  assert.match(detail,/"id":"K"[^}]*"got":0[,}]/,'a value Mathpix reads the same changes nothing');
  assert.equal(sql.prepare("SELECT count(*) n FROM lab_calls WHERE session_id=? AND step='focus' AND provider='mathpix'").get(sid).n,1,'metered');
}));
test('LAB_FOCUS_ENGINE gemini: the value the code marks wrong is read again by Gemini zooming into the photo itself',async()=>fixture(async({api,start,upload,drain,calls,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='deepseek';env.LAB_MODERATE_PROVIDER='none';env.LAB_FOCUS_READ='on';env.LAB_FOCUS_ENGINE='gemini';env.LAB_FOCUS_MODE='agentic';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:2,items:[
    {id:'N',points:0.6,type:'value',sheet:'answer',what:'n_c',ref:'1.59e18',unit:'m^-3'},
    {id:'K',points:1.4,type:'value',sheet:'answer',what:'k',ref:'4.2',unit:'m'}]}),'fixture',Math.floor(Date.now()/1000));
  const item=(id,value)=>({id,found:true,page:1,label:id,score:0,rules:[],note:'',quote:'',value,unit_ok:true});
  replies({items:[item('N',1.59e13),item('K',7.9)],feedback:[],review:{summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}});
  const text=pageReading.text;pageReading.text='N: n_c = 1.59 × 10^{13} m^-3\nK: k = 7.9 m';
  try{
    await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
    await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  }finally{pageReading.text=text;}
  const zoom=calls.filter(c=>c.text.includes('[TASK: zoom read]'));
  assert.equal(zoom.length,1,'one call for the page');assert.equal(calls.filter(c=>c.provider==='mathpix').length,0);
  assert.deepEqual(zoom[0].body.tools,[{code_execution:{}}]);assert.match(zoom[0].url,/gemini-3\.1-flash-lite/);
  assert.ok(!zoom[0].text.includes('1.59e13')&&!zoom[0].text.includes('1.59e18'),'blind: neither the first reading nor the official value');
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"N"[^}]*"got":0\.6/,'10^13 read again as 10^18');
  assert.match(detail,/"id":"K"[^}]*"got":0[,}]/,'a value read the same changes nothing');
  assert.equal(sql.prepare("SELECT count(*) n FROM lab_calls WHERE session_id=? AND step='focus' AND provider='gemini'").get(sid).n,1,'metered');
}));
test('a right value with a missing unit loses 0.1, not the item (R3); a step whose quote is not found is looked for again before R13 zeroes it',async()=>fixture(async({api,start,upload,drain,calls,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:2,items:[
    {id:'N',points:0.6,type:'value',sheet:'answer',what:'n_c',ref:'1.59e18',unit:'m^-3'},
    {id:'S1',points:0.7,type:'derivation',role:'step',sheet:'any',what:'Gauss law on a small cylinder'},
    {id:'S2',points:0.7,type:'derivation',role:'step',sheet:'any',what:'energy conservation'}]}),'fixture',Math.floor(Date.now()/1000));
  const g=(id,extra)=>({id,found:true,page:1,label:id,rules:[],note:'',...extra});
  replies({items:[g('N',{score:0.6,value:1.59e18,unit_ok:false,quote:'n_c = 1.59e18'}),g('S1',{score:0.7,quote:'2 pi r 2z g_r + pi r^2 g_z = 0'}),g('S2',{score:0.7,quote:'E_k + U = const'})],feedback:[],review:{summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}},
    {items:[g('S1',{score:0.7,quote:'',visual:{kind:'text',box:[400,100,450,900],description:'Gauss law: g_r 2z 2 pi r + g_z pi r^2 = 0 on the left half'}}),g('S2',{score:0,note:'not written'})]});
  const text=pageReading.text;pageReading.text='N: n_c = 1.59e18';
  try{
    await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
    await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  }finally{pageReading.text=text;}
  const mods=calls.filter(c=>c.text.includes('[TASK: moderate]'));
  assert.equal(mods.length,1,'one look at the two steps');assert.match(mods[0].text,/quote_missing/);
  assert.match(mods[0].text,/"id":"S1"/);assert.match(mods[0].text,/"id":"S2"/);assert.ok(!mods[0].text.includes('"id":"N"'),'the value is not doubted');
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"N"[^}]*"got":0\.5/,'0.6 less the 0.1 unit deduction');
  assert.match(detail,/"id":"S1"[^}]*"got":0\.7/,'seen in the photo');
  assert.match(detail,/"id":"S2"[^}]*"got":0[,}]/,'not written');
}));
test('units in code: an equivalent unit is the right unit, and a value in another unit is converted by code',async()=>fixture(async({api,start,upload,drain,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:3,items:[
    {id:'MU',points:1,type:'value',sheet:'answer',what:'magnetic moment',ref:'1.04',unit:'J T^-1'},
    {id:'V',points:1,type:'value',sheet:'answer',what:'speed',ref:'2500',unit:'m/s'},
    {id:'L',points:1,type:'value',sheet:'answer',what:'length',ref:'3.0',unit:'m'}]}),'fixture',Math.floor(Date.now()/1000));
  const g=(id,value,unit,extra={})=>({id,found:true,page:1,label:id,score:0,rules:[],note:'',quote:'',value,unit,unit_ok:false,...extra});
  replies({items:[g('MU',1.04,'A·m^2'),g('V',2.5,'km/s',{value_in_unit:2.5}),g('L',3.0,'s')],feedback:[],review:{summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}});
  const text=pageReading.text;pageReading.text='MU = 1.04 A m^2\nV = 2.5 km/s\nL = 3.0 s';
  try{
    await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
    await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  }finally{pageReading.text=text;}
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"MU"[^}]*"got":1[,}]/,'A·m² is J/T, whatever the grader thought');
  assert.match(detail,/"id":"V"[^}]*"got":1[,}]/,'2.5 km/s is 2500 m/s, converted by code');
  assert.match(detail,/"id":"L"[^}]*"got":0\.9/,'a value with a wrong unit loses 0.1');
}));
test('LAB_SCHEME_TWO_STAGE: the solution is analysed first, and the scheme is built with that analysis beside it',async()=>fixture(async({api,start,upload,drain,calls,sql,env})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';env.LAB_SCHEME_TWO_STAGE='on';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  const i=calls.findIndex(c=>c.text.includes('[TASK: analyse solution]')),j=calls.findIndex(c=>c.text.includes('[TASK: build marking scheme]'));
  assert.ok(i>=0&&j>i,'the analysis comes first');
  assert.match(calls[j].text,/<<ANALYSIS>>[^]*accepted_forms[^]*<<END>>/,'and goes beside the solution');
  assert.ok(sql.prepare("SELECT source FROM lab_schemes WHERE exam_key='ipho2025' AND task='T1'").all().some(r=>/#2:/.test(r.source)),'kept under its own key');
}));
test('an admin puts a purged page photo back from a saved copy: into R2, the page readable again',async()=>fixture(async({api,start,upload,sql,env})=>{
  const a=(await start('deepseek')).data,sid=a.session.id;await upload(a.token);   // into D1: no bucket yet
  const store=new Map();env.LAB_PAGES={async put(k,v,o){store.set(k,{v:new Uint8Array(v),o});},async get(k){const x=store.get(k);return x?{arrayBuffer:async()=>x.v.buffer}:null;},async delete(){}};
  const pid=sql.prepare('SELECT id FROM lab_pages WHERE session_id=?').get(sid).id;
  const send=(id,image,user=1)=>api(`/admin/lab/pages/${id}/photo`,{id:user,body:{image}});
  const jpeg=Buffer.concat([Buffer.from([0xff,0xd8,0xff,0xe0]),Buffer.alloc(2000,7)]).toString('base64');
  assert.equal((await send(pid,jpeg)).status,403,'admins only');
  sql.prepare("UPDATE users SET role='admin' WHERE id=1").run();
  assert.equal((await send(pid,jpeg)).data.restored,false,'a page that still has its photo is left alone');
  sql.prepare("UPDATE lab_pages SET data=X'',purged_at=1 WHERE id=?").run(pid);
  assert.equal((await send(pid,Buffer.alloc(3000,1).toString('base64'))).status,400,'only a JPEG or PNG');
  const r=await send(pid,jpeg);assert.equal(r.data.restored,true);
  const row=sql.prepare('SELECT r2_key,purged_at,mime FROM lab_pages WHERE id=?').get(pid);
  assert.ok(row.r2_key&&store.has(row.r2_key)&&row.purged_at===null&&row.mime==='image/jpeg');
}));
test('LAB_ONLY_PROVIDER: a sitting asked for Gemini runs on DeepSeek, and the start page offers DeepSeek alone',async()=>fixture(async({api,start,sql,env})=>{
  env.LAB_ONLY_PROVIDER='deepseek';
  const a=(await start('gemini')).data,sid=a.session.id;
  assert.equal(JSON.parse(sql.prepare('SELECT sources FROM lab_sessions WHERE id=?').get(sid).sources)._provider,'deepseek');
  const {visionCapabilities}=await import('./src/vision-provider.js'),caps=visionCapabilities(env);
  assert.equal(caps.default,'deepseek');assert.deepEqual(caps.providers.map(p=>[p.id,p.available]),[['gemini',false],['deepseek',true]]);
}));
test('LAB_READ_MATHPIX answer: an answer page carries Mathpix\'s transcript after the reader\'s; a failed call leaves the reading',async()=>fixture(async({api,start,upload,drain,calls,sql,env})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MATHPIX='answer';env['mathpix_client-ID']='mp-id';env['mathpix_client-secret']='mp-secret';
  const a=(await start('deepseek')).data,sid=a.session.id;
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  const page=sql.prepare('SELECT ocr,kind,ocr_status FROM lab_pages WHERE session_id=?').get(sid);
  assert.equal(page.kind,'answer');assert.equal(page.ocr_status,'done');
  assert.match(page.ocr,/<<SECOND TRANSCRIPT: Mathpix[\s\S]*\(mathpix\)[\s\S]*<<END SECOND TRANSCRIPT>>/);
  const mp=calls.filter(c=>c.provider==='mathpix');assert.equal(mp.length,1);assert.equal(mp[0].body.metadata.improve_mathpix,false);
  assert.equal(sql.prepare("SELECT count(*) n FROM lab_calls WHERE session_id=? AND step='ocr2' AND provider='mathpix'").get(sid).n,1,'metered');
}));
test('a paid sitting\'s pages are read whatever the account has read that day',async()=>fixture(async({api,start,upload,drain,sql})=>{
  const a=(await start('gemini')).data,sid=a.session.id;
  sql.prepare("INSERT OR REPLACE INTO ratelimits(k,start,n) VALUES('labocr:1',?,10000)").run(Math.floor(Date.now()/1000));
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'gemini'}});await drain();
  assert.equal(sql.prepare('SELECT ocr_status FROM lab_pages WHERE session_id=?').get(sid).ocr_status,'done');
}));
test('mixed pipeline: Gemini reads, DeepSeek grades, Gemini moderates only what DeepSeek marked down',async()=>fixture(async({api,start,upload,drain,calls,sql,env})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';env.LAB_MODERATE_MODEL='gemini-3.1-flash-lite';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:3,items:[
    {id:'G',points:2,type:'graph',sheet:'answer',what:'Label axes and fitted line with direction.',checks:[{check:'axes_labeled',points:1},{check:'fit_line',points:1}]},
    {id:'R',points:1,type:'derivation',role:'result',sheet:'answer',what:'Expression of the velocity'}]}),'fixture',Math.floor(Date.now()/1000));
  await upload(a.token);
  await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  const done=(await api(`/lab/sessions/${sid}`)).data.session,result=done.detail.tasks.T1;
  assert.equal(done.status,'graded');assert.equal(done.score,3,'DeepSeek missed R; Gemini found it in the photo');
  const step=c=>c.text.includes('[TASK: read page]')?'read':c.text.includes('[TASK: moderate]')?'moderate':c.text.includes('[TASK: grade]')?'grade':'other';
  assert.ok(calls.filter(c=>step(c)==='read').length>=1&&calls.filter(c=>step(c)==='read').every(c=>c.provider==='gemini'),'Gemini reads every page');
  assert.ok(calls.filter(c=>step(c)==='grade').length===1&&calls.filter(c=>step(c)==='grade').every(c=>c.provider==='deepseek'),'DeepSeek grades');
  assert.ok(!calls.filter(c=>step(c)==='grade').some(c=>c.text.includes('[Canonical ')),'the grader works from the scheme and pages, without the problem or solution PDFs');
  const mod=calls.filter(c=>step(c)==='moderate');assert.equal(mod.length,1);assert.equal(mod[0].provider,'gemini');
  assert.ok(calls.filter(c=>step(c)==='read').every(c=>/\/gemini-3\.1-pro-preview:generateContent$/.test(c.url)&&c.body.generationConfig.thinkingConfig?.thinkingLevel==='low'),'theory pages are read by the configured model and thinking level');
  assert.match(mod[0].url,/\/gemini-3\.1-flash-lite:generateContent$/,'moderation uses its own configured model');
  assert.match(mod[0].text,/visual:\{kind:"value"/,'a misread number is shown from the photo as visual evidence');
  assert.ok(mod[0].text.includes('"id":"R"')&&!mod[0].text.includes('"id":"G"'),'only the item DeepSeek marked down is moderated');
  assert.ok(!JSON.stringify(mod[0].body).includes('application/pdf'),'no problem or solution PDF in moderation');
  assert.equal(result.items.find(i=>i.id==='R').moderated,true);assert.match(result.grader,/moderated by/);
  const health=(await api('/health')).data,vision=health.vision||health.arena?.vision;assert.equal(vision?.pipeline,'mixed','the exam page shows the fixed pipeline');
}));

test('a page the reading model refuses for its quota is read by the fallback model at once',async()=>fixture(async({api,start,upload,drain,calls,sql,env,limit})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';env.LAB_READ_FALLBACK_MODEL='gemini-3.8-flash';
  limit('gemini-3.1-pro-preview');
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  const reads=calls.filter(c=>c.text.includes('[TASK: read page]'));
  assert.match(reads[0].url,/gemini-3\.1-pro-preview/);assert.match(reads[1].url,/gemini-3\.8-flash/,'the refused page goes straight to the fallback');
  assert.equal(sql.prepare('SELECT ocr_status FROM lab_pages WHERE session_id=?').get(sid).ocr_status,'done');
}));
