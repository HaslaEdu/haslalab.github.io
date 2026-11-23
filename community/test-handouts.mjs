import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {createHandoutRouter, HANDOUT_MAX_BYTES, cleanFileName, isPdf} from './src/handouts.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
/* R2 as the Worker sees it: put, get (with a readable body), delete */
function fakeR2(){
  const store=new Map();
  return {store,
    async put(key,bytes,opts){store.set(key,{bytes:new Uint8Array(bytes),opts});},
    async get(key){const o=store.get(key);if(!o)return null;return{size:o.bytes.length,httpEtag:'"e-'+key.length+'"',body:new Blob([o.bytes]).stream(),async arrayBuffer(){return o.bytes.buffer;}};},
    async delete(key){for(const k of [].concat(key))store.delete(k);}};
}
function setup({r2=true}={}){
  const db=new DatabaseSync(':memory:');
  const D1={prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){db.prepare(sql).run(...args);return{meta:{}};}};}};
  const limits=[];let t=1_800_000_000;
  const route=createHandoutRouter({HttpError:H,bad,now:()=>t,needUser:u=>{if(!u)throw new H(401,'login_required');return u;},
    limit:async(env,key,max,win)=>{limits.push([key,max,win]);},isAdmin:u=>u?.role==='admin'});
  const R2=r2?fakeR2():null,env={DB:D1,...(R2?{LAB_PAGES:R2}:{})};
  const call=(p,m,body,me,req)=>route(p,m,body,me,req||new Request('https://x.test'+p,{method:m==='GET'||m==='DELETE'?m:'PATCH'}),env);
  return {db,R2,env,limits,call,route,tick:s=>{t+=s;}};
}
const admin={id:1,role:'admin'},member={id:7};
const pdf=(n=100)=>Buffer.concat([Buffer.from('%PDF-1.7\n'),Buffer.alloc(n,0x20),Buffer.from('\n%%EOF\n')]);
const json=(over={})=>({title_ko:'등가속도 운동 정리',title_en:'Constant acceleration notes',summary_ko:'네 식과 예제',unit:'mechanics/kinematics',level:3,status:'public',file_name:'kinematics.pdf',file_base64:pdf().toString('base64'),...over});
const fails=async(p,code,status)=>assert.rejects(p,e=>e.code===code&&(status==null||e.status===status));

test('only an administrator uploads; a PDF goes to R2 under handouts/ and the row records it',async()=>{
  const {call,R2,db,limits}=setup();
  await fails(call('/api/learn/handouts','POST',json(),null),'login_required',401);
  await fails(call('/api/learn/handouts','POST',json(),member),'forbidden',403);
  const {handout:h}=await call('/api/learn/handouts','POST',json(),admin);
  assert.equal(h.title_en,'Constant acceleration notes');assert.equal(h.unit,'mechanics/kinematics');assert.equal(h.level,3);assert.equal(h.status,'public');
  assert.equal(h.bytes,pdf().length);assert.equal(h.file,`/api/learn/handouts/${h.id}/file`);assert.ok(!('file_key' in h),'the R2 key stays on the server');
  const row=db.prepare('SELECT * FROM handouts WHERE id=?').get(h.id);
  assert.match(row.file_key,/^handouts\/[0-9a-f-]{36}\.pdf$/);assert.equal(row.author_id,1);
  assert.equal(R2.store.get(row.file_key).opts.httpMetadata.contentType,'application/pdf');
  assert.ok(limits.some(([k])=>k==='handout-up:1'),'uploads are rate limited');
});

test('multipart/form-data works the same as JSON',async()=>{
  const {route,env,R2}=setup();
  const form=new FormData();
  form.set('file',new File([pdf(300)],'../../핸드아웃 1.pdf',{type:'application/pdf'}));
  form.set('title_ko','에너지 보존');form.set('unit','mechanics/energy');form.set('level','4');
  const req=new Request('https://x.test/api/learn/handouts',{method:'POST',body:form});
  const {handout:h}=await route('/api/learn/handouts','POST',{},admin,req,env);
  assert.equal(h.file_name,'핸드아웃 1.pdf','the path is dropped from the name');
  assert.equal(h.status,'hidden','a new handout is hidden unless marked public');
  assert.equal(h.level,4);assert.equal(R2.store.size,1);
});

