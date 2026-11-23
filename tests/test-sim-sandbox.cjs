/* sim-sandbox.html runs a member's simulation code only inside the opaque-origin frame create.js opens
   (sandbox="allow-scripts", no allow-same-origin). Framed by another site without the sandbox, the page would be
   haslalab.org itself, so it must not run code it is sent. */
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'..','sim-sandbox.html'),'utf8');
const script=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].pop()[1];

function frame(origin){
  const listeners={},el=()=>({append(){},getBoundingClientRect:()=>({width:300,height:200}),getContext:()=>({setTransform(){}}),style:{},textContent:'',innerHTML:''});
  const parent={posted:[],postMessage(m){this.posted.push(m);}};
  const ctx={self:{origin},parent,devicePixelRatio:1,ran:false,
    document:{getElementById:el,createElement:el,documentElement:{dataset:{},scrollHeight:400}},
    addEventListener:(type,fn)=>{listeners[type]=fn;},requestAnimationFrame(){}};
  vm.createContext(ctx);
  vm.runInContext(script,ctx);
  return {ctx,parent,send:data=>listeners.message({source:parent,data})};
}

test('the simulation code runs in the opaque-origin sandbox frame', () => {
  const f=frame('null');
  f.send({type:'run',code:'globalThis.ran=true;'});
  assert.equal(f.ctx.ran,true);
});

test('framed as haslalab.org (no sandbox) the page refuses to run code it is sent', () => {
  const f=frame('https://haslalab.org');
  f.send({type:'run',code:'globalThis.ran=true;'});
  assert.equal(f.ctx.ran,false);
});

test('create.js opens the frame with scripts only, never same-origin', () => {
  const js=fs.readFileSync(path.join(__dirname,'..','create.js'),'utf8');
  assert.match(js,/<iframe class="sim" sandbox="allow-scripts" src="sim-sandbox.html"/);
  assert.doesNotMatch(js,/allow-same-origin/);
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
