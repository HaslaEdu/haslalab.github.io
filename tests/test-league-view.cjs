const test=require('node:test');
const assert=require('node:assert/strict');
const V=require('../league-view.js');
const F=require('../learner-form.js');
const P=require('../learn-path.js');
const fs=require('node:fs'),path=require('node:path'),read=f=>fs.readFileSync(path.join(__dirname,'..',f),'utf8');

const group=(tier,n,zones)=>({tier,rebirths:0,days_left:3,joined:true,xp:40,rank:2,zones,rules:{daily_counted:200},
  standings:Array.from({length:n},(_,i)=>({rank:i+1,nickname:'m'+(i+1),xp:100-i,rebirths:i===0?2:0,country:i===1?'KR':null,me:i===1,zone:'stay'}))});
const PLAIN=/—|unlock|seamless|elevate|empower|journey|잠금 해제|원활/i;

test('ten tiers in order, Korean and English names',()=>{
  assert.deepEqual(V.TIERS.map(t=>t[0]),['bronze','silver','gold','platinum','emerald','sapphire','ruby','amethyst','diamond','master']);
  assert.deepEqual(V.TIERS.map(t=>t[1]),['브론즈','실버','골드','플래티넘','에메랄드','사파이어','루비','자수정','다이아몬드','마스터']);
  assert.equal(V.tierName(9,'en'),'Master');assert.equal(V.tierName('gold','ko'),'골드');assert.equal(V.tierName(42,'en'),'Master','clamped');
});

test('the badge shows the tier and, once reborn, the rebirth count',()=>{
  assert.match(V.badge(0,0,'ko'),/브론즈/);assert.doesNotMatch(V.badge(0,0,'ko'),/환생/);
  assert.match(V.badge(0,3,'ko'),/브론즈<b>3환생<\/b>/);assert.match(V.badge(9,1,'en'),/Master<b>Rebirth 1<\/b>/);
  assert.match(V.badge(2,0,'en',{big:true}),/lg-gold lg-big/);
});

test('the zones follow the server rule: 7 up, last 5 down, none down from Bronze, Master 3 reborn',()=>{
  assert.deepEqual(V.zoneCounts(4,30),{up:7,reborn:0,down:5});
  assert.deepEqual(V.zoneCounts(0,30),{up:7,reborn:0,down:0});
  assert.deepEqual(V.zoneCounts(4,9),{up:7,reborn:0,down:2},'promotion first in a small group');
  assert.deepEqual(V.zoneCounts(9,30),{up:0,reborn:3,down:5});
  assert.deepEqual(V.zoneCounts(9,6),{up:0,reborn:3,down:3});
});

test('the group table marks the zones, the member and the flags; the legend says what each zone does',()=>{
  const d=group(3,12,{up:7,reborn:0,down:5});
  d.standings.forEach((s,i)=>{s.zone=i<7?'up':i>=7?'down':'stay';});
  const html=V.meHtml(d,'ko',{settingsHref:'/#/community/account?section=learning'});
  assert.equal((html.match(/lg-z-up/g)||[]).length,7);assert.equal((html.match(/lg-z-down/g)||[]).length,5);
  assert.match(html,/class="lg-z-up lg-me" aria-current="true"/);
  assert.match(html,/flagcdn\.com\/w40\/kr\.png/);assert.match(html,/2환생/);
  assert.match(html,/3일 남음/);assert.match(html,/플래티넘/);
  assert.match(html,/1~7위 승급/);assert.match(html,/마지막 5명 강등/);
  assert.match(html,/href="#\/ranking"/);assert.match(html,/section=learning/);
  const master=group(9,10,{up:0,reborn:3,down:5});master.standings.forEach((s,i)=>{s.zone=i<3?'reborn':i>=5?'down':'stay';});
  const m=V.meHtml(master,'en');
  assert.equal((m.match(/lg-z-reborn/g)||[]).length,3);assert.match(m,/Top 3: rebirth/);assert.doesNotMatch(m,/Top 7: up/);
  const bronze=V.legendHtml({tier:0,zones:{up:7,reborn:0,down:0},standings:[{}]},'en');
  assert.match(bronze,/No demotion from Bronze/);
});

