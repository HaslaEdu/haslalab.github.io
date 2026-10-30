// The real Worker and SQLite, with local OCR/extraction/grading stand-ins only.
import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import worker from './src/index.js';
import { getMonthlyAnswerSheet } from '../monthly-problems.mjs';
import { extractMonthlyCaptureParts } from './src/monthly-capture.js';

const NOW=Date.parse('2026-11-01T12:00:00+09:00')/1000;
const ANSWER='$x=1$',WORKING='Apply Newton’s second law to the mass.';
const TRANSCRIPT='HaslaLab monthly answer sheet\nPart a\nFinal answer\n'+ANSWER+'\nWorking\n'+WORKING;
const requestId=name=>name.padEnd(32,'x');
const png=size=>{const out=new Uint8Array(size).fill(79);out.set([137,80,78,71,13,10,26,10]);return out;};
const parts=()=>[{id:'a',answer:ANSWER,working:WORKING}];

async function environment(run) {
  const sql=new DatabaseSync(':memory:');
  for(const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(name=>/^00(?:0[1-9]|1[012])_.*\.sql$/.test(name)).sort())sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
  let beforeReserve=async()=>{},beforeGrant=async()=>{},failPhoto=false;const reservationBatches=[];
  const DB={prepare(query){const st=sql.prepare(query),make=args=>({query,bind:(...values)=>make(values.map(value=>value instanceof ArrayBuffer?new Uint8Array(value):value)),
    async first(){return st.get(...args)||null;},async all(){return{results:st.all(...args)};},async run(){return this.executeSync();},
    executeSync(){if(st.columns().length)return{results:st.all(...args)};const r=st.run(...args);return{results:[],meta:{changes:r.changes,last_row_id:Number(r.lastInsertRowid)}};}});return make([]);},
    async batch(statements){if(statements.some(st=>st.query.includes('INSERT INTO monthly_capture_sessions'))){const run=beforeGrant;beforeGrant=async()=>{};await run();}
      if(statements.some(st=>st.query.includes('INSERT INTO monthly_answer_requests'))){reservationBatches.push(statements.map(st=>st.query));const run=beforeReserve;beforeReserve=async()=>{};await run();}
      sql.exec('BEGIN');try{const value=statements.map(st=>{const result=st.executeSync();if(failPhoto&&st.query.includes('INSERT INTO monthly_capture_pages')){failPhoto=false;throw Error('local photo interruption');}return result;});sql.exec('COMMIT');return value;}catch(error){sql.exec('ROLLBACK');throw error;}}};
  const saved={fetch:globalThis.fetch,caches:globalThis.caches,now:Date.now};
  let clock=NOW,transcript=TRANSCRIPT,extracted=parts(),beforeOcr=async()=>{},beforeGrade=async()=>{},beforeExtract=async()=>{};
  const calls={ocr:0,extract:0,grade:0,screen:0};
  Date.now=()=>clock*1000;globalThis.caches={default:{async match(){},async put(){}}};
  const tokens=[];
  for(let id=1;id<=2;id++){
    const token=('monthly-capture-owner-'+id).padEnd(48,'x');tokens.push(token);
    const hash=Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token))).toString('base64url');
    sql.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at) VALUES(?,?,?,'unused','user',?)").run(id,'capture'+id,'Capture '+id,NOW-100);
    sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(hash,id,NOW-100,NOW+864000);
  }
  globalThis.fetch=async(url,init)=>{
    if(String(url).includes('document-digitization')){
      calls.ocr++;await beforeOcr();
      assert.deepEqual(new Uint8Array(await init.body.get('document').arrayBuffer()),png(32));
      return Response.json({content:{markdown:transcript},confidence:0.98,usage:{pages:1}});
    }
    assert.match(String(url),/:generateContent$/);
    const request=JSON.parse(init.body),schema=request.generationConfig.responseSchema;
    let raw;
    if(schema.properties.parts){calls.extract++;await beforeExtract();raw={parts:extracted};}
    else if(schema.properties.assessment){calls.screen++;raw={assessment:'uncertain',confidence:0.5,signals:[]};}
    else{
      calls.grade++;await beforeGrade();
      const rubric=JSON.parse(sql.prepare('SELECT rubric FROM problems WHERE id=4').get().rubric);
      raw={scores:rubric.map(c=>({id:c.id,got:c.id==='a'?c.max:0,note:'PRIVATE_CAPTURE_NOTE',decision:c.id==='a'?'met':'not_met',evidence:c.id==='a'?[ANSWER]:[]})),feedback:[],confidence:0.99};
    }
    return Response.json({candidates:[{content:{parts:[{text:JSON.stringify(raw)}]}}]});
  };
  const env={DB,ALLOWED_ORIGINS:'http://localhost:8765',UPSTAGE_API_KEY:'local-ocr',GEMINI_API_KEY:'local-grader',LAB_KEEP_HOURS:'off'};
  const api=async(path,{user=1,body,method,headers={}}={})=>{
    const form=body instanceof FormData,response=await worker.fetch(new Request('http://monthly.local/api'+path,{method:method||(body===undefined?'GET':'POST'),
      headers:{Origin:'http://localhost:8765','Cache-Control':'no-cache',...(user?{Authorization:'Bearer '+tokens[user-1]}:{}),...(!form&&body!==undefined?{'Content-Type':'application/json'}:{}),...headers},
      ...(body===undefined?{}:{body:form?body:JSON.stringify(body)})}),env);
    return{status:response.status,response,data:response.headers.get('Content-Type')?.includes('application/json')?await response.json():new Uint8Array(await response.arrayBuffer())};
  };
  const grant=async(body={},user=1)=>api('/monthly/problems/4/scan',{user,body});
  const phone=async(scan,path='',options={})=>api('/monthly/up'+path,{user:0,...options,headers:{'X-Lab-Token':scan.token,...options.headers}});
  const upload=async(scan,{page=1,kind='answer',original=png(200),image=png(32),request_id=crypto.randomUUID()}={})=>{
    const form=new FormData();form.set('image',new File([image],'scan.png',{type:'image/png'}));form.set('original_image',new File([original],'original.png',{type:'image/png'}));
    if(request_id!==null)form.set('request_id',request_id);
    return phone(scan,`/pages?task=${page}&kind=${kind}`,{body:form});
  };
  const submit=async(scan,key,extra={})=>api('/problems/4/submit',{body:{scan_id:scan.id,request_id:requestId(key),lang:'ko',...extra}});
  try{return await run({sql,DB,api,grant,phone,upload,submit,calls,time:value=>{clock=value;},
    transcript:value=>{transcript=value;},extract:value=>{extracted=value;},beforeOcr:callback=>{beforeOcr=callback;},beforeGrade:callback=>{beforeGrade=callback;},beforeExtract:callback=>{beforeExtract=callback;},beforeReserve:callback=>{beforeReserve=callback;},beforeGrant:callback=>{beforeGrant=callback;},failPhoto:()=>{failPhoto=true;},reservationBatches});}
  finally{globalThis.fetch=saved.fetch;globalThis.caches=saved.caches;Date.now=saved.now;sql.close();}
}

