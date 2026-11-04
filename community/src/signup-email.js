// Password sign-up completes only for an address its owner can read: one IP made six throwaway password accounts in an
// hour (2026-11), each taking the free grading tokens. POST /api/signup/email-code mails a 6-digit code; only its digest
// is kept, for 10 minutes and 5 tries, and POST /api/signup spends it. Social sign-up is left alone: the provider account
// stands in for the address there. Accounts made before this keep working without an address.
import {accountMailAvailable,cleanRecoveryEmail,ensureAccountSecuritySchema,deliverSignupCode} from './account-security.js';
import {disposableEmail} from './reserved-names.js';
export const CODE_SEC=600,CODE_TRIES=5;
export const SIGNUP_CODE_SCHEMA=[
  `CREATE TABLE IF NOT EXISTS signup_email_codes (
    email TEXT PRIMARY KEY COLLATE NOCASE,
    code_hash TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
  )`,
  'CREATE INDEX IF NOT EXISTS signup_email_codes_expiry ON signup_email_codes(expires_at)',
];
const ready=new WeakMap();
// one statement at a time (the index needs its table when it is prepared); `scope` is the raw binding, as in consent.js
export function ensureSignupCodeSchema(db,scope=db){
  if(!ready.has(scope))ready.set(scope,(async()=>{for(const sql of SIGNUP_CODE_SCHEMA)await db.prepare(sql).run()})().catch(error=>{ready.delete(scope);throw error}));
  return ready.get(scope);
}
/* the digest binds the code to its address, so a row cannot be spent for another one. Six digits are no secret against
   a stolen table; what guards them is the 10-minute life and the 5 tries. */
export async function signupCodeHash(email,code){
  const bytes=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode('signup-code\n'+email+'\n'+code)));
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}
// 4294000000 is a multiple of 10^6: drawing below it keeps every code equally likely
function newCode(){const a=new Uint32Array(1);do crypto.getRandomValues(a);while(a[0]>=4294000000);return String(a[0]%1e6).padStart(6,'0')}
const same=(a,b)=>{if(typeof a!=='string'||typeof b!=='string'||a.length!==b.length)return false;let d=0;for(let i=0;i<a.length;i++)d|=a.charCodeAt(i)^b.charCodeAt(i);return d===0};
/* the sign-up route's guard on its INSERTs, bound as (email, code_hash, now): the row must still be there when the
   batch runs, so two sign-ups racing on one code make one account */
export const CODE_HELD='EXISTS(SELECT 1 FROM signup_email_codes WHERE email=? AND code_hash=? AND expires_at>?)';
export function createSignupEmail({HttpError,now,limit,sha256,clientIp,scope}){
  const error=(status,code)=>{throw new HttpError(status,code)};
  async function taken(env,email){await ensureAccountSecuritySchema(env.DB);return !!await env.DB.prepare('SELECT 1 FROM account_emails WHERE email=?').bind(email).first()}
  async function sendCode(req,env,body){
    body=body&&typeof body==='object'&&!Array.isArray(body)?body:{};
    // the IP limit comes first: it also bounds probing which addresses are on an account
    await limit(env,'signup-code-ip:'+clientIp(req),20,3600);
    const email=cleanRecoveryEmail(body.email);if(!email)error(400,'bad_email');
    if(disposableEmail(email,env))error(400,'email_disposable');     // a throwaway mailbox is not one readable mailbox per account
    if(!accountMailAvailable(env))error(503,'mail_unavailable');
    await ensureSignupCodeSchema(env.DB,scope(env));
    if(await taken(env,email))error(409,'email_taken');
    // the key is the address's digest: rate-limit rows are not where addresses should be kept
    await limit(env,'signup-code:'+await sha256(email),5,3600);await limit(env,'signup-code-total',200,3600);
    const t=now(),code=newCode(),hash=await signupCodeHash(email,code);
    // a new code replaces the last one and its tries; expired rows of other addresses go with the same write
    await env.DB.batch([
      env.DB.prepare('DELETE FROM signup_email_codes WHERE expires_at<=?').bind(t),
      env.DB.prepare(`INSERT INTO signup_email_codes(email,code_hash,expires_at,attempts,created_at) VALUES(?,?,?,0,?)
        ON CONFLICT(email) DO UPDATE SET code_hash=excluded.code_hash,expires_at=excluded.expires_at,attempts=0,created_at=excluded.created_at`).bind(email,hash,t+CODE_SEC,t),
    ]);
    try{await deliverSignupCode(env,{to:email,code,lang:body.lang,minutes:CODE_SEC/60,key:hash})}
    catch{
      // neither the address nor the provider's message is logged
      console.error('signup_code_delivery_failed');
      await env.DB.prepare('DELETE FROM signup_email_codes WHERE email=? AND code_hash=?').bind(email,hash).run();error(503,'mail_unavailable');
    }
    return {ok:true};
  }
  /* body.email and body.code of a sign-up, after its other fields passed. Returns what the INSERTs bind to CODE_HELD.
     The try is counted before the comparison, so parallel guesses cannot share one; the row goes with the account. */
  async function checkCode(env,body){
    const email=cleanRecoveryEmail(body.email);if(!email)error(400,'bad_email');
    const code=typeof body.code==='string'||typeof body.code==='number'?String(body.code).replace(/\s+/g,''):'';
    if(!code)error(400,'code_required');if(!/^\d{6}$/.test(code))error(400,'code_invalid');
    await ensureSignupCodeSchema(env.DB,scope(env));
    if(await taken(env,email))error(409,'email_taken');
    const t=now(),hash=await signupCodeHash(email,code);
    const row=await env.DB.prepare('UPDATE signup_email_codes SET attempts=attempts+1 WHERE email=? AND attempts<? AND expires_at>? RETURNING code_hash,attempts').bind(email,CODE_TRIES,t).first();
    if(!row){
      const old=await env.DB.prepare('SELECT expires_at FROM signup_email_codes WHERE email=?').bind(email).first();
      if(!old)error(400,'code_invalid');                 // never sent, already spent, or purged
      error(400,old.expires_at<=t?'code_expired':'code_attempts');
    }
    if(!same(row.code_hash,hash))error(400,row.attempts>=CODE_TRIES?'code_attempts':'code_invalid');
    return {email,hash,t};
  }
  return {sendCode,checkCode};
}
