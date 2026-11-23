/* Written answers on the practice page: bands and XP, moving on, the unit step-up rule, the study levels' pools and the
   image helpers (all pure functions in practice-tools.js), plus what the page sends and where. */
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const T=require('../practice-tools.js');
const root=path.join(__dirname,'..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');

test('bands: 0.70 and up pass, 0.40–0.69 partial, below 0.40 retry',()=>{
  for(const [f,b] of [[1,'pass'],[0.7,'pass'],[0.6999999999,'pass'],[0.69,'partial'],[0.5,'partial'],[0.4,'partial'],[0.39,'retry'],[0,'retry'],[NaN,'retry'],[undefined,'retry']])assert.equal(T.bandOf(f),b,String(f));
  assert.deepEqual(T.BANDS,['pass','partial','retry']);
});

test('XP: the usual XP of the problem times 1, 0.5 or 0.15; a second grading adds only the difference',()=>{
  assert.equal(T.baseXp({kind:'track',s:5}),20);assert.equal(T.baseXp({s:3}),16);
  assert.equal(T.baseXp({kind:'contest',s:8}),60);assert.equal(T.baseXp({kind:'bank',stars:3}),25);
  assert.equal(T.gradedXp(20,'pass'),20);assert.equal(T.gradedXp(20,'partial'),10);assert.equal(T.gradedXp(20,'retry'),3);
  assert.equal(T.gradedXp(60,'retry'),9);assert.equal(T.gradedXp(4,'retry'),1,'at least 1 XP for handing in');
  assert.equal(T.gradedGain(20,'retry',null),3);assert.equal(T.gradedGain(20,'pass','retry'),17);
  assert.equal(T.gradedGain(20,'partial','pass'),0,'a worse second grading takes nothing away and adds nothing');
});

test('moving on: pass is solved, partial goes to review as hinted, retry waits and goes to review as a miss',()=>{
  assert.deepEqual(T.moveOn('pass'),{solved:true,review:'right',result:'solved',next:true,retry:false});
  assert.deepEqual(T.moveOn('partial'),{solved:false,review:'hinted',result:'missed',next:true,retry:false});
  assert.deepEqual(T.moveOn('retry'),{solved:false,review:'wrong',result:'missed',next:false,retry:true});
  /* the review queue takes the outcomes as they are */
  const r=T.reviewUpdate({},'x',T.moveOn('partial').review,'2026-11-23',{k:'track'},1);assert.equal(r.x.due,'2026-11-24');
  for(const b of T.BANDS)assert.ok(['right','hinted','wrong'].includes(T.moveOn(b).review));
});

test('unit step-up: the last five graded fractions in a unit average 0.60 or more; then the count starts again',()=>{
  let h={},up=0;
  for(const f of [0.9,0.2,0.5,0.6])({hist:h}=T.pushGraded(h,'u',f));
  assert.deepEqual(h.u,[0.9,0.2,0.5,0.6]);
  let r=T.pushGraded(h,'u',0.8);assert.equal(r.up,true,'avg 0.6 over five');assert.deepEqual(r.hist.u,[]);
  r=T.pushGraded(h,'u',0.79);assert.equal(r.up,false,'2.99 / 5 is below 0.60');assert.deepEqual(r.hist.u,[0.9,0.2,0.5,0.6,0.79]);
  h={u:[0.5,0.5,0.5,0.5]};r=T.pushGraded(h,'u',0.99);assert.equal(r.up,false,'0.598 is below 0.60');assert.equal(r.hist.u.length,5);
  r=T.pushGraded(r.hist,'u',0.5);assert.equal(r.up,false,'only the last five count: 0.5, 0.5, 0.5, 0.99, 0.5');assert.equal(r.hist.u.length,5);
  r=T.pushGraded(r.hist,'u',0.7);assert.equal(r.up,true,'0.5, 0.5, 0.99, 0.5, 0.7 → 0.638');
  h={};for(let i=0;i<4;i++){r=T.pushGraded(h,'v',1);h=r.hist;up+=r.up;}assert.equal(up,0,'fewer than five never moves the step');
  assert.deepEqual(T.pushGraded({a:[1]},'b',2).hist,{a:[1],b:[1]},'fractions are clamped to 0..1; other units untouched');
});