test('capture grants are account-scoped and upload-only; only their hash is stored',async()=>{
  await environment(async({api,grant,phone,sql})=>{
    assert.equal((await grant({},0)).status,401);
    const created=await grant();assert.equal(created.status,200);const scan=created.data.scan;
    assert.match(scan.token,/^[a-f0-9-]{36}\.[A-Za-z0-9_-]{43}$/);assert.equal(scan.expires_at,NOW+7200);
    assert.ok(!sql.prepare('SELECT token_hash FROM monthly_capture_sessions WHERE id=?').get(scan.id).token_hash.includes(scan.token));
    assert.equal((await api('/monthly/problems/4/scan?scan_id='+scan.id,{user:2})).status,404);
    assert.equal((await api('/problems/4/submit',{user:2,body:{scan_id:scan.id,request_id:requestId('foreign-capture')}})).status,404);
    assert.equal((await api('/monthly/problems/4/scan?scan_id='+scan.id,{user:0,headers:{'X-Lab-Token':scan.token}})).status,401);
    const mobile=await phone(scan);assert.equal(mobile.status,200);assert.equal(mobile.data.token,undefined);assert.equal(mobile.data.problem_id,4);
    assert.deepEqual(mobile.data.tasks,['1','2','3','4']);
    const owner=await api('/monthly/problems/4/scan?scan_id='+scan.id);assert.equal(owner.status,200);assert.equal(owner.data.scan.token,undefined);
    assert.equal((await api('/problems/4/submit',{user:0,body:{scan_id:scan.id,request_id:requestId('phone-grade')},headers:{'X-Lab-Token':scan.token}})).status,401);
    assert.equal((await api('/monthly/up',{headers:{'X-Lab-Token':'wrong'}})).status,403);
    assert.equal((await phone(scan,'',{headers:{'X-Lab-Token':''}})).status,403);
  });
});

