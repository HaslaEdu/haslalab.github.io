/* The makers' "공유하기" step (share-makers.js): the dialog's checks, the problem set built from teach.js's paper (and
   accepted by the server's cleanSet), a shared set opened back as a paper, and creation_id for remix drafts and saved
   creations; plus the wiring in teach.js, create-studio.js, the two pages and index.html. */
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const read=f=>fs.readFileSync(path.join(__dirname,'..',f),'utf8');
function load(){
  const context={window:{},localStorage:{getItem:()=>null},fetch:async()=>({ok:true,json:async()=>({})}),location:{assign(){}},TextEncoder,URL,console,JSON,Promise,encodeURIComponent};
  context.window=context;vm.createContext(context);
  vm.runInContext(read('share-publish.js'),context,{filename:'share-publish.js'});
  vm.runInContext(read('share-makers.js'),context,{filename:'share-makers.js'});
  return context.HL_SHARE_MAKER;
}
const plain=x=>JSON.parse(JSON.stringify(x));
const SVG='data:image/svg+xml;base64,'+Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><line x1="0" y1="0" x2="10" y2="10" stroke="#000"/></svg>').toString('base64');
const PAPER={title:'1학기 중간고사',school:'하슬라고',info:'1학년',minutes:'50',note:'계산기 사용 가능',two:true,key:true,store:{id:'f'.repeat(32),name:'x.json'},
  share:{id:9,published:true},items:[
    {key:'ap1:12',pts:4,bp:{unit:'역학',level:'apply'}},
    {key:'own:abc',pts:3,own:{q:'공의 속력은? $v=\\sqrt{2gh}$',answer:'14',unit:'m/s',sol:'에너지 보존',choices:['7','14','28'],correct:1,rubric:[{desc:'식',pts:2}],fig:{src:SVG,w:300,h:200,scene:{objects:[1]}}}},
    {key:'own:fig',pts:2,own:{q:'',answer:'',unit:'',sol:'',fig:{src:SVG,w:300,h:200}}},
    {key:'own:empty',pts:2,own:{q:'  ',answer:'',unit:'',sol:''}},
    {key:'bad key with spaces',pts:1},{key:'own:nobody',pts:1}]};

test('the set payload: the paper\'s heading and items only, in the shapes the server keeps',async()=>{
  const M=load(),p=plain(M.paperPayload(PAPER,'ko'));
  assert.deepEqual(Object.keys(p).sort(),['info','items','minutes','title']);
  assert.equal(p.title,'1학기 중간고사');assert.equal(p.info,'하슬라고 · 1학년');assert.equal(p.minutes,50);
  assert.equal(p.items.length,3,'empty own problems, bad keys and own keys without a problem are left out');
  assert.deepEqual(p.items[0],{key:'ap1:12',pts:4});
  const own=p.items[1].own;
  assert.deepEqual(Object.keys(own).sort(),['answer','choices','correct','fig','q','sol','unit']);
  assert.deepEqual(own.fig,{src:SVG,w:300,h:200},'a figure goes as its picture, without the scene');
  assert.equal(p.items[2].own.q,'(그림)','a problem that is only a figure gets a stand-in text');
  assert.ok(!JSON.stringify(p).includes('store')&&!JSON.stringify(p).includes('rubric')&&!JSON.stringify(p).includes('share'));
  const {cleanSet}=await import('../community/src/workshop-share.js');
  const kept=cleanSet(p);assert.ok(kept&&kept.items.length===3,'the server accepts it');
  assert.equal(kept.items[1].own.correct,1);assert.ok(kept.items[1].own.fig.src.startsWith('data:image/svg+xml;base64,'));
  const many={items:Array.from({length:130},(_,i)=>({key:'ap1:'+i,pts:1}))};
  assert.equal(M.paperPayload(many).items.length,100,'at most 100 problems');
});

