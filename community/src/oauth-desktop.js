// System-browser OAuth handoff. Only a short-lived, proof-bound code reaches loopback.
const schema=`CREATE TABLE IF NOT EXISTS oauth_desktop_intents (
 intent_hash TEXT PRIMARY KEY, provider TEXT NOT NULL, challenge TEXT NOT NULL,
 callback_url TEXT NOT NULL, client_state TEXT NOT NULL, link_user INTEGER,
 created_at INTEGER NOT NULL, started_at INTEGER, code_hash TEXT UNIQUE,
 user_id INTEGER, fresh INTEGER NOT NULL DEFAULT 0, used_at INTEGER
)`;
const ready=new WeakMap();
async function ensure(db){let pending=ready.get(db);if(!pending){pending=db.prepare(schema).run().catch(error=>{ready.delete(db);throw error});ready.set(db,pending)}await pending}
export function createDesktopOAuth({HttpError,now,limit,sha256,b64u,providers,newSession,pubUser}){
 const fail=code=>{throw new HttpError(400,code)};
 const callback=(row,params)=>{const url=new URL(row.callback_url),query=new URLSearchParams({state:row.client_state,...params});if(url.protocol==='https:')url.hash='/oauth?'+new URLSearchParams({...(params.code?{c:params.code}:{}),...(params.error?{e:params.error}:{}),state:row.client_state});else url.search=query.toString();return new Response(null,{status:302,headers:{Location:url.href,'Cache-Control':'no-store','Referrer-Policy':'no-referrer'}})};
 return {
  async readBody(req,env){
   const origins=(env.ALLOWED_ORIGINS||'').split(',').map(value=>value.trim());
   if(!origins.includes(req.headers.get('Origin'))||!/^application\/json(?:\s*;|$)/i.test(req.headers.get('Content-Type')||''))throw new HttpError(403,'request_origin');
   const reader=req.body?.getReader(),chunks=[];let length=0;if(reader){for(;;){const part=await reader.read();if(part.done)break;length+=part.value.byteLength;if(length>8192){await reader.cancel();throw new HttpError(413,'request_too_large')}chunks.push(part.value)}}
   const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length}let data;try{data=JSON.parse(new TextDecoder().decode(bytes))}catch{fail('bad_desktop_request')}if(!data||typeof data!=='object'||Array.isArray(data))fail('bad_desktop_request');return data;
  },
  async handle(req,env,url,body){
   if(req.method!=='POST'||!/^\/api\/oauth\/(desktop|web)\/(start|exchange)$/.test(url.pathname))return null;
   const webFlow=url.pathname.includes('/web/');
   await ensure(env.DB);await limit(env,'oauth-desktop:'+ (req.headers.get('CF-Connecting-IP')||'unknown'),40,600);
   if(url.pathname.endsWith('/start')){
    const provider=String(body.provider||''),challenge=String(body.code_challenge||''),state=String(body.state||'');let redirect;
    try{redirect=new URL(body.redirect_uri)}catch{fail('bad_desktop_request')}
    if(!providers(env).includes(provider))fail('oauth_off');
    const trustedWeb=webFlow&&redirect.protocol==='https:'&&(env.ALLOWED_ORIGINS||'').split(',').map(value=>value.trim()).includes(redirect.origin)&&redirect.pathname==='/'&&!redirect.port;
    const trustedDesktop=!webFlow&&redirect.protocol==='http:'&&redirect.hostname==='127.0.0.1'&&redirect.port&&+redirect.port>=1024&&redirect.pathname==='/oauth/callback';
    if(!/^[A-Za-z0-9_-]{43}$/.test(challenge)||!/^[A-Za-z0-9_-]{43,128}$/.test(state)||!(trustedWeb||trustedDesktop)||redirect.search||redirect.hash||redirect.username||redirect.password)fail('bad_desktop_request');
    let linkUser=null;
    if(body.ticket){const hash=await sha256('t:'+String(body.ticket)),ticket=await env.DB.prepare('DELETE FROM oauth_codes WHERE code_hash=? AND fresh=-1 RETURNING user_id,created_at').bind(hash).first();if(!ticket||ticket.created_at<now()-120)fail('bad_code');linkUser=ticket.user_id}
    const intent=b64u(crypto.getRandomValues(new Uint8Array(32)));
    await env.DB.prepare('DELETE FROM oauth_desktop_intents WHERE created_at<?').bind(now()-600).run();
    await env.DB.prepare('INSERT INTO oauth_desktop_intents(intent_hash,provider,challenge,callback_url,client_state,link_user,created_at) VALUES(?,?,?,?,?,?,?)').bind(await sha256(intent),provider,challenge,redirect.href,state,linkUser,now()).run();
    const authorize=new URL('/api/oauth/'+provider+'/start',url.origin);authorize.searchParams.set('desktop',intent);
    return {authorize_url:authorize.href,expires_in:300};
   }
   const code=String(body.code||''),verifier=String(body.code_verifier||''),state=String(body.state||'');
   if(!/^[A-Za-z0-9_-]{32,128}$/.test(code)||!/^[A-Za-z0-9._~-]{43,128}$/.test(verifier)||!/^[A-Za-z0-9_-]{43,128}$/.test(state))fail('bad_code');
   const hash=await sha256(code),row=await env.DB.prepare('SELECT * FROM oauth_desktop_intents WHERE code_hash=?').bind(hash).first();
   const challenge=b64u(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier)));
   if(!row||row.used_at||row.created_at<now()-300||row.client_state!==state||row.challenge!==challenge||(new URL(row.callback_url).protocol==='https:')!==webFlow)fail('bad_code');
   const claimed=await env.DB.prepare('UPDATE oauth_desktop_intents SET used_at=? WHERE code_hash=? AND used_at IS NULL RETURNING user_id').bind(now(),hash).first();if(!claimed)fail('bad_code');
   const user=await env.DB.prepare('SELECT id,username,nickname,role,created_at,avatar FROM users WHERE id=? AND deleted=0').bind(row.user_id).first();if(!user)fail('bad_code');
   return {token:await newSession(env,user.id),user:pubUser(user),fresh:!!row.fresh};
  },
  async start(env,intent,provider){
   await ensure(env.DB);if(!/^[A-Za-z0-9_-]{43}$/.test(intent))return null;
   const hash=await sha256(intent),row=await env.DB.prepare('SELECT * FROM oauth_desktop_intents WHERE intent_hash=? AND provider=?').bind(hash,provider).first();
   if(!row||row.created_at<now()-300||row.started_at)return null;
   const claimed=await env.DB.prepare('UPDATE oauth_desktop_intents SET started_at=? WHERE intent_hash=? AND started_at IS NULL RETURNING intent_hash').bind(now(),hash).first();
   return claimed?{returnTo:'desktop:'+intent,linkUser:row.link_user}:null;
  },
  async finish(env,ret,userId,fresh){
   await ensure(env.DB);const row=await env.DB.prepare('SELECT * FROM oauth_desktop_intents WHERE intent_hash=?').bind(await sha256(ret.slice(8))).first();
   if(!row||row.created_at<now()-300||row.code_hash)return new Response('This sign-in link expired.',{status:400});
   const code=b64u(crypto.getRandomValues(new Uint8Array(32)));
   const claimed=await env.DB.prepare('UPDATE oauth_desktop_intents SET code_hash=?,user_id=?,fresh=? WHERE intent_hash=? AND code_hash IS NULL RETURNING intent_hash').bind(await sha256(code),userId,fresh,row.intent_hash).first();if(!claimed)return new Response('This sign-in link expired.',{status:400});
   return callback(row,{code});
  },
  async error(env,ret,error){
   await ensure(env.DB);const row=await env.DB.prepare('SELECT * FROM oauth_desktop_intents WHERE intent_hash=?').bind(await sha256(ret.slice(8))).first();
   return row?callback(row,{error}):new Response('This sign-in link expired.',{status:400});
  }
 };
}
