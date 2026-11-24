/* The Workshop's coding environment (create.html, view=edit): code on the left, the running simulation on the right
   (tabs Code / Run / AI on a phone or a tablet held upright), an AI panel that proposes a whole new file shown as a diff,
   and saving: local autosave, a downloaded file, the member's storage, and publishing as a creation (creations.js).
   Storage (보관함): the first "보관함에 저장" makes a text file in the folder "시뮬레이션" (kind 'sim', .js.txt: storage
   never keeps a runnable .js, and serves every file as an attachment); its id is remembered with this creation, so later
   saves replace that same file (PUT /api/workshop/storage/files/:id/content). "보관함에서 열기" lists the member's saved
   simulations and loads one into the editor (undo brings the previous code back).
   Security: a simulation, and anything the AI wrote, runs only in sim-sandbox.html inside
   <iframe sandbox="allow-scripts"> (an opaque origin: no cookies, storage or tokens of the site, no network by its own
   policy, and this page's frame-src 'self' keeps it from navigating anywhere else). Messages from it are accepted only
   from that frame's window with origin "null", read as plain data and shown as text; it is recreated on every run and
   removed on Stop or when its heartbeat stops. Python (a creation's solution and grader, the member's own code) runs in
   compute-worker.js, which takes the site's stored data out of reach first; the AI never writes Python. */
