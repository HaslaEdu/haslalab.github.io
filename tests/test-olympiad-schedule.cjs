/* The Olympiad calendar (#/olympiad/schedule, guides.js, data/schedule.json): olympiads only, and for each country
   in the selector its national selection stages, each with an announced date or the usual month, never a made-up day. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const sched=JSON.parse(read('data/schedule.json'));
const DAY=/^\d{4}-\d{2}-\d{2}$/;

test('the calendar holds no university entrance exams',()=>{
  assert.ok(sched.events.length>=20);
  for(const e of sched.events){
    assert.notEqual(e.kind,'entrance',e.key);
    assert.doesNotMatch(`${e.key} ${e.name} ${e.name_ko}`,/\bJEE\b|NEET|\bAP Physics|A level|gaokao|가오카오|IB Diploma|입시|입학시험/i,e.key);
  }
  const g=read('guides.js');
  assert.doesNotMatch(g,/\['entrance',\{ko:'입시'/,'no entrance-exam filter');
  assert.doesNotMatch(/function scheduleView[\s\S]*?\n  \}/.exec(g)[0],/입시|entrance/i);
});

test('every country in the selector has its national selection, stage by stage',()=>{
  const keys=new Map(sched.events.map(e=>[e.key,e]));
  const countries=[...new Set(sched.events.map(e=>e.country).filter(c=>c&&c!=='intl'))];
  for(const c of countries){
    const plan=sched.selection[c];assert.ok(plan&&plan.stages.length,c+' has stages');
    for(const t of plan.targets){assert.ok(keys.has(t),c+' target '+t);assert.equal(keys.get(t).kind,'international');}
    for(const s of plan.stages){
      const e=s.event?{...keys.get(s.event),...s}:s;
      assert.ok(e&&e.name&&e.name_ko,c+' stage named: '+JSON.stringify(s));
      assert.equal(e.country??c,c,c+' stage is that country\'s: '+e.key);
      /* a date only when announced; otherwise the usual month(s), or the event's own wording */
      if(e.start){assert.match(e.start,DAY);assert.match(e.end||e.start,DAY);}
      else assert.ok(Array.isArray(e.months)&&e.months.length&&e.months.every(m=>Number.isInteger(m)&&m>=1&&m<=12)||e.typical_ko,c+' '+e.key+' has a usual month');
      if(!s.event)assert.ok(/^https:\/\//.test(s.url),c+' '+s.key+' links its source');
    }
  }
  /* the dates confirmed on the official pages */
  assert.equal(keys.get('us-fma-2027').start,'2027-02-09');assert.equal(keys.get('us-usapho-2027').start,'2027-03-14');
  assert.equal(keys.get('in-nsep-2026').start,'2026-11-22');assert.equal(keys.get('in-inpho-2027').start,'2027-01-31');
  assert.equal(keys.get('kr-kpho-winter-entrance-2027').start,'2026-12-12');
});

test('the Olympiad home lists olympiads only, and the page keeps the country choice',()=>{
  const ctx={location:{hash:'#/olympiad'},window:{},fetch:async()=>({ok:true,json:async()=>sched})};
  vm.createContext(ctx);vm.runInContext(read('guides.js'),ctx);
  const up=ctx.window.HL_GUIDES.upcomingFrom({events:[{key:'jee',kind:'entrance',name:'JEE',start:'2026-12-01'},{key:'x',kind:'international',name:'X',start:'2026-12-02'}]},3,'2026-11-24');
  assert.deepEqual(up.map(e=>e.key),['x']);
  const g=read('guides.js');
  assert.match(g,/localStorage\.setItem\(COUNTRY_KEY/);assert.match(g,/try\{return localStorage\.getItem\(COUNTRY_KEY\);\}catch\(e\)/);
  assert.match(g,/cmLearner\(\)/,'the learner profile\'s country is the default');
  assert.match(g,/예년 기준 \$\{months\.join\('–'\)\}월/);
});

test('the Olympiad home card is per country: a Korean learner sees KPhO and APhO/IPhO, an American F=ma and USAPhO, neither the other\'s rounds',()=>{
  const ctx={location:{hash:'#/olympiad'},window:{},localStorage:{getItem:()=>null},fetch:async()=>({ok:true,json:async()=>sched})};
  vm.createContext(ctx);vm.runInContext(read('guides.js'),ctx);
  const G=ctx.window.HL_GUIDES,keys=c=>G.upcomingFor(sched,c,5,'2026-11-24').map(e=>e.key),country=k=>sched.events.find(e=>e.key===k)?.country;
  const kr=keys('kr'),us=keys('us');
  for(const k of ['kr-kpho-winter-entrance-2027','kr-kpho-winter-school-2027','apho-2027','ipho-2027'])assert.ok(kr.includes(k),k);
  for(const k of ['us-fma-2027','us-usapho-2027'])assert.ok(us.includes(k),k);
  assert.ok(!kr.includes('us-usapho-2027')&&!kr.includes('in-inpho-2027')&&!kr.includes('us-fma-2027'));
  assert.ok(!us.some(k=>k.startsWith('kr-'))&&!us.includes('in-inpho-2027'));
  /* every country in the calendar: only its own rounds (or its plan's own stages) and events open to all */
  for(const c of Object.keys(sched.selection).filter(c=>!c.startsWith('_'))){
    const list=keys(c);assert.ok(list.length>=1&&list.length<=5,c);
    for(const k of list)assert.ok([c,'intl',undefined].includes(country(k)),c+' shows '+k);
  }
  /* entrance exams never, and a past event drops out */
  const t=G.upcomingFor({events:[{key:'jee',kind:'entrance',name:'JEE',country:'in',start:'2026-12-01'},{key:'old',kind:'selection',name:'Old',country:'in',start:'2026-11-01'},{key:'x',kind:'international',name:'X',country:'intl',start:'2026-12-02'}],selection:{}},'in',5,'2026-11-24');
  assert.deepEqual([...t.map(e=>e.key)],['x']);
});
