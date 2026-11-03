const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),{createRequire}=require('node:module');
const {JSDOM}=createRequire(path.resolve(__dirname,'../community/package.json'))('jsdom');
const code=fs.readFileSync(path.resolve(__dirname,'../archive-library.js'),'utf8').replace(/^export /gm,'');
const Q='q_'+'1'.repeat(64),Q2='q_'+'2'.repeat(64),SID='src_'+'a'.repeat(64),SID2='src_'+'b'.repeat(64),FIG='f_'+'c'.repeat(64);
const source=(id=SID,extra={})=>({id,title:'A Published Book',primary_author:'Author',kind:'book',collection:'physics',question_count:2,language_bodies:4,subjects:['classical_mechanics'],...extra});
const item=(id=Q,extra={})=>({id,source_id:SID,source_title:'A Published Book',source_kind:'book',collection:'physics',original_number:'1.2',snippet:'A particle has mass $m$.',stars:2,difficulty:{status:'provisional'},...extra});
const question=(extra={})=>({id:Q,source_id:SID,source:source(),source_kind:'book',kind:'problem',collection:'physics',original_number:'1.2',selected_version:{language:'ko',text:'A synthetic statement with $m=2$.'},context:{},figures:[],assets:[],...extra});
const response=(data,status=200,mime='application/json')=>({ok:status>=200&&status<300,status,headers:{get:()=>mime},json:async()=>data,blob:async()=>data});
const deferred=()=>{let resolve;return{promise:new Promise(r=>resolve=r),resolve:v=>resolve(v)};};
async function flush(){for(let n=0;n<8;n++)await new Promise(r=>setImmediate(r));}
async function setup(t,{params='',route,options={},token=''}={}){
  const dom=new JSDOM('<!doctype html><body><div id="outside">Keep</div><main id="mount"></main></body>',{url:'https://haslalab.org/#/archive/books/phys',runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window,calls=[],navigations=[],navigationOptions=[],revoked=[];let auth=token;
  w.URL.createObjectURL=()=> 'blob:synthetic-'+calls.length;w.URL.revokeObjectURL=u=>revoked.push(u);
  w.fetch=async(url,init)=>{const u=new URL(url),call={url:u,init};calls.push(call);const result=await route?.(u,init,calls);
    if(result)return result;
    if(u.pathname.endsWith('/status'))return response({questions:2,language_bodies:4,user:null,ocr_available:false});
    if(u.pathname.endsWith('/sources'))return response({sources:[source()],has_more:false});
    if(u.pathname.endsWith('/search'))return response({items:[item()],has_more:false});
    if(u.pathname.endsWith('/solutions'))return response({solutions:[]});
    if(u.pathname.endsWith('/feedback'))return response({count:0});
    if(u.pathname.endsWith('/recommendations'))return response({items:[]});
    if(u.pathname.endsWith('/context'))return response({contexts:[]});
    if(u.pathname.endsWith('/'+Q))return response({question:question()});
    throw Error('Unexpected synthetic request '+url);
  };
  w.eval(code+'\nwindow.archiveTest={mountArchiveLibrary,archiveProse};');
  const mount=w.document.getElementById('mount'),config={kind:'book',collection:'physics',lang:'ko',theme:'light',baseHash:'#/archive/books/phys',params:new URLSearchParams(params),getToken:()=>auth,onNavigate:(h,o)=>{navigations.push(h);navigationOptions.push(o);},...options};
  const instance=w.archiveTest.mountArchiveLibrary(mount,config);t.after(()=>{instance.dispose();dom.window.close();});await flush();
  return{w,mount,instance,calls,navigations,navigationOptions,revoked,config,setToken:v=>auth=v};
}

test('native directory keeps outside DOM intact, real titles/counts and all scoped endpoints',async t=>{
  const h=await setup(t);assert.equal(h.w.document.getElementById('outside').textContent,'Keep');assert(!h.mount.querySelector('iframe'));
  assert.match(h.mount.textContent,/A Published Book/);assert.match(h.mount.textContent,/Author/);assert.equal(h.mount.querySelector('[data-card-questions]').textContent,'2');
  for(const c of h.calls){assert.equal(c.url.searchParams.get('kind'),'book');assert.equal(c.url.searchParams.get('collection'),'physics');assert.equal(c.init.credentials,'omit');}
  const a=h.mount.querySelector('[data-source-list] a');assert.equal(a.getAttribute('href'),'#/archive/books/phys?source='+SID);
});

test('scoped directory follows every page, deduplicates and sorts actual published titles naturally',async t=>{
  const h=await setup(t,{route:u=>u.pathname.endsWith('/sources')?response(u.searchParams.has('after')?{sources:[source(SID),source(SID2,{title:'Book 2'})],has_more:false}:{sources:[source(SID,{title:'Book 10'})],has_more:true,next_cursor:SID}):null});
  assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/sources')).length,2);const rows=[...h.mount.querySelectorAll('[data-source-list] a .full')].map(x=>x.textContent);assert.deepEqual(rows,['Book 2','Book 10']);
});

test('scoped sources retain mixed-bank membership supplied by server, without re-filtering presentation collection',async t=>{
  const h=await setup(t,{options:{collection:'astronomy',baseHash:'#/archive/books/astro'},route:u=>u.pathname.endsWith('/sources')?response({sources:[source()],has_more:false}):u.pathname.endsWith('/search')?response({items:[]}):null});
  assert.equal(h.mount.querySelectorAll('[data-source-list] a').length,1);
});

test('repeated source cursor fails boundedly rather than publishing an incomplete directory',async t=>{
  const h=await setup(t,{route:u=>u.pathname.endsWith('/sources')?response({sources:[source()],has_more:true,next_cursor:SID}):null});
  assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/sources')).length,2);assert(h.mount.querySelector('[data-retry]'));assert.equal(h.mount.querySelector('[data-source-list]'),null);
});

test('source browse forwards the opaque cursor and leaves source order to the server',async t=>{
  const cursor='sc_opaque-safe-cursor',h=await setup(t,{params:'source='+SID+'&cursor='+cursor,route:u=>u.pathname.endsWith('/search')?response({items:[item()],has_more:true,next_cursor:'sc_next'}):null});
  const request=h.calls.find(c=>c.url.pathname.endsWith('/search'));assert.equal(request.url.searchParams.get('cursor'),cursor);assert.equal(request.url.searchParams.get('sort'),'source');
  assert.match(h.mount.querySelector('.al-pager a:last-child').getAttribute('href'),/cursor=sc_next/);
});

test('ranked search translates only bounded text offsets and preserves real outer-hash filters',async t=>{
  const h=await setup(t,{params:'q=mass&topic=classical_mechanics&stars=3&cursor=o_20'});const u=h.calls.find(c=>c.url.pathname.endsWith('/search')).url;
  assert.equal(u.searchParams.get('offset'),'20');assert.equal(u.searchParams.get('cursor'),null);assert.equal(u.searchParams.get('subject'),'classical_mechanics');assert.equal(u.searchParams.get('stars'),'3');
  const a=h.mount.querySelector('.al-problem-row');assert.match(a.getAttribute('href'),/q=mass/);assert.match(a.getAttribute('href'),/problem=q_/);
  a.dispatchEvent(new h.w.MouseEvent('click',{bubbles:true,button:0}));assert.equal(h.navigations.length,1);
});

test('opening a question renders exact escaped text and approved givens without eagerly requesting solutions',async t=>{
  const h=await setup(t,{params:'problem='+Q});assert.match(h.mount.querySelector('.al-prose').textContent,/synthetic statement/);
  assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/solutions')),false);assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/recommendations')),false);
  assert.equal(h.mount.querySelector('[data-pdf]'),null);assert.equal(h.mount.querySelector('iframe'),null);assert.equal(h.mount.querySelector('[data-panel="solutions"]').getAttribute('aria-expanded'),'false');
});