test('before the first XP of the week, and for guests: plain words and a sign-in button',()=>{
  const none=V.meHtml({tier:2,rebirths:0,days_left:1,joined:false,xp:0,zones:{up:7,down:5}},'en');
  assert.match(none,/1 day left/);assert.match(none,/Gold league/);assert.doesNotMatch(none,/lg-table/);
  for(const lang of ['ko','en']){
    const g=V.guestHtml(lang);
    assert.match(g,/href="\/#\/login"/);assert.equal((g.match(/lg-badge/g)||[]).length,10);
    for(const line of [V.rulesLine(lang),V.xpLine(lang),g])assert.doesNotMatch(line,PLAIN);
  }
  assert.match(V.rulesLine('ko'),/1~7위[\s\S]*마지막 5명[\s\S]*1~3위는 환생/);
});

test('the ranking rows, numbers and pages',()=>{
  const html=V.rankingHtml({rows:[{rank:1,nickname:'<b>x</b>',rebirths:2,tier:0,total_xp:12345,country:'IN'},{rank:2,nickname:'y',rebirths:0,tier:9,total_xp:900,country:null,me:true}]},'en');
  assert.match(html,/&lt;b&gt;x/);assert.match(html,/12,345/);assert.match(html,/Rebirth 2/);assert.match(html,/class="lg-me"/);
  assert.match(V.rankingHtml({rows:[]},'ko'),/아직/);
  assert.equal(V.pages({total:250,per_page:100}),3);assert.equal(V.pages({total:0}),1);
});

test('country first guess and the practice region it gives',()=>{
  assert.equal(F.guessCountry('en','Europe/Berlin',['en-IN']),'IN','the browser\'s region comes first');
  assert.equal(F.guessCountry('en','Asia/Seoul',['en']),'KR');assert.equal(F.guessCountry('ko','',[]),'KR');
  assert.equal(F.guessCountry('en','America/Chicago',[]),'US');assert.equal(F.guessCountry('en','',['xx-ZZ']),'US');
  assert.equal(F.regionOf('KR'),'kr');assert.equal(F.regionOf('FR'),'global');
  assert.equal(P.guessRegion('ko','Asia/Seoul','IN'),'in','a saved country wins over the language');
  assert.equal(P.guessRegion('en','Asia/Seoul','DE'),'global');assert.equal(P.guessRegion('en','Asia/Kolkata'),'in');
  assert.equal(F.flagEmoji('KR'),'\u{1F1F0}\u{1F1F7}');assert.equal(F.isCountry('XX'),false);
});

test('the daily goal field: 1 to 50, five quick picks, 10 suggested, the bonus it pays, as the server counts it',async()=>{
  assert.deepEqual([F.GOAL_MIN,F.GOAL_MAX,F.DEFAULT_GOAL,[...F.GOAL_PICKS]],[1,50,10,[1,5,10,20,30]]);
  assert.equal(F.clampGoal(0),1);assert.equal(F.clampGoal(99),50);assert.equal(F.clampGoal('12'),12);assert.equal(F.clampGoal('x'),10);
  const {goalBonus}=await import('../community/src/league.js');
  for(let g=0;g<=51;g++)assert.equal(F.goalBonus(g),goalBonus(g),'the page shows what the server pays: '+g);
  for(const lang of ['ko','en']){
    const html=F.goalHtml(lang,undefined);
    assert.match(html,/type="number" name="daily_goal" min="1" max="50" step="1"[^>]*value="10"/,'10 when nothing is saved');
    assert.deepEqual([...html.matchAll(/data-goal-pick="(\d+)"/g)].map(m=>+m[1]),[1,5,10,20,30]);
    assert.match(html,lang==='ko'?/권장 10/:/10 suggested/);
    assert.match(html,new RegExp('\\+'+F.goalBonus(10)+' XP'));
    assert.equal((html.match(/data-goal-step/g)||[]).length,2,'a stepper');
    assert.doesNotMatch(html,PLAIN);assert.doesNotMatch(html,/설정에서만|Settings only/);
    assert.match(F.goalHtml(lang,37),/value="37"/);assert.match(F.goalHtml(lang,99),/value="10"/);
    /* sign-up and Settings use the same field */
    assert.match(F.fieldsHtml(lang,{country:'KR',daily_goal:23}),/name="daily_goal"[^>]*value="23"/);
  }
});

