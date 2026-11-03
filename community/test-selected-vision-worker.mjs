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
  const curatedSchemes={};
  let mathpixText='$v_0 = I_0 / M$ (mathpix)',failProvider=false,emptyWithTools=false,truncateReads=0,beforeProvider=async()=>{},limitModel=null,gradeReply=null,moderateReply=null,reviewReply=null,auditReply=null;
  const old={fetch:globalThis.fetch,caches:globalThis.caches};globalThis.caches={default:{async match(){},async put(){}}};
  globalThis.fetch=async(input,init={})=>{
    const url=String(input);
    if(url.startsWith('https://haslalab.org/schemes/')){const k=url.slice('https://haslalab.org/schemes/'.length).replace(/\.json$/,'');return curatedSchemes[k]?Response.json(curatedSchemes[k]):new Response('not found',{status:404});}
    if(url.startsWith('https://github.com/')||url.startsWith('https://haslalab.org/pdfx/')||/https:\/\/www\.(kms|kmo)\.or\.kr\//.test(url))return new Response('%PDF-1.4\nSelected vision local reference fixture '+url);
    assert.ok(!url.includes('upstage'),'no production OCR request may reach Upstage');
    if(url.startsWith('https://api.mathpix.com/')){calls.push({provider:'mathpix',url,body:JSON.parse(init.body),parts:[],text:''});return Response.json({text:mathpixText,confidence:.9});}
    if(url==='https://oauth2.googleapis.com/token')return Response.json({access_token:'ya29.local'});
    const body=JSON.parse(init.body),provider=url.includes('deepseek')?'deepseek':'gemini',parts=provider==='gemini'?body.contents[0].parts:body.messages[1].content;
    const text=parts.map(part=>part.text||'').join('\n');calls.push({provider,url,body,parts,text});
    const hook=beforeProvider;beforeProvider=async()=>{};await hook();
    if(failProvider)return new Response('{}',{status:503});
    if(emptyWithTools&&body.tools&&text.includes('[TASK: grade]'))return Response.json({model:body.model,choices:[{finish_reason:'stop',message:{content:''}}],usage:{prompt_tokens:100,completion_tokens:0}});
    if(limitModel&&url.includes('/'+limitModel+':')&&!url.includes('aiplatform.googleapis.com'))return new Response('{}',{status:429});
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
    else if(text.includes('[TASK: review marking scheme]'))raw=reviewReply||{fixes:[]};
    else if(text.includes('[TASK: audit steps]'))raw=auditReply||{items:[]};
    else if(text.includes('[TASK: grade]'))raw=Array.isArray(gradeReply)?(gradeReply.length>1?gradeReply.shift():gradeReply[0]):gradeReply||visualGrade;
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
  try{await run({sql,env,api,start,upload,drain,calls,seedScheme,problem,ocrPhoto,beforeProvider:fn=>{beforeProvider=fn;},fail:()=>{failProvider=true;},emptyTools:()=>{emptyWithTools=true;},mathpix:t=>{mathpixText=t;},truncate:n=>{truncateReads=n;},limit:m=>{limitModel=m;},curated:(k,v)=>{curatedSchemes[k]=v;},replies:(g,mod)=>{gradeReply=g;moderateReply=mod;},review:r=>{reviewReply=r;},audit:r=>{auditReply=r;}});}finally{Object.assign(globalThis,old);sql.close();}
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
  assert.deepEqual(reads.map(c=>c.body.generationConfig.maxOutputTokens),[10240,10240],'Gemini: its thinking shares the output budget, and a loop ends at 10k (LAB_READ_MAX_TOKENS)');
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
  const graded=await bench({stage:'grade',task:'T1',grade:{provider:'deepseek',model:'deepseek-v4-pro',images:false,lessons:'L1: a final expression with an extra term is wrong, however close it looks.'},moderate:{provider:'gemini',model:'gemini-2.5-flash'},reads:{[page.id]:Number(read.id)}});
  assert.equal(graded.status,'done',graded.output);
  const grade=calls.find(c=>c.text.includes('[TASK: grade]')),mod=calls.find(c=>c.text.includes('[TASK: moderate]'));
  assert.equal(grade.body.model,'deepseek-v4-pro');
  for(const c of [grade,mod])assert.ok(c.text.indexOf('L1: a final expression with an extra term')>-1&&c.text.indexOf('[Lessons from audited past gradings')<c.text.indexOf(c===grade?'[Exam context]':'[TASK: moderate]'),'the lessons sit after the regulation, before the paper');assert.ok(!grade.parts.some(part=>part.type==='image_url'),'a text-only grader is sent no photo');
  assert.match(mod.url,/\/gemini-2\.5-flash:generateContent$/);assert.deepEqual(mod.body.generationConfig.thinkingConfig,{thinkingBudget:0});
  assert.ok(JSON.stringify(mod.body).includes('inline_data')||JSON.stringify(mod.body).includes('inlineData'),'the moderator still sees the photo');
  const out=JSON.parse(graded.output);assert.equal(out.points,3);assert.ok(out.items.some(i=>i.id==='R'&&i.moderated));
  assert.equal(sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail,null,'the sitting is untouched');
  assert.equal(sql.prepare('SELECT read FROM lab_pages WHERE id=?').get(page.id).read,page.read,'its pages too');
  assert.equal(sql.prepare('SELECT count(*) n FROM lab_calls').get().n,metered,'and its metering');
}));
test('bench grade.chat: the papers, photos and transcripts with a short instruction, one score sheet, and only the sum in code',async()=>fixture(async({api,start,upload,drain,calls,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:3,items:[
    {id:'S',points:1,type:'derivation',role:'step',sheet:'any',what:'Newton\'s law for the orbit'},{id:'R',points:2,type:'derivation',role:'result',sheet:'answer',what:'Expression of the velocity'}]}),'fixture',Math.floor(Date.now()/1000));
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  const page=sql.prepare('SELECT id FROM lab_pages WHERE session_id=?').get(sid);
  sql.exec(`CREATE TABLE IF NOT EXISTS lab_bench (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, spec TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', output TEXT, created_at INTEGER NOT NULL DEFAULT (unixepoch()), finished_at INTEGER)`);
  const bench=async spec=>{const b=sql.prepare('INSERT INTO lab_bench(session_id,spec)VALUES(?,?)').run(sid,JSON.stringify(spec)).lastInsertRowid;
    const j=sql.prepare("INSERT INTO lab_jobs(job_key,kind,session_id,page_id,status,available_at,created_at,updated_at)VALUES(?,'bench',?,?,'pending',0,0,0)").run('bench:'+b,sid,b).lastInsertRowid;
    await env.LAB_JOBS.sendBatch([{body:{v:1,jobId:Number(j)}}]);await drain();return sql.prepare('SELECT * FROM lab_bench WHERE id=?').get(b);};
  const read=await bench({stage:'read',page_id:page.id,read:{provider:'gemini',model:'gemini-3.6-flash',thinking:'low'}});
  replies({analysis:'A: correct.',items:[{id:'S',score:1,note:'implied'},{id:'R',score:5,note:'too many'}]},null);
  calls.length=0;
  const graded=await bench({stage:'grade',task:'T1',grade:{provider:'gemini',model:'gemini-3.8-flash',thinking:'low',chat:true},reads:{[page.id]:Number(read.id)}});
  assert.equal(graded.status,'done',graded.output);
  assert.equal(calls.length,1,'one call, no recheck');
  const c=calls[0];assert.match(c.text,/A teacher hands you one student's paper/);assert.match(c.text,/S \| 1 \| Newton's law for the orbit/,'the score sheet');
  assert.ok(!/R13|R9/.test(c.text),'no grading rules');assert.ok(JSON.stringify(c.body).includes('application/pdf'),'the official papers go with it');
  const out=JSON.parse(graded.output);
  assert.equal(out.score,3,'each line capped at its points, then added');assert.deepEqual(out.items.map(i=>[i.id,i.got]),[['S',1],['R',2]]);
  assert.equal(out.analysis,'A: correct.');
}));
test('bench stage gcp: what GOOGLE_CLOUD_API_KEY can do (an express call, the tuning-jobs list, buckets), statuses only, never the key',async()=>fixture(async({start,drain,sql,env})=>{
  const a=(await start('deepseek')).data,sid=a.session.id,key='AIza'+'k'.repeat(35);env.GOOGLE_CLOUD_API_KEY=key;
  sql.exec(`CREATE TABLE IF NOT EXISTS lab_bench (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, spec TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', output TEXT, created_at INTEGER NOT NULL DEFAULT (unixepoch()), finished_at INTEGER)`);
  const b=sql.prepare('INSERT INTO lab_bench(session_id,spec)VALUES(?,?)').run(sid,JSON.stringify({stage:'gcp',project:'my-proj-1'})).lastInsertRowid;
  const j=sql.prepare("INSERT INTO lab_jobs(job_key,kind,session_id,page_id,status,available_at,created_at,updated_at)VALUES(?,'bench',?,?,'pending',0,0,0)").run('bench:'+b,sid,b).lastInsertRowid;
  const seen=[],old=globalThis.fetch;
  globalThis.fetch=async(url,init)=>{const u=String(url);if(!/googleapis\.com/.test(u))return old(url,init);seen.push({u,key:init?.headers?.['x-goog-api-key']});
    return new Response(JSON.stringify({error:{message:'API keys are not supported by this API. Got '+key}}),{status:401});};
  try{await env.LAB_JOBS.sendBatch([{body:{v:1,jobId:Number(j)}}]);await drain();}finally{globalThis.fetch=old;}
  const row=sql.prepare('SELECT status,output FROM lab_bench WHERE id=?').get(b),out=JSON.parse(row.output);
  assert.equal(row.status,'done',row.output);
  assert.deepEqual(seen.map(x=>x.u),['https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-3.1-flash-lite:generateContent',
    'https://us-central1-aiplatform.googleapis.com/v1/projects/my-proj-1/locations/us-central1/tuningJobs','https://storage.googleapis.com/storage/v1/b?project=my-proj-1']);
  assert.ok(seen.every(x=>x.key===key),'the key goes in the header');
  assert.equal(out.tuning.status,401);assert.ok(!row.output.includes(key),'and never into the result');
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
  env.LAB_MISSING_RECHECK='off';   // its grade reply leaves items out on purpose; the re-ask has its own test
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
  env.LAB_MISSING_RECHECK='off';   // its grade reply leaves items out on purpose; the re-ask has its own test
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
test('an item the grader left out is graded once more, and a step found again in the photos keeps its marks without a matching quote',async()=>fixture(async({api,start,upload,drain,calls,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:2,items:[
    {id:'S1',points:0.7,type:'derivation',role:'step',sheet:'any',what:'Gauss law on a small cylinder'},
    {id:'M',points:0.6,type:'derivation',role:'step',sheet:'any',what:'energy conservation'},
    {id:'X/1',points:0.7,type:'derivation',role:'result',sheet:'any',alt:'X/1',what:'method one'}]}),'fixture',Math.floor(Date.now()/1000));
  const g=(id,extra)=>({id,found:true,page:1,label:id,rules:[],note:'',...extra});
  replies({items:[g('S1',{score:0.7,quote:'2 pi r 2z g_r + pi r^2 g_z = 0'})],feedback:[],review:{summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}},
    {items:[g('S1',{score:0.7,quote:'Gauss on the cylinder, second line'}),g('M',{score:0.6,quote:'E_k + U = const'})]});
  const text=pageReading.text;pageReading.text='E_k + U = const';
  try{
    await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
    await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  }finally{pageReading.text=text;}
  const mods=calls.filter(c=>c.text.includes('[TASK: moderate]'));
  assert.equal(mods.length,1);const listed=JSON.parse(mods[0].text.split('<<ITEMS>>')[1].split('<<END>>')[0]);
  assert.equal(listed.find(x=>x.id==='M')?.missing,true,'the left-out item is asked for');assert.equal(listed.find(x=>x.id==='S1')?.quote_missing,true);assert.ok(!mods[0].text.includes('"id":"X/1"'),'an alternative method is not asked for');
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"S1"[^}]*"got":0\.7/,'found again in the photos');
  assert.match(detail,/"id":"M"[^}]*"got":0\.6/,'graded the second time');
}));
test('split grading: a long paper is graded in groups of whole questions over the same prefix, and the groups\' items come back together',async()=>fixture(async({api,start,upload,drain,calls,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
  env.LAB_GRADE_SPLIT='on';env.LAB_R13_RECHECK='off';env.LAB_MISSING_RECHECK='off';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  const A=Array.from({length:20},(_,k)=>({id:'A.'+(k+1),points:0.1,type:'derivation',role:'result',sheet:'any',what:'a'+k})),B=Array.from({length:20},(_,k)=>({id:'B.'+(k+1),points:0.1,type:'derivation',role:'result',sheet:'any',what:'b'+k}));
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:4,items:[...A,...B]}),'fixture',Math.floor(Date.now()/1000));
  const g=id=>({id,found:true,page:1,label:id,rules:[],note:'',score:0.1,quote:''}),rev={summary:'s',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''};
  replies([{items:[...A.map(x=>g(x.id)),g('B.1')],feedback:[{note:'good',kind:'good'}],review:rev},{items:B.map(x=>g(x.id)),feedback:[],review:rev}],null);
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  const grades=calls.filter(c=>c.text.includes('[TASK: grade]'));
  assert.equal(grades.length,2,'two groups of 20');
  assert.match(grades[0].text,/Grade now only these scheme items[^\n]*A\.1, A\.2/);assert.match(grades[1].text,/Grade now only these scheme items[^\n]*B\.1, B\.2/);
  assert.ok(!/Grade now only these scheme items[^\n]*B\.1/.test(grades[0].text),'a group holds whole questions');
  const detail=JSON.parse(sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail);
  assert.equal(JSON.stringify(detail).match(/"got":0\.1/g).length>=40,true,'every item of both groups is graded');
}));
test('IP1 in code: an item whose only fault is a result carried from an earlier item that lost marks is not marked down again',async()=>fixture(async({api,start,upload,drain,calls,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
  env.LAB_ECF_RULE='on';env.LAB_IMPLIED_STEPS='on';env.LAB_R13_RECHECK='off';env.LAB_MISSING_RECHECK='off';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:1,items:[
    {id:'B8.2',points:0.2,type:'derivation',role:'result',sheet:'any',what:'amplitude'},{id:'B8.4',points:0.2,type:'derivation',role:'result',sheet:'any',what:'Coriolis force'},
    {id:'B8.5',points:0.3,type:'derivation',role:'result',sheet:'any',what:'x(t)'},{id:'B8.6',points:0.3,type:'derivation',role:'result',sheet:'any',what:'period'}]}),'fixture',Math.floor(Date.now()/1000));
  const g=(id,score,extra={})=>({id,found:true,page:1,label:id,rules:[],note:'',score,quote:'',...extra}),rev={summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''};
  replies({items:[g('B8.2',0),g('B8.4',0.1,{carried_from:'B8.2',rules:['IP2']}),g('B8.5',0.3),g('B8.6',0,{carried_from:'B8.5'})],feedback:[],review:rev},null);
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  assert.match(calls.find(c=>c.text.includes('[TASK: grade]')).text,/carried_from:/,'the grader is asked for it');
  assert.match(calls.find(c=>c.text.includes('[TASK: grade]')).text,/Implied steps \(for derivation steps this takes precedence over R9 and R13\)/,'the implied-step rule, with its precedence, goes to the grader when on');
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"B8\.4"[^}]*"got":0\.2[,}]/,'carried from B8.2, which lost its marks: not docked again');
  assert.match(detail,/"id":"B8\.6"[^}]*"got":0[,}]/,'B8.5 lost nothing: no carried error to excuse');
}));
test('training data: with LAB_TRAIN_CAPTURE on a graded paper is kept unverified; an admin checks or corrects it, and only verified rows are exported',async()=>fixture(async({api,start,upload,drain,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
  env.LAB_TRAIN_CAPTURE='on';env.LAB_R13_RECHECK='off';env.LAB_MISSING_RECHECK='off';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:1,items:[
    {id:'S',points:0.4,type:'derivation',role:'step',sheet:'any',what:'Newton for the orbit'},{id:'R',points:0.6,type:'derivation',role:'result',sheet:'any',what:'velocity'}]}),'fixture',Math.floor(Date.now()/1000));
  const g=(id,score)=>({id,found:true,page:1,label:id,rules:[],note:'',score,quote:''}),rev={summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''};
  replies({items:[g('S',0.4),g('R',0)],feedback:[],review:rev},null);
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  const row=sql.prepare("SELECT * FROM lab_train WHERE session_id=?").get(sid);
  assert.ok(row,'kept');assert.equal(row.verified,0);assert.equal(row.source,'model');
  assert.match(row.input,/S \| 0\.4 \| Newton for the orbit/);const detail=JSON.parse(sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail),final=Object.fromEntries((detail.tasks?.T1?.items||detail.T1?.items||[]).map(i=>[i.id,i.got]));
  assert.deepEqual(JSON.parse(row.target).items,[{id:'S',score:final.S??0},{id:'R',score:0}],'the target is the final marks, after the code\'s rules');
  assert.equal((await api('/admin/lab/train')).status,403,'admins only');
  sql.prepare("UPDATE users SET role='admin' WHERE id=1").run();
  assert.equal((await api('/admin/lab/train/export?kind=grade')).data.lines,0,'nothing unverified goes out');
  const fixed=await api(`/admin/lab/train/${row.id}`,{body:{items:[{id:'R',score:0.6}],note:'teacher: R is right'}});assert.equal(fixed.data.verified,true);
  const out=(await api('/admin/lab/train/export?kind=grade')).data;assert.equal(out.lines,1);
  const line=JSON.parse(out.jsonl);assert.deepEqual(line.messages.map(m=>m.role),['system','user','assistant']);
  assert.deepEqual(JSON.parse(line.messages[2].content).items,[{id:'S',score:final.S??0},{id:'R',score:0.6}],'the correction is what is learnt');
  const list=(await api('/admin/lab/train')).data;assert.equal(list.capture,true);assert.ok(list.counts.some(c=>c.verified===1&&c.n===1));
  assert.equal((await api('/admin/lab/train/export?kind=read&bucket=https://x')).status,400,'a gs:// bucket for the photos');
}));
test('pair grading: a second grader marks the paper as a chat would; agreed marks stand, an item they mark apart is rechecked with both opinions',async()=>fixture(async({api,start,upload,drain,calls,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
  env.LAB_PAIR_PROVIDER='deepseek';env.LAB_PAIR_MODEL='deepseek-flash';env.LAB_R13_RECHECK='off';env.LAB_MISSING_RECHECK='off';env.LAB_EXPR_CHECK='off';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:1,items:[
    {id:'P',points:0.4,type:'derivation',role:'result',sheet:'any',what:'period'},{id:'R',points:0.6,type:'derivation',role:'result',sheet:'any',what:'velocity'}]}),'fixture',Math.floor(Date.now()/1000));
  const g=(id,score)=>({id,found:true,page:1,label:id,rules:[],note:'',score,quote:''}),rev={summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''};
  replies([{items:[g('P',0.4),g('R',0)],feedback:[],review:rev},{analysis:'R is right.',items:[{id:'P',score:0.4},{id:'R',score:0.6,note:'correct'}]}],{items:[{id:'R',found:true,page:1,score:0.6,rules:[],note:'both read, R correct',quote:''}]});
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  const grades=calls.filter(c=>c.text.includes('[TASK: grade]'));assert.ok(grades.some(c=>/strict invigilator-grader/.test(c.text)),'the grader');
  assert.ok(grades.some(c=>/A teacher hands you one student's paper/.test(c.text)),'and the pair, marking as a chat would');
  const mod=calls.find(c=>c.text.includes('[TASK: moderate]'));assert.ok(mod,'the item they disagree on is rechecked');
  assert.equal(mod.provider,'deepseek','with no moderator of its own, the pair\'s grader decides');assert.equal(calls.filter(c=>c.text.includes('[TASK: moderate]')).length,1,'only what the two disagree on');
  assert.match(mod.text,/"id":"R"[^\n]*"second"/);assert.ok(!/"id":"P"[^\n]*"second"/.test(mod.text),'an agreed item is not');
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"R"[^}]*"got":0\.6[,}]/,'the recheck decides');assert.match(detail,/"id":"P"[^}]*"got":0\.4[,}]/);
}));
test('suspects: every item of a question with alternative methods, and the credited steps of a question whose result was marked down, are rechecked whatever their marks',async()=>fixture(async({api,start,upload,drain,calls,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
  env.LAB_SUSPECT_RECHECK='on';env.LAB_R13_RECHECK='off';env.LAB_MISSING_RECHECK='off';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:1.7,items:[
    {id:'A1.1',points:0.3,type:'derivation',role:'step',sheet:'any',alt:'A1/1',what:'sin phi = D/b'},{id:'A1.2',points:0.3,type:'derivation',role:'step',sheet:'any',alt:'A1/2',what:'torque about another point'},
    {id:'B8.1',points:0.2,type:'derivation',role:'step',sheet:'any',what:'y(t) = -d cos(omega t)'},{id:'B8.2',points:0.4,type:'derivation',role:'result',sheet:'any',what:'x(t)'},
    {id:'C.1',points:0.5,type:'derivation',role:'step',sheet:'any',what:'energy'}]}),'fixture',Math.floor(Date.now()/1000));
  const g=(id,score,quote)=>({id,found:score>0,page:1,label:id,rules:[],note:'',score,quote});
  const rev={summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''};
  replies({items:[g('A1.1',0.3,'Mg sin theta = f'),g('A1.2',0,''),g('B8.1',0.2,'y = (g/w^2 - d) cos wt'),g('B8.2',0,''),g('C.1',0.5,'E = const')],feedback:[],review:rev},
    {items:[g('A1.1',0,''),g('A1.2',0.3,'r_1 f = b M g sin phi'),g('B8.1',0,'')]});
  const text=pageReading.text;pageReading.text='Mg sin theta = f\nr_1 f = b M g sin phi\ny = (g/w^2 - d) cos wt\nE = const';
  try{await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();}
  finally{pageReading.text=text;}
  const mod=calls.find(c=>c.text.includes('[TASK: moderate]'));assert.ok(mod,'a recheck is made');
  const listed=JSON.parse(mod.text.split('<<ITEMS>>')[1].split('<<END>>')[0]).map(x=>x.id).sort();
  assert.deepEqual(listed,['A1.1','A1.2','B8.1'],'both methods of A1, the credited step under the marked-down B8 result; not C.1');
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"A1\.2"[^}]*"got":0\.3[,}]/);assert.match(detail,/"id":"A1\.1"[^}]*"got":0[,}]/);assert.match(detail,/"id":"B8\.1"[^}]*"got":0[,}]/);
}));
test('method choice: the method the grader shows the candidate used, by a line on the page, counts for its question; a line not on the page changes nothing',async()=>{
  for(const [line,expect] of [['r_1 f = b M g sin phi','method 2'],['sin phi = D/b','best of']])await fixture(async({api,start,upload,drain,calls,sql,env,replies})=>{
    env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
    env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
    env.LAB_METHOD_CHOICE='on';env.LAB_R13_RECHECK='off';env.LAB_MISSING_RECHECK='off';
    const a=(await start('deepseek')).data,sid=a.session.id;
    sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
    const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
    sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:0.8,items:[
      {id:'A1.1',points:0.3,type:'derivation',role:'step',sheet:'any',alt:'A1/1',what:'sin phi = D/b'},{id:'A1.2',points:0.3,type:'derivation',role:'step',sheet:'any',alt:'A1/1',what:'sin theta = D/r1'},
      {id:'A1.3',points:0.3,type:'derivation',role:'step',sheet:'any',alt:'A1/2',what:'torque about another point'},{id:'A1.4',points:0.2,type:'derivation',role:'step',sheet:'any',alt:'A1/2',what:'force equation'}]}),'fixture',Math.floor(Date.now()/1000));
    const g=(id,score,quote)=>({id,found:score>0,page:1,label:id,rules:[],note:'',score,quote});
    const rev={summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''};
    replies({methods:[{part:'A1',used:'A1/2',page:1,line}],items:[g('A1.1',0.3,'Mg sin theta = f'),g('A1.2',0.3,'Mg sin theta = f'),g('A1.3',0.3,'r_1 f = b M g sin phi'),g('A1.4',0,'')],feedback:[],review:rev},null);
    const text=pageReading.text;pageReading.text='Mg sin theta = f\nr_1 f = b M g sin phi\nb = r_1 sin theta / sin phi';
    try{await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();}
    finally{pageReading.text=text;}
    assert.ok(calls.find(c=>c.text.includes('[TASK: grade]')).text.includes('Alternative methods:'),'the grader is asked for the method first');
    const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
    if(expect==='method 2'){assert.match(detail,/"id":"A1\.1"[^}]*"got":0[,}]/,'method 1 dropped though it earned more');assert.match(detail,/"id":"A1\.3"[^}]*"got":0\.3[,}]/);}
    else{assert.match(detail,/"id":"A1\.1"[^}]*"got":0\.3[,}]/,'its line is not on the page: the best method counts, as before');assert.match(detail,/"id":"A1\.3"[^}]*"got":0[,}]/);}
  });
});
test('experiments: checks a scheme left at 0 points share the item, and a graph or table marked from the photo with no checks named keeps the grader\'s mark less a short count',async()=>fixture(async({api,start,upload,drain,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='deepseek';env.LAB_MODERATE_PROVIDER='none';env.LAB_MISSING_RECHECK='off';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','experiment') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:4.2,items:[
    {id:'Z',points:1.8,type:'graph',sheet:'answer',what:'graph of y against x',checks:[{check:'axes_labeled',points:0},{check:'fit_line',points:0},{check:'points_min',n:8,points:0}]},
    {id:'G',points:0.8,type:'graph',sheet:'answer',what:'graph of U against I',checks:[{check:'axes_labeled',points:0.8}]},
    {id:'T',points:1,type:'table',sheet:'answer',what:'table of I against r',checks:[{check:'columns_units',points:0.6},{check:'rows_min',n:20,points:0.4}]},
    {id:'S',points:0.6,type:'table',sheet:'answer',what:'table of U against I',checks:[{check:'columns_units',points:0.6}]}]}),'fixture',Math.floor(Date.now()/1000));
  replies({items:[{id:'Z',found:true,page:1,label:'Z',score:1.8,rules:[],checks_met:['axes_labeled','fit_line','points_min'],note:''},{id:'G',found:true,page:1,label:'G',score:0.8,rules:[],note:''},
    {id:'T',found:true,page:1,label:'T',score:1,rules:[],checks_met:[],note:''},{id:'S',found:true,page:1,label:'S',score:0.6,rules:[],checks_met:['columns_units'],note:''}],feedback:[],review:{summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}});
  const items=pageReading.items;
  pageReading.items=[{label:'T',kind:'table',text:'r, I',rows:11,columns:['r (mm)','I (mA)'],crossed_out:false},{label:'S',kind:'table',text:'U, I',rows:11,columns:['U (V)','I (mA)'],crossed_out:false},
    {label:'Z',kind:'graph',text:'y against x',crossed_out:false,graph:{axes_labeled:true,axes_units:true,scale_ok:true,n_points:8,fit_line:true,slope_read:false,error_bars:false,title:false}},
    {label:'G',kind:'graph',text:'U against I',crossed_out:false,graph:{axes_labeled:true,axes_units:true,scale_ok:true,n_points:10,fit_line:false,slope_read:false,error_bars:false,title:false}}];
  try{
    await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
    await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  }finally{pageReading.items=items;}
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"Z"[^}]*"got":1\.8[,}]/,'three checks at 0 points share the 1.8');
  assert.match(detail,/"id":"G"[^}]*"got":0\.8[,}]/,'marked from the photo, no checks named');
  assert.match(detail,/"id":"T"[^}]*"got":0\.6[,}]/,'its mark less the 20-row count the 11 rows miss');
  assert.match(detail,/"id":"S"[^}]*"got":0\.6[,}]/,'named checks are still checked as before');
}));
test('experiments: a table read as two pages under one label counts all its rows, and a graph check the grader saw in the photo counts though the reader left it unset',async()=>fixture(async({api,start,upload,drain,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='deepseek';env.LAB_MODERATE_PROVIDER='none';env.LAB_MISSING_RECHECK='off';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','experiment') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:2.7,items:[
    {id:'T',points:1,type:'table',sheet:'answer',what:'table of h(t)',checks:[{check:'rows_min',n:20,points:1}]},
    {id:'G',points:1,type:'graph',sheet:'answer',what:'graph of h(t)',checks:[{check:'axes_labeled',points:0.3},{check:'fit_line',points:0.3},{check:'points_min',n:8,points:0.4}]},
    {id:'H',points:0.7,type:'graph',sheet:'answer',what:'log-log graph',checks:[{check:'axes_labeled',points:0.3},{check:'fit_line',points:0.4}]}]}),'fixture',Math.floor(Date.now()/1000));
  replies({items:[{id:'T',found:true,page:1,label:'T',score:1,rules:[],checks_met:['rows_min'],note:''},{id:'G',found:true,page:1,label:'G',score:1,rules:[],checks_met:['axes_labeled','fit_line','points_min'],note:''},
    {id:'H',found:true,page:1,label:'H',score:0.7,rules:[],checks_met:['axes with units','straight line drawn'],note:''}],feedback:[],review:{summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}});
  const items=pageReading.items;
  pageReading.items=[{label:'T',kind:'table',text:'rows 1-8',rows:8,columns:['t (s)','h (cm)'],crossed_out:false},{label:'T',kind:'table',text:'rows 9-20',rows:12,columns:['t (s)','h (cm)'],crossed_out:false},
    {label:'G',kind:'graph',text:'h against t',crossed_out:false,graph:{axes_labeled:true,axes_units:true,scale_ok:true,n_points:4,fit_line:false,slope_read:false,error_bars:false,title:false}},
    {label:'H',kind:'graph',text:'ln F against ln H',crossed_out:false,graph:{axes_labeled:false,axes_units:false,scale_ok:true,n_points:17,fit_line:false,slope_read:false,error_bars:false,title:false}}];
  try{
    await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
    await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  }finally{pageReading.items=items;}
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"T"[^}]*"got":1[,}]/,'8 + 12 rows');
  assert.match(detail,/"id":"G"[^}]*"got":1[,}]/,'the fitted line and the eight points the grader saw in the photo, though the reader counted 4');
  assert.match(detail,/"id":"H"[^}]*"got":0\.7[,}]/,'checks named in the grader\'s own words match none of the scheme\'s: the mark it gave from the photo stands');
}));
test('experiments: of three tables on a page the one with the item\'s concentration is counted, and a value found from the candidate\'s own graph is the grader\'s to judge, not the example\'s window',async()=>fixture(async({api,start,upload,drain,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='deepseek';env.LAB_MODERATE_PROVIDER='none';env.LAB_MISSING_RECHECK='off';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','experiment') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:1.1,items:[
    {id:'A2.b',points:0.5,type:'table',sheet:'answer',what:'Table 1 of C0 = 28 g/150 mL: # data >= 20',checks:[{check:'rows_min',n:20,points:0.5}]},
    {id:'A2.c',points:0.5,type:'table',sheet:'answer',what:'Table 1 of C0 = 33 g/150 mL: # data >= 20',checks:[{check:'rows_min',n:20,points:0.5}]},
    {id:'A4.a',points:0.1,type:'value',sheet:'answer',unit:'cm',full_min:1.4,full_max:1.6,ref:'1.5',tol:'interval',role:'result',what:'h = (1.5 ± 0.1) cm. If h is correctly determined from graph A3: -0; if not: -0.1.'}]}),'fixture',Math.floor(Date.now()/1000));
  replies({items:[{id:'A2.b',found:true,page:1,score:0.5,rules:[],checks_met:[],note:''},{id:'A2.c',found:true,page:1,score:0.5,rules:[],checks_met:[],note:''},
    {id:'A4.a',found:true,page:1,score:0.1,value:2.81,unit:'cm',rules:[],note:'h read off the candidate\'s own graph'}],feedback:[],review:{summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}});
  const items=pageReading.items;
  pageReading.items=[{label:'Table 1',kind:'table',text:'Table 1 of C0 = 28 g / 150 mL\n1 | 0.3\n20 | 0.9',rows:20,columns:['i','d (cm)'],crossed_out:false},
    {label:'Table 1 (second)',kind:'table',text:'Table 1 of C0 = 33 g / 150 mL\n1 | 0.3\n8 | 0.5',rows:8,columns:['i','d (cm)'],crossed_out:false},
    {label:'A4',kind:'value',text:'h = 2.81 cm',value:2.81,crossed_out:false}];
  try{
    await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
    await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  }finally{pageReading.items=items;}
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"A2\.b"[^}]*"got":0\.5[,}]/,'the 28 g table: 20 rows');
  assert.match(detail,/"id":"A2\.c"[^}]*"got":0[,}]/,'the 33 g table holds 8 rows, not the 20 of the first table on the page');
  assert.match(detail,/"id":"A4\.a"[^}]*"got":0\.1[,}]/,'h from the candidate\'s own graph, outside the example\'s 1.4-1.6 cm');
}));

