import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { createMonthlyExperimentRouter, attachMonthlyExperimentEvidence, getMonthlyExperimentReference,
  ensureMonthlyExperimentSchema, monthlyExperimentDeletion } from './src/monthly-experiment.js';
import { PressureWaveLab, pressureWaveReference, pressureWaveParameters, MAX_RUNS, MAX_CALIBRATIONS } from './src/pressure-wave-lab.js';
import { getMonthlyAnswerSheet } from '../monthly-problems.mjs';

const NOW=Date.parse('2026-11-02T12:00:00+09:00')/1000;
const problem={id:91,week:'2026-11',no:5,title_ko:'압력파를 이용한 관의 내부 지름 측정',source:'HaslaLab · pressure-wave-experiment-v1',opens_at:NOW-100,closes_at:NOW+1000,points:100};
class HttpError extends Error {constructor(status,code,extra={}){super(code);this.status=status;this.code=code;Object.assign(this,extra);}}

async function environment(run){
  const sql=new DatabaseSync(':memory:');
  sql.exec(`CREATE TABLE users(id INTEGER PRIMARY KEY,deleted INTEGER NOT NULL DEFAULT 0);
    INSERT INTO users(id) VALUES(1),(2);
    CREATE TABLE problems(id INTEGER PRIMARY KEY,week TEXT,no INTEGER,title_ko TEXT,source TEXT,opens_at INTEGER,closes_at INTEGER,points INTEGER);`);
  sql.prepare('INSERT INTO problems VALUES(?,?,?,?,?,?,?,?)').run(...Object.values(problem));
  let beforeBatch=async()=>{};
  const DB={prepare(query){const st=sql.prepare(query),make=args=>({query,bind:(...values)=>make(values),
    async first(){return st.get(...args)||null;},async all(){return{results:st.all(...args)};},async run(){return this.executeSync();},
    executeSync(){if(st.columns().length)return{results:st.all(...args)};const result=st.run(...args);return{results:[],meta:{changes:result.changes,last_row_id:Number(result.lastInsertRowid)}};}});return make([]);},
    async batch(statements){if(statements.some(st=>st.query.includes('UPDATE monthly_experiment_sessions'))){const hook=beforeBatch;beforeBatch=async()=>{};await hook();}
      sql.exec('BEGIN');try{const result=statements.map(st=>st.executeSync());sql.exec('COMMIT');return result;}catch(error){sql.exec('ROLLBACK');throw error;}}};
  const deps={HttpError,needUser:me=>{if(!me)throw new HttpError(401,'login_required');return me;},limit:async()=>{},ensureContent:async()=>{},visibleSql:()=> '1=1',scope:env=>env.DB};
  let router=createMonthlyExperimentRouter(deps);
  const env={DB},savedNow=Date.now;let clock=NOW;Date.now=()=>clock*1000;
  const api=async({method='GET',body,user=1,id=91,path}={})=>{
    try{return{status:200,data:await router(path||`/api/problems/${id}/experiment`,method,body,user?{id:user}:null,new Request('https://monthly.test/'),env)};}
    catch(error){if(error instanceof HttpError)return{status:error.status,error:error.code,revision:error.revision};throw error;}
  };
  const command=(command,revision,request_id=crypto.randomUUID(),user=1)=>api({method:'POST',body:{command,revision,request_id},user});
  const normalized=requestId=>{const parts=[{id:'A.2',answer:'c=measured slope inverse',working:'I used RUN 1 and recorded the sensor table.'}];return{requestId,sheet:{version:getMonthlyAnswerSheet(problem).version,parts},answer:'Student final answer and working',serialized:''};};
  try{return await run({sql,DB,api,command,normalized,reset:()=>{router=createMonthlyExperimentRouter(deps);},clock:value=>{clock=value;},beforeBatch:fn=>{beforeBatch=fn;}});}
  finally{Date.now=savedNow;sql.close();}
}

