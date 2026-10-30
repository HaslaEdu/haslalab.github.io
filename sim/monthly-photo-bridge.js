/* Desktop side of a short-lived, account-owned monthly photo connection.
 * The upload capability stays in the QR fragment; it is never an account token. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.HLMonthlyPhotoBridge=api;})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const uuid=value=>typeof value==='string'&&/^[a-f0-9-]{36}$/.test(value);
  function text(language){return language==='en'?{
    title:'Send answer photos from your phone',loading:'Preparing your private QR code…',
    help:'Scan this QR code with your phone, choose the part, and photograph your answer. Photos appear in the matching working box here. Check the text and final answer before submitting.',
    private:'This connection belongs to your account and this problem. Opening it or uploading a photo does not use a submission attempt.',
    open:'Open phone upload',copy:'Copy link',copied:'Link copied',copyFailed:'Open the link to copy its address.',refresh:'New QR code',close:'Close phone connection',
    waiting:'Waiting for photos from your phone.',received:n=>`${n} photo${n===1?'':'s'} received. Check the recognized work below.`,
    closed:'The phone connection is closed. Open a new QR code to send more photos.',expired:'This QR code has expired. Open a new one to continue.',
    submitted:'This connection ended when an answer was submitted. Open a new QR code for your next attempt.',
    failed:'Could not connect. Please try again.',qrFailed:'The QR code could not be drawn. You can still use the upload link.',
    minutes:n=>`Link expires in about ${n} minute${n===1?'':'s'}.`
  }:{
    title:'휴대전화로 답안 사진 보내기',loading:'개인 QR 코드를 준비하는 중…',
    help:'휴대전화로 QR 코드를 스캔한 뒤 소문항을 고르고 답안을 촬영하세요. 사진의 풀이가 이 화면의 해당 소문항에 자동으로 추가됩니다. 읽힌 내용과 최종 답을 확인한 뒤 제출하세요.',
    private:'이 계정과 이 문제에서만 사용하는 연결입니다. 연결을 열거나 사진을 올리는 것만으로 제출 기회를 사용하지 않습니다.',
    open:'휴대전화 전송 화면 열기',copy:'링크 복사',copied:'링크를 복사했습니다',copyFailed:'링크를 열어 주소를 복사해 주세요.',refresh:'새 QR 코드',close:'휴대전화 연결 닫기',
    waiting:'휴대전화에서 보낼 사진을 기다리고 있습니다.',received:n=>`사진 ${n}장을 받았습니다. 아래의 읽힌 풀이를 확인해 주세요.`,
    closed:'휴대전화 연결을 닫았습니다. 사진을 더 보내려면 새 QR 코드를 여세요.',expired:'QR 코드 사용 시간이 끝났습니다. 새 QR 코드로 계속할 수 있습니다.',
    submitted:'답안이 제출되어 이 연결을 종료했습니다. 다음 제출에는 새 QR 코드를 여세요.',
    failed:'연결하지 못했습니다. 다시 시도해 주세요.',qrFailed:'QR 코드를 표시하지 못했습니다. 아래 전송 링크를 사용할 수 있습니다.',
    minutes:n=>`링크는 약 ${n}분 뒤 만료됩니다.`
  };}
  function create({container,problemId,partId,language='ko',apiBase,siteUrl,request,qr,createPoll,isCurrent=()=>true,blocked=()=>false,onPhotos=()=>true,document:doc=typeof document==='object'?document:null,clipboard=typeof navigator==='object'?navigator.clipboard:null,now=Date.now}={}){
    const T=text(language),basePath='/monthly/problems/'+encodeURIComponent(problemId)+'/scan';
    let session=null,token='',link='',svg='',cursor=0,received=0,expires=0,generation=0,disposed=false,enabled=false,loading=false,error='',notice='';
    const current=()=>!disposed&&isCurrent();
    const revoke=id=>{if(uuid(id))Promise.resolve(request('DELETE',basePath+'/'+id)).catch(()=>{});};
    const polling=createPoll({document:doc,active:()=>current()&&enabled&&!!session?.open,task:poll});
    function clear(){session=null;token='';link='';svg='';cursor=0;received=0;expires=0;error='';notice='';}
    function paint(){
      if(!current())return;
      const active=!!session?.open&&!!link;
      container.innerHTML=`<section class="armonthly-phone"><div class="armonthly-phone-head"><h4>${T.title}</h4><button class="cmbtn sm" type="button" data-phone-refresh${loading?' disabled':''}>${T.refresh}</button></div>
        <p>${T.help}</p><p class="armonthly-phone-private">${T.private}</p>
        ${loading?`<p role="status">${T.loading}</p>`:active?`<div class="armonthly-phone-content"><div class="armonthly-phone-qr" aria-label="QR">${svg||`<p>${T.qrFailed}</p>`}</div><div><a class="cmbtn pri" href="${esc(link)}" target="_blank" rel="noopener noreferrer">${T.open} ↗</a><button class="cmbtn sm" type="button" data-phone-copy>${T.copy}</button><p class="armonthly-phone-expiry">${T.minutes(Math.max(1,Math.ceil((expires-now())/60000)))}</p><p role="status" aria-live="polite">${esc(notice||(received?T.received(received):T.waiting))}</p><button class="cmbtn sm" type="button" data-phone-close>${T.close}</button></div></div>`:`<p role="status">${esc(notice||T.closed)}</p>`}
        ${error?`<p class="armonthly-phone-error" role="alert">${esc(error)}</p>`:''}</section>`;
      container.querySelector('[data-phone-refresh]').onclick=()=>{close();void open();};
      const end=container.querySelector('[data-phone-close]');if(end)end.onclick=close;
      const copy=container.querySelector('[data-phone-copy]');if(copy)copy.onclick=async()=>{
        try{if(!clipboard?.writeText)throw Error();await clipboard.writeText(link);if(current()){notice=T.copied;paint();}}
        catch(_){if(current()){notice=T.copyFailed;paint();}}
      };
    }
    async function open(){
      if(!current()||blocked()||loading)return;
      enabled=true;
      if(session?.open&&token&&expires>now()){paint();polling.wake();return;}
      const revision=++generation;clear();loading=true;paint();
      try{
        const response=await request('POST',basePath,{part_id:typeof partId==='function'?partId():partId});
        if(!current()||revision!==generation){revoke(response?.session?.id);return;}
        if(!uuid(response?.session?.id)||typeof response.token!=='string'||! /^[A-Za-z0-9_-]{32,160}$/.test(response.token)||!Number.isFinite(response.session.expires_at))throw Error('invalid_session');
        session={...response.session,open:true};token=response.token;
        expires=now()+Math.max(0,session.expires_at-(response.now||Math.floor(now()/1000)))*1000;
        const url=new URL('sim/monthly-scan.html',siteUrl);url.searchParams.set('lang',language);url.hash=new URLSearchParams({token,a:apiBase}).toString();link=url.href;
        let resultSvg='';try{resultSvg=await qr(link);}catch(_){}
        if(!current()||revision!==generation)return;
        svg=resultSvg;
        loading=false;paint();polling.wake();
      }catch(_){if(current()&&revision===generation){loading=false;error=T.failed;paint();}}
    }
    async function poll(){
      if(!current()||!enabled||!session?.open||blocked())return false;
      const revision=generation,id=session.id;let changed=false;
      try{
        // A response page is bounded to ten images. Drain at most the forty-image session limit.
        for(let page=0;page<4;page++){
          const response=await request('GET',basePath+'/'+id+'?after='+cursor);
          if(!current()||revision!==generation||blocked())return false;
          if(response?.session?.id!==id||!Array.isArray(response.photos))throw Error('invalid_session');
          const next=Number(response.cursor);if(!Number.isSafeInteger(next)||next<cursor)throw Error('invalid_cursor');
          if(response.photos.length){if(onPhotos(response.photos)===false)return false;received+=response.photos.length;changed=true;}
          const prior=cursor;cursor=next;session=response.session;error='';
          if(!session.open){
            token='';link='';svg='';enabled=false;polling.stop();
            notice=session.closed_reason==='expired'?T.expired:session.closed_reason==='submitted'?T.submitted:T.closed;
          }
          paint();
          if(!session.open||!response.has_more||cursor===prior)break;
        }
      }catch(e){if(current()&&revision===generation){
        error=T.failed;
        if(e?.status===410||e?.status===404){enabled=false;polling.stop();token='';link='';svg='';session=null;notice=T.expired;}
        paint();
      }}
      return changed;
    }
    function close(){
      generation++;enabled=false;loading=false;polling.stop();const id=session?.id;clear();revoke(id);paint();
    }
    function dispose(){if(disposed)return;const id=session?.id;disposed=true;generation++;enabled=false;polling.dispose();clear();container.innerHTML='';revoke(id);}
    return{open,close,dispose,poll,state:()=>({id:session?.id||null,open:!!session?.open,cursor,received})};
  }
  return{create,text};
});
