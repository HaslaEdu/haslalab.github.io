const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname,'..');
const code = '11111111-1111-4111-8111-111111111111.'+'x'.repeat(43);

test('monthly scan entry reuses the exam scanner and keeps the scoped grant out of requests and referrers',async()=>{
  const {monthlyScanTarget} = await import('../sim/monthly-scan.mjs');
  const url = new URL(monthlyScanTarget('https://haslalab.org/sim/monthly-scan.html#'+new URLSearchParams({c:code,l:'en'})));
  assert.equal(url.pathname,'/sim/scan.html');assert.equal(url.search,'?monthly=1');
  assert.equal(new URLSearchParams(url.hash.slice(1)).get('c'),code);
  assert.ok(!url.search.includes(code));
  const html = fs.readFileSync(path.join(root,'sim/monthly-scan.html'),'utf8');
  assert.match(html,/name="referrer" content="no-referrer"/);
  assert.match(html,/monthly-scan\.mjs/);
});

test('scan links reject malformed grants and untrusted API redirects',async()=>{
  const {monthlyScanTarget} = await import('../sim/monthly-scan.mjs');
  const link = params => 'https://haslalab.org/sim/monthly-scan.html#'+new URLSearchParams(params);
  assert.equal(monthlyScanTarget(link({c:'short'})),null);
  assert.equal(monthlyScanTarget(link({c:'monthly-scan-grant-0123456789abcdef'})),null,'only the scoped uuid.raw grant shape is accepted');
  assert.equal(monthlyScanTarget(link({c:'Bearer '+code})),null);
  assert.equal(monthlyScanTarget(link({c:code,a:'https://untrusted.example/'})),null);
  assert.equal(monthlyScanTarget(link({c:code,a:'https://user:secret@haslalab-community-edge.haslalab.workers.dev/'})),null);
  assert.equal(monthlyScanTarget(link({c:code,a:'https://haslalab-community-edge.haslalab.workers.dev/api'})),null);
  assert.match(monthlyScanTarget(link({c:code,a:'http://localhost:8864',l:'ko'})),/a=http%3A%2F%2Flocalhost%3A8864/);
});

test('monthly sending preserves the separate original and corrected scan using the shared readable-resolution encoder',async()=>{
  const {monthlyScanPayload} = await import('../sim/monthly-scan.mjs');
  const scan = new Blob(['corrected page'],{type:'image/png'}), capture = new Blob(['original camera image'],{type:'image/jpeg'});
  const rotated = new Blob(['rotated preview'],{type:'image/png'}), calls=[];
  const form = await monthlyScanPayload({blob:scan,file:rotated,captureFile:capture},async(blob,options)=>{calls.push({blob,options});return blob;});
  assert.equal(await form.get('image').text(),'corrected page');assert.equal(form.get('image').type,'image/png');
  assert.equal(await form.get('original_image').text(),'original camera image');assert.equal(form.get('original_image').type,'image/jpeg');
  assert.deepEqual(calls.map(call=>call.blob),[scan,capture]);assert.ok(calls.every(call=>call.options.maxBytes===4*1024*1024));
  assert.equal(form.get('token'),null,'credentials are carried by the transport header');
  assert.match(form.get('request_id'),/^[A-Za-z0-9_-]{16,100}$/);
  const same=[];await monthlyScanPayload({blob:capture,file:capture,captureFile:capture},async(blob)=>{same.push(blob);return blob;});
  assert.equal(same.length,1,'an already-small original does not need a second encoding');
});

