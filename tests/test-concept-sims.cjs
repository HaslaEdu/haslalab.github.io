const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const P=require('../learn-path.js');
/* load concepts.js against an inert DOM and read window.HL_CONCEPT_SIMS */
function sims(){
  const el=()=>new Proxy(function(){},{get:(t,k)=>k==='querySelectorAll'?()=>[]:k==='dataset'?{}:k==='classList'?{toggle(){},add(){}}:k==='style'?{}:k==='getContext'?()=>new Proxy({},{get:()=>()=>{}}):typeof k==='string'&&/^(clientWidth|clientHeight|width|height)$/.test(k)?100:el(),set:()=>true,apply:()=>el()});
  const window={};
  const ctx={window,URL,URLSearchParams,location:{href:'http://x/concepts.html'},document:{getElementById:()=>el(),querySelectorAll:()=>[],documentElement:{dataset:{},classList:{toggle(){}},lang:''},title:''},
    getComputedStyle:()=>({getPropertyValue:()=>''}),matchMedia:()=>({matches:false}),requestAnimationFrame(){},addEventListener(){},devicePixelRatio:1,console};
  ctx.window=Object.assign(window,ctx);vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'..','concepts.js'),'utf8'),ctx);
  return Object.fromEntries(window.HL_CONCEPT_SIMS.map(s=>[s.id,s]));
}
const S=sims();
const run=(id,p,T,stop)=>{const sim=S[id],s=sim.init(p);let t=0;while(t<T&&!s.done&&!(stop&&stop(s))){sim.step.call(sim,s,p,0.0005);t+=0.0005;}return s;};

test('every concept simulation is bilingual, sits on the learning path and has a quiz with one answer',()=>{
  for(const sim of Object.values(S)){
    assert.ok(P.SUBTOPICS.has(sim.unit),sim.id);
    for(const f of ['title','intro'])assert.ok(sim[f].ko&&sim[f].en,sim.id+' '+f);
    const choices=Array.isArray(sim.quiz.choices)?sim.quiz.choices:sim.quiz.choices.ko;
    assert.ok(sim.quiz.a>=0&&sim.quiz.a<choices.length,sim.id);
  }
});
test('the simulations reproduce the physics their quizzes ask about',()=>{
  assert.ok(Math.abs(run('pulley-cart',{M:2,m:1,mu:0},0.5).a-9.8/3)<1e-9,'Atwood: a = g/3');
  assert.ok(Math.abs(run('hemisphere',{R:1,v0:0.02},5,s=>!s.on).leave.h-2/3)<0.005,'leaves the hemisphere at 2R/3');
  assert.ok(Math.abs(run('projectile',{v0:18,ang:45,k:0},10).x-18*18/9.8)<1e-3,'range v0²/g at 45°');
  assert.ok(Math.abs(run('pendulum',{Lp:1,th0:5},6).period-2*Math.PI*Math.sqrt(1/9.8))/2.007<0.002,'small-angle period');
  assert.ok(run('pendulum',{Lp:1,th0:120},8).period>2.7,'large amplitude is slower');
  const e=run('collision',{m1:1,m2:1,u1:2,u2:0,e:1},3);assert.deepEqual([+e.v1.toFixed(9),+e.v2.toFixed(9)],[0,2]);
  const i=run('collision',{m1:1,m2:1,u1:2,u2:0,e:0},3);assert.deepEqual([i.v1,i.v2],[1,1]);
  assert.equal(Math.hypot(...S.charges.field({q1:1,q2:1},0,0)),0);
});
