/* Exam tracks and the static problem pages: the generated files match their sources, every
   problem validates, every formula renders, and the pages carry what a search engine needs. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),path=require('path'),{execFileSync}=require('child_process');
const root=path.join(__dirname,'..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const katex=require(path.join(root,'vendor/katex/katex.min.js'));
const run=(...a)=>execFileSync(process.execPath,a,{cwd:root,encoding:'utf8'});

test('generated track data, translations and problem pages are up to date',()=>{
  assert.match(run('tools/practice/build-tracks.mjs','--check'),/up to date/);
  assert.match(run('tools/seo/build-problem-pages.mjs','--check'),/up to date/);
});

test('every track problem is complete, has one right answer and only formulas that KaTeX renders',()=>{
  const {tracks}=JSON.parse(read('practice/tracks.json'));
  for(const k of ['ap1','ap2','apcm','jeem','fma','usapho'])assert.ok(tracks.some(t=>t.key===k),k);
  const P=require(path.join(root,'learn-path.js')),units=new Set(P.AREAS.flatMap(a=>a.subtopics.map(s=>a.key+'/'+s.key)));
  let n=0,math=0;
  for(const t of tracks){
    const items=JSON.parse(read(`practice/track/${t.key}.json`)).items;
    assert.equal(items.length,t.n);assert.equal(new Set(items.map(i=>i.id)).size,items.length);
    for(const s of t.syl)assert.equal(items.filter(i=>i.syl===s.key).length,s.n);
    for(const i of items){
      n++;assert.ok(units.has(i.unit),i.id);assert.ok(i.hints.length>=1&&i.sol);
      if(i.type==='mc'){const n=t.key==='fma'?5:4;assert.equal(i.choices.length,n,i.id);assert.ok(i.answer>=0&&i.answer<n);}
      else{assert.ok(Number.isFinite(i.answer.value));if(i.answer.tol===0)assert.ok(Number.isInteger(i.answer.value),i.id);}
      for(const s of [i.q,i.sol,...i.hints,...(i.choices||[])])for(const m of s.match(/\$\$[\s\S]+?\$\$|\$[^$]+?\$/g)||[]){
        math++;assert.doesNotThrow(()=>katex.renderToString(m.replace(/^\$\$?|\$?\$$/g,''),{throwOnError:true}),`${i.id}: ${m}`);}
    }
  }
  assert.ok(n>=190&&math>1500);
});

test('the Learn pages are in Korean and English only, for now',()=>{
  for(const f of ['practice.js','concepts.js','compute.js'])assert.match(read(f),/const LANGS=\['ko','en'\];/,f);
  assert.ok(!fs.existsSync(path.join(root,'learn-i18n.js')));
  assert.doesNotMatch(read('index.html'),/lang-more|learn-i18n/);
  assert.match(read('index.html'),/const UI_LANGS = \["ko","en"\];/);
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

test('each region starts on its own exams: Korea AP and calculation problems, India JEE, the US F=ma and USAPhO, elsewhere AP',()=>{
  const P=require(path.join(root,'learn-path.js'));
  assert.equal(P.guessRegion('ko',''),'kr');assert.equal(P.guessRegion('en','Asia/Kolkata'),'in');
  assert.equal(P.guessRegion('en','America/Los_Angeles'),'us');assert.equal(P.guessRegion('en','Europe/Berlin'),'global');
  assert.deepEqual(P.startExams({region:'in',goal:'exam'}),['jeem']);
  assert.deepEqual(P.startExams({region:'us',goal:'olympiad'}),['fma','usapho']);
  assert.deepEqual(P.startExams({region:'global',goal:'school'}),['ap1','ap2','apcm']);
  assert.deepEqual(P.startExams({region:'kr',goal:'exam'}),['ap1','ap2','apcm','calc'],'Korea: AP-level physics and the Korean exams’ calculation problems, no CSAT framing');
  assert.equal(P.startStep({level:'middle',goal:'curious'}),2);
  assert.equal(P.startStep({level:'high2',goal:'olympiad',oly:2}),7);
  assert.equal(P.startStep({level:'high2',goal:'exam',region:'in'}),5);
  assert.equal(P.startStep({}),3);
  /* every exam a region points to is a defined track (the page skips one whose problems are not published yet) */
  const tracks=new Set(execFileSync(process.execPath,['--input-type=module','-e',"import('./tools/practice/build-tracks.mjs').then(m=>console.log(m.TRACKS.map(t=>t.key).join(',')))"],{cwd:root,encoding:'utf8'}).trim().split(','));
  for(const r of Object.values(P.REGIONS))for(const k of [...r.exam,...r.olympiad,...r.other])assert.ok(k==='calc'||tracks.has(k),k);
  const js=read('practice.js');
  assert.match(js,/async function todayHome\(\)\{\s*\/\*[^*]*\*\/\s*if\(!saved\.profile\)\{quickStart\(\);return;\}/,'the first visit shows the four level cards, then the first problem');
  assert.match(js,/else if\(mode==='start'\)startHome/,'the full questions stay one link away (after sign-up)');
  assert.match(read('index.html'),/sessionStorage\.setItem\("hlCmBack","#\/learn\/practice\?mode=start"\)/,'a new member goes to the questions after signing up');
});
