const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../site-design.js'),'utf8'),Runtime=require('../site-runtime.js');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function app({language='ko',role='user',api=async()=>({posts:[],total:0})}={}){
  const dialogs=[],calls=[],body={style:{overflow:'scroll'},append(node){dialogs.push(node);node.isConnected=true;}};
  const button=dataset=>({dataset,attrs:{},disabled:false,focuses:0,setAttribute(k,v){this.attrs[k]=v;},focus(){this.focuses++;}});
  function dialog(){
    const nodes=new Map(['.hl-mail-list','.hl-mail-status','.hl-mail-more','.hl-mail-close'].map(key=>[key,{...button({}),innerHTML:'',textContent:'',hidden:false}]));
    const filters=['all','notices','updates'].map(mailFilter=>button({mailFilter})),listeners={};
    const node={...button({}),open:false,innerHTML:'',listeners,nodes,filters,
      addEventListener(type,fn){listeners[type]=fn;},
      querySelector(selector){
        if(selector==='[data-mail-retry]')return nodes.get('.hl-mail-status').innerHTML.includes('data-mail-retry')?(this.retry||=button({})):null;
        return nodes.get(selector)||null;
      },
      querySelectorAll(selector){
        if(selector==='[data-mail-filter]')return filters;
        if(selector==='[data-mail-pin]')return this.pins=[...nodes.get('.hl-mail-list').innerHTML.matchAll(/data-mail-pin="(\d+)"/g)].map(match=>button({mailPin:match[1]}));
        return[];
      },
      showModal(){this.open=true;this.modalCalls=(this.modalCalls||0)+1;nodes.get('.hl-mail-close').focus();},
      close(){if(!this.open)return;this.open=false;listeners.close?.();},
      remove(){this.isConnected=false;},
    };return node;
  }
  const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const context={lang:language,Date,Set,URL,Promise,console,document:{body,createElement(tag){assert.equal(tag,'dialog');return dialog();},getElementById(){return null;}},
    esc:escape,cmFmt:escape,cmFull:at=>'date:'+at,cm:{me:{role}},cmLoadMe:async()=>({role}),cmApi:async(method,url,body)=>{calls.push({method,url,body});return api(method,url,body);},cmToast(){},cmErr:error=>String(error)};
  vm.createContext(context);vm.runInContext(source,context);return{context,run:code=>vm.runInContext(code,context),dialogs,calls,body};
}

test('home more opens a native labelled dialog; close restores focus and page scroll without navigation',async()=>{
  const a=app(),trigger={isConnected:true,focuses:0,focus(){this.focuses++;}};a.context.trigger=trigger;
  a.run('openSiteMailbox(trigger)');await tick();
  assert.equal(a.dialogs.length,1);const dialog=a.dialogs[0];assert.equal(dialog.modalCalls,1);assert.equal(dialog.attrs['aria-labelledby'],'hlMailboxTitle');
  assert.match(dialog.innerHTML,/aria-describedby|hlMailboxHint/);assert.match(dialog.innerHTML,/autofocus/);assert.equal(a.body.style.overflow,'hidden');
  assert.equal(dialog.listeners.cancel,undefined,'Escape uses the native dialog dismissal and close cleanup');
  a.run('openSiteMailbox(trigger)');assert.equal(a.dialogs.length,1,'repeated opens reuse the current modal');
  dialog.nodes.get('.hl-mail-close').onclick();assert.equal(dialog.open,false);assert.equal(dialog.isConnected,false);assert.equal(a.body.style.overflow,'scroll');assert.equal(trigger.focuses,1);
  assert.match(source,/aria-haspopup="dialog" onclick="openSiteMailbox\(this\)"/);
});

