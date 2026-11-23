const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const T=require('../practice-tools.js');
const root=path.join(__dirname,'..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');

test('review queue: a miss or a hinted answer is due the next day; right answers on review step through 3, 7, 21 days, then leave',()=>{
  assert.deepEqual(T.REVIEW_DAYS,[1,3,7,21]);
  let r=T.reviewUpdate({},'ap1-u1-001','wrong','2026-11-23',{k:'track',u:'mechanics/kinematics'},100);
  assert.deepEqual(r['ap1-u1-001'],{k:'track',u:'mechanics/kinematics',box:0,due:'2026-11-24',at:100});
  assert.deepEqual(T.dueIds(r,'2026-11-23'),[]);assert.deepEqual(T.dueIds(r,'2026-11-24'),['ap1-u1-001']);
  /* right before it is due: nothing changes */
  assert.deepEqual(T.reviewUpdate(r,'ap1-u1-001','right','2026-11-23'),r);
  r=T.reviewUpdate(r,'ap1-u1-001','right','2026-11-24',null,200);
  assert.equal(r['ap1-u1-001'].box,1);assert.equal(r['ap1-u1-001'].due,'2026-11-27');assert.equal(r['ap1-u1-001'].u,'mechanics/kinematics');
  r=T.reviewUpdate(r,'ap1-u1-001','right','2026-11-27');assert.equal(r['ap1-u1-001'].due,'2026-12-04');
  r=T.reviewUpdate(r,'ap1-u1-001','right','2026-12-05');assert.equal(r['ap1-u1-001'].box,3);assert.equal(r['ap1-u1-001'].due,'2026-12-26');
  /* a miss at any box starts over */
  const back=T.reviewUpdate(r,'ap1-u1-001','wrong','2026-12-26');assert.equal(back['ap1-u1-001'].box,0);assert.equal(back['ap1-u1-001'].due,'2026-12-27');
  const hinted=T.reviewUpdate(r,'ap1-u1-001','hinted','2026-12-26');assert.equal(hinted['ap1-u1-001'].box,0);
  r=T.reviewUpdate(r,'ap1-u1-001','right','2026-12-26');assert.ok(!('ap1-u1-001' in r),'graduates after 21 days');
  /* a right answer on a problem that was never in the queue adds nothing */
  assert.deepEqual(T.reviewUpdate({},'x','right','2026-11-23'),{});
  assert.equal(T.addDays('2026-12-31',1),'2027-01-01');assert.equal(T.addDays('2028-02-28',1),'2028-02-29');
});

test('suggested time: 1.5 min for the easiest step up to 8 min for the hardest; an item’s own time wins',()=>{
  assert.equal(T.paceFor({s:2}),90);assert.equal(T.paceFor({s:10}),480);assert.equal(T.paceFor({s:7}),300);
  assert.equal(T.paceFor({s:4,sec:85}),85);assert.equal(T.paceFor({}),120);
  for(let s=2;s<10;s++)assert.ok(T.PACE[s+1]>=T.PACE[s]);
  assert.equal(T.clock(75),'1:15');assert.equal(T.clock(480),'8:00');
});

const pool=[
  {id:'ap1-a',from:'track:ap1',kind:'track',u:'mechanics/kinematics',s:3,type:'mc'},
  {id:'ap1-b',from:'track:ap1',kind:'track',u:'mechanics/kinematics',s:5,type:'num'},
  {id:'ap1-c',from:'track:ap1',kind:'track',u:'em/circuits',s:4,type:'mc'},
  {id:'k1',from:'calc',u:'mechanics/kinematics',s:2},
  {id:'k2',from:'calc',u:'waves/sound',s:6},
  {id:'opho-1~1',from:'contest',kind:'contest',c:'opho',s:7,year:2021},
  {id:'opho-2~1',from:'contest',kind:'contest',c:'opho',s:7,year:2024},
  {id:'wopho-1~1',from:'contest',kind:'contest',c:'wopho',s:8,year:2012}
];
const canType=i=>i.type==='num'||i.id==='k2',hasChoices=i=>i.type!=='num'&&i.kind!=='contest';
const ids=list=>list.map(i=>i.id).sort();

