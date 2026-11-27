/* The shared-storage groups (src/workshop-groups.js, src/workshop-group-gate.js): invite codes, joining, roles and
   account deletion, against an in-memory SQLite behind a D1-shaped wrapper. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createWorkshopStorageRouter, workshopForgetUser} from './src/workshop-storage.js';
import {createLearnRouter} from './src/learn-services.js';
import {newInviteCode, parseCode, hashInviteCode, formatInviteCode, INVITE_ALPHABET, JOIN_RULES} from './src/workshop-groups.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
const fails=async(p,code,status)=>assert.rejects(p,e=>{assert.equal(e.code,code);if(status!=null)assert.equal(e.status,status);return true;});
const G='/api/workshop/storage/groups';

function setup(){
  const db=new DatabaseSync(':memory:');
  const D1={prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},
    async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{changes:r.changes,last_row_id:Number(r.lastInsertRowid)}};}};}};
  let t=1_800_000_000;
  /* the fixed-window limit of index.js */
  const windows=new Map();
  const limit=async(env,key,max,win)=>{const w=windows.get(key);if(!w||t-w.start>=win){windows.set(key,{start:t,n:1});return;}if(w.n>=max)throw new H(429,'rate_limited');w.n++;};
  const needUser=u=>{if(!u)throw new H(401,'login_required');return u;};
  const route=createWorkshopStorageRouter({HttpError:H,bad,now:()=>t,needUser,limit});
  const learn=createLearnRouter({HttpError:H,bad,now:()=>t,needUser,limit,clientIp:()=>'1.2.3.4'});
  const env={DB:D1};
  db.exec(`CREATE TABLE users (id INTEGER PRIMARY KEY, nickname TEXT, email TEXT, username TEXT, avatar TEXT, deleted INTEGER NOT NULL DEFAULT 0);
    INSERT INTO users(id,nickname,email,username,avatar) VALUES (7,'박선생','park@school.test','teacher_park','avKeyPark1'),(8,'민지','minji@x.test','minji',NULL),
      (9,'서준','seojun@x.test','seojun','avKeySeo99'),(10,'하은','haeun@x.test','haeun',NULL),(11,'도윤','doyun@x.test','doyun',NULL),(12,'외부인','out@x.test','outsider',NULL);`);
  const call=(p,m,body,me,ip='9.9.9.9')=>{const [path,q]=p.split('?');return route(path,m,body,me,new Request('https://x.test'+p,{method:m,headers:{'CF-Connecting-IP':ip}}),env);};
  return {db,env,call,learn:(p,m,b,me)=>learn(p,m,b,me,null,env),tick:s=>{t+=s;},now:()=>t,windows};
}
const [owner,minji,seojun,haeun,doyun,outsider]=[7,8,9,10,11,12].map(id=>({id}));
async function group(s,approval=false){
  const g=await s.call(G,'POST',{name:'물리 동아리',description:'월요일 실험 자료',approval},owner);
  const {code}=await s.call(`${G}/${g.id}/invites`,'POST',{expires:'7d',max_uses:null},owner);
  return {...g,code};
}

