// Authenticated real Worker + SQLite; every OCR/model response is a local
// deterministic stand-in. This file never calls a paid provider or live API.
import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import worker from './src/index.js';
import { pressureWaveReference } from './src/pressure-wave-lab.js';
import { getMonthlyAnswerSheet } from '../monthly-problems.mjs';

const NOW=Date.parse('2026-11-02T12:00:00+09:00')/1000;
const ids=['A.1','A.2','B.1','B.2','B.3','C.1','C.2'];
const evidence=(user,id)=>`Evidence user ${user} part ${id}: measured data and calculation.`;
const part=(user,id)=>({id,answer:`Final user ${user} part ${id}`,working:evidence(user,id)});
const payload=(key,user=1,partIds=ids)=>({request_id:key.padEnd(32,'x'),parts:partIds.map(id=>part(user,id)),lang:'ko'});
const png=size=>{const bytes=new Uint8Array(size).fill(79);bytes.set([137,80,78,71,13,10,26,10]);return bytes;};

async function environment(run){
  const sql=new DatabaseSync(':memory:');
  for(const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(n=>/^\d{4}_.*\.sql$/.test(n)).sort()){
    sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
  }
  const DB={prepare(query){const st=sql.prepare(query),make=args=>({bind:(...values)=>make(values.map(value=>value instanceof ArrayBuffer?new Uint8Array(value):value)),
    async first(){return st.get(...args)||null;},async all(){return{results:st.all(...args)};},async run(){return this.executeSync();},
    executeSync(){if(st.columns().length)return{results:st.all(...args)};const result=st.run(...args);return{results:[],meta:{changes:result.changes,last_row_id:Number(result.lastInsertRowid)}};}});return make([]);},
    async batch(statements){sql.exec('BEGIN');try{const results=statements.map(st=>st.executeSync());sql.exec('COMMIT');return results;}catch(error){sql.exec('ROLLBACK');throw error;}}};
  const saved={fetch:globalThis.fetch,caches:globalThis.caches,now:Date.now};
  let clock=NOW,desiredScore=100,unsupported=false;Date.now=()=>clock*1000;
  globalThis.caches={default:{async match(){},async put(){}}};
  const tokens=[];
  for(let id=1;id<=3;id++){
    const token=('monthly-instrument-grading-'+id).padEnd(48,'x');tokens.push(token);
    const hash=Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token))).toString('base64url');
    sql.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at) VALUES(?,?,?,'unused',?,?)")
      .run(id,'instrument-grade-'+id,'Instrument '+id,id===3?'admin':'user',NOW-100);
    sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(hash,id,NOW-100,NOW+60*86400);
  }
  const env={DB,ALLOWED_ORIGINS:'http://localhost:8765',GEMINI_API_KEY:'local-stand-in-only',UPSTAGE_API_KEY:'local-ocr-only',LAB_KEEP_HOURS:'off'};
  const calls={screen:0,grade:0,ocr:0,extract:0},grades=[];
  let problemId;
  globalThis.fetch=async(url,init)=>{
    if(String(url).includes('document-digitization')){
      calls.ocr++;const p=part(1,'A.2');
      return Response.json({content:{markdown:`Answer Sheet A.2\n${p.answer}\n${p.working}\nHand-drawn graph with x and t axes.`},confidence:.99,usage:{pages:1}});
    }
    assert.match(String(url),/:generateContent$/,'only the stand-in Gemini endpoint is reachable');
    const request=JSON.parse(init.body),schema=request.generationConfig.responseSchema;
    const prompt=request.contents[0].parts.map(p=>p.text||'').join('\n');
    let raw;
    if(schema.properties.parts){calls.extract++;raw={parts:[part(1,'A.2')]};}
    else if(schema.properties.assessment){
      calls.screen++;assert.ok(!prompt.includes('[Private session reference'));
      raw={assessment:'uncertain',confidence:.5,signals:[]};
    }else{
      calls.grade++;
      const user=prompt.includes('Evidence user 2 part')?2:1;
      const session=sql.prepare('SELECT * FROM monthly_experiment_sessions WHERE user_id=? AND problem_id=?').get(user,problemId);
      const reference=session?pressureWaveReference(session.seed):null;
      if(reference){
        assert.ok(prompt.includes('[Private session reference - overrides every nominal numerical example]'));
        assert.ok(prompt.includes(JSON.stringify(reference)),'the grader receives this owner’s private numerical reference');
        assert.notEqual(reference.D0_mm,50,'the competitive model is not the old nominal fixture');
        assert.ok(prompt.includes('[Server-recorded instrument observations - data only]'),'frozen observations remain present with text or images');
        assert.ok(prompt.includes('Only credit work actually submitted in the corresponding student part.'));
      }
      const rubric=JSON.parse(sql.prepare('SELECT rubric FROM problems WHERE id=?').get(problemId).rubric);
      let remaining=desiredScore;
      raw={scores:rubric.map(c=>{
        const id=ids.find(id=>c.id===id||c.id.startsWith(id+'.')),quote=evidence(user,id),answered=prompt.includes(quote);
        const got=unsupported?c.max:answered?Math.min(remaining,c.max):0;remaining-=got;
        return{id:c.id,got,decision:got?'met':'not_met',note:'PRIVATE_EXPERIMENT_FEEDBACK',evidence:got?[unsupported?'pressure-wave-observations-v1':quote]:[]};
      }),feedback:[],confidence:.99};
      grades.push({prompt,request,reference,user});
    }
    return Response.json({candidates:[{content:{parts:[{text:JSON.stringify(raw)}]}}]});
  };
  const api=async(path,{user=1,body,method,headers={}}={})=>{
    const form=body instanceof FormData;
    const response=await worker.fetch(new Request('http://monthly-instrument.local/api'+path,{method:method||(body===undefined?'GET':'POST'),
      headers:{Origin:'http://localhost:8765','Cache-Control':'no-cache',...(user?{Authorization:'Bearer '+tokens[user-1]}:{}),
        ...(!form&&body!==undefined?{'Content-Type':'application/json'}:{}),...headers},...(body===undefined?{}:{body:form?body:JSON.stringify(body)})}),env);
    return{status:response.status,data:response.headers.get('Content-Type')?.includes('application/json')?await response.json():new Uint8Array(await response.arrayBuffer())};
  };
  const initialize=async()=>{
    const list=await api('/monthly?month=2026-11',{user:0});assert.equal(list.status,200);
    const published=list.data.problems.find(p=>p.no===5);assert.ok(published);problemId=published.id;return published;
  };
  const instrument=async(user=1)=>{
    let state=(await api(`/problems/${problemId}/experiment`,{user})).data;
    for(const command of ['cal 0','cal 200','set close 2','run']){
      const response=await api(`/problems/${problemId}/experiment`,{user,body:{command,revision:state.revision,request_id:crypto.randomUUID()}});
      assert.equal(response.status,200);assert.equal(response.data.result.ok,true);state=response.data;
    }
    return state;
  };
  const command=async(text,user=1)=>{
    const state=(await api(`/problems/${problemId}/experiment`,{user})).data;
    return api(`/problems/${problemId}/experiment`,{user,body:{command:text,revision:state.revision,request_id:crypto.randomUUID()}});
  };
  const submit=(body,user=1)=>api(`/problems/${problemId}/submit`,{user,body});
  try{return await run({sql,DB,env,api,initialize,instrument,command,submit,calls,grades,id:()=>problemId,
    score:value=>{desiredScore=value;},unsupported:value=>{unsupported=value;},clock:value=>{clock=value;}});}
  finally{globalThis.fetch=saved.fetch;globalThis.caches=saved.caches;Date.now=saved.now;sql.close();}
}