test('a shared set opens back as the fields of a new paper',()=>{
  const M=load(),back=plain(M.paperFromPayload(M.paperPayload(PAPER,'ko')));
  assert.equal(back.title,'1학기 중간고사');assert.equal(back.minutes,'50');assert.equal(back.items.length,3);
  assert.equal(M.paperFromPayload(null),null);assert.equal(M.paperFromPayload({items:'x'}),null);
  assert.equal(M.paperFromPayload({items:[],minutes:0}).minutes,'');
});

test('the dialog\'s checks: HL_SHARE.check\'s codes shown as messages, an update checks only what it sends',()=>{
  const M=load();
  const input=f=>M.publishInput({type:'set',form:f,payload:M.paperPayload(PAPER)});
  assert.deepEqual(plain(M.formErrors(input({title:'중간고사',tags:'역학, 에너지',topic:'mechanics'}),'ko')),[]);
  const bad=plain(M.formErrors(input({title:'  ',tags:'a,b,c,d,e,f,g,h,i',description:'x'.repeat(3001)}),'ko'));
  assert.deepEqual(bad.map(e=>e.code),['bad_title','bad_description','bad_tags']);
  assert.equal(bad[0].text,'제목을 1~80자로 적어 주세요.');
  assert.deepEqual(plain(M.formErrors(input({title:'x'.repeat(81)}),'en')).map(e=>e.text),['Give it a title of 1–80 characters.']);
  assert.deepEqual(plain(M.formErrors(M.publishInput({type:'set',form:{title:'S'},payload:{items:[]}}),'ko')).map(e=>e.code),['bad_payload'],'an empty paper cannot be shared');
  assert.deepEqual(plain(M.formErrors({title:'S',topic:'cooking'},'ko',true)).map(e=>e.code),['bad_topic']);
  assert.deepEqual(plain(M.formErrors(M.publishInput({type:'python',form:{title:'P'},payload:{statement:'s',grader:'print(1)'}}),'ko',false,e=>'own:'+e.code)).map(e=>e.text),['올릴 내용이 비어 있거나 형식이 맞지 않습니다.']);
  assert.deepEqual(plain(M.readForm({title:' A ',tags:'#진자, 주기,,',topic:'nope'})),{title:'A',description:'',howto:'',notes:'',tags:['진자','주기'],topic:'other'});
});

test('creation_id for a remix draft or a saved creation; remix_of only for someone else\'s set opened as new',()=>{
  const M=load(),form={title:'Remix: 진자',description:'d',howto:'h',notes:'n',tags:['진자'],topic:'mechanics'};
  const draft=plain(M.publishInput({type:'set',form,payload:{items:[{key:'ap1:1'}]},creationId:41,remixOf:7}));
  assert.equal(draft.creation_id,41);assert.equal(draft.remix_of,undefined);
  assert.deepEqual(Object.keys(draft).sort(),['creation_id','description','howto','notes','payload','tags','title','topic','type']);
  assert.equal(plain(M.publishInput({type:'set',form,payload:{items:[{key:'ap1:1'}]},remixOf:7})).remix_of,7);
  assert.equal(plain(M.publishInput({type:'sim',form,creationId:0})).creation_id,undefined);
  assert.equal(M.topicGuess(['em/circuits','mechanics/energy','em/fields',undefined]),'em');assert.equal(M.topicGuess([]),'other');
});

test('publishing a remix draft sends creation_id to /api/share, and the server publishes that draft',async()=>{
  const sent=[];
  const context={window:{},localStorage:{getItem:k=>k==='hlCmTok'?'t'.repeat(32):null},fetch:async(u,o)=>{sent.push([u,o]);return{ok:true,json:async()=>({id:41,url:'#/workshop/share/41'})};},location:{assign(){}},TextEncoder,URL,console,JSON,Promise,encodeURIComponent};
  context.window=context;vm.createContext(context);
  vm.runInContext(read('share-publish.js'),context);vm.runInContext(read('share-makers.js'),context);
  const M=context.HL_SHARE_MAKER,H=context.HL_SHARE;
  const r=await H.publish(M.publishInput({type:'sim',form:{title:'Pendulum (remix)'},payload:{code:'hl.loop(()=>{})'},creationId:41}));
  assert.equal(r.id,41);const body=JSON.parse(sent[0][1].body);assert.equal(body.creation_id,41);assert.equal(body.type,'sim');
});

