/* HaslaLab 3-D bench (sim/bench3d.js): the LAB3D renderer of the 3-D sims (IPhO 2017, APhO 2023–2025,
   IPhO 2026) made into one shared file, with a bench around it — a desk seen in 3-D, apparatus moved by
   hand, instrument fronts that are worked with the HaslaLab panel widgets (needs sim/handlab.js first). */
(function () {
"use strict";
const CAM={yaw:-0.62, pitch:0.62, k:6, tx:40, ty:8, tz:0, px:0, py:0, W:1000, H:600, dpr:1};
const CAM0={};
function camSave(){ Object.assign(CAM0,{yaw:CAM.yaw,pitch:CAM.pitch,k:CAM.k,tx:CAM.tx,ty:CAM.ty,tz:CAM.tz,px:CAM.px,py:CAM.py}); }
function camReset(){ Object.assign(CAM,CAM0); }
/* world → [screen x, screen y, depth]; larger depth is nearer the eye */
function P3(x,y,z){
  const c=Math.cos(CAM.yaw), s=Math.sin(CAM.yaw), cp=Math.cos(CAM.pitch), sp=Math.sin(CAM.pitch);
  const dx=x-CAM.tx, dy=y-CAM.ty, dz=z-CAM.tz;
  const xr=dx*c-dz*s, zr=dx*s+dz*c;
  const up=dy*cp-zr*sp, dep=dy*sp+zr*cp;
  const sx=CAM.W/2+CAM.px+xr*CAM.k, sy=CAM.H/2+CAM.py-up*CAM.k;
  if(_REC) _REC.set(sx+","+sy,dep);
  return [sx, sy, dep];
}
/* screen point → world point on the horizontal plane y = h */
function onPlane(px,py,h){
  const c=Math.cos(CAM.yaw), s=Math.sin(CAM.yaw), cp=Math.cos(CAM.pitch), sp=Math.sin(CAM.pitch);
  const xr=(px-CAM.W/2-CAM.px)/CAM.k, up=-(py-CAM.H/2-CAM.py)/CAM.k;
  const zr=((h-CAM.ty)*cp-up)/sp;
  return [CAM.tx+xr*c+zr*s, h, CAM.tz-xr*s+zr*c];
}
/* screen point → world point on the vertical plane x = x0 (for things mounted on a rail) */
function onPlaneX(px,py,x0){
  const c=Math.cos(CAM.yaw), s=Math.sin(CAM.yaw), cp=Math.cos(CAM.pitch), sp=Math.sin(CAM.pitch);
  const xr=(px-CAM.W/2-CAM.px)/CAM.k, up=-(py-CAM.H/2-CAM.py)/CAM.k;
  /* unknowns dz, dy with dx fixed: xr = dx c - dz s ; up = dy cp - (dx s + dz c) sp */
  const dx=x0-CAM.tx; if(Math.abs(s)<1e-4) return null;
  const dz=(dx*c-xr)/s, dy=(up+(dx*s+dz*c)*sp)/cp;
  return [x0, CAM.ty+dy, CAM.tz+dz];
}
function hex2rgb(h){ h=h.replace("#",""); if(h.length===3) h=h.split("").map(c=>c+c).join("");
  return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)]; }
const _shadeCache=new Map();
function shade(col,f){
  const key=col+"|"+f.toFixed(2); let v=_shadeCache.get(key); if(v) return v;
  let a=1, rgb;
  if(col.startsWith("rgba")){ const m=col.match(/[\d.]+/g).map(Number); rgb=m.slice(0,3); a=m[3]; } else rgb=hex2rgb(col);
  const r=rgb.map(c=>Math.max(0,Math.min(255,Math.round(c*f))));
  v=a<1?`rgba(${r[0]},${r[1]},${r[2]},${a})`:`rgb(${r[0]},${r[1]},${r[2]})`;
  _shadeCache.set(key,v); return v;
}
const LIGHT=(()=>{ const v=[-0.45,0.85,0.35], n=Math.hypot(...v); return v.map(a=>a/n); })();
let ITEMS=[], HITS=[], _REC=null;
function begin3(){ ITEMS=[]; }
function _cross(a,b){ return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]; }
function _sub(a,b){ return [a[0]-b[0],a[1]-b[1],a[2]-b[2]]; }
/* a flat polygon; o = {fill, stroke, lw, id, layer, cull, flat, bias, alpha} */
function face(pts,o){
  o=o||{};
  const n=_cross(_sub(pts[1],pts[0]),_sub(pts[2],pts[0])), nl=Math.hypot(...n)||1;
  const nn=n.map(a=>a/nl);
  const lum=o.flat?1:0.62+0.48*Math.max(0,nn[0]*LIGHT[0]+nn[1]*LIGHT[1]+nn[2]*LIGHT[2]);
  ITEMS.push({t:"f",p:pts,o,lum,n:nn});
}
function quad(a,b,c,d,o){ face([a,b,c,d],o); }
/* axis-aligned box, outward faces culled when they point away */
function box3(x0,x1,y0,y1,z0,z1,col,o){
  o=Object.assign({cull:true},o||{}); const f=Object.assign({},o,{fill:col});
  const t=o.top?Object.assign({},f,{fill:o.top}):f;
  if(!o.noTop) face([[x0,y1,z0],[x0,y1,z1],[x1,y1,z1],[x1,y1,z0]],t);          /* top    +y */
  if(!o.noBot) face([[x0,y0,z0],[x1,y0,z0],[x1,y0,z1],[x0,y0,z1]],f);          /* bottom -y */
  face([[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]],f);          /* +z */
  face([[x0,y0,z0],[x0,y1,z0],[x1,y1,z0],[x1,y0,z0]],f);          /* -z */
  face([[x1,y0,z0],[x1,y1,z0],[x1,y1,z1],[x1,y0,z1]],f);          /* +x */
  face([[x0,y0,z0],[x0,y0,z1],[x0,y1,z1],[x0,y1,z0]],f);          /* -x */
}
/* make a polygon face the direction `want` (a world vector) */
function orient(pts,want){
  const n=_cross(_sub(pts[1],pts[0]),_sub(pts[2],pts[0]));
  return (n[0]*want[0]+n[1]*want[1]+n[2]*want[2])<0?pts.slice().reverse():pts;
}
/* cylinder (or cone, with o.r1) along an axis ("x","y","z") from a0 to a1, centre (u,v) across it */
function cyl3(axis,a0,a1,u,v,r,col,o){
  o=Object.assign({cull:true,seg:18},o||{}); const N=o.seg, f=Object.assign({},o,{fill:col});
  const r1=o.r1===undefined?r:o.r1;
  const W=(a,cu,cv)=>axis==="x"?[a,cu,cv]:axis==="y"?[cu,a,cv]:[cu,cv,a];
  const pt=(a,rr,ang)=>W(a,u+rr*Math.cos(ang),v+rr*Math.sin(ang));
  const ax=W(1,0,0).map((c,i)=>c-W(0,0,0)[i]), sg=a1>=a0?1:-1;
  for(let i=0;i<N;i++){
    const t0=i/N*2*Math.PI, t1=(i+1)/N*2*Math.PI, tm=(t0+t1)/2;
    const q=[pt(a0,r,t0),pt(a0,r,t1),pt(a1,r1,t1),pt(a1,r1,t0)];
    const rad=_sub(pt(a0,1,tm),pt(a0,0,tm));
    face(orient(q,rad),Object.assign({},f,{smooth:true}));
  }
  if(o.caps!==false){
    const c0=[],c1=[]; for(let i=0;i<N;i++){ const t=i/N*2*Math.PI; c0.push(pt(a0,r,t)); c1.push(pt(a1,r1,t)); }
    const cf=Object.assign({},f,o.cap?{fill:o.cap}:{},{stroke:o.capStroke});
    if(r>0.001&&o.cap0!==false) face(orient(c0,ax.map(c=>-c*sg)),cf);
    if(r1>0.001&&o.cap1!==false) face(orient(c1,ax.map(c=>c*sg)),cf);
  }
}
/* a prism: polygon pts2 [[u,v]..] in the plane across `axis`, extruded from a0 to a1 */
function prism3(axis,a0,a1,pts2,col,o){
  o=Object.assign({cull:true},o||{}); const f=Object.assign({},o,{fill:col});
  const P=(a,[u,v])=>axis==="x"?[a,u,v]:axis==="y"?[u,a,v]:[u,v,a];
  const n=pts2.length, A=pts2.map(p=>P(a0,p)), B=pts2.map(p=>P(a1,p));
  const ax=_sub(P(1,[0,0]),P(0,[0,0])), sg=a1>=a0?1:-1;
  let cu=0,cvv=0; for(const [x,y] of pts2){ cu+=x; cvv+=y; } cu/=n; cvv/=n;
  face(orient(A,ax.map(c=>-c*sg)),f); face(orient(B,ax.map(c=>c*sg)),f);
  for(let i=0;i<n;i++){ const j=(i+1)%n; const q=[A[i],A[j],B[j],B[i]];
    const mid=[(pts2[i][0]+pts2[j][0])/2-cu,(pts2[i][1]+pts2[j][1])/2-cvv];
    face(orient(q,_sub(P(0,mid),P(0,[0,0]))),f); }
}
/* tall parts cut into short slices, so each slice is sorted at its own height
   (one long face sorted by its centre is what makes posts jump in front of things) */
