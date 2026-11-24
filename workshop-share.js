/* 작품 공유 · Showcase (#/workshop/share): the Workshop's sharing place, drawn by this file into the shell index.html's
   viewWorkshopShare() returns, with the API of community/src/workshop-share.js. Three pages:
     #/workshop/share                 explore: this week's favourites, tabs (popular, new, staff picks, by topic), type
                                      filters, search, sort, a grid of project cards loaded page by page
     #/workshop/share/<id>            a project: it runs (a simulation in sim-sandbox.html, an opaque-origin frame; a
                                      Python problem in create.html's play view; a figure as an image; a problem set as a
                                      list), its description, how to use it, notes and credits, tags, likes, favourites,
                                      views, the share link, remixes (the original and the list), report and comments
     #/workshop/share/user/<id>       an author's shared projects
   Nothing a member wrote is put into the page as markup: text is escaped (descriptions get a small markdown subset
   after escaping), thumbnails are <img> from the API (an SVG thumbnail passed the server's check and, as an image,
   cannot run anything), and a figure is drawn by the site's own draw-render.mjs into an <img>. */
(function(){
  'use strict';
  let C=null,stopSim=null,observer=null;
  const T=(ko,en)=>C.ko?ko:C.LX(en);
  const esc=s=>C.esc(s==null?'':String(s));
  const TOPICS=['mechanics','em','thermal','optics','waves','modern','other'];
  const TOPIC_NAMES={mechanics:['역학','Mechanics'],em:['전자기','Electromagnetism'],thermal:['열','Heat'],optics:['광학','Optics'],waves:['파동','Waves'],modern:['현대물리','Modern physics'],other:['기타','Other']};
  const TYPE_NAMES={sim:['시뮬레이션','Simulation'],python:['전산물리(Python)','Computational (Python)'],figure:['그림','Figure'],set:['문제 세트','Problem set']};
  const TABS=[['popular','인기','Popular'],['new','최신','New'],['featured','추천','Staff picks'],['topic','주제별','By topic']];
  const SORTS=[['popular','인기순','Most popular'],['new','최신순','Newest'],['likes','좋아요순','Most liked'],['views','조회순','Most viewed'],['remixes','리믹스순','Most remixed']];
  const topicName=k=>T(...(TOPIC_NAMES[k]||TOPIC_NAMES.other));
  const typeName=k=>T(...(TYPE_NAMES[k]||TYPE_NAMES.sim));
  const ERR={login_required:['로그인하세요.','Sign in first.'],rate_limited:['잠시 뒤에 다시 시도해 주세요.','Try again in a moment.'],not_found:['찾을 수 없는 작품입니다. 공유가 취소되었거나 숨겨졌습니다.','This project is not here. It was unshared or hidden.'],
    not_owner:['만든 사람만 할 수 있습니다.','Only the author can do this.'],forbidden:['권한이 없습니다.','Not allowed.'],bad_body:['댓글을 입력해 주세요. 2,000자까지 씁니다.','Write a comment (up to 2,000 characters).'],
    bad_title:['제목을 입력해 주세요. 80자까지 씁니다.','Enter a title (up to 80 characters).'],bad_tags:['태그는 8개, 하나에 20자까지입니다.','Up to 8 tags of 20 characters each.'],bad_reason:['신고 이유를 적어 주세요.','Say why you are reporting it.'],
    network:['연결에 실패했습니다.','Could not connect.'],other:['처리하지 못했습니다.','Something went wrong.']};
  const err=e=>{const x=ERR[e?.code]||ERR.other;return T(x[0],x[1]);};
  const api=(m,p,b)=>C.api(m,p,b);
  const nf=n=>{n=+n||0;return n>=10000?(n/1000).toFixed(n>=100000?0:1)+'k':n.toLocaleString(C.ko?'ko-KR':'en-US');};
  const day=t=>{if(!t)return '';const d=new Date(t*1000);return `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')}`;};
  const b64=s=>{const b=new TextEncoder().encode(s);let bin='';for(let i=0;i<b.length;i+=0x8000)bin+=String.fromCharCode(...b.subarray(i,i+0x8000));return btoa(bin);};
  const thumbUrl=it=>`${C.base()}/api/share/${+it.id}/thumb?v=${+it.updated_at||0}`;

  /* small line icons of HaslaLab's own (stroke = currentColor) */
  const I={heart:'<path d="M10 16.5s-6-3.7-6-8A3.4 3.4 0 0 1 10 6a3.4 3.4 0 0 1 6 2.5c0 4.3-6 8-6 8z"/>',star:'<path d="M10 3.2l2 4.3 4.6.5-3.4 3.1 1 4.6L10 13.4l-4.2 2.3 1-4.6L3.4 8l4.6-.5z"/>',
    eye:'<path d="M2.5 10S5.2 5 10 5s7.5 5 7.5 5-2.7 5-7.5 5-7.5-5-7.5-5z"/><circle cx="10" cy="10" r="2.2"/>',remix:'<path d="M5 4v5a3 3 0 0 0 3 3h7"/><path d="M12 9l3 3-3 3"/><circle cx="5" cy="4" r="1.4"/>',
    link:'<path d="M8.5 11.5l3-3"/><path d="M7 9.5L5.6 11a2.5 2.5 0 0 0 3.5 3.5l1.4-1.5"/><path d="M13 10.5l1.4-1.5A2.5 2.5 0 0 0 10.9 5.5L9.5 7"/>',
    flag:'<path d="M5 17V3.5"/><path d="M5 4h9l-2 3 2 3H5"/>',code:'<path d="M7 6l-4 4 4 4"/><path d="M13 6l4 4-4 4"/>',chat:'<path d="M4 5h12v8H9l-4 3v-3H4z"/>',
    search:'<circle cx="9" cy="9" r="5"/><path d="M13 13l4 4"/>',edit:'<path d="M4 16l1-4 8-8 3 3-8 8z"/>'};
  const icon=(k,cls='')=>`<svg class="shr-i ${cls}" viewBox="0 0 20 20" aria-hidden="true">${I[k]}</svg>`;
  /* the placeholder picture of a project with no thumbnail: a tinted panel with the type's mark */
  const ART={sim:'<circle cx="60" cy="40" r="22" fill="none" stroke-dasharray="3 4"/><line x1="60" y1="12" x2="76" y2="34"/><circle cx="76" cy="34" r="6" class="f"/><path d="M28 64h64"/>',
    python:'<path d="M44 26l-14 14 14 14M76 26l14 14-14 14M66 22l-12 36"/>',figure:'<path d="M26 62L94 62 94 22z" fill="none"/><rect x="58" y="34" width="16" height="12" transform="rotate(-30 66 40)" class="f"/><path d="M80 62a14 14 0 0 0-3-9"/>',
    set:'<rect x="34" y="16" width="52" height="50" rx="5" fill="none"/><path d="M44 30h32M44 41h32M44 52h20"/>'};
  const art=type=>`<svg class="shr-art t-${esc(type)}" viewBox="0 0 120 80" aria-hidden="true">${ART[type]||ART.sim}</svg>`;

  /* descriptions: plain text with a little markdown, escaped first, so nothing a member wrote becomes markup */
  function md(s){
    const inline=x=>x.replace(/`([^`\n]{1,200})`/g,'<code>$1</code>').replace(/\*\*([^*\n]{1,300})\*\*/g,'<strong>$1</strong>')
      .replace(/\bhttps:\/\/[^\s<>"]{3,300}/g,u=>`<a href="${u}" target="_blank" rel="nofollow noopener noreferrer ugc">${u}</a>`);
    return esc(s||'').split(/\n{2,}/).map(block=>{
      const lines=block.split('\n');
      if(lines.every(l=>/^\s*[-•]\s+/.test(l)))return `<ul>${lines.map(l=>`<li>${inline(l.replace(/^\s*[-•]\s+/,''))}</li>`).join('')}</ul>`;
      return `<p>${lines.map(inline).join('<br>')}</p>`;
    }).join('');
  }
  function style(){
    if(document.getElementById('shrStyle'))return;
    const s=document.createElement('style');s.id='shrStyle';
    s.textContent=`.shr{--sh-ink:#263247;--sh-mute:#657187;--sh-line:#d5dbe6;--sh-soft:#f4f1fa;--sh-acc:#7059a4;--sh-acc2:#5c438f;--sh-card:#fff;--sh-bg2:#f7f8fb;max-width:1120px}
.shr [hidden]{display:none!important}.shr .phead h1{margin-bottom:4px}.shr .shr-top{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;justify-content:space-between;margin:6px 0 18px}
.shr-search{display:flex;align-items:center;gap:6px;flex:1 1 320px;max-width:520px;border:1px solid var(--sh-line);border-radius:999px;padding:4px 6px 4px 12px;background:var(--sh-card)}
.shr-search input{flex:1;min-width:0;border:0;background:transparent;font:14px var(--sans);color:var(--sh-ink);padding:5px 0;outline:none}.shr-search:focus-within{border-color:var(--sh-acc)}
.shr-search button{border:0;background:var(--sh-acc2);color:#fff;border-radius:999px;padding:6px 14px;font:600 13px var(--sans);cursor:pointer}
.shr-me{display:flex;gap:8px;flex-wrap:wrap}.shr-me a{font:600 13.5px var(--sans);color:var(--sh-acc2);text-decoration:none;border:1px solid var(--sh-line);border-radius:999px;padding:6px 12px;background:var(--sh-card)}.shr-me a:hover{border-color:var(--sh-acc)}
.shr h2{font-size:17px;margin:0 0 10px;color:var(--sh-ink)}.shr-week{margin:0 0 22px}
.shr-row{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(210px,232px);gap:12px;overflow-x:auto;padding:2px 2px 10px;scroll-snap-type:x proximity}.shr-row>*{scroll-snap-align:start}
.shr-tabs{display:flex;gap:4px;border-bottom:1px solid var(--sh-line);margin:0 0 12px;overflow-x:auto}
.shr-tabs button{background:none;border:0;border-bottom:2px solid transparent;padding:9px 14px;font:600 14.5px var(--sans);color:var(--sh-mute);cursor:pointer;white-space:nowrap}
.shr-tabs button[aria-selected="true"]{color:var(--sh-acc2);border-bottom-color:var(--sh-acc)}
.shr-filters{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;justify-content:space-between;margin:0 0 14px}
.shr-chips{display:flex;flex-wrap:wrap;gap:6px}.shr-chips button{border:1px solid var(--sh-line);background:var(--sh-card);color:var(--sh-ink);border-radius:999px;padding:5px 12px;font:13px var(--sans);cursor:pointer}
.shr-chips button[aria-pressed="true"]{background:var(--sh-soft);border-color:var(--sh-acc);color:var(--sh-acc2);font-weight:600}
.shr-sort{font:13px var(--sans);color:var(--sh-mute);display:flex;gap:6px;align-items:center}.shr-sort select{font:13px var(--sans);padding:5px 8px;border:1px solid var(--sh-line);border-radius:8px;background:var(--sh-card);color:var(--sh-ink)}
.shr-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
.shr-card{display:flex;flex-direction:column;border:1px solid var(--sh-line);border-radius:14px;background:var(--sh-card);color:var(--sh-ink);text-decoration:none;overflow:hidden;transition:border-color .15s,transform .15s}
.shr-card:hover{border-color:var(--sh-acc);transform:translateY(-1px)}.shr-card:focus-visible{outline:2px solid var(--sh-acc);outline-offset:2px}
.shr-thumb{position:relative;aspect-ratio:3/2;background:linear-gradient(135deg,#f4f1fa,#eef3f9);display:grid;place-items:center;border-bottom:1px solid var(--sh-line)}
.shr-thumb img{width:100%;height:100%;object-fit:contain;background:#fff}.shr-art{width:62%;height:auto;stroke:#8d78bf;stroke-width:2.4;fill:none;stroke-linecap:round;stroke-linejoin:round}.shr-art .f{fill:#d9cff0}
.shr-badge{position:absolute;left:8px;top:8px;font:600 11.5px var(--sans);color:var(--sh-acc2);background:rgba(255,255,255,.92);border:1px solid #e3dcf2;border-radius:6px;padding:1px 7px}
.shr-pick{position:absolute;right:8px;top:8px;font:600 11.5px var(--sans);color:#7a5a10;background:#fff4d6;border:1px solid #f0d9a8;border-radius:6px;padding:1px 7px}
.shr-body{display:grid;gap:6px;padding:10px 12px 12px}.shr-title{font-weight:700;font-size:14.5px;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.7em}
.shr-by{display:flex;align-items:center;gap:7px;font-size:12.5px;color:var(--sh-mute);min-width:0}.shr-by span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.shr-by .cmav{width:22px;height:22px;font-size:11px;flex:none}
.shr-stats{display:flex;gap:12px;font-size:12.5px;color:var(--sh-mute)}.shr-stats span{display:inline-flex;align-items:center;gap:3px}
.shr-i{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round;flex:none}
.shr-more{display:flex;justify-content:center;margin:18px 0 6px}.shr-empty{padding:28px 14px;text-align:center;color:var(--sh-mute);border:1px dashed var(--sh-line);border-radius:14px}
.shr-how{margin:26px 0 4px;padding:12px 14px;border-radius:12px;background:var(--sh-bg2);font-size:13.5px;color:var(--sh-mute);line-height:1.6}
.shr-proj{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:20px;align-items:start}
.shr-stage{border:1px solid var(--sh-line);border-radius:14px;background:var(--sh-card);padding:12px;min-height:240px}
.shr-stage iframe{display:block;width:100%;height:460px;border:0;background:transparent}.shr-stage .shr-fig{display:block;max-width:100%;height:auto;margin:0 auto;background:#fff;border-radius:8px}
.shr-side{display:grid;gap:12px}.shr-panel{border:1px solid var(--sh-line);border-radius:14px;background:var(--sh-card);padding:14px}
.shr-panel h1{font-size:21px;line-height:1.3;margin:6px 0 8px}.shr-panel .shr-by{font-size:13.5px}.shr-panel .shr-by a{color:var(--sh-ink);font-weight:600;text-decoration:none}
.shr-meta{font-size:12.5px;color:var(--sh-mute);margin:8px 0 0}
.shr-acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.shr-btn{display:inline-flex;align-items:center;gap:6px;padding:7px 12px;border-radius:9px;border:1px solid var(--sh-line);background:var(--sh-card);color:var(--sh-ink);font:600 13px var(--sans);cursor:pointer;text-decoration:none;white-space:nowrap}
.shr-btn:hover{border-color:var(--sh-acc)}.shr-btn.on{background:var(--sh-soft);border-color:var(--sh-acc);color:var(--sh-acc2)}.shr-btn.on .shr-i{fill:currentColor}
.shr-btn.pri{background:var(--sh-acc2);border-color:var(--sh-acc2);color:#fff}.shr-btn.pri:hover{background:#4a3575}.shr-btn.quiet{border-color:transparent;background:transparent;color:var(--sh-mute)}
.shr-sec{margin:18px 0 0}.shr-sec h2{font-size:15.5px;margin:0 0 6px}.shr-text{font-size:14.5px;line-height:1.7;color:#3d4759}.shr-text p{margin:0 0 8px}.shr-text ul{margin:0 0 8px;padding-left:20px}
.shr-text code,.shr-code{font:12.5px/1.5 ui-monospace,Menlo,Consolas,monospace;background:var(--sh-bg2);border-radius:5px;padding:1px 4px}
.shr-code{display:block;white-space:pre;overflow:auto;max-height:420px;padding:12px;border:1px solid var(--sh-line);margin-top:10px}
.shr-tags{display:flex;flex-wrap:wrap;gap:6px}.shr-tags a{font-size:12.5px;color:var(--sh-acc2);background:var(--sh-soft);border-radius:999px;padding:3px 10px;text-decoration:none}
.shr-origin{font-size:13.5px;padding:9px 12px;border-left:3px solid var(--sh-acc);background:var(--sh-bg2);border-radius:0 10px 10px 0;margin:12px 0 0}.shr-origin a{color:var(--sh-acc2);font-weight:600}
.shr-q{margin-top:12px;padding:12px;border-radius:12px;background:var(--sh-bg2);font-size:14px}
.shr-set{list-style:none;margin:0;padding:0;counter-reset:q}.shr-set li{counter-increment:q;padding:12px 2px;border-bottom:1px solid #edf0f5;font-size:14.5px;line-height:1.65}
.shr-set li::before{content:counter(q) ". ";font-weight:700;color:var(--sh-acc2)}.shr-set .shr-ch{margin:6px 0 0 18px;padding:0;color:#3d4759}.shr-set img{max-width:100%;height:auto;display:block;margin:8px 0}
.shr-cmts{list-style:none;margin:0;padding:0}.shr-cmt{display:grid;grid-template-columns:32px minmax(0,1fr);gap:10px;padding:12px 0;border-bottom:1px solid #edf0f5}
.shr-cmt.re{margin-left:42px}.shr-cmt .cmav{width:32px;height:32px}.shr-cmt b{font-size:13.5px}.shr-cmt time{font-size:12px;color:var(--sh-mute);margin-left:6px}
.shr-cmt p{margin:3px 0 4px;font-size:14px;line-height:1.6;white-space:pre-wrap;overflow-wrap:anywhere}.shr-cmt .shr-cacts button{background:none;border:0;padding:2px 8px 2px 0;font:12.5px var(--sans);color:var(--sh-mute);cursor:pointer}
.shr-form{display:grid;gap:8px;margin:8px 0 4px}.shr-form textarea,.shr-form input,.shr-form select{font:14px var(--sans);padding:8px 10px;border:1px solid var(--sh-line);border-radius:10px;background:var(--sh-card);color:var(--sh-ink);width:100%;box-sizing:border-box}
.shr-form textarea{min-height:76px;resize:vertical}.shr-form label{font-size:13px;color:var(--sh-mute);display:grid;gap:4px}.shr-form .shr-row2{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap}
.shr-msg{font-size:13px;color:#a32f46;min-height:1em;margin:4px 0}.shr-ok{color:#2f7a56}
.shr-user{display:flex;gap:14px;align-items:center;margin:4px 0 18px}.shr-user .cmav{width:56px;height:56px;font-size:24px}.shr-user h1{margin:0}.shr-user p{margin:2px 0 0;color:var(--sh-mute);font-size:13.5px}
@media(max-width:900px){.shr-proj{grid-template-columns:minmax(0,1fr)}.shr-stage iframe{height:440px}}
@media(max-width:560px){.shr-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.shr-body{padding:8px 9px 10px}.shr-title{font-size:13.5px}.shr-stats{gap:8px;font-size:11.5px}.shr-row{grid-auto-columns:minmax(168px,180px)}.shr-cmt.re{margin-left:20px}.shr-search{flex-basis:100%}}
html[data-theme="dark"] .shr{--sh-ink:#ebe8f5;--sh-mute:#aca6bd;--sh-line:#3b344d;--sh-soft:#30243f;--sh-acc:#bca0ed;--sh-acc2:#cfbdf2;--sh-card:#1b1824;--sh-bg2:#211d2b}
html[data-theme="dark"] .shr .shr-thumb{background:linear-gradient(135deg,#2a2238,#1f2430)}html[data-theme="dark"] .shr .shr-art{stroke:#bca0ed}html[data-theme="dark"] .shr .shr-art .f{fill:#4a3a68}
html[data-theme="dark"] .shr .shr-text,html[data-theme="dark"] .shr .shr-set .shr-ch{color:#d6d1e4}html[data-theme="dark"] .shr .shr-btn.pri,html[data-theme="dark"] .shr .shr-search button{background:#7059a4;border-color:#7059a4;color:#fff}
html[data-theme="dark"] .shr .shr-badge{background:rgba(27,24,36,.9);border-color:#4a3a68}html[data-theme="dark"] .shr :is(.shr-cmt,.shr-set li){border-color:#2f2a3d}`;
    document.head.append(s);
  }

  /* ── routes ── */
  function route(){
    const [path,qs]=location.hash.replace(/^#\/?/,'').split('?'),parts=path.split('/').filter(Boolean).slice(2);
    const q=new URLSearchParams(qs||'');
    if(parts[0]==='user'&&/^\d{1,9}$/.test(parts[1]||''))return {page:'user',id:+parts[1],q};
    if(/^\d{1,9}$/.test(parts[0]||''))return {page:'project',id:+parts[0],q};
    return {page:'explore',q};
  }
  const crumbs=extra=>`<p class="eyebrow"><a href="#/workshop">${esc(C.workshop)}</a> / ${extra?`<a href="#/workshop/share">${esc(C.title)}</a> / ${extra}`:esc(C.title)}</p>`;
  function view(ctx){
    C=ctx;const r=route();
    if(r.page!=='explore')return `<div class="shell ws shr" id="shrRoot"><div class="phead">${crumbs('…')}</div><p class="ws-note" role="status">${T('불러오는 중…','Loading…')}</p></div>`;
    return `<div class="shell ws shr" id="shrRoot"><div class="phead">${crumbs()}<h1>${esc(C.title)}</h1>
      <p class="learn-tool-copy">${T('회원들이 워크샵에서 만든 시뮬레이션, 전산물리 문제, 그림, 문제 세트를 실행해 보고, 마음에 들면 리믹스해서 내 것으로 고쳐 씁니다.','Run the simulations, computational problems, figures and problem sets members made in the Workshop, and remix one to make it your own.')}</p></div>
      <div id="shrBody"><p class="ws-note" role="status">${T('불러오는 중…','Loading…')}</p></div></div>`;
  }
  function mount(ctx){
    C=ctx;style();
    if(stopSim){stopSim();stopSim=null;}
    if(observer){observer.disconnect();observer=null;}
    const r=route(),root=document.getElementById('shrRoot');if(!root)return;
    if(r.page==='project')return project(root,r.id);
    if(r.page==='user')return user(root,r.id);
    return explore(root,r.q);
  }

  /* ── cards ── */
  function cardHtml(it){
    return `<a class="shr-card" href="#/workshop/share/${+it.id}">
      <div class="shr-thumb">${it.has_thumb?`<img src="${esc(thumbUrl(it))}" alt="" loading="lazy" decoding="async">`:art(it.type)}<span class="shr-badge">${esc(typeName(it.type))}</span>${it.featured?`<span class="shr-pick">${T('추천','Pick')}</span>`:''}</div>
      <div class="shr-body"><span class="shr-title">${esc(it.title)}</span>
        <span class="shr-by">${C.av(it.nickname||'?','s',it.av)}<span>${esc(it.nickname||T('탈퇴한 회원','Former member'))}</span></span>
        <span class="shr-stats"><span title="${T('좋아요','Likes')}">${icon('heart')}${nf(it.likes)}</span><span title="${T('조회','Views')}">${icon('eye')}${nf(it.views)}</span><span title="${T('리믹스','Remixes')}">${icon('remix')}${nf(it.remixes)}</span></span></div></a>`;
  }

  /* ── explore ── */
  function explore(root,q0){
    const body=document.getElementById('shrBody');if(!body)return;
    const st={tab:TABS.some(t=>t[0]===q0.get('tab'))?q0.get('tab'):'popular',type:TYPE_NAMES[q0.get('type')]?q0.get('type'):'',topic:TOPICS.includes(q0.get('topic'))?q0.get('topic'):'',
      sort:SORTS.some(s=>s[0]===q0.get('sort'))?q0.get('sort'):'',q:(q0.get('q')||'').slice(0,60),fav:q0.get('fav')==='1',page:0,more:true,busy:false,seq:0};
    if(st.topic&&st.tab!=='topic')st.tab='topic';
    const save=()=>{const q=new URLSearchParams();if(st.tab!=='popular')q.set('tab',st.tab);for(const k of ['type','topic','sort','q'])if(st[k])q.set(k,st[k]);if(st.fav)q.set('fav','1');
      try{history.replaceState(null,'','#/workshop/share'+(q.toString()?'?'+q:''));}catch(e){}};
    body.innerHTML=`<div class="shr-top"><form class="shr-search" role="search" id="shrSearch">${icon('search')}<input id="shrQ" type="search" maxlength="60" value="${esc(st.q)}" placeholder="${T('제목, 태그, 만든 사람으로 찾기','Search titles, tags or authors')}" aria-label="${T('작품 검색','Search projects')}"><button type="submit">${T('찾기','Search')}</button></form>
        <nav class="shr-me" id="shrMe" aria-label="${T('내 작품','My projects')}"></nav></div>
      <section class="shr-week" id="shrWeek" aria-labelledby="shrWeekH" hidden><h2 id="shrWeekH">${T('이번 주 인기','Popular this week')}</h2><div class="shr-row" id="shrWeekRow"></div></section>
      <div class="shr-tabs" role="tablist" aria-label="${T('작품 목록','Project lists')}">${TABS.map(([k,ko,en])=>`<button type="button" role="tab" data-tab="${k}" aria-selected="${st.tab===k&&!st.fav}">${T(ko,en)}</button>`).join('')}</div>
      <div class="shr-chips" id="shrTopics" ${st.tab==='topic'?'':'hidden'} style="margin:0 0 10px">${TOPICS.map(k=>`<button type="button" data-topic="${k}" aria-pressed="${st.topic===k}">${esc(topicName(k))}</button>`).join('')}</div>
      <div class="shr-filters"><div class="shr-chips" role="group" aria-label="${T('종류','Type')}"><button type="button" data-type="" aria-pressed="${!st.type}">${T('전체','All')}</button>${Object.keys(TYPE_NAMES).map(k=>`<button type="button" data-type="${k}" aria-pressed="${st.type===k}">${esc(typeName(k))}</button>`).join('')}</div>
        <label class="shr-sort">${T('정렬','Sort')}<select id="shrSort"><option value="">${T('탭 기본','Tab default')}</option>${SORTS.map(([k,ko,en])=>`<option value="${k}"${st.sort===k?' selected':''}>${T(ko,en)}</option>`).join('')}</select></label></div>
      <div class="shr-grid" id="shrGrid" aria-live="polite"></div><div class="shr-more"><button type="button" class="shr-btn" id="shrMore" hidden>${T('더 보기','Show more')}</button></div><p class="shr-msg" id="shrMsg"></p>
      <p class="shr-how">${T('문제 제작, 그림 제작, 전산물리 제작에서 만든 것을 «공유하기»로 올리면 여기에 나옵니다. 남의 작품은 «리믹스»로 내 워크샵에 복사해 고칠 수 있고, 원작이 함께 표시됩니다.','Use “Share” in Problems, Figures or Computational physics to post what you made here. “Remix” copies someone’s project into your Workshop to change, and the original is credited.')}</p>`;
    const grid=document.getElementById('shrGrid'),more=document.getElementById('shrMore'),msg=document.getElementById('shrMsg');
    const query=page=>{const q=new URLSearchParams({page:String(page)});const tab=st.fav?'':st.tab==='topic'?'':st.tab;if(tab)q.set('tab',tab);if(st.tab==='topic'&&!st.sort)q.set('sort','popular');
      for(const k of ['type','topic','sort','q'])if(st[k])q.set(k,st[k]);if(st.fav)q.set('fav','1');return '/share?'+q;};
    async function load(reset){
      if(reset){st.page=0;st.more=true;grid.innerHTML='';st.seq++;}
      if(st.busy||!st.more)return;st.busy=true;const seq=st.seq;msg.textContent='';
      try{const r=await api('GET',query(st.page+1));if(seq!==st.seq||!C.here())return;
        st.page=r.page;st.more=r.more;grid.insertAdjacentHTML('beforeend',r.items.map(cardHtml).join(''));
        if(!grid.children.length)grid.innerHTML=`<div class="shr-empty">${st.q?T('찾는 작품이 없습니다. 다른 낱말로 찾아 보세요.','No projects match. Try other words.'):st.fav?T('즐겨찾기한 작품이 없습니다. 작품 페이지에서 ★를 누르면 여기에 모입니다.','No favourites yet. Press ★ on a project to keep it here.'):T('아직 올라온 작품이 없습니다. 첫 작품을 공유해 보세요.','Nothing shared here yet. Be the first to share.')}</div>`;
      }catch(e){if(seq===st.seq)msg.textContent=err(e);}
      finally{if(seq===st.seq){st.busy=false;more.hidden=!st.more;}}
    }
    const repaint=()=>{save();
      body.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(!st.fav&&b.dataset.tab===st.tab)));
      body.querySelectorAll('[data-type]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.type===st.type)));
      body.querySelectorAll('[data-topic]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.topic===st.topic)));
      document.getElementById('shrTopics').hidden=st.tab!=='topic';load(true);};
    body.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{st.tab=b.dataset.tab;st.fav=false;if(st.tab!=='topic')st.topic='';else if(!st.topic)st.topic='mechanics';repaint();});
    body.querySelectorAll('[data-type]').forEach(b=>b.onclick=()=>{st.type=b.dataset.type;repaint();});
    body.querySelectorAll('[data-topic]').forEach(b=>b.onclick=()=>{st.topic=b.dataset.topic;repaint();});
    document.getElementById('shrSort').onchange=e=>{st.sort=e.target.value;repaint();};
    document.getElementById('shrSearch').onsubmit=e=>{e.preventDefault();st.q=document.getElementById('shrQ').value.trim().slice(0,60);repaint();};
    more.onclick=()=>load(false);
    if(typeof IntersectionObserver==='function'){observer=new IntersectionObserver(es=>{if(es.some(x=>x.isIntersecting)&&C.here()&&st.page>0)load(false);},{rootMargin:'600px'});observer.observe(more.parentNode);}
    load(true);
    api('GET','/share?tab=week').then(r=>{if(!C.here()||!r.items.length)return;document.getElementById('shrWeekRow').innerHTML=r.items.map(cardHtml).join('');document.getElementById('shrWeek').hidden=false;}).catch(()=>{});
    C.me().then(me=>{const nav=document.getElementById('shrMe');if(!nav||!C.here())return;
      nav.innerHTML=me?`<a href="#/workshop/share/user/${+me.id}">${T('내 작품','My projects')}</a><a href="#/workshop/share?fav=1" id="shrFav">★ ${T('즐겨찾기','Favourites')}</a>`:`<a href="#/login" id="shrLogin">${T('로그인하고 공유하기','Sign in to share')}</a>`;
      const f=document.getElementById('shrFav');if(f)f.onclick=e=>{e.preventDefault();st.fav=true;repaint();};
      const l=document.getElementById('shrLogin');if(l)l.onclick=()=>{try{sessionStorage.setItem('hlCmBack',location.hash);}catch(x){}};});
  }

  /* ── a project ── */
  const editHash=p=>p.type==='figure'?'#/workshop/draw?share='+p.id:p.type==='set'?'#/workshop/make?share='+p.id:'#/workshop/create?view=edit&id='+p.id;
  async function project(root,id){
    let d;
    try{d=await api('GET','/share/'+id);}catch(e){if(C.here())root.innerHTML=`<div class="phead">${crumbs(T('작품','Project'))}</div><div class="shr-empty" role="alert">${esc(err(e))}</div><p><a class="shr-btn" href="#/workshop/share">${T('작품 공유로 돌아가기','Back to Showcase')}</a></p>`;return;}
    if(!C.here())return;
    const p=d.project,me=await C.me();if(!C.here())return;
    document.title=p.title+' · '+C.title+' · HaslaLab';
    if(p.status==='public')api('POST','/share/'+id+'/view',{}).catch(()=>{});
    const link=location.origin+location.pathname+'#/workshop/share/'+id;
    const status=p.status!=='public'?`<p class="shr-origin" role="status">${p.hidden_by_staff?T('운영진이 숨긴 작품입니다. 나만 볼 수 있습니다.','Staff hid this project. Only you can see it.'):p.status==='draft'?T('아직 공유하지 않은 내 초안입니다. 편집기에서 고친 뒤 «공유하기»를 누르세요.','This is your draft, not shared yet. Change it in the editor, then press “Share”.'):T('공유를 취소한 작품입니다. 나만 볼 수 있습니다.','You unshared this project. Only you can see it.')}</p>`:'';
    const origin=d.original?`<p class="shr-origin">${icon('remix')} ${d.original.gone?T('원작은 더 이상 공유되지 않습니다.','The original is no longer shared.'):`${T('원작','Remixed from')}: <a href="#/workshop/share/${+d.original.id}">${esc(d.original.title)}</a> · ${esc(d.original.nickname||'')}`}</p>`:'';
    const sec=(h,txt)=>txt?`<section class="shr-sec"><h2>${h}</h2><div class="shr-text">${md(txt)}</div></section>`:'';
    root.innerHTML=`<div class="phead">${crumbs(esc(p.title))}</div>${status}
      <div class="shr-proj"><div><div class="shr-stage" id="shrStage"></div><div id="shrCode"></div>
        ${sec(T('사용 방법','How to use'),p.howto)}${sec(T('설명','About'),p.description)}${sec(T('참고 및 출처','Notes and credits'),p.notes)}
        ${p.tags.length?`<section class="shr-sec"><h2>${T('태그','Tags')}</h2><div class="shr-tags">${p.tags.map(t=>`<a href="#/workshop/share?q=${encodeURIComponent(t)}">#${esc(t)}</a>`).join('')}</div></section>`:''}
        <section class="shr-sec" id="shrRemixes"></section>
        <section class="shr-sec" aria-labelledby="shrCmtH"><h2 id="shrCmtH">${T('댓글','Comments')} <span id="shrCmtN">${nf(p.comments)}</span></h2><div id="shrCmtForm"></div><ul class="shr-cmts" id="shrCmts"></ul></section></div>
      <aside class="shr-side"><div class="shr-panel"><span class="shr-badge" style="position:static">${esc(typeName(p.type))}</span> <span class="shr-meta">${esc(topicName(p.topic))}</span>
        <h1>${esc(p.title)}</h1>
        <div class="shr-by">${C.av(p.author.nickname||'?','s',p.author.av)}<span>${p.author.nickname?`<a href="#/workshop/share/user/${+p.author.id}">${esc(p.author.nickname)}</a>`:T('탈퇴한 회원','Former member')}</span></div>
        <p class="shr-meta">${T('공유','Shared')} ${day(p.shared_at)}${p.updated_at&&p.updated_at!==p.created_at?` · ${T('고침','Updated')} ${day(p.updated_at)}`:''}</p>
        <div class="shr-stats" style="margin-top:8px"><span>${icon('eye')}${nf(p.views)}</span><span>${icon('remix')}${nf(p.remixes)}</span><span>${icon('chat')}${nf(p.comments)}</span></div>
        ${origin}
        <div class="shr-acts"><button type="button" class="shr-btn${d.liked?' on':''}" id="shrLike" aria-pressed="${d.liked}">${icon('heart')}<span>${nf(p.likes)}</span></button>
          <button type="button" class="shr-btn${d.faved?' on':''}" id="shrFavB" aria-pressed="${d.faved}">${icon('star')}<span>${nf(p.favs)}</span></button>
          <button type="button" class="shr-btn" id="shrLink">${icon('link')}${T('링크 복사','Copy link')}</button></div>
        <div class="shr-acts">${p.mine?`<a class="shr-btn pri" href="${editHash(p)}">${icon('edit')}${T('편집기에서 열기','Open in editor')}</a>`:`<button type="button" class="shr-btn pri" id="shrRemix">${icon('remix')}${T('리믹스','Remix')}</button>`}
          ${p.type==='sim'||p.type==='python'?`<button type="button" class="shr-btn" id="shrShowCode" aria-expanded="false">${icon('code')}${T('코드 보기','See the code')}</button>`:''}</div>
        <div class="shr-acts">${p.mine?`<button type="button" class="shr-btn quiet" id="shrEdit">${T('설명 고치기','Edit details')}</button>${p.status==='public'?`<button type="button" class="shr-btn quiet" id="shrUnshare">${T('공유 취소','Unshare')}</button>`:''}`:''}
          ${d.staff&&p.status==='public'?`<button type="button" class="shr-btn quiet" id="shrPick">${p.featured?T('추천 해제','Remove pick'):T('추천','Staff pick')}</button>${p.mine?'':`<button type="button" class="shr-btn quiet" id="shrHide">${T('숨기기','Hide')}</button>`}`:''}
          ${!p.mine?`<button type="button" class="shr-btn quiet" id="shrReport">${icon('flag')}${T('신고','Report')}</button>`:''}</div>
        <p class="shr-msg" id="shrMsg2" role="status"></p><div id="shrEditBox"></div></div></aside></div>`;
    const msg=(t,ok)=>{const m=document.getElementById('shrMsg2');if(m){m.textContent=t;m.classList.toggle('shr-ok',!!ok);}};
    const needMe=()=>{if(me)return true;msg(err({code:'login_required'}));return false;};
    stage(document.getElementById('shrStage'),p);
    const $=x=>document.getElementById(x);
    $('shrLike').onclick=async()=>{if(!needMe())return;try{const on=$('shrLike').getAttribute('aria-pressed')!=='true',r=await api('POST',`/share/${id}/like`,{on});$('shrLike').setAttribute('aria-pressed',String(r.liked));$('shrLike').classList.toggle('on',r.liked);$('shrLike').lastElementChild.textContent=nf(r.likes);}catch(e){msg(err(e));}};
    $('shrFavB').onclick=async()=>{if(!needMe())return;try{const on=$('shrFavB').getAttribute('aria-pressed')!=='true',r=await api('POST',`/share/${id}/fav`,{on});$('shrFavB').setAttribute('aria-pressed',String(r.faved));$('shrFavB').classList.toggle('on',r.faved);$('shrFavB').lastElementChild.textContent=nf(r.favs);}catch(e){msg(err(e));}};
    $('shrLink').onclick=async()=>{try{await navigator.clipboard.writeText(link);msg(T('링크를 복사했습니다.','Link copied.'),true);}catch(e){msg(link,true);}};
    if($('shrRemix'))$('shrRemix').onclick=async()=>{if(!needMe())return;try{const r=await api('POST',`/share/${id}/remix`,{});location.hash=r.edit.slice(1);}catch(e){msg(err(e));}};
    if($('shrShowCode'))$('shrShowCode').onclick=()=>{const box=$('shrCode'),open=!box.innerHTML;box.innerHTML=open?`<pre class="shr-code" tabindex="0" aria-label="${T('코드','Code')}">${esc(p.type==='sim'?p.code:p.starter+'\n\n# ── grader.py ──\n'+p.grader)}</pre>`:'';$('shrShowCode').setAttribute('aria-expanded',String(open));};
    if($('shrUnshare'))$('shrUnshare').onclick=async()=>{if(!confirm(T('공유를 취소할까요? 작품은 내 워크샵에 남습니다.','Unshare this project? It stays in your Workshop.')))return;try{await api('DELETE','/share/'+id);location.hash='/workshop/share/user/'+(+me.id);}catch(e){msg(err(e));}};
    if($('shrHide'))$('shrHide').onclick=async()=>{if(!confirm(T('이 작품을 숨길까요? 만든 사람은 다시 공유할 수 없습니다.','Hide this project? The author cannot share it again.')))return;try{await api('DELETE','/share/'+id);location.hash='/workshop/share';}catch(e){msg(err(e));}};
    if($('shrPick'))$('shrPick').onclick=async()=>{try{const r=await api('POST',`/share/${id}/feature`,{on:!p.featured});p.featured=r.featured;$('shrPick').textContent=r.featured?T('추천 해제','Remove pick'):T('추천','Staff pick');msg(r.featured?T('추천에 올렸습니다.','Added to staff picks.'):T('추천에서 내렸습니다.','Removed from staff picks.'),true);}catch(e){msg(err(e));}};
    if($('shrReport'))$('shrReport').onclick=async()=>{if(!needMe())return;const reason=prompt(T('신고 이유를 적어 주세요. 운영진이 확인합니다.','Why are you reporting this project? Staff will check it.'));if(!reason||!reason.trim())return;try{await api('POST',`/share/${id}/report`,{reason:reason.trim().slice(0,300)});msg(T('신고했습니다. 고맙습니다.','Reported. Thank you.'),true);}catch(e){msg(err(e));}};
    if($('shrEdit'))$('shrEdit').onclick=()=>editForm($('shrEditBox'),p,msg);
    remixes(d);
    comments(id,p,me);
  }
  function remixes(d){
    const box=document.getElementById('shrRemixes');if(!box)return;
    if(!d.remixList.length){box.remove();return;}
    box.innerHTML=`<h2>${T('이 작품의 리믹스','Remixes of this project')} <span class="shr-meta">${nf(d.project.remixes)}</span></h2><div class="shr-row">${d.remixList.map(cardHtml).join('')}</div>`;
  }
  function editForm(box,p,msg){
    if(box.innerHTML){box.innerHTML='';return;}
    box.innerHTML=`<form class="shr-form" id="shrEditF"><label>${T('제목','Title')}<input name="title" maxlength="80" value="${esc(p.title)}" required></label>
      <label>${T('설명','About')}<textarea name="description" maxlength="3000">${esc(p.description)}</textarea></label>
      <label>${T('사용 방법','How to use')}<textarea name="howto" maxlength="3000">${esc(p.howto)}</textarea></label>
      <label>${T('참고 및 출처','Notes and credits')}<textarea name="notes" maxlength="2000">${esc(p.notes)}</textarea></label>
      <label>${T('태그 (쉼표로 나눔, 8개까지)','Tags (comma-separated, up to 8)')}<input name="tags" value="${esc(p.tags.join(', '))}"></label>
      <label>${T('주제','Topic')}<select name="topic">${TOPICS.map(k=>`<option value="${k}"${p.topic===k?' selected':''}>${esc(topicName(k))}</option>`).join('')}</select></label>
      <div class="shr-row2"><button type="button" class="shr-btn quiet" id="shrEditX">${T('닫기','Close')}</button><button type="submit" class="shr-btn pri">${T('저장','Save')}</button></div></form>`;
    document.getElementById('shrEditX').onclick=()=>{box.innerHTML='';};
    document.getElementById('shrEditF').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target),o={};for(const k of ['title','description','howto','notes','topic'])o[k]=String(f.get(k)||'');
      o.tags=String(f.get('tags')||'').split(',').map(s=>s.trim()).filter(Boolean);
      try{await api('PATCH','/share/'+p.id,o);msg(T('저장했습니다.','Saved.'),true);setTimeout(()=>C.here()&&mount(C),400);}catch(x){msg(err(x));}};
  }

  /* what runs: a simulation in the opaque-origin sandbox (the same message protocol as create-studio.js's runSandbox) */
  function runSim(host,code){
    host.innerHTML=`<iframe sandbox="allow-scripts" src="sim-sandbox.html" title="${T('시뮬레이션','Simulation')}" referrerpolicy="no-referrer"></iframe><p class="shr-msg" id="shrSimMsg"></p>`;
    const f=host.querySelector('iframe');let alive=true,sent=false,beat=Date.now();
    const on=e=>{
      if(!alive)return;if(!f.isConnected){stop();return;}
      if(e.source!==f.contentWindow||e.origin!=='null')return;
      const d=e.data;if(!d||typeof d!=='object'||typeof d.type!=='string')return;beat=Date.now();
      if(d.type==='sim-ready'&&!sent){sent=true;f.contentWindow.postMessage({type:'run',code:String(code||''),theme:document.documentElement.dataset.theme==='dark'?'dark':'light'},'*');}
      else if(d.type==='sim-height'&&Number.isFinite(d.height))f.style.height=Math.max(320,Math.min(1400,Math.ceil(d.height)+4))+'px';
      else if(d.type==='sim-error'&&typeof d.message==='string'){const m=document.getElementById('shrSimMsg');if(m)m.textContent=T('실행 중 오류: ','Error while running: ')+d.message.slice(0,300);}
    };
    addEventListener('message',on);
    const dog=setInterval(()=>{if(!alive)return;if(!f.isConnected){stop();return;}if(document.hidden)return;
      if(Date.now()-beat>(sent?6000:20000)){const m=document.getElementById('shrSimMsg');stop();f.remove();if(m)m.textContent=T('시뮬레이션이 응답하지 않아 멈췄습니다.','The simulation stopped responding and was stopped.');}},1000);
    function stop(){if(!alive)return;alive=false;clearInterval(dog);removeEventListener('message',on);}
    return stop;
  }
  function stage(box,p){
    if(p.type==='sim'){
      box.innerHTML='<div id="shrSim"></div>'+(p.question?`<div class="shr-q"><b>${T('질문','Question')}</b><div class="shr-text">${md(p.question)}</div>${p.answer?`<a class="shr-btn" href="#/workshop/create?view=play&id=${+p.id}">${T('답 확인하기','Check your answer')}</a>`:''}</div>`:'');
      stopSim=runSim(document.getElementById('shrSim'),p.code);return;
    }
    if(p.type==='python'){
      /* create.html's play view: the statement, the solver's code and the grader in a Pyodide worker */
      const q=new URLSearchParams({embed:'1',view:'play',id:String(p.id),lang:C.uiLang==='ko'?'ko':'en',theme:document.documentElement.dataset.theme==='dark'?'dark':'light'});
      box.innerHTML=`<iframe id="learnCreateFrame" src="create.html?${q}" title="${esc(p.title)}" referrerpolicy="same-origin" style="height:640px"></iframe>`;return;
    }
    if(p.type==='figure'){
      const fallback=()=>{box.innerHTML=p.has_thumb?`<img class="shr-fig" src="${esc(thumbUrl(p))}" alt="${esc(p.title)}">`:`<div class="shr-thumb">${art('figure')}</div>`;};
      fallback();
      /* the site's own renderer draws the stored scene; as an <img> the SVG cannot run anything */
      Promise.all([import('./draw-render.mjs'),import('./draw-scene.mjs')]).then(([R,S])=>{if(!box.isConnected)return;const scene=p.payload.scene,view=scene.view||S.sceneBounds?.(scene);
        const svg=R.renderSVG(scene,{width:900,...(view?{view}:{})}),s=typeof svg==='string'?svg:svg?.svg;if(typeof s!=='string'||!/^<svg[\s>]/.test(s.trim()))return;
        box.innerHTML=`<img class="shr-fig" alt="${esc(p.title)}" src="data:image/svg+xml;base64,${b64(s)}">`;}).catch(()=>{});
      return;
    }
    const set=p.payload||{items:[]};
    box.innerHTML=`${set.title?`<h2>${esc(set.title)}</h2>`:''}${set.info?`<p class="shr-meta">${esc(set.info)}</p>`:''}<p class="shr-meta">${T(`${set.items.length}문항`,`${set.items.length} problems`)}${set.minutes?` · ${T(`${+set.minutes}분`,`${+set.minutes} min`)}`:''}</p>
      <ol class="shr-set">${set.items.map(it=>`<li>${it.own?`${md(it.own.q)}${it.own.fig&&/^data:image\/svg\+xml;base64,[A-Za-z0-9+/]+=*$/.test(it.own.fig.src)?`<img src="${it.own.fig.src}" alt="${T('그림','Figure')}" width="${+it.own.fig.w}" height="${+it.own.fig.h}" loading="lazy">`:''}${Array.isArray(it.own.choices)?`<ol class="shr-ch" type="1">${it.own.choices.map(c=>`<li style="list-style:decimal">${esc(c)}</li>`).join('')}</ol>`:''}`
        :`${T('하슬라랩 문제','HaslaLab problem')} <code class="shr-code" style="display:inline;padding:1px 5px;border:0">${esc(it.key)}</code>`} <span class="shr-meta">(${+it.pts||0}${T('점',' pts')})</span></li>`).join('')}</ol>
      <p class="shr-meta">${T('정답과 풀이는 «리믹스»로 문제 제작에 가져가면 볼 수 있습니다.','Remix it into Problems to see the answers and solutions.')}</p>`;
  }

  /* ── comments: the community's rules, escaped ── */
  async function comments(id,p,me){
    const list=document.getElementById('shrCmts'),form=document.getElementById('shrCmtForm');if(!list)return;
    const paintForm=(box,parent)=>{box.innerHTML=me?`<form class="shr-form" data-parent="${parent||''}"><textarea maxlength="2000" required placeholder="${T('작품에 대한 생각이나 질문을 남겨 주세요.','Say what you think, or ask a question.')}" aria-label="${T('댓글','Comment')}"></textarea><p class="shr-msg"></p><div class="shr-row2"><button type="submit" class="shr-btn pri">${T('댓글 쓰기','Post')}</button></div></form>`
      :`<p class="ws-note"><a href="#/login" class="shr-login">${T('로그인','Sign in')}</a>${T('하면 댓글을 쓸 수 있습니다.',' to comment.')}</p>`;
      const f=box.querySelector('form');if(f)f.onsubmit=async e=>{e.preventDefault();const t=f.querySelector('textarea').value.trim();if(!t)return;
        try{await api('POST',`/share/${id}/comments`,{body:t,...(parent?{parent_id:parent}:{})});f.querySelector('textarea').value='';load();}catch(x){f.querySelector('.shr-msg').textContent=err(x);}};
      const l=box.querySelector('.shr-login');if(l)l.onclick=()=>{try{sessionStorage.setItem('hlCmBack',location.hash);}catch(x){}};};
    if(p.status==='public')paintForm(form,null);
    async function load(){
      let r;try{r=await api('GET',`/share/${id}/comments`);}catch(e){list.innerHTML=`<li class="shr-msg">${esc(err(e))}</li>`;return;}
      if(!C.here())return;
      document.getElementById('shrCmtN').textContent=nf(r.comments.length);
      list.innerHTML=r.comments.length?r.comments.map(c=>`<li class="shr-cmt${c.parent_id?' re':''}" data-id="${+c.id}">${C.av(c.nickname||'?','',c.av)}<div><b>${esc(c.nickname||T('탈퇴한 회원','Former member'))}</b><time>${day(c.created_at)}</time>
        <p>${esc(c.body)}</p><div class="shr-cacts">${me&&p.status==='public'?`<button type="button" data-reply="${+(c.parent_id||c.id)}">${T('답글','Reply')}</button>`:''}${c.mine?`<button type="button" data-del="${+c.id}">${T('삭제','Delete')}</button>`:me?`<button type="button" data-rep="${+c.id}">${T('신고','Report')}</button>`:''}</div><div class="shr-rbox"></div></div></li>`).join('')
        :`<li class="ws-note">${T('첫 댓글을 남겨 보세요.','No comments yet.')}</li>`;
      list.querySelectorAll('[data-reply]').forEach(b=>b.onclick=()=>{const box=b.closest('li').querySelector('.shr-rbox');if(box.innerHTML){box.innerHTML='';return;}paintForm(box,+b.dataset.reply);box.querySelector('textarea')?.focus();});
      list.querySelectorAll('[data-del]').forEach(b=>b.onclick=async()=>{if(!confirm(T('댓글을 지울까요? 답글도 함께 지워집니다.','Delete this comment and its replies?')))return;try{await api('DELETE','/share/comments/'+b.dataset.del);load();}catch(e){alert(err(e));}});
      list.querySelectorAll('[data-rep]').forEach(b=>b.onclick=async()=>{const reason=prompt(T('신고 이유를 적어 주세요.','Why are you reporting this comment?'));if(!reason||!reason.trim())return;try{await api('POST',`/share/comments/${b.dataset.rep}/report`,{reason:reason.trim().slice(0,300)});b.textContent=T('신고함','Reported');b.disabled=true;}catch(e){alert(err(e));}});
    }
    load();
  }

  /* ── an author ── */
  async function user(root,id){
    let r;try{r=await api('GET','/share/user/'+id+'?sort=new');}catch(e){if(C.here())root.innerHTML=`<div class="phead">${crumbs(T('만든 사람','Author'))}</div><div class="shr-empty" role="alert">${esc(err(e))}</div>`;return;}
    if(!C.here())return;
    const u=r.user,me=await C.me();if(!C.here())return;
    let page=r.page,more=r.more;
    root.innerHTML=`<div class="phead">${crumbs(esc(u.nickname))}</div><div class="shr-user">${C.av(u.nickname,'',u.av)}<div><h1>${esc(u.nickname)}${me&&me.id===u.id?` <span class="shr-meta">(${T('나','me')})</span>`:''}</h1>
      <p>${T(`공유한 작품 ${nf(r.totals.projects)}개 · 받은 좋아요 ${nf(r.totals.likes)} · 조회 ${nf(r.totals.views)}`,`${nf(r.totals.projects)} shared · ${nf(r.totals.likes)} likes · ${nf(r.totals.views)} views`)}</p></div></div>
      <div class="shr-grid" id="shrGrid">${r.items.map(cardHtml).join('')||`<div class="shr-empty">${T('아직 공유한 작품이 없습니다.','Nothing shared yet.')}</div>`}</div>
      <div class="shr-more"><button type="button" class="shr-btn" id="shrMore"${more?'':' hidden'}>${T('더 보기','Show more')}</button></div>`;
    document.getElementById('shrMore').onclick=async()=>{try{const n=await api('GET',`/share/user/${id}?sort=new&page=${page+1}`);if(!C.here())return;page=n.page;more=n.more;document.getElementById('shrGrid').insertAdjacentHTML('beforeend',n.items.map(cardHtml).join(''));document.getElementById('shrMore').hidden=!more;}catch(e){}};
  }

  window.HL_SHARE_PAGE={view,mount,_md:s=>{const keep=C;C=C||{esc:x=>String(x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])),ko:true,LX:x=>x};try{return md(s);}finally{C=keep;}},_route:route};
})();
