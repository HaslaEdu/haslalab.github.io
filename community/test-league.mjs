import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createPracticeRouter} from './src/practice-progress.js';
import {createGradeRouter} from './src/practice-grade.js';
import {createLearnRouter} from './src/learn-services.js';
import {createLearnerRouter} from './src/learner-profile.js';
import {createLeagueRouter, awardLeagueXp, closeLeagueWeeks, groupOutcomes, weekOf, dayOf, weekEnds, nextWeek, daysLeft, baseXp, attemptXp, gradedXp,
  LEAGUE_TIERS, MASTER, GROUP_SIZE, DAILY_COUNTED, leagueDeletion, ensureLeagueSchema, goalBonus, GOAL_MIN, GOAL_MAX, hintMult} from './src/league.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
/* Monday 2026-11-23 10:00 KST */
const MONDAY=Date.parse('2026-11-23T01:00:00Z')/1000;
function setup(){
  const db=new DatabaseSync(':memory:');
  const D1={async batch(s){const out=[];for(const x of s)out.push(await x.all());return out;},prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{last_row_id:Number(r.lastInsertRowid)}};}};}};
  db.exec('CREATE TABLE users (id INTEGER PRIMARY KEY, nickname TEXT, avatar TEXT, deleted INTEGER NOT NULL DEFAULT 0)');
  for(let i=1;i<=120;i++)db.prepare('INSERT INTO users(id,nickname) VALUES(?,?)').run(i,'member'+i);
  let t=MONDAY;
  const deps={HttpError:H,bad,now:()=>t,clientIp:()=>'1.2.3.4',needUser:u=>{if(!u)throw new H(401,'login_required');return u;},limit:async()=>{}};
  const vision=async()=>({raw:{transcript:'$v=9.9$',legible:true,items:[{id:'a',got:3},{id:'b',got:3},{id:'c',got:1}],feedback:'Good.'}});
  const env={DB:D1,AI:{async run(){return{response:'{"items":[{"id":"a","desc":"energy","pts":3},{"id":"b","desc":"setup","pts":3},{"id":"c","desc":"final","pts":4}]}'};}},GEMINI_API_KEY:'test-dummy'};
  const practice=createPracticeRouter(deps),grade=createGradeRouter({...deps,vision}),learn=createLearnRouter(deps),league=createLeagueRouter(deps),learner=createLearnerRouter(deps);
  const route=async(p,m,b,me,query='')=>{
    const url=new URL('https://x'+p+query),req={url:url.href,json:async()=>b};
    for(const r of [()=>practice(p,m,b,me,env),()=>grade(p,m,b,me,req,env),()=>league(p,m,b,me,req,env,url),()=>learner(p,m,b,me,req,env),()=>learn(p,m,b,me,req,env)]){const out=await r();if(out!==undefined)return out;}
  };
  return {db,env,route,set:s=>{t=s;},tick:s=>{t+=s;},now:()=>t};
}
const user=id=>({id});
const attempt=(item_id,over={})=>({item_id,mode:'track',unit:'mechanics/energy',step:5,result:'right',...over});
const xpOf=(db,id,week)=>db.prepare('SELECT xp FROM league_xp WHERE user_id=? AND week=?').get(id,week)?.xp??0;

test('the week runs Monday 00:00 to Sunday 24:00 Korean time',()=>{
  assert.equal(weekOf(MONDAY),'2026-11-23');
  assert.equal(weekOf(Date.parse('2026-11-22T14:59:59Z')/1000),'2026-11-16','Sunday 23:59:59 KST is the old week');
  assert.equal(weekOf(Date.parse('2026-11-22T15:00:00Z')/1000),'2026-11-23','Monday 00:00 KST starts the new one');
  assert.equal(weekEnds('2026-11-23'),Date.parse('2026-11-29T15:00:00Z')/1000);
  assert.equal(nextWeek('2026-11-30'),'2026-12-07');
  assert.equal(dayOf(Date.parse('2026-11-23T15:30:00Z')/1000),'2026-11-24');
  assert.equal(daysLeft(MONDAY),7);assert.equal(daysLeft(Date.parse('2026-11-29T14:00:00Z')/1000),1);
  assert.equal(LEAGUE_TIERS.length,10);assert.equal(LEAGUE_TIERS[0],'bronze');assert.equal(LEAGUE_TIERS[MASTER],'master');
});