test('experiments: a graph cited by its table\'s page is taken from the next page, unless another item was marked from that page',async()=>fixture(async({api,start,upload,drain,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='deepseek';env.LAB_MODERATE_PROVIDER='none';env.LAB_MISSING_RECHECK='off';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','experiment') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  const graph=what=>({points:1,type:'graph',sheet:'answer',what,checks:[{check:'fit_line',points:1}]});
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:3,items:[
    {id:'A1',...graph('graph of I against h')},{id:'C1',...graph('graph of U against I')},{id:'B1',...graph('graph of P against I')}]}),'fixture',Math.floor(Date.now()/1000));
  replies({items:[{id:'A1',found:true,page:1,score:1,rules:[],checks_met:[],note:''},{id:'C1',found:true,page:2,score:1,rules:[],checks_met:['fit_line'],note:''},
    {id:'B1',found:true,page:3,score:1,rules:[],checks_met:[],note:''}],feedback:[],review:{summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}});
  for(let k=0;k<4;k++)await upload(a.token);
  await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  const g={axes_labeled:true,axes_units:true,scale_ok:true,n_points:10,fit_line:true,slope_read:true,error_bars:false,title:false};
  const reads={1:[{label:'table',kind:'table',text:'1 | 0.1\n10 | 0.9',rows:10,columns:['h','I'],crossed_out:false}],2:[{label:'graph',kind:'graph',text:'U against I',graph:g,crossed_out:false}],
    3:[{label:'table',kind:'table',text:'1 | 2\n10 | 3',rows:10,columns:['P','I'],crossed_out:false}],4:[{label:'graph',kind:'graph',text:'P against I',graph:g,crossed_out:false}]};
  for(const [no,items] of Object.entries(reads))sql.prepare("UPDATE lab_pages SET read=json_set(read,'$.items',json(?)) WHERE session_id=? AND no=?").run(JSON.stringify(items),sid,+no);
  await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"B1"[^}]*"got":1[,}]/,'the graph on the page after its table');
  assert.match(detail,/"id":"C1"[^}]*"got":1[,}]/);
  assert.match(detail,/"id":"A1"[^}]*"got":0[,}]/,'the next page holds C1\'s graph, and no graph of its own is anywhere near');
}));

