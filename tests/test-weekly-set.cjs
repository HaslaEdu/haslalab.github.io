/* This week's set on the Olympiad home (weekly-set.js): weakest units first, the step follows recent accuracy,
   problems got right lately stay out, the set holds for the week and renews after all five, a starter set for a new
   learner, the national competition first, and the page that shows it. */
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const W=require('../weekly-set.js'),P=require('../learn-path.js');
const read=f=>fs.readFileSync(path.join(__dirname,'..',f),'utf8');
const realPool=JSON.parse(read('practice/weekly-pool.json'));

/* a small bank: six problems in each of eight units, steps 6 to 9, from two competitions (one Hungarian) */
const UNITS=['mechanics/newton','mechanics/energy','mechanics/rigid_body','em/electrostatics','em/magnetic_field','optics/lenses','thermal/ideal_gas','waves/shm'];
const pool=UNITS.flatMap((u,k)=>Array.from({length:6},(_,j)=>({id:`${j%2?'eotvos':'opho'}-20${10+k}-T~${j+1}`,c:j%2?'eotvos':'opho',y:2010+k,k:'T · '+(j+1),u,s:6+(j%4)})));
const NOW=Date.parse('2026-11-24T03:00:00Z'),S=NOW/1000;
const day=86400;
const skill=(unit,step,n,right)=>({unit,rating:1000+100*step,n,right_n:right,last_at:S-day});
const att=(id,ok,ago)=>({id,u:'',ok,at:S-ago});
/* n answers spread over the units, a share right */
const answers=(n,share,unit)=>Array.from({length:n},(_,i)=>att(pool.find(p=>p.u===(unit||UNITS[i%UNITS.length])&&p.s===9-i%2)?.id||pool[i].id,i<Math.round(n*share),40*day+i*60));
const base={pool,now:NOW,user:'u1',level:'L3'};

test('the week is the ISO week in Korean time: a new one starts Monday 00:00 KST',()=>{
  assert.equal(W.weekKey(Date.parse('2026-11-23T00:00:00+09:00')),'2026-W48');
  assert.equal(W.weekKey(Date.parse('2026-11-22T23:59:00+09:00')),'2026-W47');
  assert.equal(W.weekKey(Date.parse('2026-11-22T15:30:00Z')),'2026-W48','Sunday 15:30 UTC is already Monday in Seoul');
  assert.equal(W.weekKey(Date.parse('2027-01-01T12:00:00+09:00')),'2026-W53');
  assert.equal(W.weekKey(Date.parse('2026-01-01T12:00:00+09:00')),'2026-W01');
});

test('the weakest two units give three problems; the reason is the unit, or a recent miss',()=>{
  const skills={};for(const u of UNITS)skills[u]=skill(u,7,8,5);
  skills['em/magnetic_field']=skill('em/magnetic_field',4,8,1);skills['thermal/ideal_gas']=skill('thermal/ideal_gas',5,8,2);
  skills['optics/lenses']=skill('optics/lenses',9,8,8);
  const r=W.select({...base,seed:'x',skills,attempts:[]});
  assert.equal(r.items.length,5);assert.equal(r.starter,false);
  assert.deepEqual(r.weakUnits,['em/magnetic_field','thermal/ideal_gas']);
  assert.deepEqual(r.items.slice(0,3).map(i=>[i.u,i.why]),[['em/magnetic_field','weak'],['em/magnetic_field','weak'],['thermal/ideal_gas','weak']]);
  assert.deepEqual(r.items.slice(3).map(i=>i.why),['level','stretch']);
  assert.equal(r.items[4].u,'optics/lenses','the stretch problem comes from the strongest unit left');
  assert.equal(r.items[4].s,r.target+1);
  assert.equal(new Set(r.items.map(i=>i.id)).size,5);
  assert.ok(!['em/magnetic_field','thermal/ideal_gas'].includes(r.items[3].u),'the level problem is from another unit');
  /* a miss in a weak unit comes back first, once */
  const miss=pool.find(p=>p.u==='em/magnetic_field'&&p.s===8);
  const r2=W.select({...base,seed:'x',skills,attempts:[att(miss.id,false,2*day)]});
  assert.equal(r2.items[0].id,miss.id);assert.equal(r2.items[0].why,'missed');
  assert.equal(r2.items.filter(i=>i.why==='missed').length,1);
  /* recent misses make a unit weak even with an average rating */
  const atts=pool.filter(p=>p.u==='waves/shm').slice(0,3).map((p,i)=>att(p.id,false,3*day+i));
  assert.equal(W.select({...base,seed:'x',skills:{},attempts:atts}).weakUnits[0],'waves/shm');
});

