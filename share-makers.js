/* window.HL_SHARE_MAKER: the "공유하기" step the Workshop's makers share (teach.html's problem maker, create.html's
   simulation studio). It asks for what a project in 작품 공유 shows besides its content (description, how to use,
   notes and credits, tags, topic), checks it with HL_SHARE.check (share-publish.js, the server's own checks) before
   anything is sent, and builds what is published:

     paperPayload(paper)        teach.js's paper → the 'set' payload {title, info, minutes, items} (the fields the server
                                keeps: community/src/workshop-share.js cleanSet); bank problems by key, own problems
                                with their text, answer, solution, choices and figure (an SVG data URL, never its scene)
     paperFromPayload(payload)  a shared set → the fields of a new paper (teach.js cleans each item again)
     publishInput(o)            {type, form, payload?, thumbnail?, creationId?, remixOf?} → HL_SHARE.publish's input:
                                a remix draft or a saved creation is published by creation_id, never as a new one
     readForm(values) / formErrors(input)   the dialog's fields → the publish fields, and the error messages to show
     paperThumb(paper)          a PNG (canvas) of the paper's title and first problem, ≤ 200 KB, or '' when it cannot be drawn
     dialog({...})              the dialog itself: a <dialog class="shdlg"> with the fields, the errors and the result
   Nothing a member wrote is put into the page as markup: the fields are filled through .value and messages through
   textContent. */
