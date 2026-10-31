// Real SQLite, the existing Worker binding and no production service access.
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import test from 'node:test';
import worker from './src/index.js';
import { ensureNoticePins, missingNoticePins, NOTICE_PINS_SCHEMA } from './src/notice-pins.js';
import { readPublicPosts } from './src/public-data.js';
import { selectOnly } from './src/public-consistency.js';

function fixture() {
  const sql = new DatabaseSync(':memory:'), queries = [];
  const migrations = new URL('./migrations/', import.meta.url);
  // Deliberately omit the new migration: deployed databases bootstrap lazily.
  for (const name of readdirSync(migrations).filter(n => /^00(?:0[1-9]|1[0-3])_.*\.sql$/.test(n)).sort()) sql.exec(readFileSync(new URL(name, migrations), 'utf8'));
  const DB = {
    prepare(query) {
      queries.push(query);
      const statement = sql.prepare(query), make = args => ({
        bind: (...values) => make(values),
        async first() { return statement.get(...args) || null; },
        async all() { return { results: statement.all(...args).map(row => ({ ...row })) }; },
        async run() { const result = statement.run(...args); return { success: true, meta: { changes: result.changes, last_row_id: Number(result.lastInsertRowid) } }; },
        execute() { return statement.columns().length ? this.all() : this.run(); },
      });
      return make([]);
    },
    async batch(statements) {
      sql.exec('BEGIN');
      try { const result = []; for (const statement of statements) result.push(await statement.execute()); sql.exec('COMMIT'); return result; }
      catch (error) { sql.exec('ROLLBACK'); throw error; }
    },
  };
  const at = Math.floor(Date.now()/1000);
  for (const [id, role] of [[1,'admin'],[2,'user']]) sql.prepare('INSERT INTO users(id,username,nickname,pw,role,created_at) VALUES(?,?,?,?,?,?)').run(id,'private'+id,'Public '+id,'privateHash',role,at);
  for(let id=1;id<=24;id++)sql.prepare("INSERT INTO posts(id,user_id,board,tag,lang,title,body,created_at) VALUES(?,1,?,'notice','ko',?,?,?)").run(id,id%2?'qna':'free','Notice '+id,'Full public notice body '+id+'\n'.repeat(180),at-id);
  sql.prepare("INSERT INTO posts(id,user_id,board,tag,lang,title,body,created_at) VALUES(25,1,'free','notice','en','English notice','English body',?)").run(at);
  sql.prepare("INSERT INTO posts(id,user_id,board,tag,lang,title,body,created_at) VALUES(26,2,'free','gen','ko','Regular post','Regular body',?)").run(at);
  const tokens = {admin:'a'.repeat(48),user:'u'.repeat(48)};
  for(const [role, token] of Object.entries(tokens)) {
    const hash = createHash('sha256').update(token).digest('base64url');
    sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(hash,role==='admin'?1:2,at,at+3600);
  }
  const env = { DB, ALLOWED_ORIGINS:'https://haslalab.org' };
  globalThis.caches = {default:{async match(){return null;},async put(){}}};
  return {sql,DB,queries,async request(path,method='GET',body,role){
    const response=await worker.fetch(new Request('https://worker.local/api'+path,{method,headers:{'Cache-Control':'no-cache',...(role?{Authorization:'Bearer '+tokens[role]}:{}),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})}),env);
    return {status:response.status,data:await response.json()};
  }};
}

test('old databases serve complete paginated notice bodies through SELECT-only readers before any pin',async()=>{
  const h=fixture(),reader=selectOnly(h.DB),read=path=>readPublicPosts(reader,new URL('https://local/api'+path));
  const first=await read('/posts?notices=1&lang=ko');assert.equal(first.total,24);assert.equal(first.posts.length,20);assert.deepEqual(first.notices,[]);
  assert.ok(first.posts[0].body.length>160);assert.ok(first.posts.every(p=>p.tag==='notice'&&p.pinned===0));
  assert.deepEqual((await read('/posts?notices=1&lang=ko&page=2')).posts.map(p=>p.id),[4,3,2,1]);
  assert.deepEqual((await read('/posts?notices=1&lang=en')).posts.map(p=>p.id),[25]);
  assert.equal((await read('/posts?lang=ko')).posts[0].id,26);
  assert.ok(h.queries.every(query=>/^SELECT\b/.test(query)));
  assert.equal(h.sql.prepare("SELECT COUNT(*) n FROM sqlite_master WHERE name='notice_pins'").get().n,0);
  assert.doesNotMatch(JSON.stringify(first),/privateHash|private1|user_id|token_hash/);
  h.sql.close();
});