test('too few known units: units not tried yet fill in',()=>{
  const skills={'mechanics/newton':skill('mechanics/newton',6,4,1)};
  const r=W.select({...base,seed:'s',skills,attempts:[]});
  assert.equal(r.weakUnits[0],'mechanics/newton');
  assert.equal(r.items.filter(i=>i.u==='mechanics/newton').length,2);
  const fresh=r.items.find(i=>i.why==='new');assert.ok(fresh);assert.notEqual(fresh.u,'mechanics/newton');
  assert.ok(W.CORE.includes(fresh.u),'the core units come first');
});

test('the target step follows recent accuracy: up above 75 %, down below 45 %, and the ratings set the base',()=>{
  const skills={};for(const u of UNITS)skills[u]=skill(u,7,3,2);
  const t=share=>W.select({...base,seed:'a',skills,attempts:answers(20,share)});
  assert.equal(t(0.5).target,7);
  assert.equal(t(0.9).target,8);assert.equal(t(0.9).model.adjust,1);
  assert.equal(t(0.2).target,6);assert.equal(t(0.2).model.adjust,-1);
  /* newer answers weigh more: the same count right, but the misses are the recent ones */
  const old=answers(20,0.6).map((a,i)=>({...a,ok:i>=8,at:S-day-i*60}));
  assert.ok(W.model({attempts:old,skills,level:'L3'},pool).accuracy<0.6);
  /* under five answers the accuracy does not count yet */
  assert.equal(W.select({...base,seed:'a',skills,attempts:answers(4,0)}).target,7);
  /* ratings: an average step 9 learner starts one step under the bank's top, a school-level one at its bottom */
  const hi={};for(const u of UNITS)hi[u]=skill(u,9,6,4);
  assert.equal(W.select({...base,seed:'a',skills:hi,attempts:[]}).target,8);
  const lo={};for(const u of UNITS)lo[u]=skill(u,3,6,4);
  assert.equal(W.select({...base,seed:'a',skills:lo,attempts:[]}).target,6);
  /* the picks sit at the target */
  for(const share of [0.2,0.9]){const r=t(share);assert.ok(r.items.filter(i=>i.why!=='stretch').every(i=>Math.abs(i.s-r.target)<=1));}
});

test('problems got right in the last 30 days, reported ones and earlier sets are left out',()=>{
  const skills={'em/magnetic_field':skill('em/magnetic_field',4,8,1),'mechanics/newton':skill('mechanics/newton',5,8,2)};
  const unit=pool.filter(p=>p.u==='em/magnetic_field');
  const attempts=[...unit.slice(0,4).map((p,i)=>att(p.id,true,(5+i)*day)),att(unit[4].id,true,45*day)];
  const r=W.select({...base,seed:'q',skills,attempts,reported:new Set([unit[5].id])});
  const ids=r.items.map(i=>i.id);
  for(const p of unit.slice(0,4))assert.ok(!ids.includes(p.id),'solved lately: '+p.id);
  assert.ok(!ids.includes(unit[5].id),'reported');
  assert.ok(ids.includes(unit[4].id),'right 45 days ago may come back');
  const again=W.select({...base,seed:'q',skills,attempts:[],exclude:ids});
  assert.ok(again.items.every(i=>!ids.includes(i.id)));
});