test('experiments: a graph\'s slope outside the range the scheme prints loses what the scheme takes for it, from the grader\'s value or the slope read with the graph',async()=>fixture(async({api,start,upload,drain,sql,env,replies})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='deepseek';env.LAB_MODERATE_PROVIDER='none';env.LAB_MISSING_RECHECK='off';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','experiment') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  const graph=(lo,hi)=>({points:0.3,type:'graph',sheet:'answer',what:`Plot of Table 3. m (slope) = ${lo} cm^-2 till ${hi} cm^-2. Deductions: without x-axis label -0.01; m is out of range: -0.3 pts.`,checks:[{check:'fit_line',points:0.3},{check:'slope_read',points:0.3}]});
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:0.9,items:[
    {id:'B2.b',...graph(-10,-8.8)},{id:'B2.f',...graph(-11.3,-12.8)},{id:'B2.d',...graph(-11,-10.3)}]}),'fixture',Math.floor(Date.now()/1000));
  replies({items:[{id:'B2.b',found:true,page:1,label:'B2.b',score:0.3,value:12.7,rules:[],checks_met:['fit_line','slope_read'],note:'slope out of range'},
    {id:'B2.f',found:true,page:1,label:'B2.f',score:0.3,value:11.3,rules:[],checks_met:['fit_line','slope_read'],note:''},
    {id:'B2.d',found:true,page:1,label:'B2.d',score:0.3,rules:[],checks_met:['fit_line','slope_read'],note:''}],feedback:[],review:{summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}});
  const g={axes_labeled:true,axes_units:true,scale_ok:true,n_points:10,fit_line:true,slope_read:true,error_bars:false,title:false};
  const items=pageReading.items;
  pageReading.items=[{label:'B2.b',kind:'graph',text:'f against g, slope m = 12.7 cm^-2',graph:g,crossed_out:false},{label:'B2.f',kind:'graph',text:'f against g, slope m = 11.3',graph:g,crossed_out:false},
    {label:'B2.d',kind:'graph',text:'Graph of f vs g with slope m = 16.0 cm^-2',graph:g,crossed_out:false}];
  try{
    await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
    await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  }finally{pageReading.items=items;}
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"B2\.b"[^}]*"got":0[,}]/,'12.7 against 8.8-10 (the other sign counts, the size does not)');
  assert.match(detail,/"id":"B2\.f"[^}]*"got":0\.3[,}]/,'11.3 within 11.3-12.8, with the sign of a -ln axis');
  assert.match(detail,/"id":"B2\.d"[^}]*"got":0[,}]/,'no value from the grader: the slope read with the graph, 16.0, decides');
}));

