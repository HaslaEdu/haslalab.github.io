import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createShareRouter, cleanThumb, svgSafe, plainText, cleanTags, cleanSet} from './src/workshop-share.js';
import {createCreationRouter} from './src/creations.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
const text=(v,max,code)=>{if(typeof v!=='string')bad(code);v=v.trim();if(!v||v.length>max)bad(code);return v;};
function setup(externalProject){
  const db=new DatabaseSync(':memory:');
  db.exec("CREATE TABLE users(id INTEGER PRIMARY KEY,nickname TEXT,role TEXT,avatar TEXT,created_at INTEGER,deleted INTEGER DEFAULT 0)");
  db.exec("INSERT INTO users(id,nickname,role,avatar,created_at) VALUES(1,'ana',NULL,'abcdefgh12',1),(2,'bo',NULL,NULL,1),(3,'cy',NULL,NULL,1),(9,'staff','admin',NULL,1)");
  db.exec("CREATE TABLE reports(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,target_id INTEGER NOT NULL,user_id INTEGER NOT NULL,reason TEXT NOT NULL,created_at INTEGER NOT NULL,UNIQUE(kind,target_id,user_id))");
  const D1={async batch(s){const out=[];for(const x of s)out.push(await x.all());return out;},prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{last_row_id:Number(r.lastInsertRowid),changes:Number(r.changes)}};}};}};
  const hits=new Map();let clock=1_800_000_000,ip='1.1.1.1';
  const deps={HttpError:H,bad,text,now:()=>clock,clientIp:()=>ip,needUser:u=>{if(!u)throw new H(401,'login_required');return u;},
    limit:async(env,k,max)=>{const n=(hits.get(k)||0)+1;hits.set(k,n);if(n>max)throw new H(429,'rate_limited');}};
  const share=createShareRouter({...deps,externalProject}),creations=createCreationRouter(deps);
  const env={DB:D1};
  const call=(route,p,m,b,me,q='')=>route(p,m,b,me,{url:'https://x'+p+q},env);
  const r=(p,m,b,me,q)=>call(share,p,m,b,me,q);
  r.creations=(p,m,b,me,q)=>call(creations,p,m,b,me,q);
  r.db=db;r.tick=s=>{clock+=s;};r.ip=v=>{ip=v;};
  return r;
}
const ana={id:1,nickname:'ana',avatar:'abcdefgh12'},bo={id:2,nickname:'bo'},cy={id:3,nickname:'cy'},staff={id:9,nickname:'staff',role:'admin'};
const fails=async(p,code)=>assert.rejects(p,e=>e.code===code,code);
const PNG='data:image/png;base64,'+Buffer.concat([Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]),Buffer.alloc(40)]).toString('base64');
const SVG='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><defs><marker id="m"/></defs><path d="M0 0L10 10" stroke="#000" marker-end="url(#m)"/><text font-family="serif">F</text></svg>';
const scene={format:'haslalab-scene',version:2,objects:[{id:'b1',type:'block',x:0,y:0.5,w:1,h:1,m:2}]};
const sim={type:'sim',title:'Projectile',description:'Change the **angle**.\nSee where it lands.',howto:'Drag the slider.',notes:'After a textbook figure.',tags:['포물선','#Kinematics'],topic:'mechanics',
  payload:{code:'loop(dt=>{})',question:'How far?',answer:'45',answerUnit:'m'},thumbnail:PNG};

test('C and Python simulations preserve the runtime through publication and remix', async () => {
  const r = setup();
  const source = 'int main(void) { return 0; }';
  const {id} = await r('/api/share','POST',{...sim,payload:{language:'c',code:source}},ana);
  const path = '/api/share/'+id;
  assert.equal((await r(path,'GET')).project.code, source);
  assert.equal((await r(path,'GET')).project.language, 'c');
  assert.equal((await r('/api/share','GET',null,null,'?type=figure')).items.length,0);
  const remix = await r(path+'/remix','POST',{},bo);
  assert.match(remix.edit,/view=compute/);
  await fails(r('/api/share/'+remix.id,'GET',null,cy),'not_found');
  assert.equal((await r('/api/share/'+remix.id,'GET',null,bo)).project.language,'c');
  await r(path,'PATCH',{payload:{language:'python',code:'print(42)'}},ana);
  assert.equal((await r(path,'GET')).project.code,'print(42)');
  await r(path,'PATCH',{payload:{language:'js',code:'hl.clear()'}},ana);
  const {project} = await r(path,'GET');
  assert.equal(project.language,'js');
  assert.equal(project.code,'hl.clear()');
});

