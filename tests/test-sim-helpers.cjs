/* The simulation helpers in sim-sandbox.html: the fixed-step integrators against closed forms, and every editor
   template (sim-templates.js) run headless in the sandbox for a few seconds of simulated time without an error. */
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'..','sim-sandbox.html'),'utf8');
const core=/\/\* @hl-math-begin \*\/([\s\S]*?)\/\* @hl-math-end \*\//.exec(html)[1];
const M=vm.runInNewContext(core+';HLMath',{});
const TPL=require('../sim-templates.js');

/* harmonic oscillator x'' = -ω² x, energy E = (v² + ω² x²)/2 */
const w=2,osc=(t,[x,v])=>[v,-w*w*x];
const energy=([x,v])=>(v*v+w*w*x*x)/2;
function runSteps(step,y,dt,T){let t=0;for(let i=0;i<Math.round(T/dt);i++){y=step(osc,y,t,dt);t+=dt;}return y;}

test('RK4 keeps a harmonic oscillator\'s energy and phase over many periods, and converges at fourth order', () => {
  const y0=[1,0],E0=energy(y0),T=20*Math.PI;   // 20 periods
  const dt=T/6000,y=runSteps(M.rk4,y0,dt,T);
  assert.ok(Math.abs(energy(y)-E0)/E0<1e-6,'energy drift '+(energy(y)-E0));
  assert.ok(Math.abs(y[0]-1)<1e-5&&Math.abs(y[1])<1e-4,'back where it started after 20 periods: '+y);
  const e1=Math.abs(runSteps(M.rk4,y0,0.04,2)[0]-Math.cos(4)),e2=Math.abs(runSteps(M.rk4,y0,0.02,2)[0]-Math.cos(4));
  assert.ok(e1/e2>12&&e1/e2<20,'error ratio for half the step: '+e1/e2);
});

test('Euler is first order and gains energy; velocity Verlet keeps it bounded', () => {
  const y0=[1,0],E0=energy(y0);
  const e1=Math.abs(runSteps(M.euler,y0,1e-3,1)[0]-Math.cos(2)),e2=Math.abs(runSteps(M.euler,y0,5e-4,1)[0]-Math.cos(2));
  assert.ok(e1/e2>1.8&&e1/e2<2.2,'Euler error ratio '+e1/e2);
  assert.ok(energy(runSteps(M.euler,y0,1e-2,10))>E0*1.1,'explicit Euler spirals outwards');
  let x=[1],v=[0],worst=0;
  for(let i=0;i<20000;i++){[x,v]=M.verlet(p=>[-w*w*p[0]],x,v,i*1e-2,1e-2);worst=Math.max(worst,Math.abs(energy([x[0],v[0]])-E0)/E0);}
  assert.ok(worst<1e-3,'Verlet energy error stays small over 200 s: '+worst);
});

test('a projectile without drag lands where the closed form says', () => {
  const g=9.8,v0=20,a=Math.PI/5,f=(t,[x,y,vx,vy])=>[vx,vy,0,-g];
  const T=2*v0*Math.sin(a)/g;
  const r=M.solve(f,[0,0,v0*Math.cos(a),v0*Math.sin(a)],0,T,1e-3);
  const end=r.y[r.y.length-1];
  assert.ok(Math.abs(r.t[r.t.length-1]-T)<1e-12,'the last step lands on t1');
  assert.ok(Math.abs(end[0]-v0*v0*Math.sin(2*a)/g)<1e-9,'range');
  assert.ok(Math.abs(end[1])<1e-9,'back at y = 0');
  const top=Math.max(...r.y.map(y=>y[1]));assert.ok(Math.abs(top-(v0*Math.sin(a))**2/(2*g))<1e-4,'maximum height');
  /* with Verlet too: exact for a constant force */
  let x=[0,0],v=[v0*Math.cos(a),v0*Math.sin(a)];const n=1000;for(let i=0;i<n;i++)[x,v]=M.verlet(()=>[0,-g],x,v,0,T/n);
  assert.ok(Math.abs(x[0]-v0*v0*Math.sin(2*a)/g)<1e-9&&Math.abs(x[1])<1e-9);
});

test('integrators take a plain number as a one-element state, and solve refuses an absurd step count', () => {
  assert.deepEqual([...M.euler((t,[y])=>[2],1,0,0.5)],[2]);
  const r=M.rk4((t,[q])=>[-q],[1],0,0.1);assert.ok(Math.abs(r[0]-Math.exp(-0.1))<1e-7);
  assert.throws(()=>M.solve((t,y)=>y,[1],0,1,1e-9),/too many steps/);
});

/* a headless frame for the templates: a canvas that draws nothing, animation frames driven by the test */
function headless(){
  const listeners={};let ctx,raf=null;const noop=()=>{};
  const g2d=new Proxy({},{get:(o,k)=>k in o?o[k]:k==='measureText'?()=>({width:10}):noop,set:(o,k,v)=>{o[k]=v;return true;}});
  const el=tag=>({tag,children:[],style:{},dataset:{},textContent:'',classList:{add(){},toggle(){},remove(){}},value:'',
    append(...c){this.children.push(...c);for(const x of c)if(x&&x.tag==='script')vm.runInContext(x.textContent,ctx);},
    get lastChild(){return this.children[this.children.length-1]||el('b');},
    getBoundingClientRect:()=>({width:640,height:360,left:0,top:0}),getContext:()=>g2d,addEventListener(){},focus(){},setPointerCapture(){}});
  const parent={posted:[],postMessage(m){this.posted.push(m);}};
  ctx={self:{origin:'null'},parent,devicePixelRatio:1,performance,console:{},setInterval:noop,
    document:{getElementById:el,createElement:el,head:el('head'),body:el('body'),documentElement:{dataset:{},scrollHeight:400}},
    addEventListener:(t,fn)=>{listeners[t]=fn;},requestAnimationFrame(fn){raf=fn;}};
  ctx.globalThis=ctx;vm.createContext(ctx);
  for(const m of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g))vm.runInContext(m[1],ctx);
  return {parent,run(code,seconds){listeners.message({source:parent,data:{type:'run',code}});let t=0;for(let i=0;i<seconds*60&&raf;i++){const f=raf;raf=null;t+=1000/60;f(t);}},ctx};
}

test('every template runs for five seconds without an error and shows its readouts', () => {
  assert.ok(TPL.list.length>=9);
  for(const id of ['projectile','spring','pendulum','orbit','magnetic','wave','gas','rc'])assert.ok(TPL.byId(id),id);
  for(const t of TPL.list){
    const f=headless();
    f.run(t.code,5);
    const e=f.parent.posted.find(m=>m.type==='sim-error');
    assert.equal(e,undefined,t.id+': '+(e&&e.message));
    assert.ok(f.ctx.hl.t>0.5,t.id+' advanced in simulated time ('+f.ctx.hl.t+')');
  }
});
