const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {createRequire}=require('node:module');
const {JSDOM}=createRequire(path.resolve(__dirname,'../community/package.json'))('jsdom');
const root=path.resolve(__dirname,'..'),read=name=>fs.readFileSync(path.join(root,name),'utf8');
const API='https://haslalab-problem-bank.haslalab.workers.dev';
const Q1='q_'+'1'.repeat(64),Q2='q_'+'2'.repeat(64),SOURCE='src_'+'a'.repeat(64),FIGURE='f_'+'b'.repeat(64);
const item=(id=Q1)=>({id,source_id:SOURCE,source_title:'Synthetic physics source',locator:'problem-1',original_number:'1',subjects:['classical_mechanics'],snippet:'A mass $m$ moves along a plane.',review_status:'pending',unresolved_source:true,difficulty:{stars:3,status:'provisional'}});
const response=(data,status=200)=>({ok:status>=200&&status<300,status,headers:{get:()=>null},json:async()=>data});
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject};};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function flush(){for(let n=0;n<4;n++)await tick();}
async function harness(t,{token='',statusData={questions:2,user:null,ocr_available:false},route,embedded=false,params=''}={}){
  const parent=new JSDOM('<!doctype html><body></body>',{url:'https://haslalab.org/'}),posts=[];
  parent.window.postMessage=(data,origin)=>posts.push({data,origin});
  const dom=new JSDOM(read('problem-search.html'),{url:'https://haslalab.org/problem-search.html?lang=ko&theme=light'+(embedded?'&embed=1':'')+params,runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window,calls=[],urls=[],revoked=[];
  if(embedded)Object.defineProperty(w,'parent',{value:parent.window});
  w.matchMedia=query=>({matches:false,media:query,addEventListener(){}});
  w.URL.createObjectURL=blob=>{const url='blob:fixture-'+urls.length;urls.push({url,blob});return url;};
  w.URL.revokeObjectURL=url=>revoked.push(url);
  if(token)w.localStorage.setItem('hlCmTok',token);
  w.fetch=async(url,options={})=>{
    const target=new URL(url);calls.push({target,options});
    const custom=route?.(target,options,calls,w);if(custom!==undefined)return await custom;
    if(target.pathname.endsWith('/status'))return response(statusData);
    if(target.pathname.endsWith('/sources'))return response({sources:[{id:SOURCE,title:'Synthetic physics source'}]});
    if(target.pathname.endsWith('/search'))return response({items:[item()],has_more:false});
    if(target.pathname.endsWith('/identify'))return response({items:[item(Q2)],recognized_text:'A mass m moves along a plane.',has_more:false,automatic_match_confirmed:false});
    if(target.pathname.includes('/questions/'))return response({question:{id:target.pathname.split('/').at(-1),source:{title:'Synthetic physics source'},locator:'problem-1',review_status:'pending',selected_version:{language:target.searchParams.get('lang'),text:'Find the acceleration $a$.'},figures:[]}});
    throw Error('Unexpected endpoint '+target.href);
  };
  t.after(()=>{w.dispatchEvent(new w.Event('pagehide'));dom.window.close();parent.window.close();});
  w.eval(read('problem-search.js'));await flush();
  return{w,document:w.document,calls,posts,parent:parent.window,urls,revoked,submit:()=>w.document.getElementById('searchForm').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true})),send:(data,{origin='https://haslalab.org',source=parent.window}={})=>w.dispatchEvent(new w.MessageEvent('message',{data,origin,source}))};
}

test('guest search is public, bounded and renders untrusted result text without HTML',async t=>{
  const h=await harness(t,{params:'&token=untrusted-url-token',route:url=>url.pathname.endsWith('/search')?response({items:Array.from({length:25},(_,n)=>({...item('q_'+n.toString(16).padStart(64,'0')),source_title:'<img src=x onerror=alert(1)>',snippet:'<script>bad()</script>'})),has_more:true,next_cursor:Q2}):undefined});
  assert.equal(h.document.querySelectorAll('.result-card').length,20);
  assert.equal(h.document.querySelector('#results img'),null);
  assert.equal(h.document.querySelector('#results script'),null);
  assert.match(h.document.querySelector('#results').textContent,/<script>bad/);
  assert.equal(h.document.getElementById('photoControls').disabled,true);
  assert.equal(h.document.getElementById('identifyText').disabled,false);
  assert.equal(h.w.localStorage.length,0);
  for(const call of h.calls){assert.equal(call.target.origin,API);assert.equal(call.options.credentials,'omit');assert.equal(call.options.cache,'no-store');assert.equal(call.options.redirect,'error');assert.equal(call.options.headers.Authorization,undefined);assert.equal(call.target.searchParams.has('token'),false);}
  const search=h.calls.find(call=>call.target.pathname.endsWith('/search'));
  assert.equal(search.target.searchParams.get('limit'),'20');
  assert.equal(h.document.getElementById('next').disabled,false);
});