test('invite codes: eight letters from the unambiguous alphabet, shown XXXX-XXXX, case and dashes do not matter, only a hash is kept',async()=>{
  const seen=new Set();
  for(let i=0;i<200;i++){const c=newInviteCode();assert.equal(c.length,8);for(const ch of c)assert.ok(INVITE_ALPHABET.includes(ch));seen.add(c);}
  assert.ok(seen.size>195);
  for(const ch of 'IO01')assert.ok(!INVITE_ALPHABET.includes(ch));
  assert.equal(INVITE_ALPHABET.length,32);
  assert.equal(formatInviteCode('ABCDEFGH'),'ABCD-EFGH');
  assert.deepEqual(parseCode(' abcd-efgh '),{invite:'ABCDEFGH'});assert.deepEqual(parseCode('ab cd ef gh'),{invite:'ABCDEFGH'});
  assert.deepEqual(parseCode('abc123'),{legacy:'ABC123'});
  assert.equal(parseCode('ABCD-EFG0'),null);assert.equal(parseCode('ABCDEFGHJ'),null);assert.equal(parseCode(null),null);
  assert.equal(await hashInviteCode('ABCDEFGH'),await hashInviteCode('ABCDEFGH'));assert.notEqual(await hashInviteCode('ABCDEFGH'),await hashInviteCode('ABCDEFGJ'));
  const s=setup(),g=await group(s);
  assert.match(g.code,/^[A-Z2-9]{4}-[A-Z2-9]{4}$/);
  const raw=g.code.replace('-','');
  const rows=s.db.prepare('SELECT * FROM workshop_group_invites').all();
  assert.equal(rows.length,1);assert.equal(rows[0].code_hash,await hashInviteCode(raw));
  assert.ok(!JSON.stringify(rows).includes(raw),'the code itself is not stored');
  const detail=await s.call(`${G}/${g.id}`,'GET',null,owner);
  assert.ok(!JSON.stringify(detail).includes(raw),'and never shown again');
  assert.equal(detail.invites[0].hint,raw.slice(0,2)+'··-····');
  assert.equal((await s.call(`${G}/join`,'POST',{code:g.code.toLowerCase()},minji)).status,'joined');
});

test('the code alone joins: preview shows name, owner and count; members are listed with public fields only',async()=>{
  const s=setup(),g=await group(s);
  await fails(s.call(`${G}/preview`,'POST',{code:'nope'},minji),'bad_code',400);
  const {group:pre}=await s.call(`${G}/preview`,'POST',{code:g.code},minji);
  assert.deepEqual(pre,{name:'물리 동아리',description:'월요일 실험 자료',owner:{nickname:'박선생',avatar:'avKeyPark1'},member_count:1,approval:false,member:false,pending:false});
  assert.deepEqual(await s.call(`${G}/join`,'POST',{code:g.code},minji),{status:'joined',group:{id:g.id,name:'물리 동아리'}});
  assert.equal((await s.call(`${G}/join`,'POST',{code:g.code},minji)).status,'member');
  await s.call(`${G}/join`,'POST',{code:g.code.replace('-',' ')},seojun);
  const list=await s.call(G,'GET',null,minji);
  assert.equal(list.groups.length,1);
  const card=list.groups[0];
  assert.equal(card.role,'member');assert.equal(card.member_count,3);assert.ok(!('pending_requests' in card));
  assert.deepEqual(card.avatars.map(a=>a.nickname),['박선생','민지','서준']);
  const d=await s.call(`${G}/${g.id}`,'GET',null,minji);
  const text=JSON.stringify(d);
  for(const secret of ['park@school.test','teacher_park','minji@x.test','"user_id"','"id":7','"id":8','"id":9'])assert.ok(!text.includes(secret),secret);
  for(const m of d.members)assert.deepEqual(Object.keys(m).sort(),['avatar','joined_at','me','nickname','role']);
  assert.deepEqual(d.members.map(m=>[m.nickname,m.role,m.me]),[['박선생','owner',false],['민지','member',true],['서준','member',false]]);
  assert.ok(!('invites' in d)&&!('requests' in d)&&!('class_code' in d.group),'members do not see the managers\' parts');
  const od=await s.call(`${G}/${g.id}`,'GET',null,owner);
  for(const m of od.members)assert.deepEqual(Object.keys(m).sort(),['avatar','joined_at','last_active_at','me','nickname','role']);
  assert.equal(od.members[1].last_active_at,s.now(),'the last visit to the shared storage');
  assert.equal(od.group.storage.quota,5*1024*1024);assert.equal(od.group.storage.used,0);
  assert.match(od.group.class_code,/^[A-Z2-9]{6}$/);
});