test('admins can publish Korean and English notices that immediately appear in the matching public mailbox and board summary',async()=>{
  const h=fixture();
  try{
    const publish=async(lang,title,body)=>{
      const result=await h.request('/posts','POST',{board:'free',tag:'notice',lang,title,body},'admin');
      assert.equal(result.status,200,JSON.stringify(result.data));
      assert.ok(Number.isSafeInteger(result.data.id));return result.data.id;
    };
    const ko=await publish('ko','New administrator announcement','Full Korean announcement\n'+'Public detail '.repeat(30));
    const en=await publish('en','New English announcement','Full English announcement');
    assert.equal(h.sql.prepare('SELECT tag FROM posts WHERE id=?').get(ko).tag,'notice');
    const korean=(await h.request('/posts?notices=1&lang=ko')).data;
    assert.equal(korean.posts[0].id,ko);assert.equal(korean.total,25);assert.equal(korean.posts[0].body.length>160,true);
    assert.equal(korean.posts.some(post=>post.id===en),false);
    const english=(await h.request('/posts?notices=1&lang=en')).data;
    assert.equal(english.posts[0].id,en);assert.equal(english.total,2);assert.equal(english.posts.some(post=>post.id===ko),false);
    assert.equal((await h.request('/posts?board=qna&lang=ko')).data.notices[0].id,ko,'a free-board announcement reaches other boards too');
    const summary=(await h.request('/posts?lang=ko')).data;
    assert.equal(summary.notices[0].id,ko);assert.equal(summary.posts.some(post=>post.id===ko),false,'notices stay in their dedicated summary');
    const publicDetail=await h.request('/posts/'+ko);
    assert.equal(publicDetail.status,200);assert.equal(!!publicDetail.data.post.mine,false);assert.equal(publicDetail.data.post.tag,'notice');
    assert.equal((await h.request('/posts/'+ko,'GET',undefined,'admin')).data.post.mine,true);
  }finally{h.sql.close();}
});

test('anonymous and ordinary users cannot publish, promote, edit or pin administrator announcements by forging request fields',async()=>{
  const h=fixture();
  try{
    const payload={board:'free',tag:'notice',lang:'ko',title:'Forged notice',body:'Public text',role:'admin',user_id:1,pinned:true};
    const before=h.sql.prepare('SELECT COUNT(*) n FROM posts').get().n;
    const anonymous=await h.request('/posts','POST',payload);
    assert.equal(anonymous.status,401);assert.equal(h.sql.prepare('SELECT COUNT(*) n FROM posts').get().n,before);
    const created=await h.request('/posts','POST',payload,'user');
    assert.equal(created.status,200);
    const saved=h.sql.prepare('SELECT user_id,tag FROM posts WHERE id=?').get(created.data.id);
    assert.equal(saved.user_id,2);assert.equal(saved.tag,'gen','forbidden notice tags follow the existing ordinary-post fallback');
    const edited=await h.request('/posts/'+created.data.id,'PATCH',{...payload,title:'Still not a notice'},'user');
    assert.equal(edited.status,200);assert.equal(h.sql.prepare('SELECT tag FROM posts WHERE id=?').get(created.data.id).tag,'gen');
    const publicNotices=(await h.request('/posts?notices=1&lang=ko')).data;
    assert.equal(publicNotices.total,24);assert.equal(publicNotices.posts.some(post=>post.id===created.data.id),false);
    const changed=await h.request('/posts/1','PATCH',payload,'user');assert.equal(changed.status,403);
    assert.equal(h.sql.prepare('SELECT title FROM posts WHERE id=1').get().title,'Notice 1');
    assert.equal((await h.request('/posts/1/pin','PATCH',{pinned:true,role:'admin'},'user')).status,403);
  }finally{h.sql.close();}
});

test('a former admin loses notice editing, deletion and pinning immediately while retaining ownership of ordinary posts',async()=>{
  const h=fixture();
  try{
    // Keep the same authenticated session: privileges must come from the current
    // database role, including when the author still owns the announcement.
    h.sql.prepare("UPDATE users SET role='user' WHERE id=1").run();
    const before=h.sql.prepare('SELECT title,body,tag FROM posts WHERE id=1').get();
    assert.equal((await h.request('/posts/1','GET',undefined,'admin')).data.post.mine,false,'the detail UI receives the same current-role permission');
    const patch=await h.request('/posts/1','PATCH',{title:'Changed by former admin',body:'Replacement',tag:'gen'},'admin');
    assert.equal(patch.status,403);assert.equal(patch.data.error,'forbidden');
    assert.equal((await h.request('/posts/1','DELETE',undefined,'admin')).status,403);
    assert.equal((await h.request('/posts/1/pin','PATCH',{pinned:true},'admin')).status,403);
    assert.deepEqual(h.sql.prepare('SELECT title,body,tag FROM posts WHERE id=1').get(),before);
    const created=await h.request('/posts','POST',{board:'free',tag:'gen',title:'Own ordinary post',body:'Public text'},'admin');
    assert.equal(created.status,200);
    assert.equal((await h.request('/posts/'+created.data.id,'PATCH',{title:'Own post edited',body:'Updated public text'},'admin')).status,200);
    assert.equal((await h.request('/posts/'+created.data.id,'DELETE',undefined,'admin')).status,200);
    h.sql.prepare("UPDATE users SET role='admin' WHERE id=1").run();
    assert.equal((await h.request('/posts/1','PATCH',{title:'Current admin edit',body:'Updated announcement'},'admin')).status,200);
    assert.equal((await h.request('/posts/1')).data.post.tag,'notice');
    assert.equal((await h.request('/posts/1','DELETE',undefined,'admin')).status,200);
    assert.equal((await h.request('/posts/1')).status,404);
  }finally{h.sql.close();}
});

