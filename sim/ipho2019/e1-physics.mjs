/* IPhO 2019 Q1: direct physics/state port of IPhO2019_Q1_Sim_KO.py.
 * Coordinates: centimetres, +x right, +y down; angles: degrees anticlockwise.
 * No inferred refractive indices, diffraction results or solved answers are produced.
 * Air segments are diagnostic geometry ONLY; render glass paths and surface spots.
 */
export const ROOM_W = 272, ROOM_D = 208, SCREEN_W = 120;
export const DARK_FROM = 180, DARK_LEN = 420, DARK_EVERY = 900;
export const DISK_RADIUS = 10, BARREL = 2.9;
export const TRAY = Object.freeze(['ruler','disk','holder','screen','tape6','tape','ruler8']);
export const LOCAL = Object.freeze({ruler:[30.6,3],disk:[15.4,15.4],holder:[12.6,8.6],screen:[61,3],ruler8:[15.6,1.9]});
export const COLL = Object.freeze({ruler:[30.4,2.6],disk:[15.2,15.2],holder:[12.5,8.5],screen:[60,0.9]});
const NOCLASH = ['ruler','disk','holder','screen'], RAD = Math.PI/180;
const dot = (a,b) => a[0]*b[0]+a[1]*b[1];
const mod = (a,n) => ((a%n)+n)%n;
const outside = ([x,y]) => !(-6<x && x<ROOM_W+6 && -6<y && y<ROOM_D+6);
const point = p => Array.isArray(p) && p.length>=2 && Number.isFinite(p[0]) && Number.isFinite(p[1]);

export function norm(v) { const m=Math.hypot(v[0],v[1])||1;return [v[0]/m,v[1]/m]; }
export function dirv(degrees) { const a=degrees*RAD;return [Math.cos(a),-Math.sin(a)]; }
export function refract(d,nvec,n1,n2) {
  const r=n1/n2,ci=-dot(d,nvec),s2=r*r*(1-ci*ci);
  if(s2>1)return null;
  const ct=Math.sqrt(1-s2);return norm([r*d[0]+(r*ci-ct)*nvec[0],r*d[1]+(r*ci-ct)*nvec[1]]);
}
export function fresnel_s(ci,n1,n2) {
  const r=n1/n2,s2=r*r*(1-ci*ci);if(s2>=1)return 1;
  const ct=Math.sqrt(1-s2),rs=(n1*ci-n2*ct)/(n1*ci+n2*ct);return rs*rs;
}
export function seg_hit(p,d,a,b) {
  const ex=b[0]-a[0],ey=b[1]-a[1],den=d[0]*ey-d[1]*ex;
  if(Math.abs(den)<1e-12)return null;
  const t=((a[0]-p[0])*ey-(a[1]-p[1])*ex)/den,u=((a[0]-p[0])*d[1]-(a[1]-p[1])*d[0])/den;
  return t>1e-6 && -1e-9<=u && u<=1+1e-9 ? t : null;
}
export function circ_hit(p,d,c,radius) {
  const ox=p[0]-c[0],oy=p[1]-c[1],b=ox*d[0]+oy*d[1],cc=ox*ox+oy*oy-radius*radius,disc=b*b-cc;
  if(disc<0)return [];const sd=Math.sqrt(disc);return [-b-sd,-b+sd].filter(t=>t>1e-6);
}
export function grating_frame(d,a,b) {
  let gv=norm([b[0]-a[0],b[1]-a[1]]),nv=[-gv[1],gv[0]];
  if(dot(nv,d)<0)nv=nv.map(x=>-x);
  let sa=dot(d,gv);if(sa<0){gv=gv.map(x=>-x);sa=-sa;}
  return [nv,gv,sa];
}
export function vis(intensity,dark) {
  if(dark)return intensity<1e-4?0:Math.min(1,1.90*intensity**0.55);
  return intensity<0.020?0:Math.min(1,intensity**0.42*0.80);
}

