import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createCreationRouter} from './src/creations.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
function setup(){
  const db=new DatabaseSync(':memory:');db.exec("CREATE TABLE users(id INTEGER PRIMARY KEY,nickname TEXT,role TEXT)");db.exec("INSERT INTO users VALUES(1,'ana',NULL),(2,'bo',NULL),(9,'staff','admin')");
  const D1={async batch(s){const out=[];for(const x of s)out.push(await x.all());return out;},prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{last_row_id:Number(r.lastInsertRowid),changes:Number(r.changes)}};}};}};
  const hits=new Map();
  const route=createCreationRouter({HttpError:H,bad,now:()=>1_800_000_000,clientIp:()=>'1.1.1.1',needUser:u=>{if(!u)throw new H(401,'login_required');return u;},
    limit:async(env,k,max)=>{const n=(hits.get(k)||0)+1;hits.set(k,n);if(n>max)throw new H(429,'rate_limited');}});
  return (p,m,b,me,q='')=>route(p,m,b,me,{url:'https://x'+p+q},{DB:D1});
}
const ana={id:1},bo={id:2},staff={id:9,role:'admin'};
const fails=async(p,code)=>assert.rejects(p,e=>e.code===code);
const sim={kind:'sim',title:'Projectile',summary:'Change the angle',code:'loop(dt=>{})',answer:'45',unit:'deg'};
const prob={kind:'code',title:'Euler step',body:'Write step(x,v,dt).',starter:'def step(x,v,dt):\n    pass',grader:'def grade(ns):\n    return {"tests":[]}'};

test('members publish simulations and Python problems; guests read them; bad ones are refused',async()=>{
  const r=setup();
  await fails(r('/api/creations','POST',sim,null),'login_required');
  await fails(r('/api/creations','POST',{...sim,kind:'video'},ana),'bad_kind');
  await fails(r('/api/creations','POST',{...sim,code:''},ana),'bad_code');
  await fails(r('/api/creations','POST',{...prob,grader:'print(1)'},ana),'bad_grader');
  await fails(r('/api/creations','POST',{...sim,title:'x'.repeat(81)},ana),'bad_title');
  const a=await r('/api/creations','POST',sim,ana),b=await r('/api/creations','POST',prob,bo);
  const list=await r('/api/creations','GET',null,null);
  assert.deepEqual(list.items.map(i=>i.id),[b.id,a.id]);assert.equal(list.items[0].nickname,'bo');assert.ok(!('code' in list.items[0]),'the list carries no code');
  assert.deepEqual((await r('/api/creations','GET',null,null,'?kind=sim')).items.map(i=>i.id),[a.id]);
  const one=await r(`/api/creations/${a.id}`,'GET',null,null);assert.equal(one.creation.code,'loop(dt=>{})');assert.equal(one.creation.mine,false);
});

test('only the owner or staff edit and hide a creation; a hidden one is gone for everyone else',async()=>{
  const r=setup();const a=await r('/api/creations','POST',sim,ana);
  await fails(r(`/api/creations/${a.id}`,'PATCH',{title:'Mine now'},bo),'not_owner');
  await r(`/api/creations/${a.id}`,'PATCH',{title:'Projectile with drag'},ana);
  assert.equal((await r(`/api/creations/${a.id}`,'GET',null,null)).creation.title,'Projectile with drag');
  await r(`/api/creations/${a.id}`,'DELETE',null,staff);
  await fails(r(`/api/creations/${a.id}`,'GET',null,bo),'not_found');
  assert.equal((await r(`/api/creations/${a.id}`,'GET',null,ana)).creation.status,'hidden','the owner still sees it');
  assert.equal((await r('/api/creations','GET',null,null)).items.length,0);
  assert.equal((await r('/api/creations','GET',null,ana,'?mine=1')).items.length,1);
});

test('likes toggle once per member, solves count once, and plays once a day per visitor',async()=>{
  const r=setup();const a=await r('/api/creations','POST',sim,ana);
  await fails(r(`/api/creations/${a.id}/like`,'POST',{},null),'login_required');
  assert.equal((await r(`/api/creations/${a.id}/like`,'POST',{},bo)).likes,1);
  assert.equal((await r(`/api/creations/${a.id}/like`,'POST',{},bo)).likes,1);
  assert.equal((await r(`/api/creations/${a.id}/like`,'POST',{on:false},bo)).likes,0);
  await r(`/api/creations/${a.id}/solve`,'POST',{},bo);assert.equal((await r(`/api/creations/${a.id}/solve`,'POST',{},bo)).solves,1);
  assert.equal((await r(`/api/creations/${a.id}/play`,'POST',{},null)).counted,true);
  assert.equal((await r(`/api/creations/${a.id}/play`,'POST',{},null)).counted,false);
  const v=await r(`/api/creations/${a.id}`,'GET',null,bo);assert.equal(v.creation.plays,1);assert.equal(v.solved,true);assert.equal(v.liked,false);
  const f=await r('/api/creations','POST',{...sim,title:'Remix',forked_from:a.id},bo);
  assert.equal((await r(`/api/creations/${f.id}`,'GET',null,null)).creation.forked_from,a.id);
});
