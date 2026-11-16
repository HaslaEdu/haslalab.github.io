// AccountEvents.deletedAmong (src/worker.js): the HaslaEdu Worker learns which of its members deleted their account.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';

test('answers only for the ids asked about, and only deleted ones',async()=>{
  // cloudflare:workers is not available under Node: give the entrypoint a stand-in base class.
  const {register}=await import('node:module');
  register('data:text/javascript,'+encodeURIComponent(`export async function resolve(s,c,n){if(s==='cloudflare:workers')return{url:'data:text/javascript,export class WorkerEntrypoint{constructor(ctx,env){this.ctx=ctx;this.env=env}}',shortCircuit:true};return n(s,c)}`));
  const {AccountEvents}=await import('./src/worker.js');
  const sql=new DatabaseSync(':memory:');sql.exec('CREATE TABLE users(id INTEGER PRIMARY KEY, deleted INTEGER NOT NULL DEFAULT 0)');
  for(const [id,deleted] of [[1,0],[2,1],[3,2],[4,1],[700,1]])sql.prepare('INSERT INTO users VALUES(?,?)').run(id,deleted);
  const DB={prepare:q=>{const st=sql.prepare(q);return{bind:(...a)=>({all:async()=>({results:st.all(...a)})})}}};
  const events=new AccountEvents({}, {DB});
  assert.deepEqual((await events.deletedAmong([1,2,3,4,4,'5',-1,1.5])).sort((a,b)=>a-b),[2,4],'suspended (2) is not deleted; junk ignored');
  assert.deepEqual(await events.deletedAmong('nope'),[]);
  const many=Array.from({length:600},(_,i)=>i+1);
  assert.deepEqual((await events.deletedAmong(many)).sort((a,b)=>a-b),[2,4],'700 is beyond the first 500 asked');
});