test('multiple printed pages and working continuations keep their declared subquestion association',async()=>{
  await environment(async({grant,phone,upload,extract,transcript})=>{
    const scan=(await grant()).data.scan;await upload(scan);
    const secondId=getMonthlyAnswerSheet({id:4,week:'2026-11'}).pages[1][0];
    const secondAnswer='$v=2$',secondWorking='A second page contains its own derivation.';
    transcript(secondAnswer+'\n'+secondWorking);extract([{id:secondId,answer:secondAnswer,working:secondWorking}]);
    assert.equal((await upload(scan,{page:2})).status,200);
    const continuation='This continuation gives another supporting step.';
    transcript(continuation);extract([{id:'a',answer:'ignored invented answer',working:continuation}]);
    assert.equal((await upload(scan,{page:1,kind:'working'})).status,200);
    const view=(await phone(scan)).data;
    assert.equal(view.pages.length,3);assert.deepEqual(view.pages.map(page=>page.page_no).sort(),[1,1,2]);
    assert.equal(view.parts.find(part=>part.id==='a').answer,ANSWER,'a working continuation cannot replace the answer');
    assert.ok(view.parts.find(part=>part.id==='a').working.includes(WORKING));assert.ok(view.parts.find(part=>part.id==='a').working.includes(continuation));
    assert.equal(view.parts.find(part=>part.id===secondId).answer,secondAnswer);
    assert.equal(view.parts.find(part=>part.id===secondId).working,secondWorking);
  });
});

test('full pages retain originals and exact OCR-derived parts; removal detaches without spending an attempt',async()=>{
  await environment(async({api,grant,phone,upload,sql,calls})=>{
    const scan=(await grant()).data.scan,result=await upload(scan);assert.equal(result.status,200);assert.equal(result.data.task,'1');assert.equal(result.data.ocr_status,'done');
    const view=(await phone(scan)).data;assert.equal(view.pages.length,1);assert.equal(view.pages[0].id,result.data.id);assert.equal(view.pages[0].page_no,1);
    assert.equal(view.parts.find(part=>part.id==='a').answer,ANSWER);assert.equal(view.parts.find(part=>part.id==='a').working,WORKING);
    assert.equal((await api('/monthly/photos/'+result.data.id,{user:0,headers:{'X-Lab-Token':scan.token}})).status,401);
    assert.deepEqual((await api('/monthly/photos/'+result.data.id)).data,png(200));
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0);assert.deepEqual(calls,{ocr:1,extract:1,grade:0,screen:0});
    assert.equal((await phone(scan,'/pages/'+result.data.id,{method:'DELETE'})).status,200);
    assert.equal((await phone(scan)).data.pages.length,0);assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,1,'original retention is independent of active answer pages');
  });
});

test('extraction accepts only supported contiguous spans and declared page parts, and working sheets cannot supply final answers',async()=>{
  const sheet=getMonthlyAnswerSheet({id:4,week:'2026-11'});
  const extract=raw=>extractMonthlyCaptureParts(sheet,1,TRANSCRIPT,'answer',async()=>({raw:{parts:raw}}));
  assert.equal((await extract(parts()))[0].answer,ANSWER);
  for(const invalid of [[{id:'a',answer:'$x=2$',working:WORKING}],[...parts(),...parts()],[{id:'j',answer:ANSWER,working:WORKING}],
    [{id:'a',answer:ANSWER,working:'Apply Newton’s second law.'}]])await assert.rejects(extract(invalid),error=>error.code==='capture_read_failed');
  const work=await extractMonthlyCaptureParts(sheet,1,TRANSCRIPT,'working',async()=>({raw:{parts:parts()}}));assert.equal(work[0].answer,'');assert.equal(work[0].working,WORKING);
});

