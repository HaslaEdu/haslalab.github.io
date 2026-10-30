// Real Worker/SQLite routes. The OCR provider is a local stand-in; no paid calls or real credentials.
import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import worker from './src/index.js';
import { prepareMonthlyPhotoSubmission } from './src/monthly-photos.js';
import { normalizeMonthlyParts } from './src/monthly-answers.js';

const START = Date.parse('2026-11-01T12:00:00+09:00')/1000;
const png = size => { const bytes=new Uint8Array(size).fill(73); bytes.set([137,80,78,71,13,10,26,10]); return bytes; };
const FORM = (part='a',size=600000,requestId=crypto.randomUUID()) => {
  const form=new FormData();form.set('image',new File([png(32)],'scan.png',{type:'image/png'}));
  form.set('original_image',new File([png(size)],'original.png',{type:'image/png'}));form.set('part_id',part);form.set('request_id',requestId);return form;
};
async function environment(run) {
  const sql=new DatabaseSync(':memory:');
  for(const file of readdirSync(new URL('./migrations/',import.meta.url)).filter(f=>/^\d{4}_.*\.sql$/.test(f)).sort())
    sql.exec(readFileSync(new URL('./migrations/'+file,import.meta.url),'utf8'));
  let failPhoto=false;
  const DB={prepare(query){const st=sql.prepare(query),make=args=>({query,bind:(...v)=>make(v.map(x=>x instanceof ArrayBuffer?new Uint8Array(x):x)),
    async first(){return st.get(...args)||null;},async all(){return{results:st.all(...args)};},async run(){return this.executeSync();},
    executeSync(){if(st.columns().length)return{results:st.all(...args)};const r=st.run(...args);return{results:[],meta:{changes:r.changes,last_row_id:Number(r.lastInsertRowid)}};}});return make([]);},
    async batch(statements){sql.exec('BEGIN');try{const r=statements.map(s=>{const result=s.executeSync();if(failPhoto&&s.query.includes('INSERT INTO monthly_answer_photo_chunks')){failPhoto=false;throw Error('local photo transaction interruption');}return result;});sql.exec('COMMIT');return r;}catch(e){sql.exec('ROLLBACK');throw e;}}};
  const saved={now:Date.now,fetch:globalThis.fetch,caches:globalThis.caches};let clock=START,ocrCalls=0,beforeOcr=async()=>{},transcript='Final answer\nOriginal working';
  Date.now=()=>clock*1000;globalThis.caches={default:{async match(){throw Error('Private scan must not read shared cache');},async put(){throw Error('Private scan must not write shared cache');}}};
  globalThis.fetch=async(url,init)=>{assert.match(String(url),/document-digitization/,'only the mocked OCR endpoint is permitted');ocrCalls++;
    assert.deepEqual(new Uint8Array(await init.body.get('document').arrayBuffer()),png(32));await beforeOcr();
    return Response.json({content:{markdown:transcript},confidence:0.97,usage:{pages:1}});};
  const auth={};for(let user=1;user<=3;user++){
    auth[user]=('monthly-scan-owner-'+user).padEnd(48,'x');const hash=Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(auth[user]))).toString('base64url');
    sql.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at) VALUES(?,?,?,'unused',?,?)").run(user,'qr'+user,'QR '+user,user===3?'admin':'user',clock);
    sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(hash,user,clock,clock+7*86400);
  }
  const env={DB,ALLOWED_ORIGINS:'http://localhost:8765',UPSTAGE_API_KEY:'local-stand-in',LAB_KEEP_HOURS:'off'};
  const api=async(path,{user=1,body,method,headers={},scan}={})=>{
    const form=body instanceof FormData,r=await worker.fetch(new Request('https://monthly.local/api'+path,{method:method||(body===undefined?'GET':'POST'),
      headers:{Origin:'http://localhost:8765',...(user?{Authorization:'Bearer '+auth[user]}:{}),...(scan?{'X-Monthly-Scan':scan}:{}),
        ...(!form&&body!==undefined?{'Content-Type':'application/json'}:{}),...headers},...(body===undefined?{}:{body:form?body:JSON.stringify(body)})}),env);
    return{status:r.status,response:r,data:r.headers.get('Content-Type')?.includes('application/json')?await r.json():new Uint8Array(await r.arrayBuffer())};
  };
  const open=async(problem=4,user=1,part='a')=>{
    const r=await api(`/monthly/problems/${problem}/scan`,{user,body:{part_id:part}});assert.equal(r.status,200,JSON.stringify(r.data));return r.data;
  };
  const phone=async(token,options={})=>api('/monthly/scan',{user:0,scan:token,...options});
  const upload=async(token,part='a',options={})=>api('/monthly/scan/photos?mode=math',{user:0,scan:token,body:FORM(part),...options});
  const poll=async(session,after=0,user=1)=>api(`/monthly/problems/${session.problem_id}/scan/${session.id}?after=${after}`,{user});
  try{return await run({sql,DB,api,open,phone,upload,poll,advance:n=>{clock+=n;},clock:()=>clock,
    beforeOcr:fn=>{beforeOcr=fn;},failPhoto:()=>{failPhoto=true;},transcript:t=>{transcript=t;},ocrCalls:()=>ocrCalls});}
  finally{Date.now=saved.now;globalThis.fetch=saved.fetch;globalThis.caches=saved.caches;sql.close();}
}
const submission=(sql,user=1,problem=4)=>sql.prepare("INSERT INTO submissions(problem_id,user_id,answer,via_ocr,status,in_week,created_at) VALUES(?,?,'existing attempt',0,'pending',1,?)").run(problem,user,START);