// CPython's integer-seeded MT19937, including 53-bit random() and getrandbits
// rejection sampling. Thus a numeric seed reproduces the attached Python file.
export class PythonRandom {
  constructor(seed=201901) {
    if(typeof seed!=='bigint' && (!Number.isSafeInteger(seed)))throw new TypeError('Seed must be a safe integer or bigint');
    let value=BigInt(seed);if(value<0n)value=-value;
    const keys=[];do{keys.push(Number(value&0xffffffffn));value>>=32n;}while(value);
    this.mt=new Uint32Array(624);this.mt[0]=19650218;
    for(let i=1;i<624;i++)this.mt[i]=(Math.imul(this.mt[i-1]^(this.mt[i-1]>>>30),1812433253)+i)>>>0;
    let i=1,j=0;
    for(let k=Math.max(624,keys.length);k>0;k--){
      this.mt[i]=((this.mt[i]^Math.imul(this.mt[i-1]^(this.mt[i-1]>>>30),1664525))+keys[j]+j)>>>0;
      if(++i>=624){this.mt[0]=this.mt[623];i=1;}if(++j>=keys.length)j=0;
    }
    for(let k=623;k>0;k--){
      this.mt[i]=((this.mt[i]^Math.imul(this.mt[i-1]^(this.mt[i-1]>>>30),1566083941))-i)>>>0;
      if(++i>=624){this.mt[0]=this.mt[623];i=1;}
    }
    this.mt[0]=0x80000000;this.index=624;
  }
  uint32() {
    const mt=this.mt;
    if(this.index>=624){
      for(let i=0;i<624;i++){const y=(mt[i]&0x80000000)|(mt[(i+1)%624]&0x7fffffff);mt[i]=(mt[(i+397)%624]^(y>>>1)^((y&1)?0x9908b0df:0))>>>0;}
      this.index=0;
    }
    let y=mt[this.index++];y^=y>>>11;y^=(y<<7)&0x9d2c5680;y^=(y<<15)&0xefc60000;y^=y>>>18;return y>>>0;
  }
  random() { return ((this.uint32()>>>5)*67108864+(this.uint32()>>>6))/9007199254740992; }
  uniform(a,b) { return a+(b-a)*this.random(); }
  randint(a,b) {
    if(!Number.isSafeInteger(a)||!Number.isSafeInteger(b)||b<a||b-a+1>0xffffffff)throw new RangeError('Unsupported integer range');
    const n=b-a+1,k=Math.floor(Math.log2(n))+1;let r;
    do{r=this.uint32()>>>(32-k);}while(r>=n);return a+r;
  }
}

