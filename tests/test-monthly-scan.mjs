// Phone fixtures only: no camera device, provider, account or production API.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {parseMonthlyScanLink,createMonthlyScanClient,monthlyScanHistory} from '../sim/monthly-scan.js';

const token='x'.repeat(43),base='https://haslalab-community-edge.haslalab.workers.dev';
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const metadata=()=>({session:{id:'local-fixture',problem_id:1,part_id:'a',created_at:1000,expires_at:2200,open:true},problem:{id:1,title:'월별 문제',title_en:'Monthly problem'},parts:[{id:'a',label:'첫 항목',label_en:'First part'},{id:'b',label:'둘째 항목',label_en:'Second part'}],now:1000,limits:{max_image_bytes:4194304,max_photos:40}});

test('scan capability is accepted only from the fragment and never redirected to an arbitrary API',()=>{
  assert.equal(parseMonthlyScanLink({hash:'#token='+token,search:'?lang=en'}).lang,'en');
  assert.equal(parseMonthlyScanLink({hash:'#token='+token,search:''}).token,token);
  assert.equal(parseMonthlyScanLink({hash:'',search:'?token='+token}).token,'');
  assert.equal(parseMonthlyScanLink({hash:'#token=short'}).token,'');
  for(const target of ['https://attacker.example','https://haslalab-community-edge.haslalab.workers.dev.evil.example','https://name:password@haslalab-community-edge.haslalab.workers.dev','https://haslalab-community-edge.haslalab.workers.dev/private','http://haslalab-community-edge.haslalab.workers.dev']){
    assert.equal(parseMonthlyScanLink({hash:'#token='+token+'&a='+encodeURIComponent(target)}).token,'');
  }
  const local=parseMonthlyScanLink({hash:'#token='+token+'&a='+encodeURIComponent('http://127.0.0.1:8787')});
  assert.equal(local.api,'http://127.0.0.1:8787');assert.equal(local.token,token);
});

test('phone requests send the upload header and both image variants without login credentials or a token URL/body',async()=>{
  const calls=[],client=createMonthlyScanClient({api:base,token,fetch:async(url,options)=>{calls.push({url,options});return Response.json({ok:true});}});
  await client.info();await client.upload({part:'b',requestId:'fixture-upload-0001',image:new Blob(['corrected'],{type:'image/jpeg'}),original:new Blob(['original'],{type:'image/png'})});
  assert.deepEqual(calls.map(call=>call.url),[base+'/api/monthly/scan',base+'/api/monthly/scan/photos?mode=math']);
  for(const {url,options}of calls){assert.equal(url.includes(token),false);assert.equal(options.headers['X-Monthly-Scan'],token);assert.equal('Authorization'in options.headers,false);assert.equal(options.credentials,'omit');assert.equal(options.cache,'no-store');assert.equal(options.referrerPolicy,'no-referrer');}
  const form=calls[1].options.body;assert.equal(form.get('part_id'),'b');assert.equal(form.get('request_id'),'fixture-upload-0001');assert.equal(await form.get('image').text(),'corrected');assert.equal(await form.get('original_image').text(),'original');assert.equal(form.has('token'),false);assert.equal('Content-Type'in calls[1].options.headers,false,'the browser supplies the multipart boundary');
});

test('transport errors expose controlled codes and history renders only this tab’s escaped upload results',async()=>{
  const offline=createMonthlyScanClient({api:base,token,fetch:async()=>{throw Error('private transport details');}});
  await assert.rejects(offline.info(),error=>error.code==='network'&&!JSON.stringify(error).includes(token));
  const expired=createMonthlyScanClient({api:base,token,fetch:async()=>Response.json({error:'scan_expired'},{status:410})});
  await assert.rejects(expired.info(),error=>error.status===410&&error.code==='scan_expired');
  const html=monthlyScanHistory([{part_id:'<script>',text:'<img onerror=alert(1)>'}],'en');assert.match(html,/Photos sent from this phone/);assert.match(html,/&lt;script&gt;/);assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<script>|<img/);
});