test('anything that is not a PDF, or is over 25 MB, is refused before it is stored',async()=>{
  const {call,R2,route,env}=setup();
  await fails(call('/api/learn/handouts','POST',json({file_base64:Buffer.from('<html>not a pdf</html>').toString('base64')}),admin),'pdf_only',415);
  await fails(call('/api/learn/handouts','POST',json({file_base64:Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a]).toString('base64'),file_name:'x.pdf'}),admin),'pdf_only',415);
  await fails(call('/api/learn/handouts','POST',json({file_base64:''}),admin),'file_required');
  await fails(call('/api/learn/handouts','POST',json({file_base64:'%%%'}),admin),'bad_file');
  const big=Buffer.concat([pdf(0),Buffer.alloc(HANDOUT_MAX_BYTES)]);
  await fails(call('/api/learn/handouts','POST',json({file_base64:big.toString('base64')}),admin),'file_too_large',413);
  const form=new FormData();form.set('file',new File([big],'big.pdf'));form.set('title_ko','큰 파일');
  await fails(route('/api/learn/handouts','POST',{},admin,new Request('https://x.test/api/learn/handouts',{method:'POST',body:form}),env),'file_too_large',413);
  const declared=new Request('https://x.test/api/learn/handouts',{method:'POST',headers:{'Content-Length':String(40*1024*1024),'Content-Type':'application/json'},body:'{}'});
  await fails(route('/api/learn/handouts','POST',json(),admin,declared,env),'file_too_large',413);
  await fails(call('/api/learn/handouts','POST',json({title_ko:'',title_en:''}),admin),'bad_title');
  await fails(call('/api/learn/handouts','POST',json({unit:'../etc'}),admin),'bad_unit');
  await fails(call('/api/learn/handouts','POST',json({level:11}),admin),'bad_level');
  await fails(call('/api/learn/handouts','POST',json({status:'draft'}),admin),'bad_status');
  assert.equal(R2.store.size,0,'nothing reached R2');
  assert.ok(isPdf(new Uint8Array(pdf())));assert.ok(!isPdf(new Uint8Array([0x25,0x50,0x44])));
  assert.equal(cleanFileName('notes'),'notes.pdf');assert.equal(cleanFileName('a"b.PDF'),'ab.PDF');
});

test('without the R2 binding the upload says so and stores nothing',async()=>{
  const {call,db}=setup({r2:false});
  await fails(call('/api/learn/handouts','POST',json(),admin),'r2_unavailable',503);
  assert.equal(db.prepare('SELECT COUNT(*) n FROM handouts').get().n,0);
});

test('the public list shows public handouts only, filtered by unit and level; administrators can see hidden ones',async()=>{
  const {call}=setup();
  await call('/api/learn/handouts','POST',json(),admin);
  await call('/api/learn/handouts','POST',json({title_ko:'숨김',unit:'mechanics/energy',level:4,status:'hidden'}),admin);
  await call('/api/learn/handouts','POST',json({title_ko:'광학',unit:'optics/lenses',level:2}),admin);
  const get=(q,me)=>call('/api/learn/handouts','GET',null,me,new Request('https://x.test/api/learn/handouts'+q));
  assert.deepEqual((await get('',null)).handouts.map(h=>h.unit),['mechanics/kinematics','optics/lenses']);
  assert.equal((await get('',null)).admin,false);
  assert.deepEqual((await get('?unit=optics/lenses',null)).handouts.map(h=>h.title_ko),['광학']);
  assert.deepEqual((await get('?unit=mechanics',null)).handouts.map(h=>h.title_ko),['등가속도 운동 정리'],'an area alone matches its units');
  assert.deepEqual((await get('?level=2',null)).handouts.map(h=>h.title_ko),['광학']);
  assert.equal((await get('?all=1',member)).handouts.length,2,'?all=1 means nothing to a member');
  const all=await get('?all=1',admin);assert.equal(all.handouts.length,3);assert.equal(all.admin,true);
  await fails(get('?unit=%3Cscript%3E',null),'bad_unit');
  await fails(get('?level=0',null),'bad_level');
});

