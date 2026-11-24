// node --test community/test-workshop-connectors.mjs
// Workshop storage connectors: Google Drive (drive.file, PKCE, sealed tokens) and GitHub (a GitHub App narrowed to one
// repository), against a fake Google, a fake GitHub and a D1 over node:sqlite.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {generateKeyPairSync, verify as nodeVerify, createHash} from 'node:crypto';
import {createWorkshopConnectorsRouter, workshopConnectorsForgetUser, cleanGhPath, ghFileName, githubAppJwt, sealToken, openToken, pkcs1ToPkcs8,
  googleRedirectUri, githubRedirectUri, connectorOrigin, CONNECTOR_ORIGIN, DRIVE_SCOPE, allowedReturn} from './src/workshop-connectors.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
const b64u=b=>Buffer.from(b).toString('base64url');
const {privateKey,publicKey}=generateKeyPairSync('rsa',{modulusLength:2048});
const PEM8=privateKey.export({type:'pkcs8',format:'pem'}), PEM1=privateKey.export({type:'pkcs1',format:'pem'});
const KEY=Buffer.alloc(32,7).toString('base64');
const SECRETS=['rt-secret-','ya29.at-','gho_user','ghs_inst','code-g-','gh-code-','client-secret'];

function fakeR2(){const store=new Map();return{store,async put(k,b,o){store.set(k,{bytes:new Uint8Array(b),opts:o});},
  async get(k){const o=store.get(k);if(!o)return null;return{size:o.bytes.length,body:new Blob([o.bytes]).stream(),arrayBuffer:async()=>o.bytes.slice().buffer};},async delete(k){for(const x of [].concat(k))store.delete(x);}};}

/* ---- fake Google ---- */
function google(){
  const files=new Map(),calls=[],revoked=[];let n=0,codes=new Map(),refreshes=0;
  const json=(v,s=200)=>new Response(JSON.stringify(v),{status:s,headers:{'Content-Type':'application/json'}});
  const add=f=>{const id='drv'+String(++n).padStart(10,'0');files.set(id,{id,trashed:false,modifiedTime:'2026-11-20T00:00:00Z',...f});return id;};
  const meta=f=>({id:f.id,name:f.name,mimeType:f.mimeType,size:f.bytes?String(f.bytes.length):undefined,parents:f.parents,trashed:f.trashed,appProperties:f.appProperties,modifiedTime:f.modifiedTime});
  async function handle(u,init){
    const method=init.method||'GET';calls.push([method,u.href]);
    if(u.host==='oauth2.googleapis.com'&&u.pathname==='/token'){
      const fm=new URLSearchParams(init.body);
      assert.equal(fm.get('client_secret'),'client-secret-g');
      if(fm.get('grant_type')==='authorization_code'){
        const c=codes.get(fm.get('code'));if(!c)return json({error:'invalid_grant'},400);codes.delete(fm.get('code'));
        assert.equal(fm.get('redirect_uri'),googleRedirectUri({}));
        assert.equal(b64u(createHash('sha256').update(fm.get('code_verifier')).digest()),c.challenge,'PKCE verifier matches the challenge');
        return json({access_token:'ya29.at-1',refresh_token:c.noRefresh?undefined:'rt-secret-1',expires_in:3599,scope:c.scope});
      }
      if(fm.get('grant_type')==='refresh_token'){refreshes++;if(fm.get('refresh_token')!=='rt-secret-1')return json({error:'invalid_grant'},400);return json({access_token:'ya29.at-'+(++n),expires_in:3599});}
    }
    if(u.host==='oauth2.googleapis.com'&&u.pathname==='/revoke'){revoked.push(new URLSearchParams(init.body).get('token'));return json({});}
    if(u.host==='openidconnect.googleapis.com')return json({email:'alice@example.com',sub:'1'});
    assert.match(init.headers.Authorization,/^Bearer ya29\.at-/);
    let m;
    if(u.pathname==='/drive/v3/files'&&method==='GET'){
      const q=u.searchParams.get('q');
      if(/appProperties has/.test(q))return json({files:[...files.values()].filter(f=>f.appProperties?.haslalab==='root'&&!f.trashed).map(f=>({id:f.id}))});
      const parent=/'([^']+)' in parents/.exec(q)[1];
      return json({files:[...files.values()].filter(f=>f.parents?.[0]===parent&&!f.trashed).map(meta)});
    }
    if(u.pathname==='/drive/v3/files'&&method==='POST'){const b=JSON.parse(init.body);return json({id:add({name:b.name,mimeType:b.mimeType,parents:b.parents||['root'],appProperties:b.appProperties})});}
    if(u.pathname==='/upload/drive/v3/files'&&method==='POST'){
      const raw=Buffer.from(init.body),s=raw.toString('latin1'),boundary=/boundary=(\S+)/.exec(init.headers['Content-Type'])[1];
      const parts=s.split('--'+boundary),metaJson=JSON.parse(Buffer.from(parts[1].split('\r\n\r\n')[1].trim(),'latin1').toString('utf8'));
      const body=parts[2].slice(parts[2].indexOf('\r\n\r\n')+4,-2);
      return json({id:add({name:metaJson.name,mimeType:'application/octet-stream',parents:metaJson.parents,bytes:Buffer.from(body,'latin1')})});
    }
    if((m=/^\/drive\/v3\/files\/([^/]+)$/.exec(u.pathname))){
      const f=files.get(decodeURIComponent(m[1]));if(!f)return json({error:{code:404}},404);
      if(method==='GET'&&u.searchParams.get('alt')==='media')return new Response(f.bytes);
      if(method==='GET')return json(meta(f));
      if(method==='PATCH'){Object.assign(f,JSON.parse(init.body));return json({id:f.id});}
    }
    throw new Error('unexpected google call '+method+' '+u.href);
  }
  return {files,calls,revoked,codes,add,handle,get refreshes(){return refreshes;}};
}

