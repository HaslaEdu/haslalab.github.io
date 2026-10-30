const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const read=file=>fs.readFileSync(path.join(root,file),'utf8');

function app(){
  const dummy={setAttribute(){},addEventListener(){},style:{},classList:{toggle(){},add(){},remove(){}},querySelectorAll(){return[]},dataset:{}};
  const context={window:{},URL,URLSearchParams,location:{hash:'#/nbpho/2026',search:''},history:{replaceState(){}},
    document:{getElementById(){return dummy},querySelectorAll(){return[]},querySelector(){return null},documentElement:{},body:dummy},
    localStorage:{getItem(){return 'thy'},setItem(){}},addEventListener(){},matchMedia(){return{matches:false}},
    setTimeout(){},clearTimeout(){},requestAnimationFrame(){},cancelAnimationFrame(){},console};
  vm.createContext(context);
  for(const file of ['theory.js','paper-languages.js','contest-exams.js','examdur.js','rupho-selection.js','rupho-archive.js','site-design.js'])vm.runInContext(read(file),context,{filename:file});
  context.HLexam=context.window.HLexam;
  const main=[...read('index.html').matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)].find(m=>m[2].includes('const REL ='))[2];
  vm.runInContext(main.replace(/render\(\);\s*$/,''),context);
  return {context,run:code=>vm.runInContext(code,context)};
}

function sessionLinks(html){
  return [...html.matchAll(/href="(sim\/exam\.html\?[^\"]+)"/g)].map(m=>new URL(m[1].replaceAll('&amp;','&'),'https://haslalab.org/'));
}

test('NBPhO mode switches retain selected year and theory track shows its combined sitting',()=>{
  const a=app();
  for(const track of ['thy','exp']){
    a.run(`lang='en';track='${track}'`);
    const practice=a.run('viewYear("nbpho",2026)');
    assert.match(practice,/href="#\/nbpho\/2026\/exam"/);
    assert.match(practice,/href="#\/nbpho\/2026\/review"/);
    const exam=a.run('viewYear("nbpho",2026,"exam")');
    assert.match(exam,/href="#\/nbpho\/2026"/);
    assert.match(exam,/data-year="2026"/);
    assert.match(exam,/<option value="2026" selected>/);
    const links=sessionLinks(exam);
    assert.ok(links.length>0,`${track} needs a combined NBPhO sitting`);
    for(const link of links){
      assert.equal(link.searchParams.get('y'),'2026');
      assert.match(link.searchParams.get('e'),/E1.*E2.*T/);
      assert.equal(link.searchParams.get('review'),null);
    }
    const review=a.run('viewYear("nbpho",2026,"review")');
    assert.match(review,/No time limit/);
    for(const link of sessionLinks(review)){
      assert.equal(link.searchParams.get('y'),'2026');
      assert.equal(link.searchParams.get('review'),'1');
    }
  }
});

test('year selection routes the selected competition, mode and year together',()=>{
  const a=app();
  a.run('selectPortalYear("nbpho","exam","2025")');
  assert.equal(a.context.location.hash,'#/nbpho/2025/exam');
  a.run('selectPortalYear("nbpho","review","")');
  assert.equal(a.context.location.hash,'#/nbpho/review');
  a.run('selectPortalYear("ruphox","review","2025")');
  assert.equal(a.context.location.hash,'#/rupho/2025/review?stage=x');
});

for(const key of ['physcup','ortvay','opho','wopho'])
test(`${key} legacy exam entry routes to untimed grading only`,()=>{
    const a=app();a.run("lang='en';track='thy'");
    const html=a.run(`viewComp(${JSON.stringify(key)},"exam")`);
    assert.equal(/Grading &amp; feedback|Grading & feedback/.test(html),true,key+' needs a grading tab');
    assert.equal(/class="ex /.test(html),false,key+' must not offer timed mode');
    const links=sessionLinks(html);
    assert.ok(links.length>0,key+' must offer grading entries');
    for(const link of links)assert.equal(link.searchParams.get('review'),'1',key);
});

test('verified Eötvös sittings offer the Hungarian original in an English timed interface',()=>{
  const a=app();a.run("lang='en';track='thy'");
  for(const year of [2014,2015,2016,2020]){
    const html=a.run(`viewYear("eotvos",${year},"exam")`),links=sessionLinks(html);
    assert.equal(links.length,1,`${year} must offer its one verified paper`);
    const q=links[0].searchParams;
    assert.equal(q.get('lang'),'en');
    assert.equal(q.get('pl'),'hu');
    assert.equal(q.get('p'),`https://eik.bme.hu/~vanko/fizika/eotvos/Eotvos_${year}.pdf`);
    assert.equal(q.get('s'),a.context.window.THEORY.eotvos[String(year)].f.T.sol);
    assert.equal(q.get('review'),null);
    assert.equal(a.context.HLexam.sec('eotvos',year,1,true),300*60);
    assert.ok(html.includes('5:00 + 0:30'));
  }
  assert.equal(a.run('theoryGroups("eotvos",compOf("eotvos").years.find(y=>y.y===2026)).length'),0,'A recent paper without its verified solution must not become a timed scored sitting.');
});