test('a curated marking scheme on the site (schemes/<exam>/<task>.json) is used before the machine-built one',async()=>fixture(async({api,start,upload,drain,sql,env,replies,curated,calls})=>{
  env.LAB_PIPELINE='mixed';env.LAB_GRADE_PROVIDER='deepseek';env.LAB_MODERATE_PROVIDER='none';env.LAB_MISSING_RECHECK='off';env.LAB_R13_RECHECK='off';env.LAB_EXPR_CHECK='off';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:1,items:[{id:'M',points:1,type:'derivation',role:'result',sheet:'any',what:'machine line'}]}),'fixture',Math.floor(Date.now()/1000));
  curated('ipho2025/T1',{points:1.5,items:[{id:'A.1',points:0.5,type:'derivation',role:'result',sheet:'any',what:'curated: speed of the electron'},{id:'A.2',points:1,type:'derivation',role:'result',sheet:'any',what:'curated: Bohr radius'}]});
  replies({items:[{id:'A.1',found:true,page:1,score:0.5,rules:[],note:'',quote:''},{id:'A.2',found:true,page:1,score:0,rules:[],note:'',quote:''}],feedback:[],review:{summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''}});
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"A\.1"[^}]*"got":0\.5[,}]/);assert.match(detail,/"id":"A\.2"/);assert.ok(!/"id":"M"/.test(detail),'the machine scheme is not used');
  const grade=calls.find(c=>c.text.includes('[TASK: grade]'));assert.match(grade.text,/curated: Bohr radius/);
}));

