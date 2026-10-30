const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const Runtime = require('../site-runtime.js');
const rootPath = path.resolve(__dirname, '..');
const arena = fs.readFileSync(path.join(rootPath, 'arena.js'), 'utf8');
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const end = Date.parse('2026-12-01T00:00:00+09:00') / 1000;

function app(route = '#/monthly') {
  const root = {innerHTML:''}, calls = [];
  const context = {lang:'ko', esc, cm:{me:null}, location:{hash:route},
    document:{getElementById:()=>root}, cmIdentityScope:()=> 'account-A',
    cmHealth:async()=>({v:5}), cmLoadMe:async()=>null,
    cmPageRead:async p=>{calls.push(p);return{api_version:5,period:'2026-11',user:null};},
    cmApi:async(m,p)=>{calls.push(p);return{period:'2026-11',rows:[]};}};
  vm.createContext(context);
  vm.runInContext(arena, context);
  return {context,root,calls,run:code=>vm.runInContext(code,context)};
}

test('monthly routes and legacy weekly links mount the same arena and preserve period requests', async () => {
  for (const [route,request,view] of [
    ['#/monthly','/monthly?lang=ko','list'],
    ['#/monthly/2026-11','/monthly?lang=ko&month=2026-11','list'],
    ['#/weekly/2026-W44','/weekly?lang=ko&week=2026-W44','list'],
    ['#/rank/month','/rank?scope=month','rank'],
    ['#/rank/2026-11','/rank?scope=month&month=2026-11','rank'],
    ['#/rank/week','/rank?scope=week','rank'],
  ]) {
    const a=app(route);
    a.context.arWeekly=async()=>{a.root.innerHTML='list';};
    a.context.arRank=async()=>{a.root.innerHTML='rank';};
    await a.run('arMount()');
    assert.equal(a.root.innerHTML,view,route);
    assert.equal(a.calls[0],request,route);
    assert.deepEqual(Runtime.routeNeeds(route),['arena']);
  }
  for (const prefix of ['monthly','weekly']) for (const [suffix,expected] of [['p/4','problem:4'],['admin','admin']]) {
    const a=app(`#/${prefix}/${suffix}`);
    a.context.arProblem=async(r,alive,id)=>{r.innerHTML='problem:'+id;};
    a.context.arAdmin=async r=>{r.innerHTML='admin';};
    await a.run('arMount()');
    assert.equal(a.root.innerHTML,expected);
    assert.deepEqual(Runtime.routeNeeds(`#/${prefix}/${suffix}`),['arena']);
  }
});

test('monthly listing labels and absolute deadline use Korean time and canonical links', async () => {
  const a=app(), p={id:4,no:4,title:'양성자 사슬',kind:'essay',subject:'physics',level:20,points:100,users:0,solvers:0,open:true,opens_at:1792940400,closes_at:end};
  await a.context.arWeekly(a.root,()=>true,null,{period:'2026-11',week:'2026-11',problems:[p],top:[],now:end-86400,
    months:[{period:'2026-11',o:p.opens_at,c:end},{week:'2026-W43',o:p.opens_at-604800,c:p.opens_at}]});
  assert.match(a.root.innerHTML,/월별 문제/);
  assert.match(a.root.innerHTML,/2026년 11월/);
  assert.match(a.root.innerHTML,/2026\.11\.30 23:59 \(한국 시각\)/);
  assert.match(a.root.innerHTML,/href="#\/monthly\/p\/4"/);
  assert.match(a.root.innerHTML,/href="#\/rank\/2026-11"/);
  assert.match(a.root.innerHTML,/href="#\/monthly\/2026-W43"/);
  assert.ok(!a.root.innerHTML.includes('매주 월요일'));
  assert.ok(!a.root.innerHTML.includes('이번 주'));
  assert.equal(a.context.arDate(Date.parse('2026-11-01T00:00:00+09:00')/1000),'11.1');
  assert.equal(a.context.arPeriodLabel('2026-W43'),'2026-W43');
  a.context.lang='en';
  assert.equal(a.context.arPeriodLabel('2026-11'),'November 2026');
  assert.equal(a.context.arDeadline(end),'2026.11.30 23:59 KST');
});

test('monthly ranking and global navigation use the monthly vocabulary without changing the community route', async () => {
  const a=app();
  await a.context.arRank(a.root,()=>true,'month',{period:'2026-11',rows:[]});
  assert.match(a.root.innerHTML,/월별 랭킹/);
  assert.match(a.root.innerHTML,/2026년 11월/);
  assert.match(a.root.innerHTML,/href="#\/rank\/month" class="on"/);
  const index=fs.readFileSync(path.join(rootPath,'index.html'),'utf8');
  assert.match(index,/navWeekly:"월별문제"/);
  assert.match(index,/navWeekly:"Monthly"/);
  assert.match(index,/<a href="#\/monthly"/);
  assert.match(index,/<a href="#\/community"/);
});

test('the only past month stays reachable when the next month has no active problems', async () => {
  const a=app();
  await a.context.arWeekly(a.root,()=>true,null,{period:'2026-12',problems:[],top:[],now:end,
    months:[{month:'2026-11',o:1792940400,c:end}]});
  assert.match(a.root.innerHTML,/해당 월 문제가 아직 없습니다/);
  assert.match(a.root.innerHTML,/href="#\/monthly\/2026-11"/);
  assert.match(a.root.innerHTML,/2026년 11월/);
});

test('monthly personal reads coalesce but stay uncached, and submissions refresh their arena family', async () => {
  assert.deepEqual(Runtime.requestPolicy('GET','/monthly?month=2026-11'),{safe:true,public:false,ttl:0});
  const cache=Runtime.createRequestCache(), state={path:'/monthly?month=2026-11',token:'A',lang:'ko'};
  let calls=0,finish;
  const send=()=>{calls++;return new Promise(r=>{finish=r;});};
  const one=cache.run(state,send),two=cache.run(state,send);
  await new Promise(r=>setImmediate(r));assert.equal(calls,1);
  finish({problems:[]});await Promise.all([one,two]);
  await cache.run(state,async()=>{calls++;return{};});assert.equal(calls,2);
  await cache.run({...state,path:'/problems/4/submit',method:'POST'},async()=>({id:1}));
  await cache.run(state,async options=>{assert.equal(options.bypassCache,true);return{};});
});
