/* Storage connectors on #/workshop/storage (community/src/workshop-connectors.js): tabs 하슬라랩 보관함 / Google Drive /
   GitHub above the storage list. index.html's mountWorkshopStorage() calls HL_WS_CONNECT.mount() once the member is
   known; this file draws the tabs and the Drive and GitHub panels. No token of Google or GitHub ever reaches the page:
   every call goes to the HaslaLab API with the member's own HaslaLab token. */
(function(){
  "use strict";
  const S={tab:"store",status:null,msg:"",drive:{folder:"",data:null},gh:{path:"",data:null,repos:null,picking:false},storeFiles:null,busy:false,uninstall:null};
  const TYPES=["pdf","png","jpg","jpeg","webp","svg","json","txt","csv","md","hwpx","docx","xlsx","pptx"];
  let C=null;
  const ERR={
    not_configured:["준비 중입니다. 관리자 설정 후 열립니다.","Not set up yet. Opens once the administrator has set it up."],
    not_connected:["먼저 연결해 주세요.","Connect first."],
    drive_reconnect:["Google Drive 연결이 끊어졌습니다. 다시 연결해 주세요.","The Google Drive link has expired. Please connect again."],
    github_reconnect:["GitHub 설치가 없어졌습니다. 다시 연결해 주세요.","The GitHub installation is gone. Please connect again."],
    drive_scope_missing:["Google 화면에서 Drive 권한에 체크해야 연결됩니다.","Tick the Drive permission on Google's screen to connect."],
    drive_no_refresh:["Google이 오래 쓸 수 있는 권한을 주지 않았습니다. 다시 연결해 주세요.","Google did not grant lasting access. Please connect again."],
    wrong_user:["이 연결은 다른 계정에서 시작되었습니다. 이 계정에서 다시 연결해 주세요.","This link was started from another account. Connect again from this one."],
    bad_ticket:["연결 링크가 만료되었거나 이미 쓰였습니다. 다시 연결해 주세요.","The link has expired or was already used. Connect again."],
    expired:["시간이 지나 연결하지 못했습니다. 다시 연결해 주세요.","The link expired. Connect again."],
    cancelled:["연결을 취소했습니다.","Connection cancelled."],
    not_your_installation:["이 GitHub 계정이 설치한 HaslaLab 앱이 아닙니다.","That installation does not belong to this GitHub account."],
    no_installation:["HaslaLab 앱 설치를 찾지 못했습니다. 저장소를 골라 설치해 주세요.","No HaslaLab installation was found. Install it on a repository."],
    install_requested:["조직 관리자의 승인을 기다리고 있습니다. 승인 후 다시 연결해 주세요.","Waiting for the organization owner's approval. Connect again once approved."],
    repo_not_chosen:["저장소를 먼저 골라 주세요.","Choose a repository first."],
    github_repo_not_allowed:["이 저장소는 설치에 포함되어 있지 않습니다.","That repository is not part of the installation."],
    github_conflict:["GitHub에서 파일이 바뀌었습니다. 새로 고친 뒤 다시 해 주세요.","The file changed on GitHub. Refresh and try again."],
    bad_path:["폴더 이름을 확인해 주세요. 글자, 숫자, 공백, . _ - ( ) 만 쓸 수 있고 .으로 시작할 수 없습니다.","Check the folder name: letters, digits, spaces and . _ - ( ) only, not starting with a dot."],
    file_too_large:["파일 하나는 20MB까지입니다.","Each file can be up to 20 MB."],
    quota_exceeded:["보관함 용량이 모자랍니다.","Your storage is full."],
    type_not_allowed:["옮길 수 없는 파일 형식입니다.","This file type is not allowed."],
    type_mismatch:["파일 내용이 확장자와 맞지 않습니다.","The file does not match its extension."],
    rate_limited:["잠시 뒤에 다시 시도해 주세요.","Try again in a moment."],
    network:["연결에 실패했습니다.","Could not connect."],
    other:["처리하지 못했습니다.","Something went wrong."]};
  const T=(ko,en)=>C.ko?ko:C.LX(en);
  const err=code=>{const e=ERR[code]||ERR[/^(drive|github)_/.test(code||"")?"other":code]||ERR.other;return T(e[0],e[1]);};
  const esc=s=>C.esc(s==null?"":s);
  const bytes=n=>n==null?"":n>=1048576?(n/1048576).toFixed(1)+" MB":n>=1024?Math.round(n/1024)+" KB":n+" B";
  const api=(m,p,b)=>C.api(m,"/workshop/connectors"+p,b);
  async function raw(method,path,body){
    let r;try{r=await fetch(C.base()+"/api/workshop/connectors"+path,{method,headers:{Authorization:"Bearer "+C.token()},body});}catch(e){throw{code:"network"};}
    if(!r.ok){const j=await r.json().catch(()=>({}));throw{code:j.error||"other",status:r.status};}
    return r;
  }
  function style(){
    if(document.getElementById("wsConnStyle"))return;
    const s=document.createElement("style");s.id="wsConnStyle";
    s.textContent=`.ws-tabs{display:flex;gap:4px;border-bottom:1px solid #e3e8f0;margin:0 0 14px;overflow-x:auto}
.ws-tabs button{background:none;border:0;border-bottom:2px solid transparent;padding:9px 12px;font:600 14px var(--sans,system-ui);color:#56607a;cursor:pointer;white-space:nowrap}
.ws-tabs button[aria-selected="true"]{color:#3d2a6b;border-bottom-color:#6b4fb0}
.ws-tabs .ws-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#2f9e6a;margin-left:6px;vertical-align:1px}
.ws-cpanel{margin-bottom:26px}
.ws-chead{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;justify-content:space-between;padding:12px 14px;border:1px solid #e3e8f0;border-radius:10px;margin-bottom:12px;background:#fafbfd}
.ws-chead b{font-size:15px}.ws-chead p{margin:2px 0 0;font-size:13px;color:#56607a}
.ws-ccard{border:1px solid #e3e8f0;border-radius:12px;padding:18px;max-width:560px}
.ws-ccard h3{margin:0 0 6px;font-size:16px}.ws-ccard p{margin:0 0 10px;font-size:14px;color:#56607a}
.ws-ccard .ws-tag{display:inline-block;font-size:12px;padding:3px 8px;border-radius:999px;background:#eef1f6;color:#56607a}
.ws-cform{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}
.ws-cform select,.ws-cform input{font:14px var(--sans,system-ui);padding:6px 8px;border:1px solid #cfd6e2;border-radius:8px;min-width:0;max-width:100%}
.ws-cform label{font-size:13px;color:#56607a}
.ws-import{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 10px;font-size:13px}
.ws-import select{max-width:100%;min-width:0;flex:1 1 180px;font:13px var(--sans,system-ui);padding:5px 6px;border:1px solid #cfd6e2;border-radius:8px}
.ws-cnote{font-size:13px;color:#56607a;margin:8px 0}.ws-cnote a{color:#5c438f;text-decoration:underline}.ws-ccard{background:#fff}
@media (max-width:560px){.ws-chead{padding:10px}.ws-ccard{padding:14px}}
html[data-theme="dark"] .ws-cnote a{color:#cfbdf2}html[data-theme="dark"] .ws-tabs{border-color:#333a4d}html[data-theme="dark"] .ws-tabs button{color:#a9b2c8}
html[data-theme="dark"] .ws-tabs button[aria-selected="true"]{color:#e4dafb;border-bottom-color:#a68be0}
html[data-theme="dark"] :is(.ws-chead,.ws-ccard){background:#1b1f2b;border-color:#333a4d}
html[data-theme="dark"] :is(.ws-chead p,.ws-ccard p,.ws-cnote,.ws-cform label){color:#a9b2c8}
html[data-theme="dark"] :is(.ws-cform select,.ws-cform input,.ws-import select){background:#141824;color:#e7eaf2;border-color:#3a4256}`;
    document.head.append(s);
  }
  const live=()=>C&&C.here()&&C.tabs.isConnected;
  function paint(){
    if(!live())return;
    const st=S.status,tab=S.tab;
    const tabBtn=(key,label,on)=>`<button type="button" role="tab" data-wsc-tab="${key}" aria-selected="${tab===key}">${label}${on?`<span class="ws-dot" aria-label="${T("연결됨","connected")}"></span>`:""}</button>`;
    C.tabs.innerHTML=tabBtn("store",T("하슬라랩 보관함","HaslaLab storage"),false)+tabBtn("drive","Google Drive",st?.drive?.connected)+tabBtn("github","GitHub",st?.github?.connected);
    C.tabs.querySelectorAll("[data-wsc-tab]").forEach(b=>b.onclick=()=>{S.tab=b.dataset.wscTab;S.msg="";try{sessionStorage.setItem("hlWsTab",S.tab);}catch(e){}paint();load();});
    C.store.hidden=tab!=="store";C.panel.hidden=tab==="store";
    if(tab==="store")return;
    C.panel.innerHTML=!st?`<p class="ws-note">${T("불러오는 중…","Loading…")}</p>${msgLine()}`:tab==="drive"?drivePanel():ghPanel();
    wire();
  }
  const msgLine=()=>`<p class="ws-msg" role="status">${esc(S.msg)}</p>`;
  function card(prov,state){
    const name=prov==="drive"?"Google Drive":"GitHub";
    const access=prov==="drive"?T("HaslaLab이 만든 ‘HaslaLab’ 폴더만 봅니다. 드라이브의 다른 파일은 볼 수 없습니다.","HaslaLab only sees the ‘HaslaLab’ folder it creates. It cannot see your other Drive files.")
      :T("고른 저장소의 haslalab/ 폴더만 씁니다. 설치할 때 ‘Only select repositories’로 저장소를 고르세요.","HaslaLab only writes to the haslalab/ folder of the repository you pick. Choose ‘Only select repositories’ when installing.");
    if(state==="off")return `<div class="ws-ccard"><h3>${name}</h3><p>${access}</p><span class="ws-tag">${T("준비 중 — 관리자 설정 후 열립니다","Coming soon — opens once the administrator has set it up")}</span></div>`;
    const extra=prov==="github"?`<p class="ws-cnote">${T("새 저장소가 필요하면 GitHub에서 먼저 만든 뒤, 설치에 그 저장소를 포함하세요. HaslaLab은 저장소를 만들지 않습니다.","Need a new repository? Create it on GitHub first and include it in the installation. HaslaLab does not create repositories.")}</p>`:"";
    const was=prov==="github"&&S.uninstall?`<p class="ws-cnote">${T("GitHub에서 앱을 완전히 지우려면: ","To remove the app from GitHub too: ")}<a href="${esc(S.uninstall)}" target="_blank" rel="noopener noreferrer">${T("GitHub 설치 설정","GitHub installation settings")}</a></p>`:"";
    return `<div class="ws-ccard"><h3>${name}</h3><p>${access}</p>${extra}<button type="button" class="ws-btn pri" data-wsc-connect="${prov==="drive"?"google":"github"}">${T("연결하기","Connect")}</button>${was}</div>${msgLine()}`;
  }
  const head=(title,line,acts)=>`<div class="ws-chead"><div><b>${title}</b><p>${line}</p></div><span class="ws-acts">${acts}</span></div>`;
  const importRow=(dest)=>{
    const files=S.storeFiles||[];
    return `<div class="ws-import"><label for="wscImport">${T("보관함에서 가져오기","Copy from storage")}</label><select id="wscImport" data-wsc-pick>${files.length?files.map(f=>`<option value="${esc(f.id)}">${esc((f.folder?f.folder+"/":"")+f.name)}</option>`).join(""):`<option value="">${T("보관함에 파일이 없습니다","No files in storage")}</option>`}</select>
      <button type="button" class="ws-btn ghost" data-wsc-import ${files.length?"":"disabled"}>${dest}</button></div>`;
  };
  const upload=()=>`<label class="ws-btn pri ws-upbtn">${T("파일 올리기","Upload files")}<input type="file" multiple data-wsc-file accept="${TYPES.map(x=>"."+x).join(",")}"></label>`;
  function rows(items,kind){
    if(!items.length)return `<p class="ws-empty">${T("아직 파일이 없습니다.","No files yet.")}</p>`;
    return `<ul class="ws-list">${items.map(f=>f.folder
      ?`<li class="ws-row ws-folder"><button type="button" class="ws-name" data-wsc-go="${esc(kind==="drive"?f.id:f.path)}"><span class="ws-ico" aria-hidden="true">▸</span>${esc(f.name)}</button><span class="ws-meta">${T("폴더","Folder")}</span><span class="ws-row-acts"></span></li>`
      :`<li class="ws-row"><span class="ws-name"><span class="ws-ext">${esc(String(f.name.split(".").pop()).toUpperCase())}</span>${esc(f.name)}</span><span class="ws-meta">${bytes(f.size)}</span>
        <span class="ws-row-acts"><button type="button" data-wsc-down="${esc(kind==="drive"?f.id:f.path)}" data-name="${esc(f.name)}">${T("내려받기","Download")}</button>${kind==="drive"?`<button type="button" data-wsc-rename="${esc(f.id)}" data-name="${esc(f.name)}">${T("이름 바꾸기","Rename")}</button>`:""}<button type="button" data-wsc-tostore="${esc(kind==="drive"?f.id:f.path)}">${T("보관함으로 복사","Copy to storage")}</button>${/\.(json|py|c)$/i.test(f.name)?` <button type="button" data-wsc-publish="${esc(kind==="drive"?f.id:f.path)}">${T("작품 공개","Publish project")}</button>`:""}<button type="button" data-wsc-del="${esc(kind==="drive"?f.id:f.path)}" data-name="${esc(f.name)}">${T("삭제","Delete")}</button></span></li>`).join("")}</ul>`;
  }
  function drivePanel(){
    const d=S.status?.drive;
    if(!d?.configured)return card("drive","off");
    if(!d.connected)return card("drive","on");
    const D=S.drive.data;
    const top=head("Google Drive"+(d.email?" · "+esc(d.email):""),T("HaslaLab이 만든 ‘HaslaLab’ 폴더만 봅니다.","HaslaLab only sees the ‘HaslaLab’ folder it created."),`<button type="button" class="ws-btn ghost" data-wsc-off="google">${T("연결 끊기","Disconnect")}</button>`);
    if(!D)return top+`<p class="ws-note">${T("불러오는 중…","Loading…")}</p>${msgLine()}`;
    const trail=D.trail||[];
    const crumbs=`<nav class="ws-crumbs" aria-label="${T("폴더 위치","Folder")}">${trail.map((x,i)=>i===trail.length-1?`<b>${esc(x.name)}</b>`:`<button type="button" data-wsc-go="${esc(x.id)}">${esc(x.name)}</button><span aria-hidden="true">/</span>`).join("")}</nav>`;
    return top+`<div class="ws-tools">${crumbs}<span class="ws-acts"><button type="button" class="ws-btn ghost" data-wsc-newfolder>${T("새 폴더","New folder")}</button>${upload()}</span></div>
      ${importRow(T("드라이브로 복사","Copy to Drive"))}${rows(D.files,"drive")}${msgLine()}`;
  }
  function ghPanel(){
    const g=S.status?.github;
    if(!g?.configured)return card("github","off");
    if(!g.connected)return card("github","on");
    const acts=`${g.repo?`<button type="button" class="ws-btn ghost" data-wsc-pickrepo>${T("저장소 바꾸기","Change repository")}</button>`:""}<button type="button" class="ws-btn ghost" data-wsc-off="github">${T("연결 끊기","Disconnect")}</button>`;
    const top=head("GitHub"+(g.repo?" · "+esc(g.repo):g.account?" · "+esc(g.account):""),
      g.repo?T(`고른 저장소의 ${g.folder}/ 폴더만 씁니다.`,`HaslaLab only writes to the ${g.folder}/ folder of this repository.`):T("저장소와 폴더를 골라 주세요.","Choose a repository and a folder."),acts);
    if(!g.repo||S.gh.picking){
      const R=S.gh.repos;
      const manage=g.manage_url?`<a href="${esc(g.manage_url)}" target="_blank" rel="noopener noreferrer">${T("GitHub에서 설치에 저장소 추가","Add repositories to the installation on GitHub")}</a>`:"";
      if(!R)return top+`<p class="ws-note">${T("저장소 목록을 불러오는 중…","Loading repositories…")}</p>${msgLine()}`;
      return top+`<div class="ws-ccard"><h3>${T("저장소 고르기","Choose a repository")}</h3>
        <p>${T("설치할 때 고른 저장소만 보입니다. HaslaLab은 그 안의 한 폴더에만 파일을 씁니다.","Only the repositories you included in the installation appear. HaslaLab writes inside one folder only.")}</p>
        ${R.length?`<div class="ws-cform"><label for="wscRepo">${T("저장소","Repository")}</label><select id="wscRepo" data-wsc-repo>${R.map(r=>`<option value="${r.id}"${r.full_name===g.repo?" selected":""}>${esc(r.full_name)}${r.private?" 🔒":""}</option>`).join("")}</select>
          <label for="wscFolder">${T("폴더","Folder")}</label><input id="wscFolder" data-wsc-folder value="${esc(g.folder||"haslalab")}" maxlength="120" size="14">
          <button type="button" class="ws-btn pri" data-wsc-saverepo>${T("저장","Save")}</button>${g.repo?`<button type="button" class="ws-btn ghost" data-wsc-cancelrepo>${T("취소","Cancel")}</button>`:""}</div>`
          :`<p class="ws-cnote">${T("설치에 포함된 저장소가 없습니다.","No repository is included in the installation.")}</p>`}
        <p class="ws-cnote">${T("새 저장소가 필요하면 GitHub에서 먼저 만든 뒤 설치에 포함하세요.","Need a new repository? Create it on GitHub, then include it in the installation.")} ${manage}</p></div>${msgLine()}`;
    }
    const D=S.gh.data;
    if(!D)return top+`<p class="ws-note">${T("불러오는 중…","Loading…")}</p>${msgLine()}`;
    const segs=D.path?D.path.split("/"):[];
    const crumbs=`<nav class="ws-crumbs" aria-label="${T("폴더 위치","Folder")}">${[[ "",g.folder+"/"],...segs.map((s,i)=>[segs.slice(0,i+1).join("/"),s])].map(([p,n],i,a)=>i===a.length-1?`<b>${esc(n)}</b>`:`<button type="button" data-wsc-go="${esc(p)}">${esc(n)}</button><span aria-hidden="true">/</span>`).join("")}</nav>`;
    return top+`<div class="ws-tools">${crumbs}<span class="ws-acts">${upload()}</span></div>${importRow(T("GitHub로 복사","Copy to GitHub"))}${rows(D.files,"github")}
      <p class="ws-cnote">${T("올리기, 바꾸기, 지우기는 ‘HaslaLab: …’ 커밋으로 남습니다.","Uploads, updates and deletions appear as ‘HaslaLab: …’ commits.")}</p>${msgLine()}`;
  }
  const fail=e=>{S.msg=err(e?.code);if(e?.code==="drive_reconnect"||e?.code==="github_reconnect"||e?.code==="not_connected")refreshStatus();else paint();};
  async function refreshStatus(){try{S.status=await api("GET","");}catch(e){S.msg=err(e?.code);}paint();}
  async function storeFiles(){try{S.storeFiles=(await C.api("GET","/workshop/storage")).files||[];}catch(e){S.storeFiles=[];}}
  async function load(){
    if(S.tab==="drive"&&S.status?.drive?.connected){
      try{S.drive.data=await api("GET","/drive/files"+(S.drive.folder?"?folder="+encodeURIComponent(S.drive.folder):""));}catch(e){if(e?.code==="not_found"&&S.drive.folder){S.drive.folder="";return load();}return fail(e);}
      if(!S.storeFiles)await storeFiles();
    }
    if(S.tab==="github"&&S.status?.github?.connected){
      const g=S.status.github;
      if(!g.repo||S.gh.picking){try{S.gh.repos=(await api("GET","/github/repos")).repos;}catch(e){return fail(e);}}
      else{try{S.gh.data=await api("GET","/github/files"+(S.gh.path?"?path="+encodeURIComponent(S.gh.path):""));}catch(e){if(e?.code==="not_found"&&S.gh.path){S.gh.path="";return load();}return fail(e);}
        if(!S.storeFiles)await storeFiles();}
    }
    paint();
  }
  const save=(blob,name)=>{const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);};
  function wire(){
    const P=C.panel,q=s=>P.querySelectorAll(s),drive=S.tab==="drive";
    const run=async(fn,done)=>{if(S.busy)return;S.busy=true;try{await fn();S.msg=done||"";}catch(e){S.busy=false;return fail(e);}S.busy=false;await load();};
    q("[data-wsc-connect]").forEach(b=>b.onclick=async()=>{b.disabled=true;
      try{const {url}=await api("POST","/"+b.dataset.wscConnect+"/start",{return:location.origin+location.pathname});location.assign(url);}catch(e){b.disabled=false;fail(e);}});
    q("[data-wsc-off]").forEach(b=>b.onclick=async()=>{
      if(!confirm(T("연결을 끊을까요? 이미 옮긴 파일은 그대로 남습니다.","Disconnect? Files already copied stay where they are.")))return;
      try{const r=await api("DELETE","/"+b.dataset.wscOff);if(b.dataset.wscOff==="github")S.uninstall=r.manage_url||null;S.drive.data=null;S.gh.data=null;S.gh.repos=null;S.msg=T("연결을 끊었습니다.","Disconnected.");await refreshStatus();}catch(e){fail(e);}});
    q("[data-wsc-go]").forEach(b=>b.onclick=()=>{if(drive)S.drive.folder=b.dataset.wscGo;else S.gh.path=b.dataset.wscGo;S.msg="";load();});
    q("[data-wsc-down]").forEach(b=>b.onclick=async()=>{b.disabled=true;
      try{const r=await raw("GET",drive?"/drive/files/"+encodeURIComponent(b.dataset.wscDown):"/github/file?path="+encodeURIComponent(b.dataset.wscDown));save(await r.blob(),b.dataset.name);}catch(e){fail(e);}finally{b.disabled=false;}});
    q("[data-wsc-del]").forEach(b=>b.onclick=()=>{
      if(!confirm(drive?T(`‘${b.dataset.name}’을(를) 드라이브 휴지통으로 옮길까요?`,`Move “${b.dataset.name}” to the Drive trash?`):T(`‘${b.dataset.name}’을(를) 저장소에서 지울까요? 커밋으로 남습니다.`,`Delete “${b.dataset.name}” from the repository? A commit records it.`)))return;
      run(()=>drive?api("DELETE","/drive/files/"+encodeURIComponent(b.dataset.wscDel)):raw("DELETE","/github/file?path="+encodeURIComponent(b.dataset.wscDel)),T("지웠습니다.","Deleted."));});
    q("[data-wsc-rename]").forEach(b=>b.onclick=()=>{const old=b.dataset.name,v=prompt(T("새 이름","New name"),old.replace(/\.[^.]+$/,""));if(!v||!v.trim())return;
      run(()=>api("PATCH","/drive/files/"+encodeURIComponent(b.dataset.wscRename),{name:v.trim()+(old.includes(".")?"."+old.split(".").pop():"")}));});
    q("[data-wsc-tostore]").forEach(b=>b.onclick=()=>run(async()=>{
      await api("POST",drive?"/drive/copy":"/github/copy",drive?{direction:"to_storage",id:b.dataset.wscTostore,folder:""}:{direction:"to_storage",path:b.dataset.wscTostore,folder:""});
      S.storeFiles=null;C.reloadStore();},T("보관함 맨 위에 복사했습니다.","Copied to the top of your storage.")));
    q("[data-wsc-publish]").forEach(b=>b.onclick=()=>window.HL_WS_PUBLISH?.({
      file:{id:b.dataset.wscPublish,provider:drive?"drive":"github"},api:C.api,text:T,here:C.here,error:err
    }));
    P.querySelector("[data-wsc-import]")?.addEventListener("click",()=>{const id=P.querySelector("[data-wsc-pick]")?.value;if(!id)return;
      run(()=>api("POST",drive?"/drive/copy":"/github/copy",drive?{direction:"to_drive",file_id:id,folder:S.drive.folder||""}:{direction:"to_github",file_id:id,path:S.gh.path||""}),
        drive?T("드라이브로 복사했습니다.","Copied to Drive."):T("GitHub에 올렸습니다.","Committed to GitHub."));});
    P.querySelector("[data-wsc-newfolder]")?.addEventListener("click",()=>{const v=prompt(T("새 폴더 이름","New folder name"));if(!v||!v.trim())return;
      run(()=>api("POST","/drive/folders",{name:v.trim(),parent:S.drive.folder||""}));});
    P.querySelector("[data-wsc-file]")?.addEventListener("change",async e=>{
      const list=[...e.target.files];e.target.value="";if(!list.length)return;let done=0;
      for(const f of list){
        const ext=(f.name.split(".").pop()||"").toLowerCase();
        if(!TYPES.includes(ext)){S.msg=f.name+": "+err("type_not_allowed");continue;}
        if(f.size>20*1048576){S.msg=f.name+": "+err("file_too_large");continue;}
        S.msg=T("올리는 중… ","Uploading… ")+f.name;paint();
        const form=new FormData();form.append("file",f);if(drive)form.append("folder",S.drive.folder||"");else form.append("path",S.gh.path||"");
        try{await raw("POST",drive?"/drive/files":"/github/files",form);done++;S.msg="";}catch(x){S.msg=f.name+": "+err(x?.code);}
      }
      if(done&&!S.msg)S.msg=C.ko?`${done}개 파일을 올렸습니다.`:C.LX(`Uploaded ${done} file(s).`);
      load();
    });
    P.querySelector("[data-wsc-pickrepo]")?.addEventListener("click",()=>{S.gh.picking=true;S.gh.repos=null;paint();load();});
    P.querySelector("[data-wsc-cancelrepo]")?.addEventListener("click",()=>{S.gh.picking=false;paint();load();});
    P.querySelector("[data-wsc-saverepo]")?.addEventListener("click",async()=>{
      const id=+P.querySelector("[data-wsc-repo]").value,folder=P.querySelector("[data-wsc-folder]").value.trim();
      try{const r=await api("POST","/github/repo",{repo_id:id,folder});Object.assign(S.status.github,{repo:r.repo,folder:r.folder});S.gh.picking=false;S.gh.path="";S.gh.data=null;S.msg="";await load();}catch(e){fail(e);}
    });
  }
  async function mount(ctx){
    C=ctx;style();
    try{const t=sessionStorage.getItem("hlWsTab");if(["store","drive","github"].includes(t))S.tab=t;}catch(e){}
    const hp=new URLSearchParams(location.hash.split("?")[1]||""),prov=hp.get("connector"),ticket=hp.get("ticket"),e=hp.get("error");
    if(prov==="google"||prov==="github"){
      S.tab=prov==="google"?"drive":"github";
      try{history.replaceState(null,"","#/workshop/storage");}catch(x){}
      if(prov==="github"&&hp.get("resume")==="1"){
        /* GitHub came back from the install without our state: ask it for the authorization (once, not in a loop) */
        let last=0;try{last=+sessionStorage.getItem("hlWsResume")||0;sessionStorage.setItem("hlWsResume",String(Date.now()));}catch(x){}
        if(Date.now()-last>120000){try{const {url}=await api("POST","/github/start",{return:location.origin+location.pathname,authorize:true});location.assign(url);return;}catch(x){S.msg=err(x?.code);}}
        else S.msg=err("other");
      }
      if(ticket){
        S.msg=T("연결하는 중…","Connecting…");paint();
        try{await api("POST","/finish",{ticket});S.msg=prov==="google"?T("Google Drive를 연결했습니다.","Google Drive connected."):T("GitHub를 연결했습니다. 저장소를 골라 주세요.","GitHub connected. Choose a repository.");}
        catch(x){S.msg=err(x?.code);}
      }else if(e)S.msg=err(e);
    }
    paint();
    await refreshStatus();
    await load();
  }
  window.HL_WS_CONNECT={mount,_state:S};
})();