test('authorized external snapshots update in place, and daily and live caps also cover the legacy API',async()=>{
  let code='print(1)', providerCalls=0;
  const r=setup(async(provider,ref,max,member)=>{
    providerCalls++;
    assert.equal(max,1024*1024);
    if(member.id!==ana.id)throw new H(403,'forbidden');
    assert.equal(provider,'github');assert.equal(ref,'pendulum.json');
    return {key:'github:10:main:haslalab:pendulum.json',name:ref,mime:'application/json',
      bytes:new TextEncoder().encode(JSON.stringify({format:'haslalab-compute',language:'python',sources:{python:code,c:'secret alternate code'}}))};
  });
  const preview=()=>r('/api/share/source','GET',null,ana,'?provider=github&file=pendulum.json');
  const post=p=>r('/api/share','POST',{source_provider:'github',source_file:'pendulum.json',source_digest:p.digest,title:'Pendulum'},ana);
  await fails(r('/api/share/source','GET',null,bo,'?provider=github&file=pendulum.json'),'forbidden');
  const before=await preview();
  assert.deepEqual(before.payload,{language:'python',code:'print(1)'});
  code='print(2)';
  await fails(post(before),'source_changed');
  const {id}=await post(await preview());
  assert.equal((await r('/api/share/'+id,'GET')).project.code,'print(2)');
  code='print(3)';
  assert.equal((await post(await preview())).id,id);
  assert.equal((await r('/api/share/'+id,'GET')).project.code,'print(3)');
  assert.ok(providerCalls>=6);
  const legacy=()=>r.creations('/api/creations','POST',{kind:'sim',title:'Legacy',code:'hl.clear()'},ana);
  await legacy(); await legacy();
  await fails(legacy(),'workshop_daily_share_limit');
  await r('/api/share/'+id,'DELETE',null,ana);
  await fails(legacy(),'workshop_daily_share_limit');
  assert.equal((await post(await preview())).id,id);
  for(let day=0;day<2;day++){r.tick(86400);await legacy();await legacy();await legacy();}
  r.tick(86400);await legacy();
  await fails(legacy(),'workshop_public_cap');
});

test('thumbnails: real PNGs, safe SVGs (stored as base64), nothing that can run or load; 200 KB at most',()=>{
  assert.equal(cleanThumb(PNG),PNG);
  assert.equal(cleanThumb('data:image/png;base64,'+Buffer.from('GIF89a'.repeat(8)).toString('base64')),null,'a PNG label on other bytes');
  const ok=cleanThumb('data:image/svg+xml;charset=utf-8,'+encodeURIComponent(SVG));
  assert.match(ok,/^data:image\/svg\+xml;base64,/);assert.equal(Buffer.from(ok.split(',')[1],'base64').toString(),SVG);
  for(const evil of ['<svg><script>alert(1)</script></svg>','<svg onload="alert(1)"></svg>','<svg><a href="javascript:x"><text>x</text></a></svg>',
    '<svg><foreignObject><div/></foreignObject></svg>','<svg><style>@import url(x)</style></svg>','<svg><image href="https://evil/x.png"/></svg>',
    '<svg><rect fill="url(https://evil/x)"/></svg>','<!DOCTYPE svg [<!ENTITY x "y">]><svg></svg>','<svg><use xlink:href="data:image/svg+xml,..."/></svg>',
    '<svg><set attributeName="onmouseover" to="alert(1)"/></svg>','<svg><rect style="fill:url(//evil)"/></svg>','<html><svg></svg></html>','<svg><text>&#x3C;script</text></svg>']){
    assert.equal(svgSafe(evil),false,evil);
    assert.equal(cleanThumb('data:image/svg+xml;base64,'+Buffer.from(evil).toString('base64')),null,evil);
  }
  assert.equal(svgSafe(SVG),true);
  const big='<svg>'+'<path d="M0 0"/>'.repeat(20000)+'</svg>';assert.equal(cleanThumb('data:image/svg+xml,'+encodeURIComponent(big)),null,'over 200 KB');
  assert.equal(cleanThumb('data:text/html;base64,PGI+'),null);assert.equal(cleanThumb(''),'');
});

