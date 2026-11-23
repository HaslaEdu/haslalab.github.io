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
     opts: {source:'all'|'calc'|'contest'|'track:<key>', units:[...] (empty = all), min, max, format:'choice'|'typed',
     contest:'' or a key, yearMin, yearMax}. canType(item) says whether the item takes a typed answer, hasChoices(item)
     whether it has choices to pick from. */
  function matchSet(items,opts,canType,hasChoices){
    const o=opts||{},units=new Set(o.units||[]),min=Number(o.min)||1,max=Number(o.max)||10;
    return (items||[]).filter(i=>{
      if(o.source&&o.source!=='all'&&i.from!==o.source)return false;
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

  /* ── progress backup: a JSON file with {app, version, exported, state}. Import checks every field and keeps only
     what has the right shape; merging keeps the newer entry for each item ── */
  const APP='haslalab-practice',VERSION=1;
  const FIELDS=['profile','xp','days','level','solved','wrong','skills','bank','contest','review','later','recent','goalDay','diagAt'];
  function exportOf(saved,when){
    const state={};for(const k of FIELDS)if(saved&&saved[k]!==undefined)state[k]=saved[k];
    return{app:APP,version:VERSION,exported:when||new Date().toISOString(),state};
  }
  const mapOf=(v,ok)=>{if(!isObj(v))return undefined;const o={};for(const [k,x] of Object.entries(v))if(typeof k==='string'&&k.length<=120&&ok(x))o[k]=x;return o;};
  const reviewOk=r=>isObj(r)&&typeof r.due==='string'&&DAY_RE.test(r.due)&&Number.isInteger(r.box)&&r.box>=0&&r.box<REVIEW_DAYS.length&&(r.at===undefined||num(r.at));
  const laterOk=r=>isObj(r)&&num(r.at)&&(r.k===undefined||['exam','track','contest'].includes(r.k));
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
    return out;
  }
  return{REVIEW_DAYS,addDays,reviewUpdate,dueIds,PACE,paceFor,clock,matchSet,buildSet,APP,VERSION,FIELDS,exportOf,validateBackup,mergeBackup};
});
