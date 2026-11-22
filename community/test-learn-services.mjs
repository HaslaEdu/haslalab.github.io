import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createLearnRouter, keepsMath, tutorMessages, TUTOR_FREE, TUTOR_PLUS, utcDay} from './src/learn-services.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
function setup({ai}={}){
  const db=new DatabaseSync(':memory:');
  const D1={async batch(s){const out=[];for(const x of s)out.push(await x.all());return out;},prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{last_row_id:Number(r.lastInsertRowid)}};}};}};
  let t=1_800_000_000;const calls=[];
  const AI={async run(model,input){calls.push(input);return{response:ai?ai(input):'ok'};}};
  const route=createLearnRouter({HttpError:H,bad,now:()=>t,clientIp:()=>'1.2.3.4',needUser:u=>{if(!u)throw new H(401,'login_required');return u;},limit:async()=>{}});
  return {db,env:{DB:D1,AI},calls,route:(p,m,b,me)=>route(p,m,b,me,null,{DB:D1,AI}),tick:s=>{t+=s;},now:()=>t};
}
const me={id:7};
const fails=async(p,code)=>assert.rejects(p,e=>e.code===code);

test('a guest has no tutor, a member gets the free questions a day, a plan gets more',async()=>{
  const {route,db,now,tick}=setup({ai:()=>'Think about energy: what is conserved?'});
  assert.deepEqual(await route('/api/learn/plan','GET',null,null),{plan:'guest',ads:true,tutorLimit:0,tutorLeft:0});
  await fails(route('/api/learn/tutor','POST',{problem:'p',question:'q'},null),'login_required');
  const p=await route('/api/learn/plan','GET',null,me);
  assert.equal(p.plan,'free');assert.equal(p.ads,true);assert.equal(p.tutorLeft,TUTOR_FREE);
  for(let i=0;i<TUTOR_FREE;i++){const r=await route('/api/learn/tutor','POST',{problem:'A ball falls 5 m.',question:'how?',lang:'es'},me);assert.equal(r.tutorLeft,TUTOR_FREE-1-i);}
  await fails(route('/api/learn/tutor','POST',{problem:'A ball',question:'how?'},me),'tutor_limit');
  db.prepare('INSERT INTO entitlements(user_id,kind,starts_at,ends_at,source,created_at) VALUES(?,?,?,?,?,?)').run(7,'plus',now()-10,now()+86400*30,'test',now());
  const plus=await route('/api/learn/plan','GET',null,me);
  assert.equal(plus.plan,'plus');assert.equal(plus.ads,false);assert.equal(plus.tutorLeft,TUTOR_PLUS-TUTOR_FREE);
  tick(86400*31);
  const after=await route('/api/learn/plan','GET',null,me);
  assert.equal(after.plan,'free','an ended plan no longer counts');assert.equal(after.tutorLeft,TUTOR_FREE,'a new day starts afresh');
  await fails(route('/api/learn/tutor','POST',{problem:'',question:'x'},me),'bad_tutor');
});

test('a failed model call gives the question back',async()=>{
  const {route}=setup({ai:()=>''});
  await fails(route('/api/learn/tutor','POST',{problem:'p',question:'q'},me),'ai_failed');
  assert.equal((await route('/api/learn/plan','GET',null,me)).tutorLeft,TUTOR_FREE);
});

test('the tutor never gives the answer before the learner has tried, and speaks the learner\'s language',()=>{
  const m=tutorMessages({problem:'P',choices:['1 m','2 m'],question:'answer?',lang:'hi',solved:false,hintsSeen:2});
  assert.match(m[0].content,/Hindi/);assert.match(m[0].content,/never state the final/);assert.match(m[1].content,/\(B\) 2 m/);
  assert.match(tutorMessages({problem:'P',question:'q',lang:'xx',solved:true}).at(0).content,/English[\s\S]*full solution/);
});

