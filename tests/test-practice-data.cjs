const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const P=require('../learn-path.js');
const root=path.join(__dirname,'..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const index=JSON.parse(read('practice/index.json'));
const shards=Object.fromEntries(fs.readdirSync(path.join(root,'practice/data')).map(f=>[f.replace(/\.json$/,''),JSON.parse(read('practice/data/'+f)).items]));

test('every practice item has a unit on the learning path, a school-exam step, five choices and an answer',()=>{
  const ids=new Set();let total=0;
  for(const [area,items] of Object.entries(shards)){
    for(const it of items){
      total++;assert.ok(!ids.has(it.id),it.id);ids.add(it.id);
      assert.ok(P.SUBTOPICS.has(it.u),it.id+' '+it.u);assert.equal(it.u.split('/')[0],area,it.id);
      assert.ok(it.s>=2&&it.s<=6,it.id+' step '+it.s);
      assert.equal(it.ch.length,5,it.id);assert.deepEqual(it.ch.map(c=>c.n),[1,2,3,4,5]);
      assert.ok(Number.isInteger(it.a)&&it.a>=1&&it.a<=5,it.id);
      assert.ok(it.b.length>0,it.id);assert.ok(it.src&&it.by,it.id);
    }
  }
  assert.equal(total,index.total);
  const counted=Object.values(index.counts).flatMap(c=>Object.values(c)).reduce((a,b)=>a+b,0);
  assert.equal(counted,total);
});

test('every figure the items show is in the repository; nothing points at the retired PhysLeague assets',()=>{
  const files=new Set(fs.readdirSync(path.join(root,'practice/fig')));
  const used=new Set();
  const walk=blocks=>{for(const b of blocks){if(b.f){assert.ok(files.has(b.f),b.f);assert.ok(b.w>0&&b.h>0);used.add(b.f);}}};
  for(const items of Object.values(shards))for(const it of items){walk(it.b);for(const c of it.ch)walk(c.c);}
  assert.equal(used.size,files.size,'no unused figure files');
  assert.doesNotMatch(JSON.stringify(shards),/exam-assets|physleague/i);
});

test('every item carries its source and the index carries the permission note',()=>{
  for(const items of Object.values(shards))for(const it of items){
    assert.match(it.src,/(학년도|년 \d+월) .+ 물리학[ⅠⅡ] \d+번$/,it.id);
    if(it.pdf)assert.match(it.pdf,/^https:\/\//,it.id);
  }
  assert.match(index.attribution,/한국교육과정평가원/);
});

test('classifications cover every item and record how each was made',()=>{
  const c=JSON.parse(read('tools/practice/classifications.json'));
  for(const items of Object.values(shards))for(const it of items){assert.equal(c.units[it.id],it.u,it.id);assert.ok(['keyword','model'].includes(c.method[it.id]),it.id);}
});

test('the competition challenge lists the six competitions with papers on the PDF Worker only',()=>{
  const c=JSON.parse(read('practice/contests.json')).contests;
  assert.deepEqual(c.map(x=>x.key).sort(),['baupc','eotvos','eupho','opho','physcup','wopho']);
  const ids=new Set();
  for(const contest of c){
    assert.ok(contest.name.ko&&contest.name.en&&contest.step>=7&&contest.step<=10,contest.key);
    assert.ok(contest.problems.length>0,contest.key);
    for(const p of contest.problems){
      assert.ok(!ids.has(p.id),p.id);ids.add(p.id);
      const urls=[...Object.values(p.papers),...Object.values(p.sols)];
      assert.ok(Object.keys(p.papers).length>0,p.id);
      for(const u of urls)assert.match(u,/^https:\/\/haslalab-pdf\.haslalab\.workers\.dev\/pdf\/[\w./-]+\.pdf$/,p.id);
    }
  }
});

test('every practice mode lets the learner skip a problem',()=>{
  const js=read('practice.js');
  assert.equal((js.match(/id="skip"/g)||[]).length,3,'exam, bank and contest problems each have a skip button');
  assert.match(read('practice.html'),/connect-src 'self' https:\/\/haslalab-problem-bank\.haslalab\.workers\.dev https:\/\/haslalab-pdf\.haslalab\.workers\.dev/);
});

test('transcribed competition problems have text, figures that exist, and point back to their paper',()=>{
  const dir=path.join(root,'practice/contest');
  if(!fs.existsSync(dir))return;
  const list=JSON.parse(read('practice/contests.json')).contests,papers=new Map(list.flatMap(c=>c.problems.map(p=>[p.id,c.key])));
  const figs=new Set(fs.readdirSync(path.join(dir,'fig'))),used=new Set(),ids=new Set();
  for(const file of fs.readdirSync(dir).filter(f=>f.endsWith('.json'))){
    const {contest,items}=JSON.parse(fs.readFileSync(path.join(dir,file),'utf8'));
    assert.equal(list.find(c=>c.key===contest).structured,items.length,contest);
    for(const it of items){
      assert.ok(!ids.has(it.id),it.id);ids.add(it.id);
      assert.equal(papers.get(it.pdf),contest,it.id);assert.ok(it.id.startsWith(it.pdf+'~'),it.id);
      assert.ok(it.b.some(b=>b.t),it.id);
      for(const b of it.b){if(b.f){assert.ok(figs.has(b.f),b.f);used.add(b.f);}else assert.equal(typeof b.t,'string');}
      assert.doesNotMatch(JSON.stringify(it.b),/<script|javascript:/i);
    }
  }
  assert.equal(used.size,figs.size,'only placed figures are stored');
});
