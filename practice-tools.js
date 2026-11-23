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
  const FIELDS=['profile','xp','days','level','solved','wrong','skills','bank','contest','review','later','recent','goalDay','diagAt','graded','gradedHist','studyLevel','streakCfg','intro'];
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
    if(isObj(s.streakCfg)&&Array.isArray(s.streakCfg.pauses))out.streakCfg={pauses:s.streakCfg.pauses.filter(pauseOk).slice(-12)};
    const im=mapOf(s.intro,num);if(im)out.intro=im;
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
    if(B.streakCfg){const seen=new Set(),list=[];for(const p of [...pausesOf(A.streakCfg),...pausesOf(B.streakCfg)]){const k=p.from+p.to;if(!seen.has(k)){seen.add(k);list.push(p);}}out.streakCfg={pauses:list.sort((x,y)=>x.from<y.from?-1:1).slice(-12)};}
    if(B.intro)out.intro=obj(A.intro,B.intro,mx);
    return out;
  }
  /* ── streak: a day missed does not end it once a week (the week's freeze, used by itself and back each Monday), and
     an exam-time pause holds it for up to 14 days. Nothing is spent on mistakes: there are no hearts or energy.
     cfg: {pauses:[{from,to}]}. The freeze is worked out from the days, so it needs no storage. ── */
  const PAUSE_DAYS=14,PAUSE_GAP=7;
  const weekOf=day=>{const [y,m,d]=day.split('-').map(Number),dow=new Date(Date.UTC(y,m-1,d)).getUTCDay();return addDays(day,-((dow+6)%7));};
  const pauseOk=p=>isObj(p)&&typeof p.from==='string'&&typeof p.to==='string'&&DAY_RE.test(p.from)&&DAY_RE.test(p.to)&&p.from<=p.to&&p.to<=addDays(p.from,PAUSE_DAYS-1);
  const pausesOf=cfg=>(Array.isArray(cfg?.pauses)?cfg.pauses:[]).filter(pauseOk);
  function activePause(cfg,day){return pausesOf(cfg).find(p=>p.from<=day&&day<=p.to)||null;}
  function streakInfo(days,cfg,day){
    const set=new Set((days||[]).filter(x=>typeof x==='string')),pauses=pausesOf(cfg);
    const paused=d=>pauses.some(p=>p.from<=d&&d<=p.to);
    let d=set.has(day)?day:addDays(day,-1),n=0,pending=[];const used=[],weeks=new Set();
    for(let i=0;i<1000;i++,d=addDays(d,-1)){
      if(set.has(d)){n++;used.push(...pending);pending=[];continue;}
      if(paused(d))continue;
      const w=weekOf(d);if(weeks.has(w))break;
      weeks.add(w);pending.push(d);
    }
    const week=weekOf(day),pause=activePause(cfg,day);
    return{n,frozen:used.sort(),freezeLeft:!used.some(x=>weekOf(x)===week),pause,canPause:!pause&&pauseAllowed(cfg,day)};
  }
  /* a new pause needs PAUSE_GAP days since the last one ended, so pauses cannot be chained */
  const pauseAllowed=(cfg,day)=>!pausesOf(cfg).some(p=>p.to>=addDays(day,-PAUSE_GAP));
  function pauseStart(cfg,day){
    if(!pauseAllowed(cfg,day))return null;
    return{...(cfg||{}),pauses:[...pausesOf(cfg),{from:day,to:addDays(day,PAUSE_DAYS-1)}].slice(-12)};
  }
  function pauseStop(cfg,day){
    const list=pausesOf(cfg).map(p=>p.from<=day&&day<=p.to?(p.from===day?null:{from:p.from,to:addDays(day,-1)}):p).filter(Boolean);
    return{...(cfg||{}),pauses:list};
  }

  /* ── drafts: the pad's strokes and the chosen pages for one problem, kept in this browser until it is graded ── */
  const DRAFT_POINTS=40000,DRAFT_KEEP=6,DRAFT_DAYS=14,DRAFT_LOCAL_BYTES=300000;
  function compactStrokes(strokes){
    const out=[];let total=0;
    for(const st of Array.isArray(strokes)?strokes:[]){
      if(!st||!Array.isArray(st.pts)||!st.pts.length)continue;
      const room=DRAFT_POINTS-total;if(room<=0)break;
      const pts=st.pts.slice(0,room).filter(p=>Array.isArray(p)&&num(p[0])&&num(p[1])).map(p=>[Math.round(p[0]),Math.round(p[1])]);
      if(!pts.length)continue;
      total+=pts.length;out.push({tool:st.tool==='eraser'?'eraser':'pen',w:Math.max(1,Math.min(60,Number(st.w)||4)),pts});
    }
    return out;
  }
  function draftOf(id,o,at){
    const d={id:String(id||'').slice(0,120),at:num(at)?at:Math.floor(Date.now()/1000),pages:(o?.pages||[]).filter(pageOk).slice(0,MAX_PAGES),strokes:compactStrokes(o?.strokes)};
    if(isObj(o?.meta))d.meta=o.meta;if(typeof o?.t==='string')d.t=o.t.slice(0,120);
    return d;
  }
  const draftEmpty=d=>!d||(!d.pages?.length&&!d.strokes?.length);
  const draftOk=(d,now)=>isObj(d)&&typeof d.id==='string'&&d.id.length>0&&num(d.at)&&(now==null||now-d.at<=DRAFT_DAYS*86400)&&Array.isArray(d.pages)&&d.pages.every(pageOk)&&d.pages.length<=MAX_PAGES&&
    Array.isArray(d.strokes)&&d.strokes.every(st=>isObj(st)&&Array.isArray(st.pts));
  /* which drafts to drop: anything older than DRAFT_DAYS, and all but the newest DRAFT_KEEP */
  function pruneDrafts(list,now){
    const ok=(list||[]).filter(d=>draftOk(d,now)).sort((a,b)=>b.at-a.at),keep=new Set(ok.slice(0,DRAFT_KEEP).map(d=>d.id));
    return{keep:[...keep],drop:(list||[]).map(d=>d?.id).filter(id=>typeof id==='string'&&!keep.has(id))};
  }
  /* where IndexedDB is missing: localStorage, strokes first, pages only while the whole draft stays small */
  function localDraft(d){
    const size=x=>JSON.stringify(x).length;
    if(size(d)<=DRAFT_LOCAL_BYTES)return d;
    const noPages={...d,pages:[]};if(size(noPages)<=DRAFT_LOCAL_BYTES)return noPages;
    return null;
  }

  /* ── the card before a unit's first problems: what the unit covers, its key formula, the guide chapter and the concept
     simulation where there is one ── */
  const C=(ko,en,f,sim)=>({ko,en,f,sim});
  const UNIT_CARDS={
    'mechanics/kinematics':C('위치, 속도, 가속도로 운동을 나타냅니다. 등가속도 운동과 포물선 운동이 중심입니다.','Describe motion with position, velocity and acceleration: constant acceleration and projectiles.','x=x_0+v_0t+\\tfrac12at^2,\\quad v^2=v_0^2+2a\\,\\Delta x','projectile'),
    'mechanics/newton':C('물체에 작용하는 힘을 모두 그리고, 알짜힘으로 가속도를 구합니다. 마찰과 빗면도 다룹니다.','Draw every force on a body and get its acceleration from the net force, with friction and slopes.','\\sum\\vec F=m\\vec a','pulley-cart'),
    'mechanics/energy':C('힘이 한 일과 운동 에너지, 위치 에너지의 관계를 씁니다.','Relate the work done by forces to kinetic and potential energy.','W=\\Delta K,\\quad K+U=\\text{const}'),
    'mechanics/momentum':C('충격량과 운동량, 충돌 전후의 운동량 보존을 다룹니다.','Impulse, momentum and its conservation in collisions.','\\vec J=\\Delta\\vec p,\\quad \\sum\\vec p_i=\\sum\\vec p_f','collision'),
    'mechanics/circular':C('원을 따라 도는 물체에는 중심을 향하는 알짜힘이 필요합니다.','A body moving on a circle needs a net force towards the centre.','a_c=\\frac{v^2}{r}=\\omega^2r','hemisphere'),
    'mechanics/gravitation':C('만유인력과 원궤도, 케플러 법칙, 탈출 속도를 다룹니다.','Universal gravitation, circular orbits, Kepler’s laws and escape speed.','F=\\frac{GMm}{r^2},\\quad T^2\\propto a^3'),
    'mechanics/statics':C('정지한 물체는 힘의 합과 돌림힘의 합이 모두 0입니다.','A body at rest has zero net force and zero net torque.','\\sum\\vec F=0,\\quad \\sum\\tau=0'),
    'mechanics/noninertial':C('가속하는 좌표계에서는 관성력을 더해 뉴턴 법칙을 씁니다.','In an accelerating frame, add the inertial force and use Newton’s laws.','\\vec F_{\\text{in}}=-m\\vec a_{\\text{frame}}'),
    'mechanics/rigid_body':C('관성 모멘트, 돌림힘과 각가속도, 각운동량 보존을 다룹니다.','Moment of inertia, torque and angular acceleration, conservation of angular momentum.','\\tau=I\\alpha,\\quad L=I\\omega'),
    'mechanics/fluids':C('압력, 부력, 연속 방정식과 베르누이 방정식을 다룹니다.','Pressure, buoyancy, continuity and Bernoulli’s equation.','p+\\tfrac12\\rho v^2+\\rho gh=\\text{const}'),
    'waves/shm':C('복원력이 변위에 비례하면 단진동을 합니다. 용수철과 진자가 대표입니다.','A restoring force proportional to displacement gives simple harmonic motion: springs and pendulums.','T=2\\pi\\sqrt{\\frac mk},\\quad T=2\\pi\\sqrt{\\frac Lg}','pendulum'),
    'waves/wave_motion':C('파장, 진동수, 속력의 관계와 파동 그래프 읽기를 다룹니다.','Wavelength, frequency and speed, and reading wave graphs.','v=f\\lambda'),
    'waves/sound':C('소리의 세기와 높이, 음원이나 관찰자가 움직일 때의 도플러 효과를 다룹니다.','Loudness and pitch, and the Doppler shift when the source or listener moves.','f\'=f\\,\\frac{v\\pm v_o}{v\\mp v_s}'),
    'waves/superposition':C('두 파동이 겹치는 간섭, 양 끝이 고정된 줄의 정상파와 공명을 다룹니다.','Waves adding up, standing waves on a string fixed at both ends, and resonance.','\\lambda_n=\\frac{2L}{n}'),
    'optics/refraction':C('반사 법칙, 굴절 법칙, 전반사의 임계각을 다룹니다.','The law of reflection, Snell’s law and the critical angle.','n_1\\sin\\theta_1=n_2\\sin\\theta_2'),
    'optics/lenses':C('렌즈와 거울이 만드는 상의 위치와 배율을 구합니다.','Find where lenses and mirrors form images, and how large.','\\frac1a+\\frac1b=\\frac1f,\\quad m=-\\frac ba'),
    'optics/interference':C('이중 슬릿, 얇은 막, 회절에서 밝은 무늬와 어두운 무늬의 조건을 구합니다.','Conditions for bright and dark fringes in double slits, thin films and diffraction.','d\\sin\\theta=m\\lambda'),
    'optics/polarization':C('편광판을 지난 빛의 세기와 반사로 생기는 편광을 다룹니다.','Light through polarisers, and polarisation by reflection.','I=I_0\\cos^2\\theta'),
    'em/electrostatics':C('쿨롱 법칙과 전기장, 여러 전하가 만드는 전기장의 합을 다룹니다.','Coulomb’s law, the electric field and adding the fields of several charges.','F=k\\frac{q_1q_2}{r^2},\\quad \\vec E=\\frac{\\vec F}{q}','charges'),
    'em/capacitors':C('전위와 전위차, 축전기의 전기 용량과 저장 에너지를 다룹니다.','Potential and potential difference, capacitance and stored energy.','Q=CV,\\quad U=\\tfrac12CV^2'),
    'em/dc_circuits':C('옴의 법칙, 저항의 직렬 · 병렬 연결, 소비 전력을 다룹니다.','Ohm’s law, resistors in series and parallel, and power.','V=IR,\\quad P=IV'),
    'em/magnetic_field':C('직선 전류, 원형 전류, 솔레노이드가 만드는 자기장을 다룹니다.','The magnetic field of a straight wire, a loop and a solenoid.','B=\\frac{\\mu_0I}{2\\pi r},\\quad B=\\mu_0nI'),
    'em/lorentz':C('자기장 속에서 움직이는 전하와 전류가 받는 힘을 다룹니다.','The force on moving charges and currents in a magnetic field.','\\vec F=q\\vec v\\times\\vec B,\\quad r=\\frac{mv}{qB}'),
    'em/induction':C('자기 선속이 변하면 유도 기전력이 생깁니다. 렌츠 법칙으로 방향을 정합니다.','A changing magnetic flux induces an emf; Lenz’s law gives its direction.','\\varepsilon=-\\frac{d\\Phi}{dt}'),
    'em/ac_circuits':C('교류에서 저항, 코일, 축전기의 리액턴스와 공명을 다룹니다.','Reactance of resistors, coils and capacitors in AC, and resonance.','\\omega_0=\\frac1{\\sqrt{LC}}'),
    'em/em_waves':C('전자기파의 종류와 성질, 빛의 속력을 다룹니다.','Kinds and properties of electromagnetic waves, and the speed of light.','c=f\\lambda=\\frac1{\\sqrt{\\mu_0\\varepsilon_0}}'),
    'em/magnetic_materials':C('강자성체, 상자성체, 반자성체가 자기장에 반응하는 방식을 다룹니다.','How ferromagnetic, paramagnetic and diamagnetic materials respond to a field.','\\vec B=\\mu_0(\\vec H+\\vec M)'),
    'thermal/ideal_gas':C('이상 기체의 압력, 부피, 온도 사이의 관계를 다룹니다.','How pressure, volume and temperature of an ideal gas are related.','pV=nRT'),
    'thermal/first_law':C('열, 일, 내부 에너지의 관계와 여러 열역학 과정을 다룹니다.','Heat, work and internal energy, and the common thermodynamic processes.','\\Delta U=Q-W'),
    'thermal/heat_engines':C('열기관이 한 일과 효율, 카르노 기관의 최대 효율을 다룹니다.','Work and efficiency of heat engines, and the Carnot limit.','e=\\frac{W}{Q_H}\\le 1-\\frac{T_C}{T_H}'),
    'thermal/heat_transfer':C('전도, 대류, 복사로 열이 전달되는 빠르기를 다룹니다.','How fast heat moves by conduction, convection and radiation.','P=kA\\frac{\\Delta T}{L},\\quad P=\\sigma AT^4'),
    'thermal/kinetic_theory':C('기체 분자의 운동으로 압력과 온도를 설명합니다.','Explain pressure and temperature from the motion of gas molecules.','\\tfrac12m\\overline{v^2}=\\tfrac32k_BT'),
    'modern/special_relativity':C('빛의 속력이 일정하다는 데서 시간 지연, 길이 수축, 질량-에너지 관계가 나옵니다.','From a constant speed of light: time dilation, length contraction and mass-energy.','\\Delta t=\\gamma\\Delta t_0,\\quad E=mc^2'),
    'modern/general_relativity':C('등가 원리와 중력에 의한 시간 지연, 빛의 휘어짐을 다룹니다.','The equivalence principle, gravitational time dilation and the bending of light.','\\frac{\\Delta f}{f}=\\frac{gh}{c^2}'),
    'modern/photon':C('빛은 광자로 에너지를 주고받습니다. 광전 효과가 대표입니다.','Light exchanges energy in photons, as in the photoelectric effect.','E=hf,\\quad K_{\\max}=hf-W'),
    'modern/matter_waves':C('입자도 파동처럼 행동합니다. 드브로이 파장과 불확정성 원리를 다룹니다.','Particles behave as waves: the de Broglie wavelength and the uncertainty principle.','\\lambda=\\frac hp,\\quad \\Delta x\\,\\Delta p\\ge\\frac\\hbar2'),
    'modern/atoms':C('원자의 에너지 준위와 전자가 준위를 옮길 때 나오는 빛을 다룹니다.','Atomic energy levels and the light emitted when an electron changes level.','hf=E_i-E_f'),
    'modern/nuclear':C('핵반응, 방사성 붕괴와 반감기, 질량 결손을 다룹니다.','Nuclear reactions, radioactive decay and half-life, and mass defect.','N=N_0\\left(\\tfrac12\\right)^{t/T_{1/2}}'),
    'modern/solids':C('에너지띠, 도체와 반도체, 다이오드의 원리를 다룹니다.','Energy bands, conductors and semiconductors, and how a diode works.','E_g=E_c-E_v'),
    'experiment/uncertainty':C('측정값의 불확도를 구하고 계산 결과까지 전파합니다.','Estimate the uncertainty of a measurement and carry it through a calculation.','\\frac{\\delta f}{f}=\\sqrt{\\left(\\frac{\\delta x}{x}\\right)^2+\\left(\\frac{\\delta y}{y}\\right)^2}'),
    'experiment/graphs':C('데이터를 직선이 되도록 바꿔 그리고 기울기와 절편으로 값을 구합니다.','Plot data so it falls on a line, then read values from the slope and intercept.','y=mx+b'),
    'experiment/design':C('변인을 정하고 통제해 원하는 관계를 측정하는 실험을 세웁니다.','Choose and control variables to measure the relation you want.','\\text{independent}\\to\\text{dependent},\\ \\text{others fixed}'),
    'math/vectors':C('벡터의 합과 분해, 내적과 외적을 다룹니다.','Adding and resolving vectors, dot and cross products.','\\vec a\\cdot\\vec b=ab\\cos\\theta'),
    'math/calculus':C('미분은 변화율, 적분은 쌓인 양입니다. 물리 식에 바로 씁니다.','Derivatives are rates and integrals are totals, used straight in physics.','v=\\frac{dx}{dt},\\quad x=\\int v\\,dt'),
    'math/approximation':C('차원 분석과 작은 값 근사로 답의 꼴과 크기를 빨리 구합니다.','Use dimensions and small-quantity approximations to find the form and size of an answer.','(1+x)^n\\approx1+nx'),
    'math/ode':C('물리 법칙을 미분방정식으로 세우고 지수 함수나 삼각 함수 해를 찾습니다.','Write physical laws as differential equations and solve them with exponentials or sines.','\\ddot x=-\\omega^2x\\Rightarrow x=A\\cos(\\omega t+\\varphi)')
  };
  const unitCard=unit=>UNIT_CARDS[unit]||null;
  const guideHref=unit=>'/#/learn/guide/'+String(unit||'');
  const simHref=sim=>'/#/learn/concepts?sim='+encodeURIComponent(sim);

  /* ── the account's state and this browser's, merged so neither loses progress (the server's practice-progress.js
     mergeState is the same rule). Used on every sign-in, including the first one, when the account is still empty ── */
  function accountMerge(a,b){
    const A=a||{},B=b||{},obj=(x,y,f)=>{const o={...(x||{})};for(const[k,v]of Object.entries(y||{}))o[k]=own(o,k)?f(o[k],v):v;return o;},mx=(x,y)=>Math.max(Number(x)||0,Number(y)||0);
    const newer=(x,y)=>(Number(y?.at)||0)>(Number(x?.at)||0)?y:x||y;
    return{profile:newer(A.profile,B.profile),xp:mx(A.xp,B.xp),days:[...new Set([...(A.days||[]),...(B.days||[])])].sort().slice(-400),level:obj(A.level,B.level,mx),solved:obj(A.solved,B.solved,x=>x),wrong:obj(A.wrong,B.wrong,mx),
      bank:{done:obj(A.bank?.done,B.bank?.done,mx),stars:obj(A.bank?.stars,B.bank?.stars,(x,y)=>y??x)},contest:{done:obj(A.contest?.done,B.contest?.done,mx)}};
  }
  /* the account's ratings join this browser's: the one with more answers behind it wins */
  function skillsMerge(local,server){
    const out={...(local||{})};
    for(const k of Array.isArray(server)?server:[])if(k&&typeof k.unit==='string'&&(!out[k.unit]||(Number(k.n)||0)>=(Number(out[k.unit].n)||0)))out[k.unit]=k;
    return out;
  }

  return{PAUSE_DAYS,PAUSE_GAP,weekOf,activePause,streakInfo,pauseAllowed,pauseStart,pauseStop,
    DRAFT_POINTS,DRAFT_KEEP,DRAFT_DAYS,DRAFT_LOCAL_BYTES,compactStrokes,draftOf,draftEmpty,draftOk,pruneDrafts,localDraft,
    UNIT_CARDS,unitCard,guideHref,simHref,accountMerge,skillsMerge,
    STUDY_LEVELS,levelInfo,inLevel,defaultLevel,BANDS,BAND_MULT,bandOf,baseXp,gradedXp,gradedGain,moveOn,UNIT_WINDOW,UNIT_UP,pushGraded,PAGE_SIDE,PAGE_BYTES,MAX_PAGES,fitSize,dataUrlBytes,ENCODE_STEPS,pageOk,gradeItem,REVIEW_DAYS,addDays,reviewUpdate,dueIds,PACE,paceFor,clock,matchSet,buildSet,APP,VERSION,FIELDS,exportOf,validateBackup,mergeBackup};
});
