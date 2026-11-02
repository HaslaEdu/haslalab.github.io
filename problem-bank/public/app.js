const $=id=>document.getElementById(id);
const COPY={ko:{title:'문제은행',adminOnly:'관리자 계정으로 로그인하세요.',username:'아이디',password:'비밀번호',login:'로그인',logout:'로그아웃',privateLibrary:'비공개 · 관리자',textSearch:'텍스트 검색',photoSearch:'사진으로 찾기',query:'검색어',subject:'분야',source:'교재·강좌',search:'검색',photoLabel:'문제 사진',readPhoto:'사진 인식·검색',ocrPolicy:'관리자 전용 · Upstage OCR 호출',recognized:'인식된 문장·수식',searchCorrected:'수정한 텍스트로 다시 검색',noExtraOcr:'이 버튼은 OCR을 다시 호출하지 않습니다.',results:'검색 결과',previous:'이전',next:'다음',selectQuestion:'문제를 선택하면 본문을 확인할 수 있습니다.',footer:'문제·번역·풀이의 검토 상태는 각 항목에 표시됩니다.',allSubjects:'전체 분야',allSources:'전체 교재·강좌',placeholder:'문제의 문장, 수식, 문항 번호',loading:'불러오는 중…',empty:'검색 결과가 없습니다.',review:'검토 대기',unresolved:'원문 확인 사항 있음',solutions:'풀이 보기',recommendations:'비슷한 문제',pdf:'원본 PDF',figures:'원문·그림',noSolutions:'이 문항에 저장된 풀이가 아직 없습니다.',sourceSolution:'원문 해설',originalDraft:'보완 풀이 초안',ocrWarning:'인식 결과와 후보 문제의 수식·수치를 확인하세요.',privateError:'관리자 계정이 필요합니다.',ocrUnavailable:'현재 사진 인식을 사용할 수 없습니다.',network:'요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요.',badLogin:'아이디 또는 비밀번호를 확인하세요.',imageSize:'PNG·JPEG·WebP 이미지(최대 8MB)를 선택하세요.',noLang:'선택한 언어의 본문이 없습니다.',pages:'원문 쪽수',browse:'문항을 선택하세요.',working:'처리 중…',noReco:'조건에 맞는 추천 문제가 없습니다.'},en:{title:'Problem library',adminOnly:'Sign in with an administrator account.',username:'Username',password:'Password',login:'Sign in',logout:'Sign out',privateLibrary:'Private · Administrator',textSearch:'Text search',photoSearch:'Find from photo',query:'Search query',subject:'Subject',source:'Book / course',search:'Search',photoLabel:'Question photo',readPhoto:'Read photo and search',ocrPolicy:'Administrators only · Upstage OCR call',recognized:'Recognized text and equations',searchCorrected:'Search corrected text',noExtraOcr:'This button does not call OCR again.',results:'Results',previous:'Previous',next:'Next',selectQuestion:'Select a question to read its statement.',footer:'Review status is shown for each question, translation and solution.',allSubjects:'All subjects',allSources:'All books / courses',placeholder:'Question text, formula, or problem number',loading:'Loading…',empty:'No results found.',review:'Review pending',unresolved:'Source issues recorded',solutions:'Show solutions',recommendations:'Similar questions',pdf:'Original PDF',figures:'Source and figures',noSolutions:'No solution is stored for this question yet.',sourceSolution:'Source solution',originalDraft:'Supplementary solution draft',ocrWarning:'Compare the recognized formulas and numbers with the candidate questions.',privateError:'An administrator account is required.',ocrUnavailable:'Photo recognition is unavailable.',network:'The request could not be completed. Please try again later.',badLogin:'Check your username and password.',imageSize:'Choose a PNG, JPEG or WebP image up to 8MB.',noLang:'No statement in the selected language.',pages:'Source pages',browse:'Select a question.',working:'Processing…',noReco:'No matching recommendations.'}};
const SUBJECTS={classical_mechanics:['고전역학','Classical mechanics'],electromagnetism:['전자기학','Electromagnetism'],thermodynamics:['열역학','Thermodynamics'],optics:['광학','Optics'],quantum_mechanics:['양자역학','Quantum mechanics'],relativity:['상대론','Relativity'],statistical_mechanics:['통계역학','Statistical mechanics'],oscillations_waves:['진동·파동','Oscillations and waves'],mathematical_methods:['수리물리','Mathematical methods'],astronomy_astrophysics:['천문·천체물리','Astronomy / astrophysics'],mixed:['종합','Mixed']};
Object.assign(COPY.ko,{retryLoad:'다시 불러오기'});Object.assign(COPY.en,{retryLoad:'Try loading again'});
const state={token:sessionStorage.getItem('hlBankToken')||'',lang:localStorage.getItem('hlBankLang')||'ko',theme:localStorage.getItem('hlBankTheme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'),user:null,sources:[],question:null,offset:0,hasMore:false,mode:'text',request:0,identifyRequest:0,detailRequest:0,relatedRequest:0,bootstrapRequest:0,bootstrapErrorCode:null,session:0,controllers:new Set(),urls:[]};
if(!COPY[state.lang])state.lang='ko';
const tr=k=>COPY[state.lang][k]||k;
function applyTheme(){document.documentElement.dataset.theme=state.theme;$('favicon').href='/favicon-'+state.theme+'.svg';$('theme').setAttribute('aria-label',state.lang==='ko'?'테마 전환':'Toggle theme');}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function message(key,error=false){$('message').textContent=key?tr(key):'';$('message').classList.toggle('error',error);}
function errorText(error){if(error.code==='login_required'||error.code==='admin_required')return tr('privateError');if(/ocr/.test(error.code||''))return tr('ocrUnavailable');return tr('network');}
function bootstrapError(error=null){
  state.bootstrapErrorCode=error?(error.code||'network'):null;
  $('bootstrapStatus').hidden=!error;$('bootstrapMessage').textContent=error?errorText(error):'';
}
async function api(path,{method='GET',body,signal}={}){
  const target=new URL(path,window.location.href);
  if(target.origin!==window.location.origin||!/^\/(?:auth\/|api\/problem-bank(?:\/|$))/.test(target.pathname))throw new Error('invalid_api_path');
  const token=state.token,session=state.session,controller=new AbortController();state.controllers.add(controller);
  const abort=()=>controller.abort();signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted)controller.abort();
  const current=()=>{if(session!==state.session||token!==state.token)throw new DOMException('Stale private request','AbortError');};
  try{
    const headers={};if(token)headers.Authorization='Bearer '+token;if(body&&!(body instanceof FormData))headers['Content-Type']='application/json';
    const response=await fetch(target.pathname+target.search,{method,headers,body:body instanceof FormData?body:body?JSON.stringify(body):undefined,signal:controller.signal,cache:'no-store',credentials:'omit'});
    current();
    if(!response.ok){let data={};try{data=await response.json();}catch{}current();const e=new Error('request_failed');e.code=data.error;e.status=response.status;if((e.status===401||e.status===403)&&path!=='/auth/login')signOut(false);throw e;}
    const data=await (response.headers.get('Content-Type')?.includes('application/json')?response.json():response.blob());current();return data;
  }finally{state.controllers.delete(controller);signal?.removeEventListener('abort',abort);}
}
function translate(){
  document.documentElement.lang=state.lang;applyTheme();
  document.title=tr('title')+' · HaslaLab';$('language').value=state.lang;$('query').placeholder=tr('placeholder');$('logout').textContent=tr('logout');
  document.querySelectorAll('[data-i18n]').forEach(el=>el.textContent=tr(el.dataset.i18n));
  if(state.bootstrapErrorCode)$('bootstrapMessage').textContent=errorText({code:state.bootstrapErrorCode});
  const selected=$('subject').value;$('subject').innerHTML='<option value="">'+esc(tr('allSubjects'))+'</option>'+Object.entries(SUBJECTS).map(([key,n])=>`<option value="${key}">${esc(n[state.lang==='ko'?0:1])}</option>`).join('');$('subject').value=selected;
  renderSources();
}
function renderSources(){const selected=$('source').value;$('source').innerHTML='<option value="">'+esc(tr('allSources'))+'</option>'+state.sources.map(s=>`<option value="${esc(s.id)}">${esc(s.title)}</option>`).join('');$('source').value=selected;}
function math(root){if(window.renderMathInElement)renderMathInElement(root,{delimiters:[{left:'$$',right:'$$',display:true},{left:'\\[',right:'\\]',display:true},{left:'$',right:'$',display:false},{left:'\\(',right:'\\)',display:false}],throwOnError:false,trust:false,strict:'ignore',maxExpand:1000,maxSize:30});}
// HTML is never accepted from a statement. All content is escaped before a small
// Markdown subset (headings, paragraphs, tables) and trusted KaTeX are applied.
function prose(text){
  const codeBlocks=[],codeProtected=String(text||'').replace(/```[^\n]*\n([\s\S]*?)```/g,(_,code)=>`\uE002${codeBlocks.push(code)-1}\uE003`);
  const maths=[];const protectedText=codeProtected.replace(/\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$(?:\\.|[^$\n])*\$/g,m=>{const i=maths.push(m)-1;return `\uE000${i}\uE001`;});
  const restore=s=>esc(s).replace(/\uE000(\d+)\uE001/g,(_,i)=>esc(maths[+i]||''));
  const lines=protectedText.split('\n');let html='',paragraph=[];
  const flush=()=>{if(paragraph.length){html+='<p>'+restore(paragraph.join('\n'))+'</p>';paragraph=[];}};
  for(let i=0;i<lines.length;i++){
    const line=lines[i];
    const codeBlock=line.trim().match(/^\uE002(\d+)\uE003$/);
    if(codeBlock){flush();html+='<pre><code>'+esc(codeBlocks[+codeBlock[1]]||'')+'</code></pre>';}
    else if(line.trim().startsWith('|')&&i+1<lines.length&&/^\s*\|?\s*:?-{3,}/.test(lines[i+1])){
      flush();const split=s=>s.trim().replace(/^\||\|$/g,'').split('|').map(x=>restore(x.trim()));
      const head=split(line);let table='<div class="table-wrap"><table><thead><tr>'+head.map(c=>'<th>'+c+'</th>').join('')+'</tr></thead><tbody>';i++;
      while(i+1<lines.length&&lines[i+1].trim().startsWith('|')){i++;table+='<tr>'+split(lines[i]).map(c=>'<td>'+c+'</td>').join('')+'</tr>';}
      html+=table+'</tbody></table></div>';
    }else if(/^#{1,4}\s/.test(line)){flush();const n=Math.min(4,line.match(/^#+/)[0].length+1);html+=`<h${n}>${restore(line.replace(/^#+\s*/,''))}</h${n}>`;}
    else if(!line.trim())flush();else paragraph.push(line);
  }flush();return html;
}
function releaseImages(){for(const url of state.urls)URL.revokeObjectURL(url);state.urls=[];}
async function restoreSession(){
  if(!state.token)return;
  const job=++state.bootstrapRequest,session=state.session,token=state.token;
  const current=()=>job===state.bootstrapRequest&&session===state.session&&token===state.token;
  bootstrapError();$('retryBootstrap').disabled=true;
  try{
    const data=await api('/auth/me');if(!current())return;
    if(data.user?.role!=='admin'){signOut(false);$('loginMessage').textContent=tr('privateError');return;}
    state.user=data.user;await showLibrary();
  }catch(error){if(error.name!=='AbortError'&&current())bootstrapError(error);}
  finally{if(current())$('retryBootstrap').disabled=false;}
}
async function showLibrary(){
  if(!state.token||state.user?.role!=='admin')return false;
  const job=++state.bootstrapRequest,session=state.session,token=state.token;
  const current=()=>job===state.bootstrapRequest&&session===state.session&&token===state.token;
  bootstrapError();$('retryBootstrap').disabled=true;
  $('loginPanel').hidden=true;$('library').hidden=false;$('logout').hidden=false;$('account').textContent=state.user.nickname||state.user.username;
  $('photoMode').disabled=true;
  try{
    const [status,data]=await Promise.all([api('/api/problem-bank/status'),api('/api/problem-bank/sources')]);if(!current())return false;
    state.sources=data.sources;renderSources();
    $('counts').textContent=state.lang==='ko'?`${Number(status.questions).toLocaleString()}문항 · 한영 본문 ${Number(status.language_bodies).toLocaleString()}개 · 검토 대기 자료`:`${Number(status.questions).toLocaleString()} questions · ${Number(status.language_bodies).toLocaleString()} language versions · review pending`;
    $('photoMode').disabled=!status.ocr_available;await search(true);return current();
  }catch(error){if(error.name!=='AbortError'&&current())bootstrapError(error);return false;}
  finally{if(current())$('retryBootstrap').disabled=false;}
}
function signOut(remote=true){
  const token=state.token;state.session++;state.request++;state.identifyRequest++;state.detailRequest++;state.relatedRequest++;state.bootstrapRequest++;
  for(const controller of state.controllers)controller.abort();state.controllers.clear();
  state.token='';state.user=null;state.sources=[];state.question=null;state.offset=0;state.hasMore=false;sessionStorage.removeItem('hlBankToken');releaseImages();
  bootstrapError();$('retryBootstrap').disabled=false;
  $('library').hidden=true;$('loginPanel').hidden=false;$('logout').hidden=true;$('account').textContent='';$('loginForm').reset();$('photoForm').reset();
  for(const id of ['results','detail','counts','resultCount','message','loginMessage'])$(id).textContent='';
  $('query').value='';$('recognized').value='';$('recognizedPanel').hidden=true;$('subject').value='';$('source').value='';renderSources();$('previous').disabled=true;$('next').disabled=true;
  state.mode='text';$('photoForm').hidden=true;$('photoForm').querySelector('button').disabled=false;$('retryText').disabled=false;
  for(const mode of ['text','photo']){$(mode+'Mode').classList.toggle('selected',mode==='text');$(mode+'Mode').setAttribute('aria-selected',String(mode==='text'));}
  // Revoke after clearing local state. It must not be aborted with the old
  // private reads, and its delayed response must never affect a newer session.
  if(remote&&token)fetch('/auth/logout',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:'{}',cache:'no-store',credentials:'omit'}).catch(()=>{});
}
function params(){const p=new URLSearchParams({lang:state.lang,limit:'20',offset:String(state.offset)});for(const key of ['subject','source'])if($(key).value)p.set(key,$(key).value);return p;}
function previewText(text){let value=String(text||'').split(/\n\s*\n/)[0].replace(/\$\$/g,'$').replace(/\\\[/g,'\\(').replace(/\\\]/g,'\\)').replace(/\s+/g,' ');const dollars=[...value.matchAll(/(?<!\\)\$/g)];if(dollars.length%2)value=value.slice(0,dollars.at(-1).index);return value;}
function renderResults(items){
  $('results').innerHTML=items.length?items.map(x=>`<button class="result${state.question===x.id?' active':''}" data-question="${esc(x.id)}"><span class="source">${esc(x.source_title)}</span><strong>${esc(x.original_number)}${x.unresolved_source?' · '+esc(tr('unresolved')):''}</strong><span class="snippet">${esc(previewText(x.snippet))}</span></button>`).join(''):`<p style="padding:18px" class="muted">${esc(tr('empty'))}</p>`;
  $('resultCount').textContent=items.length?`${state.offset+1}–${state.offset+items.length}`:'0';$('previous').disabled=state.offset===0;$('next').disabled=!state.hasMore||state.offset>=300;
  $('results').querySelectorAll('[data-question]').forEach(el=>el.addEventListener('click',()=>selectQuestion(el.dataset.question)));math($('results'));
}
async function search(reset=false){if(reset)state.offset=0;const request=++state.request;message('loading');
  try{const p=params();p.set('q',$('query').value);const data=await api('/api/problem-bank/search?'+p);if(request!==state.request)return;state.hasMore=data.has_more;renderResults(data.items);message('');}
  catch(e){if(e.name!=='AbortError'&&request===state.request){$('message').textContent=errorText(e);$('message').classList.add('error');}}
}
async function identify(text,file){const request=++state.request,job=++state.identifyRequest;message('working');$('photoForm').querySelector('button').disabled=true;$('retryText').disabled=true;
  try{let body;if(file){body=new FormData();body.set('image',file);for(const key of ['lang','subject','source','limit']){const value=params().get(key);if(value)body.set(key,value);}}else body={text,lang:state.lang,subject:$('subject').value||undefined,source:$('source').value||undefined,limit:20};
    const data=await api('/api/problem-bank/identify',{method:'POST',body});if(request!==state.request)return;state.offset=0;state.hasMore=false;if(data.recognized_text){$('recognized').value=data.recognized_text;$('recognizedPanel').hidden=false;}renderResults(data.candidates||data.items);message('ocrWarning');
  }catch(e){if(e.name!=='AbortError'&&request===state.request){$('message').textContent=errorText(e);$('message').classList.add('error');}}finally{if(job===state.identifyRequest){$('photoForm').querySelector('button').disabled=false;$('retryText').disabled=false;}}
}
async function loadFigures(container,assets,questionId,view=state.detailRequest){
  const current=()=>state.question===questionId&&view===state.detailRequest&&container?.isConnected;
  for(const a of assets){if(!current())return;try{const blob=await api(a.url);if(!current())return;const url=URL.createObjectURL(blob);state.urls.push(url);const fig=document.createElement('figure');fig.className='figure';const img=document.createElement('img');img.src=url;img.alt=tr('figures');img.loading='lazy';fig.append(img);const caption=document.createElement('figcaption');caption.textContent=tr('pages')+': '+[...new Set((a.spans||[]).map(s=>s.page))].join(', ');fig.append(caption);container.append(fig);}catch(e){if(!current()||e.name==='AbortError')return;const p=document.createElement('p');p.textContent=tr('network');container.append(p);}}
}
async function selectQuestion(id){const view=++state.detailRequest;state.relatedRequest++;state.question=id;releaseImages();$('detail').innerHTML=`<p class="muted">${esc(tr('loading'))}</p>`;document.querySelectorAll('.result').forEach(el=>el.classList.toggle('active',el.dataset.question===id));
  try{const {question:q}=await api(`/api/problem-bank/questions/${id}?lang=${state.lang}`);if(state.question!==id||view!==state.detailRequest)return;
    const version=q.selected_version;$('detail').innerHTML=`<p class="source-title">${esc(q.source.title)}</p><h2>${esc(q.original_number)}</h2><div class="meta"><span class="badge">${esc(tr('review'))}</span>${q.context?.unresolved_source?`<span class="badge">${esc(tr('unresolved'))}</span>`:''}${q.subjects.map(s=>`<span class="muted">${esc(SUBJECTS[s]?.[state.lang==='ko'?0:1]||s)}</span>`).join('')}</div><div class="prose">${prose(version?.text||tr('noLang'))}</div><div class="actions"><button id="showSolutions">${esc(tr('solutions'))}</button><button id="showRecommendations">${esc(tr('recommendations'))}</button><button id="sourcePdf">${esc(tr('pdf'))}</button></div><div class="figures"><details id="sourceFigures"><summary>${esc(tr('figures'))} (${q.assets.length})</summary><div id="questionFigures"></div></details></div><div id="related"></div>`;
    math($('detail'));$('showSolutions').addEventListener('click',()=>showSolutions(id));$('showRecommendations').addEventListener('click',()=>showRecommendations(id));$('sourcePdf').addEventListener('click',async()=>{try{const blob=await api(`/api/problem-bank/sources/${q.source_id}/pdf`);if(state.question!==id||view!==state.detailRequest)return;const url=URL.createObjectURL(blob);state.urls.push(url);const link=document.createElement('a');link.href=url;const filename=(q.source.title||'source').replace(/[\\/:*?"<>|]/g,'_').slice(0,180);link.download=/\.pdf$/i.test(filename)?filename:filename+'.pdf';link.click();}catch(e){if(e.name!=='AbortError'&&state.question===id&&view===state.detailRequest)$('message').textContent=errorText(e);}});
    if(q.context_links?.length){const button=document.createElement('button');button.textContent=(state.lang==='ko'?'참조 문제':'Referenced questions')+' ('+q.context_links.length+')';button.addEventListener('click',()=>showContexts(id));$('detail').querySelector('.actions').append(button);}
    let loaded=false;const figures=$('sourceFigures');figures.addEventListener('toggle',()=>{if(!loaded&&figures.open&&view===state.detailRequest){loaded=true;loadFigures($('questionFigures'),q.assets,id,view);}});
  }catch(e){if(e.name!=='AbortError'&&state.question===id&&view===state.detailRequest)$('detail').innerHTML=`<p class="error">${esc(errorText(e))}</p>`;}
}
async function showSolutions(id){
  const related=$('related'),view=state.detailRequest,action=++state.relatedRequest;
  const current=()=>state.question===id&&view===state.detailRequest&&action===state.relatedRequest&&related.isConnected;
  related.innerHTML=`<p>${esc(tr('loading'))}</p>`;
  try{const data=await api(`/api/problem-bank/questions/${id}/solutions?lang=${state.lang}`);if(!current())return;
    related.innerHTML='<section class="solutions"><h3>'+esc(tr('solutions'))+'</h3>'+(data.solutions.length?data.solutions.map((s,i)=>`<section class="solution-entry"><p><span class="badge">${esc(tr(s.authorship==='source_transcription'?'sourceSolution':'originalDraft'))}</span> <span class="muted">${esc(tr('review'))} · ${esc(s.kind)}</span></p><div class="prose">${prose(s.selected_version?.text||tr('noLang'))}</div><details data-solution-figures="${i}"><summary>${esc(tr('figures'))} (${s.assets.length})</summary><div></div></details></section>`).join(''):`<p>${esc(tr('noSolutions'))}</p>` )+'</section>';math(related);
    related.querySelectorAll('[data-solution-figures]').forEach(el=>{let loaded=false;el.addEventListener('toggle',()=>{if(el.open&&!loaded&&current()){loaded=true;loadFigures(el.querySelector('div'),data.solutions[+el.dataset.solutionFigures].assets,id,view);}});});
  }catch(e){if(e.name!=='AbortError'&&current())related.textContent=errorText(e);}
}
async function showRecommendations(id){
  const related=$('related'),view=state.detailRequest,action=++state.relatedRequest;
  const current=()=>state.question===id&&view===state.detailRequest&&action===state.relatedRequest&&related.isConnected;
  related.textContent=tr('loading');
  try{const data=await api(`/api/problem-bank/questions/${id}/recommendations?lang=${state.lang}&limit=8`);if(!current())return;
    related.innerHTML='<section class="solutions recommendations"><h3>'+esc(tr('recommendations'))+'</h3>'+(data.items.length?data.items.map(x=>`<button data-question="${esc(x.id)}">${esc(x.source_title)} · ${esc(x.original_number)}<br><span class="muted">${esc(x.snippet.slice(0,140))}</span></button>`).join(''):`<p>${esc(tr('noReco'))}</p>` )+'</section>';related.querySelectorAll('[data-question]').forEach(el=>el.addEventListener('click',()=>selectQuestion(el.dataset.question)));math(related);
  }catch(e){if(e.name!=='AbortError'&&current())related.textContent=errorText(e);}
}
async function showContexts(id){
  const related=$('related'),view=state.detailRequest,action=++state.relatedRequest;
  const current=()=>state.question===id&&view===state.detailRequest&&action===state.relatedRequest&&related.isConnected;
  related.textContent=tr('loading');
  try{
    const data=await api(`/api/problem-bank/questions/${id}/context?lang=${state.lang}`);if(!current())return;
    related.innerHTML='<section class="solutions"><h3>'+(state.lang==='ko'?'참조 문제':'Referenced questions')+'</h3>'+data.contexts.map((q,i)=>`<section class="solution-entry"><p class="muted">${esc(q.source.title)} · ${esc(q.original_number)}</p><div class="prose">${prose(q.selected_version?.text||tr('noLang'))}</div><button data-open-reference="${esc(q.id)}">${state.lang==='ko'?'이 문제 열기':'Open question'}</button><details data-context-figures="${i}"><summary>${esc(tr('figures'))} (${q.assets.length})</summary><div></div></details></section>`).join('')+(data.truncated?`<p class="muted">${state.lang==='ko'?'참조 문제 일부만 표시됩니다. 각 문제에서 다음 참조를 확인할 수 있습니다.':'Some references are omitted here. Open a question to inspect further references.'}</p>`:'')+'</section>';
    math(related);related.querySelectorAll('[data-open-reference]').forEach(el=>el.addEventListener('click',()=>selectQuestion(el.dataset.openReference)));
    related.querySelectorAll('[data-context-figures]').forEach(el=>{let loaded=false;el.addEventListener('toggle',()=>{if(el.open&&!loaded&&current()){loaded=true;loadFigures(el.querySelector('div'),data.contexts[+el.dataset.contextFigures].assets,id,view);}});});
  }catch(e){if(e.name!=='AbortError'&&current())related.textContent=errorText(e);}
}
$('loginForm').addEventListener('submit',async e=>{e.preventDefault();state.bootstrapRequest++;bootstrapError();const button=e.currentTarget.querySelector('button');button.disabled=true;$('loginMessage').textContent=tr('working');try{const form=new FormData(e.currentTarget),data=await api('/auth/login',{method:'POST',body:{username:form.get('username'),password:form.get('password')}});state.token=data.token;state.user=data.user;sessionStorage.setItem('hlBankToken',data.token);$('loginForm').reset();$('loginMessage').textContent='';await showLibrary();}catch(e){if(e.name!=='AbortError')$('loginMessage').textContent=e.status===401?tr('badLogin'):errorText(e);}finally{button.disabled=false;}});
$('retryBootstrap').addEventListener('click',()=>state.user?showLibrary():restoreSession());
$('logout').addEventListener('click',()=>signOut());$('theme').addEventListener('click',()=>{state.theme=state.theme==='dark'?'light':'dark';localStorage.setItem('hlBankTheme',state.theme);applyTheme();});
$('language').addEventListener('change',async()=>{const selected=state.question;state.lang=$('language').value;const language=state.lang;state.request++;state.detailRequest++;state.relatedRequest++;releaseImages();$('detail').textContent='';localStorage.setItem('hlBankLang',state.lang);translate();if(state.user){const ready=await showLibrary();if(ready&&selected&&state.user&&state.lang===language)await selectQuestion(selected);}});
$('searchForm').addEventListener('submit',e=>{e.preventDefault();search(true);});$('previous').addEventListener('click',()=>{state.offset=Math.max(0,state.offset-20);search();});$('next').addEventListener('click',()=>{state.offset=Math.min(300,state.offset+20);search();});
for(const mode of ['text','photo'])$(mode+'Mode').addEventListener('click',()=>{state.mode=mode;$('photoForm').hidden=mode!=='photo';for(const key of ['text','photo']){$(key+'Mode').classList.toggle('selected',key===mode);$(key+'Mode').setAttribute('aria-selected',String(key===mode));}});
$('photoForm').addEventListener('submit',e=>{e.preventDefault();const file=$('photo').files[0];if(!file||!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>8*1024*1024){message('imageSize',true);return;}identify(null,file);});$('retryText').addEventListener('click',()=>identify($('recognized').value));
translate();restoreSession();
