// Account recovery belongs to the account service, never the browser bundle.
// Only digests of short-lived links are stored. A recovery address is usable
// only after its owner has followed a verification link.
import {disposableEmail} from './reserved-names.js';
const readySchemas=new WeakMap();
export const ACCOUNT_SECURITY_SCHEMA=[
  `CREATE TABLE IF NOT EXISTS account_emails (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    verified_at INTEGER NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS account_email_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL CHECK(purpose IN ('verify','reset')),
    email TEXT NOT NULL,
    password_stamp TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    used_at INTEGER
  )`,
  'CREATE INDEX IF NOT EXISTS account_email_tokens_user ON account_email_tokens(user_id,purpose,created_at)',
  'CREATE INDEX IF NOT EXISTS account_email_tokens_expiry ON account_email_tokens(expires_at)',
];
export function ensureAccountSecuritySchema(db){
  /* one statement at a time: an index needs its table to exist when the statement is prepared (a batch prepares
     every statement first, so CREATE INDEX on a table created in the same batch failed under the test database) */
  if(!readySchemas.has(db))readySchemas.set(db,(async()=>{for(const sql of ACCOUNT_SECURITY_SCHEMA)await db.prepare(sql).run()})().catch(error=>{readySchemas.delete(db);throw error}));
  return readySchemas.get(db);
}
const ORIGINS=new Set(['https://haslalab.org','https://www.haslalab.org','https://haslaedu.kr','https://www.haslaedu.kr','https://physleague.kr','https://www.physleague.kr','https://haslaedu.haslalab.workers.dev']);
const EMAIL=/^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$/;
export function cleanRecoveryEmail(value){const email=typeof value==='string'?value.trim().toLowerCase():'';return email.length<=254&&EMAIL.test(email)?email:null}
export function accountMailAvailable(env){return env.AUTH_EMAIL_ENABLED==='on'&&!!cleanRecoveryEmail(env.AUTH_MAIL_FROM)&&
  (typeof env.ACCOUNT_EMAIL?.send==='function'||!!(env.AUTH_RESEND_API_KEY||env.RESEND_API_KEY))}
