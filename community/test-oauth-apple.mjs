// Sign in with Apple (src/oauth-apple.js): real Worker and SQLite, Apple mocked. Never authenticates a real user.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
import {appleSubject,appleClientSecret,appleConfigured} from './src/oauth-apple.js';

const origin='https://haslalab.org',gateway='https://haslalab-community-edge.haslalab.workers.dev';
const b64u=v=>Buffer.from(typeof v==='string'?v:JSON.stringify(v)).toString('base64url');
const idToken=claims=>b64u({alg:'RS256',kid:'x'})+'.'+b64u(claims)+'.sig';
const pem=async()=>{const pair=await crypto.subtle.generateKey({name:'ECDSA',namedCurve:'P-256'},true,['sign','verify']);
  const der=Buffer.from(await crypto.subtle.exportKey('pkcs8',pair.privateKey)).toString('base64');
  return{pem:'-----BEGIN PRIVATE KEY-----\n'+der.match(/.{1,64}/g).join('\n')+'\n-----END PRIVATE KEY-----',publicKey:pair.publicKey};};

async function setup(){
  const sql=new DatabaseSync(':memory:');for(const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(n=>/^\d{4}_.*\.sql$/.test(n)).sort())sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
  const DB={prepare(query){const statement=sql.prepare(query),make=args=>({bind:(...values)=>make(values),async first(){return statement.get(...args)||null},async all(){return{results:statement.all(...args)}},async run(){return this.execute()},execute(){if(statement.columns().length)return{results:statement.all(...args),meta:{changes:sql.prepare('SELECT changes() n').get().n}};const out=statement.run(...args);return{results:[],meta:{changes:Number(out.changes),last_row_id:Number(out.lastInsertRowid)}}}});return make([])},async batch(statements){sql.exec('BEGIN');try{const out=statements.map(s=>s.execute());sql.exec('COMMIT');return out}catch(e){sql.exec('ROLLBACK');throw e}}};
  const key=await pem();
  const env={DB,ALLOWED_ORIGINS:origin,OAUTH_MOCK_BASE:'https://provider.invalid',APPLE_CLIENT_ID:'kr.haslaedu.signin',APPLE_TEAM_ID:'TEAM123456',APPLE_KEY_ID:'KEY1234567',APPLE_PRIVATE_KEY:key.pem};
  const calls=[];
  const get=path=>worker.fetch(new Request(gateway+path,{headers:{Origin:origin,'CF-Connecting-IP':'192.0.2.90'}}),env,{waitUntil(){}});
  const api=async(method,path,body,token)=>{const r=await worker.fetch(new Request(gateway+'/api'+path,{method,headers:{Origin:origin,'CF-Connecting-IP':'192.0.2.90',...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{})},...(body?{body:JSON.stringify(body)}:{})}),env,{waitUntil(){}});return{status:r.status,data:await r.json()}};
  const withApple=async(answer,fn)=>{const original=globalThis.fetch;globalThis.fetch=async(input,init={})=>{const url=new URL(input);assert.equal(url.origin,'https://provider.invalid');calls.push({path:url.pathname,body:new URLSearchParams(String(init.body||''))});return Response.json(answer(url.pathname))};try{return await fn()}finally{globalThis.fetch=original}};
  return{sql,env,key,calls,get,api,withApple,close(){sql.close()}};
}
const tokenAnswer=(env,sub='000123.abcdef.0456',aud)=>path=>path.endsWith('/token')?{access_token:'a',refresh_token:'r-'+sub,id_token:idToken({iss:'https://appleid.apple.com',aud:aud||env.APPLE_CLIENT_ID,sub,exp:Math.floor(Date.now()/1000)+600})}:{};

test('id_token checks: issuer, audience, expiry and a sane subject',()=>{
  const now=1_800_000_000,ok={iss:'https://appleid.apple.com',aud:'svc',sub:'001.abc.002',exp:now+60};
  assert.equal(appleSubject(idToken(ok),'svc',now),'001.abc.002');
  assert.equal(appleSubject(idToken({...ok,aud:['other','svc']}),'svc',now),'001.abc.002');
  assert.equal(appleSubject(idToken({...ok,iss:'https://evil.example'}),'svc',now),null);
  assert.equal(appleSubject(idToken({...ok,aud:'other'}),'svc',now),null);
  assert.equal(appleSubject(idToken({...ok,exp:now-120}),'svc',now),null);
  assert.equal(appleSubject(idToken({...ok,sub:'a b'}),'svc',now),null);
  assert.equal(appleSubject('not.a',  'svc',now),null);assert.equal(appleSubject(undefined,'svc',now),null);
});

