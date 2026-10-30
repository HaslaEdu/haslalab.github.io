const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const rootPath=path.resolve(__dirname,'..'),read=file=>fs.readFileSync(path.join(rootPath,file),'utf8');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const deferred=()=>{let resolve,reject;return{promise:new Promise((yes,no)=>{resolve=yes;reject=no;}),resolve,reject};};
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function gate({role='admin',auth,load}={}){
  let scope='account-A',present=true,mounts=0,disposals=0;
  const nodes=new Map(),root={innerHTML:'',querySelector(selector){if(!nodes.has(selector))nodes.set(selector,{});return nodes.get(selector);},querySelectorAll:()=>[]};
  const calls=[],loads=[],context={lang:'ko',esc,cm:{me:{id:1,role,nickname:'Cached identity'}},window:{},
    location:{hash:'#/lab/server-guide'},document:{getElementById:()=>root},cmIdentityScope:()=>scope,cmTok:()=>scope,
    cmBase:()=> 'https://haslalab-community-edge.haslalab.workers.dev',cmErr:error=>error?.code||'server_error',
    cmApi:async(...args)=>{calls.push(args);return auth?auth():{user:{id:1,role:'admin',nickname:'Current administrator'}};},
    siteDataLoader:{load:async name=>{loads.push(name);if(load)await load();}},
    sessionStorage:{getItem:()=>null,setItem(){},removeItem(){}},console};
  context.window.HL_SERVER_GUIDE={html:language=>'<div>guide '+language+'</div>',mount(target,options){mounts++;target.innerHTML=this.html(options.language);return{dispose(){disposals++;}};}};
  vm.createContext(context);vm.runInContext(read('arena.js'),context,{filename:'arena.js'});
  const initialScope=scope,alive=()=>present&&scope===initialScope;
  return{context,root,nodes,calls,loads,alive,run:code=>vm.runInContext(code,context),mounts:()=>mounts,disposals:()=>disposals,
    changeAccount:()=>scope='account-B',leave:()=>present=false};
}

test('a stale cached administrator cannot load the guide after the fresh server response denies the role',async()=>{
  const a=gate({auth:async()=>({user:{id:1,role:'user',nickname:'Current member'}})});
  await a.context.arServerGuide(a.root,a.alive);
  assert.equal(a.calls.length,1);assert.equal(a.calls[0][0],'GET');assert.equal(a.calls[0][1],'/me');assert.equal(a.calls[0][3]?.forcePrimary,true);
  assert.deepEqual(a.loads,[]);assert.equal(a.mounts(),0);assert.ok(!a.root.innerHTML.includes('guide ko'));
});

test('only a freshly verified administrator loads and mounts the developer module',async()=>{
  const a=gate({role:'user'});await a.context.arServerGuide(a.root,a.alive);
  assert.deepEqual(a.loads,['developer-guide']);assert.equal(a.mounts(),1);assert.match(a.root.innerHTML,/guide ko/);assert.equal(a.context.cm.me.nickname,'Current administrator');
  a.run('ar.poller.dispose()');assert.equal(a.disposals(),1);
});

test('account and route changes while authorization is pending prevent the module from loading',async()=>{
  for(const change of ['changeAccount','leave']){
    const authorization=deferred(),a=gate({auth:()=>authorization.promise});const pending=a.context.arServerGuide(a.root,a.alive);await flush();a[change]();authorization.resolve({user:{id:1,role:'admin'}});await pending;
    assert.deepEqual(a.loads,[],change);assert.equal(a.mounts(),0,change);
  }
});

test('account and route changes during module loading prevent stale mounting',async()=>{
  for(const change of ['changeAccount','leave']){
    const module=deferred(),a=gate({load:()=>module.promise});const pending=a.context.arServerGuide(a.root,a.alive);await flush();assert.deepEqual(a.loads,['developer-guide']);a[change]();module.resolve();await pending;
    assert.equal(a.mounts(),0,change);
  }
});

test('a role downgrade during module loading prevents mounting even when the account and route stay the same',async()=>{
  const module=deferred(),a=gate({load:()=>module.promise});const pending=a.context.arServerGuide(a.root,a.alive);await flush();a.context.cm.me={id:1,role:'user'};module.resolve();await pending;assert.equal(a.mounts(),0);
});

test('authorization failures do not load the module and their retry handler cannot revive a departed route',async()=>{
  const a=gate({auth:async()=>{throw{code:'network'};}});await a.context.arServerGuide(a.root,a.alive);assert.deepEqual(a.loads,[]);assert.equal(a.mounts(),0);
  const retry=a.nodes.get('[data-retry-server-guide]');assert.equal(typeof retry?.onclick,'function');const before=a.calls.length;a.leave();await retry.onclick();assert.equal(a.calls.length,before);
});

test('the actual arena route disposes the mounted guide before leaving developer tools',async()=>{
  const a=gate();a.context.cmLoadMe=async()=>a.context.cm.me;a.context.cmHealth=async()=>({v:5});await a.run('arMount()');assert.equal(a.mounts(),1);
  a.context.location.hash='#/login';a.context.arAuth=()=>{};await a.run('arMount()');assert.equal(a.disposals(),1);
});