test('instrument routes require the owning account and a published experiment identity',async()=>{
  await environment(async({api,sql})=>{
    assert.equal((await api({user:0})).status,401);
    assert.equal((await api({id:4})).status,404);
    assert.equal((await api({method:'DELETE'})).status,404);
    const a=(await api()).data,b=(await api({user:2})).data;
    assert.notEqual(a.session_id,b.session_id);assert.equal(a.revision,0);assert.deepEqual(a.logs,[]);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_experiment_sessions').get().n,2);
    const seed=sql.prepare('SELECT seed FROM monthly_experiment_sessions WHERE user_id=1').get().seed;
    assert.ok(!JSON.stringify(a).includes(seed));assert.doesNotMatch(JSON.stringify(a),/"(?:seed|D0_mm|K_Pa|a|b|Q0_L_s)":/);
    assert.equal((await api({path:'/api/unrelated'})).data,undefined);
  });
});

test('records, selected settings and original traces survive a new router and later observations',async()=>{
  await environment(async({api,command,reset})=>{
    await api();
    assert.equal((await command('cal 0',0)).status,200);
    await command('set close 2',1);await command('run',2);
    const trace=(await command('trace S4 1',3)).data.result;
    assert.equal(trace.trace.points.length,1631);
    reset();const restored=(await api()).data;
    assert.equal(restored.revision,4);assert.equal(restored.status.close_ms,2);assert.equal(restored.status.run_count,1);assert.equal(restored.status.cal_count,1);
    assert.equal(restored.logs[2].command,'run');assert.match(restored.logs[2].text,/RUN 1/);
    await command('set close 50',4);await command('run',5);
    const old=(await command('trace S4 1',6)).data.result;
    assert.deepEqual(old,trace);
    const csv=(await command('export 1',7)).data.result;
    const rows=csv.csv.trim().split('\r\n').map(line=>line.split(','));
    assert.equal(rows.length,1632);assert.equal(Number(rows[21][8]),trace.trace.points[20].r_kPa);
    const other=(await command('read 1',0,crypto.randomUUID(),2)).data.result;
    assert.equal(other.ok,false,'another account cannot resolve this owner’s RUN number');
  });
});

test('idempotent retries and competing CAS commands never acquire a RUN twice',async()=>{
  await environment(async({api,command,sql})=>{
    await api();const key=crypto.randomUUID();
    const first=await command('run',0,key),again=await command('run',0,key);
    assert.equal(first.status,200);assert.equal(again.status,200);assert.deepEqual(again.data.result,first.data.result);assert.equal(again.data.replayed,true);
    assert.equal((await command('cal 0',0,key)).error,'experiment_request_conflict');
    const competing=await Promise.all([command('run',1),command('run',1)]);
    assert.deepEqual(competing.map(r=>r.status).sort(),[200,409]);
    assert.equal((await api()).data.status.run_count,2);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_experiment_commands').get().n,2);
    const current=(await api()).data.revision,same=crypto.randomUUID();
    const twin=await Promise.all([command('run',current,same),command('run',current,same)]);
    assert.ok(twin.every(row=>row.status===200));assert.deepEqual(twin[0].data.result,twin[1].data.result);
    assert.equal((await api()).data.status.run_count,3);
  });
});

test('command bounds and deleted-account races cannot mutate owned instrument state',async()=>{
  await environment(async({api,command,sql,beforeBatch})=>{
    await api();
    for(const body of [{command:'run',revision:0},{command:'run\nrun',revision:0,request_id:crypto.randomUUID()},
      {command:'x'.repeat(201),revision:0,request_id:crypto.randomUUID()},{command:'run',revision:-1,request_id:crypto.randomUUID()},
      {command:'run',revision:0,request_id:1234567890123456},
      {command:'run',revision:Infinity,request_id:crypto.randomUUID()}])assert.equal((await api({method:'POST',body})).status,400);
    assert.equal((await api()).data.revision,0);
    assert.equal((await command('run extra',0)).data.result.ok,false);
    assert.equal((await api()).data.status.run_count,0);
    beforeBatch(async()=>{sql.prepare('UPDATE users SET deleted=1 WHERE id=1').run();});
    assert.equal((await command('run',1)).status,401);
    assert.equal(sql.prepare('SELECT revision FROM monthly_experiment_sessions WHERE user_id=1').get().revision,1);
  });
});

