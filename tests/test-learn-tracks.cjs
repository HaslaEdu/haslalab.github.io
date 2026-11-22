/* Exam tracks, the Learn translations and the static problem pages: the generated files match their sources, every
   problem validates, every formula renders, and the pages carry what a search engine needs. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),path=require('path'),{execFileSync}=require('child_process');
const root=path.join(__dirname,'..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const katex=require(path.join(root,'vendor/katex/katex.min.js'));
const run=(...a)=>execFileSync(process.execPath,a,{cwd:root,encoding:'utf8'});

test('generated track data, translations and problem pages are up to date',()=>{
  assert.match(run('tools/practice/build-tracks.mjs','--check'),/up to date/);
  assert.match(run('tools/i18n/build-learn-i18n.mjs','--check'),/up to date/);
  assert.match(run('tools/seo/build-problem-pages.mjs','--check'),/up to date/);
});

test('every track problem is complete, has one right answer and only formulas that KaTeX renders',()=>{
  const {tracks}=JSON.parse(read('practice/tracks.json'));
  assert.deepEqual(tracks.map(t=>t.key),['ap1','ap2','apcm','jeem']);
  const P=require(path.join(root,'learn-path.js')),units=new Set(P.AREAS.flatMap(a=>a.subtopics.map(s=>a.key+'/'+s.key)));
  let n=0,math=0;
  for(const t of tracks){
    const items=JSON.parse(read(`practice/track/${t.key}.json`)).items;
    assert.equal(items.length,t.n);assert.equal(new Set(items.map(i=>i.id)).size,items.length);
    for(const s of t.syl)assert.equal(items.filter(i=>i.syl===s.key).length,s.n);
    for(const i of items){
      n++;assert.ok(units.has(i.unit),i.id);assert.ok(i.hints.length>=1&&i.sol);
      if(i.type==='mc'){assert.equal(i.choices.length,4);assert.ok(i.answer>=0&&i.answer<4);}
      else{assert.ok(Number.isFinite(i.answer.value));if(i.answer.tol===0)assert.ok(Number.isInteger(i.answer.value),i.id);}
      for(const s of [i.q,i.sol,...i.hints,...(i.choices||[])])for(const m of s.match(/\$\$[\s\S]+?\$\$|\$[^$]+?\$/g)||[]){
        math++;assert.doesNotThrow(()=>katex.renderToString(m.replace(/^\$\$?|\$?\$$/g,''),{throwOnError:true}),`${i.id}: ${m}`);}
    }
  }
  assert.ok(n>=190&&math>1500);
});

test('the Learn pages speak seven languages and fall back to English for anything missing',()=>{
  const I=require(path.join(root,'learn-i18n.js'));
  assert.deepEqual(I.LANGS,['ko','en','es','pt','id','vi','hi']);
  const cat=JSON.parse(read('tools/i18n/learn-en.json'));
  for(const lang of ['es','pt','id','vi','hi']){
    const missing=cat.filter(x=>I.t(x.en,lang)===x.en&&x.en.length>12);
    assert.ok(missing.length<8,`${lang}: ${missing.length} untranslated`);   /* names such as AP Physics C: Mechanics stay as they are */
  }
  assert.equal(I.t('no such string','es'),'no such string');assert.equal(I.t('Hint','xx'),'Hint');
  for(const f of ['practice.js','concepts.js','compute.js']){
    const src=read(f);
    assert.match(src,/const LANGS=\['ko','en','es','pt','id','vi','hi'\]/,f);
  }
  for(const f of ['practice.html','concepts.html','compute.html'])assert.match(read(f),/<script defer src="learn-i18n\.js\?v=[0-9a-f]{12}"><\/script>/,f);
  assert.match(read('index.html'),/<select id="lang-more"/);
});

test('each problem page has its own title, description, canonical link, the problem and a way into the practice page',()=>{
  const page=read('en/problems/ap1-u1-001/index.html');
  assert.match(page,/<title>AP Physics 1 · Kinematics — practice problem 1 \| HaslaLab<\/title>/);
  assert.match(page,/<link rel="canonical" href="https:\/\/haslalab\.org\/en\/problems\/ap1-u1-001\/">/);
  assert.match(page,/<meta name="description" content="[^"]{40,}">/);
  assert.match(page,/href="https:\/\/haslalab\.org\/\?lang=en#\/learn\/practice\?item=ap1-u1-001"/);
  assert.doesNotMatch(page,/<script(?![^>]*vendor\/katex)/,'only KaTeX runs on the page');
  const map=read('sitemap-learn.xml');
  assert.match(map,/<loc>https:\/\/haslalab\.org\/en\/problems\/jeem-u20-003\/<\/loc>/);
  assert.match(map,/<loc>https:\/\/haslalab\.org\/ko\/problems\/[a-z0-9-]+\/<\/loc>/);
  assert.match(read('robots.txt'),/Sitemap: https:\/\/haslalab\.org\/sitemap-learn\.xml/);
});
