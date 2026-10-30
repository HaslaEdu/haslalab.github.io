const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const Runtime=require('../site-runtime.js'),root=path.resolve(__dirname,'..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const html=read('index.html'),main=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].find(m=>m[1].includes('const REL ='))[1];
const earlyMain=html.match(/<script id="hlEarlyApi">([\s\S]*?)<\/script>/)[1];
const metadataScope={window:{}};vm.runInNewContext(read('site-catalogue.js'),metadataScope);const catalogue=metadataScope.window.HL_CATALOGUE;
const plain=v=>JSON.parse(JSON.stringify(v)),tick=()=>new Promise(r=>setImmediate(r));
const anchors=html=>[...html.matchAll(/<a\b[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g)].map(([,url,label])=>({
  url:url.replaceAll('&amp;','&').replaceAll('&quot;','"').replaceAll('&#39;',"'"),label:label.replace(/<[^>]+>/g,'')
}));

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
function enableReadState(a,saved=new Map()){
  a.context.sessionStorage={getItem:key=>saved.get(key)||null,setItem:(key,value)=>saved.set(key,String(value)),removeItem:key=>saved.delete(key)};
  if(!a.context.fetch)a.context.fetch=async()=>{throw Error('unexpected fetch');};
  a.run(earlyMain);return saved;
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

test('every competition keeps its labelled official website before and after lazy hydration in both interface languages',()=>{
  const lean=app(),full=app({preload:true}),keys=Object.keys(catalogue.competitions);
  const check=(a,phase)=>{
    for(const language of ['ko','en']){
      a.run(`lang=${JSON.stringify(language)}`);
      for(const key of keys){
        const meta=catalogue.competitions[key].data,c=a.run(`compOf(${JSON.stringify(key)})`),site=meta.officialWebsite;
        assert.match(site,/^https?:\/\//,`${phase}/${key}: published official website`);
        assert.equal(c.officialWebsite,site,`${phase}/${key}: hydrated official website`);
        assert.equal(Boolean(c.officialWebsiteArchived),Boolean(meta.officialWebsiteArchived),`${phase}/${key}: archived-site context`);
        if(new URL(site).hostname==='web.archive.org')assert.equal(meta.officialWebsiteArchived,true,`${key}: archived official website must be disclosed`);
        const page=a.run(`viewComp(${JSON.stringify(key)})`);
        const official=anchors(page).find(link=>link.url===site&&(language==='ko'?/공식/:/official/i).test(link.label));
        assert.ok(official,`${phase}/${key}/${language}: labelled official website link`);
        if(c.officialWebsiteArchived)assert.match(official.label,language==='ko'?/보관|아카이브/:/archiv/i,`${key}: archived label`);
      }
    }
  };
  check(lean,'cold metadata');check(full,'preloaded');
  lean.run('hydrateCatalogue()');check(lean,'repeated hydration');
  for(const key of catalogue.theoryKeys)lean.load('theory:'+key);
  for(const key of ['iypt','usaco','rupho'])lean.load(key);
  check(lean,'lazy archives loaded');
  for(const key of ['rupho','ruphow','ruphox','ruphoy']){
    for(const language of ['ko','en']){
      lean.run(`lang=${JSON.stringify(language)}`);
      const source=lean.run(`compOf(${JSON.stringify(key)})`);
      assert.match(source.officialWebsite,/^https?:\/\//,key+' official stage website');
      assert.ok(anchors(lean.run(`viewComp(${JSON.stringify(key)})`)).some(link=>link.url===source.officialWebsite&&(language==='ko'?/공식/:/official/i).test(link.label)),key+'/'+language+' official stage link');
    }
  }
});

test('PLANCKS public resources contain only its official homepage and general rules while preserving archive papers',()=>{
  const lean=app(),full=app({preload:true}),manifest=JSON.parse(read('tools/theory/plancks.json'));
  const rules='https://iaps.info/wp-content/uploads/2021/01/PLANCKS-General-Rules-EGM-2020.pdf';
  for(const phase of ['cold','loaded']){
    if(phase==='loaded')lean.load('theory:plancks');
    for(const language of ['ko','en']){
      const links=anchors(lean.run(`lang=${JSON.stringify(language)};archiveResources(compOf("plancks"))`));
      assert.deepEqual(links.map(link=>link.url).sort(),[manifest.officialWebsite,rules].sort(),phase+'/'+language+' visible resources');
    }
  }
  assert.deepEqual(plain(lean.run('THEORY.plancks')),plain(full.run('THEORY.plancks')),'resource trimming must not change any question or solution PDF');
  for(const year of manifest.years){
    const published=lean.run(`THEORY.plancks[${year.y}].f.T`);
    for(const file of year.files){
      if(file.kind==='paper')assert.equal(published.papers[file.lang.toLowerCase()],file.local,`${year.y}: paper remains available`);
      if(file.kind==='solution')assert.equal(published.sol,file.local,`${year.y}: solution remains available`);
    }
  }
});

test('new physics archives retain official metadata and historical context through independent lazy loads',()=>{
  const lean=app(),options={known:Object.keys(catalogue.competitions),theory:catalogue.theoryKeys,versions:catalogue.versions};
  lean.run('lang="en";track="thy"');
  const subjects=lean.run('viewComps("phys")');
  assert.equal(lean.run('Object.keys(THEORY).length'),0);
  const loaded=[];
  for(const [key,count] of [['plancks',13],['eotvos',45]]){
    const manifest=JSON.parse(read(`tools/theory/${key}.json`)),meta=catalogue.competitions[key];
    assert.ok(subjects.includes(`href="#/${key}"`),key+' remains discoverable before its PDFs load');
    assert.equal(meta.counts.years,count);
    assert.equal(meta.data.officialWebsite,manifest.officialWebsite);
    assert.deepEqual(plain(meta.data.note),manifest.resourceNote);
    assert.deepEqual(plain(meta.data.resources),manifest.resources);
    for(const route of [`#/${key}`,`#/${key}/2021/exam`,`#/${key}/2021/review`])assert.deepEqual(Runtime.routeNeeds(route,options),['theory:'+key],route);
    lean.load('theory:'+key);loaded.push(key);
    assert.deepEqual(plain(lean.run('Object.keys(THEORY).sort()')),loaded.slice().sort());
    assert.equal(lean.run(`DATA.${key}.years.length`),count);
    assert.deepEqual(plain(lean.run(`DATA.${key}.note`)),manifest.resourceNote);
    assert.ok(lean.run(`viewComp(${JSON.stringify(key)})`).includes(manifest.officialWebsite));
  }
  const historical=lean.run('viewYear("eotvos",1987)'),paper=lean.run('THEORY.eotvos[1987].f.T.paper');
  assert.ok(historical.includes(paper+'#page=2'),'the old paper opens at its verified report section');
  assert.ok(historical.includes('Report with reprinted problems'),'historical statements remain labelled as reprints');
  assert.ok(historical.includes('alongside other years and solutions'),'combined historical reports disclose unrelated solutions');
  assert.ok(historical.includes('a solution to this historical set is not supplied'),'a historical source report must not imply an unavailable matching solution');
  assert.ok(lean.run('viewYear("eotvos",1996)').includes('Problems & solutions · Magyar'),'a clean English default retains the combined Hungarian report label');
});

test('lazy native papers and year-specific standalone review keep language and mode arguments',()=>{
  const lean=app();for(const key of ['nbpho','eotvos','physcup'])lean.load('theory:'+key);
  lean.run('lang="en";track="thy"');
  const combined=lean.run('viewYear("nbpho",2026,"review")');assert.match(combined,/data-mode="review" data-year="2026"/);assert.ok(combined.includes('review=1'));
  const native=lean.run('viewYear("eotvos",2020,"exam")');
  const nativeLink=new URL(native.match(/href="(sim\/exam\.html\?[^\"]+)"/)[1].replaceAll('&amp;','&'),'https://haslalab.org/');
  assert.equal(nativeLink.searchParams.get('pl'),'hu');
  assert.equal(nativeLink.searchParams.get('p'),lean.run('THEORY.eotvos[2020].f.T.papers.hu'));
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

test('account sections coalesce only while pending and never retain private results',async()=>{
  for(const path of ['/me/stats','/me/identities','/me/overview']){
    const policy=Runtime.requestPolicy('GET',path);assert.equal(policy.safe,true);assert.equal(policy.public,false);assert.equal(policy.ttl,0);
    const cache=Runtime.createRequestCache();let calls=0,finish;
    const state={path,token:'A'},send=()=>{calls++;return new Promise(resolve=>finish=resolve);};
    const first=cache.run(state,send),second=cache.run(state,send);await tick();assert.equal(calls,1);finish({user:'A'});await Promise.all([first,second]);
    await cache.run(state,async()=>{calls++;return{user:'A-new'};});assert.equal(calls,2);
  }
});

test('public profiles omit authorization but fetch fresh visibility and names on every completed read',async()=>{
  const a=app(),calls=[];a.store.set('hlCmTok','account-A');
  a.context.fetch=async(url,options)=>{calls.push({url,options});return{ok:true,json:async()=>({profile:{nickname:'A'}})};};
  for(const path of ['/users?nickname=A','/users/A']){
    const policy=Runtime.requestPolicy('GET',path);assert.equal(policy.public,true);assert.equal(policy.ttl,0);
    a.context.profilePath=path;await Promise.all([a.run('cmApi("GET",profilePath)'),a.run('cmApi("GET",profilePath)')]);await a.run('cmApi("GET",profilePath)');
  }
  assert.equal(calls.length,4);for(const call of calls)assert.equal(call.options.headers.Authorization,undefined);
});

test('a weekly submission bypasses its shared derived data while retaining configuration caches',async()=>{
  const cache=Runtime.createRequestCache(),state={base:'https://a',token:'A',lang:'ko'};
  await cache.run({...state,path:'/health'},async()=>({v:5}));await cache.run({...state,method:'POST',path:'/problems/4/submit'},async()=>({id:2}));
  for(const path of ['/weekly?lang=ko','/rank?scope=week','/me/overview','/me/stats'])await cache.run({...state,path},async options=>{assert.equal(options.bypassCache,true,path+' must refresh its derived leaderboard');return{};});
  await cache.run({...state,path:'/me/identities'},async options=>{assert.equal(options.bypassCache,false);return{};});
  await cache.run({...state,path:'/health'},async()=>{throw Error('configuration cache should survive a submission');});
});

test('a community write refreshes all community lists while retaining unrelated public configuration and lab statistics',async()=>{
  const cache=Runtime.createRequestCache(),state={base:'https://a',token:'A',lang:'ko'};
  for(const path of ['/health','/pay/config','/lab/contest/catalog','/lab/stats?comp=kmo','/boards','/posts?sort=hot'])await cache.run({...state,path},async()=>({path}));
  await cache.run({...state,method:'POST',path:'/posts/4/comments'},async()=>({id:2}));
  for(const path of ['/health','/pay/config','/lab/contest/catalog','/lab/stats?comp=kmo'])await cache.run({...state,path},async()=>{throw Error('unrelated cache was discarded: '+path);});
  for(const path of ['/boards','/posts?sort=hot','/posts?best=1'])await cache.run({...state,path},async options=>{assert.equal(options.bypassCache,true);return{};});
  await cache.run({...state,path:'/lab/stats?comp=kmchc'},async options=>{assert.equal(options.bypassCache,false);return{};});
});

test('weekly and ranking content use their own version and identity without waiting for unrelated health or a second me request',async()=>{
  for(const route of ['#/weekly/2026-W44','#/rank/all']){
    const a=app(),calls=[];vm.runInContext(read('arena.js'),a.context);a.store.set('hlCmTok','account-A');a.context.location.hash=route;
    const root=a.node('arRoot');a.run('arWeekly=async(root,alive,week,data)=>{if(alive())root.innerHTML="weekly:"+data.week;};arRank=async(root,alive,scope,data)=>{if(alive())root.innerHTML="rank:"+data.scope;};');
    a.context.fetch=async(url,options)=>{calls.push({url,options});if(url.includes('/health'))return new Promise(()=>{});return{ok:true,json:async()=>({api_version:5,user:{nickname:'A'},week:'2026-W44',scope:'all'})};};
    const mounted=a.run('arMount()'),identity=a.run('cmLoadMe()');await mounted;assert.equal((await identity).nickname,'A');
    assert.match(root.innerHTML,/^(weekly:2026-W44|rank:all)$/);assert.equal(calls.filter(x=>new URL(x.url).pathname==='/api/me').length,0);
    assert.equal(calls[0].options.headers.Authorization,'Bearer account-A');assert.match(calls[0].url,route.includes('weekly')?/weekly\?lang=ko&week=2026-W44/:/rank\?scope=all/);
  }
});

test('a stale page response cannot hydrate another account or render after a language change',async()=>{
  const a=app();vm.runInContext(read('arena.js'),a.context);a.store.set('hlCmTok','account-A');a.context.location.hash='#/weekly';let finish;
  a.context.fetch=url=>url.includes('/health')?new Promise(()=>{}):new Promise(resolve=>finish=resolve);
  a.run('arWeekly=async root=>{root.innerHTML="stale";};');const pending=a.run('arMount()');await tick();a.run('cmTok("account-B");lang="en"');
  finish({ok:true,json:async()=>({api_version:5,user:{nickname:'A'}})});await pending;assert.equal(a.run('cm.me'),null);assert.notEqual(a.node('arRoot').innerHTML,'stale');
});

test('account overview is the sole initial request and shares identity with the header',async()=>{
  const a=app(),calls=[];vm.runInContext(read('arena.js'),a.context);a.store.set('hlCmTok','account-A');a.context.location.hash='#/me';
  a.run('arMe=async(root,alive,overview)=>{if(alive())root.innerHTML="tokens:"+overview.tokens;};');
  a.context.fetch=async url=>{calls.push(url);return{ok:true,json:async()=>({user:{nickname:'A'},stats:{},identities:[],has_password:true,active:null,tokens:2,health:{v:5,lab:true}})};};
  const pending=a.run('arMount()'),identity=a.run('cmLoadMe()');await pending;assert.equal((await identity).nickname,'A');assert.equal(calls.length,1);assert.match(calls[0],/\/me\/overview$/);assert.equal(a.node('arRoot').innerHTML,'tokens:2');
  await a.run('cmMeOverview()');assert.equal(calls.length,2,'balances and role must not persist in a response cache');
});

test('overview falls back only on 404 and starts all older account sections together',async()=>{
  const a=app(),calls=[],finishes=[];a.store.set('hlCmTok','account-A');
  const data={'/api/me':{user:{nickname:'A'}},'/api/me/stats':{subs:[]},'/api/me/identities':{identities:[],providers:[],has_pw:true},'/api/lab/active':{tokens:4,active:null},'/api/health':{v:5,lab:true}};
  a.context.fetch=async url=>{const p=new URL(url).pathname;calls.push(p);if(p==='/api/me/overview')return{ok:false,status:404,json:async()=>({error:'not_found'})};return new Promise(resolve=>finishes.push(()=>resolve({ok:true,json:async()=>data[p]})));};
  const pending=a.run('cmMeOverview()');await tick();assert.equal(calls.length,6);assert.equal(finishes.length,5);for(const finish of finishes)finish();const result=await pending;assert.equal(result.tokens,4);assert.equal(result.has_password,true);
  for(const status of [401,503]){
    const b=app(),seen=[];b.store.set('hlCmTok','account-A');b.context.fetch=async url=>{seen.push(url);return{ok:false,status,json:async()=>({error:status===401?'login_required':'server_error'})};};
    await assert.rejects(b.run('cmMeOverview()'));assert.equal(seen.length,1);
  }
});

test('an expired overview session redirects to login without a fanout of account requests',async()=>{
  const a=app(),calls=[];vm.runInContext(read('arena.js'),a.context);a.store.set('hlCmTok','account-A');a.context.location.hash='#/me';
  a.context.fetch=async url=>{calls.push(url);return{ok:false,status:401,json:async()=>({error:'login_required'})};};
  await a.run('arMount()');assert.equal(a.context.location.hash,'#/login');assert.equal(calls.length,1);assert.equal(a.store.has('hlCmTok'),false);
});

test('the actual account renderer consumes overview sections without additional HTTP reads',async()=>{
  const a=app(),calls=[];vm.runInContext(read('arena.js'),a.context);a.store.set('hlCmTok','account-A');a.context.location.hash='#/me';
  const elements=new Map(),get=s=>{if(!elements.has(s))elements.set(s,{innerHTML:'',textContent:'',value:'A',querySelector:child=>get(s+' '+child),querySelectorAll:()=>[]});return elements.get(s);};
  a.node('arRoot').querySelector=get;get('#arNick').n={value:'A'};a.run('cmAvatarForm=()=>{};cmNickCheck=()=>async()=>true;');
  a.context.fetch=async url=>{calls.push(url);return{ok:true,json:async()=>({user:{nickname:'A',username:'a'},stats:{subs:[],lv:0,rating:0,total:0,solved:0},identities:[{provider:'google'}],has_password:true,active:null,tokens:2,health:{v:5,lab:true,oauth:['google','kakao']}})};};
  await a.run('arMount()');assert.equal(calls.length,1);assert.ok(a.node('arRoot').innerHTML.includes('@a'));assert.match(get('#arIds').innerHTML,/google/);assert.match(get('#arIds').innerHTML,/kakao/);assert.match(get('#arLabMe').innerHTML,/<b>2<\/b>/);
});

test('a legacy weekly response retains its old-server guard while the primary request starts before health',async()=>{
  const a=app(),calls=[],finishes=new Map();vm.runInContext(read('arena.js'),a.context);a.store.set('hlCmTok','account-A');a.context.location.hash='#/weekly';
  a.context.fetch=url=>{const p=new URL(url).pathname;calls.push(p);return new Promise(resolve=>finishes.set(p,resolve));};
  const pending=a.run('arMount()');await tick();assert.deepEqual(calls,['/api/weekly','/api/health']);
  finishes.get('/api/weekly')({ok:true,json:async()=>({week:'2026-W44'})});await tick();assert.ok(calls.includes('/api/me'));
  finishes.get('/api/me')({ok:true,json:async()=>({user:{nickname:'A'}})});finishes.get('/api/health')({ok:true,json:async()=>({v:3})});await pending;
  assert.ok(a.node('arRoot').innerHTML.includes(a.run('arT().oldServer')));
});

test('post details render authoritative permissions without waiting on identity or health, and a returned comment updates locally',async()=>{
  const a=app(),calls=[];a.store.set('hlCmTok','account-A');const root=a.node('cmRoot'),elements=new Map();
  const get=selector=>{if(!elements.has(selector))elements.set(selector,{innerHTML:'',textContent:'',classList:{toggle(){}},querySelector(){return null;}});return elements.get(selector);};
  const btn={disabled:false},error={textContent:''},form={body:{value:'New comment'},querySelector:s=>s==='button'?btn:error,reset(){this.body.value='';}};
  root.querySelector=s=>s==='#cmDel'?null:s==='#cmCmt'?form:get(s);root.querySelectorAll=()=>[];
  a.run('cmHealth=()=>new Promise(()=>{});cmMount=()=>{throw Error("must not remount after comment");};');
  const post={id:12,board:'free',lang:'ko',title:'Post',body:'Body',nickname:'A',created_at:1,views:1,mine:false,n_likes:0,n_dislikes:0};
  a.context.fetch=async(url,options)=>{calls.push({url,options});return{ok:true,json:async()=>options.method==='POST'?{id:13,comment:{id:13,parent_id:null,body:'New comment',nickname:'A',created_at:2,mine:true}}:new URL(url).pathname==='/api/posts/12'?{post,comments:[],my:0,user:{nickname:'A'},api_version:5}:{posts:[]}};};
  const pending=a.run('cmPost(document.getElementById("cmRoot"),12,()=>true)'),identity=a.run('cmLoadMe()');await pending;assert.equal((await identity).nickname,'A');assert.ok(root.innerHTML.includes('id="cmCmt"'));assert.equal(calls.length,2);
  await form.onsubmit({preventDefault(){},target:form});assert.equal(calls.length,3);assert.match(get('#cmThread').innerHTML,/New comment/);assert.match(get('#cmThread').innerHTML,/data-c="edit"/);assert.equal(get('.cmcmts .hd em').textContent,1);assert.equal(btn.disabled,false);assert.equal(form.body.value,'');
});

test('new lazy arena remains compatible with cached HTML missing the new page and overview helpers',async()=>{
  for(const route of ['#/weekly','#/rank/all','#/me']){
    const a=app(),calls=[];vm.runInContext(read('arena.js'),a.context);a.store.set('hlCmTok','account-A');a.context.location.hash=route;
    a.run('cmPageRead=undefined;cmMeOverview=undefined;arWeekly=async(root,alive,week,data)=>{if(alive())root.innerHTML="weekly:"+data.week;};arRank=async(root,alive,scope,data)=>{if(alive())root.innerHTML="rank:"+data.scope;};arMe=async(root,alive,data)=>{if(alive())root.innerHTML="tokens:"+data.tokens;};');
    a.context.fetch=async(url,options)=>{calls.push({url,options});if(url.includes('/health'))return new Promise(()=>{});return{ok:true,json:async()=>({api_version:5,user:{nickname:'A'},week:'2026-W44',scope:'all',stats:{},identities:[],has_password:true,tokens:2,health:{v:5,lab:true}})};};
    const mounted=a.run('arMount()'),identity=a.run('cmLoadMe()');await mounted;assert.equal((await identity).nickname,'A');
    assert.match(a.node('arRoot').innerHTML,/^(weekly:2026-W44|rank:all|tokens:2)$/);
    assert.equal(calls.filter(c=>!c.url.includes('/health')).length,1,'primary response must also supply header identity');
    assert.equal(calls.some(c=>new URL(c.url).pathname==='/api/me'),false);assert.equal(calls[0].options.headers.Authorization,'Bearer account-A');
  }
});

test('cached HTML overview compatibility keeps 404-only fallback and rejects stale identity',async()=>{
  for(const status of [401,503]){
    const a=app(),calls=[];vm.runInContext(read('arena.js'),a.context);a.run('cmMeOverview=undefined');a.store.set('hlCmTok','account-A');
    a.context.fetch=async url=>{calls.push(url);return{ok:false,status,json:async()=>({error:status===401?'login_required':'server_error'})};};
    await assert.rejects(a.run('arMeOverview()'));assert.equal(calls.length,1);
  }
  const a=app(),calls=[];vm.runInContext(read('arena.js'),a.context);a.run('cmMeOverview=undefined');a.store.set('hlCmTok','account-A');let finish;
  a.context.fetch=url=>{calls.push(url);return new Promise(resolve=>finish=resolve);};const pending=a.run('arMeOverview()');await tick();a.run('cmTok("account-B")');finish({ok:false,status:404,json:async()=>({error:'not_found'})});
  await assert.rejects(pending,error=>error.code==='account_changed');assert.equal(calls.length,1);assert.equal(a.run('cm.me'),null);
});

test('head prefetch starts the route read before lazy arena and hands it to the scoped client exactly once',async()=>{
  assert.ok(html.indexOf('id="hlEarlyApi"')<html.indexOf('rel="apple-touch-icon"'));
  assert.match(html,/<link rel="preconnect" href="https:\/\/haslalab-community-edge\.haslalab\.workers\.dev" crossorigin>/);
  for(const route of ['#/weekly/2026-W44','#/rank/all','#/weekly/p/12','#/me']){
    const a=app(),calls=[];a.store.set('hlCmTok','account-A');a.context.location.hash=route;
    a.context.fetch=async(url,options)=>{calls.push({url,options});if(url.includes('/health'))return new Promise(()=>{});return{ok:true,json:async()=>({api_version:5,user:{nickname:'A'},week:'2026-W44',scope:'all',problem:{id:12},stats:{},identities:[],tokens:2,health:{v:5,lab:true}})};};
    enableReadState(a);assert.equal(calls.length,1,'the read starts before arena loads');
    vm.runInContext(read('arena.js'),a.context);a.run('arWeekly=arRank=arProblem=arMe=async(root,alive)=>{if(alive())root.innerHTML="ready";};');
    const mounted=a.run('arMount()'),identity=a.run('cmLoadMe()');await mounted;assert.equal((await identity).nickname,'A');assert.equal(a.node('arRoot').innerHTML,'ready');
    assert.equal(calls.filter(c=>!c.url.includes('/health')).length,1);assert.equal(calls[0].options.headers.Authorization,'Bearer account-A');assert.equal(a.context.window.HL_EARLY_API,null);
    const path=new URL(calls[0].url).pathname.replace('/api','')+new URL(calls[0].url).search;a.context.repeatPath=path;await a.run('cmApi("GET",repeatPath)');assert.equal(calls.filter(c=>!c.url.includes('/health')).length,2,'personal response is not retained after the initial handoff');
  }
});

test('early public lists omit authentication, normalize defaults and never prefetch view counters or writes',async()=>{
  const a=app(),calls=[];a.store.set('hlCmTok','account-A');a.context.location.hash='#/community/free/2?tag=q';
  a.context.fetch=async(url,options)=>{calls.push({url,options});return{ok:true,json:async()=>({posts:[],total:0})};};enableReadState(a);
  await a.run('cmApi("GET","/posts?tag=q&board=free&page=2&lang=ko&sort=new")');assert.equal(calls.length,1);assert.equal(calls[0].options.headers.Authorization,undefined);
  assert.equal(Runtime.canonicalPath('/posts?board=free'),Runtime.canonicalPath('/posts?sort=new&lang=ko&page=1&board=free'));
  for(const route of ['#/community/post/12','#/community/write','#/weekly/admin','#/lab/12']){
    const b=app();b.context.location.hash=route;b.context.fetch=()=>{throw Error('must not issue a speculative write or view counter');};enableReadState(b);assert.equal(b.context.window.HL_EARLY_API,undefined);
  }
});

test('an account change discards the prefetched private response and its consistency bookmark',async()=>{
  const a=app(),calls=[];a.store.set('hlCmTok','account-A');a.context.location.hash='#/weekly';let finish;
  a.context.fetch=(url,options)=>{calls.push({url,options});return calls.length===1?new Promise(resolve=>finish=resolve):Promise.resolve({ok:true,headers:{get:()=> 'B-current'},json:async()=>({api_version:5,user:{nickname:'B'}})});};
  const saved=enableReadState(a);a.run('cmTok("account-B")');await a.run('cmPageRead("/weekly?lang=ko")');finish({ok:true,headers:{get:()=> 'A-old'},json:async()=>({user:{nickname:'A'}})});await tick();
  assert.equal(calls.length,2);assert.equal(a.run('cm.me.nickname'),'B');assert.ok(![...saved.values()].join('').includes('A-old'));
});

test('bookmarks use a hashed storage scope, travel only on eligible read URLs and survive reload',async()=>{
  const a=app(),calls=[];a.store.set('hlCmTok','private-token-A');
  a.context.fetch=async(url,options)=>{calls.push({url,options});return{ok:true,headers:{get:()=> 'opaque-position-1'},json:async()=>({posts:[]})};};const saved=enableReadState(a);
  await a.run('cmApi("GET","/posts")');await a.run('cmApi("GET","/posts?sort=new&page=1&lang=ko")');assert.equal(calls.length,1,'this exact response may be reused at its own returned bookmark');
  const scope={base:a.run('cmBase()'),token:'private-token-A',lang:'ko'},reads=a.context.window.HL_READ_STATE;
  for(const path of ['/posts','/boards','/weekly?lang=ko','/rank?scope=all'])assert.equal(new URL(reads.prepare({...scope,path}).path,'https://api.invalid').searchParams.get('__hl_bm'),'opaque-position-1');
  for(const path of ['/me/overview','/me/stats','/users?nickname=A','/lab/tokens','/pay/config'])assert.equal(new URL(reads.prepare({...scope,path}).path,'https://api.invalid').searchParams.has('__hl_bm'),false,path);
  for(const changed of [{token:'private-token-B'},{base:'http://localhost:8765'},{lang:'en'}])assert.equal(new URL(reads.prepare({...scope,...changed,path:'/posts'}).path,'https://api.invalid').searchParams.has('__hl_bm'),false);
  assert.ok([...saved.keys()].every(key=>/^hlReadBookmark:v1:[0-9a-f]+$/.test(key)));assert.ok(!JSON.stringify([...saved]).includes('private-token-A'));
  const b=app();b.store.set('hlCmTok','private-token-A');enableReadState(b,saved);assert.equal(new URL(b.context.window.HL_READ_STATE.prepare({...scope,path:'/posts'}).path,'https://api.invalid').searchParams.get('__hl_bm'),'opaque-position-1');
  assert.equal(Object.keys(calls[0].options.headers).some(key=>/bookmark/i.test(key)),false,'no extra CORS request header is used');
});

test('a stronger read bookmark changes the public cache key instead of reusing an older list',async()=>{
  const a=app(),calls=[];let marker=0;a.store.set('hlCmTok','account-A');
  a.context.fetch=async(url,options)=>{calls.push({url,options});const bookmark='position-'+(++marker);return{ok:true,headers:{get:()=>bookmark},json:async()=>({posts:[],user:{nickname:'A'}})};};enableReadState(a);
  await a.run('cmApi("GET","/posts")');await a.run('cmApi("GET","/me/overview")');await a.run('cmApi("GET","/posts")');
  assert.equal(calls.length,3);assert.equal(new URL(calls[1].url).searchParams.has('__hl_bm'),false);assert.equal(new URL(calls[2].url).searchParams.get('__hl_bm'),'position-2');
  await a.run('cmApi("GET","/posts")');assert.equal(calls.length,3);
});

test('out-of-order writes keep reads on primary until a fresh response covers every completed write',()=>{
  const a=app(),saved=enableReadState(a),reads=a.context.window.HL_READ_STATE,scope={base:a.run('cmBase()'),token:'A',lang:'ko'};
  const first=reads.prepare({...scope,method:'POST',path:'/posts'}),second=reads.prepare({...scope,method:'POST',path:'/posts'});
  reads.accept(second,'position-newer-start');reads.finish(second);reads.accept(first,'position-older-response');reads.finish(first);
  const health=reads.prepare({...scope,path:'/health'});reads.accept(health,'old-cached-settings');
  const primary=reads.prepare({...scope,path:'/posts'});assert.equal(primary.forcePrimary,true);assert.equal(new URL(primary.path,'https://api.invalid').searchParams.get('__hl_bm'),'position-newer-start');
  reads.accept(primary,'position-all-writes');const next=reads.prepare({...scope,path:'/posts'});assert.equal(next.forcePrimary,false);assert.equal(new URL(next.path,'https://api.invalid').searchParams.get('__hl_bm'),'position-all-writes');
  const reloaded=app();enableReadState(reloaded,saved);assert.equal(reloaded.context.window.HL_READ_STATE.prepare({...scope,path:'/posts'}).forcePrimary,false);
});

test('a dirty checkpoint restored on reload consumes its already-primary head request without duplicating it',async()=>{
  const a=app(),saved=enableReadState(a),scope={base:a.run('cmBase()'),token:'account-A',lang:'ko'};
  const write=a.context.window.HL_READ_STATE.prepare({...scope,method:'POST',path:'/posts'});a.context.window.HL_READ_STATE.accept(write,'own-write');a.context.window.HL_READ_STATE.finish(write);
  const b=app(),calls=[];b.store.set('hlCmTok','account-A');b.context.location.hash='#/weekly';b.context.fetch=async(url,options)=>{calls.push({url,options});return{ok:true,headers:{get:()=> 'fresh-primary'},json:async()=>({api_version:5,user:{nickname:'A'}})};};enableReadState(b,saved);
  await b.run('cmPageRead("/weekly?lang=ko")');assert.equal(calls.length,1);assert.equal(calls[0].options.headers['Cache-Control'],'no-cache');assert.equal(new URL(calls[0].url).searchParams.get('__hl_bm'),'own-write');
});

test('expired public lists render immediately and share one background refresh while private responses stay live',async()=>{
  let now=0,calls=0,finish;const cache=Runtime.createRequestCache({now:()=>now}),state={path:'/posts',base:'https://a',token:'A',lang:'ko'},updates=[];
  await cache.run(state,async()=>({posts:['old']}));now=6000;
  const send=()=>{calls++;return new Promise(resolve=>finish=resolve);};const first=await cache.run({...state,onRefresh:value=>updates.push(value)},send),second=await cache.run({...state,onRefresh:value=>updates.push(value)},send);
  assert.deepEqual(first.posts,['old']);assert.deepEqual(second.posts,['old']);assert.equal(calls,1);finish({posts:['new']});await tick();assert.equal(updates.length,2);assert.deepEqual(updates[0].posts,['new']);
  await cache.run({...state,method:'POST',path:'/posts/12/vote'},async()=>({ok:true}));let fresh;
  const waiting=cache.run({...state,onRefresh:()=>{throw Error('writes must not show stale data');}},options=>{assert.equal(options.bypassCache,true);return new Promise(resolve=>fresh=resolve);});await tick();fresh({posts:['after write']});assert.deepEqual((await waiting).posts,['after write']);
  let balance=0;for(let i=0;i<2;i++)await cache.run({...state,path:'/lab/tokens',onRefresh:()=>{}},async()=>({tokens:++balance}));assert.equal(balance,2);
});

test('a public refresh that races a mutation cannot repaint stale content',async()=>{
  let now=0,finish;const cache=Runtime.createRequestCache({now:()=>now}),state={path:'/posts',base:'https://a',token:'A',lang:'ko'};await cache.run(state,async()=>({posts:['old']}));now=6000;let paints=0;
  await cache.run({...state,onRefresh:()=>paints++},()=>new Promise(resolve=>finish=resolve));await cache.run({...state,method:'POST'},async()=>({ok:true}));finish({posts:['stale']});await tick();assert.equal(paints,0);
});

test('the community sidebar starts alongside a pending main list instead of after it',async()=>{
  const a=app(),events=[];let finish;a.context.never=new Promise(()=>{});a.context.paintMain=()=>{events.push('main');return new Promise(resolve=>finish=resolve);};a.context.paintRight=()=>events.push('right');
  a.run('cmHash=()=>({parts:["all"],q:new URLSearchParams()});cmRailHtml=()=>"";cmWire=()=>{};cmLoadMe=cmHealth=cmApi=()=>never;cmList=paintMain;cmRight=paintRight;');
  const pending=a.run('cmMount()');await tick();assert.deepEqual(events,['main','right']);finish();await pending;
});

test('a refreshed public list paints without another request and preserves an active search field',async()=>{
  const a=app(),root=a.node('cmRoot'),nodes=new Map();root.querySelector=selector=>{if(!nodes.has(selector))nodes.set(selector,{});return nodes.get(selector);};root.querySelectorAll=()=>[];
  const data=title=>({posts:[{id:1,board:'free',tag:'gen',title,nickname:'Public author',created_at:1,views:0,n_comments:0,n_likes:0,n_dislikes:0}],total:1,per:30});let refresh,calls=0;
  a.context.readPosts=async(method,path,body,options)=>{calls++;refresh=options.onRefresh;return data('Old public title');};a.run('cmApi=readPosts');
  await a.run('cmList(document.getElementById("cmRoot"),{where:"all",page:1,tag:"",sort:"",q:"",field:""},()=>true)');assert.match(root.innerHTML,/Old public title/);
  await refresh(data('Fresh public title'));assert.match(root.innerHTML,/Fresh public title/);assert.equal(calls,1);
  a.context.document.activeElement={matches:()=>true};root.contains=()=>true;await refresh(data('While typing'));assert.ok(!root.innerHTML.includes('While typing'));assert.equal(calls,1);
});

test('a private-read bookmark arriving after an identity switch cannot enter session storage',async()=>{
  const a=app();a.store.set('hlCmTok','account-A');let finish;a.context.fetch=()=>new Promise(resolve=>finish=resolve);const saved=enableReadState(a);
  const pending=a.run('cmApi("GET","/me/overview")');await tick();a.run('cmTok("account-B")');finish({ok:true,headers:{get:()=> 'old-account-position'},json:async()=>({user:{nickname:'A'}})});await pending;
  assert.ok(!JSON.stringify([...saved]).includes('old-account-position'));
});

test('a confirmed primary checkpoint releases the old family refresh window for subsequent replica reads',async()=>{
  const a=app(),calls=[];a.store.set('hlCmTok','account-A');let number=0;
  a.context.fetch=async(url,options)=>{calls.push({url,options});const marker='checkpoint-'+(++number);return{ok:true,headers:{get:()=>marker},json:async()=>({posts:[],ok:true})};};enableReadState(a);
  await a.run('cmApi("POST","/posts",{body:"new"})');await a.run('cmApi("GET","/posts?board=free")');
  assert.equal(calls[1].options.headers['Cache-Control'],'no-cache');assert.equal(new URL(calls[1].url).searchParams.get('__hl_bm'),'checkpoint-1');
  await a.run('cmApi("GET","/posts?board=qna")');assert.equal(new URL(calls[2].url).searchParams.get('__hl_bm'),'checkpoint-2');assert.equal(calls[2].options.headers['Cache-Control'],undefined);
  await a.run('cmApi("GET","/posts?board=study",null,{forcePrimary:true})');assert.equal(calls[3].options.headers['Cache-Control'],'no-cache','explicit primary refresh must still bypass caches');
});

test('pending writes retain primary transport and cannot release dirty state through an overlapping read',async()=>{
  const a=app(),calls=[];a.store.set('hlCmTok','account-A');let finishWrite;
  a.context.fetch=(url,options)=>{calls.push({url,options});if(options.method==='POST')return new Promise(resolve=>finishWrite=resolve);return Promise.resolve({ok:true,headers:{get:()=> 'read-'+calls.length},json:async()=>({posts:[]})});};enableReadState(a);
  const write=a.run('cmApi("POST","/posts",{body:"new"})');await tick();await a.run('cmApi("GET","/posts?board=free")');assert.equal(calls[1].options.headers['Cache-Control'],'no-cache');
  finishWrite({ok:true,headers:{get:()=> 'completed-write'},json:async()=>({ok:true})});await write;
  await a.run('cmApi("GET","/posts?board=qna")');assert.equal(calls[2].options.headers['Cache-Control'],'no-cache','the overlapping read did not confirm the completed write');
  await a.run('cmApi("GET","/posts?board=study")');assert.equal(calls[3].options.headers['Cache-Control'],undefined);
  const reads=a.context.window.HL_READ_STATE,scope={base:a.run('cmBase()'),token:'account-A',lang:'ko'},prepared=reads.prepare({...scope,path:'/boards'});
  assert.equal(reads.transport(prepared).canUseReplica,true);const newerWrite=reads.prepare({...scope,method:'POST',path:'/posts'});assert.equal(reads.transport(prepared).canUseReplica,false);assert.equal(reads.transport(prepared).forcePrimary,true);reads.finish(newerWrite);
});

test('a legacy response without a checkpoint never disables post-mutation primary refreshes',async()=>{
  const a=app(),calls=[];a.context.fetch=async(url,options)=>{calls.push({url,options});return{ok:true,json:async()=>({posts:[],ok:true})};};enableReadState(a);
  await a.run('cmApi("POST","/posts",{body:"new"})');await a.run('cmApi("GET","/posts?board=free")');await a.run('cmApi("GET","/posts?board=qna")');
  for(const call of calls.slice(1)){assert.equal(call.options.headers['Cache-Control'],'no-cache');assert.equal(new URL(call.url).searchParams.has('__hl_bm'),false);}
});