test('profile pictures in the tables, the letter otherwise, and the flag beside the name',()=>{
  const src=k=>'https://api.example/api/avatar/'+k;
  const d=group(3,3,{up:7,reborn:0,down:5});d.standings[0].avatar='Abc_def-1234';d.standings[1].avatar='../x';
  const html=V.meHtml(d,'en',{avatarSrc:src});
  assert.match(html,/<img class="lg-av" src="https:\/\/api\.example\/api\/avatar\/Abc_def-1234"/);
  assert.equal((html.match(/<span class="lg-av"/g)||[]).length,2,'the others get the letter avatar');
  assert.match(html,/<span class="lg-av"[^>]*>M<\/span><img class="lg-flag"[^>]*kr\.png/,'the flag stays next to the name');
  assert.doesNotMatch(V.meHtml(d,'en'),/<img class="lg-av"/,'no address, no picture');
  const r=V.rankingHtml({rows:[{rank:1,nickname:'ana',rebirths:0,tier:1,total_xp:5,country:'IN',avatar:'Abc_def-1234'},{rank:2,nickname:'<b>',rebirths:0,tier:0,total_xp:1,country:null,avatar:null}]},'ko',{avatarSrc:src});
  assert.match(r,/lg-av" src="https:\/\/api\.example\/api\/avatar\/Abc_def-1234"[\s\S]*in\.png/);assert.match(r,/>&lt;<\/span>/);
  assert.match(read('index.html'),/V\.rankingHtml\(data,lang,\{avatarSrc:k=>cmBase\(\)\+"\/api\/avatar\/"\+k\}\)/);
  assert.match(read('practice.js'),/avatarSrc:k=>API\+'\/api\/avatar\/'\+k/);
});

test('today\'s goal in the league tab: counted, goal, the bonus pending or earned, the next day\'s goal',()=>{
  assert.equal(V.goalLine(null,'ko'),'');assert.equal(V.goalLine({goal:null},'ko'),'');
  assert.match(V.goalLine({counted:4,goal:10,bonus_xp:90,earned:false},'ko'),/오늘 목표 4\/10[\s\S]*달성하면 \+90 XP/);
  assert.match(V.goalLine({counted:12,goal:10,bonus_xp:90,earned:true,earned_xp:90,next_goal:5},'en'),/Today 10\/10[\s\S]*Goal reached \+90 XP · 5 from tomorrow/);
  assert.match(V.meHtml({...group(0,2,{up:7}),today:{counted:1,goal:3,bonus_xp:20}},'ko'),/lg-goal/);
});

test('the practice page: the goal is changed on the page itself, counted like the server, and its reward shown',()=>{
  const js=read('practice.js');
  assert.doesNotMatch(js,/goalSettings/,'no "change it in Settings" link on the goal');
  assert.match(js,/id="goalBtn" aria-expanded/);
  assert.match(js,/api\('\/api\/me\/learner','PUT',needCountry\?v:\{country:state\.learner\.country,daily_goal:g\}\)/,'members save to the account');
  assert.match(js,/saved\.dailyGoal=g;if\(saved\.profile\)saved\.profile\.daily=g;save\(\)/,'guests on this device');
  assert.match(js,/if\(result==='right'\|\|result==='solved'\)\{[^\n]*\n\s*if\(!saved\.goalDay\.ids\.includes\(item_id\)\)/,'right answers, once per problem a day');
  assert.match(js,/if\(r\.goal_bonus>0\)\{[^\n]*goalMoment\(r\.goal_bonus\)/,'the moment comes with the server\'s bonus');
  assert.match(js,/type:'hl-practice-goal'/);assert.match(read('index.html'),/hl-practice-goal"\)homeGoalMoment/);
  assert.match(read('practice.css'),/prefers-reduced-motion:reduce\)\{\.goalmoment\{animation:none\}/);
  assert.match(js,/LF\(\)\.goalHtml\(state\.lang,a\.daily\)/,'the first questions use the same stepper');
});