function returnOrigin(raw){try{const u=new URL(raw);if(ORIGINS.has(u.origin)&&u.pathname==='/'&&!u.search&&!u.hash)return u.origin}catch{}return 'https://haslalab.org'}
function randomToken(){const bytes=crypto.getRandomValues(new Uint8Array(32));return btoa(String.fromCharCode(...bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'')}
const tokenOk=value=>typeof value==='string'&&/^[A-Za-z0-9_-]{43}$/.test(value);
const escapeHtml=value=>value.replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
/* one look for every account mail: `main` is the HTML between the expiry line and the footer (a button, or a sign-up code) */
export const mailHtml=({english,title,intro,expiry,main,ignore,notice})=>`<!doctype html><html lang="${english?'en':'ko'}"><body style="margin:0;padding:32px 16px;background:#f6f5fa;color:#263247;font-family:Arial,'Malgun Gothic',sans-serif"><div style="max-width:520px;margin:0 auto;background:#fff;border:1px solid #e2ddea;border-radius:12px;padding:32px"><p style="margin:0 0 28px;font-size:22px;font-weight:700;color:#7059a4">HaslaEdu</p><h1 style="font-size:23px;line-height:1.5;margin:0 0 16px">${title}</h1><p style="font-size:15px;line-height:1.8">${intro}</p><p style="font-size:14px;line-height:1.8;color:#657187">${expiry}</p>${main}<hr style="border:0;border-top:1px solid #e2ddea;margin:28px 0"><p style="font-size:12px;line-height:1.8;color:#657187">${ignore}<br>${notice}</p></div></body></html>`;
/* the send_email binding when the Worker has one, else Resend; `key` (a digest, never the secret) makes a retried send one mail */
export async function sendMail(env,message,key){
  if(typeof env.ACCOUNT_EMAIL?.send==='function'){await env.ACCOUNT_EMAIL.send(message);return}
  const from=message.from.email,response=await fetch('https://api.resend.com/emails',{method:'POST',headers:{Authorization:'Bearer '+(env.AUTH_RESEND_API_KEY||env.RESEND_API_KEY),
    'Content-Type':'application/json','Idempotency-Key':'account-'+key},body:JSON.stringify({...message,from:'HaslaEdu <'+from+'>'}),signal:AbortSignal.timeout(15000)});
  if(!response.ok)throw Error('mail_delivery_failed');
}
async function deliver(env,{to,purpose,token,origin,lang,digest}){
  const english=lang==='en',verify=purpose==='verify',minutes=verify?30:15;
  const title=english?(verify?'Verify your recovery email':'Reset your password'):(verify?'복구 이메일 확인':'비밀번호 재설정');
  const page=origin==='https://haslalab.org'||origin==='https://www.haslalab.org'?'/account.html':'/';
  const link=origin+page+'?lang='+(english?'en':'ko')+'#/'+(verify?'verify-email':'reset-password')+'?token='+encodeURIComponent(token);
  const intro=english?(verify?'Confirm this address for your HaslaEdu / HaslaLab account.':'Choose a new password for your HaslaEdu / HaslaLab account.'):(verify?'하슬라에듀 / 하슬라랩 계정의 복구 이메일을 확인해 주세요.':'하슬라에듀 / 하슬라랩 계정의 새 비밀번호를 설정해 주세요.');
  const expiry=english?`This link expires in ${minutes} minutes and can be used once.`:`이 링크는 ${minutes}분 동안 한 번만 사용할 수 있습니다.`;
  const ignore=english?'If you did not request this, ignore this email.':'요청하지 않았다면 이 메일을 무시하세요.';
  const copyLink=english?'If the button does not work, copy this address into your browser:':'버튼이 열리지 않으면 아래 주소를 복사해 브라우저에서 열어 주세요.';
  const notice=english?'We never ask you to reply with your password or verification link.':'비밀번호나 인증 링크를 답장으로 보내 달라고 요청하지 않습니다.';
  const safeLink=escapeHtml(link);
  const main=`<p style="margin:28px 0"><a href="${safeLink}" style="display:inline-block;background:#7059a4;color:#fff;text-decoration:none;border-radius:7px;padding:14px 22px;font-weight:700">${title}</a></p><p style="font-size:12px;line-height:1.8;color:#657187">${copyLink}</p><p style="font-size:12px;line-height:1.8;word-break:break-all"><a href="${safeLink}" style="color:#7059a4">${safeLink}</a></p>`;
  await sendMail(env,{from:{email:cleanRecoveryEmail(env.AUTH_MAIL_FROM),name:'HaslaEdu'},to,subject:'HaslaEdu · '+title,
    text:['HaslaEdu',intro,link,expiry,ignore,notice].join('\n\n'),html:mailHtml({english,title,intro,expiry,main,ignore,notice})},digest);
}
/* the sign-up code (signup-email.js). The code is the only secret in it; it is six digits, so it needs no escaping */
export async function deliverSignupCode(env,{to,code,lang,minutes,key}){
  const english=lang==='en',title=english?'Your sign-up code':'가입 인증 코드';
  const intro=english?'Enter this code on the HaslaEdu / HaslaLab sign-up page to confirm your email address.':'하슬라에듀 / 하슬라랩 가입 화면에 아래 코드를 입력해 이메일 주소를 확인해 주세요.';
  const expiry=english?`The code expires in ${minutes} minutes.`:`이 코드는 ${minutes}분 동안 쓸 수 있습니다.`;
  const ignore=english?'If you did not try to sign up, ignore this email: no account is made without the code.':'가입하려 한 적이 없다면 이 메일을 무시하세요. 코드 없이는 계정이 만들어지지 않습니다.';
  const notice=english?'We never ask you to reply with your password or code.':'비밀번호나 인증 코드를 답장으로 보내 달라고 요청하지 않습니다.';
  const main=`<p style="margin:28px 0;font-size:34px;font-weight:700;letter-spacing:8px;color:#263247;font-family:'Courier New',monospace">${code}</p>`;
  await sendMail(env,{from:{email:cleanRecoveryEmail(env.AUTH_MAIL_FROM),name:'HaslaEdu'},to,subject:'HaslaEdu · '+title,
    text:['HaslaEdu',intro,code,expiry,ignore,notice].join('\n\n'),html:mailHtml({english,title,intro,expiry,main,ignore,notice})},key);
}
export function createAccountSecurityRouter({HttpError,now,limit,sha256,hashPw,checkPw,pwOk}){
  const error=(status,code)=>{throw new HttpError(status,code)};
  const authenticated=me=>{if(!me)error(401,'login_required')};
  async function account(db,me){authenticated(me);const row=await db.prepare('SELECT id,pw FROM users WHERE id=? AND deleted=0').bind(me.id).first();if(!row)error(401,'login_required');return row}
  async function confirmAccount(row,me,body){
    if(row.pw){if(typeof body.old!=='string'||!body.old)error(400,'current_password_required');if(!await checkPw(body.old,row.pw))error(401,'bad_current_password')}
    else if(!Number.isFinite(me.sessionCreatedAt)||me.sessionCreatedAt<now()-600)error(401,'recent_login_required');
  }
  async function issue(env,req,{row,email,purpose,body}){
    const t=now(),token=randomToken(),digest=await sha256(token),stamp=await sha256(row.pw||'');
    await env.DB.batch([
      env.DB.prepare('DELETE FROM account_email_tokens WHERE expires_at<?').bind(t-86400),
      env.DB.prepare('UPDATE account_email_tokens SET used_at=? WHERE user_id=? AND purpose=? AND used_at IS NULL').bind(t,row.id,purpose),
      env.DB.prepare('INSERT INTO account_email_tokens(token_hash,user_id,purpose,email,password_stamp,created_at,expires_at) VALUES(?,?,?,?,?,?,?)')
        .bind(digest,row.id,purpose,email,stamp,t,t+(purpose==='verify'?1800:900)),
    ]);
    try{await deliver(env,{to:email,purpose,token,origin:returnOrigin(body.return_origin),lang:body.lang,digest})}
    catch{await env.DB.prepare('DELETE FROM account_email_tokens WHERE token_hash=?').bind(digest).run();error(503,'email_unavailable')}
  }
  return async function accountSecurity(req,env,{path,body,me,ctx}){
    body=body&&typeof body==='object'&&!Array.isArray(body)?body:{};
    if(path==='/api/auth/recovery'&&req.method==='GET')return {mail_available:accountMailAvailable(env)};
    if(!['/api/me/security','/api/me/email','/api/me/password','/api/auth/verify-email','/api/auth/forgot-password','/api/auth/reset-password'].includes(path))return null;
    if(path==='/api/me/security'&&req.method==='GET'){
      const row=await account(env.DB,me);await ensureAccountSecuritySchema(env.DB);
      const email=await env.DB.prepare('SELECT email,verified_at FROM account_emails WHERE user_id=?').bind(me.id).first();
      const pending=await env.DB.prepare("SELECT email FROM account_email_tokens WHERE user_id=? AND purpose='verify' AND used_at IS NULL AND expires_at>? ORDER BY created_at DESC LIMIT 1").bind(me.id,now()).first();
      return {has_password:!!row.pw,email:email?.email||null,email_verified:!!email,pending_email:pending?.email||null,mail_available:accountMailAvailable(env)};
    }
    if(req.method!=='POST')return null;
    if(path==='/api/me/password'){
      const row=await account(env.DB,me);await limit(env,'pw:'+me.id,10,900);
      if(!row.pw)error(409,'password_not_set');await confirmAccount(row,me,body);
      if(!pwOk(body.password))error(400,'bad_password');if(body.password===body.old)error(409,'password_unchanged');await ensureAccountSecuritySchema(env.DB);
      const password=await hashPw(body.password);
      const changed=await env.DB.batch([
        env.DB.prepare('UPDATE users SET pw=? WHERE id=? AND pw IS ? AND deleted=0').bind(password,me.id,row.pw),
        env.DB.prepare('DELETE FROM sessions WHERE user_id=? AND token_hash<>? AND EXISTS(SELECT 1 FROM users WHERE id=? AND pw=?)').bind(me.id,me.tokenHash,me.id,password),
        env.DB.prepare("UPDATE account_email_tokens SET used_at=? WHERE user_id=? AND purpose='reset' AND used_at IS NULL AND EXISTS(SELECT 1 FROM users WHERE id=? AND pw=?)").bind(now(),me.id,me.id,password),
      ]);
      if(!changed[0]?.meta?.changes)error(409,'account_changed');return {ok:true};
    }
    if(path==='/api/me/email'){
      const row=await account(env.DB,me);await limit(env,'email-register:'+me.id,3,3600);await confirmAccount(row,me,body);
      const email=cleanRecoveryEmail(body.email);if(!email)error(400,'bad_email');if(disposableEmail(email,env))error(400,'email_disposable');
      if(!accountMailAvailable(env))error(503,'email_unavailable');await ensureAccountSecuritySchema(env.DB);
      await limit(env,'email-send:'+await sha256(email),5,3600);await limit(env,'account-email-total',100,3600);
      await issue(env,req,{row,email,purpose:'verify',body});return {ok:true};
    }
    if(path==='/api/auth/forgot-password'){
      await limit(env,'forgot-ip:'+(req.headers.get('CF-Connecting-IP')||'local'),5,900);
      const email=cleanRecoveryEmail(body.email);if(!email)error(400,'bad_email');
      if(!accountMailAvailable(env))error(503,'email_unavailable');await ensureAccountSecuritySchema(env.DB);
      await limit(env,'email-send:'+await sha256(email),5,3600);await limit(env,'account-email-total',100,3600);
      const row=await env.DB.prepare('SELECT u.id,u.pw FROM account_emails e JOIN users u ON u.id=e.user_id WHERE e.email=? AND u.deleted=0').bind(email).first();
      if(row){
        // Provider latency/failure must not reveal whether an address is on an
        // account. The Worker keeps delivery alive after the generic response.
        const delivery=issue(env,req,{row,email,purpose:'reset',body}).catch(()=>{console.error('account_recovery_delivery_failed')});
        if(ctx?.waitUntil)ctx.waitUntil(delivery);else await delivery;
      }
      return {ok:true};
    }
    if(path!=='/api/auth/verify-email'&&path!=='/api/auth/reset-password')return null;
    await limit(env,'email-confirm-ip:'+(req.headers.get('CF-Connecting-IP')||'local'),20,900);
    if(!tokenOk(body.token))error(400,'invalid_or_expired_link');await ensureAccountSecuritySchema(env.DB);
    const digest=await sha256(body.token),purpose=path==='/api/auth/verify-email'?'verify':'reset',t=now();
    const row=await env.DB.prepare(`SELECT t.*,u.pw FROM account_email_tokens t JOIN users u ON u.id=t.user_id
      WHERE t.token_hash=? AND t.purpose=? AND t.used_at IS NULL AND t.expires_at>? AND u.deleted=0`).bind(digest,purpose,t).first();
    if(!row||row.password_stamp!==await sha256(row.pw||''))error(400,'invalid_or_expired_link');
    if(purpose==='verify'){
      let results;
      try{results=await env.DB.batch([
        env.DB.prepare(`INSERT INTO account_emails(user_id,email,verified_at) SELECT ?,?,? WHERE EXISTS(
          SELECT 1 FROM account_email_tokens t JOIN users u ON u.id=t.user_id WHERE t.token_hash=? AND t.used_at IS NULL AND t.expires_at>? AND u.pw IS ? AND u.deleted=0)
          ON CONFLICT(user_id) DO UPDATE SET email=excluded.email,verified_at=excluded.verified_at`).bind(row.user_id,row.email,t,digest,t,row.pw),
        env.DB.prepare('UPDATE account_email_tokens SET used_at=? WHERE token_hash=? AND EXISTS(SELECT 1 FROM account_emails WHERE user_id=? AND email=? AND verified_at=?)').bind(t,digest,row.user_id,row.email,t),
        env.DB.prepare("UPDATE account_email_tokens SET used_at=? WHERE user_id=? AND purpose='reset' AND used_at IS NULL AND EXISTS(SELECT 1 FROM account_emails WHERE user_id=? AND email=? AND verified_at=?)").bind(t,row.user_id,row.user_id,row.email,t),
      ])}catch(e){if(/UNIQUE constraint/i.test(String(e?.message)))error(409,'email_in_use');throw e}
      if(!results[0]?.meta?.changes)error(400,'invalid_or_expired_link');return {ok:true};
    }
    if(!pwOk(body.password))error(400,'bad_password');if(row.pw&&await checkPw(body.password,row.pw))error(409,'password_unchanged');
    const password=await hashPw(body.password),results=await env.DB.batch([
      env.DB.prepare(`UPDATE users SET pw=? WHERE id=? AND deleted=0 AND pw IS ? AND EXISTS(
        SELECT 1 FROM account_email_tokens t JOIN account_emails e ON e.user_id=t.user_id AND e.email=t.email
        WHERE t.token_hash=? AND t.purpose='reset' AND t.used_at IS NULL AND t.expires_at>?)`).bind(password,row.user_id,row.pw,digest,t),
      env.DB.prepare('UPDATE account_email_tokens SET used_at=? WHERE token_hash=? AND EXISTS(SELECT 1 FROM users WHERE id=? AND pw=?)').bind(t,digest,row.user_id,password),
      env.DB.prepare('DELETE FROM sessions WHERE user_id=? AND EXISTS(SELECT 1 FROM users WHERE id=? AND pw=?)').bind(row.user_id,row.user_id,password),
      env.DB.prepare("UPDATE account_email_tokens SET used_at=? WHERE user_id=? AND purpose='reset' AND used_at IS NULL AND EXISTS(SELECT 1 FROM users WHERE id=? AND pw=?)").bind(t,row.user_id,row.user_id,password),
    ]);
    if(!results[0]?.meta?.changes)error(400,'invalid_or_expired_link');return {ok:true};
  };
}
