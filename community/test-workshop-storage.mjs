import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {ensureLearnSchema} from './src/learn-services.js';
import {createWorkshopStorageRouter, workshopForgetUser, cleanFolder, cleanName, contentMatches, WORKSHOP_MAX_FILE, WORKSHOP_QUOTA, WORKSHOP_KINDS} from './src/workshop-storage.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
function fakeR2(){
  const store=new Map();
  return {store,
    async put(key,bytes,opts){store.set(key,{bytes:new Uint8Array(bytes),opts});},
    async get(key){const o=store.get(key);if(!o)return null;return{size:o.bytes.length,body:new Blob([o.bytes]).stream()};},
    async delete(key){for(const k of [].concat(key))store.delete(k);}};
}
function setup({r2=true}={}){
  const db=new DatabaseSync(':memory:');
  const D1={prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{changes:r.changes}};}};}};
  const limits=[];let t=1_800_000_000;
  const route=createWorkshopStorageRouter({HttpError:H,bad,now:()=>t,needUser:u=>{if(!u)throw new H(401,'login_required');return u;},limit:async(env,key,max,win)=>{limits.push([key,max,win]);}});
  const R2=r2?fakeR2():null,env={DB:D1,...(R2?{LAB_PAGES:R2}:{})};
  const call=(p,m,body,me,req)=>route(p,m,body,me,req||new Request('https://x.test'+p,{method:m==='HEAD'?'GET':m}),env);
  const upload=(me,name,bytes,folder='',extra={})=>{const form=new FormData();form.set('file',new File([bytes],name));form.set('folder',folder);for(const [k,v] of Object.entries(extra))form.set(k,v);
    return route('/api/workshop/storage/files','POST',{},me,new Request('https://x.test/api/workshop/storage/files',{method:'POST',body:form}),env);};
  /* PUT …/content: a multipart file (with kind, base) or the raw bytes (?kind, ?base) */
  const replace=(me,id,bytes,{name,raw=false,kind,base}={})=>{
    const path=`/api/workshop/storage/files/${id}/content`;
    if(raw){const q=new URLSearchParams({...(kind?{kind}:{}),...(base!=null?{base:String(base)}:{})});return route(path,'PUT',{},me,new Request('https://x.test'+path+(q.size?'?'+q:''),{method:'PUT',body:bytes}),env);}
    const form=new FormData();form.set('file',new File([bytes],name||'x'));if(kind)form.set('kind',kind);if(base!=null)form.set('base',String(base));
    return route(path,'PUT',{},me,new Request('https://x.test'+path,{method:'PUT',body:form}),env);};
  return {db,R2,env,limits,call,upload,replace,route,tick:s=>{t+=s;}};
}
const alice={id:7},bob={id:8};

