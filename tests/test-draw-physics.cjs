/* The figure editor's solver (draw-physics.mjs) against closed-form answers, the scene check (draw-scene.mjs) and the
   SVG drawing (draw-render.mjs) */
const test=require('node:test'),assert=require('node:assert/strict');
const load=()=>Promise.all([import('../draw-scene.mjs'),import('../draw-physics.mjs'),import('../draw-render.mjs')]).then(([S,P,R])=>({S,P,R}));
const g=9.8,near=(a,b,rel,msg)=>assert.ok(Math.abs(a-b)<=rel*Math.abs(b),`${msg}: ${a} vs ${b}`);
const scene=(S,objects,extra={})=>{const r=S.validateScene({g,objects:objects.map(o=>({...S.defaults(o.type),...o})),...extra});assert.ok(r.ok,JSON.stringify(r.errors));return r.scene;};
/* times at which q crosses zero going the same way, linearly interpolated between solver steps */
function period(sim,read,T,dt=1e-3){
  const ups=[];let prev=read(sim),t=0;
  while(t<T){sim.advanceTo(t+dt);const v=read(sim);if(prev<0&&v>=0)ups.push(t+dt*(-prev/(v-prev)));prev=v;t+=dt;}
  return (ups.at(-1)-ups[0])/(ups.length-1);
}

test('Atwood machine: a = (m1 − m2) g / (m1 + m2), T = 2 m1 m2 g / (m1 + m2)',async()=>{
  const {S,P}=await load();
  for(const [m1,m2] of [[3,2],[5,1],[1.2,1]]){
    const sc=S.validateScene(S.template('atwood')).scene;
    sc.objects.find(o=>o.id==='m1').mass=m1;sc.objects.find(o=>o.id==='m2').mass=m2;
    const sim=P.buildSim(sc);assert.equal(sim.systems[0].kind,'chain');
    const a=(m1-m2)*g/(m1+m2);
    near(-sim.accelerations().get('m1').y,a,1e-9,'acceleration');near(sim.tensions().s1,2*m1*m2*g/(m1+m2),1e-9,'tension');
    const y0=sim.poses().get('m1').y;sim.run(0.5);near(y0-sim.poses().get('m1').y,a*0.25/2,1e-6,'distance after 0.5 s');
  }
});

test('a block sliding down an incline with friction: a = g (sin θ − μ cos θ); it stays put when tan θ ≤ μ',async()=>{
  const {S,P}=await load();
  const make=(angle,mu)=>scene(S,[{id:'inc',type:'incline',x:0,y:0,angle,length:5,mu},{id:'b',type:'block',on:'inc',at:4,w:0.2,h:0.2,mass:2}]);
  for(const [th,mu] of [[30,0.2],[40,0.5],[25,0]]){
    const sim=P.buildSim(make(th,mu)),r=th*Math.PI/180,a=g*(Math.sin(r)-mu*Math.cos(r));
    sim.run(0.8);const v=sim.velocities().get('b');near(Math.hypot(v.x,v.y),a*0.8,1e-6,`speed at θ=${th}, μ=${mu}`);
    near(4-sim.poses().get('b').at,a*0.32,1e-6,'distance');
    const e=sim.energy();near(e.E+e.heat,P.buildSim(make(th,mu)).energy().E,1e-9,'energy lost = heat');
  }
  const held=P.buildSim(make(20,0.5));held.run(2);assert.equal(held.poses().get('b').at,4,'static friction holds');
  const fr=held.forces().get('b').find(x=>x.kind==='friction');near(Math.hypot(fr.v.x,fr.v.y),2*g*Math.sin(20*Math.PI/180),1e-9,'static friction = mg sin θ');
});