test('teach.js: 공유하기 for signed-in members, publish/update/unpublish, the remix opened as a new paper after asking',()=>{
  const js=read('teach.js');
  assert.match(js,/if\(!token\(\)\)\{row\.innerHTML=`<span class="note">\$\{esc\(SH\.login\)\}<\/span>`;return;\}/,'logged-in members only');
  assert.match(js,/publishInput\(\{type:'set',form:fv,payload:sharePayload\(\),thumbnail,creationId:mine,remixOf:sh\.remixOf\}\)/);
  assert.match(js,/update:input=>HS\(\)\.update\(mine,input\)/);assert.match(js,/HS\(\)\.unpublish\(sh\.id\)/);assert.match(js,/HS\(\)\.open\(sh\.id\)/);
  assert.match(js,/const sid=params\.get\('share'\);if\(\/\^\\d\{1,9\}\$\/\.test\(sid\|\|''\)\)loadShared\(\+sid\)/);
  assert.match(js,/if\(paper\.items\.length&&!paper\.store\?\.id&&!confirm\(SH\.ask\)\)/,'unsaved changes are asked about first');
  assert.match(js,/share:p\.mine\?\{id,from:id,published:p\.status==='public',meta\}:\{from:id,remixOf:id/,'one\'s own draft is published by its id');
  assert.match(js,/items:np\.items\.map\(cleanItem\)\.filter\(Boolean\)/,'shared items are cleaned like saved files');
  const html=read('teach.html');
  assert.ok(html.indexOf('src="share-publish.js?v=')>0&&html.indexOf('src="share-makers.js?v=')>html.indexOf('src="share-publish.js?v=')&&html.indexOf('src="share-makers.js?v=')<html.indexOf('src="teach.js?v='));
  assert.match(html,/connect-src 'self' https:\/\/\*\.haslalab\.workers\.dev;/,'the sharing API host is allowed');
  assert.match(read('index.html'),/if\(\/\^\\d\{1,9\}\$\/\.test\(asked\.get\("share"\)\|\|""\)\)query\.set\("share",asked\.get\("share"\)\);/,'#/workshop/make?share=N reaches the frame');
});

test('create-studio.js: save, then share with creation_id; the share dialog replaces the bare publish',()=>{
  const js=read('create-studio.js');
  assert.match(js,/publish:async input=>\{const cid=await saveCreation\(\);return HS\.publish\(\{\.\.\.withoutPayload\(input\),creation_id:cid\}\);\}/);
  assert.match(js,/build:fv=>SM\.publishInput\(\{type,form:fv,payload:sharePayload\(\),creationId:savedId\|\|undefined\}\)/);
  assert.match(js,/const type=d\.kind==='sim'\?'sim':'python'/);
  assert.match(js,/let savedId=\/\^\\d\{1,9\}\$\/\.test\(String\(id\|\|''\)\)\?\+id:null;/,'the id from the address is sent as a number');
  assert.match(js,/if\(savedId\)await ctx\.api\('\/api\/creations\/'\+savedId,'PATCH',body\)/,'an opened creation or remix draft is saved in place');
  const html=read('create.html');
  assert.ok(html.indexOf('src="share-makers.js?v=')>html.indexOf('src="share-publish.js?v=')&&html.indexOf('src="share-makers.js?v=')<html.indexOf('src="create-studio.js?v='));
  const sm=read('share-makers.js');
  assert.doesNotMatch(sm,/innerHTML\s*=\s*[^`'"]*\b(?:v|o\.values|fv|input)\./,'what members typed goes in through .value and textContent');
});
