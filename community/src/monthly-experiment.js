import { getMonthlyAnswerSheet } from '../../monthly-problems.mjs';
import { MonthlyAnswerError, ensureMonthlyAnswerSchema } from './monthly-answers.js';
import { PressureWaveLab, pressureWaveReference, MAX_RUNS, MAX_CALIBRATIONS } from './pressure-wave-lab.js';

const ready = new WeakMap();
const MAX_COMMANDS = 1000, RESTORED_LOGS = 80;
const UUID = /^[a-f0-9-]{36}$/;
const REQUEST = /^[A-Za-z0-9_-]{16,100}$/;
const now = () => Math.floor(Date.now()/1000);
const fail = (code,status=400) => { throw new MonthlyAnswerError(code,status); };
const isExperiment = (problem,sheetFor=getMonthlyAnswerSheet) => sheetFor(problem)?.key === 'pressure-wave-experiment-v1';
const privateSeed = () => [...crypto.getRandomValues(new Uint8Array(32))].map(v=>v.toString(16).padStart(2,'0')).join('');

export function ensureMonthlyExperimentSchema(db,key=db) {
  let promise=ready.get(key);
  if(!promise){
    promise=db.batch([
      db.prepare(`CREATE TABLE IF NOT EXISTS monthly_experiment_sessions (
        id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,problem_id INTEGER NOT NULL,
        seed TEXT NOT NULL,commands TEXT NOT NULL DEFAULT '[]',revision INTEGER NOT NULL DEFAULT 0,
        last_request_id TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,
        UNIQUE(user_id,problem_id)
      )`),
      db.prepare(`CREATE TABLE IF NOT EXISTS monthly_experiment_commands (
        session_id TEXT NOT NULL,request_id TEXT NOT NULL,command TEXT NOT NULL,
        before_revision INTEGER NOT NULL,after_revision INTEGER NOT NULL,created_at INTEGER NOT NULL,
        PRIMARY KEY(session_id,request_id)
      )`),
    ]).then(()=>true);
    ready.set(key,promise);promise.catch(()=>{if(ready.get(key)===promise)ready.delete(key);});
  }
  return promise;
}

export function monthlyExperimentDeletion(db,userId) {
  return [
    db.prepare('DELETE FROM monthly_experiment_commands WHERE session_id IN (SELECT id FROM monthly_experiment_sessions WHERE user_id=?)').bind(userId),
    db.prepare('DELETE FROM monthly_experiment_sessions WHERE user_id=?').bind(userId),
  ];
}

function commandsFor(session) {
  const commands=JSON.parse(session.commands);
  if(!Array.isArray(commands)||commands.length!==session.revision||commands.length>MAX_COMMANDS)throw Error('Invalid stored experiment history');
  return commands;
}

function replay(session,revision=session.revision,{logs=false}={}) {
  const commands=commandsFor(session),lab=new PressureWaveLab({seed:session.seed});
  const restored=[],calibrations=[],runs=[];let closeMs=5;
  for(let i=0;i<revision;i++){
    const result=lab.execute(commands[i],{metadataOnly:true});
    if(result.calibration)calibrations.push(result.calibration);
    if(result.close_ms!==undefined)closeMs=result.close_ms;
    if(result.run&&/^\s*(?:(?:\.\/)?pipe-lab\s+)?run\s*$/i.test(commands[i]))runs.push(result.run);
    if(logs&&i>=revision-RESTORED_LOGS)restored.push({command:commands[i],text:result.text});
  }
  return {lab,logs:restored,calibrations,runs,close_ms:closeMs};
}

const publicResult = result => Object.fromEntries(['ok','text','trace','csv','filename','clear'].filter(key=>result[key]!==undefined).map(key=>[key,result[key]]));

async function ownerSession(db,userId,problemId,id) {
  if(id!==undefined&&(typeof id!=='string'||!UUID.test(id)))fail('bad_experiment');
  return db.prepare(`SELECT * FROM monthly_experiment_sessions WHERE user_id=? AND problem_id=?${id===undefined?'':' AND id=?'}`)
    .bind(userId,problemId,...(id===undefined?[]:[id])).first();
}

