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
  bad(Array.from({length:S.MAX_OBJECTS+1},(_,i)=>({id:'f'+i,type:'floor'})),'too_many');
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
  assert.ok(!/<script/i.test(svg));assert.match(svg,/&lt;/);assert.match(svg,/&gt;/);assert.ok(!/href|url\(|on\w+=/i.test(svg));
  assert.match(svg,/<tspan x="[\d.]+" y="([\d.]+)" font-style="italic">m<\/tspan><tspan x="[\d.]+" y="([\d.]+)" font-size="[\d.]+">1<\/tspan>/);
  const [,y1,y2]=/<tspan x="[\d.]+" y="([\d.]+)" font-style="italic">m<\/tspan><tspan x="[\d.]+" y="([\d.]+)"/.exec(svg);assert.ok(+y2>+y1,'the 1 is a subscript, lower than the m');
  assert.deepEqual(R.texRuns('2 kg'),[{t:'2 ',it:false,sh:''},{t:'kg',it:false,sh:''}]);assert.equal(R.texRuns('\\theta')[0].t,'θ');
});

/* ── the other domains (draw-physics.mjs), against closed forms ── */
const K=8.9875517923e9,h=6.62607015e-34,me=9.1093837015e-31,eV=1.602176634e-19,hbar=h/(2*Math.PI);
const loadAll=load;

test('point charge: E = kq/r² along r̂; a dipole on its axis; field lines run from + to −',async()=>{
  const {S,P}=await loadAll();
  const q=2e-6,c=[{x:1,y:-1,q}];
  for(const p of [{x:1.5,y:-1},{x:1,y:0.2},{x:-0.3,y:0.4}]){
    const E=P.eField(c,p),r=Math.hypot(p.x-1,p.y+1);
    near(Math.hypot(E.x,E.y),K*q/r**2,1e-12,'magnitude');near((E.x*(p.x-1)+E.y*(p.y+1))/(Math.hypot(E.x,E.y)*r),1,1e-12,'radial, outward');
  }
  const neg=P.eField([{x:0,y:0,q:-q}],{x:0,y:2});assert.ok(neg.y<0,'towards a negative charge');
  /* the midpoint of a dipole ±q at ∓a: E = 2kq/a², from + towards − */
  const a=0.7,mid=P.eField([{x:-a,y:0,q},{x:a,y:0,q:-q}],{x:0,y:0});near(mid.x,2*K*q/a**2,1e-12,'dipole midpoint');near(mid.y+1,1,1e-9,'no y part');
  near(P.potential([{x:0,y:0,q}],{x:3,y:4}),K*q/5,1e-12,'potential kq/r');
  const sc=S.validateScene(S.template('dipole_field')).scene,view=sc.view,lines=P.fieldLines(sc,view,{n:12});
  assert.ok(lines.length>=12);
  const ends=lines.filter(L=>Math.hypot(L.pts.at(-1).x-1,L.pts.at(-1).y)<0.2).length;assert.ok(ends>=6,'most lines from +q end on −q: '+ends);
  for(const L of lines)assert.ok(Math.hypot(L.pts[0].x+1,L.pts[0].y)<0.2,'each starts at +q');
  /* along a line the field is tangent */
  const L=lines[0],i=Math.floor(L.pts.length/3),d=vec2(L.pts[i+1],L.pts[i]),E=P.eField(P.chargesOf(sc),L.pts[i]);near((d.x*E.x+d.y*E.y)/(Math.hypot(d.x,d.y)*Math.hypot(E.x,E.y)),1,1e-4,'tangent');
  assert.ok(P.equipotentials(sc,view,{levels:6}).length>=6,'equipotentials drawn');
});
const vec2=(a,b)=>({x:a.x-b.x,y:a.y-b.y});

test('a charge in a uniform B field moves on a circle of radius mv/(qB); in a uniform E field on a parabola',async()=>{
  const {S,P}=await loadAll();
  const sc=S.validateScene(S.template('particle_in_b')).scene,q=sc.objects.find(o=>o.id==='q1'),B=sc.objects.find(o=>o.id==='B1');
  const pts=P.chargePath(sc,q,sc.view),inside=pts.filter(p=>p.x>B.x+1e-9),top=Math.max(...inside.map(p=>p.y));
  const r=q.mass*1e-6*q.vx/(q.q*1e-6*B.mag);near(top-q.y,2*r,2e-3,'diameter 2mv/(qB)');
  const cap=S.validateScene(S.template('capacitor_charge')).scene,c=cap.objects.find(o=>o.id==='q1'),F=cap.objects.find(o=>o.id==='F1');
  const path=P.chargePath(cap,c,cap.view),exit=path.find(p=>p.x>=F.x+F.w);
  const t=F.w/c.vx,a=c.q/c.mass*F.mag;near(c.y-exit.y,0.5*a*t*t,2e-3,'deflection qEL²/(2mv²)');
});

const el=(id,kind,x1,y1,x2,y2,extra={})=>({id,type:'element',kind,x1,y1,x2,y2,...extra});
test('circuits: series, parallel, internal resistance, Wheatstone balance and the galvanometer current',async()=>{
  const {S,P}=await loadAll();
  const solve=objs=>{const r=S.validateScene({grid:0.25,objects:objs});assert.ok(r.ok,JSON.stringify(r.errors));const c=P.solveCircuit(r.scene);assert.ok(c.ok,c.code);return c;};
  /* a loop: battery up the left side, three resistors along the top, a wire back */
  const E=9,R=[100,220,470];
  let c=solve([el('E1','battery',0,0,0,2,{value:E}),el('R1','resistor',0,2,1,2,{value:R[0]}),el('R2','resistor',1,2,2,2,{value:R[1]}),el('R3','resistor',2,2,3,2,{value:R[2]}),el('W1','wire',3,2,0,0,{route:'vh'})]);
  near(c.el.get('R2').I,E/P.seriesR(...R),1e-9,'series current');near(c.el.get('R3').drop,E*R[2]/P.seriesR(...R),1e-9,'voltage divider');
  c=solve([el('E1','battery',0,0,0,2,{value:E,r:2}),el('R1','resistor',0,2,2,2,{value:40}),el('W1','wire',2,2,2,0),el('W2','wire',2,0,0,0)]);
  near(c.el.get('R1').I,E/42,1e-9,'I = E/(R + r)');
  /* two resistors in parallel: the battery current E (1/R1 + 1/R2); a T junction on a wire joins */
  c=solve([el('E1','battery',0,0,0,2,{value:E}),el('W1','wire',0,2,3,2),el('R1','resistor',1,2,1,0,{value:300}),el('R2','resistor',3,2,3,0,{value:600}),el('W2','wire',3,0,0,0),el('A1','ammeter',0,2,0,2.5)].slice(0,5));
  near(c.el.get('E1').I,E/P.parallelR(300,600),1e-9,'parallel');near(P.parallelR(300,600),200,1e-12,'300 ∥ 600 = 200');
  /* the Wheatstone bridge of the template: balanced when R1/R2 = R3/R4 */
  const sc=S.validateScene(S.template('wheatstone')).scene,wb=P.solveCircuit(sc);
  assert.ok(Math.abs(wb.el.get('G1').I)<1e-9,'balanced: no galvanometer current');
  for(const R4 of [150,450,1000]){
    const s2=structuredClone(sc);s2.objects.find(o=>o.id==='R4').value=R4;const r=P.solveCircuit(s2),g=s2.objects.find(o=>o.id==='G1').value;
    const [R1,R2,R3]=['R1','R2','R3'].map(id=>s2.objects.find(o=>o.id===id).value),Eb=s2.objects.find(o=>o.id==='E1').value;
    /* Thevenin seen by G from B to D (A at 0 V, C at E) */
    const Vth=Eb*(R1/(R1+R2)-R3/(R3+R4)),Rth=P.parallelR(R1,R2)+P.parallelR(R3,R4);
    near(r.el.get('G1').I,Vth/(Rth+g),1e-7,'galvanometer current, R4 = '+R4);
  }
  /* a diode conducts one way only */
  const fwd=solve([el('E1','battery',0,0,0,2,{value:5}),el('D1','diode',0,2,2,2,{value:0.7}),el('R1','resistor',2,2,2,0,{value:100}),el('W1','wire',2,0,0,0)]);near(fwd.el.get('R1').I,4.3/100,1e-9,'forward');
  const rev=solve([el('E1','battery',0,0,0,2,{value:5}),el('D1','diode',2,2,0,2,{value:0.7}),el('R1','resistor',2,2,2,0,{value:100}),el('W1','wire',2,0,0,0)]);assert.ok(Math.abs(rev.el.get('R1').I)<1e-9,'reverse');
});

test('RC charging: τ = RC; behind a divider τ = (R1 ∥ R2) C and V∞ = E R2/(R1 + R2)',async()=>{
  const {S,P}=await loadAll();
  const sc=S.validateScene(S.template('rc_circuit')).scene,c=P.solveCircuit(sc),t=c.transients[0];
  near(t.tau,10000*100e-6,1e-6,'τ = RC');near(t.final,12,1e-6,'V∞ = E');near(t.at(t.tau),12*(1-Math.exp(-1)),1e-6,'V(τ) = E(1 − 1/e)');
  const E=10,R1=1000,R2=3000,C=47;
  const r=S.validateScene({grid:0.25,objects:[el('E1','battery',0,0,0,2,{value:E}),el('R1','resistor',0,2,2,2,{value:R1}),el('R2','resistor',2,2,2,0,{value:R2}),el('C1','capacitor',2,2,4,2,{value:C}),el('W1','wire',4,2,4,0),el('W2','wire',4,0,0,0)]}).scene;
  const d=P.solveCircuit(r).transients[0];near(d.tau,P.parallelR(R1,R2)*C*1e-6,1e-6,'τ');near(d.final,E*R2/(R1+R2),1e-6,'V∞');
  const L=S.validateScene({grid:0.25,objects:[el('E1','battery',0,0,0,2,{value:6}),el('R1','resistor',0,2,2,2,{value:20}),el('L1','inductor',2,2,2,0,{value:0.5}),el('W1','wire',2,0,0,0)]}).scene;
  const rl=P.solveCircuit(L).transients[0];near(rl.tau,0.5/20,1e-6,'RL: τ = L/R');near(rl.final,6/20,1e-6,'I∞ = E/R');
});

test('gas processes: isothermal work P₁V₁ ln(V₂/V₁), adiabatic (P₁V₁ − P₂V₂)/(γ − 1); Carnot η = 1 − T_C/T_H, Otto η = 1 − r^(1−γ)',async()=>{
  const {P}=await loadAll();
  for(const [x1,x2,y1,g] of [[1,4,4,1.4],[2,3,1.5,5/3],[3,1,2,1.3]]){
    near(P.processWork('isotherm',{x1,x2,y1}),y1*x1*Math.log(x2/x1),1e-10,'isotherm');
    const y2=y1*Math.pow(x1/x2,g);near(P.processWork('adiabat',{x1,x2,y1,gamma:g}),(y1*x1-y2*x2)/(g-1),1e-10,'adiabat');
    near(P.processWork('isobar',{x1,x2,y1}),y1*(x2-x1),1e-12,'isobar');
  }
  for(const [Th,Tc,g] of [[600,400,1.4],[900,300,5/3],[500,350,1.3]]){
    const c=P.gasCycle({kind:'carnot',v1:1,v2:2.5,t1:Th,t2:Tc,gamma:g});
    near(c.eta,1-Tc/Th,1e-9,'Carnot');near(c.W,(Th-Tc)*Math.log(2.5),1e-9,'W = nR(T_H − T_C) ln(V_B/V_A)');
    near(c.states[2].P*Math.pow(c.states[2].V,g),c.states[1].P*Math.pow(c.states[1].V,g),1e-12,'B → C is adiabatic');
  }
  const o=P.gasCycle({kind:'otto',v1:1,v2:8,t1:2000,t2:300,gamma:1.4});near(o.eta,1-Math.pow(8,-0.4),1e-9,'Otto');
  const st=P.gasCycle({kind:'stirling',v1:1,v2:3,t1:600,t2:300,gamma:1.4});near(st.W,300*Math.log(3),1e-9,'Stirling W');
});

