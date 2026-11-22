const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {createRequire}=require('node:module'),{JSDOM}=createRequire(path.resolve(__dirname,'../community/package.json'))('jsdom');
const Runtime=require('../site-runtime.js');
const read=file=>fs.readFileSync(path.join(__dirname,'..',file),'utf8');
const main=[...read('index.html').matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].find(m=>m[1].includes('const REL ='))[1];
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const QID='q_'+'a'.repeat(64),SID='src_'+'b'.repeat(64);
function app(hash='#/archive/books/phys'){
  const dom=new JSDOM('<!doctype html><html><body></body></html>'),document=dom.window.document;
  const find=document.getElementById.bind(document),handlers={},observers=[],store=new Map([['hlCmTok','SYNTHETIC_ACCOUNT_TOKEN']]);
  const nodes={has:id=>!!find(id),get:id=>find(id)};
  const calls={mounts:[],disposed:[],updates:[],accounts:0};let context;
  const node=id=>{let element=find(id);if(!element){element=document.createElement('div');element.id=id;document.body.append(element);}return element;};
  // Exercise real parent/child, closest(), hidden and removal behavior while
  // retaining the existing parent application's synthetic service boundaries.
  document.getElementById=id=>id==='archiveNative'||/^learn.*Frame$/.test(id)?find(id):node(id);
  const native={bookMedia:{[SID]:{image_url:'archive-media/books/synthetic.webp'}},schoolMedia:{institutions:[{id:'kaist',name:{ko:'KAIST',en:'KAIST'},source_ids:[]}]},mountArchiveLibrary(container,options){calls.mounts.push({container,options});const result={dispose(){calls.disposed.push(container);},update(value){calls.updates.push(value);}};return result;}};
  context={window:{HL_RUNTIME:Runtime,HL_ARCHIVE_NATIVE:native},URL,URLSearchParams,console,innerHeight:850,
    location:new URL('https://haslalab.org/'+hash),history:{replaceState(_state,_title,url){context.location.href=new URL(url,context.location).href;}},
    document,
    localStorage:{getItem:key=>store.get(key)||null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)},sessionStorage:{getItem:()=>null,setItem(){}},
    addEventListener(name,fn){(handlers[name]??=[]).push(fn);},matchMedia:()=>({matches:false}),setTimeout(){},clearTimeout(){},requestAnimationFrame(){},cancelAnimationFrame(){},scrollTo(){},
    MutationObserver:class{constructor(callback){this.callback=callback;observers.push(this);}observe(target){this.target=target;}},fetch:async()=>{throw Error('Parent must delegate data reads to its scoped native reader');}};
  vm.createContext(context);
  for(const f of ['archive-navigation.js','site-catalogue.js','site-design.js'])vm.runInContext(read(f),context,{filename:f});
  context.HLexam=context.window.HLexam;vm.runInContext(main.replace(/render\(\);\s*$/,''),context,{filename:'index-main.js'});
  const run=code=>vm.runInContext(code,context);context.arChip=()=>calls.accounts++;run('buildRails=()=>{};paintSiteTheme=()=>{};mountHaslaAdFit=()=>{}');
  return{context,run,node,nodes,calls,handlers,observers,store,native};
}
test('Learn retains Studio and sends reading to Archive without a bank tile or frame',()=>{
  const a=app();for(const language of ['ko','en']){
    a.run('lang='+JSON.stringify(language));
    for(const subject of ['physics','astronomy']){
      const html=a.run(`viewLearnSubject(${JSON.stringify(subject)})`);assert.doesNotMatch(html,/문제은행|Problem library|data-learn-tool="library"|<iframe/);
      assert.match(html,new RegExp('href="#/archive/books/'+(subject==='physics'?'phys':'astro')+'"'));
    }
    a.run('cm.me={id:1,role:"admin"}');assert.match(a.run('viewLearnSubject("physics")'),/href="#\/learn\/physics\/studio"/);a.run('cm.me=null');
    assert.doesNotMatch(a.run('viewLearn()'),/문제은행|Problem library/);
  }
  assert.doesNotMatch(read('index.html'),/learnLibraryFrame|function viewLearnLibrary|hl-bank-settings/);
});
test('Archive has three categories and keeps the original competition gallery and logos',()=>{
  const a=app();for(const language of ['ko','en']){
    a.run('lang='+JSON.stringify(language));const html=a.run('viewComps("phys",2)');
    for(const category of ['contests','books','schools'])assert.match(html,new RegExp('href="#/archive/'+category+'/phys"'));
    assert.match(html,/data-logo-key="ipho"/);assert.match(html,/class="comp" href="#\/ipho"/);assert.equal((html.match(/class="comp" href=/g)||[]).length,2);
    assert.match(html,language==='ko'?/>학교<|>교재</:/>Schools<|>Books</);
  }
  assert.deepEqual(Runtime.routeNeeds('#/archive/books/phys'),[]);assert.deepEqual(Runtime.routeNeeds('#/archive/schools/astro'),[]);
});
test('Books and Schools mount native category- and subject-bound readers without frames',async()=>{
  for(const [category,kind] of [['books','book'],['schools','course']])for(const [sub,collection] of [['phys','physics'],['astro','astronomy']]){
    const a=app(`#/archive/${category}/${sub}?source=${SID}&problem=${QID}`);a.run('render()');await tick();
    const {options}=a.calls.mounts[0];assert.equal(options.kind,kind);assert.equal(options.collection,collection);assert.equal(options.params.get('source'),SID);assert.equal(options.params.get('problem'),QID);
    assert.equal(options.baseHash,`#/archive/${category}/${sub}`);assert.equal(options.apiOrigin,'https://haslalab-problem-bank.haslalab.workers.dev');assert.equal(typeof options.renderMath,'function');
    assert.equal(options.bookMedia,a.native.bookMedia);assert.equal(options.schoolMedia,a.native.schoolMedia);
    assert.equal(options.getToken(),'SYNTHETIC_ACCOUNT_TOKEN');assert.doesNotMatch(a.node('view').innerHTML,/<iframe|SYNTHETIC_ACCOUNT_TOKEN|workers\.dev/);
    const shell=a.nodes.get('archiveNative').closest('.shell');assert(shell.classList.contains('archive-reading'));assert.equal(shell.querySelector(':scope > .phead').hidden,true);assert.equal(shell.querySelector(':scope > .subjs').hidden,true);
    assert.equal(shell.dataset.archiveKind,kind);assert.match(a.node('view').innerHTML,/<nav[^>]*class="subjs archive-library-subjects"/);assert.match(a.node('view').innerHTML,new RegExp('data-subject-art="'+sub+'"'));assert.doesNotMatch(a.node('view').innerHTML,/data-logo-key="ipho"|archive-shell|archive-disciplines/);
    assert.match(a.node('nav').innerHTML,/<a href="#\/comps" class="on">/);assert.match(a.context.document.title,/아카이브/);
  }
});