test('the client secret is an ES256 JWT for this Services ID, verifiable with the key',async()=>{
  const s=await setup();try{
    const jwt=await appleClientSecret(s.env,1_800_000_000),[h,p,sig]=jwt.split('.');
    assert.deepEqual(JSON.parse(Buffer.from(h,'base64url')),{alg:'ES256',kid:'KEY1234567'});
    assert.deepEqual(JSON.parse(Buffer.from(p,'base64url')),{iss:'TEAM123456',iat:1_800_000_000,exp:1_800_000_300,aud:'https://appleid.apple.com',sub:'kr.haslaedu.signin'});
    assert.ok(await crypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},s.key.publicKey,Buffer.from(sig,'base64url'),new TextEncoder().encode(h+'.'+p)));
    // a key pasted with literal \n (as some dashboards store it) works too
    assert.ok((await appleClientSecret({...s.env,APPLE_PRIVATE_KEY:s.key.pem.replace(/\n/g,'\\n')})).split('.').length===3);
    assert.equal(appleConfigured({...s.env,APPLE_KEY_ID:''}),false);assert.equal(appleConfigured({...s.env,APPLE_TEAM_ID:'short'}),false);
  }finally{s.close()}
});

test('offered only with all four secrets; sign-in asks for nothing and returns by GET',async()=>{
  const s=await setup();try{
    assert.ok((await s.api('GET','/oauth/providers')).data.providers.includes('apple'));
    const bare={...s.env};delete bare.APPLE_PRIVATE_KEY;
    const r=await worker.fetch(new Request(gateway+'/api/oauth/providers',{headers:{Origin:origin}}),bare,{waitUntil(){}});
    assert.ok(!(await r.json()).providers.includes('apple'));
    const start=await s.get('/api/oauth/apple/start?return='+encodeURIComponent(origin+'/'));
    assert.equal(start.status,302);const to=new URL(start.headers.get('Location'));
    assert.equal(to.pathname,'/auth/authorize');assert.equal(to.searchParams.get('response_mode'),'query');
    assert.equal(to.searchParams.get('scope'),null,'no name or e-mail asked for');assert.equal(to.searchParams.get('client_id'),'kr.haslaedu.signin');
    assert.equal(to.searchParams.get('redirect_uri'),gateway+'/api/oauth/apple/callback');
  }finally{s.close()}
});

test('a new Apple user gets an account; only the sub and the refresh token (for revocation) are kept',async()=>{
  const s=await setup();try{
    const start=await s.get('/api/oauth/apple/start?return='+encodeURIComponent(origin+'/'));const state=new URL(start.headers.get('Location')).searchParams.get('state');
    const back=await s.withApple(tokenAnswer(s.env),()=>s.get('/api/oauth/apple/callback?state='+state+'&code=fixture'));
    assert.equal(back.status,302);const loc=new URL(back.headers.get('Location'));assert.match(loc.hash,/^#\/oauth\?c=/);
    const token=s.calls.find(c=>c.path==='/auth/token');assert.ok(token,'token endpoint called');assert.equal(token.body.get('client_id'),'kr.haslaedu.signin');assert.equal(token.body.get('client_secret').split('.').length,3);
    assert.equal(s.calls.filter(c=>c.path!=='/auth/token').length,0,'no user-info call');
    const id=s.sql.prepare("SELECT user_id FROM identities WHERE provider='apple' AND sub=?").get('000123.abcdef.0456');assert.ok(id);
    assert.equal(s.sql.prepare('SELECT refresh_token FROM apple_tokens WHERE user_id=?').get(id.user_id).refresh_token,'r-000123.abcdef.0456');
    const code=new URLSearchParams(loc.hash.split('?')[1]).get('c'),signed=await s.api('POST','/oauth/redeem',{code});
    assert.equal(signed.status,200);
    // deleting the account revokes the Apple token and forgets it (App Store Guideline 5.1.1(v))
    s.calls.length=0;
    const gone=await s.withApple(()=>({}),()=>s.api('DELETE','/me',{},signed.data.token));
    assert.equal(gone.status,200,JSON.stringify(gone.data));assert.equal(gone.data.ok,true);
    const revoke=s.calls.find(c=>c.path==='/auth/revoke');assert.ok(revoke,'revoke called');
    assert.equal(revoke.body.get('token'),'r-000123.abcdef.0456');assert.equal(revoke.body.get('token_type_hint'),'refresh_token');
    assert.equal(s.sql.prepare('SELECT COUNT(*) n FROM apple_tokens').get().n,0);
    assert.equal(s.sql.prepare("SELECT COUNT(*) n FROM identities WHERE provider='apple'").get().n,0);
  }finally{s.close()}
});

test('an id_token for another Services ID is refused',async()=>{
  const s=await setup();try{
    const start=await s.get('/api/oauth/apple/start?return='+encodeURIComponent(origin+'/'));const state=new URL(start.headers.get('Location')).searchParams.get('state');
    const back=await s.withApple(tokenAnswer(s.env,'000999.x.1','someone.else'),()=>s.get('/api/oauth/apple/callback?state='+state+'&code=fixture'));
    assert.equal(back.status,302);assert.match(back.headers.get('Location'),/e=oauth_failed&d=token-id_token/);
    assert.equal(s.sql.prepare("SELECT COUNT(*) n FROM identities WHERE provider='apple'").get().n,0);
  }finally{s.close()}
});