test('set builder: source, topics, step range, format, competition and years each narrow the pool',()=>{
  const m=o=>ids(T.matchSet(pool,{min:1,max:10,...o},canType,hasChoices));
  assert.equal(m({source:'all'}).length,8);
  assert.deepEqual(m({source:'track:ap1'}),['ap1-a','ap1-b','ap1-c']);
  assert.deepEqual(m({source:'all',units:['mechanics/kinematics']}),['ap1-a','ap1-b','k1'],'a topic filter leaves out competition problems');
  assert.deepEqual(m({source:'all',min:4,max:6}),['ap1-b','ap1-c','k2']);
  assert.deepEqual(m({source:'track:ap1',format:'typed'}),['ap1-b']);
  assert.deepEqual(m({source:'track:ap1',format:'choice'}),['ap1-a','ap1-c']);
  assert.deepEqual(m({source:'contest',contest:'opho'}),['opho-1~1','opho-2~1']);
  assert.deepEqual(m({source:'contest',yearMin:2020,yearMax:2022}),['opho-1~1']);
  assert.deepEqual(m({source:'contest',format:'typed'}),['opho-1~1','opho-2~1','wopho-1~1'],'format does not apply to self-marked problems');
});

test('set builder: takes the count asked for, unsolved and not recently seen first, and reports how many match',()=>{
  const now=1_800_000_000,day=86400;
  const ctx={now,rand:()=>0.5,recent:{'ap1-a':now-2*day,'k1':now-40*day},solved:{'ap1-c':'em/circuits'},canType,hasChoices};
  const r=T.buildSet(pool,{source:'all',count:5,units:[],min:1,max:10},ctx);
  assert.equal(r.matches,8);assert.equal(r.items.length,5);
  assert.ok(!r.items.some(i=>i.id==='ap1-a'),'seen two days ago goes last');
  assert.ok(!r.items.some(i=>i.id==='ap1-c'),'solved goes after unsolved');
  const all=T.buildSet(pool,{source:'all',count:20,units:[],min:1,max:10},ctx).items.map(i=>i.id);
  assert.equal(all.length,8);assert.equal(all[all.length-1],'ap1-a');assert.equal(all[all.length-2],'ap1-c');
  /* shuffled: different random draws give different orders */
  let k=0;const seq=[.9,.1,.8,.2,.7,.3,.6,.4];
  const a=T.buildSet(pool,{source:'all',count:8},{rand:()=>seq[k++%8]}).items.map(i=>i.id);
  k=3;const b=T.buildSet(pool,{source:'all',count:8},{rand:()=>seq[k++%8]}).items.map(i=>i.id);
  assert.notDeepEqual(a,b);assert.deepEqual([...a].sort(),[...b].sort());
});

test('backup: the export carries the review queue and saved problems; import rejects files that are not backups',()=>{
  const saved={xp:120,days:['2026-11-20'],solved:{a:'u'},queue:[{item_id:'a'}],review:{a:{k:'exam',u:'u',box:1,due:'2026-11-25',at:5}},later:{b:{k:'track',at:9,t:'B'}}};
  const file=T.exportOf(saved,'2026-11-23T00:00:00Z');
  assert.equal(file.app,'haslalab-practice');assert.equal(file.version,1);
  assert.ok(!('queue' in file.state),'unsent attempts stay out of the file');
  assert.deepEqual(file.state.review,saved.review);assert.deepEqual(file.state.later,saved.later);
  const back=T.validateBackup(JSON.stringify(file));assert.ok(back.ok);assert.deepEqual(back.state.review,saved.review);
  assert.deepEqual(T.validateBackup('{nope'),{ok:false,error:'not_json'});
  assert.deepEqual(T.validateBackup({hello:1}),{ok:false,error:'not_backup'});
  assert.deepEqual(T.validateBackup({app:'haslalab-practice',version:9,state:{}}),{ok:false,error:'version'});
  assert.deepEqual(T.validateBackup({app:'haslalab-practice',version:1,state:{xp:'lots',days:'x'}}),{ok:false,error:'empty'});
  /* entries with the wrong shape are dropped, the rest kept */
  const v=T.validateBackup({app:'haslalab-practice',version:1,state:{xp:-4,days:['2026-11-01','soon'],level:{u:3,v:'high'},review:{ok:{box:2,due:'2026-12-01'},bad:{box:9,due:'2026-12-01'},bad2:{box:1,due:'tomorrow'}},skills:{u:{rating:'x',n:1}}}});
  assert.ok(v.ok);assert.deepEqual(v.state.days,['2026-11-01']);assert.deepEqual(v.state.level,{u:3});assert.deepEqual(Object.keys(v.state.review),['ok']);
  assert.ok(!('xp' in v.state));assert.deepEqual(v.state.skills,{});
});

