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
    if(u.pathname.endsWith('/contents')){const id=u.pathname.split('/').at(-2);return response({source_id:id,source:source(id,{kind:options.kind||'book',collection:options.collection||'physics'}),question_count:2,chapters:[{chapter:'1',title:'1',question_count:1},{chapter:'2',title:'2',question_count:1}]});}
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
  const gate=deferred(),h=await setup(t,{params:'source='+SID+'&chapter=1',route:u=>u.pathname.endsWith('/search')?gate.promise:null});
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
  const h=await setup(t,{token:'synthetic-admin',params:'cursor=sc_old&stars=2',route:u=>u.pathname.endsWith('/status')?response({questions:2,user:{role:'admin'},ocr_available:true}):u.pathname.endsWith('/identify')?response({candidates:[item()],recognized_text:'Recognized synthetic text'}):null});
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
  const asset='sa_'+'e'.repeat(64),h=await setup(t,{token:'synthetic-admin',params:'problem='+Q,route:u=>u.pathname.endsWith('/status')?response({questions:2,user:{role:'admin'},ocr_available:false}):u.pathname.endsWith('/solutions')?response({solutions:[{authorship:'source_transcription',selected_version:{language:'ko',text:'Synthetic source solution.'},assets:[{id:asset,role:'solution_crop',url:'/api/problem-bank/assets/'+asset}]}]}):u.pathname.endsWith('/'+asset)?response(new Blob(['png'],{type:'image/png'}),200,'image/png'):null});
  h.mount.querySelector('[data-panel="solutions"]').click();await flush();assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/'+asset)),false);const d=h.mount.querySelector('[data-solution-figures]');d.open=true;d.dispatchEvent(new h.w.Event('toggle'));await flush();assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/'+asset)),true);assert.equal(d.querySelectorAll('img').length,1);
});

test('manual difficulty feedback validates inputs and writes only the explicit scoped feedback endpoint',async t=>{
  const h=await setup(t,{params:'problem='+Q,token:'synthetic-user',route:u=>u.pathname.endsWith('/status')?response({questions:2,user:{role:'user'},ocr_available:false}):null});
  const form=h.mount.querySelector('[data-feedback-form]');form.elements.stars.value='4';form.elements.outcome.value='solved';form.elements.minutes.value='25';form.dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();
  const write=h.calls.find(c=>c.init.method==='POST');assert.match(write.url.pathname,/\/feedback$/);assert.equal(write.url.searchParams.get('kind'),'book');assert.deepEqual(JSON.parse(write.init.body),{stars:4,outcome:'solved',minutes:25});assert.match(h.mount.textContent,/평가를 저장/);
});