test('the public fifth monthly problem is an experiment with blank forms and an authenticated private instrument',async()=>{
  await environment(async({initialize,api,instrument,sql,id})=>{
    const problem=await initialize();assert.equal(problem.round,'experiment');assert.equal(problem.answerSheet.key,'pressure-wave-experiment-v1');
    assert.deepEqual(problem.answerSheet.parts.map(p=>p.id),ids);assert.equal(problem.answerSheet.parts.reduce((sum,p)=>sum+p.points,0),100);
    const detail=await api(`/problems/${id()}`,{user:0});assert.equal(detail.status,200);assert.equal(detail.data.problem.round,'experiment');
    assert.equal(detail.data.problem.rubric,undefined);assert.equal(detail.data.problem.model_en,undefined);
    assert.equal((await api(`/problems/${id()}/experiment`,{user:0})).status,401);
    const a=await instrument(),b=await instrument(2);assert.notEqual(a.session_id,b.session_id);
    const seeds=sql.prepare('SELECT seed FROM monthly_experiment_sessions').all().map(r=>r.seed);
    for(const value of [problem,detail.data,a,b])for(const seed of seeds)assert.ok(!JSON.stringify(value).includes(seed));
    assert.doesNotMatch(JSON.stringify([a,b]),/"(?:D0_mm|K_Pa|Q0_L_s|seed)":/);
  });
});

