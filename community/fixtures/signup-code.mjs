// Password sign-up needs a code mailed to the address (src/signup-email.js). Worker tests without a mail fixture put the
// code row in themselves, as POST /api/signup/email-code would, and add the two fields it returns to the sign-up body.
import {execSync} from 'node:child_process';
import {SIGNUP_CODE_SCHEMA,signupCodeHash} from '../src/signup-email.js';
export const SIGNUP_CODE='246810';
const t=()=>Math.floor(Date.now()/1000);
// a fresh address per account: account_emails holds each address once
let n=0;export const fixtureEmail=(name='user')=>`${String(name).toLowerCase().replace(/[^a-z0-9_]/g,'')||'user'}.${process.pid}.${++n}@example.com`;
/* node:sqlite (DatabaseSync); `ttl` below 0 makes an expired code */
export async function signupCode(sql,email=fixtureEmail(),{code=SIGNUP_CODE,ttl=600,attempts=0}={}){
  for(const statement of SIGNUP_CODE_SCHEMA)sql.exec(statement);
  sql.prepare('INSERT OR REPLACE INTO signup_email_codes(email,code_hash,expires_at,attempts,created_at) VALUES(?,?,?,?,?)').run(email,await signupCodeHash(email,code),t()+ttl,attempts,t());
  return {email,code};
}
/* a test against `npm run dev`: the same row goes into the local D1 through wrangler (run from community/) */
export async function devSignupCode(email=fixtureEmail(),{code=SIGNUP_CODE,config=''}={}){
  const hash=await signupCodeHash(email,code),q=s=>"'"+s.replace(/'/g,"''")+"'";
  const command=[...SIGNUP_CODE_SCHEMA.map(s=>s.replace(/\s+/g,' ')),
    `INSERT OR REPLACE INTO signup_email_codes(email,code_hash,expires_at,attempts,created_at) VALUES(${q(email)},${q(hash)},${t()+600},0,${t()})`].join('; ');
  execSync(`npx wrangler d1 execute haslalab-community --local ${config} --command "${command}"`,{cwd:new URL('..',import.meta.url).pathname,stdio:'ignore'});
  return {email,code};
}