function boxY(x0,x1,y0,y1,z0,z1,col,o,step){ const n=Math.max(1,Math.ceil((y1-y0)/(step||1)));
  for(let i=0;i<n;i++) box3(x0,x1,y0+(y1-y0)*i/n,y0+(y1-y0)*(i+1)/n,z0,z1,col,Object.assign({},o,{noTop:i<n-1,noBot:i>0})); }
function cylSeg(axis,a0,a1,u,v,r,col,o,step){ const n=Math.max(1,Math.ceil(Math.abs(a1-a0)/(step||1)));
  for(let i=0;i<n;i++) cyl3(axis,a0+(a1-a0)*i/n,a0+(a1-a0)*(i+1)/n,u,v,r,col,Object.assign({},o,{cap0:i===0&&(o||{}).cap0!==false,cap1:i===n-1&&(o||{}).cap1!==false})); }
function line3(a,b,col,lw,o){ ITEMS.push({t:"l",p:[a,b],o:Object.assign({col,lw:lw||1},o||{})}); }
function poly3(pts,col,lw,o){ ITEMS.push({t:"pl",p:pts,o:Object.assign({col,lw:lw||1},o||{})}); }
/* text lying in the plane spanned by U (right) and V (up), size in cm */
function text3(O,U,V,str,size,col,o){ ITEMS.push({t:"x",p:[O],O,U,V,str,size,o:Object.assign({col},o||{})}); }
/* anything else: draw(ctx) is called in its depth order; ref is a world point */
function custom3(ref,draw,o){ ITEMS.push({t:"c",p:[ref],draw,o:o||{}}); }

function render3_2d(ctx){
  const vis=[];
  for(const it of ITEMS){
    const q=it.p.map(p=>P3(p[0],p[1],p[2]));
    let dep=0; for(const v of q) dep+=v[2]; dep/=q.length;
    if(it.t==="f"&&it.o.cull){
      let a=0; for(let i=0;i<q.length;i++){ const j=(i+1)%q.length; a+=q[i][0]*q[j][1]-q[j][0]*q[i][1]; }
      if(a>=0) continue;                                  /* facing away */
    }
    vis.push({it,q,dep:dep+(it.o.bias||0),layer:it.o.layer||0});
  }
  vis.sort((a,b)=>a.layer-b.layer||a.dep-b.dep);
  HITS=[];
  for(const v of vis){
    const it=v.it, o=it.o, q=v.q;
    if(it.t==="f"){
      ctx.beginPath(); ctx.moveTo(q[0][0],q[0][1]); for(let i=1;i<q.length;i++) ctx.lineTo(q[i][0],q[i][1]); ctx.closePath();
      if(o.fill){ if(o.alpha!==undefined) ctx.globalAlpha=o.alpha; ctx.fillStyle=o.flat?o.fill:shade(o.fill,it.lum); ctx.fill(); ctx.globalAlpha=1; }
      if(o.stroke){ ctx.strokeStyle=o.stroke; ctx.lineWidth=o.lw||0.8; ctx.lineJoin="round"; ctx.stroke(); }
      else if(o.fill&&o.alpha===undefined){ ctx.strokeStyle=ctx.fillStyle; ctx.lineWidth=0.6; ctx.stroke(); }
      if(o.id) HITS.push([o.id,q]);
    }else if(it.t==="l"||it.t==="pl"){
      ctx.beginPath(); ctx.moveTo(q[0][0],q[0][1]); for(let i=1;i<q.length;i++) ctx.lineTo(q[i][0],q[i][1]);
      ctx.strokeStyle=o.col; ctx.lineWidth=o.lw; ctx.lineCap=o.cap||"round"; ctx.lineJoin="round";
      if(o.alpha!==undefined) ctx.globalAlpha=o.alpha; ctx.stroke(); ctx.globalAlpha=1;
    }else if(it.t==="x"){
      const O=q[0], pu=P3(it.O[0]+it.U[0],it.O[1]+it.U[1],it.O[2]+it.U[2]), pv=P3(it.O[0]+it.V[0],it.O[1]+it.V[1],it.O[2]+it.V[2]);
      const a=[pu[0]-O[0],pu[1]-O[1]], b=[pv[0]-O[0],pv[1]-O[1]];
      if(a[0]*b[1]-a[1]*b[0]>=0) continue;                 /* seen from behind */
      if(Math.hypot(...a)*it.size<2.2) continue;           /* too small to read */
      ctx.save(); ctx.transform(a[0],a[1],-b[0],-b[1],O[0],O[1]);
      ctx.font=(o.weight||"600")+" "+it.size+"px "+(o.font||"-apple-system,'Segoe UI','Malgun Gothic',sans-serif");
      ctx.textAlign=o.align||"left"; ctx.textBaseline=o.base||"middle"; ctx.fillStyle=o.col; ctx.fillText(it.str,0,0); ctx.restore();
    }else if(it.t==="c"){ ctx.save(); it.draw(ctx); ctx.restore(); }
  }
}
function pointIn(q,x,y){ let c=false; for(let i=0,j=q.length-1;i<q.length;j=i++){
  const xi=q[i][0], yi=q[i][1], xj=q[j][0], yj=q[j][1];
  if(((yi>y)!==(yj>y))&&(x<(xj-xi)*(y-yi)/(yj-yi)+xi)) c=!c; } return c; }
/* the id of the nearest object under a screen point */
function pick3_2d(x,y){ for(let i=HITS.length-1;i>=0;i--) if(pointIn(HITS[i][1],x,y)) return HITS[i][0]; return null; }
/* a sphere: a shaded disc in its depth order */
function sphere3_2d(c,r,col,o){ o=o||{};
  custom3(c,ctx=>{ const p=P3(...c), R=r*CAM.k;
    const g=ctx.createRadialGradient(p[0]-R*0.35,p[1]-R*0.4,R*0.08,p[0],p[1],R);
    g.addColorStop(0,o.hi||"#ffffff"); g.addColorStop(0.35,col); g.addColorStop(1,o.lo||"#5d646b");
    ctx.fillStyle=g; ctx.beginPath(); ctx.arc(p[0],p[1],R,0,7); ctx.fill();
    if(o.stroke){ ctx.strokeStyle=o.stroke; ctx.lineWidth=0.8; ctx.stroke(); }
    if(o.id) HITS.push([o.id,Array.from({length:12},(_,i)=>[p[0]+R*Math.cos(i/12*6.283),p[1]+R*Math.sin(i/12*6.283)])]);
  },{bias:o.bias||0,layer:o.layer||0});
}
/* a cylinder between two arbitrary points */
function cylAB(a,b,r,col,o){
  o=Object.assign({cull:true,seg:14},o||{}); const f=Object.assign({},o,{fill:col});
  const ax=_sub(b,a), L=Math.hypot(...ax), n=ax.map(v=>v/L);
  const t=Math.abs(n[1])<0.9?[0,1,0]:[1,0,0];
  let u=_cross(n,t); const ul=Math.hypot(...u); u=u.map(v=>v/ul); const v=_cross(n,u);
  const P=(base,ang)=>[base[0]+r*(u[0]*Math.cos(ang)+v[0]*Math.sin(ang)),base[1]+r*(u[1]*Math.cos(ang)+v[1]*Math.sin(ang)),base[2]+r*(u[2]*Math.cos(ang)+v[2]*Math.sin(ang))];
  const N=o.seg;
  for(let i=0;i<N;i++){ const t0=i/N*2*Math.PI, t1=(i+1)/N*2*Math.PI, tm=(t0+t1)/2;
    face(orient([P(a,t0),P(a,t1),P(b,t1),P(b,t0)],[u[0]*Math.cos(tm)+v[0]*Math.sin(tm),u[1]*Math.cos(tm)+v[1]*Math.sin(tm),u[2]*Math.cos(tm)+v[2]*Math.sin(tm)]),f); }
  if(o.caps!==false){ const c0=[],c1=[]; for(let i=0;i<N;i++){ const t=i/N*2*Math.PI; c0.push(P(a,t)); c1.push(P(b,t)); }
    const cf=Object.assign({},f,o.cap?{fill:o.cap}:{}); face(orient(c0,n.map(x=>-x)),cf); face(orient(c1,n),cf); }
}
/* a 2-D canvas (or a part of it) painted onto a flat rectangle: O is the world
   point of its top-left corner, U and V the world vectors along its width and down its height */
