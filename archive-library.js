/* Native archive reader. Canonical data stays in the existing problem-bank service. */
const PREFIX='/api/problem-bank';
const QID=/^q_[a-f0-9]{64}$/,SID=/^src_[a-f0-9]{64}$/;
const DISCIPLINES={physics:'phys',astronomy:'astro',mathematics:'math',chemistry:'chem',biology:'bio',earth_science:'earth',informatics:'info'};
const CATEGORIES={contest:'contests',book:'books',course:'schools'};
const TOPICS={classical_mechanics:['고전역학','Classical mechanics'],electromagnetism:['전자기학','Electromagnetism'],thermodynamics:['열역학','Thermodynamics'],statistical_mechanics:['통계역학','Statistical mechanics'],optics:['광학','Optics'],oscillations_waves:['진동·파동','Oscillations and waves'],quantum_mechanics:['양자역학','Quantum mechanics'],relativity:['상대론','Relativity'],special_relativity:['특수상대론','Special relativity'],general_relativity:['일반상대론','General relativity'],mathematical_methods:['수리물리','Mathematical methods'],astronomy_astrophysics:['천문·천체물리','Astronomy / astrophysics'],mathematics:['수학','Mathematics'],chemistry:['화학','Chemistry'],biology:['생물학','Biology'],earth_science:['지구과학','Earth science'],informatics:['정보과학','Informatics'],mixed:['종합','Mixed']};
const WORDS={
  ko:{sources:'자료 목록',findSource:'자료 이름 찾기',allSources:'전체 자료',search:'검색',query:'문장·수식·문항 번호',topic:'분야',allTopics:'전체 분야',stars:'난이도',allStars:'전체 난이도',provisional:'잠정',problems:'문제',empty:'조건에 맞는 문제가 없습니다.',emptySources:'등록된 자료가 없습니다.',loading:'불러오는 중…',retry:'다시 불러오기',error:'자료를 불러오지 못했습니다. 잠시 후 다시 시도하세요.',notFound:'이 분류에 해당하는 자료를 찾지 못했습니다.',list:'문제 목록',first:'처음',next:'다음',back:'← 문제 목록',statement:'문제',solutions:'풀이 보기',hideSolutions:'풀이 닫기',noSolutions:'저장된 풀이가 아직 없습니다.',sourceSolution:'원문 풀이',draft:'보완 풀이 초안',pending:'검토 대기',sourceIssue:'원문 확인 사항 있음',recommendations:'추천 문제',contexts:'참조 문제',referenceFigures:'참고 그림',rawFigures:'원문 캡처',given:'문제 그림',pages:'원문 쪽수',pdf:'원본 PDF',source:'자료',limited:'검색 결과 일부입니다. 자료나 분야로 범위를 좁혀 주세요.',photo:'사진으로 찾기',ocr:'사진 인식·검색',ocrNote:'관리자 전용 · Upstage OCR 호출',image:'문제 사진',badImage:'PNG·JPEG·WebP 이미지(최대 8MB)를 선택하세요.',recognized:'인식된 문장·수식',resubmit:'수정한 텍스트로 다시 검색',noOcr:'OCR을 다시 호출하지 않습니다.',candidates:'후보 문제입니다. 원문의 수식과 수치를 확인하세요.',feedback:'난이도 평가',feedbackNote:'사용자가 직접 남기는 풀이 기록입니다.',noFeedback:'아직 사용자 평가가 없습니다.',rate:'별점 선택',outcome:'풀이 상태',minutes:'풀이 시간(분, 선택)',not_attempted:'아직 풀지 않음',solved:'풀었음',partial:'일부 해결',unsolved:'해결하지 못함',save:'평가 저장',saved:'평가를 저장했습니다.',login:'로그인하고 평가 남기기',invalidFeedback:'별점과 풀이 시간을 확인하세요.',auth:'로그인 상태를 확인한 뒤 다시 시도하세요.',badQuery:'검색어는 600자 이내로 입력하세요.',noLanguage:'선택한 언어의 본문이 없습니다.',competition:'대회',year:'연도',type:'구분',all:'전체',theory:'이론',experiment:'실험',reset:'초기화'},
  en:{problem:'Problem',sources:'Sources',findSource:'Find a source',allSources:'All sources',search:'Search',query:'Text, formula or problem number',topic:'Topic',allTopics:'All topics',stars:'Difficulty',allStars:'All difficulties',provisional:'Provisional',problems:'Problems',empty:'No problems match these filters.',emptySources:'No sources are registered.',loading:'Loading…',retry:'Try again',error:'Could not load the material. Please try again later.',notFound:'This material is not available in this category.',list:'Problem list',first:'First',next:'Next',back:'← Problem list',statement:'Statement',solutions:'Show solutions',hideSolutions:'Hide solutions',noSolutions:'No solution is stored yet.',sourceSolution:'Source solution',draft:'Supplementary solution draft',pending:'Review pending',sourceIssue:'Source issues recorded',recommendations:'Recommended problems',contexts:'Referenced problems',referenceFigures:'Reference figures',rawFigures:'Source captures',given:'Problem figure',pages:'Source pages',pdf:'Original PDF',source:'Source',limited:'Showing part of the results. Narrow the source or topic.',photo:'Find from photo',ocr:'Read photo and search',ocrNote:'Administrators only · Upstage OCR call',image:'Question photo',badImage:'Choose a PNG, JPEG or WebP image up to 8MB.',recognized:'Recognized text and equations',resubmit:'Search corrected text',noOcr:'This does not call OCR again.',candidates:'Candidate problems. Check the original formulas and numbers.',feedback:'Rate difficulty',feedbackNote:'These are self-reported solving records.',noFeedback:'No user ratings yet.',rate:'Choose a rating',outcome:'Solving outcome',minutes:'Time spent (minutes, optional)',not_attempted:'Not attempted',solved:'Solved',partial:'Partly solved',unsolved:'Unsolved',save:'Save rating',saved:'Rating saved.',login:'Sign in to leave a rating',invalidFeedback:'Check the rating and solving time.',auth:'Check your sign-in status and try again.',badQuery:'Enter a search query up to 600 characters.',noLanguage:'No statement in the selected language.',competition:'Competition',year:'Year',type:'Type',all:'All',theory:'Theory',experiment:'Experiment',reset:'Reset'}
};
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sourceTitle=s=>s?.title||s?.published_title_en||s?.published_title_ko||s?.id||'';
const titleOf=(q,lang)=>q?.[lang==='ko'?'title_ko':'title_en']||q?.[lang==='ko'?'title_en':'title_ko']||'';
const fail=code=>Object.assign(new Error(code),{code});
function snippet(value){
  const text=String(value||'').split(/\n\s*\n/)[0].replace(/\$\$/g,'$').replace(/\\\[/g,'\\(').replace(/\\\]/g,'\\)').replace(/\s+/g,' ').slice(0,300);
  let cut=text.length;const dollars=[...text.matchAll(/(?<!\\)\$/g)];if(dollars.length%2)cut=Math.min(cut,dollars.at(-1).index);
  const opens=[];for(const m of text.matchAll(/(?<!\\)\\[()]/g)){if(m[0]==='\\(')opens.push(m.index);else opens.pop();}if(opens.length)cut=Math.min(cut,opens[0]);return text.slice(0,cut).trim();
}

