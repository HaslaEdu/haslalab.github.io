import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import worker from './src/index.js';
import { normalizeMonthlyParts } from './src/monthly-answers.js';
import { prepareMonthlyPhotoSubmission, deleteMonthlyPhotos } from './src/monthly-photos.js';

const NOW = Date.parse('2026-11-01T12:00:00+09:00')/1000;
const ANSWER = '$a^2+b^2=c^2$', WORKING = 'Apply the governing equation.';
const png = size => { const bytes = new Uint8Array(size).fill(73); bytes.set([137,80,78,71,13,10,26,10]); return bytes; };
const payload = (key, photoIds) => ({ provider:'gemini',request_id:key.padEnd(32,'x'), parts:[{id:'a',answer:ANSWER,working:WORKING}], photo_ids:photoIds });

async function environment(run) {
  const sql = new DatabaseSync(':memory:');
  for (const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(name=>/^00(?:0[1-9]|1[01])_.*\.sql$/.test(name)).sort()) {
    sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
  }
  sql.exec(readFileSync(new URL('./migrations/0012_omr.sql',import.meta.url),'utf8'));
  const DB = {
    prepare(query) {
      const st = sql.prepare(query), make = args => ({
        bind:(...values)=>make(values.map(value=>value instanceof ArrayBuffer?new Uint8Array(value):value)),
        async first(){return st.get(...args)||null;}, async all(){return{results:st.all(...args)};}, async run(){return this.executeSync();},
        executeSync(){if(st.columns().length)return{results:st.all(...args)};const r=st.run(...args);return{results:[],meta:{changes:r.changes,last_row_id:Number(r.lastInsertRowid)}};},
      }); return make([]);
    },
    async batch(statements){sql.exec('BEGIN');try{const r=statements.map(st=>st.executeSync());sql.exec('COMMIT');return r;}catch(e){sql.exec('ROLLBACK');throw e;}},
  };
  const saved={fetch:globalThis.fetch,caches:globalThis.caches,now:Date.now};
  Date.now=()=>NOW*1000; globalThis.caches={default:{async match(){},async put(){}}};
  const tokens = [];
  for (let id=1;id<=3;id++) {
    const token=('monthly-photo-owner-'+id).padEnd(48,'x'); tokens.push(token);
    const hash=Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token))).toString('base64url');
    sql.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at) VALUES(?,?,?,'unused',?,?)").run(id,'photo'+id,'Photo '+id,id===3?'admin':'user',NOW-100);
    sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(hash,id,NOW-100,NOW+86400);
  }
  let transcript=ANSWER+'\n'+WORKING, visuals=[], gradeEvidence=ANSWER, ocrCalls=0, screenCalls=0, beforeOcr=async()=>{};
  const gradingRequests=[];
  globalThis.fetch=async(url,init)=>{
    const request=JSON.parse(init.body),gemini=String(url).endsWith(':generateContent'),schema=gemini?request.generationConfig.responseSchema:JSON.parse(request.messages[0].content.split('JSON schema:\n')[1]);
    assert.ok(gemini||String(url).endsWith('/chat/completions'),'no legacy OCR request is allowed');
    if(schema.properties.visuals){
      ocrCalls++;
      await beforeOcr();
      assert.ok(JSON.stringify(request).includes(Buffer.from(png(32)).toString('base64')),'OCR receives selected scan, not the stored original');
      const raw={text:transcript,confidence:0.97,legible:true,uncertainties:[],visuals};
      return Response.json(gemini?{candidates:[{content:{parts:[{text:JSON.stringify(raw)}]}}]}:{choices:[{message:{content:JSON.stringify(raw)},finish_reason:'stop'}]});
    }
    const isScreen=!!schema.properties.assessment;
    let raw;
    if(isScreen){screenCalls++;raw={assessment:'uncertain',confidence:0.5,signals:[]};}
    else{gradingRequests.push(request);const rubric=JSON.parse(sql.prepare('SELECT rubric FROM problems WHERE id=4').get().rubric);raw={scores:rubric.map(c=>({id:c.id,got:c.id==='a'?c.max:0,note:'Private note',decision:c.id==='a'?'met':'not_met',evidence:c.id==='a'?[gradeEvidence]:[]})),feedback:[],confidence:0.9};}
    return Response.json(gemini?{candidates:[{content:{parts:[{text:JSON.stringify(raw)}]}}]}:{choices:[{message:{content:JSON.stringify(raw)},finish_reason:'stop'}]});
  };
  const env={DB,ALLOWED_ORIGINS:'http://localhost:8765',GEMINI_API_KEY:'local-grader',DEEPSEEK_API_KEY:'local-deepseek',LAB_KEEP_HOURS:'off'};
  const api=async(path,{user=1,body,method,headers={}}={})=>{
    if(body&&!(body instanceof FormData)&&path==='/problems/4/submit')body={provider:'gemini',...body};
    const form=body instanceof FormData;
    const response=await worker.fetch(new Request('http://monthly.local/api'+path,{method:method||(body===undefined?'GET':'POST'),
      headers:{Origin:'http://localhost:8765','Cache-Control':'no-cache',...(user?{Authorization:'Bearer '+tokens[user-1]}:{}),...(!form&&body!==undefined?{'Content-Type':'application/json'}:{}),...headers},
      ...(body===undefined?{}:{body:form?body:JSON.stringify(body)})}),env);
    return {status:response.status,response,data:response.headers.get('Content-Type')?.includes('application/json')?await response.json():new Uint8Array(await response.arrayBuffer())};
  };
  const upload=async({part='a',original=png(600000),image=png(32),user=1,provider='gemini'}={})=>{
    const form=new FormData();form.set('image',new File([image],'scan.png',{type:'image/png'}));form.set('original_image',new File([original],'original.png',{type:'image/png'}));form.set('part_id',part);
    return api('/monthly/problems/4/photos?mode=math&provider='+provider,{user,body:form});
  };
  try{return await run({sql,DB,api,upload,transcript:value=>{transcript=value;},visuals:value=>{visuals=value;},gradeEvidence:value=>{gradeEvidence=value;},gradingRequests,beforeOcr:callback=>{beforeOcr=callback;},ocrCalls:()=>ocrCalls,screenCalls:()=>screenCalls});}
  finally{globalThis.fetch=saved.fetch;globalThis.caches=saved.caches;Date.now=saved.now;sql.close();}
}