export class OpticalLab {
  constructor(options) {
    const provided=typeof options==='object' && options!==null ? options.seed : options;
    const seed=provided??(globalThis.crypto?.getRandomValues?globalThis.crypto.getRandomValues(new Uint32Array(1))[0]:(Date.now()^Math.floor(Math.random()*0xffffffff))>>>0);
    this.seed=seed;this.rng=new PythonRandom(seed);const rng=this.rng;
    this.n_disk=rng.uniform(1.505,1.524);this.n_prism=rng.uniform(1.6395,1.6455);
    this.lam_over_d=rng.uniform(0.3955,0.4045);this.grating_id='#'+rng.randint(100,999);
    const e1=rng.uniform(-0.35,0.35),e2=rng.uniform(-0.35,0.35);
    this.prism_eps=[e1,e2,-(e1+e2)];this.prot_zero=rng.uniform(-0.4,0.4);
    const item=(x,y,ang=0)=>({on:false,pos:[x,y],ang,tapes:[]});
    this.obj={ruler:item(136,170),disk:item(136,96,270),holder:item(150,110),screen:item(136,30),ruler8:item(60,150),tape6:item(40,60)};
    this.order=['screen','holder','disk','ruler8','ruler','tape6'];
    this.tape_on=false;this.tape_held=false;this.tape_a=[50,192];this.tape_b=[170,192];
    this.ftape_a=[-40,6];this.ftape_b=[40,6];this.slider=0;this.laser_fine=0;
    this.hold_item='grating';this.hold_rot=0;this.sel=null;this.level='low';this.laser_on=false;
    this.parchment=false;this.dark=false;this.clock=0;this.t=0;
    this._ph=Array.from({length:9},()=>rng.uniform(0,6.3));this._pc=new Map();
    this.LOCAL=LOCAL;this.COLL=COLL;this.BARREL=BARREL;
    this.segs=[];this.spots=[];this.hits=[];this.shots=[];
  }
  clearPoseCache() { this._pc.clear(); }
  raise_(key) { const i=this.order.indexOf(key);if(i>=0){this.order.splice(i,1);this.order.push(key);} }
  pose(key) {
    if(this._pc.has(key))return this._pc.get(key);
    const o=this.obj[key];if(!o)throw new RangeError('Unknown apparatus');
    let [x,y]=o.pos,a=o.ang;const n=o.tapes.length;
    if(o.on && n<2 && LOCAL[key]){
      const t=this.t,p=this._ph,da=0.26*Math.sin(0.23*t+p[4])+0.09*Math.sin(0.71*t+p[5]);
      if(n===0){x+=0.085*Math.sin(0.31*t+p[0])+0.028*Math.sin(0.83*t+p[1]);y+=0.080*Math.sin(0.27*t+p[2])+0.026*Math.sin(0.97*t+p[3]);a+=da;}
      else{
        const [ta,tb]=o.tapes[0];let u=dirv(a),v=dirv(a+90);const fx=x+u[0]*ta+v[0]*tb,fy=y+u[1]*ta+v[1]*tb;
        a+=0.45*da;u=dirv(a);v=dirv(a+90);x=fx-(u[0]*ta+v[0]*tb);y=fy-(u[1]*ta+v[1]*tb);
      }
    }
    const result=[x,y,a];this._pc.set(key,result);return result;
  }
  local(key,x,y) { const [cx,cy,a]=this.pose(key),u=dirv(a),v=dirv(a+90),d=[x-cx,y-cy];return [dot(d,u),dot(d,v)]; }
  inside(key,x,y) { const h=LOCAL[key];if(!h||!this.obj[key].on)return false;const [a,b]=this.local(key,x,y);return Math.abs(a)<h[0] && Math.abs(b)<h[1]; }
  in_ruler8(x,y) {
    if(!this.obj.ruler8.on||this.order.indexOf('ruler8')<this.order.indexOf('disk'))return false;
    const [a,b]=this.local('ruler8',x,y);return Math.abs(a)<15.6&&Math.abs(b)<1.9;
  }
  wobbly() { return Object.entries(this.obj).some(([key,o])=>o.on&&LOCAL[key]&&o.tapes.length<2); }
  light_phase() {
    if(this.clock<DARK_FROM)return [false,DARK_FROM-this.clock];
    const p=mod(this.clock-DARK_FROM,DARK_EVERY);return p<DARK_LEN?[true,DARK_LEN-p]:[false,DARK_EVERY-p];
  }
  slider_limits() {
    let lo=-27,hi=27;
    for(const [ta] of this.obj.ruler.tapes){if(ta<this.slider)lo=Math.max(lo,ta+6.5);else hi=Math.min(hi,ta-6.5);}
    return [lo,hi];
  }
  pivot() { const [x,y,a]=this.pose('ruler'),u=dirv(a);return [x+u[0]*this.slider,y+u[1]*this.slider]; }
  beam_dir() { return dirv(this.pose('ruler')[2]+90+this.laser_fine); }
  laser() { const p=this.pivot(),d=this.beam_dir();return [p[0]+d[0]*BARREL,p[1]+d[1]*BARREL]; }
  disk_center() { return this.pose('disk').slice(0,2); }
  protractor(q) { const [x,y,a]=this.pose('disk');return mod(Math.atan2(-(q[1]-y),q[0]-x)/RAD-a-this.prot_zero,360); }
  prism_poly() {
    const [cx,cy,base]=this.pose('holder'),rot=base+this.hold_rot,A=60+2*this.prism_eps[0],C=60+2*this.prism_eps[2];
    return [0,2*C,2*C+2*A].map(t=>[cx+2.90*Math.cos((rot+t)*RAD),cy-2.90*Math.sin((rot+t)*RAD)]);
  }
  grating_seg() { const [x,y,rot]=this.pose('holder'),u=dirv(rot+this.hold_rot);return [[x-2.4*u[0],y-2.4*u[1]],[x+2.4*u[0],y+2.4*u[1]]]; }
  screen_seg() { const [x,y,rot]=this.pose('screen'),u=dirv(rot);return [[x-60*u[0],y-60*u[1]],[x+60*u[0],y+60*u[1]]]; }
  active() { if(this.obj.disk.on&&this.level==='low')return 'disk';if(this.obj.holder.on&&this.level==='high')return this.hold_item;return null; }
  trace() {
    this.clearPoseCache();this.segs=[];this.spots=[];this.hits=[];this.shots=[];
    if(this.laser_on&&this.obj.ruler.on)this._air(this.laser(),this.beam_dir(),1,0);
    return {segments:this.segs,segs:this.segs,spots:this.spots,hits:this.hits,shots:this.shots};
  }
  _air(p,d,intensity,depth) {
    if(intensity<1e-6||depth>6)return;
    const active=this.active();let best=1e9,kind=null,extra=null;
    const nearer=(t,k,e=null)=>{if(t&&t<best){best=t;kind=k;extra=e;}};
    if(this.obj.screen.on){const [a,b]=this.screen_seg();nearer(seg_hit(p,d,a,b),'screen',[a,b]);}
    if(active==='disk'){const ts=circ_hit(p,d,this.disk_center(),10);if(ts.length)nearer(Math.min(...ts),'disk');}
    if(this.obj.holder.on&&this.level==='low'){const [x,y]=this.pose('holder'),ts=circ_hit(p,d,[x,y],4.4);if(ts.length)nearer(Math.min(...ts),'block');}
    if(active==='grating'){const [a,b]=this.grating_seg();nearer(seg_hit(p,d,a,b),'grating');}
    if(active==='prism'){const pts=this.prism_poly();for(let i=0;i<3;i++)nearer(seg_hit(p,d,pts[i],pts[(i+1)%3]),'prism');}
    for(const [a,b] of [[[0,0],[ROOM_W,0]],[[0,0],[0,ROOM_D]],[[ROOM_W,0],[ROOM_W,ROOM_D]],[[0,ROOM_D],[ROOM_W,ROOM_D]]])nearer(seg_hit(p,d,a,b),'wall');
    if(!kind)return;
    const q=[p[0]+d[0]*best,p[1]+d[1]*best];this.segs.push([...p,...q,intensity,'air']);
    if(kind==='wall')this.spots.push([...q,intensity]);
    else if(kind==='screen'){
      const [a,b]=extra,length=Math.hypot(b[0]-a[0],b[1]-a[1]),u=[(b[0]-a[0])/length,(b[1]-a[1])/length];
      this.shots.push([(q[0]-a[0])*u[0]+(q[1]-a[1])*u[1]-length/2,intensity]);
    }else if(kind==='disk')this._disk(q,d,intensity,depth);
    else if(kind==='grating')this._grating(q,d,intensity,depth);
    else if(kind==='prism')this._prism(q,d,intensity,depth);
  }
  _disk(q,d,initial,depth) {
    const center=this.disk_center(),n=this.n_disk,nv=norm([q[0]-center[0],q[1]-center[1]]),ci=-dot(d,nv),rs=fresnel_s(ci,1,n),di=refract(d,nv,1,n);
    this.hits.push(q);this._air(q,norm([d[0]+2*ci*nv[0],d[1]+2*ci*nv[1]]),initial*rs,depth+1);
    if(!di)return;
    let intensity=initial*(1-rs),cur=q,cd=di;
    for(let k=0;k<12;k++){
      const ts=circ_hit(cur,cd,center,10);if(!ts.length)break;const distance=Math.max(...ts),next=[cur[0]+cd[0]*distance,cur[1]+cd[1]*distance];
      this.segs.push([...cur,...next,intensity,'glass']);this.hits.push(next);
      const outward=norm([next[0]-center[0],next[1]-center[1]]),inward=outward.map(v=>-v),ci2=-dot(cd,inward),rs2=fresnel_s(ci2,n,1),out=refract(cd,inward,n,1);
      if(out)this._air(next,out,intensity*(1-rs2),depth+1);
      cd=norm([cd[0]+2*ci2*inward[0],cd[1]+2*ci2*inward[1]]);cur=next;intensity*=rs2;if(intensity<1e-6)break;
    }
  }
  _grating(q,d,initial,depth) {
    const [a,b]=this.grating_seg(),[nv,gv,sa]=grating_frame(d,a,b);
    this.segs.push([q[0]-d[0]*0.42,q[1]-d[1]*0.42,q[0]+d[0]*0.06,q[1]+d[1]*0.06,initial,'glass']);
    for(let m=-6;m<=6;m++){
      const sd=m*this.lam_over_d-sa;if(Math.abs(sd)>1)continue;
      const cd=Math.sqrt(1-sd*sd),eff=m===0?0.40:0.26/(1+0.7*Math.abs(m));
      this._air(q,norm([cd*nv[0]-sd*gv[0],cd*nv[1]-sd*gv[1]]),initial*eff,depth+1);
    }
  }
  _prism(q,d,initial,depth) {
    const pts=this.prism_poly(),faces=pts.map((p,i)=>[p,pts[(i+1)%3]]),n=this.n_prism;
    const perpendicular=(p,[a,b])=>Math.abs((p[0]-a[0])*(b[1]-a[1])-(p[1]-a[1])*(b[0]-a[0]))/(Math.hypot(b[0]-a[0],b[1]-a[1])||1);
    const faceNormal=([a,b],ray)=>{const fv=norm([b[0]-a[0],b[1]-a[1]]);let nv=[-fv[1],fv[0]];if(dot(nv,ray)>0)nv=nv.map(x=>-x);return nv;};
    let entry=faces[0];for(const face of faces)if(perpendicular(q,face)<perpendicular(q,entry))entry=face;
    const nv=faceNormal(entry,d),ci=-dot(d,nv),rs=fresnel_s(ci,1,n);
    this._air(q,norm([d[0]+2*ci*nv[0],d[1]+2*ci*nv[1]]),initial*rs,depth+1);
    const cd=refract(d,nv,1,n);if(!cd)return;
    const intensity=initial*(1-rs);let best=1e9,exit=null;
    for(const face of faces){const t=seg_hit(q,cd,...face);if(t&&t<best){best=t;exit=face;}}
    if(!exit)return;const next=[q[0]+cd[0]*best,q[1]+cd[1]*best];this.segs.push([...q,...next,intensity,'glass']);
    const nv2=faceNormal(exit,cd),ci2=-dot(cd,nv2),rs2=fresnel_s(ci2,n,1),out=refract(cd,nv2,n,1);
    if(out)this._air(next,out,intensity*(1-rs2),depth+1);
  }