function tex3_2d(src,sx,sy,sw,sh,O,U,V,o){ o=o||{};
  const C=[O[0]+U[0]/2+V[0]/2,O[1]+U[1]/2+V[1]/2,O[2]+U[2]/2+V[2]/2];
  custom3(C,ctx=>{ const a=P3(...O), b=P3(O[0]+U[0],O[1]+U[1],O[2]+U[2]), c=P3(O[0]+V[0],O[1]+V[1],O[2]+V[2]);
    const ux=b[0]-a[0], uy=b[1]-a[1], vx=c[0]-a[0], vy=c[1]-a[1];
    if(ux*vy-uy*vx<=0) return;                                /* seen from behind */
    ctx.save(); ctx.transform(ux/sw,uy/sw,vx/sh,vy/sh,a[0],a[1]); ctx.imageSmoothingEnabled=true;
    try{ ctx.drawImage(src,sx,sy,sw,sh,0,0,sw,sh); }catch(e){}
    ctx.restore();
    if(o.id) HITS.push([o.id,[a,b,[b[0]+vx,b[1]+vy],c]]);
  },{bias:o.bias||0.3,layer:o.layer||0});
}

/* ══════════════════════════════════════════════════════════════
   WebGL back end — the same scene list drawn with a depth buffer,
   so parts can no longer show through one another from some angles
   (the 2-D painter above stays as the fallback without WebGL)
   ══════════════════════════════════════════════════════════════ */
function sphere3(c,r,col,o){ if(!gl3Init()) return sphere3_2d(c,r,col,o); ITEMS.push({t:"sp",p:[c],c,r,col,o:o||{}}); }
function tex3(src,sx,sy,sw,sh,O,U,V,o){ if(!gl3Init()) return tex3_2d(src,sx,sy,sw,sh,O,U,V,o);
  o=o||{}; ITEMS.push({t:"tx",p:[O],src,sx,sy,sw,sh,O,U,V,o}); }
const GL3={ok:null};
function gl3Init(){
  if(GL3.ok!==null) return GL3.ok;
  try{
    const c=document.createElement("canvas");
    const gl=c.getContext("webgl",{antialias:true,alpha:true,premultipliedAlpha:true,preserveDrawingBuffer:true,depth:true});
    if(!gl){ GL3.ok=false; return false; }
    c.addEventListener("webglcontextlost",e=>{ e.preventDefault(); GL3.ok=false; });
    const sh=(t,src)=>{ const o=gl.createShader(t); gl.shaderSource(o,src); gl.compileShader(o); if(!gl.getShaderParameter(o,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(o)); return o; };
    const prog=(vs,fs)=>{ const p=gl.createProgram(); gl.attachShader(p,sh(gl.VERTEX_SHADER,vs)); gl.attachShader(p,sh(gl.FRAGMENT_SHADER,fs)); gl.linkProgram(p);
      if(!gl.getProgramParameter(p,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p)); return p; };
    const pc=prog("attribute vec3 p;attribute vec4 c;varying vec4 v;void main(){gl_Position=vec4(p,1.0);v=c;}",
                  "precision mediump float;varying vec4 v;void main(){gl_FragColor=v;}");
    const pt=prog("attribute vec3 p;attribute vec2 t;varying vec2 u;void main(){gl_Position=vec4(p,1.0);u=t;}",
                  "precision mediump float;varying vec2 u;uniform sampler2D s;uniform float a;void main(){gl_FragColor=texture2D(s,u)*a;}");
    Object.assign(GL3,{ok:true,c,gl,pc,pt,pcP:gl.getAttribLocation(pc,"p"),pcC:gl.getAttribLocation(pc,"c"),
      ptP:gl.getAttribLocation(pt,"p"),ptT:gl.getAttribLocation(pt,"t"),ptS:gl.getUniformLocation(pt,"s"),ptA:gl.getUniformLocation(pt,"a"),
      buf:gl.createBuffer(),txt:new Map(),src:new Map(),frame:0});
  }catch(e){ GL3.ok=false; }
  return GL3.ok;
}
/* css colour → premultiplied-ready [r,g,b,a] in 0..1 */
const _rgbaCache=new Map(); let _parseCtx=null;
function rgba01(col){
  let v=_rgbaCache.get(col); if(v) return v;
  let m;
  if(col[0]==="#"){ const r=hex2rgb(col); v=[r[0]/255,r[1]/255,r[2]/255,1]; }
  else if((m=col.match(/^rgba?\(([^)]+)\)/))){ const a=m[1].split(",").map(Number); v=[a[0]/255,a[1]/255,a[2]/255,a.length>3?a[3]:1]; }
  else { if(!_parseCtx) _parseCtx=document.createElement("canvas").getContext("2d"); _parseCtx.fillStyle="#000"; _parseCtx.fillStyle=col;
    const f=_parseCtx.fillStyle; v=f[0]==="#"?rgba01(f):rgba01(f.replace(/\s/g,"")); }
  if(_rgbaCache.size>4000) _rgbaCache.clear(); _rgbaCache.set(col,v); return v;
}
/* the per-frame geometry: opaque triangles, then see-through pieces sorted far to near */
function _G(){ return {op:[],tq:[],tr:[],dmin:Infinity,dmax:-Infinity}; }
function _gd(G,d){ if(d<G.dmin) G.dmin=d; if(d>G.dmax) G.dmax=d; }
function _gtri(G,vs,col,alpha,dep){            /* vs: [[x,y,d],...] a fan */
  const c=rgba01(col), a=c[3]*(alpha===undefined?1:alpha); if(a<=0.003) return;
  const out=[]; for(let i=1;i+1<vs.length;i++) for(const v of [vs[0],vs[i],vs[i+1]]){ _gd(G,v[2]); out.push(v[0],v[1],v[2],c[0]*a,c[1]*a,c[2]*a,a); }
  if(a>0.995) for(const x of out) G.op.push(x);
  else G.tr.push({dep:dep===undefined?vs.reduce((s,v)=>s+v[2],0)/vs.length:dep,col:out});
}
function _gline(G,a,b,w,col,alpha,cap){
  const dx=b[0]-a[0], dy=b[1]-a[1], L=Math.hypot(dx,dy); if(L<1e-6) return;
  const h=Math.max(0.5,w)/2, ux=dx/L, uy=dy/L, nx=-uy*h, ny=ux*h, e=cap==="butt"?0:h;
  const A=[a[0]-ux*e,a[1]-uy*e,a[2]], B=[b[0]+ux*e,b[1]+uy*e,b[2]];
  _gtri(G,[[A[0]+nx,A[1]+ny,A[2]],[B[0]+nx,B[1]+ny,B[2]],[B[0]-nx,B[1]-ny,B[2]],[A[0]-nx,A[1]-ny,A[2]]],col,alpha);
}
/* a stand-in 2-D context: custom3 drawings are recorded as lines and fills that keep
   the depth of every point they took from P3 */
