const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'sim/monthly-pressure-wave/app.mjs'),'utf8');
const html=fs.readFileSync(path.join(root,'sim/monthly-pressure-wave/index.html'),'utf8');

// Exercise the actual shell with the small DOM surface used by its terminal.
function shell({search='?embed=1&id=8&lang=ko&theme=dark&view=cmd',token='',respond}={}){
 const storage=new Map(token?[['hlCmTok',token]]:[]),session=new Map(),requests=[],listeners=new Map(),downloads=[];
 class Element{
  constructor(tag='div'){this.tagName=tag;this.children=[];this.attributes={};this.dataset={};this.hidden=false;this.disabled=false;this.focusCount=0;this.value='';this._text='';}
  set textContent(text){this._text=String(text);this.children=[];}
  get textContent(){return this._text+this.children.map(child=>child.textContent||'').join('');}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this._text='';this.children=children;}
  setAttribute(key,value){this.attributes[key]=String(value);}
  focus(){this.focusCount++;}
  click(){this.onclick?.();if(this.download)downloads.push({name:this.download,href:this.href});}
 }
 const elements=new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(match=>[match[1],new Element()]));
 for(const id of ['terminal','embeddedNotice','embeddedLogin','login','loadError'])elements.get(id).hidden=true;
 elements.get('prompt').textContent='student@haslalab:~/experiment$ ';
 const document={body:new Element('body'),documentElement:new Element('html'),getElementById:id=>elements.get(id),createElement:tag=>new Element(tag),createElementNS:(_ns,tag)=>new Element(tag),importNode:node=>node};
 const parent={},location={search,origin:'https://haslalab.org'},localStorage={getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,String(value))};
 const window={addEventListener:(type,handler)=>listeners.set(type,handler),katex:{render:(text,node)=>{node.textContent=text;}}};
 const fetch=async(url,options={})=>{
  requests.push({url,options});
  const data=respond?await respond(url,options,{storage,requests}):{revision:4,session_id:'saved-session',logs:[{command:'run 2',text:'Saved run 2'}],status:{run_count:2,cal_count:1}};
  return {ok:data?.ok!==false,status:data?.status||200,json:async()=>data,text:async()=>'<svg></svg>'};
 };
 const context={document,window,parent,location,localStorage,sessionStorage:{getItem:key=>session.get(key)||null,setItem:(key,value)=>session.set(key,String(value))},matchMedia:()=>({matches:false}),URLSearchParams,URL:{createObjectURL:()=> 'blob:test',revokeObjectURL:()=>{}},Blob,AbortSignal,crypto:require('node:crypto').webcrypto,fetch,setTimeout:()=>0,console,DOMParser:class{parseFromString(){return{documentElement:new Element('svg')};}}};
 const ready=vm.runInNewContext('(async()=>{'+source+'\nreturn {accept,mode,get inside(){return inside;}};})()',context,{filename:'monthly-pressure-wave/app.mjs'});
 return {ready,elements,document,storage,session,requests,downloads,emit:(type,event)=>listeners.get(type)?.(event),parent,location};
}

test('embedded guests see sign-in without requests, redirects or changing the return route until clicked',async()=>{
 const s=shell();await s.ready;
 assert.equal(s.requests.length,0,'a guest must not fetch problem assets or create an apparatus session');
 assert.equal(s.document.body.dataset.embedded,'true');
 assert.equal(s.elements.get('problem').hidden,true);assert.equal(s.elements.get('terminal').hidden,false);
 assert.equal(s.elements.get('embeddedNotice').hidden,false);assert.equal(s.elements.get('embeddedLogin').hidden,false);
 assert.equal(s.elements.get('embeddedLogin').href,'../../?lang=ko#/login');
 assert.match(html,/<a id="embeddedLogin"[^>]*target="_top"/);
 assert.equal(s.elements.get('command').disabled,true);assert.equal(s.elements.get('command').focusCount,0);
 assert.equal(s.session.has('hlCmBack'),false);
 s.elements.get('embeddedLogin').click();
 assert.equal(s.session.get('hlCmBack'),'#/monthly/p/8');
});

