(() => {
  const types = {sim:['시뮬레이션','Simulation'],figure:['그림','Figure'],set:['문제·시험지','Problems and papers']};
  window.HL_WS_PUBLISH = async ({file,api,text:T,here,error}) => {
    const dialog=document.createElement('dialog');
    dialog.className='ws-share-dialog ws-student-paper';
    dialog.innerHTML='<form><h2></h2><p data-status role="status"></p><label hidden><span></span><input name="title" required maxlength="80"></label><details hidden><summary></summary><pre></pre></details><div class="ws-acts"><button type="submit" class="ws-btn pri" hidden></button><button type="button" class="ws-btn" data-close></button></div></form>';
    document.body.append(dialog);
    dialog.onclose=()=>dialog.remove();
    const form=dialog.querySelector('form'), title=form.elements.title, status=form.querySelector('[data-status]'), submit=form.querySelector('[type=submit]');
    const trError=e=>({
      bad_source:T('워크샵 JSON 또는 Python·C 소스 파일을 선택하세요.','Select a Workshop JSON file or a Python or C source file.'),
      bad_payload:T('이 파일의 작품 내용을 읽을 수 없습니다.','This file does not contain a valid project.'),
      source_changed:T('미리 본 뒤 파일이 바뀌었습니다. 닫고 다시 열어 확인하세요.','The file changed after preview. Close and reopen it to review the latest version.'),
      workshop_daily_share_limit:T('오늘은 새 작품을 3개까지 공개할 수 있습니다.','You can publish up to three new projects today.'),
      workshop_public_cap:T('공개 중인 작품은 10개까지입니다.','You can have up to ten public projects.'),
      file_too_large:T('미리 볼 파일은 1 MB까지입니다.','Choose a file up to 1 MB.')
    }[e?.code]||error(e?.code));
    dialog.querySelector('h2').textContent=T('작품 공개 미리보기','Preview public project');
    dialog.querySelector('[data-close]').textContent=T('닫기','Close');
    dialog.querySelector('[data-close]').onclick=()=>dialog.close();
    status.textContent=T('파일을 확인하는 중…','Loading project…');
    dialog.showModal();
    try{
      const p=await api('GET','/share/source?file='+encodeURIComponent(file.id)+'&provider='+encodeURIComponent(file.provider||'storage'));
      if(!here()||!dialog.open){dialog.close();return;}
      const type=types[p.type]||[];
      status.textContent=(T(...type)||'')+' · '+T('아래 내용은 게시 후 누구나 볼 수 있습니다.','Anyone can view the content below after publication.')+(p.type==='set'?' '+T('파일에 포함된 정답과 해설도 공개됩니다.','Answers and explanations in the file are included.'):'');
      title.value=p.previous?.title||p.title;
      const label=title.closest('label');label.hidden=false;label.querySelector('span').textContent=T('공개 제목','Public title');
      const details=form.querySelector('details'), pre=details.querySelector('pre');
      details.hidden=false;
      details.querySelector('summary').textContent=T('공개되는 데이터 확인','Review public data');
      pre.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;max-height:16rem;overflow:auto';
      pre.textContent=p.type==='sim'?p.payload.code:JSON.stringify(p.payload,null,2);
      if (p.type==='figure') import('./draw-render.mjs').then(({renderSVG})=>{
        if (!dialog.open) return;
        const svg=renderSVG(p.payload.scene,{width:600});
        const image=new Image();
        image.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
        image.alt=T('공개될 그림','Figure to be shared');
        details.before(image);
      }).catch(()=>{});
      if (p.type==='set') {
        const list=document.createElement('ol');
        for (const item of p.payload.items.slice(0,5)) {
          const li=document.createElement('li');
          li.textContent=item.own?.q || item.key;
          list.append(li);
        }
        details.before(list);
      }
      submit.hidden=false;
      submit.textContent=p.previous?T('기존 작품 업데이트','Update existing project'):T('작품 공개','Publish project');
      form.onsubmit=async e=>{
        e.preventDefault();
        submit.disabled=true;
        try {
          const result=await api('POST','/share',{source_file:file.id,source_provider:file.provider,source_digest:p.digest,title:title.value,description:p.description});
          dialog.close();location.hash='/workshop/share/'+result.id;
        } catch(e) {status.textContent=trError(e);submit.disabled=false;}
      };
    }catch(e){status.textContent=trError(e);}
  };
})();