class Rec3{
  constructor(G,d0,e){ this.G=G; this.d0=d0; this.e=e; this.path=[]; this.cur=null; this.strokeStyle="#000"; this.fillStyle="#000";
    this.lineWidth=1; this.globalAlpha=1; this.lineCap="butt"; this.lineJoin="miter"; this.font="10px sans-serif"; this.textAlign="left"; this.textBaseline="alphabetic"; }
  _d(x,y){ const v=_REC&&_REC.get(x+","+y); return (v===undefined?this.d0:v)+this.e; }
  beginPath(){ this.path=[]; this.cur=null; }
  moveTo(x,y){ this.cur=[[x,y,this._d(x,y)]]; this.path.push(this.cur); }
  lineTo(x,y){ if(!this.cur) return this.moveTo(x,y); this.cur.push([x,y,this._d(x,y)]); }
  closePath(){ if(this.cur&&this.cur.length>1) this.cur.push(this.cur[0]); }
  rect(x,y,w,h){ this.moveTo(x,y); this.lineTo(x+w,y); this.lineTo(x+w,y+h); this.lineTo(x,y+h); this.closePath(); }
  arc(x,y,r,a0,a1){ const n=20; for(let i=0;i<=n;i++){ const a=a0+(a1-a0)*i/n, px=x+r*Math.cos(a), py=y+r*Math.sin(a); if(i===0&&!this.cur) this.moveTo(px,py); else this.lineTo(px,py); } }
  stroke(){ const st=typeof this.strokeStyle==="string"?this.strokeStyle:"#000";
    for(const s of this.path) for(let i=1;i<s.length;i++) _gline(this.G,s[i-1],s[i],this.lineWidth,st,this.globalAlpha,this.lineCap); }
  fill(){ const st=typeof this.fillStyle==="string"?this.fillStyle:"#888"; for(const s of this.path) if(s.length>=3) _gtri(this.G,s,st,this.globalAlpha); }
  fillRect(x,y,w,h){ this.beginPath(); this.rect(x,y,w,h); this.fill(); }
  strokeRect(x,y,w,h){ this.beginPath(); this.rect(x,y,w,h); this.stroke(); }
  save(){} restore(){} setLineDash(){} fillText(){} strokeText(){} clip(){} drawImage(){} translate(){} scale(){} rotate(){} setTransform(){} transform(){}
  measureText(){ return {width:0}; } createLinearGradient(){ return {addColorStop(){}}; } createRadialGradient(){ return {addColorStop(){}}; }
}
function _textTex(str,o){
  const key=str+"|"+(o.weight||"600")+"|"+(o.font||"")+"|"+o.col;
  let t=GL3.txt.get(key); if(t) return t;
  const F=48, c=document.createElement("canvas"), x=c.getContext("2d"), font=(o.weight||"600")+" "+F+"px "+(o.font||"-apple-system,'Segoe UI','Malgun Gothic',sans-serif");
  x.font=font; const w=Math.ceil(x.measureText(str).width);
  c.width=Math.max(4,w+8); c.height=Math.ceil(F*1.5);
  x.font=font; x.textBaseline="middle"; x.fillStyle=o.col; x.fillText(str,4,c.height/2);
  const gl=GL3.gl, tex=gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D,tex);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,true); gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,c);
  for(const [k,v] of [[gl.TEXTURE_MIN_FILTER,gl.LINEAR],[gl.TEXTURE_MAG_FILTER,gl.LINEAR],[gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE],[gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D,k,v);
  t={tex,F,w,cw:c.width,ch:c.height};
  if(GL3.txt.size>600){ for(const v of GL3.txt.values()) gl.deleteTexture(v.tex); GL3.txt.clear(); }
  GL3.txt.set(key,t); return t;
}
function _srcTex(src){
  const gl=GL3.gl; let t=GL3.src.get(src);
  if(!t){ t={tex:gl.createTexture(),frame:-1}; GL3.src.set(src,t); gl.bindTexture(gl.TEXTURE_2D,t.tex);
    for(const [k,v] of [[gl.TEXTURE_MIN_FILTER,gl.LINEAR],[gl.TEXTURE_MAG_FILTER,gl.LINEAR],[gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE],[gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D,k,v); }
  if(t.frame!==GL3.frame&&!(src._static&&t.frame>=0)){ t.frame=GL3.frame; gl.bindTexture(gl.TEXTURE_2D,t.tex); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,true);
    try{ gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,src); }catch(e){} }
  return t;
}
function render3(ctx){
  if(!gl3Init()) return render3_2d(ctx);
  const G=_G(), W=CAM.W, H=CAM.H; HITS=[]; GL3.frame++;
  const eff=o=>0.004*(o.bias||0)+0.02*(o.layer||0);
  for(const it of ITEMS){
    const o=it.o, e=eff(o);
    if(it.t==="f"){
      const q=it.p.map(p=>P3(p[0],p[1],p[2]));
      if(o.cull){ let a=0; for(let i=0;i<q.length;i++){ const j=(i+1)%q.length; a+=q[i][0]*q[j][1]-q[j][0]*q[i][1]; } if(a>=0) continue; }
      const vs=q.map(v=>[v[0],v[1],v[2]+e]);
      if(o.fill) _gtri(G,vs,o.flat?o.fill:shade(o.fill,it.lum),o.alpha);
      if(o.stroke) for(let i=0;i<vs.length;i++) _gline(G,vs[i],vs[(i+1)%vs.length],o.lw||0.8,o.stroke,undefined,"round");
      if(o.id) HITS.push([o.id,vs]);
    }else if(it.t==="l"||it.t==="pl"){
      const vs=it.p.map(p=>{ const v=P3(p[0],p[1],p[2]); return [v[0],v[1],v[2]+e]; });
      for(let i=1;i<vs.length;i++) _gline(G,vs[i-1],vs[i],o.lw,o.col,o.alpha,o.cap||"round");
    }else if(it.t==="x"){
      const O=P3(...it.O), pu=P3(it.O[0]+it.U[0],it.O[1]+it.U[1],it.O[2]+it.U[2]), pv=P3(it.O[0]+it.V[0],it.O[1]+it.V[1],it.O[2]+it.V[2]);
      const a=[pu[0]-O[0],pu[1]-O[1]], b=[pv[0]-O[0],pv[1]-O[1]];
      if(a[0]*b[1]-a[1]*b[0]>=0) continue; if(Math.hypot(...a)*it.size<2.2) continue;
      const T=_textTex(it.str,o), s=it.size/T.F, wcm=T.w*s, x0=-4*s+(o.align==="center"?-wcm/2:o.align==="right"?-wcm:0), x1=x0+T.cw*s;
      let y0=-T.ch*s/2; if(o.base==="top") y0=-0.25*it.size; else if(o.base==="bottom"||o.base==="alphabetic") y0=-T.ch*s+0.25*it.size;
      const y1=y0+T.ch*s, Wp=(x,y)=>{ const v=P3(it.O[0]+x*it.U[0]-y*it.V[0],it.O[1]+x*it.U[1]-y*it.V[1],it.O[2]+x*it.U[2]-y*it.V[2]); return [v[0],v[1],v[2]+e+0.002]; };
      G.tr.push({dep:O[2]+e,tex:T.tex,a:1,q:[Wp(x0,y0),Wp(x1,y0),Wp(x1,y1),Wp(x0,y1)]});
    }else if(it.t==="tx"){
      const a=P3(...it.O), b=P3(it.O[0]+it.U[0],it.O[1]+it.U[1],it.O[2]+it.U[2]), c=P3(it.O[0]+it.V[0],it.O[1]+it.V[1],it.O[2]+it.V[2]);
      if((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<=0) continue;
      const d=P3(it.O[0]+it.U[0]+it.V[0],it.O[1]+it.U[1]+it.V[1],it.O[2]+it.U[2]+it.V[2]), ee=e+0.004*(o.bias===undefined?0.3:0);
      const q=[a,b,d,c].map(v=>[v[0],v[1],v[2]+ee]); for(const v of q) _gd(G,v[2]);
      const sw=it.src.width||1, sh=it.src.height||1;
      G.tq.push({src:it.src,q,uv:[it.sx/sw,it.sy/sh,(it.sx+it.sw)/sw,(it.sy+it.sh)/sh]});
      if(o.id) HITS.push([o.id,q]);
    }else if(it.t==="sp"){
      const p=P3(...it.c), R=it.r*CAM.k, base=rgba01(it.col), hi=rgba01(o.hi||"#ffffff"), lo=rgba01(o.lo||"#5d646b");
      const L=[-0.38,0.45,0.81], col=(fx,fy)=>{ const fz=Math.sqrt(Math.max(0,1-fx*fx-fy*fy)), l=fx*L[0]+fy*L[1]+fz*L[2];
        const m=(A,B,t)=>A.map((v,i)=>v+(B[i]-v)*t); const c=l>0.75?m(base,hi,(l-0.75)/0.25):m(lo,base,Math.max(0,(l+0.2)/0.95)); return "rgb("+c.slice(0,3).map(v=>Math.round(v*255)).join(",")+")"; };
      const N=18, rings=[0,0.45,0.8,1];
      for(let k=1;k<rings.length;k++) for(let i=0;i<N;i++){
        const A=i/N*6.2832, B=(i+1)/N*6.2832, pt=(f,a)=>[p[0]+R*f*Math.cos(a),p[1]+R*f*Math.sin(a),p[2]+e+it.r*Math.sqrt(Math.max(0,1-f*f))];
        const f0=rings[k-1], f1=rings[k], fm=(f0+f1)/2, am=(A+B)/2;
        _gtri(G,[pt(f0,A),pt(f1,A),pt(f1,B),pt(f0,B)],col(fm*Math.cos(am),-fm*Math.sin(am))); }
      if(o.id) HITS.push([o.id,Array.from({length:12},(_,i)=>[p[0]+R*Math.cos(i/12*6.283),p[1]+R*Math.sin(i/12*6.283),p[2]+it.r])]);
    }else if(it.t==="c"){
      const r=P3(...it.p[0]); _REC=new Map(); try{ it.draw(new Rec3(G,r[2],e)); }catch(err){} _REC=null;
    }
  }
  for(const t of G.tr) if(t.q) for(const v of t.q) _gd(G,v[2]);
  /* draw */
  const gl=GL3.gl, dpr=CAM.dpr||1, cw=Math.max(1,Math.round(W*dpr)), ch=Math.max(1,Math.round(H*dpr));
  if(GL3.c.width!==cw||GL3.c.height!==ch){ GL3.c.width=cw; GL3.c.height=ch; }
  gl.viewport(0,0,cw,ch); gl.clearColor(0,0,0,0); gl.clearDepth(1); gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.enable(gl.BLEND); gl.blendFunc(gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
  const d0=G.dmin===Infinity?0:G.dmin, dr=Math.max(1e-6,(G.dmax===-Infinity?1:G.dmax)-d0);
  const X=x=>x/W*2-1, Y=y=>1-y/H*2, Z=d=>0.98-1.96*(d-d0)/dr;
  const drawCol=arr=>{ if(!arr.length) return; const n=arr.length/7, f=new Float32Array(arr.length);
    for(let i=0;i<n;i++){ const j=i*7; f[j]=X(arr[j]); f[j+1]=Y(arr[j+1]); f[j+2]=Z(arr[j+2]); f[j+3]=arr[j+3]; f[j+4]=arr[j+4]; f[j+5]=arr[j+5]; f[j+6]=arr[j+6]; }
    gl.useProgram(GL3.pc); gl.bindBuffer(gl.ARRAY_BUFFER,GL3.buf); gl.bufferData(gl.ARRAY_BUFFER,f,gl.STREAM_DRAW);
    gl.enableVertexAttribArray(GL3.pcP); gl.vertexAttribPointer(GL3.pcP,3,gl.FLOAT,false,28,0);
    gl.enableVertexAttribArray(GL3.pcC); gl.vertexAttribPointer(GL3.pcC,4,gl.FLOAT,false,28,12);
    gl.drawArrays(gl.TRIANGLES,0,n); gl.disableVertexAttribArray(GL3.pcC); };
  const drawTex=(tex,q,uv,a)=>{ const [u0,v0,u1,v1]=uv||[0,0,1,1], t=[[u0,v0],[u1,v0],[u1,v1],[u0,v1]], f=new Float32Array(30); let k=0;
    for(const i of [0,1,2,0,2,3]){ f[k++]=X(q[i][0]); f[k++]=Y(q[i][1]); f[k++]=Z(q[i][2]); f[k++]=t[i][0]; f[k++]=t[i][1]; }
    gl.useProgram(GL3.pt); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,tex); gl.uniform1i(GL3.ptS,0); gl.uniform1f(GL3.ptA,a===undefined?1:a);
    gl.bindBuffer(gl.ARRAY_BUFFER,GL3.buf); gl.bufferData(gl.ARRAY_BUFFER,f,gl.STREAM_DRAW);
    gl.enableVertexAttribArray(GL3.ptP); gl.vertexAttribPointer(GL3.ptP,3,gl.FLOAT,false,20,0);
    gl.enableVertexAttribArray(GL3.ptT); gl.vertexAttribPointer(GL3.ptT,2,gl.FLOAT,false,20,12);
    gl.drawArrays(gl.TRIANGLES,0,6); gl.disableVertexAttribArray(GL3.ptT); };
  gl.depthMask(true); drawCol(G.op);
  for(const t of G.tq) drawTex(_srcTex(t.src).tex,t.q,t.uv,1);
  gl.depthMask(false); G.tr.sort((a,b)=>a.dep-b.dep);
  let batch=[];
  for(const t of G.tr){ if(t.col){ for(const x of t.col) batch.push(x); continue; } drawCol(batch); batch=[]; drawTex(t.tex,t.q,null,t.a); }
  drawCol(batch); gl.depthMask(true);
  ctx.drawImage(GL3.c,0,0,W,H);
}
/* the id under a screen point: the nearest of the faces that contain it */
function pick3(x,y){
  if(GL3.ok!==true) return pick3_2d(x,y);
  let best=null, bd=-Infinity;
  for(const [id,q] of HITS){ if(!pointIn(q,x,y)) continue;
    let d=-Infinity;
    for(let i=1;i+1<q.length;i++){ const a=q[0], b=q[i], c=q[i+1], den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1]); if(Math.abs(den)<1e-9) continue;
      const l1=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den, l2=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den, l3=1-l1-l2;
      if(l1>=-1e-6&&l2>=-1e-6&&l3>=-1e-6){ d=l1*a[2]+l2*b[2]+l3*c[2]; break; } }
    if(d===-Infinity) d=q.reduce((s,v)=>s+(v[2]||0),0)/q.length;
    if(d>=bd){ bd=d; best=id; } }
  return best;
}

