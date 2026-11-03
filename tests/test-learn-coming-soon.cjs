const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const Runtime=require('../site-runtime.js');
const read=file=>fs.readFileSync(path.join(__dirname,'..',file),'utf8');
const main=[...read('index.html').matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].find(match=>match[1].includes('const REL ='))[1];
const links=html=>[...html.matchAll(/<a\b[^>]*href="([^"]+)"/g)].map(match=>match[1]);
function app(){
  const node={dataset:{},style:{},classList:{toggle(){},add(){},remove(){}},setAttribute(){},addEventListener(){},querySelector(){return null},querySelectorAll(){return[]}};
  const context={window:{HL_RUNTIME:Runtime},URL,URLSearchParams,console,
    location:{hash:'#/learn',search:''},history:{replaceState(){}},
    document:{getElementById:()=>node,querySelector:()=>null,querySelectorAll:()=>[],documentElement:{dataset:{theme:'light'}},body:node},
    localStorage:{getItem:()=>null,setItem(){}},sessionStorage:{getItem:()=>null,setItem(){}},
    addEventListener(){},matchMedia:()=>({matches:false}),setTimeout(){},clearTimeout(){},requestAnimationFrame(){},cancelAnimationFrame(){},
    fetch:async()=>{throw Error('Coming-soon pages must not fetch resources');}};
  vm.createContext(context);
  for(const file of ['site-catalogue.js','paper-languages.js','examdur.js','rupho-archive.js','site-design.js'])vm.runInContext(read(file),context,{filename:file});
  context.HLexam=context.window.HLexam;
  vm.runInContext(main.replace(/render\(\);\s*$/,''),context,{filename:'index-main.js'});
  return{run:code=>vm.runInContext(code,context)};
}

test('the learning overview exposes the physics studio and keeps unreleased subjects coming soon',()=>{
  const a=app(),keys=Array.from(a.run('Object.keys(LEARN)'));
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const html=a.run('viewLearn()');
    assert.match(html,language==='ko'?/준비중/:/Coming soon/);
    assert.equal((html.match(/class="learn-state"/g)||[]).length,keys.length);
    assert.equal((html.match(language==='ko'?/준비중/g:/Coming soon/g)||[]).length,keys.length-2);
    const physicsCard=[...html.matchAll(/<a\b[^>]*href="#\/learn\/physics"[\s\S]*?<\/a>/g)][0]?.[0];
    assert.ok(physicsCard);assert.match(physicsCard,language==='ko'?/문제 제작소/:/Problem Studio/);
    for(const key of keys){
      assert.ok(links(html).includes('#/learn/'+key));
      assert.deepEqual(Runtime.routeNeeds('#/learn/'+key),[],'learning navigation does not download archive papers');
    }
    assert.ok(links(html).every(href=>href.startsWith('#/learn/')));
    assert.doesNotMatch(html,/IPhO|APhO|EuPhO|IChO|IBO|IMO|IOAA|IESO|IJSO|in preparation|when ready|준비하고 있습니다|준비가 끝나면/);
    assert.doesNotMatch(html,/<dl>|<dd>|class="ritem"|Start learning|학습을 시작하세요/);
  }
});

test('physics publishes only its internal studio while other subjects keep placeholders and no external cards',()=>{
  const a=app(),keys=Array.from(a.run('Object.keys(LEARN)'));
  for(const language of ['ko','en'])for(const key of [...keys,'not-a-subject']){
    a.run(`lang=${JSON.stringify(language)}`);
    const html=a.run(`viewLearnSubject(${JSON.stringify(key)})`);
    if(key==='physics'){
      assert.match(html,language==='ko'?/문제 제작소/:/Problem Studio/);
      assert.ok(links(html).includes('#/learn/physics/studio'));
      assert.doesNotMatch(html,/learn-pending/);
    }else if(key==='astronomy')assert.ok(links(html).includes('#/archive/books/astro'));else assert.match(html,language==='ko'?/준비중/:/Coming soon/);
    assert.ok(links(html).every(href=>href.startsWith('#/learn')||href.startsWith('#/archive/books/')));
    assert.doesNotMatch(html,/data-learn-tool="library"|learn\/astronomy\/library|learn\/physics\/library/);
    assert.doesNotMatch(html,/IPhO|APhO|EuPhO|IChO|IBO|IMO|IOAA|IESO|IJSO|in preparation|when ready|준비하고 있습니다|준비가 끝나면/);
    assert.doesNotMatch(html,/<a[^>]*class="ritem"|<dd>|https?:\/\/(?:openstax|ocw\.mit|stellarium|bio\.libretexts)/);
    if(keys.includes(key)){
      if(!['physics','astronomy'].includes(key))assert.match(html,/<section class="learn-pending" role="status">/);
      assert.ok(links(html).includes('#/learn'));
      assert.ok(html.includes(a.run(`LEARN[${JSON.stringify(key)}].name[lang]`)));
    }
  }
  assert.equal(a.run('UI.ko.navLearn'),'학습');assert.equal(a.run('UI.en.navLearn'),'Learn');
});

test('IPhO 2019 E1 exposes the new browser URL and bilingual original documents without staged download links',()=>{
  const a=app(),entry=a.run('DATA.ipho.years.find(year=>year.y===2019).problems.find(problem=>problem.id==="E1")');
  assert.notEqual(entry.hold,true);assert.notEqual(entry.state,'wip');
  assert.equal(entry.files.sim,'sim/ipho2019_E1_web.html');
  assert.equal(entry.files.src,undefined);assert.equal(entry.files.exe,undefined);
  assert.ok(entry.files.pdf.ko.endsWith('/IPhO_2019_E1_KO.pdf'));
  assert.ok(entry.files.pdf.en.endsWith('/IPhO_2019_E1_EN.pdf'));
  assert.ok(entry.files.sol.ko.endsWith('/IPhO_2019_S1_KO.pdf'));
  assert.ok(entry.files.sol.en.endsWith('/IPhO_2019_S1.pdf'));
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)};track="exp"`);
    const html=a.run('viewYear("ipho",2019)');
    /* the run button carries the digest of the simulator page, so an updated simulator is never served from a cache */
    const v=JSON.parse(JSON.stringify(require('node:vm').runInNewContext(read('site-catalogue.js')+';window.HL_CATALOGUE',{window:{}}))).versions.sims.ipho2019_E1;
    assert.match(v,/^[a-f0-9]{12}$/);
    assert.ok(links(html).includes('sim/ipho2019_E1_web.html?v='+v+'&lang='+language));
    assert.ok(html.includes(entry.title[language]));
  }
  const tasks=Array.from(a.run('examGroups("ipho",DATA.ipho.years.find(year=>year.y===2019))[0].map(problem=>problem.id)'));
  assert.deepEqual(tasks,['E1','E2']);
});