test('repeated submit while an admin OCR request is pending does not issue a second provider request',async t=>{
  const gate=deferred(),h=await setup(t,{token:'synthetic-admin',route:u=>u.pathname.endsWith('/status')?response({questions:2,user:{role:'admin'},ocr_available:true}):u.pathname.endsWith('/identify')?gate.promise:null});
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
  const h=await setup(t,{params:'school=mit&source='+SID+'&chapter=1',options:{kind:'course',baseHash:'#/archive/schools/phys',schoolMedia:schools},route:u=>schoolRoute(u)||(u.pathname.endsWith('/search')?response({items:[item(Q,{source_kind:'course'})],has_more:false}):null)});
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

test('guest landing loads only source metadata and never status or question bodies',async t=>{
  const h=await setup(t);assert.equal(h.calls.length,1);assert(h.calls[0].url.pathname.endsWith('/sources'));
});

test('selecting a book opens its table of contents without loading any chapter questions',async t=>{
  const h=await setup(t,{params:'source='+SID});assert.equal(h.calls.length,1);assert(h.calls[0].url.pathname.endsWith('/contents'));
  assert(h.mount.querySelector('.al-source-layout .al-toc'));assert.equal(h.mount.querySelectorAll('.al-toc li').length,2);
  assert.match(h.mount.querySelector('.al-toc a').href,/chapter=1/);assert.equal(h.mount.querySelector('.al-problem-row'),null);assert(h.mount.querySelector('.al-source-main [data-search]'));assert(h.mount.querySelector('.al-list-instruction'));
});

test('chapter browsing is exact, bounded and summary-only including the empty chapter',async t=>{
  const h=await setup(t,{params:'source='+SID+'&chapter=',route:u=>u.pathname.endsWith('/contents')?response({source_id:SID,source:source(),chapters:[{chapter:'',title:'Technical fallback name',question_count:2}]}):null});
  const request=h.calls.find(c=>c.url.pathname.endsWith('/search'));assert(request);assert.equal(request.url.searchParams.get('chapter'),'');assert.equal(request.url.searchParams.get('limit'),'20');assert.equal(request.url.searchParams.get('summary'),'1');
  assert.match(h.mount.querySelector('.al-results-heading').textContent,/문제 목록/);assert.doesNotMatch(h.mount.textContent,/Technical fallback name/);
  assert.equal(h.mount.querySelector('.al-snippet'),null);assert(h.mount.querySelector('.al-source-layout .al-toc'));
});

test('an unknown chapter fails before requesting a cross-chapter page',async t=>{
  const h=await setup(t,{params:'source='+SID+'&chapter=not-present'});assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/search')),false);assert(h.mount.querySelector('[data-retry]'));
});

test('archive navigation reuses source, contents, chapter and detail reads while solutions stay closed',async t=>{
  const h=await setup(t),root=h.mount.querySelector('.al'),go=async params=>{h.instance.update({params:new URLSearchParams(params)});await flush();};
  await go('source='+SID);await go('source='+SID+'&chapter=1');await go('source='+SID+'&chapter=1&problem='+Q);
  await go('source='+SID+'&chapter=1');await go('');await go('source='+SID+'&chapter=1&problem='+Q);
  assert.equal(h.mount.querySelector('.al'),root);
  for(const suffix of ['/sources','/contents','/search','/'+Q])assert.equal(h.calls.filter(c=>c.url.pathname.endsWith(suffix)).length,1,suffix);
  assert.equal(h.calls.length,4);assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/solutions')),false);
  assert.equal(h.mount.querySelector('[data-panel="solutions"]').getAttribute('aria-expanded'),'false');
});

test('a direct statement renders while contents and authenticated capabilities are pending',async t=>{
  const status=deferred(),toc=deferred(),h=await setup(t,{params:'problem='+Q,token:'synthetic-user',route:u=>u.pathname.endsWith('/status')?status.promise:u.pathname.endsWith('/contents')?toc.promise:null});
  assert.match(h.mount.querySelector('.al-prose').textContent,/synthetic statement/);
  assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/sources')),false);
  const detail=h.calls.find(c=>c.url.pathname.endsWith('/'+Q));assert.equal(detail.init.headers.Authorization,undefined);
  const capability=h.calls.find(c=>c.url.pathname.endsWith('/status'));assert.equal(capability.url.searchParams.get('capabilities'),'1');assert.equal(capability.init.headers.Authorization,'Bearer synthetic-user');
  status.resolve(response({user:{role:'user'},ocr_available:false}));toc.resolve(response({source_id:SID,source:source(),chapters:[]}));await flush();assert(h.mount.querySelector('[data-feedback-form]'));
});

test('rapid chapter navigation joins an in-flight table of contents request',async t=>{
  const gate=deferred(),h=await setup(t,{params:'source='+SID,route:u=>u.pathname.endsWith('/contents')?gate.promise:null});
  h.instance.update({params:new URLSearchParams('source='+SID+'&chapter=2')});await flush();
  gate.resolve(response({source_id:SID,source:source(),chapters:[{chapter:'1',question_count:1},{chapter:'2',question_count:1}]}));await flush();
  assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/contents')).length,1);const request=h.calls.find(c=>c.url.pathname.endsWith('/search'));assert.equal(request.url.searchParams.get('chapter'),'2');
});

test('changing identity invalidates cached chapter and statement data',async t=>{
  const h=await setup(t,{params:'source='+SID+'&chapter=1'});assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/search')).length,1);
  h.setToken('synthetic-user');h.instance.update({params:new URLSearchParams('source='+SID+'&chapter=1')});await flush();
  assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/contents')).length,2);assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/search')).length,2);
  for(const c of h.calls.filter(c=>c.url.pathname.endsWith('/contents')||c.url.pathname.endsWith('/search')))assert.equal(c.init.headers.Authorization,undefined);
});