test('solutions are explicit, preserve original authorship and are scoped on the subrequest',async t=>{
  const h=await setup(t,{params:'problem='+Q,route:u=>u.pathname.endsWith('/solutions')?response({solutions:[{authorship:'source_transcription',kind:'answer_only',selected_version:{language:'ko',text:'A source answer.'}},{authorship:'haslalab_original_draft',kind:'worked_solution',selected_version:{language:'ko',text:'A labelled draft.'}}]}):null});
  h.mount.querySelector('[data-panel="solutions"]').click();await flush();assert.match(h.mount.textContent,/A source answer/);assert.match(h.mount.textContent,/원문 풀이/);assert.match(h.mount.textContent,/보완 풀이 초안/);
  assert.equal(h.calls.find(c=>c.url.pathname.endsWith('/solutions')).url.searchParams.get('collection'),'physics');
});

test('closing a pending solution invalidates late text',async t=>{
  const gate=deferred(),h=await setup(t,{params:'problem='+Q,route:u=>u.pathname.endsWith('/solutions')?gate.promise:null});
  const b=h.mount.querySelector('[data-panel="solutions"]');b.click();await flush();b.click();gate.resolve(response({solutions:[{selected_version:{language:'ko',text:'LATE ANSWER'}}]}));await flush();assert.doesNotMatch(h.mount.textContent,/LATE ANSWER/);
});

