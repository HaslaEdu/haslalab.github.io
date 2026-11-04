// node --test community/test-paddle-switch.mjs
// PADDLE_CHECKOUT "off" closes Paddle checkout: no pack offered, no new order; the signed webhook still answers.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
import {signupCode} from './fixtures/signup-code.mjs';

globalThis.caches ??= { default: { async match() {}, async put() {} } };
const PADDLE={PADDLE_CLIENT_TOKEN:'test_fixture',PADDLE_API_KEY:'pdl_fixture',PADDLE_WEBHOOK_SECRET:'pdl_ntfset_fixture',
  PADDLE_PACKS:JSON.stringify([{id:'p1',tokens:1,price_id:'pri_01fixtureone',usd:1.49}])};
function setup(extra){
  const sql=new DatabaseSync(':memory:');for(const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(n=>/^\d{4}_.*\.sql$/.test(n)).sort())sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
  const DB={prepare(query){const st=sql.prepare(query),make=args=>({bind:(...v)=>make(v),async first(){return st.get(...args)||null},async all(){return{results:st.all(...args)}},async run(){return this.execute()},execute(){if(st.columns().length)return{results:st.all(...args),meta:{changes:sql.prepare('SELECT changes() n').get().n}};const o=st.run(...args);return{results:[],meta:{changes:Number(o.changes),last_row_id:Number(o.lastInsertRowid)}}}});return make([])},
    async batch(sts){sql.exec('BEGIN');try{const o=sts.map(s=>s.execute());sql.exec('COMMIT');return o}catch(e){sql.exec('ROLLBACK');throw e}}};
  const env={DB,ALLOWED_ORIGINS:'https://haslalab.org',AUTH_EMAIL_ENABLED:'on',AUTH_MAIL_FROM:'a@hasla.example',ACCOUNT_EMAIL:{async send(){return{messageId:'x'}}},...PADDLE,...extra};
  let ip=10;
  const api=async(m,path,body,{token,headers={}}={})=>{const r=await worker.fetch(new Request('https://worker.invalid/api'+path,{method:m,headers:{Origin:'https://haslalab.org','CF-Connecting-IP':'192.0.2.'+(ip++),...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{}),...headers},body:body?JSON.stringify(body):undefined}),env,{waitUntil(){}});return{status:r.status,data:await r.json().catch(()=>null)}};
  return {sql,api,close(){sql.close()}};
}
async function user(s){const {email}=await signupCode(s.sql,'buyer@example.com');const r=await s.api('POST','/signup',{username:'buyer',nickname:'buyer n',password:'fixture-password',consent:{terms:true,privacy:true,age14:true},email,code:'246810'});assert.equal(r.status,200,JSON.stringify(r.data));return r.data.token;}

test('Paddle checkout closed: no pack in the shop, no new order, the webhook still checks its signature', async () => {
  const s=setup({PADDLE_CHECKOUT:'off'});try{
    const cfg=await s.api('GET','/pay/config');assert.equal(cfg.status,200);assert.equal(cfg.data.paddle,null);
    const token=await user(s);
    const order=await s.api('POST','/pay/order',{pack:'p1',provider:'paddle'},{token});
    assert.equal(order.status,503);assert.equal(order.data.error,'pay_off');
    assert.equal(s.sql.prepare('SELECT count(*) n FROM pay_orders').get().n,0,'no order is written');
    const hook=await s.api('POST','/pay/paddle/webhook',{event_type:'transaction.completed',data:{}},{headers:{'Paddle-Signature':'ts=1;h1=00'}});
    assert.equal(hook.status,401,'the webhook is still there and still refuses a bad signature');
  }finally{s.close()}
});
test('Paddle checkout open (PADDLE_CHECKOUT unset): the pack is offered and an order is made', async () => {
  const s=setup({});try{
    const cfg=await s.api('GET','/pay/config');assert.equal(cfg.data.paddle.packs[0].id,'p1');
    const token=await user(s);
    const order=await s.api('POST','/pay/order',{pack:'p1',provider:'paddle'},{token});
    assert.equal(order.status,200,JSON.stringify(order.data));
  }finally{s.close()}
});