function scannerContext({monthly,hash,storage=new Map(),request,payload}={}) {
  let source=fs.readFileSync(path.join(root,'sim/scan.html'),'utf8').match(/<script type="module">([\s\S]*?)<\/script>/)[1];
  source=source.replace(/^import[^\n]+\n/m,'');
  source=source.replace(/^const monthlyScanPayload = [^\n]+/m,'const monthlyScanPayload = (...args) => monthlyFixturePayload(...args);');
  source=source.replace(/if \(!KEY\) \$\("app"\)\.innerHTML[^\n]+refresh\(\)\.finally\(\(\)=>phonePoll\.start\(\)\);/,'');
  source+='\n;globalThis.scanTest={MONTHLY,SCAN_STORAGE,KEY,UP,SCAN_ACCENT,api,copy:t(),setInfo:value=>{INFO=value;},setShot:value=>{shot=value;},getShot:()=>shot,send,redo,paint};';
  const calls=[],history=[],nodes=new Map(),bodyClasses=[],htmlClasses=[],appended=[];
  const node = id => {if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',querySelectorAll:()=>[]});return nodes.get(id);};
  const context={URL,URLSearchParams,FormData,Blob,console,navigator:{language:'ko',mediaDevices:null},location:{hash:hash||'',search:monthly?'?monthly=1':'',pathname:'/sim/scan.html'},
    sessionStorage:{getItem:key=>storage.get(key),setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)},history:{replaceState:(_a,_b,value)=>history.push(value)},
    document:{getElementById:node,documentElement:{classList:{add:value=>htmlClasses.push(value)}},body:{classList:{add:value=>bodyClasses.push(value)},append:value=>appended.push(value)},querySelectorAll:()=>[],createElement:()=>({setAttribute(){},remove(){}})},window:{HLExamNetwork:{createTransport:()=>({request:(...args)=>{calls.push(args);return request?request(...args):Promise.resolve({});}}),createPoll:()=>({start(){},stop(){}})}},
    monthlyFixturePayload:payload||(()=>Promise.resolve(new FormData())),encodeUpload:async value=>value,reprocess:async()=>({previewUrl:'data:fixture',blob:new Blob(['new pixels'],{type:'image/jpeg'})}),
    canProcess:()=>false,setInterval(){},setTimeout(){},clearTimeout(){},};
  vm.runInNewContext(source,context);
  return {hooks:context.scanTest,storage,calls,history,nodes,bodyClasses,htmlClasses,appended};
}

test('monthly camera grants survive reloads in a separate namespace and never enter account bearer headers',async()=>{
  const storage=new Map([['hlScan','c=ipho-existing-grant&l=en']]);
  const view=scannerContext({monthly:true,hash:'#'+new URLSearchParams({c:code,l:'ko'}),storage});
  assert.equal(view.hooks.UP,'/monthly/up');assert.equal(view.hooks.SCAN_STORAGE,'hlMonthlyScan');assert.equal(view.hooks.KEY,code);
  assert.equal(storage.get('hlScan'),'c=ipho-existing-grant&l=en');assert.ok(storage.get('hlMonthlyScan').includes(code));
  assert.deepEqual(view.history,['/sim/scan.html?monthly=1'],'only public monthly metadata remains in the address');
  const reloaded=scannerContext({monthly:true,storage});assert.equal(reloaded.hooks.KEY,code);
  await reloaded.hooks.api('GET','/monthly/up');const [method,path,body,options]=reloaded.calls[0];
  assert.equal(method,'GET');assert.equal(path,'/monthly/up');assert.equal(body,undefined);
  assert.equal(options.headers['X-Lab-Token'],code);assert.equal(options.headers.Authorization,undefined);
  assert.match(reloaded.hooks.copy.help,/쪽 번호/);assert.ok(!reloaded.hooks.copy.legH.poor.includes('0점'));
  const ipho=scannerContext({monthly:false,storage});assert.equal(ipho.hooks.KEY,'ipho-existing-grant');assert.equal(ipho.hooks.UP,'/lab/up');
  assert.equal(ipho.hooks.SCAN_STORAGE,'hlScan');assert.equal(ipho.hooks.copy.task,'Experiment','existing IPhO language and labels remain unchanged');
});

test('exam and monthly camera guidance accept unmarked paper in both languages',()=>{
  for(const monthly of [false,true]) for(const language of ['ko','en']) {
    const view=scannerContext({monthly,hash:'#'+new URLSearchParams({c:monthly?code:'existing-exam-code',l:language})});
    if(language==='ko') {
      assert.match(view.hooks.copy.help,/종이의 네 모서리와 테두리/);assert.match(view.hooks.copy.help,/검은 표식이 없어도/);
      assert.match(view.hooks.copy.lvAim,/선택 사항/);
    } else {
      assert.match(view.hooks.copy.help,/four paper corners and edges/);assert.match(view.hooks.copy.help,/Black markers are optional/);
      assert.match(view.hooks.copy.lvAim,/Black markers are optional/);
    }
    assert.ok(view.hooks.copy.weak.includes(language==='en'?'Fix corners':'모서리 맞추기'),'manual corner correction remains the uncertain-detection fallback');
  }
});