test('capabilities exist only after an authenticated explicit request; tokens are hashed and never returned by polls',async()=>{
  await environment(async({sql,api,open,phone,poll,ocrCalls})=>{
    await api('/problems/4');
    assert.equal(sql.prepare("SELECT name FROM sqlite_master WHERE name='monthly_scan_sessions'").get(),undefined);
    assert.equal((await api('/monthly/problems/4/scan',{user:0,body:{part_id:'a'}})).status,401);
    const first=await open(),second=await open(4,2);
    assert.match(first.token,/^[A-Za-z0-9_-]{43}$/);assert.notEqual(first.token,second.token);
    assert.equal(first.session.expires_at-first.session.created_at,1200);
    const stored=sql.prepare('SELECT * FROM monthly_scan_sessions WHERE id=?').get(first.session.id);
    assert.notEqual(stored.token_hash,first.token);assert.ok(!JSON.stringify(stored).includes(first.token));
    const metadata=await phone(first.token);assert.equal(metadata.status,200);assert.equal(metadata.data.problem.id,4);
    assert.deepEqual(metadata.data.parts.map(p=>p.id),['a','b','c','d','e','f','g','h','i','j']);
    for(const forbidden of ['user_id','username','nickname','token_hash','rubric','model_ko','model_en','answer'])assert.equal(Object.hasOwn(metadata.data,forbidden),false);
    const desktop=await poll(first.session);assert.equal(desktop.status,200);assert.deepEqual(desktop.data.photos,[]);
    assert.equal(desktop.data.cursor,0);assert.equal(desktop.data.has_more,false);assert.ok(!JSON.stringify(desktop.data).includes(first.token));
    for(const result of [metadata,desktop])assert.equal(result.response.headers.get('Cache-Control'),'no-store');
    assert.equal((await poll(first.session,0,2)).status,404);assert.equal((await poll(first.session,0,3)).status,404,'capability management is owner-only');
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0);assert.equal(sql.prepare('SELECT exam_tokens FROM users WHERE id=1').get().exam_tokens,5);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM lab_ledger').get().n,0);assert.equal(ocrCalls(),0);
  });
});