test('the XP rule is the page\'s: 10 + 2 x step, competitions 20 + 5 x step, graded bands 1, 0.5, 0.15',()=>{
  assert.equal(baseXp('track',5),20);assert.equal(baseXp('contest',4),40);assert.equal(baseXp('exam',99),30,'steps are clamped');
  assert.equal(attemptXp(attempt('a')),20);assert.equal(attemptXp(attempt('a',{result:'solved'})),10,'a self-marked solve earns half');
  for(const result of ['wrong','missed','skip','place'])assert.equal(attemptXp(attempt('a',{result})),0,result);
  assert.equal(gradedXp('track',5,'pass'),20);assert.equal(gradedXp('track',5,'partial'),10);assert.equal(gradedXp('track',5,'retry'),3);
  assert.equal(gradedXp('contest',2,'pass'),30);assert.equal(gradedXp('archive',5,'pass'),0);
});

test('league XP comes only from recorded attempts and gradings: right ones, once per problem a day, at most 200 a day',async()=>{
  const {route,db,tick}=setup(),me=user(7),week='2026-11-23';
  const r=await route('/api/practice/attempts','POST',{attempts:[attempt('kr-1'),attempt('kr-2',{result:'wrong'}),attempt('kr-3',{mode:'contest',unit:'contest/ipho',step:2}),attempt('kr-1')]},me);
  assert.equal(r.league_xp,20+30,'the repeat of kr-1 and the wrong answer earn nothing');
  assert.equal(xpOf(db,7,week),50);
  await route('/api/practice/state','POST',{state:{xp:999999}},me);
  assert.equal(xpOf(db,7,week),50,'the page\'s own XP number is never read');
  assert.equal((await route('/api/practice/attempts','POST',{attempts:[attempt('kr-1')]},me)).league_xp,0,'the same problem later the same day');
  /* a server-graded written answer: 7 of 10 marks is a pass, step 4 track item: 18 XP */
  const jpeg='data:image/jpeg;base64,'+Buffer.concat([Buffer.from([0xff,0xd8,0xff,0xe0]),Buffer.alloc(200)]).toString('base64');
  const g=await route('/api/learn/grade','POST',{item:{id:'ap1-u1-001',source:'track',q:'A ball falls 5 m. Speed?',answer:'9.9 m/s',sol:'v=sqrt(2gh)',unit:'mechanics/energy',step:4},pages:[jpeg],level:'L1',lang:'en'},me);
  assert.equal(g.band,'pass');assert.equal(g.league_xp,18);
  const solvedAfter=await route('/api/practice/attempts','POST',{attempts:[attempt('ap1-u1-001',{step:4,result:'solved'})]},me);
  assert.equal(solvedAfter.league_xp,0,'the attempt the page records after a passed grading adds nothing more');
  assert.equal(xpOf(db,7,week),68);
  /* the daily cap */
  const many=Array.from({length:250},(_,i)=>attempt('cap-'+i,{step:1}));
  let gained=0;for(let i=0;i<many.length;i+=50)gained+=(await route('/api/practice/attempts','POST',{attempts:many.slice(i,i+50)},me)).league_xp;
  assert.equal(gained,(DAILY_COUNTED-3)*12,'200 problems a day in all (kr-1, kr-3 and the graded one already counted)');
  tick(86400);
  assert.equal((await route('/api/practice/attempts','POST',{attempts:[attempt('kr-1')]},me)).league_xp,20,'a new day counts again');
  assert.equal(await awardLeagueXp({DB:null},7,[],0),0);
});

