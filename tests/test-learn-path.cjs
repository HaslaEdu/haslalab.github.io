const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const Runtime=require('../site-runtime.js'),P=require('../learn-path.js');
const read=file=>fs.readFileSync(path.join(__dirname,'..',file),'utf8');
const main=[...read('index.html').matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].find(match=>match[1].includes('const REL ='))[1];
const links=html=>[...html.matchAll(/<a\b[^>]*href="([^"]+)"/g)].map(match=>match[1]);
function app(hash='#/learn/physics'){
  let navHtml='';
  const node={dataset:{},style:{},classList:{toggle(){},add(){},remove(){}},setAttribute(){},addEventListener(){},querySelector(){return null},querySelectorAll(){return[]}};
  const nav={...node,set innerHTML(v){navHtml=v;},get innerHTML(){return navHtml;}};
  const context={window:{HL_RUNTIME:Runtime},URL,URLSearchParams,console,
    location:{hash,search:''},history:{replaceState(){}},
    document:{getElementById:id=>id==='nav'?nav:node,querySelector:()=>null,querySelectorAll:()=>[],documentElement:{dataset:{theme:'light'}},body:node},
    localStorage:{getItem:()=>null,setItem(){}},sessionStorage:{getItem:()=>null,setItem(){}},
    addEventListener(){},matchMedia:()=>({matches:false}),setTimeout(){},clearTimeout(){},requestAnimationFrame(){},cancelAnimationFrame(){},
    fetch:async()=>{throw Error('learning pages must not fetch resources');}};
  vm.createContext(context);
  for(const file of ['site-catalogue.js','paper-languages.js','examdur.js','rupho-archive.js','learn-path.js','site-design.js'])vm.runInContext(read(file),context,{filename:file});
  context.HLexam=context.window.HLexam;
  context.window.HL_LEARN_PATH=context.HL_LEARN_PATH; /* in a browser globalThis is window */
  vm.runInContext(main.replace(/render\(\);\s*$/,''),context,{filename:'index-main.js'});
  return{run:code=>vm.runInContext(code,context),nav:()=>navHtml,context};
}

test('index.html loads the learning path before the page script',()=>{
  const html=read('index.html'),at=html.indexOf('<script src="learn-path.js'),page=html.indexOf('const REL =');
  assert.ok(at>0&&at<page);
});

test('every stage covers two steps, and the ten steps are covered once',()=>{
  const steps=P.STAGES.flatMap(stage=>{assert.equal(stage.steps[1]-stage.steps[0],1);return[stage.steps[0],stage.steps[1]];});
  assert.deepEqual(steps,[1,2,3,4,5,6,7,8,9,10]);
  for(const stage of P.STAGES)for(const field of ['name','who','goal','sources'])for(const language of ['ko','en'])assert.ok(stage[field][language],stage.key+' '+field);
  assert.equal(P.stageOf(1).key,'intro');assert.equal(P.stageOf(10).key,'national');assert.equal(P.stageOf(11),null);
});

test('the topic map has unique keys, both languages, a first step and problem-bank subjects the search knows',()=>{
  const searchSubjects=new Set([...read('problem-search.js').matchAll(/(\w+):\['[^']+','[^']+'\]/g)].map(match=>match[1]));
  const keys=new Set();
  for(const area of P.AREAS){
    if(area.bank)assert.ok(searchSubjects.has(area.bank),area.key);
    for(const sub of area.subtopics){
      const key=area.key+'/'+sub.key;assert.ok(!keys.has(key),key);keys.add(key);
      assert.ok(sub.name.ko&&sub.name.en,key);assert.ok(sub.from>=1&&sub.from<=10,key);assert.ok(sub.kw.length>0,key);
      if(sub.bank)assert.ok(searchSubjects.has(sub.bank),key);
    }
  }
  assert.equal(P.SUBTOPICS.size,keys.size);
});

