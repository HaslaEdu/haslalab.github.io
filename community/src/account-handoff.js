// Short-lived proof-bound transfer between isolated Edu application sessions.
// Session credentials never travel in a URL or get copied between web views.
// HaslaEdu's own addresses: haslaedu.kr (the main one from the domain move) and physleague.kr (kept for older clients).
const origins=new Set(['https://haslaedu.kr','https://www.haslaedu.kr','https://physleague.kr','https://www.physleague.kr','https://haslaedu.haslalab.workers.dev']);
const proof=value=>typeof value==='string'&&/^[A-Za-z0-9_-]{43}$/.test(value);
const ready=new WeakMap();
export const HANDOFF_SCHEMA=`CREATE TABLE IF NOT EXISTS account_session_handoffs (
 code_hash TEXT PRIMARY KEY, source_session_hash TEXT NOT NULL REFERENCES sessions(token_hash) ON DELETE CASCADE,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 source_origin TEXT NOT NULL, target_origin TEXT NOT NULL, challenge TEXT NOT NULL, state TEXT NOT NULL,
 created_at INTEGER NOT NULL, used_at INTEGER, used_session_hash TEXT
)`;
async function ensure(db,scope=db){if(!ready.has(scope))ready.set(scope,db.prepare(HANDOFF_SCHEMA).run().catch(error=>{ready.delete(scope);throw error}));return ready.get(scope)}
export function createAccountHandoff({HttpError,now,limit,sha256,b64u,needUser,pubUser,readUser}){
 const fail=(code='invalid_or_expired_handoff',status=400)=>{throw new HttpError(status,code)};
 const random=()=>b64u(crypto.getRandomValues(new Uint8Array(32)));
 const activeSource=`EXISTS(SELECT 1 FROM sessions s JOIN users u ON u.id=s.user_id
  WHERE s.token_hash=h.source_session_hash AND s.user_id=h.user_id AND s.expires_at>? AND u.deleted=0)`;
 return {
  async readBody(request,env){
   const allowed=(env.ALLOWED_ORIGINS||'').split(',').map(value=>value.trim());
   if(!allowed.includes(request.headers.get('Origin'))||!/^application\/json(?:\s*;|$)/i.test(request.headers.get('Content-Type')||''))fail('request_origin',403);
   const reader=request.body?.getReader(),chunks=[];let size=0;
   if(reader)for(;;){const part=await reader.read();if(part.done)break;size+=part.value.byteLength;if(size>8192){await reader.cancel();fail('request_too_large',413)}chunks.push(part.value)}
   const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength}let body;try{body=JSON.parse(new TextDecoder().decode(bytes))}catch{fail('invalid_request')}
   if(!body||typeof body!=='object'||Array.isArray(body))fail('invalid_request');return body;
  },
  async handle(request,env,{path,body,me,scope=env.DB}){
   if(request.method!=='POST'||!['/api/auth/handoff/start','/api/auth/handoff/exchange'].includes(path))return null;
   const t=now();
   if(path.endsWith('/start')){
    needUser(me);
    if(!origins.has(body.source_origin)||!origins.has(body.target_origin)||!proof(body.code_challenge)||!proof(body.state)||!proof(me.tokenHash))fail('invalid_request');
    await limit(env,'handoff-start:'+me.id,30,600);await ensure(env.DB,scope);
    const code=random(),createdAt=now();await env.DB.prepare('DELETE FROM account_session_handoffs WHERE created_at<?').bind(createdAt-600).run();
    const inserted=await env.DB.prepare(`INSERT INTO account_session_handoffs(code_hash,source_session_hash,user_id,source_origin,target_origin,challenge,state,created_at)
     SELECT ?,s.token_hash,s.user_id,?,?,?,?,? FROM sessions s JOIN users u ON u.id=s.user_id
     WHERE s.token_hash=? AND s.user_id=? AND s.expires_at>? AND u.deleted=0`)
     .bind(await sha256(code),body.source_origin,body.target_origin,body.code_challenge,body.state,createdAt,me.tokenHash,me.id,createdAt).run();
    if(!inserted.meta?.changes)fail('login_required',401);return {code,expires_in:60};
   }
   if(!origins.has(body.target_origin)||!proof(body.code)||!proof(body.code_verifier)||!proof(body.state))fail();
   await limit(env,'handoff-exchange:'+(request.headers.get('CF-Connecting-IP')||'unknown'),120,600);await ensure(env.DB,scope);
   const hash=await sha256(body.code),row=await env.DB.prepare(`SELECT h.*,s.created_at AS source_created_at,s.expires_at AS source_expires_at
    FROM account_session_handoffs h JOIN sessions s ON s.token_hash=h.source_session_hash JOIN users u ON u.id=s.user_id
    WHERE h.code_hash=? AND h.user_id=s.user_id AND h.used_at IS NULL AND h.created_at>? AND s.expires_at>? AND u.deleted=0`).bind(hash,t-60,t).first();
   const challenge=b64u(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(body.code_verifier)));
   if(!row||row.target_origin!==body.target_origin||row.state!==body.state||row.challenge!==challenge||!Number.isSafeInteger(row.source_created_at)||!Number.isSafeInteger(row.source_expires_at))fail();
   if(me&&me.id!==row.user_id)fail('account_mismatch',409);
   const user=await readUser(env,row.user_id);if(!user)fail();needUser(user);
   const token=random(),tokenHash=await sha256(token),consumedAt=now();
   const consume=env.DB.prepare(`UPDATE account_session_handoffs AS h SET used_at=?,used_session_hash=?
    WHERE h.code_hash=? AND h.used_at IS NULL AND h.created_at>? AND ${activeSource}`).bind(consumedAt,tokenHash,hash,consumedAt-60,consumedAt);
   if(me){const changed=await consume.run();if(!changed.meta?.changes)fail();return {ok:true,user:pubUser(user),already_signed_in:true};}
   const result=await env.DB.batch([
    consume,
    env.DB.prepare(`INSERT INTO sessions(token_hash,user_id,created_at,expires_at)
     SELECT ?,s.user_id,s.created_at,s.expires_at FROM account_session_handoffs h
     JOIN sessions s ON s.token_hash=h.source_session_hash JOIN users u ON u.id=s.user_id
     WHERE h.code_hash=? AND h.used_session_hash=? AND h.used_at=? AND s.user_id=h.user_id AND s.expires_at>? AND u.deleted=0`)
     .bind(tokenHash,hash,tokenHash,consumedAt,consumedAt),
   ]);
   if(!result[0]?.meta?.changes||!result[1]?.meta?.changes)fail();
   return {token,user:pubUser(user)};
  }
 };
}