/* ══════════════════════════════════════════════════════════════
   The bench: a desk you look at in 3-D, apparatus you move on it and
   instruments you work with your own hands.

     const b = B3.bench(host, {
       aspect: 0.6, speeds: [1, 10, 60], keys: [' '],
       home:  { yaw, pitch, k, tx, ty, tz },          // the whole-desk view (k: pixels per cm at 1000 px wide)
       views: { psu: { yaw, pitch, k, tx, ty, tz, title: {ko, en} }, ... },
       lang:  () => 'ko' | 'en',
       frame: b => { ... }                             // describe the scene again every frame
     });

   Inside frame(b):
     b.t, b.dt        scene time and its step (s), already multiplied by the time speed
     b.keys           keys pressed since the last frame
     b.L(ko, en)      the text in the page's language
     b.panel(name, w, h, draw)
                      a front panel drawn in 2-D (w × h panel units) with the HaslaLab widgets
                      (HL.knob, HL.button, HL.toggle, HL.lcd ...) — draw(ui) gets a ui that works like
                      the handlab one; it returns the canvas, which the page lays on a face with
                      B3.tex3(cv, 0, 0, cv.width, cv.height, O, U, V, { id: 'p:' + name }).
                      Clicks, drags and the wheel on that face reach the panel's widgets.
     b.moved(name)    [dx, dz] the hand moved the part 'm:<name>' on the desk since the last frame
     b.clicked(id)    the face id was clicked (pressed and let go without moving)
     b.held(id)       the face id is being held down
     b.view           the open close-up view, or null; b.go(name) opens one, b.go(null) goes back
   Every face of a movable part carries the id 'm:<name>'; a click on it (no drag) opens views[name].
   Drag on an empty spot turns the desk round, right- or Shift-drag pans, the wheel zooms,
   a double click on an empty spot (or Esc) goes back to the whole desk. */
const B3 = window.B3 = {hitAt: (x, y) => hitAt(x, y), CAM, P3, onPlane, onPlaneX, face, quad, box3, boxY, cyl3, cylSeg, cylAB, prism3, line3, poly3,
  text3, custom3, sphere3, tex3, shade, orient, begin3, render3, pick3};

function hitAt(x, y){
  let best = null, bd = -Infinity;
  for (const [id, q] of HITS){ if (!pointIn(q, x, y)) continue;
    let d = -Infinity;
    for (let i = 1; i + 1 < q.length; i++){ const a = q[0], b = q[i], c = q[i + 1], den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1]); if (Math.abs(den) < 1e-9) continue;
      const l1 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / den, l2 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / den, l3 = 1 - l1 - l2;
      if (l1 >= -1e-6 && l2 >= -1e-6 && l3 >= -1e-6){ d = l1 * (a[2] || 0) + l2 * (b[2] || 0) + l3 * (c[2] || 0); break; } }
    if (d === -Infinity) d = q.reduce((s, v) => s + (v[2] || 0), 0) / q.length;
    if (d >= bd){ bd = d; best = [id, q]; } }
  return best;
}
/* screen point → (u, v) in 0..1 on a laid-on panel; the quad is [O, O+U, O+U+V, O+V] */
function quadUV(q, x, y){
  const a = q[0], b = q[1], c = q[3];
  const ux = b[0] - a[0], uy = b[1] - a[1], vx = c[0] - a[0], vy = c[1] - a[1], det = ux * vy - uy * vx;
  if (Math.abs(det) < 1e-9) return null;
  const px = x - a[0], py = y - a[1];
  return [(px * vy - py * vx) / det, (ux * py - uy * px) / det];
}
function insideShape(s, x, y){
  if (typeof s === 'function') return s(x, y);
  if (s.r !== undefined) return (x - s.cx) * (x - s.cx) + (y - s.cy) * (y - s.cy) <= s.r * s.r;
  return x >= s.x && x <= s.x + s.w && y >= s.y && y <= s.y + s.h;
}