test('thin lens 1/u + 1/v = 1/f and mirror 1/u + 1/v = 1/f (real is positive), traced; two lenses in turn',async()=>{
  const {S,P}=await loadAll();
  const lensScene=(f,u,hO=0.4)=>S.validateScene({objects:[{id:'L',type:'lens',x:5,y:0,h:2,f},{id:'O',type:'oarrow',x:5-u,y:0,h:hO}]}).scene;
  for(const [f,u] of [[1,2],[1,3.5],[1,0.6],[2,1],[-1.2,2],[-0.5,4],[0.8,1.6]]){
    const sc=lensScene(f,u),im=P.opticImage(sc,sc.objects[1]),v=im.x-5;
    near(1/u+1/v,1/f,1e-9,`lens f=${f} u=${u}`);near(v,P.lensImage(u,f),1e-9,'formula');near(im.m,-v/u,1e-9,'m = −v/u');
    assert.equal(im.real,v>0,'real exactly when v > 0');
  }
  const mirrorScene=(f,u)=>S.validateScene({objects:[{id:'M',type:'mirror',x:5,y:0,h:3,f,face:'left'},{id:'O',type:'oarrow',x:5-u,y:0,h:0.3}]}).scene;
  for(const [f,u] of [[1,2.5],[1,3],[1,0.5],[-1,2],[-2,1.5]]){
    const sc=mirrorScene(f,u),im=P.opticImage(sc,sc.objects[1]),v=5-im.x;
    near(1/u+1/v,1/f,1e-9,`mirror f=${f} u=${u}`);near(im.m,-v/u,1e-9,'m');assert.equal(im.real,v>0);
  }
  const plane=mirrorScene(0,1.7),pi=P.opticImage(plane,plane.objects[1]);near(pi.x,6.7,1e-9,'a plane mirror: as far behind');near(pi.m,1,1e-9,'upright, same size');
  /* two lenses: the image of the first is the object of the second */
  const sc=S.validateScene(S.template('two_lens')).scene,im=P.opticImage(sc,sc.objects.find(o=>o.id==='O'));
  const v1=P.lensImage(2,1),u2=5.5-(2+v1),v2=P.lensImage(u2,1);near(im.x,5.5+v2,1e-9,'final image');near(im.m,(-v1/2)*(-v2/u2),1e-9,'total magnification');
  /* a prism: Snell at both faces gives the minimum-deviation formula n = sin((A + δ)/2)/sin(A/2) at symmetric passage */
  const A=60,n=1.5,dmin=2*Math.asin(n*Math.sin(A*Math.PI/360))*180/Math.PI-A,inc=(A+dmin)/2;
  const pr=S.validateScene({objects:[{id:'p',type:'prism',x:0,y:0,size:2,apex:A,n}]}).scene,corn=P.prismCorners(pr.objects[0]),mid={x:(corn[0].x+corn[2].x)/2,y:(corn[0].y+corn[2].y)/2};
  const dirIn=(inc-A/2)*Math.PI/180,start={x:mid.x-3*Math.cos(dirIn),y:mid.y-3*Math.sin(dirIn)};
  const tr=P.traceRay(pr,start,{x:Math.cos(dirIn),y:Math.sin(dirIn)},{len:10});const dev=(dirIn-Math.atan2(tr.d.y,tr.d.x))*180/Math.PI;
  near(dev,dmin,1e-6,'minimum deviation');
});

test('slits: double-slit fringe spacing λL/d, the single slit\'s first minimum λL/a, a grating\'s orders',async()=>{
  const {S,P}=await loadAll();
  const o={...S.defaults('slits'),n:2,d:0.25,a:0.0001,L:1.5,lambda:600};  /* narrow slits: a flat envelope */
  const m=P.slitMaxima(o),c=m.findIndex(y=>Math.abs(y)<1e-9);assert.ok(c>=0,'a bright centre');
  near(m[c+1]-m[c],600e-9*1.5/0.25e-3,1e-4,'Δy = λL/d');near(P.fringeSpacing(o),3.6e-3,1e-12,'3.6 mm');
  const one={...o,n:1,a:0.1};assert.ok(P.slitIntensity(one,Math.tan(Math.asin(600e-9/0.1e-3))*1.5)<1e-12,'first dark fringe of a single slit: a sin θ = λ');
  const gr={...o,n:6,d:0.002,a:0.0005,L:1,lambda:500},y1=Math.tan(Math.asin(500e-9/2e-6));near(P.slitIntensity(gr,y1),P.slitIntensity({...gr,n:1},y1),1e-9,'principal maximum: d sin θ = λ');
});

test('wells: E_n = n²h²/(8mL²); a finite well\'s ground state lies below the infinite one and tends to it; tunnelling',async()=>{
  const {P}=await loadAll();
  for(const [L,mass] of [[1,1],[0.5,1],[2,0.067]]){
    const w=P.wellModel({kind:'infinite',L,mass,levels:4,V0:0,E:0,psi:'psi'});
    w.levels.forEach((l,i)=>near(l.E,(i+1)**2*h*h/(8*mass*me*(L*1e-9)**2)/eV,1e-12,`E_${i+1}, L=${L}`));
    near(w.levels[1].psi(0.25*L),0+Math.sin(2*Math.PI*0.25),1e-12,'ψ₂ = sin(2πx/L)');
  }
  near(P.infiniteWellEnergy(1,1),0.376,3e-3,'an electron in 1 nm: 0.376 eV');
  for(const V0 of [0.5,3,10,50]){
    const f=P.finiteWellLevels(1,V0),E1=P.infiniteWellEnergy(1,1);
    assert.ok(f[0].E<E1,`finite ground ${f[0].E} < infinite ${E1} (V0=${V0})`);
    const z0=0.5e-9*Math.sqrt(2*me*V0*eV)/hbar;assert.equal(f.length,Math.ceil(2*z0/Math.PI),'bound states: ⌈2z₀/π⌉');
    for(const l of f){const z=l.z,rhs=Math.sqrt(z0*z0-z*z);near(l.parity==='even'?z*Math.tan(z):-z/Math.tan(z),rhs,1e-8,'transcendental equation');}
    assert.ok(f.every((l,i)=>i===0||l.E>f[i-1].E));
  }
  near(P.finiteWellLevels(1,1e4)[0].E,P.infiniteWellEnergy(1,1),0.02,'a deep well is nearly infinite');
  const b=P.wellModel({kind:'barrier',L:0.4,V0:4,E:2.5,mass:1,levels:1,psi:'psi'}),kap=Math.sqrt(2*me*1.5*eV)/hbar;
  near(b.T,1/(1+16*Math.sinh(kap*0.4e-9)**2/(4*2.5*1.5)),1e-12,'T of a rectangular barrier');
  const ho=P.wellModel({kind:'harmonic',V0:0.2,mass:1,levels:3,L:1,E:0,psi:'psi'});near(ho.levels[2].E,0.5,1e-12,'(n + ½)ħω');
});

test('hydrogen lines, a moving clock\'s ticks γτ apart',async()=>{
  const {P}=await loadAll();
  const m=P.levelModel({kind:'hydrogen',n:6,values:'',trans:'3-2,4-2,2-1'});
  near(m.trans[0].lambda,656.3,2e-3,'Hα');near(m.trans[1].lambda,486.1,2e-3,'Hβ');near(m.trans[2].lambda,121.5,2e-3,'Lyman α');
  const ticks=P.clockTicks({x0:0,beta:0.6,tau:1},10);near(ticks[0].ct,1.25,1e-12,'γ = 1.25');near(ticks[0].x,0.75,1e-12,'x = βγτ');
  near(ticks[1].ct**2-ticks[1].x**2,4,1e-12,'(ct)² − x² = τ²');
});

test('scene version 2: v1 is migrated, the new types are checked strictly and leniently, the formula language is closed',async()=>{
  const {S}=await loadAll();
  const v1=S.validateScene({format:'haslalab-scene',version:1,objects:[{id:'n1',type:'line',x1:0,y1:0,x2:1,y2:1,dash:false},{id:'n2',type:'line',x1:0,y1:0,x2:1,y2:1}]});
  assert.ok(v1.ok);assert.equal(v1.scene.version,2);assert.equal(v1.scene.style,'textbook');assert.deepEqual(v1.scene.objects.map(o=>o.pattern),['solid','dashed']);
  assert.ok(v1.notes.some(n=>n.code==='migrated'));
  assert.ok(!S.validateScene({version:3,objects:[]}).ok);
  const bad=(objects,code,extra={})=>{const r=S.validateScene({objects,...extra});assert.ok(!r.ok,code);assert.ok(r.errors.some(e=>e.code===code),code+' '+JSON.stringify(r.errors));};
  bad([{id:'e',type:'element',kind:'flux-capacitor'}],'bad_enum');
  bad([{id:'e',type:'element',x1:1,y1:1,x2:1,y2:1}],'zero_length');
  bad([{id:'L',type:'lens',f:0}],'out_of_range');
  bad([{id:'c',type:'curve',graph:'g'}],'bad_ref');
  bad([{id:'g',type:'graph'},{id:'c',type:'curve',graph:'g',expr:'alert(1)'}],'bad_expr');
  bad([{id:'w',type:'worldline'}],'missing_ref');
  bad([],'bad_enum',{style:'comic'});
  const len=S.validateScene({style:'olympiad',objects:[{id:'g',type:'graph'},{id:'c',type:'curve',graph:'g',expr:'x.constructor'},{id:'L',type:'lens',f:0},{id:'w',type:'worldline',diagram:'nope'},{id:'q',type:'charge',q:1e9}]},{lenient:true});
  assert.ok(len.ok);assert.equal(len.scene.style,'olympiad');assert.deepEqual(len.scene.objects.map(o=>o.id),['g','c','L','q']);
  assert.equal(len.scene.objects[1].expr,'sin(x)');assert.equal(len.scene.objects[2].f,0.01);assert.equal(len.scene.objects[3].q,1e4);
  for(const e of ['x.constructor','this','process','alert(1)','x;1','[1]','`x`','x=1','(x','2^^x'])assert.equal(S.compileExpr(e),null,e);
  for(const [e,x,v] of [['2x^2 - 3x + 1',2,3],['sin(pi/2)',0,1],['-x^2',3,-9],['e^x',1,Math.E],['3(x+1)',1,6],['ln(e)',0,1],['sqrt 16',0,4]])near(S.compileExpr(e)(x),v,1e-12,e);
  const props=S.visionProperties();for(const k of ['kind','f','q','expr','pattern'])assert.ok(props[k],k);assert.ok(props.kind.enum.includes('resistor')&&props.kind.enum.includes('isotherm'));
});