/* ---- fake GitHub ---- */
function github(){
  const calls=[],tokenRequests=[],revoked=[],repoFiles=new Map(),puts=[];let users=new Map(),insts=[];
  const json=(v,s=200)=>new Response(JSON.stringify(v),{status:s,headers:{'Content-Type':'application/json'}});
  const repos=[{id:501,full_name:'alice/notes',private:true,default_branch:'main'},{id:502,full_name:'alice/site',private:false,default_branch:'trunk'}];
  async function handle(u,init){
    const method=init.method||'GET';calls.push([method,u.href,init]);
    if(u.host==='github.com'&&u.pathname==='/login/oauth/access_token'){const b=JSON.parse(init.body);assert.equal(b.client_secret,'client-secret-gh');assert.equal(b.redirect_uri,githubRedirectUri({}));
      const who=users.get(b.code);if(!who)return json({error:'bad_verification_code'});users.delete(b.code);return json({access_token:'gho_user_'+who});}
    if(u.pathname==='/user')return json({login:/gho_user_(\w+)/.exec(init.headers.Authorization)[1]});
    if(u.pathname==='/user/installations'){const who=/gho_user_(\w+)/.exec(init.headers.Authorization)[1];return json({installations:insts.filter(i=>i.users.includes(who)).map(({users,...i})=>i)});}
    if((u.pathname.startsWith('/applications/'))&&method==='DELETE'){revoked.push(JSON.parse(init.body).access_token);return new Response(null,{status:204});}
    let m;
    if((m=/^\/app\/installations\/(\d+)\/access_tokens$/.exec(u.pathname))){
      const jwt=init.headers.Authorization.slice(7),[h,p,s]=jwt.split('.');
      assert.ok(nodeVerify('sha256',Buffer.from(h+'.'+p),publicKey,Buffer.from(s,'base64url')),'the App JWT verifies with the public key');
      const body=JSON.parse(init.body);tokenRequests.push({inst:+m[1],...body});
      if(!insts.some(i=>i.id===+m[1]))return json({message:'Not Found'},404);
      if(body.repository_ids&&!body.repository_ids.every(id=>repos.some(r=>r.id===id)))return json({message:'nope'},422);
      return json({token:'ghs_inst_'+tokenRequests.length,expires_at:new Date(Date.now()+3600e3).toISOString()});
    }
    assert.match(init.headers.Authorization,/^Bearer ghs_inst_/);
    if(u.pathname==='/installation/repositories')return json({repositories:repos});
    if((m=/^\/repos\/alice\/notes\/contents\/(.*)$/.exec(u.pathname))){
      const path=decodeURIComponent(m[1]);
      if(method==='GET'){
        if(repoFiles.has(path)){const f=repoFiles.get(path);
          if(init.headers.Accept==='application/vnd.github.raw')return new Response(f.bytes);
          return json({type:'file',name:path.split('/').pop(),path,size:f.bytes.length,sha:f.sha});}
        const kids=[...repoFiles.keys()].filter(k=>k.startsWith(path+'/'));
        if(!kids.length)return json({message:'Not Found'},404);
        const seen=new Map();for(const k of kids){const rest=k.slice(path.length+1),top=rest.split('/')[0];seen.set(top,rest.includes('/')?{type:'dir',name:top,path:path+'/'+top}:{type:'file',name:top,path:k,size:repoFiles.get(k).bytes.length,sha:repoFiles.get(k).sha});}
        return json([...seen.values()]);
      }
      if(method==='PUT'){const b=JSON.parse(init.body);puts.push({path,...b});const old=repoFiles.get(path);if(old&&b.sha!==old.sha)return json({message:'sha'},409);
        const sha='sha'+puts.length;repoFiles.set(path,{bytes:Buffer.from(b.content,'base64'),sha});return json({content:{sha,path}},old?200:201);}
      if(method==='DELETE'){const b=JSON.parse(init.body);puts.push({path,del:true,...b});const old=repoFiles.get(path);if(!old||old.sha!==b.sha)return json({},409);repoFiles.delete(path);return json({});}
    }
    throw new Error('unexpected github call '+method+' '+u.href);
  }
  return {calls,tokenRequests,revoked,repoFiles,puts,handle,users,setInsts:l=>{insts=l;},repos};
}