test('foreign-bank question is rejected before any statement is rendered',async t=>{
  const h=await setup(t,{params:'problem='+Q,route:u=>u.pathname.endsWith('/'+Q)?response({question:question({collection:'astronomy',selected_version:{language:'ko',text:'FOREIGN BODY'}})}):null});
  assert.doesNotMatch(h.mount.textContent,/FOREIGN BODY/);assert.match(h.mount.textContent,/이 분류/);
});

test('dispose aborts pending requests, removes only own DOM and never paints a late response',async t=>{
  const gate=deferred(),h=await setup(t,{params:'source='+SID,route:u=>u.pathname.endsWith('/search')?gate.promise:null});
  const request=h.calls.find(c=>c.url.pathname.endsWith('/search'));h.instance.dispose();assert.equal(request.init.signal.aborted,true);gate.resolve(response({items:[item()]}));await flush();assert.equal(h.mount.children.length,0);assert.equal(h.w.document.getElementById('outside').textContent,'Keep');
});

test('language/scope updates clear prior statement and invalidate the old authenticated request',async t=>{
  const h=await setup(t,{params:'problem='+Q,token:'synthetic-old'});assert.match(h.mount.textContent,/synthetic statement/);
  h.setToken('synthetic-new');h.instance.update({kind:'course',collection:'astronomy',baseHash:'#/archive/schools/astro',params:new URLSearchParams(),lang:'en'});await flush();
  assert.doesNotMatch(h.mount.textContent,/synthetic statement/);assert.equal(h.mount.querySelector('.al').lang,'en');
  for(const c of h.calls.filter(c=>c.init.headers.Authorization==='Bearer synthetic-new')){assert.equal(c.url.searchParams.get('kind'),'course');assert.equal(c.url.searchParams.get('collection'),'astronomy');}
});

test('safe prose protects multiline equations and rejects injected HTML in statements and source titles',async t=>{
  const text='$$\\begin{aligned}\nx&=1\\\\\ny&=2\n\\end{aligned}$$\n\n<img src=x onerror=alert(1)>';
  const h=await setup(t,{params:'problem='+Q,route:u=>u.pathname.endsWith('/'+Q)?response({question:question({source:source(SID,{title:'<svg onload=alert(1)>'}),selected_version:{language:'ko',text}})}):null});
  assert.equal(h.mount.querySelector('svg'),null);assert.equal(h.mount.querySelector('.al-prose img'),null);assert.match(h.mount.querySelector('.al-prose').textContent,/begin\{aligned\}/);assert.equal(h.mount.querySelector('.al-prose p').querySelector('br'),null);
});

test('parent asynchronous math callback is supported without requiring global KaTeX',async t=>{
  let calls=0;const h=await setup(t,{params:'problem='+Q,options:{renderMath:async el=>{calls++;el.dataset.mathChecked='true';}}});assert.equal(calls,1);assert.equal(h.mount.querySelector('[data-content]').dataset.mathChecked,'true');
});

