const $=id=>document.getElementById(id);
const BANK_ORIGIN='https://haslalab-problem-bank.haslalab.workers.dev';
const launch=new URL(window.location.href);
const EMBED=(()=>{try{return launch.searchParams.get('embed')==='1'&&window.parent&&window.parent!==window&&window.parent.location.origin===launch.origin&&['haslalab.org','www.haslalab.org','haslaedu.github.io','localhost','127.0.0.1','[::1]'].includes(launch.hostname);}catch{return false;}})();
const API_ORIGIN=EMBED?BANK_ORIGIN:launch.origin;
const sharedToken=()=>{try{return localStorage.getItem('hlCmTok')||'';}catch{return '';}};
const COPY={ko:{title:'문제은행',adminOnly:'관리자 계정으로 로그인하세요.',username:'아이디',password:'비밀번호',login:'로그인',logout:'로그아웃',privateLibrary:'비공개 · 관리자',textSearch:'텍스트 검색',photoSearch:'사진으로 찾기',query:'검색어',subject:'분야',source:'교재·강좌',search:'검색',photoLabel:'문제 사진',readPhoto:'사진 인식·검색',ocrPolicy:'관리자 전용 · Upstage OCR 호출',recognized:'인식된 문장·수식',searchCorrected:'수정한 텍스트로 다시 검색',noExtraOcr:'이 버튼은 OCR을 다시 호출하지 않습니다.',results:'검색 결과',previous:'이전',next:'다음',selectQuestion:'문제를 선택하면 본문을 확인할 수 있습니다.',footer:'문제·번역·풀이의 검토 상태는 각 항목에 표시됩니다.',allSubjects:'전체 분야',allSources:'전체 교재·강좌',placeholder:'문제의 문장, 수식, 문항 번호',loading:'불러오는 중…',empty:'검색 결과가 없습니다.',review:'검토 대기',unresolved:'원문 확인 사항 있음',solutions:'풀이 보기',recommendations:'비슷한 문제',pdf:'원본 PDF',figures:'원문·그림',noSolutions:'이 문항에 저장된 풀이가 아직 없습니다.',sourceSolution:'원문 해설',originalDraft:'보완 풀이 초안',ocrWarning:'인식 결과와 후보 문제의 수식·수치를 확인하세요.',privateError:'관리자 계정이 필요합니다.',ocrUnavailable:'현재 사진 인식을 사용할 수 없습니다.',network:'요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요.',badLogin:'아이디 또는 비밀번호를 확인하세요.',imageSize:'PNG·JPEG·WebP 이미지(최대 8MB)를 선택하세요.',noLang:'선택한 언어의 본문이 없습니다.',pages:'원문 쪽수',browse:'문항을 선택하세요.',working:'처리 중…',noReco:'조건에 맞는 추천 문제가 없습니다.'},en:{title:'Problem library',adminOnly:'Sign in with an administrator account.',username:'Username',password:'Password',login:'Sign in',logout:'Sign out',privateLibrary:'Private · Administrator',textSearch:'Text search',photoSearch:'Find from photo',query:'Search query',subject:'Subject',source:'Book / course',search:'Search',photoLabel:'Question photo',readPhoto:'Read photo and search',ocrPolicy:'Administrators only · Upstage OCR call',recognized:'Recognized text and equations',searchCorrected:'Search corrected text',noExtraOcr:'This button does not call OCR again.',results:'Results',previous:'Previous',next:'Next',selectQuestion:'Select a question to read its statement.',footer:'Review status is shown for each question, translation and solution.',allSubjects:'All subjects',allSources:'All books / courses',placeholder:'Question text, formula, or problem number',loading:'Loading…',empty:'No results found.',review:'Review pending',unresolved:'Source issues recorded',solutions:'Show solutions',recommendations:'Similar questions',pdf:'Original PDF',figures:'Source and figures',noSolutions:'No solution is stored for this question yet.',sourceSolution:'Source solution',originalDraft:'Supplementary solution draft',ocrWarning:'Compare the recognized formulas and numbers with the candidate questions.',privateError:'An administrator account is required.',ocrUnavailable:'Photo recognition is unavailable.',network:'The request could not be completed. Please try again later.',badLogin:'Check your username and password.',imageSize:'Choose a PNG, JPEG or WebP image up to 8MB.',noLang:'No statement in the selected language.',pages:'Source pages',browse:'Select a question.',working:'Processing…',noReco:'No matching recommendations.'}};
const SUBJECTS={classical_mechanics:['고전역학','Classical mechanics'],electromagnetism:['전자기학','Electromagnetism'],thermodynamics:['열역학','Thermodynamics'],optics:['광학','Optics'],quantum_mechanics:['양자역학','Quantum mechanics'],relativity:['상대론','Relativity'],statistical_mechanics:['통계역학','Statistical mechanics'],oscillations_waves:['진동·파동','Oscillations and waves'],mathematical_methods:['수리물리','Mathematical methods'],astronomy_astrophysics:['천문·천체물리','Astronomy / astrophysics'],mixed:['종합','Mixed']};
Object.assign(COPY.ko,{retryLoad:'다시 불러오기',siteLogin:'하슬라랩에서 로그인',authUnavailable:'로그인 서버에 연결하지 못했습니다. 다시 불러오기를 눌러 주세요.',bankUnavailable:'문제 자료를 불러오지 못했습니다. 다시 불러오기를 눌러 주세요.',rateLimited:'요청 횟수를 초과했습니다. 잠시 후 다시 시도하세요.'});Object.assign(COPY.en,{retryLoad:'Try loading again',siteLogin:'Sign in on HaslaLab',authUnavailable:'The sign-in service is unavailable. Try loading again.',bankUnavailable:'The problem data could not be loaded. Try loading again.',rateLimited:'Too many requests. Please try again later.'});
Object.assign(COPY.ko,{publicLibrary:'물리 · 천문 문제',guest:'게스트',collection:'문제 모음',allCollections:'물리·천문 전체',physics:'물리학',astronomy:'천문학',stars:'난이도',allStars:'난이도 전체',provisional:'잠정',difficulty:'난이도',photoAdmin:'사진 인식은 관리자 계정에서 사용할 수 있습니다.',sourceCrops:'원문 캡처',referenceFigures:'참고 그림',givenFigures:'문제 그림',limitedResults:'검색 결과 일부를 표시합니다. 교재나 분야로 범위를 좁혀 주세요.'});
Object.assign(COPY.en,{publicLibrary:'Physics · Astronomy',guest:'Guest',collection:'Collection',allCollections:'Physics and astronomy',physics:'Physics',astronomy:'Astronomy',stars:'Difficulty',allStars:'All difficulties',provisional:'Provisional',difficulty:'Difficulty',photoAdmin:'Photo recognition is available to administrators.',sourceCrops:'Source captures',referenceFigures:'Reference figures',givenFigures:'Problem figures',limitedResults:'Showing part of the search results. Narrow the source or subject to find more.'});
Object.assign(SUBJECTS,{special_relativity:['특수상대론','Special relativity'],general_relativity:['일반상대론','General relativity']});
Object.assign(COPY.ko,{feedback:'난이도 평가',feedbackNote:'사용자가 직접 남긴 풀이 기록입니다.',feedbackEmpty:'아직 사용자 평가가 없습니다.',feedbackSave:'평가 저장',feedbackSaved:'평가를 저장했습니다.',feedbackLogin:'로그인하고 평가 남기기',feedbackOutcome:'풀이 상태',feedbackMinutes:'풀이 시간(분, 선택)',not_attempted:'아직 풀지 않음',solved:'풀었음',partial:'일부 해결',unsolved:'해결하지 못함',chooseRating:'별점 선택',invalidFeedback:'별점과 풀이 시간을 확인하세요.',loginNeeded:'로그인한 뒤 이용할 수 있습니다.'});
Object.assign(COPY.en,{feedback:'Rate difficulty',feedbackNote:'These are self-reported solving records.',feedbackEmpty:'No user ratings yet.',feedbackSave:'Save rating',feedbackSaved:'Rating saved.',feedbackLogin:'Sign in to leave a rating',feedbackOutcome:'Solving outcome',feedbackMinutes:'Time spent (minutes, optional)',not_attempted:'Not attempted',solved:'Solved',partial:'Partly solved',unsolved:'Unsolved',chooseRating:'Choose a rating',invalidFeedback:'Check the rating and solving time.',loginNeeded:'Sign in to use this feature.'});
COPY.ko.recommendations='추천 문제';COPY.en.recommendations='Recommended problems';
const DIFFICULTY_REASONS={source_level:['교재·강좌 수준','Source level'],calculus:['미적분','Calculus'],linear_algebra:['선형대수','Linear algebra'],differential_equations:['미분방정식','Differential equations'],advanced_mathematics:['고급 수학','Advanced mathematics'],approximation:['근사 방법','Approximation methods'],concept_integration:['여러 개념의 결합','Combining concepts'],nontrivial_reasoning:['여러 단계의 추론','Multi-step reasoning'],reference_context_pending:['참고 자료 검토 중','Reference context under review']};
const state={token:EMBED?sharedToken():sessionStorage.getItem('hlBankToken')||'',lang:(EMBED&&launch.searchParams.get('lang'))||localStorage.getItem('hlBankLang')||'ko',theme:(EMBED&&['light','dark'].includes(launch.searchParams.get('theme'))?launch.searchParams.get('theme'):localStorage.getItem('hlBankTheme'))||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'),user:null,sources:[],question:null,offset:0,hasMore:false,mode:'text',request:0,identifyRequest:0,detailRequest:0,relatedRequest:0,bootstrapRequest:0,bootstrapErrorCode:null,session:0,controllers:new Set(),urls:[]};
if(!COPY[state.lang])state.lang='ko';
Object.assign(state,{ocrAvailable:false,cursor:null,nextCursor:null,cursorHistory:[],pageSize:0,limitedResults:false,feedbackRequest:0});
const tr=k=>COPY[state.lang][k]||k;
function applyTheme(){document.documentElement.dataset.theme=state.theme;$('favicon').href='./favicon-'+state.theme+'.svg';$('theme').setAttribute('aria-label',state.lang==='ko'?'테마 전환':'Toggle theme');}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function message(key,error=false){$('message').textContent=key?tr(key):'';$('message').classList.toggle('error',error);}
function errorText(error){if(error.code==='login_required')return tr('loginNeeded');if(error.code==='admin_required')return tr('privateError');if(/ocr/.test(error.code||''))return tr('ocrUnavailable');if(/^(?:auth_|invalid_auth_response)/.test(error.code||''))return tr('authUnavailable');if(/^problem_bank_/.test(error.code||''))return tr('bankUnavailable');if(error.code==='rate_limited')return tr('rateLimited');return tr('network');}
function bootstrapError(error=null){
  state.bootstrapErrorCode=error?(error.code||'network'):null;
  $('bootstrapStatus').hidden=!error;$('bootstrapMessage').textContent=error?errorText(error):'';
}
async function api(path,{method='GET',body,signal}={}){
  const target=new URL(path,API_ORIGIN+'/');
  if(target.origin!==API_ORIGIN||!/^\/(?:auth\/|api\/problem-bank(?:\/|$))/.test(target.pathname))throw new Error('invalid_api_path');
  const token=state.token,session=state.session,controller=new AbortController();state.controllers.add(controller);
  const abort=()=>controller.abort();signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted)controller.abort();
  const current=()=>{if(session!==state.session||token!==state.token)throw new DOMException('Stale private request','AbortError');};
  try{
    const headers={};if(token)headers.Authorization='Bearer '+token;if(body&&!(body instanceof FormData))headers['Content-Type']='application/json';
    const response=await fetch((EMBED?target.origin:'')+target.pathname+target.search,{method,headers,body:body instanceof FormData?body:body?JSON.stringify(body):undefined,signal:controller.signal,cache:'no-store',credentials:'omit'});
    current();
    if(!response.ok){let data={};try{data=await response.json();}catch{}current();const e=new Error('request_failed');e.code=data.error;e.status=response.status;if(e.status===401&&token&&path!=='/auth/login')signOut(false);throw e;}
    const data=await (response.headers.get('Content-Type')?.includes('application/json')?response.json():response.blob());current();return data;
  }finally{state.controllers.delete(controller);signal?.removeEventListener('abort',abort);}
}
function translate(){
  document.documentElement.lang=state.lang;applyTheme();
  document.title=tr('title')+' · HaslaLab';$('language').value=state.lang;$('query').placeholder=tr('placeholder');$('logout').textContent=tr('logout');
  if(EMBED)$('siteLogin').href='../../?lang='+state.lang+'#/login';
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
  // Public browsing does not wait for a separate authentication round trip.
  // Status supplies an optional verified user and role-scoped OCR availability.
  return showLibrary();
}
async function showLibrary(){
  const job=++state.bootstrapRequest,session=state.session,token=state.token;
  const current=()=>job===state.bootstrapRequest&&session===state.session&&token===state.token;
  bootstrapError();$('retryBootstrap').disabled=true;
  $('loginPanel').hidden=true;$('library').hidden=false;
  state.ocrAvailable=false;$('photoMode').disabled=true;$('photoAccess').hidden=false;
  try{
    const [status,data]=await Promise.all([api('/api/problem-bank/status'),api('/api/problem-bank/sources')]);if(!current())return false;
    if(Object.hasOwn(status,'user'))state.user=status.user||null;
    $('logout').hidden=!state.user;$('account').textContent=state.user?(state.user.nickname||state.user.username):tr('guest');
    state.sources=data.sources;renderSources();
    $('counts').textContent=state.lang==='ko'?`${Number(status.questions).toLocaleString()}문항 · 한영 본문 ${Number(status.language_bodies).toLocaleString()}개 · 검토 대기 자료`:`${Number(status.questions).toLocaleString()} questions · ${Number(status.language_bodies).toLocaleString()} language versions · review pending`;
    state.ocrAvailable=status.ocr_available===true&&state.user?.role==='admin';$('photoMode').disabled=!state.ocrAvailable;$('photoAccess').hidden=state.ocrAvailable;
    if(!state.ocrAvailable){state.mode='text';$('photoForm').hidden=true;$('recognizedPanel').hidden=true;}
    await search(true);return current();
  }catch(error){if(error.name!=='AbortError'&&current())bootstrapError(error);return false;}
  finally{if(current())$('retryBootstrap').disabled=false;}
}
function signOut(remote=true,reload=true){
  const token=state.token;state.session++;state.request++;state.identifyRequest++;state.detailRequest++;state.relatedRequest++;state.bootstrapRequest++;
  for(const controller of state.controllers)controller.abort();state.controllers.clear();
  state.token='';state.user=null;state.sources=[];state.question=null;state.offset=0;state.hasMore=false;state.ocrAvailable=false;state.cursor=null;state.nextCursor=null;state.cursorHistory=[];if(!EMBED)sessionStorage.removeItem('hlBankToken');releaseImages();
  bootstrapError();$('retryBootstrap').disabled=false;
  $('library').hidden=false;$('loginPanel').hidden=true;$('logout').hidden=true;$('account').textContent=tr('guest');$('loginForm').reset();$('photoForm').reset();$('photoMode').disabled=true;$('photoAccess').hidden=false;
  for(const id of ['results','detail','counts','resultCount','message','loginMessage'])$(id).textContent='';
  $('query').value='';$('recognized').value='';$('recognizedPanel').hidden=true;$('subject').value='';$('source').value='';renderSources();$('previous').disabled=true;$('next').disabled=true;
  state.mode='text';$('photoForm').hidden=true;$('photoForm').querySelector('button').disabled=false;$('retryText').disabled=false;
  for(const mode of ['text','photo']){$(mode+'Mode').classList.toggle('selected',mode==='text');$(mode+'Mode').setAttribute('aria-selected',String(mode==='text'));}
  // Revoke after clearing local state. It must not be aborted with the old
  // private reads, and its delayed response must never affect a newer session.
  if(remote&&token&&!EMBED)fetch('/auth/logout',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:'{}',cache:'no-store',credentials:'omit'}).catch(()=>{});
  if(reload)showLibrary();
}
function params(){const p=new URLSearchParams({lang:state.lang,limit:'20'});if($('query').value.trim())p.set('offset',String(state.offset));else if(state.cursor)p.set('cursor',state.cursor);for(const key of ['subject','source','collection','stars'])if($(key).value)p.set(key,$(key).value);return p;}
function difficultyBadge(item){
  const n=item.stars??item.difficulty?.stars;if(!Number.isInteger(n)||n<1||n>5)return '';
  const provisional=!['reviewed','community_calibrated'].includes(item.difficulty?.status);
  const reasons=difficultyReasons(item);
  return `<span class="difficulty" title="${esc(reasons)}" aria-label="${esc(tr('difficulty'))} ${n}/5${provisional?' · '+esc(tr('provisional')):''}">${'★'.repeat(n)}${'☆'.repeat(5-n)}${provisional?` <small>${esc(tr('provisional'))}</small>`:''}</span>`;
}
function difficultyReasons(item){return (Array.isArray(item.difficulty?.reason_codes)?item.difficulty.reason_codes:[]).map(code=>DIFFICULTY_REASONS[code]?.[state.lang==='ko'?0:1]).filter(Boolean).join(' · ');}
function previewText(text){let value=String(text||'').split(/\n\s*\n/)[0].replace(/\$\$/g,'$').replace(/\\\[/g,'\\(').replace(/\\\]/g,'\\)').replace(/\s+/g,' ');const dollars=[...value.matchAll(/(?<!\\)\$/g)];if(dollars.length%2)value=value.slice(0,dollars.at(-1).index);return value;}
function renderResults(items){
  $('results').innerHTML=items.length?items.map(x=>`<button class="result${state.question===x.id?' active':''}" data-question="${esc(x.id)}"><span class="source">${esc(x.source_title)}</span><strong>${esc(x.original_number)}${x.unresolved_source?' · '+esc(tr('unresolved')):''}</strong>${difficultyBadge(x)}<span class="snippet">${esc(previewText(x.snippet))}</span></button>`).join(''):`<p style="padding:18px" class="muted">${esc(tr('empty'))}</p>`;
  const textSearch=!!$('query').value.trim();$('resultCount').textContent=items.length?`${state.offset+1}–${state.offset+items.length}`:'0';$('previous').disabled=textSearch?state.offset===0:state.cursorHistory.length===0;$('next').disabled=!state.hasMore||(textSearch&&state.offset>=300);$('resultLimit').textContent=state.limitedResults?tr('limitedResults'):'';
  $('results').querySelectorAll('[data-question]').forEach(el=>el.addEventListener('click',()=>selectQuestion(el.dataset.question)));math($('results'));
}
async function search(reset=false){if(reset){state.offset=0;state.cursor=null;state.nextCursor=null;state.cursorHistory=[];}const request=++state.request;message('loading');
  try{const p=params();p.set('q',$('query').value);const data=await api('/api/problem-bank/search?'+p);if(request!==state.request)return;state.nextCursor=/^q_[a-f0-9]{64}$/.test(data.next_cursor||'')?data.next_cursor:null;state.hasMore=!!data.has_more&&($('query').value.trim()||!!state.nextCursor);state.pageSize=data.items.length;state.limitedResults=!!data.limited_results;renderResults(data.items);message('');}
  catch(e){if(e.name!=='AbortError'&&request===state.request){$('message').textContent=errorText(e);$('message').classList.add('error');}}
}
async function identify(text,file){const request=++state.request,job=++state.identifyRequest;message('working');$('photoForm').querySelector('button').disabled=true;$('retryText').disabled=true;
  try{if(file&&!state.ocrAvailable){message('photoAdmin',true);return;}let body;if(file){body=new FormData();body.set('image',file);for(const key of ['lang','subject','source','collection','stars','limit']){const value=params().get(key);if(value)body.set(key,value);}}else body={text,lang:state.lang,subject:$('subject').value||undefined,source:$('source').value||undefined,collection:$('collection').value||undefined,stars:$('stars').value||undefined,limit:20};
    const data=await api('/api/problem-bank/identify',{method:'POST',body});if(request!==state.request)return;state.offset=0;state.hasMore=false;state.cursor=null;state.nextCursor=null;state.cursorHistory=[];state.limitedResults=false;if(data.recognized_text){$('recognized').value=data.recognized_text;$('recognizedPanel').hidden=false;}renderResults(data.candidates||data.items);message('ocrWarning');
  }catch(e){if(e.name!=='AbortError'&&request===state.request){$('message').textContent=errorText(e);$('message').classList.add('error');}}finally{if(job===state.identifyRequest){$('photoForm').querySelector('button').disabled=false;$('retryText').disabled=false;}}
}
async function loadFigures(container,assets,questionId,view=state.detailRequest){
  const current=()=>state.question===questionId&&view===state.detailRequest&&container?.isConnected;
  for(const a of assets){if(!current())return;try{const blob=await api(a.url);if(!current())return;const url=URL.createObjectURL(blob);state.urls.push(url);const fig=document.createElement('figure');fig.className='figure';const img=document.createElement('img');img.src=url;img.alt=a.figure_label?tr('givenFigures')+' '+a.figure_label:tr('givenFigures');img.loading='lazy';if(Number.isSafeInteger(a.width)&&a.width>0)img.width=a.width;if(Number.isSafeInteger(a.height)&&a.height>0)img.height=a.height;fig.append(img);const caption=document.createElement('figcaption');caption.textContent=(a.figure_label?a.figure_label+' · ':'')+tr('pages')+': '+[...new Set((a.spans||[]).map(s=>s.page))].join(', ');fig.append(caption);container.append(fig);}catch(e){if(!current()||e.name==='AbortError')return;const p=document.createElement('p');p.textContent=tr('network');container.append(p);}}
}
function figureGroups(question){
  const variants=Array.isArray(question.figures)?question.figures:[],assets=Array.isArray(question.assets)?question.assets:[];
  const parents=new Set(variants.map(x=>x.parent_asset_id).filter(Boolean)),seen=new Set(),inline=[],reference=[];
  for(const asset of [...variants,...assets.filter(x=>x.role==='figure'&&x.placement!=='source_only'&&!parents.has(x.id))]){
    if(!asset.url||['blocked','hidden','source_only'].includes(asset.placement))continue;
    const key=asset.id||asset.url;if(seen.has(key))continue;seen.add(key);
    (asset.placement==='reference'?reference:inline).push(asset);
  }
  return {inline,reference,raw:question.can_view_source===true?assets.filter(x=>x.role!=='figure'||x.placement==='source_only'):[]};
}
function lazyFigures(details,container,assets,id,view){let loaded=false;details?.addEventListener('toggle',()=>{if(!loaded&&details.open&&view===state.detailRequest&&state.question===id){loaded=true;loadFigures(container,assets,id,view);}});}
function learnReturnHash(){return '#/learn/'+(($('collection').value||launch.searchParams.get('collection'))==='astronomy'?'astronomy':'physics')+'/library';}
function rememberLearningReturn(){try{sessionStorage.setItem('hlCmBack',learnReturnHash());}catch{}}
function feedbackPanel(){
  const login=EMBED?new URL('../../?lang='+state.lang+'#/login',launch).href:'https://haslalab.org/?lang='+state.lang+'#/login';
  return `<details id="difficultyFeedback"><summary>${esc(tr('feedback'))}</summary><p class="muted">${esc(tr('feedbackNote'))}</p><p id="feedbackStats" role="status"></p>${state.user?`<form id="feedbackForm"><label>${esc(tr('stars'))}<select id="feedbackStars" name="stars" required><option value="">${esc(tr('chooseRating'))}</option>${[1,2,3,4,5].map(n=>`<option value="${n}">${'★'.repeat(n)}${'☆'.repeat(5-n)}</option>`).join('')}</select></label><label>${esc(tr('feedbackOutcome'))}<select id="feedbackOutcome" name="outcome">${['not_attempted','solved','partial','unsolved'].map(x=>`<option value="${x}">${esc(tr(x))}</option>`).join('')}</select></label><label>${esc(tr('feedbackMinutes'))}<input id="feedbackMinutes" name="minutes" type="number" min="1" max="1440" step="1"></label><button>${esc(tr('feedbackSave'))}</button></form>`:`<a id="feedbackLogin" href="${esc(login)}" target="_top">${esc(tr('feedbackLogin'))}</a>`}<p id="feedbackMessage" role="status"></p></details>`;
}
async function loadFeedback(id,view=state.detailRequest){
  const action=++state.feedbackRequest,current=()=>state.question===id&&state.detailRequest===view&&state.feedbackRequest===action;
  $('feedbackStats').textContent=tr('loading');
  try{const data=await api(`/api/problem-bank/questions/${id}/feedback`);if(!current())return;
    const mean=Number(data.mean_stars),average=Number.isFinite(mean)&&mean>=1&&mean<=5?mean.toFixed(1):'—';
    $('feedbackStats').textContent=Number(data.count)>0?(state.lang==='ko'?`사용자 ${Number(data.count).toLocaleString()}명 · 평균 ${average}/5`:`${Number(data.count).toLocaleString()} users · mean ${average}/5`):tr('feedbackEmpty');
    if(state.user&&data.own){$('feedbackStars').value=String(data.own.stars);$('feedbackOutcome').value=data.own.outcome;$('feedbackMinutes').value=data.own.minutes??'';}
    return true;
  }catch(error){if(error.name!=='AbortError'&&current())$('feedbackStats').textContent=errorText(error);return false;}
}
async function saveFeedback(id,form,view=state.detailRequest){
  if(!state.user){$('feedbackMessage').textContent=tr('loginNeeded');return;}
  const fields=new FormData(form),stars=Number(fields.get('stars')),outcome=fields.get('outcome'),rawMinutes=fields.get('minutes'),minutes=rawMinutes===null||rawMinutes===''?null:Number(rawMinutes);
  if(!Number.isInteger(stars)||stars<1||stars>5||!['not_attempted','solved','partial','unsolved'].includes(outcome)||(minutes!==null&&(!Number.isInteger(minutes)||minutes<1||minutes>1440))){$('feedbackMessage').textContent=tr('invalidFeedback');return;}
  const action=++state.feedbackRequest,current=()=>state.question===id&&state.detailRequest===view&&state.feedbackRequest===action,button=form.querySelector('button');button.disabled=true;
  try{await api(`/api/problem-bank/questions/${id}/feedback`,{method:'POST',body:{stars,outcome,minutes}});if(!current())return;$('feedbackMessage').textContent=tr('feedbackSaved');await loadFeedback(id,view);}
  catch(error){if(error.name!=='AbortError'&&current())$('feedbackMessage').textContent=errorText(error);}
  finally{if(state.question===id&&state.detailRequest===view)button.disabled=false;}
}
async function selectQuestion(id){const view=++state.detailRequest;state.relatedRequest++;state.question=id;releaseImages();$('detail').innerHTML=`<p class="muted">${esc(tr('loading'))}</p>`;document.querySelectorAll('.result').forEach(el=>el.classList.toggle('active',el.dataset.question===id));
  try{const {question:q}=await api(`/api/problem-bank/questions/${id}?lang=${state.lang}`);if(state.question!==id||view!==state.detailRequest)return;
    const version=q.selected_version,groups=figureGroups(q);$('detail').innerHTML=`<p class="source-title">${esc(q.source.title)}</p><h2>${esc(q.original_number)}</h2><div class="meta"><span class="badge">${esc(tr('review'))}</span>${difficultyBadge(q)}${q.context?.unresolved_source?`<span class="badge">${esc(tr('unresolved'))}</span>`:''}${(q.subjects||[]).map(s=>`<span class="muted">${esc(SUBJECTS[s]?.[state.lang==='ko'?0:1]||s)}</span>`).join('')}</div><div class="prose">${prose(version?.text||tr('noLang'))}</div><div id="questionFigures" class="figures inline-figures"></div><div class="actions"><button id="showSolutions">${esc(tr('solutions'))}</button><button id="showRecommendations">${esc(tr('recommendations'))}</button>${q.can_view_source===true?`<button id="sourcePdf">${esc(tr('pdf'))}</button>`:''}</div><div class="figures">${groups.reference.length?`<details id="referenceFigures"><summary>${esc(tr('referenceFigures'))} (${groups.reference.length})</summary><div id="referenceFigureImages"></div></details>`:''}${groups.raw.length?`<details id="sourceFigures"><summary>${esc(tr('sourceCrops'))} (${groups.raw.length})</summary><div id="sourceFigureImages"></div></details>`:''}</div><div id="related"></div>`;
    math($('detail'));loadFigures($('questionFigures'),groups.inline,id,view);$('showSolutions').addEventListener('click',()=>showSolutions(id));$('showRecommendations').addEventListener('click',()=>showRecommendations(id));if(q.can_view_source===true)$('sourcePdf').addEventListener('click',async()=>{try{const blob=await api(`/api/problem-bank/sources/${q.source_id}/pdf`);if(state.question!==id||view!==state.detailRequest)return;const url=URL.createObjectURL(blob);state.urls.push(url);const link=document.createElement('a');link.href=url;const filename=(q.source.title||'source').replace(/[\\/:*?"<>|]/g,'_').slice(0,180);link.download=/\.pdf$/i.test(filename)?filename:filename+'.pdf';link.click();}catch(e){if(e.name!=='AbortError'&&state.question===id&&view===state.detailRequest)$('message').textContent=errorText(e);}});
    if(q.context_links?.length){const button=document.createElement('button');button.textContent=(state.lang==='ko'?'참조 문제':'Referenced questions')+' ('+q.context_links.length+')';button.addEventListener('click',()=>showContexts(id));$('detail').querySelector('.actions').append(button);}
    if(groups.reference.length)lazyFigures($('referenceFigures'),$('referenceFigureImages'),groups.reference,id,view);
    if(groups.raw.length)lazyFigures($('sourceFigures'),$('sourceFigureImages'),groups.raw,id,view);
    $('related').textContent='';
    const reasons=difficultyReasons(q);if(reasons){const description=document.createElement('p');description.className='difficulty-reasons';description.textContent=tr('difficulty')+': '+reasons;$('detail').append(description);}
    const feedback=document.createElement('section');feedback.className='feedback';feedback.innerHTML=feedbackPanel();$('detail').append(feedback);
    let feedbackLoaded=false,feedbackLoading=false;$('difficultyFeedback').addEventListener('toggle',async()=>{if($('difficultyFeedback').open&&!feedbackLoaded&&!feedbackLoading&&state.question===id&&view===state.detailRequest){feedbackLoading=true;feedbackLoaded=await loadFeedback(id,view);feedbackLoading=false;}});
    if(state.user)$('feedbackForm').addEventListener('submit',event=>{event.preventDefault();saveFeedback(id,event.currentTarget,view);});
    else $('feedbackLogin').addEventListener('click',rememberLearningReturn);
  }catch(e){if(e.name!=='AbortError'&&state.question===id&&view===state.detailRequest)$('detail').innerHTML=`<p class="error">${esc(errorText(e))}</p>`;}
}
async function showSolutions(id){
  const related=$('related'),view=state.detailRequest,action=++state.relatedRequest;
  const current=()=>state.question===id&&view===state.detailRequest&&action===state.relatedRequest&&related.isConnected;
  related.innerHTML=`<p>${esc(tr('loading'))}</p>`;
  try{const data=await api(`/api/problem-bank/questions/${id}/solutions?lang=${state.lang}`);if(!current())return;
    const assets=data.solutions.map(s=>(s.assets||[]).filter(a=>a.role==='figure'||state.user?.role==='admin'));
    related.innerHTML='<section class="solutions"><h3>'+esc(tr('solutions'))+'</h3>'+(data.solutions.length?data.solutions.map((s,i)=>`<section class="solution-entry"><p><span class="badge">${esc(tr(s.authorship==='source_transcription'?'sourceSolution':'originalDraft'))}</span> <span class="muted">${esc(tr('review'))} · ${esc(s.kind)}</span></p><div class="prose">${prose(s.selected_version?.text||tr('noLang'))}</div>${assets[i].length?`<details data-solution-figures="${i}"><summary>${esc(tr('figures'))} (${assets[i].length})</summary><div></div></details>`:''}</section>`).join(''):`<p>${esc(tr('noSolutions'))}</p>` )+'</section>';math(related);
    related.querySelectorAll('[data-solution-figures]').forEach(el=>{let loaded=false;el.addEventListener('toggle',()=>{if(el.open&&!loaded&&current()){loaded=true;loadFigures(el.querySelector('div'),assets[+el.dataset.solutionFigures],id,view);}});});
  }catch(e){if(e.name!=='AbortError'&&current())related.textContent=errorText(e);}
}
async function showRecommendations(id){
  const related=$('related'),view=state.detailRequest,action=++state.relatedRequest;
  const current=()=>state.question===id&&view===state.detailRequest&&action===state.relatedRequest&&related.isConnected;
  related.textContent=tr('loading');
  try{const filters=new URLSearchParams({lang:state.lang,limit:'8'});for(const key of ['collection','stars'])if($(key).value)filters.set(key,$(key).value);const data=await api(`/api/problem-bank/questions/${id}/recommendations?${filters}`);if(!current())return;
    related.innerHTML='<section class="solutions recommendations"><h3>'+esc(tr('recommendations'))+'</h3>'+(data.items.length?data.items.map(x=>`<button data-question="${esc(x.id)}">${esc(x.source_title)} · ${esc(x.original_number)}<br><span class="muted">${esc(x.snippet.slice(0,140))}</span></button>`).join(''):`<p>${esc(tr('noReco'))}</p>` )+'</section>';related.querySelectorAll('[data-question]').forEach(el=>el.addEventListener('click',()=>selectQuestion(el.dataset.question)));math(related);
  }catch(e){if(e.name!=='AbortError'&&current())related.textContent=errorText(e);}
}
async function showContexts(id){
  const related=$('related'),view=state.detailRequest,action=++state.relatedRequest;
  const current=()=>state.question===id&&view===state.detailRequest&&action===state.relatedRequest&&related.isConnected;
  related.textContent=tr('loading');
  try{
    const data=await api(`/api/problem-bank/questions/${id}/context?lang=${state.lang}`);if(!current())return;
    const groups=data.contexts.map(figureGroups);
    related.innerHTML='<section class="solutions"><h3>'+(state.lang==='ko'?'참조 문제':'Referenced questions')+'</h3>'+data.contexts.map((q,i)=>`<section class="solution-entry"><p class="muted">${esc(q.source.title)} · ${esc(q.original_number)}</p>${difficultyBadge(q)}<div class="prose">${prose(q.selected_version?.text||tr('noLang'))}</div><div class="inline-figures" data-context-inline="${i}"></div><button data-open-reference="${esc(q.id)}">${state.lang==='ko'?'이 문제 열기':'Open question'}</button>${groups[i].reference.length?`<details data-context-figures="${i}"><summary>${esc(tr('referenceFigures'))} (${groups[i].reference.length})</summary><div></div></details>`:''}${groups[i].raw.length?`<details data-context-raw="${i}"><summary>${esc(tr('sourceCrops'))} (${groups[i].raw.length})</summary><div></div></details>`:''}</section>`).join('')+(data.truncated?`<p class="muted">${state.lang==='ko'?'참조 문제 일부만 표시됩니다. 각 문제에서 다음 참조를 확인할 수 있습니다.':'Some references are omitted here. Open a question to inspect further references.'}</p>`:'')+'</section>';
    math(related);related.querySelectorAll('[data-open-reference]').forEach(el=>el.addEventListener('click',()=>selectQuestion(el.dataset.openReference)));
    groups.forEach((group,i)=>loadFigures(related.querySelector(`[data-context-inline="${i}"]`),group.inline,id,view));
    related.querySelectorAll('[data-context-figures]').forEach(el=>{let loaded=false;el.addEventListener('toggle',()=>{if(el.open&&!loaded&&current()){loaded=true;loadFigures(el.querySelector('div'),groups[+el.dataset.contextFigures].reference,id,view);}});});
    related.querySelectorAll('[data-context-raw]').forEach(el=>{let loaded=false;el.addEventListener('toggle',()=>{if(el.open&&!loaded&&current()){loaded=true;loadFigures(el.querySelector('div'),groups[+el.dataset.contextRaw].raw,id,view);}});});
  }catch(e){if(e.name!=='AbortError'&&current())related.textContent=errorText(e);}
}
$('loginForm').addEventListener('submit',async e=>{e.preventDefault();state.bootstrapRequest++;bootstrapError();const button=e.currentTarget.querySelector('button');button.disabled=true;$('loginMessage').textContent=tr('working');try{const form=new FormData(e.currentTarget),data=await api('/auth/login',{method:'POST',body:{username:form.get('username'),password:form.get('password')}});state.token=data.token;state.user=data.user;sessionStorage.setItem('hlBankToken',data.token);$('loginForm').reset();$('loginMessage').textContent='';await showLibrary();}catch(e){if(e.name!=='AbortError')$('loginMessage').textContent=e.status===401?tr('badLogin'):errorText(e);}finally{button.disabled=false;}});
$('retryBootstrap').addEventListener('click',restoreSession);
$('logout').addEventListener('click',()=>signOut());$('theme').addEventListener('click',()=>{state.theme=state.theme==='dark'?'light':'dark';localStorage.setItem('hlBankTheme',state.theme);applyTheme();});
async function setLanguage(language){if(!COPY[language]||state.lang===language)return;const selected=state.question;state.lang=language;state.request++;state.detailRequest++;state.relatedRequest++;releaseImages();$('detail').textContent='';if(!EMBED)localStorage.setItem('hlBankLang',state.lang);translate();const ready=await showLibrary();if(ready&&selected&&state.lang===language)await selectQuestion(selected);}
$('language').addEventListener('change',()=>setLanguage($('language').value));
$('searchForm').addEventListener('submit',e=>{e.preventDefault();search(true);});
function changePage(direction){
  if($('query').value.trim())state.offset=Math.max(0,Math.min(300,state.offset+20*direction));
  else if(direction>0){if(!state.nextCursor||!state.hasMore)return;state.cursorHistory.push({cursor:state.cursor,offset:state.offset});state.cursor=state.nextCursor;state.offset+=state.pageSize;}
  else{const previous=state.cursorHistory.pop();if(!previous)return;state.cursor=previous.cursor;state.offset=previous.offset;}
  return search();
}
$('previous').addEventListener('click',()=>changePage(-1));$('next').addEventListener('click',()=>changePage(1));
for(const key of ['collection','stars','subject','source'])$(key).addEventListener('change',()=>search(true));
for(const mode of ['text','photo'])$(mode+'Mode').addEventListener('click',()=>{if(mode==='photo'&&!state.ocrAvailable)return;state.mode=mode;$('photoForm').hidden=mode!=='photo';for(const key of ['text','photo']){$(key+'Mode').classList.toggle('selected',key===mode);$(key+'Mode').setAttribute('aria-selected',String(key===mode));}});
$('photoForm').addEventListener('submit',e=>{e.preventDefault();const file=$('photo').files[0];if(!file||!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>8*1024*1024){message('imageSize',true);return;}identify(null,file);});$('retryText').addEventListener('click',()=>identify($('recognized').value));
if(EMBED){
  document.documentElement.dataset.embedded='true';$('loginForm').hidden=true;$('siteLogin').hidden=false;
  $('siteLogin').addEventListener('click',rememberLearningReturn);
  window.addEventListener('message',event=>{if(event.origin!==launch.origin||event.source!==window.parent||event.data?.type!=='hl-bank-settings')return;if(['light','dark'].includes(event.data.theme)){state.theme=event.data.theme;applyTheme();}const changedCollection=['physics','astronomy'].includes(event.data.collection)&&$('collection').value!==event.data.collection;if(changedCollection)$('collection').value=event.data.collection;if(['ko','en'].includes(event.data.lang)&&event.data.lang!==state.lang)setLanguage(event.data.lang);else if(changedCollection)search(true);});
  window.addEventListener('storage',event=>{if(event.key!==null&&event.key!=='hlCmTok')return;const token=sharedToken();if(token===state.token)return;signOut(false,false);state.token=token;restoreSession();});
  const size=()=>{const height=Math.ceil(document.querySelector('main').getBoundingClientRect().height)+24;if(Number.isFinite(height))window.parent.postMessage({type:'hl-bank-height',height},launch.origin);};
  if(typeof ResizeObserver==='function')new ResizeObserver(size).observe(document.body);
  size();
}
translate();if(['physics','astronomy'].includes(launch.searchParams.get('collection')))$('collection').value=launch.searchParams.get('collection');restoreSession();