test('detected administrator demotion removes protected controls and cached administrator details',async t=>{
  let role='admin';const h=await setup(t,{params:'problem='+Q,token:'synthetic-admin',options:{getUser:()=>({role:'admin'})},route:(u,init)=>u.pathname.endsWith('/status')?response({user:{role},ocr_available:role==='admin'}):u.pathname.endsWith('/'+Q)?response({question:question({can_view_source:role==='admin'&&!!init.headers.Authorization})}):null});
  assert(h.mount.querySelector('[data-pdf]'));const now=h.w.Date.now();h.w.Date.now=()=>now+31000;role='user';h.instance.update({params:new URLSearchParams('problem='+Q+'&stars=2')});await flush();
  assert.equal(h.mount.querySelector('[data-pdf]'),null);assert.equal(h.mount.querySelector('[data-raw]'),null);
  const calls=h.calls.filter(c=>c.url.pathname.endsWith('/'+Q));assert.equal(calls.at(-1).init.headers.Authorization,undefined);
});

test('old book and question aliases redirect to the admitted canonical records',async t=>{
  const sourceAlias=await setup(t,{params:'source='+SID2,route:u=>u.pathname.endsWith('/contents')?response({source_id:SID,source:source(),chapters:[]}):null});
  assert.equal(sourceAlias.navigations[0],'#/archive/books/phys?source='+SID);assert.equal(sourceAlias.navigationOptions[0].replace,true);
  const legacy=await setup(t,{params:'problem='+Q2,options:{resolveLegacy:true},route:u=>u.pathname.endsWith('/'+Q2)?response({question:question({canonical_id:Q,display_source_id:SID})}):null});
  assert.match(legacy.navigations[0],new RegExp('problem='+Q));assert.match(legacy.navigations[0],new RegExp('source='+SID));assert.equal(legacy.calls.length,1);
});