test('class storage checks membership on each read and withholds worksheet solutions', async () => {
  const {db, env, call, upload} = setup();
  await ensureLearnSchema(env);
  db.exec(`CREATE TABLE users (id INTEGER PRIMARY KEY, deleted INTEGER NOT NULL);
    INSERT INTO users VALUES (7,0), (8,0), (9,0);
    INSERT INTO classes VALUES (1,7,'Physics club','ABCDEF',0,NULL);
    INSERT INTO class_members VALUES (1,8,0);`);
  const outside = {id: 9};
  const prefix = '/api/workshop/storage/shared';
  const worksheet = {format:'haslalab-paper', paper:{title:'Pendulum', items:[{pts:2, own:{
    q:'What is the period?', choices:['1', '2'], correct:1, answer:'SECRET', sol:'SECRET', rubric:[{desc:'SECRET'}]
  }}]}};
  const mime = {kind:'paper', ensure_folder:'1'};
  const {file} = await upload(alice, 'paper.json', JSON.stringify(worksheet), 'Club', mime);
  const input = {kind:'assignment',class_id:1,title:'Pendulum',folder:'Club',due_at:1_800_001_000};
  await fails(call(prefix,'POST',input,bob),'forbidden',403);
  await fails(call(prefix,'POST',{...input,kind:'resource',due_at:null},outside),'forbidden',403);
  const {id} = await call(prefix,'POST',input,alice);
  const {file: later} = await upload(alice, 'later.json', JSON.stringify(worksheet), 'Club', mime);
  assert.equal((await call(prefix,'GET',null,outside)).shares.length,0);
  assert.equal((await call(prefix,'GET',null,bob)).shares[0].file_count,1);
  const list = await call(prefix+'/'+id,'GET',null,bob);
  assert.deepEqual(list.files.map(f=>f.id), [file.id]);
  assert.ok(!('folder' in list.files[0]));
  const url = prefix+'/'+id+'/files/'+file.id;
  const res = await call(url,'GET',null,bob);
  assert.match(res.headers.get('content-disposition'), /^attachment/);
  const student = await res.text();
  assert.doesNotMatch(student, /SECRET|correct|answer|rubric/);
  assert.match(student, /What is the period/);
  await fails(call(prefix+'/'+id+'/files/'+later.id,'GET',null,bob),'not_found',404);
  const {file: material} = await upload(bob,'readme.txt','club notes');
  const resource = await call(prefix,'POST',{kind:'resource',class_id:1,title:'Club notes',file_id:material.id},bob);
  assert.equal(await (await call(prefix+'/'+resource.id+'/files/'+material.id,'GET',null,alice)).text(), 'club notes');
  db.exec('DELETE FROM class_members WHERE class_id=1 AND user_id=8');
  await fails(call(url,'GET',null,bob),'not_found',404);
  await fails(call(prefix+'/'+resource.id,'GET',null,alice),'not_found',404);
  assert.deepEqual(await call(prefix+'/'+id,'DELETE',null,alice),{ok:true});
  await fails(call(url,'GET',null,alice),'not_found',404);
});
const pdf=(n=100)=>Buffer.concat([Buffer.from('%PDF-1.7\n'),Buffer.alloc(n,0x20),Buffer.from('\n%%EOF\n')]);
const png=()=>Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a,0,0,0,13]);
const zip=()=>Buffer.from([0x50,0x4b,0x03,0x04,20,0,0,0]);
const fails=async(p,code,status)=>assert.rejects(p,e=>e.code===code&&(status==null||e.status===status));

test('every route needs a signed-in member',async()=>{
  const {call,upload}=setup();
  await fails(call('/api/workshop/storage','GET',null,null),'login_required',401);
  await fails(upload(null,'a.pdf',pdf()),'login_required',401);
  await fails(call('/api/workshop/storage/files/'+'a'.repeat(32),'GET',null,null),'login_required',401);
  assert.equal(await call('/api/workshopx','GET',null,alice),undefined,'other paths are left to other routers');
});

test('an upload goes to R2 under workshop/<user>/<id>, never under a name the member typed',async()=>{
  const {upload,call,R2,db,limits}=setup();
  const {file:f,used,quota}=await upload(alice,'../../시험지 1.pdf',pdf());
  assert.match(f.id,/^[0-9a-f]{32}$/);assert.equal(f.name,'시험지 1.pdf','the path is dropped from the name');
  assert.equal(f.folder,'');assert.equal(f.mime,'application/pdf');assert.equal(f.size,pdf().length);assert.ok(!('r2_key' in f));
  assert.equal(used,pdf().length);assert.equal(quota,WORKSHOP_QUOTA);
  const row=db.prepare('SELECT * FROM workshop_files WHERE id=?').get(f.id);
  assert.equal(row.r2_key,`workshop/7/${f.id}`);assert.equal(row.owner_id,7);
  assert.equal(R2.store.get(row.r2_key).opts.httpMetadata.contentType,'application/pdf');
  assert.ok(limits.some(([k])=>k==='ws-up:7'),'uploads are rate limited');
  const list=await call('/api/workshop/storage','GET',null,alice);
  assert.deepEqual(list.files.map(x=>x.name),['시험지 1.pdf']);assert.equal(list.used,pdf().length);
  assert.equal(list.max_file,WORKSHOP_MAX_FILE);assert.ok(list.types.includes('hwpx')&&list.types.includes('svg'));
  assert.equal((await call('/api/workshop/storage','GET',null,bob)).files.length,0,'another member sees nothing');
  const again=await upload(alice,'시험지 1.pdf',pdf());assert.equal(again.file.name,'시험지 1 (2).pdf','a taken name gets a number');
});