(function(){
  'use strict';
  const E=()=>window.HL_EDITOR,TPL=()=>window.HL_SIM_TEMPLATES;
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const store={get(k){try{return localStorage.getItem(k);}catch(e){return null;}},set(k,v){try{localStorage.setItem(k,v);return true;}catch(e){return false;}},del(k){try{localStorage.removeItem(k);}catch(e){}}};

  /* ── the sandbox runner, shared with the play view ── */
  function runSandbox(host,o){
    host.innerHTML=`<iframe class="sim" sandbox="allow-scripts" src="sim-sandbox.html" title="simulation"></iframe>`;
    const f=host.querySelector('iframe');let alive=true,sent=false,dead=false,beat=Date.now();
    const on=e=>{
      if(!alive||e.source!==f.contentWindow||e.origin!=='null')return;
      const d=e.data;if(!d||typeof d!=='object'||typeof d.type!=='string')return;
      beat=Date.now();
      if(d.type==='sim-ready'&&!sent){sent=true;f.contentWindow.postMessage({type:'run',code:String(o.code||''),theme:o.dark?'dark':'light',fit:!!o.fit},'*');}
      else if(d.type==='sim-height'&&Number.isFinite(d.height))o.onHeight&&o.onHeight(Math.min(4000,Math.max(0,d.height)));
      else if(d.type==='sim-log'&&typeof d.text==='string')o.onLog&&o.onLog(['log','info','warn','error'].includes(d.level)?d.level:'log',d.text.slice(0,2000));
      else if(d.type==='sim-error'&&typeof d.message==='string'&&!dead){dead=true;o.onError&&o.onError(d.message.slice(0,1000),Number.isInteger(d.line)&&d.line>0&&d.line<1e6?d.line:0);}
    };
    addEventListener('message',on);
    const vis=()=>{beat=Date.now();};document.addEventListener('visibilitychange',vis);
    /* the watchdog: a frame that stops answering (a loop the guard could not see) is removed */
    const dog=setInterval(()=>{if(!alive||dead||document.hidden)return;if(Date.now()-beat>(sent?6000:20000)){stop();o.onHang&&o.onHang();}},1000);
    function stop(){if(!alive)return;alive=false;clearInterval(dog);removeEventListener('message',on);document.removeEventListener('visibilitychange',vis);f.remove();}
    return {stop,frame:f,get alive(){return alive;}};
  }

  const S={
    ko:{code:'코드',run:'실행',ai:'AI',runBtn:'▶ 실행',stop:'■ 멈춤',auto:'자동 실행',tpl:'예시 불러오기',undo:'↶ 되돌리기',download:'⤓ 내려받기',storage:'보관함에 저장',publish:'저장하고 공개',
      title:'제목',kindSim:'시뮬레이션 (JavaScript)',kindCode:'계산물리 문제 (Python)',solution:'solution.py (처음 코드)',grader:'grader.py (채점)',console:'콘솔',clear:'지우기',
      idle:'▶ 실행을 누르거나 Ctrl+Enter.',stopped:'멈췄습니다.',hang:'시뮬레이션이 응답하지 않아 멈췄습니다. 끝나지 않는 반복문이 있는지 보세요.',line:'줄',
      loading:'Python을 불러오는 중…',pyRunning:'실행 중…',timeout:'30초를 넘어 멈췄습니다.',pass:'모두 통과',fail:'통과하지 못한 검사가 있습니다',noTests:'검사 없음',
      aiTitle:'AI에게 맡기기',aiLede:'만들고 싶은 것이나 고치고 싶은 점을 적으면 AI가 코드 전체를 새로 써서 제안합니다. 바뀌는 줄을 확인한 뒤 적용하세요. AI가 쓴 코드도 격리된 실행 창에서만 돌아갑니다.',
      aiPh:'예: 공기 저항 계수를 슬라이더로 바꾸고, 높이-시간 그래프를 추가해 줘',aiAsk:'제안 받기',aiAsking:'AI가 코드를 쓰는 중…',apply:'적용',discard:'버리기',applied:'적용했습니다. 마음에 들지 않으면 되돌리기를 누르세요.',
      aiLeft:n=>`오늘 ${n}번 더 쓸 수 있습니다.`,aiLogin:'AI는 로그인한 회원이 쓸 수 있습니다.',login:'로그인',aiPython:'AI는 지금 JavaScript 시뮬레이션만 씁니다. 종류를 시뮬레이션으로 바꾸면 쓸 수 있습니다.',
      aiNoChange:'AI가 바꾼 줄이 없습니다.',diffHead:(a,r)=>`바뀌는 줄: +${a} −${r}`,
      chips:['슬라이더로 값을 바꿀 수 있게','그래프 추가','설명 주석 달기','오류 고치기','처음부터 새로'],
      aiErr:{ai_failed:'지금은 AI를 쓸 수 없습니다. 잠시 뒤에 다시 해 보세요.',code_ai_limit:'오늘 쓸 수 있는 AI 횟수를 다 썼습니다.',rate_limited:'너무 자주 요청했습니다. 잠시 뒤에 다시 해 보세요.',login_required:'로그인하세요.',bad_prompt:'요청을 1~2000자로 적어 주세요.',bad_code:'코드가 너무 깁니다 (60,000자까지).',network:'서버에 연결하지 못했습니다.'},
      details:'설명 · 문제',summary:'한 줄 설명',question:'질문 (선택: 실험으로 답을 구하게 하려면)',answer:'답 (숫자나 식, 예: 9.8, 2*pi*sqrt(L/g))',unit:'단위',body:'문제 설명 (수식은 $...$)',
      ref:'도우미 API (hl) 설명',restored:'자동 저장된 내용을 불러왔습니다.',restoreOffer:'저장하지 않은 고친 내용이 이 기기에 있습니다.',restore:'불러오기',drop:'버리기',
      saved:'저장했습니다.',savedStorage:n=>`보관함의 ‘${n}’에 저장했습니다.`,needLogin:'로그인하면 저장하고 공개할 수 있습니다. 코드는 이 기기에 자동 저장됩니다.',autosaved:'이 기기에 자동 저장됨',
      folder:'시뮬레이션',open:'보관함에서 열기',openTitle:'보관함에서 열기',none:'보관함에 저장한 시뮬레이션이 없습니다.',close:'닫기',loading:'불러오는 중…',opened:n=>`보관함의 ‘${n}’을(를) 열었습니다. 되돌리기로 앞의 코드로 돌아갈 수 있습니다.`,
      updated:n=>`보관함의 ‘${n}’에 덮어 저장했습니다.`,badFile:'이 파일은 시뮬레이션이 아닙니다.',confirmTpl:'지금 코드를 예시로 바꿀까요? 되돌리기로 돌아올 수 있습니다.',keys:'기호 입력',
      err:{bad_title:'제목을 입력하세요.',bad_code:'코드를 입력하세요.',bad_grader:'채점 코드에 def grade(ns): 가 있어야 합니다.',bad_body:'문제 설명을 입력하세요.',rate_limited:'잠시 뒤에 다시 시도하세요.',login_required:'로그인이 필요합니다.',not_owner:'내 작품만 고칠 수 있습니다.',file_too_large:'파일이 너무 큽니다.',quota_exceeded:'보관함 용량이 모자랍니다.',r2_unavailable:'지금은 보관함을 쓸 수 없습니다.',network:'서버에 연결하지 못했습니다.'}},
    en:{code:'Code',run:'Run',ai:'AI',runBtn:'▶ Run',stop:'■ Stop',auto:'Auto-run',tpl:'Load an example',undo:'↶ Undo',download:'⤓ Download',storage:'Save to Storage',publish:'Save and publish',
      title:'Title',kindSim:'Simulation (JavaScript)',kindCode:'Python problem',solution:'solution.py (starter)',grader:'grader.py',console:'Console',clear:'Clear',
      idle:'Press ▶ Run or Ctrl+Enter.',stopped:'Stopped.',hang:'The simulation stopped responding and was stopped. Look for a loop that never ends.',line:'line',
      loading:'Loading Python…',pyRunning:'Running…',timeout:'Stopped after 30 seconds.',pass:'All tests passed',fail:'Some tests failed',noTests:'No tests',
      aiTitle:'Ask the AI',aiLede:'Describe what to build or change and the AI rewrites the whole file as a proposal. Check the changed lines, then apply. Code the AI writes also runs only in the isolated frame.',
      aiPh:'e.g. make the drag coefficient a slider and add a height–time plot',aiAsk:'Get a proposal',aiAsking:'The AI is writing…',apply:'Apply',discard:'Discard',applied:'Applied. Press Undo if you do not like it.',
      aiLeft:n=>`${n} more today.`,aiLogin:'The AI is for signed-in members.',login:'Log in',aiPython:'For now the AI writes JavaScript simulations only. Switch the kind to Simulation to use it.',
      aiNoChange:'The AI changed no lines.',diffHead:(a,r)=>`Changed lines: +${a} −${r}`,
      chips:['Add sliders for the parameters','Add a plot','Comment the code','Fix the error','Start over'],
      aiErr:{ai_failed:'The AI is not available right now. Try again in a moment.',code_ai_limit:'You have used today’s AI requests.',rate_limited:'Too many requests. Try again in a moment.',login_required:'Log in first.',bad_prompt:'Write the request in 1–2000 characters.',bad_code:'The code is too long (60,000 characters at most).',network:'Could not reach the server.'},
      details:'Description and question',summary:'One-line summary',question:'Question (optional, for a virtual experiment)',answer:'Answer (a number or a formula, e.g. 9.8, 2*pi*sqrt(L/g))',unit:'Unit',body:'Problem statement ($...$ for math)',
      ref:'Helper API (hl) reference',restored:'Restored what was autosaved.',restoreOffer:'This device has unsaved changes to this creation.',restore:'Restore',drop:'Discard',
      saved:'Saved.',savedStorage:n=>`Saved to Storage as “${n}”.`,needLogin:'Log in to save and publish. Your code is autosaved on this device.',autosaved:'Autosaved on this device',
      folder:'Simulations',open:'Open from Storage',openTitle:'Open from Storage',none:'No simulations saved in Storage yet.',close:'Close',loading:'Loading…',opened:n=>`Opened “${n}” from Storage. Undo brings the previous code back.`,
      updated:n=>`Saved over “${n}” in Storage.`,badFile:'This file is not a simulation.',confirmTpl:'Replace the current code with the example? Undo brings it back.',keys:'Symbols',
      err:{bad_title:'Enter a title.',bad_code:'Enter the code.',bad_grader:'The grader needs a def grade(ns): function.',bad_body:'Enter the problem statement.',rate_limited:'Try again in a moment.',login_required:'Log in first.',not_owner:'You can only edit your own.',file_too_large:'The file is too large.',quota_exceeded:'Your storage is full.',r2_unavailable:'Storage is not available right now.',network:'Could not reach the server.'}}
  };
  /* the reference beside the editor: the same helpers the sandbox defines and the AI is told about */
  const REF=[
    ['hl.view(xmin, xmax, ymin, ymax)','보이는 영역 (m). 비율은 유지','Visible area in metres (aspect kept)'],
    ['hl.slider(name, min, max, value, step)','슬라이더 → 현재 값을 돌려주는 함수','A slider → a function returning its value'],
    ['hl.toggle(name, on) · hl.choice(name, [..])','체크 상자 · 고르기','A checkbox · a choice'],
    ['hl.button(label, fn) · hl.show(label, value, unit)','버튼 · 값 표시','A button · a live readout'],
    ['hl.run({init, step(s, dt, t), draw(s, t), dt, resetOnChange})','고정 시간 간격 시뮬레이션 + ▶ ❚❚ ↺ 속도','Fixed-step simulation with play, pause, reset, speed'],
    ['hl.loop((dt, t) => …)','매 프레임 호출','Called every frame'],
    ['hl.clear() · hl.grid(step) · hl.axes() · hl.ground(y)','지우기 · 격자 · 축 · 바닥','Clear · grid · axes · ground'],
    ['hl.circle(x, y, r) · hl.dot(x, y, px) · hl.line(…) · hl.rect(x, y, w, h)','도형 (m 단위; dot은 픽셀 반지름)','Shapes in metres (dot: pixel radius)'],
    ['hl.arrow(x, y, dx, dy, {scale, label, color})','벡터 화살표','A vector arrow'],
    ['hl.spring(x1, y1, x2, y2, {coils, width})','용수철','A spring'],
    ['hl.text(s, x, y) · hl.label(s, px, py)','글자 (세계 좌표 · 픽셀)','Text (world · pixels)'],
    ['hl.trail(max) → t.push(x, y), t.draw()','궤적','A trail'],
    ['hl.plot(title, {xlabel, ylabel}) → p.add(x, y, series)','그래프 (캔버스 아래)','A plot under the canvas'],
    ['hl.euler(f, y, t, dt) · hl.rk4(f, y, t, dt)','적분 한 단계: f(t, y) → dy/dt 배열','One step: f(t, y) → dy/dt array'],
    ['hl.verlet(acc, x, v, t, dt) → [x, v]','속도 Verlet (에너지 보존에 좋음)','Velocity Verlet (keeps energy)'],
    ['hl.solve(f, y0, t0, t1, dt) → {t, y}','한 번에 적분','Integrate in one go'],
    ['hl.key(\'ArrowLeft\') · hl.pointer · hl.onClick(fn) · hl.onDrag(fn)','키보드 · 포인터(m) · 터치','Keys · pointer (m) · touch'],
    ['hl.colors.{blue, red, green, orange, accent, muted, ink} · hl.t · hl.p','색 · 시뮬레이션 시간 · 슬라이더 값','Colours · simulated time · slider values'],
    ['console.log(…)','콘솔 패널에 출력','Prints to the console panel']
  ];
  /* Python: plot(x, y, label) collects points the page draws; one line, so the member's line numbers move by one */
  const PY_PRELUDE='__hl_plots=[];plot=lambda x,y,label="",title="":__hl_plots.append({"x":[float(v) for v in list(x)[:4000]],"y":[float(v) for v in list(y)[:4000]],"label":str(label)[:60],"title":str(title)[:80]})\n';
  /* the plots the solution drew itself (not those the grader's calls add), sent back with the grader's result */
  const PY_WRAP='\n__hl_user_grade=grade\ndef grade(ns):\n    n=len(ns.get("__hl_plots",[]))\n    r=__hl_user_grade(ns)\n    if isinstance(r,dict):\n        r["__plots"]=ns.get("__hl_plots",[])[:(n or 8)][:8]\n    return r\n';
  const PY_NOGRADE='def grade(ns):\n    return {"tests": []}\n';

  function open(ctx){
    const L=S[ctx.lang==='en'?'en':'ko'],ko=ctx.lang!=='en',root=ctx.root,id=ctx.id||null;
    const key='hlStudio:'+(id||'new');
    let d={kind:'sim',title:'',summary:'',body:'',code:'',starter:'',grader:'',answer:'',unit:'',...ctx.creation};
    let file='main',auto=store.get('hlStudioAuto')!=='0',right='run',pane='code',runner=null,lastError='',history=[],proposal=null,worker=null,wtimer=0,autoT=0,saveT=0,job=0;
    const autoBackup=(()=>{try{return JSON.parse(store.get(key)||'null');}catch(e){return null;}})();
    let note='';
    if(ctx.fresh&&!ctx.fromDraft&&autoBackup&&autoBackup.d){d={...d,...autoBackup.d};note=L.restored;}
    if(ctx.fresh&&!(autoBackup&&!ctx.fromDraft)&&!d.code&&d.kind==='sim')d.code=TPL()?.byId('projectile')?.code||'';
    const offer=(!ctx.fresh||ctx.fromDraft)&&!ctx.fromDraft&&autoBackup&&autoBackup.d&&autoBackup.t>(d.updated_at||0)*1000&&JSON.stringify(pick(autoBackup.d))!==JSON.stringify(pick(d));
    function pick(x){return {kind:x.kind,title:x.title,summary:x.summary,body:x.body,code:x.code,starter:x.starter,grader:x.grader,answer:x.answer,unit:x.unit};}

    document.querySelector('main')?.classList.add('wide');
    const tplOptions=()=>d.kind==='sim'?(TPL()?.list||[]).map(t=>`<option value="${t.id}">${esc(ko?t.ko:t.en)}</option>`).join(''):`<option value="euler">${ko?'오일러 방법으로 낙하':'A falling ball by Euler steps'}</option>`;
    root.innerHTML=`<div class="studio" data-pane="code" data-right="run">
      <div class="st-top">
        <button type="button" class="back" id="stBack">${esc(ctx.T.back)}</button>
        <input id="stTitle" class="st-title" maxlength="80" placeholder="${esc(L.title)}" aria-label="${esc(L.title)}">
        <select id="stKind" aria-label="kind"><option value="sim">${esc(L.kindSim)}</option><option value="code">${esc(L.kindCode)}</option></select>
      </div>
      <div class="st-bar" role="toolbar">
        <button type="button" class="primary" id="stRun" title="Ctrl+Enter">${L.runBtn}</button><button type="button" id="stStop">${L.stop}</button>
        <label class="st-check"><input type="checkbox" id="stAuto"> ${esc(L.auto)}</label>
        <select id="stTpl" aria-label="${esc(L.tpl)}"><option value="">${esc(L.tpl)}…</option></select>
        <button type="button" id="stUndo" disabled>${L.undo}</button>
        <span class="st-gap"></span>
        <button type="button" id="stDown">${L.download}</button><button type="button" id="stStore">${esc(L.storage)}</button><button type="button" id="stOpenStore">${esc(L.open)}</button><button type="button" class="primary" id="stPub">${esc(L.publish)}</button>
      </div>
      <p class="st-msg" id="stMsg" role="status"></p>
      <nav class="st-mtabs" role="tablist"><button type="button" data-m="code" role="tab">${L.code}</button><button type="button" data-m="run" role="tab">▶ ${L.run}</button><button type="button" data-m="ai" role="tab">✦ ${L.ai}</button></nav>
      <div class="st-work">
        <section class="st-code" aria-label="${esc(L.code)}">
          <div class="st-files" id="stFiles"></div>
          <div class="st-ed" id="stEd"></div>
          <div class="st-keys" aria-label="${esc(L.keys)}">${['⇥','{ }','( )','[ ]',';','=','.',',','\'','hl.','=>'].map(k=>`<button type="button" data-k="${esc(k)}">${esc(k)}</button>`).join('')}</div>
        </section>
        <section class="st-right">
          <div class="st-rtabs" role="tablist"><button type="button" data-r="run" role="tab">▶ ${L.run}</button><button type="button" data-r="ai" role="tab">✦ ${esc(L.aiTitle)}</button></div>
          <div class="st-run">
            <div class="st-stage" id="stStage"><p class="st-idle">${esc(L.idle)}</p></div>
            <div class="st-con"><div class="st-conh"><b>${L.console}</b><button type="button" id="stConClear">${L.clear}</button></div><div class="st-log" id="stLog" aria-live="polite"></div></div>
          </div>
          <div class="st-ai" id="stAi"></div>
        </section>
      </div>
      <details class="st-details" id="stDetails"><summary>${esc(L.details)}</summary><div class="editor">
        <label>${esc(L.summary)}<input id="stSummary" maxlength="200"></label>
        <div class="only-sim"><label>${esc(L.question)}<textarea id="stQ" rows="3"></textarea></label><div class="two"><label>${esc(L.answer)}<input id="stAns" maxlength="400" spellcheck="false"></label><label>${esc(L.unit)}<input id="stUnit" maxlength="24"></label></div></div>
        <div class="only-code"><label>${esc(L.body)}<textarea id="stBody" rows="5"></textarea></label><p class="help">${esc(ctx.T.helpCode)}</p></div>
      </div></details>
      <details class="st-details st-ref"><summary>${esc(L.ref)}</summary><table class="st-reftab"><tbody>${REF.map(r=>`<tr><td><code>${esc(r[0])}</code></td><td>${esc(ko?r[1]:r[2])}</td></tr>`).join('')}</tbody></table>
        <p class="help">${ko?'옛 작품의 함수(W, H, loop, slider(이름, 최소, 최대, 간격, 값), circle, line, arrow, text, show, button, clear: 픽셀 좌표)도 그대로 쓸 수 있습니다.':'The original helpers (W, H, loop, slider(label, min, max, step, value), circle, line, arrow, text, show, button, clear, in pixels) still work.'}</p></details>
    </div>`;
    const $=s=>root.querySelector(s),studio=$('.studio');
    const msg=(t,cls='')=>{const m=$('#stMsg');m.className='st-msg '+cls;m.textContent=t||'';ctx.height();};

    /* the editor */
    let quiet=false;
    const ed=E().create($('#stEd'),{value:'',lang:'js',label:L.code,onRun:()=>run(),onSave:()=>autosave(true),onChange:v=>{
      if(quiet)return;
      if(d.kind==='sim')d.code=v;else if(file==='main')d.starter=v;else d.grader=v;
      clearTimeout(saveT);saveT=setTimeout(autosave,700);
      if(auto&&d.kind==='sim'){clearTimeout(autoT);autoT=setTimeout(()=>run(),900);}
    }});
    function showFile(){
      const v=d.kind==='sim'?d.code:file==='main'?d.starter:d.grader;ed.setLang(d.kind==='sim'?'js':'py');quiet=true;ed.setValue(v||'');quiet=false;
      $('#stFiles').innerHTML=d.kind==='sim'?`<span class="st-file on">sim.js</span>`:`<button type="button" class="st-file ${file==='main'?'on':''}" data-f="main">${esc(L.solution)}</button><button type="button" class="st-file ${file==='grader'?'on':''}" data-f="grader">${esc(L.grader)}</button>`;
      $('#stFiles').querySelectorAll('[data-f]').forEach(b=>b.onclick=()=>{file=b.dataset.f;showFile();});
    }
    function fillForm(){
      $('#stTitle').value=d.title||'';$('#stKind').value=d.kind;$('#stSummary').value=d.summary||'';
      $('#stQ').value=d.kind==='sim'?d.body||'':'';$('#stBody').value=d.kind==='code'?d.body||'':'';$('#stAns').value=d.answer||'';$('#stUnit').value=d.unit||'';
      studio.querySelector('.only-sim').hidden=d.kind!=='sim';studio.querySelector('.only-code').hidden=d.kind!=='code';
      $('#stAuto').checked=auto;$('#stAuto').disabled=d.kind!=='sim';
      $('#stTpl').innerHTML=`<option value="">${esc(L.tpl)}…</option>`+tplOptions();
      showFile();paintAi();
    }
    const readForm=()=>{d.title=$('#stTitle').value;d.summary=$('#stSummary').value;if(d.kind==='sim'){d.body=$('#stQ').value;d.answer=$('#stAns').value;d.unit=$('#stUnit').value;}else d.body=$('#stBody').value;};
    for(const s of ['#stTitle','#stSummary','#stQ','#stBody','#stAns','#stUnit'])$(s).addEventListener('input',()=>{readForm();clearTimeout(saveT);saveT=setTimeout(autosave,700);});
    function autosave(now){readForm();const ok=store.set(key,JSON.stringify({t:Date.now(),d:pick(d)}));if(now===true&&ok)msg(L.autosaved,'ok');}
    $('#stKind').onchange=()=>{readForm();d.kind=$('#stKind').value;file='main';
      if(d.kind==='code'&&!d.grader&&ctx.codeTemplate){d.starter=d.starter||ctx.codeTemplate.starter;d.grader=ctx.codeTemplate.grader;d.body=d.body||ctx.codeTemplate.body;}
      if(d.kind==='sim'&&!d.code)d.code=TPL()?.byId('blank')?.code||'';
      stop();fillForm();autosave();ctx.height();};

    /* layout: the right pane's tabs, and the phone's three tabs */
    function layout(){studio.dataset.pane=pane;studio.dataset.right=right;
      studio.querySelectorAll('[data-r]').forEach(b=>{b.classList.toggle('on',b.dataset.r===right);b.setAttribute('aria-selected',b.dataset.r===right);});
      const m=pane==='code'?'code':right;studio.querySelectorAll('[data-m]').forEach(b=>{b.classList.toggle('on',b.dataset.m===m);b.setAttribute('aria-selected',b.dataset.m===m);});ctx.height();}
    studio.querySelectorAll('[data-r]').forEach(b=>b.onclick=()=>{right=b.dataset.r;layout();});
    studio.querySelectorAll('[data-m]').forEach(b=>b.onclick=()=>{if(b.dataset.m==='code')pane='code';else{pane='right';right=b.dataset.m;}layout();});
    const narrow=()=>matchMedia('(max-width: 899px)').matches;
    studio.querySelectorAll('[data-k]').forEach(b=>{b.addEventListener('pointerdown',e=>e.preventDefault());b.onclick=()=>{const k=b.dataset.k;
      if(k==='⇥')ed.insert(d.kind==='sim'?'  ':'    ');else if(/^. .$/.test(k)){ed.insert(k[0]+k[2]);const t=ed.el;t.setSelectionRange(t.selectionStart-1,t.selectionStart-1);}else ed.insert(k);};});

    /* the console */
    const logBox=$('#stLog');let pending=[],painting=0,logCount=0;
    function log(level,text){pending.push([level,text]);if(!painting)painting=requestAnimationFrame(()=>{painting=0;const frag=document.createDocumentFragment();
      for(const [lv,t] of pending.splice(0)){if(logCount>=500){logBox.firstChild&&logBox.firstChild.remove();}else logCount++;const div=document.createElement('div');div.className='lg-'+lv;div.textContent=t;frag.append(div);}
      logBox.append(frag);logBox.scrollTop=logBox.scrollHeight;});}
    $('#stConClear').onclick=()=>{logBox.textContent='';logCount=0;};

    /* running */
    function stop(quiet){
      clearTimeout(autoT);
      if(runner){runner.stop();runner=null;}
      if(worker){clearTimeout(wtimer);worker.terminate();worker=null;}
      $('#stRun').disabled=false;
      if(quiet!==true)$('#stStage').innerHTML=`<p class="st-idle">${esc(L.stopped)}</p>`;
    }
    function run(){
      readForm();stop(true);ed.markError(0);lastError='';
      if(narrow()&&pane==='code'){pane='right';right='run';layout();}else if(right!=='run'&&!narrow()){right='run';layout();}
      if(d.kind==='sim'){
        log('info','— '+new Date().toLocaleTimeString()+' —');
        runner=runSandbox($('#stStage'),{code:d.code,dark:ctx.dark,fit:true,onLog:log,
          onError:(m,line)=>{lastError=m+(line?` (${L.line} ${line})`:'');log('error',(line?L.line+' '+line+': ':'')+m);if(line)ed.markError(line);paintAi(true);},
          onHang:()=>{log('error',L.hang);$('#stStage').innerHTML=`<p class="st-idle bad">${esc(L.hang)}</p>`;runner=null;}});
      }else runPython();
    }
    function runPython(){
      const stage=$('#stStage');stage.innerHTML=`<p class="st-idle" id="stPy">${esc(L.loading)}</p>`;
      const id=++job;$('#stRun').disabled=true;
      worker=new Worker('compute-worker.js');
      const done=()=>{clearTimeout(wtimer);$('#stRun').disabled=false;};
      worker.onmessage=ev=>{const m=ev.data;if(!m||m.id!==id)return;
        if(m.phase==='running'){$('#stPy')&&($('#stPy').textContent=L.pyRunning);clearTimeout(wtimer);wtimer=setTimeout(()=>{stop();log('error',L.timeout);},30000);}
        if(m.phase==='done'){done();pyResult(m.result,typeof m.stdout==='string'?m.stdout:'');worker.terminate();worker=null;}};
      worker.onerror=()=>{done();stop();log('error','worker error');};
      wtimer=setTimeout(()=>{stop();log('error',L.timeout);},120000);
      const grader=(d.grader&&/def\s+grade\s*\(/.test(d.grader)?d.grader:PY_NOGRADE)+PY_WRAP;
      worker.postMessage({id,code:PY_PRELUDE+(d.starter||''),grader,common:window.HL_COMPUTE_PROBLEMS?.COMMON||''});
    }
    function pyResult(r,stdout){
      const stage=$('#stStage');stage.innerHTML='';
      if(stdout.trim())for(const l of stdout.replace(/\n$/,'').split('\n').slice(0,400))log('log',l);
      if(!r||r.error){const t=String(r?.error||'error')+(r?.trace?'\n'+r.trace:'');const m=/solution\.py", line (\d+)/.exec(t);const line=m?Math.max(1,+m[1]-1):0;
        lastError=String(r?.error||'');log('error',(line?L.line+' '+line+': ':'')+String(r?.error||'error'));if(line&&file==='main')ed.markError(line);
        stage.innerHTML=`<p class="st-idle bad">${esc(String(r?.error||'error'))}</p>`;return;}
      const tests=Array.isArray(r.tests)?r.tests.filter(t=>t&&typeof t==='object').slice(0,50):[],all=tests.length>0&&tests.every(t=>t.ok);
      const fmt=v=>v==null?'—':typeof v==='number'?String(+v.toPrecision(6)):typeof v==='string'?v.slice(0,200):JSON.stringify(v).slice(0,200);
      const box=document.createElement('div');box.className='st-py';
      box.innerHTML=`<p class="${tests.length?all?'ok':'bad':''}">${tests.length?(all?'✓ '+L.pass:L.fail)+` (${tests.filter(t=>t.ok).length}/${tests.length})`:L.noTests}</p>`+
        (tests.length?`<div class="tablewrap"><table><tbody>${tests.map(t=>`<tr><td>${esc(String(t.name??''))}</td><td class="${t.ok?'ok':'bad'}">${t.ok?'✓':'✗'}</td><td>${esc(fmt(t.got))}</td><td>${esc(fmt(t.want))}</td></tr>`).join('')}</tbody></table></div>`:'');
      stage.append(box);
      for(const p of Array.isArray(r.__plots)?r.__plots.slice(0,8):[])pyPlot(stage,p);
      ctx.height();
    }
    /* a plot from Python: numbers only, drawn by this page */
    function pyPlot(stage,p){
      const xs=(Array.isArray(p?.x)?p.x:[]).map(Number),ys=(Array.isArray(p?.y)?p.y:[]).map(Number),n=Math.min(xs.length,ys.length,4000);if(n<1)return;
      const cv=document.createElement('canvas');cv.className='st-plot';stage.append(cv);
      const r=cv.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);cv.width=r.width*dpr;cv.height=r.height*dpr;const g=cv.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);
      const w=r.width,h=r.height,Lm=52,R=10,T=20,B=22;let x0=Infinity,x1=-Infinity,y0=Infinity,y1=-Infinity;
      for(let i=0;i<n;i++){if(!isFinite(xs[i])||!isFinite(ys[i]))continue;x0=Math.min(x0,xs[i]);x1=Math.max(x1,xs[i]);y0=Math.min(y0,ys[i]);y1=Math.max(y1,ys[i]);}
      if(!(x1>=x0))return;if(x1===x0)x1+=1;if(y1===y0){y0-=1;y1+=1;}
      const ink=getComputedStyle(document.documentElement).getPropertyValue('--ink')||'#263247',muted=getComputedStyle(document.documentElement).getPropertyValue('--muted')||'#657187';
      const X=x=>Lm+(x-x0)/(x1-x0)*(w-Lm-R),Y=y=>h-B-(y-y0)/(y1-y0)*(h-T-B);
      g.font='12px system-ui,sans-serif';g.fillStyle=ink;g.fillText(String(p.title||p.label||'plot').slice(0,80),Lm,14);
      g.fillStyle=muted;g.textAlign='right';g.fillText(String(+y1.toPrecision(4)),Lm-4,T+9);g.fillText(String(+y0.toPrecision(4)),Lm-4,h-B);g.textAlign='left';g.fillText(String(+x0.toPrecision(4)),Lm,h-6);g.textAlign='right';g.fillText(String(+x1.toPrecision(4)),w-R,h-6);
      g.strokeStyle=muted;g.globalAlpha=.3;g.strokeRect(Lm,T,w-Lm-R,h-T-B);g.globalAlpha=1;
      g.beginPath();let started=false;for(let i=0;i<n;i++){if(!isFinite(xs[i])||!isFinite(ys[i])){started=false;continue;}started?g.lineTo(X(xs[i]),Y(ys[i])):g.moveTo(X(xs[i]),Y(ys[i]));started=true;}
      g.strokeStyle='#2563eb';g.lineWidth=1.6;g.stroke();
    }
    $('#stRun').onclick=()=>run();$('#stStop').onclick=()=>{stop();log('info',L.stopped);};
    $('#stAuto').onchange=()=>{auto=$('#stAuto').checked;store.set('hlStudioAuto',auto?'1':'0');if(auto)run();};

    /* undo for whole-file changes (an example, an AI proposal); typing has the browser's own Ctrl+Z */
    function remember(){history.push({kind:d.kind,file,code:d.code,starter:d.starter,grader:d.grader});if(history.length>30)history.shift();$('#stUndo').disabled=false;}
    $('#stUndo').onclick=()=>{const h=history.pop();if(!h)return;Object.assign(d,{code:h.code,starter:h.starter,grader:h.grader});if(h.kind!==d.kind){d.kind=h.kind;fillForm();}else{file=h.file;showFile();}$('#stUndo').disabled=!history.length;autosave();if(auto&&d.kind==='sim')run();};
    $('#stTpl').onchange=()=>{const v=$('#stTpl').value;$('#stTpl').value='';if(!v)return;
      const cur=d.kind==='sim'?d.code:d.starter;if(cur&&cur.trim()&&!confirm(L.confirmTpl))return;remember();
      if(d.kind==='sim'){const t=TPL()?.byId(v);if(!t)return;d.code=t.code;if(!d.title.trim()){d.title=ko?t.ko:t.en;$('#stTitle').value=d.title;}}
      else if(ctx.codeTemplate){d.starter=ctx.codeTemplate.starter;d.grader=ctx.codeTemplate.grader;if(!d.body)d.body=ctx.codeTemplate.body;$('#stBody').value=d.body;}
      showFile();autosave();run();};

    /* ── the AI panel ── */
    let quota=null,asking=false;
    function paintAi(keep){
      const box=$('#stAi');
      if(d.kind!=='sim'){box.innerHTML=`<h2>${esc(L.aiTitle)}</h2><p class="note">${esc(L.aiPython)}</p>`;return;}
      if(!ctx.token()){box.innerHTML=`<h2>${esc(L.aiTitle)}</h2><p class="note">${esc(L.aiLede)}</p><p class="note">${esc(L.aiLogin)}</p><p><a class="btn primary" href="/#/login" target="_top">${esc(L.login)}</a></p>`;return;}
      if(keep&&box.querySelector('#aiPrompt'))return;
      box.innerHTML=`<h2>${esc(L.aiTitle)}</h2><p class="note">${esc(L.aiLede)}</p>
        <textarea id="aiPrompt" rows="3" maxlength="2000" placeholder="${esc(L.aiPh)}"></textarea>
        <div class="st-chips">${L.chips.map((c,i)=>`<button type="button" data-chip="${i}">${esc(c)}</button>`).join('')}</div>
        <div class="row"><button type="button" class="primary" id="aiAsk">${esc(L.aiAsk)}</button><span class="note" id="aiLeft"></span></div>
        <p class="st-aimsg" id="aiMsg" role="status"></p><div id="aiOut"></div>`;
      box.querySelectorAll('[data-chip]').forEach(b=>b.onclick=()=>{const i=+b.dataset.chip,p=$('#aiPrompt');
        p.value=i===3&&lastError?(ko?'실행하면 이 오류가 납니다. 고쳐 줘: ':'It fails with this error, fix it: ')+lastError:i===4?(ko?'처음부터 새로 만들어 줘: ':'Start over and build: '):L.chips[i];p.focus();});
      $('#aiAsk').onclick=ask;
      showQuota();
    }
    async function showQuota(){
      if(!ctx.token())return;
      if(quota==null){try{quota=(await ctx.api('/api/workshop/code-ai')).left;}catch(e){quota=null;}}
      const el=$('#aiLeft');if(el)el.textContent=quota!=null?L.aiLeft(quota):'';
    }
    async function ask(){
      if(asking)return;const prompt=$('#aiPrompt').value.trim();if(!prompt){$('#aiPrompt').focus();return;}
      if(prompt.length>2000){$('#aiMsg').textContent=L.aiErr.bad_prompt;return;}
      if(d.code.length>60000){$('#aiMsg').textContent=L.aiErr.bad_code;return;}
      asking=true;$('#aiAsk').disabled=true;$('#aiMsg').className='st-aimsg';$('#aiMsg').textContent=L.aiAsking;$('#aiOut').innerHTML='';
      const fresh=/^(처음부터 새로|Start over)/.test(prompt);
      try{
        const r=await ctx.api('/api/workshop/code-ai','POST',{prompt,code:fresh?'':d.code,error:lastError.slice(0,1000),lang:ko?'ko':'en'});
        if(typeof r?.code!=='string'||!r.code.trim())throw Object.assign(new Error('ai_failed'),{code:'ai_failed'});
        quota=Number.isFinite(r.left)?r.left:quota;showQuota();
        proposal={code:r.code.slice(0,60000),explanation:typeof r.explanation==='string'?r.explanation.slice(0,1500):''};
        $('#aiMsg').textContent='';showProposal();
      }catch(e){$('#aiMsg').className='st-aimsg bad';$('#aiMsg').textContent=L.aiErr[e.code]||(e.status?L.aiErr.ai_failed:L.aiErr.network);}
      finally{asking=false;const b=$('#aiAsk');if(b)b.disabled=false;ctx.height();}
    }
    function showProposal(){
      const out=$('#aiOut');if(!proposal){out.innerHTML='';return;}
      const diff=E().diffLines(d.code,proposal.code),add=diff.filter(x=>x.op==='+').length,rem=diff.filter(x=>x.op==='-').length;
      /* only the changed lines with three lines around them */
      const keep=new Set();diff.forEach((x,i)=>{if(x.op!==' ')for(let k=i-3;k<=i+3;k++)keep.add(k);});
      const rows=[];let gap=false;
      diff.forEach((x,i)=>{if(!keep.has(i)){if(!gap)rows.push('<div class="df-gap">⋯</div>');gap=true;return;}gap=false;rows.push(`<div class="df-${x.op===' '?'eq':x.op==='+'?'add':'del'}"><i>${x.op}</i>${esc(x.text)||' '}</div>`);});
      out.innerHTML=`<div class="st-explain"></div><p class="note">${esc(add||rem?L.diffHead(add,rem):L.aiNoChange)}</p><div class="st-diff">${rows.join('')}</div>
        <div class="row"><button type="button" class="primary" id="aiApply" ${add||rem?'':'disabled'}>${esc(L.apply)}</button><button type="button" id="aiDrop">${esc(L.discard)}</button></div>`;
      out.querySelector('.st-explain').textContent=proposal.explanation;
      $('#aiApply').onclick=()=>{if(!proposal)return;if(d.kind!=='sim')return;remember();d.code=proposal.code;proposal=null;quiet=true;ed.setValue(d.code,{undoable:true});quiet=false;autosave();
        out.innerHTML=`<p class="ok">${esc(L.applied)}</p>`;run();};
      $('#aiDrop').onclick=()=>{proposal=null;out.innerHTML='';ctx.height();};
      ctx.height();
    }

    /* ── saving ── */
    const fileName=ext=>(d.title.trim()||(d.kind==='sim'?'simulation':'problem')).replace(/[\\/:*?"<>|\u0000-\u001f]/g,'_').slice(0,60)+ext;
    const fileText=()=>d.kind==='sim'?`// ${d.title.trim()||'HaslaLab simulation'} · HaslaLab Workshop (hl helpers: sim-sandbox.html)\n${d.code}`:`# ${d.title.trim()||'HaslaLab problem'}\n# ── solution.py ──\n${d.starter}\n\n# ── grader.py ──\n${d.grader}`;
    $('#stDown').onclick=()=>{readForm();const blob=new Blob([fileText()],{type:'text/plain;charset=utf-8'}),a=document.createElement('a');
      a.href=URL.createObjectURL(blob);a.download=fileName(d.kind==='sim'?'.js':'.py');document.body.append(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},1000);};
    /* the storage file this creation was saved to: {id, name, folder}, kept on this device beside the autosave */
    const refKey='hlStudioStore:'+(id||'new');
    let storeRef=(()=>{try{const r=JSON.parse(store.get(refKey)||'null');return r&&/^[0-9a-f]{32}$/.test(r.id)?r:null;}catch(e){return null;}})();
    const setRef=f=>{storeRef=f?{id:f.id,name:f.name,folder:f.folder}:null;if(storeRef)store.set(refKey,JSON.stringify(storeRef));else store.del(refKey);};
    async function sendForm(path,method,fd){
      let r;try{r=await fetch(ctx.apiBase+path,{method,headers:{Authorization:'Bearer '+ctx.token()},body:fd});}catch(e){throw Object.assign(new Error('network'),{code:'network'});}
      const j=await r.json().catch(()=>({}));if(!r.ok)throw Object.assign(new Error(j.error||'error'),{code:j.error,status:r.status});return j;
    }
    $('#stStore').onclick=async()=>{
      readForm();if(!ctx.token()){msg(L.needLogin,'bad');return;}
      const b=$('#stStore');b.disabled=true;
      try{
        const kind=d.kind==='sim'?'sim':'file',name=fileName(d.kind==='sim'?'.js.txt':'.py.txt'),file=()=>new File([fileText()],name,{type:'text/plain'});
        let f=null;
        if(storeRef){
          const fd=new FormData();fd.append('file',file());fd.append('kind',kind);
          try{f=(await sendForm('/api/workshop/storage/files/'+storeRef.id+'/content','PUT',fd)).file;}
          catch(e){if(e.status!==404&&e.code!=='type_change')throw e;}
          if(f){setRef(f);msg(L.updated((f.folder?f.folder+'/':'')+f.name),'ok');return;}
        }
        const fd=new FormData();fd.append('file',file());fd.append('folder',L.folder);fd.append('kind',kind);fd.append('ensure_folder','1');
        f=(await sendForm('/api/workshop/storage/files','POST',fd)).file;
        setRef(f);msg(L.savedStorage((f.folder?f.folder+'/':'')+f.name),'ok');
      }catch(e){msg(L.err[e.code]||e.message||'error','bad');}
      finally{b.disabled=false;}
    };
    /* a saved file → the editor: «// title · HaslaLab Workshop …» then the code; a Python one has its two sections */
    function fromText(text,name){
      const t=String(text).replace(/\r\n?/g,'\n');
      if(/\.js\.txt$/i.test(name)){const m=/^\/\/ (.*?) · HaslaLab Workshop[^\n]*\n/.exec(t);return {kind:'sim',title:m?m[1]:name.replace(/\.js\.txt$/i,''),code:m?t.slice(m[0].length):t};}
      const m=/^# (.*)\n# ── solution\.py ──\n([\s\S]*?)\n\n# ── grader\.py ──\n([\s\S]*)$/.exec(t);
      return m?{kind:'code',title:m[1],starter:m[2],grader:m[3]}:null;
    }
    $('#stOpenStore').onclick=async()=>{
      if(!ctx.token()){msg(L.needLogin,'bad');return;}
      let dlg=document.getElementById('stStoreDlg');if(!dlg){dlg=document.createElement('dialog');dlg.id='stStoreDlg';dlg.className='stdlg';document.body.append(dlg);}
      dlg.innerHTML=`<div class="dlg-head"><h2>${esc(L.openTitle)}</h2><button type="button" data-x aria-label="${esc(L.close)}">✕</button></div><div class="dlg-list"><p class="note">${esc(L.loading)}</p></div><p class="note" data-msg></p>`;
      dlg.querySelector('[data-x]').onclick=()=>dlg.close();
      if(!dlg.open)dlg.showModal();
      const list=dlg.querySelector('.dlg-list'),say=(t,c)=>{const m=dlg.querySelector('[data-msg]');m.className='note '+(c||'');m.textContent=t;};
      let files=[];
      try{
        /* the files saved as simulations, and the ones saved before files had a kind (a .js.txt or .py.txt in the folder) */
        const [a,b]=await Promise.all([ctx.api('/api/workshop/storage?kind=sim'),ctx.api('/api/workshop/storage?folder='+encodeURIComponent(L.folder))]);
        const seen=new Set();files=[...(a.files||[]),...(b.files||[])].filter(f=>/\.(js|py)\.txt$/i.test(f.name)&&!seen.has(f.id)&&seen.add(f.id)).sort((x,y)=>y.updated_at-x.updated_at);
      }catch(e){list.innerHTML=`<p class="bad">${esc(L.err[e.code]||e.message||'error')}</p>`;return;}
      const when=s=>new Date(s*1000).toLocaleString(ko?'ko-KR':'en-GB',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
      list.innerHTML=files.length?files.map(f=>`<button type="button" class="dlg-file${storeRef?.id===f.id?' on':''}" data-id="${f.id}"><b>${esc(f.name)}</b><span>${esc(f.folder||'/')} · ${when(f.updated_at)}</span></button>`).join(''):`<p class="empty">${esc(L.none)}</p>`;
      list.querySelectorAll('[data-id]').forEach(btn=>btn.onclick=async()=>{
        const f=files.find(x=>x.id===btn.dataset.id);
        try{
          const r=await fetch(ctx.apiBase+'/api/workshop/storage/files/'+f.id,{headers:{Authorization:'Bearer '+ctx.token()}});
          if(!r.ok){const j=await r.json().catch(()=>({}));throw Object.assign(new Error(j.error||'error'),{code:j.error});}
          const got=fromText((await r.text()).slice(0,200000),f.name);
          if(!got){say(L.badFile,'bad');return;}
          remember();stop(true);
          d.kind=got.kind;d.title=(got.title||'').slice(0,80);if(got.kind==='sim')d.code=got.code.slice(0,60000);else{d.starter=got.starter;d.grader=got.grader;}
          file='main';fillForm();autosave();setRef(f);dlg.close();msg(L.opened((f.folder?f.folder+'/':'')+f.name),'ok');
          if(d.kind==='sim'&&d.code.trim())run();
        }catch(e){say(L.err[e.code]||e.message||'error','bad');}
      });
    };
    /* publishing: the creation is saved (creations.js), then shared in 작품 공유 with its details through the sharing
       dialog (share-makers.js → HL_SHARE.publish with creation_id, so a remix draft or an existing creation is published
       as itself, never as a new project). No thumbnail: the sandbox does not hand frames to the page. */
    /* the creation's number (the address gives it as text; creation_id must be a number, or the server makes a new project) */
    let savedId=/^\d{1,9}$/.test(String(id||''))?+id:null;
    const creationBody=()=>({kind:d.kind,title:d.title.trim(),summary:d.summary.trim(),body:d.body,code:d.kind==='sim'?d.code:'',answer:d.kind==='sim'?d.answer.trim():'',unit:d.kind==='sim'?d.unit.trim():'',starter:d.kind==='code'?d.starter:'',grader:d.kind==='code'?d.grader:''});
    async function saveCreation(){
      const body=creationBody();
      if(savedId)await ctx.api('/api/creations/'+savedId,'PATCH',body);
      else savedId=(await ctx.api('/api/creations','POST',{...body,...(Number.isInteger(d.forked_from)?{forked_from:d.forked_from}:{})})).id;
      store.del(key);return savedId;
    }
    const sharePayload=()=>d.kind==='sim'?{code:d.code,question:d.body||'',answer:d.answer.trim(),answerUnit:d.unit.trim()}:{statement:d.body||'',starter:d.starter||'',grader:d.grader||''};
    const withoutPayload=input=>{const o={...input};delete o.payload;return o;};
    $('#stPub').onclick=async()=>{
      readForm();if(!ctx.token()){msg(L.needLogin,'bad');return;}
      if(!d.title.trim()){msg(L.err.bad_title,'bad');$('#stTitle').focus();return;}
      if(d.kind==='sim'&&d.answer.trim()&&!ctx.answerFrom(d.answer.trim())){msg(L.answer,'bad');$('#stDetails').open=true;return;}
      const SM=window.HL_SHARE_MAKER,HS=window.HL_SHARE,b=$('#stPub');
      if(!SM||!HS){b.disabled=true;try{const to=await saveCreation();stop(true);ctx.go('play',to);}catch(e){msg(ctx.errText(e),'bad');}finally{b.disabled=false;}return;}
      b.disabled=true;
      let shared=null;if(savedId){try{shared=(await HS.get(savedId)).project;}catch(e){shared=null;}}
      b.disabled=false;
      const type=d.kind==='sim'?'sim':'python',live=!!(shared&&shared.status==='public');
      const values={title:d.title.trim(),description:shared?.description||d.summary.trim(),howto:shared?.howto||'',notes:shared?.notes||'',tags:shared?.tags||[],topic:shared?.topic||'other'};
      let done=false;
      const dlg=SM.dialog({lang:ko?'ko':'en',type,values,shared:live?{id:savedId,published:true}:null,height:ctx.height,errText:ctx.errText,
        build:fv=>SM.publishInput({type,form:fv,payload:sharePayload(),creationId:savedId||undefined}),
        publish:async input=>{const cid=await saveCreation();return HS.publish({...withoutPayload(input),creation_id:cid});},
        update:async input=>{await saveCreation();return HS.update(savedId,withoutPayload(input));},
        unpublish:()=>HS.unpublish(savedId),
        onDone:r=>{done=!r.unpublished;if(r.form&&r.form.title){d.title=r.form.title;$('#stTitle').value=d.title;}}});
      dlg.addEventListener('close',()=>{if(done){stop(true);ctx.go('play',savedId);}},{once:true});
    };
    $('#stBack').onclick=()=>{autosave();stop(true);document.querySelector('main')?.classList.remove('wide');ctx.go('gallery');};

    fillForm();layout();
    if(note)msg(note,'ok');
    if(offer){const m=$('#stMsg');m.className='st-msg';m.innerHTML=`${esc(L.restoreOffer)} <button type="button" id="stRestore">${esc(L.restore)}</button> <button type="button" id="stDrop">${esc(L.drop)}</button>`;
      $('#stRestore').onclick=()=>{remember();d={...d,...autoBackup.d};fillForm();msg('');run();};$('#stDrop').onclick=()=>{store.del(key);msg('');};}
    if(!ctx.token()&&!note&&!offer)msg(L.needLogin);
    if(d.kind==='sim'&&d.code.trim())run();
    ctx.height();
    return {stop};
  }
  window.HL_STUDIO={open,runSandbox};
})();