test('distinct edition variants with the same printed number remain separate and labelled',async t=>{
  const h=await setup(t,{params:'source='+SID+'&chapter=1',route:u=>u.pathname.endsWith('/search')?response({items:[item(Q,{original_number:'3.17'}),item(Q2,{source_id:SID2,display_source_id:SID,original_number:'3.17',edition_label:'2012 edition',edition_original_number:'3.17'})]}):null});
  const rows=h.mount.querySelectorAll('.al-problem-row');assert.equal(rows.length,2);assert(rows[1].href.includes('source='+SID));assert(rows[1].href.includes('chapter=1'));assert.match(rows[1].textContent,/2012 edition/);assert.notEqual(rows[0].href,rows[1].href);
});
test('book contents use source-specific bilingual chapter names with one chapter prefix',async t=>{
  const bookMedia={[SID]:{chapter_titles:{'1':{ko:'맥스웰 방정식',en:'The Maxwell Equations'},F:{ko:'곡선좌표',en:'Curvilinear coordinates'}}}};
  const h=await setup(t,{params:'source='+SID,options:{bookMedia},route:u=>u.pathname.endsWith('/contents')?response({source_id:SID,source:source(),chapters:[{chapter:'1',title:'1',question_count:1},{chapter:'F',title:'F',question_count:1}]}):null});
  const labels=()=>[...h.mount.querySelectorAll('.al-toc li a>span')].map(x=>x.textContent);
  assert.deepEqual(labels(),['제1장 · 맥스웰 방정식','부록 F · 곡선좌표']);assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/search')),false);
  h.instance.update({lang:'en'});await flush();assert.deepEqual(labels(),['Chapter 1 · The Maxwell Equations','Appendix F · Curvilinear coordinates']);
});
test('chapter name lookup remains bound to its source instead of leaking another book title',async t=>{
  const h=await setup(t,{params:'source='+SID+'&chapter=1',options:{bookMedia:{[SID2]:{chapter_titles:{'1':{ko:'다른 교재 제목',en:'Unrelated chapter'}}}}}});
  assert.doesNotMatch(h.mount.textContent,/다른 교재 제목|Unrelated chapter/);assert.equal(h.mount.querySelector('.al-results-heading h3').textContent,'제1장');
});
test('source-bound chapter order ranks known parts and preserves unknown API order and exact keys',async t=>{
  const chapterList=[{chapter:'unknown-z',title:'Unlisted Z',question_count:1},{chapter:'rigid-body-dynamics',question_count:2},{chapter:'dynamics-of-a-point-mass',question_count:3},{chapter:'unknown-a',title:'Unlisted A',question_count:1}];
  const metadata={chapter_order:['dynamics-of-a-point-mass','rigid-body-dynamics'],chapter_titles:{'dynamics-of-a-point-mass':{ko:'질점의 운동',en:'Dynamics of a point mass'},'rigid-body-dynamics':{ko:'강체의 운동',en:'Rigid-body dynamics'}}};
  const h=await setup(t,{params:'source='+SID,options:{bookMedia:{[SID]:metadata}},route:u=>u.pathname.endsWith('/contents')?response({source_id:SID,source:source(),chapters:chapterList}):null});
  const links=[...h.mount.querySelectorAll('.al-toc li a')],chapterOf=link=>new URLSearchParams(link.hash.split('?')[1]).get('chapter');
  assert.deepEqual(links.map(chapterOf),['dynamics-of-a-point-mass','rigid-body-dynamics','unknown-z','unknown-a']);assert.deepEqual(links.slice(0,2).map(a=>a.querySelector('span').textContent),['질점의 운동','강체의 운동']);assert.equal(h.calls.length,1);
  assert.deepEqual(chapterList.map(c=>c.chapter),['unknown-z','rigid-body-dynamics','dynamics-of-a-point-mass','unknown-a'],'shared response data must not be reordered in place');
  h.instance.update({lang:'en'});await flush();assert.equal(h.mount.querySelector('.al-toc li a>span').textContent,'Dynamics of a point mass');
});
test('chapter ordering metadata from another source cannot reorder the current book',async t=>{
  const h=await setup(t,{params:'source='+SID,options:{bookMedia:{[SID2]:{chapter_order:['2','1']}}}});assert.deepEqual([...h.mount.querySelectorAll('.al-toc li a>span')].map(x=>x.textContent),['제1장','제2장']);assert.equal(h.calls.length,1);
});

test('flat books open a bounded first page without contents or a repeated source request',async t=>{
  const h=await setup(t,{options:{bookMedia:{[SID]:{short_title:'PUZZLING',full_title:'200 Puzzling Physics Problems',browse_mode:'flat'}}}});
  h.instance.update({params:new URLSearchParams('source='+SID)});await flush();
  assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/sources')).length,1);assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/contents')),false);
  const search=h.calls.find(c=>c.url.pathname.endsWith('/search'));assert.equal(search.url.searchParams.get('limit'),'20');assert.equal(search.url.searchParams.get('source'),SID);assert.equal(search.url.searchParams.has('chapter'),false);
  assert.equal(h.mount.querySelector('.al-toc'),null);assert(h.mount.querySelector('.al-problem-row'));assert.match(h.mount.querySelector('h2').textContent,/PUZZLING/);
});

test('direct flat-book links verify source metadata and never fetch a fabricated table of contents',async t=>{
  const h=await setup(t,{params:'source='+SID,options:{bookMedia:{[SID]:{browse_mode:'flat'}}}});assert.equal(h.calls.length,2);
  assert.deepEqual(h.calls.map(c=>c.url.pathname.split('/').at(-1)),['sources','search']);assert.equal(h.mount.querySelector('.al-toc'),null);
});
test('flat-book statements skip contents and return to their paged list without an invented chapter',async t=>{
  const h=await setup(t,{params:'source='+SID+'&problem='+Q,options:{bookMedia:{[SID]:{browse_mode:'flat'}}},route:u=>u.pathname.endsWith('/'+Q)?response({question:question({chapter:'old-classification'})}):null});
  assert.equal(h.calls.length,1);assert.equal(h.mount.querySelector('.al-toc'),null);assert.equal(h.mount.querySelector('.al-reading-layout').classList.contains('has-toc'),false);assert.doesNotMatch(h.mount.querySelector('.al-reader-nav a').href,/chapter=/);
});