  // Interaction rules below port LabTab's tape, SAT separation and solid-screen rules.
  screenSide(key) {
    this.clearPoseCache();if(!this.obj.screen.on||!LOCAL[key])return 0;
    const [sx,sy,a]=this.pose('screen'),v=dirv(a+90),[px,py]=this.obj[key].pos;
    return (px-sx)*v[0]+(py-sy)*v[1]>=0?1:-1;
  }
  separate(key) {
    this.clearPoseCache();if(!NOCLASH.includes(key))return;
    const hA=COLL[key];
    for(const other of this.order){
      if(other===key||!NOCLASH.includes(other)||!this.obj[other].on)continue;const hB=COLL[other];
      for(let iteration=0;iteration<4;iteration++){
        this.clearPoseCache();const [ax,ay]=this.obj[key].pos,aa=this.obj[key].ang,[bx,by,ba]=this.pose(other),ua=dirv(aa),va=dirv(aa+90),ub=dirv(ba),vb=dirv(ba+90),delta=[bx-ax,by-ay];let best=null;
        for(const axis of [ua,va,ub,vb]){
          const ra=hA[0]*Math.abs(dot(ua,axis))+hA[1]*Math.abs(dot(va,axis)),rb=hB[0]*Math.abs(dot(ub,axis))+hB[1]*Math.abs(dot(vb,axis)),distance=dot(delta,axis),penetration=ra+rb+0.35-Math.abs(distance);
          if(penetration<=0){best=null;break;}if(!best||penetration<best[0])best=[penetration,axis,distance>=0?1:-1];
        }
        if(!best)break;const [pen,axis,sign]=best;this.obj[key].pos=[ax-axis[0]*pen*sign,ay-axis[1]*pen*sign];
      }
      this.clearPoseCache();
    }
  }
  avoidScreen(key,side) {
    this.clearPoseCache();if(key==='screen'||!side||!this.obj.screen.on||!COLL[key])return;
    const h=COLL[key],[sx,sy,ang]=this.pose('screen'),u=dirv(ang),v=dirv(ang+90),theta=(this.obj[key].ang-ang)*RAD,c=Math.abs(Math.cos(theta)),sn=Math.abs(Math.sin(theta));
    const ra=h[0]*c+h[1]*sn+0.15,radius=h[0]*sn+h[1]*c+0.15+COLL.screen[1],[px,py]=this.obj[key].pos,delta=[px-sx,py-sy],a=dot(delta,u),b=dot(delta,v);
    if(Math.abs(a)>SCREEN_W/2+ra||b*side>=radius)return;
    this.obj[key].pos=[sx+u[0]*a+v[0]*side*radius,sy+u[1]*a+v[1]*side*radius];this.clearPoseCache();
  }
  setMounted(key,on=true,position) {
    if(key==='tape'){
      this.tape_on=!!on;if(on&&point(position)){this.tape_a=[position[0]-60,position[1]+14];this.tape_b=[position[0]+60,position[1]+14];}return this.tape_on;
    }
    const o=this.obj[key];if(!o)return false;o.on=!!on;
    if(o.on){if(point(position))o.pos=position.slice(0,2);this.clearPoseCache();const side=this.screenSide(key);this.avoidScreen(key,side);this.separate(key);}
    if(!o.on&&key==='tape6')this.tape_held=false;this.clearPoseCache();return o.on;
  }
  toggle(key,position) { return this.setMounted(key,key==='tape'?!this.tape_on:!this.obj[key]?.on,position); }
  move(key,position,{removeOutside=true}={}) {
    const o=this.obj[key];if(!o||!o.on||!point(position)||o.tapes.length)return false;
    const side=this.screenSide(key);o.pos=position.slice(0,2);this.clearPoseCache();this.avoidScreen(key,side);this.separate(key);
    if(removeOutside&&outside(o.pos))this.setMounted(key,false);this.clearPoseCache();return true;
  }
  rotate(key,delta) {
    if(!Number.isFinite(delta))return false;
    if(key==='laser')this.laser_fine+=delta;
    else if(key==='holder12b')this.hold_rot=mod(this.hold_rot+delta,360);
    else{
      const o=this.obj[key];if(!o||!LOCAL[key]||!o.on||o.tapes.length>=2)return false;
      o.ang=mod(o.ang+delta,360);this.clearPoseCache();const side=this.screenSide(key);this.avoidScreen(key,side);this.separate(key);
    }
    this.clearPoseCache();return true;
  }
  setSlider(value) { if(!Number.isFinite(value))return this.slider;const [lo,hi]=this.slider_limits();this.slider=Math.max(lo,Math.min(hi,value));return this.slider; }
  peelTape(key,index) { const o=this.obj[key];if(!o||!Number.isInteger(index)||index<0||index>=o.tapes.length)return false;o.tapes.splice(index,1);this.clearPoseCache();return true; }
  stickTape(x,y) {
    if(!this.tape_held||!this.obj.tape6.on||!Number.isFinite(x)||!Number.isFinite(y))return false;
    this.clearPoseCache();
    for(const key of [...this.order].reverse()){
      if(!LOCAL[key]||!this.obj[key].on||!this.inside(key,x,y))continue;
      let [a,b]=this.local(key,x,y);const o=this.obj[key];
      const existing=o.tapes.findIndex(t=>Math.abs(t[0]-a)<1.9&&Math.abs(t[1]-b)<1.3);
      if(existing>=0)return this.peelTape(key,existing);
      if(key==='ruler'&&Math.abs(a-this.slider)<6.6)return true;
      if(!o.tapes.length){const [cx,cy,ang]=this.pose(key);o.pos=[cx,cy];o.ang=ang;this.clearPoseCache();[a,b]=this.local(key,x,y);}
      o.tapes.push([a,b]);this.clearPoseCache();return true;
    }
    return false;
  }
  moveTapeEndpoint(key,position,{removeOutside=true}={}) {
    if(!['tape_a','tape_b','ftape_a','ftape_b'].includes(key)||!point(position))return false;
    this[key]=position.slice(0,2);if(removeOutside&&key.startsWith('tape_')&&outside(position))this.tape_on=false;return true;
  }
  advance(dt,scale=1) {
    if(!Number.isFinite(dt)||dt<0||!Number.isFinite(scale)||scale<0)throw new RangeError('Time step must be finite and nonnegative');
    this.t+=dt*scale;this.clock+=dt*scale;this.clearPoseCache();this.dark=this.light_phase()[0];return this.light_phase();
  }
}