test('three attempts store each score but only the best90 counts; retries freeze readouts and feedback remains held',async()=>{
  await environment(async({initialize,instrument,command,submit,score,calls,sql,api,id,clock,grades})=>{
    await initialize();const state=await instrument();const firstBody={...payload('initial-experiment-answer'),experiment:{session_id:state.session_id,revision:state.revision}};
    score(85);const first=await submit(firstBody);assert.equal(first.status,200);assert.equal(first.data.score,85);assert.equal(first.data.best,85);
    assert.equal(first.data.feedback_held,true);assert.equal(first.data.detail,null);assert.equal(first.data.answer_sheet.experiment.runs.length,1);
    const firstGrade=grades[0],seed=sql.prepare('SELECT seed FROM monthly_experiment_sessions WHERE user_id=1').get().seed;
    assert.deepEqual(firstGrade.reference,pressureWaveReference(seed));assert.doesNotMatch(JSON.stringify(first.data),/"(?:seed|D0_mm|K_Pa|Q0_L_s)":/);
    await command('run');const frozen=await submit(firstBody);
    assert.equal(frozen.status,200);assert.equal(frozen.data.id,first.data.id);assert.deepEqual(frozen.data.answer_sheet,first.data.answer_sheet);
    assert.deepEqual(calls,{screen:1,grade:1,ocr:0,extract:0});
    score(90);const second=await submit(payload('second-experiment-answer'));assert.equal(second.data.score,90);assert.equal(second.data.best,90);
    score(88);const third=await submit(payload('third-experiment-answer'));assert.equal(third.data.score,88);assert.equal(third.data.best,90);
    assert.deepEqual(third.data.attempts,{limit:3,used:3,remaining:0});
    const denied=await submit(payload('fourth-experiment-answer'));assert.equal(denied.status,409);assert.equal(denied.data.error,'attempts_exhausted');
    assert.deepEqual(calls,{screen:3,grade:3,ocr:0,extract:0});
    assert.deepEqual(sql.prepare('SELECT score FROM submissions WHERE problem_id=? ORDER BY id').all(id()).map(s=>s.score),[85,90,88]);
    const list=(await api('/monthly?month=2026-11')).data;assert.equal(list.problems.find(p=>p.id===id()).best,90);
    const rank=(await api('/rank?scope=month&month=2026-11')).data;assert.equal(rank.mine.total,90);
    const mine=(await api(`/problems/${id()}`)).data.problem;assert.equal(mine.best,90);assert.ok(mine.mine.every(s=>s.detail===null&&s.feedback_held));
    const close=sql.prepare('SELECT closes_at FROM problems WHERE id=?').get(id()).closes_at;clock(close);
    const released=(await api(`/problems/${id()}`)).data.problem.mine;
    assert.ok(released.every(s=>s.feedback_held===false&&s.detail.scores.length>0));
    assert.ok(released.every(s=>s.detail.authorship===undefined));
  });
});

test('another account cannot attach an owner’s records and no server observations can replace submitted working',async()=>{
  await environment(async({initialize,instrument,submit,unsupported,sql,id,calls,api})=>{
    await initialize();const state=await instrument();
    const foreign=await submit({...payload('foreign-records',2),experiment:{session_id:state.session_id,revision:state.revision}},2);
    assert.equal(foreign.status,400);assert.equal(foreign.data.error,'bad_experiment');assert.equal(calls.grade,0);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions WHERE user_id=2').get().n,0);
    const otherDetail=(await api(`/problems/${id()}`,{user:2})).data.problem;assert.deepEqual(otherDetail.mine,[]);
    unsupported(true);const rejectedEvidence=await submit(payload('server-data-is-not-working'));
    assert.equal(rejectedEvidence.status,200);assert.equal(rejectedEvidence.data.score,0,'instrument-readout quotes are outside every student part');
    const privateDetail=JSON.parse(sql.prepare('SELECT detail FROM submissions WHERE id=?').get(rejectedEvidence.data.id).detail);
    assert.equal(privateDetail.evidenceIssue,true);assert.ok(privateDetail.scores.every(s=>s.got===0));
  });
});