test('letter-labelled astronomy pages map to the durable submitted part IDs for both new and older printed sheets',async()=>{
  const sheet=getMonthlyAnswerSheet(7);
  for(const label of ['a','16']){
    const text='Part '+label+'\nFinal answer\n'+ANSWER+'\nWorking\n'+WORKING;
    const result=await extractMonthlyCaptureParts(sheet,1,text,'answer',async prompt=>{
      assert.ok(prompt.includes('"id":"16","printed_label":"a","legacy_label":"16"'));
      assert.ok(prompt.includes('"id":"17","printed_label":"b","legacy_label":"17"'));
      return{raw:{parts:[{id:'16',answer:ANSWER,working:WORKING}]}};
    });
    assert.deepEqual(result,[{id:'16',answer:ANSWER,working:WORKING},{id:'17',answer:'',working:''}]);
  }
});

test('unsupported extraction is saved for retake and cannot be submitted or consume a chance',async()=>{
  await environment(async({grant,phone,upload,submit,extract,sql,calls})=>{
    const scan=(await grant()).data.scan;extract([{id:'a',answer:'invented answer',working:WORKING}]);
    const result=await upload(scan);assert.equal(result.status,200);assert.equal(result.data.ocr_status,'failed');
    const view=(await phone(scan)).data;assert.equal(view.pages[0].ocr_status,'failed');assert.equal(view.parts[0].answer,'');
    const graded=await submit(scan,'failed-extraction');assert.equal(graded.status,422);assert.equal(graded.data.error,'capture_read_failed');
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0);assert.equal(calls.grade,0);
  });
});

test('scan_id submission derives immutable answers on the server, closes uploads, and replays exactly one accepted attempt',async()=>{
  await environment(async({api,grant,phone,upload,submit,sql,calls})=>{
    const scan=(await grant()).data.scan;await upload(scan);
    const response=await submit(scan,'captured',{parts:[{id:'a',answer:'forged final answer',working:'forged working'}],photo_ids:['forged'],via_ocr:false});
    assert.equal(response.status,200);assert.equal(response.data.status,'graded');assert.equal(response.data.attempts.used,1);assert.equal(response.data.detail,null);
    assert.equal(response.data.answer_sheet.parts[0].answer,ANSWER);assert.equal(response.data.answer_sheet.parts[0].working,WORKING);
    assert.equal(response.data.answer_sheet.capture.scan_id,scan.id);assert.equal(calls.screen,0,'server-derived photographed work is not treated as typed text');assert.equal(calls.grade,1);
    const record=sql.prepare('SELECT answer,via_ocr FROM submissions WHERE id=?').get(response.data.id);assert.ok(!record.answer.includes('forged'));assert.equal(record.via_ocr,1);
    assert.equal((await phone(scan)).data.open,false);assert.equal((await upload(scan)).data.error,'scan_over');
    const replay=await submit(scan,'captured',{parts:[{id:'a',answer:'a different forged value',working:'different forged work'}]});
    assert.equal(replay.status,200);assert.equal(replay.data.id,response.data.id);assert.deepEqual(replay.data.answer_sheet,response.data.answer_sheet);assert.equal(calls.grade,1);
    assert.equal((await submit(scan,'another-key')).status,409);assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,1);
    const mine=(await api('/problems/4')).data.problem.mine[0];assert.equal(mine.answer_sheet.capture.scan_id,scan.id);assert.equal(mine.photo_attachments.length,1);
  });
});

test('concurrent distinct request IDs cannot charge or grade the same capture twice',async()=>{
  await environment(async({grant,upload,submit,sql,calls})=>{
    const scan=(await grant()).data.scan;await upload(scan);
    const result=await Promise.all([submit(scan,'concurrent-a'),submit(scan,'concurrent-b')]);
    assert.deepEqual(result.map(item=>item.status).sort(),[200,409]);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,1);assert.equal(calls.grade,1);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_requests').get().n,1);
  });
});