test('login-free uploads bind the owner/problem and permit only that problem canonical parts',async()=>{
  await environment(async({sql,DB,api,open,phone,upload,poll,ocrCalls})=>{
    const cap=await open();assert.equal((await upload(cap.token,'A.1')).status,400);assert.equal(ocrCalls(),0);
    const result=await upload(cap.token,'b',{user:2});assert.equal(result.status,200,JSON.stringify(result.data));
    const row=sql.prepare('SELECT * FROM monthly_answer_photos WHERE id=?').get(result.data.photo_id);
    assert.equal(row.user_id,1);assert.equal(row.problem_id,4);assert.equal(row.part_id,'b');assert.equal(row.bytes,600000);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photo_chunks').get().n,2);
    const update=await poll(cap.session);assert.equal(update.data.photos.length,1);assert.equal(update.data.photos[0].text,'Final answer\nOriginal working');
    assert.equal(update.data.photos[0].photo_id,row.id);assert.equal(update.data.photos[0].part_id,'b');
    assert.deepEqual((await poll(cap.session,update.data.cursor)).data.photos,[]);
    assert.equal((await api('/monthly/photos/'+row.id,{user:0,scan:cap.token})).status,401);
    assert.equal((await api('/monthly/photos/'+row.id,{user:2})).status,404);
    assert.deepEqual((await api('/monthly/photos/'+row.id)).data,png(600000));
    assert.equal((await api('/monthly/problems/5/photos',{user:0,scan:cap.token,body:FORM('a')})).status,401);
    assert.equal((await api('/problems/4/submit',{user:0,scan:cap.token,body:{}})).status,401);
    const problem=sql.prepare('SELECT * FROM problems WHERE id=4').get(),normalized=normalizeMonthlyParts(problem,
      {request_id:'qr-saved-answer'.padEnd(32,'x'),parts:[{id:'b',answer:'Final answer',working:'Original working'}]});
    await prepareMonthlyPhotoSubmission(DB,1,problem,normalized,[row.id]);assert.deepEqual(normalized.photographedPartIds,['b']);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0,'upload does not consume one of three attempts');
    assert.equal((await phone(cap.token)).data.session.open,true);
  });
});

test('rotation/revocation affect only the owner/problem; expiry blocks uploads while owner may recover existing photos',async()=>{
  await environment(async({sql,api,open,phone,upload,poll,advance,ocrCalls})=>{
    const a=await open(),otherOwner=await open(4,2),otherProblem=await open(5,1);await upload(a.token);
    const replacement=await open(4,1,'b');assert.equal((await phone(a.token)).data.error,'scan_revoked');
    assert.equal((await phone(otherOwner.token)).status,200);assert.equal((await phone(otherProblem.token)).status,200);
    assert.equal((await poll(a.session)).data.session.closed_reason,'revoked');assert.equal((await poll(a.session)).data.photos.length,1);
    assert.equal((await api(`/monthly/problems/4/scan/${replacement.session.id}`,{user:2,method:'DELETE'})).status,404);
    assert.equal((await api(`/monthly/problems/4/scan/${replacement.session.id}`,{method:'DELETE'})).status,200);
    assert.equal((await upload(replacement.token)).data.error,'scan_revoked');assert.equal(ocrCalls(),1);
    const expiring=await open();await upload(expiring.token);advance(1200);
    assert.equal((await phone(expiring.token)).data.error,'scan_expired');assert.equal((await upload(expiring.token)).status,410);
    const saved=await poll(expiring.session);assert.equal(saved.data.session.open,false);assert.equal(saved.data.session.closed_reason,'expired');assert.equal(saved.data.photos.length,1);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,2);
  });
});

test('accepted final submissions close their scan; exhausted attempts and invisible/unopened problems cannot create capabilities',async()=>{
  await environment(async({sql,api,open,phone,upload,ocrCalls})=>{
    const a=await open();submission(sql);assert.equal((await phone(a.token)).data.error,'scan_submitted');assert.equal((await upload(a.token)).status,410);
    const b=await open();submission(sql);submission(sql);
    assert.equal((await phone(b.token)).data.error,'attempts_exhausted');assert.equal((await api('/monthly/problems/4/scan',{body:{part_id:'a'}})).status,409);
    assert.equal((await api('/monthly/problems/1/scan',{body:{part_id:'a'}})).status,404);
    const next=await open(5);sql.prepare('UPDATE problems SET opens_at=? WHERE id=5').run(START+3600);
    assert.equal((await phone(next.token)).data.error,'scan_closed');assert.equal((await api('/monthly/problems/5/scan',{body:{part_id:'a'}})).status,404);
    assert.equal(ocrCalls(),0);assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,3);
  });
});

