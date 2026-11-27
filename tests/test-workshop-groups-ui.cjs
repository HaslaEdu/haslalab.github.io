/* The shared-storage groups on #/workshop/storage (workshop-class-storage.js): the addresses, the group cards, joining
   with a code, one group's detail for the owner and for a member, and the invite code dialog. */
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {JSDOM}=require('node:module').createRequire(path.resolve(__dirname,'../community/package.json'))('jsdom');
const source=fs.readFileSync(path.join(__dirname,'..','workshop-class-storage.js'),'utf8');
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const flush=async(n=8)=>{for(let i=0;i<n;i++)await new Promise(r=>setTimeout(r,0));};

const GROUPS=[
  {id:3,name:'물리 동아리',description:'월요일 실험',role:'owner',approval:false,member_count:8,pending_requests:2,owner:{nickname:'박선생',avatar:'avKeyPark1'},
    avatars:[{nickname:'박선생',avatar:'avKeyPark1'},{nickname:'민지',avatar:null},{nickname:'서준',avatar:'avKeySeo99'},{nickname:'하은',avatar:null},{nickname:'도윤',avatar:null}]},
  {id:4,name:'2학년 3반',description:'',role:'member',approval:true,member_count:2,owner:{nickname:'김선생',avatar:null},avatars:[{nickname:'김선생',avatar:null},{nickname:'박선생',avatar:'avKeyPark1'}]}
];
const DETAIL={group:{id:3,name:'물리 동아리',description:'월요일 실험',created_at:1_790_000_000,approval:false,role:'owner',owner:{nickname:'박선생',avatar:'avKeyPark1'},
    member_count:3,seats:31,storage:{used:3*1048576,files:4,shares:2,quota:100*1048576},legacy_code:true,class_code:'ABC234'},
  members:[{nickname:'박선생',avatar:'avKeyPark1',role:'owner',joined_at:1_790_000_000,last_active_at:1_800_000_000,me:true},
    {nickname:'민지',avatar:null,role:'admin',joined_at:1_790_100_000,last_active_at:null,me:false},
    {nickname:'<img src=x onerror=alert(1)>',avatar:null,role:'member',joined_at:1_790_200_000,last_active_at:1_799_000_000,me:false}],
  invites:[{id:'1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed',hint:'AB··-····',created_at:1_799_000_000,expires_at:1_800_600_000,max_uses:50,uses:3,created_by:'박선생'}],
  requests:[{nickname:'서준',avatar:'avKeySeo99',requested_at:1_799_500_000}]};

function page(hash='#/workshop/storage',{groups=GROUPS,detail=DETAIL,routes={}}={}){
  const dom=new JSDOM('<!doctype html><body><div id="root"><button data-ws-invites></button><section data-class-shares></section></div></body>',{url:'https://haslalab.org/'+hash,runScripts:'outside-only'});
  const w=dom.window;
  if(!w.HTMLDialogElement.prototype.showModal)w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'));};
  w.confirm=()=>true;
  const calls=[];
  const api=async(method,p,body)=>{
    calls.push(JSON.parse(JSON.stringify([method,p,body??null])));
    const key=method+' '+p;
    if(routes[key])return routes[key](body);
    if(key==='GET /workshop/storage/shared')return{shares:[]};
    if(key==='GET /workshop/storage/groups')return{groups};
    if(/^GET \/workshop\/storage\/groups\/\d+$/.test(key))return detail;
    return{ok:true};
  };
  w.eval(source);
  const root=w.document.getElementById('root');
  const av=(name,cls,key)=>key?`<img class="cmav ${cls}" src="https://api.test/api/avatar/${key}" alt="">`:`<span class="cmav ${cls}">${esc([...String(name)][0])}</span>`;
  w.HL_WS_CLASS_STORAGE({host:root.querySelector('[data-class-shares]'),root,api,fetchFile:async()=>{},text:(ko)=>ko,esc,error:c=>'error:'+c,files:[],folders:[],here:()=>true,av});
  return{w,root,calls,doc:w.document};
}

test('addresses: ?group= opens a group, ?code= and the old ?invite= fill in the code',()=>{
  const {w}=page();
  const R=w.HL_WS_CLASS_STORAGE.route;
  const plain=x=>JSON.parse(JSON.stringify(x));
  assert.deepEqual(plain(R('#/workshop/storage?group=12')),{group:12,code:''});
  assert.deepEqual(plain(R('#/workshop/storage?code=abcd-ef23')),{group:null,code:'ABCD-EF23'});
  assert.deepEqual(plain(R('#/workshop/storage?code=ABCDEF23')),{group:null,code:'ABCD-EF23'});
  assert.deepEqual(plain(R('#/workshop/storage?invite=ABC234')),{group:null,code:'ABC2-34'},'a six-letter class code still goes in');
  assert.deepEqual(plain(R('#/workshop/storage?group=x&code=<script>')),{group:null,code:''});
  assert.equal(w.HL_WS_CLASS_STORAGE.formatCode('ab cd e'),'ABCD-E');
  assert.equal(w.HL_WS_CLASS_STORAGE.codeOk('ABCD-EF2O'),false,'O is not in the alphabet');
});

