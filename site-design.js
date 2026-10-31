/* Shared presentation; community data and authentication use the existing API. */
const SITE_DESIGN_TEXT = {
  ko: {recent:"커뮤니티 최신 글",updates:"공지 · 업데이트",more:"더보기",title:"제목",board:"게시판",date:"작성일",empty:"등록된 글이 없습니다.",notice:"공지",update:"업데이트",retry:"다시 불러오기",failed:"최신 글을 불러오지 못했습니다.",all:"전체",close:"닫기",pinned:"상단 고정",pin:"공지 상단 고정",unpin:"상단 고정 해제",loading:"공지를 불러오는 중…",noticeFailed:"공지를 불러오지 못했습니다.",loadMore:"이전 공지 더 보기",openPost:"게시글 열기",openArchive:"관련 페이지 열기",hint:"항목을 선택하면 내용을 펼쳐 볼 수 있습니다."},
  en: {recent:"Latest community posts",updates:"Notices & updates",more:"More",title:"Title",board:"Board",date:"Date",empty:"No posts yet.",notice:"Notice",update:"Update",retry:"Retry",failed:"Could not load the latest posts.",all:"All",close:"Close",pinned:"Pinned",pin:"Pin notice",unpin:"Unpin notice",loading:"Loading notices…",noticeFailed:"Could not load notices.",loadMore:"Load older notices",openPost:"Open post",openArchive:"Open related page",hint:"Select an item to expand and read it."}
};

