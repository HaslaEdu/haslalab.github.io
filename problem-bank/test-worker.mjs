import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash,webcrypto} from 'node:crypto';
import vm from 'node:vm';
import worker from './worker.mjs';

if(!globalThis.crypto)globalThis.crypto=webcrypto;
const TOKEN='a'.repeat(32),OTHER='b'.repeat(32),ADMIN={id:1,role:'admin',username:'admin',nickname:'Admin'},USER={id:2,role:'user',username:'member'};
const origin='https://library.test',sha=x=>createHash('sha256').update(x).digest('hex'),SID='src_'+sha('synthetic-source');
const PDF=Buffer.from('%PDF-1.4\nsynthetic private source\n%%EOF\n'),PNG=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aXioAAAAASUVORK5CYII=','base64');
function fixture({user=ADMIN,meStatus=200,loginUser=ADMIN,loginToken=TOKEN,ocrStatus=200,pdfRow,pdfObject={}}={}){
  const calls={community:[],db:[],r2:[],metadata:0};
  const row=pdfRow??{object_key:'sources/'+sha(PDF)+'.pdf',sha256:sha(PDF),byte_length:PDF.length};
  const env={ALLOWED_ORIGINS:origin,BANK_OCR_ENABLED:'1',COMMUNITY:{async fetch(req){
    calls.community.push(req);
    const url=new URL(req.url);
    if(url.pathname==='/api/me')return Response.json({user:{...user,tokenHash:'upstream-private-hash',api_key:'upstream-private-key'}},{status:meStatus});
    if(url.pathname==='/api/login')return Response.json({token:loginToken,user:{...loginUser,tokenHash:'upstream-private-hash'}});
    if(url.pathname==='/api/logout')return Response.json({ok:true});
    if(url.pathname==='/api/ocr')return Response.json(ocrStatus===200?{text:'A body moves with acceleration 2 m per second squared.',confidence:.92}:{error:'secret-upstream-detail'},{status:ocrStatus});
    throw Error('unexpected upstream path');
  }},ASSETS:{async fetch(){return new Response('<!doctype html><h1>Public login shell</h1>',{headers:{'Content-Type':'text/html','Cache-Control':'public, max-age=120','Vary':'Accept-Encoding'}});}},
  LIBRARY:{async get(key,options){calls.r2.push({key,options});const range=options?.range;const bytes=range?PDF.subarray(range.offset,range.offset+range.length):PDF;return {size:PDF.length,range,body:new Response(bytes).body,customMetadata:{sha256:sha(PDF)},writeHttpMetadata(h){calls.metadata++;h.set('Cache-Control','public');h.set('Content-Disposition','secret-original-path');},...pdfObject};}}};
  const db={prepare(sql){calls.db.push(sql);return {bind(){return {async first(){
    if(sql.includes('bank_source_objects'))return row;
    if(sql.includes('sources_registered'))return {sources_registered:2};
    if(sql.includes('sources_with_documents'))return {questions:3,language_bodies:6,sources_with_documents:2,unresolved_questions:1};
    throw Error('Unexpected query '+sql);
  },async all(){return {results:[]};}};}};}};
  env.BANK_REGISTRY=db;env.BANK2=db;env.BANK3=db;env.BANK_SEARCH=db;
  const call=(path,{method='GET',headers={},body,token=TOKEN}={})=>worker.fetch(new Request(origin+path,{method,headers:{...(token?{Authorization:'Bearer '+token}:{}),...headers},body}),env);
  return {env,calls,call,row};
}

