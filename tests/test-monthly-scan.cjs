const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname,'..');
const code = 'monthly-scan-grant-0123456789abcdef';

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
  const same=[];await monthlyScanPayload({blob:capture,file:capture,captureFile:capture},async(blob)=>{same.push(blob);return blob;});
  assert.equal(same.length,1,'an already-small original does not need a second encoding');
});

function scannerContext({monthly,hash,storage=new Map()}) {
  let source=fs.readFileSync(path.join(root,'sim/scan.html'),'utf8').match(/<script type="module">([\s\S]*?)<\/script>/)[1];
  source=source.replace(/^import[^\n]+\n/m,'');
  source=source.replace(/if \(!KEY\) \$\("app"\)\.innerHTML[^\n]+refresh\(\)\.finally\(\(\)=>phonePoll\.start\(\)\);/,'');
  source+='\n;globalThis.scanTest={MONTHLY,SCAN_STORAGE,KEY,UP,api,copy:t(),setInfo:value=>{INFO=value;},paint};';
  const calls=[],history=[],nodes=new Map();
  const node = id => {if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',querySelectorAll:()=>[]});return nodes.get(id);};
  const context={URLSearchParams,FormData,Blob,console,navigator:{language:'ko',mediaDevices:null},location:{hash:hash||'',search:monthly?'?monthly=1':'',pathname:'/sim/scan.html'},
    sessionStorage:{getItem:key=>storage.get(key),setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)},history:{replaceState:(_a,_b,value)=>history.push(value)},
    document:{getElementById:node,documentElement:{},querySelectorAll:()=>[]},window:{HLExamNetwork:{createTransport:()=>({request:(...args)=>{calls.push(args);return Promise.resolve({});}}),createPoll:()=>({start(){},stop(){}})}},
    canProcess:()=>false,setInterval(){},setTimeout(){},clearTimeout(){},};
  vm.runInNewContext(source,context);
  return {hooks:context.scanTest,storage,calls,history,nodes};
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

test('monthly upload changes only its payload/endpoint while retaining actual IPhO capture and correction controls',()=>{
  const html=fs.readFileSync(path.join(root,'sim/scan.html'),'utf8');
  assert.match(html,/MONTHLY \? await monthlyScanPayload\(sending,encodeUpload\) : await encodeUpload\(sending.blob, \{ maxBytes: MAX_BYTES \}\)/);
  assert.match(html,/api\(MONTHLY \? "POST" : "PUT"/);
  assert.match(html,/function liveCamera\(/);assert.match(html,/function cornerEditor\(/);assert.match(html,/rotatePhoto\(keep.file\)/);
  assert.match(html,/const captureFile = internal && shot\?\.captureFile \|\| file/);
  assert.match(html,/reprocess\(keep.baseUrl, corners, m, undefined, keep.method === "marker" \? MARKER_INSET : null\)/);
  assert.match(html,/const MAX_BYTES = 1850000/,'the existing exam upload limit remains intact');
});
