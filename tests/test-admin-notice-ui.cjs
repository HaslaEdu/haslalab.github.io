const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const read=file=>fs.readFileSync(path.join(__dirname,'..',file),'utf8');
const main=[...read('index.html').matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].find(match=>match[1].includes('const REL ='))[1];
const plain=value=>JSON.parse(JSON.stringify(value));
const decode=value=>value.replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
const dummy=()=>({innerHTML:'',textContent:'',hidden:false,dataset:{},style:{},classList:{toggle(){},add(){},remove(){}},setAttribute(){},addEventListener(){},querySelector(){return null},querySelectorAll(){return[]}});

function editor(){
  let html='',form;
  const count=dummy(),preview=dummy(),error=dummy(),submit={disabled:false};
  const tabs=['w','p'].map(tab=>({...dummy(),dataset:{tab}}));
  const root={querySelector:selector=>selector==='#cmW'?form:selector==='#cmCnt'?count:selector==='.cmprev'?preview:null,
    querySelectorAll:selector=>selector==='[data-tab]'?tabs:[]};
  Object.defineProperty(root,'innerHTML',{get:()=>html,set:value=>{
    html=value;
    const field=name=>{
      const input=html.match(new RegExp('<input\\b[^>]*name="'+name+'"[^>]*>'));
      if(input)return{value:decode(input[0].match(/\bvalue="([^"]*)"/)?.[1]||'')};
      const select=html.match(new RegExp('<select\\b[^>]*name="'+name+'"[^>]*>([\\s\\S]*?)</select>'));
      if(select){const options=[...select[1].matchAll(/<option\b([^>]*)>([\s\S]*?)<\/option>/g)],option=options.find(option=>/\bselected\b/.test(option[1]))||options[0];return{value:decode(option?.[1].match(/\bvalue="([^"]*)"/)?.[1]||'')};}
      const area=html.match(new RegExp('<textarea\\b[^>]*name="'+name+'"[^>]*>([\\s\\S]*?)</textarea>'));
      return{value:decode(area?.[1]||'')};
    };
    form={board:field('board'),tag:field('tag'),title:field('title'),body:field('body'),
      querySelector:selector=>selector==='button[type=submit]'?submit:selector==='.cmerr'?error:null};
    submit.disabled=false;error.textContent='';
  }});
  return{root,get form(){return form},submit,error,count};
}

function app(language='ko',role='admin'){
  const e=editor(),nodes=new Map([['cmRoot',e.root]]),calls=[],stored=new Map();
  const node=id=>{if(!nodes.has(id))nodes.set(id,dummy());return nodes.get(id);};
  const context={window:{},URL,URLSearchParams,console,
    location:{hash:'#/community/write/free?tag=notice',search:''},history:{replaceState(){}},
    document:{getElementById:node,querySelector(){return null},querySelectorAll(){return[]},documentElement:{dataset:{}},body:dummy()},
    localStorage:{getItem(){return null},setItem(){}},sessionStorage:{getItem:key=>stored.get(key)||null,setItem:(key,value)=>stored.set(key,value),removeItem:key=>stored.delete(key)},
    addEventListener(){},matchMedia(){return{matches:false}},setTimeout(){},clearTimeout(){},requestAnimationFrame(){},cancelAnimationFrame(){},
    fetch:async()=>{throw new Error('Notice UI regression tests must never use the network');}};
  vm.createContext(context);
  for(const file of ['theory.js','paper-languages.js','contest-exams.js','examdur.js','rupho-selection.js','rupho-archive.js','site-design.js'])vm.runInContext(read(file),context,{filename:file});
  context.HLexam=context.window.HLexam;
  vm.runInContext(main.replace(/render\(\);\s*$/,''),context,{filename:'index-main.js'});
  const run=code=>vm.runInContext(code,context);
  run(`lang=${JSON.stringify(language)};cm.me=${role?JSON.stringify({role,nickname:'Tester'}):'null'};cm.v=5;cm.boards={};cm.boardsLang=lang;cm.boardsAt=Date.now();cmRailHtml=()=>'';cmWire=()=>{};cmRight=()=>{};cmLoadMe=async()=>cm.me;`);
  context.cmApi=async(method,url,data)=>{calls.push({method,url,data:plain(data??null)});if(method==='POST'&&url==='/posts')return{id:321};if(method==='GET'&&url.startsWith('/posts?'))return{posts:[],notices:[]};throw new Error('Unexpected mocked API '+method+' '+url);};
  context.editorRoot=e.root;
  return{...e,get form(){return e.form},context,run,calls,node,stored,
    write:(board='free',tag='notice',post=null)=>run(`cmWrite(editorRoot,${JSON.stringify(post)},${JSON.stringify(board)},${JSON.stringify(tag)})`)};
}

test('admin notice presets use a dedicated editor and immutable free/notice submission fields in Korean and English',()=>{
  for(const language of ['ko','en']){
    const a=app(language);a.write('qna');
    assert.match(a.root.innerHTML,language==='ko'?/공지 작성/:/Write a notice/);
    assert.match(a.root.innerHTML,language==='ko'?/공지 등록/:/Publish notice/);
    assert.match(a.root.innerHTML,/<input type="hidden" name="board" value="free">/);
    assert.match(a.root.innerHTML,/<input type="hidden" name="tag" value="notice">/);
    assert.doesNotMatch(a.root.innerHTML,/<select name="(?:board|tag)">/);
    assert.match(a.root.innerHTML,/href="#\/"/,'cancel returns to the home notice entry point');
    assert.equal(a.form.board.value,'free');assert.equal(a.form.tag.value,'notice');
    assert.equal(a.calls.length,0,'opening an editor does not publish or call a provider');
  }
});

test('a notice query does not grant ordinary users an admin editor or a notice tag',()=>{
  for(const language of ['ko','en']){
    const a=app(language,'user');a.write('qna');
    assert.match(a.root.innerHTML,/<select name="board">/);
    assert.match(a.root.innerHTML,/<select name="tag">/);
    assert.doesNotMatch(a.root.innerHTML,/value="notice"|공지 등록|Publish notice|공지 작성|Write a notice/);
    assert.equal(a.form.board.value,'qna');assert.equal(a.form.tag.value,'gen');
    assert.equal(a.run('siteNoticeWriteLink()'),'');assert.equal(a.calls.length,0);
  }
  const guest=app('ko',null);guest.write();
  assert.match(guest.context.location.hash,/\/login$/);assert.equal(guest.root.innerHTML,'');
});

test('regular and notice drafts stay separate across redraws and notice publishing uses canonical fields then its post route',async()=>{
  const a=app();a.write('study',null);
  a.form.title.value='Regular title';a.form.body.value='Regular draft';a.form.oninput();
  a.write('qna');assert.equal(a.form.title.value,'');assert.equal(a.form.body.value,'');
  a.form.title.value='Notice <title> "quoted"';a.form.body.value='Notice body <b>plain text</b>';
  a.form.board.value='qna';a.form.tag.value='gen';a.form.oninput();
  assert.equal(a.run('cm.draft.new.title'),'Regular title');
  assert.equal(a.run('cm.draft.notice.title'),'Notice <title> "quoted"');
  a.run('lang="en"');a.write();
  assert.equal(a.form.title.value,'Notice <title> "quoted"');assert.equal(a.form.board.value,'free');assert.equal(a.form.tag.value,'notice');
  assert.match(a.root.innerHTML,/&lt;title&gt; &quot;quoted&quot;/);assert.doesNotMatch(a.root.innerHTML,/<b>plain text<\/b>/);
  a.write('free',null);assert.equal(a.form.title.value,'Regular title');assert.equal(a.form.body.value,'Regular draft');assert.equal(a.form.board.value,'study');
  a.write();a.form.board.value='qna';a.form.tag.value='gen';
  let prevented=false;await a.form.onsubmit({preventDefault(){prevented=true;}});
  assert.equal(prevented,true);
  assert.deepEqual(a.calls,[{method:'POST',url:'/posts',data:{board:'free',tag:'notice',title:'Notice <title> "quoted"',body:'Notice body <b>plain text</b>',lang:'en'}}]);
  assert.equal(a.context.location.hash,'#/community/post/321');
  assert.equal(a.run('cm.draft.notice'),undefined);assert.equal(a.run('cm.draft.new.body'),'Regular draft');assert.equal(a.run('cm.boards'),null);
});

test('a failed notice submission keeps its draft and restores the submit control',async()=>{
  const a=app();a.write();a.form.title.value='Unpublished notice';a.form.body.value='Keep this draft';a.form.oninput();
  a.context.cmApi=async()=>{throw{code:'forbidden'};};
  await a.form.onsubmit({preventDefault(){}});
  assert.equal(a.submit.disabled,false);assert.ok(a.error.textContent);
  assert.equal(a.run('cm.draft.notice.body'),'Keep this draft');
  assert.equal(a.context.location.hash,'#/community/write/free?tag=notice');
});

test('the real community route forwards the notice query to the admin editor',async()=>{
  const a=app('en');await a.run('cmMount()');
  assert.match(a.root.innerHTML,/Write a notice/);assert.equal(a.form.tag.value,'notice');
  assert.equal(a.calls.length,0,'known identity and board metadata do not make an editor network request');
});

test('notice entry links are admin-only and the home slot updates after identity resolves',async()=>{
  for(const language of ['ko','en'])for(const role of [null,'user','admin']){
    const a=app(language,role),link=a.run('siteNoticeWriteLink()');
    if(role==='admin'){
      assert.match(link,/href="#\/community\/write\/free\?tag=notice"/);
      assert.match(link,language==='ko'?/공지 작성/:/Write a notice/);
    }else assert.equal(link,'');
  }
  const a=app('ko',null);let finishIdentity;
  a.context.cmLoadMe=()=>new Promise(resolve=>{finishIdentity=role=>{a.run(`cm.me={role:${JSON.stringify(role)},nickname:'Tester'}`);resolve();};});
  const slot=a.node('homeNoticeWrite');await a.run('mountHomeActivity()');
  assert.equal(slot.innerHTML,'');finishIdentity('admin');await new Promise(resolve=>setImmediate(resolve));
  assert.match(slot.innerHTML,/href="#\/community\/write\/free\?tag=notice"/);
  assert.ok(a.calls.every(call=>call.method==='GET'),'home entry discovery never publishes a notice');
});

test('the mailbox compose slot exposes the same notice route only to admins in both languages',()=>{
  for(const language of ['ko','en'])for(const role of [null,'user','admin']){
    const a=app(language,role),slots=new Map();
    const dialog={open:true,querySelector:selector=>{if(!slots.has(selector))slots.set(selector,dummy());return slots.get(selector);},querySelectorAll:()=>[]};
    a.context.mailState={dialog,language,filter:'updates',posts:[],expanded:new Set(),total:0,loading:false};
    a.run('siteMailboxState=mailState;paintSiteMailbox(mailState)');
    const compose=slots.get('.hl-mail-compose').innerHTML;
    if(role==='admin')assert.match(compose,/href="#\/community\/write\/free\?tag=notice"/);
    else assert.equal(compose,'');
    assert.equal(a.calls.length,0,'rendering the compose entry does not post or fetch a provider');
  }
});