test('opening the embedded apparatus restores saved records once and never starts a measurement',async()=>{
 const s=shell({token:'owner-token',respond:(_url,options)=>options.method==='GET'?{revision:4,session_id:'saved-session',logs:[{command:'run 2',text:'Saved run 2'}],status:{run_count:2,cal_count:1}}:{revision:5,session_id:'saved-session',result:{ok:true,text:'Command accepted'}}});
 const app=await s.ready;
 assert.equal(s.requests.length,1);
 assert.equal(s.requests[0].url,'https://haslalab-community-edge.haslalab.workers.dev/api/problems/8/experiment');
 assert.equal(s.requests[0].options.method,'GET');assert.equal(s.requests[0].options.headers.Authorization,'Bearer owner-token');
 assert.equal(s.requests[0].options.body,undefined);assert.equal(app.inside,true);
 assert.match(s.elements.get('screen').textContent,/Saved run 2/);assert.match(s.elements.get('status').textContent,/RUN 2.*CAL 1/);
 assert.equal(s.elements.get('embeddedNotice').hidden,true);assert.equal(s.elements.get('command').disabled,false);
 assert.equal(s.elements.get('command').focusCount,0,'restoring a frame must not steal focus from the problem');
 await app.accept('status');
 assert.equal(s.requests.length,2);assert.equal(s.requests[1].options.method,'POST');
 assert.deepEqual(JSON.parse(s.requests[1].options.body),{command:'status',revision:4,request_id:JSON.parse(s.requests[1].options.body).request_id});
 assert.match(s.elements.get('screen').textContent,/Command accepted/);
});

test('an embedded shell requires the supplied positive database ID instead of discovering or guessing a problem',async()=>{
 for(const id of ['',0,-1,'wrong',Number.MAX_SAFE_INTEGER+1]){
  const s=shell({search:'?embed=1&id='+id,token:'owner-token'});await s.ready;
  assert.equal(s.requests.length,0);assert.equal(s.elements.get('command').disabled,true);
  assert.equal(s.elements.get('embeddedNotice').hidden,false);assert.equal(s.elements.get('embeddedLogin').hidden,true);
 }
});

test('the embedded terminal keeps server-backed CSV export and downloads without opening a new page',async()=>{
 const s=shell({token:'owner-token',respond:(_url,options)=>options.method==='GET'?{revision:4,session_id:'saved-session',logs:[]}:{revision:5,session_id:'saved-session',result:{ok:true,text:'Export ready',csv:'t_ms,r_kPa\n0,12\n',filename:'trace.csv'}}});
 const app=await s.ready;await app.accept('export');
 assert.equal(s.requests.length,2);assert.equal(JSON.parse(s.requests[1].options.body).command,'export');
 assert.deepEqual(s.downloads,[{name:'trace.csv',href:'blob:test'}]);
});

test('only the same-origin parent can update the embedded theme, with no reload or new requests',async()=>{
 const s=shell();await s.ready;
 const message={type:'haslalab-experiment-theme',theme:'light'};
 s.emit('message',{source:s.parent,origin:'https://other.example',data:message});
 assert.equal(s.document.body.dataset.theme,'dark');
 s.emit('message',{source:{},origin:s.location.origin,data:message});
 assert.equal(s.document.body.dataset.theme,'dark');
 s.emit('message',{source:s.parent,origin:s.location.origin,data:{...message,theme:'invalid'}});
 assert.equal(s.document.body.dataset.theme,'dark');
 s.emit('message',{source:s.parent,origin:s.location.origin,data:message});
 assert.equal(s.document.body.dataset.theme,'light');assert.equal(s.requests.length,0);
});

test('account changes disable commands and an in-flight response cannot display another account’s saved records',async()=>{
 const s=shell({token:'original'}),app=await s.ready;
 s.storage.set('hlCmTok','new-owner');s.emit('storage',{key:'hlCmTok'});
 assert.equal(s.elements.get('command').disabled,true);assert.equal(s.elements.get('downloadAllCsv').disabled,true);
 await app.accept('run 4');assert.equal(s.requests.length,1);
 assert.match(s.elements.get('embeddedMessage').textContent,/로그인 정보가 바뀌/);
 const switched=shell({token:'original',respond:(_url,_options,{storage})=>{
  storage.set('hlCmTok','new-owner');
  return{revision:9,session_id:'private',logs:[{command:'run 9',text:'old-owner-private-data'}]};
 }});
 await switched.ready;
 assert.doesNotMatch(switched.elements.get('screen').textContent,/old-owner-private-data/);
 assert.equal(switched.elements.get('command').disabled,true);
});

test('the standalone viewer still loads its full problem and waits for an explicit apparatus launch',async()=>{
 const s=shell({search:'?id=8&lang=ko&view=cmd',token:'owner-token',respond:url=>url==='./problem.json'?{intro:'Problem introduction',figure_caption:'Apparatus',model:[],commands:[],sections:[],parts:[]}:null});
 const app=await s.ready;
 assert.deepEqual(s.requests.map(request=>request.url),['./problem.json','../../weekly/figures/pressure-wave-apparatus.svg']);
 assert.equal(s.document.body.dataset.embedded,undefined);assert.equal(app.inside,false);
 assert.match(s.elements.get('statement').textContent,/Problem introduction/);assert.equal(s.elements.get('loadError').hidden,true);
 assert.equal(s.elements.get('terminal').hidden,false);
});