test('part selection loads one chapter page and folding contents is local and remembered per source',async t=>{
  const h=await setup(t,{params:'source='+SID}),choose=h.mount.querySelector('.al-toc a');choose.click();
  const target=new URL(h.navigations.at(-1),'https://haslalab.org/').hash.split('?')[1];h.instance.update({params:new URLSearchParams(target)});await flush();
  assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/contents')).length,1);assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/search')).length,1);
  const before=h.calls.length,toggle=h.mount.querySelector('[data-toggle-toc]');toggle.click();assert.equal(toggle.getAttribute('aria-expanded'),'false');assert.equal(h.mount.querySelector('.al-toc nav').hidden,true);assert(h.mount.querySelector('.al-source-layout').classList.contains('is-toc-collapsed'));assert.equal(h.calls.length,before);
  h.instance.update({params:new URLSearchParams('source='+SID+'&chapter=2')});await flush();assert.equal(h.mount.querySelector('[data-toggle-toc]').getAttribute('aria-expanded'),'false');
  h.instance.update({params:new URLSearchParams('source='+SID2)});await flush();assert.equal(h.mount.querySelector('[data-toggle-toc]').getAttribute('aria-expanded'),'true');
  h.instance.update({params:new URLSearchParams('source='+SID)});await flush();assert.equal(h.mount.querySelector('[data-toggle-toc]').getAttribute('aria-expanded'),'false');
  const count=h.calls.length;h.mount.querySelector('[data-toggle-toc]').click();assert.equal(h.calls.length,count);assert.equal(h.mount.querySelector('.al-toc nav').hidden,false);
});

test('text typing and scope selection issue no requests until explicit submit and clear old cursors',async t=>{
  const h=await setup(t,{params:'source='+SID+'&chapter=1&cursor=sc_previous'}),input=h.mount.querySelector('[data-search] [name=q]'),scope=h.mount.querySelector('[data-search-scope]');
  const count=h.calls.length;input.value='uniform field';input.dispatchEvent(new h.w.Event('input',{bubbles:true}));scope.value='book';scope.dispatchEvent(new h.w.Event('change',{bubbles:true}));await flush();assert.equal(h.calls.length,count);
  h.mount.querySelector('[data-search]').dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));const target=h.navigations.at(-1);assert.match(target,/source=src_/);assert.match(target,/q=uniform\+field/);assert.doesNotMatch(target,/chapter=|cursor=/);
  h.instance.update({params:new URLSearchParams(target.split('?')[1])});await flush();const search=h.calls.filter(c=>c.url.pathname.endsWith('/search')).at(-1);assert.equal(search.url.searchParams.get('source'),SID);assert.equal(search.url.searchParams.get('q'),'uniform field');assert.equal(search.url.searchParams.has('chapter'),false);assert.equal(search.url.searchParams.get('offset'),'0');
});

test('text search keeps the selected chapter when its visible scope is selected',async t=>{
  const h=await setup(t,{params:'source='+SID+'&chapter=2'});assert.equal(h.mount.querySelector('[data-search-scope]').value,'chapter');
  const form=h.mount.querySelector('[data-search]');form.elements.q.value='charge';form.dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));assert.match(h.navigations.at(-1),/chapter=2/);
});

test('OCR tab is visible but guest and ordinary accounts cannot submit provider calls',async t=>{
  for(const token of ['', 'synthetic-user']){
    const h=await setup(t,{params:'source='+SID,token,route:u=>u.pathname.endsWith('/status')?response({user:{role:'user'},ocr_available:false}):null});
    const before=h.calls.length;h.mount.querySelector('[data-search-mode=ocr]').click();assert.equal(h.mount.querySelector('[data-search-pane=ocr]').hidden,false);assert(h.mount.querySelector('[data-photo] fieldset').disabled);assert.match(h.mount.textContent,/관리자만/);
    const file=h.mount.querySelector('[data-photo] input');Object.defineProperty(file,'files',{value:[new h.w.File(['x'],'question.png',{type:'image/png'})]});h.mount.querySelector('[data-photo]').dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();assert.equal(h.calls.length,before);assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/identify')),false);
  }
});