test('approved monochrome flags are applied only to reviewed figures, preserving color images',async t=>{
  const h=await setup(t,{params:'problem='+Q,route:u=>u.pathname.endsWith('/'+Q)?response({question:question({figures:[{id:FIG,url:'/api/problem-bank/figures/'+FIG,placement:'inline',monochrome:true,figure_label:'Fig. 1'},{id:'f_'+'d'.repeat(64),url:'/api/problem-bank/figures/f_'+'d'.repeat(64),placement:'inline',monochrome:false}]})}):u.pathname.includes('/figures/')?response(new (globalThis.Blob)(['PNG'],{type:'image/png'}),200,'image/png'):null});
  const imgs=h.mount.querySelectorAll('.al-figures img');assert.equal(imgs.length,2);assert.equal(imgs[0].className,'al-monochrome');assert.equal(imgs[1].className,'');h.instance.dispose();assert.equal(h.revoked.length,2);
});

test('legacy question lookup is metadata-only before canonical redirect, ignoring conflicting legacy filters',async t=>{
  const h=await setup(t,{params:'problem='+Q+'&source='+SID2+'&subject=optics',options:{resolveLegacy:true},route:u=>u.pathname.endsWith('/'+Q)?response({question:question({source_kind:'course',collection:'astronomy'})}):null});
  assert.equal(h.calls.length,1);assert.equal(h.calls[0].url.searchParams.get('kind'),null);assert.doesNotMatch(h.mount.textContent,/synthetic statement/);
  assert.match(h.navigations[0],/^#\/archive\/schools\/astro\?/);assert.match(h.navigations[0],/source=src_aaaa/);assert.match(h.navigations[0],/topic=optics/);
});

test('admin OCR is gated by verified status, includes scope and never forwards browse cursors',async t=>{
  const h=await setup(t,{params:'cursor=sc_old&stars=2',route:u=>u.pathname.endsWith('/status')?response({questions:2,user:{role:'admin'},ocr_available:true}):u.pathname.endsWith('/identify')?response({candidates:[item()],recognized_text:'Recognized synthetic text'}):null});
  const file=new h.w.File(['x'],'image.png',{type:'image/png'}),input=h.mount.querySelector('[data-photo] input');Object.defineProperty(input,'files',{value:[file]});h.mount.querySelector('[data-photo]').dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();
  const call=h.calls.find(c=>c.url.pathname.endsWith('/identify'));assert.equal(call.init.body.get('collection'),'physics');assert.equal(call.init.body.get('kind'),'book');assert.equal(call.init.body.get('cursor'),null);assert.equal(call.init.body.get('sort'),null);assert.match(h.mount.querySelector('textarea').value,/Recognized/);
  h.mount.querySelector('[data-resubmit]').click();await flush();const retry=h.calls.filter(c=>c.url.pathname.endsWith('/identify'))[1];assert.equal(typeof retry.init.body,'string');assert.equal(JSON.parse(retry.init.body).text,'Recognized synthetic text');
});

test('guest view offers no photo provider action and feedback is fetched only when expanded',async t=>{
  const h=await setup(t,{params:'problem='+Q});assert.equal(h.mount.querySelector('[data-photo]'),null);assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/feedback')),false);
  const d=h.mount.querySelector('[data-feedback]');d.open=true;d.dispatchEvent(new h.w.Event('toggle'));await flush();assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/feedback')).length>=1,true);
});

test('scoped legacy context DTOs remain readable and omit the stale parent source from reference links',async t=>{
  const h=await setup(t,{params:'source='+SID+'&problem='+Q,route:u=>u.pathname.endsWith('/'+Q)?response({question:question({context_links:[{question_id:Q2}]})}):u.pathname.endsWith('/context')?response({contexts:[{id:Q2,original_number:'3.1',source:{title:'Another real source'},selected_version:{language:'ko',text:'Required synthetic input.'}}]}):null});
  h.mount.querySelector('[data-panel="context"]').click();await flush();assert.match(h.mount.textContent,/Required synthetic input/);const a=h.mount.querySelector('.al-context a');assert.equal(a.getAttribute('href'),'#/archive/books/phys?problem='+Q2);
});

test('recommendations omit both current problem and foreign scope, and clear an unrelated parent source',async t=>{
  const h=await setup(t,{params:'source='+SID+'&problem='+Q,route:u=>u.pathname.endsWith('/recommendations')?response({items:[item(),item(Q2,{source_id:SID2}),item('q_'+'3'.repeat(64),{collection:'astronomy'})]}):null});
  h.mount.querySelector('[data-panel="recommendations"]').click();await flush();const a=h.mount.querySelectorAll('[data-panel-content] .al-problem-row');assert.equal(a.length,1);assert.doesNotMatch(a[0].getAttribute('href'),/source=/);
});

test('admin explicit solution captures retain the sa_ namespace and remain lazy',async t=>{
  const asset='sa_'+'e'.repeat(64),h=await setup(t,{params:'problem='+Q,route:u=>u.pathname.endsWith('/status')?response({questions:2,user:{role:'admin'},ocr_available:false}):u.pathname.endsWith('/solutions')?response({solutions:[{authorship:'source_transcription',selected_version:{language:'ko',text:'Synthetic source solution.'},assets:[{id:asset,role:'solution_crop',url:'/api/problem-bank/assets/'+asset}]}]}):u.pathname.endsWith('/'+asset)?response(new Blob(['png'],{type:'image/png'}),200,'image/png'):null});
  h.mount.querySelector('[data-panel="solutions"]').click();await flush();assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/'+asset)),false);const d=h.mount.querySelector('[data-solution-figures]');d.open=true;d.dispatchEvent(new h.w.Event('toggle'));await flush();assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/'+asset)),true);assert.equal(d.querySelectorAll('img').length,1);
});