const CSS = '' +
  '.b3wrap{position:relative;width:100%;user-select:none;-webkit-user-select:none;touch-action:none}' +
  '.b3wrap canvas{display:block;width:100%;border-radius:8px;background:#20242a}' +
  '.b3bar{position:absolute;top:8px;right:8px;display:flex;gap:4px;align-items:center}' +
  '.b3bar button,.b3back{font:600 12px/1 ui-sans-serif,system-ui,"Segoe UI","Malgun Gothic",sans-serif;padding:6px 9px;border-radius:6px;border:1px solid #3a414a;background:rgba(30,34,40,.88);color:#dfe7ee;cursor:pointer}' +
  '.b3bar button.on{background:#4ec9b0;border-color:#4ec9b0;color:#0c0c0c}' +
  '.b3back{position:absolute;top:8px;left:8px}' +
  '.b3back[hidden]{display:none}' +
  '.b3title{position:absolute;top:13px;left:50%;transform:translateX(-50%);font:600 12.5px ui-sans-serif,system-ui,"Malgun Gothic",sans-serif;color:#e8eef3;background:rgba(20,24,28,.7);padding:4px 10px;border-radius:6px;pointer-events:none}' +
  '.b3title:empty{display:none}' +
  '.b3hint{position:absolute;left:10px;bottom:8px;font:12px ui-sans-serif,system-ui,"Malgun Gothic",sans-serif;color:#c9d1d9;background:rgba(20,24,28,.62);padding:3px 8px;border-radius:5px;pointer-events:none;max-width:80%}' +
  '.b3msg{position:absolute;left:50%;bottom:34px;transform:translateX(-50%);font:600 12.5px ui-sans-serif,system-ui,"Malgun Gothic",sans-serif;color:#10161b;background:#ffd479;padding:5px 11px;border-radius:6px;pointer-events:none;opacity:0;transition:opacity .25s}' +
  '.b3msg.on{opacity:1}';

