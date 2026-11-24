/* the Workshop's coding assistant (src/workshop-code-ai.js) against a fake model: members only, size limits, a flood guard
   and a daily quota that a failed call does not use, and an answer reduced to {code, explanation}. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createWorkshopCodeAiRouter, cleanAiOutput, codeAiMessages, CODE_AI_FREE, CODE_AI_PLAN, CODE_AI_MAX_CODE, CODE_AI_MAX_PROMPT} from './src/workshop-code-ai.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
function setup({ai,flood=Infinity}={}){
  const db=new DatabaseSync(':memory:');
  const D1={async batch(s){const out=[];for(const x of s)out.push(await x.all());return out;},prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{last_row_id:Number(r.lastInsertRowid)}};}};}};
  let t=1_800_000_000;const calls=[],hits=new Map(),seen=[];
  const AI={async run(model,input){calls.push(input);const r=ai?ai(input):'';if(r instanceof Error)throw r;return{response:r};}};
  const route=createWorkshopCodeAiRouter({HttpError:H,bad,now:()=>t,needUser:u=>{if(!u)throw new H(401,'login_required');return u;},
    limit:async(env,k,max)=>{const n=(hits.get(k)||0)+1;hits.set(k,n);seen.push([k,max]);if(n>flood)throw new H(429,'rate_limited');}});
  return {db,calls,seen,route:(p,m,b,me)=>route(p,m,b,me,null,{DB:D1,AI}),tick:s=>{t+=s;},now:()=>t};
}
const me={id:7};
const fails=async(p,code)=>assert.rejects(p,e=>e.code===code);
const good=JSON.stringify({code:'hl.run({init:()=>({x:0}),step(s,dt){s.x+=dt;},draw(s){hl.clear();hl.dot(s.x,1);}});',explanation:'공이 오른쪽으로 움직입니다.'});

test('other paths pass through; guests are refused',async()=>{
  const {route}=setup({ai:()=>good});
  assert.equal(await route('/api/workshop/storage','GET',null,me),undefined);
  await fails(route('/api/workshop/code-ai','POST',{prompt:'x'},null),'login_required');
  await fails(route('/api/workshop/code-ai','GET',null,null),'login_required');
});

test('the request is size-checked before any model call',async()=>{
  const {route,calls}=setup({ai:()=>good});
  await fails(route('/api/workshop/code-ai','POST',{prompt:''},me),'bad_prompt');
  await fails(route('/api/workshop/code-ai','POST',{prompt:'   '},me),'bad_prompt');
  await fails(route('/api/workshop/code-ai','POST',{prompt:'x'.repeat(CODE_AI_MAX_PROMPT+1)},me),'bad_prompt');
  await fails(route('/api/workshop/code-ai','POST',{prompt:{a:1}},me),'bad_prompt');
  await fails(route('/api/workshop/code-ai','POST',{prompt:'ok',code:'x'.repeat(CODE_AI_MAX_CODE+1)},me),'bad_code');
  await fails(route('/api/workshop/code-ai','POST',{prompt:'ok',code:['x']},me),'bad_code');
  await fails(route('/api/workshop/code-ai','POST',{prompt:'ok',error:5},me),'bad_error');
  await fails(route('/api/workshop/code-ai','PUT',{prompt:'ok'},me),'method_not_allowed');
  assert.equal(calls.length,0);
});

test('a member gets code and a short explanation; the prompt documents only the helper API',async()=>{
  const {route,calls}=setup({ai:()=>good});
  const r=await route('/api/workshop/code-ai','POST',{prompt:'공을 굴려 줘',code:'hl.clear();',error:'ReferenceError: y is not defined',lang:'ko'},me);
  assert.deepEqual(Object.keys(r).sort(),['code','explanation','left','plan']);
  assert.match(r.code,/hl\.run/);assert.equal(r.explanation,'공이 오른쪽으로 움직입니다.');assert.equal(r.left,CODE_AI_FREE-1);assert.equal(r.plan,'free');
  const [sys,user]=calls[0].messages;
  assert.match(sys.content,/hl\.slider\(name, min, max, value, step\?\)/);assert.match(sys.content,/hl\.rk4/);assert.match(sys.content,/Never use fetch/);assert.match(sys.content,/Korean/);
  assert.match(user.content,/Current program:[\s\S]*hl\.clear\(\);/);assert.match(user.content,/ReferenceError/);assert.match(user.content,/공을 굴려 줘/);
  assert.equal((await route('/api/workshop/code-ai','GET',null,me)).left,CODE_AI_FREE-1);
});

test('the daily quota: free members get a few, a plan more; a failed call is given back',async()=>{
  let fail=false;
  const {route,db,now,tick}=setup({ai:()=>fail?new Error('down'):good});
  for(let i=0;i<CODE_AI_FREE;i++)await route('/api/workshop/code-ai','POST',{prompt:'p'+i},me);
  await fails(route('/api/workshop/code-ai','POST',{prompt:'one more'},me),'code_ai_limit');
  db.prepare('INSERT INTO entitlements(user_id,kind,starts_at,ends_at,source,created_at) VALUES(?,?,?,?,?,?)').run(7,'plus',now()-10,null,'test',now());
  const g=await route('/api/workshop/code-ai','GET',null,me);assert.equal(g.limit,CODE_AI_PLAN);assert.equal(g.left,CODE_AI_PLAN-CODE_AI_FREE);
  fail=true;
  await fails(route('/api/workshop/code-ai','POST',{prompt:'x'},me),'ai_failed');
  assert.equal((await route('/api/workshop/code-ai','GET',null,me)).left,CODE_AI_PLAN-CODE_AI_FREE,'the failed call did not count');
  tick(86400);fail=false;
  assert.equal((await route('/api/workshop/code-ai','GET',null,me)).left,CODE_AI_PLAN,'a new day');
});

test('a reply with no program is a failure, not a charge',async()=>{
  const {route}=setup({ai:()=>'Sorry, I cannot help with that.'});
  await fails(route('/api/workshop/code-ai','POST',{prompt:'x'},me),'ai_failed');
  assert.equal((await route('/api/workshop/code-ai','GET',null,me)).left,CODE_AI_FREE);
});

test('the flood guard stops rapid requests',async()=>{
  const {route,seen}=setup({ai:()=>good,flood:2});
  await route('/api/workshop/code-ai','POST',{prompt:'a'},me);await route('/api/workshop/code-ai','POST',{prompt:'b'},me);
  await fails(route('/api/workshop/code-ai','POST',{prompt:'c'},me),'rate_limited');
  assert.deepEqual(seen[0],['code-ai-flood:7',6],'six a minute per member');
});

test('the answer is reduced to code and an explanation; markdown and extra fields are dropped',()=>{
  const a=cleanAiOutput('```json\n'+JSON.stringify({code:'```js\nhl.clear();\n```',explanation:'Done. ```js\nalert(1)\n```',token:'x',html:'<img src=x onerror=1>'})+'\n```');
  assert.deepEqual(a,{code:'hl.clear();\n',explanation:'Done.'});
  const b=cleanAiOutput('Here is the program:\n```javascript\nhl.loop(dt=>{});\n```\nIt loops.');
  assert.equal(b.code,'hl.loop(dt=>{});\n');assert.match(b.explanation,/Here is the program:[\s\S]*It loops\./);assert.doesNotMatch(b.explanation,/```/);
  assert.equal(cleanAiOutput('<think>plan</think>no code here'),null);
  assert.equal(cleanAiOutput(JSON.stringify({code:'   ',explanation:'x'})),null);
  assert.equal(cleanAiOutput(JSON.stringify({code:'x'.repeat(CODE_AI_MAX_CODE+5)})),null);
  assert.equal(cleanAiOutput(JSON.stringify({code:'a',explanation:'e'.repeat(5000)})).explanation.length,1500);
  assert.match(codeAiMessages({prompt:'p',code:'',lang:'en'})[1].content,/no program yet/);
});