test('monthly upload changes only its payload/endpoint while retaining actual IPhO capture and correction controls',()=>{
  const html=fs.readFileSync(path.join(root,'sim/scan.html'),'utf8');
  assert.match(html,/MONTHLY \? await monthlyScanPayload\(sending,encodeUpload\) : await encodeUpload\(sending.blob, \{ maxBytes: MAX_BYTES \}\)/);
  assert.match(html,/api\(MONTHLY \? "POST" : "PUT"/);
  assert.match(html,/function liveCamera\(/);assert.match(html,/function cornerEditor\(/);assert.match(html,/rotatePhoto\(keep.file\)/);
  assert.match(html,/const captureFile = internal && shot\?\.captureFile \|\| file/);
  assert.match(html,/preserveOriginal: \(keep.warpApplied \?\? keep.a4WarpApplied\) === false, pageFormat: keep.outputFormat \|\| "a4"/);
  assert.match(html,/const MAX_BYTES = 1850000/,'the existing exam upload limit remains intact');
});

test('monthly visual theme and page/kind reassignment are scoped away from the existing exam presentation',()=>{
  const monthly=scannerContext({monthly:true,hash:'#c='+code}),exam=scannerContext({monthly:false,hash:'#c=existing-exam-code'});
  assert.deepEqual(monthly.bodyClasses,['monthly-scan']);assert.deepEqual(monthly.htmlClasses,['monthly-scan']);assert.equal(monthly.hooks.SCAN_ACCENT,'#c5a3f5');
  assert.deepEqual(exam.bodyClasses,[]);assert.deepEqual(exam.htmlClasses,[]);assert.equal(exam.hooks.SCAN_ACCENT,'#f2c14e');
  const metadata={tasks:['1','2'],pages:[],open:true,status:'scanning',title_ko:'월별 문제'};
  const shot={task:'1',kind:'answer',requestId:'same-prepared-upload',previewUrl:'data:fixture'};
  monthly.hooks.setInfo(metadata);monthly.hooks.setShot(shot);monthly.hooks.paint();
  monthly.nodes.get('tasks').onclick({target:{closest:()=>({dataset:{t:'2'}})}});
  assert.equal(monthly.hooks.getShot().task,'2');assert.equal(monthly.hooks.getShot().requestId,null);
  monthly.hooks.getShot().requestId='same-pixels-new-page';monthly.nodes.get('kinds').onclick({target:{closest:()=>({dataset:{k:'working'}})}});
  assert.equal(monthly.hooks.getShot().kind,'working');assert.equal(monthly.hooks.getShot().requestId,null);
  exam.hooks.setInfo({...metadata,comp:'ipho',year:2024});exam.hooks.setShot({...shot,task:'1'});exam.hooks.paint();exam.nodes.get('tasks').onclick({target:{closest:()=>({dataset:{t:'2'}})}});
  assert.equal(exam.hooks.getShot().task,'1','exam classification retains its existing capture-time selection');
});

test('monthly retries retain their request ID and original capture while new correction pixels reset it',async()=>{
  const {monthlyScanPayload}=await import('../sim/monthly-scan.mjs');
  const capture=new Blob(['original'],{type:'image/jpeg'}),scan=new Blob(['corrected'],{type:'image/png'}),shot={file:scan,captureFile:capture,blob:scan};
  const first=await monthlyScanPayload(shot,async value=>value),retry=await monthlyScanPayload(shot,async value=>value);
  assert.equal(first.get('request_id'),retry.get('request_id'));assert.equal(await retry.get('original_image').text(),'original');
  const monthly=scannerContext({monthly:true,hash:'#c='+code});monthly.hooks.setShot({...shot,baseUrl:'data:baseline',requestId:shot.requestId});
  await monthly.hooks.redo([], 'mono');assert.equal(monthly.hooks.getShot().requestId,null);assert.equal(monthly.hooks.getShot().captureFile,capture);
  const corrected=await monthlyScanPayload(monthly.hooks.getShot(),async value=>value);assert.notEqual(corrected.get('request_id'),first.get('request_id'));
});

test('a pending monthly upload ignores double taps and page changes until its response is known',async()=>{
  let resolve;const gate=new Promise(done=>resolve=done),metadata={tasks:['1','2'],pages:[],open:true,status:'scanning',title_ko:'문제',now:100};
  const monthly=scannerContext({monthly:true,hash:'#c='+code,request:async method=>method==='POST'?gate:metadata});
  monthly.hooks.setInfo(metadata);monthly.hooks.setShot({task:'1',kind:'answer',blob:new Blob(['photo'],{type:'image/jpeg'}),previewUrl:'data:fixture'});monthly.hooks.paint();
  const sending=monthly.hooks.send();monthly.hooks.send();await new Promise(done=>setImmediate(done));
  monthly.nodes.get('tasks').onclick({target:{closest:()=>({dataset:{t:'2'}})}});assert.equal(monthly.hooks.getShot().task,'1');assert.equal(monthly.calls.filter(call=>call[0]==='POST').length,1);
  resolve({no:1,ocr_status:'done',legible:'good'});await sending;assert.equal(monthly.hooks.getShot(),null);
});
