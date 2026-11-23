/* Runs a learner's Python in Pyodide, off the page's thread. The page terminates this worker when a run
   exceeds its time limit, so an endless loop never freezes the tab. The code runs only in this browser. */
'use strict';
/* A creation's grader (create.js) is another member's code, and this worker shares the site's origin: before anything
   runs, the site's stored data here (IndexedDB, which holds exam recordings; Cache Storage) and the channel to the site's
   other tabs are taken out of reach. The accessors are deleted along the whole prototype chain, so no path leads back. */
function seal(scope){for(const k of ['indexedDB','caches','BroadcastChannel']){for(let o=scope;o;o=Object.getPrototypeOf(o)){try{delete o[k];}catch(e){}}}}
seal(self);
const PYODIDE='https://cdn.jsdelivr.net/pyodide/v0.26.4/full/';
let ready=null;
function boot(){
  if(!ready)ready=(async()=>{
    importScripts(PYODIDE+'pyodide.js');
    const py=await loadPyodide({indexURL:PYODIDE});
    return py;
  })();
  return ready;
}
self.onmessage=async event=>{
  const {id,code,grader,common}=event.data||{};
  if(typeof code!=='string'||typeof grader!=='string'||typeof common!=='string')return;
  let out='';
  try{
    self.postMessage({id,phase:'loading'});
    const py=await boot();
    py.setStdout({batched:s=>{if(out.length<20000)out+=s+'\n';}});
    py.setStderr({batched:s=>{if(out.length<20000)out+=s+'\n';}});
    try{await py.loadPackagesFromImports(code);}catch(e){/* an unknown import fails below with a clear message */}
    self.postMessage({id,phase:'running'});
    py.globals.set('__hl_code',code);py.globals.set('__hl_grader',common+'\n'+grader);
    const json=await py.runPythonAsync(`
import json as __json, traceback as __tb
__ns={"__name__":"__main__"}
try:
    exec(compile(__hl_code,"solution.py","exec"),__ns)
    __g={}
    exec(__hl_grader,__g)
    __res=__g["grade"](__ns)
except Exception as __e:
    __res={"error":"".join(__tb.format_exception_only(type(__e),__e)).strip(),"trace":__tb.format_exc(limit=-3)}
__json.dumps(__res,allow_nan=True,default=str)`);
    self.postMessage({id,phase:'done',result:JSON.parse(json.replace(/\bNaN\b|-?Infinity\b/g,'null')),stdout:out});
  }catch(error){
    self.postMessage({id,phase:'done',result:{error:String(error&&error.message||error).slice(0,4000)},stdout:out});
  }
};
