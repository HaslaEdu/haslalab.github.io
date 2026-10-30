const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const read = file => fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
const arena = read('arena.js'), index = read('index.html');
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const rows = [
  {rank:1,nickname:'물리 연구자',av:'avatar_123',lv:15,total:125.5,rating:333,solved:7},
  {rank:2,nickname:'No photo',av:null,lv:0,total:90,rating:222,solved:3},
  {rank:3,nickname:'<script>"x"</script>',av:'javascript:bad',lv:5,total:0,rating:0,solved:0}
];

function app(lang) {
  const context = {lang,esc,cm:{me:{nickname:rows[0].nickname}},cmBase:()=> 'https://community.example',
    cmApi:async()=>{throw new Error('preloaded public ranking should not need another request');}};
  vm.createContext(context);
  for (const [start,end] of [['function cmProfileHref(', '\nconst cmName'], ['function cmAv(', '\nconst cmTag']]) {
    const at=index.indexOf(start);assert.ok(at>=0);
    vm.runInContext(index.slice(at,index.indexOf(end,at)),context);
  }
  vm.runInContext(arena,context);
  return {context,root:{innerHTML:''}};
}

function assertPeople(html, context) {
  const people=[...html.matchAll(/<a class="ar-rank-person"[^>]*>[\s\S]*?<\/a>/g)].map(match=>match[0]);
  assert.equal(people.length,rows.length);
  for (const [i,row] of rows.entries()) {
    assert.ok(people[i].includes(`href="${esc(context.cmProfileHref(row.nickname))}"`));
    assert.ok(people[i].includes(`<span class="ar-rank-name">${esc(row.nickname)}</span>`));
    assert.match(people[i],/class="artier"/,'tier remains attached to the public identity');
  }
  assert.match(people[0],/<img class="cmav ar-rank-avatar"[^>]*src="https:\/\/community\.example\/api\/avatar\/avatar_123"[^>]*alt=""/);
  for (const person of people.slice(1)) {
    assert.match(person,/ar-rank-avatar-default[^>]*aria-hidden="true"><svg/);
    assert.doesNotMatch(person,/<img\b/);
  }
  assert.doesNotMatch(html,/<script>|javascript:bad/,'public names and invalid avatar values never create executable markup');
}

test('monthly and all-time leaderboards link clear photo/name identities without losing score, tier or solved counts',async()=>{
  for (const lang of ['ko','en']) for (const scope of ['month','all']) {
    const {context,root}=app(lang);
    await context.arRank(root,()=>true,scope,{period:scope==='month'?'2026-11':null,rows});
    const html=root.innerHTML;
    assertPeople(html,context);
    assert.match(html,/<table class="ar-rank-table">/,'dedicated table is unaffected by community post-list mobile hiding rules');
    assert.match(html,/<tr class="armine">/);
    assert.match(html,/<th scope="col" class="ar-rank-score">/);
    assert.match(html,new RegExp(`<td class="ar-rank-score"><b>${scope==='all'?'333':'125\\.5'}</b>`));
    assert.match(html,/<td class="ar-rank-solved-cell">7<\/td>/);
    assert.match(html,/ar-rank-mobile-meta/,'narrow layouts retain tier and solved information beside the name');
    assert.match(html,lang==='en'?/View public profile/:/공개 프로필 보기/);
  }
});

test('the monthly top list uses the same profile identities with visible ordinal positions and scores',async()=>{
  for (const lang of ['ko','en']) {
    const {context,root}=app(lang);
    await context.arWeekly(root,()=>true,'2026-11',{period:'2026-11',problems:[],top:rows.map(({rank,...row})=>row),now:0});
    const html=root.innerHTML;
    assertPeople(html,context);
    assert.match(html,/<ol class="ar-rank-top">/);
    for (const rank of [1,2,3]) assert.ok(html.includes(`<span class="ar-rank-position">${rank}</span>`));
    assert.match(html,/<span class="ar-rank-top-score"><b>125\.5<\/b><small>/);
    assert.match(html,/href="#\/rank\/2026-11"/);
  }
});