test('double grading: an item the two gradings mark differently is decided once more from the photos, and the scheme review fixes a one-point window before grading',async()=>fixture(async({api,start,upload,drain,calls,sql,env,replies,review})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
  env.LAB_DOUBLE_GRADE='on';env.LAB_SCHEME_CHECK='on';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:2,items:[
    {id:'V',points:1,type:'value',sheet:'answer',what:'v',ref:'4.5',full_min:4.5,full_max:4.5,unit:'m/s'},
    {id:'S',points:1,type:'derivation',role:'step',sheet:'any',what:'energy conservation'}]}),'fixture',Math.floor(Date.now()/1000));
  review({fixes:[{id:'S',add_rule:'0.5 if a factor 2 is missing',reason:'printed in the solution'}],drop:[],final_full:[]});
  const g=(id,extra)=>({id,found:true,page:1,label:id,rules:[],note:'',...extra});
  const rev={summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''};
  replies([{items:[g('V',{score:1,value:4.52,unit_ok:true,quote:'v = 4.52 m/s'}),g('S',{score:1,quote:'E_k + U = const'})],feedback:[],review:rev},
           {items:[g('V',{score:1,value:4.52,unit_ok:true,quote:'v = 4.52 m/s'}),g('S',{score:0,note:'not written'})],feedback:[],review:rev}],
    {items:[g('S',{score:0.5,quote:'E_k + U = const',note:'factor 2 missing'})]});
  const text=pageReading.text;pageReading.text='v = 4.52 m/s\nE_k + U = const';
  try{
    await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
    await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  }finally{pageReading.text=text;}
  const grades=calls.filter(c=>c.text.includes('[TASK: grade]')&&!c.text.includes('[TASK: moderate]')),mods=calls.filter(c=>c.text.includes('[TASK: moderate]'));
  assert.equal(grades.length,2,'two independent gradings');
  assert.equal(calls.filter(c=>c.text.includes('[TASK: review marking scheme]')).length,1,'the scheme is reviewed once');
  assert.match(grades[0].text,/Scheme rule: 0\.5 if a factor 2 is missing/,'the reviewed scheme is the one graded with');
  const listed=JSON.parse(mods[0].text.split('<<ITEMS>>')[1].split('<<END>>')[0]);
  assert.deepEqual(listed.map(x=>x.id),['S'],'only the item the gradings disagree on');assert.equal(listed[0].second.score,0);
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"V"[^}]*"got":1[,}]/,'4.52 within the printed tolerance of 4.5');
  assert.match(detail,/"id":"S"[^}]*"got":0\.5/,'decided once more');
  const kept=sql.prepare("SELECT scheme FROM lab_schemes WHERE source LIKE 'review:v1:%'").get();assert.ok(kept,'kept for the next candidate');
  assert.deepEqual(JSON.parse(kept.scheme).review.applied.map(x=>x.fix),['rule'],'a one-point window is already dropped when a scheme is tidied; the review adds the missing rule');
}));
test('step audit: a credited step whose line differs loses its marks, a step judged absent but written gains them, and a step done «inherently» follows its result',async()=>fixture(async({api,start,upload,drain,calls,sql,env,replies,audit})=>{
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.1-pro-preview';env.LAB_READ_THINKING='low';
  env.LAB_GRADE_PROVIDER='gemini';env.LAB_GRADE_MODEL='gemini-3.8-flash';env.LAB_GRADE_THINKING='low';env.LAB_MODERATE_PROVIDER='none';
  env.LAB_STEP_AUDIT='on';env.LAB_R13_RECHECK='off';
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1'),key=['gemini',VISION_MODELS.gemini,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:4,items:[
    {id:'A.1',points:1,type:'derivation',role:'step',sheet:'any',what:'y(t) = -d cos(omega t)'},
    {id:'A.2',points:1,type:'derivation',role:'step',sheet:'any',what:'Newton: m a = -k x'},
    {id:'B.1',points:1,type:'derivation',role:'step',sheet:'any',what:'omega = 2 pi/T (even if it was done inherently)'},
    {id:'B.2',points:1,type:'derivation',role:'result',sheet:'any',what:'h = 22 km'}]}),'fixture',Math.floor(Date.now()/1000));
  const g=(id,extra)=>({id,found:true,page:1,label:id,rules:[],note:'',...extra});
  const rev={summary:'',strengths:[],habits:[],handwriting:{rating:'clear',notes:''},presentation:''};
  replies({items:[g('A.1',{score:1,quote:'y = (g/w^2 - d) cos wt'}),g('A.2',{score:0,found:false,quote:''}),g('B.1',{score:0,found:false,quote:''}),g('B.2',{score:1,quote:'h = 22 km'})],feedback:[],review:rev},null);
  audit({items:[{id:'A.1',verdict:'differs',page:1,quote:'y = (g/w^2 - d) cos wt',reason:'extra term g/w^2'},{id:'A.2',verdict:'states',page:1,quote:'m x\'\' = -k x',reason:'Newton written'}]});
  const text=pageReading.text;pageReading.text="y = (g/w^2 - d) cos wt\nm x'' = -k x\nh = 22 km";
  try{
    await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
    await api(`/lab/sessions/${sid}/submit`,{body:{provider:'deepseek'}});await drain();
  }finally{pageReading.text=text;}
  const au=calls.find(c=>c.text.includes('[TASK: audit steps]'));assert.ok(au,'the steps are audited');
  const listed=JSON.parse(au.text.split('<<STEPS>>')[1].split('<<END>>')[0]);
  assert.deepEqual(listed.map(x=>x.id),['A.1','A.2'],'the steps it judges: not results, not a step done inherently');
  const detail=sql.prepare('SELECT detail FROM lab_sessions WHERE id=?').get(sid).detail;
  assert.match(detail,/"id":"A\.1"[^}]*"got":0[,}]/,'the line in its place is another equation');
  assert.match(detail,/"id":"A\.2"[^}]*"got":1[,}]/,'written after all, and its quote is on the page');
  assert.match(detail,/"id":"B\.1"[^}]*"got":1[,}]/,'credited with its correct result');
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