test('mailbox loads every notice page, separates languages, sorts pins first and escapes expanded public text',async()=>{
  const notice=id=>({id,title:id===1?'<script>unsafe</script>':'Notice '+id,body:'<img src=x onerror=alert(1)>\nFull text '+id,created_at:id,pinned:id===1});
  const a=app({language:'en',api:async(method,url)=>url.includes('page=1')?{posts:[notice(20),notice(1)],total:3}:{posts:[notice(2)],total:3}});
  a.run('openSiteMailbox()');await tick();const dialog=a.dialogs[0],list=dialog.nodes.get('.hl-mail-list');
  assert.match(a.calls[0].url,/notices=1&lang=en&page=1/);assert.ok(list.innerHTML.indexOf('notice:1')<list.innerHTML.indexOf('notice:20'));
  assert.match(list.innerHTML,/Pinned/);assert.match(list.innerHTML,/&lt;script&gt;unsafe&lt;\/script&gt;/);assert.match(list.innerHTML,/&lt;img src=x onerror/);assert.doesNotMatch(list.innerHTML,/<script>|<img src=x/);
  assert.equal(dialog.nodes.get('.hl-mail-more').hidden,false);await dialog.nodes.get('.hl-mail-more').onclick();
  assert.match(a.calls[1].url,/page=2/);assert.match(list.innerHTML,/notice:2/);assert.equal(dialog.nodes.get('.hl-mail-more').hidden,true);
  dialog.filters[2].onclick();assert.doesNotMatch(list.innerHTML,/data-mail-key="notice:/);assert.equal((list.innerHTML.match(/data-mail-key="update:/g)||[]).length,a.run('SITE_UPDATES.length'));assert.match(list.innerHTML,/international finals are available/);
  assert.ok(list.innerHTML.indexOf('update:0')<list.innerHTML.indexOf('update:1'),'same-day updates retain publication order');
  dialog.filters[1].onclick();assert.doesNotMatch(list.innerHTML,/data-mail-key="update:/);assert.equal((list.innerHTML.match(/data-mail-key="notice:/g)||[]).length,3);
  assert.doesNotMatch(list.innerHTML,/data-mail-pin=/,'non-admin readers never receive controls');
});

test('failed notices keep updates readable and can retry; closed dialogs ignore late reads',async()=>{
  let fail=true;const a=app({api:async()=>{if(fail)throw Error('offline');return{posts:[],total:0};}});
  a.run('openSiteMailbox()');await tick();const dialog=a.dialogs[0];assert.match(dialog.nodes.get('.hl-mail-list').innerHTML,/update:/);assert.match(dialog.nodes.get('.hl-mail-status').innerHTML,/다시 불러오기/);
  fail=false;await dialog.retry.onclick();assert.equal(dialog.nodes.get('.hl-mail-status').innerHTML,'');
  let resolve;const b=app({api:()=>new Promise(done=>resolve=done)});b.run('openSiteMailbox()');const old=b.dialogs[0];old.close();resolve({posts:[{id:1,title:'Too late',created_at:1}],total:1});await tick();
  assert.equal(old.isConnected,false);assert.equal(b.run('siteMailboxState'),null);assert.doesNotMatch(old.nodes.get('.hl-mail-list').innerHTML,/Too late/);
});

test('admin mailbox pin persists through the API then reloads ordered pages instead of retaining stale offsets',async()=>{
  let pinned=false;const a=app({role:'admin',api:async(method,url,body)=>{
    if(method==='PATCH'){pinned=body.pinned;return{ok:true,id:7,pinned};}
    return{posts:[{id:7,title:'Admin notice',body:'Body',created_at:1,pinned}],total:1};
  }});
  a.run('openSiteMailbox()');await tick();const dialog=a.dialogs[0];assert.match(dialog.nodes.get('.hl-mail-list').innerHTML,/공지 상단 고정/);
  await dialog.pins[0].onclick();assert.deepEqual(a.calls.map(call=>call.method),['GET','PATCH','GET']);assert.equal(a.calls[1].url,'/posts/7/pin');assert.equal(a.calls[1].body.pinned,true);
  assert.match(dialog.nodes.get('.hl-mail-list').innerHTML,/상단 고정 해제/);assert.match(a.calls[2].url,/page=1/);
});

test('notice-only canonical cache keys stay distinct and pin writes invalidate all community projections',async()=>{
  assert.notEqual(Runtime.canonicalPath('/posts?notices=1'),Runtime.canonicalPath('/posts'));
  const cache=Runtime.createRequestCache();let reads=0,last;
  const read=path=>cache.run({path},async policy=>{last=policy;return ++reads;});
  await read('/posts');await read('/posts?notices=1');await read('/posts?notices=1');assert.equal(reads,2);
  await cache.run({method:'PATCH',path:'/posts/7/pin'},async()=>({ok:true}));
  await read('/posts?notices=1');assert.equal(reads,3);assert.equal(last.bypassCache,true);
  await read('/posts');assert.equal(reads,4);assert.equal(last.bypassCache,true);
});
