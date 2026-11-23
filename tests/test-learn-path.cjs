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

test('the unit map is the roadmap\'s second tab: stages, the topic map with practice links, and no fetches; the old physics page goes there',()=>{
  const a=app();
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    for(const html of [a.run('viewLearnSubject("physics")'),a.run('viewLearnRoadmap("units")')]){
      assert.equal((html.match(/class="lp-stage"/g)||[]).length,P.STAGES.length);
      assert.equal((html.match(/data-subtopic="/g)||[]).length,P.SUBTOPICS.size);
      assert.ok(links(html).includes('#/learn'));
      assert.ok(links(html).includes('#/learn/practice?unit=mechanics/momentum'));
      assert.ok(links(html).includes('#/learn/roadmap')&&links(html).includes('#/learn/roadmap?view=units'),'both roadmap tabs');
      assert.match(html,/href="#\/learn\/roadmap\?view=units" aria-current="page"/);
      assert.ok(!links(html).includes('#/learn/physics/studio'),'the studio stays for administrators');
      assert.match(html,language==='ko'?/어디서 시작할까요/:/Where to start/);
    }
  }
  /* the studio is on the Learn page for administrators only */
  assert.ok(!links(a.run('viewLearnHome()')).includes('#/learn/physics/studio'));
  a.run('cm.me={id:1,role:"admin"}');assert.ok(links(a.run('viewLearnHome()')).includes('#/learn/physics/studio'));a.run('cm.me=null');
  assert.deepEqual(Runtime.routeNeeds('#/learn/physics/search?subject=optics'),[]);
  /* #/learn/physics is replaced by the unit map */
  const replaced=[];a.context.history.replaceState=(s,t,url)=>replaced.push(url);
  a.context.location.hash='#/learn/physics';try{a.run('render()');}catch(e){}
  assert.equal(replaced[0],'#/learn/roadmap?view=units');
  for(const hash of ['#/learn/roadmap','#/learn/courses','#/learn/lab','#/learn/subjects','#/learn'])assert.deepEqual(Runtime.routeNeeds(hash),[],hash);
});

test('the search page forwards only a valid topic and difficulty to the search frame',()=>{
  const a=app('#/learn/physics/search?subject=optics&stars=3');
  let src=/id="learnSearchFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnSearch()'))[1];
  let q=new URLSearchParams(src.split('?')[1]);assert.equal(q.get('subject'),'optics');assert.equal(q.get('stars'),'3');
  a.context.location.hash='#/learn/physics/search?subject=%3Cscript%3E&stars=9';
  src=/id="learnSearchFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnSearch()'))[1];
  q=new URLSearchParams(src.split('?')[1]);assert.equal(q.get('subject'),null);assert.equal(q.get('stars'),null);
});

test('the top menu has six items: Home, Learn, Olympiad, Workshop, Community, About; the current one is marked',()=>{
  const a=app('#/');
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    for(const [active,hash,on] of [['home','#/','#/'],['learn','#/learn/physics','#/learn'],['learn','#/learn/lab','#/learn'],['comps','#/comps','#/olympiad'],['comps','#/archive/books/phys','#/learn'],['weekly','#/monthly','#/olympiad'],['olympiad','#/olympiad','#/olympiad'],['workshop','#/workshop','#/workshop'],['workshop','#/workshop/make','#/workshop'],['community','#/community','#/community'],['about','#/about','#/about']]){
      a.context.location.hash=hash;a.run(`paintPageChrome(${JSON.stringify(active)})`);
      assert.deepEqual(links(a.nav()),['#/','#/learn','#/olympiad','#/workshop','#/community','#/about'],hash);
      assert.equal((a.nav().match(/class="on"/g)||[]).length,1,hash);
      assert.match(a.nav(),new RegExp(`href="${on.replace(/\//g,'\\/')}" class="on"`),hash);
    }
    assert.equal(a.run('UI[lang].navOly'),language==='ko'?'올림피아드':'Olympiad');
    assert.equal(a.run('UI[lang].navHome'),language==='ko'?'홈':'Home');
    assert.equal(a.run('UI[lang].navWork'),language==='ko'?'워크샵':'Workshop');
  }
  /* the phone tab bar copies the top menu: the same six items, no extra button, an icon for each */
  const ux=read('site-ux.js');assert.doesNotMatch(ux,/data-hlx="search"/);assert.match(ux,/nav\.querySelectorAll\("a"\)/);
});

test('the Learn bar: today\'s problems, roadmap, courses, search, lab, in that order; old routes mark where they now live',()=>{
  const a=app('#/');
  const bar=(section,hash)=>{a.context.location.hash=hash;return a.run(`sectionLinks(${JSON.stringify(section)}).map(([href,label,current])=>[href,current(${JSON.stringify(hash)})])`);};
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const learn=bar('learn','#/learn/physics/search');
    assert.deepEqual(Array.from(learn,([href])=>href),['#/learn/practice','#/learn/roadmap','#/learn/guide','#/learn/courses','#/learn/physics/search','#/learn/lab']);
    assert.deepEqual(Array.from(a.run('sectionLinks("learn").map(x=>x[1])')),language==='ko'?['오늘의 문제','로드맵','교재','강좌','문제 검색','실험실']:["Today's problems",'Roadmap','Guide','Courses','Search problems','Lab']);
    assert.ok(Array.from(a.run('sectionLinks("learn").map(x=>x[3])')).every(line=>line&&line.length<90),'each item has one short line');
    for(const [hash,on] of [['#/learn/physics/search','#/learn/physics/search'],['#/learn/practice','#/learn/practice'],['#/learn/physics','#/learn/roadmap'],['#/learn/roadmap','#/learn/roadmap'],['#/learn/courses','#/learn/courses'],
      ['#/learn/lab','#/learn/lab'],['#/learn/concepts','#/learn/lab'],['#/learn/compute','#/learn/lab']])
      assert.deepEqual(Array.from(bar('learn',hash)).filter(([,x])=>x).map(([h])=>h),[on],hash);
    for(const hash of ['#/workshop/make','#/workshop/create'])assert.deepEqual(Array.from(bar('learn',hash)).filter(([,x])=>x),[],'the makers left the Learn bar: '+hash);
    const ws=bar('workshop','#/workshop/storage');
    assert.deepEqual(Array.from(ws,([href])=>href),['#/workshop','#/workshop/make','#/workshop/draw','#/workshop/create','#/workshop/storage']);
    assert.deepEqual(Array.from(ws).filter(([,x])=>x).map(([h])=>h),['#/workshop/storage']);
  }
  const oly=bar('olympiad','#/ipho/2019');
  assert.deepEqual(Array.from(oly,([href])=>href),['#/olympiad','#/comps','#/olympiad/schedule','#/monthly','#/hpho']);
  assert.deepEqual(Array.from(bar('olympiad','#/lab')).filter(([,on])=>on),[],'exam mode is off the bar; #/lab still routes');
  assert.deepEqual(Array.from(oly).filter(([,on])=>on).map(([h])=>h),['#/comps']);
  assert.equal(a.run('sectionLinks(null).length'),0);
  assert.equal(a.run('siteSection("home")'),null);assert.equal(a.run('siteSection("learn")'),'learn');
  assert.equal(a.run('siteSection("community")'),null);assert.equal(a.run('siteSection("workshop")'),'workshop');assert.equal(a.run('siteSection("about")'),null);
});

