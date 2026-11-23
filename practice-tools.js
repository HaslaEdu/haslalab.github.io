/* Practice helpers with no page state: the review schedule, suggested times, the custom set filter and the
   progress backup's check and merge. The browser reads window.HL_PRACTICE_TOOLS; the tests require() this file. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.HL_PRACTICE_TOOLS=api;
})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  const DAY_RE=/^\d{4}-\d{2}-\d{2}$/;
  const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
  const isObj=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
  const num=v=>typeof v==='number'&&Number.isFinite(v);

  /* ── review queue: a miss, or a right answer that needed hints, comes back after 1 day; each right answer on a
     due review moves it one box on (3, 7, 21 days); after the last box it leaves the queue. A miss sends it back
     to the first box. ── */
  const REVIEW_DAYS=[1,3,7,21];
  function addDays(day,n){
    const [y,m,d]=day.split('-').map(Number),t=new Date(Date.UTC(y,m-1,d+n));
    return t.toISOString().slice(0,10);
  }
  /* outcome: 'right' | 'hinted' | 'wrong'. meta is what the page needs to find the item again (kind, unit, contest) */
  function reviewUpdate(review,id,outcome,day,meta,at){
    const out={...(review||{})},cur=out[id],stamp=at??Math.floor(Date.now()/1000);
    if(outcome==='wrong'||outcome==='hinted'){
      out[id]={...(cur||{}),...(meta||{}),box:0,due:addDays(day,REVIEW_DAYS[0]),at:stamp};
      return out;
    }
    if(outcome!=='right'||!cur)return out;
    if(cur.due>day)return out;                       /* answered right before it was due: no change */
    const box=(cur.box|0)+1;
    if(box>=REVIEW_DAYS.length){delete out[id];return out;}
    out[id]={...cur,box,due:addDays(day,REVIEW_DAYS[box]),at:stamp};
    return out;
  }
  const dueIds=(review,day)=>Object.entries(review||{}).filter(([,r])=>r&&r.due<=day).sort((a,b)=>a[1].due<b[1].due?-1:a[1].due>b[1].due?1:0).map(([id])=>id);

  /* ── suggested time per problem from its step (1–10): 1.5 min for the easiest school items, 8 min for the hardest
     olympiad items. A Korean exam item keeps its own time when it has one. ── */
  const PACE=[0,90,90,120,150,180,240,300,360,420,480];
  const paceFor=item=>{const s=Math.max(1,Math.min(10,Math.round(Number(item?.s)||3)));return num(item?.sec)&&item.sec>0?item.sec:PACE[s];};
  const clock=sec=>{sec=Math.max(0,Math.round(sec));return Math.floor(sec/60)+':'+String(sec%60).padStart(2,'0');};

  /* ── custom set: filter the loaded items, then put unsolved and not-recently-seen ones first, shuffled ──
     item fields: id, u (unit), s (step), from: 'track:<key>' | 'calc' | 'contest', and for competitions c (key), year.
     opts: {source:'all'|'calc'|'contest'|'track:<key>'|'level:L1'…'level:L4', units:[...] (empty = all), min, max, format:'choice'|'typed',
     contest:'' or a key, yearMin, yearMax}. canType(item) says whether the item takes a typed answer, hasChoices(item)
     whether it has choices to pick from. */
  function matchSet(items,opts,canType,hasChoices){
    const o=opts||{},units=new Set(o.units||[]),min=Number(o.min)||1,max=Number(o.max)||10;
    return (items||[]).filter(i=>{
      if(o.source&&o.source.startsWith('level:')){if(!inLevel(i,o.source.slice(6)))return false;}
      else if(o.source&&o.source!=='all'&&i.from!==o.source)return false;
      if(i.s<min||i.s>max)return false;
      if(i.from==='contest'){
        if(units.size)return false;                   /* competition problems carry no unit */
        if(o.contest&&i.c!==o.contest)return false;
        if(o.yearMin&&i.year<o.yearMin)return false;
        if(o.yearMax&&i.year>o.yearMax)return false;
        return true;
      }
      if(units.size&&!units.has(i.u))return false;
      if(o.format==='typed'&&canType&&!canType(i))return false;
      if(o.format==='choice'&&hasChoices&&!hasChoices(i))return false;
      return true;
    });
  }
  /* recent: {id: unix seconds of the last attempt}; solved: {id: unit}. rand: () => [0,1) */
  function buildSet(items,opts,ctx){
    const c=ctx||{},rand=c.rand||Math.random,now=c.now??Math.floor(Date.now()/1000),recentSec=(c.recentDays??14)*86400;
    const pool=matchSet(items,opts,c.canType,c.hasChoices);
    const tier=i=>(c.recent&&c.recent[i.id]&&now-c.recent[i.id]<recentSec?2:0)+(c.solved&&c.solved[i.id]?1:0);
    const keyed=pool.map(i=>({i,k:tier(i)+rand()}));
    keyed.sort((a,b)=>a.k-b.k);
    const n=Math.max(1,Number(opts?.count)||10);
    return{matches:pool.length,items:keyed.slice(0,n).map(x=>x.i)};
  }

  /* ── study levels: the learner picks one; it decides which problems today's set and the set builder draw from.
     tracks: exam-track keys; calc: the Korean exams' calculation items; contests: competition keys; bank: the
     books & university bank. soon: what the level will hold but the bank does not have yet. ── */
  const STUDY_LEVELS=[
    {key:'L1',name:{ko:'AP · Physics Bowl · F=ma',en:'AP · Physics Bowl · F=ma'},tracks:['ap1','ap2','apcm','fma'],calc:true,contests:[],bank:false,written:false,
      has:{ko:['AP Physics 1 · 2 · C: Mechanics','F=ma 형식','한국 시험 계산 문제'],en:['AP Physics 1, 2 and C: Mechanics','F=ma style','Calculation problems from Korean exams']},
      soon:{ko:['Physics Bowl 기출'],en:['Physics Bowl past papers']}},
    {key:'L2',name:{ko:'JEE',en:'JEE'},tracks:['jeem'],calc:false,contests:[],bank:false,written:false,
      has:{ko:['JEE Main 형식'],en:['JEE Main style']},soon:{ko:['JEE Advanced 기출'],en:['JEE Advanced past papers']}},
    {key:'L3',name:{ko:'올림피아드 (국가 + 국제)',en:'Olympiad (national + international)'},tracks:['usapho'],calc:false,contests:['opho','wopho','physcup','eupho','eotvos'],bank:false,written:true,
      has:{ko:['USAPhO 형식','OPhO','WoPhO','Physics Cup','EuPhO','Eötvös'],en:['USAPhO style','OPhO','WoPhO','Physics Cup','EuPhO','Eötvös']},
      soon:{ko:['국가 선발 시험 기출 (KPhO 등)','IPhO · APhO 기출'],en:['National selection papers (KPhO and others)','IPhO and APhO papers']}},
    {key:'L4',name:{ko:'대학 물리',en:'University physics'},tracks:[],calc:false,contests:['baupc','eupho','physcup'],bank:true,written:true,
      has:{ko:['BAUPC','EuPhO','Physics Cup','교재 · 대학 강의 문제'],en:['BAUPC','EuPhO','Physics Cup','Textbook and university course problems']},soon:{ko:[],en:[]}}
  ];
  const levelInfo=key=>STUDY_LEVELS.find(l=>l.key===key)||STUDY_LEVELS[0];
  /* item.from: 'track:<key>' | 'calc' | 'contest' (with c) | 'bank' */
  function inLevel(item,key){
    const L=levelInfo(key),f=item?.from||'';
    if(f.startsWith('track:'))return L.tracks.includes(f.slice(6));
    if(f==='calc')return L.calc;
    if(f==='contest')return L.contests.includes(item.c);
    if(f==='bank')return L.bank;
    return false;
  }
  /* a first guess from the onboarding answers; the learner can change it */
  function defaultLevel(p){
    if(!p)return 'L1';
    if(p.goal==='olympiad'&&(p.oly|0)>=1)return 'L3';
    if(p.region==='in')return 'L2';
    if(p.level==='uni')return 'L4';
    return 'L1';
  }

  /* ── written answers: the server marks the learner's working against a rubric and returns a fraction of the points.
     fraction >= 0.70 pass, 0.40–0.69 partial, below that retry. XP is the problem's usual XP times 1, 0.5 or 0.15. ── */
  const BANDS=['pass','partial','retry'],BAND_MULT={pass:1,partial:0.5,retry:0.15};
  const bandOf=f=>{const x=Number(f)||0;return x>=0.7-1e-9?'pass':x>=0.4-1e-9?'partial':'retry';};
  /* the usual XP of a problem: school and track items 10 + 2·step, competition items 20 + 5·step, book items 10 + 5·stars */
  function baseXp(item){
    const s=Math.max(1,Math.min(10,Number(item?.s)||3));
    if(item?.kind==='contest')return 20+5*s;
    if(item?.kind==='bank')return 10+5*Math.max(1,Math.min(5,Number(item.stars)||1));
    return 10+2*s;
  }
  const gradedXp=(base,band)=>Math.max(1,Math.round(base*(BAND_MULT[band]??0)));
  /* a second grading of the same problem in a session adds only what the better band is worth beyond the first */
  const gradedGain=(base,band,prevBand)=>Math.max(0,gradedXp(base,band)-(prevBand?gradedXp(base,prevBand):0));
  /* what happens after a grading: pass counts as solved and moves on; partial counts as tried, goes to review
     (as a hinted answer) and moves on; retry offers another go, and moving on sends it to review as a miss */
  function moveOn(band){
    if(band==='pass')return{solved:true,review:'right',result:'solved',next:true,retry:false};
    if(band==='partial')return{solved:false,review:'hinted',result:'missed',next:true,retry:false};
    return{solved:false,review:'wrong',result:'missed',next:false,retry:true};
  }
  /* a unit's step goes up when the last five graded fractions there average 0.60 or more; the count starts again */
  const UNIT_WINDOW=5,UNIT_UP=0.6;
  function pushGraded(hist,unit,fraction){
    const out={...(hist||{})},list=[...(out[unit]||[]),Math.max(0,Math.min(1,Number(fraction)||0))].slice(-UNIT_WINDOW);
    const avg=list.reduce((a,x)=>a+x,0)/list.length,up=list.length>=UNIT_WINDOW&&avg>=UNIT_UP-1e-9;
    out[unit]=up?[]:list;
    return{hist:out,up,avg};
  }

  /* ── pages of working: each is scaled so its long side is at most 1600 px and sent as a JPEG of at most 1.5 MB ── */
  const PAGE_SIDE=1600,PAGE_BYTES=1500000,MAX_PAGES=4;
  function fitSize(w,h,max){
    const m=max||PAGE_SIDE,W=Math.max(1,Math.round(Number(w)||1)),Hh=Math.max(1,Math.round(Number(h)||1)),k=Math.min(1,m/Math.max(W,Hh));
    return{w:Math.max(1,Math.round(W*k)),h:Math.max(1,Math.round(Hh*k)),scale:k};
  }
  /* the size of a data URL as the server counts it: the whole string */
  const dataUrlBytes=u=>typeof u==='string'?u.length:0;
  /* the encodings to try in turn until one fits */
  const ENCODE_STEPS=[[1600,0.8],[1600,0.7],[1400,0.65],[1200,0.6],[1000,0.55],[800,0.5]];
  const pageOk=u=>typeof u==='string'&&u.startsWith('data:image/jpeg;base64,')&&u.length>30&&dataUrlBytes(u)<=PAGE_BYTES;
  /* the problem as the grading endpoint takes it, cut to its limits */
  function gradeItem(o){
    const cut=(v,n)=>typeof v==='string'?v.slice(0,n):undefined;
    const it={id:String(o.id||'').slice(0,80),source:['track','exam','contest','bank'].includes(o.source)?o.source:'track',q:cut(o.q,8000)||''};
    if(o.answer)it.answer=cut(String(o.answer),600);
    if(o.sol)it.sol=cut(o.sol,8000);
    if(Array.isArray(o.choices)&&o.choices.length)it.choices=o.choices.slice(0,8).map(c=>String(c).slice(0,600));
    it.points=Number(o.points)>0?Math.round(o.points):10;
    return it;
  }

  /* ── progress backup: a JSON file with {app, version, exported, state}. Import checks every field and keeps only
     what has the right shape; merging keeps the newer entry for each item ── */
  const APP='haslalab-practice',VERSION=1;
  const FIELDS=['profile','xp','days','level','solved','wrong','skills','bank','contest','review','later','recent','goalDay','diagAt','graded','gradedHist','studyLevel'];
  function exportOf(saved,when){
    const state={};for(const k of FIELDS)if(saved&&saved[k]!==undefined)state[k]=saved[k];
    return{app:APP,version:VERSION,exported:when||new Date().toISOString(),state};
  }
  const mapOf=(v,ok)=>{if(!isObj(v))return undefined;const o={};for(const [k,x] of Object.entries(v))if(typeof k==='string'&&k.length<=120&&ok(x))o[k]=x;return o;};
  const reviewOk=r=>isObj(r)&&typeof r.due==='string'&&DAY_RE.test(r.due)&&Number.isInteger(r.box)&&r.box>=0&&r.box<REVIEW_DAYS.length&&(r.at===undefined||num(r.at));
  const laterOk=r=>isObj(r)&&num(r.at)&&(r.k===undefined||['exam','track','contest'].includes(r.k));
  const gradedOk=g=>isObj(g)&&num(g.fraction)&&g.fraction>=0&&g.fraction<=1&&BANDS.includes(g.band)&&num(g.at);
  const skillOk=k=>isObj(k)&&num(k.rating)&&Number.isInteger(k.n)&&k.n>=0&&(k.right_n===undefined||Number.isInteger(k.right_n))&&(k.last_at===undefined||num(k.last_at));
  /* returns {ok:true, state} or {ok:false, error:'not_json'|'not_backup'|'version'|'empty'} */
  function validateBackup(data){
    let d=data;
    if(typeof d==='string'){try{d=JSON.parse(d);}catch(e){return{ok:false,error:'not_json'};}}
    if(!isObj(d)||d.app!==APP||!isObj(d.state))return{ok:false,error:'not_backup'};
    if(d.version!==VERSION)return{ok:false,error:'version'};
    const s=d.state,out={};
    if(isObj(s.profile)&&typeof s.profile.region==='string')out.profile=s.profile;
    if(num(s.xp)&&s.xp>=0)out.xp=Math.floor(s.xp);
    if(Array.isArray(s.days))out.days=s.days.filter(x=>typeof x==='string'&&DAY_RE.test(x)).slice(-400);
    const maps={level:x=>num(x),solved:x=>typeof x==='string',wrong:x=>num(x),skills:skillOk,review:reviewOk,later:laterOk,recent:x=>num(x)};
    for(const [k,ok] of Object.entries(maps)){const m=mapOf(s[k],ok);if(m)out[k]=m;}
    if(isObj(s.bank))out.bank={done:mapOf(s.bank.done,num)||{},stars:mapOf(s.bank.stars,num)||{}};
    if(isObj(s.contest))out.contest={done:mapOf(s.contest.done,num)||{}};
    if(isObj(s.goalDay)&&typeof s.goalDay.d==='string'&&DAY_RE.test(s.goalDay.d)&&num(s.goalDay.n))out.goalDay={d:s.goalDay.d,n:s.goalDay.n};
    if(num(s.diagAt))out.diagAt=s.diagAt;
    const gm=mapOf(s.graded,gradedOk);if(gm)out.graded=gm;
    const hm=mapOf(s.gradedHist,h=>Array.isArray(h)&&h.length<=UNIT_WINDOW&&h.every(x=>num(x)&&x>=0&&x<=1));if(hm)out.gradedHist=hm;
    if(typeof s.studyLevel==='string'&&/^L[1-4]$/.test(s.studyLevel))out.studyLevel=s.studyLevel;
    if(!Object.keys(out).length)return{ok:false,error:'empty'};
    return{ok:true,state:out};
  }
  /* a and b are both states; for each item the newer one wins (by its own time where it has one, else the larger) */
  function mergeBackup(a,b){
    const A=a||{},B=b||{},out={...A};
    const obj=(x,y,pick)=>{const o={...(x||{})};for(const [k,v] of Object.entries(y||{}))o[k]=own(o,k)?pick(o[k],v):v;return o;};
    const mx=(x,y)=>Math.max(Number(x)||0,Number(y)||0);
    const byAt=f=>(x,y)=>(Number(y?.[f])||0)>(Number(x?.[f])||0)?y:x;
    if(B.profile)out.profile=(Number(B.profile.at)||0)>(Number(A.profile?.at)||0)||!A.profile?B.profile:A.profile;
    if(B.xp!==undefined)out.xp=mx(A.xp,B.xp);
    if(B.days)out.days=[...new Set([...(A.days||[]),...B.days])].sort().slice(-400);
    if(B.level)out.level=obj(A.level,B.level,mx);
    if(B.solved)out.solved=obj(A.solved,B.solved,x=>x);
    if(B.wrong)out.wrong=obj(A.wrong,B.wrong,mx);
    if(B.recent)out.recent=obj(A.recent,B.recent,mx);
    if(B.skills)out.skills=obj(A.skills,B.skills,byAt('last_at'));
    if(B.review)out.review=obj(A.review,B.review,byAt('at'));
    if(B.later)out.later=obj(A.later,B.later,byAt('at'));
    if(B.bank)out.bank={done:obj(A.bank?.done,B.bank.done,mx),stars:obj(A.bank?.stars,B.bank.stars,(x,y)=>y??x)};
    if(B.contest)out.contest={done:obj(A.contest?.done,B.contest.done,mx)};
    if(B.goalDay)out.goalDay=!A.goalDay||B.goalDay.d>A.goalDay.d?B.goalDay:A.goalDay.d===B.goalDay.d?{d:A.goalDay.d,n:mx(A.goalDay.n,B.goalDay.n)}:A.goalDay;
    if(B.diagAt!==undefined)out.diagAt=mx(A.diagAt,B.diagAt);
    if(B.graded)out.graded=obj(A.graded,B.graded,byAt('at'));
    if(B.gradedHist)out.gradedHist={...(A.gradedHist||{}),...B.gradedHist};
    if(B.studyLevel&&!A.studyLevel)out.studyLevel=B.studyLevel;
    return out;
  }
  return{STUDY_LEVELS,levelInfo,inLevel,defaultLevel,BANDS,BAND_MULT,bandOf,baseXp,gradedXp,gradedGain,moveOn,UNIT_WINDOW,UNIT_UP,pushGraded,PAGE_SIDE,PAGE_BYTES,MAX_PAGES,fitSize,dataUrlBytes,ENCODE_STEPS,pageOk,gradeItem,REVIEW_DAYS,addDays,reviewUpdate,dueIds,PACE,paceFor,clock,matchSet,buildSet,APP,VERSION,FIELDS,exportOf,validateBackup,mergeBackup};
});