test('acceptance freezes the capture before grading and an in-flight same-key retry reuses one attempt',async()=>{
  await environment(async({grant,phone,upload,submit,beforeGrade,sql,calls})=>{
    const scan=(await grant()).data.scan;await upload(scan);
    let start,release;const started=new Promise(resolve=>{start=resolve;}),gate=new Promise(resolve=>{release=resolve;});
    beforeGrade(async()=>{start();await gate;});
    const first=submit(scan,'inflight-capture');await started;
    try{
      assert.equal((await phone(scan)).data.open,false);
      assert.equal((await upload(scan)).data.error,'scan_over');
      const replay=await submit(scan,'inflight-capture');assert.equal(replay.status,200);assert.equal(replay.data.processing,true);assert.equal(replay.data.attempts.used,1);
      assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,1);assert.equal(calls.grade,1);
    }finally{release();}
    assert.equal((await first).data.status,'graded');
  });
});

test('capture grants rotate, expire, and reject late OCR completions after closure',async()=>{
  await environment(async({grant,phone,upload,beforeOcr,time,sql})=>{
    const first=(await grant()).data.scan,rotated=(await grant({scan_id:first.id})).data.scan;
    assert.notEqual(rotated.token,first.token);assert.equal((await phone(first)).status,403);assert.equal((await phone(rotated)).status,200);
    time(rotated.expires_at+1);const expired=await phone(rotated);assert.equal(expired.status,403);assert.equal(expired.data.error,'scan_over');assert.equal(expired.data.pages,undefined);assert.equal((await upload(rotated)).data.error,'scan_over');
    const current=(await grant({fresh:true})).data.scan;
    beforeOcr(async()=>{await grant({fresh:true});});
    const late=await upload(current);assert.equal(late.status,409);assert.equal(late.data.error,'scan_over');
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_capture_pages WHERE session_id=? AND active=1').get(current.id).n,0);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,0,'closure rejects original bytes in the same transaction as page association');
  });
});

test('an expired unsubmitted capture renews its upload grant and retains its already photographed pages',async()=>{
  await environment(async({grant,phone,upload,time,calls,sql})=>{
    const first=(await grant()).data.scan;await upload(first);time(first.expires_at+1);
    assert.equal((await phone(first)).status,403,'expired phone grants no longer expose retained answers');
    const restored=await grant({scan_id:first.id});assert.equal(restored.status,200);const renewed=restored.data.scan;
    assert.equal(renewed.id,first.id);assert.equal(renewed.open,true);assert.equal(renewed.expires_at,first.expires_at+7201);
    assert.notEqual(renewed.token,first.token);assert.equal(renewed.pages.length,1);assert.equal(calls.ocr,1);
    assert.equal((await phone(first)).status,403);assert.equal((await phone(renewed)).data.open,true);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0);
  });
});

test('capture creation finishing after account deletion cannot recreate an upload grant',async()=>{
  await environment(async({grant,api,beforeGrant,sql,calls})=>{
    beforeGrant(async()=>{assert.equal((await api('/me',{method:'DELETE'})).status,200);});
    const created=await grant();assert.equal(created.status,401);assert.equal(created.data.error,'login_required');
    assert.equal(sql.prepare('SELECT deleted FROM users WHERE id=1').get().deleted,1);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_capture_sessions').get().n,0);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_capture_pages').get().n,0);
    assert.equal(calls.ocr,0);
  });
});

test('pages sent in the same second preserve insertion order instead of random UUID order',async()=>{
  await environment(async({grant,upload,phone,extract,transcript,sql})=>{
    const scan=(await grant()).data.scan,first=(await upload(scan)).data;
    const secondAnswer='$x=2$',secondWork='A later handwritten derivation.';transcript(secondAnswer+'\n'+secondWork);extract([{id:'a',answer:secondAnswer,working:secondWork}]);
    const second=(await upload(scan)).data;
    const replacements=[[first.id,'ffffffff-ffff-4fff-bfff-ffffffffffff'],[second.id,'00000000-0000-4000-8000-000000000000']];
    // TEXT primary keys remain opaque; force the reverse lexical order while
    // retaining each row's original insert order and the same-second timestamp.
    for(const [oldId,newId] of replacements){
      sql.prepare('UPDATE monthly_answer_photo_chunks SET photo_id=? WHERE photo_id=?').run(newId,oldId);
      sql.prepare('UPDATE monthly_answer_photos SET id=? WHERE id=?').run(newId,oldId);
      sql.prepare('UPDATE monthly_capture_pages SET photo_id=? WHERE photo_id=?').run(newId,oldId);
    }
    const viewed=(await phone(scan)).data;assert.deepEqual(viewed.pages.map(page=>page.id),replacements.map(([,id])=>id));
    assert.equal(viewed.parts[0].answer,secondAnswer);assert.equal(viewed.parts[0].working,WORKING+'\n\n'+secondWork);
  });
});

