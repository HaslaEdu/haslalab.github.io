/* Practice by unit: short exam problems on the learning path, one at a time, graded at once.
   Like a language-learning app: a session of ten, the step rises after two right answers in a row and
   falls after a wrong one, and a daily streak. Progress stays in this browser (localStorage). */
(()=>{
  'use strict';
  const P=window.HL_LEARN_PATH,$=id=>document.getElementById(id);
  const params=new URL(location.href).searchParams;
  const embedded=params.get('embed')==='1'&&window.parent!==window;
  const SESSION=10;
  const copy={
    ko:{title:'단원별 문제',streak:'일 연속',xp:'XP',solved:'문제 해결',pick:'단원을 고르면 내 단계에 맞는 문제 10개를 풉니다.',
      none:'아직 문제가 없습니다',step:'단계',start:'시작',again:'한 번 더',units:'단원 목록',next:'다음 문제',finish:'결과 보기',
      right:'정답입니다!',wrong:'오답입니다. 정답은',up:'단계가 올랐습니다',down:'한 단계 쉬운 문제로 갑니다',
      result:'맞힌 문제',of:'/',done:'세션 완료',loading:'문제를 불러오는 중…',failed:'문제를 불러오지 못했습니다.',retry:'다시 시도',
      pdf:'원본 시험지',quit:'← 단원 목록',time:'권장 시간',sec:'초',progress:'해결',skip:'건너뛰기',skipped:'건너뜀',
      tabExam:'수능 · 모의고사 계산',synced:'계정에 저장됨',tabToday:'오늘의 추천',todayTitle:'오늘의 10문제',whyReview:'복습',whyWeak:'약한 단원',whyStretch:'도전',whyNew:'새 단원',focus:'집중 단원',startToday:'시작하기',mySkills:'단원별 실력',unit:'단원',accuracy:'정답률',noSkills:'문제를 풀수록 단원별 실력이 쌓이고 추천이 정확해집니다.',syncFailed:'저장 실패 · 다시 시도합니다',loginToSave:'로그인하면 기록이 계정에 저장됩니다 →',tabBank:'교재 · 대학 문제',tabContest:'대회 도전',
      bankPick:'분야와 난이도를 고르면 교재와 대학 강의 문제를 하나씩 풉니다. 풀이를 확인하고 스스로 채점하세요.',stars:'난이도',showSol:'풀이 보기',noSol:'아직 등록된 풀이가 없습니다. 커뮤니티 질문 · 답변 갤러리나 AI에게 물어보세요.',
      solvedIt:'풀었어요',missedIt:'못 풀었어요',original:'원문 보기',translated:'번역 보기',noKo:'한국어 번역이 아직 없어 원문을 보여 줍니다.',draft:'하슬라랩 작성 풀이 · 검수 전',refFig:'참고 그림',empty:'이 조건의 문제가 더 없습니다. 난이도나 분야를 바꿔 보세요.',
      contestPick:'대회를 고르면 기출 문제가 하나씩 나옵니다. PDF로 풀고, 풀이를 확인한 뒤 스스로 채점하세요.',paper:'문제',solution:'풀이',noContestSol:'이 문제는 공식 풀이가 없습니다.',problems:'문제',another:'다른 문제',figInPdf:'그림은 아래 원본 PDF에서 볼 수 있습니다.',transcribed:'문제 글은 원본 PDF에서 옮겨 적은 것입니다. 원본과 다르면 PDF를 기준으로 하세요.',noteBank:'문항 출처는 문제마다 표시합니다(교재 · 대학 강의). 한국어 번역과 "하슬라랩 작성" 풀이는 검수 중입니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장되어 다른 기기에서 이어집니다.',noteContest:'각 대회의 공식 문제와 풀이이며, 한국어판은 하슬라랩 번역입니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장되어 다른 기기에서 이어집니다.',
      note:'문항 출처: 한국교육과정평가원, 서울특별시교육청, 경기도교육청, 인천광역시교육청 (웹·앱 배포 허가 범위 안에서 제공). 단원 분류 일부는 자동 분류이며 검수 중입니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장되어 다른 기기에서 이어집니다.'},
    en:{title:'Practice by unit',streak:'day streak',xp:'XP',solved:'solved',pick:'Pick a unit to solve ten problems at your step.',
      none:'No problems yet',step:'Step',start:'Start',again:'Again',units:'Units',next:'Next',finish:'See results',
      right:'Correct!',wrong:'Not quite. The answer is',up:'Step up',down:'Back one step',
      result:'Correct',of:'/',done:'Session complete',loading:'Loading problems…',failed:'Could not load the problems.',retry:'Retry',
      pdf:'Original paper',quit:'← Units',time:'Suggested time',sec:'s',progress:'solved',skip:'Skip',skipped:'skipped',
      tabExam:'Korean exam calculations',synced:'Saved to your account',tabToday:'Today',todayTitle:'Today’s ten',whyReview:'review',whyWeak:'weak unit',whyStretch:'stretch',whyNew:'new unit',focus:'focus',startToday:'Start',mySkills:'Your units',unit:'Unit',accuracy:'Correct',noSkills:'Your unit ratings grow as you solve problems, and the picks get sharper.',syncFailed:'Not saved · retrying',loginToSave:'Log in to keep your progress on your account →',tabBank:'Books & university',tabContest:'Competition challenge',
      bankPick:'Pick a field and a difficulty to work through textbook and university course problems one at a time. Check the solution and mark yourself.',stars:'Difficulty',showSol:'Show solution',noSol:'No solution is stored yet. Ask in the community Q&A gallery or ask the AI.',
      solvedIt:'I solved it',missedIt:'I missed it',original:'Original',translated:'Translation',noKo:'',draft:'HaslaLab draft solution · not yet reviewed',refFig:'Reference figures',empty:'No more problems here. Try another difficulty or field.',
      contestPick:'Pick a competition to get its problems one at a time. Solve from the PDF, check the solution and mark yourself.',paper:'Problem',solution:'Solution',noContestSol:'This problem has no official solution.',problems:'problems',another:'Another problem',figInPdf:'The figures are in the original PDF below.',transcribed:'The text is transcribed from the original paper; if they differ, the PDF is authoritative.',noteBank:'Each problem shows its source (textbook or university course). Translations and HaslaLab draft solutions are under review. Progress is kept on this device and, when you log in, on your account too.',noteContest:'Official problems and solutions of each competition; Korean versions are HaslaLab translations. Progress is kept on this device and, when you log in, on your account too.',
      note:'Problems: Korea Institute for Curriculum and Evaluation and the Seoul, Gyeonggi and Incheon education offices (Korean only), shared within the permitted web and app use. Some unit labels are automatic and under review. Progress is kept on this device and, when you log in, on your account too.'}
  };
  const state={lang:params.get('lang')==='en'?'en':'ko',index:null,shards:{},session:null};
  const tr=k=>copy[state.lang][k];
  const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const store={
    read(){try{return JSON.parse(localStorage.getItem('hlPractice')||'{}')||{};}catch(e){return {};}},
    write(v){try{localStorage.setItem('hlPractice',JSON.stringify(v));}catch(e){}}
  };
  let saved=store.read();saved.solved||={};saved.level||={};saved.xp||=0;saved.days||=[];
  const save=()=>store.write(saved);
  saved.skills||={};saved.queue||=[];saved.wrong||={};

  /* ── progress on the account (community/src/practice-progress.js): the same Elo-style rating per unit is kept
     here so guests see it too; signed-in members' attempts go to the server in batches and their state merges
     with every other device ── */
  const START=1300,stepRating=st=>1000+100*st,ratingStep=r=>Math.max(1,Math.min(10,Math.round((r-1000)/100)));
  function updateRating(r,step,result){
    if(result==='skip')return r;
    const won=result==='right'||result==='solved'?1:0,expected=1/(1+10**((stepRating(step)-r)/400)),k=result==='right'||result==='wrong'?32:16;
    return Math.round((r+k*(won-expected))*10)/10;
  }
  const API=(()=>{let o='';try{o=localStorage.getItem('hlCmApi')||'';}catch(e){}return(/^https:\/\/[a-z0-9-]+\.haslalab\.workers\.dev\/?$/.test(o)?o:'https://haslalab-community-edge.haslalab.workers.dev').replace(/\/+$/,'');})();
  const token=()=>{try{const v=localStorage.getItem('hlCmTok')||'';return /^[A-Za-z0-9_-]{20,4096}$/.test(v)?v:'';}catch(e){return '';}};
  function record(item_id,mode,unit,step,result){
    const at=Math.floor(Date.now()/1000);
    if(result!=='skip'){const k=saved.skills[unit]||{unit,rating:START,n:0,right_n:0,last_at:at};k.rating=updateRating(k.rating,step,result);k.n++;if(result==='right'||result==='solved')k.right_n++;k.last_at=at;saved.skills[unit]=k;}
    saved.queue.push({item_id,mode,unit,step,result,at});if(saved.queue.length>500)saved.queue=saved.queue.slice(-500);
    save();scheduleSync();
  }
  function mergeState(a,b){
    const A=a||{},B=b||{},obj=(x,y,f)=>{const o={...(x||{})};for(const[k,v]of Object.entries(y||{}))o[k]=k in o?f(o[k],v):v;return o;},mx=(x,y)=>Math.max(Number(x)||0,Number(y)||0);
    return{xp:mx(A.xp,B.xp),days:[...new Set([...(A.days||[]),...(B.days||[])])].sort().slice(-400),level:obj(A.level,B.level,mx),solved:obj(A.solved,B.solved,x=>x),wrong:obj(A.wrong,B.wrong,mx),
      bank:{done:obj(A.bank?.done,B.bank?.done,mx),stars:obj(A.bank?.stars,B.bank?.stars,(x,y)=>y??x)},contest:{done:obj(A.contest?.done,B.contest?.done,mx)}};
  }
  const stateOf=()=>({xp:saved.xp,days:saved.days,level:saved.level,solved:saved.solved,wrong:saved.wrong,bank:saved.bank,contest:saved.contest});
  async function api(path,method='GET',body){
    const r=await fetch(API+path,{method,headers:{Authorization:'Bearer '+token(),...(body?{'content-type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});
    if(!r.ok)throw new Error('api '+r.status);return r.json();
  }
  let syncTimer=0,syncing=false;state.sync=token()?'pending':'local';
  function scheduleSync(){clearTimeout(syncTimer);syncTimer=setTimeout(sync,1500);}
  async function sync(){
    if(!token()){state.sync='local';paintStats();return;}
    if(syncing){scheduleSync();return;}syncing=true;
    try{
      while(saved.queue.length){const batch=saved.queue.slice(0,50),r=await api('/api/practice/attempts','POST',{attempts:batch});saved.queue.splice(0,batch.length);for(const k of r.skills||[])saved.skills[k.unit]=k;save();}
      const r=await api('/api/practice/state','POST',{state:stateOf()});Object.assign(saved,mergeState(stateOf(),r.state));save();state.sync='saved';
    }catch(e){state.sync='error';setTimeout(scheduleSync,30000);}
    syncing=false;paintStats();
  }
  /* on opening: the account's state and ratings join this device's, then anything queued here is sent */
  async function pull(){
    if(!token())return;
    try{const r=await api('/api/practice/state');Object.assign(saved,mergeState(stateOf(),r.state));for(const k of r.skills||[])saved.skills[k.unit]=k;save();state.sync='saved';}catch(e){state.sync='error';}
    paintStats();scheduleSync();
  }
  const today=()=>new Date().toLocaleDateString('sv');   /* YYYY-MM-DD in local time */
  function streak(){
    const days=new Set(saved.days);let n=0;const d=new Date();
    if(!days.has(today()))d.setDate(d.getDate()-1);     /* today not yet studied: yesterday keeps the streak */
    while(days.has(d.toLocaleDateString('sv'))){n++;d.setDate(d.getDate()-1);}
    return n;
  }
  function reportHeight(){if(embedded)requestAnimationFrame(()=>window.parent.postMessage({type:'hl-practice-height',height:Math.ceil(document.documentElement.scrollHeight)},location.origin));}
  function tellUnit(unit){if(embedded)window.parent.postMessage({type:'hl-practice-unit',unit:unit||''},location.origin);}
  function math(latex,display){try{return window.katex?katex.renderToString(latex,{displayMode:!!display,throwOnError:false,strict:false}):esc(latex);}catch(e){return esc(latex);}}
  function blocks(list){
    return list.map(b=>{
      if(b.p)return '<p>'+b.p.map(s=>s.m!==undefined?math(s.m):esc(s.t||'')).join('')+'</p>';
      if(b.mb!==undefined)return '<div class="mb">'+math(b.mb,true)+'</div>';
      if(b.f)return `<figure><img src="practice/fig/${encodeURIComponent(b.f)}" width="${b.w}" height="${b.h}" alt="${esc(b.alt||'')}" loading="lazy"></figure>`;
      return '';
    }).join('');
  }
  const unitName=key=>{const e=P.SUBTOPICS.get(key);return e?e.sub.name[state.lang]:key;};
  function paintStats(){
    const solvedCount=Object.keys(saved.solved).length;
    const badge=state.sync==='saved'?`<span class="stat sync ok">☁ ${tr('synced')}</span>`:state.sync==='error'?`<span class="stat sync">⚠ ${tr('syncFailed')}</span>`:state.sync==='local'?`<a class="stat sync" href="/#/login" target="_top">${tr('loginToSave')}</a>`:'';
    $('stats').innerHTML=`<span class="stat fire"><b>🔥 ${streak()}</b>${tr('streak')}</span><span class="stat"><b>${saved.xp}</b>${tr('xp')}</span><span class="stat"><b>${solvedCount}</b>${tr('solved')}</span>${badge}`;
  }
  async function loadIndex(){
    if(!state.index){const r=await fetch('practice/index.json',{cache:'no-cache'});if(!r.ok)throw new Error('index');state.index=await r.json();}
    return state.index;
  }
  async function loadArea(area){
    if(!state.shards[area]){const r=await fetch('practice/data/'+encodeURIComponent(area)+'.json');if(!r.ok)throw new Error('shard');state.shards[area]=(await r.json()).items;}
    return state.shards[area];
  }
  function failed(retry){$('app').innerHTML=`<p>${tr('failed')}</p><button type="button" id="retry">${tr('retry')}</button>`;$('retry').onclick=retry;reportHeight();}

  /* ── unit list ── */
  async function home(){
    state.mode='exam';paintTabs();
    state.session=null;tellUnit('');paintStats();
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let index;try{index=await loadIndex();}catch(e){failed(home);return;}
    const solvedIn=unit=>Object.entries(saved.solved).filter(([,u])=>u===unit).length;
    $('app').innerHTML=`<p class="pick">${tr('pick')}</p><div class="areas">${P.AREAS.map(area=>{
      const units=area.subtopics.map(sub=>{const key=area.key+'/'+sub.key,c=index.counts[key];return{key,sub,total:c?Object.values(c).reduce((a,b)=>a+b,0):0,steps:c?Object.keys(c).map(Number):[]};}).filter(u=>u.total);
      if(!units.length)return '';
      return `<section class="area"><h2>${esc(area.name[state.lang])}</h2>${units.map(u=>{
        const done=solvedIn(u.key),lvl=saved.level[u.key]||Math.min(...u.steps);
        return `<button type="button" class="unit" data-unit="${u.key}"><span class="name">${esc(u.sub.name[state.lang])}<small>${tr('step')} ${lvl} · ${done}/${u.total} ${tr('progress')}</small></span><span class="bar"><i style="width:${Math.round(100*done/u.total)}%"></i></span></button>`;}).join('')}</section>`;
    }).join('')}</div>`;
    $('app').querySelectorAll('[data-unit]').forEach(b=>b.addEventListener('click',()=>start(b.dataset.unit)));
    reportHeight();
  }

  /* ── a session ── */
  async function start(unit){
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let index,items;
    try{index=await loadIndex();items=(await loadArea(unit.split('/')[0])).filter(i=>i.u===unit);}catch(e){failed(()=>start(unit));return;}
    if(!items.length){home();return;}
    const steps=[...new Set(items.map(i=>i.s))].sort((a,b)=>a-b);
    const level=saved.level[unit]&&steps.includes(saved.level[unit])?saved.level[unit]:steps[0];
    state.session={unit,items,steps,level,n:0,right:0,run:0,seen:new Set(),current:null,answered:false,xp:0};
    tellUnit(unit);next();
  }
  function pick(s){
    if(s.fixed)return s.items.find(i=>!s.seen.has(i.id))||null;
    /* nearest step to the learner's level, unsolved and unseen first */
    const pool=s.items.filter(i=>!s.seen.has(i.id));
    const score=i=>Math.abs(i.s-s.level)*10+(saved.solved[i.id]?5:0)+Math.random();
    return pool.sort((a,b)=>score(a)-score(b))[0]||null;
  }
  function next(){
    const s=state.session;
    if(s.n>=SESSION){summary();return;}
    const item=pick(s);if(!item){summary();return;}
    s.current=item;s.answered=false;s.seen.add(item.id);s.n++;
    const imageChoices=item.ch.every(c=>!c.c.length);
    $('app').innerHTML=`<div class="session">
      <div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button><span class="unitname">${s.fixed?esc(tr('tabToday'))+' · ':''}${esc(unitName(s.fixed?item.u:s.unit))}</span><span class="lvl">${tr('step')} ${item.s}</span><span class="progress" aria-hidden="true"><i style="width:${Math.round(100*(s.n-1)/SESSION)}%"></i></span><span>${s.n}/${SESSION}</span></div>
      <div class="q">${blocks(item.b)}</div>
      <div class="choices${imageChoices?' compact':''}" role="group">${item.ch.map(c=>`<button type="button" class="choice" data-n="${c.n}"><span class="no">${'①②③④⑤'[c.n-1]}</span>${imageChoices?'':`<span>${blocks(c.c).replace(/^<p>|<\/p>$/g,'')}</span>`}</button>`).join('')}</div>
      <div id="feedback"></div>
      <div class="foot"><span class="src">${esc(item.src)} · ${esc(item.by)}${item.pdf?` · <a href="${esc(item.pdf)}" target="_blank" rel="noopener noreferrer">${tr('pdf')}</a>`:''} · ${tr('time')} ${item.sec}${tr('sec')}</span><span class="footbtns"><button type="button" id="skip">${tr('skip')}</button><button type="button" class="primary" id="next" hidden>${s.n>=SESSION?tr('finish'):tr('next')}</button></span></div>
    </div>`;
    $('quit').onclick=s.fixed?todayHome:home;
    $('app').querySelectorAll('.choice').forEach(b=>b.addEventListener('click',()=>answer(Number(b.dataset.n))));
    $('next').onclick=next;
    $('skip').onclick=()=>{if(s.answered)return;record(item.id,'exam',item.u,item.s,'skip');s.skipped=(s.skipped||0)+1;s.n--;s.extra=(s.extra||0)+1;if(s.extra>30){summary();return;}next();};
    reportHeight();window.scrollTo?.(0,0);if(embedded)window.parent.postMessage({type:'hl-practice-top'},location.origin);
  }
  function answer(choice){
    const s=state.session,item=s.current;if(s.answered)return;s.answered=true;
    const ok=choice===item.a;
    $('app').querySelectorAll('.choice').forEach(b=>{b.disabled=true;const n=Number(b.dataset.n);if(n===item.a)b.classList.add('right');else if(n===choice)b.classList.add('wrong');});
    let note='';
    if(ok){
      s.right++;s.run++;const gain=10+2*item.s;s.xp+=gain;saved.xp+=gain;saved.solved[item.id]=item.u;delete saved.wrong[item.id];
      if(s.fixed){}else if(s.run>=2){const up=s.steps.find(x=>x>s.level);if(up){s.level=up;note=' · '+tr('up')+' ↑';}s.run=0;}
    }else{
      s.run=0;saved.wrong[item.id]=Math.floor(Date.now()/1000);
      if(!s.fixed){const down=[...s.steps].reverse().find(x=>x<s.level);if(down){s.level=down;note=' · '+tr('down');}}
    }
    if(!s.fixed)saved.level[s.unit]=s.level;
    record(item.id,'exam',item.u,item.s,ok?'right':'wrong');
    if(!saved.days.includes(today())){saved.days.push(today());saved.days=saved.days.slice(-400);}
    save();paintStats();
    $('feedback').innerHTML=`<p class="feedback ${ok?'ok':'bad'}">${ok?tr('right'):tr('wrong')+' '+'①②③④⑤'[item.a-1]}${note}</p>`;
    $('next').hidden=false;$('skip').hidden=true;$('next').focus();reportHeight();
  }
  function summary(){
    const s=state.session;
    $('app').innerHTML=`<div class="session summary"><p class="eyebrow">${tr('done')}</p><p class="big">${s.right}${tr('of')}${s.n}</p><p>${tr('result')} · +${s.xp} XP · ${s.mode==='bank'?'★'.repeat(s.stars):s.fixed?tr('tabToday'):tr('step')+' '+s.level}${s.skipped?` · ${s.skipped} ${tr('skipped')}`:''} · 🔥 ${streak()}${tr('streak')}</p>
      <div class="actions"><button type="button" class="primary" id="again">${tr('again')}</button><button type="button" id="units">${tr('units')}</button></div></div>`;
    $('again').onclick=()=>s.fixed?todayHome():s.mode==='bank'?bankStart(s.field,s.stars):start(s.unit);$('units').onclick=s.fixed?todayHome:s.mode==='bank'?bankHome:home;reportHeight();
  }


  /* ── modes: Korean exams (graded), books & university (problem bank, self-marked), competitions (PDF, self-marked) ── */
  const BANK_API='https://haslalab-problem-bank.haslalab.workers.dev';
  const PDF_HOST=/^https:\/\/haslalab-pdf\.haslalab\.workers\.dev\/pdf\//;
  const BANK_FIELDS=[['classical_mechanics','고전역학','Classical mechanics'],['electromagnetism','전자기학','Electromagnetism'],['oscillations_waves','진동과 파동','Oscillations and waves'],
    ['optics','광학','Optics'],['thermodynamics','열역학','Thermodynamics'],['statistical_mechanics','통계역학','Statistical mechanics'],['quantum_mechanics','양자역학','Quantum mechanics'],
    ['special_relativity','특수 상대성','Special relativity'],['general_relativity','일반 상대성','General relativity'],['mathematical_methods','수리물리','Mathematical methods']];
  saved.bank||={done:{},stars:{}};saved.contest||={done:{}};
  const BANK_AREA={classical_mechanics:'mechanics',electromagnetism:'em',oscillations_waves:'waves',optics:'optics',thermodynamics:'thermal',statistical_mechanics:'thermal',quantum_mechanics:'modern',special_relativity:'modern',general_relativity:'modern',mathematical_methods:'math'};
  function studied(xp){saved.xp+=xp;if(!saved.days.includes(today())){saved.days.push(today());saved.days=saved.days.slice(-400);}save();paintStats();}
  function paintTabs(){
    $('tabs').innerHTML=[['today',tr('tabToday')],['exam',tr('tabExam')],['bank',tr('tabBank')],['contest',tr('tabContest')]].map(([k,l])=>`<button type="button" role="tab" data-mode="${k}" aria-selected="${state.mode===k}">${l}</button>`).join('');
    $('tabs').querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>({today:todayHome,exam:home,bank:bankHome,contest:contestHome})[b.dataset.mode]());
    $('note').textContent=tr(state.mode==='bank'?'noteBank':state.mode==='contest'?'noteContest':'note');
  }
  /* bank text: paragraphs with $…$ and $$…$$ left to KaTeX auto-render */
  function textHtml(t){return esc(t||'').split(/\n{2,}/).map(p=>'<p>'+p.replace(/\n/g,'<br>')+'</p>').join('');}
  function typeset(el){try{window.renderMathInElement?.(el,{delimiters:[{left:'$$',right:'$$',display:true},{left:'\\[',right:'\\]',display:true},{left:'$',right:'$',display:false},{left:'\\(',right:'\\)',display:false}],throwOnError:false});}catch(e){}}
  function pickVersion(item){
    const vs=item.versions||[],ko=vs.find(v=>v.language==='ko'),orig=vs.find(v=>v.role==='original')||vs[0];
    return state.lang==='ko'&&ko?{main:ko,alt:orig!==ko?orig:null}:{main:orig||ko,alt:null,missing:state.lang==='ko'&&!ko};
  }
  async function bankGet(path){const r=await fetch(BANK_API+path,{headers:{accept:'application/json'}});if(!r.ok)throw new Error('bank '+r.status);return r.json();}

  function bankHome(){
    state.mode='bank';state.session=null;paintTabs();paintStats();tellUnit('');
    const field=state.bankField||BANK_FIELDS[0][0];
    $('app').innerHTML=`<p class="pick">${tr('bankPick')}</p><div class="areas">${BANK_FIELDS.map(([k,ko,en])=>{
      const st=saved.bank.stars[k]||1;
      return `<section class="area"><h2>${esc(state.lang==='ko'?ko:en)}</h2><div class="starrow" role="group" aria-label="${tr('stars')}">${[1,2,3,4,5].map(n=>`<button type="button" class="unit star${n===st?' cur':''}" data-field="${k}" data-stars="${n}">${'★'.repeat(n)}<small>${tr('step')} ${P.stepFromStars(n)}</small></button>`).join('')}</div></section>`;}).join('')}</div>`;
    $('app').querySelectorAll('[data-field]').forEach(b=>b.onclick=()=>bankStart(b.dataset.field,Number(b.dataset.stars)));
    reportHeight();
  }
  async function bankStart(field,stars){
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    saved.bank.stars[field]=stars;save();
    const s=state.session={mode:'bank',field,stars,pool:[],cursor:null,more:true,n:0,right:0,skipped:0,xp:0,seen:new Set()};
    try{await bankFill(s);}catch(e){failed(()=>bankStart(field,stars));return;}
    bankNext();
  }
  async function bankFill(s){
    for(let page=0;page<3&&s.more&&s.pool.length<40;page++){
      const q=new URLSearchParams({lang:state.lang,limit:'20',collection:'physics',subject:s.field,stars:String(s.stars)});if(s.cursor)q.set('cursor',s.cursor);
      const j=await bankGet('/api/problem-bank/search?'+q);
      s.pool.push(...(j.items||[]).filter(i=>!saved.bank.done[i.id]&&!s.seen.has(i.id)));s.cursor=j.next_cursor||null;s.more=!!(j.has_more&&s.cursor);
    }
    for(let i=s.pool.length-1;i>0;i--){const k=Math.floor(Math.random()*(i+1));[s.pool[i],s.pool[k]]=[s.pool[k],s.pool[i]];}
  }
  async function bankNext(){
    const s=state.session;
    if(s.n>=5){summary();return;}
    if(!s.pool.length&&s.more){try{await bankFill(s);}catch(e){}}
    const pick=s.pool.shift();
    if(!pick){$('app').innerHTML=`<div class="session"><p>${tr('empty')}</p><div class="actions"><button type="button" id="units">${tr('units')}</button></div></div>`;$('units').onclick=bankHome;reportHeight();return;}
    s.seen.add(pick.id);s.n++;s.answered=false;s.current=pick;
    $('app').innerHTML=`<div class="session"><p>${tr('loading')}</p></div>`;
    let item;try{item=(await bankGet('/api/problem-bank/questions/'+pick.id+'?lang='+state.lang)).question;}catch(e){failed(bankNext);return;}
    const v=pickVersion(item),figs=(item.assets||[]).filter(a=>a.role==='figure'&&/^\/api\/problem-bank\/assets\/a_[0-9a-f]{64}$/.test(a.url||''));
    const fig=a=>`<figure><img src="${BANK_API+a.url}" alt="" loading="lazy"></figure>`;
    const label=BANK_FIELDS.find(f=>f[0]===s.field);
    $('app').innerHTML=`<div class="session">
      <div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button><span class="unitname">${esc(state.lang==='ko'?label[1]:label[2])}</span><span class="lvl">${'★'.repeat(s.stars)}</span><span class="progress" aria-hidden="true"><i style="width:${Math.round(100*(s.n-1)/5)}%"></i></span><span>${s.n}/5</span></div>
      ${v.missing?`<p class="src">${tr('noKo')}</p>`:''}<div class="q" id="qtext">${textHtml(v.main?.text)}</div>
      ${v.alt?`<details class="alt"><summary>${tr('original')}</summary><div class="q" id="qalt">${textHtml(v.alt.text)}</div></details>`:''}
      ${figs.filter(a=>a.placement!=='reference').map(fig).join('')}
      ${figs.some(a=>a.placement==='reference')?`<details class="alt"><summary>${tr('refFig')}</summary>${figs.filter(a=>a.placement==='reference').map(fig).join('')}</details>`:''}
      <div id="sol"></div><div id="feedback"></div>
      <div class="foot"><span class="src">${esc(pick.source_title||'')}${item.original_number?' · '+esc(item.original_number):''}</span>
        <span class="footbtns"><button type="button" id="skip">${tr('skip')}</button><button type="button" id="showSol">${tr('showSol')}</button><button type="button" class="primary" id="good">${tr('solvedIt')}</button><button type="button" id="miss">${tr('missedIt')}</button><button type="button" class="primary" id="next" hidden>${s.n>=5?tr('finish'):tr('next')}</button></span></div></div>`;
    typeset($('app'));
    $('quit').onclick=bankHome;
    const bankUnit=(BANK_AREA[s.field]||'mechanics')+'/*',bankStep=P.stepFromStars(s.stars);
    $('skip').onclick=()=>{if(s.answered)return;record(pick.id,'bank',bankUnit,bankStep,'skip');s.skipped++;s.n--;bankNext();};
    $('showSol').onclick=async()=>{
      $('showSol').disabled=true;$('sol').innerHTML=`<p class="src">${tr('loading')}</p>`;
      try{const j=await bankGet('/api/problem-bank/questions/'+pick.id+'/solutions?lang='+state.lang);
        const sols=(j.solutions||[]).map(x=>({x,v:pickVersion(x).main})).filter(o=>o.v?.text);
        $('sol').innerHTML=sols.length?sols.map(({x,v})=>`<section class="solution"><h3>${tr('solution')}${x.authorship==='haslalab_original_draft'?` <small>${tr('draft')}</small>`:''}</h3>${textHtml(v.text)}</section>`).join(''):`<p class="feedback bad">${tr('noSol')}</p>`;
        typeset($('sol'));}catch(e){$('sol').innerHTML=`<p class="feedback bad">${tr('failed')}</p>`;}
      reportHeight();
    };
    const mark=ok=>{if(s.answered)return;s.answered=true;
      record(pick.id,'bank',bankUnit,bankStep,ok?'solved':'missed');
      if(ok){s.right++;const gain=10+5*s.stars;s.xp+=gain;saved.bank.done[pick.id]=1;studied(gain);}else{saved.bank.done[pick.id]=0;studied(2);}
      ['good','miss','skip'].forEach(id=>$(id).hidden=true);$('next').hidden=false;$('next').focus();
      $('feedback').innerHTML=`<p class="feedback ${ok?'ok':'bad'}">${ok?'✓ '+tr('solvedIt'):tr('missedIt')}</p>`;reportHeight();};
    $('good').onclick=()=>mark(true);$('miss').onclick=()=>mark(false);$('next').onclick=bankNext;
    reportHeight();if(embedded)window.parent.postMessage({type:'hl-practice-top'},location.origin);
  }

  async function contestHome(){
    state.mode='contest';state.session=null;paintTabs();paintStats();tellUnit('');
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    try{if(!state.contests){const r=await fetch('practice/contests.json');if(!r.ok)throw 0;state.contests=(await r.json()).contests;}}catch(e){failed(contestHome);return;}
    $('app').innerHTML=`<p class="pick">${tr('contestPick')}</p><div class="areas">${state.contests.map(c=>{
      const total=c.structured||c.problems.length,done=Object.entries(saved.contest.done).filter(([id,v])=>v===1&&id.startsWith(c.key+'-')&&(c.structured?id.includes('~'):!id.includes('~'))).length;
      return `<section class="area"><button type="button" class="unit" data-contest="${c.key}"><span class="name"><b>${esc(c.name[state.lang])}</b><small>${tr('step')} ${c.step} · ${total} ${tr('problems')} · ${done} ${tr('progress')}</small></span><span class="bar"><i style="width:${Math.round(100*done/Math.max(1,total))}%"></i></span></button></section>`;}).join('')}</div>`;
    $('app').querySelectorAll('[data-contest]').forEach(b=>b.onclick=()=>contestShow(b.dataset.contest));
    reportHeight();
  }
  /* PDFs are drawn page by page with pdf.js (the same build the HPhO exam uses), so phones show them too */
  const PDFJS='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/';
  let pdfjs=null;
  const loadPdfjs=()=>pdfjs||=new Promise((ok,fail)=>{if(window.pdfjsLib)return ok(window.pdfjsLib);const sc=document.createElement('script');sc.src=PDFJS+'pdf.min.js';
    sc.onload=()=>{if(!window.pdfjsLib){pdfjs=null;return fail(Error('pdfjs'));}window.pdfjsLib.GlobalWorkerOptions.workerSrc=PDFJS+'pdf.worker.min.js';ok(window.pdfjsLib);};sc.onerror=()=>{pdfjs=null;fail(Error('pdfjs'));};document.head.append(sc);});
  let pdfJob=0;
  async function showPdf(url){
    const box=$('pdf');if(!box||!PDF_HOST.test(url))return;const job=++pdfJob;box.innerHTML=`<p class="src">${tr('loading')}</p>`;
    try{
      const lib=await loadPdfjs(),doc=await lib.getDocument({url,isEvalSupported:false}).promise;if(job!==pdfJob)return;
      box.innerHTML='';const width=Math.min(box.clientWidth||800,1000),dpr=Math.min(devicePixelRatio||1,2);
      for(let i=1;i<=Math.min(doc.numPages,16);i++){
        const page=await doc.getPage(i);if(job!==pdfJob)return;
        const vp=page.getViewport({scale:width/page.getViewport({scale:1}).width*dpr}),cv=document.createElement('canvas');
        cv.width=vp.width;cv.height=vp.height;cv.style.width='100%';box.append(cv);
        await page.render({canvasContext:cv.getContext('2d'),viewport:vp}).promise;reportHeight();
      }
    }catch(e){if(job===pdfJob)box.innerHTML=`<p class="src">${tr('failed')} <a href="${esc(url)}" target="_blank" rel="noopener">PDF ↗</a></p>`;}
    reportHeight();
  }
  /* a competition: problems transcribed per problem (text with LaTeX and the figures cut from the paper) when
     practice/contest/<key>.json has them; otherwise the paper itself, drawn with pdf.js */
  async function contestItems(key){
    state.contestItems||={};
    if(!(key in state.contestItems)){try{const r=await fetch('practice/contest/'+encodeURIComponent(key)+'.json');state.contestItems[key]=r.ok?(await r.json()).items:[];}catch(e){state.contestItems[key]=[];}}
    return state.contestItems[key];
  }
  async function contestShow(key,skipId){
    const c=state.contests.find(x=>x.key===key);if(!c){contestHome();return;}
    const items=await contestItems(key);
    const L={ko:'한국어',en:'English',hu:'Magyar'},safe=u=>PDF_HOST.test(u||'')?u:'';
    let item=null,p;
    if(items.length){
      const open=items.filter(i=>saved.contest.done[i.id]!==1&&i.id!==skipId),pool=open.length?open:items;
      item=pool[Math.floor(Math.random()*pool.length)];p=c.problems.find(x=>x.id===item.pdf);
    }else{
      const open=c.problems.filter(x=>saved.contest.done[x.id]!==1&&x.id!==skipId),pool=open.length?open:c.problems;
      p=pool[Math.floor(Math.random()*pool.length)];
    }
    const doneId=item?item.id:p.id;
    const langs=Object.entries(p.papers).filter(([,u])=>safe(u)),pref=langs.find(([l])=>l===state.lang)||langs[0];
    const sols=Object.entries(p.sols||{}).filter(([,u])=>safe(u));
    const label=item?`${item.year} · ${p.key}${item.key&&item.key!==p.key?' · '+item.key:''}`:`${p.year} · ${p.key}`;
    const title=item?.title||p.title||'';
    const body=item?item.b.map(b=>b.f?`<figure><img src="practice/contest/fig/${encodeURIComponent(b.f)}" width="${b.w}" height="${b.h}" alt="" loading="lazy"></figure>`:textHtml(b.t)).join(''):'';
    $('app').innerHTML=`<div class="session">
      <div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button><span class="unitname">${esc(c.name[state.lang])}</span><span class="lvl">${esc(label)}</span>${title?`<span>${esc(title)}</span>`:''}</div>
      ${item?`<div class="q" id="qtext">${body}</div>`:''}
      <div class="langrow">${tr('paper')}: ${langs.map(([l,u])=>`<button type="button" class="${!item&&l===pref[0]?'cur':''}" data-pdf="${esc(u)}">${L[l]||l} PDF</button>`).join('')} <a href="${esc(pref[1])}" target="_blank" rel="noopener" id="openPdf">PDF ↗</a></div>
      <div id="pdf" class="pdf"${item?' hidden':''} role="document" aria-label="${esc(c.name[state.lang])} ${esc(label)}"><p class="src">${tr('loading')}</p></div>
      <div id="feedback"></div>
      <div class="foot"><span class="src">${sols.length?`${tr('solution')}: `+sols.map(([l,u])=>`<a href="${esc(u)}" target="_blank" rel="noopener">${L[l]||l} ↗</a>`).join(' · '):tr('noContestSol')}${item?' · '+tr('transcribed'):''}</span>
        <span class="footbtns"><button type="button" id="skip">${tr('skip')}</button><button type="button" class="primary" id="good">${tr('solvedIt')}</button><button type="button" id="miss">${tr('missedIt')}</button><button type="button" class="primary" id="next" hidden>${tr('another')}</button></span></div></div>`;
    if(item)typeset($('qtext'));
    /* a figure that could not be cut out is described in brackets: point to the paper */
    if(item&&item.b.some(b=>/\[(그림|Figure)[^\]]*\]/.test(b.t||''))&&!item.b.some(b=>b.f))$('qtext').insertAdjacentHTML('beforeend',`<p class="src">${tr('figInPdf')}</p>`);
    $('app').querySelectorAll('[data-pdf]').forEach(b=>b.onclick=()=>{$('pdf').hidden=false;showPdf(b.dataset.pdf);$('openPdf').href=b.dataset.pdf;$('app').querySelectorAll('[data-pdf]').forEach(x=>x.classList.toggle('cur',x===b));});
    if(!item)showPdf(pref[1]);
    $('quit').onclick=contestHome;$('skip').onclick=()=>{record(doneId,'contest','contest/'+key,c.step,'skip');contestShow(key,doneId);};$('next').onclick=()=>contestShow(key,doneId);
    const mark=ok=>{saved.contest.done[doneId]=ok?1:0;record(doneId,'contest','contest/'+key,c.step,ok?'solved':'missed');studied(ok?20+5*c.step:2);['good','miss','skip'].forEach(id=>$(id).hidden=true);$('next').hidden=false;
      $('feedback').innerHTML=`<p class="feedback ${ok?'ok':'bad'}">${ok?'✓ '+tr('solvedIt'):tr('missedIt')}</p>`;reportHeight();};
    $('good').onclick=()=>mark(true);$('miss').onclick=()=>mark(false);
    reportHeight();if(embedded)window.parent.postMessage({type:'hl-practice-top'},location.origin);
  }


  /* ── today: ten graded problems chosen from the ratings — review of earlier mistakes, the weakest and the
     longest-untouched units at the learner's step, and one stretch problem — plus a textbook and a competition
     suggestion ── */
  async function allExamItems(){
    const index=await loadIndex(),areas=[...new Set(Object.keys(index.counts).map(u=>u.split('/')[0]))];
    return (await Promise.all(areas.map(loadArea))).flat();
  }
  function unitStatus(units){
    const nowS=Date.now()/1000;
    return units.map(u=>{const k=saved.skills[u];const r=k?k.rating:START,days=k?(nowS-k.last_at)/86400:99;
      /* lower is more urgent: a weak rating, few attempts, or a long gap since the last one */
      return{u,k,r,step:ratingStep(r),urgency:r-Math.min(days,30)*4-(k?0:60)+(k&&k.n>=6&&k.right_n/k.n>0.8?80:0)};}).sort((a,b)=>a.urgency-b.urgency);
  }
  function chooseToday(items){
    const byUnit={};for(const it of items)(byUnit[it.u]||=[]).push(it);
    const status=unitStatus(Object.keys(byUnit)),chosen=[],taken=new Set();
    const add=it=>{if(it&&!taken.has(it.id)&&chosen.length<SESSION){taken.add(it.id);chosen.push({...it,why:it.why});}};
    const near=(u,step,why)=>{const pool=(byUnit[u]||[]).filter(i=>!taken.has(i.id)&&!saved.solved[i.id]&&!saved.wrong[i.id]);
      pool.sort((a,b)=>Math.abs(a.s-step)-Math.abs(b.s-step)+(Math.random()-.5)*.4);return pool[0]&&{...pool[0],why};};
    const byId=new Map(items.map(i=>[i.id,i]));
    for(const [id] of Object.entries(saved.wrong).sort((a,b)=>a[1]-b[1]).slice(0,3)){const it=byId.get(id);if(it)add({...it,why:'review'});}
    for(const st of status.slice(0,3)){add(near(st.u,st.step,'weak'));add(near(st.u,st.step,'weak'));}
    const strong=[...status].filter(x=>x.k&&x.k.n>=3).sort((a,b)=>b.r-a.r)[0];
    if(strong)add(near(strong.u,strong.step+1,'stretch'));
    for(const st of status.slice(3)){if(chosen.length>=SESSION)break;add(near(st.u,st.step,'new'));}
    return{chosen,status};
  }
  async function todayHome(){
    state.mode='today';state.session=null;paintTabs();paintStats();tellUnit('');
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let items;try{items=await allExamItems();}catch(e){failed(todayHome);return;}
    const {chosen,status}=chooseToday(items);
    const why={review:tr('whyReview'),weak:tr('whyWeak'),stretch:tr('whyStretch'),new:tr('whyNew')};
    const counts=chosen.reduce((m,i)=>(m[i.why]=(m[i.why]||0)+1,m),{});
    const weakUnits=[...new Set(chosen.filter(i=>i.why==='weak').map(i=>i.u))];
    /* textbook: the field whose area rating is lowest; competition: the one closest to the learner's best step */
    const areaRating=a=>saved.skills[a+'/*']?.rating??(()=>{const ks=Object.values(saved.skills).filter(k=>k.unit.startsWith(a+'/'));return ks.length?ks.reduce((x,k)=>x+k.rating,0)/ks.length:START;})();
    const field=[...BANK_FIELDS].sort((x,y)=>areaRating(BANK_AREA[x[0]])-areaRating(BANK_AREA[y[0]]))[0];
    const fieldStars=Math.max(1,Math.min(5,ratingStep(areaRating(BANK_AREA[field[0]]))-3));
    const best=Math.max(START,...Object.values(saved.skills).map(k=>k.rating)),bestStep=ratingStep(best);
    let contests=state.contests;try{if(!contests){const r=await fetch('practice/contests.json');contests=state.contests=(await r.json()).contests;}}catch(e){contests=[];}
    const contest=[...contests].sort((a,b)=>Math.abs(a.step-(bestStep+3))-Math.abs(b.step-(bestStep+3)))[0];
    const top=status.filter(x=>x.k).sort((a,b)=>a.r-b.r);
    $('app').innerHTML=`<section class="session today">
        <h2>${tr('todayTitle')}</h2>
        <p class="src">${Object.entries(counts).map(([k,n])=>`${why[k]} ${n}`).join(' · ')}${weakUnits.length?` · ${tr('focus')}: ${weakUnits.map(u=>esc(unitName(u))).join(', ')}`:''}</p>
        <ol class="todaylist">${chosen.map(i=>`<li><span class="tag ${i.why}">${why[i.why]}</span> ${esc(unitName(i.u))} <small>${tr('step')} ${i.s}</small></li>`).join('')}</ol>
        <div class="actions"><button type="button" class="primary" id="startToday"${chosen.length?'':' disabled'}>${tr('startToday')}</button></div>
      </section>
      <div class="areas suggest">
        <button type="button" class="area unit" id="sugBank"><span class="name"><b>${tr('tabBank')}</b><small>${esc(state.lang==='ko'?field[1]:field[2])} · ${'★'.repeat(fieldStars)}</small></span><span>→</span></button>
        ${contest?`<button type="button" class="area unit" id="sugContest"><span class="name"><b>${tr('tabContest')}</b><small>${esc(contest.name[state.lang])} · ${tr('step')} ${contest.step}</small></span><span>→</span></button>`:''}
      </div>
      ${top.length?`<section class="area skills"><h2>${tr('mySkills')}</h2><table><thead><tr><th>${tr('unit')}</th><th>${tr('step')}</th><th>${tr('accuracy')}</th></tr></thead><tbody>${top.slice(0,12).map(x=>`<tr><td>${esc(unitName(x.u))}</td><td>${x.step}</td><td>${Math.round(100*x.k.right_n/Math.max(1,x.k.n))}% <small>(${x.k.n})</small></td></tr>`).join('')}</tbody></table></section>`:`<p class="src">${tr('noSkills')}</p>`}`;
    $('startToday').onclick=()=>{state.session={unit:'today',fixed:true,items:chosen,steps:[],level:0,n:0,right:0,run:0,seen:new Set(),current:null,answered:false,xp:0};next();};
    $('sugBank').onclick=()=>{state.bankField=field[0];bankStart(field[0],fieldStars);};
    if($('sugContest'))$('sugContest').onclick=()=>{paintTabs();contestShow(contest.key);};
    reportHeight();
  }

  function applyTheme(){const t=params.get('theme'),dark=t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.dataset.theme=dark?'dark':'light';}
  function translate(){document.documentElement.lang=state.lang;document.querySelectorAll('[data-i18n]').forEach(el=>{el.textContent=tr(el.dataset.i18n);});$('note').textContent=tr('note');document.title=tr('title')+' · HaslaLab';}
  window.addEventListener('message',event=>{
    if(!embedded||event.origin!==location.origin||event.source!==window.parent||event.data?.type!=='hl-practice-settings')return;
    if(['light','dark'].includes(event.data.theme))document.documentElement.dataset.theme=event.data.theme;
    if(['ko','en'].includes(event.data.lang)&&event.data.lang!==state.lang){state.lang=event.data.lang;translate();paintStats();paintTabs();if(!state.session)({today:todayHome,exam:home,bank:bankHome,contest:contestHome})[state.mode||'today']();}
  });
  addEventListener('keydown',e=>{
    const s=state.session;if(!s||s.mode==='bank'||/^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName||''))return;
    if(!s.answered&&/^[1-5]$/.test(e.key))answer(Number(e.key));
    else if(s.answered&&e.key==='Enter'&&document.activeElement?.id!=='next'){e.preventDefault();$('next')?.click();}
  });
  if(typeof ResizeObserver==='function')new ResizeObserver(reportHeight).observe(document.body);
  document.documentElement.classList.toggle('embedded',embedded);
  applyTheme();translate();
  const boot=()=>{pull();const unit=params.get('unit'),mode=params.get('mode');state.mode='exam';paintTabs();if(mode==='bank')bankHome();else if(mode==='contest')contestHome();else if(unit&&P.SUBTOPICS.has(unit))start(unit);else if(mode==='exam')home();else todayHome();};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