const PLAIN=/—|unlock|seamless|elevate|comprehensive|empower|journey|잠금 해제|원활|한 단계 높/i;
test('the home page: one line, one button to practice, a strip of problems loaded later, four doors and a footer line',()=>{
  const a=app('#/'),counts=require('../tools/build-courses.cjs').build().counts;
  assert.deepEqual({...a.run('PRACTICE_COUNTS')},counts,'the practice counts are what practice/ holds');
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const html=a.run('viewHome()'),hrefs=links(html),A=a.run('archiveTotals()');
    assert.doesNotMatch(html,/<iframe|practice\.html/,'today\'s problem is not embedded');
    assert.equal((html.match(/class="hm-start"/g)||[]).length,1,'one primary button');
    assert.match(html,/<a class="hm-start" href="#\/learn\/practice">/);
    assert.match(html,language==='ko'?/문제 풀러 가기/:/Start solving/);
    assert.equal((html.match(/<h1\b/g)||[]).length,1);
    assert.match(html,/id="hmStrip"[^>]*data-state="wait"/,'the strip is empty until its data arrives');
    const doors=[...html.matchAll(/class="hm-door" href="([^"]+)"/g)].map(m=>m[1]);
    assert.deepEqual(doors,['#/learn','#/olympiad','#/learn/lab','#/community']);
    const foot=/<p class="hm-foot">([\s\S]*?)<\/p>/.exec(html)[1];
    assert.deepEqual(links(foot),['#/workshop','#/workshop?for=clubs'],'teachers and clubs go to the Workshop');
    assert.equal(hrefs.length,1+4+2,'nothing else to choose from');
    assert.doesNotMatch(html,/hm-sec|hm-go|hm-grid"|hm-top/,'the old sections are gone');
    assert.ok(html.includes(a.run(`nfmt(${A.comps})`)));
    assert.equal(A.comps,language==='en'?49:50);
    assert.doesNotMatch(html,PLAIN);assert.doesNotMatch(html,/id="deflect"|homeLatest/);
    for(const view of ['viewLearnHome()','viewLearnLab()','viewWorkshop()','viewWorkshopStorage()'])assert.doesNotMatch(a.run(view),PLAIN,view);
  }
  assert.deepEqual(Runtime.routeNeeds('#/'),[]);
});

