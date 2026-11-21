const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process'),os=require('node:os');
const C=require('../compute-problems.js'),P=require('../learn-path.js');
const read=file=>fs.readFileSync(path.join(__dirname,'..',file),'utf8');

test('every computational problem is bilingual, placed on the learning path, and asks for a function',()=>{
  const ids=new Set();
  for(const p of C.PROBLEMS){
    assert.match(p.id,/^[a-z0-9-]{2,40}$/);assert.ok(!ids.has(p.id),p.id);ids.add(p.id);
    for(const f of ['title','statement'])for(const l of ['ko','en'])assert.ok(p[f][l],p.id+' '+f+' '+l);
    assert.ok(P.SUBTOPICS.has(p.area+'/'+p.subtopic),p.id);assert.ok(p.step>=1&&p.step<=10,p.id);
    const fn=/_need\(ns,"(\w+)"\)/.exec(p.grader)[1];
    assert.match(p.starter,new RegExp('def '+fn+'\\('),p.id);assert.match(p.statement.ko,new RegExp('`'+fn+'\\('),p.id);
    assert.match(p.grader,/def grade\(ns\)/);
  }
  assert.equal(C.byId('kepler-orbit').id,'kepler-orbit');assert.equal(C.byId('nope'),null);
});

test('graders pass reference solutions and reject the starter code (needs python3)',t=>{
  const probe=spawnSync('python3',['-c','print(1)']);
  if(probe.status!==0){t.skip('python3 not available');return;}
  const solutions=JSON.parse(read('tests/fixtures/compute-solutions.json'));
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'hl-compute-'));
  const job=path.join(dir,'job.json');
  fs.writeFileSync(job,JSON.stringify({common:C.COMMON,problems:C.PROBLEMS.map(p=>({id:p.id,grader:p.grader,starter:p.starter,solution:solutions[p.id]}))}));
  const script=`
import json,sys
d=json.load(open(sys.argv[1]))
out={}
for p in d["problems"]:
    r={}
    for kind in ("solution","starter"):
        ns={}
        try:
            exec(p[kind],ns); g={}; exec(d["common"]+p["grader"],g); res=g["grade"](ns)
            r[kind]=all(t["ok"] for t in res["tests"]) and len(res["tests"])>0
        except Exception as e:
            r[kind]="error: %s"%e
    out[p["id"]]=r
print(json.dumps(out))`;
  const run=spawnSync('python3',['-I','-c',script,job],{encoding:'utf8',timeout:120000});
  fs.rmSync(dir,{recursive:true,force:true});
  assert.equal(run.status,0,run.stderr);
  const result=JSON.parse(run.stdout);
  for(const p of C.PROBLEMS){
    assert.equal(result[p.id].solution,true,p.id+' reference solution must pass: '+result[p.id].solution);
    assert.notEqual(result[p.id].starter,true,p.id+' starter code must not pass');
  }
});

test('the compute page only runs code in its own worker, and its CSP allows nothing else to load',()=>{
  const html=read('compute.html'),worker=read('compute-worker.js');
  const csp=/Content-Security-Policy" content="([^"]+)"/.exec(html)[1];
  assert.match(csp,/script-src 'self';/);assert.match(csp,/connect-src 'none'/);assert.match(csp,/worker-src 'self'/);
  assert.match(worker,/cdn\.jsdelivr\.net\/pyodide\/v0\.26\.4\/full\//,'Pyodide is pinned to one version');
  assert.doesNotMatch(read('compute.js'),/searchParams\.get\(['"]code['"]\)|fetch\(/,'code never comes from the URL or the network');
});
