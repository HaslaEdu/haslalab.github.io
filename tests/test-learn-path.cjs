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
    assert.ok(links(html).includes('#/learn/practice?unit=mechanics/momentum'));
    assert.ok(links(html).includes('#/learn/physics/search'));
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

test('the header switches between the Learn and Olympiad sections; community and about stand apart',()=>{
  const a=app('#/');
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    for(const [active,hash,on] of [['home','#/','#/'],['learn','#/learn/physics','#/'],['comps','#/comps','#/olympiad'],['comps','#/archive/books/phys','#/'],['weekly','#/monthly','#/olympiad'],['olympiad','#/olympiad','#/olympiad']]){
      a.context.location.hash=hash;a.run(`paintPageChrome(${JSON.stringify(active)})`);
      assert.deepEqual(links(a.nav()),['#/','#/olympiad','#/community','#/about'],hash);
      assert.match(a.nav(),new RegExp(`href="${on.replace(/\//g,'\\/')}" class="on"`),hash);
    }
    a.context.location.hash='#/community';a.run('paintPageChrome("community")');
    assert.doesNotMatch(a.nav(),/href="#\/(olympiad)?" class="on"/);
    assert.equal(a.run('UI[lang].navOly'),language==='ko'?'올림피아드':'Olympiad');
  }
});

test('each section has its own bar, and the current page is marked in it',()=>{
  const a=app('#/');
  const bar=(section,hash)=>{a.context.location.hash=hash;return a.run(`sectionLinks(${JSON.stringify(section)}).map(([href,label,current])=>[href,current(${JSON.stringify(hash)})])`);};
  const learn=bar('learn','#/learn/physics/search');
  assert.deepEqual(Array.from(learn,([href])=>href).filter(h=>h.startsWith('#')),['#/','#/learn/practice','#/learn/roadmap','#/learn/create','#/learn/physics','#/archive/books/phys','#/learn/physics/search','#/learn']);
  assert.deepEqual(Array.from(learn).filter(([,on])=>on).map(([h])=>h),['#/learn/physics/search']);
  const oly=bar('olympiad','#/ipho/2019');
  assert.deepEqual(Array.from(oly,([href])=>href),['#/olympiad','#/comps','#/olympiad/schedule','#/monthly','#/hpho','#/lab']);
  assert.deepEqual(Array.from(oly).filter(([,on])=>on).map(([h])=>h),['#/comps']);
  assert.equal(a.run('sectionLinks(null).length'),0);
  assert.equal(a.run('siteSection("community")'),null);assert.equal(a.run('siteSection("about")'),null);
});

test('the site opens on the Learn home with a problem open; the roadmap, the calendar and the rest are one click away',()=>{
  const a=app('#/');
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const html=a.run('viewHome()'),hrefs=links(html);
    /* a plain home: today's problems first, then six doors; the bar above carries the rest */
    for(const href of ['#/learn/practice','#/learn/roadmap','#/learn/practice?mode=tracks','#/learn/practice?mode=contest','#/olympiad/schedule','#/learn/create','#/community'])assert.ok(hrefs.includes(href),href);
    assert.match(html,/src="practice\.html\?[^"]*mode=play/,'a problem is open on the home page');
    assert.doesNotMatch(html,/id="deflect"|homeLatest/);
  }
  assert.deepEqual(Runtime.routeNeeds('#/'),[]);
});

test('the Olympiad home is the former HaslaLab home with its hero and community panels',()=>{
  const a=app('#/olympiad');
  a.context.document.createElement=()=>{const el={_h:'',set innerHTML(v){this._h=v;},get innerHTML(){return this._h;},querySelector(sel){
    const h=this._h;if(sel==='figure.screen'){const m=/<figure class="screen">[\s\S]*?<\/figure>/.exec(h);return{outerHTML:m[0]};}
    if(sel==='.hero > div'){const m=/<div class="hero">\s*<div>([\s\S]*?)<\/div>\s*<figure/.exec(h);return{innerHTML:m[1]};}return null;}};return el;};
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const html=a.run('viewOlympiad()');
    assert.match(html,/id="deflect"/);assert.match(html,/id="homeLatest"/);
    assert.ok(links(html).includes('#/comps'));
  }
  assert.deepEqual(Runtime.routeNeeds('#/olympiad'),[]);
});

test('the computational physics page embeds the judge and passes on only a valid problem id',()=>{
  const a=app('#/learn/compute?problem=kepler-orbit');
  let src=/id="learnComputeFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnCompute()'))[1];
  assert.ok(src.startsWith('compute.html?'));assert.equal(new URLSearchParams(src.split('?')[1]).get('problem'),'kepler-orbit');
  a.context.location.hash='#/learn/compute?problem=%22%3E%3Cscript%3E';
  src=/id="learnComputeFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnCompute()'))[1];
  assert.equal(new URLSearchParams(src.split('?')[1]).get('problem'),null);
  assert.ok(links(a.run('viewHome()')).includes('#/learn/create'),'the home leads to Create, which links the site\'s own Python problems');
  assert.deepEqual(Runtime.routeNeeds('#/learn/compute'),[]);
});

test('the practice page embeds practice.html and passes on only a unit of the learning path',()=>{
  const a=app('#/learn/practice?unit=em/induction');
  let src=/id="learnPracticeFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnPractice()'))[1];
  assert.ok(src.startsWith('practice.html?'));assert.equal(new URLSearchParams(src.split('?')[1]).get('unit'),'em/induction');
  a.context.location.hash='#/learn/practice?unit=../../etc';
  src=/id="learnPracticeFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnPractice()'))[1];
  assert.equal(new URLSearchParams(src.split('?')[1]).get('unit'),null);
  assert.deepEqual(Runtime.routeNeeds('#/learn/practice'),[]);
});