/* Actual repository changes. Add new entries here when publishing archive updates. */
const SITE_UPDATES = [
  {date:"2026-10-31",ko:"IPhO 2011 실험 2 역학 블랙박스 3D 실험대",en:"IPhO 2011 Experiment 2: the mechanical blackbox bench in 3D",body:{ko:"IPhO 2011 실험 2를 문제지 사진대로 3D 실험대로 다시 만들었습니다. 책상에 고정한 투명 받침판의 핀, 균형용 실 고리, 구멍이 줄지은 알루미늄 원통, 자·연필·지우개, 초시계를 그대로 다룹니다. 실 고리 균형과 미끄러짐, 핀에 건 진자, 초시계 반응 시간은 기존 시뮬레이터와 같고, 공식 풀이대로 풀면 무게중심 17.8 cm, z ≈ 25.3 cm, M/m ≈ 2.7, g ≈ 9.78 m/s²가 나옵니다.",en:"IPhO 2011 Experiment 2 is rebuilt as a 3D bench after the photograph in the paper: the pin on the clear base plate clamped to the table, the thread loop for balancing, the aluminium tube with its row of holes, the ruler, pencil and rubber, and the stopwatch. The balancing loop, slipping, the pendulum on the pin and the reaction time on the stopwatch are those of the previous simulator; solved as in the official solution it gives x_CM = 17.8 cm, z ≈ 25.3 cm, M/m ≈ 2.7 and g ≈ 9.78 m/s²."},href:"#/ipho/2011"},
  {date:"2026-10-31",ko:"IPhO 2011 실험 1 전기 블랙박스 3D 실험대",en:"IPhO 2011 Experiment 1: the electrical blackbox bench in 3D",body:{ko:"IPhO 2011 실험 1을 문제지 사진대로 3D 실험대로 다시 만들었습니다. 나무 밑판 위의 9 V 건전지와 이완 발진기, 블랙박스와 미닫이 위 극판, mm 눈금, MASTECH 멀티미터, 표 1의 축전기를 직접 연결하고 읽습니다. 블랙박스는 이빨이 줄지은 빗살 극판의 실제 겹침으로 계산하며, 공식 해설의 f–x 표와 같은 모양이 나오고 풀이하면 α ≈ 714 nF/s, C_s ≈ 18 pF, 마디당 19.9 pF(b = 60 mm), 분해능 0.016 mm가 나옵니다.",en:"IPhO 2011 Experiment 1 is rebuilt as a 3D bench after the photographs in the paper: the 9 V battery and relaxation oscillator on the wooden base, the blackbox with its sliding upper plate over a millimetre scale, the MASTECH multimeter and the capacitors of Table 1, all wired and read by hand. The blackbox is computed from the real overlap of two toothed combs and follows the shape of the official f–x table; solved, it gives α ≈ 714 nF/s, C_s ≈ 18 pF, 19.9 pF per node (b = 60 mm) and a 0.016 mm resolution."},href:"#/ipho/2011"},
  {date:"2026-10-31",ko:"APhO 2023 실험 2 실제 열변형 광학 모형과 초점 링",en:"APhO 2023 Experiment 2: a real thermal-bump optics model and a focusing ring",body:{ko:"스크린의 간섭무늬를 가열된 PMMA 표면의 열변형에서 반사된 빔의 회절로 직접 계산합니다. 바깥쪽 고리가 가장 밝고 고리 간격이 바깥으로 갈수록 넓어지며, 초점을 맞춘 판에서 항복 전력 363.6 mW, 화면 거리 49.2 cm일 때 바깥 지름 27.5 cm 등 공식 결과가 나옵니다. 레이저 앞의 초점 링을 돌릴 수 있고, 초점이 어긋나면 무늬가 작아지고 항복 전력이 올라갑니다.",en:"The fringes are now computed as the diffraction of the beam reflected from the thermal bump on the heated PMMA surface. The outermost ring is the brightest and the rings open out towards the edge. In focus the plate gives the official results, such as a 363.6 mW yield power and a 27.5 cm outer diameter on a screen 49.2 cm away. The focusing ring at the front of the laser can be turned; out of focus the pattern shrinks and the yield power rises."},href:"#/apho/2023"},
  {date:"2026-10-31",ko:"IPhO 2019 실험 1 부품함 광학 소자와 소등 시간",en:"IPhO 2019 Experiment 1: optics from the tray and the blackout schedule",body:{ko:"회절격자 12C와 프리즘 12D를 부품함에서 꺼내 홀더 12B에 끼워 씁니다. 상단 시점 탭을 없애고 원판·스크린·자를 클릭하면 확대 화면이 열리며, 우클릭으로 부품함에 되돌리고 더블클릭으로 시점을 처음으로 돌립니다. 연습 모드에서는 조명을 마음대로 켜고 끌 수 있고, 실전 모드에서는 실제 시험처럼 정해진 소등 시간에만 어두워집니다. 실험 공간은 앞면이 열린 검은 암실 상자로 바꿨습니다. APhO 2023 실험 2의 판마다 다른 오차도 줄여 공식 값에 더 가깝게 나옵니다.",en:"Grating 12C and prism 12D now come from the tray and fit into holder 12B. The view tabs are gone: click the disk, screen or ruler for a close-up, right-click to put an item back, and double-click to reset the view. Practice mode has a free light switch; exam mode darkens the hall only during the real blackout. The bench sits in a black chamber open at the front. APhO 2023 Experiment 2 plates now vary less, so results sit closer to the official values."},href:"#/ipho/2019"},
  {date:"2026-10-31",ko:"APhO 2023 실험 1·2 배선 보드와 공유 컨트롤 박스",en:"APhO 2023 Experiments 1 and 2: wiring board and a shared control box",body:{ko:"컨트롤 박스의 옆면을 펼친 배선 보드에서 실제 플러그를 끌어 꽂을 수 있습니다. 오실로스코프에 전원 코드를 추가했고, 공을 끌어 전자석에 붙이거나 상자 스위치로 놓을 수 있습니다. 실전 모드에서는 두 실험이 컨트롤 박스 하나를 옮겨 가며 씁니다.",en:"Plugs are dragged into the control box on a board that opens its walls out flat. The oscilloscope has a mains cord, the ball can be dragged onto the magnet and released with the box switch, and in exam mode both experiments share one control box."},href:"#/apho/2023"},
  {date:"2026-10-31",ko:"IPhO 2019 실험 1 광학 측정 3D 실험실",en:"IPhO 2019 Experiment 1 optics lab in 3D",body:{ko:"IPhO 2019 실험 1을 다른 실험 시뮬레이터와 같은 3D 실험대로 다시 만들었습니다. 레이저 슬라이더, 각도기 원판, 회전 홀더, 회절격자·프리즘을 문제지 사진대로 만들었고, 광학 계산은 원본 시뮬레이터와 같습니다.",en:"IPhO 2019 Experiment 1 now runs on the same 3D bench as the other simulators. The laser slider, protractor disk, rotating holder, grating and prism follow the photographs in the problem paper, and the optics match the original simulator."},href:"#/ipho/2019"},
  {date:"2026-10-31",ko:"공지·업데이트 편지함과 공지 상단 고정",en:"Notice mailbox and pinned announcements",body:{ko:"홈의 공지·업데이트 ‘더보기’에서 전체 목록을 펼쳐 읽을 수 있습니다. 관리자는 공지 작성 버튼으로 새 공지를 등록하고 상단에 고정할 수 있습니다. 고정 공지는 홈 요약과 전체 목록에 먼저 표시됩니다.",en:"Open More in the home notice panel to read all announcements and updates without leaving the page. Admins can write and pin notices. Pinned notices appear first in the summary and full list."},href:"#/"},
  {date:"2026-10-31",ko:"랭킹 프로필 표시와 모바일 목록 개선",en:"Leaderboard profiles and mobile layout improved",body:{ko:"랭킹에서 프로필 사진과 닉네임을 더 읽기 쉽게 정리하고, 화면이 좁아도 사용자와 점수를 확인할 수 있게 개선했습니다.",en:"Leaderboard profile pictures and nicknames are easier to read, with user identities and scores kept visible on smaller screens."},href:"#/rank"},
  {date:"2026-10-31",ko:"AI 채점 0.3토큰 · 이론·실험 세트 0.5토큰",en:"AI grading: 0.3 tokens, theory + experiment set: 0.5",body:{ko:"AI 채점 비용을 단일 채점 0.3토큰, 이론·실험 세트 채점 0.5토큰으로 조정했습니다. 채점을 시작하기 전에 표시되는 비용을 확인할 수 있습니다.",en:"AI grading now costs 0.3 tokens for a single grading and 0.5 tokens for a theory + experiment set. The cost is shown before starting."},href:"#/lab"},
  {date:"2026-10-30",ko:"PLANCKS 국제 결선 2014~2026 기출 추가",en:"PLANCKS international finals 2014–2026 added",body:{ko:"PLANCKS 국제 결선의 2014~2026년 문제 자료를 연도별 기출에서 확인할 수 있습니다.",en:"Problem papers from the 2014–2026 PLANCKS international finals are available in the archive by year."},href:"#/plancks"},
  {date:"2026-10-30",ko:"Eötvös 기출·보고서 45개 연도로 확대",en:"Eötvös archive expanded to 45 years",body:{ko:"확인된 45개 연도의 문제와 보고서를 추가했습니다. 해설이 함께 있는 보고서와 일부 문제만 수록한 자료는 자료 설명에 구분해 표시합니다.",en:"Verified papers and reports now cover 45 years. Reports containing solutions and sources with only part of a year's problems are labelled in the archive."},href:"#/eotvos"},
  {date:"2026-10-30",ko:"중학생생물챌린지 공식 예시문항 추가",en:"Official MSKBO sample questions added",body:{ko:"중학생생물챌린지 대회 안내에서 공식 예시문항과 출처를 확인할 수 있습니다.",en:"The MSKBO page now links to official sample questions and their source."},href:"#/mskbo"},
  {date:"2026-10-30",ko:"AMC 8·10·12 문제·해설 130회차 추가",en:"130 AMC 8, 10 and 12 papers with solutions added",body:{ko:"AMC 8·10·12의 총 130회차 문제와 해설을 대회·연도별로 찾아볼 수 있습니다.",en:"Browse 130 AMC 8, 10 and 12 papers and their solutions by contest and year."},href:"#/amc"},
  {date:"2026-10-30",ko:"IZhO 2024 한국어 풀이 수식 보완",en:"Full equations restored in IZhO 2024 Korean solutions",body:{ko:"IZhO 2024 한국어 풀이에 누락되었던 수식을 보완했습니다. 해당 연도의 한국어 해설에서 확인할 수 있습니다.",en:"Missing equations in the IZhO 2024 Korean solutions have been restored. Open the year's Korean solution files to read the corrected version."},href:"#/izho/2024"},
  {date:"2026-10-30",ko:"RuPhO 단계 선택 화면 통합",en:"RuPhO stage selection unified",body:{ko:"RuPhO 대회 화면에서 연도와 단계를 함께 선택하고 해당 자료로 이동할 수 있게 정리했습니다.",en:"RuPhO year and stage selection are now available together on the competition page."},href:"#/rupho"},
  {date:"2026-10-30",ko:"CPhO 2006 한국어 · 영어 자료 추가",en:"CPhO 2006 papers added in Korean and English",body:{ko:"CPhO 2006년 자료에 한국어와 영어 버전을 추가했습니다. 연도별 자료의 언어 선택에서 열 수 있습니다.",en:"Korean and English versions of the CPhO 2006 papers are available through the year's paper language options."},href:"#/cpho/2006"},
  {date:"2026-10-30",ko:"커뮤니티 글쓴이 프로필 · 글과 댓글 조회",en:"Public community profiles and activity history",body:{ko:"커뮤니티의 글쓴이 이름을 선택하면 공개 프로필과 작성한 글·댓글을 모아 볼 수 있습니다.",en:"Select an author's name in the community to view their public profile, posts and comments."},href:"#/community"}
];