test('only the listed types, whose first bytes match the extension, and at most 20 MB',async()=>{
  const {upload,R2}=setup();
  await fails(upload(alice,'run.exe',Buffer.from('MZ')),'type_not_allowed',415);
  await fails(upload(alice,'page.html',Buffer.from('<html>')),'type_not_allowed',415);
  await fails(upload(alice,'fake.png',Buffer.from('<html><script>alert(1)</script>')),'type_mismatch',415);
  await fails(upload(alice,'fake.pdf',png()),'type_mismatch',415);
  await fails(upload(alice,'bin.txt',Buffer.from([0xff,0xfe,0x00,0x41])),'type_mismatch',415);
  await fails(upload(alice,'empty.pdf',Buffer.alloc(0)),'file_required');
  await fails(upload(alice,'big.pdf',Buffer.concat([pdf(0),Buffer.alloc(WORKSHOP_MAX_FILE)])),'file_too_large',413);
  assert.equal(R2.store.size,0,'nothing reached R2');
  for(const [name,bytes] of [['a.png',png()],['b.docx',zip()],['c.hwpx',zip()],['d.csv',Buffer.from('t,x\n0,1\n')],['e.md',Buffer.from('# 실험')],['f.json',Buffer.from('{"a":1}')],
    ['g.svg',Buffer.from('<svg xmlns="http://www.w3.org/2000/svg"></svg>')],['h.jpg',Buffer.from([0xff,0xd8,0xff,0xe0])],['i.webp',Buffer.from('RIFF\0\0\0\0WEBPVP8 ')]])
    assert.ok((await upload(alice,name,bytes)).file.id,name);
  assert.ok(!contentMatches('svg',Buffer.from('<html></html>')));assert.ok(!contentMatches('exe',Buffer.from('MZ')));
});

test('the quota counts every file of the member and is checked in the insert too',async()=>{
  const {upload,R2,db}=setup();
  db.exec(`CREATE TABLE IF NOT EXISTS workshop_files (id TEXT PRIMARY KEY, owner_id INTEGER NOT NULL, folder TEXT NOT NULL DEFAULT '', name TEXT NOT NULL, size INTEGER NOT NULL, mime TEXT NOT NULL, r2_key TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)`);
  db.prepare("INSERT INTO workshop_files VALUES('x',7,'','old.pdf',?, 'application/pdf','workshop/7/x',0,0)").run(WORKSHOP_QUOTA-50);
  await fails(upload(alice,'over.pdf',pdf()),'quota_exceeded',413);
  assert.equal(R2.store.size,0);
  assert.ok((await upload(bob,'mine.pdf',pdf())).file,'another member has their own quota');
});

