/* The Workshop's problem and test maker (#/workshop/make): put a test together from HaslaLab's problems, make number
   variants of a problem written with named values (the answers computed by teach-tools.js), make new problems from one
   with the AI (each checked by evaluating the stated calculation and by a second, independent solve), tag each problem
   with a unit and a level for the exam blueprint, print the paper with its answer key and blueprint, or send the bank
   problems to a class as an assignment. The server parts are /api/learn/variants and /api/learn/classes
   (community/src/learn-services.js). The paper and the template being written stay in this browser (localStorage). */
(()=>{
  'use strict';
  const $=id=>document.getElementById(id),params=new URL(location.href).searchParams;
  const embedded=params.get('embed')==='1'&&window.parent!==window;
  const lang=params.get('lang')==='en'?'en':'ko',ko=lang==='ko',dark=params.get('theme')==='dark';
  document.documentElement.lang=lang;document.documentElement.dataset.theme=dark?'dark':'light';document.documentElement.classList.toggle('embedded',embedded);
  const T=ko?{
    title:'문제·시험지 만들기',lede:'하슬라랩 문제와 직접 쓴 문제로 시험지를 만듭니다. 숫자만 바꾼 문제를 여러 개 만들 수 있고, 시험지는 정답표, 이원목적분류표와 함께 인쇄하거나 PDF로 저장합니다.',
    tabPaper:'시험지 만들기',tabTpl:'숫자 바꾼 문제',tabVar:'AI로 비슷한 문제',tabClass:'내 학급',
    tpl:{title:'숫자 바꾼 문제',how:'문제 글에서 바꿀 값을 {m}처럼 중괄호로 적고, 값마다 범위와 간격을 정한 다음 답을 식으로 적으세요. 문제마다 답을 계산해 붙입니다.',
      q:'문제 (바꿀 값은 {이름})',qPh:'질량 {m} kg인 공을 높이 {h} m에서 가만히 놓았다. 바닥에 닿기 직전 공의 속력은?',name:'값',min:'최소',max:'최대',step:'간격',
      noNames:'문제 글에 {m}처럼 중괄호로 값을 적으면 여기에 범위를 정하는 칸이 생깁니다.',formula:'답 (식)',formulaPh:'sqrt(2 g h)',unit:'답의 단위',constants:'상수 (선택)',constPh:'g = 9.8',
      sig:'유효숫자',bpUnit:'단원 (분류표용)',n:'몇 문제',make:'만들기',example:'예시 넣기',all:'모두 시험지에 넣기',allIn:n=>`${n}문제를 시험지에 넣었습니다.`,answer:'답',
      syntax:'식은 계산기처럼 씁니다: 2*sqrt(g*h), v_0^2/(2g), m g sin(theta). 값 이름은 글자 하나(m, h), 아래 첨자가 붙은 글자(v_0), 그리스 문자 이름(theta)만 됩니다.',
      err:{no_template:'문제 글을 적으세요.',no_values:'바꿀 값을 {m}처럼 중괄호로 적으세요.',too_many_values:'바꿀 값은 8개까지입니다.',bad_name:n=>`{${n}}: 값 이름은 m, v_0, theta처럼 적어야 식에서 읽을 수 있습니다.`,
        no_range:n=>`{${n}}의 범위를 정하세요.`,bad_range:n=>`{${n}}: 최소가 최대보다 작고 간격이 0보다 커야 합니다.`,no_formula:'답을 계산할 식을 적으세요.',bad_formula:'답 식을 읽지 못했습니다.',
        unknown_in_formula:n=>`식의 ${n}이(가) 문제의 값이나 상수에 없습니다.`,no_valid_values:'이 범위에서는 답을 계산할 수 없습니다. 0으로 나누거나 음수의 제곱근이 되는지 보세요.',bad_constants:'상수는 g = 9.8, c = 3e8처럼 적으세요.'}},
    bp:{title:'이원목적분류표',unit:'단원',level:'수준',levels:{know:'지식',understand:'이해',apply:'적용',analyze:'분석'},attach:'분류표 붙이기',total:'합계',items:n=>`${n}문항`,
      note:'문항마다 단원과 수준을 고르면 아래 표가 채워집니다.',nos:'문항'},
    bank:'문제 고르기',source:'문제 출처',unit:'단원',level:'난이도',all:'전체',search:'검색',searchPh:'낱말이나 수식',
    srcKr:'국내 학력평가 · 모의고사 (객관식)',add:'넣기',added:'넣음',vary:'비슷한 문제',more:'더 보기',none:'맞는 문제가 없습니다.',loading:'불러오는 중…',
    paper:'시험지',pTitle:'시험 이름',pSchool:'학교 · 학원',pInfo:'학년 · 반 · 날짜',pMin:'시간 (분)',pNote:'안내 (선택)',pts:'점',total:'총점',
    two:'2단으로',key:'정답표 붙이기 (시험지 뒤 새 쪽)',sol:'해설 붙이기',space:'풀이 칸 두기',print:'인쇄 · PDF 저장',clear:'비우기',clearAsk:'시험지를 비울까요?',
    empty:'왼쪽에서 문제를 넣으세요.',own:'직접 만든 문제',up:'위로',down:'아래로',del:'빼기',
    assign:'학급 과제로 보내기',assignNote:'직접 만든 문제는 과제로 보낼 수 없어 빠집니다. 학생은 문제 풀기 화면에서 풀고, 진도는 내 학급에서 봅니다.',
    noClass:'아직 학급이 없습니다.',makeClass:'학급 만들기',classPick:'학급',sent:'과제로 보냈습니다.',
    vSrc:'바탕 문제',vOther:'다른 문제로',vFig:'그림이 있는 문제입니다. AI는 글만 읽으므로, 그림에 있는 조건은 문제 직접 입력에 글로 적어 주세요.',vPick:'왼쪽 목록이나 시험지에서 \'비슷한 문제\'를 누르거나, 문제를 직접 붙여 넣으세요.',vOwn:'문제 직접 입력 (수식은 $...$)',vAns:'답 (선택)',
    vN:'몇 문제',vMode:'바꾸는 방식',vLevel:'난이도',vFormat:'형식',
    modes:{numbers:'숫자만 바꾸기',context:'상황 바꾸기',new:'새 유형'},levels:{easier:'조금 쉽게',same:'비슷하게',harder:'조금 어렵게'},formats:{free:'주관식',mc:'객관식'},
    make:'만들기',making:'만드는 중입니다. 문제마다 따로 한 번 더 풀어 확인하느라 1분 정도 걸립니다.',left:n=>`오늘 ${n}번 더 만들 수 있습니다.`,
    calcOk:'계산식이 답과 맞음',calcBad:'계산식이 답과 다름',calcNone:'계산식 없음',checkOk:'따로 풀어도 같은 답',checkBad:'따로 푼 답이 다름',checkNone:'따로 풀기 실패',
    verify:'두 확인이 모두 맞아도 정답을 보장하지는 않습니다. 시험에 쓰기 전에 직접 풀어 보세요.',
    q:'문제',a:'답',unitL:'단위',solL:'해설',choices:'선택지 (한 줄에 하나, 정답 앞에 *)',why:'오답 선택지가 나온 실수',toPaper:'시험지에 넣기',inPaper:'시험지에 넣었습니다.',
    login:'로그인하면 AI 문제 만들기와 학급 과제를 쓸 수 있습니다. 시험지 만들기와 인쇄는 로그인 없이 됩니다.',loginBtn:'로그인',
    keyTitle:'정답',name:'이름',number:'번호',src:'출처',
    err:{variant_limit:'오늘 만들 수 있는 횟수를 다 썼습니다. 교사 플랜은 하루 40번입니다.',ai_failed:'AI가 문제를 만들지 못했습니다. 다시 시도해 주세요.',ai_unavailable:'AI를 지금 쓸 수 없습니다.',
      login_required:'로그인하세요.',rate_limited:'잠시 뒤에 다시 시도해 주세요.',bad_source:'바탕 문제를 넣으세요.',bad_items:'과제로 보낼 문제가 없습니다.',bad_title:'시험 이름을 입력하세요.',class_not_found:'학급을 찾지 못했습니다.'}
  }:{
    title:'Problems and tests',lede:'Build a test from HaslaLab problems and your own. Make several versions of a problem with different numbers, and print the paper with its answer key and exam blueprint or save it as a PDF.',
    tabPaper:'Build a test',tabTpl:'Number variants',tabVar:'Similar problems (AI)',tabClass:'My classes',
    tpl:{title:'Number variants',how:'Write the problem with the values to change in braces, like {m}. Give each value a range and a step, then write the answer as a formula. Each version gets its own computed answer.',
      q:'Problem (values to change in {braces})',qPh:'A ball of mass {m} kg is released from rest at a height of {h} m. How fast is it moving just before it hits the floor?',name:'Value',min:'Min',max:'Max',step:'Step',
      noNames:'Write a value in braces, like {m}, and a row for its range appears here.',formula:'Answer (formula)',formulaPh:'sqrt(2 g h)',unit:'Answer unit',constants:'Constants (optional)',constPh:'g = 9.8',
      sig:'Significant figures',bpUnit:'Unit (for the blueprint)',n:'How many',make:'Make',example:'Fill in an example',all:'Add all to the paper',allIn:n=>`Added ${n} to the paper.`,answer:'Answer',
      syntax:'Write formulas the way a calculator takes them: 2*sqrt(g*h), v_0^2/(2g), m g sin(theta). A value is named by one letter (m, h), a letter with a subscript (v_0) or a Greek letter name (theta).',
      err:{no_template:'Write the problem.',no_values:'Put the values to change in braces, like {m}.',too_many_values:'Up to 8 values can change.',bad_name:n=>`{${n}}: name values like m, v_0 or theta so the formula can read them.`,
        no_range:n=>`Give {${n}} a range.`,bad_range:n=>`{${n}}: the minimum must not exceed the maximum and the step must be above 0.`,no_formula:'Write the formula for the answer.',bad_formula:'The answer formula could not be read.',
        unknown_in_formula:n=>`${n} in the formula is not a value of the problem or a constant.`,no_valid_values:'No answer can be computed in these ranges. Check for division by zero or a root of a negative number.',bad_constants:'Write constants like g = 9.8, c = 3e8.'}},
    bp:{title:'Exam blueprint',unit:'Unit',level:'Level',levels:{know:'Knowledge',understand:'Understanding',apply:'Application',analyze:'Analysis'},attach:'Add the blueprint',total:'Total',items:n=>`${n} item${n===1?'':'s'}`,
      note:'Pick a unit and a level for each problem and the table below fills in.',nos:'No.'},
    bank:'Pick problems',source:'Source',unit:'Topic',level:'Difficulty',all:'All',search:'Search',searchPh:'a word or a formula',
    srcKr:'Korean national practice exams (multiple choice, Korean)',add:'Add',added:'Added',vary:'Similar',more:'More',none:'No problems match.',loading:'Loading…',
    paper:'Test paper',pTitle:'Test name',pSchool:'School',pInfo:'Class and date',pMin:'Time (min)',pNote:'Instructions (optional)',pts:'pts',total:'Total',
    two:'Two columns',key:'Answer key (new page after the test)',sol:'Solutions',space:'Working space',print:'Print or save as PDF',clear:'Clear',clearAsk:'Clear the paper?',
    empty:'Add problems from the list.',own:'your own',up:'Up',down:'Down',del:'Remove',
    assign:'Send to a class',assignNote:'Problems you wrote are left out of assignments. Students solve the rest on the practice page; you see progress under My classes.',
    noClass:'No classes yet.',makeClass:'Make a class',classPick:'Class',sent:'Sent as an assignment.',
    vSrc:'Source problem',vOther:'Use another problem',vFig:'This problem has a figure. The AI reads only the text, so describe what the figure shows when you type the problem yourself.',vPick:'Press "Similar" on a problem in the list or the paper, or paste a problem.',vOwn:'Type a problem ($...$ for math)',vAns:'Answer (optional)',
    vN:'How many',vMode:'What changes',vLevel:'Difficulty',vFormat:'Format',
    modes:{numbers:'Numbers only',context:'New situation',new:'New question type'},levels:{easier:'A little easier',same:'About the same',harder:'A little harder'},formats:{free:'Free response',mc:'Multiple choice'},
    make:'Make',making:'Working. Each problem is solved a second time to check it, so this takes about a minute.',left:n=>`${n} more today.`,
    calcOk:'calculation matches the answer',calcBad:'calculation differs from the answer',calcNone:'no calculation given',checkOk:'second solve agrees',checkBad:'second solve disagrees',checkNone:'second solve failed',
    verify:'Passing both checks does not prove the answer right. Solve each problem yourself before you use it.',
    q:'Problem',a:'Answer',unitL:'Unit',solL:'Solution',choices:'Choices (one per line, * before the right one)',why:'The mistake behind each wrong choice',toPaper:'Add to the paper',inPaper:'Added to the paper.',
    login:'Log in to make problems with the AI and to send assignments. Building and printing a paper works without an account.',loginBtn:'Log in',
    keyTitle:'Answer key',name:'Name',number:'No.',src:'Sources',
    err:{variant_limit:'You have used today\'s runs. A teacher plan gives 40 a day.',ai_failed:'The AI could not write the problems. Try again.',ai_unavailable:'The AI is not available right now.',
      login_required:'Log in first.',rate_limited:'Try again in a moment.',bad_source:'Add a source problem.',bad_items:'No problems to send.',bad_title:'Enter a test name.',class_not_found:'Class not found.'}
  };
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const API=(()=>{let o='';try{o=localStorage.getItem('hlCmApi')||'';}catch(e){}return(/^https:\/\/[a-z0-9-]+\.haslalab\.workers\.dev\/?$/.test(o)?o:'https://haslalab-community-edge.haslalab.workers.dev').replace(/\/+$/,'');})();
  const token=()=>{try{const v=localStorage.getItem('hlCmTok')||'';return /^[A-Za-z0-9_-]{20,4096}$/.test(v)?v:'';}catch(e){return '';}};
  async function api(path,method='GET',body){
    const r=await fetch(API+path,{method,headers:{...(token()?{Authorization:'Bearer '+token()}:{}),...(body?{'content-type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});
    const j=await r.json().catch(()=>({}));if(!r.ok)throw Object.assign(new Error(j.error||'api '+r.status),{code:j.error,status:r.status});return j;
  }
  const errText=e=>T.err[e.code]||e.message||'error';
  function height(){if(embedded)requestAnimationFrame(()=>window.parent.postMessage({type:'hl-teach-height',height:Math.ceil(document.querySelector('main').getBoundingClientRect().bottom+scrollY+16)},location.origin));}
  if(typeof ResizeObserver==='function')new ResizeObserver(height).observe(document.body);
  const typeset=el=>{try{window.renderMathInElement?.(el,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false});}catch(e){}};
  const textHtml=t=>esc(t).split(/\n{2,}/).map(p=>'<p>'+p.replace(/\n/g,'<br>')+'</p>').join('');
  const P=()=>window.HL_LEARN_PATH;
  const unitName=k=>{const e=P()?.SUBTOPICS?.get(k);return e?(ko?e.sub.name.ko:e.sub.name.en):k;};

  /* ── the bank: HaslaLab's exam tracks and the Korean practice exams, read as plain items ── */
  const TRACKS=[['ap1','AP Physics 1'],['ap2','AP Physics 2'],['apcm','AP Physics C: Mechanics'],['jeem','JEE Main'],['fma','F=ma'],['usapho','USAPhO']];
  const AREAS=['mechanics','em','waves','optics','thermal','modern'];
  const SOURCES=[['kr',T.srcKr],...TRACKS];
  const cache={};
  const fetchJson=f=>cache[f]||(cache[f]=fetch(f).then(r=>{if(!r.ok)throw new Error(f);return r.json();}).catch(e=>{delete cache[f];throw e;}));
  const seg=p=>p.map(s=>s.m!==undefined?'$'+s.m+'$':(s.t||'')).join('').replace(/\s*\n\s*/g,' ').trim();
  const fig=(f,w,h)=>`<figure><img src="practice/fig/${encodeURIComponent(f)}" width="${w}" height="${h}" alt="" loading="lazy"></figure>`;
  function fromKr(x){
    const text=x.b.filter(b=>b.p||b.mb!==undefined).map(b=>b.p?seg(b.p):'$$'+b.mb+'$$');
    const qHtml=x.b.map(b=>b.p?`<p>${esc(seg(b.p))}</p>`:b.mb!==undefined?`<p>$$${esc(b.mb)}$$</p>`:b.f?fig(b.f,b.w,b.h):'').join('');
    const choices=x.ch.map(c=>c.c.map(b=>b.p?esc(seg(b.p)):b.f?fig(b.f,b.w,b.h):'').join(' '));
    const plainCh=x.ch.map(c=>c.c.filter(b=>b.p).map(b=>seg(b.p)).join(' '));
    return {key:'kr:'+x.id,id:x.id,src:x.src||'',by:x.by||'',unit:x.u,level:x.s,qHtml,q:text.join('\n\n'),choices,plainCh,mark:'①②③④⑤',answer:'①②③④⑤'[x.a-1]||'',answerPlain:plainCh[x.a-1]||'',sol:'',hasFig:x.b.some(b=>b.f)};
  }
  function fromTrack(t,name,x){
    const ans=x.type==='num'?`${+x.answer.value} ${x.answer.unit||''}`.trim():String.fromCharCode(65+x.answer)+'. '+(x.choices?.[x.answer]||'');
    return {key:t+':'+x.id,id:x.id,src:name,unit:x.unit,level:x.step,qHtml:textHtml(x.q),q:x.q,choices:(x.choices||[]).map(c=>esc(c)),plainCh:x.choices||[],mark:'ABCDE',
      answer:x.type==='num'?ans:'('+String.fromCharCode(65+x.answer)+')',answerPlain:x.type==='num'?ans:x.choices[x.answer],sol:x.sol||'',hasFig:false};
  }
  async function loadSource(src,unit){
    if(src==='kr'){
      const areas=unit?[unit.split('/')[0]]:AREAS;
      const parts=await Promise.all(areas.map(a=>fetchJson(`practice/data/${a}.json`).then(d=>d.items||d).catch(()=>[])));
      return parts.flat().map(fromKr);
    }
    const name=(TRACKS.find(x=>x[0]===src)||[])[1];
    const d=await fetchJson(`practice/track/${src}.json`);
    return d.items.map(x=>fromTrack(src,name,x));
  }
  const byKey=new Map();
  async function itemOf(key){
    if(byKey.has(key))return byKey.get(key);
    const [src]=key.split(':');
    const list=await loadSource(src,null).catch(()=>[]);list.forEach(i=>byKey.set(i.key,i));
    return byKey.get(key)||null;
  }

  /* ── the paper, kept in this browser ── */
  const KEY='hlTeachPaper';
  const blank=()=>({title:'',school:'',info:'',minutes:'',note:'',two:true,key:true,sol:false,space:false,bp:false,items:[]});
  let paper=(()=>{try{const p=JSON.parse(localStorage.getItem(KEY)||'null');return p&&Array.isArray(p.items)?{...blank(),...p}:blank();}catch(e){return blank();}})();
  const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(paper));}catch(e){}};
  /* the number-variant template being written, kept the same way */
  const TPL_KEY='hlTeachTemplate';
  const tplBlank=()=>({template:'',params:{},formula:'',unit:'',constants:'',sig:3,n:5,bpUnit:''});
  let tpl=(()=>{try{const t=JSON.parse(localStorage.getItem(TPL_KEY)||'null');return t&&typeof t==='object'&&t.params&&typeof t.params==='object'?{...tplBlank(),...t}:tplBlank();}catch(e){return tplBlank();}})();
  const saveTpl=()=>{try{localStorage.setItem(TPL_KEY,JSON.stringify(tpl));}catch(e){}};
  const TT=()=>window.HL_TEACH_TOOLS;
  const LEVELS=['know','understand','apply','analyze'];
  /* a problem's place in the blueprint: what the teacher picked, else the bank's unit and "understanding" */
  const bpOf=(p,item)=>({unit:p.bp?.unit??(item?unitName(item.unit):''),level:LEVELS.includes(p.bp?.level)?p.bp.level:'understand'});

  const state={tab:['vary','tpl'].includes(params.get('tab'))?params.get('tab'):'paper',tplOut:[],src:'ap1',unit:'',level:'',q:'',shown:30,list:[],source:null,variants:[],busy:false,me:null,plan:null,classes:null};

  function shell(){
    $('app').innerHTML=`<div class="head"><div><h1>${T.title}</h1><p class="lede">${T.lede}</p></div></div>
      <div class="seg tabs" role="tablist">${[['paper',T.tabPaper],['tpl',T.tabTpl],['vary',T.tabVar]].map(([k,n])=>`<button type="button" role="tab" aria-selected="${state.tab===k}" data-tab="${k}" class="${state.tab===k?'on':''}">${n}</button>`).join('')}
        <button type="button" data-class="1">${T.tabClass}</button></div>
      <div id="loginNote"></div><div class="cols"><section class="panel" id="bankPanel"></section><section class="panel" id="rightPanel"></section></div>
      <datalist id="bpUnits">${[...(P()?.SUBTOPICS||new Map()).keys()].map(k=>`<option value="${esc(unitName(k))}">`).join('')}</datalist>`;
    $('app').querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{state.tab=b.dataset.tab;shell();});
    $('app').querySelector('[data-class]').onclick=()=>window.top.location.assign('/#/learn/practice?mode=class');
    if(!token()&&state.tab!=='tpl')$('loginNote').innerHTML=`<p class="note">${T.login} <a class="btn" href="/#/login" target="_top">${T.loginBtn}</a></p>`;
    paintBank();state.tab==='paper'?paintPaper():state.tab==='tpl'?paintTpl():paintVary();
  }

  async function paintBank(){
    const box=$('bankPanel');
    const units=state.src==='kr'?AREAS.flatMap(a=>[...(P()?.SUBTOPICS||new Map()).keys()].filter(k=>k.startsWith(a+'/'))):[...new Set(state.list.map(i=>i.unit))];
    box.innerHTML=`<h2>${T.bank}</h2><div class="filt">
      <label class="wide">${T.source}<select id="fSrc">${SOURCES.map(([k,n])=>`<option value="${k}"${k===state.src?' selected':''}>${esc(n)}</option>`).join('')}</select></label>
      <label>${T.unit}<select id="fUnit"><option value="">${T.all}</option>${units.map(u=>`<option value="${esc(u)}"${u===state.unit?' selected':''}>${esc(unitName(u))}</option>`).join('')}</select></label>
      <label>${T.level}<select id="fLevel"><option value="">${T.all}</option>${[1,2,3,4,5,6,7,8,9,10].map(n=>`<option${String(n)===state.level?' selected':''}>${n}</option>`).join('')}</select></label>
      <label class="wide">${T.search}<input id="fQ" value="${esc(state.q)}" placeholder="${T.searchPh}"></label></div><div class="items" id="items"><p class="empty">${T.loading}</p></div>`;
    $('fSrc').onchange=e=>{state.src=e.target.value;state.unit='';state.shown=30;loadList();};
    $('fUnit').onchange=e=>{state.unit=e.target.value;state.shown=30;state.src==='kr'?loadList():paintItems();};
    $('fLevel').onchange=e=>{state.level=e.target.value;state.shown=30;paintItems();};
    let tm;$('fQ').oninput=e=>{clearTimeout(tm);tm=setTimeout(()=>{state.q=e.target.value;state.shown=30;paintItems();},250);};
    if(!state.list.length)loadList();else paintItems();
  }
  async function loadList(){
    try{state.list=await loadSource(state.src,state.src==='kr'?state.unit:null);}catch(e){state.list=[];}
    state.list.forEach(i=>byKey.set(i.key,i));
    paintBank();
  }
  function paintItems(){
    const box=$('items');if(!box)return;
    const q=state.q.trim().toLowerCase(),inPaper=new Set(paper.items.map(i=>i.key));
    const list=state.list.filter(i=>(!state.unit||i.unit===state.unit)&&(!state.level||String(i.level)===state.level)&&(!q||(i.q+' '+i.plainCh.join(' ')).toLowerCase().includes(q)));
    box.innerHTML=list.length?list.slice(0,state.shown).map(i=>`<div class="item${inPaper.has(i.key)?' added':''}" data-k="${esc(i.key)}"><div class="q">${i.qHtml}</div>
        ${i.choices.length&&!i.choices.every(c=>c.includes('<figure'))?`<div class="ch">${i.choices.map((c,n)=>`<span>${i.mark[n]}${i.mark==='ABCDE'?'.':''} ${c}</span>`).join('')}</div>`:''}
        <div class="bar"><span>${esc(unitName(i.unit))} · ${T.level} ${i.level}${i.src&&state.src==='kr'?' · '+esc(i.src):''}</span>
        <span class="acts"><button type="button" data-vary>${T.vary}</button><button type="button" data-add${inPaper.has(i.key)?' disabled':''}>${inPaper.has(i.key)?T.added:T.add}</button></span></div></div>`).join('')
      +(list.length>state.shown?`<button type="button" id="more">${T.more} (${list.length-state.shown})</button>`:''):`<p class="empty">${T.none}</p>`;
    typeset(box);
    box.querySelectorAll('.item').forEach(el=>{
      const it=byKey.get(el.dataset.k);
      el.querySelector('[data-add]').onclick=()=>{paper.items.push({key:it.key,pts:3});save();paintItems();if(state.tab==='paper')paintPaper();};
      el.querySelector('[data-vary]').onclick=()=>{state.source=it;state.tab='vary';shell();};
    });
    if($('more'))$('more').onclick=()=>{state.shown+=30;paintItems();};
    height();
  }

  async function paintPaper(){
    const box=$('rightPanel');
    const items=await Promise.all(paper.items.map(async p=>({...p,item:p.own?null:await itemOf(p.key)})));
    const total=paper.items.reduce((a,p)=>a+(+p.pts||0),0);
    const label=x=>x.own?(x.own.q.replace(/\$[^$]*\$/g,'…').slice(0,70)):x.item?(x.item.q.replace(/\$[^$]*\$/g,'…').slice(0,70)):x.key;
    box.innerHTML=`<h2>${T.paper}<span class="plan">${T.total} ${total}${T.pts==='점'?'점':' '+T.pts}</span></h2>
      <div class="paper-meta"><label class="wide">${T.pTitle}<input data-f="title" value="${esc(paper.title)}"></label>
        <label>${T.pSchool}<input data-f="school" value="${esc(paper.school)}"></label><label>${T.pInfo}<input data-f="info" value="${esc(paper.info)}"></label>
        <label>${T.pMin}<input data-f="minutes" inputmode="numeric" value="${esc(paper.minutes)}"></label><label>${T.pNote}<input data-f="note" value="${esc(paper.note)}"></label></div>
      <div class="opts">${[['two',T.two],['key',T.key],['sol',T.sol],['space',T.space],['bp',T.bp.attach]].map(([k,n])=>`<label><input type="checkbox" data-o="${k}"${paper[k]?' checked':''}>${n}</label>`).join('')}</div>
      <div class="plist">${items.length?items.map((x,i)=>`<div class="pitem" data-i="${i}"><span class="n">${i+1}</span><span class="t">${esc(label(x))}${x.own?`<span class="own">${T.own}</span>`:''}</span>
        <input data-pts value="${esc(x.pts)}" inputmode="decimal" aria-label="${T.pts}"><span class="acts"><button type="button" data-up title="${T.up}">↑</button><button type="button" data-down title="${T.down}">↓</button><button type="button" data-vary>${T.vary}</button><button type="button" data-del title="${T.del}">✕</button></span>
        <span class="pbp"><input data-bpu list="bpUnits" maxlength="40" value="${esc(bpOf(x,x.item).unit)}" placeholder="${T.bp.unit}" aria-label="${T.bp.unit}"><select data-bpl aria-label="${T.bp.level}">${LEVELS.map(l=>`<option value="${l}"${bpOf(x,x.item).level===l?' selected':''}>${T.bp.levels[l]}</option>`).join('')}</select></span></div>`).join(''):`<p class="empty">${T.empty}</p>`}</div>
      ${items.length?`<details class="bpbox" id="bpBox"${paper.bp?' open':''}><summary>${T.bp.title}</summary><p class="note">${T.bp.note}</p><div id="bpTable"></div></details>`:''}
      <div class="row"><button type="button" class="primary" id="print"${items.length?'':' disabled'}>${T.print}</button><button type="button" id="assign"${items.some(x=>!x.own)?'':' disabled'}>${T.assign}</button><button type="button" id="clear"${items.length?'':' disabled'}>${T.clear}</button></div>
      <div id="assignBox"></div>`;
    box.querySelectorAll('[data-f]').forEach(el=>el.oninput=()=>{paper[el.dataset.f]=el.value.slice(0,120);save();});
    box.querySelectorAll('[data-o]').forEach(el=>el.onchange=()=>{paper[el.dataset.o]=el.checked;save();});
    box.querySelectorAll('.pitem').forEach(el=>{
      const i=+el.dataset.i;
      el.querySelector('[data-pts]').onchange=e=>{const v=Math.max(0,Math.min(100,parseFloat(e.target.value)||0));paper.items[i].pts=v;save();paintPaper();};
      el.querySelector('[data-up]').onclick=()=>{if(i>0){[paper.items[i-1],paper.items[i]]=[paper.items[i],paper.items[i-1]];save();paintPaper();}};
      el.querySelector('[data-down]').onclick=()=>{if(i<paper.items.length-1){[paper.items[i+1],paper.items[i]]=[paper.items[i],paper.items[i+1]];save();paintPaper();}};
      el.querySelector('[data-del]').onclick=()=>{paper.items.splice(i,1);save();paintPaper();paintItems();};
      const bpSet=()=>{paper.items[i].bp={unit:el.querySelector('[data-bpu]').value.trim().slice(0,40),level:el.querySelector('[data-bpl]').value};save();paintBlueprint(items);};
      el.querySelector('[data-bpu]').onchange=bpSet;el.querySelector('[data-bpl]').onchange=bpSet;
      el.querySelector('[data-vary]').onclick=()=>{const x=items[i];state.source=x.own?{q:x.own.q,answerPlain:x.own.answer,sol:x.own.sol,plainCh:x.own.choices||[],qHtml:textHtml(x.own.q)}:x.item;state.tab='vary';shell();};
    });
    paintBlueprint(items);
    $('print').onclick=()=>printPaper(items);
    $('clear').onclick=()=>{if(confirm(T.clearAsk)){paper=blank();save();paintPaper();paintItems();}};
    $('assign').onclick=()=>assignBox(items);
    typeset(box);height();
  }

  async function assignBox(items){
    const box=$('assignBox');
    if(!token()){box.innerHTML=`<p class="note">${T.login}</p>`;return;}
    box.innerHTML=`<p class="note">${T.loading}</p>`;
    try{state.classes=(await api('/api/learn/classes')).teaching||[];}catch(e){box.innerHTML=`<p class="bad">${esc(errText(e))}</p>`;return;}
    if(!state.classes.length){box.innerHTML=`<p class="note">${T.noClass} <a class="btn" href="/#/learn/practice?mode=class" target="_top">${T.makeClass}</a></p>`;height();return;}
    box.innerHTML=`<div class="row"><select id="aClass" aria-label="${T.classPick}">${state.classes.map(c=>`<option value="${c.id}">${esc(c.name)} (${c.n})</option>`).join('')}</select>
      <button type="button" class="primary" id="aSend">${T.assign}</button></div><p class="note">${T.assignNote}</p><p id="aMsg"></p>`;
    $('aSend').onclick=async()=>{
      const ids=items.filter(x=>!x.own&&x.item).map(x=>x.item.id).slice(0,40);
      try{await api(`/api/learn/classes/${$('aClass').value}/assignments`,'POST',{title:(paper.title||T.paper).slice(0,80),items:ids});$('aMsg').innerHTML=`<span class="ok">${T.sent}</span>`;}
      catch(e){$('aMsg').innerHTML=`<span class="bad">${esc(errText(e))}</span>`;}
    };
    height();
  }

  /* the blueprint table: one row per unit, a column per level, each cell the count, the points and the item numbers */
  function blueprintHtml(items){
    const B=TT()?.blueprint(items.map(x=>({...bpOf(x,x.item),pts:x.pts})));if(!B)return '';
    const pt=n=>`${+n.toFixed(2)}${ko?'점':' pts'}`;
    const cell=c=>c?`<b>${T.bp.items(c.n)}</b> <span>${pt(c.pts)}</span><small>${T.bp.nos} ${c.nos.join(', ')}</small>`:'';
    return `<table class="bp"><thead><tr><th>${T.bp.unit}</th>${B.levels.map(l=>`<th>${T.bp.levels[l]}</th>`).join('')}<th>${T.bp.total}</th></tr></thead>
      <tbody>${B.units.map(u=>`<tr><th scope="row">${esc(u)}</th>${B.levels.map(l=>`<td>${cell(B.cells[u][l])}</td>`).join('')}<td><b>${T.bp.items(B.rowTotals[u].n)}</b> <span>${pt(B.rowTotals[u].pts)}</span></td></tr>`).join('')}</tbody>
      <tfoot><tr><th scope="row">${T.bp.total}</th>${B.levels.map(l=>`<td><b>${T.bp.items(B.byLevel[l].n)}</b> <span>${pt(B.byLevel[l].pts)}</span></td>`).join('')}<td><b>${T.bp.items(B.total.n)}</b> <span>${pt(B.total.pts)}</span></td></tr></tfoot></table>`;
  }
  function paintBlueprint(items){const box=$('bpTable');if(box){box.innerHTML=blueprintHtml(items);height();}}

  function printPaper(items){
    const out=$('paperPrint'),pt=n=>`${n}${ko?'점':' pts'}`;
    const qHtml=x=>x.own?textHtml(x.own.q):x.item?x.item.qHtml:'';
    const chs=x=>{const list=x.own?(x.own.choices||[]).map(esc):x.item?.choices||[],mark=x.own?'①②③④⑤':x.item?.mark||'①②③④⑤';
      return list.length?`<div class="pp-ch">${list.map((c,n)=>`<span>${mark[n]}${mark==='ABCDE'?'.':''} ${c}</span>`).join('')}</div>`:'';};
    const ans=x=>x.own?(x.own.choices?.length?'①②③④⑤'[x.own.correct]+' '+esc(x.own.choices[x.own.correct]):esc(x.own.answer+(x.own.unit?' '+x.own.unit:''))):x.item?esc(x.item.answer):'';
    const sol=x=>x.own?x.own.sol:x.item?.sol||'';
    const total=items.reduce((a,x)=>a+(+x.pts||0),0);
    const srcs=[...new Set(items.filter(x=>x.item&&x.item.by).map(x=>x.item.src))];
    out.innerHTML=`<div class="pp-head"><div class="pp-sub"><span>${esc(paper.school)}</span><span>${esc(paper.info)}</span></div>
        <div class="pp-title">${esc(paper.title||T.paper)}</div>
        <div class="pp-sub"><span>${paper.minutes?esc(paper.minutes)+(ko?'분':' min'):''}</span><span>${T.total} ${pt(total)}</span></div>
        <div class="pp-id"><b>${T.number}</b><span></span><b>${T.name}</b><span></span></div></div>
      ${paper.note?`<div class="pp-note">${esc(paper.note)}</div>`:''}
      <div class="pp-body${paper.two?' two':''}">${items.map((x,i)=>`<div class="pp-q"><p><span class="no">${i+1}.</span> <span class="pts">[${pt(x.pts)}]</span></p>${qHtml(x)}${chs(x)}${paper.space&&!(x.own?.choices?.length||x.item?.choices?.length)?'<div class="pp-space"></div>':''}</div>`).join('')}</div>
      ${paper.key?`<div class="pp-key"><h2>${esc(paper.title||T.paper)} · ${T.keyTitle}</h2><table>${items.map((x,i)=>`<tr><td style="width:3em">${i+1}</td><td>${ans(x)}</td>${paper.sol?`<td>${textHtml(sol(x))}</td>`:''}</tr>`).join('')}</table>
        ${srcs.length?`<p class="pp-src">${T.src}: ${srcs.map(esc).join(', ')}</p>`:''}</div>`:''}
      ${paper.bp?`<div class="pp-bp"><h2>${esc(paper.title||T.paper)} · ${T.bp.title}</h2>${blueprintHtml(items)}</div>`:''}`;
    typeset(out);
    const imgs=[...out.querySelectorAll('img')];
    Promise.all(imgs.map(im=>im.complete?0:new Promise(r=>{im.loading='eager';im.onload=im.onerror=r;}))).then(()=>window.print());
  }

  /* ── number variants: a template with named values, the answers computed in this browser ── */
  const EXAMPLE=ko?{template:'질량 {m} kg인 공을 높이 {h} m에서 가만히 놓았다. 공기 저항을 무시할 때, 바닥에 닿기 직전 공의 속력은? (중력 가속도 $g = 9.8\\ \\mathrm{m/s^2}$)',
      params:{m:{min:0.5,max:3,step:0.5},h:{min:2,max:20,step:1}},formula:'sqrt(2 g h)',unit:'m/s',constants:'g = 9.8',sig:3,n:5,bpUnit:unitName('mechanics/energy')}
    :{template:'A ball of mass {m} kg is released from rest at a height of {h} m. Ignoring air resistance, how fast is it moving just before it hits the floor? ($g = 9.8\\ \\mathrm{m/s^2}$)',
      params:{m:{min:0.5,max:3,step:0.5},h:{min:2,max:20,step:1}},formula:'sqrt(2 g h)',unit:'m/s',constants:'g = 9.8',sig:3,n:5,bpUnit:unitName('mechanics/energy')};
  const tplErr=e=>{const f=T.tpl.err[e.code];return typeof f==='function'?f(e.name):f||e.code;};
  function paintTpl(){
    const box=$('rightPanel'),L=T.tpl;
    box.innerHTML=`<h2>${L.title}<button type="button" class="link" id="tEx">${L.example}</button></h2><p class="note">${L.how}</p>
      <label class="fld">${L.q}<textarea id="tTpl" rows="5" placeholder="${esc(L.qPh)}">${esc(tpl.template)}</textarea></label>
      <div id="tParams"></div>
      <div class="two"><label class="fld">${L.formula}<input id="tFormula" class="mono" value="${esc(tpl.formula)}" placeholder="${esc(L.formulaPh)}" autocomplete="off" spellcheck="false"></label><label class="fld">${L.unit}<input id="tUnit" value="${esc(tpl.unit)}" placeholder="m/s"></label></div>
      <div class="fpre" id="tPre" aria-live="polite"></div>
      <div class="two"><label class="fld">${L.constants}<input id="tConst" class="mono" value="${esc(tpl.constants)}" placeholder="${esc(L.constPh)}" spellcheck="false"></label><label class="fld">${L.sig}<select id="tSig">${[2,3,4].map(n=>`<option${n===+tpl.sig?' selected':''}>${n}</option>`).join('')}</select></label></div>
      <label class="fld">${L.bpUnit}<input id="tBp" list="bpUnits" maxlength="40" value="${esc(tpl.bpUnit)}"></label>
      <p class="note">${L.syntax}</p>
      <div class="row"><label class="inl">${L.n}<select id="tN">${[1,2,3,4,5,6,8,10,12,15,20].map(n=>`<option${n===+tpl.n?' selected':''}>${n}</option>`).join('')}</select></label><button type="button" class="primary" id="tMake">${L.make}</button><span id="tMsg" class="note" role="status"></span></div>
      <div id="tList"></div>`;
    const sync=()=>{
      const names=TT().namesIn($('tTpl').value);
      for(const n of names)if(!tpl.params[n])tpl.params[n]={min:1,max:10,step:1};
      const rows=names.map(n=>{const p=tpl.params[n];return `<tr data-n="${esc(n)}"><th scope="row" class="mono">{${esc(n)}}</th>${['min','max','step'].map(k=>`<td><input data-k="${k}" inputmode="decimal" value="${esc(p[k])}" aria-label="${esc(n)} ${L[k]}"></td>`).join('')}</tr>`;}).join('');
      $('tParams').innerHTML=names.length?`<table class="ptab"><thead><tr><th>${L.name}</th><th>${L.min}</th><th>${L.max}</th><th>${L.step}</th></tr></thead><tbody>${rows}</tbody></table>`:`<p class="note">${L.noNames}</p>`;
      $('tParams').querySelectorAll('tr[data-n]').forEach(tr=>tr.querySelectorAll('input').forEach(i=>i.oninput=()=>{tpl.params[tr.dataset.n][i.dataset.k]=i.value.trim();saveTpl();}));
      height();
    };
    const pre=()=>{const tex=window.HL_MATH?.preview($('tFormula').value);$('tPre').innerHTML=tex?`$${esc(tex)}$${tpl.unit?' '+esc(tpl.unit):''}`:'';typeset($('tPre'));};
    let tm;$('tTpl').oninput=()=>{tpl.template=$('tTpl').value;saveTpl();clearTimeout(tm);tm=setTimeout(sync,200);};
    $('tFormula').oninput=()=>{tpl.formula=$('tFormula').value;saveTpl();pre();};
    for(const [id,k] of [['tUnit','unit'],['tConst','constants'],['tBp','bpUnit']])$(id).oninput=()=>{tpl[k]=$(id).value;saveTpl();if(k==='unit')pre();};
    $('tSig').onchange=()=>{tpl.sig=+$('tSig').value;saveTpl();};$('tN').onchange=()=>{tpl.n=+$('tN').value;saveTpl();};
    $('tEx').onclick=()=>{tpl={...tplBlank(),...JSON.parse(JSON.stringify(EXAMPLE))};saveTpl();state.tplOut=[];paintTpl();};
    $('tMake').onclick=makeTpl;
    sync();pre();paintTplOut();
  }
  function makeTpl(){
    const msg=$('tMsg'),consts=TT().constants(tpl.constants);
    if(consts===null){msg.innerHTML=`<span class="bad">${esc(T.tpl.err.bad_constants)}</span>`;return;}
    const r=TT().variants({template:tpl.template,params:tpl.params,formula:tpl.formula,constants:consts},+tpl.n||5,{sig:+tpl.sig||3});
    if(r.errors.length){msg.innerHTML=r.errors.map(e=>`<span class="bad">${esc(tplErr(e))}</span>`).join('<br>');state.tplOut=[];paintTplOut();return;}
    msg.textContent='';state.tplOut=r.items.map(x=>({...x,unit:tpl.unit,bpUnit:tpl.bpUnit.trim(),added:false}));paintTplOut();
  }
  function paintTplOut(){
    const box=$('tList');if(!box)return;const L=T.tpl,out=state.tplOut;
    const add=v=>{paper.items.push({key:'own:'+Date.now().toString(36)+Math.random().toString(36).slice(2,6),pts:3,own:{q:v.text,answer:v.answerText,unit:v.unit,sol:''},bp:{unit:v.bpUnit,level:'apply'}});v.added=true;};
    box.innerHTML=out.length?`<div class="row"><button type="button" id="tAll">${L.all}</button><span class="note" id="tAllMsg"></span></div>`+out.map((v,i)=>`<div class="variant tv" data-i="${i}"><div class="text"><span class="vno">${i+1}</span>${textHtml(v.text)}</div>
      <p class="tans"><b>${L.answer}</b> ${esc(v.answerText)}${v.unit?' '+esc(v.unit):''}</p><div class="row"><button type="button" class="primary" data-take${v.added?' disabled':''}>${v.added?T.inPaper:T.toPaper}</button></div></div>`).join(''):'';
    typeset(box);
    box.querySelectorAll('.tv').forEach(el=>{const v=out[+el.dataset.i];el.querySelector('[data-take]').onclick=()=>{add(v);save();paintTplOut();};});
    if($('tAll'))$('tAll').onclick=()=>{const left=out.filter(v=>!v.added);left.forEach(add);save();paintTplOut();$('tAllMsg').textContent=L.allIn(left.length);};
    height();
  }

  /* ── variants ── */
  function answerObj(s){
    const M=window.HL_MATH;if(!M||!s)return null;
    const lead=/^\s*([-+]?\d[\d.,]*(?:\s*[eE][-+]?\d+)?(?:\s*[*×x]\s*10\s*\^\s*\(?[-+]?\d+\)?)?)/.exec(s);
    const body=lead?lead[1].replace(/,/g,'').replace(/[×x]/,'*'):s;
    try{const ast=M.parse(body),vs=[...M.vars(ast)];if(!vs.length){const v=M.evaluate(ast,{});return Number.isFinite(v)?{kind:'num',value:v}:null;}return {kind:'expr',ast,vars:vs};}
    catch(e){try{return M.answerOf(s);}catch(x){return null;}}
  }
  function agree(given,answer,tol){
    const a=answerObj(answer);if(!a||!given)return null;
    const lead=/^\s*([-+]?\d[\d.,]*(?:\s*[eE][-+]?\d+)?(?:\s*[*×x]\s*10\s*\^\s*\(?[-+]?\d+\)?)?)\s*[A-Za-zΩμ°/^·\s0-9-]*$/.exec(given);
    const input=lead&&a.kind==='num'?lead[1].replace(/,/g,'').replace(/[×x]/,'*'):given;
    try{return window.HL_MATH.check(input,a,tol).ok;}catch(e){return false;}
  }
  function paintVary(){
    const box=$('rightPanel'),s=state.source;
    box.innerHTML=`<h2>${T.vSrc}${state.plan?`<span class="plan">${T.left(state.plan.variantLeft??0)}</span>`:''}</h2>
      ${s?`<div class="srcbox">${s.qHtml||textHtml(s.q)}</div><div class="row"><button type="button" class="back" id="vReset">✕ ${T.vOther}</button></div>${s.hasFig?`<p class="note">${T.vFig}</p>`:''}`:
        `<p class="note">${T.vPick}</p><label class="fld"><textarea id="vOwn" rows="5" placeholder="${T.vOwn}"></textarea></label><label class="fld"><input id="vAns" placeholder="${T.vAns}"></label>`}
      <div class="vform"><label>${T.vN}<select id="vN">${[1,2,3,4,5].map(n=>`<option${n===3?' selected':''}>${n}</option>`).join('')}</select></label>
        <label>${T.vMode}<select id="vMode">${Object.entries(T.modes).map(([k,n])=>`<option value="${k}">${n}</option>`).join('')}</select></label>
        <label>${T.vLevel}<select id="vLevel">${Object.entries(T.levels).map(([k,n])=>`<option value="${k}"${k==='same'?' selected':''}>${n}</option>`).join('')}</select></label>
        <label>${T.vFormat}<select id="vFormat">${Object.entries(T.formats).map(([k,n])=>`<option value="${k}"${(s?.plainCh?.length?'mc':'free')===k?' selected':''}>${n}</option>`).join('')}</select></label></div>
      <div class="row"><button type="button" class="primary" id="vMake"${state.busy?' disabled':''}>${T.make}</button><span id="vMsg" class="note">${state.busy?T.making:''}</span></div>
      <p class="note">${T.verify}</p><div id="vList"></div>`;
    typeset(box);
    if($('vReset'))$('vReset').onclick=()=>{state.source=null;paintVary();};
    $('vMake').onclick=make;
    paintVariants();
    if(token()&&!state.plan)api('/api/learn/plan').then(p=>{state.plan=p;if(state.tab==='vary'){const el=box.querySelector('h2');if(el&&!el.querySelector('.plan'))el.insertAdjacentHTML('beforeend',`<span class="plan">${T.left(p.variantLeft??0)}</span>`);}}).catch(()=>{});
    height();
  }
  async function make(){
    if(!token()){$('vMsg').innerHTML=`<span class="bad">${T.err.login_required}</span>`;return;}
    const s=state.source;
    const source=s?{q:s.q,answer:s.answerPlain||'',sol:s.sol||'',choices:s.plainCh||[]}:{q:($('vOwn').value||'').trim(),answer:($('vAns').value||'').trim()};
    if(!source.q){$('vMsg').innerHTML=`<span class="bad">${T.err.bad_source}</span>`;return;}
    state.busy=true;$('vMake').disabled=true;$('vMsg').textContent=T.making;
    try{
      const r=await api('/api/learn/variants','POST',{source,n:+$('vN').value,mode:$('vMode').value,level:$('vLevel').value,format:$('vFormat').value,lang});
      state.variants=r.variants.map(v=>({...v,calcOk:agree(v.calc,v.answer,0.02),checkOk:v.choices?agreeChoice(v):agree(v.check,v.answer,0.03)}));
      if(state.plan)state.plan.variantLeft=r.left;
      state.busy=false;paintVary();
    }catch(e){state.busy=false;$('vMake').disabled=false;$('vMsg').innerHTML=`<span class="bad">${esc(errText(e))}</span>`;}
  }
  /* a multiple-choice check may name the choice number or give the value */
  function agreeChoice(v){
    if(!v.check)return null;
    const k=/^\s*\(?([1-5])\)?\s*$/.exec(v.check);if(k)return +k[1]-1===v.correct;
    return agree(v.check,v.answer,0.03);
  }
  function paintVariants(){
    const box=$('vList');if(!box)return;
    const badge=(ok,yes,no,none)=>`<span class="chk ${ok===true?'ok':ok===false?'bad':''}">${ok===true?'✓ '+yes:ok===false?'✕ '+no:none}</span>`;
    box.innerHTML=state.variants.map((v,i)=>`<div class="variant" data-i="${i}"><div class="checks">${badge(v.calcOk,T.calcOk,T.calcBad,T.calcNone)}${badge(v.checkOk,T.checkOk,T.checkBad,T.checkNone)}</div>
      <div class="text" data-view>${textHtml(v.q)}</div>
      <label class="fld">${T.q}<textarea data-e="q">${esc(v.q)}</textarea></label>
      ${v.choices?`<label class="fld">${T.choices}<textarea data-e="choices">${esc(v.choices.map((c,k)=>(k===v.correct?'*':'')+c).join('\n'))}</textarea></label>${v.why?.length?`<div class="note">${T.why}</div><ul class="why">${v.why.map(w=>`<li>${esc(w)}</li>`).join('')}</ul>`:''}`:''}
      <div class="two"><label class="fld">${T.a}<input data-e="answer" value="${esc(v.answer)}"></label><label class="fld">${T.unitL}<input data-e="unit" value="${esc(v.unit)}"></label></div>
      <label class="fld">${T.solL}<textarea data-e="sol">${esc(v.sol)}</textarea></label>
      <div class="row"><button type="button" class="primary" data-take>${T.toPaper}</button><span class="note" data-msg></span></div></div>`).join('');
    typeset(box);
    box.querySelectorAll('.variant').forEach(el=>{
      const v=state.variants[+el.dataset.i];
      el.querySelectorAll('[data-e]').forEach(f=>f.oninput=()=>{
        if(f.dataset.e==='choices'){const lines=f.value.split('\n').map(x=>x.trim()).filter(Boolean);v.correct=Math.max(0,lines.findIndex(x=>x.startsWith('*')));v.choices=lines.map(x=>x.replace(/^\*\s*/,''));}
        else v[f.dataset.e]=f.value;
        if(f.dataset.e==='q'){const view=el.querySelector('[data-view]');view.innerHTML=textHtml(v.q);typeset(view);}
      });
      el.querySelector('[data-take]').onclick=()=>{
        paper.items.push({key:'own:'+Date.now().toString(36)+i,pts:3,own:{q:v.q,answer:v.answer,unit:v.unit,sol:v.sol,...(v.choices?{choices:v.choices,correct:v.correct}:{})}});
        save();el.querySelector('[data-msg]').innerHTML=`<span class="ok">${T.inPaper}</span>`;
      };
    });
    height();
  }

  addEventListener('DOMContentLoaded',shell);
})();