test('deadline practice keeps the original records and does not reset experiment identity',async()=>{
  await environment(async({api,command,clock})=>{
    const before=(await api()).data;await command('run',0);
    clock(problem.closes_at+1);const after=(await api()).data;
    assert.equal(after.session_id,before.session_id);assert.equal(after.status.practice,true);
    assert.equal((await command('run',1)).data.result.ok,true);assert.equal((await api()).data.status.run_count,2);
  });
});

test('frozen owned observations accompany grading without filling or changing student answer fields',async()=>{
  await environment(async({api,command,DB,sql,normalized})=>{
    await api();await command('cal 0',0);await command('cal 200',1);await command('set close 2',2);await command('run',3);
    const before=(await api()).data,normal=normalized('submission-key-123456');
    const studentParts=JSON.stringify(normal.sheet.parts);
    await attachMonthlyExperimentEvidence(DB,1,problem,normal,{experiment:{session_id:before.session_id,revision:before.revision,calibrations:['forged']}});
    assert.equal(JSON.stringify(normal.sheet.parts),studentParts);assert.equal(normal.sheet.experiment.calibrations.length,2);assert.equal(normal.sheet.experiment.runs.length,1);
    assert.match(normal.answer,/not student answers or working/);assert.match(normal.answer,/Only credit work actually submitted/);
    const seed=sql.prepare('SELECT seed FROM monthly_experiment_sessions WHERE user_id=1').get().seed;
    assert.deepEqual(normal.experimentReference,pressureWaveReference(seed));
    assert.ok(!normal.serialized.includes(seed));assert.doesNotMatch(normal.serialized,/"(?:seed|D0_mm|K_Pa|Q0_L_s)":/);
    const frozen=normal.serialized;
    sql.prepare(`INSERT INTO monthly_answer_requests(user_id,problem_id,request_id,answer_sheet,answer_text,via_ocr,created_at) VALUES(1,91,?,?,?,?,?)`)
      .run(normal.requestId,normal.serialized,normal.answer,0,NOW);
    await command('run',4);
    const retry=normalized(normal.requestId);await attachMonthlyExperimentEvidence(DB,1,problem,retry,{experiment:{revision:5}});
    assert.equal(retry.serialized,frozen);assert.equal(retry.sheet.experiment.runs.length,1);assert.equal(retry.answer,normal.answer);
    const capturedRetry={...normalized(normal.requestId),sheet:JSON.parse(frozen),answer:normal.answer,viaOcr:1,photographedPartIds:['A.2']};
    await attachMonthlyExperimentEvidence(DB,1,problem,capturedRetry,{experiment:{revision:5}});
    assert.equal(capturedRetry.serialized,frozen);assert.equal(capturedRetry.answer,normal.answer);
    assert.equal(capturedRetry.answer.split('[Server-recorded instrument observations - data only]').length-1,1);
    assert.equal(capturedRetry.viaOcr,1);assert.deepEqual(capturedRetry.photographedPartIds,['A.2']);
    await attachMonthlyExperimentEvidence(DB,1,problem,capturedRetry);
    assert.equal(capturedRetry.answer,normal.answer,'calling attachment twice still appends only one frozen context');
    assert.deepEqual(await getMonthlyExperimentReference(DB,1,problem,retry.sheet.experiment),normal.experimentReference);
    const unowned=normalized('foreign-session-key');
    await assert.rejects(attachMonthlyExperimentEvidence(DB,2,problem,unowned,{experiment:{session_id:before.session_id}}),e=>e.code==='bad_experiment');
    const stale=normalized('stale-session-key');
    await assert.rejects(attachMonthlyExperimentEvidence(DB,1,problem,stale,{experiment:{revision:3}}),e=>e.code==='experiment_changed');
  });
});

test('a theory-only partial answer can be saved without creating an instrument session',async()=>{
  await environment(async({DB,sql,normalized})=>{
    const normal=normalized('theory-only-key');await attachMonthlyExperimentEvidence(DB,1,problem,normal);
    assert.equal(normal.sheet.experiment.status,'none');assert.equal(normal.experimentReference,null);
    assert.deepEqual(normal.sheet.experiment.runs,[]);assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_experiment_sessions').get().n,0);
  });
});