test('stores original bytes in bounded chunks, OCRs scan separately, and serves only owner/admin without caching',async()=>{
  await environment(async({sql,api,upload})=>{
    const result=await upload(); assert.equal(result.status,200);const id=result.data.photo_id;assert.match(id,/^[a-f0-9-]{36}$/);
    assert.equal(result.data.bytes,600000);assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photo_chunks').get().n,2);
    assert.equal(sql.prepare('SELECT ocr_text FROM monthly_answer_photos WHERE id=?').get(id).ocr_text,ANSWER+'\n'+WORKING);
    const original=await api('/monthly/photos/'+id);assert.equal(original.status,200);assert.deepEqual(original.data,png(600000));
    assert.equal(original.response.headers.get('Content-Type'),'image/png');assert.equal(original.response.headers.get('Cache-Control'),'private, no-store');
    assert.equal(original.response.headers.get('Access-Control-Allow-Origin'),'http://localhost:8765');
    assert.equal((await api('/monthly/photos/'+id,{user:0})).status,401);
    assert.equal((await api('/monthly/photos/'+id,{user:2})).status,404);
    assert.equal((await api('/monthly/photos/'+id,{user:3})).status,200);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0,'OCR is not a grading attempt');
  });
});

test('submitted photo IDs survive private history and idempotent replay; foreign ownership is rejected before consuming an attempt',async()=>{
  await environment(async({api,upload,screenCalls})=>{
    const id=(await upload()).data.photo_id;
    const foreign=await api('/problems/4/submit',{user:2,body:payload('foreign',[id])});assert.equal(foreign.status,400);assert.equal(foreign.data.attempts.used,0);
    const first=await api('/problems/4/submit',{body:payload('photos',[id,id])});assert.equal(first.status,200);assert.equal(first.data.status,'graded');assert.equal(first.data.detail,null);
    assert.deepEqual(first.data.answer_sheet.photo_ids,[id]);assert.equal(screenCalls(),0,'only full server-verified OCR coverage excludes this part');
    const replay=await api('/problems/4/submit',{body:payload('photos',[id])});assert.equal(replay.data.id,first.data.id);assert.equal(replay.data.attempts.used,1);
    const mine=(await api('/problems/4')).data.problem.mine[0];assert.equal(mine.via_ocr,1);assert.equal(mine.photo_attachments[0].id,id);assert.equal(mine.photo_attachments[0].bytes,600000);
    assert.equal((await api('/problems/4/submit',{body:payload('photos',[])})).status,409,'attachment changes cannot reuse an accepted request ID');
  });
});