function setup({configured=true,pem=PEM8}={}){
  const db=new DatabaseSync(':memory:');
  const D1={prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){const r=db.prepare(sql).get(...args);return r?{...r}:null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{changes:r.changes}};}};}};
  db.exec('CREATE TABLE workshop_files (id TEXT PRIMARY KEY, owner_id INTEGER NOT NULL, folder TEXT NOT NULL DEFAULT \'\', name TEXT NOT NULL, size INTEGER NOT NULL, mime TEXT NOT NULL, r2_key TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)');
  const G=google(),GH=github(),limits=[];let t=1_800_000_000;
  const fetchImpl=async(url,init={})=>{const u=new URL(url);return /googleapis\.com$/.test(u.host)?G.handle(u,init):GH.handle(u,init);};
  const env={DB:D1,LAB_PAGES:fakeR2(),ALLOWED_ORIGINS:'https://haslalab.org,http://localhost:8765',
    ...(configured?{GOOGLE_CLIENT_ID:'gid',GOOGLE_CLIENT_SECRET:'client-secret-g',WORKSHOP_TOKEN_KEY:KEY,
      GITHUB_APP_ID:'77',GITHUB_APP_SLUG:'haslalab-storage',GITHUB_APP_CLIENT_ID:'Iv1.abc',GITHUB_APP_CLIENT_SECRET:'client-secret-gh',GITHUB_APP_PRIVATE_KEY:pem}:{})};
  const route=createWorkshopConnectorsRouter({HttpError:H,bad,now:()=>t,fetchImpl,needUser:u=>{if(!u)throw new H(401,'login_required');return u;},limit:async(e,k,max,w)=>{limits.push([k,max,w]);}});
  const responses=[];
  const keep=r=>{responses.push(r instanceof Response?'':JSON.stringify(r));return r;};
  const call=async(p,m,body,me,extra='')=>keep(await route(p,m,body,me,new Request('https://haslalab-community.haslalab.workers.dev'+p+extra,{method:m==='HEAD'?'GET':m}),env));
  const form=async(p,me,name,bytes,fields={})=>{const fd=new FormData();fd.set('file',new File([bytes],name));for(const [k,v] of Object.entries(fields))fd.set(k,v);
    return keep(await route(p,'POST',{},me,new Request('https://x.test'+p,{method:'POST',body:fd}),env));};
  const visit=async url=>{const u=new URL(url);const r=await route(u.pathname,'GET',null,null,new Request(url),env);responses.push(r.headers.get('Location')||'');return r;};
  return {db,env,G,GH,route,call,form,visit,limits,responses,tick:s=>{t+=s;},fetchImpl};
}
const alice={id:7},bob={id:8};
const fails=async(p,code,status)=>assert.rejects(p,e=>e.code===code&&(status==null||e.status===status));
const pdf=()=>Buffer.concat([Buffer.from('%PDF-1.7\n'),Buffer.alloc(50,0x20),Buffer.from('\n%%EOF\n')]);
const noSecrets=(S,extra=[])=>{const all=S.responses.join('\n');for(const s of [...SECRETS,...extra])assert.ok(!all.includes(s),'no response carries '+s);};

/* Google: start, Google's callback, the site's finish */
async function connectDrive(S,me=alice,{scope=`openid email ${DRIVE_SCOPE}`,noRefresh=false}={}){
  const {url}=await S.call('/api/workshop/connectors/google/start','POST',{return:'https://haslalab.org/'},me);
  const u=new URL(url),state=u.searchParams.get('state'),code='code-g-'+Math.random().toString(36).slice(2);
  S.G.codes.set(code,{challenge:u.searchParams.get('code_challenge'),scope,noRefresh});
  const cb=await S.visit(`${CONNECTOR_ORIGIN}/api/workshop/connectors/google/callback?state=${state}&code=${code}`);
  const loc=cb.headers.get('Location')||'',ticket=new URLSearchParams(loc.split('?')[1]||'').get('ticket');
  return {url:u,state,code,cb,loc,ticket};
}

test('not configured: the status says so, and every route answers not_configured',async()=>{
  const S=setup({configured:false});
  const st=await S.call('/api/workshop/connectors','GET',null,alice);
  assert.deepEqual([st.drive.configured,st.drive.connected,st.github.configured,st.github.connected],[false,false,false,false]);
  await fails(S.call('/api/workshop/connectors/google/start','POST',{return:'https://haslalab.org/'},alice),'not_configured',503);
  await fails(S.call('/api/workshop/connectors/github/start','POST',{return:'https://haslalab.org/'},alice),'not_configured',503);
  await fails(S.call('/api/workshop/connectors/drive/files','GET',null,alice),'not_configured',503);
  await fails(S.call('/api/workshop/connectors/github/repos','GET',null,alice),'not_configured',503);
  assert.equal((await S.visit(CONNECTOR_ORIGIN+'/api/workshop/connectors/google/callback?state=x&code=y')).status,503);
  await fails(S.call('/api/workshop/connectors','GET',null,null),'login_required',401);
  assert.equal(await S.call('/api/workshop/storage','GET',null,alice),undefined,'other paths are left to other routers');
  /* a key of the wrong length is not a key */
  const T=setup();T.env.WORKSHOP_TOKEN_KEY=Buffer.alloc(16).toString('base64');
  assert.equal((await T.call('/api/workshop/connectors','GET',null,alice)).drive.configured,false);
});