test('admin OCR multipart uses the selected book and the allowed fields without chapter or summary',async t=>{
  const h=await setup(t,{params:'source='+SID+'&chapter=1&stars=2&topic=classical_mechanics&cursor=sc_old',token:'synthetic-admin',route:u=>u.pathname.endsWith('/status')?response({user:{role:'admin'},ocr_available:true}):u.pathname.endsWith('/identify')?response({candidates:[item()],recognized_text:'Recognized test text'}):null});
  h.mount.querySelector('[data-search-mode=ocr]').click();const scope=h.mount.querySelector('[data-search-scope]');assert.equal(scope.value,'book');assert.equal(scope.disabled,true);
  const input=h.mount.querySelector('[data-photo] input');Object.defineProperty(input,'files',{value:[new h.w.File(['x'],'question.png',{type:'image/png'})]});h.mount.querySelector('[data-photo]').dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();
  const call=h.calls.find(c=>c.url.pathname.endsWith('/identify'));assert(call);const body=call.init.body,keys=[...body.keys()],allowed=new Set(['lang','subject','source','collection','stars','kind','competition','year','type','limit','image']);assert(keys.every(key=>allowed.has(key)));assert.equal(body.get('source'),SID);assert.equal(body.get('kind'),'book');assert.equal(body.get('collection'),'physics');assert.equal(body.get('chapter'),null);assert.equal(body.get('summary'),null);assert.equal(body.get('cursor'),null);
});
test('unchanged text submission after OCR restores text results from cache without relying on hashchange',async t=>{
  const h=await setup(t,{params:'source='+SID+'&chapter=1',token:'synthetic-admin',route:u=>u.pathname.endsWith('/status')?response({user:{role:'admin'},ocr_available:true}):u.pathname.endsWith('/search')?response({items:[item(Q,{title_ko:'정상 검색 결과'})]}):u.pathname.endsWith('/identify')?response({candidates:[item(Q2,{title_ko:'사진 인식 후보'}),item('q_'+'4'.repeat(64),{source_id:SID2,title_ko:'다른 교재 후보'})]}):null});
  h.mount.querySelector('[data-search-mode=ocr]').click();const input=h.mount.querySelector('[data-photo] input');Object.defineProperty(input,'files',{value:[new h.w.File(['x'],'question.png',{type:'image/png'})]});h.mount.querySelector('[data-photo]').dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();
  assert.match(h.mount.querySelector('[data-results]').textContent,/사진 인식 후보/);assert.doesNotMatch(h.mount.querySelector('[data-results]').textContent,/다른 교재 후보/);
  const count=h.calls.length;h.mount.querySelector('[data-toggle-toc]').click();assert.equal(h.calls.length,count);h.mount.querySelector('[data-search-mode=text]').click();
  h.mount.querySelector('[data-search]').dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();assert.match(h.mount.querySelector('[data-results]').textContent,/정상 검색 결과/);assert.doesNotMatch(h.mount.querySelector('[data-results]').textContent,/사진 인식 후보/);assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/search')).length,1);assert.equal(h.navigations.length,0);
  h.mount.querySelector('[data-search]').dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();assert.equal(h.calls.length,count);
});
test('invalid text submissions keep valid OCR results, and a different source clears those candidates',async t=>{
  const h=await setup(t,{params:'source='+SID,token:'synthetic-admin',route:u=>u.pathname.endsWith('/status')?response({user:{role:'admin'},ocr_available:true}):u.pathname.endsWith('/identify')?response({candidates:[item(Q2,{title_ko:'유효한 사진 후보'})]}):null});
  const photo=h.mount.querySelector('[data-photo] input');Object.defineProperty(photo,'files',{value:[new h.w.File(['x'],'q.png',{type:'image/png'})]});h.mount.querySelector('[data-photo]').dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();const count=h.calls.length;
  const form=h.mount.querySelector('[data-search]');form.elements.q.value='x'.repeat(601);form.dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();assert.match(h.mount.querySelector('[data-results]').textContent,/유효한 사진 후보/);assert.equal(h.calls.length,count);
  h.instance.update({params:new URLSearchParams('source='+SID2)});await flush();assert.doesNotMatch(h.mount.textContent,/유효한 사진 후보/);assert(h.mount.querySelector('.al-list-instruction'));assert.equal(h.calls.some(c=>c.url.pathname.endsWith('/search')),false);
});
test('a late OCR success or error cannot replace a newer unchanged-URL text search',async t=>{
  for(const status of [200,500]){
    const gate=deferred(),h=await setup(t,{params:'source='+SID+'&chapter=1',token:'synthetic-admin',route:u=>u.pathname.endsWith('/status')?response({user:{role:'admin'},ocr_available:true}):u.pathname.endsWith('/search')?response({items:[item(Q,{title_ko:'최신 텍스트 결과'})]}):u.pathname.endsWith('/identify')?gate.promise:null});
    const photo=h.mount.querySelector('[data-photo] input');Object.defineProperty(photo,'files',{value:[new h.w.File(['x'],'q.png',{type:'image/png'})]});h.mount.querySelector('[data-photo]').dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();
    h.mount.querySelector('[data-search-mode=text]').click();h.mount.querySelector('[data-search]').dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();assert.match(h.mount.querySelector('[data-results]').textContent,/최신 텍스트 결과/);
    gate.resolve(response(status===200?{candidates:[item(Q2,{title_ko:'늦은 사진 후보'})]}:{error:'old_ocr_failure'},status));await flush();
    assert.match(h.mount.querySelector('[data-results]').textContent,/최신 텍스트 결과/);assert.doesNotMatch(h.mount.textContent,/늦은 사진 후보|old_ocr_failure/);assert.equal(h.mount.querySelector('[data-message]').textContent,'');assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/identify')).length,1);assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/search')).length,1);assert.equal(h.mount.querySelector('[data-photo] button').disabled,false);
  }
});
test('invalid text leaves an already pending OCR action valid',async t=>{
  const gate=deferred(),h=await setup(t,{params:'source='+SID,token:'synthetic-admin',route:u=>u.pathname.endsWith('/status')?response({user:{role:'admin'},ocr_available:true}):u.pathname.endsWith('/identify')?gate.promise:null});
  const photo=h.mount.querySelector('[data-photo] input');Object.defineProperty(photo,'files',{value:[new h.w.File(['x'],'q.png',{type:'image/png'})]});h.mount.querySelector('[data-photo]').dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();
  const form=h.mount.querySelector('[data-search]');form.elements.q.value='x'.repeat(601);form.dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));gate.resolve(response({candidates:[item(Q2,{title_ko:'원래 사진 요청 결과'})]}));await flush();assert.match(h.mount.querySelector('[data-results]').textContent,/원래 사진 요청 결과/);assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/identify')).length,1);
});
test('only an explicit image identify upload receives the scan timeout and it is never retried',async t=>{
  const scan=deferred(),corrected=deferred(),h=await setup(t,{params:'source='+SID,token:'synthetic-admin',route:(u,init)=>u.pathname.endsWith('/status')?response({user:{role:'admin'},ocr_available:true}):u.pathname.endsWith('/identify')?(typeof init.body==='string'?corrected.promise:scan.promise):null});
  const originalSet=h.w.setTimeout.bind(h.w),originalClear=h.w.clearTimeout.bind(h.w),timers=new Map();let next=100000;
  h.w.setTimeout=(fn,delay,...args)=>{if(delay<20000)return originalSet(fn,delay,...args);const id=++next;timers.set(id,{fn,delay});return id;};h.w.clearTimeout=id=>{if(!timers.delete(id))originalClear(id);};
  const input=h.mount.querySelector('[data-photo] input');Object.defineProperty(input,'files',{value:[new h.w.File(['x'],'q.png',{type:'image/png'})]});const form=h.mount.querySelector('[data-photo]');form.dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();
  const call=h.calls.find(c=>c.url.pathname.endsWith('/identify'));assert.deepEqual([...timers.values()].map(timer=>timer.delay),[120000]);for(const timer of timers.values())if(timer.delay<=20000)timer.fn();assert.equal(call.init.signal.aborted,false);
  form.dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/identify')).length,1);
  scan.resolve(response({candidates:[item()],recognized_text:'Recognized test text'}));await flush();assert.equal(timers.size,0);h.mount.querySelector('[data-resubmit]').click();await flush();assert.deepEqual([...timers.values()].map(timer=>timer.delay),[20000]);
  corrected.resolve(response({candidates:[item()]}));await flush();assert.equal(h.calls.filter(c=>c.url.pathname.endsWith('/identify')&&c.init.body instanceof h.w.FormData).length,1);assert.equal(timers.size,0);
  h.w.setTimeout=originalSet;h.w.clearTimeout=originalClear;
});