test('folders: made with their parents, files moved in, renamed with everything inside, deleted only when empty',async()=>{
  const {call,upload,db}=setup();
  await fails(upload(alice,'a.pdf',pdf(),'수업/1학기'),'folder_not_found',404);
  assert.deepEqual(await call('/api/workshop/storage/folders','POST',{path:' 수업 / 1학기 '},alice),{path:'수업/1학기'});
  assert.deepEqual((await call('/api/workshop/storage','GET',null,alice)).folders,['수업','수업/1학기']);
  for(const path of ['../x','a/../../b','a\\b','.', 'x'.repeat(61),'a/b/c/d/e/f',42])await fails(call('/api/workshop/storage/folders','POST',{path},alice),'bad_folder');
  const f=(await upload(alice,'a.pdf',pdf(),'수업/1학기')).file;assert.equal(f.folder,'수업/1학기');
  await fails(call('/api/workshop/storage/folders','DELETE',null,alice,new Request('https://x.test/api/workshop/storage/folders?path='+encodeURIComponent('수업'),{method:'DELETE'})),'folder_not_empty',409);
  await fails(call('/api/workshop/storage/folders','PATCH',{path:'수업',to:'수업/안'},alice),'folder_into_itself');
  assert.deepEqual(await call('/api/workshop/storage/folders','PATCH',{path:'수업',to:'2026/수업'},alice),{path:'2026/수업'});
  assert.deepEqual((await call('/api/workshop/storage','GET',null,alice)).folders,['2026','2026/수업','2026/수업/1학기']);
  assert.equal(db.prepare('SELECT folder FROM workshop_files WHERE id=?').get(f.id).folder,'2026/수업/1학기');
  assert.equal(db.prepare('SELECT r2_key FROM workshop_files WHERE id=?').get(f.id).r2_key,`workshop/7/${f.id}`,'a move never touches R2');
  await call(`/api/workshop/storage/files/${f.id}`,'PATCH',{folder:''},alice);
  const del=p=>call('/api/workshop/storage/folders','DELETE',null,alice,new Request('https://x.test/api/workshop/storage/folders?path='+encodeURIComponent(p),{method:'DELETE'}));
  await fails(del('2026'),'folder_not_empty',409);
  assert.deepEqual(await del('2026/수업/1학기'),{ok:true});
  await fails(del('없는 폴더'),'folder_not_found',404);
  await fails(call('/api/workshop/storage/folders','PATCH',{path:'2026',to:'x'},bob),'folder_not_found',404,'another member cannot touch the folder');
});

test('download: owner only, always an attachment, nosniff; an SVG is never served inline',async()=>{
  const {call,upload,R2}=setup();
  const f=(await upload(alice,'그림.svg',Buffer.from('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'))).file;
  const res=await call(`/api/workshop/storage/files/${f.id}`,'GET',null,alice);
  assert.ok(res instanceof Response);assert.equal(res.status,200);
  assert.match(res.headers.get('Content-Disposition'),/^attachment; filename="__\.svg"; filename\*=UTF-8''%EA%B7%B8/);
  assert.equal(res.headers.get('X-Content-Type-Options'),'nosniff');
  assert.match(res.headers.get('Content-Security-Policy'),/sandbox/);assert.match(res.headers.get('Cache-Control'),/no-store/);
  assert.match(await res.text(),/<svg/);
  await fails(call(`/api/workshop/storage/files/${f.id}`,'GET',null,bob),'not_found',404);
  await fails(call('/api/workshop/storage/files/..%2F..%2Fhandouts','GET',null,alice),'not_found',404);
  await fails(call('/api/workshop/storage/files/'+'0'.repeat(32),'GET',null,alice),'not_found',404);
  R2.store.clear();
  await fails(call(`/api/workshop/storage/files/${f.id}`,'GET',null,alice),'file_missing',404);
});

test('rename keeps the extension, refuses a taken name; another member can neither rename nor delete',async()=>{
  const {call,upload,R2,db}=setup();
  const a=(await upload(alice,'a.pdf',pdf())).file,b=(await upload(alice,'b.pdf',pdf())).file;
  assert.equal((await call(`/api/workshop/storage/files/${a.id}`,'PATCH',{name:'중간고사.exe'},alice)).file.name,'중간고사.exe.pdf');
  assert.equal((await call(`/api/workshop/storage/files/${a.id}`,'PATCH',{name:'기말 "최종"'},alice)).file.name,'기말 최종.pdf');
  await fails(call(`/api/workshop/storage/files/${a.id}`,'PATCH',{name:'b.pdf'},alice),'name_taken',409);
  await fails(call(`/api/workshop/storage/files/${a.id}`,'PATCH',{name:'  '},alice),'bad_name');
  await fails(call(`/api/workshop/storage/files/${a.id}`,'PATCH',{},alice),'nothing_to_change');
  await fails(call(`/api/workshop/storage/files/${a.id}`,'PATCH',{folder:'없음'},alice),'folder_not_found',404);
  await fails(call(`/api/workshop/storage/files/${a.id}`,'PATCH',{name:'x.pdf'},bob),'not_found',404);
  await fails(call(`/api/workshop/storage/files/${a.id}`,'DELETE',null,bob),'not_found',404);
  assert.equal(R2.store.size,2);
  assert.deepEqual(await call(`/api/workshop/storage/files/${a.id}`,'DELETE',null,alice),{ok:true});
  assert.equal(R2.store.size,1);assert.equal(db.prepare('SELECT COUNT(*) n FROM workshop_files').get().n,1);
  await fails(call(`/api/workshop/storage/files/${a.id}`,'DELETE',null,alice),'not_found',404);
  assert.ok(b.id);
});