test('study levels: four levels with the contract’s pools; problems not in the bank are marked as coming',()=>{
  assert.deepEqual(T.STUDY_LEVELS.map(l=>l.key),['L1','L2','L3','L4']);
  const L=k=>T.levelInfo(k);
  assert.deepEqual(L('L1').tracks,['ap1','ap2','apcm','fma']);assert.equal(L('L1').calc,true);
  assert.deepEqual(L('L2').tracks,['jeem']);
  assert.deepEqual(L('L3').tracks,['usapho']);assert.deepEqual(L('L3').contests,['opho','wopho','physcup','eupho','eotvos']);
  assert.deepEqual(L('L4').contests,['baupc','eupho','physcup']);assert.equal(L('L4').bank,true);
  assert.equal(L('L1').name.ko,'AP · Physics Brawl · F=ma');assert.equal(L('L2').name.ko,'JEE');
  assert.equal(L('L3').name.ko,'올림피아드 (국가 선발 → IPhO·APhO → 전공 수준)');assert.equal(L('L4').name.ko,'대학 물리 (국제 대회 일부 → 학부 전 범위)');
  assert.ok(L('L1').soon.en.includes('Physics Brawl'));assert.ok(L('L3').soon.ko.some(x=>/국가 선발/.test(x)));
  assert.equal(L('L3').written,true);assert.equal(L('L4').written,true);assert.equal(L('L1').written,false);
  assert.equal(T.levelInfo('nope').key,'L1');
  /* every pool key exists in the data */
  const tracks=new Set(JSON.parse(read('practice/tracks.json')).tracks.map(t=>t.key)),contests=new Set(JSON.parse(read('practice/contests.json')).contests.map(c=>c.key));
  for(const l of T.STUDY_LEVELS){for(const k of l.tracks)assert.ok(tracks.has(k),k);for(const k of l.contests)assert.ok(contests.has(k),k);}
  /* inLevel and the set builder's level source */
  const pool=[{id:'a',from:'track:ap1'},{id:'b',from:'track:jeem'},{id:'c',from:'calc'},{id:'d',from:'contest',c:'opho',kind:'contest'},{id:'e',from:'contest',c:'baupc',kind:'contest'},{id:'f',from:'contest',c:'eupho',kind:'contest'},{id:'g',from:'track:usapho'}].map(i=>({...i,s:5}));
  const ids=k=>T.matchSet(pool,{source:'level:'+k}).map(i=>i.id);
  assert.deepEqual(ids('L1'),['a','c']);assert.deepEqual(ids('L2'),['b']);assert.deepEqual(ids('L3'),['d','f','g']);assert.deepEqual(ids('L4'),['e','f']);
  assert.equal(T.inLevel({from:'bank'},'L4'),true);assert.equal(T.inLevel({from:'bank'},'L3'),false);
  /* a first guess from the onboarding answers */
  assert.equal(T.defaultLevel(null),'L1');assert.equal(T.defaultLevel({region:'in'}),'L2');assert.equal(T.defaultLevel({goal:'olympiad',oly:1}),'L3');
  assert.equal(T.defaultLevel({level:'uni'}),'L4');assert.equal(T.defaultLevel({goal:'olympiad',oly:0,region:'kr'}),'L1');
});