test('every template, in every style, draws without NaN; labels are typeset (accents as paths, no fonts or scripts in the file)',async()=>{
  const {S,P,R}=await loadAll();
  for(const k of S.TEMPLATE_KEYS)for(const style of S.STYLE_KEYS){
    const sc=S.validateScene(S.template(k)).scene,svg=R.renderSVG(sc,{style,circuit:P.solveCircuit(sc),labelScale:1.8,strokeScale:1.4});
    assert.ok(!/NaN|undefined|Infinity/.test(svg),k+' '+style);assert.ok(!/<script|href=|@font-face|url\(http/i.test(svg),k);
  }
  const b=R.texLayout('\\vec{F} = m\\ddot{\\vec{r}}',20);assert.ok(b.paths.length>=3,'two arrows and the dots');assert.ok(b.items.some(i=>i.t==='F'&&i.it));
  const fr=R.texLayout('\\frac{1}{2}mv^2',20),one=fr.items.find(i=>i.t==='1'),two=fr.items.find(i=>i.t==='2');assert.ok(one.y<two.y&&Math.abs(one.x-two.x)<1,'a stacked fraction');assert.ok(one.size>=13,'not tiny at 20 px');
  assert.deepEqual(R.texRuns('\\hbar\\omega').map(r=>r.t),['ħ','ω']);assert.equal(R.texRuns('\\ket{\\psi}').map(r=>r.t).join(''),'|ψ⟩');
  assert.equal(R.texRuns('\\mathcal{E}')[0].t,'ℰ');assert.equal(R.texRuns('30^\\circ').map(r=>r.t).join(''),'30°');assert.equal(R.texRuns('\\mathrm{k\\Omega}')[0].it,false);
  for(const c of ['\\varepsilon','\\vartheta','\\varphi','\\varrho','\\varsigma','\\nabla','\\partial','\\oint','\\odot','\\otimes','\\rightleftharpoons','\\AA','\\propto','\\equiv','\\langle'])assert.ok(!/[a-z]{3}/.test(R.texRuns(c)[0].t),c);
  const bold=R.texLayout('\\vec{F}',16);assert.ok(bold.paths.length===1);
  const sc=S.validateScene({style:'olympiad',objects:[{id:'l',type:'label',x:0,y:0,text:'\\vec{F}'}]}).scene;assert.match(R.renderSVG(sc,{view:{x:-1,y:-1,w:2,h:2}}),/font-weight="bold"/,'olympiad: bold vectors');
  /* the paper scale makes labels larger */
  const a=S.validateScene(S.template('atwood')).scene,size=svg=>Math.max(...[...svg.matchAll(/font-size="([\d.]+)"/g)].map(m=>+m[1]));
  assert.ok(size(R.renderSVG(a,{labelScale:2}))>1.8*size(R.renderSVG(a,{}))*0.9);
});

/* ── the added elements, the measured styles and the editor's history ── */
test('turned objects: extents hold the turned corners; a plane mirror at 45° turns a ray through 90°; a turned lens still focuses',async()=>{
  const {S,P}=await load();
  const box=S.objectExtent({...S.defaults('region'),x:0,y:0,w:2,h:1,rot:90});near(box.w,1,1e-9,'w after 90°');near(box.h,2,1e-9,'h after 90°');near(box.x+box.w/2,1,1e-9,'same centre');
  const m=S.objectExtent({...S.defaults('magnet'),x:0,y:0,w:2,h:0.4,rot:45}),d=(2+0.4)/Math.SQRT2;near(m.w,d,1e-9,'45° box');
  const sc=scene(S,[{id:'M',type:'mirror',x:2,y:0,h:2,f:0,rot:-45}]),tr=P.traceRay(sc,{x:0,y:0},{x:1,y:0},{len:5});
  near(tr.pts[1].x,2,1e-9,'hits the mirror');assert.ok(Math.abs(tr.d.x)<1e-9,'goes up: dx');near(tr.d.y,1,1e-9,'goes up: dy');
  /* a lens turned half a turn is the same lens; a lens turned 90° about a vertical axis and hit along y focuses at f */
  for(const rot of [0,180]){const s2=scene(S,[{id:'L',type:'lens',x:1,y:0,h:2,f:0.5,rot}]),t=P.traceRay(s2,{x:0,y:0.2},{x:1,y:0},{len:3});assert.ok(Math.abs(t.pts[1].y+t.d.y/t.d.x*0.5)<1e-9,'parallel ray through the focus, rot '+rot);}
  const s3=scene(S,[{id:'L',type:'lens',x:0,y:1,h:2,f:0.5,rot:90}]),t3=P.traceRay(s3,{x:0.2,y:0},{x:0,y:1},{len:3});assert.ok(Math.abs(t3.pts[1].x+t3.d.x/t3.d.y*0.5)<1e-9,'turned lens focuses at f');
  /* a half-silvered mirror passes the ray and forks a reflected branch; a screen stops a ray */
  const s4=scene(S,[{id:'B',type:'mirror',x:1,y:0,h:1,f:0,rot:-45,half:true},{id:'Sc',type:'screen',x:3,y:0,h:1}]),t4=P.traceRay(s4,{x:0,y:0},{x:1,y:0},{len:10});
  near(t4.end.x,3,1e-9,'stopped by the screen');assert.equal(t4.forks.length,1);near(t4.forks[0].d.y,1,1e-9,'reflected up');
});

test('stacked blocks with friction: they move together while F ≤ μ₂ g (m₁ + m₂) (frictionless floor), else the top slips with a = μ₂ g',async()=>{
  const {S,P}=await load();
  const make=(F,mu2,mu1=0)=>scene(S,[{id:'f',type:'floor',x:0,y:0,w:40,mu:mu1},{id:'M',type:'block',on:'f',at:5,w:1.2,h:0.3,mass:3,mu:mu2},{id:'m',type:'block',on:'M',at:0.6,w:0.4,h:0.3,mass:1},{id:'F',type:'force',on:'M',F,angle:0}]);
  const mu2=0.4,lim=mu2*g*4;
  const t=P.buildSim(make(0.8*lim,mu2));assert.equal(t.systems[0].kind,'stack');
  near(t.accelerations().get('M').x,0.8*lim/4,1e-9,'together: a = F / (m₁ + m₂)');near(t.accelerations().get('m').x,0.8*lim/4,1e-9,'top too');
  const fr=t.systems[0].friction();near(fr.between,1*0.8*lim/4,1e-9,'static friction on the top = m a');assert.equal(fr.slipping,false);
  const F=2*lim,sl=P.buildSim(make(F,mu2));
  near(sl.accelerations().get('m').x,mu2*g,1e-9,'top: μ₂ g');near(sl.accelerations().get('M').x,(F-mu2*1*g)/3,1e-9,'bottom: (F − μ₂ m g)/M');
  sl.run(0.3);near(sl.velocities().get('M').x-sl.velocities().get('m').x,((F-mu2*g)/3-mu2*g)*0.3,1e-6,'relative speed');
  const e=sl.energy();near(e.K+e.heat,e.work,1e-6,'work = kinetic energy + heat');
  /* a floor with friction under a stack at rest holds a small pull */
  const held=P.buildSim(make(5,0.4,0.5));held.run(1);assert.equal(held.poses().get('M').at,5);
  /* the top slides off the block's edge */
  const off=P.buildSim(make(2*lim,mu2));off.run(5);assert.equal(off.events[0].code,'end_of_surface');assert.equal(off.events[0].id,'m');
});

test('rolling without slipping: a = g sin θ / (1 + I/mr²) for a disk, a ring and a sphere; with too little friction it slides',async()=>{
  const {S,P}=await load();
  for(const [kind,k] of [['disk',0.5],['ring',1],['sphere',0.4]]){
    const sim=P.buildSim(scene(S,[{id:'i',type:'incline',x:0,y:0,angle:30,length:6,mu:0.5},{id:'w',type:'wheel',on:'i',at:5,r:0.2,mass:2,kind}]));
    const a=sim.accelerations().get('w');near(Math.hypot(a.x,a.y),P.rollingAccel(g,30,k),1e-9,kind);near(P.rollingAccel(g,30,k),g*0.5/(1+k),1e-12,'formula');
    const E0=sim.energy().E;sim.run(0.6);near(sim.energy().E,E0,1e-6,kind+': rolling keeps the energy (K includes the spin)');
  }
  const slip=P.buildSim(scene(S,[{id:'i',type:'incline',x:0,y:0,angle:60,length:6,mu:0.1},{id:'w',type:'wheel',on:'i',at:5,r:0.2,mass:2,kind:'ring'}]));
  const r=60*Math.PI/180,a=slip.accelerations().get('w');near(Math.hypot(a.x,a.y),g*(Math.sin(r)-0.1*Math.cos(r)),1e-9,'slides: g (sin θ − μ cos θ)');
});

test('buoyancy ρ g V, a floating fraction ρ_b/ρ_f; motional EMF ε = BLv; meter bridge balance R/S = l/(100 − l)',async()=>{
  const {S,P}=await load();
  near(P.buoyancy(1000,0.002,9.8),19.6,1e-12,'ρ g V');near(P.floatFraction(600,1000),0.6,1e-12,'fraction');
  const sc=S.validateScene(S.template('buoyancy')).scene,info=P.containerInfo(sc,sc.objects.find(o=>o.id==='ct'));
  const A=info.bodies.find(b=>b.id==='A');near(A.Vsub,0.5*0.24*0.5,1e-9,'submerged volume of A');near(A.B,1000*9.8*0.06,1e-9,'buoyancy on A');near(A.floats,0.6,1e-9,'A floats with 0.6 under');
  const B=info.bodies.find(b=>b.id==='b1');near(B.B,1000*9.8*4/3*Math.PI*0.15**3,1e-9,'the sunken ball');
  const rails={...S.defaults('rails'),h:0.5,v:4,B:0.2,R:2},m=P.motionalEMF(rails);near(m.emf,0.4,1e-12,'ε = BLv');near(m.I,0.2,1e-12,'I = ε/R');near(m.F,0.2*0.2*0.5,1e-12,'F = BIL');
  near(P.meterBridgeBalance(4,6),40,1e-12,'l = 100 R/(R + S)');
  const mb=S.validateScene(S.template('meter_bridge')).scene,c=P.solveCircuit(mb);assert.ok(c.ok);
  assert.ok(Math.abs(c.el.get('G1').I)<1e-9,'balanced: no galvanometer current at l = 40 cm');
  mb.objects.find(o=>o.id==='BR').at=0.6;const c2=P.solveCircuit(mb);assert.ok(Math.abs(c2.el.get('G1').I)>1e-4,'off balance: a current');
  const rh=S.validateScene({objects:[{id:'E',type:'element',kind:'cell',x1:0,y1:0,x2:0,y2:1,value:3},{id:'R',type:'element',kind:'rheostat',x1:0,y1:1,x2:1,y2:1,value:30},{id:'C',type:'element',kind:'dielectric',x1:1,y1:1,x2:1,y2:0,value:10},{id:'W',type:'element',kind:'wire',x1:1,y1:0,x2:0,y2:0}]}).scene;
  const c3=P.solveCircuit(rh);near(c3.transients[0].tau,30*10e-6,1e-9,'τ = RC with a rheostat and a dielectric capacitor');
});

test('history: one step a change, at most the limit, redo cleared by a new change; scene v2 with the added fields',async()=>{
  const {S}=await load();
  const h=S.createHistory(250);assert.equal(h.canUndo,false);assert.equal(h.limit>=200,true);
  for(let i=0;i<300;i++)h.record(JSON.stringify({n:i}));assert.equal(h.size,250,'kept 250 steps');
  let cur=JSON.stringify({n:300});const back=h.undo(cur);assert.equal(JSON.parse(back).n,299);assert.equal(h.canRedo,true);
  const fwd=h.redo(back);assert.equal(JSON.parse(fwd).n,300);h.undo(fwd);h.record(JSON.stringify({n:'x'}));assert.equal(h.canRedo,false,'a new change clears redo');
  const h2=S.createHistory();h2.record('{"a":1}');h2.record('{"a":1}');assert.equal(h2.size,1,'the same state twice is one step');
  /* the added fields and types validate; stacks must end on a surface */
  const ok=S.validateScene({values:true,printW:60,objects:[{id:'f',type:'floor',x:0,y:0,w:3},{id:'A',type:'block',on:'f',at:1,w:0.5,h:0.3,rot:0,look:'cart',lw:1.5,ls:1.2,lock:true},{id:'B',type:'block',on:'A',at:0.2,w:0.2,h:0.2},{id:'p',type:'panel',x:0,y:0,w:1,h:1,caption:'(가)'}]});
  assert.ok(ok.ok,JSON.stringify(ok.errors));assert.equal(ok.scene.values,true);assert.equal(ok.scene.printW,60);near(ok.scene.objects.find(o=>o.id==='B').y,0.3+0.1,1e-9,'B sits on A');
  const loop=S.validateScene({objects:[{id:'A',type:'block',on:'B',x:0,y:0},{id:'B',type:'block',on:'A',x:0,y:0}]});assert.equal(loop.ok,false);assert.ok(loop.errors.some(e=>e.code==='bad_stack'));
  assert.equal(S.validateScene({objects:[{id:'A',type:'block',on:'B',x:0,y:0},{id:'B',type:'block',on:'A',x:0,y:0}]},{lenient:true}).ok,true);
  assert.equal(S.validateScene({version:1,objects:[{id:'l',type:'line',x1:0,y1:0,x2:1,y2:1,dash:false}]}).scene.objects[0].pattern,'solid','v1 still migrates');
  assert.ok(S.TEMPLATE_KEYS.length>=61,'at least 25 new templates');
  for(const k of S.TEMPLATE_KEYS)assert.ok(S.validateScene(S.template(k)).ok,k);
  assert.equal(S.template('ks_collision').style,'suneung');
});

test('figure styles come from the measured table: each preset has its row, 수능 exists with Hangul and caption faces, the print scale gives the measured sizes',async()=>{
  const {S,R}=await load();
  assert.deepEqual(Object.keys(R.STYLE_TABLE).sort(),[...S.STYLE_KEYS].sort());
  for(const k of ['suneung','olympiad','jee']){const t=R.STYLE_TABLE[k];assert.ok(t.n>0&&t.source&&t.measured.length>=5&&t.basis==='measured',k+' is measured');}
  for(const k of ['textbook','classic','modern','print']){const t=R.STYLE_TABLE[k];assert.equal(t.source,'assumed');assert.equal(t.basis,'designed');assert.ok(t.designed.length>=1,k+' says what was designed');}
  assert.ok(!S.STYLE_KEYS.includes('university')&&!R.STYLES.university,'대학 과제 merged into 교과서');
  const t=R.STYLE_TABLE.suneung,st=R.STYLES.suneung;near(st.lw,t.main*15/t.labelPt,1e-12,'lines keep the ratio to the label');assert.ok(st.hangul&&st.caption&&st.uprightNames);
  const p=R.printScale('suneung');near(p.widthPt,t.widthPt,1e-12,'default print width');near(15*p.labelScale*p.widthPt/800,t.labelPt,1e-9,'labels come out at the measured pt');
  const sc=S.validateScene(S.template('ks_collision')).scene,svg=R.renderSVG(sc,{});
  assert.match(svg,/\(가\)/);assert.match(svg,/font-family="'Noto Serif KR'/,'captions in myeongjo');assert.match(svg,/>A<\/tspan>/);assert.ok(!/font-style="italic">A</.test(svg),'object names upright in 수능');
  /* a floor in the 수능 style is a bare line: no hatching path next to it */
  const f=S.validateScene({style:'suneung',objects:[{id:'f',type:'floor',x:0,y:0,w:2}]}).scene,f2={...f,style:'textbook'};
  assert.ok(R.renderSVG(f,{view:{x:-1,y:-1,w:4,h:2}}).split('<path').length<R.renderSVG(f2,{view:{x:-1,y:-1,w:4,h:2}}).split('<path').length);
});

/* ── the mechanics regression (bodies fell through planks, tracks and lines when played; mounts left their pulleys;
   a free body touching a floor fell through it; labels of tall figures came out tiny on screen) ── */
test('mechanics templates: every one runs without NaN; bodies on parts the solver does not compute are held, not dropped',async()=>{
  const {S,P}=await load();
  for(const k of S.TEMPLATE_KEYS.filter(k=>S.TEMPLATE_DOMAIN[k]==='mech')){
    const sc=S.validateScene(S.template(k)).scene,sim=P.buildSim(sc);sim.run(1);
    for(const [id,p] of sim.poses())assert.ok(Number.isFinite(p.x)&&Number.isFinite(p.y),`${k}: ${id} is finite`);
    const held=new Set(sim.unsupported.filter(u=>u.code==='held_by_figure').flatMap(u=>u.ids));
    for(const b of sc.objects.filter(S.isBody)){const by=P.heldBy(sc,b);if(by&&!b.on&&!b.vx&&!b.vy)assert.ok(held.has(b.id),`${k}: ${b.id} rests on ${by} and is held`);}
  }
  const ids=k=>{const sim=P.buildSim(S.validateScene(S.template(k)).scene);return sim.unsupported.filter(u=>u.code==='held_by_figure').flatMap(u=>u.ids).sort().join();};
  assert.equal(ids('seesaw'),'m1,m2','blocks on a seesaw plank stay');assert.equal(ids('loop_track'),'b1','a ball on a curved ramp stays');assert.equal(ids('hinged_beam'),'m1','a block hung from a drawn line stays');
  assert.equal(ids('buoyancy'),'A,b1','bodies in a liquid stay');
  /* the six classic set-ups still move as before */
  const kind=k=>P.buildSim(S.validateScene(S.template(k)).scene).systems.map(s=>s.kind).join();
  assert.deepEqual(['atwood','incline_pulley','spring_block','pendulum','projectile','conical'].map(kind),['chain','chain','surface','pendulum','free','conical']);
  /* a free block put exactly on a floor (not "on" it) lands at once instead of falling through it */
  const sc=scene(S,[{id:'f',type:'floor',x:0,y:0,w:4},{id:'b',type:'block',x:1,y:0.15,w:0.3,h:0.3}]);
  const sim=P.buildSim(sc);sim.run(1);assert.equal(sim.events[0]?.code,'landed');assert.ok(sim.poses().get('b').y>0.149,'still on the floor');
  /* a block standing on a drawn rectangle (a table drawn with the tools) stays on it */
  const tb=P.buildSim(scene(S,[{id:'t',type:'rect',x:0,y:0,w:2,h:0.5},{id:'b',type:'block',x:1,y:0.65,w:0.3,h:0.3}]));assert.deepEqual(tb.unsupported.map(u=>u.code),['held_by_figure']);
  /* template details: the amplitude mark sits under the floor; the string to the table block runs level to the pulley's top */
  const sb=S.validateScene(S.template('spring_block')).scene,d=sb.objects.find(o=>o.id==='d1');assert.ok(d.y1<0&&d.offset===0&&d.x2>d.x1);
  const kp=S.validateScene(S.template('ks_pulley')).scene,A=kp.objects.find(o=>o.id==='A'),p1=kp.objects.find(o=>o.id==='p1');near(p1.y+p1.r,A.y,1e-9,'the pulley top is level with A');
});
test('labels on screen: a figure shown smaller (a phone, a tall figure held to the canvas height) gets larger labels',async()=>{
  const {R}=await load();
  assert.equal(R.labelScaleFor(730,612,459),1,'a wide figure at full width: as drawn');
  assert.ok(R.labelScaleFor(730,612,1017)>1.25,'Atwood (tall) shrunk to 612 px high: labels grow');
  assert.ok(R.labelScaleFor(346,Infinity,459)>1.7,'on a 390-px phone');
  assert.ok(R.labelScaleFor(100,100,5000)<=2.6,'capped');
});

/* ── particles and other minimal defaults ── */
test('particles are plain by default (no velocity arrow); the arrow is an option; old scenes keep theirs',async()=>{
  const {S,R}=await load();
  assert.equal(S.defaults('particle').arrow,false);assert.equal(S.defaults('wave').showLambda,false);assert.equal(S.defaults('wave').showA,false);assert.equal(S.defaults('levels').showLambda,false);
  const draw=o=>R.renderSVG(scene(S,[{id:'p',type:'particle',x:0,y:0,...o}]),{width:800,view:{x:-1,y:-1,w:4,h:2}});
  for(const kind of ['neutron','proton','electron','positron','alpha']){
    const plain=draw({kind}),withArrow=draw({kind,arrow:true});
    assert.doesNotMatch(plain,/<line /,`${kind}: no arrow by default`);assert.match(withArrow,/<line /,`${kind}: the arrow when asked`);
  }
  const old=S.validateScene({objects:[{id:'p',type:'particle',x:0,y:0,kind:'proton',len:1}]}).scene.objects[0];assert.equal(old.arrow,true,'a scene written before keeps its arrow');
  assert.equal(S.validateScene({objects:[{id:'p',type:'particle',x:0,y:0,kind:'proton',len:0}]}).scene.objects[0].arrow,false);
  assert.equal(S.validateScene({objects:[{id:'w',type:'wave',x:0,y:0}]}).scene.objects[0].showLambda,true,'an old wave keeps its λ mark');
  for(const k of ['alpha_decay','compton'])assert.ok(S.validateScene(S.template(k)).scene.objects.filter(o=>o.type==='particle'&&o.kind!=='photon').every(o=>o.arrow),`${k} still shows its arrows`);
});

/* ── basic drawing shapes ── */
test('basic shapes: rect, ellipse, polyline/polygon/pen and Bézier are checked, drawn, exported; points are simplified',async()=>{
  const {S,R}=await load();
  const sc=scene(S,[{id:'r',type:'rect',x:0,y:0,w:1,h:0.6,r:0.1,fill:'hatch',color:'blue'},{id:'e',type:'ellipse',x:1.2,y:0,w:1,h:0.5,fill:'tint',color:'red',pattern:'dashed'},
    {id:'p',type:'poly',pts:[[0,1],[0.5,1.4],[1,1]],heads:'end',smooth:true},{id:'q',type:'poly',pts:[[2,1],[2.5,1.5],[3,1]],closed:true,fill:'lightgray'},
    {id:'b',type:'bezier',x1:0,y1:2,cx1:0.5,cy1:2.5,cx2:1,cy2:1.5,x2:1.5,y2:2,heads:'both',color:'green'},{id:'l',type:'line',x1:0,y1:3,x2:1,y2:3,pattern:'solid',heads:'end',color:'orange'},{id:'t',type:'label',x:2,y:3,text:'A',color:'blue'}]);
  for(const style of S.STYLE_KEYS){const svg=R.renderSVG({...sc,style},{width:800,view:{x:-0.5,y:-0.5,w:4,h:4},...R.printScale(style)});assert.doesNotMatch(svg,/NaN|undefined|Infinity/,style);
    assert.match(svg,/stroke="#1d4ed8"/);assert.match(svg,/fill="#c0262d" fill-opacity="0.16"/);assert.match(svg,/ C|C[0-9.]/);assert.match(svg,/fill="#e6e8ec"/);}
  const ed=R.renderSVG(sc,{width:800,view:{x:-0.5,y:-0.5,w:4,h:4},edit:true,selected:['p']});assert.equal((ed.match(/data-handle="p\d"/g)||[]).length,3,'a handle for each vertex');
  assert.match(R.renderSVG(sc,{width:800,view:{x:-0.5,y:-0.5,w:4,h:4},edit:true,selected:['b']}),/data-handle="c1"[\s\S]*data-handle="c2"/,'Bézier control handles');
  for(const bad of [{pts:[[0,0]]},{pts:[[0,'a'],[1,1]]},{pts:[[0,0],[1e6,0]]},{pts:'0,0 1,1'}])assert.ok(!S.validateScene({objects:[{id:'p',type:'poly',...bad}]}).ok,JSON.stringify(bad));
  assert.ok(!S.validateScene({objects:[{id:'r',type:'rect',x:0,y:0,w:1,h:1,color:'purple'}]}).ok,'only the listed colours');
  assert.ok(S.SHAPE_TYPES.every(t=>S.TYPES.includes(t)));
  const ext=S.objectExtent(sc.objects.find(o=>o.id==='b'));assert.ok(ext.y+ext.h>2.1&&ext.y<1.95,'a Bézier\'s box holds its bulges');
  const raw=Array.from({length:300},(_,i)=>({x:i/100,y:Math.sin(i/30)+(i%2?1e-4:-1e-4)})),simp=S.simplifyPath(raw,0.005,200);
  assert.ok(simp.length<60&&simp.length>=5,`simplified to ${simp.length}`);assert.deepEqual(simp[0],raw[0]);assert.deepEqual(simp.at(-1),raw.at(-1));
  const bp=S.bezierPoints({x1:0,y1:0,cx1:0,cy1:1,cx2:1,cy2:1,x2:1,y2:0},4);assert.deepEqual([bp[0],bp[4]],[{x:0,y:0},{x:1,y:0}]);near(bp[2].y,0.75,1e-12,'B(½)');
  /* a scene with shapes survives JSON and the paper's figure (SVG) */
  const again=S.validateScene(JSON.parse(JSON.stringify(sc)));assert.ok(again.ok);assert.deepEqual(again.scene,sc);
});

/* ── functions with parameters ── */
test('formulas: comparisons, conditionals and named parameters with slider ranges',async()=>{
  const {S,R}=await load();
  const V=S.compileExpr('x<0 ? 0 : (x<a ? V0 : 0)',['x','a','V0']);assert.deepEqual([-1,0.5,2].map(x=>V([x,1,5])),[0,5,0]);
  assert.equal(S.compileExpr('x>=1 && x<=2',['x'])([1.5]),1);assert.equal(S.compileExpr('x<0 || x>3')(2),0);assert.equal(S.compileExpr('step(x-1)')(2),1);
  assert.equal(S.compileExpr('2x^2')(3),18,'implicit products still work');assert.equal(S.compileExpr('kx',['x','k'])([2,3]),6,'"kx" is k·x');
  assert.equal(S.compileExpr('a+1'),null,'an unknown name is refused');assert.equal(S.compileExpr('x ? 1'),null);assert.equal(S.compileExpr('alert(1)'),null);
  assert.deepEqual(S.parseParams('a=1 [0.2, 3], V0=5'),[{name:'a',value:1,min:0.2,max:3},{name:'V0',value:5,min:0,max:10}]);
  for(const bad of ['x=1','a=1, a=2','a=','sin=2','a=1 [3, 1]','a=1;; b'])assert.equal(S.parseParams(bad),null,bad);
  assert.deepEqual(S.parseParams(S.paramsText(S.parseParams('w=3 [0.5, 8], A=-1'))),S.parseParams('w=3 [0.5, 8], A=-1'),'the text round-trips');
  const f=S.boundExpr('A exp(-x/tau) cos(w x)','A=2, tau=3, w=3');near(f(1),2*Math.exp(-1/3)*Math.cos(3),1e-12,'bound');
  const mk=params=>({objects:[{id:'G',type:'graph',x:0,y:0,w:3,h:2,auto:false,xmin:0,xmax:6,ymin:-2,ymax:2},{id:'c',type:'curve',graph:'G',kind:'func',params,expr:'A sin(k x)',x1:0,x2:6}]});
  assert.ok(S.validateScene(mk('A=1, k=1')).ok);assert.ok(!S.validateScene(mk('A=1')).ok,'the formula names a parameter that is not there');
  const s1=R.renderSVG(S.validateScene(mk('A=1, k=1')).scene,{width:800,view:{x:-0.5,y:-0.5,w:4,h:3}}),s2=R.renderSVG(S.validateScene(mk('A=1.5, k=2')).scene,{width:800,view:{x:-0.5,y:-0.5,w:4,h:3}});
  assert.notEqual(s1,s2,'a slider value changes the plot');assert.doesNotMatch(s2,/NaN/);
  assert.ok(S.validateScene(S.template('param_function')).ok);
});

/* ── the Schrödinger equation for a typed potential ── */
test('typed potentials: finite differences give the infinite well, (n + ½)ħω and a finite well\'s count; transfer matrices give a barrier\'s T',async()=>{
  const {S,P,R}=await load();
  const C=hbar*hbar/(2*me)/eV*1e18;near(P.HBAR2_2ME,C,1e-12,'ħ²/2m in eV nm²');
  /* infinite well of width L: E_n = n²π²ħ²/(2mL²) */
  for(const [L,mass] of [[1,1],[0.5,0.067]]){const st=P.boundStates(()=>0,0,L,{mass,N:1500,count:4});st.forEach(s=>near(s.E,P.infiniteWellEnergy(s.n,L,mass),2e-5,`E_${s.n}, L=${L}`));
    const h2=L/1501;near(st[0].psi.reduce((a,v)=>a+v*v,0)*h2,1,1e-9,'normalised');}
  /* harmonic oscillator ½kx²: E_n = (n + ½) ħω, ħω = √(2Ck/m) */
  for(const k of [2,8]){const hw=Math.sqrt(2*C*k),st=P.boundStates(S.boundExpr('0.5 k x^2','k='+k),-4,4,{N:2000,count:5});st.forEach(s=>near(s.E,(s.n-0.5)*hw,2e-4,`HO level ${s.n}, k=${k}`));}
  /* finite well of depth V0, width 1 nm: ⌈2z₀/π⌉ bound states, energies close to the transcendental roots */
  for(const V0 of [0.5,3,10]){const V=S.boundExpr('abs(x)<a/2 ? 0 : V0',`a=1, V0=${V0}`),st=P.boundStates(V,-3,3,{N:2000,count:12}).filter(s=>s.E<V0);
    const z0=0.5e-9*Math.sqrt(2*me*V0*eV)/hbar;assert.equal(st.length,Math.ceil(2*z0/Math.PI),`bound states for V0=${V0}`);
    P.finiteWellLevels(1,V0).forEach((l,i)=>near(st[i].E,l.E,3e-3,`finite level ${i+1}, V0=${V0}`));}
  /* rectangular barrier: T = 1/(1 + V0² sinh²(κa)/(4E(V0−E))) below the top, with sin above it; T + R = 1 */
  const B=S.boundExpr('abs(x) < a/2 ? V0 : 0','a=0.4, V0=4');
  for(const E of [0.5,2.5,3.9,4.5,8]){const q=Math.sqrt(Math.abs(4-E)/C),T=E<4?1/(1+16*Math.sinh(q*0.4)**2/(4*E*(4-E))):1/(1+16*Math.sin(q*0.4)**2/(4*E*(E-4)));
    const r=P.scatterState(B,-1,1,E);near(r.T,T,1e-9,`T at E=${E}`);near(r.T+r.R,1,1e-9,'T + R = 1');}
  /* a step up: T = 4 k₁k₂/(k₁+k₂)² above it, 0 below; the wave decays inside */
  const st2=S.boundExpr('x<0 ? 0 : V0','V0=3');{const r=P.scatterState(st2,-1,1,5),k1=Math.sqrt(5/C),k2=Math.sqrt(2/C);near(r.T,4*k1*k2/(k1+k2)**2,1e-9,'step T');}
  {const r=P.scatterState(st2,-1,1,2);assert.equal(r.T,0);near(r.R,1,1e-9,'total reflection');const end=r.psi.at(-1);assert.ok(Math.hypot(end.re,end.im)<0.05,'evanescent inside');}
  /* the object: a template draws its levels and its scattering state without NaN; T(E) rises to 1 */
  for(const k of ['custom_well','custom_barrier']){const sc=S.validateScene(S.template(k)).scene,o=sc.objects[0],m=P.qpotModel(o);assert.ok(m.ok);
    assert.doesNotMatch(R.renderSVG(sc,{width:800,view:sc.view}),/NaN|undefined/);
    if(o.levels)assert.equal(m.states.filter(s=>s.bound).length,o.levels,'its levels are bound');
    if(o.tplot){assert.ok(m.curve.at(-1).T>0.5&&m.curve[5].T<0.01,"T(E) grows from ~0 past the top");near(m.scatter.T,P.scatterState(m.V,m.x0,m.x1,o.E).T,1e-12,'T at its E');}}
  assert.ok(!S.validateScene({objects:[{id:'Q',type:'qpot',x:0,y:0,V:'V0 x',params:'a=1'}]}).ok,'V names a parameter that is not there');
  const info=P.computedInfo(S.validateScene(S.template('custom_barrier')).scene);assert.equal(info[0].type,'qpot');assert.ok(info[0].T>0&&info[0].T<1);
});

/* ── the workshop round of 2026-11: per-object style, styles merged and added, the TeX spacing, the conical pendulum,
   the construction, function features, and drawn shapes given physics (the rigid-body world) ── */
test('styles: 대학 과제 reads as 교과서 (figure and object); 클래식 hatches with open heads, 모던 is sans with round caps and an accent; one object drawn in another style',async()=>{
  const {S,R}=await load();
  const r=S.validateScene({style:'university',objects:[{id:'a',type:'rect',x:0,y:0,w:1,h:1,style:'university'}]});
  assert.ok(r.ok);assert.equal(r.scene.style,'textbook');assert.equal(r.scene.objects[0].style,'textbook');assert.ok(r.notes.some(n=>n.code==='style_merged'));
  assert.equal(R.STYLES.classic.gray,null);assert.equal(R.STYLES.classic.head,'open');assert.ok(R.STYLES.modern.sans&&R.STYLES.modern.round&&R.STYLES.modern.vecInk);
  const sc=S.validateScene({objects:[{id:'v1',type:'vector',x1:0,y1:0,x2:1,y2:0},{id:'v2',type:'vector',x1:0,y1:1,x2:1,y2:1,style:'modern',label:'\\vec{v}'}]}).scene;
  const svg=R.renderSVG(sc,{view:{x:-0.5,y:-0.5,w:2,h:2}});
  assert.match(svg,/stroke="#2563eb"/,'the modern object takes the accent');assert.match(svg,/stroke="#000"/,'the other keeps the figure style');
  assert.match(svg,/font-family="'Inter'/,'its label face too');
  for(const k of S.STYLE_KEYS)assert.equal(S.validateScene({objects:[{id:'a',type:'label',x:0,y:0,text:'A',style:k}]}).scene.objects[0].style,k);
});

test('TeX: binary operators and relations get TeX spacing, so ∇×B, ∇·E, a×b do not overlap; glyph boxes never overlap; metrics hold the widest fallback faces',async()=>{
  const {R}=await load();
  const F=['\\nabla\\times\\vec{B}','\\nabla\\times B','\\nabla\\cdot\\vec{E}','\\nabla^2\\phi','\\partial_t \\rho','a\\times b','a\\cdot b','\\int f\\,dx','\\vec{F} = m\\vec{a}','x = -b \\pm c','\\hbar\\omega','\\sum_{i} m_i v_i','\\oint \\vec{B}\\cdot d\\vec{l} = \\mu_0 I','\\hat{x}\\times\\hat{y} = \\hat{z}','\\dot{x}\\ddot{y}','∇×B','E \\approx mc^2','\\ce{SO4^2-}','\\ce{2H2 + O2 -> 2H2O}','\\langle x \\rangle'];
  for(const s of F){
    const b=R.glyphBoxes(s,100);assert.ok(b.length>0,s);
    /* on one baseline (scripts aside) each glyph starts after the previous one ends */
    const base=b.filter(g=>Math.abs(g.y)<1).sort((p,q)=>p.x-q.x);
    for(let i=1;i<base.length;i++)assert.ok(base[i].x>=base[i-1].x+base[i-1].w-0.01,`${s}: “${base[i-1].t}” and “${base[i].t}” overlap`);
  }
  /* a script sits right after its base, Greek and ∇ included (ε₀ not “ε 0”): within 0.15 em of the base's right edge */
  for(const s of ['\\varepsilon_0','\\nabla^2','\\rho_0','\\omega_0','\\theta_i','\\mu_0','\\psi^2','\\Omega_k']){
    const [b0,sc]=R.glyphBoxes('$'+s+'$',100),gap=sc.x-(b0.x+b0.w);assert.ok(gap<=15&&gap>=-8,`${s}: the script is ${gap} from its base`);
  }
  /* the operator gets room on both sides (TeX's medium space, 4/18 em) */
  const c=R.glyphBoxes('\\nabla\\times B',100),[n,x,B]=c;assert.ok(x.x-(n.x+n.w)>=20&&B.x-(x.x+x.w)>=20,'medium space around ×');
  const rel=R.glyphBoxes('a = b',100);assert.ok(rel.length===3||rel.length===2);
  const unary=R.glyphBoxes('-x',100);assert.ok(unary[1].x-(unary[0].x+unary[0].w)<5,'a sign at the start is unary (no space)');
  /* advances at least those of Times New Roman / STIX Two (em ×1000) for the symbols that overlapped */
  const W={'∇':722,'×':564,'·':250,'∂':494,'∑':713,'∫':444,'ħ':500,'→':1000,'≈':548};
  for(const [ch,w] of Object.entries(W))assert.ok(R.glyphBoxes('$'+ch+'$',1000)[0].w>=w,ch+' advance');
  /* \ce: subscripts, charges, arrows; matrices and cases typeset */
  assert.equal(R.ceTex('SO4^2-'),'SO_{4}^{2−}');assert.equal(R.ceTex('NH4+'),'NH_{4}^{+}');assert.match(R.ceTex('2H2 + O2 -> 2H2O'),/^2H_\{2\} \+ O_\{2\}\\rightarrow 2H_\{2\}O$/);
  const m=R.texSVG('\\pmatrix{a & b \\\\ c & d}',20);assert.doesNotMatch(m,/NaN/);assert.equal((m.match(/<tspan/g)||[]).length,4);
  assert.match(R.texSVG('Q_{⬚}',20),/class="ph"/,'a placeholder is a box');
});

test('conical pendulum: drawn in an oblique view (the bob goes round an ellipse), period 2π√(L cos θ / g), tension mg/cos θ, the centripetal force in the free-body diagram',async()=>{
  const {S,P,R}=await load();
  const sc=S.validateScene(S.template('conical')).scene,sim=P.buildSim(sc),s=sim.systems[0],L=1.6,th=30*Math.PI/180;
  assert.equal(s.kind,'conical');near(s.period,2*Math.PI*Math.sqrt(L*Math.cos(th)/g),1e-4,'period');
  /* measured from the motion: the bob's x crosses the axis upwards once a period */
  const ups=[];let prev=sim.poses().get('b1').x-1.5,t=0;while(t<8){t+=1e-3;sim.advanceTo(t);const x=sim.poses().get('b1').x-1.5;if(prev<0&&x>=0)ups.push(t);prev=x;}
  near((ups.at(-1)-ups[0])/(ups.length-1),2*Math.PI*Math.sqrt(L*Math.cos(th)/g),2e-3,'measured period');
  /* not a plane pendulum: the drawn y changes as the bob goes round (front lower, back higher), the true height does not */
  const ys=[];const s2=P.buildSim(sc);for(let k=0;k<20;k++){s2.run(s.period/20);ys.push(s2.poses().get('b1').y);}
  assert.ok(Math.max(...ys)-Math.min(...ys)>0.2*L*Math.sin(th),'the drawn orbit is an ellipse');
  const f=sim.forces().get('b1'),kinds=f.map(x=>x.kind);assert.deepEqual(kinds,['gravity','tension','centripetal']);
  near(sim.tensions().s1,0.5*g/Math.cos(th),1e-4,'tension');
  const svg=R.renderSVG(sim.applyTo(sc),{poses:sim.poses(),forces:sim.forces(),conical:[{id:'s1',centre:s.centre,radius:s.radius}]});
  /* the force labels stand clear of the bob and of each other */
  const bob=sim.poses().get('b1'),V=sc.view,Sc=800/V.w,bx=(bob.x-V.x)*Sc,by=(V.y+V.h-bob.y)*Sc,rb=0.08*Sc;
  const labs=[...svg.matchAll(/data-kind="(\w+)">.*?<text[^>]*>(.*?)<\/text>/g)].map(m=>{const xs=[...m[2].matchAll(/x="([\d.]+)" y="([\d.]+)"/g)].map(q=>[+q[1],+q[2]]);return {k:m[1],x:xs[0][0],y:xs[0][1]};});
  assert.equal(labs.length,3);for(const l of labs)assert.ok(Math.hypot(l.x-bx,l.y-by)>rb,`${l.k} label off the bob`);
  for(let i=0;i<3;i++)for(let j=i+1;j<3;j++)assert.ok(Math.hypot(labs[i].x-labs[j].x,labs[i].y-labs[j].y)>12,'labels apart');
  assert.match(svg,/A[\d.]+,[\d.]+ 0 0 1/,'the orbit drawn as arcs of an ellipse');assert.match(svg,/data-kind="centripetal"/);assert.doesNotMatch(svg,/NaN/);
});

test('construction: points, midpoints, perpendiculars, intersections and circles follow when a free point moves; cycles are refused',async()=>{
  const {S,R}=await load();
  const sc=S.validateScene(S.template('geo_triangle')).scene,G=S.computeGeometry(sc);
  const O=G.get('O'),dist=id=>Math.hypot(G.get(id).x-O.x,G.get(id).y-O.y);
  near(dist('A'),dist('B'),1e-9,'circumcentre: OA = OB');near(dist('B'),dist('C'),1e-9,'OB = OC');near(G.get('cc').r,dist('A'),1e-9,'the circle goes through A');
  /* drag B: everything that depends on it moves, the circumcentre stays equidistant */
  sc.objects.find(o=>o.id==='B').x=4.2;const G2=S.computeGeometry(sc),O2=G2.get('O');
  assert.ok(Math.hypot(O2.x-O.x,O2.y-O.y)>0.05,'O moved');near(Math.hypot(G2.get('A').x-O2.x,G2.get('A').y-O2.y),Math.hypot(G2.get('C').x-O2.x,G2.get('C').y-O2.y),1e-9,'still OA = OC');
  const ang=G.get('ang');near(ang.deg,Math.acos(((3.2*1.2)+(0.2*2.4))/(Math.hypot(3.2,0.2)*Math.hypot(1.2,2.4)))*180/Math.PI,1e-9,'angle BAC');
  /* line–circle and circle–circle intersections, a point on a circle */
  const two=S.computeGeometry(S.validateScene({objects:[{id:'C1',type:'gpoint',x:0,y:0},{id:'C2',type:'gpoint',x:1,y:0},{id:'k1',type:'gcircle',c:'C1',r:1},{id:'k2',type:'gcircle',c:'C2',r:1},{id:'X',type:'gpoint',kind:'inter',a:'k1',b:'k2',n:1},{id:'Q',type:'gpoint',kind:'on',a:'k1',x:3,y:0}]}).scene);
  near(two.get('X').y,Math.sqrt(3)/2,1e-12,'circle ∩ circle (the second, by x then y)');near(two.get('Q').x,1,1e-12,'a point on a circle is the nearest one');
  const bad=S.validateScene({objects:[{id:'P',type:'gpoint',kind:'on',a:'L'},{id:'Q',type:'gpoint',x:1,y:1},{id:'L',type:'gline',a:'P',b:'Q'}]});
  assert.ok(!bad.ok&&bad.errors.some(e=>e.code==='geo_cycle'));assert.equal(S.validateScene(bad.scene.objects.length?bad.scene:{objects:[]},{lenient:true}).ok,true);
  assert.ok(!S.validateScene({objects:[{id:'L',type:'gline',a:'',b:''}]}).ok,'a line needs its points');
  const svg=R.renderSVG(sc,{edit:true});assert.doesNotMatch(svg,/NaN|undefined/);assert.match(svg,/class="free"/,'free points marked for dragging');
});

test('functions: roots and extrema found numerically, the tangent, the area by Simpson, parametric, polar and inequality curves drawn',async()=>{
  const {S,P,R}=await load();
  const ft=P.funcFeatures(x=>0.5*x**3-2*x,-3,3);
  assert.deepEqual(ft.roots.map(x=>+x.toFixed(9)),[-2,0,2]);near(ft.extrema[0].x,-Math.sqrt(4/3),1e-6,'max at −√(4/3)');assert.equal(ft.extrema[0].kind,'max');
  near(P.integrate(x=>x*x,0,3),9,1e-12,'∫x² = 9');near(P.derivative(Math.sin,0),1,1e-9,"sin' 0 = 1");
  assert.equal(P.funcFeatures(Math.tan,-1.5,4.5).roots.length,2,'a jump is not a root (tan: 0 and π)');
  const sc=S.validateScene(S.template('func_features')).scene,svg=R.renderSVG(sc,{});
  assert.doesNotMatch(svg,/NaN|undefined/);assert.match(svg,/>S<\/tspan><tspan[^>]*> = /,'the area written');assert.match(svg,/stroke="#b42318"/,'the tangent drawn in the accent');
  /* the formula of a parametric curve is in t; one in x is refused there */
  assert.ok(S.validateScene({objects:[{id:'G',type:'graph'},{id:'c',type:'curve',graph:'G',kind:'param',expr:'cos(t)',expr2:'sin(t)'}]}).ok);
  assert.ok(!S.validateScene({objects:[{id:'G',type:'graph'},{id:'c',type:'curve',graph:'G',kind:'param',expr:'cos(x)',expr2:'sin(t)'}]}).ok);
});

/* the rigid-body world: a semi-implicit Euler step of 1/480 s, sequential impulses */
const rig=async(objects,extra)=>{const {S,P}=await load();return P.buildSim(scene(S,objects,extra));};
const crossing=(sim,read,T)=>{const ups=[];let prev=read(),t=0;while(t<T){t+=1e-3;sim.advanceTo(t);const v=read();if(prev<0&&v>=0)ups.push(t);prev=v;}return (ups.at(-1)-ups[0])/(ups.length-1);};
test('drawn shapes with physics: free fall ½gt², projectile range v² sin 2θ / g',async()=>{
  const sim=await rig([{id:'c',type:'ellipse',x:0,y:10,w:0.2,h:0.2,phys:'dynamic'}]);
  assert.equal(sim.systems[0].kind,'rigid');sim.run(1);near(10.1-sim.poses().get('c').y,0.5*g,3e-3,'fall in 1 s');
  const v=10,a=Math.PI/4,p=await rig([{id:'c',type:'ellipse',x:-0.05,y:-0.05,w:0.1,h:0.1,phys:'dynamic',pvx:v*Math.cos(a),pvy:v*Math.sin(a)}]);
  let prev=p.poses().get('c'),t=0,range=null;while(t<3&&range===null){t+=1e-3;p.advanceTo(t);const q=p.poses().get('c');if(t>0.5&&prev.y>=0&&q.y<0)range=prev.x+(q.x-prev.x)*prev.y/(prev.y-q.y);prev=q;}
  near(range,v*v/g,3e-3,'range');
});
test('drawn shapes with physics: an elastic collision keeps momentum and energy, a perfectly inelastic one moves together',async()=>{
  for(const e of [1,0]){
    const sim=await rig([{id:'a',type:'ellipse',x:0,y:0,w:0.2,h:0.2,phys:'dynamic',pmass:1,pvx:2,pe:e,pmu:0},{id:'b',type:'ellipse',x:1,y:0,w:0.2,h:0.2,phys:'dynamic',pmass:2,pe:e,pmu:0}],{gravityOn:false});
    sim.run(1.5);const va=sim.velocities().get('a').x,vb=sim.velocities().get('b').x;
    near(va+2*vb,2,1e-9,'momentum');
    if(e===1){near(va,-2/3,1e-6,'v_a');near(vb,4/3,1e-6,'v_b');near(0.5*va*va+vb*vb,2,1e-6,'kinetic energy');}
    else{near(va,2/3,1e-6,'common velocity');near(vb,2/3,1e-6,'common velocity');}
  }
});
test('drawn shapes with physics: a block on a drawn ramp slides with a = g (sin θ − μ cos θ) and stays when tan θ ≤ μ',async()=>{
  for(const [th,mu] of [[30,0.2],[40,0.3],[20,0.5],[25,0.47]]){
    const r=th*Math.PI/180,c=Math.cos(r),sn=Math.sin(r),w=0.4,h=0.2,cen={x:4*c-sn*h/2,y:4*sn+c*h/2};
    const sim=await rig([{id:'rp',type:'line',x1:0,y1:0,x2:6*c,y2:6*sn,phys:'static',pmu:mu},{id:'b',type:'rect',x:cen.x-w/2,y:cen.y-h/2,w,h,rot:th,phys:'dynamic',pmu:mu,pmass:2}]);
    sim.run(1);const v=sim.velocities().get('b'),a=g*(sn-mu*c),p=sim.poses().get('b');
    if(Math.tan(r)<=mu){assert.ok(Math.hypot(p.x-cen.x,p.y-cen.y)<1e-3,`held at θ=${th}, μ=${mu}`);}
    else{near(Math.hypot(v.x,v.y),a,5e-3,`speed after 1 s at θ=${th}, μ=${mu}`);assert.ok(Math.abs(p.angle-r)<1e-3,'it slides without tipping');}
  }
});
test('drawn shapes with physics: a rod joint is a pendulum (2π√(L/g)), a spring joint oscillates with 2π√(m/k)',async()=>{
  const L=1.2,a=5*Math.PI/180;
  const pend=await rig([{id:'c',type:'ellipse',x:L*Math.sin(a)-0.03,y:-L*Math.cos(a)-0.03,w:0.06,h:0.06,phys:'dynamic'},{id:'j',type:'joint',a:'c',b:'',kind:'rod',bx:0,by:0}]);
  near(crossing(pend,()=>pend.poses().get('c').x,12),2*Math.PI*Math.sqrt(L/g),3e-3,'pendulum period');
  const k=40,m=1,spr=await rig([{id:'c',type:'rect',x:-0.1,y:-1.3,w:0.2,h:0.2,phys:'dynamic',pmass:m},{id:'j',type:'joint',a:'c',b:'',kind:'spring',bx:0,by:0,k,L0:1}]);
  near(crossing(spr,()=>spr.poses().get('c').y+1+m*g/k,10),2*Math.PI*Math.sqrt(m/k),3e-3,'spring period');
  const e0=spr.energy();assert.ok(Number.isFinite(e0.E)&&e0.Us>0);
});
test('drawn shapes with physics: a stack of five boxes stands still for 10 s (no jitter, no explosion); the demo template runs',async()=>{
  const objs=[{id:'f',type:'line',x1:-2,y1:0,x2:2,y2:0,phys:'static'}];for(let i=0;i<5;i++)objs.push({id:'b'+i,type:'rect',x:-0.25+0.01*(i%2),y:i*0.3,w:0.5,h:0.3,phys:'dynamic'});
  const sim=await rig(objs);sim.run(10);
  for(const [id,p] of sim.poses()){const i=+id.slice(1);assert.ok(Math.abs(p.y-(0.15+0.3*i))<3e-3&&Math.abs(p.angle)<1e-3&&Math.abs(p.x-(0.01*(i%2)))<3e-3,id+' stayed');const v=sim.velocities().get(id);assert.ok(Math.hypot(v.x,v.y)<1e-3,id+' at rest');}
  const {S,P,R}=await load(),sc=S.validateScene(S.template('rigid_demo')).scene,d=P.buildSim(sc);d.run(3);
  for(const [,p] of d.poses())assert.ok(Number.isFinite(p.x)&&Number.isFinite(p.y));
  const svg=R.renderSVG(d.applyTo(sc),{poses:d.poses(),forces:d.forces()});assert.doesNotMatch(svg,/NaN|undefined/);
  /* deterministic: the same figure plays the same way */
  const d2=P.buildSim(sc);d2.run(3);assert.deepEqual([...d2.poses()],[...d.poses()]);
});

test('diagrams and notation: matrices of any size with dots and augmented bars, tensors, a neural network with weights, a block diagram; the schema for the AI',async()=>{
  const {S,R}=await load();
  for(const s of ['\\pmatrix{a_{11} & \\cdots & a_{1n} \\\\ \\vdots & \\ddots & \\vdots \\\\ a_{m1} & \\cdots & a_{mn}}','\\amatrix{1 & 2 & 3 \\\\ 4 & 5 & 6}','\\begin{array}{cc|c} 1 & 0 & 2 \\\\ 0 & 1 & 3 \\end{array}','\\begin{bmatrix} 1 & 0 \\\\ 0 & 1 \\end{bmatrix}','T^{\\mu\\nu}{}_{\\rho}','\\varepsilon_{ijk}\\delta_{jk}','R^{\\rho}{}_{\\sigma\\mu\\nu}']){
    const v=R.texSVG(s,20);assert.doesNotMatch(v,/NaN|undefined/,s);
  }
  const big=R.texSVG('\\pmatrix{1&2&3&4&5\\\\6&7&8&9&10\\\\1&2&3&4&5\\\\6&7&8&9&10\\\\1&2&3&4&5}',20);assert.equal((big.match(/<tspan/g)||[]).length,25,'5×5');
  assert.match(R.texSVG('\\amatrix{1 & 2 \\\\ 3 & 4}',20),/V[\d.]+"/,'the augmented bar');
  assert.deepEqual(S.nnLayers('2,3,1'),[2,3,1]);assert.equal(S.nnLayers('1'),null);
  assert.deepEqual(S.nnWeights('1 2 3 / 4 5 6 ; 7 / 8 / 9',[2,3,1]),[[[1,2,3],[4,5,6]],[[7],[8],[9]]]);
  for(const k of ['nn_mlp','matrix_eq','tensor_sample','block_flow']){const r=S.validateScene(S.template(k));assert.ok(r.ok,k);const svg=R.renderSVG(r.scene,{edit:true});assert.doesNotMatch(svg,/NaN|undefined/,k);}
  const nn=R.renderSVG(S.validateScene(S.template('nn_mlp')).scene,{});assert.match(nn,/stroke="#1d4ed8"/,'a positive weight in blue');assert.match(nn,/stroke="#c0262d"/,'a negative one in red');
  assert.equal((nn.match(/<line [^>]*stroke-opacity/g)||[]).length,2*3+3*1,'every weighted edge drawn');
  assert.ok(!S.validateScene({objects:[{id:'N',type:'nnet',layers:'0'}]}).ok);assert.ok(!S.validateScene({objects:[{id:'b',type:'fbox'},{id:'a',type:'farrow',a:'b',b:'b'}]}).ok);
  /* every template in every style: no attribute twice on a tag (a doubled one makes the downloaded SVG invalid XML), the
     values written on the figure typeset (not “mathrm”) */
  for(const k of S.TEMPLATE_KEYS)for(const style of S.STYLE_KEYS){const svg=R.renderSVG({...S.validateScene(S.template(k)).scene,style,values:true},{edit:true,grid:true});
    for(const m of svg.matchAll(/<[a-z]+ [^>]*>/g)){const names=[...m[0].matchAll(/ ([a-z-]+)="/g)].map(x=>x[1]);assert.equal(new Set(names).size,names.length,`${k}/${style}: ${m[0].slice(0,80)}`);}
    assert.doesNotMatch(svg,/>mathrm|>circ</,k);}
  const sch=S.sceneSchemaForAI();assert.equal(JSON.parse(JSON.stringify(sch)).types.block.fields.mass[0],'num');assert.deepEqual(sch.types.farrow.needs,['a','b']);assert.ok(sch.top.style[2].includes('modern'));
});

/* ── the figure editor round of 2026-11 (2): the figure's identity and links, the share passthrough, unsaved changes,
   new parts that do not stack, circuit junctions, free-body defaults, the friction region, the text style ── */
test('identity: a new, loaded or copied figure has its own uid; storage and share links go only with the figure they belong to',async()=>{
  const {S}=await load();
  const a=S.validateScene(S.template('atwood')).scene,b=S.validateScene(S.template('incline_pulley')).scene;
  const file={json:'f1',svg:'f2',base:5,name:'x.json',folder:'그림',hash:'h'};
  const opened=S.docFor('storage',a,{store:file});assert.deepEqual(opened.store,file);assert.equal(opened.share,null);assert.equal(S.docState(opened,a).state,'saved');
  /* every action that starts or loads another figure: a new uid and no links (모두 지우기, template, JSON, browser save, AI, photo) */
  const fresh=S.docFor('new',b);assert.notEqual(fresh.uid,opened.uid);assert.equal(fresh.store,null);assert.equal(fresh.share,null);assert.equal(S.docState(fresh,b).state,'new');
  const shared=S.docFor('share',b,{share:{remixOf:100}});assert.equal(shared.store,null);assert.deepEqual(shared.share,{remixOf:100});
  /* save as: a new identity on the new files; copy: no links and not saved */
  const sa=S.docFor('saved-as',a,{store:{...file,json:'f9'}});assert.notEqual(sa.uid,opened.uid);assert.equal(sa.store.json,'f9');assert.equal(sa.share,null);
  const cp=S.docFor('copy',a,{store:file,share:{id:3}});assert.equal(cp.store,null);assert.equal(cp.share,null);assert.equal(S.docState(cp,a).state,'unsaved');
  /* a recovery draft keeps its own identity and links, unsaved */
  const dr=S.docFor('draft',a,{uid:opened.uid,store:file,changes:4});assert.equal(dr.uid,opened.uid);assert.equal(dr.store.json,'f1');assert.deepEqual(S.docState(dr,a),{dirty:true,state:'unsaved',changes:4});
  for(let i=0;i<50;i++)assert.notEqual(S.docFor('new',a).uid,S.docFor('new',a).uid);
});

test('unsaved indicator: changes counted after a save, clean again when saved or undone to the saved figure; recovery drafts by identity',async()=>{
  const {S}=await load();
  const a=S.validateScene(S.template('atwood')).scene;let doc=S.docFor('storage',a,{store:{json:'f1'}});
  const b=JSON.parse(JSON.stringify(a));b.objects[0].mass=7;
  doc=S.docEdited(doc);assert.deepEqual(S.docState(doc,b),{dirty:true,state:'unsaved',changes:1});
  doc=S.docEdited(doc);assert.equal(S.docState(doc,b).changes,2);
  assert.equal(S.docState(doc,JSON.parse(JSON.stringify(a))).state,'saved','back to the saved figure (undo): clean');
  doc=S.docSaved(doc,b,{json:'f1',base:9});assert.deepEqual(S.docState(doc,b),{dirty:false,state:'saved',changes:0});
  let l=S.keepDraft([],doc,b,1);l=S.keepDraft(l,{uid:'u2',changes:3},a,2);l=S.keepDraft(l,doc,b,3);
  assert.deepEqual(l.map(d=>d.uid),[doc.uid,'u2'],'one draft an identity, newest first');assert.equal(l[0].store.json,'f1');
  assert.deepEqual(S.dropDraft(l,'u2').map(d=>d.uid),[doc.uid]);
  for(let i=0;i<9;i++)l=S.keepDraft(l,{uid:'k'+i},a,10+i);assert.equal(l.length,5);
  assert.notEqual(S.sceneSig(a),S.sceneSig(b));assert.equal(S.sceneSig(a),S.sceneSig(JSON.parse(JSON.stringify(a))));
});

test('작품 공유 → editor: the figures page passes ?share=N (a whole number only) on to draw.html, as the problem maker does',async()=>{
  const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
  const html=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8'),i=html.indexOf('function viewWorkshopDraw(){'),j=html.indexOf('\n}\n',i);
  assert.ok(i>0&&j>i);
  const src=(hash)=>{const ctx={lang:'ko',uiLang:'ko',UI:{ko:{navWork:'워크샵'}},wsTitle:()=>'그림 제작',location:{hash},document:{documentElement:{dataset:{theme:'light'}}},URLSearchParams};
    vm.createContext(ctx);vm.runInContext(html.slice(i,j+2)+';globalThis.out=viewWorkshopDraw();',ctx);return /src="draw\.html\?([^"]+)"/.exec(ctx.out)[1];};
  assert.match(src('#/workshop/draw?share=100'),/(^|&)share=100(&|$)/);
  assert.match(src('#/workshop/draw?t=atwood&share=7'),/t=atwood/);
  for(const bad of ['#/workshop/draw?share=1x','#/workshop/draw?share=0','#/workshop/draw?share=-3','#/workshop/draw'])assert.doesNotMatch(src(bad),/share=/,bad);
  /* the gallery's remix and "open in the editor" go to #/workshop/draw?share=N */
  assert.match(fs.readFileSync(path.join(__dirname,'..','workshop-share.js'),'utf8'),/#\/workshop\/draw\?share='\+p\.id/);
});

test('new parts do not stack: the nearest free place in whole steps, down and to the right first, inside the view',async()=>{
  const {S}=await load();
  const view={x:0,y:0,w:4,h:3},box={x:1.6,y:1.4,w:0.8,h:0.2};
  assert.deepEqual(S.freeSpot(box,[],0.2,view),{dx:0,dy:0});
  const placed=[];for(let k=0;k<6;k++){const {dx,dy}=S.freeSpot(box,placed,0.2,view);const b={...box,x:box.x+dx,y:box.y+dy};
    assert.ok(placed.every(p=>!(b.x<p.x+p.w-1e-9&&b.x+b.w>p.x+1e-9&&b.y<p.y+p.h-1e-9&&b.y+b.h>p.y+1e-9)),'no overlap '+k);
    assert.ok(b.x>=0&&b.x+b.w<=4&&b.y>=0&&b.y+b.h<=3,'inside');placed.push(b);}
  assert.ok(placed[1].y<placed[0].y||placed[1].x>placed[0].x,'down or right first');
  /* nowhere free: a cascade */
  assert.deepEqual(S.freeSpot(box,[{x:-10,y:-10,w:30,h:30}],0.2,view,3),{dx:0.6000000000000001,dy:-0.6000000000000001});
});

test('circuits: an end on the middle of a wire splits it into a junction (a dot); two resistors in parallel get I = E/R each',async()=>{
  const {S,P,R}=await load();
  const el=(id,kind,x1,y1,x2,y2,value)=>({id,type:'element',kind,x1,y1,x2,y2,...(value!=null?{value}:{})});
  /* battery on the left; R1 on top, R2 in the middle; the right rail is ONE wire from (2,1) to (2,0) that R2's lead ends on */
  const sc=scene(S,[el('E1','battery',0,0,0,1,12),el('W1','wire',0,1,0.6,1),el('R1','resistor',0.6,1,1.4,1,100),el('W2','wire',1.4,1,2,1),
    el('W3','wire',0.6,1,0.6,0.5),el('R2','resistor',0.6,0.5,1.4,0.5,200),el('W4','wire',1.4,0.5,2,0.5),el('W5','wire',2,1,2,0),el('W6','wire',2,0,0,0)]);
  const j=P.splitWires(sc);assert.equal(j.split.length,1);assert.equal(j.split[0].wire,'W5');assert.deepEqual([j.split[0].x,j.split[0].y],[2,0.5]);
  const w5=j.scene.objects.filter(o=>o.id==='W5'||o.id===j.split[0].added);assert.equal(w5.length,2);assert.ok(w5.some(w=>w.y2===0.5)&&w5.some(w=>w.y1===0.5));
  assert.ok(S.validateScene(j.scene).ok);assert.equal(P.splitWires(j.scene).split.length,0,'nothing left to split');
  for(const s0 of [sc,j.scene]){const c=P.solveCircuit(s0);assert.ok(c.ok);near(Math.abs(c.el.get('R1').I),0.12,1e-9,'I1 = 12/100');near(Math.abs(c.el.get('R2').I),0.06,1e-9,'I2 = 12/200');near(Math.abs(c.el.get('E1').I),0.18,1e-9,'I = I1 + I2');}
  const svg=R.renderSVG(j.scene,{edit:true});assert.equal((svg.match(/class="junction"/g)||[]).length,2,'the two three-way junctions, (0.6, 1) and (2, 0.5), are dots');
  /* an end on the body of a resistor does not join it: reported and ringed in the editor */
  const bad=scene(S,[el('E1','battery',0,0,0,1,12),el('R1','resistor',0,1,2,1,100),el('W1','wire',1,1,1,0)]);
  assert.deepEqual(P.splitWires(bad).loose,[{id:'W1',end:1,on:'R1'}]);assert.match(R.renderSVG(bad,{edit:true}),/class="loose"/);
});

test('free-body diagram: forces added one after another are mg (down), N (off the surface), T (along the string), f (against the motion), then F, at distinct angles',async()=>{
  const {S}=await load();
  let sc=S.validateScene(S.template('incline_pulley')).scene;const inc=sc.objects.find(o=>o.type==='incline'),th=inc.angle;
  const out=[];for(let k=0;k<6;k++){const f=S.nextForce(sc,'m1');out.push(f);sc=S.validateScene({...sc,objects:[...sc.objects,{...S.defaults('force'),id:'Fq'+k,on:'m1',...f}]}).scene;}
  assert.deepEqual(out.map(f=>f.label),['mg','N','T','f','F','F_2']);
  assert.equal(out[0].angle,-90);near(out[0].F,2*9.8,1e-2,'mg');
  near(out[1].angle,90+th,1e-6,'N ⟂ incline');near(out[2].angle,th,1e-6,'T up the slope');near(out[3].angle,th-180,1e-6,'f down the slope (m1 is pulled up)');
  const angles=out.map(f=>((f.angle%360)+360)%360);assert.equal(new Set(angles.map(a=>Math.round(a))).size,angles.length,'all angles different');
  /* a body hanging from the pulley: T straight up; a free body: mg then F */
  assert.equal(S.nextForce(S.validateScene({...sc,objects:[...sc.objects,{...S.defaults('force'),id:'G1',on:'m2',...S.nextForce(sc,'m2')}]}).scene,'m2').angle,90);
  assert.equal(S.nextForce(sc,'nothing'),null);
});

test('friction region (마찰 구간): on a floor or incline, checked, drawn as a band with μ, found in the palette data; the solver uses its μ on that span',async()=>{
  const {S,P,R}=await load();
  assert.ok(S.DOMAINS.mech.includes('rough'));assert.ok(!S.validateScene({objects:[{id:'z',type:'rough'}]}).ok,'needs a surface');
  assert.ok(!S.validateScene({objects:[{id:'b',type:'block'},{id:'z',type:'rough',on:'b'}]}).ok,'a floor or an incline only');
  /* a block sliding at 4 m/s on a smooth floor enters a span with μ = 0.5 at 1 m: it stops v²/(2μg) further on */
  const mk=(mu,len=2)=>scene(S,[{id:'f',type:'floor',x:0,y:0,w:6,mu:0},{id:'z',type:'rough',on:'f',from:1,len,mu},{id:'b',type:'block',on:'f',at:0.5,w:0.2,h:0.2,mass:1,vx:4}]);
  const sim=P.buildSim(mk(0.5));sim.run(0.1);near(Math.hypot(sim.velocities().get('b').x,0),4,1e-9,'smooth before the span');
  sim.run(2);near(sim.poses().get('b').at,1+16/(2*0.5*g),1e-3,'stops at 1 + v²/(2μg)');near(sim.velocities().get('b').x,0,1e-9,'at rest');
  const e=sim.energy();near(e.heat,0.5*16,1e-3,'all kinetic energy to heat');
  /* a short span: it slows, leaves it and slides on at √(v² − 2μgL) */
  const s2=P.buildSim(mk(0.5,0.5));s2.run(1.5);near(s2.velocities().get('b').x,Math.sqrt(16-2*0.5*g*0.5),1e-3,'out of the span');
  /* an incline: a block held by the span (tan θ < μ) stays, one above it slides */
  const inc=a=>scene(S,[{id:'i',type:'incline',x:0,y:0,angle:20,length:4,mu:0},{id:'z',type:'rough',on:'i',from:0,len:2,mu:0.6},{id:'b',type:'block',on:'i',at:a,w:0.2,h:0.2,mass:1}]);
  const h=P.buildSim(inc(1));h.run(1);assert.equal(h.poses().get('b').at,1,'held');
  const sl=P.buildSim(inc(3));sl.run(0.3);assert.ok(sl.poses().get('b').at<3,'slides above the span');
  const svg=R.renderSVG(mk(0.5),{edit:true});assert.match(svg,/data-id="z"/);assert.match(svg,/<polygon points=/);assert.match(svg,/μ/);assert.doesNotMatch(svg,/NaN|undefined/);
  const fs=require('node:fs'),path=require('node:path'),src=fs.readFileSync(path.join(__dirname,'..','draw.js'),'utf8');
  assert.match(src,/\['rough', \{\}, N2\('마찰 구간 \(거친 면\)', 'Friction region \(rough patch\)'\), '[^']*friction rough[^']*마찰[^']*'\]/,'the palette finds it by 마찰, friction, rough');
});

test('values on the figure: no pulley radius; an incline\'s angle goes with its name (θ = 30°), not on top of it',async()=>{
  const {S,R}=await load();
  const sc={...S.validateScene(S.template('incline_pulley')).scene,values:true},svg=R.renderSVG(sc,{});
  const p=sc.objects.find(o=>o.type==='pulley');assert.doesNotMatch(svg,new RegExp('>'+p.r+'</tspan>'),'no pulley radius');
  const txt=[...svg.matchAll(/<text[^>]*>(.*?)<\/text>/g)].map(m=>m[1].replace(/<[^>]+>/g,''));assert.ok(txt.some(t=>/θ.*=.*30°/.test(t)),'θ = 30° together: '+txt.join(' | '));
  assert.ok(!txt.some(t=>t==='30°'),'no separate 30°');
});

test('text style: labels and text boxes take face, italic, bold, underline, alignment; runs \\textit \\textbf \\mathrm \\mathsf \\mathtt \\text; old labels read as before; the SVG carries it',async()=>{
  const {S,R}=await load();
  const old=S.validateScene({objects:[{id:'l1',type:'label',x:0,y:0,text:'m_1 v'}]});assert.ok(old.ok);
  assert.deepEqual(['font','italic','bold','underline','align'].map(k=>old.scene.objects[0][k]),['math',false,false,false,'center'],'migrated to the defaults');
  const v={x:-1,y:-1,w:2,h:2};
  assert.equal(R.renderSVG(old.scene,{view:v}),R.renderSVG(S.validateScene({objects:[{...old.scene.objects[0]}]}).scene,{view:v}),'the defaults draw as before');
  const st={id:'l2',type:'label',x:0,y:0,text:'Hello x',font:'mono',italic:true,bold:true,underline:true,align:'left',box:true};
  const r=S.validateScene({objects:[st]});assert.ok(r.ok);const back=S.validateScene(JSON.parse(JSON.stringify(r.scene)));assert.deepEqual(back.scene.objects[0],r.scene.objects[0],'round trip through JSON');
  assert.ok(!S.validateScene({objects:[{...st,font:'comic'}]}).ok,'faces are a closed list');assert.ok(!S.validateScene({objects:[{...st,align:'justify'}]}).ok);
  const svg=R.renderSVG(r.scene,{view:v});
  assert.match(svg,/font-family="'Courier New'[^"]*monospace"/,'the mono stack');assert.match(svg,/font-style="italic"/);assert.match(svg,/font-weight="bold"/);
  assert.match(svg,/<path d="M0,[\d.]+H[\d.]+"[^>]*stroke-width/,'the underline');assert.doesNotMatch(svg,/@font-face|url\(/,'no fonts loaded');
  const x0=+/<tspan x="([\d.]+)"/.exec(svg)[1];assert.ok(Math.abs(x0-400)<1,'left-aligned: starts at x');
  /* a text face: letters upright (no italic) unless asked */
  const serif=R.renderSVG(S.validateScene({objects:[{id:'l3',type:'label',x:0,y:0,text:'m v',font:'serif'}]}).scene,{view:v});assert.doesNotMatch(serif,/font-style="italic"/);
  for(const f of ['sans','hand'])assert.match(R.renderSVG(S.validateScene({objects:[{id:'l3',type:'label',x:0,y:0,text:'a',font:f}]}).scene,{view:v}),new RegExp(f==='sans'?"Helvetica":"Segoe Print"));
  /* runs inside one label */
  const runs=R.renderSVG(S.validateScene({objects:[{id:'l4',type:'label',x:0,y:0,text:'\\textbf{F} = \\mathtt{code} + \\mathsf{S} + \\textit{it} + \\text{kg}'}]}).scene,{view:v});
  assert.match(runs,/font-weight="bold">F</);assert.match(runs,/monospace"[^>]*>code</);assert.match(runs,/sans-serif"[^>]*>S</);assert.match(runs,/font-style="italic"[^>]*>it</);assert.match(runs,/<tspan[^>]*>kg</);assert.doesNotMatch(runs,/italic"[^>]*>kg</);
  assert.equal(R.texRuns('\\mathtt{ab}')[0].it,false);
});

test('ink in the editor: the pen tool drives draw-ink.mjs; a stroke or a group is one step of history; 다른 모양으로 swaps in place; 수식 쓰기 posts to the maths route',async()=>{
  const {S}=await load();const I=await import('../draw-ink.mjs');
  const fs=require('node:fs'),path=require('node:path'),src=fs.readFileSync(path.join(__dirname,'..','draw.js'),'utf8');
  assert.match(src,/import \{createInkController, toSceneObjects, candidatesFromScene, rasteriseStrokes, mathRequestBody, MATH_PATH[^}]*\} from '\.\/draw-ink\.mjs/);
  for(const re of [/st\.tool === 'pen'[^\n]*\n[^\n]*\n\s*if \(st\.ink\.pointerdown\(ev\)\)/,/if \(st\.ink\?\.pointermove\(ev\)\) return;/,/st\.ink\.pointerup\(ev\)/,/onShape: \(r, ctx\) => insertInk\(r, ctx\)/,/onMathRegion: m => readMath\(m\.strokes\)/,/api\(MATH_PATH, 'POST', mathRequestBody\(png\.dataUrl\)\)/,/commit\(next, \{before: L\.before\}\)/,/autoShape: p\.inkAuto !== false/,/fingerDraw: p\.inkFinger === true/])assert.match(src,re,String(re));
  /* the history the editor keeps: stroke 1 (S0 → S1), then a group that replaces it, committed with the state before
     stroke 1 → one undo goes back to S0 */
  const h=S.createHistory(10),S0='{"s":0}';h.record(S0);h.record(S0);assert.equal(h.size,1,'the group adds no second step');assert.equal(h.undo('{"s":2}'),S0);
  /* the shapes the editor inserts are scene objects the validator takes */
  const line=I.toSceneObjects({type:'line',params:{a:{x:0,y:0},b:{x:1,y:0.02}}},{grid:0.1,look:{color:'blue',lw:1,pattern:'solid'}});assert.equal(line[0].type,'line');
  const lab=I.toSceneObjects({type:'latex',params:{latex:'F = m\\vec{a}',x:1,y:1,size:18}},{});assert.equal(lab[0].text,'$F = m\\vec{a}$');
  assert.ok(S.validateScene({objects:[...line,...lab]}).ok);assert.equal(I.MATH_PATH,'/api/workshop/ai/math');
});