test('descriptions are plain text, tags are short words, problem sets keep only known fields',()=>{
  assert.equal(plainText('<b>bold</b> a < b <img src=x onerror=alert(1)><!-- c -->ok',100),'bold a < b ok');
  assert.equal(plainText('x'.repeat(11),10),null);
  assert.deepEqual(cleanTags('#Optics, 렌즈 ,optics'),['optics','렌즈']);
  assert.equal(cleanTags(['<script>']),null);assert.equal(cleanTags(Array.from({length:9},(_,i)=>'t'+i)),null);
  const s=cleanSet({title:'Quiz <i>1</i>',items:[{key:'ap1:12',pts:4},{key:'own:a1',own:{q:'Find v.',answer:'3',unit:'m/s',sol:'',evil:'<x>',fig:{src:'data:image/svg+xml;base64,'+Buffer.from('<svg onload=1></svg>').toString('base64')}}}],extra:1});
  assert.deepEqual(s,{title:'Quiz 1',info:'',minutes:0,items:[{key:'ap1:12',pts:4},{key:'own:a1',pts:3,own:{q:'Find v.',answer:'3',unit:'m/s',sol:''}}]});
  const withIllustration=cleanSet({items:[{key:'own:raster',own:{q:'Read the diagram.',fig:{src:PNG,w:100,h:70}}}]});
  assert.deepEqual(withIllustration.items[0].own.fig,{src:PNG,w:100,h:70});
  assert.equal(cleanSet({items:[]}),null);assert.equal(cleanSet({items:[{key:'own:x'}]}),null,'an own problem needs its text');
});

test('publishing checks the type, the fields and the payload of each kind; guests read the list and the page',async()=>{
  const r=setup();
  await fails(r('/api/share','POST',sim,null),'login_required');
  await fails(r('/api/share','POST',{...sim,type:'video'},ana),'bad_type');
  await fails(r('/api/share','POST',{...sim,title:''},ana),'bad_title');
  await fails(r('/api/share','POST',{...sim,topic:'astrology'},ana),'bad_topic');
  await fails(r('/api/share','POST',{...sim,tags:['a<b>']},ana),'bad_tags');
  await fails(r('/api/share','POST',{...sim,thumbnail:'data:image/svg+xml,'+encodeURIComponent('<svg><script/></svg>')},ana),'bad_thumbnail');
  await fails(r('/api/share','POST',{...sim,payload:{code:''}},ana),'bad_payload');
  await fails(r('/api/share','POST',{type:'python',title:'P',payload:{statement:'x',grader:'print(1)'}},ana),'bad_payload');
  await fails(r('/api/share','POST',{type:'figure',title:'F',payload:{scene:{objects:[]}}},ana),'bad_payload');
  await fails(r('/api/share','POST',{type:'figure',title:'F',payload:{scene:{objects:[{id:'b',type:'block',label:'x'.repeat(130000)}]}}},ana),'payload_too_large');
  await fails(r('/api/share','POST',{type:'set',title:'S',payload:{items:[{key:'<bad>'}]}},ana),'bad_payload');
  const a=await r('/api/share','POST',{...sim,description:'<script>x</script>Change the angle.\nNow record the range. '+ 'a'.repeat(260)},ana);
  assert.equal(a.url,'#/workshop/share/'+a.id);
  const f=await r('/api/share','POST',{type:'figure',title:'Block on a floor',topic:'mechanics',payload:{scene},thumbnail:'data:image/svg+xml,'+encodeURIComponent(SVG)},bo);
  const s=await r('/api/share','POST',{type:'set',title:'Kinematics quiz',topic:'mechanics',payload:{items:[{key:'own:q1',own:{q:'A car…',answer:'2'}}]}},bo);
  const py=await r('/api/share','POST',{type:'python',title:'Euler',topic:'other',payload:{statement:'Write step().',starter:'def step():\n  pass',grader:'def grade(ns):\n  return {}'}},cy);
  const list=await r('/api/share','GET',null,null,'?tab=new');
  assert.deepEqual(list.items.map(i=>[i.id,i.type]),[[py.id,'python'],[s.id,'set'],[f.id,'figure'],[a.id,'sim']]);
  assert.ok(!('code' in list.items[0])&&!('payload' in list.items[0]),'the list carries no code or payload');
  assert.equal(list.items.at(-1).summary,'xChange the angle.');
  assert.match(list.items.at(-1).preview,/Now record the range/);
  assert.equal(list.items.at(-1).preview.length,240);
  assert.equal(list.items.at(-1).av,'abcdefgh12');assert.equal(list.items.at(-1).has_thumb,true);assert.deepEqual(list.items.at(-1).tags,['포물선','kinematics']);
  assert.deepEqual((await r('/api/share','GET',null,null,'?type=figure')).items.map(i=>i.id),[f.id]);
  assert.deepEqual((await r('/api/share','GET',null,null,'?topic=other')).items.map(i=>i.id),[py.id]);
  assert.deepEqual((await r('/api/share','GET',null,null,'?q=KINEMAT')).items.map(i=>i.id).sort(),[a.id,s.id].sort(),'title or tag');
  assert.deepEqual((await r('/api/share','GET',null,null,'?q=100%25')).items,[],'% is not a wildcard');
  const one=(await r(`/api/share/${a.id}`,'GET',null,null)).project;
  assert.match(one.description,/^xChange the angle\.\nNow record the range\./,'tags stripped, full description retained');assert.equal(one.code,'loop(dt=>{})');assert.equal(one.answerUnit,'m');assert.equal(one.mine,false);
  assert.equal((await r(`/api/share/${f.id}`,'GET',null,null)).project.payload.scene.objects[0].type,'block');
  assert.equal((await r(`/api/share/${s.id}`,'GET',null,null)).project.payload.items[0].own.q,'A car…');
  /* create.html's own gallery keeps showing only simulations and Python problems */
  assert.deepEqual((await r.creations('/api/creations','GET',null,null)).items.map(i=>i.kind).sort(),['code','sim']);
  const th=await r(`/api/share/${f.id}/thumb`,'GET',null,null);
  assert.ok(th instanceof Response);assert.equal(th.headers.get('Content-Type'),'image/svg+xml');assert.match(th.headers.get('Content-Security-Policy'),/default-src 'none'.*sandbox/);
  assert.equal(await th.text(),SVG);
  await fails(r(`/api/share/${py.id}/thumb`,'GET',null,null),'not_found');
});