test('backup: merging keeps both sides and the newer record for each item',()=>{
  const local={xp:100,days:['2026-11-20'],solved:{a:'u'},wrong:{c:50},level:{u:3},
    skills:{u:{unit:'u',rating:1300,n:4,right_n:2,last_at:100}},review:{a:{box:1,due:'2026-11-25',at:100},b:{box:0,due:'2026-11-24',at:300}},later:{x:{at:10}},recent:{a:100},
    contest:{done:{p:0}},profile:{region:'kr',at:50},queue:[{item_id:'q'}]};
  const file={xp:80,days:['2026-11-21'],solved:{b:'v'},wrong:{c:70},level:{u:5},
    skills:{u:{unit:'u',rating:1400,n:9,right_n:7,last_at:200},w:{unit:'w',rating:1200,n:1,right_n:0,last_at:5}},review:{a:{box:2,due:'2026-11-30',at:200},b:{box:3,due:'2026-12-20',at:200}},later:{y:{at:20}},recent:{a:50,b:60},
    contest:{done:{p:1}},profile:{region:'us',at:40}};
  const m=T.mergeBackup(local,file);
  assert.equal(m.xp,100);assert.deepEqual(m.days,['2026-11-20','2026-11-21']);
  assert.deepEqual(m.solved,{a:'u',b:'v'});assert.equal(m.wrong.c,70);assert.equal(m.level.u,5);
  assert.equal(m.skills.u.rating,1400,'newer last_at wins');assert.ok(m.skills.w);
  assert.equal(m.review.a.box,2,'newer review entry wins');assert.equal(m.review.b.box,0,'the local entry is newer here');
  assert.deepEqual(Object.keys(m.later).sort(),['x','y']);assert.deepEqual(m.recent,{a:100,b:60});
  assert.equal(m.contest.done.p,1);assert.equal(m.profile.region,'kr','the newer profile stays');
  assert.deepEqual(m.queue,[{item_id:'q'}],'fields the file does not carry are untouched');
});

test('the page loads the helpers, keeps review and saved problems out of the account sync, and has the new tabs',()=>{
  const js=read('practice.js'),html=read('practice.html');
  assert.ok(html.indexOf('practice-tools.js')>0&&html.indexOf('practice-tools.js')<html.indexOf('practice.js?'),'the helpers load before the page script');
  const stateOf=/const stateOf=\(\)=>\(\{([^)]*)\}\);/.exec(js)[1];
  assert.doesNotMatch(stateOf,/review|later|recent/,'the server keeps only the fields it knows, so these stay local');
  for(const k of ['review','custom'])assert.match(js,new RegExp(`\\['${k}',tr\\('tab${k[0].toUpperCase()+k.slice(1)}'\\)`));
  assert.match(js,/mailto:'\+CONTACT/);assert.match(read('index.html'),/mailto:mgsnew88@naver\.com/);
  /* every new string has Korean and English */
  const keys=['tabReview','tabCustom','report','later','exportP','importP','resetP','cStartSet','avgTime','strike'];
  for(const k of keys){assert.match(js,new RegExp(`(^|[\\s,{])${k}:'[^']*[가-힣]`,'m'),k+' ko');}
  assert.doesNotMatch(js,/seamless|unlock|elevate/i);
});
