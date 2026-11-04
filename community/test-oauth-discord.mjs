// Discord sign-in against a stand-in provider: the requests carry a User-Agent, and a failure comes back to the site with
// the step, the provider's status and its error code (never a token or a secret). Real Worker and SQLite; no real account.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
const origin='https://haslalab.org',gateway='https://haslalab-community-edge.haslalab.workers.dev';
function setup(){
 const sql=new DatabaseSync(':memory:');for(const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(name=>/^\d{4}_.*\.sql$/.test(name)).sort())sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
 const DB={prepare(query){const statement=sql.prepare(query),make=args=>({bind:(...values)=>make(values),async first(){return statement.get(...args)||null},async all(){return{results:statement.all(...args)}},async run(){return this.execute()},execute(){if(statement.columns().length)return{results:statement.all(...args),meta:{changes:sql.prepare('SELECT changes() n').get().n}};const out=statement.run(...args);return{results:[],meta:{changes:Number(out.changes),last_row_id:Number(out.lastInsertRowid)}}}});return make([])},async batch(statements){sql.exec('BEGIN');try{const out=statements.map(s=>s.execute());sql.exec('COMMIT');return out}catch(e){sql.exec('ROLLBACK');throw e}}};
 const env={DB,ALLOWED_ORIGINS:origin,DISCORD_CLIENT_ID:'fixture-client',DISCORD_CLIENT_SECRET:'fixture-secret',OAUTH_MOCK_BASE:'https://provider.invalid'};
 const get=path=>worker.fetch(new Request(path.startsWith('http')?path:gateway+path,{headers:{Origin:origin,'CF-Connecting-IP':'192.0.2.90'}}),env,{waitUntil(){}});
 /* one round trip: start, then the provider's callback; `reply(url, init)` stands in for Discord */
 const signIn=async reply=>{const original=globalThis.fetch,seen=[];globalThis.fetch=async(input,init={})=>{const url=new URL(input);assert.equal(url.origin,'https://provider.invalid');seen.push({path:url.pathname,ua:new Headers(init.headers).get('User-Agent')});return reply(url,init)};
  try{const started=await get('/api/oauth/discord/start?return='+encodeURIComponent(origin+'/'));assert.equal(started.status,302);
   const state=new URL(started.headers.get('Location')).searchParams.get('state'),done=await get('/api/oauth/discord/callback?state='+state+'&code=fixture');
   assert.equal(done.status,302);return{back:new URL(done.headers.get('Location')),seen}}finally{globalThis.fetch=original}};
 return{signIn,close(){sql.close()}};
}
const frag=back=>new URLSearchParams(back.hash.split('?')[1]||'');

test('Discord sign-in: both requests identify HaslaLab and a new account is made from the Discord profile',async()=>{
 const s=setup();try{
  const {back,seen}=await s.signIn(url=>Response.json(url.pathname.includes('token')?{access_token:'fixture-access'}:{id:'80351110224678912',username:'nelly',global_name:'Nelly'}));
  assert.ok(frag(back).get('c'),'a one-time code comes back to the site');
  assert.deepEqual(seen.map(x=>x.path),['/api/oauth2/token','/api/users/@me']);
  for(const x of seen)assert.match(x.ua||'',/^HaslaLab \(https:\/\/haslalab\.org/);
 }finally{s.close()}
});

test('Discord sign-in: a wrong client secret is reported as token-401-invalid_client',async()=>{
 const s=setup();try{
  const {back}=await s.signIn(url=>url.pathname.includes('token')?Response.json({error:'invalid_client'},{status:401}):Response.json({}));
  assert.equal(frag(back).get('e'),'oauth_failed');assert.equal(frag(back).get('d'),'token-401-invalid_client');
  assert.doesNotMatch(back.href,/fixture-secret|fixture-access/);
 }finally{s.close()}
});

test('Discord sign-in: a blocked request (an HTML page, no JSON) is reported by its status',async()=>{
 const s=setup();try{
  const {back}=await s.signIn(url=>url.pathname.includes('token')?new Response('<html>error code: 1010</html>',{status:403,headers:{'Content-Type':'text/html'}}):Response.json({}));
  assert.equal(frag(back).get('d'),'token-403');
  const {back:profile}=await s.signIn(url=>url.pathname.includes('token')?Response.json({access_token:'fixture-access'}):Response.json({message:'401: Unauthorized',code:0},{status:401}));
  assert.equal(frag(profile).get('d'),'profile-401-401_unauthorized');
 }finally{s.close()}
});