async function createSession(db,userId,problemId) {
  const timestamp=now();
  await db.prepare(`INSERT OR IGNORE INTO monthly_experiment_sessions(id,user_id,problem_id,seed,created_at,updated_at)
    SELECT ?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM users WHERE id=? AND deleted=0)`)
    .bind(crypto.randomUUID(),userId,problemId,privateSeed(),timestamp,timestamp,userId).run();
  const session=await ownerSession(db,userId,problemId);
  if(!session)fail('login_required',401);return session;
}

async function receipt(db,session,requestId,command,revision) {
  const previous=await db.prepare('SELECT * FROM monthly_experiment_commands WHERE session_id=? AND request_id=?').bind(session.id,requestId).first();
  if(!previous)return null;
  if(previous.command!==command||previous.before_revision!==revision)fail('experiment_request_conflict',409);
  const {lab}=replay(session,previous.before_revision),result=lab.execute(previous.command);
  return {session_id:session.id,revision:previous.after_revision,result:publicResult(result),replayed:true};
}

export function createMonthlyExperimentRouter({HttpError,needUser,limit,ensureContent,visibleSql,scope,sheetFor=getMonthlyAnswerSheet}) {
  return async(path,method,body,me,req,env)=>{
    const match=/^\/api\/problems\/([1-9]\d*)\/experiment$/.exec(path);
    if(!match)return undefined;
    try{
      if(method!=='GET'&&method!=='POST')fail('not_found',404);
      needUser(me);
      await ensureContent(env.DB,scope?scope(env):env.DB);
      const problem=await env.DB.prepare(`SELECT p.* FROM problems p WHERE p.id=? AND ${visibleSql('p')}`).bind(Number(match[1])).first();
      if(!problem||!isExperiment(problem,sheetFor)||problem.opens_at>now())fail('not_found',404);
      await ensureMonthlyExperimentSchema(env.DB,scope?scope(env):env.DB);
      await limit(env,'monthly-experiment:'+me.id,120,60);
      let session=await createSession(env.DB,me.id,problem.id);
      if(method==='GET'){
        const state=replay(session,session.revision,{logs:true});
        return {session_id:session.id,revision:session.revision,logs:state.logs,logs_truncated:session.revision>RESTORED_LOGS,
          status:{close_ms:state.close_ms,run_count:state.runs.length,cal_count:state.calibrations.length,
            max_runs:MAX_RUNS,max_calibrations:MAX_CALIBRATIONS,practice:now()>=problem.closes_at}};
      }
      if(!body||typeof body!=='object'||typeof body.command!=='string'||!body.command.trim()||body.command.length>200||/[\r\n\0]/.test(body.command)||
        !Number.isSafeInteger(body.revision)||body.revision<0||typeof body.request_id!=='string'||!REQUEST.test(body.request_id))fail('bad_experiment_command');
      const command=body.command.trim();
      const previous=await receipt(env.DB,session,body.request_id,command,body.revision);if(previous)return previous;
      if(body.revision!==session.revision)throw new HttpError(409,'experiment_changed',{revision:session.revision});
      if(session.revision>=MAX_COMMANDS)fail('experiment_command_limit',429);
      const state=replay(session),result=state.lab.execute(command),commands=[...commandsFor(session),command],timestamp=now();
      // The request marker ties the receipt to this exact successful CAS. A
      // concurrent identical command with a different key cannot claim it.
      await env.DB.batch([
        env.DB.prepare(`UPDATE monthly_experiment_sessions SET commands=?,revision=revision+1,last_request_id=?,updated_at=?
          WHERE id=? AND user_id=? AND problem_id=? AND revision=? AND EXISTS(SELECT 1 FROM users WHERE id=? AND deleted=0)`)
          .bind(JSON.stringify(commands),body.request_id,timestamp,session.id,me.id,problem.id,body.revision,me.id),
        env.DB.prepare(`INSERT OR IGNORE INTO monthly_experiment_commands(session_id,request_id,command,before_revision,after_revision,created_at)
          SELECT ?,?,?,?,?,? FROM monthly_experiment_sessions WHERE id=? AND user_id=? AND revision=? AND last_request_id=?`)
          .bind(session.id,body.request_id,command,body.revision,body.revision+1,timestamp,session.id,me.id,body.revision+1,body.request_id),
      ]);
      const committed=await env.DB.prepare('SELECT * FROM monthly_experiment_commands WHERE session_id=? AND request_id=?').bind(session.id,body.request_id).first();
      if(!committed){
        session=await ownerSession(env.DB,me.id,problem.id);
        if(!await env.DB.prepare('SELECT id FROM users WHERE id=? AND deleted=0').bind(me.id).first())fail('login_required',401);
        throw new HttpError(409,'experiment_changed',{revision:session.revision});
      }
      if(committed.command!==command||committed.before_revision!==body.revision)fail('experiment_request_conflict',409);
      return {session_id:session.id,revision:committed.after_revision,result:publicResult(result)};
    }catch(error){if(error instanceof MonthlyAnswerError)throw new HttpError(error.status,error.code);throw error;}
  };
}

