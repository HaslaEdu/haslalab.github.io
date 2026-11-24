/* This week's set (the Olympiad home, #/olympiad): five competition problems picked from the learner's own record.
   Nothing here calls a model: each choice comes from the ratings the practice page already keeps (one Elo-style
   rating per unit, practice.js record()), the recent answers (today's problems included) and the problems a
   learner got right lately, and each pick carries the reason it was chosen.

   The rules, in order:
   - level: the ratings' average step (weighted by answers) once there are 5 answers, else the study level's first
     step (L3, the Olympiad level: step 7). Recent accuracy (the last 30 answers, newer ones weigh more) moves it one
     step up above 75 % and one step down below 45 %, once there are 5 answers. That is the target step.
   - units: a unit is known once it has 3 rated answers or 2 recent ones. Its weakness is how far its rating sits
     below the target, plus 2 for each recent miss there, minus 1 for each recent right answer.
   - picks: 2 problems from the weakest unit and 1 from the second (a problem missed lately comes back first, at
     most one, and only within a step of the target), 1 at the target from a middle unit, 1 a step above from the strongest unit left. Too few known units:
     units not tried yet fill in. Problems got right in the last 30 days, reported ones and the week's earlier sets
     are left out. Within a unit the learner's national competition goes first when it has a problem near the step.
   - no record at all: a starter set across the core units at the level's first step.
   - the set stays for the ISO week (Korean time, from Monday), seeded by the week and the account (or a random id
     kept on this device); when all five are done a new set can be drawn.
   The problems (practice/weekly-pool.json) are built by tools/build-site-catalogue.cjs from the transcribed
   competition problems and the USAPhO-style track; a competition problem's unit is estimated from the learning
   path's keywords (unitOfText) and its step is the competition's, one less in the first third of a paper and one
   more in the last. The browser reads window.HL_WEEKLY_SET; the tests require() this file. */
