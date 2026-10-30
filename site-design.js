/* Shared presentation only; account, community and archive behavior stays in its existing modules. */
const SITE_DESIGN_TEXT = {
  ko: {recent:"커뮤니티 최신 글",updates:"공지 · 업데이트",more:"더보기",title:"제목",board:"게시판",date:"작성일",empty:"등록된 글이 없습니다.",notice:"공지",update:"업데이트",retry:"다시 불러오기",failed:"최신 글을 불러오지 못했습니다."},
  en: {recent:"Latest community posts",updates:"Notices & updates",more:"More",title:"Title",board:"Board",date:"Date",empty:"No posts yet.",notice:"Notice",update:"Update",retry:"Retry",failed:"Could not load the latest posts."}
};

/* Actual repository changes. Add new entries here when publishing archive updates. */
const SITE_UPDATES = [
  {date:"2026-10-30",ko:"IZhO 2024 한국어 풀이 수식 보완",en:"Full equations restored in IZhO 2024 Korean solutions",href:"#/izho/2024"},
  {date:"2026-10-30",ko:"RuPhO 단계 선택 화면 통합",en:"RuPhO stage selection unified",href:"#/rupho"},
  {date:"2026-10-30",ko:"CPhO 2006 한국어 · 영어 자료 추가",en:"CPhO 2006 papers added in Korean and English",href:"#/cpho/2006"},
  {date:"2026-10-30",ko:"커뮤니티 글쓴이 프로필 · 글과 댓글 조회",en:"Public community profiles and activity history",href:"#/community"}
];

function paintSiteTheme(){
  const dark=document.documentElement.dataset.theme==="dark",button=document.getElementById("siteTheme");
  const label=lang==="ko"?(dark?"화이트 모드":"다크 모드"):(dark?"Light mode":"Dark mode");
  button.setAttribute("aria-label",label);button.setAttribute("title",label);button.setAttribute("aria-pressed",String(dark));button.textContent=dark?"☀":"◐";
  document.querySelector('meta[name="theme-color"]').content=dark?"#111017":"#2E3945";
  const icon=document.getElementById("siteFavicon"),href="favicon-"+(dark?"dark":"light")+".svg?v=20261030-logos";
  if(icon&&icon.getAttribute("href")!==href)icon.setAttribute("href",href);
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
  archive.innerHTML=viewComps();
  const experiment=original.querySelector("figure.screen").outerHTML;
  const homeText=original.querySelector(".hero > div").innerHTML;
  const subjects=archive.querySelector(".subjs").outerHTML,cards=archive.querySelector(".comps");
  [...cards.children].slice(4).forEach(node=>node.remove());
  const updateRows=SITE_UPDATES.map(item=>`<a class="hl-update" href="${item.href}"><span class="hl-update-type">${T.update}</span><b>${esc(item[lang])}</b><time datetime="${item.date}">${item.date.slice(5).replace("-",".")}</time></a>`).join("");
  return `<div class="shell hl-home">
    <section class="hl-home-cover">${experiment}<div class="hl-cover-info">${homeText}</div></section>
    <div class="hl-dashboard"><section class="hl-panel"><div class="hl-panel-head"><h2>${T.recent}</h2><a href="#/community">${T.more} →</a></div><div id="homeLatest" aria-live="polite"><p class="hl-empty">${CMT[lang].loading}</p></div></section>
    <section class="hl-panel"><div class="hl-panel-head"><h2>${T.updates}</h2><a href="#/community">${T.more} →</a></div><div id="homeNotices"></div>${updateRows}</section></div>
    <section class="hl-home-archive"><div class="hl-section-head"><h2>${UI[lang].navComps}</h2><a href="#/comps">${T.more} →</a></div>${subjects}${cards.outerHTML}</section>
  </div>${adFitBanner("home")}`;
}

async function mountHomeActivity(){
  const latest=document.getElementById("homeLatest"),notices=document.getElementById("homeNotices"),current=lang,T=SITE_DESIGN_TEXT[lang];
  if(!latest||!notices)return;
  const alive=()=>lang===current&&document.getElementById("homeLatest")===latest;
  try{
    const result=await cmApi("GET","/posts?lang="+current+"&page=1");
    if(!alive())return;
    latest.innerHTML=result.posts.length?`<table class="hl-post-table"><thead><tr><th>${T.title}</th><th>${T.board}</th><th>${T.date}</th></tr></thead><tbody>${result.posts.slice(0,7).map(post=>`<tr><td><a href="#/community/post/${post.id}">${esc(post.title)}</a>${post.n_comments?` <span class="hl-comment-count">[${post.n_comments}]</span>`:""}</td><td>${esc(CMT[current].boards[post.board]||post.board)}</td><td><time>${cmShort(post.created_at)}</time></td></tr>`).join("")}</tbody></table>`:`<p class="hl-empty">${T.empty}</p>`;
    notices.innerHTML=(result.notices||[]).slice(0,2).map(post=>`<a class="hl-update" href="#/community/post/${post.id}"><span class="hl-update-type">${T.notice}</span><b>${esc(post.title)}</b><time>${cmShort(post.created_at)}</time></a>`).join("");
  }catch(error){
    if(!alive())return;
    latest.innerHTML=`<p class="hl-empty">${T.failed} <button type="button" class="cmbtn sm">${T.retry}</button></p>`;
    latest.querySelector("button").onclick=mountHomeActivity;
  }
}