test('likes and favourites count once per member; views once a day per visitor, shared with create.html\'s plays',async()=>{
  const r=setup();const {id}=await r('/api/share','POST',sim,ana);
  await fails(r(`/api/share/${id}/like`,'POST',{},null),'login_required');
  assert.equal((await r(`/api/share/${id}/like`,'POST',{},bo)).likes,1);
  assert.equal((await r(`/api/share/${id}/like`,'POST',{on:true},bo)).likes,1,'idempotent');
  assert.equal((await r(`/api/share/${id}/like`,'POST',{},cy)).likes,2);
  assert.equal((await r(`/api/share/${id}/like`,'POST',{on:false},cy)).likes,1);
  assert.equal((await r(`/api/share/${id}/fav`,'POST',{},bo)).favs,1);assert.equal((await r(`/api/share/${id}/fav`,'POST',{},bo)).favs,1);
  assert.equal((await r(`/api/share/${id}/view`,'POST',{},null)).counted,true);
  assert.equal((await r(`/api/share/${id}/view`,'POST',{},null)).counted,false,'the same visitor');
  assert.equal((await r.creations(`/api/creations/${id}/play`,'POST',{},null)).counted,false,'opening it in create.html too');
  r.ip('2.2.2.2');assert.equal((await r(`/api/share/${id}/view`,'POST',{},null)).counted,true);
  assert.equal((await r(`/api/share/${id}/view`,'POST',{},bo)).counted,true);
  const v=await r(`/api/share/${id}`,'GET',null,bo);
  assert.equal(v.project.views,3);assert.equal(v.project.likes,1);assert.equal(v.project.favs,1);assert.equal(v.liked,true);assert.equal(v.faved,true);
  assert.deepEqual((await r('/api/share','GET',null,bo,'?fav=1')).items.map(i=>i.id),[id]);
  await fails(r('/api/share','GET',null,null,'?fav=1'),'login_required');
  assert.deepEqual((await r('/api/share','GET',null,null,'?tab=week')).items.map(i=>i.id),[id]);
});