test('the group cards: stacked faces (five and +n), role, member count and waiting requests',async()=>{
  const {root}=page();
  await flush();
  const cards=[...root.querySelectorAll('.wsg-card')];
  assert.equal(cards.length,2);
  const first=cards[0];
  assert.match(first.textContent,/물리 동아리/);assert.match(first.textContent,/소유자/);assert.match(first.textContent,/8명/);assert.match(first.textContent,/요청 2/);
  assert.equal(first.querySelectorAll('.wsg-stack .cmav').length,5);
  assert.equal(first.querySelector('.wsg-more').textContent,'+3');
  assert.equal(first.querySelector('.wsg-stack img').getAttribute('src'),'https://api.test/api/avatar/avKeyPark1');
  assert.ok(!cards[1].querySelector('.wsg-more'),'no +n when everyone is shown');
  assert.match(cards[1].textContent,/멤버/);
  assert.ok(root.querySelector('[data-wsg-join] input[name=code]'),'코드로 참여 is on the list');
});

test('joining by code: the link fills the code, the group is shown to confirm, then joined and opened',async()=>{
  const {root,calls,w}=page('#/workshop/storage?code=abcd-ef23',{routes:{
    'POST /workshop/storage/groups/preview':()=>({group:{name:'과학 탐구반',description:'토요일',owner:{nickname:'이선생',avatar:'avKeyLee123'},member_count:12,approval:false,member:false,pending:false}}),
    'POST /workshop/storage/groups/join':()=>({status:'joined',group:{id:3,name:'과학 탐구반'}})}});
  await flush();
  assert.equal(root.querySelector('[data-wsg-join] input').value,'ABCD-EF23');
  assert.deepEqual(calls.find(c=>c[1]==='/workshop/storage/groups/preview')[2],{code:'ABCD-EF23'});
  const card=root.querySelector('.wsg-confirm');
  assert.match(card.textContent,/과학 탐구반/);assert.match(card.textContent,/이선생 님의 그룹/);assert.match(card.textContent,/멤버 12명/);
  assert.equal(card.querySelector('img').getAttribute('src'),'https://api.test/api/avatar/avKeyLee123');
  card.querySelector('[data-wsg-do]').click();
  await flush();
  assert.deepEqual(calls.find(c=>c[1]==='/workshop/storage/groups/join')[2],{code:'ABCD-EF23'});
  assert.equal(w.location.hash,'#/workshop/storage?group=3','the code leaves the address and the group opens');
  assert.match(root.querySelector('[data-wsg-status]').textContent,/참여했습니다/);
});

test('joining a group that asks for approval sends a request; a wrong code says so and joins nothing',async()=>{
  const {root,calls}=page('#/workshop/storage',{routes:{
    'POST /workshop/storage/groups/preview':b=>{if(b.code==='ZZZZ-ZZZZ')throw{code:'invite_not_found'};return{group:{name:'승인반',description:'',owner:{nickname:'김선생',avatar:null},member_count:3,approval:true,member:false,pending:false}};},
    'POST /workshop/storage/groups/join':()=>({status:'pending',group:{id:9,name:'승인반'}})}});
  await flush();
  const form=root.querySelector('[data-wsg-join]'),input=form.elements.code;
  input.value='zzzzzzzz';input.dispatchEvent(new input.ownerDocument.defaultView.Event('input'));
  assert.equal(input.value,'ZZZZ-ZZZZ');
  form.requestSubmit();await flush();
  assert.match(root.querySelector('[data-wsg-status]').textContent,/참여할 수 있는 그룹이 없습니다/);
  input.value='abc';form.requestSubmit();await flush();
  assert.match(root.querySelector('[data-wsg-status]').textContent,/초대 코드를 확인/);
  input.value='QRST-UV23';form.requestSubmit();await flush();
  const card=root.querySelector('.wsg-confirm');
  assert.match(card.textContent,/승인하면 참여/);
  assert.equal(card.querySelector('[data-wsg-do]').textContent,'참여 요청 보내기');
  card.querySelector('[data-wsg-do]').click();await flush();
  assert.match(root.querySelector('[data-wsg-status]').textContent,/참여 요청을 보냈습니다/);
  assert.equal(calls.filter(c=>c[1]==='/workshop/storage/groups/join').length,1);
});