function paintSiteTheme(){
  const dark=document.documentElement.dataset.theme==="dark",button=document.getElementById("siteTheme");
  const label=lang==="ko"?(dark?"화이트 모드":"다크 모드"):(dark?"Light mode":"Dark mode");
  button.setAttribute("aria-label",label);button.setAttribute("title",label);button.setAttribute("aria-pressed",String(dark));button.textContent=dark?"☀":"◐";
  document.querySelector('meta[name="theme-color"]').content=dark?"#111017":"#2E3945";
  const icon=document.getElementById("siteFavicon"),href="favicon-"+(dark?"dark":"light")+".svg?v=20261030-logos";
  if(icon&&icon.getAttribute("href")!==href)icon.setAttribute("href",href);
  document.querySelectorAll("img[data-logo-key]").forEach(img=>{
    const src=logoSource(img.dataset.logoKey)+"?v="+LOGO_V;
    img.dataset.logoVariant=src.match(/\/(dark|light)\//)?.[1]||"original";
    if(img.getAttribute("src")!==src)img.setAttribute("src",src);
  });
}

function initSiteDesign(){
  document.getElementById("siteTheme").onclick=()=>{
    const theme=document.documentElement.dataset.theme==="dark"?"light":"dark";
    document.documentElement.dataset.theme=theme;
    try{localStorage.setItem("hlTheme",theme);}catch(e){}
    paintSiteTheme();
  };
}

function viewHome(){
  const T=SITE_DESIGN_TEXT[lang],original=document.createElement("div"),archive=document.createElement("div");
  original.innerHTML=viewOriginalHome();
  archive.innerHTML=viewComps(undefined,4);
  const experiment=original.querySelector("figure.screen").outerHTML;
  const homeText=original.querySelector(".hero > div").innerHTML;
  const subjects=archive.querySelector(".subjs").outerHTML,cards=archive.querySelector(".comps");
  const updateRows=SITE_UPDATES.slice(0,4).map(item=>`<a class="hl-update" href="${item.href}"><span class="hl-update-type">${T.update}</span><b>${esc(item[lang])}</b><time datetime="${item.date}">${item.date.slice(5).replace("-",".")}</time></a>`).join("");
  return `<div class="shell hl-home">
    <section class="hl-home-cover">${experiment}<div class="hl-cover-info">${homeText}</div></section>
    <div class="hl-dashboard"><section class="hl-panel"><div class="hl-panel-head"><h2>${T.recent}</h2><a href="#/community">${T.more} →</a></div><div id="homeLatest" aria-live="polite"><p class="hl-empty">${CMT[lang].loading}</p></div></section>
    <section class="hl-panel"><div class="hl-panel-head"><h2>${T.updates}</h2><div class="hl-panel-actions"><span id="homeNoticeWrite"></span><button type="button" class="hl-more" aria-haspopup="dialog" onclick="openSiteMailbox(this)">${T.more} →</button></div></div><div id="homeNotices"></div>${updateRows}</section></div>
    <section class="hl-home-archive"><div class="hl-section-head"><h2>${UI[lang].navComps}</h2><a href="#/comps">${T.more} →</a></div>${subjects}${cards.outerHTML}</section>
  </div>${adFitBanner("home")}`;
}

async function mountHomeActivity(){
  const latest=document.getElementById("homeLatest"),notices=document.getElementById("homeNotices"),current=lang,T=SITE_DESIGN_TEXT[lang];
  if(!latest||!notices)return;
  const alive=()=>lang===current&&document.getElementById("homeLatest")===latest;
  const paintWriter=()=>{const slot=document.getElementById('homeNoticeWrite');if(alive()&&slot)slot.innerHTML=siteNoticeWriteLink();};
  paintWriter();cmLoadMe().then(paintWriter).catch(()=>{});
  try{
    const result=await cmApi("GET","/posts?lang="+current+"&page=1");
    if(!alive())return;
    latest.innerHTML=result.posts.length?`<table class="hl-post-table"><thead><tr><th>${T.title}</th><th>${T.board}</th><th>${T.date}</th></tr></thead><tbody>${result.posts.slice(0,7).map(post=>`<tr><td><a href="#/community/post/${post.id}">${esc(post.title)}</a>${post.n_comments?` <span class="hl-comment-count">[${post.n_comments}]</span>`:""}</td><td>${esc(CMT[current].boards[post.board]||post.board)}</td><td><time>${cmShort(post.created_at)}</time></td></tr>`).join("")}</tbody></table>`:`<p class="hl-empty">${T.empty}</p>`;
    notices.innerHTML=(result.notices||[]).slice(0,2).map(post=>`<a class="hl-update" href="#/community/post/${post.id}"><span class="hl-update-type">${post.pinned?"⌖ "+T.pinned:T.notice}</span><b>${esc(post.title)}</b><time>${cmShort(post.created_at)}</time></a>`).join("");
  }catch(error){
    if(!alive())return;
    latest.innerHTML=`<p class="hl-empty">${T.failed} <button type="button" class="cmbtn sm">${T.retry}</button></p>`;
    latest.querySelector("button").onclick=mountHomeActivity;
  }
}

// A native modal keeps the current page in place and makes the background inert.
// Notice bodies remain escaped text, formatted exactly like community posts.
let siteMailboxState = null;
function siteNoticeWriteLink(){
  return cm.me?.role==='admin'?`<a class="cmbtn sm hl-notice-write" href="#/community/write/free?tag=notice">＋ ${lang==='ko'?'공지 작성':'Write a notice'}</a>`:'';
}
function siteMailboxRows(state){
  const T=SITE_DESIGN_TEXT[state.language],items=[];
  if(state.filter!=="updates")for(const post of state.posts)items.push({kind:"notice",id:String(post.id),at:post.created_at,pinned:!!post.pinned,post});
  if(state.filter!=="notices")SITE_UPDATES.forEach((item,index)=>items.push({kind:"update",id:String(index),at:Date.parse(item.date+"T00:00:00+09:00")/1000,pinned:false,item}));
  items.sort((a,b)=>Number(b.pinned)-Number(a.pinned)||b.at-a.at||(a.kind===b.kind?(a.kind==="notice"?Number(b.id)-Number(a.id):Number(a.id)-Number(b.id)):a.kind==="notice"?-1:1));
  return items.map(row=>{
    const notice=row.kind==="notice",post=row.post,item=row.item,key=row.kind+":"+row.id;
    const title=notice?post.title:item[state.language],date=notice?cmFull(post.created_at):item.date;
    return `<details class="hl-mail-item${row.pinned?" is-pinned":""}" data-mail-key="${key}"${state.expanded.has(key)?" open":""}>
      <summary><span class="hl-mail-kind">${notice?T.notice:T.update}</span><span class="hl-mail-title">${row.pinned?`<span class="hl-pin-badge">⌖ ${T.pinned}</span>`:""}${esc(title)}</span><time>${esc(date)}</time><span class="hl-mail-chevron" aria-hidden="true">⌄</span></summary>
      <div class="hl-mail-body">${notice?`<div class="hl-mail-copy">${cmFmt(post.body||"")}</div>`:`<p>${esc(item.body?.[state.language]||title)}</p>`}
        <div class="hl-mail-actions"><a class="cmbtn sm" href="${notice?"#/community/post/"+post.id:item.href}">${notice?T.openPost:T.openArchive} →</a>
        ${notice&&cm.me?.role==="admin"?`<button class="cmbtn sm" type="button" data-mail-pin="${post.id}" aria-pressed="${row.pinned}"${state.loading||state.pinning?" disabled":""}>${row.pinned?T.unpin:T.pin}</button>`:""}</div>
      </div></details>`;
  }).join("")||`<p class="hl-empty">${T.empty}</p>`;
}
function paintSiteMailbox(state){
  if(siteMailboxState!==state||!state.dialog.open)return;
  if(lang!==state.language){state.dialog.close();return;}
  const T=SITE_DESIGN_TEXT[state.language],dialog=state.dialog;
  const compose=dialog.querySelector('.hl-mail-compose');if(compose)compose.innerHTML=siteNoticeWriteLink();
  dialog.querySelector(".hl-mail-list").innerHTML=siteMailboxRows(state);
  dialog.querySelectorAll("[data-mail-filter]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.mailFilter===state.filter)));
  const status=dialog.querySelector(".hl-mail-status"),more=dialog.querySelector(".hl-mail-more");
  status.innerHTML=state.error?`${T.noticeFailed} <button type="button" class="cmbtn sm" data-mail-retry>${T.retry}</button>`:state.loading?T.loading:"";
  more.hidden=state.filter==="updates"||state.posts.length>=state.total||!!state.error;
  more.disabled=state.loading;more.textContent=T.loadMore;
  dialog.querySelectorAll("[data-mail-key]").forEach(details=>details.ontoggle=()=>{
    if(details.open)state.expanded.add(details.dataset.mailKey);else state.expanded.delete(details.dataset.mailKey);
  });
  const retry=dialog.querySelector("[data-mail-retry]");if(retry)retry.onclick=()=>loadSiteMailboxNotices(state);
  dialog.querySelectorAll("[data-mail-pin]").forEach(button=>button.onclick=async()=>{
    const post=state.posts.find(item=>item.id===Number(button.dataset.mailPin));if(!post)return;
    if(state.loading||state.pinning)return;state.pinning=true;paintSiteMailbox(state);
    try{
      const result=await cmApi("PATCH",`/posts/${post.id}/pin`,{pinned:!post.pinned});
      if(siteMailboxState!==state||lang!==state.language)return;
      post.pinned=result.pinned;state.posts=[];state.page=1;state.total=Infinity;state.pinning=false;
      await loadSiteMailboxNotices(state);
      dialog.querySelector(`[data-mail-pin="${post.id}"]`)?.focus();
      if(document.getElementById("homeLatest"))mountHomeActivity();
    }catch(error){if(siteMailboxState===state){state.pinning=false;paintSiteMailbox(state);cmToast(cmErr(error));}}
  });
}
async function loadSiteMailboxNotices(state){
  if(state.loading||siteMailboxState!==state)return;
  state.loading=true;state.error=false;paintSiteMailbox(state);
  try{
    const result=await cmApi("GET",`/posts?notices=1&lang=${state.language}&page=${state.page}`);
    if(siteMailboxState!==state||lang!==state.language)return;
    const seen=new Set(state.posts.map(post=>post.id));
    state.posts.push(...result.posts.filter(post=>!seen.has(post.id)));
    state.total=result.total;state.page++;
  }catch(error){if(siteMailboxState===state)state.error=true;}
  finally{state.loading=false;paintSiteMailbox(state);}
}
function openSiteMailbox(trigger){
  if(siteMailboxState?.dialog.open){siteMailboxState.dialog.querySelector(".hl-mail-close").focus();return;}
  const T=SITE_DESIGN_TEXT[lang],dialog=document.createElement("dialog"),previousOverflow=document.body.style.overflow;
  dialog.className="hl-mailbox";dialog.setAttribute("aria-labelledby","hlMailboxTitle");dialog.setAttribute("aria-describedby","hlMailboxHint");
  dialog.innerHTML=`<div class="hl-mail-head"><div><h2 id="hlMailboxTitle">${T.updates}</h2><p id="hlMailboxHint">${T.hint}</p></div><div class="hl-mail-head-actions"><span class="hl-mail-compose"></span><button type="button" class="hl-mail-close" aria-label="${T.close}" autofocus>×</button></div></div>
    <div class="hl-mail-tabs" role="group" aria-label="${T.updates}">${[["all",T.all],["notices",T.notice],["updates",T.update]].map(([key,label])=>`<button type="button" data-mail-filter="${key}" aria-pressed="${key==="all"}">${label}</button>`).join("")}</div>
    <div class="hl-mail-scroll"><div class="hl-mail-list"></div><p class="hl-mail-status" role="status" aria-live="polite"></p><button class="cmbtn hl-mail-more" type="button" hidden>${T.loadMore}</button></div>`;
  const state={dialog,language:lang,posts:[],page:1,total:Infinity,loading:false,error:false,filter:"all",expanded:new Set()};siteMailboxState=state;
  document.body.append(dialog);
  dialog.addEventListener("close",()=>{
    if(siteMailboxState===state)siteMailboxState=null;
    document.body.style.overflow=previousOverflow;dialog.remove();
    if(trigger?.isConnected)trigger.focus();
  },{once:true});
  dialog.querySelector(".hl-mail-close").onclick=()=>dialog.close();
  dialog.querySelector(".hl-mail-more").onclick=()=>loadSiteMailboxNotices(state);
  dialog.querySelectorAll("[data-mail-filter]").forEach(button=>button.onclick=()=>{state.filter=button.dataset.mailFilter;paintSiteMailbox(state);});
  dialog.addEventListener("click",event=>{if(event.target.closest?.('a[href^="#/"]'))dialog.close();});
  dialog.showModal();document.body.style.overflow="hidden";
  paintSiteMailbox(state);loadSiteMailboxNotices(state);
  cmLoadMe().then(()=>paintSiteMailbox(state)).catch(()=>{});
}