test('translations keep the math, are cached for everyone and fall back to the original',async()=>{
  assert.ok(keepsMath('Find $v$ and $$E=mc^2$$.','Encuentra $v$ y $$E=mc^2$$.'));
  assert.ok(!keepsMath('Find $v$.','Encuentra $w$.'));
  let n=0;
  const {route,calls}=setup({ai:input=>{n++;const s=input.messages[1].content;return s.includes('broken')?'수식 없음':s.replace('Find','구하라');}});
  const r=await route('/api/learn/translate','POST',{to:'ko',texts:['Find $v_0$.','A broken $x$ here','']},null);
  assert.deepEqual(r.texts,['구하라 $v_0$.',null,null]);
  const again=await route('/api/learn/translate','POST',{to:'ko',texts:['Find $v_0$.']},me);
  assert.deepEqual(again.texts,['구하라 $v_0$.']);assert.equal(calls.length,2,'the cached text costs no second call');
  await fails(route('/api/learn/translate','POST',{to:'es',texts:['a']},null),'bad_lang','only Korean and English for now');
  await fails(route('/api/learn/translate','POST',{to:'ko',texts:new Array(13).fill('a')},null),'bad_texts');
  assert.match(utcDay(0),/^1970-01-01$/);
});

test('a teacher makes a free class, students join with its code, and the teacher sees assignments done',async()=>{
  const {route,db,now}=setup();
  db.exec("CREATE TABLE users(id INTEGER PRIMARY KEY,nickname TEXT)");db.exec("INSERT INTO users VALUES(7,'teacher'),(8,'ana'),(9,'bo')");
  const {PRACTICE_SCHEMA}=await import('./src/practice-progress.js');for(const s of PRACTICE_SCHEMA)db.exec(s);
  const t={id:7},a={id:8},b={id:9};
  await fails(route('/api/learn/classes','POST',{name:''},t),'bad_name');
  const c=await route('/api/learn/classes','POST',{name:'Physics 11B'},t);
  assert.match(c.code,/^[A-Z2-9]{6}$/);
  await fails(route('/api/learn/classes','POST',{name:'Second'},t),'class_limit');
  await fails(route('/api/learn/classes/join','POST',{code:'ZZZZZZ'},a),'class_not_found');
  await fails(route('/api/learn/classes/join','POST',{code:c.code},t),'own_class');
  assert.equal((await route('/api/learn/classes/join','POST',{code:c.code.toLowerCase()},a)).name,'Physics 11B');
  await route('/api/learn/classes/join','POST',{code:c.code},b);
  await fails(route(`/api/learn/classes/${c.id}`,'GET',null,a),'not_teacher');
  await fails(route(`/api/learn/classes/${c.id}/assignments`,'POST',{title:'HW1',items:['drop table']},t),'bad_items');
  const as=await route(`/api/learn/classes/${c.id}/assignments`,'POST',{title:'Kinematics',items:['ap1-u1-001','ap1-u1-002'],due_at:now()+86400},t);
  db.prepare("INSERT INTO practice_attempts(user_id,item_id,mode,unit,step,result,created_at) VALUES(8,'ap1-u1-001','track','mechanics/kinematics',3,'right',1)").run();
  db.prepare("INSERT INTO practice_skills(user_id,unit,rating,n,right_n,last_at) VALUES(8,'mechanics/kinematics',1320,1,1,1)").run();
  const view=await route(`/api/learn/classes/${c.id}`,'GET',null,t);
  const ana=view.members.find(m=>m.id===8);
  assert.equal(ana.assignments[as.id],1);assert.equal(ana.answered,1);assert.equal(ana.units[0].unit,'mechanics/kinematics');
  assert.equal(view.members.find(m=>m.id===9).assignments[as.id],0);
  const mine=await route('/api/learn/classes','GET',null,a);
  assert.equal(mine.joined[0].teacher,'teacher');assert.equal(mine.assignments[0].done,1);assert.deepEqual(mine.assignments[0].items,['ap1-u1-001','ap1-u1-002']);
  await route(`/api/learn/classes/${c.id}/leave`,'POST',{},b);
  assert.equal((await route(`/api/learn/classes/${c.id}`,'GET',null,t)).members.length,1);
  await route(`/api/learn/classes/${c.id}`,'DELETE',null,t);
  assert.equal((await route('/api/learn/classes','GET',null,t)).teaching.length,0);
});