test('in-flight OCR cannot create photos after revocation, expiry, final submission or owner deletion',async()=>{
  for(const closure of ['revoked','expired','submitted','deleted'])await environment(async({sql,api,open,upload,beforeOcr,advance})=>{
    const cap=await open();beforeOcr(async()=>{
      if(closure==='revoked')await api(`/monthly/problems/4/scan/${cap.session.id}`,{method:'DELETE'});
      if(closure==='expired')advance(1200);
      if(closure==='submitted')submission(sql);
      if(closure==='deleted')assert.equal((await api('/me',{method:'DELETE'})).status,200);
    });
    const result=await upload(cap.token);assert.equal(result.status,410,closure+JSON.stringify(result.data));
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,0);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photo_chunks').get().n,0);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_scan_photos').get().n,0);
    if(closure==='deleted'){
      assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_scan_sessions').get().n,0);
      assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_scan_uploads').get().n,0);
    }
  });
});

test('desktop cursors are ordered, bounded and session-specific with no lost same-second uploads',async()=>{
  await environment(async({sql,api,open,upload,poll})=>{
    const cap=await open();for(let i=0;i<12;i++)assert.equal((await upload(cap.token,'a',{body:FORM('a',32)})).status,200);
    const a=await poll(cap.session);assert.equal(a.data.photos.length,10);assert.equal(a.data.has_more,true);
    const b=await poll(cap.session,a.data.cursor);assert.equal(b.data.photos.length,2);assert.equal(b.data.has_more,false);
    assert.equal(new Set([...a.data.photos,...b.data.photos].map(p=>p.photo_id)).size,12);
    assert.deepEqual((await poll(cap.session,b.data.cursor)).data.photos,[]);
    assert.equal((await api(`/monthly/problems/4/scan/${cap.session.id}?after=-1`)).status,400);
    const fresh=await open();assert.deepEqual((await poll(fresh.session)).data.photos,[]);
    sql.prepare('UPDATE monthly_scan_sessions SET expires_at=? WHERE id=?').run(START-86401,cap.session.id);
    await open();assert.equal(sql.prepare('SELECT id FROM monthly_scan_sessions WHERE id=?').get(cap.session.id),undefined);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,12,'expired link cleanup retains the separate originals archive');
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_scan_uploads').get().n,0);
  });
});

test('concurrent uploads cannot exceed archive quota or leave unlinked chunks',async()=>{
  await environment(async({sql,open,upload,beforeOcr})=>{
    const cap=await open();for(let i=0;i<39;i++)sql.prepare("INSERT INTO monthly_answer_photos(id,user_id,problem_id,part_id,mime,bytes,ocr_text,created_at) VALUES(?,1,4,'a','image/png',32,'fixture',?)").run(crypto.randomUUID(),START);
    let reached=0,release;const both=new Promise(resolve=>{release=resolve;});
    beforeOcr(async()=>{if(++reached===2)release();await both;});
    const results=await Promise.all([upload(cap.token),upload(cap.token)]);
    assert.deepEqual(results.map(r=>r.status).sort(),[200,413]);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,40);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_scan_photos').get().n,1);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photo_chunks').get().n,2);
  });
});