B3.bench = function (host, o){
  if (!document.getElementById('b3css')){ const st = document.createElement('style'); st.id = 'b3css'; st.textContent = CSS; document.head.appendChild(st); }
  const wrap = document.createElement('div'); wrap.className = 'b3wrap';
  const cv = document.createElement('canvas'); wrap.appendChild(cv);
  const bar = document.createElement('div'); bar.className = 'b3bar'; wrap.appendChild(bar);
  const back = document.createElement('button'); back.className = 'b3back'; back.hidden = true; wrap.appendChild(back);
  const title = document.createElement('div'); title.className = 'b3title'; wrap.appendChild(title);
  const hint = document.createElement('div'); hint.className = 'b3hint'; wrap.appendChild(hint);
  const msg = document.createElement('div'); msg.className = 'b3msg'; wrap.appendChild(msg);
  host.appendChild(wrap);
  const ctx = cv.getContext('2d');
  const L = (ko, en) => (o.lang && o.lang() === 'en') ? (en === undefined ? ko : en) : ko;
  const aspect = o.aspect || 0.6, views = o.views || {};
  let t = 0, last = performance.now(), speed = 1, paused = false, keys = [];
  let view = null, anim = null, msgT = 0;

  /* time speeds */
  const speeds = o.speeds || [1];
  function syncBar(){ bar.querySelectorAll('button').forEach(x => x.classList.toggle('on', x.dataset.s === 'p' ? paused : (+x.dataset.s === speed && !paused))); }
  if (speeds.length > 1){
    speeds.forEach(s => { const x = document.createElement('button'); x.textContent = '×' + s; x.dataset.s = s; x.onclick = () => { speed = s; paused = false; syncBar(); }; bar.appendChild(x); });
    const pz = document.createElement('button'); pz.textContent = '❚❚'; pz.dataset.s = 'p'; pz.onclick = () => { paused = !paused; syncBar(); }; bar.appendChild(pz);
    syncBar();
  }

  /* camera */
  const camOf = v => ({ yaw: v.yaw, pitch: v.pitch, k: v.k * CAM.W / 1000, tx: v.tx, ty: v.ty, tz: v.tz, px: 0, py: 0 });
  function go(name){
    view = name && views[name] ? name : null;
    const v = view ? views[view] : o.home;
    anim = { from: { yaw: CAM.yaw, pitch: CAM.pitch, k: CAM.k, tx: CAM.tx, ty: CAM.ty, tz: CAM.tz, px: CAM.px, py: CAM.py }, to: camOf(v), s: 0 };
    back.hidden = !view; renderText();
    if (o.onView) o.onView(view);
  }
  function renderText(){
    back.textContent = L('← 책상 전체', '← Whole desk');
    title.textContent = view && views[view].title ? L(views[view].title.ko, views[view].title.en) : '';
    hint.textContent = view ? L(views[view].hint ? views[view].hint.ko : '손잡이는 끌거나 휠로 돌리기 · 버튼은 클릭 · Esc: 돌아가기', views[view].hint ? views[view].hint.en : 'Turn knobs by dragging or with the wheel · click buttons · Esc: back')
                     : L(o.hint ? o.hint.ko : '장비 클릭: 가까이 보기 · 장비 끌기: 옮기기 · 빈 곳 끌기: 돌려 보기 · 휠: 확대',
                         o.hint ? o.hint.en : 'Click an instrument: close up · drag it: move it · drag empty space: turn · wheel: zoom');
  }
  back.onclick = () => go(null);

  function layout(){
    const dpr = Math.min(devicePixelRatio || 1, 2), w = wrap.clientWidth || 900;
    const hmax = innerHeight * (document.fullscreenElement ? 0.9 : 0.8);
    const cw = Math.min(w, hmax / aspect), ch = cw * aspect, oldW = CAM.W || cw;
    cv.style.width = cw + 'px'; cv.style.height = ch + 'px'; cv.width = Math.round(cw * dpr); cv.height = Math.round(ch * dpr);
    CAM.k *= cw / oldW; CAM.W = cw; CAM.H = ch; CAM.dpr = dpr;
  }
  CAM.W = 0; layout();
  Object.assign(CAM, camOf(o.home));
  addEventListener('resize', layout);
  if (window.ResizeObserver) new ResizeObserver(layout).observe(wrap);

  /* pointer state */
  let ptr = null, down = null, wheelEv = null, clicks = new Set(), moves = {}, smoves = {}, wheels = {}, dbl = false;
  const panels = {};
  const pos = e => { const r = cv.getBoundingClientRect(); return [(e.clientX - r.left) * CAM.W / r.width, (e.clientY - r.top) * CAM.H / r.height]; };
  function panelPoint(name, q, x, y){
    const P = panels[name]; if (!P) return null; const uv = quadUV(q, x, y); if (!uv) return null;
    return [uv[0] * P.w, uv[1] * P.h];
  }
  function panelRegion(P, px, py){
    for (let i = P.regions.length - 1; i >= 0; i--){ const R = P.regions[i], q = R.inv.transformPoint(new DOMPoint(px * P.R, py * P.R));
      if (insideShape(R.shape, q.x, q.y)) return R; }
    return null;
  }
  function pev(P, id){ return P.ev[id] || (P.ev[id] = {}); }
  cv.addEventListener('contextmenu', e => e.preventDefault());
  cv.addEventListener('pointerdown', e => {
    const p = pos(e); ptr = p; cv.setPointerCapture(e.pointerId);
    const h = hitAt(p[0], p[1]), id = h ? h[0] : null;
    down = { x: p[0], y: p[1], lx: p[0], ly: p[1], id, q: h && h[1], btn: e.button, shift: e.shiftKey, moved: 0, kind: 'cam' };
    if (e.button === 0 && id && id.startsWith('p:') && views[id.slice(2)] && view !== id.slice(2)){
      down.kind = 'move'; down.name = id.slice(2); down.w0 = onPlane(p[0], p[1], o.moveY || 0); }      /* first look closer, then work it */
    else if (e.button === 0 && id && id.startsWith('p:')){
      const name = id.slice(2), pp = panelPoint(name, h[1], p[0], p[1]), P = panels[name];
      const R = pp && panelRegion(P, pp[0], pp[1]);
      if (R){ down.kind = 'panel'; down.panel = name; down.rid = R.id; P.active = R.id; const E = pev(P, R.id); E.press = true; E.shift = e.shiftKey; E.x = pp[0]; E.y = pp[1]; }
      else { down.kind = 'move'; down.name = name; down.w0 = onPlane(p[0], p[1], o.moveY || 0); }
    } else if (e.button === 0 && id && id.startsWith('m:')){ down.kind = 'move'; down.name = id.slice(2); down.w0 = onPlane(p[0], p[1], o.moveY || 0); }
    else if (e.button === 0 && id && id.startsWith('c:')) down.kind = 'click';
    if (e.button === 2 || e.button === 1 || e.shiftKey) down.kind = down.kind === 'cam' ? 'pan' : down.kind;
  });
  cv.addEventListener('pointermove', e => {
    const p = pos(e); ptr = p; if (!down) return;
    const dx = p[0] - down.lx, dy = p[1] - down.ly; down.lx = p[0]; down.ly = p[1]; down.moved += Math.abs(dx) + Math.abs(dy);
    if (down.kind === 'panel'){ const P = panels[down.panel], E = pev(P, down.rid); E.rawdy = (E.rawdy || 0) + dy; E.rawdx = (E.rawdx || 0) + dx;
      const h = down.q, pp = panelPoint(down.panel, h, p[0], p[1]); if (pp){ E.dx = (E.dx || 0) + (pp[0] - (E.x || pp[0])); E.dy = (E.dy || 0) + (pp[1] - (E.y || pp[1])); E.x = pp[0]; E.y = pp[1]; } }
    else if (down.kind === 'move'){ const w1 = onPlane(p[0], p[1], o.moveY || 0), m = moves[down.name] || (moves[down.name] = [0, 0]);
      m[0] += w1[0] - down.w0[0]; m[1] += w1[2] - down.w0[2]; down.w0 = w1;
      const sm = smoves[down.name] || (smoves[down.name] = [0, 0]); sm[0] += dx / CAM.k; sm[1] += dy / CAM.k; }
    else if (down.kind === 'pan' || (down.kind === 'cam' && (down.btn === 2 || down.shift))){ CAM.px += dx; CAM.py += dy; anim = null; }
    else if (down.kind === 'cam' || (down.kind === 'click' && down.moved > 6)){ down.kind = 'cam';
      CAM.yaw += dx * 0.008; CAM.pitch = Math.max(0.06, Math.min(1.45, CAM.pitch + dy * 0.006)); anim = null; }
  });
  function up(e){
    if (!down) return; const p = pos(e);
    const quiet = down.moved < 6;
    if (down.kind === 'panel'){ const P = panels[down.panel], E = pev(P, down.rid); E.release = true;
      if (quiet){ const pp = panelPoint(down.panel, down.q, p[0], p[1]), R = pp && panelRegion(P, pp[0], pp[1]); if (R && R.id === down.rid) E.click = true; }
      P.active = null; }
    else if (quiet && down.id && down.btn === 0){
      clicks.add(down.id);
      const nm = down.id.slice(2);
      if ((down.id.startsWith('m:') || down.id.startsWith('p:')) && views[nm] && view !== nm) go(nm);
    }
    down = null;
  }
  cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
  cv.addEventListener('pointerleave', () => { if (!down) ptr = null; });
  cv.addEventListener('dblclick', e => { const p = pos(e), h = hitAt(p[0], p[1]); if (!h || h[0] === 'desk') { if (view) go(null); else { anim = { from: Object.assign({}, CAM), to: camOf(o.home), s: 0 }; } } });
  cv.addEventListener('wheel', e => {
    e.preventDefault(); const p = pos(e), h = hitAt(p[0], p[1]), dir = e.deltaY < 0 ? 1 : -1;
    if (h && h[0].startsWith('p:')){ const name = h[0].slice(2), P = panels[name], pp = panelPoint(name, h[1], p[0], p[1]), R = pp && panelRegion(P, pp[0], pp[1]);
      if (R && R.o && R.o.wheel){ const E = pev(P, R.id); E.wheel = (E.wheel || 0) + dir; E.shift = e.shiftKey; return; } }
    if (h && h[0].startsWith('m:') && (o.wheelIds || []).indexOf(h[0].slice(2)) >= 0){ const nm = h[0].slice(2); wheels[nm] = (wheels[nm] || 0) + dir * (e.shiftKey ? 0.1 : 1); return; }
    const f = dir > 0 ? 1.12 : 1 / 1.12, k0 = CAM.k, k1 = Math.max(CAM.W / 1000 * 0.8, Math.min(CAM.W / 1000 * 160, k0 * f));
    const cx = CAM.W / 2 + CAM.px, cy = CAM.H / 2 + CAM.py;
    CAM.px = p[0] - (p[0] - cx) * k1 / k0 - CAM.W / 2; CAM.py = p[1] - (p[1] - cy) * k1 / k0 - CAM.H / 2; CAM.k = k1; anim = null;
  }, { passive: false });
  addEventListener('keydown', e => {
    if (!wrap.isConnected || wrap.offsetParent === null) return;
    if (/INPUT|TEXTAREA|SELECT/.test((e.target.tagName || ''))) return;
    if (e.key === 'Escape' && view){ go(null); return; }
    if ((o.keys || []).indexOf(e.key) >= 0){ keys.push(e.key); e.preventDefault(); }
  });

  /* panels: a 2-D front drawn with the handlab widgets, laid on a face */
  function panel(name, w, h, draw){
    let P = panels[name];
    const R = o.panelRes || 2;
    if (!P){ const c = document.createElement('canvas'); c.width = Math.round(w * R); c.height = Math.round(h * R);
      P = panels[name] = { cv: c, g: c.getContext('2d'), w, h, R, regions: [], ev: {}, active: null }; }
    const g = P.g; P.regions = [];
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, P.cv.width, P.cv.height); g.setTransform(R, 0, 0, R, 0, 0);
    const ui = { g, W: w, H: h, t, dt: api.dt, pass: 'main', keys, lens: 1,
      hit(id, shape, ho){ P.regions.push({ id, shape, o: ho, inv: g.getTransform().invertSelf() });
        const E = P.ev[id] || {}, out = { hover: false, down: P.active === id, press: !!E.press, click: !!E.click, release: !!E.release,
          dx: E.dx || 0, dy: E.dy || 0, rawdy: E.rawdy || 0, rawdx: E.rawdx || 0, x: E.x, y: E.y, wheel: E.wheel || 0, shift: !!E.shift, dbl: false };
        P.ev[id] = { x: E.x, y: E.y }; return out; },
      bg(){ return {}; }, zoomTo(){}, inZoom(){ return false; } };
    g.save(); draw(ui); g.restore();
    return P.cv;
  }

  const api = { t: 0, dt: 0, keys, L, views, lang: () => (o.lang ? o.lang() : 'ko'), panel, go, el: wrap, canvas: cv, renderText,
    moved: name => { const m = moves[name]; return m ? m : [0, 0]; },
    screenMoved: name => smoves[name] || [0, 0],          /* [right, down] in cm of the screen at the present zoom */
    wheel: name => wheels[name] || 0,
    dragging: name => !!(down && down.kind === 'move' && down.name === name),
    clicked: id => clicks.has(id), held: id => !!(down && down.id === id && down.kind !== 'cam' && down.kind !== 'pan'),
    say: (ko, en) => { msg.textContent = L(ko, en); msg.classList.add('on'); msgT = performance.now() + 2600; },
    get view(){ return view; }, get speed(){ return paused ? 0 : speed; },
    setHome: v => { o.home = v; } };

  function frame(now){
    const real = Math.min(0.1, (now - last) / 1000); last = now;
    const dt = paused ? 0 : real * speed; t += dt; api.t = t; api.dt = dt; api.real = real;
    if (anim){ anim.s = Math.min(1, anim.s + real / 0.45); const s = anim.s * anim.s * (3 - 2 * anim.s);
      for (const k of ['yaw', 'pitch', 'k', 'tx', 'ty', 'tz', 'px', 'py']) CAM[k] = anim.from[k] + (anim.to[k] - anim.from[k]) * s;
      if (anim.s >= 1) anim = null; }
    if (msgT && now > msgT){ msg.classList.remove('on'); msgT = 0; }
    ctx.setTransform(CAM.dpr, 0, 0, CAM.dpr, 0, 0); ctx.clearRect(0, 0, CAM.W, CAM.H);
    const bgr = ctx.createLinearGradient(0, 0, 0, CAM.H); bgr.addColorStop(0, o.bg ? o.bg[0] : '#2c3138'); bgr.addColorStop(1, o.bg ? o.bg[1] : '#1a1d22');
    ctx.fillStyle = bgr; ctx.fillRect(0, 0, CAM.W, CAM.H);
    begin3();
    try { o.frame(api); } catch (err){ console.error(err); }
    render3(ctx);
    if (o.overlay) o.overlay(ctx, api);
    /* cursor */
    let cur = 'grab';
    if (down) cur = down.kind === 'panel' ? 'ns-resize' : down.kind === 'move' ? 'grabbing' : down.kind === 'pan' ? 'move' : 'grabbing';
    else if (ptr){ const h = hitAt(ptr[0], ptr[1]); if (h){ const id = h[0];
      if (id.startsWith('p:')){ const name = id.slice(2), pp = panelPoint(name, h[1], ptr[0], ptr[1]), R = pp && panels[name] && panelRegion(panels[name], pp[0], pp[1]);
        cur = views[name] && view !== name ? 'zoom-in' : R ? ((R.o && R.o.cursor) || 'pointer') : 'grab'; }
      else if (id.startsWith('m:')) cur = views[id.slice(2)] && view !== id.slice(2) ? 'zoom-in' : 'grab'; else if (id.startsWith('c:')) cur = 'pointer'; } }
    cv.style.cursor = cur;
    /* per-frame events are used up */
    for (const P of Object.values(panels)) for (const k in P.ev){ const E = P.ev[k]; P.ev[k] = { x: E.x, y: E.y }; }
    clicks = new Set(); moves = {}; smoves = {}; wheels = {}; keys.length = 0;
    requestAnimationFrame(frame);
  }
  renderText();
  requestAnimationFrame(frame);
  return api;
};

