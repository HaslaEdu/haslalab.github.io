/* Render official URLs or a user-selected file on this device; no upload or document mirroring. */
(function () {
  'use strict';
  const CDN = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/';
  let libraryPromise = null;
  function library() {
    if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    if (libraryPromise) return libraryPromise;
    libraryPromise = new Promise((resolve,reject) => {
      const script=document.createElement('script'); script.src=CDN+'pdf.min.js';
      const timer=setTimeout(()=>failed(),15000);
      function failed() { clearTimeout(timer); script.remove(); libraryPromise=null; reject(new Error('PDF reader unavailable')); }
      script.onerror=failed;
      script.onload=()=>{clearTimeout(timer);if(!window.pdfjsLib){failed();return;}window.pdfjsLib.GlobalWorkerOptions.workerSrc=CDN+'pdf.worker.min.js';resolve(window.pdfjsLib);};
      document.head.append(script);
    });
    return libraryPromise;
  }
  function mount(host,source,options={}) {
    const ko=options.lang!=='en',tr=(a,b)=>ko?a:b;
    let alive=true,loadVersion=0,drawVersion=0,doc=null,loadingTask=null,renderTask=null,requestTimer=null,resizeTimer=null;
    let page=1,first=1,last=1,zoom=1,previousWidth=0;
    host.classList.add('contest-pdf');host.replaceChildren();
    const toolbar=document.createElement('div');toolbar.className='contest-pdf-tools';
    function button(text,label,fn){const el=document.createElement('button');el.type='button';el.textContent=text;el.setAttribute('aria-label',label);el.onclick=fn;toolbar.append(el);return el;}
    const prev=button('‹',tr('이전 쪽','Previous page'),()=>navigate(page-1));
    const pageLabel=document.createElement('label');pageLabel.textContent=tr('쪽 ','Page ');toolbar.append(pageLabel);
    const select=document.createElement('select');select.setAttribute('aria-label',tr('문제지 쪽','Paper page'));select.onchange=()=>navigate(Number(select.value));pageLabel.append(select);
    const total=document.createElement('span');total.className='hint';toolbar.append(total);
    const next=button('›',tr('다음 쪽','Next page'),()=>navigate(page+1));
    const smaller=button('−',tr('축소','Zoom out'),()=>{zoom=Math.max(.7,zoom-.2);draw();});
    const larger=button('+',tr('확대','Zoom in'),()=>{zoom=Math.min(2.5,zoom+.2);draw();});
    const fit=button(tr('폭 맞춤','Fit width'),tr('문제지 폭 맞춤','Fit paper to width'),()=>{zoom=1;draw();});
    const boundsNote=document.createElement('span');boundsNote.className='hint';boundsNote.hidden=true;boundsNote.textContent=tr('문제 페이지만 표시','Question pages only');toolbar.append(boundsNote);
    const status=document.createElement('div');status.className='contest-pdf-status';status.setAttribute('role','status');
    const viewport=document.createElement('div');viewport.className='contest-pdf-view';
    const canvas=document.createElement('canvas');canvas.hidden=true;canvas.setAttribute('role','img');viewport.append(canvas);
    const retry=document.createElement('button');retry.type='button';retry.textContent=tr('문제지 다시 열기','Retry opening paper');retry.hidden=true;retry.onclick=()=>load();
    const fallback=document.createElement('p');fallback.className='hint';fallback.hidden=true;fallback.textContent=tr('위의 공식 원문 링크로 열거나 개인 학습용 PDF를 선택하세요. 시험 시간은 계속 흐릅니다.','Use the official original link above or select a personal study PDF. The exam clock keeps running.');
    host.append(toolbar,status,viewport,retry,fallback);
    function live(v){return alive&&host.isConnected&&(v===undefined||v===loadVersion);}
    function controls(){prev.disabled=!doc||page<=first;next.disabled=!doc||page>=last;select.disabled=!doc;smaller.disabled=larger.disabled=fit.disabled=!doc;select.value=String(page);}
    function cancelDraw(){drawVersion++;if(renderTask){try{renderTask.cancel();}catch(_){}renderTask=null;}}
    function destroyDocument(){cancelDraw();if(loadingTask){try{Promise.resolve(loadingTask.destroy()).catch(()=>{});}catch(_){}loadingTask=null;}doc=null;}
    function showError(){if(!live())return;status.textContent=tr('이 화면에서 문제지를 불러오지 못했습니다.','The paper could not be loaded in this reader.');status.classList.add('error');retry.hidden=false;fallback.hidden=false;canvas.hidden=true;controls();}
    async function load(){
      const version=++loadVersion;let localTimer=null;clearTimeout(requestTimer);destroyDocument();controls();canvas.hidden=true;retry.hidden=true;fallback.hidden=true;boundsNote.hidden=true;status.classList.remove('error');status.textContent=tr('문제지를 불러오는 중입니다…','Loading paper…');
      try{
        const lib=await library();if(!live(version))return;
        // A fresh ArrayBuffer avoids reusing a buffer transferred to a previous PDF worker.
        const args=source.file?{data:new Uint8Array(await source.file.arrayBuffer())}:{url:source.url};
        if(!live(version))return;
        loadingTask=lib.getDocument(args);
        const timeout=new Promise((_,reject)=>{localTimer=setTimeout(()=>reject(new Error('Paper request timed out')),25000);requestTimer=localTimer;});
        const loaded=await Promise.race([loadingTask.promise,timeout]);clearTimeout(localTimer);
        if(!live(version)){try{await loaded.destroy();}catch(_){}return;}
        doc=loaded;
        first=Number.isInteger(options.firstPage)&&options.firstPage>0?Math.min(options.firstPage,doc.numPages):1;
        last=Number.isInteger(options.lastPage)&&options.lastPage>0?Math.min(options.lastPage,doc.numPages):doc.numPages;
        if(first>last)first=last;
        page=first;select.replaceChildren();
        for(let n=first;n<=last;n++){const option=document.createElement('option');option.value=String(n);option.textContent=String(n);select.append(option);}
        total.textContent=tr(`/ ${last}쪽`, `/ ${last}`);
        boundsNote.hidden=last>=doc.numPages;
        await draw();
      }catch(error){clearTimeout(localTimer);if(!live(version))return;destroyDocument();showError();}
    }
    function navigate(n){if(!doc||n<first||n>last)return;page=n;draw();viewport.scrollTop=0;viewport.scrollLeft=0;}
    async function draw(){
      if(!live()||!doc)return;
      cancelDraw();const version=drawVersion,documentNow=doc,pageNow=page;
      controls();status.textContent=tr('문제지를 표시하는 중입니다…','Rendering paper…');status.classList.remove('error');
      try{
        const pdfPage=await documentNow.getPage(pageNow);if(!live()||version!==drawVersion||documentNow!==doc)return;
        const available=viewport.clientWidth-24;if(available<30)return;
        const base=pdfPage.getViewport({scale:1}),scale=available/base.width*zoom,dpr=Math.min(window.devicePixelRatio||1,2),vp=pdfPage.getViewport({scale:scale*dpr});
        canvas.width=Math.ceil(vp.width);canvas.height=Math.ceil(vp.height);canvas.style.width=Math.ceil(vp.width/dpr)+'px';canvas.style.height=Math.ceil(vp.height/dpr)+'px';canvas.hidden=false;canvas.setAttribute('aria-label',tr(`문제지 ${pageNow}쪽`,`Paper page ${pageNow}`));
        renderTask=pdfPage.render({canvasContext:canvas.getContext('2d'),viewport:vp});await renderTask.promise;
        if(!live()||version!==drawVersion||documentNow!==doc)return;renderTask=null;status.textContent=tr(`${pageNow}쪽 · ${Math.round(zoom*100)}%`, `Page ${pageNow} · ${Math.round(zoom*100)}%`);retry.hidden=true;fallback.hidden=true;
      }catch(error){if(!live()||version!==drawVersion||error.name==='RenderingCancelledException')return;showError();}
    }
    const observer=typeof ResizeObserver==='function'?new ResizeObserver(()=>{const width=host.clientWidth;if(width<=0||Math.abs(width-previousWidth)<2)return;previousWidth=width;clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>draw(),100);}):null;
    if(observer)observer.observe(host);load();
    return {dispose(){alive=false;loadVersion++;clearTimeout(requestTimer);clearTimeout(resizeTimer);if(observer)observer.disconnect();destroyDocument();},refresh(){if(live())draw();}};
  }
  window.ContestPdf={mount};
})();
