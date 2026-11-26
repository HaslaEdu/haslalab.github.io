/* Synthetic hand-drawn strokes for tests/test-draw-ink.cjs: the ideal path of a shape, resampled as a 120 Hz digitiser
   would at ~700 px/s, with a slow wobble (a low-passed random walk) and jitter, in the editor's world (metres, y up) at
   100 px per metre (unit 0.01), pressure varying. Seeded, so every run draws the same strokes. */
const U=0.01;
function rng(seed){let a=seed>>>0;return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
/* a path (dense points, world) → a stroke: time at ~700 px/s, wobble (low-pass random walk) + jitter, pressure */
function hand(path,{seed=1,wobble=1.6,jitter=0.4,speed=700,t0=0}={}){
  const R=rng(seed),out=[];let wx=0,wy=0,vx=0,vy=0,t=t0;
  /* resample the path every ~6 px (a 120 Hz digitiser at 700 px/s) */
  const step=speed/120*U;const pts=[path[0]];let acc=0;
  for(let i=1;i<path.length;i++){let a=pts[pts.length-1],b=path[i],d=Math.hypot(b.x-a.x,b.y-a.y);while(acc+d>=step){const k=(step-acc)/d;a={x:a.x+(b.x-a.x)*k,y:a.y+(b.y-a.y)*k};pts.push(a);d=Math.hypot(b.x-a.x,b.y-a.y);acc=0;}acc+=d;}
  pts.push(path[path.length-1]);
  for(const p of pts){vx=0.85*vx+(R()-0.5)*0.6;vy=0.85*vy+(R()-0.5)*0.6;wx=0.9*wx+vx;wy=0.9*wy+vy;const s=wobble/4;
    out.push({x:p.x+(wx*s+(R()-0.5)*jitter)*U,y:p.y+(wy*s+(R()-0.5)*jitter)*U,t:t,pressure:0.4+0.3*R()});t+=1000/120;}
  return {points:out,pointerType:'pen'};
}
const seg=(a,b,n=40)=>Array.from({length:n+1},(_,i)=>({x:a.x+(b.x-a.x)*i/n,y:a.y+(b.y-a.y)*i/n}));
const chain=(...ps)=>{const out=[];for(let i=1;i<ps.length;i++)out.push(...seg(ps[i-1],ps[i]).slice(i>1?1:0));return out;};
const line=(x,y,len,deg)=>seg({x,y},{x:x+len*Math.cos(deg*Math.PI/180),y:y+len*Math.sin(deg*Math.PI/180)});
const ellipse=(cx,cy,rx,ry,rot=0,{start=0.3,over=0.04}={})=>{const out=[],N=120,c=Math.cos(rot*Math.PI/180),s=Math.sin(rot*Math.PI/180);for(let i=0;i<=N*(1+over);i++){const t=start+2*Math.PI*i/N,u=rx*Math.cos(t),v=ry*Math.sin(t);out.push({x:cx+u*c-v*s,y:cy+u*s+v*c});}return out;};
const rect=(cx,cy,w,h,rot=0)=>{const c=Math.cos(rot*Math.PI/180),s=Math.sin(rot*Math.PI/180),P=(u,v)=>({x:cx+u*c-v*s,y:cy+u*s+v*c});return chain(P(-w/2,-h/2),P(w/2,-h/2),P(w/2,h/2),P(-w/2,h/2),P(-w/2,-h/2*0.92));};
const tri=(a,b,c)=>chain(a,b,c,a,{x:a.x+(b.x-a.x)*0.03,y:a.y+(b.y-a.y)*0.03});
const zig=(a,b,teeth,amp,lead=0.12)=>{const L=Math.hypot(b.x-a.x,b.y-a.y),u={x:(b.x-a.x)/L,y:(b.y-a.y)/L},n={x:-u.y,y:u.x},ps=[a];const l0=L*lead,body=L-2*l0;ps.push({x:a.x+u.x*l0,y:a.y+u.y*l0});for(let i=0;i<teeth;i++){const t=l0+body*(i+0.5)/teeth,s=i%2?-1:1;ps.push({x:a.x+u.x*t+n.x*amp*s,y:a.y+u.y*t+n.y*amp*s});}ps.push({x:b.x-u.x*l0,y:b.y-u.y*l0},b);return chain(...ps);};
const coil=(a,b,n,amp)=>{const L=Math.hypot(b.x-a.x,b.y-a.y),u={x:(b.x-a.x)/L,y:(b.y-a.y)/L},nv={x:-u.y,y:u.x},out=[],N=n*40,pitch=L/(n+0.6);for(let i=0;i<=N;i++){const s=i/N*n*2*Math.PI,al=pitch*s/(2*Math.PI)+pitch*0.3*(1-Math.cos(s)),ac=amp*Math.sin(s);out.push({x:a.x+u.x*al+nv.x*ac,y:a.y+u.y*al+nv.y*ac});}return out;};
const sine=(x,y,len,A,lambda,ph=0)=>Array.from({length:301},(_,i)=>{const t=len*i/300;return{x:x+t,y:y+A*Math.sin(2*Math.PI*t/lambda+ph)};});
const arc=(cx,cy,r,from,to)=>Array.from({length:81},(_,i)=>{const t=(from+(to-from)*i/80)*Math.PI/180;return{x:cx+r*Math.cos(t),y:cy+r*Math.sin(t)};});
const scribble=seed=>{const R=rng(seed),out=[];let x=1,y=1,a=0;for(let i=0;i<160;i++){a+=(R()-0.5)*1.6;x+=Math.cos(a)*0.04;y+=Math.sin(a)*0.04;out.push({x,y});}return out;};
module.exports={U,rng,hand,seg,chain,line,ellipse,rect,tri,zig,coil,sine,arc,scribble};