test('manual difficulty feedback validates inputs and writes only the explicit scoped feedback endpoint',async t=>{
  const h=await setup(t,{params:'problem='+Q,token:'synthetic-user',route:u=>u.pathname.endsWith('/status')?response({questions:2,user:{role:'user'},ocr_available:false}):null});
  const form=h.mount.querySelector('[data-feedback-form]');form.elements.stars.value='4';form.elements.outcome.value='solved';form.elements.minutes.value='25';form.dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();
  const write=h.calls.find(c=>c.init.method==='POST');assert.match(write.url.pathname,/\/feedback$/);assert.equal(write.url.searchParams.get('kind'),'book');assert.deepEqual(JSON.parse(write.init.body),{stars:4,outcome:'solved',minutes:25});assert.match(h.mount.textContent,/평가를 저장/);
});

test('repeated submit while an admin OCR request is pending does not issue a second provider request',async t=>{
  const gate=deferred(),h=await setup(t,{route:u=>u.pathname.endsWith('/status')?response({questions:2,user:{role:'admin'},ocr_available:true}):u.pathname.endsWith('/identify')?gate.promise:null});
  const input=h.mount.querySelector('[data-photo] input');Object.defineProperty(input,'files',{value:[new h.w.File(['x'],'image.png',{type:'image/png'})]});const form=h.mount.querySelector('[data-photo]');
  for(let i=0;i<2;i++)form.dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/identify')).length,1);
  gate.resolve(response({candidates:[item()]}));await flush();
});

test('contest web-view route survives source/question/back/reset links without becoming an API filter',async t=>{
  const h=await setup(t,{params:'view=web',options:{kind:'contest',baseHash:'#/archive/contests/phys'},route:u=>u.pathname.endsWith('/sources')?response({sources:[source(SID,{kind:'contest'})],has_more:false}):u.pathname.endsWith('/search')?response({items:[item(Q,{source_kind:'contest'})]}):null});
  for(const a of h.mount.querySelectorAll('[data-source-list] a,.al-problem-row,.al-reset'))assert.match(a.getAttribute('href'),/view=web/);
  assert(h.calls.every(c=>!c.url.searchParams.has('view')));
});

test('special/general relativity filters remain available even when original book tags are broader',async t=>{
  const h=await setup(t);const values=[...h.mount.querySelectorAll('[name=topic] option')].map(x=>x.value);assert(values.includes('special_relativity'));assert(values.includes('general_relativity'));
});