test('an interrupted photo transaction rolls back original, OCR and desktop notification together without logging the capability',async()=>{
  await environment(async({sql,open,upload,poll,failPhoto})=>{
    const cap=await open(),requestId=crypto.randomUUID();failPhoto();const originalError=console.error,logs=[];let result;
    try{console.error=(...args)=>logs.push(args.join(' '));result=await upload(cap.token,'a',{body:FORM('a',600000,requestId)});}finally{console.error=originalError;}
    assert.equal(result.status,500);assert.ok(!logs.join('\n').includes(cap.token));
    for(const table of ['monthly_answer_photos','monthly_answer_photo_chunks','monthly_scan_photos'])assert.equal(sql.prepare(`SELECT COUNT(*) n FROM ${table}`).get().n,0);
    assert.deepEqual((await poll(cap.session)).data.photos,[]);
    assert.equal((await upload(cap.token,'a',{body:FORM('a',600000,requestId)})).status,200);assert.equal((await poll(cap.session)).data.photos.length,1);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0);
  });
});

test('response-loss retries return the same original/OCR; changed bytes, part or mode cannot reuse a request key',async()=>{
  await environment(async({sql,api,open,upload,poll,ocrCalls})=>{
    const cap=await open(),id=crypto.randomUUID(),send=()=>upload(cap.token,'a',{body:FORM('a',600000,id)});
    const first=await send(),retry=await send();assert.equal(first.status,200);assert.equal(retry.status,200);
    assert.equal(retry.data.photo_id,first.data.photo_id);assert.equal(retry.data.text,first.data.text);assert.equal(retry.data.replayed,true);
    assert.equal(ocrCalls(),1);assert.equal((await poll(cap.session)).data.photos.length,1);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,1);
    for(const form of [FORM('b',600000,id),FORM('a',600001,id)]){
      const conflict=await upload(cap.token,'a',{body:form});assert.equal(conflict.status,409);assert.equal(conflict.data.error,'upload_conflict');
    }
    const changed=FORM('a',600000,id);changed.set('image',new File([png(33)],'changed.png',{type:'image/png'}));
    assert.equal((await upload(cap.token,'a',{body:changed})).data.error,'upload_conflict');assert.equal(ocrCalls(),1);
    const differentOriginal=FORM('a',600000,id),original=png(600000);original[original.length-1]^=1;
    differentOriginal.set('original_image',new File([original],'original.png',{type:'image/png'}));
    assert.equal((await upload(cap.token,'a',{body:differentOriginal})).data.error,'upload_conflict');
    assert.equal((await api('/monthly/scan/photos?mode=text',{user:0,scan:cap.token,body:FORM('a',600000,id)})).data.error,'upload_conflict');
    const missing=FORM();missing.delete('request_id');assert.equal((await upload(cap.token,'a',{body:missing})).data.error,'bad_upload_request');
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0);
  });
});

test('a scan has a bounded upload-request journal even when all earlier requests failed',async()=>{
  await environment(async({sql,open,upload,ocrCalls})=>{
    const cap=await open();for(let i=0;i<80;i++)sql.prepare("INSERT INTO monthly_scan_uploads(scan_id,request_id,payload_hash,claim,created_at,updated_at) VALUES(?,?,?,'',?,0)").run(cap.session.id,'failed-request-'+String(i).padStart(3,'0'),'fixture',START);
    const r=await upload(cap.token);assert.equal(r.status,429);assert.equal(r.data.error,'monthly_scan_upload_limit');
    assert.equal(ocrCalls(),0);assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,0);
  });
});

test('parallel requests with one upload key run OCR once and expose explicit processing before replay',async()=>{
  await environment(async({open,upload,poll,beforeOcr,ocrCalls})=>{
    const cap=await open(),id=crypto.randomUUID();let reached,release;
    const entered=new Promise(resolve=>{reached=resolve;}),finish=new Promise(resolve=>{release=resolve;});
    beforeOcr(async()=>{reached();await finish;});
    const first=upload(cap.token,'a',{body:FORM('a',600000,id)});await entered;
    const pending=await upload(cap.token,'a',{body:FORM('a',600000,id)});
    assert.equal(pending.status,409);assert.equal(pending.data.error,'upload_processing');assert.equal(pending.data.retry_after,2);assert.equal(ocrCalls(),1);
    release();const complete=await first;assert.equal(complete.status,200);
    const retry=await upload(cap.token,'a',{body:FORM('a',600000,id)});assert.equal(retry.data.photo_id,complete.data.photo_id);
    assert.equal(ocrCalls(),1);assert.equal((await poll(cap.session)).data.photos.length,1);
  });
});