test('the owner\'s detail: members with faces, nickname, role and dates; codes, requests, settings, transfer and delete',async()=>{
  const {root,calls}=page('#/workshop/storage?group=3');
  await flush();
  assert.ok(calls.some(c=>c[0]==='GET'&&c[1]==='/workshop/storage/groups/3'));
  const rows=[...root.querySelectorAll('[data-wsg-members] li')];
  assert.equal(rows.length,3);
  assert.match(rows[0].textContent,/박선생/);assert.match(rows[0].textContent,/소유자/);assert.match(rows[0].textContent,/\(나\)/);
  assert.equal(rows[0].querySelector('img').getAttribute('src'),'https://api.test/api/avatar/avKeyPark1');
  assert.equal(rows[1].querySelector('[data-wsg-role]').value,'admin');assert.match(rows[1].textContent,/참여/);
  assert.ok(!rows[2].querySelector('img[src="x"]'),'a nickname is text, not markup');
  assert.match(rows[2].innerHTML,/&lt;img src=x/);
  assert.match(rows[2].textContent,/최근 활동/);
  assert.ok(rows[1].querySelector('[data-wsg-role]')&&rows[1].querySelector('[data-wsg-remove]'),'the owner changes roles and removes');
  assert.ok(!rows[0].querySelector('[data-wsg-remove]'));
  assert.match(root.textContent,/공유 자료 3\.0 MB \/ 100\.0 MB/);
  assert.match(root.textContent,/AB로 시작하는 코드/);assert.match(root.textContent,/3\/50회 사용/);assert.match(root.textContent,/ABC234/);
  assert.match(root.querySelector('[data-wsg-approve]').closest('li').textContent,/서준/);
  /* role change and removal go to the member's nickname */
  const sel=rows[1].querySelector('[data-wsg-role]');sel.value='member';sel.dispatchEvent(new sel.ownerDocument.defaultView.Event('change'));await flush();
  assert.deepEqual(calls.find(c=>c[0]==='PATCH'&&c[1].includes('/members/')),['PATCH','/workshop/storage/groups/3/members/'+encodeURIComponent('민지'),{role:'member'}]);
  root.querySelector('[data-wsg-remove]').click();await flush();
  assert.ok(calls.some(c=>c[0]==='DELETE'&&c[1]==='/workshop/storage/groups/3/members/'+encodeURIComponent('민지')));
  root.querySelector('[data-wsg-approve]').click();await flush();
  assert.deepEqual(calls.find(c=>c[1].includes('/requests/')),['POST','/workshop/storage/groups/3/requests/'+encodeURIComponent('서준'),{approve:true}]);
  /* delete waits for the name */
  const del=root.querySelector('[data-wsg-delete]'),typed=root.querySelector('[data-wsg-confirm-name]');
  assert.equal(del.disabled,true);
  typed.value='물리 동아리';typed.dispatchEvent(new typed.ownerDocument.defaultView.Event('input'));
  assert.equal(del.disabled,false);
  del.click();await flush();
  assert.ok(calls.some(c=>c[0]==='DELETE'&&c[1]==='/workshop/storage/groups/3?confirm='+encodeURIComponent('물리 동아리')));
});

test('a member\'s detail: no codes, no requests, no management, a leave button',async()=>{
  const member={...DETAIL,group:{...DETAIL.group,role:'member',legacy_code:undefined,class_code:undefined},members:DETAIL.members.map(m=>{const {last_active_at,...r}=m;return{...r,me:m.nickname==='민지'};})};
  delete member.invites;delete member.requests;
  const {root,calls}=page('#/workshop/storage?group=3',{detail:member});
  await flush();
  assert.ok(!root.querySelector('[data-wsg-invite]')&&!root.querySelector('[data-wsg-role]')&&!root.querySelector('[data-wsg-remove]')&&!root.querySelector('[data-wsg-settings]'));
  assert.doesNotMatch(root.textContent,/최근 활동/);
  root.querySelector('[data-wsg-leave]').click();await flush();
  assert.ok(calls.some(c=>c[0]==='POST'&&c[1]==='/workshop/storage/groups/3/leave'));
});

test('the invite code dialog: expiry and uses, then the code and its link shown once',async()=>{
  const {root,calls,doc}=page('#/workshop/storage?group=3',{routes:{'POST /workshop/storage/groups/3/invites':()=>({code:'K7MQ-2XPA',invite:{id:'x',hint:'K7··-····',created_at:1,expires_at:null,max_uses:10,uses:0}})}});
  await flush();
  root.querySelector('[data-wsg-invite]').click();
  const dialog=doc.querySelector('dialog.wsg-dialog');
  assert.ok(dialog.open);
  const f=dialog.querySelector('form').elements;
  assert.deepEqual([...f.expires.options].map(o=>o.value),['1d','7d','never']);
  assert.deepEqual([...f.max_uses.options].map(o=>o.value),['1','10','50','']);
  f.expires.value='never';f.max_uses.value='10';
  dialog.querySelector('form').requestSubmit();await flush();
  assert.deepEqual(calls.find(c=>c[1]==='/workshop/storage/groups/3/invites')[2],{expires:'never',max_uses:10});
  const shown=doc.querySelector('[data-wsg-code]');
  assert.equal(shown.textContent,'K7MQ-2XPA');
  assert.equal(doc.querySelector('[data-wsg-link]').value,'https://haslalab.org/#/workshop/storage?code=K7MQ-2XPA');
  assert.match(shown.closest('dialog').textContent,/다시 볼 수 없습니다/);
});