test('members join groups of 30 of their tier in join order; /me shows the group and the zones',async()=>{
  const {route,env,now}=setup(),week=weekOf(now());
  for(let id=1;id<=31;id++)await awardLeagueXp(env,id,[{item_id:'p',xp:id}],now()+id);
  const me=await route('/api/league/me','GET',null,user(31));
  assert.equal(me.joined,true);assert.equal(me.tier_key,'bronze');assert.equal(me.group_id,week+'/bronze/2','the 31st member opens a second group');
  assert.equal(me.standings.length,1);assert.equal(me.days_left,7);
  const first=await route('/api/league/me','GET',null,user(5));
  assert.equal(first.standings.length,GROUP_SIZE);assert.equal(first.standings[0].nickname,'member30');assert.equal(first.standings[0].zone,'up');
  assert.equal(first.standings.find(s=>s.me).rank,26);
  assert.equal(first.standings.at(-1).zone,'stay','no demotion out of Bronze');
  assert.equal(first.zones.up,7);assert.equal(first.zones.down,0);
  assert.ok(!('user_id' in first.standings[0]),'no member ids leave the server');
  const guest=await route('/api/league/me','GET',null,user(99));
  assert.equal(guest.joined,false);assert.deepEqual(guest.standings,[]);
  await assert.rejects(route('/api/league/me','GET',null,null),e=>e.code==='login_required');
});

test('the week closes once: ranks 1-7 up, the last 5 down, Master 1-3 reborn in Bronze',async()=>{
  const {route,env,db,set,now}=setup(),week=weekOf(now());
  /* a Gold group of 12 and a Master group of 10 */
  await ensureLeagueSchema(env);
  for(let id=1;id<=12;id++)db.prepare('INSERT INTO league_state(user_id,tier,rebirths,total_xp,updated_at) VALUES(?,?,0,0,0)').run(id,2);
  for(let id=1;id<=12;id++)await awardLeagueXp(env,id,[{item_id:'x',xp:id}],now()+id);
  for(let id=21;id<=30;id++){db.prepare('INSERT INTO league_state(user_id,tier,rebirths,total_xp,updated_at) VALUES(?,?,?,0,0)').run(id,MASTER,id===21?2:0);await awardLeagueXp(env,id,[{item_id:'x',xp:id}],now()+id);}
  const master=await route('/api/league/me','GET',null,user(30));
  assert.deepEqual(master.zones,{up:0,reborn:3,down:5});
  assert.deepEqual(master.standings.map(s=>s.zone),['reborn','reborn','reborn','stay','stay','down','down','down','down','down']);
  assert.deepEqual(await closeLeagueWeeks(env,{now:now()}),{week:null},'nothing closes during the week');
  /* member 12 plays a little on Monday before the cron runs */
  set(weekEnds(week)+30);
  await awardLeagueXp(env,12,[{item_id:'y',xp:5}],now());
  let r;do r=await closeLeagueWeeks(env,{now:now(),groups:1});while(r.week&&!r.closed);
  assert.equal(r.week,week);
  const state=id=>db.prepare('SELECT tier,rebirths FROM league_state WHERE user_id=?').get(id);
  const outcome=id=>db.prepare('SELECT outcome,rank FROM league_results WHERE user_id=? AND week=?').get(id,week);
  for(let id=12;id>=6;id--){assert.equal(outcome(id).outcome,'up',String(id));assert.equal(state(id).tier,3);}
  for(let id=5;id>=1;id--){assert.equal(outcome(id).outcome,'down',String(id));assert.equal(state(id).tier,1);}
  for(const id of [30,29,28]){assert.equal(outcome(id).outcome,'reborn');assert.deepEqual({...state(id)},{tier:0,rebirths:1});}
  assert.equal(outcome(27).outcome,'stay');assert.equal(state(27).tier,MASTER);
  for(const id of [25,21]){assert.equal(outcome(id).outcome,'down');assert.equal(state(id).tier,MASTER-1);}
  assert.equal(state(21).rebirths,2,'a demotion keeps the rebirths');
  assert.equal(db.prepare('SELECT tier FROM league_xp WHERE user_id=12 AND week=?').get(nextWeek(week)).tier,3,'an early player of the new week moves to the new tier');
  /* idempotent: running again changes nothing */
  const before=JSON.stringify(db.prepare('SELECT * FROM league_state ORDER BY user_id').all());
  assert.deepEqual(await closeLeagueWeeks(env,{now:now()+60}),{week:null});
  db.prepare('DELETE FROM league_weeks').run();
  await closeLeagueWeeks(env,{now:now()+7*86400});   /* even with the marker gone, results and tiers do not move twice */
  assert.equal(JSON.stringify(db.prepare('SELECT * FROM league_state ORDER BY user_id').all()),before);
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM league_results').get().n,22);
  const hist=await route('/api/league/history','GET',null,user(30));
  assert.equal(hist.weeks.length,1);assert.equal(hist.weeks[0].outcome,'reborn');assert.equal(hist.weeks[0].tier_key,'master');
});