test('a remix is the member\'s private draft linked to the original; publishing it lists it under the original',async()=>{
  const r=setup();const a=await r('/api/share','POST',sim,ana);
  await fails(r(`/api/share/${a.id}/remix`,'POST',{},null),'login_required');
  const x=await r(`/api/share/${a.id}/remix`,'POST',{},bo);
  assert.equal(x.remix_of,a.id);assert.equal(x.edit,'#/workshop/create?view=edit&id='+x.id);
  await fails(r(`/api/share/${x.id}`,'GET',null,null),'not_found');await fails(r(`/api/share/${x.id}`,'GET',null,cy),'not_found');
  const draft=(await r(`/api/share/${x.id}`,'GET',null,bo)).project;
  assert.equal(draft.status,'draft');assert.equal(draft.code,'loop(dt=>{})');assert.equal(draft.forked_from,a.id);assert.equal(draft.title,'Remix: Projectile');assert.equal(draft.howto,'Drag the slider.');
  assert.equal((await r(`/api/share/${a.id}`,'GET',null,null)).project.remixes,0,'a draft is not counted');
  await fails(r('/api/share','POST',{type:'sim',creation_id:x.id,title:'Mine'},cy),'not_found');
  await fails(r('/api/share','POST',{type:'figure',creation_id:x.id},bo),'bad_type');
  await r('/api/share','POST',{type:'sim',creation_id:x.id,title:'Projectile with drag',description:'Adds air drag.'},bo);
  const page=await r(`/api/share/${a.id}`,'GET',null,null);
  assert.equal(page.project.remixes,1);assert.deepEqual(page.remixList.map(i=>[i.id,i.nickname]),[[x.id,'bo']]);
  const child=await r(`/api/share/${x.id}`,'GET',null,null);
  assert.deepEqual(child.original,{id:a.id,title:'Projectile',nickname:'ana'});assert.equal(child.project.description,'Adds air drag.');assert.equal(child.project.howto,'Drag the slider.','kept');
  assert.equal((await r('/api/share','GET',null,null,'?sort=remixes')).items[0].id,a.id);
  /* a figure remix opens in the figure editor, a set in the problem maker */
  const f=await r('/api/share','POST',{type:'figure',title:'F',payload:{scene}},ana),s=await r('/api/share','POST',{type:'set',title:'S',payload:{items:[{key:'ap1:3'}]}},ana);
  assert.match((await r(`/api/share/${f.id}/remix`,'POST',{},bo)).edit,/^#\/workshop\/draw\?share=\d+$/);
  const sx=await r(`/api/share/${s.id}/remix`,'POST',{},bo);assert.match(sx.edit,/^#\/workshop\/make\?share=\d+$/);
  assert.deepEqual((await r(`/api/share/${sx.id}`,'GET',null,bo)).project.payload.items,[{key:'ap1:3',pts:3}]);
  /* the creations editor's save-and-publish also makes a remixed draft public */
  const y=await r(`/api/share/${a.id}/remix`,'POST',{},cy);
  await r.creations(`/api/creations/${y.id}`,'PATCH',{title:'Cy remix'},cy);
  assert.equal((await r(`/api/share/${y.id}`,'GET',null,null)).project.status,'public');
  /* the original hidden: the remix says so without naming it */
  await r(`/api/share/${a.id}`,'DELETE',null,ana);
  assert.deepEqual((await r(`/api/share/${x.id}`,'GET',null,null)).original,{id:null,gone:true});
});

test('only the owner edits and unpublishes; staff hide, pick and the owner cannot publish a hidden one again',async()=>{
  const r=setup();const {id}=await r('/api/share','POST',sim,ana);
  await fails(r(`/api/share/${id}`,'PATCH',{title:'Mine now'},bo),'not_owner');
  await fails(r(`/api/share/${id}`,'DELETE',null,bo),'not_owner');
  await r(`/api/share/${id}`,'PATCH',{title:'Projectile 2',tags:['drag'],description:'<i>new</i> text',payload:{code:'loop(()=>{})'}},ana);
  let p=(await r(`/api/share/${id}`,'GET',null,null)).project;
  assert.equal(p.title,'Projectile 2');assert.deepEqual(p.tags,['drag']);assert.equal(p.description,'new text');assert.equal(p.code,'loop(()=>{})');assert.equal(p.howto,'Drag the slider.','fields not sent stay');
  await fails(r(`/api/share/${id}/feature`,'POST',{},ana),'forbidden');
  await r(`/api/share/${id}/feature`,'POST',{on:true},staff);
  assert.deepEqual((await r('/api/share','GET',null,null,'?tab=featured')).items.map(i=>[i.id,i.featured]),[[id,true]]);
  await r(`/api/share/${id}/feature`,'POST',{on:false},staff);assert.equal((await r('/api/share','GET',null,null,'?tab=featured')).items.length,0);
  await r(`/api/share/${id}`,'DELETE',null,staff);
  await fails(r(`/api/share/${id}`,'GET',null,bo),'not_found');
  assert.equal((await r(`/api/share/${id}`,'GET',null,ana)).project.hidden_by_staff,true,'the owner still sees it');
  await fails(r('/api/share','POST',{type:'sim',creation_id:id,title:'Back'},ana),'hidden_by_staff');
  assert.equal((await r('/api/share','GET',null,null)).items.length,0);
  /* the owner unpublishes their own and can publish it again */
  const b=await r('/api/share','POST',{...sim,title:'Second'},ana);
  await r(`/api/share/${b.id}`,'DELETE',null,ana);assert.equal((await r('/api/share','GET',null,null)).items.length,0);
  await r('/api/share','POST',{type:'sim',creation_id:b.id},ana);assert.deepEqual((await r('/api/share','GET',null,null)).items.map(i=>i.title),['Second']);
});

test('comments: members write, one level of replies, the writer or an admin deletes, reports go to the reports table',async()=>{
  const r=setup();const {id}=await r('/api/share','POST',sim,ana);
  await fails(r(`/api/share/${id}/comments`,'POST',{body:'hi'},null),'login_required');
  await fails(r(`/api/share/${id}/comments`,'POST',{body:'  '},bo),'bad_body');
  const c1=await r(`/api/share/${id}/comments`,'POST',{body:'<b>Nice</b>'},bo);
  const c2=await r(`/api/share/${id}/comments`,'POST',{body:'Thanks',parent_id:c1.id},ana);
  const c3=await r(`/api/share/${id}/comments`,'POST',{body:'Reply to a reply',parent_id:c2.id},cy);
  assert.equal(c3.comment.parent_id,c1.id,'replies stay one level deep');
  const list=await r(`/api/share/${id}/comments`,'GET',null,cy);
  assert.deepEqual(list.comments.map(c=>[c.body,c.mine]),[['<b>Nice</b>',false],['Thanks',false],['Reply to a reply',true]],'stored as written; the page escapes it');
  assert.equal((await r(`/api/share/${id}`,'GET',null,null)).project.comments,3);
  await fails(r(`/api/share/comments/${c1.id}`,'DELETE',null,cy),'forbidden');
  await r(`/api/share/comments/${c1.id}/report`,'POST',{reason:'spam'},cy);await r(`/api/share/comments/${c1.id}/report`,'POST',{reason:'spam'},cy);
  await r(`/api/share/${id}/report`,'POST',{reason:'copied'},bo);
  assert.deepEqual(r.db.prepare('SELECT kind,target_id FROM reports ORDER BY id').all().map(x=>({...x})),[{kind:'share_comment',target_id:c1.id},{kind:'share',target_id:id}]);
  await r(`/api/share/comments/${c1.id}`,'DELETE',null,staff);
  assert.equal((await r(`/api/share/${id}/comments`,'GET',null,null)).comments.length,0,'a thread goes with its first comment');
  assert.equal((await r(`/api/share/${id}`,'GET',null,null)).project.comments,0);
});

test('an author\'s page lists their public projects and totals; existing creations appear without share details',async()=>{
  const r=setup();
  const old=await r.creations('/api/creations','POST',{kind:'sim',title:'Old sim',code:'loop(()=>{})'},bo);
  await r('/api/share','POST',sim,bo);const hidden=await r('/api/share','POST',{...sim,title:'Gone'},bo);await r(`/api/share/${hidden.id}`,'DELETE',null,bo);
  const u=await r('/api/share/user/2','GET',null,null);
  assert.equal(u.user.nickname,'bo');assert.equal(u.totals.projects,2);assert.deepEqual(u.items.map(i=>i.title).sort(),['Old sim','Projectile']);
  const o=(await r(`/api/share/${old.id}`,'GET',null,null)).project;assert.equal(o.topic,'other');assert.equal(o.has_thumb,false);assert.deepEqual(o.tags,[]);
  await fails(r('/api/share/user/77','GET',null,null),'not_found');
});