function phone({fetch:perform,canProcess=false,mediaDevices}={}){
  const nodes=new Map(),listeners={},docListeners={},timers=new Map(),appended=[],revoked=[],calls=[];let now=1000000,nextTimer=0,requestSerial=0;
  class Node{
    constructor(id=''){this.id=id;this.dataset={};this.style={};this.classList={toggle(){},add(){},remove(){}};this.value='';this._html='';this.disabled=false;this.listeners={};}
    set innerHTML(value){this._html=value;for(const match of value.matchAll(/\bid="([^"]+)"/g))nodes.set(match[1],new Node(match[1]));}
    get innerHTML(){return this._html;}
    querySelectorAll(){return[];}querySelector(){return new Node();}setAttribute(){}addEventListener(type,fn){this.listeners[type]=fn;}remove(){this.removed=true;}click(){this.onclick?.();}focus(){}
  }
  nodes.set('app',new Node('app'));nodes.set('language',new Node('language'));
  const document={hidden:false,documentElement:{lang:''},body:{append(node){appended.push(node);}},getElementById:id=>nodes.get(id)||null,querySelectorAll:()=>[],querySelector:()=>null,createElement:()=>new Node(),addEventListener:(type,fn)=>docListeners[type]=fn};
  const location={pathname:'/sim/monthly-scan.html',search:'?lang=en',hash:'#token='+token},history={replaceState(_a,_b,path){this.path=path;location.hash='';location.search='';}};
  const clock=class extends Date{static now(){return now;}};
  const fakeURL=class extends URL{static createObjectURL(){return'blob:local-photo';}static revokeObjectURL(value){revoked.push(value);}};
  const context={document,location,history,navigator:{language:'en',mediaDevices},URL:fakeURL,URLSearchParams,FormData,Blob,Response,Date:clock,Set,console,devicePixelRatio:1,crypto:{randomUUID:()=> 'fixture-request-'+String(++requestSerial).padStart(4,'0')},
    fetch:async(url,options)=>{calls.push({url,options});return perform?perform(url,options):Response.json(metadata());},
    canProcess:()=>canProcess,processShot:async()=>{throw Error('fixture no canvas');},encodeUpload:async blob=>blob,reprocess:async()=>({}),rotatePhoto:async blob=>blob,orderCorners:points=>points,quadScore:()=>1,MARKER_INSET:{},inspectDocumentPixels:()=>({focus:50}),toGray(){},findSheetMarkersGray(){},findPageQuadGray(){},
    setTimeout(fn){const id=++nextTimer;timers.set(id,fn);return id;},clearTimeout:id=>timers.delete(id),setInterval(fn){const id=++nextTimer;timers.set(id,fn);return id;},clearInterval:id=>timers.delete(id),addEventListener:(type,fn)=>listeners[type]=fn,removeEventListener(){},
    localStorage:{getItem(){return null;},setItem(){throw Error('capability must not be stored');}},sessionStorage:{getItem(){throw Error('must not read account storage');},setItem(){throw Error('capability must not be stored');}},
  };
  const source=readFileSync(new URL('../sim/monthly-scan.js',import.meta.url),'utf8').replace(/^import .*;\r?\n/m,'').replace(/\bexport /g,'').replace(/if\(typeof document!==.*mountMonthlyScan\(\);\s*$/,'');
  vm.createContext(context);vm.runInContext(source,context);vm.runInContext('mountMonthlyScan()',context);
  return{nodes,document,history,location,listeners,docListeners,timers,appended,calls,revoked,setNow:value=>now=value};
}

test('phone selects canonical parts, checks photos before upload and sends once while a request is pending',async()=>{
  let finishUpload;const h=phone({fetch:async(url)=>url.includes('/photos')?new Promise(resolve=>finishUpload=resolve):Response.json(metadata())});await tick();
  assert.equal(h.history.path,'/sim/monthly-scan.html');assert.equal(h.location.hash,'');assert.match(h.nodes.get('app').innerHTML,/Second part/);
  const parts=h.nodes.get('parts');parts.value='b';parts.onchange();
  h.nodes.get('gal').onchange({target:{files:[new Blob(['fixture image'],{type:'image/jpeg'})],value:'file'}});await tick();
  assert.match(h.nodes.get('shot').innerHTML,/b · Second part/);assert.match(h.nodes.get('shot').innerHTML,/View original/);assert.equal(h.calls.length,1,'selecting a photo never uploads it');
  h.nodes.get('compare').onclick();assert.match(h.nodes.get('shot').innerHTML,/View corrected/);
  const send=h.nodes.get('send').onclick,one=send();send();await tick();
  assert.equal(h.calls.filter(call=>call.options.method==='POST').length,1);assert.equal(h.calls.at(-1).options.body.get('part_id'),'b');
  finishUpload(Response.json({photo_id:'local-photo-id',part_id:'b',text:'Recognized fixture working'}));await one;await tick();
  assert.match(h.nodes.get('app').innerHTML,/Recognized fixture working/);assert.match(h.nodes.get('app').innerHTML,/Photo 1/);assert.ok(h.revoked.includes('blob:local-photo'));
});

test('closed or locally expired links disable uploads and ask for a new computer QR',async()=>{
  const h=phone({fetch:async()=>Response.json({error:'scan_revoked'},{status:410})});await tick();assert.match(h.nodes.get('app').innerHTML,/expired or closed/);assert.equal(h.calls.length,1);
  const active=phone();await tick();active.setNow(2300000);for(const callback of [...active.timers.values()])callback();await tick();assert.match(active.nodes.get('app').innerHTML,/expired or closed/);assert.doesNotMatch(active.nodes.get('app').innerHTML,/id="parts"/);
});

test('network and processing retries keep one upload ID; changing the selected part creates a new ID',async()=>{
  let uploads=0;const h=phone({fetch:async(url)=>{
    if(!url.includes('/photos'))return Response.json(metadata());
    if(++uploads===1)throw Error('local simulated lost response');
    if(uploads===2)return Response.json({error:'upload_processing'},{status:409});
    return Response.json({photo_id:'retry-fixture',part_id:'b',text:'Recognized once'});
  }});await tick();
  h.nodes.get('gal').onchange({target:{files:[new Blob(['fixture image'],{type:'image/jpeg'})],value:'file'}});await tick();
  await h.nodes.get('send').onclick();await h.nodes.get('send').onclick();
  const firstTwo=h.calls.filter(call=>call.options.method==='POST');assert.equal(firstTwo.length,2);assert.equal(firstTwo[0].options.body.get('request_id'),firstTwo[1].options.body.get('request_id'));
  h.nodes.get('parts').value='b';h.nodes.get('parts').onchange();await h.nodes.get('send').onclick();
  const final=h.calls.filter(call=>call.options.method==='POST').at(-1);assert.notEqual(final.options.body.get('request_id'),firstTwo[0].options.body.get('request_id'));assert.equal(final.options.body.get('part_id'),'b');assert.match(h.nodes.get('app').innerHTML,/Recognized once/);
});

test('a camera permission response arriving after the page is hidden releases its stream',async()=>{
  let allow,stops=0;const h=phone({canProcess:true,mediaDevices:{getUserMedia:()=>new Promise(resolve=>allow=resolve)}});await tick();
  h.nodes.get('live').onclick();h.document.hidden=true;h.docListeners.visibilitychange();allow({getTracks:()=>[{stop(){stops++;}}]});await tick();assert.equal(stops,1);assert.equal(h.appended.length,0);
});
