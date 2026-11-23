const test=require('node:test');
const assert=require('node:assert/strict');
const V=require('../league-view.js');
const F=require('../learner-form.js');
const P=require('../learn-path.js');

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
  assert.deepEqual([...F.DAILY_GOALS],[5,10,15,20]);
});
