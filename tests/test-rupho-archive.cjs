const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const read=f=>fs.readFileSync(path.join(root,f),'utf8');

function app(){
  const dummy={setAttribute(){},addEventListener(){},style:{},classList:{toggle(){},add(){},remove(){}},querySelectorAll(){return[]},dataset:{}};
  const context={window:{},URL,URLSearchParams,location:{hash:'#/rupho',search:''},history:{replaceState(){}},
    document:{getElementById(){return dummy},querySelectorAll(){return[]},querySelector(){return null},documentElement:{},body:dummy},
    localStorage:{getItem(){return 'thy'},setItem(){}},addEventListener(){},matchMedia(){return{matches:false}},
    setTimeout(){},clearTimeout(){},requestAnimationFrame(){},cancelAnimationFrame(){},console};
  vm.createContext(context);
  for(const file of ['theory.js','paper-languages.js','rupho-selection.js','rupho-archive.js','site-design.js'])vm.runInContext(read(file),context);
  // Source manifests are authoritative even before a local theory.js regeneration.
  const manifests={};
  for(const key of ['rupho','ruphow','ruphox','ruphoy']){
    const m=JSON.parse(read(`tools/theory/${key}.json`));manifests[key]=m;
    context.window.THEORY[key]={};
    context.window.THEORY_META[key]={...m,abbr:m.abbr||m.prefix};
    for(const year of m.years){
      const f={};for(const file of year.files){
        const role={paper:'paper',solution:'sol',marking:'mark',answer:'answer',key:'key'}[file.kind];
        if(role)(f[file.part]||=( {} ))[role]=file.file;
      }
      context.window.THEORY[key][year.y]={f,p:(year.problems||[]).map(p=>[p.id,p.title]),h:year.host,cc:year.cc};
    }
  }
  const main=[...read('index.html').matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)].find(m=>m[2].includes('const REL ='))[2];
  new vm.Script(main);vm.runInContext(main.replace(/render\(\);\s*$/,''),context);
  const run=code=>vm.runInContext(code,context);
  const page=(stage,year,track='thy',lang='ko')=>{
    context.location.hash=`#/rupho${year?'/'+year:''}?stage=${stage}`;
    return run(`lang=${JSON.stringify(lang)};track=${JSON.stringify(track)};${year?'viewYear("rupho",'+JSON.stringify(String(year))+')':'viewComp("rupho")'}`);
  };
  return {context,manifests,run,page,archive:context.window.RUPHO_ARCHIVE};
}