test('the pure rule for small and large groups',()=>{
  assert.deepEqual(groupOutcomes(0,[5,4,3]).map(o=>o.outcome),['up','up','up']);
  assert.deepEqual(groupOutcomes(4,Array.from({length:30},(_,i)=>30-i)).map(o=>o.outcome),[...Array(7).fill('up'),...Array(18).fill('stay'),...Array(5).fill('down')]);
  assert.deepEqual(groupOutcomes(4,[9,8,7,6,5,4,3,2,1]).map(o=>o.outcome),[...Array(7).fill('up'),'down','down'],'promotion comes first in a small group');
  assert.deepEqual(groupOutcomes(MASTER,[3,2,1]).map(o=>o.outcome),['reborn','reborn','reborn']);
  assert.equal(groupOutcomes(3,[5,0])[1].outcome,'stay','0 XP neither moves nor counts');
});

test('the final ranking: rebirths, then tier, then total league XP; public, 100 a page, with flags',async()=>{
  const {route,env,db,now}=setup();
  await ensureLeagueSchema(env);
  const put=(id,tier,rebirths,total)=>db.prepare('INSERT INTO league_state(user_id,tier,rebirths,total_xp,updated_at) VALUES(?,?,?,?,0) ON CONFLICT(user_id) DO UPDATE SET tier=excluded.tier,rebirths=excluded.rebirths,total_xp=excluded.total_xp').run(id,tier,rebirths,total);
  put(1,9,0,90000);put(2,0,1,50);put(3,3,1,900);put(4,3,1,1200);put(5,8,0,99999);put(6,0,0,0);
  for(let id=10;id<=114;id++)put(id,0,0,id);
  db.prepare('UPDATE users SET deleted=1 WHERE id=114').run();
  await route('/api/me/learner','PUT',{country:'IN',daily_goal:15},user(4));
  const p1=await route('/api/league/ranking','GET',null,null,'?page=1');
  assert.deepEqual(p1.rows.slice(0,5).map(r=>r.nickname),['member4','member3','member2','member1','member5']);
  assert.equal(p1.rows[0].country,'IN');assert.equal(p1.rows[0].tier_key,'platinum');assert.equal(p1.rows[0].rebirths,1);
  assert.equal(p1.rows.length,100);assert.equal(p1.total,5+104,'no 0 XP members, no deleted accounts');
  const p2=await route('/api/league/ranking','GET',null,user(10),'?page=2');
  assert.equal(p2.rows.length,9);assert.equal(p2.rows[0].rank,101);assert.equal(p2.mine,109);
  await assert.rejects(route('/api/league/ranking','GET',null,null,'?page=0'),e=>e.code==='bad_page');
  for(const s of leagueDeletion(env,4))await s.run();
  assert.equal((await route('/api/league/ranking','GET',null,null,'?page=1')).rows[0].nickname,'member3','a deleted member leaves the ranking');
});

test('profile pictures: the group table and the ranking carry the avatar key, never anything else',async()=>{
  const {route,env,db,now}=setup();
  db.prepare('UPDATE users SET avatar=? WHERE id=1').run('Abc_def-1234');
  db.prepare('UPDATE users SET avatar=? WHERE id=2').run('../../etc/passwd');
  for(const id of [1,2,3])await awardLeagueXp(env,id,[{item_id:'p',xp:10+id}],now()+id);
  const me=await route('/api/league/me','GET',null,user(1));
  const by=Object.fromEntries(me.standings.map(r=>[r.nickname,r]));
  assert.equal(by.member1.avatar,'Abc_def-1234');assert.equal(by.member2.avatar,null,'a malformed key is dropped');assert.equal(by.member3.avatar,null);
  const rank=await route('/api/league/ranking','GET',null,null,'?page=1');
  assert.equal(rank.rows.find(r=>r.nickname==='member1').avatar,'Abc_def-1234');
  assert.equal(rank.rows.find(r=>r.nickname==='member2').avatar,null);
});

