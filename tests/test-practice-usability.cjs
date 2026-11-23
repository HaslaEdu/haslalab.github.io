/* Practice usability rules (practice-tools.js): the streak's weekly free day and exam-time break, drafts of the
   working kept in the browser, the card before a unit's first problems, and a guest's progress joining the account on
   the first sign-in (checked against the server's own merge and routes). */
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const T=require('../practice-tools.js'),P=require('../learn-path.js');
const root=path.join(__dirname,'..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const days=(from,n)=>Array.from({length:n},(_,i)=>T.addDays(from,i));

test('weeks start on Monday',()=>{
  assert.equal(T.weekOf('2026-11-23'),'2026-11-23');assert.equal(T.weekOf('2026-11-29'),'2026-11-23');
  assert.equal(T.weekOf('2026-11-22'),'2026-11-16');assert.equal(T.weekOf('2027-01-01'),'2026-12-28');
});

test('streak: today not yet studied keeps it; one missed day a week is bridged by itself; a second one ends it',()=>{
  const wed='2026-11-25';
  /* Mon and Tue studied, today (Wed) not yet */
  assert.equal(T.streakInfo(['2026-11-23','2026-11-24'],{},wed).n,2);
  /* Fri to Sun of last week studied, Mon missed, Tue studied: Monday uses this week's free day */
  let s=T.streakInfo(['2026-11-20','2026-11-21','2026-11-22','2026-11-24'],{},wed);
  assert.equal(s.n,4);assert.deepEqual(s.frozen,['2026-11-23']);assert.equal(s.freezeLeft,false);
  /* two days missed in one week: the streak is the days after them */
  s=T.streakInfo(['2026-11-20','2026-11-23','2026-11-26'],{},'2026-11-26');
  assert.equal(s.n,1);assert.deepEqual(s.frozen,[]);assert.equal(s.freezeLeft,true,'a free day is not spent on a streak that ended anyway');
  /* the free day comes back each week: one miss in each of three weeks keeps a long streak */
  const list=days('2026-11-02',28).filter(d=>!['2026-11-04','2026-11-12','2026-11-20'].includes(d));
  s=T.streakInfo(list,{},'2026-11-29');assert.equal(s.n,25);assert.deepEqual(s.frozen,['2026-11-04','2026-11-12','2026-11-20']);
  assert.equal(s.freezeLeft,true,'this week (from 23 November) has not used one');
  /* no history: nothing to keep, nothing used */
  s=T.streakInfo([],{},wed);assert.equal(s.n,0);assert.deepEqual(s.frozen,[]);
});

test('exam-time break: holds the streak up to 14 days, can be stopped, and cannot be chained',()=>{
  const start='2026-12-01';
  const cfg=T.pauseStart({},start);
  assert.deepEqual(cfg.pauses,[{from:'2026-12-01',to:'2026-12-14'}]);
  assert.equal(T.activePause(cfg,'2026-12-14').to,'2026-12-14');assert.equal(T.activePause(cfg,'2026-12-15'),null);
  /* studied until 30 November, then nothing during the break, back on 15 December */
  const before=days('2026-11-24',7);
  let s=T.streakInfo(before,cfg,'2026-12-10');assert.equal(s.n,7);assert.ok(s.pause);assert.deepEqual(s.frozen,[]);
  s=T.streakInfo([...before,'2026-12-15'],cfg,'2026-12-15');assert.equal(s.n,8,'the paused days neither count nor break it');
  /* studying on a paused day still counts */
  s=T.streakInfo([...before,'2026-12-03'],cfg,'2026-12-05');assert.equal(s.n,8);
  /* stopping early: the paused days so far stay paused; from today it runs again */
  const stopped=T.pauseStop(cfg,'2026-12-05');assert.deepEqual(stopped.pauses,[{from:'2026-12-01',to:'2026-12-04'}]);
  assert.deepEqual(T.pauseStop(T.pauseStart({},start),start).pauses,[],'stopped on its first day: no pause left');
  /* a new break needs 7 days after the last one ended */
  assert.equal(T.pauseStart(cfg,'2026-12-10'),null);assert.equal(T.pauseStart(cfg,'2026-12-21'),null);
  assert.equal(T.pauseAllowed(cfg,'2026-12-22'),true);assert.equal(T.pauseStart(cfg,'2026-12-22').pauses.length,2);
  assert.equal(T.streakInfo(before,cfg,'2026-12-10').canPause,false);
  /* a pause longer than 14 days (edited by hand) is ignored */
  assert.equal(T.activePause({pauses:[{from:'2026-12-01',to:'2026-12-31'}]},'2026-12-05'),null);
});

test('no hearts or energy: the page never blocks practice after mistakes',()=>{
  const js=read('practice.js');
  assert.doesNotMatch(js,/\bhearts?\s*[:=]|energy\s*[:=]|lives\s*[:=]/i);
  assert.match(js,/skNoHearts/);
});

test('drafts: strokes are compacted and capped, pages checked, old and extra drafts dropped, a small local copy',()=>{
  const st=T.compactStrokes([{tool:'pen',w:9,pts:[[1.4,2.6],[3.5,4.49]],id:3},{tool:'x',pts:[]},null,{tool:'eraser',w:999,pts:[[0,0]]}]);
  assert.deepEqual(st,[{tool:'pen',w:9,pts:[[1,3],[4,4]]},{tool:'eraser',w:60,pts:[[0,0]]}]);
  const big=T.compactStrokes([{tool:'pen',w:4,pts:Array.from({length:T.DRAFT_POINTS+500},(_,i)=>[i,i])}]);
  assert.equal(big[0].pts.length,T.DRAFT_POINTS);
  const page='data:image/jpeg;base64,'+'A'.repeat(4000);
  const d=T.draftOf('ap1-u1-001',{pages:[page,'data:image/png;base64,xx','nope',page,page,page,page],strokes:[{tool:'pen',w:4,pts:[[1,1]]}],meta:{k:'track',u:'mechanics/kinematics'},t:'AP 1'},1000);
  assert.equal(d.pages.length,4,'only JPEG pages, at most four');assert.equal(d.strokes.length,1);assert.equal(d.meta.k,'track');
  assert.ok(T.draftOk(d,1000+86400));assert.ok(!T.draftOk(d,1000+15*86400),'two weeks old: gone');
  assert.ok(T.draftEmpty(T.draftOf('x',{},1)));assert.ok(!T.draftEmpty(d));
  const list=Array.from({length:9},(_,i)=>T.draftOf('p'+i,{strokes:[{pts:[[0,0]]}]},2000+i));list.push(T.draftOf('old',{strokes:[{pts:[[0,0]]}]},1));list.push({id:'junk'});
  const {keep,drop}=T.pruneDrafts(list,3000);
  assert.deepEqual(keep,['p8','p7','p6','p5','p4','p3']);assert.deepEqual(drop.sort(),['junk','old','p0','p1','p2']);
  /* localStorage: the whole draft when small; without pages when they are too big; nothing when even the strokes are */
  assert.equal(T.localDraft(d),d);
  const heavy=T.draftOf('h',{pages:Array(4).fill('data:image/jpeg;base64,'+'A'.repeat(100000)),strokes:[{pts:[[0,0]]}]},1);
  assert.deepEqual(T.localDraft(heavy).pages,[]);
  assert.equal(T.localDraft({...heavy,strokes:[{pts:Array(T.DRAFT_LOCAL_BYTES).fill([0,0])}]}),null);
});

test('backups carry the streak break and the unit cards seen; bad pauses are dropped',()=>{
  const v=T.validateBackup({app:T.APP,version:T.VERSION,state:{xp:5,streakCfg:{pauses:[{from:'2026-12-01',to:'2026-12-14'},{from:'2026-12-01',to:'2027-02-01'},'x']},intro:{'mechanics/kinematics':100,bad:'x'}}});
  assert.ok(v.ok);assert.deepEqual(v.state.streakCfg.pauses,[{from:'2026-12-01',to:'2026-12-14'}]);assert.deepEqual(v.state.intro,{'mechanics/kinematics':100});
  const m=T.mergeBackup({streakCfg:{pauses:[{from:'2026-10-01',to:'2026-10-03'}]},intro:{a:1}},v.state);
  assert.equal(m.streakCfg.pauses.length,2);assert.deepEqual(m.intro,{a:1,'mechanics/kinematics':100});
});

test('every unit on the path has a card: one line in each language, a formula, and a simulation only where one exists',()=>{
  const sims=new Map([...read('concepts.js').matchAll(/\{id:'([a-z-]+)',unit:'([a-z_]+\/[a-z_]+)'/g)].map(m=>[m[1],m[2]]));
  assert.ok(sims.size>=6);
  for(const unit of P.SUBTOPICS.keys()){
    const c=T.unitCard(unit);assert.ok(c,unit);
    assert.ok(c.ko&&c.en&&c.f,unit);assert.ok(c.ko.length<=90&&c.en.length<=110,unit+' one short line');
    assert.doesNotMatch(c.ko+c.en,/—|unlock|seamless|elevate|comprehensive/i,unit);
    if(c.sim)assert.equal(sims.get(c.sim),unit,unit+' → '+c.sim);
  }
  for(const [sim,unit] of sims)assert.equal(T.unitCard(unit).sim,sim,'the '+sim+' simulation is linked from its unit');
  assert.equal(T.unitCard('nope/x'),null);
  assert.equal(T.guideHref('mechanics/energy'),'/#/learn/guide/mechanics/energy');assert.equal(T.simHref('pendulum'),'/#/learn/concepts?sim=pendulum');
});

test('first sign-in: a guest’s progress joins the empty account and stays there',async()=>{
  const {mergeState,createPracticeRouter,PRACTICE_SCHEMA}=await import('../community/src/practice-progress.js');
  const {DatabaseSync}=require('node:sqlite');
  const db=new DatabaseSync(':memory:');for(const sql of PRACTICE_SCHEMA)db.exec(sql);
  const D1={async batch(s){for(const x of s)await x.run();return [];},prepare(sql){let a=[];return{bind(...x){a=x;return this;},async first(){return db.prepare(sql).get(...a)||null;},async all(){return{results:db.prepare(sql).all(...a)};},async run(){db.prepare(sql).run(...a);return{meta:{}};}};}};
  class E extends Error{constructor(s,c){super(c);this.code=c;}}
  const t=1_800_000_000,route=createPracticeRouter({HttpError:E,needUser:u=>{if(!u)throw new E(401,'login_required');return u;},limit:async()=>{},now:()=>t,bad:c=>{throw new E(400,c);}});
  const env={DB:D1},me={id:42};
  /* what a guest built up in this browser */
  const guest={profile:{region:'kr',level:'high1',goal:'exam',oly:0,daily:10,at:t-5000},xp:120,days:['2027-01-10','2027-01-11'],level:{'mechanics/energy':4},
    solved:{'ap1-u3-002':'mechanics/energy'},wrong:{'ap1-u1-004':t-100},bank:{done:{'b1':1},stars:{}},contest:{done:{'opho-2021-1':1}}};
  const queue=[{item_id:'ap1-u3-002',mode:'track',unit:'mechanics/energy',step:4,result:'right',at:t-200},{item_id:'ap1-u1-004',mode:'track',unit:'mechanics/kinematics',step:3,result:'wrong',at:t-100}];
  /* the page's order on the first load with a token: pull (GET state), merge, send the queue, then POST the merged state */
  const first=await route('/api/practice/state','GET',null,me,env);
  assert.deepEqual(first.state,{},'a new account is empty');
  let local=Object.assign({...guest},T.accountMerge(guest,first.state));
  let skills=T.skillsMerge({'mechanics/energy':{unit:'mechanics/energy',rating:1320,n:1,right_n:1}},first.skills);
  assert.equal(skills['mechanics/energy'].n,1,'an empty account does not wipe the guest’s ratings');
  const sent=await route('/api/practice/attempts','POST',{attempts:queue},me,env);
  assert.equal(sent.recorded,2);
  const saved=await route('/api/practice/state','POST',{state:local},me,env);
  for(const k of ['xp','days','level','solved','wrong','bank','contest'])assert.deepEqual(saved.state[k],guest[k],k+' carried over');
  assert.equal(saved.state.profile.region,'kr');
  /* the account now holds it: a second browser (empty) gets it all back */
  const again=await route('/api/practice/state','GET',null,me,env);
  const other=T.accountMerge({},again.state);
  assert.equal(other.xp,120);assert.deepEqual(other.solved,guest.solved);
  assert.deepEqual(T.skillsMerge({},again.skills)['mechanics/energy'].n,1);
  /* the browser's rule and the server's agree */
  const a={xp:5,days:['2027-01-01'],solved:{x:'u'},level:{u:2}},b={xp:9,days:['2027-01-02'],solved:{y:'v'},level:{u:3}};
  for(const k of ['xp','days','solved','level'])assert.deepEqual(T.accountMerge(a,b)[k],mergeState(a,b)[k],k);
});

test('the page sends the two grading steps and an appeal, and keeps drafts in IndexedDB',()=>{
  const js=read('practice.js');
  assert.match(js,/step:'read',item:/);assert.match(js,/step:'grade',read_id:/);
  assert.match(js,/\/api\/learn\/grade\/appeal'/);assert.match(js,/\/api\/learn\/grade\/appeals\/mine/);
  assert.match(js,/indexedDB\.open\('hlPracticeDrafts'/);assert.match(js,/withIntro\(unit,next,home\)/);
  assert.match(js,/addEventListener\('storage'/);
  for(const k of ['wReadTitle','wLowConf','apBtn','apMine','skPause','dResume','dDrop','icStart','icSkip']){
    assert.match(js,new RegExp(k+":'[^']+'[\\s\\S]*"+k+":'[^']+'"),k+' in both languages');
  }
});