test('private API and R2 source bytes deny anonymous/ordinary users before storage access',async()=>{
  const f=fixture();let res=await f.call('/api/problem-bank/sources/'+SID+'/pdf',{token:null});assert.equal(res.status,401);assert.equal(f.calls.community.length,0);assert.equal(f.calls.db.length,0);assert.equal(f.calls.r2.length,0);
  const normal=fixture({user:USER});res=await normal.call('/api/problem-bank/sources/'+SID+'/pdf');assert.equal(res.status,403);assert.equal(normal.calls.db.length,0);assert.equal(normal.calls.r2.length,0);
});
test('expired upstream auth becomes 401 and auth responses discard upstream private fields',async()=>{
  const f=fixture({meStatus:401});assert.equal((await f.call('/api/problem-bank/status')).status,401);
  const good=fixture(),res=await good.call('/auth/me');assert.equal(res.status,200);const body=await res.json();assert.equal(body.user.role,'admin');assert.doesNotMatch(JSON.stringify(body),/tokenHash|upstream-private|api_key/);
});
test('bounded login rejects arrays/null/oversized bodies without any authentication request',async()=>{
  for(const body of ['null','[]','{}',JSON.stringify({username:'x',password:''}),'x'.repeat(4097)]){
    const f=fixture(),res=await f.call('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body,token:null});assert.equal(res.status,400);assert.equal(f.calls.community.length,0);
  }
});
test('login proxies only credentials, sanitizes users and rejects malformed session tokens',async()=>{
  const f=fixture(),res=await f.call('/auth/login?redirect=https://evil.test',{method:'POST',headers:{'Content-Type':'application/json','Cookie':'private-cookie','X-Role':'admin','CF-Connecting-IP':'192.0.2.1'},body:JSON.stringify({username:'admin',password:'synthetic',role:'admin'}),token:null});
  assert.equal(res.status,200);const out=await res.json();assert.equal(out.token,TOKEN);assert.doesNotMatch(JSON.stringify(out),/tokenHash|upstream-private/);
  const forwarded=f.calls.community[0];assert.equal(forwarded.url,'https://haslalab-community.haslalab.workers.dev/api/login');assert.equal(forwarded.redirect,'manual');assert.equal(forwarded.headers.get('Cookie'),null);assert.equal(forwarded.headers.get('X-Role'),null);assert.equal(forwarded.headers.get('CF-Connecting-IP'),'192.0.2.1');assert.deepEqual(await forwarded.json(),{username:'admin',password:'synthetic'});
  const bad=fixture({loginToken:'invalid token'});assert.equal((await bad.call('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'admin',password:'synthetic'}),token:null})).status,502);
});
test('ordinary-account login immediately revokes the newly created upstream session',async()=>{
  const f=fixture({loginUser:USER,loginToken:OTHER}),res=await f.call('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'member',password:'synthetic'}),token:null});
  assert.equal(res.status,403);assert.deepEqual(f.calls.community.map(x=>new URL(x.url).pathname),['/api/login','/api/logout']);assert.equal(f.calls.community[1].headers.get('Authorization'),'Bearer '+OTHER);assert.doesNotMatch(await res.text(),new RegExp(OTHER));
});
test('auth readiness checks omit caller credentials and expose only sanitized failures',async()=>{
  const f=fixture(),res=await f.call('/auth/status');assert.equal(res.status,200);assert.deepEqual(await res.json(),{authentication:'available'});assert.equal(f.calls.community[0].headers.get('Authorization'),null);assert.equal(f.calls.db.length,0);
  for(const [fetch,code] of [[async()=>{throw Error('SECRET TRANSPORT');},'auth_transport_failed'],[async()=>new Response('SECRET invalid JSON'),'auth_invalid_response']]){
    const bad=fixture();bad.env.COMMUNITY.fetch=fetch;const response=await bad.call('/auth/status');assert.equal(response.status,503);assert.deepEqual(await response.json(),{error:code});
  }
});
test('upstream login server failures remain service errors instead of credential errors',async()=>{
  for(const status of [500,503]){
    const f=fixture();f.env.COMMUNITY.fetch=async()=>new Response('PRIVATE upstream failure',{status,headers:{'Content-Type':'text/html'}});
    const res=await f.call('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'admin',password:'synthetic'}),token:null});
    assert.equal(res.status,503);assert.deepEqual(await res.json(),{error:'auth_unavailable'});
  }
});
test('static HTML receives CSP/no-referrer and CORS never reflects untrusted origins',async()=>{
  const f=fixture(),res=await f.call('/',{token:null,headers:{Origin:'https://evil.test'}});
  assert.equal(res.status,200);assert.match(res.headers.get('Content-Security-Policy'),/script-src 'self'/);assert.match(res.headers.get('Content-Security-Policy'),/frame-ancestors 'none'/);assert.equal(res.headers.get('Referrer-Policy'),'no-referrer');assert.equal(res.headers.get('Access-Control-Allow-Origin'),null);assert.match(res.headers.get('Vary'),/Accept-Encoding/);assert.match(res.headers.get('Vary'),/Origin/);
  const allowed=await f.call('/api/health',{token:null,headers:{Origin:origin}});assert.equal(allowed.headers.get('Access-Control-Allow-Origin'),origin);
  assert.match(readFileSync(new URL('./wrangler.toml',import.meta.url),'utf8'),/^run_worker_first\s*=\s*true\s*$/m);
});
test('R2 PDF reads require the exact hash-addressed key and preserve private headers',async()=>{
  const f=fixture(),res=await f.call('/api/problem-bank/sources/'+SID+'/pdf');
  assert.equal(res.status,200);assert.deepEqual(Buffer.from(await res.arrayBuffer()),PDF);assert.equal(f.calls.r2[0].key,'sources/'+sha(PDF)+'.pdf');assert.equal(f.calls.metadata,0);assert.equal(res.headers.get('Cache-Control'),'private, no-store');assert.equal(res.headers.get('Content-Disposition'),'inline; filename="source.pdf"');assert.equal(res.headers.get('X-Source-SHA256'),sha(PDF));assert.match(res.headers.get('Content-Security-Policy'),/sandbox/);
  const bad=fixture({pdfRow:{object_key:'../../private.pdf',sha256:sha(PDF),byte_length:PDF.length}});assert.equal((await bad.call('/api/problem-bank/sources/'+SID+'/pdf')).status,404);assert.equal(bad.calls.r2.length,0);
});
test('PDF ranges are single, bounded and verified against actual R2 object metadata',async()=>{
  const f=fixture(),res=await f.call('/api/problem-bank/sources/'+SID+'/pdf',{headers:{Range:'bytes=2-9'}});assert.equal(res.status,206);assert.equal(res.headers.get('Content-Range'),`bytes 2-9/${PDF.length}`);assert.deepEqual(Buffer.from(await res.arrayBuffer()),PDF.subarray(2,10));assert.deepEqual(f.calls.r2[0].options,{range:{offset:2,length:8}});
  const suffix=fixture(),last=await suffix.call('/api/problem-bank/sources/'+SID+'/pdf',{headers:{Range:'bytes=-5'}});assert.equal(last.status,206);assert.deepEqual(Buffer.from(await last.arrayBuffer()),PDF.subarray(-5));
  for(const range of ['bytes=1-2,4-5','bytes=9999-','bytes=-0','bytes=8-2','bytes=999999999999999999999-']){
    const bad=fixture(),out=await bad.call('/api/problem-bank/sources/'+SID+'/pdf',{headers:{Range:range}});assert.equal(out.status,416,range);assert.equal(bad.calls.r2.length,0);assert.equal(out.headers.get('Content-Range'),'bytes */'+PDF.length);
  }
  const mismatch=fixture({pdfObject:{size:PDF.length+1}});assert.equal((await mismatch.call('/api/problem-bank/sources/'+SID+'/pdf')).status,503);
  const hashMismatch=fixture({pdfObject:{customMetadata:{sha256:sha('wrong')}}});assert.equal((await hashMismatch.call('/api/problem-bank/sources/'+SID+'/pdf')).status,503);
});
test('OCR uses only the authenticated existing service with a reconstructed bounded file form',async()=>{
  const f=fixture(),form=new FormData();form.set('image',new Blob([PNG],{type:'image/png'}),'question.png');form.set('lang','en');
  const res=await f.call('/api/problem-bank/identify',{method:'POST',body:form});assert.equal(res.status,200);const out=await res.json();assert.equal(out.ocr_used,true);assert.ok(out.recognized_text.length>5);assert.equal(out.identification_status,'candidates_only');
  assert.deepEqual(f.calls.community.map(x=>new URL(x.url).pathname),['/api/me','/api/ocr']);const req=f.calls.community[1];assert.equal(new URL(req.url).search,'?mode=math');assert.equal(req.redirect,'manual');assert.equal(req.headers.get('Authorization'),'Bearer '+TOKEN);const sent=await req.formData();assert.deepEqual([...sent.keys()],['image']);assert.equal(sent.get('image').type,'image/png');
});
test('OCR disabled, non-admin calls and invalid input cannot reach a paid adapter',async()=>{
  for(const user of [USER]){const f=fixture({user}),form=new FormData();form.set('image',new Blob([PNG],{type:'image/png'}),'scan.png');assert.equal((await f.call('/api/problem-bank/identify',{method:'POST',body:form})).status,403);assert.equal(f.calls.community.length,1);}
  const disabled=fixture();disabled.env.BANK_OCR_ENABLED='0';const form=new FormData();form.set('image',new Blob([PNG],{type:'image/png'}),'scan.png');assert.equal((await disabled.call('/api/problem-bank/identify',{method:'POST',body:form})).status,503);assert.equal(disabled.calls.community.length,1);
  const limited=fixture({ocrStatus:429}),photo=new FormData();photo.set('image',new Blob([PNG],{type:'image/png'}),'scan.png');const res=await limited.call('/api/problem-bank/identify',{method:'POST',body:photo});assert.equal(res.status,429);assert.doesNotMatch(await res.text(),/secret-upstream/);
});

function browserFixture(){
  const nodes=new Map(),pending=[],revoked=[],calls=[];
  class Element {
    constructor(id=''){this.id=id;this.hidden=false;this.disabled=false;this.value='';this.dataset={};this.isConnected=true;this.listeners={};this.style={};this.children=[];this.classList={toggle(){},add(){},remove(){}};this._html='';this._text='';}
    set innerHTML(x){this._html=String(x);this._text='';}get innerHTML(){return this._html;}
    set textContent(x){this._text=String(x);this._html='';}get textContent(){return this._text;}
    addEventListener(type,fn){this.listeners[type]=fn;}setAttribute(){}querySelector(){return this.button??=new Element();}querySelectorAll(){return [];}reset(){this.value='';}append(x){this.children.push(x);}click(){}
  }
  const node=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
  const storage=()=>{const values=new Map();return {getItem(key){return values.get(key)??null;},setItem(key,value){values.set(key,String(value));},removeItem(key){values.delete(key);}};};
  const sessionStore=storage();
  class BrowserFormData extends FormData {constructor(form){super();for(const [key,value] of Object.entries(form?.fields||{}))this.set(key,value);}}
  class BrowserURL extends URL {static createObjectURL(){return 'blob:synthetic';}static revokeObjectURL(x){revoked.push(x);}}
  const sandbox={console,URL:BrowserURL,URLSearchParams,AbortController,DOMException,FormData:BrowserFormData,Blob,Set,Map,Number,String,Object,Promise,localStorage:storage(),sessionStorage:sessionStore,matchMedia:()=>({matches:false}),window:{location:new URL(origin+'/'),renderMathInElement:null},document:{documentElement:{dataset:{}},getElementById:node,querySelectorAll:()=>[],createElement:()=>new Element()},fetch:(path,opts)=>new Promise((resolve,reject)=>{const request={path,opts,resolve,reject};pending.push(request);calls.push(request);})};
  vm.createContext(sandbox);const source=readFileSync(new URL('./public/app.js',import.meta.url),'utf8');vm.runInContext(source+'\nglobalThis.exposed={state,api,signOut,restoreSession,showLibrary,search,identify,selectQuestion,showSolutions,showRecommendations,prose};',sandbox);
  sandbox.exposed.state.token=TOKEN;sandbox.exposed.state.user={...ADMIN};
  sessionStore.setItem('hlBankToken',TOKEN);node('bootstrapStatus').hidden=true;
  return {...sandbox.exposed,node,pending,revoked,calls,sessionStore};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const metadata={questions:7,language_bodies:14,ocr_available:false};
async function finishBootstrap(b,sources=[{id:SID,title:'Current source'}]){
  const requests=b.pending.splice(0);
  assert.equal(requests.length,2);
  for(const request of requests)request.resolve(Response.json(request.path.endsWith('/status')?metadata:{sources}));
  await tick();const search=b.pending.shift();assert.match(search.path,/\/search\?/);search.resolve(Response.json({items:[],has_more:false}));
}

test('successful login exposes bootstrap failures with a retry that never resubmits credentials',async()=>{
  const b=browserFixture();b.state.token='';b.state.user=null;b.sessionStore.removeItem('hlBankToken');
  const form=b.node('loginForm');form.fields={username:'admin',password:'synthetic'};
  const login=form.listeners.submit({preventDefault(){},currentTarget:form});
  assert.equal(b.pending[0].path,'/auth/login');b.pending.shift().resolve(Response.json({token:OTHER,user:ADMIN}));await tick();
  for(const request of b.pending.splice(0))request.resolve(request.path.endsWith('/status')?Response.json({error:'service_unavailable'},{status:503}):Response.json({sources:[]}));
  await login;
  assert.equal(b.state.token,OTHER);assert.equal(b.sessionStore.getItem('hlBankToken'),OTHER);
  assert.equal(b.node('library').hidden,false);assert.equal(b.node('loginPanel').hidden,true);
  assert.equal(b.node('bootstrapStatus').hidden,false);assert.ok(b.node('bootstrapMessage').textContent.length>0);
  assert.equal(b.node('loginMessage').textContent,'');assert.equal(b.node('retryBootstrap').disabled,false);
  const retry=b.node('retryBootstrap').listeners.click();await finishBootstrap(b);await retry;
  assert.equal(b.node('bootstrapStatus').hidden,true);assert.equal(b.state.sources[0].title,'Current source');
  assert.equal(b.calls.filter(r=>r.path==='/auth/login').length,1);assert.equal(b.calls.filter(r=>r.path==='/auth/me').length,0);
});

test('restoring a session survives a transient auth outage and visibly retries with the same saved session',async()=>{
  const b=browserFixture();b.state.user=null;b.node('library').hidden=true;b.node('loginPanel').hidden=false;
  const restore=b.restoreSession();b.pending.shift().resolve(Response.json({error:'auth_unavailable'},{status:503}));await restore;
  assert.equal(b.state.token,TOKEN);assert.equal(b.sessionStore.getItem('hlBankToken'),TOKEN);assert.equal(b.state.user,null);
  assert.equal(b.node('bootstrapStatus').hidden,false);assert.equal(b.node('retryBootstrap').disabled,false);
  const retry=b.node('retryBootstrap').listeners.click();assert.equal(b.pending[0].path,'/auth/me');
  b.pending.shift().resolve(Response.json({user:ADMIN}));await tick();await finishBootstrap(b);await retry;
  assert.equal(b.state.token,TOKEN);assert.equal(b.state.user.role,'admin');assert.equal(b.node('library').hidden,false);assert.equal(b.node('bootstrapStatus').hidden,true);
});

test('transient metadata failure during session restore keeps the authenticated session and shows a visible retry',async()=>{
  const b=browserFixture();b.state.user=null;
  const restore=b.restoreSession();b.pending.shift().resolve(Response.json({user:ADMIN}));await tick();
  for(const request of b.pending.splice(0))request.resolve(Response.json({error:'service_unavailable'},{status:503}));
  await restore;assert.equal(b.state.token,TOKEN);assert.equal(b.state.user.role,'admin');assert.equal(b.sessionStore.getItem('hlBankToken'),TOKEN);
  assert.equal(b.node('library').hidden,false);assert.equal(b.node('bootstrapStatus').hidden,false);assert.equal(b.node('retryBootstrap').disabled,false);
});

test('confirmed expired and non-admin sessions are cleared rather than offered a bootstrap retry',async()=>{
  for(const response of [Response.json({error:'login_required'},{status:401}),Response.json({error:'admin_required'},{status:403}),Response.json({user:USER}),Response.json({user:null})]){
    const b=browserFixture(),restore=b.restoreSession();b.pending.shift().resolve(response);await restore;
    assert.equal(b.state.token,'');assert.equal(b.state.user,null);assert.equal(b.sessionStore.getItem('hlBankToken'),null);
    assert.equal(b.node('loginPanel').hidden,false);assert.equal(b.node('library').hidden,true);assert.equal(b.node('bootstrapStatus').hidden,true);
  }
});

test('logout during library bootstrap rejects late private metadata and leaves no retry or source data',async()=>{
  const b=browserFixture(),load=b.showLibrary(),requests=b.pending.splice(0);b.signOut(false);
  for(const request of requests)request.resolve(Response.json(request.path.endsWith('/status')?metadata:{sources:[{id:SID,title:'LATE PRIVATE SOURCE'}]}));
  await load;assert.equal(b.state.sources.length,0);assert.equal(b.node('counts').textContent,'');assert.equal(b.node('library').hidden,true);
  assert.equal(b.node('bootstrapStatus').hidden,true);assert.equal(b.node('bootstrapMessage').textContent,'');assert.equal(b.pending.length,0);
});

test('newest bootstrap wins and old-session auth errors cannot overwrite a newly signed-in user',async()=>{
  const b=browserFixture(),old=b.showLibrary(),first=b.pending.splice(0),latest=b.showLibrary();
  await finishBootstrap(b,[{id:SID,title:'NEW SOURCE'}]);await latest;
  for(const request of first)request.resolve(Response.json(request.path.endsWith('/status')?{...metadata,questions:999}:{sources:[{id:SID,title:'OLD SOURCE'}]}));
  await old;assert.equal(b.state.sources[0].title,'NEW SOURCE');assert.match(b.node('counts').textContent,/7/);assert.doesNotMatch(b.node('counts').textContent,/999/);
  const restore=b.restoreSession(),late=b.pending.shift();b.signOut(false);b.state.token=OTHER;b.state.user={...ADMIN};b.sessionStore.setItem('hlBankToken',OTHER);
  late.resolve(Response.json({error:'login_required'},{status:401}));await restore;
  assert.equal(b.state.token,OTHER);assert.equal(b.sessionStore.getItem('hlBankToken'),OTHER);assert.equal(b.node('bootstrapStatus').hidden,true);
});
const detail=(id,text)=>({question:{id,original_number:'1',source_id:SID,source:{title:'Synthetic source'},subjects:[],context:{},selected_version:{text},assets:[]}});
test('frontend logout clears actual private DOM/state and rejects delayed search/OCR completions',async()=>{
  const b=browserFixture();b.node('detail').innerHTML='PRIVATE STATEMENT';b.node('recognized').value='PRIVATE OCR';b.state.sources=[{id:SID,title:'PRIVATE SOURCE'}];b.state.question='qid';b.state.urls=['blob:private'];
  const search=b.search(true);const old=b.pending.shift();assert.ok(old.opts.signal);
  b.signOut(false);assert.equal(b.node('detail').innerHTML,'');assert.equal(b.node('recognized').value,'');assert.equal(b.state.sources.length,0);assert.equal(b.state.question,null);assert.equal(b.state.token,'');assert.equal(old.opts.signal.aborted,true);assert.deepEqual(b.revoked,['blob:private']);
  old.resolve(Response.json({items:[{id:'old',source_title:'PRIVATE LATE',original_number:'1',snippet:'PRIVATE LATE'}],has_more:false}));await search;assert.equal(b.node('results').innerHTML,'');assert.equal(b.node('library').hidden,true);
  const o=browserFixture(),identify=o.identify('private scanned statement');const late=o.pending.shift();o.signOut(false);late.resolve(Response.json({recognized_text:'LATE PRIVATE OCR',items:[],candidates:[]}));await identify;assert.equal(o.node('recognized').value,'');assert.equal(o.node('recognizedPanel').hidden,true);assert.equal(o.node('photoForm').querySelector('button').disabled,false);
});
test('old-session 401 cannot clear a newly signed-in session',async()=>{
  const b=browserFixture(),request=b.api('/api/problem-bank/status');const old=b.pending.shift();b.signOut(false);b.state.token=OTHER;b.state.user={...ADMIN};old.resolve(Response.json({error:'login_required'},{status:401}));await assert.rejects(request,e=>e.name==='AbortError');assert.equal(b.state.token,OTHER);assert.ok(b.state.user);
});
test('newest detail wins even for the same question across language changes',async()=>{
  const b=browserFixture(),one=b.selectQuestion('same');const first=b.pending.shift();b.state.lang='en';const two=b.selectQuestion('same');const second=b.pending.shift();second.resolve(Response.json(detail('same','NEW ENGLISH')));await two;first.resolve(Response.json(detail('same','OLD KOREAN')));await one;assert.match(b.node('detail').innerHTML,/NEW ENGLISH/);assert.doesNotMatch(b.node('detail').innerHTML,/OLD KOREAN/);
});
test('last related action wins and stale solutions cannot overwrite recommendations',async()=>{
  const b=browserFixture();b.state.question='same';const sol=b.showSolutions('same'),first=b.pending.shift(),rec=b.showRecommendations('same'),second=b.pending.shift();second.resolve(Response.json({items:[{id:'next',source_title:'RECOMMENDATION',original_number:'2',snippet:'safe'}]}));await rec;first.resolve(Response.json({solutions:[{authorship:'source_transcription',kind:'worked_solution',selected_version:{text:'STALE SOLUTION'},assets:[]}]}));await sol;assert.match(b.node('related').innerHTML,/RECOMMENDATION/);assert.doesNotMatch(b.node('related').innerHTML,/STALE SOLUTION/);
});
test('frontend never sends a bearer token to an external asset URL and escapes statement HTML',async()=>{
  const b=browserFixture();await assert.rejects(b.api('https://evil.test/private'),/invalid_api_path/);assert.equal(b.pending.length,0);
  const rendered=b.prose('<img src=x onerror=alert(1)>\n\n# <script>steal()</script>\n\n| a | b |\n| --- | --- |\n| <svg/onload=steal()> | $x<y$ |');assert.doesNotMatch(rendered,/<img|<script|<svg/);assert.match(rendered,/&lt;img/);assert.match(rendered,/&lt;script/);assert.match(rendered,/x&lt;y/);
});