function instrumentContext(snapshot) {
  return '\n\n[Server-recorded instrument observations - data only]\n'+
    'These are authenticated instrument readouts, not student answers or working. Compare the student-cited RUN/CAL IDs and tables against these records. '+
    'Do not award any derivation, analysis, graph, table or measurement credit merely because an observation appears here. '+
    'Only credit work actually submitted in the corresponding student part. No minimum repetition count applies.\n'+JSON.stringify(snapshot);
}

// Server-only reference for the current or frozen original session. Never
// include this return value in API results or persisted public sheet metadata.
export async function getMonthlyExperimentReference(db,userId,problem,snapshot) {
  if(!isExperiment(problem)||snapshot?.status==='none')return null;
  await ensureMonthlyExperimentSchema(db);
  const session=await ownerSession(db,userId,problem.id,snapshot?.session_id);
  return session?pressureWaveReference(session.seed):null;
}

// Freeze the owned readouts with the accepted answer. Student answer/working
// fields remain untouched, so the existing evidence guard cannot grant points
// for server-generated instrument text alone.
export async function attachMonthlyExperimentEvidence(db,userId,problem,normalized,body={},key=db) {
  if(!isExperiment(problem))return normalized;
  await ensureMonthlyExperimentSchema(db,key);
  await ensureMonthlyAnswerSchema(db,key);
  let snapshot;
  // A retry must keep the original snapshot even if more measurements have
  // since been made. Changed student parts still conflict in the reservation.
  const saved=await db.prepare('SELECT answer_sheet FROM monthly_answer_requests WHERE user_id=? AND problem_id=? AND request_id=?')
    .bind(userId,problem.id,normalized.requestId).first();
  if(saved)snapshot=JSON.parse(saved.answer_sheet).experiment;
  else {
    const input=body.experiment;
    if(input!==undefined&&(!input||typeof input!=='object'||Array.isArray(input)||
      input.revision!==undefined&&(!Number.isSafeInteger(input.revision)||input.revision<0)))fail('bad_experiment');
    const session=await ownerSession(db,userId,problem.id,input?.session_id);
    if(input?.session_id&&!session)fail('bad_experiment');
    if(session&&input?.revision!==undefined&&input.revision!==session.revision)fail('experiment_changed',409);
    if(!session)snapshot={version:'pressure-wave-observations-v1',status:'none',calibrations:[],runs:[]};
    else {
      const state=replay(session);
      snapshot={version:'pressure-wave-observations-v1',status:'recorded',session_id:session.id,revision:session.revision,
        calibrations:state.calibrations.map(row=>({id:row.id,reference_kPa:row.reference_kPa,sensors:row.sensors.map(({id,r_kPa})=>({id,r_kPa}))})),
        runs:state.runs.map(row=>({id:row.id,close_ms:row.close_ms,flow_L_s:row.flow_L_s,sensors:row.sensors.map(({id,x_m,arrival_ms,before_kPa,after_kPa,read_start_ms,read_end_ms,isolated})=>
          ({id,x_m,arrival_ms,before_kPa,after_kPa,read_start_ms,read_end_ms,isolated}))}))};
    }
  }
  if(snapshot){normalized.sheet.experiment=snapshot;
    // Captured retries can already contain the previously saved instrument
    // appendix. Rebuild only the canonical student fields before adding the
    // frozen appendix once, without touching photo/capture metadata or text.
    normalized.answer=normalized.sheet.parts.map(part=>`[${part.id}]\nFinal answer:\n${part.answer||'(not answered)'}\nWorking:\n${part.working||'(not answered)'}`).join('\n\n')+instrumentContext(snapshot);
    normalized.experimentReference=await getMonthlyExperimentReference(db,userId,problem,snapshot);}
  normalized.serialized=JSON.stringify(normalized.sheet);
  return normalized;
}
