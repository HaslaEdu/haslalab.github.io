// Worker tests that sit or grade an exam: their fixture accounts have agreed to the current terms, as grading requires.
import {CONSENT_SQL,TERMS_VERSION} from '../src/consent.js';
export const AGREED={terms:true,privacy:true,age14:true};
export function agreeTerms(sql,ids,at=Math.floor(Date.now()/1000),{train=false}={}){
  sql.exec(CONSENT_SQL);
  const row=sql.prepare('INSERT OR REPLACE INTO user_consents(user_id,terms_version,age_ok,train_ok,agreed_at) VALUES(?,?,1,?,?)');
  for(const id of [].concat(ids))row.run(id,TERMS_VERSION,train?1:0,at);
}
