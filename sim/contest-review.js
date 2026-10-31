/* KMO written-answer review. Reuses the signed-in lab account, scan service and token ledger. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.ContestReview=api;
})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  const Network=typeof module==='object'&&module.exports?require('./exam-network.js'):window.HLExamNetwork;
  const DEFAULT_API='https://haslalab-community-edge.haslalab.workers.dev';
  const apiBase=value=>{const base=String(value||DEFAULT_API).replace(/\/+$/,'');return base==='https://haslalab-community.haslalab.workers.dev'?DEFAULT_API:base;};
  const PDFJS='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/';
  const MAX_IMAGE=1850000,MAX_PAGES=40;
  const PROVIDERS=['deepseek','gemini'];
  const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function sessionId(value){const n=Number(value);if(!Number.isSafeInteger(n)||n<=0)throw{code:'bad_session'};return n;}
  function taskNumbers(entry){return Array.from({length:entry.questions},(_,i)=>i+1+(Number.isInteger(entry.questionOffset)?entry.questionOffset:0));}
  function mapAnswers(entry,answers){
    const out={};
    for(const [i,n]of taskNumbers(entry).entries()){
      const v=answers&&answers[i+1];
      if(typeof v==='string'&&v.trim())out[n]=v.slice(0,50000);
    }
    return out;
  }
  function storageKey(entry,runId){return 'hlContestReview:'+entry.id+':'+String(runId||'latest');}
  function uploadWarning(page,lang='ko'){
    if(page?.ocr_status!=='failed')return '';
    const message=Network.ocrErrorMessage?.(page.ocr_error||page.read?.ocr?.error,lang);
    return message?(lang!=='en'?'사진은 보관했습니다. ':'The photo was saved. ')+message:lang!=='en'?'사진은 보관했지만 글자를 읽지 못했습니다. 판독 실패가 계속되면 운영자에게 알려 주세요.':'The photo was saved, but its text could not be read. Contact the operator if reading keeps failing.';
  }
  function createClient({fetch:fetcher,getToken,getBase}={}){
    const base=()=>apiBase(getBase?getBase():DEFAULT_API);
    const transport=Network.createTransport({fetch:fetcher,getToken,getBase:base}),request=transport.request;
    return {
      request,fingerprint:transport.fingerprint,
      bootstrap:()=>request('GET','/lab/bootstrap'),
      active:()=>request('GET','/lab/active'),
      get:id=>request('GET','/lab/sessions/'+sessionId(id)),
      start:body=>request('POST','/lab/contest/start',{...body,purpose:'review'}),
      text:(id,answers)=>request('POST','/lab/contest/sessions/'+sessionId(id)+'/text',{answers}),
      pay:(id,maxCost,provider)=>request('POST','/lab/sessions/'+sessionId(id)+'/pay',{...(maxCost==null?{}:{max_cost:maxCost}),...(provider?{provider}:{})}),
      read:(id,provider)=>request('POST','/lab/contest/sessions/'+sessionId(id)+'/read',provider?{provider}:{}),
      confirm:(id,pid,text,task)=>request('POST','/lab/contest/sessions/'+sessionId(id)+'/pages/'+sessionId(pid)+'/confirm',{text,task}),
      confirmAll:(id,pages)=>request('POST','/lab/contest/sessions/'+sessionId(id)+'/confirm',{pages}),
      submit:(id,maxCost,provider)=>request('POST','/lab/sessions/'+sessionId(id)+'/submit',{grade:true,...(maxCost==null?{}:{max_cost:maxCost}),...(provider?{provider}:{})}),
      qr:id=>request('POST','/lab/sessions/'+sessionId(id)+'/qr',{}),
      upload:(code,task,blob)=>request('PUT','/lab/up/pages?task='+encodeURIComponent(task)+'&kind=answer',blob,{binary:true,headers:{'X-Lab-Token':code,'Content-Type':blob.type||'image/jpeg'}}),
      remove:(id,pid)=>request('DELETE','/lab/sessions/'+sessionId(id)+'/pages/'+sessionId(pid)),
      classify:(id,pid,task,kind)=>request('PATCH','/lab/sessions/'+sessionId(id)+'/pages/'+sessionId(pid),{task,kind}),
      imageURL:pid=>base()+'/api/lab/pages/'+sessionId(pid)+'/img'
    };
  }
  let pdfPromise=null,qrPromise=null;
  function pdfLibrary(){
    if(window.pdfjsLib){window.pdfjsLib.GlobalWorkerOptions.workerSrc=PDFJS+'pdf.worker.min.js';return Promise.resolve(window.pdfjsLib);}
    return pdfPromise||(pdfPromise=new Promise((resolve,reject)=>{
      const s=document.createElement('script');s.src=PDFJS+'pdf.min.js';
      s.onload=()=>{if(!window.pdfjsLib){pdfPromise=null;reject({code:'pdf_unavailable'});return;}window.pdfjsLib.GlobalWorkerOptions.workerSrc=PDFJS+'pdf.worker.min.js';resolve(window.pdfjsLib);};
      s.onerror=()=>{pdfPromise=null;reject({code:'pdf_unavailable'});};document.head.append(s);
    }));
  }
  function qrLibrary(){
    if(typeof window.qrcode==='function')return Promise.resolve(window.qrcode);
    return qrPromise||(qrPromise=new Promise(resolve=>{const s=document.createElement('script');s.src='../vendor/qrcode/qrcode.js';s.onload=()=>resolve(window.qrcode||null);s.onerror=()=>{qrPromise=null;resolve(null);};document.head.append(s);}));
  }
  let scannerPromise;
  const scannerLibrary=()=>scannerPromise||(scannerPromise=import('./labscan/scanner.js?v=bc509c5941c5').catch(error=>{scannerPromise=null;throw error;}));
  async function imageBlob(file){return(await scannerLibrary()).encodeUpload(file,{maxBytes:MAX_IMAGE});}
  async function filePages(file,remaining){
    if(!file||file.size>30*1024*1024)throw{code:'file_too_big'};
    if(file.type==='application/pdf'||/\.pdf$/i.test(file.name)){
      const lib=await pdfLibrary(),doc=await lib.getDocument({data:new Uint8Array(await file.arrayBuffer())}).promise;
      try{
        if(doc.numPages>remaining)throw{code:'too_many_pages'};
        const pages=[];
        for(let n=1;n<=doc.numPages;n++){
          const page=await doc.getPage(n),v=page.getViewport({scale:1}),scale=Math.min(200/72,2400/Math.max(v.width,v.height)),vp=page.getViewport({scale});
          const canvas=document.createElement('canvas');canvas.width=Math.ceil(vp.width);canvas.height=Math.ceil(vp.height);
          await page.render({canvasContext:canvas.getContext('2d'),viewport:vp,background:'white'}).promise;
          const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
          pages.push({blob:await imageBlob(blob),name:file.name+' · '+n});
        }
        return pages;
      }finally{await doc.destroy();}
    }
    if(!/^image\/(jpeg|png|webp)$/.test(file.type))throw{code:'bad_image'};
    const scanner=await scannerLibrary();let scan=null,failed=false;
    if(scanner.canProcess())try{scan=await scanner.processShot(file,{mode:'color'});}catch(_){failed=true;}
    return [{blob:await imageBlob(scan?.blob||file),name:file.name,source:file,scan,mode:'color',processingFailed:failed}];
  }
  function mount(host,entry,options={}){
    if(!host||!entry||entry.comp!=='kmo'||entry.kind!=='proof')return{dispose(){},refresh:async()=>null,getSession:()=>null};
    const ko=options.lang!=='en',tr=(a,b)=>ko?a:b,local=v=>v&&typeof v==='object'?v[ko?'ko':'en']||v.ko||v.en||'':v||'';
    let storage=options.storage;
    if(!storage)try{storage=localStorage;}catch(_){}
    storage=storage||{getItem:()=>null,setItem(){},removeItem(){}};
    const read=(k,fallback)=>{try{return JSON.parse(storage.getItem(k)||'null')||fallback;}catch(_){return fallback;}};
    const write=(k,value)=>{try{storage.setItem(k,JSON.stringify(value));}catch(_){}};
    const getToken=()=>{try{return storage.getItem('hlCmTok')||'';}catch(_){return '';}};
    const getBase=()=>{try{return apiBase(storage.getItem('hlCmApi'));}catch(_){return DEFAULT_API;}};
    const client=createClient({fetch:options.fetch,getToken,getBase});
    const key=storageKey(entry,options.runId),numbers=taskNumbers(entry),answers=mapAnswers(entry,options.answers||options.localAnswers||{}),tasks=numbers.map(n=>'Q'+n);
    let alive=true,session=options.session||null,contest=options.contest||null,tokens=null,busy='',error='',approved=false,uploadCode=options.token||'',queue=[],poller=null,clock=null,qrUrl='',revision=0,skew=0,needsLogin=false;
    const fee=()=>Number.isFinite(session?.cost)?session.cost:0.3;
    const dirty=new Map(),thumbs=new Map(),thumbPending=new Map(),queueDialogs=new Set();
    let cornerAbort=null;
    let refreshPromise=null,refreshKey='',revisionEpoch=0,identity=client.fingerprint(),actionIdentity=null,provider=PROVIDERS.includes(session?.provider)?session.provider:'gemini',vision=null;
    const choices=()=>PROVIDERS.map(id=>({id,available:vision?.providers?vision.providers.some(row=>row.id===id&&row.available===true):id==='gemini'}));
    const available=()=>choices().some(row=>row.id===provider&&row.available);
    const locked=()=>!!(session?.provider_locked||session?.paid);
    function providerHTML(){return `<label class="cr-small">${tr('OCR·채점·피드백','OCR, grading and feedback')}<select data-cr-provider aria-label="${tr('채점 제공자','Grading provider')}" ${busy||locked()?'disabled':''}>${choices().map(row=>`<option value="${row.id}" ${row.id===provider?'selected':''} ${row.available?'':'disabled'}>${row.id}</option>`).join('')}</select></label>`;}
    function bindProvider(){const field=$('[data-cr-provider]');if(!field)return;field.value=provider;field.disabled=!!busy||locked();field.onchange=()=>{if(!alive||client.fingerprint()!==identity){accountChanged();return;}if(busy||locked()||!choices().some(row=>row.id===field.value&&row.available)){field.value=provider;return;}provider=field.value;approved=false;};}
    function $(s){return host.querySelector(s);}
    function saved(){return read(key,null);}
    function remember(){if(session)write(key,{id:session.id,examId:entry.id,mode:options.mode||'paper'});if(session&&uploadCode)try{storage.setItem('hlExamUp:'+session.id,uploadCode);}catch(_){}}
    function use(response,scope=actionIdentity){if(scope&&(!alive||client.fingerprint()!==scope))throw{code:'stale_account'};vision=response?.vision||response?.health?.vision||response?.health?.arena?.vision||response?.contest?.vision||vision;if(response?.session){if(response.session.examId!==entry.id)throw{code:'bad_exam'};sessionId(response.session.id);const before=Network.sessionSignature(session);session=response.session;if(PROVIDERS.includes(session.provider))provider=session.provider;if(before!==Network.sessionSignature(session))approved=false;if(Number.isFinite(session.now))skew=session.now-Date.now()/1000;}if(response?.contest)contest=response.contest;if(response?.token)uploadCode=response.token;if(Number.isFinite(response?.tokens)){tokens=response.tokens;if(options.onTokens)options.onTokens(tokens);}remember();if(options.onSession&&session)options.onSession(session);}
    const providerError=e=>({provider_required:tr('채점 제공자를 선택하세요.','Choose a grading provider.'),provider_unavailable:tr('선택한 제공자를 사용할 수 없습니다. 사용 가능한 항목을 선택하세요.','This provider is unavailable. Choose an available option.'),provider_locked:tr('판독·채점을 시작한 뒤에는 제공자를 바꿀 수 없습니다.','The provider is fixed after reading or grading starts.')})[e?.code];
    const reason=e=>providerError(e)||Network.ocrErrorMessage?.(e?.code,ko?"ko":"en")||({price_changed:tr('채점 비용이 갱신되었습니다. 새 비용을 확인한 뒤 다시 신청해 주세요.','The fee changed. Check the updated fee and request review again.'),network:tr('서버에 연결하지 못했습니다. 다시 시도하세요.','Connection failed. Please retry.'),login_required:tr('채점을 접수하려면 로그인하세요.','Sign in to request review.'),no_tokens:tr('실전 토큰이 부족합니다. 토큰을 충전한 뒤 다시 요청하세요.','You need an exam token before requesting review.'),closed:tr('답안 제출 시간이 끝났습니다. 이미 접수한 답안과 기록은 내 시험에서 확인하세요.','The answer submission window has closed. See your submitted record under My exams.'),other_active:tr('다른 시험의 제출 접수가 열려 있습니다. 해당 시험을 먼저 마무리하세요.','Another exam submission is open. Finish it first.'),not_found:tr('이 채점 접수를 찾지 못했습니다. 로그인 계정과 서버 상태를 확인하세요.','This review could not be found. Check your account and server.'),bad_exam:tr('이 시험은 아직 서버의 서술형 채점 목록에 없습니다.','This exam is not in the written-review catalogue yet.'),too_many_pages:tr('한 접수에 최대 40쪽을 보낼 수 있습니다.','A review accepts at most 40 pages.'),bad_image:tr('사진 또는 PDF 파일을 선택하세요.','Choose an image or PDF.'),image_too_big:tr('작은 글씨를 보존하는 화질로는 용량이 너무 큽니다. 흑백 모드로 바꾸거나 종이가 화면을 채우게 다시 촬영하세요.','This image is too large at a readable resolution. Try B&W or retake with the page filling the frame.'),file_too_big:tr('파일 하나는 30 MB 이하여야 합니다.','Each file must be 30 MB or smaller.'),pdf_unavailable:tr('PDF 리더를 불러오지 못했습니다. 사진으로 보내거나 다시 시도하세요.','The PDF reader could not load. Try again or use image files.'),empty_answers:tr('제출할 풀이가 없습니다. 답안 사진 또는 작성한 풀이를 먼저 보내세요.','Add scanned pages or your written answers first.'),unconfirmed_pages:tr('스캔 원문과 읽힌 풀이를 대조하고 확인을 마쳐 주세요.','Check the scans against the recognized answers first.')})[({needs_confirmation:'unconfirmed_pages',no_answers:'empty_answers'})[e?.code]||e?.code]||tr('요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요.','The request could not be completed. Please retry.');
    function stateLabel(state){return({scanning:tr('답안 제출 준비','Prepare answers'),running:tr('시험 진행 중','Exam running'),grading:tr('검토 중','Under review'),graded:tr('검토 완료','Review complete'),pending:tr('관리자 검토 대기','Waiting for manual review'),error:tr('검토 오류 · 관리자 확인 필요','Review error · awaiting staff'),ended:tr('채점 미신청','Review not requested'),empty:tr('제출 답안 없음','No answers submitted')})[state]||escape(state||'');}
    function rememberLogin(){try{sessionStorage.setItem('hlCmBack','#/kmo/exam');sessionStorage.setItem('hlContestReviewBack',location.href);}catch(_){}}
    function scanURL(){const u=new URL('scan.html',location.href),hash=new URLSearchParams({c:uploadCode,l:ko?'ko':'en'});if(getBase().replace(/\/+$/,'')!==DEFAULT_API)hash.set('a',getBase());u.hash=hash.toString();return u.href;}
    const authError=e=>e?.code==='login_required'||e?.status===401;
    async function act(label,fn){if(busy||!alive)return;if(client.fingerprint()!==identity){accountChanged();return;}const account=client.fingerprint();actionIdentity=account;revisionEpoch++;busy=label;error='';render();try{await fn();}catch(e){if(!alive||client.fingerprint()!==account)return;error=reason(e);if(e?.code==='price_changed'&&session&&Number.isFinite(e.cost)){session={...session,cost:e.cost,price_estimate:true};approved=false;if(Number.isFinite(e.tokens))tokens=e.tokens;}if(authError(e)){tokens=null;needsLogin=true;}}finally{actionIdentity=null;busy='';if(alive)render();}}
    function refresh(silent=false){
      if(!alive||!getToken())return;
      const account=client.fingerprint(),epoch=revisionEpoch,id=session?.id,key=account+'\n'+epoch+'\n'+(id||'');
      if(refreshPromise&&refreshKey===key)return refreshPromise;
      refreshKey=key;
      const promise=(async()=>{try{
        const r=id?await client.get(id):await client.bootstrap();
        if(!alive||client.fingerprint()!==account||revisionEpoch!==epoch||session?.id!==id)return;
        if(id)use(r,null);else{vision=r.vision||r.health?.vision||r.health?.arena?.vision||vision;if(Number.isFinite(r.tokens))tokens=r.tokens;}
        if(!silent)render();
      }catch(e){if(!alive||client.fingerprint()!==account||revisionEpoch!==epoch)return;if(authError(e)){tokens=null;needsLogin=true;}if(!silent||needsLogin){error=reason(e);render();}}})();
      refreshPromise=promise;promise.finally(()=>{if(refreshPromise===promise)refreshPromise=null;});return promise;
    }
    function stopTimers(){poller?.stop();if(clock)clearInterval(clock);clock=null;}
    function startTimers(){
      stopTimers();
      if(!session)return;
      if(!poller)poller=Network.createPoll({document:typeof document==='object'?document:null,active:()=>alive&&!busy&&!needsLogin&&!!getToken()&&['running','scanning','grading'].includes(session?.status),task:async()=>{const prior=Network.sessionSignature(session);await refresh(true);const changed=prior!==Network.sessionSignature(session);if(alive&&changed){poller?.reset();render();}return changed;}});
      if(['running','scanning','grading'].includes(session.status))poller.start();
      if(session.status==='scanning'){clock=setInterval(paintClock,1000);paintClock();}
    }
    function paintClock(){const el=$('[data-cr-clock]');if(!el||!session)return;const remain=Math.max(0,Math.floor((session.scan_until||0)-(Date.now()/1000+skew)));el.textContent=remain?Math.floor(remain/60)+':'+String(remain%60).padStart(2,'0'):tr('제출 창 종료','Submission closed');}
    function header(){return `<div class="cr-head"><div><span class="cr-eyebrow">${tr('KMO 서술형 채점 · 실전 토큰 0.3개','KMO written review · 0.3 exam token')}</span><h2>${tr('손글씨 풀이 또는 화면 풀이 채점','Review handwritten or typed solutions')}</h2></div>${tokens!==null?`<span class="cr-balance">${tr('보유 토큰','Tokens')}: <b>${escape(tokens)}</b></span>`:''}</div><p class="cr-note">${tr('AI 학습용 검토와 참고점수입니다. 공식 대회 채점·공식 해설을 대신하지 않으며, 판단이 불확실한 답안은 관리자 검토를 기다립니다.','This is an AI learning review with reference scores, not official contest marking or an official solution. Uncertain answers await manual review.')}</p>`;}
    function render(){
      if(!alive)return;revision++;stopTimers();host.classList.add('contest-review');
      const prefix=header()+(getToken()&&!needsLogin?providerHTML():'')+`${error?`<p class="cr-alert" role="alert">${escape(error)}</p>`:''}${busy?`<p class="cr-progress" role="status">${escape(busy)}</p>`:''}`;
      try{
      if(!getToken()||needsLogin){
        host.innerHTML=prefix+`<p>${tr('무료 응시 기록은 그대로 유지됩니다. 채점을 접수하려면 HaslaLab 계정으로 로그인하세요.','Your free attempt stays saved. Sign in to your HaslaLab account to request review.')}</p><a class="cr-button" data-cr-login href="../#/community/login">${tr('로그인하고 채점 접수','Sign in for review')}</a>`;$('[data-cr-login]').onclick=rememberLogin;return;
      }
      if(!session){
        host.innerHTML=prefix+`<p>${tr('시험은 이미 종료됐습니다. 아래 버튼은 채점용 답안을 보내는 접수 창을 열며, 토큰을 차감하지 않습니다. 접수 후 30분은 스캔·전송 시간이며 추가 풀이 시간이 아닙니다.','Your exam has ended. Open an answer-submission window below without spending a token. Its 30 minutes are for scanning and transmission, not additional solving time.')}</p><button class="primary" data-cr-start ${busy?'disabled':''}>${tr('채점용 답안 제출 준비','Prepare answers for review')}</button><p class="cr-small">${tr('사진·PDF 또는 화면 풀이를 서버로 보낼 때 해당 자료가 계정의 채점 접수에 저장됩니다. 토큰은 별도의 ‘0.3토큰으로 검토 시작’ 버튼을 누를 때만 사용합니다.','Scans, PDFs and typed answers sent here are stored with your account review. A token is used only when you select “Start review for 0.3 token”.')}</p>`;
        $('[data-cr-start]').onclick=()=>act(tr('제출 접수를 여는 중…','Opening submission…'),async()=>{if(!available())throw{code:'provider_unavailable'};use(await client.start({provider,examId:entry.id,lang:ko?'ko':'en',entry:options.entry||'?id='+encodeURIComponent(entry.id),mode:options.mode==='paper'?'paper':'online',purpose:'review',runId:String(options.runId||'')}));if(!uploadCode&&session)use(await client.qr(session.id));});return;
      }
      if(!session.status){host.innerHTML=prefix+`<p>${tr('저장된 채점 접수 정보를 확인하고 있습니다.','Loading the saved review record.')}</p><button data-cr-refresh>${tr('다시 확인','Retry')}</button> <button data-cr-reset>${tr('이 기기의 접수 연결만 해제','Unlink saved review on this device')}</button>`;$('[data-cr-refresh]').onclick=()=>refresh();$('[data-cr-reset]').onclick=()=>{try{storage.removeItem(key);}catch(_){}session=null;error='';render();};return;}
      if(session.pages===null||session.pages===undefined)session.pages=[];
      if(!['scanning','running'].includes(session.status)){host.innerHTML=prefix+resultHTML();bindResult();startTimers();return;}
      if(session.status==='running'){host.innerHTML=prefix+`<p>${tr('서버의 시험이 아직 진행 중입니다. 종료 후 제출할 수 있습니다.','The server exam is still running. Submit answers after it ends.')}</p><button data-cr-refresh>${tr('상태 다시 확인','Refresh status')}</button>`;$('[data-cr-refresh]').onclick=()=>refresh();startTimers();return;}
      const pages=session.pages||[],paid=!!session.paid,reading=pages.some(Network.reading);
      host.innerHTML=prefix+`<div class="cr-status"><b>${stateLabel(session.status)}</b><span>${tr('스캔·전송 마감까지','Scan/upload window')}: <strong data-cr-clock></strong></span><span>${tr('접수 번호','Review')}: ${session.id}</span></div>`+
        `${reading?`<p class="cr-progress" role="status">${tr('답안 판독을 진행 중입니다. 다른 화면으로 이동해도 계속 처리합니다.','Your pages are being read. Processing continues if you leave this screen.')}</p>`:''}${paid?`<p class="cr-paid">${tr(`${fee()}토큰 사용 완료 · 같은 접수의 최종 제출에 다시 차감하지 않습니다.`,`${fee()} token used. Final submission of this review does not charge again.`)}</p>`:''}`+
        `${Object.keys(answers).length?onlineHTML():''}<div class="cr-columns"><section><h3>${tr('스캔 파일 보내기','Send scanned pages')}</h3><p class="cr-small">${tr('사진 또는 PDF를 선택한 뒤 문항을 지정하세요. ‘서버로 보내기’를 누르기 전에는 파일이 전송되지 않습니다. 한 접수에 최대 40쪽입니다.','Choose images or a PDF and assign each page to a question. Files are not transmitted until you select Send to server. Maximum 40 pages.')}</p><label class="cr-file">${tr('사진·PDF 선택','Choose images / PDF')}<input data-cr-files type="file" accept="image/*,application/pdf,.pdf" multiple ${busy?'disabled':''}></label><div data-cr-queue>${queueHTML()}</div></section><section class="cr-mobile"><h3>${tr('휴대전화로 스캔','Scan with your phone')}</h3><div data-cr-qr></div><p class="cr-small">${tr('기존 답안 스캐너를 엽니다. 종이 네 귀퉁이가 모두 보이게 찍고 원근 보정 후 전송하세요.','Open the existing answer scanner. Photograph all four corners, check the perspective correction, then send.')}</p><button data-cr-newqr ${busy?'disabled':''}>${tr('스캔 링크 새로 만들기','Renew scan link')}</button></section></div><section class="cr-pages"><h3>${tr('서버에 보낸 답안','Submitted pages')} · ${pages.length}</h3>${pagesHTML(pages)}</section>`+
        `<div class="cr-actions">${!paid?`<button class="primary" data-cr-pay ${busy||!pages.length?'disabled':''}>${tr('0.3토큰으로 검토 시작','Start review for 0.3 token')}</button><p class="cr-small">${tr('이 버튼을 누르면 0.3토큰을 사용하고, 스캔한 풀이를 읽습니다. 읽힌 수식을 원문과 대조한 뒤 최종 제출하세요.','This uses 0.3 token and reads your scanned work. Check recognized formulas against the originals before final submission.')}</p>`:`<button data-cr-read ${busy||reading||!pages.length?'disabled':''}>${tr('새 답안 읽기 / 다시 확인','Read new pages / refresh')}</button><label class="cr-check"><input data-cr-approved type="checkbox" ${reading?'disabled':''} ${approved?'checked':''}>${tr('원본 답안과 읽힌 수식·문항 분류를 대조했고, OCR 오독만 정정했습니다.','I checked question labels and recognized formulas against the originals and corrected only OCR errors.')}</label><button class="primary" data-cr-submit ${busy||reading||!approved||!pages.length?'disabled':''}>${tr('확인한 답안 최종 제출','Submit checked answers')}</button>`}<a href="../#/lab/${session.id}">${tr('내 채점 접수 기록','My review record')}</a></div>`;
      bindOnline();bindQueue();bindScanQueue();bindPages();
      $('[data-cr-files]').onchange=e=>{const files=Array.from(e.target.files||[]);e.target.value='';if(files.length)act(tr('스캔 파일을 준비하는 중…','Preparing scanned files…'),()=>prepareFiles(files));};
      $('[data-cr-newqr]').onclick=()=>act(tr('스캔 링크를 갱신하는 중…','Renewing scan link…'),async()=>{use(await client.qr(session.id));});
      if($('[data-cr-pay]'))$('[data-cr-pay]').onclick=()=>pay();
      if($('[data-cr-read]'))$('[data-cr-read]').onclick=()=>act(tr('답안을 읽는 중…','Reading answers…'),async()=>{if(!available())throw{code:'provider_unavailable'};use(await client.read(session.id,provider));approved=false;});
      if($('[data-cr-approved]'))$('[data-cr-approved]').onchange=e=>{approved=e.target.checked;const button=$('[data-cr-submit]');if(button)button.disabled=busy||reading||!approved||!pages.length;};
      if($('[data-cr-submit]'))$('[data-cr-submit]').onclick=()=>submit();
      paintQR();paintThumbs(pages);startTimers();
      }finally{bindProvider();}
    }
    function onlineHTML(){return `<details class="cr-online"><summary>${tr('화면에 작성한 풀이 보내기','Send answers typed on screen')} · ${Object.keys(answers).length} ${tr('문항','questions')}</summary><p class="cr-small">${tr('시험 종료 때 확정된 풀이입니다. 서버로 보내기 전 내용을 확인하세요.','These answers were locked at the end of your attempt. Check them before sending.')}</p>${Object.entries(answers).map(([n,text])=>`<article><h4>${n}. ${tr('문항','Question')}</h4><pre>${escape(text)}</pre></article>`).join('')}<button data-cr-text ${busy||session.paid?'disabled':''}>${tr('이 풀이를 서버로 보내기','Send these answers to server')}</button></details>`;}
    function bindOnline(){if($('[data-cr-text]'))$('[data-cr-text]').onclick=()=>act(tr('화면 풀이를 저장하는 중…','Saving typed answers…'),async()=>{use(await client.text(session.id,answers));approved=false;});}
    function taskOptions(selected){return tasks.map(t=>`<option value="${t}" ${selected===t?'selected':''}>${t.replace('Q','')} ${tr('번','')}</option>`).join('');}
    function queueHTML(){return queue.length?`<ul class="cr-queue">${queue.map((p,i)=>`<li><img src="${escape(p.url)}" alt="${escape(p.name)}"><div><b>${escape(p.name)}</b><label>${tr('문항','Question')} <select data-cr-qtask="${i}" ${busy?'disabled':''}>${taskOptions(p.task)}</select></label>${p.processingFailed?`<p class="cr-small">${tr('자동 보정 실패 · 원본을 확인하거나 다시 선택하세요.','Automatic correction failed. Check the original or choose another photo.')}</p>`:p.scan&&(p.scan.warpApplied??p.scan.a4WarpApplied)===false?`<p class="cr-small">${tr('종이 모서리를 확인하지 못해 원본을 유지합니다. 모서리를 직접 확인한 뒤 보정하세요.','The paper corners are unconfirmed. The original image is retained. Confirm its corners to straighten it.')}</p>`:p.scan&&(p.scan.cornersReliable===false||p.scan.autoScore<.75)?`<p class="cr-small">${tr('모서리를 확인하고 필요하면 직접 맞춰 주세요.','Check the corners and adjust them if needed.')}</p>`:''}${p.scan?.quality&&!p.scan.quality.ok?`<p class="cr-small">${tr('사진이 흐립니다. 작은 글씨를 확인하고 필요하면 다시 촬영하세요.','The photo is blurry. Check small writing and retake if needed.')}</p>`:''}<div><button data-cr-qzoom="${i}" ${busy?'disabled':''}>${tr('크게 보기','Enlarge')}</button>${p.source?` <button data-cr-qsource="${i}" ${busy?'disabled':''}>${tr('촬영 원본','Original photo')}</button>`:''}${p.scan?.baseUrl?` <button data-cr-qedit="${i}" ${busy?'disabled':''}>${tr('모서리 맞추기','Fix corners')}</button><div>${[['color',tr('컬러 스캔','Color scan')],['clean',tr('또렷하게','Clean')],['mono',tr('흑백','B&W')],['original',tr('원본 색상','Original colour')]].map(([mode,label])=>`<button data-cr-qmode="${i}" data-mode="${mode}" aria-pressed="${p.mode===mode}" ${busy?'disabled':''}>${label}</button>`).join(' ')} <button data-cr-qrotate="${i}" ${busy?'disabled':''}>90° ↻</button></div>`:''}</div><button data-cr-qremove="${i}" ${busy?'disabled':''}>${tr('선택 취소','Remove')}</button></div></li>`).join('')}</ul><button data-cr-upload ${busy?'disabled':''}>${tr('선택한 '+queue.length+'쪽을 서버로 보내기','Send '+queue.length+' selected pages to server')}</button>`:'';}
    function inspectQueue(p,original){
      const dialog=document.createElement('dialog'),url=original?URL.createObjectURL(p.source):p.url;
      dialog.style.cssText='width:95vw;max-width:1100px;max-height:94vh;overflow:auto;padding:15px';
      const close=document.createElement('button'),img=document.createElement('img');close.textContent=tr('닫기','Close');img.src=url;img.alt=original?tr('촬영 원본','Original photo'):tr('보낼 답안','Answer page to upload');img.style.cssText='display:block;max-width:100%;height:auto;margin-top:12px;cursor:zoom-in';
      img.onclick=()=>{const zoom=img.style.maxWidth==='none';img.style.maxWidth=zoom?'100%':'none';img.style.cursor=zoom?'zoom-in':'zoom-out';};
      dialog.append(close,img);document.body.append(dialog);queueDialogs.add(dialog);close.onclick=()=>dialog.close();dialog.onclose=()=>{if(original)URL.revokeObjectURL(url);queueDialogs.delete(dialog);dialog.remove();};dialog.showModal();
    }
    function clearQueuedImages(){cornerAbort?.abort();cornerAbort=null;for(const dialog of queueDialogs){dialog.close();dialog.remove();}queueDialogs.clear();for(const p of queue)URL.revokeObjectURL(p.url);queue=[];}
    async function rebuildQueue(p,change={}){
      const account=client.fingerprint();
      const scanner=await scannerLibrary();let scan=p.scan,source=p.source,mode=change.mode||p.mode;
      if(change.rotate){source=await scanner.rotatePhoto(source);scan=await scanner.processShot(source,{mode});}
      else {const marker=change.marker??scan.method==='marker',corners=change.corners||scan.corners,pageFormat=change.pageFormat||scan.outputFormat||'auto';scan={...scan,...await scanner.reprocess(scan.baseUrl,corners,mode,undefined,marker?scanner.MARKER_INSET:null,{preserveOriginal:(scan.warpApplied??scan.a4WarpApplied)===false&&!change.corners,pageFormat,source:scan.sourceBlob}),corners,method:change.corners?(marker?'marker':'manual'):scan.method,autoScore:change.corners?1:scan.autoScore,...(change.corners?{cornersReliable:true,paperStatus:pageFormat==='a4'?'manual_a4':'manual',warpApplied:true,a4WarpApplied:pageFormat==='a4',outputFormat:pageFormat}:{})};}
      const blob=await scanner.encodeUpload(scan.blob,{maxBytes:MAX_IMAGE});
      if(!alive||client.fingerprint()!==account||!queue.includes(p))return;
      URL.revokeObjectURL(p.url);Object.assign(p,{blob,url:URL.createObjectURL(blob),scan,source,mode,processingFailed:false});
    }
    function bindQueue(){host.querySelectorAll('[data-cr-qtask]').forEach(el=>el.onchange=()=>{queue[+el.dataset.crQtask].task=el.value;});host.querySelectorAll('[data-cr-qremove]').forEach(el=>el.onclick=()=>{const item=queue.splice(+el.dataset.crQremove,1)[0];if(item)URL.revokeObjectURL(item.url);render();});if($('[data-cr-upload]'))$('[data-cr-upload]').onclick=()=>act(tr('답안 사진을 서버로 보내는 중…','Sending answer pages…'),async()=>{if(!uploadCode)use(await client.qr(session.id));const warnings=new Set();while(queue.length){const p=queue[0],uploaded=await client.upload(uploadCode,p.task,p.blob),warning=uploadWarning(uploaded,ko?'ko':'en');if(warning)warnings.add(warning);queue.shift();URL.revokeObjectURL(p.url);}approved=false;await refresh(true);if(warnings.size)error=[...warnings].join(' ');});}
    function bindScanQueue(){
      host.querySelectorAll('[data-cr-qzoom]').forEach(el=>el.onclick=()=>inspectQueue(queue[+el.dataset.crQzoom],false));
      host.querySelectorAll('[data-cr-qsource]').forEach(el=>el.onclick=()=>inspectQueue(queue[+el.dataset.crQsource],true));
      host.querySelectorAll('[data-cr-qmode]').forEach(el=>el.onclick=()=>act(tr('사진을 다시 보정하는 중…','Rebuilding the page…'),()=>rebuildQueue(queue[+el.dataset.crQmode],{mode:el.dataset.mode})));
      host.querySelectorAll('[data-cr-qrotate]').forEach(el=>el.onclick=()=>act(tr('사진을 회전하는 중…','Rotating the photo…'),()=>rebuildQueue(queue[+el.dataset.crQrotate],{rotate:true})));
      host.querySelectorAll('[data-cr-qedit]').forEach(el=>el.onclick=()=>act(tr('모서리를 확인하세요.','Check the corners.'),async()=>{
        const p=queue[+el.dataset.crQedit],account=client.fingerprint(),abort=new AbortController();cornerAbort?.abort();cornerAbort=abort;
        try{const scanner=await scannerLibrary();if(!alive||client.fingerprint()!==account||abort.signal.aborted)return;
          const edit=await scanner.editCorners(p.scan.baseUrl,p.scan.corners,{marker:p.scan.method==='marker',lang:ko?'ko':'en',pageFormat:p.scan.outputFormat||'auto',signal:abort.signal});
          if(edit&&!abort.signal.aborted&&alive&&client.fingerprint()===account&&queue.includes(p))await rebuildQueue(p,edit);
        }finally{if(cornerAbort===abort)cornerAbort=null;}
      }));
    }
    async function prepareFiles(files){const account=client.fingerprint();for(const file of files){const remaining=MAX_PAGES-(session.pages||[]).length-queue.length;if(remaining<=0)throw{code:'too_many_pages'};const prepared=await filePages(file,remaining);if(!alive||client.fingerprint()!==account)return;for(const p of prepared)queue.push({...p,url:URL.createObjectURL(p.blob),task:tasks[0]});}}
    function ocrLabel(p){return uploadWarning(p,ko?'ko':'en')||(p.source==='typed'?tr('확정된 화면 풀이','Locked typed answer'):({unpaid:tr('검토 시작 후 읽기','Read after review starts'),queued:tr('판독 대기','Queued for reading'),reading:tr('판독 중','Reading'),done:tr('읽음','Read'),failed:tr('판독 실패 · 원본 대조 필요','Reading failed · check original'),off:tr('자동 읽기 대기','Waiting for reading'),none:tr('접수됨','Received')})[p.ocr_status]||tr('원본 대조 필요','Check original'));}
    function pageText(p){if(dirty.has(p.id))return dirty.get(p.id);if(p.text)return p.text;return(p.read?.items||[]).filter(i=>!i.crossed_out).map(i=>i.label+': '+(i.text||(i.value??''))).join('\n');}
    function pagesHTML(pages){if(!pages.length)return `<p class="cr-empty">${tr('아직 보낸 답안이 없습니다.','No pages sent yet.')}</p>`;return pages.map(p=>`<article class="cr-page" data-cr-page="${p.id}"><div class="cr-thumb" data-cr-thumb="${p.id}"></div><div class="cr-pagebody"><div class="cr-pagemeta"><b>#${p.no}</b><label>${tr('문항','Question')}<select data-cr-task="${p.id}" ${busy?'disabled':''}>${taskOptions(p.task)}</select></label><span>${escape(ocrLabel(p))}</span><button data-cr-remove="${p.id}" ${busy?'disabled':''}>${tr('이 쪽 빼기','Remove page')}</button></div>${session.paid?`<label class="cr-readlabel">${tr('읽힌 풀이 · 원본의 OCR 오독만 정정','Recognized solution · correct OCR errors only')}<textarea data-cr-edit="${p.id}" maxlength="50000" ${p.source==='typed'||Network.reading(p)?'readonly':''} ${busy||Network.reading(p)?'disabled':''}>${escape(pageText(p))}</textarea></label><p class="cr-small">${tr('원본과 정정 내용을 함께 보관합니다. 추가 풀이를 작성하는 칸이 아닙니다.','Original scans and corrections are retained together. This is not a space for additional solving.')}</p>`:`<p class="cr-small">${tr('답안을 저장했습니다. 0.3토큰으로 검토를 시작하면 읽힌 풀이를 확인할 수 있습니다.','Page saved. Start review for 0.3 token to inspect the recognized work.')}</p>`}</div></article>`).join('');}
    function bindPages(){host.querySelectorAll('[data-cr-task]').forEach(el=>el.onchange=()=>act(tr('문항 분류를 저장하는 중…','Saving question label…'),async()=>{await client.classify(session.id,+el.dataset.crTask,el.value,'answer');approved=false;await refresh(true);}));host.querySelectorAll('[data-cr-remove]').forEach(el=>el.onclick=()=>act(tr('답안 쪽을 빼는 중…','Removing page…'),async()=>{await client.remove(session.id,+el.dataset.crRemove);dirty.delete(+el.dataset.crRemove);approved=false;await refresh(true);}));host.querySelectorAll('[data-cr-edit]').forEach(el=>el.oninput=()=>{dirty.set(+el.dataset.crEdit,el.value);approved=false;const check=$('[data-cr-approved]');if(check)check.checked=false;const button=$('[data-cr-submit]');if(button)button.disabled=true;});}
    async function pay(){
      if(!session||session.paid||busy)return;
      await act(tr('0.3토큰을 사용하고 답안을 읽는 중…','Using 0.3 token and reading answers…'),async()=>{if(!available())throw{code:'provider_unavailable'};use(await client.pay(session.id,fee(),provider));use(await client.read(session.id,provider));approved=false;});
    }
    async function submit(){
      if(!session?.paid||!approved||busy||(session.pages||[]).some(Network.reading))return;
      await act(tr('확인한 답안을 제출하고 검토하는 중…','Submitting checked work for review…'),async()=>{
        const pages=(session.pages||[]).filter(p=>(p.source!=='typed'&&!p.confirmed)||dirty.has(p.id)).map(p=>({id:p.id,text:pageText(p),task:p.task}));
        if(pages.length)use(await client.confirmAll(session.id,pages));
        use(await client.submit(session.id,fee(),provider));dirty.clear();approved=false;
      });
    }
    async function paintQR(){
      const area=$('[data-cr-qr]');if(!area||!session)return;
      if(!uploadCode){try{uploadCode=storage.getItem('hlExamUp:'+session.id)||'';}catch(_){} }
      if(!uploadCode){area.innerHTML=`<p class="cr-small">${tr('‘스캔 링크 새로 만들기’를 눌러 휴대전화 접속 링크를 받으세요.','Renew the scan link to connect your phone.')}</p>`;return;}
      qrUrl=scanURL();area.innerHTML=`<a href="${escape(qrUrl)}" target="_blank" rel="noopener noreferrer">${tr('휴대전화 스캐너 열기','Open phone scanner')} ↗</a>`;
      const version=revision,make=await qrLibrary();if(!alive||version!==revision||!make||!area.isConnected)return;
      const q=make(0,'M');q.addData(qrUrl);q.make();area.insertAdjacentHTML('afterbegin',q.createSvgTag({cellSize:3,margin:3,scalable:true}));
    }
    async function paintThumbs(pages){
      const version=revision;
      for(const p of pages){const area=$('[data-cr-thumb="'+p.id+'"]');if(!area)continue;let url=thumbs.get(p.id);
        if(p.source==='typed'){area.textContent=tr('화면 풀이','Typed answer');continue;}
        if(!url){try{if(!thumbPending.has(p.id)){const account=client.fingerprint(),pending=(async()=>{const r=await (options.fetch||fetch)(client.imageURL(p.id),{headers:{Authorization:'Bearer '+getToken()}});if(!r.ok)return null;const blob=await r.blob();if(!/^image\//.test(blob.type)||!alive||client.fingerprint()!==account)return null;const value=URL.createObjectURL(blob);thumbs.set(p.id,value);return value;})();thumbPending.set(p.id,pending);pending.finally(()=>thumbPending.delete(p.id)).catch(()=>{});}url=await thumbPending.get(p.id);if(!url)continue;}catch(_){continue;}}
        if(!alive||version!==revision)return;area.innerHTML=`<a href="${escape(url)}" target="_blank" rel="noopener"><img src="${escape(url)}" alt="${tr('원본 답안','Original answer')} #${p.no}"></a>`;
      }
    }
    function resultHTML(){
      const per=session.detail?.tasks||{},done=Object.entries(per);
      const summary=session.status==='graded'?`<p class="cr-score">${escape(session.score??0)} / ${escape(session.points??entry.questions*7)}</p><p class="cr-small">${tr('AI 학습용 참고점수 · 공식 점수 아님','AI learning reference score · not an official score')}</p>`:`<p class="cr-note">${session.status==='pending'?tr('답안 또는 검토 근거가 불확실하여 관리자 검토를 기다립니다. 아직 확정된 점수는 없습니다.','The work or review evidence is uncertain and awaits manual review. No score is final yet.'):escape(stateLabel(session.status))}</p>`;
      return `<h3>${stateLabel(session.status)}</h3>${summary}<div class="cr-results">${done.map(([task,r])=>`<article><div class="cr-resulthead"><b>${escape(task.replace(/^Q/,''))}. ${tr('문항','Question')}</b><span>${stateLabel(r.status)}</span>${r.status==='graded'?`<strong>${escape(r.score??0)} / ${escape(r.points??7)}</strong>`:''}</div>${r.why?`<p class="cr-small">${tr('검토 근거 또는 답안 판독이 부족해 관리자 확인이 필요합니다.','The evidence or recognized work needs manual checking.')}</p>`:''}${Array.isArray(r.items)?`<ul>${r.items.map(i=>`<li>${escape(i.name||i.what||i.id||'')} ${i.got!==undefined?`<b>${escape(i.got)} / ${escape(i.points??i.max??'')}</b>`:''}${i.note?` — ${escape(i.note)}`:''}</li>`).join('')}</ul>`:''}${feedbackHTML(r)}</article>`).join('')}</div><div class="cr-actions"><button data-cr-refresh ${busy?'disabled':''}>${tr('결과 다시 확인','Refresh result')}</button><a href="../#/lab/${session.id}">${tr('내 채점 접수 기록','My review record')}</a><p class="cr-small">${tr('새 응시는 새 접수로 분리됩니다. 이미 사용한 이 접수의 토큰은 결과 새로고침 때 다시 차감하지 않습니다.','A new attempt creates a separate review. Refreshing this result does not spend another token.')}</p></div>`;
    }
    function feedbackHTML(r){const review=r.review||{},summary=review.summary||review.overall||r.summary||r.comment||'';return(summary?`<p>${escape(summary)}</p>`:'')+(Array.isArray(r.feedback)?`<ul class="cr-feedback">${r.feedback.filter(f=>f.note).map(f=>`<li>${escape(f.note)}</li>`).join('')}</ul>`:'')+(Array.isArray(review.habits)?`<ul>${review.habits.map(h=>`<li><b>${escape(h.habit||'')}</b> ${escape(h.fix||'')}</li>`).join('')}</ul>`:'');}
    function bindResult(){if($('[data-cr-refresh]'))$('[data-cr-refresh]').onclick=()=>act(tr('검토 결과를 확인하는 중…','Refreshing review…'),()=>refresh(true));}
    async function init(){
      let requested=options.reviewId;
      if(requested===undefined)try{requested=new URL(location.href).searchParams.get('review');}catch(_){}
      if(requested!==undefined&&requested!==null)try{session={id:sessionId(requested)};}catch(_){error=reason({code:'not_found'});render();return;}
      const link=saved();if(!session&&link?.examId===entry.id&&Number.isSafeInteger(link.id))session={id:link.id};
      render();
      if(getToken()){
        await refresh();if(session&&!uploadCode)try{uploadCode=storage.getItem('hlExamUp:'+session.id)||'';}catch(_){}if(alive)render();
      }
    }
    function accountChanged(){if(identity===client.fingerprint())return;identity=client.fingerprint();revisionEpoch++;clearQueuedImages();needsLogin=false;tokens=null;approved=false;provider='gemini';vision=null;dirty.clear();session=null;uploadCode='';for(const url of thumbs.values())URL.revokeObjectURL(url);thumbs.clear();render();if(getToken())void init();}
    if(typeof window==='object'){window.addEventListener?.('storage',accountChanged);window.addEventListener?.('focus',accountChanged);}
    init();
    return{refresh:()=>refresh(),getSession:()=>session,dispose(){alive=false;revision++;stopTimers();poller?.dispose();clearQueuedImages();if(typeof window==='object'){window.removeEventListener?.('storage',accountChanged);window.removeEventListener?.('focus',accountChanged);}for(const url of thumbs.values())URL.revokeObjectURL(url);thumbs.clear();}};
  }
  return{mount,createClient,mapAnswers,taskNumbers,storageKey,sessionId,uploadWarning,DEFAULT_API};
});
