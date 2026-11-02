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
function fixture({user=ADMIN,meStatus=200,loginUser=ADMIN,loginToken=TOKEN,ocrStatus=200,pdfRow,pdfObject={},figureRow=null,figureObject={},figureBytes=PNG,figureMissing=false}={}){
  const calls={community:[],db:[],bindings:[],r2:[],metadata:0,figureReads:0,figureCancels:0};
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
  LIBRARY:{async get(key,options){calls.r2.push({key,options});
    if(key.startsWith('figures/'))return figureMissing?null:{size:figureBytes.length,body:{async cancel(){calls.figureCancels++;}},customMetadata:{sha256:sha(figureBytes)},async arrayBuffer(){calls.figureReads++;return Uint8Array.from(figureBytes).buffer;},writeHttpMetadata(h){calls.metadata++;h.set('Content-Type','text/html');h.set('Content-Disposition','secret-source-path');},...figureObject};
    const range=options?.range;const bytes=range?PDF.subarray(range.offset,range.offset+range.length):PDF;return {size:PDF.length,range,body:new Response(bytes).body,customMetadata:{sha256:sha(PDF)},writeHttpMetadata(h){calls.metadata++;h.set('Cache-Control','public');h.set('Content-Disposition','secret-original-path');},...pdfObject};}}};
  const db={prepare(sql){calls.db.push(sql);return {bind(...args){calls.bindings.push({sql,args});return {async first(){
    if(sql.includes('bank_figure_variants')){
      if(figureRow?.id&&figureRow.id!==args[0])return null;
      if(sql.includes('verified_givens_only=1')&&figureRow?.verified_givens_only===0)return null;
      return figureRow;
    }
    if(sql.includes('bank_source_objects'))return row;
    if(sql.includes('sources_registered'))return {sources_registered:2};
    if(sql.includes('sources_with_documents'))return {questions:3,language_bodies:6,sources_with_documents:2,unresolved_questions:1};
    if(sql.includes('sqlite_master'))return null;
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
test('public status tolerates expired auth and auth responses discard upstream private fields',async()=>{
  const f=fixture({meStatus:401}),status=await f.call('/api/problem-bank/status');assert.equal(status.status,200);const publicStatus=await status.json();assert.equal(publicStatus.user,null);assert.equal(publicStatus.access,'public');assert.equal(publicStatus.ocr_available,false);
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
test('ordinary-account login preserves the member session for public learning and feedback',async()=>{
  const f=fixture({loginUser:USER,loginToken:OTHER}),res=await f.call('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'member',password:'synthetic'}),token:null});
  assert.equal(res.status,200);assert.deepEqual(f.calls.community.map(x=>new URL(x.url).pathname),['/api/login']);const data=await res.json();assert.equal(data.token,OTHER);assert.equal(data.user.role,'user');assert.doesNotMatch(JSON.stringify(data),/upstream-private|tokenHash/);
});
test('guest reads survive auth transport failures while guest writes and photo OCR stay gated',async()=>{
  const f=fixture();f.env.COMMUNITY.fetch=async()=>{throw Error('PRIVATE TRANSPORT FAILURE');};
  const res=await f.call('/api/problem-bank/status');assert.equal(res.status,200);const data=await res.json();assert.equal(data.user,null);assert.equal(data.ocr_available,false);assert.doesNotMatch(JSON.stringify(data),/PRIVATE/);
  const guest=fixture(),form=new FormData();form.set('image',new Blob([PNG],{type:'image/png'}),'photo.png');
  assert.equal((await guest.call('/api/problem-bank/identify',{method:'POST',body:form,token:null})).status,401);assert.equal(guest.calls.community.length,0);
  const feedback=await guest.call('/api/problem-bank/questions/q_'+'a'.repeat(64)+'/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({stars:3,outcome:'not_attempted',minutes:null}),token:null});assert.equal(feedback.status,401);assert.equal(guest.calls.db.length,0);
  const typed=await guest.call('/api/problem-bank/identify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:'A freely moving body has constant velocity.'}),token:null});assert.equal(typed.status,200);assert.equal((await typed.json()).ocr_used,false);assert.equal(guest.calls.community.length,0);
  const typedDuringAuthFailure=await f.call('/api/problem-bank/identify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:'A freely moving body has constant velocity.'})});assert.equal(typedDuringAuthFailure.status,200);assert.equal((await typedDuringAuthFailure.json()).ocr_used,false);
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
  const full=fixture({pdfObject:{range:{offset:0,length:PDF.length}}}),whole=await full.call('/api/problem-bank/sources/'+SID+'/pdf');assert.equal(whole.status,200);assert.deepEqual(Buffer.from(await whole.arrayBuffer()),PDF);
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

const FID='f_'+sha('synthetic-approved-figure');
const figureRecord=(bytes=PNG,mime_type='image/png')=>({id:FID,verified_givens_only:1,object_key:`figures/${sha(bytes)}.${mime_type==='image/png'?'png':'svg'}`,sha256:sha(bytes),mime_type,byte_length:bytes.length});

test('guest figure reads use only the exact approved registry ID and hash-addressed PNG or SVG object',async()=>{
  const SVG=Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M1 1L9 9"/></svg>');
  for(const [bytes,mime] of [[PNG,'image/png'],[SVG,'image/svg+xml']]){
    const row=figureRecord(bytes,mime),f=fixture({figureRow:row,figureBytes:bytes}),res=await f.call('/api/problem-bank/figures/'+FID,{token:null});
    assert.equal(res.status,200);assert.deepEqual(Buffer.from(await res.arrayBuffer()),bytes);assert.equal(f.calls.community.length,0);
    assert.equal(f.calls.bindings.length,1);assert.deepEqual(f.calls.bindings[0].args,[FID]);assert.match(f.calls.bindings[0].sql,/WHERE id=\? AND verified_givens_only=1/);
    assert.deepEqual(f.calls.r2,[{key:row.object_key,options:undefined}]);assert.equal(f.calls.figureReads,1);assert.equal(f.calls.metadata,0);
    assert.equal(res.headers.get('Content-Type'),mime);assert.equal(res.headers.get('Content-Length'),String(bytes.length));assert.equal(res.headers.get('X-Asset-SHA256'),sha(bytes));
    assert.equal(res.headers.get('Cache-Control'),'private, no-store');assert.equal(res.headers.get('X-Content-Type-Options'),'nosniff');assert.match(res.headers.get('Content-Security-Policy'),/sandbox/);assert.equal(res.headers.get('Content-Disposition'),null);
  }
  const noMetadata=fixture({figureRow:figureRecord(),figureObject:{customMetadata:{}}});assert.equal((await noMetadata.call('/api/problem-bank/figures/'+FID,{token:null})).status,200);assert.equal(noMetadata.calls.figureReads,1);
  const fullRange=fixture({figureRow:figureRecord(),figureObject:{range:{offset:0,length:PNG.length}}}),complete=await fullRange.call('/api/problem-bank/figures/'+FID,{token:null});assert.equal(complete.status,200);assert.deepEqual(Buffer.from(await complete.arrayBuffer()),PNG);assert.equal(fullRange.calls.figureReads,1);
});

test('unknown or unapproved figure IDs never reach R2 or authenticate the guest',async()=>{
  for(const config of [{},{figureRow:{...figureRecord(),verified_givens_only:0}},{figureRow:{...figureRecord(),id:'f_'+'b'.repeat(64)}}]){
    const f=fixture(config),res=await f.call('/api/problem-bank/figures/'+FID,{token:null});assert.equal(res.status,404);assert.deepEqual(await res.json(),{error:'figure_not_found'});assert.equal(f.calls.r2.length,0);assert.equal(f.calls.figureReads,0);assert.equal(f.calls.community.length,0);
  }
  for(const suffix of ['f_bad','f_'+'A'.repeat(64),'f_'+'a'.repeat(65)]){
    const f=fixture({figureRow:figureRecord()}),res=await f.call('/api/problem-bank/figures/'+suffix,{token:null});assert.notEqual(res.status,200);assert.equal(f.calls.r2.length,0);assert.equal(f.calls.figureReads,0);
  }
});

test('figure registry key, type, hash and length mismatches are rejected before reading storage',async()=>{
  for(const change of [
    {object_key:'../../private.pdf'},{object_key:'sources/'+sha(PNG)+'.pdf'},{object_key:'figures/'+sha('other')+'.png'},
    {object_key:'figures/'+sha(PNG)+'.svg'},{mime_type:'image/jpeg'},{mime_type:'text/html'},{sha256:'not-a-sha'},
    {byte_length:0},{byte_length:-1},{byte_length:1.5},{byte_length:4*1024*1024+1},{byte_length:'70'}
  ]){
    const f=fixture({figureRow:{...figureRecord(),...change}}),res=await f.call('/api/problem-bank/figures/'+FID,{token:null});
    assert.equal(res.status,503,JSON.stringify(change));assert.deepEqual(await res.json(),{error:'figure_integrity_error'});assert.equal(f.calls.r2.length,0);assert.equal(f.calls.figureReads,0);
  }
});

test('figure R2 missing objects and metadata mismatches cannot return or read the stored body',async()=>{
  const missing=fixture({figureRow:figureRecord(),figureMissing:true}),absent=await missing.call('/api/problem-bank/figures/'+FID,{token:null});assert.equal(absent.status,404);assert.equal(missing.calls.figureReads,0);
  for(const figureObject of [{size:PNG.length+1},{size:4*1024*1024+1},{range:{offset:0,length:1}},{customMetadata:{sha256:sha('PRIVATE different bytes')}}]){
    const f=fixture({figureRow:figureRecord(),figureObject}),res=await f.call('/api/problem-bank/figures/'+FID,{token:null});
    assert.equal(res.status,503);assert.deepEqual(await res.json(),{error:'figure_integrity_error'});assert.equal(f.calls.figureReads,0);assert.equal(f.calls.figureCancels,1);assert.equal(f.calls.metadata,0);
  }
});

test('figure route verifies actual full bytes even when R2 size and metadata claim the approved hash',async()=>{
  for(const bytes of [Buffer.from('PRIVATE wrong bytes'),Buffer.concat([PNG,Buffer.from('PRIVATE trailing bytes')])]){
    const f=fixture({figureRow:figureRecord(),figureBytes:bytes,figureObject:{size:PNG.length,customMetadata:{sha256:sha(PNG)}}}),res=await f.call('/api/problem-bank/figures/'+FID,{token:null});
    assert.equal(res.status,503);assert.deepEqual(await res.json(),{error:'figure_integrity_error'});assert.equal(f.calls.figureReads,1);assert.equal(f.calls.metadata,0);
  }
  const changed=Buffer.from(PNG);changed[changed.length-1]^=1;
  const f=fixture({figureRow:figureRecord(),figureBytes:changed,figureObject:{customMetadata:{sha256:sha(PNG)}}}),res=await f.call('/api/problem-bank/figures/'+FID,{token:null});assert.equal(res.status,503);assert.equal(f.calls.figureReads,1);assert.deepEqual(await res.json(),{error:'figure_integrity_error'});
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

function browserFixture({embedded=false,initialize=true,boot=false,token=TOKEN,user=ADMIN,parentOrigin='https://haslalab.org',pageOrigin='https://haslalab.org'}={}){
  const nodes=new Map(),pending=[],revoked=[],created=[],calls=[],events={},messages=[];
  class Element {
    constructor(id=''){this.id=id;this.hidden=false;this.disabled=false;this.value='';this.dataset={};this.isConnected=true;this.listeners={};this.style={};this.children=[];this.selectors=new Map();this.classList={toggle(){},add(){},remove(){}};this._html='';this._text='';}
    set innerHTML(x){this._html=String(x);this._text='';this.children=[];}get innerHTML(){return this._html;}
    set textContent(x){this._text=String(x);this._html='';this.children=[];}get textContent(){return this._text;}
    addEventListener(type,fn){this.listeners[type]=fn;}setAttribute(){}querySelector(selector){if(!this.selectors.has(selector))this.selectors.set(selector,new Element());return this.selectors.get(selector);}querySelectorAll(){return [];}reset(){this.value='';}append(x){this.children.push(x);}click(){}getBoundingClientRect(){return {height:800};}
  }
  const node=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
  const storage=()=>{const values=new Map();return {getItem(key){return values.get(key)??null;},setItem(key,value){values.set(key,String(value));},removeItem(key){values.delete(key);}};};
  const sessionStore=storage(),localStore=storage();if(embedded&&token)localStore.setItem('hlCmTok',token);if(!embedded&&boot&&token)sessionStore.setItem('hlBankToken',token);
  class BrowserFormData extends FormData {constructor(form){super();for(const [key,value] of Object.entries(form?.fields||{}))this.set(key,value);}}
  class BrowserURL extends URL {static createObjectURL(){const id='blob:synthetic-'+created.length;created.push(id);return id;}static revokeObjectURL(x){revoked.push(x);}}
  const parent={location:{origin:parentOrigin},postMessage:(data,target)=>messages.push({data,target})};
  const sandbox={console,URL:BrowserURL,URLSearchParams,AbortController,DOMException,FormData:BrowserFormData,Blob,Set,Map,Number,String,Object,Promise,localStorage:localStore,sessionStorage:sessionStore,matchMedia:()=>({matches:false}),window:{location:new URL(embedded?pageOrigin+'/problem-bank/public/index.html?embed=1&lang=ko&theme=light':origin+'/'),renderMathInElement:null,parent:embedded?parent:null,addEventListener:(name,fn)=>{events[name]=fn;}},document:{documentElement:{dataset:{}},body:node('body'),getElementById:node,querySelector:()=>node('main'),querySelectorAll:()=>[],createElement:()=>new Element()},fetch:(path,opts)=>new Promise((resolve,reject)=>{const request={path,opts,resolve,reject};pending.push(request);calls.push(request);})};
  vm.createContext(sandbox);let source=readFileSync(new URL('./public/app.js',import.meta.url),'utf8');if(!boot)source=source.replace(/restoreSession\(\);\s*$/,'');
  vm.runInContext(source+'\nglobalThis.exposed={state,api,signOut,restoreSession,showLibrary,search,changePage,params,identify,selectQuestion,showSolutions,showRecommendations,showContexts,figureGroups,difficultyBadge,feedbackPanel,loadFeedback,saveFeedback,prose};',sandbox);
  if(initialize){sandbox.exposed.state.token=token;sandbox.exposed.state.user=user;if(token&&!embedded)sessionStore.setItem('hlBankToken',token);node('bootstrapStatus').hidden=true;}
  return {...sandbox.exposed,node,pending,revoked,created,calls,sessionStore,localStore,events,parent,messages};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const metadata={access:'public',questions:7,language_bodies:14,ocr_available:false,user:null};
async function finishBootstrap(b,{user=null,ocr=false,sources=[{id:SID,title:'Current source'}]}={}){
  const requests=b.pending.splice(0);assert.equal(requests.length,2);
  for(const request of requests)request.resolve(Response.json(request.path.endsWith('/status')?{...metadata,user,ocr_available:ocr}:{sources}));
  await tick();const search=b.pending.shift();assert.match(search.path,/\/search\?/);search.resolve(Response.json({items:[],has_more:false,next_cursor:null}));await tick();
}
const detail=(id,text,extra={})=>({question:{id,original_number:'1',source_id:SID,source:{title:'Synthetic source'},subjects:[],context:{},selected_version:{text},assets:[],...extra}});
const imageResponse=()=>new Response(PNG,{headers:{'Content-Type':'image/png'}});

test('frontend guest startup browses immediately without a login or auth round trip',async()=>{
  const b=browserFixture({initialize:false,boot:true,token:'',user:null});
  assert.deepEqual(b.pending.map(x=>x.path),['/api/problem-bank/status','/api/problem-bank/sources']);
  await finishBootstrap(b);assert.equal(b.node('library').hidden,false);assert.equal(b.node('loginPanel').hidden,true);
  assert.equal(b.node('photoMode').disabled,true);assert.equal(b.node('photoAccess').hidden,false);
  assert(!b.calls.some(x=>x.path.includes('/auth/')));assert(b.calls.every(x=>!x.opts.headers.Authorization));
});

test('frontend native embedding preserves member sessions and uses only the fixed bank origin',async()=>{
  const b=browserFixture({embedded:true,initialize:false,boot:true});await finishBootstrap(b,{user:USER});
  assert.equal(b.state.user.role,'user');assert.equal(b.state.token,TOKEN);assert.equal(b.localStore.getItem('hlCmTok'),TOKEN);assert.equal(b.sessionStore.getItem('hlBankToken'),null);
  assert.equal(b.node('library').hidden,false);assert.equal(b.node('photoMode').disabled,true);
  assert(b.calls.every(c=>c.path.startsWith('https://haslalab-problem-bank.haslalab.workers.dev/api/problem-bank/')));
  assert(!b.calls.some(c=>c.path.includes('/auth/login')));await assert.rejects(b.api('https://evil.test/api/problem-bank/search'),/invalid_api_path/);
  assert.deepEqual(JSON.parse(JSON.stringify(b.messages)),[{data:{type:'hl-bank-height',height:824},target:'https://haslalab.org'}]);
});

test('frontend parent logout clears private data, ignores stale responses and resumes public browsing',async()=>{
  const b=browserFixture({embedded:true,initialize:false,boot:true}),old=b.pending.splice(0);b.node('detail').innerHTML='PRIVATE SOURCE';
  b.localStore.removeItem('hlCmTok');b.events.storage({key:'hlCmTok'});assert.equal(b.node('detail').innerHTML,'');assert.equal(b.state.token,'');
  for(const request of old)request.resolve(Response.json(request.path.endsWith('/status')?{...metadata,user:ADMIN}:{sources:[{id:SID,title:'OLD PRIVATE SOURCE'}]}));
  await tick();await finishBootstrap(b);assert.equal(b.state.user,null);assert.equal(b.state.sources[0].title,'Current source');assert.equal(b.node('library').hidden,false);
});

test('frontend embed settings require the real same-origin parent and never accept credentials or roles',async()=>{
  const foreign=browserFixture({embedded:true,initialize:false,parentOrigin:'https://evil.test'});assert.equal(foreign.state.token,'');assert.equal(foreign.messages.length,0);
  const b=browserFixture({embedded:true,initialize:false});
  for(const event of [{origin:'https://evil.test',source:b.parent},{origin:'https://haslalab.org',source:{}}])b.events.message({...event,data:{type:'hl-bank-settings',theme:'dark',lang:'en',token:OTHER}});
  assert.equal(b.state.theme,'light');assert.equal(b.state.lang,'ko');
  b.events.message({origin:'https://haslalab.org',source:b.parent,data:{type:'hl-bank-settings',theme:'dark',token:OTHER,role:'admin'}});
  assert.equal(b.state.theme,'dark');assert.equal(b.state.token,TOKEN);assert.equal(b.state.user,null);assert.equal(b.pending.length,0);
});

test('frontend transient metadata errors keep the saved session and expose a retry without resending credentials',async()=>{
  const b=browserFixture({user:USER}),load=b.restoreSession();
  for(const request of b.pending.splice(0))request.resolve(Response.json({error:'service_unavailable'},{status:503}));await load;
  assert.equal(b.state.token,TOKEN);assert.equal(b.sessionStore.getItem('hlBankToken'),TOKEN);assert.equal(b.state.user.role,'user');assert.equal(b.node('bootstrapStatus').hidden,false);
  const retry=b.node('retryBootstrap').listeners.click();await finishBootstrap(b,{user:USER});await retry;
  assert.equal(b.node('bootstrapStatus').hidden,true);assert(!b.calls.some(c=>c.path.includes('/auth/')));
});

test('frontend administrators alone can activate photo OCR and member 403 does not erase a valid session',async()=>{
  const member=browserFixture({user:USER});member.node('photoMode').listeners.click();assert.equal(member.state.mode,'text');
  await member.identify(null,new Blob([PNG],{type:'image/png'}));assert.equal(member.calls.length,0);
  const denied=member.api('/api/problem-bank/identify',{method:'POST',body:{text:'synthetic'}});member.pending.shift().resolve(Response.json({error:'admin_required'},{status:403}));await assert.rejects(denied);
  assert.equal(member.state.token,TOKEN);assert.equal(member.state.user.role,'user');
  const admin=browserFixture(),load=admin.showLibrary();await finishBootstrap(admin,{user:ADMIN,ocr:true});await load;
  assert.equal(admin.node('photoMode').disabled,false);assert.equal(admin.node('photoAccess').hidden,true);
});

test('frontend cursor browsing passes the canonical last ID, supports back and resets on filters',async()=>{
  const b=browserFixture({token:'',user:null}),one='q_'+'1'.repeat(64),two='q_'+'2'.repeat(64);
  let request=b.search(true);let pending=b.pending.shift();assert.equal(new URL(pending.path,origin).searchParams.has('offset'),false);
  pending.resolve(Response.json({items:[{id:one,source_title:'Source',original_number:'1',snippet:'first'}],has_more:true,next_cursor:one}));await request;
  request=b.changePage(1);pending=b.pending.shift();assert.equal(new URL(pending.path,origin).searchParams.get('cursor'),one);
  pending.resolve(Response.json({items:[{id:two,source_title:'Source',original_number:'2',snippet:'second'}],has_more:false,next_cursor:null}));await request;assert.equal(b.node('previous').disabled,false);
  request=b.changePage(-1);pending=b.pending.shift();assert.equal(new URL(pending.path,origin).searchParams.has('cursor'),false);pending.resolve(Response.json({items:[],has_more:false,next_cursor:null}));await request;
  b.node('collection').value='astronomy';b.node('stars').value='4';b.node('subject').value='general_relativity';request=b.node('collection').listeners.change();pending=b.pending.shift();
  const query=new URL(pending.path,origin).searchParams;assert.equal(query.get('collection'),'astronomy');assert.equal(query.get('stars'),'4');assert.equal(query.get('subject'),'general_relativity');assert.equal(query.has('cursor'),false);
  pending.resolve(Response.json({items:[],has_more:false,next_cursor:null}));await request;assert.equal(b.state.cursorHistory.length,0);
});

test('frontend text search retains bounded offsets and visibly marks limited results',async()=>{
  const b=browserFixture({token:'',user:null});b.node('query').value='oscillator';b.state.offset=300;
  const search=b.search(),request=b.pending.shift();assert.equal(new URL(request.path,origin).searchParams.get('offset'),'300');
  request.resolve(Response.json({items:[{id:'q',source_title:'Source',original_number:'1',snippet:'test'}],has_more:true,limited_results:true}));await search;
  assert.equal(b.node('next').disabled,true);assert.ok(b.node('resultLimit').textContent.length>0);
  const badge=b.difficultyBadge({stars:4,difficulty:{status:'provisional',reason_codes:['calculus','<img onerror=steal()>']}});
  assert.match(badge,/★★★★☆/);assert.match(badge,/잠정/);assert.doesNotMatch(badge,/<img|onerror/);
});

test('frontend question selection inlines only givens, deduplicates variants and never fetches solutions or feedback',async()=>{
  const b=browserFixture({token:'',user:null}),load=b.selectQuestion('same');b.node('related').innerHTML='OLD SOLUTION';
  b.pending.shift().resolve(Response.json(detail('same','QUESTION ONLY',{figures:[{id:'variant',parent_asset_id:'original',url:'/api/problem-bank/figures/f_variant',mime_type:'image/png',spans:[]}],assets:[{id:'original',role:'figure',url:'/api/problem-bank/assets/original'},{id:'reference',role:'figure',placement:'reference',url:'/api/problem-bank/assets/reference'},{id:'raw',role:'question_crop',url:'/api/problem-bank/assets/raw'}]})));
  await load;assert.equal(b.pending.length,1);assert.equal(b.pending[0].path,'/api/problem-bank/figures/f_variant');
  assert.doesNotMatch(b.node('detail').innerHTML,/id="sourcePdf"|id="sourceFigures"/);assert.equal(b.node('related').textContent,'');
  assert(!b.calls.some(c=>/\/solutions|\/feedback|\/assets\/raw|\/assets\/original/.test(c.path)));
  b.pending.shift().resolve(imageResponse());await tick();assert.equal(b.node('questionFigures').children.length,1);
  b.node('referenceFigures').open=true;b.node('referenceFigures').listeners.toggle();assert.equal(b.pending[0].path,'/api/problem-bank/assets/reference');
  b.pending.shift().resolve(imageResponse());await tick();
  const solutions=b.node('showSolutions').listeners.click();assert.match(b.pending[0].path,/\/solutions\?/);b.pending.shift().resolve(Response.json({solutions:[]}));await solutions;
});

test('frontend theme inversion marks only explicitly verified monochrome figures and preserves source captions',async()=>{
  const b=browserFixture({token:'',user:null}),load=b.selectQuestion('same');
  const figures=[true,false,undefined,'true',1].map((flag,index)=>({id:'fig-'+index,monochrome:flag,figure_label:'Fig.1.'+index,url:'/api/problem-bank/figures/f_'+index,spans:[{page:13}]}));
  b.pending.shift().resolve(Response.json(detail('same','QUESTION',{figures})));await load;
  for(let i=0;i<figures.length;i++){assert.equal(b.pending.length,1);b.pending.shift().resolve(imageResponse());await tick();}
  const rendered=b.node('questionFigures').children;assert.equal(rendered.length,5);
  for(let i=0;i<rendered.length;i++){
    assert.equal(rendered[i].className.includes('figure-monochrome'),i===0);
    assert.equal(rendered[i].children[0].className==='source-monochrome',i===0);
    assert.equal(rendered[i].children[0].src,'blob:synthetic-'+i);
    assert.match(rendered[i].children[1].textContent,new RegExp('Fig\\.1\\.'+i));
  }
  const css=readFileSync(new URL('./public/styles.css',import.meta.url),'utf8');
  assert.match(css,/:root\[data-theme=dark\] \.figure img\.source-monochrome\{filter:invert\(1\);mix-blend-mode:screen\}/);
  assert.match(css,/:root\[data-theme=dark\] \.figure\.figure-monochrome\{background:var\(--panel\)/);
  assert.equal((css.match(/filter:invert\(/g)||[]).length,1);
});

test('frontend administrator raw captures remain collapsed and image completions cannot reappear after logout',async()=>{
  const b=browserFixture(),load=b.selectQuestion('same');
  b.pending.shift().resolve(Response.json(detail('same','QUESTION',{can_view_source:true,assets:[{id:'raw',role:'question_crop',url:'/api/problem-bank/assets/raw'},{id:'annotated',role:'figure',placement:'source_only',url:'/api/problem-bank/assets/annotated'}]})));await load;
  assert.equal(b.pending.length,0);assert.match(b.node('detail').innerHTML,/id="sourcePdf"/);
  b.node('sourceFigures').open=true;b.node('sourceFigures').listeners.toggle();const old=b.pending.shift();
  b.signOut(false,false);old.resolve(imageResponse());await tick();assert.equal(b.created.length,0);assert.equal(b.node('detail').innerHTML,'');assert.equal(b.state.user,null);
});

test('frontend native sign-in return links preserve the selected astronomy collection',async()=>{
  const b=browserFixture({embedded:true,initialize:false,token:''});b.node('collection').value='astronomy';
  b.node('siteLogin').listeners.click();assert.equal(b.sessionStore.getItem('hlCmBack'),'#/learn/astronomy/library');
  const load=b.selectQuestion('same');b.pending.shift().resolve(Response.json(detail('same','QUESTION')));await load;
  b.node('feedbackLogin').listeners.click();assert.equal(b.sessionStore.getItem('hlCmBack'),'#/learn/astronomy/library');
  assert(!b.calls.some(c=>c.path.includes('/feedback')||c.path.includes('/solutions')));
});

test('frontend feedback loads only when explicitly opened and guest writes require sign-in',async()=>{
  const b=browserFixture({token:'',user:null}),load=b.selectQuestion('same');b.pending.shift().resolve(Response.json(detail('same','QUESTION')));await load;
  assert.equal(b.pending.length,0);assert.match(b.node('detail').children.at(-1).innerHTML,/target="_top"/);assert.doesNotMatch(b.node('detail').children.at(-1).innerHTML,/id="feedbackForm"/);
  b.node('difficultyFeedback').open=true;const open=b.node('difficultyFeedback').listeners.toggle();assert.match(b.pending[0].path,/\/feedback$/);
  b.pending.shift().resolve(Response.json({count:2,mean_stars:3.5,own:null,evidence:'self_report'}));await open;assert.match(b.node('feedbackStats').textContent,/3\.5/);
  await b.saveFeedback('same',b.node('feedbackForm'));assert.equal(b.pending.length,0);assert.ok(b.node('feedbackMessage').textContent);
});

test('frontend member difficulty feedback uses bounded self-reported fields and refreshes its own rating',async()=>{
  const b=browserFixture({user:USER});b.state.question='same';const form=b.node('feedbackForm');form.fields={stars:'4',outcome:'partial',minutes:'25'};
  const save=b.saveFeedback('same',form);let request=b.pending.shift();assert.equal(request.opts.method,'POST');assert.deepEqual(JSON.parse(request.opts.body),{stars:4,outcome:'partial',minutes:25});
  request.resolve(Response.json({ok:true}));await tick();request=b.pending.shift();assert.equal(request.opts.method,'GET');request.resolve(Response.json({count:1,mean_stars:4,own:{stars:4,outcome:'partial',minutes:25},evidence:'self_report'}));await save;
  assert.equal(b.node('feedbackStars').value,'4');assert.equal(b.node('feedbackMinutes').value,25);assert.equal(form.querySelector('button').disabled,false);
  for(const fields of [{stars:'6',outcome:'solved',minutes:''},{stars:'2',outcome:'verified',minutes:'5'},{stars:'2',outcome:'solved',minutes:'1441'}]){form.fields=fields;await b.saveFeedback('same',form);assert.equal(b.pending.length,0);}
  assert(!b.calls.some(c=>c.path.includes('/solutions')));
});

test('frontend delayed searches and old-session errors cannot restore private data or clear a newer member',async()=>{
  const b=browserFixture(),search=b.search(true),old=b.pending.shift();b.node('detail').innerHTML='PRIVATE';b.signOut(false,false);
  old.resolve(Response.json({items:[{id:'old',source_title:'LATE PRIVATE',original_number:'1',snippet:'LATE'}],has_more:false}));await search;assert.equal(b.node('detail').innerHTML,'');assert.equal(b.node('results').innerHTML,'');
  b.state.token=TOKEN;b.state.user=ADMIN;const check=b.api('/api/problem-bank/status'),late=b.pending.shift();b.signOut(false,false);b.state.token=OTHER;b.state.user=USER;
  late.resolve(Response.json({error:'login_required'},{status:401}));await assert.rejects(check,e=>e.name==='AbortError');assert.equal(b.state.token,OTHER);assert.equal(b.state.user.role,'user');
});

test('frontend newest detail and related action win without accepting statement HTML',async()=>{
  const b=browserFixture(),one=b.selectQuestion('same'),first=b.pending.shift(),two=b.selectQuestion('same'),second=b.pending.shift();second.resolve(Response.json(detail('same','NEW')));await two;first.resolve(Response.json(detail('same','OLD')));await one;assert.match(b.node('detail').innerHTML,/NEW/);assert.doesNotMatch(b.node('detail').innerHTML,/>OLD</);
  const solutions=b.showSolutions('same'),s=b.pending.shift(),recommendations=b.showRecommendations('same'),rec=b.pending.shift();rec.resolve(Response.json({items:[{id:'next',source_title:'RECOMMENDATION',original_number:'2',snippet:'safe'}]}));await recommendations;s.resolve(Response.json({solutions:[{authorship:'source_transcription',kind:'worked_solution',selected_version:{text:'STALE SOLUTION'},assets:[]}]}));await solutions;assert.match(b.node('related').innerHTML,/RECOMMENDATION/);assert.doesNotMatch(b.node('related').innerHTML,/STALE SOLUTION/);
  const html=b.prose('<img src=x onerror=steal()>\n\n| a | b |\n| --- | --- |\n| <svg/onload=steal()> | $x<y$ |');assert.doesNotMatch(html,/<img|<svg/);assert.match(html,/&lt;img/);
});
