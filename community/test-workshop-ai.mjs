/* the Workshop's AI makers (src/workshop-ai.js) against fake providers and a D1 on node:sqlite: members only, size
   limits, a daily quota per member and one for everyone (given back when no usable answer came), the cheapest configured
   provider with at most one more try, scenes reduced to what validateScene keeps, problems checked by our arithmetic
   (a wrong answer flagged, a multiple choice with exactly one right choice), and never the model's own text. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {createWorkshopAiRouter, checkProblem, checkTemplate, leadNumber, plan, sceneFromObjects, WORKSHOP_AI_FREE, WORKSHOP_AI_PLAN, AI_MAX_PROMPT, AI_MAX_SCENE} from './src/workshop-ai.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
const KEYS={GEMINI_API_KEY:'g',OPENAI_API_KEY:'o'};
function setup({answer,keys=KEYS,flood=Infinity,vars={}}={}){
  const db=new DatabaseSync(':memory:');
  const D1={async batch(s){const out=[];for(const x of s)out.push(await x.all());return out;},prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{changes:r.changes}};}};}};
  let t=1_800_000_000;const calls=[],hits=new Map();
  const call=async(env,o)=>{calls.push(o);const r=answer(o,calls.length);if(r instanceof Error)throw r;return{raw:r,usage:{input_tokens:1000,output_tokens:500,pricing:{total_usd:0.001}}};};
  const route=createWorkshopAiRouter({HttpError:H,bad,now:()=>t,call,needUser:u=>{if(!u)throw new H(401,'login_required');return u;},
    limit:async(env,k,max)=>{const n=(hits.get(k)||0)+1;hits.set(k,n);if(n>flood)throw new H(429,'rate_limited');}});
  const env={DB:D1,...keys,...vars};
  return {db,calls,env,route:(p,m,b,me)=>route(p,m,b,me,null,env),tick:s=>{t+=s;}};
}
const me={id:7},you={id:8};
const fails=async(p,code,status)=>assert.rejects(p,e=>e.code===code&&(status==null||e.status===status));
const SCENE='/api/workshop/ai/scene',PROB='/api/workshop/ai/problem',MODELS='/api/workshop/ai/models';
const goodScene={objects:[{id:'f',type:'floor',x:0,y:0,w:5},{id:'b',type:'block',on:'f',at:1,w:0.5,h:0.4,mass:2,label:'m'},{id:'x',type:'script',code:'alert(1)'},{id:'z',type:'block',x:'NaN',w:-3}],notes:['마찰은 없다고 두었습니다.','<b>x</b>'],secret:'raw text'};
const prob=(over={})=>({stem:'질량 $2\\ \\mathrm{kg}$인 물체를 높이 $1.5\\ \\mathrm{m}$에서 놓았다. 바닥에 닿기 직전 속력은?',answer:'5.42 m/s',answer_value:5.42,unit:'m/s',calc:'sqrt(2*9.8*1.5)',solution:'$v=\\sqrt{2gh}$',...over});

test('other paths pass through; guests are refused; the model list needs no login and shows no key',async()=>{
  const {route}=setup({answer:()=>goodScene});
  assert.equal(await route('/api/workshop/code-ai','POST',{},me),undefined);
  await fails(route(SCENE,'POST',{prompt:'x'},null),'login_required',401);
  await fails(route(PROB,'POST',{prompt:'x'},null),'login_required',401);
  const m=await route(MODELS,'GET',null,null);
  assert.deepEqual(m.models.map(x=>[x.id,x.configured]),[['gemini',true],['gpt',true],['claude',false]]);
  assert.ok(!JSON.stringify(m).includes('"g"')&&!JSON.stringify(m).match(/KEY/),'no key names or values');
  assert.equal(m.default,'gpt','the cheapest configured by the price table');
  const mine=await route(MODELS,'GET',null,me);assert.equal(mine.left,WORKSHOP_AI_FREE);assert.equal(mine.plan,'free');
});

test('requests are size-checked before any model call',async()=>{
  const {route,calls}=setup({answer:()=>goodScene});
  await fails(route(SCENE,'POST',{prompt:''},me),'bad_prompt');
  await fails(route(SCENE,'POST',{prompt:'x'.repeat(AI_MAX_PROMPT+1)},me),'bad_prompt');
  await fails(route(SCENE,'POST',{prompt:{a:1}},me),'bad_prompt');
  await fails(route(SCENE,'POST',{prompt:'ok',scene:[1]},me),'bad_scene');
  await fails(route(SCENE,'POST',{prompt:'ok',scene:{objects:[],pad:'x'.repeat(AI_MAX_SCENE)}},me),'scene_too_large',413);
  await fails(route(SCENE,'POST',{prompt:'ok',model:'llama'},me),'bad_model');
  await fails(route(PROB,'POST',{prompt:'ok',count:6},me),'bad_count');
  await fails(route(PROB,'POST',{prompt:'ok',count:0},me),'bad_count');
  await fails(route(PROB,'POST',{prompt:'ok',format:'essay'},me),'bad_format');
  await fails(route(PROB,'POST',{prompt:'ok',level:'impossible'},me),'bad_level');
  await fails(route(PROB,'GET',null,me),'method_not_allowed',405);
  assert.equal(calls.length,0);
});

test('a scene comes back validated: unknown types and broken objects are dropped, no raw model text',async()=>{
  const {route,calls,db}=setup({answer:()=>goodScene});
  const r=await route(SCENE,'POST',{prompt:'마찰 없는 바닥 위의 상자',lang:'ko'},me);
  assert.deepEqual(Object.keys(r).sort(),['left','model','notes','scene']);
  assert.deepEqual(r.scene.objects.map(o=>o.type).sort(),['block','floor']);
  assert.ok(!JSON.stringify(r).includes('alert')&&!JSON.stringify(r).includes('raw text')&&!JSON.stringify(r).includes('<b>'));
  assert.ok(r.notes.length<=5&&r.notes.some(n=>/뺐습니다/.test(n)));
  assert.equal(r.left,WORKSHOP_AI_FREE-1);assert.equal(r.model,'gpt');
  assert.equal(calls[0].provider,'openai');assert.equal(calls[0].model,'gpt-6-luna');assert.ok(calls[0].maxTokens<=6000);
  assert.match(calls[0].policy,/incline \{x,y,angle,length/,'the editor schema is in the prompt');
  const log=db.prepare('SELECT * FROM workshop_ai_calls').all();
  assert.equal(log.length,1);assert.equal(log[0].ok,1);assert.equal(log[0].tokens_in,1000);assert.equal(log[0].cost_usd,0.001);
});

test('the current scene is sent cleaned; its own types may come back',async()=>{
  const {route,calls}=setup({answer:()=>({objects:[{id:'p',type:'gpoint',x:1,y:1},{id:'f',type:'floor',x:0,y:0,w:4}]})});
  const r=await route(SCENE,'POST',{prompt:'점 하나 더',scene:{format:'haslalab-scene',version:2,style:'olympiad',objects:[{id:'p',type:'gpoint',x:1,y:1},{id:'bad',type:'nope'}]}},me);
  assert.deepEqual(r.scene.objects.map(o=>o.type).sort(),['floor','gpoint']);assert.equal(r.scene.style,'olympiad');
  assert.ok(!JSON.stringify(calls[0].input).includes('nope'));
});

test('the daily quota per member, given back when the call fails or nothing usable came',async()=>{
  let mode='ok';
  const {route,db}=setup({answer:o=>mode==='err'?Object.assign(new Error('x'),{code:'vision_provider_failed'}):mode==='junk'?{objects:[{type:'script'}]}:o.schema.properties.problems?{problems:[prob()]}:goodScene});
  mode='err';await fails(route(SCENE,'POST',{prompt:'a'},me),'ai_failed',503);
  mode='junk';await fails(route(SCENE,'POST',{prompt:'a'},me),'ai_unusable',422);
  assert.equal(db.prepare("SELECT n FROM ai_usage_daily WHERE user_id=7 AND kind='ws-ai'").get().n,0,'both given back');
  assert.equal(db.prepare("SELECT n FROM ai_usage_daily WHERE user_id=0 AND kind='ws-ai-global'").get().n,2,'the global count keeps every model call, failed or not');
  mode='ok';
  for(let i=0;i<WORKSHOP_AI_FREE;i++)await route(i%2?SCENE:PROB,'POST',{prompt:'a'},me);
  await fails(route(PROB,'POST',{prompt:'a'},me),'ai_limit',429);
  assert.ok(await route(SCENE,'POST',{prompt:'a'},you),'another member has their own');
});

test('a plan gives more a day',async()=>{
  const {route,db}=setup({answer:()=>goodScene});
  db.exec("CREATE TABLE IF NOT EXISTS entitlements (user_id INTEGER, kind TEXT, starts_at INTEGER, ends_at INTEGER)");
  db.prepare("INSERT INTO entitlements(user_id,kind,starts_at,ends_at) VALUES(7,'teacher',0,NULL)").run();
  assert.equal((await route(MODELS,'GET',null,me)).limit,WORKSHOP_AI_PLAN);
});

test('the global daily cap fails closed with busy and takes nothing from the member',async()=>{
  const {route,db,calls}=setup({answer:()=>goodScene,vars:{WORKSHOP_AI_DAILY_CAP:'2'}});
  await route(SCENE,'POST',{prompt:'a'},me);await route(SCENE,'POST',{prompt:'a'},you);
  await fails(route(SCENE,'POST',{prompt:'a'},{id:9}),'busy',503);
  assert.equal(db.prepare("SELECT n FROM ai_usage_daily WHERE user_id=9 AND kind='ws-ai'").get().n,0);
  assert.equal(calls.length,2);
});

test('auto tries one more configured provider when the first fails, never more; a named one is not retried',async()=>{
  const {route,calls}=setup({answer:(o,n)=>n<=10&&o.provider==='openai'?new Error('down'):goodScene});
  const r=await route(SCENE,'POST',{prompt:'a'},me);
  assert.deepEqual(calls.map(c=>c.provider),['openai','gemini']);assert.equal(r.model,'gemini');
  calls.length=0;await fails(route(SCENE,'POST',{prompt:'a',model:'gpt'},me),'ai_failed');
  assert.equal(calls.length,1);
  const all=setup({answer:()=>new Error('down'),keys:{GEMINI_API_KEY:'g',OPENAI_API_KEY:'o',ANTHROPIC_API_KEY:'a'}});
  await fails(all.route(SCENE,'POST',{prompt:'a'},me),'ai_failed');assert.equal(all.calls.length,2,'at most one retry');
});

test('a provider without a key is reported not configured, before any quota is taken',async()=>{
  const {route,db,calls}=setup({answer:()=>goodScene});
  await fails(route(PROB,'POST',{prompt:'a',model:'claude'},me),'not_configured',503);
  const none=setup({answer:()=>goodScene,keys:{}});
  await fails(none.route(SCENE,'POST',{prompt:'a'},me),'not_configured',503);
  assert.equal(calls.length+none.calls.length,0);
  assert.equal(db.prepare("SELECT COUNT(*) n FROM sqlite_master WHERE name='ai_usage_daily'").get().n,0);
  assert.deepEqual(plan({ANTHROPIC_API_KEY:'a'},'claude'),{order:['claude']});
});

test('problems: a right answer is verified, a wrong one flagged, nothing but the checked fields returned',async()=>{
  const {route,calls}=setup({answer:()=>({problems:[prob(),prob({answer:'7.0 m/s',answer_value:7})],notes:['g = 9.8로 두었습니다.'],thinking:'raw'})});
  const r=await route(PROB,'POST',{prompt:'자유 낙하 문제',count:2,format:'short',lang:'ko'},me);
  assert.equal(r.problems.length,2);
  assert.equal(r.problems[0].check.status,'verified');assert.equal(r.problems[1].check.status,'mismatch');assert.equal(r.problems[1].check.calc,'differs');
  assert.deepEqual(Object.keys(r.problems[0]).sort(),['answer','check','solution','stem','unit']);
  assert.ok(!JSON.stringify(r).includes('raw'));
  assert.match(calls[0].policy,/"calc"/);assert.ok(calls[0].maxTokens<=9000);
  assert.ok(!/Figure editor schema/.test(calls[0].policy),'no figure schema unless asked');
});

test('multiple choice: exactly one right choice; a wrong key is corrected and flagged; two right or none are dropped',()=>{
  const ok=checkProblem(prob({choices:['2.71 m/s','5.42 m/s','7.67 m/s','10.8 m/s','29.4 m/s'],correct:1}),{format:'mc'}).problem;
  assert.equal(ok.correct,1);assert.equal(ok.check.mc,'ok');assert.equal(ok.check.status,'verified');
  const fixed=checkProblem(prob({choices:['2.71','5.42','7.67','10.8','29.4'],correct:3}),{format:'mc'}).problem;
  assert.equal(fixed.correct,1);assert.equal(fixed.check.mc,'fixed');assert.equal(fixed.check.status,'mismatch');
  assert.equal(checkProblem(prob({choices:['5.42','5.42','7.67','10.8'],correct:0}),{format:'mc'}).drop,'mc_choices','the same text twice');
  assert.equal(checkProblem(prob({choices:['5.42','5.42 m/s','7.67','10.8'],correct:0}),{format:'mc'}).drop,'mc_two_correct','the same value twice');
  assert.equal(checkProblem(prob({choices:['5.42','5.43','7.67','10.8'],correct:0}),{format:'mc'}).drop,'mc_two_correct');
  assert.equal(checkProblem(prob({choices:['1','2','3','4'],correct:0}),{format:'mc'}).drop,'mc_no_correct');
  const words=checkProblem(prob({choices:['$2v_0$','$v_0$','$4v_0$','$v_0/2$'],correct:2,answer:'$4v_0$',answer_value:undefined,calc:''}),{format:'mc'}).problem;
  assert.equal(words.check.mc,'unchecked');assert.equal(words.check.status,'unverified');
  assert.equal(checkProblem(prob({choices:['a','b','c'],correct:9,answer:'b',answer_value:undefined,calc:''}),{format:'mc'}).drop,'mc_no_correct');
});

test('templates in the problem maker format are kept only when their formula gives the answer',()=>{
  const t={text:'높이 {h} m에서 놓은 공의 속력은?',formula:'sqrt(2 g h)',unit:'m/s',params:[{name:'h',value:1.5,min:1,max:10,step:0.5}],constants:[{name:'g',value:9.8}]};
  const r=checkTemplate(t,5.42);
  assert.equal(r.ok,true);assert.deepEqual(r.template,{template:t.text,params:{h:{min:1,max:10,step:0.5}},formula:'sqrt(2 g h)',unit:'m/s',constants:'g = 9.8'});
  assert.equal(checkTemplate({...t,formula:'2 g h'},5.42).template,null,'formula gives another answer');
  assert.equal(checkTemplate({...t,formula:'sqrt(2 g k)'},5.42).template,null,'unknown name');
  assert.equal(checkTemplate({...t,params:[{name:'h',value:1.5,min:5,max:1,step:1}]},5.42).template,null,'bad range');
  const p=checkProblem(prob({template:t}),{format:'short'}).problem;assert.equal(p.check.template,'ok');assert.equal(p.template.formula,'sqrt(2 g h)');
});

test('written problems keep a bounded rubric; a figure is a validated scene',async()=>{
  const {route,calls}=setup({answer:()=>({problems:[prob({rubric:[{desc:'역학적 에너지 보존',pts:3},{desc:'',pts:2},{desc:'답',pts:99}],figure:{objects:[{id:'f',type:'floor',x:0,y:0,w:4},{id:'q',type:'iframe'}]}})]})});
  const r=await route(PROB,'POST',{prompt:'서술형',format:'written',withFigure:true},me);
  const p=r.problems[0];
  assert.deepEqual(p.rubric,[{desc:'역학적 에너지 보존',pts:3},{desc:'답',pts:20}]);
  assert.deepEqual(p.figure_scene.objects.map(o=>o.type),['floor']);assert.equal(p.figure_scene.format,'haslalab-scene');
  assert.match(calls[0].policy,/Figure editor schema/);
});

test('numbers in answers and choices are read the way they are written',()=>{
  assert.equal(leadNumber('$4.9\\ \\mathrm{m/s}$'),4.9);assert.equal(leadNumber('2.0 \\times 10^{-3} C'),0.002);assert.equal(leadNumber('1,200 J'),1200);
  assert.ok(Number.isNaN(leadNumber('\\frac{1}{2}mv^2')));assert.ok(Number.isNaN(leadNumber('2v_0')));
  assert.equal(sceneFromObjects([{type:'nope'}]),null);
});

test('the Worker wires the router and forgets the log; the deploy runs this test',()=>{
  const src=readFileSync(new URL('./src/index.js',import.meta.url),'utf8');
  assert.match(src,/import \{ createWorkshopAiRouter, workshopAiForgetUser \} from '\.\/workshop-ai\.js'/);
  assert.ok(src.indexOf('await workshopAiRouter(')>0);assert.ok(src.indexOf('await workshopAiForgetUser(env, me.id)')>0);
  assert.match(readFileSync(new URL('../.github/workflows/deploy-worker.yml',import.meta.url),'utf8'),/test-workshop-ai\.mjs/);
  const mod=readFileSync(new URL('./src/workshop-ai.js',import.meta.url),'utf8');
  assert.doesNotMatch(mod,/env\.[A-Z_]*(KEY|SECRET|TOKEN)/,'no secret read here: the providers come through vision-provider.js');
});