test('via_ocr, unrelated same-part images and typed additions cannot bypass screening',async()=>{
  await environment(async({DB,sql,api,upload,transcript,screenCalls})=>{
    const id=(await upload()).data.photo_id, problem=sql.prepare('SELECT * FROM problems WHERE id=4').get();
    const value=payload('changed',[id]);value.parts[0].working+=' Additional typed text.';value.via_ocr=true;
    const normalized=normalizeMonthlyParts(problem,value);await prepareMonthlyPhotoSubmission(DB,1,problem,normalized,[id],'gemini');
    assert.deepEqual(normalized.photographedPartIds,[]);assert.equal(normalized.viaOcr,1);
    const forged=normalizeMonthlyParts(problem,{...payload('forged',[]),via_ocr:true});await prepareMonthlyPhotoSubmission(DB,1,problem,forged,[],'gemini');assert.equal(forged.viaOcr,0);
    const submitted=await api('/problems/4/submit',{body:value});assert.equal(submitted.status,200);assert.equal(screenCalls(),1);
    transcript('Unrelated printed text.');const unrelated=(await upload()).data.photo_id;
    const next=normalizeMonthlyParts(problem,payload('unrelated',[unrelated]));await prepareMonthlyPhotoSubmission(DB,1,problem,next,[unrelated],'gemini');assert.deepEqual(next.photographedPartIds,[]);
  });
});

test('bounds image uploads and atomic storage quotas, rejects invalid part IDs, and retains no empty OCR uploads',async()=>{
  await environment(async({sql,api,upload,transcript,ocrCalls})=>{
    assert.equal((await upload({part:'unknown'})).status,400);assert.equal(ocrCalls(),0);
    assert.equal((await upload({original:png(4*1024*1024+1)})).status,413);assert.equal(ocrCalls(),0);
    const invalid=new Uint8Array(32);assert.equal((await upload({original:invalid})).status,415);
    transcript('');assert.notEqual((await upload()).status,200);assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0);
    transcript(ANSWER+'\n'+WORKING);await upload();
    for(let i=0;i<39;i++)sql.prepare("INSERT INTO monthly_answer_photos(id,user_id,problem_id,part_id,mime,bytes,ocr_text,created_at) VALUES(?,1,4,'a','image/png',32,'fixture',?)").run(crypto.randomUUID(),NOW);
    const before=sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photo_chunks').get().n;
    assert.equal((await upload()).data.error,'monthly_photo_storage_full');assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,40);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photo_chunks').get().n,before,'failed reservation writes no orphan chunks');
    assert.equal((await api('/problems/4/submit',{body:payload('badids',['not-an-id'])})).status,400);
  });
});

test('monthly originals have no lab expiry and owner deletion removes all their original bytes',async()=>{
  await environment(async({DB,sql,upload})=>{
    await upload();await upload({user:2});assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,2);
    assert.ok(!sql.prepare('PRAGMA table_info(monthly_answer_photos)').all().some(row=>/expires|purge/.test(row.name)));
    await deleteMonthlyPhotos(DB,1);assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,1);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photo_chunks').get().n,2,'only other owner chunks remain');
  });
});

test('an OCR upload finishing after account deletion cannot recreate original photo bytes',async()=>{
  await environment(async({sql,api,upload,beforeOcr})=>{
    await upload();
    beforeOcr(async()=>{assert.equal((await api('/me',{method:'DELETE'})).status,200);});
    const late=await upload();assert.equal(late.status,401);assert.equal(late.data.error,'login_required');
    assert.equal(sql.prepare('SELECT deleted FROM users WHERE id=1').get().deleted,1);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,0);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photo_chunks').get().n,0);
  });
});