test('PhysLeague labels are reclassified, misfiled topics move, and noise is left for review',()=>{
  const cases=[
    ['역학','트랜지스터','modern','solids'],['역학','p-n 접합 다이오드를 이해한다.','modern','solids'],
    ['역학','물질의 자성','em','magnetic_materials'],['광학','도플러 효과를 이해한다.','waves','sound'],
    ['역학','포물선 운동의 역학적 에너지 보존','mechanics','energy'],['역학','운동량 보존과 상대 속도','mechanics','momentum'],
    ['전자기','전자기 유도 자료 분석 및 해석하기','em','induction'],['전자기','저항의 연결과 소비 전력','em','dc_circuits'],
    ['광학','이중 슬릿에 의한 빛의 간섭','optics','interference'],['광학','빛의 굴절과 전반사','optics','refraction'],
    ['열물리','열기관의 열효율을 이해한다.','thermal','heat_engines'],['현대물리','보어의 수소 원자 모형','modern','atoms'],
    ['역학','케플러 법칙 자료 분석 및 해석하기','mechanics','gravitation'],['역학','가속 좌표계와 관성력','mechanics','noninertial']];
  for(const [topic,label,area,subtopic] of cases){
    const found=P.classifyLeagueTopic(topic,label);
    assert.deepEqual([found.area,found.subtopic,found.confidence],[area,subtopic,'keyword'],label);
  }
  for(const label of ['{출제의도}','[ ]','물리학Ⅰ 문항 15 개념','( ), ( ) .','ms'])assert.equal(P.classifyLeagueTopic('역학',label).subtopic,null,label);
  assert.equal(P.classifyLeagueTopic('미분류','물리학Ⅰ 문항 9 개념(검수 필요)'),null);
});

test('school-exam difficulty and olympiad stars land on one ten-step scale',()=>{
  assert.equal(P.stepFromCsat(2),2);assert.equal(P.stepFromCsat(24),6);assert.equal(P.stepFromCsat(13),4);
  assert.equal(P.stepFromCsat(0),2);assert.equal(P.stepFromCsat('x'),null);
  assert.deepEqual([1,2,3,4,5].map(P.stepFromStars),[5,6,7,8,9]);assert.equal(P.stepFromStars(0),null);
  assert.equal(P.bankSubjectOf('modern','special_relativity'),'special_relativity');assert.equal(P.bankSubjectOf('modern','photon'),'quantum_mechanics');
});

test('the physics learning hub shows the stages, the topic map with search links, and no fetches',()=>{
  const a=app();
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const html=a.run('viewLearnSubject("physics")');
    assert.equal((html.match(/class="lp-stage"/g)||[]).length,P.STAGES.length);
    assert.equal((html.match(/data-subtopic="/g)||[]).length,P.SUBTOPICS.size);
    assert.ok(links(html).includes('#/learn'));
    assert.ok(links(html).includes('#/learn/physics/search?subject=classical_mechanics'));
    assert.ok(links(html).includes(language==='ko'?'problems.html':'problems-en.html'));
    assert.ok(!links(html).includes('#/learn/physics/studio'),'the studio stays for administrators');
    assert.match(html,language==='ko'?/어디서 시작할까요/:/Where to start/);
  }
  a.run('cm.me={id:1,role:"admin"}');assert.ok(links(a.run('viewLearnSubject("physics")')).includes('#/learn/physics/studio'));
  assert.deepEqual(Runtime.routeNeeds('#/learn/physics/search?subject=optics'),[]);
});

test('the search page forwards only a valid topic and difficulty to the search frame',()=>{
  const a=app('#/learn/physics/search?subject=optics&stars=3');
  let src=/id="learnSearchFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnSearch()'))[1];
  let q=new URLSearchParams(src.split('?')[1]);assert.equal(q.get('subject'),'optics');assert.equal(q.get('stars'),'3');
  a.context.location.hash='#/learn/physics/search?subject=%3Cscript%3E&stars=9';
  src=/id="learnSearchFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnSearch()'))[1];
  q=new URLSearchParams(src.split('?')[1]);assert.equal(q.get('subject'),null);assert.equal(q.get('stars'),null);
});

test('the navigation separates Learn and Olympiad, and competition pages light up Olympiad',()=>{
  const a=app('#/');
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    a.run('paintPageChrome("comps")');
    const nav=a.nav(),hrefs=links(nav);
    assert.deepEqual(hrefs,['#/','#/learn','#/olympiad','#/community','#/about']);
    assert.match(nav,/href="#\/olympiad" class="on"/);
    a.run('paintPageChrome("weekly")');assert.match(a.nav(),/href="#\/olympiad" class="on"/);
    a.run('paintPageChrome("learn")');assert.match(a.nav(),/href="#\/learn" class="on"/);
    assert.equal(a.run('UI[lang].navOly'),language==='ko'?'올림피아드':'Olympiad');
  }
});

test('the olympiad hub keeps the former home hero and links every competition section',()=>{
  const a=app('#/olympiad');
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const html=a.run('viewOlympiad()'),hrefs=links(html);
    for(const href of ['#/comps','#/monthly','#/hpho','#/lab','#/learn/physics'])assert.ok(hrefs.includes(href),href);
    assert.match(html,/id="deflect"/);
  }
  assert.deepEqual(Runtime.routeNeeds('#/olympiad'),[]);
});
