const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const Runtime=require('../site-runtime.js'),root=path.resolve(__dirname,'..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const html=read('index.html'),main=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].find(m=>m[1].includes('const REL ='))[1];
const metadataScope={window:{}};vm.runInNewContext(read('site-catalogue.js'),metadataScope);const catalogue=metadataScope.window.HL_CATALOGUE;
const plain=v=>JSON.parse(JSON.stringify(v)),tick=()=>new Promise(r=>setImmediate(r));

test('home, subjects, learning and community do not download paper datasets; deep links select only their data',()=>{
  const options={known:Object.keys(catalogue.competitions),theory:catalogue.theoryKeys,versions:catalogue.versions};
  for(const route of ['#/','#/comps/math','#/about','#/learn/physics','#/community','#/community/user/kim'])assert.deepEqual(Runtime.routeNeeds(route,options),[],route);
  assert.deepEqual(Runtime.routeNeeds('#/amc/2026',options),['theory:amc']);
  assert.deepEqual(Runtime.routeNeeds('#/kmo/exam',options),['theory:kmo','contest:kmo']);
  assert.deepEqual(Runtime.routeNeeds('#/kmchc/2025',options),['theory:kmchc','contest:kmchc']);
  assert.deepEqual(Runtime.routeNeeds('#/iypt/2026',options),['iypt']);
  assert.deepEqual(Runtime.routeNeeds('#/usaco/2025',options),['usaco']);
  assert.deepEqual(Runtime.routeNeeds('#/community/login',options),['arena']);
  assert.deepEqual(Runtime.routeNeeds('#/lab/3',options),['arena']);
  assert.equal(Runtime.routeNeeds('#/ruphox/2024',options).filter(x=>x.startsWith('theory:')).length,4);
  for(const source of ['theory.js','contest-exams.js','iypt.js','usaco.js','rupho-selection.js','arena.js'])assert.ok(!new RegExp('<script src="'+source.replace('.','\\.')+'(?:[?"\\s])').test(html),source+' must stay lazy');
});

test('module loads merge simultaneous requests once, retain completed chunks and retry a failed network request',async()=>{
  let calls=0,resolve;const loader=Runtime.createDataLoader({versions:{a:'a.js'},loadScript:()=>{calls++;return new Promise(r=>resolve=r);}});
  const a=loader.ensure(['a']),b=loader.ensure(['a']);await tick();assert.equal(calls,1);resolve();await Promise.all([a,b]);await loader.ensure(['a']);assert.equal(calls,1);
  let fail=true;const retry=Runtime.createDataLoader({versions:{a:'a.js'},loadScript:async()=>{if(fail)throw Error('offline');}});
  await assert.rejects(retry.ensure(['a']));assert.equal(retry.ready(['a']),false);fail=false;await retry.ensure(['a']);assert.equal(retry.ready(['a']),true);
});

function app({preload=false}={}){
  const nodes=new Map(),scripts=[],listeners={},store=new Map();
  const dummy=()=>({innerHTML:'',textContent:'',dataset:{},style:{},classList:{toggle(){},add(){},remove(){}},setAttribute(){},addEventListener(){},querySelector(){return null},querySelectorAll(){return[]},append(){},before(){}});
  const node=id=>{if(!nodes.has(id))nodes.set(id,dummy());return nodes.get(id);};
  const context={window:{HL_RUNTIME:Runtime},URL,URLSearchParams,Blob,console,queueMicrotask,
    location:{hash:'#/',search:''},history:{replaceState(){}},
    document:{getElementById:node,querySelectorAll:()=>[],querySelector:()=>null,createElement:tag=>({...dummy(),tagName:tag,remove(){},isConnected:true}),head:{append:s=>scripts.push(s)},body:dummy(),documentElement:{dataset:{theme:'light'}}},
    localStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)},sessionStorage:{getItem:()=>null,setItem(){},removeItem(){}},
    addEventListener:(event,fn)=>listeners[event]=fn,matchMedia:()=>({matches:false}),setTimeout(){},clearTimeout(){},requestAnimationFrame(){},cancelAnimationFrame(){},scrollTo(){}};
  vm.createContext(context);
  for(const file of ['site-catalogue.js','paper-languages.js','examdur.js','rupho-archive.js','site-design.js'])vm.runInContext(read(file),context,{filename:file});
  context.HLexam=context.window.HLexam||context.HLexam;
  if(preload)for(const file of ['theory.js','contest-exams.js','iypt.js','usaco.js','rupho-selection.js'])vm.runInContext(read(file),context,{filename:file});
  vm.runInContext(main.replace(/\nrender\(\);\s*$/,''),context,{filename:'index-main.js'});
  const run=code=>vm.runInContext(code,context);
  const load=key=>{vm.runInContext(read(catalogue.versions[key].split('?')[0]),context);run('hydrateCatalogue()');};
  return{context,run,load,node,scripts,listeners,store};
}

