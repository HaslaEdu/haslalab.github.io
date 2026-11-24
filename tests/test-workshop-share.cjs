const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const read=file=>fs.readFileSync(path.join(__dirname,'..',file),'utf8');
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function page(hash='#/workshop/share'){
  const context={window:{},location:{hash,origin:'https://haslalab.org',pathname:'/'},URLSearchParams,URL,TextEncoder,btoa,console,document:{getElementById:()=>null,head:{append(){}},createElement:()=>({}),documentElement:{dataset:{}}}};
  context.window=context;vm.createContext(context);vm.runInContext(read('workshop-share.js'),context,{filename:'workshop-share.js'});
  const ctx={ko:true,uiLang:'ko',LX:s=>s,esc,api:async()=>({}),base:()=>'https://api.test',av:()=>'',me:async()=>null,here:()=>true,title:'작품 공유',workshop:'워크샵'};
  return{P:context.HL_SHARE_PAGE,context,ctx};
}
function publisher(fetchImpl,store={hlCmTok:'t'.repeat(32)}){
  const context={window:{},localStorage:{getItem:k=>store[k]??null},fetch:fetchImpl,location:{assign(){}},TextEncoder,URL,console,JSON,Promise,encodeURIComponent};
  context.window=context;vm.createContext(context);vm.runInContext(read('share-publish.js'),context,{filename:'share-publish.js'});
  return context.HL_SHARE;
}

test('the sharing place\'s addresses: explore, a project, an author',()=>{
  const {P,context}=page();
  const r=h=>{context.location.hash=h;const x=P._route();return [x.page,x.id??null];};
  assert.deepEqual(r('#/workshop/share'),['explore',null]);assert.deepEqual(r('#/workshop/share?tab=new&type=figure'),['explore',null]);
  assert.deepEqual(r('#/workshop/share/42'),['project',42]);assert.deepEqual(r('#/workshop/share/user/7'),['user',7]);
  assert.deepEqual(r('#/workshop/share/abc'),['explore',null]);assert.deepEqual(r('#/workshop/share/user/x'),['explore',null]);
});