function guideModule({fetchImpl,language='ko',apiBase='https://haslalab-community-edge.haslalab.workers.dev'}={}){
  const calls=[],timers=new Map();let timerId=0,present=true;
  const element=()=>{let text='',html='';return{disabled:false,attributes:{},htmlWrites:[],setAttribute(key,value){this.attributes[key]=String(value);},
    get textContent(){return text;},set textContent(value){text=String(value);},get innerHTML(){return html;},set innerHTML(value){html=String(value);this.htmlWrites.push(html);}};};
  const content=element(),probe=element(),output=element();let choices=[],markup='';
  const root={get innerHTML(){return markup;},set innerHTML(value){markup=String(value);choices=[...markup.matchAll(/data-guide-flow="(\d+)"/g)].map(match=>Object.assign(element(),{dataset:{guideFlow:match[1]}}));},
    querySelector:selector=>({'[data-guide-flow-content]':content,'[data-guide-probe]':probe,'[data-guide-probe-output]':output}[selector]),
    querySelectorAll:selector=>selector==='[data-guide-flow]'?choices:[]};
  const fetcher=async(...args)=>{calls.push(args);return fetchImpl?fetchImpl(...args):{ok:true,json:async()=>({supported:true,replica:true,primary:false,regions:['APAC'],colos:['ICN']})};};
  const context={window:{fetch:fetcher},URL,AbortController,console,Intl,Date,
    setTimeout:(fn,ms)=>{timers.set(++timerId,{fn,ms});return timerId;},clearTimeout:id=>timers.delete(id)};
  vm.createContext(context);vm.runInContext(read('developer-server-guide.js'),context,{filename:'developer-server-guide.js'});
  const guide=context.window.HL_SERVER_GUIDE;
  return{guide,root,calls,timers,content,probe,output,choices:()=>choices,leave:()=>present=false,
    mount:()=>guide.mount(root,{language,apiBase,alive:()=>present}),context};
}

test('opening the guide and switching every flow performs no requests or AI calls',()=>{
  for(const language of ['ko','en']){
    const a=guideModule({language});assert.equal(a.calls.length,0);assert.match(a.guide.html(language),/data-guide-probe/);assert.equal(a.calls.length,0);
    const mounted=a.mount();assert.ok(a.choices().length>=4);
    for(const button of a.choices()){
      button.onclick();assert.ok(a.content.innerHTML.length>30);assert.equal(button.attributes['aria-pressed'],'true');
      for(const other of a.choices().filter(x=>x!==button))assert.equal(other.attributes['aria-pressed'],'false');
    }
    assert.equal(a.calls.length,0);assert.equal(a.timers.size,0);mounted.dispose();
  }
});

test('the explicit diagnostic makes one anonymous uncached GET and ignores a repeated click while pending',async()=>{
  const result=deferred(),a=guideModule({fetchImpl:()=>result.promise});const mounted=a.mount();
  const pending=a.probe.onclick();await flush();await a.probe.onclick();assert.equal(a.calls.length,1);
  const [url,options]=a.calls[0];assert.equal(url,'https://haslalab-community-edge.haslalab.workers.dev/api/health?read_region_check=1');
  assert.equal(options.method,'GET');assert.equal(options.credentials,'omit');assert.equal(options.cache,'no-store');assert.equal(options.referrerPolicy,'no-referrer');
  assert.equal(options.body,undefined);assert.equal(options.headers?.Authorization,undefined);assert.equal(options.headers?.['X-Lab-Token'],undefined);assert.equal(a.probe.disabled,true);
  assert.equal([...a.timers.values()][0].ms,15000);
  result.resolve({ok:true,json:async()=>({supported:true,replica:true,primary:false,regions:['APAC'],colos:['ICN']})});await pending;
  assert.match(a.output.textContent,/APAC/);assert.match(a.output.textContent,/ICN/);assert.equal(a.probe.disabled,false);assert.equal(a.timers.size,0);mounted.dispose();
});

test('diagnostic values are rendered as text and do not inject markup or expose unrelated response fields',async()=>{
  const attack='<img src=x onerror=alert(1)>',a=guideModule({fetchImpl:async()=>({ok:true,json:async()=>({supported:true,replica:true,primary:true,regions:[attack],colos:['<script>alert(1)</script>'],secret:'must-not-render'})})});
  const mounted=a.mount();await a.probe.onclick();assert.ok(a.output.textContent.includes(attack));assert.equal(a.output.htmlWrites.length,0);assert.ok(!a.root.innerHTML.includes(attack));assert.ok(!a.output.textContent.includes('must-not-render'));mounted.dispose();
});

test('unsupported or failed diagnostics display a controlled message without retrying or calling another endpoint',async()=>{
  for(const fetchImpl of [async()=>({ok:true,json:async()=>({supported:false,detail:'do-not-display'})}),async()=>({ok:false,status:503}),async()=>{throw Error('private request detail');}]){
    const a=guideModule({fetchImpl}),mounted=a.mount();await a.probe.onclick();assert.equal(a.calls.length,1);assert.ok(a.output.textContent.length>5);assert.ok(!/do-not-display|private request detail/.test(a.output.textContent));assert.equal(a.probe.disabled,false);assert.equal(a.timers.size,0);mounted.dispose();
  }
});

test('leaving or disposing the guide prevents a stale diagnostic completion from updating its UI',async()=>{
  for(const dispose of [false,true]){
    const result=deferred(),a=guideModule({fetchImpl:()=>result.promise}),mounted=a.mount();const pending=a.probe.onclick();await flush();const before=a.output.textContent;
    if(dispose){mounted.dispose();assert.equal(a.calls[0][1].signal.aborted,true);assert.equal(a.timers.size,0);}else a.leave();
    result.resolve({ok:true,json:async()=>({supported:true,replica:true,primary:false,regions:['STALE-RESULT'],colos:[]})});await pending;assert.equal(a.output.textContent,before);mounted.dispose();
  }
});

test('a diagnostic rejects API URLs containing credentials before issuing a request',async()=>{
  const a=guideModule({apiBase:'https://user:password@example.test'}),mounted=a.mount();await a.probe.onclick();assert.equal(a.calls.length,0);assert.ok(!a.output.textContent.includes('password'));mounted.dispose();
});