test('account deletion removes private experiment histories and idempotency receipts together',async()=>{
  await environment(async({DB,api,command,sql})=>{
    await api();await command('run',0);await api({user:2});
    await DB.batch(monthlyExperimentDeletion(DB,1));
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_experiment_sessions WHERE user_id=1').get().n,0);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_experiment_commands').get().n,0);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_experiment_sessions WHERE user_id=2').get().n,1);
  });
});

test('instrument storage caps are resource bounds, never minimum acquisition counts',()=>{
  const lab=new PressureWaveLab({seed:'resource-limits'});
  for(let i=0;i<MAX_CALIBRATIONS;i++)assert.equal(lab.execute('cal 0').calibration.id,i+1);
  assert.equal(lab.execute('cal 0').ok,false);assert.equal(lab.execute('cal history').calibrationHistory.length,MAX_CALIBRATIONS);
  for(let i=0;i<MAX_RUNS;i++)assert.equal(lab.execute('run').run.id,i+1);
  assert.equal(lab.execute('run').ok,false);assert.equal(lab.execute('read 1').run.id,1);
  assert.equal(lab.execute('stats 5 1').statistics[0].n,1);assert.equal(lab.execute('stats 5 1').statistics[0].flow_L_s.s,null);
  assert.ok(!Object.hasOwn(lab.execute('stats 5 1').statistics[0],'minimum'));
});

const mean=xs=>xs.reduce((a,b)=>a+b,0)/xs.length;
function linear(x,y){const xm=mean(x),ym=mean(y),s=x.reduce((a,v,i)=>a+(v-xm)*(y[i]-ym),0)/x.reduce((a,v)=>a+(v-xm)**2,0);return[s,ym-s*xm];}
function quadratic(x,y){const m=Array.from({length:3},(_,r)=>[...Array.from({length:3},(_,c)=>x.reduce((s,v)=>s+v**(r+c),0)),x.reduce((s,v,i)=>s+y[i]*v**r,0)]);
  for(let i=0;i<3;i++){const z=m[i][i];for(let k=i;k<4;k++)m[i][k]/=z;for(let j=0;j<3;j++)if(j!==i){const z=m[j][i];for(let k=i;k<4;k++)m[j][k]-=z*m[i][k];}}return m.map(r=>r[3]);}

test('100 private models remain identifiable from one calibrated 2 ms observation and have valid closure choices',()=>{
  const choices=new Set();
  for(let i=0;i<100;i++){
    const seed='private-model-'+i,p=pressureWaveParameters(seed),ref=pressureWaveReference(seed),lab=new PressureWaveLab({seed});
    assert.ok(p.D0>=.048&&p.D0<=.054&&p.a>=.06&&p.a<=.10&&p.b>=.025&&p.b<=.055&&p.K>=2.05e9&&p.K<=2.30e9&&p.Q>=.000135&&p.Q<=.000165);
    const zero=lab.execute('cal 0').calibration.sensors,span=lab.execute('cal 200').calibration.sensors,gain=span.map((s,j)=>(s.r_kPa-zero[j].r_kPa)/200);
    lab.execute('set close 2');const run=lab.execute('run').run,x=run.sensors.map(s=>s.x_m),t=run.sensors.map(s=>s.arrival_ms/1000),[slope]=linear(x,t),c=1/slope;
    const P=run.sensors.map((s,j)=>(s.after_kPa-s.before_kPa)/gain[j]*1000),Q=run.flow_L_s/1000,d0=Math.sqrt(4*1000*c*Q/(Math.PI*P[0])),D=P.map(v=>d0*P[0]/v);
    const idx=[0,2,4,6],coef=quadratic(idx.map(j=>x[j]/120),idx.map(j=>D[j])),[d,b1,b2]=coef,a=b1/d,b=b2/d;
    const u=Array.from({length:121},(_,j)=>j/120),rms=Math.sqrt(mean(u.map(v=>((d*(1+a*v+b*v*v))/(p.D0*(1+p.a*v+p.b*v*v))-1)**2)));
    assert.ok(Math.abs(c/ref.c_m_s-1)<.01);assert.ok(Math.abs(c*c/(ref.c_m_s**2)-1)<.03);assert.ok(rms<.015);assert.ok(Math.abs(a-p.a)<.02&&Math.abs(b-p.b)<.02);
    assert.ok([2,5].includes(ref.selected_tau_ms));choices.add(ref.selected_tau_ms);
    assert.ok(2<ref.tau_model_max_ms&&2<ref.tau_echo_max_ms,'initial 2 ms observation always obeys both approximations');
    assert.ok(ref.selected_tau_ms<=ref.tau_model_max_ms&&ref.selected_tau_ms<ref.tau_echo_max_ms);
    const gradientGrid=Array.from({length:101},(_,j)=>{const v=j/100;return 2*(p.a+2*p.b*v)/(120*(1+p.a*v+p.b*v*v));});
    assert.ok(gradientGrid.every((value,j)=>j===0||value>gradientGrid[j-1]));
    assert.ok(Math.abs(Math.max(...gradientGrid)-ref.max_dlnA_dx_per_m)<1e-14);
    assert.ok(Math.abs(ref.D60_mm-p.D0*(1+p.a/2+p.b/4)*1000)<1e-10);
    assert.ok(Math.abs(ref.D120_mm-p.D0*(1+p.a+p.b)*1000)<1e-10);
  }
  assert.deepEqual([...choices].sort(),[2,5]);
});