/* ---------- parts many benches share ---------- */
/* a wooden lab desk, x0..x1 × z0..z1, top at y = 0 */
B3.desk = function (x0, x1, z0, z1, o){
  o = o || {};
  box3(x0, x1, -4, 0, z0, z1, o.col || '#b8875a', { id: 'desk', top: o.top || '#c99a6b', cull: true });
  const n = Math.floor((x1 - x0) / 14);
  for (let i = 1; i < n; i++){ const x = x0 + (x1 - x0) * i / n + (i % 3) * 1.3; line3([x, 0.01, z0], [x + 0.8, 0.01, z1], 'rgba(120,80,45,.18)', 0.8); }
  if (o.mat){ const [mx0, mx1, mz0, mz1] = o.mat; box3(mx0, mx1, 0, 0.25, mz0, mz1, '#2f6b4f', { id: 'desk', top: '#3a7d5d' }); }
};
/* a cable hanging between two points (sag in cm), drawn as a thick polyline */
B3.cable = function (a, b, col, sag, lw, n){
  n = n || 18; sag = sag === undefined ? 6 : sag;
  const pts = [];
  for (let i = 0; i <= n; i++){ const s = i / n, y = a[1] + (b[1] - a[1]) * s - sag * 4 * s * (1 - s);
    pts.push([a[0] + (b[0] - a[0]) * s, Math.max(0.35, y), a[2] + (b[2] - a[2]) * s]); }
  poly3(pts, col, lw || 2.2);
};
/* a cable lying on the desk from a to b with a soft bend */
B3.cableDesk = function (a, b, col, lw){
  const mid = [(a[0] + b[0]) / 2, 0.4, (a[2] + b[2]) / 2 + 6];
  const pts = []; for (let i = 0; i <= 20; i++){ const s = i / 20, u = 1 - s;
    pts.push([u * u * a[0] + 2 * u * s * mid[0] + s * s * b[0], Math.max(0.4, u * u * a[1] + 2 * u * s * mid[1] + s * s * b[1]), u * u * a[2] + 2 * u * s * mid[2] + s * s * b[2]]); }
  poly3(pts, col, lw || 2.2);
};
/* a banana jack on a vertical panel facing +z, centre (x, y, z) */
B3.jack = function (x, y, z, col, o){
  cyl3('z', z, z + 0.9, x, y, 0.55, col, Object.assign({ seg: 14, cap: B3.shade(col, 0.6) }, o || {}));
  cyl3('z', z + 0.9, z + 0.95, x, y, 0.22, '#111', { seg: 10 });
};
/* a hand stopwatch (button latency in s): startStop / lapReset / read like the handlab one */
B3.Stopwatch = function (latency){ this.run = false; this.acc = 0; this.t0 = 0; this.lap = null; this.latency = latency || 0.03; this.pend = []; };
B3.Stopwatch.prototype.read = function (t){ return this.acc + (this.run ? t - this.t0 : 0); };
B3.Stopwatch.prototype.startStop = function (t){ this.pend.push(['ss', t + this.latency]); };
B3.Stopwatch.prototype.lapReset = function (t){ this.pend.push(['lr', t + this.latency]); };
B3.Stopwatch.prototype.update = function (t){
  const keep = [];
  for (const p of this.pend){
    if (p[1] > t){ keep.push(p); continue; }
    if (p[0] === 'ss'){ if (this.run){ this.acc += p[1] - this.t0; this.run = false; } else { this.t0 = p[1]; this.run = true; } }
    else { if (this.run) this.lap = this.lap === null ? this.read(p[1]) : null; else { this.acc = 0; this.lap = null; } }
  }
  this.pend = keep;
};
B3.fmtWatch = function (s){ const m = Math.floor(s / 60), r = s - m * 60; return String(m).padStart(2, '0') + "'" + r.toFixed(2).padStart(5, '0').replace('.', '"'); };
/* the stopwatch on the desk, after the Casio HS-3V: a grey body, a two-line LCD, START/STOP right,
   LAP/RESET left; its face is a panel, so it is worked by hand like any instrument.
   p = [x, z] on the desk; returns nothing, the movable id is 'm:<name>' */
B3.stopwatch = function (b, name, p, sw){
  const [x, z] = p, w = 6.8, d = 7.8, h = 1.7;
  sw.update(b.t);
  box3(x - w / 2, x + w / 2, 0, h, z - d / 2, z + d / 2, '#3b3f45', { id: 'm:' + name, top: '#4a4f56' });
  cyl3('x', x - w / 2 + 0.3, x + w / 2 - 0.3, h * 0.55, z - d / 2 - 0.25, 0.5, '#2f3338', { id: 'm:' + name, seg: 10 });
  box3(x - 0.5, x + 0.5, h * 0.4, h * 0.9, z - d / 2 - 1.3, z - d / 2 - 0.2, '#2a2d31', { id: 'm:' + name });
  const cv = b.panel(name, 300, 340, ui => {
    const g = ui.g;
    HL.rr(g, 0, 0, 300, 340, 34, '#4a4f56'); HL.rr(g, 12, 12, 276, 316, 28, '#575d65');
    HL.text(g, 'CASIO', 150, 40, '#e8ecef', 22, 'center', '800');
    HL.text(g, 'STOPWATCH  HS-3V', 150, 66, '#c9d0d6', 13, 'center', '600');
    HL.rr(g, 34, 86, 232, 110, 12, '#22262a'); HL.rr(g, 44, 96, 212, 90, 6, '#b9c4a4');
    const v = sw.lap !== null ? sw.lap : sw.read(b.t), s = B3.fmtWatch(v);
    HL.text(g, s, 150, 146, '#1d2318', 44, 'center', '700', HL.MONO);
    if (sw.lap !== null) HL.text(g, 'SPLIT', 64, 112, '#1d2318', 12, 'left', '800');
    if (sw.run) HL.text(g, '▶', 236, 112, '#1d2318', 12, 'right', '800');
    const lr = HL.button(ui, 'lr', 40, 232, 100, 70, { round: false, col: '#2e3237', label: b.L('LAP/RESET', 'LAP/RESET'), size: 13 });
    const ss = HL.button(ui, 'ss', 160, 232, 100, 70, { round: false, col: '#b83a32', label: 'START/STOP', size: 13 });
    if (lr.press) sw.lapReset(b.t); if (ss.press) sw.startStop(b.t);
  });
  B3.tex3(cv, 0, 0, cv.width, cv.height, [x - w / 2 + 0.25, h + 0.01, z - d / 2 + 0.25], [w - 0.5, 0, 0], [0, 0, d - 0.5], { id: 'p:' + name });
};
})();
