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
      pdf:'원본 시험지',quit:'← 단원 목록',time:'권장 시간',sec:'초',progress:'해결',
      note:'문항 출처: 한국교육과정평가원, 서울특별시교육청, 경기도교육청, 인천광역시교육청 (웹·앱 배포 허가 범위 안에서 제공). 단원 분류 일부는 자동 분류이며 검수 중입니다. 기록은 이 기기에만 저장됩니다.'},
    en:{title:'Practice by unit',streak:'day streak',xp:'XP',solved:'solved',pick:'Pick a unit to solve ten problems at your step.',
      none:'No problems yet',step:'Step',start:'Start',again:'Again',units:'Units',next:'Next',finish:'See results',
      right:'Correct!',wrong:'Not quite. The answer is',up:'Step up',down:'Back one step',
      result:'Correct',of:'/',done:'Session complete',loading:'Loading problems…',failed:'Could not load the problems.',retry:'Retry',
      pdf:'Original paper',quit:'← Units',time:'Suggested time',sec:'s',progress:'solved',
      note:'Problems: Korea Institute for Curriculum and Evaluation and the Seoul, Gyeonggi and Incheon education offices (Korean only), shared within the permitted web and app use. Some unit labels are automatic and under review. Progress is kept on this device only.'}
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
    $('stats').innerHTML=`<span class="stat fire"><b>🔥 ${streak()}</b>${tr('streak')}</span><span class="stat"><b>${saved.xp}</b>${tr('xp')}</span><span class="stat"><b>${solvedCount}</b>${tr('solved')}</span>`;
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
      <div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button><span class="unitname">${esc(unitName(s.unit))}</span><span class="lvl">${tr('step')} ${item.s}</span><span class="progress" aria-hidden="true"><i style="width:${Math.round(100*(s.n-1)/SESSION)}%"></i></span><span>${s.n}/${SESSION}</span></div>
      <div class="q">${blocks(item.b)}</div>
      <div class="choices${imageChoices?' compact':''}" role="group">${item.ch.map(c=>`<button type="button" class="choice" data-n="${c.n}"><span class="no">${'①②③④⑤'[c.n-1]}</span>${imageChoices?'':`<span>${blocks(c.c).replace(/^<p>|<\/p>$/g,'')}</span>`}</button>`).join('')}</div>
      <div id="feedback"></div>
      <div class="foot"><span class="src">${esc(item.src)} · ${esc(item.by)}${item.pdf?` · <a href="${esc(item.pdf)}" target="_blank" rel="noopener noreferrer">${tr('pdf')}</a>`:''} · ${tr('time')} ${item.sec}${tr('sec')}</span><button type="button" class="primary" id="next" hidden>${s.n>=SESSION?tr('finish'):tr('next')}</button></div>
    </div>`;
    $('quit').onclick=home;
    $('app').querySelectorAll('.choice').forEach(b=>b.addEventListener('click',()=>answer(Number(b.dataset.n))));
    $('next').onclick=next;
    reportHeight();window.scrollTo?.(0,0);if(embedded)window.parent.postMessage({type:'hl-practice-top'},location.origin);
  }
  function answer(choice){
    const s=state.session,item=s.current;if(s.answered)return;s.answered=true;
    const ok=choice===item.a;
    $('app').querySelectorAll('.choice').forEach(b=>{b.disabled=true;const n=Number(b.dataset.n);if(n===item.a)b.classList.add('right');else if(n===choice)b.classList.add('wrong');});
    let note='';
    if(ok){
      s.right++;s.run++;const gain=10+2*item.s;s.xp+=gain;saved.xp+=gain;saved.solved[item.id]=s.unit;
      if(s.run>=2){const up=s.steps.find(x=>x>s.level);if(up){s.level=up;note=' · '+tr('up')+' ↑';}s.run=0;}
    }else{
      s.run=0;const down=[...s.steps].reverse().find(x=>x<s.level);if(down){s.level=down;note=' · '+tr('down');}
    }
    saved.level[s.unit]=s.level;
    if(!saved.days.includes(today())){saved.days.push(today());saved.days=saved.days.slice(-400);}
    save();paintStats();
    $('feedback').innerHTML=`<p class="feedback ${ok?'ok':'bad'}">${ok?tr('right'):tr('wrong')+' '+'①②③④⑤'[item.a-1]}${note}</p>`;
    $('next').hidden=false;$('next').focus();reportHeight();
  }
  function summary(){
    const s=state.session;
    $('app').innerHTML=`<div class="session summary"><p class="eyebrow">${tr('done')}</p><p class="big">${s.right}${tr('of')}${s.n}</p><p>${tr('result')} · +${s.xp} XP · ${tr('step')} ${s.level} · 🔥 ${streak()}${tr('streak')}</p>
      <div class="actions"><button type="button" class="primary" id="again">${tr('again')}</button><button type="button" id="units">${tr('units')}</button></div></div>`;
    $('again').onclick=()=>start(s.unit);$('units').onclick=home;reportHeight();
  }

  function applyTheme(){const t=params.get('theme'),dark=t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.dataset.theme=dark?'dark':'light';}
  function translate(){document.documentElement.lang=state.lang;document.querySelectorAll('[data-i18n]').forEach(el=>{el.textContent=tr(el.dataset.i18n);});$('note').textContent=tr('note');document.title=tr('title')+' · HaslaLab';}
  window.addEventListener('message',event=>{
    if(!embedded||event.origin!==location.origin||event.source!==window.parent||event.data?.type!=='hl-practice-settings')return;
    if(['light','dark'].includes(event.data.theme))document.documentElement.dataset.theme=event.data.theme;
    if(['ko','en'].includes(event.data.lang)&&event.data.lang!==state.lang){state.lang=event.data.lang;translate();paintStats();if(!state.session)home();}
  });
  addEventListener('keydown',e=>{
    const s=state.session;if(!s||/^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName||''))return;
    if(!s.answered&&/^[1-5]$/.test(e.key))answer(Number(e.key));
    else if(s.answered&&e.key==='Enter'&&document.activeElement?.id!=='next'){e.preventDefault();$('next')?.click();}
  });
  if(typeof ResizeObserver==='function')new ResizeObserver(reportHeight).observe(document.body);
  document.documentElement.classList.toggle('embedded',embedded);
  applyTheme();translate();
  const boot=()=>{const unit=params.get('unit');if(unit&&P.SUBTOPICS.has(unit))start(unit);else home();};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