test('compact metadata preserves all competition names, subject counts and home totals before any paper loads',()=>{
  const lean=app(),full=app({preload:true});
  for(const subject of ['phys','chem','bio','earth','astro','sci','math','info'])assert.equal(lean.run(`viewComps('${subject}')`),full.run(`viewComps('${subject}')`),subject);
  assert.equal(lean.run('Object.keys(THEORY).length'),0);
  assert.equal(lean.run('Object.keys(DATA).length'),catalogue.totals.comps);
  for(const key of ['amc','kmo','kmchc','iypt','usaco'])assert.equal(lean.run(`DATA.${key}.full.en`),full.run(`DATA.${key}.full.en`));
  assert.equal((lean.run('viewComps("phys",4)').match(/class="comp" href=/g)||[]).length,4);
  const home=lean.run('viewOriginalHome()');for(const value of Object.values(catalogue.totals))assert.ok(home.includes('>'+value+'</dd>')||home.includes('>'+value+'</dd>'),String(value));
});

test('individual AMC, KMO and chemistry chunks preserve paper links and scores without loading unrelated subjects',()=>{
  const lean=app(),full=app({preload:true});
  lean.load('theory:amc');assert.deepEqual(plain(lean.run('THEORY.amc')),plain(full.run('THEORY.amc')));assert.equal(lean.run('Object.keys(THEORY).length'),1);
  lean.load('theory:kmo');lean.load('contest:kmo');lean.load('theory:kmchc');lean.load('contest:kmchc');
  assert.deepEqual(plain(lean.run('THEORY.kmo')),plain(full.run('THEORY.kmo')));
  assert.deepEqual(plain(lean.run('THEORY.kmchc')),plain(full.run('THEORY.kmchc')));
  assert.deepEqual(plain(lean.context.window.CONTEST_EXAMS.entries).sort((a,b)=>a.id.localeCompare(b.id)),plain(full.context.window.CONTEST_EXAMS.entries).sort((a,b)=>a.id.localeCompare(b.id)));
  assert.equal(lean.run('DATA.kmo.years.length'),full.run('DATA.kmo.years.length'));
  assert.equal(lean.run('Object.keys(THEORY).length'),3);
});

test('lazy chunks retain every source export, general instructions and corrected KPhE PDF versions',()=>{
  const full={window:{}};vm.runInNewContext(read('theory.js'),full);
  assert.deepEqual(Object.keys(full.window).sort(),['GENERAL','KPHE_PDF_VERSIONS','THEORY','THEORY_META']);
  vm.runInNewContext(read('contest-exams.js'),full);
  const split={window:{}};
  for(const key of catalogue.theoryKeys)vm.runInNewContext(read(catalogue.versions['theory:'+key].split('?')[0]),split);
  for(const key of ['THEORY','THEORY_META','GENERAL','KPHE_PDF_VERSIONS'])assert.deepEqual(plain(split.window[key]),plain(full.window[key]),key);
  const lean=app();lean.load('theory:ipho');lean.load('theory:kphe');
  assert.deepEqual(plain(lean.run('GENERAL.ipho')),plain(full.window.GENERAL.ipho));
  const [file,version]=Object.entries(full.window.KPHE_PDF_VERSIONS)[0];assert.equal(lean.run(`thyUrl(${JSON.stringify(file)})`),file+'?v='+version);
  const [year,entries]=Object.entries(full.window.GENERAL.ipho)[0];const links=lean.run(`genLinks('ipho',{y:${JSON.stringify(year)}})`);assert.ok(links.includes(entries[0][1]),'the year retains its general instructions link');
});

