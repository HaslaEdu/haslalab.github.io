/* Small request/polling primitives shared by the exam clients. No account data is persisted here. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.HLExamNetwork=api;})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  // Fixed, safe categories only. Provider response bodies and arbitrary server
  // messages never become page markup or advice to retake an otherwise valid photo.
  const OCR_ERRORS={
    vision_provider_auth:['판독 제공자의 인증 설정에 문제가 있습니다. 운영자에게 문의해 주세요.','The reading provider rejected its authentication settings. Contact the site operator.'],
    vision_provider_credits:['판독 제공자의 API 잔액이 부족합니다. 운영자에게 문의해 주세요.','The reading provider has insufficient API credit. Contact the site operator.'],
    vision_provider_rate_limited:['판독 제공자의 요청 한도에 걸렸습니다. 잠시 후 다시 읽기를 요청해 주세요.','The reading provider reached its request limit. Request reading again later.'],
    vision_model_unavailable:['선택한 판독 모델을 사용할 수 없습니다. 운영자에게 문의해 주세요.','The selected reading model is unavailable. Contact the site operator.'],
    vision_request_rejected:['판독 제공자가 이미지 요청을 거절했습니다. 운영자가 파일 형식·크기와 연결 설정을 확인해야 합니다.','The reading provider rejected the image request. The operator must check file format, size and connection settings.'],
    vision_provider_failed:['판독 제공자의 서버 오류로 처리하지 못했습니다. 잠시 후 다시 읽기를 요청해 주세요.','The reading provider returned a server error. Request reading again later.'],
    vision_provider_timeout:['판독 응답 시간이 초과됐습니다. 잠시 후 다시 읽기를 요청해 주세요.','The reading request timed out. Request reading again later.'],
    vision_response_empty:['판독 모델의 응답이 비어 있어 처리하지 못했습니다. 다시 읽기를 요청하거나 운영자에게 알려 주세요.','The reading model returned an empty response. Request reading again or contact the operator.'],
    vision_response_truncated:['판독 모델의 응답이 중간에 끊겼습니다. 운영자에게 문의해 주세요.','The reading model response was cut off. Contact the site operator.'],
    vision_response_blocked:['판독 모델이 응답을 제한했습니다. 운영자에게 문의해 주세요.','The reading model restricted its response. Contact the site operator.'],
    vision_invalid_response:['판독 모델의 응답 형식을 해석하지 못했습니다. 운영자에게 문의해 주세요.','The reading model response could not be decoded. Contact the site operator.'],
    vision_response_schema:['판독 응답의 필수 항목을 확인하지 못했습니다. 운영자에게 문의해 주세요.','Required fields were missing or invalid in the reading response. Contact the operator.'],
    ocr_bad_response:['판독 응답의 필수 항목을 확인하지 못했습니다. 운영자에게 문의해 주세요.','Required fields were missing or invalid in the reading response. Contact the operator.'],
    ocr_storage_limit:['사진과 읽은 원문의 합계 용량이 큽니다. 파일 용량을 줄여 다시 올려 주세요.','The photo and full recognized text exceed the storage limit. Reduce the file size and upload again.'],
  };
  function ocrErrorMessage(code,lang='ko'){return typeof code==='string'&&Object.hasOwn(OCR_ERRORS,code)?OCR_ERRORS[code][lang==='en'?1:0]:'';}
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
  function sessionSignature(s){return JSON.stringify(s?[s.id,s.status,s.paid,s.cost,s.price_estimate,s.paired_with,s.discount,s.pair_mixed_mode,s.score,s.points,s.graded_at,s.detail,(s.pages||[]).map(p=>[p.id,p.task,p.kind,p.ocr_status,p.ocr_error,p.read?.ocr?.error,p.legible,p.edited,p.text])]:null);}
  const reading=p=>p?.source!=='typed'&&['queued','reading'].includes(p?.ocr_status);
  return{createTransport,createPoll,sessionSignature,reading,ocrErrorMessage};
});