test('without the R2 binding nothing is stored; deleting the account removes every file',async()=>{
  const none=setup({r2:false});
  await fails(none.upload(alice,'a.pdf',pdf()),'r2_unavailable',503);
  const {upload,env,R2,db}=setup();
  await upload(alice,'a.pdf',pdf());await upload(alice,'b.png',png());await upload(bob,'c.pdf',pdf());
  assert.equal(await workshopForgetUser(env,7),2);
  assert.deepEqual([...R2.store.keys()].map(k=>k.split('/')[1]),['8']);
  assert.equal(db.prepare('SELECT COUNT(*) n FROM workshop_files WHERE owner_id=7').get().n,0);
});

test('apps save in place: PUT …/content keeps the id, name and folder, checks the type, and frees the old object',async()=>{
  const {upload,replace,call,R2,db,tick}=setup();
  const json=o=>Buffer.from(JSON.stringify(o));
  const f=(await upload(alice,'중간고사.json',json({v:1}),'시험지',{kind:'paper',ensure_folder:'1'})).file;
  assert.equal(f.kind,'paper');assert.equal(f.folder,'시험지','ensure_folder made the folder');
  assert.deepEqual((await call('/api/workshop/storage','GET',null,alice)).folders,['시험지']);
  const key0=db.prepare('SELECT r2_key FROM workshop_files WHERE id=?').get(f.id).r2_key;
  tick(5);
  const r=await replace(alice,f.id,json({v:2,items:[1,2,3]}),{name:'아무 이름.json'});
  assert.equal(r.file.id,f.id);assert.equal(r.file.name,'중간고사.json');assert.equal(r.file.folder,'시험지');assert.equal(r.file.kind,'paper');
  assert.equal(r.file.size,json({v:2,items:[1,2,3]}).length);assert.ok(r.file.updated_at>f.updated_at);assert.equal(r.used,r.file.size);
  const key1=db.prepare('SELECT r2_key FROM workshop_files WHERE id=?').get(f.id).r2_key;
  assert.notEqual(key1,key0);assert.match(key1,new RegExp(`^workshop/7/${f.id}-[0-9a-f]{12}$`));
  assert.ok(!R2.store.has(key0),'the old object is gone');assert.equal(R2.store.size,1);
  assert.deepEqual(JSON.parse(await (await call(`/api/workshop/storage/files/${f.id}`,'GET',null,alice)).text()),{v:2,items:[1,2,3]});
  /* the raw body works too, with ?kind */
  const raw=await replace(alice,f.id,json({v:3}),{raw:true,kind:'problem'});assert.equal(raw.file.kind,'problem');
  /* base: a save over a version the page did not see is refused */
  await fails(replace(alice,f.id,json({v:4}),{base:f.updated_at}),'changed',409);
  assert.ok((await replace(alice,f.id,json({v:4}),{base:raw.file.updated_at})).file);
  /* the file's own type only */
  await fails(replace(alice,f.id,Buffer.from([0xff,0xfe,0,0x41])),'type_mismatch',415);
  await fails(replace(alice,f.id,pdf(),{name:'a.pdf'}),'type_change',415);
  await fails(replace(alice,f.id,Buffer.alloc(0)),'file_required');
  await fails(replace(alice,f.id,json({v:1}),{kind:'virus'}),'bad_kind');
  await fails(replace(bob,f.id,json({hack:1})),'not_found',404);
  await fails(replace(alice,'0'.repeat(32),json({v:1})),'not_found',404);
  await fails(call(`/api/workshop/storage/files/${f.id}/content`,'POST',{},alice),'method_not_allowed',405);
  assert.equal(R2.store.size,1,'refused saves leave nothing behind');
});