test('the home strip: real problems from every level, short excerpts with whole math, links that open the problem',()=>{
  const strip=JSON.parse(read('practice/home-strip.json')),a=app('#/');
  assert.match(read('index.html'),new RegExp('const HOME_STRIP_V="'+require('node:crypto').createHash('sha256').update(read('practice/home-strip.json')).digest('hex').slice(0,12)+'"'),'the page asks for the current file');
  assert.ok(strip.items.length>=24);
  assert.deepEqual([...new Set(strip.items.map(i=>i.level))].sort(),['L1','L2','L3','L4']);
  assert.ok(new Set(strip.items.map(i=>i.src.en)).size>=10,'many sources');
  const ids=new Set();
  for(const it of strip.items){
    assert.ok(!ids.has(it.id),it.id);ids.add(it.id);
    assert.ok(it.text.length>=40&&it.text.length<=260,it.id+' '+it.text.length);
    const dollars=(it.text.match(/(?<!\\)\$/g)||[]).length;assert.equal(dollars%2,0,'math is never cut: '+it.id);
    assert.match(it.id,/^[a-z0-9]+-[A-Za-z0-9~._-]{1,60}$/,'the practice page accepts the id');
  }
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    a.context.__items=strip.items;
    const pick=a.run('homeStripPick(__items,lang)');
    assert.equal(pick.length,24);
    if(language==='en')assert.ok(pick.every(i=>i.lang==='en'),'English cards are in English');
    else assert.ok(pick.some(i=>i.lang==='ko')&&pick.some(i=>i.lang==='en'),'the Korean page mixes tracks and competitions');
    const html=a.run('homeStripCards(homeStripPick(__items,lang),lang)');
    assert.equal((html.match(/class="hm-card/g)||[]).length,24);
    for(const href of links(html))assert.match(href,/^#\/learn\/practice\?item=[A-Za-z0-9~._%-]+$/);
    assert.doesNotMatch(html,/<script|onerror=/);
  }
  /* the strip waits for the first paint and respects reduced motion with a still grid */
  const js=read('index.html');
  assert.match(js,/requestIdleCallback\(go/);assert.match(js,/prefers-reduced-motion: reduce/);assert.match(js,/hm-grid6/);
  assert.match(read('site-design.css'),/prefers-reduced-motion:reduce\)\{\s*body\.hl-site \.hm-track\{animation:none\}/);
  assert.match(read('site-design.css'),/\.hm-strip:hover,\.hm-strip:focus-within,\.hm-strip\.hm-paused\) \.hm-track\{animation-play-state:paused\}/);
});

test('the Learn page lists the six parts with one line each, then books and other subjects; the teacher page moved to the Workshop',()=>{
  const a=app('#/learn');
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const html=a.run('viewLearnHome()'),hrefs=links(html);
    const parts=[...html.matchAll(/<ol class="ll-parts">([\s\S]*?)<\/ol>/g)][0][1];
    assert.deepEqual(links(parts),['#/learn/practice','#/learn/roadmap','#/learn/guide','#/learn/courses','#/learn/physics/search','#/learn/lab']);
    for(const href of ['#/archive/books/phys','#/learn/subjects'])assert.ok(hrefs.includes(href),href);
    assert.ok(!hrefs.some(h=>/^#\/(learn\/teach|learn\/create|workshop)/.test(h)),'no making tools in Learn');
    assert.equal((html.match(/class="hm-go"/g)||[]).length,1);
  }
});

test('the lab gathers the concept simulations, computational physics, the creations gallery and the experiment simulators; making is in the Workshop',()=>{
  const a=app('#/learn/lab');
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const html=a.run('viewLearnLab()'),cards=[...html.matchAll(/class="lab-card" href="([^"]+)"/g)].map(m=>m[1]);
    assert.deepEqual(cards,['#/learn/concepts','#/learn/compute','#/workshop/create',language==='ko'?'problems.html':'problems-en.html']);
    assert.ok(!links(html).some(h=>/view=edit/.test(h)),'no editor button in the lab');assert.equal((html.match(/class="hm-go"/g)||[]).length,1);
    for(const view of ['viewLearnConcepts()','viewLearnCompute()'])assert.ok(links(a.run(view)).includes('#/learn/lab'),view);
    for(const view of ['viewWorkshopCreate()','viewWorkshopMake()','viewWorkshopStorage()'])assert.ok(links(a.run(view)).includes('#/workshop'),view);
  }
});

test('the courses: one per study level from the repository\'s own data, every link pointing at something that exists',()=>{
  const C=require('../tools/build-courses.cjs').build(),T=require('../practice-tools.js');
  assert.equal(read('data/courses.json'),JSON.stringify(C,null,1)+'\n','data/courses.json is current (node tools/build-courses.cjs)');
  assert.deepEqual(C.levels.map(l=>l.key),T.STUDY_LEVELS.map(l=>l.key));
  const sims=new Set([...read('concepts.js').matchAll(/\{id:'([a-z0-9-]+)',unit:/g)].map(m=>m[1])),rm=new Set(JSON.parse(read('data/roadmap.json')).stages.map(s=>s.key));
  for(const L of C.levels){
    for(const u of L.units){assert.ok(P.SUBTOPICS.has(u.u),u.u);assert.ok(u.n>0);}
    for(const k of L.roadmap)assert.ok(rm.has(k),k);
    assert.ok(L.units.length||L.areas.length,L.key);
  }
  for(const s of C.sims)assert.ok(sims.has(s.id)&&P.SUBTOPICS.has(s.u),s.id);
  assert.equal(C.sims.length,sims.size);
  /* the page: the four levels, a units list with practice links, and the video note */
  const ctx={lang:'ko',location:{hash:'#/learn/courses?level=L1'},history:{replaceState(){}},URLSearchParams,window:{HL_LEARN_PATH:P},
    fetch:async f=>({ok:true,json:async()=>JSON.parse(read(f))})};
  let box={innerHTML:'',querySelectorAll:()=>[]};
  ctx.document={getElementById:id=>id==='courses'?box:null,body:{contains:()=>true}};
  vm.createContext(ctx);vm.runInContext(read('guides.js'),ctx);
  const view=vm.runInContext('window.HL_GUIDES.coursesView()',ctx);
  assert.match(view,/강의 영상 준비 중/);assert.doesNotMatch(view,PLAIN);
  return vm.runInContext('window.HL_GUIDES.coursesMount()',ctx).then(()=>{
    const html=box.innerHTML;
    assert.equal((html.match(/data-level="L\d"/g)||[]).length,4);
    assert.ok(links(html).includes('#/learn/practice?mode=custom&amp;level=L1&amp;unit=mechanics/newton'));
    assert.ok(links(html).includes('#/learn/concepts?sim=pulley-cart'));
    assert.ok(links(html).some(h=>h.startsWith('#/learn/roadmap?stage=')));
    assert.match(html,/AP · Physics Bowl · F=ma/);assert.match(html,/Physics Bowl 기출/);
  });
});

test('the Olympiad home: the hero, then upcoming contests, this month and HPhO, recent papers and competition chips',()=>{
  const a=app('#/olympiad');
  a.context.document.createElement=()=>{const el={_h:'',set innerHTML(v){this._h=v;},get innerHTML(){return this._h;},querySelector(sel){
    const h=this._h;if(sel==='figure.screen'){const m=/<figure class="screen">[\s\S]*?<\/figure>/.exec(h);return{outerHTML:m[0]};}
    if(sel==='.hero > div'){const m=/<div class="hero">\s*<div>([\s\S]*?)<\/div>\s*<figure/.exec(h);return{innerHTML:m[1]};}return null;}};return el;};
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const html=a.run('viewOlympiad()');
    assert.match(html,/id="deflect"/);
    assert.doesNotMatch(html,/homeLatest|homeNotices|hl-home-studio|hl-dashboard|#\/community|#\/learn\/physics\/studio/,'no community or studio panels');
    const heads=[...html.matchAll(/<h2 id="(oly\w+)H">/g)].map(m=>m[1]);
    assert.deepEqual(heads,['olyUpcoming','olyNow','olyRecent','olyQuick']);
    assert.match(html,language==='ko'?/다가오는 대회[\s\S]*이번 달 월별문제 · HPhO[\s\S]*최근 추가된 기출[\s\S]*대회 바로가기/:/Upcoming[\s\S]*Monthly problems · HPhO[\s\S]*Recently added papers[\s\S]*Go to a competition/);
    const hrefs=links(html);
    for(const href of ['#/olympiad/schedule','#/monthly','#/hpho','#/comps'])assert.ok(hrefs.includes(href),href);
    assert.match(html,/aria-haspopup="dialog" onclick="openSiteMailbox\(this\)"/,'the full update log is one tap away');
    const chips=[...html.matchAll(/class="oly-chip" href="#\/([a-z0-9]+)"/g)].map(m=>m[1]);
    assert.deepEqual(chips.slice(0,4),['ipho','apho','eupho','usapho']);
    assert.ok(chips.length>=8&&chips.length<=12);
    if(language==='en')assert.ok(!chips.includes('cpho'),'a competition the English site hides is not offered');
    /* the recent papers are the newest SITE_UPDATES entries that add papers */
    const recent=/id="olyRecent"[^>]*>([\s\S]*?)<\/div><\/section>/.exec(html)[1];
    assert.deepEqual(links(recent),[...a.run('olyRecent().map(u=>u.href)')]);
    assert.ok(links(recent).length>=3);
    assert.doesNotMatch(html,PLAIN);
  }
  assert.deepEqual(Runtime.routeNeeds('#/olympiad'),[]);
});

test('the Olympiad home cards fill from the calendar, /monthly and /hpho, and fall back to plain links',async()=>{
  const sched=JSON.parse(read('data/schedule.json'));
  const ctx={location:{hash:'#/olympiad'},history:{replaceState(){}},URLSearchParams,window:{},fetch:async()=>({ok:true,json:async()=>sched})};
  vm.createContext(ctx);vm.runInContext(read('guides.js'),ctx);
  const up=ctx.window.HL_GUIDES.upcomingFrom(sched,3,'2026-11-23');
  assert.equal(up.length,3);assert.ok(up.every(e=>e.end>='2026-11-23'));
  assert.ok(up[0].start<=up[1].start&&up[1].start<=up[2].start);
  assert.deepEqual(ctx.window.HL_GUIDES.upcomingFrom({events:[{key:'a',name:'A',start:'2026-11-20',end:'2026-11-25'},{key:'b',name:'B',start:'2026-11-30'},{key:'c',name:'C',typical:'May'}]},3,'2026-11-23').map(e=>[e.key,e.days]),[['a',0],['b',7]]);
  /* the page: with the server down, the card keeps its two links */
  const a=app('#/olympiad'),boxes={};
  const box=id=>boxes[id]||(boxes[id]={id,isConnected:true,innerHTML:''});
  a.context.document.getElementById=id=>['olyUpcoming','olyNow'].includes(id)?box(id):null;
  a.context.cmApi=async()=>{throw Error('offline');};
  a.context.window.HL_GUIDES={upcoming:async()=>up};
  a.run('lang="ko"');a.run('mountOlympiadHome()');
  await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));
  assert.deepEqual(links(boxes.olyNow.innerHTML),['#/monthly','#/hpho']);
  assert.equal((boxes.olyUpcoming.innerHTML.match(/<li>/g)||[]).length,3);
  assert.match(boxes.olyUpcoming.innerHTML,/일 남음|진행 중/);
  /* and with it up: the month's deadline and days left, HPhO's next round */
  const t=Date.parse('2026-11-23T03:00:00Z')/1000;
  a.context.cmApi=async(m,p)=>p.startsWith('/monthly')?{now:t,problems:[{open:true,closes_at:t+7*86400}]}:{rounds:[{id:'r1',title:{ko:'제2회 HPhO',en:'HPhO 2'},status:'open',reg_open:t-86400,reg_close:t+10*86400,start_at:t+20*86400,duration_min:300}]};
  a.context.window.HL_HPHO={roundStatus:r=>'open'};
  boxes.olyNow.innerHTML='';a.run('mountOlympiadHome()');
  await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));
  assert.match(boxes.olyNow.innerHTML,/마감[\s\S]*7일 남음/);
  assert.match(boxes.olyNow.innerHTML,/제2회 HPhO[\s\S]*접수 중[\s\S]*20일 남음/);
});

