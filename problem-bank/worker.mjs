import {problemBankRoute} from '../community/src/problem-bank.js';

const PRIVATE = {'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'};
const json=(data,status=200)=>Response.json(data,{status,headers:PRIVATE});
const bearer=req=>/^Bearer [A-Za-z0-9_-]{20,200}$/.test(req.headers.get('Authorization')||'');
const sessionToken=value=>typeof value==='string'&&/^[A-Za-z0-9_-]{20,200}$/.test(value);
class AuthError extends Error {constructor(code){super(code);this.code=code;}}
const publicUser=value=>value&&typeof value==='object'&&!Array.isArray(value)&&Number.isSafeInteger(value.id)&&value.id>0&&typeof value.role==='string'
  ?{id:value.id,role:value.role,username:typeof value.username==='string'?value.username.slice(0,100):'',nickname:typeof value.nickname==='string'?value.nickname.slice(0,100):''}:null;
const safeHeaders=req=>{
  const h=new Headers();
  for(const name of ['Authorization','Content-Type','CF-Connecting-IP']) if(req.headers.has(name))h.set(name,req.headers.get(name));
  return h;
};
async function limitedJson(response,max=2*1024*1024){
  const reader=response.body?.getReader();if(!reader)throw new Error('empty_response');
  const chunks=[];let size=0;
  try{
    for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>max){await reader.cancel();throw new Error('response_too_large');}chunks.push(value);}
  }finally{reader.releaseLock();}
  const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
}
async function community(env,path,request,{method=request.method,body}={}){
  if(!env.COMMUNITY?.fetch)throw new AuthError('auth_unavailable');
  // Workers supports manual/follow, but rejects the standard Fetch "error" mode
  // before dispatch. Manual also keeps credentials from following redirects.
  try{return await env.COMMUNITY.fetch(new Request('https://haslalab-community.haslalab.workers.dev'+path,{method,headers:safeHeaders(request),body,redirect:'manual',signal:AbortSignal.timeout(15000)}));}
  catch{throw new AuthError('auth_transport_failed');}
}
async function authJson(response){try{return await limitedJson(response,16384);}catch{throw new AuthError('auth_invalid_response');}}
async function currentUser(request,env){
  if(!bearer(request))return null;
  const response=await community(env,'/api/me',request,{method:'GET'});
  if(response.status===401||response.status===403)return null;
  if(!response.ok)throw new AuthError('auth_unavailable');
  const body=await authJson(response);return publicUser(body?.user);
}
async function auth(request,env,url){
  if(url.pathname==='/auth/status'&&request.method==='GET'){
    const response=await community(env,'/api/me',new Request(request.url,{headers:{'CF-Connecting-IP':request.headers.get('CF-Connecting-IP')||''}}),{method:'GET'});
    const data=await authJson(response);
    if(!response.ok||!data||!Object.hasOwn(data,'user'))throw new AuthError('auth_unavailable');
    return json({authentication:'available'});
  }
  if(url.pathname==='/auth/me'&&request.method==='GET')return json({user:await currentUser(request,env)});
  if(url.pathname==='/auth/logout'&&request.method==='POST'){
    if(!bearer(request))return json({error:'login_required'},401);
    const response=await community(env,'/api/logout',request,{method:'POST',body:'{}'});
    return json({ok:response.ok},response.ok?200:502);
  }
  if(url.pathname!=='/auth/login'||request.method!=='POST')return json({error:'not_found'},404);
  if(!/^application\/json(?:;|$)/i.test(request.headers.get('Content-Type')||''))return json({error:'json_required'},415);
  let body;
  try{body=await limitedJson(request,4096);}catch{return json({error:'invalid_login'},400);}
  if(!body||typeof body!=='object'||Array.isArray(body)||typeof body.username!=='string'||!body.username.trim()||body.username.length>100||typeof body.password!=='string'||!body.password||body.password.length>200)return json({error:'invalid_login'},400);
  const response=await community(env,'/api/login',request,{method:'POST',body:JSON.stringify({username:body.username,password:body.password})});
  if(!response.ok&&response.status!==401&&response.status!==403&&response.status!==429){await response.body?.cancel?.().catch(()=>{});throw new AuthError('auth_unavailable');}
  const data=await authJson(response);
  if(!response.ok)return json({error:response.status===429?'rate_limited':'bad_credentials'},response.status===429?429:401);
  const user=publicUser(data.user);
  if(!sessionToken(data.token)||!user)return json({error:'invalid_auth_response'},502);
  return json({token:data.token,user});
}
function ocrAdapter(env){
  if(env.BANK_OCR_ENABLED!=='1'||!env.COMMUNITY?.fetch)return undefined;
  return async(image,request)=>{
    const body=new FormData();body.set('image',image,image.name||'question.png');
    const headers=safeHeaders(request);headers.delete('Content-Type');
    const response=await env.COMMUNITY.fetch(new Request('https://haslalab-community.haslalab.workers.dev/api/ocr?mode=math',{method:'POST',headers,body,redirect:'manual',signal:AbortSignal.timeout(80000)}));
    if(!response.ok){const error=new Error('ocr_failed');error.status=response.status;throw error;}
    const data=await limitedJson(response);return {text:data.text,confidence:data.confidence};
  };
}
async function sourcePdf(request,env,id){
  const row=await env.BANK_REGISTRY.prepare('SELECT object_key,sha256,byte_length FROM bank_source_objects WHERE source_id=?').bind(id).first();
  if(!row||!/^sources\/[a-f0-9]{64}\.pdf$/.test(row.object_key)||row.object_key!=='sources/'+row.sha256+'.pdf')return json({error:'source_pdf_not_found'},404);
  if(!Number.isSafeInteger(row.byte_length)||row.byte_length<1||row.byte_length>2*1024*1024*1024)return json({error:'source_pdf_integrity_error'},503);
  const rawRange=request.headers.get('Range');let range=null;
  if(rawRange){
    const match=/^bytes=(\d*)-(\d*)$/.exec(rawRange.trim());let start,end;
    if(match&&(match[1]||match[2])){
      if(!match[1]){const suffix=Number(match[2]);if(Number.isSafeInteger(suffix)&&suffix>0){start=Math.max(0,row.byte_length-suffix);end=row.byte_length-1;}}
      else{start=Number(match[1]);end=match[2]?Number(match[2]):row.byte_length-1;}
    }
    if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start<0||start>=row.byte_length||end<start)return new Response(null,{status:416,headers:{...PRIVATE,'Content-Range':'bytes */'+row.byte_length}});
    end=Math.min(end,row.byte_length-1);range={offset:start,length:end-start+1};
  }
  const object=await env.LIBRARY.get(row.object_key,range?{range}:undefined);
  if(!object)return json({error:'source_pdf_not_found'},404);
  if(object.size!==row.byte_length||(object.customMetadata?.sha256&&object.customMetadata.sha256!==row.sha256)||
    (range&&(!object.range||object.range.offset!==range.offset||object.range.length!==range.length))||(!range&&object.range&&(object.range.offset!==0||object.range.length!==row.byte_length))){
    await object.body?.cancel?.().catch(()=>{});return json({error:'source_pdf_integrity_error'},503);
  }
  const headers=new Headers({...PRIVATE,'Content-Type':'application/pdf','Content-Disposition':'inline; filename="source.pdf"','Content-Security-Policy':"default-src 'none'; sandbox",'Accept-Ranges':'bytes','X-Source-SHA256':row.sha256});
  // Hash-addressed object bytes were verified during ingestion. Do not allow
  // stored HTTP metadata to override private caching or the safe filename.
  if(range){headers.set('Content-Range',`bytes ${range.offset}-${range.offset+range.length-1}/${object.size}`);headers.set('Content-Length',String(range.length));}
  else headers.set('Content-Length',String(object.size));
  return new Response(object.body,{status:range?206:200,headers});
}
async function figure(env,id){
  const row=await env.BANK_REGISTRY.prepare('SELECT object_key,mime_type,sha256,byte_length FROM bank_figure_variants WHERE id=? AND verified_givens_only=1').bind(id).first();
  if(!row)return json({error:'figure_not_found'},404);
  const ext=row.mime_type==='image/png'?'png':row.mime_type==='image/svg+xml'?'svg':null;
  if(!ext||!/^[a-f0-9]{64}$/.test(row.sha256)||row.object_key!==`figures/${row.sha256}.${ext}`||!Number.isSafeInteger(row.byte_length)||row.byte_length<1||row.byte_length>4*1024*1024)return json({error:'figure_integrity_error'},503);
  const object=await env.LIBRARY.get(row.object_key);
  if(!object)return json({error:'figure_not_found'},404);
  const partial=object.range&&(object.range.offset!==0||object.range.length!==row.byte_length);
  if(object.size!==row.byte_length||partial||(object.customMetadata?.sha256&&object.customMetadata.sha256!==row.sha256)){await object.body?.cancel?.().catch(()=>{});return json({error:'figure_integrity_error'},503);}
  const bytes=await object.arrayBuffer(),hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
  if(bytes.byteLength!==row.byte_length||hash!==row.sha256)return json({error:'figure_integrity_error'},503);
  return new Response(bytes,{headers:{...PRIVATE,'Content-Type':row.mime_type,'Content-Length':String(bytes.byteLength),'Content-Security-Policy':"default-src 'none'; sandbox",'X-Asset-SHA256':row.sha256}});
}
function decorate(response,request,env){
  const headers=new Headers(response.headers),origin=request.headers.get('Origin')||'';
  if((env.ALLOWED_ORIGINS||'').split(',').map(x=>x.trim()).includes(origin))headers.set('Access-Control-Allow-Origin',origin);
  headers.set('Access-Control-Allow-Headers','Authorization,Content-Type,Range');headers.set('Access-Control-Allow-Methods','GET,POST,OPTIONS');headers.set('Vary',[...new Set((headers.get('Vary')||'').split(',').map(x=>x.trim()).filter(Boolean).concat('Origin'))].join(', '));
  headers.set('Referrer-Policy','no-referrer');headers.set('X-Content-Type-Options','nosniff');
  if(!headers.has('Content-Security-Policy'))headers.set('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'");
  return new Response(response.body,{status:response.status,headers});
}
export const worker={async fetch(request,env){
  const url=new URL(request.url);let response;
  try{
    if(request.method==='OPTIONS')response=new Response(null,{status:204,headers:PRIVATE});
    else if(url.pathname==='/api/health'&&request.method==='GET')response=json({ok:true,service:'haslalab-problem-bank',access:'public'});
    else if(url.pathname.startsWith('/auth/'))response=await auth(request,env,url);
    else if(url.pathname.startsWith('/api/')){
      const pdf=url.pathname.match(/^\/api\/problem-bank\/sources\/(src_[a-f0-9]{64})\/pdf$/),fig=url.pathname.match(/^\/api\/problem-bank\/figures\/(f_[a-f0-9]{64})$/);
      const restricted=!!pdf||request.method==='POST'&&(/\/(?:feedback|difficulty-review)$/.test(url.pathname)||url.pathname==='/api/problem-bank/identify'&&!/^application\/json(?:;|$)/i.test(request.headers.get('Content-Type')||''));let user=null;
      // These projections are identical for every role. In particular a public
      // figure has already passed the registry's givens-only approval gate.
      // Authenticate personalized reads and private/raw assets on every request
      // so permission changes and logout still take effect immediately.
      const invariantRead=request.method==='GET'&&(!!fig||/^\/api\/problem-bank\/(?:sources|search)$/.test(url.pathname)||/^\/api\/problem-bank\/sources\/src_[a-f0-9]{64}\/contents$/.test(url.pathname));
      if(!invariantRead)try{user=await currentUser(request,env);}catch(error){if(restricted)throw error;}
      if(pdf&&request.method==='GET'&&user?.role!=='admin')response=json({error:user?'admin_required':'login_required'},user?403:401);
      else{
        response=pdf&&request.method==='GET'?await sourcePdf(request,env,pdf[1]):fig&&request.method==='GET'?await figure(env,fig[1]):await problemBankRoute(request,env,url,{user,ocr:ocrAdapter(env)});
        response??=json({error:'not_found'},404);
      }
    }else if(['GET','HEAD'].includes(request.method)&&env.ASSETS?.fetch)response=await env.ASSETS.fetch(request);
    else response=json({error:'not_found'},404);
  }catch(error){response=json({error:error instanceof AuthError?error.code:'service_unavailable'},503);}
  return decorate(response,request,env);
}};
export default worker;