test('the goal bonus: 5 x goal + 2 x goal^1.3, rounded; bigger goals pay more in all and per problem',()=>{
  assert.deepEqual([GOAL_MIN,GOAL_MAX],[1,50]);
  assert.equal(goalBonus(1),7);assert.equal(goalBonus(10),90);assert.equal(goalBonus(30),316);assert.equal(goalBonus(50),573);
  for(let g=2;g<=50;g++){assert.ok(goalBonus(g)>goalBonus(g-1),String(g));assert.ok(goalBonus(g)/g>=goalBonus(g-1)/(g-1),'per problem '+g);}
  for(const g of [0,51,-3,NaN,'x'])assert.equal(goalBonus(g),0,String(g));
});

test('reaching the daily goal pays its bonus once, from the problems the server counted',async()=>{
  const {route,db,tick}=setup(),me=user(8),week='2026-11-23';
  await route('/api/me/learner','PUT',{country:'KR',daily_goal:3},me);
  let r=await route('/api/practice/attempts','POST',{attempts:[attempt('g-1'),attempt('g-2',{result:'wrong'}),attempt('g-1')]},me);
  assert.equal(r.goal_bonus,0);assert.equal(r.league_today.counted,1,'a wrong answer and a repeat do not count');assert.equal(r.league_today.goal,3);
  r=await route('/api/practice/attempts','POST',{attempts:[attempt('g-2'),attempt('g-3')]},me);
  assert.equal(r.goal_bonus,goalBonus(3));assert.equal(r.league_xp,40+goalBonus(3),'the bonus is part of the league XP');
  assert.equal(xpOf(db,8,week),60+goalBonus(3));
  assert.equal(db.prepare('SELECT total_xp FROM league_state WHERE user_id=8').get().total_xp,60+goalBonus(3));
  let today=(await route('/api/league/me','GET',null,me)).today;
  assert.deepEqual({counted:today.counted,goal:today.goal,earned:today.earned,earned_xp:today.earned_xp,pending:today.pending},{counted:3,goal:3,earned:true,earned_xp:goalBonus(3),pending:false});
  /* more problems, and lowering the goal after reaching it: no second bonus */
  r=await route('/api/practice/attempts','POST',{attempts:[attempt('g-4')]},me);assert.equal(r.goal_bonus,0);assert.equal(r.league_xp,20);
  await route('/api/me/learner','PUT',{country:'KR',daily_goal:1},me);
  r=await route('/api/practice/attempts','POST',{attempts:[attempt('g-5')]},me);assert.equal(r.goal_bonus,0);
  today=(await route('/api/league/me','GET',null,me)).today;
  assert.equal(today.goal,3,'today keeps the goal in effect');assert.equal(today.next_goal,1,'the new goal counts from tomorrow');
  assert.equal(xpOf(db,8,week),60+goalBonus(3)+40);
  /* the next day: the new goal, a new bonus */
  tick(86400);
  r=await route('/api/practice/attempts','POST',{attempts:[attempt('g-1')]},me);
  assert.equal(r.goal_bonus,goalBonus(1));assert.equal(r.league_today.goal,1);
});

test('the goal in effect is the one saved before the day\'s first counted problem: lowering it mid-day does not help',async()=>{
  const {route,tick}=setup(),me=user(9);
  await route('/api/me/learner','PUT',{country:'IN',daily_goal:10},me);
  await route('/api/practice/attempts','POST',{attempts:[attempt('h-1'),attempt('h-2')]},me);
  await route('/api/me/learner','PUT',{country:'IN',daily_goal:2},me);
  let r=await route('/api/practice/attempts','POST',{attempts:[attempt('h-3')]},me);
  assert.equal(r.goal_bonus,0,'3 counted, the goal in effect is still 10');assert.equal(r.league_today.goal,10);
  r=await route('/api/practice/attempts','POST',{attempts:Array.from({length:6},(_,i)=>attempt('h-x'+i))},me);
  assert.equal(r.goal_bonus,0,'9 counted');
  r=await route('/api/practice/attempts','POST',{attempts:[attempt('h-last')]},me);
  assert.equal(r.goal_bonus,goalBonus(10),'the tenth');
  /* raising it mid-day does not move today's target either */
  tick(86400);
  await route('/api/practice/attempts','POST',{attempts:[attempt('h-1')]},me);
  await route('/api/me/learner','PUT',{country:'IN',daily_goal:40},me);
  r=await route('/api/practice/attempts','POST',{attempts:[attempt('h-2')]},me);
  assert.equal(r.goal_bonus,goalBonus(2),'the goal saved before the first problem (2)');
});