test('the same week and learner keep the same set; a new week, a new learner or a finished set give another',()=>{
  const skills={};for(const u of UNITS)skills[u]=skill(u,6+UNITS.indexOf(u)%3,5,3);
  const o={...base,skills,attempts:[]};
  const a=W.weekSet(null,o),b=W.weekSet(null,o);
  assert.deepEqual(a.items,b.items,'the same inputs give the same set');
  assert.equal(a.week,'2026-W48');assert.equal(a.gen,0);
  /* answers during the week change nothing until it ends */
  const later={...o,now:NOW+2*day*1000,attempts:answers(12,0.1)};
  assert.equal(W.weekSet(a,later),a);
  const next=W.weekSet(a,{...o,now:NOW+7*day*1000});
  assert.equal(next.week,'2026-W49');assert.notDeepEqual(next.items.map(i=>i.id),a.items.map(i=>i.id));
  assert.notEqual(W.weekSet(a,{...o,user:'u2'}),a,'another learner on this device');
  assert.notEqual(W.weekSet(a,{...o,pool:pool.filter(p=>p.id!==a.items[0].id)}),a,'a problem gone from the bank');
  /* progress: answers given after the set was made; all five done offers a new set without the same problems */
  const t0=a.at;
  const done=a.items.map((i,k)=>({id:i.id,u:'',ok:k!==1,at:t0+60*(k+1)}));
  const pr=W.progress(a,[...done.slice(0,2),{id:a.items[2].id,u:'',ok:true,at:t0-3600}]);
  assert.equal(pr.done,2);assert.equal(pr.marks[a.items[0].id],'right');assert.equal(pr.marks[a.items[1].id],'wrong');assert.equal(pr.marks[a.items[2].id],'','answered before the set: not counted');
  assert.equal(pr.complete,false);
  const full=W.progress(a,done);assert.equal(full.done,5);assert.equal(full.right,4);assert.equal(full.complete,true);
  const fresh=W.nextSet(a,{...o,attempts:done,now:NOW+3600e3});
  assert.equal(fresh.gen,1);assert.equal(fresh.week,a.week);
  assert.ok(fresh.items.every(i=>!a.items.some(x=>x.id===i.id)));
  assert.deepEqual(fresh.prev,a.items.map(i=>i.id));
  assert.equal(W.weekSet(fresh,o),fresh,'the new set is then the week\'s');
  assert.equal(W.setHref(a),'#/learn/practice?mode=set&ids='+a.items.map(i=>i.id).join(','));
});

test('no record yet: a starter set across the core units at the Olympiad level\'s first step',()=>{
  const r=W.select({...base,seed:'n',skills:{},attempts:[]});
  assert.equal(r.starter,true);assert.equal(r.target,7);
  assert.deepEqual(r.items.map(i=>i.u),W.CORE.slice(0,5));
  assert.ok(r.items.every(i=>i.s===7&&i.why==='starter'));
  const set=W.weekSet(null,{...base,skills:{},attempts:[]});assert.equal(set.starter,true);assert.equal(set.accuracy,null);
  /* a skip-only record is still no record */
  assert.equal(W.select({...base,seed:'n',...W.inputsFrom({local:{queue:[{item_id:pool[0].id,unit:'contest/opho',result:'skip',at:S}]}})}).starter,true);
  /* on the real bank too */
  const real=W.select({pool:realPool.items,now:NOW,seed:'n',skills:{},attempts:[],level:'L3'});
  assert.equal(real.items.length,5);assert.equal(new Set(real.items.map(i=>i.u)).size,5);
});

test('the national competition comes first when it has a problem near the step in that unit',()=>{
  const skills={'mechanics/newton':skill('mechanics/newton',5,8,2)};
  const hu=W.select({...base,seed:'z',skills,attempts:[],country:'HU'});
  const plain=W.select({...base,seed:'z',skills,attempts:[],country:'fr'});
  assert.ok(hu.items.filter(i=>i.u==='mechanics/newton').every(i=>i.c==='eotvos'));
  assert.ok(hu.items.filter(i=>i.c==='eotvos').length>plain.items.filter(i=>i.c==='eotvos').length);
  /* a country whose national paper is not in the bank: the same set as no country */
  assert.deepEqual(W.select({...base,seed:'z',skills,attempts:[],country:'kr'}).items,W.select({...base,seed:'z',skills,attempts:[],country:''}).items);
  const us=W.select({pool:realPool.items,now:NOW,seed:'z',skills:{'mechanics/energy':skill('mechanics/energy',5,8,2)},attempts:[],country:'us',level:'L3'});
  assert.ok(us.items.some(i=>i.c==='usapho'),'the United States: USAPhO-style problems');
});