test('the file is streamed inline as a PDF with cache headers; a hidden one only to administrators',async()=>{
  const {call,R2}=setup();
  const pub=(await call('/api/learn/handouts','POST',json({file_name:'등가속도.pdf'}),admin)).handout;
  const hid=(await call('/api/learn/handouts','POST',json({status:'hidden'}),admin)).handout;
  const res=await call(pub.file,'GET',null,null);
  assert.ok(res instanceof Response);assert.equal(res.status,200);
  assert.equal(res.headers.get('Content-Type'),'application/pdf');
  assert.match(res.headers.get('Content-Disposition'),/^inline; filename="____\.pdf"; filename\*=UTF-8''%EB%93%B1/);
  assert.match(res.headers.get('Cache-Control'),/public, max-age=3600/);
  assert.equal(res.headers.get('X-Content-Type-Options'),'nosniff');assert.ok(res.headers.get('ETag'));
  assert.deepEqual(Buffer.from(await res.arrayBuffer()),pdf());
  const again=await call(pub.file,'GET',null,null,new Request('https://x.test'+pub.file,{headers:{'If-None-Match':res.headers.get('ETag')}}));
  assert.equal(again.status,304);
  await fails(call(hid.file,'GET',null,null),'not_found',404);
  await fails(call(hid.file,'GET',null,member),'not_found',404);
  const own=await call(hid.file,'GET',null,admin);assert.equal(own.status,200);assert.match(own.headers.get('Cache-Control'),/no-store/);
  await fails(call('/api/learn/handouts/999/file','GET',null,null),'not_found',404);
  R2.store.clear();
  await fails(call(pub.file,'GET',null,null),'file_missing',404);
});

test('administrators edit, hide and delete; delete removes the R2 object',async()=>{
  const {call,R2,db}=setup();
  const h=(await call('/api/learn/handouts','POST',json(),admin)).handout;
  await fails(call(`/api/learn/handouts/${h.id}`,'PATCH',{status:'hidden'},member),'forbidden',403);
  const e=(await call(`/api/learn/handouts/${h.id}`,'PATCH',{title_en:'Kinematics, four equations',status:'hidden',level:null,unit:'mechanics/kinematics'},admin)).handout;
  assert.equal(e.title_en,'Kinematics, four equations');assert.equal(e.status,'hidden');assert.equal(e.level,null);
  await fails(call(`/api/learn/handouts/${h.id}`,'PATCH',{status:'gone'},admin),'bad_status');
  await fails(call(`/api/learn/handouts/${h.id}`,'PATCH',{},admin),'nothing_to_change');
  await fails(call(`/api/learn/handouts/${h.id}`,'PATCH',{title_ko:'',title_en:''},admin),'bad_title');
  assert.equal(db.prepare('SELECT title_ko FROM handouts WHERE id=?').get(h.id).title_ko,'등가속도 운동 정리','a refused edit changes nothing');
  await fails(call('/api/learn/handouts/999','PATCH',{status:'public'},admin),'not_found',404);
  await fails(call(`/api/learn/handouts/${h.id}`,'DELETE',null,member),'forbidden',403);
  assert.equal(R2.store.size,1);
  assert.deepEqual(await call(`/api/learn/handouts/${h.id}`,'DELETE',null,admin),{ok:true});
  assert.equal(R2.store.size,0);assert.equal(db.prepare('SELECT COUNT(*) n FROM handouts').get().n,0);
  await fails(call(`/api/learn/handouts/${h.id}`,'DELETE',null,admin),'not_found',404);
});

test('other paths are left to the other routers, and the Worker wires the handouts router before the Learn router',async()=>{
  const {call}=setup();
  assert.equal(await call('/api/learn/plan','GET',null,null),undefined);
  assert.equal(await call('/api/learn/handoutsx','GET',null,null),undefined);
  const src=readFileSync(new URL('./src/index.js',import.meta.url),'utf8');
  assert.match(src,/import \{ createHandoutRouter \} from '\.\/handouts\.js'/);
  assert.ok(src.indexOf('await handoutRouter(')>0&&src.indexOf('await handoutRouter(')<src.indexOf('await learnRouter('));
  const yml=readFileSync(new URL('../.github/workflows/deploy-worker.yml',import.meta.url),'utf8');
  assert.match(yml,/test-handouts\.mjs/,'the deploy runs this test');
  assert.doesNotMatch(readFileSync(new URL('./src/handouts.js',import.meta.url),'utf8'),/env\.(?!DB\b|LAB_PAGES\b)[A-Z_]+/,'no binding or variable other than DB and LAB_PAGES');
});