test('a valid long source cursor above 2048 bytes round-trips from URL through request and next-page anchor',async t=>{
  const cursor='sc_'+Buffer.from(JSON.stringify({key:'a'.repeat(1500),id:Q})).toString('base64url');assert(cursor.length>2048&&cursor.length<=2800);
  const h=await setup(t,{params:'cursor='+cursor,route:u=>u.pathname.endsWith('/search')?response({items:[item()],has_more:true,next_cursor:cursor}):null});
  assert.equal(h.calls.find(c=>c.url.pathname.endsWith('/search')).url.searchParams.get('cursor'),cursor);assert.equal(new URL(h.mount.querySelector('.al-pager a:last-child').href).hash.split('?')[1],new URLSearchParams({cursor}).toString());
});

test('inline equations that fit desktop are contained after narrowing without rerender or small-math tab stops',async t=>{
  let available=900,renders=0;
  const h=await setup(t,{params:'problem='+Q,options:{renderMath:async el=>{
    renders++;const prose=el.querySelector('.al-prose');prose.getBoundingClientRect=()=>({width:available});
    for(const width of [500,30]){const math=el.ownerDocument.createElement('span');math.className='katex';math.textContent='Synthetic math';math.getBoundingClientRect=()=>({width});prose.append(math);}
  }}});
  assert.equal(h.mount.querySelectorAll('.al-inline-equation').length,0);
  Object.defineProperty(h.w.HTMLElement.prototype,'scrollWidth',{configurable:true,get(){return this.classList.contains('al-inline-equation')?500:0;}});
  Object.defineProperty(h.w.HTMLElement.prototype,'clientWidth',{configurable:true,get(){return this.classList.contains('al-inline-equation')?available:0;}});
  available=284;h.w.dispatchEvent(new h.w.Event('resize'));await new Promise(r=>setTimeout(r,35));
  const wrapper=h.mount.querySelector('.al-inline-equation');assert(wrapper);assert.equal(wrapper.tabIndex,0);assert.equal(h.mount.querySelectorAll('.al-inline-equation').length,1);assert.equal(renders,1);
  available=900;h.w.dispatchEvent(new h.w.Event('resize'));await new Promise(r=>setTimeout(r,35));assert.equal(wrapper.hasAttribute('tabindex'),false);assert.equal(renders,1);
  h.instance.dispose();h.w.dispatchEvent(new h.w.Event('resize'));await new Promise(r=>setTimeout(r,25));assert.equal(h.mount.children.length,0);
});

const schools={institutions:[
  {id:'mit',name:{ko:'매사추세츠 공과대학교',en:'MIT'},logo_url:'/assets/mit.svg',source_ids:[SID,SID2],materials:{physics:[]}},
  {id:'snu',name:{ko:'서울대학교',en:'Seoul National University'},logo_url:'/assets/snu.svg',source_ids:[],materials:{physics:[{url:'https://ocw.example.edu/physics',label:{ko:'서울대 공식 물리 공개자료',en:'Official physics materials'}}],mathematics:[{url:'https://ocw.example.edu/math',label:{ko:'공식 수학 자료',en:'Official mathematics materials'}}]}},
  {id:'kaist',name:{ko:'KAIST',en:'KAIST'},logo_url:'/assets/kaist.svg',dark_logo_url:'/assets/kaist-dark.svg',source_ids:[],materials:{physics:[{url:'https://kaist.example.edu/physics',label:{ko:'KAIST 공식 공개자료',en:'Official open materials'}}]}}
]};
const courseSources=[source(SID,{kind:'course',title:'Mechanics problem set 1'}),source(SID2,{kind:'course',title:'Mechanics problem set 2'}),source('src_'+'c'.repeat(64),{kind:'course',title:'Unclassified public paper'})];
const schoolRoute=u=>u.pathname.endsWith('/sources')?response({sources:courseSources,has_more:false}):null;