test('RuPhO is one public competition with all four source catalogues intact',()=>{
  const a=app();
  assert.equal(a.run('Object.keys(DATA).filter(k=>k.startsWith("rupho")).join(",")'),'rupho');
  assert.equal(a.run('SUBJ.find(s=>s.k==="phys").comps.filter(k=>k.startsWith("rupho")).join(",")'),'rupho');
  const list=a.run('viewComps("phys")');
  assert.equal((list.match(/class="comp" href="#\/rupho"/g)||[]).length,1);
  assert.doesNotMatch(list, /href="#\/rupho[wxy]/);
  for(const [key,m] of Object.entries(a.manifests)){
    const c=a.archive.catalogue(key);
    for(const y of m.years){
      assert.ok(c.years.some(e=>String(e.y)===String(y.y)),key+' '+y.y);
      const t=a.context.window.THEORY[key][y.y];
      for(const f of y.files)assert.ok(Object.values(t.f[f.part]).includes(f.file),f.file);
    }
  }
});

test('each stage selects its own year and preserves every original theory PDF link',()=>{
  const a=app();let checked=0;
  for(const [key,m] of Object.entries(a.manifests))for(const y of m.years){
    const stage=a.archive.stages.find(s=>s.key===key).id;
    const html=a.page(stage,y.y);
    assert.match(html,new RegExp(`href="#/rupho/${y.y}\\?stage=${stage}"`));
    assert.match(html,new RegExp(`stage=${stage}" aria-current="page"`));
    assert.doesNotMatch(html,/href="#\/rupho[wxy]/);
    for(const f of y.files.filter(f=>['paper','solution'].includes(f.kind))){
      assert.ok(html.includes(f.file),f.file);checked++;
    }
  }
  assert.ok(checked>=319,checked+' theory links');
});

test('W/X/Y experiment and paper-experiment links survive inside RuPhO',()=>{
  const a=app();let checked=0;
  for(const stage of a.archive.stages.filter(s=>s.id!=='final')){
    const c=a.archive.catalogue(stage.key);
    for(const y of c.years.filter(y=>y.problems.length)){
      const html=a.page(stage.id,y.y,'exp','en');
      assert.match(html,/RuPhO stage/);
      for(const p of y.problems)for(const role of ['pdf','sol']){
        for(const u of Object.values(p.files[role]||{})){assert.ok(html.includes(u),u);checked++;}
      }
    }
  }
  assert.equal(checked,96); // 49 papers and 47 published solutions; no invented solution URLs.
});

test('old stage URLs redirect to the selected stage and unavailable years fall back to its list',()=>{
  const a=app();
  for(const letter of ['w','x','y']){
    assert.equal(a.archive.canonical(`#/rupho${letter}/2025`),`#/rupho/2025?stage=${letter}`);
    assert.equal(a.archive.canonical(`#/rupho${letter}/exam`),`#/rupho/exam?stage=${letter}`);
  }
  assert.equal(a.archive.canonical('#/rupho/2025?stage=x'),null);
  assert.equal(a.archive.route('#/rupho?stage=z').stage,'final');
  const html=a.page('final',1967);
  assert.match(html,/href="#\/rupho\?stage=w"/);
  assert.doesNotMatch(html,/href="#\/rupho\/1967\?stage=w"/);
  const exam=a.page('x',null);
  assert.ok(exam.includes('#/rupho/exam?stage=x'));
  const final=a.page('final',2026);
  for(const grade of ['T1','T2','T3'])assert.ok(final.includes(`RuPhO_2026_${grade}`),grade);
});

test('stage changes retain year and study mode as separate route segments',()=>{
  const a=app();
  for(const mode of ['exam','review']){
    for(const letter of ['w','x','y']){
      assert.equal(a.archive.canonical(`#/rupho${letter}/2025/${mode}`),`#/rupho/2025/${mode}?stage=${letter}`);
      assert.equal(a.archive.href(`rupho${letter}`,`2025/${mode}`),`#/rupho/2025/${mode}?stage=${letter}`);
      assert.equal(a.archive.href(`rupho${letter}`,2025,mode),`#/rupho/2025/${mode}?stage=${letter}`);
    }
    const route=a.archive.route(`#/rupho/2025/${mode}?stage=x`);
    assert.equal(route.year,'2025');assert.equal(route.mode,mode);assert.equal(route.key,'ruphox');
    const selector=a.archive.selector('ruphox',`2025/${mode}`,'en');
    assert.match(selector,new RegExp(`#/rupho/2025/${mode}\\?stage=x`));
    assert.doesNotMatch(selector,/%2f/i);
    const unavailable=a.archive.selector('rupho',`1967/${mode}`,'en');
    assert.match(unavailable,new RegExp(`#/rupho/${mode}\\?stage=x`));
    assert.doesNotMatch(unavailable,new RegExp(`#/rupho/1967/${mode}\\?stage=x`));
    const decorated=a.archive.decorate('ruphox',`<div class="phead"><a href="#/ruphox/2025/${mode}">continue</a></div>`,`2025/${mode}`,'en');
    assert.match(decorated,new RegExp(`href="#/rupho/2025/${mode}\\?stage=x"`));
    assert.doesNotMatch(decorated,/%2f/i);
    assert.equal(a.archive.canonical(`#/rupho/2025%2F${mode}?stage=x`),`#/rupho/2025/${mode}?stage=x`);
  }
});