test('search tabs support keyboard selection without clearing text or fetching data',async t=>{
  const h=await setup(t,{params:'source='+SID}),input=h.mount.querySelector('[name=q]');input.value='unsent text';const count=h.calls.length;
  h.mount.querySelector('[data-search-mode=text]').dispatchEvent(new h.w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true}));assert.equal(h.mount.querySelector('[data-search-mode=ocr]').getAttribute('aria-selected'),'true');
  h.mount.querySelector('[data-search-mode=ocr]').dispatchEvent(new h.w.KeyboardEvent('keydown',{key:'Home',bubbles:true,cancelable:true}));assert.equal(input.value,'unsent text');assert.equal(h.mount.querySelector('[data-search-pane=text]').hidden,false);assert.equal(h.calls.length,count);
});

test('book aliases and volume topics are prominent while full published titles remain searchable',async t=>{
  const h=await setup(t,{options:{bookMedia:{[SID]:{short_title:'PNS',topic_label:{ko:'역학',en:'Mechanics'},topic_prominent:true,full_title:'Problems and Solutions on Mechanics'}}}});
  const card=h.mount.querySelector('.al-book-card');assert.match(card.querySelector('.abbr').textContent,/PNS/);assert.equal(card.querySelector('.al-card-topic.prominent').textContent,'역학');assert.equal(card.querySelector('.full').textContent,'Problems and Solutions on Mechanics');
  const filter=h.mount.querySelector('[data-source-query]');filter.value='PNS';filter.dispatchEvent(new h.w.Event('input',{bubbles:true}));assert.equal(h.mount.querySelectorAll('.al-book-card').length,1);filter.value='Problems and Solutions on Mechanics';filter.dispatchEvent(new h.w.Event('input',{bubbles:true}));assert.equal(h.mount.querySelectorAll('.al-book-card').length,1);
});