test('a reclaimed stalled upload cannot let its late OCR overwrite the one completed photo',async()=>{
  await environment(async({sql,open,upload,poll,beforeOcr,advance,ocrCalls})=>{
    const cap=await open(),id=crypto.randomUUID();let reached,release;
    const entered=new Promise(resolve=>{reached=resolve;}),finish=new Promise(resolve=>{release=resolve;});
    beforeOcr(async()=>{if(ocrCalls()===1){reached();await finish;}});
    const first=upload(cap.token,'a',{body:FORM('a',600000,id)});await entered;advance(301);
    const replacement=await upload(cap.token,'a',{body:FORM('a',600000,id)});assert.equal(replacement.status,200);
    release();const late=await first;assert.equal(late.status,409);assert.equal(late.data.error,'upload_processing');
    const retry=await upload(cap.token,'a',{body:FORM('a',600000,id)});assert.equal(retry.data.photo_id,replacement.data.photo_id);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,1);
    assert.equal((await poll(cap.session)).data.photos.length,1);assert.equal(ocrCalls(),2);
  });
});

test('image/OCR/storage/admission limits reject before extra calls and preserve full transcripts without truncation',async()=>{
  await environment(async({sql,api,open,upload,transcript,ocrCalls})=>{
    const cap=await open();assert.equal((await upload(cap.token,'unknown')).status,400);
    assert.equal((await upload(cap.token,'a',{body:FORM('a',4*1024*1024+1)})).status,413);assert.equal(ocrCalls(),0);
    transcript('x'.repeat(256*1024+1));assert.equal((await upload(cap.token)).data.error,'ocr_too_big');
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,0);
    transcript('Final answer\nOriginal working');
    sql.prepare("INSERT INTO ratelimits(k,start,n) VALUES('ocr:1',?,30) ON CONFLICT(k) DO UPDATE SET n=30,start=excluded.start").run(START);
    const before=ocrCalls();assert.equal((await upload(cap.token)).status,429);assert.equal(ocrCalls(),before);
    sql.prepare("DELETE FROM ratelimits WHERE k='ocr:1'").run();
    for(let i=0;i<40;i++)sql.prepare("INSERT INTO monthly_answer_photos(id,user_id,problem_id,part_id,mime,bytes,ocr_text,created_at) VALUES(?,1,4,'a','image/png',32,'fixture',?)").run(crypto.randomUUID(),START);
    assert.equal((await upload(cap.token)).status,413);assert.equal(ocrCalls(),before);
    sql.prepare("INSERT INTO ratelimits(k,start,n) VALUES('monthly-scan-create:1',?,30) ON CONFLICT(k) DO UPDATE SET n=30,start=excluded.start").run(START);
    assert.equal((await api('/monthly/problems/5/scan',{body:{part_id:'a'}})).status,429);
  });
});

test('private header is CORS-admitted and never accepted through URL params or leaked into responses',async()=>{
  await environment(async({api,open,phone,ocrCalls})=>{
    const cap=await open();
    for(const token of [undefined,'invalid','a'.repeat(43)])assert.equal((await phone(token)).status,403);
    assert.equal((await api('/monthly/scan?token='+cap.token,{user:0})).status,403);
    const preflight=await api('/monthly/scan/photos',{user:0,method:'OPTIONS',headers:{'Access-Control-Request-Headers':'X-Monthly-Scan'}});
    assert.equal(preflight.status,204);assert.match(preflight.response.headers.get('Access-Control-Allow-Headers'),/X-Monthly-Scan/);
    const metadata=await phone(cap.token);assert.ok(!JSON.stringify(metadata.data).includes(cap.token));
    assert.ok(!JSON.stringify([...metadata.response.headers]).includes(cap.token));assert.equal(ocrCalls(),0);
  });
});
