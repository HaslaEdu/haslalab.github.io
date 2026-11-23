/* The study roadmap (#/learn/roadmap), the courses (#/learn/courses) and the contest calendar (#/olympiad/schedule):
   reference pages drawn from data/roadmap.json, data/courses.json (tools/build-courses.cjs) and data/schedule.json.
   Each view returns its frame at once and fills it when the data arrives.
   window.HL_GUIDES = {roadmapView, roadmapMount, coursesView, coursesMount, scheduleView, scheduleMount}. */
(function(){
  'use strict';
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const ko=()=>typeof lang==='undefined'||lang==='ko';
  const get=(()=>{const cache={};return f=>cache[f]||(cache[f]=fetch(f,{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error(f);return r.json();}).catch(e=>{delete cache[f];throw e;}));})();
  const safe=u=>/^https:\/\/[^\s"'<>]+$/.test(u||'')?u:'';
  /* where each stage meets HaslaLab's own practice */
  const OURS={
    start:[['#/learn/practice',{ko:'오늘의 문제',en:"Today's problems"}],['#/learn/concepts',{ko:'개념 시뮬레이션',en:'Concept simulations'}]],
    school:[['#/learn/practice?mode=tracks&track=ap1',{ko:'AP Physics 1',en:'AP Physics 1'}],['#/learn/practice?mode=tracks&track=ap2',{ko:'AP Physics 2',en:'AP Physics 2'}]],
    exam:[['#/learn/practice?mode=tracks&track=apcm',{ko:'AP Physics C: 역학',en:'AP Physics C: Mechanics'}],['#/learn/practice?mode=tracks&track=jeem',{ko:'JEE Main',en:'JEE Main'}]],
    olympiad1:[['#/learn/practice?mode=tracks&track=fma',{ko:'F=ma 형식',en:'F=ma style'}],['#/learn/practice?mode=diag',{ko:'내 수준 찾기',en:'Find your level'}]],
    olympiad2:[['#/learn/practice?mode=tracks&track=usapho',{ko:'USAPhO 형식',en:'USAPhO style'}],['#/learn/practice?mode=contest',{ko:'대회 기출 599문제',en:'599 competition problems'}],['#/comps',{ko:'대회 아카이브',en:'Contest archive'}]],
    undergrad:[['#/learn/practice?mode=bank',{ko:'교재 · 대학 문제',en:'Textbook and university problems'}],['#/learn/compute',{ko:'계산물리',en:'Computational physics'}]],
    upper:[['#/learn/practice?mode=bank',{ko:'교재 · 대학 문제 (★4–5)',en:'Textbook problems (★4–5)'}]]
  };
  const STAGE={start:{ko:'처음 배우는 물리',en:'A first physics course'},school:{ko:'고등학교 물리',en:'High-school physics'},exam:{ko:'입시: AP · JEE',en:'Entrance exams: AP, JEE'},
    olympiad1:{ko:'올림피아드 1단계: F=ma · 국내 예선',en:'Olympiad, first round: F=ma and national qualifiers'},olympiad2:{ko:'올림피아드 2단계: USAPhO · APhO · IPhO',en:'Olympiad, final rounds: USAPhO, APhO, IPhO'},
    undergrad:{ko:'학부 1–2학년',en:'University, years 1–2'},upper:{ko:'학부 3–4학년',en:'University, years 3–4'}};
  const stageName=k=>STAGE[k]?(ko()?STAGE[k].ko:STAGE[k].en):k;
  const KIND={handout:{ko:'핸드아웃',en:'Handout'},book:{ko:'책',en:'Book'},course:{ko:'강의',en:'Course'},problems:{ko:'문제',en:'Problems'},video:{ko:'영상',en:'Video'},tool:{ko:'도구',en:'Tool'}};
  const pick=(o,k)=>ko()?(o[k+'_ko']||o[k]):(o[k]||o[k+'_ko']);
  /* tabs: the roadmap's own tab row (index.html adds the unit map as a second tab) */
  function roadmapView(tabs){
    const K=ko();
    return `<div class="shell guide"><div class="phead"><p class="eyebrow"><a href="#/learn">${K?'학습':'Learn'}</a> / ${K?'로드맵':'Roadmap'}</p><h1>${K?'물리 공부 로드맵':'A roadmap for physics'}</h1>
      <p class="lede">${K?'처음 배우는 물리부터 입시, 올림피아드, 학부까지 단계마다 무엇을 공부하고 무엇으로 연습할지 정리했습니다. 외부 자료는 저자가 무료로 공개한 것 위주이고, 링크는 원래 사이트로 갑니다.':'What to study at each stage, from a first physics course through entrance exams and olympiads to university, and where to practise it. Outside material is mostly free from its authors; links go to their own sites.'}</p></div>${tabs||''}
      <div id="roadmap"><p class="note">${K?'불러오는 중…':'Loading…'}</p></div></div>`;
  }
  async function roadmapMount(){
    const box=document.getElementById('roadmap');if(!box)return;const K=ko();
    let d;try{d=await get('data/roadmap.json');}catch(e){box.innerHTML=`<p class="note">${K?'로드맵을 불러오지 못했습니다.':'Could not load the roadmap.'}</p>`;return;}
    if(!document.body.contains(box))return;
    const res=r=>{const u=safe(r.url);return `<li><span class="rk">${esc(pick(KIND[r.kind]||{ko:r.kind,en:r.kind},K?'ko':'en'))}</span>${u?`<a href="${esc(u)}" target="_blank" rel="noopener">${esc(r.title)}</a>`:`<b>${esc(r.title)}</b>`}${r.author?` <small>${esc(r.author)}</small>`:''}${r.free===false?` <small class="paid">${K?'유료':'paid'}</small>`:''}${pick(r,'note')?`<p>${esc(pick(r,'note'))}</p>`:''}</li>`;};
    box.innerHTML=`<ol class="rm-stages">${d.stages.map((s,i)=>`<li class="rm-stage" id="rm-${esc(s.key)}"><div class="rm-num">${i+1}</div><div class="rm-body">
        <h2>${esc(pick(s,'name')||stageName(s.key))}</h2><p class="rm-goal">${esc(pick(s,'goal'))}</p>
        ${(s.topics||[]).length?`<p class="rm-topics">${s.topics.map(t=>`<span>${esc(typeof t==='string'?t:pick(t,'name'))}</span>`).join('')}</p>`:''}
        ${OURS[s.key]?`<p class="rm-ours"><b>${K?'하슬라랩에서 연습':'Practise on HaslaLab'}</b> ${OURS[s.key].map(([h,n])=>`<a href="${h}">${esc(K?n.ko:n.en)}</a>`).join('')}</p>`:''}
        <ul class="rm-res">${(s.resources||[]).map(res).join('')}</ul></div></li>`).join('')}</ol>
      ${(d.math||[]).length?`<section class="rm-math"><h2>${K?'수학은 언제 무엇을':'Which math, and when'}</h2>${d.math.map(m=>`<div><h3>${esc(stageName(m.stage))}</h3><p>${esc(pick(m,'note'))}</p>${(m.learn||[]).length?`<p class="rm-topics">${m.learn.map(t=>`<span>${esc(t)}</span>`).join('')}</p>`:''}<ul class="rm-res">${(m.resources||[]).map(res).join('')}</ul></div>`).join('')}</section>`:''}
      <p class="note">${K?'기준일':'As of'} ${esc(d.as_of||'')}. ${K?'빠진 자료나 끊긴 링크는 커뮤니티 질문 게시판에 알려 주세요.':'Report a missing resource or a broken link on the community Q&A board.'}</p>`;
    /* a course's link to one stage (#/learn/roadmap?stage=exam) */
    const st=new URLSearchParams(location.hash.split('?')[1]||'').get('stage'),el=st&&/^[a-z0-9]+$/.test(st)&&document.getElementById('rm-'+st);
    if(el){el.classList.add('rm-focus');el.scrollIntoView({block:'start'});}
  }

  /* ── the courses: one per study level, its units in order, each with its problems and simulations; video lectures later ── */
  const tl=o=>!o?'':ko()?(o.ko??o.en):(typeof LX==='function'?LX(o.en??o.ko):(o.en??o.ko));
  const LEVEL_KEY=/^L[1-4]$/;
  function coursesView(){
    const K=ko();
    return `<div class="shell guide courses"><div class="phead"><p class="eyebrow"><a href="#/learn">${K?'학습':'Learn'}</a> / ${K?'강좌':'Courses'}</p><h1>${K?'강좌':'Courses'}</h1>
      <p class="lede">${K?'레벨마다 단원을 공부할 순서대로 묶었습니다. 단원마다 그 레벨의 연습 문제와 개념 시뮬레이션, 계산물리 문제가 연결됩니다.':'The units of each level in the order to study them. Each unit links that level\'s practice problems, and its concept simulation and computational problem where there is one.'}</p>
      <p class="co-soon" role="note"><b>${K?'강의 영상 준비 중':'Video lectures coming'}</b> ${K?'아직 강의 영상은 없습니다. 지금은 문제, 시뮬레이션, 로드맵 자료로 공부합니다.':'There are no video lectures yet. For now each course is its problems, simulations and roadmap resources.'}</p></div>
      <div id="courses"><p class="note">${K?'불러오는 중…':'Loading…'}</p></div></div>`;
  }
  async function coursesMount(){
    const box=document.getElementById('courses');if(!box)return;const K=ko();
    let d,rm=null;try{[d,rm]=await Promise.all([get('data/courses.json'),get('data/roadmap.json').catch(()=>null)]);}catch(e){box.innerHTML=`<p class="note">${K?'강좌를 불러오지 못했습니다.':'Could not load the courses.'}</p>`;return;}
    if(!document.body.contains(box))return;
    const P=window.HL_LEARN_PATH,unitName=u=>{const x=P?.SUBTOPICS.get(u);return x?tl(x.sub.name):u;},areaName=a=>tl(P?.AREAS.find(x=>x.key===a)?.name)||a;
    const simsOf=u=>d.sims.filter(x=>x.u===u),codeOf=u=>d.compute.filter(x=>x.u===u);
    const extra=list=>list.map(x=>`<a class="co-sim" href="#/learn/concepts?sim=${esc(x.id)}">${K?'시뮬레이션':'Simulation'}: ${esc(tl(x.name))}</a>`).join('');
    const code=list=>list.map(x=>`<a class="co-code" href="#/learn/compute?problem=${esc(x.id)}">${K?'계산물리':'Computational'}: ${esc(tl(x.name))}</a>`).join('');
    let level=new URLSearchParams(location.hash.split('?')[1]||'').get('level');if(!LEVEL_KEY.test(level||''))level='L1';
    const paint=()=>{
      const L=d.levels.find(x=>x.key===level)||d.levels[0],n=L.key.slice(1);
      const has=(K?L.has.ko:L.has.en)||[],soon=(K?L.soon.ko:L.soon.en)||[];
      const groups=[];for(const u of L.units){const a=u.u.split('/')[0];let g=groups.find(x=>x.a===a);if(!g)groups.push(g={a,units:[]});g.units.push(u);}
      let i=0;
      const unitRows=groups.map(g=>`<li class="co-area"><h3>${esc(areaName(g.a))}</h3><ol class="co-units">${g.units.map(u=>`<li><span class="co-no mono">${++i}</span><div><b>${esc(unitName(u.u))}</b>
          <span class="co-meta">${K?`문제 ${u.n}개 · 단계 ${u.steps[0]}${u.steps[1]!==u.steps[0]?'–'+u.steps[1]:''}`:`${u.n} problem${u.n===1?'':'s'} · step ${u.steps[0]}${u.steps[1]!==u.steps[0]?'–'+u.steps[1]:''}`}</span>
          <span class="co-links"><a href="#/learn/practice?mode=custom&amp;level=${L.key}&amp;unit=${esc(u.u)}">${K?'문제 풀기':'Practise'}</a>${extra(simsOf(u.u))}${code(codeOf(u.u))}</span></div></li>`).join('')}</ol></li>`).join('');
      const areaRows=L.areas.map(x=>{const inArea=list=>list.filter(y=>y.u.startsWith(x.area+'/'));return `<li><span class="co-no mono">${++i}</span><div><b>${esc(areaName(x.area))}</b>
          <span class="co-links"><a href="#/learn/physics/search?subject=${esc(x.bank)}">${K?'교재 · 대학 문제 찾기':'Find textbook and university problems'}</a>${extra(inArea(d.sims))}${code(inArea(d.compute))}</span></div></li>`;}).join('');
      const contests=L.contests.filter(c=>c.n).map(c=>`<li><a href="#/learn/practice?mode=contest">${esc(tl(d.contestNames[c.key]))}</a> <span class="co-meta">${K?`${c.n}문제`:`${c.n} problems`}</span></li>`).join('');
      const stages=(rm?.stages||[]).filter(s=>L.roadmap.includes(s.key));
      const res=r=>{const u=safe(r.url);return `<li>${u?`<a href="${esc(u)}" target="_blank" rel="noopener">${esc(r.title)}</a>`:esc(r.title)}${r.author?` <small>${esc(r.author)}</small>`:''}</li>`;};
      box.innerHTML=`<div class="co-tabs" role="tablist" aria-label="${K?'레벨':'Levels'}">${d.levels.map(x=>`<button type="button" role="tab" data-level="${x.key}" aria-selected="${x.key===L.key}"><span class="mono">${K?'레벨':'Level'} ${x.key.slice(1)}</span>${esc(tl(x.name))}</button>`).join('')}</div>
        <section class="co-course" aria-labelledby="coH"><h2 id="coH">${K?'레벨':'Level'} ${n} · ${esc(tl(L.name))}</h2>
          <p class="co-has">${K?'들어 있는 문제':'In the bank'}: ${has.map(esc).join(' · ')}${soon.length?` <span class="co-later">${soon.map(x=>`<span class="tag">${K?'준비 중':'coming'}</span> ${esc(x)}`).join(' ')}</span>`:''}</p>
          <p><a class="hm-go" href="#/learn/practice?mode=custom&amp;level=${L.key}">${K?'이 레벨 문제로 세트 시작':'Start a set at this level'}</a></p>
          ${L.units.length?`<h3 class="co-h">${K?'단원 순서':'Units in order'}</h3><ol class="co-groups">${unitRows}</ol>`:''}
          ${L.areas.length?`<h3 class="co-h">${K?'분야 순서':'Fields in order'}</h3><p class="note">${K?'이 레벨의 교재 · 대학 문제는 문제 은행에 분야별로 있습니다.':'This level\'s textbook and university problems are in the problem bank, by field.'}</p><ol class="co-units">${areaRows}</ol>`:''}
          ${contests?`<h3 class="co-h">${K?'대회 기출':'Competition problems'}</h3><ul class="co-contests">${contests}</ul>`:''}
          ${stages.length?`<h3 class="co-h">${K?'로드맵 자료':'Roadmap resources'}</h3>${stages.map(s=>`<details class="co-rm"><summary><a href="#/learn/roadmap?stage=${esc(s.key)}">${esc(pick(s,'name')||stageName(s.key))}</a> <span class="co-meta">${K?`자료 ${(s.resources||[]).length}개`:`${(s.resources||[]).length} resources`}</span></summary><ul>${(s.resources||[]).map(res).join('')}</ul></details>`).join('')}`:''}
        </section>`;
      box.querySelectorAll('[data-level]').forEach(b=>b.onclick=()=>{level=b.dataset.level;try{history.replaceState(null,'','#/learn/courses?level='+level);}catch(e){}paint();});
    };
    paint();
  }

  /* ── the calendar: a row per event, the date if announced, otherwise the usual month ── */
  const MONTHS={ko:['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월'],en:['January','February','March','April','May','June','July','August','September','October','November','December']};
  const KINDS=[['all',{ko:'전체',en:'All'}],['international',{ko:'국제 올림피아드',en:'International'}],['regional',{ko:'지역 · 온라인',en:'Regional and online'}],['national',{ko:'각국 선발',en:'National rounds'}],['entrance',{ko:'입시',en:'Entrance exams'}]];
  const kindOf=e=>e.kind==='online'?'regional':e.kind==='selection'?'national':e.kind;
  function scheduleView(){
    const K=ko();
    return `<div class="shell guide"><div class="phead"><p class="eyebrow"><a href="#/olympiad">${K?'올림피아드':'Olympiad'}</a> / ${K?'대회 일정':'Calendar'}</p><h1>${K?'대회 · 시험 일정':'Contest and exam calendar'}</h1>
      <p class="lede">${K?'국제 올림피아드, 각국 선발 시험, 물리가 들어가는 입시의 다음 날짜입니다. 공식 발표가 없는 것은 보통 열리는 달로 적었습니다. 날짜는 바뀔 수 있으니 공식 사이트에서 확인하세요.':'The next dates of the international olympiads, national selection rounds and entrance exams with physics. Where nothing is announced yet, the usual month is shown. Dates change; check the official site.'}</p></div>
      <div class="sc-filters" id="scFilters"></div><div id="schedule"><p class="note">${K?'불러오는 중…':'Loading…'}</p></div></div>`;
  }
  async function scheduleMount(){
    const box=document.getElementById('schedule'),bar=document.getElementById('scFilters');if(!box)return;const K=ko();
    let d;try{d=await get('data/schedule.json');}catch(e){box.innerHTML=`<p class="note">${K?'일정을 불러오지 못했습니다.':'Could not load the calendar.'}</p>`;return;}
    if(!document.body.contains(box))return;
    const today=new Date().toISOString().slice(0,10);
    const monthOf=e=>e.start?Number(e.start.slice(5,7)):(()=>{const m=MONTHS.en.findIndex(n=>String(e.typical||'').toLowerCase().startsWith(n.toLowerCase()));return m>=0?m+1:13;})();
    const ev=[...d.events].map(e=>({...e,_m:monthOf(e),_y:e.start?Number(e.start.slice(0,4)):null})).filter(e=>!e.end||e.end>=today||!e.start||e.start>=today);
    let kind='all',country='';
    const countries=[...new Set(ev.map(e=>e.country).filter(c=>c&&c!=='intl'))].sort();
    const date=e=>{
      if(e.start){
        const [y,m,dd]=e.start.split('-').map(Number),[y2,m2,d2]=(e.end||e.start).split('-').map(Number),one=e.end===e.start||!e.end;
        if(K)return `<b>${y}년 ${m}월 ${dd}일${one?'':` – ${y2!==y?y2+'년 ':''}${m2!==m||y2!==y?m2+'월 ':''}${d2}일`}</b>`;
        const M=n=>MONTHS.en[n-1].slice(0,3);
        return `<b>${M(m)} ${dd}${one?'':` – ${m2!==m?M(m2)+' ':''}${d2}`}, ${y2}</b>`;
      }
      return `<span class="tba">${K?'미정 · 보통 ':'TBA · usually '}${esc(K?e.typical_ko||e.typical||'':e.typical||'')}</span>`;
    };
    const paint=()=>{
      bar.innerHTML=`<div class="seg">${KINDS.map(([k,n])=>`<button type="button" data-k="${k}" class="${k===kind?'on':''}">${K?n.ko:n.en}</button>`).join('')}</div>
        <select id="scCountry" aria-label="${K?'나라':'Country'}"><option value="">${K?'모든 나라':'All countries'}</option>${countries.map(c=>`<option value="${c}"${c===country?' selected':''}>${c.toUpperCase()}</option>`).join('')}</select>`;
      bar.querySelectorAll('[data-k]').forEach(b=>b.onclick=()=>{kind=b.dataset.k;paint();});
      document.getElementById('scCountry').onchange=e=>{country=e.target.value;paint();};
      const rows=ev.filter(e=>(kind==='all'||kindOf(e)===kind)&&(!country||e.country===country||e.country==='intl'&&kind==='international'));
      rows.sort((a,b)=>(a.start||'9999')<(b.start||'9999')?-1:(a.start||'9999')>(b.start||'9999')?1:a._m-b._m);
      box.innerHTML=rows.length?`<table class="sc-table"><thead><tr><th>${K?'날짜':'Date'}</th><th>${K?'대회 · 시험':'Event'}</th><th>${K?'종류':'Kind'}</th><th>${K?'장소':'Where'}</th></tr></thead><tbody>${rows.map(e=>`<tr>
          <td>${date(e)}</td><td>${safe(e.url)?`<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(K?e.name_ko||e.name:e.name)}</a>`:esc(K?e.name_ko||e.name:e.name)}${K?'':`<small>${esc(e.level||'')}</small>`}</td>
          <td><span class="sc-kind ${kindOf(e)}">${esc((KINDS.find(k=>k[0]===kindOf(e))||[0,{ko:e.kind,en:e.kind}])[1][K?'ko':'en'])}</span></td>
          <td>${e.country&&e.country!=='intl'&&typeof flagImg==='function'?flagImg(e.country,'sc-flag'):''} ${esc(e.host||(e.country==='intl'?'':e.country.toUpperCase()))}</td></tr>`).join('')}</tbody></table>`:`<p class="note">${K?'해당하는 일정이 없습니다.':'Nothing matches.'}</p>`;
    };
    paint();
    box.insertAdjacentHTML('afterend',`<p class="note">${K?'기준일':'As of'} ${esc(d.as_of||'')}. ${K?'날짜가 바뀌었거나 빠진 대회가 있으면 커뮤니티에 알려 주세요.':'If a date has changed or a contest is missing, tell us in the community.'}</p>`);
  }
  window.HL_GUIDES={roadmapView,roadmapMount,coursesView,coursesMount,scheduleView,scheduleMount};
})();