test('official book references use real external links without phantom question identities or counts',async t=>{
  const references=[{id:'goldstein',title:{ko:'골드슈타인',en:'Goldstein'},full_title:{ko:'Classical Mechanics Goldstein',en:'Classical Mechanics Goldstein'},short_title:'GOLDSTEIN',author:'Goldstein',collection:'physics',href:'https://www.pearson.com/book',availability:'digitization_pending',resource_kind:'textbook'},{id:'kzhou',title:{ko:'K. Zhou 문제자료',en:'K. Zhou handouts'},short_title:'KZHOU',collection:'physics',href:'https://knzhou.github.io/teaching/',availability:'official_online',resource_kind:'handouts'},{id:'bad',title:'Bad',collection:'physics',href:'javascript:alert(1)'},{id:'astro-only',title:'Astro',collection:'astronomy',href:'https://example.edu/'}];
  const h=await setup(t,{options:{bookReferences:references}}),cards=h.mount.querySelectorAll('.al-reference-card');assert.equal(cards.length,2);assert.match(cards[0].textContent,/웹문항 준비 중/);assert.match(cards[1].textContent,/공식 문제자료/);
  for(const card of cards){assert.equal(card.target,'_blank');assert.match(card.rel,/noopener/);assert.equal(new URL(card.href).protocol,'https:');assert.equal(card.querySelector('[data-card-questions]'),null);assert.equal(card.querySelector('img'),null);assert(!card.href.includes('source=src_'));}
  assert.equal(h.mount.querySelectorAll('[data-card-questions]').length,1);const filter=h.mount.querySelector('[data-source-query]');filter.value='Goldstein';filter.dispatchEvent(new h.w.Event('input',{bubbles:true}));assert.equal(h.mount.querySelectorAll('.al-reference-card').length,1);assert.equal(h.mount.querySelectorAll('.al-book-card').length,0);assert.equal(h.calls.length,1);
});
