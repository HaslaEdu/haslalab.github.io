import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createGalleryRouter, galleryBoard, activeGallery, GALLERY_BOARD} from './src/galleries.js';
import {readPublicPosts} from './src/public-data.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
const text=(v,max,code)=>{if(typeof v!=='string')bad(code);v=v.trim();if(!v||v.length>max)bad(code);return v;};
function setup(){
  const db=new DatabaseSync(':memory:');
  db.exec(`CREATE TABLE users(id INTEGER PRIMARY KEY,nickname TEXT,avatar TEXT,deleted INTEGER DEFAULT 0);
    CREATE TABLE posts(id INTEGER PRIMARY KEY,board TEXT NOT NULL,tag TEXT,lang TEXT,user_id INTEGER,title TEXT,body TEXT,created_at INTEGER,updated_at INTEGER,views INTEGER DEFAULT 0,n_comments INTEGER DEFAULT 0,n_likes INTEGER DEFAULT 0,n_dislikes INTEGER DEFAULT 0);
    INSERT INTO users(id,nickname) VALUES(1,'kim'),(2,'lee'),(3,'admin');`);
  const D1={async batch(s){const out=[];for(const x of s)out.push(await x.all());return out;},prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{last_row_id:Number(r.lastInsertRowid)}};}};}};
  let t=1000;const limits=new Map();
  const route=createGalleryRouter({HttpError:H,needUser:u=>{if(!u)throw new H(401,'login_required');return u;},bad,text,now:()=>++t,
    limit:async(env,key,max)=>{const n=(limits.get(key)||0)+1;limits.set(key,n);if(n>max)throw new H(429,'rate_limited');}});
  return {db,env:{DB:D1},route};
}
const kim={id:1,role:'user'},lee={id:2,role:'user'},admin={id:3,role:'admin'};
const fails=async(promise,code)=>{await assert.rejects(promise,e=>e.code===code);};

test('addresses are short lower-case slugs and never shadow the main gallery or site routes',()=>{
  assert.equal(galleryBoard('Physics-Olympiad'),'g-physics-olympiad');
  for(const bad of ['ab','-abc','abc-','free','qna','admin','new','a b c','한글갤','x'.repeat(25)])assert.equal(galleryBoard(bad),null,bad);
  assert.ok(GALLERY_BOARD.test('g-kpho2027'));assert.ok(!GALLERY_BOARD.test('free'));
});

test('a member opens a gallery; names are unique; the list shows it with its post count',async()=>{
  const {env,route,db}=setup();
  await fails(route('/api/galleries','POST',{address:'kpho',name:'KPhO 갤러리'},null,env),'login_required');
  const made=await route('/api/galleries','POST',{address:'KPhO',name:'KPhO 갤러리',intro:'한국물리올림피아드 준비'},kim,env);
  assert.deepEqual(made,{board:'g-kpho',name:'KPhO 갤러리',intro:'한국물리올림피아드 준비'});
  await fails(route('/api/galleries','POST',{address:'kpho',name:'다른 이름'},lee,env),'gallery_taken');
  await fails(route('/api/galleries','POST',{address:'kpho2',name:'kpho 갤러리'},lee,env),'gallery_taken');
  db.prepare("INSERT INTO posts(board,tag,lang,user_id,title,body,created_at) VALUES('g-kpho','gen','ko',2,'첫 글','내용',5)").run();
  const list=await route('/api/galleries','GET',{},null,env);
  assert.equal(list.galleries.length,1);assert.equal(list.galleries[0].n,1);assert.equal(list.galleries[0].owner,'kim');
  assert.equal((await activeGallery(env,'g-kpho')).name,'KPhO 갤러리');assert.equal(await activeGallery(env,'free'),null);
});

test('a member may open at most three galleries and two a day',async()=>{
  const {env,route}=setup();
  await route('/api/galleries','POST',{address:'aaa',name:'A갤'},kim,env);
  await route('/api/galleries','POST',{address:'bbb',name:'B갤'},kim,env);
  await fails(route('/api/galleries','POST',{address:'ccc',name:'C갤'},kim,env),'rate_limited');
});

test('only the opener or an administrator edits or closes a gallery; a closed gallery leaves the list',async()=>{
  const {env,route}=setup();
  await route('/api/galleries','POST',{address:'optics',name:'광학갤'},kim,env);
  await fails(route('/api/galleries/g-optics','PATCH',{intro:'x'},lee,env),'forbidden');
  assert.equal((await route('/api/galleries/g-optics','PATCH',{intro:'빛과 렌즈'},kim,env)).intro,'빛과 렌즈');
  assert.deepEqual(await route('/api/galleries/g-optics','DELETE',{},admin,env),{ok:true});
  assert.equal((await route('/api/galleries','GET',{},null,env)).galleries.length,0);
  assert.equal(await activeGallery(env,'g-optics'),null);
  await fails(route('/api/galleries/g-optics','GET',{},null,env),'not_found');
});

test('public post lists accept a gallery board and still refuse other unknown boards',async()=>{
  const {env,db}=setup();
  db.prepare("INSERT INTO posts(board,tag,lang,user_id,title,body,created_at) VALUES('g-kpho','gen','ko',1,'갤 글','본문',5),('free','gen','ko',1,'자유 글','본문',6)").run();
  const url=board=>new URL('https://x/api/posts?lang=ko&board='+board);
  const r=await readPublicPosts(env.DB,url('g-kpho'));
  assert.deepEqual(r.posts.map(p=>p.title),['갤 글']);
  await assert.rejects(readPublicPosts(env.DB,url('secret')),e=>e.code==='bad_board'||/bad_board/.test(e.message));
});
