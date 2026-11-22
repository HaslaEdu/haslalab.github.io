/* The study roadmap (#/learn/roadmap) and the contest calendar (#/olympiad/schedule): two reference pages drawn from
   data/roadmap.json and data/schedule.json. Each view returns its frame at once and fills it when the data arrives.
   window.HL_GUIDES = {roadmapView, roadmapMount, scheduleView, scheduleMount}. */
(function(){
  'use strict';
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const ko=()=>typeof lang==='undefined'||lang==='ko';
  const get=(()=>{const cache={};return f=>cache[f]||(cache[f]=fetch(f,{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error(f);return r.json();}).catch(e=>{delete cache[f];throw e;}));})();
  const safe=u=>/^https:\/\/[^\s"'<>]+$/.test(u||'')?u:'';
  /* where each stage meets HaslaLab's own practice */
  const OURS={
    start:[['#/',{ko:'오늘의 문제',en:"Today's problems"}],['#/learn/concepts',{ko:'개념 시뮬레이션',en:'Concept simulations'}]],
    school:[['#/learn/practice?mode=tracks&track=ap1',{ko:'AP Physics 1',en:'AP Physics 1'}],['#/learn/practice?mode=tracks&track=ap2',{ko:'AP Physics 2',en:'AP Physics 2'}]],
    exam:[['#/learn/practice?mode=tracks&track=apcm',{ko:'AP Physics C: 역학',en:'AP Physics C: Mechanics'}],['#/learn/practice?mode=tracks&track=jeem',{ko:'JEE Main',en:'JEE Main'}]],
    olympiad1:[['#/learn/practice?mode=tracks&track=fma',{ko:'F=ma 형식',en:'F=ma style'}],['#/learn/practice?mode=diag',{ko:'내 수준 찾기',en:'Find your level'}]],
    olympiad2:[['#/learn/practice?mode=tracks&track=usapho',{ko:'USAPhO 형식',en:'USAPhO style'}],['#/learn/practice?mode=contest',{ko:'대회 기출 599문제',en:'599 competition problems'}],['#/comps',{ko:'대회 아카이브',en:'Contest archive'}]],
    undergrad:[['#/learn/practice?mode=bank',{ko:'교재 · 대학 문제',en:'Textbook and university problems'}],['#/learn/compute',{ko:'계산물리',en:'Computational physics'}]],
    upper:[['#/learn/practice?mode=bank',{ko:'교재 · 대학 문제 (★4–5)',en:'Textbook problems (★4–5)'}]]
  };
  const KIND={handout:{ko:'핸드아웃',en:'Handout'},book:{ko:'책',en:'Book'},course:{ko:'강의',en:'Course'},problems:{ko:'문제',en:'Problems'},video:{ko:'영상',en:'Video'},tool:{ko:'도구',en:'Tool'}};
  const pick=(o,k)=>ko()?(o[k+'_ko']||o[k]):(o[k]||o[k+'_ko']);
  function roadmapView(){
    const K=ko();
    return `<div class="shell guide"><div class="phead"><p class="eyebrow"><a href="#/">${K?'학습':'Learn'}</a> / ${K?'로드맵':'Roadmap'}</p><h1>${K?'물리 공부 로드맵':'A roadmap for physics'}</h1>
      <p class="lede">${K?'처음 배우는 물리부터 입시, 올림피아드, 학부까지 단계마다 무엇을 공부하고 무엇으로 연습할지 정리했습니다. 외부 자료는 저자가 무료로 공개한 것 위주이고, 링크는 원래 사이트로 갑니다.':'What to study at each stage, from a first physics course through entrance exams and olympiads to university, and where to practise it. Outside material is mostly free from its authors; links go to their own sites.'}</p></div>
      <div id="roadmap"><p class="note">${K?'불러오는 중…':'Loading…'}</p></div></div>`;
  }
  async function roadmapMount(){
    const box=document.getElementById('roadmap');if(!box)return;const K=ko();
    let d;try{d=await get('data/roadmap.json');}catch(e){box.innerHTML=`<p class="note">${K?'로드맵을 불러오지 못했습니다.':'Could not load the roadmap.'}</p>`;return;}
    if(!document.body.contains(box))return;
    const res=r=>{const u=safe(r.url);return `<li><span class="rk">${esc(pick(KIND[r.kind]||{ko:r.kind,en:r.kind},K?'ko':'en'))}</span>${u?`<a href="${esc(u)}" target="_blank" rel="noopener">${esc(r.title)}</a>`:`<b>${esc(r.title)}</b>`}${r.author?` <small>${esc(r.author)}</small>`:''}${r.free===false?` <small class="paid">${K?'유료':'paid'}</small>`:''}${pick(r,'note')?`<p>${esc(pick(r,'note'))}</p>`:''}</li>`;};
    box.innerHTML=`<ol class="rm-stages">${d.stages.map((s,i)=>`<li class="rm-stage" id="rm-${esc(s.key)}"><div class="rm-num">${i+1}</div><div class="rm-body">
        <h2>${esc(pick(s,'name')||s.key)}</h2><p class="rm-goal">${esc(pick(s,'goal'))}</p>
        ${(s.topics||[]).length?`<p class="rm-topics">${s.topics.map(t=>`<span>${esc(typeof t==='string'?t:pick(t,'name'))}</span>`).join('')}</p>`:''}
        ${OURS[s.key]?`<p class="rm-ours"><b>${K?'하슬라랩에서 연습':'Practise on HaslaLab'}</b> ${OURS[s.key].map(([h,n])=>`<a href="${h}">${esc(K?n.ko:n.en)}</a>`).join('')}</p>`:''}
        <ul class="rm-res">${(s.resources||[]).map(res).join('')}</ul></div></li>`).join('')}</ol>
      ${(d.math||[]).length?`<section class="rm-math"><h2>${K?'수학은 언제 무엇을':'Which math, and when'}</h2>${d.math.map(m=>`<div><h3>${esc(pick(m,'stage')||pick(m,'name')||'')}</h3><p>${esc(pick(m,'goal')||pick(m,'note')||'')}</p><ul class="rm-res">${(m.resources||[]).map(res).join('')}</ul></div>`).join('')}</section>`:''}
      <p class="note">${K?'기준일':'As of'} ${esc(d.as_of||'')}. ${K?'빠진 자료나 끊긴 링크는 커뮤니티 질문 게시판에 알려 주세요.':'Report a missing resource or a broken link on the community Q&A board.'}</p>`;
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
      if(e.start){const f=s=>`${Number(s.slice(5,7))}${K?'월 ':'/'}${Number(s.slice(8,10))}${K?'일':''}`;return `<b>${e.start.slice(0,4)}. ${f(e.start)}${e.end&&e.end!==e.start?' – '+f(e.end):''}</b>`;}
      return `<span class="tba">${K?'미정 · 보통 ':'TBA · usually '}${esc(e.typical||'')}</span>`;
    };
    const paint=()=>{
      bar.innerHTML=`<div class="seg">${KINDS.map(([k,n])=>`<button type="button" data-k="${k}" class="${k===kind?'on':''}">${K?n.ko:n.en}</button>`).join('')}</div>
        <select id="scCountry" aria-label="${K?'나라':'Country'}"><option value="">${K?'모든 나라':'All countries'}</option>${countries.map(c=>`<option value="${c}"${c===country?' selected':''}>${c.toUpperCase()}</option>`).join('')}</select>`;
      bar.querySelectorAll('[data-k]').forEach(b=>b.onclick=()=>{kind=b.dataset.k;paint();});
      document.getElementById('scCountry').onchange=e=>{country=e.target.value;paint();};
      const rows=ev.filter(e=>(kind==='all'||kindOf(e)===kind)&&(!country||e.country===country||e.country==='intl'&&kind==='international'));
      rows.sort((a,b)=>(a.start||'9999')<(b.start||'9999')?-1:(a.start||'9999')>(b.start||'9999')?1:a._m-b._m);
      box.innerHTML=rows.length?`<table class="sc-table"><thead><tr><th>${K?'날짜':'Date'}</th><th>${K?'대회 · 시험':'Event'}</th><th>${K?'종류':'Kind'}</th><th>${K?'장소':'Where'}</th></tr></thead><tbody>${rows.map(e=>`<tr>
          <td>${date(e)}</td><td>${safe(e.url)?`<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(K?e.name_ko||e.name:e.name)}</a>`:esc(K?e.name_ko||e.name:e.name)}<small>${esc(e.level||'')}</small></td>
          <td><span class="sc-kind ${kindOf(e)}">${esc((KINDS.find(k=>k[0]===kindOf(e))||[0,{ko:e.kind,en:e.kind}])[1][K?'ko':'en'])}</span></td>
          <td>${e.country&&e.country!=='intl'&&typeof flagImg==='function'?flagImg(e.country,'sc-flag'):''} ${esc(e.host||'')}</td></tr>`).join('')}</tbody></table>`:`<p class="note">${K?'해당하는 일정이 없습니다.':'Nothing matches.'}</p>`;
    };
    paint();
    box.insertAdjacentHTML('afterend',`<p class="note">${K?'기준일':'As of'} ${esc(d.as_of||'')}. ${K?'날짜가 바뀌었거나 빠진 대회가 있으면 커뮤니티에 알려 주세요.':'If a date has changed or a contest is missing, tell us in the community.'}</p>`);
  }
  window.HL_GUIDES={roadmapView,roadmapMount,scheduleView,scheduleMount};
})();
