/* Small request/polling primitives shared by the exam clients. No account data is persisted here. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.HLExamNetwork=api;})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  function createTransport({fetch:perform,getBase,getToken}={}){
    const pending=new Map();let generation=0;
    const fingerprint=()=>String(getBase?.()||'').replace(/\/+$/,'')+'\n'+String(getToken?.()||'');
    function request(method,path,body,extra={}){
      const identity=fingerprint(),base=identity.slice(0,identity.indexOf('\n')),token=identity.slice(identity.indexOf('\n')+1),key=identity+'\n'+generation+'\n'+path;
      if(method==='GET'&&pending.has(key))return pending.get(key);
      if(method!=='GET'){generation++;pending.clear();}
      const promise=(async()=>{
        const headers={...extra.headers};
        if(token&&!(method==='GET'&&/^\/health(?:\?|$)/.test(path)))headers.Authorization='Bearer '+token;
        if(body!==undefined&&!extra.binary)headers['Content-Type']='application/json';
        let r;try{r=await(perform||fetch)(base+'/api'+path,{method,headers,body:body===undefined?undefined:extra.binary?body:JSON.stringify(body)});}catch(_){throw{code:'network'};}
        const value=await r.json().catch(()=>({}));
        if(fingerprint()!==identity)throw{code:'account_changed'};
        if(!r.ok)throw{...value,code:value.error||'server_error',status:r.status};
        return value;
      })();
      if(method==='GET'){pending.set(key,promise);promise.finally(()=>{if(pending.get(key)===promise)pending.delete(key);}).catch(()=>{});}
      return promise;
    }
    return{request,fingerprint,clear(){generation++;pending.clear();}};
  }
  function createPoll({task,active=()=>true,delays=[5000,10000,20000,30000],document:doc=typeof document==='object'?document:null,setTimeout:schedule=setTimeout,clearTimeout:cancel=clearTimeout}={}){
    let enabled=false,disposed=false,timer=null,running=false,step=0,generation=0,wakePending=false;
    const visible=()=>!doc?.hidden;
    function clear(){if(timer!==null)cancel(timer);timer=null;}
    function later(){clear();if(enabled&&!disposed&&visible()&&active())timer=schedule(tick,delays[Math.min(step,delays.length-1)]);}
    async function tick(){
      timer=null;if(!enabled||disposed||!visible()||!active())return;
      if(running){wakePending=true;return;}
      running=true;const started=generation;let changed=false;
      try{changed=await task()===true;}catch(_){}
      finally{
        running=false;if(disposed||!enabled)return;
        if(wakePending){wakePending=false;step=0;later();return;}
        if(started===generation)step=changed?0:Math.min(step+1,delays.length-1);
        later();
      }
    }
    function start(){if(disposed)return;enabled=true;later();}
    function stop(){enabled=false;generation++;clear();}
    function wake(){if(disposed)return;enabled=true;generation++;step=0;clear();if(running){wakePending=true;return;}if(visible()&&active())void tick();}
    function visibility(){clear();if(enabled&&visible())wake();}
    doc?.addEventListener?.('visibilitychange',visibility);
    return{start,stop,wake,reset(){step=0;},dispose(){stop();disposed=true;doc?.removeEventListener?.('visibilitychange',visibility);},getDelay:()=>delays[Math.min(step,delays.length-1)],isRunning:()=>running};
  }
  function sessionSignature(s){return JSON.stringify(s?[s.id,s.status,s.paid,s.score,s.points,s.graded_at,s.detail,(s.pages||[]).map(p=>[p.id,p.task,p.kind,p.ocr_status,p.legible,p.edited,p.text])]:null);}
  const reading=p=>p?.source!=='typed'&&['queued','reading'].includes(p?.ocr_status);
  return{createTransport,createPoll,sessionSignature,reading};
});