test('the goal bonus: no saved goal pays nothing; two requests crossing the goal at once pay it once',async()=>{
  const {route,env,db,now}=setup();
  let r=await route('/api/practice/attempts','POST',{attempts:Array.from({length:12},(_,i)=>attempt('n-'+i))},user(10));
  assert.equal(r.goal_bonus,0);assert.equal(r.league_today.goal,null);
  const today=(await route('/api/league/me','GET',null,user(10))).today;
  assert.equal(today.goal,null);assert.equal(today.pending,false);assert.equal(today.counted,12);
  await route('/api/me/learner','PUT',{country:'FR',daily_goal:2},user(11));
  await awardLeagueXp(env,11,[{item_id:'a',xp:10}],now());
  const [x,y]=await Promise.all([awardLeagueXp(env,11,[{item_id:'b',xp:10}],now()),awardLeagueXp(env,11,[{item_id:'c',xp:10}],now())]);
  assert.equal(x+y,20+goalBonus(2),'one of the two carries the bonus');
  assert.equal(xpOf(db,11,weekOf(now())),30+goalBonus(2));
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM league_goal_days WHERE user_id=11 AND bonus>0').get().n,1);
  /* the day rows go with the account and with the closed week */
  for(const st of leagueDeletion(env,11))await st.run();
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM league_goal_days WHERE user_id=11').get().n,0);
});

test('hints: 25 % off the problem\'s XP per hint, never below 25 %; the server\'s own hint records count whatever the answer says',async()=>{
  assert.deepEqual([0,1,2,3,4,9].map(hintMult),[1,0.75,0.5,0.25,0.25,0.25]);
  assert.equal(attemptXp(attempt('a',{hints:1})),15);assert.equal(attemptXp(attempt('a',{hints:2,result:'solved'})),5);
  assert.equal(gradedXp('track',5,'pass',2),10);assert.equal(gradedXp('track',5,'retry',3),1);
  const {route,db}=setup(),me=user(9),week='2026-11-23';
  /* hints shown (recorded at once), then an answer that claims none: the recorded two still count */
  await route('/api/practice/attempts','POST',{attempts:[attempt('ap1-u1-001',{result:'hint',ctx:'daily',level:'L1'}),attempt('ap1-u1-001',{result:'hint',ctx:'daily',level:'L1'})]},me);
  assert.equal(db.prepare("SELECT COUNT(*) n FROM sqlite_master WHERE name='league_xp'").get().n?xpOf(db,9,week):0,0,'a hint earns nothing');
  const r=await route('/api/practice/attempts','POST',{attempts:[attempt('ap1-u1-001',{ctx:'daily',level:'L1',hints:0})]},me);
  assert.equal(r.league_xp,10,'20 XP × 50 % for two hints');
  /* in the same batch too, and the answer's own count wins when it is higher */
  const r2=await route('/api/practice/attempts','POST',{attempts:[attempt('ap1-u1-002',{result:'hint'}),attempt('ap1-u1-002')]},me);
  assert.equal(r2.league_xp,15);
  const r3=await route('/api/practice/attempts','POST',{attempts:[attempt('ap1-u1-003',{hints:3})]},me);
  assert.equal(r3.league_xp,5);
  /* "I can't solve this" earns nothing; the goal still counts only right or solved problems */
  assert.equal((await route('/api/practice/attempts','POST',{attempts:[attempt('ap1-u1-004',{result:'giveup',ctx:'daily',level:'L1'})]},me)).league_xp,0);
  assert.equal(xpOf(db,9,week),30);
});