test('incline, pulley and hanging mass: a = (m2 − m1 sin θ − μ m1 cos θ) g / (m1 + m2); the hanging mass lands',async()=>{
  const {S,P}=await load();
  const sc=S.validateScene(S.template('incline_pulley')).scene,sim=P.buildSim(sc),r=Math.PI/6;
  const a=(3-2*Math.sin(r)-0.1*2*Math.cos(r))*g/5;
  near(-sim.accelerations().get('m2').y,a,1e-9,'acceleration');near(sim.tensions().s1,3*(g-a),1e-9,'tension m2 (g − a)');
  sim.run(5);assert.equal(sim.events[0].code,'landed');assert.equal(sim.events[0].id,'m2');
  const drop=0.75-0.12;near(sim.events[0].t,Math.sqrt(2*drop/a),1e-6,'landing time');
});

test('block on a spring: period 2π√(m/k), energy kept',async()=>{
  const {S,P}=await load();
  for(const [m,k] of [[1,40],[0.5,200],[2,10]]){
    const sc=S.validateScene(S.template('spring_block')).scene;sc.objects.find(o=>o.id==='m1').mass=m;sc.objects.find(o=>o.id==='k1').k=k;
    const sim=P.buildSim(sc),x0=sim.poses().get('m1').x,c=x0-0.25,E0=sim.energy().E;
    near(period(sim,s=>s.poses().get('m1').x-c,4*2*Math.PI*Math.sqrt(m/k)+0.1),2*Math.PI*Math.sqrt(m/k),2e-4,`period m=${m} k=${k}`);
    assert.ok(Math.abs(sim.energy().E-E0)<1e-9*E0+1e-9,'no drift');
  }
});

test('simple pendulum: small-angle period 2π√(L/g); energy drift small over 20 s',async()=>{
  const {S,P}=await load();
  const L=1.2,make=deg=>{const a=deg*Math.PI/180;return scene(S,[{id:'pv',type:'pivot',x:0,y:2},{id:'b',type:'ball',x:L*Math.sin(a),y:2-L*Math.cos(a),r:0.05,mass:0.4},{id:'s',type:'string',a:'pv',b:'b'}]);};
  const sim=P.buildSim(make(2));
  near(period(sim,s=>s.poses().get('b').x,6),2*Math.PI*Math.sqrt(L/g),5e-4,'period at 2°');
  const big=P.buildSim(make(60)),E0=big.energy().E;big.run(20);
  assert.ok(Math.abs(big.energy().E-E0)/E0<1e-8,'relative energy drift '+Math.abs(big.energy().E-E0)/E0);
  near(P.buildSim(make(0)).tensions().s,0.4*g,1e-9,'tension at rest = mg');
});

test('projectile: range v² sin 2θ / g, landing time 2 v sin θ / g',async()=>{
  const {S,P}=await load();
  for(const [v,deg] of [[10,45],[15,30],[8,70]]){
    const a=deg*Math.PI/180;
    const sim=P.buildSim(scene(S,[{id:'f',type:'floor',x:-1,y:0,w:40},{id:'b',type:'ball',x:0,y:0.1,r:0.1,mass:0.2,vx:v*Math.cos(a),vy:v*Math.sin(a)}]));
    sim.run(10);assert.equal(sim.events[0].code,'landed');
    near(sim.poses().get('b').x,v*v*Math.sin(2*a)/g,1e-7,`range v=${v} θ=${deg}`);near(sim.events[0].t,2*v*Math.sin(a)/g,1e-7,'time');
  }
});

test('conical pendulum: ω = √(g / (L cos α)), T = mg / cos α; vertical circle: the string goes slack below the critical speed',async()=>{
  const {S,P}=await load();
  const sc=S.validateScene(S.template('conical')).scene,sim=P.buildSim(sc),s=sim.systems[0];
  const pv=sc.objects.find(o=>o.id==='pv'),b=sc.objects.find(o=>o.id==='b1'),L=Math.hypot(b.x-pv.x,b.y-pv.y),cos=(pv.y-b.y)/L;
  assert.equal(s.kind,'conical');near(s.omega,Math.sqrt(g/(L*cos)),1e-12,'ω');near(sim.tensions().s1,0.5*g/cos,1e-12,'tension');
  near(cos,Math.cos(Math.PI/6),1e-4,'the template hangs at 30°');
  const x0=sim.poses().get('b1').x;sim.run(s.period);near(sim.poses().get('b1').x,x0,1e-9,'back after one period');
  const vc=P.buildSim(S.validateScene(S.template('vertical_circle')).scene);vc.run(3);
  assert.equal(vc.events[0].code,'slack');
  /* slack where v² = g r cos φ with v² = v0² − 2 g r (1 + cos φ): cos φ = (v0² − 2gr)/(3gr) above the centre */
  const cosphi=(36-2*g)/(3*g),p=vc.poses().get('b1');near(p.y-1.5,cosphi,1e-5,'height where the string slackens');
});