(function(root,factory){
  const api=factory(root);
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.HL_WEEKLY_SET=api;
})(typeof globalThis==='object'?globalThis:this,function(root){
  'use strict';
  const POOL_V="6d8ffb0a42be";   /* practice/weekly-pool.json's digest, stamped by tools/build-site-catalogue.cjs */
  const POOL_URL='practice/weekly-pool.json?v='+POOL_V;
  const LP=()=>root.HL_LEARN_PATH||(typeof require==='function'?require('./learn-path.js'):null);

  const SIZE=5,WINDOW=30,DECAY=0.93,MIN_ANSWERS=5,UP=0.75,DOWN=0.45,SOLVED_DAYS=30,KNOWN_RATED=3,KNOWN_RECENT=2;
  const LEVEL_STEP={L1:6,L2:6,L3:7,L4:8};
  /* the competitions a country selects its team with, when the bank has them */
  const NATIONAL={hu:['eotvos'],us:['usapho'],kr:['kpho']};
  /* the starter set's units: mechanics, electricity, oscillations, heat and optics first */
  const CORE=['mechanics/newton','em/electrostatics','waves/shm','thermal/ideal_gas','optics/lenses','mechanics/energy','mechanics/momentum','em/dc_circuits','em/magnetic_field','thermal/first_law','optics/refraction','mechanics/rigid_body'];
  const stepRating=s=>1000+100*s,ratingStep=r=>Math.max(1,Math.min(10,Math.round((r-1000)/100)));
  const clamp=(x,lo,hi)=>Math.max(lo,Math.min(hi,x));
  const isObj=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
  const ID=/^[a-z0-9]+-[A-Za-z0-9~._-]{1,60}$/;

  /* FNV-1a: the same seed and id give the same order on every device */
  function hash(s){let h=0x811c9dc5;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,0x01000193)>>>0;}return h>>>0;}

  /* the ISO week in Korean time: a new set every Monday 00:00 KST */
  function weekKey(ms){
    const d=new Date((Number(ms)||0)+9*3600e3),day=(d.getUTCDay()+6)%7;
    const th=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate()-day+3));
    const y=th.getUTCFullYear(),first=new Date(Date.UTC(y,0,4));
    const w=1+Math.round(((th-first)/86400e3-3+((first.getUTCDay()+6)%7))/7);
    return y+'-W'+String(w).padStart(2,'0');
  }

  /* a unit from a problem's title and text: each learning-path keyword counts 4 in the title and once (up to three
     times) in the text; the subtopic with the highest count wins, none when nothing matches */
  function unitOfText(title,body){
    const P=LP();if(!P)return null;
    const T=String(title||'').toLowerCase(),B=String(body||'').toLowerCase();
    const count=(s,w)=>{let n=0,i=0;while(n<3&&(i=s.indexOf(w,i))>=0){n++;i+=w.length;}return n;};
    let best=null;
    for(const a of P.AREAS)for(const sub of a.subtopics){
      let score=0;for(const kw of sub.kw){const w=kw.toLowerCase();if(w.length>=2)score+=4*count(T,w)+count(B,w);}
      if(score>0&&(!best||score>best.score))best={u:a.key+'/'+sub.key,score};
    }
    return best?best.u:null;
  }

  /* ── what the learner has done: this browser's practice state (localStorage hlPractice) joined with the account's
     (GET /api/practice/state and /api/practice/recent), as practice.js joins them ── */
  function mergeSkills(local,server){
    const out={...(isObj(local)?local:{})};
    for(const k of Array.isArray(server)?server:[])if(k&&typeof k.unit==='string'&&(!out[k.unit]||(Number(k.n)||0)>=(Number(out[k.unit].n)||0)))out[k.unit]=k;
    return out;
  }
  const okOf=r=>r==='right'||r==='solved'?true:r==='wrong'||r==='missed'?false:null;
  /* attempts newest first: {id, u (unit or ''), ok, at (seconds)}. The account's recent answers, the ones still waiting
     to be sent, and, for answers already sent from this device, its record of when each problem was last tried and
     how it went (solved, wrong, contest.done) */
  function attemptsOf(o){
    const out=[],seen=new Set(),push=(id,u,ok,at)=>{
      if(!ID.test(id||'')||typeof ok!=='boolean'||!Number.isFinite(at))return;
      const key=id+'@'+Math.round(at/120);if(seen.has(key))return;seen.add(key);
      out.push({id,u:typeof u==='string'&&!u.startsWith('contest/')&&!u.endsWith('/*')?u:'',ok,at});
    };
    for(const a of [...(o.server||[]),...(o.queue||[])])if(a)push(a.item_id||a.id,a.unit,okOf(a.result),Number(a.at));
    const local=o.local||{},done=local.contest?.done||{},solved=local.solved||{},wrong=local.wrong||{};
    for(const [id,at] of Object.entries(local.recent||{})){
      if(out.some(a=>a.id===id&&Math.abs(a.at-at)<600))continue;
      const ok=id in done?done[id]===1:wrong[id]&&wrong[id]>=at-60?false:solved[id]?true:null;
      if(ok!==null)push(id,typeof solved[id]==='string'?solved[id]:'',ok,Number(at));
    }
    return out.sort((a,b)=>b.at-a.at);
  }
  /* everything select() needs from the two records */
  function inputsFrom({local,serverState,serverSkills,serverAttempts,reports}={}){
    const L=isObj(local)?local:{},S=isObj(serverState)?serverState:{};
    const solvedEver=new Set([...Object.keys(L.solved||{}),...Object.keys(S.solved||{}),
      ...Object.entries({...(S.contest?.done||{}),...(L.contest?.done||{})}).filter(([,v])=>v===1).map(([k])=>k)]);
    const level=/^L[1-4]$/.test(L.studyLevel||'')?L.studyLevel:'L3';
    return{skills:mergeSkills(L.skills,serverSkills),attempts:attemptsOf({server:serverAttempts,queue:L.queue,local:L}),solvedEver,
      reported:new Set((Array.isArray(reports)?reports:[]).map(r=>r&&(r.id||r.item_id)).filter(Boolean)),level};
  }

  /* ── the learner's level and units ── */
  function model(o,pool){
    const atts=o.attempts||[],win=atts.slice(0,WINDOW);
    let sw=0,so=0;win.forEach((a,i)=>{const w=DECAY**i;sw+=w;if(a.ok)so+=w;});
    const accuracy=win.length>=MIN_ANSWERS?so/sw:null;
    const rated=Object.values(o.skills||{}).filter(k=>isObj(k)&&Number(k.n)>0&&Number.isFinite(Number(k.rating)));
    const answers=rated.reduce((n,k)=>n+Number(k.n),0);
    const levelStep=LEVEL_STEP[o.level]||LEVEL_STEP.L3;
    const fromRatings=answers>=MIN_ANSWERS?ratingStep(rated.reduce((x,k)=>x+Number(k.rating)*Number(k.n),0)/answers):null;
    const base=fromRatings??levelStep,adjust=accuracy==null?0:accuracy>UP?1:accuracy<DOWN?-1:0;
    const steps=pool.map(i=>i.s),lo=Math.min(...steps),hi=Math.max(...steps);
    const target=clamp(base+adjust,lo,Math.max(lo,hi-1));
    const byId=new Map(pool.map(i=>[i.id,i])),unitOf=a=>byId.get(a.id)?.u||a.u;
    const units={};
    for(const u of new Set(pool.map(i=>i.u))){
      const k=o.skills?.[u],rec=win.filter(a=>unitOf(a)===u),rW=rec.filter(a=>!a.ok).length,rR=rec.length-rW;
      const n=k&&Number(k.n)>0?Number(k.n):0,rating=n?Number(k.rating):stepRating(target);
      units[u]={u,n,recent:rec.length,wrong:rW,right:rR,rating,known:n>=KNOWN_RATED||rec.length>=KNOWN_RECENT,
        weakness:Math.round(((stepRating(target)-rating)/100+2*rW-rR)*100)/100};
    }
    return{accuracy,recentN:win.length,answers,fromRatings,levelStep,base,adjust,target,units,hasData:atts.length>0||answers>0};
  }

  /* ── the five problems ── */
  function select(o){
    const pool=(o.pool||[]).filter(i=>i&&ID.test(i.id)&&i.u&&Number.isFinite(i.s));
    if(!pool.length)return{items:[],starter:true,target:0};
    const m=model(o,pool),nowS=(o.now??Date.now())/1000,seed=String(o.seed||''),tie=id=>hash(seed+'|'+id)/4294967296;
    const atts=o.attempts||[],solvedAt={},lastOk={};
    for(const a of atts){if(!(a.id in lastOk))lastOk[a.id]=a.ok;if(a.ok&&!(a.id in solvedAt))solvedAt[a.id]=a.at;}
    const out=new Set([...(o.exclude||[]),...(o.reported||[])]);
    const avail=pool.filter(i=>!out.has(i.id)&&!(solvedAt[i.id]&&nowS-solvedAt[i.id]<SOLVED_DAYS*86400));
    const byUnit={};for(const i of avail)(byUnit[i.u]||=[]).push(i);
    const national=new Set(NATIONAL[String(o.country||'').toLowerCase()]||[]),ever=o.solvedEver||new Set();
    const chosen=[],taken=new Set(),used=new Set();
    const add=(i,why)=>{taken.add(i.id);used.add(i.u);chosen.push({id:i.id,c:i.c,y:i.y||0,k:i.k||'',u:i.u,s:i.s,why});return true;};
    const pick=(u,step,why)=>{
      const c=(byUnit[u]||[]).filter(i=>!taken.has(i.id));if(!c.length)return false;
      const home=c.some(i=>national.has(i.c)&&Math.abs(i.s-step)<=1);
      const score=i=>Math.abs(i.s-step)*10+(home&&!national.has(i.c)?15:0)+(ever.has(i.id)?4:0)+tie(i.id);
      return add(c.sort((a,b)=>score(a)-score(b))[0],why);
    };
    let missedUsed=false;
    const missed=(u,step)=>{
      if(missedUsed)return false;
      const c=(byUnit[u]||[]).filter(i=>!taken.has(i.id)&&lastOk[i.id]===false&&Math.abs(i.s-step)<=1).sort((a,b)=>tie(a.id)-tie(b.id));
      if(!c.length)return false;missedUsed=true;return add(c[0],'missed');
    };
    const coreRank=u=>{const k=CORE.indexOf(u);return k<0?CORE.length:k;};
    const fresh=Object.values(m.units).filter(x=>!x.n&&!x.recent&&byUnit[x.u]).sort((a,b)=>coreRank(a.u)-coreRank(b.u)||tie(a.u)-tie(b.u));
    const others=()=>Object.keys(byUnit).filter(u=>!used.has(u)).sort((a,b)=>tie(a)-tie(b));
    const fill=(step,why)=>{for(const u of others()){if(chosen.length>=SIZE)return;pick(u,step,why);}
      for(const u of Object.keys(byUnit)){while(chosen.length<SIZE&&pick(u,step,why));}};
    if(!m.hasData){
      for(const u of [...CORE,...others()]){if(chosen.length>=SIZE)break;if(!used.has(u))pick(u,m.levelStep,'starter');}
      fill(m.levelStep,'starter');
      return{items:chosen.slice(0,SIZE),starter:true,target:m.levelStep,model:m};
    }
    const known=Object.values(m.units).filter(x=>x.known&&byUnit[x.u]).sort((a,b)=>b.weakness-a.weakness||tie(a.u)-tie(b.u));
    const weak=known.slice(0,2).map(x=>({u:x.u,why:'weak'}));
    for(const x of fresh){if(weak.length>=2)break;weak.push({u:x.u,why:'new'});}
    weak.forEach((w,k)=>{const want=k===0?2:1;let got=0;
      if(missed(w.u,m.target))got++;
      while(got<want&&pick(w.u,m.target,w.why))got++;
      used.add(w.u);});
    while(chosen.length<3&&fresh.length){const x=fresh.find(f=>!used.has(f.u));if(!x||!pick(x.u,m.target,'new'))break;}
    const rest=known.filter(x=>!used.has(x.u));
    const mid=rest[Math.floor(rest.length/2)];
    if(!(mid&&pick(mid.u,m.target,'level')))for(const u of others())if(pick(u,m.target,'level'))break;
    const strong=known.filter(x=>!used.has(x.u)).sort((a,b)=>a.weakness-b.weakness||tie(a.u)-tie(b.u))[0];
    if(!(strong&&pick(strong.u,m.target+1,'stretch')))for(const u of others())if(pick(u,m.target+1,'stretch'))break;
    fill(m.target,'level');
    return{items:chosen.slice(0,SIZE),starter:false,target:m.target,model:m,weakUnits:weak.map(w=>w.u)};
  }

  /* ── the week's set as it is kept on this device (localStorage hlWeeklySet) ── */
  function build(o,gen,prev){
    const week=o.week||weekKey(o.now??Date.now()),user=String(o.user||''),r=select({...o,seed:user+'|'+week+'|'+gen,exclude:prev});
    const m=r.model||{};
    return{v:1,week,user,gen,at:Math.floor((o.now??Date.now())/1000),items:r.items,starter:r.starter,target:r.target,
      accuracy:m.accuracy==null?null:Math.round(m.accuracy*100)/100,recentN:m.recentN||0,adjust:m.adjust||0,prev};
  }
  const validSet=(s,o)=>isObj(s)&&s.v===1&&Array.isArray(s.items)&&s.items.length>0&&s.week===(o.week||weekKey(o.now??Date.now()))&&s.user===String(o.user||'')&&
    (!o.pool||s.items.every(i=>o.pool.some(p=>p.id===i.id)));
  /* the stored set while it is this week's and this learner's; otherwise a new one */
  function weekSet(stored,o){return validSet(stored,o)?stored:build(o,0,[]);}
  /* "New set": the next one this week, leaving out the problems of the earlier ones */
  function nextSet(stored,o){
    const same=validSet(stored,o),prev=same?[...(stored.prev||[]),...stored.items.map(i=>i.id)].slice(-60):[];
    return build(o,same?(stored.gen|0)+1:0,prev);
  }
  /* each problem's latest answer since the set was made: 'right', 'wrong' or none */
  function progress(set,attempts){
    const marks={};let done=0,right=0;
    for(const i of set?.items||[]){
      const a=(attempts||[]).find(x=>x.id===i.id&&x.at>=set.at-60);
      marks[i.id]=a?a.ok?'right':'wrong':'';if(a){done++;if(a.ok)right++;}
    }
    return{done,right,total:(set?.items||[]).length,complete:!!set&&done>=set.items.length&&done>0,marks};
  }
  /* the link that opens practice with exactly these problems */
  const setHref=set=>'#/learn/practice?mode=set&ids='+(set?.items||[]).map(i=>i.id).filter(id=>ID.test(id)).join(',');
  const dots=s=>{const n=clamp(Math.round(s)-5,1,5);return '●'.repeat(n)+'○'.repeat(5-n);};

  return{POOL_V,POOL_URL,SIZE,WINDOW,DECAY,UP,DOWN,SOLVED_DAYS,LEVEL_STEP,NATIONAL,CORE,ID,hash,weekKey,unitOfText,mergeSkills,attemptsOf,inputsFrom,model,select,weekSet,nextSet,progress,setHref,dots};
});