test('removing a page or revoking a capture between preparation and reservation consumes no attempt or grader call',async()=>{
  for(const race of ['remove','revoke'])await environment(async({grant,upload,submit,beforeReserve,sql,calls})=>{
    const scan=(await grant()).data.scan;await upload(scan);
    beforeReserve(async()=>{
      if(race==='remove')sql.prepare('UPDATE monthly_capture_pages SET active=0 WHERE session_id=?').run(scan.id);
      sql.prepare('UPDATE monthly_capture_sessions SET revision=revision+1,revoked=? WHERE id=?').run(race==='revoke'?1:0,scan.id);
    });
    const result=await submit(scan,'racing-'+race);assert.equal(result.status,409);assert.equal(result.data.error,'capture_changed');
    assert.equal(result.data.attempts.used,0);assert.equal(calls.grade,0);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,0);assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_requests').get().n,0);
    assert.equal(sql.prepare('SELECT submission_id FROM monthly_capture_sessions WHERE id=?').get(scan.id).submission_id,null);
  });
});

test('captured submission reservation and upload closure are committed in one atomic batch',async()=>{
  await environment(async({grant,upload,submit,sql,reservationBatches,beforeGrade})=>{
    const scan=(await grant()).data.scan;await upload(scan);
    beforeGrade(async()=>{assert.ok(sql.prepare('SELECT submission_id FROM monthly_capture_sessions WHERE id=?').get(scan.id).submission_id);});
    assert.equal((await submit(scan,'atomic-close')).status,200);
    assert.equal(reservationBatches.length,1);assert.ok(reservationBatches[0].some(query=>query.includes('UPDATE monthly_capture_sessions')));
    assert.ok(reservationBatches[0].some(query=>query.includes('INSERT INTO submissions')));
  });
});

test('three fresh captures share the same problem cap and a fourth can never invoke OCR or grading',async()=>{
  await environment(async({api,grant,upload,submit,sql,calls})=>{
    for(let attempt=1;attempt<=3;attempt++){
      const result=await grant({fresh:true});assert.equal(result.status,200);const scan=result.data.scan;
      assert.equal((await upload(scan)).status,200);const grade=await submit(scan,'max-'+attempt);assert.equal(grade.status,200);assert.equal(grade.data.attempts.used,attempt);
    }
    const fourth=await grant({fresh:true});assert.equal(fourth.status,409);assert.equal(fourth.data.error,'attempts_exhausted');
    assert.equal(calls.ocr,3);assert.equal(calls.grade,3);assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,3);
    const typed=await api('/problems/4/submit',{body:{request_id:requestId('typed-bypass'),parts:parts()}});assert.equal(typed.status,409);
  });
});

test('exact-byte retry keys replay one OCR/extraction receipt and reject changed payload, printed page or kind',async()=>{
  await environment(async({grant,upload,phone,sql,calls})=>{
    const scan=(await grant()).data.scan,id=crypto.randomUUID();
    const first=await upload(scan,{request_id:id}),retry=await upload(scan,{request_id:id});
    assert.equal(first.status,200);assert.equal(retry.status,200);assert.equal(retry.data.id,first.data.id);assert.equal(retry.data.replayed,true);
    assert.equal(calls.ocr,1);assert.equal(calls.extract,1);assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,1);
    const original=png(200);original[199]^=1;
    for(const options of [{original},{image:png(33)},{page:2},{kind:'working'}]){
      const conflict=await upload(scan,{request_id:id,...options});assert.equal(conflict.status,409);assert.equal(conflict.data.error,'upload_conflict');
    }
    assert.equal(calls.ocr,1);assert.equal(calls.extract,1);assert.equal((await phone(scan)).data.pages.length,1);
    assert.equal((await upload(scan,{request_id:'short'})).status,400);
  });
});