test('book landing displays verified cover cards and no unsolicited all-question feed',async t=>{
  const h=await setup(t,{options:{bookMedia:{[SID]:{image_url:'/assets/published-cover.jpg',alt:'Verified published cover'}}}});
  const card=h.mount.querySelector('.al-book-card');assert(card);assert.equal(card.querySelector('img').getAttribute('src'),'https://haslalab.org/assets/published-cover.jpg');assert.match(card.textContent,/A Published Book/);assert.match(card.textContent,/Author/);assert.match(card.getAttribute('href'),new RegExp('source='+SID));
  assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/search')),false);assert.equal(h.mount.querySelector('[data-results]').hidden,true);
});

test('missing book covers are an explicit placeholder rather than a fabricated image',async t=>{
  const h=await setup(t);const card=h.mount.querySelector('.al-book-card');assert.equal(card.querySelector('img'),null);assert.match(card.textContent,/표지 이미지 없음/);assert.match(card.textContent,/A Published Book/);
});

test('school landing groups actual papers into institution logo cards and retains unmatched papers separately',async t=>{
  const h=await setup(t,{options:{kind:'course',baseHash:'#/archive/schools/phys',schoolMedia:schools},route:schoolRoute});
  const cards=[...h.mount.querySelectorAll('.al-school-card')];assert.equal(cards.length,4);const mit=cards.find(a=>a.getAttribute('href').includes('school=mit'));assert(mit);assert.equal(mit.querySelector('[data-card-papers]').textContent,'2');assert.equal(mit.querySelector('[data-card-questions]').textContent,'4');assert.equal(mit.querySelector('img').src,'https://haslalab.org/assets/mit.svg');assert.equal(cards.filter(a=>a.textContent.includes('기타 자료')).length,1);
  assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/search')),false);assert.equal(cards.filter(a=>a.textContent.includes('Mechanics problem set')).length,0);
});

test('selected school lists only its exact source IDs and keeps school filter out of API requests',async t=>{
  const h=await setup(t,{params:'school=mit',options:{kind:'course',baseHash:'#/archive/schools/phys',schoolMedia:schools},route:schoolRoute});
  const cards=[...h.mount.querySelectorAll('[data-source-list] a')];assert.equal(cards.length,2);assert(cards.every(a=>a.href.includes('school=mit')&&a.href.includes('source=src_')));assert.doesNotMatch(h.mount.textContent,/Unclassified public paper/);
  assert.equal(h.calls.some(c=>c.url.searchParams.has('school')),false);assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/search')),false);
});

test('SNU official-only entry exposes verified links without inventing digitized questions',async t=>{
  const h=await setup(t,{params:'school=snu',options:{kind:'course',baseHash:'#/archive/schools/phys',schoolMedia:schools},route:schoolRoute});
  assert.match(h.mount.textContent,/현재 이 과목에 등록된 웹 문제는 없습니다/);const a=h.mount.querySelector('.al-official a');assert.equal(a.href,'https://ocw.example.edu/physics');assert.equal(a.target,'_blank');assert.match(a.rel,/noopener/);assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/search')),false);
});

test('school official materials respect selected discipline rather than leaking physics into astronomy',async t=>{
  const h=await setup(t,{options:{kind:'course',collection:'astronomy',baseHash:'#/archive/schools/astro',schoolMedia:schools},route:u=>u.pathname.endsWith('/sources')?response({sources:[],has_more:false}):null});
  assert.equal(h.mount.querySelectorAll('.al-school-card').length,0);assert.equal(h.mount.querySelectorAll('.al-official a').length,0);assert.doesNotMatch(h.mount.textContent,/서울대학교|KAIST/);
});

test('school-wide search explicitly leaves the local school filter instead of filtering a paginated global feed',async t=>{
  const h=await setup(t,{params:'school=mit',options:{kind:'course',baseHash:'#/archive/schools/phys',schoolMedia:schools},route:schoolRoute});
  const form=h.mount.querySelector('[data-search]');form.elements.q.value='oscillation';form.dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));const url=h.navigations.at(-1);assert.match(url,/q=oscillation/);assert.doesNotMatch(url,/school=/);assert.match(h.mount.textContent,/모든 학교 자료/);
});