test('expiry, max uses, revoke and regenerate',async()=>{
  const s=setup(),g=await s.call(G,'POST',{name:'반'},owner),inv=b=>s.call(`${G}/${g.id}/invites`,'POST',b,owner);
  await fails(inv({expires:'3d',max_uses:null}),'bad_expiry');await fails(inv({expires:'1d',max_uses:5}),'bad_max_uses');
  const day=await inv({expires:'1d',max_uses:10}),never=await inv({expires:'never',max_uses:null}),once=await inv({expires:'7d',max_uses:1});
  assert.equal(day.invite.expires_at,s.now()+86400);assert.equal(never.invite.expires_at,null);
  assert.equal((await s.call(`${G}/join`,'POST',{code:once.code},minji)).status,'joined');
  await fails(s.call(`${G}/join`,'POST',{code:once.code},seojun),'invite_used_up',410);
  s.tick(86401);
  await fails(s.call(`${G}/join`,'POST',{code:day.code},seojun),'invite_expired',410);
  assert.equal((await s.call(`${G}/join`,'POST',{code:never.code},seojun)).status,'joined');
  const listed=(await s.call(`${G}/${g.id}`,'GET',null,owner)).invites;
  assert.deepEqual(listed.map(i=>i.id),[never.invite.id],'used-up and expired codes leave the list');
  assert.equal(listed[0].uses,1);assert.equal(listed[0].created_by,'박선생');
  await s.call(`${G}/${g.id}/invites/${never.invite.id}`,'DELETE',null,owner);
  await fails(s.call(`${G}/join`,'POST',{code:never.code},haeun),'invite_not_found',404);
  const week=await inv({expires:'7d',max_uses:50});
  const again=await s.call(`${G}/${g.id}/invites/${week.invite.id}/regenerate`,'POST',{},owner);
  assert.notEqual(again.code,week.code);assert.equal(again.invite.max_uses,50);assert.equal(again.invite.expires_at,s.now()+7*86400);
  await fails(s.call(`${G}/join`,'POST',{code:week.code},haeun),'invite_not_found');
  assert.equal((await s.call(`${G}/join`,'POST',{code:again.code},haeun)).status,'joined');
  await fails(s.call(`${G}/${g.id}/invites/${week.invite.id}`,'DELETE',null,owner),'invite_not_found');
});

test('guessing is limited per member and per address, and repeated wrong codes lock out',async()=>{
  const s=setup(),g=await group(s);
  const guess=(me,ip)=>s.call(`${G}/preview`,'POST',{code:'ZZZZ-ZZZZ'},me,ip);
  for(let i=0;i<JOIN_RULES.userAttempts;i++){
    if(i<JOIN_RULES.userFails-1)await fails(guess(outsider,'1.1.1.1'),'invite_not_found',404);
    else if(i===JOIN_RULES.userFails-1)await fails(guess(outsider,'1.1.1.1'),'invite_not_found',404);
    else await fails(guess(outsider,'1.1.1.1'),'join_locked',429);
  }
  /* locked: even the right code is refused, after the attempt window too, until the lock ends */
  s.tick(JOIN_RULES.window+1);
  await fails(s.call(`${G}/join`,'POST',{code:g.code},outsider,'1.1.1.1'),'join_locked',429);
  s.tick(JOIN_RULES.lock);
  assert.equal((await s.call(`${G}/join`,'POST',{code:g.code},outsider,'1.1.1.1')).status,'joined');
  /* the attempt limit alone: ten entries in ten minutes, right or wrong */
  const s2=setup(),g2=await group(s2);
  for(let i=0;i<JOIN_RULES.userAttempts;i++)await s2.call(`${G}/preview`,'POST',{code:g2.code},minji);
  await fails(s2.call(`${G}/preview`,'POST',{code:g2.code},minji),'rate_limited',429);
  /* one address trying many accounts is locked too */
  const s3=setup();await group(s3);
  const people=[8,9,10,11,12,13,14,15,16,17].map(id=>({id}));
  let n=0;
  try{for(;n<200;n++)await s3.call(`${G}/preview`,'POST',{code:'ZZZZ-ZZZY'},people[Math.floor(n/5)%people.length],'5.5.5.5').catch(e=>{if(e.code!=='invite_not_found')throw e;});}
  catch(e){assert.equal(e.code,'join_locked');}
  assert.equal(n,JOIN_RULES.ipFails,'the address locks after its failures');
  await fails(s3.call(`${G}/preview`,'POST',{code:'ZZZZ-ZZZY'},{id:99},'5.5.5.5'),'join_locked');
  await fails(s3.call(`${G}/preview`,'POST',{code:'ZZZZ-ZZZY'},{id:99},'6.6.6.6'),'invite_not_found');
});