test('photo controls require verified admin plus OCR capability, not a local token or advertised OCR alone',async t=>{
  const pending=deferred();
  const h=await harness(t,{token:'fixture-session-token',route:url=>url.pathname.endsWith('/status')?pending.promise:undefined});
  assert.equal(h.document.getElementById('photoControls').disabled,true);
  pending.resolve(response({questions:1,user:{role:'user'},ocr_available:true}));await flush();
  assert.equal(h.document.getElementById('photoControls').disabled,true);
  const admin=await harness(t,{token:'fixture-admin-token',statusData:{questions:1,user:{role:'admin'},ocr_available:true}});
  assert.equal(admin.document.getElementById('photoControls').disabled,false);
  assert.equal(admin.document.getElementById('photoAccess').hidden,true);
  for(const call of admin.calls)assert.equal(call.options.headers.Authorization,'Bearer fixture-admin-token');
});

test('public text identification uses JSON without OCR and enforces separate input limits',async t=>{
  const h=await harness(t),query=h.document.getElementById('query');
  query.value='mass '.repeat(150);h.submit();await flush();
  assert.match(h.document.getElementById('status').textContent,/600/);
  assert.equal(h.calls.filter(call=>call.target.pathname.endsWith('/search')).length,1);
  h.document.getElementById('identifyText').click();await flush();
  const identify=h.calls.find(call=>call.target.pathname.endsWith('/identify'));
  assert.ok(identify);assert.equal(identify.options.headers['Content-Type'],'application/json');
  const body=JSON.parse(identify.options.body);assert.equal(body.text,query.value);assert.equal(body.limit,20);assert.equal(body.image,undefined);assert.equal(identify.options.headers.Authorization,undefined);
  assert.match(h.document.getElementById('status').textContent,/자동 확정되지/);
  assert.equal(h.document.getElementById('next').disabled,true);
  query.value='x'.repeat(12001);h.document.getElementById('identifyText').click();await flush();
  assert.equal(h.calls.filter(call=>call.target.pathname.endsWith('/identify')).length,1);
});

test('admin photo selection previews locally; only submit invokes OCR and correction uses JSON',async t=>{
  const h=await harness(t,{token:'fixture-admin-token',statusData:{questions:1,user:{role:'admin'},ocr_available:true}});
  const input=h.document.getElementById('photo'),file=new h.w.File(['fixture'],'question.png',{type:'image/png'});
  Object.defineProperty(input,'files',{value:[file],configurable:true});input.dispatchEvent(new h.w.Event('change'));await flush();
  assert.equal(h.calls.filter(call=>call.target.pathname.endsWith('/identify')).length,0);
  assert.equal(h.document.getElementById('photoPreview').hidden,false);
  h.document.getElementById('photoForm').dispatchEvent(new h.w.Event('submit',{bubbles:true,cancelable:true}));await flush();
  const first=h.calls.find(call=>call.target.pathname.endsWith('/identify'));
  assert.ok(first.options.body instanceof h.w.FormData);assert.equal(first.options.body.get('image').name,'question.png');assert.equal(first.options.body.get('limit'),'20');
  assert.equal(h.document.getElementById('recognizedPanel').hidden,false);
  h.document.getElementById('recognized').value='Corrected mass and equation m a = F.';h.document.getElementById('searchRecognized').click();await flush();
  const second=h.calls.filter(call=>call.target.pathname.endsWith('/identify')).at(-1);
  assert.equal(second.options.headers['Content-Type'],'application/json');assert.match(JSON.parse(second.options.body).text,/Corrected mass/);
  assert.equal(h.calls.filter(call=>call.options.body instanceof h.w.FormData).length,1);
  const badFile=new h.w.File(['x'],'question.svg',{type:'image/svg+xml'});Object.defineProperty(input,'files',{value:[badFile],configurable:true});input.dispatchEvent(new h.w.Event('change'));await flush();
  assert.match(h.document.getElementById('status').textContent,/8MB/);
});

test('cursor browse and query pagination retain filters and disable old-query pages',async t=>{
  const h=await harness(t,{route:url=>url.pathname.endsWith('/search')?response({items:[item()],has_more:true,next_cursor:Q2}):undefined});
  h.document.getElementById('next').click();await flush();
  let latest=h.calls.filter(call=>call.target.pathname.endsWith('/search')).at(-1);
  assert.equal(latest.target.searchParams.get('cursor'),Q2);assert.equal(latest.target.searchParams.has('offset'),false);
  h.document.getElementById('query').value='angular momentum';h.document.getElementById('query').dispatchEvent(new h.w.Event('input'));
  assert.equal(h.document.getElementById('next').disabled,true);
  h.document.getElementById('subject').value='classical_mechanics';h.document.getElementById('source').value=SOURCE;h.submit();await flush();h.document.getElementById('next').click();await flush();
  latest=h.calls.filter(call=>call.target.pathname.endsWith('/search')).at(-1);
  assert.equal(latest.target.searchParams.get('offset'),'20');assert.equal(latest.target.searchParams.get('q'),'angular momentum');assert.equal(latest.target.searchParams.get('subject'),'classical_mechanics');assert.equal(latest.target.searchParams.get('source'),SOURCE);
});