test('the two records join: the account\'s ratings with more answers win, every answer source counts once',()=>{
  const local={skills:{'waves/shm':skill('waves/shm',6,3,1),'em/induction':skill('em/induction',7,9,6)},
    queue:[{item_id:'opho-2020-T~1',unit:'contest/opho',result:'missed',at:S-100}],
    recent:{'opho-2020-T~1':S-100,'eotvos-1949-T~2':S-5000,'usapho-u1-001':S-9000,'usapho-u1-002':S-9500},
    contest:{done:{'opho-2020-T~1':0,'eotvos-1949-T~2':1}},solved:{'usapho-u1-001':'mechanics/energy'},wrong:{'usapho-u1-002':S-9500},studyLevel:'L4'};
  const inp=W.inputsFrom({local,serverSkills:[skill('waves/shm',8,7,6),skill('em/induction',5,2,0)],
    serverAttempts:[{item_id:'opho-2021-T~3',mode:'contest',unit:'contest/opho',step:7,result:'solved',at:S-200},{item_id:'eotvos-1949-T~2',unit:'contest/eotvos',result:'solved',at:S-5010}],
    serverState:{contest:{done:{'wopho-2011-T1~1':1}}},reports:[{id:'opho-2022-T~2',r:'rTypo'}]});
  assert.equal(inp.skills['waves/shm'].n,7);assert.equal(inp.skills['em/induction'].n,9);
  assert.deepEqual(inp.attempts.map(a=>[a.id,a.ok]),[['opho-2020-T~1',false],['opho-2021-T~3',true],['eotvos-1949-T~2',true],['usapho-u1-001',true],['usapho-u1-002',false]]);
  assert.equal(inp.attempts.find(a=>a.id==='usapho-u1-001').u,'mechanics/energy');
  assert.equal(inp.attempts[0].u,'','a contest rating key is not a unit');
  assert.ok(inp.solvedEver.has('wopho-2011-T1~1')&&inp.solvedEver.has('eotvos-1949-T~2'));
  assert.ok(inp.reported.has('opho-2022-T~2'));assert.equal(inp.level,'L4');
  assert.equal(W.inputsFrom({}).level,'L3','the Olympiad home\'s default level');
});

test('the bank: every problem has a learning-path unit, a step and a competition name; units come from keywords',()=>{
  assert.ok(realPool.items.length>=300);
  for(const i of realPool.items){assert.ok(P.SUBTOPICS.has(i.u),i.id+' '+i.u);assert.ok(i.s>=1&&i.s<=10);assert.ok(realPool.names[i.c],i.c);assert.match(i.id,W.ID);}
  assert.ok(new Set(realPool.items.map(i=>i.u)).size>=20);
  assert.equal(W.unitOfText('직렬 축전기와 코일',''),'em/capacitors');
  assert.equal(W.unitOfText('앵그리 버드','새를 포물선 궤도로 던진다'),'mechanics/kinematics');
  assert.equal(W.unitOfText('제목',''),null);
  assert.equal(W.dots(7),'●●○○○');assert.equal(W.dots(10),'●●●●●');assert.equal(W.dots(3),'●○○○○');
  /* weekly-set.js carries the bank file's digest (tools/build-site-catalogue.cjs) */
  assert.match(read('weekly-set.js'),/const POOL_V="[a-f0-9]{12}";/);
  assert.match(read('index.html'),/<script src="weekly-set\.js\?v=[a-f0-9]{12}"><\/script>/);
});