test('the computational physics page embeds the judge and passes on only a valid problem id',()=>{
  const a=app('#/learn/compute?problem=kepler-orbit');
  let src=/id="learnComputeFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnCompute()'))[1];
  assert.ok(src.startsWith('compute.html?'));assert.equal(new URLSearchParams(src.split('?')[1]).get('problem'),'kepler-orbit');
  a.context.location.hash='#/learn/compute?problem=%22%3E%3Cscript%3E';
  src=/id="learnComputeFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnCompute()'))[1];
  assert.equal(new URLSearchParams(src.split('?')[1]).get('problem'),null);
  assert.ok(links(a.run('viewLearnLab()')).includes('#/workshop/create'),'the lab leads to Create, which links the site\'s own Python problems');
  assert.deepEqual(Runtime.routeNeeds('#/learn/compute'),[]);
});

test('the practice page embeds practice.html and passes on only a unit of the learning path',()=>{
  const a=app('#/learn/practice?unit=em/induction');
  let src=/id="learnPracticeFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnPractice()'))[1],q;
  assert.ok(src.startsWith('practice.html?'));assert.equal(new URLSearchParams(src.split('?')[1]).get('unit'),'em/induction');
  a.context.location.hash='#/learn/practice?unit=../../etc';
  src=/id="learnPracticeFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnPractice()'))[1];
  assert.equal(new URLSearchParams(src.split('?')[1]).get('unit'),null);
  /* a course's unit link opens the set builder on that level and unit */
  a.context.location.hash='#/learn/practice?mode=custom&level=L2&unit=em/induction';
  q=new URLSearchParams(/id="learnPracticeFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnPractice()'))[1].split('?')[1]);
  assert.deepEqual([q.get('mode'),q.get('level'),q.get('unit')],['custom','L2','em/induction']);
  a.context.location.hash='#/learn/practice?mode=custom&level=L9';
  q=new URLSearchParams(/id="learnPracticeFrame"[^>]*src="([^"]+)"/.exec(a.run('viewLearnPractice()'))[1].split('?')[1]);
  assert.equal(q.get('level'),null);
  assert.deepEqual(Runtime.routeNeeds('#/learn/practice'),[]);
});