test('callback addresses: one fixed origin, overridable only by an https origin',()=>{
  assert.equal(googleRedirectUri({}),'https://haslalab-community.haslalab.workers.dev/api/workshop/connectors/google/callback');
  assert.equal(githubRedirectUri({}),'https://haslalab-community.haslalab.workers.dev/api/workshop/connectors/github/callback');
  assert.equal(connectorOrigin({WORKSHOP_CONNECTOR_ORIGIN:'https://api.example.org/'}),'https://api.example.org');
  for(const v of ['http://api.example.org','https://api.example.org/x','javascript:alert(1)'])assert.equal(connectorOrigin({WORKSHOP_CONNECTOR_ORIGIN:v}),CONNECTOR_ORIGIN,v);
  const env={ALLOWED_ORIGINS:'https://haslalab.org,http://localhost:8765'};
  assert.equal(allowedReturn(env,'https://haslalab.org/ko/?x=1#/a'),'https://haslalab.org/ko/');
  for(const v of ['http://localhost:8765/','https://evil.example/','https://haslalab.org.evil.example/'])assert.equal(allowedReturn(env,v),null,v);
});

test('Google: drive.file with PKCE and offline access; the state is single use, bound to the member and short-lived',async()=>{
  const S=setup();
  await fails(S.call('/api/workshop/connectors/google/start','POST',{return:'https://evil.example/'},alice),'bad_return');
  const a=await connectDrive(S);
  assert.equal(a.url.origin+a.url.pathname,'https://accounts.google.com/o/oauth2/v2/auth');
  const q=a.url.searchParams;
  assert.equal(q.get('scope'),`openid email ${DRIVE_SCOPE}`,'drive.file is the only Drive scope');
  assert.deepEqual([q.get('code_challenge_method'),q.get('access_type'),q.get('include_granted_scopes'),q.get('prompt'),q.get('redirect_uri'),q.get('response_type')],
    ['S256','offline','true','consent',googleRedirectUri({}),'code']);
  assert.equal(S.db.prepare('SELECT COUNT(*) n FROM workshop_connector_states WHERE state_hash=?').get(a.state).n,0,'the state itself is not stored, only its hash');
  assert.equal(a.cb.status,302);assert.match(a.loc,/^https:\/\/haslalab\.org\/#\/workshop\/storage\?connector=google&ticket=[A-Za-z0-9_-]+$/);
  assert.ok(!a.loc.includes(a.code),'the code does not go back to the site');
  assert.ok(!JSON.stringify(S.db.prepare('SELECT * FROM workshop_connector_states').all()).includes(a.code),'the code is kept sealed');
  /* the same state again */
  const again=await S.visit(`${CONNECTOR_ORIGIN}/api/workshop/connectors/google/callback?state=${a.state}&code=${a.code}`);
  assert.equal(again.status,400);assert.equal(again.headers.get('Location'),null);
  /* someone else's ticket: refused, and it is gone */
  await fails(S.call('/api/workshop/connectors/finish','POST',{ticket:a.ticket},bob),'wrong_user',403);
  await fails(S.call('/api/workshop/connectors/finish','POST',{ticket:a.ticket},alice),'bad_ticket',400);
  assert.equal((await S.call('/api/workshop/connectors','GET',null,bob)).drive.connected,false);
  /* an expired state */
  const {url}=await S.call('/api/workshop/connectors/google/start','POST',{return:'https://haslalab.org/'},alice);
  S.tick(601);
  const late=await S.visit(`${CONNECTOR_ORIGIN}/api/workshop/connectors/google/callback?state=${new URL(url).searchParams.get('state')}&code=code-g-late`);
  assert.match(late.headers.get('Location'),/connector=google&error=expired$/);
  /* an expired ticket */
  const b=await connectDrive(S);S.tick(601);
  await fails(S.call('/api/workshop/connectors/finish','POST',{ticket:b.ticket},alice),'expired');
  /* cancelled at Google */
  const {url:u3}=await S.call('/api/workshop/connectors/google/start','POST',{return:'https://haslalab.org/'},alice);
  const c=await S.visit(`${CONNECTOR_ORIGIN}/api/workshop/connectors/google/callback?state=${new URL(u3).searchParams.get('state')}&error=access_denied`);
  assert.match(c.headers.get('Location'),/error=cancelled$/);
  /* an unknown state */
  assert.equal((await S.visit(`${CONNECTOR_ORIGIN}/api/workshop/connectors/google/callback?state=${'x'.repeat(40)}&code=z`)).status,400);
  /* Drive unticked on Google's consent screen */
  const d=await connectDrive(S,alice,{scope:'openid email'});
  await fails(S.call('/api/workshop/connectors/finish','POST',{ticket:d.ticket},alice),'drive_scope_missing');
  assert.ok(S.G.revoked.includes('rt-secret-1'),'a grant without Drive is revoked');
  assert.ok(S.limits.some(([k])=>k==='wsc-start:7')&&S.limits.some(([k])=>k==='wsc-finish:7'));
});

test('Google: tokens are sealed with AES-GCM in D1 and never reach a response',async()=>{
  const S=setup();
  const a=await connectDrive(S);
  const fin=await S.call('/api/workshop/connectors/finish','POST',{ticket:a.ticket},alice);
  assert.deepEqual(fin,{provider:'google',connected:true,email:'alice@example.com'});
  const r=S.db.prepare("SELECT * FROM workshop_connectors WHERE user_id=7 AND provider='google'").get();
  assert.match(r.refresh_enc,/^v1\./);assert.ok(!JSON.stringify(r).includes('rt-secret')&&!JSON.stringify(r).includes('ya29'),'no token in plaintext');
  assert.equal(await openToken(S.env,r.refresh_enc,'drive-refresh:7'),'rt-secret-1','round trip');
  await assert.rejects(openToken(S.env,r.refresh_enc,'drive-refresh:8'),'bound to the member: another row cannot use it');
  await assert.rejects(openToken({WORKSHOP_TOKEN_KEY:Buffer.alloc(32,9).toString('base64')},r.refresh_enc,'drive-refresh:7'),'useless without the key');
  const s1=await sealToken(S.env,'x','a'),s2=await sealToken(S.env,'x','a');assert.notEqual(s1,s2,'a fresh IV each time');
  const root=[...S.G.files.values()].find(f=>f.appProperties?.haslalab==='root');
  assert.equal(root.name,'HaslaLab');assert.equal(r.root_id,root.id);
  const st=await S.call('/api/workshop/connectors','GET',null,alice);
  assert.deepEqual(st.drive,{configured:true,connected:true,email:'alice@example.com'});
  noSecrets(S);
});

test('Drive: list, upload, download, rename, trash and copy, only inside the HaslaLab folder',async()=>{
  const S=setup();
  const a=await connectDrive(S);await S.call('/api/workshop/connectors/finish','POST',{ticket:a.ticket},alice);
  await fails(S.call('/api/workshop/connectors/drive/files','GET',null,bob),'not_connected',409);
  const root=(await S.call('/api/workshop/connectors/drive/files','GET',null,alice)).root;
  const up=await S.form('/api/workshop/connectors/drive/files',alice,'시험지.pdf',pdf());
  assert.equal(up.file.name,'시험지.pdf');
  await fails(S.form('/api/workshop/connectors/drive/files',alice,'run.exe',Buffer.from('MZ')),'type_not_allowed',415);
  await fails(S.form('/api/workshop/connectors/drive/files',alice,'fake.png',Buffer.from('<html>')),'type_mismatch',415);
  const {folder}=await S.call('/api/workshop/connectors/drive/folders','POST',{name:'실험',parent:root},alice);
  assert.equal(S.G.files.get(folder.id).appProperties.haslalab,'folder');
  const list=await S.call('/api/workshop/connectors/drive/files','GET',null,alice);
  assert.deepEqual(list.files.map(f=>[f.name,f.folder]).sort(),[['시험지.pdf',false],['실험',true]]);
  const sub=await S.call('/api/workshop/connectors/drive/files','GET',null,alice,'?folder='+folder.id);
  assert.deepEqual(sub.trail.map(x=>x.name),['HaslaLab','실험']);
  const dl=await S.call('/api/workshop/connectors/drive/files/'+up.file.id,'GET',null,alice);
  assert.match(dl.headers.get('Content-Disposition'),/^attachment/);assert.equal(dl.headers.get('Content-Type'),'application/pdf');
  assert.deepEqual(Buffer.from(await dl.arrayBuffer()),pdf());
  /* a file elsewhere in the member's Drive (the app picked it once, outside the folder) is out of reach */
  const outside=S.G.add({name:'diary.pdf',mimeType:'application/pdf',parents:['root'],bytes:pdf()});
  await fails(S.call('/api/workshop/connectors/drive/files/'+outside,'GET',null,alice),'not_found',404);
  await fails(S.call('/api/workshop/connectors/drive/files/'+outside,'DELETE',null,alice),'not_found',404);
  await fails(S.call('/api/workshop/connectors/drive/files','GET',null,alice,'?folder='+outside),'not_found');
  await fails(S.call('/api/workshop/connectors/drive/files/'+root,'DELETE',null,alice),'root_folder',403);
  const rn=await S.call('/api/workshop/connectors/drive/files/'+up.file.id,'PATCH',{name:'중간고사'},alice);
  assert.equal(rn.file.name,'중간고사.pdf','the extension stays');
  /* copies both ways */
  const toStore=await S.call('/api/workshop/connectors/drive/copy','POST',{direction:'to_storage',id:up.file.id,folder:''},alice);
  assert.equal(toStore.file.name,'중간고사.pdf');
  assert.equal(S.db.prepare('SELECT COUNT(*) n FROM workshop_files WHERE owner_id=7').get().n,1);
  const toDrive=await S.call('/api/workshop/connectors/drive/copy','POST',{direction:'to_drive',file_id:toStore.file.id,folder:folder.id},alice);
  assert.equal(S.G.files.get(toDrive.file.id).parents[0],folder.id);
  await fails(S.call('/api/workshop/connectors/drive/copy','POST',{direction:'to_drive',file_id:toStore.file.id},bob),'not_connected');
  await S.call('/api/workshop/connectors/drive/files/'+up.file.id,'DELETE',null,alice);
  assert.equal(S.G.files.get(up.file.id).trashed,true,'deleted means moved to the Drive trash');
  /* an expired access token is refreshed with the sealed refresh token */
  S.tick(4000);const before=S.G.refreshes;
  await S.call('/api/workshop/connectors/drive/files','GET',null,alice);assert.equal(S.G.refreshes,before+1);
  noSecrets(S);
});

test('Drive: disconnecting and deleting the account revoke the token at Google',async()=>{
  const S=setup();
  const a=await connectDrive(S);await S.call('/api/workshop/connectors/finish','POST',{ticket:a.ticket},alice);
  await S.call('/api/workshop/connectors/google','DELETE',null,alice);
  assert.deepEqual(S.G.revoked,['rt-secret-1']);
  assert.equal(S.db.prepare('SELECT COUNT(*) n FROM workshop_connectors').get().n,0);
  assert.equal((await S.call('/api/workshop/connectors','GET',null,alice)).drive.connected,false);
  const b=await connectDrive(S);await S.call('/api/workshop/connectors/finish','POST',{ticket:b.ticket},alice);
  S.db.prepare("INSERT INTO workshop_connectors(user_id,provider,installation_id,created_at,updated_at) VALUES(7,'github',11,0,0)").run();
  await workshopConnectorsForgetUser(S.env,7,{fetchImpl:S.fetchImpl});
  assert.deepEqual(S.G.revoked,['rt-secret-1','rt-secret-1']);
  assert.equal(S.db.prepare('SELECT COUNT(*) n FROM workshop_connectors').get().n,0);
  assert.equal(S.db.prepare('SELECT COUNT(*) n FROM workshop_connector_states WHERE user_id=7').get().n,0);
});

async function connectGithub(S,me=alice,{inst=11,who='alice',withCode=true}={}){
  const {url}=await S.call('/api/workshop/connectors/github/start','POST',{return:'https://haslalab.org/'},me);
  const state=new URL(url).searchParams.get('state'),code='gh-code-'+Math.random().toString(36).slice(2);S.GH.users.set(code,who);
  const cb=await S.visit(`${CONNECTOR_ORIGIN}/api/workshop/connectors/github/callback?${withCode?'code='+code+'&':''}installation_id=${inst}&setup_action=install&state=${state}`);
  const loc=cb.headers.get('Location')||'';
  return {url:new URL(url),state,code,cb,loc,ticket:new URLSearchParams(loc.split('?')[1]||'').get('ticket')};
}

test('GitHub: the installation must belong to the GitHub user who came back, and the link to the member who started',async()=>{
  const S=setup();
  S.GH.setInsts([{id:11,app_id:77,account:{login:'alice',type:'User'},users:['alice']},{id:12,app_id:77,account:{login:'mallory',type:'User'},users:['mallory']},
    {id:13,app_id:99,account:{login:'alice',type:'User'},users:['alice']}]);
  const a=await connectGithub(S);
  assert.equal(a.url.href.split('?')[0],'https://github.com/apps/haslalab-storage/installations/new');
  assert.match(a.loc,/^https:\/\/haslalab\.org\/#\/workshop\/storage\?connector=github&ticket=/);
  assert.deepEqual(S.GH.revoked,['gho_user_alice'],'the user token is revoked right after the check');
  await fails(S.call('/api/workshop/connectors/finish','POST',{ticket:a.ticket},bob),'wrong_user',403);
  /* someone else's installation id */
  const m=await connectGithub(S,alice,{inst:12});
  assert.match(m.loc,/error=not_your_installation$/);
  /* another App's installation */
  assert.match((await connectGithub(S,alice,{inst:13})).loc,/error=not_your_installation$/);
  /* reusing a state */
  const again=await S.visit(`${CONNECTOR_ORIGIN}/api/workshop/connectors/github/callback?code=x&installation_id=11&state=${a.state}`);
  assert.equal(again.status,400);
  /* without "authorize during installation": the callback asks GitHub for the authorization, keeping the state */
  const n=await connectGithub(S,alice,{withCode:false});
  const go=new URL(n.loc);
  assert.equal(go.origin+go.pathname,'https://github.com/login/oauth/authorize');
  assert.equal(go.searchParams.get('state'),n.state);assert.equal(go.searchParams.get('redirect_uri'),githubRedirectUri({}));
  const code='gh-code-2';S.GH.users.set(code,'alice');
  const cb2=await S.visit(`${CONNECTOR_ORIGIN}/api/workshop/connectors/github/callback?code=${code}&state=${n.state}`);
  const t2=new URLSearchParams(cb2.headers.get('Location').split('?')[1]).get('ticket');
  const fin=await S.call('/api/workshop/connectors/finish','POST',{ticket:t2},alice);
  assert.deepEqual(fin,{provider:'github',connected:true,account:'alice'});
  const st=(await S.call('/api/workshop/connectors','GET',null,alice)).github;
  assert.deepEqual(st,{configured:true,connected:true,account:'alice',repo:null,folder:null,manage_url:'https://github.com/settings/installations/11'});
  /* an install whose redirect carried no state: nothing is linked, the site resumes with a plain authorization */
  const lost=await S.visit(`${CONNECTOR_ORIGIN}/api/workshop/connectors/github/callback?code=gh-code-x&installation_id=11&setup_action=install`);
  assert.equal(lost.headers.get('Location'),'https://haslalab.org/#/workshop/storage?connector=github&resume=1');
  const {url:au}=await S.call('/api/workshop/connectors/github/start','POST',{return:'https://haslalab.org/',authorize:true},alice);
  const auu=new URL(au);assert.equal(auu.origin+auu.pathname,'https://github.com/login/oauth/authorize');
  S.GH.users.set('gh-code-3','alice');
  const cb3=await S.visit(`${CONNECTOR_ORIGIN}/api/workshop/connectors/github/callback?code=gh-code-3&state=${auu.searchParams.get('state')}`);
  const t3=new URLSearchParams(cb3.headers.get('Location').split('?')[1]).get('ticket');
  assert.equal((await S.call('/api/workshop/connectors/finish','POST',{ticket:t3},alice)).account,'alice','the installation on the user\'s own account');
  /* an install an org owner must approve */
  const {url}=await S.call('/api/workshop/connectors/github/start','POST',{return:'https://haslalab.org/'},alice);
  const rq=await S.visit(`${CONNECTOR_ORIGIN}/api/workshop/connectors/github/callback?setup_action=request&state=${new URL(url).searchParams.get('state')}`);
  assert.match(rq.headers.get('Location'),/error=install_requested$/);
  noSecrets(S);
});

test('GitHub: one repository, its folder only; tokens narrowed to that repository; commits say HaslaLab',async()=>{
  for(const pem of [PEM8,PEM1]){
    const S=setup({pem});
    S.GH.setInsts([{id:11,app_id:77,account:{login:'alice',type:'User'},users:['alice']}]);
    const a=await connectGithub(S);await S.call('/api/workshop/connectors/finish','POST',{ticket:a.ticket},alice);
    await fails(S.call('/api/workshop/connectors/github/files','GET',null,alice),'repo_not_chosen',409);
    const {repos}=await S.call('/api/workshop/connectors/github/repos','GET',null,alice);
    assert.deepEqual(repos.map(r=>r.full_name),['alice/notes','alice/site']);
    assert.deepEqual(S.GH.tokenRequests[0],{inst:11,permissions:{metadata:'read'}},'listing repositories needs metadata only');
    await fails(S.call('/api/workshop/connectors/github/repo','POST',{repo_id:999},alice),'github_repo_not_allowed',403);
    await fails(S.call('/api/workshop/connectors/github/repo','POST',{repo_id:501,folder:'../x'},alice),'bad_path');
    await fails(S.call('/api/workshop/connectors/github/repo','POST',{repo_id:501,folder:'.github/workflows'},alice),'bad_path');
    assert.deepEqual(await S.call('/api/workshop/connectors/github/repo','POST',{repo_id:501},alice),{repo:'alice/notes',folder:'haslalab'});
    const up=await S.form('/api/workshop/connectors/github/files',alice,'report 1.pdf',pdf(),{path:'lab'});
    assert.equal(up.file.path,'lab/report 1.pdf');
    const put=S.GH.puts.at(-1);
    assert.equal(put.path,'haslalab/lab/report 1.pdf');assert.equal(put.message,'HaslaLab: add report 1.pdf');assert.equal(put.sha,undefined);assert.equal(put.branch,'main');
    assert.deepEqual(Buffer.from(put.content,'base64'),pdf());
    const w=S.GH.tokenRequests.at(-1);
    assert.deepEqual(w,{inst:11,repository_ids:[501],permissions:{contents:'write',metadata:'read'}},'a write token for the one repository');
    await S.form('/api/workshop/connectors/github/files',alice,'report 1.pdf',pdf(),{path:'lab'});
    assert.equal(S.GH.puts.at(-1).sha,'sha1','an update sends the sha');assert.equal(S.GH.puts.at(-1).message,'HaslaLab: update report 1.pdf');
    await fails(S.form('/api/workshop/connectors/github/files',alice,'a.pdf',pdf(),{path:'../../.github'}),'bad_path');
    await fails(S.form('/api/workshop/connectors/github/files',alice,'run.exe',Buffer.from('MZ'),{path:''}),'type_not_allowed',415);
    const ls=await S.call('/api/workshop/connectors/github/files','GET',null,alice);
    assert.deepEqual(ls.files,[{name:'lab',path:'lab',folder:true,size:null}]);
    const ls2=await S.call('/api/workshop/connectors/github/files','GET',null,alice,'?path=lab');
    assert.deepEqual(ls2.files.map(x=>x.path),['lab/report 1.pdf']);
    assert.ok(S.GH.tokenRequests.some(r=>r.permissions.contents==='read'&&r.repository_ids?.[0]===501),'reads use a read-only token');
    const dl=await S.call('/api/workshop/connectors/github/file','GET',null,alice,'?path='+encodeURIComponent('lab/report 1.pdf'));
    assert.deepEqual(Buffer.from(await dl.arrayBuffer()),pdf());assert.match(dl.headers.get('Content-Disposition'),/^attachment/);
    await fails(S.call('/api/workshop/connectors/github/file','GET',null,alice,'?path='+encodeURIComponent('../README.md')),'bad_path');
    /* copies */
    const toStore=await S.call('/api/workshop/connectors/github/copy','POST',{direction:'to_storage',path:'lab/report 1.pdf',folder:''},alice);
    assert.equal(toStore.file.name,'report 1.pdf');
    await S.call('/api/workshop/connectors/github/copy','POST',{direction:'to_github',file_id:toStore.file.id,path:'copies'},alice);
    assert.equal(S.GH.puts.at(-1).path,'haslalab/copies/report 1.pdf');assert.match(S.GH.puts.at(-1).message,/^HaslaLab: add report 1\.pdf \(from storage\)$/);
    await S.call('/api/workshop/connectors/github/file','DELETE',null,alice,'?path='+encodeURIComponent('lab/report 1.pdf'));
    assert.equal(S.GH.puts.at(-1).message,'HaslaLab: delete report 1.pdf');assert.equal(S.GH.repoFiles.has('haslalab/lab/report 1.pdf'),false);
    /* disconnect: the stored installation goes; the site shows where to uninstall */
    const d=await S.call('/api/workshop/connectors/github','DELETE',null,alice);
    assert.equal(d.manage_url,'https://github.com/settings/installations/11');
    assert.equal((await S.call('/api/workshop/connectors','GET',null,alice)).github.connected,false);
    noSecrets(S);
  }
});

test('the App JWT is RS256 and verifies with the App public key; PKCS#1 keys are accepted',async()=>{
  for(const pem of [PEM8,PEM1,PEM1.replace(/\n/g,'\\n')]){
    const jwt=await githubAppJwt({GITHUB_APP_ID:'77',GITHUB_APP_PRIVATE_KEY:pem},1_800_000_000);
    const [h,p,s]=jwt.split('.');
    assert.deepEqual(JSON.parse(Buffer.from(h,'base64url')),{alg:'RS256',typ:'JWT'});
    assert.deepEqual(JSON.parse(Buffer.from(p,'base64url')),{iat:1_800_000_000-60,exp:1_800_000_000+540,iss:'77'});
    assert.ok(nodeVerify('sha256',Buffer.from(h+'.'+p),publicKey,Buffer.from(s,'base64url')));
  }
  const der1=privateKey.export({type:'pkcs1',format:'der'}),der8=privateKey.export({type:'pkcs8',format:'der'});
  assert.deepEqual(Buffer.from(pkcs1ToPkcs8(new Uint8Array(der1))),der8,'the PKCS#1 wrap is the PKCS#8 encoding');
});

test('GitHub paths: no "..", no leading "/", no dot folders, a bounded depth and alphabet',()=>{
  for(const [v,want] of [['haslalab','haslalab'],['haslalab/','haslalab'],['a/b c/실험(1)','a/b c/실험(1)'],['','']])assert.equal(cleanGhPath(v),want,v);
  for(const v of ['../x','a/../b','/etc','a//b','.github/workflows','a/.git','a\\b','a/b.','x/'+'a'.repeat(81),Array(9).fill('a').join('/'),'a\u0000b','a/b:c','a/*',42])
    assert.equal(cleanGhPath(v),null,String(v));
  assert.equal(cleanGhPath('',{allowEmpty:false}),null);
  assert.equal(ghFileName('../.env#1.pdf','pdf'),'_env_1.pdf');
  assert.equal(ghFileName('보고서 (최종).pdf','pdf'),'보고서 (최종).pdf');
});