/* the card on the page: index.html's site-design.js with this module, the pool and a practice record */
function page(store,api){
  const boxes={},ls={...store};
  const box={id:'olyWeekly',isConnected:true,innerHTML:'',querySelector:()=>null};
  const ctx={window:{},console,URL,URLSearchParams,lang:'ko',esc:s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])),
    localStorage:{getItem:k=>k in ls?ls[k]:null,setItem:(k,v)=>{ls[k]=String(v);}},
    document:{getElementById:id=>id==='olyWeekly'?box:null},
    fetch:async url=>{assert.match(url,/^practice\/weekly-pool\.json\?v=/);return{ok:true,json:async()=>realPool};},
    Date:class extends Date{constructor(...a){super(...(a.length?a:[NOW]));}static now(){return NOW;}}};
  if(api){ctx.cmTok=()=>'tok';ctx.cmApi=api;ctx.cmLoadMe=async()=>({id:42});}
  vm.createContext(ctx);
  for(const f of ['learn-path.js','weekly-set.js'])vm.runInContext(read(f),ctx,{filename:f});
  ctx.window.HL_LEARN_PATH=ctx.HL_LEARN_PATH;ctx.window.HL_WEEKLY_SET=ctx.HL_WEEKLY_SET;
  const src=read('site-design.js');
  vm.runInContext(src.slice(src.indexOf('const OLY_TEXT='),src.indexOf('async function mountHomeActivity')).replace(/^const /gm,'var ').replace(/^let /gm,'var '),ctx);
  return{ctx,box,ls,run:async()=>{ctx.mountWeeklySet('kr');for(let i=0;i<8;i++)await new Promise(r=>setImmediate(r));return box.innerHTML;}};
}
test('the Olympiad home card: starter line for a new visitor, reasons, progress and the one button for a learner',async()=>{
  let p=page({});
  let html=await p.run();
  assert.match(html,/풀수록 내 약점에 맞춰집니다/);assert.match(html,/href="#\/learn\/practice\?mode=diag"/);
  assert.equal((html.match(/<li class="oly-wk/g)||[]).length,5);
  assert.match(html,/0\/5/);assert.match(html,/href="#\/learn\/practice\?mode=set&ids=[^"]+"/);
  assert.match(html,/기본 단원/);
  const stored=JSON.parse(p.ls.hlWeeklySet);assert.equal(stored.week,'2026-W48');assert.match(stored.user,/^[a-z0-9]{8,32}$/);
  /* a learner with weak units and two of the set answered */
  const set=stored;
  const recent={},done={};set.items.slice(0,2).forEach((i,k)=>{recent[i.id]=set.at+60;done[i.id]=k?0:1;});
  const skills={'em/magnetic_field':skill('em/magnetic_field',4,9,2),'mechanics/newton':skill('mechanics/newton',8,9,8)};
  p=page({hlPractice:JSON.stringify({skills,recent,contest:{done}}),hlWeeklySet:JSON.stringify(set),hlWeeklyId:JSON.stringify(set.user).slice(1,-1)});
  html=await p.run();
  assert.match(html,/2\/5/);assert.match(html,/oly-wk right/);assert.match(html,/oly-wk wrong/);assert.match(html,/✓/);
  /* a member: the account's record decides, and the set is theirs */
  const calls=[];
  p=page({},async(m,path)=>{calls.push(path);return path==='/practice/state'?{state:{},skills:Object.values(skills)}:path==='/practice/recent'?{attempts:[]}:null;});
  html=await p.run();
  assert.deepEqual(calls.sort(),['/practice/recent','/practice/state']);
  assert.match(html,/약한 단원: 전류와 자기장/);assert.match(html,/목표 난이도 \d단계/);assert.doesNotMatch(html,/풀수록/);
  assert.equal(JSON.parse(p.ls.hlWeeklySet).user,'u42');
  /* an old server without /recent still gives a set */
  p=page({},async(m,path)=>{if(path==='/practice/recent')throw{status:404};return{state:{},skills:Object.values(skills)};});
  assert.match(await p.run(),/약한 단원/);
});