test('the Workshop: a short page of cards, two plain lists, the makers moved from Learn and old links redirected',()=>{
  const a=app('#/workshop');
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const html=a.run('viewWorkshop()');
    assert.deepEqual([...html.matchAll(/<a class="ws-card" href="([^"]+)"/g)].map(m=>m[1]),['#/workshop/make','#/workshop/create','#/workshop/storage','#/workshop/draw']);
    assert.equal((html.match(/class="ws-card ws-soon"/g)||[]).length,1,'only the lab tools are marked as coming');
    assert.match(html,language==='ko'?/물리 그림·시뮬레이션/:/Physics figures and simulations/);
    assert.match(html,/id="wsTeachers"/);assert.match(html,/id="wsClubs"/);
    assert.equal((html.match(/<h1\b/g)||[]).length,1);
    assert.doesNotMatch(html,PLAIN);
    for(const p of html.match(/<p>[^<]*<\/p>/g)||[])assert.ok(p.length<160,'one sentence a card: '+p);
    const store=a.run('viewWorkshopStorage()');
    assert.match(store,/id="wsStore"/);
    assert.equal((store.match(/ws-soon/g)||[]).length,2);assert.match(store,/Google Drive/);assert.match(store,/GitHub/);
    assert.match(a.run('viewWorkshopMake()'),/id="learnTeachFrame"[^>]*src="teach\.html\?/);
    assert.match(a.run('viewWorkshopCreate()'),/id="learnCreateFrame"[^>]*src="create\.html\?/);
    const draw=a.run('viewWorkshopDraw()');
    assert.match(draw,/id="learnDrawFrame"[^>]*src="draw\.html\?embed=1&amp;lang=|id="learnDrawFrame"[^>]*src="draw\.html\?embed=1&lang=/);assert.ok(links(draw).includes('#/workshop'));
  }
  assert.deepEqual({...a.run('WORKSHOP_MOVED')},{teach:'#/workshop/make',create:'#/workshop/create'});
  const replaced=[];a.context.history.replaceState=(s,t,url)=>replaced.push(url);
  for(const [from,to] of [['#/learn/teach','#/workshop/make'],['#/learn/teach?tab=vary','#/workshop/make?tab=vary'],['#/learn/create?view=edit&id=12','#/workshop/create?view=edit&id=12']]){
    a.context.location.hash=from;try{a.run('render()');}catch(e){}
    assert.equal(replaced.at(-1),to,from);
  }
  for(const hash of ['#/workshop','#/workshop/make','#/workshop/draw','#/workshop/storage'])assert.deepEqual(Runtime.routeNeeds(hash),[],hash);
  assert.equal(a.run('WORKSHOP_TITLES.draw.ko'),'그림·시뮬레이션');
  const ux=read('site-ux.js');assert.match(ux,/"#\/workshop": '<path/,'the phone bar has an icon for the Workshop');
  assert.match(ux,/\["워크샵", "#\/workshop"\]/);assert.match(ux,/\["그림·시뮬레이션", "#\/workshop\/draw"\]/);assert.match(ux,/\["Figures and simulations", "#\/workshop\/draw"\]/);assert.doesNotMatch(ux,/#\/learn\/teach/);
});