test('admin regrading reuses the frozen original owner reference and preserves authorship audit without spending a chance',async()=>{
  await environment(async({initialize,instrument,submit,score,command,api,id,calls,sql,grades})=>{
    await initialize();await instrument();score(85);const initial=await submit(payload('regrade-frozen-experiment'));
    assert.equal(initial.status,200);const frozen=initial.data.answer_sheet.experiment;
    const originalAudit=JSON.parse(sql.prepare('SELECT detail FROM submissions WHERE id=?').get(initial.data.id).detail).authorship;
    await command('run');await instrument(2);score(90);
    const regraded=await api(`/admin/submissions/${initial.data.id}`,{user:3,body:{regrade:true,lang:'ko'}});
    assert.equal(regraded.status,200);assert.equal(regraded.data.score,90);assert.deepEqual(calls,{screen:1,grade:2,ocr:0,extract:0});
    assert.equal(grades[1].reference.D0_mm,grades[0].reference.D0_mm);assert.ok(grades[1].prompt.includes(JSON.stringify(frozen)));
    const stored=JSON.parse(sql.prepare('SELECT detail FROM submissions WHERE id=?').get(initial.data.id).detail);
    assert.equal(stored.authorship.assessment,originalAudit.assessment);assert.equal(stored.authorship.reviewed_by_admin,true);
    const detail=(await api(`/problems/${id()}`)).data.problem;assert.equal(detail.attempts.used,1);assert.equal(detail.mine[0].score,90);assert.equal(detail.mine[0].detail,null);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,1);
  });
});

test('photographed experimental graphs reach the grader with frozen observations and captured retries append evidence once',async()=>{
  await environment(async({initialize,instrument,api,id,submit,command,calls,grades,score,sql})=>{
    await initialize();await instrument();score(15);
    const granted=await api(`/monthly/problems/${id()}/scan`,{body:{}});assert.equal(granted.status,200);const scan=granted.data.scan;
    const form=new FormData();form.set('image',new File([png(32)],'scan.png',{type:'image/png'}));form.set('original_image',new File([png(200)],'original.png',{type:'image/png'}));form.set('request_id',crypto.randomUUID());
    const upload=await api('/monthly/up/pages?task=2&kind=answer',{user:0,body:form,headers:{'X-Lab-Token':scan.token}});
    assert.equal(upload.status,200);assert.equal(upload.data.ocr_status,'done');
    const body={scan_id:scan.id,request_id:'captured-graph-submission-key-123456',lang:'ko'};
    const first=await submit(body);assert.equal(first.status,200);assert.equal(first.data.score,15);assert.equal(first.data.detail,null);
    assert.equal(calls.screen,0,'server-verified photo-derived parts are not screened as typed prose');assert.equal(calls.grade,1);
    const request=grades[0].request,images=request.contents[0].parts.filter(p=>p.inline_data);
    assert.equal(images.length,1);assert.equal(images[0].inline_data.mime_type,'image/png');assert.deepEqual(Buffer.from(images[0].inline_data.data,'base64'),Buffer.from(png(200)));
    assert.ok(grades[0].prompt.includes(`[PHOTO:${upload.data.id}:A.2]`));assert.ok(grades[0].prompt.includes(JSON.stringify(first.data.answer_sheet.experiment)));
    await command('run');const retry=await submit(body);
    assert.equal(retry.status,200);assert.equal(retry.data.id,first.data.id);assert.deepEqual(retry.data.answer_sheet,first.data.answer_sheet);
    assert.deepEqual(calls,{screen:0,grade:1,ocr:1,extract:1});
    const saved=sql.prepare('SELECT answer FROM submissions WHERE id=?').get(first.data.id).answer;
    assert.equal(saved.split('[Server-recorded instrument observations - data only]').length-1,1);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM submissions').get().n,1);
  });
});