(function(){
  'use strict';
  const TOPICS=['mechanics','em','thermal','optics','waves','modern','other'];
  const S={
    ko:{title:'작품 공유에 올리기',updTitle:'공유 내용 고치기',name:'제목',desc:'설명',descPh:'무엇을 만들었는지, 누구에게 쓸모 있는지 적어 주세요.',howto:'사용 방법',howtoPh:'어떻게 쓰면 좋은지 (예: 수업 도입에 10분, 슬라이더로 길이를 바꿔 보기)',
      notes:'참고 · 출처',notesPh:'참고한 자료나 도와준 사람',tags:'태그 (쉼표로, 8개까지)',tagsPh:'진자, 주기, 고1',topic:'분야',thumb:'미리보기 그림',noThumb:'미리보기 그림 없이 올립니다.',
      topics:{mechanics:'역학',em:'전자기',thermal:'열',optics:'광학',waves:'파동',modern:'현대물리',other:'기타'},
      publish:'공유하기',update:'공유 내용 업데이트',unpublish:'공유 취소',cancel:'닫기',sending:'올리는 중…',done:'작품 공유에 올렸습니다.',updated:'공유 내용을 고쳤습니다.',unpublished:'공유를 취소했습니다. 다시 공유하면 같은 작품으로 올라갑니다.',
      view:'작품 공유에서 보기',unpubAsk:'공유를 취소할까요? 작품 공유 목록에서 사라집니다.',hint:'설명은 글로만 보입니다. **굵게**, `코드`, "- "로 시작하는 줄, https 링크만 꾸며집니다.',
      err:{bad_title:'제목을 1~80자로 적어 주세요.',bad_description:'설명은 3000자까지입니다.',bad_howto:'사용 방법은 3000자까지입니다.',bad_notes:'참고 · 출처는 2000자까지입니다.',bad_tags:'태그는 20자 안의 낱말로 8개까지입니다.',
        bad_topic:'분야를 고르세요.',bad_thumbnail:'미리보기 그림을 쓸 수 없습니다.',bad_payload:'올릴 내용이 비어 있거나 형식이 맞지 않습니다.',payload_too_large:'내용이 너무 큽니다.',bad_type:'올릴 수 없는 종류입니다.',
        login_required:'로그인하세요.',hidden_by_staff:'운영진이 숨긴 작품이라 다시 올릴 수 없습니다.',rate_limited:'오늘 올릴 수 있는 수를 넘었습니다. 잠시 뒤에 다시 해 주세요.',not_owner:'내 작품만 고칠 수 있습니다.',not_found:'작품을 찾지 못했습니다.',network:'서버에 연결하지 못했습니다.',bad_request:'입력을 확인해 주세요.'}},
    en:{title:'Share in the gallery',updTitle:'Edit what is shared',name:'Title',desc:'Description',descPh:'What you made and who it is for.',howto:'How to use it',howtoPh:'How to use it (e.g. a 10-minute class opener; change the length with the slider)',
      notes:'Notes and credits',notesPh:'Sources you used, people who helped',tags:'Tags (comma-separated, up to 8)',tagsPh:'pendulum, period',topic:'Topic',thumb:'Thumbnail',noThumb:'Shared without a thumbnail.',
      topics:{mechanics:'Mechanics',em:'Electromagnetism',thermal:'Thermal',optics:'Optics',waves:'Waves',modern:'Modern physics',other:'Other'},
      publish:'Share',update:'Update the shared copy',unpublish:'Stop sharing',cancel:'Close',sending:'Sharing…',done:'Shared in the gallery.',updated:'Updated.',unpublished:'No longer shared. Sharing again brings back the same project.',
      view:'View in the gallery',unpubAsk:'Stop sharing? It leaves the gallery.',hint:'Descriptions are plain text: **bold**, `code`, lines starting "- " and https links are drawn.',
      err:{bad_title:'Give it a title of 1–80 characters.',bad_description:'The description is limited to 3000 characters.',bad_howto:'"How to use it" is limited to 3000 characters.',bad_notes:'Notes are limited to 2000 characters.',bad_tags:'Up to 8 tags of at most 20 characters.',
        bad_topic:'Pick a topic.',bad_thumbnail:'The thumbnail cannot be used.',bad_payload:'There is nothing to share, or it is not in the right form.',payload_too_large:'It is too large to share.',bad_type:'This kind cannot be shared.',
        login_required:'Log in first.',hidden_by_staff:'Staff hid this project, so it cannot be shared again.',rate_limited:'You have shared as much as today allows. Try again later.',not_owner:'You can only edit your own.',not_found:'Not found.',network:'Could not reach the server.',bad_request:'Check the fields.'}}
  };
  const L=lang=>S[lang==='en'?'en':'ko'];
  const str=(v,n)=>typeof v==='string'?v.slice(0,n):'';

  /* ── the set payload ── */
  const KEY=/^[\w:.~\-]{1,80}$/;
  function paperPayload(paper,lang){
    const p=paper&&typeof paper==='object'?paper:{};
    const info=[str(p.school,120).trim(),str(p.info,120).trim()].filter(Boolean).join(' · ');
    const items=[];
    for(const it of Array.isArray(p.items)?p.items:[]){
      if(items.length>=100)break;
      if(!it||typeof it.key!=='string'||!KEY.test(it.key))continue;
      const pts=Math.max(0,Math.min(100,+it.pts||0));
      if(!it.own){if(!it.key.startsWith('own:'))items.push({key:it.key,pts});continue;}
      const w=it.own,fig=w.fig&&typeof w.fig.src==='string'&&/^data:image\/svg\+xml;base64,/.test(w.fig.src)&&w.fig.src.length<=300000*1.4?{src:w.fig.src,w:+w.fig.w||800,h:+w.fig.h||400}:null;
      const own={q:str(w.q,6000).trim()||(fig?(lang==='en'?'(figure)':'(그림)'):''),answer:str(w.answer,400),unit:str(w.unit,24),sol:str(w.sol,6000)};
      if(!own.q)continue;
      if(Array.isArray(w.choices)&&w.choices.length){own.choices=w.choices.slice(0,10).map(c=>str(c,500));own.correct=Number.isInteger(w.correct)&&w.correct>=0&&w.correct<own.choices.length?w.correct:0;}
      if(fig)own.fig=fig;
      items.push({key:it.key,pts,own});
    }
    const min=parseInt(p.minutes,10);
    return {title:str(p.title,120).trim(),info,minutes:Number.isFinite(min)&&min>0?Math.min(600,min):0,items};
  }
  function paperFromPayload(pl){
    if(!pl||typeof pl!=='object'||!Array.isArray(pl.items))return null;
    return {title:str(pl.title,120),info:str(pl.info,120),minutes:pl.minutes?String(Math.max(0,Math.min(600,parseInt(pl.minutes,10)||0))||''):'',items:pl.items.slice(0,100)};
  }

  /* ── the form ── */
  function readForm(v){
    const tags=String(v?.tags||'').split(/[,#\n]/).map(t=>t.trim()).filter(Boolean);
    return {title:String(v?.title||'').trim(),description:String(v?.description||''),howto:String(v?.howto||''),notes:String(v?.notes||''),tags,topic:TOPICS.includes(v?.topic)?v.topic:'other'};
  }
  const errText=(code,lang)=>L(lang).err[code]||String(code||'error');
  /** the dialog's checks: HL_SHARE.check on the whole input (an update: only what it sends), as messages to show */
  function formErrors(input,lang,partial,own){const H=window.HL_SHARE;const codes=H?[...H.check(input,!!partial)]:['network'];
    return codes.map(c=>({code:c,text:L(lang).err[c]||(own&&own({code:c,message:c}))||String(c)}));}
  function publishInput(o){
    const f=readForm(o.form||{}),out={type:o.type,title:f.title,description:f.description,howto:f.howto,notes:f.notes,tags:f.tags,topic:f.topic};
    if(o.payload!=null)out.payload=o.payload;
    if(o.thumbnail)out.thumbnail=o.thumbnail;
    if(Number.isInteger(o.creationId)&&o.creationId>0)out.creation_id=o.creationId;
    else if(Number.isInteger(o.remixOf)&&o.remixOf>0)out.remix_of=o.remixOf;
    return out;
  }
  /** the most common area of the bank problems' units ('mechanics/energy' → 'mechanics'), else 'other' */
  function topicGuess(units){
    const n={};for(const u of units||[]){const a=String(u||'').split('/')[0];if(TOPICS.includes(a)&&a!=='other')n[a]=(n[a]||0)+1;}
    return Object.keys(n).sort((a,b)=>n[b]-n[a])[0]||'other';
  }

  /* ── a thumbnail of the paper: its title and the start of its first problem, drawn on a canvas ── */
  function paperThumb(paper,lang){
    try{
      const c=document.createElement('canvas');if(!c.getContext)return '';
      const W=480,H=300;c.width=W;c.height=H;const g=c.getContext('2d');if(!g)return '';
      g.fillStyle='#f6f4fb';g.fillRect(0,0,W,H);g.fillStyle='#fff';g.fillRect(28,18,W-56,H-18);g.strokeStyle='#d5dbe6';g.strokeRect(28.5,18.5,W-57,H-19);
      g.fillStyle='#7059a4';g.fillRect(28,18,W-56,5);
      const font='"Pretendard Variable",Pretendard,system-ui,"Apple SD Gothic Neo","Noto Sans KR",sans-serif';
      const p=paper||{},first=(p.items||[]).find(x=>x&&(x.own?.q||x.text));
      g.fillStyle='#263247';g.font='700 22px '+font;g.textAlign='center';
      g.fillText(String(p.title||(lang==='en'?'Problem set':'문제 세트')).slice(0,30),W/2,62);
      g.fillStyle='#657187';g.font='13px '+font;
      const n=(p.items||[]).length;g.fillText(lang==='en'?`${n} problem${n===1?'':'s'}`:`${n}문항`,W/2,86);
      g.textAlign='left';g.fillStyle='#263247';g.font='15px '+font;
      const text=String(first?.own?.q||first?.text||'').replace(/\$\$?([^$]*)\$\$?/g,'$1').replace(/\\[a-zA-Z]+/g,'').replace(/\s+/g,' ').trim();
      if(text){
        const words=[...text];let line='',y=124,lines=0;g.fillText('1.',48,y);
        for(const ch of words){const t=line+ch;if(g.measureText(t).width>W-120){g.fillText(line,72,y);line=ch.trim()?ch:'';y+=24;if(++lines>=6)break;}else line=t;}
        if(lines<6&&line)g.fillText(line,72,y);
      }
      let url=c.toDataURL('image/png');
      if(url.length>200*1024*1.33)url=c.toDataURL('image/jpeg',0.8);
      return /^data:image\/(png|jpeg);base64,/.test(url)&&url.length<=200*1024*1.33?url:'';
    }catch(e){return '';}
  }

  /* ── the dialog ──
     o: {lang, type, values:{title, description, howto, notes, tags, topic}, thumbnail, shared:{id, published}|null,
         build(form) → the publish input, publish(input) → Promise<{id}>, update(input) → Promise, unpublish() → Promise,
         onDone(result), errText(error) for the maker's own error codes, height()} */
  function dialog(o){
    const T=L(o.lang),H=window.HL_SHARE,v=o.values||{};
    let dlg=document.getElementById('shDlg');if(!dlg){dlg=document.createElement('dialog');dlg.id='shDlg';dlg.className='stdlg shdlg';document.body.append(dlg);}
    const live=!!(o.shared&&o.shared.id&&o.shared.published);
    dlg.innerHTML=`<form method="dialog" class="sh-form" novalidate><div class="dlg-head"><h2></h2><button type="button" data-x aria-label="${T.cancel}">✕</button></div>
      <div class="sh-fields">
        <label>${T.name}<input name="title" maxlength="80" required></label>
        <label>${T.desc}<textarea name="description" rows="4" maxlength="3000"></textarea></label>
        <label>${T.howto}<textarea name="howto" rows="3" maxlength="3000"></textarea></label>
        <label>${T.notes}<textarea name="notes" rows="2" maxlength="2000"></textarea></label>
        <div class="sh-two"><label>${T.tags}<input name="tags"></label>
          <label>${T.topic}<select name="topic">${TOPICS.map(k=>`<option value="${k}">${T.topics[k]}</option>`).join('')}</select></label></div>
        <p class="help">${T.hint}</p>
        <div class="sh-thumb"><span class="note">${T.thumb}</span><span data-thumb></span></div>
      </div>
      <ul class="sh-errs" role="alert"></ul><p class="note sh-msg" role="status"></p>
      <div class="row sh-acts"><button type="submit" class="primary" data-go></button>${live?`<button type="button" data-unpub>${T.unpublish}</button>`:''}<button type="button" data-x>${T.cancel}</button></div></form>`;
    const f=dlg.querySelector('form'),F=f.elements,q=s=>dlg.querySelector(s);
    q('h2').textContent=live?T.updTitle:T.title;q('[data-go]').textContent=live?T.update:T.publish;
    F.title.value=v.title||'';F.description.value=v.description||'';F.howto.value=v.howto||'';F.notes.value=v.notes||'';
    F.tags.value=Array.isArray(v.tags)?v.tags.join(', '):v.tags||'';F.topic.value=TOPICS.includes(v.topic)?v.topic:'other';
    F.description.placeholder=T.descPh;F.howto.placeholder=T.howtoPh;F.notes.placeholder=T.notesPh;F.tags.placeholder=T.tagsPh;
    const th=q('[data-thumb]');
    if(o.thumbnail){const im=document.createElement('img');im.src=o.thumbnail;im.alt='';th.append(im);}else th.textContent=T.noThumb;
    const errs=q('.sh-errs'),msg=q('.sh-msg'),et=c=>T.err[c]||(o.errText&&o.errText({code:c,message:c}))||String(c||'error');
    const showErrs=list=>{errs.textContent='';for(const e of list){const li=document.createElement('li');li.textContent=e.text;errs.append(li);}};
    const say=(t,cls)=>{msg.className='note sh-msg '+(cls||'');msg.textContent=t||'';};
    const form=()=>readForm({title:F.title.value,description:F.description.value,howto:F.howto.value,notes:F.notes.value,tags:F.tags.value,topic:F.topic.value});
    const finish=(text,id)=>{
      say(text,'ok');showErrs([]);
      const acts=q('.sh-acts');acts.textContent='';
      if(id){const a=document.createElement('button');a.type='button';a.className='primary';a.textContent=T.view;a.dataset.view='1';a.onclick=()=>H.open(id);acts.append(a);}
      const x=document.createElement('button');x.type='button';x.textContent=T.cancel;x.onclick=()=>dlg.close();acts.append(x);
      o.height&&o.height();
    };
    dlg.querySelectorAll('[data-x]').forEach(b=>b.onclick=()=>dlg.close());
    f.onsubmit=async e=>{
      e.preventDefault();
      const fv=form(),input=o.build(fv),list=formErrors(input,o.lang,live,o.errText);
      showErrs(list);if(list.length)return;
      const go=q('[data-go]');go.disabled=true;say(T.sending);
      try{
        if(live){await o.update(input);finish(T.updated,o.shared.id);o.onDone&&o.onDone({id:o.shared.id,updated:true,form:fv});}
        else{const r=await o.publish(input);finish(T.done,r&&r.id);o.onDone&&o.onDone({id:r&&r.id,form:fv});}
      }catch(err){go.disabled=false;say('');showErrs((err&&err.codes||[err&&err.code]).map(c=>({code:c,text:et(c)})));}
    };
    const ub=q('[data-unpub]');
    if(ub)ub.onclick=async()=>{if(!confirm(T.unpubAsk))return;ub.disabled=true;
      try{await o.unpublish();finish(T.unpublished,null);o.onDone&&o.onDone({id:o.shared.id,unpublished:true});}
      catch(err){ub.disabled=false;showErrs([{text:et(err&&err.code)}]);}};
    if(!dlg.open)dlg.showModal?.();
    F.title.focus?.();
    return dlg;
  }

  window.HL_SHARE_MAKER={paperPayload,paperFromPayload,readForm,formErrors,publishInput,topicGuess,paperThumb,dialog,errText,TOPICS,S};
})();