// Escape prose before adding the small set of supported structural elements.
// Protect complete TeX spans before splitting paragraphs, including multiline aligned equations.
export function archiveProse(value){
  const blocks=[],maths=[];
  const protectedText=String(value??'').replace(/```[^\n]*\n([\s\S]*?)```/g,(_,code)=>`\uE002${blocks.push(code)-1}\uE003`).replace(/\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$(?:\\.|[^$\n])*\$/g,m=>`\uE000${maths.push(m)-1}\uE001`);
  const restore=s=>esc(s).replace(/\uE000(\d+)\uE001/g,(_,i)=>esc(maths[+i]||''));
  const lines=protectedText.split('\n');let html='',paragraph=[];
  const flush=()=>{if(paragraph.length){html+='<p>'+restore(paragraph.join('\n'))+'</p>';paragraph=[];}};
  for(let i=0;i<lines.length;i++){
    const line=lines[i],block=line.trim().match(/^\uE002(\d+)\uE003$/);
    if(block){flush();html+='<pre><code>'+esc(blocks[+block[1]]||'')+'</code></pre>';}
    else if(line.trim().startsWith('|')&&i+1<lines.length&&/^\s*\|?\s*:?-{3,}/.test(lines[i+1])){
      flush();const split=s=>s.trim().replace(/^\||\|$/g,'').split('|').map(x=>restore(x.trim()));
      html+='<div class="al-table"><table><thead><tr>'+split(line).map(x=>'<th>'+x+'</th>').join('')+'</tr></thead><tbody>';i++;
      while(i+1<lines.length&&lines[i+1].trim().startsWith('|')){i++;html+='<tr>'+split(lines[i]).map(x=>'<td>'+x+'</td>').join('')+'</tr>';}
      html+='</tbody></table></div>';
    }else if(/^#{1,4}\s/.test(line)){flush();const level=Math.min(5,line.match(/^#+/)[0].length+2);html+=`<h${level}>${restore(line.replace(/^#+\s*/,''))}</h${level}>`;}
    else if(!line.trim())flush();else paragraph.push(line);
  }flush();return html;
}

export function mountArchiveLibrary(container,options={}){
  if(!container?.ownerDocument)throw new TypeError('Archive container required');
  const doc=container.ownerDocument,win=doc.defaultView||window;
  let config={kind:'book',collection:'physics',lang:'ko',theme:'light',apiOrigin:'https://haslalab-problem-bank.haslalab.workers.dev',params:new URLSearchParams(),...options};
  let disposed=false,epoch=0,panelRequest=0,bootstrapRequest=0,activeQuestion=null,identifyBusy=false,sources=[],status={},urls=new Set(),controllers=new Set();
  let token=String(config.getToken?.()||''),params=cleanParams(config.params),candidateItems=null;
  const root=doc.createElement('section');root.className='al';container.replaceChildren(root);
  const $=selector=>root.querySelector(selector),tr=key=>WORDS[config.lang==='en'?'en':'ko'][key]||key;
  const current=e=>!disposed&&e===epoch&&String(config.getToken?.()||'')===token;
  const isAbort=e=>e?.name==='AbortError';
  function cleanParams(input){
    const p=new URLSearchParams(input||''),out=new URLSearchParams();
    for(const [key,value]of p){
      if(key==='source'&&SID.test(value)||key==='problem'&&QID.test(value)||key==='stars'&&/^[1-5]$/.test(value)||key==='topic'&&Object.hasOwn(TOPICS,value)||key==='competition'&&/^[a-z0-9_-]{1,80}$/.test(value)||key==='year'&&/^\d{4}$/.test(value)||key==='type'&&['theory','experiment'].includes(value))out.set(key,value);
      if(key==='q'&&value.length<=600&&!value.includes('\0')||key==='cursor'&&value.length<=2800&&!/[\x00-\x1f]/.test(value))out.set(key,value);
      if(key==='view'&&value==='web'&&config.kind==='contest')out.set(key,value);
    }return out;
  }
  function scope(p=new URLSearchParams()){
    p.set('kind',config.kind);p.set('collection',config.collection);p.set('lang',config.lang==='en'?'en':'ko');return p;
  }
  function scopedPath(path,query,unscoped=false){const u=new URL(path,config.apiOrigin);if(u.origin!==new URL(config.apiOrigin).origin)throw fail('invalid_api_path');if(query)for(const [k,v]of query)u.searchParams.set(k,v);if(!unscoped)scope(u.searchParams);return u.pathname+u.search;}
  async function api(path,{method='GET',body,unscoped=false}={}){
    const origin=new URL(config.apiOrigin).origin,u=new URL(scopedPath(path,null,unscoped),origin);
    if(u.origin!==origin||!u.pathname.startsWith(PREFIX+'/')||!['GET','POST'].includes(method)||method==='POST'&&!/^\/api\/problem-bank\/(identify|questions\/q_[a-f0-9]{64}\/feedback)$/.test(u.pathname))throw fail('invalid_api_path');
    const e=epoch,c=new win.AbortController();controllers.add(c);
    try{
      const headers={};if(token)headers.Authorization='Bearer '+token;
      const multipart=body instanceof win.FormData;if(body&&!multipart)headers['Content-Type']='application/json';
      const response=await win.fetch(u.href,{method,headers,body:multipart?body:body?JSON.stringify(body):undefined,signal:c.signal,credentials:'omit',cache:'no-store'});
      if(!current(e))throw new win.DOMException('Stale archive request','AbortError');
      if(!response.ok){let result={};try{result=await response.json();}catch{}throw fail(result.error||'request_failed');}
      const data=response.headers.get('Content-Type')?.includes('application/json')?await response.json():await response.blob();
      if(!current(e))throw new win.DOMException('Stale archive request','AbortError');return data;
    }finally{controllers.delete(c);}
  }
  function errorText(e){return /scope|not_found|invalid_question/.test(e?.code||'')?tr('notFound'):/login_required|admin_required/.test(e?.code||'')?tr('auth'):tr('error');}
  function message(text,error=false){const el=$('[data-message]');if(el){el.textContent=text;el.classList.toggle('al-error',error);}}
  async function math(el){
    if(!el||!el.isConnected||disposed)return;const e=epoch;
    try{
      if(typeof config.renderMath==='function')await config.renderMath(el);else if(typeof win.renderMathInElement==='function')win.renderMathInElement(el,{delimiters:[{left:'$$',right:'$$',display:true},{left:'\\[',right:'\\]',display:true},{left:'\\(',right:'\\)',display:false},{left:'$',right:'$',display:false}],throwOnError:false,trust:false,strict:'ignore',maxExpand:1000,maxSize:30});
      if(!current(e)||!el.isConnected)return;
      for(const node of el.querySelectorAll('.katex')){
        if(node.closest('.katex-display,.al-inline-equation'))continue;const prose=node.closest('.al-prose');
        if(prose&&node.getBoundingClientRect().width>prose.getBoundingClientRect().width){const wrapper=doc.createElement('span');wrapper.className='al-inline-equation';wrapper.tabIndex=0;wrapper.setAttribute('aria-label',config.lang==='en'?'Equation':'수식');node.before(wrapper);wrapper.append(node);}
      }
    }catch{/* The readable escaped source remains available if the optional renderer fails. */}
  }
  function href(changes={},base=config.baseHash){const p=new URLSearchParams(params);for(const [k,v]of Object.entries(changes)){if(v===null||v===undefined||v==='')p.delete(k);else p.set(k,String(v));}return (base||`#/archive/${CATEGORIES[config.kind]||'books'}/${DISCIPLINES[config.collection]||'phys'}`)+(p.size?'?'+p:'');}
  function navigate(hash){if(disposed)return;if(config.onNavigate)config.onNavigate(hash);else win.location.hash=hash;}
  function link(hash,label,className=''){const a=doc.createElement('a');a.href=hash;a.textContent=label;if(className)a.className=className;return a;}
  function matches(q){const kind=q?.source_kind||q?.source?.kind||q?.kind,collection=q?.collection||q?.discipline||q?.source?.collection;return kind===config.kind&&collection===config.collection;}
  // Membership belongs to the scoped endpoint: one source may contain both banks.
  function sourceMatches(s){return s?.kind===config.kind;}
  function badge(q){const n=q?.stars??q?.difficulty?.stars;if(!Number.isInteger(n)||n<1||n>5)return '';const pending=!['reviewed','community_calibrated'].includes(q.difficulty?.status);return `<span class="al-stars" aria-label="${esc(tr('stars'))} ${n}/5${pending?' · '+esc(tr('provisional')):''}">${'★'.repeat(n)}${'☆'.repeat(5-n)}${pending?` <small>${esc(tr('provisional'))}</small>`:''}</span>`;}
  function sourceMeta(s){return [s?.primary_author,s?.institution,s?.edition_label,s?.year,s?.round].filter((x,i,a)=>x!=null&&x!==''&&a.indexOf(x)===i).join(' · ');}
  function ordered(list){const c=new Intl.Collator(config.lang,{numeric:true,sensitivity:'base'});return [...list].sort((a,b)=>config.kind==='contest'?(c.compare(a.competition||'',b.competition||'')||(b.year||0)-(a.year||0)||c.compare(sourceTitle(a),sourceTitle(b))):c.compare(sourceTitle(a),sourceTitle(b))||String(a.id).localeCompare(String(b.id)));}
  async function loadSources(unscoped=false){
    const list=[],seen=new Set(),cursors=new Set();let after=null;
    for(let page=0;page<100;page++){
      const query=new URLSearchParams({source_limit:'200'});if(after)query.set('after',after);
      const result=await api(PREFIX+'/sources?'+query,{unscoped});
      if(!Array.isArray(result.sources)||result.sources.length>500)throw fail('invalid_sources');
      for(const s of result.sources){if(!SID.test(s?.id||''))throw fail('invalid_sources');if(!seen.has(s.id)){seen.add(s.id);if(seen.size>20000)throw fail('invalid_sources');list.push(s);}}
      if(result.has_more!==true)return ordered(unscoped?list:list.filter(sourceMatches));
      if(!SID.test(result.next_cursor||'')||cursors.has(result.next_cursor))throw fail('invalid_sources');after=result.next_cursor;cursors.add(after);
    }throw fail('invalid_sources');
  }
  function release(){for(const u of urls)win.URL.revokeObjectURL(u);urls.clear();}
  function abort(){epoch++;panelRequest++;bootstrapRequest++;identifyBusy=false;for(const c of controllers)c.abort();controllers.clear();release();activeQuestion=null;}
  function renderShell(){
    root.dataset.theme=config.theme==='dark'?'dark':'light';root.lang=config.lang;
    root.innerHTML=`<p class="al-status" data-message role="status" aria-live="polite">${esc(tr('loading'))}</p><div data-content></div>`;
  }
  function renderDirectory(){
    const slot=$('[data-source-list]');if(!slot)return;const query=($('[data-source-query]')?.value||'').trim().toLocaleLowerCase();
    const list=sources.filter(s=>[sourceTitle(s),sourceMeta(s)].join(' ').toLocaleLowerCase().includes(query));
    slot.innerHTML=list.length?list.map(s=>`<li><a href="${esc(href({source:s.id,problem:null,cursor:null}))}"><strong>${esc(sourceTitle(s))}</strong><span>${esc(sourceMeta(s))}</span>${Number.isSafeInteger(s.question_count)?`<small>${s.question_count.toLocaleString()} ${esc(tr('problems'))}</small>`:''}</a></li>`).join(''):`<li class="al-muted">${esc(tr('emptySources'))}</li>`;
  }
  function filters(){
    const topics=new Set(sources.flatMap(s=>Array.isArray(s.subjects)?s.subjects:[]).filter(s=>Object.hasOwn(TOPICS,s)));
    // Per-question SR/GR facets can be more specific than source-level tags.
    if(['physics','astronomy'].includes(config.collection))for(const key of ['classical_mechanics','electromagnetism','thermodynamics','statistical_mechanics','optics','oscillations_waves','quantum_mechanics','relativity','special_relativity','general_relativity','mathematical_methods'])topics.add(key);
    if(config.collection==='astronomy')topics.add('astronomy_astrophysics');
    if(params.has('topic'))topics.add(params.get('topic'));
    const selected=params.get('source'),source=sources.find(s=>s.id===selected),query=params.get('q')||'';
    const count=Number(status.questions),countText=Number.isSafeInteger(count)&&count>=0?`${count.toLocaleString()} ${tr('problems')}`:'';
    $('[data-content]').innerHTML=`<div class="al-catalog"><div class="al-catalog-heading"><div><h2>${esc(source?sourceTitle(source):tr('sources'))}</h2><p class="al-muted">${esc(source?sourceMeta(source):countText)}</p></div>${selected?`<a href="${esc(href({source:null,problem:null,cursor:null}))}">${esc(tr('allSources'))}</a>`:''}</div><form data-search class="al-search"><label class="al-query"><span class="al-sr">${esc(tr('query'))}</span><input name="q" type="search" maxlength="600" value="${esc(query)}" placeholder="${esc(tr('query'))}"></label><button type="submit">${esc(tr('search'))}</button><label><span>${esc(tr('topic'))}</span><select name="topic"><option value="">${esc(tr('allTopics'))}</option>${[...topics].map(key=>`<option value="${key}"${params.get('topic')===key?' selected':''}>${esc(TOPICS[key][config.lang==='en'?1:0])}</option>`).join('')}</select></label><label><span>${esc(tr('stars'))}</span><select name="stars"><option value="">${esc(tr('allStars'))}</option>${[1,2,3,4,5].map(n=>`<option value="${n}"${params.get('stars')===String(n)?' selected':''}>${'★'.repeat(n)}${'☆'.repeat(5-n)}</option>`).join('')}</select></label>${source?`<label class="al-source-select"><span>${esc(tr('source'))}</span><select name="source">${sources.map(s=>`<option value="${s.id}"${s.id===selected?' selected':''}>${esc(sourceTitle(s))}</option>`).join('')}</select></label>`:''}<a class="al-reset" href="${esc(href({source:null,problem:null,q:null,topic:null,stars:null,cursor:null,competition:null,year:null,type:null}))}">${esc(tr('reset'))}</a></form>${!selected&&!query?`<section class="al-directory"><label class="al-source-find">${esc(tr('findSource'))}<input type="search" data-source-query maxlength="120"></label><ul data-source-list></ul></section>`:''}<section data-results aria-label="${esc(tr('list'))}"><p>${esc(tr('loading'))}</p></section><div data-admin-tools></div></div>`;
    renderDirectory();renderAdminTools();
  }
  function searchParams(){
    const p=new URLSearchParams({limit:'20'}),query=params.get('q')?.trim()||'';
    for(const key of ['source','stars','competition','year','type'])if(params.has(key))p.set(key,params.get(key));
    if(params.has('topic'))p.set('subject',params.get('topic'));
    if(query){p.set('q',query);const m=params.get('cursor')?.match(/^o_(\d+)$/);p.set('offset',String(m?Math.min(300,Number(m[1])):0));}
    else{p.set('sort','source');if(params.has('cursor')&&!/^o_/.test(params.get('cursor')))p.set('cursor',params.get('cursor'));}
    return p;
  }
  function resultRows(items){return items.map(q=>{const changes={problem:q.id};if(params.has('source')&&q.source_id!==params.get('source')){changes.source=null;changes.cursor=null;}return `<li><a class="al-problem-row" href="${esc(href(changes))}"><span class="al-number">${esc(q.original_number||q.locator)}</span><span><strong>${esc(titleOf(q,config.lang)||q.source_title||'')}</strong>${q.source_title&&titleOf(q,config.lang)?`<small>${esc(q.source_title)}</small>`:''}<span class="al-snippet">${esc(snippet(q.snippet))}</span></span>${badge(q)}</a></li>`;}).join('');}
  async function renderResults(){
    const e=epoch,slot=$('[data-results]');if(!slot)return;
    try{
      const data=candidateItems?{items:candidateItems}:await api(PREFIX+'/search?'+searchParams());if(!current(e)||!slot.isConnected)return;
      if(!Array.isArray(data.items))throw fail('invalid_results');const items=data.items.filter(q=>QID.test(q?.id||'')&&matches(q));
      const query=params.get('q')?.trim(),offset=Number(searchParams().get('offset')||0),next=query&&offset<300&&data.has_more?'o_'+(offset+20):!query&&data.has_more&&typeof data.next_cursor==='string'&&data.next_cursor.length<=2800?data.next_cursor:null;
      slot.innerHTML=`<h3>${esc(tr('list'))}</h3>${candidateItems?`<p class="al-muted">${esc(tr('candidates'))}</p>`:''}${items.length?`<ol class="al-results">${resultRows(items)}</ol>`:`<p class="al-empty">${esc(tr('empty'))}</p>`}${data.limited_results?`<p class="al-muted">${esc(tr('limited'))}</p>`:''}<nav class="al-pager" aria-label="${esc(tr('list'))}">${params.has('cursor')?`<a href="${esc(href({cursor:null,problem:null}))}">← ${esc(tr('first'))}</a>`:''}${next?`<a href="${esc(href({cursor:next,problem:null}))}">${esc(tr('next'))} →</a>`:''}</nav>`;await math(slot);if(current(e)&&slot.isConnected)message('');
    }catch(error){if(!isAbort(error)&&current(e)&&slot.isConnected){slot.innerHTML=`<p class="al-error">${esc(errorText(error))}</p>`;}}
  }
  function figureGroups(q){
    const variants=Array.isArray(q.figures)?q.figures:[],assets=Array.isArray(q.assets)?q.assets:[],parents=new Set(variants.map(x=>x.parent_asset_id)),seen=new Set(),inline=[],reference=[];
    for(const a of [...variants,...assets.filter(a=>a.role==='figure'&&!parents.has(a.id))]){if(!a?.url||['blocked','hidden','source_only'].includes(a.placement))continue;const key=a.id||a.url;if(seen.has(key))continue;seen.add(key);(a.placement==='reference'?reference:inline).push(a);}
    return {inline,reference,raw:q.can_view_source===true?assets.filter(a=>a.role!=='figure'||a.placement==='source_only'):[]};
  }
  async function loadFigures(slot,assets,e=epoch){
    for(const a of assets.slice(0,40)){
      if(!current(e)||!slot?.isConnected)return;
      try{
        if(!/^\/api\/problem-bank\/(?:figures\/f_[a-f0-9]{64}|assets\/(?:a_|sa_)[a-f0-9]{64})$/.test(a.url||''))throw fail('invalid_asset');
        const blob=await api(a.url);if(!current(e)||!slot.isConnected)return;
        if(!['image/png','image/jpeg','image/webp'].includes(blob.type)||blob.size>20*1024*1024)throw fail('invalid_asset');
        const url=win.URL.createObjectURL(blob);urls.add(url);const fig=doc.createElement('figure'),img=doc.createElement('img');
        img.src=url;img.alt=(a.figure_label?tr('given')+' '+a.figure_label:tr('given'));img.loading='lazy';if(a.monochrome===true)img.className='al-monochrome';
        if(Number.isSafeInteger(a.width)&&a.width>0)img.width=a.width;if(Number.isSafeInteger(a.height)&&a.height>0)img.height=a.height;
        fig.append(img);const caption=doc.createElement('figcaption'),pages=[...new Set((a.spans||[]).map(x=>x.page).filter(Number.isInteger))];caption.textContent=[a.figure_label,pages.length?tr('pages')+': '+pages.join(', '):''].filter(Boolean).join(' · ');if(caption.textContent)fig.append(caption);slot.append(fig);
      }catch(error){if(isAbort(error)||!current(e)||!slot.isConnected)return;const p=doc.createElement('p');p.className='al-error';p.textContent=tr('error');slot.append(p);}
    }
  }
  function lazyFigures(details,slot,assets,e){let loaded=false;details.addEventListener('toggle',()=>{if(details.open&&!loaded&&current(e)){loaded=true;loadFigures(slot,assets,e);}});}
  function selectedVersion(q){return q.selected_version?.language===config.lang?q.selected_version:(q.versions||[]).find(v=>v.language===config.lang);}
  function feedbackHTML(){return `<details class="al-feedback" data-feedback><summary>${esc(tr('feedback'))}</summary><p class="al-muted">${esc(tr('feedbackNote'))}</p><p data-feedback-stats role="status"></p>${status.user?`<form data-feedback-form><label>${esc(tr('stars'))}<select name="stars" required><option value="">${esc(tr('rate'))}</option>${[1,2,3,4,5].map(n=>`<option value="${n}">${n}/5</option>`).join('')}</select></label><label>${esc(tr('outcome'))}<select name="outcome">${['not_attempted','solved','partial','unsolved'].map(x=>`<option value="${x}">${esc(tr(x))}</option>`).join('')}</select></label><label>${esc(tr('minutes'))}<input name="minutes" type="number" min="1" max="1440" step="1"></label><button>${esc(tr('save'))}</button></form>`:`<a href="#/login" data-login>${esc(tr('login'))}</a>`}<p data-feedback-message role="status"></p></details>`;}
  async function renderReader(id){
    const e=epoch;activeQuestion=id;message(tr('loading'));
    try{
      const {question:q}=await api(PREFIX+'/questions/'+id);if(!current(e))return;
      if(q?.id!==id||!matches(q))throw fail('invalid_question');
      const version=selectedVersion(q),groups=figureGroups(q),title=titleOf(q,config.lang);
      $('[data-content]').innerHTML=`<article class="al-reader" tabindex="-1"><nav class="al-reader-nav"><a href="${esc(href({problem:null}))}">${esc(tr('back'))}</a><a href="${esc(href({source:q.source_id,problem:null,cursor:null}))}">${esc(sourceTitle(q.source))}</a></nav><header><p class="al-muted">${esc(sourceMeta(q.source))}</p><h2>${title?`<small>${esc(tr(config.lang==='en'?'problem':'problems'))} ${esc(q.original_number)}</small>${esc(title)}`:`${esc(tr(config.lang==='en'?'problem':'problems'))} ${esc(q.original_number)}`}</h2><div class="al-meta">${badge(q)}<span>${esc(tr('pending'))}</span>${q.context?.unresolved_source?`<span>${esc(tr('sourceIssue'))}</span>`:''}</div></header><div class="al-prose" lang="${config.lang}">${archiveProse(version?.text||tr('noLanguage'))}</div><div class="al-figures" data-givens></div><div class="al-actions"><button data-panel="solutions" aria-expanded="false">${esc(tr('solutions'))}</button><button data-panel="recommendations" aria-expanded="false">${esc(tr('recommendations'))}</button>${q.context_links?.length?`<button data-panel="context" aria-expanded="false">${esc(tr('contexts'))} (${q.context_links.length})</button>`:''}${q.can_view_source===true?`<button data-pdf="${esc(q.source_id)}">${esc(tr('pdf'))}</button>`:''}</div><section data-panel-content aria-live="polite"></section>${groups.reference.length?`<details class="al-reference" data-reference><summary>${esc(tr('referenceFigures'))} (${groups.reference.length})</summary><div class="al-figures"></div></details>`:''}${groups.raw.length?`<details class="al-reference" data-raw><summary>${esc(tr('rawFigures'))} (${groups.raw.length})</summary><div class="al-figures"></div></details>`:''}${feedbackHTML()}</article>`;
      const rendered=math($('[data-content]'));loadFigures($('[data-givens]'),groups.inline,e);
      for(const [name,assets]of [['reference',groups.reference],['raw',groups.raw]]){const el=$('[data-'+name+']');if(el)lazyFigures(el,el.querySelector('.al-figures'),assets,e);}
      const feedback=$('[data-feedback]');let loaded=false;feedback.addEventListener('toggle',async()=>{if(feedback.open&&!loaded){loaded=await loadFeedback(id,e);}});
      $('[data-feedback-form]')?.addEventListener('submit',event=>{event.preventDefault();saveFeedback(id,event.currentTarget,e);});
      $('[data-login]')?.addEventListener('click',event=>{if(config.onLogin&&!event.metaKey&&!event.ctrlKey&&!event.shiftKey){event.preventDefault();config.onLogin(href());}});
      $('[data-pdf]')?.addEventListener('click',()=>downloadPDF(q.source_id,q.source,e));
      $('[data-content]').querySelectorAll('[data-panel]').forEach(button=>button.addEventListener('click',()=>showPanel(button.dataset.panel,id,e)));
      await rendered;if(current(e)){$('[data-content] article')?.focus?.({preventScroll:true});message('');}
    }catch(error){if(!isAbort(error)&&current(e)){message(errorText(error),true);$('[data-content]').replaceChildren(link(href({problem:null}),tr('back')));}}
  }
  async function showPanel(kind,id,e){
    const slot=$('[data-panel-content]'),button=$('[data-panel="'+kind+'"]');if(!slot||!button)return;
    const closing=button.getAttribute('aria-expanded')==='true',action=++panelRequest;
    root.querySelectorAll('[data-panel]').forEach(b=>{b.setAttribute('aria-expanded','false');if(b.dataset.panel==='solutions')b.textContent=tr('solutions');});
    slot.replaceChildren();if(closing)return;button.setAttribute('aria-expanded','true');if(kind==='solutions')button.textContent=tr('hideSolutions');
    const valid=()=>current(e)&&activeQuestion===id&&panelRequest===action&&slot.isConnected;slot.textContent=tr('loading');
    try{
      const query=new URLSearchParams({limit:'8'});if(params.has('stars'))query.set('stars',params.get('stars'));
      const data=await api(PREFIX+'/questions/'+id+'/'+kind+'?'+query);if(!valid())return;
      if(kind==='solutions'){
        const list=Array.isArray(data.solutions)?data.solutions:[];
        slot.innerHTML=`<h3>${esc(tr('solutions'))}</h3>`+(list.length?list.map((s,i)=>`<section class="al-solution"><p class="al-meta"><strong>${esc(tr(s.authorship==='source_transcription'?'sourceSolution':'draft'))}</strong><span>${esc(s.kind||'')}</span><span>${esc(tr('pending'))}</span></p><div class="al-prose" lang="${config.lang}">${archiveProse(selectedVersion(s)?.text||tr('noLanguage'))}</div>${(s.assets||[]).some(a=>a.role==='figure'||status.user?.role==='admin')?`<details data-solution-figures="${i}"><summary>${esc(tr('referenceFigures'))}</summary><div class="al-figures"></div></details>`:''}</section>`).join(''):`<p>${esc(tr('noSolutions'))}</p>`);
        slot.querySelectorAll('[data-solution-figures]').forEach(el=>lazyFigures(el,el.querySelector('.al-figures'),(list[+el.dataset.solutionFigures].assets||[]).filter(a=>a.role==='figure'||status.user?.role==='admin'),e));
      }else if(kind==='recommendations'){
        const items=(data.items||[]).filter(q=>QID.test(q?.id||'')&&q.id!==id&&matches(q));slot.innerHTML=`<h3>${esc(tr('recommendations'))}</h3><ol class="al-results">${resultRows(items)}</ol>`;
      }else{
        // Older context DTOs omit catalogue fields. The scoped endpoint verifies
        // every graph target, so absence of optional DTO fields is not a mismatch.
        const contexts=(data.contexts||[]).filter(q=>QID.test(q?.id||'')&&(!(q.source_kind||q.collection||q.discipline||q.source?.kind||q.source?.collection)||matches(q)));
        slot.innerHTML=`<h3>${esc(tr('contexts'))}</h3>`+contexts.map((q,i)=>`<section class="al-context"><h4><a href="${esc(href({problem:q.id,source:null,cursor:null}))}">${esc(sourceTitle(q.source))} · ${esc(q.original_number)}</a></h4><div class="al-prose">${archiveProse(selectedVersion(q)?.text||tr('noLanguage'))}</div><div class="al-figures" data-context="${i}"></div></section>`).join('');
        contexts.forEach((q,i)=>loadFigures(slot.querySelector('[data-context="'+i+'"]'),figureGroups(q).inline,e));
      }await math(slot);
    }catch(error){if(!isAbort(error)&&valid())slot.textContent=errorText(error);}
  }
  async function downloadPDF(id,source,e){try{if(!SID.test(id))return;const blob=await api(PREFIX+'/sources/'+id+'/pdf');if(!current(e)||blob.type!=='application/pdf')return;const u=win.URL.createObjectURL(blob);urls.add(u);const a=doc.createElement('a');a.href=u;a.download=sourceTitle(source).replace(/[\\/:*?"<>|]/g,'_').slice(0,180)+'.pdf';a.click();}catch(error){if(!isAbort(error)&&current(e))message(errorText(error),true);}}
  async function loadFeedback(id,e){
    const slot=$('[data-feedback-stats]');try{const data=await api(PREFIX+'/questions/'+id+'/feedback');if(!current(e)||!slot?.isConnected)return false;
      const mean=Number(data.mean_stars);slot.textContent=Number(data.count)>0?`${Number(data.count).toLocaleString()} · ${Number.isFinite(mean)&&mean>=1&&mean<=5?mean.toFixed(1):'—'}/5`:tr('noFeedback');
      const form=$('[data-feedback-form]');if(form&&data.own){form.elements.stars.value=String(data.own.stars||'');form.elements.outcome.value=data.own.outcome||'not_attempted';form.elements.minutes.value=data.own.minutes??'';}return true;
    }catch(error){if(!isAbort(error)&&current(e)&&slot?.isConnected)slot.textContent=errorText(error);return false;}
  }
  async function saveFeedback(id,form,e){
    const fields=new win.FormData(form),stars=Number(fields.get('stars')),outcome=fields.get('outcome'),raw=fields.get('minutes'),minutes=raw===''?null:Number(raw),slot=$('[data-feedback-message]');
    if(!Number.isInteger(stars)||stars<1||stars>5||!['not_attempted','solved','partial','unsolved'].includes(outcome)||(minutes!==null&&(!Number.isInteger(minutes)||minutes<1||minutes>1440))){slot.textContent=tr('invalidFeedback');return;}
    const button=form.querySelector('button');button.disabled=true;
    try{await api(PREFIX+'/questions/'+id+'/feedback',{method:'POST',body:{stars,outcome,minutes}});if(!current(e)||!slot.isConnected)return;slot.textContent=tr('saved');await loadFeedback(id,e);}
    catch(error){if(!isAbort(error)&&current(e)&&slot.isConnected)slot.textContent=errorText(error);}
    finally{if(current(e)&&button.isConnected)button.disabled=false;}
  }
  function renderAdminTools(){
    const slot=$('[data-admin-tools]');if(!slot||status.user?.role!=='admin'||status.ocr_available!==true)return;
    slot.innerHTML=`<details class="al-photo"><summary>${esc(tr('photo'))}</summary><p class="al-muted">${esc(tr('ocrNote'))}</p><form data-photo><label>${esc(tr('image'))}<input type="file" name="image" accept="image/png,image/jpeg,image/webp" required></label><button>${esc(tr('ocr'))}</button></form><div data-recognized hidden><label>${esc(tr('recognized'))}<textarea rows="5" maxlength="12000"></textarea></label><button data-resubmit>${esc(tr('resubmit'))}</button><p class="al-muted">${esc(tr('noOcr'))}</p></div></details>`;
    slot.querySelector('[data-photo]').addEventListener('submit',event=>{event.preventDefault();const file=event.currentTarget.elements.image.files[0];if(!file||!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>8*1024*1024){message(tr('badImage'),true);return;}identify(null,file);});
    slot.querySelector('[data-resubmit]').addEventListener('click',()=>identify(slot.querySelector('textarea').value));
  }
  async function identify(text,file){
    const e=epoch,slot=$('[data-admin-tools]');if(!slot||identifyBusy)return;if(file&&(status.user?.role!=='admin'||status.ocr_available!==true))return;
    if(!file&&(typeof text!=='string'||text.trim().length<5||text.length>12000||text.includes('\0')))return;
    identifyBusy=true;const buttons=[...slot.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);message(tr('loading'));
    try{
      const p=scope(searchParams());for(const key of ['q','sort','cursor','offset'])p.delete(key);let body;
      if(file){body=new win.FormData();for(const [k,v]of p)body.set(k,v);body.set('image',file);}else body={...Object.fromEntries(p),text};
      const data=await api(PREFIX+'/identify',{method:'POST',body});if(!current(e))return;candidateItems=(data.candidates||data.items||[]).filter(q=>QID.test(q?.id||'')&&matches(q));
      if(typeof data.recognized_text==='string'){slot.querySelector('[data-recognized]').hidden=false;slot.querySelector('textarea').value=data.recognized_text.slice(0,12000);}await renderResults();message(tr('candidates'));
    }catch(error){if(!isAbort(error)&&current(e))message(errorText(error),true);}
    finally{if(current(e)){identifyBusy=false;buttons.forEach(b=>{if(b.isConnected)b.disabled=false;});}}
  }
  async function resolveLegacy(){
    const original=new URLSearchParams(config.params||''),target=new URLSearchParams(params),id=original.get('problem'),sourceId=original.get('source');let s;
    if(QID.test(id||'')){const data=await api(PREFIX+'/questions/'+id+'?lang='+config.lang,{unscoped:true});if(data.question?.id!==id)throw fail('invalid_question');const q=data.question;s={kind:q.source_kind||q.source?.kind,collection:q.collection||q.discipline||q.source?.collection};target.set('problem',id);if(SID.test(q.source_id||''))target.set('source',q.source_id);}
    else if(SID.test(sourceId||'')){s=(await loadSources(true)).find(x=>x.id===sourceId);if(!s)throw fail('source_not_found');}
    else s={kind:CATEGORIES[original.get('kind')]?original.get('kind'):config.kind,collection:DISCIPLINES[original.get('collection')]?original.get('collection'):config.collection};
    if(!CATEGORIES[s?.kind]||!DISCIPLINES[s?.collection])throw fail('invalid_scope');
    if(Object.hasOwn(TOPICS,original.get('subject')))target.set('topic',original.get('subject'));
    const lang=original.get('lang');if(['ko','en'].includes(lang))target.set('lang',lang);
    if(s.kind==='contest')target.set('view','web');
    const base=`#/archive/${CATEGORIES[s.kind]}/${DISCIPLINES[s.collection]}`;navigate(base+(target.size?'?'+target:''));
  }
  async function boot(){
    const e=epoch,job=++bootstrapRequest;renderShell();
    try{
      if(config.resolveLegacy){await resolveLegacy();return;}
      if(!CATEGORIES[config.kind]||!DISCIPLINES[config.collection])throw fail('invalid_scope');
      const [s,list]=await Promise.all([api(PREFIX+'/status'),loadSources()]);if(!current(e)||job!==bootstrapRequest)return;status=s;sources=list;
      if(params.has('source')&&!sources.some(s=>s.id===params.get('source')))throw fail('source_not_found');
      if(params.has('problem'))await renderReader(params.get('problem'));else{filters();await renderResults();}
    }catch(error){if(!isAbort(error)&&current(e)&&job===bootstrapRequest){message(errorText(error),true);$('[data-content]').innerHTML=`<button data-retry>${esc(tr('retry'))}</button>`;}}
  }
  function onClick(event){
    const retry=event.target.closest?.('[data-retry]');if(retry){abort();boot();return;}
    const a=event.target.closest?.('a');if(!a||!root.contains(a)||!a.getAttribute('href')?.startsWith('#/archive/')||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
    event.preventDefault();navigate(a.getAttribute('href'));
  }
  function onSubmit(event){if(!event.target.matches('[data-search]'))return;event.preventDefault();const form=new win.FormData(event.target),q=String(form.get('q')||'').trim();if(q.length>600||q.includes('\0')){message(tr('badQuery'),true);return;}navigate(href({q,topic:form.get('topic'),stars:form.get('stars'),source:form.has('source')?form.get('source'):params.get('source'),problem:null,cursor:null}));}
  function onChange(event){if(event.target.matches('[data-search] select'))event.target.form.requestSubmit();}
  function onInput(event){if(event.target.matches('[data-source-query]'))renderDirectory();}
  function authChanged(){const next=String(config.getToken?.()||'');if(next===token)return;abort();token=next;status={};sources=[];candidateItems=null;boot();}
  root.addEventListener('click',onClick);root.addEventListener('submit',onSubmit);root.addEventListener('change',onChange);root.addEventListener('input',onInput);
  win.addEventListener('storage',authChanged);boot();
  return {
    dispose(){if(disposed)return;abort();disposed=true;win.removeEventListener('storage',authChanged);root.removeEventListener('click',onClick);root.removeEventListener('submit',onSubmit);root.removeEventListener('change',onChange);root.removeEventListener('input',onInput);root.remove();},
    update(next={}){if(disposed)return;const previous=config;config={...config,...next};const nextParams=cleanParams(config.params),newToken=String(config.getToken?.()||'');const dataChanged=['kind','collection','lang','baseHash','resolveLegacy'].some(k=>previous[k]!==config[k])||nextParams.toString()!==params.toString()||newToken!==token;if(dataChanged){abort();params=nextParams;token=newToken;status={};sources=[];candidateItems=null;boot();}else{root.dataset.theme=config.theme==='dark'?'dark':'light';authChanged();}}
  };
}
