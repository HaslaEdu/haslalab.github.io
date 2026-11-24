/* sim-sandbox.html runs a member's simulation code only inside the opaque-origin frame create.js opens
   (sandbox="allow-scripts", no allow-same-origin). Framed by another site without the sandbox, the page would be
   haslalab.org itself, so it must not run code it is sent. A runaway loop is stopped, errors carry the member's line,
   and the console reaches the page as text. */
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'..','sim-sandbox.html'),'utf8');
const scripts=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(m=>m[1]);

function frame(origin){
  const listeners={};let ctx;
  const noop=()=>{};
  const g2d=new Proxy({},{get:(o,k)=>k in o?o[k]:k==='measureText'?()=>({width:10}):noop,set:(o,k,v)=>{o[k]=v;return true;}});
  const el=tag=>{const e={tag,children:[],style:{},dataset:{},textContent:'',innerHTML:'',classList:{add(){},toggle(){},remove(){}},
    append(...c){this.children.push(...c);for(const x of c)if(x&&x.tag==='script')vm.runInContext(x.textContent,ctx);},
    get lastChild(){return this.children[this.children.length-1]||el('b');},
    getBoundingClientRect:()=>({width:300,height:200,left:0,top:0}),getContext:()=>g2d,addEventListener(){},focus(){},setPointerCapture(){}};return e;};
  const parent={posted:[],postMessage(m){this.posted.push(m);}};
  const head=el('head');
  ctx={self:{origin},parent,devicePixelRatio:1,ran:false,performance,console:{},setInterval:noop,
    document:{getElementById:el,createElement:el,head,body:el('body'),documentElement:{dataset:{},scrollHeight:400}},
    addEventListener:(type,fn)=>{listeners[type]=fn;},requestAnimationFrame(){}};
  ctx.globalThis=ctx;
  vm.createContext(ctx);
  for(const s of scripts)vm.runInContext(s,ctx);
  return {ctx,parent,listeners,send:data=>listeners.message({source:parent,data}),
    error(e){listeners.error({error:e,message:e.message,filename:'',lineno:0,preventDefault(){}});}};
}

test('the simulation code runs in the opaque-origin sandbox frame', () => {
  const f=frame('null');
  f.send({type:'run',code:'globalThis.ran=true;'});
  assert.equal(f.ctx.ran,true);
  assert.equal(f.parent.posted[0].type,'sim-ready');
});

test('framed as haslalab.org (no sandbox) the page refuses to run code it is sent', () => {
  const f=frame('https://haslalab.org');
  f.send({type:'run',code:'globalThis.ran=true;'});
  assert.equal(f.ctx.ran,false);
});

test('only the parent can start it, and only once', () => {
  const f=frame('null');
  f.listeners.message({source:{},data:{type:'run',code:'globalThis.ran=true;'}});
  assert.equal(f.ctx.ran,false,'a message from another window is ignored');
  f.send({type:'run',code:'globalThis.n=(globalThis.n||0)+1;'});f.send({type:'run',code:'globalThis.n=(globalThis.n||0)+1;'});
  assert.equal(f.ctx.n,1);
});

test('the policy: no network, no eval, no frames or workers', () => {
  const csp=/http-equiv="Content-Security-Policy" content="([^"]+)"/.exec(html)[1];
  assert.match(csp,/default-src 'none'/);assert.match(csp,/connect-src 'none'/);assert.match(csp,/form-action 'none'/);
  assert.doesNotMatch(csp,/unsafe-eval/);assert.doesNotMatch(csp,/'self'|https?:/);
});

test('the old helpers and hl are both there; the sandbox\'s own variables are not', () => {
  const f=frame('null');
  f.send({type:'run',code:`globalThis.seen=[typeof loop,typeof slider,typeof circle,typeof hl.run,typeof hl.rk4,typeof hl.slider,typeof stage,typeof frames,typeof fail].join(',');
    const m=hl.slider('m',0.1,10,2);globalThis.m=m();`});
  assert.equal(f.ctx.seen,'function,function,function,function,function,function,undefined,undefined,undefined');
  assert.equal(f.ctx.m,2);
});

test('a loop that never ends is stopped and reported', () => {
  for(const code of ['let i=0;\nwhile(true){i++;}','for(;;){}','do{}while(1)','for(let i=0;i>=0;i++){}']){
    const f=frame('null');
    const t=Date.now();
    try{f.send({type:'run',code});}catch(e){f.error(e);}
    assert.ok(Date.now()-t<6000);
    const e=f.parent.posted.find(m=>m.type==='sim-error');
    assert.ok(e,'reported: '+code);assert.match(e.message,/loop ran for more than/);
  }
});

test('loops in strings, comments and regular expressions are left alone; real ones still work', () => {
  const f=frame('null');
  f.send({type:'run',code:`const s="while(true){}"; // for(;;){}
/* while(1) */ const r=/for\\(;;\\)/; let n=0; for(let i=0;i<5;i++){n+=i;} let k=0; while(k<3)k++;
globalThis.out=[s.length,r.source,n,k,\`\${'for(;;)'}\`].join('|');`});
  assert.equal(f.ctx.out,'13|for\\(;;\\)|10|3|for(;;)');
});

test('an error reports the line in the member\'s code', () => {
  const f=frame('null');
  try{f.send({type:'run',code:'const a=1;\nconst b=2;\nnotDefined();'});}catch(e){f.error(e);}
  const e=f.parent.posted.find(m=>m.type==='sim-error');
  assert.match(e.message,/ReferenceError/);assert.equal(e.line,3);
});

test('console output reaches the page as text', () => {
  const f=frame('null');
  f.send({type:'run',code:'console.log("v =", 1/3, {a:[1,2]});'});
  const l=f.parent.posted.find(m=>m.type==='sim-log');
  assert.deepEqual({level:l.level,text:l.text},{level:'log',text:'v = 0.333333 {"a":[1,2]}'});
});

test('create.js opens the frame with scripts only, never same-origin', () => {
  for(const file of ['create.js','create-studio.js']){
    const js=fs.readFileSync(path.join(__dirname,'..',file),'utf8');
    assert.doesNotMatch(js,/allow-same-origin/,file);
  }
  const js=fs.readFileSync(path.join(__dirname,'..','create-studio.js'),'utf8');
  assert.match(js,/<iframe class="sim" sandbox="allow-scripts" src="sim-sandbox.html"/);
});

test('the Python worker takes the site\'s stored data out of reach before any member code runs', () => {
  const src=fs.readFileSync(path.join(__dirname,'..','compute-worker.js'),'utf8');
  /* a worker-like global: the storage accessors live on its prototypes, as in a browser's WorkerGlobalScope */
  class Scope{}Object.defineProperty(Scope.prototype,'indexedDB',{get:()=>({open(){}}),configurable:true});
  Object.defineProperty(Scope.prototype,'caches',{get:()=>({}),configurable:true});
  const self=new Scope();self.BroadcastChannel=function(){};
  let imported=false;
  const ctx={self,importScripts(){imported=true;}};
  vm.createContext(ctx);vm.runInContext(src,ctx);
  for(const k of ['indexedDB','caches','BroadcastChannel'])assert.equal(self[k],undefined,k);
  assert.equal(typeof self.onmessage,'function');assert.equal(imported,false,'Pyodide loads only when asked to run');
});