test('the scene check is strict: types, ranges, references, sizes',async()=>{
  const {S}=await load();
  const bad=(objects,code)=>{const r=S.validateScene({objects});assert.ok(!r.ok);assert.ok(r.errors.some(e=>e.code===code),code+' '+JSON.stringify(r.errors));};
  bad([{id:'a',type:'block',mass:0}],'out_of_range');
  bad([{id:'a',type:'block',mass:'2'}],'bad_number');
  bad([{id:'a',type:'teleporter'}],'bad_type');
  bad([{id:'a',type:'floor'},{id:'a',type:'floor'}],'dup_id');
  bad([{id:'1a',type:'floor'}],'bad_id');
  bad([{id:'s',type:'string',a:'x',b:'y'}],'bad_ref');
  bad([{id:'p',type:'pivot'},{id:'s',type:'spring',a:'p',b:'p'}],'same_ends');
  bad([{id:'f',type:'floor'},{id:'b',type:'block',on:'f'},{id:'c',type:'block'},{id:'d',type:'block'},{id:'s1',type:'string',a:'b',b:'c'},{id:'s2',type:'string',a:'b',b:'d'}],'two_strings');
  bad(Array.from({length:61},(_,i)=>({id:'f'+i,type:'floor'})),'too_many');
  bad([{id:'l',type:'label',text:'x'.repeat(10)+'\u0000'.repeat(1),size:100}],'out_of_range');
  assert.ok(!S.validateScene(null).ok);assert.ok(!S.validateScene({format:'other',objects:[]}).ok);
  for(const k of S.TEMPLATE_KEYS)assert.ok(S.validateScene(S.template(k,'en')).ok,k);
  const lenient=S.validateScene({objects:[{id:'a',type:'block',mass:-3},{id:'s',type:'string',a:'a',b:'gone'}]},{lenient:true});
  assert.ok(lenient.ok);assert.deepEqual(lenient.scene.objects.map(o=>o.id),['a']);assert.equal(lenient.scene.objects[0].mass,0.001);
});

test('unsupported systems are reported, not simulated wrongly',async()=>{
  const {S,P}=await load();
  const sim=P.buildSim(scene(S,[{id:'p',type:'pulley',x:1,y:2},{id:'a',type:'block',x:0.5,y:1},{id:'b',type:'block',x:1.1,y:1},{id:'s',type:'string',a:'a',b:'b',over:['p']}]));
  assert.deepEqual(sim.unsupported.map(u=>u.code),['hanging_not_vertical']);assert.equal(sim.systems.length,0);
});

test('the SVG: escaped labels, subscripts, no scripts or outside references',async()=>{
  const {S,R}=await load();
  const sc=S.validateScene({objects:[{id:'b',type:'block',x:0,y:0,label:'m_1'},{id:'l',type:'label',x:1,y:1,text:'<script>alert(1)</script>'}]}).scene;
  const svg=R.renderSVG(sc,{view:{x:-1,y:-1,w:3,h:3}});
  assert.ok(!/<script/i.test(svg));assert.match(svg,/&lt;script&gt;/);assert.ok(!/href|url\(|on\w+=/i.test(svg));
  assert.match(svg,/<tspan font-style="italic">m<\/tspan><tspan dy="[\d.]+" font-size="[\d.]+">1<\/tspan>/);
  assert.deepEqual(R.texRuns('2 kg'),[{t:'2 kg',it:false,sh:''}]);assert.equal(R.texRuns('\\theta')[0].t,'θ');
});
