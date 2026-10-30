import { processShot, reprocess, canProcess, toGray, findSheetMarkersGray, findPageQuadGray, MARKER_INSET, encodeUpload, rotatePhoto, orderCorners, quadScore, inspectDocumentPixels } from './labscan/scanner.js?v=20261030-ocr';

const DEFAULT_API='https://haslalab-community-edge.haslalab.workers.dev';
const API_HOSTS=new Set(['haslalab-community-edge.haslalab.workers.dev','haslalab-community.haslalab.workers.dev']);
export function parseMonthlyScanLink(location,navigatorLanguage='ko'){
  const hash=new URLSearchParams(String(location.hash||'').replace(/^#/,'')),query=new URLSearchParams(location.search||'');
  const candidate=hash.get('token')||'',token=/^[A-Za-z0-9_-]{43}$/.test(candidate)?candidate:'';
  const language=hash.get('l')||query.get('lang'),lang=['ko','en'].includes(language)?language:String(navigatorLanguage).startsWith('ko')?'ko':'en';
  let api=DEFAULT_API,validApi=true;
  const requested=hash.get('a');
  if(requested)try{
    const url=new URL(requested),loopback=['localhost','127.0.0.1','[::1]'].includes(url.hostname);
    if(url.username||url.password||url.search||url.hash||!/^\/?$/.test(url.pathname)||!(url.protocol==='https:'&&API_HOSTS.has(url.hostname)||loopback&&['http:','https:'].includes(url.protocol)))throw Error('invalid');
    api=url.origin;
  }catch{validApi=false;}
  return {token:validApi?token:'',api,lang};
}

// This upload capability is unrelated to sign-in. Never read account storage,
// put it in a URL/body, or include it in error messages or diagnostics.
export function createMonthlyScanClient({api,token,fetch:perform=globalThis.fetch}){
  const request=async(method,path,body)=>{
    let response;
    try{response=await perform(api+'/api/monthly/scan'+path,{method,credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',headers:{'X-Monthly-Scan':token},...(body?{body}:{})});}
    catch{throw{code:'network'};}
    const value=await response.json().catch(()=>({}));
    if(!response.ok)throw{code:value.error||'server_error',status:response.status};
    return value;
  };
  return {info:()=>request('GET',''),upload:({image,original,part,requestId})=>{
    const form=new FormData();form.append('image',image,'answer.'+(image.type==='image/png'?'png':image.type==='image/webp'?'webp':'jpg'));
    form.append('original_image',original,'original.'+(original.type==='image/png'?'png':original.type==='image/webp'?'webp':'jpg'));form.append('part_id',part);form.append('request_id',requestId);
    return request('POST','/photos?mode=math',form);
  }};
}
export function monthlyUploadRequestId(random=globalThis.crypto){
  if(random?.randomUUID)return random.randomUUID();
  if(!random?.getRandomValues)throw{code:'unsupported_browser'};
  const bytes=random.getRandomValues(new Uint8Array(16));
  return 'monthly-'+Array.from(bytes,value=>value.toString(16).padStart(2,'0')).join('');
}

export const monthlyScanText={
  ko:{title:'월별 문제 답안 스캔',part:'소문항 선택',answer:'답안 사진',help:'답안지의 네 귀퉁이를 모두 보이게 찍으세요. 여러 소문항을 쓴 사진은 해당 소문항을 선택해 보내고, 컴퓨터에서 읽힌 내용을 나누어 확인하세요.',
    privacy:'사진 전송과 인식은 최종 제출이 아닙니다. 컴퓨터에서 소문항별 최종 답·풀이를 확인하고 제출하세요.',
    live:'카메라로 스캔',camApp:'기본 카메라',gallery:'사진 고르기',working0:'사진을 보정하는 중…',corners:'모서리 맞추기',modes:{clean:'또렷하게',mono:'흑백',original:'원본'},
    weak:'종이 모서리를 확실히 찾지 못했습니다. 모서리 맞추기로 네 점을 확인하세요.',blurry:'사진이 흐립니다. 다시 찍으면 글자를 더 잘 읽습니다.',lowRes:'글씨가 작게 찍혔습니다. 종이가 화면을 채우도록 가까이 찍어 주세요.',processFailed:'자동 보정에 실패했습니다. 원본을 확인하거나 다시 촬영하세요.',
    compare:'원본 보기',processed:'보정본 보기',zoom:'크게 보기',rotate:'90° 회전',detail:'작은 글씨와 수식이 선명한지 확대해서 확인하세요.',pointMarker:'검은 표식 중심',pointPaper:'종이 귀퉁이',ceMarker:'네 점을 검은 사각형 표식의 중심에 맞추세요. 바깥 여백도 보존됩니다.',badCorners:'네 점을 서로 다른 네 귀퉁이에 맞춰 주세요.',
    send:'컴퓨터로 보내기',retake:'다시 찍기',sending:'전송하고 글자를 읽는 중…',sentOk:'사진을 보냈습니다. 컴퓨터에서 읽힌 풀이를 확인하세요.',sentH:'이 휴대전화에서 보낸 사진',none:'아직 보낸 사진이 없습니다.',read:'읽힌 내용',saved:'전송 완료',sentNo:n=>`${n}번째 사진`,left:'스캔 링크 남은 시간',closed:'이 스캔 링크는 만료되었거나 닫혔습니다. 컴퓨터에서 새 QR 코드를 열어 주세요.',badLink:'스캔 링크가 올바르지 않습니다. 컴퓨터의 월별 문제 화면에서 QR 코드를 다시 찍어 주세요.',
    connecting:'컴퓨터와 연결하는 중…',retry:'다시 연결',disconnected:'연결하지 못했습니다. 인터넷 연결을 확인하고 다시 시도하세요.',noCanvas:'이 브라우저에서는 자동 보정할 수 없습니다. 원본을 확인한 뒤 보낼 수 있습니다.',
    lvAim:'종이의 네 귀퉁이가 모두 화면에 들어오게 하세요.',lvPage:'종이를 찾았습니다. 검은 표식이 보이면 더 정확합니다.',lvHold:'그대로 멈추세요…',lvTake:'찍는 중…',lvAuto:'자동 촬영',lvClose:'닫기',lvNoCam:'카메라를 열 수 없습니다. 기본 카메라나 사진 고르기를 사용하세요.',ceTop:'네 점을 종이의 네 귀퉁이에 맞추세요.',ceOk:'이대로 펴기',ceCancel:'취소',
    err:{network:'전송 상태를 확인하지 못했습니다. 컴퓨터에 사진이 도착했는지 먼저 확인한 뒤 다시 보내세요.',image_too_big:'사진 용량이 큽니다. 흑백 모드로 바꾸거나 종이를 가까이서 다시 찍어 주세요.',bad_image:'JPG, PNG, WebP 사진을 선택해 주세요.',input_too_big:'12MB 이하의 사진을 선택해 주세요.',monthly_photo_storage_full:'이 문제의 사진 저장 한도에 도달했습니다. 컴퓨터에서 답안을 확인해 주세요.',rate_limited:'잠시 후 다시 시도하세요.',ocr_off:'사진 인식 기능이 잠시 꺼져 있습니다. 나중에 다시 시도해 주세요.',ocr_failed:'사진을 읽지 못했습니다. 선명한 사진으로 다시 시도해 주세요.',bad_part:'컴퓨터에서 새 QR 코드를 열어 소문항 목록을 다시 확인해 주세요.',server_error:'전송하지 못했습니다. 잠시 후 다시 시도하세요.'}},
  en:{title:'Monthly answer scan',part:'Choose answer part',answer:'Answer photo',help:'Include all four paper corners. Choose the matching part before sending. If a photo contains several parts, separate and check the recognized work on your computer.',
    privacy:'Sending and reading photos does not submit your answer. Check each final answer and working on the computer, then submit.',
    live:'Scan with camera',camApp:'Camera app',gallery:'Choose photo',working0:'Straightening photo…',corners:'Fix corners',modes:{clean:'Clean',mono:'B&W',original:'Original'},
    weak:'Page corners were not found with certainty. Check the four points using Fix corners.',blurry:'The photo is blurry. A sharper photo reads better.',lowRes:'The writing occupies too little of the photo. Move closer so the page fills the frame.',processFailed:'Automatic correction failed. Inspect the original or retake the photo.',
    compare:'View original',processed:'View corrected',zoom:'Enlarge',rotate:'Rotate 90°',detail:'Enlarge the photo to check small writing and equations.',pointMarker:'Black marker centres',pointPaper:'Paper corners',ceMarker:'Put the points at the centres of the black squares. Outside margins are preserved.',badCorners:'Place the points at four different corners.',
    send:'Send to computer',retake:'Retake',sending:'Sending and reading…',sentOk:'Photo sent. Check the recognized working on your computer.',sentH:'Photos sent from this phone',none:'No photos sent yet.',read:'Recognized text',saved:'Sent',sentNo:n=>`Photo ${n}`,left:'Scan link expires in',closed:'This scan link has expired or closed. Open a new QR code on the computer.',badLink:'This scan link is invalid. Scan a new QR code from the monthly problem on your computer.',
    connecting:'Connecting to your computer…',retry:'Reconnect',disconnected:'Could not connect. Check your internet connection and try again.',noCanvas:'This browser cannot straighten photos. Inspect and send the original instead.',
    lvAim:'Include all four paper corners in the frame.',lvPage:'Page found. Printed black markers improve accuracy.',lvHold:'Hold still…',lvTake:'Taking photo…',lvAuto:'Auto',lvClose:'Close',lvNoCam:'Camera unavailable. Use Camera app or Choose photo.',ceTop:'Place the points at the four paper corners.',ceOk:'Straighten',ceCancel:'Cancel',
    err:{network:'Could not confirm delivery. Check whether the photo arrived on your computer before sending again.',image_too_big:'The photo is too large. Try B&W or retake with the page filling the frame.',bad_image:'Choose a JPG, PNG or WebP photo.',input_too_big:'Choose a photo no larger than 12 MB.',monthly_photo_storage_full:'Photo storage for this problem is full. Check your work on the computer.',rate_limited:'Please try again shortly.',ocr_off:'Photo recognition is temporarily unavailable. Please try later.',ocr_failed:'The photo could not be read. Try a sharper photo.',bad_part:'Open a new QR code on the computer to refresh the answer parts.',server_error:'Could not send. Please try again later.'}}
};
Object.assign(monthlyScanText.ko.err,{upload_processing:'이 사진의 판독을 진행 중입니다. 잠시 후 같은 사진으로 다시 보내면 처리 결과를 확인합니다.',upload_conflict:'이 사진의 전송 기록과 선택 항목이 일치하지 않습니다. 사진을 다시 선택해 확인해 주세요.'});
Object.assign(monthlyScanText.en.err,{upload_processing:'This photo is still being read. Wait briefly and send the same photo again to retrieve its result.',upload_conflict:'This photo does not match its previous upload. Choose the photo again and check its answer part.'});
for(const language of ['ko','en']){const errors=monthlyScanText[language].err;errors.ocr_empty=errors.ocr_failed;errors.ocr_too_big=errors.ocr_failed;errors.bad_answer_sheet=errors.bad_part;}

const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function monthlyScanHistory(rows,lang='ko'){
  const T=monthlyScanText[lang]||monthlyScanText.ko;
  return `<section class="card"><h2>${T.sentH} · ${rows.length}</h2><ol class="sent">${rows.map((row,i)=>`<li><div class="meta"><b>${esc(row.part_id)}</b><span>${T.sentNo(i+1)}</span><span>${T.saved}</span></div>${row.text?`<details><summary>${T.read}</summary><pre>${esc(row.text)}</pre></details>`:''}</li>`).join('')||`<li class="help">${T.none}</li>`}</ol></section>`;
}

export function mountMonthlyScan(){
  const link=parseMonthlyScanLink(location,navigator.language);let {lang}=link;
  // Scrub even invalid links. The capability stays in this tab's memory only.
  try{history.replaceState(null,'',location.pathname);}catch{}
  const client=createMonthlyScanClient(link),$=id=>document.getElementById(id),t=()=>monthlyScanText[lang];
  let INFO=null,SKEW=0,task='',kind='answer',shot=null,mode='clean',shotRevision=0,closeShotEditor=null,closeLive=null,closeZoom=null,cameraRequest=0,uploading=false,closed=false,inactive=false,failed=false,refreshing=null,pollTimer=null;
  const sent=[],srvNow=()=>Date.now()/1000+SKEW;
  const partLabel=id=>{const p=INFO?.parts?.find(part=>part.id===id);return id+(p?' · '+(lang==='en'?p.label_en||p.label:p.label||p.label_en):'');};
  function toast(message,duration=5500){const node=document.createElement('div');node.className='toast';node.setAttribute('role','status');node.textContent=message;document.body.append(node);setTimeout(()=>node.remove(),duration);}
  function stopPolling(){clearTimeout(pollTimer);pollTimer=null;}
  const phonePoll={stop:stopPolling,start(){stopPolling();if(!closed&&!inactive&&!shot&&!document.hidden)pollTimer=setTimeout(()=>refresh(),15000);}};
  function expire(){if(closed)return;closed=true;cameraRequest++;phonePoll.stop();closeLive?.();closeZoom?.();closeShotEditor?.();releaseShot();paint();}
  function isClosed(error){return error.status===403||error.status===410||['scan_closed','scan_expired','bad_scan_token','bad_token'].includes(error.code);}
  async function refresh(){
    if(closed||inactive||!link.token)return;
    if(refreshing)return refreshing;
    const promise=(async()=>{try{
      const info=await client.info();if(closed||inactive)return;
      if(!info.session||!Array.isArray(info.parts)||!info.parts.length||!Number.isFinite(info.session.expires_at))throw{code:'server_error'};
      INFO=info;SKEW=Number.isFinite(info.now)?info.now-Date.now()/1000:0;failed=false;
      if(!INFO.parts.some(part=>part.id===task))task=INFO.parts.some(part=>part.id===info.session.part_id)?info.session.part_id:INFO.parts[0].id;
      if(info.session.open===false||info.session.expires_at<=srvNow())return expire();
      if(!shot)paint();
    }catch(error){if(isClosed(error))return expire();failed=true;if(!shot)paint();}
    finally{phonePoll.start();}})();refreshing=promise;promise.finally(()=>{if(refreshing===promise)refreshing=null;});return promise;
  }
  function paint(){
    document.documentElement.lang=lang;document.title=t().title+' · HaslaLab';$('language').value=lang;$('language').disabled=uploading;
    if(!link.token){$('app').innerHTML=`<h1>${t().title}</h1><p class="note w">${t().badLink}</p>`;return;}
    const title=lang==='en'?INFO?.problem?.title_en||INFO?.problem?.title:INFO?.problem?.title||INFO?.problem?.title_en;
    const top=`<p class="eyebrow">${t().title}</p><h1>${esc(title||t().title)}</h1>`;
    if(closed){$('app').innerHTML=top+`<p class="note w" role="alert">${t().closed}</p>`+monthlyScanHistory(sent,lang);return;}
    if(!INFO){$('app').innerHTML=top+`<p class="note${failed?' w':''}" role="status">${failed?t().disconnected:t().connecting}</p>${failed?`<button id="retry" type="button">${t().retry}</button>`:''}`;if($('retry'))$('retry').onclick=refresh;return;}
    $('app').innerHTML=top+`<p class="sub">${t().privacy}</p><div class="clock" id="clockBox"><span>${t().left}</span><b id="clock">--:--</b></div>${failed?`<p class="note w">${t().disconnected}</p>`:''}
      <section class="card"><label class="part-label" for="parts">${t().part}</label><select id="parts"${uploading?' disabled':''}>${INFO.parts.map(part=>`<option value="${esc(part.id)}"${part.id===task?' selected':''}>${esc(partLabel(part.id))}</option>`).join('')}</select>
      <div class="shoot">${LIVE_OK?`<button type="button" class="pri" id="live">${t().live}</button>`:''}<button type="button" id="camera">${t().camApp}</button><button type="button" id="gallery">${t().gallery}</button><input id="cam" type="file" accept="image/jpeg,image/png,image/webp" capture="environment"><input id="gal" type="file" accept="image/jpeg,image/png,image/webp"></div><p class="help">${t().help}</p>${canProcess()?'':`<p class="note w">${t().noCanvas}</p>`}</section><div id="shot"></div>${monthlyScanHistory(sent,lang)}`;
    $('parts').onchange=()=>{task=$('parts').value;if(shot&&!uploading){if(shot.task!==task)shot.requestId=null;shot.task=task;paintShot();}};
    $('camera').onclick=()=>$('cam').click();$('gallery').onclick=()=>$('gal').click();
    for(const id of ['cam','gal'])$(id).onchange=event=>{const file=event.target.files?.[0];event.target.value='';if(file)take(file);};
    if($('live'))$('live').onclick=liveCamera;
    if(uploading)document.querySelectorAll('.shoot button,.shoot input').forEach(button=>button.disabled=true);
    paintShot();updateClock();
  }
  async function send(){
    if(!shot||shot.busy||uploading||closed)return;
    const sending=shot,revision=shotRevision;uploading=true;paint();const button=$('send');button.disabled=true;button.textContent=t().sending;
    try{
      if(!sending.requestId)sending.requestId=monthlyUploadRequestId();
      const maximum=Math.min(4*1024*1024,INFO.limits?.max_image_bytes||4*1024*1024);
      const image=await encodeUpload(sending.blob,{maxBytes:maximum}),original=await encodeUpload(sending.file,{maxBytes:maximum});
      if(closed||revision!==shotRevision)return;
      const result=await client.upload({image,original,part:sending.task,requestId:sending.requestId});
      if(closed||revision!==shotRevision)return;
      sent.push({part_id:result.part_id||sending.task,text:typeof result.text==='string'?result.text:'',photo_id:result.photo_id});
      releaseShot();toast(t().sentOk);await refresh();
    }catch(error){if(isClosed(error))expire();else toast(t().err[error.code]||t().err.server_error,9000);}
    finally{uploading=false;if(!closed)paint();else $('language').disabled=false;}
  }
  function updateClock(){
    if(!INFO||closed)return;const left=Math.ceil(INFO.session.expires_at-srvNow());if(left<=0)return expire();
    if($('clock'))$('clock').textContent=Math.floor(left/60)+':'+String(left%60).padStart(2,'0');$('clockBox')?.classList.toggle('warn',left<=120);
  }
  function showZoom(){
    if(!shot)return;const dialog=document.createElement('dialog');dialog.className='image-check';dialog.setAttribute('aria-label',t().detail);
    dialog.innerHTML=`<button type="button" autofocus>${t().lvClose}</button><img alt="${esc(t().detail)}" src="${shot.showOriginal?shot.originalUrl:shot.previewUrl}">`;
    document.body.append(dialog);const close=()=>dialog.close();closeZoom=close;
    dialog.addEventListener('close',()=>{dialog.remove();if(closeZoom===close)closeZoom=null;},{once:true});dialog.querySelector('button').onclick=close;dialog.showModal();
  }
  // Camera and perspective controls below share the proven exam scan engine.
  // Image state belongs to this page; the timed exam scanner is never changed.
  async function take(file, live, internal = false) {
  if (!file || uploading || closed || inactive) return;
  if (!/^image\/(jpeg|png|webp)$/.test(file.type)) return toast(t().err.bad_image);
  if (!internal && file.size > 12 * 1024 * 1024) return toast(t().err.input_too_big);
  releaseShot();
  const revision = shotRevision;
  shot = { file, originalUrl: URL.createObjectURL(file), busy: true, pct: 0, task, kind, live: !!live };phonePoll.stop();
  mode = "clean"; paintShot();
  if (!canProcess()) { shot = { ...shot, busy: false, blob: file, previewUrl: shot.originalUrl, autoScore: 0, quality: null, processFailed: true }; return paintShot(); }
  try {
    const r = await processShot(file, { mode, onProgress: p => { if (revision !== shotRevision || !shot) return; shot.pct = p; const i = document.querySelector("#shot .bar i"); if (i) i.style.width = p + "%"; } });
    if (revision !== shotRevision || !shot) return;
    shot = { ...shot, ...r, busy: false };
  } catch (e) { if (revision !== shotRevision || !shot) return; shot = { ...shot, busy: false, blob: file, previewUrl: shot.originalUrl, autoScore: 0, quality: null, processFailed: true }; }
  paintShot();
}
function releaseShot() { ++shotRevision; if (closeShotEditor) closeShotEditor(); if (shot?.originalUrl) URL.revokeObjectURL(shot.originalUrl); shot = null;phonePoll.start(); }
function paintShot() {
  const box = $("shot"); if (!box) return;
  if (!shot) { box.innerHTML = ""; return; }
  if (shot.busy) { box.innerHTML = `<div class="card"><h2>${t().working0}</h2><div class="bar"><i style="width:${shot.pct || 3}%"></i></div></div>`; return; }
  const q = shot.quality || {}, warn = [];
  if (shot.processFailed) warn.push(t().processFailed);
  else if (shot.autoScore != null && shot.autoScore < 0.75) warn.push(t().weak);
  if (q.focus != null && q.focus < 22) warn.push(t().blurry);          // (the cleaned page is white on purpose, so glare is not judged on it)
  if (shot.sourceShortSide != null && shot.sourceShortSide < 1200) warn.push(t().lowRes);
  box.innerHTML = `<div class="card prev"><h2>${esc(partLabel(shot.task))} · ${shot.kind === "answer" ? t().answer : t().working}</h2>
    <img alt="${esc(shot.showOriginal ? t().compare : t().processed)}" src="${shot.showOriginal ? shot.originalUrl : shot.previewUrl}">
    <p style="font-size:12.5px;color:var(--muted)">${t().detail}${shot.width ? ` · ${shot.width}×${shot.height}px` : ""}</p>
    <div class="row"><button id="compare">${shot.showOriginal ? t().processed : t().compare}</button><button id="zoom">${t().zoom}</button>${canProcess() ? `<button id="rotate">${t().rotate}</button>` : ""}</div>
    ${warn.map(w => `<div class="note w">${w}</div>`).join("")}
    ${shot.baseUrl ? `<div class="chips" style="margin-top:10px">${Object.entries(t().modes).map(([k, v]) => `<button data-m="${k}" class="${k === mode ? "on" : ""}">${v}</button>`).join("")}</div>` : ""}
    <div class="row">${shot.baseUrl ? `<button id="fix">${t().corners}</button>` : ""}<button id="again">${t().retake}</button></div>
    <div class="row"><button class="pri" id="send">${t().send}</button></div></div>`;
  box.querySelectorAll("[data-m]").forEach(b => b.onclick = () => redo(shot.corners, b.dataset.m));
  if ($("fix")) $("fix").onclick = () => cornerEditor();
  $("compare").onclick = () => { shot.showOriginal = !shot.showOriginal; paintShot(); };
  $("zoom").onclick = showZoom;
  if ($("rotate")) $("rotate").onclick = async () => { const keep = shot, revision = ++shotRevision, b = $("rotate"); b.disabled = true; try { const file = await rotatePhoto(keep.file); if (revision !== shotRevision || !shot) return; await take(file, keep.live, true); } catch (e) { if (revision !== shotRevision || !shot) return; toast(t().err[e.code] || t().err.bad_image); b.disabled = false; } };
  $("again").onclick = () => { const lv = shot.live; releaseShot(); paintShot(); if (lv) liveCamera(); else $("cam").click(); };
  $("send").onclick = send;
  if (uploading) { box.querySelectorAll("button").forEach(button => button.disabled = true); $("send").textContent = t().sending; }
}
async function redo(corners, m) {
  if (!shot) return;
  const revision = ++shotRevision;
  mode = m; const keep = shot; shot = { ...shot, busy: true, pct: 50 }; paintShot();
  try { const r = await reprocess(keep.baseUrl, corners, m, undefined, keep.method === "marker" ? MARKER_INSET : null); if (revision !== shotRevision || !shot) return; shot = { ...keep, ...r, requestId: null, corners, busy: false, showOriginal: false }; }
  catch (e) { if (revision !== shotRevision || !shot) return; shot = { ...keep, busy: false }; }
  paintShot();
}
async function cornerEditor() {
  if (!shot) return;
  const revision = shotRevision, editing = shot;
  const img = new Image(); img.src = editing.baseUrl; await img.decode().catch(() => {});
  if (revision !== shotRevision || !shot) return;
  const ov = document.createElement("div"); ov.className = "ce";
  let pointMode = editing.method === "marker" ? "marker" : "page";
  ov.innerHTML = `<div class="top"><div class="chips"><button data-point-mode="marker">${t().pointMarker}</button><button data-point-mode="page">${t().pointPaper}</button></div><p id="ceHint"></p></div><canvas></canvas><div class="row"><button id="ceNo">${t().ceCancel}</button><button class="pri" id="ceOk">${t().ceOk}</button></div>`;
  document.body.append(ov);
  const cv = ov.querySelector("canvas"), g = cv.getContext("2d");
  let pts = (editing.corners || [{ x: 0, y: 0 }, { x: img.width, y: 0 }, { x: 0, y: img.height }, { x: img.width, y: img.height }]).map(p => ({ ...p }));
  let sc = 1, ox = 0, oy = 0, drag = -1, dpr = devicePixelRatio || 1, moved = false;
  function fit() {
    const r = cv.getBoundingClientRect(); cv.width = r.width * dpr; cv.height = r.height * dpr;
    sc = Math.min(cv.width / img.width, cv.height / img.height) * 0.94; ox = (cv.width - img.width * sc) / 2; oy = (cv.height - img.height * sc) / 2; draw();
  }
  const scr = p => ({ x: ox + p.x * sc, y: oy + p.y * sc });
  function draw() {
    g.clearRect(0, 0, cv.width, cv.height); g.drawImage(img, ox, oy, img.width * sc, img.height * sc);
    const q = [0, 1, 3, 2].map(i => scr(pts[i]));
    g.strokeStyle = "#c5a3f5"; g.lineWidth = 2 * dpr; g.beginPath(); q.forEach((p, i) => i ? g.lineTo(p.x, p.y) : g.moveTo(p.x, p.y)); g.closePath(); g.stroke();
    pts.forEach((p, i) => { const s = scr(p); g.fillStyle = i === drag ? "#fff" : "rgba(197,163,245,.85)"; g.beginPath(); g.arc(s.x, s.y, 13 * dpr, 0, 7); g.fill(); });
    if (drag >= 0) {                                               // magnifier
      const p = pts[drag], R = 60 * dpr, z = 3, mx = pts[drag].x < img.width / 2 ? cv.width - R - 10 : R + 10, my = R + 10;
      g.save(); g.beginPath(); g.arc(mx, my, R, 0, 7); g.clip();
      g.drawImage(img, p.x - R / (sc * z), p.y - R / (sc * z), 2 * R / (sc * z), 2 * R / (sc * z), mx - R, my - R, 2 * R, 2 * R);
      g.strokeStyle = "#c5a3f5"; g.lineWidth = 1.5 * dpr; g.beginPath(); g.moveTo(mx - 10 * dpr, my); g.lineTo(mx + 10 * dpr, my); g.moveTo(mx, my - 10 * dpr); g.lineTo(mx, my + 10 * dpr); g.stroke();
      g.restore(); g.strokeStyle = "#fff"; g.beginPath(); g.arc(mx, my, R, 0, 7); g.stroke();
    }
  }
  const at = e => { const r = cv.getBoundingClientRect(); return { x: ((e.clientX - r.left) * dpr - ox) / sc, y: ((e.clientY - r.top) * dpr - oy) / sc }; };
  cv.onpointerdown = e => { const p = at(e); let best = -1, bd = 1e9; pts.forEach((q, i) => { const d = Math.hypot(q.x - p.x, q.y - p.y); if (d < bd) { bd = d; best = i; } });
    if (bd * sc < 60 * dpr) { drag = best; cv.setPointerCapture(e.pointerId); draw(); } };
  cv.onpointermove = e => { if (drag < 0) return; moved = true; const p = at(e); pts[drag] = { x: Math.max(0, Math.min(img.width, p.x)), y: Math.max(0, Math.min(img.height, p.y)) }; draw(); };
  cv.onpointerup = cv.onpointercancel = () => { drag = -1; draw(); };
  function choosePointMode(next) { pointMode = next; ov.querySelector("#ceHint").textContent = pointMode === "marker" ? t().ceMarker : t().ceTop; ov.querySelectorAll("[data-point-mode]").forEach(b => b.classList.toggle("on", b.dataset.pointMode === pointMode)); }
  ov.querySelectorAll("[data-point-mode]").forEach(b => b.onclick = () => choosePointMode(b.dataset.pointMode)); choosePointMode(pointMode);
  const close = () => { removeEventListener("resize", fit); ov.remove(); if (closeShotEditor === close) closeShotEditor = null; };
  closeShotEditor = close;
  addEventListener("resize", fit); fit();
  ov.querySelector("#ceNo").onclick = close;
  ov.querySelector("#ceOk").onclick = () => {
    if (revision !== shotRevision || !shot) return close();
    const ordered = orderCorners(pts);
    if (quadScore(ordered, img.width, img.height) < 0.1) return toast(t().badCorners);
    close(); shot.autoScore = 1; shot.method = pointMode === "marker" ? "marker" : "manual"; redo(ordered, mode);
  };
}

/* ── live camera, as scanning apps do it: the page is looked for in the moving picture a few times a second and
      outlined (green: the four printed corner squares, yellow: only the paper's edge); once the squares hold still
      for about a second the photo is taken by itself.  The photo then goes through the same straightening. ── */
const LIVE_OK = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia) && canProcess();
let AUTO = true;
try { AUTO = localStorage.getItem("hlScanAuto") !== "0"; } catch (e) {}
async function liveCamera() {
  if (closed || uploading || inactive) return;
  const request = ++cameraRequest;
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: { facingMode: { ideal: "environment" }, width: { ideal: 3840 }, height: { ideal: 2160 } } }); }
  catch (e) { toast(t().lvNoCam, 5000); return; }
  if (closed || inactive || document.hidden || request !== cameraRequest) { stream.getTracks().forEach(track => track.stop()); return; }
  const ov = document.createElement("div"); ov.className = "lv";
  ov.innerHTML = `<div class="vw"><video playsinline muted autoplay></video><canvas></canvas></div><div class="msg"></div>
    <div class="ctl"><button data-x="close">${t().lvClose}</button><button class="sh" data-x="shoot" aria-label="shutter"></button><button data-x="auto" class="${AUTO ? "on" : ""}">${t().lvAuto}</button></div>`;
  document.body.append(ov);
  const v = ov.querySelector("video"), cv = ov.querySelector("canvas"), g = cv.getContext("2d"), msg = ov.querySelector(".msg");
  v.srcObject = stream; await v.play().catch(() => {});
  const small = document.createElement("canvas"), sg = small.getContext("2d", { willReadFrequently: true });
  let alive = true, busy = false, hist = [], last = null, timer = null;
  const close = () => { alive = false; clearTimeout(timer); stream.getTracks().forEach(k => k.stop()); ov.remove(); if (closeLive === close) closeLive = null; };
  closeLive = close;
  const say = (m, ok) => { msg.textContent = m; msg.classList.toggle("ok", !!ok); };
  say(t().lvAim);
  async function capture() {
    if (busy || !alive) return; busy = true; say(t().lvTake, true);
    let blob = null;
    try { if (window.ImageCapture) blob = await new ImageCapture(stream.getVideoTracks()[0]).takePhoto(); } catch (e) { blob = null; }
    if (!blob) {
      const c = document.createElement("canvas"); c.width = v.videoWidth; c.height = v.videoHeight; c.getContext("2d").drawImage(v, 0, 0);
      blob = await new Promise(r => c.toBlob(r, "image/jpeg", 0.95));
    }
    const deliver = alive && request === cameraRequest && !closed && !inactive;
    close(); if (blob && deliver) take(blob, true);
  }
  function frame() {
    if (!alive) return;
    if (v.videoWidth) {
      const k = Math.min(1, 720 / Math.max(v.videoWidth, v.videoHeight)), w = Math.round(v.videoWidth * k), h = Math.round(v.videoHeight * k);
      if (small.width !== w) { small.width = w; small.height = h; }
      sg.drawImage(v, 0, 0, w, h);
      const pixels = sg.getImageData(0, 0, w, h).data, gray = toGray(pixels, w, h);
      let d = findSheetMarkersGray(gray, w, h), how = "marker";
      if (!d || d.score < 0.5) { const p = findPageQuadGray(gray, w, h); d = p && p.corners && p.score > 0.45 ? p : null; how = "page"; }
      /* the overlay, where the video is drawn (object-fit: contain) */
      const r = cv.getBoundingClientRect(), dpr = devicePixelRatio || 1;
      if (cv.width !== Math.round(r.width * dpr)) { cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr); }
      g.clearRect(0, 0, cv.width, cv.height);
      if (d) {
        const s = Math.min(cv.width / w, cv.height / h), ox = (cv.width - w * s) / 2, oy = (cv.height - h * s) / 2;
        const q = [0, 1, 3, 2].map(i => ({ x: ox + d.corners[i].x * s, y: oy + d.corners[i].y * s }));
        g.fillStyle = how === "marker" ? "rgba(87,171,90,.22)" : "rgba(197,163,245,.18)"; g.strokeStyle = how === "marker" ? "#57ab5a" : "#c5a3f5"; g.lineWidth = 3 * dpr;
        g.beginPath(); q.forEach((p, i) => i ? g.lineTo(p.x, p.y) : g.moveTo(p.x, p.y)); g.closePath(); g.fill(); g.stroke();
      }
      /* steady: the four squares moved less than 1.2 % of the picture over the last six looks */
      const focused = inspectDocumentPixels(pixels, w, h).focus >= 22;
      if (d && how === "marker" && d.score >= 0.75 && focused) {
        hist.push(d.corners); if (hist.length > 6) hist.shift();
        const span = Math.max(w, h), still = hist.length === 6 && hist.every(c => c.every((p, i) => Math.hypot(p.x - d.corners[i].x, p.y - d.corners[i].y) < span * 0.012));
        say(t().lvHold, true);
        if (still && AUTO) return capture();
      } else { hist = []; say(!focused && d ? t().blurry : d ? t().lvPage : t().lvAim); }
    }
    timer = setTimeout(frame, 140);
  }
  ov.onclick = e => { const b = e.target.closest("button"); if (!b) return;
    if (b.dataset.x === "close") close();
    else if (b.dataset.x === "shoot") capture();
    else if (b.dataset.x === "auto") { AUTO = !AUTO; b.classList.toggle("on", AUTO); hist = []; try { localStorage.setItem("hlScanAuto", AUTO ? "1" : "0"); } catch (e) {} } };
  frame();
}


  $('language').onchange=()=>{lang=$('language').value==='en'?'en':'ko';cameraRequest++;closeLive?.();closeZoom?.();closeShotEditor?.();paint();};
  let clockTimer=setInterval(updateClock,1000);
  document.addEventListener('visibilitychange',()=>{if(document.hidden){cameraRequest++;phonePoll.stop();closeLive?.();}else if(!closed&&!shot)refresh();});
  addEventListener('pagehide',()=>{inactive=true;cameraRequest++;phonePoll.stop();clearInterval(clockTimer);closeLive?.();closeZoom?.();closeShotEditor?.();releaseShot();});
  addEventListener('pageshow',event=>{if(event.persisted&&!closed){inactive=false;clockTimer=setInterval(updateClock,1000);refresh();}});
  addEventListener('hashchange',()=>{if(new URLSearchParams(location.hash.slice(1)).has('token'))location.reload();});
  paint();if(link.token)refresh();
}
if(typeof document!=='undefined')mountMonthlyScan();
