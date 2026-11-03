// Terms, privacy and the optional training consent, one row per account.
// A new TERMS_VERSION asks every account again: a row of an older version counts as no consent.
// Korea (PIPA art. 22-2) needs a guardian for under-14s; the service takes no guardian consent, so
// under-14s in KR are refused at sign-up. Outside KR the age box is not asked.
export const TERMS_VERSION='2026-11-03';
export const CONSENT_SQL=`CREATE TABLE IF NOT EXISTS user_consents (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 terms_version TEXT NOT NULL, age_ok INTEGER NOT NULL DEFAULT 0, train_ok INTEGER NOT NULL DEFAULT 0,
 country TEXT, agreed_at INTEGER NOT NULL, train_at INTEGER
)`;
// training rows are kept at most this long after capture (the privacy notice promises one year)
export const TRAIN_KEEP_SEC=365*86400;
const ready=new WeakMap();
// env.DB is wrapped per request for timing; the scope is the raw binding, so the CREATE runs once per isolate
export function ensureConsentSchema(db,scope=db){if(!ready.has(scope))ready.set(scope,db.prepare(CONSENT_SQL).run().catch(error=>{ready.delete(scope);throw error}));return ready.get(scope)}
/* request.cf on a direct request; behind the edge gateway's service binding the copied CF-IPCountry header
   (set by Cloudflare's edge, not by the client) carries it */
export const requestCountry=req=>{const c=req?.cf?.country||req?.headers?.get?.('CF-IPCountry');return typeof c==='string'&&/^[A-Z]{2}$/.test(c)?c:null};
export const ageRequired=country=>country==='KR';
export const consentInfo=req=>{const country=requestCountry(req);return {version:TERMS_VERSION,country,age_required:ageRequired(country)}};
/* body.consent = {terms:true, privacy:true, age14:bool, train:bool}. Only literal true counts as agreement,
   so a missing field or the string "true" is no consent. `fail(code)` throws the caller's 400. */
export function readConsent(value,country,fail){
 const c=value&&typeof value==='object'&&!Array.isArray(value)?value:{};
 if(c.terms!==true||c.privacy!==true)fail('consent_required');
 if(ageRequired(country)&&c.age14!==true)fail('age_required');
 return {age14:c.age14===true,train:c.train===true,country:country||null};
}
/* one upsert; train_at is the time of the last training decision (given or withdrawn) */
export function consentStatement(db,userId,consent,t){
 return db.prepare(`INSERT INTO user_consents(user_id,terms_version,age_ok,train_ok,country,agreed_at,train_at) VALUES(?,?,?,?,?,?,?)
  ON CONFLICT(user_id) DO UPDATE SET terms_version=excluded.terms_version,age_ok=excluded.age_ok,train_ok=excluded.train_ok,
  country=excluded.country,agreed_at=excluded.agreed_at,
  train_at=CASE WHEN excluded.train_ok=user_consents.train_ok THEN user_consents.train_at ELSE excluded.train_at END`)
  .bind(userId,TERMS_VERSION,consent.age14?1:0,consent.train?1:0,consent.country||null,t,t);
}
export async function recordConsent(db,userId,consent,t,scope=db){await ensureConsentSchema(db,scope);await consentStatement(db,userId,consent,t).run()}
const shape=row=>({consent_required:row?.terms_version!==TERMS_VERSION,train_ok:row?.terms_version===TERMS_VERSION&&row.train_ok===1});
export async function consentStatus(db,userId,scope=db){
 await ensureConsentSchema(db,scope);
 const row=await db.prepare('SELECT terms_version,age_ok,train_ok,country,agreed_at,train_at FROM user_consents WHERE user_id=?').bind(userId).first();
 return {...shape(row),version:TERMS_VERSION,agreed_at:row?.agreed_at??null,train_at:row?.train_at??null};
}
// the two fields pubUser shows; a user object without them leaves pubUser unchanged
export const decorateConsent=(user,status)=>user&&status?{...user,consent_required:status.consent_required,train_ok:status.train_ok}:user;
// for a query that already reads the user row: LEFT JOIN user_consents k ON k.user_id=u.id
export const CONSENT_COLUMNS='k.terms_version AS _consent_version,k.train_ok AS _consent_train';
export const consentOf=row=>shape(row&&row._consent_version!=null?{terms_version:row._consent_version,train_ok:row._consent_train}:null);
/* Withdrawing deletes what was captured from this user's sittings; giving it again only applies to later grading. */
export async function dropTrainRows(db,userId,trainSql){await db.prepare(trainSql).run();await db.prepare('DELETE FROM lab_train WHERE session_id IN (SELECT id FROM lab_sessions WHERE user_id=?)').bind(userId).run()}
// Toggling needs a current consent row: training consent without the terms would mean nothing.
export async function setTrainConsent(db,userId,train,t,trainSql,scope=db){
 await ensureConsentSchema(db,scope);
 const changed=await db.prepare('UPDATE user_consents SET train_ok=?,train_at=CASE WHEN train_ok=? THEN train_at ELSE ? END WHERE user_id=? AND terms_version=?').bind(train?1:0,train?1:0,t,userId,TERMS_VERSION).run();
 if(!changed.meta?.changes)return false;
 if(!train)await dropTrainRows(db,userId,trainSql);
 return true;
}
// the grader's capture asks this: only a current consent with the training box ticked
export async function trainAllowed(db,userId,scope=db){
 await ensureConsentSchema(db,scope);
 return !!(await db.prepare('SELECT 1 FROM user_consents WHERE user_id=? AND terms_version=? AND train_ok=1').bind(userId,TERMS_VERSION).first());
}