test('school source selection still uses canonical server browsing and retains deep-link school context',async t=>{
  const h=await setup(t,{params:'school=mit&source='+SID,options:{kind:'course',baseHash:'#/archive/schools/phys',schoolMedia:schools},route:u=>schoolRoute(u)||(u.pathname.endsWith('/search')?response({items:[item(Q,{source_kind:'course'})],has_more:false}):null)});
  const request=h.calls.find(c=>c.url.pathname.endsWith('/search'));assert.equal(request.url.searchParams.get('source'),SID);assert.equal(request.url.searchParams.get('school'),null);const row=h.mount.querySelector('.al-problem-row');assert.match(row.href,/school=mit/);assert.match(row.href,/problem=q_/);
});

test('school logo switches to verified dark artwork without remounting gallery state',async t=>{
  const h=await setup(t,{options:{kind:'course',baseHash:'#/archive/schools/phys',schoolMedia:schools},route:schoolRoute});
  const card=[...h.mount.querySelectorAll('.al-school-card')].find(a=>a.href.includes('school=kaist')),img=card.querySelector('img');assert.equal(img.src,'https://haslalab.org/assets/kaist.svg');h.instance.update({theme:'dark'});assert.equal(card.querySelector('img'),img);assert.equal(img.src,'https://haslalab.org/assets/kaist-dark.svg');
});

test('verified media edition is a fallback while source title and explicit source edition remain authoritative',async t=>{
  const h=await setup(t,{options:{bookMedia:{[SID]:{image_url:'/assets/title-page.jpg',title:'Do not replace published title',edition:'2012 source edition',provenanceKind:'source_title_page'}}}});
  const card=h.mount.querySelector('.al-book-card');assert.match(card.textContent,/A Published Book/);assert.doesNotMatch(card.textContent,/Do not replace published title/);assert.match(card.textContent,/2012 source edition/);assert.match(card.textContent,/표제지/);
});

test('automatic school search normalization replaces history while deliberate school-card navigation pushes',async t=>{
  const h=await setup(t,{params:'school=mit&q=oscillation',options:{kind:'course',baseHash:'#/archive/schools/phys',schoolMedia:schools},route:schoolRoute});
  assert.match(h.navigations[0],/q=oscillation/);assert.doesNotMatch(h.navigations[0],/school=/);assert.equal(h.navigationOptions[0].replace,true);
  const landing=await setup(t,{options:{kind:'course',baseHash:'#/archive/schools/phys',schoolMedia:schools},route:schoolRoute});landing.mount.querySelector('.al-school-card').click();assert.equal(landing.navigationOptions[0].replace,undefined);
});

test('books and schools literally reuse original competition DOM without poster grid or layout overrides',async t=>{
  const book=await setup(t,{options:{bookMedia:{[SID]:{image_url:'/assets/cover.jpg'}}}}),school=await setup(t,{options:{kind:'course',baseHash:'#/archive/schools/phys',schoolMedia:schools},route:schoolRoute});
  for(const h of [book,school]){
    const grid=h.mount.querySelector('div.comps[data-lang="ko"]');assert(grid);assert([...grid.children].every(x=>x.matches('a.comp')));assert.equal(h.mount.querySelector('.al-catalog-heading'),null);
    for(const card of grid.children){assert(card.querySelector('.chead > .abbr'));assert(card.querySelector('.full'));assert.equal(card.querySelectorAll('dl > div').length,4);assert([...card.querySelectorAll('dl > div')].every(d=>d.querySelector('dt')&&d.querySelector('dd')));assert(card.querySelector('span.go'));}
    assert(h.mount.querySelector('.al-search-disclosure [data-source-query]'));assert.equal(h.mount.querySelector('.al-directory > .al-source-find'),null);
  }
  const css=fs.readFileSync(path.resolve(__dirname,'../archive-library.css'),'utf8');assert.doesNotMatch(css,/al-media-grid|al-media-card|\.al-book-cover|\.al-school-logo/);assert.doesNotMatch(css,/\.comps\s*\{[^}]*grid-template-columns/);
});