test('descriptions: escaped first, then bold, code, lists and https links only',()=>{
  const {P}=page();
  const html=P._md('**F = ma** and `x<y`\n\n- one\n- two <img src=x onerror=alert(1)>\n\nsee https://haslalab.org/a?b=1&c=2 or javascript:alert(1) "q"');
  assert.match(html,/<strong>F = ma<\/strong>/);assert.match(html,/<code>x&lt;y<\/code>/);assert.match(html,/<ul><li>one<\/li><li>two &lt;img src=x onerror=alert\(1\)&gt;<\/li><\/ul>/);
  assert.match(html,/<a href="https:\/\/haslalab\.org\/a\?b=1&amp;c=2" target="_blank" rel="nofollow noopener noreferrer ugc">/);
  assert.doesNotMatch(html,/<img|href="javascript/);assert.match(html,/&quot;q&quot;/);
  assert.equal(P._md('<script>alert(1)</script>'),'<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>');
});

test('the explore shell: breadcrumbs back to the Workshop, one heading, and the page draws the rest',()=>{
  const {P,ctx}=page();
  const html=P.view(ctx);
  assert.match(html,/href="#\/workshop">워크샵<\/a> \/ 작품 공유/);assert.equal((html.match(/<h1\b/g)||[]).length,1);assert.match(html,/id="shrBody"/);
});

test('projects run only in the opaque sandbox; thumbnails and figures are images; nothing a member wrote is markup',()=>{
  const js=read('workshop-share.js');
  assert.match(js,/<iframe sandbox="allow-scripts" src="sim-sandbox\.html"/);assert.doesNotMatch(js,/allow-same-origin/);
  assert.match(js,/e\.source!==f\.contentWindow\|\|e\.origin!=='null'/,'messages only from the sandbox frame');
  assert.match(js,/<img class="shr-fig" alt="\$\{esc\(p\.title\)\}" src="data:image\/svg\+xml;base64,/,'a figure is drawn into an <img>');
  assert.match(js,/<img src="\$\{esc\(thumbUrl\(it\)\)\}"/,'thumbnails come from the API as images');
  assert.doesNotMatch(js,/innerHTML\s*=\s*(?:p|it|c|d)\.(?:description|howto|notes|body|title|code)/);
  for(const f of ['title','nickname','body','key'])assert.ok(!new RegExp('\\$\\{(?:p|it|c|u|d\\.original)\\.'+f+'\\}').test(js),'unescaped '+f);
  const sandbox=read('sim-sandbox.html');assert.match(sandbox,/connect-src 'none'/);
});

test('HaslaLab\'s own look: the site\'s ink and violet, no other gallery\'s colours or names',()=>{
  const js=read('workshop-share.js');
  assert.match(js,/--sh-ink:#263247/);assert.match(js,/--sh-acc:#7059a4/);
  assert.doesNotMatch(js,/#855CD6|#4D97FF|#FFAB19|#00B6B1|#4F80FF|scratch|entry\b|playentry/i);
});

test('HL_SHARE.publish checks first, then posts to /api/share with the member\'s token',async()=>{
  const sent=[];
  const S=publisher(async(url,o)=>{sent.push([url,o]);return{ok:true,json:async()=>({id:5,url:'#/workshop/share/5'})};});
  assert.deepEqual([...S.check({type:'sim',title:'x',payload:{code:''}})],['bad_payload']);
  assert.deepEqual([...S.check({type:'video',title:'',payload:{}})],['bad_type','bad_title']);
  assert.deepEqual([...S.check({type:'python',title:'P',payload:{statement:'s',grader:'print(1)'}})],['bad_payload']);
  assert.deepEqual([...S.check({type:'set',title:'S',payload:{items:[{key:'ap1:1'}]},tags:['a','b'],topic:'optics'})],[]);
  assert.deepEqual([...S.check({type:'figure',title:'F',payload:{scene:{objects:[]}},thumbnail:'data:text/html,<b>'})],['bad_thumbnail']);
  assert.deepEqual([...S.check({type:'sim',title:'Mine',creation_id:3})],[],'publishing an existing creation needs no payload');
  await assert.rejects(S.publish({type:'sim',title:'',payload:{code:'x'}}),e=>e.code==='bad_title');
  const r=await S.publish({type:'sim',title:'Pendulum',description:'Swing',payload:{code:'loop(()=>{})'},extra:'dropped'});
  assert.equal(r.id,5);
  const [url,o]=sent[0];assert.equal(url,'https://haslalab-community-edge.haslalab.workers.dev/api/share');assert.equal(o.method,'POST');
  assert.equal(o.headers.Authorization,'Bearer '+'t'.repeat(32));assert.deepEqual(Object.keys(JSON.parse(o.body)).sort(),['description','payload','title','type']);
  await S.update(5,{title:'P2'});assert.equal(sent[1][0],'https://haslalab-community-edge.haslalab.workers.dev/api/share/5');assert.equal(sent[1][1].method,'PATCH');
  await S.remix(5);assert.equal(sent[2][0].endsWith('/api/share/5/remix'),true);
  assert.match(S.svgThumb('<svg></svg>'),/^data:image\/svg\+xml;charset=utf-8,%3Csvg/);
  /* only HaslaLab's own API hosts, as on the rest of the site */
  const evil=publisher(async(url)=>{sent.push([url]);return{ok:false,status:401,json:async()=>({error:'login_required'})};},{hlCmApi:'https://evil.example',hlCmTok:''});
  await assert.rejects(evil.get(1),e=>e.code==='login_required');assert.match(sent.at(-1)[0],/^https:\/\/haslalab-community-edge\.haslalab\.workers\.dev\/api\/share\/1$/);
});

test('index.html draws the sharing place from workshop-share.js and loads both scripts with their digests',()=>{
  const html=read('index.html');
  assert.match(html,/<script src="share-publish\.js\?v=[0-9a-f]{12}"><\/script>\n<script src="workshop-share\.js\?v=[0-9a-f]{12}"><\/script>/);
  assert.match(html,/second==="share"\?viewWorkshopShare\(\)/);assert.match(html,/if\(second==="share"\)\{window\.HL_SHARE_PAGE\?\.mount\(workshopShareCtx\(generation\)\);return;\}/);
});