test('with approval on, a code asks to join; the owner or an admin approves or denies',async()=>{
  const s=setup(),g=await group(s,true);
  assert.equal((await s.call(`${G}/preview`,'POST',{code:g.code},minji)).group.approval,true);
  assert.deepEqual(await s.call(`${G}/join`,'POST',{code:g.code},minji),{status:'pending',group:{id:g.id,name:'물리 동아리'}});
  assert.equal((await s.call(`${G}/join`,'POST',{code:g.code},minji)).status,'pending');
  assert.equal((await s.call(`${G}/preview`,'POST',{code:g.code},minji)).group.pending,true);
  await s.call(`${G}/join`,'POST',{code:g.code},seojun);
  await fails(s.call(`${G}/${g.id}`,'GET',null,minji),'group_not_found',404);
  assert.equal((await s.call(G,'GET',null,minji)).groups.length,0);
  const d=await s.call(`${G}/${g.id}`,'GET',null,owner);
  assert.deepEqual(d.requests.map(r=>[r.nickname,r.avatar]),[['민지',null],['서준','avKeySeo99']]);
  assert.equal((await s.call(G,'GET',null,owner)).groups[0].pending_requests,2);
  assert.equal(d.invites[0].uses,2,'a request uses the code once');
  assert.equal((await s.call(`${G}/${g.id}/requests/${encodeURIComponent('민지')}`,'POST',{approve:true},owner)).status,'joined');
  await fails(s.call(`${G}/${g.id}/requests/${encodeURIComponent('서준')}`,'POST',{approve:true},minji),'forbidden',403);
  await s.call(`${G}/${g.id}/members/${encodeURIComponent('민지')}`,'PATCH',{role:'admin'},owner);
  assert.equal((await s.call(`${G}/${g.id}/requests/${encodeURIComponent('서준')}`,'POST',{approve:false},minji)).status,'denied');
  await fails(s.call(`${G}/${g.id}`,'GET',null,seojun),'group_not_found');
  assert.equal((await s.call(`${G}/${g.id}`,'GET',null,owner)).requests.length,0);
  /* the admin turns approval off; the next code joins at once */
  await s.call(`${G}/${g.id}`,'PATCH',{approval:false},minji);
  assert.equal((await s.call(`${G}/join`,'POST',{code:g.code},haeun)).status,'joined');
});