test('a replacement counts only the size difference against the quota, in the update itself',async()=>{
  const {upload,replace,R2,db}=setup();
  const f=(await upload(alice,'a.txt',Buffer.from('x'.repeat(100)))).file;
  db.prepare("INSERT INTO workshop_files(id,owner_id,folder,name,size,mime,r2_key,created_at,updated_at) VALUES('y',7,'','big.pdf',?,'application/pdf','workshop/7/y',0,0)").run(WORKSHOP_QUOTA-150);
  assert.ok((await replace(alice,f.id,Buffer.from('y'.repeat(140)))).file,'40 more bytes fit');
  await fails(replace(alice,f.id,Buffer.from('z'.repeat(200))),'quota_exceeded',413);
  assert.equal(db.prepare('SELECT size FROM workshop_files WHERE id=?').get(f.id).size,140,'the file is unchanged');
  assert.equal(R2.store.size,1);
});

test('kinds: tagged at upload or later, listed by kind and folder (newest first)',async()=>{
  const {upload,call,tick}=setup();
  assert.deepEqual(WORKSHOP_KINDS,['file','paper','problem','figure','sim']);
  await fails(upload(alice,'a.json',Buffer.from('{}'),'',{kind:'exe'}),'bad_kind');
  const a=(await upload(alice,'a.json',Buffer.from('{}'),'그림',{kind:'figure',ensure_folder:'1'})).file;tick(3);
  const b=(await upload(alice,'b.svg',Buffer.from('<svg xmlns="http://www.w3.org/2000/svg"></svg>'),'그림',{kind:'figure'})).file;
  await upload(alice,'c.pdf',pdf());
  const q=(qs,me=alice)=>call('/api/workshop/storage','GET',null,me,new Request('https://x.test/api/workshop/storage?'+qs));
  assert.deepEqual((await q('kind=figure')).files.map(f=>f.name),['b.svg','a.json']);
  assert.deepEqual((await q('kind=file')).files.map(f=>f.name),['c.pdf']);
  assert.deepEqual((await q('folder='+encodeURIComponent('그림'))).files.map(f=>f.id),[b.id,a.id]);
  assert.equal((await q('kind=figure',bob)).files.length,0);
  await fails(q('kind=nope'),'bad_kind');
  assert.equal((await call(`/api/workshop/storage/files/${a.id}`,'PATCH',{kind:'sim'},alice)).file.kind,'sim');
  await fails(call(`/api/workshop/storage/files/${a.id}`,'PATCH',{kind:'x'},alice),'bad_kind');
  assert.equal((await call('/api/workshop/storage','GET',null,alice)).files.find(f=>f.id===a.id).kind,'sim');
});

test('names and folders are cleaned the same way everywhere',()=>{
  assert.equal(cleanName('a/b\\c.pdf','pdf'),'c.pdf');assert.equal(cleanName('','pdf'),'file.pdf');assert.equal(cleanName('.pdf','pdf'),'file.pdf');
  assert.equal(cleanName('x'.repeat(300)+'.pdf','pdf').length,120);
  assert.equal(cleanFolder(''),'');assert.equal(cleanFolder('/a//b/'),'a/b');assert.equal(cleanFolder('a/../b'),null);
});

test('the Worker wires the router, forgets the files on account deletion, and the deploy runs this test',()=>{
  const src=readFileSync(new URL('./src/index.js',import.meta.url),'utf8');
  assert.match(src,/import \{ createWorkshopStorageRouter, workshopForgetUser \} from '\.\/workshop-storage\.js'/);
  assert.ok(src.indexOf('await workshopStorageRouter(')>0);
  assert.ok(src.indexOf('await workshopForgetUser(env, me.id)')>0);
  const yml=readFileSync(new URL('../.github/workflows/deploy-worker.yml',import.meta.url),'utf8');
  assert.match(yml,/test-workshop-storage\.mjs/);
  assert.doesNotMatch(readFileSync(new URL('./src/workshop-storage.js',import.meta.url),'utf8'),/env\.(?!DB\b|LAB_PAGES\b)[A-Z_]+/,'no binding or variable other than DB and LAB_PAGES');
});
