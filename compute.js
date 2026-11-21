/* Computational physics judge: the learner's Python runs in this browser (Pyodide in a Web Worker),
   graded against physics (exact solutions, conservation laws, reference integrations). Nothing is sent anywhere. */
(()=>{
  'use strict';
  const C=window.HL_COMPUTE_PROBLEMS,P=window.HL_LEARN_PATH||null;
  const $=id=>document.getElementById(id);
  const params=new URL(location.href).searchParams;
  const embedded=params.get('embed')==='1'&&window.parent!==window;
  const TIME_LIMIT=30000;
  const copy={
    ko:{title:'계산물리',intro:'물리 시뮬레이션을 Python으로 직접 짜고, 정확해 · 보존 법칙 · 기준 계산과 비교해 채점받으세요. 코드는 이 브라우저 안에서만 실행됩니다. numpy를 쓸 수 있습니다.',
      code:'Python 코드',run:'실행 · 채점',reset:'처음 코드로',stop:'중지',loading:'Python을 불러오는 중… (처음 한 번은 몇 초 걸립니다)',running:'실행 중…',
      timeout:'시간 제한(30초)을 넘어 중지했습니다. 무한 루프나 너무 작은 시간 간격이 없는지 확인하세요.',stopped:'중지했습니다.',
      pass:'모두 통과했습니다',fail:'통과하지 못한 검사가 있습니다',error:'코드를 실행하다 오류가 났습니다',test:'검사',result:'결과',got:'내 값',want:'기준',
      ok:'통과',bad:'실패',step:'단계',solved:'해결',stdout:'출력',confirmReset:'처음 코드로 되돌릴까요? 지금 코드는 사라집니다.',
      note:'채점은 이 브라우저에서 합니다. 해결 기록과 작성 중인 코드는 이 기기에만 저장됩니다.'},
    en:{title:'Computational physics',intro:'Write physics simulations in Python and have them graded against exact solutions, conservation laws and reference calculations. Your code runs only in this browser; numpy is available.',
      code:'Python code',run:'Run & grade',reset:'Starter code',stop:'Stop',loading:'Loading Python… (a few seconds the first time)',running:'Running…',
      timeout:'Stopped after the 30-second limit. Check for an endless loop or a time step that is too small.',stopped:'Stopped.',
      pass:'All tests passed',fail:'Some tests failed',error:'Your code raised an error',test:'Test',result:'Result',got:'Yours',want:'Reference',
      ok:'pass',bad:'fail',step:'Step',solved:'Solved',stdout:'Output',confirmReset:'Go back to the starter code? Your current code will be lost.',
      note:'Grading happens in this browser. Solved problems and drafts are kept on this device only.'}
  };
  const state={lang:params.get('lang')==='en'?'en':'ko',worker:null,job:0,timer:0,current:null};
  const tr=k=>copy[state.lang][k];
  const store={
    get(k){try{return localStorage.getItem('hlCompute:'+k);}catch(e){return null;}},
    set(k,v){try{localStorage.setItem('hlCompute:'+k,v);}catch(e){}}
  };
  const solved=()=>{try{return new Set(JSON.parse(store.get('solved')||'[]'));}catch(e){return new Set();}};
  const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

  function applyTheme(){
    const t=params.get('theme'),dark=t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.dataset.theme=dark?'dark':'light';
  }
  function reportHeight(){
    if(!embedded)return;
    requestAnimationFrame(()=>window.parent.postMessage({type:'hl-compute-height',height:Math.ceil(document.documentElement.scrollHeight)},location.origin));
  }
  function areaLabel(p){
    const area=P?.AREAS.find(a=>a.key===p.area),sub=area?.subtopics.find(s=>s.key===p.subtopic);
    return [area?.name[state.lang],sub?.name[state.lang]].filter(Boolean).join(' · ');
  }
  /* statements: paragraphs, numbered lists and `code`, with $…$ left for KaTeX */
  function renderStatement(text){
    return esc(text).split(/\n{2,}/).map(block=>{
      const lines=block.split('\n'),inline=s=>s.replace(/`([^`]+)`/g,'<code>$1</code>');
      if(lines.every(l=>/^\d+\.\s/.test(l)))return '<ol>'+lines.map(l=>'<li>'+inline(l.replace(/^\d+\.\s/,''))+'</li>').join('')+'</ol>';
      return '<p>'+lines.map(inline).join('<br>')+'</p>';
    }).join('');
  }
  function paintList(){
    const done=solved();
    $('plist').innerHTML=C.PROBLEMS.map(p=>`<li><button type="button" data-id="${p.id}" aria-current="${p.id===state.current?.id}">
      <b>${esc(p.title[state.lang])}</b><span class="meta">${tr('step')} ${p.step} · ${esc(areaLabel(p))}${done.has(p.id)?` · <span class="solved">✓ ${tr('solved')}</span>`:''}</span></button></li>`).join('');
  }
  function select(id,{push=true}={}){
    const p=C.byId(id)||C.PROBLEMS[0];
    state.current=p;
    $('statement').innerHTML=`<h2>${esc(p.title[state.lang])}</h2><p class="meta">${tr('step')} ${p.step} · ${esc(areaLabel(p))}</p>${renderStatement(p.statement[state.lang])}`;
    if(window.renderMathInElement)renderMathInElement($('statement'),{delimiters:[{left:'$',right:'$',display:false}],throwOnError:false});
    $('code').value=store.get('code:'+p.id)||p.starter;
    $('results').innerHTML='';$('plotbox').hidden=true;$('out').hidden=true;$('status').textContent='';
    paintList();
    if(push){
      const url=new URL(location.href);url.searchParams.set('problem',p.id);history.replaceState(null,'',url);
      if(embedded)window.parent.postMessage({type:'hl-compute-problem',problem:p.id},location.origin);
    }
    reportHeight();
  }
  function translate(){
    document.documentElement.lang=state.lang;
    document.querySelectorAll('[data-i18n]').forEach(el=>{el.textContent=tr(el.dataset.i18n);});
    document.title=tr('title')+' · HaslaLab';
  }

  function stopWorker(message){
    clearTimeout(state.timer);
    if(state.worker){state.worker.terminate();state.worker=null;}
    busy(false);if(message)$('status').textContent=message;
  }
  function busy(on){$('run').disabled=on;$('stop').hidden=!on;}
  function run(){
    const p=state.current,code=$('code').value;
    store.set('code:'+p.id,code);
    if(!state.worker)state.worker=new Worker('compute-worker.js');
    const job=++state.job;busy(true);$('status').textContent=tr('loading');
    $('results').innerHTML='';$('plotbox').hidden=true;$('out').hidden=true;
    let started=false;
    state.worker.onmessage=event=>{
      const m=event.data;if(m.id!==job)return;
      if(m.phase==='running'){started=true;$('status').textContent=tr('running');clearTimeout(state.timer);state.timer=setTimeout(()=>stopWorker(tr('timeout')),TIME_LIMIT);}
      if(m.phase==='done'){clearTimeout(state.timer);busy(false);$('status').textContent='';show(p,m.result,m.stdout);}
    };
    state.worker.onerror=()=>stopWorker(tr('error'));
    /* loading Pyodide is not counted against the time limit, but a stalled download still ends */
    state.timer=setTimeout(()=>{if(!started)stopWorker(tr('timeout'));},120000);
    state.worker.postMessage({id:job,code,grader:p.grader,common:C.COMMON});
  }
  const fmt=v=>v===null||v===undefined?'—':typeof v==='number'?(Math.abs(v)>=1e4||Math.abs(v)<1e-3&&v!==0?v.toExponential(4):String(+v.toPrecision(6))):esc(v);
  function show(p,result,stdout){
    const box=$('results');
    if(!result||result.error){
      box.innerHTML=`<p class="verdict bad">${tr('error')}</p><pre class="out">${esc(result?.error||'')}${result?.trace?'\n\n'+esc(result.trace):''}</pre>`;
    }else{
      const tests=Array.isArray(result.tests)?result.tests:[],all=tests.length>0&&tests.every(t=>t.ok);
      box.innerHTML=`<p class="verdict ${all?'ok':'bad'}">${all?'✓ '+tr('pass'):tr('fail')} (${tests.filter(t=>t.ok).length}/${tests.length})</p>
        <div class="tablewrap"><table><thead><tr><th>${tr('test')}</th><th>${tr('result')}</th><th>${tr('got')}</th><th>${tr('want')}</th></tr></thead><tbody>${tests.map(t=>`<tr><td>${esc(t.name)}${t.note?`<br><small>${esc(t.note)}</small>`:''}</td><td class="${t.ok?'ok':'bad'}">${t.ok?tr('ok'):tr('bad')}</td><td class="num">${fmt(t.got)}</td><td class="num">${fmt(t.want)}</td></tr>`).join('')}</tbody></table></div>`;
      if(all){const s=solved();s.add(p.id);store.set('solved',JSON.stringify([...s]));paintList();}
      if(result.plot)plot(result.plot);
    }
    if(stdout&&stdout.trim()){$('out').hidden=false;$('out').textContent=tr('stdout')+':\n'+stdout.slice(0,20000);}
    reportHeight();
  }
  function plot(spec){
    const series=(spec.series||[]).filter(s=>Array.isArray(s.x)&&Array.isArray(s.y)&&s.x.length);
    if(!series.length)return;
    $('plotbox').hidden=false;
    const cv=$('plot'),dpr=Math.min(devicePixelRatio||1,2),w=cv.clientWidth||600,h=cv.clientHeight||300;
    cv.width=w*dpr;cv.height=h*dpr;const g=cv.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,w,h);
    const css=getComputedStyle(document.documentElement),col=k=>css.getPropertyValue(k).trim();
    const colors=[col('--s1'),col('--s2'),col('--s3')];
    const fin=v=>Number.isFinite(v);
    let xs=series.flatMap(s=>s.x.filter(fin)),ys=series.flatMap(s=>s.y.filter(fin));
    if(!xs.length||!ys.length)return;
    let x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);
    if(x1===x0){x0-=1;x1+=1;}if(y1===y0){y0-=1;y1+=1;}
    const m={l:64,r:12,t:12,b:36},pw=w-m.l-m.r,ph=h-m.t-m.b;
    if(spec.aspect==='equal'){const sx=(x1-x0)/pw,sy=(y1-y0)/ph,s=Math.max(sx,sy),cx=(x0+x1)/2,cy=(y0+y1)/2;x0=cx-s*pw/2;x1=cx+s*pw/2;y0=cy-s*ph/2;y1=cy+s*ph/2;}
    const X=v=>m.l+(v-x0)/(x1-x0)*pw,Y=v=>m.t+(1-(v-y0)/(y1-y0))*ph;
    g.strokeStyle=col('--line');g.fillStyle=col('--muted');g.lineWidth=1;g.font='11px system-ui,sans-serif';
    g.strokeRect(m.l,m.t,pw,ph);
    const tick=v=>{if(Math.abs(v)<Math.max(Math.abs(x1-x0),Math.abs(y1-y0))*1e-9)v=0;return Math.abs(v)>=1e4||Math.abs(v)<1e-2&&v!==0?v.toExponential(1):String(+v.toPrecision(3));};
    for(let i=0;i<=4;i++){
      const xv=x0+(x1-x0)*i/4,yv=y0+(y1-y0)*i/4;
      g.textAlign='center';g.fillText(tick(xv),X(xv),h-m.b+14);
      g.textAlign='right';g.fillText(tick(yv),m.l-6,Y(yv)+4);
    }
    g.textAlign='center';g.fillText(spec.xlabel||'',m.l+pw/2,h-4);
    g.save();g.translate(12,m.t+ph/2);g.rotate(-Math.PI/2);g.fillText(spec.ylabel||'',0,0);g.restore();
    series.forEach((s,i)=>{
      g.strokeStyle=colors[i%colors.length];g.lineWidth=i?1.5:2;g.setLineDash(i?[5,4]:[]);g.beginPath();let pen=false;
      for(let k=0;k<Math.min(s.x.length,s.y.length);k++){const a=s.x[k],b=s.y[k];if(!fin(a)||!fin(b)){pen=false;continue;}pen?g.lineTo(X(a),Y(b)):g.moveTo(X(a),Y(b));pen=true;}
      g.stroke();
    });
    g.setLineDash([]);
    $('legend').innerHTML=series.map((s,i)=>`<span><i style="background:${colors[i%colors.length]}"></i>${esc(s.label||'')}</span>`).join('');
    cv.setAttribute('aria-label',(spec.ylabel||'')+' vs '+(spec.xlabel||''));
  }

  $('plist').addEventListener('click',e=>{const b=e.target.closest('button[data-id]');if(b)select(b.dataset.id);});
  $('run').addEventListener('click',run);
  $('stop').addEventListener('click',()=>stopWorker(tr('stopped')));
  $('reset').addEventListener('click',()=>{if(confirm(tr('confirmReset'))){$('code').value=state.current.starter;store.set('code:'+state.current.id,state.current.starter);}});
  $('code').addEventListener('keydown',e=>{
    if(e.key==='Tab'&&!e.shiftKey&&!e.altKey&&!e.ctrlKey&&!e.metaKey){e.preventDefault();const t=e.target,s=t.selectionStart;t.setRangeText('    ',s,t.selectionEnd,'end');}
    if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();if(!$('run').disabled)run();}
  });
  let saveTimer=0;$('code').addEventListener('input',()=>{clearTimeout(saveTimer);saveTimer=setTimeout(()=>store.set('code:'+state.current.id,$('code').value),400);});
  window.addEventListener('message',event=>{
    if(!embedded||event.origin!==location.origin||event.source!==window.parent||event.data?.type!=='hl-compute-settings')return;
    if(['ko','en'].includes(event.data.lang)&&event.data.lang!==state.lang){state.lang=event.data.lang;translate();select(state.current.id,{push:false});}
    if(['light','dark'].includes(event.data.theme)){document.documentElement.dataset.theme=event.data.theme;}
  });
  if(typeof ResizeObserver==='function')new ResizeObserver(reportHeight).observe(document.body);
  document.documentElement.classList.toggle('embedded',embedded);
  applyTheme();translate();
  const start=()=>select(params.get('problem')||C.PROBLEMS[0].id,{push:false});
  /* KaTeX loads with defer just before this script; render once it is there */
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