test('roles: only the owner and admins manage, admins cannot touch admins, outsiders see nothing',async()=>{
  const s=setup(),g=await group(s);
  for(const me of [minji,seojun,haeun,doyun])await s.call(`${G}/join`,'POST',{code:g.code},me);
  const member=n=>`${G}/${g.id}/members/${encodeURIComponent(n)}`;
  for(const [p,m,b] of [[`${G}/${g.id}`,'GET'],[`${G}/${g.id}`,'PATCH',{description:'x'}],[`${G}/${g.id}/invites`,'POST',{expires:'1d',max_uses:1}],[member('민지'),'DELETE'],[`${G}/${g.id}/leave`,'POST',{}]])
    await fails(s.call(p,m,b||null,outsider),'group_not_found',404);
  await fails(s.call(`${G}/${g.id}/invites`,'POST',{expires:'1d',max_uses:1},seojun),'forbidden',403);
  await fails(s.call(`${G}/${g.id}`,'PATCH',{approval:true},seojun),'forbidden',403);
  await fails(s.call(member('하은'),'DELETE',null,seojun),'forbidden',403);
  await fails(s.call(member('서준'),'PATCH',{role:'admin'},minji),'forbidden',403);
  await s.call(member('민지'),'PATCH',{role:'admin'},owner);
  await fails(s.call(member('서준'),'PATCH',{role:'owner'},owner),'bad_role');
  await fails(s.call(`${G}/${g.id}`,'PATCH',{name:'새 이름'},minji),'forbidden',403);
  await s.call(`${G}/${g.id}`,'PATCH',{description:'관리자가 고침'},minji);
  assert.ok((await s.call(`${G}/${g.id}/invites`,'POST',{expires:'1d',max_uses:1},minji)).code);
  await s.call(member('도윤'),'PATCH',{role:'admin'},owner);
  await fails(s.call(member('도윤'),'DELETE',null,minji),'forbidden',403);
  await fails(s.call(member('박선생'),'DELETE',null,minji),'member_not_found',404);
  /* a removed member loses the group and its shares at once and cannot come back with the old code or the class code */
  s.db.exec(`INSERT INTO workshop_files(id,owner_id,folder,name,size,mime,r2_key,created_at,updated_at) VALUES ('${'a'.repeat(32)}',9,'','notes.txt',5,'text/plain','k',0,0)`);
  const share=await s.call('/api/workshop/storage/shared','POST',{kind:'resource',class_id:g.id,title:'노트',file_id:'a'.repeat(32)},seojun);
  assert.equal((await s.call('/api/workshop/storage/shared','GET',null,haeun)).shares.length,1);
  assert.equal((await s.call(`${G}/${g.id}`,'GET',null,owner)).group.storage.used,5);
  await s.call(member('서준'),'DELETE',null,minji);
  await fails(s.call(`${G}/${g.id}`,'GET',null,seojun),'group_not_found');
  await fails(s.call('/api/workshop/storage/shared/'+share.id,'GET',null,seojun),'not_found');
  assert.equal((await s.call('/api/workshop/storage/shared','GET',null,haeun)).shares.length,0,'their shares go with them');
  await fails(s.call(`${G}/join`,'POST',{code:g.code},seojun),'removed_from_group',403);
  const classCode=(await s.call(`${G}/${g.id}`,'GET',null,owner)).group.class_code;
  await fails(s.call(`${G}/join`,'POST',{code:classCode},seojun),'removed_from_group',403);
  await fails(s.learn('/api/learn/classes/join','POST',{code:classCode},seojun),'removed_from_group',403);
  s.tick(1);
  const fresh=await s.call(`${G}/${g.id}/invites`,'POST',{expires:'1d',max_uses:1},owner);
  assert.equal((await s.call(`${G}/join`,'POST',{code:fresh.code},seojun)).status,'joined','a code made after the removal is a new invitation');
  /* leave, the owner cannot leave, rename, transfer, delete with the name typed */
  await s.call(`${G}/${g.id}/leave`,'POST',{},haeun);
  await fails(s.call(`${G}/${g.id}`,'GET',null,haeun),'group_not_found');
  await fails(s.call(`${G}/${g.id}/leave`,'POST',{},owner),'owner_must_transfer',409);
  await s.call(`${G}/${g.id}`,'PATCH',{name:'물리 실험반'},owner);
  await fails(s.call(`${G}/${g.id}/transfer`,'POST',{nickname:'외부인'},owner),'member_not_found');
  await fails(s.call(`${G}/${g.id}/transfer`,'POST',{nickname:'민지'},minji),'forbidden');
  assert.deepEqual(await s.call(`${G}/${g.id}/transfer`,'POST',{nickname:'민지'},owner),{ok:true,owner:'민지'});
  const after=await s.call(`${G}/${g.id}`,'GET',null,owner);
  assert.equal(after.group.role,'admin');assert.equal(after.group.owner.nickname,'민지');assert.equal(after.group.name,'물리 실험반');
  assert.deepEqual(after.members.filter(m=>m.role==='owner').map(m=>m.nickname),['민지']);
  await fails(s.call(`${G}/${g.id}?confirm=${encodeURIComponent('물리 실험반')}`,'DELETE',null,owner),'forbidden');
  await fails(s.call(`${G}/${g.id}?confirm=x`,'DELETE',null,minji),'confirm_name');
  assert.deepEqual(await s.call(`${G}/${g.id}?confirm=${encodeURIComponent('물리 실험반')}`,'DELETE',null,minji),{ok:true});
  await fails(s.call(`${G}/${g.id}`,'GET',null,minji),'group_not_found');
  await fails(s.call(`${G}/join`,'POST',{code:fresh.code},doyun),'invite_not_found');
});