test('resource-only MSKBO stays visible and honest before paper data loads',()=>{
  const lean=app(),full=app({preload:true});
  assert.deepEqual(plain(lean.run('DATA.mskbo.resources')),plain(full.run('DATA.mskbo.resources')));
  assert.equal(lean.run('DATA.mskbo.years.length'),0);
  const page=lean.run('lang="en";viewComp("mskbo")');assert.ok(page.includes('Official sample questions'));assert.ok(page.includes('https://mskbo.bioedu.kr/'));assert.ok(!page.includes('#/mskbo/2026'));
});

test('lazy native papers and year-specific standalone review keep language and mode arguments',()=>{
  const lean=app();for(const key of ['nbpho','eotvos','physcup'])lean.load('theory:'+key);
  lean.run('lang="en";track="thy"');
  const combined=lean.run('viewYear("nbpho",2026,"review")');assert.match(combined,/data-mode="review" data-year="2026"/);assert.ok(combined.includes('review=1'));
  const native=lean.run('viewYear("eotvos",2020,"exam")');assert.ok(native.includes('pl=hu'));assert.ok(native.includes('Eotvos_2020.pdf'));
  const open=lean.run('viewComp("physcup","exam")');assert.ok(open.includes('No time limit'));assert.ok(open.includes('review=1'));assert.equal(/class="ex /.test(open),false);
});

test('async portal hydration retains the selected year and review mode while omitting timed statistics',async()=>{
  const a=app(),calls=[];a.load('theory:nbpho');a.run('lang="en";track="thy"');
  const portal=a.node('xmRoot');Object.assign(portal.dataset,{key:'nbpho',mode:'review',year:'2026'});
  a.context.fetch=async(url)=>{calls.push(url);return{ok:true,json:async()=>url.includes('/lab/stats')?{exams:{}}:{user:null,sessions:[],health:{lab:true,v:5}}};};
  await a.run('xmMount("nbpho")');assert.equal(calls.length,1);assert.ok(calls[0].includes('/lab/bootstrap'));assert.ok(portal.innerHTML.includes('No time limit'));assert.ok(portal.innerHTML.includes('y=2026'));assert.ok(portal.innerHTML.includes('review=1'));assert.ok(!portal.innerHTML.includes('y=2025'));
  calls.length=0;portal.dataset.mode='exam';await a.run('xmMount("nbpho")');assert.equal(calls.length,2);assert.ok(calls.some(url=>url.includes('/lab/stats')));assert.ok(!portal.innerHTML.includes('review=1'));assert.ok(portal.innerHTML.includes('y=2026'));
});

test('loading RuPhO after another archive keeps stages and does not duplicate year problems on repeated hydration',()=>{
  const lean=app(),full=app({preload:true});lean.load('theory:amc');
  for(const key of ['theory:rupho','theory:ruphow','theory:ruphox','theory:ruphoy','rupho'])lean.load(key);
  const before=lean.run('JSON.stringify(DATA.rupho.years)');for(let i=0;i<5;i++)lean.run('hydrateCatalogue()');assert.equal(lean.run('JSON.stringify(DATA.rupho.years)'),before);
  assert.deepEqual(plain(lean.run('DATA.rupho.years')),plain(full.run('DATA.rupho.years')));
  assert.equal(lean.run('RUPHO_ARCHIVE.route("#/ruphox/2024").key'),'ruphox');
});

test('a slow archive load cannot repaint a newer route or undo a language change',async()=>{
  const a=app();a.run('viewAbout=()=>"<about>";buildRails=()=>{};paintSiteTheme=()=>{};cmAccountChip=()=>{};');
  a.context.location.hash='#/kmo';a.run('render()');await tick();assert.equal(a.scripts.length,2);
  a.context.location.hash='#/about';a.run('lang="en";render()');assert.equal(a.node('view').innerHTML,'<about>');
  for(const script of a.scripts){vm.runInContext(read(script.src.split('?')[0]),a.context);script.onload();}
  await tick();await tick();assert.equal(a.node('view').innerHTML,'<about>');assert.equal(a.run('lang'),'en');
});

test('only public invariant reads omit identity and receive a short TTL; balances and results stay live',()=>{
  for(const path of ['/health','/boards?lang=ko','/posts?page=1','/lab/stats?comp=ipho','/pay/config','/lab/contest/catalog'])assert.equal(Runtime.requestPolicy('GET',path).public,true,path);
  for(const path of ['/me','/weekly','/rank','/lab/tokens','/lab/active','/lab/sessions','/lab/sessions/12','/lab/bootstrap?include=sessions,health']){const p=Runtime.requestPolicy('GET',path);assert.equal(p.public,false,path);assert.equal(p.ttl,0,path);}
  assert.equal(Runtime.requestPolicy('GET','/posts/3?view=1').safe,false);
  assert.equal(Runtime.requestPolicy('POST','/posts').safe,false);
});

test('identical safe reads share one request and independent values, with TTL expiry and exact account/base/language separation',async()=>{
  let now=1000,calls=0;const cache=Runtime.createRequestCache({now:()=>now}),state={method:'GET',path:'/posts?lang=ko&page=1',base:'https://a',token:'A',lang:'ko'};
  const send=async()=>({posts:[{id:++calls}]});const [a,b]=await Promise.all([cache.run(state,send),cache.run({...state,path:'/posts?page=1&lang=ko'},send)]);assert.equal(calls,1);a.posts[0].id=99;assert.equal(b.posts[0].id,1);
  assert.equal((await cache.run(state,send)).posts[0].id,1);now+=5001;await cache.run(state,send);assert.equal(calls,2);
  for(const changed of [{token:'B'},{base:'https://b'},{lang:'en'}])await cache.run({...state,...changed},send);assert.equal(calls,5);
  const money={...state,path:'/lab/tokens'};await Promise.all([cache.run(money,send),cache.run(money,send)]);const prior=calls;await cache.run(money,send);assert.equal(calls,prior+1);
});

test('mutations discard racing stale reads and request fresh shared-cache content before caching their new view',async()=>{
  let now=1000,resolve,calls=0;const cache=Runtime.createRequestCache({now:()=>now}),state={method:'GET',path:'/posts',base:'https://a',token:'A',lang:'ko'};
  const old=cache.run(state,()=>new Promise(r=>resolve=r));await tick();
  await cache.run({...state,method:'POST'},async()=>({ok:true}));resolve({posts:['old']});await old;
  const fresh=await cache.run(state,async options=>{calls++;assert.equal(options.bypassCache,true);return{posts:['new']};});assert.deepEqual(fresh.posts,['new']);
  await cache.run(state,async()=>{throw Error('should use fresh memory value');});assert.equal(calls,1);
  now+=30001;await cache.run(state,async options=>{assert.equal(options.bypassCache,false);return{};});
});

test('an unsafe view counter is never deduplicated and failed safe reads can retry immediately',async()=>{
  const cache=Runtime.createRequestCache(),state={method:'GET',path:'/posts/1?view=1'};let calls=0;
  await Promise.all([cache.run(state,async()=>++calls),cache.run(state,async()=>++calls)]);assert.equal(calls,2);
  await assert.rejects(cache.run({...state,path:'/posts'},async()=>{throw Error('offline');}));assert.deepEqual(await cache.run({...state,path:'/posts'},async()=>({ok:true})),{ok:true});
});

test('the actual API client keeps authorization on personal reads, removes it from invariant lists and refreshes after writes',async()=>{
  const a=app(),calls=[];a.store.set('hlCmTok','account-A');
  a.context.fetch=async(url,options)=>{calls.push({url,...options});return{ok:true,json:async()=>({ok:true})};};
  await Promise.all([a.run('cmApi("GET","/posts?lang=ko&page=1")'),a.run('cmApi("GET","/posts?page=1&lang=ko")')]);assert.equal(calls.length,1);assert.equal(calls[0].headers.Authorization,undefined);
  await a.run('cmApi("GET","/lab/tokens")');await a.run('cmApi("GET","/lab/tokens")');assert.equal(calls.length,3);assert.equal(calls[1].headers.Authorization,'Bearer account-A');
  await a.run('cmApi("POST","/posts",{title:"new"})');await a.run('cmApi("GET","/posts?lang=ko&page=1")');assert.equal(calls.at(-1).headers['Cache-Control'],'no-cache');assert.equal(calls[3].headers.Authorization,'Bearer account-A');
});

test('an old account response cannot sign out a newer account or replace its identity',async()=>{
  const a=app();a.store.set('hlCmTok','account-A');let finish;
  a.context.fetch=(url,options)=>options.headers.Authorization==='Bearer account-A'?new Promise(resolve=>finish=resolve):Promise.resolve({ok:true,json:async()=>({user:{nickname:'B'}})});
  const old=a.run('cmApi("GET","/me")');await tick();a.run('cmTok("account-B")');const current=await a.run('cmLoadMe()');assert.equal(current.nickname,'B');
  finish({ok:false,status:401,json:async()=>({error:'login_required'})});await assert.rejects(old);
  assert.equal(a.store.get('hlCmTok'),'account-B');assert.equal(a.run('cm.me.nickname'),'B');
});

test('the exam bootstrap shares identity with the account chip without a second me request',async()=>{
  const a=app(),calls=[];a.store.set('hlCmTok','account-A');
  a.context.fetch=async(url)=>{calls.push(url);return{ok:true,json:async()=>({user:{nickname:'A'},tokens:3,sessions:[],health:{v:5,lab:true}})};};
  const bootstrap=a.run('cmLabBootstrap()'),identity=a.run('cmLoadMe()');const [b,user]=await Promise.all([bootstrap,identity]);
  assert.equal(b.tokens,3);assert.equal(user.nickname,'A');assert.equal(calls.length,1);assert.ok(calls[0].includes('/lab/bootstrap?include=health,sessions'));
  calls.length=0;
  await Promise.all([a.run('cmLabBootstrap({id:12,include:"health,sessions"})'),a.run('cmLabBootstrap({id:12,include:"sessions,health"})')]);assert.equal(calls.length,1);assert.ok(calls[0].includes('&id=12'));
});

test('only a missing bootstrap endpoint uses the older parallel reads during deployment or rollback',async()=>{
  const a=app(),calls=[];a.store.set('hlCmTok','account-A');
  const data={'/api/me':{user:{nickname:'A'}},'/api/lab/active':{tokens:4,active:null,now:100},'/api/lab/sessions':{sessions:[{id:12}]},'/api/health':{lab:true,v:5},'/api/lab/sessions/12':{session:{id:12,user_id:1}}};
  a.context.fetch=async url=>{calls.push(url);const u=new URL(url);return u.pathname==='/api/lab/bootstrap'?{ok:false,status:404,json:async()=>({error:'not_found'})}:{ok:true,json:async()=>data[u.pathname]};};
  const [first,second]=await Promise.all([a.run('cmLabBootstrap({id:12})'),a.run('cmLabBootstrap({id:12})')]);assert.equal(first.tokens,4);assert.equal(first.session.id,12);assert.equal(second.user.nickname,'A');assert.equal(calls.length,6);assert.equal(a.run('cm.me.nickname'),'A');
  for(const status of [401,503]){
    const b=app(),seen=[];b.store.set('hlCmTok','account-A');b.context.fetch=async url=>{seen.push(url);return{ok:false,status,json:async()=>({error:status===401?'login_required':'server_error'})};};await assert.rejects(b.run('cmLabBootstrap()'));assert.equal(seen.length,1,'fallback must not hide authentication or server errors');
  }
  const b=app(),seen=[];b.context.fetch=async url=>{seen.push(url);throw Error('offline');};await assert.rejects(b.run('cmLabBootstrap()'));assert.equal(seen.length,1,'network failure must not fan out into more failing requests');
  const c=app();let finish;c.store.set('hlCmTok','account-A');c.context.fetch=()=>new Promise(resolve=>finish=resolve);const stale=c.run('cmLabBootstrap()');await tick();c.run('cmTok("account-B")');finish({ok:false,status:404,json:async()=>({error:'not_found'})});await assert.rejects(stale,error=>error.code==='account_changed');assert.equal(c.store.get('hlCmTok'),'account-B');assert.equal(c.run('cm.me'),null);
});

test('community list content starts before identity, health and board widgets finish',async()=>{
  const a=app(),calls=[];
  a.node('cmRoot');a.run('cmHash=()=>({parts:["all"],q:new URLSearchParams()});cmRailHtml=()=>"rail";cmWire=()=>{};cmRight=()=>{};');
  a.context.never=new Promise(()=>{});a.context.paintList=async root=>{calls.push('main');root.innerHTML='visible list';};
  a.run('cmLoadMe=()=>never;cmHealth=()=>never;cmApi=()=>never;cmList=paintList;');
  await a.run('cmMount()');assert.deepEqual(calls,['main']);assert.equal(a.node('cmRoot').innerHTML,'visible list');
});