test('only admins can pin notices; first pin bootstraps durably and unpin/re-tag updates every public list',async()=>{
  const h=fixture();
  assert.equal((await h.request('/posts/1/pin','PATCH',{pinned:true})).status,401);
  assert.equal((await h.request('/posts/1/pin','PATCH',{pinned:true},'user')).status,403);
  assert.equal((await h.request('/posts/26/pin','PATCH',{pinned:true},'admin')).data.error,'not_notice');
  assert.equal((await h.request('/posts/1/pin','PATCH',{pinned:'true'},'admin')).data.error,'bad_pin');
  assert.equal((await h.request('/posts/999/pin','PATCH',{pinned:true},'admin')).status,404);
  assert.equal(h.sql.prepare("SELECT COUNT(*) n FROM sqlite_master WHERE name='notice_pins'").get().n,0);
  assert.deepEqual((await h.request('/posts/1/pin','PATCH',{pinned:true},'admin')).data,{ok:true,id:1,pinned:true});
  assert.equal(h.sql.prepare('SELECT COUNT(*) n FROM notice_pins WHERE post_id=1').get().n,1);
  assert.equal((await h.request('/posts?notices=1&lang=ko')).data.posts[0].id,1);
  assert.equal((await h.request('/posts?lang=ko')).data.notices[0].id,1);
  assert.equal((await h.request('/posts?board=qna&lang=ko')).data.notices[0].id,1);
  assert.equal((await h.request('/posts/1')).data.post.pinned,true);
  await h.request('/posts/1/pin','PATCH',{pinned:true},'admin');
  assert.equal(h.sql.prepare('SELECT COUNT(*) n FROM notice_pins').get().n,1,'repeated pin is idempotent');
  assert.equal((await h.request('/posts/1/pin','PATCH',{pinned:false},'admin')).data.pinned,false);
  assert.equal((await h.request('/posts?notices=1')).data.posts[0].id,24);
  await h.request('/posts/1/pin','PATCH',{pinned:true},'admin');
  await h.request('/posts/1','PATCH',{title:'Changed',body:'Public body',tag:'gen'},'admin');
  assert.equal(h.sql.prepare('SELECT COUNT(*) n FROM notice_pins').get().n,0,'changing the notice tag clears the old pin');
  h.sql.exec(readFileSync(new URL('./migrations/0014_notice_pins.sql',import.meta.url),'utf8'));
  h.sql.exec(NOTICE_PINS_SCHEMA); // Migration and runtime order never conflict.
  h.sql.close();
});

test('lazy ensure coalesces by stable DB scope and retries unexpected failures without swallowing them',async()=>{
  const scope={},calls=[];let resolve;
  const db={prepare(query){calls.push(query);return {run:()=>new Promise(done=>resolve=done)};}};
  const one=ensureNoticePins(db,scope),two=ensureNoticePins({...db},scope);assert.equal(one,two);
  await Promise.resolve();assert.equal(calls.length,1);resolve({success:true});await one;
  await ensureNoticePins({...db},scope);assert.equal(calls.length,1);
  let tries=0;const broken={prepare(){return {run:async()=>{if(++tries===1)throw Error('disk unavailable');}};}};
  await assert.rejects(ensureNoticePins(broken),/disk unavailable/);await ensureNoticePins(broken);assert.equal(tries,2);
  assert.equal(missingNoticePins(Error('D1_ERROR: no such table: notice_pins: SQLITE_ERROR')),true);
  assert.equal(missingNoticePins(Error('no such table: users')),false);
  assert.equal(missingNoticePins(Error('permission denied')),false);
  await assert.rejects(readPublicPosts({prepare(){throw Error('disk unavailable');}},new URL('https://local/api/posts?notices=1')),/disk unavailable/);
});