test('images: the long side shrinks to 1600 px (never grows), the data URL fits 1.5 MB, the steps get smaller',()=>{
  assert.deepEqual(T.fitSize(4032,3024),{w:1600,h:1200,scale:1600/4032});
  assert.deepEqual(T.fitSize(3000,4000),{w:1200,h:1600,scale:0.4});
  assert.deepEqual(T.fitSize(800,600),{w:800,h:600,scale:1},'small pictures stay as they are');
  assert.deepEqual(T.fitSize(1200,1600,800),{w:600,h:800,scale:0.5});
  assert.equal(T.fitSize(0,0).w,1);
  const steps=T.ENCODE_STEPS;assert.deepEqual(steps[0],[1600,0.8]);
  for(let i=1;i<steps.length;i++)assert.ok(steps[i][0]<=steps[i-1][0]&&steps[i][1]<steps[i-1][1]);
  const ok='data:image/jpeg;base64,'+'A'.repeat(1000);assert.equal(T.pageOk(ok),true);
  assert.equal(T.pageOk('data:image/png;base64,'+'A'.repeat(1000)),false,'JPEG only');
  assert.equal(T.pageOk('data:image/jpeg;base64,'+'A'.repeat(1500001)),false,'over 1.5 MB');
  assert.equal(T.dataUrlBytes(ok),ok.length);assert.equal(T.MAX_PAGES,4);
});

test('the grading request item is cut to the endpoint’s limits',()=>{
  const it=T.gradeItem({id:'x'.repeat(100),source:'contest',q:'q'.repeat(9000),answer:42,sol:'s'.repeat(9000),choices:['a','b'],points:0});
  assert.equal(it.id.length,80);assert.equal(it.source,'contest');assert.equal(it.q.length,8000);assert.equal(it.answer,'42');assert.equal(it.sol.length,8000);
  assert.deepEqual(it.choices,['a','b']);assert.equal(it.points,10);
  assert.equal(T.gradeItem({id:'a',source:'nope',q:'x'}).source,'track');assert.ok(!('choices' in T.gradeItem({id:'a',q:'x',choices:[]})));
});

test('backup keeps graded results, the unit history and the study level',()=>{
  const saved={xp:1,graded:{a:{fraction:0.8,band:'pass',at:5}},gradedHist:{u:[0.5,0.7]},studyLevel:'L3'};
  const back=T.validateBackup(T.exportOf(saved,'2026-11-23T00:00:00Z'));assert.ok(back.ok);
  assert.deepEqual(back.state.graded,saved.graded);assert.deepEqual(back.state.gradedHist,saved.gradedHist);assert.equal(back.state.studyLevel,'L3');
  const v=T.validateBackup({app:'haslalab-practice',version:1,state:{xp:1,graded:{a:{fraction:2,band:'pass',at:1},b:{fraction:0.5,band:'meh',at:1},c:{fraction:0.5,band:'partial',at:1}},studyLevel:'L9'}});
  assert.deepEqual(Object.keys(v.state.graded),['c']);assert.ok(!('studyLevel' in v.state));
  const m=T.mergeBackup({graded:{a:{fraction:0.2,band:'retry',at:10}},studyLevel:'L2'},{graded:{a:{fraction:0.9,band:'pass',at:20},b:{fraction:0.5,band:'partial',at:1}},studyLevel:'L4'});
  assert.equal(m.graded.a.band,'pass');assert.ok(m.graded.b);assert.equal(m.studyLevel,'L2','the level set on this device stays');
});

test('the page sends working to the grading endpoint and reports to the report endpoint, with a pad that does not scroll',()=>{
  const js=read('practice.js'),css=read('practice.css');
  assert.match(js,/API\+'\/api\/learn\/grade'/);assert.match(js,/API\+'\/api\/learn\/report'/);assert.match(js,/\/api\/learn\/reports\/mine/);
  assert.match(js,/accept="\$\{photo\?'image\/\*':'image\/\*,application\/pdf,\.pdf'\}"\$\{photo\?' capture="environment"':''\} multiple/);
  assert.match(js,/r\.status===404\?tr\('wSoon'\)/,'a missing server reads as "not ready"');
  assert.match(css,/\.padcv\{[^}]*touch-action:none/);
  for(const k of ['wTitle','wSend','wSoon','wLogin','bandPass','bandPartial','bandRetry','lvTitle','lvSoon','rQueued'])assert.match(js,new RegExp(`(^|[\\s,{])${k}:'[^']*[가-힣]`,'m'),k+' ko');
  assert.doesNotMatch(js,/seamless|unlock|elevate|delve/i);
});