test('on-demand regenerated traces and metadata replay preserve exact stored window means and future noise',()=>{
  const a=new PressureWaveLab({seed:'checkpoints'}),b=new PressureWaveLab({seed:'checkpoints'});
  for(const cmd of ['cal 0','set close 2','run','run','set close 50','run'])assert.deepEqual(a.execute(cmd),b.execute(cmd));
  const before=a.execute('trace S4 1');a.execute('export 1');a.execute('trace S0 3',{metadataOnly:true});a.execute('export 2',{metadataOnly:true});
  assert.deepEqual(a.execute('cal 200'),b.execute('cal 200'),'regenerating an old trace never advances the present random state');
  assert.deepEqual(a.execute('trace S4 1'),before);
  const summary=a.execute('read 1').run.sensors[4],points=before.trace.points;
  const window=points.filter(p=>p.t_ms>=summary.read_start_ms&&p.t_ms<summary.read_end_ms);
  const quantise=value=>Math.round((value+Number.EPSILON)*10)/10;
  assert.equal(summary.after_kPa,quantise(mean(window.map(p=>p.r_kPa))));
  const csv=a.execute('export 1').csv.trim().split('\r\n').slice(1).map(line=>line.split(',').map(Number));
  assert.equal(summary.after_kPa,quantise(mean(csv.filter(row=>row[3]>=summary.read_start_ms&&row[3]<summary.read_end_ms).map(row=>row[8]))));
});

test('a fast wave reflects its returning rarefaction at the closed valve with the same negative pressure sign',()=>{
  const parameters={D0:.05,a:.08,b:.04,K:2.30e9,Q:.00015},lab=new PressureWaveLab({seed:'high-K-second-echo',parameters});
  const c=Math.sqrt(parameters.K/1000),returnAtValve=.30+240000/c;
  assert.ok(returnAtValve<160&&returnAtValve>158,'the first return reaches the valve inside the recorded tail');
  assert.ok(.30+255000/c>160,'the reflected return cannot yet reach S1');
  lab.execute('set close 2');const run=lab.execute('run').run;
  const s0=lab.execute('trace S0 1').trace.points,at=t=>s0.find(p=>p.t_ms===t).r_kPa;
  const displayedAmplitude=run.sensors[0].after_kPa-run.sensors[0].before_kPa;
  // Incoming rarefaction and its +1-pressure-coefficient closed-end echo
  // overlap at S0. A 0.5 ms interval therefore drops 2*(0.5/2)*P.
  assert.ok(Math.abs((at(159)-at(159.5))/displayedAmplitude-.5)<.003);
  assert.ok(at(160)<run.sensors[0].before_kPa-20,'the double rarefaction has crossed below the initial pressure');
  const s1=lab.execute('trace S1 1').trace.points;
  assert.ok(Math.abs(s1.at(-1).r_kPa-run.sensors[1].before_kPa)<.3,'S1 has only the reservoir return before its valve echo arrives');
});