test('cancelled requests cannot paint a late success and network failures remain explicit',async t=>{
  const pending=deferred();let initial=true;
  const h=await harness(t,{route:url=>{if(url.pathname.endsWith('/search')){if(initial){initial=false;return pending.promise;}throw Error('offline');}}});
  h.document.getElementById('cancelSearch').click();pending.resolve(response({items:[item()],has_more:false}));await flush();
  assert.equal(h.document.querySelectorAll('.result-card').length,0);assert.match(h.document.getElementById('status').textContent,/취소/);
  assert.equal(h.calls.find(call=>call.target.pathname.endsWith('/search')).options.signal.aborted,true);
  h.submit();await flush();assert.equal(h.document.getElementById('status').classList.contains('error'),true);assert.doesNotMatch(h.document.getElementById('status').textContent,/조건에 맞는 문제가 없/);
});

test('auth changes clear photos and stale detail requests without copying or writing tokens',async t=>{
  const pending=deferred();
  const h=await harness(t,{token:'fixture-admin-token',statusData:{questions:1,user:{role:'admin'},ocr_available:true},route:url=>url.pathname.includes('/questions/')?pending.promise:undefined});
  h.document.querySelector('.result-card').click();await flush();
  const input=h.document.getElementById('photo');Object.defineProperty(input,'files',{value:[new h.w.File(['fixture'],'q.png',{type:'image/png'})],configurable:true});input.dispatchEvent(new h.w.Event('change'));
  h.w.localStorage.removeItem('hlCmTok');h.w.dispatchEvent(new h.w.StorageEvent('storage',{key:'hlCmTok',newValue:null}));await flush();
  pending.resolve(response({question:{id:Q1,source:{title:'Old private detail'},selected_version:{language:'ko',text:'Stale account text'}}}));await flush();
  assert.doesNotMatch(h.document.getElementById('detail').textContent,/Old private|Stale account/);
  assert.equal(h.document.getElementById('photoPreview').hidden,true);assert.ok(h.revoked.length>0);assert.equal(h.w.localStorage.length,0);
  assert.equal(h.calls.filter(call=>call.target.pathname.endsWith('/search')).at(-1).options.headers.Authorization,undefined);
});

test('read-only statements escape HTML and only verified fixed-origin figure paths load',async t=>{
  const h=await harness(t,{route:url=>{
    if(url.pathname.includes('/questions/'))return response({question:{id:Q1,source:{title:'Synthetic source'},selected_version:{language:'ko',text:'<script>bad()</script> $F=ma$'},review_status:'pending',figures:[{figure_review_status:'source_verified',url:'https://evil.example/image.png'},{figure_review_status:'pending',url:'/api/problem-bank/figures/'+FIGURE},{figure_review_status:'source_verified',url:'/api/problem-bank/figures/'+FIGURE,figure_label:'Fixture figure'}]}});
    if(url.pathname.includes('/figures/'))return{ok:true,status:200,headers:{get:()=>null},blob:async()=>new Blob(['fixture'],{type:'image/png'})};
  }});
  h.document.querySelector('.result-card').click();await flush();
  assert.equal(h.document.querySelector('#detail script'),null);assert.match(h.document.querySelector('.statement').textContent,/<script>bad/);
  assert.equal(h.calls.filter(call=>call.target.pathname.includes('/figures/')).length,1);assert.equal(h.document.querySelectorAll('#detail img').length,1);
  assert.ok(h.calls.every(call=>call.target.origin===API));
  assert.equal(h.calls.some(call=>/solutions|feedback|recommendations|assets|import/.test(call.target.pathname)),false);
});

test('embed messages require the same-origin parent; settings clamp viewport and never accept tokens',async t=>{
  const h=await harness(t,{token:'fixture-shared-token',embedded:true});
  h.send({type:'hl-problem-search-settings',lang:'en',theme:'dark',token:'injected'},{origin:'https://evil.example'});await flush();assert.equal(h.document.documentElement.lang,'ko');
  h.send({type:'hl-problem-search-settings',lang:'en',theme:'dark',token:'injected'},{source:h.w});await flush();assert.equal(h.document.documentElement.lang,'ko');
  h.send({type:'hl-problem-search-settings',lang:'en',theme:'dark',viewportHeight:99999,token:'injected'});await flush();
  assert.equal(h.document.documentElement.lang,'en');assert.equal(h.document.documentElement.dataset.theme,'dark');assert.equal(h.document.documentElement.style.getPropertyValue('--search-viewport-height'),'3000px');
  assert.equal(h.w.localStorage.getItem('hlCmTok'),'fixture-shared-token');
  assert.ok(h.calls.every(call=>call.options.headers.Authorization==='Bearer fixture-shared-token'));
  const before=h.calls.length;h.send({type:'hl-problem-search-reload'});await flush();assert.ok(h.calls.length>before);
  await new Promise(resolve=>setTimeout(resolve,25));assert.ok(h.posts.some(post=>post.data.type==='hl-problem-search-height'&&post.origin==='https://haslalab.org'));
});