test('direct photo metadata binds the explicit provider and rejects mismatched grading before reserving an attempt',async()=>{
  await environment(async({sql,api,upload})=>{
    const photo=await upload({provider:'deepseek'});assert.equal(photo.status,200);assert.equal(photo.data.provider,'deepseek');
    assert.equal(sql.prepare('SELECT provider FROM monthly_answer_photos WHERE id=?').get(photo.data.photo_id).provider,'deepseek');
    const mismatch=await api('/problems/4/submit',{body:{...payload('wrong-provider',[photo.data.photo_id]),provider:'gemini'}});
    assert.equal(mismatch.status,409);assert.equal(mismatch.data.error,'provider_locked');assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0);
    const good=await api('/problems/4/submit',{body:{...payload('right-provider',[photo.data.photo_id]),provider:'deepseek'}});assert.equal(good.status,200);assert.equal(good.data.answer_sheet.provider,'deepseek');
    const foreign=await api('/problems/4/submit',{user:2,body:{...payload('foreign-provider',[photo.data.photo_id]),provider:'deepseek'}});assert.equal(foreign.status,400);assert.equal(foreign.data.error,'bad_photo_ids');
  });
});

test('image-only direct photos expose an owned evidence reference and retain original images at final grading',async()=>{
  await environment(async({sql,api,upload,transcript,visuals,gradeEvidence,gradingRequests})=>{
    transcript('');visuals([{page:1,kind:'graph',description:'A visible labelled curve and direction arrow',box:[0.1,0.1,0.9,0.9]}]);
    const image=png(700000),saved=await upload({original:image,provider:'deepseek'});
    assert.equal(saved.status,200);assert.equal(saved.data.text,'','photo references must not be presented as OCR text');
    const marker=`[PHOTO:${saved.data.photo_id}:a]`;assert.equal(saved.data.photo_evidence,marker);gradeEvidence(marker);
    const body={...payload('image-only-direct',[saved.data.photo_id]),provider:'deepseek',parts:[{id:'a',answer:marker,working:marker}]};
    const foreign=await api('/problems/4/submit',{user:2,body});assert.equal(foreign.status,400);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0);
    const graded=await api('/problems/4/submit',{body});assert.equal(graded.status,200);assert.equal(graded.data.status,'graded');
    assert.ok(graded.data.score>0,'the final server-owned image map authorizes evidence for the matching part');
    assert.equal(gradingRequests.length,1);const request=JSON.stringify(gradingRequests[0]);
    assert.ok(request.includes(Buffer.from(image).toString('base64')),'final grading receives the original, not just OCR or a marker');
    assert.ok(request.includes(marker));assert.ok(!request.includes('"cachedContent"'));
  });
});

test('a visual batch beyond the provider-safe byte budget fails before reserving an attempt or grading',async()=>{
  await environment(async({sql,api,upload,gradingRequests,screenCalls})=>{
    const saved=await upload(),ids=[saved.data.photo_id];assert.equal(saved.status,200);
    // Four legitimate maximum-size photos cannot fit one provider request. The
    // metadata alone must reject this batch, before chunks or models are loaded.
    sql.prepare('UPDATE monthly_answer_photos SET bytes=? WHERE id=?').run(4*1024*1024,ids[0]);
    for(let i=0;i<3;i++){
      const id=crypto.randomUUID();ids.push(id);
      sql.prepare(`INSERT INTO monthly_answer_photos(id,user_id,problem_id,part_id,mime,bytes,ocr_text,provider,created_at)
        SELECT ?,user_id,problem_id,part_id,mime,bytes,ocr_text,provider,created_at FROM monthly_answer_photos WHERE id=?`).run(id,ids[0]);
    }
    const result=await api('/problems/4/submit',{body:payload('oversized-visual-batch',ids)});
    assert.equal(result.status,413);assert.equal(result.data.error,'monthly_visuals_too_large');
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0);
    assert.equal(screenCalls(),0);assert.equal(gradingRequests.length,0,'neither screening nor final grading may start');
  });
});
