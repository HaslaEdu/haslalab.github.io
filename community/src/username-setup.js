// One explicit login-name choice for historical social-only accounts.
// Their old generated identifier and numeric user/role ownership stay intact.
const ready=new WeakMap();
export const USERNAME_CLAIM_SCHEMA=`CREATE TABLE IF NOT EXISTS account_username_claims (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 previous_username TEXT NOT NULL, chosen_username TEXT NOT NULL, claimed_at INTEGER NOT NULL
)`;
export const isPendingUsername=user=>!!user&&String(user.username).startsWith('~pending_');
const legacyShape=name=>typeof name==='string'&&/^[gdnk]_[A-Za-z0-9]{1,10}$/.test(name);
// Old OAuth created its matching identity with the user. Passwords may have
// been added later, so current password presence is not a creation record.
// A prefix alone is not evidence. This exposes an optional, owner-confirmed
// choice; ordinary g_* accounts without the initial identity stay unchanged.
const initialSocial=`EXISTS(SELECT 1 FROM identities i WHERE i.user_id=u.id
 AND i.created_at BETWEEN u.created_at AND u.created_at+60
 AND ((substr(u.username,1,1)='g' AND i.provider IN ('google','github'))
 OR (substr(u.username,1,1)='d' AND i.provider='discord')
 OR (substr(u.username,1,1)='n' AND i.provider='naver')
 OR (substr(u.username,1,1)='k' AND i.provider='kakao')))`;
export function ensureUsernameClaimSchema(db,scope=db){if(!ready.has(scope))ready.set(scope,db.prepare(USERNAME_CLAIM_SCHEMA).run().catch(error=>{ready.delete(scope);throw error}));return ready.get(scope)}
export function usernameProfileColumns(user){return `c.previous_username AS _username_previous,CASE WHEN ${legacyShape(user.username)?initialSocial:'0'} THEN 1 ELSE 0 END AS _username_legacy`;}
export function decorateUsernameProfile(user,record){
 if(!user||!record)return user;
 if(record._username_previous!==null&&record._username_previous!==undefined)return {...user,username_setup_available:false,...(legacyShape(record._username_previous)?{unique_identifier:record._username_previous,username_kind:'chosen'}:{})};
 if(isPendingUsername(user))return {...user,username_setup_available:true};
 return record._username_legacy?{...user,username_setup_available:true,username_kind:'generated',unique_identifier:user.username}:user;
}
export async function usernameProfile(env,user,scope=env.DB){
 if(!user)return user;await ensureUsernameClaimSchema(env.DB,scope);
 const record=await env.DB.prepare(`SELECT ${usernameProfileColumns(user)} FROM users u LEFT JOIN account_username_claims c ON c.user_id=u.id WHERE u.id=? AND u.username=? AND u.deleted=0`).bind(user.id,user.username).first();
 return decorateUsernameProfile(user,record);
}
export async function claimUsername(env,me,username,now,scope=env.DB){
 await ensureUsernameClaimSchema(env.DB,scope);
 const pending=isPendingUsername(me),eligible=pending||legacyShape(me.username)&&me.username_setup_available===true;
 if(!eligible)return false;
 // Insert and compare-and-swap are one D1 transaction. A uniqueness failure
 // rolls the marker back, while concurrent requests cannot claim twice.
 const outcome=await env.DB.batch([
  env.DB.prepare(`INSERT INTO account_username_claims(user_id,previous_username,chosen_username,claimed_at)
   SELECT ?,?,?,? WHERE EXISTS(SELECT 1 FROM users u WHERE u.id=? AND u.username=? AND u.deleted=0
   AND (${pending?'1':initialSocial})) AND NOT EXISTS(SELECT 1 FROM account_username_claims WHERE user_id=?)`)
   .bind(me.id,me.username,username,now,me.id,me.username,me.id),
  env.DB.prepare(`UPDATE users SET username=? WHERE id=? AND username=? AND deleted=0
   AND EXISTS(SELECT 1 FROM account_username_claims WHERE user_id=? AND previous_username=? AND chosen_username=? AND claimed_at=?)`)
   .bind(username,me.id,me.username,me.id,me.username,username,now),
 ]);
 return !!outcome[0]?.meta?.changes&&!!outcome[1]?.meta?.changes;
}