test('LAB_READ_VERTEX: a page AI Studio is too busy for is read by the same model through Vertex AI, not the fallback model',async()=>fixture(async({api,start,upload,drain,calls,sql,env,limit})=>{
  const kp=await crypto.subtle.generateKey({name:'RSASSA-PKCS1-v1_5',modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'},true,['sign','verify']);
  const der=new Uint8Array(await crypto.subtle.exportKey('pkcs8',kp.privateKey)),pem='-----BEGIN PRIVATE KEY-----\n'+Buffer.from(der).toString('base64').match(/.{1,64}/g).join('\n')+'\n-----END PRIVATE KEY-----\n';
  env.GCP_SA_KEY=JSON.stringify({client_email:'reader@proj-9.iam.gserviceaccount.com',private_key:pem,project_id:'proj-9'});
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.8-flash';env.LAB_READ_THINKING='';env.LAB_READ_FALLBACK_MODEL='gemini-3.1-flash-lite';env.LAB_READ_VERTEX='on';
  limit('gemini-3.8-flash');
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  const reads=calls.filter(c=>c.text.includes('[TASK: read page]'));
  assert.match(reads[0].url,/generativelanguage\.googleapis\.com\/.*gemini-3\.8-flash:/,'AI Studio first');
  assert.equal(reads[1].url,'https://aiplatform.googleapis.com/v1/projects/proj-9/locations/global/publishers/google/models/gemini-3.8-flash:generateContent','then the same model on Vertex AI');
  assert.ok(!reads.some(c=>/gemini-3\.1-flash-lite/.test(c.url)),'the less exact fallback model is not needed');
  assert.equal(sql.prepare('SELECT ocr_status FROM lab_pages WHERE session_id=?').get(sid).ocr_status,'done');
}));

test('a 3.8 Flash read that runs to its token cap (looping) is asked once more by the same model, not Vertex, before any fallback',async()=>fixture(async({api,start,upload,drain,calls,sql,env,truncate})=>{
  const kp=await crypto.subtle.generateKey({name:'RSASSA-PKCS1-v1_5',modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'},true,['sign','verify']);
  const der=new Uint8Array(await crypto.subtle.exportKey('pkcs8',kp.privateKey)),pem='-----BEGIN PRIVATE KEY-----\n'+Buffer.from(der).toString('base64').match(/.{1,64}/g).join('\n')+'\n-----END PRIVATE KEY-----\n';
  env.GCP_SA_KEY=JSON.stringify({client_email:'reader@proj-9.iam.gserviceaccount.com',private_key:pem,project_id:'proj-9'});
  env.LAB_PIPELINE='mixed';env.LAB_READ_MODEL='gemini-3.8-flash';env.LAB_READ_THINKING='';env.LAB_READ_FALLBACK_MODEL='gemini-3.1-flash-lite';env.LAB_READ_VERTEX='on';
  truncate(1);
  const a=(await start('deepseek')).data,sid=a.session.id;
  sql.prepare("UPDATE lab_sessions SET sources=json_set(sources,'$.T1.kind','theory') WHERE id=?").run(sid);
  await upload(a.token);await api(`/lab/sessions/${sid}/pay`,{body:{provider:'deepseek'}});await drain();
  const reads=calls.filter(c=>c.text.includes('[TASK: read page]'));
  assert.equal(reads.length,2);assert.match(reads[0].url,/generativelanguage.*gemini-3\.8-flash:/);
  assert.equal(reads[0].body.generationConfig.maxOutputTokens,10240,'a loop ends at the cap (10k by default), not 32k');
  assert.match(reads[1].url,/generativelanguage.*gemini-3\.8-flash:/,'the same model once more: its loops come and go');
  assert.ok(!reads.some(c=>/aiplatform|gemini-3\.1-flash-lite/.test(c.url)),'neither Vertex nor the fallback was needed');
  assert.equal(sql.prepare('SELECT ocr_status FROM lab_pages WHERE session_id=?').get(sid).ocr_status,'done');
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