test('already-open legacy phone pages without request IDs still deduplicate exact-byte retries',async()=>{
  await environment(async({grant,upload,sql,calls})=>{
    const scan=(await grant()).data.scan,first=await upload(scan,{request_id:null}),retry=await upload(scan,{request_id:null});
    assert.equal(first.status,200);assert.equal(retry.data.id,first.data.id);assert.equal(retry.data.replayed,true);
    assert.equal(calls.ocr,1);assert.equal(calls.extract,1);assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_capture_uploads').get().n,1);
  });
});

test('parallel upload retries perform one OCR/extraction and explicitly report processing',async()=>{
  await environment(async({grant,upload,beforeOcr,calls,sql})=>{
    const scan=(await grant()).data.scan,id=crypto.randomUUID();let signal,release;
    const started=new Promise(resolve=>{signal=resolve;}),gate=new Promise(resolve=>{release=resolve;});
    beforeOcr(async()=>{signal();await gate;});const first=upload(scan,{request_id:id});await started;
    const pending=await upload(scan,{request_id:id});assert.equal(pending.status,409);assert.equal(pending.data.error,'upload_processing');assert.equal(pending.data.retry_after,2);
    assert.equal(calls.ocr,1);release();const saved=await first;assert.equal(saved.status,200);
    assert.equal((await upload(scan,{request_id:id})).data.id,saved.data.id);assert.equal(calls.ocr,1);assert.equal(calls.extract,1);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_capture_pages').get().n,1);
  });
});

test('a stale processing lease can be retried without letting late OCR overwrite the one stored page',async()=>{
  await environment(async({grant,upload,beforeOcr,time,calls,sql})=>{
    const scan=(await grant()).data.scan,id=crypto.randomUUID();let signal,release;
    const started=new Promise(resolve=>{signal=resolve;}),gate=new Promise(resolve=>{release=resolve;});
    beforeOcr(async()=>{if(calls.ocr===1){signal();await gate;}});const first=upload(scan,{request_id:id});await started;
    time(NOW+301);const restored=await upload(scan,{request_id:id});assert.equal(restored.status,200);
    release();const late=await first;assert.equal(late.status,200);assert.equal(late.data.id,restored.data.id);assert.equal(late.data.replayed,true);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,1);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_capture_pages').get().n,1);
  });
});

test('closure during extraction cannot leave new original bytes, pages or a stale receipt',async()=>{
  for(const race of ['revoke','rotate','expire','submit','delete','retire','exhaust'])await environment(async({sql,api,grant,upload,submit,beforeExtract,time})=>{
    const scan=(await grant()).data.scan;assert.equal((await upload(scan)).status,200);
    beforeExtract(async()=>{
      if(race==='revoke')assert.equal((await api('/monthly/problems/4/scan?scan_id='+scan.id,{method:'DELETE'})).status,200);
      if(race==='rotate')assert.equal((await grant({scan_id:scan.id})).status,200);
      if(race==='expire')time(scan.expires_at+1);
      if(race==='submit')assert.equal((await submit(scan,'in-extractor')).status,200);
      if(race==='delete')assert.equal((await api('/me',{method:'DELETE'})).status,200);
      if(race==='retire')sql.prepare("INSERT INTO monthly_problem_retirements(problem_id,retired_at,reason) VALUES(4,?,'test closure')").run(NOW);
      if(race==='exhaust')for(let i=0;i<3;i++)sql.prepare("INSERT INTO submissions(problem_id,user_id,answer,status,in_week,created_at) VALUES(4,1,'prior','pending',1,?)").run(NOW);
    });
    const late=await upload(scan);assert.ok([401,409].includes(late.status),race+JSON.stringify(late.data));
    const count=race==='delete'?0:1;
    for(const table of ['monthly_answer_photos','monthly_answer_photo_chunks','monthly_capture_pages'])assert.equal(sql.prepare(`SELECT COUNT(*) n FROM ${table}`).get().n,count,race+table);
    if(race==='delete')assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_capture_uploads').get().n,0);
  });
});