test('school cards keep their selection in the native route and the main language switch',async()=>{
  const a=app('#/archive/schools/math?school=kaist');a.run('render()');await tick();
  assert.equal(a.calls.mounts[0].options.params.get('school'),'kaist');assert.equal(a.calls.mounts[0].options.collection,'mathematics');
  assert.match(a.node('view').innerHTML,/<h1>학교를 고르세요<\/h1>/);assert.doesNotMatch(a.node('view').innerHTML,/학교 아카이브/);
  a.run('setLang("en")');await tick();assert.equal(a.calls.mounts.at(-1).options.params.get('school'),'kaist');assert.match(a.node('view').innerHTML,/<h1>Choose a school<\/h1>/);
});
test('old Learn bank bookmarks resolve into Archive and never remount the retired app',async()=>{
  const a=app('#/learn/astronomy/library');a.run('render()');await tick();assert.equal(a.context.location.hash,'#/archive/books/astro');assert.equal(a.calls.mounts[0].options.collection,'astronomy');
  const b=app('#/learn/physics/library?problem='+QID);b.run('render()');await tick();
  assert.match(b.context.location.hash,/^#\/archive\/open\?/);const first=b.calls.mounts[0].options;assert.equal(first.resolveLegacy,true);
  first.onNavigate('#/archive/schools/astro?problem='+QID);await tick();
  assert.equal(b.context.location.hash,'#/archive/schools/astro?problem='+QID);assert.equal(b.calls.mounts.at(-1).options.kind,'course');assert.equal(b.calls.mounts.at(-1).options.collection,'astronomy');assert.equal(b.calls.disposed.length,1);
});
test('contest web questions remain available alongside the full paper gallery',async()=>{
  const a=app('#/archive/contests/phys');a.run('render()');await tick();assert.equal(a.calls.mounts.length,0);assert.match(a.node('view').innerHTML,/view=web/);
  a.context.location.hash='#/archive/contests/phys?view=web';a.run('render()');await tick();assert.equal(a.calls.mounts.at(-1).options.kind,'contest');
  const container=a.nodes.get('archiveNative');
  a.context.location.hash='#/archive/contests/phys?problem='+QID;a.run('render()');await tick();assert.equal(a.calls.updates.at(-1).params.get('problem'),QID);
  a.context.location.hash='#/archive/contests/phys?type=experiment';a.run('render()');await tick();assert.equal(a.calls.updates.at(-1).params.get('type'),'experiment');
  assert.equal(a.calls.mounts.length,1);assert.equal(a.calls.disposed.length,0);assert.equal(a.nodes.get('archiveNative'),container);
  a.context.location.hash='#/archive/contests/phys';a.run('render()');await tick();assert.equal(a.calls.disposed.length,1);assert.equal(a.nodes.has('archiveNative'),false);assert(a.node('view').querySelector('a.comp[href="#/ipho"]'));assert(a.node('view').querySelector('[data-logo-key="ipho"]'));
});
test('source, chapter, question and back navigation reuse one reader while hiding only reading chrome',async()=>{
  const a=app();a.run('render()');await tick();const container=a.nodes.get('archiveNative'),shell=container.closest('.shell'),head=shell.querySelector(':scope > .phead'),subjects=shell.querySelector(':scope > .subjs');
  assert.equal(head.hidden,false);assert.equal(subjects.hidden,false);
  for(const query of ['source='+SID,'source='+SID+'&chapter=1','source='+SID+'&chapter=1&problem='+QID,'source='+SID+'&chapter=1']){
    a.context.location.hash='#/archive/books/phys?'+query;a.run('render()');await tick();
    assert.equal(a.nodes.get('archiveNative'),container);assert.equal(a.calls.mounts.length,1);assert.equal(a.calls.disposed.length,0);assert.equal(head.hidden,true);assert.equal(subjects.hidden,true);assert(shell.classList.contains('archive-reading'));
    assert.equal(a.calls.updates.at(-1).params.get('source'),SID);assert.equal(a.calls.updates.at(-1).params.get('chapter'),query.includes('chapter=1')?'1':null);
  }
  a.context.location.hash='#/archive/books/phys';a.run('render()');await tick();assert.equal(a.nodes.get('archiveNative'),container);assert.equal(head.hidden,false);assert.equal(subjects.hidden,false);assert.equal(shell.classList.contains('archive-reading'),false);assert.equal(a.calls.mounts.length,1);
});
test('language changes preserve the outer source/problem URL and use the same site account',async()=>{
  const a=app('#/archive/books/astro?source='+SID+'&problem='+QID);a.node('acct').innerHTML='EXISTING_ACCOUNT';a.run('render()');await tick();
  a.run('setLang("en")');await tick();const current=a.calls.mounts.at(-1).options;
  assert.equal(current.lang,'en');assert.equal(current.collection,'astronomy');assert.equal(current.params.get('problem'),QID);assert.equal(current.params.get('source'),SID);assert.equal(a.node('acct').innerHTML,'EXISTING_ACCOUNT');assert.equal(a.context.location.search,'?lang=en');
  a.context.document.documentElement.dataset.theme='dark';for(const o of a.observers)if(o.target===a.context.document.documentElement)o.callback([]);
  assert.equal(a.calls.updates.at(-1).theme,'dark');assert.equal(a.calls.mounts.length,2);
});
test('native login uses the existing return location and auth changes do not copy tokens into URLs',async()=>{
  const a=app();a.run('render()');await tick();const options=a.calls.mounts[0].options;
  a.run('cmTok("NEW_SYNTHETIC_TOKEN")');await tick();assert.equal(options.getToken(),'NEW_SYNTHETIC_TOKEN');assert.equal(a.calls.updates.length,1);
  options.onLogin();assert.equal(a.context.location.hash,'#/login');assert.doesNotMatch(a.context.location.href,/SYNTHETIC|Bearer|token=/);
});
test('navigation disposes the old reader and cannot be undone by stale module resolution',async()=>{
  const a=app();a.run('render()');a.context.location.hash='#/archive/schools/astro';a.run('render()');await tick();
  assert.equal(a.calls.mounts.length,1);const options=a.calls.mounts[0].options;assert.equal(options.kind,'course');assert.equal(options.collection,'astronomy');
  a.context.location.hash='#/about';a.run('render()');await tick();assert.equal(a.calls.disposed.length,1);assert.equal(a.nodes.has('archiveNative'),false);
  options.onNavigate('#/archive/books/phys');assert.equal(a.context.location.hash,'#/about');
});
