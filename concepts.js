/* Concept simulations for beginners: watch the motion, change one quantity, read the numbers, then answer one
   question about it. Each simulation integrates its own equations (RK4 or exact where simple); nothing is canned. */
(()=>{
  'use strict';
  const $=id=>document.getElementById(id);
  const params=new URL(location.href).searchParams;
  const embedded=params.get('embed')==='1'&&window.parent!==window;
  const G=9.8;
  const L=(ko,en)=>({ko,en});
  const LANGS=['ko','en'];
  const tx=en=>state.lang==='en'||state.lang==='ko'?en:(window.HL_I18N?.t?.(en,state.lang)??en);
  const state={lang:LANGS.includes(params.get('lang'))?params.get('lang'):'ko',sim:null,s:null,p:{},running:true,last:0,graph:[],answered:false};
  const tr=v=>typeof v==='string'?v:state.lang==='ko'?v.ko:tx(v.en);
  const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const fmt=(v,d=2)=>Number.isFinite(v)?(Math.abs(v)<1e-9?'0':v.toFixed(d)):'—';
  const css=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();

  /* ── the simulations ── */
  const SIMS=[
    {id:'pulley-cart',unit:'mechanics/newton',title:L('도르래로 연결된 수레와 추','A cart pulled by a hanging weight'),
      intro:L('수평면 위 수레(질량 M)가 도르래를 지나는 줄로 추(질량 m)와 연결되어 있습니다. 놓으면 둘은 같은 가속도로 움직입니다. "줄 끊기"를 누르면 그 뒤로 수레는 등속, 추는 자유 낙하합니다.','A cart (mass M) on a table is tied over a pulley to a hanging weight (m). Released, both share one acceleration. Cut the string and the cart keeps its speed while the weight falls freely.'),
      params:[{k:'M',l:L('수레 질량 M','Cart mass M'),min:0.5,max:5,step:0.1,v:2,u:'kg'},{k:'m',l:L('추 질량 m','Weight mass m'),min:0.1,max:3,step:0.1,v:1,u:'kg'},{k:'mu',l:L('마찰 계수 μ','Friction μ'),min:0,max:0.6,step:0.01,v:0,u:''}],
      action:L('줄 끊기','Cut the string'),
      init:()=>({t:0,x:0,v:0,y:0,vy:0,cut:false}),
      step(s,p,dt){
        if(!s.cut){const a=Math.max(0,(p.m*G-p.mu*p.M*G))/(p.M+p.m);s.v+=a*dt;s.x+=s.v*dt;s.vy=s.v;s.y=s.x;s.a=a;}
        else{const ac=p.mu>0&&s.v>0?-p.mu*G:0;s.v=Math.max(0,s.v+ac*dt);s.x+=s.v*dt;s.vy+=G*dt;s.y+=s.vy*dt;s.a=ac;}
        s.t+=dt;if(s.x>3.2||s.y>3.2)s.done=true;
      },
      onAction(s){s.cut=true;},
      readouts:(s,p)=>[[L('시간','time'),fmt(s.t)+' s'],[L('가속도 (수레)','acceleration (cart)'),fmt(s.a||0)+' m/s²'],[L('속력 (수레)','speed (cart)'),fmt(s.v)+' m/s'],[L('장력','tension'),s.cut?'0 N':fmt(p.m*(G-(s.a||0)))+' N']],
      graph:{label:L('수레 속력 v (m/s)','cart speed v (m/s)'),y:s=>s.v},
      draw(g,s,p,w,h){
        const tableY=h*0.42,edge=w*0.72,scale=w*0.16,cartW=40+p.M*10,cartH=26+p.M*4;
        g.fillStyle=css('--line');g.fillRect(20,tableY,edge-20,6);g.fillRect(edge-6,tableY,6,h-tableY-10);
        const px=edge+12,py=tableY-2;g.strokeStyle=css('--muted');g.lineWidth=2;g.beginPath();g.arc(px,py,12,0,2*Math.PI);g.stroke();
        const cx=Math.min(30+s.x*scale,edge-cartW-14);
        g.fillStyle=css('--s1');g.fillRect(cx,tableY-cartH,cartW,cartH);
        g.fillStyle=css('--ink');for(const wx of [cx+10,cx+cartW-10]){g.beginPath();g.arc(wx,tableY-2,5,0,2*Math.PI);g.fill();}
        const wy=py+30+s.y*scale,size=16+p.m*8;
        g.strokeStyle=css('--ink');g.lineWidth=1.5;
        if(!s.cut){g.beginPath();g.moveTo(cx+cartW,tableY-cartH/2);g.lineTo(px,py-12);g.moveTo(px+12,py);g.lineTo(px+12,wy);g.stroke();}
        g.fillStyle=css('--s2');g.fillRect(px+12-size/2,Math.min(wy,h-size-4),size,size);
        g.fillStyle=css('--muted');g.font='12px system-ui';g.fillText('M',cx+cartW/2-4,tableY-cartH/2+4);g.fillText('m',px+8,Math.min(wy,h-size-4)+size/2+4);
      },
      quiz:{q:L('M = 2 kg, m = 1 kg, 마찰이 없을 때 수레의 가속도는? (g = 9.8 m/s²)','With M = 2 kg, m = 1 kg and no friction, what is the cart’s acceleration? (g = 9.8 m/s²)'),
        choices:['9.8 m/s²','4.9 m/s²','3.3 m/s²','2.5 m/s²'],a:2,
        why:L('두 물체를 한 덩어리로 보면 알짜힘은 mg, 전체 질량은 M+m이므로 a = mg/(M+m) = g/3 ≈ 3.3 m/s²입니다. 슬라이더를 이 값에 맞추면 같은 결과가 나옵니다.','Treat both as one body: net force mg, total mass M+m, so a = mg/(M+m) = g/3 ≈ 3.3 m/s². Set the sliders to these values and you get the same number.')}},

    {id:'hemisphere',unit:'mechanics/circular',title:L('반구에서 미끄러지는 물체','Sliding off a hemisphere'),
      intro:L('마찰 없는 반구 꼭대기에서 물체가 출발합니다. 수직항력이 0이 되는 순간 물체는 면을 떠나 포물선 운동을 합니다. 출발 속력을 바꿔 떠나는 높이를 재 보세요.','A block starts at the top of a frictionless hemisphere. When the normal force reaches zero it leaves the surface and flies as a projectile. Change the starting speed and read the height where it leaves.'),
      params:[{k:'R',l:L('반지름 R','Radius R'),min:0.5,max:2,step:0.1,v:1,u:'m'},{k:'v0',l:L('출발 속력 v₀','Start speed v₀'),min:0.02,max:3,step:0.02,v:0.1,u:'m/s'}],
      init:(p)=>({t:0,th:0,w:p.v0/p.R,on:true,x:0,y:p.R,vx:p.v0,vy:0,leave:null}),
      step(s,p,dt){
        if(s.on){
          const f=(th,w)=>[w,G/p.R*Math.sin(th)];
          const k1=f(s.th,s.w),k2=f(s.th+dt/2*k1[0],s.w+dt/2*k1[1]),k3=f(s.th+dt/2*k2[0],s.w+dt/2*k2[1]),k4=f(s.th+dt*k3[0],s.w+dt*k3[1]);
          s.th+=dt/6*(k1[0]+2*k2[0]+2*k3[0]+k4[0]);s.w+=dt/6*(k1[1]+2*k2[1]+2*k3[1]+k4[1]);
          const v=s.w*p.R,N=G*Math.cos(s.th)-v*v/p.R;
          s.x=p.R*Math.sin(s.th);s.y=p.R*Math.cos(s.th);s.vx=v*Math.cos(s.th);s.vy=-v*Math.sin(s.th);s.N=N;
          if(N<=0){s.on=false;s.leave={h:s.y,th:s.th};}
        }else{s.x+=s.vx*dt;s.vy-=G*dt;s.y+=s.vy*dt;if(s.y<-0.05)s.done=true;}
        s.t+=dt;
      },
      readouts:(s,p)=>[[L('각도 θ','angle θ'),fmt(s.th*180/Math.PI,1)+'°'],[L('속력','speed'),fmt(Math.hypot(s.vx,s.vy))+' m/s'],[L('떠난 높이','height when it leaves'),s.leave?fmt(s.leave.h)+' m ('+fmt(s.leave.h/p.R)+' R)':'—'],[L('이론값','theory'),fmt((2+p.v0*p.v0/(G*p.R))/3*p.R)+' m']],
      graph:{label:L('수직항력 / mg','normal force / mg'),y:s=>s.on?Math.max(0,s.N/G):0},
      draw(g,s,p,w,h){
        const sc=Math.min(w*0.32,h*0.55)/p.R,ox=w*0.38,oy=h-20;
        g.fillStyle=css('--surface-alt');g.strokeStyle=css('--line');g.lineWidth=2;
        g.beginPath();g.arc(ox,oy,p.R*sc,Math.PI,0);g.closePath();g.fill();g.stroke();
        g.fillStyle=css('--line');g.fillRect(10,oy,w-20,3);
        if(s.leave){g.setLineDash([4,4]);g.strokeStyle=css('--s3');g.beginPath();g.moveTo(10,oy-s.leave.h*sc);g.lineTo(w-10,oy-s.leave.h*sc);g.stroke();g.setLineDash([]);}
        g.fillStyle=css('--s2');g.beginPath();g.arc(ox+s.x*sc,oy-s.y*sc-7,7,0,2*Math.PI);g.fill();
      },
      quiz:{q:L('꼭대기에서 거의 정지 상태로 출발하면, 물체는 바닥에서 얼마 높이에서 반구를 떠날까요?','Starting from almost rest at the top, at what height above the ground does the block leave?'),
        choices:['R','3R/4','2R/3','R/2'],a:2,
        why:L('떠나는 순간 수직항력이 0이므로 mg cosθ = mv²/R, 에너지 보존 v² = 2gR(1−cosθ)에서 cosθ = 2/3, 높이 R cosθ = 2R/3입니다.','At the moment N = 0: mg cosθ = mv²/R, and energy gives v² = 2gR(1−cosθ), so cosθ = 2/3 and the height is 2R/3.')}},

    {id:'projectile',unit:'mechanics/kinematics',title:L('포물선 운동과 공기 저항','Projectiles and air drag'),
      intro:L('같은 속력으로 던진 공의 궤적입니다. 점선은 공기 저항이 없을 때입니다. 각도와 저항을 바꿔 가장 멀리 가는 각도를 찾아보세요.','The path of a ball thrown at fixed speed; the dashed line is without air drag. Change the angle and drag to find the angle that goes farthest.'),
      params:[{k:'v0',l:L('속력 v₀','Speed v₀'),min:5,max:30,step:0.5,v:18,u:'m/s'},{k:'ang',l:L('각도','Angle'),min:5,max:85,step:1,v:45,u:'°'},{k:'k',l:L('저항 계수 k','Drag k'),min:0,max:1,step:0.02,v:0.2,u:'1/s'}],
      init:(p)=>{const a=p.ang*Math.PI/180;return{t:0,x:0,y:0,vx:p.v0*Math.cos(a),vy:p.v0*Math.sin(a),path:[[0,0]],max:0};},
      step(s,p,dt){
        if(s.done)return;
        const f=(vx,vy)=>[-p.k*vx,-G-p.k*vy];
        const a1=f(s.vx,s.vy),a2=f(s.vx+dt/2*a1[0],s.vy+dt/2*a1[1]),a3=f(s.vx+dt/2*a2[0],s.vy+dt/2*a2[1]),a4=f(s.vx+dt*a3[0],s.vy+dt*a3[1]);
        const nvx=s.vx+dt/6*(a1[0]+2*a2[0]+2*a3[0]+a4[0]),nvy=s.vy+dt/6*(a1[1]+2*a2[1]+2*a3[1]+a4[1]);
        const nx=s.x+dt*(s.vx+nvx)/2,ny=s.y+dt*(s.vy+nvy)/2;
        if(ny<0){s.x=s.x+(nx-s.x)*s.y/(s.y-ny);s.y=0;s.done=true;}else{s.x=nx;s.y=ny;}
        s.vx=nvx;s.vy=nvy;s.t+=dt;s.max=Math.max(s.max,s.y);s.path.push([s.x,s.y]);
      },
      readouts:(s,p)=>{const a=p.ang*Math.PI/180;return[[L('수평 거리','range'),fmt(s.x,1)+' m'],[L('최고 높이','max height'),fmt(s.max,1)+' m'],[L('비행 시간','flight time'),fmt(s.t)+' s'],[L('저항 없을 때 거리','range without drag'),fmt(p.v0*p.v0*Math.sin(2*a)/G,1)+' m']];},
      graph:{label:L('높이 y (m)','height y (m)'),y:s=>s.y},
      draw(g,s,p,w,h){
        const a=p.ang*Math.PI/180,R0=p.v0*p.v0/G,sc=Math.min((w-40)/R0,(h-30)/(R0/2+0.5)),ox=20,oy=h-14;
        g.fillStyle=css('--line');g.fillRect(10,oy,w-20,2);
        g.setLineDash([5,4]);g.strokeStyle=css('--muted');g.beginPath();
        const T=2*p.v0*Math.sin(a)/G;for(let i=0;i<=60;i++){const t=T*i/60,x=p.v0*Math.cos(a)*t,y=p.v0*Math.sin(a)*t-G*t*t/2;i?g.lineTo(ox+x*sc,oy-y*sc):g.moveTo(ox,oy);}g.stroke();g.setLineDash([]);
        g.strokeStyle=css('--s1');g.lineWidth=2;g.beginPath();s.path.forEach(([x,y],i)=>i?g.lineTo(ox+x*sc,oy-y*sc):g.moveTo(ox,oy));g.stroke();g.lineWidth=1;
        g.fillStyle=css('--s2');g.beginPath();g.arc(ox+s.x*sc,oy-s.y*sc,6,0,2*Math.PI);g.fill();
      },
      quiz:{q:L('공기 저항이 없을 때 같은 속력으로 가장 멀리 던지려면 몇 도로 던져야 할까요?','Without air drag, at what angle does a ball thrown at a fixed speed go farthest?'),
        choices:['30°','45°','60°','저항과 상관없이 항상 같다 / always the same'],a:1,
        why:L('수평 거리 R = v₀² sin2θ / g는 2θ = 90°, 즉 θ = 45°에서 가장 큽니다. 저항을 켜면 가장 멀리 가는 각도는 45°보다 작아집니다.','The range R = v₀² sin2θ / g is largest at 2θ = 90°, θ = 45°. Turn drag on and the best angle drops below 45°.')}},

    {id:'pendulum',unit:'waves/shm',title:L('단진자의 주기','The period of a pendulum'),
      intro:L('진자를 놓으면 왕복 운동을 합니다. 시뮬레이션에서 잰 주기를 작은 각 근사 2π√(L/g)와 비교해 보세요. 진폭을 키우면 둘이 달라집니다.','Release the pendulum and it swings. Compare the measured period with the small-angle value 2π√(L/g). At large amplitude the two differ.'),
      params:[{k:'Lp',l:L('길이 L','Length L'),min:0.2,max:3,step:0.05,v:1,u:'m'},{k:'th0',l:L('진폭 θ₀','Amplitude θ₀'),min:2,max:170,step:1,v:20,u:'°'}],
      init:(p)=>({t:0,th:p.th0*Math.PI/180,w:0,cross:[],period:null}),
      step(s,p,dt){
        const f=(th,w)=>[w,-G/p.Lp*Math.sin(th)];
        const k1=f(s.th,s.w),k2=f(s.th+dt/2*k1[0],s.w+dt/2*k1[1]),k3=f(s.th+dt/2*k2[0],s.w+dt/2*k2[1]),k4=f(s.th+dt*k3[0],s.w+dt*k3[1]);
        const nth=s.th+dt/6*(k1[0]+2*k2[0]+2*k3[0]+k4[0]),nw=s.w+dt/6*(k1[1]+2*k2[1]+2*k3[1]+k4[1]);
        if(s.w<0&&nw>=0)s.cross.push(s.t+dt*(-s.w)/(nw-s.w));   /* turning points on one side */
        if(s.cross.length>=2)s.period=s.cross.at(-1)-s.cross.at(-2);
        s.th=nth;s.w=nw;s.t+=dt;
      },
      readouts:(s,p)=>[[L('잰 주기','measured period'),s.period?fmt(s.period,3)+' s':'…'],[L('근사 2π√(L/g)','small-angle 2π√(L/g)'),fmt(2*Math.PI*Math.sqrt(p.Lp/G),3)+' s'],[L('각도','angle'),fmt(s.th*180/Math.PI,1)+'°']],
      graph:{label:L('각도 θ (°)','angle θ (°)'),y:s=>s.th*180/Math.PI},
      draw(g,s,p,w,h){
        const ox=w/2,oy=24,sc=(h-60)/3,len=p.Lp*sc,x=ox+len*Math.sin(s.th),y=oy+len*Math.cos(s.th);
        g.fillStyle=css('--line');g.fillRect(ox-60,oy-4,120,4);
        g.strokeStyle=css('--ink');g.lineWidth=1.5;g.beginPath();g.moveTo(ox,oy);g.lineTo(x,y);g.stroke();
        g.fillStyle=css('--s1');g.beginPath();g.arc(x,y,12,0,2*Math.PI);g.fill();
      },
      quiz:{q:L('진폭이 작을 때, 진폭을 두 배로 늘리면 주기는?','At small amplitude, doubling the amplitude makes the period…'),
        choices:L(['두 배가 된다','거의 그대로다','절반이 된다','√2배가 된다'],['double','stay almost the same','halve','grow by √2']),a:1,
        why:L('작은 각에서는 sinθ ≈ θ라 주기가 2π√(L/g)로 진폭과 무관합니다(등시성). 진폭을 60° 이상으로 올리면 잰 주기가 근사보다 길어지는 것을 볼 수 있습니다.','For small angles sinθ ≈ θ and the period 2π√(L/g) does not depend on amplitude. Above about 60° the measured period grows longer than the approximation.')}},

    {id:'collision',unit:'mechanics/momentum',title:L('1차원 충돌','Collisions in one dimension'),
      intro:L('두 수레가 마주 보고 움직이다 부딪힙니다. 반발 계수 e = 1은 탄성 충돌, e = 0은 완전 비탄성 충돌입니다. 운동량과 운동 에너지가 어떻게 되는지 보세요.','Two carts collide. Restitution e = 1 is elastic, e = 0 perfectly inelastic. Watch what happens to momentum and kinetic energy.'),
      params:[{k:'m1',l:L('질량 m₁','Mass m₁'),min:0.5,max:5,step:0.1,v:1,u:'kg'},{k:'m2',l:L('질량 m₂','Mass m₂'),min:0.5,max:5,step:0.1,v:1,u:'kg'},{k:'u1',l:L('속도 v₁','Velocity v₁'),min:-3,max:3,step:0.1,v:2,u:'m/s'},{k:'u2',l:L('속도 v₂','Velocity v₂'),min:-3,max:3,step:0.1,v:0,u:'m/s'},{k:'e',l:L('반발 계수 e','Restitution e'),min:0,max:1,step:0.05,v:1,u:''}],
      init:(p)=>({t:0,x1:-1.2,x2:1.2,v1:p.u1,v2:p.u2,hit:false}),
      step(s,p,dt){
        const w1=0.15+p.m1*0.04,w2=0.15+p.m2*0.04;
        s.x1+=s.v1*dt;s.x2+=s.v2*dt;s.t+=dt;
        if(!s.hit&&s.x2-s.x1<=w1+w2&&s.v1>s.v2){
          const M=p.m1+p.m2,P=p.m1*s.v1+p.m2*s.v2,rel=s.v1-s.v2;
          s.v1=(P-p.m2*p.e*rel)/M;s.v2=(P+p.m1*p.e*rel)/M;s.hit=true;
        }
        if(Math.abs(s.x1)>3.5||Math.abs(s.x2)>3.5)s.done=true;
      },
      readouts:(s,p)=>[[L('총 운동량','total momentum'),fmt(p.m1*s.v1+p.m2*s.v2)+' kg·m/s'],[L('총 운동 에너지','total kinetic energy'),fmt(p.m1*s.v1*s.v1/2+p.m2*s.v2*s.v2/2)+' J'],[L('처음 운동 에너지','initial kinetic energy'),fmt(p.m1*p.u1*p.u1/2+p.m2*p.u2*p.u2/2)+' J'],['v₁, v₂',fmt(s.v1)+', '+fmt(s.v2)+' m/s']],
      graph:{label:L('운동 에너지 (J)','kinetic energy (J)'),y:(s,p)=>p.m1*s.v1*s.v1/2+p.m2*s.v2*s.v2/2},
      draw(g,s,p,w,h){
        const sc=w/7.2,ox=w/2,y=h*0.6,w1=(0.15+p.m1*0.04)*sc,w2=(0.15+p.m2*0.04)*sc;
        g.fillStyle=css('--line');g.fillRect(10,y,w-20,3);
        g.fillStyle=css('--s1');g.fillRect(ox+s.x1*sc-w1,y-2*w1*0.6,2*w1,2*w1*0.6);
        g.fillStyle=css('--s2');g.fillRect(ox+s.x2*sc-w2,y-2*w2*0.6,2*w2,2*w2*0.6);
        g.fillStyle=css('--muted');g.font='12px system-ui';g.fillText('m₁',ox+s.x1*sc-6,y+16);g.fillText('m₂',ox+s.x2*sc-6,y+16);
      },
      quiz:{q:L('질량이 같은 두 수레가 탄성 충돌(e = 1)하고, 하나는 정지해 있었습니다. 충돌 뒤에는?','Equal masses, elastic (e = 1), one cart at rest. After the collision…'),
        choices:L(['둘이 붙어서 절반 속력으로 간다','움직이던 수레는 멈추고 정지했던 수레가 그 속도로 간다','둘 다 멈춘다','움직이던 수레가 튕겨 나온다'],['they stick and move at half speed','the moving cart stops and the other leaves with its velocity','both stop','the moving cart bounces back']),a:1,
        why:L('운동량과 운동 에너지가 모두 보존되면 같은 질량의 두 물체는 속도를 맞바꿉니다. m₁ = m₂, v₂ = 0, e = 1로 맞춰 확인해 보세요.','With momentum and kinetic energy both conserved, equal masses swap velocities. Set m₁ = m₂, v₂ = 0, e = 1 to see it.')}},

    {id:'charges',unit:'em/electrostatics',title:L('두 전하가 만드는 전기장','The field of two charges'),
      intro:L('두 점전하 주변의 전기장 방향(화살표)과 세기(색)를 보여 줍니다. 시험 전하는 전기력을 받아 움직입니다. 전하의 부호와 크기를 바꿔 보세요.','Arrows show the field direction around two point charges and colour shows its strength. A small test charge moves under the force. Change the charges’ signs and sizes.'),
      params:[{k:'q1',l:L('전하 q₁','Charge q₁'),min:-3,max:3,step:0.5,v:1,u:''},{k:'q2',l:L('전하 q₂','Charge q₂'),min:-3,max:3,step:0.5,v:-1,u:''}],
      init:()=>({t:0,x:0.05,y:0.6,vx:0,vy:0}),
      field(p,x,y){let ex=0,ey=0;for(const [q,cx] of [[p.q1,-1],[p.q2,1]]){const dx=x-cx,dy=y,r2=dx*dx+dy*dy+0.01,r3=r2*Math.sqrt(r2);ex+=q*dx/r3;ey+=q*dy/r3;}return[ex,ey];},
      step(s,p,dt){
        const [ex,ey]=this.field(p,s.x,s.y);s.vx+=0.3*ex*dt;s.vy+=0.3*ey*dt;s.vx*=0.995;s.vy*=0.995;s.x+=s.vx*dt;s.y+=s.vy*dt;s.t+=dt;
        if(Math.abs(s.x)>2.6||Math.abs(s.y)>1.6||Math.hypot(s.x+1,s.y)<0.08||Math.hypot(s.x-1,s.y)<0.08)s.done=true;
      },
      readouts:(s,p)=>{const [ex,ey]=SIMS[5].field(p,0,0);return[[L('가운데 점의 전기장','field at the midpoint'),fmt(Math.hypot(ex,ey))],[L('시험 전하 위치','test charge'),'('+fmt(s.x)+', '+fmt(s.y)+')']];},
      graph:{label:L('시험 전하의 속력','test charge speed'),y:s=>Math.hypot(s.vx,s.vy)},
      draw(g,s,p,w,h){
        const sc=Math.min(w/5.4,h/3.4),ox=w/2,oy=h/2;
        for(let gx=-2.5;gx<=2.5;gx+=0.25)for(let gy=-1.5;gy<=1.5;gy+=0.25){
          const [ex,ey]=this.field(p,gx,gy),m=Math.hypot(ex,ey);if(!m)continue;
          const len=Math.min(14,4+Math.log1p(m)*4),ux=ex/m,uy=ey/m,X=ox+gx*sc,Y=oy-gy*sc;
          g.strokeStyle=`rgba(112,89,164,${Math.min(0.9,0.15+Math.log1p(m)/3)})`;g.beginPath();g.moveTo(X-ux*len/2,Y+uy*len/2);g.lineTo(X+ux*len/2,Y-uy*len/2);g.stroke();
          g.beginPath();g.arc(X+ux*len/2,Y-uy*len/2,1.6,0,2*Math.PI);g.fillStyle=g.strokeStyle;g.fill();
        }
        for(const [q,cx] of [[p.q1,-1],[p.q2,1]]){if(!q)continue;g.fillStyle=q>0?'#d9622b':'#2b7bb9';g.beginPath();g.arc(ox+cx*sc,oy,8+Math.abs(q)*3,0,2*Math.PI);g.fill();g.fillStyle='#fff';g.font='bold 14px system-ui';g.textAlign='center';g.fillText(q>0?'+':'−',ox+cx*sc,oy+5);g.textAlign='start';}
        g.fillStyle=css('--ink');g.beginPath();g.arc(ox+s.x*sc,oy-s.y*sc,4,0,2*Math.PI);g.fill();
      },
      quiz:{q:L('크기와 부호가 같은 두 전하 사이의 한가운데에서 전기장의 세기는?','Midway between two equal charges of the same sign, the field is…'),
        choices:L(['0이다','한 전하만 있을 때의 2배다','한 전하만 있을 때와 같다','무한히 크다'],['zero','twice that of one charge','the same as one charge','infinite']),a:0,
        why:L('가운데에서 두 전하가 만드는 전기장은 크기가 같고 방향이 반대라 상쇄됩니다. q₁ = q₂로 맞추고 "가운데 점의 전기장"을 보세요.','At the midpoint the two fields are equal and opposite, so they cancel. Set q₁ = q₂ and read the midpoint field.')}}
  ];

  /* ── page ── */
  const copy={ko:{title:'개념 시뮬레이션',play:'재생',pause:'일시 정지',reset:'처음부터',check:'확인 문제',right:'정답입니다.',wrong:'다시 생각해 보세요.',practice:'이 단원 문제 풀기 →',all:'올림피아드 실험 시뮬레이터 →',
      note:'움직임은 모두 운동 방정식을 수치 적분해 계산합니다. 값을 바꾸면 처음부터 다시 시작합니다.'},
    en:{title:'Concept simulations',play:'Play',pause:'Pause',reset:'Restart',check:'Check yourself',right:'Correct.',wrong:'Think again.',practice:'Practise this unit →',all:'Olympiad experiment simulators →',
      note:'Every motion is computed by integrating its equations. Changing a value restarts the run.'}};
  window.HL_PAGE_COPY=copy;   /* the strings, for the translation catalogue (tools/i18n) */
  const t=k=>copy[state.lang]?.[k]??tx(copy.en[k]);
  function reportHeight(){if(embedded)requestAnimationFrame(()=>window.parent.postMessage({type:'hl-concepts-height',height:Math.ceil(document.documentElement.scrollHeight)},location.origin));}
  function list(){
    $('list').innerHTML=SIMS.map(sim=>`<li><button type="button" data-id="${sim.id}" aria-current="${sim===state.sim}">${esc(tr(sim.title))}</button></li>`).join('');
  }
  function choose(id,{push=true}={}){
    const sim=SIMS.find(s=>s.id===id)||SIMS[0];state.sim=sim;state.p={};for(const q of sim.params)state.p[q.k]=q.v;state.answered=false;
    if(push&&embedded)window.parent.postMessage({type:'hl-concepts-sim',sim:sim.id},location.origin);
    list();
    const choices=Array.isArray(sim.quiz.choices)?sim.quiz.choices:tr(sim.quiz.choices);
    $('sim').innerHTML=`<h2>${esc(tr(sim.title))}</h2><p class="intro">${esc(tr(sim.intro))}</p>
      <div class="stage"><canvas id="cv" aria-label="${esc(tr(sim.title))}"></canvas>
      <div class="side"><div class="controls">${sim.params.map(q=>`<label>${esc(tr(q.l))} <b id="pv-${q.k}">${state.p[q.k]}</b> ${q.u}<input type="range" min="${q.min}" max="${q.max}" step="${q.step}" value="${q.v}" data-k="${q.k}"></label>`).join('')}</div>
        <div class="buttons"><button type="button" id="play" class="primary">${t('pause')}</button><button type="button" id="reset">${t('reset')}</button>${sim.action?`<button type="button" id="act">${esc(tr(sim.action))}</button>`:''}</div>
        <dl class="read" id="read"></dl></div></div>
      <div class="graph"><span class="glabel">${esc(tr(sim.graph.label))} — t</span><canvas id="gcv"></canvas></div>
      <section class="quiz"><h3>${t('check')}</h3><p>${esc(tr(sim.quiz.q))}</p><div class="qchoices">${choices.map((c,i)=>`<button type="button" data-i="${i}">${esc(c)}</button>`).join('')}</div><p id="why" class="why" hidden></p>
      <a class="more" href="#" id="toPractice" data-unit="${sim.unit}">${t('practice')}</a></section>`;
    $('sim').querySelectorAll('input[type=range]').forEach(r=>r.addEventListener('input',()=>{state.p[r.dataset.k]=Number(r.value);$('pv-'+r.dataset.k).textContent=r.value;restart();}));
    $('play').onclick=()=>{state.running=!state.running;$('play').textContent=state.running?t('pause'):t('play');};
    $('reset').onclick=restart;if($('act'))$('act').onclick=()=>sim.onAction?.(state.s);
    $('sim').querySelectorAll('.qchoices button').forEach(b=>b.addEventListener('click',()=>{
      const ok=Number(b.dataset.i)===sim.quiz.a;b.classList.add(ok?'right':'wrong');if(ok){$('sim').querySelectorAll('.qchoices button').forEach(x=>x.disabled=true);}
      $('why').hidden=false;$('why').textContent=(ok?t('right')+' ':t('wrong')+' ')+(ok?tr(sim.quiz.why):'');reportHeight();
    }));
    $('toPractice').onclick=e=>{e.preventDefault();if(embedded)window.parent.postMessage({type:'hl-concepts-practice',unit:sim.unit},location.origin);else location.href='practice.html?unit='+encodeURIComponent(sim.unit);};
    restart();reportHeight();
  }
  function restart(){state.s=state.sim.init(state.p);state.graph=[];state.running=true;if($('play'))$('play').textContent=t('pause');}
  function size(cv){const dpr=Math.min(devicePixelRatio||1,2),w=cv.clientWidth,h=cv.clientHeight;if(cv.width!==Math.round(w*dpr)){cv.width=Math.round(w*dpr);cv.height=Math.round(h*dpr);}const g=cv.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,w,h);return[g,w,h];}
  function frame(now){
    const sim=state.sim,s=state.s;
    if(sim&&s){
      const dt=Math.min(0.05,(now-(state.last||now))/1000);state.last=now;
      if(state.running&&!s.done){const n=Math.max(1,Math.ceil(dt/0.002));for(let i=0;i<n;i++)sim.step.call(sim,s,state.p,dt/n);state.graph.push([s.t,sim.graph.y(s,state.p)]);if(state.graph.length>2000)state.graph.shift();}
      const cv=$('cv');if(cv){const [g,w,h]=size(cv);sim.draw.call(sim,g,s,state.p,w,h);}
      $('read').innerHTML=sim.readouts(s,state.p).map(([k,v])=>`<dt>${esc(tr(k))}</dt><dd>${esc(v)}</dd>`).join('');
      const gc=$('gcv');if(gc){const [g,w,h]=size(gc);const pts=state.graph;if(pts.length>1){
        const t0=pts[0][0],t1=Math.max(pts.at(-1)[0],t0+1e-6),ys=pts.map(p=>p[1]),y0=Math.min(0,...ys),y1=Math.max(...ys,y0+1e-6);
        g.strokeStyle=css('--line');g.strokeRect(0.5,0.5,w-1,h-1);g.strokeStyle=css('--s1');g.lineWidth=2;g.beginPath();
        pts.forEach(([x,y],i)=>{const X=4+(x-t0)/(t1-t0)*(w-8),Y=h-4-(y-y0)/(y1-y0)*(h-8);i?g.lineTo(X,Y):g.moveTo(X,Y);});g.stroke();
        g.fillStyle=css('--muted');g.font='11px system-ui';g.fillText(fmt(y1),6,13);g.fillText(fmt(y0),6,h-6);}}
    }else state.last=now;
    requestAnimationFrame(frame);
  }
  function applyTheme(){const th=params.get('theme'),dark=th==='dark'||(th!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.dataset.theme=dark?'dark':'light';}
  function translate(){document.documentElement.lang=state.lang;document.querySelectorAll('[data-i18n]').forEach(el=>{el.textContent=t(el.dataset.i18n);});$('note').textContent=t('note');document.title=t('title')+' · HaslaLab';
    const a=$('olympiadSims');a.textContent=t('all');a.href=state.lang==='ko'?'problems.html':'problems-en.html';}
  $('list').addEventListener('click',e=>{const b=e.target.closest('button[data-id]');if(b)choose(b.dataset.id);});
  window.addEventListener('message',event=>{
    if(!embedded||event.origin!==location.origin||event.source!==window.parent||event.data?.type!=='hl-concepts-settings')return;
    if(['light','dark'].includes(event.data.theme))document.documentElement.dataset.theme=event.data.theme;
    if(LANGS.includes(event.data.lang)&&event.data.lang!==state.lang){state.lang=event.data.lang;translate();choose(state.sim.id,{push:false});}
  });
  if(typeof ResizeObserver==='function')new ResizeObserver(reportHeight).observe(document.body);
  document.documentElement.classList.toggle('embedded',embedded);
  applyTheme();translate();choose(params.get('sim')||SIMS[0].id,{push:false});requestAnimationFrame(frame);
  window.HL_CONCEPT_SIMS=SIMS;   /* for tests */
})();