test('concurrent capture uploads enforce the original archive quota atomically',async()=>{
  await environment(async({sql,grant,upload,beforeExtract})=>{
    const scan=(await grant()).data.scan;
    for(let i=0;i<39;i++)sql.prepare("INSERT INTO monthly_answer_photos(id,user_id,problem_id,part_id,mime,bytes,ocr_text,created_at) VALUES(?,1,4,'a','image/png',32,'fixture',?)").run(crypto.randomUUID(),NOW);
    let reached=0,release;const gate=new Promise(resolve=>{release=resolve;});beforeExtract(async()=>{if(++reached===2)release();await gate;});
    const results=await Promise.all([upload(scan),upload(scan)]);assert.deepEqual(results.map(r=>r.status).sort(),[200,413]);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,40);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_capture_pages').get().n,1);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photo_chunks').get().n,1);
    assert.equal(sql.prepare('SELECT revision FROM monthly_capture_sessions WHERE id=?').get(scan.id).revision,1);
  });
});

test('photo/page/receipt transaction interruption rolls back together and the same request can retry',async()=>{
  await environment(async({sql,grant,upload,failPhoto})=>{
    const scan=(await grant()).data.scan,id=crypto.randomUUID();failPhoto();const previous=console.error,logs=[];let result;
    try{console.error=(...args)=>logs.push(args.join(' '));result=await upload(scan,{request_id:id});}finally{console.error=previous;}
    assert.equal(result.status,500);assert.ok(!logs.join('\n').includes(scan.token));
    for(const table of ['monthly_answer_photos','monthly_answer_photo_chunks','monthly_capture_pages'])assert.equal(sql.prepare(`SELECT COUNT(*) n FROM ${table}`).get().n,0);
    assert.equal(sql.prepare('SELECT revision FROM monthly_capture_sessions WHERE id=?').get(scan.id).revision,0);
    assert.equal((await upload(scan,{request_id:id})).status,200);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_capture_pages').get().n,1);
  });
});

test('capture uploads bound OCR transcripts and request journals before retaining any bytes',async()=>{
  await environment(async({sql,grant,upload,transcript,calls,phone})=>{
    const scan=(await grant()).data.scan;transcript('x'.repeat(256*1024+1));
    assert.equal((await upload(scan)).data.error,'ocr_too_big');assert.equal(calls.extract,0);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,0);
    for(let i=1;i<80;i++)sql.prepare("INSERT INTO monthly_capture_uploads(session_id,request_id,payload_hash,claim,created_at,updated_at) VALUES(?,?,?,'',?,0)").run(scan.id,'failed-request-'+String(i).padStart(3,'0'),'fixture',NOW);
    assert.equal((await upload(scan)).data.error,'monthly_capture_upload_limit');assert.equal(calls.ocr,1);
    for(let i=0;i<122;i++){const response=await phone(scan);if(response.status===429)return;}
    assert.fail('phone reads must be rate-limited');
  });
});

test('old empty capabilities are cleaned up without removing photographed drafts or their originals',async()=>{
  await environment(async({sql,grant,upload})=>{
    const empty=(await grant()).data.scan,photographed=(await grant({fresh:true})).data.scan;
    assert.equal((await upload(photographed)).status,200);
    sql.prepare("INSERT INTO monthly_capture_uploads(session_id,request_id,payload_hash,claim,created_at,updated_at) VALUES(?,'failed-request-journal','fixture','',?,0)").run(empty.id,NOW);
    sql.prepare('UPDATE monthly_capture_sessions SET expires_at=? WHERE id IN (?,?)').run(NOW-86401,empty.id,photographed.id);
    assert.equal((await grant({fresh:true})).status,200);
    assert.equal(sql.prepare('SELECT id FROM monthly_capture_sessions WHERE id=?').get(empty.id),undefined);
    assert.equal(sql.prepare('SELECT session_id FROM monthly_capture_uploads WHERE session_id=?').get(empty.id),undefined);
    assert.ok(sql.prepare('SELECT id FROM monthly_capture_sessions WHERE id=?').get(photographed.id));
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_answer_photos').get().n,1);
  });
});
