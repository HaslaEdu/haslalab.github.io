/* Creations: members make simulations, virtual experiments and Python problems, and anyone plays and solves them, the
   way Scratch works for games. Three views on one page: the gallery, a creation (play it, answer its question or run
   code against its grader), and the editor. Code from other members runs only in sim-sandbox.html (a sandboxed frame
   with no network) or in the Pyodide worker (compute-worker.js). The server is community/src/creations.js. */
(()=>{
  'use strict';
  const $=id=>document.getElementById(id),params=new URL(location.href).searchParams;
  const embedded=params.get('embed')==='1'&&window.parent!==window;
  const lang=params.get('lang')==='en'?'en':'ko',dark=params.get('theme')==='dark';
  document.documentElement.lang=lang;document.documentElement.dataset.theme=dark?'dark':'light';document.documentElement.classList.toggle('embedded',embedded);
  const T={
    ko:{ours:'하슬라랩이 만든 것:',oursSim:'개념 시뮬레이션 6개',oursCode:'계산물리 6문제',title:'만들기',lede:'회원이 만든 시뮬레이션, 가상 실험, 계산물리 문제입니다. 직접 만들어 올리면 다른 사람이 풀고 리믹스할 수 있습니다.',
      all:'전체',sim:'시뮬레이션 · 실험',code:'계산물리',newest:'새 작품',popular:'인기',mine:'내 작품',make:'만들기',more:'더 보기',sample:'예시',
      plays:'실행',likes:'좋아요',solves:'해결',by:'만든 사람',back:'← 목록',edit:'편집',hide:'숨기기',hideConfirm:'이 작품을 숨길까요? 목록에서 사라집니다.',remix:'리믹스',like:'좋아요',liked:'좋아요 취소',
      question:'문제',answer:'답',check:'확인',right:'정답입니다.',wrong:'다시 생각해 보세요.',solvedBy:'명이 풀었습니다',
      run:'실행 · 채점',running:'Python을 불러오는 중…',pass:'모두 통과했습니다.',fail:'통과하지 못한 검사가 있습니다.',error:'코드를 실행하다 오류가 났습니다.',timeout:'30초를 넘어 멈췄습니다.',test:'검사',result:'결과',got:'결과값',want:'기대값',
      login:'로그인하면 만들고, 좋아요를 누르고, 푼 기록을 남길 수 있습니다.',loginBtn:'로그인',offline:'서버에 연결하지 못했습니다. 아래 예시는 바로 실행해 볼 수 있습니다.',empty:'아직 작품이 없습니다.',
      kind:'종류',name:'제목',summary:'한 줄 설명',body:'설명 · 문제 (수식은 $...$)',codeSim:'시뮬레이션 코드 (JavaScript)',qText:'질문 (선택: 실험으로 답을 구하게 하려면)',ans:'답 (숫자나 식, 예: 9.8, 2*pi*sqrt(L/g))',unit:'단위',
      starter:'처음 코드 (Python)',grader:'채점 코드 (Python, grade(ns) 함수)',preview:'미리 실행',save:'저장하고 공개',saved:'저장했습니다.',helpers:'쓸 수 있는 도구',template:'예시로 채우기',
      helpSim:'W, H: 화면 크기 · loop(dt => …): 매 프레임 · slider(이름, 최소, 최대, 간격, 값) · button(이름, 함수) · show(이름, 값, 단위) · clear() · circle(x, y, r, 색) · line(x1, y1, x2, y2, 색, 두께) · arrow(…) · text(글, x, y)',
      helpCode:'grade(ns)는 풀이 코드가 만든 이름들(ns)을 받아 {"tests": [{"name", "ok", "got", "want"}]}를 돌려줍니다. 공통 도구: _need(ns, 이름)으로 함수 가져오기, _test(이름, 통과, 결과값, 기대값), _rel(a, b) 상대 오차.',
      err:{bad_title:'제목을 입력하세요.',bad_code:'시뮬레이션 코드를 입력하세요.',bad_grader:'채점 코드에 def grade(ns): 가 있어야 합니다.',bad_body:'문제 설명을 입력하세요.',rate_limited:'잠시 뒤에 다시 시도하세요.',login_required:'로그인이 필요합니다.',not_owner:'내 작품만 고칠 수 있습니다.'}},
    en:{ours:'Made by HaslaLab:',oursSim:'six concept simulations',oursCode:'six Python problems',title:'Create',lede:'Simulations, virtual experiments and computational problems made by members. Make one and others can play it, solve it and remix it.',
      all:'All',sim:'Simulations and experiments',code:'Computational',newest:'Newest',popular:'Popular',mine:'Mine',make:'Make one',more:'More',sample:'Example',
      plays:'plays',likes:'likes',solves:'solved',by:'by',back:'← All creations',edit:'Edit',hide:'Hide',hideConfirm:'Hide this creation? It leaves the list.',remix:'Remix',like:'Like',liked:'Unlike',
      question:'Question',answer:'Answer',check:'Check',right:'Correct.',wrong:'Not yet. Try again.',solvedBy:'people solved it',
      run:'Run and grade',running:'Loading Python…',pass:'All tests passed.',fail:'Some tests failed.',error:'Your code raised an error.',timeout:'Stopped after 30 seconds.',test:'Test',result:'Result',got:'Got',want:'Expected',
      login:'Log in to make creations, like them and keep your solves.',loginBtn:'Log in',offline:'Could not reach the server. The examples below still run.',empty:'No creations yet.',
      kind:'Kind',name:'Title',summary:'One-line summary',body:'Description or problem ($...$ for math)',codeSim:'Simulation code (JavaScript)',qText:'Question (optional, for a virtual experiment)',ans:'Answer (a number or a formula, e.g. 9.8, 2*pi*sqrt(L/g))',unit:'Unit',
      starter:'Starter code (Python)',grader:'Grader (Python, a grade(ns) function)',preview:'Run it',save:'Save and publish',saved:'Saved.',helpers:'Helpers',template:'Fill in an example',
      helpSim:'W, H: canvas size · loop(dt => …): every frame · slider(label, min, max, step, value) · button(label, fn) · show(label, value, unit) · clear() · circle(x, y, r, color) · line(x1, y1, x2, y2, color, width) · arrow(…) · text(s, x, y)',
      helpCode:'grade(ns) gets the names the solution defined (ns) and returns {"tests": [{"name", "ok", "got", "want"}]}. Shared helpers: _need(ns, name) to fetch a function, _test(name, ok, got, want), _rel(a, b) for relative error.',
      err:{bad_title:'Enter a title.',bad_code:'Enter the simulation code.',bad_grader:'The grader needs a def grade(ns): function.',bad_body:'Enter the problem statement.',rate_limited:'Try again in a moment.',login_required:'Log in first.',not_owner:'You can only edit your own.'}}
  }[lang];
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const API=(()=>{let o='';try{o=localStorage.getItem('hlCmApi')||'';}catch(e){}return(/^https:\/\/[a-z0-9-]+\.haslalab\.workers\.dev\/?$/.test(o)?o:'https://haslalab-community-edge.haslalab.workers.dev').replace(/\/+$/,'');})();
  const token=()=>{try{const v=localStorage.getItem('hlCmTok')||'';return /^[A-Za-z0-9_-]{20,4096}$/.test(v)?v:'';}catch(e){return '';}};
  async function api(path,method='GET',body){
    const r=await fetch(API+path,{method,headers:{...(token()?{Authorization:'Bearer '+token()}:{}),...(body?{'content-type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});
    const j=await r.json().catch(()=>({}));if(!r.ok)throw Object.assign(new Error(j.error||'api '+r.status),{code:j.error,status:r.status});return j;
  }
  const errText=e=>T.err[e.code]||e.message||'error';
  function height(){if(embedded)requestAnimationFrame(()=>window.parent.postMessage({type:'hl-create-height',height:Math.ceil(document.querySelector('main').getBoundingClientRect().bottom+scrollY+16)},location.origin));}
  if(typeof ResizeObserver==='function')new ResizeObserver(height).observe(document.body);
  const typeset=el=>{try{window.renderMathInElement?.(el,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false});}catch(e){}};
  const textHtml=t=>esc(t).split(/\n{2,}/).map(p=>'<p>'+p.replace(/\n/g,'<br>')+'</p>').join('');
  const go=(view,id)=>{const u=new URL(location.href);u.searchParams.set('view',view);if(id!=null)u.searchParams.set('id',id);else u.searchParams.delete('id');history.pushState(null,'',u);route();};

  /* two examples that run without the server, and the starting point of a new creation */
  const SAMPLES=[
    {id:'sample-pendulum',sample:true,kind:'sim',title:lang==='ko'?'진자의 주기 재기':'Measure a pendulum’s period',nickname:'HaslaLab',
      summary:lang==='ko'?'줄 길이를 바꾸며 10번 흔들리는 시간을 재 보세요.':'Change the length and time ten swings.',
      body:lang==='ko'?'줄 길이를 1.00 m로 두고 진자가 10번 왕복하는 시간을 재세요. 주기 T는 몇 초입니까? (작은 진폭, g = 9.8 m/s²)':'Set the length to 1.00 m and time ten swings. What is the period T in seconds? (Small amplitude, g = 9.8 m/s².)',
      answer:'2*pi*sqrt(1/9.8)',unit:'s',
      code:`const L=slider('L (m)',0.2,2,0.05,1), A=slider('amplitude (°)',5,60,1,10);
let th=null, w=0, t=0, swings=0, prev=0;
button('reset',()=>{th=null;});
loop(dt=>{
  const g=9.8, len=L();
  if(th===null){th=A()*Math.PI/180;w=0;t=0;swings=0;prev=0;}
  for(let i=0;i<10;i++){const h=dt/10;w+=-g/len*Math.sin(th)*h;th+=w*h;t+=h;if(prev<0&&w>=0)swings++;prev=w;}
  clear();
  const ox=W/2, oy=30, s=(H-60)/2.1, x=ox+len*s*Math.sin(th), y=oy+len*s*Math.cos(th);
  line(ox-60,oy,ox+60,oy,'#657187',3); line(ox,oy,x,y,'#263247',1.5); circle(x,y,12);
  show('t',t,'s'); show('swings',swings);
});`},
    {id:'sample-euler',sample:true,kind:'code',title:lang==='ko'?'오일러 방법으로 낙하':'A falling ball by Euler steps',nickname:'HaslaLab',
      summary:lang==='ko'?'공기 저항 없는 낙하를 시간 간격 dt로 계산합니다.':'Free fall, one time step at a time.',
      body:lang==='ko'?'정지 상태에서 떨어지는 공의 높이를 오일러 방법으로 계산하는 함수 `fall(h0, dt, T)`를 작성하세요. 시간 T 뒤의 높이를 돌려줍니다. $g = 9.8$ m/s², 저항 없음. dt가 작으면 결과가 $h_0 - \\tfrac12 g T^2$에 가까워야 합니다.':'Write `fall(h0, dt, T)` that steps a ball dropped from rest with Euler’s method and returns its height after time T. $g = 9.8$ m/s², no drag. For small dt the result should approach $h_0 - \\tfrac12 g T^2$.',
      starter:'def fall(h0, dt, T):\n    h, v, t = h0, 0.0, 0.0\n    while t < T - 1e-12:\n        # one Euler step\n        pass\n    return h\n',
      grader:`def grade(ns):
    fall = _need(ns, "fall")
    tests = []
    for h0, T in [(100.0, 2.0), (20.0, 1.5)]:
        got = fall(h0, 1e-4, T)
        want = h0 - 0.5 * 9.8 * T * T
        tests.append(_test(f"h0={h0}, T={T}", _rel(got, want) < 1e-3, got, want))
    return {"tests": tests}`}
  ];
  const TEMPLATE={sim:SAMPLES[0],code:SAMPLES[1]};

  /* ── gallery ── */
  let cache=new Map();
  async function gallery(){
    const kind=params.get('kind')||'',sort=params.get('sort')||'new',mine=params.get('mine')==='1';
    $('app').innerHTML=`<header class="head"><div><h1>${T.title}</h1><p class="lede">${T.lede}</p><p class="meta">${T.ours} <a href="/#/learn/concepts" target="_top">${T.oursSim}</a> · <a href="/#/learn/compute" target="_top">${T.oursCode}</a></p></div><button type="button" class="primary" id="make">＋ ${T.make}</button></header>
      <nav class="filters"><div class="seg">${[['',T.all],['sim',T.sim],['code',T.code]].map(([k,l])=>`<button type="button" data-kind="${k}" class="${k===kind&&!mine?'on':''}">${l}</button>`).join('')}${token()?`<button type="button" data-mine="1" class="${mine?'on':''}">${T.mine}</button>`:''}</div>
        <div class="seg">${[['new',T.newest],['popular',T.popular]].map(([k,l])=>`<button type="button" data-sort="${k}" class="${k===sort?'on':''}">${l}</button>`).join('')}</div></nav>
      <p class="note" id="gnote"></p><div class="grid" id="grid"></div>`;
    const setQ=(k,v)=>{const u=new URL(location.href);v?u.searchParams.set(k,v):u.searchParams.delete(k);if(k!=='mine')u.searchParams.delete('mine');history.replaceState(null,'',u);for(const x of ['kind','sort','mine'])params.set(x,u.searchParams.get(x)||'');gallery();};
    $('app').querySelectorAll('[data-kind]').forEach(b=>b.onclick=()=>setQ('kind',b.dataset.kind));
    $('app').querySelectorAll('[data-sort]').forEach(b=>b.onclick=()=>setQ('sort',b.dataset.sort));
    $('app').querySelectorAll('[data-mine]').forEach(b=>b.onclick=()=>setQ('mine','1'));
    $('make').onclick=()=>go('edit');
    let items=[];
    try{const q=new URLSearchParams({sort:sort==='popular'?'popular':'new',...(kind?{kind}:{}),...(mine?{mine:'1'}:{})});items=(await api('/api/creations?'+q)).items;}
    catch(e){$('gnote').textContent=T.offline;}
    const samples=mine?[]:SAMPLES.filter(s=>!kind||s.kind===kind);
    const all=[...items,...samples];for(const it of all)cache.set(String(it.id),it);
    $('grid').innerHTML=all.length?all.map(card).join(''):`<p class="note">${T.empty}</p>`;
    $('grid').querySelectorAll('[data-open]').forEach(a=>a.onclick=e=>{e.preventDefault();go('play',a.dataset.open);});
    height();
  }
  const card=it=>`<a class="card" href="?view=play&id=${esc(it.id)}" data-open="${esc(it.id)}"><span class="badge ${it.kind}">${it.kind==='sim'?T.sim:T.code}</span>${it.sample?`<span class="badge sample">${T.sample}</span>`:''}
    <b>${esc(it.title)}</b><span class="sum">${esc(it.summary||'')}</span><span class="meta">${esc(it.nickname||'')}${it.sample?'':` · ▶ ${it.plays||0} · ♥ ${it.likes||0} · ✓ ${it.solves||0}`}</span></a>`;

  /* ── a creation: play the simulation (and answer its question) or solve the Python problem ── */
  async function play(id){
    let c=SAMPLES.find(s=>s.id===id),liked=false,solved=false;
    if(!c){try{const r=await api('/api/creations/'+encodeURIComponent(id));c=r.creation;liked=r.liked;solved=r.solved;}catch(e){$('app').innerHTML=`<p class="note">${esc(errText(e))}</p><button type="button" id="back">${T.back}</button>`;$('back').onclick=()=>go('gallery');height();return;}
      api(`/api/creations/${c.id}/play`,'POST',{}).catch(()=>{});}
    $('app').innerHTML=`<button type="button" class="back" id="back">${T.back}</button>
      <header class="head"><div><span class="badge ${c.kind}">${c.kind==='sim'?T.sim:T.code}</span><h1>${esc(c.title)}</h1><p class="lede">${esc(c.summary||'')}</p>
        <p class="meta">${T.by} ${esc(c.nickname||'')}${c.sample?'':` · ▶ ${c.plays} · ✓ ${c.solves} ${T.solves}`}${c.forked_from?` · <a href="?view=play&id=${c.forked_from}" data-open="${c.forked_from}">${T.remix} #${c.forked_from}</a>`:''}</p></div>
        <div class="acts">${c.sample?'':`<button type="button" id="like" class="${liked?'on':''}">♥ ${c.likes}</button>`}<button type="button" id="remix">${T.remix}</button>${c.mine?`<button type="button" id="edit">${T.edit}</button><button type="button" id="hide">${T.hide}</button>`:''}</div></header>
      <div id="stagebox"></div><div id="qbox"></div>`;
    $('back').onclick=()=>go('gallery');
    $('app').querySelectorAll('[data-open]').forEach(a=>a.onclick=e=>{e.preventDefault();go('play',a.dataset.open);});
    $('remix').onclick=()=>{sessionStorage.setItem('hlCreateDraft',JSON.stringify({...c,id:undefined,forked_from:c.sample?null:c.id,title:c.title+(lang==='ko'?' (리믹스)':' (remix)')}));go('edit');};
    if($('edit'))$('edit').onclick=()=>go('edit',c.id);
    if($('hide'))$('hide').onclick=async()=>{if(!confirm(T.hideConfirm))return;try{await api('/api/creations/'+c.id,'DELETE');go('gallery');}catch(e){alert(errText(e));}};
    if($('like'))$('like').onclick=async()=>{if(!token()){alert(T.login);return;}try{const r=await api(`/api/creations/${c.id}/like`,'POST',{on:!liked});liked=r.liked;$('like').textContent='♥ '+r.likes;$('like').classList.toggle('on',liked);}catch(e){}};
    const done=()=>{if(c.sample||solved||!token())return;solved=true;api(`/api/creations/${c.id}/solve`,'POST',{}).catch(()=>{});};
    if(c.kind==='sim'){runSim($('stagebox'),c.code);if(c.answer)question($('qbox'),c,done);else if(c.body){$('qbox').innerHTML=`<div class="text">${textHtml(c.body)}</div>`;typeset($('qbox'));}}
    else codeProblem($('stagebox'),c,done);
    height();
  }
  /* a simulation runs in sim-sandbox.html: an opaque-origin frame that cannot read this site or reach the network */
  function runSim(box,code){
    box.innerHTML=`<iframe class="sim" sandbox="allow-scripts" src="sim-sandbox.html" title="simulation"></iframe>`;
    const f=box.querySelector('iframe');
    const on=e=>{
      if(e.source!==f.contentWindow)return;
      if(e.data?.type==='sim-ready')f.contentWindow.postMessage({type:'run',code,theme:dark?'dark':'light'},'*');
      if(e.data?.type==='sim-height'&&Number.isFinite(e.data.height)){f.style.height=Math.min(1200,Math.max(380,e.data.height))+'px';height();}
    };
    addEventListener('message',on);
  }
  /* the experiment's question, answered on the same keypad syntax as the practice page (math-input.js) */
  function answerFrom(text){
    const M=window.HL_MATH;let ast;try{ast=M.parse(text);}catch(e){return null;}
    const vars=[...M.vars(ast)];
    if(!vars.length){const v=M.evaluate(ast,{});return Number.isFinite(v)?{kind:'num',value:v}:null;}
    return {kind:'expr',ast,vars};
  }
  function question(box,c,done){
    const ans=answerFrom(c.answer);
    box.innerHTML=`<section class="qcard"><h2>${T.question}</h2><div class="text">${textHtml(c.body||'')}</div>
      <form id="qf" class="ansrow"><input id="qa" autocomplete="off" spellcheck="false" placeholder="${T.answer}">${c.unit?`<span class="unit">${esc(c.unit)}</span>`:''}<button type="submit" class="primary">${T.check}</button></form>
      <div id="qpv" class="preview"></div><p id="qr"></p></section>`;
    typeset(box);
    const M=window.HL_MATH;
    $('qa').oninput=()=>{const t=M.preview($('qa').value);$('qpv').innerHTML=t&&window.katex?katex.renderToString(t,{throwOnError:false}):'';};
    $('qf').onsubmit=e=>{e.preventDefault();if(!ans)return;const r=M.check($('qa').value,ans,0.02);
      $('qr').className=r.ok?'ok':'bad';$('qr').textContent=r.ok?T.right:T.wrong;if(r.ok)done();height();};
  }
  /* a Python problem: the statement, the solver's code and the author's grader, run in Pyodide (compute-worker.js) */
  let worker=null,job=0,timer=0;
  function codeProblem(box,c,done){
    const key='hlCreateCode:'+c.id;let saved='';try{saved=localStorage.getItem(key)||'';}catch(e){}
    box.innerHTML=`<div class="text">${textHtml(c.body||'')}</div>
      <textarea id="code" class="code" spellcheck="false" rows="14">${esc(saved||c.starter||'')}</textarea>
      <div class="row"><button type="button" class="primary" id="run">${T.run}</button><span class="note" id="status"></span></div><div id="results"></div>`;
    typeset(box);
    $('code').onkeydown=e=>{if(e.key==='Tab'&&!e.shiftKey){e.preventDefault();const t=e.target,s=t.selectionStart;t.setRangeText('    ',s,t.selectionEnd,'end');}};
    $('run').onclick=()=>{
      const code=$('code').value;try{localStorage.setItem(key,code);}catch(e){}
      if(!worker)worker=new Worker('compute-worker.js');
      const id=++job;$('run').disabled=true;$('status').textContent=T.running;$('results').innerHTML='';
      const stop=msg=>{clearTimeout(timer);worker?.terminate();worker=null;$('run').disabled=false;$('status').textContent=msg||'';};
      worker.onmessage=ev=>{const m=ev.data;if(m.id!==id)return;
        if(m.phase==='running'){clearTimeout(timer);timer=setTimeout(()=>stop(T.timeout),30000);}
        if(m.phase==='done'){clearTimeout(timer);$('run').disabled=false;$('status').textContent='';results(m.result,m.stdout,done);}};
      worker.onerror=()=>stop(T.error);
      timer=setTimeout(()=>stop(T.timeout),120000);
      worker.postMessage({id,code,grader:c.grader,common:window.HL_COMPUTE_PROBLEMS?.COMMON||''});
    };
  }
  const fmt=v=>v==null?'—':typeof v==='number'?(Math.abs(v)>=1e4||Math.abs(v)<1e-3&&v!==0?v.toExponential(4):String(+v.toPrecision(6))):esc(typeof v==='string'?v:JSON.stringify(v));
  function results(r,stdout,done){
    if(!r||r.error){$('results').innerHTML=`<p class="bad">${T.error}</p><pre class="out">${esc(r?.error||'')}</pre>`;height();return;}
    const tests=Array.isArray(r.tests)?r.tests:[],all=tests.length>0&&tests.every(t=>t.ok);
    $('results').innerHTML=`<p class="${all?'ok':'bad'}">${all?'✓ '+T.pass:T.fail} (${tests.filter(t=>t.ok).length}/${tests.length})</p>
      <div class="tablewrap"><table><thead><tr><th>${T.test}</th><th>${T.result}</th><th>${T.got}</th><th>${T.want}</th></tr></thead><tbody>${tests.map(t=>`<tr><td>${esc(t.name)}</td><td class="${t.ok?'ok':'bad'}">${t.ok?'✓':'✗'}</td><td>${fmt(t.got)}</td><td>${fmt(t.want)}</td></tr>`).join('')}</tbody></table></div>
      ${stdout&&stdout.trim()?`<pre class="out">${esc(stdout.slice(0,8000))}</pre>`:''}`;
    if(all)done();height();
  }

  /* ── the editor: a new creation, an edit of one's own, or a remix ── */
  async function edit(id){
    if(!token()){$('app').innerHTML=`<button type="button" class="back" id="back">${T.back}</button><p class="note">${T.login}</p><p><a class="btn primary" href="/#/login" target="_top">${T.loginBtn}</a></p>`;$('back').onclick=()=>go('gallery');height();return;}
    let c={kind:'sim',title:'',summary:'',body:'',code:'',starter:'',grader:'',answer:'',unit:''};
    if(id){try{c=(await api('/api/creations/'+encodeURIComponent(id))).creation;}catch(e){}}
    else{try{const d=JSON.parse(sessionStorage.getItem('hlCreateDraft')||'null');if(d){c={...c,...d};sessionStorage.removeItem('hlCreateDraft');}}catch(e){}}
    $('app').innerHTML=`<button type="button" class="back" id="back">${T.back}</button><h1>${id?T.edit:T.make}</h1>
      <form id="ef" class="editor">
        <label>${T.kind}<select name="kind"><option value="sim">${T.sim}</option><option value="code">${T.code}</option></select></label>
        <label>${T.name}<input name="title" maxlength="80" required></label>
        <label>${T.summary}<input name="summary" maxlength="200"></label>
        <div class="only-sim"><label>${T.codeSim}<textarea name="code" class="code" rows="16" spellcheck="false"></textarea></label><p class="help"><b>${T.helpers}</b> ${esc(T.helpSim)}</p>
          <label>${T.qText}<textarea name="body" rows="3"></textarea></label><div class="two"><label>${T.ans}<input name="answer" maxlength="400" spellcheck="false"></label><label>${T.unit}<input name="unit" maxlength="24"></label></div></div>
        <div class="only-code"><label>${T.body}<textarea name="bodyc" rows="5"></textarea></label><label>${T.starter}<textarea name="starter" class="code" rows="8" spellcheck="false"></textarea></label>
          <label>${T.grader}<textarea name="grader" class="code" rows="12" spellcheck="false"></textarea></label><p class="help">${esc(T.helpCode)}</p></div>
        <div class="row"><button type="button" id="tpl">${T.template}</button><button type="button" id="pv">${T.preview}</button><button type="submit" class="primary">${T.save}</button><span class="note" id="emsg"></span></div>
      </form><div id="pvbox"></div>`;
    const f=$('ef');
    const fill=c=>{f.kind.value=c.kind;f.title.value=c.title||'';f.summary.value=c.summary||'';f.code.value=c.code||'';f.body.value=c.kind==='sim'?c.body||'':'';f.bodyc.value=c.kind==='code'?c.body||'':'';
      f.answer.value=c.answer||'';f.unit.value=c.unit||'';f.starter.value=c.starter||'';f.grader.value=c.grader||'';kindView();};
    const kindView=()=>{const k=f.kind.value;f.querySelector('.only-sim').hidden=k!=='sim';f.querySelector('.only-code').hidden=k!=='code';height();};
    const read=()=>{const k=f.kind.value;return{kind:k,title:f.title.value.trim(),summary:f.summary.value.trim(),body:k==='sim'?f.body.value:f.bodyc.value,
      code:k==='sim'?f.code.value:'',answer:k==='sim'?f.answer.value.trim():'',unit:k==='sim'?f.unit.value.trim():'',starter:k==='code'?f.starter.value:'',grader:k==='code'?f.grader.value:''};};
    fill(c);f.kind.onchange=kindView;
    for(const ta of f.querySelectorAll('textarea.code'))ta.onkeydown=e=>{if(e.key==='Tab'&&!e.shiftKey){e.preventDefault();const s=ta.selectionStart;ta.setRangeText('    ',s,ta.selectionEnd,'end');}};
    $('back').onclick=()=>go('gallery');
    $('tpl').onclick=()=>{const t=TEMPLATE[f.kind.value];fill({...t,title:f.title.value||t.title,summary:f.summary.value||t.summary});};
    $('pv').onclick=()=>{const d=read();if(d.kind==='sim'){runSim($('pvbox'),d.code);if(d.answer)question(document.createElement('div'),d,()=>{});}else codeProblem($('pvbox'),{...d,id:'preview'},()=>{});height();};
    f.onsubmit=async e=>{
      e.preventDefault();const d=read();if(d.answer&&!answerFrom(d.answer)){$('emsg').textContent=T.ans;return;}
      try{
        if(id){await api('/api/creations/'+id,'PATCH',d);go('play',id);}
        else{const r=await api('/api/creations','POST',{...d,...(Number.isInteger(c.forked_from)?{forked_from:c.forked_from}:{})});go('play',r.id);}
      }catch(err){$('emsg').textContent=errText(err);}
    };
    height();
  }

  function route(){
    const v=new URL(location.href).searchParams;
    for(const k of ['kind','sort','mine'])params.set(k,v.get(k)||'');
    const view=v.get('view')||'gallery',id=v.get('id');
    if(view==='play'&&id)play(id);else if(view==='edit')edit(id);else gallery();
    window.scrollTo?.(0,0);if(embedded)window.parent.postMessage({type:'hl-create-top'},location.origin);
  }
  addEventListener('popstate',route);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',route);else route();
})();