test('the Learn class code: turned off by the owner, and it asks for approval like an invite code',async()=>{
  const s=setup(),g=await group(s);
  const code=(await s.call(`${G}/${g.id}`,'GET',null,owner)).group.class_code;
  assert.equal((await s.learn('/api/learn/classes/join','POST',{code},minji)).name,'물리 동아리');
  await s.call(`${G}/${g.id}`,'PATCH',{approval:true},owner);
  await fails(s.learn('/api/learn/classes/join','POST',{code},seojun),'join_pending',403);
  assert.deepEqual((await s.call(`${G}/${g.id}`,'GET',null,owner)).requests.map(r=>r.nickname),['서준']);
  await s.call(`${G}/${g.id}`,'PATCH',{legacy_code:false},owner);
  await fails(s.learn('/api/learn/classes/join','POST',{code},haeun),'class_not_found',404);
  await fails(s.call(`${G}/join`,'POST',{code},haeun),'invite_not_found',404);
  assert.equal((await s.call(`${G}/${g.id}`,'GET',null,owner)).group.class_code,null);
  await fails(s.call(`${G}/${g.id}`,'PATCH',{legacy_code:true},minji),'forbidden');
});

test('account deletion: an owned group goes to the longest-serving admin, one without an admin closes, memberships go',async()=>{
  const s=setup();
  await s.call(G,'GET',null,owner);
  s.db.exec("INSERT INTO entitlements(user_id,kind,starts_at,ends_at,source,created_at) VALUES (7,'teacher',0,NULL,'test',0)");
  const a=await group(s),b=await s.call(G,'POST',{name:'두 번째'},owner);
  const bc=(await s.call(`${G}/${b.id}/invites`,'POST',{expires:'never',max_uses:null},owner)).code;
  await s.call(`${G}/join`,'POST',{code:a.code},minji);s.tick(10);
  await s.call(`${G}/join`,'POST',{code:a.code},seojun);await s.call(`${G}/join`,'POST',{code:bc},seojun);
  await s.call(`${G}/${a.id}/members/${encodeURIComponent('서준')}`,'PATCH',{role:'admin'},owner);
  await s.call(`${G}/${a.id}/members/${encodeURIComponent('민지')}`,'PATCH',{role:'admin'},owner);
  /* a group the owner is only a member of */
  const c=await s.call(G,'POST',{name:'민지네'},minji);
  const cc=(await s.call(`${G}/${c.id}/invites`,'POST',{expires:'never',max_uses:null},minji)).code;
  await s.call(`${G}/join`,'POST',{code:cc},owner);
  await workshopForgetUser(s.env,7);
  const ad=await s.call(`${G}/${a.id}`,'GET',null,minji);
  assert.equal(ad.group.owner.nickname,'민지','the admin who joined first');
  assert.deepEqual(ad.members.map(m=>[m.nickname,m.role]),[['민지','owner'],['서준','admin']]);
  await fails(s.call(`${G}/${b.id}`,'GET',null,seojun),'group_not_found');
  assert.ok(s.db.prepare('SELECT closed_at FROM classes WHERE id=?').get(b.id).closed_at);
  assert.deepEqual((await s.call(`${G}/${c.id}`,'GET',null,minji)).members.map(m=>m.nickname),['민지']);
  assert.equal(s.db.prepare('SELECT COUNT(*) AS n FROM class_members WHERE user_id=7').get().n,0);
  assert.equal(s.db.prepare('SELECT COUNT(*) AS n FROM workshop_group_invites WHERE created_by=7 AND revoked_at IS NULL').get().n,0,'their codes stop working');
  await fails(s.call(`${G}/join`,'POST',{code:a.code},haeun),'invite_not_found');
});
